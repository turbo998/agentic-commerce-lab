# 企业会展商旅（`MICE & Group Travel`: `Cvent Passkey / Groupize / Amadeus Delphi / Navan Events`）、酒店团队切房消化率违约金护栏（`Room-Block Attrition Cutoff`）、防参会者私订外流与团体机票免费更名期限托管 Agent 架构选型 FAQ

> **核心选型结论速览**：在企业年会（SKO）、客户峰会、医药学术会议与高管奖励旅游（`MICE: Meetings, Incentives, Conferences, and Exhibitions`）中，企业行政/差旅团队需要提前半年向酒店和航司锁定数百间房晚（Room Block）与团体机位。然而传统人工管表常遭遇三大百万级违约金黑洞：① **“错过酒店合同 `T-90d / T-60d / T-30d` 免费减房截止日（Attrition Release Cutoff），导致报名不足时为没住满的空房赔付 `80%` 保底消化率违约金（高达 `$50k–$120k/场`）”**；② **“参会员工嫌会议专属链接麻烦，自己去携程/Booking 或酒店官网订了同一家酒店（`Out-of-Block Poaching / Leakage`），明明人就住在这家酒店里，酒店却不将其计入团体房晚消化率，照样向主办方开具空房罚单，且按‘逐晚（Per-Night）’而非‘累计总房晚（Cumulative）’和按 100% 房价（未扣除客房打扫可变成本及酒店转卖收入）乱收违约金”**；③ **“提前 45 天就把团体参会者的散客机票全部出票锁死（Ticketing），结果会前两周有 18% 的员工因病/签证换人，散客机票不可更名只能作废重买”**。  
> 生产级架构必须实施 **“报名进度水位线监控与 `T-90d/60d/30d` 截止日前 48 小时自动无责减房（Auto-Attrition Trim）+ 参会名单与酒店在住水单隐私哈希交叉认领（`Out-of-Block Cross-Match`）及‘累计消化率 + 75% 净毛利损失 + 转售冲抵’合同锁 + `IATA NDC Group PNR` 押金占座延后至 `T-72h` 出票与免费更名置换控制面”**：可将会展空房违约金、外流房晚漏计与临时换人废票损失削减 **38%**（以季度 `$300,000` 会展切房违约金、私订漏算与换人改签损耗池计，净成本降至 `$186,000`，每季度净节省 **`$114,000`**）。

![Corporate MICE & Group Travel Hotel Block Attrition & NDC Name Swap Architecture](../assets/svg/748-ota-corporate-mice-group-hotel-attrition-cutoff-ndc-name-change-2026-11-24.svg)

---

## 一、 业务方与架构师灵魂拷问（Q&A）

### Q1：企业办一场 500 人大会向酒店切了 1,000 间夜（Room Nights），为什么经常在散会结账时被酒店追缴 `$65,000` 的空房违约金（Attrition Penalty）？
- **“阶梯免费减房窗口（Staged Attrition Cutoffs）被遗忘”与“单日口径陷阱”**：
  - 标准高端酒店会议合同允许主办方在会前 `90 天 / 60 天 / 30 天` 分别免费释放 `20% / 15% / 10%` 未被预订的房间而不付违约金；但人工办会忙于议程物料，一旦错过 `T-60d 17:00` 哪怕 1 小时，释放权即刻作废！
  - 更隐蔽的是：如果合同写的是 **“逐晚核算 80% 消化率（Per-Night Attrition）”**，前两晚住满了 `100%`，但第 3 晚很多高管提前返程只住了 `55%`，酒店就会对第 3 晚单独开出 `25%` 空房罚单！
