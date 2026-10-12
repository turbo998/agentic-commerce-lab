# 从会用 Copilot，到可复现的 Agent 工程

**面向合作伙伴工程师的一小时分享详细大纲 · 2026-10-12**

定位：听众已有 GitHub Copilot 基础。HVE 是主角，Agentic Commerce 是贯穿实例。目标是让听众会选择工作流入口、分清建议与权限、把决策和验收变成团队资产；不是支付协议培训，不展示虚构生产接入。

本文件供 Cowork 制作演示文稿，**本交付不制作 PPT/PPTX**。下文 24 个“建议页面”是内容单元，可在制作时合并；不得删去版本、mock、实际 host 与未验证标识。每页保留一句主张，较长讲者展开放备注。图示请用原创关系图，不复制上游整页文档。配色由后续制作者选择，不必照搬报告网页。

## 时间与叙事

| 单元 | 时间 | 建议页面 | 核心作用 |
|---|---|---|---|
| 1–5 | 00:00–10:00 | 工程问题、两类 Agent、HVE 定位 | 建立正确预期 |
| 6–8 | 10:00–18:00 | 四类资产、上下文、生命周期 | 建立机制地图 |
| 9–12 | 18:00–28:00 | Research / Plan / Implement / Review | 解释推进门槛 |
| 13–15 | 28:00–34:00 | 版本、Commerce 架构、需求卡 | 建立 Demo 条件 |
| 16–18 | 34:00–46:00 | 真实预演证据与运行闭环 | 展示工程产出和业务边界 |
| 19–23 | 46:00–56:00 | 恢复、定制、采用、衡量、反模式 | 迁移到合作伙伴团队 |
| 24 | 56:00–60:00 | 收束与 Q&A | 带走可复现任务 |

来源编号见 [sources.json](sources.json)：H1–H4 为官方固定文档，W1–W12 为固定源码契约，W13–W14 为研究日 VS Code 在线文档，C1–C3 为 Commerce 参考，E1–E3 为本次执行/建议。所有 HVE 源码主张固定到 `49dfb73866f8c5f81bf734d6ca808dac25a2a330`；本次本机 phase skills 的来源 revision 未确定，使用 [host.json](evidence/host.json) 中哈希标识，**不是同一版本**。

## 1. 为什么生成了代码，任务仍未完成（00:00–02:00）

**目标：**把注意力从代码生成速度转向工程结果。**页面主张：**“能运行”只是一个门槛，需求覆盖、权限边界和交接复现仍要成立。

关键点：购物 Agent 可以找到看似合理的商品，但未必在预算内；单笔合格也未必允许一起买；权限判断不能依赖一句“请遵守预算”。提问听众：接手一段昨天生成的代码时，最缺的是代码还是决策背景？

图示：需求 → 建议 → 实现 → 验证 → 交接，每个箭头标一个容易丢失的信息。

讲者展开：“今天不是展示更长提示词。我们选一个非常小、能量化的缺口：USD70 的任务仍推荐 USD79.99 耳机。我要展示如何查清事实、计划受限变更、发现计划问题、实施并用不同证据对账。到结束时，大家应能解释为什么报价推荐不等于支付授权。”

证据：C1、E1 的原症状记录。转场：先拆开今天的两个 Agent，避免把开发工具与业务运行时混为一谈。

## 2. 两类 Agent：开发工程与商业任务（02:00–04:00）

**目标：**理解两个控制循环。**页面主张：**“Copilot 帮我们工程化开发；Commerce Agent 帮用户提出任务建议。”

关键点：工程层用真实 Copilot + 已加载 HVE phase skills读代码、留下计划、执行工具；业务层是确定性 `scripted-offline` planner、合成目录和模拟付款。没有模型密钥，也没有付费推理。

图示：上下两条泳道。上：工程需求 → Copilot/HVE → 代码/测试/证据；下：用户目标 → planner → 人审 → authority → 合成收据。代码由上层产生，权限不因此扩张。

讲者展开：“业务 Agent 的 mock 是有意取舍。它让现场不依赖配额、网络和支付环境，也让我们能精确讨论错误边界。这里的开发过程是真的，业务智能效果不是模型评测；不要把页面上类聊天的体验当 Microsoft 365 Copilot 或 Copilot Studio 集成。”

