# Stage 1671：Poppy assertion 作用域重放历史只读查询与草案 0.3 演进边界

[English](2026-10-30-poppy-replay-read.en.md) |
[当日日报](../../research/daily/2026-10-30.md) |
[上一阶段](2026-10-29-stripe-receipt-read.md) |
[原始 replay 资产](2026-10-29-poppy-replay.md) |
[锁后时钟准入](2026-10-29-poppy-admission-clock.md)

**结论：**在 [`PoppyAssertionJournal`](../../lab/poppy_replay.py) 上增加只读的
`is_consumed(scope, jti)`，必须同时按可信 `(auth_issuer, client_id, SHA256(jti))`
完整三维主键做只读 `SELECT`。**返回 `True` 只证明本地日志此前已在该 Company/client
作用域烧掉该 `jti`，不证明下游 Token 已签发或成功送达；返回 `False` 绝不能替代
`consume` / `consume_with_clock` 的 `BEGIN IMMEDIATE` 原子准入，也不授予任何会话、
账户或支付权限。**

**核验日期：2026-10-30，北京时间 23:03–23:24；基线 `b494db6`（含 Stage 1670 `3ecd71c`）。**
`provenance=synthetic`、`independently_reproduced=false`：纯离线 SQLite 参考资产，
不是模型 benchmark、真实 JWT/DPoP 验签器、OAuth 授权服务或跨厂商兼容认证。

## 1. 上游一手证据：已发布 0.2（2026-10-24）与进行中 Draft 0.3（`3e9bada`）的区分

