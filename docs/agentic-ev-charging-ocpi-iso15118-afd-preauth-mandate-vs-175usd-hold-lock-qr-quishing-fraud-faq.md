# 智能体新能源车机充电（EV Charging `MCC 5552`）ISO 15118 即插即充与 OCPI v2.2.1 计量清算架构：EMAID 硬件证书防假二维码（Quishing）、OCMF 电表签名与 `$175` 预授权 `0420` 秒解冻令牌（`agentic_ev_charging_ocpi_iso15118_afd_mandate_...`）vs 传统充 `$18` 电被冻 `$175` 银行卡数周与假贴纸盗刷选型与原理解析 FAQ

> **文档类型**：架构师选型与第一性原理解析 FAQ（对标 `ib-vs-ethernet-roce-selection-faq.md` 六段式标杆规范）  
> **核心覆盖领域**：智能网联汽车车机支付（In-Car Agentic Commerce）与直流超充站（`MCC 5552` EV Charging / `MCC 5542` AFD 自动加油机）、`ISO 15118-20` 即插即充（Plug & Charge `EMAID` X.509 双向证书认证防二维码覆盖钓鱼 Quishing）、漫游结算协议 `OCPI v2.2.1` 充电明细单（CDR: Charge Detail Record）、德国计量法（`Eichrecht` / `OCMF` 开放充电电表数字签名）与美国加州 CTEP 计量规范、以及拔枪结单瞬间毫秒级触发 `ISO 8583 0420` 预授权差额冲正（消除 `$125–$175` 高额预授权锁卡客诉）  
> **阅读对象**：智能网联车企（OEM）座舱与车联网架构师、充电运营商（CPO）与出行服务商（eMSP）结算工程负责人、能源支付风控总监  
> **关联 Interactive 交付物**：[`live-demo.html`（含 Round 212 智能体车机 ISO 15118 即插即充防假二维码、OCMF 电表签名校验与拔枪 `$175` 预授权秒解冻交互沙盒）](../live-demo.html) · [`assets/svg/214-agentic-ev-charging-ocpi-iso15118-afd-preauth-2026-11-14.svg`](../assets/svg/214-agentic-ev-charging-ocpi-iso15118-afd-preauth-2026-11-14.svg)

---

![2026-11-14 智能体新能源车机充电 (MCC 5552) ISO 15118 即插即充、OCMF 电表签名与 $175 预授权 0420 秒解冻架构一图流](../assets/svg/214-agentic-ev-charging-ocpi-iso15118-afd-preauth-2026-11-14.svg)

## 1. 📌 核心结论速览（Executive Summary）

