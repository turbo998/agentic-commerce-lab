<!-- markdownlint-disable-file -->
# Stage 1658 planning log

## Discrepancy Log
DD1 resolved: choose Session assertion replay only, not a purported complete token
endpoint or a DPoP store with guessed timing/key semantics.
DD2 resolved: retain IDs without expiry pruning; explicitly stricter than minimum
retention, with fresh-jti retry and production growth limitations.

## Validator Findings
Configured Plan Validator/Phase Implementor agents absent (02:11 BJT).
Bounded continuous trace researched and validated inline under direct-work rules.
No blocking Critical/High findings: no signature-validation shortcut, no per-user
replay namespace, transactional insert, storage errors propagate, no credential output.
Details/plan ranges inspected; full-validation/fix iteration is required.

## Validation Coverage
Local baseline clean and refs aligned at 292207f. Unit assertions cover exact
timing/type limits and immutable scope; existing Poppy API behavior remains covered.
Full validation, examples/links, protected paths and runtime release gates planned.
Phase 1 complete: 42 focused tests pass (26 new), including fresh-process replay
refusal, eight independent concurrent journals, commit/insert/connection faults.
Inline implementation validation confirms one transaction, digest-only ID storage,
same-client namespace independent of subject/session, and no new crypto claim.
Phases 2/3 local checks complete: 3,880 full tests (62.499 seconds), compileall,
both demos, 61 local links and two executable bilingual examples pass.
Evidence: session files/stage1658-unittest.log. Ten generated historical reports
restored; protected-path difference from 1d9273d remains zero.
Final source extraction reviewed inline; no duplicate metadata logic, legacy
replay/key-isolation behavior preserved, no implicit JWT/DPoP verification added.
Publication, final-SHA CI and canonical receipt remain runtime release gates.

## Implementation Paths Considered
Selected durable opt-in journal and extracted pure metadata check.
Rejected new in-memory cache, broad historical guard rewrite, custom crypto,
cross-assertion batch authentication and speculative expiry eviction.

## Suggested Follow-On Work
Real signature/discovery/authenticated-client binding, DPoP proof replay,
distributed replay storage and safe retention remain external or future work.
