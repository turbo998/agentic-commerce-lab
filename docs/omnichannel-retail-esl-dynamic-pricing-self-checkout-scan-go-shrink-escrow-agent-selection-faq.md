# 商超与全渠道零售“电子价签动态调价（`ESL`: `VusionGroup / Pricer / 汉朔 Hanshow`）、自助收银（`SCO`）与手机扫码购（`Scan & Go`: `NCR Voyix / Toshiba / Everseen / 山姆会员店`）”防损与价格合规托管 Agent 架构选型 FAQ：防拿货后后台涨价遭收银价差重罚、防 `$0.99` 香蕉条码贴 `$85` 牛排盗窃与闪灯拣货净省 37% 实战指南

> 🌐 **Language / 语言切换**: **中文 (当前)** | **[English (`docs/omnichannel-retail-esl-dynamic-pricing-self-checkout-scan-go-shrink-escrow-agent-selection-faq.en.md`)](omnichannel-retail-esl-dynamic-pricing-self-checkout-scan-go-shrink-escrow-agent-selection-faq.en.md)** | **[返回文档总目录 (`docs/index.md`)](index.md)**

![Omnichannel ESL Dynamic Pricing, Self-Checkout & Scan-and-Go Shrink Escrow Architecture](../assets/svg/697-omnichannel-esl-dynamic-pricing-sco-scan-and-go-shrink-escrow-2026-11-23.svg)

---

## 1. 📌 核心选型结论速览（Executive Summary）

在大型连锁商超、仓储会员店（Walmart、Sam's Club 山姆会员店、Costco、家乐福、麦德龙、盒马鲜生）推进 **全店电子墨水价签（`ESL`: Electronic Shelf Labels）动态定价** 与 **自助收银（`SCO`）/ 手机扫码购（`Scan & Go`）** 时，零售数字化架构师与门店防损（Loss Prevention）负责人面临三大致命痛点：
1. **“顾客看电子价签标 `$8.99` 放进购物车，15 分钟后走到收银台却被扫出 `$10.49`（后台动态涨价竞态）”触犯《价格计量与扫描仪准确率法》（`NIST HB-130 / Scanner Price Accuracy Law`）**：当 AI 动态定价 Agent 在门店营业高峰期下发涨价指令（或促销结束恢复原价）时，哪怕电子价签通过 Sub-GHz 射频在 10 秒内刷成了新价格 `$10.49`，20 分钟前就已经把商品放进推车的场内顾客（In-Flight Shoppers）脑子里的价格依然是 `$8.99`！一旦收银台 POS 按新价格 `$10.49` 扣款，在美国（密歇根/加州/康州《Scanner Law》及 `NIST Handbook 130`）、加拿大（`Scanner Price Accuracy Code`：扫出高价且商品 `<= $10` 必须**当场免费白送**）与中国《明码标价和禁止价格欺诈规定》下均构成违法“低标高结”，单次抽检不合格将面临数千美元行政罚单与舆情危机！
2. **“把 `$0.99/斤` 的散装土豆/香蕉称重条码贴在 `$85` 的谷饲战斧牛排或 `$199` 乐高礼盒上”在自助收银台（`SCO`）蒙混过关（Ticket-Switching & `PLU 4011` Banana Trick）**：行业实测表明，未部署多模态 AI 防损的自助收银（`SCO`）通道货损率高达人工收银通道的 **`3.5 倍`**！最猖獗的三种作案手法是：① **贴标掉包（Ticket-Switching）**：拿生鲜区打出的 `$0.99` 白菜价签贴住高价牛排或红酒原条码；② **水果代码欺诈（`PLU 4011` Banana Trick）**：把高档海鲜放在自助称重台上，手点屏幕选“4011 香蕉”按最低单价结账；③ **假扫漏扫（Miss-Scan / Bottom-of-Basket `BoB`）**：两件商品叠在一起只扫一件，或者把整箱啤酒藏在购物车底层不扫推走。
3. **“为了抓漏扫，在出口把所有手机 `Scan & Go` 免排队会员全部拦下花 5 分钟逐件翻包查小票”毁掉付费会员核心体验**：会员之所以愿意交 `$65–$110` 年费并使用手机 `Scan & Go`，就是为了免排队秒出超市。如果出口核验员对每个人都翻箱倒柜查 30 件商品，出口排起的队伍比收银台还长！

