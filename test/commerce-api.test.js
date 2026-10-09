import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createAppServer } from "../src/server.js";
import { CATALOG } from "../src/catalog.js";

async function start(statePath) {
  const server = createAppServer({ statePath });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  async function session(persona, human = false) {
    const response = await fetch(`${base}/api/demo/session`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ persona }),
    });
    const agent = await response.json();
    if (!human) return agent;
    const humanResponse = await fetch(`${base}/api/demo/human-session`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        origin: base,
        "sec-fetch-site": "same-origin",
      },
      body: JSON.stringify({ persona }),
    });
    return { ...agent, ...(await humanResponse.json()) };
  }
  const alex = await session("alex");
  const sam = await session("sam");
  const alexHuman = await session("alex", true);
  const samHuman = await session("sam", true);
  return {
    base,
    alex,
    sam,
    alexHuman,
    samHuman,
    async call(path, { method = "GET", body, role = "agent", principal = "alex", token } = {}) {
      const sessionIdentity = principal === "sam" ? this.sam : this.alex;
      const humanIdentity = principal === "sam" ? this.samHuman : this.alexHuman;
      const authToken = token ?? (role === "human" ? humanIdentity.humanToken : sessionIdentity.agentToken);
      const response = await fetch(`${base}${path}`, {
        method,
        headers: {
          ...(body === undefined ? {} : { "content-type": "application/json" }),
          ...(authToken ? { authorization: `Bearer ${authToken}` } : {}),
        },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      return { status: response.status, body: await response.json() };
    },
    close() { return new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve())); },
  };
}

async function createQuoteRequest(app, { journey, quoteId, goal, principal = "alex", budgetLimit }) {
  const quote = CATALOG[quoteId];
  const limit = budgetLimit ?? {
    currency: quote.currency,
    amountMinor: Math.max(quote.amountMinor * 4, quote.amountMinor),
  };
  const taskResult = await app.call("/api/commerce/v1/tasks", {
    method: "POST", principal, body: { journey, quoteId, goal, budgetLimit: limit },
  });
  assert.equal(taskResult.status, 201);
  const task = taskResult.body.result;
  const action = await app.call(`/api/commerce/v1/tasks/${task.id}/actions`, {
    method: "POST", principal,
    body: { action: { type: "request_quote", quoteId }, idempotencyKey: `action-${task.id}` },
  });
  assert.equal(action.status, 200);
  let challenge;
  if (quoteId === "travel-guide") {
    challenge = await app.call("/api/commerce/v1/resources/travel-guide", {
      method: "POST", principal, body: { taskId: task.id },
    });
    assert.equal(challenge.status, 402);
  }
  const request = await app.call("/api/commerce/v1/consent-requests", {
    method: "POST", principal,
    body: { taskId: task.id, quoteId, ...(challenge ? { challengeId: challenge.body.challenge.challengeId } : {}) },
  });
  assert.equal(request.status, 201);
  return { task, request: request.body.result, challenge: challenge?.body.challenge };
}

test("legacy state upgrades retain compensated payments and populate consent budget fields without reset", async () => {
  const directory = mkdtempSync(join(tmpdir(), "commerce-upgrade-"));
  const statePath = join(directory, "state.json");
  let app = await start(statePath);
  try {
    const { task, request } = await createQuoteRequest(app, {
      journey: "weekend", quoteId: "weekend-camera", goal: "upgrade fixture",
    });
    const approved = await app.call(`/api/commerce/v1/consent-requests/${request.id}/approve`, {
      method: "POST", body: {}, role: "human",
    });
    const captured = await app.call(`/api/commerce/v1/consents/${approved.body.result.consent.id}/execute`, {
      method: "POST", body: {},
    });
    const paymentId = captured.body.result.payment.id;
    await app.call("/api/payments/fulfillment/fail", {
      method: "POST", role: "human", body: { paymentId, reason: "simulated_failure" },
    });
    const compensated = await app.call("/api/payments/fulfillment/resolve", {
      method: "POST", role: "human", body: { paymentId, action: "refund" },
    });
    assert.equal(compensated.status, 200);
    const before = (await app.call("/api/state")).body;
    await app.close();
    app = null;
    const legacy = JSON.parse(readFileSync(statePath, "utf8"));
    delete legacy.tasks[task.id].budgetLimit;
    delete legacy.consentRequests[request.id].budgetLimit;
    for (const section of ["tasks", "consents", "consentRequests", "payments"]) {
      for (const record of Object.values(legacy[section])) {
        record.ownerId = "user-demo";
        delete record.tenantId;
      }
    }
    writeFileSync(statePath, JSON.stringify(legacy));
    app = await start(statePath);
    const after = (await app.call("/api/state")).body;
    assert.deepEqual(after.balances, before.balances);
    assert.deepEqual(after.events, before.events);
    assert.equal(after.payments[0].id, paymentId);
    assert.equal(after.payments[0].fulfillmentStatus, "compensated");
    assert.equal(after.payments[0].refundedMinor, 5999);
    assert.ok(after.consentRequests[0].budgetLimit.amountMinor > 0);
    assert.equal(after.consentRequests[0].budgetPolicySource, "legacy-migration-not-user-policy");
    assert.equal(after.tasks[0].budgetPolicySource, "legacy-migration-not-user-policy");
    assert.equal((await app.call("/api/reset", { method: "POST", role: "human", body: {} })).status, 200);
    assert.equal((await app.call("/api/state")).body.payments.length, 0);
  } finally {
    if (app) await app.close();
    rmSync(directory, { recursive: true, force: true });
  }
});

