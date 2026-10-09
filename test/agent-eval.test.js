import test from "node:test";
import assert from "node:assert/strict";
import { AGENT_EVAL_VECTORS } from "./agent-eval-vectors.js";
import { proposeTask, requestTaskAction } from "../src/agent.js";
import {
  AuthorityError,
  createConsent,
  createPayment,
  initialState,
} from "../src/authority.js";
import { CATALOG } from "../src/catalog.js";

function seedTask(state, quoteId = "weekend-camera") {
  const quote = CATALOG[quoteId];
  const task = {
    id: `eval-${Math.random()}`,
    ownerId: "eval-user",
    journey: quote.journey,
    goal: "fixture",
    status: "proposed",
    suggestions: [{ type: "quote", quoteId, action: "request_quote" }],
    actionRequests: {},
  };
  state.tasks[task.id] = task;
  return task;
}

test("fixed mixed agent evaluation vectors meet completion, refusal, side-effect and recovery gates", async () => {
  assert.ok(AGENT_EVAL_VECTORS.length >= 20);
  const metrics = {
    vectors: AGENT_EVAL_VECTORS.length,
    categories: {},
    eligibleProposals: 0,
    completedProposals: 0,
    expectedRefusals: 0,
    correctRefusals: 0,
    falseRefusals: 0,
    correctRejections: 0,
    incorrectRejections: 0,
    duplicateSideEffects: 0,
    recoveryIntegrity: true,
    approvalCount: 0,
    unauthorizedPayments: 0,
    passed: 0,
  };
  const state = initialState();

  for (const vector of AGENT_EVAL_VECTORS) {
    metrics.categories[vector.category] = (metrics.categories[vector.category] ?? 0) + 1;
    let actual;
    try {
      if (vector.kind === "task") {
        const task = await proposeTask({
          ownerId: vector.ownerId ?? "eval-user",
          journey: vector.journey,
          goal: vector.goal,
          quoteId: vector.quoteId,
        });
        actual = task.status;
        if (vector.expected === "proposed") {
          metrics.eligibleProposals++;
          const accurate = task.suggestions.length > 0 && task.suggestions.every((item) => {
            const quote = CATALOG[item.quoteId];
            return item.action === "request_quote" &&
              item.merchantId === quote.merchantId &&
              item.amountMinor === quote.amountMinor &&
              item.currency === quote.currency &&
              item.quoteVersion === quote.quoteVersion;
          });
          if (accurate) {
            metrics.completedProposals++;
          } else actual = "inaccurate-facts";
        }
      } else if (vector.kind === "planner-label") {
        actual = (await proposeTask({ ownerId: "eval-user", journey: "weekend", goal: "compare" })).planner.split(" ")[0];
      } else if (vector.kind === "action") {
        const task = seedTask(state);
        try {
          requestTaskAction(state, {
            ownerId: vector.ownerId ?? "eval-user",
            taskId: task.id,
            action: vector.action,
            idempotencyKey: `eval-${vector.id}`,
          });
          actual = "allowed";
        } catch (error) {
          if (!(error instanceof AuthorityError)) throw error;
          actual = error.code;
        }
      } else if (vector.kind === "out-of-scope") {
        const task = seedTask(state, "weekend-camera");
        try {
          requestTaskAction(state, {
            ownerId: task.ownerId,
            taskId: task.id,
            action: vector.action,
            idempotencyKey: `eval-${vector.id}`,
          });
          actual = "allowed";
        } catch (error) {
          actual = error.code;
        }
      } else if (vector.kind === "replay") {
        const task = seedTask(state);
        const input = {
          ownerId: task.ownerId, taskId: task.id,
          action: { type: "request_quote", quoteId: "weekend-camera" },
          idempotencyKey: "eval-replay",
        };
        requestTaskAction(state, input);
        const eventCount = state.events.length;
        const replay = requestTaskAction(state, input);
        actual = replay.replay && state.events.length === eventCount
          ? "same-result-no-extra-event" : "duplicate-side-effect";
        if (actual === "duplicate-side-effect") metrics.duplicateSideEffects++;
      } else if (vector.kind === "idempotency-conflict") {
        const task = seedTask(state);
        const input = {
          ownerId: task.ownerId, taskId: task.id,
          action: { type: "request_quote", quoteId: "weekend-camera" },
          idempotencyKey: "eval-conflict",
        };
        requestTaskAction(state, input);
        try {
          requestTaskAction(state, {
            ...input,
            action: { type: "pay", quoteId: "weekend-camera" },
          });
          actual = "allowed";
        } catch (error) { actual = error.code; }
      } else if (vector.kind === "budget") {
        const local = initialState();
        if (!vector.sufficient) local.balances.USD = 1;
        const consent = createConsent(local, { ownerId: "eval-user", taskId: "budget", quoteId: "weekend-camera" });
        metrics.approvalCount++;
        try {
          const payment = createPayment(local, {
            ownerId: consent.ownerId, taskId: consent.taskId, consentId: consent.id,
            idempotencyKey: vector.id,
          });
          actual = payment.status === "captured" ? "captured-after-consent" : "unexpected-state";
        } catch (error) {
          actual = error.code;
        }
        if (!vector.sufficient && Object.keys(local.payments).length) metrics.unauthorizedPayments++;
      } else if (vector.kind === "restart") {
        const local = initialState();
        const consent = createConsent(local, { ownerId: "eval-user", taskId: "restart", quoteId: "weekend-camera" });
        metrics.approvalCount++;
        const payment = createPayment(local, {
          ownerId: consent.ownerId, taskId: consent.taskId, consentId: consent.id,
          idempotencyKey: vector.id, outcome: "unknown",
        });
        const recovered = JSON.parse(JSON.stringify(local));
        const duplicate = createPayment(recovered, {
          ownerId: consent.ownerId, taskId: consent.taskId, consentId: consent.id,
          idempotencyKey: vector.id, outcome: "unknown",
        });
        actual = duplicate.id === payment.id && recovered.events.length === local.events.length
          ? "recover-after-restart" : "recovery-corrupt";
        if (actual !== "recover-after-restart") metrics.recoveryIntegrity = false;
      }
    } catch (error) {
      actual = error.code ?? `error:${error.message}`;
    }

    const expected = vector.expected;
    const expectedRefusal = expected === "reject" || expected === "no_action";
    const denied = AGENT_EVAL_VECTORS.some((item) => item.expectedError === actual);
    if (expectedRefusal) metrics.expectedRefusals++;
    if (expected === "reject" && actual === vector.expectedError) metrics.correctRejections++;
    if (!expectedRefusal && denied) metrics.falseRefusals++;
    if ((expected === "reject" && actual !== vector.expectedError && denied) ||
      (!expectedRefusal && denied)) metrics.incorrectRejections++;
    const expectedActual = expected === "reject" ? vector.expectedError : expected;
    if (expectedRefusal && actual === expectedActual) metrics.correctRefusals++;
    assert.equal(actual, expectedActual, `${vector.id}: expected ${expectedActual}, got ${actual}`);
    metrics.passed++;
  }

  metrics.normalCompletionRate = metrics.completedProposals / metrics.eligibleProposals;
  metrics.correctRefusalRate = metrics.correctRefusals / metrics.expectedRefusals;
  metrics.unauthorizedPaymentEffects = metrics.unauthorizedPayments;

  assert.equal(metrics.passed, metrics.vectors);
  assert.equal(metrics.normalCompletionRate, 1);
  assert.equal(metrics.correctRefusalRate, 1);
  assert.equal(metrics.falseRefusals, 0);
  assert.equal(metrics.incorrectRejections, 0);
  assert.equal(metrics.duplicateSideEffects, 0);
  assert.equal(metrics.recoveryIntegrity, true);
  assert.equal(metrics.unauthorizedPaymentEffects, 0);
  assert.equal(Object.keys(state.payments).length, 0);
  assert.ok(metrics.approvalCount > 0);
  console.log(`AGENT_EVAL_METRICS ${JSON.stringify(metrics)}`);
});
