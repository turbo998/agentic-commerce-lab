# Stripe Sessions 2026：从 Personal Agent 到支付原生架构

**发布基线：2026-04-29；公开文档研究截点：2026-10-09。** 本文是原创研究，不复制供应商实现，不连接账户、不执行支付或计费模型调用。产品文档会变化；“文档描述”“本地模拟”“供应商 sandbox 验证”“真实资金验证”是不同证据等级。下列供应商能力均未由本实验室做 sandbox 或 live 验证。

## 1. 核心结论

Stripe 的 Agentic Commerce 不是一个统一的“Agent 支付 API”，而是覆盖不同参与者的产品组合：

| 参与者 | 核心诉求 | 对应产品 | 不能混淆的边界 |
|---|---|---|---|
| 商户 | 商品可被 Agent 发现、在 AI 渠道结账 | Agentic Commerce Suite（ACS）、ACP/UCP、Connect 平台集成 | 商户目录和订单不等于消费者付款授权 |
| 消费者及 Personal Agent 运营方 | 使用用户已有支付方式，按用户同意执行采购 | Link Agent Wallet | 客户 OAuth 不等于批准每一笔购买；Link API 不是 Stripe API |
| 付款凭证提供方与卖家 | 把受限付款能力交给指定卖家 | Shared Payment Token（SPT） | SPT 是受限凭证，不是订单、到账证明或独立支付网络 |
| 付费 API/数字服务提供者 | 无需传统注册订阅流程，按次向 Agent 收费 | MPP、Stripe machine payments、x402 支持 | HTTP 402、支付方法、收据、服务交付和结算需分别核实 |
| 企业或发卡平台 | 为 Agent 配置可受控的消费卡 | Issuing for agents | 可支持平台消费者用例，但不是个人 Link 钱包的另一个名称 |
| AI 服务运营商 | 计量快速消耗的资源、收款、控制 token abuse | Metronome、Tempo、Radar | 精细计量不意味着每个 token 都独立进行任意小额链上结算 |
| 开发者或企业财务 Agent | 采购基础设施、管理企业资金 | Stripe Projects、Treasury、Stripe MCP | 企业账户/资源权限不能推导为个人消费者购物权限 |

原生架构的中心应是 **Task + 报价快照 + 用户/委托批准 + 确定性权限层 + 支付尝试与恢复**，不是给模型同时开放商户工具、付款凭证和任意金融写操作。下面的产品组合是按需求选取的能力，不是必须串联的协议栈。

## 2. Sessions 发布日与当前状态矩阵

发布日列只依据当日官方公告；当前列依据研究日直接读取的产品文档。`preview`、`soon`、`now` 和“有文档”均不能统一改写成全球 GA。[S01]、[S02]

| 能力 | 2026-04-29 公告基线 | 2026-10-09 文档/资格证据 | 本轮未核实项 |
|---|---|---|---|
| ACS 商户接入 | 公告称可在 Dashboard 上传目录、管理 Agent access | 总览区分 seller 与 agent；agent 侧入口标 Private preview [S03] | 各渠道、商品类别和具体账户的上线资格 |
| ACS for platforms / Connect | 公告为平台接入 preview | 文档要求美国业务、waitlist approval；连接账户分别上传目录、配置 hooks、选择渠道 [S04] | 非美国平台开放计划、合同与渠道商业费用 |
| Google / UCP | 公告称买家“soon”可在 AI Mode/Gemini 购买 | 不能仅凭 UCP 文档存在认定该渠道对所有账户已上线 | 本轮没有逐账户验证渠道 enablement |
| Link Agent Wallet | 公告发布 Agent 钱包，强调批准与购买可见性 | 支付面向美国/加拿大客户；financial insights 面向美国客户；运营企业和卖家可以在这些国家之外 [S05] | 个别用户/支付方式资格与商业收费 |
| MPP + SPT | 公告称支持机器交易和通过 SPT/稳定币付款 | 文档给出 profile、402、PaymentIntent 处理及方法/地区门槛 [S08]、[S09] | 具体账户 enablement、实际退款/争议与端到端兼容 |
| Issuing for agents | 公告为 preview | 当前文档描述自用企业卡与平台发行卡；通过 Dashboard apply 或联系 Stripe [S10] | 发卡项目、地区、卡产品、卡组织与合同资格 |
| Metronome + Tempo | 公告宣布 streaming payments 组合 | 本轮核实公告；machine payments 文档另区分 sub-cent 计量与最小结算额 [S01]、[S02]、[S09] | 实际计量延迟、配置、渠道/链上最终性和商业条款 |
| Radar token abuse | 官方新闻稿宣布覆盖 signup/usage 风险 | 本轮核实公告级能力，不声称取得风控 API 权限 [S02] | API/SDK、定价、数据要求、误拒绝率与账户 enablement |
| Stripe Projects | 公告称向所有开发者开放，当日累计 32 providers | 当前文档称 60+ providers，并描述 provisioning、credential vault、环境和计费管理 [S11] | 某 provider 的实际供给/价格、企业政策和区域限制 |
| Agent-ready Treasury / MCP | 公告称企业金融 Agent 及关键动作人工确认 | MCP 文档把 balance summary 标 public preview，convert/send/setup recipient/transfer 标 private preview [S12] | 账户及地区资格、每项金融写操作是否获准、合同与费用 |