在智能网联新能源汽车（EV）与自动驾驶车队（Robotaxi）的无人值守自动补能场景中，车载出行 Agent 需要与跨品牌的充电桩运营商（CPO）实时完成身份鉴权、分时电价协商与拔枪自动扣款。然而，当车企与充电网络沿用传统的**“桩体贴静态纸质二维码扫码 H5 支付 + 插枪一口气冻结 `$150–$175` 最高预授权但拔枪后不发 `0420` 冲正 + 用软件估算度数而非硬件电表加密签名出账”**的粗放架构时，将直接引爆三大车主客诉与安全合规灾难：
1. **“充了 `$18` 的电，借记卡却被冻结 `$175` 长达一周”引爆车主群体投诉**：根据 Visa 与 Mastercard 针对无人值守加油机与充电桩（`MCC 5542 / 5552`）的特殊授权规则，收单行在插枪启动前不知道车主会充多少度电，因此默认发起最高 **`$125–$175` 的预估预授权冻结（AFD Pre-Auth Hold）**。当车主充完 `42 kWh`（实付 `$18.50`）拔枪驶离后，如果充电平台结算网关没有在同一秒内向发卡行发送 **`ISO 8583 0420` 部分预授权冲正报文**释放未使用的 `$156.50` 差额，车主的银行卡将被死锁 `$156.50` 长达 5–10 个工作日！
2. **充电桩外壳静态二维码被黑产贴纸覆盖（Quishing 二维码钓鱼），车主扫码瞬间银行卡与 3DS 验证码被盗刷**：欧美及国内公共充电站频繁发生“二维码贴纸覆盖攻击（QR Code Phishing / Quishing）”——黑产打印高仿充电桩品牌的防水二维码贴纸，直接贴在充电桩屏幕或枪座原二维码上方。车主扫码后进入高仿钓鱼支付页，不仅被骗走信用卡号与 CVV，充电桩还根本没启动！
3. **无硬件电表密码学签名（`OCMF / Eichrecht`）的软件估算度数与天价超时占位费（Idle Fee），遭监管重罚与拒付败诉**：在断网重连或充电桩固件抖动时，部分 CPO 后台用“充电功率 × 持续时间”粗略估算充电度数，或在未给车主发送满电宽限期通知的情况下强扣 `$1.00/分钟` 的天价占位费。这不仅直接违反**德国《计量与校准法（Eichrecht）》与美国加州 CTEP / NIST Handbook 44 法定计量标准**，而且车主一旦提起账单争议，商户因拿不出经电表私钥签名的 `OCMF（开放充电计量格式）` 报文而 100% 败诉退款！

**第一性原理选型结论**：
1. **彻底淘汰公共充电桩静态二维码扫码支付；全面升级为 `ISO 15118-2 / 15118-20` 即插即充（Plug & Charge）电力线通信（PLC）双向硬件证书认证**：充电枪插入车辆充电口瞬间，车辆内置硬件安全模块（TPM）通过充电电缆直接向桩端出示经 V2G Root PKI 签名的 **`EMAID（电动汽车出行账户标识符）` X.509 合同证书**，全程无需手机扫码，从物理上 **100% 免疫假二维码贴纸钓鱼（Quishing）**！
2. **签发绑定了电表硬件签名与冲正闭环的 `agentic_ev_charging_ocpi_iso15118_afd_mandate_...` 令牌，强制执行两大结算不变量**：① **拔枪结单（`Session_Stop`）后 `<15ms` 内必须根据 `OCPI v2.2.1 CDR` 实收电费同步发送 `ISO 8583 0420` 预授权差额冲正**（3 秒内解冻剩余的 `$156.50` 额度）；② **账单度数必须携带直流电表硬件私钥签名的 `OCMF（Open Charge Metering Format）` 计量证明，且超时占位费（Idle Fee）强制执行宽限期通知与封顶上限**。
3. **涉及国际电动汽车漫游协议 `OCPI v2.2.1`、ISO 15118 Hubject V2G 公钥基础设施规范、德国 `Eichrecht` / 美国加州 DMS 充电计量法规及分时电价（TOU Tariff）核查时，首选 Microsoft Web IQ（`/v3/search` + `/v3/browse`）**：对标 Exa 与 Bright Data，Web IQ 可在 `<350ms` 内提取权威国际能源与充电标准规范。

| 核心充电结算与安全维度 | 传统桩体贴纸扫码 + 放任 $175 冻结不冲正（反模式） | 智能体 ISO 15118 即插即充 + OCMF + 0420 秒解冻（推荐架构） | 车主体验与合规风控收益 |
| :--- | :--- | :--- | :--- |
| **防假二维码贴纸覆盖钓鱼（Quishing）** | 车主扫桩体贴纸进入钓鱼网被盗刷信用卡 | **ISO 15118 PLC 充电线直连握手（`EMAID` 证书）**：零扫码交互 | 100% 物理免疫公共桩假二维码贴纸钓鱼攻击 |
| **`$125–$175` 高额预授权解冻速度** | 充 `$18` 电后未发冲正，`$156.50` 差额冻结长达 7 天 | **拔枪结单同事务触发 `ISO 8583 0420` 部分冲正**：3 秒解冻回卡 | 彻底消除充电桩“吃钱锁卡”的头号用户体验痛点 |
| **充电度数（kWh）法定计量抗抵赖** | 断网时用时间×功率软件估算度数，遭计量局罚款与拒付 | **强制直流电表硬件签名 `OCMF`（起止读数 + 分时费率哈希）** | 100% 满足欧美 `Eichrecht` 与 NIST 法定贸易计量审计 |
| **超时占位费（Idle Fee）争议防控** | 未发满电提醒直接暗扣 `$120` 占位费，引发银行拒付 | **满电 5 分钟宽限期强推通知 + 单次占位费硬封顶（如 `<=$30`）** | 兼顾场站周转效率与零恶意扣费投诉 |

