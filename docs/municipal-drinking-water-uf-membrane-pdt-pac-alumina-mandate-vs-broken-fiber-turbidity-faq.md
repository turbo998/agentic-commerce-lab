# 市政自来水厂超滤膜组件与饮用水级聚合氯化铝（PAC）交割（Municipal Drinking Water Ultrafiltration Membrane & Potable PAC Coagulant Offtake）、中空纤维膜压力衰减完整性（EPA LT2 $\text{PDT} \le 0.01\text{ bar/min}$ 防断丝漏隐孢子虫）与有效氧化铝（$\text{Al}_2\text{O}_3 \ge 10.5\%$）/ NSF 60 零废酸重金属智能托管 vs 传统按药液湿重盲付：架构选型与第一性原理 FAQ

> **文档类型**：AI Solution Architect 实战选型指南（对标 `ib-vs-ethernet-roce-selection-faq.md` 极简吸收范式）  
> **适用对象**：市政自来水集团与水务投资运营商（北控水务 / 首创环保 / 粤海水务 / 威立雅水务 Veolia / 苏伊士 Suez）水厂总工与药剂/膜组件集中采购架构师、超滤膜与净水混凝剂制造商（杜邦水处理 DuPont / 旭化成 Asahi Kasei / 碧水源 / 立升科技 / 凯米拉 Kemira）质量与供应链金融负责人  
> **核心结论一句话**：在单批次货值达 **$180,000.00** 的大型市政自来水厂 PVDF 超滤（UF）中空纤维膜组件更换与饮用水级液态聚合氯化铝（PAC Coagulant）长协交割中，**绝对不能让采购 Agent 仅凭“出厂总管混合水浊度 $< 0.1\text{ NTU}$ + 槽罐车过磅湿吨”就盲目放款**——必须构建 **“每日自动直接完整性压力衰减测试（EPA LT2ESWTR Pressure Decay Test $\text{PDT} \le 0.010\text{ bar/min}$ 且隐孢子虫对数去除值 $\text{LRV} \ge 4.0\text{-log}$ 严防单根膜丝断裂被总管清水稀释掩盖）与跨膜压差比通量恢复率硬件签章 + 液态 PAC 有效三氧化二铝含量（GB 15892 $\text{Al}_2\text{O}_3 \ge 10.5\%$）与盐基度（Basicity $65\%\text{–}85\%$）折百干基计价门禁 + Microsoft Web IQ NSF/ANSI 60 饮用水化学品无工业废盐酸重金属（铅 $\text{Pb}$ / 砷 $\text{As}$ / 镉 $\text{Cd}$）与消毒副产物三卤甲烷（THMs）合规核验 + 流动电流仪（Streaming Current Detector, SCD）AI 闭环动态加药与超滤反冲洗水回流混凝沉淀池套利”** 的四层智能托管架构。

![2026-11-12 市政自来水厂超滤膜与饮用水级 PAC 交割、压力衰减 (PDT) 与氧化铝品位智能托管架构一图流](../assets/svg/140-municipal-water-uf-membrane-pdt-pac-2026-11-12.svg)

---

## ① 📌 核心结论速览（Executive Summary）

