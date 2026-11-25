# 订阅制 SaaS 与 DTC 会员退订挽留（`Cancel-Flow Deflection`）、暂停跳期 vs. 折扣因果归因、美国 `FTC 一键退订法案 (16 CFR Part 464)` 合规与智能催收（`Smart Dunning`）Agent 架构选型对比：`Chargebee Retention` vs. `ProsperStack` vs. `Recurly` vs. `Recharge / Stripe Billing`、防“每 90 天假装点退订白嫖半价”及净省 43% 决策指南（FAQ · 🏆 历史性第 1,400 项确定性单元测试重大里程碑！）

> **导读（对齐 `ib-vs-ethernet-roce-selection-faq.md` 标杆风格 · 🏆 历史性全库第 1,400 项确定性单元测试重大里程碑 · 第 522 篇双语指南 · 第 403 轮 · 第 846 张 SVG · 第 296 个策略沙盒）**：本文面向 B2B/B2C 订阅制 SaaS、AI 生成式工具会员、流媒体以及 DTC 周期购订阅盒（保健品/咖啡/宠物粮/美妆盒）领域的 **Cloud & AI Solution Architect**。在订阅制商业中，将月流失率（Monthly Churn）从 `6%` 压降到 `3.5%` 可直接使客户终身价值（`LTV`）提升 **`70%+`**！然而，传统的退订挽留弹窗与续费扣款重试（Dunning）正在遭遇三大致命危机：① **美国联邦贸易委员会 `FTC Click-to-Cancel 新规 (16 CFR Part 464)` 与加州自动续费法（`ARL`）重锤执法（每次违规最高罚 `$51,744`）**：如果用户当初在线上点 2 下就完成了订阅，退订时却逼他打客服电话、逼他先跟 AI 挽留机器人聊 10 句才放出隐藏的退订按钮、或连跳 6 页“您真的忍心离开吗？”迷宫（`Roach Motel` 暗黑模式），将直接面临联邦巨额罚单与信用卡 `13.2 (Canceled Recurring)` 拒付潮！② **“假装点退订白嫖 5 折券”的毛利自残漏洞（Cancel-Button Coupon Gaming）**：许多小红书/Reddit 攻略专门教用户“每 3 个月去后台点一次取消订阅，系统就会自动弹出一张半价挽留券”，让原本根本不会流失的老客常年白嫖 5 折；或者对明明是因为“家里囤货没吃完”想退订的客户塞折扣券，而不是引导其 **“一键暂停/跳过下月发货（Pause / Skip 1 Month）”**！③ **被动流失（`Involuntary Churn`）无脑每日定时重扣触发 Visa `Category-1` 死卡重罚（`$15/次`）**。本文给出 **`Chargebee Retention` vs. `ProsperStack` vs. `Recurly Churn & Dunning` vs. `Recharge / Stripe Billing`** 的横向选型矩阵，并落地 **`365天` 挽留折扣冷却期与囤货原因优先导流“暂停/跳期”锁（`HTTP 403`）**、**先查 `VAU/ABU` 换卡更新器、死卡零重试熔断与发薪日智能重扣锁（`HTTP 422`）**、**`FTC 16 CFR Part 464` 单屏对称显式“立即退订”按钮锁（`HTTP 451`）** 及 **合规高转化双挽留编排（`HTTP 409`，净省 43%）**。

![Subscription Churn-Save, FTC Click-to-Cancel & Smart Dunning Copilot Architecture](../assets/svg/846-saas-subscription-cancel-flow-ftc-retention-1400th-test-2026-11-26.svg)

---

## 一、 📌 核心选型结论速览（Executive Summary）

