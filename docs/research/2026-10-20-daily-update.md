# 2026-10-20 Agentic Commerce 技术资产与架构演进索引（中文版）

🌐 **Language / 语言导航**: **中文版 (当前)** | **[English Version (`2026-10-20-daily-update.en.md`)](2026-10-20-daily-update.en.md)** | **[2026-10-20 每日研究 (`research/daily/2026-10-20.md`)](../../research/daily/2026-10-20.md)** | **[English Daily Research (`research/daily/2026-10-20.en.md`)](../../research/daily/2026-10-20.en.md)**

---

## Stage 54：UCP `ucp-schema 2.0.0` 打包引用恢复与 `seller.logo` 边界、ACP 双源属性漂移与 `allOf` 饥饿防御、Google AP2 `kb+sd-jwt+kb` 终端受众强制校验与 Poppy `v0.2` DPoP、Sierra $\tau$-bench 2.0.0 外呼实体采集与 Visa TAP `x402` 结账护栏（全套中英双语化）

- **一手协议与上游代码审计**：
  1. **Universal Commerce Protocol (`Universal-Commerce-Protocol/ucp`)**：PR `#982`（恢复 `ucp-schema 2.0.0` `--bundle` 剥离非根 `$id` 后的跨文件 `$ref` 链接并规范化 `_resolve_schema` 缓存键）与 PR `#962`（共享变体可选 `seller.logo` 媒体引用及非发现权威绑定边界）。
  2. **Agentic Commerce Protocol (`agentic-commerce-protocol/agentic-commerce-protocol`)**：PR `#310`（JSON Schema `$defs` 与 OpenAPI `components.schemas` 双向属性漂移检测及 23 处已知漂移基线反陈旧门禁）、PR `#290` / `#275`（修复 JSON Schema 2020-12 `allOf` + `additionalProperties: false` 导致 `CheckoutSessionWithOrder.order` 与 `DelegateAuthenticationSessionWithResult.authentication_result` 兄弟属性被拒绝的缺陷）及 PR `#284`（修复 `PaymentHandler.display_order` 缩进脱离 `properties:`）。
  3. **Google AP2 (`google-agentic-commerce/AP2`) & Poppy `v0.2`**：PR `#369`（跨语言合规语料库及修复 `poc_aud_not_enforced.py` 揭示的 `kb+sd-jwt+kb` 终端受众 `expected_aud` 静默绕过漏洞）、PR `#385`/`#383`（`ParsedToken.cnf_jwk` `mode="json"` 序列化枚举字段 `use="sig"`）、PR `#384`（`verify_receipt` `has_reference_in_store_cb` 空回调防护）及 Poppy `v0.2` commit `39b35bd`（`#71`：`ES256` + $\ge 128\text{-bit}$ `jti` DPoP 证明、MCP Bearer 豁免与 API 写请求 `Idempotency-Key`）。
  4. **Sierra $\tau$-bench `2.0.0` (`sierra-research/tau2-bench` `#642`, `989d328`) & Visa TAP (`visa/trusted-agent-protocol` `#11`)**：实施 $\tau$-bench 2.0.0 `intake` 外呼实体采集六大护栏（先征得同意、仅采工单缺失字段、禁编造外部值、提交前静默 `log_capture`、`mod-97`/ISO 日期时间校验、提前挂断零提交、`submit_fields` 与 `end_call` 跨轮次隔离）及 Visa TAP `x402` Solana/Base USDC 机器对机器结账护栏。
- **新增代码与双语文档资产**：
  - 护栏模块：[`lab/ucp_schema_bundle_acp_drift_ap2_aud_tau2_intake_guard.py`](../../lab/ucp_schema_bundle_acp_drift_ap2_aud_tau2_intake_guard.py)
  - 单元测试：[`tests/test_ucp_schema_bundle_acp_drift_ap2_aud_tau2_intake_guard.py`](../../tests/test_ucp_schema_bundle_acp_drift_ap2_aud_tau2_intake_guard.py)（全量单测 **316/316** 通过）
  - 双语文档：[`README.md`](../../README.md) ⇄ [`README.en.md`](../../README.en.md)、[`research/daily/2026-10-20.md`](../../research/daily/2026-10-20.md) ⇄ [`research/daily/2026-10-20.en.md`](../../research/daily/2026-10-20.en.md)、[`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md` (§53)](2026-10-18-agentic-commerce-full-stack-architecture.md) ⇄ [`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.en.md`](2026-10-18-agentic-commerce-full-stack-architecture.en.md)

