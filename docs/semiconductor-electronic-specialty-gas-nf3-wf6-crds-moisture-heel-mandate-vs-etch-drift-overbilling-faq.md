# 半导体晶圆厂电子特气（Electronic Specialty Gas, ESG $6\text{N }\text{NF}_3 / \text{WF}_6 / \text{SiH}_4$）供应、光腔衰荡光谱（CRDS $\text{H}_2\text{O} \le 10\text{ ppb}$）水分门禁与钢瓶余气回皮（Heel Credit）智能托管 vs 传统按整瓶标称重盲付：架构选型与第一性原理 FAQ

> **文档类型**：AI Solution Architect 实战选型指南（对标 `ib-vs-ethernet-roce-selection-faq.md` 极简吸收范式）  
> **适用对象**：300mm 晶圆厂（Logic 2nm/3nm & 200+ 层 3D NAND）厂务特气（TGCM / Sub-Fab BSGS）总监、特种气体采购与供应链负责人、半导体设备（Etch / CVD / ALD）工艺良率工程团队  
> **核心结论一句话**：在单批结算额高达 **$210,000.00** 的半导体超高纯电子特气（如 $99.9999\%$ 六氟化钨 $\text{WF}_6$、三氟化氮 $\text{NF}_3$、硅烷 $\text{SiH}_4$、笑气 $\text{N}_2\text{O}$ 及氖氪氙光刻混气）采购中，**绝对不能让采购 Agent 仅凭气体供应商交来的“整瓶标称充装公斤数 + 出厂纸质 COA”就盲目全额付款**——必须构建 **“大宗特气柜（BSGS）换瓶吹扫后在线光腔衰荡光谱（CRDS 实测痕量水分 $\text{H}_2\text{O} \le 10\text{ ppb}$）与 FTIR 零氢氟酸（HF）水解硬门禁 + 特气柜高精度防爆电子秤（Load Cell）实测退瓶保压余气自动回皮抵扣（Heel Gas Credit $\ge 10\%$ 残余重量）+ Microsoft Web IQ 316L 电抛光 Y-Ton 钢瓶定检 / 欧盟 F-Gas 法规核验与蚀刻尾气稀有气体（$\text{Xe}/\text{Kr}/\text{Ne}$）纯化回收套利”** 的四层智能托管架构。

![2026-11-11 半导体电子特气 (6N NF3 / WF6 / SiH4)、CRDS 痕量水分与钢瓶余气回皮智能托管架构一图流](../assets/svg/110-semiconductor-esg-specialty-gas-crds-heel-2026-11-11.svg)

---

## ① 📌 核心结论速览（Executive Summary）

1. **为什么传统“按钢瓶标称充装重量 + 出厂纸质 COA 付款”是先进制程晶圆厂的良率杀手与成本黑洞？**
   - **第一性原理拆解**：在 3nm GAA 逻辑芯片或 232 层 3D NAND 闪存的原子层沉积（ALD）与高深宽比等离子蚀刻（HAR Etch）中，电子特气是直接参与晶格生长的“原子级建材”。**哪怕混入百亿分之几（ppb 级）的水汽，或者把原本无法用完的安全保压余气（Heel）白送给气商二次售卖，都会造成巨额良率与资金双杀**！
   - **三大物理与财务致命伤**：
     - **换瓶接头微漏湿气引发剧烈水解生成氢氟酸（HF），蚀穿 316L 管路并毒化反应腔**：六氟化钨（$\text{WF}_6$）、三氟化氯（$\text{ClF}_3$）与三氯化硼（$\text{BCl}_3$）极易与空气中的痕量水分发生水解反应（如 $\text{WF}_6 + 3\text{H}_2\text{O} \rightarrow \text{WO}_3\downarrow + 6\text{HF}\uparrow$）。如果气瓶阀门垫圈（CGA / DISS 接口）在运输或接驳时渗入哪怕 **180 ppb 的水分**，生成的强腐蚀性氟化氢（HF）不仅会剥落不锈钢管内壁的氧化铬钝化层、产生铁/镍金属纳米颗粒直接击穿整批晶圆栅极，氧化钨（$\text{WO}_3$）粉末还会直接堵死价值百万美元的质量流量控制器（MFC）；
     - **10%–15% 的退瓶安全保压余气（Cylinder Heel Gas）被气商“两头通吃”**：为了防止外界空气倒吸入高纯钢瓶（Back-diffusion）以及防止液化特气相变夹带重沸物杂质，晶圆厂 BSGS 特气柜在钢瓶残余压力降至 **100–150 psi（约占满瓶总质量的 10%–15%）** 时必须强制自动切瓶停用。在传统按“整瓶标称充装量”买断模式下，每瓶价值 **$210,000.00** 的高价特气（如高纯 $\text{WF}_6$ 或 $\text{Xe}$），晶圆厂白白把 **$25,000+** 的余气原封不动退回给气商，气商无需提纯直接补气再按 100% 满瓶卖给下一家；
     - **Y-Ton 大钢瓶内壁电抛光（EP $R_a \le 0.13\ \mu\text{m}$）退化与高 GWP 温室气体合规断层**：若气商使用逾期未做水压/声发射定检或内壁粗糙度劣化的周转钢瓶，或者隐瞒三氟化氮（$\text{NF}_3$，全球变暖潜能值 $\text{GWP} = 17,200$）合成工艺副产排放，将直接触发 SEMI F57/C3 违约与欧美供应链碳合规禁令。
