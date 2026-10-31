# 2026-11-01 Stage 1746：支付审批与商户签名准入无锁单 `SELECT` 预检及 Provenance 生命周期相位对齐

**English Version**: [2026-11-01-approval-and-signer-admission-dry-run-preview.en.md](2026-11-01-approval-and-signer-admission-dry-run-preview.en.md)

## 1. 背景与架构痛点

在完成 `CheckoutStore.preview_execute()`（Stage 1744）、`find_stripe_observation_preview()`（Stage 1741）以及 `PaymentAttemptJournal.preview_reserve()` / `preview_reconcile()` 与 `preview_signed_checkout()`（Stage 1745）之后，仓库的其余两个核心跨表准入平面——**支付审批准入（`PaymentApprovalStore.admit()`）** 与 **商户签名权限/时间窗准入（`MerchantSignerStore.admit()`）**——仍缺少无锁单 `SELECT` 预检接口与统一的生命周期相位投影：

1. **支付审批状态缺少时钟求值辅助方法，且双库 Provenance 缺少路径与生命周期相位属性**：
   `PaymentApprovalStatus` 仅暴露静态 `state in ("active", "revoked")` 与 `expires_at`，未提供在指定可信 64 位非负整数时钟 `now` 下按 `revoked > expired > active` 优先级求值的 `state_at(now) -> ApprovalTimedState`。同时，`ApprovalAdmissionProvenance` 未暴露 `.path`（`TwoStoreAdmissionPath = Literal["direct_reservation", "approval_admission"]`）与 `.attempt_phase`（`AttemptPhase`），`OperationAdmissionProvenance` 也未暴露 `.attempt_phase`。
2. **`PaymentApprovalStore` 缺少无锁单 `SELECT` 准入预检（`preview_admit()`）**：
   调用方若需在开启 `BEGIN IMMEDIATE` 写锁前预检某笔带 RFC 9421 请求绑定的支付审批准入是否会获批、是否会首次写入 `payment_admissions`、或是否因重试/历史直接预留而拒绝放行且**绝不回填（non-backfill）** `payment_admissions`，原先只能直接执行写事务。
3. **`MerchantSignerStore` 缺少跨 5 表的无锁单 `SELECT` 准入预检（`preview_admit()`）**：
   `MerchantSignerStore.admit()` 在同一事务内串联校验 `merchant_signer_permissions`、`payment_approvals`、可选 RFC 9421 签名时间窗 `[created, expires)`、`payment_attempts`、`payment_admissions` 与 `merchant_timed_admissions`。调用方缺少一条不获取写锁、单条 `SELECT` 同时投影审批准入与时间窗签名准入（及重试不回填语义）的只读预检契约。

---

## 2. AI Native 架构设计（Stage 1746）

### 2.1 `PaymentApprovalStatus.state_at(now)` 与 Provenance 相位对齐

在 `lab/payment_approvals.py` 与 `lab/merchant_signers.py` 中引入：

- `ApprovalTimedState = Literal["active", "expired", "revoked"]` 与 `PaymentApprovalStatus.state_at(now: int) -> ApprovalTimedState`：
  严格校验 `now` 为非负有符号 64 位整数（拒绝 `bool`、负数、浮点数与 `> 2**63 - 1`），并按 `admit()` 的真实判断顺序返回 `"revoked"`（当 `state == "revoked"` 时优先于过期）、`"expired"`（当 `now >= expires_at`）或 `"active"`。
- `TwoStoreAdmissionPath = Literal["direct_reservation", "approval_admission"]`、`ApprovalAdmissionProvenance.path`、`ApprovalAdmissionProvenance.attempt_phase` 与 `OperationAdmissionProvenance.attempt_phase`：
  使两级与三级跨表 Provenance 快照均直接暴露 4 态支付尝试相位（`reserved_unassociated` / `pending_associated` / `succeeded_terminal` / `failed_terminal`）与准入路径枚举。

### 2.2 `ApprovalAdmissionPreview` 与 `PaymentApprovalStore.preview_admit()`

在 `lab/payment_approvals.py` 中新增不可变数据类 `ApprovalAdmissionPreview` 与 `PaymentApprovalStore.preview_admit(...)`：

- 先在连接外完成 `validate_signed_checkout(...)` 与同库解析路径校验；
- 通过**单条无锁 `SELECT`** 联表查询 `payment_approvals`、`payment_attempts`、`payment_admissions` 以及 `approval_conflict` / `idempotency_conflict` 子查询；
- 严格复刻 `admit()` 的校验顺序与**非回填（non-backfill）不变量**：
  - 当 `existing_attempt is None` 时：`decision = DispatchDecision(PaymentAttempt("unknown", None), True)`，`would_record_admission = True`，`projected_admission = ApprovalAdmission(operation.fingerprint, now, approval_status.expires_at)`；
  - 当 `existing_attempt is not None` 时：`decision = DispatchDecision(existing_attempt, False)`，`would_record_admission = False`，`projected_admission = existing_admission`（若原操作通过 `journal.reserve()` 直接预留而无 `payment_admissions` 行，`projected_admission` 保持 `None`，绝不回填）。

### 2.3 `SignerAdmissionPreview` 与 `MerchantSignerStore.preview_admit()`

在 `lab/merchant_signers.py` 中新增不可变数据类 `SignerAdmissionPreview` 与 `MerchantSignerStore.preview_admit(...)`：

- 通过**单条无锁 `SELECT`** 同时联表读取 `merchant_signer_permissions`、`payment_approvals`、`payment_attempts`、`payment_admissions`、`merchant_timed_admissions` 及冲突存在性位；
- 按 `MerchantSignerStore.admit()` 的精确顺序校验：签名者权限未吊销 $\rightarrow$ 审批存在且未吊销 $\rightarrow$ 若输入为 `TimedRequestSignatureSnapshot` 则校验 `require_signature_time(timed, now=now)` $\rightarrow$ 时钟类型与审批未过期 $\rightarrow$ 存量准入行与孤儿行完整性 $\rightarrow$ 预留/幂等冲突与非回填投影；
- 暴露 `.dispatch_allowed`、`.attempt_phase` 与 `.projected_path`（`"timed_signer_admission"` / `"approval_admission"` / `"direct_reservation"`）。

---

## 3. 验证结果

- 定向测试：`tests/test_approval_admission_provenance.py`、`tests/test_payment_approvals.py`、`tests/test_payment_approval_read.py`、`tests/test_merchant_signers.py`、`tests/test_timed_signer_admission_find.py` 全部通过（`85 passed, 207 subtests passed`）。
- 全量回归测试：将在提交前运行 `python -m pytest -q` 验证全仓通过。
