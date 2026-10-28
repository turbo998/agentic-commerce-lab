---
applyTo: '.copilot-tracking/changes/2026-10-29/merchant-signature-time-changes.md'
---
<!-- markdownlint-disable-file -->
# Stage 1667 plan: one post-lock sample for signature and approval time

## Context and requirements
Research: .copilot-tracking/research/2026-10-29/merchant-signature-time-research.md
Details: .copilot-tracking/details/2026-10-29/merchant-signature-time-details.md
Log: .copilot-tracking/plans/logs/2026-10-29/merchant-signature-time-log.md
Controller269 resumese1144b1. Bilingual/full tests/compile/CI/non-force main and
1d9273d protection unchanged. Only23:00-06:00, from05:30 closeout only.
Derived objective: opt-in authenticated time metadata, never a fake crypto verifier.

## Phases and prerequisites
- [x] Same-signature wrapper/pure time policy and clock composition.
  Details: (Lines 9-17).
- [x] SQL-observed temporal/metadata/failure and legacy regression evidence.
  Depends on phase1; Details: (Lines 19-26).
- [x] Bilingual archive and full validation/fix iteration/release preparation.
  Depends on phase2; Details: (Lines 28-34).

## Risks and success
Trusted verifier supplies times from same signature's authenticated parameters.
No constructor proves that; no unsigned/cross-label aggregation permitted.
Mandatory times/exclusive expiry/zero skew/nonnegative epochs are local profile.
SF Integer fifteen-digit bound is not signed64; trusted clock retains approval bounds.
Guarantee only at sample; nonce/crypto/remote lifecycle/consumer proof remain external.
Bare old input and legacy APIs bypass stronger time policy; route adapter must require it.
No new schema or signer/time provenance claim. Standard library only.
Focused/full checks, links/examples, report cleanup and protected paths required;
final-SHA CI/canonical/main hygiene are postpublication runtime gates.
