# Enterprise Agentic Commerce Full-Stack Reference Architecture (English Guide)

🌐 **Language / 语言导航**: **[Full-Stack Technical Blueprint (`2026-10-18-agentic-commerce-full-stack-architecture.md`)](2026-10-18-agentic-commerce-full-stack-architecture.md)** | **English Architecture Guide (Current)** | **[SA Decision Catalog (`docs/index.en.md`)](../index.en.md)** | **[中文首页 (`README.md`)](../../README.md)** | **[English Home (`README.en.md`)](../../README.en.md)**

---

## 1. Architectural Thesis: Why Classic 3-Tier Web Architectures Fail for Agentic Commerce

Cloud **Well-Architected Frameworks (WAF)** and classic **3-Tier Web Architectures (Presentation → Stateless App Tier → Shared Database)** rely on three assumptions that break down when autonomous AI agents transact across organizational boundaries:

1. **Human-in-the-Browser vs. Delegated Non-Deterministic Principal**: A 3-tier web app assumes a human visually inspects the DOM and clicks "Pay" over a first-party session cookie. In Agentic Commerce, an LLM agent acts on delegated authority and is exposed to indirect prompt injection, catalog bait-and-switch, and hallucinated tool arguments. Authorization must move out of the LLM prompt loop into a **Deterministic Fiduciary Control Plane** backed by cryptographic mandates (`Google AP2 SD-JWT+kb`, `Stripe SPT`, `Visa VIC / TAP RFC 9421`, `Mastercard Agent Pay`, `Poppy v0.2 DPoP`).
2. **Stateless CRUD vs. Multi-Party Settlement & Token-Burn Conservation**: In an agentic workflow, LLM reasoning cost + payment rail fees (`SPT`, `x402`, `MPP Tempo`) must stay bounded within transaction unit economics, while multi-seller splits, B2B 3-way match holds, and streaming sub-cent metering require **Atomic Settlement Conservation & FinOps Circuit Breakers**.
3. **Internal Logs vs. Cross-Boundary Cryptographic Non-Repudiation**: When an issuer raises a `Visa CE 3.0 (10.4 / 13.3)` or `Mastercard (4837 / 4853)` dispute, mutable internal application logs carry no evidentiary weight. Production workloads must compile **4-Pillar Cryptographic Evidence Packs** (`AP2 Mandate JWS` + `Scoped Payment Token Cryptogram` + `RFC 9530 Catalog Digest` + `Fulfillment / DDP Proof`).

