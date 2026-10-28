<!-- markdownlint-disable-file -->
# Stage 1668 details

## Context and requirements
Research: .copilot-tracking/research/2026-10-29/timed-signer-history-research.md
Resume15fae33, preserve bilingual/main/full tests/CI and1d9273d paths.
Only23:00-06:00, no new phase from05:30. Trusted adapter/database remain prerequisites.

## Phase 1: additive first-timed-admission history
Frozen TimedSignerAdmission holds fingerprint, exact frozen scope, selected label,
created/expires and admitted_at. Add empty merchant_timed_admissions table at store
construction; read_timed_admission(operation) checks full binding and stored metadata,
independent of current clock/revocation. Missing/mismatched/malformed records error.
Capture existing timed clock's single post-lock sample, insert only on NEW timed
reservation in same connection after original approval participant succeeds.
Bare and all existing-return/legacy/retry paths never insert, overwrite or backfill.
Acceptance: no new clock/public transaction/crypto claim; approval/journal unchanged.

## Phase 2: history, ordering and rollback evidence
Test first row/frozen/binding/tenant separation/reopen/fresh process, unchanged first
scope/key/label/window on retry, revoked/expired read versus admission, old bare/
generic/terminal attempts and empty-table upgrade with no backfill.
Actual blocked BEGIN and concurrency use one sample/one row. Trigger failure at final
insert and commit/post-write failures prove attempt+approval+signer all3-or-none.
Stored bad scalars/window/scope/label fail explicitly; read never calls clock.
Rename old no-new-schema test to reflect its constructor/admission lifecycle assertion.
Run all original signer/time/approval/request/quote/journal focused regressions.

## Phase 3: bilingual archive and integrated release preparation
Document local execution record versus independent signature/payment/consumer proof;
absence is not rejection, no nonce or tamper resistance/retention automation.
Research pair/daily/index plus historical Stage1667 scope note. Full tests/compile/
demos/links and identical examples, inspect/restore generated reports, protect paths.
Verify line references, fix introduced issues and prepare exact-file commit.
Final-SHA CI/count, non-force main and actual controller269 canonical receipt remain
separate postpublication runtime gates, not prepublication claims.
