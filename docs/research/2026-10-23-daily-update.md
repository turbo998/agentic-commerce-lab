# 2026-10-23 Agentic Commerce 每日技术资产与架构更新索引（Stages 170–185）

🌐 **Language / 语言导航**: **中文索引 (当前)** | **[English Version (`2026-10-23-daily-update.en.md`)](2026-10-23-daily-update.en.md)** | **[2026-10-23 每日深度研究主报告 (`research/daily/2026-10-23.md`)](../../research/daily/2026-10-23.md)** | **[English Daily Report (`research/daily/2026-10-23.en.md`)](../../research/daily/2026-10-23.en.md)**

---

## Stage 170：x402 XRPL `upto` 支付通道规范（`#3023` `2b06a54`）与通配路由 `OPTIONS` 预检放行/CORS 暴露头（`#3738`/`#3809`）及批量退款收据/燃气代付 RPC/Paywall XSS/反自付洗钱（`#3096`/`#3459`/`#3855`/`#3910`）、UCP 结账状态机 `ready_for_complete` 四出边对齐（`#672` `5410813`）与采购选项远期订阅零当期计费/签名响应绑定/分操作类幂等（`#890`/`#699`/`#782`）、Stripe AI `8.0.5` 沙箱 RAK 与 `@stripe/mcp` 代理注解保留/转发失败快速 JSON-RPC 报错及 MCP `SEP-3415` 事件扩展（`8a8818e`/`#584`/`#542`/`#540`/`#3415`）、Sierra $\tau$-bench 2.0 畸形工具参数计入 `AGENT_ERROR` 分母与零售 `known_info` 剥离内部主键（`#674`/`#677`）确定性护栏

- **新增代码与双语文档资产**：
  - 护栏模块：[`lab/x402_xrpl_upto_cors_ucp_lifecycle_purchase_options_stripe_mcp_proxy_tau2_guard.py`](../../lab/x402_xrpl_upto_cors_ucp_lifecycle_purchase_options_stripe_mcp_proxy_tau2_guard.py)
  - 单元测试：[`tests/test_x402_xrpl_upto_cors_ucp_lifecycle_purchase_options_stripe_mcp_proxy_guard.py`](../../tests/test_x402_xrpl_upto_cors_ucp_lifecycle_purchase_options_stripe_mcp_proxy_guard.py)（全仓库 **739/739** 单测通过）
  - 双语架构章节：[`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md` (§169)](2026-10-18-agentic-commerce-full-stack-architecture.md) ⇄ [`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.en.md` (§169)](2026-10-18-agentic-commerce-full-stack-architecture.en.md)

---

## Stage 171：16 场景（`XP-01..XP-16`）中英双语 7-Card 4:5 视觉基准评测报告（覆盖 Stage 170）

- **新增代码与双语报告资产**：
  - 基准套件：[`lab/x402_xrpl_upto_cors_ucp_lifecycle_purchase_options_stripe_mcp_proxy_tau2_bench.py`](../../lab/x402_xrpl_upto_cors_ucp_lifecycle_purchase_options_stripe_mcp_proxy_tau2_bench.py)
  - 单元测试：[`tests/test_x402_xrpl_upto_cors_ucp_lifecycle_purchase_options_stripe_mcp_proxy_bench.py`](../../tests/test_x402_xrpl_upto_cors_ucp_lifecycle_purchase_options_stripe_mcp_proxy_bench.py)（全仓库 **741/741** 单测通过）
  - 双语 7-Card 4:5 报告：[`reports/agentic-commerce-x402-xrpl-upto-cors-ucp-lifecycle-purchase-options-stripe-mcp-proxy-tau2-bench/index.html`（中文）](../../reports/agentic-commerce-x402-xrpl-upto-cors-ucp-lifecycle-purchase-options-stripe-mcp-proxy-tau2-bench/index.html) ⇄ [`index.en.html`（English）](../../reports/agentic-commerce-x402-xrpl-upto-cors-ucp-lifecycle-purchase-options-stripe-mcp-proxy-tau2-bench/index.en.html) ⇄ [`report.json`](../../reports/agentic-commerce-x402-xrpl-upto-cors-ucp-lifecycle-purchase-options-stripe-mcp-proxy-tau2-bench/report.json)

