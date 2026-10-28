<!-- markdownlint-disable-file -->
# Stage 1662 research: first approval admission is not a later approval lookup

## Scope and request
Controller 269 resumes ef44ddf for Stage 1662; actual start 03:22 BJT.
Preserve permissions/model, bilingual archives, full tests/CI/non-force main and
1d9273d README/assets. Only 23:00-06:00, no new phase from 05:30.
Investigate durable provenance of the existing first-dispatch admission, not
consumer-consent authentication, cryptographic receipts or actual payments.

## Research executed and dated evidence
03:22-03:24 BJT, bounded continuous trace inline: the named Researcher Subagent
is not configured; no independent exploration/delegation is needed.
- lab/payment_approvals.py: admission checks approval and reserves atomically,
  but retains no historical record of this gate. A later valid approval cannot
  distinguish a historical direct journal reservation from an approved admission.
- lab/payment_attempts.py: the full-operation fingerprint and single dispatch
  already exist; reuse them. Unknown remains recoverable and retries never send.
- lab/checkout.py Receipt and lab/stripe_inbox.py InboxReceipt are different facts,
  not a persisted record of the approval gate's first reservation.
- lab/poppy_replay.py consumes a Session assertion for its own protocol boundary.
  Do not couple token-exchange replay to a purchase or call it purchase consent.
- https://docs.stripe.com/api/idempotent_requests rechecked: API v1 saves first
  response after execution starts, including 500; keys can be pruned after at least
  24h and reuse after pruning creates a new request. V2 has different behavior.
  Provider idempotency is not permanent local approval history.
- https://docs.stripe.com/agents/how-it-works.md rechecked: developer tools,
  billing and commerce are separate components; tool access is not purchase authority.
- https://sierra.ai/blog/poppy rechecked: customers choose access, businesses set
  parameters, and the flight example confirms before booking. No new release claim.
- https://www.sqlite.org/lang_transaction.html rechecked: one writer, explicit
  transaction commit/rollback and no nested BEGIN. Record provenance on the same
  connection as first reservation, not best-effort logging after return.

## Key discovery and selected approach
Extend the opt-in PaymentApprovalStore with an immutable-by-API first-admission
record: tenant/operation key, full operation fingerprint, post-lock sampled time
and approval expiry. Insert only when this gate creates the first reservation,
inside its existing transaction. No receipt is synthesized for pre-existing
standalone/older reservations or for a non-dispatch retry.
Expose a frozen read model and independent read_admission(operation) that works
after revocation/expiry without checking current approval or granting dispatch.
Missing historical record is an explicit error, not a success-shaped empty receipt.
This proves only a local gate record under a trusted database/application, not
who approved, legal consent, signature verification, remote send/result or finality.

## Alternatives and scenarios
Rejected: reconstruct history from current approval, log after commit, backfill
legacy reservations, treat a provider key as permanent approval, bind Poppy
Session exchange to payments, or change old journal/facade authority contracts.
Separate audit ledger/service adds unneeded two-phase coordination here.
First admission creates reservation+record together; commit failure returns no
decision and leaves neither. Retry/reconciliation/revoke preserve original record.
Existing databases add an empty table with no invented history.

## Risks, open gaps and potential follow-up
Trusted local database/coherent backups remain assumptions. No tamper evidence,
append-only external ledger, authenticated approver, receipt signing, retention/
deletion service, clock truth or commit/send deadline guarantee. Direct SQL can
alter records; do not describe them as cryptographic proof. No blocking question.
Future authenticated approval provenance/distributed recovery is out of scope.

## Validation and planning handoff
Test exact record shape, full binding/scopes, first time/expiry immutability,
legacy non-backfill, restart/fresh process, revoke/expiry/reconcile recovery,
concurrent one-first-record, rollback after both writes and failed commit.
Preserve existing 34 approval tests plus journal/checkout compatibility; full suite,
compile/demos, executable bilingual examples, links/protected paths and CI/canonical.
Artifact self-check: scope/request, dated evidence, discoveries, alternatives,
scenarios, risks/open questions and handoff checked. No implementation in research.
Proceed /rpi-plan with this artifact and bounded selected approach.