公告与当前文档有两类差异值得持续记录：一是 Projects provider 数量随时间增长；二是发布文案可能概括产品愿景，而开发者文档分别说明各具体入口的地区、preview 与 enablement 条件。这不是通过一张“支持 Agent”标签就能完成的采购判断。

## 3. 商户侧：ACS、Connect 与 AI 渠道

### 3.1 谁服务谁

ACS 面向希望通过 AI 渠道销售商品的商户。平台版本让 SaaS/Connect 平台为 connected accounts 上传目录、配置 checkout hooks，让连接账户选择启用的渠道。[S03]、[S04]

这条链路解决的是 **目录分发、交易信息回传、checkout 配置和商户运营**。它不能替消费者 Agent 判断是否具有用户的有效付款委托，也不能把自然语言“帮我买合适的东西”当成无限制 mandate。

### 3.2 当前 Connect 流程的架构含义

公开文档给出的核心顺序是：每个连接账户上传 feed → 分发到 enabled agent channels → 买家选择商品 → Stripe 开始 checkout → 平台处理 `customize_checkout` → checkout 确认前调用 `finalize_checkout` → 完成后发送 `checkout.session.completed` → 平台履约。[S04]

当前文档支持 direct charges 和带 `on_behalf_of` 的 destination charges，并把 connected account 作为 seller；该具体集成中应核实 charge type 和 merchant-of-record 责任，不能把整个 Connect 产品所有模式的法律责任统一套用过来。

文档还有三项容易被“AI 购物”故事掩盖的工程约束：

1. **目录不是实时库存。** 文档给出价格/库存频繁刷新建议，并提供 checkout 前价格/可用性 hook；用户批准时要绑定最终报价，而非早期搜索缓存。
2. **feed 导入可乱序完成。** 上传是独立异步任务，不保证按提交顺序完成；平台应以版本/时间戳防止旧报价覆盖新报价。
3. **删除与遗漏不同。** `upsert` 中省略商品不等于删除；错误使用 `replace` 可能删除未包含的商品。Agent 看到的可售商品应来自可审计的目录状态。

对本项目的设计推论：商户侧价格/库存改变应使本地报价指纹失效，重新请求用户批准；catalog 搜索结果不能直接构成支付请求。

## 4. 消费者侧：Link Agent Wallet

### 4.1 身份、产品与地域

Link Agent Wallet 的授权与请求分别使用 `login.link.com` 和 `api.link.com`；Stripe secret/restricted API key 不能替代代表一位客户的 Link OAuth access token。Link CLI/SDK 和 Stripe server SDK 不是相同的 API surface。[S05]

文档把两种能力分别授权：

- **Agent payments**：按具体购买申请付款凭证，面向美国与加拿大客户。
- **Financial insights**：读取客户选择分享账户的交易、余额等，面向美国客户，另有 Financial Connections 依赖。

支持付款不等于自动得到财务数据读取权限。运营 Personal Agent 的企业及卖家可位于其他国家，因此也不能把客户居住资格误写成所有参与者必须为美国/加拿大企业。

### 4.2 一笔购买的原生顺序

