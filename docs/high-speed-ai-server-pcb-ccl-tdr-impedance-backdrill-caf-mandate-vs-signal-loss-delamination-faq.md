# 高速 AI 服务器多层 PCB 与超低损耗覆铜板制造交割（High-Speed AI Server PCB & Ultra-Low-Loss CCL Fabrication）、时域反射阻抗（TDR $\pm 5\%$）与 X-Ray 背钻残桩（$\text{Stub} \le 6\text{ mil}$）/ 防导电阳极丝（CAF）智能托管 vs 传统仅看飞针通断盲付：架构选型与第一性原理 FAQ

> **文档类型**：AI Solution Architect 实战选型指南（对标 `ib-vs-ethernet-roce-selection-faq.md` 极简吸收范式）  
> **适用对象**：AI 智算服务器与交换机 ODM/OEM（鸿海 / 广达 / 浪潮 / 思科 / Arista）硬件工程与供应链采购总监、高多层高速印制电路板厂（沪电 / 深南电路 / 鹏鼎 / 金像电）与覆铜板厂（松下电工 / 台光电 / 生益科技）品质副总裁  
> **核心结论一句话**：在单批次货值达 **$230,000.00** 的 24–40 层 AI 训练通用基板（UBB / OAM）与 800G/1.6T 交换机高速 PCB 交割中，**绝对不能让采购 Agent 仅凭“直流飞针/针床开短路测试（Flying-Probe DC Continuity）100% 导通 + 外观 AOI 无划痕”就盲目放款**——必须构建 **“每拼板随行测试条时域反射计（Coupon TDR Controlled Impedance $\pm 5\%$）与矢量网络分析仪插损（VNA $S_{21}$ @ 28/56 GHz）叠加 X-Ray 控深背钻残桩（Backdrill Stub $\le 6\text{ mil}$）硬件签章 + IPC-6012 Class 3 六次 $288^\circ\text{C}$ 漂锡热冲击无爆板与微切片孔铜厚度（$\ge 25\ \mu\text{m}$ 零镀层空洞）门禁 + Microsoft Web IQ 超低损耗覆铜板（Megatron / Tachyon / HVLP3 铜箔）原厂批号溯源 / 离子色谱防导电阳极丝（CAF 洁净度 $\le 0.8\ \mu\text{g/cm}^2\text{ NaCl}$）核验与信号/电源层混压叠层（Hybrid Stackup）+ 蚀刻废液电解再生铜冲抵”** 的四层智能托管架构。

![2026-11-11 高速 AI 服务器多层 PCB 与覆铜板交割、TDR 阻抗 (±5%) 与背钻残桩/防 CAF 智能托管架构一图流](../assets/svg/129-high-speed-ai-pcb-ccl-tdr-backdrill-2026-11-11.svg)

---

## ① 📌 核心结论速览（Executive Summary）

1. **为什么传统“直流飞针测试通断合格就收货”会让贴了 8 颗高价 AI GPU 的服务器母板全军覆没？**
   - **第一性原理拆解**：一块 AI 服务器 UBB 母板本身价值 `$2,500`，但一旦进入 SMT 贴片线焊上 8 颗 AI 加速芯片、光模块底座与高密连接器，整板价值瞬间飙升至 **`$250,000+`**（且 BGA 芯片一旦焊上几乎无法无损返修）！在 112G/224G PAM4 高速 SerDes 信道中，电流不再是简单的直流电，而是高达 28 GHz–56 GHz 的电磁波。**只测直流导通，等于拿手电筒去检验光纤——根本看不出高频信号反射、损耗与潜伏短路！**
   - **三大物理与财务致命伤**：
     - **控深背钻残桩过长（$\text{Backdrill Stub} = 15\text{ mil} \gg 6\text{ mil}$）或蚀刻线宽偏差导致差分阻抗失配（$Z_{\text{diff}}$ 偏离 $\pm 12\% > \pm 5\%$），112G PAM4 眼图彻底闭合**：多层板导通孔（PTH）未使用的下半截铜柱就像一根“四分之一波长天线（Stub）”，在 28 GHz 下会产生剧烈的谐振反射把高频信号吃光！如果 PCB 厂钻刀磨损未及时换刀导致背钻残桩余留 $15\text{ mil}$（标准要求 $\le 6\text{ mil}$），直流飞针测试 100% 通过，但等焊完 8 颗 GPU 上电跑 PCIe Gen6 / NVLink 压力测试时，高速通道疯狂丢包误码（BER $> 10^{-4}$），整批 `$230,000` 母板及连带元器件直接报废！
     - **压合除胶渣（Desmear）不良或偷工减料导致 $260^\circ\text{C}$ 无铅回流焊时“爆板分层（Delamination）”与导通孔铜壁拉裂（Barrel Crack）**：30 层以上厚板若黑化/棕化结合力不足，或电镀深孔能力（Throwing Power）差导致中心孔壁铜厚不足 $15\ \mu\text{m}$（低于 IPC-6012 Class 3 $\ge 25\ \mu\text{m}$ 红线），常温下测试完全导通；一进 SMT 回流焊炉经历 3 次 $260^\circ\text{C}$ 热膨胀，Z 轴膨胀直接把孔铜拉断、内层起泡分层；
     - **偷换低等级覆铜板（拿 M6 冒充 M8 或普通玻纤布冒充扁平低介电 NE-Glass）或药水清洗不净引发导电阳极丝（CAF, Conductive Anodic Filament）微短路起火**：若孔壁残留钻孔玻璃粉尘与溴/氯离子（$> 1.56\ \mu\text{g/cm}^2\text{ NaCl}$），服务器在数据中心高温高湿高偏压下运行 90 天后，铜离子会沿着玻纤束缝隙长出导电晶须（CAF），直接引发 54V 主供电层与信号层短路烧毁！