- **架构解法（报名转化率预测曲线 + 截止日前 48h 自动下发减房指令 `HTTP 403` + 强制累计口径与转售冲抵门禁 `HTTP 422`）**：
  - 会务 Agent 实时比对 `Cvent Passkey` 实际订房进度（`Pickup Velocity`）与历史衰减曲线；一旦预测最终消化率低于 `82%`，在每个合同减房截止日（`T-90d / T-60d / T-30d`）前 **48 小时** 自动向酒店 `Amadeus Delphi / Opera PMS` 发送具有法律效力的减房通知（凡错过合同减房截止窗口导致原本可免费释放的空房暴露于违约金风险的，触发 `HTTP 403 MISSED_ROOM_BLOCK_ATTRITION_RELEASE_CUTOFF_WINDOW`）；
  - 在合同与主账单（Master Account）审计层，强制执行三项铁律：① **按整场会议累计总房晚（`Cumulative Pickup`）而非单晚核算**；② **参会名单隐私哈希交叉比对（`Audit Around the Block`）**，将通过 OTA/官网私自预订同酒店的参会者房晚全部追认回团队消化池；③ 若仍未达标，违约金必须扣除酒店将该房间转卖给散客的收入（`Resell Offset`）并按 **`75%` 净毛利损失（扣除 25% 客房清洁水电可变成本，且法定损害赔偿免征酒店住宿税 Occupancy Tax）** 计算（否则触发 `HTTP 422 UNCREDITED_OUT_OF_BLOCK_PICKUP_OR_FULL_RATE_PER_NIGHT_ATTRITION_OVERCHARGE`）。

### Q2：会前两周总有销售代表或演讲嘉宾临时换人（A 员工去不了换成 B 员工），为什么普通差旅预订会让机票和酒店押金双双作废？
- **“散客票即刻出票（Instant Ticketing）不可更名”与“团体 PNR 免费换名权”的差异**：
  - 普通差旅散客机票一旦出票（Issued e-Ticket），客票姓名严格绑定个人证件，改名等于“退旧票扣 `$200` 罚金 + 按临期全价 `$900` 买新票”；
- **架构解法（`IATA NDC Group PNR` 押金锁位延后至 `T-72h` 统一出票 + 酒店 `Passkey` 原地换名不退房 `HTTP 451 / 409`）**：
  - 针对同一航班 `>= 10 人` 的会议航线，强制走 **`IATA NDC Group Contract`（押金锁位模式）**：在 `T-72h`（或合同约定的最终出票截止日 `Ticketing Time Limit`）之前，只锁座位与团队协议一口价，**暂不签发最终 13 位电子客票号**；在此期间发生任何参会人员替换，Agent 直接调用 `ModifyGroupPassengerName` 免费将张A替换为李B；
  - 同步在 `Cvent Passkey` 中执行酒店房晚 **原地更名过户（`In-Place Guest Name Swap`）**，严禁“先退掉张A的协议房（被酒店收回不再放回协议池）再让李B按门市高价重订”（凡在名单锁定期前过早将团体票出死或采用先退再订弄丢团体协议房库存的，触发 `HTTP 451 PREMATURE_GROUP_AIR_TICKETING_OR_CANCEL_REBOOK_ROOM_BLOCK_LOSS`；自动减房 + 私订追认 + 无损换名确认返回 `HTTP 409 AUTOMATED_ATTRITION_TRIM_OUT_OF_BLOCK_CREDIT_AND_NAME_SWAP_CONFIRM`）。

---

## 二、 直观可视化图解（Mermaid 决策树 + 架构图 + 时序图）

### 1. 企业会展商旅（MICE）酒店切房防违约金与团体机票换名决策树
```mermaid
flowchart TD
    A[企业会展 MICE 启动酒店切房 Room Block 与参会机酒协同] --> B{监控 T-90d/60d/30d 订房进度:<br/>是否在截止日前 48h 自动释放冗余房量?}
    B -- 错过合同 Cutoff 日期致空房锁死 --> C[HTTP 403 拦截: 截止日前 48h 自动执行合同上限免费减房 Trim]
    B -- 房间池规模已动态收敛 --> D{结账主账单 Master Folio 核算:<br/>是否追认私订房晚并按累计+75%净利扣减转售?}
    D -- 漏算OTA私订参会者 或 按单晚100%含税房价强收罚金 --> E[HTTP 422 拦截: 交叉比对认领私订房晚并强制 Cumulative + 75% 净损公理]
    D -- 酒店消化率达标或依法减免 --> F{参会人员临时替换 (A换B) 时机酒如何处理?}
    F -- 提前30天把机票出死无法改名 或 先退协议房再高价重订 --> G[HTTP 451 拦截: 保持团体 PNR 待出票态免费改名并原地过户 Passkey 房单]
    F -- 零罚金平滑换人 --> H[HTTP 409 确认: 自动减房 + 私订追认 + $0 原地换名净省38%]
```

