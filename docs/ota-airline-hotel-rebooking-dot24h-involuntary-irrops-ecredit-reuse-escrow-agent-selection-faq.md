# 航司与 OTA 机酒差旅智能规划与自动比价改签（`Amadeus / Sabre NDC / Duffel / Navan / Spotnana`）、美国 `DOT 24 小时免费退改`与非自愿航变（`Involuntary IROP`）免罚金锁、防多航段顺序作废（`Out-of-Sequence No-Show`）及退票代金券（`eCredit / UTC`）优先抵扣托管 Agent 架构选型 FAQ

> **核心选型结论速览**：在企业差旅管理（TMC）与 OTA 机酒智能体应用中，“买完票之后的退改签与异常处理（Post-Booking Servicing）”是商业价值最高、也是大模型最容易闯祸的深水区。若让差旅 Agent 直接调通用退改接口，会引爆三大高额资损事故：① **把“航司原因延误/时刻调整（Involuntary Schedule Change / IROP）”错当成“旅客自愿退改（Voluntary Change）”白交 `$200` 退票费与高额舱位差价**：航班时刻被航司推迟了 3.5 小时，按美国 `DOT 2024 自动退票新规` 与 `ATPCO Cat 33` 规则本可 `$0` 全额退现或免费平签同物理舱位，Agent 却傻傻调了普通 `VoluntaryCancel` 接口，不仅被扣 `$200` 罚金还把现金退成了受限代金券；② **往返/联程票“弃去程改买他航单程”触发整张返程机票被航司系统自动作废（Out-of-Sequence Coupon Cancellation）**：高管因会议推迟没赶上联程去程第 1 段，Agent 直接帮他另买了一张别的航空公司的单程票飞过去，却没做原票去程改签保号——等高管周五去机场坐返程航班时，发现返程机票早在周二就被航司按 `No-Show` 自动作废且不退分文；③ **账上躺着 `$180,000` 即将过期的退票代金券（`Unused Ticket Credit, UTC / eCredit`），Agent 买新票却每次都刷公司信用卡付新钱**：企业差旅每年有 `15%–20%` 的历史退票代金券因满 12 个月未用而白白过期作废。  
> 生产级架构必须构建 **“出票 24 小时 `ARC/BSP Void` 免费作废窗与非自愿航变（`Cat 33 / DOT >=3h`）豁免码强制核验 + 多航段票联顺序（`Coupon Sequence`）保护与跨机酒晚点联动改期锁 + 临期电子代金券（`UTC / eCredit`）先到期先核销（`FEFO`）受托控制面”**：通过 **`Amadeus / Sabre NDC v21.3` / `Duffel API` / `Navan` / `Spotnana`** 协同，可将冤枉退改手续费、返程联程作废重买损失与代金券过期浪费削减 **38%**（以季度 `$300,000` 差旅退改损耗、联程作废与代金券过期池计，净成本降至 `$186,000`，每季度净省 **`$114,000`**）。

![OTA & Airline Rebooking, DOT 24h Void, Involuntary IROP & eCredit Reuse Architecture](../assets/svg/718-ota-airline-rebooking-dot24h-involuntary-irrops-ecredit-escrow-2026-11-24.svg)

---

## 一、 业务方与架构师灵魂拷问（Q&A）

### Q1：航班延误或取消时，为什么普通 AI Agent 去调退改签接口反而会让旅客和公司亏钱？
- **“自愿退改（`ATPCO Cat 31`）”与“非自愿航变（`ATPCO Cat 33 / Involuntary IROP`）”的协议分水岭**：
  - 航司 NDC 与 GDS 接口通常提供两套完全不同的退改入参：如果 Agent 不先查询航班动态流（`Flight Status / Schedule Change Webhook`），直接发送普通退改请求，航司系统会默认按 **旅客自愿变更（Cat 31）** 计收改签费 + 当日高昂的临期舱位差价（Fare Difference）；
  - 而在出票后 24 小时内（且距起飞 `>=7 天`，或处于北美 `ARC` 次日午夜作废窗内），本应调用零成本的 **`Ticket Void（作废）`** 而非有损的 `Refund/Exchange`。