---

## Stage 55：16 场景中英双语 7-Card 4:5 视觉基准评测报告（`SD-01..SD-16`）

- **基准评测覆盖（`SD-01..SD-16`）**：
  - 评估 AI-Native 6-Plane 护栏对比经典三层 Web 基线在 UCP `#982` 打包 `$ref` 恢复、`#962` 卖家 Logo 非权威边界、ACP `#310`/`#290`/`#284`/`#275` 属性漂移与 `allOf` 饥饿防御、Google AP2 `#369` `kb+sd-jwt+kb` 终端跳 `expected_aud` 强制校验、`#385`/`#384` `cnf.jwk` JSON 枚举与回执核验、Poppy `v0.2` `#71` DPoP、Sierra $\tau$-bench 2.0.0 `#642` `intake` 外呼采集及 Visa TAP `#11` `x402` USDC 结账上的拦截表现。
  - **评测结果**：AI-Native 通过率 **16/16 (100.0%)** vs 经典三层基线 **1/16 (6.2%)**，键序翻转扰动一致性 **100.0%**，平均内联延迟 **0.41 ms** vs **2.09 ms**（提速 **5.1x**）。
- **新增代码与双语报告资产**：
  - 基准生成器：[`lab/ucp_schema_acp_drift_ap2_aud_tau2_intake_bench.py`](../../lab/ucp_schema_acp_drift_ap2_aud_tau2_intake_bench.py)
  - 单元测试：[`tests/test_ucp_schema_acp_drift_ap2_aud_tau2_intake_bench.py`](../../tests/test_ucp_schema_acp_drift_ap2_aud_tau2_intake_bench.py)（全仓库 **318/318** 单测通过）
  - 双语 7-Card 4:5 报告：[`reports/agentic-commerce-ucp-schema-acp-drift-ap2-aud-tau2-intake-bench/index.html`（中文）](../../reports/agentic-commerce-ucp-schema-acp-drift-ap2-aud-tau2-intake-bench/index.html) ⇄ [`index.en.html`（English）](../../reports/agentic-commerce-ucp-schema-acp-drift-ap2-aud-tau2-intake-bench/index.en.html) ⇄ [`report.json`](../../reports/agentic-commerce-ucp-schema-acp-drift-ap2-aud-tau2-intake-bench/report.json)

---

## Stage 56：UCP RFC 9728/8414 多发证方身份发现与履约/状态机契约、Mercado Pago Pix 带外展示构件 & Razorpay Magic 托管结账、ACP Delegate Auth `Signature` 必填与解包错误信封、以及 Sierra $\tau$-bench 2.0 `loan_servicing`（英/法）与时间戳规范化护栏（中英双语）

- **一手协议与上游代码审计**：
  1. **Universal Commerce Protocol (`Universal-Commerce-Protocol/ucp`)**：PR `#891`（RFC 9728 `authorization_servers` 与 RFC 8414 §3.3 字节级 `issuer` 精确匹配、严禁去尾斜杠归一化、仅 HTTP `404` 允许回退 OIDC Discovery、多候选顺序优选并显式记录丢弃项）、PR `#573`（履约选项 `options[].totals` 非空数组且 `description` 不得重复标题/价格）、PR `#672`（恢复 `ready_for_complete -> requires_escalation` 与 `ready_for_complete <-> incomplete` 生命周期转换）、PR `#635`（`com.mercadopago.payment.render_artifact` Pix 带外展示构件：禁 `continue_url` 重定向、禁实例 `required` 字段、到期时间不越界、同源说明页防自动提交与零敏感凭证）及 PR `#316`（`com.razorpay.magic_checkout` `hosted_checkout` 支付工具与凭证：禁平台拉取凭证、`return_url != continue_url` 与取消重定向后权威轮询）。
  2. **Agentic Commerce Protocol (`agentic-commerce-protocol/agentic-commerce-protocol`)**：PR `#287`（`openapi.delegate_authentication.yaml` 将 `Signature` 头标为 `required: true`）、PR `#289`（`CheckoutSessionCreateRequest` 要求 `line_items`/`currency`/`capabilities`，拦截旧版 `items`/`product_id`）及 PR `#266`/`#243`（移除已发布 `delegate_payment` OpenAPI 示例中的 `{ "error": { ... } }` 包装层，对齐顶层 `Error` Schema）。
  3. **Sierra $\tau$-bench 2.0 (`sierra-research/tau2-bench`)**：PR `#638`（Boréal Finance 英/法消费贷款服务域 `loan_servicing` / `loan_servicing_fr`：三要素核身、两次失败转人工 `failed_verification`、授权第三方只读范围、每项写操作需先获 `"yes"` 确认且禁与消息同轮调用、同通话申请豁免与还款时必须先豁免滞纳金后扣款、改邮箱后同会话禁发文档）与 PR `#634`（`banking_knowledge` `canonicalize_time_verified` 将等价的 `2025-11-14 03:40:00 EST` 变体规范化，同时保留伪造时间或错误时区 `Z`/`+00:00`/`PST` 以便评分拦截）。