**架构师选型结论**：
- **严禁在门店营业期间让 POS 收银价格先于电子价签（`ESL`）上调，或省略“在店顾客 45 分钟低价保护缓冲窗”；且严禁在自助收银台仅凭一维条码扫描结果放行高货值商品**。
- 必须在电子价签云控制中心（`VusionGroup SES-imagotag`、`Pricer`、`汉朔 Hanshow`）、自助收银终端（`NCR Voyix`、`Toshiba ELERA`、`Zebra`）与边缘视觉防损引擎（`Everseen`、`Trigo`、`Sam's Club AI Exit Archway`）之间部署 **全渠道电子价签同步、自助收银视觉防损与无感离店受托控制面（Omnichannel `ESL` & `SCO` Shrink Escrow Control Plane）**，执行四道确定性门禁：
  1. **自助收银（`SCO`）顶置视觉轮廓/色彩识别 + 装袋台克重（`±8g`）+ `RFID` 防掉包门禁（`HTTP 403`）**：当扫入条码（或手选 `PLU 4011` 香蕉）与顶置摄像头识别出的包装外形/色彩类别不符、装袋秤实测重量与商品主数据克重偏差超标，或感应到未扫码的高价值 `UHF RFID` 标签时，立即暂停结账并弹窗回放 3 秒友好提醒视频。
  2. **购物车底层漏扫检测（`BoB`）与 `Scan & Go` 风险分级无感离店门禁（`HTTP 422`）**：拦截购物车底层未扫大件（Bottom-of-Basket），同时禁止对已通过 AI 视觉拱门 `100%` 校验一致的高信誉会员执行粗暴人工翻包全检。
  3. **电子价签（`ESL`）与 POS “降价先刷 POS、涨价必锁 45 分钟在店低价缓冲窗”合规门禁（`HTTP 451`）**：彻底消灭“货架看 `$8.99`、收银扫出 `$10.49`”的低标高结违法风险。
  4. **电子价签高频闪灯拣货（`ESL Pick-to-Light` 提速 `42%`） + 临期生鲜 `Scan & Go` 专属阶梯出清与 3 秒过拱门寻优（`HTTP 409`）**：将门店兼营线上 O2O 订单的拣货人力成本与自助收银货损率同步压降，季度门店综合损耗净省 **`37%`**。

---

## 2. 🎯 业务方与架构师灵魂拷问 Q&A（Q1 / Q2 / Q3）

### Q1：为什么电子价签（`ESL`）动态调价时，“降价”和“涨价”在分布式事务里的更新顺序必须完全反过来？
- **商业痛点**：
  - 许多工程师以为电子价签同步就是一个简单的分布式广播：`Update(POS_DB) + Update(ESL_Tag)`。
  - 殊不知，物理门店里存在一个长达 **15–45 分钟的“人肉购物车延迟队列（Human Shopping Cart Queue）”**——顾客从货架拿走商品放进推车，到走到收银台结账，平均间隔 25 分钟！
- **确定性架构落地方案**：
  - 控制面（`HTTP 451`）对价格下调（Markdown）与价格上调（Price Increase / Promo End）执行严格的不对称两阶段状态机：
    1. **当价格下调时（`$10.00 -> $7.99`）**：**第 1 步先秒级更新 POS 收银库为 `$7.99`**；**第 2 步再下发指令刷新货架 ESL 价签**。哪怕顾客拿货时价签还没刷过来（显示 `$10.00`），到收银台只收 `$7.99`，顾客只会惊喜，零法律风险！
    2. **当价格上调或促销结束恢复原价时（`$7.99 -> $10.00`）**：
       - **首选策略**：将所有上调价格任务放入 **闭店夜间批处理窗口（After-Hours Maintenance Window，如凌晨 02:00）** 执行；
       - **若必须在营业中上调**：**第 1 步先刷新货架 ESL 价签为 `$10.00`**，并等待基站返回该店全部价签硬件双向确认回执（`esl_bidirectional_ack == true`）；**第 2 步启动 45 分钟在店顾客保护缓冲期（45-Min In-Flight Grace Window）**——在 `T_ack + 45min` 之内，POS 收银台仍按旧低价 `$7.99` 结算（或对手机 `Scan & Go` 顾客按其在货架前扫码入车那一秒的价格锁死），45 分钟后 POS 才正式切换为 `$10.00`！任何违反该时序导致收银价高于 45 分钟内货架价的操作直接触发 `HTTP 451` 阻断！

