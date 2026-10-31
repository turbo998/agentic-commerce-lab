# 2026-11-01 Stage 1744: Checkout Mandate Phase Classification (`CheckoutPhase` / `CheckoutTimedPhase`), Fingerprint Digest Binding, and Lock-Free Execution Preview (`CheckoutExecutionPreview`)

> **中文对应版**: [2026-11-01-checkout-execution-preview-and-phase-integrity.md](2026-11-01-checkout-execution-preview-and-phase-integrity.md)  
> **Verification Timestamp (Beijing Time)**: `2026-11-01T04:00:05+08:00`  
> **Related Modules**: [`lab/checkout.py`](../../lab/checkout.py), [`tests/test_checkout_provenance.py`](../../tests/test_checkout_provenance.py)

---

## 1. Architectural Context & Problem Statement

In the local checkout mandate and idempotency-receipt persistence plane ([`lab/checkout.py`](../../lab/checkout.py)), `CheckoutStore` couples operator-approved single-use mandates (`mandates`) with execution receipts (`receipts`) inside one SQLite database. Stage 1737 introduced `CheckoutProvenance` and lock-free `find_provenance()`, but auditing revealed three remaining integrity and observability gaps:

1. **Missing Cryptographic Fingerprint Binding and Null-Mandate Rejection in `CheckoutProvenance`**:
   - `CheckoutProvenance.__post_init__()` previously checked only that `fingerprint` matched `[0-9a-f]{64}`, without verifying that `fingerprint` equaled the canonical SHA-256 digest of `[mandate_id, mandate_status.cart_digest]` (`_execution_fingerprint_for_digest`).
   - Calling `CheckoutProvenance(..., mandate_status=None, request_key=None, receipt=None)` was also permitted at construction time even though `find_provenance()` always returns `None` when both mandate and receipt are absent.
2. **Orphan-Receipt Error Attribution Drift in `execute()` on New Idempotency Keys**:
   - If a parent `mandates` row was deleted under `PRAGMA foreign_keys = OFF` leaving an orphan row in `receipts`, calling `execute()` with the original `request_key` raised `AuthorizationError("Orphan receipt exists without a recorded mandate.")`, whereas calling `execute()` with a different `request_key` checked `receipts WHERE request_key=?` (miss) and `mandates WHERE id=?` (miss) and raised `"No trusted approval exists for this mandate."`, masking the orphan receipt row in `receipts WHERE mandate_id=?`.
3. **Lack of a Lock-Free Single-Query Execution Preview (`CheckoutExecutionPreview`)**:
   - `CheckoutStore.execute()` immediately acquires `BEGIN IMMEDIATE` and consumes the mandate when valid. Recovery auditors and preflight checks need a lock-free, single-`SELECT` preview that evaluates what `execute()` would do at a caller-supplied timestamp `now` without mutating SQLite.

---

## 2. AI-Native Architectural Improvements

### 2.1 Separating Clock-Free Phase (`CheckoutPhase`) from Clock-Evaluated Phase (`CheckoutTimedPhase`)

- `CheckoutProvenance.phase -> CheckoutPhase` (clock-independent):
  - `"active_unspent"`: Mandate is `"active"` and unconsumed;
  - `"revoked_unspent"`: Mandate is `"revoked"` and unconsumed;
  - `"consumed_active"`: Mandate has a recorded receipt and remains `"active"`;
  - `"consumed_revoked"`: Mandate was revoked after execution (preserving the completed receipt while marking authority revoked).
- `CheckoutProvenance.phase_at(now: int) -> CheckoutTimedPhase` (pure clock evaluation without wall-clock sampling):
  - When `receipt is not None`, returns `"consumed_active"` or `"consumed_revoked"` regardless of `now >= expires_at` (reflecting the invariant that completed receipts remain replayable under their original `request_key` after expiry or revocation);
  - When `receipt is None`, returns `"revoked_unspent"` if revoked, `"expired_unspent"` if `now >= mandate_status.expires_at`, or `"active_unspent"` otherwise.

### 2.2 Single-Snapshot Lock-Free Execution Preview (`CheckoutExecutionPreview`)

Added frozen `CheckoutExecutionPreview` along with `CheckoutStore.find_execution_preview()` and `CheckoutStore.preview_execute()`:

| `timed_phase` | `decision` | `execution_allowed` | `will_mutate` | `projected_receipt` |
|---|---|---|---|---|
| `"active_unspent"` | `"consume_mandate"` | `True` | `True` | `Receipt(f"sim_{fingerprint[:24]}", amount, currency)` |
| `"expired_unspent"` | `"blocked_expired"` | `False` | `False` | `None` |
| `"revoked_unspent"` | `"blocked_revoked"` | `False` | `False` | `None` |
| `"consumed_active"` / `"consumed_revoked"` (same `request_key`) | `"replay_receipt"` | `True` | `False` | Persisted `provenance.receipt` |

If an already-consumed mandate is previewed with a different `request_key`, or if any cart/merchant/currency/amount/row integrity check fails, both `find_execution_preview()` and `CheckoutExecutionPreview.__post_init__()` fail closed with `AuthorizationError`.

---

## 3. Verification

Running `python -m pytest tests/test_checkout_provenance.py tests/test_checkout.py tests/test_checkout_admission.py -q`:
- **`46 passed, 152 subtests passed`** (`8.24s`).
- Verified all `CheckoutPhase` / `CheckoutTimedPhase` branches, single-`SELECT` lock-free SQL trace assertions, fail-closed rejection of mismatched `fingerprint` digests on `CheckoutProvenance`, 16 fail-closed invariant permutations on `CheckoutExecutionPreview`, and consistent orphan-receipt detection across both original and new `request_key` values in `execute()`.
