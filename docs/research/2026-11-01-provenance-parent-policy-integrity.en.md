# Five-Table Provenance Parent-Policy Referential Integrity and PaymentAttempt Invariants (Stage 1734)

**中文版**: [2026-11-01-provenance-parent-policy-integrity.md](2026-11-01-provenance-parent-policy-integrity.md)

## Context

In Stages 1732 and 1733, `MerchantSignerStore.find_provenance()` joined the three per-operation tables (`payment_attempts`, `payment_admissions`, and `merchant_timed_admissions`) in a single `SELECT ... LEFT JOIN` snapshot and verified `payment_attempts` denormalized uniqueness columns. However, `commerce.sqlite3` also contains two append-only, non-replaceable **parent policy tables**:

1. `payment_approvals (tenant_id, approval_id, fingerprint, expires_at, revoked)`: Every `payment_admissions` row is created inside `PaymentApprovalStore._admit_in_transaction()` by copying `expires_at` from the bound `payment_approvals` row. Revocation only transitions `revoked` from `0` to `1`; rows are never deleted or mutated in `fingerprint` or `expires_at`.
2. `merchant_signer_permissions (tenant_id, merchant, target_uri, key_id, revoked)`: Every `merchant_timed_admissions` row is created inside `MerchantSignerStore.admit()` after verifying the matching `merchant_signer_permissions` row. Revocation only transitions `revoked` from `0` to `1`; rows are never deleted.

Additionally, `PaymentAttemptJournal._attempt()` (used by `read()`, `reserve()`, `reconcile()`, and `associate_stripe_intent()`) previously checked only `outcome` without enforcing the `provider_reference` nonblank/non-null invariants introduced in `read_attempt()`, and `PaymentAttempt` / `DispatchDecision` lacked `__post_init__` self-validation.

## Architectural Improvements (Stage 1734)

### 1. Five-Table Single-Snapshot Parent-Policy Verification in `MerchantSignerStore.find_provenance`

Extended the single `SELECT ... LEFT JOIN` query in `find_provenance()` across all five governance and provenance tables using their exact `PRIMARY KEY` indexes:

- `payment_attempts` (`USING (tenant_id, operation_id)`)
- `payment_admissions` (`USING (tenant_id, operation_id)`)
- `payment_approvals` (`ON app.tenant_id = k.tenant_id AND app.approval_id = k.approval_id`)
- `merchant_timed_admissions` (`USING (tenant_id, operation_id)`)
- `merchant_signer_permissions` (`ON perm.tenant_id = k.tenant_id AND perm.merchant = k.merchant AND perm.target_uri = tmd.target_uri AND perm.key_id = tmd.key_id`)

Without adding SQL round-trips, acquiring write locks, or breaking post-admission revocation (`revoked = 1`), `find_provenance()` now enforces:

- **Parent Approval Fingerprint Binding**: Whenever an operation is reserved or admitted and `app_fingerprint` is present, `app_fingerprint == operation.fingerprint` is required.
- **Parent Approval Existence & Expiry Parity**: Whenever a `payment_admissions` row exists (`adm_fp is not None`), the parent `payment_approvals` row must exist (rejecting orphan approval admissions), `app_expires_at` must be a valid positive 64-bit integer, `app_revoked in (0, 1)`, and `adm_expires_at == app_expires_at` must hold.
- **Parent Signer Permission Existence & State Integrity**: Whenever a `merchant_timed_admissions` row exists (`tmd_fp is not None`), the parent `merchant_signer_permissions` row for `(tenant_id, merchant, target_uri, key_id)` must exist (preventing forged timed-admission rows for unallowed keys/routes) and satisfy `perm_revoked in (0, 1)`.

### 2. Unified Fail-Closed Invariants on `PaymentAttempt`, `DispatchDecision`, and `_reconcile_in_transaction()`

- `PaymentAttempt.__post_init__`: Enforces `outcome in ("unknown", "succeeded", "failed")` and requires a nonblank `str` whenever `provider_reference` is present.
- `DispatchDecision.__post_init__`: Enforces `isinstance(attempt, PaymentAttempt)`, `type(dispatch_allowed) is bool`, and forbids `dispatch_allowed=True` when `attempt.outcome != "unknown"` or `attempt.provider_reference is not None`.
- `PaymentAttemptJournal._attempt()`, `read_attempt()`, and `_reconcile_in_transaction()` share `PaymentAttempt` construction validation and explicitly block rebinding unassociated terminal attempts (`previous.provider_reference is None and previous.outcome != "unknown"`).

## Verification

Added `tests/test_provenance_parent_policy_integrity.py` covering:

- Direct reservations without a `payment_approvals` row succeeding as `direct_reservation`, while rejecting conflicting `payment_approvals` fingerprints.
- Preservation of five-table provenance after dual revocation (`approvals.revoke()` and `signers.revoke()`), and fail-closed rejection of deleted parent policy rows, corrupted `expires_at` / `revoked` columns, cross-table expiry split-brain (`adm.expires_at != app.expires_at`), and forged `merchant_timed_admissions` `key_id` values.
- `PaymentAttempt` and `DispatchDecision` `__post_init__` invariants and unified fail-closed `provider_reference` checks across `read()`, `read_attempt()`, `reserve()`, and `reconcile()`.
