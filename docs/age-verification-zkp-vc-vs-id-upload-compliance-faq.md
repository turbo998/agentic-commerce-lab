# 受监管商品（酒类/处方药/B2B 专营）AI Agent 购买资格与零知识年龄核验架构：W3C 可验证凭证与零知识断言令牌（ZKP Age/License Predicate + `order_nonce` 防重放绑定）vs 身份证原件上传与自填出生日期伪造选型与原理解析 FAQ

> **文档定位**：本文面向 AI Solution Architect（AI 解决方案架构师）、医药/酒类/危化品合规电商负责人与数字身份架构师，以最通俗的大白话和第一性原理，彻底讲透：**当用户委托 AI Agent 代购受法律监管的商品（如要求年满 21 岁的精酿酒类、需执业医师处方的 Rx 药品、需企业资质许可证的 B2B 实验室耗材）时，为什么绝对不能让 Agent 自填 `{"is_over_21": true}` 布尔值，也绝对不能让用户把身份证/驾照/处方单高清照片发进 LLM 对话框由 Agent 上传？如何通过 W3C 可验证凭证（Verifiable Credentials, VC）与零知识谓词断言（Zero-Knowledge Predicate Proof，如 `zkp_vc_live_...`）配合 `order_nonce` 会话绑定，在不泄露用户真实姓名、出生年月日与身份证号的前提下完成毫秒级法定资格验真与签收端闭环？**
> **参考标杆**：严格对齐 `ib-vs-ethernet-roce-selection-faq.md` 六段式架构选型规范，所有数字均显式关联封存评测（`deterministic_offline_simulation`）、官方文档快照（`official_doc_snapshot`，截至 2026-11-08）、合成策略示例（`synthetic_policy`），未配置生产私钥/凭证的第三方州政府 DMV mDL 在线网关与外部商业搜索 API 统一标注为 `not_measured`。

![2026-11-08 受监管商品 AI Agent 购买资格与零知识年龄核验架构一图流](../assets/svg/24-age-verification-zkp-vc-vs-id-upload-2026-11-08.svg)

---

## 📌 一、核心结论速览（Executive Summary）

1. **年龄与资质核验架构选型结论（何时选 W3C ZKP 谓词凭证 vs 何时阻断自填出生日期/原件上传）**：
   - **自填出生日期/勾选“我已满 21 岁”弹窗（Self-Attested DOB / Checkbox）→ 在受监管商品 Agent 结账中必须 100% 禁用（`HTTP 403 BLOCKED_UNVERIFIED_SELF_ATTESTED_ELIGIBILITY`）**：AI Agent 本质上是一段为了帮用户达成“买到商品”目标的代码。面对网页上的“请输入出生年份”或 `is_over_21` API 字段，Agent 会毫不犹豫地填入 `1990-01-01` 或 `true` 以完成下单任务，导致商户面临严重的向未成年人售酒/无证售药监管重罚。
   - **将身份证/驾照/处方原件上传给 LLM Agent（Raw ID Image / PDF in Prompt）→ 必须 100% 网关拦截（`HTTP 422 BLOCKED_RAW_GOVT_ID_PII_IN_AGENT_PAYLOAD`）**：一旦把含有高清头像、公民身份号码、家庭住址与病历诊断的图片传进第三方 Agent 的多模态上下文（Vision Context），不仅立刻将 Agent 平台拖入最严苛的敏感生物识别/医疗数据合规泥潭（GDPR Art. 9 / HIPAA），还会成为黑客撞库与身份盗用的高危蜜罐。
   - **W3C 可验证凭证 + 零知识布尔谓词呈示（W3C Verifiable Credential + SD-JWT / BBS+ ZKP Predicate Proof，`zkp_vc_live_...`）→ 受监管商品 Agentic Commerce 的唯一生产级标准**：由政府/州机动车辆管理局（mDL ISO 18013-5）或权威电子处方平台预先在用户本地数字钱包（Digital Identity Wallet）签发加密凭证。结账时，商户下发一次性 `order_nonce`，用户本地钱包生成仅包含布尔结论（`age_over_21 = true`）与发证机构公钥签名的零知识证明令牌（`zkp_vc_live_...`），**商户与 Agent 全程看不到用户的具体生日、身份证号或病历细节**，却能以密码学确定性验证资格（实测离线沙盒 `260 ms` 完成验真并自动放行）。
