const API = "/api/commerce/v1";
const params = new URLSearchParams(location.search);
let identity;

async function request(path, body, role = "human") {
  const token = role === "human" ? identity.humanToken : identity.agentToken;
  const response = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers: {
      ...(body === undefined ? {} : { "content-type": "application/json" }),
      authorization: `Bearer ${token}`,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.message ?? result.error ?? `HTTP ${response.status}`);
  return result;
}

const money = (minor, currency) => {
  const divisor = currency === "USDC" ? 1_000_000 : 100;
  if (currency === "USDC") return `${(minor / divisor).toFixed(6)} USDC`;
  return new Intl.NumberFormat("zh-Hans", { style: "currency", currency }).format(minor / divisor);
};

function showError(error) {
  document.querySelector("#consent-result").textContent = `未完成：${error.message}`;
}

function showActions(html) {
  document.querySelector("#consent-actions").innerHTML = html;
}

async function loadConsentRequest(id) {
  const item = await request(`${API}/consent-requests/${encodeURIComponent(id)}`);
  document.querySelector("#consent-details").innerHTML = `
    <article class="payment">
      <div><h2>逐笔购买授权请求 <span class="status">${item.status}</span></h2>
      <p><strong>商户：</strong>${item.merchantId}<br>
      <strong>商品：</strong>${item.items.map((entry) => `${entry.name} × ${entry.quantity}`).join("、")}<br>
      <strong>总额：</strong>${money(item.amountMinor, item.currency)} (${item.currency})<br>
      <strong>任务：</strong>${item.taskId}<br>
      <strong>报价版本：</strong>${item.quoteVersion}<br>
      <strong>任务限额：</strong>${money(item.budgetLimit.amountMinor, item.budgetLimit.currency)} ${item.budgetLimit.currency}<br>
      <strong>到期：</strong>${new Date(item.expiresAt).toLocaleString()}<br>
      <strong>权限：</strong>仅本 task/merchant/items/amount/currency/quote 版本，不增加预算，不授权其他订单。</p></div>
    </article>`;
  if (item.status !== "pending") {
    showActions(`<a class="button primary" href="/">返回对话和状态</a>`);
    return;
  }
  showActions(`
    <button id="approve" class="button primary">批准此精确报价</button>
    <button id="deny" class="button secondary">拒绝</button>`);
  document.querySelector("#approve").addEventListener("click", async () => {
    try {
      const approved = await request(`${API}/consent-requests/${encodeURIComponent(id)}/approve`, {}, "human");
      const result = approved.result;
      if (result.consent.quoteId === "travel-guide") {
        const delivered = await request(`${API}/resources/travel-guide`, {
          taskId: result.request.taskId,
          consentRequestId: id,
          challengeId: result.request.resourceChallengeId,
        });
        await loadConsentRequest(id);
        document.querySelector("#consent-result").textContent =
          `授权后资源 retry 完成。SIMULATED receipt ${delivered.result.payment.receipt.id}；资源 ${delivered.result.delivery.id}。`;
      } else {
        const executed = await request(`${API}/consents/${encodeURIComponent(result.consent.id)}/execute`, {}, "human");
        await loadConsentRequest(id);
        document.querySelector("#consent-result").textContent =
          `授权后 workflow 已执行。SIMULATED receipt ${executed.result.payment.receipt?.id ?? "待对账"}；状态 ${executed.result.payment.status}。`;
      }
    } catch (error) {
      await loadConsentRequest(id).catch(showError);
      showError(error);
    }
  });
  document.querySelector("#deny").addEventListener("click", async () => {
    try {
      await request(`${API}/consent-requests/${encodeURIComponent(id)}/deny`, {}, "human");
      await loadConsentRequest(id);
      document.querySelector("#consent-result").textContent = "已拒绝。没有创建付款或使用预算。";
    } catch (error) {
      await loadConsentRequest(id).catch(showError);
      showError(error);
    }
  });
}

async function loadRefundRequest(id) {
  const item = await request(`${API}/refund-requests/${encodeURIComponent(id)}`);
  document.querySelector("#consent-details").innerHTML = `
    <article class="payment"><div><h2>退款人工复核 <span class="status">${item.status}</span></h2>
    <p><strong>原交易：</strong>${item.paymentId}<br>
    <strong>申请金额：</strong>${money(item.amountMinor, item.currency)}<br>
    仅退还原交易未退款余额，不会超过原捕获金额。</p></div></article>`;
  if (item.status !== "pending") {
    showActions(`<a class="button primary" href="/">返回交易状态</a>`);
    return;
  }
  showActions(`<button id="approve-refund" class="button primary">批准退款申请</button>`);
  document.querySelector("#approve-refund").addEventListener("click", async () => {
    try {
      const result = await request(`${API}/refund-requests/${encodeURIComponent(id)}/approve`, {}, "human");
      await loadRefundRequest(id);
      document.querySelector("#consent-result").textContent =
        `退款已模拟批准。交易 ${result.result.payment.status}；预算按幂等键恢复。`;
    } catch (error) { showError(error); }
  });
}

async function initialize() {
  document.querySelector("#human-start").addEventListener("click", async () => {
    try {
      const response = await fetch("/api/demo/human-session", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ persona: "alex" }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.message ?? "无法创建合成本地人工会话");
      identity = result;
      document.querySelector("#consent-identity").textContent =
        `Synthetic human role · ${identity.subject}@${identity.tenantId} · 仅本地演示`;
      document.querySelector("#human-start").hidden = true;
      document.querySelector("#human-workspace").hidden = false;
      if (params.has("request")) return loadConsentRequest(params.get("request"));
      if (params.has("refund")) return loadRefundRequest(params.get("refund"));
      document.querySelector("#consent-details").textContent = "缺少待审核请求编号。请从主对话进入审批链接。";
    } catch (error) { showError(error); }
  });
}

initialize().catch(showError);
