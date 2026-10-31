# Poppy 会话断言重放日志只读摘要读取模型与过期后全声明一致性审计（Stage 1739）

**验证日期（北京时间）**：`2026-11-01`  
**适用范围**：`lab/poppy_replay.py`、`tests/test_poppy_replay_read.py`  
**关联阶段**：Stage 1662（`PoppyAssertionJournal`）、Stage 1664（`consume_with_clock`）、Stage 1671（`is_consumed`）

---

## 1. 背景与架构痛点

在 Poppy Draft 0.2（`poppy-session+jwt`）会话断言防重放设计中，`PoppyAssertionJournal` 为保护用户隐私，在 SQLite `poppy_assertion_replays` 表中仅持久化三元组主键 `(auth_issuer, client_id, jti_sha256)`，绝不将私有用户标识（`sub`）、会话标识（`session_id`）或明文 `jti` 写入磁盘。

然而，在生产环境的**事后重放审计（Post-Incident Replay Audit）**与**跨声明一致性核查**中，原先仅提供 `consume(scope, assertion, now=...)` 与 `is_consumed(scope, jti)` 存在两处结构性盲区：

1. **事后审计受限于 300 秒实时准入窗口（Post-Expiry Audit Blind Spot）**：
   - `consume()` / `consume_with_clock()` 不仅会产生写入副作用（消耗尚未使用的 `jti`），而且要求 `assertion.iat <= now < assertion.exp`（最长 300 秒）。一旦断言过期（`now >= assertion.exp`），调用方无法通过 `consume()` 核验历史 `SessionAssertionClaims` 是否满足 Poppy v0.2 声明约束并曾被消费。
2. **仅按 `jti` 查询忽略断言声明与作用域绑定（Claim-Unbound `jti` Lookup）**：
   - `is_consumed(scope, assertion.jti)` 仅接受原始 `jti: str` 字符串，完全忽略了 `assertion` 对象上的其余 Poppy v0.2 关键声明（`typ == "poppy-session+jwt"`、`iss == scope.client_id`、`aud == scope.auth_issuer`、`0 <= iat < exp <= 2**63 - 1` 以及 `0 < exp - iat <= 300`）。
   - 若调用方直接将伪造或作用域错配的 `SessionAssertionClaims`（例如 `typ="poppy-browser+jwt"`、`iss` 属于其他客户端、`aud` 指向其他商户，或 `exp - iat = 86400 > 300`）提取 `.jti` 传入 `is_consumed(scope, assertion.jti)`，只要该 `jti` 曾在该 `scope` 下被合法断言消费过，`is_consumed` 就会返回 `True`，导致审计器误将该非法断言识别为“已合法准入消费”。
3. **缺少类型化不可变已消费摘要模型**：
   - 与 `PaymentApprovalStore`、`MerchantSignerStore`、`StripeEventInbox` 和 `CheckoutStore` 不同，`PoppyAssertionJournal` 原先缺少返回 `(scope, jti_sha256)` 持久化记录的不可变只读数据类及闭锁行一致性校验。

---

## 2. AI Native 架构设计改进

我们在 [`lab/poppy_replay.py`](../../lab/poppy_replay.py) 中新增了不可变读取模型 `PoppyConsumedAssertion` 与两组只读审计接口：

1. **`PoppyConsumedAssertion` 不可变只读模型与存储行对偶校验（`_row_to_consumed_assertion`）**：
   - 包含 `scope: PoppyReplayScope` 与 `jti_sha256: str`。
   - `__post_init__` 强制验证 `isinstance(scope, PoppyReplayScope)` 且 `jti_sha256` 为严格的 64 位小写十六进制 SHA-256 摘要（`[0-9a-f]{64}`）。
   - `_row_to_consumed_assertion(scope, expected_digest, row)` 在水合数据库行时验证存储的 `(auth_issuer, client_id, jti_sha256)` 与查询键完全一致，任何篡改或偏移均闭锁抛出 `PoppyReplayError`。
2. **基于 `(scope, jti)` 的类型化摘要读取器**：
   - `find_consumed(scope, jti) -> PoppyConsumedAssertion | None`：无写锁查询已消费摘要记录，未消费时返回 `None`。
   - `read_consumed(scope, jti) -> PoppyConsumedAssertion`：严格读取已消费摘要记录，未消费时抛出 `PoppyReplayError`。
   - 保持 `is_consumed(scope, jti) -> bool` 的轻量 `SELECT 1` 查询路径不变，完全兼容既有 SQL trace 与并发读取语义。
3. **独立于实时时钟的全声明结构化审计器（`_validated_assertion_key`）**：
   - `find_assertion_consumption(scope, assertion) -> PoppyConsumedAssertion | None`
   - `read_assertion_consumption(scope, assertion) -> PoppyConsumedAssertion`
   - `is_assertion_consumed(scope, assertion) -> bool`
   - 在打开 SQLite 连接前，完整验证 `SessionAssertionClaims` 的全部非时钟依赖 Poppy v0.2 不变量（`typ == "poppy-session+jwt"`、`iss == scope.client_id`、`aud == scope.auth_issuer`、`0 <= iat, exp <= 2**63 - 1`、`1 <= exp - iat <= 300` 以及 22–256 字符 base64url `jti`），既支持断言过期后的历史审计，又拒绝任何声明错配的伪造断言对象，且绝不消耗未使用的 `jti` 或在磁盘持久化私有声明。

---

## 3. 测试验证

在 [`tests/test_poppy_replay_read.py`](../../tests/test_poppy_replay_read.py) 中新增 4 组测试方法（全套 Poppy 重放与时钟测试共 `64 passed, 132 subtests passed`）：

- `test_find_and_read_consumed_return_typed_immutable_digest_record`
- `test_consumed_assertion_record_and_row_parity_invariants`
- `test_assertion_consumption_audit_is_clock_independent_and_non_consuming`
- `test_assertion_consumption_rejects_mismatched_claims_even_when_jti_was_consumed`
