# Stage 1664: Assertion expiry must be sampled after waiting for the writer

[中文](2026-10-29-poppy-admission-clock.md) |
[Daily record](../../research/daily/2026-10-29.en.md) |
[Original replay asset](2026-10-29-poppy-replay.en.md) |
[Previous increment](2026-10-29-stripe-association.en.md)

**Finding:** a Session assertion valid before SQLite lock contention can expire
while waiting. A fixed caller `now` remains stale even if its comparison moves.
Add an explicit trusted-clock admission path that samples **after `BEGIN IMMEDIATE`
succeeds**, then validates metadata and consumes the replay key in that transaction.
**This is a post-lock sample guarantee, not a physical commit/token-issuance deadline.**

Resumed from `c3c9702` at 03:47 Asia/Shanghai on 2026-10-29; evidence checked
03:47–03:49. Work stays 23:00–06:00, no new phase from 05:30; README/SVG unchanged.
`provenance=synthetic`, `independently_reproduced=false`: offline engineering fixtures,
not model benchmarks, actual JWT/DPoP verification or protocol certification.

## 1. Pin published 0.2, not an in-progress draft

Official repository HEAD remains `a95b757872533a6ef1e1a9bcf29802857d2e5ff4`
(2026-10-26). The pinned
[registry](https://github.com/personal-agent-protocol/personal-agent-protocol/blob/a95b757872533a6ef1e1a9bcf29802857d2e5ff4/content/versions/versions.json)
records **0.2 published 2026-10-24**; 0.3 has no published field.
The [0.2 specification](https://github.com/personal-agent-protocol/personal-agent-protocol/blob/a95b757872533a6ef1e1a9bcf29802857d2e5ff4/content/versions/0.2/spec.mdx)
requires exact Company `auth.issuer` audience, at most five minutes from `iat` to
`exp`, and rejection of the same client's seen `jti` until expiry.
Producer entropy of at least 128 random bits is separate from checking string shape.

SHA-256 of the decoded specification bytes was independently computed and matched
the registry's published-page checksum:
`5f6ac40cb2c2114fe85ebe3f1c2fec8a2cbfc90f2a92a2bf44e6ce0e518e0a26`.
This is a document content checksum, not a Git blob SHA-1, assertion signature or
new release announcement.

[RFC 7519 §4.1.4](https://www.rfc-editor.org/rfc/rfc7519.html#section-4.1.4)
requires time before `exp`, while permitting small clock-skew leeway.
This lab retains its stricter **zero-skew, integral signed-64-bit,
`iat <= now < exp`** local policy. It does not claim that generic JWT forbids
fractional NumericDates or requires this future-`iat` policy.
[SQLite's transaction contract](https://www.sqlite.org/lang_transaction.html)
explains why `BEGIN IMMEDIATE` can wait or fail behind another writer.
The protocol does not mandate SQLite or this specific locking implementation.

DPoP proof replay at the token endpoint is a **separate** obligation. Session
assertion lifetime is not Session/Account Token lifetime, purchase consent or a
payment-operation TTL. No new Visa/Stripe release was checked.

## 2. One metadata policy and one durable replay history

[`PoppyAssertionJournal.consume_with_clock`](../../lab/poppy_replay.py) requires
`clock: Callable[[], int]`, with no fallback to a request timestamp or system clock.

1. Require a callable, then acquire the existing local write transaction.
2. Invoke the clock **after** acquiring the write lock.
3. Reuse the complete existing metadata/key validator: type/client, exact audience,
   strict times/lifetime and local bounded base64url `jti`.
4. Reuse the same transaction participant to reject or insert the scoped key.
5. Return only after commit; clock, lock, validation, storage and commit failures
   propagate rather than turning into successful admission.

The callback must read fresh trusted time **when invoked**, not return an old
request/model-selected or captured timestamp. Clock accuracy and rollback,
database integrity and coherent backup/restore remain deployment responsibilities.
Pauses after sampling can cross expiry; this API does not prevent that or
atomically issue a credential.

The original `consume(..., now=...)` remains a fixed-snapshot compatibility API,
including its validation-before-lock behavior. Use the explicit new method when
lock waiting must not preserve stale admission time. Both paths share the same
validation/key calculation and replay participant; no schema migration, new replay
namespace, pruning or retention change. Calls through either path consume the
same `(Company issuer, authenticated client, SHA256(jti))` key.

Only namespace and digest remain persisted; not time, raw `jti`, user/session,
JWT, DPoP proof or token. IDs remain permanently retained by this local API.
The private participant requires an active transaction and is not an agent tool.
Bypassing this gate or using separate files defeats coordinated replay history.

## 3. Runnable synthetic example

The mutable clock and predictable IDs are fixtures, not a production clock or
random-ID generator. External signature/client/user/session/proof checks are assumed.

```python
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from lab.poppy_guard import SessionAssertionClaims
from lab.poppy_replay import (
    PoppyAssertionJournal, PoppyReplayDetected, PoppyReplayError, PoppyReplayScope,
)

current = [1700000000]
scope = PoppyReplayScope("https://auth.company.example", "https://agent.example/client.json")
assertion = SessionAssertionClaims(
    "poppy-session+jwt", scope.client_id, "synthetic-user", scope.auth_issuer,
    current[0], current[0] + 60, "synthetic_assertion_000001",
)
with TemporaryDirectory() as directory:
    journal = PoppyAssertionJournal(Path(directory) / "replays.sqlite3")
    journal.consume_with_clock(scope, assertion, clock=lambda: current[0])
    try:
        journal.consume(scope, assertion, now=current[0])
    except PoppyReplayDetected:
        pass
    else:
        raise AssertionError("both facades must share durable replay history")
    current[0] = assertion.exp
    expired = replace(assertion, jti="synthetic_assertion_000002")
    try:
        journal.consume_with_clock(scope, expired, clock=lambda: current[0])
    except PoppyReplayError:
        pass
    else:
        raise AssertionError("exact expiry must reject admission")
```

## 4. AI-native architecture: queueing must not freeze authority time

Well-Architected describes quality/trade-offs, not Web three-tier topology.
Fresh time and transactional replay protection are established techniques.
AI-native planners add retries, queued workers and resumptions that may package
old authority or timestamps as fresh. Keep timing on the durable admission boundary,
not inside the model's narrative or an old request context.

Authenticated discovery/JWT algorithms/signatures/client/user/session association,
other assertions, DPoP proof/nonce checks and token issuance remain outside this
reference. A crash or lost response after consume burns the assertion; recover with
a fresh authenticated assertion, not a success-shaped replay response.
Fresh Session assertions still do not authorize a repeated purchase or replace
Stripe business idempotency, Visa communication identity or scoped local approval.

## 5. Validation scope

[`tests/test_poppy_admission_clock.py`](../../tests/test_poppy_admission_clock.py)
adds 20 methods; all 62 focused Poppy tests pass with original replay/metadata tests.
SQL tracing signals the actual `BEGIN IMMEDIATE` attempt while a writer holds the
lock: clock is uncalled while waiting, then exact expiry rejects or still-valid
time admits after release. Lock failure never calls the clock.
Coverage also includes strict scalar/lifetime/time endpoints, old/new one-winner
concurrency, scopes, true fresh process, minimal storage, clock exceptions and
actual post-insert/commit rollback. Covered failures leave the ID unconsumed.
All 4,042 repository tests, compilation, both existing demos, 109 local links and
two identical executable bilingual examples passed. Ten generated historical
reports were restored, with no report content staged. Protected README/assets have
zero diff from `1d9273d`. Final-SHA CI/canonical synchronization remain
post-publication gates, not token issuance or payment evidence.
