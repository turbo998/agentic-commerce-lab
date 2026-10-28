# Stage 1661: Revocation checks and first reservation must share a write transaction

[中文](2026-10-29-approval-admission.md) |
[Daily record](../../research/daily/2026-10-29.en.md) |
[Previous increment](2026-10-29-checkout-admission.en.md)

**Finding:** checking approval on one connection and reserving on another leaves
a revocation race. This increment reads the bound approval, checks revocation/expiry
and reuses reservation inside one SQLite write transaction. Sample the trusted clock
after acquiring the write lock, not before waiting.
**This fences local admission only: later revocation cannot withdraw a committed
dispatch decision or prevent a remote payment.**

Resumed from `238aa8c` at 03:03 Asia/Shanghai on 2026-10-29; primary sources/code
checked 03:03–03:06. Work stays 23:00–06:00, no new phase from 05:30; README/SVG
protected paths are unchanged. `provenance=synthetic`, `independently_reproduced=false`:
not model benchmarks, actual signature/payment interoperability, consent UI or legal
proof that a person agreed.

## 1. Protocol access and local approval are different facts

| Primary source | Supported architecture boundary |
|---|---|
| [Sierra's Poppy explanation](https://sierra.ai/blog/poppy) | Customers choose agent access and companies set parameters; the flight example confirms with the customer before booking |
| [Pinned Poppy version registry](https://github.com/personal-agent-protocol/personal-agent-protocol/blob/a95b757872533a6ef1e1a9bcf29802857d2e5ff4/content/versions/versions.json) | 0.2 published 2026-10-24; 0.3 has no published field; retrieval date is not a release |
| [Stripe: how agents work](https://docs.stripe.com/agents/how-it-works.md) | Developer tools, Billing and commerce are separate components; MCP tools do not independently handle billing/commerce |
| [SQLite transactions](https://www.sqlite.org/lang_transaction.html) | One simultaneous writer per file; BEGIN IMMEDIATE starts a write transaction, and BEGIN transactions do not nest |

Official Poppy HEAD remains `a95b757872533a6ef1e1a9bcf29802857d2e5ff4`
(2026-10-26), with no new release evidence. No Visa release was rechecked;
Stage 1659 TAP coverage and local admission remain separate gates.
Poppy session/account access, Stripe MCP permissions and TAP identity do not
automatically authorize a particular purchase.

## 2. Small asset and compatibility boundaries

[`PaymentApprovalStore`](../../lab/payment_approvals.py) is opt-in trusted-operator
metadata. `approve(operation, expires_at=...)` **records** an external trusted decision;
it neither authenticates the operator nor creates consumer consent.
Persist only tenant_id, approval_id, existing full-operation fingerprint, expires_at
and revoked. The fingerprint binds operation/approval/provider/account/key/checkout,
not just amount. No original JSON, JWT, Poppy token, signature or buyer identity is stored.

Records cannot be replaced, extended, reactivated or pruned through this API.
Repeated approve raises; revoking the same binding is idempotent and only returns
after commit. The older [`CheckoutStore`](../../lab/checkout.py) uses global
mandate IDs/simulated receipts; those rows are not automatically migrated or treated
as tenant/provider/operation-scoped approval.

`admit(...)` first reuses
[`validate_signed_checkout`](../../lab/checkout_admission.py), then requires
approval store and journal to have the **same resolved SQLite path**.
Different files reject, rather than concatenating separate transactions into a guarantee.

1. Acquire the local write transaction with `BEGIN IMMEDIATE`.
2. Load tenant/approval scope and exact operation fingerprint; reject missing,
   changed or revoked approval.
3. Invoke the required trusted clock; strictly validate nonnegative signed-64 integer
   time and persisted expiry.
4. Require `now < expires_at`, rejecting exact expiry.
5. Invoke the journal transaction participant and return its existing decision only
   after commit.

[`PaymentAttemptJournal`](../../lab/payment_attempts.py) only extracts
`_reserve_in_transaction`; old reserve idempotency/unknown/conflict contracts remain.
The participant rejects use outside a transaction. Stage 1660's original facade is
also preserved. The new facade requires valid approval on **every** use, even a
non-dispatch retry. After expiry/revocation, recover using independent `journal.read`,
not new operation/key identity. Standalone journal/SQL writes can still bypass this
opt-in guarantee; a historical reservation does not prove prior approval.

## 3. Runnable synthetic example

The signer, approval and clock are fixtures, not production consent UI or public-key
verification. A production callback must read fresh trusted time when invoked,
not capture an old request/model-provided timestamp.

```python
import json
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from lab.agent_identity_attestation_guard import compute_rfc9530_content_digest
from lab.checkout import Checkout
from lab.payment_approvals import PaymentApprovalError, PaymentApprovalStore
from lab.payment_attempts import PaymentAttemptJournal, PaymentOperation
from lab.request_binding import MUTATION_COMPONENTS, RequestSignatureSnapshot

now = 1700000000
operation = PaymentOperation(
    "tenant", "operation", "approval", "stripe:test", "acct_synthetic", "key",
    Checkout("synthetic-shop", "USD", "synthetic-sku", 2, 1000),
)
body = json.dumps(asdict(operation.checkout)).encode()
digest = compute_rfc9530_content_digest(body)
uri = "https://synthetic-shop.example/checkout?cart=one"
fixture = RequestSignatureSnapshot(
    "sig1", "synthetic-key", MUTATION_COMPONENTS,
    "POST", uri, "application/json", digest,
)
with TemporaryDirectory() as directory:
    path = Path(directory) / "commerce.sqlite3"
    journal, approvals = PaymentAttemptJournal(path), PaymentApprovalStore(path)
    approvals.approve(operation, expires_at=now + 60)
    request = dict(
        clock=lambda: now, expected_target_uri=uri, method="POST", target_uri=uri,
        content_type="application/json", content_digest=digest,
        content_encoding=None, body=body,
    )
    first = approvals.admit(journal, operation, fixture, **request)
    assert first.dispatch_allowed and first.attempt.outcome == "unknown"
    assert not approvals.admit(journal, operation, fixture, **request).dispatch_allowed
    approvals.revoke(operation)
    try:
        approvals.admit(journal, operation, fixture, **request)
    except PaymentApprovalError:
        pass
    else:
        raise AssertionError("revocation must reject further admission")
    assert journal.read(operation) == first.attempt
```

## 4. Races, time and AI-native architecture

If revocation commits first, later admission cannot grant new dispatch. If admission
commits first, revocation cannot delete unknown state or let an agent create another
key. A worker already holding a dispatch decision may still send it later.
Network effects are outside this SQLite transaction. Expiry is checked at the
post-lock time sample, not a physical deadline guarantee at commit/send. Clock
accuracy, pauses, cross-machine consistency, the database file and coherent backup/
restore remain deployment responsibilities.

Well-Architected is quality/trade-off guidance, not a Web three-tier topology.
Transactions and approval gates are established system techniques. AI-native risk
adds replanning workers packaging stale authority, old clocks or recovery as new
authorization. Put invariants on the actual effect-admission path and preserve
recoverable unknown outcomes, not merely consumer-consent instructions in a prompt.

Not implemented: signer/operator authentication, Poppy OAuth, consent UI/legal
proof, distributed revocation, provider cancellation/refund or payment dispatch.
History is not automatically pruned; growth and authorization lifecycle need
production design.

## 5. Validation scope

[`tests/test_payment_approvals.py`](../../tests/test_payment_approvals.py) adds
34 methods; 119 focused tests pass with checkout/admission/journal/atomic-readback.
Coverage includes exact expiry, revocation, full fingerprint, tenant scope, immutable
records, no legacy-mandate reuse, real fresh processes, concurrent admission/revoke,
and SQL tracing proving BEGIN was attempted before releasing a held lock.
Faults observe actual inserted/revoked state before failure: approve/revoke/reservation
commit failures return no success. Noninteger persisted expiry rejects explicitly.
All 3,968 repository tests, compilation, both existing demos, 89 local links and
two executable bilingual examples passed. Eight generated historical reports were
restored, not published as new benchmarks. README.md, README.en.md and assets/ have
zero diff from `1d9273d`. Final-commit CI/canonical-main synchronization remain
post-publication gates, not remote effects or consent authentication.
