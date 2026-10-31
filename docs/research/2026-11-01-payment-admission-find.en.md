# 2026-11-01 Optional Read-Only Local First-Admission Lookup and Unadmitted-vs-Conflict Disambiguation (Stage 1729)

> **中文对应版**: [2026-11-01-payment-admission-find.md](2026-11-01-payment-admission-find.md)

## 1. Context and Architectural Gap

Across the three-gate local commerce stack in `agentic-commerce-lab` (`MerchantSignerStore` $\rightarrow$ `PaymentApprovalStore` $\rightarrow$ `PaymentAttemptJournal`), Stages 1726–1728 added lock-free (`SELECT`-only) optional read methods for `payment_approvals`, `merchant_signer_permissions`, and `payment_attempts`.

However, for the first-gate admission provenance table `payment_admissions` in `PaymentApprovalStore` (`lab/payment_approvals.py`), the existing `read_admission(operation) -> ApprovalAdmission` still raised the same `PaymentApprovalError` exception for two distinct conditions:

1. **Benign Absence (Unadmitted or Legacy Pre-Reserved Operation)**: The operation was approved via `approve()` but `admit()` has not yet been called, or the attempt was pre-reserved directly in `PaymentAttemptJournal` without backfilling `payment_admissions` (`PaymentApprovalError("No first-admission record exists for this operation.")`);
2. **Integrity Conflict**: The stored admission record's `fingerprint` differs from `operation.fingerprint`, or stored `admitted_at` / `expires_at` values violate `0 <= admitted_at < expires_at <= 2**63 - 1`.

## 2. Primary-Source Verification and Architectural Mapping (2026-11-01)

| External Protocol / Product Surface | Initial Release / Window | Verification Status (`2026-11-01`) | Local Stage 1729 Architectural Mapping |
|---|---|---|---|
| **Stripe MCP Key Migration Window (First Day Past `2026-10-31`)** | Banner cutoff `2026-10-31` / `after November 1, 2026`; body prose `after November 30, 2026` | Verified on `2026-11-01`: `docs.stripe.com/mcp.md` still retains both conflicting dates (`calendar_days_until_deadline = 29` to `2026-11-30`, while `2026-10-31` has elapsed) | Enables lock-free audit disambiguating unadmitted operations (`None`) from tampered admission provenance (`PaymentApprovalError`) during post-deadline cutover |
| **Stripe Shared Payment Tokens (SPT)** | Preview `2026-03-04.preview` | Seller/Connect parity holds across `34` countries (SHA-256 `6ae0a508...`) | Cleanly separates static approval state (`read_approval`) from first-admission clock provenance (`find_admission`) |
| **Stripe Link Agent Wallet** | Private preview | Intake form: `https://docs.stripe.com/forms/agent-wallet-interest` | Preserves strict boundary between local admission provenance and external wallet authorization |

## 3. Design and Implementation (`lab/payment_approvals.py`)

We added `PaymentApprovalStore.find_admission(operation: PaymentOperation) -> ApprovalAdmission | None` and refactored `read_admission(operation) -> ApprovalAdmission` to delegate to `find_admission(operation)` (raising `PaymentApprovalError("No first-admission record exists for this operation.")` when `None` for 100% backward compatibility):

1. **Pre-Connection Input Validation**: Calls `self._require_operation(operation)` before opening any SQLite connection.
2. **Lock-Free Read-Only Query (`SELECT`-Only)**: Runs `SELECT fingerprint,admitted_at,expires_at FROM payment_admissions WHERE tenant_id=? AND operation_id=?` without `BEGIN IMMEDIATE`.
3. **Unadmitted vs. Conflict Disambiguation**:
   - Returns `None` when no row exists for `(tenant_id, operation_id)` (including unadmitted approvals, rolled-back admissions, or unbackfilled legacy reservations);
   - Raises `PaymentApprovalError("Admission record differs from the bound operation.")` on any `fingerprint` mismatch across all 10 bound dimensions;
   - Raises `PaymentApprovalError("Stored admission times are invalid.")` if `admitted_at` or `expires_at` is non-`int` or violates `0 <= admitted_at < expires_at <= 2**63 - 1`.

## 4. Verification Summary

- Targeted suite: `python -m pytest tests/test_payment_admission_find.py tests/test_admission_provenance.py tests/test_payment_approval_read.py -v` (`44 passed, 54 subtests passed`, with `test_payment_admission_find.py` contributing `9 passed, 23 subtests passed`).
- Full regression suite: `python -m pytest -q` (`4304 passed, 1164 subtests passed`).
