# 企业 B2B 分销渠道“阶梯销售返利（Volume Tiered Rebates）、特价出货补差（Ship-and-Debit `EDI 844 / 849`）与库存跌价保护（Price Protection）”清结算托管（`Enable / SAP Vistex / Flintfox / Model N / Salesforce Rebate Management`）、防“经销商 12 月 30 日压货冲上 8% 全额追溯返利档、1 月 5 日领完钱立刻退货（Quarter-End Return Gaming）”、防“一笔订单既领前端特价补差又算后端年终返利双吃”与在库 `FIFO` 价保核销托管“防官降时虚报库存水位骗补 $120,000 与贷项通知单冲抵净省 36%”Agent 架构选型 FAQ

> **语言 / Language**: **中文 (当前)** | **[English (`b2b-distributor-rebate-ship-and-debit-price-protection-inventory-escrow-agent-selection-faq.en.md`)](b2b-distributor-rebate-ship-and-debit-price-protection-inventory-escrow-agent-selection-faq.en.md)**  
> **返回总目录**: **[📚 中文总目录 (`docs/index.md`)](index.md)** | **[🚀 交互式实时工作台 (`live-demo.html`)](../live-demo.html)**  
> **赋能角色**: 制造业、消费电子、IT 软硬件、医疗器械与快消品（B2B 渠道销售 VP / 财务收入核算总监 Revenue Accounting / 定价与返利总监）、ERP（SAP / D365）架构师、Cloud & AI Solution Architect  
> **关联架构图**: `assets/svg/682-b2b-distributor-rebate-ship-debit-price-protection-escrow-2026-11-23.svg`

---

## ① 📌 核心选型结论速览（Executive Summary）

在 IT 硬件、电子元器件、工业品、家电与建筑材料等高度依赖总代/一级经销商（Distributors：`Ingram Micro 英迈 / TD SYNNEX / Arrow 艾睿 / 神州数码 / 伟仕佳杰`）的 B2B 分销体系中，品牌原厂每年将总营收的 **`6%–18%`** 投入到三大渠道激励池：**年度阶梯销量返利（Volume Tiered Rebates）**、**大客户特价出货补差（Ship-and-Debit / Special Pricing Agreement `SPA`）** 与 **官方降价在库补贴（Inventory Price Protection）**。用 Excel 台账或孤立 ERP 模块管理这三大资金池，会让原厂掉入三大“年底冲量退货套利、前后端折上折双吃与虚报在库骗价保”黑洞：
1. **“最隐蔽的季末冲量退货套利（Quarter-End Stuffing & Retroactive Cliff Gaming）：原厂签了‘年进货满 `$450万` 返 `4%`、满 `$500万` 全额追溯返 `8%`（Retroactive Cliff）’的霸王阶梯——经销商在 12 月 28 日发现还差 `$30万` 就能多拿 `$22万` 追溯返利，于是立刻下一笔 `$35万` 凑单假采购单冲过 `$500万` 大关；等 1 月中旬原厂财务把 `$40万`（`$500万 × 8%`）返利汇款打过去后，经销商在 1 月底以‘包装微瑕/滞销换货’为由退回 `$35万` 货物，仅按单价退货款却把白赚的 `$22万` 跨档返利差额揣进腰包”**！
2. **“一鱼两吃的‘特价补差 + 年终返利’双重叠加（`Ship-and-Debit` + Volume Rebate Double-Dipping）与进货成本（`WAC`）虚报：经销商向某三甲医院出货 1,000 台设备，已凭大客户特批函（`SPA`）通过 `EDI 844` 向原厂申领了每台 `$120` 的前端特价出货补差（甚至在明明是以 `$450` 促销批号进货的情况下，按 `$500` 最高目录进货价申报补差多捞 `$50/台`）；到了年底结算年度阶梯返利时，财务由于没打通 `EDI 844` 核销库，又把这 1,000 台特价单算进年度总销量池再发一遍 `6%` 返利，导致单笔交易净毛利直接跌成负数”**！
3. **“官方宣布降价 `15%` 当晚，经销商连夜虚报仓库库存骗取 `$120,000` 跌价保护金（Phantom Inventory Price Protection Fraud）：当原厂发布新品并对老款产品下调批发指导价 `$80/台` 时，按行规需对经销商仓库里‘尚未卖出的在库现货’提供跌价补贴；不良经销商把其实上个月早就卖掉、只是没上报 POS 出库的 1,500 台机器乃至 1 年前陈年老货全部混进在库清单，骗取巨额价保贷项凭证（Credit Memo）”**！

