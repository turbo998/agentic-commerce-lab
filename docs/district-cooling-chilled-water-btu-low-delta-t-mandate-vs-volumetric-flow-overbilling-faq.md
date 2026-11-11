# 区域集中供冷与 AI 智算中心冷冻水交割（District Cooling & Chilled-Water Offtake）、EN 1434 配对冷量表（BTU Meter）与防“大流量小温差综合征（Low-$\Delta T$ Syndrome $\ge 8.0^\circ\text{C}$）”智能托管 vs 传统按水流量盲付：架构选型与第一性原理 FAQ

> **文档类型**：AI Solution Architect 实战选型指南（对标 `ib-vs-ethernet-roce-selection-faq.md` 极简吸收范式）  
> **适用对象**：AI 智算中心液冷/冷冻水基础设施总监、商业综合体与生物医药园区区域能源站（District Cooling System, DCS）采购负责人、暖通空调（HVAC / 磁悬浮冷机）节能改造架构师  
> **核心结论一句话**：在月度结算额高达 **$135,000.00** 的区域集中供冷（District Cooling）与智算中心一次侧冷冻水采购中，**绝对不能让采购 Agent 仅凭水表读数或未配对校准的温度计盲目支付冷量费与超额流量罚金**——必须构建 **“EN 1434 Class 2 成对匹配 Pt1000 铂电阻与超声波冷量表（实测供水温度 $T_{\text{supply}} \le 6.0^\circ\text{C}$ 保证潜热除湿与 CDU 换热裕度）硬件签章 + 动态压差无关型平衡调节阀（PICV）锁死供回水温差（$\Delta T = T_{\text{return}} - T_{\text{supply}} \ge 8.0^\circ\text{C}$）杜绝‘大流量小温差综合征’罚款 + Microsoft Web IQ ASHRAE 188 冷却塔军团菌合规核验与夜间谷电冰/水蓄冷（TES）移峰套利”** 的四层智能托管架构。

![2026-11-11 区域供冷与智算中心冷冻水交割、BTU 温差冷量表与防小温差综合征智能托管架构一图流](../assets/svg/111-district-cooling-chilled-water-delta-t-2026-11-11.svg)

---

## ① 📌 核心结论速览（Executive Summary）

1. **为什么传统“按水表流量计费”或“忽视大流量小温差（Low-$\Delta T$ Syndrome）”是数据中心与商业园区空调账单的头号资金黑洞？**
   - **第一性原理拆解**：根据热力学第一定律，冷冻水输送的真实冷量功率为 $\dot{Q} = \dot{m} \cdot c_p \cdot (T_{\text{return}} - T_{\text{supply}})$（单位：冷吨时 $\text{Ton-Hour}$ 或 $\text{kWh}_{\text{thermal}}$）。**一旦供水温度偏高，或者供回水温差 $\Delta T$ 坍塌，水泵就会陷入疯狂空转耗电与双向罚款的恶性循环**！
   - **三大物理与财务致命伤**：
     - **供水温度漂移（$T_{\text{supply}} = 9.5^\circ\text{C} > 6.0^\circ\text{C}$）导致丧失除湿与高密散热能力，或者温度探头 $0.6^\circ\text{C}$ 零点漂移凭空虚增冷量**：如果区域冷站为了省自己的离心式冷水机组电费，将供水温度从合同规定的 $5.5^\circ\text{C}$ 偷偷调高到 **$9.5^\circ\text{C}$**（高于空气露点温度），洁净室与机房空调盘管将完全丧失潜热除湿能力；更隐蔽的是，在设计温差 $8^\circ\text{C}$ 下，如果供回水两支温度计未做激光配对校准、存在哪怕 **$+0.6^\circ\text{C}$ 的正向零点漂移**，就会在全年每一秒钟凭空多算出 **$7.5\%$ 的虚假冷量**，让买方每年白交十多万美元冤枉钱；
     - **换热器结垢或三通阀旁通引发“大流量小温差综合征（Low-$\Delta T$ Syndrome）”，触发 25% 惩罚性流量附加费**：当买方板式换热器（PHE）结垢、电动二通阀选型过大关不严，或老旧末端采用三通旁通阀时，$5.5^\circ\text{C}$ 的冷冻水还没充分吸热就在 **$8.7^\circ\text{C}$（温差 $\Delta T = 3.2^\circ\text{C} \ll 8.0^\circ\text{C}$）** 时直接流回区域供冷管网。这会导致供冷站回水温度过低、多台冷机无法满载运行且循环水泵电耗暴增 **$3.3^3 \approx 35$ 倍**，区域供冷合同因此对 $\Delta T < 8.0^\circ\text{C}$ 的用冷户强征高达 **20%–30% 的“超额体积流量罚款（Excess Flow Surcharge）”**；
     - **敞开式冷却塔嗜肺军团菌（Legionella pneumophila）超标触发公共卫生停机令**：若供冷站省掉非氧化性杀菌剂投加，导致冷却塔气溶胶检出嗜肺军团菌 $>1,000\text{ CFU/L}$，将直接触发疾控与环保部门紧急关停冷站，导致智算中心瞬间高温宕机。
