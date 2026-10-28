# Stage 1652：支付响应丢失后，重启不能重新获得扣款权限

[English](2026-10-28-authority-recovery.en.md) | [当日日报](../../research/daily/2026-10-28.md)

**核验日期：2026-10-28，北京时间；夜间增量，基线 `1d9273d`。**
本阶段交付公开资料研究与离线恢复参考资产，不是供应商发布、
互操作认证、真实支付接入或模型 benchmark。保留用户的 README 与 SVG
重构，不延续未经本轮独立核验的历史 PR/仓库规模或性能结论。

## 当前一手来源：五种权限证明不能合并为 `authorized=true`

| 产品/协议 | 本轮直接核验的事实 | 不能由此推出 |
|---|---|---|
| Visa TAP | RFC 9421 请求签名承载可信 Agent、意图、消费者识别及可选支付信息；[官方示例](https://github.com/visa/trusted-agent-protocol/blob/16d59bdf3f8a542bc538d0962edbb80ea30a02af/merchant-backend/app/routes/cart.py#L248-L270)明确是 mock payment processing | 验签或示例 `processed` 不是发卡行批准、真实扣款或结算证明 |
| Sierra Poppy | Account/Session Token 与 OAuth scope 控制账户访问；Draft 0.3 的 `auth.scope_hints` 有 `changes` 和 `personal_data`，明确只是公司声明，不是用户批准 | 收到聊天指令、`changes=none` 或 `personal_data=false` 都不是本次动作授权 |
| Stripe MCP | 商户账户的 OAuth / Agent API key 权限；当前文档确认 **2026-11-30 前迁移**，12 月开始拒绝 full-access secret keys 与无 Agent tag 的 restricted keys | 这不是所有 Stripe API 密钥失效，也不是消费者购买同意 |
| Stripe SPT | 支付凭据访问受接收商户、金额、币种和期限约束；支持 recurring SPT，但第三方处理商 Resolve 仍只能一次 | `active`、Resolve 或拿到凭据不是 PaymentIntent 成功，更不是结算 |
| 支付结果与余额 | PaymentIntent 区分 `requires_action`、`processing`、`requires_capture`、`succeeded`；余额另分 `pending` / `available` | 支付完成不等于资金已到账商户银行，也不等于履约完成 |

来源与版本边界：

1. Visa [TAP 开发文档](https://developer.visa.com/docs/trusted-agent-protocol)、
   [TAP 公告](https://corporate.visa.com/en/sites/visa-perspectives/newsroom/visa-unveils-trusted-agent-protocol-for-ai-commerce.html)、
   [Intelligent Commerce 公告](https://corporate.visa.com/en/sites/visa-perspectives/newsroom/product-drop-intelligent-commerce.html)。
   VIC 的消费者控制/网络能力与 TAP 的可信通信应分开；本轮 VIC 详细开发页
   返回 **403**，未核实完整 API、生产准入与 settlement 契约。
2. Sierra 于 **2026-10-06** [宣布 Personal Agent Protocol](https://sierra.ai/blog/introducing-personal-agent-protocol)，
   **2026-10-09** [介绍 Poppy 初始草案](https://sierra.ai/blog/poppy)。
   [版本记录](https://github.com/personal-agent-protocol/personal-agent-protocol/blob/a95b757872533a6ef1e1a9bcf29802857d2e5ff4/content/versions/versions.json)
   将 0.2 登记为 **2026-10-24** 发布；
   [changelog](https://github.com/personal-agent-protocol/personal-agent-protocol/blob/a95b757872533a6ef1e1a9bcf29802857d2e5ff4/content/shared/changelog.mdx#L3-L11)
   的 0.3 仍是 **In progress**，不是正式稳定版。
   [scope hints 原文](https://github.com/personal-agent-protocol/personal-agent-protocol/blob/a95b757872533a6ef1e1a9bcf29802857d2e5ff4/content/versions/0.3/spec.mdx#L772-L808)
   与[聊天动作授权边界](https://github.com/personal-agent-protocol/personal-agent-protocol/blob/a95b757872533a6ef1e1a9bcf29802857d2e5ff4/content/versions/0.3/spec.mdx#L1913-L1915)
   使用固定提交快照，未将工作草案当作已发布规范。
3. Stripe [MCP 认证](https://docs.stripe.com/mcp)、
   [Agent keys](https://docs.stripe.com/keys#agent-keys)、
   [SPT Agent 侧](https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens.md?agent-seller=agent)
   与[商户侧](https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens.md?agent-seller=seller)。
   文档示例 `2026-09-30.preview` 是 API 示例版本，不是发布日期或 GA 证明。
   Agent key 审批规则属于商户运营控制面，不能替代消费者同意。
4. Stripe [PaymentIntent 生命周期](https://docs.stripe.com/payments/paymentintents/lifecycle)、
   [余额与 settlement time](https://docs.stripe.com/payments/balances#balance-states)；
   这些状态映射不能未经核验外推到其他支付轨道。

## 1. 三层部署拓扑不等于 Well-Architected，AI-native 也不等于多 Agent

[AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html)
是架构质量与取舍的评估框架，不规定展示层、应用层、数据库层的唯一拓扑。
[Generative AI Lens](https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/generative-ai-lens.html)
已覆盖过度代理权、追踪、可靠通信、故障处理与制品版本化。不能把这些原则
描述为不适用于 AI，或把“三层应用一定会重复扣款”当作对照实测。

Agentic Commerce 的增量是把这些原则落实为**经济副作用不变量**：

| 边界 | 常见不足，而非三层架构的必然缺陷 | 商业 workload 的设计要求 |
|---|---|---|
| 推理与执行 | 模型重述“再试一次”生成新操作 | 可信执行层持久化逻辑操作与不可变请求绑定 |
| 身份与同意 | 将已认证 Agent 当成消费者已批准 | 身份、用户批准、支付凭证范围分别验证 |
| 工具与资金权限 | 将工具可调用或 scope 提示当成付款权 | 最终金额、商户、用途、有效期与撤销状态在执行点检查 |
| 本地事务与远端支付 | 本地没写 receipt，就推断没扣款 | 发送前落盘；无响应即 `unknown`，不新建扣款恢复 |
| 支付结果与履约 | 把支付确认当成交付、清算或退款完成 | 资金、订单、履约、退款状态独立建模与对账 |

这些逻辑边界可以先存在于模块化单体，不要求拆成六个微服务。
模型 failover 可以换推理服务，不能自行更换收款方、凭证或支付幂等键。

## 2. 从“检查重试参数”到“持久化恢复事实”

已有 [`CheckoutStore`](../../lab/checkout.py) 原子消耗本地模拟批准并生成
`simulated` receipt；这不意味着它能原子提交外部支付。
已有 [lost-response guard](../../lab/mcp_lost_response_retry_routing_digest_tau2_loan_servicing_ucp_token_context_donations_guard.py)
检查调用者传入的重试事实，但不持久化 dispatch。

新增 [`PaymentAttemptJournal`](../../lab/payment_attempts.py) 复用 `Checkout`
的整数最小货币单位与本地购物车摘要，独立记录：

- 不可变的租户、逻辑操作、批准引用、provider/account、provider 幂等键与购物车绑定。
- `BEGIN IMMEDIATE` 事务内只授予一次本地 dispatch 决策，同时落盘 `unknown`。
- 重启、超时、重复请求与已确认失败都不能重新取得 dispatch 决策；
  改 key/operation 也不能在同租户重用原批准。
- provider 幂等键和 payment reference 按 provider/account 隔离，不能跨租户
  将同一 provider 请求或支付结果重新绑定到另一操作。
- 可信对账入口记录 `pending → unknown`、`succeeded` 或 `failed`；
  terminal 结果和 provider reference 不能被矛盾事件覆盖。

本地状态转换：

```text
no record -- trusted reserve + commit --> unknown [one dispatch decision]
unknown  -- no response / pending -----> unknown [no new dispatch]
unknown  -- trusted provider result ---> succeeded | failed
terminal -- identical result ---------> same terminal [no new dispatch]
terminal -- contradictory result -----> explicit AttemptConflict
```

**安全与活性取舍：** 在本地提交后、实际发送前崩溃，也必须保留 `unknown`。
这可能导致未发送操作停留待人工核实；资产刻意不通过“换 key 重发”解决。
单机 SQLite 的唯一决策不等于远端 exactly-once，也不能阻止恶意调用者
重放曾经取得的发送决定。真实 adapter 必须独立实现认证、撤销/到期检查、
provider 幂等保留期限、可信状态查询与签名 webhook 验证。

[Stripe 低层错误处理](https://docs.stripe.com/error-low-level#network-errors)
明确网络错误不能证明原操作未执行，HTTP 500 的结果也可能未决。
其 [POST/幂等说明](https://docs.stripe.com/error-low-level#post-requests)
允许在 provider 规则内使用**持久化的同一个 key** 重试，包括跨进程重启；
本资产“一次 dispatch 决策”是**更保守的本地策略，不是 Stripe 的强制要求**。
API v1 幂等结果至少保留 24 小时，移除 key 后重用可能成为新请求；
原操作长期未决应查询与对账，而非自动重发。API v2 语义不同，
不能把 v1 的窗口作为所有 Stripe API 的统一规则。

## 3. 可运行资产与验收边界

```powershell
python -m lab.payment_attempts
python -m unittest tests.test_payment_attempts tests.test_checkout -q
```

演示明确输出 `synthetic=true`、`real_payments=false`、
`after_restart.dispatch_allowed=false`、`outcome=unknown`，
可信合成对账后才出现 `succeeded`，且始终
`settlement_verified=false`。测试见
[`tests/test_payment_attempts.py`](../../tests/test_payment_attempts.py)。

适合采购、补货、售后退款等有经济副作用工作流的**恢复设计练习**；
不是 TAP/SPT/Poppy wire-format 实现，也不自动验证批准来源、scope、
数字签名、settlement finality 或库存履约。`approval_id` 仅为可信调用方传入的
单次批准引用，不能把它直接暴露给模型当作自助批准接口。

## 4. 证据边界与下一步

观测时间不等于发布日期；文档存在不等于账户、地区或 preview 功能已获准。
历史日报中的发布时间、迁移截止期与协议版本必须由当前一手来源逐项核实。
本阶段不生成新的模型评测报告、延迟坐标或生产就绪分数。
生产化后续包括独立批准服务、签名事件入站、分布式 outbox/恢复 worker、
provider 特定状态映射和不可篡改审计，而非增加更多可自行付款的 Agent。
