# Personal Agent 商业参考架构

这是一份供应商中立的原创设计，不是 Visa/Stripe 官方架构。当前实现只有 [离线实验](../lab/commerce.py)，不部署云、不使用模型或真实付款。

## 模块与信任边界

| 模块 | 输入/输出与责任 | 约束 |
| --- | --- | --- |
| 用户界面/Consent | 购买要求、明确同意、授权撤销 | 批准动作不由 LLM 冒充；人工确认保存最终 quote 证据 |
| Personal Agent | 检索、比较、建议 cart、解释原因 | 商品描述和网页为不可信数据；不能修改授权和直接访问密钥 |
| Policy/Delegation service | merchant、商品、数量、累计预算、币种、时间窗口 | 确定性判断；所有执行入口都检查；无权限时显式拒绝 |
| Commerce adapter | ACP/UCP → 内部 Quote/Checkout/Order | 日期版本固定、capability 协商；库存/税/运费/折扣由商户重算 |
| Merchant trust boundary | TAP verifier、Agent registry、trusted headers | 检查签名、目标、目的、期限、唯一性；外部伪造 trusted headers 必须剥离 |
| Credential broker | 用户批准 → scope-limited credential reference | 原始卡数据不进入 prompt、日志或仓库；支付凭证不等于商品授权 |
| Payment adapter | Stripe SPT/PaymentIntent 或获资格的 Visa 集成 | 独立 adapter；明确 authentication_required、pending、failed；不假定同步结算 |
| Order/Recovery service | durable 状态、outbox、webhook、对账、退款 | event 去重、签名校验、重试预算；超时先查询，不盲目再扣款 |
| Observability/Audit | trace、策略结果、凭证引用的脱敏标识、订单事件 | 隔离租户，限制保留期限；证据可复查，避免保存秘密和敏感购物信息 |

**最关键边界：** Agent 请求 ≠ 用户批准；TAP 验证通过 ≠ 授权扣款；支付授权成功 ≠ 结算；结算 ≠ 已履约；自动退款 ≠ 所有副作用都已撤销。

## 推荐执行顺序

1. 发现商户 capabilities；从商户取得包含税费运费的最终 quote，检查库存及期限。
2. 用户或已有受限 delegation 批准具体 quote；确定性策略服务保存批准范围与 fingerprint。
3. 需要 TAP 的商户，在真实 verifier 通过后才处理 Agent 请求；消费者身份数据按同意最小披露。
4. Credential broker 获得 scoped payment credential，传给获资格的 payment handler；商户保留商业逻辑。
5. 写入 durable intent，调用 provider 并保存 correlation/idempotency key；不让模型决定是否重试扣款。
6. 验证 provider webhook，按 event ID 去重和状态机处理；对 pending/unknown 查询 provider。
7. 确认订单、资源 entitlement 或履约；失败通过对账和补偿恢复，不把跨系统操作称为 ACID 事务。

## 状态与恢复

生产状态可分为 `quoted → approval_required → approved → payment_pending → authorized → order_confirmed → fulfilled`；分支含 `expired`、`revoked`、`authentication_required`、`payment_failed`、`unknown_requires_reconciliation`、`refund_pending`。这些是建议的内部状态，不是声称符合任何厂商枚举。

支付超时不能直接进入 `payment_failed`：请求可能已被 provider 接受。必须利用 provider 支持的 idempotency key、查询和 webhook 追踪；同一 key 的 payload 改变必须拒绝。记录订单与 outbox 本地原子提交，但外部扣款不能靠 SQLite rollback 撤销。

本实验仅把 grant 消费、模拟订单和 audit event 放在同一 SQLite transaction；重复相同请求返回原 receipt，即使 quote 已过期也不会重新执行。新 key 使用已消费 grant 会拒绝。不同请求复用 key 会拒绝。

## 非功能目标：建议而非测得结果

| 维度 | POC 目标/机制 | 上生产前必须补齐 |
| --- | --- | --- |
| 可靠性 | 持久 idempotency、限次重试、unknown 状态与人工恢复 | provider 故障注入、数据库 HA、RTO/RPO 演练 |
| 安全 | scoped credential、商品与金额批准、密钥隔离、租户边界 | TAP/AP2 真签名、密钥轮转、SCA、PCI scope 和法律责任评估 |
| 性能 | 发现可缓存，支付与报价时效不可盲缓存；预算独立于 token 预算 | 端到端 p95、provider timeout、并发预算扣减测试 |
| 成本 | 默认离线；限制 LLM/tool calls、支付重试和 API spending | 支付费用、拒付成本、机器付费 minimum 与聚合策略 |
| 运维 | 可观察的拒绝、审计事件、版本锁定、CI、公开来源监测 | 脱敏 trace、报警、on-call、退款/争议 runbook |

## 实现范围

`Quote` 是可信边界收到的商户报价，实验不实现网络验证，**不能将模型自由生成的 Quote 直接用于真实支付**。`Delegation` 也是本地受信配置，不是用户签名证据。真实系统需要身份服务验证授权主体、可信商户报价、持续预算账本、异步支付恢复及 event outbox dispatcher。

当前实验采用 USD/EUR 和正整数 minor units，不支持跨币种自动换汇、订阅、累计多订单预算或履约。它只能用于说明不变式。完整能力状态见 [场景矩阵](scenarios.md)。
