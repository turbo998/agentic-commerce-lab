# Coupled Local Checkout Mandate (`mandates`) and Idempotency Receipt (`receipts`) Read-Only Provenance Model & Stored-Row Invariants (Stage 1737)

> ** 中文版**: [2026-11-01-checkout-provenance.md](./2026-11-01-checkout-provenance.md)  
> **Verification Date**: 2026-11-01 (Beijing Time `UTC+08:00`)  
> **Related Modules**: `lab/checkout.py`, `tests/test_checkout_provenance.py`, `tests/test_checkout.py`  
> **Preceding Stage**: [Stage 1736 (`2026-11-01-stripe-readback-provenance.en.md`)](./2026-11-01-stripe-readback-provenance.en.md)

---

## 1. Context & Architectural Problem

In `agentic-commerce-lab`'s deterministic local checkout store `CheckoutStore` (`lab/checkout.py`), operator-issued mandates and consumption receipts are persisted across two SQLite tables linked by `UNIQUE REFERENCES mandates(id)`:

1. **`mandates`**: Stores single-use operator checkout authorizations (`id`, `merchant`, `currency`, `cart_digest`, `max_amount`, `expires_at`, `revoked`).
2. **`receipts`**: Stores atomic local simulated outcomes (`request_key`, `fingerprint`, `mandate_id`, `order_id`, `amount`, `currency`) written by `CheckoutStore.execute(...)` inside a `BEGIN IMMEDIATE` transaction.

Prior to Stage 1737, `CheckoutStore` had four read/write asymmetry and stored-row integrity gaps:

1. **No Lock-Free, Clock-Free Read-Only Provenance Inspection API**: `CheckoutStore` exposed only write methods (`approve`, `revoke`, `execute`) and lacked read-only accessors (`read_mandate`, `read_receipt`, `find_provenance`, `read_provenance`). Operators or audit workflows inspecting whether a `mandate_id` was unspent (`active` / `revoked`) or already consumed (with its bound `request_key` and `Receipt`) had to query SQLite directly or invoke `execute()` with a clock and write lock.
2. **Idempotent Replay Path (`execute`) Did Not Verify Full `receipts` and Parent `mandates` Invariants**:
   - When `SELECT * FROM receipts WHERE request_key=?` matched a prior row, `execute()` checked only `previous["fingerprint"] != fingerprint`. It did not verify that `previous["fingerprint"]` was a valid 64-character lowercase hex SHA-256 digest, nor did it verify `previous["mandate_id"] == mandate_id`, `previous["order_id"] == f"sim_{fingerprint[:24]}"`, `previous["amount"] == checkout.amount`, or `previous["currency"] == checkout.currency`;
   - If `receipts.amount`, `receipts.currency`, or `receipts.order_id` was tampered with in SQLite, or if the parent `mandates` row was deleted under `PRAGMA foreign_keys = OFF` (an orphan receipt), idempotent retries silently returned corrupted receipts.
3. **Missing Constructor Invariants on `Receipt`**: `Receipt` lacked `__post_init__` validation, allowing construction of malformed `order_id` values (outside `sim_<24-hex>`), non-positive 64-bit integer `amount` values, invalid currency codes, or statuses other than `"simulated"`.
4. **Silent Overwrite and Misclassification on Corrupted `mandates` Columns**:
   - `CheckoutStore.revoke(mandate_id)` executed `UPDATE mandates SET revoked=1 WHERE id=?` directly without validating stored columns, overwriting and masking corrupted `revoked` (e.g., `2`, `-1`, `'active'`), `expires_at`, `max_amount`, `cart_digest`, `currency`, or `merchant` values;
   - `CheckoutStore.execute(...)` used Python truthiness `if mandate["revoked"]:`, misreporting corrupted `revoked = 2` values as `"Mandate is revoked or expired; obtain new approval."`.

---

## 2. Classical 3-Tier Web Architecture vs. AI-Native Agentic Commerce Architecture

