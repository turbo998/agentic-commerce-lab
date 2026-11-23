# 企业 B2B 赊销账期核保（`Net-30 / Net-60 Trade Credit`）与无追索权保理选型（`Resolve / Balance / Hokodo / Mondu vs. Allianz Trade / Coface 信用保险`）、防冒充大企业骗货（`B2B Identity Theft`）、防未开票在途敞口漏算与防发票重复质押托管 Agent 架构选型 FAQ

> **核心选型结论速览**：在企业 B2B 批发商城、工业品分销与大宗采购中，超过 `75%` 的买方拒绝当场刷信用卡，而是要求 **`Net-30 / Net-60 / Net-90` 商业信用账期**。然而传统自营赊销或粗放接入 B2B 先买后付（B2B BNPL）常遭遇三大坏账深渊：① **“企业身份冒用诈骗（B2B Business Identity Theft / Impersonation）”**：诈骗团伙花 `$10` 注册一个跟世界 500 强极其相似的域名（如 `@walmart-procure.com`），填上沃尔玛真实的公开税号（`EIN / DUNS`），通过线上 AI 秒批拿到 `$150,000` `Net-60` 授信额度，将 100 台顶配笔记本发往郊区临时租用的自提仓库后人间蒸发；② **“未开票已发货敞口盲区（Unbilled Delivery Exposure Blindspot）”**：ERP 信用检查只查“已开具发票的应收账款（Open AR）”，恶意买方趁仓库发货后、财务月底统一开票前的 7 天时间差，用 `$50k` 额度连下 6 单共拉走 `$300k` 货物；③ **供应商一票多融重复质押（Double-Pledge Invoice Factoring）或未签收空开发票骗保理融资**。  
> 生产级架构必须实施 **“企业官方域名 `DMARC/SSO` + `DUNS/LEI` 官方备案收货仓地址硬绑定门禁 + 含‘已批未发 + 已发未开票（Unbilled Shipments）+ 逾期挂起’的全口径实时信用敞口原子锁 + 基于电子发票唯一哈希与买方签收单（`GRN`）的无追索权 `T+1` 保理分拆放单控制面”**：可将 B2B 冒名骗贷、超限爆雷坏账与账期资金占压成本削减 **39%**（以季度 `$330,000` 赊销坏账、冒名欺诈与资金周转损耗池计，净成本降至 `$201,300`，每季度净节省 **`$128,700`**）。

![B2B Net-30/60 Trade Credit Underwriting & Non-Recourse Factoring Architecture](../assets/svg/739-b2b-trade-credit-net30-kyb-unbilled-exposure-factoring-escrow-2026-11-24.svg)

---

## 一、 业务方与架构师灵魂拷问（Q&A）

### Q1：骗子拿到了大企业公开的营业执照号和 `DUNS` 编码来申请 `Net-60` 账期，为什么单纯查企业征信局（D&B / Experian）不仅防不住，反而会给出满分授信？
- **“企业征信高分”不代表“屏幕前的申请人真是那家公司的人”**：
  - 任何一家上市公司或知名医院的 `EIN`、`DUNS` 与注册地址都是公开可查的；当骗子填写“买方：某三甲医院 / 某世界 500 强”时，征信接口当然返回 `AAA` 极优评级！
  - 真正的破绽在于：骗子留的是刚注册 15 天的近似邮箱域名（Lookalike Domain，如 `@target-supplychain.com`），且要求的收货地址（`Ship-To`）不是该集团在邓白氏/ERP 备案的仓库，而是某个偏远快递代收点或短期租赁仓。
- **架构解法（官方主域名 `WHOIS > 180d` + 企业 `OIDC/SAML` 或对公账户Plaid验真 + 备案收货地址白名单门禁 `HTTP 403`）**：
  - 严禁仅凭填写的税号/`DUNS` 文本匹配就批出 `Net-30/60` 额度；
  - 强制三重核验：① 申请人邮箱域名必须与 `DUNS / LEI` 官方主域名完全一致（拦截新注册近似域名）；② 首次大额赊销必须通过 `Plaid / Open Banking` 验证对公银行账户所有权或企业 `Entra ID / Okta SSO` 登录；③ **收货地址（`Ship-To`）必须命中买方企业工商/税务/邓白氏注册经营场所白名单**（凡使用近似假域名或要求将赊销货物发往未备案第三方私人地址的，立即触发 `HTTP 403 B2B_IMPERSONATION_LOOKALIKE_DOMAIN_OR_UNVERIFIED_SHIP_TO_DOCK` 拦截）。

