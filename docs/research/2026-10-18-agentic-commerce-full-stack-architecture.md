# Agentic Commerce Full-Stack AI-Native Reference Architecture (Stages 1–14 Consolidated Blueprint)

> **Canonical Reference Blueprint (`2026-10-18` – `2026-10-19` Overnight Evolution)**
> Covers the 6-Plane AI-Native Workload Architecture, 7-Gate Deterministic Checkout Pipeline, and §20 Multi-Party Marketplace Split Settlement, Sub-Merchant KYB Rolling Reserve Escalation & Clawback Recovery Waterfall.

---

## 1–19. Architectural Planes & Stage 1–13 Guard Matrix

| Section / Stage | Architectural Domain | Executable Module | Core Deterministic Invariants |
|---|---|---|---|
| **§1–§6 (Stages 1–2)** | 6-Plane AI-Native vs. Classic 3-Tier Workload Benchmark | [`lab/workload_arch_bench.py`](../../lab/workload_arch_bench.py) | Connect SPT profile routing, single-use `SPT Resolve` + RSA slicing, SPT 3DS state machine, AP2 §7.4 FCB, Policy Broker, UCP RFC 9530 catalog feed digest barrier, ATDRP 17-gateway fallback, MPP Tempo sub-cent forfeiture |
| **§7–§9 (Stage 3)** | Cross-Border Multi-Seller Split, Token Margin & Customs Incoterms | [`lab/cross_border_b2b_guard.py`](../../lab/cross_border_b2b_guard.py) | `separate_charges_and_transfers` conservation, `reverse_transfer=True`, `token_burn + rail_fee <= gross_margin`, `DDP` & WCO 6-digit `HS` lock |
| **§10–§11 (Stage 4)** | ACP PR #316 Appendix C 17-Gateway CE 3.0 Dispute Compiler | [`lab/dispute_evidence_replay.py`](../../lab/dispute_evidence_replay.py) | 4-pillar Merkle root (`AP2 Mandate JWS` + `SPT cryptogram` + `UCP RFC 9530 digest` + `DDP/HS6 proof`) & 3-way liability routing |
| **§12 (Stage 5)** | Enterprise Dual-Stack Cutover (`2026-11-30` 42-Day Countdown) | [`lab/protocol_readiness_auditor.py`](../../lab/protocol_readiness_auditor.py) | Phase A/B/C readiness scoring (`100/100`) & self-contained H5 Architect Workbench |
| **§13–§14 (Stage 6)** | Multi-Leg Booking Two-Phase Hold Saga & SFTP EOD Reconciliation | [`lab/booking_sftp_reconciliation_guard.py`](../../lab/booking_sftp_reconciliation_guard.py) | `HOLD_ALL (manual) -> VERIFY_TTL -> ATOMIC_CAPTURE_OR_REVERSE` & `00:00 UTC` SFTP × Tempo × Metronome three-way ledger balance |
| **§15 (Stage 7)** | RFC 9421 Agent Identity Attestation & Anti-Scalping Quotas | [`lab/agent_identity_attestation_guard.py`](../../lab/agent_identity_attestation_guard.py) | Mandatory 6-component RFC 9421 signatures, `<=60s` window, single-use `nonce`, Visa TAP/Stripe Directory JWKS & `(principal_did, sku_id)` scarcity quota |
| **§16 (Stage 8)** | 7-Gate Unified Agentic Checkout Pipeline Orchestrator | [`lab/unified_checkout_pipeline.py`](../../lab/unified_checkout_pipeline.py) | Fail-fast 7-gate execution across 14 chaos & adversarial scenarios (`14/14` AI-Native vs `1/14` Classic 3-Tier) |
| **§17 (Stage 9)** | Recurring Mandate `TCCV` Guard & 3-Layer Atomic Revocation | [`lab/recurring_subscription_guard.py`](../../lab/recurring_subscription_guard.py) | Worst-case $\text{TCCV} = C_{\text{init}} + \max(N_{\text{min}},1)C_{\text{rec}} + F_{\text{ETF}}$ & AP2 + SPT + Billing revocation cascade (`Visa 13.5` / `MC 4841`) |
| **§18 (Stage 10)** | Enterprise B2B 3-Way Match (`PO == GRN == Invoice`) & `2/10 Net 30` | [`lab/b2b_three_way_match_guard.py`](../../lab/b2b_three_way_match_guard.py) | Split-shipment partial capture escrow, BEC/OFAC sanctions block & `37.2449%` implied APR dynamic discounting |
| **§19 (Stages 11–13)** | Sealed Vickrey RFQ, B2B VAT, RMA, Split-Tender & `x402` Finality | [`lab/reverse_auction_tax_returns_guard.py`](../../lab/reverse_auction_tax_returns_guard.py), [`lab/split_tender_finops_guard.py`](../../lab/split_tender_finops_guard.py), [`lab/onchain_finality_peg_guard.py`](../../lab/onchain_finality_peg_guard.py) | Commit-Reveal second-price RFQ, reverse-charge VAT, bilateral RMA guard, split-tender anti-cash-out waterfall, cost-center encumbrance & `x402` EIP-3009 finality/peg guard |

---

## 20. Multi-Party Marketplace Split Settlement, Sub-Merchant KYB Rolling Reserve Escalation & Negative-Balance Clawback Waterfall (Stage 14)

### 20.1 Split Settlement Conservation & Largest Remainder Allocation (`evaluate_split_settlement_invariant`)

In multi-seller carts settled via Stripe Connect or Adyen Balance Platform, proportional allocation of shared pools across seller weights $w_1, \dots, w_K$ must use **Hamilton's Largest Remainder Method**:
1. Compute exact floor shares $q_i = \lfloor P_{\text{pool}} \cdot w_i / \sum w_j \rfloor$ and remainders $r_i = (P_{\text{pool}} \cdot w_i) \bmod \sum w_j$.
2. Distribute the residual cents $\Delta = P_{\text{pool}} - \sum_{i=1}^K q_i$ one cent each to the $\Delta$ sellers with the largest remainders $(r_i, -i)$.
3. Enforce global conservation:
   $$\text{gross\_amount\_minor} = \sum_{i=1}^K \text{seller\_net\_split}_i + \text{platform\_commission\_minor} + \text{tax\_withholding\_minor} + \text{rolling\_reserve\_hold\_minor}$$

### 20.2 Sub-Merchant KYB Risk Tiering & Dynamic Rolling Reserve Escalation (`evaluate_seller_kyb_rolling_reserve`)

- **Unverified KYB (`kyb_verified=False`)**: `100%` (`10000 bps`) escrow hold, all payouts blocked (`SUBMERCHANT_KYB_UNVERIFIED_PAYOUT_BLOCKED`).
- **Standard Verified Tier (`dispute_rate_bps <= 65` & `gmv_velocity_30d <= 3.5x`)**: `5%` (`500 bps`) rolling reserve, `T+0` Instant Payout permitted.
- **Elevated Risk Tier (`65 < dispute_rate_bps <= 90` OR `3.5x < gmv_velocity_30d <= 5.0x`)**: Escalates rolling reserve to `15%` (`1500 bps`) and freezes `T+0` Instant Payout (`ROLLING_RESERVE_ESCALATED_15PCT_INSTANT_PAYOUT_FROZEN`).
- **High-Risk Bust-Out Guard (`dispute_rate_bps > 90` OR `gmv_velocity_30d > 5.0x` OR dual VAMP + velocity breach)**: Escalates rolling reserve to `25%` (`2500 bps`) and freezes `T+0` Instant Payout (`ROLLING_RESERVE_ESCALATED_25PCT_BUST_OUT_GUARD`).

### 20.3 Cross-Seller Partial Fulfillment Default & 4-Stage Clawback Recovery Waterfall (`execute_negative_balance_clawback_waterfall`)

When a defaulting sub-merchant owes $R_{\text{obligation}}$ on a failed bundle leg:
1. **Stage 1 (`Pending Settlement Freeze`)**: $C_1 = \min(R_{\text{obligation}}, B_{\text{pending}})$
2. **Stage 2 (`Rolling Reserve Pool Offset`)**: $C_2 = \min(R_{\text{obligation}} - C_1, B_{\text{reserve}})$
3. **Stage 3 (`Linked Guarantor Debit`)**: $C_3 = \min(R_{\text{obligation}} - C_1 - C_2, B_{\text{guarantor}})$
4. **Stage 4 (`Platform Risk Reserve Isolation`)**: $C_4 = \min(R_{\text{obligation}} - C_1 - C_2 - C_3, B_{\text{platform\_cap}})$, locking the sub-merchant account (`seller_account_locked=True`). Any remaining deficit triggers `UNCOVERED_DEFAULT_EXCEEDS_PLATFORM_RISK_BUFFER`.

---

## 21. Cross-Border Real-Time FX Quote Lock, Multi-Currency Natural Netting Sweep & ISO 20022 `pacs.008` Clearing Compliance (Stage 15)

### 21.1 Bounded FX Quote Lock & Volatility Collar (`evaluate_fx_quote_lock_and_slippage`)

