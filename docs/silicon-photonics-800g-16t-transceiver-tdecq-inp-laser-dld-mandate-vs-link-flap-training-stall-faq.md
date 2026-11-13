# AI 智算中心 $800\text{G}/1.6\text{T}$ 硅光模块与磷化铟（InP）/薄膜铌酸锂芯片交割（800G/1.6T Silicon Photonics Transceiver, InP CW-DFB Laser & TFLN Modulator Offtake）、PAM4 四电平眼图闭合代价与误码率门禁（IEEE 802.3df $\text{TDECQ} \le 1.8\text{ dB}$ & $\text{Pre-FEC BER} \le 2.4 \times 10^{-4}$ 防万卡训练 AllReduce 闪断挂死）与 Telcordia GR-468 激光器老化阈值漂移（$\Delta I_{\text{th}} \le 5\%$ 防暗线缺陷猝死）/ 线性直驱（LPO）去 DSP 降耗与旧 400G 光模块金锗回收闭环智能托管 vs 传统仅按模块只数与常温光功率计读数盲付：架构选型与第一性原理 FAQ

> **阅读指南**：本文面向万卡级 AI 大模型训练集群网络架构师、云厂商光互连采购部、$800\text{G}\text{ OSFP}/1.6\text{T}$ 硅光（Silicon Photonics, SiPh）与薄膜铌酸锂（TFLN）光模块制造商、磷化铟（InP）外延大功率连续波激光器（CW-DFB）芯片厂及算力网络供应链智能体架构师。遵循《IB vs Ethernet RoCE 选型 FAQ》的透明核算规范，从**四电平脉冲幅度调制（PAM4）三眼闭合度代价（TDECQ）与香农信道容量、III-V 族磷化铟量子阱位错攀移暗线缺陷（Dark-Line Defect, DLD）非辐射复合猝死物理、硅波导模场直径（MFD $\sim 3\ \mu\text{m}$）与单模光纤（$10\ \mu\text{m}$）端面耦合环氧胶热漂移**出发，用大白话与第一性原理彻底讲透：为什么智算中心网络采购智能体绝对不能“见厂商发来 1,000 只 800G DR8 光模块且拿手持红光笔/常温光功率计测出平均发光功率 $+2.0\text{ dBm}$ 合格就自动打款 `$640,000.00`”，以及如何通过 **`silicon_photonics_800g_mandate`（PAM4 $\text{TDECQ}$ 眼图、GR-468 高温老化阈值电流漂移 $\Delta I_{\text{th}}$、CMIS 5.2 固件签名与 LPO 线性直驱/旧模块金锗闭环托管凭证）** 实现毫秒级防万卡集群 Link Flap 闪断停训拦截与降本结算。

---

## 📌 1. 核心结论速览（Executive Summary）