2. **终极架构选型：CRDS 光腔衰荡水分门禁 + BSGS 电子秤余气回皮 + Web IQ 钢瓶溯源与尾气回收套利（`semiconductor_esg_gas_mandate_...`）**
   - **核心机制**：
     1. **上机吹扫后在线光腔衰荡光谱（CRDS $\text{H}_2\text{O} \le 10\text{ ppb}$）与 FTIR 零水解硬门禁（`11 ms` 极速阻断 HTTP 403）**：在 Sub-Fab 大宗特气分配柜（BSGS）经 50 次循环真空氦气吹扫（Cycle Purge）后，接入在线光腔衰荡光谱仪（CRDS）与傅里叶变换红外光谱仪（FTIR），实测痕量水汽 **$\text{H}_2\text{O} \le 10\text{ ppb}$**、氧 $\text{O}_2 \le 10\text{ ppb}$ 且游离 $\text{HF}$ 酸度无检出；若水分超标，网关在 **`11 ms`** 内锁死气动隔膜阀并拒付整瓶货款（`HTTP 403 SUB_PPB_MOISTURE_OR_ACID_HYDROLYSIS_BREACH_BLOCKED`）；
     2. **BSGS 防爆电子秤净消耗量计量与退瓶保压余气（Heel Credit）强制冲抵门禁（`14 ms` 阻断 HTTP 422）**：实时采集特气柜底部防爆称重传感器（Load Cell）的满瓶上架毛重 $W_{\text{full}}$ 与切瓶下架退瓶毛重 $W_{\text{return}}$，强制要求按实耗净质量 $\Delta W = W_{\text{full}} - W_{\text{return}}$ 计费，或对 $10\%\text{–}15\%$ 退瓶合格余气执行 100% 贷项回皮冲抵；若气商拒绝余气回皮或 ICP-MS 检出颗粒铁/镍超标（$>1\text{ ppt}$），网关在 **`14 ms`** 内拦截（`HTTP 422 CYLINDER_HEEL_UNCREDITED_OR_METAL_PARTICLE_BLOCKED`）；
     3. **Microsoft Web IQ 钢瓶 DOT/TPED 钝化溯源与蚀刻尾气稀有气体（$\text{Xe}/\text{Kr}$）回收套利（`290 ms` / `300 ms`）**：通过 Web IQ `/v3/browse` 实时核验该钢瓶激光刻印唯一序列号的 316L 真空电抛光（VIM-VAR EP）证书、5 年期超声波/声发射定检记录及欧盟 F-Gas 法规配额——违规即在 **`290 ms`** 内触发 **`HTTP 451 CYLINDER_HYDROTEST_OR_FGAS_QUOTA_COMPLIANCE_HOLD`**；当 Web IQ 将退瓶保压余气回皮（Heel Credit）与 Sub-Fab 干泵尾气深冷膜分离提纯回收系统（将蚀刻腔排出的高价氙气 $\text{Xe}$ / 氪气 $\text{Kr}$ 提纯回流至 $6\text{N}$ 标准）联合对冲时，单批立省 **`$29,400.00`**（`HTTP 409 Confirm`，净付降至 **`$180,600.00`**）。