| Dimension | Classical Web App / Well-Architected 3-Tier | AI-Native Agentic Commerce Architecture (Stage 1737) |
| :--- | :--- | :--- |
| **Idempotency Cache Hit (`receipts`) Trust Boundary** | Returns cached row columns directly whenever `request_key` and fingerprint match | Both idempotent replays (`execute`) and read-only lookups (`read_receipt`, `find_provenance`) enforce `_parse_receipt_row()` across the 64-hex `fingerprint`, `mandate_id`, `sim_<24-hex>` `order_id`, exact `amount`/`currency`, and parent `mandates` binding |
| **Mandate & Receipt Provenance Inspection** | Reuses write endpoints or issues separate queries across `mandates` and `receipts` | `CheckoutStore.find_provenance()` / `read_provenance()` execute a single read-only `SELECT ... FROM (SELECT 1) LEFT JOIN mandates ... LEFT JOIN receipts ...` snapshot without a clock or write lock |
| **Deleted Parent Mandate or Corrupted Columns** | Returns orphan receipts when foreign keys are bypassed; `revoke()` overwrites corrupted rows | Rejects orphan receipts across `read_receipt()`, `find_provenance()`, and `execute()` with `AuthorizationError("Orphan receipt exists without a recorded mandate.")`; `revoke()` validates `_parse_mandate_row()` under `BEGIN IMMEDIATE` before updating |

---

## 3. Stage 1737 Core Implementation

### 3.1 Immutable `MandateStatus`, `Receipt`, and `CheckoutProvenance` Value Objects

In `lab/checkout.py`:

1. **`MandateStatus`**:
   - Fields: `mandate_id: str`, `merchant: str`, `currency: str`, `cart_digest: str`, `max_amount: int`, `expires_at: int`, `state: Literal["active", "revoked"]`.
   - `__post_init__` enforces nonempty `mandate_id`/`merchant`, 3-letter uppercase ASCII `currency`, 64-character lowercase hex `cart_digest`, positive signed 64-bit integer `max_amount`/`expires_at`, and exact `state in ("active", "revoked")`.
2. **`Receipt`**:
   - `__post_init__` enforces `re.fullmatch(r"sim_[0-9a-f]{24}", self.order_id)`, positive signed 64-bit integer `amount`, 3-letter uppercase ASCII `currency`, and `status == "simulated"`.
3. **`CheckoutProvenance`**:
   - Fields: `mandate_id: str`, `fingerprint: str`, `mandate_status: MandateStatus | None`, `request_key: str | None`, `receipt: Receipt | None`.
   - `__post_init__` enforces `mandate_status.mandate_id == mandate_id`, `request_key` presence parity with `receipt`, rejection of orphan receipts (`receipt is not None and mandate_status is None`), and consistency of `receipt.order_id`, `receipt.currency`, and `receipt.amount <= mandate_status.max_amount`.

### 3.2 Single-Query Read-Only Snapshot & Write-Path Symmetry

1. **`CheckoutStore.read_mandate(mandate_id, checkout) -> MandateStatus | None`**:
   - Lock-free, clock-free read of `mandates` with `_parse_mandate_row()` and `_verify_mandate_binding()`.
2. **`CheckoutStore.read_receipt(mandate_id, checkout, *, request_key) -> Receipt | None`**:
   - Single `SELECT ... FROM receipts r LEFT JOIN mandates m ON m.id = r.mandate_id WHERE r.request_key = ?` verifying both receipt integrity and parent mandate binding.
3. **`CheckoutStore.find_provenance(mandate_id, checkout, *, request_key=None)` and `read_provenance(...)`**:
   - Single `FROM (SELECT 1) LEFT JOIN mandates m ON m.id = ? LEFT JOIN receipts rm ON rm.mandate_id = ? LEFT JOIN receipts rk ON ? IS NOT NULL AND rk.request_key = ?` snapshot covering unapproved, approved unspent (`active`/`revoked`), consumed, cross-checkout `request_key` conflicts, alternate-key retries on consumed mandates, and orphan receipts.

---

## 4. Verification Results

- Added unit test suite `tests/test_checkout_provenance.py` (`4 passed, 46 subtests passed`); combined with `tests/test_checkout.py`, `15 passed, 61 subtests passed`.
- Full repository regression suite (`python -m pytest -q`): `4341 passed, 1561 subtests passed`.
