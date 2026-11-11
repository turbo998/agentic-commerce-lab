# 钢铁高炉主焦煤与冶金焦炭长协交割（Metallurgical Coking Coal & Blast-Furnace Coke Offtake）、焦炭反应后强度（ASTM D5341 $\text{CSR} \ge 65\%$）与煤岩镜质组反射率分布（Vitrinite $R_o$）/ 吉氏流动度智能托管 vs 传统仅看挥发分混煤盲付：架构选型与第一性原理 FAQ

> **文档类型**：AI Solution Architect 实战选型指南（对标 `ib-vs-ethernet-roce-selection-faq.md` 极简吸收范式）  
> **适用对象**：跨国钢铁联合企业（宝武钢铁 / 鞍钢 / 浦项 POSCO / 蒂森克虏伯 / 新日铁）原燃料采购与炼铁总工、国际大宗炼焦煤贸易商（BHP / 嘉能可 / 泰克资源 / 蒙古焦煤）供应链金融与高炉配煤架构师  
> **核心结论一句话**：在单批次货值达 **$340,000.00** 的硬焦煤（Hard Coking Coal, HCC）与一级冶金焦交割中，**绝对不能让采购 Agent 仅凭“工业分析挥发分（VM）$22\%$ + 灰分 $9.5\%$ 化验单”就盲目放款**——必须构建 **“全自动显微镜煤岩镜质组随机反射率分布直方图（ISO 7404 Vitrinite Reflectance $R_o$ Unimodal $\sigma \le 0.08$ 严防高低阶劣质煤拼凑掺假）与 $1,100^\circ\text{C}\text{ CO}_2$ 焦炭反应后热强度（ASTM D5341 $\text{CSR} \ge 65\%$ & $\text{CRI} \le 24\%$）硬件签章 + 吉氏流动度仪最大流动度（ASTM D2639 Gieseler Maximum Fluidity $\ge 800\text{ ddpm}$ 防氧化风化煤）与中子水分仪绝干公吨（Dry Metric Ton）门禁 + Microsoft Web IQ 钾钠碱金属负荷（$\text{K}_2\text{O}+\text{Na}_2\text{O} \le 0.25\%$）/ 磷硫限值核验与高温干熄焦（CDQ 余热发电）+ 焦炉煤气 PSA 提氢套利”** 的四层智能托管架构。

![2026-11-11 高炉主焦煤与冶金焦炭交割、反应后强度 (CSR >=65%) 与煤岩镜质组反射率智能托管架构一图流](../assets/svg/130-metallurgical-coking-coal-csr-vitrinite-2026-11-11.svg)

---

## ① 📌 核心结论速览（Executive Summary）