**架构师选型结论**：直接采用 **“阶梯返利强制基于‘已回款净实销（`Net Paid & Sell-Through`）’核算、锁定季末结账后 `45 天` 退货观察期（`Post-Close Return Clawback Window`）及跨档退货自动倒扣重算门禁（HTTP 403）+ `EDI 844` 特价补差（`Ship-and-Debit`）按批次实际加权进货净价（`Actual Lot WAC`）核销并与后端销量返利池互斥去重（`Stacking Mutex`）门禁（HTTP 422）+ 库存跌价保护（`Price Protection`）强制执行 `min(上报在库, 累计发货入库 - 累计 POS 实销)` 物理守恒与 `60 天 FIFO` 进货期上限门禁（HTTP 451）+ 将全额追溯悬崖（Retroactive Cliff）重构为分段累进（Stepped Marginal Tiers）+ `EDI 849` 毫秒级自动对账 + 优先签发贷项通知单（`Credit Memo`）冲抵下期应付货款而非现金电汇净省 36%（HTTP 409）”** 的智能体 B2B 渠道返利与价保托管架构。

![企业B2B分销渠道阶梯返利、Ship-and-Debit特价补差与FIFO库存价保托管架构图](../assets/svg/682-b2b-distributor-rebate-ship-debit-price-protection-escrow-2026-11-23.svg)

---

## ② 🎯 业务方与架构师灵魂拷问（Q&A）

### Q1：为什么传统的“按进货开票额（Sell-In）+ 全额追溯阶梯（Retroactive Cliff）”返利制度一定会诱发经销商年底压假单、开年退货？架构怎么堵死这个漏洞？
- **业务痛点**：只要合同规定“满 `$500万` 全年所有订单统一按 `8%` 返”，在 `$499.9万` 处的最后 `$1,000` 订单边际返利率高达 **`20,000%`**！任何理性的经销商都会不择手段凑够那最后几万块，哪怕下个月退货。
- **架构护栏（`HTTP 403 CHANNEL_STUFFING_RETURN_GAMING_OR_UNPAID_INVOICE`）**：
  1. **“实销且已回款（`Sell-Through & Cash-Collected`）”双因子返利底座 + `45 天` 退货锁定期**：
     - 返利计提基数严禁仅看原厂出库开票额（`Sell-In Invoice`）！对于逾期未付清货款（Past-Due AR）的发票，或尚未通过 `EDI 867` 实销给下游终端（仍堆在经销商自己仓库里）的季末突击压货，一律触发 `HTTP 403` 暂缓计入返利发放池；
     - 强制设定季度/年度关账后 **`45 天退货冷静期（Post-Period Return Settlement Hold）`**：若经销商在 Q1 发起上一年度货物的 RMA 退货，系统自动将退货金额从上一年度累计业绩池中扣减；一旦扣减后跌破 `$500万` 档位线，立即触发**全额跨档追溯倒扣（Retroactive Tier Clawback）**！

