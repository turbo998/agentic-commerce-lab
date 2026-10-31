# Stage 1749: Lock-Free Single-`SELECT` Dry-Run Preview for Stripe `PaymentIntent` Association (`StripeAssociationPreview`) and Observation Phase Alignment

> **Verification Date**: 2026-11-01 (Beijing Time `UTC+08:00`)  
> **Chinese Version（中文版）**: [`2026-11-01-stripe-intent-association-dry-run-preview.md`](2026-11-01-stripe-intent-association-dry-run-preview.md)  
> **Related Artifacts**: [`lab/stripe_observation.py`](../../lab/stripe_observation.py), [`tests/test_stripe_association.py`](../../tests/test_stripe_association.py)

---

## 1. Context & Architectural Problem

While Stage 1741 introduced `StripeObservationPreview` for `reconcile_stripe_intent()`, the companion state-transition primitive in `lab/stripe_observation.py`—**initial `PaymentIntent` reference binding (`associate_stripe_intent()`)**—still lacked a lock-free single-`SELECT` dry-run preview:

1. **Distinct Transition Invariants of `associate_stripe_intent()`**:
   - Even when the inspected `PaymentIntent` snapshot already has `status="succeeded"` or `status="canceled"`, initial association never advances a payment attempt to a terminal outcome; it binds `PaymentAttempt("unknown", expected_reference)` (`"reserved_unassociated"` $\to$ `"pending_associated"`).
   - Conversely, when `associate_stripe_intent()` is retried with the same `expected_reference` on an already-associated attempt (including a settled `"succeeded_terminal"` or `"failed_terminal"` attempt), it preserves `previous` unchanged (`would_bind=False`) without downgrading terminal state.
2. **Cross-Operation `reference_conflict` Detection Without `BEGIN IMMEDIATE`**:
   - Recovery controllers need a single lock-free `SELECT` to verify `(tenant_id, operation_id)` denormalized row bindings, check whether `expected_reference` is already bound to another operation under the same `(provider, provider_account)` namespace (`reference_conflict`), and run full `validate_stripe_intent()` quote/routing verification before acquiring a write lock.

---

## 2. AI-Native Architectural Design

### 2.1 `StripeAssociationPreview` and `StripeObservationPreview` Phase Properties

In `lab/stripe_observation.py`:

- Added `previous_phase: AttemptPhase` and `next_phase: AttemptPhase` properties to `StripeObservationPreview`.
- Added the immutable `StripeAssociationPreview` dataclass with fail-closed `__post_init__` invariants:
  - `expected_reference` must match `pi_[A-Za-z0-9_]+`;
  - Conflicting `previous.provider_reference` raises `AttemptConflict("Provider reference changed; investigate the conflict.")`;
  - Unassociated terminal `previous` raises `AttemptConflict("An unassociated terminal attempt cannot be rebound.")`;
  - First-time binding (`previous.provider_reference is None`) requires `would_bind=True` and `next_attempt == PaymentAttempt("unknown", expected_reference)`;
  - Idempotent retry (`previous.provider_reference == expected_reference`) requires `would_bind=False` and `next_attempt == previous`.
  - Exposes `previous_phase`, `next_phase`, and `is_already_bound`.

### 2.2 Single-`SELECT` Lock-Free Preview Functions

Added `find_stripe_association_preview()`, `read_stripe_association_preview()`, and `preview_associate_stripe_intent()`:

- Executes a single lock-free `SELECT p.*, CASE WHEN EXISTS (...) THEN 1 ELSE 0 END AS reference_conflict FROM payment_attempts p WHERE p.tenant_id = ? AND p.operation_id = ?` query to verify operation binding, `validate_stripe_intent()` snapshot semantics, and cross-operation `provider_reference` uniqueness without acquiring a write lock.
- Returns `None` in `find_stripe_association_preview()` or raises `AttemptConflict("Operation was never reserved.")` in `read_stripe_association_preview()` / `preview_associate_stripe_intent()` when the operation has not been reserved.

---

## 3. Validation Results

```text
python -m pytest tests/test_stripe_association.py tests/test_stripe_observation.py -q
49 passed, 124 subtests passed
```