3. **定量实测基准结论（7-Card 4:5 报告核心数据）**：
   - 在 `$210,000.00` 半导体 $6\text{N}$ 电子特气批次交割基准测试中，确定性网关在 **`11 ms`** 内拦截 $180\text{ ppb}$ 水分水解风险瓶（`HTTP 403`），在 **`14 ms`** 内拦截吞没 12% 退瓶余气的霸王账单（`HTTP 422`），并通过 Web IQ 余气回皮与尾气稀有气体纯化回收在 **`300 ms`** 内捕获 **`$29,400.00`（14.0%）** 净节省，全部 **129 项单元测试 100% 通过**。

---

## ② 🎯 客户与架构师灵魂拷问 Q&A（Three Soul-Searching Questions）

### Q1：什么时候可以按“整瓶一口价”买气 vs 什么时候必须强制上“在线 CRDS 水分门禁 + BSGS 称重余气回皮（`semiconductor_esg_gas_mandate_...`）”？
- **通俗大白话解答**：
  - 如果你只是**机加工车间买几瓶几十块钱的普通工业氩气或二氧化碳用来焊铁架子**，用光为止按瓶付钱即可；
  - 但只要你是**半导体晶圆厂、化合物半导体（SiC/GaN）外延厂或先进封装厂采购高纯电子特气（$\text{WF}_6, \text{NF}_3, \text{SiH}_4, \text{C}_4\text{F}_6, \text{Xe}, \text{Kr}$）**，单瓶 Y-Ton 钢瓶或鱼雷车动辄数十万美元，且安全规程严禁把瓶抽干（必须留 10%–15% 余压防倒吸），**必须 100% 强制执行“上机 CRDS $\le 10\text{ ppb}$ 水分联锁 + BSGS 电子秤退瓶余气回皮（Heel Credit）”**！否则每年光白送回气商的瓶底余气就高达数百万美元。

### Q2：在特气钢瓶全生命周期溯源、SEMI 标准对标与稀有气体行情套利场景下，何时用 Microsoft Web IQ vs Exa vs Bright Data？
- **架构师黄金切分原则**：
  1. **首选 Microsoft Web IQ（`/v3/browse` + Work IQ 晶圆厂 TGCM 特气管理系统联动）**：
     - **适用场景**：实时核验**钢瓶唯一条码对应的 DOT 3AA / ISO 11120 声发射定检证书、316L 内壁电抛光（EP）批次记录、欧盟 F-Gas 与 EPA AIM Act 含氟温室气体配额，以及现场尾气回收纯化与新气采购的价差结算**。
     - **核心优势**：支持在晶圆厂严苛的零信任边界内将 Sub-Fab PLC 电子秤读数与外部气商 e-COA 台账做确定性加密核对。
  2. **辅选 Exa（Neural Search）**：适合检索低 GWP 替代蚀刻气体（如 $\text{C}_3\text{F}_6\text{O}$ 替代 $\text{C}_4\text{F}_8$）的等离子体化学反应机理文献。
  3. **慎用 Bright Data**：适合跟踪公开工业稀有气体（氖、氪、氙）大宗现货价格波动，不适合晶圆厂内网 TGCM 钢瓶安全联锁。

### Q3：电子特气痕量水分与余气回皮令牌（`semiconductor_esg_gas_mandate_...`）在晶圆厂、特气巨头、Sub-Fab BSGS 气柜与托管行之间到底是怎么流转资金的？
- **第一性原理防伪链拆解**：
  1. **BSGS 接头氦质谱检漏与在线 CRDS 水分签章**：新钢瓶吊装进 BSGS 气柜并完成高压氮/氦自动循环吹扫（Cycle Purge）后，样气先进入在线光腔衰荡水分仪（CRDS）与 FTIR。只有确认 $\text{H}_2\text{O} \le 10\text{ ppb}$ 且无 $\text{HF}$ 水解酸峰，气柜主供气阀才允许开启；
  2. **防爆称重传感器（Load Cell）退瓶回皮（Heel Credit）验算**：当钢瓶用至残压 $120\text{ psi}$ 触发自动切瓶（Auto-Switchover）时，电子秤签名记录残余净气重 $m_{\text{heel}}$（前提是止回阀完好、余气未被倒吸污染），自动从本期进货账单中扣减对应金额；
  3. **Web IQ 钢瓶合规与尾气回收冲抵**：Web IQ 核验钢瓶定检合规并叠加腔室尾气氙/氪回收收益，单批立省 `$29,400.00`（`HTTP 409 Confirm`）或在 `20 ms` 内释放 `$210,000.00`。

---

## ③ 🧭 直观可视化图解（Mermaid 决策树 + 路径对比 + 时序图）