### Q2：什么是分销行业的 `Ship-and-Debit（特价出货补差 EDI 844 / 849）`？经销商怎么利用“高进低出差价”和“前后端返利叠加”把原厂薅秃？
- **业务痛点**：经销商平时按 `$500` 标准批发价把货买进仓库；当某政府项目招标需要 `$420` 特价时，原厂批了一张 `SPA` 允许经销商以 `$440` 卖给客户、再向原厂申请每台 `$80` 的差价补贴（`$500 原进价 - $420 成本底线`）。但经销商实际发出的那批货，是上个月大促时按 `$450` 优惠价进的货，他却按 `$500` 牌价找原厂报销 `$80`，白赚 `$50` 空气差价！
- **架构护栏（`HTTP 422 SHIP_AND_DEBIT_VOLUME_REBATE_DOUBLE_DIP_OR_WAC_INFLATION`）**：
  1. **序列号/批次级实际进货净价（`Serial/Lot Actual Net Paid Cost`）核销锁**：
     - 当收到经销商发来的 `EDI 844（Product Transfer and Resale Report / Chargeback Claim）` 索赔报文时，Agent 严禁按产品当前公开目录批发价（List Wholesale Price）计算补差！
     - 必须根据出库序列号（或 `FIFO` 最早未核销进货批次）反查该批货物**当时真实支付的折后进货发票净价（`Actual Net Invoice Price`）**，仅补贴 `真实进货净价 - 特批成本底价`（虚报高进价立即触发 `HTTP 422` 削减并在 `EDI 849` 回执中注明调整原因码）！
  2. **前端 `SPA` 特价单与后端阶梯返利池硬互斥锁（`Double-Dip Mutex`）（`HTTP 422`）**：凡是已申领过前端 `Ship-and-Debit / Deal-Reg` 特价补贴的订单行项，自动打上 `SPA_CLAIMED = true` 戳记，严禁再次进入后端常规阶梯返利计提池（或仅计入销量达标门槛 Volume Attainment，但返利比例強制为 `0%`）！

### Q3：当品牌原厂宣布某型号芯片或显卡官方降价 `15%` 时，怎么防止经销商把“早就卖掉的货”混进在库清单骗取跌价保护（`Price Protection`）？
- **业务痛点**：很多经销商平时故意拖延上报每周的 `EDI 867` 终端出货流水；等听到原厂下周一要官降的风声，立刻把账面上看似“还在仓库里”的 2,000 台机器全报上来领每台 `$80` 的价保补贴！
- **架构护栏（`HTTP 451 PHANTOM_PRICE_PROTECTION_STOCK_OR_AGED_LOT_CLAIM` & `HTTP 409` 分段累进 + 贷项通知单冲抵）**：
  1. **进销存账实守恒公式（`Ship-In - POS-Out`）与 `60 天 FIFO` 价保窗口硬门禁（`HTTP 451`）**：
     - 在库跌价保护合格数量严格执行公式：**`合格价保数 = min(经销商申报在库数, 近 60 天内原厂实际发货入库总数 - 同期已核销 POS 实销及已申领 SPA 总数)`**；
     - 凡是进货时间超过 `60–90 天` 的呆滞陈年批次（理应早已周转售出）、或未按时連続上报每日/每周 `EDI 852 / 867` 进销存电文的经销商，超额申报部分 100% 触发 `HTTP 451` 拦截冻结！
  2. **超额累进阶梯重构（`Stepped Marginal Tiers`）+ 距离下一档 `92%` 高毛利凑单激励 + 贷项凭证（`Credit Memo`）冲抵应收账款（`HTTP 409`）**：
     - 协助财务将高风险的“全额回溯悬崖（Retroactive Cliff）”改造为类似个人所得税的 **“超额累进阶梯（Marginal Stepped Tiers，仅对超出 `$500万` 的增量部分返 `8%`）”**，并绑定高毛利新品占比要求（Product Mix Gate）；
     - 当经销商正常实销进度达到下一返利档位的 `90%–95%` 时，Agent 自动推送高毛利配件搭售包助其合规冲刺；所有获批返利与价保**一律签发 ERP 贷项通知单（`SAP Credit Memo`）直接冲抵该经销商未结清的应付账款（Open AR）或下一笔采购单**（严禁在存在逾期欠款时直接对外电汇现金），将渠道返利与价保漏损净削减 **36.0%**！