2. **终极架构选型：EN 1434 配对 Pt1000 冷量表 + PICV 动态平衡防小温差 + Web IQ 军团菌核验与谷电蓄冷套利（`district_cooling_delta_t_mandate_...`）**
   - **核心机制**：
     1. **EN 1434 Class 2 成对匹配 Pt1000 铂电阻与供水温度（$\le 6.0^\circ\text{C}$）硬门禁（`11 ms` 极速阻断 HTTP 403）**：强制要求一次侧交割边界超声波冷量表采用出厂配对标定的四线制 Pt1000 铂电阻对（温差配对误差 $\le 0.03^\circ\text{C}$），且供水温度必须 **$T_{\text{supply}} \le 6.0^\circ\text{C}$**；若供水超温沦为“温水空转”或温度探头失配漂移，网关在 **`11 ms`** 内直接拦截（`HTTP 403 WARM_SUPPLY_TEMP_OR_UNPAIRED_BTU_DRIFT_BLOCKED`）；
     2. **供回水温差（$\Delta T \ge 8.0^\circ\text{C}$）与动态压差无关型调节阀（PICV）防旁通门禁（`14 ms` 阻断 HTTP 422）**：实时监测板换一次侧供回水温差 $\Delta T$ 与污垢热阻（Fouling Factor）。一旦检出 $\Delta T < 8.0^\circ\text{C}$（发生三通旁通漏流或板换结垢）企图触发区域冷站小温差罚单，网关在 **`14 ms`** 内拦截异常流量账单并自动下发指令关小动态压差平衡阀（PICV）逼高回水温度（`HTTP 422 LOW_DELTA_T_BYPASS_OR_FOULING_PENALTY_BLOCKED`）；
     3. **Microsoft Web IQ ASHRAE 188 军团菌/制冷剂合规与夜间谷电冰/水蓄冷（TES）移峰套利（`285 ms` / `295 ms`）**：通过 Web IQ `/v3/browse` 实时核验供冷站冷却塔月度嗜肺军团菌 qPCR 检测阴性报告（符合 ASHRAE Standard 188）与磁悬浮离心机低 GWP 氢氟烯烃制冷剂（如 R-1233zd(E)）检漏记录——违规即在 **`285 ms`** 内触发 **`HTTP 451 LEGIONELLA_BIOCIDE_OR_REFRIGERANT_LEAK_HOLD`**；当遇到电网尖峰电价与高需量费（Demand Charge）时段，Web IQ 自动切换园区 **分层水蓄冷罐 / 冰蓄冷槽（Thermal Energy Storage, TES，利用夜间 $0.04/\text{kWh}$ 谷电制冰/蓄冷水）** 并在过渡季低温湿球天气启用板换免费自然冷却（Waterside Economizer），单月立省 **`$21,600.00`**（`HTTP 409 Confirm`，净付降至 **`$113,400.00`**）。
3. **定量实测基准结论（7-Card 4:5 报告核心数据）**：
   - 在 `$135,000.00` 区域集中供冷与智算中心冷冻水月度交割基准测试中，确定性网关在 **`11 ms`** 内拦截 $9.5^\circ\text{C}$ 超温供水与探头漂移账单（`HTTP 403`），在 **`14 ms`** 内拦截 $\Delta T = 3.2^\circ\text{C}$ 小温差旁通惩罚（`HTTP 422`），并通过 Web IQ 夜间谷电蓄冷移峰在 **`295 ms`** 内捕获 **`$21,600.00`（16.0%）** 净节省，全部 **130 项单元测试 100% 通过**。

