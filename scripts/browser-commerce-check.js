async (page) => {
  const base = "http://127.0.0.1:4187";
  const checks = [];
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const assert = (value, label) => {
    if (!value) throw new Error(label);
    checks.push(label);
  };
  await page.goto(base);
  await page.locator("#identity-label").filter({ hasText: "alex" }).waitFor();
  await page.evaluate(() => { window.confirm = () => true; });
  await page.locator("#reset").click();
  await page.locator("#notice").filter({ hasText: "已重置" }).waitFor();
  const submit = async (amount, goal = "比较合成报价") => {
    await page.locator("#goal").fill(goal);
    await page.locator("#budget-amount").fill(amount);
    await page.locator("#task-form button[type=submit]").click();
  };
  await submit("70");
  await page.locator('[data-exclusion="weekend-headphones"]').waitFor();
  assert(await page.locator("[data-request-consent]").count() === 2, "USD70: exactly camera and coffee buttons");
  assert((await page.locator('[data-exclusion="weekend-headphones"]').innerText()).includes("9.99"), "USD70: exact USD9.99 shortfall");
  assert((await page.locator("#conversation").innerText()).includes("不代表同时购买全部候选"), "UI distinguishes candidate from basket/authorization");
  await page.locator('[data-request-consent="weekend-camera"]').click();
  await page.locator("#consents a").waitFor();
  const pending = await page.evaluate(async () => {
    const identity = JSON.parse(sessionStorage.getItem("commerce-demo-identity"));
    const headers = { authorization: `Bearer ${identity.agentToken}` };
    const state = await (await fetch("/api/commerce/v1/status", { headers })).json();
    const request = state.consentRequests.find((entry) => entry.quoteId === "weekend-camera");
    const approval = await fetch(`/api/commerce/v1/consent-requests/${request.id}/approve`, {
      method: "POST", headers: { ...headers, "content-type": "application/json" }, body: "{}",
    });
    const execute = await fetch(`/api/commerce/v1/consents/${request.id}/execute`, {
      method: "POST", headers: { ...headers, "content-type": "application/json" }, body: "{}",
    });
    return { payments: state.payments.length, approvalStatus: approval.status, executeStatus: execute.status };
  });
  assert(pending.payments === 0 && pending.approvalStatus === 403 && pending.executeStatus === 404,
    "Pending request: no payment; agent approval403/unapproved execute404");
  const href = await page.locator("#consents a").getAttribute("href");
  const approvalPage = await page.context().newPage();
  await approvalPage.goto(`${base}${href}`);
  await approvalPage.locator("#human-start").click();
  await approvalPage.locator("#approve").click();
  await approvalPage.locator("#consent-result").filter({ hasText: "SIMULATED receipt" }).waitFor();
  assert((await approvalPage.locator("#consent-result").innerText()).includes("captured"), "Independent human page executes synthetic capture");
  await approvalPage.close();
  const replay = await page.evaluate(async () => {
    const identity = JSON.parse(sessionStorage.getItem("commerce-demo-identity"));
    const headers = { authorization: `Bearer ${identity.agentToken}` };
    const status = async () => (await fetch("/api/commerce/v1/status", { headers })).json();
    const before = await status();
    const consentId = before.consentRequests.find((entry) => entry.quoteId === "weekend-camera").consentId;
    const result = await (await fetch(`/api/commerce/v1/consents/${consentId}/execute`, {
      method: "POST", headers: { ...headers, "content-type": "application/json" }, body: "{}",
    })).json();
    const after = await status();
    return {
      samePayment: result.result.payment.id === before.payments[0].id,
      sameEvents: after.events.length === before.events.length,
      sameBalance: after.balances.USD === before.balances.USD,
      remainingMinor: after.tasks.find((entry) => entry.id === before.payments[0].taskId).budgetUsage.remainingMinor,
    };
  });
  assert(replay.samePayment && replay.sameEvents && replay.sameBalance && replay.remainingMinor === 1001,
    "Same-consent replay: one payment, unchanged events/balance, remaining1001");
  await page.locator('[data-request-consent="weekend-coffee"]').click();
  await page.locator("#notice").filter({ hasText: "结构化限额" }).waitFor();
  assert((await page.locator("#tool-trace").innerText()).includes("rejected"), "Camera then coffee: cumulative runtime rejection shown");
  await submit("10");
  await page.locator("[data-no-action]").waitFor();
  assert(await page.locator("[data-request-consent]").count() === 0, "USD10: no action button");
  assert(await page.locator("[data-exclusion]").count() === 3, "USD10: three explained exclusions");
  await page.locator('[data-select="weekend-camera"]').click();
  await page.locator("#budget-currency").selectOption("HKD");
  await submit("70");
  await page.locator("#notice").filter({ hasText: "币种" }).waitFor();
  assert((await page.locator("#notice").innerText()).includes("不会"), "Selected mismatched currency: explicit error, no FX");
  await page.locator("#budget-currency").selectOption("USD");
  await submit("70", "<img src=x onerror=alert(1)>");
  await page.locator('[data-request-consent="weekend-camera"]').waitFor();
  assert(await page.locator("#conversation img").count() === 0, "Untrusted summary HTML is escaped");
  await page.locator("#reset").click();
  await page.locator("#notice").filter({ hasText: "已重置" }).waitFor();
  assert(await page.locator("[data-request-consent]").count() === 0, "Workshop reset clears stale action buttons");
  assert(errors.length === 0, "No browser script errors");
  const result = { mode: "actual Playwright Chromium UI and same-origin HTTP; reset confirmation accepted by test stub", base, checks, errors, replay };
  await page.evaluate((value) => { window.__commerceCheckResult = value; }, result);
  return result;
}
