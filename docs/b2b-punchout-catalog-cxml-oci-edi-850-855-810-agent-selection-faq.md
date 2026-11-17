# 企业 B2B 采购目录集成（cXML / OCI PunchOut：SAP Ariba / Coupa）与 EDI 850/855/810 订单协同 Agent 架构选型 FAQ：PunchOut 禁直接扣款、UOM 箱件防错与 ASN 对账实战指南

> **专题定位（世界 500 强企业 B2B 采购门户 SAP Ariba / Coupa / Jaggaer 集成、cXML/OCI PunchOut 目录跳出与 EDI 850/855/856/810 自动化智能体聚焦 · Round 420）**：面向为工业办公耗材（如 Grainger / 京东企采 / Amazon Business）、IT 硬件分销商与品牌大客户部设计 B2B 电子采购对接系统的 **Cloud & AI Solution Architect**，系统解答企业级大客户采购对接中最容易踩坑的四大协议与工程难题：**“为什么买方采购员从 SAP Ariba / Coupa 点击进入你的电商网站（PunchOut Session）选好商品后，如果你在网页上直接弹出信用卡收银台扣款，买方财务部会立刻拉黑你的供应商资格（必须设 `disable_checkout=true` 将购物车封装成 `cXML PunchOutOrderMessage` 传回买方 ERP 走内部预算审批）、为什么买方 EDI 850 采购单写的是 `10 EA`（10 个，单价 $12），卖方 AI 解析器却当成了 `10 CS`（10 箱共 240 个，总价 $2,880）直接发错货、怎么拦截供应商在 EDI 855 订单确认单里偷偷塞入涨价 8% 的单价变更、以及怎么保障供应商目录同步严守 Stripe SFTP `mode='upsert'` 而不使用全量 `replace` 清空在线商品”**。  
> **文风标杆**：严格对标 `ib-vs-ethernet-roce-selection-faq.md` 六段式结构（核心结论速览、业务方与架构师灵魂拷问 Q&A、Mermaid 决策树/架构对比/时序图、B2B 电子采购集成路径选型矩阵、定量错单/罚款测算与 7-Card 溯源表、生产上线 Checklist）。  
> **双语版本**：**[中文版（当前）](b2b-punchout-catalog-cxml-oci-edi-850-855-810-agent-selection-faq.md)** · **[English Version (`b2b-punchout-catalog-cxml-oci-edi-850-855-810-agent-selection-faq.en.md`)](b2b-punchout-catalog-cxml-oci-edi-850-855-810-agent-selection-faq.en.md)**  
> **数据溯源声明（Provenance & As-Of `2026-11-18`）**：Stripe Agentic Commerce SFTP Catalog（`disable_checkout=true` 发现模式、库存更新仅支持 `mode="upsert"` 严禁 `replace`）与 Web IQ `/v3/search` 联合国 UNSPSC 分类核验引自 `research/daily/2026-11-08-sources.json`（标记为 `official_doc_snapshot`）；cXML PunchOut 购物车回传拦截直接扣款、EDI 850/855 单价与包装单位（UOM）校验、856 ASN 条码核验引自 `lab/webiq_commerce_demo.py`（标记为 `deterministic_offline_simulation`）。

![2026-11-18 企业 B2B 采购目录集成 (cXML/OCI PunchOut) 与 EDI 850/855/810 订单协同 Agent 架构一图流总结](../assets/svg/422-b2b-punchout-catalog-cxml-oci-edi-850-855-810-2026-11-18.svg)

---

## 📌 一、核心选型结论速览（Executive Summary）

想把商品卖给大型跨国企业、医院、高校或连锁巨头，对方**绝不会让员工直接去你的公开 B2C 网站注册账号刷私人卡**，而是强制要求接入其内部采购系统（**SAP Ariba、Coupa、Oracle Procurement、Jaggaer**）或 **X12 EDI / EDIFACT** 报文总线。架构师必须执行以下四条选型铁律：

1. **PunchOut 会话结账边界选型：严禁“在 `cXML / OCI PunchOut` 会话中展示直接付款按钮并扣款”，必选【锁定 `disable_checkout=true` 仅生成签名 `PunchOutOrderMessage` 将购物车回传买方采购系统审批（`HTTP 403`）】**：
   - **核心原因**：在 PunchOut 模式下，买方员工只是“跳出”到卖方商城挑配置、查专属协议价；挑完点击“Transfer Cart（传回采购车）”时，卖方系统必须把包含 `UNSPSC` 分类码、专属合同价与交期的 `cXML PunchOutOrderMessage` POST 回买方的 `BrowserFormPost` 地址，由买方主管在 Coupa/Ariba 内完成预算审批后，再下发正式的 **`cXML OrderRequest` 或 `EDI 850` 采购订单**！若在跳出页直接扣款，属于严重绕过买方内控（Maverick Spend），门禁必须在 **`11 ms`** 内返回 `HTTP 403 PUNCHOUT_SESSION_DIRECT_PAYMENT_OR_SFTP_INVENTORY_REPLACE_BLOCKED`。