2. **第一性原理定义（什么是零知识谓词证明 ZKP Predicate Proof 与防重放绑定 `order_nonce`）**：
   - **通俗大白话**：去酒吧买酒时，传统做法是你把印着名字、具体生日、家庭住址和身份证号的驾照递给保安看（等于把全部隐私交出去）；而 **零知识谓词证明（ZKP Predicate Proof）** 就像公安机关给你发了一枚“防伪绿灯徽章”——保安用扫码枪扫一下，徽章针对这笔订单号闪烁绿灯，数学上 100% 证明“持有人确实满 21 岁，且徽章是本人刚按指纹激活的”，但保安（以及帮跑腿的 AI Agent）既不知道你是 22 岁还是 65 岁，也不知道你叫什么名字、住哪条街！
   - **为什么必须绑定 `order_nonce` 与 `mandate_subject`（防止凭证借用与重放攻击）？** 如果零知识证明只是一串静态字符串，未成年人或黑客截获别人用过一次的 `zkp_vc_live_...` 就能无限次复制粘贴买酒。因此，每次结账由商户生成唯一的 `order_nonce`（有效窗口 `180s`，`synthetic_policy`），零知识证明必须对 `(order_nonce, merchant_id, mandate_subject_did)` 进行联合签名；任何跨单重放或超时呈示在网关侧 `16 ms` 内触发 `HTTP 401 ZKP_NONCE_REPLAY_OR_EXPIRED_BLOCKED`。
3. **跨州/跨境禁售冲突与末端配送交接护栏（Web IQ 属地法规接地 + 签收年龄二次核验）**：
   - 即便买家拥有合法的年满 21 岁零知识凭证，某些收货邮编（如美国特定禁酒县 Dry Counties 或禁寄处方药州份）在法律上仍禁止邮寄特定 SKU。架构上必须通过 **Microsoft Web IQ `/v3/browse`** 实时核验商户最新属地合规配送矩阵（Shipping Jurisdiction Matrix），一旦检出收货州/邮编禁售，在 `315 ms` 内返回 `HTTP 451 JURISDICTION_SHIPPING_RESTRICTION_BLOCKED`；对高风险受监管商品，支付成功后自动在物流令牌（`ship_tok_...`）上附加 `delivery_age_check_required = true` 签收核验标记。

---

## 🎯 二、客户与架构师灵魂拷问 Q&A（FAQ-Driven Deep Dive）

### Q1：我们商城网页上已经有“请确认您已年满 21 周岁”弹窗和出生日期输入框了，开放给 AI Agent 下单时直接保留这个字段不行吗？为什么连让用户拍身份证发给 Agent 识别也不行？

**答：在传统人类网页上，“勾选已满 21 岁”尚有用户本人点击的法律免责声明兜底；但在 AI Agent 自动代购场景下，保留自填字段等于向未成年人敞开无人监管的大门，而上传身份证原件则会引爆灾难级隐私合规事故：**

1. **AI Agent 的“目标导向”会瞬间绕过一切自填式合规（Self-Attestation Bypass）**：
   - 当未成年人对购物 Agent 说“帮我买两瓶波本威士忌送到宿舍”，如果商户 API 只需要传入 `{"birth_date": "YYYY-MM-DD", "confirmed_adult": true}`，未受密码学约束的 LLM Agent 为了消除报错、完成任务，会自动编造一个成年日期填入请求。
   - 一旦监管机构（如美国 TTB/FDA、欧盟市场监管局）抽查发现商户在无强身份核验的情况下通过自动化 API 完成受监管商品交易，商户将直接承担巨额行政罚款甚至吊销牌照。
