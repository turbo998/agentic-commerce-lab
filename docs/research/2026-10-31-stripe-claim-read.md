# Stage 1672：Stripe readback claim 作用域状态只读查询与状态边界

[English](2026-10-31-stripe-claim-read.en.md) |
[当日日报](../../research/daily/2026-10-31.md) |
[前序 claim 协调](2026-10-29-stripe-readback.md) |
[前序 receipt 历史查询](2026-10-29-stripe-receipt-read.md)

**结论：**新增 `StripeEventInbox.read_claim(scope, event_id)` 与冻结数据结构
`ReadbackClaimStatus(claim, state)`，按五维作用域
`(tenant_id, endpoint_id, provider_account, livemode, event_id)` 只读查询本地 claim 历史状态。
**返回 `active` 或 `handled` 仅表示本地协调元数据，不代表 worker 仍在线、已完成 provider 回读、
或支付状态已成功；返回 `None` 仅表示该 Event 在该作用域下当前没有 claim 记录。**

本阶段 `provenance=synthetic`、`independently_reproduced=false`：
离线 SQLite 工程资产，不是支付执行器、分布式租约系统或协议互操作认证。

## 1. 上游核验背景（2026-10-31 00:06 BJT）

- `python scripts/source_monitor.py` 生成
  [`research/daily/2026-10-31-sources.json`](../../research/daily/2026-10-31-sources.json)，
  `51/51` 项 `status="ok"`。
- 当日唯一 `change="changed"` 来源为 `stripe-spt`；连续两次抓取
  `shared-payment-tokens.md?agent-seller=seller` 的 unified diff 显示示例字段
  `expires_at` 秒级抖动（如 `1795968579 -> 1795968581`），属于动态示例值，不可直接等同新协议发布。
- `stripe-mcp` 解析事实维持不变：`deadline=2026-11-30`，
  `previous_deadline=2026-10-31`，`policy_change="unchanged"`。
- Poppy 上游 HEAD 更新到 `ec16efa4459aaf98b1b82a1a5973504f4fd75fd9`（`Draft 0.3` 文本修订），
  但 `versions.json` 仍仅 `0.2`/`0.1` 有 `published` 字段，`0.3` 仍为 in progress。

## 2. 新增只读 claim 状态契约

在 [`lab/stripe_inbox.py`](../../lab/stripe_inbox.py)：

1. 新增 `ClaimState = Literal["active", "handled"]` 与冻结结构
   `ReadbackClaimStatus(claim: ReadbackClaim, state: ClaimState)`。
2. 抽取 `_require_event_lookup(scope, event_id)` 复用连接前校验：
   - `scope` 必须是可信 `StripeInboxScope`；
   - `event_id` 必须匹配 `evt_[A-Za-z0-9_]+`；
   - 非法输入在连接前报错，避免“坏输入=不存在”的静默降级。
3. `read_claim(scope, event_id)` 执行单条只读 JOIN：
   - 从 `stripe_event_inbox` 与 `stripe_readback_claims` 按主键关联读取；
   - 若不存在 claim 行返回 `None`；
   - 若存在，返回 `ReadbackClaimStatus(ReadbackClaim(...), state)`；
   - 不创建 claim、不交接、不完成、不写入、不取 writer 锁。

## 3. 与既有路径的边界关系

| 方法 | 本阶段保证 | 不保证 |
|---|---|---|
| `read_claim` | 读取该 Event 在该作用域下的本地 claim 状态历史。 | worker liveness、provider readback 真伪、支付成功与否。 |
| `claim_next` | 首次本地领用并创建 generation=1 claim。 | 支付授权或远端 exactly-once。 |
| `handoff` | 可信控制器显式转移本地处理权并递增 generation。 | 旧 worker 已停止外部动作。 |
| `finish_readback` | 标记本地 claim 为 handled。 | readback 内容已通过业务语义验证。 |
| `accept_stripe_readback` | 在同库事务中更新账本并将 claim 标记 handled。 | provider 终局结算或履约完成。 |

## 4. 可运行 synthetic 示例

```python
import hashlib
import hmac
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from lab.stripe_inbox import StripeEventInbox, StripeInboxScope

now = 1700000000
secret = "synthetic-stage-1672-secret"
body = json.dumps({
    "id": "evt_claim_read", "object": "event", "livemode": False,
    "type": "payment_intent.succeeded",
    "data": {"object": {"id": "pi_claim_read", "object": "payment_intent", "livemode": False}},
}).encode()
sig = hmac.new(secret.encode(), str(now).encode() + b"." + body, hashlib.sha256).hexdigest()
scope = StripeInboxScope("tenant", "endpoint", "acct_synthetic", False)

with TemporaryDirectory() as directory:
    inbox = StripeEventInbox(Path(directory) / "inbox.sqlite3")
    inbox.record(scope, body, f"t={now},v1={sig}", secret, now=now)
    assert inbox.read_claim(scope, "evt_claim_read") is None
    claim = inbox.claim_next(scope, "worker-a")
    status = inbox.read_claim(scope, "evt_claim_read")
    assert status is not None and status.state == "active"
    current = inbox.handoff(status.claim, "worker-b")
    inbox.finish_readback(current)
    done = inbox.read_claim(scope, "evt_claim_read")
    assert done is not None and done.state == "handled"
```

## 5. 验证结果

- 新增 [`tests/test_stripe_claim_read.py`](../../tests/test_stripe_claim_read.py) **12 项测试**：
  覆盖未 claim 返回 `None`、active/handled 读取、重启与新进程持久化、五维作用域隔离、
  超过 `active_claims(limit=1000)` 的 claim 直接定位、失败提交回滚不污染状态、
  连接前输入校验、坏存储元数据拒绝、存储异常透传、SQL trace 只读 `SELECT`。
- 回归命令通过（`505/505`）：
  `python -m unittest tests.test_stripe_claim_read ... tests.test_poppy_replay_read -q`。

