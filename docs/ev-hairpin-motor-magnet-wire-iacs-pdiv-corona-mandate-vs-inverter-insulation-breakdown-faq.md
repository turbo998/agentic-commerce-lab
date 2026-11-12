# 800V 电驱扁线电机无氧铜杆与耐电晕漆包扁线交割（800V EV Hairpin Motor Oxygen-Free Copper & PEEK/PI Magnet Wire Offtake）、局部放电起始电压（IEC 60851-5 $\text{PDIV} \ge 1,350\text{ V}_{\text{pk}}$ 防碳化硅高频脉冲匝间击穿）与导电率/低氧（$\ge 101.0\%\text{ IACS}$ & $\text{O}_2 \le 5\text{ ppm}$ 防激光焊接气孔）/ 铜米闭环智能托管 vs 传统按铜线过磅毛重盲付：架构选型与第一性原理 FAQ

> **文档类型**：AI Solution Architect 实战选型指南（对标 `ib-vs-ethernet-roce-selection-faq.md` 极简吸收范式）  
> **适用对象**：新能源汽车 800V/1000V 电驱系统与主机厂（特斯拉 / 比亚迪 / 华为数字能源 / 汇川技术 / 博世 Bosch / 采埃孚 ZF / 蔚来）定子绕组工程与大宗有色金属采购架构师、电磁线与高导铜材龙头（精达股份 / 金杯电工 / 住友电工 Sumitomo / 苏威 Solvay / 江西铜业）质量与点价结算负责人  
> **核心结论一句话**：在单批次货值达 **$325,000.00** 的 800V 碳化硅（SiC）高压发卡式扁线电机（Hairpin Stator）聚酰亚胺（PI）/ 聚醚醚酮（PEEK）耐电晕漆包铜扁线交割中，**绝对不能让采购 Agent 仅凭“线盘过磅重量 + 常温万用表直流电阻合格单”就盲目放款**——必须构建 **“高频脉冲局部放电起始电压（IEC 60851-5 / IEC 60034-18-41 Type II $\text{PDIV} \ge 1,350\text{ V}_{\text{pk}}$ @ $150^\circ\text{C}$ 严防 SiC 逆变器 $50\text{ kV/}\mu\text{s}$ 尖峰电压击穿匝间绝缘）与全长高压直流火花零针孔（Inline HV Spark Test $= 0\text{ Pinholes/30m}$）硬件签章 + 无氧铜杆（TU1/OFC）氧含量（$\text{O}_2 \le 5\text{ ppm}$ 防定子发卡端部激光焊接气孔虚焊）与国际退火铜标准导电率（ASTM B193 $\ge 101.0\%\text{ IACS}$）及急弯扭转不脱漆门禁 + Microsoft Web IQ LME A 级阴极铜伦敦金银/有色可追溯牌号（The Copper Mark）与 UL 1446 绝缘系统认证核验 + 冲槽切头裸铜废料闭环上引连铸（Closed-Loop Copper Tolling）与 LME 远期均价点价套利”** 的四层智能托管架构。

![2026-11-12 800V 扁线电机无氧铜与耐电晕漆包线交割、局部放电 (PDIV >=1,350 Vpk) 与低氧导电率智能托管架构一图流](../assets/svg/138-ev-hairpin-magnet-wire-pdiv-iacs-2026-11-12.svg)

---

## ① 📌 核心结论速览（Executive Summary）

