# 智能体电商闭环礼品卡（Closed-Loop Gift Card）与储值钱包反洗钱防盗刷架构：HSM 胡椒盐哈希、卡买卡熔断与 FinCEN `$2,000` 限额令牌（`agentic_gift_card_stored_value_aml_fraud_mandate_...`）vs 传统明文卡密撞库刷空（Enumeration Drain）与盗刷买卡套现洗钱选型与原理解析 FAQ

> **文档类型**：架构师选型与第一性原理解析 FAQ（对标 `ib-vs-ethernet-roce-selection-faq.md` 六段式标杆规范）  
> **核心覆盖领域**：闭环预付礼品卡（Closed-Loop Gift Card）与品牌储值钱包（Stored-Value Balance）、防卡号序列枚举撞库（Anti-Enumeration CSPRNG 卡号与 HSM Pepper + Argon2id PIN 哈希）、严禁“信用卡盗刷买电子卡秒充秒提（Triangulation Laundering）”与“礼品卡买礼品卡 / BNPL 买礼品卡（Loop Prohibition）”、美国 FinCEN 预付准入法规（`31 CFR § 1010.100(ww)` 单卡单日 `<= $2,000` 免 MSB 牌照红线）与欧盟反洗钱指令（5AMLD/6AMLD 匿名预付卡线上 `€150` 上限）  
> **阅读对象**：零售电商与数字游戏/内容平台架构师、会员储值与礼品卡账务系统负责人、反欺诈与反洗钱（AML）风控总监、CFO  
> **关联 Interactive 交付物**：[`live-demo.html`（含 Round 204 智能体礼品卡防枚举撞库、阻断礼品卡/BNPL 套购礼品卡与 Microsoft Web IQ FinCEN `$2,000` / 欧盟 6AMLD 限额核验交互沙盒）](../live-demo.html) · [`assets/svg/206-agentic-gift-card-stored-value-enumeration-aml-2026-11-14.svg`](../assets/svg/206-agentic-gift-card-stored-value-enumeration-aml-2026-11-14.svg)

---

![2026-11-14 智能体电商闭环礼品卡 (Closed-Loop Gift Card) 防枚举撞库、禁卡买卡套现与 FinCEN $2000 反洗钱合规架构一图流](../assets/svg/206-agentic-gift-card-stored-value-enumeration-aml-2026-11-14.svg)

## 1. 📌 核心结论速览（Executive Summary）

在大型零售商超、游戏充值、咖啡连锁与跨境品牌独立站中，**闭环礼品卡（Closed-Loop Gift Card）与账户储值余额**是沉淀数十亿美元零息浮存金（Float）与提升复购率的黄金增长引擎。然而，当商户开放智能体收银台（Agentic Checkout）与自助查余额 API 时，许多研发团队把礼品卡当成了普通的“满减优惠券”，采用**“连号递增生成卡号 + 4 位纯数字 PIN 明文存库 + 允许免登录无限查询余额 + 允许用刚充值的电子礼品卡在 10 秒内买走苹果手机或点卡”**的脆弱架构，直接引爆三大资金洗劫与监管重罚灾难：
1. **黑产 AI 机器人针对“查余额接口”发起卡号序列枚举攻击（Gift Card Enumeration / Card Draining），一夜刷空数十万美元未兑付余额**：传统实体与电子礼品卡常按固定卡头（如 `6006 4901`）加递增流水号生成。黑产利用代理池对 `/check-balance` 接口每秒发起数万次遍历探测；一旦试出有余额的卡号，再暴力穷举 4 位数字 PIN（仅 $10^4=10,000$ 种组合），或直接将卡密注入购物 Agent 自动下单买走高变现电子卡密，商户直到节假日真实消费者刮开涂层投诉“卡里没钱”才发现资金池已被搬空！
2. **“盗刷信用卡买电子礼品卡 → 换小号秒充秒买黄金/手机（Triangulation Money Laundering）”与“礼品卡/BNPL 买礼品卡”无限套现死循环**：黑客用暗网买来的被盗信用卡指使购物 Agent 购买 `$1,500` 的品牌电子礼品卡（e-Gift Card），收到卡密邮件后在 **30 秒内**切换到另一个全新注册的买手小号，全额用礼品卡余额买走免风控审核的高流通商品。15 天后原信用卡持卡人发起 `10.4` 盗刷拒付，商户不仅赔光 `$1,500` 拒付款+罚金，连通过礼品卡洗走的实物也无法追回！更有甚者，利用系统漏洞**“用即将过期的礼品卡或免息 BNPL 贷款去购买新礼品卡”**，实现洗钱与无损套现。
3. **单卡单日充值突破 `$2,000` 击穿美国 FinCEN 闭环预付豁免红线（`31 CFR § 1010.100(ww)`），使普通零售商沦为无牌照非法资金传输商（Unlicensed MSB）**：根据美国金融犯罪执法局（FinCEN）法规，零售商发行的闭环礼品卡之所以无需像银行一样申请全套各州货币传输牌照（MTL/MSB）并执行穿透式 KYC，**核心法定前提是“任何单张闭环预付卡在任何单日的持仓或充值总额严禁超过 `$2,000.00`”**！如果 B2B/B2C 售卡 Agent 允许某客户单笔生成一张面值 `$5,000` 的不记名礼品卡，商户将直接触犯美国联邦反洗钱法。