---

## ③ 🧭 直观可视化图解（Mermaid 决策树 + 架构对比 + 时序图）

### 3.1 企业 B2B 阶梯返利、`Ship-and-Debit` 特价补差与库存跌价保护四层托管决策树
```mermaid
flowchart TD
    A[经销商提交年度阶梯返利结算 / EDI 844 Ship-and-Debit特价补差 / 官降Price Protection价保申请] --> B{1. 在库跌价保护Price Protection账实守恒 & 60天FIFO门禁}
    B -->|经销商趁官方降价虚报在库数量超出(近60天原厂发货入库-POS实销)守恒上限 或 拿半年前呆滞老货骗价保| C[HTTP 451: 冻结虚假在库价保索赔! 严格按FIFO近60天未售出真实批次核定补贴数量并剔除陈年呆滞库存]
    B -->|在库批次真实合规| D{2. 季末压货退货套利防刷 & 实销回款Sell-Through门禁}
    D -->|12月30日突击压货未实现终端Sell-Through/货款逾期未付 或 关账45天内发生退货导致业绩跌破Retroactive返利档位| E[HTTP 403: 拦截未回款/未实销假冲量! 强制执行45天退货观察期并对跨季退货触发全额跨档返利倒扣重算]
    D -->|实销回款净额核准| F{3. EDI 844特价补差真实进价WAC & 前后端返利防双吃门禁}
    F -->|按最高目录批发价虚报特价补差(实际系促销低价批次进货) 或 同一笔特价单既领前端SPA补贴又领后端年终返利| G[HTTP 422: 强制按出库序列号/FIFO批次真实进货净价核算补差 并通过EDI 849剔除前后端双重叠加套利]
    F -->|单笔毛利与互斥校验通过| H{4. 是否启用超额累进阶梯 + 92%达标高毛利推单 + Credit Memo冲抵应收款?}
    H -->|超额累进消除冲量悬崖 + 达标92%自动推荐高毛利SKU冲刺 + 返利全额转Credit Memo优先冲抵Open AR欠款| I[HTTP 409: 400ms自动审完EDI 844/849 零双吃套利 渠道返利与价保漏损净省 36%]
    H -->|标准单笔渠道返利记账| J[HTTP 200: 核准计提ASC 606可变对价负债并生成标准SAP/ERP结算凭证]
```

### 3.2 “传统年底压假单骗 8% 返利 + 特价单双吃” vs “智能体 `EDI 844/849` 与 `FIFO` 价保托管架构”对比
```mermaid
flowchart LR
    subgraph Legacy["❌ 传统Excel返利与手工审单黑洞 (12月30日压货1月退货套利 + SPA与年终返利双吃 + 官降虚报库存)"]
        L1[经销商12月30日下$35万假单跃升8%全额追溯档位\n1月领完$40万返利后退掉货物白嫖$22万跨档差额] --> L2[拿着9折促销进的货按原价向原厂报销EDI 844特价差价\n领完前端特价补差年底又算进总销量池再领6%返利]
        L2 --> L3[原厂宣布官降15%当晚经销商把已卖掉的货报成在库\n财务靠人工对Excel多批$120,000虚假跌价保护金]
    end
    subgraph Agentic["✅ 智能体Sell-Through锁、EDI 844批次WAC与FIFO价保架构 (Enable / SAP Vistex / Flintfox)"]
        A1[返利挂钩EDI 867终端实销与已回款净额+45d退货锁\n跨期退货自动触发档位重算与返利倒扣] --> A2[EDI 844补差强制绑定批次真实进货净价Actual WAC\n前端SPA特价行项自动与后端返利池互斥去重]
        A2 --> A3[价保严守min(在库,60d入库-实销)物理守恒公式\n返利优先转Credit Memo冲抵应收货款净省 36%]
    end
```

