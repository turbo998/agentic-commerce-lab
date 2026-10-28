<!-- markdownlint-disable-file -->
# Stage 1662 changes

Plan: .copilot-tracking/plans/2026-10-29/admission-provenance-plan.instructions.md
Details: .copilot-tracking/details/2026-10-29/admission-provenance-details.md

## Phase 1
admission-provenance-2026-10-29-binding: complete.
Added immutable-by-API first-gate table/read model. Same transaction inserts only
on new reservation; retries and legacy reservations are not backfilled.
read_admission validates exact binding/stored times and does not check live approval
or grant authority. Named implementation/validation agents absent; bounded inline.

## Phase 2
admission-provenance-2026-10-29-focused: complete.
25 new methods / 144 focused tests pass in 3.537s, including actual two-write
visibility, post-write/commit rollback, true process persistence and legacy non-backfill.

## Phase 3
admission-provenance-2026-10-29-validation: local validation complete.
3,993 full tests (71.132s), compileall, both demos, 91 local links and two identical
executable bilingual examples pass. Ten regenerated historical reports restored.
Protected paths have zero diff from 1d9273d; no open implementation blocker.
Final-SHA CI/canonical clean/lock/protected receipt remain post-commit runtime gates.
