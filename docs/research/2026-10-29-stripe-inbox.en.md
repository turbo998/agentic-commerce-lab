# Stage 1655: One durable receipt is not one economic side effect

[中文](2026-10-29-stripe-inbox.md) | [Daily research](../../research/daily/2026-10-29.en.md) |
[Stage 1654 verification](2026-10-29-stripe-delivery.en.md)

**Verified 2026-10-29, Asia/Shanghai, starting 00:27; baseline `0ad9a5d`.**
This is a `synthetic` offline engineering asset, not a model benchmark, Stripe
SDK, production queue or live payment integration. New primary evidence is
Stripe/SQLite-specific; no new Visa or Sierra release is asserted.

## 1. Delivery, Event and business operation have different identities

[Stripe Webhooks](https://docs.stripe.com/webhooks#event-delivery-behaviours)
documents live-mode automatic retries for up to three days, manual resends
overlapping automatic retries, and no guaranteed delivery order. `created`
cannot reliably determine processing or event order; distinct events can share
a second. [Duplicate handling guidance](https://docs.stripe.com/webhooks#handle-duplicate-events)
distinguishes repeated delivery of an Event from distinct Events concerning
the same `data.object` and `event.type`.

| Identity | Local purpose | Not a substitute for |
|---|---|---|
| Delivery signature and timestamp | Authenticate exact bytes within a time window | Event ID, payment operation or consumer authority |
| Trusted configured scope plus Event ID | Persistent receipt dedup in one endpoint context | Globally processed work or cross-endpoint/cross-Event economic dedup |
| Payment operation/approval and existing provider association | Independent journal and authoritative readback boundary | Ownership inferred from incoming event JSON |

The [Event object](https://docs.stripe.com/api/events/object) includes `id`,
`object=event`, `type`, `livemode`, `data.object`, and potentially Connect
`account` or organization `context`. These are meaningful routing boundaries.
Current documentation recommends thin events for most new integrations. This
reference intentionally handles a narrow snapshot slice, not a production
recommendation or full SDK-compatible schema. Observation dates are not releases.

## 2. The new asset persists readback hints only

[`lab/stripe_inbox.py`](../../lab/stripe_inbox.py) verifies with Stage 1654
before parsing UTF-8 JSON. Duplicate JSON keys, malformed JSON, mode mismatch,
unsupported types and routing reject explicitly, not via success-shaped defaults.
Only `payment_intent.succeeded` and `payment_intent.payment_failed` are accepted;
the nested object must be a same-mode `payment_intent` with a `pi_` reference.
This validates routing fields, not complete Event/PaymentIntent schemas or
business terminality.

Trusted `StripeInboxScope` supplies tenant, stable endpoint, provider account
and mode from configuration. **Requests, metadata and models must not select
scope or secret.** This implementation does not authenticate that configuration.
All non-null `account`/`context` values reject; Connect/organization events are
never silently downgraded.

A SQLite compound primary key combines scope and Event ID; `BEGIN IMMEDIATE`
serializes the check/insert transaction, committed before return. Store only
minimal routing metadata and the first body SHA-256, never the full event,
endpoint secret, `client_secret` or metadata. `synchronous=FULL` is explicit,
but [SQLite atomic commit](https://www.sqlite.org/atomiccommit.html) still
depends on filesystem/device flush assumptions. Reopen and injected-failure
tests are not power-loss certification or distributed transactions.

An existing Event ID cannot change type/object binding. Different raw bytes
return an explicit `body_matches_first=False`, preserving the first digest
without inserting another row. This is difference evidence, **not proof that
all payload semantics are equivalent or a claim that Stripe always changes
redelivery bytes**. New signatures, timestamps or rotated secrets do not create
new Event identity; duplicates must still authenticate again. Every receipt
retains `requires_readback=True`.
In particular, `payment_intent.payment_failed` does not terminally fail the
entire Intent; [Stage 1653's trusted readback/binding gate](2026-10-28-stripe-observation.en.md)
remains separate.

`pending(scope, limit=100)` enumerates hints in local receipt order, with limits
from 1 to 1000. There is no worker claim, processed flag, completion or deletion
API. Repeated enumeration can return the same rows: this is not a dequeue/lease
or a guarantee against duplicate processing.

## 3. Runnable synthetic receipt example

```python
import hashlib
import hmac
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from lab.stripe_inbox import StripeEventInbox, StripeInboxScope

secret = "synthetic-only-inbox-secret"
body = json.dumps({
    "id": "evt_synthetic", "object": "event", "livemode": False,
    "type": "payment_intent.succeeded",
    "data": {"object": {"id": "pi_synthetic", "object": "payment_intent", "livemode": False}},
}).encode()
digest = hmac.new(secret.encode(), b"1700000000." + body, hashlib.sha256).hexdigest()
header = f"t=1700000000,v1={digest}"
scope = StripeInboxScope("tenant", "endpoint", "acct_synthetic", False)
with TemporaryDirectory() as directory:
    inbox = StripeEventInbox(Path(directory) / "inbox.sqlite3")
    first = inbox.record(scope, body, header, secret, now=1700000000)
    repeat = inbox.record(scope, body, header, secret, now=1700000000)
    assert first.first_seen and not repeat.first_seen
    assert len(inbox.pending(scope)) == 1
    assert repeat.receipt.requires_readback
```

Secret and clock are synthetic inputs. Production must not copy a frozen clock
or let requests select secrets. All 83 focused tests passed, including 21 new
methods covering a fresh Python process, concurrency, resigning, scope isolation, routing/
identity conflicts, commit-failure rollback, sensitive-field exclusion, and
integration assertions that payment `unknown` remains unchanged.
All 3,808 repository tests, compilation and both existing offline demos passed.

```powershell
python -m unittest tests.test_stripe_inbox tests.test_stripe_delivery tests.test_stripe_observation tests.test_payment_attempts tests.test_checkout -q
```

## 4. Architectural conclusion and remaining boundaries

Durable receipt and prompt ACK can separate complex processing, but this asset
implements no HTTP endpoint or ACK. Receipt is not completion. Real deployments
still need worker ownership, retry/completion state, retention, trusted initial
payment association, provider readback and independent business-effect
idempotency. Different endpoint/tenant scopes get separate receipts; this is
not cross-endpoint exactly-once behavior. Digests/object IDs are not automatically
safe public log data.

Inboxes, idempotent ledgers and out-of-order events are not uniquely AI problems:
mature payment/event-driven systems already need them. AI-native design adds
the constraint that a variable planner can propose actions but cannot reconstruct
consumer authority, claim an unknown object or fill unknown outcomes during
replanning/repeated notifications. These are deterministic specializations of
Well-Architected reliability, not a mandate for more agents or slogans against
modular monoliths or three-tier applications.
