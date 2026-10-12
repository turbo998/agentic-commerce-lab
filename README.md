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
- 按旅程、币种和单报价整数金额筛选预算内候选；服务器计算 `OVER_BUDGET` / `CURRENCY_MISMATCH` 排除说明、精确差额和相对上限余量，无合格报价返回 `no_action`。候选不是获准购物车，累计支出、预留与批准继续由权限层检查。Injected planner 接收请求副本，不能更改服务器保存的预算/范围。
- 旅行指南先返回本地 HTTP 402-shaped challenge，批准后通过幂等 retry 返回合成内容与收据；不是完整 MPP/x402 或网络结算。
- USD、HKD、USDC 分开记账，不隐式换汇；单调状态机、幂等键、未知结果对账、重启恢复与累计退款上限。
- 模拟收据、商户履约状态、退款、失败后人工重试/补偿、离线事件记录和 23 个分类混合评估向量。

## 研究

### Copilot / HVE 合作伙伴工程分享（60 分钟）

以尚未合并的 [PR #1](https://github.com/turbo998/agentic-commerce-lab/pull/1) 为完整运行基线、[PR #4](https://github.com/turbo998/agentic-commerce-lab/pull/4) 为只读研究对照。此分支交付新增预算推荐及分享包，不自动合并现有 PR，不重建空 main。

```powershell
npm run check
npm run test:e2e
npm run demo
```

专用 Demo：<http://127.0.0.1:4187>；HVE 深度 H5：<http://127.0.0.1:4187/hve-report.html>。`npm run demo` **仅使用 `data/workshop-state.json`**，不影响原 `npm start` 的 `data/state.json`。服务只绑定 loopback；重置仅在专用实例操作，别删除整个 data。H5 的正文、目录、来源和 CSS/JS 均本地可读，无 CDN，保留原 CSP；交互支持全文章节检索、主题、复制反馈、完整打印及键盘导航。

- [详细中文大纲](docs/workshops/copilot-hve-commerce/outline.md)：24 单元，连续 60 分钟，含讲者展开、图示、事实来源、Demo 转场和 Q&A，供 Cowork 制作；不含 PPT。
- [可复现操作手册](docs/workshops/copilot-hve-commerce/demo-runbook.md)：干净状态、业务场景、开始/完成检查点、RPI 输入、VS Code 预检和失败备用。
- [来源登记](docs/workshops/copilot-hve-commerce/sources.json)：15 研究问题、26 网页引用及额外 Commerce/执行证据；官方说明、源码合同、实际运行与建议分别标识。
- [真实阶段预演](docs/workshops/copilot-hve-commerce/evidence/rpi-execution.md)、[host/skill 哈希](docs/workshops/copilot-hve-commerce/evidence/host.json)、[业务浏览器断言](docs/workshops/copilot-hve-commerce/evidence/browser-commerce.json)、[H5 浏览器断言](docs/workshops/copilot-hve-commerce/evidence/browser-report.json)。

实际开发使用 **Copilot App/CLI 1.0.94-3 + 本机 user-scoped RPI phase skills**，Research/Plan/critique 在应用编辑前执行。固定 HVE `49dfb738…` 是源码研究基准，不是已执行 skill revision；本机来源 revision 未确定，以哈希标识。VS Code Chat、当前 upstream RPI Agent wrapper 和 HVE Builder 未执行，教学路径待主讲人复现。业务始终 scripted-offline，未调用模型或支付供应商，不声明量化提效。

新增 focused 12/12、完整 check（含三项材料/静态边界检查）38/38、原 HTTP e2e 2/2；实际 Playwright 业务 13 项、H5 35 项断言通过。复制已验证真实 API 参数及失败降级，但此浏览器 host 写入成功后读回为空，**未声称 OS 剪贴板 round-trip 通过**。打印验证含真实 Chromium PDF 渲染、3 个折叠代码示例展开与恢复；不是实体打印机或全面 WCAG 合规认证。

- [Agentic Commerce 研究报告（中文）](docs/research.md)：商业场景、价值链、AI 边界、协议地图、参考架构、Visa 生命周期和供应商状态区分。
- [Stripe Sessions 2026 专题研究](docs/research/stripe-sessions-2026.md)：ACS/Connect、Link Agent Wallet、SPT、MPP/x402、Issuing、Metronome/Tempo/Radar、Projects/Treasury 的发布日与当前文档状态、费用/资格边界及官方来源。
- [Copilot Studio connector 与本地旅程](docs/copilot-studio-connector.md)：typed API 契约、合成角色登录、独立人工批准、两条 walkthrough 和真实租户接入门槛。
- [实现、状态机与运行手册](docs/architecture.md)：架构和模拟边界、故障场景、API 和测试说明。
- [来源与发布资格](docs/sources.md)：一手来源、证据等级、许可证与清洁室决策。

## 验收证据

PR #1 基线的历史验收记录：`npm run check` 24/24，包含 23 个固定混合 Agent 向量（正常建议完成率 100%、正确拒绝率 100%、误拒绝 0、重复副作用 0、恢复完整性通过、未授权付款 0）；`npm run test:e2e` 2/2；原记录中 `npm audit --omit=dev` 为 0 vulnerabilities，并已有独立 loopback 浏览器 USDC/HTTP402/人工批准/retry/receipt走查。**本分享增量的最新实际检查与浏览器证据见上方 HVE 分享包，不把基线历史 audit/浏览器记录当成本次新执行。**自动验收继续覆盖并发额度争用、请求/事件/履约/退款重放、对账、服务重启恢复、旧状态升级、跨 owner/tenant 拒绝和履约补偿。Stripe 专题仅为公开文档研究；未执行 sandbox、live provider、真实支付、云部署或计费模型调用。

## 现状与非目标

这是研究原型，不是可部署的支付产品，不表示 Stripe、Visa、AWS 或任何协议组织认证或背书。本地模拟不验证供应商集成，也不代表真实授权、清算或结算。Demo 没有生产鉴权、并发数据库或多租户部署设计。任何未来真实支付适配器都必须另行进行安全、合规和供应商环境验证，不能绕过确定性权限层。
