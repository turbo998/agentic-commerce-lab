# Agentic Commerce Lab

面向 Personal Agent 的 Agentic Commerce 研究与可运行模拟实验：聚焦商业场景、AI 职责、授权与支付原生架构。

本仓库研究 Stripe Sessions 2026、Agentic Commerce Suite / ACP / SPT / Link / MPP、Visa Intelligent Commerce / Trusted Agent Protocol / Intelligent Commerce Connect，并对照 UCP、AP2 与 Agent 工具框架，记录来源、发布日期、适用范围和证据类型。研究内容区分产品公告、当前文档、协议规范、代码观察和本地模拟，不把演示结果描述为供应商认证或真实支付结算。

## 目标

- 研究 Agent 参与发现、比较、委托、批准、支付、履约和售后的商业价值链。
- 设计把用户同意、交易约束、支付凭证隔离、持久状态和恢复流程放在确定性权限层中的 Personal Agent 架构。
- 提供无需支付账户、真实资金或云资源即可运行的合成购物与支付模拟。
- 将可选模型推理与支付执行隔离；模型只能提出建议和动作请求，不能批准或扩大权限。

默认实验是离线模拟。真实商户支付、账户连接、付费模型调用及云部署均不属于默认能力。请勿输入真实卡号、账户凭证或个人财务数据。

## 研究边界

本仓库只发布原创说明、合成数据和经许可审核的代码；不托管内部材料、客户信息、支付秘密或第三方资料副本。各能力的集成与验证状态会明确标记。

## 状态

已提供首日原创研究、架构/协议/场景文档、离线 SQLite 授权与 checkout 实验，以及每日官方资料监测流水线。尚未连接真实支付或执行厂商协议集成；自动监测不是每日深度研究代理。

## 研究与资产导航

| 内容 | 入口 |
| --- | --- |
| 每日研究成果 | [2026-10-10：Visa/Stripe 架构、发布与协议](research/daily/2026-10-10.md) |
| 可追溯官方来源 | [来源登记与版本锚点](research/sources.json) |
| 技术架构 | [模块、信任边界、状态与恢复](docs/architecture.md) |
| 协议和框架 | [产品/协议决策矩阵](docs/protocols.md) |
| Agent 使用场景 | [场景与离线实验验收](docs/scenarios.md) |
| 每日流程 | [监测、研究、资产增量与 GitHub 发布](docs/research-operations.md) |

## 快速运行

Python 3.12，仅使用标准库，无需支付账户、模型密钥或安装依赖。从仓库根目录运行：

```powershell
python -m lab.commerce
python -m unittest discover -s tests -v
python -m scripts.daily_monitor --date 2026-10-10
```

实验输出明确为 `offline_simulation`，验证 merchant/商品/金额/币种/期限约束、批准后的 quote 绑定、撤销、单次授权消费和持久幂等。公开来源监测需要网络访问，只存 hash/status，失败返回非零；不保存网页副本或推断新发布。

应用内已有每日 **22:00** 的自动研究任务，本次产出由该任务执行。GitHub Actions 补充监测在默认分支启用后每日约北京时间 **08:20** 生成观察 artifact 并尝试创建审核 PR，不自动合并；当前仓库限制 Actions 创建 PR。工作分支上的 workflow 尚不能按 cron 调度，详见[运行指南](docs/research-operations.md)。

## 公开参考

- [Stripe: Sessions 2026 announcements](https://stripe.com/blog/everything-we-announced-at-sessions-2026)
- [Stripe: Agentic commerce](https://docs.stripe.com/agentic-commerce)
- [Visa: Intelligent Commerce](https://www.visa.com/en-us/solutions/intelligent-commerce)
- [Visa: Trusted Agent Protocol overview](https://developer.visa.com/capabilities/trusted-agent-protocol/overview)
- [AWS AgentCore Shopping Concierge sample](https://github.com/awslabs/agentcore-samples/tree/main/05-blueprints/shopping-concierge-agent)

AWS 示例仅作为后续框架研究参考，本次未执行或评估。研究由 AI 辅助编写，结合公开官方资料；涉及生产支付、法律责任或产品承诺时需人工复核。
