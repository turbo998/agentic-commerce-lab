# 智能体企业司库现金归集（`Corporate Treasury Cash-Sweep`）、`FDIC` 跨行分片联保与税损收割防“洗售（`IRC § 1091 61-Day Wash-Sale`）”清算架构：跨券商账户 61 天同质标的互斥锁、单行 `<= $250k` 存款保险自动拆单与 7 日工资流动性底线令牌（`agentic_corporate_treasury_cash_sweep_wash_sale_fdic_mandate_...`）vs 传统多 Agent 反向买卖触发税务局洗售拒抵、单家银行超额裸存挤兑风险与发薪日流动性穿仓选型与原理解析 FAQ

> **核心摘要（TL;DR）**  
> 在科技企业与家族办公室自动化司库现金管理及量化税损收割（`Autonomous Corporate Treasury Cash-Sweep & Tax-Loss Harvesting`，`SEC Rule 2a-7 / IRC § 1091 / FDIC ICS`，`$950,000/批次`）中，如果让多个理财/司库子 Agent 各自独立在券商和银行账户间调拨闲置资金、买卖国债 ETF 或货币基金，会引爆三大隐蔽却致命的财务风险：**为什么绝对不能让两个投资子 Agent 各自独立做“税损收割（Tax-Loss Harvesting）”，也不能把几百万美元运营资金直接存在单一商业银行的普通活期账户里或全仓买进定期理财？** 第一，美国国税局（`IRS`）《国内税收法典第 1091 条（`IRC § 1091 Wash-Sale Rule`）》规定：在卖出亏损证券的前 30 天至后 30 天（合计 **61 天对称窗口**）内，只要同一纳税主体（含旗下所有关联子账户、甚至自动股息再投资计划 `DRIP`）买回了“实质相同（Substantially Identical）”的证券或期权，该笔亏损抵税资格 **100% 当场作废**！现实中常出现 Agent A 在摩根士丹利账户卖掉亏损标普 ETF 准备抵税，3 天后 Agent B 在盈透证券账户触发定投又买了回来，导致年底报税时数万美元抵税额被 IRS 全部驳回并加收罚息；第二，单一银行的美国联邦存款保险（`FDIC`）上限仅为 **`$250,000/储户`**（硅谷银行 SVB 危机血泪教训），若未通过 `IntraFi ICS` 跨行网络将大额资金拆分为每片 `< $250,000` 或转入 `SEC Rule 2a-7` 国债货币市场基金（Government MMF），一旦中小银行暴雷将面临无保险敞口冻结；第三，若司库 AI 为多赚 `30 bps` 收益把周五要发工资的钱扫入 `T+1 / T+2` 交收资产，发薪日早上将触发零余额账户（`ZBA`）透支违约。生产级架构必须采用 **`agentic_corporate_treasury_cash_sweep_wash_sale_fdic_mandate_2026_11_15` 跨托管行 61 天 `CUSIP` 洗售互斥锁 + `FDIC <= $250k` 自动分片与 7 日刚性付现水位引擎 + Microsoft Web IQ `SEC Rule 2a-7` 货币基金周流动性与银行一级资本核验网关**：在 **11ms** 内拦截 61 天跨户洗售与单行无保险超额裸存（`HTTP 403`），在 **14ms** 内阻断发薪日流动性错配透支（`HTTP 422`），并由 **Microsoft Web IQ** 280ms 穿透核验货币基金 `>= 50%` 周高流资产底线（`HTTP 451`）。

---

## 📌 一、 核心结论速览（Executive Summary）

