# Stage 1738 — Single-Snapshot Cross-Plane Lifecycle Provenance Inspector (`StripeLifecycleProvenance`, 5-Table & 7-Table Topologies)

> **中文对应版**: [2026-11-01-stripe-lifecycle-provenance.md](2026-11-01-stripe-lifecycle-provenance.md)  
> **Stage**: Stage 1738  
> **Verification Date (Beijing Time)**: `2026-11-01`  
> **Related Artifacts**: [`lab/stripe_readback.py`](../../lab/stripe_readback.py), [`tests/test_stripe_lifecycle_provenance.py`](../../tests/test_stripe_lifecycle_provenance.py)

---

## 1. Motivation & Architectural Gap (AI-Native Commerce vs. Classic 3-Tier Web Architecture)

Across the local SQLite persistence stack for Agentic Commerce, a payment operation's end-to-end lifecycle spans two control planes and up to **7 SQLite tables** bridged by `payment_attempts`:

1. **Admission Control Plane (5 tables)**: `payment_approvals`, `payment_admissions`, `merchant_signer_permissions`, `merchant_timed_admissions`, and `payment_attempts`.
2. **Readback Reconciliation Plane (3 tables)**: `payment_attempts`, `stripe_event_inbox`, and `stripe_readback_claims`.

Prior to Stage 1738, auditing both how an operation was admitted and how its Stripe webhook readback was reconciled required calling `signers.find_provenance()` at $T_1$ and `find_stripe_readback_provenance()` at $T_2$:

- **Cross-Plane Torn-Read Race ($T_1 \neq T_2$)**: Concurrent workers calling `admit()`, `associate_stripe_intent()`, `accept_stripe_readback()`, `approvals.revoke()`, or `signers.revoke()` between $T_1$ and $T_2$ could cause callers to stitch together an unreserved or unassociated admission view at $T_1$ with a terminal `succeeded` readback view at $T_2$.
- **Approval & Signer Revocation Visibility**: `OperationAdmissionProvenance` validated `revoked IN (0, 1)` on parent policy rows but did not surface `PaymentApprovalStatus` or `MerchantSignerPermissionStatus` in the returned provenance object, nor did it surface pre-staged `payment_approvals` rows before `payment_attempts` reservation.
- **3-Store (5-Table) vs. 4-Store (7-Table) Deployment Topologies**: Deployments that do not instantiate the opt-in `MerchantSignerStore` only create 5 tables (`payment_attempts`, `payment_admissions`, `payment_approvals`, `stripe_event_inbox`, `stripe_readback_claims`), whereas deployments with RFC 9421 route/key fencing create all 7 tables.

---

## 2. Stage 1738 Design

### 2.1 `StripeLifecycleProvenance` Frozen Dataclass

Added `StripeLifecycleProvenance` (`@dataclass(frozen=True)`) in [`lab/stripe_readback.py`](../../lab/stripe_readback.py):

- Captures `scope`, `event_id`, `fingerprint`, `attempt`, `approval_status`, `approval_admission`, `signer_permission`, `timed_signer_admission`, `receipt`, and `claim_status` from a single SQLite read snapshot.
- Exposes three zero-query projection properties:
  - `admission_path -> AdmissionProvenancePath | None`: returns `None` when unreserved (`attempt is None`), or `"timed_signer_admission"` / `"approval_admission"` / `"direct_reservation"`.
  - `admission_provenance -> OperationAdmissionProvenance | None`: projects the 5-table admission provenance model from the same snapshot.
  - `readback_provenance -> StripeReadbackProvenance | None`: projects the 3-table readback provenance model from the same snapshot.
- Enforces fail-closed invariants in `__post_init__`:
  - Rejects all-empty snapshots where no lifecycle artifact is present.
  - Verifies 64-character lowercase hex SHA-256 `fingerprint` parity across `approval_status`, `approval_admission`, and `timed_signer_admission`.
  - Rejects orphan `approval_admission` rows lacking a reserved `attempt` or parent `approval_status`, and enforces `approval_admission.expires_at == approval_status.expires_at`.
  - Rejects orphan `timed_signer_admission` rows lacking `attempt`, `approval_admission`, or `signer_permission`, and enforces `signer_permission.scope == timed_signer_admission.scope`, tenant parity, and single-clock-sample parity (`timed_signer_admission.admitted_at == approval_admission.admitted_at`).
  - Enforces `receipt`, `claim_status`, and cross-plane `PaymentIntent` reference parity (`attempt.provider_reference == receipt.provider_reference`).

### 2.2 `find_stripe_lifecycle_provenance()` and `read_stripe_lifecycle_provenance()`

- Accepts `signers: MerchantSignerStore | None = None`:
  - When `signers is None`, executes a single lock-free **5-table** `SELECT ... LEFT JOIN` without requiring `merchant_signer_*` tables to exist.
  - When `signers` is provided, verifies `Path.resolve(strict=True)` parity across all four stores before executing a single lock-free **7-table** `SELECT ... LEFT JOIN`.
- Executes exactly one read-only `SELECT` statement with zero `BEGIN`, `INSERT`, `UPDATE`, or `DELETE` statements and zero clock samples.

---

## 3. Validation

Added [`tests/test_stripe_lifecycle_provenance.py`](../../tests/test_stripe_lifecycle_provenance.py):

- `python -m pytest tests/test_stripe_lifecycle_provenance.py tests/test_stripe_readback_provenance.py tests/test_stripe_readback.py -q`: `30 passed, 152 subtests passed` (`5 passed, 61 subtests passed` in `test_stripe_lifecycle_provenance.py`).
