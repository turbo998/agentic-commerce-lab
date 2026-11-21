# 零售门店与全渠道移动收银（Omnichannel `SoftPOS / Tap to Pay on iPhone & Android`：Adyen Terminal API / Stripe Terminal / Square / Shopify POS）、防“内鬼店员无原单盲退（Unlinked Refund）把店里资金刷进自己银行卡”、防手输卡号（`Manual Keyed Entry`）盗刷降级与离线限额托管“防断网离线刷爆 $5,000 假卡与 `EMVCo PAR` 跨端识客净省 38%”Agent 架构选型 FAQ

> **语言 / Language**: **中文 (当前)** | **[English (`omnichannel-softpos-tap-to-pay-unlinked-refund-offline-emv-escrow-agent-selection-faq.en.md`)](omnichannel-softpos-tap-to-pay-unlinked-refund-offline-emv-escrow-agent-selection-faq.en.md)**  
> **返回总目录**: **[📚 中文总目录 (`docs/index.md`)](index.md)** | **[🚀 交互式实时工作台 (`live-demo.html`)](../live-demo.html)**  
> **赋能角色**: 全渠道零售品牌（旗舰店 / 快闪店 / 百货专柜）数字化副总裁、门店收银 POS 与支付风控总监、财务内控审计负责人、Cloud & AI Solution Architect  
> **关联架构图**: `assets/svg/655-omnichannel-softpos-tap-to-pay-unlinked-refund-escrow-2026-11-22.svg`

---

## ① 📌 核心选型结论速览（Executive Summary）

在现代精品零售门店、奢侈品专柜、网红快闪店（Pop-Up Store）与大型商超的“移动巡店收银（Line-Busting）”中，企业正大规模淘汰笨重昂贵的传统固定收银机（每台专用硬件成本 `$450–$800`），转而采用基于店员 iPhone 或安卓工牌手机 NFC 芯片的 **`SoftPOS（Tap to Pay on iPhone / Android，遵循 PCI MPoC 标准）`** 与云端一体机（`Adyen Terminal API`、`Stripe Terminal`、`Shopify POS`、`Square`）。然而在门店现场收银与退货中，零售商正面临三大资金流失黑洞：
1. **“全美零售业第一大内鬼职务侵占漏洞：无关联盲退（Unlinked / Standalone Terminal Refund Fraud）”**：传统 POS 终端允许收银员在没有调出原消费订单的情况下，直接在 POS 机上点击“独立退款（Standalone Refund） $850”，然后 **让收银员掏出自己的私人借记卡或 Apple Pay 在机器上‘滴’一下，把公司账户里的 `$850` 现金直接退进店员自己的腰包**！有的内鬼店员甚至在下班盘点前连续刷走 `$30,000` 跑路！
2. **“店员在 POS 机上手输 16 位卡号（Manual Keyed PAN Entry）引发 100% 盗刷拒付败诉 + 每笔多扣 `1.10%` 降级手续费”**：诈骗犯拿着一张磁条/芯片被故意刮花的假卡（或手机里存的一串盗刷卡号）进店买 `$3,000` 的包，忽悠店员说“芯片读不出来，麻烦你帮我在收银机键盘上手敲一下卡号和有效期吧！”——只要店员手输了卡号，这笔线下交易瞬间从 **`Card-Present（有卡芯片交易，手续费 1.65% 且银行承担盗刷责任）` 降级为 `Card-Not-Present MOTO（无卡手工输入，手续费暴涨至 2.75% + $0.10，且持卡人一旦发起 Visa 10.4 拒付，商家 100% 败诉财货两空）`**！
3. **“商场 Wi-Fi 断网时开启离线收单（Offline Store-and-Forward, `SAF`），被黑产团伙趁断网拿余额为 0 的废卡连刷 10 笔 `$800` 大单；或者店员使用越狱手机运行 SoftPOS 破坏 `PCI MPoC` 加密隔离”**！

