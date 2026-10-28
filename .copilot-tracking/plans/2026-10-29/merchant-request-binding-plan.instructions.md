---
applyTo: '.copilot-tracking/changes/2026-10-29/merchant-request-binding-changes.md'
---
<!-- markdownlint-disable-file -->
# Stage 1659 plan: exact merchant mutation request binding

## Requirements, context and derived objective
Source: controller 269's Stage 1659 request from 134c414, received 02:27 BJT.
Preserve bilingual/full tests/CI/main, 1d9273d README/assets and existing permissions/
model. Work 23:00-06:00 only, with no new phase from 05:30.
Research: .copilot-tracking/research/2026-10-29/merchant-request-binding-research.md
Details: .copilot-tracking/details/2026-10-29/merchant-request-binding-details.md
Derived objective: bind actual mutation fields/body to one trusted signature
snapshot; do not infer whole-request coverage from agent recognition.

## Risks and mitigation
High-impact unsigned body/metadata substitution: compare signed snapshot to current
method/URI/type/digest, then raw body to digest. No signature-label coverage unions.
High-impact false cryptographic claim: full RFC verification/key/tag/time/nonce
selection and raw-header handling remain external; the dataclass is not proof.
Resource growth bounded at 1 MiB. Strict canonical JSON-header profile avoids
hand-written structured-field parsing; unsupported valid RFC forms reject explicitly.
No historical guard changes, new dependency or authorization/dispatch side effects.

## Checklist
- [x] Snapshot/binding helper and focused regressions. Details: (Lines 10-21).
- [x] Bilingual evidence and navigation. Details: (Lines 23-28).
- [x] Integrated local validation and release preparation. Details: (Lines 30-37).

## Dependencies and success
Existing Python standard library and pure digest formatter only.
Independent fixture, exact 1 MiB boundary, substitution failures and no economic
mutation pass; legacy/full suites, demos/examples/links/protected paths pass.
Final-SHA CI and controller canonical receipt are runtime release gates.
Runtime release execution follows this locally completed preparation checklist.
Log: .copilot-tracking/plans/logs/2026-10-29/merchant-request-binding-log.md
No implementation during planning; handoff /rpi-implement.