- **TTL & Markup Bounds**: Enforces $\text{TTL}_{\text{quote}} \le 120\text{s}$ (`FX_QUOTE_TTL_EXCEEDED_OR_EXPIRED`) and mid-market markup $\le 50\text{ bps}$ (`FX_SPREAD_MARKUP_EXCEEDED`).
- **Three-Zone Volatility Collar**:
  $$\Delta_{\text{slippage}} = \left\lfloor \frac{|S_{\text{live}} - R_{\text{locked}}|}{R_{\text{locked}}} \times 10000 \right\rceil$$
  - $\Delta_{\text{slippage}} \le C_{\text{collar}}$ (`75 bps`): `FX_QUOTE_LOCK_WITHIN_COLLAR`
  - $C_{\text{collar}} < \Delta_{\text{slippage}} \le C_{\text{collar}} + B_{\text{merchant}}$: `FX_SLIPPAGE_ABSORBED_BY_MERCHANT_BUFFER`
  - $\Delta_{\text{slippage}} > C_{\text{collar}} + B_{\text{merchant}}$: `FX_VOLATILITY_COLLAR_BREACHED_REQUOTE_REQUIRED`

### 21.2 Multi-Currency Natural Netting Sweep (`optimize_multicurrency_netting_sweep`)

Across non-USD sub-ledgers $c \in \{\text{EUR}, \text{GBP}, \text{JPY}, \text{SGD}\}$:
$$V_{\text{matched},c} = 2 \min(\text{AR}_c, \text{AP}_c), \qquad E_{\text{net},c} = |\text{AR}_c - \text{AP}_c|$$
By settling $V_{\text{matched},c}$ internally at `0 bps` and sweeping only $E_{\text{net},c}$ at wholesale institutional spreads (`10 bps` vs `275 bps` retail), effective blended FX drag drops from `275 bps` to **`< 12 bps`** (`0.54 bps` on balanced global treasury books).

### 21.3 ISO 20022 `pacs.008` / SWIFT gpi `UETR` Instruction Compliance (`validate_iso20022_pacs008_instruction`)

Enforces canonical UUIDv4 `UETR` (`ISO20022_INVALID_UETR_UUIDV4`), regulatory trade purpose code (`GDDS`/`SUPP`/`CORT`), `DEBT` (`OUR`) charge bearer for full-principal B2B invoices (`ISO20022_CHARGE_BEARER_VIOLATES_FULL_VALUE_DELIVERY`), and correspondent bank cutoff windows (`ISO20022_CORRESPONDENT_CUTOFF_WINDOW_MISSED`).

---

## 22. Cross-Border HS-Code DDP Landed Cost (De-Minimis / CBAM), Cold-Chain IoT Mean Kinetic Temperature (`MKT`) Escrow & Scope 3 Low-Carbon Pareto Carrier Router (Stage 16)

### 22.1 DDP Landed Cost, CBAM & De-Minimis Anti-Structuring (`evaluate_hs_code_landed_cost_and_deminimis`)

$$\text{DDP}_{\text{total}} = (\text{CIF} + \text{Duty} + \text{Surtax} + \text{CBAM}) \times (1 + r_{\text{VAT}})$$
- Blocks undervaluation (`declared_fob_minor < 0.70 * reference_fair_value_minor` $\Rightarrow$ `CUSTOMS_UNDERVALUATION_FRAUD_BLOCKED`).
- Blocks split-consignment structuring (`same_consignee_24h_cumulative_minor > de_minimis_cap_minor` with `claimed_de_minimis_exempt=True` $\Rightarrow$ `CUSTOMS_SPLIT_CONSIGNMENT_EVASION_BLOCKED`).

### 22.2 Arrhenius Mean Kinetic Temperature (`MKT`) Cold-Chain Escrow (`evaluate_cold_chain_iot_telemetry_escrow`)

$$T_{\text{MKT (K)}} = \frac{\Delta H / R}{-\ln\!\left(\frac{1}{n}\sum_{i=1}^n \exp\!\left(\frac{-\Delta H}{R \cdot (T_{C,i} + 273.15)}\right)\right)}$$
When thermal excursions outside `[2.0°C, 8.0°C]` exceed `15 minutes` or $T_{\text{MKT}} > 8.0^\circ\text{C}$, seller settlement is frozen and escrow compensation is automatically routed to the buyer (`COLD_CHAIN_SLA_BREACH_ESCROW_CLAIMED`).

### 22.3 Scope 3 Carbon Pareto Multimodal Routing (`optimize_carbon_pareto_carrier_route`)

Selects $\arg\min_{r \in \mathcal{F}} \text{kgCO}_2\text{e}(r)$ subject to $\text{hours}(r) \le T_{\text{SLA}}$, $\text{cost}(r) \le B_{\text{cost}}$, and $\text{kgCO}_2\text{e}(r) \le B_{\text{carbon}}$.

---

## 23. Zero-Knowledge Selective-Disclosure Eligibility (`SD-JWT` / `zk-VC`), PCI-DSS v4.0.1 Redaction Firewall & GDPR Art. 17 Crypto-Shredding Ledger (Stage 17)

### 23.1 Selective-Disclosure Predicate Eligibility (`evaluate_zk_selective_disclosure_eligibility`)

Enforces zero-raw-PII boolean predicate proofs (`age_over_21`, `residency_eu`, `professional_license_active`) signed by trusted DID issuers (`did:web:trust.visa.com:tap-vc`, `did:web:identity.stripe.com:vc-issuer`), bound to `presentation_nonce == checkout_session_id` within `proof_ttl_seconds <= 300`, while blocking merchant MCP requests for raw `ssn`, `date_of_birth`, or `passport_number` (`OVERPRIVILEGED_PII_HARVESTING_BLOCKED`).

### 23.2 PCI-DSS v4.0.1 Luhn PAN/CVV & Live Key Context Firewall (`scan_and_redact_agent_context_pii_pci`)

Intercepts Luhn-valid 13–19 digit PANs, CVVs, SSNs, and live API secret keys (`sk_live_*`, `rk_live_*`, `whsec_*`) before LLM inference or telemetry persistence (`PCI_RAW_PAN_OR_CVV_LEAK_BLOCKED`), replacing them with deterministic vault surrogates (`<REDACTED_PAN_L4:4242>`).

### 23.3 GDPR Art. 17 Crypto-Shredding vs. ATDRP Merkle Non-Repudiation (`verify_crypto_shredding_erasure_tombstone`)

Commits only salted ciphertext digests $L_{\text{pii}} = \text{SHA256}(\text{Enc}_{\text{CEK}_u}(\text{PII}) \parallel \text{salt})$ into the ACP `PR #316` ATDRP Merkle tree; destroying $\text{CEK}_u$ in KMS renders PII mathematically irrecoverable (`CRYPTO_SHREDDED_TOMBSTONE_VERIFIED`) while keeping `ATDRP_CE3_MERKLE_ROOT` 100% verifiable for 7-year financial/tax audits.

---

## 24. Agentic Subscription Lifecycle, Usage-Metering Watermark Idempotency & FTC Click-to-Cancel / PSD3 Recurring Mandate Guard (Stage 18)

### 24.1 Usage Metering Watermark & Hard Spend Cap (`evaluate_usage_based_metering_idempotency`)

Deduplicates high-frequency token/API usage events by `idempotency_key` (UUIDv7), rejects late events beyond `max_watermark_lateness_seconds <= 300` (`USAGE_EVENT_LATE_WATERMARK_EXPIRED`), and halts runaway agent loops when cumulative spend exceeds `hard_spend_cap_minor` (`SPEND_CAP_HARD_LIMIT_REACHED_THROTTLED`).

### 24.2 PSD3 / RBI Recurring Mandate Renewal & Price-Escalation Guard (`evaluate_recurring_mandate_renewal_and_pre_debit_notice`)

Enforces `>= 48h` pre-debit notification (`PRE_DEBIT_NOTICE_WINDOW_VIOLATION`), explicit trial-to-paid consent (`TRIAL_TO_PAID_EXPLICIT_CONSENT_MISSING`), and fresh buyer re-consent whenever renewal exceeds `mandate_max_amount_minor` or escalates `> 500 bps` (`5%`) over the prior cycle (`RECURRING_PRICE_ESCALATION_RECONSENT_REQUIRED`).

### 24.3 FTC "Click-to-Cancel" Symmetric Offramp & Pro-Rata Refund (`execute_ftc_click_to_cancel_symmetric_offramp`)

Enforces `required_cancellation_steps <= min(enrollment_steps, 2)` and zero retention walls (`DARK_PATTERN_RETENTION_WALL_BLOCKED`), computes exact unused-cycle refund $R_{\text{pro\_rata}} = \lfloor C_{\text{paid}} \cdot D_{\text{unused}} / D_{\text{total}} \rfloor$ (`PRO_RATA_REFUND_ISSUED`), and atomically revokes downstream Stripe `SPT` / network tokens.

---

## 25. Agentic Promo Coupon Stacking Guard, Cryptographic Multi-Hop Affiliate Attribution & Loyalty Return Clawback (Stage 19)

### 25.1 Promo Coupon Stacking & Margin Floor Invariant (`evaluate_promo_coupon_stacking_invariant`)

