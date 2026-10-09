import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const connector = JSON.parse(readFileSync(new URL("../connector/copilot-commerce.swagger.json", import.meta.url)));

test("Copilot connector stays within the least-privilege tool contract", () => {
  assert.equal(connector.swagger, "2.0");
  assert.equal(connector.host, "localhost:4173");
  assert.deepEqual(connector.schemes, ["http"]);
  const operations = Object.values(connector.paths).flatMap((path) => Object.entries(path)
    .map(([method, operation]) => ({ method, operation })));
  const operationIds = operations.map(({ operation }) => operation.operationId);
  assert.deepEqual(operationIds.sort(), [
    "Commerce_CreateTask",
    "Commerce_GetMyCommerceStatus",
    "Commerce_GetTask",
    "Commerce_ListSyntheticOffers",
    "Commerce_RequestPaidResourceChallenge",
    "Commerce_RequestEligibleRefund",
    "Commerce_RequestHumanApproval",
    "Commerce_RequestQuote",
  ].sort());
  assert.ok(operations.every(({ method }) => ["get", "post"].includes(method)));
  assert.ok(!connector.paths["/consent-requests/{requestId}/approve"]);
  assert.ok(!connector.paths["/consents/{consentId}/execute"]);
  assert.ok(!connector.paths["/payments"]);
  assert.ok(!connector.paths["/payments/refund"]);
  assert.ok(!connector.paths["/demo/human-session"]);
  assert.deepEqual(connector.definitions.CreateTask.required.sort(), ["budgetLimit", "goal", "journey"]);
  for (const definition of Object.values(connector.definitions)) {
    assert.equal(definition.additionalProperties, false);
    assert.ok(!Object.hasOwn(definition.properties ?? {}, "ownerId"));
    assert.ok(!Object.hasOwn(definition.properties ?? {}, "tenantId"));
  }
  assert.match(connector.info.description, /not Microsoft Entra authentication/);
});
