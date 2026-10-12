# 一小时分享 Demo 操作手册

**完成版本业务Demo可直接运行；VS Code + Copilot Chat路径需主讲人实际预检。**本次真实开发host是Copilot App/CLI1.0.94-3加本机phase skills，见 [host.json](evidence/host.json)；未声称VS Code、固定upstream wrapper或Builder已执行。HVE research snapshot `49dfb738…` 与执行skill哈希是两种版本。

## 1. 克隆正确分支，不从空main重建

Node22+，本次验证Node24.13.1/npm11.8.0；原生HTTP/static/node:test，无第三方运行依赖，无密钥或付款账户。

```powershell
git clone --branch turbo998-hve-commerce-workshop https://github.com/turbo998/agentic-commerce-lab.git commerce-workshop
Set-Location .\commerce-workshop
node --version
npm run check
npm run test:e2e
npm run demo
```

若已在本隔离worktree，直接从`node --version`开始。`npm ci`不是运行前置（没有dependencies）；不需要先装React、Python服务或模型SDK。**分支完整复用尚未合并PR #1，材料在stacked PR中，未合并main。**

打开 <http://127.0.0.1:4187>，研究页 <http://127.0.0.1:4187/hve-report.html>。`npm run demo`固定使用本checkout的`data/workshop-state.json`，不读取/覆盖`data/state.json`。默认`npm start`仍是原4173与默认state，不用于本次分享。不要同时启两个workshop进程写同一JSON文件。

端口被占用不自动杀进程；选自己空闲端口：

```powershell
$env:PORT = '4188'
npm run demo
```

`$env:PORT`仅在当前PowerShell进程及其后启动的子进程中生效，新开终端需重新设置。恢复默认端口可在当前终端执行`Remove-Item Env:PORT`；浏览器测试固定4187，换端口时需修改脚本base或现场手动走查，不假称4187脚本验证了4188。

## 2. 预演前flight与限定reset

使用loopback，不隧道公网，不输入卡号、真实身份、支付凭证或财务资料。先确认日志是专用workshop、state路径正确、页面SIMULATED/OFFLINE。检查自身服务：

```powershell
Invoke-WebRequest -Uri 'http://127.0.0.1:4187' -TimeoutSec 10 | Select-Object StatusCode
Get-NetTCPConnection -LocalPort 4187 -State Listen | Select-Object LocalAddress,LocalPort,OwningProcess
```

推荐页面“重置本地模拟”，接受提示，仅对该服务合成tenant状态操作。不要对默认4173做reset。若需文件级干净开始，先在**自己的**server终端Ctrl+C，确认自己的实例已停，再执行窄范围删除：

```powershell
if (Get-NetTCPConnection -LocalPort 4187 -State Listen -ErrorAction SilentlyContinue) {
  throw '4187仍有监听者：先核对并停止自己的workshop实例；不要删除运行中的状态'
}
if (Test-Path -LiteralPath '.\data\workshop-state.json') {
  Remove-Item -LiteralPath '.\data\workshop-state.json'
}
npm run demo
```

禁止删除整个data目录、`data/state.json`、任何别的checkout或服务文件。若使用其他端口，停止检查也要对应改变。若后台保留服务，记录自己的shellId/PID，最后按该实例停止；不要按Node/npm进程名批量kill。

## 3. 业务演示顺序：约9分钟核心操作

先不要点目录“加入任务比较”，否则任务只比较所选单报价。周末旅程，USD，上限70，目标“比较周末购物”：

| 步骤 | 操作 | 预期/应说的话 |
|---|---|---|
| 1 | 生成70USD任务 | camera5999、coffee1899两个按钮；headphones7999，OVER_BUDGET/超限999（USD9.99） |
| 2 | 指出解释与限额 | 每个候选单独合格，不代表合并购物车或可用余额；budgetHeadroomMinor不是付款权限 |
| 3 | camera“请求人工批准” | pending request，付款尚未发生；agent不能approve |
| 4 | 审批链接在另一标签页打开 | 点击“启动本地人工演示会话”，核对商户/明细/精确金额/币种/version/task限额后“批准此精确报价” |
| 5 | 观察模拟captured receipt | 此页approve后原workflow执行；没有真实支付。返回原标签页保留同task的coffee按钮 |
| 6 | 同task请求coffee | 累计预算拒绝；camera5999后剩1001，coffee1899不足。不要新建task代替这个验收 |
| 7 | 新task USD10 | suggestions空、no_action、三个超预算说明，没有批准按钮 |
| 8 | 选择camera再改限额币种HKD | TASK_BUDGET_CURRENCY_MISMATCH，明确无FX；不是跨币种授权建议 |
| 9 | 重置专用状态 | 清陈旧task按钮，恢复合成余额，不影响默认服务 |

