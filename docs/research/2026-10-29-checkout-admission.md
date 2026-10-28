# Stage 1660：已签署的客户端总额不能成为可信报价

[English](2026-10-29-checkout-admission.en.md) |
[每日记录](../../research/daily/2026-10-29.md) |
[上一阶段](2026-10-29-request-binding.md)

**结论：** 字节完整性、JSON 语义、可信报价、消费者授权与业务幂等必须分开。
Stage 1659 只证明传入字段与可信签名 snapshot 的绑定；正文可能依然有重复键，
也可能是签名正确但价格错误的 JSON。本阶段以**已有可信 Checkout** 为比较基准，
全部门禁通过后才调用已有 journal，不从客户端价格、签名身份或模型输出创建授权。

北京时间 2026-10-29 02:46 从 `779ebe6` 恢复，02:47–02:48 核验下列一手资料。
保持 23:00–06:00 门禁，05:30 起不启动新阶段，README/SVG 不改动。
`provenance=synthetic`、`independently_reproduced=false`；这是离线工程资产，
不是模型 benchmark、Stripe SDK 认证、真实签名/支付互操作或新的产品发布。
本轮未重新核验 Visa/Sierra 的发布。

## 1. 资料与已有资产

| 证据 | 本阶段采用的约束 |
|---|---|
| [Stripe 动态更新金额指南，Payment Intents 版本](https://docs.stripe.com/payments/advanced/dynamically-update-amounts.md?payment-ui=elements) | 服务端确定总额，不能信任客户端价格；业务授权和可更新状态另行检查 |
| [RFC 8259 §4/6/8/9](https://www.rfc-editor.org/rfc/rfc8259.html) | 重复名称可能产生不同解释；非有限数不在 JSON 数字语法内；明确编码与解析资源边界 |
| [Python 3.12 JSON 文档](https://docs.python.org/3.12/library/json.html#repeated-names-within-an-object) | 默认重复键 last-wins，接受 NaN/Infinity，不能直接当作严格业务入口 |
| [`Checkout`](../../lab/checkout.py) | 复用已校验不可变报价；amount 是含税费/运费的总额，不是单价 |
| [`PaymentAttemptJournal`](../../lab/payment_attempts.py) | 复用持久 operation/approval/provider key 绑定；首次本地 dispatch 后仍为 unknown |

RFC 的对象名称唯一性是 SHOULD，不将本地拒绝重复键说成所有合法 JSON 的语法要求。
Stripe 文档不是新发布公告，也不证明商户已经实现定价、同意或 PaymentIntent 更新。

## 2. 显式选择的接纳入口

[`reserve_signed_checkout`](../../lab/checkout_admission.py) 接收可信 journal、
已批准的 `PaymentOperation`、可信签名 snapshot 和实际 ingress 原始值。
可信路由配置 `expected_target_uri` 与 operation lookup 不得由请求 JSON/agent 决定。

1. 要求 POST，实际完整 URI 精确匹配可信配置。
2. 复用 Stage 1659 的签名 snapshot/原始 body 绑定，再解析 JSON，不先重序列化。
3. 仅接受一个 UTF-8 object，键集合精确为 merchant/currency/sku/quantity/amount。
4. 拒绝解码后重复键（包括转义后的同名键）、fraction/exponent/非有限数、boolean/
   string 数字、未知字段、BOM、非法 Unicode scalar；不规范化币种或商户身份。
5. 严格类型与字段逐项匹配可信 Checkout，最后返回原 journal 的 `DispatchDecision`。

这五个字段是**本地单商品协议切片**，不是 Stripe API 或 Visa TAP 的通用 payload。
不能把 quantity × amount 当作总额；amount 本身已是可信总额。
既有 1 MiB 原始 body 限制仍有效；integer token 转换前最多 20 个字符，
最终值必须精确匹配 Checkout 的正 signed-64-bit 整数。合法 signed-64 边界不四舍五入；
这不意味着 JavaScript binary64 能精确往返这些数，跨语言生产 schema 仍需单独设计。
深层非 object/schema 数据被拒绝，decoder 的 RecursionError 也显式转换为接纳错误；
不宣称实现了独立固定深度预算或流式解析。

重复键 hook 从已有 MCP inventory 代码抽取到 [`json_members.py`](../../lab/json_members.py)。
旧 `lab.mcp_migration.unique_members` 名称、ValueError 文本和 module/direct-file CLI
保持兼容；不改 inventory policy、Stripe inbox 或历史模拟 pipeline。
接纳/schema 错误为 `CheckoutAdmissionError`；原 `RequestBindingError`、journal
conflict 与存储错误原样传播，不改成成功形状的默认值。

## 3. 可运行 synthetic 示例：不同签名字节仍是同一 operation

以下 snapshot 是 fixture，不是生产验签实现。假设可信调用者已完成定价、消费者同意、
有效期/撤销与 operation 选择；本例不创建或证明这些前提。

```python
import json
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from lab.agent_identity_attestation_guard import compute_rfc9530_content_digest
from lab.checkout import Checkout
from lab.checkout_admission import reserve_signed_checkout
from lab.payment_attempts import PaymentAttemptJournal, PaymentOperation
from lab.request_binding import MUTATION_COMPONENTS, RequestSignatureSnapshot

operation = PaymentOperation(
    "tenant", "operation", "approval", "stripe:test", "acct_synthetic", "key",
    Checkout("synthetic-shop", "USD", "synthetic-sku", 2, 1000),
)
uri = "https://synthetic-shop.example/checkout?cart=one"
with TemporaryDirectory() as directory:
    journal = PaymentAttemptJournal(Path(directory) / "commerce.sqlite3")
    decisions = []
    for indent in (None, 2):
        body = json.dumps(asdict(operation.checkout), indent=indent).encode()
        digest = compute_rfc9530_content_digest(body)
        fixture = RequestSignatureSnapshot(
            "sig1", "synthetic-key", MUTATION_COMPONENTS,
            "POST", uri, "application/json", digest,
        )
        decisions.append(reserve_signed_checkout(
            journal, operation, fixture, expected_target_uri=uri,
            method="POST", target_uri=uri, content_type="application/json",
            content_digest=digest, content_encoding=None, body=body,
        ))
    assert [d.dispatch_allowed for d in decisions] == [True, False]
    assert all(d.attempt.outcome == "unknown" for d in decisions)
```

字节/签名变化不是新经济操作；未知结果不能通过换 JSON 格式、operation/key 来重发。
失败请求不预占首次 dispatch；成功接纳只记录本地 reservation，没有任何网络付款。
程序必须检查 `dispatch_allowed`；原 journal API 仍可绕过此 opt-in facade。

## 4. 架构与验证边界

Well-Architected 是质量与权衡框架，不是 Web 三层部署图。成熟系统本就需要服务端
定价、授权、schema 和幂等；AI-native 的额外约束是防止可变 planner/工具翻译层
用已认证但不可信的值重新构造报价、批准对象或 retry 身份。确定性 effect 路径应保留
每条事实的权威来源，而不是把“签名成功”放大为“一切可执行”。

本入口不验证真实签名/key/nonce、不提供 consent service，也不将撤销/过期核验与
reservation 放进同一事务。生产可信调用者必须在每次接纳前执行这些业务门禁；
支付 provider 的 wire mapping、实时金额更新、token、结算和多商品 schema 都不在范围内。

[`tests/test_checkout_admission.py`](../../tests/test_checkout_admission.py) 新增 30 项方法，
与 migration/checkout/payment-attempt/binding 合计 94 项针对性测试通过。
覆盖字节绑定先于解析、严格语义、同名转义键、20/21 字符整数 token、1 MiB ±1 边界、
真实新进程与并发一胜者、终态/unknown 不重发及旧 CLI。
初次验证修正了依赖平台递归阈值的测试断言，并补齐 helper 抽取引入的直接文件 CLI 兼容性。
全库 3,934 项单元测试、编译、两个既有演示、81 个本地链接和两个双语可执行示例
均通过；历史测试生成的十个报告文件已恢复，不发布为新 benchmark。
README.md、README.en.md 与 assets/ 相对 `1d9273d` 零差异。
最终提交 CI 与 canonical main 同步仍作为发布后的独立收尾门禁，不宣称真实付款或授权。