1. **终极选型结论（一句话先看懂怎么选）**：
   - **中大型 B2B/B2C SaaS 企业（追求基于客户使用率画像、合同金额与生命周期分层定制退订挽留流，并同步写回 Salesforce / HubSpot）**：首选 **`Chargebee Retention (原 Brightback)`**，企业级分群规则与挽留 A/B 实验能力最强。
   - **使用 `Stripe Billing / Paddle / Chargebee / Recurly` 的快速增长型 AI 应用与现代 SaaS（追求 1 天内通过嵌入式组件上线高颜值退订挽留流、自带防薅券冷却期与因果挽留率分析）**：首选 **`ProsperStack`**。
   - **高并发流媒体、内容付费与消费者数字会员（核心痛点是 `35%+` 的流失来自信用卡过期或余额不足导致的“非自愿被动流失 Involuntary Churn”）**：首选 **`Recurly`**，其机器学习动态催收引擎（Smart Dunning）与卡组织自动换卡更新器（Account Updater）挽回率全行业领先。
   - **基于 `Shopify` 的实物周期购订阅盒品牌（保健品、咖啡、猫粮、剃须刀，核心诉求是让用户通过短信或单页一键“跳过本月 Skip / 换口味 Swap / 推迟 30 天发货 Pause”而非退订）**：首选 **`Recharge`** 或 **`Skio`**。
2. **三大订阅挽留与智能催收确定性风控红线（Fiduciary Control Gates）**：
   - **红线 1（拦截客户每 90 天假装点退订反复薅走半价挽留券及对“囤货太多/出差”客户错误发放价格折扣 / `HTTP 403`）**：当用户点击“取消订阅”进入单屏挽留流程时，控制平面必须执行两项硬校验：① **退订原因精准映射（Reason-to-Remedy Matching）**：若用户勾选“家里还有存货没用完 / 近期出差度假 / 暂时用不上”，**严禁发放现金折扣券**（给囤货过多的用户打 7 折只会让他下个月攒下更多存货彻底退订！），必须唯一推荐 **“一键免费暂停 30/60 天或跳过下一期（`1-Click Pause / Skip`）”**；② **365 天价格挽留冷却锁（`365-Day Save-Discount Cooldown`）**：若该账号在过去 365 天内已经领取过一次退订挽留折扣，严禁再次弹出折扣码（仅提供降级至轻量套餐或暂停服务），违者触发 `HTTP 403 SERIAL_CANCEL_DISCOUNT_GAMING_OR_OVERSTOCK_COUPON_MISMATCH_VETO`！
   - **红线 2（拦截在未调用卡组织自动换卡更新器 `VAU/ABU` 前盲目重扣过期卡，以及对 `Visa Category-1` 硬拒付死卡发起重复扣款招致 `$15/次` 罚金 / `HTTP 422`）**：在发起周期续费扣款前 48 小时，必须先通过 **`Visa Account Updater (VAU) / Mastercard Automatic Billing Updater (ABU)`** 或 **`EMVCo Network Token`** 同步最新有效期与新卡号；一旦续费扣款失败，必须解析收单行返回的精确 `ISO 8583 / Network Advice Code`：若属于 **`Category-1` 永久硬拒付（如 `04 没收卡`、`41/43 挂失被盗卡`、`R0/R1 持卡人已向银行下达停止代扣令`）**，必须 **`0 次重试` 立即熔断**；若属于 `Code 51 (余额不足)` 软拒付，严禁半夜连续每天盲刷，必须对齐当地发薪日（每月 `1号 / 15号 / 周五下午`）择时重试，违者触发 `HTTP 422 VISA_CAT1_HARD_DECLINE_RETRY_OR_MISSING_VAU_UPDATER_BREACH`。
   - **红线 3（拦截违反美国 `FTC Click-to-Cancel (16 CFR Part 464)` 强制打电话/强制聊满 5 轮 AI 才给退订及年费自动续费漏发 `T-30d` 法定提醒 / `HTTP 451`）**：根据美国联邦贸易委员会 `16 CFR Part 464` 负面选项规则（Click-to-Cancel）与加州 `ARL` 法案：在线签约的订阅必须提供在线平权退订入口；挽留流程最多只允许展示 **1 个单屏挽留方案（Single-Screen Save Offer）**，且同一屏幕底部必须 **始终展示清晰可见、无需额外滚动或客服审批的“不接受优惠，立即取消订阅（Cancel Immediately）”按钮**；且年付套餐或免费试用转付费必须在扣款前 `15–45 天` 发送带有一键退订链接的法定预通知邮件，违者触发 `HTTP 451 FTC_CLICK_TO_CANCEL_DARK_PATTERN_OR_ARL_NOTICE_BREACH`。

