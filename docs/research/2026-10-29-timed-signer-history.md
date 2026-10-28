# Stage 1668：首次 timed signer 准入与两个既有写入同事务提交

[English](2026-10-29-timed-signer-history.en.md) |
[资产](../../lab/merchant_signers.py) |
[测试](../../tests/test_timed_signer_history.py) |
[前序锁后时间](2026-10-29-merchant-signature-time.md)

## 结论与证据边界

“曾经过 approval gate”不能推出“曾经过 timed signer gate”。本轮增加独立的
**首次 timed 分支执行历史**：只有该分支实际创建新 reservation 时，才把本地
signer scope、selected signature label、签名窗口与原锁后时钟样本一起提交。
attempt、approval history、timed history **三个写入同事务成功或回滚**。
它是可信数据库中的本地执行记录，不是可独立验签的凭证或当前授权。

2026-10-29 04:45 BJT 核验：

- [RFC 9421 §3.2.1](https://www.rfc-editor.org/rfc/rfc9421.html#section-3.2.1)
  的实际标题为 *Enforcing Application Requirements*，区分完整协议验证与应用
  对时间、key、nonce、tag 等附加要求；应用采用的要求不能因数学验签成功而跳过。
- [§3.3](https://www.rfc-editor.org/rfc/rfc9421.html#section-3.3)
  定义密码学 sign/verify 的输入输出；本地 SQLite 历史并没有保存或重做这些证明。
  **本审计 schema 是工程选择，不是 RFC 强制要求。**
- [Visa 官方仓库](https://github.com/visa/trusted-agent-protocol/tree/16d59bdf3f8a542bc538d0962edbb80ea30a02af)
  HEAD 仍为 `16d59bdf3f8a542bc538d0962edbb80ea30a02af`，
  时间 `2025-10-28T22:43:43Z`，不当作本次访问日新产品发布。

既有 [approval 首次历史](2026-10-29-admission-provenance.md) 提供 first-reservation-only、
禁止回填的本地模式；[Stage 1667](2026-10-29-merchant-signature-time.md)
提供单次锁后样本。本轮组合既有机制，不新增 Stripe/Sierra 发布判断。

## 小资产与读取合同

`TimedSignerAdmission(fingerprint, scope, signature_label, created, expires, admitted_at)`
及其嵌套 `MerchantSignerScope` 均冻结。新增 `merchant_timed_admissions` 表只保存
tenant/operation/full fingerprint、精确 URI/key ID、label、签名窗口和原样本。
`created`/`expires` **来自签名，不是 approval expiry**；`admitted_at` 与 approval
历史使用同一原始样本，没有第二次 clock 调用。

`MerchantSignerStore.read_timed_admission(operation)`：

1. 要求可信 `PaymentOperation`，以 tenant/operation 查找并匹配完整 fingerprint，
   因此 provider/account、idempotency key、approval 及 Checkout 改动不能复用记录。
2. 返回首次记录的 route/key/label/window；scope 的 tenant/merchant 从已绑定 operation
   恢复，不读取当前 permission，也不按当前请求的 scope 重写旧值。
3. 检查存储 scope、label、严格整数和历史关系
   `0 <= created <= admitted_at < expires <= 999_999_999_999_999`。
   缺失、绑定不符或坏元数据显式报错，不用默认值补成成功。
4. **不调用当前 clock，不重新准入**。撤销或到期后仍可读历史，但 mutation 继续拒绝。

原 `admit` 复用原事务和时钟 callback，仅在
`timed is not None and decision.dispatch_allowed` 时追加一次 INSERT，commit 后才返回。
最后一条历史写入失败也回滚先前 attempt/approval 写入；没有 after-commit 日志窗口。
既有 approval/journal schema 与 public transaction 不变。

| 已有状态或输入 | 新 timed history |
|---|---|
| 新 reservation 确实通过 timed 分支 | 同事务写入一份首次记录。 |
| 有效 retry，甚至换了仍允许的 scope/key/label/window | 不派发、不替换首次记录。 |
| bare signer、generic approval 或直接 journal 的既有 attempt | timed retry 不回填；即使已经 terminal 也不回填。 |
| 升级旧数据库 | 只新增空表，不从旧 approval/attempt 推测执行过新门禁。 |
| 撤销、过期、坏正文、clock 错误或失败 commit | 不新增可提交的三类记录，不返回可用 dispatch decision。 |

缺少记录仅表示**没有该执行记录**，不能反推曾被拒绝。

## 可执行 synthetic 示例

下面构造的是离线测试输入，不是声称由生产 verifier 生成的证据；不访问网络或发送支付。

```python
import json
from dataclasses import asdict, replace
from pathlib import Path
from tempfile import TemporaryDirectory

from lab.agent_identity_attestation_guard import compute_rfc9530_content_digest
from lab.checkout import Checkout
from lab.merchant_signers import MerchantSignerError, MerchantSignerScope, MerchantSignerStore
from lab.payment_approvals import PaymentApprovalStore
from lab.payment_attempts import PaymentAttemptJournal, PaymentOperation
from lab.request_binding import (
    MUTATION_COMPONENTS, RequestSignatureSnapshot, TimedRequestSignatureSnapshot,
)

now, samples = [1700000000], []

def clock():
    samples.append(now[0])
    return now[0]

with TemporaryDirectory() as directory:
    path = Path(directory) / "commerce.sqlite3"
    journal, approvals = PaymentAttemptJournal(path), PaymentApprovalStore(path)
    signers = MerchantSignerStore(path)
    uri = "https://synthetic-shop.example/checkout"
    operation = PaymentOperation(
        "tenant", "operation", "approval", "stripe:test", "acct_synthetic", "key",
        Checkout("synthetic-shop", "USD", "synthetic-sku", 1, 1000),
    )
    scope = MerchantSignerScope("tenant", "synthetic-shop", uri, "synthetic-key")
    approvals.approve(operation, expires_at=now[0] + 60)
    signers.allow(scope)
    body = json.dumps(asdict(operation.checkout)).encode()
    digest = compute_rfc9530_content_digest(body)
    snapshot = RequestSignatureSnapshot(
        "sig1", scope.key_id, MUTATION_COMPONENTS, "POST", uri, "application/json", digest,
    )
    timed = TimedRequestSignatureSnapshot(snapshot, now[0], now[0] + 10)
    ingress = dict(
        clock=clock, method="POST", target_uri=uri, content_type="application/json",
        content_digest=digest, content_encoding=None, body=body,
    )
    assert signers.admit(scope, approvals, journal, operation, timed, **ingress).dispatch_allowed
    first = signers.read_timed_admission(operation)
    assert first.scope == scope and first.signature_label == "sig1"
    assert first.admitted_at == approvals.read_admission(operation).admitted_at == now[0]
    now[0] += 1
    newer = replace(timed, signature=replace(snapshot, signature_label="sig2"), expires=now[0] + 20)
    assert not signers.admit(scope, approvals, journal, operation, newer, **ingress).dispatch_allowed
    assert signers.read_timed_admission(operation) == first
    signers.revoke(scope)
    try:
        signers.admit(scope, approvals, journal, operation, timed, **ingress)
    except MerchantSignerError as error:
        assert "revoked" in str(error)
    else:
        raise AssertionError("Revoked signer was admitted.")
    assert signers.read_timed_admission(operation) == first
    assert samples == [1700000000, 1700000001]
    assert journal.read(operation).outcome == "unknown"
    print("First timed history retained; retry and revoke cannot rewrite it.")
```

## AI-native 架构含义与未覆盖缺口

云 Well-Architected 的可靠性和传统三层职责分离仍有价值，但一条“请求成功”日志
无法区分哪个权限门禁在哪个时刻放行。Agent 可重试同一经济意图，因此执行架构
还需要**按事实类型区分的控制面历史**，而不是把单一 approval boolean、日志或
远端 status 扩张成完整授权链。这里保留各自的首次事实，不让新门禁给旧 attempt 补造来源。

数据库、策略操作者与完整 verifier adapter 仍必须可信。冻结对象、fingerprint、
label 或 key ID 都不认证密码学来源，也不是公钥 pinning；URI/key ID 不得含 credentials。
没有保存 raw body、raw signature、密钥、完整 signature base 或 verifier key material，
因此不能据此独立重验原始请求。没有 authenticated consumer consent、nonce 消费、
远端撤销、付款成功或 economic exactly-once 保证。裸 API 仍绕过 timed 路径。
没有不可篡改审计、外部签名、自动保留/清理策略；记录存储带来额外的数据保留责任。
样本时刻有效不等于 commit/send 时刻仍有效，读历史更不赋予新的发送许可。

## 验证

新增 **33** 项方法，**234** 项针对性测试通过：真实锁等待后的同一样本、零 epoch/
Structured Field 上限、跨 tenant 与完整绑定、首次 scope/label/window 不变、旧库/旧路径
不回填、fresh process、坏存储元数据、并发，以及最终 INSERT/真实第三写入/commit 失败
后三写入回滚。全库 **4,159** 项单测、编译、两个既有演示、**157** 个本地链接，
以及本轮/前轮共四份可执行示例（两组中英代码各自相同）通过。
最终 SHA CI/canonical main 同步保留为发布后门禁；这是 synthetic 工程测试，非模型 benchmark。
