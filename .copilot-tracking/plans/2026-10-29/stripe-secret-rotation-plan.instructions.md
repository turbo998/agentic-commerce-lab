---
applyTo: '.copilot-tracking/changes/2026-10-29/stripe-secret-rotation-changes.md'
---
<!-- markdownlint-disable-file -->
# Stage 1665 plan: trusted endpoint secret overlap

## Context and requirements
Research: .copilot-tracking/research/2026-10-29/stripe-secret-rotation-research.md
Details: .copilot-tracking/details/2026-10-29/stripe-secret-rotation-details.md
Log: .copilot-tracking/plans/logs/2026-10-29/stripe-secret-rotation-log.md
Controller269 resumes37b1e7e. Existing single-key multi-v1 overlap already works;
this is an additive local trusted-config extension, not a Stripe protocol repair.
Preserve bilingual/full tests/compile/CI/non-force main and1d9273d README/assets.
Only23:00-06:00; from05:30 closeout only. Standard library, no remote access/keys.

## Phases and prerequisites
- [x] Shared verifier and inbox tuple configuration.
  Details: (Lines 9-16).
- [x] Rotation/configuration and scoped receipt regression evidence.
  Depends on phase1; Details: (Lines 18-25).
- [x] Bilingual archive and full validation/fix iteration/release preparation.
  Depends on phase2; Details: (Lines 27-33).

## Risks, dependencies and success criteria
Trusted adapter selects all keys for one endpoint/account/mode, never a request.
All configured values validated before any match; no broad catches or empty fallback.
No secret lifecycle/distribution, implicit24h expiry, automatic retry or payment send.
Remote expiration does not remove a retained local key. Raw bytes/time/header policy
and receipt schema/identity remain unchanged; authenticated readback still required.
Focused/full checks, links/examples, report cleanup/protected paths required.
Final-SHA CI/canonical/main hygiene are postpublication runtime gates.
Distributed lifecycle convergence, thin events and Connect remain deferred.
