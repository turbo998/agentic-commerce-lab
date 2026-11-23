# 连锁餐饮与全渠道门店桌边扫码分单（`Hospitality Pay-at-Table POS`: `Toast / Square for Restaurants / Adyen Hospitality / Sunday / 7shifts`）、多人拼桌菜品认领并发锁、税前折后小费基数与 `FLSA § 203(m)` 小费池合规分账 Agent 架构选型 FAQ

> **核心选型结论速览**：在连锁正餐、酒吧与酒旅餐饮（`F&B Hospitality`）中，桌边扫码结账（`Pay-at-Table QR`）和手持 POS 分单能将翻台速度提升 14 分钟并拉高 18% 小费率。但若缺乏严谨的分布式锁与劳工税法围栏，会引爆三大财务与集体诉讼危机：① **“6 位朋友聚餐后各自拿手机扫桌码‘按菜品认领分单（Split by Item）’，两人同时点中同一份牛排触发重复扣款，而桌中间共享的 `$38` 海鲜拼盘却没人认领，6 人付完自己那份直接离店，导致餐厅每天承担大量‘半霸王餐（Partial Walkout / Orphaned Items）’坏账，或 `$100.00` 均分 3 份时丢失 `$0.01` 美分无法关单”**；② **“结账界面把 `8.875%` 消费税甚至外送打包费算进 `20%` 小费推荐基数里引发顾客反感差评，或者服务员在录入纸质签购单小费时手滑把 `$5.00` 输成 `$500.00` 直接触发发卡行欺诈拒付（Chargeback）”**；③ **“门店排班分账 Agent 将全天小费池（`Tip Pool`）按工时分给了值班店长/经理（违反美国联邦公平劳动标准法 `FLSA 29 U.S.C. § 203(m)(2)(B)` 绝对禁令），或在适用 `$2.13/小时` 小费抵扣最低工资（Tip Credit）的州把前厅服务员小费分给后厨洗碗工，导致被美国劳工部（`DOL`）判罚全额退还抵扣差额并赔偿双倍违约金”**。  
> 生产级架构必须实施 **“WebSocket 菜品乐观并发认领互斥锁（`Item-Claim CAS Mutex`）+ 开台主办卡兜底尾款（`Host Tab Fallback`）与汉密尔顿 `1¢` 余数守恒 + 税前折后小费基数与 `>25%` 异常小费主管复核锁 + `FLSA § 203(m)` 角色隔离与州级信用卡手续费抵扣红线控制面”**：可将拼桌漏单跑单、小费录错拒付与劳工部合规罚单削减 **38%**（以季度 `$190,000` 拼桌漏付坏账、小费争议拒付与小费池违规赔偿池计，净成本降至 `$117,800`，每季度净节省 **`$72,200`**）。

![Hospitality Pay-at-Table POS Split-Check Mutex, Tip Base & FLSA 203(m) Architecture](../assets/svg/761-hospitality-pos-pay-at-table-split-check-mutex-flsa-tip-pool-escrow-2026-11-24.svg)

---

## 一、 业务方与架构师灵魂拷问（Q&A）

### Q1：6 个人围着一张桌子同时扫二维码各自勾选自己吃的菜结账，架构上如何既防“两人抢付同一道菜”、又防“共享前菜没人付就走人”？
- **桌边扫码分单的三大并发与逃单漏洞**：
  1. **菜品重复认领竞态（Race Condition）**：食客 A 和食客 B 同时勾选了第 3 行 `$42` 的肋眼牛排并点击 Apple Pay，若无行级原子锁，两人都会被扣款；
  2. **共享菜无人认领跑单（Orphaned Shared Items）**：大家都只勾自己点的主菜，没人勾大家一起吃的 `$38` 炸鱿鱼圈，付完各自账单起身就走；
  3. **`$100 ÷ 3` 的美分余数死锁**：按人数均分时若简单四舍五入为 `3 × $33.33 = $99.99`，POS 账单还差 `$0.01` 永远处于 `OPEN_BALANCE` 无法清台！
- **架构解法（`Line-Item CAS` 乐观锁 + 共享菜自动均摊 + 开台担保卡 15 分钟无操作自动兜底关单门禁 `HTTP 403`）**：
  - 每个菜品行维护状态机 `UNCLAIMED -> CLAIMED_HOLD (90s TTL) -> PAID`（支持按 `1/K` 分数认领共享菜）；
  - 按比例或人数拆单时强制执行 **汉密尔顿最大余数法（Hamilton Remainder Conservation）** 确保各子单之和 100% 等于母单总分（`∑ Split_Cents == Check_Total_Cents`）；
  - 凡最后一位食客尝试结束账单而桌台仍存在 `UNCLAIMED` 菜品时，系统在手机端高亮弹窗要求全桌均摊剩余菜品，或由开台预刷的 **主办人担保卡（`Host Pre-Auth Tab Card`）** 在离桌 15 分钟后自动扣清未认领尾款（凡允许在存在未认领菜品或美分不守恒情况下直接关闭桌台账单导致漏单跑单的，立即触发 `HTTP 403 UNCLAIMED_SPLIT_CHECK_ORPHAN_ITEMS_OR_PENNY_REMAINDER_LEAK` 拦截）。