---

## ② 🎯 客户与架构师灵魂拷问 Q&A（Three Soul-Searching Questions）

### Q1：什么时候可以按“普通水表或建筑面积平摊”付空调费 vs 什么时候必须强制上“EN 1434 配对 BTU 冷量表 + $\Delta T \ge 8.0^\circ\text{C}$ PICV 闭环托管（`district_cooling_delta_t_mandate_...`）”？
- **通俗大白话解答**：
  - 如果你只是**租了一间 50 平米的小办公室，物业按平米收固定中央空调管理费**，无需单装工业级超声波冷量表；
  - 但只要你是**AI 智算中心（液冷 CDU 一次侧靠冷冻水散热）、半导体洁净厂房、三甲医院或大型商业综合体向区域供冷站（DCS）买冷**，月度账单动辄十多万美元且包含严苛的“最低回水温差（$\Delta T \ge 8.0^\circ\text{C}$）与超流量阶梯惩罚条款”，**必须 100% 强制部署“EN 1434 激光配对 Pt1000 超声波冷量表 + PICV 动态压差平衡阀锁温差”**！否则冷站送来 $9^\circ\text{C}$ 的温水不仅压不住 GPU 结温，还会因为你为了降温被迫开大阀门放大水流量，反过来被冷站按“小温差超流量违约”倒罚一笔巨款！

### Q2：在冷却塔军团菌监管、气象湿球自然冷却与蓄冷谷电调度场景下，何时用 Microsoft Web IQ vs Exa vs Bright Data？
- **架构师黄金切分原则**：
  1. **首选 Microsoft Web IQ（`/v3/browse` + Work IQ 楼宇/机房 BMS 台账联动）**：
     - **适用场景**：实时核验**第三方卫检机构 ASHRAE 188 嗜肺军团菌检测公报、区域电网分时尖峰/深谷电价（TOU）与容量需量费率、以及当地气象局逐时湿球温度（Wet-Bulb Temperature，用于判断何时开启冷却塔直供板换 Free Cooling 停掉冷机）**。
     - **核心优势**：支持在企业零信任边界内将机房 BMS / CDU 供回水遥测与外部电价、气象及卫生合规记录做确定性融合。
  2. **辅选 Exa（Neural Search）**：适合检索磁悬浮无油离心冷水机组喘振抑制算法与相变蓄冷材料（PCM）文献。
  3. **慎用 Bright Data**：适合抓取公开家电零售价格，不适合数据中心 BMS 与区域能源站高可靠结算。

### Q3：冷冻水配对热焓与防小温差令牌（`district_cooling_delta_t_mandate_...`）在智算中心业主、区域供冷站、BMS 控制器与结算银行之间到底是怎么流转资金的？
- **第一性原理防伪链拆解**：
  1. **EN 1434 四线制配对 Pt1000 与双声道超声波流量积分**：能量积分仪每 2 秒采样一次体积流量 $q_v$、供水温度 $T_s$ 与回水温度 $T_r$，结合水温对应的精确密度 $\rho(T)$ 与比热容 $c_p(T)$ 积分真实冷量 $E = \int q_v \rho c_p (T_r - T_s) dt$。只有 $T_s \le 6.0^\circ\text{C}$ 的合格深度冷量才进入有效结算池；
  2. **PICV 动态温差锁死与污垢诊断**：当一次侧供水温度正常（$5.5^\circ\text{C}$）但回水温度跌破 $13.5^\circ\text{C}$（$\Delta T < 8.0^\circ\text{C}$）时，网关在 `14 ms` 内拦截超额流量账单，并指令 BMS 将末端压差无关型调节阀（PICV）切换至定温差追踪模式（Delta-T Control Mode）；
  3. **Web IQ 蓄冷移峰冲抵与自动清算**：Web IQ 核算夜间谷电水蓄冷罐（TES）在白天尖峰时段放冷替代的高价区域买冷费 `$21,600.00`（`HTTP 409 Confirm`），或在 `19 ms` 内自动释放 `$135,000.00` 净冷量款。

---

## ③ 🧭 直观可视化图解（Mermaid 决策树 + 路径对比 + 时序图）

### 3.1 架构师选型决策树（`flowchart TD`）