test("expired requests persist their terminal status once across refresh and restart", async () => {
  const directory = mkdtempSync(join(tmpdir(), "commerce-expiry-"));
  const statePath = join(directory, "state.json");
  let app = await start(statePath);
  try {
    const { request } = await createQuoteRequest(app, {
      journey: "weekend", quoteId: "weekend-coffee", goal: "expiry fixture",
    });
    await app.close();
    app = null;
    const state = JSON.parse(readFileSync(statePath, "utf8"));
    state.consentRequests[request.id].expiresAt = 1;
    writeFileSync(statePath, JSON.stringify(state));
    app = await start(statePath);
    const result = await app.call(`/api/commerce/v1/consent-requests/${request.id}`);
    assert.equal(result.body.status, "expired");
    const before = readFileSync(statePath, "utf8");
    for (let index = 0; index < 10; index++) {
      const refused = await app.call(`/api/commerce/v1/consent-requests/${request.id}/approve`, {
        method: "POST", role: "human", body: {},
      });
      assert.equal(refused.body.error, "CONSENT_REQUEST_EXPIRED");
    }
    assert.equal(readFileSync(statePath, "utf8"), before);
    await app.close();
    app = await start(statePath);
    assert.equal((await app.call(`/api/commerce/v1/consent-requests/${request.id}`)).body.status, "expired");
    assert.equal((await app.call("/api/state")).body.payments.length, 0);
  } finally {
    if (app) await app.close();
    rmSync(directory, { recursive: true, force: true });
  }
});

