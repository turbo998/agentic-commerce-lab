# 2026-11-01 Optional Read-Only Timed-Signer Admission Lookup & Non-Timed Path Disambiguation (Stage 1730)

> **中文对应版**: [2026-11-01-timed-signer-admission-find.md](2026-11-01-timed-signer-admission-find.md)

## 1. Context & Architectural Problem

Across the three local execution-fencing stores in `agentic-commerce-lab` (`MerchantSignerStore` $\rightarrow$ `PaymentApprovalStore` $\rightarrow$ `PaymentAttemptJournal`), an operation can legitimately enter the journal through multiple paths:

1. **Timed Signer Admission**: Calling `MerchantSignerStore.admit()` with a `TimedRequestSignatureSnapshot` checks both the signature window and approval expiry against the same post-lock clock sample (`BEGIN IMMEDIATE`), writing to `payment_attempts`, `payment_admissions`, and `merchant_timed_admissions`.
2. **Bare Signer Admission**: Calling `MerchantSignerStore.admit()` with a bare `RequestSignatureSnapshot` writes to `payment_attempts` and `payment_admissions` while leaving `merchant_timed_admissions` empty.
3. **Approval-Only or Legacy Reservation**: Admitting via `PaymentApprovalStore.admit()` or reserving directly via `PaymentAttemptJournal.reserve()` also leaves no row in `merchant_timed_admissions`.

Previously, `MerchantSignerStore.read_timed_admission(operation) -> TimedSignerAdmission` raised the same `MerchantSignerError` whether the operation had no `merchant_timed_admissions` row (unadmitted or admitted via a non-timed path) or the stored row suffered fingerprint tampering, corrupted `target_uri`/`key_id` scope, malformed `signature_label`, or invalid timestamps (`created`, `expires`, `admitted_at`). Offline audit and dispute-evidence pipelines could not distinguish a legitimate non-timed admission path from persisted data corruption without catching `MerchantSignerError` or matching error message text.

## 2. Primary-Source Verification & Architectural Mapping (2026-11-01)

| External Protocol / Surface | Initial Release / Window | Verified Status (`2026-11-01`) | Local Stage 1730 Architectural Mapping |
|---|---|---|---|
| **Visa Trusted Agent Protocol (TAP)** | RFC 9421 HTTP Message Signatures | `51/51` primary sources `ok` (`unchanged`) | Separates timed signature admission provenance (`created`/`expires`) from bare snapshot admission without retroactive backfilling |
| **Stripe MCP Key Migration Window (First Day Past `2026-10-31`)** | Banner cutoff `2026-10-31`; body prose `2026-11-30` | Contradiction persists on `2026-11-01` (`calendar_days_until_deadline = 29`) | Completes the lock-free (`SELECT`-only) provenance triad (`read_attempt` + `find_admission` + `find_timed_admission`) |
| **Stripe Shared Payment Tokens (SPT) / Link Agent Wallet** | SPT `2026-03-04.preview` / Link Private Preview | `34`-country parity across Seller & Connect docs | Preserves read-only signer provenance inspection without granting dispatch or payment authority |

## 3. Design & Implementation (`lab/merchant_signers.py`)

We added `_require_operation` and `MerchantSignerStore.find_timed_admission(operation: PaymentOperation) -> TimedSignerAdmission | None`, and refactored `read_timed_admission(operation) -> TimedSignerAdmission` as a strict wrapper:

1. **Pre-Connection Validation**: `_require_operation(operation)` rejects non-`PaymentOperation` inputs with `MerchantSignerError` before opening a SQLite connection.
2. **Lock-Free Read-Only Query (`SELECT`-Only)**: Executes `SELECT * FROM merchant_timed_admissions WHERE tenant_id=? AND operation_id=?` without `BEGIN IMMEDIATE`, without checking live permission state (`_permission`), and without sampling a clock (`require_signature_time`).
3. **Non-Timed Absence vs. Integrity Conflict Disambiguation**:
   - Returns `None` when no row exists for `(tenant_id, operation_id)` (including unadmitted operations, bare-snapshot admissions, approval-only admissions, or direct journal reservations);
   - Raises `MerchantSignerError("Timed-admission record differs from the bound operation.")` if `row["fingerprint"] != operation.fingerprint`;
   - Raises `MerchantSignerError` if `target_uri`/`key_id` fail `MerchantSignerScope` validation, if `signature_label` violates RFC 8941 key syntax, or if `created`, `expires`, `admitted_at` are non-integers or violate `0 <= created <= admitted_at < expires <= MAX_SIGNATURE_TIMESTAMP`.

## 4. Verification Summary

- Targeted suite: `python -m pytest tests/test_timed_signer_admission_find.py tests/test_timed_signer_history.py tests/test_merchant_signers.py tests/test_merchant_signer_permission_read.py -v` (`77 passed, 155 subtests passed`, including `6 passed, 38 subtests passed` in `test_timed_signer_admission_find.py`).
- Full regression suite: `python -m pytest -q` (`4310 passed, 1202 subtests passed`).
