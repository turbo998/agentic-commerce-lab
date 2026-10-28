# Stage 1663：首次保存 PaymentIntent 关联前，先校验完整回读

[English](2026-10-29-stripe-association.en.md) |
[当日日报](../../research/daily/2026-10-29.md) |
[上一阶段](2026-10-29-admission-provenance.md)

**结论：**先保存初始 PaymentIntent ID、再检查回读，可能让错误 account/mode/报价
污染恢复历史。应依据**独立可信的 operation-to-reference 关联**验证后才首次写入；
金额相同或 metadata 看起来合理，都不能建立这层关联。
**关联不是新 dispatch、消费者同意或终态付款结果。**

2026-10-29 北京时间 03:35 从 `df5f6b5` 恢复，03:35–03:37 核验来源。
两位总控的同阶段指令合并为当前单一工作树任务，canonical 同步仍交总控 269。
仅在 23:00–06:00 工作，05:30 起不再开新阶段；README/SVG 不变。
`provenance=synthetic`、`independently_reproduced=false`：离线工程 fixture，
不是模型 benchmark、真实支付或 Stripe SDK/互操作认证。

## 1. Provider ID 需要可信来源，不是合理叙事

| 本轮重新核验的官方来源 | 架构含义 |
|---|---|
| [PaymentIntent retrieve](https://docs.stripe.com/api/payment_intents/retrieve) | 按 ID 回读；publishable key/client_secret 路径只返回部分字段，严格策略不能把缺失当安全默认值 |
| [Payment Intents 概览](https://docs.stripe.com/payments/payment-intents) | 将 ID 保存在 cart/session，恢复时复用 intent，并使用创建幂等；金额不唯一标识 operation |
| [Metadata](https://docs.stripe.com/metadata) | metadata 可修改；除文档说明的 Radar 使用外，通常不用于授权/拒绝 charge，不能认证本地 operation 关联 |

Stripe 当前建议多数新集成使用 Checkout Sessions。本轮只加固已有离线 PaymentIntent
恢复实验，不建议新建 PaymentIntent 集成，也不创建 sandbox。无需 API key、
真实请求或 client secret。本轮未核验新的 Visa/Sierra 协议发布；
TAP 身份、Poppy 访问、本地 approval/provenance 与 provider 对象关联各有独立边界。

## 2. 小型可选门禁，复用校验与事务 participant

[`associate_stripe_intent`](../../lab/stripe_observation.py) 接收：

- 既有 journal 与不可变可信 `PaymentOperation`。
- 来自已认证 provider context 的 `retrieved_account`。
- 独立可信 `expected_reference`，由 adapter 的已认证 create/result 路径或
  持久化 operation 映射建立关联。
- 完整可信 PaymentIntent 回读，不是 Event 或模型编写的 JSON。

函数**不能认证这些输入，也不能发现正确映射**。不能由 Event、自由文本、匹配金额或
请求可控 metadata 推导 `expected_reference`。`pi_[A-Za-z0-9_]+` 是本地窄语法策略，
不是 provider 身份认证。

在同一 `BEGIN IMMEDIATE` 事务内：

1. 查找精确且已 reserved 的 operation，不创建 reservation 或权限。
2. 用临时 `PaymentAttempt("unknown", expected_reference)` 复用
   `validate_stripe_intent`，而不是先把 ID 写入数据库。
3. 核对 account/provider test-live、ID/object、精确总额/currency、严格
   amount_received、status 及显式 direct-account routing。
4. 已持久化不同 reference 则拒绝；相同 reference 重试保留当前状态，不降级终态。
5. 仅对尚无关联的 `unknown` attempt 调用既有事务 participant，
   使用 `observation="pending"`；commit 后才返回。

即使 snapshot 是有效 `succeeded` 或零收款 `canceled`，本入口也只建立关联，
首次结果保持 `unknown`。结果接纳仍由独立显式
[`reconcile_stripe_intent`](../../lab/stripe_observation.py) 或带 fencing 的
[`accept_stripe_readback`](../../lab/stripe_readback.py) 完成。
有意不使用 validator 返回的 outcome：本 API 合同是关联，不是 reconciliation；
相同 ID 重试也不会接纳新 snapshot 的结果。

Operation fingerprint 改变或出现“终态却无 reference”时拒绝。
复用 provider/account/reference 唯一约束，防止关联到另一 operation；
不同 account 与 test/live 是独立 namespace。写入/提交错误直接抛出，没有成功形状回退。
不改 schema、generic journal 或既有 reconciliation 合同。
旧 `journal.reconcile(..., observation="pending")` 仍是兼容旁路，不自动升级为语义校验。

## 3. 可运行 synthetic 示例：拒绝、关联、独立 reconciliation

Expected reference 是显式可信 fixture，**不是从 intent 推导**。
本例不实现 provider 回读、认证或 freshness。

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from lab.checkout import Checkout
from lab.payment_attempts import PaymentAttemptJournal, PaymentOperation
from lab.stripe_observation import (
    StripeObservationError, associate_stripe_intent, reconcile_stripe_intent,
)

operation = PaymentOperation(
    "tenant", "operation", "approval", "stripe:test", "acct_synthetic", "key",
    Checkout("synthetic-shop", "USD", "synthetic-sku", 2, 1000),
)
trusted_reference = "pi_synthetic"
intent = {
    "object": "payment_intent", "id": "pi_synthetic", "livemode": False,
    "amount": 1000, "amount_received": 1000, "currency": "usd",
    "status": "succeeded", "transfer_data": None, "on_behalf_of": None,
}
with TemporaryDirectory() as directory:
    journal = PaymentAttemptJournal(Path(directory) / "commerce.sqlite3")
    journal.reserve(operation)
    context = dict(retrieved_account="acct_synthetic",
                   expected_reference=trusted_reference)
    try:
        associate_stripe_intent(journal, operation, intent={**intent, "amount": 999},
                               **context)
    except StripeObservationError:
        pass
    else:
        raise AssertionError("wrong quote must not establish first association")
    assert journal.read(operation).provider_reference is None
    bound = associate_stripe_intent(journal, operation, intent=intent, **context)
    assert bound.provider_reference == trusted_reference and bound.outcome == "unknown"
    assert not journal.reserve(operation).dispatch_allowed
    final = reconcile_stripe_intent(
        journal, operation, retrieved_account="acct_synthetic", intent=intent,
    )
    assert final.outcome == "succeeded"
    assert associate_stripe_intent(journal, operation, intent=intent, **context) == final
```

## 4. AI-native：可信关联不是“看起来像同一笔”

Well-Architected 是质量与权衡框架，不是 Web 三层拓扑。可信外部引用关联与事务校验
是成熟系统技术；AI-native 的额外风险是 planner 从 webhook、金额或解释性 metadata
选一个合理 PaymentIntent，再把它当权威恢复历史。应在首次写状态之前约束关联来源
和 provider 语义，而不是保存后再靠给 agent 的指令纠偏。

本门禁不能阻止可信 adapter 提供错误但看似合理的 expected reference。认证、持久化
create-result correlation、freshness、一致备份与调用者访问控制仍属部署责任。
恢复已 reserved attempt 不要求 active approval，也不制造 Stage 1662 准入历史。
不新增 approval、dispatch、Connect/organization、部分付款、退款或结算保证。

## 5. 验证范围

[`tests/test_stripe_association.py`](../../tests/test_stripe_association.py)
新增 29 项方法；与既有 observation/journal/atomic-readback/approval/provenance 合计
148 项针对性测试通过。覆盖首次写入前完整字段、显式 context/reference、总额而非
quantity × amount、mode/account 隔离、缺失 reservation、operation/reference
双向 scope 唯一约束、同/不同 reference 并发、真实新进程、终态保留、敏感字段排除，
以及真实 update 后与 commit 失败回滚；不嵌套 public reconciliation 连接。
全库 4,022 项单测、编译、两个既有演示、103 个本地链接及两个相同双语可执行示例通过。
八个历史生成报告文件已恢复，没有报告内容进入暂存；README/assets 相对 `1d9273d`
零差异。最终 SHA CI/canonical 同步保留为发布后门禁，不作为真实 provider effect 证据。
