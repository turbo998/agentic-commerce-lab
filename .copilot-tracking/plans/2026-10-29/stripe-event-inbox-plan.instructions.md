---
applyTo: '.copilot-tracking/changes/2026-10-29/stripe-event-inbox-changes.md'
---
<!-- markdownlint-disable-file -->
# Stage 1655 plan: durable receipt does not authorize an economic effect

## Context and requirements
Continue the existing night research from 0ad9a5d. Caller asks Stage 1655,
bilingual assets, full local tests and origin/main, preserving user 1d9273d
README/SVG. Night gate: no research outside 23:00-06:00, no new phase after
05:30. Research: .copilot-tracking/research/2026-10-29/stripe-event-inbox-research.md
Details: .copilot-tracking/details/2026-10-29/stripe-event-inbox-details.md

## Derived objectives and risks
Persist verified routing hints before any future HTTP acknowledgment. Scoped
event identity must survive restart; it must not be a signature/body hash or a
claim of exactly-once payment. High-impact account routing ambiguity is mitigated
by trusted configured scope and rejection of Connect/organization context.
Byte changes are observable, not silently equated to an immutable business fact.
Use standard-library SQLite; no deployment, secrets or new dependencies.

## Checklist
- [x] Verifier-backed inbox and focused tests. Details: (Lines 9-21).
- [x] Bilingual dated research/daily/navigation. Details: (Lines 23-28).
- [x] Full project validation, fixes and release preparation. Details: (Lines 30-37).

## Success and release gates
Reopen/concurrency/rollback and no-payment-mutation assertions pass. Full suite,
compilation, demos, examples and local links pass. Protected paths remain zero
diff. Main publication, final CI and controller-owned canonical sync required.
Deferred: HTTP ACK, worker claim/completion, downstream economic idempotency,
other event types, thin/Connect/organization events and real provider retrieval.
Log: .copilot-tracking/plans/logs/2026-10-29/stripe-event-inbox-log.md
Handoff to /rpi-implement; no code implemented during planning.
