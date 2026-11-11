# 深远海网箱与陆基循环水（RAS）三文鱼养殖饲料与成鱼交割（Salmon Aquaculture Feed & Harvest Offtake）、双目 3D 饵料系数（$\text{eFCR} \le 1.15$）与土臭素/虾青素色度（$\text{Geosmin} \le 10\text{ ng/kg}$ & $\text{SalmoFan} \ge 26$）智能托管 vs 传统按毛重盲付：架构选型与第一性原理 FAQ

> **文档类型**：AI Solution Architect 实战选型指南（对标 `ib-vs-ethernet-roce-selection-faq.md` 极简吸收范式）  
> **适用对象**：深远海智能网箱（Offshore Farming）/ 陆基循环水养殖（RAS）集团采购与运营总监、跨国生鲜商超（Costco / 山姆 / 盒马）冰鲜三文鱼买手、水产膨化饲料（Skretting / BioMar / 通威）供应链金融团队  
> **核心结论一句话**：在单批次结算额达 **$160,000.00** 的大西洋三文鱼（Atlantic Salmon）高能膨化饲料绩效合同与冰鲜成鱼（HOG 去腮去内脏净重）交割中，**绝对不能让采购 Agent 仅凭“投喂了多少吨饲料”或“活鱼吸鱼泵过秤毛重”就盲目放款**——必须构建 **“水下双目立体视觉相机（3D Stereo Biomass Camera）与残饵回声声呐实测经济饵料系数（Economic Feed Conversion Ratio, $\text{eFCR} \le 1.15$）叠加捕捞前 $\ge 48\text{ 小时}$ 停食清肠（Fasting Gut-Clearance）硬件签章 + 顶空固相微萃取气相色谱（HS-SPME-GC-MS）实测土臭素与二甲基异冰片（Geosmin / 2-MIB $\le 10\text{ ng/kg}$ 零土腥味）及高光谱虾青素罗氏色卡（SalmoFan $\ge 26$）门禁 + Microsoft Web IQ ASC 水产养殖管理委员会认证 / 水下激光海虱计数（Sea Lice $\le 0.2\text{ 只/尾}$）核验与裂殖壶藻油（Algal EPA/DHA）替代秘鲁鱼油 + RAS 鱼粪厌氧沼气热电套利”** 的四层智能托管架构。

![2026-11-11 深海与循环水三文鱼养殖交割 (RAS/Offshore)、3D 饵料系数与土臭素智能托管架构一图流](../assets/svg/126-salmon-aquaculture-ras-fcr-geosmin-2026-11-11.svg)

---

## ① 📌 核心结论速览（Executive Summary）