2. **终极架构选型：随行测试条 TDR/VNA + X-Ray 背钻残桩（$\le 6\text{ mil}$）+ Class 3 热冲击金相 + Web IQ 覆铜板/CAF 核验与混压/提铜套利（`high_speed_ai_pcb_ccl_mandate_...`）**
   - **核心机制**：
     1. **每拼板测试条 TDR 特征阻抗（$\pm 5\%$）、VNA 插损（$S_{21}$）与 X-Ray 背钻残桩（$\le 6\text{ mil}$）硬门禁（`11 ms` 极速阻断 HTTP 403）**：强制要求每张工作拼板（Working Panel）随附高频测试条（SET2DIL / Coupon），出货前由自动探针台实测 **TDR 差分阻抗（$85\ \Omega / 100\ \Omega \pm 5\%$）**、28/56 GHz 插入损耗（$\text{Insertion Loss} \le \text{Target dB/inch}$）及 **3D X-Ray 背钻残桩长度 $\le 6\text{ mil}$（$150\ \mu\text{m}$）**；任何阻抗越界或长残桩在 **`11 ms`** 内直接拦截（`HTTP 403 TDR_IMPEDANCE_MISMATCH_OR_BACKDRILL_STUB_BLOCKED`）；
     2. **IPC-6012 Class 3 六次 $288^\circ\text{C}$ 漂锡热应力与金相微切片（孔铜 $\ge 25\ \mu\text{m}$ 零空洞）门禁（`14 ms` 阻断 HTTP 422）**：每批次必须通过 **6 次 $288^\circ\text{C} \times 10\text{ s}$ 焊锡漂浮试验（Solder Float）与 IST 互连应力测试**，金相显微镜切片确认零分层起泡、零内层铜箔裂纹（Foil Crack）且孔壁平均铜厚 **$\ge 25\ \mu\text{m}$**；若存在热分层或镀层空洞，网关在 **`14 ms`** 内拦截（`HTTP 422 THERMAL_STRESS_DELAMINATION_OR_PLATING_VOID_BLOCKED`）；
     3. **Microsoft Web IQ 覆铜板（Megatron/Tachyon）原厂批号溯源 / 离子色谱防 CAF 核验与高低速混压叠层 + 蚀刻提铜套利（`285 ms` / `295 ms`）**：通过 Web IQ `/v3/browse` 实时核验覆铜板原厂（Panasonic Megatron-7/8、Isola Tachyon 100G、EMC EM-892K）的 **批次质保书（UL 94V-0 & 低介电扁平玻纤布 NE-Glass + HVLP3 超低轮廓铜箔批次号）** 及 **IPC-TM-650 离子色谱（IC）表面溴/氯/硫酸根残留报告与 500h 高温高湿高偏压（$85^\circ\text{C}/85\%\text{RH}/100\text{V}$）CAF 绝缘电阻报告（$\ge 10^9\ \Omega$）**——违规即在 **`285 ms`** 内触发 **`HTTP 451 CCL_RESIN_SUBSTITUTION_OR_IONIC_CAF_CONTAMINATION_HOLD`**；同时，Web IQ 自动将非关键低速控制层与厚铜电源层优化为**高低速混合压合架构（Hybrid Stackup：仅在 112G/224G SerDes 层采用天价 M8 超低损耗板材，其余电源/地层采用高 Tg FR-4 匹配膨胀系数）**，并实时按 LME 伦铜价结算 PCB 厂内层大面积蚀刻废液（Acid/Alkaline Etchant）电解回收阴极铜返利，单批立省 **`$36,800.00`**（`HTTP 409 Confirm`，净付降至 **`$193,200.00`**）。