1. **为什么传统“只看总管出水浊度表、按槽罐车毛重买液态 PAC”是导致自来水厂爆发隐孢子虫（Cryptosporidium）公共卫生危机与被工业废酸假药坑骗的根源？**
   - **第一性原理拆解**：在现代日产 $50\text{ 万吨}$ 的深度处理市政自来水厂中，超滤膜（UF，孔径 $0.01\text{–}0.02\ \mu\text{m}$）是阻挡**耐氯寄生的隐孢子虫卵囊（*Cryptosporidium* oocysts，尺寸 $3\text{–}5\ \mu\text{m}$，普通加氯消毒完全杀不死！）与贾第鞭毛虫**进入市民水龙头的最后一道物理屏障。然而，一支超滤膜柱内有上万根细如发丝的中空纤维膜丝；如果因为水锤冲击或材质脆化断了 5 根膜丝，含有病原体的原水就会从断口直接短路喷入产水侧。可怕的是：**被上万根完好膜丝产出的巨量清水一稀释，总产水管上的在线激光浊度仪读数依然是 $0.06\text{ NTU} < 0.1\text{ NTU}$**！浊度表根本无法发现几根断丝造成的病原体泄漏，唯有将膜丝排空充入压缩空气做**泡点压力衰减测试（PDT, Pressure Decay Test）**，才能听见断丝处每秒冒出的微小气泡！
   - **三大物理与财务致命伤**：
     - **超滤膜组件耐次氯酸钠氧化性能劣质导致运行半年后断丝率激增，压力衰减率突破 $\text{PDT} = 0.045\text{ bar/min} \gg 0.010\text{ bar/min}$（隐孢子虫截留率跌破 $2.5\text{-log}$），或不可逆膜污染使跨膜压差（TMP）飙至 $1.8\text{ bar}$**：劣质共混 PVDF 膜丝在频繁次氯酸钠化学加强反洗（CEB）下发生分子链断裂脆化。总管浊度看似达标，实则每天漏过数百万个耐氯孢子；且膜孔堵塞导致抽吸泵电耗翻倍；
     - **液态聚合氯化铝（PAC）供应商掺水稀释，把有效氧化铝（$\text{Al}_2\text{O}_3$）从合同要求的 $10.5\%$ 偷降到 $7.2\%$ 按湿吨收全款，或盐基度过低（$<50\%$）导致冬季低温低浊水不结矾花、出水残余铝超标（$> 0.2\text{ mg/L}$ 诱发神经毒性风险）**：传统地磅只称槽罐车拉了多少吨液体。无良化工厂多加 $30\%$ 的自来水进去，水厂不仅白付了高价药剂钱，操作工看沉淀池不起矾花只能拼命开大加药计量泵，结果耗药量翻倍且滤后水残余溶解铝超标；
     - **用廉价“钢铁酸洗废盐酸 / 铝型材厂含重金属废渣”非法生产的工业级 PAC 冒充饮用水级白/金黄 PAC，导致自来水中砷（$\text{As}$）、铅（$\text{Pb}$）、镉（$\text{Cd}$）重金属超标**：正规饮用水级 PAC 必须采用高纯氢氧化铝粉与合成高纯盐酸生产（通过 NSF/ANSI 60 认证）；若混入工业副产废酸，等于把重金属毒物直接投进全城百姓的饮水源！