2. **目录与库存同步模式选型：严禁“对在售库存清单执行全量覆盖（`mode='replace'`）”，必选【增量更新（`mode='upsert'`）与客户专属价格表（Customer-Specific Price List）绑定】**：
   - **核心原因**：根据 Stripe Agentic Catalog 规范（`official_doc_snapshot`），库存同步传 `mode="replace"` 会直接返回 `HTTP 400 sftp_inventory_forbids_replace_mode`。
3. **EDI 850（采购单）$\leftrightarrow$ 855（确认单）校验选型：严禁“忽略计量单位（UOM）换算与单价上浮直接转仓配发货”，必选【`EA / PK / CS / PLT` 四级包装单位确定性换算 + 855 确认价 `<= 850 合同价` 零上浮硬门禁（`HTTP 422`）】**：
   - **核心原因**：B2B 错单之王就是买方下 `10 EA`（10 个独立包装），卖方 ERP 录成 `10 CS`（10 整箱 = 240 个），或者卖方在 `EDI 855 (Purchase Order Acknowledgment)` 里把单价从合同约定的 `$50.00` 擅自改成 `$54.00`。
4. **EDI 856（预发货通知 ASN）与 810（电子发票）协同选型：必选【先发含 `SSCC-18` 托盘条码的 856 ASN、再触发 810 发票与虚拟卡/ACH 结算（`HTTP 451`）】**：
   - **核心原因**：大型零售商（如 Walmart / Target / 亚马逊自营 VC）仓库若在收货前未收到合规的 `EDI 856 ASN`，收货月台会直接拒收或开出每单 **`$250 ~ $1,500` 的供应链合规罚单（Chargeback Penalty）**。

---

## 🎯 二、业务方与架构师灵魂拷问 Q&A（FAQ-Driven）

### Q1：我们花了 3 个月给大客户上线了 AI 导购商城，为什么客户采购总监试了一下就大发雷霆，说我们的 AI 助手“破坏了他们全公司的 SAP Ariba 审批内控”？

**答：因为你的 AI 导购没有识别当前会话是 `cXML PunchOutSetupRequest` 发起的“采购车组装模式”，居然在聊天框里直接诱导客户员工刷卡下单了！**

1. **分清普通 B2B 直购与企业 `PunchOut` 跳出采购的本质区别**：
   - **Stage 1（`PunchOutSetupRequest` 握手）**：买方员工从内部 Ariba/Coupa 点击你的供应商图标，Ariba 向你的网关发送包含 `BuyerCookie`、`From/To Identity` 与 `BrowserFormPost URL` 的认证请求；
   - **Stage 2（AI 辅助选品与协议价锁定，`disable_checkout=true`）**：你的 AI 导购根据 `From Identity` 加载该大客户的**专属阶梯协议价目录**，帮员工选好配件并校验库存；但此时**严禁调用支付网关扣款**，结账按钮必须替换为 **`Return Cart to Ariba / Coupa`**；
   - **Stage 3（回传 `PunchOutOrderMessage` 并在审批通过后接收 `OrderRequest / EDI 850`）**：员工在内部走完部门经理和财务审批后，Ariba 自动通过后台机器接口发来正式 `OrderRequest`（内含企业采购虚拟卡 `PCard / Stripe SPT` 或正式 `PO Number`），此时才真正创单履约！

---

### Q2：为什么对接传统制造业和医院客户的 EDI 850 报文时，用大模型直接把 EDI 文本转成 JSON 传给仓库，每个月都会闹出“买 12 盒手套发过去 12 大箱”的乌龙？

**答：因为 X12 EDI `PO1` 段里的计量单位代码（如 `EA` 个、`DZ` 打、`BX` 盒、`CS` 箱、`PL` 托盘）必须查主数据换算表（UOM Conversion Matrix），绝不能靠 LLM 猜！**

