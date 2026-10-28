<!-- markdownlint-disable-file -->
# Stage 1665 research: explicit trusted endpoint secret overlap

## Scope, request and success criteria
Controller269 resumes 37b1e7e; actual start 2026-10-29 04:00 BJT.
Continue small offline bilingual assets, full/focused checks, compilation, exact-SHA
CI and non-force main publication. Preserve 1d9273d README/assets. Only23:00-06:00,
no new phase from05:30. No live Stripe endpoint, key management or account access.
Success: one trusted configuration snapshot can express overlap while original
single-secret verification, raw-body/time/header policy and durable receipt scope persist.

## Research executed and evidence
Bounded continuous trace inline; named Researcher Subagent is not configured.
- lab/stripe_delivery.py accepts one externally selected secret, parses all v1
  candidates and authenticates exact timestamp-dot-body bytes before time acceptance.
- tests/test_stripe_delivery.py already proves multiple header signatures against
  ONE secret. This already supports Stripe's overlap delivery; it is not broken.
- lab/stripe_inbox.py record always verifies before parsing or duplicate lookup,
  persists only scoped Event identity/type/reference/body digest, and never keys
  receipt identity by secret/signature. Keep that ordering and schema.
- tests/test_stripe_inbox.py already demonstrates re-signing with a different
  externally selected scalar secret is the same receipt, not a new business event.
- https://docs.stripe.com/webhooks, retrieved04:01 BJT, sections "Roll endpoint
  signing secrets periodically" and "Verify the signature": immediate expiry or
  delayed expiry up to24h, multiple active secrets, one signature per secret;
  endpoint/test/live secrets are separate; official libraries recommended.
- https://docs.stripe.com/events/manage-webhook-endpoints, retrieved04:01 BJT:
  confirms rolling semantics and says CLI-forwarded and Dashboard endpoint secrets
  differ. /webhooks/signature currently redirects to this management page.
- Official docs require exact raw bytes and describe duplicate Event handling.
  Their key-roll window is NOT delivery freshness tolerance or a replay TTL.

## Discovery and selected alternative
Additive local configuration extension, not a missing Stripe protocol requirement:
accept str OR a nonempty immutable tuple of nonblank strings in the same existing
verifier and inbox record entry point. Fully validate all configured entries before
any match, then accept any v1 matching any configured secret over the SAME bytes.
No exception-based loop over whole verification calls, no partial-config fallback,
no new facade/schema, secret IDs, selection from headers or duplicated HMAC parser.
All tuple entries must be currently active secrets for the SAME trusted endpoint,
account and mode; adapter/control plane owns that assertion and retirement.
No arbitrary secret-count cap or lifecycle/expiry inferred from request timestamp.
Duplicate configured values are harmless redundancy; do not invent a new policy.
Keep scalar behavior; tuple is a local API extension, not Stripe SDK compatibility.

## Scenarios, alternatives and risks
Cover either secret/order, several v1 values, foreign-only signatures, malformed
candidate even alongside a valid one, invalid trailing config even after a valid
key, empty/mutable/nested config, body changes and exact freshness bounds.
Post-retirement old-only delivery rejects even if duplicate Event already exists;
new-key re-signing dedups across restart/concurrency and does not create dispatch,
payment success, claim ownership or provider freshness. Secrets never persist.
Rejected: header-chosen key/account, global keyring, catching mismatch as fallback,
automatic24h expiry, broad SDK replacement, digest/receipt identities by key version.
Remote expiration does not remove a retained local secret. Publishing a fresh
configuration snapshot and deploying it to every verifier remains operator work.
No claim of constant total runtime across secret order; compare_digest protects
individual comparisons, not whole-keyring timing. No blocking question.

## Potential next research and handoff
Authenticated secret-distribution/retirement convergence is follow-up only; this
offline asset cannot verify external lifecycle state. Thin events, Connect and
organization contexts remain unsupported by the existing snapshot inbox.
No implementation during research. Self-check: scope, request, evidence,
discoveries, alternatives/scenarios, risks/open questions and follow-up checked.
Proceed /rpi-plan with this artifact; no model benchmark report is generated.
