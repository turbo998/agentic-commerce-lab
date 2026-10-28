<!-- markdownlint-disable-file -->
# Stage 1662 planning log

## Context assessment and paths considered
03:24 BJT: research completed; current admission has no historic first-gate record.
Select additive same-transaction record/read, not a new ledger service, a Poppy
token/purchase coupling, a changed journal interface or a post-commit audit write.

## Discrepancy Log
DD1 resolved: record only dispatch_allowed=True inside existing transaction.
DD2 resolved: current approval and historical direct reservation cannot backfill.
DD3 resolved: read works after revoke/expiry and means local gate history only.
DD4 resolved: add empty table on reopen, with no migration inventing old records.

## Validator Findings
Named Plan Validator is not configured; bounded inline requirements/phase validation.
No Critical/High blocker. Strict read-time scalar checks, rollback after both writes
and exact fingerprint/scopes are required, not just row count or happy path.
Details/plan line references checked; no implementation during planning.

## Validation Coverage
Target exact fields/times/binding, upgrade/non-backfill, concurrency, fresh process,
commit faults and prior approval contracts. Final full suite, compile, demos,
links/examples/protected paths and final CI/canonical receipt remain mandatory.

## Suggested Follow-On Work
Authenticated approver and signed/tamper-evident external logs, retention and
distributed coordination are deferred. No provider send/cancel/finality claim.

## Completed phase evidence
Phase 1: additive first-gate table/read model and same-transaction first-only insert;
no public return contract change, legacy migration or new provider call.
Phase 2: 25 new methods / 144 focused tests pass in 3.537s. Actual SQL trigger
observes both writes while independent readers see neither; post-write/commit
failures roll back both. Revoke/expiry/terminal state preserves history; legacy
attempts are not backfilled. Fresh-process/concurrent and exact boundary tests pass.
Phase 3: bilingual archive/daily/index prepared; 3,993 full tests pass in 71.132s.
Compileall, both demos, 91 local links and two identical executable bilingual
examples pass. Ten generated historical reports restored. Protected paths unchanged
from 1d9273d. Detail-line references 9-19/21-27/29-35 checked against actual file.
No implementation blocker; final-SHA CI/canonical/main hygiene are runtime gates.
Named implementor/validator agents absent; bounded inline implementation/validation.
