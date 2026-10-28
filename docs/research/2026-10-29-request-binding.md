# Stage 1659：Agent 身份签名不等于请求正文已受保护

[English](2026-10-29-request-binding.en.md) |
[每日记录](../../research/daily/2026-10-29.md) |
[阶段索引](../stage-archive-index.md)

**结论：** 商户不能由“某个 TAP 签名有效”推断所有 mutation 输入都受保护。
本增量以一个可信签名的**覆盖项与原始签名值**为边界，逐项匹配实际请求，
再核对原始 body 与已签署的 Content-Digest；正文改变后重新计算摘要也不得通过。
这是商户自定义的窄 JSON mutation profile，不是 Visa 新增强制规范。

研究于北京时间 2026-10-29 02:27 从 `134c414` 恢复，02:28–02:32 访问一手资料。
遵守 23:00–06:00 门禁，05:30 起不启动新阶段；README/SVG 保护路径不变。
`provenance=synthetic`，`independently_reproduced=false`：离线人工构造的工程
验证，不是模型 benchmark、Visa 认证、真实签名互操作或支付结果。
没有重新核验 Stripe/Sierra 的产品发布。

## 1. 一手证据与版本边界

| 证据 | 本次可支持的结论 | 不能推导的结论 |
|---|---|---|
| [Visa TAP 开发者文档](https://developer.visa.com/docs/trusted-agent-protocol) | RFC 9421 签名支持 agent/意图及可选消费者/支付信息传递 | 任意签名都覆盖正文、所有 query/header；身份等于购买同意 |
| [官方商户签名示例，固定提交](https://github.com/visa/trusted-agent-protocol/blob/16d59bdf3f8a542bc538d0962edbb80ea30a02af/merchant-backend/app/security/signature_verification.py) | 示例按选中的组件构造验证数据 | 示例是完整 RFC 解析器或商户通用授权规则 |
| [RFC 9421](https://www.rfc-editor.org/rfc/rfc9421.html) | 应用需要选择相关签名并执行覆盖策略；不同标签的覆盖不能随意拼接 | 密码学有效就代表应用字段全部绑定 |
| [RFC 9530 §6.3](https://www.rfc-editor.org/rfc/rfc9530.html#section-6.3) | digest 保护内容字节，解释依赖 Content-Type/Content-Encoding；摘要本身不认证或授权 | JSON 语义正确、内容未经过转码、消费者授权或支付完成 |

本次官方仓库 HEAD 仍为 `16d59bdf3f8a542bc538d0962edbb80ea30a02af`，
提交日期为 **2025-10-28**；不把 2026 年的访问日期写成新发布。
`@path` 不包含全部 query，本地策略选择 `@target-uri` 绑定完整目标 URI。
此处不更改历史 Stage 7 HMAC/目录/配额模拟，其“必需覆盖项”属于本地演示，
不是 RFC 9421 或 TAP 对所有应用的统一要求。

## 2. 小资产：只接纳精确绑定，不接纳模型声称的身份

[`lab/request_binding.py`](../../lab/request_binding.py) 提供
`RequestSignatureSnapshot` 与 `require_bound_json_mutation(...) -> None`。
Snapshot 必须来自**同一条请求、同一个已验证签名**的可信 ingress adapter，
保留 label、key ID、原始覆盖标识符和 method/URI/type/digest 的已签署值。
Dataclass 的构造或不可变性不提供认证；绝不能从 agent 输出或请求 JSON 构造可信证据。

| 本地规则 | 精确行为 |
|---|---|
| 同一签名覆盖 | 必须含裸 `@method`、`@target-uri`、`content-type`、`content-digest`；不合并多个签名的证据 |
| 参数处理 | 参数化、重复或非裸组件显式拒绝，不剥离 `;sf`、`;req`、`;tr` 等语义 |
| 当前值绑定 | method/URI/type/digest 与 snapshot 精确一致；不做 URL 大小写、百分号或 JSON 归一化 |
| 方法/媒体类型 | 仅大写 POST/PUT/PATCH/DELETE，精确 `application/json`，不接受 charset 参数 |
| Content-Encoding | 必须缺席；连 `identity`/空字段也拒绝，避免假装支持代理解压后的签名语义 |
| 字节/资源 | 原始不可变 `bytes`；最多 **1,048,576 bytes**，超出 1 byte 即拒绝 |
| 摘要 | 仅精确规范形式 `sha-256=:...:`；复用已有 formatter，常量时间比较原始 body 摘要 |
| 返回与副作用 | 成功返回 `None`，失败抛 `RequestBindingError`；不写 journal、不发支付、不消费 nonce |

允许额外的裸组件名称，但本 helper **不核对它们的值**；业务关键 header 仍需
adapter/路由自己的签名值与不可变 operation/approval 绑定。签名 label/key ID 在此
只保留上下文并检查格式，不做签名人白名单、key 发现或真实性检查。
可信 verifier 负责完整 RFC 9421 解析与密码学、相关 label/tag、key 信任、有效期、
nonce/重放及准确的 `@target-uri` 派生；adapter 还必须拒绝歧义/重复原始 HTTP header，
并在代理转码或重序列化**之前**传入签名所绑定的 ingress 字节。

这是有意收窄的应用策略：更丰富但合法的 RFC 9530 字典/算法/参数可能被拒绝。
没有手写 Structured Fields 通用解析器，也没有模拟公钥验签成功。

## 3. 可运行的 synthetic 边界示例

以下 snapshot 是测试 fixture，**不是接入未验证 HTTP 请求的生产写法**。
独立 .NET SHA256 计算得到固定 body 的十六进制值
`a223b60dc6adbc2911e7c073889b220df1181c5534fa6be58c3a70981c354c54`。

```python
from lab.agent_identity_attestation_guard import compute_rfc9530_content_digest
from lab.request_binding import (
    MUTATION_COMPONENTS, RequestBindingError, RequestSignatureSnapshot,
    require_bound_json_mutation,
)

body = b'{"amount":1000,"currency":"usd"}'
digest = "sha-256=:oiO2DcatvCkR58BziJsiDfEYHFU0+mvljDpwmBw1TFQ=:"
uri = "https://synthetic-shop.example/checkout?cart=one"
fixture = RequestSignatureSnapshot(
    "sig1", "synthetic-key", MUTATION_COMPONENTS,
    "POST", uri, "application/json", digest,
)
assert compute_rfc9530_content_digest(body) == digest
assert require_bound_json_mutation(
    fixture, method="POST", target_uri=uri, content_type="application/json",
    content_digest=digest, content_encoding=None, body=body,
) is None

changed = body.replace(b"1000", b"9000")
try:
    require_bound_json_mutation(
        fixture, method="POST", target_uri=uri, content_type="application/json",
        content_digest=compute_rfc9530_content_digest(changed),
        content_encoding=None, body=changed,
    )
except RequestBindingError:
    pass
else:
    raise AssertionError("a recomputed header must not replace the signed digest")
```

绑定通过不证明正文是有效 JSON；JSON schema、重复 key、金额/币种/商户语义、
消费者同意、幂等以及业务状态仍是后续独立门禁。反复调用不消耗 nonce，不防重放。
匹配成功不允许把 Stage 1652–1658 的 `unknown` 支付关闭或重新 dispatch。

## 4. 架构判断：由身份通道走向不可变 effect 输入

Well-Architected 是质量与权衡框架，不等同于 Web 三层部署拓扑。
签名覆盖、字节完整性和应用授权是成熟系统已有的安全边界；AI-native 的额外风险
是规划器、工具 adapter 或摘要器把“身份已验证”补全成“这些经济输入已授权”。
应让可信 ingress 保留已签署原始值，让确定性 effect 路径比较当前输入，
再独立检查 operation/approval 和 provider 事实，不能让模型重构证据。

Visa TAP 可信通信、Poppy 账号/session 权限、Stripe PaymentIntent 状态各有不同
权威来源；本地 binding 成功不把它们合并为单一“支付成功”布尔值。
自动发现生产 key/目录、完整 RFC verifier、HTTP 服务、内容编码适配、业务 schema、
购买同意和远端付款都不在本阶段实现范围。

## 5. 验证边界

[`tests/test_request_binding.py`](../../tests/test_request_binding.py) 新增 24 项方法，
与旧 identity guard 合计 29 项针对性测试通过。覆盖独立固定向量、正文/摘要同时替换、
URI/query/方法/type 改写、缺失/参数化/重复覆盖、严格文本、精确 1 MiB 边界、
不可变性、重复调用及支付 journal 保持 unknown/不得再次 dispatch。
全库 3,904 项单元测试、编译、两个既有演示、67 个本地链接和两个双语可执行示例
均通过；历史测试生成的八个报告文件已恢复，不发布为新 benchmark。
README.md、README.en.md 与 assets/ 相对 `1d9273d` 零差异。
最终提交的远端 CI 与 canonical main 同步仍作为发布后的独立收尾门禁，
不以这些工程结果宣称生产互操作或新模型测量。
