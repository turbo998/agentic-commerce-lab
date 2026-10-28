# Stage 1662: A later approval lookup cannot prove an earlier admission

[中文](2026-10-29-admission-provenance.md) |
[Daily record](../../research/daily/2026-10-29.en.md) |
[Previous increment](2026-10-29-approval-admission.en.md)

**Finding:** an existing reservation plus a currently valid approval is not evidence
that the first reservation passed the approval gate. Persist a first-gate record
in the same transaction, and never backfill history from a later retry.
**The record is local application history, not authenticated consumer consent,
a cryptographic receipt, a network send or provider success.**

Resumed from `ef44ddf` at 03:22 Asia/Shanghai on 2026-10-29; sources checked
03:22–03:24. Work remains 23:00–06:00, with no new phase from 05:30.
`provenance=synthetic`, `independently_reproduced=false`: offline engineering fixtures,
not a model benchmark or actual Visa/Stripe/Poppy interoperability certification.
Protected README/SVG content is unchanged.

## 1. Three facts that should not collapse into one receipt

| Fact | What it establishes | What it does not establish |
|---|---|---|
| Current local approval | This trusted operator record currently admits this exact operation | A historical reservation used that gate |
| First-gate record | This local admission path created the first reservation at its sampled time | Who consented, real-time clock truth or a remote payment |
| Trusted provider readback | Provider-specific outcome under the existing reconciliation policy | Prior consumer consent or permanent settlement finality |

Primary evidence rechecked this round:

