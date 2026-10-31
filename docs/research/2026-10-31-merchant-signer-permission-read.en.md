# 2026-10-31: Stage 1727 — `MerchantSignerStore.read_permission` Scoped Read-Only Signer Permission Lookup and Authority Boundary

[中文](2026-10-31-merchant-signer-permission-read.md) | [Stage archive index](../stage-archive-index.md) | [Daily report](../../research/daily/2026-10-31.en.md)

## 1. Context and Problem Statement

Where Visa Trusted Agent Protocol (TAP, built on RFC 9421 HTTP Message Signatures) meets a merchant's local execution plane, `MerchantSignerStore` in [`lab/merchant_signers.py`](../../lab/merchant_signers.py) fences local allow (`allow`) and revocation (`revoke`) rules per four-dimensional `MerchantSignerScope(tenant_id, merchant, target_uri, key_id)` and participates in single-transaction checkout admission (`admit()`) alongside `PaymentApprovalStore` and `PaymentAttemptJournal`.

Prior to Stage 1727:
- `MerchantSignerStore.read_timed_admission(operation)` only inspected `merchant_timed_admissions` rows recorded **after** a first timed-signature dispatch had already been admitted;
- `_permission(db, scope)` was private and raised `MerchantSignerError` whenever a scope was absent;
- Operator health checks, key-rotation audits (e.g., verifying Visa Agentic Key Directory revocations or merchant route-key isolation), and incident responders lacked a **lock-free, read-only public API** to inspect `merchant_signer_permissions` without taking a SQLite writer lock, verifying a signature, sampling an admission clock, or mutating store state.

## 2. Dialectical Comparison: AI-Native Commerce vs. Classic 3-Tier Web / Cloud WAF

| Dimension | Classic 3-Tier Web App / Cloud WAF | Agentic Commerce AI-Native Architecture (Stage 1727) |
|---|---|---|
| **Key & route permission granularity** | Coarse IAM roles or API gateway keys cached in memory across broad service routes | Exact four-dimensional `MerchantSignerScope(tenant_id, merchant, target_uri, key_id)` isolation across tenants, merchants, query-bearing target URIs, and key IDs |
| **Permission inspection vs. admission authority** | Checking that a key is on an allowlist is often conflated with request authorization, or only testable by attempting a live mutation | `read_permission` performs a pure `SELECT` returning persisted policy state (`None` / `"active"` / `"revoked"`). It never proves RFC 9421 signature validity or substitutes for `admit()`'s transactional window, approval, and reservation checks |
| **Locking & failure isolation** | Reusing write paths or lazy-initializing rows during status checks causes writer-lock contention and audit pollution | `read_permission` validates `MerchantSignerScope` before opening SQLite, never issues `BEGIN IMMEDIATE`, never observes rolled-back `allow`/`revoke` writes, and fails closed on corrupted `revoked` values |

## 3. Implementation ([`lab/merchant_signers.py`](../../lab/merchant_signers.py))

1. Added permission-state literal and immutable status model:
   - `SignerPermissionState = Literal["active", "revoked"]`
   - Frozen dataclass `MerchantSignerPermissionStatus(scope: MerchantSignerScope, state: SignerPermissionState)` with `__post_init__` validation of `scope` and `state`.
2. Added `MerchantSignerStore.read_permission(self, scope: MerchantSignerScope) -> MerchantSignerPermissionStatus | None`:
   - Calls `self._require_scope(scope)` before opening any SQLite connection;
   - Executes a read-only `SELECT revoked FROM merchant_signer_permissions WHERE tenant_id=? AND merchant=? AND target_uri=? AND key_id=?` without `BEGIN IMMEDIATE`;
   - Returns `None` when no permission row exists for the scope;
   - Strictly validates `type(revoked) is int and revoked in (0, 1)`;
   - Returns `MerchantSignerPermissionStatus(scope, "revoked" if revoked else "active")`.

## 4. Verification Evidence ([`tests/test_merchant_signer_permission_read.py`](../../tests/test_merchant_signer_permission_read.py))

Added 10 unit tests (18 subtests) covering:
- Absent scope returns `None` without creating rows in `merchant_signer_permissions`, `merchant_timed_admissions`, `payment_approvals`, or `payment_attempts`;
- `allow()` yields `state="active"` across store reopens and fresh Python subprocesses;
- `MerchantSignerPermissionStatus` is `frozen=True` and rejects invalid `scope` or `state` values at construction;
- Idempotent `revoke()` transitions status to `state="revoked"`, preserves `read_timed_admission(operation)` history, and blocks subsequent `admit()` calls;
- `state="active"` reflects only persisted signer policy and cannot bypass a missing `PaymentApprovalStore` record during `admit()`;
- Full isolation across all four `MerchantSignerScope` dimensions (`tenant_id`, `merchant`, `target_uri`, `key_id`);
- Invalid `scope` values fail before `_connect()`;
- Rolled-back `allow()` and `revoke()` commits are never reported by `read_permission`;
- Corrupted persisted `revoked` values raise `MerchantSignerError`;
- SQL trace confirms `SELECT`-only execution without `BEGIN IMMEDIATE`.

Validation commands and results:
- `python -m pytest tests/test_merchant_signer_permission_read.py -q`: `10 passed, 18 subtests passed`
- `python -m pytest -q`: `4287 passed, 1122 subtests passed`