---

## Stage 172：x402 Algorand 32 字符 CAIP-2 规范化（`#3894`）与 EVM 验签 RPC 传输错误可重试分类（`#3886`）及 SVM 可读批量证明协商/Python `x402MCPClientSync` 未付 402 抛错/Bazaar 资源契约输入（`#3905`/`#3907`/`#3906`）、UCP 分单支付 Profile `capabilities` 反向域名对象映射与 `schema` 强校验（`#658`）及 CIMD 免注册身份绑定/MCP 统一信封（`#985`/`#444`）、MCP `SEP-2076` Agent Skills 原语与 `SEP-1932` DPoP 发送方约束及 `SEP-2848` 异步工具审批（`#2076`/`#1932`/`#2848`）确定性护栏

- **新增代码与双语文档资产**：
  - 护栏模块：[`lab/x402_avm_svm_mcp_sync_ucp_split_profile_cimd_mcp_skills_dpop_guard.py`](../../lab/x402_avm_svm_mcp_sync_ucp_split_profile_cimd_mcp_skills_dpop_guard.py)
  - 单元测试：[`tests/test_x402_avm_svm_mcp_sync_ucp_split_profile_cimd_mcp_skills_dpop_guard.py`](../../tests/test_x402_avm_svm_mcp_sync_ucp_split_profile_cimd_mcp_skills_dpop_guard.py)（全仓库 **744/744** 单测通过）
  - 双语架构章节：[`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md` (§171)](2026-10-18-agentic-commerce-full-stack-architecture.md) ⇄ [`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.en.md` (§171)](2026-10-18-agentic-commerce-full-stack-architecture.en.md)

---

## Stage 173：16 场景（`AS-01..AS-16`）中英双语 7-Card 4:5 视觉基准评测报告（覆盖 Stage 172）

- **新增代码与双语报告资产**：
  - 基准套件：[`lab/x402_avm_svm_mcp_sync_ucp_split_profile_cimd_mcp_skills_dpop_bench.py`](../../lab/x402_avm_svm_mcp_sync_ucp_split_profile_cimd_mcp_skills_dpop_bench.py)
  - 单元测试：[`tests/test_x402_avm_svm_mcp_sync_ucp_split_profile_cimd_mcp_skills_dpop_bench.py`](../../tests/test_x402_avm_svm_mcp_sync_ucp_split_profile_cimd_mcp_skills_dpop_bench.py)（全仓库 **746/746** 单测通过）
  - 双语 7-Card 4:5 报告：[`reports/agentic-commerce-x402-avm-svm-mcp-sync-ucp-split-profile-cimd-mcp-skills-dpop-bench/index.html`（中文）](../../reports/agentic-commerce-x402-avm-svm-mcp-sync-ucp-split-profile-cimd-mcp-skills-dpop-bench/index.html) ⇄ [`index.en.html`（English）](../../reports/agentic-commerce-x402-avm-svm-mcp-sync-ucp-split-profile-cimd-mcp-skills-dpop-bench/index.en.html) ⇄ [`report.json`](../../reports/agentic-commerce-x402-avm-svm-mcp-sync-ucp-split-profile-cimd-mcp-skills-dpop-bench/report.json)

---

## Stage 174：UCP 分单支付跨付款条件账期分配（PR `#987` `instrument_group.schedule_type="immediate"` 与逐结账 `allowed_combinations` 收窄）、ACP ATDRP §7.4a Req 5 账本证据包时间锚定与锚后 `unanchored` 记录禁作时间类争议唯一依据（PR `#316` `8802ebe`）、x402 签名前多笔交易代付组四项不变量（`#3910` §10.3）与 `createPaymentPayload` 钩子上下文关联/SVM 失败预留释放/响应头溢出诊断（`#3898`/`#3892`/`#3899`/`#3901`/`#3904`）确定性护栏

