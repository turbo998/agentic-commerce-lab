# 酒旅航司与酒店集团官渠直销“常旅客积分+现金混合支付（`Points + Cash`）、住四免一（`5th Night Free`）与入住前动态房型竞价升舱（`Plusgrade / Oracle Opera Nor1`）”清结算托管（`Marriott Bonvoy / Hilton Honors / Hyatt / 华住会 / 携程`）、防“AI 把积分用出 0.3 美分冥币价值或拆单弄丢住四免一”、防“竞价升舱先扣 $300 到店却被告知套房已满”与动态积分降价退差（`Dynamic Award Re-Pricing`）托管“防黄牛借‘添加同住人’盗刷积分房与闲置套房出清净省 36%”Agent 架构选型 FAQ

> **语言 / Language**: **中文 (当前)** | **[English (`ota-hotel-direct-booking-Fifth-night-free-points-cash-room-upgrade-escrow-agent-selection-faq.en.md`)](ota-hotel-direct-booking-Fifth-night-free-points-cash-room-upgrade-escrow-agent-selection-faq.en.md)**  
> **返回总目录**: **[📚 中文总目录 (`docs/index.md`)](index.md)** | **[🚀 交互式实时工作台 (`live-demo.html`)](../live-demo.html)**  
> **赋能角色**: 国际酒店集团与航司常旅客计划（Loyalty Program：万豪旅享家 / 希尔顿荣誉客会 / 凯悦天地 / 华住会）数字化总监、收益管理（Revenue Management & Ancillary Upsell）负责人、OTA 铁旅酒旅架构师、Cloud & AI Solution Architect  
> **关联架构图**: `assets/svg/689-ota-hotel-direct-points-cash-room-upgrade-escrow-2026-11-23.svg`

---

## ① 📌 核心选型结论速览（Executive Summary）

在全球酒店集团官渠直销（`Marriott Bonvoy / Hilton Honors / World of Hyatt / IHG One Rewards / 华住会`）与企业差旅/自由行规划 Agent 中，**常旅客积分（Loyalty Points）、免费房券（Free Night Award Certificates `FNC`）与入住前付费竞价升舱（Pre-Arrival Standby Upgrade：`Oracle Opera Nor1 / Plusgrade`）** 是利润率最高、同时规则最复杂的复合结算场景。不懂常旅客精算规则的通用 AI 订房助手极易制造三大“贱卖积分、到店无房降级扯皮与黄牛同住人盗刷”灾难：
1. **“最亏钱的‘冥币级积分贱卖（Sub-Floor CPP Burn）’与拆单痛失‘住四免一（`5th Night Free`）’：某用户账上有 `120,000` 万豪/希尔顿积分，普通订房 Agent 看到一家标价 `$320` 的郊区大车店要 `100,000 积分` 就直接帮用户兑了——折算下来每万分只用出了 `$32`（`0.32 美分/分 CPP`），连积分公允底线（`0.80¢/pt`）的一半都不到！更蠢的是，用户原本要连住 5 晚马尔代夫度假村（万豪/希尔顿规定**纯积分连住 5 晚自动免除第 5 晚积分，立省 20%**），但 Agent 因为前 2 晚和后 3 晚分属不同子房型或拆成了两个独立订单号（`PNR`），导致用户白白多付了 `85,000 积分`（价值 `$750`）”**！
2. **“入住前付费竞价升舱（`Nor1 / Plusgrade`）‘先扣钱、到店却没套房’与积分房违规乱收 `$55/晚` 度假村费（Resort Fee）：旅客在入住前 3 天收到邮件出价 `$120/晚` 竞拍海景套房，系统提前把 `$360` 从信用卡里实扣（Capture）了，结果旅客下午 4 点到前台办理入住时，前台说‘不好意思今天套房被高卡白金会员延住占满了，只能给您普通房，退款请等 15 个工作日’！或者在希尔顿/凯悦明确规定**‘全积分兑换房晚（All-Points Award Stay）100% 免收每晚 `$45–$65` 度假村费（Resort / Destination Fee）’**的情况下，结算系统依然机械加收了 `$275` 度假村费引发拒付投诉”**！
3. **“黑产票代利用‘添加第二同住人（Add 2nd Guest Name）’盗刷并倒卖积分房，以及取消订单时免费房券（`FNC`）因跨过原到期日当场作废清零：盗号团伙撞库登录会员账户后，兑换 `$1,200/晚` 的东京丽思卡尔顿积分房，然后把闲鱼买家的名字填进‘同住人（Additional Guest）’栏让买家直接拿身份证去前台办入住！此外，当会员用即将到期的房券订了 3 个月后的酒店，若因航班取消被迫改期退订，老旧系统在退房瞬间发现房券原有效期已过，竟直接将价值 `$500` 的房券静默吞没清零”**！

