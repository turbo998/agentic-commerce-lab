---
applyTo: '.copilot-tracking/changes/2026-10-29/stripe-receipt-read-changes.md'
---
<!-- markdownlint-disable-file -->
# Stage 1670 plan: scoped historical receipt reader

Research: .copilot-tracking/research/2026-10-29/stripe-receipt-read-research.md
Details: .copilot-tracking/details/2026-10-29/stripe-receipt-read-details.md
Log: .copilot-tracking/plans/logs/2026-10-29/stripe-receipt-read-log.md

- [x] Implement scoped SELECT reader and focused contract tests.
- [x] Bilingual research/daily/index, full validation and fix iteration.
  Depends on reader/tests.
- [x] Review/Discover and publication preparation.
  Depends on full validation.

Success: canonical ID/scope validation, full-key isolation, original receipt,
None absence, no writer/verification/worker/payment effects, storage errors surface.
Final-SHA CI/count/non-force main/canonical receipt are postpublication gates.
No new stage from05:30, no Stage1671; README/assets unchanged.