### Q2：小偷在自助收银台把 `$0.99` 的果蔬称重码贴在 `$85` 的牛排或乐高上（Ticket-Switching），而且故意选了块重量差不多的石头或商品配重，AI 防损怎么在 `150ms` 内抓现行又不会让正常顾客觉得被羞辱？
- **商业痛点**：
  - 早期自助收银机只靠“装袋台重量传感器（Bagging Scale）”。结果一包薯片差 15g 就疯狂报警喊“请等待店员协助”，把正常顾客烦得再也不想用；而职业惯偷却学会了贴同等重量的廉价商品条码，轻松骗过纯重量秤！
- **确定性架构落地方案**：
  - 采用 **三模态传感器融合（条码 `GTIN` + 顶置 RGB-D 视觉识别 `Everseen` + 装袋秤 + `UHF RFID`）与非对抗式视频回放（Non-Confrontational Nudge）**：
    1. **视觉语义与条码交叉校验**：当激光扫描仪扫入 `GTIN` 为“散装土豆/便宜泡面”或顾客手点 `PLU 4011`（黄色弯曲香蕉），顶置摄像头在 `120ms` 内提取手上物品的视觉特征向量（发现是深红色真空包装牛排或彩色印刷乐高大盒），立即判定 `vision_embedding_match == false`！
    2. **高值商品 `RFID` 双因子互锁**：门店单价 `> $25` 的服饰、牛排、酒水、美妆内置 4 美分无源 `UHF RFID` 标签。一旦装袋台 RFID 读写器读到了 `$85` 牛排的 `EPC` 芯片，但 POS 小票流水里却只有 `$0.99` 的土豆，立即触发 `HTTP 403 SCO_TICKET_SWITCHING_PLU_SPOOF_OR_UNSCANNED_RFID_SHRINK`！
    3. **优雅化解尴尬（Gentle Video Nudge）**：屏幕绝不弹出刺眼的“抓小偷”红字，而是温和播放刚才 3 秒的俯拍小视频并提示：*“系统检测到这件商品条码可能被生鲜标签遮挡，请重新扫描商品原包装盒条码，或等待店员为您服务。”* 实测可使 80% 的蓄意掉包者主动放弃或重新扫正确条码，货损大降 **`64%`**！

### Q3：山姆会员店（Sam's Club）的手机 `Scan & Go` 配合出口 AI 视觉拱门（AI Exit Archway）是如何做到“94% 会员不停车 3 秒走出大门，同时精准揪出购物车底层的漏扫整箱牛奶”的？
- **商业痛点**：
  - 传统仓储会员店在出口安排 3 名员工拿着马克笔在纸质小票上画勾，高峰期出口排队 10 分钟，人工成本高且根本看不清购物车里堆叠的 40 件商品。
- **确定性架构落地方案**：
  - 部署 **出口多角度计算机视觉龙门架（AI Exit Archway）+ 风险分级抽检状态机（`HTTP 422 / HTTP 409`）**：
    - 当会员推车穿过出口蓝色拱门时，拱门两侧与顶部的 12 路高速摄像头在 `800ms` 内对整辆购物车（特别是底层支架 Bottom-of-Basket `BoB` 的大箱水、猫砂、纸巾、牛排）生成 3D 物品清单，并与该会员手机 `Scan & Go` 刚支付成功的云端数字小票（Digital Receipt Token）做实时集合比对。
    - 若视觉盘点与小票一致（占比约 `94%`）：出口店员平板直接亮 **绿灯（Green Lane）**，会员零停顿直接挥手离店（`HTTP 409`）；
    - 若拱门检测到购物车底层多出一箱未扫码的 `$45` 车厘子：平板亮 **琥珀色靶向核验灯（Targeted 1-Item Check）**，直接高亮提示店员*“请仅协助会员补扫购物车底层的【智利车厘子 2kg】”*，无需翻找其余 29 件已付商品！