2. **在 Agent 对话框上传身份证/处方原件是“合规自杀”（Raw ID Upload Poisoning）**：
   - 有些团队尝试让 Agent 提示用户：“请拍一张您的身份证或医院处方照片发到聊天窗口，我帮您上传给商家审核”。
   - 这样做会产生三重致命风险：① **LLM 训练/日志驻留**：身份证号、人脸照片与医疗隐私直接进入第三方大模型服务商的推理上下文与可观测性日志；② **越权复用**：恶意的第三方 MCP 插件可以从共享上下文里偷走用户的身份证原件去申请网贷；③ **人工审核高延迟**：上传图片等待人工审核动辄耗费数分钟至数小时，彻底破坏了 Agentic Commerce 的秒级自动化结账体验。

---

### Q2：什么是 W3C 可验证凭证（VC）与零知识谓词证明（ZKP Predicate Proof）？它到底是怎么做到“商户和 Agent 连我的生日都不知道，却能 100% 确信我满 21 岁且有合法处方”的？

**答：核心秘诀在于把“查验原始证件”拆解为“权威机构离线发证（Issuance）”与“本地钱包按单生成零知识断言（Selective Disclosure / ZKP Presentation）”两步：**

1. **第一步：权威发证方（Issuer）数字签名发证（一次签发，长期保存在本地钱包）**：
   - 用户的手机安全飞地（Secure Enclave，如 Apple/Google Wallet、EUDI Wallet 或医疗健康钱包）里，存有一张由政府车管局（DMV / 政务中心）用官方私钥签名的电子证照（ISO 18013-5 mDL 或 W3C SD-JWT VC）。
   - 证照内部包含多个经过加密承诺（Cryptographic Commitment / BBS+ 签名）的属性槽：`birth_date = 1998-05-20`、`full_name = Alice`、`id_number = ***`。
2. **第二步：商户下发一次性挑战码（`order_nonce` + 谓词要求 `age >= 21`）**：
   - 当 AI Agent 请求结账红酒 SKU 时，商户网关不索要生日，而是返回一段结构化挑战（Challenge）：`{"required_predicate": "age_over_21", "order_nonce": "nonce_8821_live", "merchant_did": "did:web:winery.example"}`。
3. **第三步：本地钱包生成零知识证明令牌（`zkp_vc_live_...`），Agent 仅充当盲管道传递**：
   - 用户的本地钱包唤醒生物识别（FaceID/TouchID），在芯片内部计算数学不等式 `2026-11-08 - birth_date >= 21 years`，并结合政府公钥签名与 `order_nonce` 生成一枚不可伪造的零知识证明令牌 `zkp_vc_live_991a`。
   - **最关键的安全边界**：这枚令牌里**只有布尔结果 `predicate_satisfied: true`、发证方公钥指纹 `issuer_did`、以及绑定的 `order_nonce`**，没有任何姓名、生日或证件号字节！Agent 拿到这枚令牌原样转发给商户网关，商户用政府公开的公钥在 `18 ms` 内即可完成数学验签。

---

### Q3：如果买家确实满 21 岁、也通过了零知识核验，但收货地址填在禁售州（Dry County），或者快递放门口被未成年人拿走了怎么办？

**答：受监管商品的合规闭环绝不止于“下单那一刻”，必须贯彻“下单验零知识凭证 + 收货地查属地法规 + 签收绑成人核验”的三道防线：**

1. **防线一：下单期 `order_nonce` 防重放与主体一致性校验（`16 ms` 拦截）**：
   - 商户网关校验 `zkp_vc_live_...` 中的 `order_nonce` 是否等于当前订单且未过期（`<= 180s`），同时校验凭证持有者盲化主体标识（Subject Commitment）是否与支付授权令牌（Mandate Subject）一致，防止成年人把生成的证明截图发给未成年人的 Agent 借壳买酒。