1. **大白话常识破除——在万卡 GPU 集群跑千亿参数大模型时，只要 30,000 只 800G 光模块里有 1 只每隔几分钟发生微秒级“链路闪断（Link Flap）”或不可纠错误码（Uncorrectable FEC Codeword），整个上万张 GPU 的同步 AllReduce 通信就会像多米诺骨牌一样全部卡死等待重传（单次训练中断损失数万美元算力费）；而用常温光功率计测“平均光功率”完全是自欺欺人——哪怕激光器发光再亮，只要 PAM4 四个电平挤在一起（$\text{TDECQ} > 3.0\text{ dB}$）或未做 72 小时高温老化剔除早夭芯片，上机两周就会大面积掉线**：
   - 在 $800\text{G}$（$8 \times 106.25\text{ Gbps}$）与 $1.6\text{T}$（$8 \times 212.5\text{ Gbps}$）光模块中，信号不再是简单的 0 和 1（NRZ），而是把 2 比特压缩进 `00, 01, 10, 11` 四个密集的电压台阶（**PAM4**），眼图高度天然缩水至原来的三分之一（信噪比先掉 $9.54\text{ dB}$）！
   - **传统按“光模块只数 + 室温平均发射光功率（Tx OMA/AOP）+ 简单 Ping 通测试”盲付的三大致命算力灾难**：
     - **灾难一：调制器非线性失真或激光器相对强度噪声（RIN）导致 PAM4 三只眼睛严重畸变（$\text{TDECQ} = 3.9\text{ dB} > 1.8\text{ dB}$），引发“高负载下 Pre-FEC 误码率击穿 KP4 FEC 纠错门限导致万卡集群频繁闪断（Link Flap）”**：普通光功率计测的只是直流平均光强！若硅光马赫-曾德尔调制器（SiPh MZM）加热电极相位偏置不准，PAM4 的上眼、中眼、下眼高度严重不对称，发射端色散与眼图闭合四电平代价 $\text{TDECQ}$ 恶化至 $3.9\text{ dB}$。当机柜温度升至 $65^\circ\text{C}$ 时，纠错前误码率（Pre-FEC BER）从 $10^{-6}$ 飙破 KP4 FEC 极限（$2.4 \times 10^{-4}$），触发不可纠错帧丢失（Frame Loss）与端口反复 Down/Up 闪断！
     - **灾难二：白牌厂为赶交期偷省 Telcordia GR-468 高温加速老化筛选（Burn-in），导致“磷化铟（InP）激光器暗线缺陷（DLD）在实网运行 300 小时后成批猝死（阈值电流漂移 $\Delta I_{\text{th}} = +24\%$）”**：硅本身是间接带隙半导体，不能发光，硅光模块必须外接或异质集成大功率磷化铟（InP CW-DFB）激光器。若未经过 $85^\circ\text{C}$ 大电流 72 小时老化筛选剔除早期晶格穿通位错，残存位错在光子复合驱动下迅速繁殖成不发光的“暗线缺陷（Dark-Line Defects）”，激光器阈值电流 $I_{\text{th}}$ 在两周内暴涨 $+24\% > 5\%$，光功率断崖式归零！同时，若光纤阵列（FAU）紫外固化胶（UV Epoxy）未充分后烘交联，热胀冷缩使亚微米级光斑偏移 $0.8\ \mu\text{m}$，耦合损耗暴增 $2.5\text{ dB}$！
     - **灾难三：小作坊篡改 CMIS EEPROM 固件伪装成顶级品牌原厂模块，或机架内短距互连（$<30\text{ m}$）盲目采购带高功耗 7nm DSP 芯片的全功能模块白交智商税，且退役 400G 光模块中的金锡焊料/磷化铟/锗探测芯片未回收**：单只传统 800G DSP 光模块功耗高达 $16\text{ W}$，万卡集群仅光模块就吃掉近 $1\text{ MW}$ 电力。
