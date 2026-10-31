# 2026-11-01 结账授权、支付审批与商户签名签发的无锁单 `SELECT` 预检（`MandateGrantPreview` / `ApprovalGrantPreview` / `SignerGrantPreview`）

> **Stage 1751** · 验证日期：`2026-11-01`（北京时间 `UTC+08:00`） · 关联代码：[`lab/checkout.py`](../../lab/checkout.py)、[`lab/payment_approvals.py`](../../lab/payment_approvals.py)、[`lab/merchant_signers.py`](../../lab/merchant_signers.py)、[`tests/test_checkout_provenance.py`](../../tests/test_checkout_provenance.py)、[`tests/test_approval_admission_provenance.py`](../../tests/test_approval_admission_provenance.py) · [English Version](2026-11-01-mandate-approval-and-signer-grant-dry-run-preview.en.md)

---

## 1. 背景与架构问题

在完成 Stages 1744–1750 后，Agentic Commerce 控制面的全部**执行、准入、对账、关联与撤销**跃迁均已具备无写锁单 `SELECT` 预检契约。为形成完整的全生命周期策略预演闭环，本次 Stage 1751 为三类**初始策略签发（Operator Provisioning / Grant）**入口补齐无写锁单 `SELECT` 预检：

1. **结账授权签发**（`CheckoutStore.approve()` $\rightarrow$ `MandateGrantPreview` / `preview_approve()`，见 [`lab/checkout.py`](../../lab/checkout.py)）；
2. **支付审批签发**（`PaymentApprovalStore.approve()` $\rightarrow$ `ApprovalGrantPreview` / `preview_approve()`，见 [`lab/payment_approvals.py`](../../lab/payment_approvals.py)）；
3. **商户签名密钥授权**（`MerchantSignerStore.allow()` $\rightarrow$ `SignerGrantPreview` / `preview_allow()`，见 [`lab/merchant_signers.py`](../../lab/merchant_signers.py)）。

---

## 2. 辩证架构分析：传统 Web App 三层架构 vs. Agentic Commerce AI-Native 架构

| 维度 | 传统 Web App 三层架构（Well-Architected） | Agentic Commerce AI-Native 工作负载架构 |
|---|---|---|
| **策略下发幂等与防覆盖校验** | 常采用 `INSERT OR REPLACE` 或 `UPSERT` 覆盖已有授权记录，存在静默篡改已消费或已撤销策略的风险 | 严格执行不可变单次签发（Forbidden Replacement），并通过 `MandateGrantPreview`、`ApprovalGrantPreview` 与 `SignerGrantPreview` 在无锁单 `SELECT` 下预检重复签发冲突 |
| **签发后初始状态投影** | 签发接口仅返回布尔成功或空值，调用方需二次查询才能获取绑定摘要与激活状态 | 预检结果直接构造并校验强类型 `MandateStatus`、`PaymentApprovalStatus` 与 `MerchantSignerPermissionStatus`（`state="active"`，`would_record=True`） |

---

## 3. Stage 1751 设计与实现要点

### 3.1 `MandateGrantPreview` 与 `CheckoutStore.preview_approve()`（`lab/checkout.py`）
- 新增不可变数据类 `MandateGrantPreview(mandate_id, checkout, max_amount, expires_at, projected_status, would_record)`，在 `__post_init__` 中校验 `max_amount >= checkout.amount`、`expires_at > 0`、`projected_status` 与 `checkout.digest` 一致且 `would_record is True`。
- 在 `CheckoutStore` 中新增 `preview_approve(mandate_id, checkout, *, max_amount, expires_at)`：通过单条无锁 `SELECT 1 FROM mandates WHERE id=?` 检测是否已存在同名授权（若已存在则闭锁抛出 `AuthorizationError`），并返回 `MandateGrantPreview`。

### 3.2 `ApprovalGrantPreview` 与 `PaymentApprovalStore.preview_approve()`（`lab/payment_approvals.py`）
- 新增不可变数据类 `ApprovalGrantPreview(operation, expires_at, projected_status, would_record)`，校验 `projected_status == PaymentApprovalStatus(operation.fingerprint, expires_at, "active")`。
- 在 `PaymentApprovalStore` 中新增 `preview_approve(operation, *, expires_at)`：通过单条无锁 `SELECT 1 FROM payment_approvals WHERE tenant_id=? AND approval_id=?` 预演签发冲突与投影状态。

### 3.3 `SignerGrantPreview` 与 `MerchantSignerStore.preview_allow()`（`lab/merchant_signers.py`）
- 新增不可变数据类 `SignerGrantPreview(scope, projected_status, would_record)`，校验 `projected_status == MerchantSignerPermissionStatus(scope, "active")`。
- 在 `MerchantSignerStore` 中新增 `preview_allow(scope)`：通过单条无锁 `SELECT 1 FROM merchant_signer_permissions WHERE tenant_id=? AND merchant=? AND target_uri=? AND key_id=?` 预演签名权限签发。

---

## 4. 测试与验证结果

在 [`tests/test_checkout_provenance.py`](../../tests/test_checkout_provenance.py) 与 [`tests/test_approval_admission_provenance.py`](../../tests/test_approval_admission_provenance.py) 中新增单 `SELECT` 跟踪断言、重复签发拒绝及数据类闭锁不变量测试：

- `python -m pytest tests/test_checkout_provenance.py tests/test_approval_admission_provenance.py -q`：`13 passed, 164 subtests passed`