| Architectural Plane | Classic 3-Tier Web Assumption | Enterprise Agentic Commerce Requirement | Executable Reference Modules |
|---|---|---|---|
| **Plane 1: Edge & Agent Identity** | TLS + WAF IP rate-limiting + static API keys | RFC 9421 HTTP Message Signatures (`@signature-params`), `<= 60s` replay window, single-use nonce, Visa TAP / Web Bot Auth JWKS, principal DID anti-scalping quotas | [`lab/agent_identity_attestation_guard.py`](../../lab/agent_identity_attestation_guard.py), [`lab/poppy_guard.py`](../../lab/poppy_guard.py) |
| **Plane 2: Grounding & Catalog Integrity** | Frontend trusts search index / CDN JSON | Microsoft Web IQ `passage` + live `/v3/browse` price/stock verification, DOM prompt-injection sanitization, RFC 9530 shard digest barrier (`manifest.json`) | [`lab/webiq_commerce_demo.py`](../../lab/webiq_commerce_demo.py), [`lab/ucp_preflight.py`](../../lab/ucp_preflight.py) |
| **Plane 3: Fiduciary Policy & UI Isolation** | Prompt instructions / React modal confirmation | Out-of-band Policy Broker (`summary == terms`), AP2 §7.4 Fiduciary Circuit Breaker, declarative UI isolation, consequence-gated human confirmation | [`lab/payment_approvals.py`](../../lab/payment_approvals.py), [`lab/poppy_guard.py`](../../lab/poppy_guard.py) |
| **Plane 4: Mandates & Scoped Credentials** | Long-lived merchant API keys / card-on-file | Google AP2 `SD-JWT+kb` (`checkout_hash`), Stripe SPT single-use seller-scoped grants, Link Agent Wallet `liwltoken_` isolation, FIDO2/Passkey step-up | [`lab/checkout.py`](../../lab/checkout.py), [`lab/mcp_migration.py`](../../lab/mcp_migration.py) |
| **Plane 5: Multi-Rail Settlement & B2B Sagas** | Single PSP synchronous capture | Multi-seller Largest-Remainder split conservation, Two-Phase OTA/Booking Hold Saga, B2B `PO == GRN == Invoice` 3-way match, `x402` & `MPP Tempo` micropayments | [`lab/unified_checkout_pipeline.py`](../../lab/unified_checkout_pipeline.py), [`lab/b2b_three_way_match_guard.py`](../../lab/b2b_three_way_match_guard.py), [`lab/marketplace_split_settlement_guard.py`](../../lab/marketplace_split_settlement_guard.py) |
| **Plane 6: Dispute Defense, Privacy & Tax/FX** | Manual support tickets & mutable DB rows | 4-Pillar Visa CE 3.0 Merkle evidence compiler, SFTP × Ledger EOD reconciliation, FX volatility collars, PCI-DSS v4.0.1 redaction & GDPR Art. 17 crypto-shredding | [`lab/dispute_evidence_replay.py`](../../lab/dispute_evidence_replay.py), [`lab/zk_eligibility_privacy_redaction_guard.py`](../../lab/zk_eligibility_privacy_redaction_guard.py), [`lab/fx_treasury_iso20022_guard.py`](../../lab/fx_treasury_iso20022_guard.py) |

---

## 2. Domain Architecture Blueprints & Executable Guard Suite

Every architectural subsystem in [`2026-10-18-agentic-commerce-full-stack-architecture.md`](2026-10-18-agentic-commerce-full-stack-architecture.md) pairs a formal Solution Architect specification with a deterministic, zero-dependency Python verification module and unit test suite:

| Architectural Domain | Blueprint Document | Executable Guard Module | Key SA Invariants Verified |
|---|---|---|---|
| **7-Gate Unified Checkout Pipeline** | [Full-Stack Blueprint §1–§16](2026-10-18-agentic-commerce-full-stack-architecture.md) | [`lab/unified_checkout_pipeline.py`](../../lab/unified_checkout_pipeline.py) | End-to-end Identity → Digest → Policy → Mandate → FX/Margin → Settlement → CE 3.0 Receipt |
| **Marketplace Split Settlement & Reserves** | [`marketplace-split-settlement-and-reserve-guard.md`](../architecture/marketplace-split-settlement-and-reserve-guard.md) | [`lab/marketplace_split_settlement_guard.py`](../../lab/marketplace_split_settlement_guard.py) | Hamilton Largest-Remainder cent conservation, VAMP rolling reserve escalation, 4-stage clawback waterfall |
| **Enterprise B2B 3-Way Match & Escrow** | [`b2b-three-way-match-and-escrow.md`](../architecture/b2b-three-way-match-and-escrow.md) | [`lab/b2b_three_way_match_guard.py`](../../lab/b2b_three_way_match_guard.py) | `PO == GRN == Invoice` tolerance gate, BEC/OFAC IBAN block, `2/10 Net 30` dynamic discounting |
| **Sealed Vickrey RFQ, B2B VAT & RMA** | [`reverse-auction-tax-and-returns-guard.md`](../architecture/reverse-auction-tax-and-returns-guard.md) | [`lab/reverse_auction_tax_returns_guard.py`](../../lab/reverse_auction_tax_returns_guard.py) | Commit-Reveal second-price procurement RFQ, reverse-charge VAT validation, bilateral RMA inspection |
| **Split-Tender & FinOps Budget Encumbrance** | [`split-tender-and-finops-chargeback.md`](../architecture/split-tender-and-finops-chargeback.md) | [`lab/split_tender_finops_guard.py`](../../lab/split_tender_finops_guard.py) | Anti-cash-out refund waterfall, cost-center encumbrance isolation, token-burn ROI circuit breaker |
| **Recurring Mandates & Click-to-Cancel** | [`subscription-metering-and-click-to-cancel-guard.md`](../architecture/subscription-metering-and-click-to-cancel-guard.md) | [`lab/subscription_metering_click_to_cancel_guard.py`](../../lab/subscription_metering_click_to_cancel_guard.py) | UUIDv7 usage watermark deduplication, PSD3 48h pre-debit notice, symmetric FTC Click-to-Cancel |
| **FX Treasury Netting & ISO 20022** | [`fx-treasury-netting-and-iso20022-guard.md`](../architecture/fx-treasury-netting-and-iso20022-guard.md) | [`lab/fx_treasury_iso20022_guard.py`](../../lab/fx_treasury_iso20022_guard.py) | 120s FX quote lock collar, multi-currency natural AR/AP netting (`<12 bps`), `pacs.008` UETR validation |
| **Cross-Border DDP Customs & Carbon Routing** | [Full-Stack Blueprint §22](2026-10-18-agentic-commerce-full-stack-architecture.md) | [`lab/green_logistics_customs_sla_guard.py`](../../lab/green_logistics_customs_sla_guard.py) | WCO HS6 DDP landed cost, de-minimis split-consignment anti-evasion, Scope 3 Pareto carrier selection |
| **ZK Eligibility, PCI Redaction & GDPR** | [`zk-eligibility-pci-redaction-and-crypto-shredding.md`](../architecture/zk-eligibility-pci-redaction-and-crypto-shredding.md) | [`lab/zk_eligibility_privacy_redaction_guard.py`](../../lab/zk_eligibility_privacy_redaction_guard.py) | Zero-PII `SD-JWT` predicate proofs, Luhn PAN/live-key firewall, KMS CEK crypto-shredding tombstones |
| **Embedded BNPL, SLA Insurance & Factoring** | [`embedded-bnpl-and-parametric-insurance-guard.md`](../architecture/embedded-bnpl-and-parametric-insurance-guard.md) | [`lab/embedded_bnpl_parametric_insurance_guard.py`](../../lab/embedded_bnpl_parametric_insurance_guard.py) | Cross-issuer BNPL velocity cap, DSCR underwriting, UCC invoice double-pledge prevention |
| **OTA Aviation NDC, Open-Banking VRP & 5G** | [Full-Stack Blueprint §33](2026-10-18-agentic-commerce-full-stack-architecture.md) | [`lab/aviation_ndc_vrp_telecom_slice_guard.py`](../../lab/aviation_ndc_vrp_telecom_slice_guard.py) | IATA ONE Order interline prorate, EU261 automated delay escrow, PSD3 VRP sweeping bounds |
| **Trade Finance MLETR eBL & eUCP 600** | [`trade-finance-ebl-lc-and-demurrage-guard.md`](../architecture/trade-finance-ebl-lc-and-demurrage-guard.md) | [`lab/trade_finance_ebl_lc_demurrage_guard.py`](../../lab/trade_finance_ebl_lc_demurrage_guard.py) | MLETR eBL exclusive control transfer, eUCP 600 documentary presentation match, demurrage caps |
| **On-Chain `x402` Finality & Stablecoin Peg** | [`onchain-settlement-finality-and-peg-guard.md`](../architecture/onchain-settlement-finality-and-peg-guard.md) | [`lab/onchain_finality_peg_guard.py`](../../lab/onchain_finality_peg_guard.py) | EIP-3009 `validBefore` replay protection, chain reorg finality depth, USDC depeg circuit breaker |

---

## 3. Verification & Interactive Workbenches

- **Interactive H5 Solution Architect Workbench**: [`live-demo.en.html`](../../live-demo.en.html) ([中文版 `live-demo.html`](../../live-demo.html))
- **7-Card 4:5 Benchmark Visual Deck**: [`benchmark-cards.en.html`](../../benchmark-cards.en.html) ([中文版 `benchmark-cards.html`](../../benchmark-cards.html))
- **Run Complete Deterministic Test Suite (`997` unit tests)**:
  ```bash
  python -m unittest discover -s tests
  ```