---

## 二、 🎯 业务方与架构师灵魂拷问 Q&A（The Why & How）

### Q1：很多增长黑客喜欢把“取消订阅”按钮藏在四级菜单深处，点进去还要先跟 AI 客服对话 5 分钟才能取消——为什么这种设计在 2026 年会让公司赔得倾家荡产？
- **商业痛点与事故还原**：
  1. **联邦重罚**：美国 `FTC 16 CFR Part 464 (Click-to-Cancel)` 明确规定：退订的步数和难度绝不能高于注册购买时的难度！用聊天机器人堵门不让退订属于典型的非法暗黑模式（Dark Pattern），单次违例最高罚款 **`$51,744`**；
  2. **银行端强行拒付反噬（`Visa Reason Code 13.2`）**：现在的年轻消费者找不到退订按钮时，根本不会打你的客服电话——他直接打开手机银行 App 点一下 **“举报该商户拒绝取消订阅并发起拒付（Dispute Recurring Transaction）”**！你不仅保不住这 `$29` 月费，还要倒赔 `$15` 拒付处理费，并把商户拒付率推向 `Visa VAMP` 封号红线！
- **架构师确定性解法（单屏双按钮合规挽留架构 `Single-Screen Symmetric Save-or-Cancel` / `HTTP 451 & HTTP 409`）**：
  - 用户点击“管理订阅 -> 取消”后，在 **同一个屏幕（耗时 `< 5 秒`）** 上同时完成两件事：
    - 上半屏：基于用户的真实画像（如“过去 30 天仅使用 2 次”或“实物盒周期”）展示 **1 个最匹配的挽留胶囊**（如 *“一键免费暂停 2 个月，保留您的全部历史数据与老客特权”* 或 *“切换为每两个月发一次货”*）；
    - 下半屏：并列提供醒目的 **`[不，立即取消我的订阅]`** 按钮，点击即刻生效并签发带有加密时间戳的退订回执邮件，将 `13.2` 拒付率直接压降至 **`0.02%`**！

### Q2：为什么说在订阅流失中，高达 `30%–40%` 的流失用户其实根本“没想退订”，而是因为银行卡过期或卡里恰好没钱而被动流失（`Involuntary Churn`）？怎么把这笔钱无感捞回来？
- **商业痛点与事故还原**：
  - 每年大约有 `30%` 的信用卡会因为到期换卡、遗失补卡或银行升级芯片而更换卡号/有效期；还有大量年轻用户用借记卡或低额度信用卡绑定订阅，月底扣款时恰好差 `$5` 触发 `Code 51 (Insufficient Funds)`。
  - 如果你的计费系统只会机械地在“扣款失败后第 1、2、3 天凌晨 0 点”各重试一次，此时用户还没发工资，3 次重刷全部失败后系统直接把老客账号停用注销！
- **架构师确定性解法（三层非自愿流失无感打捞网 / `HTTP 422 & HTTP 409`）**：
  1. **第一层（扣款前免打扰自动换卡）**：全量启用 `EMVCo Network Token` 与 `VAU / ABU`，用户换新实体卡后令牌自动映射新卡，扣款成功率直接提升 `+4.5%`；
  2. **第二层（发薪日感知择时重试 `Payday-Aligned Smart Retry`）**：对 `Code 51` 余额不足软拒付，自动挂起至 **当月 1 号、15 号或最近一个周五上午 10 点**（北美/欧洲双周发薪入账时刻）再发起重试；
  3. **第三层（免登录一键 Apple Pay 补缴短信）**：若仍失败，发送一条内嵌免登录 `Stripe Link / Apple Pay` 令牌化更新链接的邮件/短信，客户按一下 FaceID 即可恢复订阅！