Blocks Sybil self-referral rings (`SELF_REFERRAL_SYBIL_RING_BLOCKED`), mutually exclusive campaign group collisions (`EXCLUSIVITY_GROUP_CONFLICT`), and coupon combinations that drive post-discount net margin below `merchant_floor_margin_bps` (`PROMO_STACK_EXCEEDS_FLOOR_MARGIN_BLOCKED`).

### 25.2 Cryptographic Multi-Hop Affiliate Attribution (`verify_cryptographic_affiliate_attribution_chain`)

Verifies multi-hop discovery/comparison/checkout JWS attribution proofs, blocks last-second browser extension or rogue intermediary attribution hijacks injected within `<= 5s` of checkout without verified discovery lineage (`LAST_SECOND_ATTRIBUTION_HIJACK_BLOCKED`), and allocates total commission across valid hops via the Largest Remainder Method (`AFFILIATE_ATTRIBUTION_SPLIT_VERIFIED`).

### 25.3 Return-Window Loyalty Escrow & Clawback (`evaluate_loyalty_points_escrow_and_return_clawback`)

Holds order-earned loyalty points/cashback in `PENDING_RETURN_WINDOW_ESCROW` during the return window; when a buyer returns goods after redeeming rewards, claws back available points (`LOYALTY_POINTS_CLAWED_BACK`) and deducts any unrecovered spent deficit from the principal refund (`CASHBACK_DEFICIT_DEDUCTED_FROM_REFUND`).

---

## 26. Agentic Embedded BNPL / B2B Trade-Credit Underwriting, Parametric SLA Microinsurance & Invoice Factoring Double-Pledge Guard (Stage 20)

### 26.1 Embedded BNPL & B2B Trade-Credit Underwriting (`evaluate_agentic_bnpl_trade_credit_underwriting`)

Enforces Debt Service Coverage Ratio (`dscr >= 1.35`), open-banking cash buffer, and cross-issuer BNPL velocity (`concurrent_active_bnpl_issuers <= 2`, `post_purchase_dti_bps <= 4000`) to block phantom multi-issuer over-indebtedness (`MULTI_ISSUER_BNPL_STACKING_BLOCKED`), while generating an exact integer-cent installment schedule via the Largest Remainder Method (`sum(installment_principal_minor) == financed_principal_minor`).

### 26.2 Parametric SLA Microinsurance & Indemnity Guard (`evaluate_parametric_sla_microinsurance_claim`)

Requires multi-oracle quorum signatures (`oracle_quorum_signatures >= 2`) and deterministic threshold breach (`actual_metric >= policy_trigger_threshold`) for instant payout (`PARAMETRIC_INSTANT_PAYOUT_SETTLED`), while enforcing the Indemnity Principle to block double-dipping when the buyer already received a merchant refund or SLA credit (`DOUBLE_DIP_INDEMNITY_BLOCKED`).

### 26.3 Invoice Factoring UCC Lien & Double-Pledge Guard (`verify_invoice_factoring_ucc_lien_uniqueness`)

Computes canonical SHA-256 invoice fingerprints and verifies global lien uniqueness plus countersigned buyer ERP Notice of Assignment (NOA) locks, blocking double-pledging fraud (`INVOICE_DOUBLE_PLEDGING_BLOCKED`).

---

## 27. EU ESPR Digital Product Passport (DPP) Provenance, Two-Hop C2C Authentication Escrow & Trade-In Anti-Bait-and-Switch Guard (Stage 21)

### 27.1 EU ESPR Digital Product Passport Provenance (`verify_digital_product_passport_provenance`)

Verifies GS1 Digital Link identifiers, OEM hardware signatures (`manufacturer_signature_valid`), repair Merkle lineage (`repair_merkle_root_valid`), and stolen/recall registries, blocking stolen or recalled hardware (`STOLEN_OR_RECALLED_DPP_ASSET_BLOCKED`) and counterfeit passports (`COUNTERFEIT_DPP_SIGNATURE_REJECTED`).

### 27.2 Two-Hop Authenticated C2C Escrow & Brand Royalty Split (`evaluate_authenticated_c2c_escrow_inspection_release`)

Releases buyer escrow only when an accredited authentication hub verifies `inspection_verdict == "AUTHENTIC"` and `hardware_serial_matches_dpp == True`, splitting `escrow_gross_minor` via the Largest Remainder Method across `seller_net_minor`, `authentication_fee_minor`, and `brand_resale_royalty_minor` (`AUTHENTICATED_ESCROW_RELEASED_WITH_ROYALTY_SPLIT`), or refunding 100% of buyer escrow and slashing the seller's collateral bond on counterfeit detection (`COUNTERFEIT_INSPECTION_FAILED_BUYER_REFUNDED`).

### 27.3 Trade-In Residual Valuation & Anti-Bait-and-Switch Guard (`evaluate_trade_in_residual_value_and_grade_clawback`)

Blocks unilateral post-receipt Trade-In card debits when re-grading slashes the locked quote by `> 500 bps` (`5%`, `UNILATERAL_TRADE_IN_BAIT_AND_SWITCH_BLOCKED`), requiring explicit buyer re-consent or free prepaid device return (`TRADE_IN_DOWNGRADE_RECONSENT_OR_FREE_RETURN`).

---

## 28. Cross-Protocol Agentic Real-Time Auction / Reverse RFQ Clearing, Consortium Group-Buying Tiered Escrow & Anti-Collusion / Earnest-Bond Slashing Guard (Stage 22)

### 28.1 Vickrey Second-Price Auction Clearing, Anti-Sniping Soft Close & Anti-Collusion (`evaluate_vickrey_reverse_auction_clearing`)

Enforces incentive-compatible Vickrey second-price clearing (`VICKREY_INCENTIVE_COMPATIBLE_CLEARED`) across B2B Reverse RFQs and scarce compute/ad-slot forward auctions, extends auctions by `+30s` when bids arrive within `<= 15s` of close (`ANTI_SNIPING_SOFT_CLOSE_EXTENDED`), and blocks shill self-dealing or collusion rings (`collusion_ring_score >= 0.85`, `BID_RIGGING_OR_SHILL_COLLUSION_BLOCKED`).

### 28.2 Consortium Group-Buying Tiered Escrow (`evaluate_consortium_group_buying_tier_escrow`)

Unlocks volume wholesale pricing tiers across multi-buyer consortium pools while enforcing exact rebate conservation `sum(final_charges + rebates) == sum(initial_holds)` (`GROUP_TIER_UNLOCKED_REBATE_SETTLED`), or automatically releases 100% of pre-authorized holds when cutoff demand falls below MOQ (`MOQ_NOT_MET_ESCROW_AUTO_RELEASED`).

### 28.3 Winner Griefing-Default Earnest-Bond Slashing & Runner-Up Fallback (`verify_winner_commitment_earnest_bond_slash`)

Slashes 100% of the winning bidder's earnest bond when settlement TTL expires (`WINNER_DEFAULT_EARNEST_BOND_SLASHED`) and seamlessly awards the contract to the second-price runner-up bidder (`SECOND_PRICE_FALLBACK_AWARDED`).

---

## 29. Digital Goods / SaaS Seat DRM Revocation, Secondary Ticketing Anti-Scalping Rotating-QR Escrow & C2PA Generative IP Micro-Royalty Split Guard (Stage 23)

### 29.1 Digital License DRM Revocation & TPM Seat Concurrency (`evaluate_digital_license_seat_activation_guard`)

Revokes activation keys immediately upon order refund/dispute (`REFUNDED_LICENSE_KEY_REVOKED_BLOCKED`), blocks datacenter proxy bulk key harvesting (`DATACENTER_BULK_KEY_HARVESTING_BLOCKED`), and enforces hardware TPM/Enclave seat concurrency limits (`SEAT_CONCURRENCY_LIMIT_EXCEEDED`).

### 29.2 Secondary Ticket Anti-Scalping & `<= 15s` Rotating TOTP QR Escrow (`evaluate_event_ticket_anti_scalping_escrow`)

Enforces face-value resale markup caps (`RESALE_MARKUP_CAP_EXCEEDED_SCALPING_BLOCKED`), requires `<= 15s` rotating TOTP cryptographic QR tokens (`STATIC_SCREENSHOT_QR_EXPIRED_BLOCKED`), and releases escrow only after venue turnstile check-in (`VENUE_CHECKIN_VERIFIED_ESCROW_RELEASED`).

### 29.3 C2PA Provenance & Multi-Creator Micro-Royalty Split (`evaluate_generative_ip_royalty_micro_split`)

Verifies C2PA Content Credentials signatures and blocks unauthorized training scrapes (`C2PA_PROVENANCE_MISSING_OR_SCRAPE_BLOCKED`), splitting net creator pools across contribution weights via the Largest Remainder Method with `conservation_delta_minor == 0` (`C2PA_ROYALTY_MICRO_SPLIT_SETTLED`).

---

## 30. Healthcare & Pharmacy FSA/HSA SIGIS IIAS Dual-Tender Split, NCPDP/DEA eRx Dispense Guard & HIPAA PHI Descriptor Scrubber (Stage 24)

### 30.1 IRS §213(d) & SIGIS IIAS Dual-Tender Split (`evaluate_sigis_fsa_hsa_iias_split_tender`)