- **新增代码与双语文档资产**：
  - 护栏模块：[`lab/ucp_rfc9728_pix_razorpay_acp_envelope_tau2_loan_guard.py`](../../lab/ucp_rfc9728_pix_razorpay_acp_envelope_tau2_loan_guard.py)
  - 单元测试：[`tests/test_ucp_rfc9728_pix_razorpay_acp_envelope_tau2_loan_guard.py`](../../tests/test_ucp_rfc9728_pix_razorpay_acp_envelope_tau2_loan_guard.py)（全仓库 **322/322** 单测通过）
  - 双语架构章节：[`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md` (§55)](2026-10-18-agentic-commerce-full-stack-architecture.md) ⇄ [`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.en.md`](2026-10-18-agentic-commerce-full-stack-architecture.en.md)

---

## Stage 57：16 场景中英双语 7-Card 4:5 视觉基准评测报告（`RP-01..RP-16`）

- **基准评测覆盖（`RP-01..RP-16`）**：
  - 评估 AI-Native 6-Plane 护栏对比经典三层 Web 基线在 UCP `#891` RFC 9728/8414 多发证方身份发现、`#573` 履约 `options[].totals` 数组、`#672` `ready_for_complete` 状态回退/升级、`#635` Mercado Pago Pix `render_artifact` 带外展示构件、`#316` Razorpay Magic `hosted_checkout`、ACP `#287` `delegate_authentication` 必填 `Signature` 头、`#289` `CheckoutSessionCreateRequest` 必填字段、`#266` `delegate_payment` 顶层解包 `Error` 信封，以及 Sierra $\tau$-bench 2.0 `#638` Boréal Finance 英/法消费信贷服务与 `#634` `canonicalize_time_verified` 上的拦截表现。
  - **评测结果**：AI-Native 通过率 **16/16 (100.0%)** vs 经典三层基线 **1/16 (6.2%)**，候选重排与时间戳变体扰动一致性 **100.0%**，平均内联延迟 **0.38 ms** vs **2.06 ms**（提速 **5.4x**）。
- **新增代码与双语报告资产**：
  - 基准生成器：[`lab/ucp_rfc9728_pix_razorpay_acp_envelope_tau2_loan_bench.py`](../../lab/ucp_rfc9728_pix_razorpay_acp_envelope_tau2_loan_bench.py)
  - 单元测试：[`tests/test_ucp_rfc9728_pix_razorpay_acp_envelope_tau2_loan_bench.py`](../../tests/test_ucp_rfc9728_pix_razorpay_acp_envelope_tau2_loan_bench.py)（全仓库 **324/324** 单测通过）
  - 双语 7-Card 4:5 报告：[`reports/agentic-commerce-ucp-rfc9728-pix-razorpay-acp-envelope-tau2-loan-bench/index.html`（中文）](../../reports/agentic-commerce-ucp-rfc9728-pix-razorpay-acp-envelope-tau2-loan-bench/index.html) ⇄ [`index.en.html`（English）](../../reports/agentic-commerce-ucp-rfc9728-pix-razorpay-acp-envelope-tau2-loan-bench/index.en.html) ⇄ [`report.json`](../../reports/agentic-commerce-ucp-rfc9728-pix-razorpay-acp-envelope-tau2-loan-bench/report.json)

---

