# Stage 1670: five-dimensional receipt lookup exceeds the 1,000-row enumeration limit

[中文](2026-10-29-stripe-receipt-read.md) |
[Asset](../../lab/stripe_inbox.py) |
[Tests](../../tests/test_stripe_receipt_read.py) |
[Prior delivery-time boundary](2026-10-29-stripe-receipt-clock.en.md)

## Finding and evidence

`pending(limit=1000)` is bounded enumeration, not a specific Event existence query.
New `read_receipt(scope, event_id)` queries original history by the five-part key:
tenant, endpoint, provider account, live/test mode and Event ID.
A 1,001-row local fixture demonstrates lookup beyond the first page; it does not
represent 1,001 actual deliveries.

Rechecked 2026-10-29 05:18 BJT: Stripe's [origin verification guidance](https://docs.stripe.com/webhooks#verify-events-are-sent-from-stripe)
and [asynchronous handling](https://docs.stripe.com/webhooks#handle-events-asynchronously).
Stripe requires origin verification before actions and recommends queue-based
decoupling. This neither supplies nor mandates a local SQLite reader.
This is local engineering, not a new product release. Visa/Sierra were not rechecked.

## Historical reads are not current delivery admission

| Path | Fact and boundary |
|---|---|
| `record_with_clock` | Validates current raw bytes/HMAC/time/JSON, rechecks time after the lock, then receives/deduplicates. |
| `read_receipt` | Validates trusted scope/canonical Event ID, then one SELECT of original history, without request authentication. |
| `pending` | Retains bounded receipt-order enumeration regardless of claim state. |
| `claim_next` / `finish_readback` | Existing local coordination, not payment results; reading history never reopens handled work. |

Presence returns the original frozen `InboxReceipt`, including first payload hash
and `requires_readback=True`. Reserialized duplicates keep the first hash.
Different Event IDs referencing the same PaymentIntent remain distinct.
Absence returns `None`, not payment failure or proof of nonpayment. Invalid
scope/ID errors are explicit; database failures never masquerade as absence.

No writer transaction, clock, HMAC, JSON, new schema or claim/payment writes.
“Read-only” describes method behavior, not OS/database access control. The local
database and caller-provided scope remain trusted; no tamper protection,
independent cryptographic evidence or HTTP authentication is added.
History proves neither current signature freshness nor ACK, worker or payment
authority. HTTP adapters must never look up an unauthenticated Event ID and use
its existence to skip delivery verification, or use this reader as a fallback
after `record_with_clock` rejects a delivery.

## Executable synthetic example

Only temporary local SQLite and a synthetic secret, without Stripe or payments.

```python
import hashlib
import hmac
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from lab.stripe_inbox import StripeEventInbox, StripeInboxScope

now = 1700000000
secret = "synthetic-only-receipt-reader"
body = json.dumps({
    "id": "evt_read", "object": "event", "livemode": False,
    "type": "payment_intent.succeeded",
    "data": {"object": {
        "id": "pi_read", "object": "payment_intent", "livemode": False,
    }},
}).encode()
digest = hmac.new(secret.encode(), str(now).encode() + b"." + body, hashlib.sha256).hexdigest()
signature = f"t={now},v1={digest}"
times = iter((now, now + 1))

with TemporaryDirectory() as directory:
    inbox = StripeEventInbox(Path(directory) / "inbox.sqlite3")
    scope = StripeInboxScope("tenant", "endpoint", "acct_synthetic", False)
    assert inbox.read_receipt(scope, "evt_read") is None
    receipt = inbox.record_with_clock(
        scope, body, signature, secret, clock=lambda: next(times),
    ).receipt
    claim = inbox.claim_next(scope, "synthetic-worker")
    inbox.finish_readback(claim)
    assert StripeEventInbox(inbox.path).read_receipt(scope, "evt_read") == receipt
    assert inbox.claim_next(scope, "another-worker") is None
    other = StripeInboxScope("another-tenant", "endpoint", "acct_synthetic", False)
    assert inbox.read_receipt(other, "evt_read") is None
    assert receipt.requires_readback
    print("Original scoped history survives handled work without reopening or payment authority.")
```

## AI Native architecture implications and validation

Cloud Well-Architected and three-tier observability remain useful, but Agent
execution needs explicit separation of historical facts, current admission and
executable authority. Queryability must not extend authority; enumeration
omissions are not absence proofs; handled work is not payment success. This
refines the execution fact model rather than replacing reliability, authentication
or provider reconciliation with architecture terminology.

Fifteen new methods cover five-dimensional isolation, absence/reopen, first hash,
distinct Events for one object, active/handled preservation, strict IDs, database
errors, single-SELECT SQL traces, beyond-page lookup and stale delivery rejection.
All 199 Stripe-focused and 4,204 integrated tests, compilation, both demos,
157 local links and two identical executable bilingual examples pass. An initial
fixture connection-close error on Windows was fixed with explicit closing and
rerun successfully. Eight content-changed generated reports were restored; two
normalization-only file states were refreshed, without report commits.
Final-SHA CI/canonical synchronization are post-publication gates. No production
credentials, network payments or model benchmark.
