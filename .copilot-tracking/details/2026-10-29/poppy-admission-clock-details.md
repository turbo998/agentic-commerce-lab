<!-- markdownlint-disable-file -->
# Stage 1664 details

## Context and requirements
Research: .copilot-tracking/research/2026-10-29/poppy-admission-clock-research.md
Controller269 resumes c3c9702; bilingual/main/full tests/CI, protected README/assets
and 23:00-06:00/no new phase from05:30 unchanged.

## Phase 1: clocked assertion admission
Modify lab/poppy_replay.py: extract existing pure validated replay-key calculation
and private transaction participant, preserving fixed-now consume behavior.
Add consume_with_clock with required trusted callable. BEGIN IMMEDIATE first,
then sample clock, reuse complete metadata/key validation and replay insertion.
No clock fallback, schema/namespace/pruning change or token/economic operation.
Participant rejects autocommit. Return only after commit; exceptions propagate.
Acceptance: same metadata policy/history for legacy and new paths, no duplication.

## Phase 2: temporal ordering and failure evidence
Create tests/test_poppy_admission_clock.py with actual SQL-traced held-lock tests
for expiry/validity after waiting, exact expiry/lifetime/integer bounds, lock failure
without clock call, clock exceptions, shared legacy replay, scoped concurrency,
fresh process/minimal storage and actual insert/commit rollback.
Run existing Poppy replay and v0.2 metadata regressions together.
Acceptance: no ID burned by failed metadata/clock/storage, no success fallback.

## Phase 3: archive and integrated validation
Create bilingual docs/research/2026-10-29-poppy-admission-clock pair; append daily/
index. Cite checksum-verified published0.2, RFC7519 leeway and local stricter policy.
Full unittest discover, compileall lab scripts, both demos, links and executable
bilingual examples; restore generated reports and verify protected paths.
Fix introduced failures, exact-file commit/non-force main publication; final-SHA CI
and controller269 canonical clean/zero-lock/protected receipt gate completion.
