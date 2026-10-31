# Stage 1732 — 跨表准入溯源单快照只读审计（`MerchantSignerStore.find_provenance` / `read_provenance`）

> **English companion**: [2026-11-01-operation-admission-provenance.en.md](2026-11-01-operation-admission-provenance.en.md)  
> **验证日期（北京时间）**：`2026-11-01`（窗口 `00:49–01:02+08:00`）  
> **关联资产**：[`lab/merchant_signers.py`](../../lab/merchant_signers.py) · [`tests/test_operation_admission_provenance.py`](../../tests/test_operation_admission_provenance.py)

---

## 1. 背景与问题定义

在完成 Stage 1728（`PaymentAttemptJournal.read_attempt`）、Stage 1729（`PaymentApprovalStore.find_admission`）与 Stage 1730（`MerchantSignerStore.find_timed_admission`）后，单表层面的无锁只读查询已全部完备。然而在并发准入与故障排障场景下，若运维或对账逻辑依次在三个独立 SQLite 连接上调用 `read_attempt()`、`find_admission()` 与 `find_timed_admission()`，仍存在两个核心架构隐患：

1. **多连接顺序读取的 TOCTOU 读偏斜（Read Skew）**：当并发写线程正在执行 `approvals.admit()` 或 `signers.admit()` 并提交事务时，跨三次独立连接读取可能在第 1 次查询时看到“无 `payment_attempts`”，而在第 2、3 次查询时看到刚提交的 `payment_admissions` 与 `merchant_timed_admissions`，从而产生虚假的“有准入历史但无尝试预留”读偏斜。
2. **跨表因果不变量与时钟裂脑（Clock Split-Brain）缺失统一校验**：
   - 在合法的本地准入路径中，`payment_admissions` 行绝不可能脱离 `payment_attempts` 孤立存在，`merchant_timed_admissions` 行也绝不可能脱离 `payment_admissions` 和 `payment_attempts` 孤立存在。
   - 在计时签名路径（`MerchantSignerStore.admit`）中，`payment_admissions.admitted_at` 与 `merchant_timed_admissions.admitted_at` 必须在同一次 `BEGIN IMMEDIATE` 锁内共享同一次可信时钟采样（`tmd.admitted_at == adm.admitted_at`）。

---

## 2. 辩证架构分析：经典三层 Web 应用 vs. Agentic Commerce AI-Native 架构

| 架构维度 | 云服务商经典三层 Web / 微服务架构 | Agentic Commerce AI-Native 架构（Stage 1732） |
|---|---|---|
| **跨表/跨仓储只读聚合** | 在应用层拼装多次 DAO/Repository 查询（`getAttempt()` + `getApprovalAdmission()` + `getTimedAdmission()`），在并发写入下容易出现非原子读偏斜（Read Skew）。 | `MerchantSignerStore.find_provenance()` 强制验证三存储指向同一规范化 SQLite 文件后，在**单条 `SELECT ... LEFT JOIN` 语句快照**内原子读取三表状态，彻底消除多连接 TOCTOU 读偏斜。 |
| **执行路径分类（Provenance Path）** | 依赖外部日志或分布式追踪标签推断请求走了哪条鉴权分支。 | `OperationAdmissionProvenance.path` 基于单快照因果证据精确分类三类合法路径：`direct_reservation`（仅预留）、`approval_admission`（通用/裸签名审批准入）、`timed_signer_admission`（RFC 9421 计时签名准入）。 |
| **跨表因果与时钟一致性校验** | 仅校验单表字段格式，忽略跨表孤儿行或时间戳不一致。 | 失败关闭（Fail-Closed）拦截孤儿准入行（无 `payment_attempts` 的 `payment_admissions`/`merchant_timed_admissions`，或无 `payment_admissions` 的 `merchant_timed_admissions`）以及跨表时钟采样裂脑（`tmd.admitted_at != adm.admitted_at`）。 |

---

## 3. 核心实现细节（`lab/merchant_signers.py`）

1. **`OperationAdmissionProvenance` 不可变数据类**：
   - 字段：`fingerprint: str`、`attempt: PaymentAttempt`、`approval_admission: ApprovalAdmission | None`、`timed_signer_admission: TimedSignerAdmission | None`。
   - `__post_init__` 强校验：64 位小写十六进制 `fingerprint`、三表指纹完全一致、非孤立层级关系（`timed_signer_admission` 存在时 `approval_admission` 必不为 `None`）、跨表时钟采样一致（`timed_signer_admission.admitted_at == approval_admission.admitted_at`）且严格位于审批有效期内（`0 <= admitted_at < expires_at`）。
   - `path` 属性：返回 `"direct_reservation"` | `"approval_admission"` | `"timed_signer_admission"`。
2. **`MerchantSignerStore.find_provenance()` 与 `read_provenance()`**：
   - 校验 `approvals`、`journal`、`operation` 类型及 `self.path.resolve(strict=True) == approvals.path.resolve(strict=True) == journal.path.resolve(strict=True)`。
   - 使用单条锚定查询 `FROM (SELECT ? AS tenant_id, ? AS operation_id) k LEFT JOIN payment_attempts att USING (tenant_id, operation_id) LEFT JOIN payment_admissions adm USING (tenant_id, operation_id) LEFT JOIN merchant_timed_admissions tmd USING (tenant_id, operation_id)`。
   - 三表均无记录时 `find_provenance()` 返回 `None`，`read_provenance()` 抛出 `MerchantSignerError`；任一表指纹偏离、孤儿行、列值损坏或时钟不一致均抛出 `MerchantSignerError`。

---

## 4. 测试与回归验证

在 [`tests/test_operation_admission_provenance.py`](../../tests/test_operation_admission_provenance.py) 中新增 6 项测试（覆盖 42 个子测试）：

- `test_unreserved_operation_returns_none_and_read_raises_without_creating_rows`
- `test_classifies_all_three_provenance_paths_and_survives_revocation_and_settlement`
- `test_rejects_untrusted_inputs_cross_file_stores_and_direct_dataclass_corruption`
- `test_rejects_ten_dimension_fingerprint_mismatches_and_table_fingerprint_drift`
- `test_rejects_cross_table_orphans_clock_split_brain_and_corrupted_columns`
- `test_single_select_snapshot_takes_no_write_locks_under_concurrent_writer`