- **新增代码与双语文档资产**：
  - 护栏模块：[`lab/ucp_split_schedules_acp_ledger_anchor_x402_group_sponsor_hooks_guard.py`](../../lab/ucp_split_schedules_acp_ledger_anchor_x402_group_sponsor_hooks_guard.py)
  - 单元测试：[`tests/test_ucp_split_schedules_acp_ledger_anchor_x402_group_sponsor_hooks_guard.py`](../../tests/test_ucp_split_schedules_acp_ledger_anchor_x402_group_sponsor_hooks_guard.py)（全仓库 **749/749** 单测通过）
  - 双语架构章节：[`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md` (§173)](2026-10-18-agentic-commerce-full-stack-architecture.md) ⇄ [`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.en.md` (§173)](2026-10-18-agentic-commerce-full-stack-architecture.en.md)

---

## Stage 175：16 场景（`SP-01..SP-16`）中英双语 7-Card 4:5 视觉基准评测报告（覆盖 Stage 174）

- **新增代码与双语报告资产**：
  - 基准套件：[`lab/ucp_split_schedules_acp_ledger_anchor_x402_group_sponsor_hooks_bench.py`](../../lab/ucp_split_schedules_acp_ledger_anchor_x402_group_sponsor_hooks_bench.py)
  - 单元测试：[`tests/test_ucp_split_schedules_acp_ledger_anchor_x402_group_sponsor_hooks_bench.py`](../../tests/test_ucp_split_schedules_acp_ledger_anchor_x402_group_sponsor_hooks_bench.py)（全仓库 **750/750** 单测通过）
  - 双语 7-Card 4:5 报告：[`reports/agentic-commerce-ucp-split-schedules-acp-ledger-anchor-x402-group-sponsor-hooks-bench/index.html`（中文）](../../reports/agentic-commerce-ucp-split-schedules-acp-ledger-anchor-x402-group-sponsor-hooks-bench/index.html) ⇄ [`index.en.html`（English）](../../reports/agentic-commerce-ucp-split-schedules-acp-ledger-anchor-x402-group-sponsor-hooks-bench/index.en.html) ⇄ [`report.json`](../../reports/agentic-commerce-ucp-split-schedules-acp-ledger-anchor-x402-group-sponsor-hooks-bench/report.json)

---

## Stage 176：UCP 目录相似检索（`like[]` 锚点自排除与全未解析空集阻断）及替品发现（`include: ["substitutes"]` 缺省即未提供、禁含被替换变体自身，PR `#974`）、餐饮单店结账与履约（`dev.ucp.food.checkout` 单店作用域、单数 `destination`、菜品加料 `quantity >= 1` 与小费守恒，PR `#897`）、位置无关企业身份（`dev.ucp.common.business`，PR `#939`）与方括号 JSONPath（PR `#774`）、以及 AP2 结账后行为记录检查点周期上限与 `window_anchor="uncertified"` 防盲视绕过（Issue `#290` `trail-head-ref-v1.md`）确定性护栏

- **新增代码与双语文档资产**：
  - 护栏模块：[`lab/ucp_catalog_similarity_food_checkout_business_id_ap2_trail_head_guard.py`](../../lab/ucp_catalog_similarity_food_checkout_business_id_ap2_trail_head_guard.py)
  - 单元测试：[`tests/test_ucp_catalog_similarity_food_checkout_business_id_ap2_trail_head_guard.py`](../../tests/test_ucp_catalog_similarity_food_checkout_business_id_ap2_trail_head_guard.py)（全仓库 **753/753** 单测通过）
  - 双语架构章节：[`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md` (§175)](2026-10-18-agentic-commerce-full-stack-architecture.md) ⇄ [`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.en.md` (§175)](2026-10-18-agentic-commerce-full-stack-architecture.en.md)

---

## Stage 177：16 场景（`CF-01..CF-16`）中英双语 7-Card 4:5 视觉基准评测报告（覆盖 Stage 176）