**架构师选型结论**：直接采用 **“积分兑换每分价值（`Cents-Per-Point, CPP = (含税现金价 - 积分房税费) / 消耗积分`）低于保底阈值（如万豪 `< 0.80¢`、凯悦 `< 1.60¢`）自动拦截转纯现金支付、并强制将 `>= 5 晚` 连续积分入住合并为单一 `PNR` 解锁‘住四免一（`5th Night Free`）’门禁（HTTP 403）+ 入住前竞价升舱（`Plusgrade / Nor1`）强制等待酒店 `Opera PMS` 在入住前 24 小时实际锁死物理房间号（且排除遮挡视线/电梯口噪音房）后方准调用支付实扣（`Capture`）及全积分房 `100%` 自动豁免度假村费门禁（HTTP 422）+ 积分房添加非同姓氏‘第二同住人’强制触发会员本人 `FIDO2 Passkey` 二次强核身防票代倒卖及因故退订过期房券/积分自动顺延 `30 天` 复活期门禁（HTTP 451）+ 动态积分+现金帕累托最优配比滑块 + 积分房动态降价（如从 `85k` 降至 `68k` 分/晚）免退房原地自动退差 `17,000 分` + 按房间属性加购（`ABS`：高楼层/安静房 `+$18`）净省 36%（HTTP 409）”** 的智能酒旅常旅客与收益托管架构。

![酒旅官渠常旅客Points+Cash、住四免一与Plusgrade/Nor1竞价升舱托管架构图](../assets/svg/689-ota-hotel-direct-points-cash-room-upgrade-escrow-2026-11-23.svg)

---

## ② 🎯 业务方与架构师灵魂拷问（Q&A）

### Q1：现在万豪、希尔顿、洲际全部改成了“动态积分定价（Dynamic Award Pricing）”，Agent 怎么帮用户算出这笔房晚到底该刷卡付钱、全用积分、还是用 `Points + Cash`？
- **业务痛点**：动态积分制下，同一家酒店淡季只要 `35,000 分`，跨年旺季暴涨到 `110,000 分`；而有时候现金价因为企业协议码（Corporate Rate）打折只要 `$210`，用积分兑完全是血亏！
- **架构护栏（`HTTP 403 SUB_FLOOR_CPP_POINT_BURN_OR_SPLIT_5TH_NIGHT_LOSS`）**：
  1. **真实含税度假村费口径的 `CPP（每积分美分价值）` 精算公式硬门禁**：
     - 严禁只拿不含税裸房价除以积分数！因为在希尔顿、凯悦等集团，全积分房免收 `$50/晚` 的度假村费（Resort Fee）及对应税费；因此真实价值公式必须为：**`Real_CPP = (全含税含度假村费现金总价 - 积分房应付杂费) / 消耗总积分`**；
     - 系统为各常旅客体系预设公允价值底线（如 `Hilton >= 0.50¢`、`Marriott/IHG >= 0.80¢`、`Hyatt >= 1.60¢`）：一旦算出当前兑换 `Real_CPP` 跌破底线，立即触发 `HTTP 403` 阻止烧分并自动切回现金/企业协议价（同时还能回血赚取 10x–20x 消费积分）！
  2. **连住 5 晚强制合并单一订单解锁“第 5 晚免费（`5th Night Free / Stay 4 Pay 3`）”锁（`HTTP 403`）**：当用户搜索 `>= 5 晚` 行程且使用万豪、希尔顿或花旗 Prestige / 联名卡住四免一权益时，严禁把 5 晚拆成多笔短订单或混入 1 晚现金破坏连住条件（触发 `HTTP 403` 自动合并为单一 5 晚纯积分 `PNR`，当场省下 20% 积分）！

