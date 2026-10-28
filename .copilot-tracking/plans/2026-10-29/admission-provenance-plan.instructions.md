---
applyTo: '.copilot-tracking/changes/2026-10-29/admission-provenance-changes.md'
---
<!-- markdownlint-disable-file -->
# Stage 1662 plan: retain first-admission provenance without inventing consent

## Context and requirements
Controller 269's 03:21 BJT request resumes ef44ddf. Preserve bilingual/full tests/
compile/CI/main and 1d9273d README/assets. Only 23:00-06:00; no new phase from 05:30.
Research: .copilot-tracking/research/2026-10-29/admission-provenance-research.md
Details: .copilot-tracking/details/2026-10-29/admission-provenance-details.md
Log: .copilot-tracking/plans/logs/2026-10-29/admission-provenance-log.md

## Derived objective and phases
Current approval cannot reconstruct historical admission. Retain the local first
gate record in the same reservation transaction without backfilling legacy state.
- [x] First-admission table/read model and transactionally coupled insertion.
  Details: (Lines 9-19).
- [x] Focused record/race/rollback/process/legacy regressions.
  Depends on phase 1; Details: (Lines 21-27).
- [x] Bilingual archive and full validation/fix iteration/release preparation.
  Depends on phase 2; Details: (Lines 29-35).

## Risks, dependencies and success criteria
High-impact false authority is mitigated by no retry/legacy backfill and explicit
missing history. Atomic loss risk is mitigated by existing same-file transaction,
post-write/commit fault tests and return only after commit. Existing API compatibility
is mandatory. Trusted DB/coherent backups/clock remain deployment assumptions;
external tamper evidence and consent authentication deferred. Standard library only.
Local full/focused checks and protected paths pass; final-SHA remote CI, non-force
main and canonical clean/zero-lock receipt are required runtime gates after commit.
