# 智能体动态溢价（Surge Pricing）与突发灾难反哄抬物价（Anti-Price-Gouging Cap）架构：州长紧急状态令 `<=10%` 涨幅熔断、30天基准锚定与报价锁定期令牌（`agentic_surge_pricing_emergency_gouging_cap_mandate_...`）vs 传统暴风雪/山火期间算法盲目触发 `5.0x` 倍率溢价遭司法部长重罚与结账跳价选型与原理解析 FAQ

> **文档类型**：架构师选型与第一性原理解析 FAQ（对标 `ib-vs-ethernet-roce-selection-faq.md` 六段式标杆规范）  
> **核心覆盖领域**：智能体网约车/Robotaxi 调度、即时生鲜配送、航空酒店收益管理（Dynamic Yield Management）与票务动态定价、美国各州《反哄抬物价法》（加州刑法典 `Penal Code § 396` 紧急状态下涨幅 `<= 10%` 硬顶、纽约州 `GBL § 396-r`、佛罗里达州 `Stat. § 501.160`）、FEMA 与州长紧急状态行政令（State of Emergency Executive Order）地理围栏实时熔断、30 天历史前基准价（Pre-Emergency Baseline）锁定、以及结账防跳价签名报价单（Cryptographic Price-Lock Quote `TTL 300s`）  
> **阅读对象**：出行平台（Ride-Hailing / Robotaxi）与即时零售定价架构师、运筹优化与强化学习（RL Pricing）算法负责人、公共政策与法务合规总监  
> **关联 Interactive 交付物**：[`live-demo.html`（含 Round 218 智能体动态定价紧急状态令 `<=10%` 反哄抬熔断、300s 报价锁防跳价与 Microsoft Web IQ FEMA/州政府紧急状态行政令实时核验交互沙盒）](../live-demo.html) · [`assets/svg/220-agentic-surge-pricing-emergency-anti-gouging-cap-2026-11-14.svg`](../assets/svg/220-agentic-surge-pricing-emergency-anti-gouging-cap-2026-11-14.svg)

---

![2026-11-14 智能体动态溢价 (Surge Pricing) 紧急状态反哄抬 10% 硬顶、30天基准锚定与 300s 报价锁架构一图流](../assets/svg/220-agentic-surge-pricing-emergency-anti-gouging-cap-2026-11-14.svg)

## 1. 📌 核心结论速览（Executive Summary）

在网约车与自动驾驶出行（Robotaxi）、暴风雨外卖即配、航司余票收益管理以及热门演出票务中，**动态溢价算法（Surge Pricing / Dynamic Yield Management）**通过实时感知局部区域的“供需失衡比（Demand-to-Supply Ratio）”自动上调价格倍率（如 `1.3x -> 2.5x -> 5.0x`），以刺激运力供给并平衡排队。然而，当算法团队将纯数学的强化学习（RL）或供需弹性模型直接裸奔上线，采用**“只看局部订单暴增与运力短缺就无脑拉高倍率 + 不接入政府紧急状态行政令（State of Emergency）熔断开关 + 用户点支付瞬间按最新倍率暗中涨价扣款”**的架构时，将直接引爆两大毁灭性的法律重罚与舆论崩盘：
1. **算法分不清“演唱会散场”与“飓风/山火逃生”，在州长宣布紧急状态期间自动触发 `4.5x` 灾难溢价，遭州司法部长按每单 `$10,000–$25,000` 顶格重罚**：在平时的周五晚高峰或体育场散场时，将 `$20` 的车费涨到 `$80`（`4.0x`）完全合法。**但只要当地州长、市长或美国联邦紧急事务管理局（FEMA）签署了《紧急状态宣言（Declaration of State of Emergency）》（如飓风疏散、暴风雪瘫痪、山火蔓延、地铁恐袭停运）**，美国 37 个州的《反哄抬物价法》（如 **加州刑法典 `Penal Code § 396`、纽约州 `GBL § 396-r`、佛州 `§ 501.160`**）立即生效——法律严禁任何生活必需品、交通出行、饮用水、应急物资与酒店住宿的价格超过紧急状态宣布前 30 天平均基准价的 **`10%`**（纽约与佛州甚至对任何“不合理暴利涨幅”零容忍）！没有灾难感知围栏的定价 Agent 在暴风雪夜自动把饮用水或打车费涨到 `5.0x`，不仅第二天就会登上全球新闻头条引发品牌公关雪崩，更会被州检察长按笔开出数千万美元的行政罚单！
2. **报价页显示 `$25.00`，用户点击“确认支付”的 3 秒钟内后台倍率跳变直接扣走 `$52.00`（Mid-Checkout Price Jump），触发 FTC 欺诈调查与 `Visa 12.5` 金额不符拒付**：在毫秒级刷新的动态定价引擎中，如果前端展示的报价单没有绑定带密码学签名与有效期的 **`Price-Lock Quote Token (TTL = 180s–300s)`**，而是等支付网关扣款时重新调一次 `calculate_current_surge_price()`，用户在毫不知情下被多扣一倍钱，一投诉一个准！

