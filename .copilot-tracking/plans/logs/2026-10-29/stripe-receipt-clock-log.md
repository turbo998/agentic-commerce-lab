<!-- markdownlint-disable-file -->
# Stage 1669 planning log

## Context assessment
Actual start05:01 BJT froma8e908d; no new phases05:30, stop by06:00.
Bilingual/main/CI/full tests/protected paths unchanged. Named Researcher/Plan
Validator unavailable; bounded continuous trace/validation inline.
Stripe primary replay/async/duplicate docs checked05:03.

## Planning and discrepancy log
Existing inbox already rejects duplicate JSON; do not repair a nonexistent gap.
Keep old fixed-now ingress semantics. New facade intentionally samples twice:
arrival validation first, post-lock same-timestamp validation second.
Reuse original HMAC/JSON/receipt pipeline and shared time policy; never disable
time to preverify, repeat crypto under lock or expire durable worker tasks.
No new schema/time audit/secret-state claims.

## Validator findings
Inline validation found no Critical/High blocker. Require real SQL trace BEGIN,
post-lock boundary301 rejection/300 acceptance, duplicate/claim preservation,
first/second clock errors, one HMAC pass and old API behavior.
Details9-16/18-25/27-33 to be checked against actual lines before publication.

## Deferred and handoff
HTTP/queue bounds,live secret lifecycle,clock sync/ACK and worker freshness remain
external. Proceed /rpi-implement; phaseStop=false,stepStop=false.

## Implementation progression
Phase1 complete: shared clock/time helpers and new facade/original pipeline.
Original verifier error ordering preserved; two-boundary calls only on new path.
Named implementor absent, bounded work inline. Focused validation next.
Phase2 complete:184 focused tests,30 new methods,5.091s. Actual lock boundaries,
two-sample ordering and original crypto/JSON/identity/claim behavior verified.
Phase3 archives written; integrated validation/fix iteration next.
Detail ranges9-16/18-25/27-33 checked against actual file.
05:11-05:13 BJT:phase3 local validation complete.4,189 full tests in64.962s;
compileall,both demos,167 local links,two identical executed examples,daily tail
1668/1669 and30 AST methods pass. Ten generated reports restored. Protected
README/assets zero diff; origin/main ancestor verified. Final publication,exact
SHA CI/count and canonical ff-only/clean/locks receipt remain runtime gates.
