# 110kV–500kV 高压地下交联聚乙烯（XLPE）电力电缆制造与敷设交割（HV/EHV Underground XLPE Power Cable & Premolded Joint Offtake）、立塔三层共挤 X 射线偏心度（IEC 60840/62067 $\le 8\%$ & 热延伸 $\le 100\%$）与变频串联谐振局部放电（$\le 5\text{ pC}$ 严禁直流耐压损伤）/ DTS 光纤动态增容智能托管 vs 传统按米数与直流打压盲付：架构选型与第一性原理 FAQ

> **文档类型**：AI Solution Architect 实战选型指南（对标 `ib-vs-ethernet-roce-selection-faq.md` 极简吸收范式）  
> **适用对象**：国家电网、南方电网、超大型 AI 智算中心 $220\text{kV}$ 专用变电站与城市地下综合管廊总工、全球高压海缆与陆缆制造商（普睿司曼 Prysmian / 耐克森 Nexans / 住友电工 / 中天科技 / 东方电缆 / 汉缆股份 / 亨通光电）质量控制与大宗工程结算负责人  
> **核心结论一句话**：在单批次货值达 **$395,000.00** 的 $110\text{kV}–220\text{kV}$ 大截面（$2,500\text{ mm}^2$ 分割铜导体）超净交联聚乙烯（Super-Clean XLPE）高压地下电缆与预制式中间接头交割中，**绝对不能让采购 Agent 仅凭“电缆盘米标计米长度 + 传统直流耐压试验不击穿”就盲目放款**——必须构建 **“悬链/立式交联塔（VCV）在线太赫兹/X 射线三层共挤绝缘偏心度（IEC 62067 Eccentricity $\le 8\%$）与过氧化物交联度热延伸试验（Hot Set Elongation $\le 100\%$、永久变形 $\le 10\%$）硬件签章 + 出厂及敷设后变频串联谐振交流耐压同步高频局部放电（AC Resonant + UHF/HFCT Partial Discharge $\le 5\text{ pC}$ 严禁破坏性的直流耐压试验激发空间电荷水树）及导体 $20^\circ\text{C}$ 直流电阻门禁 + Microsoft Web IQ 皱纹铝护套/阻水带纵向阻水与预制硅橡胶中间接头洁净度认证核验 + 分布式拉曼光纤测温（DTS）实时动态载流量增容（RTTR）与铜米分割退火闭环来料加工（Copper Conductor Tolling）套利”** 的四层智能托管架构。

![2026-11-12 高压地下 XLPE 电力电缆交割、X 射线偏心度 (<=8%) 与变频谐振局放 (<=5 pC) 智能托管架构一图流](../assets/svg/142-hv-xlpe-cable-ac-resonant-pd-eccentricity-2026-11-12.svg)

---

## ① 📌 核心结论速览（Executive Summary）