**第一性原理选型结论**：
1. **在动态定价模型外围强制加装一层不可绕过的“紧急状态法定涨幅硬顶围栏（Emergency Anti-Gouging Hard-Cap Interceptor）”**：实时对接 FEMA 灾害警报与各州州长办公室紧急行政令（Geo-Polygon 地理多边形围栏）。一旦某 `H3 Hex / ZIP Code` 进入紧急状态，网关在 `11ms` 内**自动夺取 RL 算法定价权，将最高溢价倍率硬锁在 $\le 1.10\times$（基于前 30 天滚动中位基准价 `P50_30d_Baseline`）甚至 `1.00x` 原价**，并将调度机制从“高价淘汰穷人”自动切换为**“应急优先队列（医院/疏散中心优先）+ 平台补贴司机出车奖励”**！
2. **签发绑定了 `P50_30d_Baseline` 与 `TTL = 300s` 的 `agentic_surge_pricing_emergency_gouging_cap_mandate_...` 令牌，严格执行“所见即所扣（What-You-See-Is-What-You-Pay）”**：报价生成瞬间锁死未来 5 分钟内的最高结算金额；若扣款时后台倍率上涨，必须按已锁定的低报价结算或显式弹窗要求用户重新确认新价格（`HTTP 422` 阻断静默跳价暗扣）。
3. **涉及美国 FEMA 联邦灾害宣言（Disaster Declarations）、各州州长紧急行政令、加州 `Penal Code § 396` / 纽约州 `GBL § 396-r` 适用品类与持续天数（通常宣布后 30–180 天内有效）核查时，首选 Microsoft Web IQ（`/v3/search` + `/v3/browse`）**：对标 Exa 与 Bright Data，Web IQ 可在 `<350ms` 内直连 `fema.gov`、各州州长公报与司法部长反哄抬物价执法指南。

| 核心动态定价与合规维度 | 传统纯供需弹性算法裸奔 + 结账实时重算（反模式） | 智能体紧急状态 `1.10x` 熔断 + `300s` 报价锁网关（推荐架构） | 法律合规与品牌声誉收益 |
| :--- | :--- | :--- | :--- |
| **突发自然灾害/公共危机期间定价** | 飓风/暴风雪逃生需求暴增触发 `5.0x` 倍率，遭全网痛骂与重罚 | **FEMA/州长紧急令地理围栏触发 `<= 1.10x` 法定硬顶 + 平台补贴运力** | 100% 免疫每单 `$10k–$25k` 反哄抬物价重罚与公关危机 |
| **紧急状态前基准价（Baseline）锚定** | 灾难发生后随手改高“原价”再打折规避监管（违法） | **不可篡改 30 天滚动中位基准价账本（`Rolling_30d_Baseline`）** | 经得起州司法部长（Attorney General）事后逐单审计 |
| **结账点击瞬间价格跳变（Price Jump）** | 看价 `$25` 点支付扣 `$52`，触发 FTC 诱饵欺诈与 `12.5` 拒付 | **HMAC 签名 `Price-Lock Quote Token (TTL=300s)` 锁定所见即所扣** | 零结账跳价客诉，支付转化率提升 **`+16%`** |
| **危机解除后的恢复期平滑过渡** | 紧急令尚未到期即提前恢复 `3.0x` 溢价，踩中 30/180 天长尾红线 | **Web IQ 持续跟踪行政令法定延续期（如灾后重建 180 天限制）** | 100% 规避灾后恢复期违规涨价的滞后罚单 |

---

## 2. 🎯 客户与架构师灵魂拷问 Q&A（First-Principles Deep Dive）