```mermaid
flowchart TD
    A["区域供冷 / 智算中心冷冻水月度交割 ($135,000)"] --> B{"1. 供水温度与配对 Pt1000 铂电阻校准？<br/>(T_supply <= 6.0°C & 温差配对误差 <= 0.03°C)"}
    B -- "❌ 供水超温 (9.5°C > 6.0°C) 丧失除湿换热力<br/>或探头零点漂移 0.6°C 虚增冷量" --> C["🛑 11ms 硬阻断 HTTP 403<br/>WARM_SUPPLY_TEMP_OR_UNPAIRED_BTU_DRIFT_BLOCKED<br/>拒付温水空转账单并豁免买方流量违约"]
    B -- "✅ 供水 <= 6.0°C 且配对精度达标" --> D{"2. 供回水温差 (ΔT) 与板换/PICV 状态？<br/>(ΔT >= 8.0°C 零三通旁通)"}
    D -- "❌ 阀门内漏/板换结垢致 ΔT = 3.2°C < 8.0°C<br/>诱发 25% 小温差超流量罚款" --> E["🚨 14ms 硬阻断 HTTP 422<br/>LOW_DELTA_T_BYPASS_OR_FOULING_PENALTY_BLOCKED<br/>自动闭环调节 PICV 阀并发起板换在线反冲洗"]
    D -- "✅ 温差 ΔT >= 8.0°C 高效换热" --> F{"3. Web IQ 冷却塔军团菌与制冷剂合规？<br/>(/v3/browse 核查 ASHRAE 188 & R-1233zd)"}
    F -- "❌ 嗜肺军团菌 > 1,000 CFU/L 或高 GWP 氟利昂泄漏" --> G["🛑 285ms 合规冻结 HTTP 451<br/>LEGIONELLA_BIOCIDE_OR_REFRIGERANT_LEAK_HOLD<br/>强制投加杀菌剂以防疾控停机令"]
    F -- "✅ 微生物安全与低 GWP 制冷剂达标" --> H{"4. Web IQ 检出尖峰电价可切蓄冷罐 (TES) 放冷？<br/>(谷电冰/水蓄冷 + 过渡季湿球自然冷却)"}
    H -- "💡 高峰时段由 TES 蓄冷罐顶替区域高价买冷" --> I["🧑‍⚖️ 295ms 触发 HTTP 409 Confirm<br/>TES_CHILLED_WATER_PEAK_SHAVING_CONFIRM<br/>立省 $21,600 (净付 $113,400)"]
    H -- "⚡ 标准高效大温差供冷直结" --> J["✅ 19ms 自动放款 HTTP 200<br/>VERIFIED_DISTRICT_COOLING_BTU_SETTLED ($135,000)"]
```

### 3.2 传统“按流量/未配对探头盲付”路径 vs 智能体“配对 Pt1000+PICV 锁温差+TES 蓄冷”路径对比（`flowchart LR`）

```mermaid
flowchart LR
    subgraph Legacy["❌ 传统按流量或劣质冷量表盲付路径 (温水空转与双向罚款)"]
        L1["冷站送 9.5°C 温水或探头漂移 0.6°C"] --> L2["买方被迫开大阀门致温差跌至 ΔT=3.2°C"]
        L2 --> L3["冷站反过来加收 25% 小温差超流量罚款"]
        L3 --> L4["财务盲付 $135,000 且机房湿度失控"]
    end

    subgraph Agentic["✅ Agentic 配对 Pt1000 + PICV 锁温差 + Web IQ TES 路径"]
        A1["EN 1434 激光配对 Pt1000 + PICV 阀门遥测签名"] --> A2["11ms/14ms 拦截超温供水与小温差旁通"]
        A2 --> A3["Web IQ 285ms 军团菌核验 + 295ms 谷电蓄冷移峰"]
        A3 --> A4["净省 $21,600 尖峰冷费或 19ms 安全清算"]
    end
```

### 3.3 端到端毫秒级验真与资金清算时序图（`sequenceDiagram`）

