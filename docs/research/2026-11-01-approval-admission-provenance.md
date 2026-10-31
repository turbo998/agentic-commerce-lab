# Stage 1735：双存储审批准入溯源单快照只读审计与策略表写入路径闭锁校验

> **日期**：2026-11-01（北京时间 `UTC+08:00`）  
> **阶段**：Stage 1735  
> **核心模块**：`lab/payment_approvals.py`、`lab/merchant_signers.py`、`lab/stripe_readback.py`、`lab/stripe_delivery.py`、`tests/test_approval_admission_provenance.py`  
> **English Version**: [`2026-11-01-approval-admission-provenance.en.md`](2026-11-01-approval-admission-provenance.en.md)

---

## 1. 背景与架构问题

在 Stage 1732–1734 中，我们为三存储拓扑（`MerchantSignerStore` + `PaymentApprovalStore` + `PaymentAttemptJournal`）设计了五表联查单快照只读审计方法 `MerchantSignerStore.find_provenance()`。然而在实际生产部署中，许多轻量商户结账网关仅部署**双存储拓扑**（`PaymentApprovalStore` + `PaymentAttemptJournal`，不启用 `MerchantSignerStore` 的多密钥与限时签名控制）。同时，在审查 `PaymentApprovalStore`、`MerchantSignerStore`、`accept_stripe_readback` 与 `VerifiedDelivery` 的读写边界时，我们识别出三项结构性缺口：

1. **双存储拓扑缺乏单快照跨表溯源审计器**：
   - 在仅部署 `PaymentApprovalStore` + `PaymentAttemptJournal` 的环境中，调用方若分别调用 `journal.read_attempt(operation)`、`approvals.read_approval(operation)` 与 `approvals.find_admission(operation)`，不仅需要开启三次独立的 SQLite 连接与事务（存在并发准入/撤销/对账下的读偏斜），而且各单表查询无法检测跨表孤儿行（如缺失 `payment_attempts` 预留行或缺失父表 `payment_approvals` 策略行的孤立 `payment_admissions` 行）以及跨表过期时间分裂（`payment_admissions.expires_at != payment_approvals.expires_at`）。
2. **`revoke()` 与 `admit()` 写路径对已损坏的父表策略列缺少前置闭锁校验**：
   - `PaymentApprovalStore._bound_approval(db, operation)` 原先仅校验行存在性与 `fingerprint`，导致：
     - `PaymentApprovalStore.revoke(operation)` 在 `payment_approvals` 行的 `expires_at`（如 `0`、`-5`、`1.5`、`'invalid'`）或 `revoked`（如 `2`、`-1`、`b'0'`、`'revoked'`）发生存储损坏时，会静默覆盖 `revoked = 1` 并掩盖存储篡改；
     - `PaymentApprovalStore._admit_in_transaction()` 先执行 `if row["revoked"] != 0: raise PaymentApprovalError("Approval is revoked.")`，将损坏的 `revoked = 2` 或 `revoked = 'revoked'` 误报为正常的业务已撤销状态。
   - 同理，`MerchantSignerStore._permission(db, scope)` 原先未校验 `row["revoked"] in (0, 1)`，导致 `signers.revoke(scope)` 会静默覆盖损坏行，而 `signers.admit(...)` 会将 `revoked = 2` 误报为 `"Signer permission is revoked."`。
3. **Stripe 回读接收前置参数校验与 `VerifiedDelivery` 构造期不变量缺口**：
   - `accept_stripe_readback()` 在校验 `inbox`、`journal`、`claim`、`operation` 类型前便直接访问 `.path` 或开启 SQLite `BEGIN IMMEDIATE` 事务；
   - `VerifiedDelivery` 数据类缺少 `__post_init__` 闭锁不变量校验。

---

## 2. AI-Native 架构设计改进

### 2.1 `ApprovalAdmissionProvenance` 与三表联查单快照只读审计

在 `lab/payment_approvals.py` 中新增不可变数据类 `ApprovalAdmissionProvenance` 及 `PaymentApprovalStore.find_provenance(journal, operation)` / `read_provenance(journal, operation)`：

```sql
SELECT
    att.fingerprint AS att_fingerprint,
    att.approval_id AS att_approval_id,
    att.provider AS att_provider,
    att.provider_account AS att_provider_account,
    att.idempotency_key AS att_idempotency_key,
    att.outcome AS att_outcome,
    att.provider_reference AS att_provider_reference,
    adm.fingerprint AS adm_fingerprint,
    adm.admitted_at AS adm_admitted_at,
    adm.expires_at AS adm_expires_at,
    app.fingerprint AS app_fingerprint,
    app.expires_at AS app_expires_at,
    app.revoked AS app_revoked
FROM (SELECT 1)
LEFT JOIN payment_attempts att
    ON att.tenant_id=? AND att.operation_id=?
LEFT JOIN payment_admissions adm
    ON adm.tenant_id=? AND adm.operation_id=?
LEFT JOIN payment_approvals app
    ON app.tenant_id=? AND app.approval_id=?
```

| 审计场景 | `payment_attempts` | `payment_approvals` | `payment_admissions` | `find_provenance()` 行为 |
|---|---|---|---|---|
| **未预留（含仅预置审批但未准入）** | `NULL` | `NULL` 或存在 | `NULL` | 返回 `None`（`read_provenance()` 抛出 `PaymentApprovalError`） |
| **直接预留（无审批记录）** | 存在 | `NULL` | `NULL` | 返回 `ApprovalAdmissionProvenance(..., approval_status=None, approval_admission=None)` |
| **直接预留（含已激活或已撤销审批）** | 存在 | 存在 (`revoked IN (0,1)`) | `NULL` | 返回 `ApprovalAdmissionProvenance(..., approval_status=PaymentApprovalStatus(...), approval_admission=None)` |
| **标准审批准入（含事后撤销与对账）** | 存在 | 存在 (`revoked IN (0,1)`) | 存在 (`adm.expires_at == app.expires_at`) | 返回完整三表快照 |
| **孤儿准入行（无预留行或无父审批行）** | `NULL` 或存在 | `NULL` 或存在 | 存在 | 抛出 `PaymentApprovalError` |
| **跨表过期时间分裂** | 存在 | `expires_at = T1` | `expires_at = T2 != T1` | 抛出 `PaymentApprovalError` |

### 2.2 策略表 `_bound_approval()` 与 `_permission()` 写路径前置闭锁校验

- `PaymentApprovalStore._bound_approval(db, operation)` 统一校验 `expires_at`（正 64 位有符号整数）与 `revoked in (0, 1)`，确保 `revoke()` 与 `admit()` 在遇到损坏策略行时立即抛出 `PaymentApprovalError` 并拒绝写入。
- `MerchantSignerStore._permission(db, scope)` 统一校验 `revoked in (0, 1)`，确保 `revoke()` 与 `admit()` 在遇到损坏权限行时立即抛出 `MerchantSignerError("Stored signer permission revocation state is invalid.")`。
- `accept_stripe_readback()` 在触碰文件系统或开启 SQLite 连接前校验 `inbox`、`journal`、`claim`、`operation` 类型；`VerifiedDelivery.__post_init__()` 强制校验 `timestamp`、`payload_sha256` 与 `requires_readback is True`。

---

## 3. 验证结果

- 新增测试套件：`tests/test_approval_admission_provenance.py`（`4 passed, 61 subtests passed`）。
- 关联回归测试：`121 passed, 315 subtests passed`；全量测试套件：`4333 passed, 1444 subtests passed`。
