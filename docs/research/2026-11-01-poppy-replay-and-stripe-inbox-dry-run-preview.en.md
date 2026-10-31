# Stage 1748: Lock-Free Single-`SELECT` Dry-Run Previews for Poppy Session Assertion Consumption and Stripe Inbox/Claim Transitions (`PoppyConsumptionPreview` / `InboxRecordPreview` / `ClaimTransitionPreview`)

> **Verification Date**: 2026-11-01 (Beijing Time `UTC+08:00`)  
> **Chinese Version（中文版）**: [`2026-11-01-poppy-replay-and-stripe-inbox-dry-run-preview.md`](2026-11-01-poppy-replay-and-stripe-inbox-dry-run-preview.md)  
> **Related Artifacts**: [`lab/poppy_replay.py`](../../lab/poppy_replay.py), [`lab/stripe_inbox.py`](../../lab/stripe_inbox.py), [`tests/test_poppy_replay_read.py`](../../tests/test_poppy_replay_read.py), [`tests/test_stripe_claim_read.py`](../../tests/test_stripe_claim_read.py)

---

## 1. Context & Architectural Problem

After adding lock-free single-`SELECT` dry-run previews across checkout execution, payment attempts, payment approvals, merchant signers, and Stripe readback acceptance in Stages 1744–1747, two remaining high-frequency ingress and coordination planes still lacked read-only dry-run primitives:

1. **Sierra Poppy v0.2 Session Assertion Replay Journal (`PoppyAssertionJournal`)**:
   - `find_assertion_consumption()` performs clock-independent historical auditing (`now=assertion.iat`), whereas `consume()` immediately burns the `jti` inside a `BEGIN IMMEDIATE` transaction. Operators and preflight guards had no non-consuming single-`SELECT` method to evaluate live temporal admission (`iat - 30 <= now < exp`) alongside replay state at a specific `now` timestamp.
2. **Stripe Webhook Inbox and Claim Coordination Plane (`StripeEventInbox`)**:
   - `read_receipt()`, `read_claim()`, and `find_provenance()` inspect stored rows by `event_id`, but could not dry-run raw webhook signature verification, JSON unique-key parsing, and `(event_type, provider_reference)` conflict checks without acquiring `BEGIN IMMEDIATE` in `record()`, nor preview `handoff()` and `finish_readback()` claim transitions.

---

## 2. AI-Native Architectural Design

### 2.1 `PoppyConsumptionPreview` and `PoppyAssertionJournal.preview_consume()`

In `lab/poppy_replay.py`, we added `PoppyConsumptionPreview` and `PoppyAssertionJournal.preview_consume(scope, assertion, *, now)`:

- **Pre-connection full validation**: Reuses `_validated_key(scope, assertion, now=now)` before opening SQLite to enforce `PoppyReplayScope`, `typ == "poppy-session+jwt"`, `iss == scope.client_id`, `aud == scope.auth_issuer`, `1 <= exp - iat <= 300`, `iat - 30 <= now < exp`, and 22–256 char base64url `jti` policy.
- **Single lock-free `SELECT`**: Calls `_lookup_consumed_key(scope, key)` against `poppy_assertion_replays` without `BEGIN IMMEDIATE`.
- **Structured projection**:
  - Unconsumed assertion: `existing_consumption=None`, `projected_consumption=PoppyConsumedAssertion(scope, jti_sha256)`, `would_consume=True` (`is_replay=False`).
  - Already consumed assertion: `existing_consumption=existing`, `projected_consumption=existing`, `would_consume=False` (`is_replay=True`).

### 2.2 `InboxRecordPreview`, `ClaimTransitionPreview`, and `StripeEventInbox` Dry-Run Previews

In `lab/stripe_inbox.py`, we factored `_parse_verified_event()` and added two immutable preview models and three lock-free methods:

1. **`InboxRecordPreview` and `StripeEventInbox.preview_record()`**:
   - Validates raw-byte HMAC delivery (`verify_stripe_delivery()`), strict UTF-8 unique-key JSON, boolean `livemode` parity, and `evt_` / `pi_` identifiers before opening SQLite.
   - Executes a single lock-free `FROM (SELECT 1) LEFT JOIN stripe_event_inbox i ... LEFT JOIN stripe_readback_claims c ...` query, failing closed on orphan readback claims or conflicting `(event_type, provider_reference)` bindings and returning `InboxRecordPreview` with `existing_receipt`, `existing_claim_status`, `decision`, `would_insert_receipt`, and `event_phase`.
2. **`ClaimTransitionPreview`, `preview_handoff()`, and `preview_finish_readback()`**:
   - Validates live claim ownership and generation in a single lock-free `SELECT` via `_current_claim(db, claim)`:
     - `preview_handoff(claim, worker_id)` requires an `"active"` claim with `generation < 2**63 - 1` and projects `generation + 1` (`would_write=True`).
     - `preview_finish_readback(claim)` projects `ReadbackClaimStatus(claim, "handled")` with `would_write=(existing_state == "active")`.

---

## 3. Validation Results

```text
python -m pytest tests/test_poppy_replay.py tests/test_poppy_replay_read.py tests/test_poppy_admission_clock.py tests/test_stripe_inbox.py tests/test_stripe_claim_read.py -q
102 passed, 231 subtests passed
```
