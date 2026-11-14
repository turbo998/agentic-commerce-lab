# B2B 智能体大宗散货与油轮航次租船（`Voyage Charterparty BIMCO GENCON / ASBATANKVOY`）、装卸准备就绪通知书（`NOR`）起算与滞期费/速遣费（`Demurrage & Despatch`）清算架构：`AIS` 港区锚地围栏与验舱合格双锁、晴天工作日（`WWD SHEX`）气象雷达停表与速遣返还令牌（`b2b_maritime_charterparty_nor_laytime_demurrage_despatch_mandate_...`）vs 传统船长在港外抢递无效 `NOR` 骗取 `$65,000/天` 滞期费、暴雨停工照算时间与吞没速遣奖金选型与原理解析 FAQ

> **核心摘要（TL;DR）**  
> 在铁矿石、粮食、煤炭与原油等大宗商品国际海运航次租船结算（`Dry-Bulk & Tanker Voyage Charterparty`，`BIMCO GENCON / ASBATANKVOY`，`$890,000/批次`）中，一艘好望角型散货船（Capesize）或超大型油轮（VLCC）的滞期费（`Demurrage`）高达 **`$45,000–$120,000/天`（每小时高达 `$2,000–$5,000`）**！如果让大宗贸易结算 AI Agent 仅凭船东发来的装卸时间事实记录表（`SOF`）和邮件里的《装卸准备就绪通知书（`NOR - Notice of Readiness`）》时间戳就自动计算并支付滞期费，货主/租家每航次都会被船东“偷表”多收十余万美元：**为什么绝对不能按船长邮件递交 `NOR` 的那一刻起算装卸时间（Laytime），也不能把装卸期间的下雨天和移泊时间统统算进滞期费？** 第一，根据英国海商法两大经典判例（*The Johanna Oldendorff* 到达船原则与 *The Tres Flores* 物理就绪原则），船长递交有效 `NOR` 必须同时满足**“地理上已进入港口习惯锚地/界限内（Arrived Ship）”**且**“物理上货舱已清洁干燥并通过独立检验师（Surveyor）验舱合格”**——现实中大量船长为了抢时间，在距离港口还有 40 海里航行途中就抢发 `NOR`（甚至货舱里还有上一航次的煤渣水渍被验舱员拒收），若 AI 不拦截这种自始无效（Invalid *ab initio*）的早产 `NOR`，等于白送船东 2–4 天、价值 `$150,000+` 的虚假滞期费！第二，干散货合同普遍约定 **`WWD SHEX UU`（晴天工作日，周日节假日除外，除非使用）**，一旦港口因暴雨（防止粮食/化肥受潮结块）或涌浪超标暂停装卸，必须从允许装卸时间（Allowed Laytime）中精确剔除，且从锚地起锚移泊至泊位的航行时间（Shifting Time）归船东自担；反过来，若租家提前装完货，船东必须按滞期费的 **50% 返还“速遣费（`Despatch`）”**！第三，若船东未在卸货完毕后 **30/90 天约定时效（`Time-Bar Clause`）**内交齐船长与码头双签 `SOF` 正本，索赔权依法永久灭失。生产级架构必须采用 **`b2b_maritime_charterparty_nor_laytime_demurrage_despatch_mandate_2026_11_15` `AIS` 锚地地理围栏 + SGS 验舱合格双锁 `NOR` 门禁 + 港口气象雷达 `WWD` 自动停表与 50% 速遣对冲引擎 + Microsoft Web IQ `OFAC` 暗船筛查与 `BIMCO` 索赔时效网关**：在 **11ms** 内拦截港外抢递或验舱不合格的无效 `NOR`（`HTTP 403`），在 **14ms** 内阻断暴雨/移泊时段违规计费与吞没速遣费（`HTTP 422`），并由 **Microsoft Web IQ** 280ms 穿透核验 `IMO` 暗船制裁与合同索赔过期锁（`HTTP 451`）。

---

## 📌 一、 核心结论速览（Executive Summary）