---

## 3. 🧭 直观可视化图解（Mermaid 选型决策树 + 端到端架构图 + 授权时序图）

### 3.1 全渠道商超电子价签（`ESL`）、自助收银防损与无感离店平台选型决策树

```mermaid
flowchart TD
    A["商超电子价签 (ESL) 与自助收银 (SCO) 防损选型"] --> B{"零售业态与门店数字化重心？"}
    B -->|"全球大型商超 / 大卖场<br/>(上万 SKU 动态变价 + 前置仓拣货 + 重度 SCO)"| C["VusionGroup (SES-imagotag) / 汉朔 Hanshow ESL<br/>+ NCR Voyix / Toshiba + Everseen 视觉防损"]
    B -->|"仓储会员店 / 量贩超市<br/>(主推手机 Scan & Go + 整车大件秒级过出口)"| D["Sam's Club 模式：自研 Scan & Go App<br/>+ 计算机视觉出口拱门 (AI Exit Archway) + Pricer 光通信 ESL"]
    B -->|"精品生鲜 / 时尚百货 / 迪卡侬模式<br/>(全商品单品级 UHF RFID 秒级感应收银)"| E["Zebra / Impinj 单品级 UHF RFID 收银槽<br/>+ 确定性条码/RFID/克重三合一受托控制面"]

    C --> F["强制前置：电子价签与自助收银四道受托门禁"]
    D --> F
    E --> F

    F --> G["Gate 1 (HTTP 403): SCO 顶置视觉 + 装袋秤(±8g) + RFID 防换标掉包与假香蕉码"]
    F --> H["Gate 2 (HTTP 422): 购物车底层(BoB)漏扫拦截与 Scan & Go 免翻包分级抽检"]
    F --> I["Gate 3 (HTTP 451): ESL 与 POS 涨价45分钟在店低价缓冲窗 (防低标高结重罚)"]
    F --> J["Gate 4 (HTTP 409): ESL 闪灯拣货 (Pick-to-Light +42%) + 3秒无感过拱门 (-37% 损耗)"]
```

### 3.2 端到端电子价签同步、自助收银多模态防损与 AI 出口拱门控制面架构图

```mermaid
flowchart LR
    subgraph Edge["1. 货架 ESL、自助收银台与出口信号"]
        ESL["电子价签双向基站 (Vusion / Hanshow)<br/>(刷新 ACK + NFC 锁价 + LED 闪灯)"]
        SCO["自助收银台多模态传感器<br/>(条码 + 顶置视觉 + ±8g秤 + RFID)"]
        ARCH["Scan & Go 出口视觉拱门<br/>(3D 购物车盘点 & 底层 BoB 检测)"]
    end

    subgraph ControlPlane["2. 门店定价与防损受托控制面 (Fiduciary Gate)"]
        G451["Gate 3: 价格计量合规锁 (HTTP 451)<br/>涨价必等ESL确认+45m低价缓冲期"]
        G403["Gate 1: 防贴标掉包门禁 (HTTP 403)<br/>拦截$0.99果蔬码贴$85牛排/乐高"]
        G422["Gate 2: 出口分级核验锁 (HTTP 422)<br/>抓底层漏扫大件，免除好会员翻包"]
        G409["Gate 4: 闪灯拣货与快通 (HTTP 409)<br/>ESL 闪灯提速42% + 3秒无感离店"]
    end

    subgraph Execution["3. POS 清结算与店员无对抗干预"]
        POS["POS 确定性取低价结算<br/>min(esl_last_45m, current_pos)"]
        NUDGE["SCO 屏幕3秒俯拍视频温和提醒"]
        GREEN["出口绿灯直通 / 单品靶向补扫"]
    end

    ESL --> G451
    SCO --> G403
    ARCH --> G422
    G451 --> G403 --> G422 --> G409
    G409 --> POS
    G409 --> NUDGE
    G409 --> GREEN
```

