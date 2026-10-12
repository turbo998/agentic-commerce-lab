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

const budgetTask = (amountMinor, currency = "USD", extra = {}) => ({
  ownerId: "fixture", journey: "weekend", goal: "compare synthetic quotes",
  budgetLimit: { currency, amountMinor }, ...extra,
});

test("USD70 returns two individual candidates and exact headphones rejection, not a basket", async () => {
  const task = await proposeTask(budgetTask(7000));
  assert.deepEqual(task.suggestions.map((entry) => entry.quoteId), ["weekend-camera", "weekend-coffee"]);
  assert.deepEqual(task.suggestions.map((entry) => entry.budgetHeadroomMinor), [1001, 5101]);
  assert.ok(task.suggestions.every((entry) => entry.reasonCode === "WITHIN_SINGLE_QUOTE_LIMIT"));
  assert.deepEqual(task.exclusions, [{
    quoteId: "weekend-headphones", amountMinor: 7999, currency: "USD",
    reasonCode: "OVER_BUDGET", shortfallMinor: 999,
  }]);
  assert.equal(task.noActionReason, null);
});

test("USD10 and one-minor boundary produce genuine no-action; equality is eligible", async () => {
  const task = await proposeTask(budgetTask(1000));
  assert.equal(task.status, "no_action");
  assert.deepEqual(task.suggestions, []);
  assert.equal(task.noActionReason, "NO_ELIGIBLE_QUOTES");
  assert.equal(task.exclusions.length, 3);
  const exact = await proposeTask(budgetTask(5999, "USD", { quoteId: "weekend-camera" }));
  assert.equal(exact.suggestions.length, 1);
  assert.equal(exact.suggestions[0].budgetHeadroomMinor, 0);
  const short = await proposeTask(budgetTask(5998, "USD", { quoteId: "weekend-camera" }));
  assert.equal(short.status, "no_action");
  assert.equal(short.exclusions[0].shortfallMinor, 1);
});

test("currency mismatch exclusions never convert; selected mismatch retains its error contract", async () => {
  const none = await proposeTask(budgetTask(1_000_000, "HKD"));
  assert.equal(none.status, "no_action");
  assert.ok(none.exclusions.every((entry) => entry.reasonCode === "CURRENCY_MISMATCH"));
  assert.ok(none.exclusions.every((entry) => !Object.hasOwn(entry, "shortfallMinor")));
  await assert.rejects(proposeTask(budgetTask(1_000_000, "HKD", { quoteId: "weekend-camera" })),
    (error) => error.code === "TASK_BUDGET_CURRENCY_MISMATCH");
  const guide = await proposeTask(budgetTask(1_200_000, "USDC", { journey: "travel" }));
  assert.deepEqual(guide.suggestions.map((entry) => entry.quoteId), ["travel-guide"]);
  assert.equal(guide.suggestions[0].budgetHeadroomMinor, 0);
  assert.equal(guide.exclusions.length, 2);
  const hotel = await proposeTask(budgetTask(8800, "HKD", { journey: "travel" }));
  assert.deepEqual(hotel.suggestions.map((entry) => entry.quoteId), ["travel-hotel", "travel-transit"]);
});

test("cancellation stays no-action and injected catalog overbudget proposal is rejected, not filtered", async () => {
  const cancel = await proposeTask(budgetTask(10000, "USD", { goal: "取消购买" }));
  assert.equal(cancel.status, "no_action");
  assert.equal(cancel.noActionReason, "PLANNER_NO_PROPOSALS");
  assert.match(cancel.summary, /取消/);
  const quote = CATALOG["weekend-headphones"];
  const mock = {
    async propose() {
      return { summary: "untrusted", suggestions: [{
        type: "quote", quoteId: quote.id, merchantId: quote.merchantId,
        amountMinor: quote.amountMinor, currency: quote.currency, quoteVersion: quote.quoteVersion,
        action: "request_quote",
      }] };
    },
  };
  await assert.rejects(proposeTask(budgetTask(7000), mock), (error) => error.code === "PLANNER_OUTPUT_INVALID");
  await assert.rejects(proposeTask(budgetTask(10000, "USD", { quoteId: "weekend-camera" }), mock),
    (error) => error.code === "PLANNER_OUTPUT_INVALID");
  const valid = await proposeTask(budgetTask(10000), mock);
  assert.equal(valid.suggestions[0].budgetHeadroomMinor, 2001);
});

test("server does not trust injected price, explanation or approval fields", async () => {
  const quote = CATALOG["weekend-camera"];
  const suggestion = {
    type: "quote", quoteId: quote.id, merchantId: quote.merchantId,
    amountMinor: quote.amountMinor, currency: quote.currency, quoteVersion: quote.quoteVersion,
    action: "request_quote",
  };
  for (const mutation of [
    { amountMinor: 1 }, { action: "approve_and_pay" }, { merchantId: "forged" },
    { currency: "HKD" }, { quoteVersion: "forged" },
  ]) {
    await assert.rejects(proposeTask(budgetTask(7000), {
      async propose() { return { summary: "bad", suggestions: [{ ...suggestion, ...mutation }] }; },
    }), (error) => error.code === "PLANNER_OUTPUT_INVALID");
  }
  const task = await proposeTask(budgetTask(7000), {
    async propose() {
      return { summary: "test", exclusions: [], suggestions: [{
        ...suggestion, reasonCode: "APPROVED", budgetHeadroomMinor: 999999, humanApproved: true,
      }] };
    },
  });
  assert.equal(task.suggestions[0].reasonCode, "WITHIN_SINGLE_QUOTE_LIMIT");
  assert.equal(task.suggestions[0].budgetHeadroomMinor, 1001);
  assert.equal(Object.hasOwn(task.suggestions[0], "humanApproved"), false);
  assert.equal(task.exclusions[0].quoteId, "weekend-headphones");
});

test("planner cannot mutate the server-owned budget or selected quote scope", async () => {
  const suggestionFor = (quoteId) => {
    const quote = CATALOG[quoteId];
    return {
      type: "quote", quoteId, merchantId: quote.merchantId, amountMinor: quote.amountMinor,
      currency: quote.currency, quoteVersion: quote.quoteVersion, action: "request_quote",
    };
  };
  const original = budgetTask(7000, "USD", { quoteId: "weekend-camera" });
  await assert.rejects(proposeTask(original, {
    async propose(input) {
      input.budgetLimit.amountMinor = 10000;
      input.quoteId = "weekend-headphones";
      return { summary: "mutated", suggestions: [suggestionFor("weekend-headphones")] };
    },
  }), (error) => error.code === "PLANNER_OUTPUT_INVALID");
  assert.equal(original.budgetLimit.amountMinor, 7000);
  assert.equal(original.quoteId, "weekend-camera");
  const result = await proposeTask(original, {
    async propose(input) {
      input.budgetLimit.amountMinor = 999999;
      input.journey = "travel";
      input.goal = "mutated";
      input.ownerId = "mutated";
      return { summary: "valid proposal despite mutated input", suggestions: [suggestionFor("weekend-camera")] };
    },
  });
  assert.equal(result.budgetLimit.amountMinor, 7000);
  assert.equal(result.journey, "weekend");
  assert.equal(result.goal, original.goal);
  assert.equal(result.ownerId, original.ownerId);
  assert.equal(result.suggestions[0].budgetHeadroomMinor, 1001);
  await assert.rejects(proposeTask(original, {
    async propose() { return { summary: "null", suggestions: [null] }; },
  }), (error) => error.code === "PLANNER_OUTPUT_INVALID");
});
