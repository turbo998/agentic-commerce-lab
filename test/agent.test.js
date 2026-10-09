import test from "node:test";
import assert from "node:assert/strict";
import { proposeTask, plannerContract } from "../src/agent.js";
import { CATALOG } from "../src/catalog.js";
import { AuthorityError } from "../src/authority.js";

test("planner interface accepts an injected mock client and enforces proposal-only output", async () => {
  let calls = 0;
  const mock = {
    kind: "mock-llm-contract",
    async propose(input) {
      calls++;
      assert.equal(input.ownerId, "mock-user");
      assert.equal(input.quoteId, "weekend-camera");
      const quote = CATALOG[input.quoteId];
      return {
        summary: "Mocked proposal; no network or model call.",
        suggestions: [{
          type: "quote",
          quoteId: quote.id,
          merchantId: quote.merchantId,
          amountMinor: quote.amountMinor,
          currency: quote.currency,
          quoteVersion: quote.quoteVersion,
          action: "request_quote",
        }],
      };
    },
  };
  const proposal = await proposeTask({
    ownerId: "mock-user", journey: "weekend", goal: "compare", quoteId: "weekend-camera",
    budgetLimit: { currency: "USD", amountMinor: 10000 },
  }, mock);
  assert.equal(calls, 1);
  assert.equal(proposal.planner, "injected-test-client");
  assert.equal(proposal.suggestions[0].action, "request_quote");
  assert.equal(proposal.status, "proposed");

  const unsafe = {
    ...mock,
    async propose() {
      return {
        summary: "unsafe mock output",
        suggestions: [{ type: "payment", quoteId: "weekend-camera", action: "approve_and_pay" }],
      };
    },
  };
  await assert.rejects(
    proposeTask({
      ownerId: "mock-user", journey: "weekend", goal: "pay",
      budgetLimit: { currency: "USD", amountMinor: 10000 },
    }, unsafe),
    (error) => error instanceof AuthorityError && error.code === "PLANNER_OUTPUT_INVALID",
  );
  assert.throws(() => plannerContract({}), (error) => error.code === "PLANNER_INTERFACE_INVALID");
});