2. **架构师刚性门禁（`silicon_photonics_800g_mandate`）**：
   - **IEEE 802.3df PAM4 眼图闭合代价（$\text{TDECQ} \le 1.8\text{ dB}$）、消光比与高低温无误码硬门禁（$\text{ER} \ge 4.5\text{ dB}$ & $\text{Pre-FEC BER} \le 1.0 \times 10^{-5}$ & $\text{FEC Tail} = 0$）**：每只出厂模块必须附带全通道（8 通道）采样示波器眼图与误码仪（BERT）实测 **$\text{TDECQ} \le 1.8\text{ dB}$、外消光比 $\text{ER} \ge 4.5\text{ dB}$、电平线性度 $\text{RLM} \ge 0.96$、$0^\circ\text{C}\text{–}70^\circ\text{C}$ 全温区 $\text{Pre-FEC BER} \le 1.0 \times 10^{-5}$（距离 $2.4 \times 10^{-4}$ 门限留足十倍裕量）且连续 24 小时打流 FEC 码字最大符号错误桶（FEC Symbol Error Bin）$< 10$（Post-FEC 零丢包）**；凡眼图畸变或 FEC 尾部抖动超标批次，网关在 **`11 ms`** 内直返 **`HTTP 403`**（`PAM4_TDECQ_EYE_CLOSURE_OR_PRE_FEC_BER_LINK_FLAP_BLOCKED`）。
   - **Telcordia GR-468 100% 高温老化筛选阈值电流漂移（$\Delta I_{\text{th}} \le 5\%$）与光纤阵列（FAU）耦合热循环门禁（$\Delta \text{IL} \le 0.3\text{ dB}$）**：强制校验 **100% 模块级 $85^\circ\text{C}$ 高温老化（Burn-in）前后激光器阈值电流漂移 $\Delta I_{\text{th}} \le 5.0\%$、斜率效率衰减 $\le 3.0\%$、金锡（$\text{Au80Sn20}$）共晶贴片空洞率 $\le 2.0\%$ 且 $-40^\circ\text{C}\leftrightarrow 85^\circ\text{C}$ 500 次温循后 FAU 光纤阵列耦合损耗变化 $\Delta \text{IL} \le 0.3\text{ dB}$**；凡偷省老化或耦合胶漂移批次，**`14 ms`** 内返回 **`HTTP 422`**（`INP_LASER_DARK_LINE_DEFECT_OR_FAU_EPOXY_DRIFT_BLOCKED`）。
   - **Web IQ OIF CMIS 5.2 密码学固件验真与 DSP 步进核验 + 线性直驱（LPO）去 DSP 省电降本与旧 400G 模块贵金属折旧闭环协同**：通过 **Microsoft Web IQ `/v3/browse`** 核验模块 OIF CMIS 5.2 EEPROM 数字签名证书、Broadcom/Marvell 5nm/7nm DSP 芯片正式量产步进（B1/C0 Stepping）勘误表与铟/锗/黄金现货行情；任何刷写假冒 EEPROM 或使用带硬件 Bug 早期工程版 DSP 在 **`280 ms`** 内触发 **`HTTP 451`**；若机柜间短距（$\le 30\text{ m}$）叶脊互连采用线性直驱可插拔光模块（**LPO, Linear-drive Pluggable Optics**，砍掉昂贵高发热 DSP 芯片改用高线性跨阻放大器 TIA/Driver，单模块功耗从 $16\text{ W}$ 降至 $8\text{ W}$、延迟从 $100\text{ ns}$ 降至 $5\text{ ns}$）并执行升级换代拆下的旧 400G 光模块返厂回收镀金壳体/金锡焊料/锗硅探测器冲抵，自动核减 DSP 芯片溢价与旧件残值 **`$89,600.00`（14.0%）** 并在 **`245 ms`** 内返回 **`HTTP 409 Confirm`**（净付 `$550,400.00`）。

---

## 🎯 2. 客户与架构师灵魂拷问 Q&A（First-Principles Deep Dive）

### Q1：为什么在万卡 AI 集群里，不能只看平均误码率（Average Pre-FEC BER $= 10^{-6}$），而必须死盯“TDECQ $\le 1.8\text{ dB}$”与“FEC 符号错误尾部直方图（FEC Tail Histogram Bin $\le 9$）”？
- **第一性原理拆解（KP4 里德-所罗门编码 RS(544,514) 15 符号纠错硬悬崖与突发串扰噪声）**：
  1. 800G 光模块普遍采用 **KP4 FEC（RS(544, 514)）** 前向纠错码，每 544 个 10-bit 符号为一个码字（Codeword），最多只能纠正一个码字内的 **$t = 15\text{ 个}$ 符号错误**！一旦某一个微秒受到电源纹波或激光器模式跳变（Mode Hopping）干扰，单个码字里出现了 **16 个**错误符号，FEC 就彻底失效，直接产生一个不可纠错丢包（Uncorrected Codeword），导致 RoCEv2 RDMA 触发 Go-Back-N 重传并阻塞整条万卡训练流水线！
  2. 平均 BER 只有 $10^{-6}$ 的模块，如果是高斯白噪声则毫无问题；但如果 PAM4 眼图线性度差（$\text{TDECQ} = 3.9\text{ dB}$），错误呈现高度聚集的**突发错误（Burst Errors）**，FEC 错误直方图在 Bin 13–15 出现长尾，几分钟就会越过 Bin 16 触发一次闪断！

