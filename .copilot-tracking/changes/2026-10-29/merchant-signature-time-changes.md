<!-- markdownlint-disable-file -->
# Stage 1667 changes

Plan: .copilot-tracking/plans/2026-10-29/merchant-signature-time-plan.instructions.md
Details: .copilot-tracking/details/2026-10-29/merchant-signature-time-details.md
Research: .copilot-tracking/research/2026-10-29/merchant-signature-time-research.md

merchant-signature-time-2026-10-29-asset: frozen same-signature wrapper/pure local
time validation and timed union branch in existing merchant facade implemented.
One post-lock sample flows through signature check to original approval/history.
Bare behavior/schema unchanged; no nonce, crypto or signed provenance claim.
merchant-signature-time-2026-10-29-focused: 30 new methods, 201 focused tests pass
in5.473s. Real SQL BEGIN attempts observe queued time advance/revoke; one clock
sample reaches history. Invalid metadata/clock, quote/key/body, old paths and
real post-write/commit rollback covered, no implementation deviation.
merchant-signature-time-2026-10-29-archive: bilingual research/daily/index and
two short historical Stage1666 scope notes added; no protected-path changes.
merchant-signature-time-2026-10-29-validation: 4,126 full tests pass in55.409s;
compileall lab/scripts, both demos,149 local links and two identical executable
examples pass; daily1666/1667 tail order checked. Ten generated historical report
files restored only after inspecting exact paths/content; no report committed.
Details line ranges9-17/19-26/28-34 verified; self-validation found no blocking issue.
Original approval core/schema unchanged, bare clock object preserved.
README.md/README.en.md/assets remain zero diff against1d9273d.
Release preparation complete; actual final-SHA CI/canonical/main hygiene pending
as separate postpublication runtime gates, not claimed complete in this artifact.
Named Phase Implementor/Implementation Validator unavailable; bounded work inline.
Final-SHA CI/canonical/main hygiene remain postpublication runtime gates.