1. **跨托管账户 `IRC § 1091` 61 天对称洗售互斥锁（`Cross-Custodian Wash-Sale Lock`）与 `FDIC <= $250,000` 自动拆单门禁**：
   - **61 天全局 `CUSIP` 冷却锁**：网关维护企业同一税号（`EIN / TIN`）下全部券商、托管行与子账户的统一交易图谱。任何触发税损收割（Tax-Loss Harvesting）卖出的标的及其高相关性同质替代簇（如追踪同一指数的不同发行商 ETF），在 `[-30 天, +30 天]` 共 **61 个日历日**内自动加入全局禁买黑名单，并强制暂停该标的的自动股息再投资（`DRIP`）。
   - **单行 `$250k FDIC` 风险敞口硬顶**：严禁在单一商业银行留存超过 `$250,000` 的无担保活期存款；超额头寸必须自动通过 `IntraFi ICS / Reich & Tang` 拆分为每家成员银行 `<= $245,000`（留出利息空间）或转入国债逆回购/国债货币基金。违背上述任一规则，网关在 **11ms** 内硬拦截（`HTTP 403 IRC_1091_61DAY_WASH_SALE_VIOLATION_OR_UNINSURED_SINGLE_BANK_CONCENTRATION_BLOCKED`）。
2. **`T+0` 日内清算对齐与未来 7 日刚性应付（`AP + Payroll Liquidity Floor`）安全垫门禁**：司库 AI 发起任何期限 `> T+0`（如 `T+1` 国债交收、定期存单 CD）的资金归集（Sweep）前，网关强制读取 ERP 未来 7 个自然日的【工资单（Payroll）+ 预提税款 + 到期刚性应付账款（AP）】总额，要求实时可动用的 `T+0 Fedwire / 即时赎回国债货币基金` 余额 **100% 覆盖未来 7 日刚性支出 × 1.15 安全缓冲系数**。检出久期错配导致发薪账户（ZBA）面临日内透支风险，网关在 **14ms** 内拦截（`HTTP 422 ILLIQUID_DURATION_MISMATCH_OR_PAYROLL_ZBA_OVERDRAFT_BREACH`）。
3. **`SEC Rule 2a-7` 机构货币市场基金 `50%` 周流动性红线与银行 `CET1` 资本充足率核验**：借助 **Microsoft Web IQ** `/v3/browse` 在 **280ms** 内实时核验目标货币市场基金（MMF）每日披露的 **`Weekly Liquid Assets`（周度高流动性资产占比）是否 `>= 50%`**（根据美国证监会 `SEC Rule 2a-7` 新规，一旦机构优先货币基金周高流资产跌破 25% 将强制征收流动性赎回费 Liquidity Fee），并核查合作银行核心一级资本充足率（`CET1`）与不良率预警（`HTTP 451 MMF_WEEKLY_LIQUIDITY_BELOW_50PCT_MANDATORY_FEE_OR_BANK_CAMELS_STRESS_HOLD`）。
4. **闲置活期自动归集 `T+0` 国债货币基金与无洗售税损收割阿尔法立省/增厚 8.0%**：通过 **Microsoft Web IQ** 将原本躺在 `0.05%` 活期账户里的闲置资金自动转入 `T+0` 纯国债货币基金并安全完成跨品种免洗售税损置换，在 `$950,000.00` 的企业司库与财资调拨批次上单批创造无风险收益与节税价值 **`$76,000.00`**（净资金成本优化至 **`$874,000.00`**，`HTTP 409 TREASURY_T0_GOVT_MMF_SWEEP_AND_TAX_ALPHA_SAVINGS_CONFIRM`）。

![2026-11-15 智能体企业司库现金归集、FDIC 跨行分片与 IRC 1091 防洗售清算架构一图流](../assets/svg/252-agentic-corporate-treasury-cash-sweep-wash-sale-fdic-2026-11-15.svg)

---

## 🎯 二、 客户与架构师灵魂拷问 Q&A（First-Principles Q&A）

