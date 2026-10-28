<!-- markdownlint-disable-file -->
# Stage 1659 changes: merchant-request-binding-2026-10-29

Plan: .copilot-tracking/plans/2026-10-29/merchant-request-binding-plan.instructions.md
Details: .copilot-tracking/details/2026-10-29/merchant-request-binding-details.md

## Phase 1
merchant-request-binding-2026-10-29-binding: complete.
Added immutable one-signature snapshot and exact raw request binding using the
existing canonical SHA256 Content-Digest formatter; no old guard behavior changes.
Focused tests include independent .NET vector, substitution, profile/limit/metadata
failures, no normalization/replay consumption and unchanged economic journal.
Configured custom implementation/validation agents absent; bounded trace inline.
24 new methods and 5 legacy identity methods pass, with no economic mutation.

## Phase 2
merchant-request-binding-2026-10-29-documentation: complete.
Bilingual pinned Visa/RFC evidence, narrow local-policy limits and synthetic examples;
daily/phase index updated without README/assets changes or new release claims.

## Phase 3
merchant-request-binding-2026-10-29-validation: local validation complete.
3,904 full tests (58.510s), compilation, both existing demos, 67 local links and
two bilingual executable examples pass. Restored eight generated historical reports.
Protected paths have zero diff from 1d9273d; no introduced failures or open blocker.
Runtime gates: final-SHA CI, canonical main receipt and clean refs.
Next review command: /rpi-review.