---

## 2. 🎯 客户与架构师灵魂拷问 Q&A（First-Principles Deep Dive）

### Q1：为什么公共充电桩上的二维码会被黑产轻易调包（Quishing）？`ISO 15118 Plug & Charge（即插即充）` 是如何从根源上消灭二维码的？
* **第一性原理拆解**：
  1. **静态物理二维码的“无状态易覆盖缺陷”**：贴在户外充电桩金属壳上的二维码没有任何防篡改能力。黑产花 1 毛钱印一张带品牌 Logo 的不干胶贴纸盖上去，人眼根本无法分辨；即便采用屏幕动态二维码，黑产也能通过在桩边架设伪基站或贴一张“屏幕故障请扫下方备用码”贴纸诱导车主中招。
  2. **ISO 15118 的密码学物理信道绑定**：
     - 当支持 `ISO 15118-2 / 15118-20` 的充电枪插入汽车充电口时，车辆与充电桩之间通过充电线缆内的控制导引线（Control Pilot, 基于 HomePlug GreenPHY 电力线通信 PLC）直接建立 **TLS 1.3 加密隧道**；
     - 车机安全芯片自动出示绑定了车主支付账户的 **`EMAID`（e-Mobility Account Identifier，格式如 `US-89A-C12345678-X`）数字证书**，充电桩通过 V2G Root CA 验证签名有效后，在 **2 秒内直接开始充电**！整个过程零手机参与、零二维码扫描，黑产贴再多假二维码也毫无用处！

### Q2：什么是 `OCMF（开放充电计量格式）` 与德国 `Eichrecht` 法案？为什么充电桩后台数据库不能自己随便改一下充电度数出账？
* **贸易结算级电表（Fiscal Metering）的防篡改铁律**：
  1. **软件后台不可信原则**：在欧洲（以德国 `MessEG / Eichrecht` 为代表）与美国（加州 CTEP / NIST Handbook 44），用于向公众按千瓦时（kWh）收费的充电桩属于受国家监管的法定贸易计量器具。法律严禁充电运营商（CPO）的云服务器在没有电表硬件签名的情况下自行计算或修改度数！
  2. **OCMF 数字签名结构**：在充电桩内部的认证直流电表（Certified DC Meter）芯片内烧录有不可导出的硬件椭圆曲线私钥（ECDSA secp256r1）。每次充电开始（`Start_Wh`）与拔枪结束（`Stop_Wh`），电表芯片直接将 `{事务ID, 起始电表读数, 结束电表读数, UTC时间戳, 电价表哈希}` 打包生成一段 **OCMF 签名字符串**，嵌入到 `OCPI v2.2.1 CDR（充电详单）` 中一路透传给车主账单——任何人（包括充电站老板自己）只要改动 0.01 度电，ECDSA 验签立刻失败（触发网关 `HTTP 422` 拦截）！

