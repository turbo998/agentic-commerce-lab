<!-- markdownlint-disable-file -->
# Stage 1661 details

## Context
Research: .copilot-tracking/research/2026-10-29/approval-admission-research.md
Controller 269 continues from 238aa8c; preserve bilingual/main/full tests/CI and
1d9273d README/assets. Existing permissions/model and night-only gates unchanged.

## Phase 1: same-file approval and reservation
Extract PaymentAttemptJournal._reserve_in_transaction with active-transaction
guard; standalone reserve retains its original BEGIN/return/error behavior.
Extract validate_signed_checkout as pure reuse; keep old facade and guarantees.
Add PaymentApprovalStore in lab/payment_approvals.py: immutable tenant/approval/
operation fingerprint/expiry/revoked records, trusted approve, idempotent revoke,
and admit using strict same-resolved-file policy. No global mandate ID reuse.
admit validates signed checkout, then BEGIN IMMEDIATE, bound approval, active state,
trusted clock sampled after lock, strict now < expiry, then reserve participant.
Commit before returning; all failures explicit and rollback. Every new-facade retry
requires valid approval; independent journal.read remains recovery after expiry.
No actual consent UI, token verifier, provider call or distributed revocation.

## Phase 2: focused regression and transaction proof
Add tests/test_payment_approvals.py: metadata bounds, scopes/fingerprints, immutable
approvals, exact expiry/revocation, missing/legacy approval, signed/semantic input,
same-file refusal, real processes, concurrent admissions and revoke ordering.
Prove post-lock clock sampling and inject post-insert/commit/approve/revoke failures.
Run checkout-admission/checkout/payment-attempt/atomic-readback regressions.

## Phase 3: bilingual archive and integrated validation
Create docs/research/2026-10-29-approval-admission.md and .en.md with sources, synthetic
executable example and local-not-remote race semantics; append daily/index.
Full suite/fix iteration, compileall, both demos, examples/local links/protected paths.
Restore only generated historical reports. Non-force push with coauthor;
final-SHA CI/controller canonical receipt/final clean refs are runtime gates.
