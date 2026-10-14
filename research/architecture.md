# Personal Agent 参考架构

日期：2026-10-11。**方案设计，不是已部署基础设施或已获供应商认证的实现。** 图使用 Mermaid（适合 GitHub 内联预览）；默认云无关，避免在未确认区域、预算与数据驻留前指定云产品。

## Personal Agent Commerce Architecture

```mermaid
flowchart TB
    user["User / approval UI"]
    subgraph agentzone["Agent application trust boundary"]
        planner["LLM planner - proposes only"]
        tools["Tool router - MCP / optional A2A"]
    end
    subgraph controlzone["Deterministic execution boundary"]
        policy["Consent and mandate service"]
        orchestrator["Checkout state machine"]
        journal[("Orders / idempotency / outbox")]
        evidence[("Redacted audit evidence")]
        vault["Credential broker - no model access"]
    end
    subgraph merchantzone["Merchant boundary"]
        gate["Gateway - optional TAP verification"]
        commerce["ACP / UCP adapter"]
        catalog["Catalog / tax / inventory / fulfillment"]
    end
    provider["PSP / wallet / network"]
    user --> planner
    user -->|approve final quote| policy
    planner --> tools
    tools -->|proposed actions| orchestrator
    orchestrator -->|validate authority| policy
    orchestrator --> journal
    orchestrator --> evidence
    orchestrator -->|revalidate final cart| commerce
    tools -. optional browse .-> gate
    gate --> commerce
    commerce --> catalog
    orchestrator -->|scoped credential request| vault
    vault --> provider
    commerce -->|merchant charges scoped credential| provider
    provider -->|signed status / webhook| orchestrator
    catalog -->|order events| orchestrator
```

### Legend

实线表示必要的数据或执行依赖；虚线表示可选浏览路径。框为逻辑信任边界，不表示网络配置已经部署。数据库形状代表持久存储。凭证经过专用 broker，图中不表示其流经 LLM。

### Key Relationships

Agent 只能请求动作，不能调用批准接口、扩大预算或修改已批准对象。最终金额包括税费、运费及费用；库存/报价变动重新批准。MCP 是工具边界，ACP/UCP 是商户商业接口，TAP 是可选请求信任机制，PSP/network 才执行实际资金授权。

## 状态与失败恢复

建议状态：`discovered → quoted → approval_required → approved → credential_ready → payment_pending → paid → fulfillment_pending → fulfilled`；异常状态包括 `expired`、`revoked`、`declined`、`unknown`、`refund_pending`。**`unknown` 不能转成成功，也不能通过重新付款“恢复”。**

| 失败点 | 正确处理 | 不能做什么 |
|---|---|---|
| 批准后价格/税费/运费或收款方变化 | 校验最终 cart binding，重新批准 | 用用户笼统“帮我买”覆盖最终价格 |
| 支付超时但可能已扣款 | 用既有 PaymentIntent/transaction hash 查询与对账；保留相同幂等键 | 换 key 重试产生第二笔扣款 |
| webhook 重复/乱序 | 验签、event 去重、单调状态/版本条件写 | 只信网页提示或模型总结 |
| 支付成功、库存/履约失败 | 订单 saga，补偿/退款等待确认；告知用户 | 假装“全部回滚”，把退款请求视为到账 |
| 用户撤销与执行并发 | 最终执行点校验撤销，事务化消耗授权；已支付结果保留 | 删除审计记录或把已扣款当作未执行 |
| 多商户购物 | 按商户拆分凭证、子订单与预算；定义部分成功策略 | 假定跨 PSP 有原子事务 |
| 链上结算后记账失败 | 保存链上 proof，按 hash 重放记账与对账 | 再次生成链上转账 |
| 来源/工具提示注入 | 外部文本作为数据；allowlist tool/merchant/schema；确定性审批 | 让商品描述改写工具权限 |

## 非功能目标与取舍（建议，不是测量值）

| 维度 | 原型边界 / 生产验收方向 |
|---|---|
| 可靠性 | 原型单机 SQLite、单次授权原子消耗；生产使用事务存储/outbox、PSP 对账、恢复演练、明确 RTO/RPO |
| 安全 | 原型仅合成数据；生产独立认证与同意 UI、凭证 broker、轮换、最小权限、TLS、日志脱敏及支付合规评估 |
| 成本 | 无付费模型和真实支付；生产测量每次成功订单的推理、工具、支付、风控成本，设置任务/预算上限 |
| 运维 | 明确错误、持久回执、source provenance、CI；生产增加 trace ID、webhook 验签与告警、密钥迁移 runbook |
| 性能 | 先保证正确性；生产分别测量报价 p95、批准等待、支付确认时长、峰值并发，不把人工等待算作网关延迟 |

先从模块化单体 + 异步订单事件切入，而不是为了“多 Agent”默认微服务。独立凭证边界、版本化商业 adapter 与可替换 PSP 是演进点；模型可切换不能替代确定性的权限层。

## 本仓库资产和设计的映射

`lab/checkout.py` 只实现**已批准最终购物车的单次、离线执行**：商户/币种/金额/购物车绑定、到期/撤销、事务化消耗、持久 receipt 与幂等重试。批准与时钟在测试中由可信调用方提供；没有用户认证/Passkey、数字签名、网络支付、webhook、库存、退款或 outbox。

不能把 SQLite 的本地原子性外推成“外部扣款与订单原子提交”。生产 PSP adapter 必须先设计 `payment_pending/unknown` 和对账恢复；本资产不是 ACP/AP2/TAP/SPT wire-format 实现或兼容性测试。

来源与产品边界见 [协议研究](protocols.md)，场景与验收见 [Agent 使用场景](use-cases.md)。