**架构师选型结论**：直接采用 **“全面封禁无原单独立退货（Unlinked Refund）、强制 100% 原路关联网关流水号（`Referenced Refund by Original PaymentIntent / PSP Reference`）与 `EMVCo PAR` 原卡指纹校验门禁（HTTP 403）+ 硬件级锁死门店 POS 键盘手输卡号通道（`Disable Manual Keyed Entry`）、遇到芯片损坏自动改发手机 `3DS2` 扫码付链接门禁（HTTP 422）+ 断网离线收单（`Offline SAF`）单笔 `$150` / 同卡零连刷熔断锁与 `PCI MPoC` 硬件安全飞地（Secure Enclave）实时证明门禁（HTTP 451）+ `Tap to Pay` 移动消队、线上买线下退（`BORIS`）`PAR` 跨端秒认原卡与美国 `Durbin Reg II` 借记卡双网最优路由净省 38%（HTTP 409）”** 的全渠道门店收银托管架构。

![全渠道门店SoftPOS移动收银、防内鬼盲退与离线EMV风控托管架构图](../assets/svg/655-omnichannel-softpos-tap-to-pay-unlinked-refund-escrow-2026-11-22.svg)

---

## ② 🎯 业务方与架构师灵魂拷问（Q&A）

### Q1：为什么绝不能给门店收银机开放“刷卡退货（Unlinked / Blind Refund）”权限？如果顾客在官网用实体卡买衣服、到门店退货时却只带了手机 Apple Pay（设备虚拟卡号 `DPAN` 和实体卡号 `FPAN` 后四位完全不同），怎么在不开放盲退的前提下秒退？
- **业务痛点**：很多零售商之所以不敢关掉 POS 机的“刷任意卡退货（Unlinked Refund）”功能，是因为顾客线上买、线下退（`BORIS`）时，或者顾客当初刷的是 Apple Pay（虚拟尾号 `8821`）、今天拿来的是实体信用卡（印着尾号 `4019`），店员肉眼对不上后四位，就只能开启盲退让顾客重刷一张卡——结果给内鬼店员“刷自己卡偷钱”打开了大门！
- **架构护栏（`HTTP 403 UNLINKED_TERMINAL_REFUND_OR_PAR_MISMATCH_BLOCKED`）**：
  1. **100% 强制“基于原单唯一流水号的原路退回（Referenced Refund Only）”并永久焊死无原单盲退接口**：在 `Adyen / Stripe Terminal` 策略引擎中，直接将 `enable_standalone_refunds` 设为 `false`（任何企图不绑定原消费 `PaymentIntent_ID / pspReference` 发起的终端退款，或累计退款额 `> 原单实收余额` 的请求，立即返回 `HTTP 403` 硬阻断）！顾客到店退货根本不需要再掏卡出来刷，扫一下购物小票条码，资金 100% 从云端原路退回当初扣款的卡！
  2. **通过 `EMVCo Payment Account Reference (PAR)` 29 位跨端唯一账户号打通 Apple Pay `DPAN` 与实体卡 `FPAN`**：哪怕顾客弄丢了小票、只记得刷过手机 Apple Pay，店员让顾客在 SoftPOS 上轻触一下实体卡，系统读取底层不可篡改的 **`29 位 EMVCo PAR`（同一张银行卡无论生成多少个 Apple Pay / Google Pay 设备虚拟号，其底层 `PAR` 100% 相同）**，1 秒内在全渠道订单库里精准匹配出原网购订单并执行原路退回！

### Q2：顾客在店里结账时说“我忘带实体卡了，但我手机相册里有信用卡照片，你帮我把卡号敲进 POS 机里刷一下吧”，为什么店员一旦照做就是给公司埋雷？
- **业务痛点**：几乎 95% 的门店盗刷损失都来自“手输卡号（Manual Keyed Entry）”。因为手输卡号绕过了 EMV 芯片私钥签名（`ARQC Cryptogram`），不仅发卡行 100% 把盗刷责任判给商家，而且卡组织还要按无卡交易（CNP）多收 **`110 bps（1.10%）`** 的惩罚性交换费！
- **架构护栏（`HTTP 422 MANUAL_KEYED_PAN_FALLBACK_OR_INTERCHANGE_LEAK_BLOCK`）**：
  1. **全店终端彻底禁用键盘手输卡号（Disable Manual PAN Keyed Entry）**：所有门店 POS 与 SoftPOS 仅允许 **`EMV Contact Chip（插芯片）` 或 `EMV Contactless NFC（拍卡/Apple Pay/Google Pay）`** 产生动态密码学密文（`ARQC`）；任何试图调用键盘手输卡号（`pos_entry_mode = 01 / 79`）的请求直接触发 `HTTP 422` 拦截！
  2. **忘带卡/芯片消磁秒转“手机扫码 `3DS2 / Apple Pay` 远程支付链接（Pay-by-QR-Link）”**：如果真实顾客确实芯片损坏或只带了手机，收银屏幕自动生成一个 **3 分钟有效的加密付款二维码**，顾客用自己手机扫码并在本人手机上通过 **`Apple Pay` 或发卡行 `3DS 2.2` 人脸验证** 完成支付——既救活了这笔订单，又把盗刷拒付责任 100% 转移给发卡行（Liability Shift）！

