---
applyTo: '.copilot-tracking/changes/2026-10-29/timed-signer-history-changes.md'
---
<!-- markdownlint-disable-file -->
# Stage 1668 plan: immutable first timed signer admission record

Research: .copilot-tracking/research/2026-10-29/timed-signer-history-research.md
Details: .copilot-tracking/details/2026-10-29/timed-signer-history-details.md
Log: .copilot-tracking/plans/logs/2026-10-29/timed-signer-history-log.md
Resume15fae33 with nightly/protected/bilingual/main rules unchanged.
No inferred cryptographic provenance, consumer authority or nonce consumption.

## Phases and prerequisites
- [x] Add first-timed-admission table/read model and atomic new-reservation write.
  Details: (Lines 9-17).
- [x] Validate non-backfill, original clock ordering, read lifetime and rollback.
  Depends on phase1; Details: (Lines 19-27).
- [x] Bilingual archive and full validation/fix iteration/release preparation.
  Depends on phase2; Details: (Lines 29-36).

## Risks and success
One recorded execution is not authentication of input/provenance or current authority.
Persist no raw body/key/signature/credentials; operators own safe identifiers and retention.
Existing first approval row remains a distinct record, never upgraded retroactively.
No new public transaction or extra clock sample; three writes commit or roll back.
Missing historical row means no recorded execution, not rejection. Bare paths bypass.
Upgrade adds empty table; read uses historical window and full fingerprint.
Focused/full/compile/demos/links/examples/protection gates required; final-SHA CI/main/
canonical hygiene are separate runtime release gates. Standard library only.