```mermaid
sequenceDiagram
    actor User as 用户
    participant Agent as Personal Agent
    participant Authority as 本地权限/工作流
    participant Link as Link OAuth / Wallet
    participant Seller as 商户 checkout
    Agent->>Authority: 候选商品与报价，申请执行
    Authority->>Authority: 检查主体、任务、预算与报价版本
    Authority->>Link: 创建对应本次购买的 spend request
    Link-->>User: 托管批准界面
    User->>Link: 审阅与批准
    Authority->>Link: 查询原 spend request 状态
    Link-->>Authority: 状态允许后取得受限凭证
    Authority->>Seller: 隔离执行器使用匹配 checkout 的凭证
    Seller-->>Authority: 付款/订单结果或未知状态
    Authority-->>Agent: 脱敏状态与收据
    Agent-->>User: 解释完成、拒绝或待恢复
```

该图是 **本项目参考设计**，不是宣称 Link 具有本地权限层 API。官方流程要求先判断卖家的收款方式，再创建 spend request、取得客户批准、查询状态、取得凭证并向卖家付款。[S06]

### 4.3 选择凭证，而非寻找万能 token

| 卖家入口 | Link 文档描述的凭证 | 服务端需要额外确认 |
|---|---|---|
| 支持且启用 Link 的 Stripe checkout | Link Pay Token | 商户匹配、checkout 是否支持该集成 |
| 接收 SPT 的 API 或 `method="stripe"` 的 MPP | Shared Payment Token | seller/network profile、金额、币种、expiry 和实际支付结果 |
| 普通卡表单 | 一次性虚拟卡 | checkout 执行隔离、敏感信息处理、未知结果与订单回查 |

“用户真实卡号没有暴露”不等于“一次性虚拟 PAN/CVC 不是秘密”。官方 CLI 文档特别建议不要把卡详情写到 stdout，而应隔离输出；本项目的架构应进一步禁止通用模型/工具读取 credential broker 的秘密文件或原始响应。[S06]

### 4.4 批准、幂等、时限与异常

- 默认会请求批准；`--no-request-approval` 是 **暂不发起批准请求**，文档描述之后调用 `request-approval`。不能据此推断可绕过客户批准直接发放/使用凭证。`created`、`pending_approval`、`approved` 与付款完成是不同状态。
- 文档描述客户有批准窗口；另有 request/credential expiry。不要把本地 demo 的时限当供应商固定承诺，也不要把同一 expiry 套到所有支付方法。
- 同一 purchase intent 创建 spend request 使用同一幂等键；商户端付款、订单与退款仍需自己的幂等和状态记录，不能以 wallet 创建幂等代替完整 checkout 幂等。
- `requires_action` 需要按官方 `next_action.resolution` 处理，例如原 request 的认证恢复或需要新 request；不能无条件重新支付，也不能把它当最终 decline。
- `approved` 只说明批准及可取得凭证，不证明商户已扣款或履约。查询实际 spend/payment 状态，保留商户订单与支付结果的映射。
- CLI 文档的 test 模式参数默认不是开启；本实验室不执行官方示例，也不把“本机命令”当无资金风险的 test-mode 操作。

## 5. SPT：受限访问凭证，不是资金动作

### 5.1 两端职责

SPT 允许 seller 在限制范围内访问客户 payment method。当前 agent-side 文档描述：获得 seller Stripe profile → 安全收集 customer payment method → 为指定 seller 签发带币种、最高金额和到期限制的 token → seller 使用 token 创建 PaymentIntent。[S07]

独立 SPT 集成的 agent/server、Link Wallet 与 Issuing 都可能涉及 SPT，但不能把它们的账户、身份和 API 认证视为一致：

| SPT 来源 | 资金/付款方式来源 | 认证和责任边界 |
|---|---|---|
| Link Agent Wallet | 客户 Link 账户中可用方式 | 客户 OAuth、wallet spend request 与客户批准 |
| agent-side SPT 集成 | 在该集成中安全收集的 payment method | Stripe 账户/profile、前端安全收集与 server-side issuance |
| Issuing 转换路径 | 平台/企业发行的 Issuing card | 发卡项目、cardholder/card 控制和 issuer authorization |

本地 `Approval`/`CredentialReference` 只是教学领域对象，不是供应商 SPT 对象。SPT 的限额是凭证可使用范围；本地订单绑定可以更严格，例如精确金额、逐行商品、任务版本。

### 5.2 可用性、版本与结果

