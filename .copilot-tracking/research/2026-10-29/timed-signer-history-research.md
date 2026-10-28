<!-- markdownlint-disable-file -->
# Stage 1668 research: first timed signer admission history

## Scope and request
Continue from15fae33, actual start2026-10-29 04:43 BJT. Preserve bilingual archives,
full/focused/compile/CI/non-force main and protected README/assets against1d9273d.
Only23:00-06:00, no new phase from05:30. Narrow offline durable local history;
do not expand into nonce service, cryptographic verifier or signed payment receipt.

## Evidence and discoveries
Bounded continuous trace handled inline; named Researcher Subagent unavailable.
lab/merchant_signers.py admits timed input in approval's transaction but currently
records only approval history. That existing row cannot distinguish timed/bare
signer execution. Its admitted_at sample is already available through clock wrapper.
lab/payment_approvals.py and tests/test_admission_provenance.py provide prior art:
first-new-reservation-only insertion, read independently of current revocation/time,
exact full-operation fingerprint, upgrade without backfill and rollback on failure.
2026-10-29 04:45 BJT: RFC9421 section3.2.1 actual title is
"Enforcing Application Requirements"; section3.3 distinguishes mathematical
verification from application restrictions. Retrieved https://www.rfc-editor.org/rfc/rfc9421.txt .
Initial assumed heading lookup failed explicitly; corrected actual heading before
drawing evidence. RFC permits application requirements, not this audit schema.
Visa HEAD rechecked04:45 remains16d59bdf3f8a542bc538d0962edbb80ea30a02af,
dated2025-10-28T22:43:43Z. No new vendor release; Stripe/Sierra not rechecked.

## Selected approach and alternatives
Add immutable TimedSignerAdmission and read_timed_admission(operation) to existing
store. Persist minimal non-secret identifiers, selected signature label, authenticated
created/expires and original single admitted_at sample only when timed branch
creates a NEW reservation. Same transaction includes attempt/approval/signer rows.
Retain operation fingerprint binding and reconstruct exact frozen scope from
operation tenant/merchant plus recorded target_uri/key_id.
Read uses historical stored times, not current clock/policy; malformed stored
metadata raises explicitly. Historical window valid at admitted_at, not today.
No new clock sample, public transaction, dispatch result, key/raw body/signature
storage or schema change in approval/journal. Additive empty table migration only.
Rejected: infer proof from approval history, backfill on retry/upgrade, overwrite
with re-signed metadata, persist before successful reservation, log after commit,
or authenticate provenance merely by constructing a frozen record.

## Scenarios, risks and open questions
First timed dispatch writes all3 or none. Valid timed retries retain first record,
including different still-permitted scope/key/label/window. Bare/generic/journal
legacy attempts never gain history retroactively, including terminal attempts.
Revocation/expiry block admission but not read. Concurrency grants one dispatch
and one first record. SQL-trigger/post-write/commit failures roll back all3.
Actual blocked BEGIN retains one post-lock time in both history rows.
Old database migration creates empty history, never invents historical execution.
Database and adapter are trusted; this is a local execution record, not independently
verifiable signature, authentic consumer consent, nonce proof or remote payment result.
Identifiers/URIs must contain no credentials. Persistence adds retention responsibility;
no pruning/expiration policy or append-only tamper resistance is promised.
Bare APIs remain bypasses; row absence is absence of recorded execution, not rejection.
No blocking question. Follow-ups: authenticated wire evidence/nonce, policy version
and remote send boundary remain separate.

## Artifact self-check and handoff
Request, dated evidence, discoveries, alternatives, scenarios, risks, gaps and
follow-ups checked. No implementation in research. Proceed /rpi-plan with this brief.
