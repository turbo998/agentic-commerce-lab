<!-- markdownlint-disable-file -->
# Stage 1667 details

## Context and requirements
Research: .copilot-tracking/research/2026-10-29/merchant-signature-time-research.md
Resumee1144b1; bilingual/main/full tests/CI, protected README/assets and nightly
23:00-06:00/no new phase from05:30 unchanged. No general verifier or nonce service.

## Phase 1: same-signature time input and shared sampling
Add frozen TimedRequestSignatureSnapshot(signature,created,expires) in request_binding.
Pure require_signature_time checks wrapper/nested types, strict integer clocks,
nonnegative signed timestamps within SF Integer max999999999999999 and
created<=now<expires with created<expires. No invented max-age or skew fallback.
Merchant signer admit accepts bare/timed union, unwraps for existing validation;
timed path wraps required clock so one post-lock sample checks time and reaches
original approval core/history. Bare path behavior and all schemas unchanged.
Acceptance: no new entry point, second clock sample, copied gate logic or time persistence.

## Phase 2: temporal ordering, metadata and compatibility
Tests: exact created/expiry, future/inverted/zero/invalid/fifteen-digit boundaries,
wrong nested/outer input, failed clock and one invocation, actual blocked BEGIN
expiring/still-valid paths, shared time in admission history, post-write rollback.
Retain key/revoke/body/quote/path checks; stale retry cannot dispatch or erase history.
Bare compatibility, legacy bypass, concurrent one dispatch and no signature-time storage.
Run signer/approval/provenance/checkout/request/journal regressions together.
Acceptance: invalid/expired timed input never creates reservation/history.

## Phase 3: bilingual archive and integrated release gates
Document signed @signature-params provenance and local mandatory/zero-skew policy,
not universal RFC/TAP requirements. Preserve separate nonce/remote revoke boundaries.
Bilingual research/daily/index, full tests/compile/both demos/links/executable examples.
Restore generated reports, protect paths, validate line refs and fix introduced issues.
Exact-file commit/non-force main, final-SHA CI/count and controller269 canonical
clean/zero-lock/protected receipt gate completion, no automatic next stage.
