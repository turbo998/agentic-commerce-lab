# Stage 1670：五维 receipt 查询不受 1,000 条枚举上限约束

[English](2026-10-29-stripe-receipt-read.en.md) |
[资产](../../lab/stripe_inbox.py) |
[测试](../../tests/test_stripe_receipt_read.py) |
[前序送达时间边界](2026-10-29-stripe-receipt-clock.md)

## 研究结论与来源

`pending(limit=1000)` 是有界枚举，不是对特定 Event 的存在性查询。
新增 `read_receipt(scope, event_id)`，直接以 tenant、endpoint、provider account、
live/test mode 和 Event ID 五维主键查原始 receipt。测试构造 1,001 条本地记录，
确认第一页未列出的第 1,001 条仍可被直接查询；该 fixture 不是 1,001 次真实送达。

2026-10-29 05:18 BJT 重查 [Stripe 验证来源指导](https://docs.stripe.com/webhooks#verify-events-are-sent-from-stripe)
与 [异步处理指导](https://docs.stripe.com/webhooks#handle-events-asynchronously)：
官方要求采取动作前验证来源，并建议用异步队列解耦处理。
这些要求不等于官方提供或强制本地 SQLite reader。本轮为本地工程设计，
不声称新产品发布；未重新核验 Visa/Sierra。

## 历史读取不是本次接收准入

| 路径 | 事实与边界 |
|---|---|
| `record_with_clock` | 验证本次 raw bytes/HMAC/时间/JSON，在锁后重查时间，再接收/查重。 |
| `read_receipt` | 严格检查可信 scope 与 Event ID，再单次 SELECT 原始历史；不验本次请求。 |
| `pending` | 仍按 receipt 顺序有界枚举，与 claim 状态无关。 |
| `claim_next` / `finish_readback` | 既有本地工作协调，不是支付结果；历史读取不会重新开启 handled 工作。 |

找到记录仅返回原始 frozen `InboxReceipt`，包括首次 payload hash 和
`requires_readback=True`。同一 Event 重序列化后，仍读首次 hash；不同 Event ID 即使
指向同一 PaymentIntent，也不合并。缺失返回 `None`，不是支付失败或未付款结论。
非法 scope/ID 明确报错，数据库异常不伪装成 `None`。

没有 writer transaction、时钟、HMAC、JSON、schema 新增或 claim/payment 写入。
这里“只读”描述方法行为，不是建立 OS/数据库只读权限。数据库和调用方 scope
仍属可信本地边界，不增加存储防篡改、独立密码学证据或 HTTP 身份认证。
历史记录既不证明签名仍新鲜，也不授予 ACK、worker 或支付权限。
HTTP adapter 不能先按未认证 Event ID 查历史，再用“已经存在”跳过送达验签，
更不能将 reader 当作 `record_with_clock` 失败后的降级路径。

## 可执行 synthetic 示例

仅本地临时 SQLite 与合成 secret，不连接 Stripe 或创建支付。

```python
import hashlib
import hmac
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from lab.stripe_inbox import StripeEventInbox, StripeInboxScope

now = 1700000000
secret = "synthetic-only-receipt-reader"
body = json.dumps({
    "id": "evt_read", "object": "event", "livemode": False,
    "type": "payment_intent.succeeded",
    "data": {"object": {
        "id": "pi_read", "object": "payment_intent", "livemode": False,
    }},
}).encode()
digest = hmac.new(secret.encode(), str(now).encode() + b"." + body, hashlib.sha256).hexdigest()
signature = f"t={now},v1={digest}"
times = iter((now, now + 1))

with TemporaryDirectory() as directory:
    inbox = StripeEventInbox(Path(directory) / "inbox.sqlite3")
    scope = StripeInboxScope("tenant", "endpoint", "acct_synthetic", False)
    assert inbox.read_receipt(scope, "evt_read") is None
    receipt = inbox.record_with_clock(
        scope, body, signature, secret, clock=lambda: next(times),
    ).receipt
    claim = inbox.claim_next(scope, "synthetic-worker")
    inbox.finish_readback(claim)
    assert StripeEventInbox(inbox.path).read_receipt(scope, "evt_read") == receipt
    assert inbox.claim_next(scope, "another-worker") is None
    other = StripeInboxScope("another-tenant", "endpoint", "acct_synthetic", False)
    assert inbox.read_receipt(other, "evt_read") is None
    assert receipt.requires_readback
    print("Original scoped history survives handled work without reopening or payment authority.")
```

## AI Native 架构含义与验证

云 Well-Architected 与三层 Web 的可观测性原则仍适用，但 Agent 执行系统需要
进一步区分历史事实、当前准入和可执行权限。可查询性不能隐式延长 authority，
枚举缺失不能变成不存在证明，handled 也不能变成支付成功。这是执行事实模型的
细化，不是用新架构名词替代可靠性、身份认证或 provider reconciliation。

新增 15 项方法：五维隔离、缺失/重启、首次 hash、同对象不同 Event、active/handled
保持、严格 ID、数据库错误、SQL trace 单次 SELECT、超页查询及陈旧送达仍被拒绝。
199 项 Stripe 针对性与 4,204 项全量测试、编译、两个 demo、157 个本地链接及
两个一致的可执行双语示例通过。初次测试发现 fixture 未关闭 SQLite connection，
改用显式 closing 后重跑通过；八份有内容变化的生成 report 已恢复，另两份仅刷新
规范化文件状态，未提交 report。最终 SHA CI/canonical 同步为发布后门禁。
无生产密钥、网络支付或模型 benchmark。
