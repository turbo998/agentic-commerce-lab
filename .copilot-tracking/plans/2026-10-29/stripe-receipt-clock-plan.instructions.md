---
applyTo: '.copilot-tracking/changes/2026-10-29/stripe-receipt-clock-changes.md'
---
<!-- markdownlint-disable-file -->
# Stage 1669 plan: ingress and post-lock Stripe receipt time

Research: .copilot-tracking/research/2026-10-29/stripe-receipt-clock-research.md
Details: .copilot-tracking/details/2026-10-29/stripe-receipt-clock-details.md
Log: .copilot-tracking/plans/logs/2026-10-29/stripe-receipt-clock-log.md
Resumea8e908d with nightly/bilingual/main/protected rules unchanged.

## Phases and prerequisites
- [x] Shared time policy and required-clock receipt facade/pipeline.
  Details: (Lines 9-16).
- [x] Actual lock-time/duplicate/failure and legacy regression evidence.
  Depends on phase1; Details: (Lines 18-25).
- [x] Bilingual archive and full validation/fix iteration/release preparation.
  Depends on phase2; Details: (Lines 27-33).

## Risks and success
This is optional local receipt-admission freshness, not a Stripe protocol repair.
Exactly2 samples are intentional arrival/admission boundaries; no HMAC/JSON repeat.
Fresh callback/config trusted. Old API retains ingress-only semantics; no downgrade
fallback on new-path failures. Recheck before duplicate return and receipt writes.
No new schema/worker timeout/nonce,secret re-resolution,readback or payment authority.
Full/targeted/compile/demos/links/examples/protection required. Final CI/canonical
and main hygiene are runtime gates; no new phase after05:30.
