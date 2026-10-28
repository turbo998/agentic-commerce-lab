# Stage 1661：撤销检查与首次 reservation 必须共享写事务

[English](2026-10-29-approval-admission.en.md) |
[每日记录](../../research/daily/2026-10-29.md) |
[上一阶段](2026-10-29-checkout-admission.md)

**结论：** 先在一个连接检查 approval、再在另一个连接 reserve，会留下撤销竞态。
本增量在同一 SQLite 写事务内读取绑定 approval、检查撤销/到期并调用已有 reservation
逻辑。时钟在取得写锁后采样，避免把排队前的时间误当作当前接纳时间。
**只约束本地 admission：后来的撤销不能撤回已提交的 dispatch 决策，也不能阻止远端付款。**

北京时间 2026-10-29 03:03 从 `238aa8c` 恢复，03:03–03:06 核验一手资料及既有代码。
严格保持 23:00–06:00 门禁，05:30 起不启动新阶段，README/SVG 保护路径不变。
`provenance=synthetic`、`independently_reproduced=false`；不是模型 benchmark、
真实签名/支付互操作、consent UI 或法律意义上的同意证明。

## 1. 协议权限与本地审批不是同一事实

| 一手资料 | 本次可支持的架构边界 |
|---|---|
| [Sierra 对 Poppy 的说明](https://sierra.ai/blog/poppy) | 客户决定 agent 的 access，企业决定可执行参数；航班示例在预订前向客户确认 |
| [Poppy 固定版本注册表](https://github.com/personal-agent-protocol/personal-agent-protocol/blob/a95b757872533a6ef1e1a9bcf29802857d2e5ff4/content/versions/versions.json) | 0.2 于 2026-10-24 发布；0.3 无 published 字段，不能把访问日期当作发布 |
| [Stripe：agent 如何使用平台](https://docs.stripe.com/agents/how-it-works.md) | developer tools、Billing 与 commerce 是不同组件；MCP 开发工具不会独立完成 billing/commerce |
| [SQLite transaction](https://www.sqlite.org/lang_transaction.html) | 同一文件只有一个同时写事务；BEGIN IMMEDIATE 建立写事务，不能嵌套 BEGIN |

本次 Poppy 官方 HEAD 仍为 `a95b757872533a6ef1e1a9bcf29802857d2e5ff4`
（2026-10-26），没有新版本发布证据。本轮未重新核验 Visa 发布；
Stage 1659 的 TAP 签名覆盖与本地 admission 仍是独立门禁。
Poppy session/account access、Stripe MCP 工具权限、TAP 身份都不自动产生某次购买的授权。

## 2. 最小资产与兼容边界

[`PaymentApprovalStore`](../../lab/payment_approvals.py) 是显式选择的可信操作员元数据存储。
`approve(operation, expires_at=...)` **记录**外部可信决定，并不认证操作者或创造消费者同意。
表中仅有 tenant_id、approval_id、既有完整 operation fingerprint、expires_at、revoked。
Fingerprint 绑定 operation/approval/provider/account/key/checkout，不只绑定金额。
不保存原始 JSON、JWT、Poppy token、签名或买家身份。

记录不可覆盖、延长、复活或通过此 API 清理；重复 approve 明确报错，
同一绑定的 revoke 可重复调用。撤销必须在 commit 成功后才返回。
旧 [`CheckoutStore`](../../lab/checkout.py) 使用全局 mandate ID 与模拟 receipt；
不自动迁移或把这些行视为 tenant/provider/operation 范围的批准。

`admit(...)` 先复用 [`validate_signed_checkout`](../../lab/checkout_admission.py)，
再要求 approval store 与 payment journal 的 **resolved 文件路径相同**。
跨文件明确拒绝；不把分离事务拼成成功保证。

1. `BEGIN IMMEDIATE` 获得本地写事务。
2. 查 tenant/approval 范围及精确 operation fingerprint，拒绝缺失、变化或 revoked。
3. 调用必传的可信 clock；严格检查非负 signed-64-bit 整数和存储 expiry。
4. 要求 `now < expires_at`，恰好到期即拒绝。
5. 调用 journal 的共享事务 participant，commit 后才返回原 `DispatchDecision`。

[`PaymentAttemptJournal`](../../lab/payment_attempts.py) 仅抽取
`_reserve_in_transaction`，不改旧 reserve 的幂等/unknown/conflict 合同；
新 participant 拒绝无事务调用。旧 Stage 1660 facade 也保留原行为。
新入口**每次**都检查有效 approval，连不 dispatch 的 retry 也如此；撤销/到期后
仍可独立 `journal.read` 做恢复，不以接纳错误重建 key、operation 或再次发款。
既有 standalone journal/SQL 写入仍可绕过 opt-in 保证，历史 reservation 也不证明先前有批准。

## 3. 可运行 synthetic 示例

以下 signer、approval 和时钟均为测试 fixture，不是生产同意 UI 或公钥验签。
生产 clock 必须由可信应用在回调时读取新鲜时间，不得捕获请求/模型提供的旧时间。

```python
import json
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from lab.agent_identity_attestation_guard import compute_rfc9530_content_digest
from lab.checkout import Checkout
from lab.payment_approvals import PaymentApprovalError, PaymentApprovalStore
from lab.payment_attempts import PaymentAttemptJournal, PaymentOperation
from lab.request_binding import MUTATION_COMPONENTS, RequestSignatureSnapshot

now = 1700000000
operation = PaymentOperation(
    "tenant", "operation", "approval", "stripe:test", "acct_synthetic", "key",
    Checkout("synthetic-shop", "USD", "synthetic-sku", 2, 1000),
)
body = json.dumps(asdict(operation.checkout)).encode()
digest = compute_rfc9530_content_digest(body)
uri = "https://synthetic-shop.example/checkout?cart=one"
fixture = RequestSignatureSnapshot(
    "sig1", "synthetic-key", MUTATION_COMPONENTS,
    "POST", uri, "application/json", digest,
)
with TemporaryDirectory() as directory:
    path = Path(directory) / "commerce.sqlite3"
    journal, approvals = PaymentAttemptJournal(path), PaymentApprovalStore(path)
    approvals.approve(operation, expires_at=now + 60)
    request = dict(
        clock=lambda: now, expected_target_uri=uri, method="POST", target_uri=uri,
        content_type="application/json", content_digest=digest,
        content_encoding=None, body=body,
    )
    first = approvals.admit(journal, operation, fixture, **request)
    assert first.dispatch_allowed and first.attempt.outcome == "unknown"
    assert not approvals.admit(journal, operation, fixture, **request).dispatch_allowed
    approvals.revoke(operation)
    try:
        approvals.admit(journal, operation, fixture, **request)
    except PaymentApprovalError:
        pass
    else:
        raise AssertionError("revocation must reject further admission")
    assert journal.read(operation) == first.attempt
```

## 4. 竞态、时间与 AI-native 架构判断

撤销先 commit，后来的 admission 不能取得新的 dispatch；admission 先 commit，
后来的撤销不能删除 unknown，也不能让 agent 另起 key。已经持有 dispatch 决策但尚未
发送的 worker 仍可能发送；网络 side effect 不属于这个 SQLite 事务。
Expiry 在写锁内采样时检查，不是对 commit/发送时刻的物理时间承诺；
时钟准确性、暂停、跨机一致性、数据库文件与一致备份/恢复仍由部署负责。

Well-Architected 是质量与权衡框架，不等同于 Web 三层拓扑。事务串行化和审批门禁
并非 AI 发明；AI-native 的额外风险是重规划 worker 将过时权限、旧 clock 或恢复请求
重新包装为新授权。应把约束放到真正的 effect 接纳路径，并保留可恢复的未知结果，
而非把消费者同意仅写进 planner prompt。

不实现：生产 signer/操作者认证、Poppy OAuth、consent UI/法律证据、分布式撤销、
远端取消/退款或支付发送。审批历史不自动清理，存储增长与授权生命周期仍需生产设计。

## 5. 验证范围

[`tests/test_payment_approvals.py`](../../tests/test_payment_approvals.py) 新增 34 项方法，
与 checkout/admission/journal/atomic-readback 合计 119 项针对性测试通过。
覆盖精确到期、撤销、完整 fingerprint、tenant scope、不可变记录、旧 mandate 不复用、
真实新进程、并发 admission/revoke，以及 SQL trace 确认 worker 已尝试 BEGIN 后才释放锁。
注入先观察到 SQL insert/revoked 更新，再制造失败，验证 approve/revoke/reservation
commit 失败不返回成功；存储 expiry 的非整数也明确拒绝。
全库 3,968 项单元测试、编译、两个既有演示、89 个本地链接及两个双语可执行示例
均通过；历史测试生成的八个报告文件已恢复，不发布为新 benchmark。
README.md、README.en.md 与 assets/ 相对 `1d9273d` 零差异。
最终提交 CI 与 canonical main 同步保留为发布后收尾门禁，不宣称远端效果或同意认证。
