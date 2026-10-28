# Stage 1658: Poppy assertion replay history must outlive a worker

[中文](2026-10-29-poppy-replay.md) | [Daily research](../../research/daily/2026-10-29.en.md) |
[Earlier authority boundaries](2026-10-28-authority-recovery.en.md)

**Verified 2026-10-29, Asia/Shanghai, starting 02:06; baseline `292207f`.**
`synthetic` offline engineering reference, not a model benchmark, OAuth server,
JWT verifier, protocol certification or new vendor release.

## 1. Published 0.2 is not the in-progress 0.3 draft

The official repository still resolves to commit
`a95b757872533a6ef1e1a9bcf29802857d2e5ff4` (2026-10-26).
Its [version registry](https://github.com/personal-agent-protocol/personal-agent-protocol/blob/a95b757872533a6ef1e1a9bcf29802857d2e5ff4/content/versions/versions.json)
records **0.2 published 2026-10-24**. The pinned
[changelog](https://github.com/personal-agent-protocol/personal-agent-protocol/blob/a95b757872533a6ef1e1a9bcf29802857d2e5ff4/content/shared/changelog.mdx)
explicitly calls 0.3 **In progress**; no new publication is inferred from this
night's access date. [Sierra's explanation](https://sierra.ai/blog/poppy) describes
discovery, sign-in, sessions and cross-channel Company access, not payment settlement.

The [published 0.2 specification](https://github.com/personal-agent-protocol/personal-agent-protocol/blob/a95b757872533a6ef1e1a9bcf29802857d2e5ff4/content/versions/0.2/spec.mdx),
sections 4.1/4.2, requires exact Company `auth.issuer` audience, an assertion lifetime
of at most five minutes, and same-`client_id` replay rejection until expiry.
The producer must generate at least 128 random bits for `jti`. A string's length
and alphabet cannot establish that entropy.

DPoP proofs have a **separate** replay requirement at the token endpoint (§4.3)
and a proof acceptance window. They are not Session assertions with `exp`.
This increment implements only durable Session assertion admission, not the
client-assertion or DPoP replay stores needed by a complete token endpoint.

## 2. Pure metadata checks are not durable admission

The existing [`poppy_guard`](../../lab/poppy_guard.py) has v0.2 metadata validation,
same-client replay and per-user DPoP-key isolation, but replay history lives in a
caller-owned memory set. Restarting a worker or using an independent set loses it.
The existing behavior remains supported; this is not a silent global upgrade.

[`PoppyAssertionJournal`](../../lab/poppy_replay.py) is an opt-in shared-local-file
path. It reuses the extracted pure metadata check, then consumes the key
`(Company auth.issuer, authenticated client_id, SHA256(jti))` in one SQLite
`BEGIN IMMEDIATE` transaction. Subject, session ID and signing-key changes cannot
create a new replay namespace for the same client. A duplicate raises
`PoppyReplayDetected`; storage errors propagate. Return occurs only after commit.
[SQLite's transaction contract](https://sqlite.org/lang_transaction.html) explains
the serialized writer boundary; it is not distributed authorization-server consensus.

Local input policy is deliberately stricter and bounded: canonical nonblank
configuration strings, exact Session assertion type/client, nonnegative
signed-64-bit integer times (never booleans), `iat <= now < exp`, and 22–256
base64url characters for `jti`. These bounds do not certify wire completeness,
randomness, signatures, authenticated identity or permission to access an account.

Only public issuer/client namespace and the ID digest are stored. No raw JWT,
`jti`, subject, session ID, DPoP proof, Account/Session Token or password is stored.
IDs are **not pruned**: even a later otherwise-valid assertion cannot reuse an old
ID. This exceeds the minimum retention window and grows without bound; production
retention, resource limits and a shared replay service require a separate design.

## 3. Executable synthetic example

Run from the repository root. The fixed identifier is a synthetic fixture, not a
production random-ID generator; no token, signature or network call is involved.

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from lab.poppy_guard import SessionAssertionClaims
from lab.poppy_replay import (
    PoppyAssertionJournal, PoppyReplayDetected, PoppyReplayScope,
)

with TemporaryDirectory() as directory:
    path = Path(directory) / "replays.sqlite3"
    scope = PoppyReplayScope(
        "https://auth.company.example", "https://agent.example/client.json",
    )
    assertion = SessionAssertionClaims(
        typ="poppy-session+jwt", iss=scope.client_id, sub="synthetic-user",
        aud=scope.auth_issuer, iat=1700000000, exp=1700000060,
        jti="synthetic_assertion_000001",
    )
    PoppyAssertionJournal(path).consume(scope, assertion, now=1700000000)
    try:
        PoppyAssertionJournal(path).consume(scope, assertion, now=1700000001)
    except PoppyReplayDetected:
        print("durable replay rejected")
    else:
        raise RuntimeError("replay was admitted")
```

[`Tests`](../../tests/test_poppy_replay.py) cover new-process rejection, independent
concurrent journals with one winner, issuer/client separation, changed subject/
session replay, exact timing/type/ID limits, invalid-input non-consumption, minimal
stored data, failed insert/connection and failed commit after the row was written.
All **42 focused tests** passed, including **26 new test methods**.

## 4. Integration order and AI-native architecture

The trusted application first validates discovery/issuer configuration, JWT
signature and algorithm, authenticated client, user/session ownership, other
assertions and DPoP proofs/nonces. It consumes the Session assertion only after
those checks and before credential issuance. This reference does not implement
those checks or atomically couple admission to issuing a credential. If a response
is lost or the process crashes after consume, the assertion is burned; recovery
needs a fresh authenticated assertion, not a success-shaped replay response.

Every cooperating worker must use the same local file. Separate files, bypassing
the journal, malicious database access or rolling back its history defeat this
guarantee; this is not a network-filesystem or multi-host deployment recipe.

Well-Architected qualities and Web three-tier topology are distinct. Durable replay
protection is an established requirement, not an AI invention. The AI-native
constraint is that replanning must not reset identity/authority history:
fresh assertions do **not** make a repeated business operation new or authorized.
Poppy account/session access, Visa trusted communication, Stripe payment observation,
business idempotency and consumer purchase consent remain separate boundaries.
No new Visa/Stripe release or cross-vendor interoperability was verified here.
