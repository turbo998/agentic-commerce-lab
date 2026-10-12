# 真实预演证据：Commerce预算推荐与HVE分享

研究/开发日期：2026-10-12。**这是实际工具执行之后整理的原创脱敏摘要，不是伪造的上游artifact、VS Code运行日志或现场生成承诺。**原始阶段文件在开发时依次产生并被gitignore；只公开可核对的事实、结果和必要限制，不公开tokens、身份文件或整段会话。

## 开始与完成检查点

开始：PR #1固定 `7c5d931f38a1743be7d99e99324755ae2a176693`。完整继承Node基线；工作树干净；PR #1/#4在线head与批准计划一致。功能检查点：`d39a5d4e5a1336b171526436dd6ae66f7e4d64f1`。材料完成状态以最终提交和stacked PR为准，不把未合并资产描述成main已有能力。

在动应用源码前，用原生Node调用proposeTask，USD7000得到5999、1899、7999三个报价，exclusions为空。**已证明的是推荐质量缺口，不是支付授权绕过。**基线原check24/24、原HTTP e2e2/2。

## 顺序1：实际Research

加载user-scoped `rpi-research`，先读批准范围、原源码/API/UI/测试，再写Research文档。实际旧skill要求有dispatch工具时委派Researcher，因而只委派一个有边界PR4概念研究：固定revision、proposal/authority、exact binding、replay和来源不等于permission。

Researcher用gh取固定资料，返回带路径/行号的证据，**没有写出请求的subagent文件**。主上下文据实记录这个限制并合入研究；Python测试只读未运行。父级提供固定HVE源码研究，核对当前phase skills、wrapper、state、Builder和VS Code合同；这是source-contract研究，不是VS Code执行。

选择：同一确定性eligibility供offline planner和server validator使用；服务器从固定目录计算解释；有效旧mock不必新增字段。拒绝：静默过滤坏planner成成功、自由文本预算、FX、降价、新Python/React/SDK服务。

## 顺序2：实际Plan与critique，均在应用修改前

加载 `rpi-plan`，写计划/details/log。Plan Validator实际只读计划，发现：

| Finding | 级别 | 纠正 |
|---|---|---|
| 将rpi-implement激活列在T1/T2代码修改之后，且Review未覆盖材料 | High | 激活移到首个应用编辑前；最终Review放到完整代码与材料之后 |
| 15研究问题未枚举，上游依赖未界定 | High | 逐项Q1–Q15与source coverage；材料源核对在材料阶段收口，不阻塞已充分的feature research |
| selected wrong-currency契约需显式保持 | Medium | 新增TASK_BUDGET_CURRENCY_MISMATCH回归，与目录exclusion分开 |
| workshop reset不能影响默认状态/另一服务 | Medium | 独立状态launcher、两个同时运行服务文件不变断言与实际默认state不存在检查 |

尝试同sync validator follow-up，host明确拒绝：write_agent只支持background agent。没有再启动一个validator；主上下文针对已纠正finding做inline复核并据实标记，而非声称第二次独立Pass。

## 顺序3：实际Implement和验证迭代

`rpi-implement`在首个应用编辑前显式加载并记录start。按已就绪计划改agent.js、UI、专用launcher和相关测试。Payment Authority未修改。主上下文做精确inline实现，不声称Phase Implementor已派发。

Implementation Validator实际执行命令：focused10/10；full check32/33；后续e2e因`&&`未执行。失败来自旧fixture：guide价格1.2USDC，但统一限额200000minor=0.2USDC仍期待proposed。修正事实向量的“可负担”夹具为至少所选报价额，保留事实/权限断言；新增专门低于/等于边界测试，不放宽validator。

父级审查同时发现input ownership风险：planner收到server request同一对象可修改budget/quote scope。改为 `planner.propose(structuredClone(request))`，validate/persist保留server-owned normalized original；unit覆盖预算/quote/journey/goal/owner变更，HTTP覆盖mutating overbudget planner不存task、不付款。并使null suggestion返回结构化PLANNER_OUTPUT_INVALID。

纠正后focused12/12、full check35/35、原e2e2/2。23固定混合评估向量仍通过；这些是确定性合成夹具结果，不是模型真实准确率或HVE提效实验。

## 顺序4：实际浏览器与隔离运行

实际 `npm run demo` detached启动在loopback4187，独立`data/workshop-state.json`；HTTP200与监听127.0.0.1确认；默认`data/state.json`仍不存在。只操作本worktree自己的workshop实例，没有停其他服务。

Playwright Chromium实际UI与同源HTTP完成13条断言，见 [browser-commerce.json](browser-commerce.json)。独立审批页面实际点击human session和approve，产生模拟captured receipt。camera执行后同task剩1001minor；coffee1899被累计权限拒绝。重复同consent得到同payment，余额和events不变。USD10无候选，selected mismatch有错误，文本转义和reset清过期按钮均验证。