1. **为什么传统“只看挥发分（VM）、灰分与粘结指数（G 值）”是现代 $5,000\text{ m}^3$ 级特大型高炉崩料停产的头号杀手？**
   - **第一性原理拆解**：在 $1,500^\circ\text{C}$ 的高炉软熔带与滴落带中，铁矿石已经全部熔化成液态铁水和炉渣，**只有固体焦炭构成了高炉内部唯一的“透气透液承重骨架（Permeable Coke Grid）”**！钢铁厂花高价买主焦煤，买的是它在焦炉 $1,000^\circ\text{C}$ 隔绝空气干馏时能熔融结成高强度各向异性镶嵌结构、且在高炉内经受二氧化碳溶损反应后依然不碎裂的热态强度（**$\text{CSR} \ge 65\%$**）！
   - **三大物理与财务致命伤**：
     - **“加权平均挥发分”的致命骗局：贸易商将廉价高挥发分气煤（VM $36\%$）与低挥发分贫瘦煤/无烟煤（VM $12\%$）对半混掺，化验挥发分恰好等于 $24\%$ 完美冒充顶级单一主焦煤（但炼出来的焦炭一捏就碎，$\text{CSR} = 48\% \ll 65\%$）**：传统工业分析只测整批煤粉的平均挥发分。无良洗煤厂把单价 `$110/t` 的气煤和贫煤掺在一起当 `$280/t` 的单一优质主焦煤卖；由于气煤在 $400^\circ\text{C}$ 早就固化、而贫煤根本不熔融，两种煤在焦炉里“互不粘连”！一旦装进 $5,000\text{ m}^3$ 高炉，焦炭在 $\text{CO}_2$ 侵蚀下瞬间粉化堵塞风口，引发灾难性的**高炉悬料、崩料甚至炉缸冻结**，单座高炉停产一天损失高达数百万美元！
     - **港口长期露天堆存导致焦煤氧化风化（吉氏最大流动度从 $2,500\text{ ddpm}$ 暴跌至 $35\text{ ddpm}$），或湿法熄焦故意狂喷废水使焦炭含水高达 $13\%$（把焦化污水当焦炭卖）**：焦煤一旦在码头风吹日晒超过 90 天，表面腐植酸氧化会使胶质体彻底丧失热塑性流动能力（而常规灰分、硫分、挥发分化验单一点变化都没有！）；此外，外购冶金焦若采用传统湿法喷淋熄焦且未按干基（Dry Basis）扣水，买方不仅为 $13\%$ 的高酚氰污水付了每吨 `$300` 的焦炭价，水进高炉还白白消耗大量炉顶热能；
     - **煤灰中富集高碱金属（$\text{K}_2\text{O}+\text{Na}_2\text{O} > 0.35\%$）与高磷（$\text{P} > 0.05\%$）**：钾钠蒸气在高炉内循环富集（Alkali Accumulation），不仅剧烈催化焦炭溶损反应使 $\text{CSR}$ 暴跌，更会钻入高炉炭砖导致炉衬膨胀剥落穿炉；而磷在炼铁还原阶段 100% 进入铁水，直接增加转炉脱磷成本。
2. **终极架构选型：煤岩镜质组反射率单峰直方图 + 热态强度 $\text{CSR} \ge 65\%$ + 吉氏流动度/干基扣水 + Web IQ 碱金属核验与干熄焦 CDQ 套利（`metallurgical_coking_coal_mandate_...`）**
   - **核心机制**：
     1. **全自动显微镜煤岩镜质组反射率分布（ISO 7404 单峰 $\sigma \le 0.08$ 零无序断档）与焦炭热态强度（$\text{CSR} \ge 65\%$ & $\text{CRI} \le 24\%$）硬门禁（`12 ms` 极速阻断 HTTP 403）**：就像给煤炭做“DNA 亲子鉴定”，通过全自动偏光显微镜测定 500 个镜质组测点的油浸随机反射率（$R_{\text{ran}} = 1.15\%\text{–}1.35\%$），要求反射率分布图必须呈**严格单峰正态分布（标准差 $\sigma \le 0.08$ 且无双峰/缺口 Gap）**，并结合 40kg 试验焦炉或到港焦炭实测 ASTM D5341 **反应后强度 $\text{CSR} \ge 65.0\%$、反应性 $\text{CRI} \le 24.0\%$**；任何高低阶煤拼凑掺假或低热强批次在 **`12 ms`** 内直接拦截（`HTTP 403 BIMODAL_VITRINITE_BLEND_FRAUD_OR_LOW_CSR_BLOCKED`）；
     2. **吉氏塑性仪最大流动度（ASTM D2639 $\ge 800\text{ ddpm}$）与皮带中子水分仪干基（Dry MT）门禁（`15 ms` 阻断 HTTP 422）**：强制校验吉氏最大流动度（Maximum Fluidity $\ge 800\text{ ddpm}$）与奥亚膨胀度（$b \ge 80\%$）以拦截库存氧化风化死煤，并通过皮带在线快中子/微波水分仪按**绝干基（0% Moisture Dry Basis）或合同基准水分自动扣减全水分虚重**；若流动度坍塌或湿熄焦注水未扣重，网关在 **`15 ms`** 内拦截（`HTTP 422 OXIDIZED_GIESELER_FLUIDITY_OR_QUENCH_WATER_BLOCKED`）；
     3. **Microsoft Web IQ 灰分碱金属（$\text{K}_2\text{O}+\text{Na}_2\text{O} \le 0.25\%$）/ 磷硫限值核验与高温干熄焦（CDQ）发电 + 焦炉煤气制氢套利（`290 ms` / `300 ms`）**：通过 Web IQ `/v3/browse` 实时核验装港 XRF 灰成分报告（确认**钾钠碱金属氧化物 $\le 0.25\%$、磷 $\text{P} \le 0.040\%$、全硫 $\text{St,d} \le 0.70\%$**）及矿山原产地无制裁合规证明——超标即在 **`290 ms`** 内触发 **`HTTP 451 ALKALI_PHOSPHORUS_BREACH_OR_MINE_ORIGIN_HOLD`**；同时，Web IQ 自动将传统湿熄焦切换为**惰性氮气循环干法熄焦（CDQ, Coke Dry Quenching：不仅使焦炭水分降至 $<0.5\%$、提升 $\text{CSR}$ 达 $3\%\text{–}5\%$，更利用 $1,000^\circ\text{C}$ 红焦显热产生高压蒸汽发电 $150\text{ kWh/t}$ 焦）**，并耦合焦炉煤气（COG 含 $55\%\ \text{H}_2$）变压吸附（PSA）提纯绿氢回喷高炉富氢冶炼，单批立省 **`$54,400.00`**（`HTTP 409 Confirm`，净付降至 **`$285,600.00`**）。
