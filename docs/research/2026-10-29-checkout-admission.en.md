# Stage 1660: Signed client totals cannot become trusted prices

[中文](2026-10-29-checkout-admission.md) |
[Daily record](../../research/daily/2026-10-29.en.md) |
[Previous increment](2026-10-29-request-binding.en.md)

**Finding:** byte integrity, JSON semantics, trusted quotes, consent and business
idempotency are separate gates. Stage 1659 binds supplied fields to one trusted
signature snapshot, but the body can still contain duplicate keys or a correctly
signed wrong price. This increment compares against an **existing trusted Checkout**
before using the existing journal. No client price, identity signature or model output
creates pricing authority or approval.

Resumed from `779ebe6` at 02:46 Asia/Shanghai on 2026-10-29; primary sources checked
02:47–02:48. Work remains 23:00–06:00, with no new phase from 05:30 and no README/SVG
changes. `provenance=synthetic`, `independently_reproduced=false`: offline engineering
assets, not model benchmarks, Stripe SDK certification, actual signature/payment
interoperability or a new product release. No new Visa/Sierra release verification.

## 1. Evidence and prior assets

| Evidence | Constraint adopted here |
|---|---|
| [Stripe dynamic amount guidance, Payment Intents variant](https://docs.stripe.com/payments/advanced/dynamically-update-amounts.md?payment-ui=elements) | Determine totals server-side, not from client prices; authorize business changes and check mutable payment state separately |
| [RFC 8259 sections 4/6/8/9](https://www.rfc-editor.org/rfc/rfc8259.html) | Duplicate names can have divergent interpretations; nonfinite numbers are outside the grammar; specify encoding/resources |
| [Python 3.12 JSON documentation](https://docs.python.org/3.12/library/json.html#repeated-names-within-an-object) | Default duplicate handling is last-wins and accepts NaN/Infinity; defaults are not strict business admission |
| [`Checkout`](../../lab/checkout.py) | Reuse the validated immutable quote; amount is total including tax/shipping, not unit price |
| [`PaymentAttemptJournal`](../../lab/payment_attempts.py) | Reuse durable operation/approval/provider-key binding; first local dispatch still leaves unknown outcome |

RFC object-name uniqueness is SHOULD; rejecting duplicates is local policy, not
a claim that the JSON grammar universally forbids them. Stripe guidance is not a
new release announcement or proof of deployed pricing, consent or PaymentIntent updates.

## 2. Opt-in admission facade

[`reserve_signed_checkout`](../../lab/checkout_admission.py) takes a trusted journal,
already-approved `PaymentOperation`, trusted signature snapshot and actual ingress.
The configured `expected_target_uri` and operation lookup must not come from agent/request JSON.

1. Require POST and exact current full URI equality with trusted route configuration.
2. Reuse Stage 1659 snapshot/raw-byte binding before decoding, never reserializing first.
3. Require one UTF-8 object with exactly merchant/currency/sku/quantity/amount keys.
4. Reject decoded duplicate names, including escaped equivalents, fraction/exponent/
   nonfinite numbers, boolean/string numbers, unknown fields, BOM and invalid Unicode
   scalars. Do not normalize currency or merchant identity.
5. Match strict types/values against the trusted Checkout, then return the journal's
   existing `DispatchDecision`.

These five fields form a **local single-item slice**, not a universal Stripe API
or Visa TAP payload. Do not multiply quantity by amount: amount is already total.
The existing 1 MiB byte limit applies. Integer tokens are capped at 20 characters
before conversion; values must exactly match Checkout's positive signed-64 integers.
The valid signed-64 boundary is not rounded, but JavaScript binary64 cannot
necessarily round-trip it; cross-language production schemas need separate design.
Deep nonobject/schema input rejects; decoder RecursionError is explicitly converted.
No independent fixed-depth budget or streaming parser is claimed.

The duplicate hook is extracted from existing MCP inventory code into
[`json_members.py`](../../lab/json_members.py). The old
`lab.mcp_migration.unique_members` name, ValueError text and module/direct-file CLI
remain compatible. Inventory policy, Stripe inbox and historical simulated pipelines
are unchanged. Schema errors raise `CheckoutAdmissionError`; original binding errors,
journal conflicts and storage errors propagate rather than becoming success defaults.

## 3. Runnable synthetic example: different signed bytes, same operation

Snapshots below are fixtures, not production signature verification. Assume trusted
pricing, consent, expiry/revocation and operation selection are already satisfied;
this example neither creates nor proves those prerequisites.

```python
import json
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from lab.agent_identity_attestation_guard import compute_rfc9530_content_digest
from lab.checkout import Checkout
from lab.checkout_admission import reserve_signed_checkout
from lab.payment_attempts import PaymentAttemptJournal, PaymentOperation
from lab.request_binding import MUTATION_COMPONENTS, RequestSignatureSnapshot

operation = PaymentOperation(
    "tenant", "operation", "approval", "stripe:test", "acct_synthetic", "key",
    Checkout("synthetic-shop", "USD", "synthetic-sku", 2, 1000),
)
uri = "https://synthetic-shop.example/checkout?cart=one"
with TemporaryDirectory() as directory:
    journal = PaymentAttemptJournal(Path(directory) / "commerce.sqlite3")
    decisions = []
    for indent in (None, 2):
        body = json.dumps(asdict(operation.checkout), indent=indent).encode()
        digest = compute_rfc9530_content_digest(body)
        fixture = RequestSignatureSnapshot(
            "sig1", "synthetic-key", MUTATION_COMPONENTS,
            "POST", uri, "application/json", digest,
        )
        decisions.append(reserve_signed_checkout(
            journal, operation, fixture, expected_target_uri=uri,
            method="POST", target_uri=uri, content_type="application/json",
            content_digest=digest, content_encoding=None, body=body,
        ))
    assert [d.dispatch_allowed for d in decisions] == [True, False]
    assert all(d.attempt.outcome == "unknown" for d in decisions)
```

Changed bytes/signatures are not a new economic operation; changing formatting,
operation/key must not resend an unknown payment. Failed admission does not consume
first dispatch; successful admission records only a local reservation, with no network
payment. Callers must inspect `dispatch_allowed`; standalone journal APIs can bypass
this opt-in facade.

## 4. Architecture and validation boundaries

Well-Architected is quality/trade-off guidance, not a Web three-tier diagram.
Server-side pricing, authorization, schema and idempotency are established system
requirements. AI-native workloads additionally must prevent variable planners/tool
translators from rebuilding quotes, approvals or retry identity out of authenticated
but untrusted values. Deterministic effect paths must preserve each fact's authority,
not amplify "signature valid" into "everything executable."

This facade does not verify real signatures/keys/nonces or provide a consent service.
Revocation/expiry checks are not atomic with reservation here; trusted production
callers must enforce them before each admission. Provider wire mapping, live amount
updates, tokens, settlement and multi-item schemas are outside scope.

[`tests/test_checkout_admission.py`](../../tests/test_checkout_admission.py) adds
30 methods; 94 focused tests pass with migration/checkout/payment-attempt/binding.
Coverage includes binding-before-decoding, strict semantics, escaped duplicates,
20/21-character integer tokens, 1 MiB ±1 boundary, real fresh processes, concurrent
one-winner admission, terminal/unknown non-redispatch and the old CLI.
Initial validation corrected a platform-dependent recursion assertion and preserved
direct-file CLI behavior affected by helper extraction. All 3,934 repository tests,
compilation, both existing demos, 81 local links and two executable bilingual examples
passed. Ten generated historical report files were restored, not published as new
benchmarks. README.md, README.en.md and assets/ have zero diff from `1d9273d`.
Final-commit CI and canonical-main synchronization remain independent post-publication
gates, not actual payment or authorization.