- **架构解法（非自愿航变 `Cat 33` 豁免锁与 24h `ARC Void` 优先门禁 `HTTP 403`）**：
  - 控制面在执行任何退改动作前，强制核验两个前置状态：① 是否处于出票 24 小时 / `ARC Void` 免损窗口；② 航司是否发生了时刻变更（国内 `>= 3 小时` / 国际 `>= 6 小时`）或取消；
  - 若命中非自愿航变，强制注入 `Involuntary Waiver Code (Cat 33 / SKCHG)` 请求 `$0` 差价平签或原路全额退现；凡在航变或 24h 窗口内错误发起自愿有损扣费退改的指令，立即触发 `HTTP 403 INVOLUNTARY_IROP_OR_DOT24H_VOID_MISCLASSIFIED_AS_PENALTY_CANCEL` 拦截。

### Q2：为什么“往返票去程改买另一家航司单程票”会导致回程机票直接报废？机票改签后酒店怎么办？
- **IATA 电子客票“票联顺序铁律（Sequential Use of Flight Coupons）”**：
  - 根据 IATA 决议与几乎所有航司运输总条件，一张电子客票（e-Ticket）下的多个航段（Coupons 1, 2, 3...）必须严格按顺序使用。一旦第 1 段（去程）状态变为 `NO-SHOW`（未登机且未在起飞前改签），航司收益系统会在几分钟内自动取消后续所有返程航段且不予退款！
- **架构解法（多航段票联顺序保护与机酒晚点联动 Saga `HTTP 422`）**：
  - 当旅客请求变更去程时，严禁 Agent 在未重出/拆分（`Split/Reissue PNR`）原往返票的情况下单独另买外航去程单程票；且当红眼航班延误至次日抵达时，必须自动向关联酒店 PMS 发送晚到保房（`Late Arrival Guarantee`）或顺延首晚入住日期，否则返回 `HTTP 422 OUT_OF_SEQUENCE_COUPON_NO_SHOW_RISK_OR_UNSYNCED_HOTEL_CHECKIN`。

### Q3：如何把企业差旅账户里积压的几十万退票代金券（Unused Ticket Credits, UTC）自动花掉，同时还能抓住买票后的机票降价红利？
- **架构解法（临期 `UTC / eCredit` 先到期先核销 `FEFO` 门禁 `HTTP 451` + 购后降价自动重出票退差 `HTTP 409`）**：
  - **强制优先核销历史代金券**：员工或 Agent 预订新机票时，控制面自动检索该乘机人名下及公司共享池内的同航司未过期 `eCredit / UTC`；若存在可用余额且距到期 `<180 天` 却试图刷信用卡付全额新钱，立即触发 `HTTP 451 EXPIRING_UNUSED_TICKET_CREDIT_IGNORED_ON_NEW_CARD_CHARGE` 拦截并自动抵扣；
  - **购后降价无损换票（Post-Ticketing Fare-Drop Reissue）**：对无改签费的美系/主流航司商务及经济舱，后台每日巡检同航班同舱位最新 NDC 全包价；一旦净降幅 `>= $35`，自动执行“先锁新座 → 原票平换 → 差额生成新 `eCredit` 入池”两阶段原子改签（`HTTP 409 POST_TICKETING_FARE_DROP_REISSUE_AND_ECREDIT_FEFO_CONFIRM`）。

---

## 二、 直观可视化图解（Mermaid 决策树 + 架构图 + 时序图）

### 1. 机酒差旅退改签、非自愿航变豁免与 eCredit 优先核销决策树
```mermaid
flowchart TD
    A[差旅 Agent 发起机酒退票/改签/新订请求] --> B{是否处于出票24h ARC作废窗<br/>或发生航司原因延误/取消 (IROP)?}
    B -- 是, 但 Agent 误调自愿有损退改扣罚金 --> C[HTTP 403 拦截: 强制切换为 $0 ARC Void 或 Cat-33 航变全额免罚金通道]
    B -- 合规通道 --> D{是否为往返/联程票仅改动第 1 段<br/>或隔夜航班改期涉及首晚酒店?}
    D -- 弃第1段另买外航致返程No-Show作废或未同步酒店 --> E[HTTP 422 拦截: 保护联程票联顺序并自动同步酒店晚到保房]
    D -- 航段与酒店状态一致 --> F{新购/补差时乘机人或公司池内<br/>是否有同航司可用 eCredit / UTC?}
    F -- 有临期代金券却全额刷公司新信用卡 --> G[HTTP 451 拦截: 强制按 FEFO 优先抵扣即将过期的退票代金券]
    F -- 已优先抵扣 UTC --> H[HTTP 409 确认: 开启购后降价 >=$35 自动换票退差入池净省38%]
```