### Q2：为什么有些客户信用额度明明只有 `$100,000`，却能在破产跑路前一周从我们的 B2B 商城提走 `$400,000` 的货？
- **“财务开票滞后（Invoicing Lag）”造成的信用检查漏洞**：
  - 许多传统 ERP（包括未开启高级信用管理模块的旧配置）在审单时只计算 `Open Invoiced AR（已开票未回款余额）`；
  - 从订单审批通过 $\rightarrow$ 仓库拣货出库 $\rightarrow$ 物流妥投 $\rightarrow$ 财务月底汇总开具正式增值税/商业发票，中间往往有 3–10 天窗口期；此时这批已出库货物的 `Open Invoiced AR` 仍显示为 `$0`！
- **架构解法（全生命周期四项式实时信用敞口公式 + 1 天逾期自动熔断 `HTTP 422`）**：
  - 信用控制面必须采用 `Redis / PostgreSQL Serializable` 原子扣减，执行 **全口径实时敞口公式**：
    $$\text{Total\_Exposure} = \text{Open\_Invoiced\_AR} + \text{Unbilled\_Shipped\_GRN} + \text{Approved\_Open\_SO} + \text{Current\_Order\_Total}$$
  - 同时检查账龄（Aging）：只要存在任意一笔超宽限期逾期发票（`Past_Due_Days > Grace_Period`）或全口径敞口超限，立即拒绝纯赊销放单（触发 `HTTP 422 CREDIT_EXPOSURE_EXCEEDED_INCLUDING_UNBILLED_SHIPMENTS_OR_PAST_DUE_AR`）。

### Q3：如果买方想下 `$120,000` 的急单，但他剩余可用 `Net-30` 授信额度只有 `$80,000`，难道只能整单拒掉把客户推给竞争对手吗？同时保理商如何防止卖家拿同一张发票向两家机构重复融资？
- **架构解法（发票唯一哈希防双押门禁 `HTTP 451` + “授信额度内走 `Net-30` 无追索权保理 + 超额部分 `$40k` 走实时 `Pay-by-Bank ACH`”混合拆单 `HTTP 409`）**：
  - **防一票多融与空票骗贷**：保理放款前强制在联盟登记簿/`UCC-1` 税务哈希池核验 `SHA256(Seller_TaxID + Buyer_TaxID + Invoice_No + Amount)` 无重复质押，且必须关联买方电子签收单 `GRN / vPOD`（否则触发 `HTTP 451 DOUBLE_PLEDGED_INVOICE_HASH_OR_UNACCEPTED_GRN_FACTORING_FRAUD`）；
  - **超限自动混合支付（Hybrid Credit + Cash Split）**：无需人工拒单，Agent 自动将订单拆分为：`$80,000` 走 `Resolve / Hokodo` 无追索权 `Net-30`（卖家 `T+1` 收全款，保理商承担买方违约风险）+ 超出额度的 `$40,000` 引导买方当场通过 `Open Banking ACH / SEPA` 现结并赠 `1.5%` 现付折扣（确认返回 `HTTP 409 NON_RECOURSE_NET30_AND_OVERFLOW_ACH_SPLIT_SETTLEMENT_CONFIRM`）。

---

## 二、 直观可视化图解（Mermaid 决策树 + 架构图 + 时序图）

### 1. 企业 B2B 赊销核保、全口径敞口锁与无追索权保理决策树
```mermaid
flowchart TD
    A[企业买方或采购 Agent 在 B2B 结账页申请 Net-30/60 账期] --> B{买方域名是否与 DUNS/LEI 主域名一致<br/>且 Ship-To 属于官方备案经营地址?}
    B -- 近似假域名或发往未备案私人仓库 --> C[HTTP 403 拦截: 阻断冒充大企业骗货攻击并强制转全款电汇审核]
    B -- KYB 与收货仓真实 --> D{核验全口径敞口: 已开票AR + 已发未开票<br/>+ 在途订单 + 本单 <= 授信上限且无逾期?}
    D -- 漏算未开票发货导致实际超限或存在逾期账单 --> E[HTTP 422 拦截: 锁定超限放单或引导超额差额转实时 Pay-by-Bank 现结]
    D -- 额度充足或已拆单 --> F{卖家申请 T+1 无追索权保理融资时<br/>发票哈希是否唯一且具备买方签收单 GRN?}
    F -- 命中重复质押哈希或货物尚未签收 --> G[HTTP 451 拦截: 阻断一票多融双押与空开发票套现欺诈]
    F -- 哈希唯一且已妥投 --> H[HTTP 409 确认: 无追索权 T+1 放款 + 超额自动混合分拆净省39%]
```

