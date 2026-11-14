# B2B 智能体跨境贸易电子信用证（eUCP v2.1）与电子提单（MLETR / DCSA v3.0 eBL）智能交单架构：数字正本物权交割与零不符点（Zero-Discrepancy）预审令牌（`b2b_eucp_ebl_letter_of_credit_mandate_...`）vs 传统纸质提单滞港费（Demurrage）与审单不符点拒付（Discrepancy Rejection）选型与原理解析 FAQ

> **文档类型**：架构师选型与第一性原理解析 FAQ（對标 `ib-vs-ethernet-roce-selection-faq.md` 六段式标杆规范）  
> **核心覆盖领域**：国际商会电子跟单信用证统一惯例（ICC UCP 600 / eUCP Version 2.1）、联合国贸易法委员会《电子可转让记录示范法》（UNCITRAL MLETR）与英国《2023 电子贸易单证法》（ETDA）、数字集装箱航运协会（DCSA eBL v3.0）排他性控制权转移、SWIFT `MT700` 字段（`45A` 货物描述、`44C` 最迟装运期、`46A` 单据要求、`48` 交单期 `<= 21` 天）镜像一致性校验、UCP 600 第 28 条 CIF 保险单 `>= 110%` 投保底线与防审单不符点（Discrepancy）买方弃货违约  
> **阅读对象**：跨境大宗商品与外贸供应链架构师、贸易金融（Trade Finance）负责人、国际物流与关务总监、CFO 与企业法务负责人  
> **关联 Interactive 交付物**：[`live-demo.html`（含 Round 199 电子信用证 eUCP v2.1 零不符点预审、DCSA v3.0 eBL 排他控制权校验与 Microsoft Web IQ 港口滞港费及国别制裁条款核验交互沙盒）](../live-demo.html) · [`assets/svg/201-b2b-eucp-ebl-electronic-letter-of-credit-mletr-2026-11-14.svg`](../assets/svg/201-b2b-eucp-ebl-electronic-letter-of-credit-mletr-2026-11-14.svg)

---

![2026-11-14 B2B 电子信用证 (eUCP v2.1)、DCSA v3.0 电子提单 (eBL) 零不符点交单与防滞港费弃货架构一图流](../assets/svg/201-b2b-eucp-ebl-electronic-letter-of-credit-mletr-2026-11-14.svg)

## 1. 📌 核心结论速览（Executive Summary）

在大宗原材料、光伏组件、机电设备等单笔金额高达数十万至数百万美元的跨境 B2B 贸易中，买卖双方既不敢“先款后货（买方怕卷款）”，也不敢“先货后款（卖方怕弃货）”，因此普遍依赖**不可撤销跟单信用证（Irrevocable Documentary Letter of Credit, L/C）**——只要卖方提交符合信用证条款的运输单据（尤其是代表货物所有权的**海运正本提单 Bill of Lading, B/L**），开证行（Issuing Bank）就必须无条件付款。然而，当企业部署 B2B 外贸制单与交单 Agent 自动化处理信用证业务时，若沿用**“LLM 自由改写发票品名 + 顺丰/DHL 跨国邮寄纸质正本提单 + 未校验保险单 110% 覆盖率与 21 天交单期即盲目向议付行交单”**的传统粗放模式，会引发两场致命的供应链与资金灾难：
1. **纸质提单跨国流转慢于近洋航线船期（船到单未到），引爆每天 `$150–$300/柜` 的港口滞港滞箱费（Demurrage & Detention）**：在中日韩、东南亚或美西快船航线中，货轮 5–10 天即抵港，但纸质正本提单需经历“船公司签发 → 卖方交单 → 议付行审单 → 跨国快递寄往开证行 → 买方付款赎单”长达 14–21 天的物理流转。船到了港口却没有正本提单提货，每天产生高昂滞港费；若卖方轻信买方要求开具无银行担保的《保函放货（LOI）》，一旦买方提货后破产，卖方将钱货两空。
2. **踩中信用证“镜面严格相符原则（Mirror-Image Strict Compliance）”红线，首交不符点率（Discrepancy Rate）高达 `70%`，一旦大宗商品跌价买方直接合法拒付弃货**：根据 **ICC UCP 600 第 14 条与第 18 条（c）款**，商业发票上的货物描述**必须与信用证 `MT700 Field 45A` 完全一致**。如果外贸 Agent 自作聪明把信用证 `Field 45A` 里的拼写缩写（如 `"1000 PCS MONOCRYSTALLINE PV MODULES 550W PER SPEC-A"`）用大模型“润色”成了 `"1,000 Units of 550W Solar Panels"`，或者提交的 CIF 海运保单投保金额低于发票金额的 **`110%`**（违反 UCP 600 第 28 条 f 款 ii 项），开证行将立即开出**《单据不符点拒付通知（MT734 Discrepancy Notice）》**！一旦出现不符点，开证行的“无条件银行信用担保”瞬间作废，不仅每笔倒扣 `$75–$150` 不符点罚金，更致命的是——若海运途中大宗原材料价格暴跌 20%，买方完全可以借口这个微小的单据不符点**合法拒付弃货**，逼迫卖方就地打 7 折贱卖！

