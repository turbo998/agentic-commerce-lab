---
applyTo: '.copilot-tracking/changes/2026-10-29/approval-admission-changes.md'
---
<!-- markdownlint-disable-file -->
# Stage 1661 plan: atomic local approval admission

## Context and requirements
Continue from 238aa8c under controller 269's 03:01 BJT request. Bilingual/main/
full tests/CI and protected 1d9273d README/assets unchanged. Work only 23:00-06:00,
no new phase from 05:30. No new permissions, model or automation.
Research: .copilot-tracking/research/2026-10-29/approval-admission-research.md
Details: .copilot-tracking/details/2026-10-29/approval-admission-details.md

## Phases and prerequisites
- [x] Same-file approval store and shared validation/reservation participants.
  Details lines 9-20.
- [x] Focused legacy regressions, races and rollback proof.
  Depends on phase 1; details lines 22-27.
- [x] Bilingual archive and full local validation/fix iteration/release preparation.
  Depends on phase 2; details lines 29-34.

## Risk controls and acceptance
Never nest public reserve transactions or compare approval on a separate connection.
Sample the required trusted clock only after write lock, reject exact expiry.
Approval fingerprint binds full existing immutable operation; no renewal/reactivation.
Revocation before admission wins; later revocation cannot undo a committed decision
or remote effect. New facade strictly checks approval even on retries; journal.read
is separate recovery, and old APIs remain opt-in bypasses, not silently upgraded.
No consent proof/UI, signer authentication, physical-clock guarantee or network send.
Successful return only after commit; targeted/full tests, demos/examples/links and
protected paths pass. Final-SHA CI, controller canonical receipt and main hygiene
are required post-commit runtime gates before task completion.