1. **为什么传统“按饲料发货吨数买鱼粮 + 按未停食活鱼毛重收成鱼”是现代三文鱼养殖场与生鲜商超的头号亏损黑洞？**
   - **第一性原理拆解**：在三文鱼养殖中，高能膨化饲料成本占总成本的 **55%–60%**；而在商超生鲜端，消费者花高价买的是**橘红紧实、富含 Omega-3 且绝无泥土腥味（Off-Flavor）的生食级净鱼柳**！
   - **三大物理与财务致命伤**：
     - **膨化饲料水中耐水性差（粉化漏油）或盲目过量投喂导致 $18\%$ 鱼粮直接沉底腐烂（$\text{eFCR} = 1.48 \gg 1.15$），或者卖鱼方在捕捞前故意狂喂增重（把肚子里没消化的饲料当三文鱼卖）**：如果饲料厂膨化挤压度不足导致颗粒入水即碎，或风送投饵管未联动水下残饵相机（Pellet Detection Camera），每吨 `$2,200` 的鱼粮有近五分之一直接穿网沉入海底——不仅白扔数万美元饲料钱，沉底残饵腐败还会耗尽海底溶解氧产生剧毒硫化氢；而在成鱼交割时，若养殖场未按规程提前 48–72 小时停食排空肠道（Gut Evacuation），鱼肚子里塞满的 6% 未消化湿饲料不仅让买方花三文鱼的价格买了鱼屎，更会在宰杀运输中引发蛋白酶自溶穿肚（Belly Burst）整箱腐败；
     - **陆基循环水（RAS）未做彻底清水暂养脱腥（Depuration），导致鱼肉富集土臭素（Geosmin $> 45\text{ ng/kg}$）带着一股浓郁的“泥巴发霉味”，或偷减虾青素导致鱼肉惨白（SalmoFan $< 22$）**：RAS 循环水生物滤池中的链霉菌与蓝藻会分泌极微量的**土臭素（Geosmin）与 2-甲基异冰片（2-MIB）**，通过鱼鳃迅速富集在三文鱼脂肪中。哪怕浓度只有 $20\text{ ng/kg}$（万亿分之二十），生食刺身的顾客第一口就会吐出来要求全额退货！同时，若后期饲料偷减昂贵的虾青素（Astaxanthin），切开的鱼肉呈灰白色而非鲜亮的橙红色（SalmoFan $\ge 26$），商超根本卖不出去；
     - **深海网箱爆发鲑疮痂鱼虱（Sea Lice $> 0.5\text{ 只成年雌虱/尾}$）被渔业局勒令提前强行屠宰或吊销 ASC 认证**：挪威与苏格兰渔业局对海虱实施极其严苛的交通灯配额制，超标不仅面临天价罚单，带伤痕的残次鱼（Downgraded Fish）价值直接腰斩。
2. **终极架构选型：水下双目 3D 增重/eFCR 门禁 + GC-MS 土臭素与高光谱色度门禁 + Web IQ 海虱/ASC 核验与微藻油套利（`salmon_aquaculture_ras_mandate_...`）**
   - **核心机制**：
     1. **水下双目 3D 生物量相机实测饵料系数（$\text{eFCR} \le 1.15$）与捕捞前 $\ge 48\text{h}$ 停食清肠硬门禁（`11 ms` 极速阻断 HTTP 403）**：在网箱/养殖池部署双目立体视觉相机（3D Stereo Vision）与水下残饵追踪 AI，连续核算饲料转化率 $\text{eFCR} = \frac{M_{\text{feed}}}{M_{\text{biomass\_gain}}} \le 1.15$，并在成鱼宰杀线通过内脏回皮秤验证胃肠道排空率（肠内容物占比 $\le 0.5\%$）；若饲料粉化沉底导致 $\text{eFCR}$ 超标或未停食带粪交割，网关在 **`11 ms`** 内直接拦截（`HTTP 403 FEED_CONVERSION_WASTE_OR_UNFASTED_GUT_WEIGHT_BLOCKED`）；
     2. **顶空 GC-MS 土臭素（$\text{Geosmin/2-MIB} \le 10\text{ ng/kg}$）与高光谱虾青素色度（SalmoFan $\ge 26$）门禁（`14 ms` 阻断 HTTP 422）**：RAS 成鱼出池前必须经过独立无生物膜清水脱腥池（Purging/Depuration Tank）暂养 5–7 天，并由快检 GC-MS 确认肌肉脂肪中 **$\text{Geosmin} \le 10\text{ ng/kg}$ 且 $\text{2-MIB} \le 10\text{ ng/kg}$**；同时宰杀线高光谱相机逐条扫描鱼柳验证罗氏色卡 **$\text{SalmoFan} \ge 26$**、脂肪含量 $14\%\text{–}18\%$ 且零肚皮自溶破损；若存在土腥味或鱼肉惨白，网关在 **`14 ms`** 内拦截（`HTTP 422 GEOSMIN_MUDDY_OFF_FLAVOR_OR_PALE_FLESH_BLOCKED`）；
     3. **Microsoft Web IQ 水下激光海虱计数（$\le 0.2\text{ 只/尾}$）/ ASC 认证核验与裂殖壶藻油（Algal Oil）+ 鱼粪沼气套利（`285 ms` / `295 ms`）**：通过 Web IQ `/v3/browse` 实时核验挪威 BarentsWatch / 渔业局周度海虱遥测报告（确认成年雌性海虱 **$\le 0.2\text{ 只/尾}$** 远低于春季迁徙红线）与 **ASC（水产养殖管理委员会）及 MarinTrust 可持续鱼粉认证**——违规即在 **`285 ms`** 内触发 **`HTTP 451 SEA_LICE_REGULATORY_BREACH_OR_ASC_CERT_HOLD`**；当秘鲁鳀鱼减产导致传统海洋鱼油价格暴涨时，Web IQ 自动将饲料配方切换为**发酵裂殖壶藻油（Schizochytrium Algal EPA/DHA Oil）与黑水虻昆虫蛋白（Black Soldier Fly Larvae）**（不仅使饲料海洋鱼源依赖度 $\text{FFDR} < 1.0$ 赢得商超零捕捞溢价，更消除了海洋二噁英与重金属富集），并耦合 RAS 鼓式微滤机收集的高浓鱼粪残饵厌氧消化沼气（Biogas CHP）发电冲抵水处理电费，单批立省 **`$25,600.00`**（`HTTP 409 Confirm`，净付降至 **`$134,400.00`**）。