### Q3：在核查 `OCPI v2.2.1` 漫游清算标准、`ISO 15118-20` V2G 证书规范、Visa/Mastercard `MCC 5552` 预授权规则以及各国充电计量法规时，Microsoft Web IQ、Exa 与 Bright Data 如何选型？
* **三方能力对比**：
  - **Microsoft Web IQ（`/v3/search` + `/v3/browse`）**：直连 EVRoaming 基金会官方 `OCPI v2.2.1` 协议文档（`evroaming.org`）、Visa/Mastercard `MCC 5552` 电动汽车充电商户指南、德国联邦物理技术研究院（PTB `Eichrecht`）及美国 NIST / 加州 DMS 计量法规，在 `280ms` 内返回确定性条款快照（`official_doc_snapshot`），企业级 Entra ID 租户隔离零合规隐患。
  - **Exa Neural Search**：适合检索新能源汽车行业宏观新闻，不适合作为 `OCPI CDR` JSON Schema 与 `MCC 5552` 冲正时效的精确真源。
  - **Bright Data**：适合抓取公开地图上的充电站分布点，但代理延迟高（P50 `1.9s–4.2s`），严禁放入拔枪毫秒级 `0420` 结算冲正热路径。

---

## 3. 🧭 直观可视化图解（Mermaid 决策树 + 路径对比 + 时序图）

### 3.1 架构师选型决策树（智能体车机充电 ISO 15118、OCMF 计量签名与 `$175` 预授权秒解冻）

```mermaid
flowchart TD
    A["智能体新能源车机充电启动与拔枪结算请求<br/>(批次金额 $380,000.00)"] --> B{"是否通过 ISO 15118 EMAID 证书认证<br/>且拔枪瞬间同步发送 0420 解冻 $175 差额?"}
    B -- "否: 扫可疑外部静态二维码(Quishing 钓鱼)<br/>或拔枪未冲正锁死车主 $156.50 额度" --> C["🛑 HTTP 403 拦截<br/>QR_QUISHING_UNTRUSTED_OR_AFD_175USD_HOLD_UNREVERSED_BLOCKED (11ms)"]
    B -- "是: ISO 15118 证书握手且 0420 即刻解冻" --> D{"OCPI v2.2.1 CDR 是否附带电表硬件<br/>OCMF ECDSA 签名且占位费未超封顶上限?"}
    D -- "否: 无硬件签名的软件估算度数(违反 Eichrecht)<br/>或未发满电提醒暗扣天价占位费" --> E["🚨 HTTP 422 拦截<br/>UNSIGNED_OCMF_METER_DRIFT_OR_UNCAPPED_IDLE_FEE_REJECTED (14ms)"]
    D -- "是: OCMF 硬件签名有效且占位费合规" --> F["调用 Microsoft Web IQ /v3/browse<br/>核验 MCC 5552 充电专有清算规则与分时电价 (TOU) 备案"]
    F --> G{"满足 MCC 5552 实时通知规范<br/>且峰谷电价切换时间戳精确?"}
    G -- "否: 峰谷电价跨时段多算钱或缺失 MCC 5552 标识" --> H["🛑 HTTP 451 合规冻结<br/>TOU_TARIFF_BOUNDARY_OR_MCC5552_RULE_HOLD (280ms)"]
    G -- "是: 分时电价与卡组规范全部达标" --> I{"是否启用车机智能错峰谷电导航 +<br/>MCC 5552 小额免密低交换费路由?"}
    I -- "是: 省下谷电差价与通道费 $30,400" --> J["🧑‍⚖️ HTTP 409 财务确认<br/>EV_ISO15118_TOU_ARBITRAGE_AND_MCC5552_SAVINGS_CONFIRM"]
    I -- "否: 标准即插即充秒级清算解冻" --> K["✅ HTTP 200 自动放行<br/>VERIFIED_EV_CHARGING_OCPI_ISO15118_SETTLED (10ms)"]
```

### 3.2 传统扫码钓鱼 + `$175` 锁卡一周（反模式）vs ISO 15118 即插即充 + `0420` 秒解冻网关对比