证据：C1/C2，README 安全边界，E1。转场：已有 Copilot 基础之后，为什么还需要组织上下文？

## 3. 五种常见工程成本（04:00–06:00）

**目标：**为 HVE 的机制找到真实问题。**页面主张：**“返工通常源于上下文和验收失真，而非缺少一句聪明提示词。”

关键点：重复解释仓库、把未知当事实、遗漏边界、把通过测试等同完整验收、交接后无法恢复判断。不要给这些成本虚构统一百分比。

图示：五张成本卡片，各附一个 Commerce 反例：忘记最小单位、跨币种、planner越权、候选购物车误读、重放副作用。

讲者展开：“本次完整回归曾失败一次。原因不是代码字段变多，而是旧评估向量给 USDC 指南 0.2USDC 预算，却期待价格1.2USDC的推荐成功。HVE 的价值不在永不失败，而在让失败、根因、修复和范围能够被审查。”

证据：E1 的 validation iteration；23 个向量只是合成夹具，不是现实模型准确率。转场：HVE 到底补了哪一层？

## 4. Copilot 是宿主能力，HVE 是工程资产（06:00–08:00）

**目标：**建立分层。**页面主张：**“HVE 组织开发过程，不替代模型、宿主或业务 runtime。”

关键点：模型生成/推理；host负责工具、权限、发现和上下文装载；customization负责规范/流程；业务程序负责确定性规则。HVE 不提供支付授权、数据库事务或供应商接入。

图示：模型 / Copilot host / HVE customization / 仓库代码四层，旁侧标示人类决策；用实线指向运行时校验，虚线表示指导。

讲者展开：“同一个 SKILL.md 在不同 harness 上，发现方式、工具权限和 fork 支持未必一样。所以‘文件存在’不是‘本次加载’，‘加载’不是‘必然遵守’，更不是‘运行时保证’。后续每个事实都会注明属于哪种证据。”

证据：H1、W11、W13、W14。转场：先读 HVE 的定位与警告，而不只摘宣传语。

## 5. HVE 的主张与采用边界（08:00–10:00）

**目标：**知道该借鉴什么、不能依赖什么。**页面主张：**“AI 承载规范，人保留判断。”

关键点：高度有主张的 agentic SDLC；上下文、治理、组织知识复用与一致实践；上游明确快速演进，优先作为模式和学习来源，不未经评估当稳定生产依赖。

图示：规则搬运给 AI；取舍、风险、验收留给人。底部一条“本团队拥有并维护自己的工程资产”。

讲者展开：“HVE 的核心不是让人退出。人应从重复解释规范，转向判断需求是否正确、计划是否够用、哪些风险可以接受。Builder 能帮助借鉴模式，但团队仍要选择版本、维护 owner、审查更新与许可证。”

证据：H1、H4。转场：这套框架具体由哪些资产组成？

## 6. Agents / Instructions / Skills / Prompts（10:00–13:00）

**目标：**按责任选择资产，避免一切都造 Agent。**页面主张：**“长期规则用 instructions，按需流程用 skill，角色/隔离才考虑 agent。”

关键点：instructions 是可附加的指导；skill以description被发现、按需加载SKILL.md/references；prompt是显式一次性入口；agent定义角色、工具与工作流边界。当前RPI入口以phase skills为主，不展示旧prompt清单冒充当前实现。

图示：2×2责任对照：长期/按需 × 规范/执行，旁列文件模式和一个最小 Commerce 实例。

讲者展开：“Commerce 只增加一份简短项目 instructions，写最小单位、建议不得批准、回归命令和状态隔离。没有新建 Finance Agent，因为这不会增加预算安全，反而可能增加派发成本。可复用复杂业务研究才有理由提取领域skill。”

证据：W10/W11、H3、W14，本项目 `.github/copilot-instructions.md`。转场：资产如何缓解对话上下文流失？

## 7. 上下文工程：对话不是事实数据库（13:00–15:00）

**目标：**知道什么要持久化。**页面主张：**“把已核实证据、决策和验证留成可引用产物，而非不断重述聊天。”

关键点：短期对话保留当前任务；研究保存证据/未知；计划保存验收/范围；changes保存实际修改和检查；review保存对账/决策。原始 tracking应忽略，公开教学只保留脱敏原创摘要。

