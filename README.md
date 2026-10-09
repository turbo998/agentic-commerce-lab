# Agentic Commerce Lab

面向 Personal Agent 的 Agentic Commerce 研究与可运行模拟实验：聚焦商业场景、AI 职责、授权与支付原生架构。

本仓库将研究 Stripe Sessions 2026、Visa Intelligent Commerce / Trusted Agent Protocol 与公开的 AWS Shopping Concierge 示例，并记录来源、发布日期、适用范围和证据等级。研究内容会区分产品公告、当前文档、协议规范、代码观察和本地模拟，不把演示结果描述为供应商认证或真实支付结算。

## 目标

- 研究 Agent 参与发现、比较、委托、批准、支付、履约和售后的商业价值链。
- 设计把用户同意、交易约束、支付凭证隔离、持久状态和恢复流程放在确定性权限层中的 Personal Agent 架构。
- 提供无需支付账户、真实资金或云资源即可运行的合成购物与支付模拟。
- 将可选模型推理与支付执行隔离；模型只能提出建议和动作请求，不能批准或扩大权限。

默认实验是离线模拟。真实商户支付、账户连接、付费模型调用及云部署均不属于默认能力。请勿输入真实卡号、账户凭证或个人财务数据。

## 研究边界

本仓库只发布原创说明、合成数据和经许可审核的代码；不托管内部材料、客户信息、支付秘密或第三方资料副本。各能力的集成与验证状态会明确标记。

## 状态

研究和模拟 demo 正在建设中。尚未验证的功能会明确标注，不能据此推断生产可用性。

## 公开参考

- [Stripe: Sessions 2026 announcements](https://stripe.com/blog/everything-we-announced-at-sessions-2026)
- [Stripe: Agentic commerce](https://docs.stripe.com/agentic-commerce)
- [Visa: Intelligent Commerce](https://www.visa.com/en-us/solutions/intelligent-commerce)
- [Visa: Trusted Agent Protocol overview](https://developer.visa.com/capabilities/trusted-agent-protocol/overview)
- [AWS AgentCore Shopping Concierge sample](https://github.com/awslabs/agentcore-samples/tree/main/05-blueprints/shopping-concierge-agent)