---

## 三、 🧭 直观可视化图解（Mermaid 决策树 + 架构对比 + 时序图）

### 3.1 订阅制 SaaS 与周期购会员挽留及智能催收平台选型决策树

```mermaid
flowchart TD
    A[订阅制 SaaS 与 DTC 会员挽留及催收平台选型] --> B{核心业务形态与最大流失痛点?}
    B -->|中大型 B2B/B2C SaaS 企业<br/>需按产品活跃度遥测与 ARR 分群定制挽留流并同步 CRM| C[Chargebee Retention<br/>企业级 SaaS 退订挽留标杆 + 深度客戶分群与 CRM 闭环]
    B -->|基于 Stripe / Paddle / Recurly 的 AI 应用与现代 SaaS<br/>追求极速嵌入单屏挽留组件、防薅券冷却与因果 A/B 测试| D[ProsperStack<br/>轻量级嵌入式退订挽留引擎 + 自动 Uplift 实验与冷却锁]
    B -->|高并发流媒体、内容付费与数字会员<br/>核心痛点: 35%+ 流失来自银行卡扣款失败 被动流失| E[Recurly Churn & Smart Dunning<br/>非自愿被动流失打捞之王 + ML 择时重扣与 VAU 自动换卡]
    B -->|Shopify 实物周期购订阅盒 保健品/咖啡/宠物粮<br/>核心诉求: 引导用户一键“跳期 Skip / 换口味 Swap / 暂停”| F[Recharge / Skio<br/>DTC 实物订阅首选 + 免密短信一键延后发货防退订]

    C --> G[核心确定性风控门禁:<br/>1. 囤货原因推暂停禁发折扣 + 365d 防反复点退订薅半价锁 HTTP 403<br/>2. 扣前必查 VAU 换卡 + Cat-1 死卡零重试 + 发薪日择时重扣 HTTP 422<br/>3. FTC 16 CFR 464 单屏对称显式立即退订按钮 + 年续费预通知 HTTP 451]
    D --> G
    E --> G
    F --> G
```

### 3.2 朴素迷宫退订与暴力重刷架构（FTC 巨额罚单 + 老客每季薅半价）vs. 确定性单屏对称挽留、365d 冷却与发薪日催收架构对比

```mermaid
flowchart LR
    subgraph Naive["❌ 朴素迷宫退订、见退订就给5折与每日凌晨盲刷死卡架构 (FTC 重罚 + 被薅走50%毛利)"]
        N1[用户点击取消订阅 或 周期续费刷卡失败] --> N2[逼用户跟机器人聊10分钟才给退订，招致 FTC $51,744/次重罚与 13.2 拒付<br/>或每次点取消都弹 5 折券，被老客每 90 天卡点白嫖半价]
        N2 --> N3[对挂失死卡 Cat-1 连续5天凌晨重刷被 Visa 罚 $15/次<br/>对月底差 $5 的借记卡在发薪前刷爆重试次数直接注销老客]
    end

    subgraph Guarded["✅ 确定性 FTC 单屏对称挽留、365d 冷却与发薪日智能催收架构 (🏆 第 1,400 项单测里程碑)"]
        G1[主动退订请求 / 续费扣款失败事件] --> G2[因果挽留与 365d 冷却锁 HTTP 403:<br/>囤货/出差推一键暂停60天 + 365天内禁重复发挽留折扣]
        G2 --> G3[VAU 预更新与智能催收锁 HTTP 422/409:<br/>Cat-1 硬拒付零重试熔断 + Code 51 对齐 1号/15号/周五发薪日]
        G3 --> G4[FTC Click-to-Cancel 合规锁 HTTP 451:<br/>单屏展示1项挽留+常驻立即取消按钮 + 年费 T-30d 提醒]
    end
```

