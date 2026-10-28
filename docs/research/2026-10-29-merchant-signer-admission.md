# Stage 1666：已提交的本地 signer 撤销阻止该门禁下一次 reservation

[English](2026-10-29-merchant-signer-admission.en.md) |
[Signer 门禁](../../lab/merchant_signers.py) |
[Approval 核心](../../lab/payment_approvals.py) |
[测试](../../tests/test_merchant_signers.py)

## 结论与一手证据

入口密码学验证与当前商户权限是不同事实。排队前验证的 snapshot，不能单独证明
数据库 writer 释放锁后，本地 signer 策略仍允许准入。本轮提供 **opt-in 商户本地
权限门禁**，不是 Visa 验签、通用 TAP 强制规则或远端撤销服务。

2026-10-29 04:15 BJT 重新核验：

- [Visa TAP 开发文档](https://developer.visa.com/docs/trusted-agent-protocol)
  描述重建 signature base、验证 agent 公钥；agent recognition、可选 consumer/payment
  signature 不等于一个商户 purchase-approval boolean。
- [官方示例](https://github.com/visa/trusted-agent-protocol/blob/16d59bdf3f8a542bc538d0962edbb80ea30a02af/merchant-backend/app/security/signature_verification.py)
  展示配置式 trusted-agent/public-key lookup 与时间检查，不是商户同事务门禁。
  官方 HEAD 仍为 `16d59bdf3f8a542bc538d0962edbb80ea30a02af`，
  时间 **2025-10-28T22:43:43Z**，不当作本次访问日新发布。
- [RFC 9421 §3.2.1](https://www.rfc-editor.org/rfc/rfc9421.html#section-3.2.1)
  允许应用约束 key resolution、算法、age、nonce、tag；
  [§7.3.4](https://www.rfc-editor.org/rfc/rfc9421.html#section-7.3.4) 区分数学签名有效与
  key/algorithm 是否适合该消息，[§7.3.2](https://www.rfc-editor.org/rfc/rfc9421.html#section-7.3.2)
  讨论 key theft/rotation。

这些证据支持分离 identity 与应用策略，不强制本 SQLite 设计。本轮未核验 Stripe/Sierra 新发布。

## 小资产：一个事务、不同权限输入

`MerchantSignerScope(tenant_id, merchant, target_uri, key_id)` 是不可变可信配置，
不是身份证明。route/key ID 要求 ASCII 且无控制字符；全部 scope 值非空白、
无首尾空格。精确比较，不做 URI 归一化、通配符或跨 tenant/merchant 权限继承。
`MerchantSignerStore.allow(scope)` 仅记录一次操作者策略；
`revoke(scope)` 不可逆地翻转已有 scope 标记，可幂等调用；禁止替换/重新激活。
不同 key ID 可有独立 permit，只新增非 secret scope 标识与 revoke 标记存储。

Opt-in `admit(scope, approvals, journal, operation, signature, ...)`：

1. 要求可信类型、operation tenant/merchant 与 snapshot key ID 精确一致，
   复用原 signed-body/trusted-quote 校验，采用 scope 的精确 URI 和 POST profile。
2. 三个 store 必须 resolve 到同一 SQLite 文件，取得 `BEGIN IMMEDIATE` 后读取
   精确本地权限；缺失或 revoked 均拒绝。
3. 复用抽出的原 approval 事务 participant：不可变 approval binding、撤销、
   锁后一次 fresh clock 严格到期、reservation 与首次 approval-admission 历史。
4. commit 后才返回原 `DispatchDecision`；异常直接传播，失败写入/提交不返回可用 decision。

无嵌套 public transaction、新 journal schema、重复 approval 策略或旧 API 语义变化。
private approval participant 拒绝 autocommit。原 approval/journal API **绕过该可选
signer 门禁**；要求此约束的部署必须将所有相关 mutation 接入新 facade。

## 精确保证与未覆盖缺口

| 顺序或输入 | 有界结果 |
|---|---|
| 本地 revoke 提交后，阻塞 admission 才取得锁 | 该门禁拒绝，不写 reservation 或 approval-admission 历史。 |
| reservation 先于本地 revoke 提交 | 原 unknown attempt/history 保留，之后门禁重试拒绝；不取消/阻断远端 send。 |
| tenant、merchant、精确 URI 或 key ID 不符 | 不继承权限，reservation 前拒绝。 |
| signer permit 有效，approval 缺失/撤销/过期 | 不新增 reservation 或消费者权限。 |
| legacy reservation 或 approval 历史 | 不回填为 signer-gate provenance。 |

adapter 仍负责完整 RFC/TAP parser、crypto、directory/key 选择、algorithm、label/tag、
签名时间、nonce 和请求 provenance。`key_id` 字符串 **不是公钥 pinning**；
若外部把不同 key material 重新绑定到被允许的 ID，会破坏这里假定的来源绑定。
必须使用可信稳定解析策略，不能从 agent JSON 构建 snapshot/scope，也不能在 URI/key
标识中放 credentials。

本门禁**不重查排队期间 signature expiry**、不消费 nonce、不认证策略操作者、
不同步远端 directory、不证明 consumer consent。approval expiry 仅在锁后时钟采样点
检查，不保证 commit/send 物理截止。`read_admission` 仍只是 **approval-gate 历史**，
不证明此可选 signer 门禁执行过；没有签名或防篡改审计。分库、legacy bypass、
数据库快照回退会破坏共享本地保证。不发送、撤销、结算或履约任何付款。

## 离线可执行示例

snapshot 明确为 synthetic fixture，不是真实 Visa 验签结果；窄异常仅演示预期拒绝，
不将生产错误静默转换为 approval 或成功 ACK。

```python
import json
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory

from lab.agent_identity_attestation_guard import compute_rfc9530_content_digest
from lab.checkout import Checkout
from lab.merchant_signers import MerchantSignerError, MerchantSignerScope, MerchantSignerStore
from lab.payment_approvals import PaymentApprovalStore
from lab.payment_attempts import PaymentAttemptJournal, PaymentOperation
from lab.request_binding import MUTATION_COMPONENTS, RequestSignatureSnapshot

with TemporaryDirectory() as directory:
    path = Path(directory) / "commerce.sqlite3"
    journal, approvals = PaymentAttemptJournal(path), PaymentApprovalStore(path)
    signers = MerchantSignerStore(path)
    uri = "https://synthetic-shop.example/checkout?cart=one"
    operation = PaymentOperation(
        "tenant", "operation", "approval", "stripe:test", "acct_synthetic", "key",
        Checkout("synthetic-shop", "USD", "synthetic-sku", 2, 1000),
    )
    scope = MerchantSignerScope("tenant", "synthetic-shop", uri, "synthetic-key")
    body = json.dumps(asdict(operation.checkout)).encode()
    digest = compute_rfc9530_content_digest(body)
    fixture = RequestSignatureSnapshot(
        "sig1", "synthetic-key", MUTATION_COMPONENTS, "POST", uri, "application/json", digest,
    )
    values = dict(clock=lambda: 1700000000, method="POST", target_uri=uri,
                  content_type="application/json", content_digest=digest,
                  content_encoding=None, body=body)
    approvals.approve(operation, expires_at=1700000060)
    signers.allow(scope)
    first = signers.admit(scope, approvals, journal, operation, fixture, **values)
    assert first.dispatch_allowed and first.attempt.outcome == "unknown"
    signers.revoke(scope)
    try:
        signers.admit(scope, approvals, journal, operation, fixture, **values)
    except MerchantSignerError:
        pass
    else:
        raise AssertionError("A revoked scope must deny even a non-dispatch retry.")
    assert journal.read(operation) == first.attempt
    print({"synthetic": True, "real_payments": False, "outcome": "unknown"})
```

## 架构与验证

Well-Architected 是质量与取舍框架，不强制 Web 三层；应用权限与事务排序早于 AI。
AI-native commerce 增加独立 planner/worker 重试与证据重建风险，不能把“之前验签”
补全为“当前商户权限与消费者 approval”。它可以是模块化单体中的可信输入分离，
而非更多自授权 agent 或强制微服务。
[Stripe endpoint secret 轮换](2026-10-29-stripe-secret-rotation.md) 与
[Poppy replay 准入](2026-10-29-poppy-admission-clock.md) 有不同 key、namespace 和权限，
本 store 不合并它们。

新增 28 项方法，171 项针对性测试通过：真实 SQL trace 锁等待、revoke-first、
锁后 approval 到期、scope 隔离、并发仅一次 dispatch、新进程、真实 reservation/history
及 policy 写入/commit 失败回滚、legacy bypass/不回填与最少存储。
仅 synthetic 工程 fixture，不是模型 benchmark 或 Visa 互操作认证。
全库 4,096 项单测、编译、两个既有演示、127 个本地链接及两个相同双语可执行示例通过。
八个历史生成报告文件已恢复，没有报告内容进入暂存；README/assets 相对 `1d9273d` 零差异。
最终 SHA CI/canonical 同步保留为发布后门禁，不作为 signature 互操作或付款证据。
