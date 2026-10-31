# Stage 1749：Stripe `PaymentIntent` 首次关联绑定的无锁单 `SELECT` 预检（`StripeAssociationPreview`）与对账相位对齐

> **验证日期**：2026-11-01（北京时间 `UTC+08:00`）  
> **英文版（English Version）**：[`2026-11-01-stripe-intent-association-dry-run-preview.en.md`](2026-11-01-stripe-intent-association-dry-run-preview.en.md)  
> **关联资产**：[`lab/stripe_observation.py`](../../lab/stripe_observation.py)、[`tests/test_stripe_association.py`](../../tests/test_stripe_association.py)

---

## 1. 背景与架构问题

在 Stage 1741 为 `reconcile_stripe_intent()` 引入 `StripeObservationPreview` 之后，`lab/stripe_observation.py` 中的另一个核心状态跃迁函数——**首次绑定 `PaymentIntent` 引用（`associate_stripe_intent()`）**——仍缺少对应的只读 dry-run 预检原语：

1. **`associate_stripe_intent()` 具有不同于 `reconcile_stripe_intent()` 的状态转移不变量**：
   - 即使传入的 `PaymentIntent` 快照状态已是 `"succeeded"` 或 `"canceled"`，首次关联绑定也**绝不推进终态**（始终以 `observation="pending"` 写入 `PaymentAttempt("unknown", expected_reference)`，将状态从 `"reserved_unassociated"` 跃迁至 `"pending_associated"`）。
   - 而当同一 `expected_reference` 重入已绑定（含已对账终态）的操作时，`associate_stripe_intent()` 保持已有 `previous` 不变（`would_bind=False`），不会把 `"succeeded_terminal"` 降级回 `"unknown"`。
2. **缺乏跨操作 `reference_conflict` 的单查询无锁预检**：
   - 在不开启 `BEGIN IMMEDIATE` 写事务的前提下，恢复编排器需要单条 `SELECT` 同时验证 `(tenant_id, operation_id)` 的反规范化操作绑定、检验 `expected_reference` 是否已被同一 `(provider, provider_account)` 下的其他操作占用（`reference_conflict`），并校验 `PaymentIntent` 快照与报价的金额、币种、直连账户路由（`transfer_data=None`、`on_behalf_of=None`）一致性。

---

## 2. AI-Native 架构设计

### 2.1 `StripeAssociationPreview` 与 `StripeObservationPreview` 相位属性

在 `lab/stripe_observation.py` 中：

- 为 `StripeObservationPreview` 新增 `previous_phase: AttemptPhase` 与 `next_phase: AttemptPhase` 属性。
- 新增不可变数据类 `StripeAssociationPreview`，并在 `__post_init__` 中强制闭锁校验：
  - `expected_reference` 必须匹配 `pi_[A-Za-z0-9_]+`；
  - `previous.provider_reference` 若与 `expected_reference` 冲突则抛出 `AttemptConflict("Provider reference changed; investigate the conflict.")`；
  - 若 `previous.provider_reference is None` 且 `previous.outcome != "unknown"`，抛出 `AttemptConflict("An unassociated terminal attempt cannot be rebound.")`；
  - 首次绑定（`previous.provider_reference is None`）必须满足 `would_bind=True` 且 `next_attempt == PaymentAttempt("unknown", expected_reference)`；
  - 幂等重入（`previous.provider_reference == expected_reference`）必须满足 `would_bind=False` 且 `next_attempt == previous`。
  - 提供 `previous_phase`、`next_phase` 与 `is_already_bound` 属性。

### 2.2 单条无锁 `SELECT` 预检函数

新增 `find_stripe_association_preview()`、`read_stripe_association_preview()` 与 `preview_associate_stripe_intent()`：

- 通过单条无写锁 `SELECT p.*, CASE WHEN EXISTS (...) THEN 1 ELSE 0 END AS reference_conflict FROM payment_attempts p WHERE p.tenant_id = ? AND p.operation_id = ?` 同时完成操作存在性检查、反规范化列绑定校验、`validate_stripe_intent()` 快照校验以及跨操作唯一引用冲突检查。
- 当操作未预留时，`find_stripe_association_preview()` 返回 `None`，`read_stripe_association_preview()` / `preview_associate_stripe_intent()` 抛出 `AttemptConflict("Operation was never reserved.")`。

---

## 3. 验证结果

```text
python -m pytest tests/test_stripe_association.py tests/test_stripe_observation.py -q
49 passed, 124 subtests passed
```