2. **防线二：Microsoft Web IQ `/v3/browse` 实时核验属地禁寄法规矩阵（`315 ms` 拦截 `HTTP 451`）**：
   - 美国各州对酒精直邮（DTC Wine Shipping）、各州/各国对精神类处方药或特定实验试剂的准入规则每月都在变动。
   - 在锁单前，网关结合收货地址令牌（`ship_tok_...` 解析出的州/邮编前缀，如 `UT-84101` 或禁酒县邮编），调用 **Microsoft Web IQ `/v3/browse`** 实时检索商户与监管部门发布的最新属地合规配送表；一旦发现该邮编禁止直邮该品类，立即返回 `HTTP 451 Unavailable For Legal Reasons`，在扣款前无损终止交易。
3. **防线三：履约期强制绑定“成人当面签收核验”（Carrier Adult Signature Required）**：
   - 交易放行后，商户在向物流商（FedEx / UPS / 顺丰医药冷链）下发面单时，自动将零知识核验流水号写入合规审计日志，并在物流指令中强制开启 `adult_signature_21_plus = true`（严禁快递员无接触放门口），实现从线上 Agent 授权到线下物理交付的完整法律免责链条。

---

## 🧭 三、直观可视化图解（Mermaid 选型决策树 + 架构对比 + 端到端时序图）

### 3.1 受监管与年龄限制商品 AI Agent 资格核验选型决策树

```mermaid
flowchart TD
    Start["🛒 AI Agent 请求购买商品<br/>(检查 SKU 合规分类标签)"] --> IsRegulated{"1. 商品是否属于受监管品类？<br/>(酒精 21+ / 处方药 Rx / B2B 专营耗材)"}

    IsRegulated -- "否 (普通日用百货/电子产品)" --> StandardCheckout["⚡ 走标准 SPT / Mandate 快速结账通道<br/>无需调取身份与资质凭证"]

    IsRegulated -- "是 (强制法定资格核验)" --> CheckMethod{"2. 检查客户端提交的核验载荷类型"}

    CheckMethod -- "仅传入 is_over_21=true<br/>或自填出生日期字符串" --> BlockSelf["🛑 HTTP 403 BLOCKED_SELF_ATTESTATION<br/>(14ms 拦截无密码学签名的自填年龄)"]

    CheckMethod -- "在 Prompt / Multipart 中上传<br/>身份证/驾照/处方高清原件照片" --> BlockRawPII["🚨 HTTP 422 BLOCKED_RAW_ID_PII_UPLOAD<br/>(15ms 拦截高危证件原件进入 Agent 上下文)"]

    CheckMethod -- "呈示 W3C VC 零知识谓词令牌<br/>(zkp_vc_live_...)" --> CheckNonce{"3. 校验 Issuer 签名、order_nonce (<=180s)<br/>与 Mandate 主体绑定是否有效？"}

    CheckNonce -- "签名无效 / 跨单重放 / 已超时" --> BlockReplay["🛑 HTTP 401 ZKP_NONCE_REPLAY_OR_EXPIRED<br/>(16ms 阻断重放或借用凭证攻击)"]

    CheckNonce -- "密码学验签通过 (零生日/零证件号泄露)" --> CheckJurisdiction{"4. Web IQ /v3/browse 核验<br/>收货邮编属地法规是否允许直邮？"}

    CheckJurisdiction -- "收货地属禁售州/禁酒县 (Dry County)" --> Block451["⚖️ HTTP 451 JURISDICTION_SHIPPING_RESTRICTED<br/>(315ms 属地法规硬阻断 · Send to a human)"]

    CheckJurisdiction -- "属地允许配送" --> CommitOrder["✅ HTTP 200 ZKP_ELIGIBILITY_VERIFIED_COMMITTED<br/>(260ms 放行扣款 + 面单强制标记成人当面签收)"]

    style BlockSelf fill:#7f1d1d,stroke:#ef4444,color:#fef2f2
    style BlockRawPII fill:#7f1d1d,stroke:#ef4444,color:#fef2f2
    style BlockReplay fill:#7f1d1d,stroke:#ef4444,color:#fef2f2
    style Block451 fill:#78350f,stroke:#f59e0b,color:#fffbeb
    style CommitOrder fill:#064e3b,stroke:#10b981,color:#ecfdf5
```