test("Commerce API binds identity server-side and separates agent tools from human approval", async () => {
  const directory = mkdtempSync(join(tmpdir(), "commerce-identity-"));
  const app = await start(join(directory, "state.json"));
  try {
    assert.equal((await app.call("/api/commerce/v1/status", { token: "" })).status, 401);
    assert.ok(app.alex.agentToken);
    assert.equal(Object.hasOwn(app.alex, "humanToken"), false);
    const blockedHumanSession = await fetch(`${app.base}/api/demo/human-session`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ persona: "alex" }),
    });
    assert.equal(blockedHumanSession.status, 403);
    const spoof = await app.call("/api/commerce/v1/tasks", {
      method: "POST", body: {
        ownerId: "sam", tenantId: "tenant-alt", journey: "weekend", quoteId: "weekend-camera", goal: "compare",
      },
    });
    assert.equal(spoof.status, 400);
    assert.equal(spoof.body.error, "CLIENT_IDENTITY_FORBIDDEN");

    const legacyTask = (await createQuoteRequest(app, {
      journey: "weekend", quoteId: "weekend-coffee", goal: "legacy boundary check",
    })).task;
    const legacyRequest = await app.call("/api/consents", {
      method: "POST", body: { taskId: legacyTask.id, quoteId: "weekend-coffee" },
    });
    assert.equal(legacyRequest.status, 200);
    assert.equal(legacyRequest.body.result.status, "pending");
    assert.equal(legacyRequest.body.result.consentId, null);
    const beforeBypass = (await app.call("/api/state")).body;
    const bypass = await app.call("/api/payments", {
      method: "POST",
      body: { taskId: legacyTask.id, consentId: legacyRequest.body.result.id, idempotencyKey: "unapproved-legacy" },
    });
    assert.equal(bypass.status, 404);
    assert.equal(bypass.body.error, "CONSENT_NOT_FOUND");
    assert.deepEqual((await app.call("/api/state")).body, beforeBypass);

    const { task, request } = await createQuoteRequest(app, {
      journey: "weekend", quoteId: "weekend-camera", goal: "compare a camera",
    });
    assert.equal((await app.call(`/api/commerce/v1/tasks/${task.id}`, { principal: "sam" })).status, 404);
    assert.equal((await app.call("/api/commerce/v1/status", { principal: "sam" })).body.tasks.length, 0);
    assert.equal((await app.call(`/api/commerce/v1/consent-requests/${request.id}/approve`, {
      method: "POST", body: {}, role: "agent",
    })).status, 403);
    assert.equal((await app.call(`/api/commerce/v1/consent-requests/${request.id}/approve`, {
      method: "POST", body: {}, principal: "sam", role: "human",
    })).status, 404);
    assert.equal((await app.call(`/api/commerce/v1/consent-requests/${request.id}/approve`, {
      method: "POST", body: {}, role: "human",
    })).status, 200);

    const status = (await app.call("/api/commerce/v1/status")).body;
    assert.equal(status.consentRequests.find((item) => item.id === request.id).status, "approved");
    assert.equal(status.payments.length, 0);
    const execute = await app.call(`/api/commerce/v1/consents/${request.id}/execute`, { method: "POST", body: {} });
    assert.equal(execute.status, 404);

    const approvedRequest = status.consentRequests.find((item) => item.id === request.id);
    const consentId = approvedRequest.consentId;
    const payment = await app.call(`/api/commerce/v1/consents/${consentId}/execute`, { method: "POST", body: {} });
    assert.equal(payment.status, 200);
    assert.equal(payment.body.result.payment.status, "captured");
    assert.equal(payment.body.result.payment.receipt.simulated, true);
    const beforeForeignEvent = (await app.call("/api/state")).body;
    const crossTenantEvent = await app.call("/api/payments/events", {
      method: "POST",
      principal: "sam",
      role: "human",
      body: { paymentId: payment.body.result.payment.id, eventId: "cross-tenant-event", status: "declined" },
    });
    assert.equal(crossTenantEvent.status, 404);
    assert.deepEqual((await app.call("/api/state")).body, beforeForeignEvent);

    const samTask = await app.call("/api/commerce/v1/tasks", {
      method: "POST", principal: "sam",
      body: {
        journey: "weekend", quoteId: "weekend-coffee", goal: "compare coffee",
        budgetLimit: { currency: "USD", amountMinor: 5000 },
      },
    });

    test("task budget caps cumulative capture and concurrent consent reservations", async () => {
      const directory = mkdtempSync(join(tmpdir(), "commerce-task-budget-"));
      const app = await start(join(directory, "state.json"));
      try {
        const taskResult = await app.call("/api/commerce/v1/tasks", {
          method: "POST",
          body: {
            journey: "weekend",
            goal: "camera and coffee; free text is not a policy",
            budgetLimit: { currency: "USD", amountMinor: 7000 },
          },
        });
        assert.equal(taskResult.status, 201);
        const task = taskResult.body.result;
        const pendingRequest = async (quoteId) => {
          const action = await app.call(`/api/commerce/v1/tasks/${task.id}/actions`, {
            method: "POST",
            body: { action: { type: "request_quote", quoteId }, idempotencyKey: `quote-${quoteId}` },
          });
          assert.equal(action.status, 200);
          const request = await app.call("/api/commerce/v1/consent-requests", {
            method: "POST", body: { taskId: task.id, quoteId },
          });
          assert.equal(request.status, 201);
          return request.body.result;
        };
        const camera = await pendingRequest("weekend-camera");
        const coffee = await pendingRequest("weekend-coffee");
        const cameraApproval = await app.call(`/api/commerce/v1/consent-requests/${camera.id}/approve`, {
          method: "POST", body: {}, role: "human",
        });
        assert.equal(cameraApproval.status, 200);
        const overReserved = await app.call(`/api/commerce/v1/consent-requests/${coffee.id}/approve`, {
          method: "POST", body: {}, role: "human",
        });
        assert.equal(overReserved.status, 400);
        assert.equal(overReserved.body.error, "TASK_BUDGET_EXCEEDED");
        const reserved = (await app.call("/api/commerce/v1/status")).body.tasks[0].budgetUsage;
        assert.equal(reserved.reservedMinor, 5999);
        assert.equal(reserved.remainingMinor, 1001);
        const cameraPayment = await app.call(`/api/commerce/v1/consents/${cameraApproval.body.result.consent.id}/execute`, {
          method: "POST", body: {},
        });
        assert.equal(cameraPayment.body.result.payment.status, "captured");
        const extraConsent = await app.call("/api/commerce/v1/consent-requests", {
          method: "POST", body: { taskId: task.id, quoteId: "weekend-coffee" },
        });
        assert.equal(extraConsent.status, 400);
        assert.equal(extraConsent.body.error, "TASK_BUDGET_EXCEEDED");
        const status = (await app.call("/api/commerce/v1/status")).body;
        assert.equal(status.tasks[0].budgetUsage.reservedMinor, 0);
        assert.equal(status.tasks[0].budgetUsage.remainingMinor, 1001);
        assert.equal(status.tasks[0].budgetUsage.spentMinor, 5999);
        assert.equal(status.balances.USD, 24001);
      } finally {
        await app.close();
        rmSync(directory, { recursive: true, force: true });
      }
    });
    assert.equal(samTask.status, 201);
    await app.call("/api/reset", { method: "POST", role: "human", body: {} });
    assert.equal((await app.call("/api/commerce/v1/status")).body.payments.length, 0);
    assert.equal((await app.call("/api/commerce/v1/status", { principal: "sam" })).body.tasks.length, 1);
  } finally {
    await app.close();
    rmSync(directory, { recursive: true, force: true });
  }
});