旅程额外备查：travel/HKD88有hotel与transit；travel/USDC1.2只推荐guide，其他币种排除，HTTP402-shaped仍按原独立批准流程工作。这不是完整MPP/x402或供应商interop。

### 幂等观察：只读状态与同consent重放

在**此专用Demo页**DevTools执行；不打印tokens，不把变量或状态文件发给第三方。这段仅验证本地合成consent，在camera已经审批执行后、reset前运行：

```javascript
const identity = JSON.parse(sessionStorage.getItem("commerce-demo-identity"));
const headers = { authorization: `Bearer ${identity.agentToken}` };
const status = async () => (await fetch("/api/commerce/v1/status", { headers })).json();
const before = await status();
const request = before.consentRequests.find(r => r.quoteId === "weekend-camera" && r.consentId);
if (!request) throw new Error("先在独立人工页批准camera");
const replay = await (await fetch(`/api/commerce/v1/consents/${request.consentId}/execute`, {
  method: "POST", headers: { ...headers, "content-type": "application/json" }, body: "{}"
})).json();
const after = await status();
console.table({
  samePayment: replay.result.payment.id === before.payments[0].id,
  sameBalance: after.balances.USD === before.balances.USD,
  sameEvents: after.events.length === before.events.length
});
```

三项true，不重复副作用。不得把DevTools调用视作生产鉴权或人审设计。

## 4. 自动验证不是现场吹嘘

```powershell
node --test test\agent.test.js test\budget-http.test.js
npm run check
npm run test:e2e
```

第一项覆盖准确金额/理由码、边界相等/差1minor、币种/取消、注入事实/动作、输入mutation、HTTP无task/payment副作用、累计权限和双服务状态隔离。后两项保留原回归。`test:e2e`实际是HTTP/restart测试，**不是浏览器测试**。

实际UI测试函数在 `scripts/browser-commerce-check.js`，可由Playwright MCP `browser_run_code_unsafe`的filename加载，或在获准的本地Playwright测试host调用该async function。只指向专用4187，会reset该服务；reset confirm由测试stub接受，精确商业人审仍实际点击。它返回13条断言，详见 [browser-commerce.json](evidence/browser-commerce.json)。没有Playwright host时手动执行上表并登记结果，不把Node tests称作UI已验证。

## 5. HVE / VS Code演示前检查

记录`code --version`、Copilot Chat extension版本、模型、session/harness、HVE安装来源/渠道/version或SHA、相关设置与个人同名定制。此仓库不自动修改你的全局Copilot配置。

```powershell
code --version
code --list-extensions --show-versions |
  Select-String 'GitHub.copilot|ise-hve-essentials.hve-core'
```

VS Code Marketplace扩展主路径：安装`ise-hve-essentials.hve-core`，Copilot Chat选**RPI Agent**，核对四个phase入口。Stable/PreRelease exact tag与main研究不能混同。若旧扩展缺所需skill，使用团队选定的固定peer clone/selective adoption并按官方方法配置发现；不要把下载main当Stable行为。CLI插件跟踪main，且其instructions不自动应用，不在用户现有全局环境偷换版本。

三种独立证据：customization发现、本次References/skill调用、tool activity/actual artifact与验收。没有亲自完成VS Code步骤，只标“待复现”；本次已有Copilot App/CLI phase执行可作真实备用。

## 6. 开始/完成状态与安全的开发复演

开始revision：`7c5d931f38a1743be7d99e99324755ae2a176693`；feature完成：`d39a5d4e5a1336b171526436dd6ae66f7e4d64f1`；完整材料用本分支最终HEAD。**不要reset当前工作区回开始，不修改原PR #1会话。**

