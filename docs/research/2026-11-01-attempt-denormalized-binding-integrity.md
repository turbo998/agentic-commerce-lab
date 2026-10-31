# Stage 1733 — `payment_attempts` 反范式唯一索引列一致性与只读数据类构造期不变量加固

> **English companion**: [2026-11-01-attempt-denormalized-binding-integrity.en.md](2026-11-01-attempt-denormalized-binding-integrity.en.md)  
> **验证日期（北京时间）**：`2026-11-01`（窗口 `01:12–01:22+08:00`）  
> **关联资产**：[`lab/payment_attempts.py`](../../lab/payment_attempts.py) · [`lab/payment_approvals.py`](../../lab/payment_approvals.py) · [`lab/merchant_signers.py`](../../lab/merchant_signers.py) · [`tests/test_attempt_denormalized_binding_integrity.py`](../../tests/test_attempt_denormalized_binding_integrity.py)

---

## 1. 背景与问题定义

在 `PaymentAttemptJournal` 的 SQLite `payment_attempts` 表中，除了存储 10 维操作绑定摘要 `fingerprint` 外，还显式存储了四个反范式唯一约束列（Denormalized Uniqueness Columns）：
- `approval_id`（用于 `UNIQUE (tenant_id, approval_id)` 防止同一审批被多个操作重用）
- `provider`、`provider_account`、`idempotency_key`（用于 `UNIQUE (provider, provider_account, idempotency_key)` 与 `UNIQUE (provider, provider_account, provider_reference)` 以及 `reconcile()` 的跨操作 `provider_reference` 冲突查询）

此前实现中存在两处防御纵深盲区：
1. **反范式唯一索引列与 `fingerprint` 裂脑未被拦截**：`PaymentAttemptJournal._find()`、`read_attempt()` 与 `MerchantSignerStore.find_provenance()` 仅比对 `row["fingerprint"] == operation.fingerprint`，未校验持久化行中的 `approval_id`、`provider`、`provider_account`、`idempotency_key` 是否与 `operation` 完全一致。若存储层反范式列被篡改而 `fingerprint` 保持不变，SQLite 唯一索引与 `reconcile()` 的跨行查询将基于被篡改列执行，而操作绑定校验却静默放行。
2. **只读状态/历史数据类缺失构造期 `__post_init__` 强校验**：`PaymentApprovalStatus`、`ApprovalAdmission` 与 `TimedSignerAdmission` 原先仅在数据库读取方法中校验字段，直接内存构造时未强制执行失败关闭（Fail-Closed）不变量。

---

## 2. 辩证架构分析：经典三层 Web 应用 vs. Agentic Commerce AI-Native 架构

| 架构维度 | 云服务商经典三层 Web / ORM 架构 | Agentic Commerce AI-Native 架构（Stage 1733） |
|---|---|---|
| **摘要列与反范式索引列一致性** | 若存在 `payload_hash` 或 `fingerprint`，往往假定同行冗余索引列必然与哈希一致，不作二次核对。 | 显式认识到本地 SQLite 不具备自动校验 `fingerprint == sha256(...)` 的触发器：`PaymentAttemptJournal._verify_row_binding()` 与 `MerchantSignerStore.find_provenance()` 同时校验 `fingerprint` 及全部 4 个反范式唯一索引列（`approval_id`、`provider`、`provider_account`、`idempotency_key`），彻底阻断索引列与摘要列裂脑。 |
| **只读领域模型构造边界** | 将只读 DTO / Value Object 视为纯数据容器，仅在 DAO 查询层做一次校验。 | `PaymentApprovalStatus`、`ApprovalAdmission` 与 `TimedSignerAdmission` 全部在 `__post_init__` 中强制校验 64 位小写 SHA-256 指纹、严格 `int` 时间戳（拒绝 `bool` 伪整型）、时间区间单调性及 RFC 9421 签名标签正则，确保任何内存构造或反序列化路径均满足同等安全边界。 |

---

## 3. 核心实现细节

1. **`lab/payment_attempts.py`**：
   - 新增 `PaymentAttemptJournal._verify_row_binding(row, operation)`，同时核验 `fingerprint`、`approval_id`、`provider`、`provider_account` 与 `idempotency_key`；`_find()` 与 `read_attempt()` 统一复用该校验，任一列偏离立即抛出 `AttemptConflict("Operation binding changed; do not dispatch.")`。
2. **`lab/merchant_signers.py`**：
   - `MerchantSignerStore.find_provenance()` 在单条 `SELECT ... LEFT JOIN` 中一并选出 `att_approval_id`、`att_provider`、`att_provider_account`、`att_idempotency_key` 并与 `operation` 严格比对。
   - 为 `TimedSignerAdmission` 新增 `__post_init__` 失败关闭校验。
3. **`lab/payment_approvals.py`**：
   - 为 `PaymentApprovalStatus` 与 `ApprovalAdmission` 新增 `__post_init__` 失败关闭校验。

---

## 4. 测试与回归验证

在 [`tests/test_attempt_denormalized_binding_integrity.py`](../../tests/test_attempt_denormalized_binding_integrity.py) 中新增 4 项测试（覆盖 38 个子测试）：

- `test_approval_and_timed_admission_dataclasses_enforce_post_init_invariants`
- `test_corrupted_denormalized_attempt_columns_fail_closed_across_journal_methods`
- `test_corrupted_denormalized_attempt_columns_fail_closed_across_admission_and_provenance`
- `test_corrupted_denormalized_attempt_columns_block_stripe_association_and_readback`
