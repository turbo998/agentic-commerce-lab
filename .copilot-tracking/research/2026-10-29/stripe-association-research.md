<!-- markdownlint-disable-file -->
# Stage 1663 research: validate first PaymentIntent binding before persisting it

## Scope and request
Controllers 278/269 requested the same Stage 1663 from df5f6b5; merge into one
existing-worktree task, no extra writer. Actual start 03:35 BJT.
Preserve bilingual/full tests/compile/CI/non-force main, 1d9273d README/assets.
23:00-06:00 only, no new phase from 05:30; canonical sync remains controller269.

## Research executed and dated evidence
03:35-03:37 BJT, bounded continuous trace inline; named Researcher Subagent absent.
- lab/stripe_observation.py validates context, quote, mode, routing and state
  only after a trusted PaymentIntent association is already persisted.
- tests/test_stripe_observation.py deliberately uses manual pending reconciliation
  to establish that ID first. A wrong quote/account snapshot must not poison this
  initial association before validation. Current validator can be reused with a
  transient expected-reference PaymentAttempt without persisting it.
- lab/payment_attempts.py provides _find, _attempt and _reconcile_in_transaction,
  uniqueness per provider/account/reference, immutable operation fingerprint and
  monotonic outcomes. Reuse its same-connection participant.
- lab/stripe_readback.py already uses BEGIN IMMEDIATE for bound state updates;
  lab/stripe_inbox.py uses a narrow pi_[A-Za-z0-9_]+ local ID grammar.
- https://docs.stripe.com/api/payment_intents/retrieve: retrieval by ID; publishable
  key/client_secret returns only a subset. This strict full-readback policy rejects
  missing fields instead of treating absent routing/mode/amount as safe defaults.
- https://docs.stripe.com/payments/payment-intents: store PI ID on cart/session,
  reuse interrupted PI and use creation idempotency. Current docs recommend
  Checkout Sessions for most new integrations; this asset only hardens the
  existing offline PI recovery lab, not a recommendation to build a new PI flow.
- https://docs.stripe.com/metadata: metadata is mutable and generally not used
  to authorize/decline charges (Radar usage exception). Free-text metadata cannot
  authenticate the initial operation-to-PI association.
No sandbox provisioning, SDK installation, keys, HTTP payment calls or external
instructions from fetched documentation are authorized by this research.

## Selected bounded asset and alternatives
Add associate_stripe_intent to existing observation module. Require a separately
trusted expected_reference correlated by the authenticated adapter's create/result
or durable mapping, never an Event/model-selected ID. Matching amount is necessary,
not sufficient to prove association.
Inside BEGIN IMMEDIATE: find the exact reserved operation, validate a transient
expected-reference view using the existing complete readback validator, reject
changed reference, then set a previously unassociated unknown attempt to pending/
unknown via existing transaction participant. Never infer payment success here.
Same-reference retries return existing state without downgrading terminal outcomes.
Reject missing reservation, conflicting references and unassociated terminal state.
Rejected: persist ID then validate, infer by amount/metadata/webhook, close outcome
on first binding, or introduce another transport/approval layer. No legacy API change.

## Risks, scenarios and open questions
Authentication, provider freshness and operation-to-expected-reference correlation
remain explicit adapter responsibilities; function cannot prove them from JSON.
No new reservation, consent, dispatch, refund/settlement or provider call. Connect/
organization/partial amount remain unsupported. Existing journal facade can bypass
this opt-in semantic gate. Database integrity/coherent backups remain trusted.
Concurrent same binding is idempotent; competing references have one winner;
same provider/account/reference cannot bind another operation. No blocking question.
Future authenticated create-result provenance and Checkout Sessions adapters deferred.

## Handoff and artifact self-check
Test bad fields before first write, explicit context/reference, all existing status
policies, exact amounts/no coercion, no metadata authority, no success inference,
idempotent/terminal retry, uniqueness/races, fresh process and commit rollback.
Preserve old reconciliation APIs; full tests/compile/demos, bilingual examples/
links/protected paths and final CI/canonical receipt gate release.
Checked scope/request, dated evidence/prior art, alternatives/scenarios, risks/
open questions and handoff. No implementation in research. Proceed /rpi-plan.
