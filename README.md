# Agentic Commerce Lab

面向 Personal Agent 的 Agentic Commerce 研究与离线模拟实验室。项目聚焦商业价值链、AI 职责边界、用户授权与支付原生架构，研究 Stripe Agentic Commerce / Sessions 2026、Visa Intelligent Commerce / Trusted Agent Protocol，以及公开的 AWS Shopping Concierge 示例。

> **安全边界：** Demo 仅处理合成数据，在本地模拟授权、扣款、退款和对账；不调用支付网络、不连接账户、不持有支付凭证、不启动云资源。可选 LLM 尚未接入。请勿输入真实卡号、凭证或个人财务数据。

## 快速开始

需要 Node.js 22 或更高版本。无第三方运行依赖。

```sh
npm ci
npm run check
npm run test:e2e
npm start
```

打开 <http://127.0.0.1:4173>。页面带有醒目的 `SIMULATED / OFFLINE` 标记。运行状态写入 `data/state.json`，该文件已排除在版本控制之外；点击重置可恢复合成初始余额。

## Demo 能力

- 周末多商户购物、旅行预订和按次付费信息服务的合成目录。
- 用户明确确认后，创建绑定用户、任务、商户、商品明细、精确金额/币种、报价版本和有效期的授权指令。
- 先创建待执行授权，再次明确批准执行；授权可在执行前撤销。确定性权限层验证授权与余额，模型/代理建议不会创建授权，也无法扩大预算或批准付款。
- Agent 任务入口由**确定性离线脚本**生成结构化报价建议（非真实推理）；受限 action API 仅能请求已列出的报价。提供仅供测试注入的 planner mock contract，不配置模型 SDK、密钥或默认网络调用。
- 旅行指南先返回本地 HTTP 402-shaped challenge，批准后通过幂等 retry 返回合成内容与收据；不是完整 MPP/x402 或网络结算。
- USD、HKD、USDC 分开记账，不隐式换汇；单调状态机、幂等键、未知结果对账、重启恢复与累计退款上限。
- 模拟收据、商户履约状态、退款、失败后人工重试/补偿、离线事件记录和 23 个分类混合评估向量。

## 研究

- [Agentic Commerce 研究报告（中文）](docs/research.md)：商业场景、价值链、AI 边界、协议地图、参考架构、Visa 生命周期和供应商状态区分。
- [Stripe Sessions 2026 专题研究](docs/research/stripe-sessions-2026.md)：ACS/Connect、Link Agent Wallet、SPT、MPP/x402、Issuing、Metronome/Tempo/Radar、Projects/Treasury 的发布日与当前文档状态、费用/资格边界及官方来源。
- [Copilot Studio connector 与本地旅程](docs/copilot-studio-connector.md)：typed API 契约、合成角色登录、独立人工批准、两条 walkthrough 和真实租户接入门槛。
- [实现、状态机与运行手册](docs/architecture.md)：架构和模拟边界、故障场景、API 和测试说明。
- [来源与发布资格](docs/sources.md)：一手来源、证据等级、许可证与清洁室决策。

## 验收证据

本工作树最新实现运行 `npm run check` 23/23 通过，包含 23 个固定混合 Agent 向量（正常建议完成率 100%、正确拒绝率 100%、误拒绝 0、重复副作用 0、恢复完整性通过、未授权付款 0）；`npm run test:e2e` 2/2 通过；`npm audit --omit=dev` 为 0 vulnerabilities。独立 loopback 浏览器走查实际完成结构化 USDC task limit、typed HTTP 402 challenge、challenge-bound 人工批准、retry、模拟 receipt/resource delivery，并确认审批页从 pending 更新为 completed。自动验收还覆盖并发额度争用、10 次相同请求/事件/履约/退款重放、30 次对账、服务重启恢复、跨 owner/tenant 拒绝和履约补偿处理。Stripe 专题仅为公开文档研究；未执行 sandbox、live provider、真实支付、云部署或计费模型调用。

## 现状与非目标

这是研究原型，不是可部署的支付产品，不表示 Stripe、Visa、AWS 或任何协议组织认证或背书。本地模拟不验证供应商集成，也不代表真实授权、清算或结算。Demo 没有生产鉴权、并发数据库或多租户部署设计。任何未来真实支付适配器都必须另行进行安全、合规和供应商环境验证，不能绕过确定性权限层。