图示：对话工作区 → artifact evidence仓；新上下文引用同一整体task身份，不复制整段历史。

讲者展开：“持久文件有价值，但不是自动正确的数据库。我们还要核对路径、任务、revision和实际结果。本次的helper没有写出请求文件，主上下文如实记录并整理返回，而没有把不存在的文件描述成已完成。”

证据：H2、W12、E1。转场：有证据之后怎样推进，不机械走仪式？

## 8. RPI 生命周期与最小入口（15:00–18:00）

**目标：**会选wrapper或phase skill。**页面主张：**“RPI 是证据与阶段契约，不是必然的多worker链。”

关键点：用户选 RPI Agent wrapper；它激活phase skills、推进/恢复；research readiness有缺口才追加Research；Plan默认critique；wrapper默认实施后Review；都区分显式skip。上下文reset按需要，不是固定阶段动作。

图示：readiness → Research（条件）→ Plan↔critique → Implement → Review → 定向follow-up。helper画在侧边，不置于主路径。

讲者展开：“当前上游Research明确subagent never required，tight trace直接做。本机旧版skill却要求派Researcher；这次确实按加载的旧合同派了有界PR4研究，不能反过来讲成当前上游必须这样。小拼写修复不应被完整RPI压垮。”

证据：W2/W3/W4/W12与host.json。转场：先看Research真正交给Plan的是什么。

## 9. Research：证据、未知、备选与 readiness（18:00–20:00）

**目标：**区分研究和实施。**页面主张：**“研究的产物是可审查证据及planning readiness，不是提前写代码。”

关键点：当前源码要求Wider→Deeper→Contrarian；读现有架构、定位缺口、寻找反证。避免把HVE固定源码解释当本机执行事实。充分证据可复用，research-only明确不交接。

图示：事实 / 未知 / 反证 / 备选 / readiness五列，对照Commerce输入。

讲者展开：“我们确认的是建议质量缺口：5999、1899、7999三个金额在7000预算下全被推荐。并没有因此指控权限层失守。PR4只提供proposal-versus-authority概念，Python测试未执行，也不会把其SQLite保证移植成Node生产保证。”

证据：C1–C3、W1/W2、E1。转场：把研究压缩成可以精确验收的任务。

## 10. Plan + critique：实现前发现问题（20:00–23:00）

**目标：**理解计划审查的具体作用。**页面主张：**“critique检查计划够不够实施，不是代码生成的装饰。”

关键点：task Requirements、依赖、验收和边界；默认critique但可显式skip；fresh-eyes不强制另派代理，deep只在用户明确请求时使用。整体task ID稳定，Pxx/Pxx-Txx重组可重编号。

图示：需求卡 → T1–T5 → critique findings → 最小纠正 → readiness。展示真实的两个High：实施skill激活被写在实现之后；15问题未逐项列出/上游依赖不清。

讲者展开：“这两个问题在应用编辑前纠正。sync validator不支持同代理follow-up，host拒绝后主上下文做了限定inline复核，记录这是inline而不是第二独立Pass。好的教学证据包括限制和纠正，而非只展示全绿。”

证据：W4/W5、E1，demo-runbook中的P1输入。转场：什么时候可以动代码？

## 11. Implement：限定范围、真实验证、显式偏离（23:00–25:00）

**目标：**知道实施不是自由改写目标。**页面主张：**“计划可据实更新，重大决策不能被测试通过替代。”

关键点：执行指定计划/phase/task；记录passed/failed/skipped/unavailable；普通判断、实施注释、范围外follow-up与重大计划变更不同。approved scope不等于万能的人类签字，host权限和商业人审仍各自生效。

图示：当前任务标记 → 文件delta → focused checks → changes evidence。重大偏离箭头返回Plan/人类决策。

讲者展开：“本次修复在agent.js与UI中，不移动authority。父审查指出planner拿到同一个可变request可扩大预算，我们用structuredClone隔离，并用恶意mock验证不存task、不付款。这个真实修正属于当前边界内实现，不是扩大功能。”

证据：W6/W7、E1、agent.test/budget-http.test。转场：跑完命令为什么还需要Review？

## 12. Review / Follow-up：完成不等于验收通过（25:00–28:00）

**目标：**把执行状态与结果判定分开。**页面主张：**“Complete可以同时Defects found；检查未运行不能计为通过。”

