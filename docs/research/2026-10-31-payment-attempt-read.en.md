# 2026-10-31 Read-Only Local Payment Attempt Inspection and Unreserved-vs-Conflict Disambiguation (Stage 1728)

> **中文对应版**: [2026-10-31-payment-attempt-read.md](2026-10-31-payment-attempt-read.md)

## 1. Context and Architectural Gap

Across the three-gate local commerce stack in `agentic-commerce-lab` (`MerchantSignerStore` $\rightarrow$ `PaymentApprovalStore` $\rightarrow$ `PaymentAttemptJournal`):

- Stage 1726 added non-mutating approval state inspection (`PaymentApprovalStore.read_approval(operation) -> PaymentApprovalStatus | None`);
- Stage 1727 added non-mutating signer permission inspection (`MerchantSignerStore.read_permission(scope) -> MerchantSignerPermissionStatus | None`);
- However, in `PaymentAttemptJournal` (`lab/payment_attempts.py`), the existing `read(operation) -> PaymentAttempt` raised the same `AttemptConflict` exception for two fundamentally different conditions:
  1. **Benign Unreserved State**: `AttemptConflict("Operation was never reserved.")`;
  2. **Binding Integrity Conflict**: `AttemptConflict("Operation binding changed; do not dispatch.")` or corrupted persisted state.

For read-only audit, pre-recovery inspection, and operator diagnostics, conflating an unreserved operation with a tampered operation binding forces callers to match exception message text, and passing a non-`PaymentOperation` argument to `read()` previously opened a SQLite connection before failing with `AttributeError`.

## 2. Primary-Source Verification and Architectural Mapping (2026-10-31)

| External Protocol / Product Surface | Initial Release / Window | Verification Status (`2026-10-31`) | Local Stage 1728 Architectural Mapping |
|---|---|---|---|
| **Stripe Idempotency & Payment Attempt Reconciliation (ACP / SPT / PaymentIntents)** | 2025–2026 ongoing | `51/51` sources `status="ok"` | Cleanly separates "attempt never reserved (`None`)", "attempt reserved with `unknown` outcome", and "tampered operation fingerprint (`AttemptConflict`)" |
| **Stripe Link Agent Wallet** | Private preview | Intake form: `https://docs.stripe.com/forms/agent-wallet-interest` | Supports read-only local attempt-journal inspection around delegated wallet flows without live network side effects |
| **Stripe MCP Key Migration Window** | `2026-10-31` cutover (`2026-11-30` prose contradiction persists) | `calendar_days_until_deadline = 30` (enforcing `2026-10-31` conservatively) | Allows lock-free (`SELECT`-only, no `BEGIN IMMEDIATE`) attempt-journal audits during credential cutover |

## 3. Design and Implementation (`lab/payment_attempts.py`)

We added `PaymentAttemptJournal.read_attempt(operation: PaymentOperation) -> PaymentAttempt | None` while keeping `read(operation) -> PaymentAttempt` fully backward-compatible:

1. **Pre-Connection Input Validation**: Calls `_require_operation(operation)` and raises `AttemptConflict("A trusted PaymentOperation is required.")` before opening any SQLite connection if `operation` is not a `PaymentOperation`.
2. **Lock-Free Read-Only Query (`SELECT`-Only)**: Runs `SELECT fingerprint,outcome,provider_reference FROM payment_attempts WHERE tenant_id=? AND operation_id=?` without `BEGIN IMMEDIATE` or any row mutation.
3. **Strict Unreserved vs. Conflict Disambiguation**:
   - Returns `None` when no row exists for `(tenant_id, operation_id)`;
   - Raises `AttemptConflict("Operation binding changed; do not dispatch.")` if any bound dimension in `operation.fingerprint` (`approval_id`, `provider`, `provider_account`, `idempotency_key`, or any `Checkout` field) differs from the persisted record.
4. **Persisted Row Integrity Verification**:
   - Verifies `outcome in ("unknown", "succeeded", "failed")`;
   - Verifies that terminal outcomes (`"succeeded"`, `"failed"`) carry a non-blank string `provider_reference` and that `"unknown"` carries either `None` or a non-blank string `provider_reference`.

## 4. Verification Summary

- Targeted suite: `python -m pytest tests/test_payment_attempt_read.py tests/test_payment_attempts.py -v` (`27 passed, 55 subtests passed`, with `test_payment_attempt_read.py` accounting for `8 passed, 19 subtests passed`; full suite `4295 passed, 1141 subtests passed`).
- Covered invariants: `None` on absent attempt, cross-process durability across `unknown`/pending/`succeeded`/`failed`, frozen `PaymentAttempt` dataclass, full fingerprint tampering detection across all bound dimensions, tenant/operation isolation, pre-connection rejection of invalid inputs, rollback invisibility on commit failure, corrupted row rejection, and `SELECT`-only execution without `BEGIN IMMEDIATE`.