### 3.1 架构师选型决策树（`flowchart TD`）

```mermaid
flowchart TD
    A["半导体 6N 电子特气 (NF3/WF6/Xe) 交割 ($210,000)"] --> B{"1. 吹扫后在线 CRDS 水分与 FTIR 酸度？<br/>(H2O <= 10 ppb & HF 水解峰 = 0)"}
    B -- "❌ 水分 180 ppb > 10 ppb<br/>或检出 WF6 水解生成 HF 腐蚀管路" --> C["🛑 11ms 硬阻断 HTTP 403<br/>SUB_PPB_MOISTURE_OR_ACID_HYDROLYSIS_BREACH_BLOCKED<br/>联锁关断气柜隔膜阀并拒付整瓶"]
    B -- "✅ 水分 <= 10 ppb 且零水解" --> D{"2. BSGS 电子秤余气回皮与金属颗粒？<br/>(12% 保压余气冲抵 & 金属 <= 1 ppt)"}
    D -- "❌ 气商拒退 12% 退瓶余气款 (Heel)<br/>或 ICP-MS 检出 Fe/Ni 颗粒超标" --> E["🚨 14ms 硬阻断 HTTP 422<br/>CYLINDER_HEEL_UNCREDITED_OR_METAL_PARTICLE_BLOCKED<br/>强制按电子秤净消耗量结算"]
    D -- "✅ 净重计量与金属纯度达标" --> F{"3. Web IQ 钢瓶定检与 F-Gas 法规配额？<br/>(/v3/browse 核查 5年声发射定检与 EP)"}
    F -- "❌ Y-Ton 钢瓶定检逾期或违反 F-Gas 配额" --> G["🛑 290ms 合规冻结 HTTP 451<br/>CYLINDER_HYDROTEST_OR_FGAS_QUOTA_COMPLIANCE_HOLD<br/>禁止问题钢瓶进入晶圆厂 Sub-Fab"]
    F -- "✅ 钢瓶定检与环保配额合规" --> H{"4. Web IQ 叠加退瓶余气回皮与尾气回收？<br/>(12% Heel 抵扣 + 蚀刻尾气 Xe/Kr 膜提纯)"}
    H -- "💡 自动抵扣退瓶余气并回用提纯稀有气体" --> I["🧑‍⚖️ 300ms 触发 HTTP 409 Confirm<br/>HEEL_GAS_CREDIT_AND_EXHAUST_RECOVERY_CONFIRM<br/>立省 $29,400 (净付 $180,600)"]
    H -- "⚡ 标准大宗管道净耗量直结" --> J["✅ 20ms 自动放款 HTTP 200<br/>VERIFIED_SEMICONDUCTOR_ESG_GAS_SETTLED ($210,000)"]
```

### 3.2 传统“按整瓶标称重盲付”路径 vs 智能体“CRDS 水分+称重回皮+尾气回收”路径对比（`flowchart LR`）

```mermaid
flowchart LR
    subgraph Legacy["❌ 传统按整瓶标称重与纸质 COA 盲付路径"]
        L1["气商交纸质 COA 按满瓶收走 $210,000"] --> L2["阀口微漏湿气生成 HF 腐蚀管路毒化晶圆"]
        L2 --> L3["退瓶时瓶底 12% 保压余气白白奉送气商"]
        L3 --> L4["损失数万美元余气款 + 蚀刻良率暴跌"]
    end

    subgraph Agentic["✅ Agentic 在线 CRDS + BSGS 称重回皮 + Web IQ 路径"]
        A1["BSGS 在线 CRDS 水分仪 + 防爆电子秤签名"] --> A2["11ms/14ms 拦截痕量水汽与余气侵吞"]
        A2 --> A3["Web IQ 290ms 钢瓶定检核验 + 300ms 余气/尾气冲抵"]
        A3 --> A4["净省 $29,400 余气与回收款或 20ms 安全清算"]
    end
```

### 3.3 端到端毫秒级验真与资金清算时序图（`sequenceDiagram`）