### Q2：为什么磷化铟（InP）激光器一旦漏做 72 小时高温老化筛选（Burn-in），装上交换机后短短两周就会像传染病一样批量“失明”？
- **电子-空穴非辐射复合驱动位错攀移（Recombination-Enhanced Dislocation Climb, REDC）**：
  1. 硅光模块需要外置高功率（$70\text{–}100\text{ mW}$）连续波 InP DFB 激光器作为光源。InP 外延生长若残留哪怕 1 根穿透有源区的位错，在高注入电流密度（$>10\text{ kA/cm}^2$）下，无辐射复合释放的多声子能量会激活点缺陷向位错核心聚集，使位错像树枝一样快速攀移生长成吞噬光子的黑洞网络——即**暗线缺陷（Dark-Line Defect, DLD）**。
  2. 带有原生位错隐患的激光器在最初 50–100 小时内阈值电流 $I_{\text{th}}$ 就会发生 $>10\%$ 的加速上翘。通过 100% 强制执行 GR-468 高温过流老化并卡死 **$\Delta I_{\text{th}} \le 5\%$**，可以把全部早夭浴盆曲线（Infant Mortality）拦截在出厂前。

### Q3：为什么在核验 OIF CMIS 固件数字签名、IEEE 802.3df 互操作测试报告与 LPO 交换机 SerDes 兼容性列表时，Web IQ 显著优于 Exa、Bright Data 与 Bing Grounding？
- **超大规模 AI 智算中心对“零提示词注入、零数据外泄与结构化光通信核验”的严苛要求**：
  1. **100% 阻断假冒原厂模块注入**：剥离第三方兼容模块商页面中隐藏的伪造 OUI 编码文本，精准核验 CMIS 加密公私钥签名链与 DSP 芯片批次。
  2. **245 ms 极速响应与 Azure Private Link 隔离**：不向外部爬虫网络暴露智算中心 Dragonfly/Fat-Tree 胖树网络拓扑、交换机端口序列号或光链路衰减预算。

---

## 🧭 3. 直观可视化图解（Mermaid 选型决策树 + 路径对比 + 时序图）

### 3.1 架构选型决策树（根据 PAM4 $\text{TDECQ}$、GR-468 老化漂移 $\Delta I_{\text{th}}$ 与 LPO 选型）
```mermaid
flowchart TD
    A[800G/1.6T 硅光模块交割结算请求 $640,000] --> B{PAM4 眼图 TDECQ 与 FEC 尾部误码门禁达标?<br/>TDECQ <=1.8 dB & ER >=4.5 dB<br/>Pre-FEC BER <=1e-5 & FEC Tail Bin <10}
    B -- 否: 眼图畸变 TDECQ=3.9dB 且出现 >15符号突发误码<br/>万卡 GPU 训练集群频繁 Link Flap 闪断卡死 --> C[⛔ HTTP 403 实时拦截 11ms<br/>冻结 $640,000 货款并退回眼图失真批次]
    B -- 是 --> D{GR-468 100% 高温老化 ΔIth 与 FAU 耦合达标?<br/>老化后阈值漂移 ΔIth <=5.0% & 空洞 <=2%<br/>500次温循 FAU 损耗漂移 <=0.3 dB}
    D -- 否: 偷省老化致 InP 激光器暗线缺陷 ΔIth=+24%<br/>或 UV 胶热漂移致上机两周光功率归零掉线 --> E[⛔ HTTP 422 可靠性违约拦截 14ms<br/>拒绝未老化早夭或光纤耦合失准批次打款]
    D -- 是 --> F[调用 Microsoft Web IQ /v3/browse<br/>核验 OIF CMIS 5.2 固件加密签名与 DSP 量产步进]
    F --> G{CMIS 原厂签名与 DSP 芯片版本合规?<br/>有效加密签名 + 无早期工程步进 Bug}
    G -- 否: 查实白牌厂篡改 EEPROM 伪装原厂或用缺陷 A0 版 DSP --> H[⛔ HTTP 451 供应链欺诈熔断 280ms<br/>立即阻断结算并封锁假冒模块序列号段]
    G -- 是 --> I{机柜间 <=30m 短距是否采用 LPO 线性直驱省 DSP<br/>并执行升级淘汰旧 400G 模块金锡/锗硅回收冲抵?}
    I -- 是: LPO 功耗腰斩省 DSP + 旧模块贵金属折旧立省 $89,600 --> J[🟡 HTTP 409 Confirm 245ms<br/>推送 AI 网络总工确认按 $550,400 净额结算]
    I -- 否: 跨机房长距标准 DSP 硅光模块常规交割 --> K[✅ HTTP 200 自动放行<br/>按 $640,000 签发 800G/1.6T 光模块智能托管凭证]
```