关键点：当前upstream execution status与verdict两组词汇；RV finding绑定要求、expected/observed、证据、resolve条件和destination。实现缺陷→Implement；失效假设/重大决策→Plan；重要证据缺口→Research；非阻断剩余工作→follow-up。

图示：每条验收要求与一个证据连接，红/灰不是纯颜色而有文字状态。Review不直接修代码，remediation不自动要求第二Review。

讲者展开：“源码合同与本机旧skill合同不同，所以最终记录分清‘这次实际如何审查’和‘当前上游规定如何审查’。没在VS Code执行，不说VS Code失败，也不说已通过；它是有owner的待复现项。浏览器和HTTP检查分别举证。”

证据：W8/W9、最终evidence/rpi-execution.md。转场：现场首先确认版本，不让演示入口漂移。

## 13. 安装与版本：四件事分别记录（28:00–30:00）

**目标：**会做演示预检。**页面主张：**“研究revision、安装版本、发现、实际调用是四种证据。”

关键点：扩展 `ise-hve-essentials.hve-core` Stable/PreRelease exact tag；CLI `hve-core`跟踪main，不承载扩展发布assurance；CLI plugin instructions不自动apply；selective clone有团队ownership/更新取舍。

图示：channel → source/tag → discovered entries → References/tool activity，附VS Code主路径步骤。

讲者展开：“不要只截图slash菜单。展示本次输入确实加载skill、实际写出的artifact及验证。我们的预演host是Copilot App/CLI1.0.94-3；VS Code teaching path可复制，但需主讲人现场preflight。个人同名skill可能覆盖团队想演示的来源。”

证据：H2/H3、W13/W14，host.json。转场：切到离线Commerce页面。

## 14. Commerce既有架构：不重建支付系统（30:00–32:00）

**目标：**理解复用资产。**页面主张：**“PR1提供运行闭环；PR4提供研究对照，main尚无这些功能。”

关键点：Node22+原生HTTP/静态页面，无运行依赖；planner→request_quote→pending consent→独立人审→deterministic authority→模拟付款/收据/事件。身份是本地合成人设，不是生产认证。

图示：6段流程，每段标角色。付款边界画实线，HVE developer lane另列。PR1 open与新PR stacked base清楚标示，不暗示合并。

讲者展开：“源码完整复用PR1的批准、余额、预留、幂等、重启和退款链路。PR4Python不再起服务，以免为了分享变成双runtime项目。这里的USD/HKD/USDC各自记账，没有换汇，没有真实账款。”

证据：C1/C2/C3、README、architecture.md。Demo转场：打开 `http://127.0.0.1:4187`，先显示SIMULATED/OFFLINE。

## 15. 需求卡：预算推荐与解释，不扩大权限（32:00–34:00）

**目标：**把模糊需求改成可量化验收。**页面主张：**“≤限额才能推荐；没有候选是真no_action。”

关键点：USD7000→camera5999、coffee1899；headphones7999被排除、shortfall999；USD1000→零候选；等于限额合格，一minor超额不合格。币种错配不换汇；注入planner不可信。

图示：输入卡、三报价卡、输出字段；单候选与组合购物车画两栏，组合5999+1899=7898>7000。

讲者展开：“两件商品每件都低于70，不代表两件一起获准。planner说明预算余量只是相对上限，不是余额；Payment Authority在审批和执行继续检查累计支出与reservation。”

证据：agent.test.js/budget-http.test.js、E2。转场：先展示这次是如何研究和审查计划的，而非伪称从零现场造。

## 16. Demo Research/Plan：真实预演快照（34:00–37:00）

**目标：**看到chronological evidence。**页面主张：**“先研究和critique，后实施；预演记录与现场产出分开。”

操作：打开evidence/rpi-execution.md的Research/Plan部分，指出基线hash、原症状、备选、两项High纠正、host限制。只展示脱敏摘要，不打开包含token的状态文件。

图示：开始revision → research → plan/critique → 首次应用delta，标“2026-10-12预演”。

讲者展开：“如果有Copilot访问，按runbook在独立开始worktree执行一个限定phase。若没有访问，就展示真实预演记录与本地业务演示；不要把Markdown当VS Code已运行证据。我们今天展示的是可追溯开发，不是无条件自动化。”

