# Stage 1665：活动密钥集合改变验签，不改变 Event 身份

[English](2026-10-29-stripe-secret-rotation.en.md) |
[验签资产](../../lab/stripe_delivery.py) |
[Inbox](../../lab/stripe_inbox.py) |
[测试](../../tests/test_stripe_secret_rotation.py)

## 结论与范围

既有 verifier 已支持用一个可信 endpoint secret 检查多个 `v1` 候选，已经能够处理
Stripe 轮换重叠期的多签名投递；这不是协议缺陷。本轮增加本地配置表达：
`endpoint_secret` 继续接受字符串，也可接受**非空、每项均为非空白字符串的 tuple**，
并贯通 `StripeEventInbox.record`，不新建 facade 或数据库 schema。
匹配任何签名前先验证全部配置项；即使首项能够验签，非法末项仍必须报错。

所有项必须属于**同一可信 endpoint/account/mode 的当前活动密钥**。
adapter 在请求外选定这个快照并负责退役；正文、header、agent 都不能据此选择
密钥、端点或账户。该 primitive 无法认证配置快照的来源。
拒绝可变 list、空 tuple、嵌套值和非字符串成员；重复的有效字符串只是冗余。

## 一手证据：2026-10-29 04:01 BJT 核验

- [Stripe webhooks](https://docs.stripe.com/webhooks) 的 **Roll endpoint signing
  secrets periodically** / **Verify the signature**：可立即退役或延迟最多 24 小时；
  重叠期多个 secret 活动，每个 secret 生成一个签名。不同 endpoint、test/live
  的 secret 分离。
- [Manage webhook endpoints](https://docs.stripe.com/events/manage-webhook-endpoints)
  再次确认轮换语义，并说明 CLI 转发和 Dashboard endpoint secret 不同；
  旧 `/webhooks/signature` 当前重定向到该管理文档。
- 两者要求原始、未修改正文验签；真实集成推荐官方库。本资产是狭窄离线参考，
  不替代完整 SDK；tuple 是本地 API 扩展，不宣称 SDK 也接受此配置类型。

这些是访问日观察的可变文档页面，不是 Stripe 新产品发布或新协议版本公告。
本轮未核验 Visa/Sierra 新发布。

## 同一验签策略，不同控制平面

两种配置复用同一 parser、`timestamp + "." + body` HMAC-SHA256 输入。
每个尝试的 secret 只计算一次 HMAC，用 `compare_digest` 对比已解析的 `v1`
候选，任一匹配即可；不承诺不同密钥顺序的总耗时恒定。
即使伴随有效签名，畸形 `v1` 仍拒绝。不可变原始字节、规范且唯一 timestamp、
严格正 tolerance、对称且边界包含的时间策略均不变。

| 边界 | 新增或仍由外部负责的事项 |
|---|---|
| 密钥重叠 | 可信配置可以包含多个活动 endpoint secret。 |
| 密钥退役 | 每个 verifier 的可信快照须移除旧 key；无远端状态查询或隐式计时器。 |
| 投递 freshness | 既有默认 tolerance 仍为 300 秒，不是 24 小时；不保证防重放。 |
| 持久回执 | tenant/endpoint/account/mode/Event ID 身份不因 secret 或签名时间改变。 |
| Provider 结果 | receipt 是待认证 readback 的 hint，不是付款成功。 |
| Dispatch/approval | 不新增 reservation、消费者同意、worker 权限或付款发送。 |

**远端到期不会删除本地仍保留的 secret。** 若已泄露旧 key 仍在配置中，它仍可
生成被接受的 fresh HMAC。操作者必须发布并部署正确活动集合；本实验不管理密钥、
核验远端到期或保证所有 verifier 退役收敛。禁止把 CLI、其他 endpoint/account/mode
的 secret 混进全局 fallback keyring。

验签仍先于 JSON、数据库连接和 duplicate 查询。仅旧 key 签名的投递在退役后必须
拒绝，即使 Event 已存在；新 key 重签同一合法 Event 则仍返回首次 receipt，
不复活 handled 工作。thin event、Connect、organization context 继续不在该 snapshot
inbox 的支持范围内。

## 离线可执行示例

仅 synthetic fixture：无网络、真实密钥、端点注册或付款。下方 `except` 仅断言
预期拒绝；生产场景中 storage/verifier 异常应传播给显式 ingress/ACK 策略。

```python
import hashlib
import hmac
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from lab.stripe_delivery import StripeDeliveryError
from lab.stripe_inbox import StripeEventInbox, StripeInboxScope

now = 1700000000
old, new = "synthetic-only-overlap-old", "synthetic-only-overlap-new"
body = json.dumps({
    "id": "evt_synthetic", "object": "event", "livemode": False,
    "type": "payment_intent.succeeded",
    "data": {"object": {
        "id": "pi_synthetic", "object": "payment_intent", "livemode": False,
    }},
}).encode()

def signed(secret):
    digest = hmac.new(secret.encode(), str(now).encode() + b"." + body, hashlib.sha256)
    return f"t={now},v1={digest.hexdigest()}"

with TemporaryDirectory() as directory:
    inbox = StripeEventInbox(Path(directory) / "inbox.sqlite3")
    scope = StripeInboxScope("synthetic-tenant", "synthetic-endpoint", "acct_synthetic", False)
    first = inbox.record(scope, body, signed(old), (old, new), now=now)
    again = inbox.record(scope, body, signed(new), (new,), now=now)
    assert first.first_seen and not again.first_seen
    assert again.receipt == first.receipt and again.receipt.requires_readback
    try:
        inbox.record(scope, body, signed(old), (new,), now=now)
    except StripeDeliveryError:
        pass
    else:
        raise AssertionError("A retired-only key must not bypass verification on a duplicate.")
    assert len(inbox.pending(scope)) == 1
    print({"synthetic": True, "receipt_count": 1, "requires_readback": True})
```

## 架构含义与验证

Well-Architected 是质量与取舍框架，不是强制 Web 三层拓扑；轮换、secret 分离、
webhook 验签也不是 AI 新发明。AI-native commerce 的 planner 重试、工具生成 payload、
独立重启 worker 不能从对话重建可信活动 key 集合，或把轮换签名当消费者授权续期。
配置、传输证据、回执协调和经济权限需要分平面治理。与
[商户请求绑定](2026-10-29-request-binding.md) 和
[Poppy 锁后 assertion 准入](2026-10-29-poppy-admission-clock.md) 互补，但三者的
signature、identity、secret、replay scope 不可互换。

154 项针对性测试通过，含 26 项新增方法：key/signature 顺序、全部配置验证、
每个尝试 key 一次 HMAC、精确时间/正文、退役 duplicate 在 storage 前拒绝、
并发/重启去重、scope/最少存储及无付款/dispatch 权限。这是 synthetic 工程 fixture，
不是模型 benchmark。全库 4,068 项单测、编译、两个既有演示、119 个本地链接及
两个相同双语可执行示例通过。十个历史生成报告文件已恢复，没有报告内容进入暂存。
README/assets 相对 `1d9273d` 零差异；最终 SHA CI/canonical 同步保留为发布后门禁，
不作为 provider 或付款证据。