- **新增代码与双语报告资产**：
  - 基准套件：[`lab/ucp_catalog_similarity_food_checkout_business_id_ap2_trail_head_bench.py`](../../lab/ucp_catalog_similarity_food_checkout_business_id_ap2_trail_head_bench.py)
  - 单元测试：[`tests/test_ucp_catalog_similarity_food_checkout_business_id_ap2_trail_head_bench.py`](../../tests/test_ucp_catalog_similarity_food_checkout_business_id_ap2_trail_head_bench.py)（全仓库 **754/754** 单测通过）
  - 双语 7-Card 4:5 报告：[`reports/agentic-commerce-ucp-catalog-similarity-food-checkout-business-id-ap2-trail-head-bench/index.html`（中文）](../../reports/agentic-commerce-ucp-catalog-similarity-food-checkout-business-id-ap2-trail-head-bench/index.html) ⇄ [`index.en.html`（English）](../../reports/agentic-commerce-ucp-catalog-similarity-food-checkout-business-id-ap2-trail-head-bench/index.en.html) ⇄ [`report.json`](../../reports/agentic-commerce-ucp-catalog-similarity-food-checkout-business-id-ap2-trail-head-bench/report.json)

---

## Stage 178：UCP 订单 MCP 绑定签名（PR `#988`）、订单支付工具只读子集（PR `#584`）与参与者标识符澄清（PR `#791`）、x402 评价扩展（PR `#3656`）、结算覆盖上限（PR `#3881`/`#3877`）、EIP-3009 Low-s 验签（PR `#2728`）、402 JSON 错误体与 Python MCP 付费响应回调（PR `#3883`/`#3508`）及 MCP `SEP-3415` 事件扩展 `Mcp-Name` 与每订阅 `eventId` 去重护栏（`b0efd11`/`2ec39b9`）

- **新增代码与双语文档资产**：
  - 确定性护栏模块：[`lab/ucp_order_mcp_signing_payment_instruments_x402_reviews_override_ceiling_mcp_events_guard.py`](../../lab/ucp_order_mcp_signing_payment_instruments_x402_reviews_override_ceiling_mcp_events_guard.py)
  - 单元测试：[`tests/test_ucp_order_mcp_signing_payment_instruments_x402_reviews_override_ceiling_mcp_events_guard.py`](../../tests/test_ucp_order_mcp_signing_payment_instruments_x402_reviews_override_ceiling_mcp_events_guard.py)（全仓库 **757/757** 单测通过）
  - 双语架构章节：[`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md` (§177)](2026-10-18-agentic-commerce-full-stack-architecture.md) ⇄ [`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.en.md` (§177)](2026-10-18-agentic-commerce-full-stack-architecture.en.md)

---

## Stage 179：16 场景（`OM-01..OM-16`）中英双语 7-Card 4:5 视觉基准评测报告（覆盖 Stage 178）

- **新增代码与双语报告资产**：
  - 基准套件：[`lab/ucp_order_mcp_signing_payment_instruments_x402_reviews_override_ceiling_mcp_events_bench.py`](../../lab/ucp_order_mcp_signing_payment_instruments_x402_reviews_override_ceiling_mcp_events_bench.py)
  - 单元测试：[`tests/test_ucp_order_mcp_signing_payment_instruments_x402_reviews_override_ceiling_mcp_events_bench.py`](../../tests/test_ucp_order_mcp_signing_payment_instruments_x402_reviews_override_ceiling_mcp_events_bench.py)（全仓库 **758/758** 单测通过）
  - 双语 7-Card 4:5 报告：[`reports/agentic-commerce-ucp-order-mcp-signing-payment-instruments-x402-reviews-override-ceiling-mcp-events-bench/index.html`（中文）](../../reports/agentic-commerce-ucp-order-mcp-signing-payment-instruments-x402-reviews-override-ceiling-mcp-events-bench/index.html) ⇄ [`index.en.html`（English）](../../reports/agentic-commerce-ucp-order-mcp-signing-payment-instruments-x402-reviews-override-ceiling-mcp-events-bench/index.en.html) ⇄ [`report.json`](../../reports/agentic-commerce-ucp-order-mcp-signing-payment-instruments-x402-reviews-override-ceiling-mcp-events-bench/report.json)

---

## Stage 180：MCP 变更型 `tools/call` 丢失响应（`LOST_ACK`）派发前逻辑操作日志与权威回读对账（Issue `#3394`）、惰性加载服务端路由描述与独立 `routing_metadata_digest` 防跨工具劫持（Issue `#3430`）、Sierra $\tau$-bench 2.0 `loan_servicing` 英法双语不变量与未评分试验过滤（PR `#638` `ce55fda` & Issue `#678`）及 UCP `TokenCredential` 上下文透传与公益捐赠多主体拆账（PR `#792` & Issue `#924`）确定性护栏

