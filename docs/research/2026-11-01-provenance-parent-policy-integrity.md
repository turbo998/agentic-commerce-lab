# 五表准入溯源父级策略参照完整性与支付尝试读模型不变量（Stage 1734）

**English Version**: [2026-11-01-provenance-parent-policy-integrity.en.md](2026-11-01-provenance-parent-policy-integrity.en.md)

## 背景

在 Stage 1732 与 Stage 1733 中，`MerchantSignerStore.find_provenance()` 通过单条 `SELECT ... LEFT JOIN` 快照关联了三张按操作粒度索引的表（`payment_attempts`、`payment_admissions`、`merchant_timed_admissions`），并校验了反规范化唯一索引列。然而，`commerce.sqlite3` 中还存在两张只追加（append-only）、禁止替换或删除的**父级策略表**：

1. `payment_approvals (tenant_id, approval_id, fingerprint, expires_at, revoked)`：任何 `payment_admissions` 首门历史行都必须在 `PaymentApprovalStore._admit_in_transaction()` 中从对应的 `payment_approvals` 行复制 `expires_at` 生成，且事后撤销仅将 `revoked` 置为 `1`，永不删除行或修改 `fingerprint` / `expires_at`。
2. `merchant_signer_permissions (tenant_id, merchant, target_uri, key_id, revoked)`：任何 `merchant_timed_admissions` 限时签名历史行都必须在 `MerchantSignerStore.admit()` 中校验对应的 `merchant_signer_permissions` 行后生成，且事后撤销仅将 `revoked` 置为 `1`，永不删除行。

此外，`PaymentAttemptJournal._attempt()`（供 `read()`、`reserve()`、`reconcile()`、`associate_stripe_intent()` 调用）此前只检查了 `outcome`，未像 Stage 1728 的 `read_attempt()` 那样校验 `provider_reference` 的非空与类型不变量；`PaymentAttempt` 与 `DispatchDecision` 读模型也缺少构造期 `__post_init__` 自校验。

## 架构改进（Stage 1734）

### 1. `MerchantSignerStore.find_provenance` 五表联合快照与父级策略参照校验

将 `find_provenance()` 的单条 `SELECT ... LEFT JOIN` 扩展至全部 5 张治理与溯源表（均按各自 `PRIMARY KEY` 索引精确关联）：

- `payment_attempts` (`USING (tenant_id, operation_id)`)
- `payment_admissions` (`USING (tenant_id, operation_id)`)
- `payment_approvals` (`ON app.tenant_id = k.tenant_id AND app.approval_id = k.approval_id`)
- `merchant_timed_admissions` (`USING (tenant_id, operation_id)`)
- `merchant_signer_permissions` (`ON perm.tenant_id = k.tenant_id AND perm.merchant = k.merchant AND perm.target_uri = tmd.target_uri AND perm.key_id = tmd.key_id`)

在不额外增加 SQL 往返、不获取写锁且完全兼容事后策略撤销（`revoked = 1`）的前提下，新增以下闭锁（fail-closed）校验：

- **父级审批指纹绑定**：一旦操作已预留或存在准入记录且 `app_fingerprint` 非空，必须满足 `app_fingerprint == operation.fingerprint`。
- **父级审批存在性与过期时间一致性**：当存在 `payment_admissions` 行（`adm_fp is not None`）时，父级 `payment_approvals` 行必须存在（否则拒绝孤儿审批准入记录）、`app_expires_at` 必须为正 64 位整数、`app_revoked in (0, 1)`，且必须满足跨表过期时间一致性 `adm_expires_at == app_expires_at`。
- **父级签名者权限存在性与状态完整性**：当存在 `merchant_timed_admissions` 行（`tmd_fp is not None`）时，父级 `merchant_signer_permissions` 行必须存在（防止伪造未授权 `key_id` 或 `target_uri` 的限时准入历史），且 `perm_revoked in (0, 1)`。

### 2. `PaymentAttempt`、`DispatchDecision` 与 `_reconcile_in_transaction()` 的统一闭锁校验

- `PaymentAttempt.__post_init__`：强制校验 `outcome in ("unknown", "succeeded", "failed")`；当 `provider_reference` 非空时要求为非空白字符串。
- `DispatchDecision.__post_init__`：强制校验 `attempt` 类型、`type(dispatch_allowed) is bool`，并禁止对已终态（`outcome != "unknown"`）或已绑定外部引用（`provider_reference is not None`）的尝试授予 `dispatch_allowed=True`。
- `PaymentAttemptJournal._attempt()`、`read_attempt()` 与 `_reconcile_in_transaction()` 统一复用 `PaymentAttempt` 构造校验，并在 `_reconcile_in_transaction()` 中闭锁拦截未关联外部引用的终态行（`previous.provider_reference is None and previous.outcome != "unknown"`）。

## 测试与验证

新增 `tests/test_provenance_parent_policy_integrity.py`，覆盖：

- 无 `payment_approvals` 行的直接预留（`direct_reservation`）正常返回，但若存在同 `approval_id` 的冲突指纹行则闭锁拒绝。
- 审批与签名者权限双重撤销（`revoked = 1`）后五表溯源快照依然可读；删除父级策略行、篡改 `payment_approvals.expires_at` / `revoked`、制造 `adm.expires_at != app.expires_at` 分裂或伪造未登记 `key_id` 的限时准入行均闭锁抛出 `MerchantSignerError`。
- `PaymentAttempt` 与 `DispatchDecision` 的构造期不变量校验，以及 `read()`、`read_attempt()`、`reserve()`、`reconcile()` 对损坏 `provider_reference` 的统一闭锁拦截。
