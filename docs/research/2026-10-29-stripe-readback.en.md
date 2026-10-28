# Stage 1656: Old generations cannot finish local hints; old workers may still run

[中文](2026-10-29-stripe-readback.md) | [Daily research](../../research/daily/2026-10-29.en.md) |
[Receipt identity](2026-10-29-stripe-inbox.en.md)

**Verified 2026-10-29, Asia/Shanghai, starting 01:04; baseline `cac1ae6`.**
This is a `synthetic` offline engineering reference, not a model benchmark,
distributed lock service or real payment worker. No new Visa/Sierra release
verification was performed.

**Later compatibility note:** [Stage 1657](2026-10-29-stripe-atomic-readback.en.md)
adds an opt-in same-database transaction coupling journal reconciliation to claim
completion. The standalone ownership API below still fences only its local marker.

## 1. Primary evidence supports not building an automatic lease here

[Stripe Webhooks](https://docs.stripe.com/webhooks) recommends async handling
without assuming duplicates or out-of-order delivery disappear. Receipt dedup
does not identify the worker owner or crash-recovery policy.
The [AWS Builders' Library leader-election article](https://aws.amazon.com/builders-library/leader-election-in-distributed-systems/)
is dated **2019-12-05**, not a new release. It explains pauses, clock hazards and
old leaders still running, durable work before completion notification,
idempotency and preferring tested clients. Its leases use local elapsed duration,
not synchronized cluster wall time.

This stage does not label an injected `now + timeout` a reliable distributed
lease. Choose the smaller boundary: **a trusted controller explicitly hands off
work; a SQLite transaction compares/increments generation and rejects stale
local completion handles.** No clock parameter, expiry, renewal, heartbeat or
automatic recovery. [SQLite isolation](https://sqlite.org/isolation.html)
supports committed visibility and serialized writes across independent local
connections, not control of remote systems or paused workers.

## 2. A new generation is not a new payment attempt

[`lab/stripe_inbox.py`](../../lab/stripe_inbox.py) adds a parent-linked
`stripe_readback_claims` table without changing receipt schema, dedup or
`pending()` behavior. Reopening an older database adds the table without
deleting receipts.

| Operation | Local state | Invalid inference |
|---|---|---|
| `claim_next(scope, worker)` | Never-claimed hint becomes `active`, generation=1 | New payment attempt or consumer authority |
| `handoff(current, worker)` | Compare scope/receipt/owner/generation, then increment | Old worker is proven expired or stopped |
| `finish_readback(current)` | Current handle becomes `handled`; same-handle repeat is idempotent | Authenticated readback, paid funds or fulfillment |
| Stale finish/handoff | Explicit error; current ownership unchanged | Old worker's network call or other database write is prevented |
| Redelivery after handled | No resurrected local work | Cross-Event/endpoint economic effects are deduplicated |

Same-worker recovery also increments generation, preventing an ABA identity
mix-up. `claim_next` returns `None` for no available work, a normal control
state. Invalid input, stale handles, generation exhaustion and storage failures
never return success; generation cannot wrap. `active_claims(scope, limit=100)`
enumerates 1–1000 recovery hints, not recovery decisions. `pending()` still
enumerates all receipts, including handled ones; `receipt.requires_readback=True`
means receipts cannot prove business facts, not a worker-state flag.

**Handles are coordination metadata, not cryptographic capabilities or worker
authentication.** Only trusted workers/controllers should call these APIs;
they are not model tools. Malicious DB writers, unauthenticated callers guessing
current metadata, and backup rollback are not defended; generation history must
be retained.

## 3. Runnable explicit handoff and stale-handle rejection

```python
import hashlib
import hmac
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from lab.stripe_inbox import StripeEventInbox, StripeInboxError, StripeInboxScope

secret = "synthetic-only-readback-secret"
body = json.dumps({
    "id": "evt_synthetic", "object": "event", "livemode": False,
    "type": "payment_intent.succeeded",
    "data": {"object": {"id": "pi_synthetic", "object": "payment_intent", "livemode": False}},
}).encode()
digest = hmac.new(secret.encode(), b"1700000000." + body, hashlib.sha256).hexdigest()
scope = StripeInboxScope("tenant", "endpoint", "acct_synthetic", False)
with TemporaryDirectory() as directory:
    inbox = StripeEventInbox(Path(directory) / "inbox.sqlite3")
    inbox.record(scope, body, f"t=1700000000,v1={digest}", secret, now=1700000000)
    old = inbox.claim_next(scope, "worker-a")
    assert old is not None
    current = inbox.handoff(old, "worker-b")  # Trusted synthetic recovery decision.
    assert current.generation == old.generation + 1
    try:
        inbox.finish_readback(old)
    except StripeInboxError as error:
        assert "stale" in str(error)
    else:
        raise AssertionError("Old handle unexpectedly accepted")
    inbox.finish_readback(current)  # Synthetic local handling, no provider call.
    assert not inbox.active_claims(scope)
    assert inbox.pending(scope)[0].requires_readback
```

Secret, event and frozen clock are synthetic; no actual Stripe retrieval or
payment mutation occurs. All 104 focused tests passed, including 21 new methods:
concurrent claim/handoff, stale/ABA handles, scope/receipt substitution, actual
fresh-process completion, older-file upgrade, three commit-failure rollbacks
and unchanged payment journal.
All 3,829 repository tests, compilation, both existing demos, 46 local links
and four old/new bilingual examples passed.

```powershell
python -m unittest tests.test_stripe_readback tests.test_stripe_inbox tests.test_stripe_delivery tests.test_stripe_observation tests.test_payment_attempts tests.test_checkout -q
```

## 4. External atomicity remains an explicit boundary

`finish_readback` records a trusted caller's assertion of handled work; it does
not verify that a provider was read. Do not write another business database
first, then assume a later finish call fenced that earlier write. Readback
authenticity, existing association/account/amount checks and business-result
acceptance need independent contracts: this handle does not replace
[Stage 1653's semantic gate](2026-10-28-stripe-observation.en.md).
A payment still `unknown` after processing needs later events or independent
reconciliation; a handled hint cannot close it. No HTTP ACK, network worker,
scheduler, automatic recovery or external exactly-once effect is implemented.

Traditional reliability already handles old owners and idempotency; these are
not uniquely AI innovations. AI-native design additionally prevents replanning,
recovery or a new generation from rebuilding payment-operation IDs, consumer
authority or provider idempotency keys. Local work ownership changes; economic
authority does not.
