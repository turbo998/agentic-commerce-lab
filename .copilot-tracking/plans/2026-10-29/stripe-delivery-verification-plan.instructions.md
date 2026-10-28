---
applyTo: '.copilot-tracking/changes/2026-10-29/stripe-delivery-verification-changes.md'
---
<!-- markdownlint-disable-file -->
# Stage 1654 implementation plan

## Scope, evidence and constraints
Continue 6cdefcf with offline transport signature verification, not payment
authorization. Controller request: bilingual assets, tests, main sync, night
gate and protected README/assets from 1d9273d.
Research: .copilot-tracking/research/2026-10-29/stripe-delivery-verification-research.md
Details: .copilot-tracking/details/2026-10-29/stripe-delivery-verification-details.md

## Checklist
- [x] Raw-body verifier and focused tests. Details: (Lines 9-18).
- [x] Bilingual dated evidence/navigation. Details: (Lines 20-25).
- [x] Full local validation and release preparation. Details: (Lines 27-33).

## Risks, dependencies and success
Use standard-library HMAC, exact raw bytes and constant-time comparisons.
Local canonical-header/positive-tolerance/future-skew policy is stricter than
the pinned SDK, not a vendor compatibility claim. Verification does not
deduplicate events or prove current payment state. No network/secret storage.
All checks must pass, user paths unchanged, main published and CI verified.
Canonical sync is a controller-owned runtime release gate.
Log: .copilot-tracking/plans/logs/2026-10-29/stripe-delivery-verification-log.md
