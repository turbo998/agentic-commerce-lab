# Stage 1672: Scoped Stripe Readback-Claim Status Lookup and State Boundaries

[中文](2026-10-31-stripe-claim-read.md) |
[Daily report](../../research/daily/2026-10-31.en.md) |
[Prior claim coordination](2026-10-29-stripe-readback.en.md) |
[Prior receipt history lookup](2026-10-29-stripe-receipt-read.en.md)

**Finding:** We added `StripeEventInbox.read_claim(scope, event_id)` plus a frozen
`ReadbackClaimStatus(claim, state)` record to read local claim-state history by the
five-dimensional scope key
`(tenant_id, endpoint_id, provider_account, livemode, event_id)`.
**`active` or `handled` only describes local coordination metadata; it is not proof of worker liveness,
authenticated provider readback, or payment success. `None` only means no claim row currently exists
for that scoped Event ID.**

This stage remains `provenance=synthetic`, `independently_reproduced=false`:
offline SQLite engineering assets, not a payment executor, distributed lease service, or protocol certification.

## 1. Upstream verification context (2026-10-31 00:06 BJT)

- `python scripts/source_monitor.py` generated
  [`research/daily/2026-10-31-sources.json`](../../research/daily/2026-10-31-sources.json)
  with `51/51` observations at `status="ok"`.
- The only `change="changed"` source was `stripe-spt`; two consecutive fetches of
  `shared-payment-tokens.md?agent-seller=seller` produced a unified diff showing only second-level
  jitter in the sample `expires_at` value (for example `1795968579 -> 1795968581`), so this hash
  drift is dynamic sample data, not by itself a protocol release.
- `stripe-mcp` policy facts remain unchanged:
  `deadline=2026-11-30`, `previous_deadline=2026-10-31`, `policy_change="unchanged"`.
- Poppy upstream HEAD moved to `ec16efa4459aaf98b1b82a1a5973504f4fd75fd9`
  (Draft 0.3 text updates), while `versions.json` still marks only `0.2`/`0.1` as published and keeps
  `0.3` unpublished (`in progress`).

## 2. New read-only claim-state contract

In [`lab/stripe_inbox.py`](../../lab/stripe_inbox.py):

1. Added `ClaimState = Literal["active", "handled"]` and frozen
   `ReadbackClaimStatus(claim: ReadbackClaim, state: ClaimState)`.
2. Added `_require_event_lookup(scope, event_id)` for pre-connection validation:
   - `scope` must be a trusted `StripeInboxScope`;
   - `event_id` must match `evt_[A-Za-z0-9_]+`;
   - invalid input errors before opening SQLite (never silently downgraded to absence).
3. `read_claim(scope, event_id)` executes one read-only JOIN:
   - reads from `stripe_event_inbox` + `stripe_readback_claims` by scoped key;
   - returns `None` when no claim row exists;
   - otherwise returns `ReadbackClaimStatus(ReadbackClaim(...), state)`;
   - no claim creation, no handoff, no completion, no writes, no writer lock.

## 3. Boundaries relative to existing paths

| Method | What it guarantees | What it does **not** guarantee |
|---|---|---|
| `read_claim` | Reads local claim-state history for the scoped Event ID. | Worker liveness, provider-readback authenticity, payment success. |
| `claim_next` | Creates first local claim with generation=1. | Payment authority or remote exactly-once behavior. |
| `handoff` | Trusted controller transfers local handling ownership and increments generation. | That the old worker has stopped external side effects. |
| `finish_readback` | Marks local claim state as handled. | That readback payload semantics were validated. |
| `accept_stripe_readback` | Atomically reconciles the journal and marks claim handled in one local transaction. | Settlement finality or fulfillment completion. |

## 4. Executable synthetic example

```python
import hashlib
import hmac
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from lab.stripe_inbox import StripeEventInbox, StripeInboxScope

now = 1700000000
secret = "synthetic-stage-1672-secret"
body = json.dumps({
    "id": "evt_claim_read", "object": "event", "livemode": False,
    "type": "payment_intent.succeeded",
    "data": {"object": {"id": "pi_claim_read", "object": "payment_intent", "livemode": False}},
}).encode()
sig = hmac.new(secret.encode(), str(now).encode() + b"." + body, hashlib.sha256).hexdigest()
scope = StripeInboxScope("tenant", "endpoint", "acct_synthetic", False)

with TemporaryDirectory() as directory:
    inbox = StripeEventInbox(Path(directory) / "inbox.sqlite3")
    inbox.record(scope, body, f"t={now},v1={sig}", secret, now=now)
    assert inbox.read_claim(scope, "evt_claim_read") is None
    claim = inbox.claim_next(scope, "worker-a")
    status = inbox.read_claim(scope, "evt_claim_read")
    assert status is not None and status.state == "active"
    current = inbox.handoff(status.claim, "worker-b")
    inbox.finish_readback(current)
    done = inbox.read_claim(scope, "evt_claim_read")
    assert done is not None and done.state == "handled"
```

## 5. Validation

- Added [`tests/test_stripe_claim_read.py`](../../tests/test_stripe_claim_read.py) with **12 tests**
  covering unclaimed `None`, active/handled state reads, reopen and subprocess persistence,
  five-dimensional scope isolation, direct lookup beyond `active_claims(limit=1000)`,
  rollback safety on failed commits, pre-connection input validation, corrupted stored metadata
  rejection, storage-error propagation, and SQL trace proof of read-only `SELECT`.
- Regression command passed (`505/505`):
  `python -m unittest tests.test_stripe_claim_read ... tests.test_poppy_replay_read -q`.

