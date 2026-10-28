<!-- markdownlint-disable-file -->
# Stage 1667 research: signed time metadata at the admission clock sample

## Scope, request and success
Controller269 resumese1144b1; actual start2026-10-29 04:28 BJT.
Bilingual/full/focused/compile/CI/non-force main and1d9273d protection unchanged.
Only23:00-06:00, no new phase from05:30. Narrow optional time-aware input to the
existing merchant signer gate, not a general RFC parser/verifier or replay service.
Success: one post-lock trusted clock sample checks both signature window and
approval expiry before reservation/history. Preserve bare snapshot compatibility.

## Research executed and evidence
Bounded continuous trace inline; named Researcher Subagent not configured.
- lab/merchant_signers.py explicitly defers signature expiry while queued.
- lab/payment_approvals.py private participant calls clock once after lock and
  approval binding/revocation checks; returned now becomes admitted_at.
- lab/request_binding.py snapshot holds one verified signature's values/components,
  not signed creation/expiration metadata; frozen construction is not authentication.
- RFC9421 plaintext retrieved04:29 BJT:
  section2.3 includes created/expires as integer UNIX signature parameters,
  @signature-params REQUIRED in base and NOT enumerated as a covered component;
  each signature has its own parameters, never union timestamps across labels.
  section2.5 details base serialization; section3.2.1 allows application age/expiry
  requirements; section7.2.2 distinguishes limited replay utility from nonce detection.
- RFC8941 section3.3.1 retrieved04:30: Structured Field Integer max999999999999999,
  not signed64 max. Decoded created/expires must respect this bound.
- Visa official HEAD checked04:29 remains16d59bdf3f8a542bc538d0962edbb80ea30a02af,
  2025-10-28T22:43:43Z. No new vendor release.
Sources: https://www.rfc-editor.org/rfc/rfc9421.html
and https://www.rfc-editor.org/rfc/rfc8941.html#section-3.3.1 .

## Selected alternative
Frozen TimedRequestSignatureSnapshot(signature,created,expires) wraps ONE trusted
preverified snapshot with that SAME signature's authenticated parameters.
Pure require_signature_time validates wrapper/nested type, strict nonnegative
created/expires Integer bounds and created<=now<expires with created<expires.
Trusted now is strict nonnegative signed64 integer, as existing approval policy.
No clock skew, max-age cap or protocol-specific lifetime invented.
Existing merchant admit accepts bare OR timed snapshot. Unwrap once for original
scope/body/quote validation; timed input wraps the required clock callable so its
ONE post-lock sample checks the window and is returned to the original approval core.
No optional timestamp default/fallback, new entry point, transaction or history schema.
Rejected: reuse pre-lock ingress now, second independent clock sample, detached
unsigned times, union unrelated labels, add @signature-params to covered_components,
alter bare old API, pretend constructor verifies signature or implement a full parser.

## Risks, scenarios and open questions
Mandatory created+expires, nonnegative epochs and zero-skew exclusive expiry are
this optional local profile, not every RFC/TAP signature requirement. Missing
parameters must not be fabricated by adapter; route deployments must require timed
inputs if they need this stronger policy. Bare compatibility path is a bypass.
Adapter owns full crypto/keyid/directory/algorithm/nonce and same-signature metadata
provenance. Struct construction cannot detect forged or cross-labelled metadata.
Fresh clock must sample when called. Guarantee at sample, not commit/send deadline.
No nonce consumption, remote key revoke, consumer proof, payment send or signer
provenance. Existing approval history does not prove timed-signature execution.
Actual blocked BEGIN tests: expire at boundary while waiting -> no reservation;
still-valid after wait -> same time in approval history; one clock invocation.
Malformed metadata/clock, key/scope/quote/revoke, post-write rollback and old paths
must remain explicit. No blocking question.

## Follow-up and handoff
Authenticated wire adapter, distributed clock/lifecycle and atomic nonce/history
remain separate follow-up. No implementation during research. Self-check:
scope/request/evidence/discoveries/alternatives/scenarios/risks/open questions checked.
Proceed /rpi-plan with this artifact; no model benchmark report.
