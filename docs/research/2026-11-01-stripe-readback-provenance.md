# Stage 1736：Stripe 回读对账跨表溯源单快照只读审计与共享数据库引用一致性校验

> **日期**：2026-11-01（北京时间 `UTC+08:00`）  
> **阶段**：Stage 1736  
> **核心模块**：`lab/stripe_readback.py`、`lab/stripe_inbox.py`、`lab/stripe_observation.py`、`tests/test_stripe_readback_provenance.py`  
> **English Version**: [`2026-11-01-stripe-readback-provenance.en.md`](2026-11-01-stripe-readback-provenance.en.md)

---

## 1. 背景与架构问题

在 `StripeEventInbox` 与 `PaymentAttemptJournal` 共享本地 SQLite 数据库的对账拓扑中，`accept_stripe_readback()` 在单个本地事务中同时更新 `payment_attempts` 与 `stripe_readback_claims`（并将 `state` 置为 `'handled'`）。为防止重复提交，`accept_stripe_readback()` 对任何 `state == 'handled'` 的认领显式拒绝（包括本地响应丢失后的重试）。

然而在 Stage 1736 之前，当恢复控制器、操作员或对账审计器需要在不发起远端请求、不加写锁的前提下核验某个 `(scope, event_id, operation)` 在共享数据库上的耦合状态时，存在三项结构性缺口：

1. **缺乏跨表耦合状态的单快照只读查询**：
   - 调用方若依次调用 `journal.read_attempt(operation)`、`inbox.read_receipt(scope, event_id)` 与 `inbox.read_claim(scope, event_id)`，需要开启三次独立的 SQLite 连接并执行三条 `SELECT` 语句。在并发工作线程执行 `claim_next()`、`handoff()`、`associate_stripe_intent()` 或 `accept_stripe_readback()` 时，可能读到跨表撕裂状态（例如先读到 `attempt.outcome == 'unknown'`，后读到 `claim_status.state == 'handled'`）。
2. **分表读取无法拦截跨表 `PaymentIntent` 引用冲突与范围偏移**：
   - 分表查询不会核验 `inbox.path` 与 `journal.path` 是否指向同一规范 SQLite 文件，也不会校验 `scope`（`tenant_id`、`provider_account`、`livemode`）与 `operation`（`tenant_id`、`provider_account`、`provider`）的一致性；
   - 更关键的是，若 `payment_attempts.provider_reference`（如 `pi_a`）与 `stripe_event_inbox.provider_reference`（如 `pi_b`）不一致，单表查询均会各自返回成功，无法在读取侧闭锁拦截跨表 `PaymentIntent` 绑定冲突。
3. **`StripeEventInbox.handoff()` / `finish_readback()` 及 `stripe_observation` 连接前类型校验缺口**：
   - `handoff()` 与 `finish_readback()` 原先在开启 SQLite 连接并执行 `BEGIN IMMEDIATE` 之后才在 `_current_claim()` 内校验 `isinstance(claim, ReadbackClaim)`；
   - `reconcile_stripe_intent()` 与 `validate_stripe_intent()` 缺少对 `journal`、`operation`、`previous` 的前置类型闭锁校验。

---

## 2. AI-Native 架构设计改进

### 2.1 `StripeReadbackProvenance` 与三表联查单快照只读审计

在 `lab/stripe_readback.py` 中新增不可变数据类 `StripeReadbackProvenance` 及 `find_stripe_readback_provenance(inbox, journal, scope, event_id, operation)` / `read_stripe_readback_provenance(inbox, journal, scope, event_id, operation)`：

```sql
SELECT
    att.fingerprint AS att_fingerprint,
    att.approval_id AS att_approval_id,
    att.provider AS att_provider,
    att.provider_account AS att_provider_account,
    att.idempotency_key AS att_idempotency_key,
    att.outcome AS att_outcome,
    att.provider_reference AS att_provider_reference,
    i.event_id AS i_event_id,
    i.event_type AS i_event_type,
    i.provider_reference AS i_provider_reference,
    i.payload_sha256 AS i_payload_sha256,
    c.event_id AS c_event_id,
    c.worker_id AS c_worker_id,
    c.generation AS c_generation,
    c.state AS c_state
FROM (SELECT 1)
LEFT JOIN payment_attempts att
    ON att.tenant_id=? AND att.operation_id=?
LEFT JOIN stripe_event_inbox i
    ON i.tenant_id=? AND i.endpoint_id=?
    AND i.provider_account=? AND i.livemode=? AND i.event_id=?
LEFT JOIN stripe_readback_claims c
    ON c.tenant_id=? AND c.endpoint_id=?
    AND c.provider_account=? AND c.livemode=? AND c.event_id=?
```

| 演进阶段 / 异常场景 | `payment_attempts` | `stripe_event_inbox` | `stripe_readback_claims` | `find_stripe_readback_provenance()` 行为 |
|---|---|---|---|---|
| **均不存在** | `NULL` | `NULL` | `NULL` | 返回 `None`（`read_stripe_readback_provenance()` 抛出 `StripeReadbackError`） |
| **Webhook 先到达（未预留操作）** | `NULL` | 存在 (`pi_x`) | `NULL` 或 `active`/`handled` | 返回 `attempt=None, receipt=InboxReceipt(...), claim_status=...` |
| **操作已预留（Webhook 未到达）** | 存在 (`None` 或 `pi_x`) | `NULL` | `NULL` | 返回 `attempt=PaymentAttempt(...), receipt=None, claim_status=None` |
| **操作未关联 `pi_` + Webhook 已记录** | 存在 (`None`) | 存在 (`pi_x`) | `NULL` 或 `active`/`handled` | 返回 `attempt=PaymentAttempt('unknown', None), receipt=InboxReceipt(...)` |
| **操作已关联 `pi_x` + Webhook 已记录/认领/完成** | 存在 (`pi_x`) | 存在 (`pi_x`) | `NULL` / `active` / `handled` | 返回完整三表耦合快照 |
| **跨表 `PaymentIntent` 引用冲突** | 存在 (`pi_x`) | 存在 (`pi_y != pi_x`) | 任意 | 抛出 `StripeReadbackError("Receipt differs from the trusted PaymentIntent association.")` |
| **孤儿认领行（无收据父行）** | 任意 | `NULL` | 存在 | 抛出 `StripeInboxError` |

### 2.2 连接前参数闭锁校验

- `StripeEventInbox.handoff()` 与 `finish_readback()` 在开启 SQLite 连接及 `BEGIN IMMEDIATE` 前校验 `isinstance(claim, ReadbackClaim)`；
- `reconcile_stripe_intent()` 与 `validate_stripe_intent()` 在访问属性或读取账本前校验 `journal`、`operation`、`previous` 与 `retrieved_account` 类型。

---

## 3. 验证结果

- 新增测试套件：`tests/test_stripe_readback_provenance.py`（`4 passed, 71 subtests passed`）。
- Stripe 专项回归套件：`220 passed, 477 subtests passed`。
- 全量测试套件：`4337 passed, 1515 subtests passed`。
