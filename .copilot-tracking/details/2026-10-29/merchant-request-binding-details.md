<!-- markdownlint-disable-file -->
# Stage 1659 implementation details

## Context and requirements
Research: .copilot-tracking/research/2026-10-29/merchant-request-binding-research.md
Caller 269 requests Stage 1659 from 134c414: bilingual/offline/full tests/main,
unchanged permissions/model and protected 1d9273d README/assets.
Night-only work; no new phase from 05:30, save/verify/sync and exit before 06:00.

## Phase 1: one-signature snapshot and exact body binding
Add lab/request_binding.py: immutable trusted snapshot of one signature's label,
key ID, bare components and signed method/URI/type/digest values.
Require @method/@target-uri/content-type/content-digest coverage, exact current
values, POST/PUT/PATCH/DELETE, application/json, no Content-Encoding, bytes <=1 MiB.
Reuse compute_rfc9530_content_digest from lab/agent_identity_attestation_guard.py;
do not copy the historical HMAC signature builder or invent a general parser.
All invalid/unsupported values raise explicit errors. No journal/economic mutation.
Add tests/test_request_binding.py: independent .NET fixture, metadata/body
substitution, missing/parameterized/duplicate components, canonical profile,
exact body budget, snapshot immutability and no payment-journal update/dispatch.
Required focused run: existing identity attestation tests plus new module.

## Phase 2: bilingual boundary research and navigation
Create docs/research/2026-10-29-request-binding.md and .en.md with sources,
synthetic executable example, fixed local policy and trusted-verifier preconditions.
Append research/daily/2026-10-29.md and .en.md; update docs/stage-archive-index.md.
Distinguish local profile from Visa/RFC mandates, signatures from consent/payment,
and received-byte integrity from JSON semantic validation.

## Phase 3: integrated validation and release preparation
Full unittest discovery, compileall lab/scripts and both existing demos.
Execute bilingual examples; check changed local links and protected-path zero diff.
Restore only generated historical reports; fix introduced failures and record evidence.
Commit with coauthor and non-force push HEAD:main; verify final-SHA CI.
Controller 269 owns canonical fast-forward/clean/lock/protected-path confirmation.
Verify final refs/status/main..HEAD/branch hygiene; leave unrelated branches alone.
Dependencies: docs follow implementation; release follows all local validation.
