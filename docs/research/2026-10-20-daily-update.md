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

---

## Stage 63：覆盖 Stage 62 四大协议域的 16 场景（`CC-01..CC-16`）中英双语 7-Card 4:5 视觉基准评测报告（中英双语）

- **16 场景确定性基准评测（`CC-01..CC-16`）**：
  - `CC-01..CC-04`：UCP `#910`/`#911` 购物车转结账 `line_items` 必填与 `complete: omit`、`#907` `UCP-Agent` 签名覆盖集、`#906` OpenRPC `ec.auth`/`ep.cart.auth` `type` 必填、`#883` MCP `complete_checkout` 扩展暴露及 `#853` 259 条 `REQ-*` 规范条款目录。
  - `CC-05..CC-08`：ACP `#230` 可选 `allowance.checkout_session_id`、`#171` BOPIS `store_id` 严禁在 `complete` 阶段篡改、`#165` 行级 `LineItem.valid_until` 与 `offer_expired` vs. `quote_expired`、`#162` 纯数字订单禁 `shipped` 及 `#161` 错误前向兼容。
  - `CC-09..CC-12`：Google AP2 `#330` 闭式支付授权 `transaction_id` 结账绑定、`#310` x402 PSP 公钥缺失故障闭合、`#300` x402 严禁回退硬编码 `1250` 美分与 `#267` TrustBoost 拉美 `CPF`/`CUIT`/`RFC` 脱敏及 Solana 锚定。
  - `CC-13..CC-16`：Sierra $\tau$-bench 2.0 `#611` 电信活跃线路 `refuel_data` 状态校验、`#609`/`#610` 实时环境 DB 哈希评分与 `ToolFault` 超时注入、`#615` 语言包替换任务核验及 `#621` GPT-5 Responses 桥接 `tool_choice` 保留。
- **量化评测结果**：
  - **AI-Native 6-Plane 架构**：**16/16 (100.0%)** 场景准确率，逆序扰动稳定性 **100.0%**，中位延迟 **0.35 ms**。
  - **经典三层架构基线（Classic 3-Tier）**：**1/16 (6.25%)** 场景准确率，中位延迟 **4.605 ms**（AI-Native 提速 **13.2x**）。
- **新增代码与双语报告资产**：
  - 基准生成器：[`lab/ucp_cart_complete_acp_store_offer_ap2_x402_tau2_telecom_bench.py`](../../lab/ucp_cart_complete_acp_store_offer_ap2_x402_tau2_telecom_bench.py)
  - 单元测试：[`tests/test_ucp_cart_complete_acp_store_offer_ap2_x402_tau2_telecom_bench.py`](../../tests/test_ucp_cart_complete_acp_store_offer_ap2_x402_tau2_telecom_bench.py)（全仓库 **353/353** 单测通过）
  - 双语 7-Card 4:5 报告：[`reports/agentic-commerce-ucp-cart-complete-acp-store-offer-ap2-x402-tau2-telecom-bench/index.html`（中文）](../../reports/agentic-commerce-ucp-cart-complete-acp-store-offer-ap2-x402-tau2-telecom-bench/index.html) ⇄ [`index.en.html`（English）](../../reports/agentic-commerce-ucp-cart-complete-acp-store-offer-ap2-x402-tau2-telecom-bench/index.en.html) ⇄ [`report.json`](../../reports/agentic-commerce-ucp-cart-complete-acp-store-offer-ap2-x402-tau2-telecom-bench/report.json)

---

## Stage 64：UCP 服务 `schema` 传输定义多态（`#833`）与永久链接 CSRF 合并护栏及 WBA 签名覆盖（`#831`/`#791`/`#789`/`#785`）、ACP Stripe Link 钱包处理器（`com.stripe.link`，`#156`）与钱包干预流及 11 种会话状态（`#150`/`#144`/`#166`/`#151`）、Google AP2 跨商户原子预算权威（`#252`）与 Solana Pay 单次 `reference` 公钥绑定及 `AP2-Haggle` 多轮议价（`#228`/`#229`）、以及 Sierra $\tau$-bench 2.0 残缺黄金 DB 状态撤回认证（`#580`）与 NL 裁判裁决数 / 空轮次过滤 / `evaluator_cost` 独立核算（`#581`/`#584`/`#593`/`#600`/`#588`）（中英双语）

- **一手协议与上游代码审计**：
  1. **Universal Commerce Protocol (`Universal-Commerce-Protocol/ucp`)**：PR `#833`（明确 `services[].schema` 按 `rest`/`mcp`/`embedded`/`a2a` 指向 OpenAPI 3.1、OpenRPC 1.3.2 或缺省由 `endpoint` Agent Card 解析，区别于 `capabilities` 与 `payment_handlers` 的 JSON Schema 2020-12）、PR `#831`（`ucp-schema` `W007` 规则：将 `$defs/ucp_agent` 重命名为 `$defs/agent`，仅允许 `ucp_request`/`ucp_response` 使用 `ucp_` 前缀）、PR `#791`（`identity.access_token` 仅为参与者标识符而非调用方认证凭据，统一使用 `config.business_id`，且 `encrypted-credential` 处理器不暴露 `/tokenize` 或 `/detokenize`）、PR `#789`（阻断在页面加载、重定向或预填自动提交时静默合并购物永久链接至已登录买家购物车的 CSRF 漏洞，必须取得买家对渲染状态的显式操作）与 PR `#785`（`sign_rest_request` 必须同时覆盖 `"signature-agent";key="<label>"`、`"ucp-agent"` 及非空 `body_bytes` 的摘要头）。
  2. **Agentic Commerce Protocol (`agentic-commerce-protocol/agentic-commerce-protocol`)**：PR `#156`（引入首个加速结账钱包处理器 `com.stripe.link`：买家直接向 Link 邮箱+OTP 认证并返回钱包令牌，Agent 经 `delegate_payment` 换取 `vt_...`/`spt_...` 令牌，全程零原始卡号/CVC 暴露）、PR `#150`（新增 `redirect`、`webview`、`otp` 三类钱包认证干预能力及 `InterventionContext`/`InterventionResponse`）、PR `#144`（补全全部 11 种 `CheckoutSessionBase.status` 状态定义，拦截 `complete_in_progress` 期间重复 `complete` 调用并锁定终态不可变）、PR `#166`（链上持仓资格单次折扣 `duration="once"`、30 分钟 TTL 与行级 `allocations[]` 守恒）与 PR `#151`（取消结账 `intent_trace` 的 10 种标准原因码）。
  3. **Google Agent Payments Protocol (`google-agentic-commerce/AP2`)**：PR `#252`（解决 `#207` 多商户独立 `BudgetEvaluator` 并发超支 `$120 > $100` 漏洞，通过支持 `authorize`、`commit`、`refund`、`query` 的外部原子预算权威在支付前冻结额度）、PR `#228`（Solana Pay 在场 USDC 结算：每次结账嵌入单次只读 `reference` 公钥并链上核验 `recipient`、`amount`、`spl_mint` 与签名 `PaymentMandate` 一致）与 PR `#229`（`ap2haggle/ap2/extensions/haggle/v0.1` 多轮议价扩展：拦截未签名中间 `Offer` 直接用于支付授权，校验轮次上限与底线约束，并要求 `NegotiationOutcome` 携带商户签名 `CartMandate`）。
  4. **Sierra $\tau$-bench 2.0 (`sierra-research/tau2-bench`)**：PR `#580`（修复 `#499`：当参考轨迹中的状态变更工具［如 retail 任务 `64` 与 `105`］重放抛错导致黄金 DB 未建成时，撤回虚假的 `db_match=True` 认证并设为 `db_check=None`）、PR `#581`（修复 `#554`：当 NL 裁判返回的裁决数与断言数不一致时抛错重试，阻断 `all([]) == True` 对空结果误判满分）、PR `#584`（修复 `#553`：在构建 NL 裁判提示词时过滤 `content=None` 的纯工具调用轮次，消除占零售轨迹 `19.9%` 的 `"assistant: None"` 噪音）、PR `#593`（修复 `#556`：独立持久化占真实总成本 `32.8%` 的 `evaluator_cost` 与 `evaluator_usage`）、PR `#600`（修正 2,285 个电信任务的用户模拟器工具锚定为 `check_status_bar`）与 PR `#588`（沙箱命令超时先发 `SIGTERM` 清理两个 `socat` 代理进程再发 `SIGKILL`）。
- **新增代码与双语文档资产**：
  - 护栏模块：[`lab/ucp_service_schema_acp_link_intervention_ap2_budget_tau2_nl_guard.py`](../../lab/ucp_service_schema_acp_link_intervention_ap2_budget_tau2_nl_guard.py)
  - 单元测试：[`tests/test_ucp_service_schema_acp_link_intervention_ap2_budget_tau2_nl_guard.py`](../../tests/test_ucp_service_schema_acp_link_intervention_ap2_budget_tau2_nl_guard.py)（全仓库 **361/361** 单测通过）
  - 双语架构章节：[`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md` (§63)](2026-10-18-agentic-commerce-full-stack-architecture.md) ⇄ [`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.en.md`](2026-10-18-agentic-commerce-full-stack-architecture.en.md)

---

## Stage 65：16 场景中英双语 7-Card 4:5 基准评测报告（`SL-01..SL-16`：UCP 服务 `schema` 多态与永久链接防 CSRF 合并、ACP Stripe Link 钱包与 11 态结账、AP2 跨商户预算权威与 `AP2-Haggle`、Sierra $\tau$-bench 2.0 残缺黄金 DB 状态撤回认证与 NL 裁判门禁）

- **16 场景确定性基准评测（`SL-01..SL-16`）**：
  - `SL-01..SL-04`：UCP `#833` 服务 `schema` 传输定义多态（`rest` OpenAPI 3.1 vs `mcp`/`embedded` OpenRPC 1.3.2）、`#831` `W007` `$defs/agent` 命名规范、`#791` `identity.access_token` 禁充当调用方认证、`#789` 永久链接合并显式买家确认与 `#785` WBA `signature-agent` 签名覆盖。
  - `SL-05..SL-08`：ACP `#156` Stripe Link（`com.stripe.link`）邮箱+OTP 钱包委托与原始卡号 PAN/CVC 隔离、`#150` 钱包认证干预流（`redirect`/`webview`/`otp`）、`#144` `complete_in_progress` 并发阻断与 11 态会话生命周期、`#166` 链上持币单次折扣分摊守恒与 `#151` `intent_trace.reason_code`。
  - `SL-09..SL-12`：Google AP2 `#252` 跨商户原子预算权威（防多 Agent 并发超支 `$120 > $100`）、`#228` Solana Pay 单次只读 `reference` 公钥绑定与 `#229` `AP2-Haggle` 实时多轮议价及商户签名 `CartMandate`。
  - `SL-13..SL-16`：Sierra $\tau$-bench 2.0 `#580` 礼品卡余额不足重放异常撤回黄金 DB 认证（`db_check=None`）、`#581` NL 裁判空结果假满分拦截、`#584` 过滤 `"assistant: None"` 空轮次、`#593` `evaluator_cost` 独立持久化、`#600` `check_status_bar` 接地与 `#588` 沙箱 `SIGTERM` 清理。
- **量化评测结果**：
  - **AI-Native 6-Plane 架构**：**16/16 (100.0%)** 场景准确率，逆序扰动稳定性 **100.0%**，中位延迟 **0.34 ms**。
  - **经典三层架构基线（Classic 3-Tier）**：**4/16 (25.0%)** 场景准确率，中位延迟 **4.63 ms**（AI-Native 提速 **13.6x**）。
- **新增代码与双语报告资产**：
  - 基准生成器：[`lab/ucp_service_schema_acp_link_intervention_ap2_budget_tau2_nl_bench.py`](../../lab/ucp_service_schema_acp_link_intervention_ap2_budget_tau2_nl_bench.py)
  - 单元测试：[`tests/test_ucp_service_schema_acp_link_intervention_ap2_budget_tau2_nl_bench.py`](../../tests/test_ucp_service_schema_acp_link_intervention_ap2_budget_tau2_nl_bench.py)（全仓库 **363/363** 单测通过）
  - 双语 7-Card 4:5 报告：[`reports/agentic-commerce-ucp-service-schema-acp-link-intervention-ap2-budget-tau2-nl-bench/index.html`（中文）](../../reports/agentic-commerce-ucp-service-schema-acp-link-intervention-ap2-budget-tau2-nl-bench/index.html) ⇄ [`index.en.html`（English）](../../reports/agentic-commerce-ucp-service-schema-acp-link-intervention-ap2-budget-tau2-nl-bench/index.en.html) ⇄ [`report.json`](../../reports/agentic-commerce-ucp-service-schema-acp-link-intervention-ap2-budget-tau2-nl-bench/report.json)

---

## Stage 66：UCP 永久链接 `ucp/version` 控制参数（`#793`）与 `TokenCredential` 上下文透传 / 状态绑定 Cart `Offer` / 购物车终态 / OpenAPI `securitySchemes`（`#792`/`#773`/`#740`/`#730`/`#719`/`#716`）、ACP `session_context` 遥测统一（`#238`）与 `app_links` 内嵌深链 / 结账后订单 3 字段守恒 / 卖家侧托管支付（`#237`/`#232`/`#149`/`#114`/`#111`）、Google AP2 `(type, id)` 支付工具二元组匹配（`#301`）与 `delegate-SD-JWT` 黄金向量 / TypeScript-Zod 收据 `oneOf` 必填项（`#307`/`#305`/`#216`）、以及 Sierra $\tau$-bench 2.0 `###OUT-OF-SCOPE###` 中止归类（`#548`）与代码块 JSON 解析 / 检查点延迟删除 / 97 个银行任务同步（`#562`/`#533`/`#606`/`#602`/`#596`）（中英双语）

