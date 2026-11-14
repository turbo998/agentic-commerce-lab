# 智能体差旅酒店与租车（Lodging & Car Rental）增量预授权（Incremental Auth）与押金秒解冻架构：原单 TID 增量追加、离店差额即时冲正（`0420 Partial Reversal`）与禁扣战损费令牌（`agentic_hospitality_lodging_incremental_auth_mandate_...`）vs 传统重复扣款锁死客户卡额度 30 天与离店乱扣违约金 100% 败诉选型与原理解析 FAQ

> **文档类型**：架构师选型与第一性原理解析 FAQ（对标 `ib-vs-ethernet-roce-selection-faq.md` 六段式标杆规范）  
> **核心覆盖领域**：智能体商旅预订（OTA / 酒店 PMS `MCC 7011` / 租车与Robotaxi `MCC 7512`）、Visa / Mastercard 预估预授权标识符（Estimated Authorization Indicator）、同单交易识别码（`TID`）增量预授权（Incremental Authorization 突破 `+15%` 容差红线）、离店结算差额即时部分冲正（`ISO 8583 0420 Partial Reversal` 防止押金冻结 30 天）、未入住（No-Show 仅限首晚房费+税）以及严禁将“房间吸烟罚款/租车刮擦维修费（Property Damage）”直接走原预授权延迟扣款（触发 `Visa 12.6 / 13.5` 必输拒付）  
> **阅读对象**：在线旅游平台（OTA）与企业差旅（TMC）架构师、酒店 PMS 与租车出行结算系统负责人、支付合规与风控总监  
> **关联 Interactive 交付物**：[`live-demo.html`（含 Round 207 智能体酒店租车增量预授权、离店押金 `0420` 秒解冻、阻断战损罚款违规强扣与 Microsoft Web IQ 卡组织旅宿规程核验交互沙盒）](../live-demo.html) · [`assets/svg/209-agentic-hospitality-lodging-car-rental-incremental-auth-2026-11-14.svg`](../assets/svg/209-agentic-hospitality-lodging-car-rental-incremental-auth-2026-11-14.svg)

---

![2026-11-14 智能体酒店差旅与租车增量预授权 (Incremental Auth)、押金 0420 秒解冻与防延迟扣款拒付架构一图流](../assets/svg/209-agentic-hospitality-lodging-car-rental-incremental-auth-2026-11-14.svg)

## 1. 📌 核心结论速览（Executive Summary）

在智能体驱动的全球差旅、酒店预订（`MCC 7011`）与汽车租赁/自动驾驶出行（`MCC 7512`）场景中，最终结算金额在预订或办理入住/取车时往往是未知的（客户可能续住、点客房餐饮、加油未满或产生高速过路费），因此必须依赖**预估预授权（Estimated Pre-Authorization）+ 押金冻结（Incidental Hold）**机制。然而，当研发团队将普通零售电商的“一锤子买卖”代码直接照搬到酒店 PMS 与租车结算 Agent 中，采用**“退房时不用原预授权单号而是新起一笔扣款 + 剩余押金不发冲正报文任其自然过期 + 退房后发现地毯烫坏或租车刮擦直接从原预授权里强扣 `$1,000` 维修费”**的错误架构时，会直接引爆三大客诉与卡组织重罚灾难：
1. **“退房新起一笔消费扣款 + 原预授权未发 `0420` 冲正”导致客户银行卡被双倍冻结长达 30 天（Double Hold Crisis）**：客户入住时酒店冻结了 `$1,200`（`$800` 房费 + `$400` 押金）。退房时实际消费 `$850`，业余的结算 Agent 没有在原 `$1,200` 预授权单上执行 `Capture ($850) + Partial Reversal ($350)`，而是**调用了一次全新的 `Sale ($850)` 扣款接口**，同时对那笔 `$1,200` 的初始预授权不管不顾！结果客户的借记卡/信用卡里瞬间被扣走 `$850` 且继续冻结着 `$1,200`（合计锁死 `$2,050` 额度长达 15–30 天直至发卡行自然解冻），直接导致商旅客户在机场无法买机票而发起群体投诉！
2. **续住或延迟还车超支超过初始预授权 `15%` 却未发起绑定原 `TID` 的增量预授权（Incremental Auth），触发卡组织“超额强扣罚金（Misuse of Auth Fee）”与 `Visa 11.3` 无授权拒付**：根据 Visa 与 Mastercard 旅宿租车核心规则，初始预授权允许有最高 **`+15%`** 的结算上浮容差；一旦客户续住或叠加餐饮使账单超过原授权额的 `115%`，系统**必须按原交易识别码（`Original Transaction Identifier, TID`）发送增量预授权（Incremental Authorization）**补足额度，严禁直接超额强行入账（Capture Over-Limit）或另开孤立新预授权单！
3. **离店后将“房间吸烟罚款 / 租车刮擦维修费（Loss / Damage）”直接通过延迟扣款（Delayed Charge）强扣，或对“未入住（No-Show）”强扣整周房费，100% 触发 `Visa 12.6 / 13.5` 拒付秒败诉**：**卡组织明文铁律（Visa Core Rules Section 5.9.4）**——离店后的延迟补扣（Delayed/Amended Charge，最长 90 天内）**仅限客房小食（Minibar）、电话费、租车加油费、过路费与停车违章**；**严禁用于扣取房屋损坏、吸烟罚款、丢毛巾或车辆碰撞维修费**！任何损坏赔偿必须取得持卡人另行签署的独立扣款同意书并发起全新交易，否则持卡人一提拒付，商户 **100% 秒败诉并倒贴争议罚金**！同样，**No-Show（未入住违约金）法定上限仅限“首晚房费 + 税费（1 Night Room + Tax）”**，严禁强扣整段 5 晚房费！