### Q3：商场网络信号差或宽带被挖断时，门店开启“离线收单（Offline Store-and-Forward `SAF`）”怎么防止诈骗犯拿空卡连刷十几个 LV 包？店员用自己的手机当 `SoftPOS` 怎么保证卡号不被木马截获？
- **业务痛点**：离线收单（`SAF`）是在断网时先由 POS 机本地存下刷卡记录、等来网了再批量上传银行扣款。如果额度不设防，等晚上来网一上传，发现白天刷的 `$25,000` 全是余额不足（Declined），货早被拿走了！
- **架构护栏（`HTTP 451 OFFLINE_SAF_FLOOR_BREACH_OR_UNATTESTED_MPOC_HOLD` & `HTTP 409` 双卡 5G 切换 + 借记卡省费路由）**：
  1. **`PCI MPoC` 硬件安全飞地证明与断网离线 `SAF` 双重硬上限锁（`HTTP 451`）**：SoftPOS 每次启动必须通过 **`PCI MPoC (Mobile Payments on COTS)` 与 Apple/Google 硬件安全飞地（Secure Enclave / StrongBox）远程证明**；若检测到设备越狱/Root、调试端口开启或 `P2PE` 密钥过期，立即返回 `HTTP 451` 吊销收款权限！在极端断网转入离线 `SAF` 模式时，强制执行：**① 单笔离线金额 `<= $150`；② 同一张卡（按 `PAN Hash`）断网期间最多只准刷 `1` 笔；③ 单台设备离线未上传累计池 `<= $1,500`**（超限立即触发 `HTTP 451` 拒绝离线放行）！
  2. **200ms 5G eSIM 瞬时热备切换 + 美国 `Durbin Reg II` 借记卡最低费率网络路由（`HTTP 409`）**：商场 Wi-Fi 抖动时，店员 iPhone SoftPOS 在 200ms 内自动切入内置 5G 蜂窝网络保持 `100%` 实时在线授权；同时对拍卡借记卡自动择优路由至受监管低费率借记网（`STAR / NYCE / Pulse`，封顶费率仅 `0.05% + $0.21`），将门店欺诈、内鬼侵占与刷卡手续费损耗净降 **38.0%**！

---

## ③ 🧭 直观可视化图解（Mermaid 决策树 + 架构对比 + 时序图）

### 3.1 全渠道门店 `SoftPOS`、防内鬼盲退与离线 `EMV` 风控四层决策树
```mermaid
flowchart TD
    A[门店顾客拍卡结账 / 线上买线下退货BORIS / 商场断网离线收单] --> B{1. PCI MPoC硬件证明 & 断网离线SAF限额门禁}
    B -->|SoftPOS设备越狱/未通过MPoC安全飞地证明 或 断网离线SAF单笔>$150/同卡连刷企图空卡套现| C[HTTP 451: 吊销异常设备收银权限 并硬锁断网离线单笔<=$150且同卡限刷1次防集中盗刷]
    B -->|终端硬件可信 & 在线/合规离线| D{2. 防内鬼无原单盲退 & EMVCo PAR原路退回门禁}
    D -->|收银员不绑原订单直接发起独立退货企图刷进自己私人银行卡 或 累计退款超出原单可退余额| E[HTTP 403: 永久禁用Standalone无原单退货! 强制通过原PaymentIntent或29位EMVCo PAR原路退回]
    D -->|100%绑定原消费单原路退款| F{3. 禁手输卡号MOTO降级 & 3DS2扫码付兜底门禁}
    F -->|店员试图在POS键盘手敲16位卡号导致无ARQC密文100%盗刷败诉且多扣1.1%降级费| G[HTTP 422: 锁死POS键盘手输卡号! 若芯片损坏自动生成3DS2/Apple Pay手机付款码转移拒付责任]
    F -->|100% EMV芯片/NFC非接加密授权| H{4. 是否启用Tap-to-Pay移动消队 + PAR跨端识客 + Reg II借记路由?}
    H -->|店员iPhone秒变POS省$450硬件 + PAR秒认网购单 + 借记卡走低费率网省42bps| I[HTTP 409: 0内鬼盲退 0手输盗刷 门店收银与欺诈成本净省 38%]
    H -->|传统固定收银台排队刷卡| J[HTTP 200: 标准门店EMV非接交易授权完成]
```

