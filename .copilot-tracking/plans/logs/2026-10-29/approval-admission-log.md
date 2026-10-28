<!-- markdownlint-disable-file -->
# Stage 1661 planning log

## Discrepancy Log
DD1 resolved: existing CheckoutStore uses global mandates/simulated receipts; do not
silently treat those rows as tenant/provider-scoped PaymentOperation approvals.
DD2 resolved: sample the clock after BEGIN IMMEDIATE, not before waiting for a lock.
DD3 resolved: strict new admission rejects revoked/expired retries; recovery remains
journal.read, not a purported approval refresh or new dispatch.
DD4 resolved: SQLite affinity can retain noninteger expiry after external corruption;
the new gate explicitly rejects invalid persisted expiry rather than comparing it.
DD5 resolved: held-lock tests signal from SQL trace at actual BEGIN attempt, not
merely connection creation, so the clock-order proof is deterministic.

## Validator Findings
Configured Plan Validator/Phase Implementor absent, confirmed 03:06 BJT.
Bounded continuous trace validated inline; no redundant delegation.
No blocking Critical/High findings: shared transaction participants, exact fingerprint,
immutable records, clear serialized race boundary and trusted-operator/clock limits.

## Validation Coverage
Fault injection must observe inserted state before failure; no proxy-only success.
Deterministic held-lock test proves clock sampling after acquisition.
Full coupled/legacy regression and integrated validation/fix iteration required.
Final CI/canonical receipt remain post-commit runtime gates.

## Completed phase evidence
Phase 1: same-file scoped immutable approval store, pure checkout validation and
journal transaction participant; existing public facades remain compatible.
Phase 2: 34 new methods and 119 focused tests pass, including SQL-observed rollback,
traced lock ordering, concurrent races, fresh process and legacy-mandate exclusion.
Phase 3: 3,968 tests in 57.748s; compileall, both demos, 89 local links and two
executable bilingual examples pass. Eight generated historical reports restored.
Protected paths have zero diff from 1d9273d. Inline validation found no blocker.
Final-SHA CI/controller canonical receipt/clean refs remain post-commit runtime gates.

## Deferred and rejected alternatives
Rejected separate check/reserve connections, pre-lock time, nested transactions and
Poppy/MCP identity as purchasing authority. Deferred consent UI/legal proof,
provider cancellation, distributed revocation, key verification and actual payments.