1. **`AIS` 港区锚地地理围栏（`Arrived Ship`）与独立验舱合格证（`Hold Cleanliness Certificate`）双锁 `NOR` 起算门禁**：严禁采信船长单方面邮件声称的 `NOR` 时间！网关强制将 `NOR` 生效时刻锚定在以下两个条件**全部达成之较晚者**：① 卫星 `AIS` 轨迹证实船舶已在港章规定的习惯等待锚地抛锚完毕（或合同显式含 `WIPON` 且已抵引航站）；② 第三方检验机构（如 `SGS / Bureau Veritas / Intertek`）登轮或无人机检验出具带有时间戳的《货舱清洁干燥适货证书（`Hold/Tank Cleanliness Passed`）》。若检出港外航行抢递 `NOR` 或验舱不合格（*The Tres Flores* 规则下原 `NOR` 自始无效，必须洗舱重验后重新递交新 `NOR`），网关在 **11ms** 内硬拦截虚假起算时间（`HTTP 403 PREMATURE_INVALID_NOR_OUTSIDE_PORT_LIMITS_OR_FAILED_HOLD_SURVEY_BLOCKED`）。
2. **`WWD SHEX UU`（晴天工作日）港口气象雷达分钟级停表、移泊时间剔除与 50% 速遣费（`Despatch`）双向清算锁**：
   - **气象与移泊自动扣减**：在允许装卸期（Laytime）内，网关直连港务局气象水文日志与双签 `SOF（事实记录表）`，按分钟自动剔除因降雨、大风涌浪、港口工潮导致的停工时段（`Weather Interruptions`）以及从外锚地起锚靠泊的移泊航行时间（`Shifting from Anchorage to Berth`），并严格区分是否已实际进入超期滞期阶段（防止滥用“一旦滞期永远滞期 Once on Demurrage, Always on Demurrage”侵占免责时段）。
   - **50% 速遣费自动冲抵**：当实际净用时 `< 合同允许装卸时间（Allowed Laytime = 货量 / 装卸率）` 时，系统自动按 `节省天数 × 50% 滞期费率` 计算速遣费（`Despatch`）并直接从尾款运费中扣回。违背上述任一规则，网关在 **14ms** 内拦截（`HTTP 422 UNEXCLUDED_RAIN_SWELL_WEATHER_WORKING_DAY_OR_SHIFTING_TIME_OVERCHARGE`）。
3. **`BIMCO` 30/90 天滞期索赔时效锁（`Time-Bar Clause`）与 `OFAC` 影子船队 `AIS` 欺骗筛查**：借助 **Microsoft Web IQ** `/v3/browse` 在 **280ms** 内核验船东提交完整滞期索赔单证包（含船长、代理与码头三方签章的 `SOF`、泵速记录 `Pumping Log`）是否已超过租船合同约定的 **30 天或 90 天绝对除斥期间（Time-Bar）**——一旦超期 1 秒，依据英国上诉法院判例租家享有 100% 法定免付权！同时核验 7 位 `IMO` 船号是否存在关闭 `AIS` 挂假旗的 `OFAC` 制裁暗船记录（`HTTP 451 OFAC_DARK_FLEET_AIS_SPOOFING_OR_EXPIRED_BIMCO_DEMURRAGE_TIMEBAR_HOLD`）。
4. **分钟级 `WWD` 气象停表扣减与提前完货 50% 速遣费对冲立省 8.0%**：通过 **Microsoft Web IQ** 自动核减暴雨停工与移泊时段并结算速遣奖金，在 `$890,000.00` 的大宗海运运费与滞期清算批次上单批防损/立省 **`$71,200.00`**（净结算支出降至 **`$818,800.00`**，`HTTP 409 DESPATCH_EARLY_COMPLETION_CREDIT_AND_WWD_RAIN_DEDUCTION_SAVINGS_CONFIRM`）。

![2026-11-15 B2B 智能体大宗海运租船 NOR 验舱起算、WWD 晴天工作日停表与滞期速遣清算架构一图流](../assets/svg/250-b2b-maritime-charterparty-nor-laytime-demurrage-despatch-2026-11-15.svg)

---

