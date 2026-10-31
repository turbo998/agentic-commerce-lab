# Stage 1732 — Single-Snapshot Cross-Table Admission Provenance Lookup (`MerchantSignerStore.find_provenance` / `read_provenance`)

> **中文对应版**: [2026-11-01-operation-admission-provenance.md](2026-11-01-operation-admission-provenance.md)  
> **Verification Date (Beijing Time)**: `2026-11-01` (`00:49–01:02+08:00` window)  
> **Related Assets**: [`lab/merchant_signers.py`](../../lab/merchant_signers.py) · [`tests/test_operation_admission_provenance.py`](../../tests/test_operation_admission_provenance.py)

---

## 1. Background & Problem Statement

After completing Stage 1728 (`PaymentAttemptJournal.read_attempt`), Stage 1729 (`PaymentApprovalStore.find_admission`), and Stage 1730 (`MerchantSignerStore.find_timed_admission`), each individual execution-fencing table had a lock-free optional reader. However, when operators or reconciliation workflows inspect an operation's end-to-end admission provenance by calling `read_attempt()`, `find_admission()`, and `find_timed_admission()` sequentially across three separate SQLite connections, two structural failure modes remain:

1. **Multi-Connection TOCTOU Read Skew**: If a concurrent writer commits `approvals.admit()` or `signers.admit()` between sequential reads, the caller can observe `read_attempt() -> None` followed by `find_admission() -> ApprovalAdmission(...)`, creating a false "orphan admission" anomaly due to non-atomic connections.
2. **Missing Cross-Table Causal & Clock-Sample Invariants**:
   - In valid execution flows, a `payment_admissions` row cannot exist without a `payment_attempts` reservation, and a `merchant_timed_admissions` row cannot exist without both `payment_admissions` and `payment_attempts`.
   - Under timed-signer admission (`MerchantSignerStore.admit`), `payment_admissions.admitted_at` and `merchant_timed_admissions.admitted_at` are recorded inside one `BEGIN IMMEDIATE` transaction from a single trusted clock sample (`tmd.admitted_at == adm.admitted_at`).

---

## 2. Dialectical Architecture Analysis: Classic 3-Tier Web App vs. AI-Native Agentic Commerce

| Architectural Dimension | Classic 3-Tier Web / Repository Architecture | AI-Native Agentic Commerce Architecture (Stage 1732) |
|---|---|---|
| **Cross-Table Read Aggregation** | Composes sequential repository calls (`getAttempt()` + `getApprovalAdmission()` + `getTimedAdmission()`) in application code, exposing callers to multi-connection TOCTOU read skew under concurrent writes. | `MerchantSignerStore.find_provenance()` verifies that all three stores resolve to the exact same SQLite file and executes a **single `SELECT ... LEFT JOIN` statement snapshot**, eliminating multi-connection read skew. |
| **Execution Path Classification** | Infers which authorization gate admitted a request from external logs or distributed trace tags. | `OperationAdmissionProvenance.path` deterministically classifies the snapshot into `"direct_reservation"`, `"approval_admission"`, or `"timed_signer_admission"` from persisted causal evidence. |
| **Cross-Table Causal & Clock Integrity** | Validates individual table columns in isolation without checking cross-table hierarchy or shared clock samples. | Fails closed with `MerchantSignerError` on orphan admission rows (`payment_admissions` or `merchant_timed_admissions` without `payment_attempts`, or `merchant_timed_admissions` without `payment_admissions`) and clock-sample split-brain (`tmd.admitted_at != adm.admitted_at`). |

---

## 3. Implementation Details (`lab/merchant_signers.py`)

1. **`OperationAdmissionProvenance` Frozen Dataclass**:
   - Fields: `fingerprint: str`, `attempt: PaymentAttempt`, `approval_admission: ApprovalAdmission | None`, `timed_signer_admission: TimedSignerAdmission | None`.
   - `__post_init__` invariants: validates the 64-character lowercase hex `fingerprint`, enforces fingerprint equality across all present records, rejects orphan `timed_signer_admission` when `approval_admission is None`, and requires exact cross-table clock-sample equality (`timed_signer_admission.admitted_at == approval_admission.admitted_at`) within `[0, approval_admission.expires_at)`.
   - `path` property: returns `"direct_reservation"`, `"approval_admission"`, or `"timed_signer_admission"`.
2. **`MerchantSignerStore.find_provenance()` & `read_provenance()`**:
   - Validates `approvals`, `journal`, and `operation` types and requires `self.path.resolve(strict=True) == approvals.path.resolve(strict=True) == journal.path.resolve(strict=True)`.
   - Runs a single anchored query: `FROM (SELECT ? AS tenant_id, ? AS operation_id) k LEFT JOIN payment_attempts att USING (tenant_id, operation_id) LEFT JOIN payment_admissions adm USING (tenant_id, operation_id) LEFT JOIN merchant_timed_admissions tmd USING (tenant_id, operation_id)`.
   - Returns `None` in `find_provenance()` (or raises `MerchantSignerError` in `read_provenance()`) when all three tables are empty for the operation; raises `MerchantSignerError` on any fingerprint drift, orphan row, column corruption, or clock split-brain.

---

## 4. Verification & Regression Results

Added 6 unit tests (with 42 subtests) in [`tests/test_operation_admission_provenance.py`](../../tests/test_operation_admission_provenance.py):

- `test_unreserved_operation_returns_none_and_read_raises_without_creating_rows`
- `test_classifies_all_three_provenance_paths_and_survives_revocation_and_settlement`
- `test_rejects_untrusted_inputs_cross_file_stores_and_direct_dataclass_corruption`
- `test_rejects_ten_dimension_fingerprint_mismatches_and_table_fingerprint_drift`
- `test_rejects_cross_table_orphans_clock_split_brain_and_corrupted_columns`
- `test_single_select_snapshot_takes_no_write_locks_under_concurrent_writer`
