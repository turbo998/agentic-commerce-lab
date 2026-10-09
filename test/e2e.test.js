import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createAppServer } from "../src/server.js";
import { CATALOG } from "../src/catalog.js";

async function start(statePath, planner) {
  const server = createAppServer({ statePath, ...(planner ? { planner } : {}) });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  return {
    server,
    base,
    async get(path) {
      const response = await fetch(`${base}${path}`);
      return { status: response.status, body: await response.json() };
    },
    async post(path, body) {
      const response = await fetch(`${base}${path}`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
      });
      return { status: response.status, body: await response.json() };
    },
    close() { return new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve())); },
  };
}

async function taskAndConsent(app, ownerId, quoteId) {
  const journey = quoteId.startsWith("travel-") ? "travel" : "weekend";
  const taskResponse = await app.post("/api/tasks", {
    ownerId,
    journey,
    goal: `compare and request ${quoteId}`,
    quoteId,
  });
  assert.equal(taskResponse.status, 201);
  const task = taskResponse.body.result;
  const action = await app.post(`/api/tasks/${task.id}/actions`, {
    ownerId,
    action: { type: "request_quote", quoteId },
    idempotencyKey: `action-${ownerId}-${quoteId}`,
  });
  assert.equal(action.status, 200);
  assert.equal(action.body.result.replay, false);
  const consentResponse = await app.post("/api/consents", {
    ownerId,
    taskId: task.id,
    quoteId,
  });
  assert.equal(consentResponse.status, 200);
  return { task, consent: consentResponse.body.result };
}

