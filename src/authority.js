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
  const initialBalances = Object.fromEntries(
    Object.entries(CURRENCIES).map(([currency, config]) => [currency, config.initialMinor]),
  );
  return {
    version: 1,
    balances: initialBalances,
    tenantBalances: { "tenant-alt": clone(initialBalances) },
    consents: {},
    consentRequests: {},
    resourceChallenges: {},
    tasks: {},
    payments: {},
    refundRequests: {},
    resourceDeliveries: {},
    idempotency: {},
    events: [],
    sequence: 1,
  };
}

function balancesFor(state, tenantId = "tenant-demo") {
  if (!tenantId || tenantId === "tenant-demo") return state.balances;
  if (!state.tenantBalances) state.tenantBalances = {};
  if (!state.tenantBalances[tenantId]) {
    state.tenantBalances[tenantId] = Object.fromEntries(
      Object.entries(CURRENCIES).map(([currency, config]) => [currency, config.initialMinor]),
    );
  }

  return state.tenantBalances[tenantId];
}

export function resetTenantState(state, tenantId) {
  const owned = (record) => record.tenantId === tenantId;
  const taskIds = new Set(Object.values(state.tasks).filter(owned).map((task) => task.id));
  const consentRequestIds = new Set(Object.values(state.consentRequests).filter(owned).map((item) => item.id));
  const paymentIds = new Set(Object.values(state.payments).filter(owned).map((item) => item.id));
  const refundRequestIds = new Set(Object.values(state.refundRequests).filter(owned).map((item) => item.id));
  for (const [key, challenge] of Object.entries(state.resourceChallenges ?? {})) {
    if (taskIds.has(challenge.taskId)) delete state.resourceChallenges[key];
  }
  for (const [key, record] of Object.entries(state.tasks)) if (owned(record)) delete state.tasks[key];
  for (const [key, record] of Object.entries(state.consentRequests)) if (owned(record)) delete state.consentRequests[key];
  for (const [key, record] of Object.entries(state.consents)) if (owned(record)) delete state.consents[key];
  for (const [key, record] of Object.entries(state.payments)) if (owned(record)) delete state.payments[key];
  for (const [key, record] of Object.entries(state.refundRequests)) if (owned(record)) delete state.refundRequests[key];
  for (const [key, delivery] of Object.entries(state.resourceDeliveries)) {
    if (paymentIds.has(delivery.paymentId)) delete state.resourceDeliveries[key];
  }
  for (const [key, record] of Object.entries(state.idempotency)) {
    if (paymentIds.has(record.paymentId) || refundRequestIds.has(record.requestId)) delete state.idempotency[key];
  }
  state.events = state.events.filter((entry) =>
    !(entry.taskId && taskIds.has(entry.taskId)) &&
    !(entry.paymentId && paymentIds.has(entry.paymentId)) &&
    !(entry.consentRequestId && consentRequestIds.has(entry.consentRequestId)),
  );
  balancesFor(state, tenantId);
  const initial = initialState();
  Object.assign(balancesFor(state, tenantId), initial.balances);
  return state;
}

function taskBudgetUsage(state, taskId, now = Date.now()) {
  const spentMinor = Object.values(state.payments)
    .filter((payment) => payment.taskId === taskId && payment.status !== "declined")
    .reduce((total, payment) => total + payment.amountMinor, 0);
  const reservedMinor = Object.values(state.consents)
    .filter((consent) => consent.taskId === taskId && !consent.usedByPaymentId &&
      !consent.revokedAt && consent.expiresAt > now)
    .reduce((total, consent) => total + consent.amountMinor, 0);
  return { spentMinor, reservedMinor, committedMinor: spentMinor + reservedMinor };
}

