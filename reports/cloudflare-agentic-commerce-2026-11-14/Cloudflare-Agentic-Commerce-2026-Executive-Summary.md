# Cloudflare 智能体商业（Agentic Commerce）最新产品与解决方案总结报告

> **调研日期**：2026-11-14 | **视角**：AI Solution Architect (SA) 产品解构与商业场景落地  
> **技术资产仓库**：[`turbo998/agentic-commerce-lab`](https://github.com/turbo998/agentic-commerce-lab)（双语全栈 FAQ + SVG 架构图 + Python 边缘网关仿真与单测）

---

## 一、 核心结论（Executive Takeaways — 3 分钟速览）

2025 至 2026 年（特别是 **2026 年 8 月 Agents Week** 及 **x402 Foundation / MPP** 发布后），Cloudflare 已完成了从传统 CDN/WAF 安全厂商向 **全球智能体商业中立基础设施（Agentic Commerce Neutral Control & Clearing Plane）** 的战略跃迁。其核心逻辑是：**不在应用层做封闭电商平台，而是在网络边缘解决“我是谁、怎么读、怎么付、怎么管”四大底层信任断点**：

1. **身份与防爬范式重构（从 IP/UA 封禁走向密码学签名）**：通过 **`Web Bot Auth`（基于 IETF RFC 9421 HTTP 消息签名）** 与 **`AI Crawl Control` + `AI Labyrinth`**，首次让商户能在 `<1 ms` 内精准区分“持用户授权前来下单的真实购物 Agent”与“伪造 UA 的恶意比价/黄牛爬虫”。
2. **商品发现成本骤降 90%–99%（边缘零改造适配 Agent）**：通过 **`Markdown for Agents`**（识别 `Accept: text/markdown` 实时剥离冗余 HTML 与隐藏 DOM 注入，并附带 `Content-Signal` 版权头）、**`Agent Visibility Template`** 与 **`Stateless MCP Servers (2026-07-28)`**，存量独立站无需重写后端即可暴露给 ChatGPT、Claude、Perplexity 与企业采购 Agent。
3. **双轨制原生机器支付体系（零售卡组代买 + HTTP 402 毫秒级微支付）**：
   - **法币零售卡组轨**：联手 **Visa (`Trusted Agent Protocol, TAP`)**、**Mastercard (`Agent Pay`)**、**Amex** 与 **Stripe (`SPT`)**，实现带拒付保护（Liability Shift）的零售代买。
   - **机器原生微支付轨**：与 Coinbase 联合创立 Linux 基金会旗下 **`x402 Foundation`**，并与 Stripe 推出 **`MPP`（Machine Payments Protocol，`mppx` SDK）**、**`NET Dollar`（1:1 美元稳定币）** 与 **`Pay Per Crawl`**，复活 `HTTP 402 Payment Required`，实现无需注册账号的按次/按秒流式微结算。
   - **买方资金护栏**：推出 **`Cloudflare Wallets` 与 `cloudflare.pay`**，为每个子 Agent 派发独立 **`Virtual Wallet`**（如 `procurement.acme.cloudflare.pay`），强制执行单笔限额、日预算熔断与商户白名单。
4. **有状态长时编排与能力级零信任底座**：依托 **`Agents SDK` + `Durable Objects`（每 Agent 独立 SQLite）+ `Workflows (GA)`** 支撑跨天议价与拆单补偿，并用 **`Cloudflare OS` (`Gatekeeper Workers`)** 从微内核级杜绝提示词注入越权盗刷。

---

## 二、 重点产品与核心功能速查表（5 大产品支柱）

| 架构层级 | 核心产品 / 协议 | 关键技术能力 | 解决的核心商业痛点 |
| :--- | :--- | :--- | :--- |
| **L1 身份与爬虫治理** | `Web Bot Auth` (RFC 9421) / `Bot Management` / `AI Crawl Control` / `AI Labyrinth` | Ed25519/RSA-PSS 请求级非对称签名、JWKS 公钥目录；按“搜索 / Agent 执行 / 训练”三分授权；虚假迷宫消耗恶意爬虫算力 | 消除 WAF 误杀合法导购 Agent 导致的 GMV 损失，同时零容忍阻断黄牛与未授权白嫖爬虫 |
| **L2 商品发现与互操作** | `Markdown for Agents` / `Agent Visibility Template` / `Stateless MCP (2026-07-28)` | 边缘实时 HTML→Markdown（省 90%+ Token）+ `Content-Signal`；零代码注入 JSON-LD & `/llms.txt`；免 OAuth/支持 OAuth 2.1 的远程 MCP 工具网关（兼容 UCP / ACP） | 让存量电商目录以极低 Token 成本、零前端改造直接接入各大 AI 导购入口 |
| **L3 零售卡组信任结算** | `Visa TAP` + `Mastercard Agent Pay` + `Amex` + `Stripe SPT` | 在 RFC 9421 之上叠加“消费者意图证明 + 一次性网络级支付令牌”，直连卡组风控网络 | 解决“商家不敢收无人值守订单”与“友好欺诈拒付（Friendly Fraud）”归责难题 |
| **L4 机器微支付与变现** | `Cloudflare Wallets` (`cloudflare.pay`) / `x402` / `MPP` (`mppx`) / `NET Dollar` / `Pay Per Crawl` | 账户总钱包 + 子 Agent 虚拟钱包限额护栏；`HTTP 402` 原生挑战-签名-回执闭环；支持单次扣款 (`charge`)、按秒流式会话 (`session`) 与稳定币秒级结算 | 打通 `$0.001–$0.50` 级别的研报按次读取、API 付费工具调用 (`paidTool`) 与跨国即时结算 |
| **L5 运行时与零信任安全** | `Agents SDK` / `Durable Objects` / `Agent Memory` / `Workflows (GA)` / `Cloudflare OS` | 每 Agent 专属 SQLite 状态机与 WebSocket 休眠唤醒；跨周多步 Saga 事务；`Gatekeeper Workers` 细粒度能力沙箱 + `Identity-Aware AI Gateway` | 支撑长周期议价/履约编排，同时确保即使模型遭遇间接提示词注入也无法突破钱包与网络边界 |

---

## 三、 六大典型使用场景与落地方案选型

| 场景编号与名称 | 适用客群 | 推荐 Cloudflare 产品组合 | 关键业务价值与架构要点 |
| :--- | :--- | :--- | :--- |
| **场景 1：B2C 品牌独立站免误杀导购结账** | 零售品牌、Shopify/自建站、OTA 票务 | `Bot Management` + `Web Bot Auth` + `Markdown for Agents` + `Visa TAP` / `Mastercard Agent Pay` | 浏览态用 `Web Bot Auth` 绿通 + Markdown 加速比价；结账写操作强制要求 `Visa TAP` 双重锚定，兼顾高转化与零黄牛风险 |
| **场景 2：高价值内容与行业数据按次变现** | 财经媒体、智库研报、垂直行情库、商品评测站 | `AI Crawl Control` + `Pay Per Crawl` + `x402` / `NET Dollar` + `AI Labyrinth` | 对普通爬虫返回 `HTTP 402` 按篇微收费（Cloudflare 充当 MoR 统一结算），将“防不胜防的爬虫成本”直接转化为高毛利 API 收入 |
| **场景 3：付费远程 MCP 工具市场（Paid SaaS API）** | SaaS 厂商、跨境物流查询、海关税率/征信 API | `Workers` + `Stateless MCP (2026-07-28)` + `withX402` (`paidTool`) / `MPP (mppx)` | 第三方 Agent 无需人工注册充值买月卡，连上远程 MCP URL 即可按调用次数或流式会话自动完成微支付闭环 |
| **场景 4：企业 B2B 尾料寻源与多级预算管控** | 制造业 MRO 采购、IT 耗材补货、云资源采购 | `Cloudflare Wallets` (`Virtual Wallets`) + `Workflows (GA)` + `Durable Objects` + `Identity-Aware AI Gateway` | 财务给每个部门采购 Agent 派发专属 `*.cloudflare.pay` 虚拟钱包，硬编码日限额与合格供应商白名单，超额自动挂起等待人工审批 |
| **场景 5：跨平台比价、自动议价与拆单原子履约** | 导购超级入口、差旅机酒联订 Agent、跨境代采 | `Agents SDK` + `Agent Memory` + `Workflows` + `@cloudflare/computer` + `Cloudflare OS` | 利用每 Agent 独立 SQLite 记录多轮报价快照，通过 Saga 流程保证多商户库存预占与分账一致性，`Gatekeeper` 隔离外部不可信页面 |
| **场景 6：存量传统电商 7 天快速 Agent 化改造** | 缺乏 AI 研发团队的中大型传统零售商 | `Markdown for Agents` + `Agent Visibility Template` + 边缘反向代理 `Stateless MCP` | **零核心系统代码侵入**：在 CDN 边缘勾选开启 Markdown 转换与结构化 Schema 注入，7 天内完成 AI 搜索可见性与导购就绪度升级 |

---

## 四、 支付与授权协议选型速查（什么时候用哪套协议？）

- **买实物商品 / 机酒票务（客单价 `$10–$5,000`，需退换货与拒付保护）** 👉 选 **`Web Bot Auth` + `Visa TAP` / `Mastercard Agent Pay` / `Stripe SPT`**。
- **买单篇研报 / 实时行情 / 单次 MCP 工具调用（客单价 `$0.0005–$2`，免注册高频调用）** 👉 选 **`HTTP 402` + `x402` + `NET Dollar` / USDC**。
- **买按秒计费算力 / 流媒体 / 混合支持法币卡与稳定币的商业 API** 👉 选 **`MPP` (Machine Payments Protocol, `mppx` SDK)**（向后兼容 x402，原生支持 `session` 流式通道与法币卡轨）。
- **企业内部管控研发/采购 Agent 对外花钱上限** 👉 选 **`Cloudflare Wallets` (`Virtual Wallets` + `*.cloudflare.pay` 策略护栏)**。

---

## 五、 架构师分阶段落地路线图（SA Action Plan）

1. **Day 1–7（边缘可见性与流量摸底，零代码改动）**：在 Cloudflare 控制台开启 `AI Crawl Control` 可观测面板、`Markdown for Agents` 与 `Agent Visibility Template`，量化当前来自 OpenAI / Anthropic / Perplexity 等 Agent 的真实访问占比。
2. **Day 8–21（读写分离门禁与防伪加固）**：启用 `Web Bot Auth` 验签放行已认证导购 Agent，将伪造 UA 流量导入 `AI Labyrinth`；对结账接口接入 `Visa TAP` / `Mastercard Agent Pay` 或 `Stripe SPT` 令牌校验。
3. **Day 22–45（API / 内容变现与买方钱包试点）**：将高价值查询接口封装为 `Stateless MCP Server`，挂载 `paidTool` (`x402` / `MPP`) 对外按次收费；内部采购/研发 Agent 接入 `Cloudflare Virtual Wallets` 实施硬性限额治理。

---

## 六、 完整技术资产链接（已归档至 GitHub 主分支）

- **中文全栈深度调研与 FAQ（含 Mermaid 时序图与核查清单）**：`docs/cloudflare-agentic-commerce-fullstack-architecture-faq.md`
- **英文全栈版（English Full-Stack FAQ）**：`docs/cloudflare-agentic-commerce-fullstack-architecture-faq.en.md`
- **高清全栈架构与六大场景全景 SVG 图**：`assets/svg/189-cloudflare-agentic-commerce-fullstack-2026-11-14.svg`
- **Python 边缘网关与双轨 402/TAP 钱包护栏可运行仿真器**：`lab/cloudflare_agentic_commerce.py` & `tests/test_cloudflare_agentic_commerce.py`