test("HTTP demo enforces contention, idempotency and restart reconciliation", async () => {
  const directory = mkdtempSync(join(tmpdir(), "commerce-lab-"));
  const statePath = join(directory, "state.json");
  let app = await start(statePath);
  try {
    const page = await fetch(`${app.base}/`);
    assert.equal(page.status, 200);
    assert.match(await page.text(), /SIMULATED/);
    const reset = await app.post("/api/reset", {});
    assert.equal(reset.status, 200);
    const initial = JSON.parse(readFileSync(statePath, "utf8"));
    initial.balances.USD = 6000;
    writeFileSync(statePath, JSON.stringify(initial));
    await app.close();
    app = await start(statePath);
    const tightPrepared = await Promise.all(Array.from({ length: 20 }, (_, index) =>
      taskAndConsent(app, `contender-${index}`, "weekend-camera"),
    ));
    const outcomes = await Promise.all(tightPrepared.map((prepared, index) =>
      app.post("/api/payments", {
        ownerId: `contender-${index}`,
        taskId: tightPrepared[index].task.id,
        consentId: tightPrepared[index].consent.id,
        idempotencyKey: `contender-key-${index}`,
      }),
    ));
    assert.equal(outcomes.filter((result) => result.status === 200).length, 1);
    assert.equal(outcomes.filter((result) => result.body.error === "BUDGET_EXCEEDED").length, 19);

    const clean = await app.post("/api/reset", {});
    assert.equal(clean.body.payments.length, 0);
    assert.equal(clean.body.balances.USD, 30000);
    const fundedState = JSON.parse(readFileSync(statePath, "utf8"));
    fundedState.balances.USD = 200_000;
    writeFileSync(statePath, JSON.stringify(fundedState));
    await app.close();
    app = await start(statePath);
    const fundedPrepared = await Promise.all(Array.from({ length: 20 }, (_, index) =>
      taskAndConsent(app, `funded-${index}`, "weekend-camera"),
    ));
    const fundedInputs = fundedPrepared.map((prepared, index) => ({
      ownerId: `funded-${index}`,
      taskId: prepared.task.id,
      consentId: prepared.consent.id,
      idempotencyKey: `funded-key-${index}`,
    }));
    const fundedResults = await Promise.all(fundedInputs.map((input) => app.post("/api/payments", input)));
    assert.equal(fundedResults.filter((result) => result.status === 200).length, 20);
    const beforeDuplicatePayments = await app.get("/api/state");
    const firstFundedPayment = fundedResults[0].body.result;
    const firstFundedInput = fundedInputs[0];
    for (let index = 0; index < 10; index++) {
      const replay = await app.post("/api/payments", firstFundedInput);
      assert.equal(replay.body.result.id, firstFundedPayment.id);
    }
    const afterDuplicatePayments = await app.get("/api/state");
    assert.equal(afterDuplicatePayments.body.events.length, beforeDuplicatePayments.body.events.length);
    assert.equal(afterDuplicatePayments.body.balances.USD, beforeDuplicatePayments.body.balances.USD);
    await app.close();
    app = await start(statePath);
    const restartReplay = await app.post("/api/payments", firstFundedInput);
    assert.equal(restartReplay.body.result.id, firstFundedPayment.id);
    assert.equal(restartReplay.body.state.events.length, afterDuplicatePayments.body.events.length);

    await app.post("/api/reset", {});
    const eventPrepared = await taskAndConsent(app, "event-user", "weekend-camera");
    const eventPayment = (await app.post("/api/payments", {
      ownerId: "event-user",
      taskId: eventPrepared.task.id,
      consentId: eventPrepared.consent.id,
      idempotencyKey: "event-payment",
      outcome: "unknown",
    })).body.result;
    const authorizationEvent = {
      paymentId: eventPayment.id,
      eventId: "synthetic-auth-event",
      status: "authorized",
    };
    await app.post("/api/payments/events", authorizationEvent);
    const afterAuthorization = await app.get("/api/state");
    for (let index = 0; index < 10; index++) {
      await app.post("/api/payments/events", authorizationEvent);
    }
    const captureEvent = {
      paymentId: eventPayment.id,
      eventId: "synthetic-capture-event",
      status: "captured",
    };
    await app.post("/api/payments/events", captureEvent);
    const afterCapture = await app.get("/api/state");
    for (let index = 0; index < 10; index++) {
      await app.post("/api/payments/events", captureEvent);
    }
    assert.equal((await app.get("/api/state")).body.events.length, afterCapture.body.events.length);
    await app.close();
    app = await start(statePath);
    for (let index = 0; index < 10; index++) {
      await app.post("/api/payments/events", captureEvent);
    }
    assert.equal((await app.get("/api/state")).body.events.length, afterCapture.body.events.length);
    assert.equal(afterAuthorization.body.payments[0].status, "authorized");
    assert.equal(afterCapture.body.payments[0].status, "captured");

    await app.post("/api/reset", {});
    const { task: unknownTask, consent } = await taskAndConsent(app, "restart-user", "travel-hotel");
    const unknown = (await app.post("/api/payments", {
      ownerId: "restart-user", taskId: unknownTask.id, consentId: consent.id,
      idempotencyKey: "restart-unknown", outcome: "unknown",
    })).body.result;
    assert.equal(unknown.status, "unknown");
    const beforeRetry = await app.get("/api/state");
    const unknownInput = {
      ownerId: "restart-user", taskId: unknownTask.id, consentId: consent.id,
      idempotencyKey: "restart-unknown", outcome: "unknown",
    };
    for (let index = 0; index < 10; index++) {
      const duplicate = await app.post("/api/payments", unknownInput);
      assert.equal(duplicate.body.result.id, unknown.id);
      assert.equal(duplicate.body.state.events.length, beforeRetry.body.events.length);
    }
    await app.close();

    app = await start(statePath);
    for (let index = 0; index < 30; index++) {
      assert.equal((await app.post("/api/payments/reconcile", { paymentId: unknown.id })).status, 200);
    }
    const final = await app.get("/api/state");
    const reconciled = final.body.payments.find((payment) => payment.id === unknown.id);
    assert.equal(reconciled.status, "captured");
    assert.equal(reconciled.reconciliationCount, 1);
    assert.equal(reconciled.receipt.simulated, true);
    assert.equal(reconciled.fulfillmentStatus, "pending");
    assert.equal(final.body.events.filter((event) => event.type === "payment.reconciled_captured").length, 1);
    const fulfilled = await app.post("/api/payments/fulfill", { ownerId: "restart-user", paymentId: unknown.id });
    assert.equal(fulfilled.body.result.fulfillmentStatus, "fulfilled");
    const afterFulfill = fulfilled.body.state.events.length;
    await app.post("/api/payments/fulfill", { ownerId: "restart-user", paymentId: unknown.id });
    assert.equal((await app.get("/api/state")).body.events.length, afterFulfill);
    assert.equal(final.body.demoMode, "SIMULATED / OFFLINE");
    assert.equal((await app.post("/api/payments", {})).status, 400);
    assert.equal((await app.post("/api/no-such-api", {})).status, 404);
    const crossOrigin = await fetch(`${app.base}/api/reset`, {
      method: "POST",
      headers: { "content-type": "application/json", origin: "https://attacker.example" },
      body: "{}",
    });

    test("task proposal/action boundary accepts injected mock planner but never model approval", async () => {
      const directory = mkdtempSync(join(tmpdir(), "commerce-planner-"));
      const statePath = join(directory, "state.json");
      let plannerCalls = 0;
      const planner = {
        kind: "mock-contract",
        async propose({ quoteId }) {
          plannerCalls++;
          const quote = CATALOG[quoteId];
          return {
            summary: "Mock proposal only.",
            suggestions: [{
              type: "quote", quoteId, merchantId: quote.merchantId,
              amountMinor: quote.amountMinor, currency: quote.currency,
              quoteVersion: quote.quoteVersion, action: "request_quote",
            }],
          };
        },
      };
      let app;
      try {
        app = await start(statePath, planner);
        const taskResult = await app.post("/api/tasks", {
          ownerId: "agent-user", journey: "weekend", goal: "compare camera", quoteId: "weekend-camera",
        });
        assert.equal(taskResult.status, 201);
        assert.equal(taskResult.body.result.planner, "injected-test-client");
        assert.equal(plannerCalls, 1);
        const task = taskResult.body.result;
        const rejectedPayment = await app.post(`/api/tasks/${task.id}/actions`, {
          ownerId: "agent-user",
          action: { type: "pay", quoteId: "weekend-camera" },
          idempotencyKey: "agent-pay-attempt",
        });
        assert.equal(rejectedPayment.body.error, "ACTION_NOT_ALLOWED");
        const stateAfterReject = await app.get("/api/state");
        assert.equal(stateAfterReject.body.payments.length, 0);
        assert.equal(stateAfterReject.body.balances.USD, 30000);
        assert.equal((await app.get(`/api/tasks/${task.id}?ownerId=other`)).status, 404);
        const quoteAction = {
          ownerId: "agent-user",
          action: { type: "request_quote", quoteId: "weekend-camera" },
          idempotencyKey: "agent-quote-once",
        };
        const firstAction = await app.post(`/api/tasks/${task.id}/actions`, quoteAction);
        assert.equal(firstAction.body.result.replay, false);
        const actionEvents = firstAction.body.state.events.length;
        for (let index = 0; index < 10; index++) {
          const replay = await app.post(`/api/tasks/${task.id}/actions`, quoteAction);
          assert.equal(replay.body.result.replay, true);
          assert.equal(replay.body.state.events.length, actionEvents);
        }
        await app.close();
        app = await start(statePath, planner);
        const actionAfterRestart = await app.post(`/api/tasks/${task.id}/actions`, quoteAction);
        assert.equal(actionAfterRestart.body.result.replay, true);
        assert.equal(actionAfterRestart.body.state.events.length, actionEvents);
        const badPlanner = {
          kind: "mock-contract",
          async propose() {
            return { summary: "bad", suggestions: [{ type: "payment", action: "approve_and_pay" }] };
          },
        };
        await app.close();
        app = await start(join(directory, "unsafe.json"), badPlanner);
        const unsafeOutput = await app.post("/api/tasks", {
          ownerId: "agent-user", journey: "weekend", goal: "buy camera",
        });
        assert.equal(unsafeOutput.status, 400);
        assert.equal(unsafeOutput.body.error, "PLANNER_OUTPUT_INVALID");
        assert.equal((await app.get("/api/state")).body.payments.length, 0);
      } finally {
        if (app) await app.close();
        rmSync(directory, { recursive: true, force: true });
      }
    });
    assert.equal(crossOrigin.status, 403);
    const formRequest = await fetch(`${app.base}/api/reset`, {
      method: "POST",
      headers: { "content-type": "text/plain" },
      body: "{}",
    });
    assert.equal(formRequest.status, 415);
    assert.equal((await app.post("/api/reset", null)).body.error, "INVALID_BODY");

    await app.post("/api/reset", {});
    const fulfillmentOrder = await taskAndConsent(app, "fulfillment-user", "weekend-camera");
    const captured = await app.post("/api/payments", {
      ownerId: "fulfillment-user",
      taskId: fulfillmentOrder.task.id,
      consentId: fulfillmentOrder.consent.id,
      idempotencyKey: "fulfillment-capture",
    });
    const failedFulfillment = await app.post("/api/payments/fulfillment/fail", {
      ownerId: "fulfillment-user",
      paymentId: captured.body.result.id,
      reason: "simulated_failure",
    });
    assert.equal(failedFulfillment.body.result.fulfillmentStatus, "manual_review");
    assert.equal(failedFulfillment.body.result.status, "captured");
    await app.close();
    app = await start(statePath);
    const restoredFailure = (await app.get("/api/state")).body.payments[0];
    assert.equal(restoredFailure.fulfillmentStatus, "manual_review");
    assert.equal(restoredFailure.fulfillmentFailure.reason, "simulated_failure");
    const retryDecision = await app.post("/api/payments/fulfillment/resolve", {
      ownerId: "fulfillment-user",
      paymentId: restoredFailure.id,
      action: "retry",
    });
    assert.equal(retryDecision.body.result.fulfillmentStatus, "retrying");
    const retrySuccess = await app.post("/api/payments/fulfill", {
      ownerId: "fulfillment-user",
      paymentId: restoredFailure.id,
    });
    assert.equal(retrySuccess.body.result.fulfillmentStatus, "fulfilled");
    await app.close();
    app = await start(statePath);
    const restoredSuccess = (await app.get("/api/state")).body.payments.find((payment) => payment.id === restoredFailure.id);
    assert.equal(restoredSuccess.fulfillmentStatus, "fulfilled");
    const afterFulfillment = (await app.get("/api/state")).body.events.length;
    for (let index = 0; index < 10; index++) {
      await app.post("/api/payments/fulfill", {
        ownerId: "fulfillment-user",
        paymentId: restoredFailure.id,
      });
    }
    assert.equal((await app.get("/api/state")).body.events.length, afterFulfillment);

    const compensationOrder = await taskAndConsent(app, "compensation-user", "weekend-camera");
    const compensationPayment = await app.post("/api/payments", {
      ownerId: "compensation-user",
      taskId: compensationOrder.task.id,
      consentId: compensationOrder.consent.id,
      idempotencyKey: "compensation-capture",
    });
    await app.post("/api/payments/fulfillment/fail", {
      ownerId: "compensation-user",
      paymentId: compensationPayment.body.result.id,
      reason: "merchant_unavailable",
    });
    const compensation = await app.post("/api/payments/fulfillment/resolve", {
      ownerId: "compensation-user",
      paymentId: compensationPayment.body.result.id,
      action: "refund",
    });
    assert.equal(compensation.body.result.status, "refunded");
    assert.equal(compensation.body.result.fulfillmentStatus, "compensated");

    await app.post("/api/reset", {});
    const challenge = await app.post("/api/resources/travel-guide", {});
    assert.equal(challenge.status, 402);
    assert.equal(challenge.body.challenge.amountMinor, 1_200_000);
    assert.match(challenge.body.protocol, /not full MPP\/x402 conformance/);
    const paidPrepared = await taskAndConsent(app, "resource-user", "travel-guide");
    const resourceInput = {
      ownerId: "resource-user",
      taskId: paidPrepared.task.id,
      consentId: paidPrepared.consent.id,
      idempotencyKey: "resource-paid-once",
    };
    const delivered = await app.post("/api/resources/travel-guide", resourceInput);
    assert.equal(delivered.status, 200);
    assert.equal(delivered.body.result.delivery.simulated, true);
    assert.equal(delivered.body.result.payment.receipt.simulated, true);
    const deliveredEvents = delivered.body.state.events.length;
    for (let index = 0; index < 10; index++) {
      const replay = await app.post("/api/resources/travel-guide", resourceInput);
      assert.equal(replay.body.result.delivery.id, delivered.body.result.delivery.id);
      assert.equal(replay.body.state.events.length, deliveredEvents);
    }
    await app.close();
    app = await start(statePath);
    const restartDelivery = await app.post("/api/resources/travel-guide", resourceInput);
    assert.equal(restartDelivery.body.result.delivery.id, delivered.body.result.delivery.id);
    assert.equal(restartDelivery.body.state.resourceDeliveries.length, 1);
    const paymentId = restartDelivery.body.result.payment.id;
    const refundInput = {
      ownerId: "resource-user",
      paymentId,
      amountMinor: 1_200_000,
      idempotencyKey: "resource-refund-once",
    };
    const refund = await app.post("/api/payments/refund", refundInput);
    const refundEvents = refund.body.state.events.length;
    const afterRefundBalance = refund.body.state.balances.USDC;
    for (let index = 0; index < 10; index++) {
      await app.post("/api/payments/refund", refundInput);
    }
    const refundState = await app.get("/api/state");
    assert.equal(refundState.body.events.length, refundEvents);
    assert.equal(refundState.body.balances.USDC, afterRefundBalance);
  } finally {
    await app.close();
    rmSync(directory, { recursive: true, force: true });
  }
});