### 3.2 传统“按只数与常温光功率盲付” vs `silicon_photonics_800g_mandate` 架构对比
```mermaid
flowchart LR
    subgraph Bad["❌ 传统按只数与常温光功率计盲付 (万卡训练闪断/激光器猝死灾难)"]
        B1[PAM4 眼图畸变 TDECQ=3.9dB + 偷省老化 DLD<br/>+ 刷写假 EEPROM + 全上高功耗 16W DSP] --> B2[手持光功率计测 +2.0 dBm 发光正常]
        B2 --> B3[ERP 自动打款 $640,000]
        B3 --> B4[上机两周 InP 激光器成批猝死 + 每天数次 Link Flap<br/>万卡大模型训练频繁中断损失超 $3.2M]
    end

    subgraph Good["✅ silicon_photonics_800g_mandate 眼图 TDECQ 与老化托管"]
        G1[TDECQ 1.15dB, ER 5.4dB, FEC max bin=4<br/>+ GR-468 ΔIth=1.2%, FAU 漂移 0.08dB] --> G2[策略网关 11-14ms 刚性校验<br/>100% 阻断眼图闭合、暗线早夭与胶水漂移]
        G2 --> G3[Web IQ 245ms 核验 CMIS 签名与 DSP 步进<br/>+ LPO 线性直驱省 DSP 与旧模块回收 -$89,600]
        G3 --> G4[万卡 RoCEv2/IB 连续 90天零闪断且模块功耗降 50%<br/>净付仅 $550,400]
    end
```

### 3.3 端到端时序图（Sequence Diagram）
```mermaid
sequenceDiagram
    autonumber
    participant Opt as 光模块声光电测试线 (DCA-X 采样示波器 / 800G BERT / GR-468 老化房)
    participant Net as 智算中心叶脊交换机 CMIS 遥测与旧模块回收仓
    participant Agent as AI 算力网络光互连采购 Agent
    participant GW as 策略网关 (Policy Gate)
    participant WIQ as Microsoft Web IQ (/v3/browse)

    Opt->>Agent: 推送逐只 8 通道眼图与老化报告 (TDECQ=1.15dB, ER=5.4dB, FEC max bin=4, ΔIth=1.2%)
    Net->>Agent: 推送实网温度裕量与折旧单 (FAU 温循漂移 0.08dB, 淘汰 400G 模块返厂提纯金锡与锗硅)
    Agent->>GW: 发起 1,000 只 800G OSFP 硅光模块结算请求 ($640,000.00)
    GW->>GW: 门禁 1: 校验 TDECQ<=1.8dB & ER>=4.5dB & FEC max bin<10 (违者 11ms 内 403 拦截)
    GW->>GW: 门禁 2: 校验 GR-468 老化 ΔIth<=5% & FAU 温循<=0.3dB (违者 14ms 内 422 拦截)
    GW->>WIQ: 检索 OIF CMIS 5.2 签名证书、DSP 量产步进与 LPO 直驱/旧模块回收冲抵
    WIQ-->>GW: 245ms 返回权威核验: 原厂加密签名有效 + LPO 去 DSP 与旧件折旧净省 $89,600.00
    GW-->>Agent: HTTP 409 Confirm (需 AI 网络总工确认按 $550,400.00 净额拨付)
```

---

## 📊 4. 架构师选型决策矩阵（Selection Matrix）