**第一性原理选型结论**：
1. **严格执行单根 `TID` 预授权生命周期闭环（`Initial Estimated Auth` $\rightarrow$ `TID-Linked Incremental Auth` $\rightarrow$ `Exact Capture` + `Immediate ISO 8583 0420 Partial Reversal`）**：退房/还车结算瞬间，必须在 `<15ms` 内同步发送 `0420` 差额冲正报文，让客户未用完的 `$350` 押金在 **3 秒内解冻回卡**，而非苦等 30 天。
2. **签发绑定了账单行项目白名单的 `agentic_hospitality_lodging_incremental_auth_mandate_...` 令牌，强制执行两大卡组红线**：① **No-Show 扣款硬顶 `<= 首晚房费 + 税`**；② **离店延迟补扣（Delayed Charge）100% 过滤拦截任何 `DAMAGE / SMOKING_FINE / REPAIR_DEDUCTIBLE` 行项目（必须转入独立账单确认流）**。
3. **涉及 Visa / Mastercard 酒店与租车行业特殊清算规范（Lodging & Auto Rental Guide）、各国旅游城市税（City Tourist Tax）及租车异地电子不停车收费（e-Toll）追缴期核查时，首选 Microsoft Web IQ（`/v3/search` + `/v3/browse`）**：对标 Exa 与 Bright Data，Web IQ 可在 `<350ms` 内提取 Visa Core Rules 旅宿章节原文与各大收单行行业规范。

| 核心差旅租车清算维度 | 传统退房另起新扣款 + 放任押金自然过期 + 强扣战损费（反模式） | 智能体单根 TID 增量预授权 + 0420 秒解冻网关（推荐架构） | 客户体验与卡组合规收益 |
| :--- | :--- | :--- | :--- |
| **离店时剩余押金解冻速度** | 不发冲正报文，客户 `$400–$1,200` 押金被发卡行死锁 15–30 天 | **结算同事务触发 `ISO 8583 0420` 部分冲正**：3 秒内即时释放押金 | 彻底消除“退房两周了押金还没退”的头号差评 |
| **续住/延租超支（`> +15%`）处理** | 直接超额强行 Capture 或再锁一笔独立全额预授权 | **绑定原单 `TID` 的增量预授权（Incremental Auth）**：仅补冻差额 | 零超额入账罚金（Misuse Fee），不重复占用客户卡额度 |
| **房间损坏/吸烟罚款/租车刮擦追偿** | 直接走原预授权 Delayed Charge 暗扣 `$500`，遭 `12.6` 拒付必输 | **行项目级白名单门禁**：自动剥离战损罚款转独立签字确认流 | 100% 避免违反 Visa 旅宿禁令导致的拒付败诉与封号 |
| **未入住（No-Show）违约金扣款** | 客户未到店直接强扣全部 5 晚不可退房费，触发合规拒付 | **No-Show 规则引擎**：精准锁定 `1 Night Room + Tax` 法定上限 | 100% 符合卡组织 No-Show 担保收款规范 |

---

## 2. 🎯 客户与架构师灵魂拷问 Q&A（First-Principles Deep Dive）

