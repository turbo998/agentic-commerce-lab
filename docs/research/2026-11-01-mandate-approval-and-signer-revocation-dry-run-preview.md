# 2026-11-01 结账授权、支付审批与商户签名撤销的无锁单 `SELECT` 预检（`MandateRevocationPreview` / `ApprovalRevocationPreview` / `SignerRevocationPreview`）

> **Stage 1750** · 验证日期：`2026-11-01`（北京时间 `UTC+08:00`） · 关联代码：[`lab/checkout.py`](../../lab/checkout.py)、[`lab/payment_approvals.py`](../../lab/payment_approvals.py)、[`lab/merchant_signers.py`](../../lab/merchant_signers.py)、[`tests/test_checkout_provenance.py`](../../tests/test_checkout_provenance.py)、[`tests/test_approval_admission_provenance.py`](../../tests/test_approval_admission_provenance.py) · [English Version](2026-11-01-mandate-approval-and-signer-revocation-dry-run-preview.en.md)

---

## 1. 背景与架构问题

在 Stages 1744–1749 中，我们为 Agentic Commerce 的全部正向执行与对账跃迁路径补齐了无写锁单 `SELECT` 预检契约。然而，在安全应急响应、合规熔断或人工干预场景下，运维控制面还需要触发三类**不可逆权限撤销（Operator Revocation）**：

1. **结账授权撤销**（`CheckoutStore.revoke(mandate_id)`，见 [`lab/checkout.py`](../../lab/checkout.py)）；
2. **支付审批撤销**（`PaymentApprovalStore.revoke(operation)`，见 [`lab/payment_approvals.py`](../../lab/payment_approvals.py)）；
3. **商户签名密钥撤销**（`MerchantSignerStore.revoke(scope)`，见 [`lab/merchant_signers.py`](../../lab/merchant_signers.py)）。

此前这三项撤销操作仅提供直接持有 `BEGIN IMMEDIATE` 写锁的 `revoke()` 方法，缺少只读单 `SELECT` 预检模型来回答：目标权限当前处于 `active` 还是已处于 `revoked`（幂等无操作）、结账授权是否已产生已消费收据（`has_consumed_receipt`，决定撤销后相位是 `revoked_unspent` 还是 `consumed_revoked`），以及绑定指纹/范围是否匹配。

---

## 2. 辩证架构分析：传统 Web App 三层架构 vs. Agentic Commerce AI-Native 架构

| 维度 | 传统 Web App 三层架构（Well-Architected） | Agentic Commerce AI-Native 工作负载架构 |
|---|---|---|
| **权限吊销与状态预检** | 后台管理端直接执行 `UPDATE ... SET revoked=1` 并依赖受影响行数（rowcount）判断，无法区分未发生变更与已消费授权的撤销相位 | 显式建模 `MandateRevocationPreview`、`ApprovalRevocationPreview` 与 `SignerRevocationPreview`，在无锁单 `SELECT` 下区分首次撤销（`would_revoke=True`）与幂等重复撤销（`would_revoke=False`） |
| **已消费收据与孤儿行检测** | 仅查询 `mandates` 单表，忽略 `receipts` 子表是否已存在结算收据或孤儿收据 | `CheckoutStore.preview_revoke()` 在单条 `SELECT` 中同时联查 `mandates` 与 `receipts`，拒绝孤儿收据并精确推导 `existing_phase` / `projected_phase`（`revoked_unspent` vs. `consumed_revoked`） |
| **绑定完整性校验** | 仅按主键 ID 吊销，不验证操作指纹或商户签名四元组 | 严格复用 `_bound_approval()`、`_permission()` 与可选 `_verify_mandate_binding()`，任何绑定漂移或损坏列均触发闭锁异常 |

---

## 3. Stage 1750 设计与实现要点

### 3.1 `MandateRevocationPreview` 与 `CheckoutStore.preview_revoke()`（`lab/checkout.py`）
- 新增不可变数据类 `MandateRevocationPreview(mandate_id, existing_status, projected_status, would_revoke, has_consumed_receipt)`，并提供 `existing_phase` 与 `projected_phase` 属性（`active_unspent` / `revoked_unspent` / `consumed_active` / `consumed_revoked`）。
- 在 `CheckoutStore` 中新增 `preview_revoke(mandate_id, checkout=None)`：通过单条无锁 `SELECT ... LEFT JOIN mandates ... LEFT JOIN receipts` 读取授权与收据状态，拒绝孤儿收据并在传入 `checkout` 时校验商户、币种、限额与购物车摘要绑定。

### 3.2 `ApprovalRevocationPreview` 与 `PaymentApprovalStore.preview_revoke()`（`lab/payment_approvals.py`）
- 新增不可变数据类 `ApprovalRevocationPreview(operation, existing_status, projected_status, would_revoke)`，强制校验 `existing_status.fingerprint == operation.fingerprint`、`projected_status.state == "revoked"` 及 `would_revoke == (existing_status.state == "active")`。
- 在 `PaymentApprovalStore` 中新增 `preview_revoke(operation)`：在单条无写锁 `SELECT` 中复用 `_bound_approval(db, operation)` 完成策略行完整性校验与撤销预演。

### 3.3 `SignerRevocationPreview` 与 `MerchantSignerStore.preview_revoke()`（`lab/merchant_signers.py`）
- 新增不可变数据类 `SignerRevocationPreview(scope, existing_status, projected_status, would_revoke)`，强制校验 `existing_status.scope == scope`、`projected_status.state == "revoked"` 及 `would_revoke == (existing_status.state == "active")`。
- 在 `MerchantSignerStore` 中新增 `preview_revoke(scope)`：在单条无写锁 `SELECT` 中复用 `_permission(db, scope)` 完成签名权限完整性校验与撤销预演。

---

## 4. 测试与验证结果

在 [`tests/test_checkout_provenance.py`](../../tests/test_checkout_provenance.py) 与 [`tests/test_approval_admission_provenance.py`](../../tests/test_approval_admission_provenance.py) 中新增单 `SELECT` 跟踪断言、幂等重复撤销及数据类闭锁不变量测试：

- `python -m pytest tests/test_checkout_provenance.py tests/test_approval_admission_provenance.py -q`：`13 passed, 148 subtests passed`