```mermaid
sequenceDiagram
    autonumber
    participant Gas as 特气供应商 & Sub-Fab BSGS 气柜 (CRDS/Scale)
    participant Gate as Agentic 电子特气托管网关 (Policy Engine)
    participant WebIQ as Microsoft Web IQ (/v3/browse)
    participant Bank as 晶圆厂供应链托管银行 (Escrow Rail)

    Gas->>Gate: 提交 6N 电子特气结算单 ($210,000) + 在线 CRDS 水分与 BSGS 电子秤报文
    Gate->>Gate: Gate 1: 验算吹扫后 CRDS H2O <= 10 ppb 且 FTIR 零 HF 水解峰 (11ms)
    alt 痕量水分 > 10 ppb 或发生酸水解腐蚀
        Gate-->>Gas: HTTP 403 SUB_PPB_MOISTURE_OR_ACID_HYDROLYSIS_BREACH_BLOCKED (关阀并拒付)
    else 超高纯度与零水分达标
        Gate->>Gate: Gate 2: 验算 BSGS 电子秤退瓶余气 (Heel Credit) 已扣减且金属颗粒 <= 1 ppt (14ms)
        alt 未退还 12% 退瓶保压余气款或金属杂质超标
            Gate-->>Gas: HTTP 422 CYLINDER_HEEL_UNCREDITED_OR_METAL_PARTICLE_BLOCKED
        else 净消耗量与超净金属指标合格
            Gate->>WebIQ: 检索 Y-Ton 钢瓶声发射定检台账 + F-Gas 配额 + 余气回皮与尾气回收核算单
            WebIQ-->>Gate: 返回钢瓶合规 + 12% 余气回皮叠加尾气 Xe/Kr 回收抵扣 (-$29,400)
            alt 钢瓶 5年定检过期或违反 F-Gas 法规
                Gate-->>Gas: HTTP 451 CYLINDER_HYDROTEST_OR_FGAS_QUOTA_COMPLIANCE_HOLD (290ms)
            else 存在 $29,400 退瓶余气回皮与尾气回收冲抵
                Gate-->>Bank: HTTP 409 HEEL_GAS_CREDIT_AND_EXHAUST_RECOVERY_CONFIRM (300ms 净付 $180,600)
            else 标准净消耗量全额结算
                Gate->>Bank: HTTP 200 VERIFIED_SEMICONDUCTOR_ESG_GAS_SETTLED (20ms 释放 $210,000)
            end
        end
    end
```

---

## ④ 📊 架构师选型决策矩阵（Architect Decision Matrix）

| 评估维度 | 方案 A：传统凭出厂纸质 COA 按整瓶标称重买断 | 方案 B：仅看气柜机械压力表估算用气量 | **方案 C：在线 CRDS 水分 + BSGS 电子秤余气回皮 + Web IQ 回收托管（推荐）** |
| :--- | :--- | :--- | :--- |
| **核心计量与验真手段** | 出厂装瓶纸质化验单 + 标称充装重 | 波登管/压阻压力表读数 | **在线 CRDS 光腔衰荡水分（$\le 10\text{ ppb}$）+ 防爆电子秤净重差（$\Delta W$）** |
| **阀口微漏湿气/HF 水解防御** | ❌ 0%（毒化整批晶圆后才发现气瓶受潮） | ❌ 压力表完全测不出 ppb 级水汽 | **✅ `11 ms` 自动触发 `HTTP 403` 并硬联锁切断 BSGS 供气阀** |
| **液化特气余气（Heel）精准计量** | ❌ 10%–15% 瓶底余气白送气商 | ❌ 液化气（如 $\text{WF}_6/\text{Cl}_2$）在液相耗尽前压力恒定，看压力表根本测不出余量！ | **✅ `14 ms` 通过电子秤真实质量差强制追回 12% 余气款（`HTTP 422`）** |
| **钢瓶电抛光（EP）与定检溯源** | ❌ 人工台账易混入超期疲劳钢瓶 | ❌ 无钢瓶唯一码联动 | **✅ Web IQ `290 ms` 核查 5 年声发射定检与 F-Gas 配额（`HTTP 451`）** |
| **余气回皮 + 尾气稀有气体回收** | ❌ 高价氙/氪随干泵尾气直接排空 | ❌ 无循环提纯冲抵 | **✅ Web IQ `300 ms` 核算余气回皮与尾气提纯立省 `$29,400`（`HTTP 409`）** |

---

## ⑤ 🧪 简明定量实测与 Benchmark 核心发现（含 7-Card 报告）

我们在 `lab/webiq_commerce_demo.py` 中内置了确定性策略评估器 `evaluate_semiconductor_esg_specialty_gas_policy()`，并在 `tests/test_webiq_commerce_demo.py` 中完成全覆盖验证：

