<!-- markdownlint-disable-file -->
# Stage 1666 changes

Plan: .copilot-tracking/plans/2026-10-29/merchant-signer-admission-plan.instructions.md
Details: .copilot-tracking/details/2026-10-29/merchant-signer-admission-details.md
Research: .copilot-tracking/research/2026-10-29/merchant-signer-admission-research.md

merchant-signer-admission-2026-10-29-asset: existing approval core extracted exactly,
new local scoped allow/revoke facade composes it after signed-checkout validation
under shared write transaction. Old APIs/schema/history behavior unchanged.
No key material, signature/nonce verification, remote revoke, payment send or undo.
merchant-signer-admission-2026-10-29-focused: 28 new methods;171 combined tests pass
in3.977s. Actual blocked BEGIN/committed revoke, post-lock approval expiry,
real post-write/policy/commit rollback and fresh-process revocation covered.
merchant-signer-admission-2026-10-29-validation: all4,096 tests pass in47.340s;
compileall, both demos,127 local links and two identical executable bilingual
examples pass. Eight historical generated report files restored, reports staged
diff empty; protected paths unchanged from1d9273d. No implementation blocker.
Named Phase Implementor/Implementation Validator unavailable; bounded work inline.
Final-SHA CI/canonical/main hygiene remain postpublication runtime gates.
