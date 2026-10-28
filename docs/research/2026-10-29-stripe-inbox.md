# Stage 1655：一条持久接收记录，不等于一次支付副作用

[English](2026-10-29-stripe-inbox.en.md) | [当日研究](../../research/daily/2026-10-29.md) |
[Stage 1654 验签](2026-10-29-stripe-delivery.md)

**核验日期：2026-10-29，北京时间 00:27 起；基线 `0ad9a5d`。**
这是 `synthetic` 离线工程资产，不是模型 benchmark、Stripe SDK、生产队列或真实支付接入。
本轮只新增 Stripe/SQLite 一手证据；不声称 Visa 或 Sierra 有新的产品发布。

**历史范围说明：** 下文“没有 claim/完成 API”描述 Stage 1655 时点。
[Stage 1656](2026-10-29-stripe-readback.md) 后续新增 opt-in 本地工作交接方法，
保留原 `pending()` 与接收去重行为；不把工作完成标记变成支付事实。

后续 [Stage 1669](2026-10-29-stripe-receipt-clock.md) 新增可选 `record_with_clock`，
在入口与取得 writer lock 后分别采样；原 `record(now=...)` 接口及此处 ingress-only
时间语义保留，不给已持久化 task 新增送达过期规则。

## 1. 重复事件、重复送达与业务动作有三个不同的身份

[Stripe Webhooks](https://docs.stripe.com/webhooks#event-delivery-behaviours)
说明 live 模式自动重试可持续三天，手工重发并不取消自动重试，送达顺序也没有保证。
不能用 `created` 判断已处理或推导可靠顺序；同一秒可能产生不同事件。
[重复处理建议](https://docs.stripe.com/webhooks#handle-duplicate-events) 区分同一 Event 重复送达，
以及指向同一 `data.object` / `event.type` 的不同 Event。

| 身份 | 本地用途 | 不应替代的身份 |
|---|---|---|
| 单次送达的签名与时间戳 | 原始字节消息认证与时间窗口检查 | Event ID、支付操作或消费者授权 |
| 可信配置 scope + Event ID | 一个端点语境中的持久接收去重 | 全局已处理、跨端点或跨 Event 的经济副作用去重 |
| 支付操作/授权与既有 provider 关联 | 独立账本与权威回读的业务边界 | 从事件 JSON 临时声明的支付归属 |

[Event 对象](https://docs.stripe.com/api/events/object) 包含 `id`、`object=event`、
`type`、`livemode`、`data.object`，并可能带有 Connect `account` 或组织 `context`。
它们不是可忽略的租户路由细节。文档目前建议多数新接入优先采用 thin events；
本参考故意只实现一个小的 snapshot 切片，不把它当作生产接入推荐或完整 SDK 兼容实现。
核验日期不是发布日期。

## 2. 新资产只持久保存回读提示

[`lab/stripe_inbox.py`](../../lab/stripe_inbox.py) 复用上一阶段验签，再解析原始 UTF-8 JSON。
重复 JSON key、非法 JSON、错误 mode、未支持的事件或路由都明确报错，不返回成功形状的默认值。
只支持 `payment_intent.succeeded` 与 `payment_intent.payment_failed`，
且嵌套对象必须为同 mode 的 `payment_intent` / `pi_` 引用。这是路由字段检查，
不是完整 Event/PaymentIntent schema 验证，更不是支付终态判断。

可信 `StripeInboxScope` 由配置提供 tenant、稳定 endpoint、provider account 与 mode；
**不能由请求、metadata 或模型选择 scope/secret。** 本实现不验证这份配置的真实性，
并拒绝所有非 null 的 `account`/`context`，不静默降级 Connect/组织事件。

SQLite 复合主键是 scope 加 Event ID；`BEGIN IMMEDIATE` 将检查与插入放在同一事务，
返回前提交。记录只有最小路由信息与首次 body SHA-256，不保留完整事件、secret、
`client_secret` 或 metadata。采用 `synchronous=FULL`，但
[SQLite 原子提交](https://www.sqlite.org/atomiccommit.html) 仍依赖文件系统/设备的 flush
等假设；重启与注入故障测试不是断电认证，也不是分布式事务。

同一 Event ID 的 type/对象引用不能改变。原始字节不同时，结果显式给出
`body_matches_first=False`，保留首次摘要，且不插入第二行；这只是差异证据，
**不证明两份 payload 的全部业务语义相等，也不声称 Stripe 一定会改变重投字节**。
签名、时间戳或 secret 轮换不是新 Event；重复送达仍必须重新验签。
所有行都保持 `requires_readback=True`。
尤其 `payment_intent.payment_failed` 不把整个 Intent 判为终态失败；仍需经过
[Stage 1653 的可信回读与绑定检查](2026-10-28-stripe-observation.md)。

`pending(scope, limit=100)` 只列出本地接收顺序的提示，limit 为 1–1000；
没有 worker claim、processed 标记、完成或删除 API。重复调用可返回相同行，
它不是“取出即拥有”的任务队列，也不保证无人重复处理。

## 3. 可运行的合成接收示例

```python
import hashlib
import hmac
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from lab.stripe_inbox import StripeEventInbox, StripeInboxScope

secret = "synthetic-only-inbox-secret"
body = json.dumps({
    "id": "evt_synthetic", "object": "event", "livemode": False,
    "type": "payment_intent.succeeded",
    "data": {"object": {"id": "pi_synthetic", "object": "payment_intent", "livemode": False}},
}).encode()
digest = hmac.new(secret.encode(), b"1700000000." + body, hashlib.sha256).hexdigest()
header = f"t=1700000000,v1={digest}"
scope = StripeInboxScope("tenant", "endpoint", "acct_synthetic", False)
with TemporaryDirectory() as directory:
    inbox = StripeEventInbox(Path(directory) / "inbox.sqlite3")
    first = inbox.record(scope, body, header, secret, now=1700000000)
    repeat = inbox.record(scope, body, header, secret, now=1700000000)
    assert first.first_seen and not repeat.first_seen
    assert len(inbox.pending(scope)) == 1
    assert repeat.receipt.requires_readback
```

secret 与时钟均为合成测试输入；生产不能照搬固定时钟或由请求挑选 secret。
83 项针对性测试通过，新增 21 项方法，覆盖真实新进程读取、并发、重签名、scope 隔离、
路由/身份冲突、commit 故障回滚、敏感字段排除，以及不改变支付 `unknown` 的集成断言。
全库 3,808 项单元测试、编译及两个既有离线演示也通过。

```powershell
python -m unittest tests.test_stripe_inbox tests.test_stripe_delivery tests.test_stripe_observation tests.test_payment_attempts tests.test_checkout -q
```

## 4. 架构结论与未实现边界

持久接收与尽快 ACK 可以分离复杂业务处理，但本资产没有 HTTP endpoint 或 ACK。
接收记录也不代表工作已完成；真实部署仍需 worker 所有权、重试/完成状态、保留策略、
可信初始支付关联与 provider 回读，以及独立的业务副作用幂等。
不同 endpoint/tenant scope 下会有各自记录，不能据此宣称跨端点 exactly-once。
原始 payload 摘要与对象 ID 也不是默认可公开的日志数据。

Inbox、幂等账本与事件乱序并非 AI 独有问题，成熟支付/事件驱动系统早已需要它们。
AI-native 的额外约束是：可变 planner 可以提出动作，但不能因重规划或重复通知
重建消费者授权、关联陌生对象或补齐未知结果。Well-Architected 的可靠性原则在这里
具体化为确定性证据 gate；不需要把模块化单体改造成更多 agent 或三层之外的口号。
