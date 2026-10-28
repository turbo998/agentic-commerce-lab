# Stage 1667: Signature and approval share one post-lock time sample

[中文](2026-10-29-merchant-signature-time.md) |
[Time input and validation](../../lab/request_binding.py) |
[Signer gate](../../lab/merchant_signers.py) |
[Tests](../../tests/test_merchant_signature_time.py) |
[Previous local revocation](2026-10-29-merchant-signer-admission.en.md)

## Finding and primary evidence

Valid signature time at ingress does not imply validity after waiting for a merchant
writer lock. The optional `TimedRequestSignatureSnapshot(signature, created, expires)`
carries a snapshot and authenticated time parameters from **one preverified signature**.
After acquiring the lock, signature time and approval expiry share **one trusted clock
sample**, without a new transaction, payment send or history schema.

Evidence rechecked 2026-10-29 04:29–04:30 BJT:

- [RFC 9421 section 2.3](https://www.rfc-editor.org/rfc/rfc9421.html#section-2.3)
  and [section 2.5](https://www.rfc-editor.org/rfc/rfc9421.html#section-2.5):
  `created`/`expires` are individual signature parameters.
  `@signature-params` must enter the signature base, but is not an entry in the
  covered-components list. The trusted verifier must authenticate and extract
  these values from the **same selected signature**, never combine labels.
- [Section 3.2.1](https://www.rfc-editor.org/rfc/rfc9421.html#section-3.2.1)
  allows application age/expiry requirements. RFC 9421 does not universally require
  every signature to contain both parameters. Mandatory nonnegative times,
  zero skew and exclusive expiry here are local policy, not universal TAP rules.
- [RFC 8941 section 3.3.1](https://www.rfc-editor.org/rfc/rfc8941.html#section-3.3.1):
  these parameters use Structured Field Integers, whose maximum positive value is
  `999_999_999_999_999`, **not the signed-64-bit maximum**. Decoded signature
  parameters here must fit that range.
- [RFC 9421 section 7.2.2](https://www.rfc-editor.org/rfc/rfc9421.html#section-7.2.2)
  distinguishes time limits from nonce replay detection. A repeated signature
  within its window is not consumed by a time check.
- [Visa's official repository](https://github.com/visa/trusted-agent-protocol/tree/16d59bdf3f8a542bc538d0962edbb80ea30a02af)
  HEAD remains `16d59bdf3f8a542bc538d0962edbb80ea30a02af`,
  dated `2025-10-28T22:43:43Z`, not a new product release on this retrieval date.

This is a local application admission profile, not an RFC parser, Visa signature
implementation or vendor architecture-conformance claim. No new Stripe/Sierra
release was checked, and local guarantees are not projected onto those products.

## Small asset and exact contract

Pure `require_signature_time(timed, now=...)` requires one nested
`RequestSignatureSnapshot`; `created`/`expires` must be strict integers, rejecting
bool, float, string, negative and out-of-Structured-Field-range values, with
`created < expires`. The trusted clock retains the existing approval policy's
nonnegative signed-64-bit integer domain. The window is **`created <= now < expires`**.
No maximum signature lifetime, Stripe 300-second tolerance or fabricated defaults
for missing parameters are introduced.

The existing `signature` argument of `MerchantSignerStore.admit` now accepts bare
or timed snapshots:

1. Timed input unwraps the original snapshot for existing trusted scope/key-ID,
   original-byte, signature-coverage, exact-URI, strict-JSON and trusted-Checkout checks.
2. The same-file `BEGIN IMMEDIATE` is acquired before local signer permission
   and existing approval binding/revocation checks.
3. When the original approval core calls its clock, the timed branch checks the
   signature window using that **one sample**, then returns that exact value for
   approval expiry and first `admitted_at` history.
4. Reservation/history commit together before returning. Time errors, clock
   exceptions and failed commits do not return usable dispatch decisions.
   Even a non-dispatch retry cannot bypass the time check.

Original `RequestSignatureSnapshot` behavior is preserved, **without a new
signature-time check**. Old approval/journal APIs also bypass this optional boundary.
Route adapters requiring the stronger policy must require timed input and never
retry as bare on failure. Malformed wrappers do not downgrade here.
Existing approval history remains approval-gate-only: it does **not** prove
timed-signature, signature or signer provenance.

## Executable synthetic example

These are explicitly constructed offline test inputs, not claimed production
signature-verification results. No network request or payment is sent.

```python
import json
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory

from lab.agent_identity_attestation_guard import compute_rfc9530_content_digest
from lab.checkout import Checkout
from lab.merchant_signers import MerchantSignerScope, MerchantSignerStore
from lab.payment_approvals import PaymentApprovalStore
from lab.payment_attempts import PaymentAttemptJournal, PaymentOperation
from lab.request_binding import (
    MUTATION_COMPONENTS, RequestBindingError, RequestSignatureSnapshot,
    TimedRequestSignatureSnapshot,
)

now = [1700000000]
samples = []

def clock():
    samples.append(now[0])
    return now[0]

with TemporaryDirectory() as directory:
    path = Path(directory) / "commerce.sqlite3"
    journal, approvals = PaymentAttemptJournal(path), PaymentApprovalStore(path)
    signers = MerchantSignerStore(path)
    uri = "https://synthetic-shop.example/checkout"
    operation = PaymentOperation(
        "tenant", "operation", "approval", "stripe:test", "acct_synthetic", "key",
        Checkout("synthetic-shop", "USD", "synthetic-sku", 1, 1000),
    )
    scope = MerchantSignerScope("tenant", "synthetic-shop", uri, "synthetic-key")
    approvals.approve(operation, expires_at=now[0] + 60)
    signers.allow(scope)
    body = json.dumps(asdict(operation.checkout)).encode()
    digest = compute_rfc9530_content_digest(body)
    snapshot = RequestSignatureSnapshot(
        "sig1", scope.key_id, MUTATION_COMPONENTS, "POST", uri, "application/json", digest,
    )
    timed = TimedRequestSignatureSnapshot(snapshot, now[0], now[0] + 10)
    ingress = dict(
        clock=clock, method="POST", target_uri=uri, content_type="application/json",
        content_digest=digest, content_encoding=None, body=body,
    )
    first = signers.admit(scope, approvals, journal, operation, timed, **ingress)
    assert first.dispatch_allowed and first.attempt.outcome == "unknown"
    assert approvals.read_admission(operation).admitted_at == samples[0]
    now[0] += 10
    try:
        signers.admit(scope, approvals, journal, operation, timed, **ingress)
    except RequestBindingError as error:
        assert "window" in str(error)
    else:
        raise AssertionError("Expired timed retry was accepted.")
    assert samples == [1700000000, 1700000010]
    assert journal.read(operation) == first.attempt
    assert approvals.read_admission(operation).admitted_at == 1700000000
    print("Expired timed retry rejected; original payment remains unknown.")
```

## Why this is not just a classic three-tier concern

Web frontend/API/database layers and cloud Well-Architected reliability principles
remain useful, but do not alone identify **the linearization point at which authority
still holds**. Agents can retry economic actions; ingress signature verification,
queueing, revocation, approval expiry, reservation and remote outcomes are different
facts. This asset places adjacent local policies under one lock and time sample
instead of permanently caching an ingress verification result as purchase authority.

The guarantee holds only at the post-lock **sample**, not physical commit or remote
send time. The trusted application must provide a fresh sample when called;
a callback returning stale ingress time violates that prerequisite.
A frozen wrapper does not authenticate provenance or detect forged/cross-label
parameters. Full RFC/TAP crypto, key/directory/algorithm selection, signature-parameter
provenance, nonce and consumer authority remain the trusted adapter's responsibility.
There is no new key pinning, remote revocation, nonce consumption, signature-time
audit record or economic exactly-once guarantee.

## Validation

All **201** focused tests pass, including **30** new methods covering actual blocked
BEGIN expiry/still-valid/creation-boundary paths, one shared clock/history sample,
strict types/15-digit bounds, original scope/body/quote checks, expired retries,
legacy paths, revocation, concurrency and real post-write/commit rollback.
All **4,126** repository tests, compilation, both existing demos, **149** local
links and two identical executable bilingual examples passed. Final-SHA CI/canonical
main synchronization remain post-publication gates. These are synthetic engineering
tests, not a model benchmark.
