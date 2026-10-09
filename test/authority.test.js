import test from "node:test";
import assert from "node:assert/strict";
import {
  AuthorityError,
  applyPaymentEvent,
  createConsent,
  createPayment,
  fulfillPayment,
  initialState,
  reconcilePayment,
  refundPayment,
  revokeConsent,
} from "../src/authority.js";

const quoteId = "weekend-camera";
const request = (consent, overrides = {}) => ({
  ownerId: consent.ownerId,
  taskId: consent.taskId,
  consentId: consent.id,
  idempotencyKey: `idem-${consent.id}`,
  ...overrides,
});
const expectCode = (code, fn) => assert.throws(fn, (error) => error instanceof AuthorityError && error.code === code);

test("only one of twenty reservations wins when the remaining budget fits one quote", () => {
  const state = initialState();
  state.balances.USD = 6000;
  const consents = Array.from({ length: 20 }, (_, index) =>
    createConsent(state, { ownerId: `owner-${index}`, taskId: "weekend", quoteId }),
  );
  const results = consents.map((consent) => {
    try { return createPayment(state, request(consent)); }
    catch (error) { assert.equal(error.code, "BUDGET_EXCEEDED"); return null; }
  });
  assert.equal(results.filter(Boolean).length, 1);
  assert.equal(state.balances.USD, 1);
  assert.equal(Object.keys(state.payments).length, 1);
});

test("all twenty authorized reservations succeed when budget is sufficient", () => {
  const state = initialState();
  state.balances.USD = 200_000;
  const consents = Array.from({ length: 20 }, (_, index) =>
    createConsent(state, { ownerId: `owner-${index}`, taskId: "weekend", quoteId }),
  );
  for (const consent of consents) createPayment(state, request(consent));
  assert.equal(Object.keys(state.payments).length, 20);
  assert.equal(state.balances.USD, 200_000 - 20 * 5999);
});

test("request replay returns one payment and never repeats the balance or event effect", () => {
  const state = initialState();
  const consent = createConsent(state, { ownerId: "u1", taskId: "trip", quoteId });
  const input = request(consent, { idempotencyKey: "same-key" });
  const first = createPayment(state, input);
  const events = state.events.length;
  const retry = createPayment(state, input);
  assert.equal(retry.id, first.id);
  assert.equal(state.events.length, events);
  assert.equal(state.balances.USD, 30000 - 5999);
  expectCode("IDEMPOTENCY_CONFLICT", () => createPayment(state, { ...input, amountMinor: 1 }));
});

test("authorization is bound to its owner, task, merchant, amount, currency, items and quote version", () => {
  const changed = [
    { ownerId: "other" },
    { taskId: "other-task" },
    { merchantId: "other-merchant" },
    { amountMinor: 1 },
    { currency: "HKD" },
    { items: [] },
    { quoteVersion: "stale" },
  ];
  for (const override of changed) {
    const state = initialState();
    const consent = createConsent(state, { ownerId: "u1", taskId: "trip", quoteId });
    expectCode(override.ownerId ? "CONSENT_NOT_FOUND" : "TERMS_CHANGED", () =>
      createPayment(state, request(consent, override)),
    );
    assert.equal(Object.keys(state.payments).length, 0);
  }
});

test("revoked and expired authorizations cannot be exercised", () => {
  const revokedState = initialState();
  const revoked = createConsent(revokedState, { ownerId: "u1", taskId: "trip", quoteId }, 100);
  revokeConsent(revokedState, { ownerId: "u1", consentId: revoked.id }, 101);
  expectCode("CONSENT_REVOKED", () => createPayment(revokedState, request(revoked), 102));

  const expiredState = initialState();
  const expired = createConsent(expiredState, { ownerId: "u1", taskId: "trip", quoteId }, 100);
  expectCode("CONSENT_EXPIRED", () => createPayment(expiredState, request(expired), expired.expiresAt));
});

test("consent is single-use and independent currencies never cross-fund", () => {
  const state = initialState();
  state.balances.USD = 0;
  state.balances.HKD = 15000;
  const consent = createConsent(state, { ownerId: "u1", taskId: "travel", quoteId });
  expectCode("BUDGET_EXCEEDED", () => createPayment(state, request(consent)));
  assert.equal(state.balances.HKD, 15000);
  state.balances.USD = 6000;
  createPayment(state, request(consent));
  expectCode("CONSENT_USED", () => createPayment(state, { ...request(consent), idempotencyKey: "second-key" }));
});