test("weekend purchase and paid travel information require consent and are replay-safe", async () => {
  const directory = mkdtempSync(join(tmpdir(), "commerce-journey-"));
  const app = await start(join(directory, "state.json"));
  try {
    const weekend = await createQuoteRequest(app, {
      journey: "weekend", quoteId: "weekend-coffee", goal: "buy coffee beans",
    });
    const approved = await app.call(`/api/commerce/v1/consent-requests/${weekend.request.id}/approve`, {
      method: "POST", body: {}, role: "human",
    });
    assert.equal(approved.body.result.consent.quoteId, "weekend-coffee");
    const executed = await app.call(`/api/commerce/v1/consents/${approved.body.result.consent.id}/execute`, {
      method: "POST", body: {},
    });
    assert.equal(executed.body.result.payment.receipt.simulated, true);
    const paymentId = executed.body.result.payment.id;
    const replay = await app.call(`/api/commerce/v1/consents/${approved.body.result.consent.id}/execute`, {
      method: "POST", body: {},
    });
    assert.equal(replay.body.result.payment.id, paymentId);

    const refund = await app.call("/api/commerce/v1/refund-requests", {
      method: "POST",
      body: { paymentId, amountMinor: 500, idempotencyKey: "coffee-refund" },
    });
    assert.equal(refund.status, 201);
    assert.equal(refund.body.result.status, "pending");
    assert.equal((await app.call(`/api/commerce/v1/refund-requests/${refund.body.result.id}/approve`, {
      method: "POST", body: {}, role: "agent",
    })).status, 403);
    const balanceAfterCapture = (await app.call("/api/commerce/v1/status")).body.balances.USD;
    const refunded = await app.call(`/api/commerce/v1/refund-requests/${refund.body.result.id}/approve`, {
      method: "POST", body: {}, role: "human",
    });
    assert.equal(refunded.body.result.payment.refundedMinor, 500);
    assert.equal((await app.call("/api/commerce/v1/status")).body.balances.USD, balanceAfterCapture + 500);

    const travel = await createQuoteRequest(app, {
      journey: "travel", quoteId: "travel-guide", goal: "get a paid local guide",
    });
    assert.ok(travel.challenge.challengeId);
    const travelApproval = await app.call(`/api/commerce/v1/consent-requests/${travel.request.id}/approve`, {
      method: "POST", body: {}, role: "human",
    });
    assert.equal(travelApproval.body.result.consent.currency, "USDC");
    const retry = await app.call("/api/commerce/v1/resources/travel-guide", {
      method: "POST",
      body: {
        taskId: travel.task.id,
        consentRequestId: travel.request.id,
        challengeId: travel.challenge.challengeId,
      },
    });
    assert.equal(retry.status, 200);
    assert.equal(retry.body.result.payment.receipt.simulated, true);
    assert.equal(retry.body.result.delivery.simulated, true);
    const eventCount = (await app.call("/api/commerce/v1/status")).body.events.length;
    for (let index = 0; index < 10; index++) {
      const retryAgain = await app.call("/api/commerce/v1/resources/travel-guide", {
        method: "POST",
        body: {
          taskId: travel.task.id,
          consentRequestId: travel.request.id,
          challengeId: travel.challenge.challengeId,
        },
      });
      assert.equal(retryAgain.status, 200);
      assert.equal(retryAgain.body.result.payment.id, retry.body.result.payment.id);
      assert.equal(retryAgain.body.result.delivery.id, retry.body.result.delivery.id);
    }
    assert.equal((await app.call("/api/commerce/v1/status")).body.events.length, eventCount);
  } finally {
    await app.close();
    rmSync(directory, { recursive: true, force: true });
  }
});