- **一手协议与上游代码审计**：
  1. **Universal Commerce Protocol (`Universal-Commerce-Protocol/ucp`)**：PR `#793`（携带 UCP 字段路径查询参数的购物永久链接必须包含唯一 `ucp/version=YYYY-MM-DD` 控制参数、严禁预发布标识符、解析后消费控制参数禁泄漏至重定向 URL，且浏览器导航严禁返回 JSON `version_unsupported` 错误）、PR `#792`（在 `TokenCredential` 中透传可选 `binding` 与 `identity` 上下文，处理器比对签发记录且严禁将 `identity` 当作调用方认证）、PR `#773`（在 Cart `actions` 映射中表达状态绑定 `Offer`、禁平行 `offers.available[]` 数组，并绑定 `applies_to.cart_id` + `applies_to.state_ref` 与不可变 `revision`）、PR `#740`（新增不可变购物车终态 `ordered`/`canceled`/`expired`）、PR `#730`（`action.ready` 成功分支 `maxProperties: 0` 仅接受 `{}`）、PR `#719`（`com.mercadopago.shopping.digital_delivery` 挂载于持久化 `Order` 且仅存 `reference` + `lookup` 指针、禁缓存可变余额且交付不等于资金结算）与 PR `#716`（OpenAPI 3.1 通过 `components.securitySchemes` 声明认证并移除被规范忽略的 `Authorization`/`Accept`/`Content-Type`/`X-API-Key` 请求头参数）。
  2. **Agentic Commerce Protocol (`agentic-commerce-protocol/agentic-commerce-protocol`)**：PR `#238`（将原始买家/设备遥测对象统一命名为 `session_context` 并消除与 `delegate_payment.risk_signals` 标准化欺诈评估数组的命名冲突）、PR `#237`（`Product`/`Variant` 优先级 `app_links` 原生/内嵌应用深链及向规范 `url` 的安全回退）、PR `#232`（结账后订单 3 字段数量守恒 `ordered == fulfilled + canceled`、`returned <= fulfilled` 及订单级 `completed` 状态去重载）以及 PR `#149`/`#114`/`#111`（`content_attribution` 引用 URL 归因、`dev.acp.seller_backed.*` 卖家侧托管支付免原始凭证传输与积分余额校验，以及 `x402` 加密货币 Facilitator 验签结算）。
  3. **Google Agent Payments Protocol (`google-agentic-commerce/AP2`)**：PR `#301`（`AllowedPaymentInstrumentEvaluator` 必须同时匹配 `(type, id)` 二元组，阻断同 `id="pi-1"` 但不同 `type="bank" != "card"` 的支付工具越权通过）、PR `#307`（固化 4 组 `delegate_sd_jwt_vectors.json` 黄金向量的线格式不变量：$N$ 段委托链必含 $N-1$ 个 `~~` 分隔符、以 `~` 结尾且通过 JWS 验签）、PR `#305`（`@ap2-protocol/sdk` TypeScript/Zod 收据根级 `oneOf` 分支必填项保留）与 PR `#216`（`ghost-protocol` Base 主网 `8453` EIP-712 非托管自治基础设施 `IntentMandate` 月度 USDC 限额门禁）。
  4. **Sierra $\tau$-bench 2.0 (`sierra-research/tau2-bench`)**：PR `#548`（在 `initialize()`、`step()` 与 `_process_participant` 中将用户模拟器 `###OUT-OF-SCOPE###` 优先于 `###STOP###` 归类为 `TerminationReason.OUT_OF_SCOPE` 并按规则 5 判 `0.0` 分）、PR `#562`（NL 断言评估器通过 `extract_json_from_llm_response` 解析 Markdown 代码块包裹的 JSON 并对损坏 JSON 保持抛错）、PR `#533`（目录格式检查点替换时延迟至新轨迹写入并 `os.replace` 成功后才删除旧轨迹与索引）及 PR `#606`/`#602`/`#596`（同步 `banking_knowledge/tasks.json` 全部 97 个聚合任务定义并补齐任务 `102` 缺失的 `NL_ASSERTION`、强制航空域 `user_id` 全小写、以及校验中国高校教务双控域 `campus` 的 `v1.0.1` `[DB, COMMUNICATE]` + `env_assertions` 评分基线）。
- **新增代码与双语文档资产**：
  - 护栏模块：[`lab/ucp_token_context_cart_offer_acp_telemetry_ap2_instrument_tau2_abort_guard.py`](../../lab/ucp_token_context_cart_offer_acp_telemetry_ap2_instrument_tau2_abort_guard.py)
  - 单元测试：[`tests/test_ucp_token_context_cart_offer_acp_telemetry_ap2_instrument_tau2_abort_guard.py`](../../tests/test_ucp_token_context_cart_offer_acp_telemetry_ap2_instrument_tau2_abort_guard.py)（全仓库 **371/371** 单测通过）
  - 双语架构章节：[`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md` (§65)](2026-10-18-agentic-commerce-full-stack-architecture.md) ⇄ [`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.en.md`](2026-10-18-agentic-commerce-full-stack-architecture.en.md)

---

## Stage 67：16 场景中英双语 7-Card 4:5 基准评测报告（`TO-01..TO-16`：UCP 永久链接 `ucp/version` 与状态绑定 Cart `Offer`、ACP `session_context` 遥测与 3 字段订单守恒、AP2 `(type, id)` 支付工具二元组匹配与 `~~` 黄金向量、Sierra $\tau$-bench 2.0 `###OUT-OF-SCOPE###` 中止归类与 97 任务同步）

- **16 场景确定性基准评测（`TO-01..TO-16`）**：
  - `TO-01..TO-04`：UCP `#793` 永久链接 `ucp/version=YYYY-MM-DD` 控制参数消费与重定向脱敏、`#792` `TokenCredential.binding` 透传与 `identity` 禁充当认证、`#773` Cart `actions` 状态绑定 `Offer`（禁平行 `offers.available[]`）、`#740` 购物车 `ordered` 终态不可变、`#730` `action.ready` `maxProperties: 0`、`#719` `digital_delivery` 指针与 `#716` OpenAPI 3.1 `securitySchemes`。
  - `TO-05..TO-08`：ACP `#238` `session_context` 遥测对象与 `delegate_payment.risk_signals` 欺诈评估数组分离、`#237` `app_links` 优先级深链与 `Product.url` 回退、`#232` 结账后订单 3 字段数量守恒（`ordered == fulfilled + canceled`）与 `completed` 状态，以及 `#149`/`#114`/`#111` `content_attribution`、卖家侧托管支付积分余额校验与 `x402` 加密货币 Facilitator 验签。
  - `TO-09..TO-12`：Google AP2 `#301` `AllowedPaymentInstrumentEvaluator` `(type, id)` 二元组匹配（拦截同 `id="pi-1"` 不同 `type="bank" != "card"`）、`#307` `delegate-SD-JWT` 黄金向量 $N-1$ 个 `~~` 分隔符与尾部 `~`、`#305` `@ap2-protocol/sdk` 收据根级 `oneOf` 分支必填项与 `#216` `ghost-protocol` Base `8453` 月度限额。
  - `TO-13..TO-16`：Sierra $\tau$-bench 2.0 `#548` `###OUT-OF-SCOPE###` 优先于 `###STOP###` 归类为 `OUT_OF_SCOPE` 并判 `0.0` 分、`#562` NL 裁判代码块 JSON 解析与损坏 JSON 抛错、`#533` 目录检查点先写后删原子替换与 `#606`/`#602`/`#596` 银行 97 任务同步（含任务 `102` `NL_ASSERTION`）、小写航空 `user_id` 及 `campus` 双控域 `v1.0.1` 评分。
- **量化评测结果**：
  - **AI-Native 6-Plane 架构**：**16/16 (100.0%)** 场景准确率，逆序扰动稳定性 **100.0%**，中位延迟 **0.34 ms**。
  - **经典三层架构基线（Classic 3-Tier）**：**4/16 (25.0%)** 场景准确率，中位延迟 **4.63 ms**（AI-Native 提速 **13.6x**）。
- **新增代码与双语报告资产**：
  - 基准生成器：[`lab/ucp_token_context_cart_offer_acp_telemetry_ap2_instrument_tau2_abort_bench.py`](../../lab/ucp_token_context_cart_offer_acp_telemetry_ap2_instrument_tau2_abort_bench.py)
  - 单元测试：[`tests/test_ucp_token_context_cart_offer_acp_telemetry_ap2_instrument_tau2_abort_bench.py`](../../tests/test_ucp_token_context_cart_offer_acp_telemetry_ap2_instrument_tau2_abort_bench.py)（全仓库 **373/373** 单测通过）
  - 双语 7-Card 4:5 报告：[`reports/agentic-commerce-ucp-token-context-cart-offer-acp-telemetry-ap2-instrument-tau2-abort-bench/index.html`（中文）](../../reports/agentic-commerce-ucp-token-context-cart-offer-acp-telemetry-ap2-instrument-tau2-abort-bench/index.html) ⇄ [`index.en.html`（English）](../../reports/agentic-commerce-ucp-token-context-cart-offer-acp-telemetry-ap2-instrument-tau2-abort-bench/index.en.html) ⇄ [`report.json`](../../reports/agentic-commerce-ucp-token-context-cart-offer-acp-telemetry-ap2-instrument-tau2-abort-bench/report.json)

---

## Stage 68：UCP OpenRPC 内嵌认证 `type` 必填与目录折扣预览/通用 SPT/`price_treatment`/`event_feed`、ACP Feed API 与 `suggested_price` 溯源/完成阶段 `fulfillment_details`/营销授权/Razorpay & `Cart`、Google AP2 HNP 授权绑定与字符串金额/`IntentMandate.budget`/FCB 熔断器、以及 Sierra $\tau$-bench 2.0 语音口语与分片金额识别/动作并集与配对排序护栏

- **一手协议与基准源审计（22 个新 PR/规范）**：
  - **UCP (`Universal-Commerce-Protocol/ucp`)**：PR `#802`（修复 `#787`：OpenRPC `ec.auth` 与 `ep.cart.auth` 描述符中 `type` 参数必须标记 `"required": true` 且运行时请求必须携带非空 `type`）、PR `#715`（`dev.ucp.shopping.discount` 扩展至目录查询 `get_product` 响应开放 `discounts.available[]` 预览并保持 Cart/Checkout 对折扣核销的唯一权威，严禁目录响应返回 `discounts.applied[]`）、PR `#713`（`dev.ucp.payment.shared_payment_token` 通用共享支付令牌处理器要求短生命周期与商户作用域绑定，严禁暴露原始 PAN/CVC/网络令牌）、PR `#691`（`price_treatment.tax.inclusion` 标记含税/不含税/不适用并阻断对 `included` 含税价重复加税）、PR `#673`（业务画像 `event_feed` 与履约事件非规范性建议 `agent_hints[]` 严禁越权自动执行财务变更）以及 PR `#669`/`#661`（`actions` 映射 `minProperties: 1` 非空约束与 `policy.applies_to` `minItems: 1` 及 `$.products[?@.tags[?@=='...']]` 集合匹配路径）。
  - **ACP (`agentic-commerce-protocol/agentic-commerce-protocol`)**：PR `#255`/`#190`/`#192`（`UpsertProductsResponse` 严格 `{"id": str, "accepted": bool}` 结构与推送式商品/促销流时间窗校验）、PR `#201`（`SEP #197`：创建结账会话 `Item.suggested_price` 必须携带 `PriceSource.feed_id` 溯源与 `observed_at`）、PR `#200`（`SEP #196`：结账完成请求携带 `fulfillment_details` 时卖家必须在扣款前先应用联系信息更新）、PR `#199`（`SEP #195`：营销授权选项 HTTPS 隐私政策链接与提交渠道白名单校验）以及 PR `#215`/`#213`/`#188`（`razorpay` PSP 与 `in.razorpay.upi` 委托支付/免 PCI 属性及结账前 `Cart` 能力禁止提前触发支付处理器协商）。
  - **Google AP2 (`google-agentic-commerce/AP2`)**：PR `#191`（`PaymentCurrencyAmount.value` 必须对齐 W3C Payment Request API `DOMString` 字符串类型，阻断浮点数传入）、PR `#198`（`Closes #133`：`IntentMandate.budget` 机器可读支出上限强校验）、PR `#202`/`#189`（HNP 用户不在场模式下强制校验 `IntentMandate.user_authorization` 用户签名 JWT 与 `PaymentMandate` 的 `intent_mandate_id` + `intent_mandate_hash` 跨授权书哈希绑定）、PR `#187`/`#164`（Section 7.4 结构化风险信号 `RiskPayload` 与受托熔断器 `FCBState.OPEN` / `TRIPPED` 实时阻断自主执行）及 PR `#139`（UPI Collect 三段式请求信封 `transaction_data`、`cred_block`、`device_fingerprint`）。
  - **Sierra $\tau$-bench 2.0 (`sierra-research/tau2-bench`)**：PR `#582`（语音通信评估器支持识别英语口语金额如 `"five thousand two hundred forty four"` $\rightarrow$ `"5244"` 并重组跨流式分片数字）、PR `#575`（`analyze_reward()` 对 `reward_basis` 声明但 `reward_breakdown` 缺失的组件使用 `.get()` 安全读取，消除 `KeyError` 崩溃）、PR `#573`（`evaluate-trajs` 显式统计并上报 `replay_mismatches` 轨迹重放分歧数并支持 `--strict-replay`）、PR `#569`/`#570`（`Action.compare_with_tool_call` 比较双方参数键并集并对同长度标量列表如 `item_ids`/`new_item_ids` 按行配对排序）及 PR `#571`/`#567`/`#566`（零售域参考动作礼品卡余额充足性与 `delivered` 已交付订单换货前置校验）。
- **新增代码与双语文档资产**：
  - 护栏模块：[`lab/ucp_openrpc_auth_acp_feed_consent_ap2_hnp_fcb_tau2_voice_guard.py`](../../lab/ucp_openrpc_auth_acp_feed_consent_ap2_hnp_fcb_tau2_voice_guard.py)
  - 单元测试：[`tests/test_ucp_openrpc_auth_acp_feed_consent_ap2_hnp_fcb_tau2_voice_guard.py`](../../tests/test_ucp_openrpc_auth_acp_feed_consent_ap2_hnp_fcb_tau2_voice_guard.py)（全仓库 **382/382** 单测通过）
  - 双语架构章节：[`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md` (§67)](2026-10-18-agentic-commerce-full-stack-architecture.md) ⇄ [`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.en.md`](2026-10-18-agentic-commerce-full-stack-architecture.en.md)

---

## Stage 69：16 场景中英双语 7-Card 4:5 基准评测报告（`OA-01..OA-16`：UCP OpenRPC 鉴权与目录折扣预览/SPT/`price_treatment`、ACP Feed Upsert 与优先履约/营销授权/Razorpay、AP2 HNP 意图哈希绑定与 `DOMString` 金额/受托熔断器、Sierra $\tau$-bench 2.0 语音金额与成对列表匹配）

- **16 场景确定性基准评测（`OA-01..OA-16`）**：
  - `OA-01..OA-04`：UCP `#802` OpenRPC `ec.auth` / `ep.cart.auth` `type` 参数 `"required": true`、`#715` `get_product` 仅允许返回 `discounts.available[]` 预览（阻断 `discounts.applied[]`）、`#713` `dev.ucp.payment.shared_payment_token` 阻断明文 PAN/CVC 泄露、`#691` `price_treatment.tax.inclusion="included"` 防重复加税、`#673` `event_feed` 与 `agent_hints[]` 非强制提示及 `#669`/`#661` `actions` / `policy.applies_to` 非空校验。
  - `OA-05..OA-08`：ACP `#255`/`#190`/`#192` `UpsertProductsResponse` `additionalProperties: false` 与促销流、`#201` `Item.suggested_price` 强制 `PriceSource.feed_id` 溯源、`#200` `CheckoutSessionCompleteRequest.fulfillment_details` 先于支付处理应用、`#199` HTTPS `privacy_policy_url` 与勾选营销渠道校验及 `#215`/`#213`/`#188` `in.razorpay.upi` 与预结账 `Cart` 隔离。
  - `OA-09..OA-12`：Google AP2 `#191` `PaymentCurrencyAmount.value` `DOMString` 字符串类型、`#198` `IntentMandate.budget` 支出上限、`#202`/`#189` `human_not_present` `user_authorization` 与 `signed_intent_mandate_hash` 绑定、`#187`/`#164` Section 7.4 `RiskPayload` 与受托熔断器 `FCBState.OPEN` / `TRIPPED` 阻断及 `#139` UPI Collect 三段式请求信封。
  - `OA-13..OA-16`：Sierra $\tau$-bench 2.0 `#582` 英语单词金额 `"five thousand two hundred forty four"` $\rightarrow$ `"5244"` 与跨分片重组、`#575` `analyze_reward()` 对缺失组件的安全 `.get()` 查找、`#573` `evaluate-trajs` `replay_mismatches` 追踪、`#569`/`#570` `Action.compare_with_tool_call` 参数键并集与成对标量列表按行对齐排序及 `#571`/`#567`/`#566` 零售礼品卡余额与已交付订单换货校验。