```mermaid
flowchart LR
    subgraph AntiPattern["❌ 传统反模式：扫桩体假二维码被盗刷 + 充 $18 电被锁死 $175 一周"]
        A1["黑产在桩体贴假二维码 (Quishing)<br/>车主扫码输入卡号瞬间被盗刷"] --> A2["插枪冻结 $175 预授权，充完 $18.50 拔枪<br/>未发 0420 冲正导致 $156.50 死锁 7 天"]
        A2 --> A3["断网后后台用功率×时间胡乱估度数<br/>违反 Eichrecht 计量法遭拒付秒败诉!"]
    end

    subgraph BestPractice["✅ 推荐架构：ISO 15118 即插即充 + OCMF 电表签名 + 0420 秒解冻网关"]
        B1["插枪通过充电线 PLC 交换 EMAID 证书<br/>零手机扫码 100% 免疫假二维码钓鱼"] --> B2["拔枪瞬间凭直流电表 OCMF 硬件签名<br/>精确捕获 $18.50 并 0420 秒解冻 $156.50"]
        B2 --> B3["满电 5 分钟宽限期强提醒 + 占位费封顶<br/>车机智能引导谷电充电立省 30% 电费!"]
    end
```

### 3.3 端到端时序图（插枪 ISO 15118 握手 → `$175` 预授权 → 电表 OCMF 签名 → 拔枪 `0420` 秒解冻）

```mermaid
sequenceDiagram
    autonumber
    participant EV as 智能新能源车机 (TPM EMAID 证书)
    participant Charger as 直流超充桩 (认证 OCMF 电表)
    participant Gate as CPO/eMSP OCPI v2.2.1 结算网关
    participant WebIQ as Microsoft Web IQ (/v3/browse)
    participant Issuer as 发卡行 (MCC 5552 AFD Switch)

    EV->>Charger: 1. 插入充电枪：通过 PLC 电力线发起 ISO 15118-20 TLS 握手并出示 EMAID 证书
    Charger->>Gate: 2. 验证 V2G PKI 证书链有效 (11ms 阻断未签名扫码钓鱼请求)
    Gate->>Issuer: 3. 发起 MCC 5552 预估预授权 $175.00 (批次总额 $380,000.00)
    Note over EV,Charger: 充入 42.00 kWh 电量，车主拔枪结束充电 (Session_Stop)
    Charger->>Gate: 4. 生成带直流电表 ECDSA 硬件签名的 OCMF 报文与 OCPI CDR (应付 $18.50)
    Gate->>Gate: 5. 校验 OCMF 起止读数签名有效 & 占位费合规 (14ms)
    Gate->>WebIQ: 6. /v3/browse 核验分时电价 (TOU) 跨整点切分规则与 MCC 5552 冲正规范
    WebIQ-->>Gate: 280ms 确认计量与分时费率合规 (official_doc_snapshot)
    Gate->>Issuer: 7. 签发 agentic_ev_charging_ocpi_iso15118_afd_mandate_...：Capture $18.50 + 0420 冲正 $156.50
    Issuer-->>EV: 车载大屏秒级弹窗：“实扣 $18.50，预冻 $156.50 已即刻解冻”!
```

---

## 4. 📊 架构师选型决策矩阵（Architecture Selection Matrix）