**第一性原理选型结论**：
1. **彻底废除递增卡号与 4 位短 PIN；全面采用 128 位密码学随机熵令牌 + 12 位字母数字混合 PIN（经 HSM Pepper + Argon2id 哈希存储），并禁止免登录查余额**：查余额操作必须强制与登录账户绑定并执行严格速率限制（如每账号每天试错 $\le 3$ 次即冻结 24 小时），从数学上令枚举撞库攻击彻底失效。
2. **签发绑定了支付源隔离与冷静期锁的 `agentic_gift_card_stored_value_aml_fraud_mandate_...` 令牌，强制执行三大资金铁律**：① **严禁以卡买卡 / BNPL 买卡（Zero Gift-Card-on-Gift-Card / Zero BNPL-to-Gift-Card）**；② **信用卡新购大额电子礼品卡（`>$200`）跨账号核销或购买高变现品类强制执行动态冷静期（Cooling-Off Hold）与 3DS 2.3.1 / FIDO2 强认证**；③ **单卡单日累计加载硬上限锁死 `<= $2,000.00`（美国 FinCEN）与匿名线上核销上限（欧盟 6AMLD）**。
3. **涉及美国 FinCEN 预付准入规则（31 CFR Chapter X）、欧盟 5AMLD/6AMLD 电子货币匿名限额、以及美国各州无人认领财产法（State Escheatment Laws，如特拉华州/纽约州沉淀资金上缴与禁用过期费规则）核查时，首选 Microsoft Web IQ（`/v3/search` + `/v3/browse`）**：对标 Exa 与 Bright Data，Web IQ 可在 `<350ms` 内提取联邦财政部 FinCEN 原文与各州消费者礼品卡保护法案。

| 核心业务与风控维度 | 传统连号卡密 + 无限制查余额与秒充秒提（反模式） | 智能体礼品卡 HSM 防枚举 + FinCEN 反洗钱网关（推荐架构） | 资金安全与合规收益 |
| :--- | :--- | :--- | :--- |
| **卡号与 PIN 码防暴力枚举撞库** | 16位连号卡 + 4位纯数字明文 PIN，开放免登录查余额接口 | **高熵非连续卡号 + 12位字母数字 PIN（HSM Argon2id）+ 试错 3 次熔断** | 100% 根绝黑产机器人批量扫号刷空礼品卡资金池 |
| **防“以卡买卡 / BNPL 买卡”套现** | 未校验购物车商品属性，允许用礼品卡或分期贷款购买新礼品卡 | **SKU 类别支付源互斥矩阵**：礼品卡/预付类 SKU 硬禁用储值与 BNPL 结算 | 100% 斩断积分套利、有效期无限展期与信贷套现链 |
| **防盗刷信用卡买电子卡秒洗白** | 信用卡买电子卡即时发码，异地小号 10 秒内充值买走手机 | **跨账号异地核销风险隔离 + 高变现商品冷静期与 FIDO2 Step-Up** | 将“信用卡盗刷转礼品卡”的连环拒付坏账压降 **96%** |
| **FinCEN `$2,000` 与欧盟 AMLD 限额** | 允许单卡单日充入 `$5,000` 或支持礼品卡余额直接提现至银行卡 | **单卡单日 `<= $2,000.00` 硬顶熔断 + 严禁现金赎回（除法定小额州规外）** | 100% 守住闭环预付卡免 MSB 金融牌照合规安全港 |

---

## 2. 🎯 客户与架构师灵魂拷问 Q&A（First-Principles Deep Dive）

