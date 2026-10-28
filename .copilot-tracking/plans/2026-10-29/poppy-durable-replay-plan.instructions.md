---
applyTo: '.copilot-tracking/changes/2026-10-29/poppy-durable-replay-changes.md'
---
<!-- markdownlint-disable-file -->
# Stage 1658 plan: durable Poppy Session assertion replay admission

## Requirements, context and derived objective
Source: controller 275's 02:06 BJT request from 292207f. Keep bilingual assets,
full tests/CI/main, protected 1d9273d README/assets, existing permissions/model
and 23:00-06:00 gate, with no new phase from 05:30.
Research: .copilot-tracking/research/2026-10-29/poppy-durable-replay-research.md
Details: .copilot-tracking/details/2026-10-29/poppy-durable-replay-details.md
Published Poppy 0.2 requires same-client assertion replay refusal. Existing
in-memory history does not survive restart; add an explicit durable opt-in path.

## Risks and mitigation
High-impact duplicate admission: one database writer transaction and uniqueness.
High-impact false authentication: no JWT/DPoP validity or token-issuance claims;
trusted caller validates those before consuming. Exclusions must remain prominent.
Same jti under a changed user/session must still reject. No guessed expiry GC:
retain IDs permanently, disclose growth and backup/distributed-state limitations.
Reuse pure checks and preserve historical APIs; do not rewrite old benchmarks.

## Checklist
- [x] Metadata extraction, journal and focused tests. Details: (Lines 10-22).
- [x] Bilingual evidence and navigation. Details: (Lines 24-28).
- [x] Integrated validation and release preparation. Details: (Lines 30-38).

Local phases complete. Final-SHA CI and controller canonical receipt remain
separate runtime gates; neither is claimed complete in this committed plan.

## Dependencies and success
Existing Python/SQLite only. Same issuer/client/jti has one winner across concurrent
connections/processes; faults never return success or leave partial admission.
Legacy Poppy tests, full suite, examples/links and protected-path checks pass.
Final-SHA CI and controller canonical receipt are separate runtime release gates.
Log: .copilot-tracking/plans/logs/2026-10-29/poppy-durable-replay-log.md
No code implemented in planning; handoff /rpi-implement.
