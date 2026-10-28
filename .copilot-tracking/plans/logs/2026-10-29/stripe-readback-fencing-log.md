<!-- markdownlint-disable-file -->
# Stage 1656 planning log

## Discrepancy Log
DR-1: Initial candidate was automatic expiry. AWS timing/pause evidence supports
the smaller explicit-handoff boundary instead; do not build a distributed lease.
DR-2: pending() remains all receipt hints, including locally handled hints;
active_claims is separate. Receipt.requires_readback is not a worker state.
DR-3: Same worker ID after recovery must still increment generation (ABA).
DR-4: Handled hint is caller-attested local work, not verified payment success.
DR-5: Initial targeted run found two test-only SQLite mutation connections not
closed by the transaction context manager on Windows. Use closing plus the
transaction context, matching production code; do not suppress cleanup errors.

## Validator Findings
Configured custom validator absent. Inline bounded-plan validation: no
Critical/High findings. Requirements and tests cover explicit scope and error
surfaces. Keep direct source-to-code trace inline without redundant delegation.

## Validation Coverage
Legacy receipt schema stays intact; sidecar claim table/FK is additive.
Coverage includes scoped compare-and-increment, concurrent recovery, fresh
process persistence, commit rollback, stable old API and unchanged journal.
Final full validation, examples/links, protected paths and runtime release gates
are required.

## Paths considered and follow-on work
Selected explicit local claims; rejected implicit wall-clock lease/heartbeat,
in-memory ownership and payment changes. Production queue clients, authenticated
worker/recovery policy, repeated pending-payment polls, remote result acceptance
and business-effect transactions remain separate. No runtime network worker,
automatic schedule, readback authentication or external effect fencing added.

## Implementation evidence
Phase 1 complete: 104 focused tests including 21 new methods passed after the
two test-only connection cleanup fixes; stale completion after current handling
is also rejected.
Phase 2 complete: both languages, Stage 1655 historical notes and daily/archive
navigation. Existing receipt examples still execute unchanged.
Phase 3 local validation complete at 01:14 BJT: all 3,829 tests, compilation,
both demos, 46 links and four examples pass. Ten known test-regenerated report
files restored, none staged. Protected README/assets unchanged.
Inline implementation validation found no Critical/High issues within the
local contract. Refreshed main remains cac1ae6. Final CI/canonical receipt are
runtime release gates, not recursively committed self-SHA claims.