当前公开 SPT 页列美国、加拿大和部分欧洲国家，不能套用 Link Wallet 的消费者支付地域作为所有 SPT 的地域。示例 API 带 preview 版本，实施时应固定版本、条款及 response/error 合同，而非只看可生成 token 的示例。

`token issued` ≠ `seller accepted token` ≠ `PaymentIntent captured` ≠ `merchant fulfilled` ≠ `funds cleared`。支付权限层应保存这些不同事实，而不是把一张 token 当 receipt。

## 6. MPP / x402：按调用购买数字资源

### 6.1 分开协议层、支付方法和资金结果

MPP 被官方描述为 Stripe 与 Tempo 共同制定的开放机器支付协议。Stripe 的实现路线是资源服务返回 402/payment details，Agent 提供受限付款凭证重试，服务端验证/处理付款并返回资源与收据；Stripe 服务端集成使用 PaymentIntents 等资金处理接口。[S08]

```text
资源请求
  -> 402 challenge（资源、方法、金额、币种及约束）
  -> 本地预算/用户委托检查
  -> 取得与 seller/resource 匹配的凭证
  -> 重试原资源请求
  -> 服务端验证/资金处理
  -> 资源交付 + receipt
  -> 对账、退款或资源交付异常处理
```

这不是把每个 402 交给模型自动付款：challenge 来自不可信外部资源，必须绑定原请求、允许的卖家与价格，不能让 challenge 自行提高 Agent 的预算或改收款人。

### 6.2 当前 Stripe 方法与粒度

| Stripe 文档中的路线 | 当前公开网络/方法 | 最小额与重要限制 |
|---|---|---|
| MPP + SPT/card | 卡方式，通过受限 SPT | 当前 card 最小 US$0.50 |
| MPP + stablecoin | Tempo USDC.e、Solana USDC | 当前 stablecoin 最小 0.01 USDC |
| x402 + Stripe stablecoin | Base USDC | 方法/网络组合不能从别家 x402 facilitator 任意外推 |
| MPP sessions | 可按 sub-cent work 计量 | 当前最小 settlement 为 0.01 USDC，不等于任意小额独立结算 |

以上是 Stripe 当前集成文档的阈值，不是所有 MPP/x402 实现的统一限制。机器支付页描述资金进入 Stripe balance、以 fiat 结算，并提供退款路径。稳定币接受还有地区、账户开通和批准门槛：美国规则并非所有州相同，境外业务也需核实 enablement。[S09]

当前文档另描述 Stripe 可为满足条件的 live Tempo 集成承担网络费，且该 hosted fee-payer 路线不支持 Connect；不能把“gas sponsored”写成没有支付手续费或所有平台免费。[S08]

### 6.3 Personal Agent 的适用场景

购买一次航班价格分析、实时旅行指南或专用数据 API，比先订阅整个 SaaS 更适合短任务。必须把数据服务额度与机票/酒店额度分别约束，即使二者属于同一用户目标。

超过 card 最小额的报价不意味着便宜；低于阈值也不能简单重复多笔支付凑数。按业务需要选择单次付费、聚合计量或明确的 session 额度，并将方法手续费、链上费用、模型成本和失败退款成本纳入真实成本模型。本轮未测这些成本。

本仓库的 402 流程只应称 **protocol-shaped simulation**，除非另行固定协议版本、通过对应 contract tests 并完成指定支付方法的验证。返回 HTTP 402 本身不是 MPP 兼容证明；本轮不运行可能移动真实资金的官方验证命令。

## 7. Issuing for agents：把付款能力落实到发卡控制

### 7.1 与个人钱包的区别

当前文档明确覆盖企业为自己的 Agent 发行卡，也覆盖平台为企业或消费者发行卡。应纠正“只支持企业消费”的过度概括：消费者场景可以通过合格的平台发卡项目存在，但并不因此变成人人可接入的 Link 个人钱包。[S10]

每条 Issuing agent payment 从 Issuing card 开始，可使用单次卡详情、由卡转换出的 SPT，或文档提到的 Visa/Mastercard agentic network token。按 cardholder/card 配置 merchant category、per-authorization 和周期限额，再结合 real-time authorization。

### 7.2 不让模型站在发卡决策的关键路径

文档描述默认 real-time authorization 响应超时为 2 秒，超时会使用卡的默认规则。最合适的实现是预先固化可快速判断的政策、服务内的预算状态、允许的商户和风险阈值，而不是在每次授权回调时等待多轮 LLM 推理。