### Q1：我们给公司两个投资账户各配了一个量化理财 AI Agent，为什么 Agent A 刚卖掉浮亏的国债 ETF 准备年底抵税，却因为 Agent B 两天后的一次常规红利再投（DRIP）导致整笔抵税资格作废？
- **大白话与第一性原理**：因为美国税法 **`IRC § 1091`（洗售规则 Wash-Sale Rule）是按“同一个纳税人税号（TIN/EIN）”全局穿透合并计算的，而不是按单个券商账户隔离计算的**！
  1. **61 天对称双向时间窗**：很多人以为洗售只是“卖了之后 30 天内不能买回来”；实际上，法则规定的是**卖出日前 30 天 + 卖出当天 + 卖出日后 30 天（共 61 天）**！如果子账户 B 在卖出前第 15 天曾开启了自动股息再投资（`DRIP`）自动买进了 5 股同款 ETF，或者在卖出后第 10 天买回了追踪同一指数的同质产品，你卖出的那笔亏损就会被 IRS 认定为“虚假洗售”，当期抵税额直接清零！
  2. **跨账户协同盲区**：当企业同时拥有嘉信、盈透、摩根士丹利等多个托管账户时，单个账户内的券商风控根本看不到其他券商的持仓变动。唯有在司库网关层建立 **11ms 全局跨户 61 天 `CUSIP` 与同指数簇互斥锁**，才能确保 100% 税损收割有效（`HTTP 403`）。

### Q2：经历过硅谷银行（SVB）事件后，初创公司和中型企业的司库 AI 该如何管理账上的几百万美元现金，既不担心银行倒闭冻结、又不耽误周五发工资？
- **大白话与第一性原理**：
  - **`$250,000 FDIC` 红线与 `ICS` 跨行拆单**：任何一家美国商业银行对同一法人储户的 `FDIC` 保险上限只有 `$250,000`。把 `$5,000,000` 放在一家银行的活期户里，其中 `$4,750,000`（95%）属于无保险裸奔！通过 `IntraFi ICS` 协议自动将 `$5M` 拆成 21 份（每份 `$240,000`）分发到 21 家 FDIC 成员银行，或买入以美国财政部短期国债（T-Bills）100% 质押的 **`SEC Rule 2a-7` 政府货币市场基金（Government MMF）**，实现 100% 主权级安全。
  - **7 日发薪流动性安全垫（Liquidity Buffer）**：哪怕国债逆回购或定期存单收益再高，司库 AI 也绝不能把周五要通过 `ACH / Fedwire` 发放的 `$800,000` 工资款锁进 `T+1 / T+2` 资产里。网关通过 **14ms** 强锁 `7 日 AP + Payroll` 的 `T+0` 现金水位线，杜绝发薪违约（`HTTP 422`）。

### Q3：在实时核验 `SEC Form N-MFP` 货币基金每日周流动性占比（Weekly Liquid Assets）、银行 `CAMELS / CET1` 资本充足率及 `IRS` 同质证券裁定时，为什么选 Microsoft Web IQ 而不是 Exa 或 Bright Data？
- **架构选型对比**：
  - **Exa (Neural Search)**：语义向量匹配无法精确核验货币市场基金当日披露的 `Weekly Liquid Assets` 精确百分比是否逼近 `SEC Rule 2a-7` 的赎回费触发线。
  - **Bright Data (Scraping Proxy)**：按流量计费（`$8–$15/GB`），抓取延迟高达 `2,400–4,900ms`，且不具备企业级零数据留存（ZDR）保护企业机密现金头寸与投资组合。
  - **Microsoft Web IQ (`/v3/browse` + Deterministic Grounding)**：在 Azure 合规边界内以 **280ms** 确定性核验 `SEC Rule 2a-7` 流动性指标与银行资本充足率，并在启用 `T+0` 国债归集与免洗售置换创造 `$76,000.00` 综合收益时触发 `HTTP 409 Confirm`。

---

## 🧭 三、 直观可视化图解（Visual Architecture Diagrams）

