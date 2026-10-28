<!-- markdownlint-disable-file -->
# Stage 1658 implementation details

## Context and requirements
Research: .copilot-tracking/research/2026-10-29/poppy-durable-replay-research.md
Caller 275 requests Stage 1658 from 292207f: bilingual/offline/full tests/main,
unchanged model/permissions, protected 1d9273d README/assets, night-only work.
No new phase from 05:30; save/verify/synchronize and exit before 06:00.

## Phase 1: reusable metadata and durable admission
Extract pure v0.2 assertion audience/lifetime/jti validation from
lab/poppy_guard.py, preserving existing return/error behavior and memory-set flow.
Add lab/poppy_replay.py with trusted issuer/client scope and one-consume SQLite
journal. Validate exact client, Session typ, strict integer times and bounded local
base64url jti; reuse the extracted metadata check. One immediate transaction
rejects an existing issuer/client/jti digest or inserts before returning.
Persist no sub/session ID, JWT, DPoP proof, token, password or raw jti.
No pruning, clocks/crypto/signatures, OAuth response issuance or global rollout.
Add tests/test_poppy_replay.py for restart/new process, concurrent admission,
exact boundaries, scope isolation, invalid inputs, secret exclusion, commit rollback,
and replay denial across sub/session changes or a new later-valid assertion.
Required: run this suite with tests.test_poppy_guard.

## Phase 2: bilingual evidence and navigation
Create docs/research/2026-10-29-poppy-replay.md and .en.md with pinned 0.2 sources,
explicit 0.3 draft status, executable example, integration order and exclusions.
Append research/daily/2026-10-29.md and .en.md; update docs/stage-archive-index.md.
Distinguish assertion replay, DPoP replay, business idempotency and consumer consent.

## Phase 3: integrated validation and release preparation
Run full unittest discovery, compileall lab/scripts and both existing demos.
Execute bilingual examples; check changed local links and protected-path zero diff.
Restore only historical reports generated from this clean-baseline validation.
Resolve introduced failures and record inline validation evidence before publication.
Commit with coauthor; non-force push HEAD:main; verify final-SHA CI.
Controller 275 owns canonical fast-forward/clean/lock/protected-path confirmation.
Verify final refs/status/branch hygiene; leave unrelated branches untouched.
Dependencies: phases 2 and 3 follow implementation; publication follows validation.