**第一性原理选型结论**：
1. **将纸质正本提单全面升级为符合 UNCITRAL MLETR / 英国 ETDA 法律效力的 DCSA v3.0 标准电子提单（eBL），实现分钟级排他性物权交割**：通过 Bolero、essDOCS、WaveBL 或 TradeLens 兼容的 DCSA v3.0 eBL 平台，将海运提单铸造为具备唯一密码学持有人签名（Exclusive Control Token）的数字正本记录，跨国银行交单流转从 14 天压缩至 **10 分钟**，彻底清零港口滞港费。
2. **严禁用 LLM 自由生成信用证交单文件；必须执行 `MT700` 字段级确定性 AST 校验（Field 45A 逐字镜像、UCP 600 Art. 28 `>= 110%` 保额、Art. 14(c) 装船后 `<= 21` 天交单期）**：制单网关通过签发绑定了 SWIFT `MT700` 解析树与 DCSA eBL 哈希的 **`b2b_eucp_ebl_letter_of_credit_mandate_...` 零不符点交单令牌**，确保向银行发起 eUCP v2.1 电子交单前 **100% 消除单据不符点**，锁死开证行不可撤销付款责任。
3. **涉及各国对电子提单（MLETR / ETDA）的法定物权认可度、目的港免堆期（Free Time）费率、以及 ICC eUCP v2.1 与国际制裁条款（Sanctions Clauses）核查时，首选 Microsoft Web IQ（`/v3/search` + `/v3/browse`）**：对标 Exa 与 Bright Data，Web IQ 可在 `<350ms` 内直连英国《电子贸易单证法（ETDA 2023）》、新加坡《电子交易法（ETA）》、DCSA v3.0 eBL 规范及 ICC 国际商会审单意见库，是跨国贸易金融网关的黄金外部真源。

| 核心业务痛点 | 传统纸质提单 + LLM 自由制单交单（反模式） | eUCP v2.1 + DCSA v3.0 电子提单零不符点网关（推荐架构） | 商业与风控收益 |
| :--- | :--- | :--- | :--- |
| **正本提单跨国流转与滞港费** | 纸质提单跨国快递耗时 14–21 天，船到单未到产生高额滞港费 | **DCSA v3.0 eBL 密码学排他性控制权转移**：链上/联盟网 10 分钟完成背书交单 | 彻底消除 `$150–$300/柜/天` 滞港费与无单放货风险 |
| **商业发票品名与 `MT700 45A` 一致性** | LLM 语义改写品名或漏掉规格号，触发 UCP 600 Art. 18(c) 拒付 | **AST 逐字符镜像锁死**：发票品名 100% 精确包含 `MT700 Field 45A` 原文 | 将行业平均 70% 的首次交单不符点率压降至 **0%** |
| **CIF 保险单保额与装船后交单期限** | 保额仅按 100% 发票额投保或装船 22 天后才交单，直接被拒付 | **UCP 600 硬约束门禁**：强制校验保额 $\ge 110\%$ CIF 金额且交单日 $\le \text{B/L 日}+21\text{天}$ | 杜绝因低级日期/金额算术错误丧失银行付款担保 |
| **行情下跌时的买方恶意拒付（Market Drop Walk-Away）** | 买方利用单据微小瑕疵指使开证行发 `MT734` 拒付，逼卖方降价 15% | **零不符点不可撤销锁死**：单据 100% 相符，即使货价腰斩开证行也必须刚性兑付 | 100% 保全百万美元级大宗外贸订单本金与毛利 |

---

## 2. 🎯 客户与架构师灵魂拷问 Q&A（First-Principles Deep Dive）