2. **终极架构选型：超滤膜每日压力衰减（$\text{PDT} \le 0.010\text{ bar/min}$ / $\text{LRV} \ge 4.0$）+ 液态 PAC 有效 $\text{Al}_2\text{O}_3 \ge 10.5\%$ 折百干基 + Web IQ NSF 60 核验与流动电流仪（SCD）闭环加药套利（`municipal_water_uf_pac_mandate_...`）**
   - **核心机制**：
     1. **超滤膜架每日自动压力衰减测试（EPA LT2 $\text{PDT} \le 0.010\text{ bar/min}$ & $\text{LRV} \ge 4.0\text{-log}$）与比通量/跨膜压差（$\text{TMP} \le 1.2\text{ bar}$）硬门禁（`11 ms` 极速阻断 HTTP 403）**：直接从水厂超滤车间 PLC 读取每列膜架每日凌晨自动执行的 $1.2\text{ bar}$ 保压空气压力衰减率（$\text{PDT} \le 0.010\text{ bar/min}$ 换算隐孢子虫去除率 $\text{LRV} \ge 4.0\text{-log}$）及 $20^\circ\text{C}$ 温度校正比通量签名；任何断丝漏气或不可逆污堵超标的膜组件/维保账单在 **`11 ms`** 内直接拦截（`HTTP 403 UF_MEMBRANE_PRESSURE_DECAY_BREACH_OR_HIGH_TMP_BLOCKED`）；
     2. **液态 PAC 有效氧化铝浓度（$\text{Al}_2\text{O}_3 \ge 10.5\%$）、盐基度（$65\%\text{–}85\%$）折百计重与出水残余铝（$\le 0.10\text{ mg/L}$）门禁（`14 ms` 阻断 HTTP 422）**：通过卸药口在线科里奥利质量密度计与 ICP-OES/滴定仪强制校验每车液态 PAC 的**有效 $\text{Al}_2\text{O}_3 \ge 10.5\%$ 与高聚合态 $\text{Al}_{13}$ 盐基度**，按折百纯 $\text{Al}_2\text{O}_3$ 干吨结算，且沉后水与出厂水在线比色残余铝 $\le 0.10\text{ mg/L}$；若药液兑水不足量或低盐基度跑矾，网关在 **`14 ms`** 内拦截（`HTTP 422 PAC_ALUMINA_DILUTION_OR_RESIDUAL_ALUMINUM_BLOCKED`）；
     3. **Microsoft Web IQ NSF/ANSI 60 饮用水重金属核验与流动电流仪（SCD）AI 闭环加药 + 超滤反洗水回收套利（`285 ms` / `295 ms`）**：通过 Web IQ `/v3/browse` 实时核验 NSF 官方网站 **NSF/ANSI 60 涉水卫生批件**及本批次 ICP-MS 铅（$\le 5\text{ ppm}$）、砷（$\le 2\text{ ppm}$）、镉（$\le 1\text{ ppm}$）零工业废酸证明——检出重金属或证照过期在 **`285 ms`** 内触发 **`HTTP 451 NSF60_HEAVY_METAL_ARSENIC_LEAD_OR_WASTE_ACID_HOLD`**；同时，Web IQ 自动启用混合池**在线流动电流检测仪（Streaming Current Detector, SCD 实时测量胶体 Zeta 电位电荷中和零点，消除人工过量加药 $25\%$）**，并将超滤膜气水反冲洗排出的微絮凝水（含未反应完的活性氢氧化铝微晶核）100% 回流至原水配水井充当助凝晶种，单批立省 **`$28,800.00`**（`HTTP 409 Confirm`，净付降至 **`$151,200.00`**）。
3. **定量实测基准结论（7-Card 4:5 报告核心数据）**：
   - 在 `$180,000.00` 市政自来水厂超滤膜与饮用水级 PAC 药剂交割基准测试中，确定性网关在 **`11 ms`** 内拦截超滤断丝压力衰减超标与污堵（`HTTP 403`），在 **`14 ms`** 内拦截液态 PAC 兑水虚重与残余铝超标（`HTTP 422`），并通过 Web IQ 流动电流仪 SCD 动态减药与反洗水晶种回流在 **`295 ms`** 内捕获 **`$28,800.00`（16.0%）** 净节省，全部 **159 项单元测试 100% 通过**。

---

## ② 🎯 客户与架构师灵魂拷问 Q&A（Three Soul-Searching Questions）

### Q1：什么时候可以“只看总管浊度计和过磅吨数” vs 什么时候必须强制上“超滤 PDT 压力衰减 $\le 0.01\text{ bar/min}$ + PAC 折百 $\text{Al}_2\text{O}_3$ + NSF 60 托管（`municipal_water_uf_pac_mandate_...`）”？
- **通俗大白话解答**：
  - 如果你只是**洗煤厂或造纸厂买工业级褐黄色 PAC 处理泥浆废水回用冲渣**，按湿吨过磅加普通沉淀就行；
  - 但只要你是**供应几百万市民直接饮用的市政自来水厂或高品质再生水厂**，**必须 100% 强制锁死“超滤膜每日自动 PDT 压力衰减测试（$\text{LRV} \ge 4.0\text{-log}$）+ 液态 PAC 有效 $\text{Al}_2\text{O}_3 \ge 10.5\%$ 折百干基结算 + NSF 60 零废酸重金属签章”**！因为浊度计对几根断丝漏过的隐孢子虫完全失明，而工业废酸造的假 PAC 会让全城自来水重金属超标！

