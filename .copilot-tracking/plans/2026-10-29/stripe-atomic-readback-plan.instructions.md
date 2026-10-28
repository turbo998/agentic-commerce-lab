---
applyTo: '.copilot-tracking/changes/2026-10-29/stripe-atomic-readback-changes.md'
---
<!-- markdownlint-disable-file -->
# Stage 1657 plan: atomic local readback acceptance

## Overview and user requirements
Close the stale-writer/partial-local-state gap with one SQLite transaction.
Source: controller 274's 01:36 BJT Stage 1657 request from e95d106: preserve
1d9273d README/assets, bilingual assets, full tests/CI/main, unchanged permissions,
night-only work with 05:30 closeout and 06:00 exit. No next stage is authorized.

## Context, derived objectives and risks
Research: .copilot-tracking/research/2026-10-29/stripe-atomic-readback-research.md
Details: .copilot-tracking/details/2026-10-29/stripe-atomic-readback-details.md
Reuse existing journal/observation/claim invariants. High-impact stale payment writes
are mitigated by validating active ownership before a shared-transaction update.
High-impact partial commits are mitigated by one connection/file and rollback tests.
Already-handled false success is mitigated by explicit refusal, not inferred replay.
Filesystem trust and externally authenticated/fresh retrieval remain outside scope;
no claim of remote atomicity, live payments or power-loss certification.

## Implementation checklist
- [x] Shared-transaction participants, coordinator and tests. Details: (Lines 10-21).
- [x] Bilingual evidence, compatibility and navigation. Details: (Lines 23-28).
- [x] Full validation, fixes and release preparation. Details: (Lines 30-37).

Local phases complete. Final-SHA CI and controller canonical receipt are
separate runtime gates; they were not yet available when this plan was committed.

## Dependencies and success
Existing Python/SQLite only; no dependency or scheduler changes.
Concurrent handoff cannot coexist with an accepted old generation; injected failures
leave both payment and claim unchanged. Existing standalone behavior remains covered.
Full suite, examples, links, protected paths, final-SHA CI and canonical receipt pass.
Log: .copilot-tracking/plans/logs/2026-10-29/stripe-atomic-readback-log.md
Handoff to /rpi-implement; no code implemented during planning.
