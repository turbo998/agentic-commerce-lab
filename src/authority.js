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
    payments: {},
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
  if (payment.fulfillmentStatus === "pending") {
    payment.fulfillmentStatus = "fulfilled";
    payment.fulfilledAt = Date.now();
    event(state, "fulfillment.simulated", payment.id);
  }
  return clone(payment);
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
    payments: Object.values(state.payments).map(clone),
    events: clone(state.events),
  };
}