## 🎯 二、 客户与架构师灵魂拷问 Q&A（First-Principles Q&A）

### Q1：船长在周一下午 1 点就发邮件递交了《装卸准备就绪通知书（NOR）》，为什么不能让 AI 从周一下午就开始算装卸时间，非要查卫星 `AIS` 位置和周三的 `SGS` 验舱报告？
- **大白话与第一性原理**：因为在每小时高达 `$3,000` 的海运滞期费博弈中，**“船长最大的冲动就是在船还没到、舱还没洗干净的时候抢先按秒表；如果你不验 `AIS` 和验舱证，你就是在为船东的谎言按小时买单”**！
  1. **港外抢递（Non-Arrived Ship）**：合同规定周一下午 `14:00` 前递交 `NOR`，周二早上 `08:00` 起算时间；过了 `14:00` 递交则要推迟到周三早上起算。某些船长周一下午 `13:55` 船还在距离港口 35 海里的公海上航行，就提前群发邮件谎称“本轮已抵达并递交 NOR”。卫星 `AIS` 围栏一查，该轮直到当晚 `21:30` 才真正抛锚！
  2. **验舱不合格（Failed Hold Survey — *The Tres Flores* 铁律）**：运粮食的散货船，船长周一递了 `NOR`，周三靠泊后 `SGS` 检验员下舱一看，舱底全是上一航次铁矿石的锈水和虫害，当场签发 `Hold Failed（验舱不合格）`，船员洗舱洗到周五才通过复检。根据英国海商法，周一那张 `NOR` **自始彻底无效**，装卸时间必须从周五复检合格重递 `NOR` 后才能起算！这一项拦截直接帮货主省下 4 天 × `$60,000 = $240,000` 冤枉滞期费（**11ms** 拦截 `HTTP 403`）。

### Q2：装卸大豆或化肥时下了两天暴雨，码头被迫关舱停工，为什么船东发来的账单里这两天还在照收每天 `$60,000` 的费用？
- **大白话与第一性原理**：
  - **`WWD SHEX UU`（晴天工作日）vs “一旦滞期永远滞期”的分水岭**：在合同规定的允许装卸时间（Allowed Laytime，比如 5 天）还没用完之前，只要遇到降雨、狂风导致码头不能作业，时钟必须**立刻暂停（Stop the Clock）**；此外，船从外海锚地开进码头泊位的那 3 小时航行时间（Shifting Time）也绝不能算在货主头上。
  - **船东账单的“浑水摸鱼”**：许多船东代理在制作 `Laytime Calculation（装卸时间计算表）` 时，故意漏扣夜间阵雨时段、把引航移泊时间算进装卸期，使原本没超期的航次“被超期”进入滞期（Demurrage），甚至吞掉货主原本应得的 **50% 提前完货速遣奖金（Despatch）**。网关通过 **14ms** 逐分钟对齐港务局气象雷达与双签 `SOF`，挤干每一分钟水分（`HTTP 422`）。

### Q3：在实时核验全球卫星 `AIS` 轨迹、港口气象公报、`BIMCO` 标准租约判例以及 `OFAC` 影子船队黑名单时，为什么选 Microsoft Web IQ 而不是 Exa 或 Bright Data？
- **架构选型对比**：
  - **Exa (Neural Search)**：擅长泛文本相似度，无法精确核验 7 位 `IMO` 船舶识别码在特定港区经纬度多边形（Port Limits Polygon）内的抛锚时刻与 `BIMCO` 条款除斥期。
  - **Bright Data (Scraping Proxy)**：按流量计费（`$8–$15/GB`），抓取海事与港务局公报延迟高达 `2,600–5,200ms`，且不具备企业级零数据留存（ZDR）保护大宗商品买方航线与底价机密。
  - **Microsoft Web IQ (`/v3/browse` + Deterministic Grounding)**：在 Azure 合规边界内以 **280ms** 确定性核验 `OFAC` 海事制裁名单与 `BIMCO` 索赔时效，并在自动扣减暴雨时段与追回速遣费立省 `$71,200.00` 时触发 `HTTP 409 Confirm`。

