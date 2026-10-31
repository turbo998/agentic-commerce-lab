# 2026-11-01 Lock-Free Single-`SELECT` Dry-Run Previews for Checkout Mandate, Payment Approval, and Merchant Signer Provisioning (`MandateGrantPreview` / `ApprovalGrantPreview` / `SignerGrantPreview`)

> **Stage 1751** · Verification Date: `2026-11-01` (Beijing Time `UTC+08:00`) · Related Code: [`lab/checkout.py`](../../lab/checkout.py), [`lab/payment_approvals.py`](../../lab/payment_approvals.py), [`lab/merchant_signers.py`](../../lab/merchant_signers.py), [`tests/test_checkout_provenance.py`](../../tests/test_checkout_provenance.py), [`tests/test_approval_admission_provenance.py`](../../tests/test_approval_admission_provenance.py) · [中文版](2026-11-01-mandate-approval-and-signer-grant-dry-run-preview.md)

---

## 1. Background & Architectural Problem

After completing Stages 1744–1750, every **execution, admission, reconciliation, association, and revocation** transition across the Agentic Commerce control plane had a lock-free single-`SELECT` dry-run preview contract. Stage 1751 completes the full policy lifecycle by adding lock-free single-`SELECT` dry-run previews for the three **Operator Provisioning / Grant** entry points:

1. **Checkout Mandate Provisioning** (`CheckoutStore.approve()` $\rightarrow$ `MandateGrantPreview` / `preview_approve()` in [`lab/checkout.py`](../../lab/checkout.py));
2. **Payment Approval Provisioning** (`PaymentApprovalStore.approve()` $\rightarrow$ `ApprovalGrantPreview` / `preview_approve()` in [`lab/payment_approvals.py`](../../lab/payment_approvals.py));
3. **Merchant Signer Permission Grant** (`MerchantSignerStore.allow()` $\rightarrow$ `SignerGrantPreview` / `preview_allow()` in [`lab/merchant_signers.py`](../../lab/merchant_signers.py)).

---

## 2. Dialectical Comparison: Classic 3-Tier Web App vs. AI-Native Agentic Commerce

| Dimension | Classic 3-Tier Web App (Cloud Well-Architected) | AI-Native Agentic Commerce Workload Architecture |
|---|---|---|
| **Provisioning Idempotency & Replacement Prevention** | Frequently uses `INSERT OR REPLACE` / `UPSERT`, risking silent overwrite of previously consumed or revoked policy bindings | Enforces strict write-once policy provisioning (replacement forbidden) and previews duplicate-key conflicts in a single lock-free `SELECT` via `MandateGrantPreview`, `ApprovalGrantPreview`, and `SignerGrantPreview` |
| **Projected Initial Status Verification** | Provisioning calls return `None` or a boolean without projecting the bound status record | Preview dataclasses construct and verify strongly typed `MandateStatus`, `PaymentApprovalStatus`, and `MerchantSignerPermissionStatus` (`state="active"`, `would_record=True`) |

---

## 3. Stage 1751 Design & Implementation

### 3.1 `MandateGrantPreview` and `CheckoutStore.preview_approve()` (`lab/checkout.py`)
- Added frozen dataclass `MandateGrantPreview(mandate_id, checkout, max_amount, expires_at, projected_status, would_record)` verifying `max_amount >= checkout.amount`, `expires_at > 0`, `projected_status` alignment with `checkout.digest`, and `would_record is True`.
- Added `CheckoutStore.preview_approve(mandate_id, checkout, *, max_amount, expires_at)` to check `SELECT 1 FROM mandates WHERE id=?` in one lock-free query and reject duplicate mandate IDs with `AuthorizationError`.

### 3.2 `ApprovalGrantPreview` and `PaymentApprovalStore.preview_approve()` (`lab/payment_approvals.py`)
- Added frozen dataclass `ApprovalGrantPreview(operation, expires_at, projected_status, would_record)` verifying `projected_status == PaymentApprovalStatus(operation.fingerprint, expires_at, "active")`.
- Added `PaymentApprovalStore.preview_approve(operation, *, expires_at)` using a single lock-free `SELECT 1 FROM payment_approvals WHERE tenant_id=? AND approval_id=?`.

### 3.3 `SignerGrantPreview` and `MerchantSignerStore.preview_allow()` (`lab/merchant_signers.py`)
- Added frozen dataclass `SignerGrantPreview(scope, projected_status, would_record)` verifying `projected_status == MerchantSignerPermissionStatus(scope, "active")`.
- Added `MerchantSignerStore.preview_allow(scope)` using a single lock-free `SELECT 1 FROM merchant_signer_permissions WHERE tenant_id=? AND merchant=? AND target_uri=? AND key_id=?`.

---

## 4. Verification Results

Added single-`SELECT` trace assertions, duplicate provisioning rejection tests, and dataclass invariant checks in [`tests/test_checkout_provenance.py`](../../tests/test_checkout_provenance.py) and [`tests/test_approval_admission_provenance.py`](../../tests/test_approval_admission_provenance.py):

- `python -m pytest tests/test_checkout_provenance.py tests/test_approval_admission_provenance.py -q`: `13 passed, 164 subtests passed`
