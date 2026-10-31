# 2026-10-31 本地支付尝试状态只读查询与未预留/绑定冲突消歧（Stage 1728）

> **English companion**: [2026-10-31-payment-attempt-read.en.md](2026-10-31-payment-attempt-read.en.md)

## 1. 背景与架构问题

在 `agentic-commerce-lab` 的本地三层支付门禁栈（`MerchantSignerStore` $\rightarrow$ `PaymentApprovalStore` $\rightarrow$ `PaymentAttemptJournal`）中：

- Stage 1726 为 `PaymentApprovalStore` 补齐了只读状态查询 `read_approval(operation) -> PaymentApprovalStatus | None`；
- Stage 1727 为 `MerchantSignerStore` 补齐了只读权限查询 `read_permission(scope) -> MerchantSignerPermissionStatus | None`；
- 而在底层执行账本 `PaymentAttemptJournal`（`lab/payment_attempts.py`）中，原有的 `read(operation) -> PaymentAttempt` 在两类截然不同的场景下均抛出同一异常 `AttemptConflict`：
  1. **操作从未预留（Benign Unreserved State）**：`AttemptConflict("Operation was never reserved.")`；
  2. **操作绑定指纹冲突（Security/Integrity Conflict）**：`AttemptConflict("Operation binding changed; do not dispatch.")` 或持久化行损坏。

对于只读审计、崩溃恢复前预检或运维排障而言，将“尚未预留”与“操作参数篡改/指纹冲突”混入同一个异常类型迫使调用方解析异常字符串，且在传入非法 `operation` 对象时 `read()` 会先打开 SQLite 连接再触发 `AttributeError`。

## 2. 官方来源核验与架构映射（2026-10-31）

| 外部协议 / 产品面 | 首次发布 / 窗口 | 当日核验状态（2026-10-31） | 本地 Stage 1728 架构映射 |
|---|---|---|---|
| **Stripe幂等键与支付尝试对账（ACP / SPT / PaymentIntents）** | 2025–2026 持续演进 | `51/51` 来源 `status="ok"` | 严格区分“幂等尝试尚未预留 (`None`)”、“尝试处于未决对账状态 (`unknown`)”与“参数篡改导致的指纹冲突 (`AttemptConflict`)” |
| **Stripe Link Agent Wallet** | 私有预览（Private Preview） | 表单：`https://docs.stripe.com/forms/agent-wallet-interest` | 面向未来托管代理钱包预授权前后的本地尝试账本只读巡检，不触碰真实支付网络 |
| **Stripe MCP 密钥迁移窗口** | 截止 `2026-10-31`（文档正文仍含 `2026-11-30` 矛盾） | `calendar_days_until_deadline = 30`（保守按 `2026-10-31` 零宽限执行） | 迁移窗口切换期的本地只读尝试账本核查不加写锁（无 `BEGIN IMMEDIATE`） |

## 3. 设计与实现（`lab/payment_attempts.py`）

在 `PaymentAttemptJournal` 中新增非抛异常（针对未预留场景）的只读查询方法 `read_attempt(operation: PaymentOperation) -> PaymentAttempt | None`，同时保留原有 `read(operation) -> PaymentAttempt` 的完全向后兼容：

1. **连接前输入校验（Pre-Connection Validation）**：调用 `_require_operation(operation)`，若 `not isinstance(operation, PaymentOperation)` 则在打开 SQLite 连接前直接抛出 `AttemptConflict("A trusted PaymentOperation is required.")`。
2. **只读无写锁查询（`SELECT`-Only）**：仅执行 `SELECT fingerprint,outcome,provider_reference FROM payment_attempts WHERE tenant_id=? AND operation_id=?`，不开启 `BEGIN IMMEDIATE` 事务，不写入或修改任何行。
3. **未预留与冲突严格消歧**：
   - 当 `(tenant_id, operation_id)` 不存在时返回 `None`；
   - 当存在记录但 `row["fingerprint"] != operation.fingerprint`（涵盖 `approval_id`、`provider`、`provider_account`、`idempotency_key` 及全部 `Checkout` 字段）时抛出 `AttemptConflict("Operation binding changed; do not dispatch.")`。
4. **持久化行完整性校验**：
   - 校验 `outcome in ("unknown", "succeeded", "failed")`；
   - 校验当 `outcome in ("succeeded", "failed")` 时 `provider_reference` 必须为非空字符串，当 `outcome == "unknown"` 时 `provider_reference` 必须为 `None` 或非空白字符串，防止脏数据绕过对账约束。

## 4. 验证结果

- 定向测试：`python -m pytest tests/test_payment_attempt_read.py tests/test_payment_attempts.py -v`（`27 passed, 55 subtests passed`，其中 `test_payment_attempt_read.py` 为 `8 passed, 19 subtests passed`；全量套件 `4295 passed, 1141 subtests passed`）。
- 覆盖场景：未预留返回 `None`、预留/待定/成功/失败状态跨进程重读、不可变 `PaymentAttempt`、全绑定维度篡改检测、租户与操作隔离、连接前非法输入拦截、提交失败回滚不可见、损坏持久化行拦截、以及 `SELECT`-only 无写锁追踪。