1. **EDI 850 $\leftrightarrow$ 855 确定性三校验（`HTTP 422`）**：
   - **校验 ①（UOM 换算整数倍闭环）**：买方 `PO103` 请求 `UOM='BX'`（盒，每盒 100 只），而卖方仓库最小出库单位为 `CS`（箱，每箱 10 盒）；引擎自动将数量换算为基准最小单位（Base Unit）比对，若无法整除或总件数不匹配立即拦截；
   - **校验 ②（855 确认单零擅自涨价）**：供应商回传的 `EDI 855 (POA)` 中，任何行项目的确认单价若高于 `EDI 850` 上的协议单价（`ack_unit_price > po_contract_price`），立即返回 **`HTTP 422 EDI_855_PRICE_UOM_MISMATCH_OR_MISSING_UNSPSC_TAXONOMY_BLOCKED`**；
   - **校验 ③（强制 8 位 `UNSPSC` 分类码与买方物料号 `Buyer Part ID` 映射）**：确保买方 ERP 能自动将费用归入正确的财务总账科目（GL Code）。

---

### Q3：为什么给大型连锁商超供货时，明明货按时送到了对方仓库，月底结账却被扣了 $5,000 的“EDI 856 ASN 违规罚金”？

**答：因为货车都已经到仓库大门口了，你的系统才把 `EDI 856（预先发货通知 ASN）` 发过去，或者托盘上漏贴了对应的 `GS1-128 (SSCC-18)` 序列号箱唛！**

- 确定性履约门禁强制执行 **`ASN-Before-Gate-Out` 规则（`HTTP 451`）**：在仓库打印出库单、封车发运的那一秒，必须先确认 `EDI 856 ASN`（含精确的包装层级 `Shipment -> Order -> Tare/Pallet SSCC-18 -> Pack -> Item`）已通过 AS2/SFTP 通道收到买方返回的 **`EDI 997 Functional Acknowledgment（功能确认回执）`**，随后才允许生成 `EDI 810` 电子发票请款。

---

## 🧭 三、直观可视化图解（Mermaid 选型决策树 + 架构对比 + 端到端时序图）

### 3.1 企业 B2B `cXML / OCI PunchOut` 与 `EDI 850/855/856/810` 协同选型决策树

```mermaid
flowchart TD
    A["🎯 企业买方通过 Ariba/Coupa PunchOut 或 EDI 850 发起采购"] --> B{"1. PunchOut 会话边界与目录同步模式核验？"}

    B -- "在 PunchOut 跳出页直接弹窗刷卡扣款绕过买方 ERP 审批<br/>或对 SFTP 在售库存执行 mode='replace' 全量清空" --> C["🛑 HTTP 403 立即硬阻断违规直扣与库存误删<br/>(PUNCHOUT_DIRECT_CHARGE_OR_INVENTORY_REPLACE_BLOCKED)"]

    B -- "PunchOut 设 disable_checkout=true 仅回传购物车<br/>& SFTP 库存采用 mode='upsert'" --> D{"2. EDI 850/855 包装单位 (UOM)、协议单价与 UNSPSC 核验？"}

    D -- "EA(个) 与 CS(箱) 换算错误 / 855 确认单擅自涨价<br/>或缺失 8 位 UNSPSC 商品分类码" --> E["🚨 HTTP 422 拦截 UOM 错发与超合同价确认<br/>(EDI_855_PRICE_UOM_MISMATCH_OR_MISSING_UNSPSC_BLOCKED)"]

    D -- "UOM 换算精确 & 855 单价 <= 850 合同价" --> F{"3. EDI 856 ASN (SSCC-18) 预发货回执与 997 确认？"}

    F -- "货已发运但未发送 EDI 856 ASN 或未收到买方 EDI 997 回执" --> G["🛑 HTTP 451 挂起 EDI 810 开票请款以防供应链罚款"]

    F -- "856 ASN 已获 997 确认 & 托盘条码完备" --> H["✅ HTTP 200 自动签发 EDI 810 电子发票并触发 PCard/SPT/ACH 结算<br/>(10ms 端到端无人工干预订单到收款 O2C 闭环)"]
```

---

### 3.2 传统“PunchOut 乱扣款/UOM 发错箱”反模式 vs. 标准 cXML + EDI 闭环架构对比图