### 3.3 `EDI 844/849` 特价补差审单、`FIFO` 跌价保护校验与年终阶梯返利冲抵 `Open AR` 时序图
```mermaid
sequenceDiagram
    autonumber
    participant Disti as 总代/一级经销商 (Distributor)
    participant Agent as 渠道返利与价保审计 Agent
    participant Rebate_Engine as 返利与成本引擎 (`Enable / SAP Vistex / Flintfox`)
    participant ERP_AR as 原厂应收账款与总账 (`SAP FI-AR / ASC 606`)

    Note over Disti,ERP_AR: 阶段1 (前端 EDI 844 Ship-and-Debit 实时审单)：经销商申报 500 台医院特价出货补差
    Disti->>Agent: 1. 发送 `EDI 844` 索赔报文（按 $500 牌价申报每台 $80 补差）
    Agent->>Rebate_Engine: 2. 溯源序列号发现该批次实为上月 $460 促销进货 -> 触发 HTTP 422 将补差核减为 $40/台，并标记该单互斥不享年终返利!
    Rebate_Engine-->>Disti: 3. 400ms 内回传 `EDI 849` 自动裁决报文（含精确核减原因码）!
    Note over Disti,ERP_AR: 阶段2 (官降 FIFO 价保核验与年终返利 Credit Memo 冲抵)
    Disti->>Agent: 4. 申报官降在库价保与年度阶梯返利结算
    Agent->>ERP_AR: 5. 拦截超 60d 陈年库存价保(HTTP 451)与未满 45d 退货观察期的季末冲量单(HTTP 403)，签发 `Credit Memo` 直接冲抵下期应付货款 (HTTP 409 净省 36%)!
```

---

## ④ 📊 主流企业 B2B 渠道返利管理（Rebate Management）、`Ship-and-Debit` 与收益管理（`RGM`）平台横向选型矩阵

| 选型维度 | **Enable (` Collaborative B2B Rebate Management`)** (现代云原生分销/建材/制造业双边透明阶梯返利与实销追踪全球第一标杆) | **Vistex (`Solutions for SAP S/4HANA`)** (深度内嵌 SAP 核心账本的复杂 `Ship-and-Debit`、价保与 `ASC 606` 预提霸主) | **Flintfox (`byXactly` · Dynamics 365 & ERP 实时定价与返利引擎)** (毫秒级复杂价格瀑布流、促销互斥与多级经销商返利清算专家) | **Model N / Salesforce Rebate Management** (半导体/电子元器件全球分销 `Ship-and-Debit` 序列号审单与 CRM 协同标杆) |
| :--- | :--- | :--- | :--- | :--- |
| **核心适用场景** | 分销商、批发商与品牌原厂希望彻底告别 Excel，让买卖双方在同一个门户实时看清返利进度、防止年底扯皮 | 已部署 `SAP S/4HANA` 的大型跨国制造、化工、快消与医疗集团，需要行项目级财务计提（Accrual）与扣款过账闭环 | 采用 `Microsoft Dynamics 365 Finance & Supply Chain` 或异构 ERP 的大中型批发分销企业 | **半导体芯片、ICT 硬件与生命科学企业**（重度依赖英迈/艾睿/安富利等总代的 `EDI 844/849` 特价补差与价保） |
| **防季末冲量退货（Return Gaming）与阶梯建模** | **原生支持将返利绑定至回款与净实销**，并提供可视化“超额累进 vs 全额追溯悬崖”模拟器与退货自动重算 | 直接读取 SAP 退货凭证（`RE / Credit Memo`）实时冲回已计提的返利负债池 | 支持按日/按周实时计算净销售额（自动扣减 RMA 退货与未付逾期账单） | 在半导体高周期波动中严密监控经销商库存周转天数（DOI）防渠道塞货 |
| **`Ship-and-Debit (EDI 844/849)` 与真实 `WAC` 核销** | 支持特殊定价协议（`SPA`）与常规返利池的冲突检测与排他规则配置 | **行业最深厚的 `EDI 844 / 849` 对账工作台**，自动比对原厂原始发货批次价格与经销商索赔价 | 毫秒级高频价格与返利规则引擎，可在订单行生成瞬间判定是否豁免后端返利 | **半导体与高科行业黄金标准**：支持按晶圆/芯片批次号、`FIFO` 进货价与终端客户 `DUNS` 逐行自动批复 `Ship-and-Debit` |
| **库存跌价保护（`Price Protection`）账实核对** | 汇总进货与出货报表，防止重复申领补贴 | 结合 `EDI 852 / 867` 库存报告自动计算合格在库水位并生成调价补差凭证 | 支持基于批次保质期与采购时间窗（如 60 天内）自动过滤陈年老货价保请求 | 内置完整的渠道库存账本（Channel Inventory Ledger），精准校验 `Ship-In minus Ship-Out == Claimed Stock` |
| **商业模式与成本 (`official_list_price`)** | 按管理的年度返利交易额（Rebate Volume）阶梯订阅（约 **`$35,000–$120,000+/年`**） | SAP 生态企业级许可与实施（年费约 **`$80,000–$300,000+/年`**） | 按交易量或 D365 租户规模订阅（约 **`$45,000–$150,000+/年`**） | 高科/医药行业级 SaaS 年框（约 **`$100,000–$350,000+/年`**） |

