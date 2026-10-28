<!-- markdownlint-disable-file -->
# Stage 1662 implementation details

## Context and requirement evidence
Research: .copilot-tracking/research/2026-10-29/admission-provenance-research.md
Controller 269 request: ef44ddf baseline, bilingual/full tests/CI/non-force main,
protected README/assets, 23:00-06:00 and 05:30 closeout.

## Phase 1: first-admission persistence
Modify lab/payment_approvals.py only: add frozen ApprovalAdmission read model
and payment_admissions table, created empty for existing databases.
Insert tenant/operation/fingerprint/admitted_at/expires_at only when the existing
transaction participant returns dispatch_allowed=True. Never backfill retries.
Add read_admission(operation): exact fingerprint and strict stored time validation,
explicit missing/conflict error, no current approval check or payment mutation.
Keep old admit return/approval/revoke semantics and shared connection/commit fence.
DD1: same-transaction write, not a second connection or post-commit log.
DD2: historical gate record only, no retroactive or authenticated consent claim.
Acceptance: preserved facades and no new provider calls/dependencies.

## Phase 2: focused failure and compatibility evidence
Create tests/test_admission_provenance.py. Check record shape/scopes/full bindings,
immutable first time/expiry, no backfill, revoke/expiry/reconcile read recovery,
actual process restart, concurrency, post-write rollback and commit failure.
Check empty-table upgrade, insertion conflict rollback and strict persisted types.
Run with existing approval/checkout/admission/journal/readback test modules.
Acceptance: prior 34 approval tests unchanged; exact storage and atomic writes proven.

## Phase 3: archive, validation and release preparation
Create docs/research/2026-10-29-admission-provenance.md and .en.md with sources,
bounded claims and self-contained examples. Append daily pair and stage index.
Run full unittest discover, compileall lab scripts, both demos, local link and
executable example checks; restore only generated historical report files.
Fix introduced failures. Verify protected paths, stage exact files, non-force
publish; final-SHA CI and controller canonical clean/zero-lock receipt gate completion.
