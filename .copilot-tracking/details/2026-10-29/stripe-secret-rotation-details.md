<!-- markdownlint-disable-file -->
# Stage 1665 details

## Context and requirements
Research: .copilot-tracking/research/2026-10-29/stripe-secret-rotation-research.md
Resume37b1e7e; bilingual/main/full tests/CI and protected paths unchanged.
Only23:00-06:00, no new phase from05:30. No real secrets or remote mutations.

## Phase 1: trusted overlap configuration
Extend existing verifier/inbox endpoint_secret annotation to str|tuple[str,...].
Normalize scalar to singleton; require nonempty tuple and validate every nonblank
string BEFORE signature matching. Do not ignore invalid trailing entries.
One parser and one timestamp/body policy; one HMAC per tried secret and compare
against v1 candidates. Keep result/schema unchanged and no lifecycle fallback.
Document one trusted endpoint/account/mode, control-plane retirement and compatibility.
Acceptance: old scalar behavior, explicit tuple overlap, error propagation.

## Phase 2: rotation and receipt regression
New test_stripe_secret_rotation.py covers key/signature order, retirement,
invalid configuration, strict malformed headers, byte mutation, exact time bounds,
verification before JSON/dedup/connection and no invalid-state persistence.
Prove re-signing dedups across restart/concurrency, scope isolation and minimal
storage/no secret returns, payment remains unknown and no new dispatch.
Run all existing delivery/inbox/claim/readback/association tests together.
Acceptance: additive rotation does not alter receipt identity or payment policy.

## Phase 3: bilingual archive and integrated release gates
Create research pair, append daily pair/index; distinguish existing one-key overlap
support from new multi-key config and remote expiry from local secret removal.
Full unittest, compileall, both demos, local links/executable bilingual examples.
Restore generated reports, protect paths, validate details/plan, fix introduced issues.
Exact-file commit, non-force main, final-SHA CI/count and controller269 canonical
clean/zero-lock/protected receipt gate completion; no automatic next stage.
