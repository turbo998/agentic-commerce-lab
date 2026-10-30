# Stage 1671: Scoped Poppy Assertion Replay History Lookup and Draft 0.3 Boundary

[中文](2026-10-30-poppy-replay-read.md) |
[Daily report](../../research/daily/2026-10-30.en.md) |
[Previous stage](2026-10-29-stripe-receipt-read.en.md) |
[Original replay journal](2026-10-29-poppy-replay.en.md) |
[Post-lock clock admission](2026-10-29-poppy-admission-clock.en.md)

**Finding:** Adding read-only `is_consumed(scope, jti)` to
[`PoppyAssertionJournal`](../../lab/poppy_replay.py) must query all three primary-key
columns `(auth_issuer, client_id, SHA256(jti))` via a single read-only `SELECT`.
**Returning `True` proves only that this local journal previously burned the `jti`
in that Company/client scope—never that a downstream token was issued or delivered.
Returning `False` never substitutes for atomic `consume` / `consume_with_clock`
under `BEGIN IMMEDIATE`, and grants no session, account, or payment authority.**

**Verified on 2026-10-30, 23:03–23:24 BJT from baseline `b494db6` (including Stage 1670 `3ecd71c`).**
`provenance=synthetic`, `independently_reproduced=false`: offline SQLite reference
asset, not a model benchmark, live JWT/DPoP verifier, OAuth server, or vendor certification.

## 1. Primary-Source Verification: Published 0.2 (`2026-10-24`) vs In-Progress Draft 0.3 (`3e9bada`)