1. **为什么传统“只称线盘重量、只测工频耐压”是导致 800V 碳化硅电动汽车行驶 1 万公里后定子绕组匝间放炮烧毁、激光焊点气孔断路的头号技术灾难？**
   - **第一性原理拆解**：在第三代半导体 **碳化硅（SiC MOSFET）驱动的 800V 高压电驱平台** 中，逆变器开关速度极快，脉冲电压上升率（$dV/dt$）高达 **$40\text{–}60\text{ kV/}\mu\text{s}$**！由于行波反射效应（Transmission-Line Reflection），加在扁线电机定子第一匝线圈上的瞬态过冲尖峰电压高达 **$1,600\text{–}2,100\text{ V}_{\text{pk}}$**！如果漆包扁线四角 R 角处的绝缘漆膜涂覆变薄（Edge Thinning），使得**局部放电起始电压（PDIV, Partial Discharge Inception Voltage）低于 $1,350\text{ V}_{\text{pk}}$**，在电机内部每微秒都会发生数万次高能微电弧轰击（电晕放电 Corona），哪怕是不含纳米氧化铝填充的普通聚酯亚胺漆膜，不出 200 小时就会被紫外线、臭氧与电子轰击生生蚀穿，引发致命的**定子相间/匝间短路烧机（高速失速趴窝）**！
   - **三大物理与财务致命伤**：
     - **用普通低成本混合废杂铜熔炼的高氧铜杆（含氧量 $\text{O}_2 = 280\text{ ppm} \gg 5\text{ ppm}$）冒充 TU1 无氧铜，导致定子发卡（Hairpin）200 个端部激光焊接时“氢气孔爆炸虚焊”**：扁线定子每台电机有 $180\text{–}240$ 个发卡铜线端头需要用绿光/蓝光复合激光瞬间熔焊成球。如果铜基体里含有 $280\text{ ppm}$ 的氧化亚铜（$\text{Cu}_2\text{O}$）夹杂，在 $1,100^\circ\text{C}$ 激光熔池中氧瞬间气化膨胀，把焊球炸成满是马蜂窝气孔的假焊点（Porosity $> 15\%$）！车辆一上颠簸路面或大电流急加速，焊点直接烧融断路！
     - **涂漆模具偏心导致扁线四角 R 角漆膜厚度不足（$< 85\ \mu\text{m}$），高温下局部放电起始电压跌至 $\text{PDIV} = 880\text{ V}_{\text{pk}} < 1,350\text{ V}_{\text{pk}}$，或 3D 空间折弯成形时漆膜龟裂起皮**：800V 扁线需要将直铜扁线做复杂的 3D 扭头折弯（U-Pin Twist & Bend）。如果聚酰亚胺（PI）底涂处理不良或纳米耐电晕填料团聚，折弯后 R 角外侧出现微裂纹，一进 ATF 油冷变速箱油液浸泡立刻发生油浸击穿；
     - **把空塑料/木质交货线盘（Spool Tare）当高价漆包铜线卖，且定子去漆切头产生的 $12\%$ 高纯无氧铜线头被当低价杂铜处理**：一盘漆包扁线毛重 $250\text{ kg}$，若线盘皮重误差 $+3\text{ kg}$ 就是白送几百元铜钱；同时电驱厂切下的高纯无氧铜头若不闭环直返铜杆厂重熔（只收每吨 `$450` 加工费），等于白白承受 LME 铜价高额点价差。