Partitions mixed healthcare shopping baskets into SIGIS-qualified medical SKUs (`ELIGIBLE_RX`, `ELIGIBLE_OTC`), dual-purpose SKUs requiring a Letter of Medical Necessity (`DUAL_PURPOSE_LMN` — routing unverified LMN items to the backup payment card via `DUAL_PURPOSE_SKU_LMN_MISSING_ROUTED_TO_BACKUP`), and general retail merchandise, enforcing penny-exact conservation `conservation_delta_minor == 0` between tax-advantaged FSA/HSA tender and backup card (`SIGIS_IIAS_DUAL_TENDER_SPLIT_VERIFIED`).

### 30.2 NCPDP SCRIPT / DEA EPCS & PDMP Dispense Guard (`verify_eprescribing_ncpdp_dea_dispense_guard`)

Verifies prescriber DEA hardware token signatures and state Prescription Drug Monitoring Program (PDMP) duplicate active fill checks (`DEA_EPCS_OR_PDMP_DUPLICATE_FILL_BLOCKED`), and enforces the mandatory `80%` days-supply utilization window before authorizing refill dispensing (`EARLY_REFILL_ACCUMULATION_BLOCKED`).

### 30.3 HIPAA §164.502(b) Minimum-Necessary Payment Descriptor Scrubber (`redact_hipaa_phi_from_payment_descriptor`)

Detects and scrubs `ICD-10` diagnosis codes, `NDC` drug identifiers, and clinical specialty strings from ISO 8583 / card statement descriptors and acquirer metadata, replacing them with a neutral MCC-8099 descriptor and opaque `iias_substantiation_ref` (`HIPAA_PHI_DESCRIPTOR_SCRUBBED_TO_NEUTRAL_MCC`).

---

## 31. Autonomous EV ISO 15118 Plug-&-Charge / V2G Bidirectional Net-Metering, DePIN GPU Goodput SLA Escrow & Carbon Retirement Guard (Stage 25)

### 31.1 ISO 15118-20 OCMF Telemetry & V2G Bidirectional Settlement (`evaluate_ev_iso15118_v2g_energy_settlement`)

Verifies ISO 15118-20 contract certificates and signed hardware Open Charge Metering Format (OCMF) kWh telemetry (`UNSIGNED_OCMF_TELEMETRY_SPOOF_BLOCKED`), blocks V2G grid discharge below the vehicle's minimum safety State-of-Charge floor (`V2G_DISCHARGE_BELOW_SOC_FLOOR_BLOCKED`), and settles net Time-of-Use (ToU) charging vs Feed-in-Tariff (FiT) export credits (`V2G_BIDIRECTIONAL_NET_METER_SETTLED`).

### 31.2 DePIN GPU Goodput SLA Escrow & Carbon Credit Uniqueness (`evaluate_gpu_spot_compute_sla_and_carbon_retirement`)

Blocks double-counted or unverified Verra/Gold Standard carbon retirement serials (`CARBON_CREDIT_DOUBLE_COUNTING_RETIREMENT_BLOCKED`), voids 100% of spot GPU charges when preemption occurs before durable checkpoint commit (`UNCHECKPOINTED_PREEMPTION_CHARGE_VOIDED`), and slashes escrow when measured effective throughput (`measured_goodput_tflops`) falls below `85%` of promised capacity (`COMPUTE_GOODPUT_SLA_BREACH_ESCROW_SLASHED`).

---

## 32. Maritime Trade Finance MLETR Electronic Bill of Lading (eBL) Title Transfer, eUCP 600 Letter of Credit Document-Match & Marine Demurrage Escrow Guard (Stage 26)

### 32.1 UNCITRAL MLETR / DCSA eBL 3.0 Exclusive Control (`verify_mletr_electronic_bill_of_lading_endorsement`)

Enforces "singularity of control" on transferable electronic bills of lading (`eBL`), blocking duplicate trade-finance pledges or stale control tokens (`EBL_EXCLUSIVE_CONTROL_DOUBLE_SPEND_BLOCKED`) and executing atomic title transfer upon escrow confirmation (`MLETR_EBL_ATOMIC_TITLE_TRANSFERRED`).

### 32.2 ICC eUCP 600 Documentary Credit Compliance (`evaluate_eucp600_letter_of_credit_document_presentation`)

Automates multi-document examination across Commercial Invoice, clean-on-board eBL, and packing lists—blocking late shipments/presentations (`EUCP600_LATE_PRESENTATION_OR_EXPIRED_LC_BLOCKED`) and UCP 600 Art. 30 `±5%` quantity tolerance breaches (`EUCP600_DOCUMENT_DISCREPANCY_TOLERANCE_BREACH`).

### 32.3 FMC OSRA Excusable Marine Demurrage & Detention Escrow (`evaluate_marine_demurrage_detention_parametric_escrow`)

Subtracts carrier port-congestion and customs inspection hold hours from container dwell time before applying free-time windows, waiving non-consignee-fault demurrage (`PORT_CONGESTION_OR_CARRIER_FAULT_DEMURRAGE_WAIVED`) and capping chargeable overage fees (`MARINE_DEMURRAGE_CAPPED_SETTLED`).

---

## 33. Real-Time Agentic Ad-Bidding (RTB) Invalid Traffic (IVT) Escrow, Sovereign AI Compute Export Control / Geofencing & SLA Credit-Note Reconciliation Guard (Stage 27)

### 33.1 OpenRTB 3.0 / IAB `ads.cert` 2.0 & SIVT Bot Click-Farm Escrow (`evaluate_agentic_rtb_invalid_traffic_escrow`)

Verifies `ads.cert` 2.0 cryptographic impression signatures (`ADS_CERT_IMPRESSION_SIGNATURE_INVALID_BLOCKED`) and withholds ad-spend escrow when Sophisticated Invalid Traffic (`SIVT`) exceeds the contractual tolerance ceiling (`RTB_SIVT_BOT_CLICK_FARM_ESCROW_WITHHELD`).

### 33.2 Sovereign AI Compute Export Control & PTP/TPM Geofence (`verify_sovereign_compute_export_geofence_attestation`)

Cross-checks hardware TPM 2.0 location signatures and Precision Time Protocol (`PTP`) network latency triangulation (`HARDWARE_LOCATION_ATTESTATION_SPOOF_BLOCKED`), blocking accelerator leases in embargoed or non-sovereign regions (`EAR_EXPORT_CONTROL_OR_RESIDENCY_GEOFENCE_BLOCKED`).

### 33.3 Cloud/API SLA Downtime Credit-Note Auto-Netting (`reconcile_cloud_sla_downtime_credit_note`)

Automatically computes contractual service credit tiers (`10%`, `25%`, `100%`) when observed uptime falls below `committed_sla_bps` and nets the credit note directly against the invoice (`SLA_BREACH_CREDIT_NOTE_AUTO_NETTED`).

---

## 34. B2B Contractor Milestone Escrow, IRS 1099-K / W-8BEN-E Tax Withholding & Sovereign Data-Clean-Room Differential Privacy Budget Guard (Stage 28)

### 34.1 B2B Contractor Milestone Escrow & Retainage Holdback (`evaluate_b2b_contractor_milestone_escrow`)

Requires cryptographic CI/CD or formal acceptance attestation (`UNVERIFIED_MILESTONE_DELIVERABLE_ESCROW_HELD`), blocks unapproved change-order overruns (`UNAPPROVED_CHANGE_ORDER_OVERRUN_BLOCKED`), and disburses milestone payouts net of retainage holdbacks (`MILESTONE_ESCROW_RELEASED_WITH_RETAINAGE_HOLD`).

### 34.2 IRS §6050W (`1099-K`) & Chapter 3 (`W-8BEN-E`) Statutory Tax Withholding (`evaluate_cross_border_tax_withholding_1099k_w8bene`)

Applies 24% US backup withholding for missing TINs (`TIN_MISSING_24PCT_BACKUP_WITHHOLDING_APPLIED`), 30% statutory Chapter 3 withholding for foreign payees lacking a valid `W-8BEN-E` (`W8BENE_MISSING_30PCT_STATUTORY_WITHHOLDING_APPLIED`), or verified tax-treaty rates (`TAX_TREATY_RATE_VERIFIED_NET_SETTLED`).

### 34.3 Data-Clean-Room $(\varepsilon, \delta)$ Differential Privacy Budget Guard (`evaluate_data_clean_room_differential_privacy_budget`)

Tracks cumulative privacy loss $\varepsilon$ across buyer-agent clean-room queries and blocks dataset reconstruction attacks when projected $\varepsilon$ exceeds `max_epsilon_budget` (`DIFFERENTIAL_PRIVACY_EPSILON_BUDGET_EXHAUSTED_BLOCKED`).

---

## 35. Commodity Weather-Index Forward Escrow, GSMA SGP.32 M2M eSIM Roaming CDR Settlement & ISO 20022 `pain.008` Direct Debit Guard (Stage 29)

### 35.1 WMO/Satellite Weather-Index Commodity Forward Escrow (`evaluate_commodity_weather_index_forward_escrow`)