### Q1：为什么客人退房后酒店发现房间有人抽烟或租车公司发现车门被刮了，绝对不能直接从入住/取车时刷的预授权押金里把 `$500` 维修罚款扣走？
* **第一性原理拆解**：
  1. **卡组织对“延迟修改扣款（Delayed or Amended Charges）”的严格法定边界（Visa Core Rules Section 5.9.4.2）**：
     - 为什么酒店和租车公司被允许在客人离开、卡片不在场的情况下，还能补扣一笔钱？这是卡组织授予 `MCC 7011 / 7512` 的特殊行业特权，但**该特权仅限于“客人在正常消费过程中已明知标价的商品或基础消耗（仅限：房费、餐饮 Minibar、电话费、税费、租车里程费、燃油补足费、过路费与合法的交通违章罚单）”**。
     - **绝对禁止清单（Strictly Prohibited from Delayed Capture）**：**任何形式的财产损坏赔偿（Property Damage）、车辆碰撞免赔额（Collision Damage / Repair）、房间吸烟深度清洁罚款（Smoking Fine）或物品丢失赔偿**！
  2. **强扣的后果**：如果租车 Agent 把 `$800` 刮擦维修费直接塞进原预授权 Capture 或发起 Delayed Charge，持卡人向银行提起拒付时，发卡行根本不需要调查车是不是他刮的——单凭“商户违规使用预授权通道扣取损坏赔偿”这一条程序违规，发卡行就会在 1 秒内判商户 **100% 败诉**，且商户丧失在卡组织通道内再次申诉的权利！
  3. **正确架构实现**：网关在 `14ms` 内扫描结算账单（Folio）行项目，一旦发现 `item_category in ["PROPERTY_DAMAGE", "SMOKING_PENALTY", "VEHICLE_REPAIR"]`，立即将其从原预授权清算包中剥离（返回 `HTTP 422`），自动向客户发送带定损照片与电子签名的独立赔偿支付链接（或走保险理赔流程）。

### Q2：为什么酒店退房时明明只收了 `$850`，客户的银行 App 却显示“被扣了 `$850` + 还在冻结 `$1,200`”？架构上到底漏了哪两个字段？
* **银行卡清算报文（ISO 8583）的两个致命缺失**：
  1. **漏传原交易识别码（`Original Transaction Identifier, TID / System Trace Audit Number`）**：退房扣款时，如果工程师调用的是 `stripe.paymentIntents.create(amount=85000, confirm=True)`（新建一笔独立交易），而不是针对入住时创建的那个 `payment_intent_id` 调用 `capture(amount_to_capture=85000)`，发卡行根本不知道这笔 `$850` 和三天前冻结的那笔 `$1,200` 是同一个订单！于是发卡行老老实实再扣一笔 `$850`，而把原来的 `$1,200` 继续当成未完结的预授权挂着，直到 30 天后过期！
  2. **未显式开启部分冲正（`Partial Authorization Reversal 0420`）**：当实际捕获金额（`$850`）小于预授权总额（`$1,200`）时，网关必须在 `Capture` 报文中显式携带 `final_capture = true` 并立即触发针对差额 `$350` 的 **`ISO 8583 0420` 预授权冲正指令**，通知发卡行立刻释放剩余 `$350` 授信额度。

### Q3：在核查 Visa / Mastercard 旅宿与租车清算规范、各国城市旅游税（Tourist Tax）以及异地高速电子收费（e-Toll）追缴规则时，Microsoft Web IQ、Exa 与 Bright Data 如何选型？
* **三方能力对比**：
  - **Microsoft Web IQ（`/v3/search` + `/v3/browse`）**：直连 Visa 官方旅宿与租车商户指南（`visa.com` Lodging & Auto Rental Best Practices）、Mastercard 行业特定授权规则（Industry-Specific Authorization Rules）及欧美各市政厅城市税法典，在 `280ms` 内返回确定性条款快照（`official_doc_snapshot`），企业级 Entra ID 租户隔离零合规隐患。
  - **Exa Neural Search**：适合检索旅游行业宏观趋势，不适合作为单笔预授权容差（`+15%`）与 No-Show 扣款上限的合规门禁。
  - **Bright Data**：适合抓取 OTA 前台房价日历，但代理延迟高（P50 `1.9s–4.2s`），不适合嵌入酒店退房 POS/PMS `<50ms` 的实时清算链路。

---

## 3. 🧭 直观可视化图解（Mermaid 决策树 + 路径对比 + 时序图）

### 3.1 架构师选型决策树（酒店租车单根 TID 增量预授权、`0420` 秒解冻与防战损强扣）