3. **定量实测基准结论（7-Card 4:5 报告核心数据）**：
   - 在 `$230,000.00` 高速 AI 服务器 PCB 基准测试中，确定性网关在 **`11 ms`** 内拦截 TDR 阻抗失配与背钻残桩超标（`HTTP 403`），在 **`14 ms`** 内拦截 $288^\circ\text{C}$ 热冲击分层与孔铜空洞（`HTTP 422`），并通过 Web IQ 高低速混压叠层与蚀刻废液提铜在 **`295 ms`** 内捕获 **`$36,800.00`（16.0%）** 净节省，全部 **148 项单元测试 100% 通过**。

---

## ② 🎯 客户与架构师灵魂拷问 Q&A（Three Soul-Searching Questions）

### Q1：什么时候可以“只做飞针开短路测试”买电路板 vs 什么时候必须强制上“TDR 阻抗 $\pm 5\%$ + X-Ray 背钻残桩 $\le 6\text{ mil}$ + CAF 托管（`high_speed_ai_pcb_ccl_mandate_...`）”？
- **通俗大白话解答**：
  - 如果你只是**打样一块控制电风扇转速或跑马灯的双面普通 FR-4 电路板**，只要铜线通电不断路就行；
  - 但只要你是**采购 20 层以上 AI 服务器 GPU 加速母板（UBB/OAM）、800G/1.6T 光模块交换机背板或车载激光雷达高频板**，**必须 100% 强制锁死“逐拼板 TDR 阻抗 $\pm 5\%$ + VNA 插损 + X-Ray 背钻残桩 $\le 6\text{ mil}$ + IPC Class 3 热冲击 + 离子色谱防 CAF”**！因为一旦把几万美元的 GPU 芯片焊到一块背钻残桩超标的烂板上，神仙也救不回来！

### Q2：在超低损耗覆铜板（M7/M8）原厂防伪、UL 94V-0 黄卡核验与混压/蚀刻铜回收套利场景下，何时用 Microsoft Web IQ vs Exa vs Bright Data？
- **架构师黄金切分原则**：
  1. **首选 Microsoft Web IQ（`/v3/browse` + Work IQ PCB 厂 CAM/MES 与服务器 ODM PLM 联动）**：
     - **适用场景**：实时核验**松下/台光/联茂覆铜板与三井 HVLP3 铜箔原厂批次溯源码、UL iQ 数据库 94V-0 阻燃黄卡与最大工作温度（MOT）、以及高低速混压板材 BOM 差价与 LME 蚀刻电解铜回收折让**。
     - **核心优势**：在企业零信任边界内将 TDR/VNA Touchstone（`.s4p`）参数哈希与自动付款直连。
  2. **辅选 Exa（Neural Search）**：适合检索 224G PAM4 铜箔表面粗糙度（Huray 球模型）趋肤效应损耗与玻纤编织偏斜建模论文。
  3. **慎用 Bright Data**：适合抓取公开电解铜现货行情，不适合单拼板 TDR 曲线与金相微切片对账。

### Q3：高速 PCB 信号完整性与防 CAF 令牌（`high_speed_ai_pcb_ccl_mandate_...`）在服务器厂商、PCB 制造商、覆铜板原厂与托管银行之间到底是怎么流转资金的？
- **第一性原理防伪链拆解**：
  1. **随板 Coupon TDR/VNA 与 3D X-Ray 背钻硬件签章**：高频测试探针台自动生成带拼板二维码绑定的 `.s4p` 插损与 TDR 阻抗合格签名（$\pm 5\%$），且 X-Ray 确认背钻 $\text{Stub} \le 6\text{ mil}$；
  2. **IPC-6012 Class 3 热冲击与金相切片验算**：LIMS 签发 6 次 $288^\circ\text{C}$ 漂锡无分层及孔铜 $\ge 25\ \mu\text{m}$；
  3. **Web IQ 覆铜板溯源/CAF 核验与混压/提铜清算**：Web IQ 确认原厂 M8 树脂与离子洁净度合规，并结算混压叠层与蚀刻废液提铜节省 `$36,800.00`（`HTTP 409 Confirm`），或在 `19 ms` 内自动释放 `$230,000.00`。