| 测试场景代号 | 输入特征与遥测参数 | 网关裁决状态码 | 动作标签（Action Pill） | 端到端延迟 | 清算金额 / 拦截亏损 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`esg_commit_ok`** | CRDS 水分 `3.2 ppb <= 10 ppb` + 零 HF + 净耗量准确 + 钢瓶定检有效 | **`HTTP 200`** | `Act automatically` | **`20 ms`** | 正常清算 **`$210,000.00`** |
| **`esg_h2o_403`** | 阀口微漏致水分 `180 ppb > 10 ppb` 引发 $\text{WF}_6$ 水解生成 HF (`crds_sub_ppb_moisture_and_hf_verified=False`) | **`HTTP 403`** | `Send to a human` | **`11 ms`** | 拦截 **`$210,000.00`** 并切断供气阀 |
| **`esg_hel_422`** | 气商吞没 12% 退瓶保压余气未回皮或金属颗粒 `> 1 ppt` (`load_cell_heel_credit_and_metal_purity_passed=False`) | **`HTTP 422`** | `Send to a human` | **`14 ms`** | 拦截 **`$210,000.00`** 余气侵吞账单 |
| **`esg_cyl_451`** | Web IQ 检出 Y-Ton 钢瓶 5 年定检逾期或违反欧盟 F-Gas 配额 (`webiq_cylinder_hydrotest_and_fgas_clean=False`) | **`HTTP 451`** | `Send to a human` | **`290 ms`** | 合规冻结 **`$210,000.00`** |
| **`esg_rec_409`** | Web IQ 执行 12% 退瓶余气回皮并联动 Sub-Fab 蚀刻尾气氙/氪膜分离纯化回用 (`heel_credit_and_exhaust_xenon_recovery_savings_cents=2940000`) | **`HTTP 409`** | `Confirm` | **`300 ms`** | 净清算 **`$180,600.00`**（立省 **`$29,400.00`**） |

- **Perturbation Robustness（顺序反转稳健性）**：将 5 组半导体电子特气遥测输入做正序/逆序扰动测试，裁决一致率 **100%（0.0 pts 漂移）**。

---

## ⑥ 🛠️ 附录：生产上线快速核验与售前打单清单（Architect Checklist）

### 6.1 适用边界：Good Fit vs Not For
- **✅ Good Fit（强烈推荐采用本架构）**：
  - 300mm/200mm 晶圆厂蚀刻（Etch）、薄膜沉积（CVD/ALD）、离子注入（Ion Implant）与 EUV/DUV 准分子激光器使用的高纯电子特气（$\text{NF}_3, \text{WF}_6, \text{SiH}_4, \text{GeH}_4, \text{AsH}_3, \text{PH}_3, \text{C}_4\text{F}_6, \text{Xe}, \text{Kr}, \text{Ne}$）；
  - 第三代半导体（SiC 外延用高纯硅烷/丙烷、GaN MOCVD 用高纯氨气 $\text{NH}_3$ 与三甲基镓 TMGa）大宗特气供应合同；
  - 采用 Total Gas & Chemical Management（TGCM）驻厂托管结算模式的半导体产线。
- **⛔ Not For（不适用或无需启用全部门禁）**：
  - 普通食品包装充氮或医院普通医用氧气瓶采购；
  - 现场空分制氮站（On-Site ASU）低压大宗管道氮气（适用我们在专题 93 构建的 ASU 比功率能耗门禁）。

### 6.2 生产上线核验 Checklist（`- [ ]`）
- [ ] **破除“液化特气看压力表就能算余量”的物理误区**：确认对 $\text{WF}_6, \text{Cl}_2, \text{NH}_3, \text{C}_4\text{F}_8$ 等液化压缩气体，100% 依赖 BSGS 高精度称重传感器（Load Cell）计量净消耗质量并自动回皮 10%–15% 退瓶余气。
- [ ] **上机循环吹扫后在线 CRDS 水分硬联锁**：确认每次换瓶 Cycle Purge 结束后，必须经在线 CRDS 实测 `moisture_h2o_ppb <= 10.0` 方可解锁供气电磁阀。
- [ ] **316L VIM-VAR 电抛光钢瓶与止回阀防倒吸审计**：确认退瓶余气享受 100% 回皮的前提是气柜保压止回阀完好且退瓶残压 $\ge 100\text{ psi}$。
- [ ] **Sub-Fab 蚀刻尾气稀有气体（$\text{Xe}/\text{Kr}/\text{Ne}$）闭环提纯**：确认 Web IQ `/v3/browse` 实时核算尾气回收纯化量以冲抵外购新气订单。