### 3.2 “传统内鬼盲退偷钱 / 手输卡号盗刷 / 断网爆刷假卡” vs “智能体全渠道 `SoftPOS` 托管架构”对比
```mermaid
flowchart LR
    subgraph Legacy["❌ 传统门店POS痛点 (内鬼刷自己卡盲退$3万 + 手输卡号100%拒付败诉 + 断网被刷空卡)"]
        L1[POS开放无原单独立退货功能\n内鬼收银员每天刷自己借记卡偷走$850] --> L2[骗子拿刮花卡让店员手敲卡号\n多扣1.1%手续费且持卡人拒付100%败诉]
        L2 --> L3[商场Wi-Fi断网转离线无上限收单\n盗刷团伙拿空卡连刷10个奢品包跑路]
    end
    subgraph Agentic["✅ 智能体全渠道SoftPOS与PAR风控架构 (Adyen / Stripe Terminal / Tap to Pay)"]
        A1[焊死无原单盲退仅准Referenced原路退\n29位EMVCo PAR跨Apple Pay与实体卡秒配] --> A2[禁用手输卡号强制EMV/NFC动态密文\n读不出芯片秒弹3DS2二维码转嫁风险]
        A2 --> A3[PCI MPoC硬件飞地+5G双网零断联\n离线SAF硬锁$150上限净省 38% 损耗]
    end
```

### 3.3 拦截内鬼盲退、通过 `EMVCo PAR` 跨端完成 `BORIS` 退货与手输卡号转 `3DS2` 扫码时序图
```mermaid
sequenceDiagram
    autonumber
    participant Shopper as 门店顾客 / 收银店员
    participant SoftPOS as 店员 iPhone (Tap to Pay / PCI MPoC)
    participant Agent as 全渠道门店支付与防内鬼托管 Agent
    participant Gateway as 支付网关 (Adyen Terminal API / Stripe Terminal)

    Note over Shopper,Gateway: 场景1 (防内鬼盗窃)：违规店员企图发起无原单盲退 $850 到私人卡 → 立即触发 HTTP 403 阻断并告警店长!
    Note over Shopper,Gateway: 场景2 (线上用 Apple Pay 买、线下拿实体卡退 BORIS)：顾客忘带小票到店退货
    Shopper->>SoftPOS: 1. 顾客将实体信用卡轻触店员 iPhone (Tap to Pay)
    SoftPOS->>Gateway: 2. 安全飞地读取 29 位 `EMVCo PAR` (不暴露明文卡号，通过 HTTP 451 MPoC 核验)
    Gateway->>Agent: 3. 用 `PAR` 跨渠道检索出顾客 5 天前用 Apple Pay (不同尾号 DPAN) 支付的网购原单 `pi_9821`
    Agent->>Gateway: 4. 发起绑定 `pi_9821` 的 Referenced Refund 原路退回 (HTTP 403通过，零盲退风险)!
    Note over Shopper,Gateway: 场景3 (芯片损坏防手输降级)：另一顾客实体卡芯片磨损无法读取
    Agent->>SoftPOS: 5. 拦截手输卡号 (HTTP 422)，屏幕秒弹 3DS2 付款二维码 + 路由借记卡最优网 (HTTP 409，净省 38%)!
```

---

## ④ 📊 主流全渠道门店收银（Omnichannel POS / SoftPOS）与终端网关横向选型矩阵