可由模型事前解释预算政策、事后分析异常；真正的 approve/decline 使用确定性快速路径。还需验证事件签名、去重、fallback rules、outage behavior、部分 capture、退款和账务映射。

### 7.3 强制 capture 与现实资金风险

Issuing 文档明确将 partial captures、over-captures、force captures 纳入交易可见性。由此得到重要架构结论：**本地预算控制可以阻止新的 Agent 发起请求，但不能宣称替代卡网络全部规则或绝不出现超额最终资金事实。**

生产服务必须接纳已发生的权威交易事实，记录授权与最终金额差异、资金敞口、补偿/争议及人工处理。不能因为回调违反本地预期就丢弃事实，也不能用一个“预算永不负”的模拟字段掩盖外部实际损失。本地 fixed-quote 不变量仅是本地模拟的验收，不是生产资金保证。

## 8. Metronome、Tempo 与 Radar：计量和风险同样需要原生设计

Sessions 把 streaming payments 定位为应对 Agent 在机器速度下消耗 token 的方式：Metronome 负责精确 usage/rating，Tempo 提供稳定币微支付能力。[S01]、[S02]

对 AI 服务提供商而言，需要分别保存 usage event、rated charge、预留/可用信用、已付金额与最终结算；对消费这些服务的 Personal Agent，则需要任务预算、调用次数/时长上限和停止策略。不能把“模型愿意继续调用”当用户同意持续付费。

Radar token abuse 的公告针对伪造注册、免费额度/试用滥用以及产生无法收回的推理成本。官方新闻稿的检测数量和攻击比例是供应商报告数据，不是本实验室实测结果，也不能直接外推为本方案 ROI。

三个控制维度不可互相替代：

- **授权风险**：是不是这个用户/任务允许的支出？由本地权限/用户批准负责。
- **支付/账户欺诈**：真实交易主体及网络风险是否合理？由相关 issuer/PSP 风控与运营政策负责。
- **AI 资源滥用**：调用者是否利用试用、速率或计量漏洞消耗资源？由服务身份、usage/rating、credits、限速及风险系统负责。

本轮只验证公告与架构定位，没有配置 Metronome/Radar/Tempo，不声称拥有其实时风险 API、延迟 SLA 或具体商业定价。

## 9. Projects 与 agent-ready Treasury：相邻但不同的 Agent 经济活动

### 9.1 Stripe Projects

Projects 让开发者或 coding agent 为应用配置第三方 hosting、database、auth、AI、observability 等服务，管理计划、环境和计费。官方文档描述 provider associations、resource provisioning、credential vault 与同步到环境文件；关联会保持到显式移除。[S11]

这对应“开发者 Agent 采购和部署基础设施”，不是买衣服/机票的消费者钱包。必须单独限制允许的 provider、订阅升级、资源/成本上限、创建/删除权限及秘密读取。删除资源不意味着已写出的凭证自动被清理，官方文档也提醒 credential lifecycle 的后续管理。

本项目不安装 Projects 插件、不 provisioning 第三方资源、不上传账单/账户数据。后续 demo 如研究开发者采购，应使用合成 provider 和报价，保持消费批准与资源执行的双重门槛。

### 9.2 企业 Treasury 与 Stripe MCP

当前 Stripe MCP 文档支持 OAuth 或最小权限 Agent API key，并区分 live mode 与 sandbox、账户/组织和 session revocation 范围。其通用 `stripe_api_write` 可以对应广泛 Stripe 写操作；**工具可发现与拥有身份不等于每次金融操作已获企业业务批准**。[S12]

当前 Treasury tools 中 `get_balance_summary` 为 public preview，而 `convert_currency`、`send_money`、`setup_recipient`、`transfer_money` 为 private preview；需要逐项 access gate。读取余额、换汇、设置收款人、汇款是不同风险级别，不能共用一个笼统的“Agent 已登录”授权。

同一 MCP 文档还标记 **2026-10-31** 的认证迁移：不再接受未带 Agent tag 的 full-access secret/restricted API keys，需 OAuth 或 Agent Keys。这个研究日后的迁移要求不能倒写为 Sessions 当日已经生效的要求。