- **量化评测结果**：
  - **AI-Native 6-Plane 架构**：**16/16 (100.0%)** 场景准确率，逆序扰动稳定性 **100.0%**，中位延迟 **0.34 ms**。
  - **经典三层架构基线（Classic 3-Tier）**：**4/16 (25.0%)** 场景准确率，中位延迟 **4.63 ms**（AI-Native 提速 **13.6x**）。
- **新增代码与双语报告资产**：
  - 基准生成器：[`lab/ucp_openrpc_auth_acp_feed_consent_ap2_hnp_fcb_tau2_voice_bench.py`](../../lab/ucp_openrpc_auth_acp_feed_consent_ap2_hnp_fcb_tau2_voice_bench.py)
  - 单元测试：[`tests/test_ucp_openrpc_auth_acp_feed_consent_ap2_hnp_fcb_tau2_voice_bench.py`](../../tests/test_ucp_openrpc_auth_acp_feed_consent_ap2_hnp_fcb_tau2_voice_bench.py)（全仓库 **384/384** 单测通过）
  - 双语 7-Card 4:5 报告：[`reports/agentic-commerce-ucp-openrpc-auth-acp-feed-consent-ap2-hnp-fcb-tau2-voice-bench/index.html`（中文）](../../reports/agentic-commerce-ucp-openrpc-auth-acp-feed-consent-ap2-hnp-fcb-tau2-voice-bench/index.html) ⇄ [`index.en.html`（English）](../../reports/agentic-commerce-ucp-openrpc-auth-acp-feed-consent-ap2-hnp-fcb-tau2-voice-bench/index.en.html) ⇄ [`report.json`](../../reports/agentic-commerce-ucp-openrpc-auth-acp-feed-consent-ap2-hnp-fcb-tau2-voice-bench/report.json)

---

## Stage 70：UCP 订单 Webhook 签名门禁与保留 `ucp` 命名空间/`map_order`/`request_constraints`/销售基准步数、ACP `protocol.extensions` 与逐行限时报价 `valid_until`/`Merchant-Signature` 防重放/11 种会话状态/MCP 绑定、Google AP2 `FailureResponse` 与 `PaymentReceipt`/Verifiable Intent/微支付状态通道、以及 Sierra $\tau$-bench 2.0 OpenAI Live 打断信号与结果安全重试/Pydantic 强转/`llm_agent_solo_gt` 重放/`pass^k` 分母护栏

- **一手协议与基准源审计（32 个新 PR/规范）**：
  - **UCP (`Universal-Commerce-Protocol/ucp`)**：PR `#659`（将 `webhook-id` 与 `webhook-timestamp` 纳入 RFC 9421 闭集必签门禁并禁止订单 Webhook JSON 正文残留 `event_id`/`created_time`）、PR `#658`/`#657`（`ucp.capabilities` 必须为携带 `schema` URL 的字典映射；在所有结构化对象作用域保留 `ucp` 命名空间并纳入 AP2 `merchant_authorization` JCS 签名覆盖，新增仅限响应携带的 `ucp.map_order`）、PR `#655`/`#626`（响应携带的 `ucp.request_constraints` 请求约束语法及可用支付工具必填 RFC 9535 JSONPath `path`）、PR `#653`（整数步数 `quantity` 与 `quantity_unit` `10^-scale` 销售基准算术）及 PR `#642`/`#622`/`#596`（`context.location` 优先级、MCP `-32004` `rate_limit_exceeded` 与反滥用信号）。
  - **ACP (`agentic-commerce-protocol/agentic-commerce-protocol`)**：PR `#178`（将扩展声明从 `capabilities.extensions` 迁移至 `protocol.extensions`）、PR `#165`（`SEP #164`：逐行商品限时报价 `valid_until` 与 `offer_valid`/`offer_expired` 状态独立于会话级 `quote_expires_at` 校验）、PR `#160`（Stripe 对齐的 `Merchant-Signature: t=<unix_seconds>,v1=<64_hex>` HMAC-SHA256 签名与 300 秒防重放窗口）、PR `#144`/`#162`/`#161`（完整 11 种结账会话状态、数字商品履约禁标 `shipped`、委托支付 401/500/503 错误枚举）及 PR `#139`/`#130`/`#125`（5 个 MCP 结账工具绑定要求 `arguments.meta.api_version` 与 `arguments.payload`）。
  - **Google AP2 (`google-agentic-commerce/AP2`)**：PR `#131`/`#132`（`ap2.errors.FailureResponse` 错误分类与恢复动作映射，在要求 `USER_CONFIRMATION_REQUIRED` 或 `NEW_MANDATE_REQUIRED` 时阻断智能体静默重试）、PR `#110`/`#128`/`#92`（Section 7.1 `PaymentReceipt` 对 `artifacts is None` 的空安全提取、跨语言 Mandate JSON Schema `$schema`/`$id` 校验与 PCI/SOX/GDPR 审计日志脱敏）以及 PR `#144`/`#83`（Verifiable Intent 三跳 SD-JWT 委托链故障闭合验签与微支付状态通道累计存款上限及单调递增序号防重放）。
  - **Sierra $\tau$-bench 2.0 (`sierra-research/tau2-bench`)**：PR `#528`（OpenAI Live `session.input_transcript.delta` 映射为 `speech_started=True` 且不误置 `was_truncated=True`）、PR `#520`（全双工幻觉重试结果安全：校验 `hallucinations` 为列表、对最终重试执行评审、仅写入选中轨迹并保留完整工具结果）、PR `#516`/`#513`（在工具调用前通过 Pydantic 将浮点编码整数 `5.0 -> 5` 强制转换以防止黄金 DB 哈希漂移）、PR `#508`（重放评分时识别 `"llm_agent_solo_gt"` 为 Solo 模式以加载 `TelecomUserTools`）、PR `#498`（按 `.value` 过滤基础设施错误并在 `pass^k` 分母中保留全故障任务记 `0` 分）以及 PR `#484`（`close_bank_account_7392` 关户原因固定枚举校验以防自由文本污染 DB 哈希）。
- **新增代码与双语文档资产**：
  - 护栏模块：[`lab/ucp_webhook_signing_acp_session_states_ap2_failure_micropay_tau2_solo_guard.py`](../../lab/ucp_webhook_signing_acp_session_states_ap2_failure_micropay_tau2_solo_guard.py)
  - 单元测试：[`tests/test_ucp_webhook_signing_acp_session_states_ap2_failure_micropay_tau2_solo_guard.py`](../../tests/test_ucp_webhook_signing_acp_session_states_ap2_failure_micropay_tau2_solo_guard.py)（全仓库 **392/392** 单测通过）
  - 双语架构章节：[`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md` (§69)](2026-10-18-agentic-commerce-full-stack-architecture.md) ⇄ [`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.en.md`](2026-10-18-agentic-commerce-full-stack-architecture.en.md)

---

## Stage 71：UCP Webhook 签名门禁/约束、ACP 限时报价 `valid_until`/`Merchant-Signature`、Google AP2 `FailureResponse`/微支付通道 与 Sierra $\tau$-bench 2.0 Live 打断/Solo 重放 16 场景（`WS-01..WS-16`）中英双语 7-Card 4:5 视觉基准报告

- **评测范围（16 场景，`WS-01..WS-16`）**：
  - `WS-01..WS-04`：UCP 订单 Webhook 签名门禁（`#659`）、保留 `ucp` 命名空间与 `map_order`（`#658`/`#657`）、响应携带 `request_constraints`（`#655`/`#626`）及整数步数销售基准（`#653`）。
  - `WS-05..WS-08`：ACP `protocol.extensions`（`#178`）、逐行限时报价 `valid_until`（`#165`）、`Merchant-Signature` 防重放（`#160`）、数字商品禁标 `shipped`（`#162`）与 MCP 结账工具绑定（`#139`）。
  - `WS-09..WS-12`：Google AP2 `FailureResponse` 恢复动作强制映射（`#131`/`#132`）、`PaymentReceipt` 空安全与审计日志脱敏（`#110`/`#92`）、三跳 Verifiable Intent（`#144`）与微支付状态通道防透支（`#83`）。
  - `WS-13..WS-16`：Sierra $\tau$-bench 2.0 OpenAI Live 打断信号（`#528`）、结果安全幻觉重试（`#520`）、Pydantic 浮点强转（`#516`）、`llm_agent_solo_gt` 重放（`#508`）、`pass^k` 分母保真（`#498`）与固定关户原因枚举（`#484`）。
- **核心量化发现**：
  - **准确率**：AI-Native 确定性护栏 **16/16 (100.0%)** vs. 经典三层架构基线 **4/16 (25.0%)**。
  - **扰动鲁棒性**：选项逆序与字段乱序下 **100.0% (0.0 pts 漂移)**。
  - **延迟对比**：单轮中位延迟 **0.34 ms vs. 4.62 ms（13.6x 加速）**。
- **新增代码与双语报告资产**：
  - 基准生成器：[`lab/ucp_webhook_signing_acp_session_states_ap2_failure_micropay_tau2_solo_bench.py`](../../lab/ucp_webhook_signing_acp_session_states_ap2_failure_micropay_tau2_solo_bench.py)
  - 单元测试：[`tests/test_ucp_webhook_signing_acp_session_states_ap2_failure_micropay_tau2_solo_bench.py`](../../tests/test_ucp_webhook_signing_acp_session_states_ap2_failure_micropay_tau2_solo_bench.py)（全仓库 **394/394** 单测通过）
  - 双语 7-Card 4:5 报告：[`reports/agentic-commerce-ucp-webhook-signing-acp-session-states-ap2-failure-micropay-tau2-solo-bench/index.html`（中文）](../../reports/agentic-commerce-ucp-webhook-signing-acp-session-states-ap2-failure-micropay-tau2-solo-bench/index.html) ⇄ [`index.en.html`（English）](../../reports/agentic-commerce-ucp-webhook-signing-acp-session-states-ap2-failure-micropay-tau2-solo-bench/index.en.html) ⇄ [`report.json`](../../reports/agentic-commerce-ucp-webhook-signing-acp-session-states-ap2-failure-micropay-tau2-solo-bench/report.json)

---

## Stage 72：UCP `buyer.consent` 全量替换豁免与退货政策扩展/`ETag` 条件写/`P-521` 密钥配对、ACP 周期性委托额度与仅写联盟归因/取消意图追踪/3DS `channel` 移除、Google AP2 `AP2-Haggle` 实时议价与 Solana/Algorand 链上授权绑定/凭据脱敏、以及 Sierra $\tau$-bench 2.0 银行读日志白名单与多商品改单独立变体计价/VPN 深拷贝/重放幻觉容错护栏

- **一手协议与基准源审计（24 个新 PR/规范）**：
  - **UCP (`Universal-Commerce-Protocol/ucp`)**：PR `#660`（`buyer.consent` 豁免于购物车与结账的全量替换规则：更新请求省略 `buyer.consent` 时必须保留买家既有同意/拒收偏好而非重置为默认勾选）、PR `#634`（新增 `dev.ucp.shopping.policy.return` 结构化退货政策扩展：`final_sale: true` 时严禁携带 `window`/`supported_resolutions`/`methods`/`restocking_fee`；`window` 必须同时包含正整数 `days` 与显式 `anchor`；未声明费用严禁按免费展示）、PR `#628`（结账写操作支持 RFC 9110 `ETag` / `If-Match` 乐观并发控制，失配返回 `412 Precondition Failed`、缺失必填头返回 `428 Precondition Required`）、PR `#627`/`#625`（权威绑定兼容 `name == authority_prefix` 精确匹配，`profile.json` 中 `crv: "P-521"` 仅允许配对 `alg: "ES512"`）以及 PR `#617`/`#605`（履约事件关联送达时间窗与库存信号）。
  - **ACP (`agentic-commerce-protocol/agentic-commerce-protocol`)**：PR `#85`/`#80`（从 3DS `AuthenticationMetadata` 移除废弃 `channel` 字段，`PaymentProvider` 新增必填 `merchant_id` 与 `authentication_provider`）、PR `#73`（`SEP #12`：委托支付 `Allowance.reason` 扩展 `"recurring"` 与 `"subscription"`，要求必填 `billing_cycle` 与 `amount_per_cycle`）、PR `#57`（`SEP` 联盟归因 `affiliate_attribution` 仅写不读严禁在查询/Webhook 回显，并执行幂等冲突 `409` 与禁传 PII）及 PR `#54`/`#45`（结账取消 `intent_trace` 扁平标量 `metadata` 与酒店垂直域 `quote_token` 边界重核验）。
  - **Google AP2 (`google-agentic-commerce/AP2`)**：PR `#229`（`AP2-Haggle` 多轮实时议价扩展：中间 `Offer` 不签名、受最大轮次/买家底价/商户成本底线约束，成交 `NegotiationOutcome` 产出商户签名 `CartMandate`）、PR `#228`/`#218`（Solana Pay 单次 `reference` 公钥绑定与 Algorand USDC ASA `av:{token[:20]}` 备注前缀对 `PaymentMandate` 的链上绑定）及 PR `#212`/`#188`（凭据响应脱敏为不透明 `credential_reference`、校验 `payment_mandate_payer == token_owner` 与 ADK 会话状态 `.model_dump()` 序列化）。
  - **Sierra $\tau$-bench 2.0 (`sierra-research/tau2-bench`)**：PR `#329`（`banking_knowledge` 仅在写操作或命中 `read_log_allowlist` 时记录 `agent_discoverable_tools`，避免知识库额外读调用污染 DB 哈希）、PR `#322`（零售 `modify_pending_order_items` 多商品改单按各自替换变体独立赋价与选项）、PR `#301`（`_connect_vpn()` 对 `default_vpn_details` 执行 `copy.deepcopy` 阻断跨并发仿真状态污染）及 PR `#273`/`#264`（重放时对未知幻觉工具执行空操作跳过并保留交错思考 `raw_data`）。
- **新增代码与双语文档资产**：
  - 护栏模块：[`lab/ucp_consent_return_etag_acp_affiliate_trace_ap2_haggle_solana_tau2_vpn_guard.py`](../../lab/ucp_consent_return_etag_acp_affiliate_trace_ap2_haggle_solana_tau2_vpn_guard.py)
  - 单元测试：[`tests/test_ucp_consent_return_etag_acp_affiliate_trace_ap2_haggle_solana_tau2_vpn_guard.py`](../../tests/test_ucp_consent_return_etag_acp_affiliate_trace_ap2_haggle_solana_tau2_vpn_guard.py)（全仓库 **402/402** 单测通过）
  - 双语架构章节：[`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md` (§71)](2026-10-18-agentic-commerce-full-stack-architecture.md) ⇄ [`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.en.md`](2026-10-18-agentic-commerce-full-stack-architecture.en.md)