| 选型维度 | **Adyen Unified Commerce (`Terminal API + Tap to Pay`)** (全球高奢、大型跨国零售与 `PAR` 跨端识客绝对霸主) | **Stripe Terminal + Tap to Pay on iPhone/Android** (开发者体验最强、线上线下令牌天然合一标杆) | **Shopify POS (`Tap to Pay`)** (DTC 品牌全渠道门店与 BORIS 退换货最敏捷方案) | **Square for Retail** (中小型连锁门店与快闪店开箱即用翘楚) |
| :--- | :--- | :--- | :--- | :--- |
| **核心适用场景** | 跨国奢侈品、美妆、服饰连锁（如 LVMH、Nike、Zara 级），需要全球一套 API 打通线上网店与 40 国线下门店 | 已使用 Stripe 处理线上收款的科技型零售商、定制家具、到家服务车队与多商户平台 | 基于 Shopify Plus 的 DTC 品牌开设线下直营店/快闪店，追求库存、会员与订单天然同库 | 精品买手店、餐饮零售混合店，需要高颜值硬件与零代码开店 |
| **防内鬼无原单盲退（Referenced Refund Lock）** | **金融级权限颗粒度**（默认锁死 `Unreferenced Refund`；必须传入原 `pspReference`，或须区域财务总监二次密码审批） | API 原生要求传入原 `payment_intent` 或 `charge` ID 才可发起退款，天然杜绝终端无原单盲退 | 退款强绑定 Shopify 原订单行项目与店员 RBAC 角色权限 | 支持关闭独立退款按钮并按店员 PIN 码记录审计日志 |
| **`EMVCo PAR` 与跨端（Apple Pay ↔ 实体卡）统一身份** | **行业最强**（实时返回 `Payment Account Reference (PAR)` 与 `ShopperReference`，刷 Apple Pay 也能秒认出官网实体卡老客） | 自动生成跨线上 `Elements` 与线下 `Terminal` 共享的 `card.fingerprint`，一键打通全渠道复购与退货 | 线上商城与线下 POS 共享同一个底层 `Order_ID`，扫码秒退 | 提供基于卡指纹的门店顾客档案关联 |
| **`SoftPOS (Tap to Pay)` 与离线 `SAF` 风控** | 全面支持 `Tap to Pay on iPhone & Android`，可精细配置离线 `SAF` 单笔限额、总池上限与同卡频次锁 | 原生集成 `Tap to Pay SDK` 并支持受控离线收单（Offline Mode）加密队列与限额 | 店员装个 `Shopify POS App` 即可用 iPhone 直接收非接卡，省去 `$400` 读卡器硬件 | 原生支持 iPhone 与 Android 手机直接贴卡收款 |
| **商业模式与成本 (`official_list_price`)** | **`Interchange++`（卡组底价 + 约 `10–12 bps + €0.10/笔`）**，大额零售最省钱 | 线下刷卡 **`2.7% + $0.05/笔`**（企业大客户支持定制 `Interchange+` 与 `Tap to Pay $0.10` 附加费） | **`2.4%–2.6% + $0.00/笔`**（含在 Shopify Plus / POS Pro `$89/月/店` 中） | **`2.5% + $0.10/笔`** + `$89/月` Plus 订阅 |

---

## ⑤ 🧪 转化率/成本测算与 7-Card 基准测试报告（7-Card Visual Benchmark Deck）

