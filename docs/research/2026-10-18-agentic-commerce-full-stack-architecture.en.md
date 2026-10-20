# Agentic Commerce Full-Stack AI-Native Reference Architecture — English Reference & Stage 1–54 Matrix

🌐 **Language / 语言导航**: **[Bilingual Master Blueprint (`2026-10-18-agentic-commerce-full-stack-architecture.md`)](2026-10-18-agentic-commerce-full-stack-architecture.md)** | **English Architecture Guide (Current)** | **[中文首页 (`README.md`)](../../README.md)** | **[English Home (`README.en.md`)](../../README.en.md)**

---

## 1. Dialectical Thesis: Why Cloud Well-Architected & Classic 3-Tier Web Architectures Fail for Agentic Commerce

Cloud Hyperscaler **Well-Architected Frameworks (WAF)** and classic **3-Tier Web Architectures (Presentation → Stateless App Tier → Shared Database)** rely on three foundational assumptions that collapse when autonomous AI Agents transact across organizational boundaries:

1. **Human-in-the-Browser vs. Delegated Non-Deterministic Principal**: A 3-tier web app assumes a human visually inspects the DOM and clicks "Pay" over a first-party session cookie. In Agentic Commerce, an LLM agent acts on delegated authority and is vulnerable to indirect prompt injection, catalog bait-and-switch, and hallucinated parameters. Authorization must therefore move out of the model loop into a **Deterministic Fiduciary Control Plane** backed by hardware/cryptographic mandates (`Google AP2 SD-JWT+kb`, `Stripe SPT`, `Visa TAP RFC 9421`, `Poppy v0.2 DPoP`).
2. **Request/Response CRUD vs. Multi-Party Financial & Token-Burn Conservation**: In a Web App, an HTTP 500 or retry is an operational metric; in Agentic Commerce, LLM reasoning tokens (`stripe-token-billing`) + payment rail fees (`SPT` / `x402` / `MPP Tempo`) can exceed the gross margin of a transaction, and multi-seller splits or sub-cent streaming tails can break ledger conservation unless enforced by an **Atomic Settlement & FinOps Circuit Breaker**.
3. **Internal Logs vs. Cross-Boundary Cryptographic Non-Repudiation**: When an issuer raises a `Visa CE 3.0 (10.4 / 13.3)` or `Mastercard (4837 / 4853)` dispute, internal application logs are inadmissible (`self_asserted_only`). An AI-Native workload must compile verifiable 4-pillar cryptographic evidence packs (`ACP PR #316 ATDRP-0.1`, RFC 3161 timestamps, RFC 9530 `Content-Digest` raw-byte hashes, and RFC 8785 JCS canonicalization).