---

## Stage 73：UCP 同意持久化/退货政策/ETag、ACP 周期额度/仅写联盟归因/取消追踪、Google AP2 `AP2-Haggle`/Solana/Algorand 与 Sierra $\tau$-bench 2.0 银行读白名单/多商品改单/VPN 深拷贝 16 场景（`CR-01..CR-16`）中英双语 7-Card 4:5 视觉基准报告

- **评测范围（16 场景，`CR-01..CR-16`）**：
  - `CR-01..CR-04`：UCP `buyer.consent` 全量替换豁免（`#660`）、`dev.ucp.shopping.policy.return` 退货政策扩展（`#634`）、`ETag`/`If-Match` 条件写（`#628`）与 `P-521` $\leftrightarrow$ `ES512` 密钥配对（`#625`）。
  - `CR-05..CR-08`：ACP 3DS `AuthenticationMetadata` 移除废弃 `channel`（`#85`）、`subscription` 委托额度 `billing_cycle`/`amount_per_cycle`（`#73`）、仅写联盟归因 `affiliate_attribution` 防泄露（`#57`）与取消追踪 `intent_trace`（`#54`）。
  - `CR-09..CR-12`：Google AP2 `AP2-Haggle` 成交签名 `CartMandate`（`#229`）、Solana Pay 单次 `reference` 与 Algorand `av:{token[:20]}` 链上绑定（`#228`/`#218`）及付款人 `payer == token_owner` 与凭据脱敏（`#212`）。
  - `CR-13..CR-16`：Sierra $\tau$-bench 2.0 `banking_knowledge` 读日志白名单（`#329`）、零售多商品改单独立替换变体计价（`#322`）、电信 `_connect_vpn` `deepcopy` 并发隔离（`#301`）与重放跳过幻觉工具（`#273`）。
- **核心量化发现**：
  - **准确率**：AI-Native 确定性护栏 **16/16 (100.0%)** vs. 经典三层架构基线 **4/16 (25.0%)**。
  - **扰动鲁棒性**：选项逆序与字段乱序下 **100.0% (0.0 pts 漂移)**。
  - **延迟对比**：单轮中位延迟 **0.34 ms vs. 4.63 ms（13.6x 加速）**。
- **新增代码与双语报告资产**：
  - 基准生成器：[`lab/ucp_consent_return_etag_acp_affiliate_trace_ap2_haggle_solana_tau2_vpn_bench.py`](../../lab/ucp_consent_return_etag_acp_affiliate_trace_ap2_haggle_solana_tau2_vpn_bench.py)
  - 单元测试：[`tests/test_ucp_consent_return_etag_acp_affiliate_trace_ap2_haggle_solana_tau2_vpn_bench.py`](../../tests/test_ucp_consent_return_etag_acp_affiliate_trace_ap2_haggle_solana_tau2_vpn_bench.py)（全仓库 **404/404** 单测通过）
  - 双语 7-Card 4:5 报告：[`reports/agentic-commerce-ucp-consent-return-etag-acp-affiliate-trace-ap2-haggle-solana-tau2-vpn-bench/index.html`（中文）](../../reports/agentic-commerce-ucp-consent-return-etag-acp-affiliate-trace-ap2-haggle-solana-tau2-vpn-bench/index.html) ⇄ [`index.en.html`（English）](../../reports/agentic-commerce-ucp-consent-return-etag-acp-affiliate-trace-ap2-haggle-solana-tau2-vpn-bench/index.en.html) ⇄ [`report.json`](../../reports/agentic-commerce-ucp-consent-return-etag-acp-affiliate-trace-ap2-haggle-solana-tau2-vpn-bench/report.json)

---

## Stage 74：UCP 住宿预订能力/跨行业令牌绑定/位置空间关系/约束路径寻址、ACP 强制 POST 幂等与 `/.well-known/acp.json` 发现、Google AP2 RFC 8785 JCS 购物车哈希/KB-SD-JWT 逐跳校验与 Coinbase x402 流克隆、以及 Sierra $\tau$-bench 2.0 Gemini 8kHz 原生电话流与静默 `GoAway` 重连确定性护栏

- **一手协议与基准演进证据**：
  1. **UCP 住宿预订能力与三态取消政策（`#780`）、跨行业令牌绑定与参与方授权分离（`#762`/`#746`）、位置空间关系与自描述设施（`#766`/`#765`/`#753`）及请求约束外层 `path` 寻址（`#757`/`#744`）**：`dev.ucp.lodging.booking` 引入复合住宿绑定 `stays[]`、双层住客池 `guests[]` / `guest_assignments[]` 与三态取消政策 `dev.ucp.lodging.policy.cancellation`；`common/types/binding.json` 将资源绑定收敛为 `{type, id}` 并与调用方 `identity` 授权解耦；Location 将 `distance`/`serves` 移至顶层、以 `filters.items[]` 替代状态库存过滤并要求 `amenities` 携带非空文本描述；Request Constraints 新增仅外层 RFC 9535 `path` 与 `anyOf`。
  2. **ACP 强制 POST 幂等性保证（`#121`）、`/.well-known/acp.json` 发现文档（`#137`）、`sale` 促销扩展与 `discounts.rejected[]`（`#129`/`#123`）及 Schema 类型对齐（`#262`/`#249`/`#214`/`#116`）**：POST 强制 `Idempotency-Key`（定义 `400`/`409`/`422` 错误码与 `Idempotent-Replayed` 响应头），新增免认证 `/.well-known/acp.json`，对齐 `DiscountsResponse.rejected[]`、3DS `frictionless.type == "low_risk"`、`Message*` 严格字段、整数 `Refund.amount`、空 `risk_signals: []` 与 8 位 `iin`。
  3. **Google AP2 RFC 8785 JCS 购物车哈希绑定（`#253`）、KB-SD-JWT 逐跳与终端 `aud`/`nonce` 绑定（`#342`/`#326`/`#313`）、即时支付时间窗与主次预算单位（`#318`/`#340`）及 Coinbase x402 流克隆/多轨 `accepts`/签名器地址校验（`#323`/`#306`/`#297`/`#277`）**：`PaymentMandateContents` 绑定剥离 `null` 后的 JCS `cart_mandate_hash`；KB-SD-JWT 在每一跳与终端跳强校验 `aud`/`nonce`；缺省 `execution_date` 按当前 UTC 时间校验 `[not_before, not_after]`；x402 在 402 探测前克隆 `ReadableStream`、跳过未知 CAIP-2 `accepts[]` 轨道并强校验顶层 `.address`。
  4. **Sierra $\tau$-bench 2.0 Gemini 8kHz 原生电话采样与 `SlidingWindow`（`#544`/`#511`/`#510`/`#509`）、静默 `GoAway` 重连截止时间监控（`#461`）、全双工非阻塞语音生成（`#525`/`#522`）与文本模拟器空回复重试（`#471`）**：默认 8kHz 直传与 `START_SENSITIVITY_HIGH`，服务端静默时主动触发 `GoAway` 重连，非阻塞生成用户语音，并在文本模式模拟器返回空消息时附带 `###STOP###` 提示重试一次。
- **新增代码与双语文档资产**：
  - 护栏模块：[`lab/ucp_lodging_token_binding_acp_idempotency_wellknown_ap2_jcs_sdjwt_x402_tau2_gemini_guard.py`](../../lab/ucp_lodging_token_binding_acp_idempotency_wellknown_ap2_jcs_sdjwt_x402_tau2_gemini_guard.py)
  - 单元测试：[`tests/test_ucp_lodging_token_binding_acp_idempotency_wellknown_ap2_jcs_sdjwt_x402_tau2_gemini_guard.py`](../../tests/test_ucp_lodging_token_binding_acp_idempotency_wellknown_ap2_jcs_sdjwt_x402_tau2_gemini_guard.py)（全仓库 **412/412** 单测通过）
  - 双语架构章节：[`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md` (§73)](2026-10-18-agentic-commerce-full-stack-architecture.md) ⇄ [`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.en.md`](2026-10-18-agentic-commerce-full-stack-architecture.en.md)

---

## Stage 75：UCP 住宿预订/令牌绑定、ACP 强制 POST 幂等/发现文档、Google AP2 JCS 购物车哈希/KB-SD-JWT 逐跳校验/x402 流克隆与 Sierra $\tau$-bench 2.0 Gemini 8kHz/静默 `GoAway` 重连 16 场景（`LB-01..LB-16`）中英双语 7-Card 4:5 视觉基准报告

- **评测范围（16 场景，`LB-01..LB-16`）**：
  - `LB-01..LB-04`：UCP `dev.ucp.lodging.booking` 复合房源与三态取消政策（`#780`）、跨行业 `{type, id}` 令牌绑定与调用方授权分离（`#762`/`#746`）、Location 顶层空间关系 `distance`/`serves` 与 `filters.items[]`（`#766`/`#753`）及请求约束仅外层 `path`（`#744`）。
  - `LB-05..LB-08`：ACP 强制 POST `Idempotency-Key` 与 `422 idempotency_conflict`（`#121`）、公开 `/.well-known/acp.json`（`#137`）、`DiscountsResponse.rejected[]` 与 `sale` 划线价（`#129`/`#123`）及 `MessageInfo`/整数 `Refund.amount` 对齐（`#262`/`#249`）。
  - `LB-09..LB-12`：Google AP2 剥离 `null` 的 RFC 8785 JCS `cart_mandate_hash`（`#253`）、KB-SD-JWT 全跳 `aud`/`nonce` 与即时支付时间窗（`#326`/`#313`/`#318`）及 Coinbase x402 流式请求体克隆、未知 CAIP-2 `accepts[]` 容错与顶层 `.address`（`#306`/`#297`/`#277`）。
  - `LB-13..LB-16`：Sierra $\tau$-bench 2.0 Gemini Live 8kHz 原生电话采样与 `SlidingWindow`（`#511`/`#510`/`#509`）、静默 `GoAway` 重连截止时间监控（`#461`）、全双工非阻塞用户语音生成（`#525`/`#522`）与空回复 `###STOP###` 重试（`#471`）。
- **核心量化发现**：
  - **准确率**：AI-Native 确定性护栏 **16/16 (100.0%)** vs. 经典三层架构基线 **4/16 (25.0%)**。
  - **扰动鲁棒性**：选项逆序与字段乱序下 **100.0% (0.0 pts 漂移)**。
  - **延迟对比**：单轮中位延迟 **0.34 ms vs. 4.63 ms（13.6x 加速）**。
- **新增代码与双语报告资产**：
  - 基准生成器：[`lab/ucp_lodging_token_binding_acp_idempotency_wellknown_ap2_jcs_sdjwt_x402_tau2_gemini_bench.py`](../../lab/ucp_lodging_token_binding_acp_idempotency_wellknown_ap2_jcs_sdjwt_x402_tau2_gemini_bench.py)
  - 单元测试：[`tests/test_ucp_lodging_token_binding_acp_idempotency_wellknown_ap2_jcs_sdjwt_x402_tau2_gemini_bench.py`](../../tests/test_ucp_lodging_token_binding_acp_idempotency_wellknown_ap2_jcs_sdjwt_x402_tau2_gemini_bench.py)（全仓库 **414/414** 单测通过）
  - 双语 7-Card 4:5 报告：[`reports/agentic-commerce-ucp-lodging-token-binding-acp-idempotency-wellknown-ap2-jcs-sdjwt-x402-tau2-gemini-bench/index.html`（中文）](../../reports/agentic-commerce-ucp-lodging-token-binding-acp-idempotency-wellknown-ap2-jcs-sdjwt-x402-tau2-gemini-bench/index.html) ⇄ [`index.en.html`（English）](../../reports/agentic-commerce-ucp-lodging-token-binding-acp-idempotency-wellknown-ap2-jcs-sdjwt-x402-tau2-gemini-bench/index.en.html) ⇄ [`report.json`](../../reports/agentic-commerce-ucp-lodging-token-binding-acp-idempotency-wellknown-ap2-jcs-sdjwt-x402-tau2-gemini-bench/report.json)

---

## Stage 76：UCP 付款账期协商/确定性营业时间/核心政策披露、ACP 订单售后全生命周期/消息解决责任/版本协商、Google AP2 多跳委托链/支付证据帧 (`PEF`)/Coinbase x402 护栏与 Sierra $\tau$-bench 2.0 语音角色翻转/Qwen 嵌套工具/并行租约护栏

- **一手协议与基准演进证据**：
  1. **UCP 付款账期协商与简化（`#741`/`#736`/`#712`/`#692`/`#603`）、Location 确定性营业时间（`#687`/`#589`）、核心 `policies[]` 披露联动（`#572`）、履约目的地方法级作者边界（`#689`/`#688`/`#671`）与多模态媒体（`#690`）**：账期通过 `payment.selected_term_id` 选定、标量 `schedules[].amount` 替代单元素 `totals[]`、禁与 `split_payments` 组合并在商家改期时强制发出 `payment_term_changed` 告警；营业时间强制商家 IANA `timezone`、成对 `opens`/`closes`（禁 `00:00`–`00:00`）、闭区间 `valid_from`/`valid_through` 禁非全等重叠并以带偏移 `open_at` 替代 `open_now`；核心 `policies[]` 的 `final_sale` 强制绑定 `presentation: "disclosure"` 告警。
  2. **ACP 原生订单售后生命周期（`#106`）、`Message.resolution` 与 `intervention_required` vs `requires_3ds`（`#100`/`#143`/`#118`/`#115`）及 `supported_versions[]` 版本协商（`#99`/`#117`）**：校验 `Order.line_items[].quantity`（`shipped <= ordered`）、`fulfillments[]` 与 `adjustments[]`；校验 `Message.resolution` 闭集枚举、区分能力不匹配 `intervention_required` 与缺失认证结果 `requires_3ds`，并要求版本错误返回 `supported_versions[]`。
  3. **Google AP2 多跳 `~~` SD-JWT 解码与状态序列化（`#350`/`#371`/`#159`）、支付证据帧 `PEF`/合规/结算/信任信封与会话限额（`#274`/`#272`/`#271`/`#269`/`#276`）及 Coinbase x402 Bazaar 格式/公共 Facilitator/多链 USDC/对手方证明（`#283`/`#206`/`#244`/`#180`/`#225`/`#136`）**：先按 `~~` 再按 `~` 切分多跳委托链；校验 `PEF` 五态 `claim_type` 与 JCS SHA-256 `frame_id`/`receipt_hash` 及 `402 agent_spend_cap_exceeded`；拦截测试网公共 Facilitator 误配 Base 主网 `eip155:8453`，并校验 Celo/Arbitrum USDC 与第三方 DID Ed25519 事实证明。
  4. **Sierra $\tau$-bench 2.0 语音角色翻转空白轮次过滤（`#440`）、三态实时用户生成（`#526`/`#523`/`#521`）、Qwen `qwen3.5-omni-plus-realtime` 嵌套工具（`#449`/`#450`）与用量计费/并发上限/并行租约（`#454`/`#456`/`#455`/`#483`/`#535`）**：双向翻转丢弃无工具调用的空白轮次；Qwen 强制升级 3.5 模型并使用嵌套 `function` 工具格式；`UsageRecord` 区分增量与累计最后值胜出且未知模型返回 `cost = None`；强制语音并发上限与控制器单写检查点。