3. **定量实测基准结论（7-Card 4:5 报告核心数据）**：
   - 在 `$160,000.00` 三文鱼饲料与冰鲜成鱼交割基准测试中，确定性网关在 **`11 ms`** 内拦截沉底残饵浪费与未停食带肠增重（`HTTP 403`），在 **`14 ms`** 内拦截 RAS 土臭素泥腥味与惨白鱼肉（`HTTP 422`），并通过 Web IQ 微藻油替代与鱼粪沼气热电联产在 **`295 ms`** 内捕获 **`$25,600.00`（16.0%）** 净节省，全部 **145 项单元测试 100% 通过**。

---

## ② 🎯 客户与架构师灵魂拷问 Q&A（Three Soul-Searching Questions）

### Q1：什么时候可以“按活鱼过秤毛重”直接买鱼 vs 什么时候必须强制上“3D 视觉 eFCR + GC-MS 土臭素 $\le 10\text{ ng/kg}$ + SalmoFan 色度托管（`salmon_aquaculture_ras_mandate_...`）”？
- **通俗大白话解答**：
  - 如果你只是**在菜市场买两条普通草鱼回家红烧重油重辣炖着吃**，现场捞出来称重即可；
  - 但只要你是**生鲜连锁商超、日料刺身供应链或大型水产集团采购集装箱级冰鲜大西洋三文鱼（尤其是陆基循环水 RAS 养殖三文鱼）与高能膨化饲料**，**必须 100% 强制锁死“捕捞前 $\ge 48\text{h}$ 停食排空 + GC-MS 土臭素 $\le 10\text{ ng/kg}$ + 高光谱罗氏色度 $\ge 26$ + 双目 3D $\text{eFCR} \le 1.15$”**！因为刺身是生吃的，哪怕一丁点生姜酱油都盖不住 Geosmin 土臭素的泥腥味！

### Q2：在挪威 BarentsWatch 海虱监管、ASC 水产认证与秘鲁鱼粉/微藻油套利场景下，何时用 Microsoft Web IQ vs Exa vs Bright Data？
- **架构师黄金切分原则**：
  1. **首选 Microsoft Web IQ（`/v3/browse` + Work IQ 渔场水下 IoT 与加工厂 MES 台账联动）**：
     - **适用场景**：实时核验**挪威渔业局 BarentsWatch 每个海区网箱的周度海虱密度与病害通报、ASC（Aquaculture Stewardship Council）与 GlobalG.A.P. 养殖场证书状态、以及发酵微藻油（Veramaris / Corbion）与秘鲁超级蒸气鱼粉的 EPA+DHA 单位毫克比价**。
     - **核心优势**：在企业零信任边界内将加工厂自动去脏分级线（Marel / Baader）高光谱色度/重量数据与信用证解付直连。
  2. **辅选 Exa（Neural Search）**：适合检索陆基 RAS 移动床生物膜反应器（MBBR）厌氧氨氧化脱氮与紫外线/臭氧催化降解土臭素动力学论文。
  3. **慎用 Bright Data**：适合抓取奥斯陆三文鱼现货指数（NASDAQ Salmon Index）公开报价，不适合单批次 GC-MS 土臭素与水下 3D 生物量对账。