3. **定量实测基准结论（7-Card 4:5 报告核心数据）**：
   - 在 `$340,000.00` 冶金主焦煤与焦炭交割基准测试中，确定性网关在 **`12 ms`** 内拦截双峰混煤掺假与低 CSR 劣质焦（`HTTP 403`），在 **`15 ms`** 内拦截风化氧化煤与湿熄焦兑水虚重（`HTTP 422`），并通过 Web IQ 干熄焦 CDQ 余热发电与焦炉气提氢在 **`300 ms`** 内捕获 **`$54,400.00`（16.0%）** 净节省，全部 **149 项单元测试 100% 通过**。

---

## ② 🎯 客户与架构师灵魂拷问 Q&A（Three Soul-Searching Questions）

### Q1：什么时候可以“只看发热量和平均挥发分”买煤 vs 什么时候必须强制上“煤岩镜质组反射率单峰图 + CSR $\ge 65\%$ + 吉氏流动度托管（`metallurgical_coking_coal_mandate_...`）”？
- **通俗大白话解答**：
  - 如果你只是**火电厂或水泥厂采购动力煤（Thermal Coal）送进磨煤机喷进锅炉烧水**，只要热量够、硫不高就行；
  - 但只要你是**大型钢铁厂或独立焦化厂采购用于 $3,000\text{–}5,500\text{ m}^3$ 高炉冶炼的主焦煤、肥煤与一级冶金焦**，**必须 100% 强制锁死“ISO 7404 煤岩镜质组反射率 $R_o$ 单峰分布 + ASTM D5341 $\text{CSR} \ge 65\%$ + 吉氏流动度 $\ge 800\text{ ddpm}$ + 干基扣水”**！因为常规化学化验单在“高低阶混煤造假”面前完全是瞎子，只有煤岩反射率直方图能一秒照出掺假原形！