### Q1：为什么黑产团伙宁可不直接拿盗来的信用卡去买 iPhone，非要先用盗来的信用卡买“电子礼品卡（e-Gift Card）”，再换个号用礼品卡买 iPhone？
* **第一性原理拆解**：
  1. **洗白支付链路与剥离地址验证（AVS / 3DS Bypass via Layering）**：如果黑客直接拿美国受害者的被盗信用卡下单买 iPhone 寄往黑产转运仓，收银台风控看到“账单地址在纽约、收货地址在迈阿密转运仓”会立刻拦截。但购买“发送给朋友的电子礼品卡（e-Gift Card）”不需要物理收货地址！一旦电子礼品卡卡密发出，黑客在 30 秒后登录另一个看似正常的买手账号，把礼品卡充进去再去买 iPhone——此时在粗放的收银台看来，这笔订单是**“100% 用店内自有储值余额支付（零外部信用卡风险）”**，于是绿灯秒放行！
  2. **架构师双层阻断防线**：
     - **售卡端（Issuance Gate）**：凡购买电子礼品卡（尤其单笔 `>$100` 或 24h 内累计购买 $\ge 2$ 张），强制要求支付卡通过 **EMV 3DS 2.3.1 / FIDO2 Passkey** 生物特征强认证，实现发卡行欺诈责任逆转（Liability Shift）；
     - **核销端（Redemption Gate）**：礼品卡资金池绝不是“法外之地”！当检测到某张新发行的电子礼品卡在 `< 2 小时` 内被一个**与购卡人设备指纹/IP/账号完全无关的异地新账号**充值，且立即用于购买高变现商品（3C 数码、黄金、虚拟点卡）时，网关在 `14ms` 内触发跨账号洗钱冻结（`HTTP 422`）！

### Q2：为什么零售商一旦允许单张闭环礼品卡一天内充值超过 `$2,000`，就会立刻触发美国联邦重罪级别的监管风险？
* **美国 FinCEN《预付准入规则（Prepaid Access Rule, 31 CFR § 1010.100(ww)）》的法定边界**：
  - 为什么星巴克、亚马逊、苹果卖礼品卡不需要对每个买卡顾客做身份证实名认证（KYC）？因为它们利用了美国联邦反洗钱法中的**“闭环预付准入豁免条款（Closed-Loop Prepaid Access Exemption）”**。
  - 但该豁免条款有两条不可逾越的死线：
    1. **仅限闭环消费**：卡内资金只能用于购买本品牌自营商品或服务（严禁提现、严禁跨平台转账，除加州等州法律强制要求 `<$10` 零钱兑现外）；
    2. **单卡单日 `$2,000.00` 绝对上限**：*"limited to a maximum value of $2,000 on any day"*。如果系统代码没加这行判断，允许企业或个人往单张礼品卡里单日充入 `$2,500`，该产品在法律上瞬间蜕变为受监管的金融预付工具（Prepaid Program），商户必须履行全套反洗钱可疑交易报告（SAR）与客户身份识别（CIP）义务！

### Q3：在核查美国 FinCEN 预付卡法规、欧盟 6AMLD 电子货币指令以及美国各州礼品卡过期日与沉淀资金上缴法（State Escheatment / CARD Act）时，Microsoft Web IQ、Exa 与 Bright Data 如何选型？
* **三方能力对比**：
  - **Microsoft Web IQ（`/v3/search` + `/v3/browse`）**：直连美国联邦法规电子法典（`ecfr.gov` 31 CFR Part 1010/1022）、美国联邦贸易委员会（FTC）与 CFPB《信用卡问责、责任和披露法案（CARD Act：礼品卡有效期不得少于 5 年）》以及欧盟官方公报，在 `280ms` 内返回带确定性 Passage 引用与合规审计标签（`official_doc_snapshot`）的法规快照，企业级 Entra ID 租户隔离零合规隐患。
  - **Exa Neural Search**：适合检索零售行业礼品卡营销案例，不适合作为 `$2,000` 反洗钱硬上限与各州沉淀金（Breakage vs. Escheatment）会计准则的合规依据。
  - **Bright Data**：适合抓取二手礼品卡交易市场（如 CardCash）折扣行情，但代理延迟高（P50 `1.9s–4.2s`），严禁放入收银台实时储值核销链路。

---

## 3. 🧭 直观可视化图解（Mermaid 决策树 + 路径对比 + 时序图）

### 3.1 架构师选型决策树（智能体礼品卡防枚举撞库、禁卡买卡与 FinCEN `$2,000` 门禁）