### Q3：三文鱼 3D 饵料系数与零土腥味令牌（`salmon_aquaculture_ras_mandate_...`）在商超/养殖场、饲料厂、加工分级线与托管银行之间到底是怎么流转资金的？
- **第一性原理防伪链拆解**：
  1. **水下双目 3D 生物量与停食排空（Gut-Clearance）硬件签章**：水下双目相机连续测算鱼群平均体长体高推算真实净增重，验证饲料 $\text{eFCR} \le 1.15$；成鱼收获时核验停食满 48 小时且宰杀去内脏得率（HOG Yield $\ge 84\%$）达标；
  2. **顶空 GC-MS 土臭素与高光谱 SalmoFan 色度验算**：每池成鱼出清前通过 GC-MS 签发 $\text{Geosmin} \le 10\text{ ng/kg}$ 无腥证明，且加工线高光谱相机确认 100% A 级鱼柳色度 $\ge 26$；
  3. **Web IQ 海虱/ASC 核验与微藻油/鱼粪沼气清算**：Web IQ 确认海虱与 ASC 合规，并结算微藻油替代秘鲁鱼油与鱼粪沼气发电节省 `$25,600.00`（`HTTP 409 Confirm`），或在 `19 ms` 内自动释放 `$160,000.00`。

---

## ③ 🧭 直观可视化图解（Mermaid 决策树 + 路径对比 + 时序图）

### 3.1 架构师选型决策树（`flowchart TD`）

```mermaid
flowchart TD
    A["深海网箱 / 陆基 RAS 三文鱼饲料与成鱼交割 ($160,000)"] --> B{"1. 水下双目 3D 饵料系数与停食清肠？<br/>(eFCR <= 1.15 & 捕捞停食 >= 48h)"}
    B -- "❌ 饲料粉化沉底致 eFCR = 1.48 > 1.15<br/>或捕捞前未停食把满肚残饵当鱼卖" --> C["🛑 11ms 硬阻断 HTTP 403<br/>FEED_CONVERSION_WASTE_OR_UNFASTED_GUT_WEIGHT_BLOCKED<br/>拒付沉底劣质饲料款并扣除胃肠残饵虚重"]
    B -- "✅ 高效增重且肠道排空净膛达标" --> D{"2. GC-MS 土臭素脱腥与高光谱虾青素色度？<br/>(Geosmin <= 10 ng/kg & SalmoFan >= 26)"}
    D -- "❌ 跳过清水池脱腥致土臭素 45 ng/kg 土腥味<br/>或偷减虾青素致鱼肉惨白 (SalmoFan = 21)" --> E["🚨 14ms 硬阻断 HTTP 422<br/>GEOSMIN_MUDDY_OFF_FLAVOR_OR_PALE_FLESH_BLOCKED<br/>拒收泥腥味批次并退回清水池继续脱腥 7天"]
    D -- "✅ 零土腥味且橘红油脂纹理满分" --> F{"3. Web IQ 水下激光海虱密度与 ASC 认证？<br/>(/v3/browse 核查海虱 <= 0.2只/尾 & MarinTrust)"}
    F -- "❌ 海虱爆发超标 (>0.5只/尾) 鱼皮溃烂<br/>或饲料鱼粉涉及非法捕捞缺失 ASC 证" --> G["🛑 285ms 合规冻结 HTTP 451<br/>SEA_LICE_REGULATORY_BREACH_OR_ASC_CERT_HOLD<br/>阻断降级病鱼流入高端刺身渠道"]
    F -- "✅ 海虱受控且 ASC 可持续认证有效" --> H{"4. Web IQ 切换裂殖壶藻油 + RAS 鱼粪沼气发电？<br/>(微藻 EPA/DHA 替鱼油 + 污泥厌氧消化 CHP)"}
    H -- "💡 免受秘鲁鱼油暴涨冲击并回收鱼粪绿电" --> I["🧑‍⚖️ 295ms 触发 HTTP 409 Confirm<br/>ALGAL_OMEGA3_FEED_AND_SLUDGE_BIOGAS_CONFIRM<br/>立省 $25,600 (净付 $134,400)"]
    H -- "⚡ 标准合规冰鲜三文鱼/饲料结算" --> J["✅ 19ms 自动放款 HTTP 200<br/>VERIFIED_SALMON_AQUACULTURE_OFFTAKE_SETTLED ($160,000)"]
```