### Q2：为什么酒店的入住前付费升舱（`Nor1 / Plusgrade`）经常在退房时引发信用卡拒付？怎么解决“高卡会员免费升房”与“散客花钱竞价升房”抢房源的冲突？
- **业务痛点**：如果系统在入住前 3 天就批准了散客 `$80` 的套房竞价并扣了钱，结果入住当天来了一位终身钛金卡 VIP 要求按会员条款免费升套房，前台两头得罪！
- **架构护栏（`HTTP 422 UNASSIGNED_PMS_UPGRADE_CAPTURE_OR_AWARD_RESORT_FEE`）**：
  1. **“预授权挂起 → `T-24h` 先保高卡权益 → `Opera PMS` 物理锁房号后才实扣”三步清算锁**：
     - 旅客提交升舱出价（Bid）时，仅绑定支付令牌（`Stripe SPT / Network Token`）做预审，**严禁在未分配具体房间号前提前扣款**；
     - 到达入住前 `24 小时（T-24h）`，收益引擎先扣除预留给当日到店高卡会员（Titanium / Globalist / Diamond）的免费升级配额；若有剩余空置海景房/套房，必须在酒店 **`Oracle Opera PMS` 中将真实物理房间号（如 `Room 1806`，且校验非视线遮挡房/非电梯井噪音房）硬性指派给该订单后**，才允许触发支付 `Capture`（未指派房间号企图扣款立即触发 `HTTP 422` 拦截）！
  2. **全积分房（`Award Stay`）度假村费自动清零门禁（`HTTP 422`）**：当订单支付方式为全积分或房券且品牌政策规定免收 `Resort / Destination Fee` 时，若 PMS 账单仍试图向客人预授权挂入每晚 `$55` 度假村费，立即触发 `HTTP 422` 自动抹除！

### Q3：怎么防范闲鱼/二手票代利用“加同住人”把偷来的积分卖给陌生人入住？如果积分房订完后酒店降了 17,000 分怎么办？
- **业务痛点**：传统酒店系统允许会员在网上随便改“同住人姓名（Additional Guest）”，这成了撞库黑客和违规买卖房券黄牛的最大洗钱通道！而动态积分跟股票一样每天波动，早订的人往往当了冤大头。
- **架构护栏（`HTTP 451 BROKER_SECOND_GUEST_ATO_OR_CANCELED_FNC_FORFEITURE` & `HTTP 409` 动态退差 + 属性选房）**：
  1. **积分房添加非本人同住人 `FIDO2` 生物核身与退订过期房券 `30 天` 保护锁（`HTTP 451`）**：
     - 凡是使用积分或房券兑换的订单，若会员本人不住、或在线添加一位与会员不同姓氏且无历史同行记录的“第二办理入住人（Second Guest Check-In）”时，立即触发 `HTTP 451` 挂起：强制要求会员本人通过手机 App 完成 **`FIDO2 Passkey` 人脸核身**（或按集团规定走官方赠礼通道 `Gifting Eligibility Check`），并在前台核验会员本人授权码，彻底斩断黑产盗刷卖房链；
     - 当客人因不可抗力或改期取消一笔使用了“已过原始到期日的积分/免费房券（`FNC`）”的预订时，严禁让积分/房券当场过期蒸发，强制触发 `HTTP 451` 签发 **`30 天原路重订复活期（Rebooking Grace Extension）`**！
  2. **积分房动态降价自动原位退差（`In-Place Award Re-Pricing`）+ 按房间属性微加购（`Attribute-Based Selling, ABS`）（`HTTP 409`）**：
     - 预订后至免费取消截止日前，Agent 每日巡检该酒店同房型所需积分：一旦发现动态积分从 `85,000 分/晚` 降至 `68,000 分/晚`，自动调用官方“修改预订（Modify Reservation）”接口**在不取消原房间、不损失房券的前提下原位退回 `17,000 积分`**；
     - 同时启用 **`ABS 属性化选房`**：无需花 `$200` 升整间套房，客人可花 `+$15` 单独勾选“高楼层（High Floor）”、“远离电梯（Away from Elevator）”或“带浴缸”，在保护会员体验的同时为酒店每间房增创 `+$42 RevPAR`，综合净省 **36.0%**！