- **新增代码与双语文档资产**：
  - 护栏模块：[`lab/ucp_payment_terms_hours_policies_acp_order_lifecycle_ap2_pef_x402_tau2_voice_guard.py`](../../lab/ucp_payment_terms_hours_policies_acp_order_lifecycle_ap2_pef_x402_tau2_voice_guard.py)
  - 单元测试：[`tests/test_ucp_payment_terms_hours_policies_acp_order_lifecycle_ap2_pef_x402_tau2_voice_guard.py`](../../tests/test_ucp_payment_terms_hours_policies_acp_order_lifecycle_ap2_pef_x402_tau2_voice_guard.py)（全仓库 **422/422** 单测通过）
  - 双语架构章节：[`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md` (§75)](2026-10-18-agentic-commerce-full-stack-architecture.md) ⇄ [`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.en.md`](2026-10-18-agentic-commerce-full-stack-architecture.en.md)

---

## Stage 77：16 场景（`PT-01..PT-16`）中英双语 7-Card 4:5 基准评测套件

- **基准评测结果**：
  - 覆盖 Stage 76 四大协议域的 16 个确定性场景（`PT-01..PT-16`，含 4 个标称准入场景与 12 个真实规范违例故障注入场景）。
  - **AI-Native 护栏准确率**：**16/16 (100.0%)**；**经典三层基线准确率**：**4/16 (25.0%)**（漏放全部 12 个协议/加密/语音故障场景）。
  - **逆序扰动一致性**：**100.0% (16/16)**；**中位延迟**：**0.35 ms vs. 4.68 ms（13.4x 加速）**。
- **新增代码与双语报告资产**：
  - 基准生成器：[`lab/ucp_payment_terms_hours_policies_acp_order_lifecycle_ap2_pef_x402_tau2_voice_bench.py`](../../lab/ucp_payment_terms_hours_policies_acp_order_lifecycle_ap2_pef_x402_tau2_voice_bench.py)
  - 单元测试：[`tests/test_ucp_payment_terms_hours_policies_acp_order_lifecycle_ap2_pef_x402_tau2_voice_bench.py`](../../tests/test_ucp_payment_terms_hours_policies_acp_order_lifecycle_ap2_pef_x402_tau2_voice_bench.py)（全仓库 **424/424** 单测通过）
  - 双语 7-Card 4:5 报告：[`reports/agentic-commerce-ucp-payment-terms-hours-policies-acp-order-lifecycle-ap2-pef-x402-tau2-voice-bench/index.html`（中文）](../../reports/agentic-commerce-ucp-payment-terms-hours-policies-acp-order-lifecycle-ap2-pef-x402-tau2-voice-bench/index.html) ⇄ [`index.en.html`（English）](../../reports/agentic-commerce-ucp-payment-terms-hours-policies-acp-order-lifecycle-ap2-pef-x402-tau2-voice-bench/index.en.html) ⇄ [`report.json`](../../reports/agentic-commerce-ucp-payment-terms-hours-policies-acp-order-lifecycle-ap2-pef-x402-tau2-voice-bench/report.json)

---

## Stage 78：UCP 销售计量步长 `quantity_unit`/非空 `actions` 与 `policies`/积分分摊/事件流、ACP 委托 3DS 认证与支付处理器框架、Google AP2 跨商户原子预算中心与 TrustBoost PII 脱敏及 Sierra $\tau$-bench 2.0 `gptlive` 全双工适配器/转写重试/银行题库防泄漏护栏

- **一手协议与基准演进证据**：
  1. **UCP 销售计量步长 `quantity_unit`（`#653`）、非空 `actions` 与 `policies[].applies_to`（`#669`/`#661`）、积分 `earning_forecast.breakdown` 守恒（`#662`）、请求体服务端字段剔除（`#651`/`#646`）及 `event_feed`/数组省略符后置索引（`#686`/`#679`/`#673`）**：校验整数步长 `quantity` 与 `10^-scale` 单价舍入守恒、禁止 `C62` 使用非零 `scale`；禁止空 `actions: {}` 与空 `applies_to: []`；强制积分明细求和等于总预测积分；阻断请求体混入只读字段与省略符前置索引偏差。
  2. **ACP 委托 3DS 认证 API（`#93`/`#80`/`#85`/`#66`）与支付处理器/折扣扩展框架（`#90`/`#89`/`#77`/`#76`）**：强制 `create`/`authenticate`/`retrieve` 三端点顺序状态机、移除 `AuthenticationMetadata.channel`、以反向域名 `capabilities.payment.handlers[]` 替代 `payment_methods[]` 并绑定 `merchant_id`。
  3. **Google AP2 跨商户原子预算中心（`#252`）、TrustBoost LLM 前置 PII 脱敏（`#267`）与验证方 `checkout_hash` 规范性义务（`#243`/`#233`）**：阻断多商户独立 `MandateContext` 并发超支竞态，强制四原语原子预算授权；在载荷送入 LLM 前完成 x402 付费 PII 脱敏与 Solana 链上锚定验证。
  4. **Sierra $\tau$-bench 2.0 `gptlive` 全双工语音提供方（`#409`）、瞬态转写故障重试（`#418`）、`tau2 view` 截断（`#434`）、非空奖励准则门禁（`#411`）与银行题库答案泄漏清洗（`#429`/`#414`/`#412`/`#408`）**：校验 `delegation.responses.tools` 与 `item_id` 关联、RMS 迟滞静音门限、瞬态转写重试、移除 `db.json` 中 `SHOULD BE FREE` 等答案泄漏标注并修正 T074 黄金退款额为 `$14.50`。
- **新增代码与双语文档资产**：
  - 护栏模块：[`lab/ucp_sale_basis_loyalty_actions_acp_delegated_auth_handlers_ap2_budget_pii_tau2_gptlive_guard.py`](../../lab/ucp_sale_basis_loyalty_actions_acp_delegated_auth_handlers_ap2_budget_pii_tau2_gptlive_guard.py)
  - 单元测试：[`tests/test_ucp_sale_basis_loyalty_actions_acp_delegated_auth_handlers_ap2_budget_pii_tau2_gptlive_guard.py`](../../tests/test_ucp_sale_basis_loyalty_actions_acp_delegated_auth_handlers_ap2_budget_pii_tau2_gptlive_guard.py)（全仓库 **432/432** 单测通过）
  - 双语架构章节：[`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md` (§77)](2026-10-18-agentic-commerce-full-stack-architecture.md) ⇄ [`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.en.md`](2026-10-18-agentic-commerce-full-stack-architecture.en.md)

---

## Stage 79：覆盖 Stage 78 的 16 场景（`SB-01..SB-16`）中英双语 7-Card 4:5 视觉基准评测报告

- **评测矩阵与关键结果**：
  1. **16 场景全覆盖（`SB-01..SB-16`）**：覆盖 UCP 销售计量步长 `quantity_unit`/非空 `actions` 与 `policies`/积分分摊/事件流（`SB-01..SB-05`）、ACP 委托 3DS 认证与支付处理器框架（`SB-06..SB-09`）、Google AP2 跨商户原子预算中心与 TrustBoost PII 脱敏（`SB-10..SB-12`）以及 Sierra $\tau$-bench 2.0 `gptlive` 全双工适配器/转写重试/银行题库防泄漏（`SB-13..SB-16`）。
  2. **AI-Native vs. Classic 3-Tier 准确率与延迟**：AI-Native 确定性护栏取得 **16/16（100.0%）** 准确率与 **16/16（100.0%）** 逆序扰动一致性；经典三层架构基线仅通过 4 个正向场景（**4/16, 25.0%**），漏检全部 12 类协议与评测攻击；中位延迟 **0.36 ms vs. 4.74 ms（13.2x 加速）**。
- **新增代码与双语报告资产**：
  - 基准评测器：[`lab/ucp_sale_basis_loyalty_actions_acp_delegated_auth_handlers_ap2_budget_pii_tau2_gptlive_bench.py`](../../lab/ucp_sale_basis_loyalty_actions_acp_delegated_auth_handlers_ap2_budget_pii_tau2_gptlive_bench.py)
  - 单元测试：[`tests/test_ucp_sale_basis_loyalty_actions_acp_delegated_auth_handlers_ap2_budget_pii_tau2_gptlive_bench.py`](../../tests/test_ucp_sale_basis_loyalty_actions_acp_delegated_auth_handlers_ap2_budget_pii_tau2_gptlive_bench.py)（全仓库 **434/434** 单测通过）
  - 双语 7-Card 4:5 报告：[`reports/agentic-commerce-ucp-sale-basis-loyalty-actions-acp-delegated-auth-handlers-ap2-budget-pii-tau2-gptlive-bench/index.html`（中文）](../../reports/agentic-commerce-ucp-sale-basis-loyalty-actions-acp-delegated-auth-handlers-ap2-budget-pii-tau2-gptlive-bench/index.html) ⇄ [`index.en.html`（English）](../../reports/agentic-commerce-ucp-sale-basis-loyalty-actions-acp-delegated-auth-handlers-ap2-budget-pii-tau2-gptlive-bench/index.en.html) ⇄ [`report.json`](../../reports/agentic-commerce-ucp-sale-basis-loyalty-actions-acp-delegated-auth-handlers-ap2-budget-pii-tau2-gptlive-bench/report.json)

---

## Stage 80：UCP 命名空间权威绑定/分层买家同意/权益核验/准入期 Mandate TTL/原始 `r||s` 签名、ACP 混合履约/TLS 1.3/8 位 IIN/B2B 小数数量、Google AP2 RFC 8785 JCS 绑定/DID+STARK 结算与 Visa TAP RFC 9421 验签及 Sierra $\tau$-bench 2.0 全双工语音重评分/银行倒序交易/可发现工具调用护栏

- **一手协议与基准演进证据**：
  1. **UCP 命名空间权威绑定（`#530`）、按细分维度买家同意（`#451`）、`context.eligibility` 权益核验契约（`#250`）、`complete_checkout` 准入期 AP2 Mandate TTL（`#540`）、ECDSA 原始 `r||s` 签名编码（`#590`）及嵌入式错误包裹/链接委托/购物车折扣连续性（`#494`/`#247`/`#246`）**：强制反向域名能力前缀与 `schema` HTTPS 源站域名一致；校验未解决权益声明阻断结账完成且失败不篡改订单；准入后进入 `complete_in_progress` 的授权过期不得中断结算；拦截 ASN.1 DER `MEUC`/`MEQC` 签名编码。
  2. **ACP 混合购物车履约覆盖与联系信息（`#52`/`#51`）、`return_policy` 链接（`#49`）、`TLSv1.3`（`#32`）、6–8 位卡 IIN（`#9`）、严格 4 位 `display_last4`（`#1`）及 B2B 正小数数量（`#3`）**：强制配送选项金额为整数次单位、混合实物+数字商品全覆盖、禁用废弃 `seller_shop_policies` 链接。
  3. **Google AP2 RFC 8785 JCS `CartMandate`→`PaymentMandate` 绑定（`#251`/`#370`）、DID + STARK 结算承诺（`#257`）、Vertex AI 强类型修饰器（`#48`）及 Visa TAP RFC 9421 商户后端验签（`#21`）**：通过 RFC 8785 JCS 规范化哈希防止跨语言购物车替换；强制 Visa TAP 签名基串以 `"@signature-params"` 结尾、逐项引号包裹组件、校验 `alg` 与公钥类型一致并在验签通过后才记录 `nonce`。
  4. **Sierra $\tau$-bench 2.0 全双工语音轨迹重评分（`#399`）、银行交易时间倒序与最早重复争议（`#403`）、挂失卡可发现读取工具调用（`#402`）、嵌套 JSON/数值参数归一化（`#401`/`#397`）、单题回放故障隔离（`#393`）、白金卡 10% 标题修正（`#388`）及航司退座/LiteLLM/推理模型温度修复（`#362`/`#361`/`#360`/`#358`）**：阻断全双工轨迹按半双工 `messages=None` 误判 0 分、消除 `33` 与 `33.0` 导致的 DB 哈希漂移。
- **新增代码与双语文档资产**：
  - 护栏模块：[`lab/ucp_authority_consent_eligibility_acp_3ds_fulfillment_ap2_jcs_tap_rfc9421_tau2_duplex_guard.py`](../../lab/ucp_authority_consent_eligibility_acp_3ds_fulfillment_ap2_jcs_tap_rfc9421_tau2_duplex_guard.py)
  - 单元测试：[`tests/test_ucp_authority_consent_eligibility_acp_3ds_fulfillment_ap2_jcs_tap_rfc9421_tau2_duplex_guard.py`](../../tests/test_ucp_authority_consent_eligibility_acp_3ds_fulfillment_ap2_jcs_tap_rfc9421_tau2_duplex_guard.py)（全仓库 **442/442** 单测通过）
  - 双语架构章节：[`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md` (§79)](2026-10-18-agentic-commerce-full-stack-architecture.md) ⇄ [`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.en.md`](2026-10-18-agentic-commerce-full-stack-architecture.en.md)

---

## Stage 81：16 场景（`AC-01..AC-16`）中英双语 7-Card 4:5 视觉基准评测报告（覆盖 Stage 80 四大护栏域）

- **核心量化发现（Headline-as-Finding）**：
  - 在覆盖 UCP 命名空间权威绑定/买家同意/权益核验/Mandate TTL/原始签名（`#530`/`#451`/`#250`/`#540`/`#590`）、ACP 3DS/混合履约/8 位 IIN/B2B 小数数量（`#52`/`#51`/`#49`/`#9`/`#3`）、Google AP2 RFC 8785 JCS 绑定/DID+STARK 与 Visa TAP RFC 9421 验签（`#251`/`#257`/TAP `#21`）及 Sierra $\tau$-bench 2.0 全双工语音重评分/银行倒序交易/可发现工具调用（`#399`/`#403`/`#402`/`#397`/`#358`）的 **16 个确定性场景（`AC-01..AC-16`）** 中，AI-Native 护栏取得 **16/16（100.0%）** 准确率与 **16/16（100.0%）** 键序翻转一致性，而经典三层 Web 架构基线仅为 **4/16（25.0%）**；中位延迟 **0.35 ms vs. 4.72 ms（13.5x 加速）**。