## Stage 58：UCP 购买选项扩展（`#901`）与多卖家目录变体 `offers[]` 归因（`#811`/`#933`/`#831`）、ACP 结账行 `Item.url` 跨品牌去歧义与 Feed 边界（`#281`/`#256`/`#241`）、Google AP2 多跳 `~~` 委托链末跳脱敏与原子单次消费预留锁（`#363`/`#359`/`#347`）、以及 Sierra $\tau$-bench 2.0 六语种语音基准与 Crossed Pass³ 评审指纹门禁（`#637`/`#639`/`#620`）（中英双语）

- **一手协议与上游代码审计**：
  1. **Universal Commerce Protocol (`Universal-Commerce-Protocol/ucp`)**：PR `#901`（`dev.ucp.shopping.purchase_options` 购买选项扩展：`purchase_options[]` 仅限响应下发、`selected_purchase_option_id` 共现约束与 `complete` 省略、失效选择回退默认项并强制发出 `purchase_option_changed` 警告、免费试用禁填 `price: 0`、以及订单行 `purchase_option` `{id, title}` 快照固化）、PR `#811`（多卖家目录变体 `offers[]` 归因：`offers[].seller.domain` 裸域名标记 Merchant of Record、结账必须传 `offers[].item_id` 且严禁传 `variant.id`、`offers[].price` 优先于展示价 `variant.price`）、PR `#933`（Profile/JWKS/CIMD 条件请求 `304 Not Modified` 允许命中缓存 vs 严禁 `301`/`302`/`303`/`307`/`308` 重定向）与 PR `#831`（MCP 工具调用 Schema 将 `$defs/ucp_agent` 重命名为 `$defs/agent` 以规避 `ucp_` 保留前缀 `W007` 告警）。
  2. **Agentic Commerce Protocol (`agentic-commerce-protocol/agentic-commerce-protocol`)**：PR `#281`（SEP `#280` 结账请求 `Item.url` 规范商品页 URL，消除单卖家账户下跨品牌/多店面共享 SKU 的归属歧义）、PR `#256`（Product Feed API 服务源对齐为代理端托管 `https://agent.example.com`，并在 `Product.variants` 与 `UpsertProductsRequest.products` 强制 `minItems: 1`）与 PR `#241`（在 Feed JSON Schema 打包文件中补齐 `UpsertProductsResponse` `{id, accepted}`）。
  3. **Google Agent Payments Protocol (`google-agentic-commerce/AP2`)**：PR `#363`（`MandateClient.present()` 通过 `rpartition("~~")` 隔离末跳 `SD-JWT`，仅对末跳执行选择性披露脱敏与 `sd_hash` 绑定，原样保留前置跳并拦截前置跳披露篡改）、PR `#359`（`CheckoutMandateChain.verify()` 即使调用方省略 `expected_checkout_hash` 也强制从所呈递 `checkout_jwt` 实时计算 `compute_sha256_b64url` 并比对 `closed_mandate.checkout_hash`）与 PR `#347`（凭证提供方与商户支付处理器采用 SQLite `BEGIN IMMEDIATE` + `synchronous=FULL` 原子预留闭式付款授权哈希与结账事务 ID，联合校验旧版 token-store 并在状态损坏时以 `replay_state_unavailable` 故障闭合，重放返回 `mandate_already_used`）。
  4. **Sierra $\tau$-bench 2.0 (`sierra-research/tau2-bench`)**：PR `#637`（发布跨 `en/es/pt/hi/zh/ko` 六语种的 `voice-v2-banking` `banking_knowledge_97` 共 `582` 通电话与 `voice-v2-entity` `intake_200` 共 `1,200` 通电话及 `240s` 时长上限，校验证据包每语种 `binding_revision` 锁定哈希）、PR `#639`（Crossed Pass³ 迁移至 `voice-v2-rcs-v3` 全局种子 `42/401/16319`、支持只读复用已验证的 seed-42 `--regular-results`、并要求 Gemini 3.8 扩展思考模式下 `google-genai >= 2.26`）与 PR `#620`（`tau2 submit prepare/validate` 强制 `voice-v2` 矩阵零缺失/错误/未评分记录且全部适用裁判指标均具存盘裁决，随包生成并重算校验 `benchmark-diagnostics.json` 内容指纹）。