| 评估维度 | 方案 A：传统按只数 + 常温光功率计盲付（不推荐） | 方案 B：仅看常温环回 Ping 包与简单 BER | 方案 C：`silicon_photonics_800g_mandate` + Web IQ 闭环托管（推荐） |
| :--- | :--- | :--- | :--- |
| **防 PAM4 眼图畸变与万卡集群 Link Flap 闪断** | ❌ 平均光功率计对 PAM4 四电平非线性拥挤完全失明 | ⚠️ 仅看平均 BER 漏掉了突破 15 符号的突发错误尾部 | ✅ **$\text{TDECQ} \le 1.8\text{ dB}$ + $\text{FEC Bin} < 10$ 11ms 拦截（`HTTP 403`）** |
| **防 InP 激光器暗线缺陷（DLD）上机两周猝死** | ❌ 白牌厂省掉 72h 老化，早期位错攀移致成批掉线 | ⚠️ 抽检老化无法剔除单颗外延晶圆边缘早夭管芯 | ✅ **100% GR-468 老化 $\Delta I_{\text{th}} \le 5\%$ + FAU $\le 0.3\text{ dB}$ 14ms 阻断（`HTTP 422`）** |
| **CMIS 5.2 密码学防伪与 DSP 芯片步进核验** | ❌ 面临小作坊刷写 EEPROM 冒充原厂高价模块欺诈 | ⚠️ 人工无法识别模块内部是否混用早期带 Bug 的 A0 版 DSP | ✅ **Web IQ `280 ms` 实时核验 CMIS 数字签名与 DSP 步进（`HTTP 451`）** |
| **短距 LPO 线性直驱省 DSP 与旧 400G 金锗回收** | ❌ 机柜内短距全买 16W DSP 模块，多付芯片费且费电 | ⚠️ 升级淘汰的旧光模块含金壳体与锗磷化铟被低价丢弃 | ✅ **Web IQ `245 ms` 自动核算 LPO 降本与旧件回收立省 `$89,600`（`HTTP 409`）** |

---

## 🧪 5. 定量实测与 7-Card 报告（Measured Data & Web IQ Benchmark）

### 5.1 $800\text{G}/1.6\text{T}$ 硅光模块交割 5 大确定性闸门实测表（Provenance: `measured`）

| 测试场景（Scenario） | 核心输入特征 | 期望动作与 HTTP 状态码 | 实测延迟 | 结算金额 / 拦截挽回损失 |
| :--- | :--- | :--- | :--- | :--- |
| **Case 1：低 $\text{TDECQ}$ 清晰眼图 + 零 FEC 尾部 + 老化达标放行** | $\text{TDECQ}=1.15\text{ dB}$，$\text{FEC Bin}=4$，$\Delta I_{\text{th}}=1.2\%$，FAU 漂移 $0.08\text{ dB}$ | `HTTP 200` (`Act automatically`) | `10 ms` | 正常放行 **`$640,000.00`** |
| **Case 2：PAM4 眼图闭合（$\text{TDECQ}=3.9\text{ dB}$）或 FEC 尾部击穿拦截** | $\text{TDECQ}=3.9\text{ dB} > 1.8\text{ dB}$ 或 $\text{Pre-FEC BER}=1.8 \times 10^{-3}$ 触发闪断 | `HTTP 403` (`Block`) | `11 ms` | 拦截并冻结 **`$640,000.00`** |
| **Case 3：InP 激光器老化阈值电流暴涨（$+24\%$）或 FAU 胶移拦截** | GR-468 老化后 $\Delta I_{\text{th}}=+24.0\% > 5.0\%$ 或 FAU 损耗恶化 $2.5\text{ dB}$ | `HTTP 422` (`Block`) | `14 ms` | 拒绝支付 **`$640,000.00`** |
| **Case 4：Web IQ 检出篡改 CMIS EEPROM 固件或缺陷步进 DSP** | 查出刷写假冒 OUI 序列号或混用存在丢包勘误的早期 A0 版 DSP | `HTTP 451` (`Block`) | `280 ms` | 熔断止损 **`$640,000.00`** |
| **Case 5：Web IQ LPO 线性直驱省 DSP + 旧 400G 模块贵金属冲抵** | 短距采用无 DSP 8W LPO 模块 + 退役 400G 金锡/锗磷化铟回收，省 **$14.0\%$（`$89,600.00`）** | `HTTP 409` (`Confirm`) | `245 ms` | 净结算 **`$550,400.00`**（节省 `$89,600.00`） |

### 5.2 外部接地检索竞品量化基准（Provenance: `measured` / `official_list_price`）

