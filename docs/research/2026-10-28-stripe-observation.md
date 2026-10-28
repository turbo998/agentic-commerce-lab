# Stage 1653：五种 PaymentIntent 中间态都不能关闭未知支付结果

[English](2026-10-28-stripe-observation.en.md) | [当日日报](../../research/daily/2026-10-28.md) |
[Stage 1652](2026-10-28-authority-recovery.md)

**核验日期：2026-10-28，北京时间 23:40 起；基线 `83d4e5e`。**
本阶段为 `synthetic` 离线策略研究与测试，不是新产品发布、Stripe SDK、
真实支付集成、模型 benchmark 或供应商合规认证。用户的 README 与 assets
保持不变。

## 1. 一手证据：失败的尝试不等于不可重试的 PaymentIntent

[Stripe 生命周期](https://docs.stripe.com/payments/paymentintents/lifecycle)说明：
一次付款失败可回到 `requires_payment_method`，供该 Intent 后续重试；
`requires_capture` 表示仍待捕获，`processing` 可持续多天。
因此通用 `failed=true`、工具返回成功或 HTTP 200 都不足以关闭未知结果。

| Stripe `status` | 本资产映射 | 不允许的推导 |
|---|---|---|
| `requires_payment_method` | `pending → unknown` | 把一次 decline 当作整个 Intent 的终态失败并重新获得付款权 |
| `requires_confirmation` | `pending → unknown` | 把待确认当成已付款 |
| `requires_action` | `pending → unknown` | 跳过消费者所需操作 |
| `processing` | `pending → unknown` | 把异步处理中当成成功 |
| `requires_capture` | `pending → unknown` | 把资金 hold 或 `amount_capturable` 当成已收款 |
| `succeeded` | 仅当 `amount_received` 等于批准金额，记 `succeeded` | 忽略部分收款，或由付款完成推出银行到账/履约完成 |
| `canceled` | 仅当 `amount_received=0`，记本地 `failed` | 把取消理解为新的批准，或证明所有外部资金后果已清除 |

最后两行是**本资产的严格金额策略**，不是完整 Stripe 状态定义。
真实部分捕获、超额捕获、多次捕获与退款需独立业务状态，不能用本表替代。
任何状态都不授予新的 dispatch 决策；Stage 1652 的单次批准约束不变。

[PaymentIntent 对象](https://docs.stripe.com/api/payment_intents/object)区分
`amount`、`amount_received`、`currency`、`livemode`、`id`、`object` 与 `status`。
[Connect 请求上下文](https://docs.stripe.com/api/connected-accounts)规定
`Stripe-Account` 按请求指定；对象内的任意 `metadata.account` 不是该上下文的证明。
这些资料本轮重新读取，不将观测日期当作发布时间；没有新做 Visa/Sierra
发布核验，跨厂商权限结论延续 Stage 1652 的已列明证据与限制。

## 2. 对账前先证明“这是同一笔、同一账号和模式、同一金额”

新增 [`lab/stripe_observation.py`](../../lab/stripe_observation.py)，仅通过已有
`PaymentAttemptJournal.read/reconcile` 工作，不修改 journal schema 或批准接口：

- 必须已有可信建立并持久化的 `pi_` reference；不能从收到的 JSON 自行认领。
- 可信调用方提供实际 retrieve 所用账号，与 `provider_account` 精确匹配；
  `stripe:test` / `stripe:live` 是**本地 namespace 约定**，把模式纳入已有不可变指纹。
- `object=payment_intent`、ID、币种、整数金额与布尔 `livemode` 必须匹配。
  `true` 不能作为金额 `1`，浮点金额不能伪装成整数金额。
- 明确要求 `transfer_data=null` 与 `on_behalf_of=null`，只支持本阶段的
  direct-account 范围；destination/on-behalf-of 路由不静默降级。
- 状态未知、字段遗漏、引用冲突或金额不符均显式报错，原 journal 结果不变。
  已确认终态仍受 journal 的单调性约束，旧 `processing` 不能覆盖成功。
- 不返回或持久化原始 payload、`client_secret`、描述文本或 metadata。

**可信输入不是自动验真。** 调用方仍须验证 API 响应来源、账号凭据、版本、
新鲜度、merchant/account 映射与初始关联。这个函数不联网、不验 webhook
签名，不验证真实 Stripe ID 存在，也不从 JSON 的结构合法性推出真实已付款。

## 3. 可运行的合成例子

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from lab.checkout import Checkout
from lab.payment_attempts import PaymentAttemptJournal, PaymentOperation
from lab.stripe_observation import reconcile_stripe_intent

with TemporaryDirectory() as directory:
    journal = PaymentAttemptJournal(Path(directory) / "attempts.sqlite3")
    op = PaymentOperation("tenant", "op", "approval", "stripe:test",
                          "acct_synthetic", "key", Checkout("shop", "USD", "sku", 1, 1000))
    journal.reserve(op)
    # Trusted synthetic association, not inferred from an incoming event.
    journal.reconcile(op, observation="pending", provider_reference="pi_synthetic")
    payload = {"object": "payment_intent", "id": "pi_synthetic", "livemode": False,
               "amount": 1000, "amount_received": 0, "currency": "usd",
               "status": "requires_capture", "transfer_data": None, "on_behalf_of": None}
    result = reconcile_stripe_intent(journal, op, retrieved_account="acct_synthetic",
                                    intent=payload)
    assert result.outcome == "unknown"
    assert not journal.reserve(op).dispatch_allowed
```

```powershell
python -m unittest tests.test_stripe_observation tests.test_payment_attempts tests.test_checkout -q
```

测试覆盖状态映射、缺失字段、金额/币种/ID/账号/模式替换、持久化终态、
路由排除与敏感字段不落盘。没有模型调用、真实付款、延迟坐标或生产就绪分数。

## 4. 架构结论与后续边界

Well-Architected 的可靠性原则在这里具体化为**provider 语义适配层**：
可信传输结果、对象归属绑定与业务终态是独立门槛，不能让模型从自然语言
摘要选择财务状态。普通模块化单体也能实现这些边界，不需要增加付款 Agent。
后续的未知 ID 可信恢复、签名事件入站、Connect 路由、部分捕获与清算状态
需要各自的一手契约与验收，本阶段不假装已经覆盖。
