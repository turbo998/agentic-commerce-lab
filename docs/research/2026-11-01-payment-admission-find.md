# 2026-11-01 本地首次审批准入历史可选只读查询与未准入/绑定冲突消歧（Stage 1729）

> **English companion**: [2026-11-01-payment-admission-find.en.md](2026-11-01-payment-admission-find.en.md)

## 1. 背景与架构问题

在 `agentic-commerce-lab` 的本地三道交易执行围栏（`MerchantSignerStore` $\rightarrow$ `PaymentApprovalStore` $\rightarrow$ `PaymentAttemptJournal`）中，Stages 1726–1728 依次为审批状态表（`payment_approvals`）、商家签名密钥权限表（`merchant_signer_permissions`）以及支付尝试账本（`payment_attempts`）补齐了无写锁（`SELECT`-only）且将“记录不存在（返回 `None`）”与“绑定冲突/数据损坏（抛出异常）”消歧的只读查询方法。

然而，在记录**首次穿过审批门禁并获得派发资格的本地时间证据表** `payment_admissions`（`lab/payment_approvals.py`）中，原有的 `read_admission(operation) -> ApprovalAdmission` 仍在两类截然不同的情况下抛出同一异常 `PaymentApprovalError`：

1. **尚未发生首次准入或旧版预留（Benign Absence）**：操作已获批但尚未调用 `admit()`，或操作由旧版 `PaymentAttemptJournal.reserve()` 直接预留而未回填 `payment_admissions`（`PaymentApprovalError("No first-admission record exists for this operation.")`）；
2. **操作绑定指纹篡改或时间戳损坏（Integrity Conflict）**：持久化准入记录的 `fingerprint` 与传入 `operation` 不一致，或 `admitted_at` / `expires_at` 不满足 `0 <= admitted_at < expires_at <= 2**63 - 1`。

## 2. 官方来源核验与架构映射（2026-11-01）

| 外部协议 / 产品面 | 首次发布 / 窗口 | 当日核验状态（2026-11-01） | 本地 Stage 1729 架构映射 |
|---|---|---|---|
| **Stripe MCP 密钥迁移窗口（跨过 `2026-10-31` 首日核验）** | 顶栏公告截止 `2026-10-31` / `after November 1, 2026`；正文仍写 `after November 30, 2026` | `2026-11-01` 首日实测：`docs.stripe.com/mcp.md` 仍保留两处日期矛盾；`calendar_days_until_deadline = 29`（距 `2026-11-30`），但已跨过 `2026-10-31` | 在密钥切换与回滚排障期，运维需无锁区分“审批从未触发首次准入 (`None`)”与“准入记录被篡改 (`PaymentApprovalError`)” |
| **Stripe Shared Payment Tokens (SPT)** | 预览版 `2026-03-04.preview` | 卖方/Connect 双页 `34` 国一致（SHA-256 `6ae0a508...`） | 区分预授权状态（`read_approval`）与首次扣款准入时间点证明（`find_admission`） |
| **Stripe Link Agent Wallet** | 私有预览（Private Preview） | 准入申请表单：`https://docs.stripe.com/forms/agent-wallet-interest` | 保持本地只读准入溯源与真实外部钱包授权解耦 |

## 3. 设计与实现（`lab/payment_approvals.py`）

在 `PaymentApprovalStore` 中新增 `find_admission(operation: PaymentOperation) -> ApprovalAdmission | None`，并将原有 `read_admission(operation) -> ApprovalAdmission` 重构为其严格包装器（当返回 `None` 时抛出原有异常，保持 100% 向后兼容）：

1. **连接前输入校验**：调用 `self._require_operation(operation)`，若非 `PaymentOperation` 实例则在打开 SQLite 连接前抛出 `PaymentApprovalError`。
2. **无写锁只读查询（`SELECT`-Only）**：仅执行 `SELECT fingerprint,admitted_at,expires_at FROM payment_admissions WHERE tenant_id=? AND operation_id=?`，不开启 `BEGIN IMMEDIATE`。
3. **未准入与绑定冲突消歧**：
   - 若 `(tenant_id, operation_id)` 无记录（包括尚未准入、准入被拒绝回滚、或旧版直接 `reserve()` 未回填），返回 `None`；
   - 若记录存在但 `row["fingerprint"] != operation.fingerprint`，抛出 `PaymentApprovalError("Admission record differs from the bound operation.")`；
   - 若 `admitted_at` 或 `expires_at` 非精确整数或违反 `0 <= admitted_at < expires_at <= 2**63 - 1`，抛出 `PaymentApprovalError("Stored admission times are invalid.")`。

## 4. 验证结果

- 定向测试：`python -m pytest tests/test_payment_admission_find.py tests/test_admission_provenance.py tests/test_payment_approval_read.py -v`（`44 passed, 54 subtests passed`，其中新增 `test_payment_admission_find.py` 为 `9 passed, 23 subtests passed`）。
- 全量回归：`python -m pytest -q`（`4304 passed, 1164 subtests passed`）。
