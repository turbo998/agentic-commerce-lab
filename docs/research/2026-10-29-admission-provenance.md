# Stage 1662：后来的 approval 不能证明先前 reservation 经过了准入门禁

[English](2026-10-29-admission-provenance.en.md) |
[当日日报](../../research/daily/2026-10-29.md) |
[上一阶段](2026-10-29-approval-admission.md)

**结论：**已有 reservation 加上当前有效 approval，并不证明首次 reservation 当时
经过了批准门禁。应在同一事务中保留首次准入记录，不能由后来的重试补造历史。
**这只是本地应用历史，不是经过身份认证的消费者同意、密码学 receipt、
远端请求发送或 PSP 支付成功。**

2026-10-29 北京时间 03:22 从 `ef44ddf` 恢复，03:22–03:24 核验来源。
仅在 23:00–06:00 工作，05:30 起不再开新阶段；README/SVG 保护路径不变。
`provenance=synthetic`、`independently_reproduced=false`：离线工程 fixture，
不是模型 benchmark，也不是 Visa/Stripe/Poppy 真实互操作认证。

## 1. 不应合并为一个 receipt 的三种事实

| 事实 | 能说明什么 | 不能说明什么 |
|---|---|---|
| 当前本地 approval | 可信操作员的这条记录当前允许该精确 operation | 历史 reservation 是否使用过该门禁 |
| 首次准入记录 | 该本地入口在采样时间创建了首次 reservation | 谁同意、时钟真实准确或远端付款 |
| 可信 PSP 回读 | 既有 reconciliation 策略下的 provider-specific 结果 | 先前消费者同意或永久结算终局性 |

本轮重新核验的官方依据：