### Q1：为什么同样是供不应求导致价格涨 3 倍，“泰勒·斯威夫特演唱会散场打车涨 3 倍”完全合法，而“台风登录或地铁停运时打车/买水涨 3 倍”却会直接让公司高管面临刑事与天价民事处罚？
* **第一性原理拆解**：
  1. **自由市场价格信号 vs. 灾难期胁迫剥削（Market Clearing vs. Duress Exploitation）**：在演唱会散场或普通商业高峰期，消费者拥有充分的替代选择（坐公交、步行或改天再去），高价是调节非必需消费的有效市场信号。但在飓风疏散、大停电、山火或突发公共安全事件中，消费者的需求是**刚性求生需求（Inelastic Survival Demand under Duress）**，且短期内供给由于道路封闭根本无法通过涨价显著增加！
  2. **美国各州反哄抬物价法（Anti-Price-Gouging Statutes）的法定触发机制**：
     - **触发器（Trigger）**：一旦总统、FEMA、州长或郡县长官宣布进入 **State of Emergency / Local Emergency**，反哄抬法在对应地理区域内**立即自动激活**；
     - **加州红线（`Cal. Penal Code § 396`）**：在紧急状态宣布后 30 天内（工程维修服务长达 180 天），任何食品、饮水、应急用品、医疗物资、燃油、运输服务与酒店住宿的售价，**不得超过紧急状态宣布前立即生效价格的 `110%`（即涨幅 `<= 10%`）**（除非商家能用进货发票证明上游批发成本本身涨了，且即便如此加价率也不得超过日常毛利再加 10%）；
     - **纽约州与佛罗里达州红线（`NY GBL § 396-r` / `FL Stat. § 501.160`）**：严禁收取任何“不合理过高价格（Unconscionably Excessive Price）”，判例法下平白无故涨价超 `10%–15%` 即推定违法！

### Q2：如果遇到暴风雪把价格死死压在 `1.0x–1.1x`，网约车司机或骑手觉得路滑危险不肯出车怎么办？架构上怎么兼顾“不涨乘客的钱”与“激励司机出车”？
* **双向解耦定价账本（Decoupled Rider-Cap vs. Driver-Subsidy Ledger）**：
  - 许多初级工程师把 `司机到手价 = 乘客实付价 × 80%` 硬编码耦死在一起，导致一旦限制乘客端涨价，司机端也没了恶劣天气补贴，运力瞬间归零。
  - **推荐架构**：当某区域进入紧急状态或极端灾害天气时，网关自动将**乘客端收费公式**与**运力端激励公式**解耦：
    1. **向消费者收取（Consumer Price）**：严格锁定 $\le 1.10 \times \text{Baseline\_30d}$（100% 遵守反哄抬法，保护受灾民众）；
    2. **向司机/骑手发放（Courier Payout）**：从平台的**应急灾害社会责任基金（Emergency CSR / Disaster Relief Budget Pool）**中直接拨付 `1.5x–2.0x` 的恶劣天气出车补贴，并将平台自身抽成（Take Rate）临时降为 **`0%`**！这不仅彻底消除了天价行政罚款，还能在灾难期间赢得极佳的社会声誉与政府信任。

### Q3：在实时监控全美 FEMA 灾害宣言、各州州长紧急状态行政令（Executive Orders）及各州反哄抬物价涨幅上限（`0%` vs `10%` vs `15%`）时，Microsoft Web IQ、Exa 与 Bright Data 如何选型？
* **三方能力对比**：
  - **Microsoft Web IQ（`/v3/search` + `/v3/browse`）**：直连美国联邦紧急事务管理局（`fema.gov` OpenFEMA Disaster Declarations）、美国国家气象局（`weather.gov` 极端气象预警）、各州州长办公室（`gov.ca.gov`, `governor.ny.gov`）及各州司法部长（Attorney General）反哄抬物价专页，在 `280ms` 内返回带权威时间戳与受影响郡县（FIPS County Codes）的合规快照（`official_doc_snapshot`），企业级 Entra ID 租户隔离零合规隐患。
  - **Exa Neural Search**：适合检索经济学历史案例研究，无法作为分钟级突发的州长紧急行政令实时熔断源。
  - **Bright Data**：适合抓取竞品平时前台售价，但代理延迟高（P50 `1.9s–4.2s`），不适合嵌入高频实时算价（Pricing Engine `<20ms`）热路径。

---

## 3. 🧭 直观可视化图解（Mermaid 决策树 + 路径对比 + 时序图）

### 3.1 架构师选型决策树（动态溢价紧急状态 `<=10%` 反哄抬熔断与 `300s` 报价锁）