test("thirty reconciliations of an unchanged unknown payment append one event only", () => {
  const state = initialState();
  const consent = createConsent(state, { ownerId: "u1", taskId: "trip", quoteId });
  const payment = createPayment(state, request(consent, { outcome: "unknown" }));
  for (let index = 0; index < 30; index++) reconcilePayment(state, { paymentId: payment.id }, 1000 + index);
  assert.equal(state.payments[payment.id].status, "captured");
  assert.equal(state.payments[payment.id].reconciliationCount, 1);
  assert.equal(state.events.filter((entry) => entry.type === "payment.reconciled_captured").length, 1);
});

test("out-of-order or duplicate events cannot regress a terminal payment state", () => {
  const state = initialState();
  const consent = createConsent(state, { ownerId: "u1", taskId: "trip", quoteId });
  const payment = createPayment(state, request(consent, { outcome: "unknown" }));
  applyPaymentEvent(state, { paymentId: payment.id, eventId: "network-1", status: "captured" });
  const eventCount = state.events.length;
  applyPaymentEvent(state, { paymentId: payment.id, eventId: "network-2", status: "authorized" });
  applyPaymentEvent(state, { paymentId: payment.id, eventId: "network-1", status: "declined" });
  assert.equal(state.payments[payment.id].status, "captured");
  assert.equal(state.events.length, eventCount);
});

test("capture issues a synthetic receipt; fulfillment is owner-bound and idempotent", () => {
  const state = initialState();
  const consent = createConsent(state, { ownerId: "u1", taskId: "trip", quoteId });
  const payment = createPayment(state, request(consent));
  assert.equal(payment.receipt.simulated, true);
  assert.equal(payment.receipt.amountMinor, payment.amountMinor);
  assert.equal(payment.fulfillmentStatus, "pending");
  expectCode("PAYMENT_NOT_FOUND", () => fulfillPayment(state, { ownerId: "other", paymentId: payment.id }));
  const fulfilled = fulfillPayment(state, { ownerId: "u1", paymentId: payment.id });
  const eventCount = state.events.length;
  assert.equal(fulfilled.fulfillmentStatus, "fulfilled");
  fulfillPayment(state, { ownerId: "u1", paymentId: payment.id });
  assert.equal(state.events.length, eventCount);

  const unknownConsent = createConsent(state, { ownerId: "u1", taskId: "trip", quoteId });
  const unknown = createPayment(state, request(unknownConsent, { outcome: "unknown" }));
  assert.equal(unknown.receipt, null);
  expectCode("PAYMENT_NOT_FULFILLABLE", () => fulfillPayment(state, { ownerId: "u1", paymentId: unknown.id }));
});

test("cumulative refunds cannot exceed capture and duplicate refund keys restore budget once", () => {
  const state = initialState();
  const consent = createConsent(state, { ownerId: "u1", taskId: "trip", quoteId });
  const payment = createPayment(state, request(consent));
  const refundInput = { ownerId: "u1", paymentId: payment.id, amountMinor: 1000, idempotencyKey: "refund-1" };
  const afterCapture = state.balances.USD;
  refundPayment(state, refundInput);
  refundPayment(state, refundInput);
  assert.equal(state.balances.USD, afterCapture + 1000);
  assert.equal(state.payments[payment.id].refundedMinor, 1000);
  expectCode("IDEMPOTENCY_CONFLICT", () => refundPayment(state, {
    ...refundInput, amountMinor: 2000,
  }));
  expectCode("REFUND_LIMIT", () => refundPayment(state, {
    ownerId: "u1", paymentId: payment.id, amountMinor: 5000, idempotencyKey: "refund-too-much",
  }));
  refundPayment(state, {
    ownerId: "u1", paymentId: payment.id, amountMinor: 4999, idempotencyKey: "refund-remainder",
  });
  assert.equal(state.payments[payment.id].status, "refunded");
  assert.equal(state.balances.USD, 30000);
});

test("twenty untrusted tool proposals create no payment, event, or budget effect", () => {
  const state = initialState();
  const balances = { ...state.balances };
  for (let index = 0; index < 20; index++) {
    expectCode("CONSENT_NOT_FOUND", () => createPayment(state, {
      ownerId: "u1",
      taskId: "untrusted-agent-proposal",
      consentId: `model-suggested-consent-${index}`,
      idempotencyKey: `tool-eval-${index}`,
    }));
  }
  assert.deepEqual(state.balances, balances);
  assert.equal(Object.keys(state.payments).length, 0);
  assert.equal(state.events.length, 0);
});
