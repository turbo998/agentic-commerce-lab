---
applyTo: '.copilot-tracking/changes/2026-10-28/stripe-observation-binding-changes.md'
---
<!-- markdownlint-disable-file -->
# Stage 1653 implementation plan

## Overview and requirements
Continue from 83d4e5e with a small offline provider observation gate and bilingual
research. User/controller constraints: 23:00-06:00 only, no new phase after
05:30, preserve README/assets from 1d9273d, validate and synchronize main.
Derived objective: never interpret a retryable intent state as terminal failure
or a hold as full payment, and never close the wrong journal operation.

## Context and checklist
Research: .copilot-tracking/research/2026-10-28/stripe-observation-binding-research.md
Details: .copilot-tracking/details/2026-10-28/stripe-observation-binding-details.md
- [x] Implement/test observation gate. Details: (Lines 9-20).
- [x] Bilingual evidence and navigation. Details: (Lines 22-26).
- [x] Full local validation and release preparation. Details: (Lines 28-34).

Origin/main publication, CI and canonical checkout synchronization are runtime
release gates, recorded in the final task handoff rather than inferred from
these local-validation checkboxes.

## Risks and dependencies
Provider authenticity and initial association are trusted outside the gate;
do not claim a schema check authenticates payment. Keep partial capture and
destination charge policies out of scope and explicitly reject unsupported data.
Python standard library only. Main-checkout synchronization is controller-owned.

## Success and planning log
All focused/full checks and CI pass; protected paths unchanged; origin/main
contains the verified stage; canonical sync confirmed in runtime handoff.
.copilot-tracking/plans/logs/2026-10-28/stripe-observation-binding-log.md
