# Stage 1731 — `StripeEventInbox` Persisted Receipt & Readback Claim Integrity Validation (`InboxReceipt` / `InboxDecision` Hardening)

> **中文对应版**: [2026-11-01-stripe-receipt-integrity.md](2026-11-01-stripe-receipt-integrity.md)  
> **Verification Date (Beijing Time)**: `2026-11-01` (Window `00:35–00:46+08:00`)  
> **Related Assets**: [`lab/stripe_inbox.py`](../../lab/stripe_inbox.py) · [`tests/test_stripe_receipt_integrity.py`](../../tests/test_stripe_receipt_integrity.py)

---

## 1. Background & Problem Statement

Within the Stripe webhook ingress and readback coordination pipeline (`StripeEventInbox`), value objects such as `StripeInboxScope`, `ReadbackClaim`, `ReadbackClaimStatus`, `StripeSecretWindow`, and `StripeWebhookSecretRing` enforced fail-closed domain invariants at construction time via `__post_init__`. However, four persistence-hydration and cross-table integrity gaps remained:

1. **Missing construction-time invariants on `InboxReceipt` and `InboxDecision`**: `StripeEventInbox._receipt(row)` hydrated `event_id`, `event_type`, `provider_reference`, and `payload_sha256` from `stripe_event_inbox` without validating their column formats, allowing corrupted SQLite rows to be returned as malformed `InboxReceipt` instances across `read_receipt()`, `pending()`, `claim_next()`, `read_claim()`, and `active_claims()`.
2. **Write-before-hydration ordering in `claim_next()`**: `claim_next()` previously executed `INSERT INTO stripe_readback_claims` before calling `self._receipt(row)`; validating `receipt = self._receipt(row)` first avoids issuing an `INSERT` when the persisted receipt row is malformed.
3. **Orphan claim rows masked by `INNER JOIN`**: Because `stripe_readback_claims` does not enforce SQLite foreign-key cascading against `stripe_event_inbox`, an orphan claim row whose parent receipt row was missing was silently masked as `None` by `read_claim()` or skipped by `active_claims()`.
4. **Corrupted `state` column overwritten by `finish_readback()`**: If `stripe_readback_claims.state` was corrupted outside `('active', 'handled')`, `_finish_in_transaction()` checked only `if row["state"] == "handled": return` and otherwise overwrote the corrupted state with `'handled'`.

---

## 2. Dialectical Architecture Analysis: Classic 3-Tier Web Apps vs. AI-Native Agentic Commerce

| Architectural Dimension | Classic 3-Tier Web App / ORM | AI-Native Agentic Commerce (Stage 1731) |
|---|---|---|
| **ORM / Value-Object Hydration Boundary** | Trusts local database rows implicitly; validates payloads only at HTTP ingress and maps database columns directly into domain objects. | Enforces zero-trust storage hydration: `InboxReceipt.__post_init__` and `InboxDecision.__post_init__` validate `evt_` IDs, allowed `PaymentIntent` event types, `pi_` object references, 64-hex lowercase SHA-256 digests, and strict `bool` flags on both direct construction and SQLite row hydration. |
| **Cross-Table `JOIN` Semantics** | Uses `INNER JOIN` between parent and child coordination tables, treating missing parent rows as benign "not found (`None`)". | Queries `FROM stripe_readback_claims c LEFT JOIN stripe_event_inbox i` (with `ORDER BY i.rowid, c.rowid` so `NULL` parent rowids surface first in SQLite), raising `StripeInboxError` immediately whenever an orphan claim row lacks a persisted inbox receipt. |
| **Terminal State Transitions (`finish_readback`)** | Implements idempotency as `if state != 'done': UPDATE state = 'done'`, laundering corrupted intermediate states into terminal completion. | Verifies `row["state"] in ("active", "handled")` inside `_current_claim()` so neither `finish_readback()` nor `accept_stripe_readback()` can overwrite a corrupted claim state. |

---

## 3. Implementation Details (`lab/stripe_inbox.py`)

1. **`InboxReceipt.__post_init__` and `InboxDecision.__post_init__`**:
   - Validates `event_id` against `r"evt_[A-Za-z0-9_]+"`.
   - Validates `event_type` in `("payment_intent.succeeded", "payment_intent.payment_failed")`.
   - Validates `provider_reference` against `r"pi_[A-Za-z0-9_]+"`.
   - Validates `payload_sha256` against `r"[0-9a-f]{64}"`.
   - Validates `requires_readback`, `first_seen`, and `body_matches_first` with strict `type(...) is bool`.
2. **Hydrate-before-insert in `claim_next()`**:
   - Calls `receipt = self._receipt(row)` before executing `INSERT INTO stripe_readback_claims`.
3. **Orphan-claim detection in `read_claim()` and `active_claims()`**:
   - Uses `FROM stripe_readback_claims c LEFT JOIN stripe_event_inbox i USING(tenant_id,endpoint_id,provider_account,livemode,event_id)` so any claim row missing its parent inbox receipt triggers `StripeInboxError` during `self._receipt(row)`.
4. **Strict state check in `_current_claim()`**:
   - Rejects any stored claim row where `row["state"] not in ("active", "handled")` with `StripeInboxError`.

---

## 4. Verification & Regression Results

Added 5 unit tests (with 63 subtests) in [`tests/test_stripe_receipt_integrity.py`](../../tests/test_stripe_receipt_integrity.py):

- `test_inbox_receipt_and_decision_validate_invariants`: Verifies rejection of malformed types, prefixes, digests, and non-boolean flags on `InboxReceipt` and `InboxDecision`.
- `test_corrupted_persisted_receipt_columns_fail_closed_before_claim_or_read`: Verifies that corrupting any column in `stripe_event_inbox` causes `read_receipt()`, duplicate `record()`, `pending()`, and `claim_next()` to raise `StripeInboxError` without inserting a claim row.
- `test_corrupted_persisted_receipt_rejects_claim_reads_handoff_and_completion`: Verifies that corrupting a claimed receipt row causes `read_claim()`, `active_claims()`, `handoff()`, `finish_readback()`, and `accept_stripe_readback()` to fail closed while preserving `PaymentAttempt("unknown", "pi_synthetic")`.
- `test_orphan_claim_without_inbox_receipt_fails_closed`: Verifies that deleting a claimed receipt row from `stripe_event_inbox` causes `read_claim()`, `active_claims(limit=1)`, `handoff()`, and `finish_readback()` to raise `StripeInboxError` while leaving sibling valid claims readable.
- `test_corrupted_claim_state_is_not_overwritten_by_finish_or_readback`: Verifies that a corrupted `stripe_readback_claims.state` value is rejected and preserved rather than overwritten by `finish_readback()` or `accept_stripe_readback()`.

### Regression Results
- `python -m pytest tests/test_stripe_receipt_integrity.py tests/test_stripe_inbox.py tests/test_stripe_receipt_read.py tests/test_stripe_claim_read.py tests/test_stripe_readback.py tests/test_stripe_atomic_readback.py tests/test_stripe_receipt_clock.py tests/test_stripe_secret_rotation.py -q`: `155 passed, 261 subtests passed`.
