# Stage 1656：旧 generation 不能完成本地提示，但旧 worker 仍可能运行

[English](2026-10-29-stripe-readback.en.md) | [当日研究](../../research/daily/2026-10-29.md) |
[接收侧身份](2026-10-29-stripe-inbox.md)

**核验日期：2026-10-29，北京时间 01:04 起；基线 `cac1ae6`。**
这是 `synthetic` 离线工程参考，不是模型 benchmark、分布式锁服务或真实支付 worker。
本轮没有新的 Visa/Sierra 产品发布核验。

## 1. 一手证据让本阶段选择“不造自动租约”

[Stripe Webhooks](https://docs.stripe.com/webhooks) 建议异步处理，且重复/乱序送达不能假设消失。
接收去重并未回答哪个 worker 拥有工作、崩溃后由谁恢复。
[AWS Builders' Library 的 leader election 文章](https://aws.amazon.com/builders-library/leader-election-in-distributed-systems/)
发表于 **2019-12-05**，不是新发布；它说明进程暂停、时钟与旧 leader 继续运行的风险，
强调持久化之后再报告完成、幂等以及优先使用经过验证的客户端。文中租约依赖本地
elapsed duration，而非集群共享 wall clock。

本阶段不把“传入 now 加一个超时时间”包装成可靠的分布式租约。
选择更小的边界：**可信控制器显式交接，SQLite 事务比较并递增 generation，
拒绝旧 handle 对本地完成标记的更新。** 没有时钟参数、自动到期、续租、心跳或自动恢复。
[SQLite isolation](https://sqlite.org/isolation.html) 支撑单文件独立连接的提交可见性与写串行化，
不保证外部系统或暂停 worker 的行为。

## 2. 新 generation 不是新支付尝试

[`lab/stripe_inbox.py`](../../lab/stripe_inbox.py) 在原接收表之外增加带父表外键的
`stripe_readback_claims` 表，保留原始 receipt schema、去重与 `pending()` 行为。
已有数据库重新打开时增量建表，不删除接收记录。

| 操作 | 本地状态 | 不能推导的含义 |
|---|---|---|
| `claim_next(scope, worker)` | 从未 claim 的提示变为 `active`，generation=1 | 新支付尝试或消费者授权 |
| `handoff(current, worker)` | 比较 scope/receipt/owner/generation，递增 generation | 自动证明旧 worker 超时或已经停止 |
| `finish_readback(current)` | 当前 handle 变为 `handled`；相同 handle 重复完成幂等 | 实际回读已认证、支付成功或履约完成 |
| 旧 handle 完成/交接 | 明确报错，不修改新 owner 的状态 | 已阻止旧 worker 的网络请求或其他数据库写入 |
| 已 handled 后重复送达 | 不重新创建工作 | 跨 Event 或跨端点的业务副作用已去重 |

同一 worker ID 接管也必须递增 generation，避免“名字又相同了”的 ABA 混淆。
无可用工作时 `claim_next` 返回 `None`，这是正常控制状态；无效输入、旧 handle、
generation 耗尽与存储失败不会返回成功。计数不回绕。
`active_claims(scope, limit=100)` 提供 1–1000 条本地恢复提示，不决定恢复政策。
`pending()` 仍列出所有接收记录，包括 handled；`receipt.requires_readback=True`
仍表示 receipt 不能证明业务事实，不是 worker 状态。

**这些 handle 是协调元数据，不是密码学 capability 或身份认证。**
接口只应供可信 worker/控制器调用，不是模型工具。它不防御恶意数据库写入者、
猜出当前元数据的未认证调用者或数据库备份回滚；generation 历史必须保留。

## 3. 可运行的显式交接与旧 handle 拒绝

```python
import hashlib
import hmac
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from lab.stripe_inbox import StripeEventInbox, StripeInboxError, StripeInboxScope

secret = "synthetic-only-readback-secret"
body = json.dumps({
    "id": "evt_synthetic", "object": "event", "livemode": False,
    "type": "payment_intent.succeeded",
    "data": {"object": {"id": "pi_synthetic", "object": "payment_intent", "livemode": False}},
}).encode()
digest = hmac.new(secret.encode(), b"1700000000." + body, hashlib.sha256).hexdigest()
scope = StripeInboxScope("tenant", "endpoint", "acct_synthetic", False)
with TemporaryDirectory() as directory:
    inbox = StripeEventInbox(Path(directory) / "inbox.sqlite3")
    inbox.record(scope, body, f"t=1700000000,v1={digest}", secret, now=1700000000)
    old = inbox.claim_next(scope, "worker-a")
    assert old is not None
    current = inbox.handoff(old, "worker-b")  # Trusted synthetic recovery decision.
    assert current.generation == old.generation + 1
    try:
        inbox.finish_readback(old)
    except StripeInboxError as error:
        assert "stale" in str(error)
    else:
        raise AssertionError("Old handle unexpectedly accepted")
    inbox.finish_readback(current)  # Synthetic local handling, no provider call.
    assert not inbox.active_claims(scope)
    assert inbox.pending(scope)[0].requires_readback
```

secret、事件及固定时钟均为合成数据，示例没有回读真实 Stripe 或改变支付状态。
104 项针对性测试通过，新增 21 项方法，覆盖并发 claim/交接、旧 handle/ABA、
scope/receipt 替换、真实新进程完成、旧文件升级、三类提交故障回滚及支付账本不变。
全库 3,829 项单测、编译、两个既有演示、46 个本地链接及四个新旧双语示例均通过。

```powershell
python -m unittest tests.test_stripe_readback tests.test_stripe_inbox tests.test_stripe_delivery tests.test_stripe_observation tests.test_payment_attempts tests.test_checkout -q
```

## 4. 必须保持的外部原子性边界

`finish_readback` 只记录可信调用者声称提示已处理，不验证其是否真的读过 provider。
不能先更新另一份业务数据库，再调用此方法，并假设 fencing 已保护前面的写入。
回读真实性、既有关联/账号/金额检查与业务结果接受仍需独立合同：
[Stage 1653](2026-10-28-stripe-observation.md) 的语义 gate 不会被此 handle 替代。
处理中仍为 `unknown` 的支付还需要后续事件或独立对账策略；handled 提示并不关闭它。
本阶段没有 HTTP ACK、网络 worker、调度、自动恢复或外部副作用 exactly-once。

传统可靠性设计早已处理旧 owner 和幂等，不能把它们说成 AI 独有创新。
AI-native 的额外约束是：重规划、恢复或新 generation 都不能重建支付操作 ID、
消费者授权或支付幂等键。变的是本地工作所有权，不是经济权限。