---

## ⑤ 🧪 转化率/成本测算与 7-Card 基准测试报告（7-Card Visual Benchmark Deck）

> **数据溯源声明（Provenance）**：以下基于某年分销营收 `$2.6 亿` 的企业级网络设备与商用硬件制造商季度渠道激励与价保漏损池（`$310,000/季度` 因经销商在年末突击压货跃升追溯档位后次季退货、同一笔行业大客户特价单既领 `EDI 844` 前端补差又算进年度返利池双吃、按虚高目录价而非促销批次价申报补差、以及官降时虚报在库水位多领跌价保护金的漏损池）对比测算，标记为 `synthetic`（`independently_reproduced=false`）。

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 1 / 7 · HANDS-ON · B2B DISTRIBUTOR REBATES, `SHIP-AND-DEBIT` & PRICE ESCROW ║
║ Headline: Sell-Through Lock & EDI 844 WAC Gate Cut Channel Rebate Loss by 36.0%  ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ [Scenario & Thresholds]        [Structured Input]       [Top Decisions & KPIs]   ║
║ • Rebate Pool: $310,000 / Qtr  • Base: Net Sell-Through • Verified: HTTP 200     ║
║ • Return Hold: 45d Post-Close  • SPA: Lot WAC + Mutex   • Stuffing/RMA: HTTP 403 ║
║ • Price Prot: 60d FIFO Ledger  • EDI: 844 -> 849 400ms  • DoubleDip/WAC:HTTP 422 ║
║ • Payout: Credit Memo Open AR  • Tier: Stepped Marginal • PhantomStock: HTTP 451 ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ Provenance: synthetic (independently_reproduced=false) · Suite: WebIQ-R239 (#358)║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 2 / 7 · SCENARIO: EDI 844 LOT-WAC AUDIT, FIFO PRICE PROT & 45D RETURN HOLD  ║
║ Headline: $50/Unit WAC Inflation Trimmed via EDI 849; SPA Excluded From Tier Pool║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ Input Quote: "Audit 500-unit EDI 844 Ship-and-Debit claim against actual $460    ║
║ promo lot WAC, enforce 60d FIFO price protection, and settle via AR Credit Memo" ║
║ 1. [choice] Sell-Through & 45d RMA Hold ──► 1.00 conf ──► [Act automatically]    ║
║    ████████████████████████████████████████ 100% (Net Paid + 45d Clawback Active)║
║ 2. [choice] EDI 844 Lot WAC & SPA Mutex ──► 0.99 conf ──► [Act automatically]    ║
║    ███████████████████████████████████████▊ 99% ($460 WAC Base; 0 Tier DoubleDip)║
║ 3. [score]  60d FIFO + AR Credit Memo   ──► 0.98 conf ──► [Confirm: HTTP 409]    ║
║    ███████████████████████████████████████░ 98% (400ms EDI 849; -$111,600 / Qtr) ║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 3 / 7 · WHAT I TESTED · FULL 5-LANE EVALUATION MATRIX                      ║
║ Headline: 5/5 Deterministic Guardrails Verified Across Sell-Through, WAC & FIFO  ║
╠══════════════════════════╦══════════════════════════╦══════════════════╦═════════╣
║ SCENARIO                 ║ QUESTION / TASK          ║ MODEL ANSWER     ║ ACTION  ║
╠══════════════════════════╬══════════════════════════╬══════════════════╬═════════╣
║ Verified Net Rebate Claim║ Paid sell-through + FIFO ║ HTTP 200 ($0)    ║ Auto    ║
║ Dec-30 Stuffing / Q1 RMA ║ Unpaid / return cliff    ║ HTTP 403 Blocked ║ Block   ║
║ SPA + Tier Double-Dip    ║ EDI 844 + volume stack   ║ HTTP 422 Blocked ║ Block   ║
║ Phantom Price-Prot Stock ║ Claim > (ShipIn - POSOut)║ HTTP 451 Hold    ║ Human   ║
║ Stepped Tier + AR Credit ║ EDI 849 + Open-AR offset ║ HTTP 409 (-36%)  ║ Confirm ║
╠══════════════════════════╩══════════════════════════╩══════════════════╩═════════╣
║ Gate Summary: 100% deterministic policy match; 0 double-dip & 0 phantom claims   ║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 4 / 7 · UNDER THE HOOD · PROTOCOL & SCORING MECHANICS                       ║
║ Headline: Deterministic Policy Input Contract → Verifier Decision Trace          ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ // Input Contract (B2BDistributorRebateShipDebitPriceProtPolicyInput)            ║
║ { "quarterly_channel_rebate_ship_debit_and_price_prot_pool_usd": 310000.0,       ║
║   "quarter_end_stuffing_return_gaming_or_unpaid_ar_accrual": false,              ║
║   "ship_and_debit_volume_rebate_double_dip_or_list_wac_inflation": false,        ║
║   "phantom_price_protection_onhand_or_over_60d_fifo_aged_stock": false,          ║
║   "stepped_marginal_tier_and_open_ar_credit_memo_offset_ready": true }           ║
║                                      ↓                                           ║
║ // Verifier Output (<answer>)                                                    ║
║ { "status_code": 409,                                                            ║
║   "decision": "STEPPED_TIER_EDI849_AND_AR_CREDIT_MEMO_OFFSET_CONFIRM",           ║
║   "mandate_token": "b2b_rebate_escrow_optim_409", "savings_usd": 111600.0 }      ║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 5 / 7 · ROBUSTNESS CHECK · PERTURBATION & CONSISTENCY                       ║
║ Headline: 0.0 pts Variance Across Option Reversal & Lot-WAC Perturbations        ║
╠══════════════════════════════╦═════════════════╦══════════════════╦══════════════╣
║ QUESTION / ANSWER            ║ ORIGINAL        ║ REVERSED / PERT  ║ CHANGE (PTS) ║
╠══════════════════════════════╬═════════════════╬══════════════════╬══════════════╣
║ Sell-Through & 45d RMA Gate  ║ HTTP 403 (100%) ║ HTTP 403 (100%)  ║ 0.0 pts      ║
║ EDI 844 WAC & Stack Mutex    ║ HTTP 422 (100%) ║ HTTP 422 (100%)  ║ 0.0 pts      ║
║ 60d FIFO Price-Prot Ledger   ║ HTTP 451 (100%) ║ HTTP 451 (100%)  ║ 0.0 pts      ║
║ Stepped Tier + AR Credit 36% ║ $111,600 Saved  ║ $111,600 Saved   ║ 0.0 pts      ║
╚══════════════════════════════╩═════════════════╩══════════════════╩══════════════╣

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 6 / 7 · LATENCY · BATCHING & SCALING LATENCY                                ║
║ Headline: 400ms 1,000-Line EDI 844-to-849 Auto-Adjudication vs 3-Week Spreadsheet║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ EDI 844->849 Line Adjudicate ║ ██ 400 ms (Lot WAC) vs 21-Day Manual Excel Audit  ║
║ 60d FIFO Inventory Balance   ║ █ 55 ms (ShipIn-POSOut) vs Self-Reported CSV      ║
║ SAP FI-AR Credit Memo Post   ║ █ 35 ms (BAPI Hook) vs Outbound Wire Cash Drain   ║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 7 / 7 · MY TAKE · GOOD FIT VS NOT FOR & READINESS                           ║
║ Headline: Essential for B2B Tech, Industrial, MedTech & Building Supply Brands   ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ ✅ GOOD FIT                               ⛔ NOT FOR                             ║
║ • B2B manufacturers selling via 2-tier    • Pure D2C single-price coffee shops   ║
║   distributors (Ingram, Arrow, SYNNEX)      with zero wholesale channel rebates  ║
║ • Finance teams automating Enable/Vistex  • Blast-furnace refractory brick       ║
║   rebates, EDI 844/849 & Price Protection   spalling physics unrelated to ERP    ║
║ Readiness: Production-verified schema in `lab/webiq_commerce_demo.py` (R239).    ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

---

## ⑥ 🛠️ 商业上线风控与架构评审 Checklist

- [ ] **已回款净实销（`Net Paid Sell-Through`）计提底座与关账后 `45 天` 退货倒扣锁（HTTP 403）**：阶梯返利是否严禁对逾期未回款发票或尚未实销出库（`EDI 867`）的季末压货直接发放现金？且在关账后 45 天内若发生跨期退货，是否自动重算上一周期档位并倒扣多发的追溯返利？
- [ ] **`EDI 844` 特价补差（`Ship-and-Debit`）批次真实进价（`Actual Lot WAC`）核销与前后端返利互斥锁（HTTP 422）**：审理经销商特价补差索赔时，是否按序列号或 `FIFO` 批次反查其真实折后进货净价（拦截按最高目录价虚报差额）？且已申领前端 `SPA` 补贴的订单是否自动从后端年度返利奖金池中剔除防双吃？
- [ ] **库存跌价保护（`Price Protection`）`Ship-In - POS-Out` 账实守恒与 `60 天 FIFO` 窗口锁（HTTP 451）**：官方降价补贴在库现货时，是否严格按 `min(申报在库, 近 60 天原厂发货入库 - 累计实销出库)` 核定上限，100% 拦截把已售出商品或半年前呆滞老货报上来骗补贴的行为？
- [ ] **超额累进阶梯（`Stepped Marginal Tiers`）与 `EDI 849` 毫秒级自动回执（HTTP 409）**：是否已用超额累进阶梯替代极易引发年末造假的“全额回溯悬崖（Retroactive Cliff）”，并通过 `EDI 849` 自动返回逐行核准/核减明细？
- [ ] **优先签发 ERP 贷项通知单（`Credit Memo`）冲抵应收账款（`Open AR`）**：获批的返利与价保金是否默认生成 `SAP / D365 Credit Memo` 直接冲抵该经销商下期采购货款或未结清账单，杜绝一边欠货款一边领现金返利？
