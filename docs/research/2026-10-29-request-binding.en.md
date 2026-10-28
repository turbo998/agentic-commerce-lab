# Stage 1659: Agent identity signatures do not imply body coverage

[中文](2026-10-29-request-binding.md) |
[Daily record](../../research/daily/2026-10-29.en.md) |
[Stage index](../stage-archive-index.md)

**Finding:** a merchant cannot infer that every mutation input is protected because
some TAP signature is valid. Bind the actual request to one trusted signature's
**covered components and signed values**, then compare original body bytes against
the signed Content-Digest. Recomputing a digest after tampering must not pass.
This is a narrow merchant-local JSON mutation profile, not a new Visa mandate.

Research resumed from `134c414` at 02:27 Asia/Shanghai on 2026-10-29; primary sources
were retrieved 02:28–02:32. Work stays inside 23:00–06:00, with no new phase from
05:30. Protected README/SVG content is unchanged. `provenance=synthetic`,
`independently_reproduced=false`: offline constructed engineering verification,
not a model benchmark, Visa certification, real signature interoperability or
payment outcome. No new Stripe/Sierra release verification was performed.

## 1. Primary evidence and version boundary

| Evidence | Supported conclusion | Not implied |
|---|---|---|
| [Visa TAP developer documentation](https://developer.visa.com/docs/trusted-agent-protocol) | RFC 9421 signatures convey agent/intent and optional consumer/payment information | Any signature covers every body/query/header, or identity grants purchase consent |
| [Pinned official merchant signature example](https://github.com/visa/trusted-agent-protocol/blob/16d59bdf3f8a542bc538d0962edbb80ea30a02af/merchant-backend/app/security/signature_verification.py) | Verification input is built from selected components | The example is a complete RFC parser or universal merchant authorization policy |
| [RFC 9421](https://www.rfc-editor.org/rfc/rfc9421.html) | Applications select relevant signatures and enforce coverage; unrelated labels are not interchangeable | Cryptographic validity binds every application field |
| [RFC 9530 section 6.3](https://www.rfc-editor.org/rfc/rfc9530.html#section-6.3) | Digests cover content bytes; interpretation depends on Content-Type/Content-Encoding; digests alone do not authenticate/authorize | Valid JSON semantics, untransformed ingress, consent or successful payment |

The official repository HEAD remains `16d59bdf3f8a542bc538d0962edbb80ea30a02af`,
dated **2025-10-28**, not a new release on the 2026 retrieval date.
`@path` does not cover the full query; this local policy uses `@target-uri`.
The historical Stage 7 HMAC/directory/quota simulation remains unchanged. Its
"mandatory components" are demo-local rules, not universal RFC 9421/TAP mandates.

## 2. Small asset: exact binding, not model-claimed identity

[`lab/request_binding.py`](../../lab/request_binding.py) provides
`RequestSignatureSnapshot` and `require_bound_json_mutation(...) -> None`.
A snapshot must come from the trusted ingress adapter for **one verified signature
on the same request**, preserving label, key ID, unflattened component identifiers
and exact signed method/URI/type/digest values. Constructing or freezing the
dataclass is not authentication; never trust one supplied by an agent or request JSON.

| Local rule | Exact behavior |
|---|---|
| One signature's coverage | Require bare `@method`, `@target-uri`, `content-type`, `content-digest`; never union unrelated signatures |
| Component parameters | Reject parameterized, duplicate or non-bare identifiers; do not strip `;sf`, `;req`, `;tr` semantics |
| Current-value binding | Exact method/URI/type/digest equality with snapshot; no URL case/percent-encoding or JSON normalization |
| Method/media type | Uppercase POST/PUT/PATCH/DELETE; exact `application/json`, without charset parameters |
| Content-Encoding | Must be absent, even rejecting `identity`/empty fields rather than pretending proxy decompression is supported |
| Bytes/resources | Original immutable `bytes`; at most **1,048,576 bytes**, rejecting one byte more |
| Digest | Only exact canonical `sha-256=:...:`; reuse existing formatter and constant-time raw-body digest comparison |
| Result/effects | Return `None` on success; raise `RequestBindingError` otherwise; no journal write, payment or nonce consumption |

Additional bare identifiers are accepted, but their **values are not checked** here.
Business-critical headers still need adapter/route-specific signed-value and immutable
operation/approval bindings. Label/key ID are retained as context with format checks,
not signer allowlisting, key discovery or authenticity verification.
The trusted verifier owns full RFC 9421 parsing/cryptography, relevant label/tag,
key trust, validity, nonce/replay and faithful `@target-uri` derivation. The adapter
must reject ambiguous/duplicate raw HTTP headers and provide signed ingress bytes
**before** proxy transformations or reserialization.

This deliberate application restriction can reject richer valid RFC 9530
dictionaries/algorithms/parameters. No hand-written general Structured Fields
parser or simulated public-key verification is added.

## 3. Runnable synthetic boundary example

This snapshot is a test fixture, **not production wiring for unverified HTTP requests**.
Independent .NET SHA256 computation produced this fixed body's hex value:
`a223b60dc6adbc2911e7c073889b220df1181c5534fa6be58c3a70981c354c54`.

```python
from lab.agent_identity_attestation_guard import compute_rfc9530_content_digest
from lab.request_binding import (
    MUTATION_COMPONENTS, RequestBindingError, RequestSignatureSnapshot,
    require_bound_json_mutation,
)

body = b'{"amount":1000,"currency":"usd"}'
digest = "sha-256=:oiO2DcatvCkR58BziJsiDfEYHFU0+mvljDpwmBw1TFQ=:"
uri = "https://synthetic-shop.example/checkout?cart=one"
fixture = RequestSignatureSnapshot(
    "sig1", "synthetic-key", MUTATION_COMPONENTS,
    "POST", uri, "application/json", digest,
)
assert compute_rfc9530_content_digest(body) == digest
assert require_bound_json_mutation(
    fixture, method="POST", target_uri=uri, content_type="application/json",
    content_digest=digest, content_encoding=None, body=body,
) is None

changed = body.replace(b"1000", b"9000")
try:
    require_bound_json_mutation(
        fixture, method="POST", target_uri=uri, content_type="application/json",
        content_digest=compute_rfc9530_content_digest(changed),
        content_encoding=None, body=changed,
    )
except RequestBindingError:
    pass
else:
    raise AssertionError("a recomputed header must not replace the signed digest")
```

Binding does not prove valid JSON. Schema, duplicate keys, amount/currency/merchant
semantics, consumer consent, idempotency and business state remain separate gates.
Repeated checks consume no nonce and do not prevent replay. Successful matching
cannot close Stage 1652–1658 `unknown` payments or grant another dispatch.

## 4. Architecture: move from identity channels to immutable effect inputs

Well-Architected is quality/trade-off guidance, not a Web three-tier topology.
Signature coverage, byte integrity and application authorization are established
system boundaries. AI-native workloads additionally risk planners, tool adapters or
summarizers completing "identity verified" into "these economic inputs authorized."
Trusted ingress must preserve signed original values, and deterministic effect
paths must compare actual inputs before independent operation/approval and provider
fact checks. A model must not reconstruct evidence.

Visa TAP trusted communication, Poppy account/session access and Stripe PaymentIntent
state have distinct authorities. Local binding does not merge them into one
"payment succeeded" boolean. Production key/directory discovery, a full RFC verifier,
HTTP service, content-coding adapters, business schema, consent and remote payment
remain outside this increment.

## 5. Validation boundary

[`tests/test_request_binding.py`](../../tests/test_request_binding.py) adds 24 methods;
29 focused tests pass with the existing identity guard. Coverage includes the
independent fixture, simultaneous body/header substitution, URI/query/method/type
changes, missing/parameterized/duplicate components, strict text, the exact 1 MiB
boundary, immutability, repeat checks and an unchanged unknown/no-new-dispatch journal.
All 3,904 repository tests, compilation, both existing demos, 67 local links and
two executable bilingual examples passed. Eight historical generated report files
were restored, not published as new benchmarks. README.md, README.en.md and assets/
have zero diff from `1d9273d`. Final-commit remote CI and canonical-main synchronization
remain independent post-publication closeout gates, not production interoperability
or new model measurements.