- **新增代码与双语文档资产**：
  - 护栏模块：[`lab/ucp_purchase_options_offers_acp_feed_ap2_multihop_tau2_voice_guard.py`](../../lab/ucp_purchase_options_offers_acp_feed_ap2_multihop_tau2_voice_guard.py)
  - 单元测试：[`tests/test_ucp_purchase_options_offers_acp_feed_ap2_multihop_tau2_voice_guard.py`](../../tests/test_ucp_purchase_options_offers_acp_feed_ap2_multihop_tau2_voice_guard.py)（全仓库 **329/329** 单测通过）
  - 双语架构章节：[`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md` (§57)](2026-10-18-agentic-commerce-full-stack-architecture.md) ⇄ [`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.en.md`](2026-10-18-agentic-commerce-full-stack-architecture.en.md)

---

## Stage 59：16 场景中英双语 7-Card 4:5 视觉基准评测报告（`PO-01..PO-16`）

- **基准评测覆盖（`PO-01..PO-16`）**：
  - 评估 AI-Native 6-Plane 护栏对比经典三层 Web 基线在 UCP `#901` 购买选项扩展、`#811` 多卖家目录变体 `offers[]` 归因与裸域名 MoR、`#933` HTTP `304 Not Modified` 条件缓存与 `3xx` 重定向阻断、`#831` MCP `$defs/agent` 规范化、ACP `#281` `Item.url` 跨品牌消歧、`#256`/`#241` Agent 托管 Feed 源点与 `UpsertProductsResponse`、Google AP2 `#363` 多跳 `~~` 末跳披露隔离、`#359` 呈递态 `checkout_hash` 强制派生、`#347` 原子单次预留锁，以及 Sierra $\tau$-bench 2.0 `#637`/`#639`/`#620` 六语种 `voice-v2` 与 Crossed Pass³ 评审指纹门禁上的表现。
  - **评测结果**：AI-Native 通过率 **16/16 (100.0%)** vs 经典三层基线 **1/16 (6.25%)**，购买选项/多卖家报价/多跳候选键/多语种顺序反转一致性 **100.0%**，中位内联延迟 **0.36 ms** vs **4.595 ms**（提速 **12.6x**）。
- **新增代码与双语报告资产**：
  - 基准生成器：[`lab/ucp_purchase_options_offers_acp_feed_ap2_multihop_tau2_voice_bench.py`](../../lab/ucp_purchase_options_offers_acp_feed_ap2_multihop_tau2_voice_bench.py)
  - 单元测试：[`tests/test_ucp_purchase_options_offers_acp_feed_ap2_multihop_tau2_voice_bench.py`](../../tests/test_ucp_purchase_options_offers_acp_feed_ap2_multihop_tau2_voice_bench.py)（全仓库 **331/331** 单测通过）
  - 双语 7-Card 4:5 报告：[`reports/agentic-commerce-ucp-purchase-options-offers-acp-feed-ap2-multihop-tau2-voice-bench/index.html`（中文）](../../reports/agentic-commerce-ucp-purchase-options-offers-acp-feed-ap2-multihop-tau2-voice-bench/index.html) ⇄ [`index.en.html`（English）](../../reports/agentic-commerce-ucp-purchase-options-offers-acp-feed-ap2-multihop-tau2-voice-bench/index.en.html) ⇄ [`report.json`](../../reports/agentic-commerce-ucp-purchase-options-offers-acp-feed-ap2-multihop-tau2-voice-bench/report.json)

---

## Stage 60：UCP 根数组 Schema 反模式拦截（`#948`）与 Order 方向注解净化（`#903`/`#900`/`#882`/`#869`）、ACP 结账请求 `LineItem` 引用对齐与委托认证结果扁平 Schema（`#270`/`#261`/`#254`/`#252`）、Google AP2 `.1` 版本化 VCT 常量与 `PaymentInstrument` 扩展签名保留及 `~~` 多跳链解码（`#349`/`#333`/`#329`/`#351`/`#365`/`#364`）、以及 Sierra $\tau$-bench 2.0 Voice Design API 单位（`guidance_scale=5`）与文本矩阵内联计数（`#636`/`#619`/`#616`/`#645`/`#632`）（中英双语）