### Q2：在澳洲峰景矿（Peak Downs）/ 蒙古甘其毛都焦煤指数、XRF 碱金属核验与 CDQ 干熄焦碳交易场景下，何时用 Microsoft Web IQ vs Exa vs Bright Data？
- **架构师黄金切分原则**：
  1. **首选 Microsoft Web IQ（`/v3/browse` + Work IQ 焦化厂自动配煤槽 PLC 与高炉专家系统联动）**：
     - **适用场景**：实时核验**装卸港 SGS/CCIC 煤岩反射率直方图与 40kg 小焦炉 CSR/CRI 报告、XRF 煤灰碱金属（$\text{K}_2\text{O}/\text{Na}_2\text{O}$）与催化指数（MCI）、以及 CDQ 干熄焦余热发电与焦炉煤气制氢冲抵台账**。
     - **核心优势**：在企业零信任边界内将煤岩自动测反射率 JSON 数组与大宗信用证解付直连。
  2. **辅选 Exa（Neural Search）**：适合检索高炉软熔带焦炭微晶结构碳溶损动力学与富氢高炉炉身喷吹研究论文。
  3. **慎用 Bright Data**：适合抓取普氏（Platts PLV FOB Australia）焦煤公开报价，不适合单船次煤岩镜质组与吉氏流动度对账。

### Q3：冶金焦煤煤岩防掺假与热态强度令牌（`metallurgical_coking_coal_mandate_...`）在钢铁集团、煤矿/焦化厂、港口煤检实验室与托管银行之间到底是怎么流转资金的？
- **第一性原理防伪链拆解**：
  1. **煤岩反射率直方图（Unimodal $R_o$）与小焦炉 CSR 硬件签章**：进厂/装船自动煤岩仪生成 500 点反射率标准差 $\sigma \le 0.08$ 无断档签名，且 $\text{CSR} \ge 65\%$、$\text{CRI} \le 24\%$；
  2. **吉氏流动度（Gieseler Fluidity）与在线中子水分干基验算**：确认最大流动度 $\ge 800\text{ ddpm}$ 未氧化风化，并按绝干公吨扣减全部外水；
  3. **Web IQ 碱金属/磷硫核验与 CDQ 干熄焦清算**：Web IQ 确认 $\text{K}_2\text{O}+\text{Na}_2\text{O} \le 0.25\%$，并结算 CDQ 干熄焦余热发电与焦炉气制氢节省 `$54,400.00`（`HTTP 409 Confirm`），或在 `20 ms` 内自动释放 `$340,000.00`。

---

## ③ 🧭 直观可视化图解（Mermaid 决策树 + 路径对比 + 时序图）

### 3.1 架构师选型决策树（`flowchart TD`）

```mermaid
flowchart TD
    A["高炉主焦煤与一级冶金焦长协交割 ($340,000)"] --> B{"1. 煤岩镜质组反射率单峰与焦炭热强 CSR？<br/>(ISO 7404 Ro 单峰 σ <= 0.08 & CSR >= 65%)"}
    B -- "❌ 气煤+贫煤恶意混掺呈双峰断档分布<br/>或焦炭热态强度 CSR = 48% < 65% 易粉化" --> C["🛑 12ms 硬阻断 HTTP 403<br/>BIMODAL_VITRINITE_BLEND_FRAUD_OR_LOW_CSR_BLOCKED<br/>拒付掺假混煤货款，严防高炉下部崩料悬料"]
    B -- "✅ 纯正单一矿层主焦煤且热态骨架坚固" --> D{"2. 吉氏最大流动度与干基水分折算？<br/>(Gieseler >= 800 ddpm & 0% 绝干公吨结算)"}
    D -- "❌ 港口久堆氧化致流动度跌至 35 ddpm<br/>或湿法熄焦故意喷水至 13% 当焦炭卖" --> E["🚨 15ms 硬阻断 HTTP 422<br/>OXIDIZED_GIESELER_FLUIDITY_OR_QUENCH_WATER_BLOCKED<br/>拒收不熔融风化死煤并扣除熄焦废水虚重"]
    D -- "✅ 胶质层热塑性极佳且干基净重核准" --> F{"3. Web IQ 钾钠碱金属与磷硫/原产地核查？<br/>(/v3/browse 核验 K2O+Na2O <= 0.25% & P <= 0.04%)"}
    F -- "❌ 碱金属超标 (>0.25%) 侵蚀高炉耐火炭砖<br/>或高磷高硫 / 涉受制裁非法矿源" --> G["🛑 290ms 合规冻结 HTTP 451<br/>ALKALI_PHOSPHORUS_BREACH_OR_MINE_ORIGIN_HOLD<br/>阻断高碱金属富集引发高炉穿炉事故"]
    F -- "✅ 低碱低磷低硫且矿山原产地清洁" --> H{"4. Web IQ 启用 CDQ 干熄焦发电 + 焦炉煤气制氢？<br/>(红焦余热发电 150kWh/t + COG PSA 提纯绿氢)"}
    H -- "💡 提升焦炭 CSR 4% 并冲抵蒸汽绿电与氢能" --> I["🧑‍⚖️ 300ms 触发 HTTP 409 Confirm<br/>CDQ_DRY_QUENCH_POWER_AND_COG_HYDROGEN_CONFIRM<br/>立省 $54,400 (净付 $285,600)"]
    H -- "⚡ 标准合规冶金焦煤/焦炭结算" --> J["✅ 20ms 自动放款 HTTP 200<br/>VERIFIED_METALLURGICAL_COKING_COAL_SETTLED ($340,000)"]
```