需要展示开发增量时，在当前checkout的ignored data下建立专门开始worktree：

```powershell
git worktree add --detach .\data\workshop-start 7c5d931f38a1743be7d99e99324755ae2a176693
code .\data\workshop-start
```

该开始版本无新增workshop脚本/H5/instructions；让Copilot只在新开始worktree操作，不在完成版本“再实现一次”。不要把新开始worktree与当前已经验证的完整Demo混同。若需要演示baseline业务，另终端进入其目录用`npm start`，自行空端口；状态在该独立worktree，勿重用完成服务的JSON文件。仅创建一次，存在时不覆盖/删除。不得在主checkout执行这些操作。

## 7. 真正的RPI输入与人工决策

以下是教学输入，**不是伪称上游自动产出的artifact**。RPI Agent wrapper在当前版本按task身份管理状态；独立skills按实际合同输出。读取本次 [rpi-execution.md](evidence/rpi-execution.md) 可见真实预演次序/失败/修正，不反向补造历史。

Research输入：

```text
/rpi-research
研究这个Node离线Commerce基线。只读planner、输出校验、task API、UI和相关测试。
目标：旅程/币种一致，单报价amountMinor <= structured task limit才可推荐；
USD7000应有camera5999与coffee1899，headphones7999解释超额999；
USD1000为no_action。保留人工批准、累计预算/预留、余额、幂等。
核实代码事实、备选、未知与planning readiness；不要实现。
```

Plan输入：

```text
/rpi-plan
使用同一task已经完成的research，列出可检查Requirements与依赖。
只改推荐/校验/解释UI，Authority不扩权。
有效旧injected planner兼容；坏事实、超预算和approve动作显式拒绝。
Planner只能修改自己的输入副本，不能改变服务器保留的预算或范围；返回建议仍按原请求校验。
计划default critique，纠正阻断finding，再推进Implementation。
```

人工决策重点：是否允许新服务/模型/FX（本任务不允许）；候选是单笔还是购物车（已确认单笔）；exclusion与selected wrong-currency error区分；server-owned request不能交给planner修改。当前critique deep不能由复杂度自选。

Implement输入使用**本次实际创建的plan路径和marker**，不要照抄别人的日期/slug：

```text
/rpi-implement
执行刚完成critique且implementation-ready的当前任务计划。
先完成预算recommendation与validator任务，记录实际tests/changes；
遇到重大范围/授权语义变化先停止受影响任务并返回决策。
```

Review输入：

```text
/rpi-review
对当前task Requirements、accepted direction、changes和真实验证逐项对账。
区别HTTP tests、browser、source contract、VS Code未执行。
给出execution status与outcome、finding的resolve条件及去向；不要直接修代码。
```

当前fixed upstream示例产物：dated research、单plan、plan-critique、changes、review log，以及wrapper state指针；实际旧本机skills可能产生details/line-ref plan等不同结构。先看实际已加载合同，不重命名文件制造当前版本执行假象。原始tracking忽略；教学只发布经审阅摘要。

## 8. 上下文恢复与失败备用

新上下文给同一整体task身份、实际research/plan/changes/review文件及当前accepted direction；先读canonical artifacts和当前marker，不机械重复Research。上游wrapper规定next_action前后持久化，不是事务保证；写失败应停止而非重放已完成阶段。

Copilot网络/权限/入口失败：说明具体host限制，展示本次真实预演evidence和本地完整业务Demo；不要现场造文件冒充VS Code输出。支付模拟失败：显示真实error/状态；用专用reset重跑，不抹除未知状态说明。H5无网络仍可读；来源链接是引用而非运行依赖。

## 9. 主讲前最终签收

打开H5目录、搜索无匹配/清空、复制、深浅色、键盘跳读和打印；打开source register；确认60分钟outline；跑focused/full/HTTP e2e；从专用干净状态重走业务表；确认loopback与默认state不变。浏览器/打印/clipboard证据不由文件存在推断。

服务需要留用时以自己的detached实例保留并给URL；不用时只停止该PID/shellId。新PR应以`turbo998-agentic-commerce-lab`作stacked base，审阅增量，不合并、不开启自动merge。