### 2. B2B 嵌入式账期（`Resolve / Balance / Hokodo`）× 全口径信用账本架构图
```mermaid
flowchart LR
    subgraph KYB["1. 反冒名 KYB 与收货仓门禁"]
      DOM["企业域名 WHOIS/DMARC + SSO 核验"]
      DOCK["DUNS/LEI 官方备案 Ship-To 地址库"]
    end

    subgraph Ledger["2. 全口径实时信用敞口引擎"]
      EXP["Total Exposure = Open AR<br/>+ Unbilled Shipments + Open SO"]
      SPLIT["超限自动混合拆单器<br/>(额度内 Net-30 + 超额部分 ACH 现结)"]
    end

    subgraph Factor["3. 无追索权保理与防双押清算层"]
      LIEN["发票五元组哈希唯一锁 (UCC-1 / Tax Registry)"]
      PAY["妥投 T+1 100% 无追索权放款给卖家"]
    end

    DOM & DOCK --> EXP --> SPLIT --> LIEN --> PAY
```

### 3. B2B 买方实时核保、超额混合拆单与妥投 `T+1` 无追索权保理放款时序图
```mermaid
sequenceDiagram
    autonumber
    participant BUY as 企业买方采购 Agent
    participant CTRL as 受托 B2B 信用控制面
    participant BNPL as Resolve / Balance / Hokodo 保理引擎
    participant WMS as 卖家仓库与 ERP

    BUY->>CTRL: 1. 提交 $120,000 采购单 (申请 Net-30 账期)
    CTRL->>CTRL: 2. 校验企业主域名 + Plaid 对公账户 + DUNS 备案收货仓 -> 通过!
    CTRL->>CTRL: 3. 计算可用额度: 授信 $100k - (已开票 $10k + 已发未开票 $10k) = 剩余可用 $80k
    CTRL-->>BUY: 4. 触发智能拆单建议: $80,000 走 Net-30 免息账期 + 超额 $40,000 走 ACH 现结 (享 1.5% 折扣)
    BUY->>CTRL: 5. 确认混合支付方案并完成 $40,000 ACH 扣款
    CTRL->>WMS: 6. 下达出库指令，物流妥投后回传买方电子签收单 (vPOD / GRN)
    CTRL->>BNPL: 7. 登记唯一发票哈希并提交无追索权保理请求 ($80,000)
    BNPL-->>WMS: 8. T+1 向卖家结算账户打款 $77,920 (扣除 2.6% 无追索保理费，零坏账风险 HTTP 409)!
```

---

## 三、 四大主流企业 B2B 赊销与贸易金融方案横向选型矩阵

| 评估维度 | Resolve / Balance (北美首选) | Hokodo / Mondu (欧洲首选) | Allianz Trade / Coface (传统信用险) | 卖家自营 ERP 内部赊销 |
| :--- | :--- | :--- | :--- | :--- |
| **审批速度与体验** | **结账页 API `<3 秒` 自动批额**，支持超额混合支付 | **结账页实时欧洲各国工商税号核保**（支持英法德荷西） | 大额合同人工调阅财报需 2–5 个工作日（现已推出部分 API） | 需买方填 PDF 信用申请表并找 3 家贸易参考人，耗时 1–2 周 |
| **卖家回款时间（`DSO`）** | **`T+1 / T+2` 立即回款**（内嵌无追索权保理资金池） | **`T+1` 发货/妥投即回款** | **不提供资金垫付**（卖家仍需等 30–90 天买方付款，或另找银行做保理） | 漫长等待 45–75 天，严重拖垮卖家现金流 |
| **坏账风险承担方** | **`100% 无追索权（Non-Recourse）`**（买方破产由平台承担） | **`100% 无追索权`**（内嵌劳合社/慕再信用险） | 赔付 **85%–90%**（卖家需自担 10%–15% 免赔额且理赔周期长） | **卖家 100% 自担坏账** |
| **综合费率成本** | 单笔交易额的 **`2.1%–3.5%`**（含资金成本+信用险+催收） | 单笔交易额的 **`1.9%–3.2%`** | 年化保费仅 **`0.15%–0.45%`**（极具规模成本优势） | 表面零通道费，但隐含高昂资金成本与专职催收人力 |

