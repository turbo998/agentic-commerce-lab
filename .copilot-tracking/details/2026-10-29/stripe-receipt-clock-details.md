<!-- markdownlint-disable-file -->
# Stage 1669 details

## Context and requirements
Research: .copilot-tracking/research/2026-10-29/stripe-receipt-clock-research.md
Resumea8e908d; bilingual/main/full tests/CI/protected1d9273d paths unchanged.
Only23:00-06:00, no new phase from05:30. No live payments, new scheduler or workers.

## Phase 1: optional two-boundary receipt admission
Extract existing clock-config/time checks into shared private delivery helpers;
keep verifier validation/HMAC/time error ordering and positive/symmetric bounds.
New record_with_clock requires callable/trusted scope; ingress sample feeds existing
raw verification/JSON, then second sample after BEGIN rechecks verified timestamp.
Both facades share original receipt pipeline; old fixed-now path explicitly has
no admission callback. No repeated HMAC/JSON under lock, schema or receipt changes.
Acceptance:2 samples on success/duplicate; early failure never reaches storage.

## Phase 2: temporal ordering and compatibility
Actual blocked BEGIN crossing300/301, exact past/future boundaries, invalid second
clock/exception, initial stale or bad authentication/JSON/scope rejection.
Duplicate still rechecks; preserves original receipt/claim. Re-signing/rotation and
old fixed-now compatibility, two-sample call ordering/HMAC once, concurrency/reopen.
Real insert/commit failure rollback, payment journal unchanged. Run all Stripe
delivery/inbox/rotation/readback/association/observation regressions together.
Acceptance:no expired receipt admission/write; no new worker or economic authority.

## Phase 3: archive and full validation/release preparation
Bilingual research/daily/index plus historical inbox scope note. Explain extra
local freshness policy,2 boundaries,point-in-time not commit guarantee,unchanged
durable-worker lifecycle/ACK/secret config snapshot and old API bypass.
Full tests/compile/both demos/links/two identical examples, inspect/restore reports,
protect README/assets, verify line refs and fix introduced issues.
Final-SHA CI/count/non-force main/canonical receipt are postpublication runtime gates.