证据：E1、host.json，baseline C1。转场：打开完成版本diff，聚焦最小变更，不现场生成整套应用。

## 17. Demo Implement：看共享规则和输入所有权（37:00–41:00）

**目标：**把工程规范映射成代码。**页面主张：**“预算事实由服务器维护，planner拿到的是副本。”

操作：展示 `assessQuotes`的journey/currency/amount判断；`validatePlan`的目录和单报价检查；`structuredClone(request)`；运行focused checks。补看UI canonical reason/shortfall，不逐行读全程序。

图示：server-owned normalized request → clone → planner → untrusted proposal → validator → task；错误走显式400，不走“悄悄过滤成功”。

讲者展开：“Injected planner测试不需要真的调用模型。它能返回目录里的超预算报价、伪造价格或approve_and_pay，也可能修改自己的输入副本。超出原请求范围或事实不符的返回建议应报PLANNER_OUTPUT_INVALID且不存task、不产生支付；修改副本但返回合法建议时可接受，保存的原预算与范围不变。有效旧mock不必新增解释字段，因为服务器从目录计算解释。”

证据：新增unit/HTTP测试；E1 validation failure修正；Payment Authority无改动的diff。转场：运行业务层，证明候选输出与硬权限独立。

## 18. Demo Review：五分钟跑出完整边界（41:00–46:00）

**目标：**用可观察结果验收。**页面主张：**“推荐、拒绝、批准与重放，每一步都有不同证据。”

操作时间：约1分钟USD70候选/耳机排除；1分钟请求camera并在独立审批页人审；1分钟回到同task请求coffee显示累计拒绝；1分钟USD10/no_action与币种错配；1分钟展示same-consent replay结果与unit/HTTP/browser各自证据。

图示：四张结果卡加事件/余额不变小表；不展示凭证。浏览器自动脚本13项断言可预先跑，现场操作页只做用户可见路径，重放使用runbook的同源诊断片段。

讲者展开：“未人审之前payments是0，agent approve得到403。Camera5999执行后余额24001、task剩1001；coffee1899的consent创建被拒绝。再次执行同consent不会多扣，也不追加事件。当前报告不是供应商认证，未验证真实资金。”

证据：E2的13条实际断言，原check/e2e，最终review。转场：把上下文恢复和团队推广从业务演示中抽象出来。

## 19. 上下文恢复：同任务，不盲目重放（46:00–48:00）

**目标：**知道恢复输入和边界。**页面主张：**“恢复先读canonical artifacts，再判下一步。”

关键点：整体task身份不变，wrapper记录task status、session_status和next_action；转移写失败要停止；现有artifact可能比旧state更可信。当前phase ID可能重编号，先读当前计划marker。

图示：新会话→检查task→读research/plan/changes/review→route；划掉“仅因state缺最后写入就重跑Implement”。

讲者展开：“这是一份源码规定，不是事务系统保证。本次未验证upstream wrapper崩溃恢复，所以只解释合同；已验证的是业务付款重放与重启测试，不要把两种恢复混为一谈。”

证据：W12/W9；E1实际限制。转场：如何给团队加入规范，而非复制完整框架？

## 20. 团队定制：先少量instructions，再Builder（48:00–50:00）

**目标：**学会最小资产化。**页面主张：**“资产按责任组织，冲突由团队消除，不让host替你裁判。”

关键点：本项目全局不变量合一份instruction；若未来特定路径有规则，用可核实applyTo范围；复杂重复workflow用skill；Builder create/improve可辅助但本次未执行。阶段扩展description说明时机/输入/返回；Research/Plan/Review核实并写artifact，Implement不是同样发现方式。

图示：问题→复用→扩展→新建决策树，source owner放旁边。

讲者展开：“VS Code官方说instructions来源additive，不保证更具体glob覆盖所有冲突。因此团队评审应先删掉矛盾，而不是演示一个虚假的确定性优先级。预算安全由code/tests enforce，prose只指导开发。”

证据：W10/W11/W13，H4。转场：合作伙伴如何第一周开始？

## 21. 一个可控试点到团队资产（50:00–52:00）

**目标：**给听众可执行采用路径。**页面主张：**“选择有边界任务，指定owner，控制更新。”

