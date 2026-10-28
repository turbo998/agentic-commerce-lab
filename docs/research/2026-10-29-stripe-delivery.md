# Stage 1654：验签成功仍不能将未知支付改为成功

[English](2026-10-29-stripe-delivery.en.md) | [当日研究](../../research/daily/2026-10-29.md) |
[Stage 1653 回读边界](2026-10-28-stripe-observation.md)

**核验日期：2026-10-29，北京时间 00:06 起；基线 `6cdefcf`。**
这是 `synthetic` 离线工程参考，不是 Stripe SDK、真实支付接入、模型基准报告、
供应商认证或新的产品发布。README 与 SVG 资产保持不变。

## 1. 一手证据：真实送达与当前业务状态不是同一事实

| 一手资料 | 本轮核验的事实 | 不能推导的结论 |
|---|---|---|
| [Webhook 签名说明](https://docs.stripe.com/events/manage-webhook-endpoints#signature-errors) | 验签需要未修改的原始请求体及正确的 endpoint secret；CLI 转发与配置端点的 secret 不相同 | 重建 JSON 后仍可验签；任意环境的 secret 可混用 |
| [Webhooks](https://docs.stripe.com/webhooks) | 处理事件前验签；snapshot 与 thin event 的处理不同 | 一个校验结果覆盖所有事件格式、账号与业务规则 |
| [Events 工作方式](https://docs.stripe.com/events/how-events-work) | snapshot 在处理时可能已过时；采取行动前应获取最新对象 | 带签名的 `payment_intent.succeeded` 就是当前支付或结算证明 |
| [官方 Python 验签实现，固定提交](https://github.com/stripe/stripe-python/blob/04dc12298d359a709e9ff289094e1a00c9ca666b/stripe/_webhook.py) | HMAC-SHA256 输入为时间戳、点号及 payload；支持多个 `v1` 候选，默认 tolerance 为 300 秒 | 官方实现已承诺对称未来时钟窗口或阻止窗口内重放 |

源码提交时间为 2026-10-27；网页核验时间不是产品发布日期。本轮新增证据仅覆盖
Stripe；Visa TAP 与 Sierra Poppy 的证据与限制仍以
[Stage 1652](2026-10-28-authority-recovery.md) 为准，不声称本轮发现新发布。
HMAC 是共享 secret 下的消息认证，不是消费者同意、银行结算或面向第三方的不可否认性证明。

## 2. 离线资产只返回传输证据，不返回支付结果

[`lab/stripe_delivery.py`](../../lab/stripe_delivery.py) 提供
`verify_stripe_delivery(body, signature_header, endpoint_secret, *, now, tolerance=300)`。
它使用标准库 `hmac`、SHA-256 与 `compare_digest`，不自造密码算法。

- 输入必须是原始 `bytes`。先解析再序列化，即使语义相同，也不能替代原始字节。
- 正确匹配任一 `v1` 候选即可通过，支持轮换期间的多签名；`v0` 等未知 scheme
  不能单独认证消息。所有 header component 必须有非空 key/value。
- **严格本地策略**：恰好一个规范、无前导零的非负时间戳；`v1` 为 64 位小写十六进制；
  可信 `now` 与时间戳在 signed 64-bit 非负范围内；tolerance 为正整数且不超过
  signed 64-bit 上限；布尔值不是整数配置，零不能关闭检查。
- **严格本地时钟策略**：`abs(now - timestamp) <= tolerance`，默认允许前后各 300 秒。
  固定提交的 SDK 是过去时间检查；这里额外拒绝过远的未来时间，不能称为 SDK 等价实现。
- 输出只有 `timestamp`、`payload_sha256` 和 `requires_readback=True`。
  不返回/持久化原始 body、secret 或支付状态，不解析 JSON、不写账本、不发送 HTTP ACK。

正确签名的非 JSON 字节也可通过这个传输层函数；事件 schema 验证必须另做。
相同消息在窗口内再次送达也可以通过；这个函数没有 durable inbox 或事件去重。
摘要不是支付凭证，也不应被无条件作为可公开日志字段。
生产应优先采用维护中的官方 SDK；这里不是完整互操作或安全认证实现。

## 3. 可运行的合成固定向量

以下 secret 明确为合成数据，绝不用于真实端点。固定 HMAC 由独立 .NET 实现计算，
不是仅由被测 Python 路径生成。固定时间和注入的 `now` 只服务离线确定性测试。

```python
from lab.stripe_delivery import verify_stripe_delivery

body = b'{"id":"evt_synthetic"}'
signature = "585651ea0f3c4918ed81ef14a60ffcf0063a442cf6797db445410d1ef4930528"
result = verify_stripe_delivery(
    body, f"t=1700000000,v1={signature}",
    "synthetic-only-not-a-real-secret", now=1700000000,
)
assert result.timestamp == 1700000000
assert result.requires_readback
```

```powershell
python -m unittest tests.test_stripe_delivery tests.test_stripe_observation tests.test_payment_attempts tests.test_checkout -q
```

62 项针对性测试通过，其中 16 项为新增测试方法，覆盖固定向量、字节/空白篡改、
secret 错配、多签名、歧义 header、正负 300 秒边界、301 秒拒绝、错误配置、
窗口内重放限制以及验签后账本仍为 `unknown`、不得再次 dispatch。
这是确定性工程测试计数，不是模型表现、真实支付成功率或性能坐标。

## 4. AI-native 架构：用独立证据推进状态，不让模型补齐证明

建议边界是：原始字节接收与验签 → 独立 schema/账号校验与持久 inbox →
可信 provider 回读与既有绑定检查 → 单调更新支付账本。
**箭头表示责任顺序，不代表本资产已实现整条流水线。**
初始对象关联、时钟同步、端点 secret 管理/轮换、账号/模式隔离、入口大小限制、
持久接收与 ACK、重复/乱序事件、回读失败重试及最终结算都仍属于外部责任。

这把 Well-Architected 的可靠性与信任边界细化为经济副作用不变量，不意味着它缺少
安全指导，也不要求用更多 agent 或微服务取代模块化单体。
签名、去重、业务终态与消费者授权各自有独立的证据和生命周期；模型不能把其中一种
成功推断成其余全部成立。