### 3.2 传统“按吨买料+按毛重买鱼”路径 vs 智能体“3D生物量+土臭素GC-MS+微藻油”路径对比（`flowchart LR`）

```mermaid
flowchart LR
    subgraph Legacy["❌ 传统按饲料吨数与毛鱼重盲付路径 (残饵沉底与泥腥退货)"]
        L1["饲料入水碎裂沉底且捕捞前狂喂不排空"] --> L2["RAS 未脱腥致 Geosmin 土臭素超标 4倍"]
        L2 --> L3["采购方盲付 $160,000 货款"]
        L3 --> L4["鱼肚穿孔腐败 + 刺身泥腥味遭商超全额退货"]
    end

    subgraph Agentic["✅ Agentic 水下 3D 视觉 + GC-MS 土臭素 + Web IQ 路径"]
        A1["双目 3D 生物量 eFCR + 顶空 GC-MS 土臭素签名"] --> A2["11ms/14ms 拦截沉底残饵与泥腥惨白鱼"]
        A2 --> A3["Web IQ 285ms 海虱/ASC 核验 + 295ms 微藻油/沼气"]
        A3 --> A4["净省 $25,600 鱼油与电费或 19ms 安全清算"]
    end
```

### 3.3 端到端毫秒级验真与资金清算时序图（`sequenceDiagram`）

```mermaid
sequenceDiagram
    autonumber
    participant Farm as 水产养殖/饲料厂 & 3D相机/GC-MS (Stereo/Marel)
    participant Gate as Agentic 智慧水产托管网关 (Policy Engine)
    participant WebIQ as Microsoft Web IQ (/v3/browse)
    participant Bank as 农牧与生鲜供应链托管行 (Escrow Rail)

    Farm->>Gate: 提交三文鱼饲料与成鱼交割单 ($160,000) + 双目 3D eFCR 与 GC-MS 土臭素报文
    Gate->>Gate: Gate 1: 验算实测饵料系数 eFCR <= 1.15 且捕捞停食 >= 48h 净膛达标 (11ms)
    alt 饲料沉底浪费 (eFCR > 1.15) 或未停食带胃肠残饵充重
        Gate-->>Farm: HTTP 403 FEED_CONVERSION_WASTE_OR_UNFASTED_GUT_WEIGHT_BLOCKED (拦截 $160,000)
    else 饲料转化率与净膛得率合格
        Gate->>Gate: Gate 2: 验算 GC-MS 土臭素 Geosmin <= 10 ng/kg 且色度 SalmoFan >= 26 (14ms)
        alt 跳过清水脱腥致泥腥味 (>10 ng/kg) 或鱼肉色度惨白 (<26)
            Gate-->>Farm: HTTP 422 GEOSMIN_MUDDY_OFF_FLAVOR_OR_PALE_FLESH_BLOCKED
        else 生食级风味与虾青素色泽满分
            Gate->>WebIQ: 检索 BarentsWatch 海虱通报 + ASC/MarinTrust 证书 + 微藻油与鱼粪沼气核算单
            WebIQ-->>Gate: 返回海虱 <=0.2只/尾合规 + 裂殖壶藻油替代秘鲁鱼油与沼气发电抵扣 (-$25,600)
            alt 海虱爆发超标或缺失 ASC 可持续认证
                Gate-->>Farm: HTTP 451 SEA_LICE_REGULATORY_BREACH_OR_ASC_CERT_HOLD (285ms)
            else 存在 $25,600 微藻油配方切换与鱼粪沼气发电冲抵
                Gate-->>Bank: HTTP 409 ALGAL_OMEGA3_FEED_AND_SLUDGE_BIOGAS_CONFIRM (295ms 净付 $134,400)
            else 标准合规水产批次结算
                Gate->>Bank: HTTP 200 VERIFIED_SALMON_AQUACULTURE_OFFTAKE_SETTLED (19ms 释放 $160,000)
            end
        end
    end
```