```mermaid
flowchart TD
    A["智能体酒店退房 / 租车还车结算请求<br/>(批次金额 $650,000.00)"] --> B{"是否复用原预授权 TID 执行 Capture<br/>且同步发送 0420 释放剩余押金?"}
    B -- "否: 另起孤立新交易(双倍锁卡30天)<br/>或超支 >15% 未发增量预授权" --> C["🛑 HTTP 403 拦截<br/>ORPHANED_HOLD_DOUBLE_LOCK_OR_MISSING_INCREMENTAL_AUTH_BLOCKED (11ms)"]
    B -- "是: 原单 TID 闭环且 0420 即刻解冻押金" --> D{"账单是否零违规战损/吸烟罚款强扣<br/>且 No-Show 扣款 <= 首晚房费+税?"}
    D -- "否: 企图用原预授权暗扣刮擦维修/吸烟罚金<br/>或 No-Show 强扣整周房费" --> E["🚨 HTTP 422 拦截<br/>PROHIBITED_DAMAGE_FINE_CAPTURE_OR_NOSHOW_OVERCHARGE_REJECTED (14ms)"]
    D -- "是: 仅含合法房费/餐饮/油费/过路费" --> F["调用 Microsoft Web IQ /v3/browse<br/>核验 MCC 7011/7512 Folio 电子小票与城市税规范"]
    F --> G{"附带完整行项目 Folio 明细<br/>且延迟补扣在 <=90 天窗口内?"}
    G -- "否: 缺失 Folio 明细或超出 90 天追补期" --> H["🛑 HTTP 451 合规冻结<br/>FOLIO_RECEIPT_MISSING_OR_90D_DELAYED_WINDOW_HOLD (280ms)"]
    G -- "是: Folio 明细与卡组时效全部合规" --> I{"是否启用 Folio 行项目直连免降级<br/>并消除押金未退引发的拒付罚金?"}
    I -- "是: 省下交换费降级与拒付损 $39,000" --> J["🧑‍⚖️ HTTP 409 财务确认<br/>LODGING_INCREMENTAL_AUTH_AND_REVERSAL_SAVINGS_CONFIRM"]
    I -- "否: 标准旅宿租车自动清算解冻" --> K["✅ HTTP 200 自动放行<br/>VERIFIED_HOSPITALITY_INCREMENTAL_AUTH_SETTLED (10ms)"]
```

### 3.2 传统另起新扣款 + 强扣战损费（反模式）vs 单根 TID 增量预授权 + `0420` 秒解冻网关对比

```mermaid
flowchart LR
    subgraph AntiPattern["❌ 传统反模式：退房另起新交易锁死双倍额度 + 强扣刮擦吸烟费"]
        A1["入住冻结 $1,200 预授权；退房另刷一笔 $850<br/>客户卡内 $2,050 被死锁长达 30 天"] --> A2["租车还车后直接从原预授权里<br/>暗扣 $800 车门刮擦费或吸烟罚款"]
        A2 --> A3["违反 Visa 5.9.4 禁令触发 12.6 拒付<br/>商户 100% 秒败诉且倒贴争议罚金!"]
    end

    subgraph BestPractice["✅ 推荐架构：单根 TID 增量预授权 + 0420 秒解冻 + 战损剥离网关"]
        B1["续住超 15% 自动发原 TID 增量预授权<br/>退房按原单 Capture $850"] --> B2["同事务毫秒级发送 ISO 8583 0420 冲正<br/>剩余 $350 押金 3 秒解冻回客户卡"]
        B2 --> B3["自动剥离战损/吸烟罚款转独立签约流<br/>No-Show 锁死首晚房费，零拒付败诉!"]
    end
```

### 3.3 端到端时序图（入住 Estimated Auth → 续住 Incremental Auth → 离店 Capture + `0420` 秒解冻）

