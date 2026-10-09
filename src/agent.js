import { randomUUID } from "node:crypto";
import { CATALOG, CURRENCIES } from "./catalog.js";
import { AuthorityError } from "./authority.js";

export const offlinePlanner = Object.freeze({
  kind: "scripted-offline",
  async propose({ journey, goal, quoteId, budgetLimit }) {
    const refusal = /\b(no|don't|do not|cancel|stop)\b|不买|取消|停止/i.test(goal);
    if (refusal) return { summary: "已记录不购买/取消意图，不创建付款操作。", suggestions: [] };
    const quotes = Object.values(CATALOG).filter((quote) =>
      quote.journey === journey && quote.currency === budgetLimit.currency);
    const selected = quoteId ? quotes.filter((quote) => quote.id === quoteId) : quotes.slice(0, 3);
    return {
      summary: `离线脚本为“${goal}”列出 ${selected.length} 个合成报价；这不是 LLM 推理。`,
      suggestions: selected.map((quote) => ({
        type: "quote",
        quoteId: quote.id,
        merchantId: quote.merchantId,
        amountMinor: quote.amountMinor,
        currency: quote.currency,
        quoteVersion: quote.quoteVersion,
        action: "request_quote",
      })),
    };
  },
});

export function plannerContract(planner) {
  if (!planner || typeof planner.propose !== "function") {
    throw new AuthorityError("PLANNER_INTERFACE_INVALID", "Planner 必须实现 propose(input)。");
  }
  return planner;
}

function validatePlan(plan, journey, budgetLimit) {
  if (!plan || typeof plan.summary !== "string" || !Array.isArray(plan.suggestions) || plan.suggestions.length > 3) {
    throw new AuthorityError("PLANNER_OUTPUT_INVALID", "Planner 输出不符合结构化建议格式。");
  }
  for (const suggestion of plan.suggestions) {
    const quote = CATALOG[suggestion?.quoteId];
    if (
      suggestion.type !== "quote" ||
      suggestion.action !== "request_quote" ||
      !quote ||
      quote.journey !== journey ||
      quote.currency !== budgetLimit.currency ||
      suggestion.merchantId !== quote.merchantId ||
      suggestion.amountMinor !== quote.amountMinor ||
      suggestion.currency !== quote.currency ||
      suggestion.quoteVersion !== quote.quoteVersion
    ) {
      throw new AuthorityError("PLANNER_OUTPUT_INVALID", "Planner 只能建议本旅程中匹配固定目录报价的 request_quote。");
    }
  }
  return {
    summary: plan.summary.slice(0, 500),
    suggestions: plan.suggestions.map((suggestion) => ({ ...suggestion })),
  };
}

export async function proposeTask(input, planner = offlinePlanner) {
  plannerContract(planner);
  if (
    typeof input.ownerId !== "string" ||
    input.ownerId.length < 1 ||
    input.ownerId.length > 128 ||
    !["weekend", "travel"].includes(input.journey)
  ) {
    throw new AuthorityError("INVALID_TASK", "任务需要用户标识和受支持的旅程。");
  }
  if (typeof input.goal !== "string" || !input.goal.trim() || input.goal.length > 300) {
    throw new AuthorityError("INVALID_TASK", "任务目标必须是 1 至 300 个字符。");
  }
  if (
    !input.budgetLimit ||
    !Object.hasOwn(CURRENCIES, input.budgetLimit.currency) ||
    !Number.isSafeInteger(input.budgetLimit.amountMinor) ||
    input.budgetLimit.amountMinor < 1
  ) {
    throw new AuthorityError("INVALID_TASK_BUDGET", "任务必须绑定一个受支持币种的正整数限额（最小货币单位）。");
  }
  if (input.quoteId && CATALOG[input.quoteId]?.journey !== input.journey) {
    throw new AuthorityError("INVALID_TASK", "指定报价不属于该旅程。");
  }
  if (input.quoteId && CATALOG[input.quoteId].currency !== input.budgetLimit.currency) {
    throw new AuthorityError("TASK_BUDGET_CURRENCY_MISMATCH", "任务限额币种必须与所选报价一致；不会进行币种换算。");
  }
  const request = {
    ownerId: input.ownerId,
    journey: input.journey,
    goal: input.goal.trim(),
    quoteId: input.quoteId,
    budgetLimit: { ...input.budgetLimit },
  };
  const plan = validatePlan(await planner.propose(request), input.journey, request.budgetLimit);
  return {
    id: `task-${randomUUID()}`,
    ownerId: input.ownerId,
    tenantId: input.tenantId ?? "tenant-demo",
    journey: input.journey,
    goal: request.goal,
    budgetLimit: request.budgetLimit,
    status: plan.suggestions.length ? "proposed" : "no_action",
    planner: planner.kind === "scripted-offline" ? "scripted-offline (not model inference)" : "injected-test-client",
    summary: plan.summary,
    suggestions: plan.suggestions,
    createdAt: Date.now(),
    actionRequests: {},
  };
}

export function requestTaskAction(state, { ownerId, tenantId, taskId, action, idempotencyKey }) {
  const task = state.tasks[taskId];
  if (!task || task.ownerId !== ownerId || (tenantId && task.tenantId !== tenantId)) {
    throw new AuthorityError("TASK_NOT_FOUND", "任务不存在或不属于此用户。");
  }
  if (typeof idempotencyKey !== "string" || !idempotencyKey) {
    throw new AuthorityError("IDEMPOTENCY_REQUIRED", "Action request 需要幂等键。");
  }
  const fingerprint = JSON.stringify({ ownerId, taskId, action });
  const prior = task.actionRequests[idempotencyKey];
  if (prior) {
    if (prior.fingerprint !== fingerprint) {
      throw new AuthorityError("IDEMPOTENCY_CONFLICT", "Action 幂等键已用于不同请求。");
    }
    return { quote: CATALOG[action.quoteId], replay: true };
  }
  if (
    !action ||
    action.type !== "request_quote" ||
    !CATALOG[action.quoteId] ||
    Object.keys(action).some((key) => !["type", "quoteId"].includes(key))
  ) {
    throw new AuthorityError("ACTION_NOT_ALLOWED", "Agent 只能请求报价；不能批准、付款、退款或扩大预算。");
  }
  if (!task.suggestions.some((suggestion) => suggestion.action === "request_quote" && suggestion.quoteId === action.quoteId)) {
    throw new AuthorityError("ACTION_OUT_OF_SCOPE", "此报价不在该任务的结构化建议中。");
  }
  task.actionRequests[idempotencyKey] = { fingerprint, quoteId: action.quoteId };
  state.events.push({
    id: `evt-${state.sequence++}`,
    type: "agent.action_request_quote",
    paymentId: null,
    taskId,
    at: new Date().toISOString(),
  });
  return { quote: CATALOG[action.quoteId], replay: false };
}