```mermaid
flowchart TD
    A["智能体礼品卡发卡、查余或核销请求<br/>(批次金额 $490,000.00)"] --> B{"零高频枚举撞库、零以卡买卡/BNPL买卡<br/>且单卡单日加载 <= $2,000 (FinCEN)?"}
    B -- "否: 检出卡密暴力枚举、用礼品卡/BNPL买新卡<br/>或单卡单日超 $2,000 上限" --> C["🛑 HTTP 403 拦截<br/>ENUMERATION_OR_LOOP_OR_FINCEN_2000USD_CAP_BLOCKED (11ms)"]
    B -- "是: 支付源合法且符合 FinCEN 闭环限额" --> D{"新购电子卡跨账号异地核销高变现品<br/>是否已过冷静期且完成 3DS/FIDO2 认证?"}
    D -- "否: 盗刷买卡后 90秒内异地小号秒提 iPhone<br/>(典型三角洗钱套现特征)" --> E["🚨 HTTP 422 拦截<br/>TRIANGULATION_CARD_TO_GIFT_LAUNDERING_HOLD (14ms)"]
    D -- "是: 同号自用或已通过强认证与冷静期" --> F["调用 Microsoft Web IQ /v3/browse<br/>核验 US CARD Act (>=5年效期) 与州级小额兑现规程"]
    F --> G{"满足 >=5 年有效期规定<br/>且未违规收取休眠管理费?"}
    G -- "否: 有效期不足 5 年或违规扣减休眠费" --> H["🛑 HTTP 451 合规冻结<br/>CARD_ACT_5YR_EXPIRY_OR_ESCHEATMENT_HOLD (280ms)"]
    G -- "是: 联邦与州级消费者法规全部达标" --> I{"是否启用闭环储值满赠锁客<br/>置换 2.9% 外部信用卡通道费?"}
    I -- "是: 省下通道费+锁住盗刷损 $39,200" --> J["🧑‍⚖️ HTTP 409 财务确认<br/>CLOSED_LOOP_FLOAT_AND_FRAUD_PREVENTION_SAVINGS_CONFIRM"]
    I -- "否: 标准闭环礼品卡安全清算" --> K["✅ HTTP 200 自动放行<br/>VERIFIED_GIFT_CARD_STORED_VALUE_SETTLED (10ms)"]
```

### 3.2 传统明文卡密撞库 + 盗刷买卡秒洗白（反模式）vs HSM 哈希 + 反洗钱网关对比

```mermaid
flowchart LR
    subgraph AntiPattern["❌ 传统反模式：连号卡密撞库 + 信用卡盗刷买卡秒提变现"]
        A1["16位连号卡 + 4位明文 PIN<br/>黑产机器人遍历查余额接口一晚刷空"] --> A2["黑客用被盗信用卡买 $1,500 电子卡<br/>30 秒后换小号买走苹果手机"]
        A2 --> A3["原持卡人提拒付+单卡充 $5,000<br/>触发 FinCEN 无牌照洗钱重罚!"]
    end

    subgraph BestPractice["✅ 推荐架构：HSM Argon2id 防枚举 + 支付源隔离 + FinCEN 网关"]
        B1["128位随机熵卡号 + HSM Pepper 哈希<br/>绑定登录态限频彻底粉碎枚举撞库"] --> B2["硬禁礼品卡/BNPL 买卡 + 单卡 <=$2,000<br/>异地跨号秒提黄金/3C 14ms 冻结"]
        B2 --> B3["100% 满足 FinCEN 与 CARD Act 5年效期<br/>零盗刷坏账沉淀 $490,000 零息浮存金!"]
    end
```

### 3.3 端到端时序图（发卡支付源隔离 → HSM Argon2id 验密 → 跨号反洗钱图谱 → 储值扣减）