- **一手协议与上游代码审计**：
  1. **Universal Commerce Protocol (`Universal-Commerce-Protocol/ucp`)**：PR `#948`（禁止在能力、扩展与操作载荷根级声明 `"type": "array"`，保障非破坏性同级元数据扩展、`allOf` 属性组合与保留 `ucp` 成员承载）、PR `#903`（清除 `source/schemas/shopping/order.json` 上导致 OpenAPI 3.1 `order_event_webhook` 剥离 `currency`/`policies`/`attribution` 的游离 `"ucp_request": "omit"` 注解及 `payment_terms.json` 冗余 `"ucp_response": "optional"`）、PR `#882`（明确 `com.{vendor}.*` / `org.{org}.*` 厂商扩展必须自托管于组织自有域名，禁止合入核心 `dev.ucp.*` 仓库）、PR `#869`（明确商家回填 `buyer`/`payment.instruments[]`/`loyalty` 存储态必须基于已认证且获授权的用户请求，而非仅凭无门禁的 `config.scopes`）与 PR `#900`（`validate_examples.py --export-corpus examples.json` 仅导出完整且通过扩展组合 Schema 校验的文档示例）。
  2. **Agentic Commerce Protocol (`agentic-commerce-protocol/agentic-commerce-protocol`)**：PR `#270`（将 `2026-01-30`、`2026-04-17` 与 `unreleased` OpenAPI 中 `CheckoutSessionCreateRequest.line_items` 与 `CheckoutSessionUpdateRequest.line_items` 的引用从裸 `Item` 对齐至带 `quantity` 与 `totals[]` 的 `LineItem`）、PR `#261`（将 `DelegateAuthenticationSessionWithResult` 重构为显式包含 `authentication_result` 的扁平 `type: object` + `additionalProperties: false` Schema，并补齐 4 大规范示例映射）及 PR `#254`/`#252`（新增 `$defs`/`components.schemas` 内嵌示例与 OpenAPI `requestBody`/`responses` 内联 `$ref` 示例一致性校验）。
  3. **Google Agent Payments Protocol (`google-agentic-commerce/AP2`)**：PR `#349`（统一四大授权凭证精确版本化 VCT 常量 `mandate.payment.open.1`、`mandate.checkout.open.1`、`mandate.payment.1`、`mandate.checkout.1`）、PR `#333`/`#329`（在 `payment_instrument.json` 显式声明 `additionalProperties: true` / `ConfigDict(extra='allow')` 以保留 x402 `payee_address` 与 `facilitator` 扩展字段穿越 `model_dump()` 与签名流程）、PR `#351`（`sdJwtDecoder.ts` 先按 `~~` 切分多跳委托链再逐跳按 `~` 解析，防止将第 2 跳误判为第 1 跳末尾 `kbJwt` 并丢失披露项）、PR `#365`（`ReceiptClient.verify_receipt` 兼容 `ec.EllipticCurvePublicKey` `JWK.from_pyca` 与 `JWK`，且在调用 `has_reference_in_store_cb` 前完成签名核验）与 PR `#364`（关闭 MCP `include_payloads=True` 并从 A2A/MCP 日志中抹除支付令牌、结账授权、`risk_data` 与回退提示词）。
  4. **Sierra $\tau$-bench 2.0 (`sierra-research/tau2-bench`)**：PR `#636`（修复 `setup_voices` 将 UI 滑块 `38%` 误作 API 值 `guidance_scale=38` 发送导致语音迟缓停顿并造成高达 `10%` 评分偏差的问题，对齐 ElevenLabs API 默认值 `guidance_scale=5`）、PR `#619`（为 `en/es/pt/hi/zh/ko` 六语种提供独立于 `pack_sha256` 锁定的 `data/tau2/voice_design/<lang>.yaml` `eleven_ttv_v3` 角色设计提示词）、PR `#616`（修复 `export_submission` 传入单元格目录而非 `results.json` 文件路径导致 `text-v1` 内联仿真被误判为 `0` 计数的缺陷）及 PR `#645`/`#632`（修正 `RewardType.ACTION` 在 `telecom` 32 个任务与 `banking_knowledge` 9 个任务中的真实分布，并在 `tau2 factory` `draft()` 中实施最多 1 次有界修复）。