### 3.3 订阅主动退订 `FTC` 合规单屏分流与被动续费失败（`Smart Dunning`）智能打捞时序图

```mermaid
sequenceDiagram
    autonumber
    participant Sub as 订阅会员 (SaaS / DTC Box)
    participant Gate as 订阅挽留与催收受托控制平面
    participant Engine as 挽留决策引擎 (ProsperStack/Chargebee)
    participant Updater as 卡网更新器 (VAU/ABU) & 收单行
    participant Billing as 订阅账单状态机 (Stripe/Recurly)

    Sub->>Gate: 触发退订入口 或 到达周期续费扣款日
    Gate->>Engine: 校验 FTC 对称点击步数、历史 365 天领券记录与续费响应码
    alt 隐藏立即退订按钮/强制转人工聊天 (违反 FTC 16 CFR 464) 或 年费续费漏发 T-30d 提醒
        Gate-->>Sub: HTTP 451 FTC_CLICK_TO_CANCEL_DARK_PATTERN_OR_ARL_NOTICE_BREACH
    else 365天内已领过挽留券仍发5折码 或 用户因“存货太多”退订却错误塞价格折扣而非暂停
        Gate-->>Engine: HTTP 403 SERIAL_CANCEL_DISCOUNT_GAMING_OR_OVERSTOCK_COUPON_MISMATCH_VETO
    else 未查 VAU/ABU 直接刷过期卡 或 对 Visa Cat-1 硬拒付死卡重复发起重扣招致罚金
        Gate-->>Updater: HTTP 422 VISA_CAT1_HARD_DECLINE_RETRY_OR_MISSING_VAU_UPDATER_BREACH
    else 单屏合规展示“一键暂停60天 / 立即退订” + VAU 换卡与发薪日择时重扣 (HTTP 409)
        Engine->>Billing: 38% 主动退订客选择暂停/降档留存 + 68% 被动失败单经发薪日重扣无感挽回，净省 43% 流失损耗
    end
```

---

## 四、 📊 四大订阅制退订挽留（`Cancel-Flow`）与被动流失催收（`Dunning`）平台横向选型矩阵

| 选型维度 | Chargebee Retention | ProsperStack | Recurly (`Churn & Dunning`) | Recharge / Skio (`Shopify`) |
| :--- | :--- | :--- | :--- | :--- |
| **核心架构定位** | **中大型 SaaS 企业级退订挽留与客户健康度分流中枢** | **现代 SaaS 与 AI 应用首选嵌入式退订挽留与 Uplift 实验引擎** | **高并发订阅制“主动挽留 + 被动催收（Smart Dunning）”一体机** | **Shopify 实物周期购订阅盒（Skip/Swap/Pause）领导者** |
| **主动退订挽留（Voluntary Deflection）能力** | **极强**：支持按 CRM 字段、席位使用率、生命周期定制多分支单屏挽留体验 | **极强（开箱即用）**：5 分钟嵌入 Stripe/Paddle，内置防薅券冷却锁与保留率净增益归因 | 内置合规退订原因调查与暂停/优惠券挽留组件 | **实物盒最强**：原生支持“下月跳过、换口味、改发货频次、赠小样” |
| **被动扣款失败打捞（Involuntary Dunning）** | 依赖底层计费引擎（Chargebee Billing）执行重试策略 | 专注主动退订流，被动催收交由底层 Stripe / Chargebee 处理 | **全行业最强**：基于百亿级交易训练的发薪日/时段动态重试模型，平均多捞回 `8%–14%` 营收 | 支持针对实物发货周期的智能重试与免密短信一键换绑卡 |
| **`FTC Click-to-Cancel` 与各州 `ARL` 法案合规** | 原生提供符合 FTC 单屏双按钮規範的合规模板与审计日志 | 原生内置 `FTC Click-to-Cancel` 合规模式（确保常驻立即取消按钮） | 原生支持加州 `ARL` 试用结束提醒、年费续费提前 30 天通知与一键退订 | 原生支持免登录魔法链接（Magic Link）两步合规管理或取消订阅 |
| **计费模式（`official_list_price`）** | 按月度活跃订阅規模或企业套件定额订阅 | 按月度基础订阅费（约 `$200–$800+/月`）或按成功挽回收入分成 | 基础平台费 + 交易流水比例（约 `0.8%–1.25%`） | 基础月费 + 订阅结账流水抽成（Skio 提供固定月费零抽成方案） |

