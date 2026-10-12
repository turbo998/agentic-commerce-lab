import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createAppServer } from "../src/server.js";
import { CATALOG } from "../src/catalog.js";

async function start(statePath, planner) {
  const server = createAppServer({ statePath, ...(planner ? { planner } : {}) });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  async function post(path, body, token, humanSession = false) {
    const response = await fetch(`${base}${path}`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        ...(token ? { authorization: `Bearer ${token}` } : {}),
        ...(humanSession ? { origin: base, "sec-fetch-site": "same-origin" } : {}),
      },
      body: JSON.stringify(body),
    });
    return { status: response.status, body: await response.json() };
  }
  const agent = (await post("/api/demo/session", { persona: "alex" })).body.agentToken;
  const human = (await post("/api/demo/human-session", { persona: "alex" }, undefined, true)).body.humanToken;
  return {
    post: (path, body, role = "agent") => post(path, body, role === "human" ? human : agent),
    async status() {
      const response = await fetch(`${base}/api/commerce/v1/status`, { headers: { authorization: `Bearer ${agent}` } });
      return response.json();
    },
    close: () => new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve())),
  };
}

const input = (amountMinor, extra = {}) => ({
  journey: "weekend", goal: "compare", budgetLimit: { currency: "USD", amountMinor }, ...extra,
});

test("legacy and v1 HTTP proposals publish exact budget/no-action explanations without authorization", async () => {
  const dir = mkdtempSync(join(tmpdir(), "commerce-budget-http-"));
  const app = await start(join(dir, "state.json"));
  try {
    for (const path of ["/api/tasks", "/api/commerce/v1/tasks"]) {
      const normal = await app.post(path, input(7000));
      assert.equal(normal.status, 201);
      assert.deepEqual(normal.body.result.suggestions.map((entry) => entry.quoteId), ["weekend-camera", "weekend-coffee"]);
      assert.equal(normal.body.result.exclusions[0].reasonCode, "OVER_BUDGET");
      assert.equal(normal.body.result.exclusions[0].shortfallMinor, 999);
      const none = await app.post(path, input(1000));
      assert.equal(none.body.result.status, "no_action");
      assert.deepEqual(none.body.result.suggestions, []);
      assert.equal(none.body.result.exclusions.length, 3);
      const mismatched = await app.post(path, input(7000, {
        quoteId: "weekend-camera", budgetLimit: { currency: "HKD", amountMinor: 7000 },
      }));
      assert.equal(mismatched.body.error, "TASK_BUDGET_CURRENCY_MISMATCH");
      const excludedAction = await app.post(`/api/commerce/v1/tasks/${normal.body.result.id}/actions`, {
        action: { type: "request_quote", quoteId: "weekend-headphones" }, idempotencyKey: `exclude-${path}`,
      });
      assert.equal(excludedAction.body.error, "ACTION_OUT_OF_SCOPE");
    }
    const state = await app.status();
    assert.equal(state.payments.length, 0);
    assert.equal(state.consentRequests.length, 0);
    assert.equal(state.balances.USD, 30000);
  } finally {
    await app.close();
    rmSync(dir, { recursive: true, force: true });
  }
});

test("HTTP injected genuine overbudget quote fails with no persisted task or payment", async () => {
  const dir = mkdtempSync(join(tmpdir(), "commerce-budget-injection-"));
  const quote = CATALOG["weekend-headphones"];
  const app = await start(join(dir, "state.json"), {
    async propose() {
      return { summary: "untrusted", suggestions: [{
        type: "quote", quoteId: quote.id, action: "request_quote", merchantId: quote.merchantId,
        amountMinor: quote.amountMinor, currency: quote.currency, quoteVersion: quote.quoteVersion,
      }] };
    },
  });

  try {
    const before = await app.status();
    for (const path of ["/api/tasks", "/api/commerce/v1/tasks"]) {
      const result = await app.post(path, input(7000));
      assert.equal(result.status, 400);
      assert.equal(result.body.error, "PLANNER_OUTPUT_INVALID");
    }
    assert.deepEqual(await app.status(), before);
  } finally {
    await app.close();
    rmSync(dir, { recursive: true, force: true });
  }
});

