const OWNER = "user-demo";
const TASKS = { weekend: "weekend-trip", travel: "harbor-city-trip" };
const labels = {
  captured: "已模拟扣款",
  unknown: "结果未知 · 待对账",
  declined: "模拟拒绝",
  partially_refunded: "部分退款",
  refunded: "已全额退款",
};
let currentJourney = "weekend";

const money = (minor, currency) => {
  const value = minor / ({ USD: 100, HKD: 100, USDC: 1_000_000 }[currency]);
  if (currency === "USDC") return `${new Intl.NumberFormat("zh-Hans", { maximumFractionDigits: 6 }).format(value)} USDC`;
  return new Intl.NumberFormat("zh-Hans", { style: "currency", currency }).format(value);
};

async function api(path, body) {
  const response = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers: body === undefined ? {} : { "content-type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.message ?? data.error ?? "请求失败");
  return data;
}

function showNotice(message = "") {
  document.querySelector("#notice").textContent = message;
}

async function refresh() {
  const state = await api("/api/state");
  document.querySelector("#balances").innerHTML = Object.entries(state.balances).map(([currency, value]) =>
    `<div class="balance"><strong>${currency} 可用余额</strong><span>${money(value, currency)}</span></div>`,
  ).join("");
  const offers = Object.values(state.catalog).filter((quote) => quote.journey === currentJourney);
  document.querySelector("#catalog").innerHTML = offers.map((quote) => `
    <article class="offer">
      <div class="merchant">${quote.merchant}</div>
      <h3>${quote.items[0].name}</h3>
      <div class="subtle">报价 ${quote.quoteVersion} · 商户 ${quote.merchantId}</div>
      <div class="price">${money(quote.amountMinor, quote.currency)} <span class="currency">${quote.currency}</span></div>
      <button class="button primary" data-quote="${quote.id}">审核并授权</button>
    </article>
  `).join("");
  document.querySelectorAll("[data-quote]").forEach((button) => button.addEventListener("click", () => approveAndPay(button.dataset.quote)));
  const pendingConsents = state.consents.filter((consent) =>
    !consent.revokedAt && !consent.usedByPaymentId && consent.expiresAt > Date.now(),
  );
  document.querySelector("#consents").innerHTML = pendingConsents.map((consent) => {
    const quote = state.catalog[consent.quoteId];
    return `<article class="payment"><div><h3>${quote.merchant} <span class="status">待执行</span></h3><p>${consent.items.map((item) => `${item.name} × ${item.quantity}`).join("、")} · ${money(consent.amountMinor, consent.currency)} · ${consent.currency} · ${consent.quoteVersion}<br>任务 ${consent.taskId} · 授权有效 15 分钟</p></div><div class="payment-actions"><button class="button primary" data-pay="${consent.id}">批准并模拟扣款</button><button class="button secondary" data-unknown="${consent.id}">模拟结果未知</button><button class="button secondary" data-revoke="${consent.id}">撤销</button></div></article>`;
  }).join("") || `<p class="subtle">暂无待执行授权。审核商户报价后，可在执行前再次批准或撤销。</p>`;
  document.querySelectorAll("[data-pay]").forEach((button) => button.addEventListener("click", () => payConsent(button.dataset.pay, "captured")));
  document.querySelectorAll("[data-unknown]").forEach((button) => button.addEventListener("click", () => payConsent(button.dataset.unknown, "unknown")));
  document.querySelectorAll("[data-revoke]").forEach((button) => button.addEventListener("click", () => revoke(button.dataset.revoke)));
  document.querySelector("#payments").innerHTML = state.payments.slice().reverse().map((payment) => {
    const title = payment.items.map((item) => item.name).join("、");
    const actions = payment.status === "unknown"
      ? `<button class="button secondary" data-reconcile="${payment.id}">查询模拟结果</button>`
      : ["captured", "partially_refunded"].includes(payment.status)
        ? `${payment.fulfillmentStatus === "pending" ? `<button class="button secondary" data-fulfill="${payment.id}">模拟商户履约</button>` : ""}<button class="button secondary" data-refund="${payment.id}" data-amount="${payment.amountMinor - payment.refundedMinor}">模拟剩余退款</button>`
        : "";
    const receipt = payment.receipt ? ` · 收据 ${payment.receipt.id} · 履约 ${payment.fulfillmentStatus}` : "";
    return `<article class="payment"><div><h3>${title} <span class="status">${labels[payment.status] ?? payment.status}</span></h3><p>${payment.merchantId} · ${money(payment.amountMinor, payment.currency)} · ${payment.id}${receipt}</p></div><div class="payment-actions">${actions}</div></article>`;
  }).join("") || `<p class="subtle">尚无模拟交易。先选择一个商户报价，仔细审核后再授权。</p>`;
  document.querySelectorAll("[data-reconcile]").forEach((button) => button.addEventListener("click", () => reconcile(button.dataset.reconcile)));
  document.querySelectorAll("[data-fulfill]").forEach((button) => button.addEventListener("click", () => fulfill(button.dataset.fulfill)));
  document.querySelectorAll("[data-refund]").forEach((button) => button.addEventListener("click", () => refund(button.dataset.refund, Number(button.dataset.amount))));
  document.querySelector("#event-count").textContent = `${state.events.length} 条本地事件`;
}

async function approveAndPay(quoteId) {
  const quote = (await api("/api/state")).catalog[quoteId];
  const accepted = window.confirm(
    `仅限本次交易的授权\n\n用户：演示用户\n任务：${TASKS[currentJourney]}\n商户：${quote.merchant}\n商品：${quote.items.map((item) => item.name).join("、")}\n金额：${money(quote.amountMinor, quote.currency)}\n报价版本：${quote.quoteVersion}\n有效期：15 分钟\n\n此步骤仅建立待执行授权。随后仍需再次批准模拟付款，也可以先撤销。是否创建授权？`,
  );
  if (!accepted) return;
  try {
    await api("/api/consents", { ownerId: OWNER, taskId: TASKS[currentJourney], quoteId });
    showNotice("一次性授权已建立。可再次审核后执行模拟付款，也可在执行前撤销。");
    await refresh();
  } catch (error) {
    showNotice(error.message);
    await refresh();
  }
}

async function payConsent(consentId, outcome) {
  try {
    const consent = (await api("/api/state")).consents.find((item) => item.id === consentId);
    if (!window.confirm(`最后确认\n\n${consent.items.map((item) => item.name).join("、")}\n商户：${consent.merchantId}\n金额：${money(consent.amountMinor, consent.currency)}\n\nSIMULATED / OFFLINE：不会发生真实付款。`)) return;
    const response = await api("/api/payments", {
      ownerId: OWNER,
      taskId: consent.taskId,
      consentId,
      idempotencyKey: `ui-${crypto.randomUUID()}`,
      outcome,
    });
    showNotice(`成功：${labels[response.result.status]}。`);
    await refresh();
  } catch (error) { showNotice(error.message); }
}

async function revoke(consentId) {
  try {
    await api("/api/consents/revoke", { ownerId: OWNER, consentId });
    showNotice("待执行授权已撤销。");
    await refresh();
  } catch (error) { showNotice(error.message); }
}

async function reconcile(paymentId) {
  try {
    const response = await api("/api/payments/reconcile", { paymentId });
    showNotice(`对账完成：${labels[response.result.status]}。重复查询不会重复扣款。`);
    await refresh();
  } catch (error) { showNotice(error.message); }
}

async function fulfill(paymentId) {
  try {
    const response = await api("/api/payments/fulfill", { ownerId: OWNER, paymentId });
    showNotice(`履约状态：${response.result.fulfillmentStatus}（模拟）。`);
    await refresh();
  } catch (error) { showNotice(error.message); }
}

async function refund(paymentId, amountMinor) {
  try {
    const response = await api("/api/payments/refund", {
      ownerId: OWNER,
      paymentId,
      amountMinor,
      idempotencyKey: `refund-${crypto.randomUUID()}`,
    });
    showNotice(`退款已模拟；${response.result.currency} 预算已恢复。`);
    await refresh();
  } catch (error) { showNotice(error.message); }
}

document.querySelectorAll("[data-journey]").forEach((tab) => tab.addEventListener("click", () => {
  currentJourney = tab.dataset.journey;
  document.querySelectorAll("[data-journey]").forEach((button) => {
    const active = button === tab;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", String(active));
  });
  refresh();
}));
document.querySelector("#reset").addEventListener("click", async () => {
  if (!window.confirm("清除本地模拟交易并恢复初始合成预算？")) return;
  await api("/api/reset", {});
  showNotice("本地模拟状态已重置。");
  await refresh();
});
refresh().catch((error) => showNotice(error.message));
