# Stage 1667：签名与 approval 共用锁后一次时间采样

[English](2026-10-29-merchant-signature-time.en.md) |
[时间输入与校验](../../lab/request_binding.py) |
[Signer 门禁](../../lab/merchant_signers.py) |
[测试](../../tests/test_merchant_signature_time.py) |
[前序本地撤销](2026-10-29-merchant-signer-admission.md)

## 结论与一手证据

入口验签时有效，不代表排队取得商户写锁后仍未到期。本轮新增可选
`TimedRequestSignatureSnapshot(signature, created, expires)`，将**同一份已验证签名**
的 snapshot 与已认证时间参数交给既有 signer 门禁。取得写锁后，签名时间和
approval 到期共用**一次可信 clock 采样**，不新增事务、支付发送或历史 schema。

2026-10-29 04:29–04:30 BJT 重新核验：

- [RFC 9421 §2.3](https://www.rfc-editor.org/rfc/rfc9421.html#section-2.3)、
  [§2.5](https://www.rfc-editor.org/rfc/rfc9421.html#section-2.5)：
  `created`/`expires` 属于每份签名自己的 signature parameters；
  `@signature-params` 必须进入 signature base，但不是 covered-components 列表中的一项。
  可信 verifier 必须从**所选同一签名**认证并提取这些值，不能跨 label 拼接。
- [§3.2.1](https://www.rfc-editor.org/rfc/rfc9421.html#section-3.2.1)
  允许应用规定年龄/到期等要求；RFC 并非普遍强制所有签名同时提供这两个参数。
  本地要求二者齐备、非负、零时钟偏差且到期排他，不能包装成 TAP 通用要求。
- [RFC 8941 §3.3.1](https://www.rfc-editor.org/rfc/rfc8941.html#section-3.3.1)：
  这些参数采用 Structured Field Integer，最大正值为 `999_999_999_999_999`，
  **不是 signed-64-bit 上限**。此处已解码的签名参数受该范围约束。
- [RFC 9421 §7.2.2](https://www.rfc-editor.org/rfc/rfc9421.html#section-7.2.2)
  将时间限制与 nonce 重放检测区分；仍在有效窗口内的重复签名不会因此被消费掉。
- [Visa 官方仓库](https://github.com/visa/trusted-agent-protocol/tree/16d59bdf3f8a542bc538d0962edbb80ea30a02af)
  HEAD 仍为 `16d59bdf3f8a542bc538d0962edbb80ea30a02af`，
  时间 `2025-10-28T22:43:43Z`；不当作本次访问日新产品发布。

这是本地应用准入 profile，不是 RFC parser、Visa 验签实现或供应商架构合规声明。
本轮未核验 Stripe/Sierra 新发布；不向这些产品外推本地保证。

## 小资产与精确合同

`require_signature_time(timed, now=...)` 是纯校验：wrapper 内必须是一份
`RequestSignatureSnapshot`；`created`/`expires` 必须为严格整数（拒绝 bool、
float、string、负数及超出 Structured Field 范围），且 `created < expires`。
可信 clock 值继续遵守既有 approval 的非负 signed-64-bit 整数约束。
窗口为 **`created <= now < expires`**；不发明最大签名寿命、不挪用 Stripe 的
300 秒容忍值，不用缺省值补造缺失参数。

`MerchantSignerStore.admit` 的原 `signature` 参数现在接受 bare 或 timed snapshot：

1. timed 输入先解出原 snapshot，复用可信 scope/key-ID、原始字节、签名覆盖、
   精确 URI、严格 JSON 与可信 Checkout 匹配。
2. 取得同库 `BEGIN IMMEDIATE`，检查本地 signer 权限与既有 approval binding/revoke。
3. timed 分支在原 approval 核心调用 clock 时，先用这**一个样本**检查签名窗口，
   再将原值返回给 approval 到期校验及首次 `admitted_at` 写入。
4. reservation/history 同事务 commit 后才返回；时间错误、clock 异常及失败提交
   不返回可用 dispatch decision。即使是不会再次派发的 retry，也不能绕过时间检查。

`RequestSignatureSnapshot` 原输入行为不变，**不增加 signature-time 检查**。
旧 approval/journal API 也绕过此可选边界；需要强约束的 route adapter 必须要求
timed 输入，不能在失败时重试为 bare。格式错误的 wrapper 不会在这里降级。
现有 approval history 仍只证明 approval gate，**不证明 timed/signature/signer provenance**。

## 可执行 synthetic 示例

输入是明确构造的离线测试对象，不是假称生产验签结果；不访问网络或发送支付。

```python
import json
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory

from lab.agent_identity_attestation_guard import compute_rfc9530_content_digest
from lab.checkout import Checkout
from lab.merchant_signers import MerchantSignerScope, MerchantSignerStore
from lab.payment_approvals import PaymentApprovalStore
from lab.payment_attempts import PaymentAttemptJournal, PaymentOperation
from lab.request_binding import (
    MUTATION_COMPONENTS, RequestBindingError, RequestSignatureSnapshot,
    TimedRequestSignatureSnapshot,
)

now = [1700000000]
samples = []

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
    first = signers.admit(scope, approvals, journal, operation, timed, **ingress)
    assert first.dispatch_allowed and first.attempt.outcome == "unknown"
    assert approvals.read_admission(operation).admitted_at == samples[0]
    now[0] += 10
    try:
        signers.admit(scope, approvals, journal, operation, timed, **ingress)
    except RequestBindingError as error:
        assert "window" in str(error)
    else:
        raise AssertionError("Expired timed retry was accepted.")
    assert samples == [1700000000, 1700000010]
    assert journal.read(operation) == first.attempt
    assert approvals.read_admission(operation).admitted_at == 1700000000
    print("Expired timed retry rejected; original payment remains unknown.")
```

## 为什么不是经典三层分层问题

Web 前端/API/数据库的分层与云 Well-Architected 的可靠性原则仍然必要，
但不能单独回答**权限事实在哪个线性化点仍有效**。Agent 可多次尝试经济动作，
签名 ingress、排队、权限撤销、批准到期、reservation 与远端结果是不同事实。
本资产将相邻本地策略放到同一写锁及时间样本下，而非把“入口验签通过”永久缓存成购买权。

保证仅在锁后**采样点**成立：并不保证物理 commit 或远端发送时仍未到期。
clock 必须由可信应用在调用时 fresh 采样；返回旧 ingress 时间的 callback 会破坏前提。
冻结 wrapper 不认证来源，也不能识别伪造/跨 label 的参数；完整 RFC/TAP crypto、
key/directory/algorithm、签名参数 provenance、nonce、consumer authority 仍由可信 adapter 负责。
没有新增公钥 pinning、远端撤销、nonce 消费、签名时间审计记录或经济 exactly-once 保证。

## 验证

新增 **30** 项方法，**201** 项针对性测试通过：真实阻塞 BEGIN 后到期/仍有效/
到达 created 边界，单次 clock 与 history 样本一致，严格类型/15 位上限、原 scope/body/
quote 检查、过期 retry、旧路径、撤销、并发，以及真实写入后/commit 失败回滚。
全库 **4,126** 项单测、编译、两个既有演示、**149** 个本地链接及两份相同双语
可执行示例通过。最终 SHA CI/canonical main 同步保留为发布后门禁；
这是 synthetic 工程测试，不是模型 benchmark。