关键点：选重复但不高风险的小增量；2–3条规范与一个验收矩阵；记录host和版本；PR评审资产和运行结果；安装来源/许可证/同名覆盖/弃用策略要可追踪。

图示：第1周基线/试点 → 第2周复现/评审 → 后续提取领域skill。时间是建议安排，不是本次观测数据。

讲者展开：“可以从预算推荐或接口错误契约开始，不从全自动付款开始。团队真正拥有的是reviewed customization加验收，而不是把上游main不断追新视为治理。没有owner的长instructions最容易过时。”

证据：H4、H2/H3，E3原创建议。转场：怎样判断真的改善？

## 22. 效率衡量：同时看质量与成本（52:00–54:00）

**目标：**避免只比代码输出速度。**页面主张：**“本次没有提效百分比；先定义可观察指标。”

关键点：需求遗漏数、返工轮数、人工纠偏、验收覆盖、另一工程师交接复现率；同时记端到端时间、模型/工具成本、等待和维护。同类任务/相近熟练度对照，记录失败，不选择性报喜。

图示：质量轴×时间/成本轴；baseline与pilot观察表，所有数据留空供团队实测。

讲者展开：“23向量100%只是固定离线夹具结果，不能推论模型生产准确率或HVE效率提升。框架本身会增加规划与文档成本，只有复杂度、风险或复用收益足够时才值得完整RPI。”

证据：H4指标建议、E3。转场：用反模式强化边界。

## 23. 六个反模式（54:00–56:00）

**目标：**能主动指出常见误读。**页面主张：**“HVE不是更多agent、更多文档、更多自动授权。”

关键点：为小改动强制全RPI；巨大instructions互相冲突；把discovery当遵守；把Full Auto当支付批准；把mock当模型效果；把main研究当本机扩展版本。另提醒预演记录不得冒充现场生成。

图示：每个反模式右侧一个更好选择：最小入口、owner消冲突、看References/tool activity、运行时授权、mock标签、版本账本。

讲者展开：“自动推进只是开发工作流的节奏。商业主体、授权scope、预算和真实环境权限完全不同，不能因为自动执行开发任务就获得用户钱包权限。”

证据：H1/H3，W11–W14，E1。转场：最后留一个行动，而非一长串工具列表。

## 24. 收束与 Q&A（56:00–60:00）

**目标：**让听众带走一个任务、一组边界、一条采用路线。**页面主张：**“把可复现工程过程作为交付。”

结论：用Copilot做工程；用HVE整理证据、任务、决策和验收；业务authority由代码执行。本地Demo与完整H5供复现；大纲可供Cowork制作，不含PPT。

图示：三件带走物：需求卡 / evidence chain / runtime boundaries；附README入口与本地URL。最后3分钟Q&A，提前准备：

| 问题 | 回答要点 |
|---|---|
| 不使用wrapper可以吗？ | 可以按需phase skills；理解各自前置条件与产物，别机械重复Research。 |
| 当前必须多agent吗？ | 不必须；本机旧skill差异已记录，不作为当前upstream规则。 |
| mock有什么价值？ | 验证工程契约和权限分层；不验证模型智能、真实供应商或结算。 |
| Full Auto能自动买？ | 开发推进模式不授予商业权限，Demo仍要求精确人工批准。 |
| 谁维护规范？ | 团队owner和PR流程；版本、license、更新/弃用与运行证据一起维护。 |
| 是不是已经在VS Code演示过？ | 本次实际Copilot App/CLI；VS Code教学步骤待主讲人复现，不声称已验证。 |

证据：E1/E2，demo-runbook。结束语：“从一个有边界的真实需求开始，让下一位工程师无需猜测就能继续。”

## 备查而不挤进主讲的深读内容

H5完整15题逐章阅读；RPI state/artifact和marker合同；Builder扩展协议；扩展发布assurance与CLI main差异；PR4SQLite对照；Commerce退款/履约/HTTP402-shaped挑战。现场仅选需求相关部分，不要把一小时变为源码朗读。

## 制作与讲述验收

24单元时间区间连续覆盖00:00–60:00；HVE核心机制与团队采用占主线，业务现场demo限12分钟。每单元都有目标、主张、图示、讲者展开、来源和转场。严禁在Cowork输出加入未经实测效率百分比、供应商认证、真实支付、VS Code已运行或“必须四专职agent”的表述。
