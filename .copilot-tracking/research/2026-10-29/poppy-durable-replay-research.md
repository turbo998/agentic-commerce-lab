<!-- markdownlint-disable-file -->
# Stage 1658: durable Poppy Session assertion replay admission

## Scope and task requests
Caller 275 requests Stage 1658 from 292207f, bilingual research/offline assets,
full tests/CI/main and protected README/assets from 1d9273d. Research began at
02:06 BJT; no new phase from 05:30 and no work outside 23:00-06:00.
Focus: a durable, atomic Session assertion replay check, not an OAuth server.

## Research executed and evidence
Direct continuous trace; configured Researcher/Plan Validator/Implementor custom
agents were absent in prior stage. No redundant delegation or new orchestration.
- https://sierra.ai/blog/poppy reverified 2026-10-29: Company/Personal Agent
  interoperability, discovery, sign-in and cross-channel Session Tokens.
- Official repository HEAD remains a95b757872533a6ef1e1a9bcf29802857d2e5ff4
  (2026-10-26). content/versions/versions.json: 0.2 published 2026-10-24.
  content/shared/changelog.mdx: 0.3 explicitly In progress, not a released standard.
- Pinned content/versions/0.2/spec.mdx, sections 4.1/4.2: assertions target the
  exact auth.issuer; maximum lifetime five minutes; reject a reused jti from the
  same client_id until assertion expiry. Entropy is a producer requirement.
- Section 4.3 separately requires DPoP proof replay rejection at the token endpoint.
  DPoP proofs have an acceptance window, not this assertion exp contract; do not
  silently conflate their keys, verification or retention.
- lab/poppy_guard.py:2299-2347 already checks v0.2 audience/lifetime/jti and
  per-user DPoP-key isolation, but replay history is a caller-owned in-memory set.
  A new process or independent set forgets accepted assertions.
- SQLite single-writer transactions and commit/rollback contract verified in
  Stage 1657 at https://sqlite.org/lang_transaction.html.

## Key discoveries and selected approach
Extract the existing pure audience/lifetime/jti check from the v0.2 guard, leaving
its existing scope and in-memory replay/key-isolation behavior unchanged.
Add an opt-in SQLite journal consuming one already cryptographically authenticated
SessionAssertionClaims at a time, after external identity/authorization checks.
Bind configured Company auth.issuer and authenticated client_id. Key replay by
(auth.issuer, client_id, SHA256(jti)), deliberately not sub/session/key/type.
BEGIN IMMEDIATE and durable insert must precede return; duplicate raises an
explicit replay exception, storage errors propagate, no credential is issued.
Require strict integer times and a bounded base64url identifier as local policy;
length/alphabet do not prove 128 bits of randomness.
Keep consumed IDs without pruning: stronger retention than the minimum protocol
window, with an explicit bounded-reference/operational-growth limitation.

## Scenarios and alternatives
Chosen: local SQLite durable admission with pure metadata reuse, no historical
benchmark changes. Test restart, processes, concurrent same-ID admission, scope
isolation, unchanged history on invalid input/failed commit, and no secret storage.
Rejected: another in-memory set (restart/multi-worker gap), per-user/session keys
(can admit same-client replay), custom JWT/DPoP cryptography and guessed expiry GC.
Distributed stores, batch client+Session+DPoP atomic admission, actual token issuance
and signing-key/nonce/user-binding verification remain outside this increment.

## Open questions and risks
No blocking research gaps. Trusted issuer/client routing and authenticated decoded
claims are external. Backup rollback, malicious DB access, separate server-local
files and direct bypass defeat the local guarantee. A committed consume followed
by lost response/crash burns that assertion: retry with a fresh assertion, not
transparent idempotent success. Unbounded history needs a production retention design.
Token replay prevention is not business-operation idempotency or purchase consent.

## Potential next research and handoff
Future: shared production replay store and conservative retention bound to the
actual verifier's accepted window; do not implement pruning speculatively here.
Proceed to /rpi-plan with this dated artifact; implementation has not started.
Self-check: scope, task requests, evidence, discoveries, alternatives, risks,
follow-on research and handoff sections present; no executable validation yet.