| Architectural Plane | Classic 3-Tier Web / Cloud WAF Assumption | Agentic Commerce AI-Native Workload Requirement | Primary Protocol & Repo Guard Modules |
|---|---|---|---|
| **Plane 1: Edge & Agent Identity** | TLS + WAF IP rate-limiting + OAuth Bearer token | RFC 9421 HTTP Message Signatures (`@signature-params`), `<= 60s` window, verify-before-recording nonce, Hybrid PQ (`ed25519-ml-dsa-65`), Principal DID anti-scalping quotas | `Visa TAP (#18, #21)`, `UCP (#659, #699, #963)`, `Poppy v0.2 (#71)`, `lab/agent_identity_attestation_guard.py` |
| **Plane 2: Catalog & Discovery Integrity** | Search index / CDN JSON response trusted by UI | RFC 9530 raw-byte `Content-Digest`, `dev.ucp.common.feed` shard digest barrier, relational `purpose`/`reference_ids` self-exclusion, `seller.logo` non-authority rule | `UCP (#866, #902, #917, #962, #974, #977, #982)`, `ACP (#223, #260)`, `lab/ucp_ap2_token_issuance_catalog_purpose_acp_upi_circle_tap_rfc9421_guard.py` |
| **Plane 3: Fiduciary Policy & UI Isolation** | Prompt instructions / React frontend confirmation | Out-of-band Policy Broker (`summary == terms`), A2UI declarative surfaces stripped from LLM `content[]`, Sierra $\tau$-bench 2.0.0 `intake` consent & turn-separation gates | `Poppy v0.2 (#35, #51, #70, #71)`, `UCP (#899)`, `ACP (#314)`, `Sierra tau2-bench 2.0.0 (#642)` |
| **Plane 4: Cryptographic Mandates & Tokenization** | Long-lived merchant API keys / saved card-on-file | Google AP2 `SD-JWT+kb` (`expected_aud` on `kb+sd-jwt+kb`, `open_mandate_hash` RFC 8785 JCS, `>= 128b` `checkout_hash`), UCP `/tokenize` non-reversible tokens, Stripe SPT single-use resolve | `Google AP2 (#278, #279, #368, #369, #377, #383, #384, #385)`, `UCP (#916)`, `Stripe SPT` |
| **Plane 5: Multi-Rail Atomic Settlement & FinOps** | Single PSP synchronous charge | Multi-seller Connect split conservation, Two-Phase Booking Hold Saga, `x402` EIP-3009 / Solana & Base USDC (`HTTP 402`), `MPP Tempo` streaming sessions, Razorpay UPI Circle | `Visa TAP (#11)`, `ACP (#216, #217, #218)`, `UCP (#816, #862, #976)`, `lab/cross_border_b2b_guard.py` |
| **Plane 6: Dispute Non-Repudiation & Lifecycle** | Manual ticket support & mutable DB rows | ACP `ATDRP-0.1` (`#316`) 17-gateway CE 3.0 evidence compiler, UCP cancel-first `lookup` + tombstone `fence` (`#945`), consultation `proposal_digest` (`#946`), GDPR crypto-shredding | `ACP (#316)`, `UCP (#945, #946, #966, #979)`, `lab/dispute_evidence_replay.py`, `lab/acp_atdrp_dispute_signature_deep_links_visa_tap_pq_guard.py` |

---

## 2. Consolidated Index of Architectural Sections (§1–§53)

All 53 sections in [`docs/research/2026-10-18-agentic-commerce-full-stack-architecture.md`](2026-10-18-agentic-commerce-full-stack-architecture.md) are written with complete English technical specifications (and bilingual Chinese + English headings/explanations from §53 onward):

- **§1–§19 (Stages 1–13)**: 6-Plane AI-Native Benchmark, Cross-Border B2B Split & Incoterms (`DDP`/HS6), 17-Gateway CE 3.0 Dispute Evidence Compiler, Enterprise Cutover Workbench (`2026-11-30` Stripe MCP deadline), Multi-Leg Booking Hold Saga & SFTP Reconciliation, RFC 9421 Identity Attestation, 7-Gate Unified Checkout Pipeline, Recurring Mandate `TCCV` Guard, B2B 3-Way Match (`PO == GRN == Invoice`), Sealed Vickrey RFQ, Split-Tender FinOps, and `x402` Finality/Peg Guard.
- **§20–§38 (Stages 14–32)**: Marketplace Rolling Reserve & Clawback, FX Treasury Netting & ISO 20022 `pacs.008`, Green Logistics CBAM & Cold-Chain MKT Escrow, ZK Eligibility (`SD-JWT`) & PCI-DSS v4.0.1 Redaction + GDPR Crypto-Shredding, Subscription Metering & FTC Click-to-Cancel, Loyalty Promo Anti-Arbitrage, Embedded BNPL & Parametric Insurance, EU ESPR Digital Product Passports, Agentic Auctions, Digital Goods DRM & C2PA Royalties, Healthcare FSA/HSA SIGIS IIAS & HIPAA, EV ISO 15118 V2G & DePIN GPU Goodput, MLETR Electronic Bills of Lading & eUCP 600, RTB Ad-Fraud SIVT & Sovereign Compute Geofencing, B2B Milestone Retainage & Tax Withholding, Weather Derivatives & `pain.008`, Commercial Real Estate CAM & Autonomous Fleet Escrow, Construction AIA G702 Lien Waivers & IOLTA Trust, and Aviation IATA NDC EU261 & 5G uRLLC Slice SLA.
- **§39–§52 (Stages 33–53)**: mBridge Wholesale CBDC PvP & Poppy `v0.2`, UCP Post-Order Modification (`#945`/`#946`), Catalog Substitutes vs Search (`#974`), Food Allergen Fail-Closed (`#964`), Declarative A2UI Isolation (`#899`), Time-Bound Quotes (`#930`), Return Policy Explicit Eligibility (`#966`), Capability Webhooks (`#938`), Nested Bundle Conservation (`#976`), AP2 Token Issuance (`#916`), Payment Finality (`#816`), Guest Order Access Credentials (`#848`), `platform_reference` Immutability (`#839`), Standardized Fulfillment Events (`#979`), Catalog Similarity (`#977`), Nano `XNO` Binding (`#862`), ACP `ATDRP-0.1` (`#316`), Visa TAP Hybrid Post-Quantum `ed25519-ml-dsa-65` (`#18`/`#21`), UCP Address Line Components (`#981`), Identity-Linking Selection (`#980`), ACP `mcpToolGate` (`#314`), and Razorpay UPI Circle (`#216`).
- **§53 (Stage 54 — Bilingual Chinese + English)**:
  - **§53.1**: UCP `ucp-schema 2.0.0` Bundled `$ref` Restoration (`#982`) & Variant `seller.logo` Non-Authority (`#962`).
  - **§53.2**: ACP JSON Schema ↔ OpenAPI Property Drift Detector (`#310`) & `allOf` + `additionalProperties: false` Sibling Starvation Guard (`#290`, `#284`, `#275`).
  - **§53.3**: Google AP2 `kb+sd-jwt+kb` Terminal Audience Enforcement (`#369`), `cnf.jwk` JSON-Mode Serialization (`#385`/`#383`), `verify_receipt` Callback Safety (`#384`) & Poppy `v0.2` (`#71`, `39b35bd`).
  - **§53.4**: Sierra $\tau$-bench 2.0.0 (`#642`, `989d328`) Outbound `intake` (`τ-entity`) Policy & Visa TAP `x402` USDC on Solana/Base Checkout (`#11`).
