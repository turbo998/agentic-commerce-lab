# 产品、协议与框架选择

证据截止本次核验日 2026-10-10；live docs 可能变化。来源与版本锚点见 [登记表](../research/sources.json)，具体产品事实见 [当日研究](../research/daily/2026-10-10.md)。

## 决策矩阵

| 需求 | 首先评估 | 配合而非替代 | 实际集成门槛 |
| --- | --- | --- | --- |
| 商户在多个 AI 界面卖商品 | Stripe Agentic Commerce Suite | ACP/UCP、现有 OMS/PSP、税与履约 | 商户资格、平台 onboarding、catalog 同步、Agent 部分 private preview |
| 自建可移植 checkout | 固定日期 ACP 或 UCP capabilities | payment handlers、TAP（视商户要求）、用户授权证据 | schema、版本协商、商户执行与回调；开放规范不等于每个 surface 支持 |
| 商户区分商业 Agent 和恶意 bot | Visa TAP + registry/verifier | CDN/bot controls、checkout、授权策略 | HTTP Message Signatures、真实信任根、replay cache、域/目的绑定 |
| 已有多网络卡处理/多 vault | Visa Intelligent Commerce Connect | Acceptance Platform、TAP/ACP/UCP/MPP | 商业合作资格、地区与 method availability；公告不能视为已实测 |
| 消费者授权 Agent 花钱 | Link agent wallet / scoped credentials | SPT、商户/商品策略、AP2 意图证据 | 人工批准、撤销、限制、实际国家/账户支持 |
| Stripe 商户接收 delegated credential | Shared Payment Tokens | PaymentIntent、批准 quote、webhook 去重 | Stripe profile、preview API、使用限制和地区资格 |
| API/内容按请求收费 | MPP 或 x402 的对应 SDK | spending policy、entitlement、metering | 协议格式独立；最小额、结算方式、重试和资源交付一致性 |
| 商户财务运维 Agent | Stripe MCP、plugins、skills、billing SDK | 只读分析先行、工具 allowlist、人工审批 | 运维账户 OAuth/API 权限不是消费者付款同意 |

## 固定版本与互操作

ACP 当前代码基线观察为 `7fdd78df677a94dce04c770644b0fbbb1401272b`；规范快照选 `2026-04-17`，仓库仍标 beta。[固定代码锚点](https://github.com/agentic-commerce-protocol/agentic-commerce-protocol/tree/7fdd78df677a94dce04c770644b0fbbb1401272b)。新版本应单独跑 contract tests，而不是直接升级 `unreleased`。

TAP 样例代码锚点为 [16d59bdf…](https://github.com/visa/trusted-agent-protocol/tree/16d59bdf3f8a542bc538d0962edbb80ea30a02af)。样例 README 展示 registry、CDN proxy、merchant backend/frontend、tap-agent 五组件；它不是本仓库的运行时依赖，也未在本次执行。使用真实规范时确认 canonicalization、签名覆盖字段、密钥解析、时钟容差和 nonce 生命周期。

UCP capabilities/payment handlers 与 API/MCP/A2A bindings 是协议机制；AP2 是委托证据体系；TAP 是入口信任；SPT 是 Stripe-specific credential。一个商户可以组合其中部分，**本研究没有验证任意组合的 wire-level 互操作性**。

HTTP Message Signatures 参考 [RFC 9421](https://www.rfc-editor.org/rfc/rfc9421.html)。TAP 与 IETF/OpenID/EMVCo 的对齐意向不意味着 TAP 本身已成为这些组织的最终标准。AP2/UCP/ACP 的“open”也不等于所有账户都可以进入支付生产环境。

## Adapter 的最小契约

建议内部接口分为 `discover_capabilities`、`quote_cart`、`request_approval`、`get_scoped_credential`、`complete_checkout`、`get_order`、`reconcile`、`refund`。每个 adapter 独立处理 provider schema，不用同一个通用 `pay()` 掩盖 authentication/pending/unknown 状态。

本地 `Checkout.grant/complete/revoke` 只验证教学不变式，没有实现这些 provider adapters。真实集成应对 pinned provider schema、unsupported capability、preview 版本、webhook signing、回调重放以及部分履约追加 contract/integration tests。
