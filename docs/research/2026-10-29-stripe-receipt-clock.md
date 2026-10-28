# Stage 1669：Stripe receipt 在入口与锁后分别检查同一送达时间戳

[English](2026-10-29-stripe-receipt-clock.en.md) |
[接收资产](../../lab/stripe_inbox.py) |
[共享时间策略](../../lab/stripe_delivery.py) |
[测试](../../tests/test_stripe_receipt_clock.py) |
[原始接收边界](2026-10-29-stripe-inbox.md)

## 结论与一手证据

通过入口验签的送达，在等待 SQLite writer 后可能已超出接收方时间策略。
新增可选 `record_with_clock(..., clock=...)`：入口先完整验签/解析，取得写锁后
再检查**同一个已验证的 delivery timestamp**，然后才查重/写入 receipt。
这是额外的本地 receipt-admission profile，**不是修复 Stripe 协议或旧入口 API**。

2026-10-29 05:03 BJT 重查 [Stripe 原始正文与验签指南](https://docs.stripe.com/webhooks#webhook-endpoint-def)、
[重放时间指导](https://docs.stripe.com/webhooks#preventing-replay-attacks)、
[异步处理](https://docs.stripe.com/webhooks#handle-events-asynchronously) 与
[重复事件](https://docs.stripe.com/webhooks#handle-duplicate-events)：

- delivery timestamp 在签名内容中，不能在不使签名失效的情况下修改。
  SDK 默认容忍五分钟，文档提醒 `0` 会关闭 recency；本地既有 profile 拒绝 `0`，
  并使用正整数、过去/未来对称的包含边界，不冒称完整 SDK 兼容。
- Stripe 每次重试重新生成签名与 timestamp；旧 Event 的新送达可以重新通过时间校验。
  **不要拿 JSON `event.created` 代替签名头时间戳。**
- 官方建议异步处理并快速响应 `2xx`；接收去重与不同 Event 的业务去重不相同。
  官方并未强制此处的数据库锁后校验，也未要求对已持久化 worker task 再套送达过期窗口。

仅核验 Stripe 现行文档，不声称本次访问日新产品发布；本轮未重新核验 Visa/Sierra。
保持既有两个 PaymentIntent snapshot 类型，不因文档同时介绍 thin events 而扩张支持范围。

## 小资产：两个时间边界，一次密码学/JSON 处理

新 API 成功或有效重复路径明确采样 **两次**，不是一次：

1. 可信 scope/callable 检查后取 ingress sample，用原 raw-byte HMAC、header、
   secret 配置、时间及严格 snapshot JSON 校验。失败不连接数据库。
2. `BEGIN IMMEDIATE` 真正取得 writer lock 后取第二个 fresh sample；
   复用原时间策略，要求 `abs(now - signed_timestamp) <= tolerance`。
   第二个值同样必须是非负 signed64 严格整数。
3. 第二次校验在既有 receipt 查重之前；过期 duplicate 不能借“已经接收过”绕过。
   通过后复用原 identity/conflict/hash/INSERT/commit 流程。

HMAC 和 JSON 不在 writer lock 下重跑；一轮验签仍可能尝试多个活动密钥。
严格 duplicate-key/NaN 解析原已存在，
本轮不是 JSON parser 修复。没有新 schema、receipt 字段、时间审计或 claim 重置。
`clock` 缺失、非 callable、抛错或返回坏值都不会降级成 fixed-now 接收。
可信 callback 必须在每次调用时返回 fresh 时间；不假设墙钟一定单调递增。

原 `record(..., now=...)` **保留入口 fixed-now 语义**，不新增锁后校验。
需要更强 receipt-admission 约束的 route 必须使用新 facade，不能在错误后 fallback。
这与 [timed signer 的单次锁后样本](2026-10-29-merchant-signature-time.md) 不同：
该处需要同一决策样本；这里刻意区分 arrival 与 durable-admission 两个边界。

| 场景 | 本地有界结果 |
|---|---|
| 入口有效，锁后差值恰为 `±300`（默认配置） | 包含边界，可按原流程接收/查重。 |
| 入口有效，锁后差值变为 `±301` | 在 receipt 查重/写入之前拒绝。 |
| 入口已过期、坏 HMAC/JSON/scope | 不进入 writer 事务；不会等锁后时间“变好”再接受。 |
| 重签同一 Event，新 timestamp/活动 secret | 仍是原 scoped Event identity；不重置 receipt/claim。 |
| 已持久化 task 后来超过送达窗口 | 本 API 不使任务过期，也不创造 worker/payment 权限。 |

## 可执行 synthetic 示例

只构造离线测试签名和逻辑时钟，不连接 Stripe、创建 endpoint 或发送支付。

```python
import hashlib
import hmac
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from lab.stripe_delivery import StripeDeliveryError
from lab.stripe_inbox import StripeEventInbox, StripeInboxScope

start = 1700000000
secret = "synthetic-only-receipt-secret"
body = json.dumps({
    "id": "evt_synthetic", "object": "event", "livemode": False,
    "type": "payment_intent.succeeded", "created": start,
    "data": {"object": {
        "id": "pi_synthetic", "object": "payment_intent", "livemode": False,
    }},
}).encode()
times = iter([start, start + 1, start + 299, start + 301, start + 400, start + 401])
samples = []

def clock():
    value = next(times)
    samples.append(value)
    return value

def signature(timestamp):
    digest = hmac.new(
        secret.encode(), str(timestamp).encode() + b"." + body, hashlib.sha256,
    ).hexdigest()
    return f"t={timestamp},v1={digest}"

with TemporaryDirectory() as directory:
    inbox = StripeEventInbox(Path(directory) / "inbox.sqlite3")
    scope = StripeInboxScope("tenant", "endpoint", "acct_synthetic", False)
    first = inbox.record_with_clock(scope, body, signature(start), secret, clock=clock)
    assert first.first_seen and first.receipt.requires_readback
    try:
        inbox.record_with_clock(scope, body, signature(start), secret, clock=clock)
    except StripeDeliveryError as error:
        assert "tolerance" in str(error)
    else:
        raise AssertionError("Queued stale duplicate was admitted.")
    duplicate = inbox.record_with_clock(scope, body, signature(start + 400), secret, clock=clock)
    assert not duplicate.first_seen and duplicate.receipt == first.receipt
    assert inbox.pending(scope) == (first.receipt,)
    assert samples == [start, start + 1, start + 299, start + 301, start + 400, start + 401]
    print("Queued stale duplicate rejected; fresh retry keeps the original readback hint.")
```

## 架构含义与未覆盖缺口

三层 Web 分层和云 Well-Architected 的可靠性原则仍必要，但“入口认证通过”
与“持久准入时仍满足策略”不是同一事实。Agentic Commerce 的执行架构需要明确
策略线性化点及已有事实的生命周期，而不是把事件、receipt、worker handled 或
provider 状态统一视作已授权的经济结果。

这里的保证仅在第二次采样点成立，不保证物理 commit/send 时仍在窗口内。
重新取样不刷新入口使用的 trusted secret tuple，不检测排队期间的远端 secret 退役；
也不认证 worker、消费 nonce 或改变 Stripe readback/journal 的 unknown 状态。
`event.created` 仍不参与 freshness。caller 负责时钟同步、HTTP/queue/backpressure、
endpoint/account/mode secret 配置与 ACK/重试策略。更严格的接收窗口可能增加拒绝与
重试成本，不应拖延 webhook ACK 或错误地丢弃已接收任务。

## 验证

新增 **30** 项方法，**184** 项 Stripe 针对性测试通过。SQL trace 观察真实阻塞
`BEGIN IMMEDIATE`，逻辑时间跨越精确阈值而非实际睡眠五分钟；覆盖两次采样顺序、
一轮入口验签/JSON、duplicate/claim 保留、重签/rotation、旧路径、零 epoch/signed64 上限、
并发/重启、真实写入及 commit 失败回滚、unknown payment 不变。
全库 **4,189** 项测试、编译、两个离线 demo、167 个本地链接及两个一致的可执行
双语示例通过；测试生成的十份历史 report 已恢复。最终 SHA CI/canonical 同步
作为发布后门禁单独核验；这是 synthetic 工程测试，不是模型 benchmark。