function assertTaskBudgetAvailable(state, task, quote, now = Date.now(), excludeConsentId) {
  if (!task?.budgetLimit || !Number.isSafeInteger(task.budgetLimit.amountMinor)) {
    fail("TASK_BUDGET_REQUIRED", "任务缺少有效的结构化支出限额。");
  }
  if (task.budgetLimit.currency !== quote.currency) {
    fail("TASK_BUDGET_CURRENCY_MISMATCH", "报价币种与任务限额不同；不会进行币种换算。");
  }
  const usage = taskBudgetUsage(state, task.id, now);
  const excludedReservation = excludeConsentId ? state.consents[excludeConsentId] : null;
  const reservedMinor = usage.reservedMinor - (excludedReservation &&
    !excludedReservation.usedByPaymentId && !excludedReservation.revokedAt &&
    excludedReservation.expiresAt > now ? excludedReservation.amountMinor : 0);
  if (usage.spentMinor + reservedMinor + quote.amountMinor > task.budgetLimit.amountMinor) {
    fail("TASK_BUDGET_EXCEEDED", "累计付款与有效授权预留将超过此任务的结构化限额。");
  }
}

export function createResourceChallenge(state, { ownerId, tenantId, taskId }, now = Date.now()) {
  const task = state.tasks[taskId];
  if (!task || task.ownerId !== ownerId || task.tenantId !== tenantId) {
    fail("TASK_NOT_FOUND", "付费资源 challenge 需要当前用户/租户所属任务。");
  }
  if (!task.suggestions.some((suggestion) => suggestion.type === "quote" && suggestion.quoteId === "travel-guide")) {
    fail("RESOURCE_NOT_IN_TASK", "任务中没有结构化的付费指南建议。");
  }
  const quote = quoteFor("travel-guide");
  assertTaskBudgetAvailable(state, task, quote, now);
  const challenge = {
    id: `rch-${randomUUID()}`,
    ownerId,
    tenantId: tenantId ?? task.tenantId ?? "tenant-demo",
    taskId,
    resourceId: "travel-guide",
    quoteId: quote.id,
    merchantId: quote.merchantId,
    items: clone(quote.items),
    amountMinor: quote.amountMinor,
    currency: quote.currency,
    quoteVersion: quote.quoteVersion,
    status: "open",
    createdAt: now,
    expiresAt: now + 15 * 60_000,
    consentRequestId: null,
    consentId: null,
    paymentId: null,
    deliveryId: null,
  };
  state.resourceChallenges[challenge.id] = challenge;
  event(state, "resource.challenge_issued", null, { taskId, resourceChallengeId: challenge.id });
  return clone(challenge);
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

export function createConsent(state, { ownerId, tenantId, taskId, quoteId }, now = Date.now()) {
  if (!ownerId || !taskId) fail("INVALID_SCOPE", "用户和任务标识不能为空。");
  const task = state.tasks[taskId];
  if (!task || task.ownerId !== ownerId || (tenantId && task.tenantId !== tenantId)) {
    fail("TASK_NOT_FOUND", "任务不存在或不属于此用户/租户。");
  }
  const quote = quoteFor(quoteId);
  assertTaskBudgetAvailable(state, task, quote, now);
  const consent = {
    id: `cns-${randomUUID()}`,
    ownerId,
    tenantId: tenantId ?? task.tenantId ?? "tenant-demo",
    taskId,
    quoteId: quote.id,
    merchantId: quote.merchantId,
    items: clone(quote.items),
    amountMinor: quote.amountMinor,
    currency: quote.currency,
    quoteVersion: quote.quoteVersion,
    budgetLimit: clone(task.budgetLimit),
    createdAt: now,
    expiresAt: now + 15 * 60_000,
    revokedAt: null,
    usedByPaymentId: null,
  };
  state.consents[consent.id] = consent;
  return clone(consent);
}

export function createTaskConsent(state, { ownerId, tenantId, taskId, quoteId, challengeId }, now = Date.now()) {
  const task = state.tasks[taskId];
  if (!task || task.ownerId !== ownerId || (tenantId && task.tenantId !== tenantId)) fail("TASK_NOT_FOUND", "任务不存在或不属于此用户/租户。");
  if (!task.suggestions.some((suggestion) => suggestion.type === "quote" && suggestion.quoteId === quoteId)) {
    fail("TERMS_CHANGED", "报价不在此任务的结构化建议中。");
  }
  const quote = quoteFor(quoteId);
  assertTaskBudgetAvailable(state, task, quote, now);
  let challenge = null;
  if (quoteId === "travel-guide") {
    challenge = state.resourceChallenges?.[challengeId];
    if (!challenge || challenge.ownerId !== ownerId || challenge.tenantId !== (tenantId ?? task.tenantId) ||
        challenge.taskId !== taskId || challenge.quoteId !== quoteId) {
      fail("RESOURCE_CHALLENGE_REQUIRED", "付费指南必须绑定此任务的有效 HTTP 402 challenge。");
    }
    if (challenge.status !== "open" || challenge.expiresAt <= now) {
      fail("RESOURCE_CHALLENGE_NOT_OPEN", "402 challenge 已处理或过期，请重新请求。");
    }
    if (
      challenge.merchantId !== quote.merchantId ||
      challenge.amountMinor !== quote.amountMinor ||
      challenge.currency !== quote.currency ||
      challenge.quoteVersion !== quote.quoteVersion ||
      JSON.stringify(challenge.items) !== JSON.stringify(quote.items)
    ) fail("TERMS_CHANGED", "付费资源 challenge 条款已改变，请重新请求。");
  } else if (challengeId) {
    fail("INVALID_RESOURCE_CHALLENGE", "普通报价不能绑定付费资源 challenge。");
  }
  const request = {
    id: `crq-${randomUUID()}`,
    ownerId,
    tenantId: tenantId ?? task.tenantId ?? "tenant-demo",
    taskId,
    quoteId,
    merchantId: quote.merchantId,
    items: clone(quote.items),
    amountMinor: quote.amountMinor,
    currency: quote.currency,
    quoteVersion: quote.quoteVersion,
    budgetLimit: clone(task.budgetLimit),
    resourceChallengeId: challenge?.id ?? null,
    status: "pending",
    createdAt: now,
    expiresAt: now + 15 * 60_000,
    consentId: null,
    paymentId: null,
  };
  state.consentRequests[request.id] = request;
  if (challenge) challenge.consentRequestId = request.id;
  event(state, "consent.requested", null, { taskId, consentRequestId: request.id });
  return clone(request);
}

export function approveConsentRequest(state, { ownerId, tenantId, requestId }, now = Date.now()) {
  const request = state.consentRequests[requestId];
  if (!request || request.ownerId !== ownerId || request.tenantId !== tenantId) {
    fail("CONSENT_REQUEST_NOT_FOUND", "授权请求不存在或不属于此用户/租户。");
  }
  if (request.status === "expired") fail("CONSENT_REQUEST_EXPIRED", "授权请求已过期。");
  if (request.status !== "pending") fail("CONSENT_REQUEST_NOT_PENDING", "授权请求已处理。");
  if (request.expiresAt <= now) {
    fail("CONSENT_REQUEST_EXPIRED", "授权请求已过期。");
  }
  const quote = quoteFor(request.quoteId);
  const task = state.tasks[request.taskId];
  if (!task || task.ownerId !== ownerId || task.tenantId !== tenantId) {
    fail("TASK_NOT_FOUND", "授权任务不存在或不属于此用户/租户。");
  }
  assertTaskBudgetAvailable(state, task, quote, now);
  if (
    request.merchantId !== quote.merchantId ||
    request.amountMinor !== quote.amountMinor ||
    request.currency !== quote.currency ||
    request.quoteVersion !== quote.quoteVersion ||
    JSON.stringify(request.items) !== JSON.stringify(quote.items)
  ) {
    request.status = "changed";
    fail("TERMS_CHANGED", "报价条款已改变，需要重新请求用户批准。");
  }
  let resourceChallenge = null;
  if (request.resourceChallengeId) {
    resourceChallenge = state.resourceChallenges[request.resourceChallengeId];
    if (!resourceChallenge || resourceChallenge.consentRequestId !== request.id ||
        resourceChallenge.status !== "open" || resourceChallenge.expiresAt <= now) {
      fail("RESOURCE_CHALLENGE_NOT_OPEN", "绑定的 402 challenge 已处理或过期，请重新发起资源请求。");
    }
  } else if (request.quoteId === "travel-guide") {
    fail("RESOURCE_CHALLENGE_REQUIRED", "付费指南必须经匹配的 HTTP 402 challenge 批准。");
  }
  const consent = createConsent(state, {
    ownerId, tenantId, taskId: request.taskId, quoteId: request.quoteId,
  }, now);
  request.status = "approved";
  request.consentId = consent.id;
  request.approvedAt = now;
  if (resourceChallenge) {
    resourceChallenge.status = "approved";
    resourceChallenge.consentId = consent.id;
    resourceChallenge.approvedAt = now;
  }
  event(state, "consent.approved", null, { taskId: request.taskId, consentRequestId: request.id });
  return { request: clone(request), consent, payment: null, delivery: null };
}

export function denyConsentRequest(state, { ownerId, tenantId, requestId }, now = Date.now()) {
  const request = state.consentRequests[requestId];
  if (!request || request.ownerId !== ownerId || request.tenantId !== tenantId) {
    fail("CONSENT_REQUEST_NOT_FOUND", "授权请求不存在或不属于此用户/租户。");
  }
  if (request.status !== "pending") fail("CONSENT_REQUEST_NOT_PENDING", "授权请求已处理。");
  request.status = "rejected";
  request.resolvedAt = now;
  if (request.resourceChallengeId && state.resourceChallenges[request.resourceChallengeId]) {
    state.resourceChallenges[request.resourceChallengeId].status = "rejected";
    state.resourceChallenges[request.resourceChallengeId].resolvedAt = now;
  }
  event(state, "consent.rejected", null, { taskId: request.taskId, consentRequestId: request.id });
  return clone(request);
}

export function executeConsent(state, { ownerId, tenantId, consentId, idempotencyKey, outcome, challengeId }, now = Date.now()) {
  const consent = state.consents[consentId];
  if (!consent || consent.ownerId !== ownerId || consent.tenantId !== tenantId) {
    fail("CONSENT_NOT_FOUND", "授权不存在或不属于此用户/租户。");
  }
  const request = Object.values(state.consentRequests).find((item) => item.consentId === consent.id);
  if (consent.quoteId === "travel-guide" &&
      (!request?.resourceChallengeId || request.resourceChallengeId !== challengeId)) {
    fail("RESOURCE_CHALLENGE_REQUIRED", "付费指南只能通过已批准的匹配 challenge retry 完成。");
  }
  const payment = createPayment(state, {
    ownerId, tenantId, taskId: consent.taskId, consentId, idempotencyKey, outcome,
    resourceChallengeId: challengeId,
  }, now);
  const delivery = null;
  if (request) request.paymentId = payment.id;
  return { consent: clone(consent), payment, delivery };
}

export function revokeConsent(state, { ownerId, tenantId, consentId }, now = Date.now()) {
  const consent = state.consents[consentId];
  if (!consent || consent.ownerId !== ownerId || (tenantId && consent.tenantId !== tenantId)) fail("CONSENT_NOT_FOUND", "找不到此用户/租户的授权。");
  if (!consent.revokedAt && !consent.usedByPaymentId) {
    consent.revokedAt = now;
  }
  return clone(consent);
}

function validateConsent(state, input, now) {
  const consent = state.consents[input.consentId];
  if (!consent || consent.ownerId !== input.ownerId) fail("CONSENT_NOT_FOUND", "授权不存在或不属于此用户。");
  if (input.tenantId && consent.tenantId !== input.tenantId) fail("CONSENT_NOT_FOUND", "授权不存在或不属于此用户/租户。");
  if (consent.revokedAt) fail("CONSENT_REVOKED", "授权已撤销。");
  if (consent.expiresAt <= now) fail("CONSENT_EXPIRED", "授权已过期。");
  if (consent.usedByPaymentId) fail("CONSENT_USED", "此授权已用于付款。");
  const task = state.tasks[consent.taskId];
  if (!task || task.ownerId !== consent.ownerId || task.tenantId !== consent.tenantId) {
    fail("TASK_NOT_FOUND", "授权对应任务不存在或不属于此用户/租户。");
  }
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
  assertTaskBudgetAvailable(state, task, quote, now, consent.id);
  return { consent, quote };
}

export function createPayment(state, input, now = Date.now()) {
  if (!input.idempotencyKey || typeof input.idempotencyKey !== "string") {
    fail("IDEMPOTENCY_REQUIRED", "付款需要幂等键。");
  }
  const fingerprint = JSON.stringify({
    ownerId: input.ownerId,
    tenantId: input.tenantId,
    taskId: input.taskId,
    consentId: input.consentId,
    outcome: input.outcome ?? "captured",
    resourceChallengeId: input.resourceChallengeId,
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
  if (quote.id === "travel-guide") {
    const consentRequest = Object.values(state.consentRequests).find((item) => item.consentId === consent.id);
    const challenge = consentRequest?.resourceChallengeId &&
      state.resourceChallenges[consentRequest.resourceChallengeId];
    if (!challenge || challenge.id !== input.resourceChallengeId || challenge.status !== "approved" ||
        challenge.expiresAt <= now) {
      fail("RESOURCE_CHALLENGE_REQUIRED", "付费指南付款需要有效、已批准的绑定 HTTP 402 challenge。");
    }
  }
  const balances = balancesFor(state, consent.tenantId ?? input.tenantId);
  if (!Object.hasOwn(balances, quote.currency)) fail("CURRENCY_UNSUPPORTED", "币种不受支持。");
  if (balances[quote.currency] < quote.amountMinor) fail("BUDGET_EXCEEDED", "该币种的可用预算不足。");
  const outcome = input.outcome ?? "captured";
  if (!["captured", "unknown", "declined"].includes(outcome)) fail("INVALID_OUTCOME", "只允许指定模拟结果。");

  const payment = {
    id: `pay-${randomUUID()}`,
    consentId: consent.id,
    ownerId: consent.ownerId,
    tenantId: consent.tenantId ?? input.tenantId ?? "tenant-demo",
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
  if (outcome !== "declined") balances[quote.currency] -= quote.amountMinor;
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

export function fulfillPayment(state, { ownerId, tenantId, paymentId }) {
  const payment = state.payments[paymentId];
  if (!payment || payment.ownerId !== ownerId || (tenantId && payment.tenantId !== tenantId)) fail("PAYMENT_NOT_FOUND", "付款不存在或不属于此用户/租户。");
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

export function recordFulfillmentFailure(state, { ownerId, tenantId, paymentId, reason = "simulated_failure" }) {
  const payment = state.payments[paymentId];
  if (!payment || payment.ownerId !== ownerId || (tenantId && payment.tenantId !== tenantId)) fail("PAYMENT_NOT_FOUND", "付款不存在或不属于此用户/租户。");
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

export function resolveFulfillment(state, { ownerId, tenantId, paymentId, action }) {
  const payment = state.payments[paymentId];
  if (!payment || payment.ownerId !== ownerId || (tenantId && payment.tenantId !== tenantId)) fail("PAYMENT_NOT_FOUND", "付款不存在或不属于此用户/租户。");
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
      tenantId,
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

export function deliverPaidResource(state, { ownerId, tenantId, paymentId }) {
  const payment = state.payments[paymentId];
  if (!payment || payment.ownerId !== ownerId || (tenantId && payment.tenantId !== tenantId)) fail("PAYMENT_NOT_FOUND", "付款不存在或不属于此用户/租户。");
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

export function refundPayment(state, { ownerId, tenantId, paymentId, amountMinor, idempotencyKey }) {
  const payment = state.payments[paymentId];
  if (!payment || payment.ownerId !== ownerId || (tenantId && payment.tenantId !== tenantId)) fail("PAYMENT_NOT_FOUND", "付款不存在或不属于此用户/租户。");
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
  balancesFor(state, payment.tenantId)[payment.currency] += amountMinor;
  state.idempotency[idempotencyKey] = { fingerprint, paymentId };
  event(state, "payment.refunded", payment.id, { amountMinor, idempotencyKey });
  return clone(payment);
}

export function requestRefund(state, { ownerId, tenantId, paymentId, amountMinor, idempotencyKey }, now = Date.now()) {
  const payment = state.payments[paymentId];
  if (!payment || payment.ownerId !== ownerId || (tenantId && payment.tenantId !== tenantId)) {
    fail("PAYMENT_NOT_FOUND", "付款不存在或不属于此用户/租户。");
  }
  if (!["captured", "partially_refunded"].includes(payment.status)) fail("PAYMENT_NOT_REFUNDABLE", "只有已确认扣款的交易可申请退款。");
  if (!Number.isSafeInteger(amountMinor) || amountMinor <= 0 || payment.refundedMinor + amountMinor > payment.amountMinor) {
    fail("REFUND_LIMIT", "退款申请必须为正整数且不得超过未退还的捕获金额。");
  }
  if (!idempotencyKey || typeof idempotencyKey !== "string") fail("IDEMPOTENCY_REQUIRED", "退款申请需要幂等键。");
  const key = `refund-request:${tenantId}:${ownerId}:${idempotencyKey}`;
  const fingerprint = JSON.stringify({ ownerId, tenantId, paymentId, amountMinor });
  const previous = state.idempotency[key];
  if (previous) {
    if (previous.fingerprint !== fingerprint) fail("IDEMPOTENCY_CONFLICT", "退款申请幂等键已用于不同请求。");
    return clone(state.refundRequests[previous.requestId]);
  }
  const request = {
    id: `rfdreq-${randomUUID()}`,
    ownerId,
    tenantId,
    paymentId,
    amountMinor,
    currency: payment.currency,
    status: "pending",
    createdAt: now,
    resolvedAt: null,
  };
  state.refundRequests[request.id] = request;
  state.idempotency[key] = { fingerprint, requestId: request.id };
  event(state, "refund.requested", payment.id, { refundRequestId: request.id, amountMinor });
  return clone(request);
}

export function approveRefundRequest(state, { ownerId, tenantId, requestId }, now = Date.now()) {
  const request = state.refundRequests[requestId];
  if (!request || request.ownerId !== ownerId || request.tenantId !== tenantId) {
    fail("REFUND_REQUEST_NOT_FOUND", "退款申请不存在或不属于此用户/租户。");
  }
  if (request.status !== "pending") fail("REFUND_REQUEST_NOT_PENDING", "退款申请已处理。");
  const payment = refundPayment(state, {
    ownerId,
    tenantId,
    paymentId: request.paymentId,
    amountMinor: request.amountMinor,
    idempotencyKey: `approved-refund-request-${request.id}`,
  });
  request.status = "approved";
  request.resolvedAt = now;
  event(state, "refund.approved", payment.id, { refundRequestId: request.id });
  return { request: clone(request), payment };
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
    balancesFor(state, payment.tenantId)[payment.currency] += payment.reservedMinor;
    payment.reservedMinor = 0;
  }
  if (status === "captured") markCaptured(state, payment);
  payment.status = status;
  event(state, `payment.event_${status}`, payment.id, { externalEventId: eventId });
  return clone(payment);
}

export function snapshot(state, identity) {
  const visible = (record) => record.ownerId === identity.subject && record.tenantId === identity.tenantId;
  const tasks = Object.values(state.tasks).filter(visible);
  const taskIds = new Set(tasks.map((task) => task.id));
  const payments = Object.values(state.payments).filter(visible);
  const paymentIds = new Set(payments.map((payment) => payment.id));
  const requestIds = new Set(Object.values(state.consentRequests).filter(visible).map((request) => request.id));
  return {
    demoMode: "SIMULATED / OFFLINE",
    balances: clone(balancesFor(state, identity.tenantId)),
    catalog: clone(CATALOG),
    tenantId: identity.tenantId,
    subject: identity.subject,
    consents: Object.values(state.consents).filter(visible).map(clone),
    consentRequests: Object.values(state.consentRequests).filter(visible).map(clone),
    tasks: tasks.map((task) => {
      const budgetUsage = taskBudgetUsage(state, task.id);
      return {
        ...clone(task),
        budgetUsage: {
          ...budgetUsage,
          remainingMinor: Math.max(0, task.budgetLimit.amountMinor - budgetUsage.committedMinor),
        },
      };
    }),
    payments: payments.map(clone),
    refundRequests: Object.values(state.refundRequests).filter(visible).map(clone),
    resourceDeliveries: Object.values(state.resourceDeliveries).filter((delivery) => paymentIds.has(delivery.paymentId)).map(clone),
    resourceChallenges: Object.values(state.resourceChallenges ?? {}).filter(visible).map(clone),
    events: state.events.filter((entry) =>
      (entry.taskId && taskIds.has(entry.taskId)) ||
      (entry.paymentId && paymentIds.has(entry.paymentId)) ||
      (entry.consentRequestId && requestIds.has(entry.consentRequestId)),
    ).map(clone),
  };
}
