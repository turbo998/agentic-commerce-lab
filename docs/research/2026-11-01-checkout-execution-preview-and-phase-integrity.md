# 2026-11-01 Stage 1744：结账授权溯源阶段分类（`CheckoutPhase` / `CheckoutTimedPhase`）、指纹摘要绑定与无写锁执行预演（`CheckoutExecutionPreview`）

> **English companion**: [2026-11-01-checkout-execution-preview-and-phase-integrity.en.md](2026-11-01-checkout-execution-preview-and-phase-integrity.en.md)  
> **验证时间（北京时间）**：`2026-11-01T04:00:05+08:00`  
> **关联模块**：[`lab/checkout.py`](../../lab/checkout.py)、[`tests/test_checkout_provenance.py`](../../tests/test_checkout_provenance.py)

---

## 1. 架构背景与问题定义

在 Agentic Commerce 的本地结账授权与收据幂等平面（[`lab/checkout.py`](../../lab/checkout.py)）中，`CheckoutStore` 将用户/运营侧批准的单次结账授权令（`mandates`）与执行收据（`receipts`）耦合在同一 SQLite 库中。Stage 1737 引入了 `CheckoutProvenance` 与单条无锁查询 `find_provenance()`，但在深入审计后仍发现三项完整性与可观测性缺口：

1. **`CheckoutProvenance` 指纹摘要与父级授权缺失校验**：
   - `CheckoutProvenance.__post_init__()` 此前仅校验 `fingerprint` 是否满足 64 位小写十六进制格式（`[0-9a-f]{64}`），而未核验 `fingerprint` 是否等于 `[mandate_id, mandate_status.cart_digest]` 的规范化 SHA-256 摘要（`_execution_fingerprint_for_digest`）。
   - 同时，当 `mandate_status=None` 且 `receipt=None` 时，`CheckoutProvenance.__post_init__()` 未拒绝构造该空快照（而在 `find_provenance()` 中无授权且无收据恒返回 `None`）。
2. **`execute()` 在孤儿收据 + 新幂等键重试时的错误归因偏移**：
   - 当 `PRAGMA foreign_keys = OFF` 下父表 `mandates` 行被异常删除而 `receipts` 残留孤儿收据时，若调用方以原 `request_key` 调用 `execute()` 会正确抛出 `AuthorizationError("Orphan receipt exists without a recorded mandate.")`；但若以新 `request_key` 调用 `execute()`，原实现先查询 `receipts WHERE request_key=?`（未命中）再查询 `mandates WHERE id=?`（未命中），直接抛出 `"No trusted approval exists for this mandate."`，掩盖了 `receipts WHERE mandate_id=?` 已存在孤儿收据的数据损坏事实。
3. **缺少无写锁的单查询结账执行预演模型（`CheckoutExecutionPreview`）**：
   - `CheckoutStore.execute()` 会立即开启 `BEGIN IMMEDIATE` 写锁并在授权有效时消费授权令。运维排障与恢复编排需要一种零写锁、单条 `SELECT` 的预演能力，在给定可信时钟 `now` 下确定性返回四态执行决策（`consume_mandate`、`replay_receipt`、`blocked_revoked`、`blocked_expired`）以及预计生成的 `Receipt`。

---

## 2. AI-Native 架构设计改进

### 2.1 无时钟阶段（`CheckoutPhase`）与带时钟阶段（`CheckoutTimedPhase`）分离

- `CheckoutProvenance.phase -> CheckoutPhase`（零时钟依赖）：
  - `"active_unspent"`：授权令处于 `active` 且尚未生成收据；
  - `"revoked_unspent"`：授权令已被撤销且从未被消费；
  - `"consumed_active"`：授权令已生成幂等收据且未撤销；
  - `"consumed_revoked"`：授权令在生成收据后被调用 `revoke()`（保留已完成收据，同时标记授权撤销）。
- `CheckoutProvenance.phase_at(now: int) -> CheckoutTimedPhase`（纯函数时钟评估，不采样系统墙钟）：
  - 当 `receipt is not None` 时，无论 `now >= expires_at` 与否，均返回 `"consumed_active"` 或 `"consumed_revoked"`（体现已完成收据在过期后仍可通过原 `request_key` 幂等重放的不变量）；
  - 当 `receipt is None` 时，优先判定 `"revoked_unspent"`，其次若 `now >= mandate_status.expires_at` 判定为 `"expired_unspent"`，否则为 `"active_unspent"`。

### 2.2 单快照无写锁执行预演（`CheckoutExecutionPreview`）

新增不可变数据类 `CheckoutExecutionPreview` 及 `CheckoutStore.find_execution_preview()` / `CheckoutStore.preview_execute()`：

| `timed_phase` | `decision` | `execution_allowed` | `will_mutate` | `projected_receipt` |
|---|---|---|---|---|
| `"active_unspent"` | `"consume_mandate"` | `True` | `True` | `Receipt(f"sim_{fingerprint[:24]}", amount, currency)` |
| `"expired_unspent"` | `"blocked_expired"` | `False` | `False` | `None` |
| `"revoked_unspent"` | `"blocked_revoked"` | `False` | `False` | `None` |
| `"consumed_active"` / `"consumed_revoked"`（同 `request_key`） | `"replay_receipt"` | `True` | `False` | 已持久化 `provenance.receipt` |

若已消费授权遭遇不同 `request_key`，或购物车/商户/币种/金额/行完整性不匹配，`find_execution_preview()` 与 `CheckoutExecutionPreview.__post_init__()` 均闭锁抛出 `AuthorizationError`。

---

## 3. 测试验证

运行 `python -m pytest tests/test_checkout_provenance.py tests/test_checkout.py tests/test_checkout_admission.py -q`：
- **`46 passed, 152 subtests passed`**（`8.24s`）。
- 覆盖 `CheckoutPhase` / `CheckoutTimedPhase` 全部分支、单条 `SELECT` 无写锁 SQL 跟踪验证、`CheckoutProvenance` 指纹摘要不匹配闭锁拒绝、`CheckoutExecutionPreview` 16 项字段篡改闭锁拒绝，以及孤儿收据在相同/不同 `request_key` 下的统一异常归因。