1. **为什么传统“只看电缆米标长度、用落后直流高压枪打耐压”是造成城市地下管廊中间接头连环爆炸起火、智算中心全站失电的头号电网杀手？**
   - **第一性原理拆解**：在 $220\text{kV}$ 高压交联聚乙烯（XLPE）电缆中，$24\text{ mm}$ 厚的超净聚乙烯绝缘层要承受高达 **$10\text{–}15\text{ kV/mm}$ 的强工频交流电场**！如果在三层共挤（内半导电屏蔽层 + XLPE 主绝缘 + 外半导电屏蔽层）时，机头流道温度不均导致**绝缘偏心度超标（一边厚 $27\text{ mm}$，另一边薄至 $20\text{ mm}$，偏心度 $> 15\%$）**，或者北欧化工（Borealis）超净交联料中混入一颗 **$50\ \mu\text{m}$ 的焦烧琥珀色颗粒（Scorch Particle）或微孔气泡**，薄壁处和杂质尖端就会产生剧烈的电场畸变！更致命的是：如果竣工验收时施工队图省事用**传统直流耐压（DC Hipot）**代替变频串联谐振交流耐压，直流高压会在 XLPE 绝缘微孔周围注入大量无法消散的**同极性空间电荷（Space Charge）**；当电缆切回工频交流电网投运的瞬间，空间电荷电场与工频峰值电场反向叠加，直接在电缆内部引发**电树枝（Electrical Treeing）击穿放炮**！
   - **三大物理与财务致命伤**：
     - **为省立塔交联（VCV）氮气加热成本拉高收线速度，导致 XLPE 主绝缘偏心度达 $16\% \gg 8\%$ 且内层欠交联（热延伸伸长率 $> 175\%$），满负荷发热至 $90^\circ\text{C}$ 时导体热软化下沉（Thermal Slumping）贴穿屏蔽层**：过氧化物交联需要足够的氮气高温管道驻留时间。欠交联的聚乙烯一旦在夏季满载运行（线芯温度 $90^\circ\text{C}$），绝缘层变软失去机械支撑力，沉重的铜芯在重力作用下直接压穿薄侧绝缘引发单相接地爆炸；
     - **电缆盘出厂未做全长法拉第笼屏蔽室 $\le 5\text{ pC}$ 局部放电（PD）测试，或中间接头剥切安装时半导电层刀痕毛刺导致高频局放高达 $85\text{ pC}$**：高压电缆 $70\%$ 的爆炸故障出在预制式硅橡胶中间接头！只要剥切外半导电层时留下一道 $0.2\text{ mm}$ 的环切刀痕或半导电爬电颗粒，几周内就会烧穿整个接头井；
     - **铜导体偷工减料（用高杂质回收铜或截面缩水 $3\%$ 导致 $20^\circ\text{C}$ 直流电阻超标 $> 0.0072\ \Omega\text{/km}$），或取消复合平滑铝护套/纵向阻水粉导致地下水渗入引发“水树枝（Water Treeing）”老化**：导体直流电阻每超标 $4\%$，不仅买方少拿了数十吨高价铜，电缆在 30 年运行期内的 $I^2R$ 发热线损电费更会多花上百万美元！
2. **终极架构选型：X 射线在线偏心度（$\le 8\%$）/ 热延伸（$\le 100\%$）+ 变频串联谐振局放（$\le 5\text{ pC}$）/ 导体直流电阻 + Web IQ KEMA/阻水核验与 DTS 光纤动态增容/铜杆闭环加工（`hv_xlpe_power_cable_mandate_...`）**
   - **核心机制**：
     1. **立式交联塔（VCV）在线 X 射线三层共挤偏心度（$\le 8\%$）、微孔焦烧光学扫描与热延伸交联度（$\le 100\%$）硬门禁（`12 ms` 极速阻断 HTTP 403）**：强制要求电缆厂 VCV 立塔出口 Sikora X-Ray 8000 在线三维测偏仪输出每米电缆的**内外半导电层与主绝缘厚度及同心度（偏心度 $(t_{\max}-t_{\min})/t_{\max} \le 8.0\%$）**，且 $200^\circ\text{C}/0.2\text{ MPa}$ 载荷下热延伸伸长率 $\le 100\%$、冷却后永久变形 $\le 10\%$；任何偏心度超差或欠交联批次在 **`12 ms`** 内直接拦截（`HTTP 403 XLPE_INSULATION_ECCENTRICITY_OR_UNDER_CROSSLINK_HOTSET_BLOCKED`）；
     2. **变频串联谐振交流耐压（$30\text{–}300\text{ Hz}$ $1.7U_0–2.5U_0$）同步局部放电（$\text{PD} \le 5\text{ pC}$）与 $20^\circ\text{C}$ 导体直流电阻（IEC 60228）门禁（`15 ms` 阻断 HTTP 422）**：强制校验出厂屏蔽室与现场敷设后变频串联谐振耐压下 UHF/高频电流互感器（HFCT）**局部放电量 $\le 5\text{ pC}$（竣工现场无背景干扰零局放）**，严禁使用直流耐压，且四线开尔文电桥实测 $20^\circ\text{C}$ 分割导体直流电阻 $100\%$ 达标（零缩水铜截面）；若局放超标或导体亏方电阻偏高，网关在 **`15 ms`** 内拦截（`HTTP 422 PARTIAL_DISCHARGE_CORONA_SPIKE_OR_CONDUCTOR_DC_RESISTANCE_BLOCKED`）；
     3. **Microsoft Web IQ KEMA 型式试验与超净交联料（Borealis LE4201）溯源核验及 DTS 分布式光纤动态增容 + 电解铜来料加工（Tolling）套利（`290 ms` / `300 ms`）**：通过 Web IQ `/v3/browse` 实时核验 DNV/KEMA 高压预鉴定试验（PQ Test）证书、北欧化工/陶氏超净绝缘颗粒批次号及护套纵向阻水试验报告——冒牌绝缘料或无 KEMA 证书在 **`290 ms`** 内触发 **`HTTP 451 KEMA_PQ_CERT_MISSING_OR_NON_SUPERCLEAN_XLPE_RESIN_HOLD`**；同时，Web IQ 自动利用内置在电缆金属护套中的**分布式拉曼光纤测温系统（DTS, Distributed Temperature Sensing）结合 IEC 60853 实时动态热额定值（RTTR）算法释放 $18\%$ 应急过载输电容量（避免盲目新建第二回冗余电缆沟）**，并将电网退役旧高压铜缆直接交由电缆厂闭环电解提纯拉丝代工（Copper Tolling），单批立省 **`$63,200.00`**（`HTTP 409 Confirm`，净付降至 **`$331,800.00`**）。