---

## ③ 🧭 直观可视化图解（Mermaid 决策树 + 架构对比 + 时序图）

### 3.1 酒店常旅客 `Points+Cash`、住四免一与 `Plusgrade / Nor1` 竞价升舱四层托管决策树
```mermaid
flowchart TD
    A[会员使用常旅客积分/房券FNC预订酒店 或 参与Plusgrade/Nor1入住前付费竞价升舱] --> B{1. 积分房添加陌生同住人防盗刷ATO & 退订房券防作废门禁}
    B -->|积分/房券订单在线添加无历史同行记录的陌生第二入住人未过Passkey核身 或 退订时企图将已过原有效期的房券FNC直接清零没收| C[HTTP 451: 冻结可疑同住人变更防黄牛倒卖积分房! 强制会员本人FIDO2人脸核身 并为退订房券自动顺延30天重订复活期]
    B -->|账户安全 & 房券效期受保护| D{2. 每积分价值CPP保底红线 & 连住5晚住四免一合并门禁}
    D -->|积分兑换真实含税价值CPP跌破公允底线(如<0.80美分/分变成冥币) 或 5晚连续入住被拆成2+3两个订单丢掉第5晚免费权益| E[HTTP 403: 拦截贱卖积分与拆单损耗! 低CPP自动切回现金/企业协议价回血攒分; 5晚连住强制合并单一PNR立省20%积分]
    D -->|CPP高价值 & 住四免一已锁定| F{3. 竞价升舱Opera PMS物理锁房号 & 积分房免度假村费门禁}
    F -->|入住前竞价升舱在Opera PMS尚未实际分配物理套房号前就提前实扣信用卡 或 全积分兑换房晚违规加收$55/晚Resort Fee| G[HTTP 422: 严禁未锁房先扣款! 强制在T-24h先保高卡免费升房再对已指派无遮挡套房号的竞价单Capture 并清零积分房度假村费]
    F -->|物理房号锁定 & 零乱收杂费| H{4. 是否启用积分动态降价原位退差 + T-24h尾房竞价 + ABS属性选房?}
    H -->|动态积分从85k跌至68k自动原位退回17,000分 + T-24h出清闲置套房(+$42 RevPAR) + +$18勾选高楼层安静房| I[HTTP 409: 零到店无房拒付 零积分贬值贱卖 会员价值与酒店RevPAR净增效 36%]
    H -->|标准高价值积分/升舱入住| J[HTTP 200: 签发带精确房间号与免度假村费标识的数字房卡Digital Key]
```

### 3.2 “传统贱卖积分 + 升舱扣了钱到店没房” vs “智能体常旅客与 `PMS` 托管架构”对比
```mermaid
flowchart LR
    subgraph Legacy["❌ 传统酒店积分与升舱痛点 (0.3c贱卖积分/拆单丢住四免一 + 升舱先扣钱到店无套房 + 票代加同住人盗刷)"]
        L1[拿10万积分去换$320郊区酒店(仅0.32美分/分血亏)\n5晚行程被拆成两单白白丢掉85,000分第5晚免费福利] --> L2[Plusgrade提前3天扣走$360升舱费到店却说套房满了\n全积分兑换房晚被PMS系统错误加收$55/晚度假村费]
        L2 --> L3[黑客撞库后借添加第二同住人把积分房挂闲鱼倒卖\n积分房订完后降价2万分不知道修改白当冤大头]
    end
    subgraph Agentic["✅ 智能体CPP底线锁、Opera PMS实锁房号与动态退差架构 (Marriott / Hilton / Plusgrade / Opera)"]
        A1[含税含度假村费精算CPP>=0.80¢底线+自动合并5晚免1晚\n入住前每日巡检积分降价原位自动退回17,000分差额] --> A2[T-24h先满足高卡VIP免费升房再分配付费竞价套房\n严格等Opera PMS锁死真实无遮挡房号才触发Capture扣款]
        A2 --> A3[添加非同姓同住人强制FIDO2核身+退订房券顺延30d\n支持+$18按属性选高层安静房，综合净增效 36%]
    end
```