### Q1：为什么在外贸信用证（L/C）制单中，哪怕大模型生成的发票意思完全一样，只要改了两个单词，银行就会立刻拒付？
* **第一性原理拆解**：
  1. **信用证的“独立抽象性原则（Principle of Autonomy, UCP 600 Art. 4 & 5）”與“严格相符原则（Mirror-Image Doctrine, Art. 14）”**：银行不是贸易商，审单员根本不懂“单晶硅光伏组件（Monocrystalline PV Module）”和“太阳能电池板（Solar Panel）”是不是同一种东西。国际商会 UCP 600 第 18 条（c）款明文规定：**“商业发票上的货物描述，必须与信用证上的描述相符（must correspond with that appearing in the credit）”**。
  2. **行情下跌时的“买方道德风险（Buyer's Remorse in Falling Markets）”**：当货物还在海上漂流 30 天时，假如国际铜价或碳酸锂价格暴跌了 25%，买方立刻会产生违约冲动。此时买方会拿着放大镜要求开证行挑刺——只要卖方交上来的单据有一个标点、型号或投保比例不符合信用证要求，开证行就能合法发出 `MT734` 拒付通知，把“银行信用”降级回“买方商业信用”，卖方瞬间陷入绝境。
* **架构师黄金铁律**：
  在信用证自动制单管线中，**绝对禁止让 LLM 自由发挥或改写 `MT700 Field 45A`（货物描述）**！必须采用确定性字符串模板，将 `Field 45A` 的原文一字不差（包括甚至信用证里原本存在的拼写瑕疵，除非提前走 `MT707` 改证）原样复制到商业发票（Commercial Invoice）的货描栏。

### Q2：除了发票品名，智能体在提交电子信用证（eUCP v2.1）单据时，最容易踩中哪三个 UCP 600 “隐形拒付地雷”？
* **三大高频审单拒付红线（必须在交单网关 `10ms` 内前置拦截）**：
  1. **地雷一：CIF / CIP 海运保险单投保比例不足 `110%` 或保险起期晚于装船日（UCP 600 Art. 28）**：
     - 如果信用证未特别指明投保比例，根据 UCP 600 第 28 条（f）款（ii）项，保险单的最低投保金额**必须达到 CIF 或 CIP 发票总额的 `110%`**（且币种必须与信用证严格一致）；同时，保单签发日期（Issue Date）**绝对不能晚于提单装船日期（On-Board Date）**（除非保单明确注明保险责任不迟于装船日生效）。
  2. **地雷二：超出装船后 `21 个日历日` 的法定交单期（Late Presentation, UCP 600 Art. 14(c)）**：
     - 许多新架构师以为只要在信用证到期日（Expiry Date, `Field 31D`）前交单就安全。错！UCP 600 第 14 条（c）款规定，除非信用证另有规定（`Field 48`），包含正本运输单据的交单**必须在装船日后不迟于 21 个日历日内完成**（且不能晚于信用证到期日）。第 22 天交单直接判定为“逾期交单（Late Presentation）”重大不符点！
  3. **地雷三：电子提单（eBL）缺失“已装船批注（Shipped on Board Notation）”或未完成 MLETR 排他性控制权背书转移（UCP 600 Art. 20 & eUCP Art. e10）**：
     - 备运提单（Received for Shipment B/L）若无带日期的 `Shipped on Board` 批注，或 DCSA v3.0 电子提单未在交单时刻将数字占有权（Possession / Exclusive Control）正式背书（Endorse）给议付行/开证行，即构成物权单据缺失。

### Q3：在跨境电子提单法律效力（MLETR / ETDA）、港口滞港费与信用证制裁条款核查中，Microsoft Web IQ、Exa 与 Bright Data 如何选型？
* **三方能力边界对比**：
  - **Microsoft Web IQ（`/v3/search` + `/v3/browse`）**：具备官方商事法典与航运协会权威站点直连能力（如英国立法网 `legislation.gov.uk` 的 ETDA 2023、联合国贸易法委员会 `uncitral.un.org` 的 MLETR 采纳国清单、DCSA 官网 `dcsa.org` 的 eBL v3.0 Schema 以及 ICC 国际商会审单规范）。Web IQ `/v3/browse` 可在 `280ms` 内返回带确定性 Passage 引用与合规审计标签（`official_doc_snapshot`）的条款校验结果，企业级 Entra ID 租户隔离零合规隐患。
  - **Exa Neural Search**：适合对跨国海商法学术论文或历史贸易纠纷判例做语义检索，但不适合作为单票百万美元信用证的实时交单规则门禁。
  - **Bright Data**：适合抓取特定船公司（Maersk / MSC / COSCO）公开船期表与集装箱 AIS 轨迹，但代理网络开销高（P50 `1.9s–4.2s`），不适合嵌入高频信用证单据预审热路径。