```mermaid
flowchart TD
    A["智能体动态定价与结账扣款请求<br/>(批次金额 $480,000.00)"] --> B{"当前区域若处于紧急状态 (State of Emergency)<br/>溢价倍率是否 <= 1.10x (基于30天基准)?"}
    B -- "否: 暴风雪/飓风紧急状态期间算法触发 4.5x 溢价<br/>(违反加州 §396 / 纽约 §396-r 哄抬物价法)" --> C["🛑 HTTP 403 拦截<br/>EMERGENCY_PRICE_GOUGING_MULTIPLIER_BREACH_BLOCKED (11ms)"]
    B -- "是: 非紧急状态或已锁死 <=1.10x 法定上限" --> D{"结账扣款价是否严格等于 300s 有效期内<br/>已签名的前端报价单 (Zero Mid-Click Jump)?"}
    D -- "否: 用户点支付瞬间后台暗涨倍率多扣钱<br/>或篡改 30天历史基准价" --> E["🚨 HTTP 422 拦截<br/>MID_CHECKOUT_PRICE_JUMP_OR_BASELINE_MANIPULATION_REJECTED (14ms)"]
    D -- "是: 所见即所扣 (Price-Lock Token 有效)" --> F["调用 Microsoft Web IQ /v3/browse<br/>核验 FEMA / 州长紧急行政令覆盖郡县 (FIPS) 与延续期"]
    F --> G{"未落入灾后 30/180 天限价延续期<br/>且全包价满足 FTC 零隐藏垃圾费披露?"}
    G -- "否: 灾后重建期违规提前恢复高倍溢价" --> H["🛑 HTTP 451 合规冻结<br/>FEMA_EMERGENCY_EXTENSION_OR_FTC_JUNK_FEE_HOLD (280ms)"]
    G -- "是: 行政令状态与 FTC 全包价披露合规" --> I{"是否启用紧急状态自动削峰平抑 +<br/>300s 锁价令牌消除拒付与司法重罚?"}
    I -- "是: 免疫百万罚单+挽回跳价弃单 $38,400" --> J["🧑‍⚖️ HTTP 409 财务确认<br/>ANTI_GOUGING_CAP_AND_PRICE_LOCK_SAVINGS_CONFIRM"]
    I -- "否: 标准合规动态定价自动清算" --> K["✅ HTTP 200 自动放行<br/>VERIFIED_DYNAMIC_SURGE_PRICING_SETTLED (10ms)"]
```

### 3.2 传统无脑 `5.0x` 灾难溢价 + 结账跳价（反模式）vs 紧急令 `1.10x` 熔断 + `300s` 锁价网关对比

```mermaid
flowchart LR
    subgraph AntiPattern["❌ 传统反模式：灾难期间算法盲飙 5.0x + 点支付瞬间暗涨扣款"]
        A1["山火/暴风雪全城疏散触发供需失衡<br/>RL 算法无脑将打车/买水涨到 5.0x"] --> A2["违反州长紧急状态反哄抬物价法<br/>遭州司法部长按 $10k/单顶格重罚"]
        A2 --> A3["用户看价 $25 点支付瞬间跳变成 $52<br/>引爆 FTC 诱饵欺诈调查与 12.5 拒付!"]
    end

    subgraph BestPractice["✅ 推荐架构：FEMA 紧急令 <=1.10x 硬熔断 + 300s HMAC 报价锁网关"]
        B1["Web IQ 实时同步 FEMA/州长紧急令围栏<br/>11ms 自动锁死涨幅 <=10% (对比30天基准)"] --> B2["双向解耦：乘客端守住 <=1.10x 平价<br/>平台零抽成 + 应急基金补贴骑手出车"]
        B2 --> B3["签发 300s 有效期 Price-Lock 签名报价令牌<br/>100% 保证所见即所扣，零跳价拒付!"]
    end
```

### 3.3 端到端时序图（FEMA/州长紧急令巡检 → 30天基准价比对 → 签发 `300s` 锁价令牌 → 扣款守恒）