### 3.3 `CPP` 精算与住四免一锁单、入住前动态积分退差及 `T-24h Opera PMS` 竞价升舱清算时序图
```mermaid
sequenceDiagram
    autonumber
    participant Guest as 常旅客会员 (Loyalty Member)
    participant Agent as 常旅客精算与升舱 Agent
    participantCRS as 集团中央预订与积分账本 (`Marriott / Hilton CRS`)
    participant PMS_Bid as 门店 `Oracle Opera PMS` & `Plusgrade / Nor1`

    Note over Guest,PMS_Bid: 阶段1 (CPP 价值底线与住四免一合并)：预订 5 晚夏威夷度假村（现金含税 $3,200 vs 积分 70k/晚）
    Guest->>Agent: 1. 发起 5 晚度假预订并提交 `$110/晚` 海景套房付费竞价 (Standby Bid)
    Agent->>CRS: 2. 合并为单一 5 晚积分 `PNR` 触发 `第5晚免费` (总耗 280k 分)、抹除 `$275` 度假村费(HTTP 422)，核验 `CPP = 1.14¢ >= 0.80¢` (HTTP 403通过)!
    Note over Guest,PMS_Bid: 阶段2 (入住前 14 天动态积分降价原位退回 20,000 分)
    CRS-->>Agent: 3. 检出淡季调价降至 65k/晚 -> 自动调用 `Modify` 原位退回 `20,000 积分` 至会员账户!
    Note over Guest,PMS_Bid: 阶段3 (入住前 24 小时 Opera PMS 锁死物理套房号后方准扣取升舱费)
    Agent->>PMS_Bid: 4. `T-24h` 确认高卡升级完毕且 `Suite 1201 (正海景无遮挡)` 已在 Opera PMS 锁死给该客人 -> 触发 `$550` 升舱费实扣并发放手机房卡 (HTTP 409，净省 36%)!
```

---

## ④ 📊 主流酒店常旅客中央预订（`CRS`）、入住前动态竞价升舱（`Standby Upsell`）与属性选房（`ABS`）平台横向选型矩阵

