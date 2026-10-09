import { CATALOG } from "./catalog.js";
import { AuthorityError } from "./authority.js";

export function paymentRequired(resourceId, challenge) {
  const quote = CATALOG[resourceId];
  if (!quote || quote.id !== "travel-guide") {
    throw new AuthorityError("RESOURCE_NOT_FOUND", "本地 402 模拟未配置此资源。");
  }
  if (challenge && (challenge.resourceId !== resourceId || challenge.quoteId !== quote.id)) {
    throw new AuthorityError("RESOURCE_CHALLENGE_REQUIRED", "资源付款挑战必须来自当前任务的持久化 challenge。");
  }
  return {
    status: 402,
    protocol: "HTTP 402-shaped local simulation (not full MPP/x402 conformance)",
    challenge: {
      challengeId: challenge?.id ?? null,
      taskId: challenge?.taskId ?? null,
      resource: `urn:agentic-commerce:resource:${resourceId}`,
      merchantId: quote.merchantId,
      quoteId: quote.id,
      quoteVersion: quote.quoteVersion,
      amountMinor: quote.amountMinor,
      currency: quote.currency,
      intent: "one-time",
      settlement: "local-simulation-only",
      message: "This synthetic resource requires an exact, user-approved one-time payment.",
    },
  };
}