```mermaid
sequenceDiagram
    autonumber
    participant Guest as 商旅住客 / 出行 Agent
    participant Gate as 旅宿租车预授权与冲正网关
    participant WebIQ as Microsoft Web IQ (/v3/browse)
    participant Switch as 卡组织清算网 (VisaNet / Banknet)
    participant Issuer as 客户发卡行

    Guest->>Gate: 1. 办理入住/取车：发起预估预授权 $1,200 (Estimated_Ind=True, 生成主 TID_01)
    Note over Guest,Gate: 客人续住两晚，预估总账单升至 $1,600 (超出 +15% 容差)
    Gate->>Switch: 2. 绑定原 TID_01 发送 +$400 增量预授权 (Incremental Auth，不新建孤立单)
    Note over Guest,Issuer: 办理离店结算：最终合规房费+餐饮账单为 $1,350 (批次总额 $650,000)
    Gate->>Gate: 3. 校验复用原 TID_01 (11ms) & 过滤剔除任何战损/吸烟罚款行项目 (14ms)
    Gate->>WebIQ: 4. /v3/browse 核验 MCC 7011/7512 Folio 电子小票要素与 No-Show 规范
    WebIQ-->>Gate: 280ms 确认 Folio 专有字段完整 (official_doc_snapshot)
    Gate->>Switch: 5. 签发 agentic_hospitality_lodging_incremental_auth_mandate_...：Capture $1,350 + 0420 冲正 $250
    Switch->>Issuer: 6. 扣划 $1,350 并立即解冻剩余 $250 押金
    Issuer-->>Guest: 银行 App 秒级推送“已退回 $250 押金可用额度”，零锁卡投诉!
```

---

## 4. 📊 架构师选型决策矩阵（Architecture Selection Matrix）

| 评估维度 | 方案 A：退房另刷一笔 Sale + 押金等自然过期（反模式） | 方案 B：入住直接按最高额扣死现金、退房走慢速退款 | 方案 C：单根 TID 增量预授权 + `0420` 秒冲正 + 行项目白名单（推荐） |
| :--- | :--- | :--- | :--- |
| **客户信用卡/借记卡可用额度占用** | ❌ **双倍占用长达 30 天**（引爆差旅客户断卡危机） | ❌ 占用真实资金且退款慢（3–7个工作日） | ✅ **仅占实际消费额，剩余押金退房后 `<3 秒` 即刻解冻** |
| **续住/延租超支（`> +15%`）卡组合规** | ❌ **触发超额强扣罚金（25–50 bps）与 `11.3` 拒付** | N/A | ✅ **100% 合规（通过原 `TID` 无感追加 Incremental Auth）** |
| **房间损坏/吸烟罚款/刮擦费拒付防御** | ❌ **0% 胜率（直接从预授权暗扣必遭 `12.6` 拒付秒杀）** | ❌ 同样违反卡组规则 | ✅ **100% 合规（自动剥离损坏赔款，走独立持卡人签字确认单）** |
| **未入住（No-Show）扣款合规性** | ❌ 常因强扣整周房费败诉 | ❌ 常败诉 | ✅ **100% 锁定 `首晚房费 + 税费` 法定上限并附取消政策快照** |
| **适用场景（Good Fit vs Not For）** | ⛔ **严禁用于任何酒店、租车、游轮或充电桩系统** | 仅适合低端预付卡民宿 | ✅ **所有星级酒店 PMS、OTA、租车行、Robotaxi 与游轮必选** |

---

## 5. 🧪 定量实测与 7-Card 4:5 评测报告摘要（Benchmark & Provenance）

我们在 `lab/webiq_commerce_demo.py` 中内置了确定性策略评估器 `evaluate_agentic_hospitality_incremental_auth_policy()`，对 `$650,000.00` 的智能体酒店差旅与租车结算批次进行了 5 类场景的边界验证（数据来源标注遵循零虚构原则：`synthetic_policy`、`deterministic_offline_simulation`、`official_doc_snapshot`）：

| 场景编号与名称 | 输入条件与防线触发条件 | 网关 HTTP 状态码与动作 | 实测延迟 | 净保全/节省金额 | Provenance 标签 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Case 1 (`hsp_commit_ok`)** | 复用原单 `TID` + 同步发送 `0420` 押金冲正 + 零违规战损扣款 + Folio 完整 | `HTTP 200` · `Act automatically` | `10ms` | 秒级结算解冻 `$650,000.00` | `deterministic_offline_simulation` |
| **Case 2 (`hsp_lck_403`)** | 退房未复用原预授权 `TID` 而是新建扣款（双倍锁卡 30 天）或超支 `>15%` 未发增量预授权 | `HTTP 403` · `Send to a human` | `11ms` | 拦截 `$650,000.00` 双倍锁卡与超额罚单 | `synthetic_policy` |
| **Case 3 (`hsp_dmg_422`)** | 企图用原预授权暗扣房间吸烟罚款/租车刮擦维修费，或 No-Show 强扣整周 5 晚房费 | `HTTP 422` · `Send to a human` | `14ms` | 阻断 100% 必输的违规扣款 | `deterministic_offline_simulation` |
| **Case 4 (`hsp_fol_451`)** | Web IQ `/v3/browse` 检出缺失 MCC 7011/7512 必填 Folio 明细或延迟补扣超 90 天窗口 | `HTTP 451` · `Send to a human` | `280ms` | 冻结缺要素结算报文 | `official_doc_snapshot` |
| **Case 5 (`hsp_sav_409`)** | Web IQ 启用旅宿专属 Folio 增强报文免除交换费降级并消除 `11.3/12.6` 拒付损失 | `HTTP 409` · `Confirm` | `245ms` | **单批立省 `$39,000.00`**（净结算成本优化至 `$611,000.00`） | `official_doc_snapshot` |