2. **终极架构选型：高温局部放电起始电压（$\text{PDIV} \ge 1,350\text{ V}_{\text{pk}}$）/ 零针孔火花检测 + 无氧铜低氧（$\text{O}_2 \le 5\text{ ppm}$）/ 导电率 $\ge 101.0\%\text{ IACS}$ + Web IQ Copper Mark 核验与发卡废铜头闭环来料加工（`ev_hairpin_magnet_wire_mandate_...`）**
   - **核心机制**：
     1. **高频脉冲局部放电起始电压（IEC 60851-5 $\text{PDIV} \ge 1,350\text{ V}_{\text{pk}}$ @ $150^\circ\text{C}$）与在线全长 $3,000\text{ V}$ 高压火花零针孔硬门禁（`12 ms` 极速阻断 HTTP 403）**：强制要求电磁线厂在线激光测径/四面漆厚仪与高频局放测试台输出硬件签名报文，确认扁线窄边 R 角最小绝缘厚度 $\ge 110\ \mu\text{m}$、**$150^\circ\text{C}$ 高温下双绞/平行扁线 $\text{PDIV} \ge 1,350\text{ V}_{\text{pk}}$，且全盘在线高压直流火花试验针孔数 $= 0$**；任何耐电晕不足或 R 角偏心批次在 **`12 ms`** 内直接拦截（`HTTP 403 LOW_PDIV_CORONA_INCEPTION_OR_CORNER_ENAMEL_PINHOLE_BLOCKED`）；
     2. **无氧铜杆惰性气体熔融红外氧含量（$\text{O}_2 \le 5\text{ ppm}$）、涡流导电率（$\ge 101.0\%\text{ IACS}$）与 3D 发卡折弯零开裂门禁（`15 ms` 阻断 HTTP 422）**：强制校验 LECO 氧氮氢分析仪实测铜芯含氧量 $\le 5\text{ ppm}$（杜绝激光焊接气孔）、导电率 $\ge 101.0\%\text{ IACS}$、回弹角偏差 $\le 0.3^\circ$，且经历 $180^\circ$ U 型发卡折弯并在 $150^\circ\text{C}$ 变速箱油（ATF）浸泡后耐压无击穿；若混入高氧再生杂铜或折弯脱漆，网关在 **`15 ms`** 内拦截（`HTTP 422 HIGH_COPPER_OXYGEN_LASER_WELD_POROSITY_OR_BEND_CRACK_BLOCKED`）；
     3. **Microsoft Web IQ UL 1446 绝缘系统与 LME Copper Mark 溯源核验及发卡裸铜切头闭环上引连铸（Tolling）套利（`290 ms` / `300 ms`）**：通过 Web IQ `/v3/browse` 实时核验 UL Product iQ 数据库中的 **UL 1446 N 级（$200^\circ\text{C}$）/ R 级（$220^\circ\text{C}$）电机绝缘系统兼容性证书** 及 LME 交割品牌 The Copper Mark 无冲突矿源认证——证照不符在 **`290 ms`** 内触发 **`HTTP 451 UL1446_INSULATION_SYSTEM_MISMATCH_OR_COPPER_MARK_HOLD`**；同时，Web IQ 自动将电驱车间发卡冲制、去漆与平头工序切下的 **$12\%$ 零污染 TU1 无氧铜废线头（Clean Hairpin Copper Offcuts）纳入闭环上引法无氧连铸来料加工（免除 LME 铜基价重购，仅付拉丝涂漆加工费）**，并结合微孔发泡低介电常数聚酰亚胺（Foamed PI，$\varepsilon_r$ 从 $3.4$ 降至 $2.3$）替代昂贵进口 PEEK 挤出，单批立省 **`$52,000.00`**（`HTTP 409 Confirm`，净付降至 **`$273,000.00`**）。
3. **定量实测基准结论（7-Card 4:5 报告核心数据）**：
   - 在 `$325,000.00` 800V 扁线电机无氧铜与耐电晕漆包线交割基准测试中，确定性网关在 **`12 ms`** 内拦截低 PDIV 耐电晕缺陷与 R 角偏心针孔（`HTTP 403`），在 **`15 ms`** 内拦截高氧铜杆激光焊气孔与折弯脱漆（`HTTP 422`），并通过 Web IQ 发卡裸铜废头闭环连铸与微孔发泡 PI 方案在 **`300 ms`** 内捕获 **`$52,000.00`（16.0%）** 净节省，全部 **157 项单元测试 100% 通过**。

---

## ② 🎯 客户与架构师灵魂拷问 Q&A（Three Soul-Searching Questions）

### Q1：什么时候可以“只看直流电阻和普通工频击穿电压”买漆包线 vs 什么时候必须强制上“高温 $\text{PDIV} \ge 1,350\text{ V}_{\text{pk}}$ + 无氧铜 $\text{O}_2 \le 5\text{ ppm}$ + 零针孔托管（`ev_hairpin_magnet_wire_mandate_...`）”？
- **通俗大白话解答**：
  - 如果你只是**买普通圆铜线绕 $220\text{ V}$ 家用电风扇电机或工频水泵电机**，没有高频逆变器脉冲冲击，也不做激光焊接，普通聚酯漆包圆线就够用；
  - 但只要你是**制造 800V/1000V 碳化硅（SiC）电驱平台发卡式扁线电机（Hairpin / X-Pin / 连续波绕组）**，**必须 100% 强制锁死“$150^\circ\text{C}$ 高温 $\text{PDIV} \ge 1,350\text{ V}_{\text{pk}}$ + 铜芯含氧量 $\text{O}_2 \le 5\text{ ppm}$ + 导电率 $\ge 101.0\%\text{ IACS}$ + 在线零针孔”**！因为工频耐压高达 $6,000\text{ V}$ 的普通漆包线，如果四角 R 角漆膜稍薄导致 $\text{PDIV}$ 掉到 $900\text{ V}_{\text{pk}}$，在 SiC 逆变器每秒数万次的高频尖峰轰击下几百小时就会电晕击穿烧毁整台电驱总成！

