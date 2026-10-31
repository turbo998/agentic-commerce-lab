# Stage 1743 — Eight-State Stripe Readback Phase Classification (`StripeReadbackPhase`) and Attempt/Handled-Claim Fail-Closed Invariants

> **中文对应版**: [2026-11-01-stripe-readback-provenance-phase-and-attempt-integrity.md](2026-11-01-stripe-readback-provenance-phase-and-attempt-integrity.md)  
> **Status**: Implemented & Verified (`2026-11-01`)  
> **Related Modules**: [`lab/stripe_readback.py`](../../lab/stripe_readback.py), [`lab/merchant_signers.py`](../../lab/merchant_signers.py), [`tests/test_stripe_readback_provenance.py`](../../tests/test_stripe_readback_provenance.py), [`tests/test_stripe_lifecycle_provenance.py`](../../tests/test_stripe_lifecycle_provenance.py), [`tests/test_operation_admission_provenance.py`](../../tests/test_operation_admission_provenance.py)

---

## 1. Context & Architectural Problem

Across the single-snapshot provenance models introduced in Stages 1732, 1736, and 1738 (`OperationAdmissionProvenance`, `StripeReadbackProvenance`, and `StripeLifecycleProvenance`), three cross-table invariant and observability gaps remained:

1. **Unassociated Terminal `PaymentAttempt` Instances (`outcome in ("succeeded", "failed")` with `provider_reference is None`) Were Not Rejected**:
   - While `PaymentAttemptJournal.read_attempt()`, `ApprovalAdmissionProvenance.__post_init__()`, and `MerchantSignerStore.find_provenance()` rejected terminal attempts lacking a `provider_reference`, `OperationAdmissionProvenance.__post_init__()`, `StripeReadbackProvenance.__post_init__()`, and `StripeLifecycleProvenance.__post_init__()` did not enforce this invariant.
   - More critically, in `StripeReadbackProvenance` and `StripeLifecycleProvenance`, cross-table `PaymentIntent` reference comparison only ran when `self.attempt.provider_reference is not None`. If `payment_attempts` was corrupted to `outcome='succeeded', provider_reference=NULL`, the cross-table check against `receipt.provider_reference` was bypassed.
2. **Pre-Webhook `attempt.provider_reference` Lacked Strict `pi_[A-Za-z0-9_]+` Regex Parity**:
   - When `receipt is None` (before webhook arrival), `StripeReadbackProvenance` and `StripeLifecycleProvenance` accepted any non-blank string (such as `"ch_123"` or `"evt_123"`) in `attempt.provider_reference`, diverging from the `pi_[A-Za-z0-9_]+` contract enforced by `InboxReceipt` and `validate_stripe_intent()`.
3. **Prematurely Handled Claims and Recovery Phase Classification**:
   - Under both `accept_stripe_readback()` and standalone `reconcile_stripe_intent()`, a readback claim can only transition to `state == "handled"` after the bound operation is reserved and associated with a `pi_...` reference. Observing `claim_status.state == "handled"` while `attempt is None` or `attempt.provider_reference is None` indicates either premature `finish_readback()` execution bypassing reconciliation or post-acceptance tampering of `payment_attempts`.
   - Furthermore, recovery orchestrators lacked deterministic zero-query properties (`event_phase` and `readback_phase`) projecting `(attempt, receipt, claim_status)` into an explicit state machine.

---

## 2. Core Design (`lab/stripe_readback.py` & `lab/merchant_signers.py`)

### 2.1 Cross-Table Attempt and Handled-Claim Fail-Closed Invariants

1. **`OperationAdmissionProvenance.__post_init__()`** (`lab/merchant_signers.py`):
   - Rejects `self.attempt.provider_reference is None and self.attempt.outcome != "unknown"` with `MerchantSignerError("Stored attempt provider reference is invalid; reconciliation required.")`.
2. **`StripeReadbackProvenance.__post_init__()` & `StripeLifecycleProvenance.__post_init__()`** (`lab/stripe_readback.py`):
   - Rejects `self.attempt.provider_reference is None and self.attempt.outcome != "unknown"` with `StripeReadbackError("Stored attempt outcome and provider reference are inconsistent.")`.
   - Rejects `self.attempt.provider_reference is not None` failing `_PI_RE = re.compile(r"pi_[A-Za-z0-9_]+")` with `StripeReadbackError("Stored attempt provider reference must be a Stripe PaymentIntent ID.")`.
   - Rejects `self.claim_status is not None and self.claim_status.state == "handled"` when `self.attempt is None or self.attempt.provider_reference is None` with `StripeReadbackError("Handled readback claim requires a PaymentIntent-associated attempt.")`.

### 2.2 Eight-State Readback Phase Classification (`StripeReadbackPhase`)

Added `event_phase: InboxEventPhase | None` and `readback_phase: StripeReadbackPhase` to `StripeReadbackProvenance` (and `StripeReadbackPhase | None` to `StripeLifecycleProvenance`, returning `None` when only pre-staged policy rows exist):

| `readback_phase` | `attempt.outcome` | `attempt.provider_reference` | `receipt` | `claim_status.state` | Architectural Meaning |
|---|---|---|---|---|---|
| `"webhook_before_reservation"` | `None` | `None` | present | `None` / `"active"` | Webhook recorded before local operation reservation |
| `"reserved_unassociated"` | `"unknown"` | `None` | `None` | `None` | Reserved locally; neither outbound `pi_...` binding nor webhook exists |
| `"awaiting_intent_association"` | `"unknown"` | `None` | present | `None` / `"active"` | Webhook recorded, but local attempt still awaits trusted `associate_stripe_intent` |
| `"associated_awaiting_webhook"` | `"unknown"` | `pi_...` | `None` | `None` | Outbound `pi_...` bound; awaiting webhook delivery or direct readback |
| `"ready_to_claim"` | `"unknown"` | `pi_...` | present | `None` | Both `pi_...` association and matching `InboxReceipt` exist; ready for `claim_next()` |
| `"claimed_awaiting_acceptance"` | `"unknown"` | `pi_...` | present | `"active"` | Active worker claim exists with matching `pi_...`; ready for `accept_stripe_readback()` |
| `"handled_pending_outcome"` | `"unknown"` | `pi_...` | present | `"handled"` | Claim accepted while `PaymentIntent` was in a pending status (`"processing"`), retaining `"unknown"` |
| `"terminal_reconciled"` | `"succeeded"` / `"failed"` | `pi_...` | any | any | Payment attempt has converged to a terminal outcome |

---

## 3. Verification

- `python -m pytest tests/test_stripe_readback_provenance.py tests/test_stripe_lifecycle_provenance.py tests/test_operation_admission_provenance.py -q`: `16 passed, 204 subtests passed`.
- Full regression suite passes with zero live funds, network calls, or secrets.