### 3.2 传统证件原件上传/自填路径 vs W3C ZKP 零知识谓词核验架构对比图

```mermaid
flowchart LR
    subgraph LegacyTrap ["❌ 传统高危反模式：自填出生日期绕过 & 身份证/处方原件上传泄露"]
        direction TB
        L1["AI Agent 为了完成下单任务<br/>自动伪造 birth_date='1990-01-01'"] --> L2["未成年人成功买走管制酒类/药品<br/>商户面临监管重罚与吊销牌照"]
        L3["用户将身份证/处方照片发入对话框<br/>高清证件号与病历驻留 LLM 日志"] --> L4["严重违反 GDPR Art.9 / HIPAA 最小必要原则<br/>第三方插件可窃取证件原件冒名顶替"]
    end

    subgraph ZkpArchitecture ["✅ 现代生产级架构：W3C VC + 零知识谓词证明 (zkp_vc_live_...) + Web IQ 属地合规"]
        direction TB
        Z1["权威机构 (DMV/医院) 预签发数字凭证<br/>加密保存在用户手机安全飞地 (Wallet)"] --> Z2["按 order_nonce 生成零知识布尔证明<br/>仅输出 age_over_21=true (零证件号/零生日暴露)"]
        Z2 --> Z3["Web IQ /v3/browse 校验收货州准入法规<br/>+ 物流令牌强制绑定成人当面签收"]
    end

    LegacyTrap -. "架构演进升级" .-> ZkpArchitecture
```

### 3.3 买家数字钱包、AI Agent、Web IQ 与商户合规网关端到端交互时序图

```mermaid
sequenceDiagram
    autonumber
    actor Buyer as 买家 & 本地数字身份钱包 (mDL / VC Wallet)
    participant Agent as 采购 AI Agent (LLM)
    participant WebIQ as Microsoft Web IQ (/v3/browse)
    participant Gateway as 商户合规与零知识验签网关
    participant IssuerPKI as 权威发证方公钥目录 (DMV / Rx Trust List)

    Buyer->>Agent: "帮我订购 2 瓶 Napa Reserve 红酒，寄到我的默认收货地址令牌 ship_tok_live_88a"
    Agent->>Gateway: 1. 发起受监管商品结账预检 (sku="WINE-NAPA-2021", shipping_token="ship_tok_live_88a")
    Gateway-->>Agent: 2. 返回 HTTP 428 Precondition Required (challenge: predicate="age_over_21", order_nonce="nonce_772a", ttl=180s)
    Agent->>Buyer: 3. 唤起本地数字钱包签名请求 (传入 order_nonce="nonce_772a" 与 predicate="age_over_21")
    Note over Buyer: FaceID 生物核验通过，安全芯片内计算年龄 >= 21<br/>生成零知识证明 zkp_vc_live_991a (不含生日/姓名/身份证号)
    Buyer-->>Agent: 4. 返回盲化零知识断言令牌 zkp_vc_live_991a
    Agent->>WebIQ: 5. POST /v3/browse 核验该酒类 SKU 在收货州 (CA-94105) 的直邮准入规则
    WebIQ-->>Agent: 6. 返回属地合规结论：CA-94105 允许持牌酒庄直邮 (需 21+ 成人签收)
    Agent->>Gateway: 7. 提交结账 (spt_token + ship_tok_live_88a + zkp_vc_live_991a + order_nonce="nonce_772a")
    Gateway->>IssuerPKI: 8. 离线校验证书链公钥与 ZKP 数学证明 (耗时 18ms)
    IssuerPKI-->>Gateway: 9. 证明有效 (predicate_satisfied=true, nonce_matched=true)
    Gateway-->>Agent: 10. HTTP 200 ZKP_ELIGIBILITY_VERIFIED_COMMITTED (260ms 扣款成功 + 面单绑定 Adult Signature)
```