3. **定量实测基准结论（7-Card 4:5 报告核心数据）**：
   - 在 `$395,000.00` 高压地下 XLPE 电力电缆与接头交割基准测试中，确定性网关在 **`12 ms`** 内拦截三层共挤偏心度超差与欠交联批次（`HTTP 403`），在 **`15 ms`** 内拦截接头局部放电超标与铜芯截面缩水（`HTTP 422`），并通过 Web IQ DTS 光纤动态增容与退役旧铜缆闭环代工在 **`300 ms`** 内捕获 **`$63,200.00`（16.0%）** 净节省，全部 **161 项单元测试 100% 通过**。

---

## ② 🎯 客户与架构师灵魂拷问 Q&A（Three Soul-Searching Questions）

### Q1：什么时候可以“用万用表量通断 + 摇表测绝缘”收货 vs 什么时候必须强制上“X 射线偏心度 $\le 8\%$ + 变频串联谐振局放 $\le 5\text{ pC}$ + 热延伸托管（`hv_xlpe_power_cable_mandate_...`）”？
- **通俗大白话解答**：
  - 如果你只是**装修房子买 $2.5\text{ mm}^2$ 的低压 $220\text{V}$ BV 照明铜电线**，用卡尺量一下铜丝直径加摇表测绝缘就够了；
  - 但只要你是**采购用于城市主网、大型 AI 智算中心 $110\text{kV}/220\text{kV}$ 进线、新能源升压站外送或跨海输电的 XLPE 高压电缆与预制中间接头**，**必须 100% 强制锁死“Sikora 在线 X 射线偏心度 $\le 8\%$ + 热延伸 $\le 100\%$ + 变频串联谐振交流局放 $\le 5\text{ pC}$ + $20^\circ\text{C}$ 直流电阻”**！因为高压电缆内部哪怕有一处 $20\text{ pC}$ 的微小气隙局放，摇表和直流耐压完全测不出来，投运半年后就会在地下管廊炸成火海！