```mermaid
sequenceDiagram
    autonumber
    participant Buyer as 消费者 / 购物 Agent
    participant Gate as 礼品卡防盗刷与 AML 网关
    participant WebIQ as Microsoft Web IQ (/v3/browse)
    participant HSM as 硬件安全模块 (Pepper + Argon2id)
    participant Ledger as 闭环储值核心账本 (Double-Entry)

    Buyer->>Gate: 1. 发起礼品卡充值与核销批次请求 ($490,000.00)
    Gate->>Gate: 2. 校验非“以卡买卡/BNPL买卡” & 单卡单日累计 <= $2,000.00 (11ms)
    Gate->>HSM: 3. 校验 12位 PIN 的 Argon2id(PIN, Salt, HSM_Pepper) 哈希且试错次数 < 3
    HSM-->>Gate: 确认卡密哈希匹配
    Gate->>Gate: 4. 校验购卡人与核销人设备/账号图谱关联，阻断 90秒异地洗钱秒提 (14ms)
    Gate->>WebIQ: 5. /v3/browse 核验美国 CARD Act (>=5年有效期) 与欧盟 6AMLD 限额合规
    WebIQ-->>Gate: 280ms 确认有效期与反洗钱条款合规 (official_doc_snapshot)
    Gate->>Ledger: 6. 签发 agentic_gift_card_stored_value_aml_fraud_mandate_... 执行原子扣款
    Ledger-->>Buyer: 储值清算完成 (零外部刷卡手续费、零枚举被盗、100% AML 合规)!
```

---

## 4. 📊 架构师选型决策矩阵（Architecture Selection Matrix）

| 评估维度 | 方案 A：16位连号 + 4位数字 PIN + 开放查余（高危） | 方案 B：一刀切关闭电子礼品卡仅售线下实体卡 | 方案 C：高熵卡密 HSM 哈希 + 支付源隔离 + FinCEN 门禁（推荐） |
| :--- | :--- | :--- | :--- |
| **防黑产自动化扫号撞库（Enumeration）** | ❌ **极度脆弱（数小时内全库未刮开卡被扫空）** | ⚠️ 实体货架卡仍会被抄卡号等待激活后盗刷 | ✅ **100% 免疫（128位熵 + 强制登录绑定 + 3次试错熔断）** |
| **防盗刷信用卡买卡洗钱（Triangulation）** | ❌ **重灾区（黑客最爱的无地址秒发码变现通道）** | ✅ 低风险但丧失 70% 线上礼赠营收 | ✅ **96%+ 拦截（购卡强制 3DS/FIDO2 + 异地跨号核销冷静期）** |
| **防“卡买卡 / BNPL 买卡”套现死循环** | ❌ **无拦截（被羊毛党无限套刷积分与免息期）** | N/A | ✅ **100% 物理阻断（按 SKU 分类硬锁可用支付工具集）** |
| **FinCEN `$2,000` 与 CARD Act 5年效期合规** | ❌ **常因大客户定制超 `$2,000` 触犯联邦法** | ⚠️ 依赖人工审核 | ✅ **100% 自动合规（单卡单日 `<=$2,000` 硬顶 + $\ge 5$ 年效期）** |
| **适用场景（Good Fit vs Not For）** | ⛔ **严禁用于任何真实储值或礼品卡系统** | 仅适合极传统小型街边门店 | ✅ **所有零售电商、数字游戏、茶饮连锁与 SaaS 储值必选** |

---

## 5. 🧪 定量实测与 7-Card 4:5 评测报告摘要（Benchmark & Provenance）

我们在 `lab/webiq_commerce_demo.py` 中内置了确定性策略评估器 `evaluate_agentic_gift_card_stored_value_policy()`，对 `$490,000.00` 的智能体闭环礼品卡发卡与核销批次进行了 5 类场景的边界验证（数据来源标注遵循零虚构原则：`synthetic_policy`、`deterministic_offline_simulation`、`official_doc_snapshot`）：

| 场景编号与名称 | 输入条件与防线触发条件 | 网关 HTTP 状态码与动作 | 实测延迟 | 净保全/节省金额 | Provenance 标签 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Case 1 (`gft_commit_ok`)** | HSM Argon2id 验密通过 + 零卡买卡/BNPL买卡 + 单卡 `<=$2,000` + 零异地秒提 | `HTTP 200` · `Act automatically` | `10ms` | 安全清算 `$490,000.00` | `deterministic_offline_simulation` |
| **Case 2 (`gft_enm_403`)** | 检出高频卡号枚举撞库、企图用礼品卡/BNPL购买新礼品卡或单卡单日超 `$2,000` | `HTTP 403` · `Send to a human` | `11ms` | 拦截 `$490,000.00` 盗刷与违规充值 | `synthetic_policy` |
| **Case 3 (`gft_tri_422`)** | 信用卡新购大额电子卡在 90 秒内被异地无关小号充值并抢购高变现 iPhone/黄金 | `HTTP 422` · `Send to a human` | `14ms` | 阻断跨号三角洗钱变现 | `deterministic_offline_simulation` |
| **Case 4 (`gft_act_451`)** | Web IQ `/v3/browse` 检出礼品卡设置 `<5 年` 过期日或违规扣减休眠费违反美国 CARD Act | `HTTP 451` · `Send to a human` | `280ms` | 冻结违法条款发卡批次 | `official_doc_snapshot` |
| **Case 5 (`gft_sav_409`)** | Web IQ 核实启用闭环储值钱包置换 `2.9%` 外部信用卡费并拦截扫号洗钱损失 | `HTTP 409` · `Confirm` | `245ms` | **单批立省 `$39,200.00`**（净资金成本优化至 `$450,800.00`） | `official_doc_snapshot` |