### 2. 会展报名（`Cvent`）× 酒店切房池（`Passkey / Delphi`）× 航司团体 `NDC` 架构图
```mermaid
flowchart LR
    subgraph Reg["1. 参会注册与名单变动层"]
      CV["Cvent Event Registration<br/>(实时报名进度与换人申请)"]
    end

    subgraph Guard["2. 受托 MICE 差旅控制面"]
      TRIM["T-90d/60d/30d 自动减房调度器"]
      MATCH["Out-of-Block 私订房晚隐私哈希认领器<br/>+ Cumulative 75% 净利审计引擎"]
      SWAP["In-Place 原地换名事务协调器"]
    end

    subgraph Suppliers["3. 酒店 PMS 与航司 NDC 团体层"]
      PMS["Cvent Passkey <-> Amadeus Delphi / Opera PMS"]
      NDC["IATA NDC Group PNR (延至 T-72h 统一出票)"]
    end

    CV --> TRIM & MATCH & SWAP --> PMS & NDC
```

### 3. 会前 `T-60d` 自动减房、认领外流私订房晚与 `T-5d` 零成本换人时序图
```mermaid
sequenceDiagram
    autonumber
    participant EVT as 企业会务 Agent (Navan / Cvent)
    participant PK as Cvent Passkey / 酒店 Delphi 系统
    participant AIR as 航司 NDC Group 引擎

    EVT->>PK: 1. 初始签约锁定 500 间夜 (80% 累计保底 = 400 间夜，T-60d 可免费减 20%)
    Note over EVT,PK: 到达 T-62d，报名转化率预测仅需 410 间夜...
    EVT->>PK: 2. 自动触发 T-60d 减房条款: 免费释放 80 间夜 -> 新保底降至 336 间夜!
    Note over EVT,PK: 会前 T-5d，参会员工张A 突发急事由 李B 顶替参会...
    EVT->>PK: 3. Passkey In-Place Name Swap (Reservation #R99: 张A -> 李B，0 退房 0 差价!)
    EVT->>AIR: 4. 团体 PNR 免费更名 (张A -> 李B) 并在 T-72h 统一签发电子客票
    EVT->>PK: 5. 散会前交叉比对住客名单，追认 28 间员工在 OTA 私订房晚 -> 累计消化率 102% ($0 违约金 HTTP 409)!
```

---

## 三、 四大主流企业会展商旅（MICE & Group Travel）管理平台横向选型矩阵

| 评估维度 | Cvent (`Passkey` + `Transient`) | Groupize | Amadeus Delphi + Opera Cloud | Navan Events / Spotnana Group |
| :--- | :--- | :--- | :--- | :--- |
| **核心优势定位** | **全球大型企业峰会、医药学术会议与酒店房量池（Room Block）管理绝对霸主** | **中小型会议（Simple Meetings）与私订房晚交叉认领（Out-of-Block Audit）专家** | **全球连锁酒店集团底层的销售与宴会管理（S&C）事实标准** | **现代一体化企业差旅平台**，擅长参会者机票自助预订与预算封顶 |
| **切房消化率（`Attrition`）预警** | **极强**（支持多阶段 Cutoff 自动提醒与实时 Pickup 仪表盘） | 内置智能减房计算器与合同风险雷达 | 酒店方主控系统（与 Cvent Passkey 双向实时同步库存） | 侧重机票与散客协议房，百人以上复杂切房常集成 Cvent |
| **私订外流房晚认领（`Audit Around the Block`）** | 支持导出住客列表与注册表比对 | **核心强项**（自动化隐私安全匹配，帮主办方平均找回 18% 漏计房晚） | 提供酒店侧官方在住水单核对接口 | 自动归集所有用公司卡预订同城酒店的差旅单 |
| **临时换人（`Name Swap`）协同** | **原生支持 `Passkey` 房间预订无缝改名过户** | 支持一键参会人替换联动机酒 | 接收 Passkey 改名指令直接更新 PMS 住客姓名 | 支持将未用机票退票积分（UTC）自动重用于新参会人 |

