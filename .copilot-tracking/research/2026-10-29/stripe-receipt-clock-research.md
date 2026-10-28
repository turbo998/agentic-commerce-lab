<!-- markdownlint-disable-file -->
# Stage 1669 research: opt-in post-lock Stripe receipt freshness

## Scope and request
Continuea8e908d at2026-10-29 05:01 BJT; nightly23:00-06:00, no new phase from05:30.
Preserve bilingual/full tests/compile/CI/non-force main and1d9273d README/assets.
Bound one optional receipt-admission extension; no live account/payment or scheduler.

## Evidence and discoveries
Bounded trace inline; named Researcher unavailable.
lab/stripe_inbox.py record currently authenticates raw bytes/fixed ingress now,
strictly parses duplicate-free snapshot JSON, then waits for BEGIN IMMEDIATE.
This is valid ingress-only semantics; post-lock freshness is not its guarantee.
Existing duplicate JSON hook already rejects ambiguity; no parser repair needed.
lab/stripe_delivery.py has canonical timestamp/HMAC and symmetric inclusive time
policy, strict integer clocks/positive tolerance, plus trusted secret overlap.
2026-10-29 05:03 BJT primary Stripe webhook docs reread:
https://docs.stripe.com/webhooks.md#preventing-replay-attacks
timestamp is signed, libraries default5min,0 disables recency, retries re-sign
with a new timestamp. Asynchronous queues and distinct Event-ID versus object/type
duplicates documented. None mandates this SQLite post-lock extension.
Web docs also distinguish thin/snapshot formats; keep this reference's two
PaymentIntent snapshot types only, no broad new-format support or release claim.
Visa/Sierra not newly checked in this stage.

## Selected alternative
Add required-clock record_with_clock: ingress clock -> existing raw HMAC/time/
snapshot checks outside write lock -> BEGIN -> second fresh clock using SAME
verified delivery timestamp/tolerance -> original receipt lookup/insert/commit.
Exactly TWO samples on successful/duplicate paths; unlike the signer gate's one
sample, these intentionally represent two boundaries. Early failures may take
only ingress sample; no HMAC or JSON parse repeated under writer lock.
Extract existing clock/time validation into shared private helpers, preserve old
verifier ordering and record(now=...) semantics. Both facades share original
receipt pipeline; old explicitly passes no admission callback.
No new schema/receipt fields/worker reset, record-time audit or secret state.
Rejected: stale fixed now masquerading as fresh, disabling time for preverification,
second HMAC/JSON under lock, rewriting old API, gating durable workers on delivery
expiry, switching to event.created or reauthenticating a rotated secret config.

## Scenarios, risk and follow-up
Actual blocked BEGIN crossing300->301 rejects before receipt reads/writes; exact
inclusive past/future boundaries and clock type/error propagate explicitly.
Duplicate still checks post-lock time and leaves receipt/claim untouched on failure.
New timestamp or active secret preserves Event identity. Old API may record after
queueing, deliberately retained and documented; require new facade on stronger routes.
Initial stale/future-invalid or HMAC/JSON/scope-invalid input never reaches DB.
Clock config is trusted/fresh at both calls, no monotonic-clock assumption.
Guarantee at second sample, not physical commit; no new nonce, secret retirement,
worker freshness, provider readback authority or payment outcome.
Commit/real-write rollback and durable claim/journal invariants required.
No blocker; potential ingress HTTP limits, remote clock/secret lifecycle and ACK
policy remain caller responsibilities.

## Self-check and handoff
Request/evidence/discoveries/alternatives/scenarios/risks/open gaps checked.
Research only so far; proceed /rpi-plan with this brief.
