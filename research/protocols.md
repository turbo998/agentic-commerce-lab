# Agentic Commerce 协议与产品分层

验证日期：**2026-10-11（北京时间）**。这是架构研究，不是供应商集成认证。事实依据见 [来源注册表](sources.json)；官网 `latest`、`main` 与当前文档可能继续变化，不能用首次公告替代今天的能力边界。

## 不要把所有协议放在同一张“支付协议”清单里

| 层次 | 协议或产品 | 解决的问题 | 不负责什么 |
|---|---|---|---|
| 工具访问 | MCP；Visa MCP Server；Stripe MCP | Host/Client/Server 之间的工具、资源、能力协商及 API 访问 | 不替用户批准订单；不等于商业交易协议；不保证支付成功 |
| Agent 协作 | A2A | AgentCard、Message、Task、Artifact；跨 Agent 任务、流式与异步交互 | 不定义购物税费、卡凭证、资金结算 |
| 商业流程 | ACP、UCP | 商品、购物车、checkout、账户关联、订单及履约扩展 | 本身不成为收单网络，不免除商户责任 |
| 个人代理连接与操作确认 | Personal Agent Protocol（Poppy `v0.1` 草案）及 `operations` v1 | `/.well-known/poppy.json` 发现、OAuth `poppy_domains` 双向绑定、DPoP vs MCP Bearer、会话及两阶段 `operations` 修订确认 | `v0.1` 明确未定义 Payments（列为 Open Topic）；与 UCP 互补而非替代 |
| 请求信任 | Visa TAP；Sierra `fleming-1` 语音识别 | 商户识别可信 Agent、验证绑定上下文的请求签名（TAP）或实时音频 caller-agent 检测（`fleming-1`） | 可信请求或声学提示不等于资金授权成功，更不等于结算完成 |
| 意图与授权证据 | AP2；Visa authenticated Payment Instruction；Poppy `operations` revision | 可验证的用户约束、不可变修订提案确认与审计证据 | 不把自然语言意图或对话文本（含 `sender: "human"`）自动升级为交易确认 |
| 凭证委托与 PCI 隔离 | Stripe SPT；Visa agent-specific tokens；Link Agent Wallet；Sierra Payments（Level 1 PCI） | 隔离原始支付信息、限定商户/金额/有效期、或将卡收集切出 LLM 进入服务端预定义 PCI 流 | 不是所有商户/地域都能使用的通用 bearer token |
| 机器付费 | MPP、x402 | HTTP 402 challenge → 付款证明或凭证 → 重试 → 资源及回执 | 不是完整商品发现与售后协议；也不免除退款、税务、合规义务 |
| 商户与客服集成产品 | Stripe Agentic Commerce Suite；Sierra Agent OS（含 Stripe App） | 产品目录分发、托管商业接口、客服订单操作、语音/全渠道交互与四层运行时护栏 | 不是开放协议的同义词；标准开放不代表渠道接入已获批准 |

## Visa：网络级授权与商户信任

### Visa Intelligent Commerce（VIC）

