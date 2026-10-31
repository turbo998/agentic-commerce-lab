# Stage 1736: Single-Snapshot Stripe Readback Provenance Inspector & Cross-Table Reference Parity

> **Date**: 2026-11-01 (`UTC+08:00`)  
> **Stage**: Stage 1736  
> **Core Modules**: `lab/stripe_readback.py`, `lab/stripe_inbox.py`, `lab/stripe_observation.py`, `tests/test_stripe_readback_provenance.py`  
> **中文版**: [`2026-11-01-stripe-readback-provenance.md`](2026-11-01-stripe-readback-provenance.md)

---

## 1. Problem Statement & Architectural Gap

When `StripeEventInbox` and `PaymentAttemptJournal` share a canonical SQLite database, `accept_stripe_readback()` atomically updates `payment_attempts` and marks the `stripe_readback_claims` row as `'handled'`. Because `accept_stripe_readback()` rejects any retry once a claim is `'handled'` (including retries after a lost local response), recovery controllers and reconciliation auditors need a way to inspect the coupled local state of `(inbox, journal, scope, event_id, operation)` without mutating state or issuing remote Stripe calls.

Prior to Stage 1736, three gaps existed:

1. **No Single-Snapshot Cross-Table Provenance Reader Across `payment_attempts`, `stripe_event_inbox`, and `stripe_readback_claims`**:
   - Calling `journal.read_attempt(operation)`, `inbox.read_receipt(scope, event_id)`, and `inbox.read_claim(scope, event_id)` separately opened three independent SQLite connections and could observe torn state under concurrent `claim_next()`, `handoff()`, `associate_stripe_intent()`, or `accept_stripe_readback()` execution.
2. **Separate Readers Could Not Detect Cross-Table `PaymentIntent` Drift or Scope/File Mismatch**:
   - Individual readers did not verify that `inbox.path` and `journal.path` resolve to the same canonical SQLite file, nor that `scope` (`tenant_id`, `provider_account`, `livemode`) matches `operation` (`tenant_id`, `provider_account`, `provider`);
   - If `payment_attempts.provider_reference` (`pi_a`) differed from `stripe_event_inbox.provider_reference` (`pi_b`), each single-table reader succeeded independently instead of failing closed on the conflicting `PaymentIntent` binding.
3. **Pre-Connection Argument Type Guards in `StripeEventInbox` and `stripe_observation`**:
   - `StripeEventInbox.handoff()` and `finish_readback()` opened a SQLite connection and executed `BEGIN IMMEDIATE` before `_current_claim()` verified `isinstance(claim, ReadbackClaim)`.
   - `reconcile_stripe_intent()` and `validate_stripe_intent()` dereferenced `operation`, `journal`, or `previous` before checking their types.

---

## 2. AI-Native Architectural Improvements

### 2.1 `StripeReadbackProvenance` and Three-Table Single-Snapshot Inspection

We added the frozen `StripeReadbackProvenance` dataclass along with `find_stripe_readback_provenance(inbox, journal, scope, event_id, operation)` and `read_stripe_readback_provenance(inbox, journal, scope, event_id, operation)` in `lab/stripe_readback.py`:

```sql
SELECT
    att.fingerprint AS att_fingerprint,
    att.approval_id AS att_approval_id,
    att.provider AS att_provider,
    att.provider_account AS att_provider_account,
    att.idempotency_key AS att_idempotency_key,
    att.outcome AS att_outcome,
    att.provider_reference AS att_provider_reference,
    i.event_id AS i_event_id,
    i.event_type AS i_event_type,
    i.provider_reference AS i_provider_reference,
    i.payload_sha256 AS i_payload_sha256,
    c.event_id AS c_event_id,
    c.worker_id AS c_worker_id,
    c.generation AS c_generation,
    c.state AS c_state
FROM (SELECT 1)
LEFT JOIN payment_attempts att
    ON att.tenant_id=? AND att.operation_id=?
LEFT JOIN stripe_event_inbox i
    ON i.tenant_id=? AND i.endpoint_id=?
    AND i.provider_account=? AND i.livemode=? AND i.event_id=?
LEFT JOIN stripe_readback_claims c
    ON c.tenant_id=? AND c.endpoint_id=?
    AND c.provider_account=? AND c.livemode=? AND c.event_id=?
```

- Returns `None` (`find_stripe_readback_provenance`) or raises `StripeReadbackError` (`read_stripe_readback_provenance`) only when neither the payment attempt nor the webhook receipt exists.
- Supports all valid asynchronous orderings: webhook recorded/claimed before operation reservation (`attempt=None`), operation reserved/associated before webhook arrival (`receipt=None`), unassociated attempt alongside recorded receipt (`attempt.provider_reference=None`), and associated/accepted attempt alongside active or handled claims (`attempt.provider_reference == receipt.provider_reference`).
- Fails closed on conflicting `PaymentIntent` references (`attempt.provider_reference != receipt.provider_reference`), orphan `stripe_readback_claims` rows, 10-dimension operation binding drift, corrupted receipt/claim/attempt columns, scope-vs-operation mismatch, or separate SQLite files.

### 2.2 Pre-Connection Type Guards

- `StripeEventInbox.handoff()` and `finish_readback()` now validate `isinstance(claim, ReadbackClaim)` before opening a SQLite connection or acquiring a `BEGIN IMMEDIATE` write lock.
- `reconcile_stripe_intent()` and `validate_stripe_intent()` validate `journal`, `operation`, `previous`, and `retrieved_account` types up front.

---

## 3. Verification

- New unit test suite: `tests/test_stripe_readback_provenance.py` (`4 passed, 71 subtests passed`).
- Combined Stripe regression suites: `220 passed, 477 subtests passed`.
- Full repository test suite: `4337 passed, 1515 subtests passed`.
