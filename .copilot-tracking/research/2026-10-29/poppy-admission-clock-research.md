<!-- markdownlint-disable-file -->
# Stage 1664 research: sample assertion admission time after the write lock

## Scope and request
Controller269 resumes c3c9702; actual start 03:47 BJT. Preserve bilingual/full
tests/compile/CI/non-force main and 1d9273d README/assets. Only 23:00-06:00,
no new phase from 05:30. Research Session assertion replay admission, not purchase
approval, client assertions, DPoP proof replay or token issuance.

## Research executed and dated evidence
03:47-03:49 BJT bounded trace inline; named Researcher Subagent absent.
- lab/poppy_replay.py consume validates externally supplied now before BEGIN
  IMMEDIATE. Queueing may outlive short exp; fixed caller snapshots cannot become
  fresh simply by moving the comparison. Preserve explicit fixed-now contract.
- lab/payment_approvals.py has the correct local prior art: required clock callable
  sampled after acquiring write lock, exclusive expiry and no commit-time guarantee.
- lab/poppy_guard.py lines2299-2311 already owns pure v0.2 metadata validation;
  reuse it, not another lifetime/audience policy.
- Official Poppy HEAD remains a95b757872533a6ef1e1a9bcf29802857d2e5ff4 (2026-10-26).
  Pinned content/versions/versions.json: 0.2 published2026-10-24; 0.3 no published.
- Pinned content/versions/0.2/spec.mdx: exact auth.issuer audience, exp at most
  five minutes after iat, same-client jti rejection until expiry; DPoP replay is a
  separate token-endpoint requirement, not the Session assertion store.
- Independently SHA256-hashed decoded spec bytes match the registry's spec hash:
  5f6ac40cb2c2114fe85ebe3f1c2fec8a2cbfc90f2a92a2bf44e6ce0e518e0a26.
  Do not confuse this content checksum with Git blob SHA1 or infer a new release.
- https://www.rfc-editor.org/rfc/rfc7519.html#section-4.1.4: current time before exp;
  small clock-skew leeway MAY be provided. Existing zero-skew, integral signed64
  and future-iat rejection are stricter local policy, not all JWT conformance.
- https://www.sqlite.org/lang_transaction.html: BEGIN IMMEDIATE can wait/fail when
  another writer exists, and one writer serializes local consumption.

## Selected approach and alternatives
Add explicit consume_with_clock(scope, assertion, clock=required_callable).
Acquire existing write transaction, invoke trusted clock, reuse existing complete
metadata/key validation, then same replay check/insert and commit before return.
Extract pure validated-key and private transaction participant so fixed-now consume
and new facade share all schema/namespace/retention logic. No schema migration.
Rejected: reuse stale request/model timestamp, optional clock fallback to time, new
TTL/replay implementation, auto-prune history or couple admission to a payment.
Old consume remains explicit fixed-now compatibility API; new method is opt-in.

## Scenarios, limits and open questions
Assertion expiring while blocked rejects without consuming ID. Assertions still
valid after waiting can consume; exact exp rejects. Failure to acquire lock never
calls clock; clock/storage/commit exceptions propagate without admission.
Legacy/new calls share one namespace and one winner. Clock must read fresh trusted
time when invoked, not capture a request value. Guarantee is at post-lock sample,
not physical commit/issuance time or distributed clock consensus.
JWT/DPoP/signature/client/user/session checks precede this independent gate.
No new token/payment authority, issuance, network, retention or permission change.
No blocking question. Distributed replay service/authenticated issuance deferred.

## Validation and planning handoff
SQL-trace the actual BEGIN attempt before changing time/releasing held lock;
test exact expiry, still-valid waiting, acquisition failure/no clock call, strict
scalar/lifetime boundaries, shared legacy scope/history, new process, concurrency,
clock exceptions and actual post-insert/commit rollback. Preserve existing Poppy tests.
Full suite/compile/demos, bilingual executable examples/links, protected paths and
final-SHA CI/canonical receipt gate release. Self-check: scope/request/evidence,
discoveries, alternatives/scenarios, risks/open questions and handoff checked.
No implementation during research. Proceed /rpi-plan with this artifact.