- **新增代码与双语报告资产**：
  - 基准套件：[`lab/ucp_authority_consent_eligibility_acp_3ds_fulfillment_ap2_jcs_tap_rfc9421_tau2_duplex_bench.py`](../../lab/ucp_authority_consent_eligibility_acp_3ds_fulfillment_ap2_jcs_tap_rfc9421_tau2_duplex_bench.py)
  - 单元测试：[`tests/test_ucp_authority_consent_eligibility_acp_3ds_fulfillment_ap2_jcs_tap_rfc9421_tau2_duplex_bench.py`](../../tests/test_ucp_authority_consent_eligibility_acp_3ds_fulfillment_ap2_jcs_tap_rfc9421_tau2_duplex_bench.py)（全仓库 **444/444** 单测通过）
  - 双语 7-Card 4:5 报告：[`reports/agentic-commerce-ucp-authority-consent-eligibility-acp-3ds-fulfillment-ap2-jcs-tap-rfc9421-tau2-duplex-bench/index.html`（中文）](../../reports/agentic-commerce-ucp-authority-consent-eligibility-acp-3ds-fulfillment-ap2-jcs-tap-rfc9421-tau2-duplex-bench/index.html) ⇄ [`index.en.html`（English）](../../reports/agentic-commerce-ucp-authority-consent-eligibility-acp-3ds-fulfillment-ap2-jcs-tap-rfc9421-tau2-duplex-bench/index.en.html) ⇄ [`report.json`](../../reports/agentic-commerce-ucp-authority-consent-eligibility-acp-3ds-fulfillment-ap2-jcs-tap-rfc9421-tau2-duplex-bench/report.json)

---

## Stage 82：UCP 多变体媒体/方法级目的地/对象根 `totals.json`/MCP 幂等契约/A2A 写冻结/脱敏 `order.payment`/礼品与只读 `ask`、ACP 默认配送项/委托支付错误枚举/内容引用归因/MCP 绑定、Coinbase x402 签名前代码级限额策略/请求指纹绑定/`attestseal` 证明/`SAR` 交付绑定/`ERC-7710` 与 Sierra $\tau$-bench 2.0 关户原因枚举/空完成重试/评测溯源/TTS 并发上限护栏

- **一手协议与基准演进证据**：
  1. **UCP 多变体媒体（`#690`/`#675`）、方法级目的地类型（`#689`）、对象根 `totals.json`（`#684`）、MCP `idempotency-key` 冲突返回 `409`/`-32000` 与 A2A `complete_in_progress` 写冻结（`#679`/`#670`）、`context.location` 非目的地语义（`#671`）、脱敏 `order.payment`（`#584`）、赠品行 `gift_line_item_id` 与折扣拒绝码（`#578`/`#577`）、单一规范 `keys[]` JWKS（`#566`）、只读 `ask`（`#538`）及礼品结账 `recipient_required`（`#508`）**。
  2. **ACP 创建结账默认配送项预选（`#198`）、委托支付 `PaymentMethodCard.virtual` 必填与 `401/500/503` 错误枚举（`#161`/`#132`）、`content_attribution` 引用归因（`#149`）、MCP JSON-RPC 2.0 传输绑定（`#139`）、`PaymentHandler.display_name` 与 `authorize`/`capture`（`#130`）及统一 `AppliedDiscount`（`#125`）**。
  3. **Coinbase x402 签名前代码层 `onPaymentRequested` 策略（`#166`）、支付标识符绑定规范化请求指纹（`#165`）、`attestseal-trust-attestation` 独立权威 DID Ed25519 证明（`#136`）、结算证明收据 `SAR` 交付摘要绑定（`#46`）、`ERC-7710` `redeemDelegations` 预模拟（`#22`）及 Facilitator 钩子异常隔离与 `crypto/rand` CSPRNG 费率支付方（`#13`）**。
  4. **Sierra $\tau$-bench 2.0 银行 `close_bank_account_7392` 固定关户原因枚举（`#484`）、T091 `persona` 键修正（`#478`）、文本用户模拟器空完成自动重试（`#471`）、评测器溯源元数据（`#467`）、多客户电信 `DB` 奖励基准（`#462`）及 ElevenLabs TTS 并发上限（`#457`）**。
- **新增代码与双语文档资产**：
  - 护栏模块：[`lab/ucp_media_dest_totals_acp_default_deliv_mcp_x402_sar_erc7710_tau2_close_prov_guard.py`](../../lab/ucp_media_dest_totals_acp_default_deliv_mcp_x402_sar_erc7710_tau2_close_prov_guard.py)
  - 单元测试：[`tests/test_ucp_media_dest_totals_acp_default_deliv_mcp_x402_sar_erc7710_tau2_close_prov_guard.py`](../../tests/test_ucp_media_dest_totals_acp_default_deliv_mcp_x402_sar_erc7710_tau2_close_prov_guard.py)（全仓库 **452/452** 单测通过）
  - 双语架构章节：[`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md` (§81)](2026-10-18-agentic-commerce-full-stack-architecture.md) ⇄ [`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.en.md`](2026-10-18-agentic-commerce-full-stack-architecture.en.md)

---

## Stage 83：覆盖 Stage 82 的 16 场景中英双语 7-Card 4:5 基准评测报告（`MD-01..MD-16`）

- **量化评测结果**：
  - **AI-Native 确定性护栏**：`16/16 (100.0%)` 准确拦截/放行（对比经典三层 Web 基线 `4/16 (25.0%)`）；
  - **逆序扰动一致性**：`16/16 (100.0%)` 零漂移；
  - **中位延迟**：`0.35 ms` vs. `4.76 ms`（**13.6x 加速**）。
- **新增代码与双语报告资产**：
  - 基准套件：[`lab/ucp_media_dest_totals_acp_default_deliv_mcp_x402_sar_erc7710_tau2_close_prov_bench.py`](../../lab/ucp_media_dest_totals_acp_default_deliv_mcp_x402_sar_erc7710_tau2_close_prov_bench.py)
  - 单元测试：[`tests/test_ucp_media_dest_totals_acp_default_deliv_mcp_x402_sar_erc7710_tau2_close_prov_bench.py`](../../tests/test_ucp_media_dest_totals_acp_default_deliv_mcp_x402_sar_erc7710_tau2_close_prov_bench.py)（全仓库 **454/454** 单测通过）
  - 双语 7-Card 4:5 报告：[`reports/agentic-commerce-ucp-media-dest-totals-acp-default-deliv-mcp-x402-sar-erc7710-tau2-close-prov-bench/index.html`（中文）](../../reports/agentic-commerce-ucp-media-dest-totals-acp-default-deliv-mcp-x402-sar-erc7710-tau2-close-prov-bench/index.html) ⇄ [`index.en.html`（English）](../../reports/agentic-commerce-ucp-media-dest-totals-acp-default-deliv-mcp-x402-sar-erc7710-tau2-close-prov-bench/index.en.html) ⇄ [`report.json`](../../reports/agentic-commerce-ucp-media-dest-totals-acp-default-deliv-mcp-x402-sar-erc7710-tau2-close-prov-bench/report.json)

---

## Stage 84：UCP 单次使用配送地址隐私与 MCP 宏对齐、ACP A2A 推式银行转账与 3DS 认证结果、Coinbase x402 EIP-3009 回滚错误映射与 Google AP2 HNP 会话授权及 Sierra $\tau$-bench 2.0 重复交易 `posting_sequence` 与跨卡欺诈关停护栏

- **一手协议与基准演进证据**：
  1. **UCP 单次使用配送地址 `one_time_use` 隐私提示（`#435`）与 `checkout-mcp.md`/`order-mcp.md` `{{ schema_fields(...) }}` 宏及错误信封对齐（`#444`）**。
  2. **ACP `dev.acp.account_to_account` 推式银行转账指令与确认生命周期（`#30`）及 3DS 认证结果（`denied` vs `attempt_acknowledged`）（`#78`）**。
  3. **Coinbase x402 `verifyEIP3009` 模拟失败隔离与 `parseEIP3009TransferError` 合约回滚码映射（`#70`）及 Google AP2 人不在场 `SessionAuthorization` 与 `SpendingRuleSet`（`#74`）**。
  4. **Sierra $\tau$-bench 2.0 银行重复交易 `posting_sequence` 去歧义（`#380`）与 `task_082` 跨卡确认欺诈全量 `close_debit_card_4721` 关停（`#413`）**。
- **新增代码与双语文档资产**：
  - 护栏模块：[`lab/ucp_onetime_dest_mcp_acp_a2a_3ds_x402_eip3009_ap2_hnp_tau2_dup_guard.py`](../../lab/ucp_onetime_dest_mcp_acp_a2a_3ds_x402_eip3009_ap2_hnp_tau2_dup_guard.py)
  - 单元测试：[`tests/test_ucp_onetime_dest_mcp_acp_a2a_3ds_x402_eip3009_ap2_hnp_tau2_dup_guard.py`](../../tests/test_ucp_onetime_dest_mcp_acp_a2a_3ds_x402_eip3009_ap2_hnp_tau2_dup_guard.py)（全仓库 **462/462** 单测通过）
  - 双语架构章节：[`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md` (§83)](2026-10-18-agentic-commerce-full-stack-architecture.md) ⇄ [`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.en.md`](2026-10-18-agentic-commerce-full-stack-architecture.en.md)

---

## Stage 85：覆盖 Stage 84 的 16 场景中英双语 7-Card 4:5 基准评测报告（`OD-01..OD-16`）

- **量化评测结果**：
  - **AI-Native 确定性护栏**：`16/16 (100.0%)` 准确拦截/放行（对比经典三层 Web 基线 `4/16 (25.0%)`）；
  - **逆序扰动一致性**：`16/16 (100.0%)` 零漂移；
  - **中位延迟**：`0.35 ms` vs. `4.76 ms`（**13.6x 加速**）。
- **新增代码与双语报告资产**：
  - 基准套件：[`lab/ucp_onetime_dest_mcp_acp_a2a_3ds_x402_eip3009_ap2_hnp_tau2_dup_bench.py`](../../lab/ucp_onetime_dest_mcp_acp_a2a_3ds_x402_eip3009_ap2_hnp_tau2_dup_bench.py)
  - 单元测试：[`tests/test_ucp_onetime_dest_mcp_acp_a2a_3ds_x402_eip3009_ap2_hnp_tau2_dup_bench.py`](../../tests/test_ucp_onetime_dest_mcp_acp_a2a_3ds_x402_eip3009_ap2_hnp_tau2_dup_bench.py)（全仓库 **464/464** 单测通过）
  - 双语 7-Card 4:5 报告：[`reports/agentic-commerce-ucp-onetime-dest-mcp-acp-a2a-3ds-x402-eip3009-ap2-hnp-tau2-dup-bench/index.html`（中文）](../../reports/agentic-commerce-ucp-onetime-dest-mcp-acp-a2a-3ds-x402-eip3009-ap2-hnp-tau2-dup-bench/index.html) ⇄ [`index.en.html`（English）](../../reports/agentic-commerce-ucp-onetime-dest-mcp-acp-a2a-3ds-x402-eip3009-ap2-hnp-tau2-dup-bench/index.en.html) ⇄ [`report.json`](../../reports/agentic-commerce-ucp-onetime-dest-mcp-acp-a2a-3ds-x402-eip3009-ap2-hnp-tau2-dup-bench/report.json)

---

## Stage 86：UCP `schema.org/PropertyValue` 商品属性继承与 RFC 9535 `message.path`（`#401`/`#397`/`#380`）、ACP `RejectedDiscount` 拒绝码与 `Message.resolution` 升级隔离（`#101`/`#100`/`#115`）、Coinbase x402 `no-wallet` 扩展与 `ERC-8021` 构建者归因（`#317`/`#31`）及 Sierra $\tau$-bench 2.0 全双工语音缓冲排空与 `hospitality` 酒店预订域策略（`#363`/`#355`）确定性护栏

- **一手协议与代码审计要点**：
  1. **UCP (`#401`, `#397`, `#380`)**：`shopping/types/attribute.json` 对齐 `schema.org/PropertyValue`（必填 `name`/`value`，可选 `key`/`numeric_value`/`unit`），强制 `Variant.attributes` 按 `key` 或不区分大小写 `name` 覆盖并继承 `Product.attributes`；`messages[].path` 必须符合 RFC 9535 JSONPath 语法（禁用旧版 `$.items[...]`）、`recoverable` 错误精确修复目标字段且 `unrecoverable` 错误禁止自动重试。
  2. **ACP (`#101`, `#100`, `#115`)**：`DiscountsObject.rejected[]` 必填 `code` 与 8 值 `DiscountErrorCode` 枚举 `reason` 并校验 `AppliedDiscount.allocations` 分摊守恒；`Message.resolution` 在 `requires_buyer_input` 或 `requires_buyer_review` 时阻断无买家参与的自动重试/下单；严格隔离 `2xx` 会话内 `MessageError` 与 `4xx/5xx` 顶层 `Error`。
  3. **Coinbase x402 (`#317`, `#31`)**：`extensions["no-wallet"].info` 校验 `anyWalletWorks: true`、`requires.{asset, network, amount}` 与顶层 `PaymentRequirements` 一致、拦截自动执行不可信 `wallets[].install` Shell 命令、阻断余额不足但已有签名器时盲目安装钱包，并校验 `ERC-8021` `[builderCode UTF-8 hex][01][8021000000000000000000008021]` 归因后缀。
  4. **Sierra $\tau$-bench 2.0 (`#363`, `#355`)**：全双工 `_finalize()` 停止前调用 `_drain_buffered_agent_audio()` 将残余语音并入末个 tick 并标记 `contains_speech=True`；`hospitality` 域强制单轮单工具调用且不与回复同轮、核验确认号+姓名后才可读写预订、总人数（含儿童）不超房型容量、超 4 间房转人工，以及执行 `RP_SAVER` 禁退改/禁退订重订绕过与 `RP_FLEX` 退费精算。
- **新增代码与双语文档资产**：
  - 护栏模块：[`lab/ucp_attr_path_acp_discount_res_x402_nowallet_erc8021_tau2_hospitality_guard.py`](../../lab/ucp_attr_path_acp_discount_res_x402_nowallet_erc8021_tau2_hospitality_guard.py)
  - 单元测试：[`tests/test_ucp_attr_path_acp_discount_res_x402_nowallet_erc8021_tau2_hospitality_guard.py`](../../tests/test_ucp_attr_path_acp_discount_res_x402_nowallet_erc8021_tau2_hospitality_guard.py)（全仓库 **472/472** 单测通过）
  - 双语架构章节：[`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md` (§85)](2026-10-18-agentic-commerce-full-stack-architecture.md) ⇄ [`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.en.md`](2026-10-18-agentic-commerce-full-stack-architecture.en.md)

---

## Stage 87：16 场景（`AP-01..AP-16`）中英双语 7-Card 4:5 视觉基准评测报告

- **评测矩阵与核心量化结论**：
  - 针对 Stage 86 四大协议域构建 16 场景合成基准（`AP-01..AP-16`：4 个合规放行场景 + 12 个协议层高危违约阻断场景）。
  - **AI-Native 确定性护栏**：**16/16 (100.0%)** 准确判定 vs **经典三层 Web 基线**：**4/16 (25.0%)**（提升 **+75.0 pts**）；逆序评估扰动一致性 **16/16 (100.0%, 0.0 pts 漂移)**；中位延迟 **0.35 ms** vs **4.76 ms**（**13.6x** 加速）。