### 3.1 企业司库现金归集、`FDIC` 分片与 `IRC § 1091` 防洗售清算决策树
```mermaid
flowchart TD
    A[发起企业司库现金归集与税损收割调拨<br/>批次总额: $950,000.00] --> B{跨账户 61天窗口内是否无同质 CUSIP 洗售冲突<br/>且单行存款敞口 <= $250k FDIC 上限?}
    B -- "否 (触发 IRC 1091 61天跨户洗售 / 单家银行无保险超额裸存)" --> C[🛑 HTTP 403 HARD BLOCK · 11ms<br/>IRC_1091_61DAY_WASH_SALE_VIOLATION_OR_UNINSURED_SINGLE_BANK_CONCENTRATION_BLOCKED]
    B -- "是 (100% 免洗售锁定且全额 FDIC/国债保障)" --> D{调拨后 T+0 现金余额是否 >= 未来7日<br/>工资单与刚性应付账款安全垫?}
    D -- "否 (久期错配把周五发薪钱锁入 T+2 定期 / ZBA 透支风险)" --> E[🚨 HTTP 422 HARD BLOCK · 14ms<br/>ILLIQUID_DURATION_MISMATCH_OR_PAYROLL_ZBA_OVERDRAFT_BREACH]
    D -- "是 (7日刚性付现安全垫 100% 充足)" --> F[调用 Microsoft Web IQ /v3/browse<br/>核验 SEC Rule 2a-7 货币基金周高流资产 >=50% 与银行 CET1 率]
    F --> G{目标 MMF 周度流动性 >= 50% (零赎回费风险)<br/>且托管银行一级资本充足率健康?}
    G -- "否 (Prime MMF 周流动性跌破阈值面临强制赎回费 / 银行评级预警)" --> H[🛑 HTTP 451 LEGAL HOLD · 280ms<br/>MMF_WEEKLY_LIQUIDITY_BELOW_50PCT_MANDATORY_FEE_OR_BANK_CAMELS_STRESS_HOLD]
    G -- "是 (100% 符合 SEC Rule 2a-7 与司库风控规范)" --> I{是否启用 T+0 纯国债 MMF 自动归集<br/>与跨品种免洗售税损置换?}
    I -- "是 (单批增厚收益/节税 $76,000.00)" --> J[🧑‍⚖️ HTTP 409 CONFIRM · 245ms<br/>净资金成本优化至 $874,000.00]
    I -- "否 (标准司库调拨清算)" --> K[✅ HTTP 200 Act automatically · 10ms<br/>安全执行司库调拨批次 $950,000.00]
```

### 3.2 传统单户孤立操作与单行大额裸存 vs. 全局 61 天洗售锁 + `FDIC` 分片 + 流动性底线对比
```mermaid
flowchart LR
    subgraph Bad["❌ 传统多账户孤立调拨与单行裸存 (3 大司库暴雷点)"]
        B1[A 账户卖亏损 ETF 抵税而 B 账户 DRIP 自动买回] --> B2[触发 IRC 1091 61天洗售规则<br/>年底抵税额被 IRS 全数驳回并罚息]
        B2 --> B3[$500万活期全存在单一中小银行<br/>超 $250k FDIC 上限面临挤兑冻结风险]
        B3 --> B4[为赚 30bps 收益把全部现金买进 T+2 理财<br/>周五发工资日内透支触发违约罚金]
    end

    subgraph Good["✅ 全局 61天洗售锁 + FDIC ICS 分片 + 7日安全垫 + Web IQ"]
        G1[同税号跨券商 61天 CUSIP 互斥锁<br/>+ IntraFi ICS 自动拆单每行 <=$245k] --> G2[强制锁定未来 7日 (Payroll+AP) × 1.15<br/>的 T+0 即时可用现金底线]
        G2 --> G3[Web IQ 280ms 核验 SEC Rule 2a-7<br/>周度流动性 >=50% 与银行 CET1 资本率]
        G3 --> G4[10ms 安全调拨 $950k 批次或<br/>T+0 国债归集+税损收割创收 $76,000!]
    end
```