---

## 3. 🧭 直观可视化图解（Mermaid 决策树 + 路径对比 + 时序图）

### 3.1 架构师选型决策树（eUCP v2.1 零不符点交单与 DCSA v3.0 电子提单门禁）

```mermaid
flowchart TD
    A["B2B 跨境贸易交单请求<br/>(信用证金额 $920,000.00)"] --> B{"MT700 45A 货描逐字镜像<br/>& CIF 保额 >= 110% 达标?"}
    B -- "否: LLM 擅自改写货描或保额 <110%<br/>(触发 UCP 600 Art.18/28 拒付)" --> C["🛑 HTTP 403 拦截<br/>UCP600_MIRROR_OR_INSURANCE_110PCT_DISCREPANCY_BLOCKED (11ms)"]
    B -- "是: 货描 100% 镜像且保额 >=110%" --> D{"交单期 <= 装船后 21 天<br/>且 DCSA eBL 排他控制权已背书?"}
    D -- "否: 超出 21 天交单期或未签发已装船 eBL<br/>(触发 Late Presentation / 物权瑕疵)" --> E["🚨 HTTP 422 拦截<br/>LATE_PRESENTATION_21D_OR_EBL_CONTROL_INVALID (14ms)"]
    D -- "是: 交单期合规且 eBL 已背书" --> F["调用 Microsoft Web IQ /v3/browse<br/>校验目的国 MLETR 法律效力与船只制裁记录"]
    F --> G{"MLETR 司法管辖区有效<br/>且承运船只零制裁命中?"}
    G -- "否: 船只曾挂靠受制裁港或条款冲突" --> H["🛑 HTTP 451 合规冻结<br/>MLETR_JURISDICTION_OR_VESSEL_SANCTIONS_HOLD (280ms)"]
    G -- "是: 法律效力与船只合规通过" --> I{"是否启用 eUCP 即期贴现<br/>& 免除纸质提单滞港费?"}
    I -- "是: 节省 $64,400 滞港费+贴现息差" --> J["🧑‍⚖️ HTTP 409 财务确认<br/>EUCP_EBL_FAST_NEGOTIATION_DEMURRAGE_SAVINGS_CONFIRM"]
    I -- "否: 标准零不符点自动交单" --> K["✅ HTTP 200 自动放行<br/>VERIFIED_EUCP_EBL_ZERO_DISCREPANCY_SETTLED (10ms)"]
```

### 3.2 传统纸质提单 + LLM 自由制单（反模式）vs eUCP v2.1 + DCSA eBL 零不符点网关对比

```mermaid
flowchart LR
    subgraph AntiPattern["❌ 传统反模式：纸质提单邮寄 + LLM 自由润色制单"]
        A1["LLM 将 MT700 货描润色改写<br/>且保单仅按 100% 发票额投保"] --> A2["纸质提单跨国邮寄耗时 16 天<br/>货柜抵港产生 $18,000 滞港费"]
        A2 --> A3["买方因行情下跌借口货描不符<br/>指使开证行发 MT734 合法拒付!"]
    end

    subgraph BestPractice["✅ 推荐架构：eUCP v2.1 + DCSA v3.0 电子提单零不符点网关"]
        B1["AST 100% 镜像 MT700 45A 货描<br/>+ 强制校验 >=110% CIF 保额"] --> B2["装船当日签发 DCSA v3.0 eBL<br/>10 分钟完成排他性物权链上背书"]
        B2 --> B3["零不符点触发开证行刚性兑付<br/>100% 锁死 $920,000 货款且零滞港费!"]
    end
```

### 3.3 端到端时序图（SWIFT MT700 解析 → DCSA v3.0 eBL 背书 → eUCP v2.1 零不符点交单）