### Q2：在 LME / 沪铜（SHFE）点价结算、UL 1446 绝缘认证核查与扁线 ATF 变速箱油兼容性场景下，何时用 Microsoft Web IQ vs Exa vs Bright Data？
- **架构师黄金切分原则**：
  1. **首选 Microsoft Web IQ（`/v3/browse` + Work IQ 电驱厂 Hairpin 激光焊中控与漆包线在线测径/局放仪联动）**：
     - **适用场景**：实时核验**每轴扁线的高温 PDIV 与四面 R 角漆膜激光测厚 JSON、LECO 铜氧含量分析单、UL Product iQ 绝缘系统档案、以及发卡切头无氧废铜闭环来料加工（Copper Tolling）冲抵台账**。
     - **核心优势**：在企业零信任边界内将纳秒级局放波形与大宗有色金属点价解付直连。
  2. **辅选 Exa（Neural Search）**：适合检索纳米气相二氧化硅/聚酰亚胺（PI）杂化微孔发泡降介电常数（Low-$\varepsilon_r$）机理与蓝绿复合激光铜焊接吸收率文献。
  3. **慎用 Bright Data**：适合抓取公开电解铜现货升贴水报价，不适合电驱定子厂内部 OCT（光学相干断层扫描）焊点熔深与局放数据对账。

### Q3：800V 漆包扁线防电晕与无氧激光焊令牌（`ev_hairpin_magnet_wire_mandate_...`）在电驱主机厂、电磁线厂、高压绝缘实验室与托管银行之间到底是怎么流转资金的？
- **第一性原理防伪链拆解**：
  1. **高温 PDIV 与四面 R 角漆厚硬件签章**：脉冲局放仪（Schleich/Megger）签名确认 $150^\circ\text{C}$ 下 $\text{PDIV} = 1,480\text{ V}_{\text{pk}} \ge 1,350\text{ V}_{\text{pk}}$、R 角漆厚 $\ge 115\ \mu\text{m}$ 且在线火花试验 0 针孔；
  2. **无氧铜低氧（$\le 5\text{ ppm}$）与折弯耐油验算**：确认铜芯 $\text{O}_2 = 2.8\text{ ppm} \le 5\text{ ppm}$、导电率 $101.4\%\text{ IACS}$，且 U 型发卡折弯后无裂纹；
  3. **Web IQ UL 1446 核验与废铜头闭环清算**：Web IQ 确认 UL 1446 与 Copper Mark 合规，并结算发卡裸铜废头闭环上引连铸与微孔发泡 PI 节省 `$52,000.00`（`HTTP 409 Confirm`），或在 `20 ms` 内自动释放 `$325,000.00`。

---

## ③ 🧭 直观可视化图解（Mermaid 决策树 + 路径对比 + 时序图）

### 3.1 架构师选型决策树（`flowchart TD`）

