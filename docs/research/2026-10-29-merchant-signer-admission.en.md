# Stage 1666: A committed local signer revoke blocks this gate's next reservation

[中文](2026-10-29-merchant-signer-admission.md) |
[Signer gate](../../lab/merchant_signers.py) |
[Approval core](../../lab/payment_approvals.py) |
[Tests](../../tests/test_merchant_signers.py)

## Finding and primary evidence

Cryptographically verified ingress and current merchant permission are different
facts. A snapshot verified before queueing cannot itself prove a merchant's local
signer policy still permits admission after a database writer releases its lock.
This increment adds an **opt-in merchant-local permission gate**; it is not Visa
signature verification, a universal TAP requirement or a remote revocation service.

Evidence rechecked 2026-10-29 04:15 BJT:

- [Visa TAP developer documentation](https://developer.visa.com/docs/trusted-agent-protocol)
  describes reconstructing a signature base and verifying the agent's public key.
  Agent recognition and optional consumer/payment signatures are not one merchant
  purchase-approval boolean.
- The [official sample](https://github.com/visa/trusted-agent-protocol/blob/16d59bdf3f8a542bc538d0962edbb80ea30a02af/merchant-backend/app/security/signature_verification.py)
  illustrates configured trusted-agent/public-key lookup and time checks.
  Official HEAD remains `16d59bdf3f8a542bc538d0962edbb80ea30a02af`,
  dated **2025-10-28T22:43:43Z**, not a new release on this retrieval date.
  It is not a same-transaction merchant permission/approval implementation.
- [RFC 9421 section 3.2.1](https://www.rfc-editor.org/rfc/rfc9421.html#section-3.2.1)
  permits application requirements such as appropriate key resolution, algorithms,
  age, nonce and tag. [Section 7.3.4](https://www.rfc-editor.org/rfc/rfc9421.html#section-7.3.4)
  distinguishes a valid signature from an appropriate key/algorithm for the message;
  [section 7.3.2](https://www.rfc-editor.org/rfc/rfc9421.html#section-7.3.2) discusses key theft/rotation.

These sources motivate separating identity and application policy; they do not
mandate this SQLite design. No new Stripe/Sierra release was checked.

## Small asset: one transaction, distinct authority inputs

`MerchantSignerScope(tenant_id, merchant, target_uri, key_id)` is immutable trusted
configuration, not proof of identity. Route/key ID require ASCII without controls;
all scope values are nonblank with no surrounding whitespace. Values are exact,
without URI normalization, wildcards or inherited tenant/merchant permissions.
`MerchantSignerStore.allow(scope)` records operator policy once;
`revoke(scope)` irreversibly flips an existing scope's flag, idempotently.
Replacement/reactivation is forbidden. Different key IDs may have separate permits.
Only non-secret scope identifiers and the revoke flag are added to storage.

Opt-in `admit(scope, approvals, journal, operation, signature, ...)`:

1. Requires trusted types, matching operation tenant/merchant and the snapshot's
   exact key ID; reuses original signed-body/trusted-quote validation against the
   scope's exact target URI and POST profile.
2. Requires all three stores to resolve to the same SQLite file, then acquires
   `BEGIN IMMEDIATE` and reads the exact local permission, rejecting absent/revoked.
3. Reuses the extracted existing approval transaction participant: immutable
   approval binding, revocation, strict expiry with one fresh post-lock clock,
   reservation and first-approval-admission history.
4. Commits before returning the existing `DispatchDecision`. Exceptions propagate;
   failed writes/commit do not return a usable decision.

No nested public transaction, new journal schema, duplicate approval policy or
changed legacy API is introduced. The private approval participant rejects
autocommit use. Existing approval/journal APIs **bypass this optional signer gate**.
Deployments needing it must route every relevant mutation through this facade.

## Exact guarantee and remaining gaps

| Ordering or input | Bounded result |
|---|---|
| Local revoke commits before blocked admission acquires lock | This gate rejects without reserving or writing approval admission history. |
| Reservation commits before local revoke | Existing unknown attempt/history remains; later gate retries reject, but no remote send is canceled or fenced. |
| Wrong tenant, merchant, exact URI or key ID | No permission inheritance; reject before reservation. |
| Valid local signer permit, absent/revoked/expired approval | No new reservation or consumer authority. |
| Legacy reservation or approval history | Never backfilled into signer-gate provenance. |

The adapter still owns full RFC/TAP parsing, crypto, trusted directory/key selection,
algorithm, label/tag, signature time, nonce and request provenance. A `key_id`
string is **not public-key pinning**. Rebinding different key material to an allowed
ID externally breaks that assumed provenance; use a trustworthy stable resolution
policy. Do not construct the snapshot or scope from untrusted agent JSON, and do
not put credentials into URI/key identifiers.

This gate **does not recheck signature expiry while queued**, consume a nonce,
authenticate the policy operator, synchronize a remote directory or prove consumer
consent. Approval expiry is checked at the post-lock clock sample, not a physical
commit/send deadline. `read_admission` remains **approval-gate-only history**, not
evidence that this optional signer gate ran. No signed/tamper-evident audit is added.
Separate files, legacy bypasses and restored database snapshots defeat shared
local guarantees. No payment is sent, undone, settled or fulfilled.

## Offline executable example

The snapshot below is deliberately synthetic, not a real verified Visa signature.
The narrow exception demonstrates expected local denial; no production error is
silently converted into approval or a successful ACK.

```python
import json
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory

from lab.agent_identity_attestation_guard import compute_rfc9530_content_digest
from lab.checkout import Checkout
from lab.merchant_signers import MerchantSignerError, MerchantSignerScope, MerchantSignerStore
from lab.payment_approvals import PaymentApprovalStore
from lab.payment_attempts import PaymentAttemptJournal, PaymentOperation
from lab.request_binding import MUTATION_COMPONENTS, RequestSignatureSnapshot

with TemporaryDirectory() as directory:
    path = Path(directory) / "commerce.sqlite3"
    journal, approvals = PaymentAttemptJournal(path), PaymentApprovalStore(path)
    signers = MerchantSignerStore(path)
    uri = "https://synthetic-shop.example/checkout?cart=one"
    operation = PaymentOperation(
        "tenant", "operation", "approval", "stripe:test", "acct_synthetic", "key",
        Checkout("synthetic-shop", "USD", "synthetic-sku", 2, 1000),
    )
    scope = MerchantSignerScope("tenant", "synthetic-shop", uri, "synthetic-key")
    body = json.dumps(asdict(operation.checkout)).encode()
    digest = compute_rfc9530_content_digest(body)
    fixture = RequestSignatureSnapshot(
        "sig1", "synthetic-key", MUTATION_COMPONENTS, "POST", uri, "application/json", digest,
    )
    values = dict(clock=lambda: 1700000000, method="POST", target_uri=uri,
                  content_type="application/json", content_digest=digest,
                  content_encoding=None, body=body)
    approvals.approve(operation, expires_at=1700000060)
    signers.allow(scope)
    first = signers.admit(scope, approvals, journal, operation, fixture, **values)
    assert first.dispatch_allowed and first.attempt.outcome == "unknown"
    signers.revoke(scope)
    try:
        signers.admit(scope, approvals, journal, operation, fixture, **values)
    except MerchantSignerError:
        pass
    else:
        raise AssertionError("A revoked scope must deny even a non-dispatch retry.")
    assert journal.read(operation) == first.attempt
    print({"synthetic": True, "real_payments": False, "outcome": "unknown"})
```

## Architecture and validation

Well-Architected is quality/trade-off guidance rather than a Web three-tier mandate.
Application permission checks and transaction ordering predate AI. AI-native commerce
adds independently retried planners/workers and reconstructed evidence: do not let
"signature verified earlier" become "current merchant permission and consumer approval."
This can remain a modular monolith with distinct trusted inputs, not more self-authorizing
agents or compulsory microservices. [Stripe endpoint-secret rotation](2026-10-29-stripe-secret-rotation.en.md)
and [Poppy replay admission](2026-10-29-poppy-admission-clock.en.md) have different
keys, namespaces and authorities; this store does not combine them.

All 171 focused tests pass with 28 new methods: actual SQL-observed lock waiting,
revoke-first and post-lock approval expiry, scope isolation, one concurrent dispatch,
fresh process, real post-reservation/history and policy-write/commit rollback,
legacy bypass/no backfill and minimal storage. Synthetic engineering fixtures only,
not a model benchmark or Visa interoperability certification. All 4,096 repository
tests, compilation, both existing demos, 127 local links and two identical executable
bilingual examples passed. Eight generated historical reports were restored, with no
report content staged. Protected README/assets have zero diff from `1d9273d`.
Final-SHA CI/canonical synchronization remain post-publication gates, not signature
interoperability or payment evidence.