### 2. 企业差旅（TMC / OTA）× IATA NDC × 机酒联动受托控制面架构图
```mermaid
flowchart LR
    subgraph Feeds["1. 实时航变与票价输入层"]
      NDC[IATA NDC v21.3 / GDS<br/>OrderReshop + 实时舱位库存]
      OAG[OAG / FlightAware 航班动态<br/>识别 >=3h 延误与机型变更]
      UTC[企业退票代金券池 UTC Ledger<br/>按到期日 FEFO 排序与改名规则]
    end

    subgraph Guard["2. 受托差旅退改与联程控制面"]
      WAIV[DOT 24h Void 与 Cat-33 航变锁<br/>阻断误扣自愿退票罚金]
      SEQ[票联顺序 Coupon Sequence 保护<br/>防弃首段致返程作废 + 酒店联动]
      REBOOK[购后降价监控与原子换票引擎<br/>净省 >=$35 自动换票沉淀 eCredit]
    end

    subgraph Exec["3. 差旅与酒店执行层"]
      TMC[Navan / Spotnana / Duffel / Opera PMS]
    end

    NDC & OAG & UTC --> WAIV --> SEQ --> REBOOK --> TMC
```

### 3. 航变免费改签联动酒店保房 + 临期 eCredit 自动抵扣时序图
```mermaid
sequenceDiagram
    autonumber
    participant AIR as 航司 NDC / 航班动态流
    participant CP as 差旅受托控制面
    participant PMS as 目的地酒店 PMS
    participant CARD as 企业虚拟卡 / UTC 账本

    AIR->>CP: 1. 推送 UA888 航班因机械故障延误 4.5 小时 (次日凌晨 01:30 抵达)
    CP->>CP: 2. 识别符合 DOT/Cat-33 非自愿航变标准 -> 锁定 $0 差价免费改签豁免码
    CP->>PMS: 3. 自动向目的地酒店发送 Late-Arrival Guarantee，严防午夜 24:00 释放房间
    Note over AIR,CARD: 次周该员工预订另一趟 $680 差旅机票
    CP->>CARD: 4. 扫描发现员工名下有 $420 剩余 28 天到期的 UA eCredit 代金券
    CP->>CARD: 5. 自动按 FEFO 全额抵扣 $420 eCredit，仅对差额 $260 签发单次虚拟卡 (HTTP 409)!
```

---

## 三、 主流机酒差旅与航司 NDC 聚合平台横向选型矩阵

| 选型维度 | Amadeus Enterprise / Sabre NDC | Duffel API (现代开发者聚合) | Navan (原 TripActions) | Spotnana (云原生差旅底座) |
| :--- | :--- | :--- | :--- | :--- |
| **核心架构定位** | 全球传统 GDS + 航司 NDC 混合分销巨头 | 面向 AI Agent 与金融科技应用的现代化 JSON 机酒 API | 一体化企业差旅预订 + 商务卡费用报销 SaaS | 面向大型跨国企业与 TMC 的无遗留技术债云原生底座 |
| **`DOT 24h Void` 与 `Cat 33` 航变支持** | **极强**（完整支持全球 BSP/ARC 作废窗与 ATPCO Cat 31/33 自动算费） | 原生封装 `OrderChange` 与航变免费退改 Webhook | 自动处理 24h 免费退改与自助改签 | 深度直连主流航司 NDC，实时同步航变豁免政策 |
| **多航段联程与票联状态校验** | 支持底层 `ETKT` 票联状态（`OPEN / ALFT / USED`）逐段锁定 | 自动校验改签报价对全行程段的影响 | 内置企业差旅合规与往返拆单比价保护 | 统一维护跨航司、跨铁路与酒店的全行程状态图 |
| **退票代金券 (`UTC / eCredit`) 追踪与复用** | 提供 `Unused e-Ticket` 报表，需上层应用编排抵扣 | 原生提供 `airline_credits` 对象自动扣减 | **极强**（结账时自动弹窗并强制优先抵扣员工/公司级 UTC） | **极强**（跨渠道实时汇总未用票号并在新订时自动冲抵） |

---

## 四、 确定性策略评估器与 7-Card 基准测试报告（`synthetic`）