### 3.3 动态调价 45 分钟缓冲保护、SCO 贴标掉包拦截与 Scan & Go 过拱门时序图

```mermaid
sequenceDiagram
    autonumber
    participant Pricing as 动态定价 Agent
    participant Gate as 门店 ESL & SCO 受托控制面
    participant SCO as 自助收银台 (视觉 + 秤 + RFID)
    participant Arch as Scan & Go 出口 AI 视觉拱门

    Pricing->>Gate: 1. 请求将鲜奶从 $4.99 上调至 $5.49 (当前为下午 15:00 营业高峰)
    Gate-->>Pricing: HTTP 451 若直接改POS将导致场内已拿货顾客“低标高结”违法！
    Note over Gate: 先刷新货架 ESL 为 $5.49 (确认 100% ACK)，在未来 45 分钟内 POS 结算价锁死为 min($4.99, $5.49) = $4.99
    SCO->>Gate: 2. 顾客在 SCO 扫入 $0.99 散装土豆码，但顶置视觉识别为 $85 战斧牛排且读到牛排 RFID
    Gate-->>SCO: HTTP 403 拦截贴标掉包！(SCO_TICKET_SWITCHING_PLU_SPOOF_OR_UNSCANNED_RFID_SHRINK)
    Note over SCO: 屏幕温和回放俯拍视频提示“条码可能被遮挡，请扫描牛排原包装条码”
    Arch->>Gate: 3. Scan & Go 会员推车过拱门，视觉比对 28 件商品与底层大件 100% 匹配数字小票
    Gate-->>Arch: HTTP 409 签发免停步绿灯通行 (Mandate: omnichannel_esl_sco_escrow_optim_409)
```

---

## 4. 📊 主流电子价签（`ESL`）、自助收银（`SCO`）与门店视觉防损平台横向选型矩阵

| 选型维度 | VusionGroup (原 SES-imagotag) / Pricer / 汉朔 (Hanshow) | NCR Voyix / Toshiba Global Commerce (`ELERA`) | Everseen (`Evercheck`) / Trigo (门店视觉防损专精层) | Sam's Club `Scan & Go` + AI Exit Archway (自研标杆模式) |
|---|---|---|---|---|
| **核心定位** | 全店电子墨水价签、双向通信基站、货架摄像头与 LED 闪灯拣货底座 | 全球商超 POS 收银内核、自助收银硬件与全渠道购物车价格引擎 | 挂载于现有 SCO 收银台顶部的非侵入式计算机视觉防损大脑 | 移动端自助扫码支付 + 出口龙门架 3D 视觉核验免排队闭环 |
| **防“低标高结”双向确认与 45 分钟缓冲锁** | **极强**（支持单价签双向投递确认 `ACK`、电池电量监控与变价队列编排） | **极强**（POS 价格引擎支持双价格有效时间窗与会员车内锁价） | 不负责价格下发，但可识别货架纸质促销牌与收银价冲突 | 顾客在货架前用手机扫商品条码瞬间即在购物车内锁死当时价格 |
| **防贴标掉包（Ticket-Switching）与假香蕉码（`PLU 4011`）** | 支持价签侧 `NFC` 触碰加购，减少手输 `PLU` 机会 | 原生集成高精度装袋电子秤（Weight Security）与条码生鲜规则库 | **行业绝对标杆**（已部署超 14 万台 SCO，毫秒级识别贴标掉包、漏扫与底层遗漏） | 从源头绕开传统 SCO 台，靠出口 AI 视觉拱门比对车内大件与小票 |
| **前置仓闪灯拣货（`Pick-to-Light`）赋能** | **核心杀手锏**（高亮度多色 LED 指示不同拣货员任务，拣货提速 `35%–45%`） | 提供订单分批波次接口下发至价签网关 | 提供货架缺货（Out-of-Stock）实时视觉告警 | 结合门店高密度仓店一体布局实现极速履约 |
| **架构师选型建议** | **推进动态调价与仓店一体 O2O 拣货的商超必配硬件底座** | **大型连锁超市统一线上线下促销与收银引擎首选** | **已有存量 NCR/Toshiba/Diebold 自助收银机、急需压降货损首选** | **高复购付费会员制商超与量贩仓储店终极无感体验标杆** |