- **新增代码与双语文档资产**：
  - 护栏模块：[`lab/ucp_root_array_order_acp_lineitem_ap2_vct_tau2_voice_design_guard.py`](../../lab/ucp_root_array_order_acp_lineitem_ap2_vct_tau2_voice_design_guard.py)
  - 单元测试：[`tests/test_ucp_root_array_order_acp_lineitem_ap2_vct_tau2_voice_design_guard.py`](../../tests/test_ucp_root_array_order_acp_lineitem_ap2_vct_tau2_voice_design_guard.py)（全仓库 **340/340** 单测通过）
  - 双语架构章节：[`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md` (§59)](2026-10-18-agentic-commerce-full-stack-architecture.md) ⇄ [`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.en.md`](2026-10-18-agentic-commerce-full-stack-architecture.en.md)

---

## Stage 61：覆盖 Stage 60 四大协议域的 16 场景（`RA-01..RA-16`）中英双语 7-Card 4:5 视觉基准评测报告（中英双语）

- **16 场景确定性基准评测（`RA-01..RA-16`）**：
  - `RA-01..RA-04`：UCP `#948` 根数组 Schema 反模式拦截、`#903` Order 快照与 `order_event_webhook` 方向注解净化、`#882` 厂商自定义命名空间自托管边界、`#869` 商家回填用户存储态强制认证门禁与 `#900` 合规语料库导出。
  - `RA-05..RA-08`：ACP `#270` 结账请求 `LineItem` 引用对齐、`#261` `DelegateAuthenticationSessionWithResult` 扁平 Schema 与 `#254`/`#252` 内嵌/内联示例校验。
  - `RA-09..RA-12`：Google AP2 `#349` `.1` 精确版本化 VCT 常量、`#333`/`#329` `PaymentInstrument` x402 扩展字段签名保留、`#351` `~~` 优先多跳委托链解码、`#365` EC/JWK 收据验签与 `#364` 敏感支付日志脱敏。
  - `RA-13..RA-16`：Sierra $\tau$-bench 2.0 `#636` ElevenLabs Voice Design API 单位（`guidance_scale=5` vs UI `38%`）、`#619` 六语种非锁定 `voice_design/<lang>.yaml`、`#616` 文本矩阵 `results.json` 内联仿真计数与 `#645`/`#632` Telecom `ACTION` 奖励基准及单次有界修复。
- **量化评测结果**：
  - **AI-Native 6-Plane 架构**：**16/16 (100.0%)** 场景准确率，逆序扰动稳定性 **100.0%**，中位延迟 **0.35 ms**。
  - **经典三层架构基线（Classic 3-Tier）**：**1/16 (6.25%)** 场景准确率，中位延迟 **4.595 ms**（AI-Native 提速 **13.1x**）。
- **新增代码与双语报告资产**：
  - 基准生成器：[`lab/ucp_root_array_order_acp_lineitem_ap2_vct_tau2_voice_design_bench.py`](../../lab/ucp_root_array_order_acp_lineitem_ap2_vct_tau2_voice_design_bench.py)
  - 单元测试：[`tests/test_ucp_root_array_order_acp_lineitem_ap2_vct_tau2_voice_design_bench.py`](../../tests/test_ucp_root_array_order_acp_lineitem_ap2_vct_tau2_voice_design_bench.py)（全仓库 **342/342** 单测通过）
  - 双语 7-Card 4:5 报告：[`reports/agentic-commerce-ucp-root-array-order-acp-lineitem-ap2-vct-tau2-voice-design-bench/index.html`（中文）](../../reports/agentic-commerce-ucp-root-array-order-acp-lineitem-ap2-vct-tau2-voice-design-bench/index.html) ⇄ [`index.en.html`（English）](../../reports/agentic-commerce-ucp-root-array-order-acp-lineitem-ap2-vct-tau2-voice-design-bench/index.en.html) ⇄ [`report.json`](../../reports/agentic-commerce-ucp-root-array-order-acp-lineitem-ap2-vct-tau2-voice-design-bench/report.json)

---

## Stage 62：UCP 购物车结账完成 `cart_id` 剥离（`#911`/`#910`）与 `UCP-Agent` 签名覆盖（`#907`/`#906`/`#883`/`#853`）、ACP BOPIS 门店扩展（`#171`）与逐行限时报价（`#165`/`#162`/`#230`/`#161`）、Google AP2 闭式结账绑定（`#330`）与 x402 密钥/金额故障闭合及 TrustBoost 隐私脱敏（`#310`/`#300`/`#267`）、以及 Sierra $\tau$-bench 2.0 活跃电信线路充值（`#611`）与实时环境 DB 评分 / 故障注入 / GPT-5 `tool_choice` 保留（`#609`/`#610`/`#615`/`#621`）（中英双语）

