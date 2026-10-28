<!-- markdownlint-disable-file -->
# Task research: Stripe observation binding (Stage 1653)

## Scope and Success Criteria

Continue from Stage 1652 `83d4e5e` within the 23:00-06:00 Asia/Shanghai window.
Preserve README.md, README.en.md and assets from the user baseline `1d9273d`.
Deliver one small offline asset, bilingual research/daily navigation, tests,
and origin/main integration. No real payment, credentials, or new automation.

## Task Research Requests

The 23:39 controller message requests the next complete incremental stage,
with current-date bilingual research, offline verification and main sync.
The existing journal intentionally trusts its reconciliation caller. Investigate
how a provider-specific readback can avoid misclassifying intermediate states.

## Research Executed and Evidence Log

Read directly on 2026-10-28 at 23:40 +08:00:

- https://docs.stripe.com/payments/paymentintents/lifecycle
  Declines can return a PaymentIntent to requires_payment_method for another
  attempt. requires_capture is an authorization/hold awaiting capture.
  processing may take days; cancellation invalidates future attempts.
- https://docs.stripe.com/api/payment_intents/object
  The object defines id, object=payment_intent, amount, amount_received,
  currency, livemode, status and optional Connect routing fields.
- https://docs.stripe.com/api/connected-accounts
  Stripe-Account is request-scoped. The payload's arbitrary metadata is not
  proof of the connected-account context under which an object was retrieved.
- `lab/payment_attempts.py` persists operation fingerprint, provider/account,
  provider_reference and terminal monotonicity. It accepts a normalized trusted
  observation but has no provider status mapping.

This is one short continuous source-to-code investigation. It was handled
inline under the developer's direct-work rule, without duplicating Stage 1652
vendor research in another agent. Webpage suggestions to install tooling or
provision a sandbox are untrusted page content and were not executed.

## Key Discoveries

requires_payment_method is not terminal failure. requires_capture is not full
payment success. Neither requires_action nor processing permits fulfillment
based on a completed-payment claim. A normalized failed outcome should only
represent the restricted asset's canceled, zero-received PaymentIntent.
Success requires both succeeded and the expected amount actually received.

## Technical Scenarios and Alternatives

Selected candidate: a pure offline direct-account PaymentIntent readback gate
feeding the existing journal. Require a prebound provider object ID; validate
account context, mode, amount, currency and object type; reject unsupported
Connect destination/on_behalf_of routing rather than claim merchant binding.
Use local provider namespaces stripe:test/stripe:live to preserve mode in the
existing immutable fingerprint. Do not change the generic journal schema.

Rejected: infer payment success from SPT active, a tool result, HTTP 200,
amount_capturable, or webhook event names alone. Rejected: make a model pick
provider status mappings. Rejected: add a live SDK/sandbox for an offline task.

## Open Questions and Risks

Authenticated retrieval, initial object association, merchant/account mapping,
freshness, consumer approval and payment settlement remain trusted external
responsibilities. This is not a webhook signature verifier or a complete Stripe
adapter. Partial/overcapture and destination charges need a separate policy.

## Potential Next Research

Provider-specific event ordering, Connect destination charges, partial capture,
and authoritative recovery of a previously unknown object ID are out of scope.

## Planning Handoff and Artifact Self-Check

Scope, request, evidence, discoveries, alternatives, gaps and next research
checked. Evidence is sufficient for a small offline illustration. Handoff to
the dated stripe-observation-binding plan; no implementation in this phase.