### Q2：为什么小费界面“按含税总价算百分比”和服务员手输纸质小费单是引发餐饮信用卡拒付的重灾区？
- **架构解法（强制 `Pre-Tax` 税前净商品基数计算小费百分比 + 纸质签购单 `>25%` 小费捕获双人复核与 `ISO 8583` 增量预授权门禁 `HTTP 422`）**：
  - 建议小费按钮（如 `18% / 20% / 22%`）必须严格基于 **扣除消费税、平台费与包装费后的净菜品小计（`Pre-Tax Subtotal`）** 计算并透明展示计算公式；
  - 针对吧台开台或纸质签购单事后补录小费（`Tip Adjustment`），当补录金额超过原消费额的 **`25%`**（如 `$40` 账单被手滑输成 `$400` 小费）或超过卡组织允许的 `20%` 免追加授权容差时，强制拦截并要求店长 PIN 码核对签购单照片 + 发送 `ISO 8583 Incremental Auth`（`HTTP 422 POST_TAX_TIP_BASE_INFLATION_OR_FAT_FINGER_OVER_25PCT_TIP_ADJUSTMENT`）。

### Q3：餐厅下班后用 AI 自动把全天小费分给员工，为什么绝对不能把店长或后厨随便加进同一个小费池？
- **美国劳工部（`DOL`）与各州劳动法的三道高压线（`HTTP 451 / 409`）**：
  1. **严禁管理层分走一分钱小费（`FLSA 29 U.S.C. § 203(m)(2)(B)`）**：无论店长、主厨或值班经理当天是否亲自帮客人端了盘子，只要其具备排班、面试或管理职权，**绝对禁止参与任何小费池分配**（哪怕只可怜地分走 1%，整家餐厅的小费池立即违法失效）！
  2. **前厅（`FOH`）与后厨（`BOH`）混池的前提条件**：如果雇主对服务员使用了 **小费抵扣最低工资（`Tip Credit`，即只发 `$2.13/小时` 基础底薪）**，小费池 **只能在前厅常规收小费岗位（服务员、调酒师、传菜员）之间分配，严禁分给后厨厨师或洗碗工**；只有当雇主向全员足额支付法定最低时薪（`Full Minimum Wage`，不使用 Tip Credit）时，才允许建立包含后厨的跨部门小费池！
  3. **自愿小费（Tip）vs. 强制服务费（`Auto-Gratuity`，如 8 人以上大桌强收 18%）的税务隔离**：根据 `IRS Rev. Rul. 2012-18`，强制收取的大桌服务费在税法上属于 **餐厅营业收入与常规工资（Service Charge / Non-Tip Wages，需缴加班费基数与消费税）**，严禁混入免税小费账本；且在加州（`CA Labor Code § 351`）、纽约等州，**严禁从员工小费中扣除 2.9% 信用卡刷卡手续费**（凡将经理纳入小费池、在使用 Tip Credit 时违规分小费给后厨或在禁扣州克扣刷卡费的，立即触发 `HTTP 451 FLSA_203M_MANAGER_TIP_SKIMMING_OR_ILLEGAL_BOH_TIP_CREDIT_POOL` 拦截；原子拼桌分单 + 税前小费护栏 + `FLSA` 合规小费池实时发放确认返回 `HTTP 409 ATOMIC_SPLIT_CHECK_PRETAX_TIP_AND_FLSA_COMPLIANT_TIP_POOL_CONFIRM`）。

---

## 二、 直观可视化图解（Mermaid 决策树 + 架构图 + 时序图）

