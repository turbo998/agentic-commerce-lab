# Stage 1731 — `StripeEventInbox` 持久化收据与回读认领完整性校验（`InboxReceipt` / `InboxDecision` 闭环加固）

> **English companion**: [2026-11-01-stripe-receipt-integrity.en.md](2026-11-01-stripe-receipt-integrity.en.md)  
> **验证日期（北京时间）**：`2026-11-01`（窗口 `00:35–00:46+08:00`）  
> **关联资产**：[`lab/stripe_inbox.py`](../../lab/stripe_inbox.py) · [`tests/test_stripe_receipt_integrity.py`](../../tests/test_stripe_receipt_integrity.py)

---

## 1. 背景与问题定义

在 Stripe Webhook 异步事件接收与回读协调管道（`StripeEventInbox`）中，`StripeInboxScope`、`ReadbackClaim`、`ReadbackClaimStatus`、`StripeSecretWindow` 与 `StripeWebhookSecretRing` 均在构造期通过 `__post_init__` 强制执行失败关闭（Fail-Closed）不变量校验。然而此前实现中存在四处持久化水合（Hydration）与跨表一致性盲区：

1. **`InboxReceipt` 与 `InboxDecision` 缺失构造期不变量校验**：`StripeEventInbox._receipt(row)` 从 SQLite `stripe_event_inbox` 表读取 `event_id`、`event_type`、`provider_reference`、`payload_sha256` 时未校验列格式，导致存储损坏的记录会在 `read_receipt()`、`pending()`、`claim_next()`、`read_claim()`、`active_claims()` 中被静默封装为非法 `InboxReceipt`。
2. **`claim_next()` 先写入后水合的顺序隐患**：`claim_next()` 原先先执行 `INSERT INTO stripe_readback_claims` 再调用 `self._receipt(row)`；一旦持久化收据字段损坏，应先在内存中完成 `_receipt(row)` 校验，再发出 `INSERT` 语句。
3. **孤立认领行（Orphan Claim Rows）被内连接掩盖**：由于 `stripe_readback_claims` 未启用 SQLite 外键级联约束，当父表 `stripe_event_inbox` 对应收据缺失时，`read_claim()` 与 `active_claims()` 原先使用的 `INNER JOIN` 会静默返回 `None` 或跳过该损坏认领行，掩盖跨表不一致故障。
4. **损坏的 `state` 列在 `finish_readback()` 中可能被覆盖**：若 `stripe_readback_claims.state` 在存储层被篡改为非 `'active'` / `'handled'` 值，`_finish_in_transaction()` 原先仅检查 `row["state"] == "handled"`，否则直接覆盖为 `'handled'`，未能失败关闭。

---

## 2. 辩证架构分析：经典三层 Web 应用 vs. Agentic Commerce AI-Native 架构

| 架构维度 | 云服务商经典三层 Web / ORM 架构 | Agentic Commerce AI-Native 架构（Stage 1731） |
|---|---|---|
| **ORM / 数据类水合边界** | 默认信任本地数据库行，仅在 HTTP 入口校验请求体，从数据库读取的实体直接映射为内存对象。 | 坚持“**本地 SQLite 存储同样可能发生位翻转、部分迁移或越权篡改**”的零信任原则：`InboxReceipt.__post_init__` 与 `InboxDecision.__post_init__` 对每次内存构造及 SQLite 行水合均强制校验 `evt_`、`payment_intent.succeeded`/`payment_intent.payment_failed`、`pi_` 与 64 位小写 SHA-256。 |
| **跨表关联查询（`JOIN`）语义** | 使用 `INNER JOIN` 联合主表与状态子表，主表缺失时静默当作“无记录（`None`）”处理。 | `read_claim()` 与 `active_claims()` 改为从 `stripe_readback_claims c LEFT JOIN stripe_event_inbox i` 出发并以 `ORDER BY i.rowid, c.rowid` 排序（SQLite 中 `NULL` 排在最前）：一旦存在无主收据的孤立认领行，立即触发 `StripeInboxError`，绝不静默伪装为“无认领”。 |
| **状态机终态写入（`finish_readback`）** | 常见幂等写法为 `if state != 'done': UPDATE state = 'done'`，将非法中间状态一并洗白为成功终态。 | `_current_claim()` 显式校验 `row["state"] in ("active", "handled")`，拒绝任何偏离二元状态机的损坏行，防止 `finish_readback()` 或 `accept_stripe_readback()` 洗白损坏状态。 |