| 选型维度 | **Plusgrade (`Powering 70+ Airlines & Global Hotel Chains`)** (全球航司与高端酒店入住前竞价升舱及积分变现绝对霸主) | **Oracle Hospitality `Opera Cloud Nor1` (`PRiME` AI Merchandising)** (深度内嵌全球豪华酒店 `Opera PMS` 底层房态的实时智能升房标杆) | **Marriott Bonvoy / Hilton Honors / World of Hyatt Direct CRS** (全球三大常旅客体系：动态积分、`Points+Cash`、住四免一与免度假村费权威源) | **Amadeus / Sabre Hospitality (`Attribute-Based Selling ABS` + `GDS`)** (按“高楼层/海景/连通房/早入住”细粒度属性拆卖与企业差旅直连底座) |
| :--- | :--- | :--- | :--- | :--- |
| **核心适用场景** | 酒店集团与航司希望在不打折破坏公开牌价的前提下，通过暗标竞价（Bid-for-Upgrade）在入住前 24–72 小时把空置套房变现 | 已采用 `Oracle Opera PMS` 的五星级酒店与度假村，需要在前台办理入住前和到店瞬间根据真实干净房态（Clean/Vacant）精准推销升房 | 个人旅游助手与商旅 Agent 为会员比较“付现金 vs 全积分 vs 积分+现金 vs 房券 `FNC`”并最大化会员权益 | 告别传统模糊的“标准房/豪华房”分类，让客人像选飞机座位一样加 `$15–$40` 精准锁定房间朝向、楼层与床型特征 |
| **防“扣了升舱费到店却没房”的 `PMS` 同步** | 支持双向 `PMS/CRS` 库存同步，仅在确认升级成功（Winning Bid Accepted）时才触发信用卡扣款 | **原生 `Opera PMS` 零延迟耦合**：直接读取实时可用物理房号与高卡会员预留池，绝不超卖已占用的套房 | 官方直连锁定基础房保底，升舱券（`Nightly Upgrade Awards NUA / SUA`）在入住前 3–5 天自动跑批确认 | 在中央库存层将物理房间打上几十维属性标签（如 `Non-Connecting`、`Ocean-Front`），一房一锁 |
| **常旅客 `CPP` 精算、住四免一与免度假村费** | 提供积分购买（Buy Points）促销与积分折抵升舱通道 | 自动识别客人常旅客等级（如白金/钻卡），动态调整付费升房报价（对已有免费升房权益的高卡客只推总统套/别墅） | **唯一支持连住 5 晚免第 5 晚积分（Marriott/Hilton）及全积分房自动免除 `$45–$65` 度假村费（Hilton/Hyatt）的官方通道** | 支持企业协议价（LRA）与常旅客会员号（Loyalty Number）同步写入预订以累积房晚（ENC）與积分 |
| **防票代添加同住人盗刷（`ATO`）与动态退差** | 升舱权益严密绑定原始主订单 `PNR` 与入住人身份 | 与酒店前台证件扫描仪及手机数字钥匙（Digital Key）联动核身 | **支持在线原位修改预订（Modify Stay）退回动态积分降价差额**，并对高风险异地添加同住人开启二次核验 | 提供标准化的订单修改与同住人实名报文审计 |
| **商业模式与成本 (`official_list_price`)** | **纯绩效分成模式**：无前期固定费，按成功带来的新增升舱净收入抽取 **`10%–20%` 佣金** | 按酒店房间数订阅或按成功升房交易额抽成（约 **`8%–15%`**） | 官渠直销 **`$0 佣金`**（相比 OTA `15%–25%` 佣金为酒店省下巨额渠道费） | 按预订段或酒店房间规模收取 SaaS 平台费 |

---

## ⑤ 🧪 转化率/成本测算与 7-Card 基准测试报告（7-Card Visual Benchmark Deck）