```mermaid
flowchart TD
    A["800V 扁线电机无氧铜与耐电晕漆包线交割 ($325,000)"] --> B{"1. 150°C 高温局放电压 PDIV 与 R 角零针孔？<br/>(IEC 60851-5 PDIV >= 1,350 Vpk & 0 Pinholes)"}
    B -- "❌ 涂漆模具偏心致 R 角变薄 (PDIV = 880 Vpk)<br/>在 SiC 50kV/μs 脉冲下电晕蚀穿匝间短路烧机" --> C["🛑 12ms 硬阻断 HTTP 403<br/>LOW_PDIV_CORONA_INCEPTION_OR_CORNER_ENAMEL_PINHOLE_BLOCKED<br/>拒付不耐电晕漆包线，严防 800V 电驱高速失速召回"]
    B -- "✅ 四面漆厚均匀且高温 PDIV 裕度充沛" --> D{"2. 铜芯氧含量 O2、导电率 IACS 与折弯附着力？<br/>(O2 <= 5 ppm & >= 101.0% IACS & U 型折弯无裂)"}
    D -- "❌ 掺低价有氧铜杆 (O2 = 280 ppm) 致激光焊炸出气孔<br/>或 3D 发卡扭头折弯时 PI/PEEK 漆膜龟裂剥离" --> E["🚨 15ms 硬阻断 HTTP 422<br/>HIGH_COPPER_OXYGEN_LASER_WELD_POROSITY_OR_BEND_CRACK_BLOCKED<br/>拦截激光焊虚焊隐患线与折弯脱漆批次"]
    D -- "✅ TU1 无氧铜焊接致密无孔且高导柔韧" --> F{"3. Web IQ UL 1446 绝缘系统与 Copper Mark 核查？<br/>(/v3/browse 核验 ATF 油冷兼容性与低碳铜源)"}
    F -- "❌ 未通过变速箱 ATF 油浸热老化 UL 1446 认证<br/>或阴极铜来源缺失 Copper Mark 责任采矿证明" --> G["🛑 290ms 合规冻结 HTTP 451<br/>UL1446_INSULATION_SYSTEM_MISMATCH_OR_COPPER_MARK_HOLD<br/>阻断油冷水解溶胀隐患与不合规铜源"]
    F -- "✅ 绝缘等级与低碳铜溯源 100% 合规" --> H{"4. Web IQ 启用发卡废铜头闭环连铸 + 微孔发泡 PI？<br/>(12% 纯净铜切头免基价回炉 + 低介电发泡漆降本)"}
    H -- "💡 免除废铜头 LME 价差损耗并替代高价进口 PEEK" --> I["🧑‍⚖️ 300ms 触发 HTTP 409 Confirm<br/>HAIRPIN_SCRAP_COPPER_TOLLING_AND_FOAMED_PI_CONFIRM<br/>立省 $52,000 (净付 $273,000)"]
    H -- "⚡ 标准合规 800V 漆包扁线结算" --> J["✅ 20ms 自动放款 HTTP 200<br/>VERIFIED_EV_HAIRPIN_MAGNET_WIRE_SETTLED ($325,000)"]
```

### 3.2 传统“按线盘重量+工频耐压”路径 vs 智能体“高温 PDIV+低氧无气孔+废铜闭环”路径对比（`flowchart LR`）

```mermaid
flowchart LR
    subgraph Legacy["❌ 传统按重量与工频耐压盲付路径 (电晕击穿与激光焊气孔)"]
        L1["工频耐压合格但R角偏薄致高温PDIV仅880Vpk"] --> L2["铜杆含氧280ppm导致200个激光焊点炸出气孔"]
        L2 --> L3["电驱厂盲付 $325,000 绕制定子"]
        L3 --> L4["SiC高频脉冲蚀穿漆膜烧毁电机且废铜头被贱卖"]
    end

    subgraph Agentic["✅ Agentic 高温 PDIV + O2<=5ppm + Web IQ 废铜闭环路径"]
        A1["150°C PDIV>=1350Vpk + LECO O2<=5ppm + 零针孔签名"] --> A2["12ms/15ms 拦截R角薄漆电晕线与高氧焊孔线"]
        A2 --> A3["Web IQ 290ms UL1446核验 + 300ms 废铜头闭环/发泡PI"]
        A3 --> A4["净省 $52,000 铜材与绝缘费或 20ms 安全清算"]
    end
```

### 3.3 端到端毫秒级验真与资金清算时序图（`sequenceDiagram`）

