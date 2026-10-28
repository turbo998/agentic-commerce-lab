# Stage 1669: Stripe receipt time is checked at ingress and after the writer lock

[中文](2026-10-29-stripe-receipt-clock.md) |
[Inbox asset](../../lab/stripe_inbox.py) |
[Shared time policy](../../lab/stripe_delivery.py) |
[Tests](../../tests/test_stripe_receipt_clock.py) |
[Original receipt boundary](2026-10-29-stripe-inbox.en.md)

## Finding and primary evidence

A delivery valid at ingress can exceed receiver time policy while waiting for a
SQLite writer. Optional `record_with_clock(..., clock=...)` performs full ingress
verification/parsing, then rechecks the **same authenticated delivery timestamp**
after acquiring the lock, before receipt lookup/insertion.
This is extra local receipt-admission policy, **not a repair of Stripe's protocol
or the existing ingress API**.

Rechecked 2026-10-29 05:03 BJT: Stripe's [raw-body verification guidance](https://docs.stripe.com/webhooks#webhook-endpoint-def),
[replay-time guidance](https://docs.stripe.com/webhooks#preventing-replay-attacks),
[asynchronous handling](https://docs.stripe.com/webhooks#handle-events-asynchronously)
and [duplicate Events](https://docs.stripe.com/webhooks#handle-duplicate-events):

- The delivery timestamp is signed and cannot be changed without invalidating
  the signature. Libraries default to five minutes; `0` disables recency.
  Existing local policy rejects zero and requires positive integer tolerance
  with symmetric inclusive past/future bounds, not full SDK compatibility.
- Stripe generates a new signature/timestamp for each delivery retry. A new
  delivery of an old Event can pass again. **JSON `event.created` is not the
  signed-header timestamp.**
- Stripe recommends asynchronous handling and quick `2xx` responses. Receipt
  dedup and business dedup of different Events are distinct.
  It does not mandate this database post-lock check or reapply delivery expiry
  to already durable worker tasks.

Only current Stripe documentation is checked, not a new release on this retrieval
date. Visa/Sierra were not rechecked. The reference keeps its two PaymentIntent
snapshot types; documentation covering thin events does not broaden this asset.

## Small asset: two time boundaries, one cryptographic/JSON pass

Successful/valid-duplicate new paths explicitly sample **twice**, not once:

1. After trusted scope/callable checks, an ingress sample feeds the original raw
   HMAC, header, secret configuration, time and strict snapshot-JSON validation.
   Failure never connects to storage.
2. After `BEGIN IMMEDIATE` actually acquires the writer lock, a second fresh
   sample reuses the time policy: `abs(now - signed_timestamp) <= tolerance`.
   It also requires a strict nonnegative signed64 integer clock.
3. The second check precedes receipt dedup. An expired duplicate cannot bypass it
   because its Event ID was already received. Passing input reuses original
   identity/conflict/hash/INSERT/commit behavior.

HMAC and JSON are not repeated under the writer lock; one verification pass can
still try multiple active keys. Duplicate-key/NaN rejection
already existed; this is not a JSON parser repair. No schema, receipt fields,
time-audit row or claim reset is introduced. Missing/non-callable/throwing/invalid
clocks never downgrade to fixed-now admission. The callback must return fresh time
at each call; a wall clock is not assumed to be monotonic.

Original `record(..., now=...)` **retains fixed-now ingress semantics**, without
a post-lock recheck. Routes needing stronger receipt admission must use the new
facade and never fall back on error. This differs from the
[timed signer's one post-lock sample](2026-10-29-merchant-signature-time.en.md):
that gate shares one decision sample; here arrival and durable admission are
intentionally separate boundaries.

| Scenario | Bounded local result |
|---|---|
| Valid ingress; post-lock difference exactly `±300` with default configuration | Inclusive boundary permits original receipt/dedup flow. |
| Valid ingress; difference becomes `±301` after waiting | Reject before receipt lookup/insertion. |
| Initially stale or invalid HMAC/JSON/scope | No writer transaction; no waiting for time to become acceptable. |
| Re-signed same Event with fresh timestamp/active secret | Same scoped Event identity, without receipt/claim reset. |
| Durable task later exceeds delivery window | This API does not expire work or grant worker/payment authority. |

## Executable synthetic example

Only offline test signatures and a logical clock are constructed. No Stripe
connection, endpoint creation or payment is performed.

```python
import hashlib
import hmac
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from lab.stripe_delivery import StripeDeliveryError
from lab.stripe_inbox import StripeEventInbox, StripeInboxScope

start = 1700000000
secret = "synthetic-only-receipt-secret"
body = json.dumps({
    "id": "evt_synthetic", "object": "event", "livemode": False,
    "type": "payment_intent.succeeded", "created": start,
    "data": {"object": {
        "id": "pi_synthetic", "object": "payment_intent", "livemode": False,
    }},
}).encode()
times = iter([start, start + 1, start + 299, start + 301, start + 400, start + 401])
samples = []

def clock():
    value = next(times)
    samples.append(value)
    return value

def signature(timestamp):
    digest = hmac.new(
        secret.encode(), str(timestamp).encode() + b"." + body, hashlib.sha256,
    ).hexdigest()
    return f"t={timestamp},v1={digest}"

with TemporaryDirectory() as directory:
    inbox = StripeEventInbox(Path(directory) / "inbox.sqlite3")
    scope = StripeInboxScope("tenant", "endpoint", "acct_synthetic", False)
    first = inbox.record_with_clock(scope, body, signature(start), secret, clock=clock)
    assert first.first_seen and first.receipt.requires_readback
    try:
        inbox.record_with_clock(scope, body, signature(start), secret, clock=clock)
    except StripeDeliveryError as error:
        assert "tolerance" in str(error)
    else:
        raise AssertionError("Queued stale duplicate was admitted.")
    duplicate = inbox.record_with_clock(scope, body, signature(start + 400), secret, clock=clock)
    assert not duplicate.first_seen and duplicate.receipt == first.receipt
    assert inbox.pending(scope) == (first.receipt,)
    assert samples == [start, start + 1, start + 299, start + 301, start + 400, start + 401]
    print("Queued stale duplicate rejected; fresh retry keeps the original readback hint.")
```

## Architecture implications and remaining gaps

Classic three-tier separation and cloud Well-Architected reliability remain useful,
but “authenticated at ingress” and “policy still holds at durable admission”
are different facts. Agentic Commerce execution needs explicit policy
linearization points and existing-fact lifecycles, not one economic-success label
for an Event, receipt, handled worker or provider status.

The guarantee is at the second sample, not physical commit/send time. Resampling
does not refresh the trusted secret tuple used at ingress or detect remote
retirement while waiting. It does not authenticate workers, consume nonces or
change unknown Stripe readback/journal state. `event.created` remains irrelevant
to freshness. Callers own clock synchronization, HTTP/queue/backpressure,
endpoint/account/mode secret configuration and ACK/retry policy. Stricter receipt
windows can increase rejection/retry cost and must not delay webhook ACKs or
incorrectly discard already received work.

## Validation

All **184** Stripe-focused tests pass, including **30** new methods. SQL traces
observe actual blocked `BEGIN IMMEDIATE`; logical time crosses exact thresholds,
without sleeping five real minutes. Coverage includes two-sample ordering, one
HMAC/JSON pass, duplicate/claim preservation, re-signing/rotation, old paths,
zero epoch/signed64 maximum, concurrency/reopen, real write/commit rollback and
unchanged unknown payments. All **4,189** integrated tests, compilation, both
offline demos, 167 local links and two identical executable bilingual examples
pass; ten generated historical reports were restored. Final-SHA CI/canonical
synchronization are separate post-publication gates. These are synthetic
engineering tests, not a model benchmark.