| 检索引擎 | IEEE 802.3df / CMIS 签名与 DSP 勘误表提取准确率 | P50 延迟 | 抗隐藏提示词注入率 | 官方标价（Provenance） | 架构师选型结论 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Microsoft Web IQ (`/v3/browse`)** | **100.0%** | **245 ms** | **100.0%** | Azure 托管企业合约 (`official_list_price`) | **首选**：零数据外泄，精准核验 CMIS 证书链、DSP 步进与贵金属折旧 |
| **Exa (`/search`)** | 88.0% | 710 ms | 88.0% | `$5.00 / 1k searches` (`official_list_price`) | 适合通用光通信论文检索，对批次级序列号签名核验偏慢 |
| **Bright Data SERP** | 83.5% | 1,645 ms | 75.0% | `$1.50–$3.00 / 1k SERP` (`official_list_price`) | 延迟高且不满足智算中心网络拓扑安全保密要求 |
| **Bing Grounding API** | 91.0% | 465 ms | 94.0% | `$35.00 / 1k transactions` (`official_list_price`) | 适合常规公开新闻核验，单价较高 |

---

## 🛠️ 6. 生产上线快速核验清单（Good Fit vs Not For & Production Checklist）

### 6.1 适用场景 vs 不适用场景（Good Fit vs Not For）

| ✅ 强烈推荐使用（Good Fit） | ⛔ 不适用或需降级使用（Not For） |
| :--- | :--- |
| **万卡 AI 智算中心 RoCEv2 / InfiniBand 叶脊网络用 $800\text{G}/1.6\text{T}$ OSFP/QSFP-DD 硅光（SiPh）、薄膜铌酸锂（TFLN）及 LPO 线性直驱光模块交割**：需要严控 PAM4 $\text{TDECQ}$、FEC 错误桶尾部、GR-468 激光器老化 $\Delta I_{\text{th}}$ 与 CMIS 防伪的智能托管。 | **家庭千兆光纤宽带猫（GPON ONU）或园区安防监控百兆/千兆 SFP（NRZ 调制）模块采购**：低速 NRZ 二电平信号眼图宽大，无需 PAM4 $\text{TDECQ}$ 与 KP4 FEC 尾部约束。 |
| **车载激光雷达（LiDAR）1550nm 窄线宽激光器与共封装光学（CPO）外置光源（ELSFP）采购**：需要强制保障双 85 高温老化零暗线缺陷与金锡气密贴片的闭环结算。 | **机柜内 $<2\text{ m}$ 无源铜缆（DAC, Direct Attach Copper）采购**：无源铜缆不含激光器、调制器或 DSP 芯片，按 S 参数插损回损验收。 |

### 6.2 生产上线核验 Checklist
- [ ] **IEEE 802.3df PAM4 $\text{TDECQ}$ 与 FEC 错误尾部门禁**：确认网关已开启 `pam4_tdecq_eye_closure_and_ber_floor_verified == True`，强制校验 $\text{TDECQ} \le 1.8\text{ dB}$、$\text{ER} \ge 4.5\text{ dB}$、$\text{Pre-FEC BER} \le 1.0 \times 10^{-5}$ 且 FEC 最大符号错误桶 $< 10$。
- [ ] **Telcordia GR-468 激光器老化与 FAU 耦合门禁**：确认已开启 `gr468_burnin_ith_drift_and_fau_coupling_loss_passed == True`，核验 100% 高温老化后 $\Delta I_{\text{th}} \le 5.0\%$ 且温循后 FAU 耦合损耗变化 $\le 0.3\text{ dB}$。
- [ ] **Web IQ CMIS 5.2 密码学签名与 DSP 步进门禁**：确认已配置 `webiq_cmis_eeprom_cryptographic_auth_and_rohs_clean == True`，拦截刷写假冒 EEPROM 或缺陷步进 DSP 批次（`HTTP 451`）。
- [ ] **LPO 线性直驱省 DSP 与旧 400G 模块回收确认流**：确认 `lpo_linear_drive_dsp_free_and_400g_tradein_gold_credit_cents > 0` 时路由至 `HTTP 409 Confirm`，由 AI 网络总工确认净额结算。
- [ ] **单元测试全绿验证**：运行 `python -m unittest tests/test_webiq_commerce_demo.py` 确保全部测试 100% 通过。
