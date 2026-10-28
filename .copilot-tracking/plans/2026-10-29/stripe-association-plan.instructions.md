---
applyTo: '.copilot-tracking/changes/2026-10-29/stripe-association-changes.md'
---
<!-- markdownlint-disable-file -->
# Stage 1663 plan: validate before the first PaymentIntent association

## Context, requirements and derived objective
Research: .copilot-tracking/research/2026-10-29/stripe-association-research.md
Details: .copilot-tracking/details/2026-10-29/stripe-association-details.md
Log: .copilot-tracking/plans/logs/2026-10-29/stripe-association-log.md
Controllers 278/269 request same stage from df5f6b5. One writer, canonical269.
Keep bilingual/full tests/compile/CI/non-force main and 1d9273d README/assets.
Only 23:00-06:00, no new phase from 05:30. Derived gap: validate complete provider
semantics before persisting a separately trusted first operation/reference mapping.

## Phases and prerequisites
- [x] Shared-validator association gate in existing observation module.
  Details: (Lines 9-17).
- [x] Focused bad-input, concurrency, persistence and rollback regressions.
  Depends on phase 1; Details: (Lines 19-25).
- [x] Bilingual archive and full validation/fix iteration/release preparation.
  Depends on phase 2; Details: (Lines 27-33).

## Risks, dependencies and success criteria
High-impact wrong association mitigated by separate expected reference, exact scope/
quote and same transaction as binding, not matching amount or mutable metadata.
Outcome confusion mitigated by pending-only first binding and no terminal downgrade.
Existing generic/reconcile paths remain compatible opt-in bypasses.
Authentication/freshness/correlation remain adapter responsibilities, not hidden
defaults. Standard library only, no sandbox/real payments/new permissions.
All local checks and protected paths pass; final-SHA CI/main/canonical receipt gate
completion after publication. External authenticated create/result provenance deferred.
