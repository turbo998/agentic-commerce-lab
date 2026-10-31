# 2026-11-01 Stage 1746: Payment Approval and Merchant Signer Lock-Free Single-`SELECT` Dry-Run Previews and Provenance Phase Alignment

**中文版**: [2026-11-01-approval-and-signer-admission-dry-run-preview.md](2026-11-01-approval-and-signer-admission-dry-run-preview.md)

## 1. Context & Architectural Pain Points

Following `CheckoutStore.preview_execute()` (Stage 1744), `find_stripe_observation_preview()` (Stage 1741), and `PaymentAttemptJournal.preview_reserve()` / `preview_reconcile()` plus `preview_signed_checkout()` (Stage 1745), the two remaining multi-table admission gates in the codebase—**`PaymentApprovalStore.admit()`** and **`MerchantSignerStore.admit()`**—still lacked lock-free single-`SELECT` dry-run previews and unified lifecycle phase projections:

1. **Missing Clock-Evaluated Approval State and Provenance Lifecycle Phase Properties**:
   `PaymentApprovalStatus` only exposed static `state in ("active", "revoked")` and `expires_at` without a `state_at(now) -> ApprovalTimedState` helper that evaluates `revoked > expired > active` against a validated signed-64-bit integer clock. Furthermore, `ApprovalAdmissionProvenance` lacked `.path` (`TwoStoreAdmissionPath = Literal["direct_reservation", "approval_admission"]`) and `.attempt_phase` (`AttemptPhase`), while `OperationAdmissionProvenance` also lacked `.attempt_phase`.
2. **No Lock-Free Single-`SELECT` Dry-Run Preview for `PaymentApprovalStore.admit()`**:
   Callers inspecting whether a signed checkout approval admission would be granted, whether a new `payment_admissions` row would be recorded, or whether an existing retry/direct reservation would be denied without backfilling `payment_admissions` had no read-only single-`SELECT` preview.
3. **No Lock-Free Single-`SELECT` Dry-Run Preview for `MerchantSignerStore.admit()`**:
   `MerchantSignerStore.admit()` fences five tables (`merchant_signer_permissions`, `payment_approvals`, `payment_attempts`, `payment_admissions`, `merchant_timed_admissions`) plus optional RFC 9421 signature-time windows (`[created, expires)`), but lacked a lock-free single-`SELECT` preview projecting both approval and timed-signer admission history (and their non-backfill retry semantics).

---

## 2. AI-Native Architectural Design (Stage 1746)

### 2.1 `PaymentApprovalStatus.state_at(now)` and Provenance Phase Alignment

In `lab/payment_approvals.py` and `lab/merchant_signers.py`:

- `ApprovalTimedState = Literal["active", "expired", "revoked"]` and `PaymentApprovalStatus.state_at(now: int) -> ApprovalTimedState`:
  Validates `now` as a nonnegative signed-64-bit integer (`0 <= now <= 2**63 - 1`, rejecting `bool`) and evaluates `"revoked"` before `"expired"` (`now >= expires_at`) and `"active"`.
- `TwoStoreAdmissionPath = Literal["direct_reservation", "approval_admission"]`, `ApprovalAdmissionProvenance.path`, `ApprovalAdmissionProvenance.attempt_phase`, and `OperationAdmissionProvenance.attempt_phase`:
  Aligns two-store and three-store provenance snapshots with the 4-state `AttemptPhase` taxonomy (`reserved_unassociated`, `pending_associated`, `succeeded_terminal`, `failed_terminal`).

### 2.2 `ApprovalAdmissionPreview` and `PaymentApprovalStore.preview_admit()`

Added frozen dataclass `ApprovalAdmissionPreview` and `PaymentApprovalStore.preview_admit(...)` in `lab/payment_approvals.py`:

- Validates RFC 9421 request binding via `validate_signed_checkout(...)` and same-file SQLite path resolution before opening a connection;
- Executes **one lock-free `SELECT`** joining `payment_approvals`, `payment_attempts`, `payment_admissions`, and conflict subqueries (`approval_conflict`, `idempotency_conflict`);
- Enforces the exact validation order and **non-backfill invariant** of `admit()`:
  - When `existing_attempt is None`: `decision = DispatchDecision(PaymentAttempt("unknown", None), True)`, `would_record_admission = True`, and `projected_admission = ApprovalAdmission(operation.fingerprint, now, approval_status.expires_at)`.
  - When `existing_attempt is not None`: `decision = DispatchDecision(existing_attempt, False)`, `would_record_admission = False`, and `projected_admission = existing_admission` (never backfilling `payment_admissions` for legacy direct reservations).

### 2.3 `SignerAdmissionPreview` and `MerchantSignerStore.preview_admit()`

Added frozen dataclass `SignerAdmissionPreview` and `MerchantSignerStore.preview_admit(...)` in `lab/merchant_signers.py`:

- Executes **one lock-free `SELECT`** joining `merchant_signer_permissions`, `payment_approvals`, `payment_attempts`, `payment_admissions`, `merchant_timed_admissions`, and conflict subqueries;
- Enforces the exact check ordering of `MerchantSignerStore.admit()`: signer permission active $\rightarrow$ approval exists and active $\rightarrow$ `require_signature_time(timed, now=now)` when `signature` is a `TimedRequestSignatureSnapshot` $\rightarrow$ clock type and approval expiry check $\rightarrow$ existing admission/timed-admission integrity and orphan detection $\rightarrow$ reservation/idempotency conflict and non-backfill projection;
- Exposes `.dispatch_allowed`, `.attempt_phase`, and `.projected_path` (`"timed_signer_admission"`, `"approval_admission"`, or `"direct_reservation"`).

---

## 3. Verification

- Targeted suites: `tests/test_approval_admission_provenance.py`, `tests/test_payment_approvals.py`, `tests/test_payment_approval_read.py`, `tests/test_merchant_signers.py`, and `tests/test_timed_signer_admission_find.py` all pass (`85 passed, 207 subtests passed`).
- Full regression suite: Verified with `python -m pytest -q` across the entire repository before commit.