- **§54 (Stage 55 — Bilingual Chinese + English)**:
  - **16-Scenario Bilingual 7-Card 4:5 Benchmark Suite (`SD-01..SD-16`)**: `lab/ucp_schema_acp_drift_ap2_aud_tau2_intake_bench.py` (`16/16 100.0%` AI-Native vs. `1/16 6.2%` Classic 3-Tier, `0.41 ms` vs. `2.09 ms`, `5.1x` speedup, published as `index.html` [CN] and `index.en.html` [EN]).
- **§55 (Stage 56 — Bilingual Chinese + English)**:
  - **§55.1**: UCP RFC 9728/8414 Multi-Entry Identity Discovery (`#891`), Fulfillment `options[].totals` Array (`#573`) & Checkout Status Lifecycle (`#672`).
  - **§55.2**: UCP Mercado Pago Pix Out-of-Band `render_artifact` Action (`#635`) & Razorpay Magic `hosted_checkout` Instrument/Credential (`#316`).
  - **§55.3**: ACP Delegate Authentication `Signature` Requirement (`#287`), `CheckoutSessionCreateRequest` Conformance (`#289`) & Unwrapped `delegate_payment` Error Envelope (`#266`/`#243`).
  - **§55.4**: Sierra $\tau$-bench 2.0 Boréal Finance `loan_servicing` (`en`/`fr`, `#638`) Policy & `banking_knowledge` `canonicalize_time_verified` (`#634`).
- **§56 (Stage 57 — Bilingual Chinese + English)**:
  - **16-Scenario Bilingual 7-Card 4:5 Benchmark Suite (`RP-01..RP-16`)**: `lab/ucp_rfc9728_pix_razorpay_acp_envelope_tau2_loan_bench.py` (`16/16 100.0%` AI-Native vs. `1/16 6.2%` Classic 3-Tier, `0.38 ms` vs. `2.06 ms`, `5.4x` speedup, published as `index.html` [CN] and `index.en.html` [EN]).