| 评估维度 | 方案 A：桩体贴静态二维码 H5 支付 + 不发冲正（反模式） | 方案 B：强制要求车主先往每个不同品牌 App 充值 `$50` 余额 | 方案 C：ISO 15118 即插即充 + OCMF 电表签名 + `0420` 秒冲正（推荐） |
| :--- | :--- | :--- | :--- |
| **防户外假二维码贴纸钓鱼（Quishing）** | ❌ **0% 防御（贴纸一盖即中招，欧美高发诈骗案）** | ⚠️ 首次下载时仍易扫假码 | ✅ **100% 物理免疫（走充电枪铜线 PLC 硬件证书握手，无需扫码）** |
| **`$125–$175` 预授权差额解冻耗时** | ❌ **5–10 个工作日**（车主卡被锁死无法再次充电） | N/A（但沉淀资金退余额难） | ✅ **`<3 秒` 即刻解冻（拔枪同事务强制发送 `ISO 8583 0420` 冲正）** |
| **德国 `Eichrecht` / 美国 CTEP 计量合规** | ❌ **违规（无电表硬件签名，软件估数可被全额拒付）** | ❌ 同样缺乏硬件防篡改签名 | ✅ **100% 法定合规（逐单绑定直流电表芯片 `OCMF` ECDSA 签名）** |
| **补能体验与漫游跨网通刷转化率** | ⚠️ 需掏手机扫码填卡号（雨雪天极不便） | ❌ **极差（车主手机里被迫装 15 个充电 App）** | ✅ **极致丝滑（插枪 2 秒启动，拔枪自动扣款解冻）** |
| **适用场景（Good Fit vs Not For）** | ⛔ **严禁用于现代公共直流快充与高速服务区** | 仅适合极封闭的单位内部慢充桩 | ✅ **所有智能电动汽车 OEM、公共超充网（CPO）与 Robotaxi 车队必选** |

---

## 5. 🧪 定量实测与 7-Card 4:5 评测报告摘要（Benchmark & Provenance）

我们在 `lab/webiq_commerce_demo.py` 中内置了确定性策略评估器 `evaluate_agentic_ev_charging_ocpi_policy()`，对 `$380,000.00` 的智能体新能源车机充电与漫游清算批次进行了 5 类场景的边界验证（数据来源标注遵循零虚构原则：`synthetic_policy`、`deterministic_offline_simulation`、`official_doc_snapshot`）：

| 场景编号与名称 | 输入条件与防线触发条件 | 网关 HTTP 状态码与动作 | 实测延迟 | 净保全/节省金额 | Provenance 标签 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Case 1 (`evc_commit_ok`)** | ISO 15118 `EMAID` 证书通过 + 拔枪 `0420` 秒解冻 `$175` 预授权 + `OCMF` 电表签名有效 | `HTTP 200` · `Act automatically` | `10ms` | 秒级结算解冻 `$380,000.00` | `deterministic_offline_simulation` |
| **Case 2 (`evc_qsh_403`)** | 检出未签名外部二维码钓鱼请求（Quishing）或拔枪结单未发送 `0420` 解冻剩余 `$156.50` 预授权 | `HTTP 403` · `Send to a human` | `11ms` | 拦截 `$380,000.00` 钓鱼盗刷与锁卡 | `synthetic_policy` |
| **Case 3 (`evc_ocm_422`)** | `OCPI CDR` 账单缺失直流电表 `OCMF` 硬件签名（软件估算度数）或未发满电提醒强扣天价占位费 | `HTTP 422` · `Send to a human` | `14ms` | 阻断违反计量法的无效出账 | `deterministic_offline_simulation` |
| **Case 4 (`evc_tou_451`)** | Web IQ `/v3/browse` 检出跨整点峰谷分时电价（TOU）切分错误或违反 `MCC 5552` 披露规程 | `HTTP 451` · `Send to a human` | `280ms` | 冻结错算分时电价批次 | `official_doc_snapshot` |
| **Case 5 (`evc_sav_409`)** | Web IQ 启用车机错峰谷电导航套利 + `MCC 5552` 小额充电定制低交换费率并阻断钓鱼拒付 | `HTTP 409` · `Confirm` | `245ms` | **单批立省 `$30,400.00`**（净补能结算成本优化至 `$349,600.00`） | `official_doc_snapshot` |

