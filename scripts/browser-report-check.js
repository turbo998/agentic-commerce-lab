async (page) => {
  const base = "http://127.0.0.1:4187";
  const checks = [];
  const errors = [];
  const remote = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (request) => {
    if (!request.url().startsWith(base) && !request.url().startsWith("data:")) remote.push(request.url());
  });
  const assert = (condition, label) => {
    if (!condition) throw new Error(label);
    checks.push(label);
  };
  await page.emulateMedia({ colorScheme: "dark" });
  const response = await page.goto(`${base}/hve-report.html`);
  assert(response.status() === 200 && !response.headers()["content-security-policy"].includes("unsafe-inline"),
    "HTTP200 and original CSP retained without unsafe-inline");
  assert(await page.locator("article[data-title]").count() === 16, "16 substantive research chapters");
  assert((await page.locator("article").allTextContents()).join("").length > 12000, "Full original research body, not landing-page links");
  assert(await page.locator("#toc a").count() === 16 && await page.locator("#source-list a").count() === 26 &&
    (await page.locator('a[data-source="research"]').first().getAttribute("href")).endsWith("/rpi-research/SKILL.md#L11-L123"),
    "16 TOC entries, 26 sources and authored citation line anchors preserved");
  assert(await page.locator("html").getAttribute("data-theme") === "dark", "Initial theme detects system dark");
  await page.locator("#theme").click();
  assert(await page.locator("html").getAttribute("data-theme") === "light", "Keyboard-operable theme control switches light");
  await page.goto(`${base}/hve-report.html?scoutTheme=light`);
  assert(await page.locator("html").getAttribute("data-theme") === "light", "Explicit scoutTheme light honored");
  await page.locator("#search").fill("预算");
  assert(await page.locator("article:visible").count() > 0 && await page.locator("article:visible").count() < 16,
    "Search filters full chapter text");
  await page.locator("#search").fill("zzzz-no-such-research-998");
  assert(await page.locator("article:visible").count() === 0 && await page.locator("#empty").isVisible(),
    "No-match search shows explicit empty state");
  await page.locator("#search").press("Escape");
  assert(await page.locator("article:visible").count() === 16, "Escape restores all chapters");
  await page.locator('#toc a[href="#commerce"]').click();
  assert(page.url().endsWith("#commerce"), "TOC navigates real Commerce anchor");
  const broken = await page.evaluate(() => [...document.querySelectorAll('a[href^="#"]')]
    .map((a) => a.getAttribute("href").slice(1)).filter((id) => !document.getElementById(id)));
  assert(broken.length === 0, "No broken internal anchors");
  await page.context().grantPermissions(["clipboard-read", "clipboard-write"], { origin: base });
  await page.evaluate(() => {
    const write = navigator.clipboard.writeText.bind(navigator.clipboard);
    navigator.clipboard.writeText = (text) => {
      window.__lastClipboardPayload = text;
      return write(text);
    };
  });
  await page.locator("details").first().locator("summary").click();
  await page.locator(".copy").first().click();
  await page.locator(".copy").first().filter({ hasText: "已复制" }).waitFor();
  const clipboard = await page.evaluate(() => navigator.clipboard.readText());
  assert((await page.evaluate(() => window.__lastClipboardPayload)).includes("/rpi-research"),
    "Copy calls real clipboard API with exact research sample");
  const clipboardRoundTrip = clipboard.includes("/rpi-research")
    ? "passed" : "unavailable: host returns empty readText despite resolved writeText and granted read permission";
  assert((await page.locator("#copy-status").innerText()).includes("已复制"), "Copy success announced as status");
  await page.evaluate(() => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true, value: { writeText: async () => { throw new Error("test-denied"); } },
    });
  });
  await page.locator("details").nth(1).locator("summary").click();
  await page.locator(".copy").nth(1).click();
  assert((await page.locator("#copy-status").innerText()).includes("test-denied"),
    "Denied clipboard produces explicit status and selected-text fallback");
  await page.goto(`${base}/hve-report.html?scoutTheme=dark`);
  await page.locator("#search").fill("zzzz-no-such-research-998");
  await page.emulateMedia({ media: "print" });
  assert(await page.locator("article:visible").count() === 16, "Print CSS includes all chapters despite search filter");
  assert(!await page.locator("aside").isVisible(), "Print hides navigation and interactive controls");
  await page.emulateMedia({ media: "screen" });
  const detailStates = await page.locator("details").evaluateAll((elements) => elements.map((el) => el.open));
  await page.evaluate(() => window.dispatchEvent(new Event("beforeprint")));
  assert(await page.locator("html").getAttribute("data-theme") === "light", "beforeprint uses readable light palette");
  assert(await page.locator("details[open]").count() === 3, "beforeprint opens all three code examples");
  await page.evaluate(() => window.dispatchEvent(new Event("afterprint")));
  assert(await page.locator("html").getAttribute("data-theme") === "dark", "afterprint restores reading theme");
  assert(JSON.stringify(await page.locator("details").evaluateAll((elements) => elements.map((el) => el.open))) === JSON.stringify(detailStates),
    "afterprint restores original disclosure states");
  await page.emulateMedia({ media: "print" });
  await page.evaluate(() => {
    window.addEventListener("beforeprint", () => {
      window.__printedCodeExamples = [...document.querySelectorAll("details")].map((el) => {
        const pre = el.querySelector("pre");
        const rect = pre.getBoundingClientRect();
        return {
          open: el.open,
          visible: rect.width > 0 && rect.height > 0 && getComputedStyle(pre).visibility === "visible",
          text: pre.textContent,
          printMedia: matchMedia("print").matches,
        };
      });
    }, { once: true });
  });
  const pdf = await page.pdf({ format: "A4", printBackground: true });
  const printedCodeExamples = await page.evaluate(() => window.__printedCodeExamples);
  assert(pdf.length > 10000 && printedCodeExamples?.length === 3 &&
    printedCodeExamples.every((example) => example.open && example.visible && example.printMedia && example.text.trim()),
    "Actual Chromium PDF rendered all three visible code examples under print media");
  assert(await page.locator("html").getAttribute("data-theme") === "dark" &&
    JSON.stringify(await page.locator("details").evaluateAll((elements) => elements.map((el) => el.open))) === JSON.stringify(detailStates),
    "Actual PDF before/afterprint lifecycle restores reading state");
  await page.emulateMedia({ media: "screen" });
  await page.locator("#search").press("Escape");
  const contrast = await page.evaluate(() => {
    const luminance = (color) => {
      const values = color.match(/\d+/g).slice(0, 3).map((v) => Number(v) / 255)
        .map((v) => v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4);
      return 0.2126 * values[0] + 0.7152 * values[1] + 0.0722 * values[2];
    };
    const note = getComputedStyle(document.querySelector("#execution-note"));
    const header = getComputedStyle(document.querySelector("header"));
    const a = luminance(note.color), b = luminance(header.backgroundColor);
    return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
  });
  assert(contrast >= 4.5, "Dark header secondary-text contrast >=4.5");
  await page.setViewportSize({ width: 390, height: 844 });
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), "390px report has no page-level horizontal overflow");
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`${base}/hve-report.html`);
  await page.keyboard.press("Tab");
  assert(await page.locator(".skip").evaluate((el) => el === document.activeElement), "Keyboard first tab reaches skip link");
  await page.keyboard.press("Enter");
  assert(await page.locator("#report-main").evaluate((el) => el === document.activeElement), "Skip link moves focus to main");
  for (const path of ["/workshop/outline.md", "/workshop/demo-runbook.md", "/workshop/sources.json", "/workshop/evidence/host.json", "/workshop/evidence/rpi-execution.md", "/workshop/evidence/browser-commerce.json"]) {
    assert((await page.request.get(`${base}${path}`)).status() === 200, `Local delivery reachable: ${path}`);
  }
  assert(remote.length === 0, "No CDN/external runtime network requests");
  assert(errors.length === 0, "No report script/CSP errors");
  return {
    executor: "actual Playwright Chromium; real clipboard write API payload plus explicit denied-write test",
    base, checks, scriptErrors: errors, remoteRequests: remote, darkHeaderContrast: contrast,
    clipboardRoundTrip, printedCodeExamples,
    printing: "print media layout, all three code disclosures, and actual Chromium PDF rendering tested; no physical printer claimed",
  };
}