---

## 五、 🧪 订阅制防薅半价挽留券、发薪日智能催收与 `FTC` 合规测算与 7-Card 基准报告

### 5.1 季度老客卡点假退订薅 5 折券毛利流失、被动扣款失败死卡罚金与流失 ARR 及 `FTC / 13.2` 拒付损失测算（Synthetic Benchmark）

假设某年 ARR `$8,000 万` 的混合订阅制 SaaS 与消费级会员平台，每季度在主动退订窗口与周期续费扣款环节面临的 **老客每 90 天点击取消白嫖半价券导致的 ARR 折让、银行卡过期或月底余额不足导致的非自愿被动流失、对 `Visa Cat-1` 硬拒付盲目重试招致的卡网罚金、以及退订入口过深引发的 `13.2` 拒付损失池** 为 **`$480,000 / 季度`**（`provenance: synthetic`, `independently_reproduced: false`）：

| 评估维度 | 传统迷宫退订 + 见退订就给5折 + 每日凌晨盲刷 (Baseline) | 启用 `FTC` 单屏对称挽留 + `365d` 冷却暂停 + `VAU` 发薪日催收 Agent | 净改善幅度 |
| :--- | :--- | :--- | :--- |
| **因“假装点退订薅羊毛”损失的存量老客正价毛利** | `18.5%` 挽留单系每季重复领券老客 | **`0.0%`**（`HTTP 403` 严格执行 `365天` 折扣冷却锁 + 囤货/低频优先推一键暂停/降档） | **100% 堵死假退订薅半价漏洞** |
| **周期续费刷卡失败后的最终成功打捞率（Dunning Recovery）** | `41.0%`（定时连刷 4 天后直接销户） | **`71.5%`**（`HTTP 422/409` 扣前 `VAU/ABU` 自动换新卡 + 对齐 1号/15号/周五发薪日重试） | **被动流失打捞率飙升 `+30.5 pts`** |
| **`Visa Cat-1` 硬拒付重试罚金与 `13.2` 拒付争议率** | `$42,000 / 季度` 罚金与拒付损失 | **`$0`**（`HTTP 422/451` 硬拒付零重试秒熔断 + `FTC` 单屏常驻立即退订按钮消灭拒付） | **100% 零卡网罚金与零合规风险** |
| **季度订阅流失、挽留折扣滥用、死卡重刷罚金与拒付净损耗** | `$480,000 / 季度` | **`$273,600 / 季度`** | **净省 `$206,400 / 季度` (`43.0%`)** |