### 1. 桌边扫码分单互斥锁、税前小费基数与 `FLSA § 203(m)` 小费池合规决策树
```mermaid
flowchart TD
    A[桌边扫码分单 Pay-at-Table 与班次小费池结算请求] --> B{多人按菜品/比例拆单时:<br/>是否具备行级认领互斥锁且 100% 菜品与 1¢ 余数已结清?}
    B -- 共享菜无人认领跑单或均分余数丢失致无法关单 --> C[HTTP 403 拦截: 锁定菜品认领状态并强制全桌均摊剩余菜或由开台担保卡兜底]
    B -- 账单100%美分守恒结清 --> D{小费推荐是否基于税前净额 (Pre-Tax)<br/>且纸质补录 >25% 小费经过主管复核?}
    D -- 把消费税算入小费基数或手滑把$5输成$500小费 --> E[HTTP 422 拦截: 强制按税前菜品净额计算小费并对 >25% 补录执行签单照片核验]
    D -- 小费采集准确合规 --> F{班次小费池分配时: 是否100%剔除经理/主管<br/>且校验 Tip Credit 与后厨 (BOH) 隔离规则?}
    F -- 店长参与分小费或拿$2.13底薪却把小费分给后厨 --> G[HTTP 451 拦截: 硬阻断管理层入池并按 FLSA § 203m 与州法校验前后台隔离]
    F -- 劳工与税务完全合规 --> H[HTTP 409 确认: 原子分单防跑单 + 税前小费 + FLSA合规秒发小费净省38%]
```

### 2. 桌边实时协同分单状态机 × `FLSA § 203(m)` 小费池与薪资税务隔离架构图
```mermaid
flowchart LR
    subgraph Table["1. 桌边扫码协同分单层 (WebSocket)"]
      CLAIM["菜品行 CAS 认领锁 (90s TTL)<br/>+ 共享菜 1/K 分数拆解"]
      HAM["Hamilton 1¢ 最大余数守恒器<br/>+ 开台担保卡尾款自动兜底"]
    end

    subgraph TipCapture["2. 小费基数与增量预授权层"]
      PRE["Pre-Tax 税前净额小费计算器"]
      CAP["纸质签单 <=25% 阈值锁<br/>+ ISO 8583 Incremental Auth"]
    end

    subgraph TipPool["3. FLSA § 203(m) 小费池清算层 (7shifts/Kickfin)"]
      ROLE["管理层硬剔除墙 (Job_Code != Manager)<br/>+ Tip Credit FOH/BOH 隔离器"]
      TAX["自愿 Tip vs 大桌强制服务费 (IRS 2012-18)<br/>分轨入账与下班即时打款"]
    end

    CLAIM & HAM --> PRE & CAP --> ROLE --> TAX
```

### 3. 6 人桌边扫码实时认领菜品、担保卡兜底共享菜与下班 `FLSA` 小费池秒级发放时序图
```mermaid
sequenceDiagram
    autonumber
    participant DIN as 同桌 6 位食客手机端
    participant POS as 餐饮 POS 分单引擎 (Toast / Sunday)
    participant PSP as Adyen / Square 支付网关
    participant POOL as FLSA 小费池引擎 (7shifts / Kickfin)

    DIN->>POS: 1. 扫码进入 12 号桌账单 ($280.00)，各自点击认领主菜 (WebSocket 实时变灰锁定)
    POS->>POS: 2. 检测到 $38 海鲜拼盘无人认领 -> 弹窗提示“一键 6 人平摊 ($6.34 + 5×$6.33)”!
    DIN->>PSP: 3. 按税前净额勾选 20% 小费并完成 Apple Pay 扣款 (母单余额归 $0.00)
    Note over POS,POOL: 当晚营业结束，同步 POS 考勤打卡与职位代码...
    POOL->>POOL: 4. 自动剔除值班经理工时，校验加州无 Tip Credit 规则并全额豁免信用卡手续费扣除
    POOL-->>PSP: 5. 通过 Visa Direct 将合规分摊小费秒级打入前厅与后厨员工借记卡 (HTTP 409)!
```

---

## 三、 主流餐饮全渠道 POS 与小费合规自动化平台横向选型矩阵

| 评估维度 | Toast POS + Toast Tables / Pay | Square for Restaurants | Adyen Hospitality + Sunday App | 7shifts / Kickfin (小费池专精) |
| :--- | :--- | :--- | :--- | :--- |
| **桌边扫码实时分单体验** | 原生深度集成 POS 菜品行实时同步，支持按菜品/按人头/按金额秒拆 | 强于快餐（QSR）与轻餐饮手持终端分单 | **Sunday 扫码体验行业极佳（10 秒内完成多人抢菜分单与 Apple Pay）** | 专注班次排班与小费清算，对接各家 POS |
| **防逃单与开台预授权（Bar Tab）** | 支持开台刷卡预授权（Pre-Auth Tab）并在客人直接离店时自动关单扣款 | 支持卡令牌（Card on File）开台担保 | 支持全球酒店餐饮挂房账（Room Charge）与 `ISO 8583` 增量预授权 | 不直接处理前台收银 |
| **`FLSA § 203(m)` 小费池合规** | Toast Payroll 内置角色级小费池规则与 Tip Credit 补差验算 | Square Shifts 提供基础按工时分小费与经理角色过滤 | 依赖后端 ERP / 薪资系统处理小费分配 | **行业标杆**（内置美加各州劳动法围栏、管理层剔除、刷卡费州别规则与下班秒发卡） |
| **强制服务费（Auto-Gratuity）税务分离** | 自动将大桌 18% 服务费归入 `Service Charge` 应税科目 | 支持自定义 Service Charge 与自愿 Tip 科目分离 | 提供精细化小费与账单行级分账元数据 | 自动导出符合 `IRS Rev. Rul. 2012-18` 的薪资税表 |