---

## 3. 核心实现细节（`lab/stripe_inbox.py`）

1. **`InboxReceipt.__post_init__` 与 `InboxDecision.__post_init__`**：
   - 校验 `event_id` 匹配 `r"evt_[A-Za-z0-9_]+"`。
   - 校验 `event_type` 严格属于 `("payment_intent.succeeded", "payment_intent.payment_failed")`。
   - 校验 `provider_reference` 匹配 `r"pi_[A-Za-z0-9_]+"`。
   - 校验 `payload_sha256` 匹配 `r"[0-9a-f]{64}"`（64 位小写十六进制摘要）。
   - 校验 `requires_readback`、`first_seen`、`body_matches_first` 严格满足 `type(...) is bool`（拒绝 `1`/`0` 等整型伪布尔值）。
2. **`claim_next()` 先水合校验后插入**：
   - 在 `BEGIN IMMEDIATE` 事务中选出未认领收据后，先执行 `receipt = self._receipt(row)` 验证持久化收据完整性，通过后才执行 `INSERT INTO stripe_readback_claims`。
3. **`read_claim()` 与 `active_claims()` 孤立认领检测**：
   - 改为 `FROM stripe_readback_claims c LEFT JOIN stripe_event_inbox i USING(tenant_id,endpoint_id,provider_account,livemode,event_id)`；当 `stripe_event_inbox` 缺失对应收据时，`i.event_type` 等列为 `NULL`，`self._receipt(row)` 立即抛出 `StripeInboxError`。
4. **`_current_claim()` 状态集合强校验**：
   - 新增 `if row["state"] not in ("active", "handled"): raise StripeInboxError("Stored readback claim state is invalid.")`。

---

## 4. 测试与回归验证

在 [`tests/test_stripe_receipt_integrity.py`](../../tests/test_stripe_receipt_integrity.py) 中新增 5 项测试（含 63 个子测试）：

- `test_inbox_receipt_and_decision_validate_invariants`：覆盖 `InboxReceipt` 与 `InboxDecision` 所有字段的非法类型、前缀错误、大小写/长度偏离及伪布尔值拒绝。
- `test_corrupted_persisted_receipt_columns_fail_closed_before_claim_or_read`：验证 `stripe_event_inbox` 任一列损坏时，`read_receipt()`、`record()`（重复投递比对）、`pending()`、`claim_next()` 均抛出 `StripeInboxError`，且 `claim_next()` 不产生任何认领行。
- `test_corrupted_persisted_receipt_rejects_claim_reads_handoff_and_completion`：验证已认领收据的持久化列损坏时，`read_claim()`、`active_claims()`、`handoff()`、`finish_readback()` 与 `accept_stripe_readback()` 全部失败关闭，`payment_attempts` 保持 `unknown`。
- `test_orphan_claim_without_inbox_receipt_fails_closed`：验证删除父表 `stripe_event_inbox` 行后，`read_claim()`、`active_claims(limit=1)`、`handoff()` 与 `finish_readback()` 立即报 `StripeInboxError`，而未损坏的其他事件认领不受影响。
- `test_corrupted_claim_state_is_not_overwritten_by_finish_or_readback`：验证绕过 `CHECK` 约束写入损坏 `state` 后，`finish_readback()` 与 `accept_stripe_readback()` 拒绝覆盖该损坏状态且不推进 `payment_attempts`。

### 回归测试结果
- `python -m pytest tests/test_stripe_receipt_integrity.py tests/test_stripe_inbox.py tests/test_stripe_receipt_read.py tests/test_stripe_claim_read.py tests/test_stripe_readback.py tests/test_stripe_atomic_readback.py tests/test_stripe_receipt_clock.py tests/test_stripe_secret_rotation.py -q`：`155 passed, 261 subtests passed`。
