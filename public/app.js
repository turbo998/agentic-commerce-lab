const API = "/api/commerce/v1";
const labels = {
  captured: "已模拟扣款",
  unknown: "结果未知 · 待对账",
  declined: "模拟拒绝",
  partially_refunded: "部分退款",
  refunded: "已全额退款",
  manual_review: "履约失败 · 待人工处理",
  compensated: "已补偿退款",
};
let identity;
let currentJourney = "weekend";
let selectedQuote;
const trace = [];

function escapeHtml(value) {
  return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#39;");
}

const money = (minor, currency) => {
  const value = minor / ({ USD: 100, HKD: 100, USDC: 1_000_000 }[currency]);
  if (currency === "USDC") return `${new Intl.NumberFormat("zh-Hans", { maximumFractionDigits: 6 }).format(value)} USDC`;
  return new Intl.NumberFormat("zh-Hans", { style: "currency", currency }).format(value);
};

function tokenFor(role) {
  return role === "human" ? identity?.humanToken : identity?.agentToken;
}

async function api(path, body, role = "agent") {
  if (role === "human") {
    const session = await fetch("/api/demo/human-session", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ persona: "alex" }),
    });
    const result = await session.json();
    if (!session.ok) throw new Error(result.message ?? "无法启动本地人工演示会话");
    identity.humanToken = result.humanToken;
  }
  const response = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers: {
      ...(body === undefined ? {} : { "content-type": "application/json" }),
      ...(tokenFor(role) ? { authorization: `Bearer ${tokenFor(role)}` } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await response.json();
  if (response.status === 402) return { ...data, httpStatus: response.status };
  if (!response.ok) throw new Error(data.message ?? data.error ?? "请求失败");
  return data;
}

function showNotice(message = "") {
  document.querySelector("#notice").textContent = message;
}

function recordTool(name, status, detail = "") {
  trace.unshift({ name, status, detail, at: new Date().toLocaleTimeString() });
  document.querySelector("#tool-trace").innerHTML = trace.slice(0, 10).map((item) =>
    `<li><strong>${escapeHtml(item.name)}</strong><span>${escapeHtml(item.status)}</span><small>${escapeHtml(item.detail)} · ${escapeHtml(item.at)}</small></li>`,
  ).join("");
}

async function refresh() {
  const [catalog, state] = await Promise.all([
    api(`${API}/catalog?journey=${currentJourney}`),
    api(`${API}/status`),
  ]);
  document.querySelector("#identity-label").textContent =
    `本地合成身份 ${state.subject} · ${state.tenantId}（非 Entra 验证）`;
  document.querySelector("#balances").innerHTML = Object.entries(state.balances).map(([currency, value]) =>
    `<div class="balance"><strong>${currency} 可用余额</strong><span>${money(value, currency)}</span></div>`,
  ).join("");
  document.querySelector("#task-budgets").innerHTML = state.tasks.slice().reverse().map((task) =>
    `<article class="payment"><div><h3>绑定任务额度 ${escapeHtml(task.id)}</h3>
    <p>${task.budgetPolicySource === "legacy-migration-not-user-policy" ? "旧版本迁移额度（非原用户结构化授权） · " : ""}${escapeHtml(task.budgetLimit.currency)} · 上限 ${money(task.budgetLimit.amountMinor, task.budgetLimit.currency)}
    · 已支出 ${money(task.budgetUsage.spentMinor, task.budgetLimit.currency)}
    · 有效预留 ${money(task.budgetUsage.reservedMinor, task.budgetLimit.currency)}
    · 剩余 ${money(task.budgetUsage.remainingMinor, task.budgetLimit.currency)}</p></div></article>`,
  ).join("");
  document.querySelector("#catalog").innerHTML = catalog.items.map((quote) => `
    <article class="offer">
      <div class="merchant">${quote.merchant}</div>
      <h3>${quote.items[0].name}</h3>
      <div class="subtle">报价 ${quote.quoteVersion} · 商户 ${quote.merchantId}</div>
      <div class="price">${money(quote.amountMinor, quote.currency)} <span class="currency">${quote.currency}</span></div>
      <button class="button primary" data-select="${quote.id}">加入任务比较</button>
    </article>
  `).join("");
  document.querySelectorAll("[data-select]").forEach((button) => button.addEventListener("click", () => {
    selectedQuote = button.dataset.select;
    const quote = catalog.items.find((item) => item.id === selectedQuote);
    document.querySelector("#selected-quote").textContent =
      `已选择：${quote.items[0].name} · 报价 ${money(quote.amountMinor, quote.currency)} ${quote.currency}。请明确填写任务总限额。`;
    const budgetCurrency = document.querySelector("#budget-currency");
    budgetCurrency.value = quote.currency;
    document.querySelector("#budget-amount").step = quote.currency === "USDC" ? "0.000001" : "0.01";
    document.querySelector("#goal").focus();
  }));
  document.querySelector("#consents").innerHTML = state.consentRequests.slice().reverse().map((request) => `
    <article class="payment">
      <div><h3>${request.items[0].name} <span class="status">${request.status}</span></h3>
      <p>${request.merchantId} · ${money(request.amountMinor, request.currency)} ${request.currency} · task ${request.taskId}<br>
      任务限额 ${money(request.budgetLimit.amountMinor, request.budgetLimit.currency)} ${request.budgetLimit.currency}<br>
      报价 ${request.quoteVersion} · 到期 ${new Date(request.expiresAt).toLocaleTimeString()}</p></div>
      ${request.status === "pending" ? `<a class="button primary" href="/consent.html?request=${encodeURIComponent(request.id)}">在独立批准页审核</a>` : ""}
    </article>
  `).join("") || `<p class="subtle">暂无待批准请求。聊天中的“同意”不是消费授权。</p>`;
  document.querySelector("#payments").innerHTML = state.payments.slice().reverse().map((payment) => {
    const title = payment.items.map((item) => item.name).join("、");
    const actions = payment.status === "unknown"
      ? `<button class="button secondary" data-reconcile="${payment.id}">查询模拟结果</button>`
      : ["captured", "partially_refunded"].includes(payment.status)
        ? `${payment.fulfillmentStatus === "pending" ? `<button class="button secondary" data-fulfill="${payment.id}">模拟履约</button><button class="button secondary" data-fail="${payment.id}">模拟履约失败</button>` : ""}
          ${payment.fulfillmentStatus === "manual_review" ? `<button class="button secondary" data-resolve="${payment.id}" data-action="retry">人工重试履约</button><button class="button secondary" data-resolve="${payment.id}" data-action="refund">人工补偿退款</button>` : ""}
          ${payment.status !== "refunded" ? `<button class="button secondary" data-refund="${payment.id}" data-amount="${payment.amountMinor - payment.refundedMinor}">申请剩余退款</button>` : ""}`
        : "";
    const visibleStatus = payment.fulfillmentStatus === "manual_review"
      ? labels.manual_review
      : payment.fulfillmentStatus === "compensated"
        ? labels.compensated
        : labels[payment.status] ?? payment.status;
    return `<article class="payment"><div><h3>${title} <span class="status">${visibleStatus}</span></h3>
      <p>${payment.merchantId} · ${money(payment.amountMinor, payment.currency)} · ${payment.id}
      ${payment.receipt ? `<br>收据 ${payment.receipt.id} · 履约 ${payment.fulfillmentStatus}` : ""}</p></div>
      <div class="payment-actions">${actions}</div></article>`;
  }).join("") || `<p class="subtle">尚无模拟交易。先通过对话提出目标。</p>`;
  document.querySelector("#event-count").textContent = `${state.events.length} 条本地事件`;
  document.querySelectorAll("[data-reconcile]").forEach((button) => button.addEventListener("click", () => reconcile(button.dataset.reconcile)));
  document.querySelectorAll("[data-fulfill]").forEach((button) => button.addEventListener("click", () => fulfill(button.dataset.fulfill)));
  document.querySelectorAll("[data-fail]").forEach((button) => button.addEventListener("click", () => failFulfillment(button.dataset.fail)));
  document.querySelectorAll("[data-resolve]").forEach((button) => button.addEventListener("click", () => resolveFulfillment(button.dataset.resolve, button.dataset.action)));
  document.querySelectorAll("[data-refund]").forEach((button) => button.addEventListener("click", () => requestRefund(button.dataset.refund, Number(button.dataset.amount))));
  const refundRequests = state.refundRequests.filter((item) => item.status === "pending");
  if (refundRequests.length) {
    document.querySelector("#refund-requests").innerHTML = refundRequests.map((item) =>
      `<p>退款请求 ${money(item.amountMinor, item.currency)} <a href="/consent.html?refund=${encodeURIComponent(item.id)}">转到人工复核</a></p>`,
    ).join("");
  }
}

async function createTask(goal) {
  if (!goal.trim()) {
    showNotice("请先描述购物或旅行目标。");
    return;
  }
  try {
    const budgetCurrency = document.querySelector("#budget-currency").value;
    const budgetAmount = document.querySelector("#budget-amount").value.trim();
    const decimals = { USD: 2, HKD: 2, USDC: 6 }[budgetCurrency];
    const parts = budgetAmount.split(".");
    if (!/^\d+(?:\.\d+)?$/.test(budgetAmount) || (parts[1]?.length ?? 0) > decimals) {
      throw new Error(`请输入有效的 ${budgetCurrency} 结构化任务限额，最多 ${decimals} 位小数。`);
    }
    const amountMinor = BigInt(parts[0]) * BigInt(10 ** decimals) +
      BigInt((parts[1] ?? "").padEnd(decimals, "0") || 0);
    if (amountMinor < 1n || amountMinor > BigInt(Number.MAX_SAFE_INTEGER)) {
      throw new Error("任务限额必须为可表示的正数。");
    }
    const response = await api(`${API}/tasks`, {
      journey: currentJourney,
      goal,
      budgetLimit: { currency: budgetCurrency, amountMinor: Number(amountMinor) },
      ...(selectedQuote ? { quoteId: selectedQuote } : {}),
    });
    const task = response.result;
    recordTool("Create task", "201", `${task.planner} · ${task.id}`);
    document.querySelector("#conversation").innerHTML = `
      <article class="payment agent-message"><div><h3>离线任务建议</h3>
      <p>${escapeHtml(task.summary)}</p><p>Task ${escapeHtml(task.id)} · ${task.suggestions.length} 个目录建议</p>
      <p>结构化任务上限 ${money(task.budgetLimit.amountMinor, task.budgetLimit.currency)} ${task.budgetLimit.currency}；自由文本不是额度政策。</p></div></article>
      ${task.suggestions.map((suggestion) => {
        const quote = response.result.suggestions.find((entry) => entry.quoteId === suggestion.quoteId);
        return `<article class="offer"><h3>${quote.quoteId} · ${quote.currency} ${money(quote.amountMinor, quote.currency)}</h3>
          <p>${quote.merchantId} · ${quote.quoteVersion}</p>
          <button class="button primary" data-request-consent="${quote.quoteId}" data-task="${task.id}">请求人工批准</button></article>`;
      }).join("") || `<p class="subtle">脚本未提出购买建议。</p>`}
    `;
    document.querySelectorAll("[data-request-consent]").forEach((button) =>
      button.addEventListener("click", () => requestConsent(button.dataset.task, button.dataset.requestConsent)),
    );
    selectedQuote = undefined;
    document.querySelector("#selected-quote").textContent = "";
    document.querySelector("#goal").value = "";
    await refresh();
  } catch (error) {
    recordTool("Create task", "error", error.message);
    showNotice(error.message);
  }
}

async function requestConsent(taskId, quoteId) {
  try {
    let challengeId;
    if (quoteId === "travel-guide") {
      const challenge = await api(`${API}/resources/travel-guide`, { taskId });
      if (challenge.httpStatus !== 402 || !challenge.challenge?.challengeId) {
        throw new Error("付费资源没有返回有效的 HTTP 402 challenge。");
      }
      challengeId = challenge.challenge.challengeId;
      recordTool("Paid resource challenge", "HTTP 402", `${challengeId} · ${money(challenge.challenge.amountMinor, challenge.challenge.currency)}`);
    }
    const action = await api(`${API}/tasks/${encodeURIComponent(taskId)}/actions`, {
      action: { type: "request_quote", quoteId },
      idempotencyKey: `quote-${taskId}-${quoteId}`,
    });
    recordTool("Request quote", action.result.replay ? "replay" : "accepted", action.result.quote.merchantId);
    const result = await api(`${API}/consent-requests`, {
      taskId, quoteId, ...(challengeId ? { challengeId } : {}),
    });
    recordTool("Request consent", "pending human approval", result.result.id);
    showNotice("授权请求已提交。请在独立批准界面检查完整商户、金额、币种和报价版本。");
    await refresh();
  } catch (error) {
    recordTool("Request consent", "rejected", error.message);
    showNotice(error.message);
  }
}

async function reconcile(paymentId) {
  try {
    await api(`${API}/payments/${paymentId}/reconcile`, {});
    recordTool("Reconcile payment", "complete", paymentId);
    await refresh();
  } catch (error) { showNotice(error.message); }
}

async function fulfill(paymentId) {
  try {
    await api(`${API}/payments/${paymentId}/fulfill`, {}, "human");
    recordTool("Fulfill order", "simulated", paymentId);
    await refresh();
  } catch (error) { showNotice(error.message); }
}

async function failFulfillment(paymentId) {
  try {
    await api(`/api/payments/fulfillment/fail`, { paymentId, reason: "simulated_failure" }, "human");
    recordTool("Fulfillment", "manual review", paymentId);
    await refresh();
  } catch (error) { showNotice(error.message); }
}

async function resolveFulfillment(paymentId, action) {
  try {
    await api(`/api/payments/fulfillment/resolve`, { paymentId, action }, "human");
    recordTool("Human fulfillment decision", action, paymentId);
    await refresh();
  } catch (error) { showNotice(error.message); }
}

async function requestRefund(paymentId, amountMinor) {
  try {
    const response = await api(`${API}/refund-requests`, {
      paymentId, amountMinor, idempotencyKey: `refund-${paymentId}-${amountMinor}`,
    });
    recordTool("Request refund", response.result.status, response.result.id);
    showNotice("退款已进入人工复核；agent/tool 不能批准退款。");
    await refresh();
  } catch (error) { showNotice(error.message); }
}

async function initialize() {
  identity = await api("/api/demo/session", { persona: "alex" }, "none");
  sessionStorage.setItem("commerce-demo-identity", JSON.stringify(identity));
  const budgetCurrency = document.querySelector("#budget-currency");
  const budgetAmount = document.querySelector("#budget-amount");
  budgetCurrency.addEventListener("change", () => {
    budgetAmount.step = budgetCurrency.value === "USDC" ? "0.000001" : "0.01";
  });
  budgetAmount.step = "0.01";
  document.querySelectorAll("[data-journey]").forEach((tab) => tab.addEventListener("click", () => {
    currentJourney = tab.dataset.journey;
    selectedQuote = undefined;
    document.querySelectorAll("[data-journey]").forEach((button) => {
      const active = button === tab;
      button.classList.toggle("active", active);
      button.setAttribute("aria-selected", String(active));
    });
    refresh();
  }));
  document.querySelector("#task-form").addEventListener("submit", (event) => {
    event.preventDefault();
    createTask(document.querySelector("#goal").value);
  });
  document.querySelector("#reset").addEventListener("click", async () => {
    if (!window.confirm("清除本地模拟交易并恢复初始合成预算？")) return;
    await api("/api/reset", {}, "human");
    trace.length = 0;
    recordTool("Reset", "local state reset");
    showNotice("本地模拟状态已重置。");
    await refresh();
  });
  await refresh();
}

initialize().catch((error) => showNotice(`本地演示会话不可用：${error.message}`));
