# Agentic Commerce Lab

面向 Personal Agent 的 Agentic Commerce 研究与可运行模拟实验：聚焦商业场景、AI 职责、授权与支付原生架构。

本仓库将研究 Stripe Sessions 2026、Visa Intelligent Commerce / Trusted Agent Protocol、Sierra Agent OS / Personal Agent Protocol（"Poppy" `v0.1` 草案）与公开的 AWS Shopping Concierge 示例，并记录来源、发布日期、适用范围和证据等级。研究内容会区分产品公告、当前文档、协议规范、代码观察和本地模拟，不把演示结果描述为供应商认证或真实支付结算。

## 目标

- 研究 Agent 参与发现、比较、委托、批准、支付、履约和售后的商业价值链。
- 设计把用户同意、交易约束、支付凭证隔离、持久状态和恢复流程放在确定性权限层中的 Personal Agent 架构。
- 提供无需支付账户、真实资金或云资源即可运行的合成购物与支付模拟。
- 将可选模型推理与支付执行隔离；模型只能提出建议和动作请求，不能批准或扩大权限。

默认实验是离线模拟。真实商户支付、账户连接、付费模型调用及云部署均不属于默认能力。请勿输入真实卡号、账户凭证或个人财务数据。

## 研究边界

本仓库只发布原创说明、合成数据和经许可审核的代码；不托管内部材料、客户信息、支付秘密或第三方资料副本。各能力的集成与验证状态会明确标记。

## 研究与技术资产

| 入口 | 内容 |
|---|---|
| [2026-10-19 每日研究](research/daily/2026-10-19.md) | 50 来源监控与 Stripe SPT 三角色变体（Connect 档案路由、单次 `SPT Resolve`、三大卡组织凭证）、MPP Tempo 流式会话亚美分尾差没收与 Token 计费、AP2 `#165` 受托熔断器、UCP `#866` 批量目录摘要屏障、ACP `#316` Appendix C 17 网关映射、AI-Native vs 经典三层六平面重构及 Stripe MCP 42 日核验 |
| [2026-10-18 每日研究](research/daily/2026-10-18.md) | Stripe WebMCP/Booking/Embedded(OCA & RequestedSession)/SFTP Feed/Directory 新文档核验、Poppy `operations` v1 超时 `in_progress`/取消/去重、UCP `#940`/`#970`/`#660`/`#966` 与 ACP ATDRP §7.4a、Stripe MCP 43 日核验 |
| [2026-10-17 每日研究](research/daily/2026-10-17.md) | Poppy `#35` 企业实现套件/18 份 Schema/改造前后架构对照、UCP `#913` Permalink `303` 安全头、Stripe MCP 英式日期核验 |
| [2026-10-16 每日研究](research/daily/2026-10-16.md) | Stripe MCP 迁移延期至 `2026-11-30`、Poppy `v0.1` 17 项安全/DPoP/会话提交、UCP Webhook 签名门禁（`#659`） |
| [2026-10-14 每日研究](research/daily/2026-10-14.md) | Sierra 与 Poppy `v0.1` 草案/当日建仓核验、TAP 迁移、UCP 扩展修复、MCP 告示监测及 17 日窗口 |
| [2026-10-13 每日研究](research/daily/2026-10-13.md) | 官方 skills 增量、可执行能力边界、UCP 离线预检及 MCP 18 日迁移窗口 |
| [2026-10-12 每日研究](research/daily/2026-10-12.md) | 官方证据增量、AI Native 与 WAF 辩证比较、UCP handler 边界及 MCP 迁移盘点 |
| [2026-10-11 研究基线](research/daily/2026-10-11.md) | 发布事实纠错、已有技术资产、证据缺口与日更机制 |
| [协议与产品分层](research/protocols.md) | Visa VIC/TAP/MCP/Toolkit；Stripe ACP/UCP/Suite/SPT/Link/MPP/x402/MCP；Sierra & Poppy `v0.1` |
| [Personal Agent 参考架构](research/architecture.md) | 信任边界、六平面 AI-Native 重构、审批、幂等、异步支付恢复、Sierra 纵深防御与非功能取舍 |
| [Agent 使用场景](research/use-cases.md) | 零售、补货、预订、B2B 开票、API 付费/流式微支付、售后改单（Poppy/Sierra）与财务洞察 |
| [官方来源注册表](research/sources.json) | 50 个来源、验证日期、发布日期、版本与证据边界 |
| [离线 checkout 实验](lab/checkout.py) | 合成报价授权、购物车绑定、单次消费、持久幂等及并发保护 |
| [离线 MCP 迁移盘点](lab/mcp_migration.py) | Stripe MCP `2026-11-30`（原 `2026-10-31`）auth 类别期限检查；只接受无密钥元数据，不验证账户 |
| [离线 UCP handler 与协议边界预检](lab/ucp_preflight.py) | 版本/宣告 instrument/card tokenize 前置条件、RFC 9421 闭合必签门禁（`#659`/`#795`）、Permalink `303` 安全头与不可信 GET 输入校验（`#913`）、RFC 9728 多条目身份发现与 Accelerated IdP 单用户换票绑定（`#783`/`#970`）、Cart-to-Checkout 互斥与优先级（`#940`）、`buyer.consent` 全量替换豁免（`#660`）、退货政策禁算日校验（`#966`）、Stripe OCA/SFTP/WebMCP 护栏及 ACP ATDRP §7.4a 证据包准入（`#316`） |
| [离线 Poppy & Sierra 零售护栏](lab/poppy_guard.py) | Poppy `v0.1` 发现/RFC 8414 §3.1 路径多租户隔离/DPoP/跨上下文断言防混淆与浏览器交接/Milestone 2 `conversations.*` 与 Milestone 3 Sign-In & Account Token 生命周期及脱敏（`#35`）、`operations` v1 扩展协商/跨通道去重/下游超时 `in_progress` 驻留/取消与 $\tau^3$-bench 零售改单护栏 |
| [离线六平面 AI-Native 负载架构基准](lab/workload_arch_bench.py) | Connect SPT 档案路由、单次 `SPT Resolve` + RSA 切片、SPT 3DS 状态机与 AP2 §7.4 受托熔断器（`#165`）、Policy Broker、UCP RFC 9530 批量目录摘要屏障（`#866`）、ATDRP Appendix C 17 网关兜底证据编译（`#316`）、MPP Tempo 亚美分尾差没收审计及 [7-Card 4:5 视觉报告](reports/agentic-commerce-6plane-bench/index.html) |