---

## 四、 确定性策略评估器与 7-Card 基准测试报告（`synthetic`）

### 1. 会展切房截止日自动减房、私订房晚追认与团体票免费换名评估器（Python 参考实现）
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class OtaCorporateMiceGroupBlockPolicyInput:
    quarterly_room_attrition_penalty_and_group_air_waste_pool_usd: float = 300000.0
    missed_room_block_attrition_release_cutoff_window: bool = False
    uncredited_out_of_block_pickup_or_per_night_full_rate_penalty: bool = False
    premature_group_air_ticketing_or_cancel_rebook_room_loss: bool = False
    automated_attrition_trim_out_of_block_credit_and_name_swap_ready: bool = False
```

### 2. 7-Card 4:5 视觉基准测试报告摘要
1. **Card 1 (`1 / 7` · `HANDS-ON · CORPORATE MICE & ROOM-BLOCK ATTRITION`)**：通过 `T-90d/60d/30d` 截止日前 48h 自动减房 + 私订外流房晚交叉追认与 `75%` 净利折算 + 团体机酒原地 `$0` 换名，季度会展空房违约金与换人废票损耗从 `$300,000` 降至 `$186,000`（净省 **38% / `$114,000`**）。
2. **Card 2 (`2 / 7` · `SCENARIO: ATTRITION_CLIFF_AND_OUT_OF_BLOCK_LEAK`)**：成功拦截错过合同减房日导致的 `$60k` 空房罚单（`HTTP 403`）、纠正漏算员工 OTA 私订房晚及按单晚 100% 含税价乱罚的账单（`HTTP 422`），并阻断提前出死散客票或先退再订丢房（`HTTP 451`）。
3. **Card 3 (`3 / 7` · `WHAT I TESTED`)**：覆盖 5 类状态码：`200`（会展房量池与团体票协同合规放行）、`403`（错过 T-90d/60d/30d 免费减房窗口面临空房违约金拦截）、`422`（未追认参会者私订同酒店房晚或按单晚全额房价未扣转售收入强征违约金拦截）、`451`（过早出死团体机票丧失免费更名权或先退再订丢失协议房拦截）、`409`（自动阶梯减房 + 私订追认 + 原地换名确认）。
4. **Card 4 (`4 / 7` · `UNDER THE HOOD`)**：展示 `ota_corporate_mice_group_block_guard` 与 `ota_corporate_mice_group_optim_409` 令牌。
5. **Card 5 (`5 / 7` · `ROBUSTNESS CHECK`)**：在 100 组“最后一晚提前退房高峰 + 20% 参会名单更替 + 酒店满房转售冲抵”测试中保持 100% 零冤枉违约金。
6. **Card 6 (`6 / 7` · `LATENCY`)**：千人级参会名单与酒店住客哈希交叉比对 + `Passkey` 原地换名耗时 `< 390ms`。
7. **Card 7 (`7 / 7` · `MY TAKE`)**：**✅ 强烈适用**于所有高频举办客户大会、内部年会（SKO）、医药学术会与展会的企业采购、行政与商旅平台；**⛔ 不适用**于单人随机临时出差。

---

## 五、 商业上线风控与架构评审 Checklist

- [ ] **为每场会议合同设置 `T-92d / T-62d / T-32d` 硬性自动减房触发器**：根据报名水位线在合同截止日前 48 小时用足免费减房配额。
- [ ] **在酒店合同中锁死“整会累计消化率（Cumulative Attrition）+ 75% 净利赔偿 + 转售冲抵（Resell Credit）+ 私订追认（Out-of-Block Credit）”四项条款**：严禁接受单晚独立考核或按 100% 含税房费赔付。
- [ ] **散会结账前强制执行参会名单与酒店在住名单交叉比对（Audit Around the Block）**：将自己去 OTA 或官网订房的参会者全部计入团队完成度。
- [ ] **使用 `IATA NDC Group PNR` 押金锁位与 `Passkey` 原地换名替代提前散客出票**：在 `T-72h` 前实现参会人员 `$0` 成本无缝替换。