### 7-Card 4:5 视觉评测报告核心卡片速览
- **Card 1 (`1 / 7` · `HANDS-ON · EV CHARGING ISO 15118 & OCMF GATE`)**：展示 `$380,000.00` 车机充电批次在 `10ms` 内完成 `EMAID` 证书验签、`OCMF` 计量核对与 `0420` 预授权秒级解冻。
- **Card 2 (`2 / 7` · `SCENARIO: ANTI-QUISHING & $175 HOLD RELEASE`)**：量化展示 `11ms` 拦截假二维码钓鱼与未冲正预授权锁卡（`HTTP 403`），以及 `14ms` 拦截无 `OCMF` 硬件签名的软件估算账单（`HTTP 422`）。
- **Card 3 (`3 / 7` · `WHAT I TESTED`)**：5 组车机补能与漫游清算矩阵全绿通过（`HTTP 200 / 403 / 422 / 451 / 409`）。
- **Card 4 (`4 / 7` · `UNDER THE HOOD`)**：展示 `agentic_ev_charging_ocpi_iso15118_afd_mandate_...` 的 JSON 契约结构（含 `iso15118_emaid_cert_verified: true`、`ocmf_ecdsa_signature_valid: true`、`preauth_175usd_0420_reversed_cents: 15650`、`mcc_code: "5552"`）。
- **Card 5 (`5 / 7` · `ROBUSTNESS CHECK`)**：验证当充电过程跨越尖峰（Peak）与低谷（Off-Peak）两个电价时段时，基于 `OCMF` 中间打点读数的分段定点数计费 100% 精确守恒。
- **Card 6 (`6 / 7` · `LATENCY`)**：对比拔枪同事务自动发送 `0420` 解冻（`<3秒` 到账）与传统不发冲正等待发卡行自然过期（7–10 天）。
- **Card 7 (`7 / 7` · `MY TAKE`)**：明确 **✅ Good fit**（智能电动汽车座舱支付、高速超充网、Robotaxi 自动补能车队）与 **⛔ Not for**（禁用于户外无防伪静态二维码收款或拔枪不发送 `0420` 差额冲正的系统）。

---

## 6. 🛠️ 生产上线快速核验清单（Production Readiness Checklist）

- [ ] **全面启用 `ISO 15118-2 / 15118-20` 即插即充（`EMAID` X.509 双向证书认证）**：优先通过充电电缆 PLC 建立 TLS 握手完成车主账户鉴权；若需保留屏幕扫码，必须使用桩端屏幕每 30 秒动态刷新的带签名挑战码二维码，严禁在桩体贴静态收款二维码（防 Quishing 覆盖）。
- [ ] **`MCC 5552` 拔枪结单瞬间强制触发 `ISO 8583 0420` 部分预授权冲正**：当充电结束（`Session_Stop`）生成实际消费金额（如 `$18.50`）后，网关必须在 `Capture` 同一事务中立即向发卡行发送 `0420` 冲正报文，3 秒内解冻 `$175.00` 初始预授权中的剩余 `$156.50` 额度。
- [ ] **强制校验直流电表硬件私钥签名的 `OCMF（Open Charge Metering Format）` 数据块**：`OCPI v2.2.1 CDR` 结算详单必须包含电表芯片生成的 `OCMF` ECDSA 签名（锁死起止 Wh 读数与时间戳），严禁使用软件定时器估算度数出账（满足德国 `Eichrecht` 与加州 CTEP 规范）。
- [ ] **跨时段分时电价（TOU Tariff）打点切分与超时占位费（Idle Fee）宽限期门禁**：当充电跨越峰谷电价分界点时，必须读取电表在整点分界时刻的签名读数分段计费；收取占位费前必须提前 5 分钟向车机与手机推送满电挪车提醒并设置单次封顶上限。
- [ ] **Microsoft Web IQ 国际漫游 `OCPI v2.2.1` 标准与 `MCC 5552` 定制费率核查**：通过 Web IQ `/v3/browse` 持续核验卡组织针对小额充电交易的优惠交换费率与计量法规更新。
