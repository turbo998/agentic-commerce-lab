# Stage 1740：Stripe Webhook 收件箱单快照事件溯源（`InboxEventProvenance` 与 `StripeEventInbox.find_provenance` / `read_provenance`）

> English version: [2026-11-01-stripe-inbox-event-provenance.en.md](2026-11-01-stripe-inbox-event-provenance.en.md)

## 执行摘要

在 Agentic Commerce 的 Stripe 异步 Webhook 接收与回读认领（`StripeEventInbox`）流水线中，运营排查与后台重平衡经常需要单独针对某个作用域事件 `(scope, event_id)`（在尚未绑定 `PaymentOperation` 或独立于 `PaymentAttemptJournal` 的边缘摄取层）审计其收据与认领生命周期状态：

1. **分步读取导致的撕裂视图与歧义 `None`**：此前若只调用 `inbox.read_claim(scope, event_id)`，返回 `None` 既可能表示该 `event_id` 从未到达（`unreceived`），也可能表示已验签入库但尚待 Worker 认领（`unclaimed`）；若先后在 $T_1$ 调用 `read_receipt(scope, event_id)`、在 $T_2$ 调用 `read_claim(scope, event_id)`，并发 Worker 在 $[T_1, T_2]$ 窗口内执行 `claim_next()`、`handoff()` 或 `finish_readback()` 会产生撕裂快照（Torn Read），且孤儿认领行（`PRAGMA foreign_keys = OFF` 下删除了 `stripe_event_inbox` 父行）在两步读取中表现不一致。
2. **写路径 `_current_claim()` 世代整数类型门禁**：`_current_claim()` 在 `handoff()` 与 `finish_readback()` 前比对 `row["generation"] != claim.generation`，显式补齐 `type(row["generation"]) is not int` 与 `isinstance(row["state"], str)` 校验可防止非 `int` 类型在比较或状态检查时绕过门禁。

Stage 1740 在 `lab/stripe_inbox.py` 中新增不可变快照模型 `InboxEventProvenance`、`InboxEventPhase`（`"unclaimed" | "active" | "handled"`）以及单语句只读查询方法 `StripeEventInbox.find_provenance()` 与 `StripeEventInbox.read_provenance()`，通过单条 `FROM (SELECT 1) LEFT JOIN stripe_event_inbox ... LEFT JOIN stripe_readback_claims ...` 查询消除撕裂读取并显式拦截孤儿认领行。

---

## 架构对比：经典 Web App 两步收件箱读取 vs. AI-Native 单快照事件溯源

| 维度 | 经典 Web App 两步收件箱读取 (`read_receipt` + `read_claim`) | Agentic Commerce 单快照事件溯源 (`InboxEventProvenance`) |
|---|---|---|
| `unreceived` 与 `unclaimed` 区分 | `read_claim()` 对二者均返回 `None`，必须追加第二次查询 | 单次查询同时投影 `i_event_id` 与 `c_event_id`，精确区分未收到（`None`）与待认领（`phase == "unclaimed"`） |
| 并发 Worker 认领/移交一致性 | $T_1$ 与 $T_2$ 两次连接可能观察到不同时刻的收据与认领状态 | 单条 `SELECT ... FROM (SELECT 1) LEFT JOIN ...` 在同一 SQLite 读快照内原子返回 |
| 孤儿认领行（Orphan Claim）检测 | `read_receipt()` 返回 `None` 而 `read_claim()` 在构造 `InboxReceipt(None, ...)` 时报通用字段错误 | 显式识别 `i_event_id IS NULL AND c_event_id IS NOT NULL` 并抛出 `"Orphan readback claim exists without an inbox receipt."` |
| 跨对象绑定不变量 | 调用方自行拼装 `(scope, receipt, claim_status)` | `InboxEventProvenance.__post_init__` 强制校验 `claim_status.claim.scope == scope` 且 `claim_status.claim.receipt == receipt` |

---

## 核心不变量与状态矩阵

| `stripe_event_inbox` (`i`) | `stripe_readback_claims` (`c`) | `find_provenance()` 返回 | `read_provenance()` 行为 | `provenance.phase` |
|---|---|---|---|---|
| 不存在 (`NULL`) | 不存在 (`NULL`) | `None` | 抛出 `StripeInboxError("No inbox receipt exists...")` | — |
| 不存在 (`NULL`) | 存在 (`NOT NULL`) | 抛出 `StripeInboxError("Orphan readback claim...")` | 抛出 `StripeInboxError("Orphan readback claim...")` | — |
| 存在 (`NOT NULL`) | 不存在 (`NULL`) | `InboxEventProvenance(scope, receipt, None)` | 同左 | `"unclaimed"` |
| 存在 (`NOT NULL`) | 存在 (`state='active'`) | `InboxEventProvenance(scope, receipt, status)` | 同左 | `"active"` |
| 存在 (`NOT NULL`) | 存在 (`state='handled'`) | `InboxEventProvenance(scope, receipt, status)` | 同左 | `"handled"` |

---

## 验证结果

- `python -m pytest tests/test_stripe_claim_read.py tests/test_stripe_inbox.py tests/test_stripe_readback.py -q`：`57 passed, 91 subtests passed`。
