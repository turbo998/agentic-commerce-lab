<!-- markdownlint-disable-file -->
# Stage 1659: merchant mutation binding beyond TAP recognition

## Scope and task requests
Caller 269 resumes from 134c414 at 02:27 BJT. Preserve 1d9273d README/assets,
bilingual/offline/full validation/main rules and existing permissions/model.
No new phase from 05:30; no execution outside 23:00-06:00.
Research the exact request fields protected before a merchant mutation.

## Research executed and evidence
Direct continuous trace, no redundant delegation; configured custom research/
validator/implementor agents were absent in preceding stages.
- https://developer.visa.com/docs/trusted-agent-protocol reverified: TAP uses
  RFC 9421 signatures for trusted agent/intent/consumer/payment information.
- Official visa/trusted-agent-protocol HEAD remains
  16d59bdf3f8a542bc538d0962edbb80ea30a02af, dated 2025-10-28, not a new release.
  merchant-backend/app/security/signature_verification.py illustrates selected
  authority/path/header fields, not blanket whole-message coverage.
- RFC 9421 sections 3.2.1/7.2 distinguish application coverage requirements and
  multiple-signature confusion; a valid unrelated signature is insufficient.
- RFC 9530 sections 1.2/6.3: Content-Digest covers content, not authentication or
  authorization; Content-Type/Content-Encoding affect interpretation and integrity.
- lab/agent_identity_attestation_guard.py:99-101 already formats canonical
  sha-256 Content-Digest. Reuse it rather than add another hash/base64 codec.
  Its HMAC/directory/quota simulation is not an actual Visa signature verifier.
- Independent .NET SHA256 fixture, 02:29 BJT:
  body {"amount":1000,"currency":"usd"}
  hex a223b60dc6adbc2911e7c073889b220df1181c5534fa6be58c3a70981c354c54
  base64 oiO2DcatvCkR58BziJsiDfEYHFU0+mvljDpwmBw1TFQ=

## Discoveries and selected approach
Add a small opt-in local merchant JSON-mutation profile, not a TAP mandate:
one trusted verifier snapshot must cover bare @method, @target-uri,
content-type and content-digest. Snapshot captures exact signed values, label
and key ID. Compare actual method/URI/type/digest with that snapshot, then compare
the raw immutable body against the reused canonical SHA256 Content-Digest.
Require POST/PUT/PATCH/DELETE, exact application/json, no Content-Encoding and
at most 1 MiB. Parameters/trailers/multiple algorithms/normalization are outside
this deliberately narrow local profile. No flattening/union of signature coverage.
Actual RFC signature verification, trust/tag/time/nonce selection, raw-header
duplicate handling and faithful adapter construction are external preconditions.

## Alternatives and scenarios
Rejected: assuming authority/path protect query/body; digest without a signed
digest value; independently recomputing a new digest after tampering; unioning
unrelated signature labels; a hand-written Structured Fields/RFC 9421 parser.
Retain old historical guards unchanged; reuse only their pure digest formatter.
Test the independent vector, body and metadata substitutions, noncanonical header
forms, parameterized/duplicate components, exact 1 MiB threshold and no payment
journal mutation. Valid binding does not grant consent or new dispatch.

## Open risks and potential next research
No blocking evidence gaps. This helper cannot authenticate arbitrary Python
snapshots; never expose it as an agent tool. Trusted ingress must preserve original
bytes and derived URI, reject ambiguous headers and perform full RFC verification.
Production content coding, general structured-field support, API-specific economic
headers, consumer authority and business idempotency remain separate work.
No new Stripe/Sierra release verification or live requests/payments.

## Handoff and artifact self-check
Proceed /rpi-plan with this artifact. Research only; no implementation yet.
Checked scope, evidence, prior art, alternatives, constraints, risks and handoff.