- **新增代码与双语文档资产**：
  - 确定性护栏模块：[`lab/mcp_lost_response_retry_routing_digest_tau2_loan_servicing_ucp_token_context_donations_guard.py`](../../lab/mcp_lost_response_retry_routing_digest_tau2_loan_servicing_ucp_token_context_donations_guard.py)
  - 单元测试：[`tests/test_mcp_lost_response_retry_routing_digest_tau2_loan_servicing_ucp_token_context_donations_guard.py`](../../tests/test_mcp_lost_response_retry_routing_digest_tau2_loan_servicing_ucp_token_context_donations_guard.py)（全仓库 **762/762** 单测通过）
  - 双语架构章节：[`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md` (§179)](2026-10-18-agentic-commerce-full-stack-architecture.md) ⇄ [`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.en.md` (§179)](2026-10-18-agentic-commerce-full-stack-architecture.en.md)

---

## Stage 181：16 场景（`LR-01..LR-16`）中英双语 7-Card 4:5 视觉基准评测报告（覆盖 Stage 180）

- **新增代码与双语报告资产**：
  - 基准套件：[`lab/mcp_lost_response_retry_routing_digest_tau2_loan_servicing_ucp_token_context_donations_bench.py`](../../lab/mcp_lost_response_retry_routing_digest_tau2_loan_servicing_ucp_token_context_donations_bench.py)
  - 单元测试：[`tests/test_mcp_lost_response_retry_routing_digest_tau2_loan_servicing_ucp_token_context_donations_bench.py`](../../tests/test_mcp_lost_response_retry_routing_digest_tau2_loan_servicing_ucp_token_context_donations_bench.py)（全仓库 **763/763** 单测通过）
  - 双语 7-Card 4:5 报告：[`reports/agentic-commerce-mcp-lost-response-retry-routing-digest-tau2-loan-servicing-ucp-token-context-donations-bench/index.html`（中文）](../../reports/agentic-commerce-mcp-lost-response-retry-routing-digest-tau2-loan-servicing-ucp-token-context-donations-bench/index.html) ⇄ [`index.en.html`（English）](../../reports/agentic-commerce-mcp-lost-response-retry-routing-digest-tau2-loan-servicing-ucp-token-context-donations-bench/index.en.html) ⇄ [`report.json`](../../reports/agentic-commerce-mcp-lost-response-retry-routing-digest-tau2-loan-servicing-ucp-token-context-donations-bench/report.json)

---

## Stage 182：Google AP2 自包含拒付证据包与密钥来源分类及 OpenTimestamps 重建窗口（Issue `#338`）、UCP 本地服务预约 TTL 锁位与支付可观测原子契约及担保扣款（Issue `#922` / PTC `#53` / STC `#51`）、Permalink 显式买家合并动作防 CSRF（PR `#789`）及反向域名风险信号与 B2B 采购审批（Issue `#630` & `#947`）确定性护栏

- **新增代码与双语文档资产**：
  - 确定性护栏模块：[`lab/ap2_dispute_evidence_pack_ucp_local_services_permalink_csrf_risk_signals_b2b_guard.py`](../../lab/ap2_dispute_evidence_pack_ucp_local_services_permalink_csrf_risk_signals_b2b_guard.py)
  - 单元测试：[`tests/test_ap2_dispute_evidence_pack_ucp_local_services_permalink_csrf_risk_signals_b2b_guard.py`](../../tests/test_ap2_dispute_evidence_pack_ucp_local_services_permalink_csrf_risk_signals_b2b_guard.py)（全仓库 **766/766** 单测通过）
  - 双语架构章节：[`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md` (§181)](2026-10-18-agentic-commerce-full-stack-architecture.md) ⇄ [`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.en.md` (§181)](2026-10-18-agentic-commerce-full-stack-architecture.en.md)

---

## Stage 183：16 场景（`DS-01..DS-16`）中英双语 7-Card 4:5 视觉基准评测报告（覆盖 Stage 182）