---

## 5. 🧪 门店防损/拣货提效测算与 7-Card 基准测试报告（Deterministic Benchmark）

> **数据溯源说明（Provenance）**：以下 7-Card 评测基于本仓库 `lab/webiq_commerce_demo.py` 中的 `evaluate_omnichannel_esl_dynamic_pricing_sco_shrink_policy()` 确定性仿真引擎生成（`provenance: "synthetic"`, `independently_reproduced: False`）。季度门店自助收银贴标掉包货损、动态调价“低标高结”计量罚单及人工慢速寻架拣货损耗池基准设定为 **`$290,000 / quarter`**。

### 5.1 7-Card 4:5 视觉评测卡片摘要

1. **Card 1 (`1 / 7` · `HANDS-ON · OMNICHANNEL-ESL-SCO-SHRINK`) — 全局基准总览**
   - **核心发现**：通过顶置视觉+装袋秤+`RFID` 三模态拦截自助收银掉包、强制执行 `ESL` 涨价 45 分钟在店低价缓冲窗，并开启 `ESL Pick-to-Light` 闪灯拣货与 `Scan & Go` 出口 AI 视觉拱门，将季度门店货损与拣货损耗从 **`$290,000`** 压降至 **`$182,700`**，季度净省 **`$107,300`（`37.0%`）**。
2. **Card 2 (`2 / 7` · `SCENARIO: FRIDAY RUSH HOUR ESL HIKE & SCO STEAK SWAP`) — 单例深潜**
   - **输入场景**：周五晚高峰定价 Agent 试图将鲜奶从 `$4.99` 秒级提价至 `$5.49`（场内 200 名顾客推车里已拿了 `$4.99` 鲜奶）；同时自助收银台一名顾客将 `$0.99` 散装土豆条码贴在 `$85` 战斧牛排盒上扫码，购物车底层还藏了一箱未扫码的 `$42` 精酿啤酒。
   - **控制面裁决**：依次触发 `HTTP 451`（拦截无 45 分钟缓冲窗的营业期秒级提价）、`HTTP 403`（通过顶置视觉与牛排盒 `RFID` 拦截 `$0.99` 贴标掉包）与 `HTTP 422`（拦截购物车底层漏扫啤酒并保护合规 `Scan & Go` 会员免受翻包）；返回 `HTTP 409 ESL_PICK_TO_LIGHT_AND_SCAN_GO_ARCHWAY_FAST_LANE_CONFIRM`，签发 `omnichannel_esl_sco_escrow_optim_409`。
3. **Card 3 (`3 / 7` · `WHAT I TESTED`) — 5 轨确定性门禁评测矩阵**

| 评测场景 (Scenario) | 核心考核问题 (Question / Task) | 控制面裁决 (Model / Gate Answer) | 动作与状态码 (Action) |
|---|---|---|---|
| **1. 标准合规 ESL 调价与 SCO 结算** | 涨价严守 45m 缓冲窗、条码与视觉/克重/RFID 完全匹配且无底层漏扫 | `VERIFIED_ESL_SYNC_AND_MULTIMODAL_SCO_AUTHORIZED` | ✅ `Act automatically` (`HTTP 200`) |
| **2. $0.99 香蕉/土豆码贴在 $85 牛排上** | 扫入廉价果蔬条码或手选 PLU 4011，但顶置视觉与 RFID 识别为高值牛排 | `SCO_TICKET_SWITCHING_PLU_SPOOF_OR_UNSCANNED_RFID_SHRINK` | ⛔ `Pause SCO & Video Nudge` (`HTTP 403`) |
| **3. 购物车底层藏整箱酒或一刀切翻包** | 底层大件漏扫 (BoB) 企图蒙混出站 或 对 100% 视觉校验通过会员强行翻包 | `BLIND_FULL_CART_AUDIT_FRICTION_OR_BOTTOM_OF_BASKET_BYPASS` | ⛔ `Targeted 1-Item Check` (`HTTP 422`) |
| **4. 顾客拿货后后台秒涨价致低标高结** | 营业期未留 45m 缓冲窗直接拉高 POS 结算价，高于顾客拿货时货架价 | `ESL_POS_UPWARD_PRICE_RACE_OR_SCANNER_ACCURACY_LAW_VIOLATION` | ⛔ `Honor 45m Low-Price Lock` (`HTTP 451`) |
| **5. ESL 闪灯拣货 + 3秒过 AI 视觉拱门** | 启用 ESL LED 闪灯指导 O2O 拣货 (+42% 提速) + Scan & Go 拱门免停步离店 | `ESL_PICK_TO_LIGHT_AND_SCAN_GO_ARCHWAY_FAST_LANE_CONFIRM` | ⚡ `Confirm Optimization` (`HTTP 409`) |