- [Stripe idempotent requests](https://docs.stripe.com/api/idempotent_requests):
  API v1 saves the first response after execution starts, including `500`; keys
  can be pruned after at least 24 hours, and reuse after pruning creates a new
  request. API v2 has different retry semantics. A provider key is not a permanent
  local approval ledger; this asset does not add provider retries or implement v2.
- [Stripe agent architecture](https://docs.stripe.com/agents/how-it-works.md):
  developer tools, Billing and commerce are separate components. Tool access is
  not purchase authority, historical authorization or payment evidence.
- [Sierra's Poppy explanation](https://sierra.ai/blog/poppy): customers choose
  access, businesses set parameters and the flight example confirms before booking.
  Session access and purchase approval remain different boundaries.
- [SQLite transactions](https://www.sqlite.org/lang_transaction.html): explicit
  transactions, one simultaneous writer and commit/rollback provide the local
  coupling. No nested public transaction or post-commit best-effort audit write.

No new protocol release or Visa publication was verified. Stage 1659 TAP request
binding and Stage 1658 Poppy assertion replay still have their independent scopes:
consuming a Session assertion is not a purchase admission.

## 2. Additive persistence, without invented migration history

[`PaymentApprovalStore`](../../lab/payment_approvals.py) now creates an empty
`payment_admissions` table when opening an existing database. It stores only:

`tenant_id, operation_id, fingerprint, admitted_at, expires_at`

The existing full-operation fingerprint binds tenant/operation/approval/provider/
account/idempotency key and Checkout. It is not anonymization or tamper evidence.
Tenant/operation identifiers may themselves be sensitive; use deployment access
controls and coherent backup/restore. No body, signature, token, approver identity
or provider response is copied into the record.

Within Stage 1661's existing same-file write transaction:

1. Validate signed checkout and active approval as before; sample trusted time
   after acquiring the write lock.
2. Reuse the journal reservation participant.
3. **Only if `dispatch_allowed=True`**, insert the first-gate fingerprint and that
   time/expiry snapshot on the same connection.
4. Return the decision only after commit. Insert/commit errors propagate, rolling
   back both writes; a conflicting existing record does not grant another dispatch.

Repeated admission retains the original time/expiry and returns no new dispatch.
Old direct reservations, old Stage 1661 reservations without records, and terminal
legacy attempts are **never backfilled**, even if approval now passes. Missing
history remains missing, rather than a silent or fabricated success.
The older journal and signed-checkout facades retain their bypass/compatibility
contracts; they do not automatically acquire this provenance.

`read_admission(operation)` returns frozen `ApprovalAdmission(fingerprint,
admitted_at, expires_at)` after exact binding and strict stored integer/time checks.
Missing or mismatched history raises `PaymentApprovalError`.
It does not inspect current approval, create authority, reserve, send, reconcile or
verify current journal outcome. Reads remain available after revocation/expiry.
Records have no update/delete API, but direct SQL or database replacement can alter
them; this is not a signed, tamper-evident audit ledger.

## 3. Runnable synthetic distinction: history versus current approval

The signature snapshot, clock and approval are trusted fixtures, not real crypto,
identity authentication or consumer consent.

```python
import json
from dataclasses import asdict, replace
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
uri = "https://synthetic-shop.example/checkout"
fixture = RequestSignatureSnapshot(
    "sig1", "synthetic-key", MUTATION_COMPONENTS,
    "POST", uri, "application/json", digest,
)
with TemporaryDirectory() as directory:
    path = Path(directory) / "commerce.sqlite3"
    journal, approvals = PaymentAttemptJournal(path), PaymentApprovalStore(path)
    request = dict(
        clock=lambda: now, expected_target_uri=uri, method="POST", target_uri=uri,
        content_type="application/json", content_digest=digest,
        content_encoding=None, body=body,
    )
    approvals.approve(operation, expires_at=now + 60)
    assert approvals.admit(journal, operation, fixture, **request).dispatch_allowed
    record = approvals.read_admission(operation)
    assert record.fingerprint == operation.fingerprint and record.admitted_at == now
    approvals.revoke(operation)
    assert approvals.read_admission(operation) == record
    assert journal.read(operation).outcome == "unknown"

    legacy = replace(operation, operation_id="legacy", approval_id="legacy",
                     idempotency_key="legacy")
    journal.reserve(legacy)
    approvals.approve(legacy, expires_at=now + 60)
    assert not approvals.admit(journal, legacy, fixture, **request).dispatch_allowed
    try:
        approvals.read_admission(legacy)
    except PaymentApprovalError:
        pass
    else:
        raise AssertionError("current approval must not invent prior gate history")
```

## 4. Architecture: preserve time-of-decision evidence, not prompt recollection

Well-Architected describes quality and trade-offs, not the Web three-tier topology.
Transactional audit records predate AI. AI-native workloads add a specific failure
mode: replanning workers can treat current permission as historical permission,
or summarize an `unknown` attempt into a fictional approved/successful action.
Keep authority, first-admission history and provider outcome as separately typed
facts on the actual effect boundary. Do not let a model generate missing records
or rotate idempotency keys to evade uncertain history.

No new worker/outbox/send path is introduced. Later revocation cannot withdraw a
committed reservation, and `admitted_at` is the post-lock sample, not the physical
commit/send time. Database integrity, clock trust, authenticated operators and
external audit retention remain production responsibilities.

## 5. Validation scope

[`tests/test_admission_provenance.py`](../../tests/test_admission_provenance.py)
adds 25 methods; all 144 focused tests pass with existing approval/checkout/
journal/atomic-readback regressions. Tests cover exact storage/full fingerprints,
zero/max integer boundaries, immutable first snapshots, no backfill on upgrade or
terminal legacy attempts, concurrent one-winner admission, fresh processes,
revoked/expired recovery, real SQL-before-failure and commit rollback.
A trigger observes both writes inside the transaction while independent readers
see neither; only committed history is exposed. Persisted noninteger times reject.
All 3,993 repository tests, compilation, both existing demos, 91 local links and
two identical executable bilingual examples passed. Ten generated historical
reports were restored, not published as new benchmarks. Protected README/assets
have zero diff from `1d9273d`. Final-SHA CI/canonical sync remain post-publication
gates, not claims of live payment results.