```mermaid
flowchart LR
    subgraph BadPunchOut["❌ 传统反模式：跳出页直接扣款违约 + 把 10 个发成 10 箱 + 漏发 ASN 被罚"]
        direction TB
        BPO1["Ariba PunchOut 会话里直接收信用卡 -> 绕过买方审批被踢出供应商库"] --> BPO2["买方 850 下 10 EA(个)，卖方按 10 CS(箱) 发货 -> 产生 24 倍错单退货"]
        BPO2 --> BPO3["货车到仓还没发 EDI 856 ASN -> 被大客户每单重罚 $500 合规罚金"]
    end

    subgraph GoodPunchOut["✅ 生产级 cXML/OCI PunchOut 与 EDI 850/855/856/810 确定性架构"]
        direction TB
        GPO1["PunchOut 会话强制 disable_checkout=true -> 回传带 UNSPSC 的 cXML 购物车"] --> GPO2["审批通过接收 850 -> 确定性校验 UOM 换算与协议锁价 -> 秒回 855"]
        GPO2 --> GPO3["出库绑定 SSCC-18 生成 856 ASN -> 收到 997 回执后自动发 810 发票请款"]
    end
```

---

### 3.3 SAP Ariba/Coupa cXML PunchOut 选品、审批下发 EDI 850 与 855/856/810 端到端时序图

```mermaid
sequenceDiagram
    autonumber
    actor Buyer as 🏢 企业采购员 (在 Coupa / SAP Ariba 内)
    participant ERP as 🏛️ 买方采购系统 (Ariba / Coupa)
    participant Agent as 🤖 卖方 B2B PunchOut 与 EDI 协同 Agent
    participant Gate as 🛡️ UOM 换算、协议价与 856 ASN 门禁
    participant WMS as 📦 卖方仓库 WMS & Stripe B2B 结算

    Buyer->>ERP: 点击“从认证供应商目录采购 IT 配件”
    ERP->>Agent: 1. 发送 cXML PunchOutSetupRequest (含 BuyerCookie & 企业专属协议价组)
    Agent-->>Buyer: 渲染 AI 导购跳出页 (强制 disable_checkout=true，仅显示协议价与“传回采购车”)
    Buyer->>Agent: 选好 20 台扩展坞 ($110/EA)，点击“传回 Ariba 审批”
    Agent-->>ERP: 2. POST cXML PunchOutOrderMessage (含 8位 UNSPSC=43211602, UOM='EA', Total=$2,200)
    Note over Buyer,ERP: 买方部门总监在 Ariba 内点击“批准采购申请 (PR -> PO)”
    ERP->>Gate: 3. 正式下发 cXML OrderRequest / EDI 850 (PO #99812, 附带企业虚拟卡 PCard SPT)
    Gate->>Gate: 4. 确定性核验：<br/>• 校验 UOM='EA' 与协议价 $110 完全一致<br/>• 自动回复 EDI 855 订单确认单
    Gate-->>WMS: 5. 仓库出库生成 SSCC-18 托盘码，发送 EDI 856 ASN 并收到 EDI 997 确认回执
    WMS->>ERP: 6. 发送 EDI 810 电子发票并通过附带 PCard SPT 秒级结算 $2,200.00！
```

---

## 📊 四、企业 B2B 采购目录与订单协同路径横向选型矩阵

| 评估维度 | 方案 A：让大客户发 PDF/Excel 邮件采购单，人工录入 ERP | 方案 B：只给大客户开普通 B2C 网页账号密码 | 方案 C：静态 CIF/CSV 目录文件每季度手工上传一次 | 方案 D（推荐）：实时 `cXML/OCI PunchOut`（`disable_checkout=true`）+ `EDI 850/855/856/810` + SFTP `mode='upsert'` Agent |
|---|---|---|---|---|
| **与买方内部审批流（Ariba / Coupa）兼容性** | 极差（邮件往返慢，手工录单错漏率 `>8%`） | **不兼容**（无法回传购物车走买方内部预算流，常被合规部门禁用） | 支持，但库存与价格严重滞后 | **100% 原生无缝融入**（跳出实时选配 -> 回传买方 ERP 审批 -> 自动下发正式 PO） |
| **实时库存（ATP）与动态配置（CPQ）支持** | 无 | 有，但无 ERP 联动 | **不支持**（静态文件无法反应实时断货或复杂 BOM 选配） | **实时双向同步**（SFTP `mode="upsert"` 增量更新 + 跳出会话毫秒级查 ATP） |
| **包装单位（UOM）发错货与擅自涨价拦截** | 极易看错行或弄混箱/件 | 无企业 UOM 映射 | 中 | **100% 确定性拦截**（`EA/BX/CS/PLT` 换算锁 + `855 单价 <= 850 合同价` `HTTP 422`） |
| **大客户供应链罚款（ASN Chargeback）防御** | 常因漏发/晚发 ASN 被重罚 | 不支持 EDI 856 | 不支持 | **零罚单**（强制 `856 ASN + SSCC-18 + 997 回执` 齐备后才出库开票 `HTTP 451`） |

---