test("HTTP planner input mutation cannot expand saved task budget", async () => {
  const dir = mkdtempSync(join(tmpdir(), "commerce-budget-mutation-"));
  const app = await start(join(dir, "state.json"), {
    async propose(request) {
      request.budgetLimit.amountMinor = 10000;
      request.quoteId = "weekend-headphones";
      const quote = CATALOG[request.quoteId];
      return { summary: "mutated", suggestions: [{
        type: "quote", quoteId: quote.id, action: "request_quote", merchantId: quote.merchantId,
        amountMinor: quote.amountMinor, currency: quote.currency, quoteVersion: quote.quoteVersion,
      }] };
    },
  });
  try {
    const before = await app.status();
    const result = await app.post("/api/commerce/v1/tasks", input(7000));
    assert.equal(result.status, 400);
    assert.equal(result.body.error, "PLANNER_OUTPUT_INVALID");
    assert.deepEqual(await app.status(), before);
  } finally {
    await app.close();
    rmSync(dir, { recursive: true, force: true });
  }
});

test("individually eligible camera/coffee still require human approval, cumulative authority and replay safety", async () => {
  const dir = mkdtempSync(join(tmpdir(), "commerce-budget-authority-"));
  const app = await start(join(dir, "state.json"));
  try {
    const task = (await app.post("/api/commerce/v1/tasks", input(7000))).body.result;
    const requestQuote = async (quoteId) => {
      assert.equal((await app.post(`/api/commerce/v1/tasks/${task.id}/actions`, {
        action: { type: "request_quote", quoteId }, idempotencyKey: quoteId,
      })).status, 200);
      return app.post("/api/commerce/v1/consent-requests", { taskId: task.id, quoteId });
    };
    const camera = (await requestQuote("weekend-camera")).body.result;
    assert.equal((await app.post(`/api/commerce/v1/consent-requests/${camera.id}/approve`, {})).status, 403);
    assert.equal((await app.post(`/api/commerce/v1/consents/${camera.id}/execute`, {})).status, 404);
    assert.equal((await app.status()).payments.length, 0);
    const approval = await app.post(`/api/commerce/v1/consent-requests/${camera.id}/approve`, {}, "human");
    const consentId = approval.body.result.consent.id;
    const payment = await app.post(`/api/commerce/v1/consents/${consentId}/execute`, {});
    assert.equal(payment.body.result.payment.amountMinor, 5999);
    const beforeReplay = await app.status();
    const replay = await app.post(`/api/commerce/v1/consents/${consentId}/execute`, {});
    assert.equal(replay.body.result.payment.id, payment.body.result.payment.id);
    assert.deepEqual(await app.status(), beforeReplay);
    const coffee = await requestQuote("weekend-coffee");
    assert.equal(coffee.body.error, "TASK_BUDGET_EXCEEDED");
    const state = await app.status();
    assert.equal(state.tasks[0].budgetUsage.remainingMinor, 1001);
    assert.equal(state.payments.length, 1);
  } finally {
    await app.close();
    rmSync(dir, { recursive: true, force: true });
  }
});

test("resetting one dedicated state never touches another service state", async () => {
  const dir = mkdtempSync(join(tmpdir(), "commerce-state-isolation-"));
  const defaultPath = join(dir, "default.json");
  const original = await start(defaultPath);
  const workshop = await start(join(dir, "workshop.json"));
  try {
    await original.post("/api/commerce/v1/tasks", input(7000));
    const before = readFileSync(defaultPath, "utf8");
    await workshop.post("/api/commerce/v1/tasks", input(1000));
    assert.equal((await workshop.post("/api/reset", {}, "human")).status, 200);
    assert.equal((await workshop.status()).tasks.length, 0);
    assert.equal(readFileSync(defaultPath, "utf8"), before);
    assert.equal((await original.status()).tasks.length, 1);
  } finally {
    await original.close();
    await workshop.close();
    rmSync(dir, { recursive: true, force: true });
  }
});