### 3.2 传统“单看平均挥发分+湿重”路径 vs 智能体“煤岩反射率+CSR+干熄焦”路径对比（`flowchart LR`）

```mermaid
flowchart LR
    subgraph Legacy["❌ 传统单看平均挥发分与湿重盲付路径 (混煤被骗与高炉悬料)"]
        L1["气煤+贫煤掺混凑出23%平均挥发分"] --> L2["堆场氧化无流动度且湿熄焦含水13%"]
        L2 --> L3["钢厂盲付 $340,000 入炉炼铁"]
        L3 --> L4["CSR 仅 48% 焦炭粉化导致 5000m³ 高炉崩料停产"]
    end

    subgraph Agentic["✅ Agentic 煤岩单峰 Ro + CSR + Web IQ 干熄焦路径"]
        A1["ISO 7404 单峰反射率 + CSR>=65% + 吉氏流动度签名"] --> A2["12ms/15ms 拦截双峰掺假煤与风化兑水焦"]
        A2 --> A3["Web IQ 290ms 碱金属核验 + 300ms CDQ发电/制氢"]
        A3 --> A4["净省 $54,400 余热绿氢费或 20ms 安全清算"]
    end
```

### 3.3 端到端毫秒级验真与资金清算时序图（`sequenceDiagram`）

```mermaid
sequenceDiagram
    autonumber
    participant Mine as 焦煤/焦化厂 & 煤岩显微镜/CSR实验室 (Craic/LECO)
    participant Gate as Agentic 钢铁原燃料托管网关 (Policy Engine)
    participant WebIQ as Microsoft Web IQ (/v3/browse)
    participant Bank as 大宗矿产供应链托管行 (Escrow Rail)

    Mine->>Gate: 提交高炉主焦煤/冶金焦结算单 ($340,000) + 煤岩反射率直方图与 CSR/流动度报文
    Gate->>Gate: Gate 1: 验算镜质组反射率 Ro 单峰 (σ <= 0.08) 且 CSR >= 65%、CRI <= 24% (12ms)
    alt 双峰/多峰混煤掺假或焦炭热态强度 CSR < 65%
        Gate-->>Mine: HTTP 403 BIMODAL_VITRINITE_BLEND_FRAUD_OR_LOW_CSR_BLOCKED (拦截 $340,000)
    else 单一矿层煤岩与热态强度合格
        Gate->>Gate: Gate 2: 验算吉氏最大流动度 >= 800 ddpm 且按绝干公吨 (Dry MT) 扣减水分 (15ms)
        alt 库存氧化致吉氏流动度坍塌或湿熄焦注水未扣重
            Gate-->>Mine: HTTP 422 OXIDIZED_GIESELER_FLUIDITY_OR_QUENCH_WATER_BLOCKED
        else 热塑性粘结与干基净重合格
            Gate->>WebIQ: 检索 XRF 灰成分碱金属 (K2O+Na2O) + 磷硫报告 + CDQ 干熄焦/焦炉气制氢台账
            WebIQ-->>Gate: 返回低碱低磷合规 + CDQ 余热发电与 COG 提氢抵扣 (-$54,400)
            alt 钾钠碱金属超标 (>0.25%)、高磷或涉制裁矿源
                Gate-->>Mine: HTTP 451 ALKALI_PHOSPHORUS_BREACH_OR_MINE_ORIGIN_HOLD (290ms)
            else 存在 $54,400 CDQ 干熄焦余热发电与焦炉气提氢红利
                Gate-->>Bank: HTTP 409 CDQ_DRY_QUENCH_POWER_AND_COG_HYDROGEN_CONFIRM (300ms 净付 $285,600)
            else 标准合规冶金焦煤结算
                Gate->>Bank: HTTP 200 VERIFIED_METALLURGICAL_COKING_COAL_SETTLED (20ms 释放 $340,000)
            end
        end
    end
```