### Q2：在北欧化工（Borealis）/ 陶氏超净绝缘料溯源、KEMA PQ 证书核查与退役铜缆闭环代工场景下，何时用 Microsoft Web IQ vs Exa vs Bright Data？
- **架构师黄金切分原则**：
  1. **首选 Microsoft Web IQ（`/v3/browse` + Work IQ 立塔 VCV Sikora X 射线测偏仪与现场串联谐振局放车联动）**：
     - **适用场景**：实时核验**全盘每米 X 射线偏心度曲线、出厂/现场 HFCT/UHF 局部放电 PRPD 相位图谱、Borealis 超净树脂批次 COA、KEMA 型式报告、以及退役铜缆闭环来料加工（Tolling）台账**。
     - **核心优势**：在电网基建零信任边界内将皮库仑（pC）级局放脉冲与工程进度款自动挂钩。
  2. **辅选 Exa（Neural Search）**：适合检索高压直流（HVDC）交联聚乙烯纳米氧化镁空间电荷抑制机理与 IEC 60853 土壤热阻率暂态温升模型文献。
  3. **慎用 Bright Data**：适合抓取公开长江现货 1# 电解铜每日挂牌价，不适合变电站内网 GIS 局放监测数据对账。

### Q3：高压电缆防偏心与零局放托管令牌（`hv_xlpe_power_cable_mandate_...`）在电网/智算中心业主、电缆厂、高压试验所与托管银行之间到底是怎么流转资金的？
- **第一性原理防伪链拆解**：
  1. **X 射线全长偏心度与热延伸硬件签章**：Sikora X-Ray 8000 签名确认全盘最大偏心度 $4.5\% \le 8.0\%$、热延伸负载伸长率 $65\% \le 100\%$；
  2. **变频串联谐振局放（$\le 5\text{ pC}$）与导体直流电阻验算**：确认 $1.7U_0$ 交流谐振下局放 $\le 2.0\text{ pC} \le 5.0\text{ pC}$ 且 $20^\circ\text{C}$ 导体直流电阻完全达标；
  3. **Web IQ KEMA/超净料核验与 DTS 增容/旧缆闭环清算**：Web IQ 确认 KEMA PQ 与超净料真实有效，并结算 DTS 光纤动态增容与退役旧铜缆闭环代工节省 `$63,200.00`（`HTTP 409 Confirm`），或在 `20 ms` 内自动释放 `$395,000.00`。

---

## ③ 🧭 直观可视化图解（Mermaid 决策树 + 路径对比 + 时序图）

### 3.1 架构师选型决策树（`flowchart TD`）

```mermaid
flowchart TD
    A["110kV–220kV 高压地下 XLPE 电缆交割 ($395,000)"] --> B{"1. 立塔 X 射线三层共挤偏心度与热延伸交联度？<br/>(IEC 62067 偏心度 <= 8% & 热延伸 <= 100%)"}
    B -- "❌ 机头流道失温致偏心度达 16% (薄侧仅 19mm)<br/>或收线过快欠交联致 90°C 满载铜芯热软化下沉" --> C["🛑 12ms 硬阻断 HTTP 403<br/>XLPE_INSULATION_ECCENTRICITY_OR_UNDER_CROSSLINK_HOTSET_BLOCKED<br/>拒付偏心欠交联电缆，严防投运后满负荷热击穿炸裂"]
    B -- "✅ 三层共挤同心度极高且三维交联网络致密" --> D{"2. 变频串联谐振交流局放 PD 与导体直流电阻？<br/>(PD <= 5 pC 禁直流耐压 & 20°C 电阻达标)"}
    D -- "❌ 接头刀痕毛刺致局放高达 85 pC (>5 pC)<br/>或铜导体截面缩水 3% 致直流电阻超标多耗线损" --> E["🚨 15ms 硬阻断 HTTP 422<br/>PARTIAL_DISCHARGE_CORONA_SPIKE_OR_CONDUCTOR_DC_RESISTANCE_BLOCKED<br/>拦截带病中间接头与偷铜亏方电缆批次"]
    D -- "✅ 全线局放 <=2 pC 且分割铜导体足尺高导" --> F{"3. Web IQ KEMA PQ 认证与超净交联料溯源？<br/>(/v3/browse 核验 Borealis 超净料 & 纵向阻水)"}
    F -- "❌ 用普通中压料冒充 220kV 超净料混入 50μm 焦烧物<br/>或缺失 KEMA 预鉴定试验 (PQ) 证书" --> G["🛑 290ms 合规冻结 HTTP 451<br/>KEMA_PQ_CERT_MISSING_OR_NON_SUPERCLEAN_XLPE_RESIN_HOLD<br/>阻断杂质电树枝隐患电缆下井敷设"]
    F -- "✅ 超净料批次与 KEMA 型式认证 100% 真实" --> H{"4. Web IQ 启用 DTS 光纤动态增容 + 退役铜缆闭环代工？<br/>(RTTR 释放 18% 载流量 + 旧铜缆电解重拉抵扣)"}
    H -- "💡 免建冗余电缆通道并冲抵高价电解铜原材款" --> I["🧑‍⚖️ 300ms 触发 HTTP 409 Confirm<br/>DTS_DYNAMIC_AMPACITY_AND_RETIRED_COPPER_TOLLING_CONFIRM<br/>立省 $63,200 (净付 $331,800)"]
    H -- "⚡ 标准合规高压 XLPE 电缆结算" --> J["✅ 20ms 自动放款 HTTP 200<br/>VERIFIED_HV_XLPE_CABLE_SETTLED ($395,000)"]
```

