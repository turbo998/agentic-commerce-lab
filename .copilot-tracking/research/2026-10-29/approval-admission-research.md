<!-- markdownlint-disable-file -->
# Stage 1661 research: approval revocation and reservation share a transaction

## Scope and request
Controller 269 resumes from 238aa8c at 03:01 BJT; actual start 03:03.
Keep bilingual/full tests/CI/non-force main, 1d9273d README/assets, permissions/model.
23:00-06:00 only; no new phase from 05:30. Research the explicit Stage 1660 gap
between a trusted approval check and the durable first-dispatch reservation.

## Dated evidence and prior art
Research 03:03-03:06 BJT, bounded continuous trace inline; configured Researcher
Subagent absent.
- https://sierra.ai/blog/poppy rechecked: customers choose access, companies set
  parameters, and a flight example confirms with the customer before booking.
  Account/session access is not a universal payment approval.
- Official personal-agent-protocol repository HEAD still
  a95b757872533a6ef1e1a9bcf29802857d2e5ff4 (2026-10-26). Pinned versions.json records
  0.2 published 2026-10-24; 0.3 has no published field. No new release inferred.
- https://docs.stripe.com/agents/how-it-works.md distinguishes developer tools,
  Billing and agentic commerce; MCP integration tools do not independently handle
  billing/commerce. Tool access must not be interpreted as purchase authority.
- https://www.sqlite.org/lang_transaction.html: one writer; BEGIN IMMEDIATE starts
  a write transaction, nested BEGIN transactions are unsupported.
- lab/checkout.py CheckoutStore already validates local approvals/expiry/revocation
  against simulated receipts, but its global mandate ID and receipt-consumption
  schema do not encode tenant-scoped PaymentOperation/provider/idempotency binding.
- lab/payment_attempts.py reserve owns durable one-dispatch identity, but consent/
  expiry/revocation are external. Extract a transaction participant, preserving API.
- lab/stripe_readback.py already uses strict same-resolved-file and transaction
  participants. Reuse that co-location policy, not nested public transactions.
- lab/checkout_admission.py already binds strict signed JSON to trusted Checkout.
  Extract pure validation, retaining its original facade/behavior.
- Targeted actual class/sqlite import/CREATE TABLE search found no separate durable
  approval store among legacy approval/consent/mandate modules. Historical Boolean
  guard simulations and benchmark reports remain unchanged.

## Selected bounded asset
New PaymentApprovalStore in lab/payment_approvals.py, same local SQLite file as
payment journal. Trusted operator approve records tenant/approval/fingerprint/
expires_at/revoked only. No raw JWT/body/customer/payment token. Approval records are
immutable, never reactivated/extended/deleted via this API; revoke is idempotent.
Fingerprint binds the full existing PaymentOperation, not just price or buyer text.
admit first reuses pure signed-checkout validation, then under BEGIN IMMEDIATE checks
exact approval fingerprint, revocation and expiry before existing journal reservation.
A required trusted clock callback is sampled after the write lock is acquired.
Exact expiry (now >= expires_at) rejects. Every use of this new facade, even a
non-dispatch retry, requires a valid approval; journal.read remains available for
recovery after revocation/expiry. Old facades remain opt-in compatibility paths.

## Alternatives, limits and scenarios
Rejected: check-then-reserve on separate connections, stale clock sampled before lock
wait, nested reserve transactions, changing/recreating approvals on retry, global
mandates as tenant/provider authority and treating Poppy/Stripe access as consent.
Race semantics: revocation committed first blocks reservation; reservation committed
first is not undone by later revocation. No promise to cancel already-committed or
remote sends, authenticate approval operators, provide a consent UI, prove legal
consent, synchronize physical clocks or enforce distributed revocation.
Direct journal/SQL writes bypass this opt-in boundary. No blocking evidence gap.

## Validation and handoff self-check
Test exact expiry/revocation/scopes/fingerprint, same-file requirement, post-lock
clock sampling, concurrent admission/revoke orders, immutable approvals, real process
persistence, failure after insert/before commit and failed approve/revoke commits.
Full legacy checkout/journal/atomic-readback regressions, full suite, compilation,
demos, executable bilingual examples, links/protected paths and final CI/canonical.
Checked scope/request, dated evidence/prior art, alternatives/scenarios, open risks
and handoff. Proceed /rpi-plan with this research; no implementation in research.