首轮自动检查被modal harness与“超出/超过”选择器阻住；改为测试接受reset confirm、精确等待现有错误文案后完整重跑。**reset确认由stub接受；商业人审没有被stub绕过。**403/404/400是断言所需的预期HTTP拒绝，不是script exception。截图只辅助视觉，不替代断言。

## 材料与来源整合

父级并行原创H5正文：16章、26来源。收到已修正暗色对比度的scratch后，用一次可审计自动拆分保持原文，将CSS、首个theme boot和正文JS外置；未加unsafe-inline，保留原静态CSP。原scratch SHA256：`ea89885ab85f343e4e9fa9f37548cde7b7d806698d3786440e8efed157b63d63`。整合后补实际执行口径、证据/手册入口和打印/无JS可读性；最终验证状态在Review收口。

详细outline24单元、连续60分钟；sources区分官方说明/source contract/local execution/advice；runbook区分开始/完成revision、VS Code待复现、业务mock与实际开发host。

最终完整check38/38、原HTTP e2e2/2；新增3项分别对账连续60分钟、26引用/15问题映射与host类型，以及七文件静态白名单/不可访问私有路径。首轮37/38是新增测试错误地只识别ASCII括号，实际中文大纲全角括号；修正测试格式识别后38/38，不修改已接受的议程。

H5实际Playwright35断言见 [browser-report.json](browser-report.json)：原CSP、零外部runtime请求、16章/26来源、检索/主题、390px、键盘skip和contrast5.88。打印由beforeprint暂存theme/disclosure并展开全部3个代码示例，afterprint精确恢复；实际Chromium PDF渲染执行。复制真实API载荷与拒绝时选中降级通过，但此浏览器host读回为空，OS round-trip记为unavailable，非Pass。没有实体打印机或全面WCAG认证声明。

## 顺序5：最终Review

完整材料、业务UI/H5/PDF与干净状态重启验证后，**实际加载user-scoped rpi-review**，哈希见host.json。按本机reference派发一次有边界RPI Validator，对五个计划阶段分别生成五份原始审查记录；再派发独立full-quality Implementation Validator。工具schema不能按自定义agent名选择，实际使用general-purpose task承担这两种明确角色，不声称运行了未提供的自定义Agent。所有npm/browser命令仍由主上下文实际执行，不由审查者代跑。

RPI对账1–4通过，5的验证与runbook通过、发布保持pending；质量审查approve_with_comments。合计初始0 Critical、0 High、1 Medium、3 Low：

| Finding | 原说明/问题 | 实施阶段纠正 |
|---|---|---|
| Medium input ownership讲述 | 大纲/runbook说输入mutation一律拒绝，但实际正确行为是副本隔离 | 说明合法建议可接受，原预算/范围不变；无效返回才PLANNER_OUTPUT_INVALID，不改变已通过的runtime |
| Low环境变量 | 新开PowerShell进程才保留PORT的说法错误 | 当前进程及其后启动子进程生效，新终端需重新设置 |
| Low引用精度 | JS重写href丢失作者的source line fragment | 保留原hash，并加入真实浏览器精确行锚点断言 |
| Low基线/最新口径 | 原README把24/24历史记录称为最新 | 明确PR1历史记录；本次最新38/38与独立浏览器证据分开 |

Review阶段只产出审查记录，结束后回到实施阶段做上述最小纠正。原始finding保留，不伪造初次零问题；随后只对这些纠正运行相关回归，不机械派发重复Review。永久commit/push/stacked PR在实际存在前不标Pass。

纠正后主上下文实际重新运行check38/38、原HTTP e2e2/2、git diff --check exit0；H5浏览器35断言再次通过，确认精确`#L11-L123`来源锚点，以及实际PDF中的Research/Implement/Instructions三示例均open/visible/printMedia true。四项finding的可检查resolving condition满足，剩余Critical/High/Medium/Low均0；不是第二位审查者的新零finding verdict。

操作手册干净重启也实际执行：只停止自有detached workshop进程，窄范围移除其专用文件，再`npm run demo`启动；状态在首次写入前可在内存初始化，不能把文件不存在误判为服务失败。认证status HTTP200，tasks0/payments0/consentRequests0；只监听127.0.0.1:4187，默认state仍不存在。最终服务保留给审阅，独立shell `hve-workshop-delivery`、验证PID34500。

## 版本与真实限制

实际host/skill哈希见 [host.json](host.json)。Copilot App/CLI报告1.0.94-3；Node24.13.1；npm11.8.0。执行skill的上游revision未知。未选固定current RPI Agent wrapper，未运行HVE Builder或VS Code Chat。所引用共享tracking instruction本机缺失，按已加载明确phase合同执行，已披露。

当前upstream与本机不同：currentResearch subagent never required、artifact由phase owner写、marker式单plan/单review与本机旧details/line-ref结构不同。不要把本次真实旧skill执行讲成当前wrapper保证。无模型密钥、无真实付款、无云部署、无生产认证、无量化提效实验。