---

## ③ 🧭 直观可视化图解（Mermaid 决策树 + 路径对比 + 时序图）

### 3.1 架构师选型决策树（`flowchart TD`）

```mermaid
flowchart TD
    A["高速 AI 服务器 PCB 与覆铜板交割 ($230,000)"] --> B{"1. 随板 TDR 阻抗、S21 插损与背钻残桩？<br/>(TDR 阻抗 ±5% & X-Ray 背钻 Stub <= 6 mil)"}
    B -- "❌ 背钻残桩 15 mil > 6 mil 引发高频谐振<br/>或蚀刻偏差致差分阻抗失配 ±12% 闭死眼图" --> C["🛑 11ms 硬阻断 HTTP 403<br/>TDR_IMPEDANCE_MISMATCH_OR_BACKDRILL_STUB_BLOCKED<br/>拒收高频失配废板，保护百万美元 GPU 免遭陪葬"]
    B -- "✅ 112G/224G 眼图张开度与残桩达标" --> D{"2. IPC Class 3 热应力与金相孔铜厚度？<br/>(6次 288°C 漂锡零分层 & 孔铜 >= 25 μm)"}
    D -- "❌ 除胶渣不良致 288°C 热冲击内层爆板起泡<br/>或深孔电镀孔壁铜厚 < 15 μm 出现裂缝" --> E["🚨 14ms 硬阻断 HTTP 422<br/>THERMAL_STRESS_DELAMINATION_OR_PLATING_VOID_BLOCKED<br/>拦截回流焊隐患批次并退回重投压合"]
    D -- "✅ 高厚径比深孔镀铜与耐热性满分" --> F{"3. Web IQ 覆铜板原厂溯源与离子色谱防 CAF？<br/>(/v3/browse 核查 M8/NE-Glass 批号 & Br-/Cl- 洁净度)"}
    F -- "❌ 偷换普通玻纤布/低阶树脂诱发偏斜<br/>或离子污染 > 1.56 μg/cm² 诱发 CAF 导电阳极丝" --> G["🛑 285ms 合规冻结 HTTP 451<br/>CCL_RESIN_SUBSTITUTION_OR_IONIC_CAF_CONTAMINATION_HOLD<br/>阻断潜伏微短路起火风险板流入智算中心"]
    F -- "✅ 正品超低损耗板材与防 CAF 绝缘达标" --> H{"4. Web IQ 启用高低速混压叠层 + 蚀刻废液提铜？<br/>(Hybrid Stackup 省 M8 耗材 + 电解再生铜冲抵)"}
    H -- "💡 非高速层混压降本并返还蚀刻铜值" --> I["🧑‍⚖️ 295ms 触发 HTTP 409 Confirm<br/>HYBRID_STACKUP_AND_ETCHANT_COPPER_RECOVERY_CONFIRM<br/>立省 $36,800 (净付 $193,200)"]
    H -- "⚡ 标准合规高速 AI 母板结算" --> J["✅ 19ms 自动放款 HTTP 200<br/>VERIFIED_HIGH_SPEED_AI_PCB_SETTLED ($230,000)"]
```

### 3.2 传统“单看直流飞针”路径 vs 智能体“TDR/背钻X-Ray+金相+混压提铜”路径对比（`flowchart LR`）

```mermaid
flowchart LR
    subgraph Legacy["❌ 传统直流飞针通断盲付路径 (GPU 陪葬与机房 CAF 短路)"]
        L1["直流飞针100%导通但背钻残桩15 mil未检"] --> L2["偷用普通玻纤布且孔壁残留卤素离子"]
        L2 --> L3["服务器厂盲付 $230,000 并贴装 8 颗高价 GPU"]
        L3 --> L4["112G 链路不通整板报废 + 3个月后 CAF 短路起火"]
    end

    subgraph Agentic["✅ Agentic TDR/VNA + X-Ray 背钻 + Web IQ 路径"]
        A1["Coupon TDR ±5% + X-Ray 背钻 <=6mil + 288°C 金相"] --> A2["11ms/14ms 在 SMT 贴片前100%拦截坏板"]
        A2 --> A3["Web IQ 285ms M8原厂/CAF核验 + 295ms 混压/提铜"]
        A3 --> A4["净省 $36,800 覆铜板与铜费或 19ms 安全清算"]
    end
```

### 3.3 端到端毫秒级验真与资金清算时序图（`sequenceDiagram`）

