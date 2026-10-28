<!-- markdownlint-disable-file -->
# Stage 1670: scoped historical receipt lookup

## Scope and evidence
Started 05:17 BJT from c7ff2d2, last research stage before05:30.
Stripe webhooks.md fetched05:18; its verification section explicitly requires
origin verification before actions; async guidance separates receipt/work.
https://docs.stripe.com/webhooks#verify-events-are-sent-from-stripe
This does not prescribe a local SQLite reader or grant ACK/payment permission.
Workspace:stripe_inbox.py pending() enumerates bounded scoped receipts; no direct
reader. _receipt already reconstructs original immutable receipt. Existing
payment_approvals.read_admission/merchant_signers.read_timed_admission establish
historical-read versus current-authority separation.

## Selected bounded approach
Add read_receipt(scope,event_id): full trusted scope plus canonical Event ID;
one SELECT using every existing identity dimension, None for expected absence.
Reuse _receipt, no write lock/clock/HMAC/JSON/schema/claim effects. Return original
hash even after differently serialized duplicate. Local DB remains trusted.
Missing or found history cannot substitute for ingress verification or authorise
readback, ACK or economic actions. Error on invalid scope/ID/storage errors.

## Alternatives and risks
Do not scan pending(limit=1000): bounded enumeration cannot prove absence.
Do not coalesce different Event IDs/object IDs or add freshness to history.
Do not add transport routes, live provider calls, nonce/payment authority.
Simple/medium continuous trace handled inline: named Researcher unavailable;
no duplicate exploration agent needed. No material unresolved product decision.
Public pair/daily/index, focused/full/compile/demos/links/examples/protection,
non-force main, exact-SHA CI and canonical receipt required.
Handoff:rpi-plan; preserve old APIs and user README/assets; no Stage1671.