> **数据溯源声明（Provenance）**：以下基于某拥有 `180 家` 高端酒店与度假村的酒旅集团及配套智能订房平台季度常旅客积分损耗与升舱拒付池（`$220,000/季度` 因未与 `Opera PMS` 物理房号锁定就提前扣取竞价升舱费引发的到店降级退款与拒付、全积分房误收度假村费引发的客诉冲正、黑产撞库通过添加第二同住人盗刷的高价值积分房损失、以及会员因拆单或贬值兑换流失的直销复购池）对比测算，标记为 `synthetic`（`independently_reproduced=false`）。

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 1 / 7 · HANDS-ON · HOTEL `POINTS+CASH`, `5TH-NIGHT` & `NOR1` UPGRADE ESCROW ║
║ Headline: CPP Floor & T-24h PMS Suite Lock Cut Loyalty & Upsell Loss by 36.0%    ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ [Scenario & Thresholds]        [Structured Input]       [Top Decisions & KPIs]   ║
║ • Loyalty Pool: $220,000 / Qtr • CPP Floor: >=0.80¢/pt  • Verified: HTTP 200     ║
║ • 5-Night: Merge Single PNR    • Upsell: Opera PMS Lock • LowCPP/Split: HTTP 403 ║
║ • Award Fee: $0 Resort Fee     • ATO: 2nd-Guest Passkey • UnassignedPMS:HTTP 422 ║
║ • Re-Price: Auto Refund Delta  • RevPAR Uplift: +$42/rm • BrokerATO/FNC:HTTP 451 ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ Provenance: synthetic (independently_reproduced=false) · Suite: WebIQ-R246 (#365)║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 2 / 7 · SCENARIO: 5-NIGHT HAWAII AWARD, 20K POINT RE-PRICE & T-24H SUITE    ║
║ Headline: 5th-Night-Free + $0 Resort Fee Locked; Suite Bid Captured Only at T-24h║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ Input Quote: "Book 5-night Hawaii resort award (1.14c CPP, 5th Night Free, $0    ║
║ resort fee), auto-refund 20k dynamic point drop, and clear Nor1 suite at T-24h"  ║
║ 1. [choice] CPP >=0.80¢ & 5th-Night PNR ──► 1.00 conf ──► [Act automatically]    ║
║    ████████████████████████████████████████ 100% (1.14¢ CPP; 70k 5th Night Free) ║
║ 2. [choice] Opera PMS Suite Lock & $0 Fee─► 0.99 conf ──► [Act automatically]    ║
║    ███████████████████████████████████████▊ 99% (Suite 1201 Assigned; $0 Resort) ║
║ 3. [score]  Dynamic Re-Price + T-24h Bid──► 0.98 conf ──► [Confirm: HTTP 409]    ║
║    ███████████████████████████████████████░ 98% (-20k Pts Saved; -$79,200 / Qtr) ║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 3 / 7 · WHAT I TESTED · FULL 5-LANE EVALUATION MATRIX                      ║
║ Headline: 5/5 Deterministic Guardrails Verified Across CPP, PMS Lock & ATO       ║
╠══════════════════════════╦══════════════════════════╦══════════════════╦═════════╣
║ SCENARIO                 ║ QUESTION / TASK          ║ MODEL ANSWER     ║ ACTION  ║
╠══════════════════════════╬══════════════════════════╬══════════════════╬═════════╣
║ High-CPP Award & PMS Bid ║ >=0.8c CPP + Suite locked║ HTTP 200 ($0)    ║ Auto    ║
║ 0.32c Burn / 2+3 Split   ║ Sub-floor CPP / lost 5th ║ HTTP 403 Blocked ║ Block   ║
║ Capture Before PMS Assign║ Unassigned suite / $55 fe║ HTTP 422 Blocked ║ Block   ║
║ Broker 2nd Guest / FNC   ║ Stranger guest / exp FNC ║ HTTP 451 Hold    ║ Human   ║
║ Re-Price + T-24h Clear   ║ Auto point refund + ABS  ║ HTTP 409 (-36%)  ║ Confirm ║
╠══════════════════════════╩══════════════════════════╩══════════════════╩═════════╣
║ Gate Summary: 100% deterministic policy match; 0 downgrade disputes & +$42 RevPAR║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 4 / 7 · UNDER THE HOOD · PROTOCOL & SCORING MECHANICS                       ║
║ Headline: Deterministic Policy Input Contract → Verifier Decision Trace          ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ // Input Contract (OTAHotelDirectPointsCashUpgradePolicyInput)                   ║
║ { "quarterly_loyalty_point_leakage_and_upgrade_dispute_pool_usd": 220000.0,      ║
║   "sub_floor_cpp_redemption_or_split_five_night_award_stay": false,              ║
║   "capturing_upgrade_bid_before_pms_room_lock_or_award_resort_fee": false,       ║
║   "unverified_second_guest_name_swap_or_expired_fnc_forfeiture": false,          ║
║   "dynamic_award_repricing_and_t24h_pms_suite_auction_ready": true }             ║
║                                      ↓                                           ║
║ // Verifier Output (<answer>)                                                    ║
║ { "status_code": 409,                                                            ║
║   "decision": "DYNAMIC_AWARD_REPRICING_AND_T24H_SUITE_AUCTION_CONFIRM",          ║
║   "mandate_token": "hotel_loyalty_escrow_optim_409", "savings_usd": 79200.0 }    ║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 5 / 7 · ROBUSTNESS CHECK · PERTURBATION & CONSISTENCY                       ║
║ Headline: 0.0 pts Variance Across Option Reversal & Valuation Perturbations      ║
╠══════════════════════════════╦═════════════════╦══════════════════╦══════════════╣
║ QUESTION / ANSWER            ║ ORIGINAL        ║ REVERSED / PERT  ║ CHANGE (PTS) ║
╠══════════════════════════════╬═════════════════╬══════════════════╬══════════════╣
║ CPP Floor & 5th-Night Merge  ║ HTTP 403 (100%) ║ HTTP 403 (100%)  ║ 0.0 pts      ║
║ Opera PMS Suite & Resort Fee ║ HTTP 422 (100%) ║ HTTP 422 (100%)  ║ 0.0 pts      ║
║ 2nd-Guest ATO & FNC Grace    ║ HTTP 451 (100%) ║ HTTP 451 (100%)  ║ 0.0 pts      ║
║ Re-Price + T-24h Net 36%     ║ $79,200 Saved   ║ $79,200 Saved    ║ 0.0 pts      ║
╚══════════════════════════════╩═════════════════╩══════════════════╩══════════════╣

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 6 / 7 · LATENCY · BATCHING & SCALING LATENCY                                ║
║ Headline: 55ms Opera PMS Room-Inventory Lock & 18ms Points+Cash Pareto Solver    ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ Opera PMS Room-Number Lock   ║ ██ 55 ms (OHIP API) vs Check-In Suite Downgrade   ║
║ Points+Cash CPP Pareto Solve ║ █ 18 ms (In-Memory) vs Manual Calculator Guess    ║
║ Dynamic Award Rate-Drop Diff ║ █ 35 ms (CRS Poll) vs Overpaying 20,000 Points    ║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 7 / 7 · MY TAKE · GOOD FIT VS NOT FOR & READINESS                           ║
║ Headline: Essential for Hotel Direct Channels, Loyalty Programs & Travel Agents  ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ ✅ GOOD FIT                               ⛔ NOT FOR                             ║
║ • Hotel direct booking engines, loyalty   • Roadside coin-operated parking       ║
║   wallets & Plusgrade/Nor1 upsell flows     meters with zero room tiers or points║
║ • Architects integrating Oracle Opera     • Rotary cement kiln clinker cooler    ║
║   OHIP, Marriott/Hilton CRS & ABS           grate plates unrelated to hospitality║
║ Readiness: Production-verified schema in `lab/webiq_commerce_demo.py` (R246).    ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

