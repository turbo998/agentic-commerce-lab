# Stage 1657: One local transaction fences payment updates before marking readback handled

[中文](2026-10-29-stripe-atomic-readback.md) | [Daily research](../../research/daily/2026-10-29.en.md) |
[Previous ownership boundary](2026-10-29-stripe-readback.en.md)

**Verified 2026-10-29, Asia/Shanghai, starting 01:36; baseline `e95d106`.**
`synthetic` offline engineering reference, not a model benchmark or production
payment integration. No new Visa/Sierra release verification was performed.

## 1. Receipt ownership must be checked before the business write

Stage 1656 rejects a stale generation when finishing a local hint, but cannot undo
a payment write performed before that check. Two independently committed methods
leave both a stale-writer gap and a crash window between payment and hint state.

[SQLite transaction documentation](https://sqlite.org/lang_transaction.html)
supports one simultaneous writer and explicit `BEGIN IMMEDIATE`; nested `BEGIN`
is not supported. Calling the public journal reconciler inside an inbox write
transaction opens another connection, not a nested shared transaction.
[Stripe event documentation](https://docs.stripe.com/events/how-events-work)
states that snapshots may be outdated when processed. Binding a signed subject
is different from accepting a latest readback; Event.type is not the final result.
Thin events are recommended for new integrations; this snapshot slice deliberately
does not claim to implement that broader integration.

## 2. A deliberately co-located, opt-in acceptance path

[`accept_stripe_readback`](../../lab/stripe_readback.py) requires the same resolved
SQLite file pathname for inbox and journal. Different files and distinct hard-link
names reject. Trusted filesystem configuration is assumed; this is not protection
against malicious path swaps, database tampering or rolled-back backups.

One connection, one immediate transaction:

1. Validate the persisted scope/receipt/worker/generation and require `active`.
2. Match tenant, account and test/live namespace against the immutable operation.
3. Read the reserved attempt on that connection; require its pre-existing trusted
   PaymentIntent association to match the receipt. An event cannot create it.
4. Reuse the readback validator for account, object/ID, mode, amount, currency,
   direct-account routing and status. Reuse journal conflict/monotonicity checks.
5. Update the journal and mark the hint handled; return only after commit.

No network operation occurs under the write lock. Handoff and acceptance serialize:
if handoff wins, the old generation cannot update payment state; if acceptance
wins, that handled claim cannot be handed off. A write/commit failure propagates
and rolls back both local changes. This is a local database property, not a promise
of exactly-once provider effects, settlement or power-loss safety.

`pending` readback may commit `handled` while the payment remains `unknown`:
the hint was examined, not the payment finalized. It grants no new dispatch.
A failed-attempt Event can lead to a currently succeeded Intent; a historical
success Event does not override a currently canceled Intent.

Already-handled acceptance **rejects**, even for the same handle. Standalone
`finish_readback()` is still idempotent and only writes a marker, so it cannot
prove that a coupled payment update occurred. After a lost acceptance response,
inspect persisted journal/claim state; this API has no transparent result replay.

## 3. Executable synthetic example

Run from the repository root; no credentials, provider request or model call:

```python
import hashlib
import hmac
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from lab.checkout import Checkout
from lab.payment_attempts import PaymentAttemptJournal, PaymentOperation
from lab.stripe_inbox import StripeEventInbox, StripeInboxScope
from lab.stripe_readback import accept_stripe_readback

with TemporaryDirectory() as directory:
    path = Path(directory) / "commerce.sqlite3"
    inbox, journal = StripeEventInbox(path), PaymentAttemptJournal(path)
    scope = StripeInboxScope("tenant", "endpoint", "acct_synthetic", False)
    operation = PaymentOperation(
        "tenant", "operation", "approval", "stripe:test", "acct_synthetic", "key",
        Checkout("synthetic-shop", "USD", "synthetic-sku", 1, 1000),
    )
    journal.reserve(operation)
    journal.reconcile(operation, observation="pending", provider_reference="pi_synthetic")
    now, secret = 1700000000, "synthetic-only"
    body = json.dumps({
        "id": "evt_synthetic", "object": "event", "livemode": False,
        "type": "payment_intent.succeeded",
        "data": {"object": {
            "id": "pi_synthetic", "object": "payment_intent", "livemode": False,
        }},
    }).encode()
    signature = hmac.new(
        secret.encode(), str(now).encode() + b"." + body, hashlib.sha256,
    ).hexdigest()
    inbox.record(scope, body, f"t={now},v1={signature}", secret, now=now)
    claim = inbox.claim_next(scope, "worker-a")
    assert claim is not None
    result = accept_stripe_readback(
        inbox, journal, claim, operation, retrieved_account="acct_synthetic",
        intent={
            "object": "payment_intent", "id": "pi_synthetic", "livemode": False,
            "amount": 1000, "amount_received": 1000, "currency": "usd",
            "status": "succeeded", "transfer_data": None, "on_behalf_of": None,
        },
    )
    assert result.outcome == "succeeded" and inbox.active_claims(scope) == ()
    assert not journal.reserve(operation).dispatch_allowed
    print(result.outcome)
```

[`Tests`](../../tests/test_stripe_atomic_readback.py) inject failure after payment
SQL but before the marker, and after both updates but before commit; both states
must remain unchanged. Other cases cover fresh-process visibility, concurrent
handoff/acceptance, competing accepts, stale/ABA handles, cross-file refusal,
binding errors, intermediate results and explicit already-handled refusal.

## 4. Architecture: fence the state writer, not the planner's narrative

Transactions and fencing are established distributed-systems techniques, not an
AI invention. Well-Architected quality guidance is not synonymous with a Web
three-tier deployment. The AI-native improvement is a deterministic economic
write boundary: replanning, model narratives and delivery metadata cannot replace
the persisted operation, validated provider observation or current ownership.

This is **opt-in**: existing standalone journal/completion APIs remain available.
Every cooperating readback worker must use the coordinated path for this local
guarantee; direct database/journal writes bypass it. A claim is not authentication
or a consumer approval, and no new generation creates a new payment authority.
Real retrieval authentication/freshness, initial association, worker authorization,
HTTP ACK/retry policy, periodic readback, Connect/organization/thin-event support,
multi-database workflows and all remote effects remain outside this reference.
