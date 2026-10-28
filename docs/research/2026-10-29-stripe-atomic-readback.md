# Stage 1657：同一事务先约束支付写入，再完成本地回读提示

[English](2026-10-29-stripe-atomic-readback.en.md) | [当日研究](../../research/daily/2026-10-29.md) |
[上一阶段工作权边界](2026-10-29-stripe-readback.md)

**核验日期：2026-10-29，北京时间 01:36 起；基线 `e95d106`。**
这是 `synthetic` 离线工程参考，不是模型 benchmark 或生产支付集成。
本轮未重新核验 Visa/Sierra 产品发布。

## 1. 必须在业务写入之前核对工作权

Stage 1656 会拒绝旧 generation 完成本地提示，但不能撤销在检查之前已经发生的支付写入。
两次独立提交既留下旧 worker 写入缺口，也留下支付更新与提示标记之间的崩溃窗口。

[SQLite 事务文档](https://sqlite.org/lang_transaction.html) 说明同一时间只有一个 writer，
支持显式 `BEGIN IMMEDIATE`，不支持嵌套 `BEGIN`。
在 inbox 写事务内调用账本的公开 reconcile 方法会打开另一个连接，而非共享当前事务。
[Stripe 事件文档](https://docs.stripe.com/events/how-events-work) 明确指出 snapshot
在处理时可能已过时；验签后确认对象身份不等于接受最新回读，Event.type 也不是最终结果。
新集成推荐 thin events，本资产仍只是明确限缩的 snapshot 接收切片。

## 2. 显式选择同库协同入口，不冒充跨系统事务

[`accept_stripe_readback`](../../lab/stripe_readback.py) 要求 inbox 和 journal
解析为同一个 SQLite 文件路径；不同文件或不同硬链接名称均拒绝。
文件系统命名空间属于可信配置，不防恶意路径替换、数据库篡改或备份回滚。

同一连接中的一个 immediate 事务按顺序执行：

1. 检查持久化 scope/receipt/worker/generation，且必须仍为 `active`。
2. tenant、account 与 test/live namespace 必须匹配不可变支付操作。
3. 在当前连接读取已 reserve 的账本；必须已有可信 PaymentIntent 关联，并与 receipt
   对象一致，事件不能替调用者建立此关联。
4. 复用账户、object/ID、mode、amount、currency、直连路由与 status 回读检查，
   以及账本原有冲突拒绝和终态单调性规则。
5. 更新账本并标记提示完成，commit 成功之后才返回结果。

持有写锁期间没有网络操作。handoff 与 acceptance 串行化：交接先完成则旧 generation
不能更新支付状态；acceptance 先完成则该 handled claim 不得再被交接。
写入或 commit 故障会显式抛出，并回滚两处本地变更。
这是本地数据库边界，不是远端支付恰好一次、副作用 fencing、结算或断电安全保证。

中间状态回读可以将提示标为 `handled`，而支付仍为 `unknown`；
完成的是检查提示，不是确认支付终态，也不产生再次 dispatch 的权限。
历史失败事件可以对应当前 succeeded Intent；历史成功事件也不能覆盖当前 canceled 状态。

已 handled 的 acceptance **明确拒绝**，即使 handle 相同也不返回伪成功。
原 `finish_readback()` 保留幂等，只写提示标记，不证明支付协同更新曾发生。
如果 acceptance 响应丢失，应检查已持久化账本/claim，不宣称具有透明结果重放能力。

## 3. 可执行合成示例

在仓库根目录执行；不使用真实凭据，不请求 provider，也不调用模型：

```python
import hashlib
import hmac
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from lab.checkout import Checkout
from lab.payment_attempts import PaymentAttemptJournal, PaymentOperation
from lab.stripe_inbox import StripeEventInbox, StripeInboxScope
from lab.stripe_readback import accept_stripe_readback

with TemporaryDirectory() as directory:
    path = Path(directory) / "commerce.sqlite3"
    inbox, journal = StripeEventInbox(path), PaymentAttemptJournal(path)
    scope = StripeInboxScope("tenant", "endpoint", "acct_synthetic", False)
    operation = PaymentOperation(
        "tenant", "operation", "approval", "stripe:test", "acct_synthetic", "key",
        Checkout("synthetic-shop", "USD", "synthetic-sku", 1, 1000),
    )
    journal.reserve(operation)
    journal.reconcile(operation, observation="pending", provider_reference="pi_synthetic")
    now, secret = 1700000000, "synthetic-only"
    body = json.dumps({
        "id": "evt_synthetic", "object": "event", "livemode": False,
        "type": "payment_intent.succeeded",
        "data": {"object": {
            "id": "pi_synthetic", "object": "payment_intent", "livemode": False,
        }},
    }).encode()
    signature = hmac.new(
        secret.encode(), str(now).encode() + b"." + body, hashlib.sha256,
    ).hexdigest()
    inbox.record(scope, body, f"t={now},v1={signature}", secret, now=now)
    claim = inbox.claim_next(scope, "worker-a")
    assert claim is not None
    result = accept_stripe_readback(
        inbox, journal, claim, operation, retrieved_account="acct_synthetic",
        intent={
            "object": "payment_intent", "id": "pi_synthetic", "livemode": False,
            "amount": 1000, "amount_received": 1000, "currency": "usd",
            "status": "succeeded", "transfer_data": None, "on_behalf_of": None,
        },
    )
    assert result.outcome == "succeeded" and inbox.active_claims(scope) == ()
    assert not journal.reserve(operation).dispatch_allowed
    print(result.outcome)
```

[`单测`](../../tests/test_stripe_atomic_readback.py) 在支付 SQL 已执行、提示尚未更新时注入故障，
以及在两处更新已完成、commit 尚未成功时注入故障，要求两边状态都保持原样。
另覆盖真实新进程可见性、并发交接/acceptance、并发 acceptance、旧 generation/ABA、
跨文件拒绝、绑定错误、中间结果和已 handled 的明确拒绝。

## 4. 架构反思：约束真正的状态写入，而非模型叙述

事务与 fencing 是成熟系统技术，不是 AI 发明；Well-Architected 质量指导也不等同于
Web 三层部署。AI-native 的改进是把确定性门禁放在经济状态写入路径：
重规划、模型叙述或送达元数据不能替代持久化操作、经过校验的 provider 观察和当前工作权。

这是**显式选择的入口**：原有独立账本/完成 API 仍可用。
所有协作回读 worker 必须经过本入口，才具有此处本地保证；直接数据库/账本写入可以绕过它。
claim 不是身份认证或消费者授权，新 generation 也不创造新的支付权限。
真实回读认证与新鲜度、初始对象关联、worker 授权、HTTP ACK/重试策略、周期回读、
Connect/组织/thin events、多数据库工作流及全部远端副作用，均不在此参考实现内。
