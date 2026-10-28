# Stage 1654: A valid signature still cannot turn an unknown payment into success

[中文](2026-10-29-stripe-delivery.md) | [Daily research](../../research/daily/2026-10-29.en.md) |
[Stage 1653 readback boundary](2026-10-28-stripe-observation.en.md)

**Verified 2026-10-29, Asia/Shanghai, starting 00:06; baseline `6cdefcf`.**
This is a `synthetic` offline engineering reference, not a Stripe SDK, live
payment integration, model benchmark, vendor certification, or product release.
The user's README and SVG assets remain unchanged.

## 1. Primary evidence: authentic delivery and current business state are different facts

| Primary source | Verified fact | Invalid inference |
|---|---|---|
| [Webhook signature guidance](https://docs.stripe.com/events/manage-webhook-endpoints#signature-errors) | Verification requires the unchanged raw body and the correct endpoint secret; CLI forwarding and configured endpoints use different secrets | Reserialized JSON or an arbitrary environment's secret is interchangeable |
| [Webhooks](https://docs.stripe.com/webhooks) | Verify before handling; snapshot and thin events require different handling | One check establishes every event format, account and business rule |
| [How events work](https://docs.stripe.com/events/how-events-work) | A snapshot can be stale by processing time; retrieve the latest object before acting | Signed `payment_intent.succeeded` is proof of current payment state or settlement |
| [Official Python implementation, pinned commit](https://github.com/stripe/stripe-python/blob/04dc12298d359a709e9ff289094e1a00c9ca666b/stripe/_webhook.py) | HMAC-SHA256 signs timestamp, dot and payload; multiple `v1` candidates are supported; default tolerance is 300 seconds | The implementation promises symmetric future-clock rejection or within-window replay prevention |

The source commit is dated 2026-10-27; webpage verification dates are not release
dates. This increment adds Stripe-specific evidence only. Visa TAP and Sierra
Poppy retain [Stage 1652's](2026-10-28-authority-recovery.en.md) evidence and
limitations; no new release is asserted. Shared-secret HMAC authentication is
not consumer consent, bank settlement, or nonrepudiation for third parties.

## 2. The offline asset returns transport evidence, never a payment outcome

[`lab/stripe_delivery.py`](../../lab/stripe_delivery.py) exposes
`verify_stripe_delivery(body, signature_header, endpoint_secret, *, now, tolerance=300)`.
It uses standard-library `hmac`, SHA-256 and `compare_digest`, not custom cryptography.

- Require the original `bytes`. Parsing and reserializing equivalent JSON cannot
  substitute for the original signed bytes.
- Accept any matching `v1` candidate for rotation overlap. Unknown schemes such
  as `v0` cannot authenticate alone; every header component needs nonempty key/value.
- **Strict local policy:** exactly one canonical nonnegative timestamp with no
  leading zeros; 64 lowercase hexadecimal characters per `v1`; timestamp and
  trusted `now` within the nonnegative signed-64-bit range; positive integer
  tolerance no greater than the signed-64-bit maximum. Booleans are not integer
  configuration, and zero cannot disable time checking.
- **Strict local clock policy:** `abs(now - timestamp) <= tolerance`, defaulting
  to 300 seconds in either direction. The pinned SDK checks past age; rejecting
  far-future timestamps is an additional local restriction, not SDK equivalence.
- Return only `timestamp`, `payload_sha256`, and `requires_readback=True`.
  Never return/persist the raw body, secret or payment outcome; no JSON parsing,
  journal mutation or HTTP acknowledgment.

Correctly signed non-JSON bytes can pass this transport-only function. Event
schema validation is separate. A replay inside the tolerance window can pass
again: no durable inbox or event deduplication is implemented. A body digest is
not a payment credential or an automatically safe public logging field.
Production should prefer the maintained official SDK; this reference is not
complete interoperability or security certification.

## 3. Runnable synthetic fixed vector

The following secret is explicitly synthetic and must never protect an actual
endpoint. An independent .NET implementation computed this fixed HMAC, rather
than relying only on a Python signer sharing the tested path. The historical
timestamp and injected `now` are for deterministic offline testing only.

```python
from lab.stripe_delivery import verify_stripe_delivery

body = b'{"id":"evt_synthetic"}'
signature = "585651ea0f3c4918ed81ef14a60ffcf0063a442cf6797db445410d1ef4930528"
result = verify_stripe_delivery(
    body, f"t=1700000000,v1={signature}",
    "synthetic-only-not-a-real-secret", now=1700000000,
)
assert result.timestamp == 1700000000
assert result.requires_readback
```

```powershell
python -m unittest tests.test_stripe_delivery tests.test_stripe_observation tests.test_payment_attempts tests.test_checkout -q
```

All 62 focused tests passed, including 16 new test methods: fixed vector,
byte/whitespace tampering, secret mismatch, rotation candidates, ambiguous
headers, inclusive past/future 300-second edges, 301-second rejection, invalid
configuration, within-window replay limitations, and successful verification
leaving the journal `unknown` with no new dispatch. These are deterministic
engineering test counts, not model scores, live payment success rates or
performance coordinates.

## 4. AI-native architecture: progress from independent evidence, not model inference

Suggested boundaries: receive raw bytes and verify -> separate schema/account
checks and durable inbox -> trusted provider readback with existing bindings ->
monotonic payment journal update. **The arrows describe responsibilities, not
an end-to-end implemented pipeline.** Initial object association, clock sync,
endpoint-secret management/rotation, account/mode isolation, ingress limits,
durable receipt and ACK, duplicate/out-of-order events, failed-readback retries,
and final settlement remain external responsibilities.

This specializes Well-Architected reliability and trust boundaries into economic
side-effect invariants; it neither claims the framework lacks security guidance
nor requires extra agents or microservices instead of a modular monolith.
Signature validity, deduplication, business terminality and consumer authority
have separate evidence and lifecycles. A model cannot infer all from one success.