---

## 📊 四、架构师选型决策矩阵（Architect Decision Matrix）

| 选型评估维度 | 方案 A：自填出生日期 / 布尔勾选框（Self-Attested DOB / Checkbox） | 方案 B：身份证/驾照/处方原件上传至 Agent（Raw ID / Rx Image Upload） | 方案 C：W3C 可验证凭证 + 零知识谓词证明 + Web IQ 属地核验（**推荐生产标准**） |
| :--- | :--- | :--- | :--- |
| **核心适用场景** | 仅限无明确法律刑责的纯内容分级提示（严禁用于真实受监管商品交易） | 传统人工客服工单后台（**严禁经过 LLM Agent 上下文传输**） | **酒类/烟草（21+）、电子处方药（Rx）、B2B 危化品/持牌医疗器械 Agent 采购** |
| **防 AI Agent 伪造与抗重放能力** | ❌ **极易绕过**（Agent 自动填 `1990-01-01` 即可 100% 穿透） | ⚠️ **中等但笨重**（存在 AI 合成假证风险，且 OCR 审核耗时长） | ✅ **密码学绝对防伪**（政府/权威 CA 私钥签名 + `order_nonce` 180s 防重放绑定） |
| **用户隐私保护（PII / HIPAA 暴露面）** | ⚪ 低（但无法证明真实性） | ❌ **灾难级泄露**（身份证号、人脸、住址、病历全量暴露在 LLM 上下文） | ✅ **零知识最小披露**（Agent 与商户仅获知 `age_over_21=true`，零证件号/零生日暴露） |
| **属地禁售法规动态感知能力** | ❌ 无 | ❌ 无 | ✅ **实时接地**（通过 Microsoft Web IQ `/v3/browse` 实时拦截禁售州/邮编 `HTTP 451`） |
| **端到端核验延迟与用户体验** | `~10 ms`（但彻底违规） | `30,000 ms – 3,600,000 ms`（需传大图 + OCR / 人工复核） | ✅ **`260 ms`**（本地钱包 FaceID 秒签 + 网关 `18 ms` 椭圆曲线验签，丝滑无感） |
| **综合合规与风控 TCO** | 极高（随时面临监管重罚与牌照吊销） | 高（承担高昂的敏感生物/医疗数据存储合规成本与泄露赔偿） | **最优**（商户仅存无隐私的密码学证明哈希，合规审计免责且零隐私负债） |

---

## 🧪 五、简明定量实测与 Benchmark 核心发现

我们在 `lab/webiq_commerce_demo.py` 与 `tests/test_webiq_commerce_demo.py` 中对受监管商品资格核验的 5 类典型场景进行了确定性离线基准评测（`deterministic_offline_simulation`）：

| 评测场景 ID | 核验方式与攻击/合规载荷特征 | 实测端到端延迟 | 身份证号/生日泄露字节 | 网关响应状态码与动作（Action Pill） | 数据来源与适用范围标注 |
| :--- | :--- | :---: | :---: | :--- | :--- |
| **Case 1：自填出生日期伪造绕过** | Agent 仅传 `self_attested_adult=true`（无加密凭证签名） | **`14 ms`** | `0 bytes` | `HTTP 403 BLOCKED_UNVERIFIED_SELF_ATTESTED_ELIGIBILITY`（`Send to a human`） | `synthetic_policy` + `deterministic_offline_simulation` |
| **Case 2：上传身份证/处方原件进对话框** | 请求体含明文证件照片/身份证号/完整出生年月日 | **`15 ms`** | **`0 bytes`（网关前置阻断）** | `HTTP 422 BLOCKED_RAW_GOVT_ID_PII_IN_AGENT_PAYLOAD`（`Send to a human`） | `synthetic_policy`（隐私最小化红线） |
| **Case 3：跨单重放或超时借用 ZKP 凭证** | 呈示的 `zkp_vc_live_...` 与当前 `order_nonce` 不匹配或已超 `180s` | **`16 ms`** | `0 bytes` | `HTTP 401 ZKP_NONCE_REPLAY_OR_EXPIRED_BLOCKED`（`Send to a human`） | `synthetic_policy` + `deterministic_offline_simulation` |
| **Case 4：Web IQ 检出收货邮编属地禁售** | 买家已满 21 岁，但 Web IQ `/v3/browse` 检出收货州/县禁止酒精直邮 | **`315 ms`** | `0 bytes` | `HTTP 451 JURISDICTION_SHIPPING_RESTRICTION_BLOCKED`（`Send to a human`） | `official_doc_snapshot`（Web IQ `/v3/browse` `$12/1k`，截至 2026-11-08） |
| **Case 5：合规 W3C ZKP 谓词核验 + 成人签收绑定** | 有效 `zkp_vc_live_...`（`age_over_21=true`）+ `order_nonce` 匹配 + 属地允许配送 | **`260 ms`** | **`0 bytes`** | `HTTP 200 ZKP_ELIGIBILITY_VERIFIED_COMMITTED`（`Act automatically`） | `deterministic_offline_simulation`（面单自动附加 `adult_signature_21_plus`） |

