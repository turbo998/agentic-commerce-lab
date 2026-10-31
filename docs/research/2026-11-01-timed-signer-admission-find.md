# 2026-11-01 计时签名准入历史可选只读查询与非计时路径/绑定冲突消歧（Stage 1730）

> **English companion**: [2026-11-01-timed-signer-admission-find.en.md](2026-11-01-timed-signer-admission-find.en.md)

## 1. 背景与架构问题

在 `agentic-commerce-lab` 的本地三道交易执行围栏（`MerchantSignerStore` $\rightarrow$ `PaymentApprovalStore` $\rightarrow$ `PaymentAttemptJournal`）中，笔交易可以通过多条合法或历史路径进入执行账本：

1. **计时签名准入（Timed Signer Admission）**：传入 `TimedRequestSignatureSnapshot` 调用 `MerchantSignerStore.admit()`，在获取 `BEGIN IMMEDIATE` 写锁后用同一可信时钟样本同时校验签名时间窗与审批有效期，并同时写入 `payment_attempts`、`payment_admissions` 与 `merchant_timed_admissions` 三张表；
2. **裸签名快照准入（Bare Signer Admission）**：传入不含 `created`/`expires` 的 `RequestSignatureSnapshot` 调用 `MerchantSignerStore.admit()`，仅写入 `payment_attempts` 与 `payment_admissions`，不在 `merchant_timed_admissions` 留下记录；
3. **通用审批准入或旧版预留（Approval-Only / Legacy Reservation）**：通过 `PaymentApprovalStore.admit()` 或 `PaymentAttemptJournal.reserve()` 进入账本，同样无 `merchant_timed_admissions` 记录。

然而，原有的 `MerchantSignerStore.read_timed_admission(operation) -> TimedSignerAdmission` 对“无 `merchant_timed_admissions` 记录（未准入或走非计时路径）”与“持久化记录的 `fingerprint`、作用域（`target_uri`/`key_id`）、`signature_label` 或时间戳（`created`/`expires`/`admitted_at`）损坏”统一抛出 `MerchantSignerError`，导致离线审计或争议证据归档器无法在不依赖异常字符串匹配的前提下区分合法的非计时准入路径与持久化篡改。

## 2. 官方来源核验与架构映射（2026-11-01）

| 外部协议 / 产品面 | 首次发布 / 窗口 | 当日核验状态（2026-11-01） | 本地 Stage 1730 架构映射 |
|---|---|---|---|
| **Visa Trusted Agent Protocol (TAP)** | RFC 9421 HTTP Message Signatures | `51/51` 官方源正常（`unchanged`） | 区分含签名时间窗（`created`/`expires`）的首次准入证据与无计时参数的快照准入，严禁事后回填 |
| **Stripe MCP 密钥迁移窗口（跨过 `2026-10-31` 首日核验）** | 顶栏截止 `2026-10-31`；正文仍写 `2026-11-30` | `2026-11-01` 实测仍存双日期矛盾（`calendar_days_until_deadline = 29`） | 在排障与审计路径提供零写锁（`SELECT`-only）的三表证据对齐（`read_attempt` + `find_admission` + `find_timed_admission`） |
| **Stripe Shared Payment Tokens (SPT) / Link Agent Wallet** | SPT `2026-03-04.preview` / Link 私有预览 | SPT 卖方与 Connect 双页 `34` 国一致 | 保持本地签名准入溯源只读且不授予当前派发或支付权限 |

## 3. 设计与实现（`lab/merchant_signers.py`）

在 `MerchantSignerStore` 中新增 `_require_operation` 与 `find_timed_admission(operation: PaymentOperation) -> TimedSignerAdmission | None`，并将 `read_timed_admission(operation) -> TimedSignerAdmission` 重构为其严格包装器：

1. **连接前输入校验**：调用 `_require_operation(operation)`，非 `PaymentOperation` 实例在打开 SQLite 连接前即抛出 `MerchantSignerError`。
2. **无写锁只读查询（`SELECT`-Only）**：仅执行 `SELECT * FROM merchant_timed_admissions WHERE tenant_id=? AND operation_id=?`，不开启 `BEGIN IMMEDIATE`，不调用 `_permission()` 检查当前密钥撤销状态，也不调用 `require_signature_time()` 采样当前时钟。
3. **非计时路径与完整性冲突消歧**：
   - 若无记录（尚未准入、裸签名准入、通用审批准入或直接 `reserve()`），返回 `None`；
   - 若记录存在但 `row["fingerprint"] != operation.fingerprint`，抛出 `MerchantSignerError("Timed-admission record differs from the bound operation.")`；
   - 若 `target_uri` / `key_id` 非规范 ASCII、或 `signature_label` 不符合 RFC 8941 Structured Field key 语法、或 `created` / `expires` / `admitted_at` 违反 `0 <= created <= admitted_at < expires <= MAX_SIGNATURE_TIMESTAMP`，显式抛出 `MerchantSignerError`。

## 4. 验证结果

- 定向测试：`python -m pytest tests/test_timed_signer_admission_find.py tests/test_timed_signer_history.py tests/test_merchant_signers.py tests/test_merchant_signer_permission_read.py -v`（`77 passed, 155 subtests passed`，其中新增 `test_timed_signer_admission_find.py` 为 `6 passed, 38 subtests passed`）。
- 全量回归：`python -m pytest -q`（`4310 passed, 1202 subtests passed`）。