- **一手协议与上游代码审计**：
  1. **Universal Commerce Protocol (`Universal-Commerce-Protocol/ucp`)**：PR `#911`/`#871`（在 `shopping/cart.json#/$defs/checkout` 为 `cart_id.ucp_request` 补充 `"complete": "omit"` 并拦截 `complete_checkout` 请求携带 `cart_id`）、PR `#910`（明确通过 `cart_id` 创建结账时因 `allOf` 单调继承仍须传入 `"line_items": []`）、PR `#907`（当结账签名请求携带 `UCP-Agent` 头时，`Signature-Input` 覆盖集必须包含 `"ucp-agent"`）、PR `#906`（OpenRPC `ec.auth` 与 `ep.cart.auth` 的 `type` 参数标记为 `"required": true`）、PR `#883`（MCP `complete_checkout` 暴露 `buyer_consent` 与 `ap2_mandate` 扩展）与 PR `#853`（规范条款提取器 `REQ-*` ID、10 位 SHA-256 `content_digest` 与 `207 + 29 + 23 = 259` 守恒对账）。
  2. **Agentic Commerce Protocol (`agentic-commerce-protocol/agentic-commerce-protocol`)**：PR `#230`（`delegate_payment` 中 `allowance.checkout_session_id` 设为可选）、PR `#161`（扩展 `401`/`500`/`503` 错误枚举并规定未知错误码前向兼容回退）、PR `#171`（BOPIS 门店扩展：允许在创建/更新结账时传入 `store_id`，但严禁在 `CheckoutSessionCompleteRequest` 中传入 `store_id`）、PR `#165`（逐行 `LineItem.valid_until` 与 `offer_valid`/`offer_expired` 状态及 `offer_expired` vs `quote_expired` 错误码）与 PR `#162`（纯数字商品订单严禁使用物理物流专属的 `shipped` 状态）。
  3. **Google Agent Payments Protocol (`google-agentic-commerce/AP2`)**：PR `#330`（`PaymentMandateChain.verify()` 默认强制校验闭式支付授权 `transaction_id` 与目标 Checkout JWT 的绑定）、PR `#310`（x402 PSP `settle_payment` 在缺失 `agent_provider_pub` 时立即返回 `agent_provider_key_missing` 故障闭合）、PR `#300`（x402 凭证提供方严格按已验签 `closed_mandate.payment_amount.amount` 授权，严禁回退至硬编码 `1250` 美分）与 PR `#267`（TrustBoost 多语种/拉美 `CPF`/`CUIT`/`RFC` 脱敏与 Solana `anchor_tx` 存证）。
  4. **Sierra $\tau$-bench 2.0 (`sierra-research/tau2-bench`)**：PR `#611`（`refuel_data` 在修改流量与账单前强制校验电信线路状态为 `"active"`）、PR `#609`/`#610`（以实时环境哈希 `live_db_hash` 决定奖励评分、记录 `replay_divergence` 并支持 `timeout_before_commit` / `timeout_after_commit` 确定性故障注入）、PR `#615`（按记录语言包校验 50 个替换任务）与 PR `#621`（桥接 GPT-5 Responses 调用传入 `allowed_openai_params=["tool_choice"]` 防止 `tool_choice="required"` 被丢弃为 `None`）。
- **新增代码与双语文档资产**：
  - 护栏模块：[`lab/ucp_cart_complete_acp_store_offer_ap2_x402_tau2_telecom_guard.py`](../../lab/ucp_cart_complete_acp_store_offer_ap2_x402_tau2_telecom_guard.py)
  - 单元测试：[`tests/test_ucp_cart_complete_acp_store_offer_ap2_x402_tau2_telecom_guard.py`](../../tests/test_ucp_cart_complete_acp_store_offer_ap2_x402_tau2_telecom_guard.py)（全仓库 **351/351** 单测通过）
  - 双语架构章节：[`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md` (§61)](2026-10-18-agentic-commerce-full-stack-architecture.md) ⇄ [`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.en.md`](2026-10-18-agentic-commerce-full-stack-architecture.en.md)





