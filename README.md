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
| [2026-10-13 每日研究](research/daily/2026-10-13.md) | 官方 skills 增量、可执行能力边界、UCP 离线预检及 MCP 18 日迁移窗口 |
| [2026-10-12 每日研究](research/daily/2026-10-12.md) | 官方证据增量、AI Native 与 WAF 辩证比较、UCP handler 边界及 MCP 迁移盘点 |
| [2026-10-11 研究基线](research/daily/2026-10-11.md) | 发布事实纠错、已有技术资产、证据缺口与日更机制 |
| [协议与产品分层](research/protocols.md) | Visa VIC/TAP/MCP/Toolkit；Stripe ACP/UCP/Suite/SPT/Link/MPP/x402/MCP |
| [Personal Agent 参考架构](research/architecture.md) | 信任边界、审批、幂等、异步支付恢复与非功能取舍 |
| [Agent 使用场景](research/use-cases.md) | 零售、补货、预订、B2B 开票、API 付费、售后与财务洞察 |
| [官方来源注册表](research/sources.json) | 来源、验证日期、发布日期、版本与证据边界 |
| [离线 checkout 实验](lab/checkout.py) | 合成报价授权、购物车绑定、单次消费、持久幂等及并发保护 |
| [离线 MCP 迁移盘点](lab/mcp_migration.py) | Stripe MCP 2026-10-31 auth 类别期限检查；只接受无密钥元数据，不验证账户 |
| [离线 UCP handler 预检](lab/ucp_preflight.py) | 版本/宣告 instrument/card tokenize 前置条件检查；兼容候选不等于支付授权 |

## 本地运行

要求 Python 3.12+；只使用标准库，无需支付账户、模型密钥、联网或安装依赖：

```powershell
python -m lab.demo
python -m unittest discover -s tests -v
```

demo 使用自动清理的临时 SQLite 数据库，输出 `status=simulated`。可信调用方预置批准与时钟；生产需要独立用户认证/同意与支付 broker。此实验**不是** ACP/AP2/TAP/SPT 协议实现、真实支付或认证结果。

### Stripe MCP 迁移盘点（不读取密钥）

```powershell
python -m lab.mcp_migration --as-of 2026-10-13
python -m lab.mcp_migration --as-of 2026-10-31
```

默认读取 [合成客户端清单](lab/mcp_inventory.example.json)；`--inventory` 可指定仅含 alias、环境和 auth 类别的 JSON。禁止填入实际 key、账户 ID 或个人数据；不传 `--as-of` 时使用北京时间当天日期。示例含两种旧认证类别，两个命令都**预期 exit 1**，分别输出 `migration_required` / `blocked_by_documented_policy`；空/无效输入 exit 2。全部记录为 OAuth/Agent Key 时 exit 0 只表示元数据类别匹配，始终 `account_verification=not_performed`，不是已迁移或已获付款权限。

Stripe 文档未说明 cutoff 的具体时刻/时区，本工具只做日期模拟，不检测服务器 401。10-13 再核验，剩余 18 个日历日；依据是 [MCP 官方正文](https://docs.stripe.com/mcp)，人工迁移 runbook 见 [10-12 研究](research/daily/2026-10-12.md)，今日变化见 [10-13 研究](research/daily/2026-10-13.md)。工具无网络调用，不创建、轮换或撤销实际凭证。

### UCP handler 兼容性预检（不获取凭证）

```powershell
python -m lab.ucp_preflight
python -m lab.ucp_preflight --instrument card --relationship confirmed
python -m lab.ucp_preflight --instrument apple_pay
```

默认用完全合成的双方宣告测试 `link`，**预期 exit 1**：当前 Stripe `/complete` 不接受该 instrument。后两条 exit 0 仅为 `candidate_unverified`，始终 `payment_authorized=false`、`provider_verification=not_performed`。Google Pay 在本预检中拒绝，不自动转到 `com.google.pay`、转换 instrument 或降级到浏览器付款。

本地只审阅 UCP `2026-04-08` / Stripe handler `2026-06-25` 文档示例，匹配但未经本地审阅的版本也拒绝；这不是声明其他版本被供应商禁止。卡 tokenize 才检查双方 `sandbox/production` 环境一致和关系已确认，不能把该条件套到 Apple Pay wallet 路径。`--business-ucp-version` / `--business-handler-version` 可模拟版本漂移；无效日期 exit 2。所有参数只是元数据声明，不读取实际 UCP profile、key、PAN、SPT 或钱包数据，也不验证客户同意、Apple Pay 商户配置、地域/账户资格或支付结果。此工具不是 UCP wire-format/conformance 实现，更不是 checkout 的授权层。

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