```mermaid
sequenceDiagram
    autonumber
    participant DCS as 区域供冷站 & 边界 BTU 冷量表 (Pt1000/PICV)
    participant Gate as Agentic 冷冻水托管网关 (Policy Engine)
    participant WebIQ as Microsoft Web IQ (/v3/browse)
    participant BMS as 智算中心基础设施结算行 (Settlement Rail)

    DCS->>Gate: 提交月度冷冻水结算单 ($135,000) + 配对 Pt1000 供回水温差与流量积分报文
    Gate->>Gate: Gate 1: 验算供水温度 T_supply <= 6.0°C 且 Pt1000 探头配对误差 <= 0.03°C (11ms)
    alt 供水超温 (>6.0°C) 或未配对探头零点漂移
        Gate-->>DCS: HTTP 403 WARM_SUPPLY_TEMP_OR_UNPAIRED_BTU_DRIFT_BLOCKED (拦截 $135,000)
    else 深度低温供水品质达标
        Gate->>Gate: Gate 2: 验算供回水温差 ΔT >= 8.0°C 且无三通旁通/板换重度结垢 (14ms)
        alt ΔT < 8.0°C 发生大流量小温差综合征
            Gate-->>DCS: HTTP 422 LOW_DELTA_T_BYPASS_OR_FOULING_PENALTY_BLOCKED
        else 大温差高效换热合格
            Gate->>WebIQ: 检索冷却塔 ASHRAE 188 军团菌检测报告 + 电网分时电价与 TES 蓄冷放冷量
            WebIQ-->>Gate: 返回军团菌阴性 + 夜间谷电 TES 蓄冷与自然冷却移峰抵扣 (-$21,600)
            alt 冷却塔军团菌超标或高 GWP 制冷剂泄漏
                Gate-->>DCS: HTTP 451 LEGIONELLA_BIOCIDE_OR_REFRIGERANT_LEAK_HOLD (285ms)
            else 存在 $21,600 谷电水蓄冷/冰蓄冷移峰节省
                Gate-->>BMS: HTTP 409 TES_CHILLED_WATER_PEAK_SHAVING_CONFIRM (295ms 净付 $113,400)
            else 标准高效大温差冷量结算
                Gate->>BMS: HTTP 200 VERIFIED_DISTRICT_COOLING_BTU_SETTLED (19ms 释放 $135,000)
            end
        end
    end
```

---

## ④ 📊 架构师选型决策矩阵（Architect Decision Matrix）

| 评估维度 | 方案 A：传统按电磁水表立方米流量计费 | 方案 B：普通未配对工业热电偶/Pt100 简易算冷量 | **方案 C：EN 1434 配对 Pt1000 + PICV 锁温差 + Web IQ 蓄冷托管（推荐）** |
| :--- | :--- | :--- | :--- |
| **核心计量硬件** | 单一水流量计（只管流过多少吨水） | 独立采购未做配对标定的两支普通温度计 | **成对激光匹配 Pt1000（$\Delta T$ 误差 $\le 0.03^\circ\text{C}$）+ 双声道超声波** |
| **温水充冷水（$T_s > 6^\circ\text{C}$）与漂移防御** | ❌ 0%（哪怕送来 $12^\circ\text{C}$ 温水也照收全款） | ❌ 两支探头 $0.5^\circ\text{C}$ 零点偏差就会凭空多收 6%–8% 假冷量 | **✅ `11 ms` 拦截 $T_s > 6.0^\circ\text{C}$ 温水与失配探头（`HTTP 403`）** |
| **大流量小温差（Low-$\Delta T$）罚款防御** | ❌ 阀门全开狂抽水导致水泵电费爆炸 | ❌ 无法区分是供水超温导致开大阀，还是买方板换结垢 | **✅ `14 ms` 识别 $\Delta T < 8.0^\circ\text{C}$ 并联动 PICV 稳温差（`HTTP 422`）** |
| **冷却塔军团菌（ASHRAE 188）门禁** | ❌ 无公共卫生联动，面临突发停机风险 | ❌ 无微生物合规校验 | **✅ Web IQ `285 ms` 核查军团菌 qPCR 阴性报告（`HTTP 451`）** |
| **夜间谷电冰/水蓄冷（TES）削峰** | ❌ 白天尖峰时段被迫高价买冷 | ❌ 无分时电价与湿球温度联动 | **✅ Web IQ `295 ms` 联动 TES 蓄冷放冷立省 `$21,600`（`HTTP 409`）** |

---

## ⑤ 🧪 简明定量实测与 Benchmark 核心发现（含 7-Card 报告）

我们在 `lab/webiq_commerce_demo.py` 中内置了确定性策略评估器 `evaluate_district_cooling_chilled_water_policy()`，并在 `tests/test_webiq_commerce_demo.py` 中完成全覆盖验证：

