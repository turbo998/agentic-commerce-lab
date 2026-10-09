import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createAppServer } from "../src/server.js";

async function start(statePath) {
  const server = createAppServer({ statePath });
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
    const tightConsents = await Promise.all(Array.from({ length: 20 }, (_, index) =>
      app.post("/api/consents", { ownerId: `contender-${index}`, taskId: "weekend-trip", quoteId: "weekend-camera" }),
    ));
    const outcomes = await Promise.all(tightConsents.map((response, index) =>
      app.post("/api/payments", {
        ownerId: `contender-${index}`,
        taskId: "weekend-trip",
        consentId: response.body.result.id,
        idempotencyKey: `contender-key-${index}`,
      }),
    ));
    assert.equal(outcomes.filter((result) => result.status === 200).length, 1);
    assert.equal(outcomes.filter((result) => result.body.error === "BUDGET_EXCEEDED").length, 19);

    const clean = await app.post("/api/reset", {});
    assert.equal(clean.body.payments.length, 0);
    assert.equal(clean.body.balances.USD, 30000);
    const consent = (await app.post("/api/consents", {
      ownerId: "restart-user", taskId: "city-trip", quoteId: "travel-hotel",
    })).body.result;
    const unknown = (await app.post("/api/payments", {
      ownerId: "restart-user", taskId: "city-trip", consentId: consent.id,
      idempotencyKey: "restart-unknown", outcome: "unknown",
    })).body.result;
    assert.equal(unknown.status, "unknown");
    const beforeRetry = await app.get("/api/state");
    const duplicate = await app.post("/api/payments", {
      ownerId: "restart-user", taskId: "city-trip", consentId: consent.id,
      idempotencyKey: "restart-unknown", outcome: "unknown",
    });
    assert.equal(duplicate.body.result.id, unknown.id);
    assert.equal(duplicate.body.state.events.length, beforeRetry.body.events.length);
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
    assert.equal(crossOrigin.status, 403);
    const formRequest = await fetch(`${app.base}/api/reset`, {
      method: "POST",
      headers: { "content-type": "text/plain" },
      body: "{}",
    });
    assert.equal(formRequest.status, 415);
    assert.equal((await app.post("/api/reset", null)).body.error, "INVALID_BODY");
  } finally {
    await app.close();
    rmSync(directory, { recursive: true, force: true });
  }
});