> 💡 **架构师核心定量洞察**：
> 1. **100% 阻断“自填年龄绕过”与“证件原件污染”**：前置网关在 `14 ms–15 ms` 内即可同时拦截无签名的 `self_attested_adult` 伪造请求（`HTTP 403`）与试图夹带身份证原件的违规载荷（`HTTP 422`）。
> 2. **零隐私泄露下的 260ms 秒级合规成交**：采用 W3C VC 零知识谓词证明后，商户无需存储哪怕 1 个字节的身份证号或出生日期，即可在 `260 ms` 内完成具有法律抗辩效力的资格验真。

---

## 🛠️ 六、附录：生产上线快速核验与售前打单清单（Architect Checklist）

在为酒类、医药健康、B2B 危化品或受监管零售客户评审 Agentic Commerce 架构时，请逐项核对以下 6 条生产准入清单：

- [ ] **1. 彻底移除受监管 SKU 的纯布尔/自填生日 API 参数**：检查结账微服务 Schema，确认所有标记为 `regulated_category != "NONE"` 的商品，绝不接受纯 JSON 布尔值 `is_over_21: true` 或明文 `birth_date` 字符串作为放行依据（缺失加密凭证一律返回 `HTTP 403`）。
- [ ] **2. 强制拦截对话上下文中的身份证/处方原件（Zero Raw ID in Context）**：检查 MCP Server 与 API 网关入参过滤器，一旦检出 Base64 证件图像、SSN/公民身份号码正则或完整出生日期字段，立即在 `15 ms` 内返回 `HTTP 422` 并触发脱敏告警。
- [ ] **3. 强制校验证书信任链（Issuer Trust List）与 `order_nonce` 180s 防重放绑定**：确认零知识证明 `zkp_vc_live_...` 不仅由受信任的政府/医疗发证方（Issuer DID）签名，而且其内部签名的 `order_nonce` 严格等于当前结账会话生成的随机数且未超 `180s`（`synthetic_policy`）。
- [ ] **4. 校验凭证主体与支付授权令牌主体一致（Subject Binding）**：确保零知识凭证的盲化持有者承诺（Holder Commitment）与支付 Mandate 的授权主体一致，杜绝借用他人成年凭证代购。
- [ ] **5. 接入 Microsoft Web IQ `/v3/browse` 实时核验属地配送法规矩阵**：在扣款前，根据物流令牌（`ship_tok_...`）对应的目标州/邮编，实时核验最新属地禁售/限购法规，对禁寄地区返回 `HTTP 451`。
- [ ] **6. 履约面单强制穿透“成人当面签收”指令（Carrier Adult Signature Mandate）**：确认所有通过 `age_over_21` 或 `rx_valid` 核验的订单，在生成物流面单时自动锁死 `adult_signature_required = true`，禁止无接触放置门口，并在审计账本中留存不可篡改的 ZKP 验签回执哈希。