```mermaid
sequenceDiagram
    autonumber
    participant Wire as 电磁线厂 & 高压局放/金相实验室 (Schleich PD / LECO O2)
    participant Gate as Agentic 800V 电驱供应链网关 (Policy Engine)
    participant WebIQ as Microsoft Web IQ (/v3/browse)
    participant Bank as 新能源汽车产业链托管行 (Escrow Rail)

    Wire->>Gate: 提交 800V 漆包扁线批次结算单 ($325,000) + 150°C PDIV 曲线与铜氧/导电率报文
    Gate->>Gate: Gate 1: 验算 150°C PDIV >= 1,350 Vpk、R 角漆厚 >= 110 μm 且在线火花 0 针孔 (12ms)
    alt R 角漆膜偏薄或高温 PDIV < 1,350 Vpk 存在 SiC 电晕击穿风险
        Gate-->>Wire: HTTP 403 LOW_PDIV_CORONA_INCEPTION_OR_CORNER_ENAMEL_PINHOLE_BLOCKED (拦截 $325,000)
    else 高频脉冲局放裕度与全长绝缘无针孔合格
        Gate->>Gate: Gate 2: 验算铜芯氧含量 O2 <= 5 ppm、导电率 >= 101.0% IACS 且 U 型折弯无脱漆 (15ms)
        alt 高氧铜杆 (>5 ppm) 引发激光焊气孔或 3D 发卡折弯漆膜开裂
            Gate-->>Wire: HTTP 422 HIGH_COPPER_OXYGEN_LASER_WELD_POROSITY_OR_BEND_CRACK_BLOCKED
        else 无氧激光焊接致密性与高导机械柔韧性合格
            Gate->>WebIQ: 检索 UL 1446 油冷绝缘系统证书 + Copper Mark 溯源 + 发卡废铜头闭环/发泡 PI 台账
            WebIQ-->>Gate: 返回 UL 1446/Copper Mark 合规 + 12% 发卡铜头闭环连铸与发泡 PI 抵扣 (-$52,000)
            alt UL 1446 ATF 油冷兼容性未认证或铜源违规
                Gate-->>Wire: HTTP 451 UL1446_INSULATION_SYSTEM_MISMATCH_OR_COPPER_MARK_HOLD (290ms)
            else 存在 $52,000 发卡废铜头闭环加工与微孔发泡 PI 降本红利
                Gate-->>Bank: HTTP 409 HAIRPIN_SCRAP_COPPER_TOLLING_AND_FOAMED_PI_CONFIRM (300ms 净付 $273,000)
            else 标准合规 800V 漆包扁线结算
                Gate->>Bank: HTTP 200 VERIFIED_EV_HAIRPIN_MAGNET_WIRE_SETTLED (20ms 释放 $325,000)
            end
        end
    end
```

---

## ④ 📊 架构师选型决策矩阵（Architect Decision Matrix）

| 评估维度 | 方案 A：传统按“线盘过磅重量 + 工频击穿” | 方案 B：仅加测常温直流电阻与千分尺外径 | **方案 C：高温 $\text{PDIV} \ge 1,350\text{ V}_{\text{pk}}$ + 低氧 $\le 5\text{ ppm}$ + Web IQ 废铜闭环托管（推荐）** |
| :--- | :--- | :--- | :--- |
| **核心电驱可靠性与效率锚点** | 50Hz 工频耐压 + 电子秤毛重 | 常温电阻 + 宽边/窄边总厚度 | **$150^\circ\text{C}\text{ PDIV} \ge 1,350\text{ V}_{\text{pk}}$ + $\text{O}_2 \le 5\text{ ppm}$ + $\ge 101\%\text{ IACS}$** |
| **SiC 逆变器高频脉冲电晕击穿防御** | ❌ 0%（工频耐压合格的线在 $50\text{ kV/}\mu\text{s}$ 尖峰下照样产生局部放电蚀穿） | ❌ 测总外径根本发现不了扁线四个 R 角处的犬骨效应漆膜减薄！ | **✅ `12 ms` 强制校验 $150^\circ\text{C}$ 高频脉冲 $\text{PDIV}$ 与四面 R 角激光漆厚（`HTTP 403`）** |
| **发卡端部激光焊“马蜂窝气孔”虚焊防御** | ❌ 低纯有氧铜（$\text{O}_2 > 200\text{ ppm}$）一上激光焊机全部炸出气孔报废定子 | ❌ 直流电阻测不出几十 $\text{ppm}$ 的氧化亚铜夹杂 | **✅ `15 ms` 锁定 LECO 铜芯含氧量 $\le 5\text{ ppm}$ 与 3D 折弯耐油（`HTTP 422`）** |
| **油冷定子 ATF 水解兼容性（UL 1446）门禁** | ❌ 漆膜在高温变速箱油中溶胀脱落堵塞油道 | ❌ 无第三方 UL 档案联机校验 | **✅ Web IQ `290 ms` 穿透核验 UL 1446 油冷档案与 Copper Mark（`HTTP 451`）** |
| **发卡纯净铜切头闭环连铸与发泡 PI 套利** | ❌ 12% 高纯无氧铜切头打折卖给废品站，全价买进口 PEEK | ❌ 冲压落料与线材采购财务割裂 | **✅ Web IQ `300 ms` 启用废铜头闭环 Tolling 与发泡 PI 立省 `$52,000`（`HTTP 409`）** |

---

## ⑤ 🧪 简明定量实测与 Benchmark 核心发现（含 7-Card 报告）

我们在 `lab/webiq_commerce_demo.py` 中内置了确定性策略评估器 `evaluate_ev_hairpin_magnet_wire_policy()`，并在 `tests/test_webiq_commerce_demo.py` 中完成全覆盖验证：