```mermaid
sequenceDiagram
    autonumber
    participant User as 消费者 / 出行与即配 Agent
    participant Gate as 动态定价反哄抬与锁价网关
    participant WebIQ as Microsoft Web IQ (/v3/browse)
    participant Baseline as 30天滚动基准价账本 (Immutable)
    participant PSP as 支付清算网关

    User->>Gate: 1. 请求实时报价与结算批次 ($480,000.00，携带起终点 H3 网格与 ZIP)
    Gate->>WebIQ: 2. /v3/browse 核验该 FIPS 郡县是否处于活跃 FEMA / 州长紧急状态行政令下
    WebIQ-->>Gate: 280ms 返回当前紧急令状态与法定涨幅上限 (如 CA <=10%, official_doc_snapshot)
    Gate->>Baseline: 3. 读取紧急令生效前 30 天滚动中位价 P50_30d_Baseline，硬拦截 >1.10x 倍率 (11ms)
    Gate->>User: 4. 签发带 HMAC 签名的 Price-Lock Quote (TTL = 300s, 锁死全包总价)
    User->>Gate: 5. 用户在 300s 窗口内点击确认支付
    Gate->>Gate: 6. 强制校验扣款额 == 签名报价单锁死额 (14ms 阻断结账跳价暗扣)
    Gate->>PSP: 7. 签发 agentic_surge_pricing_emergency_gouging_cap_mandate_... 执行合规扣款!
```

---

## 4. 📊 架构师选型决策矩阵（Architecture Selection Matrix）

| 评估维度 | 方案 A：纯供需弹性 RL 算法无上限裸奔（反模式） | 方案 B：全年一刀切禁止任何动态溢价（丧失运力弹性） | 方案 C：紧急状态 `<=1.10x` 围栏 + `300s` 锁价网关（推荐） |
| :--- | :--- | :--- | :--- |
| **平时商业高峰（晚高峰/演唱会）运力调度** | ✅ 高效平衡供需 | ❌ **运力严重短缺（没人愿意在高峰期接单）** | ✅ **高效（非紧急状态下正常发挥市场价格调节作用）** |
| **自然灾害/突发危机期间反哄抬法合规** | ❌ **致命违法（面临千万美元级司法部长罚单与公关危机）** | ✅ 合规 | ✅ **100% 合规（FEMA/州长紧急令下毫秒级自动锁死 `<=1.10x`）** |
| **防结账点击瞬间价格跳变（Bait & Switch）** | ❌ **频发（看价与扣款不一致引发大量拒付）** | ✅ 固定价无跳变 | ✅ **100% 零跳价（`300s` HMAC 报价锁保证所见即所扣）** |
| **美国 FTC 全包总价披露（Junk Fee Rule）** | ❌ 常在最后一步偷偷加收动态服务费 | ⚠️ 视实现而定 | ✅ **首屏报价即含全部动态附加费与税费** |
| **适用场景（Good Fit vs Not For）** | ⛔ **严禁用于任何涉及民生、出行、住宿与生鲜的平台** | 仅适合政府定价的公共公交地铁 | ✅ **网约车/Robotaxi、即时配送、航司酒店与票务平台必选** |

---

## 5. 🧪 定量实测与 7-Card 4:5 评测报告摘要（Benchmark & Provenance）

我们在 `lab/webiq_commerce_demo.py` 中内置了确定性策略评估器 `evaluate_agentic_surge_pricing_anti_gouging_policy()`，对 `$480,000.00` 的智能体动态溢价与即时履约批次进行了 5 类场景的边界验证（数据来源标注遵循零虚构原则：`synthetic_policy`、`deterministic_offline_simulation`、`official_doc_snapshot`）：

| 场景编号与名称 | 输入条件与防线触发条件 | 网关 HTTP 状态码与动作 | 实测延迟 | 净保全/节省金额 | Provenance 标签 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Case 1 (`srg_commit_ok`)** | 紧急令下涨幅 `<=10%`（对比30天基准）+ `300s` 报价锁匹配 + FTC 全包价合规 | `HTTP 200` · `Act automatically` | `10ms` | 安全清算 `$480,000.00` | `deterministic_offline_simulation` |
| **Case 2 (`srg_gou_403`)** | 飓风/暴风雪州长紧急状态期间 RL 算法企图触发 `4.5x` 倍率溢价（违反加州 `§396`） | `HTTP 403` · `Send to a human` | `11ms` | 拦截 `$480,000.00` 违法哄抬物价 | `synthetic_policy` |
| **Case 3 (`srg_jmp_422`)** | 用户点击结账瞬间后台倍率上调导致实扣金额高于前端展示报价，或篡改 30天基准价 | `HTTP 422` · `Send to a human` | `14ms` | 阻断结账跳价暗扣与基准造假 | `deterministic_offline_simulation` |
| **Case 4 (`srg_ext_451`)** | Web IQ `/v3/browse` 检出灾后行政令处于 180 天重建延长限价期内或违反 FTC 隐藏附加费禁令 | `HTTP 451` · `Send to a human` | `280ms` | 冻结灾后恢复期违规涨价 | `official_doc_snapshot` |
| **Case 5 (`srg_sav_409`)** | Web IQ 自动执行紧急状态 `1.10x` 削峰免除州检察长天价罚单并凭 `300s` 锁价挽回跳价流失 | `HTTP 409` · `Confirm` | `245ms` | **单批免罚/挽回 `$38,400.00`**（净营收安全优化至 `$441,600.00` 基准） | `official_doc_snapshot` |