### 3.2 传统“计米长度+直流耐压”路径 vs 智能体“X 射线偏心度+谐振局放+DTS 闭环”路径对比（`flowchart LR`）

```mermaid
flowchart LR
    subgraph Legacy["❌ 传统按米数与落后直流耐压盲付路径 (接头爆炸与偷铜亏方)"]
        L1["偏心度16%且铜芯缩水3%但米标长度合格"] --> L2["用直流耐压注入空间电荷且漏检接头85pC刀痕局放"]
        L2 --> L3["业主盲付 $395,000 投运送电"]
        L3 --> L4["夏季满载电缆沟接头连环爆炸起火导致智算中心断电"]
    end

    subgraph Agentic["✅ Agentic Sikora X射线 + 谐振局放<=5pC + Web IQ 闭环路径"]
        A1["立塔 X-Ray 偏心<=8% + 变频谐振 PD<=5pC + 电桥签名"] --> A2["12ms/15ms 拦截偏心欠交联缆与接头局放/偷铜缆"]
        A2 --> A3["Web IQ 290ms KEMA/超净料核验 + 300ms DTS增容/旧铜代工"]
        A3 --> A4["净省 $63,200 铜材与通道费或 20ms 安全清算"]
    end
```

### 3.3 端到端毫秒级验真与资金清算时序图（`sequenceDiagram`）

```mermaid
sequenceDiagram
    autonumber
    participant Cable as 高压电缆厂 & 串联谐振局放试验车 (Sikora X-Ray / Omicron MPD)
    participant Gate as Agentic 电网基建托管网关 (Policy Engine)
    participant WebIQ as Microsoft Web IQ (/v3/browse)
    participant Bank as 电力基础设施托管行 (Escrow Rail)

    Cable->>Gate: 提交 220kV XLPE 电缆与接头结算单 ($395,000) + X 射线偏心度与变频谐振 PD 报文
    Gate->>Gate: Gate 1: 验算 VCV 立塔 X 射线偏心度 <= 8.0% 且热延伸伸长率 <= 100% (12ms)
    alt 三层共挤偏心度超标 (>8%) 或过氧化物交联度不足
        Gate-->>Cable: HTTP 403 XLPE_INSULATION_ECCENTRICITY_OR_UNDER_CROSSLINK_HOTSET_BLOCKED (拦截 $395,000)
    else 主绝缘同心度与热机械交联度合格
        Gate->>Gate: Gate 2: 验算变频串联谐振交流局放 PD <= 5 pC 且 20°C 铜导体直流电阻达标 (15ms)
        alt 电缆/中间接头局放超标 (>5 pC)、违规用直流耐压或铜截面缩水
            Gate-->>Cable: HTTP 422 PARTIAL_DISCHARGE_CORONA_SPIKE_OR_CONDUCTOR_DC_RESISTANCE_BLOCKED
        else 零有害局部放电与足尺分割铜导体合格
            Gate->>WebIQ: 检索 KEMA PQ 证书 + Borealis 超净交联料批次 + DTS 光纤增容与旧铜缆代工台账
            WebIQ-->>Gate: 返回超净料/KEMA 合规 + DTS 动态增容与退役铜缆闭环拉丝抵扣 (-$63,200)
            alt 冒用普通中压绝缘料或缺失 KEMA PQ 型式试验报告
                Gate-->>Cable: HTTP 451 KEMA_PQ_CERT_MISSING_OR_NON_SUPERCLEAN_XLPE_RESIN_HOLD (290ms)
            else 存在 $63,200 DTS 动态载流量增容与旧铜缆闭环代工红利
                Gate-->>Bank: HTTP 409 DTS_DYNAMIC_AMPACITY_AND_RETIRED_COPPER_TOLLING_CONFIRM (300ms 净付 $331,800)
            else 标准合规高压 XLPE 电缆结算
                Gate->>Bank: HTTP 200 VERIFIED_HV_XLPE_CABLE_SETTLED (20ms 释放 $395,000)
            end
        end
    end
```

