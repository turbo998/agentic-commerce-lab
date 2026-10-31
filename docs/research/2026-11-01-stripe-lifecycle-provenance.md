# Stage 1738 — 跨平面全生命周期（5 表 / 7 表）准入至回读单快照只读溯源审计（`StripeLifecycleProvenance`）

> **English companion**: [2026-11-01-stripe-lifecycle-provenance.en.md](2026-11-01-stripe-lifecycle-provenance.en.md)  
> **阶段编号**：Stage 1738  
> **核验日期（北京时间）**：`2026-11-01`  
> **关联资产**：[`lab/stripe_readback.py`](../../lab/stripe_readback.py)、[`tests/test_stripe_lifecycle_provenance.py`](../../tests/test_stripe_lifecycle_provenance.py)

---

## 1. 背景与架构痛点（AI-Native 交易架构 vs. 经典三层 Web 架构）

在 Agentic Commerce 的本地持久化控制平面中，一笔支付操作从“操作员审批与 RFC 9421 计时签名准入”到“Stripe Webhook 验签收据、回读认领交接与 `PaymentIntent` 终态对账”跨越两个子平面、最多 **7 张 SQLite 表**：

1. **准入控制平面（5 张表）**：`payment_approvals`、`payment_admissions`、`merchant_signer_permissions`、`merchant_timed_admissions`、`payment_attempts`。
2. **回读对账平面（3 张表，以 `payment_attempts` 为桥接表）**：`payment_attempts`、`stripe_event_inbox`、`stripe_readback_claims`。

在 Stage 1738 之前，若运维审计或争议举证需要同时观测某笔支付的**准入证据链**与**回读对账状态**，调用方不得不先后调用 `signers.find_provenance()`（时刻 $T_1$）与 `find_stripe_readback_provenance()`（时刻 $T_2$）：

- **跨平面撕裂读竞态（$T_1 \neq T_2$）**：在 $T_1$ 与 $T_2$ 之间，并发工作进程可能执行 `admit()`、`associate_stripe_intent()`、`accept_stripe_readback()`、`approvals.revoke()` 或 `signers.revoke()`，导致调用方将 $T_1$ 的“尚未预留”与 $T_2$ 的“已对账成功”拼装成自相矛盾的审计视图。
- **策略撤销态与预置审批不可见**：此前 `OperationAdmissionProvenance` 虽然校验了父表 `revoked IN (0, 1)`，但未向只读视图暴露 `PaymentApprovalStatus` 与 `MerchantSignerPermissionStatus`；且当操作员已预置审批（`approvals.approve`）或 Webhook 已先于 `reserve()` 到达时，`signers.find_provenance()` 仅返回 `None`。
- **可选签名器拓扑兼容需求**：部分商户部署仅启用 3 个存储（`StripeEventInbox` + `PaymentAttemptJournal` + `PaymentApprovalStore`，共 5 张表），而启用 RFC 9421 路由/密钥围栏的部署则包含 `MerchantSignerStore`（共 7 张表）。

---

## 2. Stage 1738 核心设计

### 2.1 `StripeLifecycleProvenance` 不可变跨平面溯源数据类

在 [`lab/stripe_readback.py`](../../lab/stripe_readback.py) 中新增 `StripeLifecycleProvenance`（`@dataclass(frozen=True)`）：

- 包含 10 个核心字段：`scope`、`event_id`、`fingerprint`、`attempt`、`approval_status`、`approval_admission`、`signer_permission`、`timed_signer_admission`、`receipt`、`claim_status`。
- 提供 3 个零额外查询的派生属性：
  - `admission_path -> AdmissionProvenancePath | None`：当 `attempt is None` 时返回 `None`；否则按 `timed_signer_admission` / `approval_admission` 精确返回 `"timed_signer_admission"`、`"approval_admission"` 或 `"direct_reservation"`。
  - `admission_provenance -> OperationAdmissionProvenance | None`：从同一 $T_0$ 快照直接投影出准入平面溯源对象。
  - `readback_provenance -> StripeReadbackProvenance | None`：从同一 $T_0$ 快照直接投影出回读平面溯源对象。
- 在 `__post_init__` 中强制执行全链路闭锁不变量：
  - 拒绝全空快照（`attempt`、`approval_status`、`receipt` 等全部为 `None`）。
  - 校验 `approval_status`、`approval_admission`、`timed_signer_admission` 的 64 位十六进制 SHA-256 `fingerprint` 与绑定操作一致。
  - 拦截无 `attempt` 或无 `approval_status` 的孤儿 `approval_admission`，并要求 `approval_admission.expires_at == approval_status.expires_at`。
  - 拦截无 `attempt`、无 `approval_admission` 或无 `signer_permission` 的孤儿 `timed_signer_admission`，校验 `signer_permission.scope == timed_signer_admission.scope`、租户一致性及跨表同一时钟采样 `timed_signer_admission.admitted_at == approval_admission.admitted_at`。
  - 校验 `receipt`、`claim_status` 与跨平面 `PaymentIntent` 引用一致性（`attempt.provider_reference == receipt.provider_reference`）。

### 2.2 `find_stripe_lifecycle_provenance()` 与 `read_stripe_lifecycle_provenance()`

- 支持 `signers: MerchantSignerStore | None = None` 可选关键字参数：
  - 当 `signers is None` 时，不要求存在 `merchant_signer_*` 表，执行单条 **5 表** `SELECT ... LEFT JOIN` 快照查询。
  - 当传入 `signers` 时，先校验四套存储指向同一 `Path.resolve(strict=True)` 物理 SQLite 文件，再执行单条 **7 表** `SELECT ... LEFT JOIN` 快照查询。
- 严格遵循只读无副作用契约：零 `BEGIN`、零 `INSERT`、零 `UPDATE`、零 `DELETE`、零时钟采样，且绝不赋予任何远程支付或准入权限。

---

## 3. 测试验证

新增 [`tests/test_stripe_lifecycle_provenance.py`](../../tests/test_stripe_lifecycle_provenance.py)：

- `python -m pytest tests/test_stripe_lifecycle_provenance.py tests/test_stripe_readback_provenance.py tests/test_stripe_readback.py -q`：`30 passed, 152 subtests passed`（其中 `test_stripe_lifecycle_provenance.py` 为 `5 passed, 61 subtests passed`）。