- **新增代码与双语报告资产**：
  - 基准套件：[`lab/ucp_attr_path_acp_discount_res_x402_nowallet_erc8021_tau2_hospitality_bench.py`](../../lab/ucp_attr_path_acp_discount_res_x402_nowallet_erc8021_tau2_hospitality_bench.py)
  - 单元测试：[`tests/test_ucp_attr_path_acp_discount_res_x402_nowallet_erc8021_tau2_hospitality_bench.py`](../../tests/test_ucp_attr_path_acp_discount_res_x402_nowallet_erc8021_tau2_hospitality_bench.py)（全仓库 **474/474** 单测通过）
  - 双语 7-Card 4:5 报告：[`reports/agentic-commerce-ucp-attr-path-acp-discount-res-x402-nowallet-erc8021-tau2-hospitality-bench/index.html`（中文）](../../reports/agentic-commerce-ucp-attr-path-acp-discount-res-x402-nowallet-erc8021-tau2-hospitality-bench/index.html) ⇄ [`index.en.html`（English）](../../reports/agentic-commerce-ucp-attr-path-acp-discount-res-x402-nowallet-erc8021-tau2-hospitality-bench/index.en.html) ⇄ [`report.json`](../../reports/agentic-commerce-ucp-attr-path-acp-discount-res-x402-nowallet-erc8021-tau2-hospitality-bench/report.json)

---

## Stage 88：UCP 身份绑定 OAuth 2.0 能力级 Scope 与 Webhook/订单签名头（`#354`/`#353`/`#342`/`#370`）、ACP 扩展框架 JSONPath 与增强结账（`#89`/`#83`）、Coinbase x402 EIP-712 域映射与 `@x402/base` 网络边界（`#324`/`#312`/`#229`）及 Sierra $\tau$-bench 2.0 多语种裁判与榜单指标门禁（`#348`/`#352`/`#342`）确定性护栏

- **新增代码与双语文档资产**：
  - 护栏模块：[`lab/ucp_identity_oauth_acp_ext_x402_eip712_base_tau2_multilingual_guard.py`](../../lab/ucp_identity_oauth_acp_ext_x402_eip712_base_tau2_multilingual_guard.py)
  - 单元测试：[`tests/test_ucp_identity_oauth_acp_ext_x402_eip712_base_tau2_multilingual_guard.py`](../../tests/test_ucp_identity_oauth_acp_ext_x402_eip712_base_tau2_multilingual_guard.py)（全仓库 **482/482** 单测通过）
  - 双语架构章节：[`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md` (§87)](2026-10-18-agentic-commerce-full-stack-architecture.md) ⇄ [`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.en.md`](2026-10-18-agentic-commerce-full-stack-architecture.en.md)

---

## Stage 89：16 场景（`IO-01..IO-16`）中英双语 7-Card 4:5 视觉基准评测报告（覆盖 Stage 88）

- **新增代码与双语报告资产**：
  - 基准套件：[`lab/ucp_identity_oauth_acp_ext_x402_eip712_base_tau2_multilingual_bench.py`](../../lab/ucp_identity_oauth_acp_ext_x402_eip712_base_tau2_multilingual_bench.py)
  - 单元测试：[`tests/test_ucp_identity_oauth_acp_ext_x402_eip712_base_tau2_multilingual_bench.py`](../../tests/test_ucp_identity_oauth_acp_ext_x402_eip712_base_tau2_multilingual_bench.py)（全仓库 **484/484** 单测通过）
  - 双语 7-Card 4:5 报告：[`reports/agentic-commerce-ucp-identity-oauth-acp-ext-x402-eip712-base-tau2-multilingual-bench/index.html`（中文）](../../reports/agentic-commerce-ucp-identity-oauth-acp-ext-x402-eip712-base-tau2-multilingual-bench/index.html) ⇄ [`index.en.html`（English）](../../reports/agentic-commerce-ucp-identity-oauth-acp-ext-x402-eip712-base-tau2-multilingual-bench/index.en.html) ⇄ [`report.json`](../../reports/agentic-commerce-ucp-identity-oauth-acp-ext-x402-eip712-base-tau2-multilingual-bench/report.json)

---

## Stage 90：UCP 单会话 ECP 委托确认与只读 `currency`/`context`（`#80`/`#62`/`#58`/`#86`）、ACP 周期授权 `Allowance`/账单履约地址拆分与酒店实时询价（`#73`/`#10`/`#45`）、Coinbase x402 v1.2 协同提现（`#44`）及 Sierra $\tau$-bench 2.0 A2A 隔离与 Gemini 3 `thought_signature`（`#83`/`#93`）确定性护栏

- **新增代码与双语文档资产**：
  - 护栏模块：[`lab/ucp_ecp_context_acp_recurring_address_x402_coop_tau2_a2a_guard.py`](../../lab/ucp_ecp_context_acp_recurring_address_x402_coop_tau2_a2a_guard.py)
  - 单元测试：[`tests/test_ucp_ecp_context_acp_recurring_address_x402_coop_tau2_a2a_guard.py`](../../tests/test_ucp_ecp_context_acp_recurring_address_x402_coop_tau2_a2a_guard.py)（全仓库 **492/492** 单测通过）
  - 双语架构章节：[`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md` (§89)](2026-10-18-agentic-commerce-full-stack-architecture.md) ⇄ [`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.en.md`](2026-10-18-agentic-commerce-full-stack-architecture.en.md)

---

## Stage 91：16 场景（`EC-01..EC-16`）中英双语 7-Card 4:5 视觉基准评测报告（覆盖 Stage 90）

- **新增代码与双语报告资产**：
  - 基准套件：[`lab/ucp_ecp_context_acp_recurring_address_x402_coop_tau2_a2a_bench.py`](../../lab/ucp_ecp_context_acp_recurring_address_x402_coop_tau2_a2a_bench.py)
  - 单元测试：[`tests/test_ucp_ecp_context_acp_recurring_address_x402_coop_tau2_a2a_bench.py`](../../tests/test_ucp_ecp_context_acp_recurring_address_x402_coop_tau2_a2a_bench.py)（全仓库 **494/494** 单测通过）
  - 双语 7-Card 4:5 报告：[`reports/agentic-commerce-ucp-ecp-context-acp-recurring-address-x402-coop-tau2-a2a-bench/index.html`（中文）](../../reports/agentic-commerce-ucp-ecp-context-acp-recurring-address-x402-coop-tau2-a2a-bench/index.html) ⇄ [`index.en.html`（English）](../../reports/agentic-commerce-ucp-ecp-context-acp-recurring-address-x402-coop-tau2-a2a-bench/index.en.html) ⇄ [`report.json`](../../reports/agentic-commerce-ucp-ecp-context-acp-recurring-address-x402-coop-tau2-a2a-bench/report.json)

---

## Stage 92：UCP 费用扩展与嵌入式购物车 ECaP/`ec.totals.change`（`#245`/`#244`/`#272`）、ACP 合并折扣与欧盟 Omnibus 促销及 x402 加密 SPT（`#125`/`#123`/`#111`）、Google AP2 `PaymentReceipt` 与审计日志（`#110`/`#92`）及 Sierra $\tau$-bench 2.0 航司退票座位释放与上下文超限分类（`#362`/`#360`/`#358`/`#364`）确定性护栏

- **新增代码与双语文档资产**：
  - 护栏模块：[`lab/ucp_fee_ecap_acp_sale_crypto_ap2_receipt_tau2_airline_ctx_guard.py`](../../lab/ucp_fee_ecap_acp_sale_crypto_ap2_receipt_tau2_airline_ctx_guard.py)
  - 单元测试：[`tests/test_ucp_fee_ecap_acp_sale_crypto_ap2_receipt_tau2_airline_ctx_guard.py`](../../tests/test_ucp_fee_ecap_acp_sale_crypto_ap2_receipt_tau2_airline_ctx_guard.py)（全仓库 **502/502** 单测通过）
  - 双语架构章节：[`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md` (§91)](2026-10-18-agentic-commerce-full-stack-architecture.md) ⇄ [`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.en.md`](2026-10-18-agentic-commerce-full-stack-architecture.en.md)

---

## Stage 93：16 场景（`FS-01..FS-16`）中英双语 7-Card 4:5 视觉基准评测报告（覆盖 Stage 92）

- **新增代码与双语报告资产**：
  - 基准套件：[`lab/ucp_fee_ecap_acp_sale_crypto_ap2_receipt_tau2_airline_ctx_bench.py`](../../lab/ucp_fee_ecap_acp_sale_crypto_ap2_receipt_tau2_airline_ctx_bench.py)
  - 单元测试：[`tests/test_ucp_fee_ecap_acp_sale_crypto_ap2_receipt_tau2_airline_ctx_bench.py`](../../tests/test_ucp_fee_ecap_acp_sale_crypto_ap2_receipt_tau2_airline_ctx_bench.py)（全仓库 **504/504** 单测通过）
  - 双语 7-Card 4:5 报告：[`reports/agentic-commerce-ucp-fee-ecap-acp-sale-crypto-ap2-receipt-tau2-airline-ctx-bench/index.html`（中文）](../../reports/agentic-commerce-ucp-fee-ecap-acp-sale-crypto-ap2-receipt-tau2-airline-ctx-bench/index.html) ⇄ [`index.en.html`（English）](../../reports/agentic-commerce-ucp-fee-ecap-acp-sale-crypto-ap2-receipt-tau2-airline-ctx-bench/index.en.html) ⇄ [`report.json`](../../reports/agentic-commerce-ucp-fee-ecap-acp-sale-crypto-ap2-receipt-tau2-airline-ctx-bench/report.json)

---

## Stage 94：UCP 钱包身份证明与资格证明/不适用折扣码/订单币种/链接委托（`#280`/`#264`/`#250`/`#271`/`#283`/`#247`）、ACP 虚拟卡标识与客户引用对齐（`#132`/`#133`/`#128`）、Coinbase x402 MCP+SIWX 权益复用与见证收据（`#27`/`#50`/`#46`）及 Sierra $\tau$-bench 2.0 嵌套 JSON/数值种子归一化与批量评测隔离（`#401`/`#397`/`#393`）确定性护栏

- **新增代码与双语文档资产**：
  - 护栏模块：[`lab/ucp_wallet_attest_discount_acp_virtual_x402_siwx_tau2_json_norm_guard.py`](../../lab/ucp_wallet_attest_discount_acp_virtual_x402_siwx_tau2_json_norm_guard.py)
  - 单元测试：[`tests/test_ucp_wallet_attest_discount_acp_virtual_x402_siwx_tau2_json_norm_guard.py`](../../tests/test_ucp_wallet_attest_discount_acp_virtual_x402_siwx_tau2_json_norm_guard.py)（全仓库 **512/512** 单测通过）
  - 双语架构章节：[`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md` (§93)](2026-10-18-agentic-commerce-full-stack-architecture.md) ⇄ [`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.en.md`](2026-10-18-agentic-commerce-full-stack-architecture.en.md)

---

## Stage 95：16 场景（`WA-01..WA-16`）中英双语 7-Card 4:5 视觉基准评测报告（覆盖 Stage 94）

- **新增代码与双语报告资产**：
  - 基准套件：[`lab/ucp_wallet_attest_discount_acp_virtual_x402_siwx_tau2_json_norm_bench.py`](../../lab/ucp_wallet_attest_discount_acp_virtual_x402_siwx_tau2_json_norm_bench.py)
  - 单元测试：[`tests/test_ucp_wallet_attest_discount_acp_virtual_x402_siwx_tau2_json_norm_bench.py`](../../tests/test_ucp_wallet_attest_discount_acp_virtual_x402_siwx_tau2_json_norm_bench.py)（全仓库 **514/514** 单测通过）
  - 双语 7-Card 4:5 报告：[`reports/agentic-commerce-ucp-wallet-attest-discount-acp-virtual-x402-siwx-tau2-json-norm-bench/index.html`（中文）](../../reports/agentic-commerce-ucp-wallet-attest-discount-acp-virtual-x402-siwx-tau2-json-norm-bench/index.html) ⇄ [`index.en.html`（English）](../../reports/agentic-commerce-ucp-wallet-attest-discount-acp-virtual-x402-siwx-tau2-json-norm-bench/index.en.html) ⇄ [`report.json`](../../reports/agentic-commerce-ucp-wallet-attest-discount-acp-virtual-x402-siwx-tau2-json-norm-bench/report.json)

---

## Stage 96：UCP 业务错误信封与支付限定符/可用工具约束（`#216`/`#223`/`#214`/`#187`）、ACP Webhook 防重放与可扩展错误枚举（`#160`/`#161`/`#143`）、Coinbase x402 EIP-3009 错误映射与 Bazaar 元数据净化（`#70`/`#156`/`#150`）及 Sierra $\tau$-bench 2.0 销户原因枚举、`pass^k` 分母保留与参数强转（`#484`/`#498`/`#516`/`#520`）确定性护栏

- **新增代码与双语文档资产**：
  - 护栏模块：[`lab/ucp_error_qualifiers_acp_webhook_x402_bazaar_tau2_closure_passk_guard.py`](../../lab/ucp_error_qualifiers_acp_webhook_x402_bazaar_tau2_closure_passk_guard.py)
  - 单元测试：[`tests/test_ucp_error_qualifiers_acp_webhook_x402_bazaar_tau2_closure_passk_guard.py`](../../tests/test_ucp_error_qualifiers_acp_webhook_x402_bazaar_tau2_closure_passk_guard.py)（全仓库 **522/522** 单测通过）
  - 双语架构章节：[`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md` (§95)](2026-10-18-agentic-commerce-full-stack-architecture.md) ⇄ [`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.en.md`](2026-10-18-agentic-commerce-full-stack-architecture.en.md)

---

## Stage 97：16 场景（`EQ-01..EQ-16`）中英双语 7-Card 4:5 视觉基准评测报告（覆盖 Stage 96）

- **新增代码与双语报告资产**：
  - 基准套件：[`lab/ucp_error_qualifiers_acp_webhook_x402_bazaar_tau2_closure_passk_bench.py`](../../lab/ucp_error_qualifiers_acp_webhook_x402_bazaar_tau2_closure_passk_bench.py)
  - 单元测试：[`tests/test_ucp_error_qualifiers_acp_webhook_x402_bazaar_tau2_closure_passk_bench.py`](../../tests/test_ucp_error_qualifiers_acp_webhook_x402_bazaar_tau2_closure_passk_bench.py)（全仓库 **524/524** 单测通过）
  - 双语 7-Card 4:5 报告：[`reports/agentic-commerce-ucp-error-qualifiers-acp-webhook-x402-bazaar-tau2-closure-passk-bench/index.html`（中文）](../../reports/agentic-commerce-ucp-error-qualifiers-acp-webhook-x402-bazaar-tau2-closure-passk-bench/index.html) ⇄ [`index.en.html`（English）](../../reports/agentic-commerce-ucp-error-qualifiers-acp-webhook-x402-bazaar-tau2-closure-passk-bench/index.en.html) ⇄ [`report.json`](../../reports/agentic-commerce-ucp-error-qualifiers-acp-webhook-x402-bazaar-tau2-closure-passk-bench/report.json)