### 3.3 端到端时序图（Cross-Account Wash-Sale Lock + FDIC Slicer + Web IQ Rule 2a-7 Gate）
```mermaid
sequenceDiagram
    autonumber
    participant CFO as 企业司库 / 财资管理 AI Agent
    participant Ledger as 跨券商持仓图谱 & ERP 应付/发薪日历
    participant Guard as 司库风控与洗售策略引擎 (Policy Engine)
    participant WebIQ as Microsoft Web IQ (/v3/browse)
    participant Cust as IntraFi ICS 分片网 / T+0 国债货币基金

    CFO->>Guard: 1. 发起闲置现金归集 (Cash-Sweep) 与税损收割指令 ($950,000.00)
    Ledger->>Guard: 2. 上报全账户 [-30d,+30d] 交易流水、单行存款额与未来 7日发薪需求
    Note over Guard: 校验 1: 是否无 61天跨户洗售冲突且单行无保险敞口 <= $250k?
    alt 命中 IRC 1091 61天同质标的洗售或单一银行超额无保险裸存
        Guard-->>CFO: HTTP 403 Blocked (11ms · 拦截洗售违规与单行挤兑风险)
    else 税务抵扣有效且 100% 存款保险覆盖
        Note over Guard: 校验 2: 留存 T+0 现金是否足以覆盖未来 7日工资与刚性 AP?
        alt 久期错配导致发薪日流动性不足或 ZBA 透支风险
            Guard-->>CFO: HTTP 422 Unprocessable (14ms · 拦截发薪流动性穿仓)
        else 7日刚性流动性安全垫充足
            Guard->>WebIQ: 3. 核验 SEC Rule 2a-7 基金周度流动性 >=50% 与银行 CET1 指标
            WebIQ-->>Guard: 4. 返回基金高流动性证明与 T+0 国债归集方案 (245-280ms)
            Guard->>Cust: 5. 执行 ICS 跨行分片存款与免洗售 ETF 置换交割 (10ms)
        end
    end
```

---

## 📊 四、 架构师选型决策矩阵（Architect Decision Matrix）

| 评估维度 | 方案 A：资金全放单一银行活期 + 各子账户独立买卖 | 方案 B：月末人工转买定期存单 + 年底手工挑亏损票卖 | **方案 C（推荐）：全局 61 天洗售锁 + `FDIC ICS` 分片 + 7 日安全垫 + Web IQ `2a-7` 门禁** |
| :--- | :--- | :--- | :--- |
| **`IRC § 1091` 跨账户 61 天防洗售** | ❌ 子账户间或 `DRIP` 定投互相踩踏，抵税资格作废 | ⚠️ 人工难以核对同一指数下不同代码的实质相同属性 | ✅ **11ms 同税号跨券商 61 天 `CUSIP` 与同质簇硬锁**（100% 保住税损抵扣额，返回 `HTTP 403`） |
| **防单一银行挤兑与 `$250k FDIC` 保障** | ❌ 90%+ 资金无存款保险保护，面临 SVB 式冻结风险 | ⚠️ 人工开立 20 家银行账户管理成本极高且对账混乱 | ✅ **`IntraFi ICS` 自动跨行拆单（每行 `<=$245k`）**（单一入口享千万级全额保障，返回 `HTTP 403`） |
| **发薪日（Payroll）与刚性 AP 防透支** | ⚠️ 虽不透支，但活期利息近乎为 0，白亏 5% 年化收益 | ❌ 定期存单无法提前支取，发薪日被迫高息透支 | ✅ **14ms 对齐 ERP 7 日刚性付现水位线**（保留足额 `T+0` 缓冲，杜绝违约，返回 `HTTP 422`） |
| **`SEC Rule 2a-7` 基金流动性与综合收益** | ❌ 零收益，每年因通胀净缩水 | ⚠️ 无法实时监测 Prime MMF 周流动性跌破红线风险 | ✅ **Web IQ 280ms `2a-7` 核验 + `T+0` 国债归集**（单批创收/节税 `$76,000.00`，触发 `HTTP 451/409`） |