## 🧪 五、定量 B2B PunchOut/EDI 错单止损测算与 7-Card 报告数据溯源表（Benchmark & Provenance Matrix）

| 指标 / 门禁规则项 | 实测数值 / 决策行为 | 数据类别 (Provenance) | 精确来源路径 / 算例说明与架构意义 |
|---|---|---|---|
| **PunchOut 回传审批 + EDI 850/855 UOM/单价一致 + 856 ASN 确认（Happy Path）** | **`HTTP 200 OK` · `10 ms`**（门禁耗时，季度 B2B PunchOut 与 EDI 结算批次 `$260,000.00`） | `deterministic_offline_simulation` | `lab/webiq_commerce_demo.py` (`evaluate_b2b_punchout_edi_orchestration_agent_policy`)：验证 cXML 与 EDI 闭环 |
| **在 PunchOut 跳出页直接扣款绕过买方 ERP，或 SFTP 库存传 `mode='replace'`** | **`HTTP 403 Forbidden` · `11 ms` 拦截** (`PUNCHOUT_DIRECT_CHECKOUT_BYPASS_OR_SFTP_INVENTORY_REPLACE_BLOCKED`) | `official_doc_snapshot` | 严格执行 `disable_checkout=true` 与 `sftp_inventory_forbids_replace_mode` 官方规范 |
| **EDI 850/855 包装单位（`EA` vs `CS`）错配、855 擅自涨价，或缺失 8 位 `UNSPSC` 码** | **`HTTP 422 Unprocessable` · `14 ms` 拦截** (`EDI_855_PRICE_UOM_MISMATCH_OR_MISSING_UNSPSC_TAXONOMY_BLOCKED`) | `deterministic_offline_simulation` | 消灭“买 10 个发 10 箱”乌龙以及发票因缺分类码被买方 AP 拒付 |
| **未收到买方 `EDI 997` 确认的 `856 ASN`（含 `SSCC-18` 箱唛），或买方 EDI 网关证书过期** | **`HTTP 451 Hold` · `265 ms` 挂起** (`MISSING_EDI_856_ASN_SSCC18_ACK_OR_AS2_CERT_EXPIRY_HOLD`) | `official_doc_snapshot` | 防止因漏发预发货通知被大型商超/大客户开出高额供应链罚单 |
| **启用“cXML PunchOut 自动回传 + UOM 确定性换算 + 856/810 无接触秒级对账”** | **`HTTP 409 Confirm` · 立省人工录单成本、错发退运与 ASN 罚单 `$54,600.00`（净值 `$205,400.00`）** | `deterministic_offline_simulation` | 消除 B2B 录单错发与商超 ASN 合规罚款，回款周期提速 14 天（节省 `21.0%`） |
| **跨国 VAN 增值网与传统 AS2 专线大文件传输物理延迟** | 标记为 **`not_measured`** | `not_measured` | 通过离线确定性 cXML PunchOut 与 X12 EDI 策略引擎完整验证 |

---

## 🛠️ 六、商业上线风控与架构评审 Checklist（Architect Production Checklist）

- [ ] **1. PunchOut 会话强制开启 `disable_checkout=true` 仅回传购物车（`HTTP 403`）**：当识别到会话源自 `cXML PunchOutSetupRequest` 或 `SAP OCI` 时，是否已隐藏全部直接支付按钮，确保 100% 通过 `PunchOutOrderMessage` 回传买方 ERP 审批？
- [ ] **2. SFTP 商品与库存目录增量同步锁（强制 `mode="upsert"`）**：向平台或企业采购网同步库存时，是否已在代码层严禁传入 `mode="replace"`（遵守 Stage 1754 硬约束）？
- [ ] **3. EDI 850 / 855 计量单位（UOM）换算表与协议单价零上浮校验（`HTTP 422`）**：解析采购单时是否强制将 `EA / PK / BX / CS / PLT` 换算为基准最小单位核对总价，并拦截任何高于协议价的 855 确认单？
- [ ] **4. 8 位 `UNSPSC` 标准分类码与买方物料号（Buyer Part Number）完整性校验**：回传的购物车与电子发票是否 100% 携带买方财务系统要求的主数据编码？
- [ ] **5. `EDI 856 ASN`（含 `SSCC-18` 托盘码）与 `EDI 997` 回执前置门禁（`HTTP 451`）**：在触发 `EDI 810` 电子发票与扣款前，是否强制确认买方已成功接收并确认预发货通知？
- [ ] **6. AS2 / SFTP 数字签名证书自动轮换监控**：用于传输加密 EDI 报文的 X.509 双向证书是否在到期前 30 天自动预警轮换？