| 测试场景代号 | 输入特征与遥测参数 | 网关裁决状态码 | 动作标签（Action Pill） | 端到端延迟 | 清算金额 / 拦截亏损 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`mag_commit_ok`** | $150^\circ\text{C}$ `PDIV = 1,480 Vpk >= 1,350` + 0 针孔 + `O2 = 2.8 ppm <= 5` + `101.4% IACS` | **`HTTP 200`** | `Act automatically` | **`20 ms`** | 正常清算 **`$325,000.00`** |
| **`mag_pd_403`** | R 角漆膜减薄致 `PDIV = 880 Vpk < 1,350` 或存在火花针孔 (`high_temp_pdiv_corona_and_zero_pinhole_verified=False`) | **`HTTP 403`** | `Send to a human` | **`12 ms`** | 拦截 **`$325,000.00`** 电晕击穿风险线 |
| **`mag_oxy_422`** | 掺有氧铜致 `O2 = 280 ppm > 5 ppm` 激光焊炸气孔或折弯开裂 (`ofc_oxygen_ppm_iacs_and_hairpin_bend_passed=False`) | **`HTTP 422`** | `Send to a human` | **`15 ms`** | 拦截 **`$325,000.00`** 虚焊脱漆批次 |
| **`mag_ul_451`** | Web IQ 检出缺失 UL 1446 ATF 油冷认证或 Copper Mark 违约 (`webiq_ul1446_atf_oil_and_copper_mark_clean=False`) | **`HTTP 451`** | `Send to a human` | **`290 ms`** | 合规冻结 **`$325,000.00`** |
| **`mag_tol_409`** | Web IQ 启用 12% 发卡无氧铜切头闭环连铸来料加工与微孔发泡低介电 PI 方案 (`hairpin_scrap_copper_tolling_and_foamed_pi_savings_cents=5200000`) | **`HTTP 409`** | `Confirm` | **`300 ms`** | 净清算 **`$273,000.00`**（立省 **`$52,000.00`**） |

- **Perturbation Robustness（顺序反转稳健性）**：将 5 组 800V 漆包扁线遥测输入做正序/逆序扰动测试，裁决一致率 **100%（0.0 pts 漂移）**。

---

## ⑥ 🛠️ 附录：生产上线快速核验与售前打单清单（Architect Checklist）

### 6.1 适用边界：Good Fit vs Not For
- **✅ Good Fit（强烈推荐采用本架构）**：
  - 800V/1000V 新能源汽车碳化硅（SiC）电驱发卡式（Hairpin / I-Pin / X-Pin / 连续波绕）定子耐电晕 PI/PAI/PEEK 漆包铜扁线及 TU1 无氧铜杆（Oxygen-Free Copper）长协交割；
  - 电动垂直起降飞行器（eVTOL）高功率密度航空电机与兆瓦级高频固态变压器绕组线采购；
  - 电驱厂冲压平头裸铜废料闭环上引连铸来料加工（Copper Tolling）。
- **⛔ Not For（不适用或无需启用全部门禁）**：
  - 低压 $12\text{ V}$ 汽车雨刮器有刷小电机普通漆包圆线采购。

### 6.2 生产上线核验 Checklist（`- [ ]`）
- [ ] **$150^\circ\text{C}$ 高温高频脉冲局部放电起始电压（$\text{PDIV} \ge 1,350\text{ V}_{\text{pk}}$）与四面 R 角漆膜厚度必检**：彻底封死 SiC 逆变器行波反射尖峰引发的匝间电晕击穿。
- [ ] **TU1 无氧铜芯含氧量（LECO $\text{O}_2 \le 5\text{ ppm}$）与导电率（$\ge 101.0\%\text{ IACS}$）硬门禁**：杜绝定子 200 个发卡端头激光焊接出现氢气孔虚焊。
- [ ] **UL 1446 油冷变速箱油（ATF）热老化兼容性与 LME Copper Mark 核验**：通过 Web IQ 保障油冷电驱 15 年绝缘寿命。
- [ ] **Web IQ 发卡纯净无氧铜切头闭环连铸（Tolling）与微孔发泡 PI 对冲**：消除 $12\%$ 切头铜价差磨损并大幅压降超低介电常数绝缘成本。