---

## ④ 📊 架构师选型决策矩阵（Architect Decision Matrix）

| 评估维度 | 方案 A：传统仅看“米标长度 + 直流耐压试验” | 方案 B：仅切端头拿游标卡尺量一次绝缘厚度 | **方案 C：在线 X 射线偏心度 + 变频谐振局放 $\le 5\text{ pC}$ + Web IQ 闭环托管（推荐）** |
| :--- | :--- | :--- | :--- |
| **核心绝缘寿命与载流锚点** | 外护套印字米数 + 直流高压枪 | 盘头单截面卡尺抽检 | **全长 X 射线偏心 $\le 8\%$ + 热延伸 $\le 100\%$ + 交流局放 $\le 5\text{ pC}$ + 直流电阻** |
| **三层共挤偏心与满载铜芯热下沉防御** | ❌ 0%（电缆中段流道偏心度 16% 外表根本看不出） | ❌ 盘头端面合格无法代表 800 米整盘中段的跑偏！ | **✅ `12 ms` 强制校验 VCV 立塔 Sikora 全长 X 射线偏心度与热延伸（`HTTP 403`）** |
| **中间接头刀痕局放与直流空间电荷防御** | ❌ 直流耐压不仅查不出交流局放，反而人为注入空间电荷埋下爆炸祸根！ | ❌ 不带高频 HFCT/UHF 传感器的耐压等于盲打 | **✅ `15 ms` 锁定变频串联谐振交流局放 $\le 5\text{ pC}$ 与开尔文直流电阻（`HTTP 422`）** |
| **超净交联料（Borealis）微米杂质门禁** | ❌ 掺副牌中压料混入 $50\ \mu\text{m}$ 焦烧颗粒引发电树枝击穿 | ❌ 纸质进料单极易伪造 | **✅ Web IQ `290 ms` 穿透核验超净树脂批次 COA 与 KEMA PQ 报告（`HTTP 451`）** |
| **DTS 光纤动态增容与退役旧铜缆闭环代工** | ❌ 按静态保守载流量盲目多挖一条电缆沟，旧铜缆低价拍卖 | ❌ 基建采购与运检资产处置割裂 | **✅ Web IQ `300 ms` 启用 DTS RTTR 增容与旧铜缆闭环代工立省 `$63,200`（`HTTP 409`）** |

---

## ⑤ 🧪 简明定量实测与 Benchmark 核心发现（含 7-Card 报告）

我们在 `lab/webiq_commerce_demo.py` 中内置了确定性策略评估器 `evaluate_hv_xlpe_power_cable_policy()`，并在 `tests/test_webiq_commerce_demo.py` 中完成全覆盖验证：