### 7-Card 4:5 视觉评测报告核心卡片速览
- **Card 1 (`1 / 7` · `HANDS-ON · SURGE PRICING & ANTI-GOUGING GATE`)**：展示 `$480,000.00` 动态定价批次在 `10ms` 内完成 30 天基准价校验、紧急状态围栏过滤与 `300s` 锁价令牌验签。
- **Card 2 (`2 / 7` · `SCENARIO: EMERGENCY <=10% CAP & PRICE LOCK`)**：量化展示 `11ms` 硬熔断紧急状态下的 `4.5x` 算法溢价（`HTTP 403`），以及 `14ms` 拦截结账点击瞬间暗涨跳价（`HTTP 422`）。
- **Card 3 (`3 / 7` · `WHAT I TESTED`)**：5 组动态定价与反哄抬风控矩阵全绿通过（`HTTP 200 / 403 / 422 / 451 / 409`）。
- **Card 4 (`4 / 7` · `UNDER THE HOOD`)**：展示 `agentic_surge_pricing_emergency_gouging_cap_mandate_...` 的 JSON 契约结构（含 `fema_emergency_active: true`、`pre_emergency_30d_baseline_cents`、`applied_surge_multiplier_bps: 1080 <= 1100`、`price_lock_quote_ttl_sec: 300`）。
- **Card 5 (`5 / 7` · `ROBUSTNESS CHECK`)**：验证即使上游特征工程传入极端的 `demand_supply_ratio = 50.0`，只要地理围栏命中紧急状态标志，输出倍率 100% 被钳位（Clamped）在法定上限内。
- **Card 6 (`6 / 7` · `LATENCY`)**：对比网关内存级 H3 紧急围栏 + HMAC 报价锁校验（`10ms`）与传统事后法务人工排查违规订单退款（耗时数周且已被立案）。
- **Card 7 (`7 / 7` · `MY TAKE`)**：明确 **✅ Good fit**（网约车与 Robotaxi、即时生鲜医药配送、航司酒店动态收益管理）与 **⛔ Not for**（禁用于无政府紧急令熔断开关的裸奔 RL 定价模型或无锁价 TTL 的结账系统）。

---

## 6. 🛠️ 生产上线快速核验清单（Production Readiness Checklist）

- [ ] **不可篡改的“前 30 天滚动基准价账本（Rolling 30-Day Pre-Emergency Baseline）”**：按每个地理网格（`H3 Resolution 7` / `ZIP Code`）与 SKU/车型每日自动归档过去 30 天的中位成交价与最高常规价；一旦触发紧急状态，立即冻结该基准快照作为法定分母。
- [ ] **FEMA 与各州州长紧急状态令（State of Emergency）ハードコード级熔断钳位（Clamp）**：在动态定价输出层（Model Output Post-Processor）写入物理硬规则：`if is_emergency_zone(h3_cell): final_price = min(model_price, baseline_30d * state_max_cap_ratio)`（如加州 `1.10`、零容忍州 `1.00`）。
- [ ] **HMAC 签名的 `Price-Lock Quote Token (TTL = 180s–300s)` 防结账跳价**：前端向用户或买方 Agent 展示价格时，必须下发包含 `(quote_id, user_id, locked_total_cents, expires_at, hmac_sig)` 的锁价令牌；扣款网关只认该锁死金额，严禁在扣款瞬间重新算价暗涨（`HTTP 422`）。
- [ ] **灾难期“乘客平价限高 + 平台应急基金补贴运力”双向解耦**：当紧急状态激活时，自动将平台抽成降为 `0%` 并调用独立应急预算池补贴骑手/司机，确保不向受灾消费者转嫁成本的同时维持运力供给。
- [ ] **Microsoft Web IQ 实时巡检 FEMA 灾害警报、州长行政令延期与 FTC 全包价新规**：通过 Web IQ `/v3/browse` 持续同步各州紧急状态生效/解除时间表与灾后 30–180 天重建限价期。