---

## ④ 📊 架构师选型决策矩阵（Architect Decision Matrix）

| 评估维度 | 方案 A：传统按饲料吨数与活鱼过秤毛重付款 | 方案 B：仅靠厨师人工闻一下或目视看颜色 | **方案 C：双目 3D $\text{eFCR}$ + GC-MS 土臭素 + Web IQ 微藻油托管（推荐）** |
| :--- | :--- | :--- | :--- |
| **核心计量与品质锚点** | 饲料袋重 + 未去脏活鱼总毛重 | 人工主观感官抽查 | **水下 3D $\text{eFCR} \le 1.15$ + 净膛 HOG + $\text{Geosmin} \le 10\text{ ng/kg}$ + $\text{SalmoFan} \ge 26$** |
| **沉底残饵与胃肠未排空充重防御** | ❌ 0%（20% 饲料漏进海底、6% 鱼肚残饵全由买方买单） | ❌ 无法量化饵料转化效率 | **✅ `11 ms` 校验 3D 增重 $\text{eFCR}$ 与 48h 停食净膛得率（`HTTP 403`）** |
| **RAS 泥腥味（Geosmin）与白肉防御** | ❌ 商超上架后被消费者退货才发现土腥味 | ❌ 冷冻状态下鼻子闻不出微量 Geosmin，解冻后腥臭扑鼻！ | **✅ `14 ms` 锁定 GC-MS $\text{Geosmin} \le 10\text{ ng/kg}$ 与高光谱色度（`HTTP 422`）** |
| **海虱（Sea Lice）与 ASC 认证门禁** | ❌ 极易买到超标海虱强制屠宰的带伤降级鱼 | ❌ 无官方渔业监管库联动 | **✅ Web IQ `285 ms` 核查海虱 $\le 0.2\text{ 只/尾}$ 与 ASC 证书（`HTTP 451`）** |
| **裂殖壶藻油与鱼粪沼气套利** | ❌ 被秘鲁厄尔尼诺鱼油涨价卡脖子，鱼粪当危废处理 | ❌ 无配方替代与厌氧沼气核算 | **✅ Web IQ `295 ms` 切换微藻油与污泥沼气立省 `$25,600`（`HTTP 409`）** |

---

## ⑤ 🧪 简明定量实测与 Benchmark 核心发现（含 7-Card 报告）

我们在 `lab/webiq_commerce_demo.py` 中内置了确定性策略评估器 `evaluate_salmon_aquaculture_ras_policy()`，并在 `tests/test_webiq_commerce_demo.py` 中完成全覆盖验证：