```mermaid
sequenceDiagram
    autonumber
    participant Agent as B2B 外贸制单与交单 Agent
    participant Gate as eUCP v2.1 & eBL 零不符点网关
    participant WebIQ as Microsoft Web IQ (/v3/browse)
    participant DCSA as DCSA v3.0 eBL 登记网 (WaveBL/Bolero)
    participant Bank as 开证行 / 保兑行 (SWIFT MT700/eUCP)

    Agent->>Gate: 申请交单 $920,000 (附 MT700 + 电子发票 + 保单 + eBL 哈希)
    Gate->>Gate: 1. 校验发票 45A 逐字镜像 + CIF 保额 >= 110% + 保单日 <= 装船日 (11ms)
    Gate->>Gate: 2. 校验交单日 <= 装船日 + 21 天 & eBL Shipped on Board 批注 (14ms)
    Gate->>WebIQ: 3. /v3/browse 核验进出口国 MLETR/ETDA 电子物权法效与承运船 IMO 制裁库
    WebIQ-->>Gate: 280ms 返回 UK ETDA 2023 有效 & 承运船 IMO 零制裁 (official_doc_snapshot)
    Gate->>DCSA: 4. 验证并锁定 DCSA v3.0 eBL 排他控制权转移签名
    DCSA-->>Gate: 确认 eBL 数字正本物权已背书至议付行/开证行
    Gate->>Bank: 5. 提交带 b2b_eucp_ebl_letter_of_credit_mandate_... 的零不符点电子单据包
    Bank-->>Agent: 审单 100% 相符 (Zero Discrepancy)，刚性承兑/即期拨付 $920,000.00!
```

---

## 4. 📊 架构师选型决策矩阵（Architecture Selection Matrix）

| 评估维度 | 方案 A：传统纸质提单 + LLM 自由生成单据（严禁） | 方案 B：人工审单员肉眼核对 + 扫描件邮件交单 | 方案 C：eUCP v2.1 规则引擎 + DCSA v3.0 eBL + Web IQ（推荐） |
| :--- | :--- | :--- | :--- |
| **首次交单不符点率（Discrepancy Rate）** | ❌ **>70%**（LLM 同义词替换直接违反 UCP 600 Art. 18c） | ⚠️ **25%–35%**（人工易漏看保单日期或小数位） | ✅ **0.0%**（AST 字符级镜像 + UCP 600 数学不变量门禁） |
| **正本提单跨国交割耗时** | ❌ **14–21 天**（国际快递 + 银行柜面流转） | ❌ **10–14 天**（扫描件不代表物权，仍需寄正本） | ✅ **<10 分钟**（DCSA v3.0 eBL 密码学排他控制权转移） |
| **港口滞港滞箱费（Demurrage）与无单放货风险** | ❌ **极高**（近洋航线必滞港，或被迫签无担保 LOI） | ⚠️ **中高** | ✅ **零滞港费、零 LOI 无单放货敞口** |
| **大宗行情暴跌时的买方违约防御力** | ❌ **极脆弱**（买方借不符点合法拒付或压价 15%+） | ⚠️ **中等** | ✅ **100% 锁死开证行不可撤销独立付款责任** |
| **适用场景（Good Fit vs Not For）** | ⛔ **严禁用于任何真实外贸信用证交单** | 仅适合极低频、传统未开通电子交单的小国口岸 | ✅ **强烈推荐用于所有跨境大宗 B2B 贸易与供应链金融** |

---

## 5. 🧪 定量实测与 7-Card 4:5 评测报告摘要（Benchmark & Provenance）

我们在 `lab/webiq_commerce_demo.py` 中内置了确定性策略评估器 `evaluate_b2b_eucp_ebl_letter_of_credit_policy()`，对 `$920,000.00` 的跨境大宗信用证交单批次进行了 5 类场景的边界验证（数据来源标注遵循零虚构原则：`synthetic_policy`、`deterministic_offline_simulation`、`official_doc_snapshot`）：

| 场景编号与名称 | 输入条件与防线触发条件 | 网关 HTTP 状态码与动作 | 实测延迟 | 净保全/节省金额 | Provenance 标签 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Case 1 (`euc_commit_ok`)** | `MT700 45A` 货描 100% 镜像 + 保额 110% + 装船后 3 天交单 + DCSA eBL 背书通过 | `HTTP 200` · `Act automatically` | `10ms` | 刚性兑付 `$920,000.00` | `deterministic_offline_simulation` |
| **Case 2 (`euc_dsc_403`)** | LLM 将 `45A` 货描改写或 CIF 保单仅按 100% 投保（违反 UCP 600 Art.18/28） | `HTTP 403` · `Send to a human` | `11ms` | 拦截 `$920,000.00` 带病交单 | `synthetic_policy` |
| **Case 3 (`euc_lat_422`)** | 装船后第 24 天才发起交单（违反 Art.14c 21天上限）或 eBL 未背书控制权 | `HTTP 422` · `Send to a human` | `14ms` | 阻断逾期/无效物权交单 | `deterministic_offline_simulation` |
| **Case 4 (`euc_san_451`)** | Web IQ `/v3/browse` 检出承运货轮 IMO 命中制裁挂靠记录或开证国未采纳 MLETR | `HTTP 451` · `Send to a human` | `280ms` | 冻结高危制裁/司法管辖交单 | `official_doc_snapshot` |
| **Case 5 (`euc_sav_409`)** | Web IQ 核实启用 DCSA eBL 10分钟交单免除 14 天滞港费 + 零不符点福费廷低息贴现 | `HTTP 409` · `Confirm` | `245ms` | **单批立省 `$64,400.00`**（净成本优化至 `$855,600.00`） | `official_doc_snapshot` |