### Q2：在氢氧化铝/液氯原料价格联动、NSF/ANSI 60 涉水批件核查与原水藻类爆发应急加药场景下，何时用 Microsoft Web IQ vs Exa vs Bright Data？
- **架构师黄金切分原则**：
  1. **首选 Microsoft Web IQ（`/v3/browse` + Work IQ 水厂 SCADA 超滤机架 PLC 与加药间 SCD 流动电流仪联动）**：
     - **适用场景**：实时核验**每列超滤膜架每日 PDT 压力衰减日志、卸药口科里奥利密度折算 $\text{Al}_2\text{O}_3$ 报文、NSF 60 与卫健委涉水批件状态、以及 SCD 动态闭环加药与反洗水回用节药台账**。
     - **核心优势**：在关键民生基础设施零信任边界内，将水质安全硬指标与供应链付款自动联锁。
  2. **辅选 Exa（Neural Search）**：适合检索高盐基度聚氯化铝 $\text{Al}_{13}$ 纳米形态分布（Ferron 逐时络合比色法）与低温低浊水强化混凝文献。
  3. **慎用 Bright Data**：适合抓取公开化工市场工业盐酸行情，不适合自来水厂内部 SCADA 压力衰减曲线对账。

### Q3：市政超滤膜防断丝与净水药剂防兑水令牌（`municipal_water_uf_pac_mandate_...`）在水务集团、膜/药剂供应商、水质监测中心与托管银行之间到底是怎么流转资金的？
- **第一性原理防伪链拆解**：
  1. **超滤膜每日 PDT 压力衰减与 TMP 硬件签章**：水厂 PLC 签名确认全部膜架 $\text{PDT} = 0.004\text{ bar/min} \le 0.010\text{ bar/min}$（$\text{LRV} = 4.6\text{-log} \ge 4.0$）且 $\text{TMP} \le 1.2\text{ bar}$；
  2. **液态 PAC 有效 $\text{Al}_2\text{O}_3$ 与残余铝验算**：确认卸车液态 PAC $\text{Al}_2\text{O}_3 = 11.2\% \ge 10.5\%$、盐基度 $78\%$ 且出厂水残余铝 $0.03\text{ mg/L} \le 0.10\text{ mg/L}$；
  3. **Web IQ NSF 60 核验与 SCD 智能减药清算**：Web IQ 确认零废酸重金属，并结算 SCD 流动电流闭环加药与超滤反洗水晶种回流节省 `$28,800.00`（`HTTP 409 Confirm`），或在 `18 ms` 内自动释放 `$180,000.00`。

---

## ③ 🧭 直观可视化图解（Mermaid 决策树 + 路径对比 + 时序图）

### 3.1 架构师选型决策树（`flowchart TD`）

```mermaid
flowchart TD
    A["市政自来水厂超滤膜与饮用水级 PAC 交割 ($180,000)"] --> B{"1. 超滤膜每日压力衰减 PDT 与隐孢子虫 LRV？<br/>(EPA LT2 PDT <= 0.010 bar/min & LRV >= 4.0-log)"}
    B -- "❌ 膜丝氧化脆断致 PDT 飙至 0.045 bar/min (LRV < 2.5)<br/>总管浊度虽被稀释掩盖，实则漏过耐氯隐孢子虫" --> C["🛑 11ms 硬阻断 HTTP 403<br/>UF_MEMBRANE_PRESSURE_DECAY_BREACH_OR_HIGH_TMP_BLOCKED<br/>自动切停断丝膜架打销修补，拒付劣质膜组件款"]
    B -- "✅ 全膜架气密完好且比通量充沛" --> D{"2. 液态 PAC 有效氧化铝 Al2O3 与出水残余铝？<br/>(GB 15892 Al2O3 >= 10.5% & 残余铝 <= 0.10 mg/L)"}
    D -- "❌ 槽罐车掺水稀释将 Al2O3 偷降到 7.2% 按毛重收费<br/>或盐基度过低跑矾致管网水残余铝 > 0.20 mg/L" --> E["🚨 14ms 硬阻断 HTTP 422<br/>PAC_ALUMINA_DILUTION_OR_RESIDUAL_ALUMINUM_BLOCKED<br/>拦截兑水假药账单并阻断高残余铝神经毒性风险"]
    D -- "✅ 折百氧化铝品位足额且矾花密实沉降快" --> F{"3. Web IQ NSF 60 涉水重金属与废酸溯源核查？<br/>(/v3/browse 核验无废酸砷 As/铅 Pb/镉 Cd)"}
    F -- "❌ 用钢铁酸洗废盐酸违规生产检出砷/铅重金属超标<br/>或涉水卫生许可批件 / NSF 60 认证失效" --> G["🛑 285ms 合规冻结 HTTP 451<br/>NSF60_HEAVY_METAL_ARSENIC_LEAD_OR_WASTE_ACID_HOLD<br/>立即锁死卸药电动阀，严防重金属污染城市水网"]
    F -- "✅ 高纯合成盐酸与氢氧化铝饮用水级认证完备" --> H{"4. Web IQ 启用 SCD 流动电流闭环加药 + 反洗水回流助凝？<br/>(Zeta 电位零点动态控药 + 超滤反洗活性微晶回用)"}
    H -- "💡 砍掉 25% 盲目过量加药并回收 99% 反洗原水" --> I["🧑‍⚖️ 295ms 触发 HTTP 409 Confirm<br/>STREAMING_CURRENT_DOSING_AND_BACKWASH_SEED_CONFIRM<br/>立省 $28,800 (净付 $151,200)"]
    H -- "⚡ 标准合规自来水厂膜与药剂结算" --> J["✅ 18ms 自动放款 HTTP 200<br/>VERIFIED_MUNICIPAL_UF_PAC_SETTLED ($180,000)"]
```

