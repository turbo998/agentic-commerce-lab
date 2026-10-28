<!-- markdownlint-disable-file -->
# Stage 1663 planning log

## Context assessment and paths considered
03:37 BJT: research complete. Select small opt-in association facade reusing the
existing semantic validator and transaction participant, not persistence before
validation, metadata-based correlation or a new transport layer.

## Discrepancy Log
DD1 resolved: separately trusted expected_reference, not readback-selected ID.
DD2 resolved: first binding retains unknown even when snapshot says succeeded.
DD3 resolved: exact-reference retries preserve current terminal outcome.
DD4 resolved: new facade hardens existing offline PI lab, not a new real payment
integration; current Stripe docs recommend Checkout Sessions for most new flows.
DD5 resolved: duplicate controller resumes merged; only269 handles canonical sync.

## Validator Findings
Named Plan Validator absent; bounded inline requirements/transaction validation.
No Critical/High blocker. Full validator must run before first association write;
provider scope/reference uniqueness and real commit failure need explicit tests.
Details/plan line ranges checked; no implementation during planning.

## Validation Coverage and deferred work
Strict full mapping and expected ID, pending-only association, scoped conflicts,
legacy observation/readback compatibility, true process, concurrent races and
post-write rollback. Full tests/compile/demos, examples/links/protected paths and
final-SHA CI/canonical runtime gates required.
Authenticated provider transport/create correlation, Checkout Sessions, Connect,
partial amount/refund/settlement and live payment actions remain out of scope.

## Completed phase evidence
Phase 1: one additive facade in existing observation module, reusing complete
validator and transaction participant. No old API/schema/permission changes.
Phase 2: 29 new methods / 148 focused tests pass in 3.589s. Actual reference update
is observed before injected failure/commit rollback; scoped namespaces, terminal
retry, metadata non-authority, concurrency and real process persistence covered.
Phase 3: bilingual research/daily/index prepared; 4,022 full tests in 58.278s pass.
Compileall, both demos, 103 local links and two identical executable bilingual
examples pass. Eight regenerated historical report files restored; two stat-only
report entries refreshed after confirming no content diff, staged reports empty.
Protected paths zero diff from 1d9273d. Detail ranges 9-17/19-25/27-33 verified.
No implementation blocker; final-SHA CI/canonical/main hygiene remain runtime gates.
Named implementor/validator agents absent; bounded inline implementation/validation.