个人购物前端若是 Copilot，应经过受限 Commerce API/connector 再进入本地权限层，不直接把 Treasury 或通用金融 write tools 暴露为购物 Agent 的支付手段。该 Copilot 接入是参考设计，不是当前已部署的集成。

## 10. 本项目集成与研究路线

| 阶段 | 目的 | 可接受证据 | 不应宣称 |
|---|---|---|---|
| 公开研究 | 确认角色、产品、地域、条款和版本 | 本文引用的公开官方页面与明确未知项 | 账户已具资格、生产可用 |
| 离线模拟 | 验证权限边界与订单/支付恢复 | 固定合成数据、真实执行的本地测试与评估 | 模型真实推理、供应商认证或真实交易 |
| 合同适配 | 固定 API/协议版本与错误/事件形状 | mock client、contract fixtures、明确 capability gates | sandbox 或 live 已接通 |
| 经授权 sandbox | 核实 provider credential、事件、退款和恢复 | 单独批准后记录 sandbox 端到端结果 | 真实资金结算或生产 SLA |
| 生产资格/上线 | 合同、隐私、认证、风控与运营责任 | 业务/法务/安全/供应商共同批准及生产证据 | 仅以 demo 测试代替真实责任 |

费用与收益也分层记录：支付方法最小额不是 processing fee；gas sponsorship 不等于全部免费；目录/平台分成、卡项目费用、机器服务报价、LLM 成本、争议/退款成本必须按具体账户/区域/合同核实。本轮不提供未经核实的费率，不把 GMV 当收入，不虚构转化提升或签约客户。

## 11. 公开来源台账

所有来源访问日为 **2026-10-09**。公告发布日期为 2026-04-29；产品文档为持续更新的研究日快照，未声称取得其完整历史版本。本研究仅读取公开材料，未接受供应商协议、连接账户或执行官方命令。

| ID | 一手来源 | 主要支持的结论 |
|---|---|---|
| S01 | [Stripe Sessions 全部发布][S01] | 发布日 now/preview/soon 区别、ACS/Connect/Link/MPP/Issuing/计量/Projects/Treasury |
| S02 | [Stripe Sessions 官方新闻稿][S02] | 钱包、streaming、token abuse、Projects 当日开放及生态规模 |
| S03 | [Agentic Commerce 总览][S03] | seller 与 agent 路径、agent preview、能力定位 |
| S04 | [Connect 平台 Agent 销售][S04] | US/waitlist、feed/hook、charge types、目录时效/导入乱序 |
| S05 | [Link Agent Wallet 总览][S05] | API/OAuth 边界、能力/客户地域、SDK/CLI、数据责任 |
| S06 | [Link Agent 消费流程][S06] | spend request/批准/凭证/状态、三类凭证、幂等、敏感输出、test 默认 |
| S07 | [SPT agent-side 概念与实现][S07] | seller profile、限额/币种/expiry、地域及 API preview |
| S08 | [Stripe MPP 集成][S08] | 402/credential/PaymentIntent、方法最低额、Tempo fee payer、live test 风险 |
| S09 | [Stripe Machine Payments][S09] | MPP/x402 方法/网络、地域、退款、session 计量与结算粒度 |
| S10 | [Issuing for agents][S10] | 企业/平台/消费者路线、实时授权超时、spend controls、capture 差异 |
| S11 | [Stripe Projects][S11] | providers、provisioning、账户关联、vault/环境和生命周期 |
| S12 | [Stripe MCP][S12] | OAuth/Agent Keys、工具权限、Treasury previews、2026-10-31 迁移 |

[S01]: https://stripe.com/blog/everything-we-announced-at-sessions-2026
[S02]: https://stripe.com/newsroom/news/sessions-2026
[S03]: https://docs.stripe.com/agentic-commerce
[S04]: https://docs.stripe.com/connect/saas/tasks/enable-in-context-selling-on-ai-agents
[S05]: https://docs.stripe.com/agentic-commerce/agents/link-agent-wallet
[S06]: https://docs.stripe.com/agentic-commerce/agents/link-agent-wallet/use-link-wallet-pay-online
[S07]: https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens?agent-seller=agent
[S08]: https://docs.stripe.com/payments/machine/mpp
[S09]: https://docs.stripe.com/payments/machine
[S10]: https://docs.stripe.com/issuing/agents
[S11]: https://docs.stripe.com/projects
[S12]: https://docs.stripe.com/mcp
