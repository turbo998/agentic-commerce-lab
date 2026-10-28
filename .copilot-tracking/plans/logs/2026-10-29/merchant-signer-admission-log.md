<!-- markdownlint-disable-file -->
# Stage 1666 planning log

## Context assessment
2026-10-29 04:13-04:16 BJT, resume4b36f8c; nightly/protected/main gates unchanged.
Bounded request->approval trace inline; named Researcher/Plan Validator not configured.
Visa HEAD16d59bdf remains2025-10-28, not a new release. RFC3.2.1/7.3.2/7.3.4 checked.

## Planning
Reuse exact approval core as a private in-transaction participant. New scoped local
permission store composes it after signed-checkout validation under one write lock.
Keep old APIs/approval history intact; no generic policy engine or new signed receipt.
Allow binding immutable; revoked flag irreversible through API. No crypto copied.

## Discrepancy log
Revocation updates a flag, so not an append-only event log; research wording corrected.
Cryptographic identity/remote directory changes/signature expiry remain external.
Existing approval admission history does not prove optional signer policy execution.

## Validator findings
Inline bounded plan validation: no Critical/High implementation blocker.
Race definition and limitation explicit: committed revoke-first blocks new local
reservation; reservation-first retains unknown/no undo. Actual blocked BEGIN and
post-write rollback tests required, not just sequential mocks.
Scope includes trusted tenant/merchant/exact target/keyid, never request-selected.
One approval core avoids expiry/clock/history drift; full legacy suite required.
Detail ranges9-17/19-27/29-35 checked against intended phase boundaries.

## Deferred and handoff
PKI/directory revocation distribution, signature-time/nonce atomicity, signer-gate
provenance and real provider effects deferred. Proceed /rpi-implement with dated
plan/details/research/log; changes file created only in implementation.
phaseStop=false, stepStop=false.

## Implementation evidence
Phase1: original approval body extracted without policy/schema changes; new
scoped permission facade composes private core after original input validation.
Phase2: initial145 tests pass, then improved non-normalized resolved-path spelling,
added actual allow/revoke commit rollback and complete provenance regressions.
Final171 focused tests pass in3.977s (28 new methods), no implementation failure.
Phase3: bilingual research/daily/index complete. All4,096 tests pass in47.340s;
compileall lab/scripts and both demos pass.127 local links and two identical
executable bilingual examples pass. Eight generated historical reports restored,
reports staged diff empty; protected paths zero diff from1d9273d.
Detail ranges9-17/19-27/29-35 verified. Inline production review confirms approval
core is unchanged apart from active-transaction precondition/extraction, and scoped
signer facade does not infer cryptographic identity or signer history.
No implementation blocker; final-SHA CI/canonical/main hygiene remain runtime gates.