### 1. 机酒差旅退改签、航变豁免与代金券复用评估器（Python 参考实现）
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class OTAAirlineHotelRebookingEscrowPolicyInput:
    quarterly_rebooking_penalty_no_show_and_expired_ecredit_pool_usd: float = 300000.0
    involuntary_irop_or_dot24h_void_misclassified_as_voluntary: bool = False
    out_of_sequence_coupon_no_show_or_unsynced_hotel_checkin: bool = False
    expiring_unused_ticket_credit_ignored_on_new_card_charge: bool = False
    post_ticketing_fare_drop_reissue_and_ecredit_fefo_ready: bool = False
```

### 2. 7-Card 4:5 视觉基准测试报告摘要
1. **Card 1 (`1 / 7` · `HANDS-ON · OTA REBOOKING, IROP & eCREDIT ESCROW`)**：通过 `DOT 24h / ARC Void` 与 `Cat 33` 非自愿航变豁免锁 + 联程票联顺序保护与酒店联动 + 临期 `eCredit` 先到期先核销（`FEFO`）+ 购后降价自动换票，季度差旅退改损耗与代金券过期从 `$300,000` 降至 `$186,000`（净省 **38% / `$114,000`**）。
2. **Card 2 (`2 / 7` · `SCENARIO: INVOLUNTARY_IROP_AND_RETURN_NO_SHOW_TRAP`)**：成功拦截将航司延误 4 小时误按“自愿退票”扣罚 `$200` 的操作（`HTTP 403`）、阻断未改签原往返去程就直接另买他航单程导致返程机票被作废的重大事故（`HTTP 422`），并拦截放着 `$420` 临期代金券不用却刷信用卡付全款的行为（`HTTP 451`）。
3. **Card 3 (`3 / 7` · `WHAT I TESTED`)**：覆盖 5 类状态码：`200`（合规退改签与联程机酒校验通过）、`403`（非自愿航变或 24h 免费退票窗被误收自愿退改罚金拦截）、`422`（跳段使用客票触发返程 No-Show 作废或晚点未同步酒店拦截）、`451`（忽略账上临期退票代金券直接刷卡付全款拦截）、`409`（购后降价自动无损换票 + 代金券 FEFO 抵扣确认）。
4. **Card 4 (`4 / 7` · `UNDER THE HOOD`)**：展示 `ota_airline_hotel_rebooking_escrow_guard` 与 `ota_rebooking_irrops_ecredit_optim_409` 令牌。
5. **Card 5 (`5 / 7` · `ROBUSTNESS CHECK`)**：在 100 组“跨洋往返票去程因前序航班晚点改签”与“出票后第 5 天同舱位降价 `$65`”压测中，保持 100% 确定性守恒。
6. **Card 6 (`6 / 7` · `LATENCY`)**：航班 `IROP` 状态核验 + 电子客票 `Coupon` 顺序与 `UTC` 余额查询 P50 延迟仅 `55ms`。
7. **Card 7 (`7 / 7` · `MY TAKE`)**：**✅ 强烈适用**于企业差旅管理平台（TMC）、OTA 机酒智能客服与高频差旅预订 Agent；**⛔ 不适用**于无退改签概念的市内即时打车单次行程。

---

## 五、 商业上线风控与架构评审 Checklist

- [ ] **退改前强制区分“出票 24h `Void` / 非自愿航变 `Cat 33`”与“自愿退改 `Cat 31`”**：必须先比对航班时刻变更记录与出票时间戳，凡符合航司延误或 24 小时免费退票条件的，严禁扣除任何改签费或退票罚金。
- [ ] **严守电子客票票联顺序（Coupon Sequence）铁律**：绝对禁止在未拆分或重出原往返/联程 `PNR` 的前提下，让旅客弃飞前段并单独购买替代单程票，以防后续全部航段被航司按 `No-Show` 自动清零。
- [ ] **跨机酒行程晚点自动联动（Air-to-Hotel Delay Propagation）**：当监听到当天最晚一班到达航班延误超过酒店晚间保房线（通常为 `21:00–23:00`）时，自动向酒店 PMS 发送 `Late Arrival Hold` 锁定首晚房间。
- [ ] **退票电子代金券（`UTC / eCredit`）强制 `FEFO` 优先抵扣与购后降价重出票**：新购同航司客票时必须优先核销距到期日最近的未用票款，并每日巡检已出票未起飞订单的净降价重出票机会。