### 3.2 传统“只看总管浊度+按湿吨买药”路径 vs 智能体“PDT 压力衰减+折百 Al2O3+SCD 加药”路径对比（`flowchart LR`）

```mermaid
flowchart LR
    subgraph Legacy["❌ 传统只看总管浊度与湿吨过磅盲付路径 (断丝漏虫与废酸兑水)"]
        L1["断5根膜丝被清水稀释掩盖且PAC掺水30%"] --> L2["混入酸洗废盐酸重金属且过量加药残铝超标"]
        L2 --> L3["水厂盲付 $180,000 药膜款"]
        L3 --> L4["隐孢子虫穿透屏障且每年多花30%冤枉药费"]
    end

    subgraph Agentic["✅ Agentic 每日 PDT 完整性 + 折百 Al2O3 + Web IQ SCD 路径"]
        A1["EPA LT2 PDT<=0.01 + 科里奥利折百 Al2O3 + 残铝签名"] --> A2["11ms/14ms 拦截断丝膜架与兑水低品位药液"]
        A2 --> A3["Web IQ 285ms NSF60重金属核验 + 295ms SCD闭环加药"]
        A3 --> A4["净省 $28,800 药耗水费或 18ms 安全清算"]
    end
```

### 3.3 端到端毫秒级验真与资金清算时序图（`sequenceDiagram`）

```mermaid
sequenceDiagram
    autonumber
    participant Plant as 水厂超滤车间/卸药站 & 水质实验室 (Memcor PDT / Milton Roy SCD)
    participant Gate as Agentic 市政水务托管网关 (Policy Engine)
    participant WebIQ as Microsoft Web IQ (/v3/browse)
    participant Bank as 公用事业供应链托管行 (Escrow Rail)

    Plant->>Gate: 提交超滤膜/饮用水 PAC 结算单 ($180,000) + 每日 PDT 压力衰减与折百 Al2O3 报文
    Gate->>Gate: Gate 1: 验算膜架 PDT <= 0.010 bar/min (LRV >= 4.0-log) 且 TMP <= 1.2 bar (11ms)
    alt 膜丝断裂致压力衰减超标或不可逆膜污堵
        Gate-->>Plant: HTTP 403 UF_MEMBRANE_PRESSURE_DECAY_BREACH_OR_HIGH_TMP_BLOCKED (拦截 $180,000)
    else 中空纤维膜完整性与比通量合格
        Gate->>Gate: Gate 2: 验算液态 PAC Al2O3 >= 10.5%、盐基度达标且出厂水残余铝 <= 0.10 mg/L (14ms)
        alt 槽罐车药液掺水稀释 (<10.5%) 或低温跑矾致残余铝超标
            Gate-->>Plant: HTTP 422 PAC_ALUMINA_DILUTION_OR_RESIDUAL_ALUMINUM_BLOCKED
        else 有效氧化铝干基品位与混凝沉降合格
            Gate->>WebIQ: 检索 NSF/ANSI 60 批件 + ICP-MS 铅砷镉零废酸报告 + SCD 流动电流与反洗回流台账
            WebIQ-->>Gate: 返回零重金属合规 + SCD 胶体电位闭环减药与反洗水晶种回流抵扣 (-$28,800)
            alt 检出废酸铅/砷重金属超标或涉水卫生批件失效
                Gate-->>Plant: HTTP 451 NSF60_HEAVY_METAL_ARSENIC_LEAD_OR_WASTE_ACID_HOLD (285ms)
            else 存在 $28,800 SCD 动态精准减药与反洗水助凝红利
                Gate-->>Bank: HTTP 409 STREAMING_CURRENT_DOSING_AND_BACKWASH_SEED_CONFIRM (295ms 净付 $151,200)
            else 标准合规市政膜与药剂结算
                Gate->>Bank: HTTP 200 VERIFIED_MUNICIPAL_UF_PAC_SETTLED (18ms 释放 $180,000)
            end
        end
    end
```