- **新增代码与双语报告资产**：
  - 基准套件：[`lab/ap2_dispute_evidence_pack_ucp_local_services_permalink_csrf_risk_signals_b2b_bench.py`](../../lab/ap2_dispute_evidence_pack_ucp_local_services_permalink_csrf_risk_signals_b2b_bench.py)
  - 单元测试：[`tests/test_ap2_dispute_evidence_pack_ucp_local_services_permalink_csrf_risk_signals_b2b_bench.py`](../../tests/test_ap2_dispute_evidence_pack_ucp_local_services_permalink_csrf_risk_signals_b2b_bench.py)（全仓库 **767/767** 单测通过）
  - 双语 7-Card 4:5 报告：[`reports/agentic-commerce-ap2-dispute-evidence-pack-ucp-local-services-permalink-csrf-risk-signals-b2b-bench/index.html`（中文）](../../reports/agentic-commerce-ap2-dispute-evidence-pack-ucp-local-services-permalink-csrf-risk-signals-b2b-bench/index.html) ⇄ [`index.en.html`（English）](../../reports/agentic-commerce-ap2-dispute-evidence-pack-ucp-local-services-permalink-csrf-risk-signals-b2b-bench/index.en.html) ⇄ [`report.json`](../../reports/agentic-commerce-ap2-dispute-evidence-pack-ucp-local-services-permalink-csrf-risk-signals-b2b-bench/report.json)

---

## Stage 184：Google UCP AP2 `ES512`/`P-521` 结账 JWS 算法绑定与 HTTP 签名回退（PR `#618`）、MCP Streamable HTTP 版本优先错误优先级（`#3449`）与 MRTR 反向域名扩展（`#2919`）及客户端 RFC 8785 工具定义摘要固定（`#1766`）、以及 x402 `solidarity` 人道主义份额扩展与 RFC 6962 默克尔树批次证明（PR `#419`）确定性护栏

- **新增代码与双语文档资产**：
  - 确定性护栏模块：[`lab/ucp_ap2_es512_alg_binding_mcp_http_version_precedence_mrtr_x402_solidarity_guard.py`](../../lab/ucp_ap2_es512_alg_binding_mcp_http_version_precedence_mrtr_x402_solidarity_guard.py)
  - 单元测试：[`tests/test_ucp_ap2_es512_alg_binding_mcp_http_version_precedence_mrtr_x402_solidarity_guard.py`](../../tests/test_ucp_ap2_es512_alg_binding_mcp_http_version_precedence_mrtr_x402_solidarity_guard.py)（全仓库 **770/770** 单测通过）
  - 双语架构章节：[`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md` (§183)](2026-10-18-agentic-commerce-full-stack-architecture.md) ⇄ [`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.en.md` (§183)](2026-10-18-agentic-commerce-full-stack-architecture.en.md)

---

## Stage 185：16 场景（`ES-01..ES-16`）中英双语 7-Card 4:5 视觉基准评测报告（覆盖 Stage 184）

- **新增代码与双语报告资产**：
  - 基准套件：[`lab/ucp_ap2_es512_alg_binding_mcp_http_version_precedence_mrtr_x402_solidarity_bench.py`](../../lab/ucp_ap2_es512_alg_binding_mcp_http_version_precedence_mrtr_x402_solidarity_bench.py)
  - 单元测试：[`tests/test_ucp_ap2_es512_alg_binding_mcp_http_version_precedence_mrtr_x402_solidarity_bench.py`](../../tests/test_ucp_ap2_es512_alg_binding_mcp_http_version_precedence_mrtr_x402_solidarity_bench.py)（全仓库 **771/771** 单测通过）
  - 双语 7-Card 4:5 报告：[`reports/agentic-commerce-ucp-ap2-es512-alg-binding-mcp-http-version-precedence-mrtr-x402-solidarity-bench/index.html`（中文）](../../reports/agentic-commerce-ucp-ap2-es512-alg-binding-mcp-http-version-precedence-mrtr-x402-solidarity-bench/index.html) ⇄ [`index.en.html`（English）](../../reports/agentic-commerce-ucp-ap2-es512-alg-binding-mcp-http-version-precedence-mrtr-x402-solidarity-bench/index.en.html) ⇄ [`report.json`](../../reports/agentic-commerce-ucp-ap2-es512-alg-binding-mcp-http-version-precedence-mrtr-x402-solidarity-bench/report.json)