- **§57 (Stage 58 — Bilingual Chinese + English)**:
  - **§57.1**: UCP Purchase Options Extension (`#901`), Per-Seller Catalog `offers[]` Attribution (`#811`), HTTP `304 Not Modified` Conditional Cache (`#933`) & MCP `$defs/agent` (`#831`).
  - **§57.2**: ACP Checkout `Item.url` Cross-Brand Disambiguation (`#281`), Agent-Hosted Feed Origin & `minItems: 1` Bounds (`#256`) & `UpsertProductsResponse` (`#241`).
  - **§57.3**: Google AP2 Multi-Hop `~~` `MandateClient.present()` Isolation (`#363`), Mandatory `checkout_hash` Derivation (`#359`) & Atomic Consume-Once Reservation (`#347`).
  - **§57.4**: Sierra $\tau$-bench 2.0 6-Language `voice-v2-banking` / `voice-v2-entity` (`#637`), Crossed Pass³ `voice-v2-rcs-v3` Seeds (`#639`) & Judged Submission Gate (`#620`).
- **§58 (Stage 59 — Bilingual Chinese + English)**:
  - **16-Scenario Bilingual 7-Card 4:5 Benchmark Suite (`PO-01..PO-16`)**: `lab/ucp_purchase_options_offers_acp_feed_ap2_multihop_tau2_voice_bench.py` (`16/16 100.0%` AI-Native vs. `1/16 6.25%` Classic 3-Tier, `0.36 ms` vs. `4.595 ms`, `12.6x` speedup, published as `index.html` [CN] and `index.en.html` [EN]).
- **§59 (Stage 60 — Bilingual Chinese + English)**:
  - **§59.1**: UCP Root-Array Anti-Pattern (`#948`), Order Directional Annotation Hygiene (`#903`), Conformance Corpus Export (`#900`), Vendor Namespace Self-Hosting (`#882`) & Auth-Gated Stored User State (`#869`).
  - **§59.2**: ACP Checkout Request `LineItem` Reference Alignment (`#270`), Flat `DelegateAuthenticationSessionWithResult` Schema (`#261`) & Inline/Embedded Example Validators (`#254`, `#252`).
  - **§59.3**: Google AP2 Exact Versioned `.1` VCT Constants (`#349`), `PaymentInstrument` Extension Preservation (`#333`/`#329`), `~~` Multi-Hop dSD-JWT Chain Decoder (`#351`), EC/JWK Receipt Verification (`#365`) & Payment Log Redaction (`#364`).
  - **§59.4**: Sierra $\tau$-bench 2.0 Voice Design API Units (`guidance_scale=5`, `#636`), Unpinned `voice_design/<lang>.yaml` (`#619`), Inline Text-Matrix `results.json` Trial Counting (`#616`) & Telecom `RewardType.ACTION` Ground Truth / Bounded Repair (`#645`, `#632`).
- **§60 (Stage 61 — Bilingual Chinese + English)**:
  - **16-Scenario Bilingual 7-Card 4:5 Benchmark Suite (`RA-01..RA-16`)**: `lab/ucp_root_array_order_acp_lineitem_ap2_vct_tau2_voice_design_bench.py` (`16/16 100.0%` AI-Native vs. `1/16 6.25%` Classic 3-Tier, `0.35 ms` vs. `4.595 ms`, `13.1x` speedup, published as `index.html` [CN] and `index.en.html` [EN]).
- **§61 (Stage 62 — Bilingual Chinese + English)**:
  - **§61.1**: UCP Cart Completion `cart_id` Omission (`#911`/`#871`), Cart Conversion `line_items` Requirement (`#910`), `UCP-Agent` Signature Coverage (`#907`), OpenRPC Auth `type` Required (`#906`), MCP `complete_checkout` Extensions (`#883`) & Normative Requirements Extractor (`#853`).
  - **§61.2**: ACP Delegate Payment Optional `checkout_session_id` (`#230`), Forward-Compatible Error Enums (`#161`), Store BOPIS Extension (`#171`), Time-Bound Line-Item Offer Expiry (`#165`) & Digital vs. Physical Order Status Semantics (`#162`).
  - **§61.3**: Google AP2 Closed Checkout Binding in `PaymentMandateChain.verify()` (`#330`), x402 PSP Missing Key Fail-Closed (`#310`), x402 Verified Mandate Amount Authorization (`#300`) & TrustBoost PII Sanitization (`#267`).
  - **§61.4**: Sierra $\tau$-bench 2.0 Active Telecom Line `refuel_data` Guard (`#611`), Live-DB Grading & `ToolFault` Injection (`#609`/`#610`), Language-Binding Task Replacement Verification (`#615`) & Bridged GPT-5 `tool_choice` Preservation (`#621`).
