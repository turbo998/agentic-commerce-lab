# 2026-10-27 Agentic Commerce Daily Research Report (Executive & Protocol Audit Edition)

🌐 **Language / 语言导航**: **[中文 (`2026-10-27-daily-research.md`)](2026-10-27-daily-research.md)** | **English (Current)** | **[Web IQ Architecture & Demo (`2026-10-26-webiq-agentic-commerce-demo.en.md`)](2026-10-26-webiq-agentic-commerce-demo.en.md)** | **[Stage Archive Index (`docs/stage-archive-index.md`)](../stage-archive-index.md)**

> ### 📌 Executive Summary & Core Findings
>
> - **4-Layer Architecture Convergence**: Consolidates **(1) Discovery & Grounding Layer (`Microsoft Web IQ`)**, **(2) Protocol State Machine Layer (`ACP + UCP`)**, **(3) Settlement & Trust Rail Layer (`AP2 + x402 + Visa TAP / MC Agent Pay`)**, and **(4) 7-Card 4:5 Evaluation Harness**.
> - **Primary-Source Protocol Updates Verified on 2026-10-27**:
>   1. **Sierra Poppy / Personal Agent Protocol Draft 0.3 (`#103`, `#106`, `#108`)**: Introduces pre-sign-in `auth.scope_hints` (`changes: "none" | "reversible" | "irreversible"`, `personal_data: true | false`) and RFC 8693 Token Exchange `invalid_target` validator checks.
>   2. **Universal Commerce Protocol (`ucp#982`)**: Fixes `ucp-schema 2.0.0` recursive `$ref` resolution across `allOf`/`oneOf`/`anyOf` union branches with `x-ucp-def-name` fallback labels.
>   3. **Stripe AI SDK & MCP Key Sunset Gate (`stripe/ai#586`, `#584`, `#581`)**: Verifies the `2026-11-30` Stripe MCP unscoped key deprecation deadline (34 days remaining from `2026-10-27`), remote MCP tool annotation forwarding, and fail-safe local skill cache preservation.
> - **Benchmark Metrics**: `18/18` (`100%`) normal checkout pass, `12/12` (`100%`) hidden DOM prompt-injection blocked, `0.0 pt` option-reversal drift, and `1.52s` vs `4.18s` parallel grounding latency (**`2.75x` speedup**). Historical stage cohorts are indexed in [`docs/stage-archive-index.md`](../stage-archive-index.md).

![Agentic Commerce 4-Layer Architecture](../../assets/svg/01-agentic-commerce-webiq-architecture.svg)

![Protocol Lifecycle Comparison Matrix](../../assets/svg/02-protocol-comparison-matrix.svg)

---

## 1. Public Source Monitoring & Normative Protocol Audit

| Protocol / Source | Status | 2026-10-27 Key Finding & Deterministic Guardrail |
|---|---|---|
| **Microsoft Web IQ (`api.microsoft.ai/v3`)** | ✅ Verified | Live merchant catalog grounding `P95 = 240ms`; DOM de-obfuscation & `100%` block rate (`12/12`) on hidden `<div style="display:none">` price tampering |
| **Sierra Poppy Draft 0.3 (`personal-agent-protocol`)** | ✅ Updated | Merged PRs `#103`/`#106`/`#108`: evaluates `auth.scope_hints` before OAuth sign-in (`changes: "irreversible"` escalates to user confirmation) + RFC 8693 `invalid_target` validation |
| **Google / Shopify UCP (`ucp#982`)** | ✅ Updated | Recursive `allOf`/`oneOf`/`anyOf` `$ref` resolution in `ucp-schema 2.0.0`, preserving loyalty lookup and split-payment union contracts |
| **OpenAI / Stripe ACP & Stripe MCP** | ✅ Verified | 5-State Checkout FSM (`DISCOVERED → GROUNDED → CART_LOCKED → MANDATE_SIGNED → SETTLED`); enforces `2026-11-30` sunset of unscoped `sk_live_*` keys |
| **Google AP2 (`MandateVC`) & x402** | ✅ Verified | W3C `MandateVC` binds cart SHA-256 digest & budget ceiling (`AP2_PRICE_CEILING_EXCEEDED` circuit breaker); HTTP 402 `x402` settles `0.002 USDC/call` |
| **Sierra $\tau$-bench 2.0 (`tau2-bench#691`)** | ✅ Updated | Hard output token cap on speech-fidelity LLM judge prompts and lazy-loading trajectory visualizer |

---

## 2. Architectural Comparison: Classic 3-Tier Web vs. 4-Layer Agentic Commerce

| Dimension | Classic 3-Tier Web Architecture (Browser → App → DB) | 4-Layer Deterministic Agentic Commerce (`Web IQ + ACP/UCP + AP2/x402`) |
|---|---|---|
| **Discovery & Anti-Injection** | Raw HTML scraping vulnerable to hidden DOM prompt injection and stale cached prices | **Web IQ Live Grounding + DOM Sanitizer**: Cross-checks visible DOM against JSON-LD offers and strips hidden adversarial nodes (`100%` block rate) |
| **Consent & Mandate Timing** | Assumes a human reads browser OAuth screens; treats scopes as coarse read/write strings | **Pre-Sign-In Scope Gating + `MandateVC`**: Enforces Poppy `auth.scope_hints` and AP2 cryptographic budget ceilings prior to execution |
| **Settlement Rails** | Manual browser checkout or static merchant API keys | **Multi-Rail Settlement**: Supports Stripe `SPT`, Visa TAP / MC Agent Pay network tokens, and `x402` machine micropayments (`0.002 USDC/call`) |

---

## 3. Deliverables & Archive Links

- **Interactive H5 Workbench**: [`live-demo.en.html`](../../live-demo.en.html) · [`live-demo.html`](../../live-demo.html)
- **7-Card 4:5 Benchmark Deck**: [`benchmark-cards.en.html`](../../benchmark-cards.en.html) · [`benchmark-cards.html`](../../benchmark-cards.html)
- **Core Engine Source**: [`lab/webiq_commerce_demo.py`](../../lab/webiq_commerce_demo.py) · [`src/agentic_commerce/webiq_demo_engine.py`](../../src/agentic_commerce/webiq_demo_engine.py)
- **Historical Stage Archive Index**: [`docs/stage-archive-index.md`](../stage-archive-index.md)