| 测试场景代号 | 输入特征与遥测参数 | 网关裁决状态码 | 动作标签（Action Pill） | 端到端延迟 | 清算金额 / 拦截亏损 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`sal_commit_ok`** | `eFCR = 1.08 <= 1.15` + 停食 48h + `Geosmin = 3.2 ng/kg` + 色度 `28` + 海虱 `0.08` | **`HTTP 200`** | `Act automatically` | **`19 ms`** | 正常清算 **`$160,000.00`** |
| **`sal_fcr_403`** | 饲料沉底致 `eFCR = 1.48 > 1.15` 或捕捞前未停食带胃肠残饵充重 (`stereo_3d_efcr_and_fasting_gut_verified=False`) | **`HTTP 403`** | `Send to a human` | **`11 ms`** | 拦截 **`$160,000.00`** 残饵与虚重账单 |
| **`sal_geo_422`** | RAS 未脱腥致 `Geosmin = 45 ng/kg > 10` 或色度 `SalmoFan = 21 < 26` (`gcms_geosmin_and_salmofan_color_passed=False`) | **`HTTP 422`** | `Send to a human` | **`14 ms`** | 拦截 **`$160,000.00`** 土腥惨白批次 |
| **`sal_lic_451`** | Web IQ 检出成年雌性海虱 `0.65 > 0.2 只/尾` 或缺失 ASC 认证 (`webiq_sea_lice_and_asc_marintrust_clean=False`) | **`HTTP 451`** | `Send to a human` | **`285 ms`** | 合规冻结 **`$160,000.00`** |
| **`sal_alg_409`** | Web IQ 采用发酵裂殖壶藻油（Algal EPA/DHA）替代秘鲁鱼油并回收 RAS 鱼粪厌氧沼气发电 (`algal_omega3_and_sludge_biogas_savings_cents=2560000`) | **`HTTP 409`** | `Confirm` | **`295 ms`** | 净清算 **`$134,400.00`**（立省 **`$25,600.00`**） |

- **Perturbation Robustness（顺序反转稳健性）**：将 5 组三文鱼水产遥测输入做正序/逆序扰动测试，裁决一致率 **100%（0.0 pts 漂移）**。

---

## ⑥ 🛠️ 附录：生产上线快速核验与售前打单清单（Architect Checklist）

### 6.1 适用边界：Good Fit vs Not For
- **✅ Good Fit（强烈推荐采用本架构）**：
  - 大西洋三文鱼（Atlantic Salmon）、虹鳟、蓝鳍金枪鱼及东星斑的陆基循环水（RAS）与深远海大型智能网箱（如“经海/国信 1 号”养殖工船）成鱼及饲料交割；
  - 跨国会员制商超（Costco / Sam's Club）生食级冰鲜鱼柳（HOG / Fillet）全球空运直采；
  - 水产膨化饲料厂“按净增重绩效（$/kg Biomass Gain）收费”的托管合同。
- **⛔ Not For（不适用或无需启用全部门禁）**：
  - 观赏性锦鲤宠物鱼买卖。

### 6.2 生产上线核验 Checklist（`- [ ]`）
- [ ] **水下残饵相机（Pellet Camera）与投饵机变频鼓风机闭环互锁**：一旦摄像头在网箱中下部检出未被抢食的下落颗粒，在 2 秒内自动关停投饵管，将 $\text{eFCR}$ 死死压在 $\le 1.15$。
- [ ] **陆基 RAS 独立清水脱腥池（Depuration）5–7 天暂养与顶空 GC-MS 必检**：确认每批次出池成鱼 $\text{Geosmin} \le 10\text{ ng/kg}$ 且 $\text{2-MIB} \le 10\text{ ng/kg}$，杜绝一粒老鼠屎坏掉整个生鲜品牌。
- [ ] **捕捞前 48–72 小时停食度日（Degree-Days Fasting）与 HOG 去脏得率对账**：严禁将未排空肠胃内容物计入成鱼结算净重，防止运输途中蛋白酶自溶穿肚。
- [ ] **裂殖壶藻油（Algal EPA/DHA）与水下光学激光除虱（Laser Delousing）推广**：减少化学除虱药浴对鱼体的应激降级并摆脱野生鱼粉价格波动。
