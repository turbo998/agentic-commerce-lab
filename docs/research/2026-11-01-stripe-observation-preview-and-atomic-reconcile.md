# Stage 1741：Stripe PaymentIntent 单事务对账收敛、严格引用正则校验与无写锁对账预演（`StripeObservationPreview`）

> English version: [2026-11-01-stripe-observation-preview-and-atomic-reconcile.en.md](2026-11-01-stripe-observation-preview-and-atomic-reconcile.en.md)

## 执行摘要

在 Agentic Commerce 的 Stripe `PaymentIntent` 观察与对账层（`lab/stripe_observation.py`）中，Stage 1741 识别并消除了三项架构缺口：

1. **`reconcile_stripe_intent()` 的双连接 TOCTOU 窗口**：此前 `reconcile_stripe_intent()` 先通过 `journal.read(operation)` 打开第 1 个只读 SQLite 连接读取 `previous`，在连接外执行 `validate_stripe_intent()`，再通过 `journal.reconcile(...)` 打开第 2 个 `BEGIN IMMEDIATE` 连接写入结果。与 `associate_stripe_intent()` 和 `accept_stripe_readback()` 的单事务模式不同，这种两步连接会在 $T_1$ 与 $T_2$ 之间暴露并发修改窗口并产生双倍连接开销。Stage 1741 将 `reconcile_stripe_intent()` 收敛至单个 `BEGIN IMMEDIATE` 事务（`journal._find()` + `validate_stripe_intent()` + `journal._reconcile_in_transaction()`）。
2. **`validate_stripe_intent()` 的 `pi_[A-Za-z0-9_]+` 严格正则对称性**：此前 `associate_stripe_intent()` 对 `expected_reference` 强制执行 `re.fullmatch(r"pi_[A-Za-z0-9_]+", ...)`，而 `validate_stripe_intent()` 仅检查 `previous.provider_reference.startswith("pi_")`，导致通过 `journal.reconcile(..., provider_reference="pi_")` 或含空白/特殊字符的 `"pi_secret/value"` 可绕过校验。现统一使用 `_PI_RE.fullmatch(...)` 闭锁拦截。
3. **无写锁单快照对账预演模型（`StripeObservationPreview`）**：为支持干跑对账（Dry-Run Reconciliation）与事后只读排障，新增 `StripeObservationPreview`、`find_stripe_observation_preview()` 与 `read_stripe_observation_preview()`，在单条无锁 `SELECT` 语句中完成绑定校验、`PaymentIntent` 语义校验、跨操作 `provider_reference` 占用冲突检测与状态转移推演（`would_advance` / `is_terminal`），不获取写锁且不修改 `payment_attempts`。

---

## 架构对比：双连接对账与无预演模式 vs. 单事务对账 + 无写锁单语句预演

| 维度 | 经典实现（Stage 1653 基线） | Agentic Commerce 强化设计（Stage 1741） |
|---|---|---|
| `reconcile_stripe_intent()` 事务边界 | 2 次 SQLite 连接（`journal.read` + `journal.reconcile`） | 单次 `BEGIN IMMEDIATE` 连接内完成 `_find`、校验与 `_reconcile_in_transaction` |
| `provider_reference` 格式门禁 | `associate` 用正则 `pi_[A-Za-z0-9_]+`，`validate` 仅用 `.startswith("pi_")` | 全链路统一强制 `_PI_RE.fullmatch(r"pi_[A-Za-z0-9_]+")` |
| 干跑 / 排障预演能力 | 仅有内存级 `validate_stripe_intent`，不校验库内终态冲突或跨操作唯一性 | `find_stripe_observation_preview` / `read_stripe_observation_preview` 单条 `SELECT` 完整预演全部存储与语义门禁 |

---

## 验证结果

- `python -m pytest tests/test_stripe_observation.py tests/test_stripe_association.py tests/test_stripe_readback.py -q`：`69 passed, 133 subtests passed`。