```chart
{
  "data": {
    "values": [
      { "category": "1. 续费刷卡失败未查VAU且错过发薪日导致被动流失", "mode": "传统固定重试与无冷却挽留基线", "cost_usd": 190000 },
      { "category": "1. 续费刷卡失败未查VAU且错过发薪日导致被动流失", "mode": "FTC合规单屏挽留与智能催收Agent(第1400测)", "cost_usd": 108300 },
      { "category": "2. 老客每90天假点退订白嫖5折券及囤货错发折扣", "mode": "传统固定重试与无冷却挽留基线", "cost_usd": 135000 },
      { "category": "2. 老客每90天假点退订白嫖5折券及囤货错发折扣", "mode": "FTC合规单屏挽留与智能催收Agent(第1400测)", "cost_usd": 76950 },
      { "category": "3. 退订迷宫违反FTC新规引发13.2银行强行拒付罚金", "mode": "传统固定重试与无冷却挽留基线", "cost_usd": 90000 },
      { "category": "3. 退订迷宫违反FTC新规引发13.2银行强行拒付罚金", "mode": "FTC合规单屏挽留与智能催收Agent(第1400测)", "cost_usd": 51300 },
      { "category": "4. 对Visa Cat-1挂失/关户死卡盲目重试遭$15/次重罚", "mode": "传统固定重试与无冷却挽留基线", "cost_usd": 65000 },
      { "category": "4. 对Visa Cat-1挂失/关户死卡盲目重试遭$15/次重罚", "mode": "FTC合规单屏挽留与智能催收Agent(第1400测)", "cost_usd": 37050 }
    ]
  },
  "semantic_types": {
    "category": "Category",
    "mode": "Category",
    "cost_usd": "Amount"
  },
  "chart_spec": {
    "chartType": "Grouped Bar Chart",
    "title": "订阅制SaaS与会员退订挽留、FTC合规与智能催收(第1,400项单测里程碑)前后季度损耗对比 (净省 $206.4k / 43%)",
    "subtitle": "单位：美元/季度 (Synthetic Benchmark, independently_reproduced=false · 🏆 历史性第1,400项单元测试重大里程碑)",
    "encodings": {
      "x": "category",
      "y": "cost_usd",
      "group": "mode"
    }
  }
}
```

### 5.2 确定性策略评估器代码（Python Control Plane Guard）

```python
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class SaasSubscriptionCancelFlowRetentionPolicyInput:
    quarterly_involuntary_churn_coupon_gaming_and_ftc_dispute_pool_usd: float = 480000.0
    retention_discount_given_within_365d_cooldown_or_on_overstock_reason: bool = False
    cat1_hard_decline_retried_or_expired_card_charged_without_vau_updater: bool = False
    cancel_requires_phone_chat_or_lacks_persistent_1click_ftc_cancel_btn: bool = False
    single_screen_pause_deflection_and_payday_vau_smart_dunning_ready: bool = False
```

---

## 六、 🛠️ 商业上线风控与架构评审 Checklist

- [ ] **退订原因精准映射（囤货推暂停）与 `365天` 挽留折扣冷却锁（`HTTP 403`）**：当用户选择“存货太多/暂时不用/出差”时是否唯一推荐“一键免费暂停 30–60 天或跳过本期”而非乱发折扣券？是否对过去 365 天内已使用过挽留折扣的账号彻底屏蔽二次发券？
- [ ] **扣款前 `VAU / ABU` 自动换卡、`Visa Cat-1` 硬拒付零重试与发薪日择时催收（`HTTP 422`）**：续费前是否自动同步卡组织换卡更新器？遇到 `04/41/43/R0/R1` 硬拒付是否立即停止重试防 `$15` 罚金，并将 `Code 51` 余额不足软拒付对齐至 `1号/15号/周五` 发薪日重试？
- [ ] **`FTC Click-to-Cancel (16 CFR Part 464)` 单屏对称常驻“立即取消”按钮与 `ARL` 预通知（`HTTP 451`）**：线上退订步数是否不高于注册步数？挽留页是否在单屏内同时展示定制挽留方案与常驻可见的“立即取消”按钮，并在年费续费前 30 天自动发送带一键退订链接的合规邮件？
- [ ] **免登录一键 `Apple Pay / Stripe Link` 补缴恢复链接（`HTTP 409`）**：催收通知邮件与短信是否内嵌免密码登录的单次令牌化支付更新页，让被动欠费老客在手机上 3 秒完成换卡续命？