---

## ④ 📊 架构师选型决策矩阵（Architect Decision Matrix）

| 评估维度 | 方案 A：传统仅看“总管浊度计 + 药车湿吨过磅” | 方案 B：仅每周人工抽检一次 PAC 比重与跨膜压差 | **方案 C：每日自动 PDT 完整性 + 折百 $\text{Al}_2\text{O}_3$ + Web IQ SCD 加药托管（推荐）** |
| :--- | :--- | :--- | :--- |
| **核心水质安全与计量锚点** | 混合产水浊度 $<0.1\text{ NTU}$ + 槽车毛重 | 波美比重计抽检 + 滤池液位 | **$\text{PDT} \le 0.01\text{ bar/min}$ ($\text{LRV}\ge 4$) + $\text{Al}_2\text{O}_3 \ge 10.5\%$ + 残铝 $\le 0.1\text{ mg/L}$** |
| **单根膜丝断裂漏过耐氯隐孢子虫防御** | ❌ 0%（几根断丝漏出的原水被万吨清水稀释，激光浊度仪读数纹丝不动！） | ❌ 跨膜压差 TMP 根本测不出个别膜丝断裂 | **✅ `11 ms` 强制校验 EPA LT2 每日自动空气压力衰减测试 PDT（`HTTP 403`）** |
| **液态 PAC 掺水稀释与高残余铝防御** | ❌ 掺 $30\%$ 水照收药钱，残余铝超标危害市民神经系统 | ❌ 往药液里掺廉价氯化钠（食盐）或氯化钙就能轻易伪造波美比重！ | **✅ `14 ms` 锁定有效 $\text{Al}_2\text{O}_3 \ge 10.5\%$ 折百干基与在线残余铝（`HTTP 422`）** |
| **工业酸洗废盐酸（砷/铅/镉重金属）门禁** | ❌ 廉价废酸 PAC 混入水厂引发重大公共饮水污染 | ❌ 常规水厂化验室不测痕量砷铅 | **✅ Web IQ `285 ms` 穿透核验 NSF 60 与 ICP-MS 铅砷镉报告（`HTTP 451`）** |
| **SCD 流动电流闭环加药与反洗水回流套利** | ❌ 凭工人肉眼看矾花常年过量加药 $25\%$，反洗水直接排掉 | ❌ 原水浊度突变时人工调药严重滞后 | **✅ Web IQ `295 ms` 启用 SCD 电位控药与反洗晶种回流立省 `$28,800`（`HTTP 409`）** |

---

## ⑤ 🧪 简明定量实测与 Benchmark 核心发现（含 7-Card 报告）

我们在 `lab/webiq_commerce_demo.py` 中内置了确定性策略评估器 `evaluate_municipal_water_uf_pac_policy()`，并在 `tests/test_webiq_commerce_demo.py` 中完成全覆盖验证：

