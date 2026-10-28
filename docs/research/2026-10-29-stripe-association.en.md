# Stage 1663: Validate the first PaymentIntent before persisting its association

[中文](2026-10-29-stripe-association.md) |
[Daily record](../../research/daily/2026-10-29.en.md) |
[Previous increment](2026-10-29-admission-provenance.en.md)

**Finding:** persisting an initial PaymentIntent ID before checking its complete
readback can poison recovery with a wrong account, mode or quote. Validate against
a **separately trusted operation-to-reference mapping** before writing that first
association. A matching amount or metadata cannot establish this mapping.
**Association is not new dispatch, consumer consent or a terminal payment result.**

Resumed from `df5f6b5` at 03:35 Asia/Shanghai on 2026-10-29; sources checked
03:35–03:37. Two controllers requested the same stage, handled as one existing
worktree task; canonical synchronization remains with controller 269.
23:00–06:00 only, no new phase from 05:30; README/SVG unchanged.
`provenance=synthetic`, `independently_reproduced=false`: offline engineering fixtures,
not model benchmarks, live payments or Stripe SDK/interoperability certification.

## 1. Provider IDs need a trusted origin, not a plausible explanation

| Rechecked primary source | Architecture implication |
|---|---|
| [PaymentIntent retrieval](https://docs.stripe.com/api/payment_intents/retrieve) | Retrieve by ID; publishable-key/client-secret retrieval returns only a subset. Missing fields are not safe defaults in this strict policy |
| [Payment Intents overview](https://docs.stripe.com/payments/payment-intents) | Persist ID on the cart/session, reuse interrupted intents and apply creation idempotency; amounts alone do not identify an operation |
| [Metadata](https://docs.stripe.com/metadata) | Metadata is mutable and generally not used to authorize/decline charges, with the documented Radar exception; it cannot authenticate local operation association |

Current Stripe guidance recommends Checkout Sessions for most new integrations.
This increment hardens the existing offline PaymentIntent recovery lab; it does not
recommend a new PaymentIntent integration or provision a sandbox. No API keys,
real requests or client secrets are needed.
No new Visa/Sierra protocol release was checked. TAP identity, Poppy access and
local approval/provenance remain independent from provider-object association.

## 2. Small opt-in gate, shared validation and transaction participants

[`associate_stripe_intent`](../../lab/stripe_observation.py) accepts:

- The existing journal and immutable trusted `PaymentOperation`.
- `retrieved_account` from authenticated provider context.
- A separately trusted `expected_reference`, correlated by the adapter's
  authenticated create/result path or durable operation mapping.
- A complete trusted PaymentIntent readback, not an Event or model-authored JSON.

The function **cannot authenticate these inputs or discover the correct mapping**.
Never derive `expected_reference` from an Event, free text, matching amount or
request-controlled metadata. The `pi_[A-Za-z0-9_]+` grammar is narrow local policy,
not a provider authentication mechanism.

Inside one `BEGIN IMMEDIATE` transaction:

1. Find the exact already-reserved operation; never reserve or create authority.
2. Reuse existing `validate_stripe_intent` against a transient
   `PaymentAttempt("unknown", expected_reference)`, without first storing that ID.
3. Validate account/provider test-live mode, ID/object type, exact full amount/
   currency, typed amount_received, status and explicit direct-account routing.
4. Reject a different persisted reference. Same-reference retries return the
   existing state without downgrading terminal outcomes.
5. Bind only an unassociated `unknown` attempt through the existing transaction
   participant with `observation="pending"`; commit before returning.

Even a valid `succeeded` or zero-received `canceled` snapshot only establishes the
reference here; the first result remains `unknown`. A separate explicit
[`reconcile_stripe_intent`](../../lab/stripe_observation.py) or fenced
[`accept_stripe_readback`](../../lab/stripe_readback.py) performs outcome acceptance.
The discarded validation result is intentional: this API's contract is association,
not reconciliation. Same-reference retry does not reconcile a new snapshot either.

Changed operation fingerprints and unassociated terminal state reject. The existing
provider/account/reference uniqueness rule prevents association with another operation;
test/live and different accounts remain separate namespaces.
Insert/update/commit errors propagate, with no success-shaped fallback.
No schema, generic journal or existing reconciliation contract changes.
Old direct `journal.reconcile(..., observation="pending")` remains a compatibility
bypass, not silently upgraded semantic validation.

## 3. Runnable synthetic failure, association and separate reconciliation

The expected reference is an explicit trusted fixture, **not inferred from intent**.
Provider retrieval/authentication/freshness are not implemented.

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from lab.checkout import Checkout
from lab.payment_attempts import PaymentAttemptJournal, PaymentOperation
from lab.stripe_observation import (
    StripeObservationError, associate_stripe_intent, reconcile_stripe_intent,
)

operation = PaymentOperation(
    "tenant", "operation", "approval", "stripe:test", "acct_synthetic", "key",
    Checkout("synthetic-shop", "USD", "synthetic-sku", 2, 1000),
)
trusted_reference = "pi_synthetic"
intent = {
    "object": "payment_intent", "id": "pi_synthetic", "livemode": False,
    "amount": 1000, "amount_received": 1000, "currency": "usd",
    "status": "succeeded", "transfer_data": None, "on_behalf_of": None,
}
with TemporaryDirectory() as directory:
    journal = PaymentAttemptJournal(Path(directory) / "commerce.sqlite3")
    journal.reserve(operation)
    context = dict(retrieved_account="acct_synthetic",
                   expected_reference=trusted_reference)
    try:
        associate_stripe_intent(journal, operation, intent={**intent, "amount": 999},
                               **context)
    except StripeObservationError:
        pass
    else:
        raise AssertionError("wrong quote must not establish first association")
    assert journal.read(operation).provider_reference is None
    bound = associate_stripe_intent(journal, operation, intent=intent, **context)
    assert bound.provider_reference == trusted_reference and bound.outcome == "unknown"
    assert not journal.reserve(operation).dispatch_allowed
    final = reconcile_stripe_intent(
        journal, operation, retrieved_account="acct_synthetic", intent=intent,
    )
    assert final.outcome == "succeeded"
    assert associate_stripe_intent(journal, operation, intent=intent, **context) == final
```

## 4. AI-native design: plausible correlation is not authority

Well-Architected describes quality/trade-offs, not the Web three-tier topology.
Trusted foreign-reference association and transactional checks are established
techniques. AI-native workloads add planners that may select a plausible
PaymentIntent from a webhook, amount or explanatory metadata and then treat it as
authoritative recovery history. Put correlation provenance and semantic checks
before the first state write, not in instructions to an agent after persistence.

This gate cannot prevent a trusted adapter from supplying a wrong but plausible
expected reference. Authentication, durable create-result correlation, freshness,
coherent database backups and caller access remain deployment responsibilities.
It does not require active approval to recover an already-reserved attempt, and
does not manufacture Stage 1662 admission history. No new approval, dispatch,
Connect/organization routing, partial payments, refunds or settlement guarantee.

## 5. Validation scope

[`tests/test_stripe_association.py`](../../tests/test_stripe_association.py)
adds 29 methods; 148 focused tests pass with existing observation/journal/
atomic-readback/approval/provenance regressions. Coverage includes strict complete
fields before first write, explicit context and reference, total-not-unit-price,
mode/account isolation, missing reservation, one-reference-per-operation and
one-operation-per-account/reference, concurrent same/competing references,
fresh process, terminal preservation, secret exclusion and real post-update/
commit rollback. No nested public reconciliation connection is used.
All 4,022 repository tests, compilation, both existing demos, 103 local links and
two identical executable bilingual examples passed. Eight generated historical
reports were restored; no report content is staged. Protected README/assets have
zero diff from `1d9273d`. Final-SHA CI/canonical synchronization remain
post-publication gates, not evidence of live provider effects.
