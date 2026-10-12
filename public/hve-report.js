
"use strict";
const hveSha = "49dfb73866f8c5f81bf734d6ca808dac25a2a330";
const hveBase = `https://github.com/microsoft/hve-core/blob/${hveSha}/`;
const commerceBase = "https://github.com/turbo998/agentic-commerce-lab/blob/7c5d931f38a1743be7d99e99324755ae2a176693/";
const sources = {
  "readme": ["HVE README：定位、原则、风险提示", hveBase + "README.md"],
  "architecture": ["AI Artifacts Architecture：职责与 manifest", hveBase + "docs/architecture/ai-artifacts.md"],
  "rpi-overview": ["RPI Overview：生命周期与最小入口", hveBase + "docs/rpi/README.md"],
  "rpi-agent": ["RPI Agent：模式、状态、停止与恢复", hveBase + ".github/agents/hve-core/rpi-agent.agent.md"],
  "research": ["Research SKILL：Goals / Flow / Success Criteria", hveBase + ".github/skills/rpi/rpi-research/SKILL.md"],
  "research-reference": ["Research Reference：Readiness / Optional helpers；213–221、246–257", hveBase + ".github/skills/rpi/rpi-research/references/research.md"],
  "plan": ["Plan SKILL：整体计划与 continuation", hveBase + ".github/skills/rpi/rpi-plan/SKILL.md"],
  "planning-reference": ["Planning Reference：ID、研究门槛、critique；51–65、170–226", hveBase + ".github/skills/rpi/rpi-plan/references/planning.md"],
  "critique": ["Plan Critique SKILL：PC findings 与只读范围", hveBase + ".github/skills/rpi/rpi-plan-critique/SKILL.md"],
  "implement": ["Implement SKILL：范围、决策、验证与恢复", hveBase + ".github/skills/rpi/rpi-implement/SKILL.md"],
  "implementation-reference": ["Implementation Reference：计划偏离；31–64、105–111", hveBase + ".github/skills/rpi/rpi-implement/references/implementation.md"],
  "review": ["Review SKILL：evidence reconciliation / routing", hveBase + ".github/skills/rpi/rpi-review/SKILL.md"],
  "review-reference": ["Review Reference：execution/outcome/finding；70–101", hveBase + ".github/skills/rpi/rpi-review/references/review.md"],
  "context-engineering": ["Context Engineering：上下文恢复与作者论述", hveBase + "docs/rpi/context-engineering.md"],
  "install": ["Installing HVE：安装选择与 gitignore", hveBase + "docs/getting-started/install.md"],
  "channels": ["HVE Identity and Channels：版本与 host 差异", hveBase + "docs/getting-started/packages.md"],
  "builder": ["HVE Builder：模式、质量门槛与边界", hveBase + ".github/skills/hve-core/hve-builder/SKILL.md"],
  "builder-extension": ["Extending HVE Builder：描述/阶段扩展；99–110、131–155", hveBase + ".github/skills/hve-core/hve-builder/references/extending-hve-builder.md"],
  "builder-types": ["Artifact Types：职责、成本、强制控制；9–56", hveBase + ".github/skills/hve-core/hve-builder/references/artifact-types.md"],
  "team": ["Team Adoption and Governance：渐进采用与衡量", hveBase + "docs/customization/team-adoption.md"],
  "vs-instructions": ["VS Code：Custom Instructions / Verify / Resolve conflicts", "https://code.visualstudio.com/docs/agent-customization/custom-instructions"],
  "vs-skills": ["VS Code：Agent Skills / inline / fork / discovery", "https://code.visualstudio.com/docs/agent-customization/agent-skills"],
  "commerce-pr1": ["Commerce PR #1：尚未合并的应用基线", "https://github.com/turbo998/agentic-commerce-lab/pull/1"],
  "commerce-pr4": ["Commerce PR #4：协议研究与 Python 实验参考", "https://github.com/turbo998/agentic-commerce-lab/pull/4"],
  "commerce-architecture": ["Commerce 固定基线架构与模拟限制", commerceBase + "docs/architecture.md"],
  "commerce-agent": ["Commerce 固定基线 planner / proposal validation", commerceBase + "src/agent.js"],
};
document.querySelectorAll("a[data-source]").forEach((link) => {
  const source = sources[link.dataset.source];
  if (!source) throw new Error(`Missing research source: ${link.dataset.source}`);
  link.href = source[1] + link.hash;
  link.title = source[0];
  link.target = "_blank";
  link.rel = "noopener noreferrer";
});
const sourceList = document.getElementById("source-list");
sourceList.replaceChildren();
for (const [id, [label, url]] of Object.entries(sources)) {
  const li = document.createElement("li");
  li.id = `source-${id}`;
  const a = document.createElement("a");
  a.href = url; a.textContent = label; a.target = "_blank"; a.rel = "noopener noreferrer";
  li.append(a); sourceList.append(li);
}
const articles = [...document.querySelectorAll("article[data-title]")];
const toc = document.getElementById("toc");
toc.replaceChildren();
for (const article of articles) {
  const li = document.createElement("li");
  const a = document.createElement("a");
  a.href = `#${article.id}`; a.textContent = article.dataset.title;
  li.append(a); toc.append(li);
}
const search = document.getElementById("search");
const searchStatus = document.getElementById("search-status");
const searchIndex = articles.map((article) => article.textContent.toLocaleLowerCase());
function filterChapters() {
  const query = search.value.trim().toLocaleLowerCase();
  let visible = 0;
  articles.forEach((article, i) => {
    const match = !query || searchIndex[i].includes(query);
    article.hidden = !match;
    toc.children[i].hidden = !match;
    if (match) visible++;
  });
  searchStatus.textContent = `显示 ${visible} / ${articles.length} 个章节`;
  document.getElementById("empty").hidden = visible !== 0;
}
search.addEventListener("input", filterChapters);
search.addEventListener("keydown", (event) => { if (event.key === "Escape") { search.value = ""; filterChapters(); } });
filterChapters();
window.addEventListener("hashchange", () => {
  const target = document.getElementById(window.location.hash.slice(1));
  if (target?.hidden) { search.value = ""; filterChapters(); target.scrollIntoView(); }
});
function updateThemeLabel() {
  document.getElementById("theme").textContent = document.documentElement.dataset.theme === "dark" ? "切换为浅色" : "切换为深色";
}
document.getElementById("theme").addEventListener("click", () => {
  document.documentElement.dataset.theme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  updateThemeLabel();
});
updateThemeLabel();
document.getElementById("print").addEventListener("click", () => {
  search.value = ""; filterChapters(); window.print();
});
let printState;
window.addEventListener("beforeprint", () => {
  printState ??= {
    theme: document.documentElement.dataset.theme,
    details: [...document.querySelectorAll("details")].map((element) => ({ element, open: element.open })),
  };
  document.documentElement.dataset.theme = "light";
  printState.details.forEach(({ element }) => { element.open = true; });
});
window.addEventListener("afterprint", () => {
  if (!printState) return;
  document.documentElement.dataset.theme = printState.theme;
  printState.details.forEach(({ element, open }) => { element.open = open; });
  printState = undefined;
  updateThemeLabel();
});
for (const pre of document.querySelectorAll("pre")) {
  const wrapper = document.createElement("div"); wrapper.className = "code-block";
  pre.before(wrapper);
  const button = document.createElement("button");
  button.type = "button"; button.className = "copy"; button.textContent = "复制示例";
  button.addEventListener("click", async () => {
    try {
      if (!navigator.clipboard?.writeText) throw new Error("当前浏览器不支持自动复制");
      await navigator.clipboard.writeText(pre.textContent);
      button.textContent = "已复制";
      document.getElementById("copy-status").textContent = "示例已复制到剪贴板。";
    } catch (error) {
      button.textContent = "复制失败，请选择示例文本";
      button.title = error.message;
      document.getElementById("copy-status").textContent = `复制失败：${error.message}。已选择示例文本，可手动复制。`;
      const selection = window.getSelection();
      const range = document.createRange(); range.selectNodeContents(pre);
      selection.removeAllRanges(); selection.addRange(range);
    }
  });
  wrapper.append(button, pre);
}
