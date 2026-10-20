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