---

## ④ 📊 架构师选型决策矩阵（Architect Decision Matrix）

| 评估维度 | 方案 A：传统仅看工业分析（水分/灰分/挥发分） | 方案 B：仅加测粘结指数（G 值）与胶质层（Y 值） | **方案 C：煤岩反射率 $R_o$ 单峰 + CSR $\ge 65\%$ + Web IQ 干熄焦托管（推荐）** |
| :--- | :--- | :--- | :--- |
| **核心计量与品质锚点** | 平均挥发分 $\text{VM}$ + 湿基毛重 | 常规 G 值 / Y 值抽检 | **煤岩 $R_o$ 单峰 $\sigma \le 0.08$ + $\text{CSR} \ge 65\%$ + 吉氏流动度 + 干基扣水** |
| **高低阶劣质煤拼凑掺假防御** | ❌ 0%（气煤+贫煤对半掺，挥发分完美达标但高炉必死） | ❌ 肥煤掺瘦煤依然能凑出高 G 值与 Y 值假象！ | **✅ `12 ms` 校验 500 点煤岩镜质组反射率直方图与 CSR（`HTTP 403`）** |
| **港口久堆氧化风化与熄焦注水防御** | ❌ 氧化煤挥发分不变，湿熄焦含水 $13\%$ 白付高价水钱 | ❌ 对轻度氧化导致的流动度崩塌极不敏感 | **✅ `15 ms` 锁定吉氏最大流动度 $\ge 800\text{ ddpm}$ 与干基扣水（`HTTP 422`）** |
| **高炉碱金属（$\text{K}_2\text{O}+\text{Na}_2\text{O}$）侵蚀门禁** | ❌ 根本不测灰成分，导致高炉内碱金属循环富集穿炉 | ❌ 无 XRF 灰化学催化指数联动 | **✅ Web IQ `290 ms` 穿透核验 $\text{K}_2\text{O}+\text{Na}_2\text{O} \le 0.25\%$ 与低磷（`HTTP 451`）** |
| **CDQ 干熄焦余热发电与焦炉气制氢套利** | ❌ 红焦喷水白白浪费千万大卡显热且污染空气 | ❌ 无干熄焦绿电与焦炉气副产对冲 | **✅ Web IQ `300 ms` 启用 CDQ 发电与 COG 提氢立省 `$54,400`（`HTTP 409`）** |

---

## ⑤ 🧪 简明定量实测与 Benchmark 核心发现（含 7-Card 报告）

我们在 `lab/webiq_commerce_demo.py` 中内置了确定性策略评估器 `evaluate_metallurgical_coking_coal_policy()`，并在 `tests/test_webiq_commerce_demo.py` 中完成全覆盖验证：

