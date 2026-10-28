# Stage 1668: First timed signer history commits with both existing writes

[中文](2026-10-29-timed-signer-history.md) |
[Asset](../../lab/merchant_signers.py) |
[Tests](../../tests/test_timed_signer_history.py) |
[Previous post-lock time](2026-10-29-merchant-signature-time.en.md)

## Finding and evidence boundaries

“Passed an approval gate” does not imply “passed the timed signer gate”.
This increment adds separate **first timed-branch execution history**: only when
that branch creates a new reservation are local signer scope, selected signature
label, signature window and the original post-lock sample committed.
Attempt, approval history and timed history **commit or roll back together**.
This is a local execution record in a trusted database, not independently
verifiable signature evidence or current authority.

Evidence checked 2026-10-29 04:45 BJT:

- [RFC 9421 section 3.2.1](https://www.rfc-editor.org/rfc/rfc9421.html#section-3.2.1),
  actually titled *Enforcing Application Requirements*, distinguishes complete
  protocol verification from application requirements for time, key, nonce or tag.
  Adopted application requirements cannot be skipped because mathematical verification succeeds.
- [Section 3.3](https://www.rfc-editor.org/rfc/rfc9421.html#section-3.3)
  defines cryptographic sign/verify inputs and outputs. A local SQLite record
  neither retains nor recreates those proofs. **This audit schema is an engineering
  choice, not an RFC mandate.**
- [Visa's official repository](https://github.com/visa/trusted-agent-protocol/tree/16d59bdf3f8a542bc538d0962edbb80ea30a02af)
  HEAD remains `16d59bdf3f8a542bc538d0962edbb80ea30a02af`,
  dated `2025-10-28T22:43:43Z`, not a new product release on this retrieval date.

Existing [first approval history](2026-10-29-admission-provenance.en.md) provides
the first-reservation-only/non-backfill local pattern;
[Stage 1667](2026-10-29-merchant-signature-time.en.md) provides the single post-lock
sample. This combines existing mechanisms without new Stripe/Sierra release claims.

## Small asset and read contract

`TimedSignerAdmission(fingerprint, scope, signature_label, created, expires, admitted_at)`
and its nested `MerchantSignerScope` are frozen. New `merchant_timed_admissions`
storage contains only tenant/operation/full fingerprint, exact URI/key ID, label,
signature window and original sample. `created`/`expires` are **signature times,
not approval expiry**. `admitted_at` is the same original sample as approval history,
without a second clock call.

`MerchantSignerStore.read_timed_admission(operation)`:

1. Requires trusted `PaymentOperation`, looks up tenant/operation and checks the
   full fingerprint. Changes to provider/account, idempotency key, approval or
   Checkout cannot reuse the record.
2. Returns the first route/key/label/window. Scope tenant/merchant are reconstructed
   from the bound operation, not current permission or a later request's scope.
3. Checks stored scope, label, strict integers and the historical relation
   `0 <= created <= admitted_at < expires <= 999_999_999_999_999`.
   Missing, mismatched or malformed records fail explicitly, without success defaults.
4. **Never samples current time or readmits.** History remains readable after
   revocation/expiry while mutation continues to reject.

Existing `admit` reuses its transaction and clock callback, adding one INSERT only
when `timed is not None and decision.dispatch_allowed`, before commit/return.
Failure of the final history insert rolls back prior attempt/approval writes,
without an after-commit logging gap. Existing approval/journal schemas and public
transactions are unchanged.

| Existing state or input | New timed history |
|---|---|
| New reservation actually through the timed branch | One first record in the same transaction. |
| Valid retry, even with another permitted scope/key/label/window | No dispatch and no replacement of the first record. |
| Existing bare-signer, generic-approval or direct-journal attempt | Timed retry never backfills, even for terminal attempts. |
| Old database upgrade | Add an empty table; never infer new-gate execution from old approval/attempt rows. |
| Revoked, expired, malformed body, clock error or failed commit | No newly committed set of records or usable dispatch decision. |

Absent history means **no recorded execution**, not evidence of rejection.

## Executable synthetic example

Inputs below are explicitly constructed offline test objects, not claimed production
verifier evidence. No network request or payment is sent.

```python
import json
from dataclasses import asdict, replace
from pathlib import Path
from tempfile import TemporaryDirectory

from lab.agent_identity_attestation_guard import compute_rfc9530_content_digest
from lab.checkout import Checkout
from lab.merchant_signers import MerchantSignerError, MerchantSignerScope, MerchantSignerStore
from lab.payment_approvals import PaymentApprovalStore
from lab.payment_attempts import PaymentAttemptJournal, PaymentOperation
from lab.request_binding import (
    MUTATION_COMPONENTS, RequestSignatureSnapshot, TimedRequestSignatureSnapshot,
)

now, samples = [1700000000], []

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
    assert signers.admit(scope, approvals, journal, operation, timed, **ingress).dispatch_allowed
    first = signers.read_timed_admission(operation)
    assert first.scope == scope and first.signature_label == "sig1"
    assert first.admitted_at == approvals.read_admission(operation).admitted_at == now[0]
    now[0] += 1
    newer = replace(timed, signature=replace(snapshot, signature_label="sig2"), expires=now[0] + 20)
    assert not signers.admit(scope, approvals, journal, operation, newer, **ingress).dispatch_allowed
    assert signers.read_timed_admission(operation) == first
    signers.revoke(scope)
    try:
        signers.admit(scope, approvals, journal, operation, timed, **ingress)
    except MerchantSignerError as error:
        assert "revoked" in str(error)
    else:
        raise AssertionError("Revoked signer was admitted.")
    assert signers.read_timed_admission(operation) == first
    assert samples == [1700000000, 1700000001]
    assert journal.read(operation).outcome == "unknown"
    print("First timed history retained; retry and revoke cannot rewrite it.")
```

## AI-native architecture implications and remaining gaps

Cloud Well-Architected reliability and classic three-tier separation remain useful,
but a “request succeeded” log cannot distinguish which authority gate admitted it
at which instant. Agents retry economic intent, so execution architecture also
needs **fact-typed control-plane history**, rather than expanding one approval
boolean, log or remote status into a complete authority chain. Separate first facts
prevent a new gate from inventing provenance for old attempts.

The database, policy operator and complete verifier adapter must still be trusted.
Frozen objects, fingerprints, labels and key IDs do not authenticate cryptographic
provenance or pin public keys. URI/key IDs must not contain credentials.
No raw body, raw signature, key, complete signature base or verifier key material
is stored, so this record cannot independently reverify the original request.
There is no authenticated consumer consent, nonce consumption, remote revocation,
payment success or economic exactly-once guarantee. Bare APIs still bypass the timed path.
No tamper-resistant audit, external signature or automated retention/pruning is
provided; the additional storage creates retention responsibility.
Validity at the sample is not validity at commit/send, and reading history grants
no new dispatch authority.

## Validation

All **234** focused tests pass, including **33** new methods covering the same
post-lock sample, zero epoch/Structured Field maximum, tenant/full binding,
immutable first scope/label/window, no legacy/upgrade backfill, fresh-process reads,
corrupt metadata, concurrency and rollback after final INSERT/real third write/
commit failure. All **4,159** repository tests, compilation, both existing demos,
**157** local links and four current/previous executable examples in two identical
bilingual pairs passed. Final-SHA CI/canonical main synchronization remain
post-publication gates. These are synthetic engineering tests, not a model benchmark.