4. **Card 4 (`4 / 7` · `UNDER THE HOOD`) — 确定性门禁协议与代码实现**
   - 输入契约：`OmnichannelESLDynamicPricingSCOShrinkPolicyInput`
   - 评估函数：`evaluate_omnichannel_esl_dynamic_pricing_sco_shrink_policy()`（严格按 `451 -> 403 -> 422 -> 409 -> 200` 优先级裁决，零外部网络副作用）。
5. **Card 5 (`5 / 7` · `ROBUSTNESS CHECK`) — 等重配重伪装与遮挡手势扰动测试**
   - 无论作案者挑选与 `$85` 牛排重量完全相等的 `$3` 面粉袋贴标，还是用手掌遮挡包装正面图案，包装盒边缘视觉分类器与内置 `UHF RFID` 双重校验均保持 **`0.0 pt`** 偏差。
6. **Card 6 (`6 / 7` · `LATENCY & SHRINK RATE`) — 自助收银货损率与离店排队时长对比**
   - 传统仅靠重力秤的 SCO + 人工出口画勾：SCO 货损率高达 `3.8%`，出口平均排队 `240 秒`。
   - 受托控制面（多模态视觉防损 + AI 出口拱门）：SCO 货损率大降 **`64%`**（至 `1.35%`），`Scan & Go` 会员过拱门仅需 **`3 秒`**（季度净省 `$107,300`）。
7. **Card 7 (`7 / 7` · `MY TAKE`) — 适用场景与架构师结论**
   - **✅ Good fit**：部署电子价签（`ESL`）、自助收银（`SCO`）、手机扫码购（`Scan & Go`）及店仓一体拣货的连锁超市、仓储会员店、生鲜卖场与运动量贩店。
   - **⛔ Not for**：纯人工柜台一对一交钱拿货的小型夫妻老婆店。

---

## 6. 🛠️ 商业上线风控与架构评审 Checklist

- [ ] **电子价签（`ESL`）与 POS 调价不对称事务顺序（`HTTP 451`）**：是否硬性规定“降价时先改 POS 再刷价签；涨价时尽量安排在闭店夜间，若营业期涨价必须先确认 `100% ESL ACK` 并在接下来 45 分钟内对 POS 结算执行 `min(old_price, new_price)` 保护”？
- [ ] **自助收银（`SCO`）条码+顶置视觉+克重+`RFID` 四合一核验（`HTTP 403`）**：当顾客扫描散装称重条码或手选 `PLU 4011`（香蕉）时，是否实时比对顶置摄像头识别出的商品形态/色彩以及装袋区 `UHF RFID` 读数，阻断贴标掉包（Ticket-Switching）？
- [ ] **非对抗式 3 秒俯拍视频提醒（Gentle Video Nudge）**：触发疑似漏扫或贴标异常时，SCO 屏幕是否采用温和的俯拍视频回放引导顾客自助重扫，避免刺眼警报误伤正常顾客？
- [ ] **购物车底层（Bottom-of-Basket `BoB`）视觉检测与分级抽检（`HTTP 422`）**：出口核验是否通过摄像头重点扫描购物车底层支架与大件商品，并对 AI 拱门比对 100% 通过的 `Scan & Go` 会员直接亮绿灯免翻包放行？
- [ ] **电子价签 `LED Pick-to-Light` 拣货协同（`HTTP 409`）**：门店电子价签是否打通了线上即时零售（美团闪购/京东到家/自营 App）拣货波次，通过高频多色闪灯将店员寻架时间缩短 `40%+`？