## 本地运行

要求 Python 3.12+；只使用标准库，无需支付账户、模型密钥、联网或安装依赖：

```powershell
python -m lab.demo
python -m unittest discover -s tests -v
```

demo 使用自动清理的临时 SQLite 数据库，输出 `status=simulated`。可信调用方预置批准与时钟；生产需要独立用户认证/同意与支付 broker。此实验**不是** ACP/AP2/TAP/SPT 协议实现、真实支付或认证结果。

### Stripe MCP 迁移盘点（不读取密钥）

```powershell
python -m lab.mcp_migration --as-of 2026-10-16
python -m lab.mcp_migration --as-of 2026-11-30
```

默认读取 [合成客户端清单](lab/mcp_inventory.example.json)；`--inventory` 可指定仅含 alias、环境和 auth 类别的 JSON。禁止填入实际 key、账户 ID 或个人数据；不传 `--as-of` 时使用北京时间当天日期。示例含两种旧认证类别，两个命令都**预期 exit 1**，分别输出 `migration_required` / `blocked_by_documented_policy`；空/无效输入 exit 2。全部记录为 OAuth/Agent Key 时 exit 0 只表示元数据类别匹配，始终 `account_verification=not_performed`，不是已迁移或已获付款权限。

Stripe 文档未说明 cutoff 的具体时刻/时区，本工具只做日期模拟，不检测服务器 401。10-16 再核验发现官方通告已将迁移截止日从 `2026-10-31` 延后至 **`2026-11-30`**（`Migrate by November 30, 2026. Starting in December, Stripe MCP will stop accepting...`），距 10-16 剩余 45 个日历日；依据是 [MCP 官方正文](https://docs.stripe.com/mcp)，人工迁移 runbook 见 [10-12 研究](research/daily/2026-10-12.md)，延期核验见 [10-16 研究](research/daily/2026-10-16.md)。工具无网络调用，不创建、轮换或撤销实际凭证；来源监测发现变化也不会自动更新本工具的规则，必须经人工审阅后显式更新。

### UCP handler 兼容性预检（不获取凭证）

```powershell
python -m lab.ucp_preflight
python -m lab.ucp_preflight --instrument card --relationship confirmed
python -m lab.ucp_preflight --instrument apple_pay
```

默认用完全合成的双方宣告测试 `link`，**预期 exit 1**：当前 Stripe `/complete` 不接受该 instrument。后两条 exit 0 仅为 `candidate_unverified`，始终 `payment_authorized=false`、`provider_verification=not_performed`。Google Pay 在本预检中拒绝，不自动转到 `com.google.pay`、转换 instrument 或降级到浏览器付款。

本地只审阅 UCP `2026-04-08` / Stripe handler `2026-06-25` 文档示例，匹配但未经本地审阅的版本也拒绝；这不是声明其他版本被供应商禁止。卡 tokenize 才检查双方 `sandbox/production` 环境一致和关系已确认，不能把该条件套到 Apple Pay wallet 路径。`--business-ucp-version` / `--business-handler-version` 可模拟版本漂移；无效日期 exit 2。所有参数只是元数据声明，不读取实际 UCP profile、key、PAN、SPT 或钱包数据，也不验证客户同意、Apple Pay 商户配置、地域/账户资格或支付结果。此工具不是 UCP wire-format/conformance 实现，更不是 checkout 的授权层。

### Poppy `v0.1` 发现与 Sierra 零售售后确定性护栏（离线模拟）

```powershell
python -m lab.poppy_guard
```

演练 Personal Agent Protocol（"Poppy" `v0.1` 草案）的 `/.well-known/poppy.json` 发现与 OAuth `poppy_domains` 双向防伪校验、令牌端点 `poppy-session+jwt` 与浏览器会话端点 `poppy-browser+jwt` 跨上下文防混淆校验（`#35`）、OpenAPI/Operations `DPoP`（封禁 `HS*` 对称算法）vs MCP 单一 `resource` 绑定 `Bearer` 与 RFC 9728 元数据验证，以及结合 Sierra Defense-in-Depth 与 $\tau^2/\tau^3$-bench 零售策略的两阶段 `operations` v1 订单修改确认：拒绝用对话消息（含 `sender: "human"`）确认操作、核对企业 `summary` 与结构化 `terms` 一致（`#51`）、对最新不可变 `revision` 幂等确认执行，并拦截同一待发货订单的二次商品修改。此模块仅使用合成内存数据，不发起真实网络请求或支付调用。

### 六平面 AI-Native vs. 经典三层 Web 架构基准与 7-Card 报告生成（离线模拟）

```powershell
python -m lab.workload_arch_bench --output-dir reports/agentic-commerce-6plane-bench
```

运行覆盖六大架构平面的 12 个对抗性评测场景（Stripe Connect SPT 档案路由、单次 `SPT Resolve` 重放拦截与 RSA 切片提取、SPT 3DS 非线性状态机、Google AP2 §7.4 四态受托熔断器、Policy Broker `summary`-vs-`terms` 校验、UCP `dev.ucp.common.feed` RFC 9530 分片摘要屏障与变体按 `id` 合并、ACP ATDRP Appendix C 17 网关争议证据兜底编译、Stripe MPP Tempo 流式会话亚美分尾差没收审计），并输出确定性评估数据 [`reports/agentic-commerce-6plane-bench/report.json`](reports/agentic-commerce-6plane-bench/report.json) 与自包含 7-Card 4:5 视觉基准报告 [`reports/agentic-commerce-6plane-bench/index.html`](reports/agentic-commerce-6plane-bench/index.html)。


## 每日研究

已有 Copilot App 自动化每日 22:00 执行研究，已补充官方来源核验、检查未合并分支、按日期增量研究、相关测试、提交推送与 PR 的要求。日更依赖本机 App/执行主机可用；GitHub Actions 目前仅执行 CI，不负责生成研究。

需要联网的公开来源跟踪命令：

```powershell
python -m scripts.source_monitor
```

生成 `research/daily/YYYY-MM-DD-sources.json`（北京时间），只记录 URL、哈希、错误和选定结构化事实，不保存第三方全文。任何抓取失败返回非零退出码；同日重跑仍对比此前日期的最后成功结果。HTML 导航或文案变化也可能改变哈希，**不能据此判断产品发布或标准升级**。专家研究写入同日 `.md`，将最新官方正文与公告日期、准入限制分开。

10-14 起，对 `stripe-mcp` 的已审阅 Markdown 迁移告示额外输出 `policy_facts` / `policy_change` / `policy_error`：截止日期、两类被拒绝 key、OAuth/Agent Key 替代路径、文档所述 401/OAuth discovery，以及未知的截止时刻/时区。首次提取为 `baseline`，不回填历史；`policy_change=unchanged` 只表示这些字段相同，不是整个政策、tool/schema 或实际账户权限未变。

提取器仅识别固定的短告示语法，忽略 fenced code 中的示例。缺失/重复告示、日期矛盾或措辞变化均 `unknown` 并返回非零，不猜测新语义、不退回旧事实冒充本日成功。正文抓取成功但解析失败时 `status=ok` 与 `policy_error` 同时记录；fetch 失败则 `status=error`。两种失败都保留此前日期最后成功基线。当前可识别语法之外的合理文案变化也会要求人工审阅，这是保守的监测取舍，不是 Stripe 拒绝该政策。

研究上传当前会话分支并通过 PR 汇总；未合并前不代表默认分支已更新。尚未验证的能力会明确标注，不能据此推断生产可用性。

## 公开参考

- [Stripe: Sessions 2026 announcements](https://stripe.com/blog/everything-we-announced-at-sessions-2026)
- [Stripe: Agentic commerce](https://docs.stripe.com/agentic-commerce)
- [Visa: Intelligent Commerce](https://www.visa.com/en-us/solutions/intelligent-commerce)
- [Visa: Trusted Agent Protocol overview](https://developer.visa.com/capabilities/trusted-agent-protocol/overview)
- [AWS AgentCore Shopping Concierge sample](https://github.com/awslabs/agentcore-samples/tree/main/05-blueprints/shopping-concierge-agent)