- **§62 (Stage 63 — Bilingual Chinese + English)**:
  - **16-Scenario Bilingual 7-Card 4:5 Benchmark Suite (`CC-01..CC-16`)**: `lab/ucp_cart_complete_acp_store_offer_ap2_x402_tau2_telecom_bench.py` (`16/16 100.0%` AI-Native vs. `1/16 6.25%` Classic 3-Tier, `0.35 ms` vs. `4.605 ms`, `13.2x` speedup, published as `index.html` [CN] and `index.en.html` [EN]).
- **§63 (Stage 64 — Bilingual Chinese + English)**:
  - **§63.1**: UCP Service `schema` Transport Definition Polymorphism (`#833`), Reserved `ucp_` Prefix `W007` (`#831`), Payment Handler Participant Identifier (`#791`), Permalink CSRF Cart Merge Guard (`#789`) & WBA `signature-agent` Coverage (`#785`).
  - **§63.2**: ACP Stripe Link Accelerated Wallet Handler (`com.stripe.link`, `#156`), Wallet Intervention Flows (`redirect`/`webview`/`otp`, `#150`), All 11 Session States (`#144`), On-Chain Eligibility Discount (`#166`) & Intent Traces (`#151`).
  - **§63.3**: Google AP2 Cross-Merchant Atomic Budget Authority (`#252`), Solana Pay Single-Use Reference Pubkey Binding (`#228`) & AP2-Haggle Multi-Round Negotiation (`#229`).
  - **§63.4**: Sierra $\tau$-bench 2.0 Incomplete Gold DB State Withdrawal (`#580`), NL-Judge Verdict Count & Contentless Turn Filtering (`#581`/`#584`), Separate `evaluator_cost` Accounting (`#593`), Telecom `check_status_bar` Grounding (`#600`) & Sandbox `srt` `SIGTERM` Cleanup (`#588`).
- **§64 (Stage 65 — Bilingual Chinese + English)**:
  - **16-Scenario Bilingual 7-Card 4:5 Benchmark Suite (`SL-01..SL-16`)**: `lab/ucp_service_schema_acp_link_intervention_ap2_budget_tau2_nl_bench.py` (`16/16 100.0%` AI-Native vs. `4/16 25.0%` Classic 3-Tier, `0.34 ms` vs. `4.63 ms`, `13.6x` speedup, published as `index.html` [CN] and `index.en.html` [EN]).
- **§65 (Stage 66 — Bilingual Chinese + English)**:
  - **§65.1**: UCP Permalink `ucp/version` Control Parameter (`#793`), `TokenCredential` `binding`/`identity` Context (`#792`), State-Bound Cart `Offer` in `actions` (`#773`), Terminal Cart `status` (`#740`), `action.ready` `maxProperties: 0` (`#730`), `digital_delivery` Order Pointer (`#719`) & OpenAPI 3.1 `securitySchemes` (`#716`).
  - **§65.2**: ACP `session_context` Telemetry Unification (`#238`), Embedded `app_links` Deep Links (`#237`), Post-Checkout 3-Field Order Alignment (`#232`) & Seller-Backed / `x402` Crypto Handlers (`#149`, `#114`, `#111`).
  - **§65.3**: Google AP2 `(type, id)` Allowed Payment Instrument Matching (`#301`), Versioned `delegate-SD-JWT` Golden Vectors (`#307`) & TypeScript/Zod Receipt `oneOf` Branch Invariants (`#305`, `#216`).
  - **§65.4**: Sierra $\tau$-bench 2.0 `###OUT-OF-SCOPE###` Abort Classification (`#548`), Fenced Markdown JSON NL-Judge Parsing (`#562`), Deferred Checkpoint Unlink (`#533`) & Banking `tasks.json` / Airline `user_id` / `campus` Domain Invariants (`#606`, `#602`, `#596`).
- **§66 (Stage 67 — Bilingual Chinese + English)**:
  - **16-Scenario Bilingual 7-Card 4:5 Benchmark Suite (`TO-01..TO-16`)**: `lab/ucp_token_context_cart_offer_acp_telemetry_ap2_instrument_tau2_abort_bench.py` (`16/16 100.0%` AI-Native vs. `4/16 25.0%` Classic 3-Tier, `0.34 ms` vs. `4.63 ms`, `13.6x` speedup, published as `index.html` [CN] and `index.en.html` [EN]).
