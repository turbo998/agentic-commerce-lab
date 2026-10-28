<!-- markdownlint-disable-file -->
# Stage 1665 planning log

## Context assessment
2026-10-29 04:00-04:02 BJT; resume37b1e7e with protected paths and nightly gates.
Continuous verifier->inbox trace inline; named Plan Validator/Researcher absent.
Official rolling/raw-body/endpoint scope evidence checked; no blocking gap.

## Planning and selected scope
One additive tuple-config branch in existing verifier, propagated through inbox.
No extra facade, global keyring, schema, TTL or exception-based verify loop.
Full config validation before matching avoids success-shaped invalid config.
One HMAC per attempted key; identical parser/expiry/body behavior for both forms.

## Discrepancy log
Existing multiple-v1/scalar secret already handles Stripe's overlap header.
Do not call it a protocol bug or claim all SDKs accept tuples.
Remote key expiry and local config retirement are independent control planes.

## Validator findings
Inline bounded plan validation: no Critical/High implementation blocker.
Scalar compatibility, tuple strictness, bad trailing config, malformed v1 with
valid candidate, stale duplicates, scope separation and minimal storage covered.
Final full/focused checks and integrated main/CI/canonical gates explicit.
Detail line references9-16/18-25/27-33 correspond to declared phases.

## Deferred and handoff
Live secrets/accounts, secret distribution, automatic retirement, thin events,
Connect/organization support and model benchmarks outside this increment.
Proceed /rpi-implement with dated plan/details/research/log; changes file is
created only during implementation. phaseStop=false, stepStop=false.

## Implementation evidence
Phase1: shared verifier/inbox config complete; no schema/result change.
Phase2: initial153-test run exposed two test-only issues: mock patched the shared
hmac module used to build fixture headers, and sqlite connection context did not
close on Windows. Precompute signed fixture before patch and use closing().
Failed test temp artifact removed exactly; corrected153 tests pass in7.130s.
Added explicit one-HMAC-per-tried-key assertion; final154 focused tests pass
in10.477s (26 new methods).
Phase3: bilingual research/daily/index complete. All4,068 tests pass in64.681s;
compileall lab/scripts and both demos pass.119 local links and two identical
executable bilingual examples pass. Ten generated historical report files restored,
reports staged diff empty; protected paths zero diff from1d9273d.
Detail ranges9-16/18-25/27-33 verified. Inline production-diff review: shared
parser/time/receipt behavior retained, no open implementation blocker.
Final-SHA CI/canonical/main hygiene remain postpublication runtime gates.
