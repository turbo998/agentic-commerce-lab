# 2026-11-01 Payment Attempt Lifecycle Phase Classification (`AttemptPhase`) and Single-`SELECT` Reservation/Reconciliation Dry-Run Previews (`AttemptReservationPreview` / `AttemptReconciliationPreview`)

> **Stage 1745** · Solutions Architect Deep-Dive Research Note  
> **Verification Timestamp (Beijing Time)**: `2026-11-01T04:12:20+08:00`  
> **Chinese Companion (中文版)**: [`2026-11-01-payment-attempt-phase-and-dry-run-preview.md`](./2026-11-01-payment-attempt-phase-and-dry-run-preview.md)

---

## 1. Context & Architectural Pain Points

In the local durable payment-attempt journal ([`lab/payment_attempts.py`](../../lab/payment_attempts.py)) and signed checkout admission gate ([`lab/checkout_admission.py`](../../lab/checkout_admission.py)), `PaymentAttemptJournal` guarantees that each `(tenant_id, operation_id)` receives at most one local dispatch authorization (`dispatch_allowed=True`) before transitioning to a terminal outcome (`succeeded` / `failed`) via trusted provider observations. Auditing the module revealed three gaps:

1. **No Explicit 4-State Attempt Phase Property or Unassociated-Terminal Rejection in `reserve()`**:
   - `PaymentAttempt` exposed raw `outcome` (`"unknown" | "succeeded" | "failed"`) and `provider_reference: str | None` fields without a phase helper distinguishing `"reserved_unassociated"` from `"pending_associated"`. Furthermore, if a row was tampered with offline to have `outcome in ('succeeded', 'failed')` while `provider_reference is None`, `journal.reserve(operation)` silently returned `DispatchDecision(PaymentAttempt("succeeded", None), False)` instead of raising `AttemptConflict` like `read_attempt()` and `reconcile()`.
2. **No Lock-Free Single-`SELECT` Dry-Run Previews for `reserve()` and `reconcile()`**:
   - `read_attempt(operation)` queries only the primary key `(tenant_id, operation_id)` and returns `None` when unreserved, so callers could not check cross-operation approval collisions (`UNIQUE (tenant_id, approval_id)`) or cross-tenant provider idempotency-key collisions (`UNIQUE (provider, provider_account, idempotency_key)`) without opening a `BEGIN IMMEDIATE` write transaction.
   - Similarly, callers lacked a lock-free single-`SELECT` preview to check whether a reconciliation observation `(observation, provider_reference)` would transition state, remain idempotent, or fail closed on cross-operation `provider_reference` collisions.
3. **No End-to-End Lock-Free Signed Checkout Admission Preview in `lab/checkout_admission.py`**:
   - `validate_signed_checkout()` checked only the request signature and JSON body, while `reserve_signed_checkout()` immediately acquired a writer lock to insert into `payment_attempts`.

---

## 2. AI-Native Architecture Design: 4-State Attempt Classification and Single-`SELECT` Previews

### 2.1 `AttemptPhase` and `PaymentAttempt.phase` / `is_terminal`

In `lab/payment_attempts.py`, we added:
- `AttemptPhase = Literal["reserved_unassociated", "pending_associated", "succeeded_terminal", "failed_terminal"]`
- `PaymentAttempt.phase` and `PaymentAttempt.is_terminal`:
  - Returns `"reserved_unassociated"` or `"pending_associated"` when `outcome == "unknown"`;
  - Fails closed with `AttemptConflict("Stored provider reference is invalid; reconciliation required.")` if `outcome in ("succeeded", "failed")` while `provider_reference is None`;
  - Returns `"succeeded_terminal"` or `"failed_terminal"` otherwise.
- Hardened `PaymentAttemptJournal._reserve_in_transaction()` so unassociated terminal rows fail closed on `reserve()` just like `read_attempt()` and `reconcile()`.

### 2.2 `AttemptReservationPreview`, `AttemptReconciliationPreview`, and `preview_signed_checkout`

1. **`AttemptReservationPreview` and `PaymentAttemptJournal.preview_reserve(operation)`**:
   - Executes a single lock-free `SELECT ... FROM (SELECT 1) LEFT JOIN payment_attempts AS current_op ...` query that projects the current operation row alongside `approval_conflict` and `idempotency_conflict` subqueries;
   - Returns `AttemptReservationPreview(operation=..., existing_attempt=None, decision=DispatchDecision(PaymentAttempt("unknown", None), True), would_insert=True)` when unreserved and conflict-free, or `would_insert=False` with `DispatchDecision(existing, False)` when already reserved.
2. **`AttemptReconciliationPreview` and `PaymentAttemptJournal.preview_reconcile(operation, *, observation, provider_reference)`**:
   - Executes a single lock-free `SELECT ... FROM (SELECT 1) LEFT JOIN payment_attempts AS current_op ...` query that projects the current operation row alongside `reference_conflict`;
   - Evaluates all reconciliation invariants and returns `AttemptReconciliationPreview(operation=..., observation=..., previous_attempt=..., resulting_attempt=..., state_changed=...)`.
3. **`preview_signed_checkout(...)` (`lab/checkout_admission.py`)**:
   - Runs `validate_signed_checkout(...)` followed by `journal.preview_reserve(operation)` for a complete side-effect-free signed checkout admission preview.

---

## 3. Verification Summary

- Targeted regression suite (`tests/test_payment_attempt_read.py`, `tests/test_payment_attempts.py`, `tests/test_checkout_admission.py`, `tests/test_stripe_association.py`):
  `88 passed, 206 subtests passed`.
- Full repository test suite: `4363 passed, 1751 subtests passed`.