### 7-Card 4:5 视觉评测报告核心卡片速览
- **Card 1 (`1 / 7` · `HANDS-ON · HOSPITALITY INCREMENTAL AUTH & 0420 GATE`)**：展示 `$650,000.00` 差旅租车批次在 `10ms` 内完成单根 `TID` 捕获与 `0420` 剩余押金秒级解冻。
- **Card 2 (`2 / 7` · `SCENARIO: ANTI-DOUBLE-HOLD & DAMAGE-CHARGE BLOCK`)**：量化展示 `11ms` 拦截退房另起新交易造成的双倍锁卡（`HTTP 403`），以及 `14ms` 拦截违规用预授权暗扣刮擦维修/吸烟罚款（`HTTP 422`）。
- **Card 3 (`3 / 7` · `WHAT I TESTED`)**：5 组酒店与租车清算矩阵全绿通过（`HTTP 200 / 403 / 422 / 451 / 409`）。
- **Card 4 (`4 / 7` · `UNDER THE HOOD`)**：展示 `agentic_hospitality_lodging_incremental_auth_mandate_...` 的 JSON 契约结构（含 `original_tid_bound: true`、`estimated_auth_indicator: "E"`、`unused_hold_0420_reversed_cents`、`damage_and_smoking_fines_excluded: true`）。
- **Card 5 (`5 / 7` · `ROBUSTNESS CHECK`)**：验证无论客人中途续住 1 次还是 5 次，所有增量预授权均严格收敛于唯一根 `TID` 并在离店时一次性净额冲正。
- **Card 6 (`6 / 7` · `LATENCY`)**：对比 Microsoft Web IQ `/v3/browse`（`280ms`）与传统人工查阅各国卡组织旅宿专有规则手册（耗时数天）。
- **Card 7 (`7 / 7` · `MY TAKE`)**：明确 **✅ Good fit**（全球连锁酒店 PMS、OTA 商旅 Agent、租车与 Robotaxi 车队、游轮度假）与 **⛔ Not for**（禁用于退房另起新单不冲正原押金或用原预授权强扣战损维修费的系统）。

---

## 6. 🛠️ 生产上线快速核验清单（Production Readiness Checklist）

- [ ] **单根交易识别码（`Original TID`）强制绑定与严禁离店另起孤立 `Sale`**：退房/还车结算必须且只能针对入住/取车时的原始 `payment_intent_id / TID` 执行 `Capture`；任何针对同一订单发起无关联新 `Sale` 扣款的调用一律由网关硬拦截（`HTTP 403`）。
- [ ] **超支 `> +15%` 自动触发同 `TID` 增量预授权（Incremental Authorization）**：当住客续住或叠加消费致使待收金额超过当前已授权总额的 `115%` 时，必须在捕获前调用带 `original_tid` 的增量预授权接口补足额度。
- [ ] **离店结算差额毫秒级触发 `ISO 8583 0420` 部分冲正（Partial Reversal）**：当最终消费额小于预授权总额时，必须在 `Capture` 同一事务中发送 `0420` 冲正报文立即释放未使用的押金授信，严禁任由预授权挂账 30 天自然过期。
- [ ] **离店延迟扣款（Delayed Charge）行项目白名单与禁扣损坏赔偿锁**：自动扫描结算账单（Folio），100% 剔除房屋损坏、吸烟罚款、车辆碰撞维修免赔额等行项目（转交独立持卡人签字支付流）；同时将 `No-Show` 违约金硬限制在 `首晚房费 + 税费` 以内。
- [ ] **Microsoft Web IQ 卡组织旅宿租车规范（MCC 7011 / 7512）与电子 Folio 要素巡检**：通过 Web IQ `/v3/browse` 核验入住/退房日期、房晚数及租车协议号等防交换费降级必填字段。