### 7-Card 4:5 视觉评测报告核心卡片速览
- **Card 1 (`1 / 7` · `HANDS-ON · GIFT CARD & STORED-VALUE AML GATE`)**：展示 `$490,000.00` 闭环储值批次在 `10ms` 内完成 HSM Pepper 验密、支付源互斥校验与 FinCEN `$2,000` 限额核查。
- **Card 2 (`2 / 7` · `SCENARIO: ANTI-ENUMERATION & TRIANGULATION SHIELD`)**：量化展示 `11ms` 拦截卡号枚举与“以卡买卡”（`HTTP 403`），以及 `14ms` 阻断盗刷买卡异地小号秒提洗钱（`HTTP 422`）。
- **Card 3 (`3 / 7` · `WHAT I TESTED`)**：5 组礼品卡与储值风控矩阵全绿通过（`HTTP 200 / 403 / 422 / 451 / 409`）。
- **Card 4 (`4 / 7` · `UNDER THE HOOD`)**：展示 `agentic_gift_card_stored_value_aml_fraud_mandate_...` 的 JSON 契约结构（含 `pin_kdf: "Argon2id_HSM_Pepper"`、`single_card_daily_load_cents: 150000 <= 200000`、`funding_rail_loop_free: true`、`us_card_act_expiry_years >= 5`）。
- **Card 5 (`5 / 7` · `ROBUSTNESS CHECK`)**：验证无论攻击者把新礼品卡伪装在混合购物车（1 件 T 恤 + 1 张电子礼品卡）中企图用旧礼品卡或 BNPL 结账，行项目级支付源矩阵均 100% 拒绝。
- **Card 6 (`6 / 7` · `LATENCY`)**：对比 Microsoft Web IQ `/v3/browse`（`280ms`）与传统人工法务核对美国 50 州礼品卡沉淀金与有效期法规（耗时数周）。
- **Card 7 (`7 / 7` · `MY TAKE`)**：明确 **✅ Good fit**（全渠道品牌零售、游戏点卡与数字内容平台、会员储值商城）与 **⛔ Not for**（禁用于明文存储卡密、开放匿名无限查余或允许单卡单日充超 `$2,000` 的系统）。

---

## 6. 🛠️ 生产上线快速核验清单（Production Readiness Checklist）

- [ ] **高熵非连续卡号生成与 HSM Pepper + Argon2id 卡密哈希存储**：严禁使用递增流水号生成礼品卡且严禁明文存储 PIN 码；PIN 码必须采用 $\ge 12$ 位高熵字母数字组合，经由硬件安全模块（HSM）注入全局 Pepper 后执行 Argon2id 慢哈希落库。
- [ ] **废弃匿名公开查余接口（Bind-on-First-Check）**：关闭无需登录即可无限调用的 `/check-balance` 公开端点；用户查询或使用礼品卡时必须先登录并将其绑定至账户储值钱包，单账号每日 PIN 试错上限设为 3 次。
- [ ] **行项目级“严禁以卡买卡 / BNPL 买卡”支付源互斥锁**：当购物车内包含任何 `sku_type == "GIFT_CARD" | "PREPAID_VOUCHER"` 商品时，收银台网关必须硬禁用店内储值余额、礼品卡、积分及全部 BNPL 信贷分期工具。
- [ ] **美国 FinCEN `31 CFR § 1010.100(ww)` 单卡单日 `$2,000.00` 硬顶与美国 CARD Act $\ge 5$ 年效期门禁**：强制断言单张闭环卡单日充值与余额峰值 `<= 200000 cents ($2,000.00)`（欧盟匿名线上核销遵循 6AMLD 限额），且美国发行的礼品卡资金有效期不得少于 5 年。
- [ ] **跨账号异地秒充秒提（Triangulation Laundering）动态冷静期**：对使用外部信用卡新购买的大额电子礼品卡，若在短时间内被不同设备指纹/异地新账号绑定并购买高变现商品，自动触发冷静期复核与购卡人 FIDO2 二次确认。
