# Stage 1664：等待写锁之后，才采样 assertion 准入时间

[English](2026-10-29-poppy-admission-clock.en.md) |
[当日日报](../../research/daily/2026-10-29.md) |
[原始 replay 资产](2026-10-29-poppy-replay.md) |
[上一阶段](2026-10-29-stripe-association.md)

**结论：**等待 SQLite 写锁之前有效的 Session assertion，排队期间可能已到期。
即使把比较语句后移，固定调用者 `now` 仍不会变新。新增显式可信时钟入口，
在 **`BEGIN IMMEDIATE` 成功后**采样，再于同一事务校验 metadata、消费 replay key。
**保证止于锁后采样点，不是实际 commit/token 签发时刻的硬截止保证。**

2026-10-29 北京时间 03:47 从 `c3c9702` 恢复，03:47–03:49 核验来源。
仅在 23:00–06:00 工作，05:30 起不再开新阶段；README/SVG 不变。
`provenance=synthetic`、`independently_reproduced=false`：离线工程 fixture，
不是模型 benchmark、真实 JWT/DPoP 验证或协议认证。

## 1. 锚定已发布 0.2，不将进行中的草案当新发布

官方仓库 HEAD 仍为 `a95b757872533a6ef1e1a9bcf29802857d2e5ff4`（2026-10-26）。
固定版本的 [registry](https://github.com/personal-agent-protocol/personal-agent-protocol/blob/a95b757872533a6ef1e1a9bcf29802857d2e5ff4/content/versions/versions.json)
记录 **0.2 于 2026-10-24 发布**，0.3 没有 published 字段。
[0.2 规范](https://github.com/personal-agent-protocol/personal-agent-protocol/blob/a95b757872533a6ef1e1a9bcf29802857d2e5ff4/content/versions/0.2/spec.mdx)
要求 audience 精确匹配 Company `auth.issuer`，`exp` 至多在 `iat` 后五分钟，
同 client 已见过的 `jti` 在 expiry 前必须拒绝。生产者至少 128 random bits
的熵要求，不等于字符串长度/字符表检查。

本轮对解码后的规范原始字节独立计算 SHA-256，与 registry 已发布页面 checksum 一致：
`5f6ac40cb2c2114fe85ebe3f1c2fec8a2cbfc90f2a92a2bf44e6ce0e518e0a26`。
这是文档内容 checksum，不是 Git blob SHA-1、assertion 验签或新发布公告。

[RFC 7519 §4.1.4](https://www.rfc-editor.org/rfc/rfc7519.html#section-4.1.4)
要求当前时间早于 `exp`，同时允许少量 clock-skew leeway。本实验保留较严格的
**零偏移、signed-64 整数、`iat <= now < exp`** 本地策略，不宣称通用 JWT 禁止
小数 NumericDate 或强制这种 future-iat 策略。
[SQLite 事务说明](https://www.sqlite.org/lang_transaction.html) 解释
`BEGIN IMMEDIATE` 为什么会等待/因其他 writer 而失败；协议本身不要求 SQLite 或本实现。

Token endpoint 的 DPoP proof replay 是另一项义务。Session assertion lifetime
不是 Session/Account Token lifetime、购买同意或支付 operation TTL。
本轮未核验新的 Visa/Stripe 发布。

## 2. 一套 metadata 策略，一份持久 replay 历史

[`PoppyAssertionJournal.consume_with_clock`](../../lab/poppy_replay.py)
要求 `clock: Callable[[], int]`，没有回退到请求时间戳或系统时钟的默认逻辑。

1. 要求 callable，再获取既有本地写事务。
2. **取得写锁后**调用时钟。
3. 复用完整 metadata/key 校验：type/client、精确 audience、
   严格时间/lifetime 与本地有界 base64url `jti`。
4. 复用同一事务 participant，拒绝或插入 scoped key。
5. commit 后才返回；clock、lock、validation、storage、commit 错误直接抛出，
   不转换为成功准入。

Callback 必须在**被调用时**读取新鲜可信时间，不能返回旧请求、模型选择或预先捕获的
时间戳。时钟准确性/回退、数据库完整性与一致备份仍属部署责任。
采样后的暂停仍可能跨越 expiry，本 API 不阻止这一点，也不原子签发凭据。

原 `consume(..., now=...)` 保留固定快照兼容合同，包括锁前校验。
需要避免锁等待保留陈旧时间时使用显式新入口。两者共享原校验/key 与 replay
participant；不迁移 schema，不改变 namespace、清理或保留策略。
任一入口消费的都是同一个 `(Company issuer, authenticated client, SHA256(jti))`。

仍只保存 namespace/digest，不保存时间、原始 `jti`、user/session、JWT、DPoP 或 token。
本地 API 仍永久保留 ID。Private participant 要求 active transaction，不是 agent 工具；
绕过门禁或采用独立文件会失去协调的重放历史。

## 3. 可运行 synthetic 示例

可变时钟与可预测 ID 是 fixture，不是生产时钟或随机 ID 生成器。
假定外部已完成签名/client/user/session/proof 校验。

```python
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from lab.poppy_guard import SessionAssertionClaims
from lab.poppy_replay import (
    PoppyAssertionJournal, PoppyReplayDetected, PoppyReplayError, PoppyReplayScope,
)

current = [1700000000]
scope = PoppyReplayScope("https://auth.company.example", "https://agent.example/client.json")
assertion = SessionAssertionClaims(
    "poppy-session+jwt", scope.client_id, "synthetic-user", scope.auth_issuer,
    current[0], current[0] + 60, "synthetic_assertion_000001",
)
with TemporaryDirectory() as directory:
    journal = PoppyAssertionJournal(Path(directory) / "replays.sqlite3")
    journal.consume_with_clock(scope, assertion, clock=lambda: current[0])
    try:
        journal.consume(scope, assertion, now=current[0])
    except PoppyReplayDetected:
        pass
    else:
        raise AssertionError("both facades must share durable replay history")
    current[0] = assertion.exp
    expired = replace(assertion, jti="synthetic_assertion_000002")
    try:
        journal.consume_with_clock(scope, expired, clock=lambda: current[0])
    except PoppyReplayError:
        pass
    else:
        raise AssertionError("exact expiry must reject admission")
```

## 4. AI-native：排队不能冻结权限时间

Well-Architected 是质量与权衡框架，不是 Web 三层拓扑。新鲜时间与事务 replay
保护是成熟技术；AI-native planner 额外引入重试、排队 worker 与恢复，可能将旧权限/
时间戳包装成新状态。应在持久化准入边界采样，而不是依靠模型叙事或旧 request context。

可信 discovery/JWT algorithm/signature/client/user/session 关联、其他 assertions、
DPoP proof/nonce 与 token issuance 仍在参考实现之外。消费后崩溃或响应丢失会 burn
assertion；应以新的经过认证的 assertion 恢复，不能把 replay 当成功响应。
新 Session assertion 也不授权重复购买，不能替代 Stripe 业务幂等、Visa 通信身份
或 scoped 本地 approval。

## 5. 验证范围

[`tests/test_poppy_admission_clock.py`](../../tests/test_poppy_admission_clock.py)
新增 20 项方法；与原 replay/metadata 合计 62 项 Poppy 针对性测试通过。
SQL trace 在另一个 writer 持锁时观察实际 `BEGIN IMMEDIATE` 尝试，证明等待时未
调用 clock；解锁后精确到期拒绝、仍有效则准入。获取锁失败不调用 clock。
还覆盖严格 scalar/lifetime/时间端点、旧新入口并发一胜者、scope、真实新进程、
最少存储、时钟异常与真实 insert 后/commit 失败回滚；被覆盖的失败路径不消费 ID。
全库 4,042 项单测、编译、两个既有演示、109 个本地链接及两个相同双语可执行示例通过。
十个历史生成报告文件已恢复，没有报告内容进入暂存；README/assets 相对 `1d9273d`
零差异。最终 SHA CI/canonical 同步保留为发布后门禁，不作为 token 签发或付款证据。