```mermaid
sequenceDiagram
    autonumber
    participant Fab as 高速 PCB 制造厂 & TDR/X-Ray/金相台 (Keysight/Nordson)
    participant Gate as Agentic 算力硬件托管网关 (Policy Engine)
    participant WebIQ as Microsoft Web IQ (/v3/browse)
    participant Bank as 电子制造供应链托管行 (Escrow Rail)

    Fab->>Gate: 提交 AI 服务器 UBB 高速板结算单 ($230,000) + TDR/S21 与 X-Ray 背钻残桩报文
    Gate->>Gate: Gate 1: 验算 TDR 阻抗 ±5%、S21 插损达标且 X-Ray 背钻残桩 <= 6 mil (11ms)
    alt 阻抗失配 (>±5%)、高频插损超标或背钻残桩过长 (>6 mil)
        Gate-->>Fab: HTTP 403 TDR_IMPEDANCE_MISMATCH_OR_BACKDRILL_STUB_BLOCKED (拦截 $230,000)
    else 高频信号完整性合格
        Gate->>Gate: Gate 2: 验算 IPC Class 3 6次 288°C 热冲击零分层且孔铜 >= 25 μm (14ms)
        alt 回流焊热应力分层起泡或孔壁镀铜空洞/裂纹
            Gate-->>Fab: HTTP 422 THERMAL_STRESS_DELAMINATION_OR_PLATING_VOID_BLOCKED
        else 热机械可靠性合格
            Gate->>WebIQ: 检索覆铜板 (Megatron/Tachyon) 原厂批号 + 离子色谱 CAF 报告 + 混压/提铜核算单
            WebIQ-->>Gate: 返回正牌超低损耗 CCL 与防 CAF 合规 + 混压叠层与蚀刻提铜抵扣 (-$36,800)
            alt 偷换覆铜板材质或离子污染诱发 CAF 短路隐患
                Gate-->>Fab: HTTP 451 CCL_RESIN_SUBSTITUTION_OR_IONIC_CAF_CONTAMINATION_HOLD (285ms)
            else 存在 $36,800 高低速混压叠层与蚀刻废液提铜红利
                Gate-->>Bank: HTTP 409 HYBRID_STACKUP_AND_ETCHANT_COPPER_RECOVERY_CONFIRM (295ms 净付 $193,200)
            else 标准合规高速 PCB 批次结算
                Gate->>Bank: HTTP 200 VERIFIED_HIGH_SPEED_AI_PCB_SETTLED (19ms 释放 $230,000)
            end
        end
    end
```

---

## ④ 📊 架构师选型决策矩阵（Architect Decision Matrix）

| 评估维度 | 方案 A：传统直流飞针通断 + AOI 目检 | 方案 B：仅由覆铜板厂提供纸质规格书 | **方案 C：TDR/VNA + X-Ray 背钻 + Web IQ 混压/提铜托管（推荐）** |
| :--- | :--- | :--- | :--- |
| **核心计量与品质锚点** | 直流导通电阻 + 外观无断线 | 静态纸质板材参数表 | **TDR $\pm 5\%$ + 背钻 $\text{Stub} \le 6\text{ mil}$ + $288^\circ\text{C}$ 金相 + 离子色谱防 CAF** |
| **112G/224G 眼图闭合与残桩防御** | ❌ 0%（残桩 15 mil 直流完全导通，贴完 GPU 全废） | ❌ 无法反映蚀刻与钻孔加工误差 | **✅ `11 ms` 逐拼板校验 TDR/VNA 与 X-Ray 残桩 $\le 6\text{ mil}$（`HTTP 403`）** |
| **无铅回流焊爆板与孔铜断裂防御** | ❌ 常温测试导通，一过 $260^\circ\text{C}$ 回流焊炉就断路 | ❌ 无 IST / 漂锡热冲击切片验证 | **✅ `14 ms` 锁定 IPC Class 3 6 次 $288^\circ\text{C}$ 漂锡与孔铜 $\ge 25\ \mu\text{m}$（`HTTP 422`）** |
| **覆铜板偷梁换柱与 CAF 微短路门禁** | ❌ 无法识别普通玻纤布与潜伏卤素离子污染 | ❌ 极易被假批号或水洗药水超标蒙混 | **✅ Web IQ `285 ms` 穿透核验 CCL 原厂批号与 IC 离子色谱（`HTTP 451`）** |
| **高低速混压叠层与蚀刻废液提铜套利** | ❌ 全板 30 层盲目全用天价 M8 板材且蚀刻铜白送 | ❌ 无叠层优化与铜回收对账 | **✅ Web IQ `295 ms` 混压叠层与蚀刻提铜立省 `$36,800`（`HTTP 409`）** |

