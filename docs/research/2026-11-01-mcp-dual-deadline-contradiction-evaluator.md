# Stripe MCP 双截止日矛盾窗口评估模型（`2026-10-31` vs `2026-11-30`）与零宽限门禁（Stage 1742）

> **English companion**: [2026-11-01-mcp-dual-deadline-contradiction-evaluator.en.md](2026-11-01-mcp-dual-deadline-contradiction-evaluator.en.md)  
> **验证日期（北京时间）**：`2026-11-01`  
> **关联资产**：[`lab/mcp_migration.py`](../../lab/mcp_migration.py) · [`tests/test_mcp_migration.py`](../../tests/test_mcp_migration.py)

---

## 1. 背景与问题定义

在 `2026-11-01`（跨过 Stripe 早期公告的 `2026-10-31` 密钥迁移截止日首日），对 `https://docs.stripe.com/mcp` 的实测核验表明官方文档内部仍存在双截止日矛盾：

1. **早期公告与迁移指南截止日（`PREVIOUS_DEADLINE = 2026-10-31`）**：多处文档与迁移说明写明需在 `2026-10-31` 前将全权限 Secret Key（`full_access_secret`）与未带 `agent` 标签的受限密钥（`restricted_without_agent_tag`）迁移至 OAuth 或带权限范围的 Agent Key（`after November 1, 2026` 停止支持）。
2. **正文通知栏截止日（`DEADLINE = 2026-11-30`，`ENFORCEMENT_STARTS = 2026-12-01`）**：`#### Update API key authentication by November 30, 2026` 通知块声明 `Migrate by November 30, 2026. Starting in December, Stripe MCP will stop accepting full-access secret keys and restricted API keys without the Agent tag.`

在 Stage 1742 之前，`lab/mcp_migration.py` 存在三项架构缺口：

1. **双截止日矛盾窗口（`[2026-10-31, 2026-11-30)`）在评估函数中不可见**：`assess(client, as_of=...)` 仅对比单一 `as_of < deadline`（默认 `2026-11-30`），导致在 `2026-10-31` 与 `2026-11-01`（早期截止日已到期、晚近通知尚未到期）评估旧版密钥时，其状态与 `2026-10-16` 完全相同（均为 `"migration_required"`），编程调用方无法识别该密钥已处于官方双截止日矛盾暴露窗口。
2. **CLI 缺少零宽限强制开关（`--strict-previous-deadline`）**：尽管 CLI 报告输出静态字符串 `"previous_deadline": "2026-10-31"`，但并未计算 `previous_deadline_elapsed`、`calendar_days_until_previous_deadline`、`deadline_window_phase` 与 `contradiction_exposed_count`，也无法通过命令行参数按 `2026-10-31` 零宽限策略直接将未迁移密钥判定为 `"blocked_by_documented_policy"`。
3. **`Finding` 缺少构造期不变量与输入类型门禁**：`Finding` 数据类未定义 `__post_init__`，允许构造出 `auth_method="oauth"` 却标记为 `"blocked_by_documented_policy"` 或 `auth_method="full_access_secret"` 却标记为 `"recorded_supported_unverified"` 的矛盾对象；同时 `assess()`、`load_inventory()` 与 `load_deadline_from_source_report()` 未对非 `Client` / 非 `Path` 入参执行显式 `ValueError` 拦截。

---

## 2. 架构设计与不变量（Stage 1742）

### 2.1 三阶段时间窗口分类（`classify_deadline_window`）

新增 `DeadlineWindowPhase = Literal["before_previous_deadline", "contradiction_window", "on_or_after_deadline"]` 与 `classify_deadline_window(*, as_of, deadline=DEADLINE, previous_deadline=PREVIOUS_DEADLINE)`：

- `as_of < previous_deadline`（如 `2026-10-30`）：`"before_previous_deadline"`（两个截止日均未到达）。
- `previous_deadline <= as_of < deadline`（如 `2026-10-31`、`2026-11-01` 至 `2026-11-29`）：`"contradiction_window"`（`2026-10-31` 已到期，但 `2026-11-30` 尚未到达）。
- `as_of >= deadline`（如 `2026-11-30`、`2026-12-01`）：`"on_or_after_deadline"`（两个截止日均已到达）。

### 2.2 双截止日联合评估模型（`DualDeadlineFinding` 与 `assess_dual_deadline`）

新增不可变数据类 `DualDeadlineFinding` 与 `assess_dual_deadline(client, *, as_of, deadline=DEADLINE, previous_deadline=PREVIOUS_DEADLINE)`：

- 同时计算针对晚近通知截止日（`deadline`）的 `primary_status` 与针对早期截止日（`previous_deadline`）的 `strict_previous_status`。
- `contradiction_exposed = (primary_status != strict_previous_status)`：仅当旧版密钥（`full_access_secret` 或 `restricted_without_agent_tag`）处于 `[2026-10-31, 2026-11-30)` 矛盾窗口内时为 `True`（此时 `primary_status == "migration_required"` 而 `strict_previous_status == "blocked_by_documented_policy"`）。
- 支持的认证方式（`oauth`、`agent_key`）在所有日期下均保持 `"recorded_supported_unverified"`，`contradiction_exposed == False`，且绝不谎称已完成在线账户权限核验。

### 2.3 CLI 零宽限门禁（`--strict-previous-deadline`）与构造期闭锁校验

- CLI 新增 `--strict-previous-deadline` 开关：启用后以 `effective_deadline = min(deadline, PREVIOUS_DEADLINE)` 评估清单，在 `2026-10-31` 及 `2026-11-01` 立即将旧版密钥输出为 `"blocked_by_documented_policy"`。
- CLI JSON 报告新增 `effective_deadline`、`strict_previous_deadline_enforced`、`previous_deadline_elapsed`、`calendar_days_until_previous_deadline`、`deadline_window_phase` 与 `contradiction_exposed_count`。
- `Finding` 与 `DualDeadlineFinding` 均在 `__post_init__` 中强制执行字段与跨字段一致性校验。

---

## 3. 回归验证

执行 `python -m pytest tests/test_mcp_migration.py tests/test_checkout_admission.py -q`：
- **`45 passed, 156 subtests passed`**。
