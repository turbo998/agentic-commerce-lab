# Stage 1748：Poppy 会话断言消费与 Stripe Webhook 收件箱/认领跃迁的无锁单 `SELECT` 预检（`PoppyConsumptionPreview` / `InboxRecordPreview` / `ClaimTransitionPreview`）

> **验证日期**：2026-11-01（北京时间 `UTC+08:00`）  
> **英文版（English Version）**：[`2026-11-01-poppy-replay-and-stripe-inbox-dry-run-preview.en.md`](2026-11-01-poppy-replay-and-stripe-inbox-dry-run-preview.en.md)  
> **关联资产**：[`lab/poppy_replay.py`](../../lab/poppy_replay.py)、[`lab/stripe_inbox.py`](../../lab/stripe_inbox.py)、[`tests/test_poppy_replay_read.py`](../../tests/test_poppy_replay_read.py)、[`tests/test_stripe_claim_read.py`](../../tests/test_stripe_claim_read.py)

---

## 1. 背景与架构问题

在 Stage 1744–1747 完成结账执行、支付尝试、审批准入、商户签名准入以及 Stripe 回读验收的无锁单 `SELECT` 预检后，Agentic Commerce 入口平面的另外两个高频持久化门禁——**Sierra Poppy v0.2 会话断言重放日志（`PoppyAssertionJournal`）**与 **Stripe Webhook 收件箱及回读认领协调平面（`StripeEventInbox`）**——仍缺少对应的只读 dry-run 预检原语：

1. **`PoppyAssertionJournal.consume()` 缺乏无损重放预检**：
   - `find_assertion_consumption()` 仅以 `now=assertion.iat` 做与时钟无关的结构审计，无法在指定时间点 `now` 预演完整准入窗口（`iat - 30 <= now < exp`）与 `jti_sha256` 消费状态；而直接调用 `consume()` 会在首次调用时烧毁（burn）断言 `jti`。
2. **`StripeEventInbox.record()` / `handoff()` / `finish_readback()` 缺乏无锁预检**：
   - `read_receipt()`、`read_claim()` 与 `find_provenance()` 只能按 `event_id` 静态读取历史，无法在不获取 `BEGIN IMMEDIATE` 写锁的前提下，端到端验证原始 Webhook 字节流的 HMAC 签名、时间戳容差、JSON 唯一键及事件类型/对象绑定冲突，也无法预演认领所有权恢复交接（`handoff`）与认领完成（`finish_readback`）的状态跃迁。

---

## 2. AI-Native 架构设计

### 2.1 `PoppyConsumptionPreview` 与 `PoppyAssertionJournal.preview_consume()`

在 `lab/poppy_replay.py` 中新增不可变数据类 `PoppyConsumptionPreview` 及方法 `PoppyAssertionJournal.preview_consume(scope, assertion, *, now)`：

- **预连接全量校验**：复用 `_validated_key(scope, assertion, now=now)`，在打开 SQLite 连接前严格核验 `PoppyReplayScope`、`typ == "poppy-session+jwt"`、`iss == scope.client_id`、`aud == scope.auth_issuer`、`1 <= exp - iat <= 300`、`iat - 30 <= now < exp` 以及 `jti` 的 22–256 位 base64url 策略。
- **单条无锁 `SELECT` 查询**：调用 `_lookup_consumed_key(scope, key)` 查询 `poppy_assertion_replays`，并在 `_row_to_consumed_assertion()` 中闭锁核验返回行与查询键一致。
- **结构化预演结果**：
  - 首次未消费：`existing_consumption=None`、`projected_consumption=PoppyConsumedAssertion(scope, jti_sha256)`、`would_consume=True`（`is_replay=False`）。
  - 重放已消费：`existing_consumption=existing`、`projected_consumption=existing`、`would_consume=False`（`is_replay=True`）。

### 2.2 `InboxRecordPreview`、`ClaimTransitionPreview` 与 `StripeEventInbox` 预检方法

在 `lab/stripe_inbox.py` 中抽取出统一的 `_parse_verified_event()`，并新增两个不可变预检模型与三个只读预检方法：

1. **`InboxRecordPreview` 与 `StripeEventInbox.preview_record()`**：
   - 先执行 `verify_stripe_delivery()`、UTF-8 JSON 严格唯一键解析、`livemode` 精确布尔绑定与 `evt_` / `pi_` 格式门禁。
   - 再通过单条 `FROM (SELECT 1) LEFT JOIN stripe_event_inbox i ... LEFT JOIN stripe_readback_claims c ...` 无写锁查询，同时获取已存收据与认领状态：
     - 检测到孤儿认领行（`i_event_id IS NULL AND c_event_id IS NOT NULL`）或同一 `event_id` 绑定不同 `event_type` / `provider_reference` 时立即闭锁抛出 `StripeInboxError`；
     - 精确返回 `existing_receipt`、`existing_claim_status`、`decision: InboxDecision`、`would_insert_receipt: bool` 与 `event_phase: InboxEventPhase`（`"unclaimed"` / `"active"` / `"handled"`）。
2. **`ClaimTransitionPreview` 与 `preview_handoff()` / `preview_finish_readback()`**：
   - 在单条无锁 `SELECT`（`_current_claim()`）中核验收据与认领的 `worker_id`、`generation`、`receipt` 绑定：
     - `preview_handoff(claim, worker_id)` 要求当前状态为 `"active"` 且 `generation < 2**63 - 1`，投影 `generation + 1` 的新 `ReadbackClaimStatus(..., "active")`（`would_write=True`）；
     - `preview_finish_readback(claim)` 投影 `ReadbackClaimStatus(claim, "handled")`，当已有状态为 `"active"` 时 `would_write=True`，当已为 `"handled"` 幂等重入时 `would_write=False`。

---

## 3. 验证结果

```text
python -m pytest tests/test_poppy_replay.py tests/test_poppy_replay_read.py tests/test_poppy_admission_clock.py tests/test_stripe_inbox.py tests/test_stripe_claim_read.py -q
102 passed, 231 subtests passed
```
