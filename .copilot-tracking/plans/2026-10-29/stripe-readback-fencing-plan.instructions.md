---
applyTo: '.copilot-tracking/changes/2026-10-29/stripe-readback-fencing-changes.md'
---
<!-- markdownlint-disable-file -->
# Stage 1656 plan: explicit readback handoff with local generation fencing

## Requirements and context
Caller requests Stage 1656 from cac1ae6, bilingual assets, full tests/CI/main,
protected README.md/README.en.md/assets from 1d9273d, and night-only execution.
No new phase from 05:30; stop before 06:00. No new automation/permissions.
Research: .copilot-tracking/research/2026-10-29/stripe-readback-fencing-research.md
Details: .copilot-tracking/details/2026-10-29/stripe-readback-fencing-details.md

## Derived objectives and risks
Use additive SQLite claims and compare-and-increment generations. A trusted
controller explicitly authorizes handoff; avoid bespoke automatic timed leases.
High-impact stale completion is mitigated by checking scope/receipt/owner/
generation transactionally. This does not fence actual provider requests or
business effects, authenticate workers, or certify backup rollback/power loss.
Existing receipt enumeration/dedup and payment authority must not change.

## Checklist
- [x] Fenced claims and focused regressions. Details: (Lines 9-21).
- [x] Bilingual dated docs and compatibility notes. Details: (Lines 23-28).
- [x] Full validation, fixes and release preparation. Details: (Lines 30-36).

## Success, dependencies and handoff
Standard Python/SQLite only. Tests prove stale/ABA rejection, concurrent claims/
handoffs, durable ownership, additive upgrade, rollback and no payment mutation.
Full suite, demos, examples/links and protected-path comparison pass. Final CI
and controller-owned canonical sync are runtime release gates.
Log: .copilot-tracking/plans/logs/2026-10-29/stripe-readback-fencing-log.md
Handoff to /rpi-implement; no code implemented during planning.