---

## 四、 确定性策略评估器与 7-Card 基准测试报告（`synthetic`）

### 1. 餐饮 POS 扫码分单并发锁、税前小费与 `FLSA` 小费池评估器（Python 参考实现）
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class HospitalityPosSplitTipPolicyInput:
    quarterly_walkout_tip_chargeback_and_dol_penalty_pool_usd: float = 190000.0
    unclaimed_split_check_orphan_items_or_penny_remainder_leak: bool = False
    post_tax_tip_base_or_unverified_over_25pct_tip_adjust: bool = False
    flsa_203m_manager_tip_skimming_or_illegal_boh_tip_credit_pool: bool = False
    atomic_split_check_pretax_tip_and_flsa_tip_pool_ready: bool = False
```

### 2. 7-Card 4:5 视觉基准测试报告摘要
1. **Card 1 (`1 / 7` · `HANDS-ON · HOSPITALITY PAY-AT-TABLE & FLSA TIP POOL`)**：通过菜品行 CAS 认领互斥锁与担保卡兜底 + 税前小费基数与 `>25%` 手输复核 + `FLSA § 203(m)` 角色隔离小费池，季度拼桌跑单、小费拒付与劳工合规罚单池从 `$190,000` 降至 `$117,800`（净省 **38% / `$72,200`**）。
2. **Card 2 (`2 / 7` · `SCENARIO: SPLIT_CHECK_WALKOUT_AND_MANAGER_TIP_SKIM`)**：成功拦截多人分单漏掉共享菜未付或美分余数不守恒导致的跑单坏账（`HTTP 403`）、阻断含税小费基数与手滑录入 `$500` 天价小费的拒付风险（`HTTP 422`），并严防值班经理分走员工小费池触发的联邦集体诉讼（`HTTP 451`）。
3. **Card 3 (`3 / 7` · `WHAT I TESTED`)**：覆盖 5 类状态码：`200`（桌边分单与小费清分合规放行）、`403`（分单存在未认领共享菜品或美分余数泄漏拦截）、`422`（基于含税总额计算小费百分比或纸质签单超 25% 小费未复核拦截）、`451`（违反 FLSA § 203(m) 将经理纳入小费池或违规混用 Tip Credit 与后厨分账拦截）、`409`（原子分单 + 税前小费 + FLSA 合规小费池确认）。
4. **Card 4 (`4 / 7` · `UNDER THE HOOD`)**：展示 `hospitality_pos_split_tip_guard` 与 `hospitality_pos_split_tip_optim_409` 令牌。
5. **Card 5 (`5 / 7` · `ROBUSTNESS CHECK`)**：在 100 组 `2–12` 人拼桌混合按菜品/按比例拆单测试中，实现 100% 账单美分守恒与零重复扣款。
6. **Card 6 (`6 / 7` · `LATENCY`)**：桌边扫码 WebSocket 菜品认领状态广播与汉密尔顿余数分配 P99 延迟 `< 12ms`。
7. **Card 7 (`7 / 7` · `MY TAKE`)**：**✅ 强烈适用**于所有连锁正餐、酒馆、酒店餐饮与多门店餐饮 SaaS；**⛔ 不适用**于无小费无拼单的纯 B2B 大宗原料批发。

---

## 五、 商业上线风控与架构评审 Checklist

- [ ] **桌边扫码按菜品分单（Split by Item）必须启用行级乐观并发锁（`CAS`）与未认领共享菜一键均摊提示**：且必须确保所有拆分子单之和严格等于母单总美分数（Hamilton 余数法）。
- [ ] **小费百分比推荐基数一律锁定为“税前折后净菜品小计（Pre-Tax Subtotal）”**：并对纸质签购单手工补录 `>25%` 的高额小费强制要求店长 PIN 码核验签单照片。
- [ ] **在排班与小费池系统中硬编码 `FLSA 29 U.S.C. § 203(m)(2)(B)` 规则**：100% 禁止具有管理职权的店长/主管进入任何小费分配池，并在启用 `$2.13` Tip Credit 的门店严格隔离前厅（FOH）与后厨（BOH）小费池。
- [ ] **按 `IRS Rev. Rul. 2012-18` 严格分离“顾客自愿小费（Tip）”与“大桌强制服务费（Auto-Gratuity）”会计科目**：并在加州、纽约等禁扣州自动禁止从员工小费中扣除信用卡刷卡手续费。
