# 2026-11-01 支付尝试生命周期阶段分类（`AttemptPhase`）与单条无锁预留/对账预演（`AttemptReservationPreview` / `AttemptReconciliationPreview`）

> **Stage 1745** · 解决方案架构师深度研究笔记  
> **验证时间（北京时间）**：`2026-11-01T04:12:20+08:00`  
> **英文版（English Companion）**：[`2026-11-01-payment-attempt-phase-and-dry-run-preview.en.md`](./2026-11-01-payment-attempt-phase-and-dry-run-preview.en.md)

---

## 1. 背景与架构痛点

在 Agentic Commerce 本地持久化支付尝试日志（[`lab/payment_attempts.py`](../../lab/payment_attempts.py)）与签名结账准入边界（[`lab/checkout_admission.py`](../../lab/checkout_admission.py)）中，`PaymentAttemptJournal` 负责确保每个 `(tenant_id, operation_id)` 仅产生一次本地外呼派发授权（`dispatch_allowed=True`），并在收到可信支付服务商（PSP）观察事实后推进至终态（`succeeded` / `failed`）。对现有实现的审查揭示了三处可演进痛点：

1. **缺乏显式 4 态支付尝试生命周期阶段属性与终态一致性校验**：
   - `PaymentAttempt` 仅暴露原始字段 `outcome`（`"unknown" | "succeeded" | "failed"`）与 `provider_reference: str | None`。调用方无法通过单一属性区分“已预留但尚未绑定服务商引用”（`reserved_unassociated`）与“已绑定服务商引用但仍在处理中”（`pending_associated`），并且当数据库行被离线篡改为“终态但缺失 `provider_reference`”（`outcome in ('succeeded', 'failed')` 且 `provider_reference is None`）时，`journal.reserve(operation)` 会静默返回 `DispatchDecision(PaymentAttempt("succeeded", None), False)` 而未像 `read_attempt()` 与 `reconcile()` 那样抛出 `AttemptConflict`。
2. **`PaymentAttemptJournal.reserve()` 与 `reconcile()` 缺乏无写锁单快照预演（Dry-Run Preview）**：
   - `read_attempt(operation)` 仅按 `(tenant_id, operation_id)` 主键查询，若未预留则返回 `None`，无法在不开启 `BEGIN IMMEDIATE` 写事务的前提下预检跨操作审批占用冲突（`UNIQUE (tenant_id, approval_id)`）或跨租户服务商幂等键冲突（`UNIQUE (provider, provider_account, idempotency_key)`）。
   - 同理，在对账平面上，调用方无法通过单条无写锁 `SELECT` 预检一次 `(observation, provider_reference)` 对账是否会改变状态、幂等保持原状，或因跨操作引用冲突（`UNIQUE (provider, provider_account, provider_reference)`）而拒绝。
3. **`lab/checkout_admission.py` 缺乏端到端无锁签名结账准入预演**：
   - `validate_signed_checkout()` 仅校验签名覆盖与 JSON 载荷，而 `reserve_signed_checkout()` 直接获取 `BEGIN IMMEDIATE` 锁写入 `payment_attempts`，缺少结合签名载荷校验与日志单 `SELECT` 预检的只读入口。

---

## 2. AI-Native 架构设计：4 态尝试分类与单 `SELECT` 预留/对账预演

### 2.1 `AttemptPhase` 与 `PaymentAttempt.phase` / `is_terminal`

在 `lab/payment_attempts.py` 中新增：
- `AttemptPhase = Literal["reserved_unassociated", "pending_associated", "succeeded_terminal", "failed_terminal"]`
- `PaymentAttempt.phase` 属性与 `PaymentAttempt.is_terminal` 属性：
  - 当 `outcome == "unknown"` 时，按 `provider_reference` 是否为 `None` 返回 `"reserved_unassociated"` 或 `"pending_associated"`；
  - 当 `outcome in ("succeeded", "failed")` 且 `provider_reference is None` 时，闭锁抛出 `AttemptConflict("Stored provider reference is invalid; reconciliation required.")`；
  - 否则返回 `"succeeded_terminal"` 或 `"failed_terminal"`。
- 同时在 `PaymentAttemptJournal._reserve_in_transaction()` 中补齐对未关联终态损坏行的闭锁拦截，使 `reserve()`、`read_attempt()` 与 `reconcile()` 具有完全一致的存储完整性保证。

### 2.2 `AttemptReservationPreview`、`AttemptReconciliationPreview` 与 `preview_signed_checkout`

1. **`AttemptReservationPreview` 与 `PaymentAttemptJournal.preview_reserve(operation)`**：
   - 通过单条无写锁 `SELECT ... FROM (SELECT 1) LEFT JOIN payment_attempts AS current_op ...` 同时读取当前操作行以及 `approval_conflict` 与 `idempotency_conflict` 存在性标记；
   - 若当前操作未预留且无唯一键冲突，返回 `AttemptReservationPreview(operation=..., existing_attempt=None, decision=DispatchDecision(PaymentAttempt("unknown", None), True), would_insert=True)`；
   - 若当前操作已存在且绑定一致，返回 `AttemptReservationPreview(operation=..., existing_attempt=existing, decision=DispatchDecision(existing, False), would_insert=False)`。
2. **`AttemptReconciliationPreview` 与 `PaymentAttemptJournal.preview_reconcile(operation, *, observation, provider_reference)`**：
   - 通过单条无写锁 `SELECT ... FROM (SELECT 1) LEFT JOIN payment_attempts AS current_op ...` 同时读取当前操作行与跨操作 `reference_conflict` 标记；
   - 完整复刻 `_reconcile_in_transaction()` 的所有冲突校验，并返回 `AttemptReconciliationPreview(operation=..., observation=..., previous_attempt=..., resulting_attempt=..., state_changed=...)`。
3. **`preview_signed_checkout(...)`（`lab/checkout_admission.py`）**：
   - 先执行 `validate_signed_checkout(...)` 严格校验 RFC 9421/9530 签名快照与 5 字段结账 JSON，随后调用 `journal.preview_reserve(operation)` 完成无副作用的准入预演。

---

## 3. 验证结果

- 定向回归测试（`tests/test_payment_attempt_read.py`、`tests/test_payment_attempts.py`、`tests/test_checkout_admission.py`、`tests/test_stripe_association.py`）：
  `88 passed, 206 subtests passed`。
- 全量测试套件：`4363 passed, 1751 subtests passed`。