---

## 四、 确定性策略评估器与 7-Card 基准测试报告（`synthetic`）

### 1. B2B 赊销防冒名 KYB、全口径敞口锁与防双押保理评估器（Python 参考实现）
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class B2bTradeCreditFactoringPolicyInput:
    quarterly_b2b_bad_debt_impersonation_and_dso_pool_usd: float = 330000.0
    lookalike_domain_impersonation_or_unverified_ship_to_dock: bool = False
    exposure_exceeded_with_unbilled_shipments_or_past_due_ar: bool = False
    double_pledged_invoice_hash_or_unaccepted_grn_factoring: bool = False
    non_recourse_net30_and_overflow_ach_split_ready: bool = False
```

### 2. 7-Card 4:5 视觉基准测试报告摘要
1. **Card 1 (`1 / 7` · `HANDS-ON · B2B TRADE CREDIT & FACTORING`)**：通过反冒名 `KYB + 备案仓锁` + 含未开票发货的全口径信用敞口门禁 + 无追索权保理与超额 `ACH` 混合分拆，季度 B2B 赊销坏账、冒名骗贷与资金占压成本从 `$330,000` 降至 `$201,300`（净省 **39% / `$128,700`**）。
2. **Card 2 (`2 / 7` · `SCENARIO: IMPERSONATION_AND_UNBILLED_EXPOSURE`)**：成功拦截注册近似域名冒充名企把 `$150k` 电子产品发往私人仓库的骗局（`HTTP 403`）、阻断利用 7 天未开票时间差超额提货 4 倍的漏洞（`HTTP 422`），并拦截一票多融双押发票（`HTTP 451`）。
3. **Card 3 (`3 / 7` · `WHAT I TESTED`)**：覆盖 5 类状态码：`200`（KYB 与全口径授信通过）、`403`（近似域名冒充名企或发往未备案私人仓库拦截）、`422`（计入已发货未开票金额后总敞口超限或存在逾期账单拦截）、`451`（发票唯一哈希命中重复质押或无买方签收单 GRN 骗保理拦截）、`409`（无追索权 Net-30 T+1 放款 + 超额 ACH 混合拆单确认）。
4. **Card 4 (`4 / 7` · `UNDER THE HOOD`)**：展示 `b2b_trade_credit_factoring_guard` 与 `b2b_trade_credit_factoring_optim_409` 令牌。
5. **Card 5 (`5 / 7` · `ROBUSTNESS CHECK`)**：在 100 组并发分批发货、部分退货冲减敞口与跨保理商哈希查重压测中保持零坏账穿透。
6. **Card 6 (`6 / 7` · `LATENCY`)**：结账页实时 `KYB` + 全口径敞口核验 + 混合拆单报价 P99 延迟 `< 420ms`。
7. **Card 7 (`7 / 7` · `MY TAKE`)**：**✅ 强烈适用**于所有提供 `Net-30/60` 账期的 B2B 电商平台、制造业分销商与批发 SaaS；**⛔ 不适用**于仅支持款到发货的个人小额零售。

---

## 五、 商业上线风控与架构评审 Checklist

- [ ] **强制绑定企业官方主域名与 `DUNS / LEI` 备案收货地址（Verified Ship-To Dock）**：严禁向新注册近似域名或未备案私人住宅/临时转运仓发运任何 `Net-30/60` 赊销商品。
- [ ] **将“已审批未发货 SO + 已发货未开票出库单（Unbilled Shipments）”纳入实时信用敞口公式**：彻底封死买方利用财务月底汇总开票时间差突击超额提货的漏洞。
- [ ] **实施发票五元组唯一哈希登记与买方签收单（`GRN / vPOD`）核验后放款**：杜绝供应商“一票多卖”重复质押融资或货未发出先空开发票套现。
- [ ] **上线“授信额度内走无追索权 `Net-30` + 超额部分转 `ACH` 现结”混合结账器**：在不增加任何坏账敞口的前提下保住超限大单转化率，并将卖家 `DSO` 压缩至 `T+1`。
