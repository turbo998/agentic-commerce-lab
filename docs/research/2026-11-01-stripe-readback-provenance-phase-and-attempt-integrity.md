# Stage 1743 — Stripe 回读与全生命周期溯源的 8 态阶段分类模型（`StripeReadbackPhase`）与支付尝试/已处理认领闭锁不变量

> **English companion**: [2026-11-01-stripe-readback-provenance-phase-and-attempt-integrity.en.md](2026-11-01-stripe-readback-provenance-phase-and-attempt-integrity.en.md)  
> **状态**：已实现并验证（`2026-11-01`）  
> **关联模块**：[`lab/stripe_readback.py`](../../lab/stripe_readback.py)、[`lab/merchant_signers.py`](../../lab/merchant_signers.py)、[`tests/test_stripe_readback_provenance.py`](../../tests/test_stripe_readback_provenance.py)、[`tests/test_stripe_lifecycle_provenance.py`](../../tests/test_stripe_lifecycle_provenance.py)、[`tests/test_operation_admission_provenance.py`](../../tests/test_operation_admission_provenance.py)

---

## 1. 背景与架构问题

在 Stage 1732、1736 与 1738 建立的跨表溯源模型（`OperationAdmissionProvenance`、`StripeReadbackProvenance` 与 `StripeLifecycleProvenance`）中，存在三处需要闭锁收敛的跨表不变量与可观测性缺口：

1. **未绑定 `provider_reference` 的终态支付尝试（`outcome in ("succeeded", "failed")` 且 `provider_reference is None`）未被拦截**：
   - 尽管 `PaymentAttemptJournal.read_attempt()`、`ApprovalAdmissionProvenance.__post_init__()` 与 `MerchantSignerStore.find_provenance()` 均拒绝 `provider_reference is None` 的终态行，但 `OperationAdmissionProvenance.__post_init__()`、`StripeReadbackProvenance.__post_init__()` 与 `StripeLifecycleProvenance.__post_init__()` 未检查该不变量。
   - 更严重的是，在 `StripeReadbackProvenance` 与 `StripeLifecycleProvenance` 中，跨表 `PaymentIntent` 引用比对仅在 `self.attempt.provider_reference is not None` 时触发；若 `payment_attempts` 被篡改为 `outcome='succeeded', provider_reference=NULL`，即使收件箱中存在指向不同 `pi_...` 的 `InboxReceipt`，跨表引用冲突检查也会被旁路。
2. **到达 Webhook 前的 `attempt.provider_reference` 缺少严格 `pi_[A-Za-z0-9_]+` 正则门禁**：
   - 当 `receipt is None`（Webhook 尚未到达）时，`StripeReadbackProvenance` 与 `StripeLifecycleProvenance` 接受任意非空字符串（如 `"ch_123"`、`"evt_123"`）作为 `attempt.provider_reference`，与 `InboxReceipt` 和 `validate_stripe_intent()` 的 `pi_[A-Za-z0-9_]+` 契约不一致。
3. **孤立的 `handled` 回读认领与多表恢复阶段缺乏确定性状态机投影**：
   - 在合法的 `accept_stripe_readback()` 或独立 `reconcile_stripe_intent()` 流程中，认领状态（`claim_status.state`）只有在本地 `payment_attempts` 已预留且已绑定 `pi_...` 引用后才能进入 `"handled"`。若 `claim_status.state == "handled"` 而 `attempt is None` 或 `attempt.provider_reference is None`，说明发生了跳过对账的提前结案或事后账本篡改。
   - 同时，恢复编排器需要一个零额外查询的确定性状态机属性（`readback_phase` 与 `event_phase`），将 `(attempt, receipt, claim_status)` 投影为精确的恢复阶段。

---

## 2. 核心设计（`lab/stripe_readback.py` 与 `lab/merchant_signers.py`）

### 2.1 跨表支付尝试与已处理认领闭锁不变量

1. **`OperationAdmissionProvenance.__post_init__()`**（`lab/merchant_signers.py`）：
   - 当 `self.attempt.provider_reference is None and self.attempt.outcome != "unknown"` 时，立即抛出 `MerchantSignerError("Stored attempt provider reference is invalid; reconciliation required.")`。
2. **`StripeReadbackProvenance.__post_init__()` 与 `StripeLifecycleProvenance.__post_init__()`**（`lab/stripe_readback.py`）：
   - 当 `self.attempt.provider_reference is None and self.attempt.outcome != "unknown"` 时，抛出 `StripeReadbackError("Stored attempt outcome and provider reference are inconsistent.")`。
   - 当 `self.attempt.provider_reference is not None` 且不匹配 `_PI_RE = re.compile(r"pi_[A-Za-z0-9_]+")` 时，抛出 `StripeReadbackError("Stored attempt provider reference must be a Stripe PaymentIntent ID.")`。
   - 当 `self.claim_status is not None and self.claim_status.state == "handled"` 且 `self.attempt is None or self.attempt.provider_reference is None` 时，抛出 `StripeReadbackError("Handled readback claim requires a PaymentIntent-associated attempt.")`。

### 2.2 8 态回读对账阶段分类模型（`StripeReadbackPhase`）

为 `StripeReadbackProvenance` 与 `StripeLifecycleProvenance` 新增 `event_phase: InboxEventPhase | None` 与 `readback_phase: StripeReadbackPhase`（在仅预置审批策略行的 `StripeLifecycleProvenance` 上返回 `None`）：

| `readback_phase` | `attempt.outcome` | `attempt.provider_reference` | `receipt` | `claim_status.state` | 架构语义 |
|---|---|---|---|---|---|
| `"webhook_before_reservation"` | `None` | `None` | 存在 | `None` / `"active"` | Webhook 先于本地操作预留到达并落盘 |
| `"reserved_unassociated"` | `"unknown"` | `None` | `None` | `None` | 本地已预留，既无出站 `pi_...` 绑定也无入站 Webhook |
| `"awaiting_intent_association"` | `"unknown"` | `None` | 存在 | `None` / `"active"` | Webhook 已到达，但本地尝试尚未完成可信 `associate_stripe_intent` 绑定 |
| `"associated_awaiting_webhook"` | `"unknown"` | `pi_...` | `None` | `None` | 出站 `pi_...` 已绑定，等待入站 Webhook 或主动回读 |
| `"ready_to_claim"` | `"unknown"` | `pi_...` | 存在 | `None` | 出站 `pi_...` 与入站收据均就绪，待工作器 `claim_next()` |
| `"claimed_awaiting_acceptance"` | `"unknown"` | `pi_...` | 存在 | `"active"` | 工作器已持有活动认领，待 `accept_stripe_readback()` 原子接纳 |
| `"handled_pending_outcome"` | `"unknown"` | `pi_...` | 存在 | `"handled"` | 认领已按中间态（如 `"processing"`）处理完毕，结果仍保持 `"unknown"` |
| `"terminal_reconciled"` | `"succeeded"` / `"failed"` | `pi_...` | 任意 | 任意 | 支付尝试已收敛至终态 |

---

## 3. 验证结果

- `python -m pytest tests/test_stripe_readback_provenance.py tests/test_stripe_lifecycle_provenance.py tests/test_operation_admission_provenance.py -q`：`16 passed, 204 subtests passed`。
- 全量回归测试套件通过，无真实资金、无外部网络调用或密钥使用。
