# Stage 1733 — `payment_attempts` Denormalized Uniqueness-Column Parity & Read-Model Construction Invariants

> **中文对应版**: [2026-11-01-attempt-denormalized-binding-integrity.md](2026-11-01-attempt-denormalized-binding-integrity.md)  
> **Verification Date (Beijing Time)**: `2026-11-01` (`01:12–01:22+08:00` window)  
> **Related Assets**: [`lab/payment_attempts.py`](../../lab/payment_attempts.py) · [`lab/payment_approvals.py`](../../lab/payment_approvals.py) · [`lab/merchant_signers.py`](../../lab/merchant_signers.py) · [`tests/test_attempt_denormalized_binding_integrity.py`](../../tests/test_attempt_denormalized_binding_integrity.py)

---

## 1. Background & Problem Statement

In `PaymentAttemptJournal`, the SQLite `payment_attempts` table stores both the 10-dimension SHA-256 `fingerprint` and four denormalized uniqueness-index columns:
- `approval_id` (enforcing `UNIQUE (tenant_id, approval_id)` so one approval cannot be reused across operations)
- `provider`, `provider_account`, and `idempotency_key` (enforcing `UNIQUE (provider, provider_account, idempotency_key)` and `UNIQUE (provider, provider_account, provider_reference)`, plus cross-operation `provider_reference` conflict checks during `reconcile()`)

Previously, two defense-in-depth gaps existed:
1. **Unchecked Split-Brain Between `fingerprint` and Denormalized Index Columns**: `PaymentAttemptJournal._find()`, `read_attempt()`, and `MerchantSignerStore.find_provenance()` checked `row["fingerprint"] == operation.fingerprint` without verifying that the stored `approval_id`, `provider`, `provider_account`, and `idempotency_key` columns also matched `operation`. If a denormalized column was corrupted in SQLite while `fingerprint` remained intact, SQLite's `UNIQUE` constraints and `reconcile()`'s cross-operation lookup would evaluate against the corrupted column while binding checks silently passed.
2. **Missing Construction-Time `__post_init__` Validation on Read-Model Dataclasses**: `PaymentApprovalStatus`, `ApprovalAdmission`, and `TimedSignerAdmission` validated fields in store query methods but did not enforce fail-closed invariants when constructed directly in memory.

---

## 2. Dialectical Architecture Analysis: Classic 3-Tier Web App vs. AI-Native Agentic Commerce

| Architectural Dimension | Classic 3-Tier Web / ORM Architecture | AI-Native Agentic Commerce Architecture (Stage 1733) |
|---|---|---|
| **Digest vs. Denormalized Index Columns** | Assumes that if a row's stored `fingerprint` matches, its denormalized index columns (`provider`, `idempotency_key`, etc.) must also be intact. | Recognizes that SQLite cannot natively enforce `fingerprint == sha256(...)`: `PaymentAttemptJournal._verify_row_binding()` and `MerchantSignerStore.find_provenance()` verify both `fingerprint` and all four denormalized index columns (`approval_id`, `provider`, `provider_account`, `idempotency_key`), preventing index/digest split-brain. |
| **Read-Model Value Object Boundaries** | Treats read-only DTOs as passive containers and validates only inside DAO query helpers. | Enforces fail-closed `__post_init__` invariants on `PaymentApprovalStatus`, `ApprovalAdmission`, and `TimedSignerAdmission` (64-char lowercase hex SHA-256 digest, strict `type(...) is int` timestamps rejecting booleans, monotonic window bounds, and RFC 9421 signature label syntax). |

---

## 3. Implementation Details

1. **`lab/payment_attempts.py`**:
   - Added `PaymentAttemptJournal._verify_row_binding(row, operation)` checking `fingerprint`, `approval_id`, `provider`, `provider_account`, and `idempotency_key`; reused across `_find()` and `read_attempt()` so `reserve()`, `read()`, `read_attempt()`, `reconcile()`, `associate_stripe_intent()`, `reconcile_stripe_intent()`, and `accept_stripe_readback()` all fail closed on denormalized column drift.
2. **`lab/merchant_signers.py`**:
   - Updated `MerchantSignerStore.find_provenance()` to select and verify `att_approval_id`, `att_provider`, `att_provider_account`, and `att_idempotency_key` in the single-snapshot `SELECT ... LEFT JOIN` query.
   - Added fail-closed `__post_init__` validation to `TimedSignerAdmission`.
3. **`lab/payment_approvals.py`**:
   - Added fail-closed `__post_init__` validation to `PaymentApprovalStatus` and `ApprovalAdmission`.

---

## 4. Verification & Regression Results

Added 4 unit tests (with 38 subtests) in [`tests/test_attempt_denormalized_binding_integrity.py`](../../tests/test_attempt_denormalized_binding_integrity.py):

- `test_approval_and_timed_admission_dataclasses_enforce_post_init_invariants`
- `test_corrupted_denormalized_attempt_columns_fail_closed_across_journal_methods`
- `test_corrupted_denormalized_attempt_columns_fail_closed_across_admission_and_provenance`
- `test_corrupted_denormalized_attempt_columns_block_stripe_association_and_readback`
