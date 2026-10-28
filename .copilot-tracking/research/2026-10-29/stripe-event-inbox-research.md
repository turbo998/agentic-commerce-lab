<!-- markdownlint-disable-file -->
# Stage 1655: durable event receipt is not business-effect deduplication

## Scope and request
Continue the existing night research from 0ad9a5d at 2026-10-29 00:26 BJT.
Preserve README.md, README.en.md and assets/ from 1d9273d. Deliver a small
offline asset, bilingual research, full validation and main synchronization.
Only work 23:00-06:00, no new phase from 05:30, no new automation/permissions.

## Research executed and evidence
Direct bounded source-to-code trace; kept inline under the direct-search
constraint rather than spawning a redundant researcher.
- https://docs.stripe.com/webhooks read at 00:27:
  retries can overlap manual resends; delivery is not ordered; event IDs identify
  duplicate deliveries; separate Event objects can concern the same object/type.
  Async processing and a prompt 2xx response are recommended. Do not equate ACK
  with business completion. No CLI/login/secret instructions were executed.
- https://docs.stripe.com/api/events/object read at 00:27:
  object=event, id, type, boolean livemode, data.object; account and context may
  route to connected/organization accounts. A narrow single-account policy must
  reject unsupported routing rather than trust metadata.
- https://www.sqlite.org/atomiccommit.html read at 00:29:
  local transactional atomicity depends on storage/flush assumptions. Tests can
  verify reopen/concurrency/error propagation, not certify real power-loss safety.
- lab/stripe_delivery.py: exact-byte signature verification, no event parsing or
  persistent dedup. lab/payment_attempts.py: BEGIN IMMEDIATE and independent
  payment authority/reconciliation; reuse that connection/transaction pattern,
  not its table or business outcome.
- Existing *pubsub2inbox* guard is a generated stage646 policy evaluator, not
  a SQLite Stripe event inbox. No existing reusable persistent inbox found.

## Discoveries and selected approach
Select a standard-library StripeEventInbox storing only minimal verified routing
metadata, first body digest and scoped event ID. Verify with Stage 1654 before
JSON parsing. Require unambiguous JSON objects, snapshot PaymentIntent shape,
matching boolean test/live mode, and own-account endpoint context.
Scope is trusted tenant + stable endpoint + provider account + mode, never taken
from request-selected metadata. Reject non-null account/context routing.
Limit event types to payment_intent.succeeded and payment_intent.payment_failed.
Neither type updates the payment journal.
Transactionally insert one receipt per scope/event ID. Retry signatures and
timestamps may differ, so neither is a dedup key. Repeated ID with changed
type/object reference conflicts. Different raw bytes with unchanged routing
identity return an explicit body_matches_first flag, not a second receipt.
Keep all receipts requiring readback; provide bounded local pending enumeration.
No processed/claim/worker state, ACK, network, consumer authority or fulfillment.

## Alternatives and risks
Rejected in-memory set (restart loses evidence), payload/signature hash as key
(resends/serialization split identities), object/type as global key (separate
events and business transitions), and updating payment state from a snapshot.
Rejected a full worker/outbox/distributed queue: larger scope and new guarantees.
Caller still owns endpoint-secret/account mapping, DB lifecycle/permissions,
ingress limits, SDK production integration, trusted initial payment association,
worker ownership/readback/completion, downstream economic idempotency and ACK.
Cross-endpoint receipts are separate; dedup is not global exactly-once behavior.
No new Visa/Sierra release verification; retain previous dated limitations.

## Handoff and artifact self-check
Scope, request, evidence, alternatives, risks and follow-on work checked.
No blocking research gap for this narrow local policy. No implementation in this
phase. Handoff to /rpi-plan using this artifact. Future work: durable worker
claim/completion with crash tests, Connect/organization context, and business
effect dedup under distinct Event IDs; these are not claimed features.