---

## Stage 98：UCP 披露警告与退货扩展/平台观测信号/`get_product`（`#267`/`#257`/`#203`/`#195`）、ACP 委托 3DS 认证与版本协商（`#93`/`#99`/`#130`）、Google AP2 会话支出规则与微支付通道（`#77`/`#83`）及 Sierra $\tau$-bench 2.0 静默 `GoAway` 重连与银行多卡止付/ATM 退费/重复交易消歧（`#461`/`#382`/`#381`/`#380`/`#361`）确定性护栏

- **新增代码与双语文档资产**：
  - 护栏模块：[`lab/ucp_disclosure_return_acp_del_auth_ap2_session_tau2_goaway_guard.py`](../../lab/ucp_disclosure_return_acp_del_auth_ap2_session_tau2_goaway_guard.py)
  - 单元测试：[`tests/test_ucp_disclosure_return_acp_del_auth_ap2_session_tau2_goaway_guard.py`](../../tests/test_ucp_disclosure_return_acp_del_auth_ap2_session_tau2_goaway_guard.py)（全仓库 **532/532** 单测通过）
  - 双语架构章节：[`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md` (§97)](2026-10-18-agentic-commerce-full-stack-architecture.md) ⇄ [`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.en.md`](2026-10-18-agentic-commerce-full-stack-architecture.en.md)

---

## Stage 99：16 场景（`DR-01..DR-16`）中英双语 7-Card 4:5 视觉基准评测报告（覆盖 Stage 98）

- **新增代码与双语报告资产**：
  - 基准套件：[`lab/ucp_disclosure_return_acp_del_auth_ap2_session_tau2_goaway_bench.py`](../../lab/ucp_disclosure_return_acp_del_auth_ap2_session_tau2_goaway_bench.py)
  - 单元测试：[`tests/test_ucp_disclosure_return_acp_del_auth_ap2_session_tau2_goaway_bench.py`](../../tests/test_ucp_disclosure_return_acp_del_auth_ap2_session_tau2_goaway_bench.py)（全仓库 **534/534** 单测通过）
  - 双语 7-Card 4:5 报告：[`reports/agentic-commerce-ucp-disclosure-return-acp-del-auth-ap2-session-tau2-goaway-bench/index.html`（中文）](../../reports/agentic-commerce-ucp-disclosure-return-acp-del-auth-ap2-session-tau2-goaway-bench/index.html) ⇄ [`index.en.html`（English）](../../reports/agentic-commerce-ucp-disclosure-return-acp-del-auth-ap2-session-tau2-goaway-bench/index.en.html) ⇄ [`report.json`](../../reports/agentic-commerce-ucp-disclosure-return-acp-del-auth-ap2-session-tau2-goaway-bench/report.json)

---

## Stage 100：UCP 条件写 `ETag` 与目录错误信封/`P-521` ↔ `ES512`/AP2 授权准入 TTL/礼赠结账（`#628`/`#625`/`#540`/`#508`）、ACP 联盟归因只写传输与商家 3DS/酒店水合报价（`#57`/`#66`/`#45`）、Google AP2 `open_mandate_hash` 与高熵 `checkout_hash`（`#279`/`#278`）、Coinbase `x402` 独立事实证明与主网 Facilitator 门禁（`#225`/`#206`）及 Sierra $\tau$-bench 2.0 银行 Write-Critic/固定关户原因/Pydantic 强转/`llm_agent_solo_gt`（`#513`/`#484`/`#516`/`#508`）确定性护栏

- **新增代码与双语文档资产**：
  - 护栏模块：[`lab/ucp_etag_gift_p521_acp_affiliate_3ds_ap2_open_hash_x402_fact_tau2_guard.py`](../../lab/ucp_etag_gift_p521_acp_affiliate_3ds_ap2_open_hash_x402_fact_tau2_guard.py)
  - 单元测试：[`tests/test_ucp_etag_gift_p521_acp_affiliate_3ds_ap2_open_hash_x402_fact_tau2_guard.py`](../../tests/test_ucp_etag_gift_p521_acp_affiliate_3ds_ap2_open_hash_x402_fact_tau2_guard.py)（全仓库 **542/542** 单测通过）
  - 双语架构章节：[`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md` (§99)](2026-10-18-agentic-commerce-full-stack-architecture.md) ⇄ [`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.en.md`](2026-10-18-agentic-commerce-full-stack-architecture.en.md)

---

## Stage 101：16 场景（`EG-01..EG-16`）中英双语 7-Card 4:5 视觉基准评测报告（覆盖 Stage 100）

- **新增代码与双语报告资产**：
  - 基准套件：[`lab/ucp_etag_gift_p521_acp_affiliate_3ds_ap2_open_hash_x402_fact_tau2_bench.py`](../../lab/ucp_etag_gift_p521_acp_affiliate_3ds_ap2_open_hash_x402_fact_tau2_bench.py)
  - 单元测试：[`tests/test_ucp_etag_gift_p521_acp_affiliate_3ds_ap2_open_hash_x402_fact_tau2_bench.py`](../../tests/test_ucp_etag_gift_p521_acp_affiliate_3ds_ap2_open_hash_x402_fact_tau2_bench.py)（全仓库 **544/544** 单测通过）
  - 双语 7-Card 4:5 报告：[`reports/agentic-commerce-ucp-etag-gift-p521-acp-affiliate-3ds-ap2-open-hash-x402-fact-tau2-bench/index.html`（中文）](../../reports/agentic-commerce-ucp-etag-gift-p521-acp-affiliate-3ds-ap2-open-hash-x402-fact-tau2-bench/index.html) ⇄ [`index.en.html`（English）](../../reports/agentic-commerce-ucp-etag-gift-p521-acp-affiliate-3ds-ap2-open-hash-x402-fact-tau2-bench/index.en.html) ⇄ [`report.json`](../../reports/agentic-commerce-ucp-etag-gift-p521-acp-affiliate-3ds-ap2-open-hash-x402-fact-tau2-bench/report.json)

### Stage 102：UCP `#617`/`#609`/`#584`/`#578`/`#577`、ACP `#54`/`#46`、Google AP2 `#253`/`#267` 与 Sierra $\tau$-bench 2.0 `#534`/`#533`/`#520`/`#471` 护栏
- 新增 [`lab/ucp_fulfillment_selection_discount_order_acp_intent_upi_ap2_jcs_tau2_guard.py`](../../lab/ucp_fulfillment_selection_discount_order_acp_intent_upi_ap2_jcs_tau2_guard.py) 与单测 `tests/test_ucp_fulfillment_selection_discount_order_acp_intent_upi_ap2_jcs_tau2_guard.py`（全仓 `552/552` 单测通过）。

### Stage 103：16 场景（`FD-01..FD-16`）中英双语 7-Card 4:5 视觉基准报告
- 新增 [`lab/ucp_fulfillment_selection_discount_order_acp_intent_upi_ap2_jcs_tau2_bench.py`](../../lab/ucp_fulfillment_selection_discount_order_acp_intent_upi_ap2_jcs_tau2_bench.py) 与报告 [`reports/agentic-commerce-ucp-fulfillment-selection-discount-order-acp-intent-upi-ap2-jcs-tau2-bench/`](../../reports/agentic-commerce-ucp-fulfillment-selection-discount-order-acp-intent-upi-ap2-jcs-tau2-bench/index.html)（`554/554` 单测通过）。

### Stage 104：UCP `#566`/`#483`/`#538`/`#530`/`#460`、ACP `#53`/`#52`/`#9`/`#3`、Google AP2 `#243`/`#252` + x402 `#354` 与 Sierra $\tau$-bench 2.0 `#584`/`#581`/`#570`/`#569`/`#566` 护栏
- 新增 [`lab/ucp_wba_keys_ask_rdns_acp_3ds_decimal_tau2_nl_judge_guard.py`](../../lab/ucp_wba_keys_ask_rdns_acp_3ds_decimal_tau2_nl_judge_guard.py) 与单测 `tests/test_ucp_wba_keys_ask_rdns_acp_3ds_decimal_tau2_nl_judge_guard.py`（全仓 `562/562` 单测通过）。

### Stage 105：16 场景（`WB-01..WB-16`）中英双语 7-Card 4:5 视觉基准报告
- 新增 [`lab/ucp_wba_keys_ask_rdns_acp_3ds_decimal_tau2_nl_judge_bench.py`](../../lab/ucp_wba_keys_ask_rdns_acp_3ds_decimal_tau2_nl_judge_bench.py) 与报告 [`reports/agentic-commerce-ucp-wba-keys-ask-rdns-acp-3ds-decimal-tau2-nl-judge-bench/`](../../reports/agentic-commerce-ucp-wba-keys-ask-rdns-acp-3ds-decimal-tau2-nl-judge-bench/index.html)（`564/564` 单测通过）。

### Stage 106：UCP `#325`/`#340`/`#326`/`#324`、ACP `#35`/`#32`/`#28`/`#18`/`#17`、Google AP2 `#64`/`#216` + x402 `#88`/`#135` 与 Sierra $\tau$-bench 2.0 `#462`/`#444`/`#443` 护栏
- 新增 [`lab/ucp_ecp_envelope_loyalty_acp_pix_tls13_x402_rfc6962_tau2_telecom_db_guard.py`](../../lab/ucp_ecp_envelope_loyalty_acp_pix_tls13_x402_rfc6962_tau2_telecom_db_guard.py) 与单测 `tests/test_ucp_ecp_envelope_loyalty_acp_pix_tls13_x402_rfc6962_tau2_telecom_db_guard.py`（全仓 `572/572` 单测通过）。

### Stage 107：16 场景（`EP-01..EP-16`）中英双语 7-Card 4:5 视觉基准报告
- 新增 [`lab/ucp_ecp_envelope_loyalty_acp_pix_tls13_x402_rfc6962_tau2_telecom_db_bench.py`](../../lab/ucp_ecp_envelope_loyalty_acp_pix_tls13_x402_rfc6962_tau2_telecom_db_bench.py) 与报告 [`reports/agentic-commerce-ucp-ecp-envelope-loyalty-acp-pix-tls13-x402-rfc6962-tau2-telecom-db-bench/`](../../reports/agentic-commerce-ucp-ecp-envelope-loyalty-acp-pix-tls13-x402-rfc6962-tau2-telecom-db-bench/index.html)（`574/574` 单测通过）。

### Stage 108：UCP `#968`/`#913`/`#763`/`#633`/`#568`、ACP `#227`/`#219`/`#176`/`#102`、Google AP2 `#157`/`#148`/`#122` + x402 `#367`/`#343` 与 Sierra $\tau$-bench 2.0 `#650`/`#623`/`#500` 护栏
- 新增 [`lab/ucp_permalink_cart_id_acp_20260417_x402_aether_tau2_completeness_guard.py`](../../lab/ucp_permalink_cart_id_acp_20260417_x402_aether_tau2_completeness_guard.py) 与单测 `tests/test_ucp_permalink_cart_id_acp_20260417_x402_aether_tau2_completeness_guard.py`（全仓 `582/582` 单测通过）。

### Stage 109：16 场景（`PC-01..PC-16`）中英双语 7-Card 4:5 视觉基准报告
- 新增 [`lab/ucp_permalink_cart_id_acp_20260417_x402_aether_tau2_completeness_bench.py`](../../lab/ucp_permalink_cart_id_acp_20260417_x402_aether_tau2_completeness_bench.py) 与报告 [`reports/agentic-commerce-ucp-permalink-cart-id-acp-20260417-x402-aether-tau2-completeness-bench/`](../../reports/agentic-commerce-ucp-permalink-cart-id-acp-20260417-x402-aether-tau2-completeness-bench/index.html)（`583/583` 单测通过）。

### Stage 110：UCP `#659`/`#657`/`#655`/`#653`、ACP `#118`/`#114`/`#99`、Google AP2 `#377`/`#378` + x402 `#317` 与 Sierra $\tau$-bench `#651`/`#634`/`#611` 护栏
- 新增 [`lab/ucp_webhook_sig_namespace_acp_seller_backed_ap2_budget_x402_nowallet_tau2_guard.py`](../../lab/ucp_webhook_sig_namespace_acp_seller_backed_ap2_budget_x402_nowallet_tau2_guard.py) 与单测 `tests/test_ucp_webhook_sig_namespace_acp_seller_backed_ap2_budget_x402_nowallet_tau2_guard.py`（全仓 `591/591` 单测通过）。

### Stage 111：16 场景（`WN-01..WN-16`）中英双语 7-Card 4:5 视觉基准报告
- 新增 [`lab/ucp_webhook_sig_namespace_acp_seller_backed_ap2_budget_x402_nowallet_tau2_bench.py`](../../lab/ucp_webhook_sig_namespace_acp_seller_backed_ap2_budget_x402_nowallet_tau2_bench.py) 与报告 [`reports/agentic-commerce-ucp-webhook-sig-namespace-acp-seller-backed-ap2-budget-x402-nowallet-tau2-bench/`](../../reports/agentic-commerce-ucp-webhook-sig-namespace-acp-seller-backed-ap2-budget-x402-nowallet-tau2-bench/index.html)（`592/592` 单测通过）。

### Stage 112：UCP `#642`/`#635`/`#622`、ACP `#116`/`#111`、Google AP2 `#385`/`#365` + x402 `#324` 与 Sierra $\tau$-bench `#632`/`#602`/`#600` 护栏
- 新增 [`lab/ucp_location_render_rate_limit_acp_crypto_spt_ap2_receipt_tau2_guard.py`](../../lab/ucp_location_render_rate_limit_acp_crypto_spt_ap2_receipt_tau2_guard.py) 与单测 `tests/test_ucp_location_render_rate_limit_acp_crypto_spt_ap2_receipt_tau2_guard.py`（全仓 `600/600` 单测通过）。

### Stage 113：16 场景（`LR-01..LR-16`）中英双语 7-Card 4:5 视觉基准报告
- 新增 [`lab/ucp_location_render_rate_limit_acp_crypto_spt_ap2_receipt_tau2_bench.py`](../../lab/ucp_location_render_rate_limit_acp_crypto_spt_ap2_receipt_tau2_bench.py) 与报告 [`reports/agentic-commerce-ucp-location-render-rate-limit-acp-crypto-spt-ap2-receipt-tau2-bench/`](../../reports/agentic-commerce-ucp-location-render-rate-limit-acp-crypto-spt-ap2-receipt-tau2-bench/index.html)（`601/601` 单测通过）。

### Stage 114：UCP `#736`/`#735`/`#725`、ACP `#129`/`#117`、Google AP2 `#270`/`#269` 与 Sierra $\tau$-bench `#571`/`#567` 护栏
- 新增 [`lab/ucp_common_types_dest_privacy_acp_discounts_3ds_ap2_psd2_tau2_retail_guard.py`](../../lab/ucp_common_types_dest_privacy_acp_discounts_3ds_ap2_psd2_tau2_retail_guard.py) 与单测 `tests/test_ucp_common_types_dest_privacy_acp_discounts_3ds_ap2_psd2_tau2_retail_guard.py`（全仓 `609/609` 单测通过）。










