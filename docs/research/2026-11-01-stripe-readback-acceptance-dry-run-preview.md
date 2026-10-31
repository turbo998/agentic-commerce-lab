# 2026-11-01 Stage 1747：Stripe 回读验收无锁单 `SELECT` 预检（`StripeReadbackAcceptancePreview`）与跨平面 Provenance 相位对齐

**English Version**: [2026-11-01-stripe-readback-acceptance-dry-run-preview.en.md](2026-11-01-stripe-readback-acceptance-dry-run-preview.en.md)

## 1. 背景与架构痛点

在完成结账授权（`CheckoutStore.preview_execute()`，Stage 1744）、支付尝试预留/对账（`PaymentAttemptJournal.preview_reserve()` / `preview_reconcile()`，Stage 1745）与审批/商户签名准入（`PaymentApprovalStore.preview_admit()` / `MerchantSignerStore.preview_admit()`，Stage 1746）的单条无写锁 `SELECT` 预检之后，Stripe 异步事件对账平面的最后一道跨表原子写门禁——**`accept_stripe_readback()`**（在 `lab/stripe_readback.py` 中同一 `BEGIN IMMEDIATE` 事务内联结 `stripe_event_inbox`、`stripe_readback_claims` 与 `payment_attempts`）——仍缺少对应的无锁单 `SELECT` 预检与相位投影：

1. **`StripeReadbackProvenance` 与 `StripeLifecycleProvenance` 缺少统一的 `attempt_phase` 属性**：
   虽然 Stage 1745 为 `PaymentAttempt` 增加了 4 态 `AttemptPhase`（`reserved_unassociated`、`pending_associated`、`succeeded_terminal`、`failed_terminal`），且 Stage 1746 将其对齐至 `ApprovalAdmissionProvenance` 与 `OperationAdmissionProvenance`，但回读与全生命周期溯源快照（`StripeReadbackProvenance`、`StripeLifecycleProvenance`）尚未直接暴露 `.attempt_phase -> AttemptPhase | None`。
2. **`accept_stripe_readback()` 缺少无锁单 `SELECT` 预检（`preview_accept_stripe_readback()`）**：
   调用方若需在获取 `BEGIN IMMEDIATE` 写锁前预演某笔已认领的 `ReadbackClaim` 配合外部回读的 `PaymentIntent` 对象是否能通过全部绑定校验（认领仍处于 `active` 且 `worker_id` / `generation` 匹配、收据与存储行一致、操作已预留且 `provider_reference` 与收据一致、`validate_stripe_intent()` 通过、无跨操作 `provider_reference` 冲突、无终态结果翻转），以及验收后 `PaymentAttempt` 是否会发生状态跃迁（`would_mutate_attempt`）并推进至何种 `StripeReadbackPhase`，原先只能直接执行写事务。

---

## 2. AI Native 架构设计（Stage 1747）

### 2.1 `StripeReadbackProvenance.attempt_phase` 与 `StripeLifecycleProvenance.attempt_phase`

在 `lab/stripe_readback.py` 中为 `StripeReadbackProvenance` 与 `StripeLifecycleProvenance` 补齐只读属性 `attempt_phase -> AttemptPhase | None`：当 `attempt is None` 时返回 `None`，否则返回 `attempt.phase`（同时触发无关联终态行的闭锁校验）。

### 2.2 `StripeReadbackAcceptancePreview` 与 `preview_accept_stripe_readback()`

在 `lab/stripe_readback.py` 中新增不可变数据类 `StripeReadbackAcceptancePreview` 与无锁预检函数 `preview_accept_stripe_readback(...)`：

- 在连接外校验 `inbox`、`journal`、`claim`、`operation` 类型以及同库解析路径一致性；
- 通过**单条无锁 `SELECT`** 联表查询 `stripe_event_inbox`、`stripe_readback_claims`、`payment_attempts` 与 `reference_conflict` 存在性子查询；
- 按 `accept_stripe_readback()` 的精确顺序执行闭锁校验：
  1. 认领与收据存在且未损坏，存储收据等于 `claim.receipt`，`worker_id` 与 `generation` 精确匹配，且认领状态为 `"active"`（若已为 `"handled"` 则抛出 `StripeReadbackError("Already-handled hints cannot authorize acceptance.")`）；
  2. `claim.scope` 与 `operation` 的 `tenant_id`、`provider_account` 及 `stripe:live` / `stripe:test` 严格一致；
  3. 支付尝试已预留、反规范化绑定列无漂移、且 `previous.provider_reference == claim.receipt.provider_reference`；
  4. 调用 `validate_stripe_intent(...)` 得到 `observation in ("pending", "succeeded", "failed")`；
  5. 校验无跨操作 `reference_conflict` 且无终态翻转冲突，投影 `projected_attempt`、`projected_claim_status = ReadbackClaimStatus(claim, "handled")`、`would_mutate_attempt` 与 `would_mark_claim_handled = True`；
- 暴露 `.previous_phase`、`.projected_phase`、`.projected_readback_phase`（`"handled_pending_outcome"` 或 `"terminal_reconciled"`）及 `.to_readback_provenance()`。

---

## 3. 验证结果

- 定向测试：`tests/test_stripe_readback_provenance.py`、`tests/test_stripe_lifecycle_provenance.py`、`tests/test_stripe_readback.py`、`tests/test_stripe_inbox.py` 全部通过（`53 passed, 224 subtests passed`）。
- 全量回归测试：将在提交前运行 `python -m pytest -q` 验证全仓通过。
