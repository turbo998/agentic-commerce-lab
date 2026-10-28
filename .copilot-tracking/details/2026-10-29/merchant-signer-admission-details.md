<!-- markdownlint-disable-file -->
# Stage 1666 details

## Context and requirements
Research: .copilot-tracking/research/2026-10-29/merchant-signer-admission-research.md
Resume4b36f8c; bilingual/main/full tests/CI, protected README/assets and nightly
23:00-06:00/no new phase from05:30 unchanged. No real crypto/payment/key management.

## Phase 1: shared approval participant and scoped signer gate
Extract existing post-lock approval/check/clock/reserve/history core into
_admit_in_transaction; reject autocommit. Preserve old public admit behavior.
New merchant_signers.py: frozen trusted tenant/merchant/target URI/keyid scope,
immutable local allow binding, idempotent irreversible revoke, no secret material.
Opt-in admit validates trusted scope/snapshot/checkout and shared file, BEGIN IMMEDIATE,
checks exact local permission, then existing approval participant on same connection.
Commit before return; no new signer provenance/audit or remote cancellation claim.
Acceptance: no duplicated approval logic, schema/result/legacy semantics unchanged.

## Phase 2: ordering, rollback and compatibility tests
Test scope/type/text, missing/revoked/cross-tenant/merchant/route/key permissions,
immutable allow/no reactivation, local namespace isolation and no permission by snapshot.
SQL-trace actual blocked BEGIN; committed revoke then blocked admission rejects.
Reserve first cannot be undone. Concurrent admissions allow one dispatch.
Observe actual reservation/history before injected/commit failure and rollback;
reopen/fresh process revocation persists, same resolved file enforced.
Existing approval/history/request/checkout/journal tests together; private core autocommit rejects.
Acceptance: revoked-first no new attempt/history, valid-first remains unknown.

## Phase 3: bilingual archive and integrated release gates
Document current pinned Visa/RFC evidence; local policy versus cryptographic identity,
keyid provenance, legacy bypass, signature freshness and remote revoke limits explicit.
Bilingual research/daily/index, full tests/compile/both demos/links/executable examples.
Restore generated reports, protect paths, validate plan references and fix issues.
Exact-file commit/non-force main, final-SHA CI/count and controller269 canonical
clean/zero-lock/protected receipt gate completion, no automatic next stage.