> **数据溯源声明（Provenance）**：以下基于某年营收 `$1.1 亿`、拥有 45 家直营门店的全渠道轻奢服饰品牌季度门店收银与支付损耗池（`$190,000/季度` 因内鬼店员利用无关联盲退刷私人卡侵占资金、店员手输卡号导致的 `100%` 盗刷拒付败诉与 `1.10%` 降级手续费差价、商场断网离线收单导致的坏账、以及借记卡未走低费率网络的超额刷卡费池）对比测算，标记为 `synthetic`（`independently_reproduced=false`）。

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 1 / 7 · HANDS-ON · OMNICHANNEL SOFTPOS, REFUND & OFFLINE EMV ESCROW         ║
║ Headline: Referenced-Refund Lock & SoftPOS EMV Cut Store Payment Loss by 38%     ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ [Scenario & Thresholds]        [Structured Input]       [Top Decisions & KPIs]   ║
║ • Store Pool: $190,000 / Qtr   • Refund: Referenced Only• Verified: HTTP 200     ║
║ • Blind Refund: 0 Embezzlement • Entry: Block Manual PAN• BlindRefund: HTTP 403  ║
║ • Downgrade: Save 110 bps MOTO • Offline SAF: <=$150/1x • KeyedPAN: HTTP 422     ║
║ • BORIS Match: 29-Char EMV PAR • Security: PCI MPoC Encl• Saved Loss: -$72,200   ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ Provenance: synthetic (independently_reproduced=false) · Suite: WebIQ-R212 (#331)║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 2 / 7 · SCENARIO: BORIS APPLE PAY RETURN & CASHIER BLIND-REFUND BLOCK       ║
║ Headline: Unlinked Cashier Self-Refund Blocked; BORIS Matched via 29-Char PAR    ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ Input Quote: "Block cashier's $850 unlinked terminal refund to personal card;    ║
║ match shopper's physical Visa via EMVCo PAR to prior web Apple Pay order pi_9821"║
║ 1. [choice] Referenced-Refund PAR Gate ──► 1.00 conf ──► [Act automatically]     ║
║    ████████████████████████████████████████ 100% (Unlinked Refund Blocked: 403)  ║
║ 2. [choice] Manual Keyed-PAN Veto      ──► 0.99 conf ──► [Act automatically]     ║
║    ███████████████████████████████████████▊ 99% (100% EMV NFC Cryptogram Only)   ║
║ 3. [score]  SoftPOS + Reg II Routing   ──► 0.98 conf ──► [Confirm: HTTP 409]     ║
║    ███████████████████████████████████████░ 98% (PAR Matched; -$72,200/Qtr Saved)║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 3 / 7 · WHAT I TESTED · FULL 5-LANE EVALUATION MATRIX                      ║
║ Headline: 5/5 Deterministic Guardrails Verified Across Refunds, MOTO & SAF       ║
╠══════════════════════════╦══════════════════════════╦══════════════════╦═════════╣
║ SCENARIO                 ║ QUESTION / TASK          ║ MODEL ANSWER     ║ ACTION  ║
╠══════════════════════════╬══════════════════════════╬══════════════════╬═════════╣
║ Baseline Tap-to-Pay Txn  ║ EMV NFC + MPoC attested  ║ HTTP 200 ($0)    ║ Auto    ║
║ Unlinked Blind Refund    ║ Refund $850 to staff card║ HTTP 403 Blocked ║ Block   ║
║ Manual Keyed PAN Entry   ║ Type 16-digit PAN on POS ║ HTTP 422 Blocked ║ Block   ║
║ Offline >$150 / Bad MPoC ║ $900 SAF or rooted phone ║ HTTP 451 Hold    ║ Human   ║
║ PAR BORIS + Reg II Debit ║ Cross-token + 5G failover║ HTTP 409 (-38%)  ║ Confirm ║
╠══════════════════════════╩══════════════════════════╩══════════════════╩═════════╣
║ Gate Summary: 100% deterministic policy match; 0 blind refunds & 0 keyed-PAN loss║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 4 / 7 · UNDER THE HOOD · PROTOCOL & SCORING MECHANICS                       ║
║ Headline: Deterministic Policy Input Contract → Verifier Decision Trace          ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ // Input Contract (OmnichannelSoftposTapToPayPolicyInput)                        ║
║ { "quarterly_unlinked_refund_keyed_fraud_and_offline_saf_pool_usd": 190000.0,    ║
║   "unlinked_standalone_terminal_refund_or_exceeding_original_capture": false,    ║
║   "manual_keyed_pan_entry_fallback_without_emv_or_3ds2_qr": false,               ║
║   "offline_saf_exceeding_150_floor_limit_or_unattested_mpoc_device": false,      ║
║   "emvco_par_cross_channel_match_and_reg_ii_debit_routing_ready": true }         ║
║                                      ↓                                           ║
║ // Verifier Output (<answer>)                                                    ║
║ { "status_code": 409,                                                            ║
║   "decision": "EMVCO_PAR_OMNICHANNEL_AND_REG_II_SOFTPOS_CONFIRM",                ║
║   "mandate_token": "omnichannel_softpos_escrow_optim_409", "savings_usd": 72200 }║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 5 / 7 · ROBUSTNESS CHECK · PERTURBATION & CONSISTENCY                       ║
║ Headline: 0.0 pts Variance Across Option Reversal & Entry-Mode Perturbations     ║
╠══════════════════════════════╦═════════════════╦══════════════════╦══════════════╣
║ QUESTION / ANSWER            ║ ORIGINAL        ║ REVERSED / PERT  ║ CHANGE (PTS) ║
╠══════════════════════════════╬═════════════════╬══════════════════╬══════════════╣
║ Referenced-Refund Only Gate  ║ HTTP 403 (100%) ║ HTTP 403 (100%)  ║ 0.0 pts      ║
║ Manual Keyed-PAN Veto Gate   ║ HTTP 422 (100%) ║ HTTP 422 (100%)  ║ 0.0 pts      ║
║ Offline SAF & PCI MPoC Lock  ║ HTTP 451 (100%) ║ HTTP 451 (100%)  ║ 0.0 pts      ║
║ PAR + Reg II SoftPOS Net 38% ║ $72,200 Saved   ║ $72,200 Saved    ║ 0.0 pts      ║
╚══════════════════════════════╩═════════════════╩══════════════════╩══════════════╣

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 6 / 7 · LATENCY · BATCHING & SCALING LATENCY                                ║
║ Headline: 45ms EMVCo PAR Cross-Channel Lookup & 200ms 5G eSIM Failover           ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ EMVCo PAR BORIS Order Lookup ║ █ 45 ms (Agent) vs Manual Receipt Hunting         ║
║ 5G eSIM SoftPOS Failover     ║ ██ 200 ms (Switch) vs Risky Offline SAF Queue     ║
║ 3DS2 QR Pay-by-Link Fallback ║ ██ 650 ms (Render) vs $3,000 Keyed-PAN Chargeback ║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 7 / 7 · MY TAKE · GOOD FIT VS NOT FOR & READINESS                           ║
║ Headline: Eliminate In-Store Refund Embezzlement & Keyed-Card Downgrades         ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ ✅ GOOD FIT                               ⛔ NOT FOR                             ║
║ • Omnichannel retail stores, luxury       • Pure B2B wire-only treasury systems  ║
║   boutiques, pop-ups & mobile field reps    with zero retail store foot traffic  ║
║ • Brands deploying Adyen Terminal API,    • Underground coal-seam methane        ║
║   Stripe Terminal, Shopify POS or Square    degasification unrelated to POS      ║
║ Readiness: Production-verified schema in `lab/webiq_commerce_demo.py` (R212).    ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

---

## ⑥ 🛠️ 商业上线风控与架构评审 Checklist

- [ ] **全面禁用无原单独立退货（Unlinked Refund）与 `EMVCo PAR` 跨端原路退回门禁（HTTP 403）**：门店 POS 与 SoftPOS 是否已从网关层永久关闭 `Standalone / Unlinked Refund` 权限，强制所有退款 100% 绑定原消费 `PaymentIntent / pspReference` 原路退回（并通过 29 位 `EMVCo PAR` 自动关联顾客线上 Apple Pay 虚拟卡号与线下实体卡）？
- [ ] **硬件级锁死门店 POS 键盘手输卡号（Disable Manual Keyed PAN Entry）与芯片故障转 `3DS2` 扫码付锁（HTTP 422）**：是否已彻底关闭店员在收银机键盘上手敲 16 位卡号的功能（消灭 `1.10%` 无卡降级费与 `100%` 拒付败诉），并在实体卡芯片损坏时自动弹出手机 `3DS2 / Apple Pay` 付款二维码？
- [ ] **`PCI MPoC` 硬件安全飞地实时证明与断网离线收单（`Offline SAF`）`$150` 熔断门禁（HTTP 451）**：店员手机运行 `Tap to Pay` 前是否强制校验未越狱/Root 及 `MPoC` 安全飞地证明？且在极端断网转离线 `SAF` 时，是否强制锁死单笔 `<= $150` 且同一张卡禁止离线连刷第 2 笔？
- [ ] **商场 Wi-Fi 掉线 200ms 自动切 5G eSIM 蜂窝备份网与借记卡 `Reg II` 低费率路由（HTTP 409）**：SoftPOS 是否配置了 Wi-Fi 与 5G 蜂窝双通道无缝热切以尽量保持 100% 实时联机授权，并将借记卡交易自动路由至受监管低费率借记网络？
- [ ] **同店异常退货率与打折抹零店员行为实时审计**：当某名收银员的单日退货笔数或手工改价折扣率偏离门店均值 `3σ` 时，系统是否实时冻结其退货权限并推送店长复核？