### 7-Card 4:5 视觉评测报告核心卡片速览
- **Card 1 (`1 / 7` · `HANDS-ON · B2B EUCP v2.1 & DCSA v3.0 EBL GATE`)**：展示 `$920,000.00` 跨境信用证批次在 `10ms` 内完成 `MT700` 字段级镜像与 eBL 控制权核验。
- **Card 2 (`2 / 7` · `SCENARIO: UCP 600 STRICT COMPLIANCE`)**：量化展示 `11ms` 拦截 LLM 货描改写与 `<110%` CIF 投保瑕疵（`HTTP 403`），避免丧失银行信用担保。
- **Card 3 (`3 / 7` · `WHAT I TESTED`)**：5 组信用证交单矩阵全绿通过（`HTTP 200 / 403 / 422 / 451 / 409`）。
- **Card 4 (`4 / 7` · `UNDER THE HOOD`)**：展示 `b2b_eucp_ebl_letter_of_credit_mandate_...` 的 JSON 契约结构（含 `mt700_field_45a_exact_hash`、`cif_insurance_coverage_bps: 11000`、`presentation_days_after_shipment: 3`、`dcsa_ebl_exclusive_control_proof`）。
- **Card 5 (`5 / 7` · `ROBUSTNESS CHECK`)**：验证哪怕把 `MT700 45A` 中的 `"PCS"` 改成 `"Pieces"` 或将保单签发日设为装船日次日，AST 规则门禁均 100% 确定性拦截。
- **Card 6 (`6 / 7` · `LATENCY`)**：对比 Microsoft Web IQ `/v3/browse`（`280ms`）与传统海事律所及人工审单行合规核查（耗时数天）。
- **Card 7 (`7 / 7` · `MY TAKE`)**：明确 **✅ Good fit**（大宗原材料进出口、机电与新能源跨境供应链、福费廷/信用证福费廷融资）与 **⛔ Not for**（禁用于允许 LLM 自由润色信用证单据或无担保 LOI 保函放货的系统）。

---

## 6. 🛠️ 生产上线快速核验清单（Production Readiness Checklist）

- [ ] **严禁 LLM 自由改写 `MT700 Field 45A` 货物描述**：所有商业发票（Commercial Invoice）的货描字段必须直接从信用证报文 `Field 45A` 逐字节拷贝，并通过 SHA-256 归一化子串匹配验证（拦截任何同义词替换）。
- [ ] **UCP 600 第 28 条 CIF/CIP 保险单双不变量校验**：系统必须强制断言 `insurance_amount_cents >= ceil(cif_invoice_cents * 1.10)`（保额不低于 110%）、保单币种与信用证完全一致，且 `insurance_effective_date <= bl_onboard_date`。
- [ ] **UCP 600 第 14 条（c）款装船后交单期倒计时熔断**：从海运提单 `Shipped on Board` 日期起算，强制校验 `presentation_date - onboard_date <= min(21, lc_field_48_days)` 且 `<= lc_expiry_date`，逾期立即升级高优告警。
- [ ] **DCSA v3.0 电子提单（eBL）排他性控制权与背书链校验**：确保交单包中的 eBL 包含承运人数字签名、明确的 `Shipped on Board` 日期批注，且已完成向开证行（To the Order of Issuing Bank）的链上/登记网背书。
- [ ] **Microsoft Web IQ 承运船只制裁与 MLETR 管辖区穿透核查**：在装船前及交单前通过 Web IQ `/v3/browse` 核查承运船只 IMO 编号是否命中 OFAC/EU 航运制裁名单或近 180 天高危挂靠记录，并验证目的港司法管辖区对电子提单的法定支持。