Verifies multi-oracle weather quorum (`UNVERIFIED_WEATHER_ORACLE_QUORUM_BLOCKED`) and triggers automatic drought/frost hedge rebates when observed rainfall drops below `drought_trigger_mm` (`PARAMETRIC_WEATHER_HEDGE_PAYOUT_TRIGGERED`).

### 35.2 GSMA SGP.32 M2M eSIM Wholesale Roaming CDR Guard (`evaluate_m2m_esim_roaming_cdr_settlement`)

Blocks replayed or unsigned visited-network CDR batches (`CDR_BATCH_REPLAY_OR_SIGNATURE_INVALID_BLOCKED`) and enforces wholesale per-MB rate caps (`ROAMING_WHOLESALE_RATE_CAP_BREACH_BLOCKED`).

### 35.3 Open-Banking / SEPA B2B ISO 20022 `pain.008` Direct Debit Mandate (`verify_open_banking_pain008_direct_debit_mandate`)

Requires verified Unique Mandate Reference (`UMR`) signatures, debtor IBAN binding (`PAIN008_UMR_OR_IBAN_BINDING_INVALID_BLOCKED`), and debtor-bank SDD B2B pre-registration (`PAIN008_B2B_PRE_REGISTRATION_OR_CAP_BLOCKED`) before executing `pain.008` A2A pull settlement (`ISO20022_PAIN008_DIRECT_DEBIT_SETTLED`).

---

## 36. Commercial Real Estate CAM Lease Audit, Autonomous Fleet Mobility Toll/Deductible Escrow & Cross-Border EOR Payroll Statutory Withholding Guard (Stage 30)

### 36.1 Commercial Real Estate Triple-Net (NNN) CAM Reconciliation (`evaluate_commercial_cam_lease_reconciliation`)

Strips excluded structural CapEx and landlord executive overhead (`EXCLUDED_STRUCTURAL_CAPEX_CAM_PASS_THROUGH_BLOCKED`) and enforces annual controllable CAM inflation caps (`CAM_CONTROLLABLE_CAP_APPLIED_AND_RECONCILED`) before reconciling prepaid estimates against actual operating expenses.

### 36.2 Autonomous Fleet Mobility Toll, Citation Liability & Collision Deductible Escrow (`evaluate_autonomous_fleet_toll_and_deductible_escrow`)

Scrubs duplicate transponder tolls against GNSS telemetry, routes municipal traffic citations to the AV operator when FSD/autonomous mode was active at the infraction timestamp (`AV_CITATION_ROUTED_TO_OPERATOR_AND_ESCROW_SETTLED`), and blocks unsigned telematics collision deductible claims (`UNSIGNED_TELEMATICS_COLLISION_CLAIM_BLOCKED`).

### 36.3 Global EOR Cross-Border Payroll Statutory & Pre-Funding Guard (`evaluate_eor_cross_border_payroll_statutory_escrow`)

Verifies worker classification compliance (`EOR_WORKER_MISCLASSIFICATION_COMPLIANCE_HOLD`), statutory minimum wage floors (`STATUTORY_MINIMUM_WAGE_FLOOR_VIOLATION_BLOCKED`), and pre-funded escrow adequacy across gross wages, employer social contributions, and EOR platform fees (`EOR_PAYROLL_PREFUNDING_DEFICIT_BLOCKED` / `EOR_STATUTORY_PAYROLL_DISBURSEMENT_SETTLED`).

---

## 37. Construction AIA G702/G703 Mechanics' Lien-Waiver Escrow, Sovereign Procurement Bid-Bond / Domestic-Content Guard & Legal IOLTA Trust Interest Sweep Guard (Stage 31)

### 37.1 Construction AIA G702/G703 Mechanics' Lien-Waiver Escrow (`evaluate_aia_g702_mechanics_lien_waiver_escrow`)

Requires unconditional subcontractor mechanics' lien waivers for prior paid draws and conditional waivers for current billings (`SUBCONTRACTOR_MECHANICS_LIEN_WAIVER_MISSING_HOLD`) before releasing progress payments net of retainage (`AIA_G702_LIEN_WAIVER_VERIFIED_PROGRESS_RELEASED`).

### 37.2 Sovereign Procurement Bid-Bond & Domestic Content Guard (`evaluate_sovereign_procurement_bid_bond_and_domestic_content`)

Screens SAM.gov / EU procurement debarment lists (`DEBARRED_OR_EXCLUDED_VENDOR_REGISTRY_BLOCKED`), verifies surety bid-bond backing (`SURETY_BID_BOND_INSUFFICIENT_OR_UNSIGNED_BLOCKED`), and enforces Buy-American / domestic BOM thresholds (`DOMESTIC_CONTENT_BUY_AMERICAN_THRESHOLD_BREACH_BLOCKED`).

### 37.3 Legal / Fiduciary IOLTA Client Trust Account Guard (`evaluate_iolta_fiduciary_trust_account_guard`)

Enforces ABA Model Rule 1.15 anti-commingling (`IOLTA_TRUST_COMMINGLING_OR_DIRECT_OPERATING_DEBIT_BLOCKED`), blocks premature drawdown of unearned client retainers (`IOLTA_UNEARNED_RETAINER_PREMATURE_DRAWDOWN_BLOCKED`), and sweeps accrued IOLTA interest to the state bar foundation (`IOLTA_EARNED_FEE_DISBURSED_AND_BAR_INTEREST_SWEPT`).

---

## 38. Aviation IATA NDC Interline IRROPS Escrow, Open-Banking VRP Sweeping Guard & Telecom 5G uRLLC Network-Slice SLA Escrow (Stage 32)

### 38.1 Aviation IATA NDC / ONE Order Interline & EU261 IRROPS Escrow (`evaluate_iata_ndc_irrops_interline_escrow`)

Computes operating vs marketing carrier prorate splits (`IATA_ONE_ORDER_INTERLINE_PRORATE_SETTLED`), triggers automatic EU261 / DOT statutory passenger compensation (`€250`/`€400`/`€600`) on non-weather delays `>= 180 min` (`IATA_IRROPS_STATUTORY_COMPENSATION_OR_REFUND_TRIGGERED`), and recognizes extraordinary weather/ATC exemptions (`IRROPS_EXTRAORDINARY_CIRCUMSTANCE_COMPENSATION_EXEMPT`).

### 38.2 UK OBIE / EU PSD3 Open-Banking VRP Sweeping Guard (`evaluate_open_banking_vrp_sweeping_guard`)

Verifies PSU SCA device-bound consent (`VRP_SCA_CONSENT_BINDING_SIGNATURE_INVALID_BLOCKED`), blocks third-party commercial merchants from abusing zero-fee `SWEEPING` VRP rails (`VRP_SWEEPING_THIRD_PARTY_MERCHANT_BYPASS_BLOCKED`), and enforces single-transfer and monthly cumulative caps (`VRP_PERIODIC_OR_SINGLE_LIMIT_EXCEEDED_BLOCKED`).

### 38.3 Telecom 3GPP 5G Network-Slice uRLLC SLA Escrow (`evaluate_telecom_5g_network_slice_sla_escrow`)

Verifies signed TWAMP active probe telemetry (`UNSIGNED_TWAMP_5G_SLICE_TELEMETRY_BLOCKED`) and automatically slashes 25%–50% of the network-slice fee when p99 latency or packet loss breaches uRLLC commitments (`TELECOM_5G_URLLC_SLA_BREACH_REBATE_SLASHED`).

---

## 39. Wholesale CBDC mBridge PvP Settlement, LBMA Allocated Bullion Bar Audit & Dual-Satellite NDVI Crop Insurance Escrow Guard (Stage 33)

### 39.1 Multi-CBDC Bridge (mBridge) Wholesale PvP Settlement (`evaluate_mbridge_wholesale_cbdc_pvp_settlement`)

Enforces asymmetric HTLC timelock ordering (`initiator_htlc_timelock_sec - responder_htlc_timelock_sec >= min_htlc_safety_margin_sec`) to eliminate unilateral Herstatt principal risk (`MBRIDGE_HTLC_TIMELOCK_INVERSION_HERSTATT_RISK_BLOCKED`), verifies signed SAFE / capital-account declarations and commercial bank reserve locks (`MBRIDGE_CAPITAL_ACCOUNT_OR_RESERVE_LOCK_MISSING_BLOCKED`), and enforces FX corridor rate bands (`<= 25 bps`, `MBRIDGE_FX_CORRIDOR_BAND_EXCEEDED_BLOCKED`) before atomic Payment-versus-Payment settlement (`MBRIDGE_WHOLESALE_CBDC_ATOMIC_PVP_SETTLED`).

### 39.2 LBMA Good Delivery Allocated Bullion Bar Audit (`evaluate_lbma_allocated_bullion_bar_audit`)

Blocks substitution of unallocated paper gold pools for physical delivery (`LBMA_UNALLOCATED_PAPER_GOLD_SUBSTITUTION_BLOCKED`), enforces active LBMA Good Delivery refiner status, ultrasonic C-scan tungsten-core screening, and `>= 999.5‰` assay fineness (`LBMA_FINENESS_OR_ULTRASONIC_ASSAY_FAILURE_BLOCKED`), and settles exact fine-troy-ounce weight with zero conservation drift (`LBMA_ALLOCATED_BULLION_FINE_WEIGHT_SETTLED`).