本轮核验官方仓库 `personal-agent-protocol/personal-agent-protocol` 最新提交为
[`3e9bada9ec8f66777b43e429d49574131dc2f67e`](https://github.com/personal-agent-protocol/personal-agent-protocol/commit/3e9bada9ec8f66777b43e429d49574131dc2f67e)
（`Draft 0.3 (#112)`，提交时间 `2026-10-29T14:36:58Z`）：

- **版本发布状态核实**：固定提交下的
  [`content/versions/versions.json`](https://github.com/personal-agent-protocol/personal-agent-protocol/blob/3e9bada9ec8f66777b43e429d49574131dc2f67e/content/versions/versions.json)
  仍明确记录 **Version `0.2` 于 `2026-10-24` 发布**（冻结规范
  `content/versions/0.2/spec.mdx` 内容 SHA-256 仍为
  `5f6ac40cb2c2114fe85ebe3f1c2fec8a2cbfc90f2a92a2bf44e6ce0e518e0a26`）、
  **Version `0.1` 于 `2026-10-09` 发布**，而 **`0.3` 条目没有 `"published"` 字段**；
  [`content/shared/changelog.mdx`](https://github.com/personal-agent-protocol/personal-agent-protocol/blob/3e9bada9ec8f66777b43e429d49574131dc2f67e/content/shared/changelog.mdx)
  顶部注明 `"In progress, at /docs/spec. This list grows until 0.3 is published."`。
  因此不能把进行中的 `0.3` 草案当作已发布版本，本仓库持久化 Session assertion
  准入继续锚定已发布 `0.2`（§4.1/4.2）。
- **Draft `0.3` 草案的架构变化与共同重放边界**：
  - 在已发布 `0.2` 中，Session assertion（`typ: "poppy-session+jwt"`）提交至 OAuth
    Token Endpoint，`aud` 绑定 Company `auth.issuer`，有效期不超过 5 分钟，Company
    拒绝同一 `client_id` 重复提交的 `jti`。
  - 在进行中的 Draft `0.3`（`content/versions/0.3/spec.mdx` §5.2–5.5 与
    `kit/company/patterns/session-header.md`）中，Session 与 OAuth 解耦，每次请求通过
    `Poppy-Session` HTTP 头携带 `poppy-session+jwt`（内嵌 `pap_dlg: pap-delegation+jwt`），
    Company 同样必须在时钟偏移窗口内按 `jti` 拒绝重放；同时 `operations` 扩展升级为 v2
    （以 `403 approval_required` + `Poppy-Approval` 头部重试及执行期 `503 Retry-After`
    取代 v1 的 `202` + 独立 operations 端点）。
  - 无论 `0.2` Token Endpoint 准入还是 `0.3` 请求头重放缓存，规范只规定接纳边界必须拒绝重复
    `jti`，并未规定本地 SQLite 查询接口，也绝不允许把“查重放表”当作跳过验签或已发证的证明。

## 2. 作用域重放历史只读查询契约

[`PoppyAssertionJournal.is_consumed(scope, jti)`](../../lab/poppy_replay.py) 提供与
[`StripeEventInbox.read_receipt`](2026-10-29-stripe-receipt-read.md)、
[`PaymentApprovalStore.read_admission`](2026-10-29-admission-provenance.md) 对齐的只读历史查询：

1. **连接前严格校验输入**：复用 `_jti_key(scope, jti)`，要求 `scope` 为已校验的
   `PoppyReplayScope`，且 `jti` 为 22–256 位 base64url ASCII 字符串；对 `None`、`bool`、
   空白、超长/过短或含非 base64url 字符的输入直接抛出 `PoppyReplayError`，不打开数据库连接，
   也不把非法输入静默折算为 `False`。
2. **完整三维主键只读 `SELECT`**：计算 `SHA256(jti)` 后执行单条
   `SELECT 1 FROM poppy_assertion_replays WHERE auth_issuer=? AND client_id=? AND jti_sha256=?`。
   不开 `BEGIN IMMEDIATE` 写锁、不采样时钟、不调用 metadata 校验器、不写入或消费 `jti`。
3. **语义边界清晰**：
   - `False` 仅表示当前时刻该 `(auth_issuer, client_id)` 下尚未持久化该 `jti` 摘要；
     调用方若以此做“先查后写（check-then-act）”，并发 worker 仍会在无写锁窗口内竞态，
     真正准入必须调用 `consume` 或 `consume_with_clock`。
   - `True` 仅表示本地准入事务已提交该 `jti`（即使随后进程崩溃或网络响应丢失，该 `jti`
     也已烧毁，Agent 恢复时必须签发新 `jti`），不代表下游已成功签发 Session/Account Token。
   - SQLite 锁超时或存储异常原样抛出，绝不伪装成 `False`。

## 3. 可运行合成示例

在仓库根目录执行。示例仅演示本地 SQLite 重放历史查询，不涉及真实 JWT 签名、网络请求或资金。

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from lab.poppy_guard import SessionAssertionClaims
from lab.poppy_replay import (
    PoppyAssertionJournal, PoppyReplayDetected, PoppyReplayScope,
)

with TemporaryDirectory() as directory:
    journal = PoppyAssertionJournal(Path(directory) / "replays.sqlite3")
    scope = PoppyReplayScope(
        "https://auth.company.example", "https://agent.example/client.json",
    )
    other_scope = PoppyReplayScope(
        "https://auth.other-company.example", scope.client_id,
    )
    assertion = SessionAssertionClaims(
        "poppy-session+jwt", scope.client_id, "synthetic-user",
        scope.auth_issuer, 1700000000, 1700000060,
        "synthetic_assertion_000001",
    )
    assert journal.is_consumed(scope, assertion.jti) is False
    journal.consume_with_clock(scope, assertion, clock=lambda: 1700000000)
    assert journal.is_consumed(scope, assertion.jti) is True
    assert journal.is_consumed(other_scope, assertion.jti) is False
    try:
        journal.consume(scope, assertion, now=1700000001)
    except PoppyReplayDetected:
        print("consumed history verified and replay rejected")
    else:
        raise AssertionError("expected replay rejection")
```

## 4. AI-Native 架构反思与验证范围

在经典三层 Web 应用中，幂等/重放表常被误用为“已完成下游动作”的缓存标志；而在
AI-Native 架构中，Agent 重试、跨 worker 恢复与协议升级（如 Poppy `0.2` 向 `0.3`
演进）频繁发生，必须严格区分**“准入标识已烧毁（replay key consumed）”**与**“凭证已签发 /
商业操作已获批（token issued / operation approved）”**。只读历史查询只服务于事后诊断与
恢复判定（确认旧 `jti` 已被消耗需换新 assertion），不能降级原子写锁准入或替代业务对账。

[`tests/test_poppy_replay_read.py`](../../tests/test_poppy_replay_read.py) 新增 **14 项单元测试**：
覆盖未消费返回 `False` 且不占用 ID、`consume` 与 `consume_with_clock` 写入均可读、
重新打开与跨进程持久化、跨 Company/client 作用域隔离、同作用域不同 `jti` 独立、
校验失败或 commit 回滚不标记已消费、非法 `scope`/`jti` 连接前拒绝、22/256 边界长度、
存储异常原样抛出、SQL trace 证明单条只读 `SELECT` 且不触发写锁或 metadata 校验。
