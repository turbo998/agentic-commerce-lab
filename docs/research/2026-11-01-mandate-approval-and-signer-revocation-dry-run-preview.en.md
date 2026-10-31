# 2026-11-01 Lock-Free Single-`SELECT` Dry-Run Previews for Checkout Mandate, Payment Approval, and Merchant Signer Revocation (`MandateRevocationPreview` / `ApprovalRevocationPreview` / `SignerRevocationPreview`)

> **Stage 1750** · Verification Date: `2026-11-01` (Beijing Time `UTC+08:00`) · Related Code: [`lab/checkout.py`](../../lab/checkout.py), [`lab/payment_approvals.py`](../../lab/payment_approvals.py), [`lab/merchant_signers.py`](../../lab/merchant_signers.py), [`tests/test_checkout_provenance.py`](../../tests/test_checkout_provenance.py), [`tests/test_approval_admission_provenance.py`](../../tests/test_approval_admission_provenance.py) · [中文版](2026-11-01-mandate-approval-and-signer-revocation-dry-run-preview.md)

---

## 1. Background & Architectural Problem

Across Stages 1744–1749, we added lock-free single-`SELECT` dry-run preview contracts across all forward execution and reconciliation transitions in our Agentic Commerce control plane. However, during incident response, compliance circuit-breaking, or human-in-the-loop overrides, operators also need to trigger three irreversible **Operator Revocation** actions:

1. **Checkout Mandate Revocation** (`CheckoutStore.revoke(mandate_id)` in [`lab/checkout.py`](../../lab/checkout.py));
2. **Payment Approval Revocation** (`PaymentApprovalStore.revoke(operation)` in [`lab/payment_approvals.py`](../../lab/payment_approvals.py));
3. **Merchant Signer Key Revocation** (`MerchantSignerStore.revoke(scope)` in [`lab/merchant_signers.py`](../../lab/merchant_signers.py)).

Previously, these three revocation boundaries only offered mutating `revoke()` methods that immediately acquired `BEGIN IMMEDIATE` write locks, lacking read-only single-`SELECT` dry-run previews to determine whether the target record is currently `active` (`would_revoke=True`) or already `revoked` (`would_revoke=False`), whether a checkout mandate already has a consumed receipt (`has_consumed_receipt`, determining whether the post-revocation phase is `revoked_unspent` or `consumed_revoked`), and whether bound fingerprints or scopes match.

---

## 2. Dialectical Comparison: Classic 3-Tier Web App vs. AI-Native Agentic Commerce

| Dimension | Classic 3-Tier Web App (Cloud Well-Architected) | AI-Native Agentic Commerce Workload Architecture |
|---|---|---|
| **Revocation Dry-Run & Idempotency** | Admin endpoints issue `UPDATE ... SET revoked=1` directly and rely on affected row counts without distinguishing prior revocation or consumed phases | Explicitly models `MandateRevocationPreview`, `ApprovalRevocationPreview`, and `SignerRevocationPreview`, distinguishing active-to-revoked transitions (`would_revoke=True`) from idempotent re-revocations (`would_revoke=False`) in one lock-free `SELECT` |
| **Consumed Receipt & Orphan Detection** | Queries only the `mandates` table during revocation checks, ignoring child `receipts` or orphan receipt corruption | `CheckoutStore.preview_revoke()` joins `mandates` and `receipts` in a single `SELECT`, rejecting orphan receipts and projecting `existing_phase` / `projected_phase` (`revoked_unspent` vs. `consumed_revoked`) |
| **Binding Integrity Verification** | Revokes by primary key alone without checking operation fingerprints or signer scope tuples | Reuses `_bound_approval()`, `_permission()`, and optional `_verify_mandate_binding()`, failing closed on any binding drift or corrupted column |

---

## 3. Stage 1750 Design & Implementation

### 3.1 `MandateRevocationPreview` and `CheckoutStore.preview_revoke()` (`lab/checkout.py`)
- Added frozen dataclass `MandateRevocationPreview(mandate_id, existing_status, projected_status, would_revoke, has_consumed_receipt)` with `existing_phase` and `projected_phase` properties (`active_unspent` / `revoked_unspent` / `consumed_active` / `consumed_revoked`).
- Added `CheckoutStore.preview_revoke(mandate_id, checkout=None)` to inspect `mandates` and `receipts` in one lock-free `SELECT`, rejecting orphan receipts and verifying optional `checkout` binding.

### 3.2 `ApprovalRevocationPreview` and `PaymentApprovalStore.preview_revoke()` (`lab/payment_approvals.py`)
- Added frozen dataclass `ApprovalRevocationPreview(operation, existing_status, projected_status, would_revoke)` enforcing `existing_status.fingerprint == operation.fingerprint`, `projected_status.state == "revoked"`, and `would_revoke == (existing_status.state == "active")`.
- Added `PaymentApprovalStore.preview_revoke(operation)` using `_bound_approval(db, operation)` inside a single lock-free `SELECT`.

### 3.3 `SignerRevocationPreview` and `MerchantSignerStore.preview_revoke()` (`lab/merchant_signers.py`)
- Added frozen dataclass `SignerRevocationPreview(scope, existing_status, projected_status, would_revoke)` enforcing `existing_status.scope == scope`, `projected_status.state == "revoked"`, and `would_revoke == (existing_status.state == "active")`.
- Added `MerchantSignerStore.preview_revoke(scope)` using `_permission(db, scope)` inside a single lock-free `SELECT`.

---

## 4. Verification Results

Added single-`SELECT` trace assertions, idempotent post-revocation checks, and dataclass fail-closed invariant tests in [`tests/test_checkout_provenance.py`](../../tests/test_checkout_provenance.py) and [`tests/test_approval_admission_provenance.py`](../../tests/test_approval_admission_provenance.py):

- `python -m pytest tests/test_checkout_provenance.py tests/test_approval_admission_provenance.py -q`: `13 passed, 148 subtests passed`
