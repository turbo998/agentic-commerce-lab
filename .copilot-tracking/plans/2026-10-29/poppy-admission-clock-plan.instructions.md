---
applyTo: '.copilot-tracking/changes/2026-10-29/poppy-admission-clock-changes.md'
---
<!-- markdownlint-disable-file -->
# Stage 1664 plan: assertion time is sampled after the write lock

## Context, requirements and derived objective
Research: .copilot-tracking/research/2026-10-29/poppy-admission-clock-research.md
Details: .copilot-tracking/details/2026-10-29/poppy-admission-clock-details.md
Log: .copilot-tracking/plans/logs/2026-10-29/poppy-admission-clock-log.md
Controller269 resumes c3c9702; bilingual/full tests/compile/CI/non-force main,
1d9273d README/assets unchanged. Only23:00-06:00; no new phase from05:30.
Derived objective: opt-in live time after locking, not stale caller/request snapshot.

## Phases and prerequisites
- [x] Shared key/transaction participant and required-clock facade.
  Details: (Lines 9-16).
- [x] SQL-observed timing, failures and legacy Poppy regressions.
  Depends on phase1; Details: (Lines 18-24).
- [x] Bilingual archive and full validation/fix iteration/release preparation.
  Depends on phase2; Details: (Lines 26-32).

## Risks, dependencies and success criteria
Expired admission while queued mitigated by post-lock clock and exact-expiry test.
Policy drift mitigated by shared original metadata/key/namespace code.
Clock authenticity/accuracy remain explicit trusted dependency, not a model value.
This only checks at sampling, not physical commit/issuance deadline. No JWT/DPoP/
client/session authentication, issuance, payment or distributed replay claim.
Standard library only. Fixed-now compatibility path remains explicitly documented.
Full/focused checks and protected paths pass; exact-SHA CI and canonical receipt
are post-publication runtime gates. Distributed auth/retention deferred.