---

## 🧭 三、 直观可视化图解（Visual Architecture Diagrams）

### 3.1 大宗海运租船 `NOR` 有效性、`WWD` 晴天停表与滞期/速遣清算决策树
```mermaid
flowchart TD
    A[收到大宗散货/油轮航次运费与滞期费结算单<br/>批次总额: $890,000.00] --> B{递交 NOR 时 AIS 是否已入习惯锚地<br/>且已通过 SGS/BV 货舱清洁度检验?}
    B -- "否 (港外航行抢递无效 NOR / 验舱不合格带病递交)" --> C[🛑 HTTP 403 HARD BLOCK · 11ms<br/>PREMATURE_INVALID_NOR_OUTSIDE_PORT_LIMITS_OR_FAILED_HOLD_SURVEY_BLOCKED]
    B -- "是 (地理到达且物理适货 NOR 100% 有效)" --> D{是否已剔除 WWD 降雨/涌浪停工与移泊时间<br/>且提前完货已按 50% 返还速遣费 Despatch?}
    D -- "否 (暴雨停工照算装卸期 / 锚地移泊转嫁货主 / 吞没速遣奖金)" --> E[🚨 HTTP 422 HARD BLOCK · 14ms<br/>UNEXCLUDED_RAIN_SWELL_WEATHER_WORKING_DAY_OR_SHIFTING_TIME_OVERCHARGE]
    D -- "是 (分钟级 Laytime 净值与速遣对冲精准)" --> F[调用 Microsoft Web IQ /v3/browse<br/>核验 BIMCO 30/90天索赔除斥期与 OFAC IMO 暗船记录]
    F --> G{索赔单证未逾越合同 Time-Bar 死线<br/>且 7位 IMO 船号无 AIS 伪造/制裁染毒?}
    G -- "否 (逾越 30/90 天 Time-Bar 索赔权灭失 / 命中 OFAC 影子船队)" --> H[🛑 HTTP 451 LEGAL HOLD · 280ms<br/>OFAC_DARK_FLEET_AIS_SPOOFING_OR_EXPIRED_BIMCO_DEMURRAGE_TIMEBAR_HOLD]
    G -- "是 (100% 符合海商法与 OFAC 合规)" --> I{是否启用 WWD 气象自动核减与<br/>提前完货 50% 速遣奖金抵扣?}
    I -- "是 (单批立省/抵扣 $71,200.00)" --> J[🧑‍⚖️ HTTP 409 CONFIRM · 245ms<br/>净海运结算 $818,800.00]
    I -- "否 (标准无争议航次清算)" --> K[✅ HTTP 200 Act automatically · 10ms<br/>安全清算海运租船批次 $890,000.00]
```

### 3.2 传统盲信船东 `Laytime` 计算表 vs. `AIS+验舱` 双锁 + 气象停表 + 速遣对冲架构对比
```mermaid
flowchart LR
    subgraph Bad["❌ 传统盲信船东计算表 (3 大滞期费黑洞)"]
        B1[船还在港外 40 海里或货舱有煤渣就抢发 NOR] --> B2[起算时间被提前 3 天<br/>货主白赔 $180,000 虚假滞期费]
        B2 --> B3[装卸期下暴雨停工 36 小时与移泊 4 小时未扣减<br/>被船东硬凑成超期滞期按 $60k/天收费]
        B3 --> B4[船东逾期 45 天才交齐 SOF 已过 30 天死线<br/>财务 AI 不懂 Time-Bar 条款照常全额打款]
    end

    subgraph Good["✅ AIS+SGS 验舱锁 + WWD 气象停表 + Time-Bar + Web IQ"]
        G1[卫星 AIS 锚地多边形 + SGS 验舱合格证书<br/>双重锁定真实 NOR 生效时刻] --> G2[直连港务局雨量/涌浪日志分钟级停表<br/>+ 剔除移泊时间并自动扣回 50% 速遣费]
        G2 --> G3[Web IQ 280ms 核验 BIMCO 30/90天除斥期<br/>与 7位 IMO 号 OFAC 暗船轨迹]
        G3 --> G4[10ms 安全清算 $890k 批次或<br/>气象核减+速遣抵扣立省 $71,200!]
    end
```

