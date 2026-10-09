# 来源、证据等级与公开发布资格

**核查截点：2026-10-09。** 链接均为公开来源；产品页面会变更。本文件仅记来源信息与本项目原创总结，不转载第三方源码或私有资料。

## 一手来源与使用范围

| 来源 | 证据等级 / 本文采用内容 | 不作出的推断 |
|---|---|---|
| [Stripe Sessions 2026 发布日公告（2026-04-29）](https://stripe.com/blog/everything-we-announced-at-sessions-2026) | Stripe 发布日对新产品、合作、预览功能和能力的自述 | 每个地区/账户可用、每项已 GA、实际性能收益 |
| [Stripe Agentic Commerce 在线文档](https://docs.stripe.com/agentic-commerce) | 截点时集成路径、协议映射与能力状态；页面称 Agents 为 Private preview | 等同于发布日公告、公开资格保证或任何商户可直接启用 |
| [Visa Intelligent Commerce 官方开发者 overview](https://developer.visa.com/capabilities/visa-intelligent-commerce/overview) | 官方描述的 agent onboarding、agent token、step-up/passkey、授权指令、凭证匹配、guest checkout、VisaNet 商户/金额控制、购买信号 | API 访问资格、地域、定价、实际 GA、未公开的 API 细节 |
| [Visa Intelligent Commerce 商业入口](https://www.visa.com/en-us/solutions/intelligent-commerce) | 官方 portfolio 市场定位；链接至开发者 overview 和 Agentic Sandbox | 开发者 API 访问和商户覆盖承诺 |
| [Visa Agentic Sandbox](https://developer.visaacceptance.com/hello-world/agentic-sandbox.html) | 公开参考链接 | 本项目已访问或验证 sandbox；本项目没有执行它 |
| [Visa Trusted Agent Protocol overview](https://developer.visa.com/capabilities/trusted-agent-protocol/overview) | 官方说明商户/用途特定、限时、防重放/转送签名方向的可信代理识别 | 本文未复述未核对的协议字段；TAP 不等于付款授权 |
| [UCP](https://ucp.dev/) / [ACP](https://www.agenticcommerce.dev/) | 协议网站对开放 commerce checkout/发现工作流的定位 | 已被单一支付网络或 PSP 统一采用 |
| [AP2](https://ap2-protocol.org/) | 协议网站对可验证 payment/checkout mandate 和 agent 支付意图的描述 | AP2 本身清算或结算资金 |
| [MCP](https://modelcontextprotocol.io/) / [A2A](https://a2a-protocol.org/) | 工具上下文/Agent 协作协议的角色 | 身份、用户授权或支付轨道 |
| [MPP](https://mpp.dev/) / [x402](https://x402.org/) | 文档对机器服务通过 HTTP 402 等模式要求支付的定位 | 某个可接受资产一定最终结算，或等同于卡支付 |
| [AWS AgentCore Shopping Concierge sample at commit `3f2d283e7030743feb310e637bf4ff1cdbab5382`](https://github.com/awslabs/agentcore-samples/tree/3f2d283e7030743feb310e637bf4ff1cdbab5382/05-blueprints/shopping-concierge-agent) | 固定 commit README、部署文档和只读代码观察：AgentCore supervisor、shopping/cart 子代理、MCP 购物车工具、DynamoDB 购物车、单独 Visa proxy、mock/真实部署区分 | 已部署/运行/认证；其 mock 或“success”文字就是真实付款 |

## AWS 示例代码观察的准确边界

对固定 commit 只读检查了 `README.md`、`DEPLOYMENT.md`、`concierge_agent/supervisor_agent/agent.py`、`cart_subagent.py`、`mcp_cart_tools/server.py` 和 `local-visa-server/handler.py`。Supervisor 使用 Bedrock Agent 与 AgentCore memory、调用 shopping/cart 子代理；购物车 MCP 暴露了独立的 request-confirmation 与 confirm-purchase 工具；同一仓库另有 Visa proxy 目录，部署指南区分 mock 与需供应商凭证的 Visa 部署选项。代码量较大、示例并非验证目标，本研究不声称对其全量实现做过测试或审计。

工具定义上的 `confirm_purchase(user_id)` 未接收授权 nonce、订单摘要或报价版本作为显式参数；它也不能单独证明调用链整体缺少 UI 用户确认。此观察仅用于论证：**单靠 prompt 说“先确认”不是可验证的交易端授权合同。**

## 发布资格 gate / 清洁室决定

1. **Northstar 源码不具备可确认的公开复用权。** 相关源目录是另一私有/非公开工作区中的未跟踪内容，父仓库无 root LICENSE/COPYING/NOTICE，源文件没有 git provenance。故不能复制、转写、翻译、机械衍生或将其片段移入本公共仓库。此仓库实现基于公开文档中的高层问题，以全新目录、数据模型、代码和文案 clean-room 编写。
2. **Visa 私有 dual-rail mock、ZIP/仓库及本地 Visa 附件禁止进入公共仓库。** 不读取、不复制、不引用其私有细节；公开内容只依赖官方公开 URL，并明确注明其边界。
3. **AWS 样例仅概念参考，不复制样例文件、提示词、UI、基础设施、图表或实现。** 固定 commit 的公开页面标明 Apache-2.0；若将来需要复制任何代码，须先逐文件保留适用许可证/NOTICE、检查依赖与文件来源并进行单独审查。目前没有复制。
4. **本仓库发布物为原创说明、合成产品/用户/余额数据、原创本地模拟与测试。** `.gitignore` 排除运行态数据、依赖、环境变量和日志；没有支付凭证、个人财务数据、云凭证或源工作区路径。明确不部署真实支付、不运行云资源、不进行付费模型调用。
5. 本仓库适用根目录 MIT License。协议名称和商标仅用于描述公开生态；不表示 Visa、Stripe、AWS 或协议维护方背书、认证或合作。

| 输入 | 复用判断 | 本仓库处理 |
|---|---|---|
| Northstar Marketplace 本地代码及其衍生材料 | **Blocked**：权利和来源无法确认 | 不读取或复用代码；只从任务要求提取一般产品问题，独立设计和实现 |
| Visa 私有 dual-rail mock、ZIP、私有仓库和本地附件 | **Blocked**：非公开/未获公开许可 | 不读取、不引用、不复制；VIC/TAP 仅引用可访问的 Visa 官方公开页面 |
| Visa VIC/TAP 官方网页 | 可引用公开事实并链接来源 | 用原创中文总结，并限定公开文档明确描述的范围 |
| AWS AgentCore Shopping Concierge 固定 commit | Apache-2.0；概念参考 | 只记录仓库 README、指南和只读代码观察；没有复制文件或代码 |
| 本仓库离线模拟和合成内容 | 原创内容 | 使用独立代码、测试、商品、用户和余额；采用 MIT 许可证 |
