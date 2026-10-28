<!-- markdownlint-disable-file -->
# Stage 1666 research: local signer revocation and approval reservation

## Scope, request and success
Controller269 resumes4b36f8c; actual start2026-10-29 04:13 BJT.
Bilingual/full/focused/compile/CI/non-force main and1d9273d protected paths unchanged.
Only23:00-06:00, no new phase from05:30. Research an opt-in merchant-local signer
permission check with approval/reservation, not a Visa verifier or network revocation.
Success: committed local revoke first prevents this gate's next reservation; reserve
first is not undone. Preserve every old public entry point and first-admission history.

## Research executed and dated evidence
Bounded continuous trace inline; named Researcher Subagent not configured.
- lab/request_binding.py snapshot retains one verifier's key_id/label but only
  checks their format; provenance, key trust and lifecycle explicitly external.
- lab/checkout_admission.py validates snapshot/body/trusted quote, not key permission.
- lab/payment_approvals.py admit takes BEGIN IMMEDIATE then checks immutable
  approval/revocation/expiry, sampling one clock and reserving/history atomically.
  Extract this exact in-transaction core for reuse rather than nested public admit.
- https://developer.visa.com/docs/trusted-agent-protocol, retrieved04:15 BJT:
  merchants reconstruct signature base and verify agent public key; optional
  consumer/payment signatures do not merge identity with local purchase authority.
- Official Visa repository HEAD independently checked:
  16d59bdf3f8a542bc538d0962edbb80ea30a02af,2025-10-28T22:43:43Z.
  Pinned merchant-backend/app/security/signature_verification.py illustrates configured
  trusted-agent/public-key lookup and timestamp checks, not a merchant DB gate.
  Initial API base64 chunks printed wrapped source; joined/decode rerun confirmed
  actual lines before using evidence. No sample code copied.
- https://www.rfc-editor.org/rfc/rfc9421.html#section-3.2.1: application constraints
  can require appropriate keyid resolution, algorithms, age, nonce and tag.
- RFC9421 section7.3.4: mathematical signature validity alone does not establish
  appropriate key/algorithm for a message. Section7.3.2 covers key theft/rotation.
  Exact plaintext sections independently retrieved04:15 BJT.

## Selected alternative and boundaries
New MerchantSignerScope(tenant_id,merchant,target_uri,key_id), frozen trusted config,
and MerchantSignerStore with immutable allow bindings/irreversible revoke flags in shared SQLite.
No replacement/reactivation; revocation idempotent and only recorded scope can revoke.
Opt-in admit checks scope versus operation and the already-verified snapshot,
reuses signed-checkout validation, requires same resolved file for all three stores.
BEGIN IMMEDIATE, require exact scope record not revoked, then reuse extracted
approval participant, clock and first-reservation/history transaction. Commit before
return. Private approval participant rejects autocommit. No schema migration to old tables.
Reject alternatives: stale in-memory allowlist, separate check-then-reserve transaction,
duplicating approval/history policy, nested public transaction, modifying legacy
admit semantics or pretending a DB allow record verifies a signature.

## Risks, scenarios and open questions
This is merchant policy, not a new TAP/RFC mandate or complete revocation solution.
Trusted operator owns allow/revoke input; trusted verifier owns full signature/key/
algorithm/directory/time/nonce/client checks and stable keyid-to-key provenance.
Keyid alone is not public-key pinning; same keyid rebound externally defeats that
assumption. Snapshot construction, scope construction and local allow are not proof.
No signature-expiry recheck while queued; only local permission and approval expiry
are serialized. No remote directory sync, automatic key expiry, payment send or undo.
Old approval/journal APIs bypass this opt-in boundary. Existing read_admission proves
only approval-gate history, never signer-gate provenance; no backfill or new audit claim.
Missing/revoked/cross-tenant/merchant/route/key cannot reserve. Actual held lock proves
revoke commits before blocked admission. Reservation-before-revoke retains unknown.
Actual post-reservation/commit failures roll back attempt+history; concurrent admission
has one dispatch; reopen/subprocess preserves revoke. No blocking question.

## Follow-up and planning handoff
Authenticated directory/PKI lifecycle, signature-time/nonce atomicity and signed
signer-admission provenance deferred, not implied by this gate.
No implementation during research. Self-check: request/scope/evidence/discoveries,
alternatives/scenarios/risks/open questions/follow-up checked. No model benchmark.
Proceed /rpi-plan with this artifact.