### 39.3 Parametric Crop Insurance Dual-Satellite NDVI & Weather Quorum (`evaluate_parametric_crop_ndvi_weather_escrow`)

Cross-verifies Sentinel-2 and MODIS multispectral NDVI vegetation indices alongside signed ground weather-station rainfall telemetry (`SATELLITE_NDVI_DIVERGENCE_OR_SPOOFED_ORACLE_BLOCKED`), releasing tiered 50% or 100% drought indemnity payouts (`PARAMETRIC_CROP_NDVI_DROUGHT_INDEMNITY_RELEASED`) while preserving exact escrow conservation.

---

## 40. Poppy Draft `0.2` Security Hardening, UCP `deferred_payment` / Identity / `201 Location` Guards & Google AP2 `SD-JWT+KB` Terminal Chain (Stage 34)

### 40.1 Poppy Draft `0.2` Transport, Redirect, Per-User DPoP & MCP Token Selection Guards (`lab/poppy_guard.py`)

Enforces Poppy `v0.2` (`#54`, `#57`–`#70`, commit `30c476455c20`):
- **HTTPS & Minor-Version Backward Compatibility (`verify_poppy_v02_https_and_version_compat`)**: Requires `https` without `#fragment` on all protocol URLs (`#67`), case-sensitive post-host comparison (`#68`), and client backward compatibility across all earlier minor versions within the same major version (`0.2 -> 0.1`, `#66`).
- **DNS-Rebinding SSRF & Non-Discovery Redirect Credential Isolation (`verify_poppy_v02_network_and_redirect_safety`)**: Blocks resolved private/loopback/link-local IP addresses (`#57`) and forbids following HTTP `3xx` redirects or forwarding `Authorization`/`DPoP` headers on any non-discovery request (`#68`).
- **Assertion `iat` Window, Per-User-ID DPoP Key Isolation & Browser `jti` Replay Cache (`verify_poppy_v02_assertion_and_user_dpop_isolation`)**: Enforces `|now - iat| <= 300s` (`#68`), forbids sharing an ES256 DPoP keypair across distinct User IDs (`#68`), and enforces single-use `jti` replay protection on `poppy-browser+jwt` assertions (`#69`).
- **DPoP-Capable MCP Server Token Selection & Signed-Out Operation Prohibition (`verify_poppy_v02_mcp_token_selection`, `RetailOrderMutationGuard`)**: Selects DPoP Session Tokens when an MCP server advertises DPoP support in RFC 9728 metadata (`#64`), forbids sending DPoP tokens under `Authorization: Bearer` (`#69`), requires direct `401 invalid_token` on expired tokens (`#69`), and blocks signed-out sessions from creating/listing/confirming `operations` (`#59`).

### 40.2 UCP `deferred_payment` Conservation, Identity Grant Restriction & Google AP2 `SD-JWT+KB` (`lab/ucp_preflight.py`)

Enforces UCP Oct-19 (`#881`, `#755`, `#731`, `#912`, commit `29e2d562ec0e`) and Google AP2 (`#369`):
- **Deferred Payment Conservation (`verify_ucp_deferred_payment_terms_and_totals`)**: Verifies `due_now + sum(deferred) == total` across deposits, installments, and B2B Net-30/60/90 schedules (`#881`), allowing zero-upfront checkout completion when `due_now == 0`.
- **OAuth Grant Restriction & `201 Location` / Escalation `continue_url` (`verify_ucp_identity_grant_and_location_headers`)**: Restricts Identity Linking `oauth2.grant_types` to `authorization_code` and `refresh_token` (`#755`), requires `Location` on all `201 Created` POST responses (`#731`), and requires an HTTPS `continue_url` whenever `status == "requires_escalation"` (`#912`).
- **Multi-Hop Terminal Key Binding JWT (`verify_ap2_sd_jwt_kb_terminal_chain`)**: Verifies RFC 9901 `SD-JWT+KB` (`typ == "kb+jwt"`, `sd_hash`, `nonce`, and terminal agent holder binding, AP2 `#369`).

---

## 41. UCP Post-Order Modification (`#945`) & Consultation (`#946`), Catalog Substitute vs Search (`#974`), Food Allergen Fail-Closed (`#964`) & ACP MCP Spend Gate (`#296`/`#314`) (Stage 35)

### 41.1 UCP Food Allergen Fail-Closed & No-Inference Guard (`evaluate_ucp_food_allergen_and_dietary_guard`, UCP PR `#964`)

Prohibits platforms/agents from inferring `free_of` from prose (`PLATFORM_INFERRED_FREE_OF_FORBIDDEN`) or businesses from clearing allergens using buyer restrictions (`BUSINESS_RESTRICTION_CLEARING_FORBIDDEN`), and emits `ALLERGEN_CONFLICT_REQUIRES_BUYER_REVIEW` whenever a buyer-restricted allergen is `contains`, `may_contain`, or unrecorded on the dish.

### 41.2 UCP Catalog Entity `substitutes` vs Open-Ended `like` Discovery (`evaluate_ucp_catalog_substitute_vs_search_guard`, UCP PR `#974`)

Enforces the architectural boundary between entity-level `get_product(include=["substitutes"])` (business-asserted replacements) and open-ended discovery `search_catalog(like=[...])` or cross-sell `recommendations` (`UNVERIFIED_SIMILARITY_SEARCH_OR_RECOMMENDATION_SUBSTITUTION_BLOCKED`).

### 41.3 UCP Cancellation-First Order Modification Safe Lookup & Atomic Fence (`evaluate_ucp_order_modification_lookup_and_fence`, UCP PR `#945` / EP `#943`)

Enforces `base_order_version == current_order_version`, guarantees that `GET /orders/{id}/modifications/lookup` (`Original-Idempotency-Key` header) is strictly read-only per RFC 9110 §9.2.1 (`UNSAFE_GET_LOOKUP_STATE_MUTATION_FORBIDDEN`), and implements atomic compare-and-set fencing (`POST /orders/{id}/modifications/fence`) to tombstone timed-out cancellation keys (`FENCED_IDEMPOTENCY_KEY_LATE_ARRIVAL_BLOCKED`).

### 41.4 UCP Business-Initiated Post-Order Consultation & ACP MCP Host Spend Gate (`evaluate_ucp_order_consultation_decision_guard`, `evaluate_acp_mcp_mutating_tool_and_host_gate`, UCP PR `#946` & ACP PR `#296`/`#314`)

Verifies reversed-host schema authority binding (`SCHEMA_AUTHORITY_BINDING_INVALID`), evaluates buyer Identity Linking authentication and dedicated `dev.ucp.shopping.order_consultation:decide` scope before replay cache lookup, verifies RFC 8785 canonical JSON `proposal_digest` (`sha-256:<hex>`), and requires `meta.idempotency_key` + signed `mcpToolGate` on mutating/spend-capable ACP MCP tools.

---

## 42. UCP Declarative A2UI / MCP Apps Isolation (`#899`), Time-Bound Quote Extension (`#930`), Offer Provenance Binding (`#918`), Reverse-DNS `declared_fields` (`#915`) & Split-Payment Credential Echo Guard (`#893`) (Stage 36)

### 42.1 UCP Declarative A2UI vs Sandboxed MCP Apps & Model-Context Isolation (`evaluate_ucp_ui_extension_a2ui_mcp_guard`, UCP PR `#899`)

Enforces `dev.ucp.common.ui`: excludes business-authored UI strings from MCP `content[]` model context (`BUSINESS_UI_INJECTED_INTO_MCP_MODEL_CONTEXT_BLOCKED`), blocks executable HTML in declarative `ui` fields (`EXECUTABLE_HTML_IN_DECLARATIVE_UI_PAYLOAD_BLOCKED`), scopes UI actions to negotiated capabilities, and merges `create_cart` into `update_cart` when a cart is already held.

### 42.2 UCP Time-Bound Quote Extension (`evaluate_ucp_quote_lifecycle_and_totals_guard`, UCP PR `#930` / EP `#929`)

Verifies quote expiry (`quote_unavailable`), line-item immutability (`quote_changed`), omission of `accepted_id` on `complete`, authoritative reflection as a single `totals[type="quote"]` entry, and projection to `order.quote = {id, subtotal}`.

### 42.3 Offer Provenance Under-Binding, Reverse-DNS `declared_fields` & Split-Payment Credential Echo Guard (`lab/ucp_ui_quote_offer_declared_fields_guard.py`, UCP PRs `#918`, `#915`, `#893`)

Blocks Offer digests that omit commercial-provenance extensions (`OFFER_DIGEST_PROVENANCE_UNDERBOUND_BLOCKED`) or conflate Cart `"applied"` with Checkout `"committed"` (`CART_APPLIED_CONFLATED_WITH_CHECKOUT_COMMITTED_BLOCKED`), validates Reverse-DNS `declared_fields` scope bindings (`#915`), and blocks businesses from echoing payment credentials/tokens in split-payment responses (`SPLIT_PAYMENT_CREDENTIAL_ECHO_LEAK_BLOCKED`, `#893`).

