# 架构与协议映射

## 范围

面向 Personal Agent 的建议参考架构，不是 Visa/Stripe 官方参考架构，也不是已部署系统。证据基线见 [2026-10-09 日报](../research/daily/2026-10-09.md)，来源编号见 [登记表](../research/sources.json)。

## 分层，而非“一个协议统治所有支付”

| 层 | 代表技术 | 负责什么 | 不负责什么 |
|---|---|---|---|
| 推理与工具 | 模型、MCP、A2A；Stripe plugins/skills | 发现能力、规划、调用工具 [S13, S14] | 用户支付授权、结算或商户合规 |
| 商业语义 | ACP、UCP | 目录、cart、checkout、订单与能力协商 [S15, S16, S18] | 默认信任任意 Agent 或付款凭证 |
| 请求可信性 | Visa TAP、RFC 9421 | 签名、上下文绑定、可信 Agent 识别 [S03–S05, S21] | 仅凭签名证明支付成功或用户同意全部金额 |
| 可验证委托 | AP2；VIC payment instruction | 可验证的具体意图、消费者同意与指令约束 [S02, S19] | 替代库存、税务和支付结果对账 |
| 支付能力 | Stripe SPT、Link Agent Wallet、VIC token | 受限凭证、钱包、支付指令/网络控制 [S02, S11, S12] | 对所有国家、卡种和账户保证开放 |
| 机器付费 | MPP；Stripe 提及 x402 路径 | 付费资源 challenge/credential/receipt [S10, S17, S20] | 实物交易完整履约、自动解决结算终局性 |
| 产品接入 | Stripe Suite、Visa Connect | 简化多渠道或多网络接入 [S06, S08, S09] | 取代底层协议版本、责任及可用性审查 |

ACP/UCP 和 MPP 存在不同对象及生命周期；不能只改 JSON 字段名就认为完成互操作。AP2 当前首页描述 open/closed Checkout Mandate 和 Payment Mandate；与旧资料术语不一致时要锁定具体 revision，不拼接两代规范。[S19]

## 组件和信任边界

| 组件 | 输入与输出 | 必须执行的边界 |
|---|---|---|
| Personal Agent | 用户目标、商品数据 → 推荐和动作提案 | 商户内容、网页和工具返回是数据，不是系统指令；模型不能自批 |
| Catalog/quote adapter | ACP/UCP 或商户 API → 内部报价 | 版本协商；区分预估与最终价格；库存、税、运费由商户确认 |
| Consent UI + mandate service | 用户身份/最终报价 → 授权证据 | 可信 UI 认证；Agent/商户/币种/购物车/金额/期限绑定；撤销 |
| Policy gate | 提案 + 授权 + 已使用额度 → allow/deny | 单笔及长期累计预算；风险阈值；权限收窄，不能从 prompt 扩权 |
| Payment broker | 批准指令 → 支付凭证引用/提交结果 | 密钥与原始支付数据不进入模型上下文；明确 live/test；最小权限 |
| Merchant ingress | TAP 请求 → 已验证请求 | 公钥可信来源、签名 component、nonce/期限/域名与动作验证 |
| Order orchestrator | 支付与商户事件 → 持久订单状态 | 幂等键、outbox/inbox、查询与对账，timeout 不直接标记失败 |
| Audit/reconciliation | consent、quote、提交、receipt → 证据/差异 | 脱敏、保留期、访问控制、重复/乱序 webhook 处理 |

凭证 API、工具 API 和同意服务应是不同权限主体。Stripe MCP 管理账户的 OAuth/session 与 Link 消费者 OAuth 是两条认证链；不能互换凭证或合并审批。[S12, S14]

## 人在场购物链路

1. Agent 搜索、比较，商户提供最终 checkout 报价；模型不得自行算出一个价格后当作商户承诺。
2. 用户在可信界面批准最终商品、数量、商户、含税/运费总价、币种和有效期；AP2/VIC 如接入则使用其真实认证/委托机制。
3. Policy gate 验证提案与批准范围。任何变价、SKU/数量/收款商户变化必须重新批准，即使仍低于最高金额。
4. Payment broker 获取受限凭证：SPT / Link credential / VIC 路径按商户与账户资格选择；不要把 token 当作身份证明。
5. 商户请求通过 TAP 等可信入口（若该商户支持），按 ACP/UCP 的已协商契约创建/完成 checkout。
6. 遇到 SPT `requires_action` 或 issuer challenge，交回用户完成。`active`、HTTP 200、模型“购买成功”都不是订单成功依据。
7. 支付结果与商户订单结果分别落盘。超时进入 `unknown/pending_reconciliation`，先按同一 provider reference 查询；重复提交只能使用原幂等语义。
8. 授权、捕获、结算、履约、退款独立跟踪；用收据和商户事件对账，保留争议所需最少证据。

## 实施与选型建议

| 需求 | 首选实验路径 | 生产前门槛 |
|---|---|---|
| 已有 Stripe 商户，进入 Agent 分销 | Suite + ACP/UCP 文档映射 | 渠道开放资格、catalog、checkout、消费者 challenge、订单事件 |
| 商户希望接纳网页购物 Agent | TAP 验证参考实现 | 可信 key discovery、CDN 覆盖、nonce 存储、撤销及隐私审查 |
| 构建持卡消费者 Personal Agent | VIC / Link 路径分别评估 | onboarding、用户认证、地区、一次/长期批准模型、dispute 责任 |
| 多网络、多 token vault enabler | Connect 可用性评估 | pilot/GA 契约、网络与 vault 支持矩阵、PCI 边界 |
| 提供机器付费 API | MPP 小额/聚合计费实验 | method minimum、费用、budget、receipt、未交付退款和对账 |

目前复用仓库已有离线 Personal Agent 与持久化 JSON workflow 比另建一套支付引擎或立即拆微服务更合适。具体实现以 [已有架构与实验说明](architecture.md) 为准。未来生产建议为事务型授权/订单存储 + outbox worker + 供应商 adapter，依据隔离与扩展需求再拆服务，而不是把模型、数据库和凭证部署在同一工具进程。

## 非功能目标：建议而非现有测量

| 关注项 | 建议目标 / 决策 | 权衡与验证 |
|---|---|---|
| 可靠性 | 不确定支付状态绝不当作可安全重付；授权与本地 ledger 原子更新 | 外部 PSP 不在数据库事务内，需要 outbox/reconciliation；不能宣称端到端 exactly-once |
| 安全与隐私 | 越权支付为 0；拒绝 prompt 注入扩权；凭证不进入模型 | 需要身份认证、真实签名与供应商网络控制；本地 hash 不提供来源认证 |
| 成本 | 单任务预算包含模型、工具和支付费用 | 先设成本上限，再选择 MPP session/聚合；不假设卡支付适合微额 |
| 运维 | 每笔有 correlation ID 和可恢复状态 | 审计脱敏、保留期与用户删除要求需协调，不能无限保存 PII |
| 性能 | 单独度量 policy p95、商户 quote p95、端到端批准耗时 | 人工/issuer challenge 不适合与纯 API SLA 混为一谈 |
| 恢复 | 为 RTO/RPO、容灾与额度一致性制定业务目标 | 多区写入易产生双花/超预算，需要明确一致性模型 |

本仓库只验证 [本地实验约束](architecture.md)，上述生产控制尚未落地。每日记录校验方式见 [维护说明](daily-research.md)。AI 辅助方案不构成供应商认证或合规意见。
