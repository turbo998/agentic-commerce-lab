<!-- markdownlint-disable-file -->
# Stage 1656 research: fence local hint completion, not external payment effects

## Scope and request
Continue cac1ae6 at 2026-10-29 01:01 BJT. Preserve user README.md,
README.en.md and assets/ from 1d9273d; bilingual assets, full tests and main/CI/
canonical synchronization. Work only 23:00-06:00, no new phase after 05:30.
No new permissions, automation, dependencies, real payment or model evaluation.

## Research executed and evidence
Direct bounded trace, inline under the direct-search constraint; no redundant
researcher delegation.
- https://aws.amazon.com/builders-library/leader-election-in-distributed-systems/
  read 01:04; redirects to
  https://builder.aws.com/content/3Ev0vH0hfkcUizISUWYTvHibtcp/leader-election-in-distributed-systems
  Article dated 2019-12-05, not a new release. Explains pauses/clock/leadership
  overlap, durable work before completion notification, idempotency, and a
  preference for tested clients rather than bespoke distributed leader election.
  Uses local elapsed duration rather than synchronized wall clocks.
- https://sqlite.org/isolation.html read 01:04: writes serialize; independent
  connections see committed transactions, not partial changes. BEGIN IMMEDIATE
  is appropriate for the existing local database pattern, not remote fencing.
- https://docs.stripe.com/webhooks read 01:04: automatic/manual retries overlap,
  order is not guaranteed, async processing recommended. Receipt identity alone
  does not specify worker ownership or downstream effect idempotency.
- lab/stripe_inbox.py: stable scoped receipt identity, _connect/_receipt helpers,
  no ownership/handled state. pending() is an immutable receipt enumeration,
  not a dequeue. Existing tests assert this boundary.

## Discoveries and selected approach
Select explicit generational claims/handoff for local readback hints. Do NOT
implement timed leases: this narrow reference cannot certify distributed clock/
pause behavior. A trusted controller decides recovery; a transaction checks the
old generation and increments it before handing off. Old completions reject.
Add an additive claim table in the same SQLite file, preserving receipt schema,
dedup, pending() behavior and all payment-journal semantics.
Provide claim_next, active_claims, handoff and finish_readback. Each claim binds
scope, receipt, worker ID and positive generation. Same-worker handoff also
increments generation (ABA protection). Completion is idempotent for the same
current handle; handled work cannot be resurrected by handoff/redelivery.
No available work returns None as an explicit normal control state. Invalid
input, stale handles, exhausted generations and storage failures raise.
Keep receipt.requires_readback=True: handling a hint is not a payment fact.

## Alternatives and risks
Rejected wall-clock auto-expiry/heartbeats, volatile worker flags, destructive
receipt removal, snapshot-driven reconciliation and automatic downstream writes.
Fencing only protects the local claim table. An old worker may still be running
or reading the provider; no remote side effect is stopped. Worker IDs/generation
handles are coordination metadata, not authentication or consumer authority.
No end-to-end worker, readback verifier, polling scheduler, HTTP ACK, renewal,
automatic recovery or distributed exactly-once protocol. Caller owns worker
authentication, actual bound readback, recovery policy and business idempotency.
DB history must be retained; backup rollback/reset is outside this generation
contract. SQLite filesystem/flush assumptions remain operational.
No new Visa/Sierra evidence: retain previous dated conclusions.

## Handoff and artifact self-check
Scope, request, evidence, alternatives, risks and follow-on work checked.
No blocking gap for explicit local ownership fencing; no implementation in this
research phase. Handoff to /rpi-plan using this artifact. Future research:
production queue/lease clients, distributed readback result acceptance,
transactional business effects and recovery policy, with separate invariants.