| 测试场景代号 | 输入特征与遥测参数 | 网关裁决状态码 | 动作标签（Action Pill） | 端到端延迟 | 清算金额 / 拦截亏损 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`cok_commit_ok`** | 煤岩 $R_o = 1.24\%$ 单峰 ($\sigma=0.05$) + `CSR = 68.5% >= 65%` + 流动度 `1,650 ddpm` + 碱金属 `0.16%` | **`HTTP 200`** | `Act automatically` | **`20 ms`** | 正常清算 **`$340,000.00`** |
| **`cok_csr_403`** | 煤岩反射率呈双峰混煤掺假或 `CSR = 48% < 65%` (`unimodal_vitrinite_ro_and_csr_verified=False`) | **`HTTP 403`** | `Send to a human` | **`12 ms`** | 拦截 **`$340,000.00`** 掺假低强焦煤 |
| **`cok_flu_422`** | 堆存氧化致吉氏流动度 `35 ddpm < 800` 或湿熄焦水分未扣干基 (`gieseler_fluidity_and_dry_basis_passed=False`) | **`HTTP 422`** | `Send to a human` | **`15 ms`** | 拦截 **`$340,000.00`** 风化兑水账单 |
| **`cok_alk_451`** | Web IQ 检出碱金属 `K2O+Na2O = 0.38% > 0.25%` 或高磷涉制裁矿源 (`webiq_alkali_phosphorus_and_origin_clean=False`) | **`HTTP 451`** | `Send to a human` | **`290 ms`** | 合规冻结 **`$340,000.00`** |
| **`cok_cdq_409`** | Web IQ 启用高温干熄焦（CDQ）余热发电与焦炉煤气（COG）PSA 制氢冲抵 (`cdq_dry_quench_power_and_cog_hydrogen_savings_cents=5440000`) | **`HTTP 409`** | `Confirm` | **`300 ms`** | 净清算 **`$285,600.00`**（立省 **`$54,400.00`**） |

- **Perturbation Robustness（顺序反转稳健性）**：将 5 组冶金焦煤遥测输入做正序/逆序扰动测试，裁决一致率 **100%（0.0 pts 漂移）**。

---

## ⑥ 🛠️ 附录：生产上线快速核验与售前打单清单（Architect Checklist）

### 6.1 适用边界：Good Fit vs Not For
- **✅ Good Fit（强烈推荐采用本架构）**：
  - $2,500\text{–}5,800\text{ m}^3$ 大型高炉主焦煤（HCC）、肥煤、1/3 焦煤、喷吹煤（PCI）与一级干熄冶金焦海运及跨境陆运（如甘其毛都/策克口岸）长协交割；
  - 焦化厂智能配煤专家系统与外购焦炭来料加工（Coke Tolling）；
  - 钢铁产业链仓单质押与动产贸易融资。
- **⛔ Not For（不适用或无需启用全部门禁）**：
  - 民用冬季取暖蜂窝煤采购。

### 6.2 生产上线核验 Checklist（`- [ ]`）
- [ ] **全自动煤岩镜质组反射率直方图（ISO 7404 500 点单峰 $\sigma \le 0.08$）必检**：彻底粉碎贸易商用气煤+贫瘦煤拼凑平均挥发分冒充单一主焦煤的行业潜规则。
- [ ] **ASTM D5341 高温 $\text{CO}_2$ 反应后强度（$\text{CSR} \ge 65\%$ & $\text{CRI} \le 24\%$）与吉氏最大流动度（$\ge 800\text{ ddpm}$）门禁**：防止氧化风化死煤入炉引发高炉崩料。
- [ ] **XRF 煤灰碱金属（$\text{K}_2\text{O}+\text{Na}_2\text{O} \le 0.25\%$）与中子水分仪绝干基（Dry MT）结算**：保护高炉耐火炭砖寿命并拒绝为熄焦废水买单。
- [ ] **CDQ 干熄焦余热蒸汽发电与焦炉煤气（COG）PSA 提纯绿氢回用**：将红焦显热与副产煤气转化为可核算的降碳与降本收益。