- [Stripe 幂等请求](https://docs.stripe.com/api/idempotent_requests)：API v1 在 endpoint
  开始执行后保存首次响应，包括 `500`；key 至少 24 小时后可清理，清理后复用会创建
  新请求。API v2 重试语义不同。Provider key 不是永久本地 approval 历史；
  本资产不增加 provider 重试，也不实现 v2。
- [Stripe agent 架构](https://docs.stripe.com/agents/how-it-works.md)：developer tools、
  Billing 和 commerce 是独立组件；工具访问不是购买权限、历史授权或支付证据。
- [Sierra Poppy 说明](https://sierra.ai/blog/poppy)：客户选择访问范围，企业设置参数，
  航班示例先与客户确认再预订；Session 访问与特定购买批准仍是不同边界。
- [SQLite 事务](https://www.sqlite.org/lang_transaction.html)：显式事务、单 writer 与
  commit/rollback 提供本地耦合；不嵌套 public transaction，也不提交后尽力写日志。

本轮没有核验新的协议发布或 Visa 发布。Stage 1659 TAP 请求绑定、Stage 1658
Poppy assertion replay 维持各自范围：消费 Session assertion 不是购买准入。

## 2. 增量持久化，不发明迁移历史

[`PaymentApprovalStore`](../../lab/payment_approvals.py) 打开旧数据库时新增空的
`payment_admissions` 表，只保留：

`tenant_id, operation_id, fingerprint, admitted_at, expires_at`

复用完整 operation fingerprint，绑定 tenant/operation/approval/provider/account/
idempotency key 与 Checkout。Hash 不是匿名化或防篡改；tenant/operation 标识本身
也可能敏感，仍需部署访问控制与一致的备份恢复。记录不复制正文、签名、token、
approver 身份或 PSP 响应。

在 Stage 1661 的既有同库写事务中：

1. 照旧验证签名 checkout 与有效 approval；取得写锁后采样可信时间。
2. 调用既有 journal reservation participant。
3. **仅在 `dispatch_allowed=True` 时**，在同一连接插入首次准入 fingerprint、
   本次时间及 expiry 快照。
4. commit 后才返回 decision。插入或提交错误直接抛出，回滚两处写入；
   已存在冲突记录不能获得新的 dispatch。

重复 admission 保留原时间/expiry，不产生新 dispatch。旧 direct reservation、
Stage 1661 时尚未记录 provenance 的 reservation、已终态的旧 attempt 都**不回填**，
即使现在 approval 能通过。没有历史就是没有历史，不能静默包装成成功。
旧 journal 与 signed-checkout facade 保持其旁路/兼容合同，不自动获得本轮 provenance。

`read_admission(operation)` 进行完整 fingerprint 和严格持久化整数/时间检查后，
返回 frozen `ApprovalAdmission(fingerprint, admitted_at, expires_at)`。
缺失或绑定不符显式抛出 `PaymentApprovalError`。它不检查当前 approval，不创造权限、
reserve、发送、reconcile 或核验当前 journal 结果；撤销/到期后仍能读历史。
API 没有更新/删除记录的方法，但直接 SQL 或替换数据库可以修改记录；
这不是签名、防篡改审计账本。

## 3. 可运行 synthetic 示例：历史不等于当前权限

签名 snapshot、时钟与 approval 都是可信 fixture，不是真实验签、身份认证或消费者同意。

```python
import json
from dataclasses import asdict, replace
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
uri = "https://synthetic-shop.example/checkout"
fixture = RequestSignatureSnapshot(
    "sig1", "synthetic-key", MUTATION_COMPONENTS,
    "POST", uri, "application/json", digest,
)
with TemporaryDirectory() as directory:
    path = Path(directory) / "commerce.sqlite3"
    journal, approvals = PaymentAttemptJournal(path), PaymentApprovalStore(path)
    request = dict(
        clock=lambda: now, expected_target_uri=uri, method="POST", target_uri=uri,
        content_type="application/json", content_digest=digest,
        content_encoding=None, body=body,
    )
    approvals.approve(operation, expires_at=now + 60)
    assert approvals.admit(journal, operation, fixture, **request).dispatch_allowed
    record = approvals.read_admission(operation)
    assert record.fingerprint == operation.fingerprint and record.admitted_at == now
    approvals.revoke(operation)
    assert approvals.read_admission(operation) == record
    assert journal.read(operation).outcome == "unknown"

    legacy = replace(operation, operation_id="legacy", approval_id="legacy",
                     idempotency_key="legacy")
    journal.reserve(legacy)
    approvals.approve(legacy, expires_at=now + 60)
    assert not approvals.admit(journal, legacy, fixture, **request).dispatch_allowed
    try:
        approvals.read_admission(legacy)
    except PaymentApprovalError:
        pass
    else:
        raise AssertionError("current approval must not invent prior gate history")
```

## 4. 架构：保留决策时证据，不依靠 prompt 回忆

Well-Architected 是质量与权衡框架，不是 Web 三层拓扑。事务审计记录并非 AI 发明；
AI-native 的额外风险是重规划 worker 把现在的权限当过去的权限，或把 `unknown`
总结成虚构的“已批准且成功”。应在实际 effect boundary 上将权限、首次准入历史与
provider outcome 分别建模，不能让模型生成缺失记录，或换 idempotency key 绕过未知状态。

本轮不新增 worker/outbox/send 路径。后来的撤销不能收回已提交的 reservation；
`admitted_at` 是取得写锁后的采样时间，不是实际 commit/send 时间。
数据库完整性、可信时钟、操作员认证与外部审计保留仍属生产部署责任。

## 5. 验证范围

[`tests/test_admission_provenance.py`](../../tests/test_admission_provenance.py)
新增 25 项方法；与既有 approval/checkout/journal/atomic-readback 合计 144 项针对性测试通过。
覆盖精确字段/完整绑定、零/最大整数边界、首次快照不变、旧库/终态 attempt 不回填、
并发一胜者、真实新进程、撤销/到期后恢复、实际 SQL 写入后的失败与 commit 回滚。
触发器观察事务内两处写入均已发生，同时独立 reader 看不到任何未提交记录；
只有已提交历史对外可见。持久化非整数时间显式拒绝。
全库 3,993 项单测、编译、两个既有演示、91 个本地链接及两个相同的双语可执行示例
通过。十个测试生成的历史报告文件已恢复，不发布为新 benchmark；
README/assets 相对 `1d9273d` 零差异。最终 SHA CI/canonical 同步保留为发布后门禁，
不作为真实付款结果。