During this window, upstream `personal-agent-protocol/personal-agent-protocol` advanced to commit
[`3e9bada9ec8f66777b43e429d49574131dc2f67e`](https://github.com/personal-agent-protocol/personal-agent-protocol/commit/3e9bada9ec8f66777b43e429d49574131dc2f67e)
(`Draft 0.3 (#112)`, committed `2026-10-29T14:36:58Z`):

- **Publication status verification**: At commit `3e9bada9ec8f66777b43e429d49574131dc2f67e`,
  [`content/versions/versions.json`](https://github.com/personal-agent-protocol/personal-agent-protocol/blob/3e9bada9ec8f66777b43e429d49574131dc2f67e/content/versions/versions.json)
  still records **Version `0.2` as `"published": "2026-10-24"`** (with frozen
  `content/versions/0.2/spec.mdx` content SHA-256
  `5f6ac40cb2c2114fe85ebe3f1c2fec8a2cbfc90f2a92a2bf44e6ce0e518e0a26`) and
  **Version `0.1` as `"published": "2026-10-09"`**, while **`0.3` has no `"published"` field**.
  [`content/shared/changelog.mdx`](https://github.com/personal-agent-protocol/personal-agent-protocol/blob/3e9bada9ec8f66777b43e429d49574131dc2f67e/content/shared/changelog.mdx)
  explicitly states: `"In progress, at /docs/spec. This list grows until 0.3 is published."`
  Accordingly, in-progress Draft `0.3` must not be cited as a published release, and durable
  Session assertion admission in this repository remains anchored to published `0.2` (§4.1/4.2).
- **Architectural shifts in Draft `0.3` vs invariant replay semantics**:
  - In published `0.2`, a Session assertion (`typ: "poppy-session+jwt"`) is sent to the OAuth
    Token Endpoint with `aud == auth.issuer` and `exp <= iat + 300`, and the Company rejects any
    repeated `jti` from the same `client_id`.
  - In in-progress Draft `0.3` (`content/versions/0.3/spec.mdx` §5.2–5.5 and
    `kit/company/patterns/session-header.md`), Sessions are decoupled from OAuth into a per-request
    `Poppy-Session` HTTP header (`poppy-session+jwt` carrying `pap_dlg: pap-delegation+jwt`),
    where the Company likewise rejects replayed `jti` values within its clock-skew window, and
    `operations` moves to v2 (`403 approval_required` + `Poppy-Approval` retry and `503 Retry-After`
    while in flight).
  - Across both versions, the specification requires the admission boundary to reject duplicate
    `jti` values; it never defines a local SQLite lookup API and never allows a replay-table read
    to bypass signature/expiry checks or prove that downstream issuance succeeded.

## 2. Scoped Read-Only Replay History Contract

[`PoppyAssertionJournal.is_consumed(scope, jti)`](../../lab/poppy_replay.py) complements
[`StripeEventInbox.read_receipt`](2026-10-29-stripe-receipt-read.en.md) and
[`PaymentApprovalStore.read_admission`](2026-10-29-admission-provenance.en.md):

1. **Strict pre-connection validation**: Reuses `_jti_key(scope, jti)` to require a validated
   `PoppyReplayScope` and a 22–256 character base64url ASCII `jti`. Invalid scopes or malformed
   `jti` values (`None`, `bool`, blank, out-of-range length, or non-base64url characters) raise
   `PoppyReplayError` before opening SQLite rather than silently returning `False`.
2. **Full 3-column primary-key read-only `SELECT`**: Hashes `jti` with SHA-256 and runs a single
   `SELECT 1 FROM poppy_assertion_replays WHERE auth_issuer=? AND client_id=? AND jti_sha256=?`
   without `BEGIN IMMEDIATE`, clock sampling, metadata verification, or state mutation.
3. **Explicit authority boundary**:
   - `False` means only that this `(auth_issuer, client_id)` scope has not committed that `jti`
     digest so far; using `is_consumed` as a pre-check before `consume` is vulnerable to TOCTOU
     races across concurrent workers and never replaces atomic `consume` / `consume_with_clock`.
   - `True` means only that the local admission transaction burned that `jti` (so recovery after
     a lost response or crash must mint a fresh `jti`), not that a token was issued or delivered.
   - SQLite lock or storage failures propagate directly instead of masquerading as `False`.

## 3. Executable Synthetic Example

Run from the repository root. This example exercises only local SQLite replay history lookup,
with no live JWT signing, network calls, or funds.

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from lab.poppy_guard import SessionAssertionClaims
from lab.poppy_replay import (
    PoppyAssertionJournal, PoppyReplayDetected, PoppyReplayScope,
)

with TemporaryDirectory() as directory:
    journal = PoppyAssertionJournal(Path(directory) / "replays.sqlite3")
    scope = PoppyReplayScope(
        "https://auth.company.example", "https://agent.example/client.json",
    )
    other_scope = PoppyReplayScope(
        "https://auth.other-company.example", scope.client_id,
    )
    assertion = SessionAssertionClaims(
        "poppy-session+jwt", scope.client_id, "synthetic-user",
        scope.auth_issuer, 1700000000, 1700000060,
        "synthetic_assertion_000001",
    )
    assert journal.is_consumed(scope, assertion.jti) is False
    journal.consume_with_clock(scope, assertion, clock=lambda: 1700000000)
    assert journal.is_consumed(scope, assertion.jti) is True
    assert journal.is_consumed(other_scope, assertion.jti) is False
    try:
        journal.consume(scope, assertion, now=1700000001)
    except PoppyReplayDetected:
        print("consumed history verified and replay rejected")
    else:
        raise AssertionError("expected replay rejection")
```

## 4. AI-Native Architecture Reflection and Validation Scope

In classic 3-tier web apps, an idempotency/replay table is often conflated with a "completed action"
flag. In AI-Native agentic commerce, where agent retries, worker handoffs, and protocol revisions
(such as Poppy `0.2` vs Draft `0.3`) occur across asynchronous boundaries, architects must separate
**"admission identifier burned (`jti` consumed)"** from **"credential issued or business operation
approved."** Read-only replay lookup supports post-crash diagnostics and recovery decisions
(confirming a burned `jti` requires a fresh assertion) without weakening atomic write-lock admission.

[`tests/test_poppy_replay_read.py`](../../tests/test_poppy_replay_read.py) adds **14 unit tests**
covering unconsumed `False` without burning the ID, visibility of both `consume` and
`consume_with_clock`, reopen and fresh-process persistence, Company/client scope isolation,
independent `jti` values within a scope, non-consumption on failed validation or rolled-back commits,
pre-connection rejection of invalid `scope`/`jti`, inclusive 22/256 length boundaries, storage error
propagation, and SQL trace verification of a single `SELECT` without writer locks or metadata checks.