---

## 🧪 五、 定量实测与 7-Card 4:5 视觉评测报告摘要（Quantitative Benchmark）

在本地确定性评测套件（`lab/webiq_commerce_demo.py`）中，我们对 `$950,000.00` 的智能体企业司库现金归集（`Cash-Sweep`）、`FDIC` 分片与 `IRC § 1091` 防洗售批次进行了 5 组边界压测（数据来源：`deterministic_offline_simulation` 与 `official_doc_snapshot`，零虚构坐标）：

| 压测场景代号 | 输入条件与故障/攻击注入 | 期望 HTTP 状态码 | 实测决策代码 (`decision_code`) | 实测延迟 | 动作标签 (`action_pill`) |
| :--- | :--- | :---: | :--- | :---: | :--- |
| **`trs_commit_ok`** | 无 61天洗售 + `FDIC` 分片合规 + 7日发薪安全垫 + `Rule 2a-7` 达标 (`$950,000.00`) | `200 OK` | `VERIFIED_CORPORATE_TREASURY_CASH_SWEEP_SETTLED` | `10ms` | `Act automatically` |
| **`trs_wsh_403`** | 关联账户 61 天内买回同质 `CUSIP` 触发 `IRC § 1091` 洗售或单行无保险存款 `>$250k` | `403 Forbidden` | `IRC_1091_61DAY_WASH_SALE_VIOLATION_OR_UNINSURED_SINGLE_BANK_CONCENTRATION_BLOCKED` | `11ms` | `Send to a human` |
| **`trs_liq_422`** | 将未来 7 日发薪（Payroll）与刚性 AP 所需资金锁入非 `T+0` 资产引发透支风险 | `422 Unprocessable` | `ILLIQUID_DURATION_MISMATCH_OR_PAYROLL_ZBA_OVERDRAFT_BREACH` | `14ms` | `Send to a human` |
| **`trs_mmf_451`** | 货币基金 `SEC Rule 2a-7` 周度高流动性资产 `<50%` 面临赎回费或银行 `CET1` 预警 | `451 Unavailable` | `MMF_WEEKLY_LIQUIDITY_BELOW_50PCT_MANDATORY_FEE_OR_BANK_CAMELS_STRESS_HOLD` | `280ms` | `Send to a human` |
| **`trs_sav_409`** | Web IQ 启用 `T+0` 纯国债货币基金归集与免洗售税损收割增厚收益 `$76,000.00` | `409 Conflict` | `TREASURY_T0_GOVT_MMF_SWEEP_AND_TAX_ALPHA_SAVINGS_CONFIRM` | `245ms` | `Confirm` |

---

## 🛠️ 六、 生产上线快速核验清单（Production Readiness Checklist）

- [ ] **强制跨托管账户 61 天 `IRC § 1091` 洗售互斥锁与 `FDIC` 分片上限**：在司库调拨引擎中要求 `irc_1091_61day_cross_account_wash_sale_free_and_fdic_ics_sliced_verified == True`，任何 61 天内同质标的反向交易或单行无保险敞口 `> $250,000` 在 `11ms` 内返回 `HTTP 403`。
- [ ] **锁定未来 7 日工资与刚性应付（Payroll + AP）`T+0` 现金底线**：严禁将 7 日内待付刚性资金扫入 `T+1/T+2` 或定期锁定资产，久期错配在 `14ms` 内返回 `HTTP 422`。
- [ ] **接入 Microsoft Web IQ `SEC Rule 2a-7` 与银行资本充足率实时监控**：通过 `/v3/browse` 核查货币基金每日 `Weekly Liquid Assets >= 50%` 披露与银行 `CET1` 比率，异常立即挂起 `HTTP 451`。
- [ ] **启用闲置活期 `T+0` 国债归集与非同质 ETF 税损置换**：安全获取无风险利差与税务阿尔法（`HTTP 409 Confirm`）。