---

## 43. UCP Return Policy Eligibility & Typed Fees (`#966`), Capability Event Webhooks (`#938`), Subscription Purchase Options (`#890`), Business Identity (`#939`) & Escalation `continue_url` (`#912`) (Stage 38)

### 43.1 Explicit Return Eligibility, Business-Stated Deadlines & Narrowest-Wins Typed Fees (`evaluate_ucp_return_policy_eligibility_and_fees_guard`, UCP PR `#966`)

Enforces explicit `eligibility.type` (`window` | `unlimited` | `not_accepted`; omitted never means `unlimited`), forbids platform date math from `duration` (`PLATFORM_COMPUTED_RETURN_DEADLINE_FORBIDDEN`), resolves method-scoped `fees[]` via narrowest-wins, and blocks presenting a return channel as free unless all well-known fees resolve to `0` (`CHANNEL_FALSELY_PRESENTED_AS_FREE_RETURN_BLOCKED`).

### 43.2 Generalized Capability Event Webhooks & Unfiltered Read-Back (`evaluate_ucp_capability_event_webhook_guard`, UCP PR `#938`)

Enforces RFC 9421 signed webhook delivery covering `webhook-id`, `webhook-timestamp`, and `ucp-agent`, requires thin `event.json` envelopes for broadcast capabilities (`THIN_EVENT_TREATED_AS_STATE_WITHOUT_READBACK_BLOCKED`), and requires an unfiltered `lookup_locations` read-back before delisting on `location.lookup:removed` (`FILTERED_LOOKUP_USED_FOR_LOCATION_REMOVAL_BLOCKED`).

### 43.3 Purchase Options, Subscription Schedules & Open-Ended Payment Instrument Retention (`evaluate_ucp_purchase_options_subscription_payment_guard`, UCP PR `#890`)

Prevents default options from auto-subscribing when a one-time option exists, blocks replacing a withdrawn subscription with another subscription (`SILENT_SUBSCRIPTION_TO_SUBSCRIPTION_REPLACEMENT_BLOCKED`), and retains only open-ended (unamounted) instruments for recurring orders (`SUBSCRIPTION_MISSING_OPEN_ENDED_RECURRING_INSTRUMENT`), while enforcing UCP PR `#939` business identity separation and PR `#912` `requires_escalation` `continue_url` validation.

---

## 44. UCP Food Checkout & Fulfillment (`#897`), Lodging Deterministic Cancellation Schedule (`#861`), Bulk Catalog Feed (`#866`), Identity Linking (`#876`/`#891`) & RFC 9421 ECDSA Raw `r||s` (`#963`) (Stage 39)

### 44.1 Single-Kitchen Food Checkout, Modification Arithmetic & Free-Form Note Isolation (`evaluate_ucp_food_checkout_and_fulfillment_guard`, UCP PR `#897`)

Enforces single-establishment binding (`MULTI_ESTABLISHMENT_OR_FOREIGN_DISH_BLOCKED`), order-wide single-destination fulfillment (`FOOD_SPLIT_DESTINATION_DELIVERY_FORBIDDEN`), exact `(dish.price + sum(mod.price * mod.quantity)) * line_item.quantity` arithmetic, and blocks paid add-ons inside free-form `dish.note` (`PAID_ADDON_IN_FREEFORM_KITCHEN_NOTE_BLOCKED`).

### 44.2 Lodging Deterministic Cancellation Schedule & Bulk Catalog Feed Authority (`evaluate_ucp_lodging_cancellation_schedule_guard`, `evaluate_ucp_bulk_catalog_feed_guard`, UCP PRs `#861`, `#866`)

Enforces half-open `[start, end)` POSIX cutoff selection and blocks multiplying penalties across multiple targeted stays (`MULTI_STAY_PENALTY_MULTIPLICATION_BLOCKED`, `#861`), while verifying RFC 9530 `sha-256` file digests on bulk catalog snapshots and blocking stale offline feeds from acting as checkout price/availability authority (`STALE_BULK_FEED_USED_AS_CHECKOUT_AUTHORITY_BLOCKED`, `#866`).

### 44.3 Identity Linking Multi-Entry Discovery, DNS-Delegated Email Matching & RFC 9421 ECDSA Raw `r||s` (`evaluate_ucp_identity_linking_and_ecdsa_raw_rs_guard`, UCP PRs `#891`, `#876`, `#963`)

Iterates RFC 9728 `authorization_servers[]` without aborting on custom-domain issuer mismatches (`#891`), enforces `draft-hardt-email-verification §3` `_email-verification.<domain>` TXT delegation before Accelerated IdP email auto-linking (`#876`), and enforces RFC 9421 §3.3.4/§3.3.5 fixed-width 64/96-byte raw `r||s` ECDSA signatures (`ASN1_DER_OR_INVALID_LENGTH_ECDSA_SIGNATURE_BLOCKED`, `#963`).

---

## 45. UCP Nested Bundle Line Items (`#976`), UCP-AP2 Credential Provider Tokenization (`#916`), Google AP2 ISO 4217 Budget & ISO 8601 Window (`#368`/`#377`/`#378`), and ACP Delegate Telemetry & Deep Links (`#238`/`#285`/`#287`/`#237`) (Stage 41)

### 45.1 Nested Bundle Line Items, Cart-Only Checkout & Deferred Terms (`evaluate_ucp_bundle_cart_and_deferred_terms_guard`, UCP PRs `#976`, `#940`, `#908`)

Enforces UCP PR `#976` single-level `parent_id` bundle containment (`BUNDLE_MULTI_LEVEL_OR_ORPHAN_NESTING_BLOCKED`), verifies that component `totals[type="total"]` sum to the parent bundle's `totals[type="subtotal"]` (`BUNDLE_COMPONENT_TOTALS_MISMATCH_PARENT_SUBTOTAL`), excludes `parent_id` components from checkout-level `subtotal`/`items_discount` to prevent double-counting (`BUNDLE_COMPONENTS_DOUBLE_COUNTED_IN_CHECKOUT_TOTALS_BLOCKED`), forbids businesses from rejecting echoed components on update (`BUSINESS_REJECTED_ECHOED_BUNDLE_COMPONENTS_FORBIDDEN`), blocks echoing input-only `cart_id` in responses (`#940`), and enforces `payment: {}` (with `selected_term_id` omitted) on `complete_checkout` for fully deferred payment terms (`#908`).

### 45.2 UCP-AP2 Step 3 Credential Provider Payment Mandate Verification & Token Issuance (`evaluate_ucp_ap2_credential_provider_tokenization_guard`, UCP PR `#916`)

Separates the AP2 `payment_mandate` (presented as `credential.type == "ap2_payment_mandate"` alongside `checkout_jwt` at `POST /tokenize`) from the resulting opaque handler token (`payment.instruments[*].credential.token`), blocking reversible composite tokens (`REVERSIBLE_COMPOSITE_MANDATE_TOKEN_CONFLATION_BLOCKED`), verifying `payment_mandate.transaction_id == checkout_jwt_hash` before token issuance (`AP2_MANDATE_CHECKOUT_JWT_CORRELATION_MISMATCH_AT_TOKENIZE`), and rejecting `complete_checkout` with `payment_mandate_required` when AP2 is negotiated without a mandate-derived token (`AP2_NEGOTIATED_WITHOUT_MANDATE_DERIVED_TOKEN_BLOCKED`).

### 45.3 Google AP2 ISO 4217 Minor-Unit Budget, ISO 8601 Execution-Date Bounds & Non-Fraud Dispute Resolver (`evaluate_ap2_iso4217_budget_execution_and_dispute_guard`, AP2 PRs `#368`, `#377`, `#378`, `#352`)

Replaces binary float `int(max * 100)` with `Decimal(str(max)) * (10 ** exponent)` (`ROUND_FLOOR`) across zero-decimal (`JPY`, `KRW`), two-decimal (`USD`, `EUR`), three-decimal (`KWD`, `BHD`), and four-decimal (`CLF`) currencies (`AP2_BUDGET_ISO4217_MINOR_UNIT_CAP_EXCEEDED`), compares `execution_date` against `not_before`/`not_after` as chronological ISO 8601 instants/dates (`AP2_EXECUTION_DATE_OUTSIDE_ISO8601_WINDOW_BLOCKED`), and resolves post-transaction partial-fulfillment disputes once the mandate-to-receipt authorization chain is verified (`#352`).

### 45.4 UCP Catalog Search `purpose` & `reference_ids` Self-Exclusion and ACP Delegate Signature, `session_context` & `app_links` Guards (`evaluate_ucp_catalog_purpose_and_acp_delegate_telemetry_guard`, UCP PR `#902`, ACP PRs `#238`, `#285`, `#287`, `#237`)

Enforces UCP PR `#902` `purpose` (`search` | `recommendation` | `swap`) and `reference_ids` pairing rules, rejects unsupported purposes (`UNSUPPORTED_SEARCH_PURPOSE_FALLBACK_BROWSE_BLOCKED`), and enforces variant/parent-product self-exclusion (`CATALOG_SEARCH_ANCHOR_SELF_EXCLUSION_VIOLATED`), while enforcing ACP `Signature`/`Timestamp` headers on `delegate_payment` and `delegate_authentication` (`#285`/`#287`), `session_context` vs `risk_signals` separation (`#238`), and registered URI scheme verification on `app_links` (`ACP_APP_LINK_UNREGISTERED_SCHEME_SQUATTING_BLOCKED`, `#237`).

