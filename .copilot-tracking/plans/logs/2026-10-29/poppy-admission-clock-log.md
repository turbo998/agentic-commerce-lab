<!-- markdownlint-disable-file -->
# Stage 1664 planning log

## Context assessment and paths considered
03:50 BJT: research completed, published0.2 spec SHA256 matches registry.
Select explicit clocked facade plus shared validation/participant, not optional
clock fallback, independent replay logic or an implicit fixed-now behavior upgrade.

## Discrepancy Log
DD1 resolved: registry spec hashes are content SHA256, not Git blob SHA1.
DD2 resolved: zero-skew/future-iat/integral64 are local strict policy; RFC7519 permits
small leeway. Post-lock sampling does not promise commit/issuance physical deadline.
DD3 resolved: clock/lock failure never substitutes request timestamp or consumes ID.
DD4 resolved: Session assertion replay separate from DPoP/client assertion/approval.

## Validator Findings
Named Plan Validator absent; bounded inline requirements/ordering validation.
No Critical/High blocker. Trace actual BEGIN attempt, not connection creation.
Reuse complete existing validation before insert; check both facades share history.
Details/plan ranges checked; no implementation during planning.

## Validation Coverage and deferred work
Deterministic lock timing, exact time/scalar/lifetime boundaries, exception and
commit rollback, concurrency/scopes, true process, minimal storage and old APIs.
Full suite/compile/demos, examples/links/protected paths and CI/canonical gates.
Distributed replay, authenticated clock/operator, token issuance and pruning are
deferred. No new permissions, real payments, automation or protocol release claim.

## Completed phase evidence
Phase1: required-clock facade and shared pure validation/transaction participant;
old fixed-now contract, schema, namespace and retention unchanged.
Phase2: 20 new methods / 62 focused tests pass in2.590s. Actual BEGIN trace proves
no clock invocation while queued; exact expiry rejects, valid time consumes.
Lock/clock/actual post-insert/commit failures, old/new concurrency, scopes and real
process/minimal storage tested. No silent fallback or token issuance.
Phase3: bilingual research/daily/index prepared; 4,042 full tests pass in48.768s.
Compileall, both demos, 109 local links and two identical executable bilingual
examples pass. Ten historical generated report files restored, staged reports empty.
Protected paths zero diff from1d9273d. Detail ranges9-16/18-24/26-32 verified.
No implementation blocker; final-SHA CI/canonical/main hygiene remain runtime gates.
Named implementor/validator agents absent; bounded inline implementation/validation.