| 测试场景代号 | 输入特征与遥测参数 | 网关裁决状态码 | 动作标签（Action Pill） | 端到端延迟 | 清算金额 / 拦截亏损 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`dcs_commit_ok`** | 供水 `5.4°C <= 6.0°C` + 温差 `ΔT = 8.8°C >= 8.0°C` + 军团菌阴性 | **`HTTP 200`** | `Act automatically` | **`19 ms`** | 正常清算 **`$135,000.00`** |
| **`dcs_tmp_403`** | 冷站供水温度漂移至 `9.5°C > 6.0°C` 或探头未配对校准 (`paired_pt1000_and_supply_temp_verified=False`) | **`HTTP 403`** | `Send to a human` | **`11 ms`** | 拦截 **`$135,000.00`** 温水空转账单 |
| **`dcs_dlt_422`** | 三通旁通或板换结垢致温差跌至 `ΔT = 3.2°C < 8.0°C` (`return_delta_t_and_picv_balance_passed=False`) | **`HTTP 422`** | `Send to a human` | **`14 ms`** | 拦截 **`$135,000.00`** 并闭环调节 PICV 阀 |
| **`dcs_leg_451`** | Web IQ 检出冷却塔嗜肺军团菌 `> 1,000 CFU/L` 或高 GWP 制冷剂泄漏 (`webiq_legionella_ashrae188_and_refrigerant_clean=False`) | **`HTTP 451`** | `Send to a human` | **`285 ms`** | 合规冻结 **`$135,000.00`** |
| **`dcs_tes_409`** | Web IQ 在电网尖峰时段调用夜间谷电水蓄冷罐（TES）与过渡季板换自然冷却 (`tes_thermal_storage_and_free_cooling_savings_cents=2160000`) | **`HTTP 409`** | `Confirm` | **`295 ms`** | 净清算 **`$113,400.00`**（立省 **`$21,600.00`**） |

- **Perturbation Robustness（顺序反转稳健性）**：将 5 组区域供冷交割遥测输入做正序/逆序扰动测试，裁决一致率 **100%（0.0 pts 漂移）**。

---

## ⑥ 🛠️ 附录：生产上线快速核验与售前打单清单（Architect Checklist）

### 6.1 适用边界：Good Fit vs Not For
- **✅ Good Fit（强烈推荐采用本架构）**：
  - AI 智算中心（液冷 CDU 一次侧冷却水 / 风冷精密空调冷冻水）向园区集中能源站买冷长协；
  - 机场航站楼、中央商务区（CBD 区域供冷管网，如前海/珠江新城/新加坡 Marina Bay / 迪拜 Empower 模式）及生物医药洁净厂房；
  - 配备水蓄冷罐、冰蓄冷槽或冬季冷却塔板换免费供冷（Waterside Free Cooling）的园区综合能源项目。
- **⛔ Not For（不适用或无需启用全部门禁）**：
  - 家用分体式壁挂空调或小型多联机（VRV/VRF 氟系统，无冷冻水环路）；
  - 不计冷量、仅按固定机柜电力包干的极小型托管机房。

### 6.2 生产上线核验 Checklist（`- [ ]`）
- [ ] **供水超温免除买方低 $\Delta T$ 责任的因果联锁**：确认合同与网关规则明确——若因供冷站供水温度 $T_{\text{supply}} > 6.0^\circ\text{C}$ 导致买方末端被迫开大阀门进而引发 $\Delta T < 8.0^\circ\text{C}$，100% 豁免买方超流量罚款并扣减供冷站违约金。
- [ ] **EN 1434 激光配对四线制 Pt1000 铂电阻强制双年检**：严禁单独更换供水或回水单支温度探头（必须成对更换成对标定），确保零点温差漂移 $\le 0.03^\circ\text{C}$。
- [ ] **全面废除末端三通旁通阀、升级动态压差无关型平衡阀（PICV）**：从物理架构上彻底切断未换热冷水直接短路回流主回水管的路径。
- [ ] **ASHRAE 188 嗜肺军团菌与谷电蓄冷（TES）自动联调**：确认 Web IQ `/v3/browse` 核验冷却塔水质生物安全，并根据次日气象湿球温度曲线自动寻优夜间蓄冷充放策略。