---

## 46. UCP Checkout Payment Finality & Order Reporting (`#816`), Guest Order Access (`#848`), RFC 9421 §2.4 REST Response Binding (`#699`), `TokenCredential` Context & `buyer.consent` Exemption (`#792`/`#660`), `Correspondence` & 3-Axis Adjustment Cause (`#836`/`#837`/`#843`), and ACP Razorpay UPI/CoFT & Feed Extensions (`#217`/`#218`/`#223`) (Stage 42)

### 46.1 Checkout Payment Finality (`final` vs `provisional`) & Order Instrument Reporting (`evaluate_ucp_checkout_payment_finality_and_order_reporting_guard`, UCP PR `#816`)

Enforces UCP PR `#816` (EP `#815`): only the aggregate `totals[type="total"]` entry may carry `amount_finality` (`NON_AGGREGATE_TOTAL_AMOUNT_FINALITY_FORBIDDEN`), final totals omit `payment.maximum_amount` (`FINAL_TOTAL_MAXIMUM_AMOUNT_MUST_BE_OMITTED`), provisional totals require `payment.maximum_amount >= aggregate_total` and buyer disclosure (`PROVISIONAL_TOTAL_MAXIMUM_AMOUNT_MISSING_OR_BELOW_TOTAL`), and `Order` responses carry immutable `order.payment.maximum_amount` while stripping `credential`, `handler_id`, and `selected` from `order.payment.instruments[]` (`ORDER_PAYMENT_INSTRUMENT_FORBIDDEN_CHECKOUT_OR_CREDENTIAL_FIELD_LEAK`).

### 46.2 Guest Order Access Credentials & RFC 9421 §2.4 REST Response-to-Request Binding (`evaluate_ucp_guest_order_access_and_rest_response_binding_guard`, UCP PRs `#848`, `#699`)

Enforces single-order-bound guest `order_confirmation.access` credentials (`#848`), blocking cross-order enumeration (`ORDER_ACCESS_CREDENTIAL_CROSS_ORDER_ENUMERATION_BLOCKED`), listing calls, permalink URL token leakage, missing `Cache-Control: no-store`, and unrevoked credentials after guest-to-account claim (`CLAIMED_ACCOUNT_GUEST_ORDER_CREDENTIAL_NOT_REVOKED`), alongside RFC 9421 §2.4 `;req` response signature binding (`@status`, `@authority;req`, `@method;req`, `@path;req`, `content-digest`, `content-type`, plus `@query;req`/`content-digest;req`) reconstructed from the client's sent request within a 300s `created` freshness window (`#699`).

### 46.3 `TokenCredential` Binding, `buyer.consent` Full-Replacement Exemption, `Correspondence` & 3-Axis `Adjustment.cause` (`evaluate_ucp_token_context_buyer_consent_and_correspondence_guard`, UCP PRs `#792`, `#660`, `#836`, `#837`, `#843`)

Preserves `TokenCredential.binding` across Platform/Business/Processor while blocking `TokenCredential.identity` as caller authentication (`#792`), exempts `buyer.consent` from full-replacement reset on `update_cart`/`update_checkout` (`BUYER_CONSENT_DROPPED_ON_FULL_REPLACEMENT_UPDATE_BLOCKED`, `#660`), prevents treating `correspondence.status == "unverifiable"` as `"agrees"` (`#836`), and enforces 3-axis `Adjustment.cause` (`category`, `attributed_to`, `nature`) with `undetermined` fallback when false assertion (`fraud`) vs rule exploitation (`abuse`) is unproven (`#837`/`#843`).

### 46.4 ACP Razorpay UPI Intent (`#217`), RBI CoFT S2S Cards (`#218`) & Feed Extensions Framework (`#223`) (`evaluate_acp_razorpay_upi_s2s_and_feed_extensions_guard`)

Enforces NPCI `<= ₹1,00,000` (`10,000,000` paise) cap, `INR` currency lock, and `upi://pay` `tr == checkout_session_id` binding (`#217`), RBI CoFT merchant-scoped `token_id` with zero raw PAN/CVV (`#218`), and declared `FeedMetadata.extensions[]` verification without SSRF external schema auto-fetching (`#223`).

---

## 47. UCP `platform_reference` Correlation & Immutability (`#839`), Cart `continue_url` & `ucp/version` Permalinks (`#801`/`#793`), Per-Operation-Class Idempotency & `ETag`/`If-Match` Conditional Writes (`#782`/`#679`/`#628`) + Agent Signals (`#835`), Recognized-Issuer Anchoring & Loyalty Breakdown (`#850`/`#783`/`#662`), and Google AP2 `open_mandate_hash` JCS Derivation (`#279`), `checkout_hash` Entropy (`#278`), `(type, id)` / `Merchant.id` Constraints (`#301`/`#324`) & `rail_confirmation_verified` Receipt Honesty (`#335`) (Stage 44)

### 47.1 `platform_reference` Create-Time Immutability, Cart `continue_url` & Two-Phase `ucp/version` Permalink Resolution (`evaluate_ucp_platform_reference_and_permalink_version_guard`, UCP PRs `#839`, `#801`, `#793`)

Enforces UCP PR `#839`: `platform_reference` (`1..512` chars) is set on Create Checkout, ignored on Update/Complete (`PLATFORM_REFERENCE_MUTATED_ON_UPDATE_OR_COMPLETE_BLOCKED`), carried unchanged onto Order (`ORDER_PLATFORM_REFERENCE_CARRYOVER_MISMATCH`), and forbidden from carrying PII/JWTs/credentials or serving as auth/idempotency (`PLATFORM_REFERENCE_PII_CREDENTIAL_OR_AUTH_MISUSE_BLOCKED`). Also enforces UCP PR `#801` (Cart `continue_url` absolute HTTPS + `line_items` preservation) and UCP PR `#793` (`ucp/version` two-phase query processing, control-parameter consumption, and browser fall-forward without JSON `version_unsupported` errors).

### 47.2 Per-Operation-Class Idempotency Identity, `ETag`/`If-Match` Conditional Writes & Agent Signals (`evaluate_ucp_idempotency_conditional_write_and_signals_guard`, UCP PRs `#782`, `#679`, `#628`, `#835`)

Enforces UCP PRs `#782`/`#679`: binds stored `Idempotency-Key` to `(operation_name, target_resource_id)` (`409 Conflict` / `-32000` on cross-operation or cross-target reuse even for target-only operations like `cancel_checkout`), compares payload-carrying operations via RFC 8785 JCS SHA-256, and requires `arguments.meta["idempotency-key"]` to match the covered `Idempotency-Key` header on signed requests (`IDEMPOTENCY_HEADER_META_MISMATCH_BLOCKED`). Also enforces UCP PR `#628` optimistic concurrency (`ETag` / `If-Match` returning `412 Precondition Failed` or `428 Precondition Required`) and UCP PR `#835` (`dev.ucp.payee_continuity` scoring-only non-decline rule and non-penalization of absent browser signals).

### 47.3 Identity-Linking Recognized-Issuer Anchoring, Per-User `subject_token` Binding & Loyalty Breakdown Sum Invariant (`evaluate_ucp_identity_recognized_issuer_and_loyalty_guard`, UCP PRs `#850`, `#783`, `#662`)

Enforces UCP PR `#850`: selects a business's `config.providers` `oauth2` entry only when `auth_url` is character-for-character identical (RFC 8414 §3.3, no trailing-slash normalization) to a pre-recognized IdP issuer and blocks discovery or `subject_token` presentation against unrecognized URLs (`UNRECOGNIZED_OR_NORMALIZED_IDP_ISSUER_SUBJECT_TOKEN_EXFILTRATION_BLOCKED`), enforces per-user `subject_token` binding (`#783`/`#970`), and verifies `sum(earning_forecast.breakdown) == earning_forecast.amount` and minor-unit loyalty discounts (`#662`).

### 47.4 Google AP2 `open_mandate_hash` JCS Derivation, `checkout_hash` Entropy, `(type, id)` Instrument / Non-Empty `Merchant.id` Constraints & `rail_confirmation_verified` Receipt Honesty (`evaluate_ap2_mandate_hash_constraints_and_receipt_guard`, AP2 PRs `#279`, `#278`, `#301`, `#324`, `#335`)

Computes `open_mandate_hash = SHA-256(JCS_RFC8785(unsigned_open_checkout_mandate_body))` over the unsigned claims object without sorting arrays or hashing JWS envelopes (`#279`), requires `>= 128` bits of payload entropy for `checkout_hash` so Ed25519/WBA integrators resist rainbow-table attacks (`#278`), matches allowed payment instruments by `(type, id)` (`#301`), matches allowed merchants by non-empty `merchant.id` without spoofable `name + website` fallback (`#324`, CWE-639), and prevents `PaymentReceipt` from asserting `rail_confirmation_verified=true` on self-generated UUIDs (`#335`).







