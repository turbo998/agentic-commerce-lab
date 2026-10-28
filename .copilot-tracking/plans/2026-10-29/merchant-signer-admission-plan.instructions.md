---
applyTo: '.copilot-tracking/changes/2026-10-29/merchant-signer-admission-changes.md'
---
<!-- markdownlint-disable-file -->
# Stage 1666 plan: serialize merchant signer permission with approval admission

## Context and requirements
Research: .copilot-tracking/research/2026-10-29/merchant-signer-admission-research.md
Details: .copilot-tracking/details/2026-10-29/merchant-signer-admission-details.md
Log: .copilot-tracking/plans/logs/2026-10-29/merchant-signer-admission-log.md
Controller269 resumes4b36f8c; preserve bilingual/full tests/compile/CI/non-force main
and1d9273d README/assets. Only23:00-06:00, from05:30 closeout only.
Derived objective: opt-in local signer revocation fencing, not signature verification.

## Phases and prerequisites
- [x] Shared existing approval core and scoped local signer facade.
  Details: (Lines 9-17).
- [x] Actual lock ordering, rollback, persistence and legacy regressions.
  Depends on phase1; Details: (Lines 19-27).
- [x] Bilingual archive and full validation/fix iteration/release preparation.
  Depends on phase2; Details: (Lines 29-35).

## Risks and success criteria
Trusted verifier authenticates keyid->key/algorithm/directory and signature times/
nonce; a scope or snapshot constructor does not. Trusted operator owns permissions.
Same-file local ordering only; earlier reservation cannot be undone or external send fenced.
Original approval/journal paths remain bypasses; old first-admission record never
proves this optional signer gate was used. No new provenance backfill or schema migration.
Signature expiry while queued is not solved. Distributed lifecycle/PKI/nonce deferred.
Standard library only. Focused/full checks, links/examples, report cleanup and protected
paths required; final-SHA CI/canonical/main hygiene are postpublication runtime gates.
