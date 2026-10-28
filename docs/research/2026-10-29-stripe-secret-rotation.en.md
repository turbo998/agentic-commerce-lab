# Stage 1665: An active secret set changes verification, not Event identity

[中文](2026-10-29-stripe-secret-rotation.md) |
[Verifier](../../lab/stripe_delivery.py) |
[Inbox](../../lab/stripe_inbox.py) |
[Tests](../../tests/test_stripe_secret_rotation.py)

## Finding and scope

The existing verifier already checks multiple `v1` signatures against one trusted
endpoint secret. That already handles Stripe's overlapping-signature delivery;
it is not a protocol bug. This increment adds a local configuration option:
`endpoint_secret` can remain a string or be a **nonempty tuple of nonblank strings**.
The same option reaches `StripeEventInbox.record`, without a new facade or schema.
Every configured entry is validated before any signature match; an invalid trailing
entry is an error even if the first entry could authenticate the delivery.

Each entry must be an active secret for the **same trusted endpoint/account/mode**.
The adapter selects this snapshot outside the request and owns its retirement.
A payload/header/agent cannot choose keys, an endpoint or a provider account.
The primitive cannot authenticate the adapter's configuration provenance.
Mutable lists, empty tuples, nested values and non-string members are rejected.
Duplicate valid strings are harmless redundancy.

## Primary evidence, checked 2026-10-29 04:01 BJT

- [Stripe webhooks](https://docs.stripe.com/webhooks), sections **Roll endpoint signing
  secrets periodically** and **Verify the signature**: immediate retirement or delayed
  expiry up to 24 hours; during overlap, multiple active secrets and one signature
  per secret. Endpoint secrets differ across endpoints and test/live modes.
- [Manage webhook endpoints](https://docs.stripe.com/events/manage-webhook-endpoints):
  confirms the rolling behavior; CLI-forwarded secrets differ from Dashboard endpoint
  secrets. The old `/webhooks/signature` URL currently redirects here.
- Both require the exact unmodified body for signature verification. Stripe recommends
  official libraries for real integrations. This is a narrow offline reference, not a
  complete SDK replacement; tuple support is our local API, not an SDK compatibility claim.

These are mutable documentation pages observed on the stated date, not a new Stripe
product release or a versioned protocol announcement. No new Visa/Sierra release
was checked in this increment.

## One verification policy, separate control planes

Both configuration forms use the existing single parser and `timestamp + "." + body`
HMAC-SHA256 input. Each tried secret computes one HMAC, compared with the parsed `v1`
candidates using `compare_digest`; the first matching pair suffices. Total runtime is
not promised constant across key ordering. All malformed `v1` candidates still reject,
even alongside a valid candidate. Original immutable bytes, canonical unique timestamp,
strict positive tolerance and inclusive symmetric time bounds remain unchanged.

| Boundary | What changes or stays outside this asset |
|---|---|
| Key-roll overlap | Trusted configuration may contain multiple active endpoint secrets. |
| Key retirement | Remove old keys from every verifier's trusted snapshot; no remote expiry lookup or implicit timer. |
| Delivery freshness | Existing tolerance remains 300 seconds by default, not 24 hours; no replay-prevention claim. |
| Durable receipt | Same tenant/endpoint/account/mode/Event ID identity, regardless of signing key or signature timestamp. |
| Provider outcome | Receipt is a hint requiring authenticated readback, not a successful payment. |
| Dispatch/approval | No new reservation, consent, worker authority or payment send. |

**Remote expiry does not remove a retained local secret.** A compromised old secret
that remains configured can still create an acceptable fresh HMAC. Operators must
publish and deploy the correct active set; this lab does not manage secrets, verify
external expiry state, or guarantee retirement convergence. Never put CLI, other
endpoint/account/mode keys into a global fallback keyring.

Verification still happens before JSON parsing, database connection and duplicate
lookup. A retired-key-only delivery therefore rejects even if its Event is already
stored. A newly signed copy of the same accepted Event still returns the first receipt;
rotation does not resurrect handled work. Thin events, Connect and organization
contexts remain outside this snapshot inbox's supported policy.

## Offline executable example

Synthetic fixtures only: no network, real keys, endpoint registration or payment.
The `except` below verifies an expected rejection; production storage/verifier
exceptions propagate to the caller's explicit ingress/ACK policy.

```python
import hashlib
import hmac
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from lab.stripe_delivery import StripeDeliveryError
from lab.stripe_inbox import StripeEventInbox, StripeInboxScope

now = 1700000000
old, new = "synthetic-only-overlap-old", "synthetic-only-overlap-new"
body = json.dumps({
    "id": "evt_synthetic", "object": "event", "livemode": False,
    "type": "payment_intent.succeeded",
    "data": {"object": {
        "id": "pi_synthetic", "object": "payment_intent", "livemode": False,
    }},
}).encode()

def signed(secret):
    digest = hmac.new(secret.encode(), str(now).encode() + b"." + body, hashlib.sha256)
    return f"t={now},v1={digest.hexdigest()}"

with TemporaryDirectory() as directory:
    inbox = StripeEventInbox(Path(directory) / "inbox.sqlite3")
    scope = StripeInboxScope("synthetic-tenant", "synthetic-endpoint", "acct_synthetic", False)
    first = inbox.record(scope, body, signed(old), (old, new), now=now)
    again = inbox.record(scope, body, signed(new), (new,), now=now)
    assert first.first_seen and not again.first_seen
    assert again.receipt == first.receipt and again.receipt.requires_readback
    try:
        inbox.record(scope, body, signed(old), (new,), now=now)
    except StripeDeliveryError:
        pass
    else:
        raise AssertionError("A retired-only key must not bypass verification on a duplicate.")
    assert len(inbox.pending(scope)) == 1
    print({"synthetic": True, "receipt_count": 1, "requires_readback": True})
```

## Architecture implications and validation

Well-Architected is quality/trade-off guidance, not a mandatory three-tier topology.
Rotation, secret separation and webhook verification predate AI. AI-native commerce
adds planner retries, tool-generated payloads and independently restarted workers:
they must not reconstruct the trusted active-key set from conversation state or
interpret a rotated signature as renewed consumer authority. Keep configuration,
transport evidence, receipt coordination and economic authority as separate planes.
This complements [merchant request binding](2026-10-29-request-binding.en.md) and
[Poppy post-lock assertion admission](2026-10-29-poppy-admission-clock.en.md);
their signatures, identities, secrets and replay scopes are not interchangeable.

All 154 focused tests pass, including 26 new methods for secret/signature ordering,
full configuration validation, one HMAC per tried key, exact time/body policy,
retired duplicates before storage, concurrent/reopened dedup, scoped minimal storage
and no payment/dispatch authority. These are synthetic engineering fixtures, not a
model benchmark. All 4,068 repository tests, compilation, both existing demos,
119 local links and two identical executable bilingual examples passed. Ten generated
historical reports were restored, with no report content staged. Protected README/assets
have zero diff from `1d9273d`. Final-SHA CI/canonical synchronization remain
post-publication gates, not provider or payment evidence.
