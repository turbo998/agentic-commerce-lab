# 2026-11-01 Stage 1747: Stripe Readback Acceptance Lock-Free Single-`SELECT` Dry-Run Preview (`StripeReadbackAcceptancePreview`) and Cross-Plane Provenance Phase Alignment

**中文版**: [2026-11-01-stripe-readback-acceptance-dry-run-preview.md](2026-11-01-stripe-readback-acceptance-dry-run-preview.md)

## 1. Context & Architectural Pain Points

Following the single-`SELECT` lock-free dry-run previews for checkout mandates (`CheckoutStore.preview_execute()`, Stage 1744), payment attempt reservation/reconciliation (`PaymentAttemptJournal.preview_reserve()` / `preview_reconcile()`, Stage 1745), and payment approval/merchant signer admission (`PaymentApprovalStore.preview_admit()` / `MerchantSignerStore.preview_admit()`, Stage 1746), the final cross-table atomic write gate in the Stripe asynchronous reconciliation plane—**`accept_stripe_readback()`** in `lab/stripe_readback.py`—still lacked a lock-free single-`SELECT` dry-run preview and unified attempt-phase projection:

1. **Missing `attempt_phase` Property on `StripeReadbackProvenance` and `StripeLifecycleProvenance`**:
   While Stage 1745 added the 4-state `AttemptPhase` (`reserved_unassociated`, `pending_associated`, `succeeded_terminal`, `failed_terminal`) to `PaymentAttempt` and Stage 1746 aligned `ApprovalAdmissionProvenance` and `OperationAdmissionProvenance`, `StripeReadbackProvenance` and `StripeLifecycleProvenance` did not yet expose `.attempt_phase -> AttemptPhase | None`.
2. **No Lock-Free Single-`SELECT` Dry-Run Preview for `accept_stripe_readback()`**:
   Callers inspecting whether an active `ReadbackClaim` and retrieved Stripe `PaymentIntent` object would pass all cross-table acceptance invariants (active claim with matching `worker_id` and `generation`, matching inbox receipt, reserved attempt associated with `claim.receipt.provider_reference`, valid `validate_stripe_intent()` observation, no cross-operation `provider_reference` conflict, and no terminal outcome reversal) and whether acceptance would mutate `payment_attempts` (`would_mutate_attempt`) had no read-only single-`SELECT` preview.

---

## 2. AI-Native Architectural Design (Stage 1747)

### 2.1 `StripeReadbackProvenance.attempt_phase` and `StripeLifecycleProvenance.attempt_phase`

Added `.attempt_phase -> AttemptPhase | None` to both `StripeReadbackProvenance` and `StripeLifecycleProvenance` in `lab/stripe_readback.py`, returning `None` when `attempt is None` and `attempt.phase` otherwise.

### 2.2 `StripeReadbackAcceptancePreview` and `preview_accept_stripe_readback()`

Added frozen dataclass `StripeReadbackAcceptancePreview` and `preview_accept_stripe_readback(...)` in `lab/stripe_readback.py`:

- Validates `inbox`, `journal`, `claim`, `operation`, and same-file SQLite path resolution before opening a connection;
- Executes **one lock-free `SELECT`** joining `stripe_event_inbox`, `stripe_readback_claims`, `payment_attempts`, and the cross-operation `reference_conflict` subquery;
- Enforces the exact check ordering and error types of `accept_stripe_readback()`:
  1. Claim and receipt exist, stored receipt matches `claim.receipt`, `worker_id` and `generation` match, and claim state is `"active"` (raising `StripeReadbackError("Already-handled hints cannot authorize acceptance.")` when already handled);
  2. `claim.scope` matches `operation.tenant_id`, `operation.provider_account`, and `stripe:live` / `stripe:test`;
  3. Attempt is reserved with matching denormalized binding columns and `previous.provider_reference == claim.receipt.provider_reference`;
  4. `validate_stripe_intent(...)` validates the retrieved `PaymentIntent` and returns `observation in ("pending", "succeeded", "failed")`;
  5. Verifies no `reference_conflict` and no terminal outcome reversal, projecting `projected_attempt`, `projected_claim_status = ReadbackClaimStatus(claim, "handled")`, `would_mutate_attempt`, and `would_mark_claim_handled = True`;
- Exposes `.previous_phase`, `.projected_phase`, `.projected_readback_phase` (`"handled_pending_outcome"` or `"terminal_reconciled"`), and `.to_readback_provenance()`.

---

## 3. Verification

- Targeted suites: `tests/test_stripe_readback_provenance.py`, `tests/test_stripe_lifecycle_provenance.py`, `tests/test_stripe_readback.py`, and `tests/test_stripe_inbox.py` all pass (`53 passed, 224 subtests passed`).
- Full regression suite: Verified with `python -m pytest -q` across the entire repository before commit.