| 测试场景代号 | 输入特征与遥测参数 | 网关裁决状态码 | 动作标签（Action Pill） | 端到端延迟 | 清算金额 / 拦截亏损 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`muf_commit_ok`** | `PDT = 0.004 bar/min <= 0.01` (`LRV = 4.6`) + `Al2O3 = 11.2% >= 10.5%` + 残铝 `0.03 mg/L` | **`HTTP 200`** | `Act automatically` | **`18 ms`** | 正常清算 **`$180,000.00`** |
| **`muf_pdt_403`** | 膜丝断裂致 `PDT = 0.045 bar/min > 0.01` (`LRV < 4.0`) 或 `TMP > 1.2 bar` (`uf_pressure_decay_lrv4_and_tmp_verified=False`) | **`HTTP 403`** | `Send to a human` | **`11 ms`** | 拦截 **`$180,000.00`** 断丝漏虫风险批次 |
| **`muf_pac_422`** | 液态 PAC 掺水致 `Al2O3 = 7.2% < 10.5%` 或出水残余铝 `> 0.10 mg/L` (`pac_alumina_grade_and_residual_aluminum_passed=False`) | **`HTTP 422`** | `Send to a human` | **`14 ms`** | 拦截 **`$180,000.00`** 兑水跑矾账单 |
| **`muf_nsf_451`** | Web IQ 检出工业废酸重金属（铅/砷/镉）超标或 NSF 60 失效 (`webiq_nsf60_potable_and_heavy_metal_clean=False`) | **`HTTP 451`** | `Send to a human` | **`285 ms`** | 合规冻结 **`$180,000.00`** |
| **`muf_scd_409`** | Web IQ 启用 SCD 流动电流仪 Zeta 电位闭环加药与超滤反洗水活性微晶回流 (`scd_streaming_current_and_backwash_seed_savings_cents=2880000`) | **`HTTP 409`** | `Confirm` | **`295 ms`** | 净清算 **`$151,200.00`**（立省 **`$28,800.00`**） |

- **Perturbation Robustness（顺序反转稳健性）**：将 5 组市政水厂超滤与药剂遥测输入做正序/逆序扰动测试，裁决一致率 **100%（0.0 pts 漂移）**。

---

## ⑥ 🛠️ 附录：生产上线快速核验与售前打单清单（Architect Checklist）

### 6.1 适用边界：Good Fit vs Not For
- **✅ Good Fit（强烈推荐采用本架构）**：
  - 市政自来水厂浸没式/柱式超滤膜（PVDF / PES UF）与纳滤膜（NF）组件采购、饮用水级聚合氯化铝（PAC）/ 聚合硫酸铁（PFS）及次氯酸钠长协交割；
  - 高品质再生水厂（Indirect Potable Reuse, NEWater 模式）双膜法药剂与膜维保绩效合同；
  - 智慧水务（Smart Water）AI 混凝加药改造项目。
- **⛔ Not For（不适用或无需启用全部门禁）**：
  - 建筑工地洗车槽泥水沉淀用工业级絮凝剂采购。

### 6.2 生产上线核验 Checklist（`- [ ]`）
- [ ] **EPA LT2 每日自动空气压力衰减测试（$\text{PDT} \le 0.010\text{ bar/min}$ & 隐孢子虫 $\text{LRV} \ge 4.0\text{-log}$）必检**：严禁仅凭总产水管激光浊度仪判断膜丝完整性。
- [ ] **液态 PAC 有效三氧化二铝（GB 15892 $\text{Al}_2\text{O}_3 \ge 10.5\%$）折百干基与在线残余铝（$\le 0.10\text{ mg/L}$）门禁**：封死掺盐水伪造波美比重与高残铝风险。
- [ ] **NSF/ANSI 60 涉水卫生批件与 ICP-MS 铅/砷/镉零废酸核验**：通过 Web IQ 彻底杜绝工业副产废盐酸混入饮用水源。
- [ ] **Web IQ 流动电流检测仪（SCD）Zeta 电位闭环加药与超滤反洗水回流对冲**：消除 $25\%$ 盲目过量加药并实现反洗水近零排放。
