import { randomUUID } from "node:crypto";
import { CATALOG, CURRENCIES } from "./catalog.js";

export class AuthorityError extends Error {
  constructor(code, message) {
    super(message);
    this.name = "AuthorityError";
    this.code = code;
  }
}

export function initialState() {
  return {
    version: 1,
    balances: Object.fromEntries(
      Object.entries(CURRENCIES).map(([currency, config]) => [currency, config.initialMinor]),
    ),
    consents: {},
    tasks: {},
    payments: {},
    resourceDeliveries: {},
    idempotency: {},
    events: [],
    sequence: 1,
  };
}

function fail(code, message) {
  throw new AuthorityError(code, message);
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function event(state, type, paymentId, details = {}) {
  state.events.push({
    id: `evt-${state.sequence++}`,
    type,
    paymentId,
    at: new Date().toISOString(),
    ...details,
  });
}

function quoteFor(id) {
  const quote = CATALOG[id];
  if (!quote) fail("UNKNOWN_QUOTE", "报价不存在。");
  return quote;
}

function markCaptured(state, payment) {
  payment.status = "captured";
  payment.reservedMinor = payment.amountMinor;
  payment.receipt = {
    id: `rcpt-${randomUUID()}`,
    paymentId: payment.id,
    amountMinor: payment.amountMinor,
    currency: payment.currency,
    items: clone(payment.items),
    simulated: true,
  };
  payment.fulfillmentStatus = "pending";
  event(state, "receipt.issued", payment.id, { receiptId: payment.receipt.id });
}

export function createConsent(state, { ownerId, taskId, quoteId }, now = Date.now()) {
  if (!ownerId || !taskId) fail("INVALID_SCOPE", "用户和任务标识不能为空。");
  const quote = quoteFor(quoteId);
  const consent = {
    id: `cns-${randomUUID()}`,
    ownerId,
    taskId,
    quoteId: quote.id,
    merchantId: quote.merchantId,
    items: clone(quote.items),
    amountMinor: quote.amountMinor,
    currency: quote.currency,
    quoteVersion: quote.quoteVersion,
    createdAt: now,
    expiresAt: now + 15 * 60_000,
    revokedAt: null,
    usedByPaymentId: null,
  };
  state.consents[consent.id] = consent;
  return clone(consent);
}

export function createTaskConsent(state, { ownerId, taskId, quoteId }, now = Date.now()) {
  const task = state.tasks[taskId];
  if (!task || task.ownerId !== ownerId) fail("TASK_NOT_FOUND", "任务不存在或不属于此用户。");
  if (!task.suggestions.some((suggestion) => suggestion.type === "quote" && suggestion.quoteId === quoteId)) {
    fail("TERMS_CHANGED", "报价不在此任务的结构化建议中。");
  }
  return createConsent(state, { ownerId, taskId, quoteId }, now);
}

export function revokeConsent(state, { ownerId, consentId }, now = Date.now()) {
  const consent = state.consents[consentId];
  if (!consent || consent.ownerId !== ownerId) fail("CONSENT_NOT_FOUND", "找不到此用户的授权。");
  if (!consent.revokedAt && !consent.usedByPaymentId) {
    consent.revokedAt = now;
  }
  return clone(consent);
}

function validateConsent(state, input, now) {
  const consent = state.consents[input.consentId];
  if (!consent || consent.ownerId !== input.ownerId) fail("CONSENT_NOT_FOUND", "授权不存在或不属于此用户。");
  if (consent.revokedAt) fail("CONSENT_REVOKED", "授权已撤销。");
  if (consent.expiresAt <= now) fail("CONSENT_EXPIRED", "授权已过期。");
  if (consent.usedByPaymentId) fail("CONSENT_USED", "此授权已用于付款。");
  const quote = quoteFor(consent.quoteId);
  const termsMatch =
    consent.taskId === input.taskId &&
    consent.merchantId === quote.merchantId &&
    consent.amountMinor === quote.amountMinor &&
    consent.currency === quote.currency &&
    consent.quoteVersion === quote.quoteVersion &&
    JSON.stringify(consent.items) === JSON.stringify(quote.items) &&
    (input.quoteVersion === undefined || input.quoteVersion === consent.quoteVersion) &&
    (input.merchantId === undefined || input.merchantId === consent.merchantId) &&
    (input.amountMinor === undefined || input.amountMinor === consent.amountMinor) &&
    (input.currency === undefined || input.currency === consent.currency) &&
    (input.items === undefined || JSON.stringify(input.items) === JSON.stringify(consent.items));
  if (!termsMatch) fail("TERMS_CHANGED", "授权条款与当前报价不一致。");
  return { consent, quote };
}

export function createPayment(state, input, now = Date.now()) {
  if (!input.idempotencyKey || typeof input.idempotencyKey !== "string") {
    fail("IDEMPOTENCY_REQUIRED", "付款需要幂等键。");
  }
  const fingerprint = JSON.stringify({
    ownerId: input.ownerId,
    taskId: input.taskId,
    consentId: input.consentId,
    outcome: input.outcome ?? "captured",
    merchantId: input.merchantId,
    amountMinor: input.amountMinor,
    currency: input.currency,
    quoteVersion: input.quoteVersion,
    items: input.items,
  });
  const previous = state.idempotency[input.idempotencyKey];
  if (previous) {
    if (previous.fingerprint !== fingerprint) fail("IDEMPOTENCY_CONFLICT", "幂等键已用于不同请求。");
    return clone(state.payments[previous.paymentId]);
  }
  const { consent, quote } = validateConsent(state, input, now);
  if (!Object.hasOwn(state.balances, quote.currency)) fail("CURRENCY_UNSUPPORTED", "币种不受支持。");
  if (state.balances[quote.currency] < quote.amountMinor) fail("BUDGET_EXCEEDED", "该币种的可用预算不足。");
  const outcome = input.outcome ?? "captured";
  if (!["captured", "unknown", "declined"].includes(outcome)) fail("INVALID_OUTCOME", "只允许指定模拟结果。");

  const payment = {
    id: `pay-${randomUUID()}`,
    consentId: consent.id,
    ownerId: consent.ownerId,
    taskId: consent.taskId,
    merchantId: quote.merchantId,
    quoteId: quote.id,
    items: clone(quote.items),
    amountMinor: quote.amountMinor,
    currency: quote.currency,
    quoteVersion: quote.quoteVersion,
    status: outcome === "declined" ? "declined" : outcome === "unknown" ? "unknown" : "captured",
    reservedMinor: outcome === "declined" ? 0 : quote.amountMinor,
    refundedMinor: 0,
    receipt: null,
    fulfillmentStatus: "not_started",
    createdAt: now,
    lastReconciledAt: null,
    reconciliationCount: 0,
  };
  if (outcome !== "declined") state.balances[quote.currency] -= quote.amountMinor;
  consent.usedByPaymentId = payment.id;
  state.payments[payment.id] = payment;
  state.idempotency[input.idempotencyKey] = { fingerprint, paymentId: payment.id };
  event(state, `payment.${payment.status}`, payment.id, { idempotencyKey: input.idempotencyKey });
  if (outcome === "captured") markCaptured(state, payment);
  return clone(payment);
}

export function reconcilePayment(state, { paymentId }, now = Date.now()) {
  const payment = state.payments[paymentId];
  if (!payment) fail("PAYMENT_NOT_FOUND", "付款不存在。");
  if (payment.status !== "unknown") return clone(payment);
  markCaptured(state, payment);
  payment.lastReconciledAt = now;
  payment.reconciliationCount += 1;
  event(state, "payment.reconciled_captured", payment.id);
  return clone(payment);
}

export function fulfillPayment(state, { ownerId, paymentId }) {
  const payment = state.payments[paymentId];
  if (!payment || payment.ownerId !== ownerId) fail("PAYMENT_NOT_FOUND", "付款不存在或不属于此用户。");
  if (!["captured", "partially_refunded"].includes(payment.status) || !payment.receipt) {
    fail("PAYMENT_NOT_FULFILLABLE", "只有已模拟扣款并生成收据的订单可以履约。");
  }
  if (payment.fulfillmentStatus === "pending" || payment.fulfillmentStatus === "retrying") {
    payment.fulfillmentStatus = "fulfilled";
    payment.fulfilledAt = Date.now();
    event(state, "fulfillment.simulated", payment.id);
  }
  return clone(payment);
}

export function recordFulfillmentFailure(state, { ownerId, paymentId, reason = "simulated_failure" }) {
  const payment = state.payments[paymentId];
  if (!payment || payment.ownerId !== ownerId) fail("PAYMENT_NOT_FOUND", "付款不存在或不属于此用户。");
  if (payment.status !== "captured" && payment.status !== "partially_refunded") {
    fail("PAYMENT_NOT_FULFILLABLE", "只有已确认扣款的订单可以进入履约处理。");
  }
  if (payment.fulfillmentStatus !== "pending" && payment.fulfillmentStatus !== "retrying") {
    fail("FULFILLMENT_NOT_PENDING", "只有待处理或重试中的履约可以失败。");
  }
  if (!["simulated_failure", "merchant_unavailable"].includes(reason)) {
    fail("INVALID_FAILURE_REASON", "履约失败原因不在本地模拟清单中。");
  }
  payment.fulfillmentStatus = "manual_review";
  payment.fulfillmentFailure = { reason, recordedAt: Date.now() };
  event(state, "fulfillment.manual_review_required", payment.id, { reason });
  return clone(payment);
}

export function resolveFulfillment(state, { ownerId, paymentId, action }) {
  const payment = state.payments[paymentId];
  if (!payment || payment.ownerId !== ownerId) fail("PAYMENT_NOT_FOUND", "付款不存在或不属于此用户。");
  if (payment.fulfillmentStatus !== "manual_review") {
    fail("FULFILLMENT_NOT_IN_REVIEW", "订单不处于待人工处理状态。");
  }
  if (action === "retry") {
    payment.fulfillmentStatus = "retrying";
    payment.fulfillmentRetryCount = (payment.fulfillmentRetryCount ?? 0) + 1;
    event(state, "fulfillment.retry_authorized", payment.id);
    return clone(payment);
  }
  if (action === "refund") {
    const remaining = payment.amountMinor - payment.refundedMinor;
    if (remaining <= 0) fail("REFUND_LIMIT", "订单没有可补偿退款余额。");
    refundPayment(state, {
      ownerId,
      paymentId,
      amountMinor: remaining,
      idempotencyKey: `fulfillment-compensation-${payment.id}`,
    });
    payment.fulfillmentStatus = "compensated";
    event(state, "fulfillment.compensated_refund", payment.id);
    return clone(payment);
  }
  fail("INVALID_FULFILLMENT_ACTION", "人工处理操作只允许 retry 或 refund。");
}

export function deliverPaidResource(state, { ownerId, paymentId }) {
  const payment = state.payments[paymentId];
  if (!payment || payment.ownerId !== ownerId) fail("PAYMENT_NOT_FOUND", "付款不存在或不属于此用户。");
  if (payment.quoteId !== "travel-guide" || payment.status !== "captured" || !payment.receipt) {
    fail("RESOURCE_NOT_PAID", "该资源需要匹配的已确认模拟付款。");
  }
  const existing = state.resourceDeliveries[payment.id];
  if (existing) return clone(existing);
  const delivery = {
    id: `delivery-${randomUUID()}`,
    paymentId,
    resourceId: "travel-guide",
    content: "模拟旅行情报：旧城区步行环线全程 2.4 公里；雨天备选为中央市场室内展区。此固定内容不含实时数据。",
    deliveredAt: Date.now(),
    simulated: true,
  };
  state.resourceDeliveries[payment.id] = delivery;
  payment.fulfillmentStatus = "fulfilled";
  event(state, "resource.delivered_simulated", payment.id, { deliveryId: delivery.id });
  return clone(delivery);
}

export function refundPayment(state, { ownerId, paymentId, amountMinor, idempotencyKey }) {
  const payment = state.payments[paymentId];
  if (!payment || payment.ownerId !== ownerId) fail("PAYMENT_NOT_FOUND", "付款不存在或不属于此用户。");
  if (!idempotencyKey || typeof idempotencyKey !== "string") fail("IDEMPOTENCY_REQUIRED", "退款需要幂等键。");
  const fingerprint = JSON.stringify({ ownerId, paymentId, amountMinor });
  const previous = state.idempotency[idempotencyKey];
  if (previous) {
    if (previous.fingerprint !== fingerprint) fail("IDEMPOTENCY_CONFLICT", "幂等键已用于不同请求。");
    return clone(payment);
  }
  if (payment.status !== "captured" && payment.status !== "partially_refunded") {
    fail("PAYMENT_NOT_REFUNDABLE", "只有已确认扣款的模拟付款可以退款。");
  }
  if (!Number.isSafeInteger(amountMinor) || amountMinor <= 0) fail("INVALID_AMOUNT", "退款金额必须是正整数最小货币单位。");
  if (payment.refundedMinor + amountMinor > payment.amountMinor) fail("REFUND_LIMIT", "累计退款不能超过已扣款金额。");
  payment.refundedMinor += amountMinor;
  payment.status = payment.refundedMinor === payment.amountMinor ? "refunded" : "partially_refunded";
  state.balances[payment.currency] += amountMinor;
  state.idempotency[idempotencyKey] = { fingerprint, paymentId };
  event(state, "payment.refunded", payment.id, { amountMinor, idempotencyKey });
  return clone(payment);
}

export function applyPaymentEvent(state, { paymentId, eventId, status }) {
  const payment = state.payments[paymentId];
  if (!payment) fail("PAYMENT_NOT_FOUND", "付款不存在。");
  if (!eventId || !["authorized", "captured", "declined"].includes(status)) {
    fail("INVALID_EVENT", "事件标识或状态无效。");
  }
  if (state.events.some((entry) => entry.externalEventId === eventId)) return clone(payment);
  const allowed = {
    unknown: new Set(["authorized", "captured", "declined"]),
    authorized: new Set(["captured", "declined"]),
    captured: new Set(),
    partially_refunded: new Set(),
    refunded: new Set(),
    declined: new Set(),
  };
  if (!allowed[payment.status]?.has(status)) return clone(payment);
  if (status === "declined") {
    state.balances[payment.currency] += payment.reservedMinor;
    payment.reservedMinor = 0;
  }
  if (status === "captured") markCaptured(state, payment);
  payment.status = status;
  event(state, `payment.event_${status}`, payment.id, { externalEventId: eventId });
  return clone(payment);
}

export function snapshot(state) {
  return {
    demoMode: "SIMULATED / OFFLINE",
    balances: clone(state.balances),
    catalog: clone(CATALOG),
    consents: Object.values(state.consents).map(clone),
    tasks: Object.values(state.tasks).map(clone),
    payments: Object.values(state.payments).map(clone),
    resourceDeliveries: Object.values(state.resourceDeliveries).map(clone),
    events: clone(state.events),
  };
}