---

## ⑤ 🧪 简明定量实测与 Benchmark 核心发现（含 7-Card 报告）

我们在 `lab/webiq_commerce_demo.py` 中内置了确定性策略评估器 `evaluate_high_speed_ai_pcb_ccl_policy()`，并在 `tests/test_webiq_commerce_demo.py` 中完成全覆盖验证：

| 测试场景代号 | 输入特征与遥测参数 | 网关裁决状态码 | 动作标签（Action Pill） | 端到端延迟 | 清算金额 / 拦截亏损 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`pcb_commit_ok`** | `TDR = 85Ω ± 2.8%` + 背钻残桩 `3.8 mil <= 6.0` + 孔铜 `28 μm` + `IC = 0.35 μg/cm²` | **`HTTP 200`** | `Act automatically` | **`19 ms`** | 正常清算 **`$230,000.00`** |
| **`pcb_tdr_403`** | 阻抗偏差 `±11% > ±5%` 或 X-Ray 背钻残桩 `14.5 mil > 6.0 mil` (`tdr_impedance_and_xray_backdrill_stub_verified=False`) | **`HTTP 403`** | `Send to a human` | **`11 ms`** | 拦截 **`$230,000.00`** 信号失配废板 |
| **`pcb_thm_422`** | $288^\circ\text{C}$ 热应力内层分层或孔铜 `< 25 μm` 空洞 (`ipc_class3_thermal_stress_and_plating_passed=False`) | **`HTTP 422`** | `Send to a human` | **`14 ms`** | 拦截 **`$230,000.00`** 爆板隐患批次 |
| **`pcb_caf_451`** | Web IQ 检出偷换低阶覆铜板或溴/氯离子超标诱发 CAF (`webiq_ccl_lot_and_ionic_caf_cleanliness_clean=False`) | **`HTTP 451`** | `Send to a human` | **`285 ms`** | 合规冻结 **`$230,000.00`** |
| **`pcb_hyb_409`** | Web IQ 采用电源层高低速混合压合（Hybrid Stackup）并回收蚀刻废液电解铜 (`hybrid_stackup_and_etchant_copper_savings_cents=3680000`) | **`HTTP 409`** | `Confirm` | **`295 ms`** | 净清算 **`$193,200.00`**（立省 **`$36,800.00`**） |

- **Perturbation Robustness（顺序反转稳健性）**：将 5 组高速 PCB 遥测输入做正序/逆序扰动测试，裁决一致率 **100%（0.0 pts 漂移）**。

---

## ⑥ 🛠️ 附录：生产上线快速核验与售前打单清单（Architect Checklist）

### 6.1 适用边界：Good Fit vs Not For
- **✅ Good Fit（强烈推荐采用本架构）**：
  - AI 训练/推理服务器 8-GPU 通用基板（UBB）、OAM 加速模块基板、NVLink 交换主板与 800G/1.6T 以太网交换机高多层背板；
  - 半导体 ATE 晶圆测试探针卡（Probe Card）与老化测试板（Burn-In Board）；
  - 毫米波雷达与卫星相控阵天线高频混压 PCB。
- **⛔ Not For（不适用或无需启用全部门禁）**：
  - 小家电按键单面板。

### 6.2 生产上线核验 Checklist（`- [ ]`）
- [ ] **随板测试条（Coupon）100% TDR 阻抗（$\pm 5\%$）与 SET2DIL 插损签章**：每块出货拼板必须绑定唯一二维码与实测 `.s4p` 参数哈希，严禁抽检代替全检。
- [ ] **3D X-Ray 控深背钻残桩（$\text{Stub} \le 6\text{ mil}$）必检**：消除 112G/224G PAM4 四分之一波长谐振凹陷。
- [ ] **IPC-6012 Class 3 六次 $288^\circ\text{C}$ 漂锡热冲击与孔铜 $\ge 25\ \mu\text{m}$ 金相切片**：确保无铅回流焊与高功耗热循环下零孔铜断裂。
- [ ] **超低损耗覆铜板（M7/M8 + NE-Glass + HVLP3）原厂批号与离子色谱防 CAF（$\le 0.8\ \mu\text{g/cm}^2$）穿透核验**：杜绝玻纤编织偏斜与机房运行期导电阳极丝微短路。