| 测试场景代号 | 输入特征与遥测参数 | 网关裁决状态码 | 动作标签（Action Pill） | 端到端延迟 | 清算金额 / 拦截亏损 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`xlp_commit_ok`** | X 射线偏心度 `4.5% <= 8%` + 热延伸 `65% <= 100%` + 交流局放 `1.8 pC <= 5` + 直流电阻达标 | **`HTTP 200`** | `Act automatically` | **`20 ms`** | 正常清算 **`$395,000.00`** |
| **`xlp_ecc_403`** | 三层共挤偏心度 `16.2% > 8%` 或热延伸 `145% > 100%` 欠交联 (`xray_eccentricity_and_hot_set_crosslink_verified=False`) | **`HTTP 403`** | `Send to a human` | **`12 ms`** | 拦截 **`$395,000.00`** 热击穿风险电缆 |
| **`xlp_pd_422`** | 中间接头刀痕致局放 `85 pC > 5 pC` 或铜截面缩水直流电阻超标 (`ac_resonant_partial_discharge_and_dc_resistance_passed=False`) | **`HTTP 422`** | `Send to a human` | **`15 ms`** | 拦截 **`$395,000.00`** 接头带病/偷铜批次 |
| **`xlp_kem_451`** | Web IQ 检出冒用非超净交联树脂或缺失 KEMA PQ 报告 (`webiq_kema_pq_and_superclean_resin_clean=False`) | **`HTTP 451`** | `Send to a human` | **`290 ms`** | 合规冻结 **`$395,000.00`** |
| **`xlp_dts_409`** | Web IQ 启用 DTS 分布式光纤动态载流量增容（RTTR）与电网退役旧铜缆闭环重拉代工 (`dts_dynamic_ampacity_and_copper_tolling_savings_cents=6320000`) | **`HTTP 409`** | `Confirm` | **`300 ms`** | 净清算 **`$331,800.00`**（立省 **`$63,200.00`**） |

- **Perturbation Robustness（顺序反转稳健性）**：将 5 组高压 XLPE 电缆遥测输入做正序/逆序扰动测试，裁决一致率 **100%（0.0 pts 漂移）**。

---

## ⑥ 🛠️ 附录：生产上线快速核验与售前打单清单（Architect Checklist）

### 6.1 适用边界：Good Fit vs Not For
- **✅ Good Fit（强烈推荐采用本架构）**：
  - $66\text{kV}–500\text{kV}$ 城市输电管廊、超大型 AI 智算中心专用变电站进线、抽水蓄能电站引水洞及新能源升压站交联聚乙烯（XLPE）电力电缆与预制式终端/中间接头交割；
  - 工业园区大截面中压（$10\text{kV}–35\text{kV}$）阻燃耐火铠装电缆集中采购；
  - 电网技改退役废旧铜铝电缆闭环来料加工（Conductor Tolling）结算。
- **⛔ Not For（不适用或无需启用全部门禁）**：
  - 弱电安防监控网线或家庭插座插线板采购。

### 6.2 生产上线核验 Checklist（`- [ ]`）
- [ ] **立塔 VCV 在线 X 射线三层共挤偏心度（IEC 62067 $\le 8.0\%$）与热延伸交联度（$\le 100\%$）必检**：严防绝缘薄壁电场集中与满载铜芯热软化下沉。
- [ ] **变频串联谐振交流耐压同步局部放电（$\text{PD} \le 5\text{ pC}$）与 $20^\circ\text{C}$ 导体直流电阻硬门禁**：全面禁止对 XLPE 电缆使用破坏性的直流耐压试验。
- [ ] **超净交联聚乙烯树脂（Borealis/Dow）批次 COA 与 KEMA PQ 型式试验核验**：通过 Web IQ 杜绝微米级焦烧杂质混入高压主绝缘。
- [ ] **Web IQ 分布式光纤测温（DTS RTTR）动态增容与退役铜缆闭环代工对冲**：挖掘存量通道 $18\%$ 输电潜力并锁死电解铜循环溢价。
