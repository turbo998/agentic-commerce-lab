# Stage 1735: Two-Store Approval-Admission Provenance Inspector & Policy-Row Write-Path Fail-Closed Integrity

> **Date**: 2026-11-01 (`UTC+08:00`)  
> **Stage**: Stage 1735  
> **Core Modules**: `lab/payment_approvals.py`, `lab/merchant_signers.py`, `lab/stripe_readback.py`, `lab/stripe_delivery.py`, `tests/test_approval_admission_provenance.py`  
> **中文版**: [`2026-11-01-approval-admission-provenance.md`](2026-11-01-approval-admission-provenance.md)

---

## 1. Problem Statement & Architectural Gap

In Stages 1732–1734, we introduced `MerchantSignerStore.find_provenance()` for the three-store governance topology (`MerchantSignerStore` + `PaymentApprovalStore` + `PaymentAttemptJournal`). However, lightweight checkout gateways frequently deploy the **two-store topology** (`PaymentApprovalStore` + `PaymentAttemptJournal` without `MerchantSignerStore`). Reviewing the read and write boundaries across `PaymentApprovalStore`, `MerchantSignerStore`, `accept_stripe_readback`, and `VerifiedDelivery` surfaced three remaining gaps:

1. **No Single-Snapshot Cross-Table Provenance Inspector for the Two-Store Topology**:
   - Callers deploying only `PaymentApprovalStore` + `PaymentAttemptJournal` had to invoke `journal.read_attempt(operation)`, `approvals.read_approval(operation)`, and `approvals.find_admission(operation)` across three separate SQLite connections (exposing read skew under concurrent admission/revocation/reconciliation), and none of those single-table readers could detect orphan `payment_admissions` rows (missing a `payment_attempts` reservation or missing a parent `payment_approvals` policy row) or cross-table approval expiry drift (`payment_admissions.expires_at != payment_approvals.expires_at`).
2. **Missing Pre-Write Policy-Row Integrity Validation in `revoke()` and `admit()`**:
   - `PaymentApprovalStore._bound_approval(db, operation)` previously checked only row existence and `fingerprint`, allowing `revoke(operation)` to overwrite corrupted `expires_at` (`0`, `-5`, `1.5`, `'invalid-expiry'`) or `revoked` (`2`, `-1`, `b'0'`, `'revoked'`) values with `revoked = 1`, while `_admit_in_transaction()` checked `if row["revoked"] != 0:` before validating `revoked in (0, 1)`, misreporting corrupted `revoked = 2` values as `"Approval is revoked."`.
   - Similarly, `MerchantSignerStore._permission(db, scope)` did not validate `row["revoked"] in (0, 1)`, allowing `signers.revoke(scope)` to overwrite corrupted rows and `signers.admit(...)` to misreport `revoked = 2` as `"Signer permission is revoked."`.
3. **Pre-Connection Argument Checks in `accept_stripe_readback()` and `VerifiedDelivery` Invariants**:
   - `accept_stripe_readback()` dereferenced `.path` and opened a `BEGIN IMMEDIATE` transaction before validating the types of `inbox`, `journal`, `claim`, and `operation`.
   - `VerifiedDelivery` lacked a fail-closed `__post_init__` guard.

---

## 2. AI-Native Architectural Improvements

### 2.1 `ApprovalAdmissionProvenance` and Three-Table Single-Snapshot Audit

We added the frozen `ApprovalAdmissionProvenance` dataclass along with `PaymentApprovalStore.find_provenance(journal, operation)` and `read_provenance(journal, operation)` in `lab/payment_approvals.py`:

```sql
SELECT
    att.fingerprint AS att_fingerprint,
    att.approval_id AS att_approval_id,
    att.provider AS att_provider,
    att.provider_account AS att_provider_account,
    att.idempotency_key AS att_idempotency_key,
    att.outcome AS att_outcome,
    att.provider_reference AS att_provider_reference,
    adm.fingerprint AS adm_fingerprint,
    adm.admitted_at AS adm_admitted_at,
    adm.expires_at AS adm_expires_at,
    app.fingerprint AS app_fingerprint,
    app.expires_at AS app_expires_at,
    app.revoked AS app_revoked
FROM (SELECT 1)
LEFT JOIN payment_attempts att
    ON att.tenant_id=? AND att.operation_id=?
LEFT JOIN payment_admissions adm
    ON adm.tenant_id=? AND adm.operation_id=?
LEFT JOIN payment_approvals app
    ON app.tenant_id=? AND app.approval_id=?
```

- Returns `None` (`find_provenance`) or raises `PaymentApprovalError` (`read_provenance`) when the operation was never reserved (without creating `merchant_signer_*` tables).
- Supports legacy direct reservations both without a `payment_approvals` row (`approval_status=None, approval_admission=None`) and with an active or revoked `payment_approvals` row (`approval_status=PaymentApprovalStatus(...), approval_admission=None`).
- Fails closed on orphan `payment_admissions` rows (missing `payment_attempts` or missing `payment_approvals`), cross-table expiry drift (`adm.expires_at != app.expires_at`), 10-dimension fingerprint or denormalized column drift, and unassociated terminal attempts.

### 2.2 Policy-Row Write-Path Fail-Closed Checks & Webhook Delivery Invariants

- `PaymentApprovalStore._bound_approval(db, operation)` now validates `expires_at` (`1..2**63-1`) and `revoked in (0, 1)` before returning the row to `revoke()` or `_admit_in_transaction()`.
- `MerchantSignerStore._permission(db, scope)` now validates `revoked in (0, 1)` before returning the row to `revoke()` or `admit()`.
- `accept_stripe_readback()` validates `inbox`, `journal`, `claim`, and `operation` types before resolving paths or opening a SQLite connection, and `VerifiedDelivery.__post_init__()` enforces `timestamp`, `payload_sha256`, and `requires_readback is True`.

---

## 3. Verification

- New unit test suite: `tests/test_approval_admission_provenance.py` (`4 passed, 61 subtests passed`).
- Combined targeted regression suites: `121 passed, 315 subtests passed`; full repository suite: `4333 passed, 1444 subtests passed`.
