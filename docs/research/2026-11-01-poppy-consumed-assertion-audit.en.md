# Poppy Session Assertion Replay Read-Only Digest Model & Post-Expiry Full-Claim Audit (Stage 1739)

**Verification Date (Beijing Time)**: `2026-11-01`  
**Scope**: `lab/poppy_replay.py`, `tests/test_poppy_replay_read.py`  
**Related Stages**: Stage 1662 (`PoppyAssertionJournal`), Stage 1664 (`consume_with_clock`), Stage 1671 (`is_consumed`)

---

## 1. Background & Architectural Gap

In the Poppy Draft 0.2 (`poppy-session+jwt`) replay-prevention design, `PoppyAssertionJournal` preserves user privacy by persisting only the three-column primary key `(auth_issuer, client_id, jti_sha256)` in `poppy_assertion_replays`, never writing private subject identifiers (`sub`), session identifiers (`session_id`), or raw `jti` strings to disk.

However, during **post-incident replay auditing** and **full-claim consistency inspection**, relying solely on `consume(scope, assertion, now=...)` and `is_consumed(scope, jti)` left two architectural blind spots:

1. **Post-Expiry Audit Blocked by the 300-Second Live Admission Window**:
   - `consume()` / `consume_with_clock()` mutates state (burning unconsumed `jti` values) and requires `assertion.iat <= now < assertion.exp` (at most 300 seconds). Once `now >= assertion.exp`, callers could not use `consume()` to verify whether a historical `SessionAssertionClaims` object satisfied Poppy v0.2 structural invariants and was previously consumed.
2. **Claim-Unbound Raw `jti` Lookup**:
   - `is_consumed(scope, assertion.jti)` accepts only a raw `jti: str`, ignoring every other Poppy v0.2 claim on `assertion` (`typ == "poppy-session+jwt"`, `iss == scope.client_id`, `aud == scope.auth_issuer`, `0 <= iat < exp <= 2**63 - 1`, and `0 < exp - iat <= 300`).
   - If an audit path extracted `.jti` from a forged or scope-mismatched `SessionAssertionClaims` (for example `typ="poppy-browser+jwt"`, `iss != scope.client_id`, `aud != scope.auth_issuer`, or `exp - iat = 86400 > 300`) and passed it to `is_consumed(scope, assertion.jti)`, `is_consumed` returned `True` whenever that `jti` had been burned by a legitimate assertion in the same `scope`.
3. **Missing Typed Immutable Consumed-Digest Read Model**:
   - Unlike `PaymentApprovalStore`, `MerchantSignerStore`, `StripeEventInbox`, and `CheckoutStore`, `PoppyAssertionJournal` lacked a frozen read-model dataclass (`PoppyConsumedAssertion`) and stored-row parity verifier returning the persisted `(scope, jti_sha256)` proof.

---

## 2. AI-Native Architectural Improvements

We extended [`lab/poppy_replay.py`](../../lab/poppy_replay.py) with `PoppyConsumedAssertion` and two complementary families of read-only audit methods:

1. **Frozen `PoppyConsumedAssertion` Read Model & Stored-Row Parity Verifier (`_row_to_consumed_assertion`)**:
   - Holds `scope: PoppyReplayScope` and `jti_sha256: str`.
   - `__post_init__` enforces `isinstance(scope, PoppyReplayScope)` and validates `jti_sha256` as a canonical 64-character lowercase hex SHA-256 digest (`[0-9a-f]{64}`).
   - `_row_to_consumed_assertion(scope, expected_digest, row)` verifies that hydrated SQLite columns `(auth_issuer, client_id, jti_sha256)` match the lookup key, failing closed with `PoppyReplayError` on any drift.
2. **Typed `(scope, jti)` Digest Readers**:
   - `find_consumed(scope, jti) -> PoppyConsumedAssertion | None`: lock-free lookup returning `PoppyConsumedAssertion` when consumed or `None` when absent.
   - `read_consumed(scope, jti) -> PoppyConsumedAssertion`: strict reader raising `PoppyReplayError` when unconsumed.
   - Preserves `is_consumed(scope, jti) -> bool` on its lightweight `SELECT 1` query path for full backward compatibility.
3. **Clock-Independent Full-Claim Session Assertion Auditors (`_validated_assertion_key`)**:
   - `find_assertion_consumption(scope, assertion) -> PoppyConsumedAssertion | None`
   - `read_assertion_consumption(scope, assertion) -> PoppyConsumedAssertion`
   - `is_assertion_consumed(scope, assertion) -> bool`
   - Validates all clock-independent Poppy v0.2 session-assertion invariants (`typ == "poppy-session+jwt"`, `iss == scope.client_id`, `aud == scope.auth_issuer`, `0 <= iat, exp <= 2**63 - 1`, `1 <= exp - iat <= 300`, and 22–256 char base64url `jti`) before opening a SQLite connection—enabling post-expiry incident auditing while rejecting mismatched claims even when the underlying `jti` was previously consumed, without burning unconsumed assertions or persisting private claims.

---

## 3. Verification

Added 4 unit test methods in [`tests/test_poppy_replay_read.py`](../../tests/test_poppy_replay_read.py) (`64 passed, 132 subtests passed` across the Poppy replay and admission-clock test suites):

- `test_find_and_read_consumed_return_typed_immutable_digest_record`
- `test_consumed_assertion_record_and_row_parity_invariants`
- `test_assertion_consumption_audit_is_clock_independent_and_non_consuming`
- `test_assertion_consumption_rejects_mismatched_claims_even_when_jti_was_consumed`