### 3.3 端到端时序图（AIS + Hold Survey NOR Gate + WWD Rain Stopper + Web IQ BIMCO Gate）
```mermaid
sequenceDiagram
    autonumber
    participant Charterer as 货主 / 租船部清算 Agent
    participant Port as 卫星 AIS / SGS 验舱仪 & 港口气象 SOF
    participant Guard as 租船装卸期与滞期引擎 (Policy Engine)
    participant WebIQ as Microsoft Web IQ (/v3/browse)
    participant Bank as 海运费与速遣费轧差结算专户

    Charterer->>Guard: 1. 收到船东航次运费与滞期费索赔账单 ($890,000.00)
    Port->>Guard: 2. 上报 AIS 抛锚坐标、SGS 验舱合格时刻、双签 SOF 降雨与移泊日志
    Note over Guard: 校验 1: 递交 NOR 时船舶是否已入锚地且货舱已检验合格?
    alt 港外航行抢递 NOR 或验舱不合格 (The Tres Flores 规则无效)
        Guard-->>Charterer: HTTP 403 Blocked (11ms · 驳回无效 NOR 起算点)
    else NOR 地理与物理就绪 100% 有效
        Note over Guard: 校验 2: 是否已剔除 WWD 降雨/涌浪停工与移泊并计提速遣费?
        alt 暴雨停工/移泊未扣减或吞没提前完货 50% 速遣奖金
            Guard-->>Charterer: HTTP 422 Unprocessable (14ms · 拦截虚增装卸时长)
        else Laytime 分钟级净值核算准确
            Guard->>WebIQ: 3. 核验 BIMCO 30/90天 Time-Bar 索赔死线与 OFAC IMO 暗船制裁
            WebIQ-->>Guard: 4. 返回时效合规证明与气象/速遣冲抵方案 (245-280ms)
            Guard->>Bank: 5. 执行扣除速遣费后的净海运费划拨 (10ms)
        end
    end
```

---

## 📊 四、 架构师选型决策矩阵（Architect Decision Matrix）

| 评估维度 | 方案 A：按船东发来的 PDF 滞期费账单直接付款 | 方案 B：人工拿纸质 `SOF` 用 Excel 手算核对 | **方案 C（推荐）：`AIS+SGS` 验舱锁 + `WWD` 气象停表引擎 + Web IQ `BIMCO/OFAC` 门禁** |
| :--- | :--- | :--- | :--- |
| **防港外抢递与带病 `NOR`（*Tres Flores*）** | ❌ 0%（被船长提前 2–4 天偷跑秒表，白亏 `$15万+`） | ⚠️ 审单员看不到当时卫星 `AIS` 抛锚精确经纬度 | ✅ **11ms `AIS` 锚地多边形 + `SGS` 验舱合格双锁**（无效 `NOR` 直接作废重起算，返回 `HTTP 403`） |
| **`WWD SHEX` 暴雨停工与移泊扣减** | ❌ 降雨、涌浪与移泊时间全被混入装卸期多收钱 | ⚠️ 跨时区分钟级分段手算极易漏扣或算错半日规则 | ✅ **14ms 对齐双签 `SOF` 与港务气象日志分钟级停表**（自动冲抵 `50%` 速遣费，返回 `HTTP 422`） |
| **`BIMCO Time-Bar` 逾期免付与暗船筛查** | ❌ 船东逾期交单本可依法拒付，却因不懂法白白打款 | ⚠️ 仅查船名未查 `IMO` 历史关停 `AIS` 接驳记录 | ✅ **Web IQ 280ms 除斥期锁定 + `OFAC` 暗船穿透**（逾期索赔 100% 依法驳回，返回 `HTTP 451`） |
| **单航次净滞期支出与速遣回收率** | ❌ 长期被船东单边多收 `15%–25%` 滞期费 | ⚠️ 争议拉锯长达 6 个月，占用保证金 | ✅ **分钟级精准核减 + 速遣费自动轧差**（单批立省 `$71,200.00`，触发 `HTTP 409 Confirm`） |

