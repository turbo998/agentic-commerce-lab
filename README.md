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

## 研究与技术资产

| 入口 | 内容 |
|---|---|
| [2026-10-11 每日研究](research/daily/2026-10-11.md) | 今日结论、发布事实纠错、技术资产、证据缺口与日更机制 |
| [协议与产品分层](research/protocols.md) | Visa VIC/TAP/MCP/Toolkit；Stripe ACP/UCP/Suite/SPT/Link/MPP/x402/MCP |
| [Personal Agent 参考架构](research/architecture.md) | 信任边界、审批、幂等、异步支付恢复与非功能取舍 |
| [Agent 使用场景](research/use-cases.md) | 零售、补货、预订、B2B 开票、API 付费、售后与财务洞察 |
| [官方来源注册表](research/sources.json) | 来源、验证日期、发布日期、版本与证据边界 |
| [离线 checkout 实验](lab/checkout.py) | 合成报价授权、购物车绑定、单次消费、持久幂等及并发保护 |

## 本地运行

要求 Python 3.12+；只使用标准库，无需支付账户、模型密钥、联网或安装依赖：

```powershell
python -m lab.demo
python -m unittest discover -s tests -v
```

demo 使用自动清理的临时 SQLite 数据库，输出 `status=simulated`。可信调用方预置批准与时钟；生产需要独立用户认证/同意与支付 broker。此实验**不是** ACP/AP2/TAP/SPT 协议实现、真实支付或认证结果。

## 每日研究

已有 Copilot App 自动化每日 22:00 执行研究，已补充官方来源核验、检查未合并分支、按日期增量研究、相关测试、提交推送与 PR 的要求。日更依赖本机 App/执行主机可用；GitHub Actions 目前仅执行 CI，不负责生成研究。

需要联网的公开来源跟踪命令：

```powershell
python -m scripts.source_monitor
```

生成 `research/daily/YYYY-MM-DD-sources.json`（北京时间），只记录 URL、哈希及错误，不保存第三方全文。任何抓取失败返回非零退出码；同日重跑仍对比此前日期的最后成功结果。HTML 导航或文案变化也可能改变哈希，**不能据此判断产品发布或标准升级**。专家研究写入同日 `.md`，将最新官方正文与公告日期、准入限制分开。

研究上传当前会话分支并通过 PR 汇总；未合并前不代表默认分支已更新。尚未验证的能力会明确标注，不能据此推断生产可用性。

## 公开参考

- [Stripe: Sessions 2026 announcements](https://stripe.com/blog/everything-we-announced-at-sessions-2026)
- [Stripe: Agentic commerce](https://docs.stripe.com/agentic-commerce)
- [Visa: Intelligent Commerce](https://www.visa.com/en-us/solutions/intelligent-commerce)
- [Visa: Trusted Agent Protocol overview](https://developer.visa.com/capabilities/trusted-agent-protocol/overview)
- [AWS AgentCore Shopping Concierge sample](https://github.com/awslabs/agentcore-samples/tree/main/05-blueprints/shopping-concierge-agent)