- **§67 (Stage 68 — Bilingual Chinese + English)**:
  - **§67.1**: UCP OpenRPC `ec.auth`/`ep.cart.auth` Required `type` (`#802`), Catalog Discount Previews (`#715`), Generic SPT Handler (`#713`), `price_treatment.tax.inclusion` (`#691`), `event_feed`/`agent_hints` (`#673`) & Non-Empty `actions`/`policies.applies_to` (`#669`, `#661`).
  - **§67.2**: ACP `UpsertProductsResponse` (`#255`), Feed API & Promotions (`#190`, `#192`), `Item.suggested_price` (`#201`), Complete `fulfillment_details` (`#200`), Marketing Consent (`#199`) & Razorpay / Pre-Checkout Cart (`#215`, `#213`, `#188`).
  - **§67.3**: Google AP2 HNP Mandate Security Binding (`#202`, `#189`), W3C `DOMString` Currency Value (`#191`), `IntentMandate.budget` Ceiling (`#198`), Section 7.4 Fiduciary Circuit Breaker (`#187`, `#164`) & UPI Collect (`#139`).
  - **§67.4**: Sierra $\tau$-bench 2.0 Spoken & Chunked Voice Amount Recognition (`#582`), Safe `analyze_reward` Lookup (`#575`), Trajectory `replay_mismatches` (`#573`), Union/Paired Action Matching (`#569`, `#570`) & Retail Reference Integrity (`#571`, `#567`, `#566`).
- **§68 (Stage 69 — Bilingual Chinese + English)**:
  - **16-Scenario Bilingual 7-Card 4:5 Benchmark Suite (`OA-01..OA-16`)**: `lab/ucp_openrpc_auth_acp_feed_consent_ap2_hnp_fcb_tau2_voice_bench.py` (`16/16 100.0%` AI-Native vs. `4/16 25.0%` Classic 3-Tier, `0.34 ms` vs. `4.63 ms`, `13.6x` speedup, published as `index.html` [CN] and `index.en.html` [EN]).
- **§69 (Stage 70 — Bilingual Chinese + English)**:
  - **§69.1**: UCP Order Webhook Signing Gate (`#659`), Reserved `ucp` Namespace & `map_order` (`#658`, `#657`), Response-Carried `request_constraints` (`#655`, `#626`) & Sale-Basis Step Quantities (`#653`, `#642`, `#622`, `#596`).
  - **§69.2**: ACP `protocol.extensions` Relocation (`#178`), Per-Line-Item `valid_until` Offer Expiry (`#165`), `Merchant-Signature` Replay Protection (`#160`), 11 Session States & Digital Order Status (`#144`, `#162`, `#161`) & MCP Transport Binding (`#139`, `#130`, `#125`).
  - **§69.3**: Google AP2 `FailureResponse` Taxonomy (`#131`, `#132`), Section 7.1 `PaymentReceipt` & Mandate JSON Schemas (`#110`, `#128`, `#92`), Verifiable Intent 3-Hop Chain (`#144`) & Micropayment Channels (`#83`).
  - **§69.4**: Sierra $\tau$-bench 2.0 OpenAI Live Interruption Signals (`#528`), Result-Safe Hallucination Retries (`#520`), Pydantic Tool Kwargs Coercion (`#516`, `#513`), `llm_agent_solo_gt` Replay (`#508`), `pass^k` Infra-Error Denominator (`#498`) & Fixed Closure Reasons (`#484`).
- **§70 (Stage 71 — Bilingual Chinese + English)**:
  - **16-Scenario Bilingual 7-Card 4:5 Benchmark Suite (`WS-01..WS-16`)**: `lab/ucp_webhook_signing_acp_session_states_ap2_failure_micropay_tau2_solo_bench.py` (`16/16 100.0%` AI-Native vs. `4/16 25.0%` Classic 3-Tier, `0.34 ms` vs. `4.62 ms`, `13.6x` speedup, published as `index.html` [CN] and `index.en.html` [EN]).