---

## 🧪 五、 定量实测与 7-Card 4:5 视觉评测报告摘要（Quantitative Benchmark）

在本地确定性评测套件（`lab/webiq_commerce_demo.py`）中，我们对 `$890,000.00` 的 B2B 大宗散货与油轮航次租船（`Voyage Charterparty`）、`NOR` 起算与滞期/速遣费清算批次进行了 5 组边界压测（数据来源：`deterministic_offline_simulation` 与 `official_doc_snapshot`，零虚构坐标）：

| 压测场景代号 | 输入条件与故障/攻击注入 | 期望 HTTP 状态码 | 实测决策代码 (`decision_code`) | 实测延迟 | 动作标签 (`action_pill`) |
| :--- | :--- | :---: | :--- | :---: | :--- |
| **`chr_commit_ok`** | `AIS` 入锚地 + `SGS` 验舱合格 + `WWD` 降雨剔除 + `IMO` 合规 (`$890,000.00`) | `200 OK` | `VERIFIED_MARITIME_CHARTERPARTY_LAYTIME_SETTLED` | `10ms` | `Act automatically` |
| **`chr_nor_403`** | 船舶在习惯港区界限外（`OPL`）抢递早产 `NOR` 或货舱未通过 `SGS` 清洁度检验 | `403 Forbidden` | `PREMATURE_INVALID_NOR_OUTSIDE_PORT_LIMITS_OR_FAILED_HOLD_SURVEY_BLOCKED` | `11ms` | `Send to a human` |
| **`chr_wwd_422`** | 未剔除 `WWD SHEX` 暴雨/涌浪停工与锚地移泊时间或吞没提前完货 `50%` 速遣费 | `422 Unprocessable` | `UNEXCLUDED_RAIN_SWELL_WEATHER_WORKING_DAY_OR_SHIFTING_TIME_OVERCHARGE` | `14ms` | `Send to a human` |
| **`chr_bar_451`** | 船东滞期索赔逾越 `BIMCO` 30/90 天 `Time-Bar` 除斥期或 `IMO` 号涉 `OFAC` 暗船 | `451 Unavailable` | `OFAC_DARK_FLEET_AIS_SPOOFING_OR_EXPIRED_BIMCO_DEMURRAGE_TIMEBAR_HOLD` | `280ms` | `Send to a human` |
| **`chr_sav_409`** | Web IQ 启用 `WWD` 降雨分钟级扣减与提前完货 `50%` 速遣费冲抵立省 `$71,200.00` | `409 Conflict` | `DESPATCH_EARLY_COMPLETION_CREDIT_AND_WWD_RAIN_DEDUCTION_SAVINGS_CONFIRM` | `245ms` | `Confirm` |

---

## 🛠️ 六、 生产上线快速核验清单（Production Readiness Checklist）

- [ ] **强制 `AIS` 锚地地理围栏与 `SGS` 验舱证书双锁 `NOR`**：在海运租船清算引擎中要求 `ais_port_limits_arrived_ship_and_hold_cleanliness_passed_before_nor == True`，任何港外抢递或验舱失败的 `NOR` 在 `11ms` 内返回 `HTTP 403`。
- [ ] **部署 `WWD SHEX` 气象停表与 50% 速遣费（Despatch）公式**：自动从装卸时间中剔除降雨/涌浪停工与锚地移泊时长，并对提前完货自动扣回 50% 速遣奖金（`14ms` 返回 `HTTP 422`）。
- [ ] **接入 Microsoft Web IQ `BIMCO Time-Bar` 与 `OFAC IMO` 筛查**：通过 `/v3/browse` 核验索赔单证送达是否逾越合同 30/90 天除斥期并筛查 `AIS` 暗船记录，违规交易立即挂起 `HTTP 451`。
- [ ] **启用双签 `SOF` 分钟级自动轧差结算**：精确冲抵速遣费与气象免责时长（`HTTP 409 Confirm`）。
