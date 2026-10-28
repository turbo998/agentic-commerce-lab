<!-- markdownlint-disable-file -->
# Stage 1657: atomic local readback acceptance

Observed BJT: 2026-10-29 01:36-01:41, within the authorized window.
Baseline: e95d106. Existing README/SVG paths remain protected.

## Evidence
- https://sqlite.org/lang_transaction.html (retrieved 2026-10-29):
  one simultaneous writer; BEGIN IMMEDIATE acquires the write transaction;
  nested BEGIN is not supported; connection snapshots and commit failures matter.
- https://docs.stripe.com/events/how-events-work (retrieved 2026-10-29):
  snapshots can be outdated when processed; latest resource retrieval is separate;
  thin events are recommended for new integrations. This asset remains a deliberately
  narrow snapshot-receipt slice, not a new Stripe SDK recommendation.
- Existing journal reconciliation owns a separate connection and transaction.
  Calling it inside an inbox write transaction cannot implement atomic acceptance.
- Existing finish_readback fences only its local marker. A business write performed
  before that check can already have happened under a stale generation.
- Existing observation validation, immutable journal bindings and monotonic
  outcomes must be reused, not replaced with Event.type inference.

## Selected boundary
Require the same resolved SQLite file path, one connection and BEGIN IMMEDIATE.
Validate the persisted active claim before any payment update; bind tenant,
account, mode and the already-associated PaymentIntent; reuse readback validation;
reconcile and mark handled in that transaction. Return only after commit.
Reject different canonical paths (including distinct hard-link names), rather
than advertising cross-file or distributed atomicity. Filesystem namespace,
workers and retrieval remain trusted configuration/integration responsibilities.

Extract transaction participants from existing journal/completion methods and
extract pure observation validation. Keep standalone APIs and their semantics.
Already-handled acceptance rejects: finish_readback alone does not prove that
payment reconciliation happened. Lost-response recovery inspects persisted state.
Pending observation can handle the hint while payment remains unknown; this is
not a provider-finality assertion or permission to dispatch again.

## Rejected alternatives and validation
- Separate commits with compensation leave the exact stale-write/partial-state gap.
- ATTACH, remote calls inside the write lock, leases and new result-receipt tables
  expand scope without establishing provider freshness or remote atomicity.
- Use exact rollback assertions after a payment SQL update but before marker
  completion, commit-failure injection, stale-owner rejection and concurrent
  handoff/acceptance. Retain all standalone regression coverage.
- Local transaction consistency is established infrastructure, not an AI invention.
  AI-native design must put this gate on the actual economic state-write path,
  rather than trusting planner sequencing or ownership checks after the effect.

No live provider access, consumer authorization, model benchmark, new automation,
remote-effect fencing, power-loss certification or distributed-transaction claim.