[开发者正文](https://developer.visa.com/capabilities/visa-intelligent-commerce/overview)描述的链路为：

1. Agent onboarding → 用户添加卡 → step-up verification → 设置 Passkey。
2. Agent 提出一笔或多笔购买建议，用户同意并用 Passkey 认证 Payment Instruction。
3. Agent 请求凭证；VIC 校验其与已认证指令一致，并设置 network-level controls。
4. Agent 在商户结账；正文将初期路径描述为 guest checkout/form fill。
5. VisaNet 在授权阶段执行预期商户与金额控制；Agent 回传购买结果，为争议处理提供证据。

**架构含义：**签名与授权证据在模型之外管理。浏览器表单自动化也必须受到同一授权约束，不能因为 API 尚未接通就绕过凭证隔离。文档可阅读不代表该账户具备生产接入资格；onboarding、市场、发行方、token provisioning 与商业合作仍需单独确认。

### Trusted Agent Protocol（TAP）

[公告](https://corporate.visa.com/en/sites/visa-perspectives/newsroom/visa-unveils-trusted-agent-protocol-for-ai-commerce.html)说明 TAP 基于 HTTP Message Signatures，与 Cloudflare 合作，并与 Web Bot Auth 相关标准方向对齐。初期规格作用于 Visa network 场景，目标是开放生态互操作；不能据此声称已完成跨网络认证或成为最终行业标准。

[开发者正文](https://developer.visa.com/capabilities/trusted-agent-protocol/overview)明确 merchant/purpose/time-bound signatures、防重放和防 relay。[官方仓库](https://github.com/visa/trusted-agent-protocol)的 README 展示 Agent Registry、CDN Proxy、Merchant Backend/Frontend、TAP Agent 拓扑，并提到 RFC 9421。今天仅核验 README 和仓库头提交，不宣称审阅了整个代码库或验证参考实现的生产安全性。

**设计要求：**在 CDN/网关验证公钥来源、签名覆盖组件、有效期、nonce/重放状态、商户域与操作上下文；保留独立交易授权与 PSP 风控。不能靠 User-Agent 字符串放行，也不能将 TAP 放行当作卡授权。

### Visa MCP Server / Acceptance Agent Toolkit

[官方产品更新](https://corporate.visa.com/en/sites/visa-perspectives/innovation/visa-mcp-server-agent-acceptance-toolkit.html)将两者描述为 **pilot**。Toolkit 的明确示例是 Acceptance Invoicing、Pay By Link 和交易信息查询；不将“开票工具”包装成已完成自主卡付款的能力。角色授权、读写工具分离、发票金额校验和确认应由宿主与服务执行层落实。

## Stripe：商户编排、凭证与机器支付

### 发布事实与今天的文档要分开

| 官方来源 | 核验的发布日期 | 实际证据与边界 |
|---|---|---|
| [ACP / Instant Checkout 公告](https://stripe.com/blog/developing-an-open-standard-for-agentic-commerce) | 2025-09-29 | 首发正文为 Stripe/OpenAI 共建；可开放实现标准与加入具体 AI 渠道是不同事项 |
| [Suite 公告](https://stripe.com/blog/agentic-commerce-suite) | 2025-12-11 | 单集成处理发现、checkout、支付、风控；正文已介绍 SPT，因此不能说 SPT 首发于 Sessions 2026 |
| [Sessions 2026](https://stripe.com/blog/everything-we-announced-at-sessions-2026) | 2026-04-29 | Link agent wallet、MPP、Suite 渠道扩展；平台能力为 preview，Google/Gemini 购买路径用的是 coming-soon 表述 |

以上日期从 Stripe 页面 `datePublished` 元数据读取。Visa 两篇公告的日期未从本轮正文/元数据独立提取，注册表保留 `null`，不把搜索摘要的日期当成确认事实。

[当前 ACP 文档](https://docs.stripe.com/agentic-commerce/protocols/acp)已经列出 Stripe/OpenAI/Meta，包含 checkout、cart/feed、delegate payment、OAuth delegate authentication、orders/webhooks。文档链接指向 `spec/2026-04-17` 的 OpenAPI 与 JSON Schema；仓库另有 `unreleased`，必须固定实际选择的规格，不能实现浮动主分支后自称特定版本合规。

### Shared Payment Tokens（SPT）和 Link Agent Wallet

[SPT seller 文档](https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens.md?agent-seller=seller)：

- SPT 对卖家的 Stripe profile 提供 scoped grant，包含 `usage_limits[currency]`、`max_amount`、`expires_at`。
- 今天示例 API version 为 **`2026-09-30.preview`**，不能混用旧示例的请求字段。
- 卖家用 `payment_method_data[shared_payment_granted_token]` 创建/确认 PaymentIntent；风控、退款、支付状态仍由 Stripe 的实际结果决定。
- 地域为美国、加拿大与部分欧洲国家；agent、customer、seller 的资格需分别查。地区列表并不等于 Link 钱包的可用地区。

[Link Agent Wallet 文档](https://docs.stripe.com/agentic-commerce/agents/link-agent-wallet)：

- 具体 purchase 的 spend request 经客户批准后获得一次性 payment credential。
- Agent payments 面向美国/加拿大客户，financial insights 面向美国客户；卖家和 Agent 开发者所在地可以不同。
- Link API 位于 `api.link.com`，授权服务器为 `login.link.com`；使用客户 OAuth token，**不是 Stripe API key**。CLI 和 Link SDK 的认证/存储边界与 Stripe server SDK 不同。
- Financial insights 的账户授权和支付批准是不同 scope；不要把“可读余额”当作“可支出资金”。

### MPP 与 x402

[Stripe MPP](https://docs.stripe.com/payments/machine/mpp)是 Stripe/Tempo 共建的 Machine Payments Protocol。HTTP 402 要求付费，Agent 授权后重试，服务端核验并返回付费资源及 receipt；Stripe 集成支持 SPT/card 和 stablecoin。今天文档含 `2026-07-29.preview` API 示例。不能把 MPP 限定为 stablecoin-only，也不能将两个 402 协议当作相同 wire format。

[Stripe x402](https://docs.stripe.com/payments/machine/x402)的示例：Client → HTTP 402 → 带凭证重试 → facilitator verify/settle on-chain → Stripe `transaction_verification` PaymentIntent 记录 → 资源。示例为 Base/USDC，API version **`2026-05-27.preview`**。链上已结算但 Stripe 记录失败，需要以交易 hash 幂等重试对账，不能再次付款。

[Machine payments 总览](https://docs.stripe.com/payments/machine)区分协议支持矩阵：MPP/Tempo/USDC.e、MPP/Solana/USDC、x402/Base/USDC。卡/SPT 最小金额 $0.50，stablecoin 最小 0.01 USDC；sessions 的 sub-cent 计量不等于每次 sub-cent 都能立即结算。稳定币接入需审批，美国纽约州不在文档的可用范围，其他市场需申请。金额与网络边界不能从“微支付”营销词自行推断。

### Stripe MCP：本月需要特别跟踪

[当前文档](https://docs.stripe.com/mcp)明确：从 **2026-10-31** 开始不再接受 full-access secret keys 或没有 Agent tag 的 restricted keys。交互客户端优先 OAuth，无交互应用使用最小权限 Agent Keys。生产迁移先在 sandbox 验证，再过期旧 key；本仓库不创建、读取或保存任何真实 key。

### Agent 框架、Toolkit、Plugin 与 Skills

[当前开发者入口](https://docs.stripe.com/agents)优先推荐组合了 MCP 与 Skills 的 agent plugin；Stripe CLI 的 `stripe agent setup` 可按客户端安装。Skills 是构建指导，不是远程付款授权，更不能覆盖权限策略。

历史 `stripe/agent-toolkit` 仓库的 GitHub Contents API 当前返回标题为 **Stripe AI** 的 README，指向 `stripe/ai`。该 README 列出 `@stripe/ai-sdk`（Vercel AI SDK 的计费集成）、`@stripe/token-meter`（原生模型 SDK 的计量集成）、remote MCP 与 plugins/skills。因此今天不沿用旧教程假设 Toolkit 目录结构和支付能力未变化；仅核验 README，不宣称执行或认证其 SDK。计费/计量、商户 checkout 与替用户付款是三个不同职责。

## 其他标准的版本与语义漂移

| 标准 | 今天的直接证据 | 架构注意事项 |
|---|---|---|
| AP2 | [当前官方正文](https://ap2-protocol.org/)使用 Checkout Mandate / Payment Mandate，各有 Open / Closed 阶段；GitHub tag 存在 `v0.2.0` | 老材料的 Intent/Cart 命名不能未经核对写成当前规范；main 正文与 tag 必须分别核验。FIDO 标准化继续进行，不表示所有实现已认证 |
| UCP | [规范](https://ucp.dev/latest/specification/overview/)要求精确协议版本选择、能力协商、reverse-domain namespace 与 schema origin 绑定 | provenance 不是 trust。远程 schema 解析需 allowlist、HTTPS、大小/超时限制，防 SSRF 与依赖投毒；draft 能力不自动成为稳定能力 |
| MCP | 已读 `2025-11-25` 文本；官方 schema 目录另有 `2026-07-28` 与 `draft` | 本轮不宣称完整审阅新版本；MCP 代表 Model Context Protocol，不是 Merchant Commerce Protocol |
| A2A | [latest 规格页](https://a2a-protocol.org/latest/specification/)显示 `1.0.0`，canonical proto → abstract operations → JSON-RPC/gRPC/HTTP bindings | 协作消息的身份认证与付款授权分开；附带授权证据不能省略校验 |

## 方案选型

零售商已有 Stripe 与库存/履约系统：先评估 Suite 或 ACP/UCP adapter 的系统接入成本，保留商户主权和订单事件回写。需要多 PSP 时，将授权、商业协议、支付 handler 分层，不将 Stripe 特有 SPT 字段扩散到领域模型。

面向消费者的 Personal Agent：先落地**报价 → 人工批准 → 最终购物车绑定 → 限额凭证 → 商户支付 → 异步确认**。再评估具备明确 Open Mandate 的补货场景；未证明撤销、累计预算、并发控制与价格漂移处理前，不开放自主购买。

API/data 服务提供商：优先比较 MPP/card 与 stablecoin、x402 的区域接入、最低金额、单位经济、钱包能力及链上失败恢复。不要为了展示“Agent 自动付款”而跳过服务定价、退款 SLA、密钥隔离与合规分析。

## 2026-10-12 增量核验

以上保留为 10-11 基线；当日证据与未解决问题见 [10-12 日研](daily/2026-10-12.md)，不能将本节新增核验当作新发布。

- [Stripe UCP handler](https://docs.stripe.com/agentic-commerce/protocols/ucp/stripe-payments-handler) 示例分开 UCP `2026-04-08` 与 handler `2026-06-25`：card/Apple Pay completion、Google Pay 使用 `com.google.pay`；discovery 宣告 `link` 不代表当前 `/complete` 接受 `link` instrument。Tokenize 还要求相同环境与已确认商业关系，profile ID 不是客户 OAuth token。
- [API keys 正文](https://docs.stripe.com/keys)确认 Agent Key 是 Agent-tagged restricted key，受 approval rules 治理。MCP 2026-10-31 期限仍未变；新离线盘点只判断 auth class，不能验证实际 tag、审批或权限。
- A2A 官网仍显示 `1.0.0`，但 [官方 repo release](https://github.com/a2aproject/A2A/releases/tag/v1.0.1) 为 `v1.0.1`，GitHub publication 为 2026-05-28；这不是今天的 release。固定 tag/proto 后再做契约验证，不将 website `latest` 自动等同于 tag。
- SPT seller 示例到期时间会动态变化；UCP 昨日到今日 head 仅更新依赖锁文件。两种变化都不构成产品发布证据。

## 2026-10-13 增量核验

完整证据和失败记录见 [10-13 日研](daily/2026-10-13.md)。首次公告与历史版本保持原记录，不以本日复核替换。

- Stripe MCP 指纹相对 10-12 改变，两次本日正文获取指纹一致；未保留昨日正文，不能精确重建全部语义 diff。**2026-10-31** 认证迁移期限仍未变，本日剩余 18 个日历日；MCP 的 Agent Key 规则不能泛化到 UCP tokenize 或 Link OAuth。
- UCP overview 未变；当前官方 head `9756aa9…` 是 contributing/roadmap/navigation 文档提交，不是协议升级。Stripe handler 文档仍区分 card tokenize → SPT、Apple Pay direct token、Link credential acquisition 与 `com.google.pay` completion。本地新增预检只处理已审阅的 Stripe handler 示例，不宣称 Google Pay 或 UCP conformance。
- [Stripe AI 官方提交](https://github.com/stripe/ai/commit/deae744bc0cbf6034b4b6f22f51c690b71a4e779)在北京时间 10-13 同步 skills，plugin manifest `0.5.16 → 0.5.17`；升级 skill 生成日期改变但 fallback API version 仍是 `2026-09-30.endive`。反馈指导调整不是新付款能力，本轮未安装插件、运行供应商 CLI 或提交反馈。

## 2026-10-14 增量核验

完整证据、来源失败及版本边界见 [10-14 日研](daily/2026-10-14.md)。没有已核验的本日 Visa/Stripe 商业产品首发；以下是正文路径、文档/代码和监测增量。

- Visa TAP 原 overview 现在重定向到 [getting started](https://developer.visa.com/docs/trusted-agent-protocol)，其[商户规格入口](https://developer.visa.com/docs/trusted-agent-protocol/trusted-agent-protocol-specifications)说明 browsing/payment 两类交互，以及 consumer recognition / optional payment information。首次看到此路径不等于今日发布。TAP 可承载支付相关信息，但请求/数据签名仍不能代替消费者最终授权和 PSP/network 结果。**VIC 开发者正文获取 403**，今日不能将历史生命周期说明标为重新核验成功。
- UCP 固定 commit [`72ea9a9…`](https://github.com/Universal-Commerce-Protocol/ucp/commit/72ea9a95c4aaaabb042adc6906430578c54549e3)修正文档示例，并对基础 capability 未声明、由 extension 引入的字段追加 composed-schema 校验。另一个 commit [`e45c021…`](https://github.com/Universal-Commerce-Protocol/ucp/commit/e45c02121fbef9125286b9f55c1f04be6a7d682a)使文档表从 OpenAPI `securitySchemes` / `security` 和 content maps 生成认证及媒体 headers。这是契约验证和文档生成修复，不是已证明的协议版本升级；本仓库 UCP metadata 预检没有新增扩展/schema/签名认证能力。
- Stripe MCP 截止日期仍 **2026-10-31**，本日相差 **17 个日历日**；未说明准确时刻/时区。当前正文也列出通用 `stripe_api_write` 和 Treasury public-preview 写操作；未保留昨日全文，不能称为今日新增工具。工具 catalog 可见不意味着任意账号、地区或审批条件下可执行。
- Stripe AI [`789ef5e…`](https://github.com/stripe/ai/commit/789ef5e0a55ee1d0787a5974660b15bf76dc29b5)仅本轮观察到 manifest bump 和 upgrade skill 生成日改变，fallback API 仍 `2026-09-30.endive`。各 provider 版本不同，不用 agent-plugins 的 `0.5.18` 代替 Claude/Codex 等版本。
- 来源监测开始记录 MCP 告示的选定结构化事实，**不是**将官网文本自动变成付款/运维权限。字段变化或解析失败需人工核验后显式修改规则，不能触发自动创建 key、绕过审批或高权限回退。
- **Personal Agent Protocol（Poppy `v0.1` 草案）与 Sierra 体系核验**：
  - [Meta 与 Sierra 首发公告（2026-10-06）](https://sierra.ai/blog/introducing-personal-agent-protocol)、[Poppy `v0.1` 草案发布（2026-10-09）](https://sierra.ai/blog/poppy)（新增 Visa、Mastercard、Adyen、PayPal、OpenAI、Cloudflare、Okta 等 35+ 设计伙伴，合著方含 Stripe、Shopify、Walmart）与**北京时间 2026-10-14 建仓**的 [GitHub 规范仓库](https://github.com/personal-agent-protocol/personal-agent-protocol)（head `f766ef8b…`）：定义 `/.well-known/poppy.json` 发现、OAuth metadata `poppy_domains` 双向防伪、OpenAPI/会话/Operations 强制 `DPoP`（RFC 9449）vs MCP 强制单服务端 `resource` 绑定 `Bearer`（RFC 8707），以及 [`operations` v1 扩展](https://personalagentprotocol.org/docs/extensions/operations)的两阶段 `proposed` → `revision` → 独立端点确认机制（明确禁止用对话消息确认操作）。官方 [`/docs/path-to-1`](https://personalagentprotocol.org/docs/path-to-1) 将 **Payments** 列为尚未定义的 Open Topic，并明确与 UCP 互补。
  - [Sierra Summit 2026（2026-10-06）](https://sierra.ai/blog/summit-recap-2026)、[`fleming-1` 语音 Agent 识别（2026-10-08）](https://sierra.ai/blog/caller-id-in-the-age-of-agents)、[Defense-in-Depth（2026-08-13）](https://sierra.ai/blog/defense-in-depth-in-the-age-of-agents)、[MCP Gateway（2026-07-22）](https://sierra.ai/blog/building-sierras-mcp-gateway-an-engineering-iceberg)、[Payments（2026-04-07）](https://sierra.ai/blog/payments) 与 [$\tau^2/\tau^3$-bench（`v1.0.1` / head `dd8757d4…`）](https://github.com/sierra-research/tau2-bench)：构成企业侧 Agent 的 PCI 旁路收款（Visa Level 1 PCI，LLM 零接触 CHD）、语音双速架构（Tandem Voice）及四层运行时护栏（Content → Rules → Supervisors → Deterministic Guards）。

## 2026-10-16 增量核验

完整证据、来源失败及代码变更见 [10-16 日研](daily/2026-10-16.md)。

- **Stripe MCP 密钥迁移期限正式延后 30 天（`2026-10-31` $\rightarrow$ `2026-11-30`）**：[Stripe MCP 官方文档](https://docs.stripe.com/mcp.md) 通告标题已更新为 `Update API key authentication by November 30, 2026`，正文改为 `Migrate by November 30, 2026. Starting in December, Stripe MCP will stop accepting full-access secret keys and restricted API keys without the Agent tag...`。其余 11 个 `docs.stripe.com/*.md` 页面哈希变化仅因站内链接追加 `.md` 后缀，并非新产品发布。
- **UCP 闭合“存在即必签”门禁修复（`#659` BREAKING CHANGE、`#795`、`#933`）**：官方提交 [`69e28f4f…`](https://github.com/Universal-Commerce-Protocol/ucp/commit/69e28f4fb7813aa6d268c604f0b7069c84418d64) 将 `webhook-id` 与 `webhook-timestamp` 纳入 IRA Step 5 闭合必签覆盖组件集，规定 `Webhook-Id` 为事件级标识且重试必须保留原始 `(Webhook-Id, Webhook-Timestamp)`，订单 Webhook 以完整状态快照按 `Webhook-Id` 去重、按 `Webhook-Timestamp` 排序收敛；[`5021fa83…`](https://github.com/Universal-Commerce-Protocol/ucp/commit/5021fa83a652ef9f1d00eb2b53e1de790f0a427f) 明确 Profile/JWKS/CIMD 抓取禁止 3xx 重定向但允许条件请求的 `304 Not Modified`。
- **Poppy `v0.1` 17 个规范提交（`f766ef8b…` $\rightarrow$ `e910c866…`）**：明确 `organization.domain` 仅按忽略大小写匹配重定向后主机名（不再剥离 `www.`，`#37`）；DPoP 对齐 RFC 9449（`dpop_signing_alg_values_supported` 含 `ES256`，令牌端点返回 `400`、API/会话端点返回 `401`，`#36`）；客户端与会话断言 `aud` 必须为 `auth.issuer` 单一字符串（`#50`）；Session 单账户绑定跨登出持久化（`#41`、`#49`）且吊销后禁止受托凭证自动重登（`#53`）；新增第 8 节《Security considerations》（`#51`）要求隔离企业不可信内容并核对操作 `summary` 与结构化 `terms` 一致。
- **Stripe AI 与 Sierra $\tau^3$-bench 增量**：`stripe/ai` 同步至 `ad3c5817…`（`agent-plugins 0.5.20`，新增 Billing 脚本参考并扩展加拿大 GST/HST 与爱尔兰欧盟 OSS 税务注册指南）；`sierra-research/tau2-bench` 更新至 `96a3ef92…`（新增 Salesforce Launa v1 原生音频适配器与 xAI Grok Voice 3.0 语音榜单提交）。Visa VIC 开发者页仍返回 HTTP 403。

## 2026-10-17 增量核验

完整证据、来源失败及代码变更见 [10-17 日研](daily/2026-10-17.md)。

- **Personal Agent Protocol（Poppy `v0.1`）发布企业实现套件与合规验证器（`#35`，[`95fcbf22…`](https://github.com/personal-agent-protocol/personal-agent-protocol/commit/95fcbf22c5991a0090061aed3dbeb68c0ea575e0)）**：新增 `kit/company/`（`implement-personal-agent-protocol` skill）、18 份 Draft 2020-12 JSON Schema（`dpop-proof.schema.json` 显式封禁 `"HS256"`/`"HS384"`/`"HS512"` 对称算法与私钥字段，断言 `jti` 长度 $\ge 22$）、10 篇企业架构集成模式及零依赖 TypeScript 合规验证器（`kit/company/validate/`）。明确令牌端点必须拒收 `typ: "poppy-browser+jwt"` 浏览器断言（`400 invalid_grant`），浏览器会话端点（`303 See Other`）必须通过 URL 解析校验 `return_to` 主机名匹配 `organization.domain`、设置 `Secure; HttpOnly; SameSite=Lax|None`（严禁 `SameSite=Strict`），且 `poppy:read` 与 `poppy:write` 完全正交、人工客服接管（Handoff）后仍受同一 Session Scopes 约束。
- **UCP Permalink `303 See Other` 强制安全响应头对齐（`#913`，[`3ab41043…`](https://github.com/Universal-Commerce-Protocol/ucp/commit/3ab41043b79373df33a6e2c377bc82a806175f78)）**：补齐 `docs/specification/permalink.md` 所有 `303 See Other` 示例中的 `Location`、`Cache-Control: no-store` 与 `Referrer-Policy: no-referrer`，防止 Permalink URL 中的买家 PII（邮箱、电话）通过缓存或 `Referer` 头外泄。`ucp.dev` 官网今日恢复 HTTP 200（`unchanged`）。
- **Stripe MCP 迁移期限核验与文档英式本地化渲染**：今日 `docs.stripe.com/*.md` 返回英式英语拼写与日期格式（`30 November 2026`），经核验政策事实未变（截止日期仍为 **`2026-11-30`**，距今 **44 个日历日**，12 月起停用旧 key）；其余 11 页哈希变化均源于英美拼写差异，所有 API/协议版本未变。`stripe/ai` 同步至 [`c1f5b082…`](https://github.com/stripe/ai/commit/c1f5b0826f3f33d7e1cc7eff5e5e6cd42749808b)（`agent-plugins 0.5.21`）。Visa VIC 开发者页仍返回 HTTP 403。

## 2026-10-18 增量核验

完整证据、来源失败及开放规范草案分析见 [10-18 日研](daily/2026-10-18.md)。

- **来源监控（扩充至 46 个来源）与 Stripe MCP 43 日窗口**：46 个来源中 45 个 `status="ok"`，`visa-vic` 仍返回 HTTP 403（`status="error"`, `change="unknown"`）。`stripe-commerce-docs` 发生真实内容更新，新增收录 5 个 Stripe 官方文档子页（`stripe-webmcp`、`stripe-booking`、`stripe-embedded`、`stripe-sftp-feed`、`stripe-directory`）；其余 10 个 `docs.stripe.com/*.md` 端点哈希变化源于英美拼写渲染切换（`November 30, 2026` vs `30 November 2026`），`stripe-spt` 因动态 `expires_at` 变化（API 版本仍为 `2026-09-30.preview`）。`stripe-mcp` 保持 `policy_change="unchanged"`，迁移截止日仍为 **`2026-11-30`**（距 2026-10-18 剩余 **43 个日历日**，距原定 `2026-10-31` 节点 13 天）。`stripe/ai` 同步至 [`24947f16…`](https://github.com/stripe/ai/commit/24947f1632eea27d0377c5047755f98838db6105)（`agent-plugins 0.5.22`），`modelcontextprotocol` 合入 [`1155ca46…`](https://github.com/modelcontextprotocol/modelcontextprotocol/commit/1155ca460e50bfaf3b7c00f2e10e3015f4e6a997)（`#3439`，确认 `SEP-2127` MCP Server Cards 状态为 `Final` 并修复 `SEP-2640` Skills Extension 链接）。
- **Stripe WebMCP、Service Bookings、Agent 侧 Embedded Commerce（OCA / RequestedSession / SFTP Feed）与 Directory**：
  - [WebMCP（Experimental）](https://docs.stripe.com/agentic-commerce/agents/webmcp.md) 支持在 Full page Checkout、Embedded form、Elements 与 Hosted invoice page 中动态发现浏览器工具，强制在切换支付方式后重新发现工具 Schema，并要求对带 `consequentialHint` 的支付提交工具先获用户显式确认。
  - [Service Bookings](https://docs.stripe.com/agentic-commerce/sellers/use-cases/booking.md)（点名パートナー Muse、Instinct）定义 `search_availability` $\rightarrow$ `create_booking`（`409 slot_unavailable`） $\rightarrow$ `complete_booking`（`Idempotency-Key` 保留 $\ge 24$h、SPT 最长 180 天有效期、兼容 UCP `com.stripe.payments` `2026-06-25`）。
  - [Embedded Commerce（Preview，33 国）](https://docs.stripe.com/agentic-commerce/agents/embedded.md?agent-checkout-mode=full) 与 [SFTP Catalog Ingestion](https://docs.stripe.com/agentic-commerce/concepts/catalog-feed/sftp-catalog-ingestion.md) 揭示双 API 版本并存：OCA（`/v2/orchestrated_commerce/agreements`，`2026-09-30.preview`；卖家发起、终止后仅终止方能重发起）与 Delegated Checkout `RequestedSession`（`/v1/delegated_checkout/requested_sessions`，`2026-04-22.preview`；卖家实时回调失败返回 `424 Failed Dependency`、协同 Visa Intelligent Commerce 与 Mastercard Agent Pay 申领网络令牌、严禁 Agent 编程操作 Affirm WebView 贷款 UI）；SFTP 目录以最后上传的 `manifest.json` 为完成屏障，`disable_checkout=true` 仅限跳转 `link`。
  - [Stripe Directory（Preview）](https://docs.stripe.com/directory.md) 与 [`stripe pay`](https://docs.stripe.com/cli/pay.md) 提供跨 Stripe Apps、Stripe Projects（`projects.dev`）、MPP（`mpp.dev`）与商户 `@handle` 的发现及 B2B 账上划转。
- **Poppy `operations` v1 全生命周期细则与 UCP/ACP 开放规范草案（区分已合并规范与未合并 PR）**：核验 Poppy `#35` `operations` v1（扩展协商、跨通道相同 `terms` 去重、下游超时驻留 `in_progress` + `Retry-After`、已登录跨 Session 共享 vs 未登录单 `session_id` 隔离）；核验 UCP 主分支 `buyer-consent.md` 与开放 PR `#660`（全量替换豁免）、PR `#912`（`requires_escalation` 携带 HTTPS `continue_url`）、PR `#940`（`create_checkout` 的 `cart_id` 互斥与禁静默回退）、PR `#783` / Issue `#970`（Accelerated IdP `subject_token` 绑定当前会话用户）及 PR `#966`（`policy.return` 禁止平台自算 `expires_at`）；核验 ACP PR `#316` Section 7.4a（ATDRP 证据包 fail-closed 准入与 `no_record` 沉默非验收规则）。

## 2026-10-19 增量核验

完整证据、51 个来源监控状态与六平面架构分析见 [10-19 日研](daily/2026-10-19.md)。

- **来源监控（扩充至 51 个来源，`50/51` `status="ok"`）与 Stripe MCP 42 日窗口**：新增收录 `stripe-spt-connect`、`stripe-how-it-works`、`stripe-mpp-sessions`、`stripe-token-billing` 与 `poppy-spec-v01-frozen`，并在 `scripts/source_monitor.py` 中注入 `"Accept-Language": "en-US,en;q=0.9"` 消除 `docs.stripe.com/*.md` 的 APAC 日语 Geo-IP 漂移。`stripe-mcp` 保持 `policy_change="unchanged"`，迁移截止日仍为 **`2026-11-30`**（距 2026-10-19 剩余 **42 个日历日**，距原定 `2026-10-31` 节点 12 天）。仅 `visa-vic` 仍返回 HTTP 403（`status="error"`, `change="unknown"`）。
- **Personal Agent Protocol（Poppy）冻结 `v0.1` 并开启 `v0.2` 草案（`#54`, `#57`–`#70`, [`30c476455c20`](https://github.com/personal-agent-protocol/personal-agent-protocol/commit/30c476455c2017b09d44675029850b09778d243c)）**：定义同主版本向后兼容（`0.2` 客户端支持 `0.1` 企业，`#66`）、全协议 URL 强制 `https` 且禁 `#fragment`（`#67`）、除两处发现端点外严禁跨 `3xx` 重定向自动转发凭证（`#68`）、企业令牌端点支持 `"none"`（默认）或 `"private_key_jwt"`（`#62`）、断言强制 `iat` 5 分钟窗口 + 按 User ID 隔离 DPoP 密钥 + `poppy-browser+jwt` 单次 `jti` 防重放（`#68`/`#69`）、允许声明 `dpop` 能力的 MCP 服务器直接复用 `DPoP` 会话令牌并要求过期令牌直接返回 `401 invalid_token`（`#64`/`#69`）、未登录会话禁发 `operations`（`#59`）以及 `CapabilityFeedback` 标准反馈 schema（`#70`）。
- **UCP 2026-10-19 6 项合入（`#881`, `#755`, `#731`, `#784`, `#912`, `#963`, [`29e2d562ec0e`](https://github.com/Universal-Commerce-Protocol/ucp/commit/29e2d562ec0ea4a8274d3d5bb51a9c911df1a1be)）**：新增 `dev.ucp.shopping.deferred_payment`（支持 Net-30/60/90、定金与分期，强制 `due_now + sum(deferred) == total`，`#881`）；Identity Linking 仅允许 `authorization_code` 与 `refresh_token` 并移除 `client_credentials`（`#755`）；所有返回 `201 Created` 的创建型 POST 强制携带 `Location` 头（`#731`）；正式合入 `requires_escalation` 条件必填 `continue_url`（`#912`）。
- **Stripe Shared Payment Tokens（SPT）三角色变体（Seller / Agent / Connect）、SPT Resolve 与三大卡组织协同**：
  - [Connect 平台视图（`?agent-seller=connect`）](https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens.md?agent-seller=connect)：Direct charges 必须传入关联商户 `network_business_profile` 并在创建 `PaymentIntent` 时携带 `Stripe-Account` 头；Destination charges / Separate charges and transfers 默认传入平台档案，但配合 `on_behalf_of` 时推荐传入关联商户档案。
  - [外部 PSP 卖家 `SPT Resolve`（`?agent-seller=seller`）](https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens.md?agent-seller=seller)：`POST /v1/shared_payment/granted_tokens/{id}/resolve` 严格限单次调用（single-use only），返回 `fpan`/`network_token`/`agentic_token`/`dpan` 与 `CAVV`/`TAVV`/`DCVV` 密文，并列点名 **Mastercard Agent Pay**、**Visa Intelligent Commerce** 与 **American Express ACE Kit**；自定义 RSA 加密使用 `encryption_block_fields`（`<field>:<start>:<length>`）。
  - [Agent 侧状态机（`?agent-seller=agent`）](https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens.md?agent-seller=agent)：`active` $\leftrightarrow$ `requires_action`（3DS 阶梯认证通过 `stripe.handleNextAction({ hashedValue })` 恢复）$\rightarrow$ `deactivated`（不可逆终态）。
- **Stripe MPP Tempo 流式微支付会话、Token 计费与 `stripe/ai 0.5.23`**：[MPP Sessions（`2026-07-29.preview`）](https://docs.stripe.com/payments/machine/mpp/sessions.md) 支持 `0.000001 USDC` 最小计价精度，但向 Stripe Balance 仅按整美分（$\ge \$0.01$）结算，**会话关闭或非整美分倍数结算周期产生的亚美分尾差将被直接没收（forfeited）**；[Token Billing](https://docs.stripe.com/billing/token-billing.md) 基于 Metronome 提供按输入/输出/缓存 Token 计量与 AI Credit Packs；`stripe/ai` 升至 [`2f68b6e13cea`](https://github.com/stripe/ai/commit/2f68b6e13cea1a0745d5594ef901b957557a939a)（`0.5.23`，新增澳大利亚 GST 税务指南）。
- **上游开放规范草案（Google AP2 `#165`/`#369`/`#385`、UCP `#866`、ACP `#316` Appendix C `b998b915638a`）**：AP2 PR `#165` 定义四态受托熔断器（`CLOSED` $\rightarrow$ `OPEN` $\rightarrow$ `HALF_OPEN` $\rightarrow$ `TERMINATED`），PR `#369` 定义多跳委托链终端 `SD-JWT+KB`（`typ: "kb+jwt"`）；UCP PR `#866` 定义 `dev.ucp.common.feed` RFC 9530 分片摘要校验与残缺分片零删除保证；ACP PR `#316` Appendix C（`b998b915638a` 更新 Nuvei Chargeback DMN 关联）确认 **7/17** 家网关支持争议关联原支付、**2/17** 家记录支付侧 Agent 信号、**0/17 家网关具备发卡行侧结构化 Mandate 字段**。

## 2026-10-22 增量核验

完整证据、50 个来源监控状态与 Stage 168–169 技术资产见 [10-22 日研（中文）](daily/2026-10-22.md) / [English (`2026-10-22.en.md`)](daily/2026-10-22.en.md)。

- **来源监控（`49/50` `status="ok"`）与 Stripe MCP 39 日窗口**：`stripe-mcp` 保持 `policy_change="unchanged"`，迁移截止日仍为 **`2026-11-30`**（距 `2026-10-22` 剩余 **39 个日历日**，距原定 `2026-10-31` 节点 9 天）。`visa-vic` 仍返回 HTTP 403（Akamai WAF）；`visa-tap` 与 `visa-tap-specs` 的哈希变化经核验为 Visa 开发者门户前端 `Prism.manual` 壳层提交（`bca825d` / `TLVDPIA-207`），TAP 规范正文零改动。
- **Stripe 周期性 Shared Payment Token（Recurring SPT）官方新规（`cf14fd45f193`）与 UCP Handler（`cf6014bea229`）**：当 SPT 包含 `usage_limits.recurring_interval`（如 `"month"`）时，卖家在后续周期扣款中直接复用同一授权 SPT 创建 `PaymentIntent`；**在使用 SPT（含周期性 SPT）创建或确认 `PaymentIntent` 时，Stripe 显式拒绝 `setup_future_usage` 与 `payment_method_options[card][setup_future_usage]`**，并独立校验 `off_session` 是否获该 SPT 授权。`stripe-ucp-handler` 明确 `POST https://commerce.stripe.com/api/ucp/tokenize` 省略 `expires_at` 时默认有效期为 1 小时，且当前 handler 不支持完成 `link` 支付。
- **x402 Foundation、UCP、`stripe/ai` 与 Sierra $\tau$-bench 2.0 当日合入**：
  - `x402-foundation/x402` 合入 `#3285`（`3ca54cb` 严格 V2 CAIP-2 正则 `^[-a-z0-9]{3,8}:[-_a-zA-Z0-9]{1,32}$`）、`#3400`（`76f2f28` Facilitator 控制面 1 MiB / 发现面 4 MiB 流式响应体上限）、`#3826`（`bc31d3e` `createPaymentRequiredResponse` `extensions` 浅拷贝）、`#3567`/`#3715`（Bazaar HTTP 动词与输入 Schema 对齐、V1 载荷返回 HTTP 402）、`#3674`（`d8e1e7b` Cardano 原始 CBOR 字节保真防 Conway Tag-258 见证失效）与 `#3125`/`#3293`（`332f65d` Stellar `TRY_AGAIN_LATER` 可重试结算分类）。
  - `Universal-Commerce-Protocol/ucp` 合入 `#940`（`2bbae24` 支持仅传 `cart_id` 创建 Checkout、同传时以 Cart 为权威、未协商 `dev.ucp.shopping.cart` 时传 `cart_id` 强制报错）与 `#966`（`4aa3127` 显式 `eligibility.type`、商家声明退货截止期与分类 `fees[]`）。
  - `stripe/ai` 升至 `8.0.4`（`326ea8b`）并在 PR `#581` 修复工作线程 `StripeTool._run` 事件循环回退；`sierra-research/tau2-bench` 合入 `#640`（`05736c2` `voice-v2`）并推进 `#667`（阻断零售 `item_id == new_item_id` 自换）、`#666`（阻断电信空白 `mmsc_url`）、`#671`（`.gitattributes` `eol=lf` 保护冻结基准哈希）与 `#670`（Phonic `mulaw_8000` 语音发言窗口门禁）。

## 2026-10-23 增量核验

完整证据、50 个来源监控状态与 Stage 170–171 技术资产见 [10-23 日研（中文）](daily/2026-10-23.md) / [English (`2026-10-23.en.md`)](daily/2026-10-23.en.md)。

- **来源监控（`49/50` `status="ok"`）与 Stripe MCP 38 日窗口**：`stripe-mcp` 保持 `policy_change="unchanged"`，迁移截止日仍为 **`2026-11-30`**（距 `2026-10-23` 剩余 **38 个日历日**，距原定 `2026-10-31` 节点 8 天）。`visa-vic` 仍返回 HTTP 403（Akamai WAF）；`stripe-spt` 哈希变化经核验为英式拼写渲染与沙箱动态示例 `expires_at` 跳变，昨日新增的周期性 SPT（Recurring SPT）规范正文未变；6 个 `sierra-*` 博客页哈希变化仅因页脚“Related Articles”推荐卡片轮播。
- **x402 Foundation、UCP、`stripe/ai` / MCP 与 Sierra $\tau$-bench 2.0 当日推进**：
  - `x402-foundation/x402` 合入 `#3023`（`2b06a54` XRPL `upto` 支付通道规范：`xrpl:0`/`1`/`2` 数字 CAIP-2、链下 `CLM\0` 索赔签名、`/verify` 禁带 `settlementTransaction` 与 `Balance == 0` 及 `20s` 着陆裕度、`/settle` `maxAmount` 上界替换与零增量裸 `tfClose` 及 `(network, channelId)` 并发互斥）、`#3738`/`#3809`（`3bd3c1d`/`58a5d7d` 无方法通配路由跳过 `OPTIONS` 预检并暴露浏览器 CORS 头）、`#3096`（`470419d` 批量结算退款缺 `Refunded` 事件 Fail-Closed）、`#3459`/`#3889`（EVM 燃气代付强制 `readContract` 或 `rpcUrl`）、`#3855`（`a9772e5` Paywall HTML 配置 XSS 转义）及 PR `#3910`（`payer != payTo` 反自付刷量洗钱）。
  - `Universal-Commerce-Protocol/ucp` 合入 `#672`（`5410813` 对齐 Checkout 状态机图，`ready_for_complete` 四出边覆盖 `complete_in_progress`/`completed`/`incomplete`/`requires_escalation`），并推进 PR `#890`（`dev.ucp.shopping.purchase_options` 远期订阅 `schedules[]` 当期结账应付为 `0`）、PR `#699`（签名 REST 响应绑定请求 `@method`/`@target-uri` 防旧价重放）与 PR `#782`（分操作类别幂等键语义与签名 MCP 请求 HTTP `Idempotency-Key` 头权威优先）。
  - `stripe/ai` 升至 `8.0.5`（`8a8818e` 指引在沙箱创建受限密钥 RAK），推进 PR `#584`（`@stripe/mcp` 代理通过 `registerTool` 保留 `destructiveHint`/`readOnlyHint` 注解）、PR `#542`（`buildForwardingErrorResponse` 在转发 JSON-RPC 请求失败时立即返回错误避免 60s 挂起）与 PR `#540`（`mcp>=1.8.0,<2`），配合 MCP PR `#3415`（`SEP-3415` Events 扩展 `events/poll` 截断标志与 Standard Webhooks 订阅验签）。
  - `sierra-research/tau2-bench` 合入 `#675`/`#676`/`#670`（`cc1df47` Avartha `Ava Zero` 与 Phonic `phonic-1`），并推进 PR `#674`（畸形工具参数与空白回复按 `AGENT_ERROR` `0.0` 分计入分母）与 PR `#677`（剥离零售 `known_info` 中的内部主键 `mei_kovacs_8020`）。