## 2026-10-12 增量：WAF 是评估框架，不是三层模板

[今日研究](daily/2026-10-12.md)对照官方 WAF AI application design：其已包含 AI 五层、确定性编排/Agent 协作、策略执行和持久状态。Agentic Commerce 需要在此基础上明确每笔交易的消费者授权、credential 隔离、经济副作用状态与对账证据，而不是用更多 Agent 取代确定性执行层。逻辑信任边界不强制微服务；先复用模块化单体，再按真实隔离/扩缩容需求拆分。

新增 `lab/mcp_migration.py` 仅检查 Stripe MCP 认证类别元数据和日期期限，不验证云身份、消费者同意或任何实际权限；它映射本架构的运维/演进职责，不是新增支付能力。

## 2026-10-13 增量：发现、兼容、授权、结果四个独立门槛

[今日研究](daily/2026-10-13.md)补强商业 adapter 入口：发现宣告 → 可执行能力交集 → 消费者最终报价授权 → provider 可信结果。不能从发现到付款直接跳步。版本匹配、受支持 instrument 和卡 tokenization 的环境/关系前置条件只构成接入候选；它们不证明 schema 来源可信、客户已同意、账号可用或付款成功。

`lab/ucp_preflight.py` 是无网络、无凭证的**合成元数据预检**。它拒绝未审阅版本、缺失双方宣告、Stripe handler 下的 Link/Google Pay completion；card 和 Apple Pay 返回不同 credential path，且所有输出 `payment_authorized=false`。本地保守的版本白名单是研究边界，不是供应商兼容矩阵。没有将它连接为现有 checkout 的批准来源，没有新增 tokenize 或付款工具。

Stripe 的自动更新 skills/plugin 改变的是开发指导面，不是交易授权来源。应记录实际加载的版本/revision，并对可执行 tool/schema 的变化做回归；供应商 skill 的反馈建议不能自动获得上传业务资料的权限。可复用的逻辑分层仍可在模块化单体中实现，不需要再造“第六层”或默认拆成多 Agent 微服务。

## 2026-10-14 增量：可解析、可执行、可授权必须分别成立

[今日研究](daily/2026-10-14.md)中的 UCP 官方修复表明：开放的基础 capability schema 允许额外字段，基础验证通过不意味着 fulfillment/AP2 等 extension 内容有效。生产商业 adapter 应分别验证已协商的 capability、extension composed schemas、方向/操作和语义约束；AP2 字符串符合格式也不等于签名、issuer、audience、有效期及最终报价绑定已验证。未知扩展隔离或显式拒绝，不能凭模型解释提升为可信条款。

API 文档表可能漏掉定义在 `securitySchemes` / `security` 或 content maps 中的字段。生成客户端和集成契约应读取固定版本的完整 OpenAPI，不靠截图、字段表或 Agent 的“参数齐全”判断认证是否必需。已有 `lab/ucp_preflight.py` 只做合成版本/instrument/环境声明检查，没有因此获得 wire-format 或 cryptographic conformance。

AI Native 的核心区别是**模型可变的行动空间与不可随意扩大、可追溯的经济权限之间的隔离**，不是推翻 WAF。建议保留 WAF 的可靠性、安全、成本、运维和性能取舍，增补领域不变量：消费者批准绑定最终报价；副作用总额不超过任务预算；`unknown` 不许新扣款；退款请求与确认到账分开；Agent 角色不能批准自己提出的动作。普通三层或模块化单体也可承载这些逻辑边界，不必默认采用多 Agent 或微服务。

新监测资产仅改善**证据/规则变更的运维闭环**：获取成功 → 固定语法选定事实 → 人工审阅 → 显式规则变更 → 回归。`policy_change=unchanged` 不等于业务授权仍有效；`unknown` 不进入自动执行路径。源码、tool schema、prompt/model、商业协议、handler、preview API、资格/地区和客户授权均需独立版本/状态记录。模型 failover 可以更换推理服务，但不能自动换付款凭证、收款方或提高工具权限。

**Sierra 与 Poppy `v0.1` 对 AI-Native 架构的进一步补充**：
- **双轨会话令牌与双向域名防伪**：Poppy `v0.1` 要求发现文档 `auth.issuer` 与 OAuth metadata `poppy_domains` 双向绑定；OpenAPI/会话/Operations 必须校验请求绑定的 `DPoP` 证明（防重放 `jti`），而 MCP 通道必须使用绑定单一 `resource` 的 `Bearer` 令牌，并根据登录方式（`direct` / `device` / `mediated`）限制最大可授予 scope。
- **四层纵深防御与两阶段 `operations` 修订确认**：Sierra 的实践证明自然语言 Rules 与 Supervisors 仍属概率控制，涉及账户修改、换货、退款或支付的工具必须具备第 4 层确定性护栏（未鉴权不暴露修改工具、单会话锁定单客户账户、待发货订单仅允许一次修改），并配合 Poppy `operations` v1：工具调用仅生成带不可变 `revision` 的 `proposed` 操作，仅由独立确认端点针对最新 `revision` 幂等执行（对话消息绝不触发确认）。
- **PCI 支付旁路与目标状态哈希评测**：第一方 Agent 收款（Sierra Payments）将支付信息采集切出 LLM，由服务端预定义序列直传 Stripe；而评测准则（$\tau^2/\tau^3$-bench `reward_basis=["DB","COMMUNICATE"]`）以最终确定性业务数据库状态哈希为准，允许推理探索路径变化但严守终态不变量。新增离线资产 `lab/poppy_guard.py` 实现了上述 Poppy `v0.1` 发现/令牌校验与 Sierra/$\tau^3$-bench 零售售后确定性护栏。