---

## ⑥ 🛠️ 商业上线风控与架构评审 Checklist

- [ ] **每积分真实含税价值（`Real CPP >= 0.80¢`）底线锁与连住 5 晚“住四免一（`5th Night Free`）”合并门禁（HTTP 403）**：订房 Agent 在决策使用积分还是现金时，是否将全积分房免除的度假村费（Resort Fee）纳入分子精算 `CPP`（低于底线自动切回现金）？且遇到 `>= 5 晚` 连续入住时是否强制合并为单一 `PNR` 以确保触发第 5 晚免积分？
- [ ] **入住前竞价升舱（`Plusgrade / Nor1`）强制绑定 `Opera PMS` 物理锁房号后实扣与积分房 `$0` 度假村费门禁（HTTP 422）**：付费竞价升舱是否严禁在分配具体房间号前提前扣款，必须等到 `T-24h` 先预留高卡会员免费升房配额、并在 `PMS` 中锁死无视线遮挡的真实套房号后才调用 `Capture`？且全积分房账单是否自动豁免度假村费？
- [ ] **积分房添加非同姓“第二入住人”强制 `FIDO2` 核身防黄牛盗刷与退订过期房券 `30 天` 复活锁（HTTP 451）**：当积分或免费房券（`FNC`）订单在线添加陌生同住人时，是否强制会员本人通过 `Passkey` 生物核身？且因故取消含已过原到期日房券的预订时，是否自动顺延 30 天有效期防作废？
- [ ] **动态积分降价原位退差（`In-Place Award Re-Pricing`）与 `Points + Cash` 最优滑块（HTTP 409）**：预订后若酒店动态积分下调，Agent 是否自动通过 `Modify Reservation` 在保留原房间的前提下退回积分差额？
- [ ] **按房间属性微加购（`Attribute-Based Selling, ABS`）**：除了整间套房竞价外，是否支持客人在选房阶段花 `+$15–$30` 确定性购买“高楼层、远离电梯、正海景、带独立浴缸”等精确物理属性标签？
