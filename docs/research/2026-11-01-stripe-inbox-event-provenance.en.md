# Stage 1740: Stripe Webhook Inbox Single-Snapshot Event Provenance (`InboxEventProvenance` & `StripeEventInbox.find_provenance` / `read_provenance`)

> 中文版: [2026-11-01-stripe-inbox-event-provenance.md](2026-11-01-stripe-inbox-event-provenance.md)

## Executive Summary

Within the Agentic Commerce Stripe asynchronous webhook ingestion and readback-claim (`StripeEventInbox`) pipeline, operational triage and worker rebalancing frequently need to inspect the coupled receipt and claim lifecycle of a scoped `(scope, event_id)` directly at the inbox tier (before or without binding a `PaymentOperation` / `PaymentAttemptJournal`):

1. **Torn Reads and Ambiguous `None` Across Two-Step Reads**: Calling `inbox.read_claim(scope, event_id)` alone returns `None` both when `event_id` was never received (`unreceived`) and when it was verified and persisted but awaits a worker (`unclaimed`). Calling `read_receipt(scope, event_id)` at $T_1$ followed by `read_claim(scope, event_id)` at $T_2$ opens two separate connections across which a concurrent worker can run `claim_next()`, `handoff()`, or `finish_readback()`, and fails to surface an explicit orphan-claim diagnostic if the `stripe_event_inbox` parent row was removed under `PRAGMA foreign_keys = OFF`.
2. **Strict Integer Generation Guard in `_current_claim()`**: `_current_claim()` now explicitly checks `type(row["generation"]) is not int` and `isinstance(row["state"], str)` before `handoff()` or `finish_readback()`.

Stage 1740 introduces `InboxEventPhase` (`"unclaimed" | "active" | "handled"`), the frozen `InboxEventProvenance` dataclass, and single-snapshot read methods `StripeEventInbox.find_provenance()` and `StripeEventInbox.read_provenance()` in `lab/stripe_inbox.py`.

---

## Architecture Comparison: Classic Two-Step Inbox Lookup vs. AI-Native Single-Snapshot Event Provenance

| Dimension | Classic Two-Step Inbox Lookup (`read_receipt` + `read_claim`) | Agentic Commerce Single-Snapshot Event Provenance (`InboxEventProvenance`) |
|---|---|---|
| Disambiguating `unreceived` vs. `unclaimed` | `read_claim()` returns `None` for both; requires a second query | Single query projects both `i_event_id` and `c_event_id`, distinguishing `None` (`unreceived`) from `phase == "unclaimed"` |
| Consistency under concurrent worker transitions | Separate $T_1$ and $T_2$ connections can observe torn state | Single `SELECT ... FROM (SELECT 1) LEFT JOIN ...` executes in one lock-free SQLite snapshot |
| Orphan claim row detection | `read_receipt()` returns `None` while `read_claim()` fails with a generic receipt field error | Explicitly detects `i_event_id IS NULL AND c_event_id IS NOT NULL` and raises `"Orphan readback claim exists without an inbox receipt."` |
| Cross-object binding invariants | Caller manually pairs `(scope, receipt, claim_status)` | `InboxEventProvenance.__post_init__` enforces `claim_status.claim.scope == scope` and `claim_status.claim.receipt == receipt` |

---

## Core Invariants & State Matrix

| `stripe_event_inbox` (`i`) | `stripe_readback_claims` (`c`) | `find_provenance()` Return | `read_provenance()` Behavior | `provenance.phase` |
|---|---|---|---|---|
| Absent (`NULL`) | Absent (`NULL`) | `None` | Raises `StripeInboxError("No inbox receipt exists...")` | — |
| Absent (`NULL`) | Present (`NOT NULL`) | Raises `StripeInboxError("Orphan readback claim...")` | Raises `StripeInboxError("Orphan readback claim...")` | — |
| Present (`NOT NULL`) | Absent (`NULL`) | `InboxEventProvenance(scope, receipt, None)` | Same as left | `"unclaimed"` |
| Present (`NOT NULL`) | Present (`state='active'`) | `InboxEventProvenance(scope, receipt, status)` | Same as left | `"active"` |
| Present (`NOT NULL`) | Present (`state='handled'`) | `InboxEventProvenance(scope, receipt, status)` | Same as left | `"handled"` |

---

## Verification

- `python -m pytest tests/test_stripe_claim_read.py tests/test_stripe_inbox.py tests/test_stripe_readback.py -q`: `57 passed, 91 subtests passed`.
