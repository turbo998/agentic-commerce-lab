# Stage 1658：Poppy assertion 的重放历史不能随 worker 重启消失

[English](2026-10-29-poppy-replay.en.md) | [当日研究](../../research/daily/2026-10-29.md) |
[此前的权限边界](2026-10-28-authority-recovery.md)

**核验日期：2026-10-29，北京时间 02:06 起；基线 `292207f`。**
这是 `synthetic` 离线工程参考，不是模型 benchmark、OAuth 服务、JWT 验签器、
协议认证或新的厂商产品发布。

## 1. 已发布 0.2 不能与进行中的 0.3 草案混用

官方仓库 HEAD 仍为 `a95b757872533a6ef1e1a9bcf29802857d2e5ff4`（2026-10-26）。
固定提交的[版本注册表](https://github.com/personal-agent-protocol/personal-agent-protocol/blob/a95b757872533a6ef1e1a9bcf29802857d2e5ff4/content/versions/versions.json)
记录 **0.2 于 2026-10-24 发布**；
[changelog](https://github.com/personal-agent-protocol/personal-agent-protocol/blob/a95b757872533a6ef1e1a9bcf29802857d2e5ff4/content/shared/changelog.mdx)
明确把 0.3 标为 **In progress**。本次访问日期不能被当作新发布证据。
[Sierra 的介绍](https://sierra.ai/blog/poppy) 覆盖发现、登录、会话和跨通道公司访问，
而非支付结算。

[已发布 0.2 规范](https://github.com/personal-agent-protocol/personal-agent-protocol/blob/a95b757872533a6ef1e1a9bcf29802857d2e5ff4/content/versions/0.2/spec.mdx)
§4.1/4.2 要求 audience 精确匹配 Company 的 `auth.issuer`，assertion 有效期不超过
五分钟，且在过期前拒绝来自同一 `client_id` 的重复 `jti`。
生产者必须使用至少 128 随机位；字符串长度和字母表不能证明熵。

DPoP proof 在 token endpoint 有**独立的**重放要求（§4.3）和 proof 接纳窗口，
不能当作带 `exp` 的 Session assertion。本轮只实现持久化 Session assertion 接纳，
不实现完整 token endpoint 所需的 client assertion 或 DPoP replay store。

## 2. 纯元数据检查不等于持久化接纳

原 [`poppy_guard`](../../lab/poppy_guard.py) 已覆盖 v0.2 元数据、同 client 重放与
每用户 DPoP key 隔离，但重放历史保存在调用者提供的内存集合中；
worker 重启或采用不同集合后会忘记历史。旧行为仍受支持，不宣称被全局透明升级。

[`PoppyAssertionJournal`](../../lab/poppy_replay.py) 是显式选择的共享本地文件入口：
复用抽取的纯元数据检查，以
`(Company auth.issuer, 已认证 client_id, SHA256(jti))`
为键，在一个 SQLite `BEGIN IMMEDIATE` 事务内消费 ID。
同一 client 改变 subject、session 或签名 key 不能另开重放命名空间。
重复值显式抛出 `PoppyReplayDetected`，存储故障原样抛出，commit 成功之后才返回。
[SQLite 事务合同](https://sqlite.org/lang_transaction.html) 支撑的是串行 writer 边界，
不是分布式授权服务器共识。

本地输入策略有意更严格：可信配置为规范、非空字符串；Session assertion 类型和 client
精确匹配；时间为非负 signed-64-bit 整数，不接受 bool，且 `iat <= now < exp`；
`jti` 限制为 22–256 个 base64url 字符。它们不证明完整协议兼容、随机性、签名、
真实身份认证或账户操作权限。

只保存公开 issuer/client 命名空间和 ID 摘要，不保存原始 JWT、`jti`、subject、
session ID、DPoP proof、Account/Session Token 或密码。
ID **不做清理**：即使新 assertion 的其他元数据有效，也不能复用旧 ID。
这比最短保留窗口更严格，但日志会持续增长；生产保留期、资源限制和共享 replay 服务
需要另行设计，不能把此离线参考直接当作部署方案。

## 3. 可执行合成示例

在仓库根目录执行。固定 ID 只是合成夹具，不是生产随机 ID 生成器；
示例不签发令牌、不验签，也不发出网络请求。

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from lab.poppy_guard import SessionAssertionClaims
from lab.poppy_replay import (
    PoppyAssertionJournal, PoppyReplayDetected, PoppyReplayScope,
)

with TemporaryDirectory() as directory:
    path = Path(directory) / "replays.sqlite3"
    scope = PoppyReplayScope(
        "https://auth.company.example", "https://agent.example/client.json",
    )
    assertion = SessionAssertionClaims(
        typ="poppy-session+jwt", iss=scope.client_id, sub="synthetic-user",
        aud=scope.auth_issuer, iat=1700000000, exp=1700000060,
        jti="synthetic_assertion_000001",
    )
    PoppyAssertionJournal(path).consume(scope, assertion, now=1700000000)
    try:
        PoppyAssertionJournal(path).consume(scope, assertion, now=1700000001)
    except PoppyReplayDetected:
        print("durable replay rejected")
    else:
        raise RuntimeError("replay was admitted")
```

[`单测`](../../tests/test_poppy_replay.py) 覆盖真实新进程拒绝、独立日志实例并发只产生一个
胜者、issuer/client 隔离、改变 subject/session 后仍拒绝、精确时间/类型/ID 边界、
无效输入不消费 ID、最小化持久化数据、插入/连接故障和写入之后的 commit 故障回滚。
**42 项针对性单测通过，新增 26 项方法。**

## 4. 集成顺序与 AI-native 架构反思

可信应用应先校验发现/issuer 配置、JWT 签名及算法、已认证 client、user/session 所有权、
其他 assertion 和 DPoP proof/nonce，再在签发凭据前消费 Session assertion。
本资产不实现这些外部校验，也不将接纳与令牌签发原子耦合。
若消费后响应丢失或进程崩溃，assertion 已被烧掉，恢复需新的已认证 assertion，
而非返回重放成功。

所有协作 worker 必须使用同一本地文件；分开数据库、绕过日志、恶意数据库访问或历史
回滚均可破坏此保证。不将其包装成网络文件系统或多主机部署方案。

Well-Architected 质量维度与 Web 三层拓扑不是同一概念；持久重放防护也不是 AI 发明。
AI-native 的约束在于重规划不能清空身份/权限历史：新的 assertion **不意味着**
重复业务操作成为新操作或获得新授权。Poppy 账户/会话访问、Visa 可信通信、
Stripe 支付观察、业务幂等与消费者购买同意仍须分开建模。
本轮未重新核验 Visa/Stripe 发布，也未认证跨厂商互操作。
