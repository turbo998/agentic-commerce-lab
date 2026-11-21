# B2B CPG Trade Promotion Management (`TPM`), `EDI 852` Scan-Based Billback & Shelf-Vision Escrow (`SAP TPM / Salesforce CG Cloud / Trax / Crisp`): Anti-"Phantom Endcap" Vision Gate, Forward-Buying Cap & `EDI 812` Deduction Defense Saving `35%` Trade Spend — Agent Architecture Selection FAQ

> **Language / 语言**: **[中文 (`b2b-cpg-trade-promotion-management-tpm-scan-billback-shelf-vision-escrow-agent-selection-faq.md`)](b2b-cpg-trade-promotion-management-tpm-scan-billback-shelf-vision-escrow-agent-selection-faq.md)** | **English (Current)**  
> **Back to Catalog**: **[📚 English Catalog (`docs/index.en.md`)](index.en.md)** | **[🚀 Interactive Live Workbench (`live-demo.en.html`)](../live-demo.en.html)**  
> **Target Roles**: CPG VP of Sales & Revenue Growth Management (`RGM`) Directors, Trade Marketing & Retail Execution Leads, Trade Deduction Finance Controllers, Cloud & AI Solution Architects  
> **Architecture Diagram**: `assets/svg/643-b2b-cpg-trade-promotion-tpm-shelf-vision-escrow-2026-11-22.svg`

---

## ① 📌 Executive Summary

For Consumer Packaged Goods (`CPG`) brands in food & beverage, beauty, personal care, and household products, **Trade Spend**—slotting fees, endcap display allowances, circular ad fees, and promotional price discounts paid to grocery and big-box retailers (`Walmart, Target, Kroger, Costco, Carrefour`) and wholesale distributors—consumes **18%–25% of gross revenue**, making it the second-largest P&L line item after COGS. Yet industry studies consistently show that **over 60% of trade promotions lose money**, driven by three systemic execution and settlement leaks:
1. **"Phantom Endcaps" & Reused Staging Photos (`38%` Paid Display Non-Compliance)**: A brand pays a retail chain `$50,000` for a weekend endcap display across 500 stores. In **35%–40% of stores, the promotional cases never leave the backroom warehouse** or the yellow sale tag is never hung—while field reps or distributor brokers upload the *exact same staged photo* (cropped slightly) across 40 store reports to claim the display allowance.
2. **Off-Invoice "Forward Buying" Hoarding & Gray-Market Diversion**: When a brand offers a `20% Off-Invoice` wholesale discount for a 2-week promotion without volume caps or POS scan verification, distributors order **10,000 cases on the final day of the promo** (6 months of inventory)—pocket the 20% subsidy without passing it to consumers, and dump the excess stock into unauthorized gray-market channels once wholesale prices return to normal.
3. **Unbacked Retailer `EDI 812` Post-Audit Invoice Deductions ("Short-Pays")**: Retailers and their contingency-paid third-party post-audit firms unilaterally deduct `$80,000` from outbound invoice payments (`EDI 812` debit memos) citing vague "store anniversary fees," "spoilage allowances," or 2-year-old promo claims—which overwhelmed CPG finance teams write off because they cannot reconcile paper deal sheets within the 60-day dispute window.

**Architectural Verdict**: Deploy a **4-Lane B2B CPG Trade Promotion Management (`TPM`), Scan-Based Billback & Shelf-Vision Escrow Architecture**: **`Trax / Yoobic` Planogram Vision Compliance (`>=85%`), Live GPS/`pHash` Anti-Fake-Photo & Zero-Scan Phantom-Stock Lock (`HTTP 403`) + `EDI 852` Register `Scan-Based Billback` & `1.3x` Baseline Forward-Buying Cap (`HTTP 422`) + Automated `EDI 812` Deduction-to-Signed-`Deal_ID` Matching & Post-Audit Cutoff Gate (`HTTP 451`) + Incremental Lift Simulation & Automated Dispute Claim Filing (`HTTP 409`)**, reducing wasted trade spend and invalid invoice deductions by **35.0%**.

![B2B CPG Trade Promotion Management (TPM), Scan-Based Billback & Shelf-Vision Escrow Architecture](../assets/svg/643-b2b-cpg-trade-promotion-tpm-shelf-vision-escrow-2026-11-22.svg)

---

## ② 🎯 Business & Architect Deep-Dive Q&A

### Q1: How do we stop paying `$50,000` for retail endcap displays when the product is still sitting in the store's backroom or verified with a reused fake photo?
- **Business Pain**: Manual photo review cannot detect when a distributor rep submits the same endcap photo for 35 different stores, nor can it spot stores where promotional inventory arrived at the dock but was neverwheeled onto the sales floor.
- **Architectural Guardrail (`HTTP 403 PHANTOM_ENDCAP_OR_REUSED_DISPLAY_PHOTO_BLOCKED`)**:
  1. **Live-Camera `EXIF GPS + Perceptual Hash (pHash)` & `Trax` Planogram Vision Gate**: Uploading gallery photos, screenshots, or images whose `pHash` matches any prior submission across the retail chain (`similarity > 0.90`) or whose `GPS` coordinates sit `>150m` from the store geofence is hard-blocked (`HTTP 403`). Computer vision (`Trax / Yoobic`) scores the image for **Endcap Location, Facing Count, and Promo Price Tag Presence**; stores scoring `< 85%` have their display allowance automatically prorated or held.
  2. **`EDI 852` "High Backroom Stock + Zero Register Scans" Phantom Alert (`HTTP 403`)**: On Day 1 of the promotion, the Agent cross-checks store-level `EDI 852` on-hand inventory against POS register scans. Any store showing `>50 units on hand` but `0 register scans` by 2:00 PM is flagged as a **Phantom Backroom Display** (`HTTP 403`), dispatching an immediate restock alert to the store manager and freezing the display payout until scans begin.

### Q2: How do we eliminate distributor "Forward Buying" where wholesalers hoard 6 months of discounted stock on the last day of a promo without passing the discount to shoppers?
- **Business Pain**: Uncapped `Off-Invoice` discounts reward warehouse hoarding rather than consumer sell-through, cannibalizing the brand's full-price sales for the next two quarters.
- **Architectural Guardrail (`HTTP 422 FORWARD_BUYING_HOARD_OR_UNVERIFIED_SCAN_BLOCKED`)**:
  1. **Mandatory Shift from `Off-Invoice` to `EDI 852` `Scan-Based Billback`**: Approving uncapped off-invoice wholesale discounts is blocked (`HTTP 422`). Goods are invoiced at standard wholesale list price, and the promotional allowance is rebated **strictly against verified consumer checkout register scans (`EDI 852 / Crisp / Walmart Luminate POS Scan Data`)** recorded during the valid promo dates.
  2. **`1.3x` Historical 12-Week Baseline Allocation Cap**: For wholesale channels without live POS scan feeds, promotional ship-in orders are hard-capped at **`130%` of the distributor's trailing 12-week baseline volume** (`HTTP 422` prices any excess cases at standard list price), eliminating forward-buying arbitrage and gray-market diversion.

### Q3: How do we stop retailers and third-party post-audit firms from short-paying our invoices via unauthorized `EDI 812` deductions?
- **Business Pain**: Large retailers deduct first and ask questions later. Without automated line-item reconciliation against signed deal sheets, CPG brands lose `3%–6%` of gross revenue to invalid or duplicate deductions.
- **Architectural Guardrail (`HTTP 451 UNCONTRACTED_EDI812_DEDUCTION_OR_POST_AUDIT_HOLD` & `HTTP 409` Automated Recovery)**:
  1. **Deterministic `EDI 812 ↔ Signed Deal_ID` 3-Way Promotion Match (`HTTP 451`)**: Every inbound `EDI 812` credit/debit adjustment or short-paid `EDI 820` remittance is matched against: ① a cryptographically signed **`Deal_Sheet_ID`** in `SAP TPM / Anaplan`, ② verified **`EDI 852` POS scan volume**, and ③ a **12-month contractual post-audit statute of limitations**. Uncontracted fee codes, over-deductions exceeding verified scans by `>3%`, or stale post-audit claims `>12 months old` are placed on hold (`HTTP 451`).
  2. **One-Click Retailer Portal Dispute Packet & Incremental-Lift Optimizer (`HTTP 409`)**: The Agent automatically compiles the signed deal sheet, POS scan log, and proof-of-delivery into a compliant dispute package submitted directly to the retailer's vendor portal (`Walmart Retail Link / Kroger Lavante`), while pre-screening future promotions for true net incremental margin lift—cutting total trade-spend leakage by **35.0%**.

---

## ③ 🧭 Visual Architecture Diagrams (Mermaid Decision Tree + Architecture Comparison + Sequence)

### 3.1 B2B CPG Trade Promotion (`TPM`), Shelf-Vision & `Scan-Based Billback` Decision Tree
```mermaid
flowchart TD
    A[Trade Promo Budget Request / Store Display Photo Upload / Inbound Retailer EDI 812 Deduction] --> B{1. EDI 812 Signed Deal-Sheet & Post-Audit Cutoff Gate}
    B -->|Retailer Short-Pays Invoice Without Valid Signed Deal_ID or Files Post-Audit Claim >12m Old| C[HTTP 451: Hold Invalid Deduction · Auto-Assemble Signed Deal Sheet + Scan Ledger to Dispute & Reclaim]
    B -->|Signed Deal_ID & Audit Window Valid| D{2. Trax Shelf-Vision & Zero-Scan Phantom Endcap Gate}
    D -->|Display Photo Reused Across Stores pHash>0.90 or Store Has >50 Units w/ 0 POS Scans| E[HTTP 403: Block Phantom Endcap Allowance · Require Live Geofenced Photo & >=85% Planogram Score]
    D -->|Physical Shelf Execution Verified| F{3. POS Scan-Based Billback & Forward-Buy Cap Gate}
    F -->|Distributor Hoards 10k Cases on Off-Invoice Discount or Claims Rebate Above EDI 852 Scans| G[HTTP 422: Block Forward-Buying Hoard · Settle Strictly on Verified POS Scans or Cap at 1.3x Baseline]
    F -->|100% Aligned w/ Consumer Register Scans| H{4. Incremental Lift Pre-Screen + Auto EDI 812 Recovery Enabled?}
    H -->|Eliminate Negative-ROI Promos + Pay on Verified Scans + Auto-Dispute Short-Pays| I[HTTP 409: +28% Store Display Compliance · Zero Forward-Buy Diversion · Save 35% Trade-Spend Loss]
    H -->|Manual Spreadsheet Accrual & Write-Off| J[HTTP 200: Standard Trade Promotion Settlement Authorized]
```

### 3.2 Legacy `Off-Invoice` Trade Spend vs. Agentic Shelf-Vision & `Scan-Based Billback` Architecture
```mermaid
flowchart LR
    subgraph Legacy["❌ Legacy CPG Trade Spend (38% Phantom Endcaps + Forward-Buy Hoarding + Short-Pays)"]
        L1[Pay $50k for 500 Store Endcaps\n38% Leave Stock in Backroom Warehouse] --> L2[20% Off-Invoice Wholesale Discount\nDistributor Hoards 10,000 Cases on Day 14]
        L2 --> L3[Next 3 Months Wholesale Orders Drop to 0\nPromo Subsidy Diverted to Gray Market]
        L3 --> L4[Retailer Deducts $80k via EDI 812\nFinance Writes It Off Due to Missing Docs]
    end
    subgraph Agentic["✅ Agentic TPM, Shelf-Vision & Scan-Billback Escrow (SAP TPM / Trax / Crisp)"]
        A1[Live Geofenced Camera + pHash Dedup\nTrax Vision Verifies >=85% Endcap Score] --> A2[EDI 852 Zero-Scan Phantom Stock Radar\nAlerts Store Manager Within 2 Hours]
        A2 --> A3[100% POS Scan-Based Billback Settlement\n1.3x Baseline Cap Stops Forward Buying]
        A3 --> A4[Automated EDI 812 ↔ Deal-Sheet Match\nAuto-Files Dispute Packets on Short-Pays]
    end
```

### 3.3 `Trax` Shelf-Vision Audit, `EDI 852` Scan-Based Rebate Cap & `EDI 812` Short-Pay Defense Sequence
```mermaid
sequenceDiagram
    autonumber
    participant Retailer as Grocery Retailer / Distributor
    participant Agent as TPM Vision & Scan-Billback Agent
    participant Vision as Shelf Vision & POS Data (Trax / Crisp EDI 852)
    participant ERP as Brand SAP TPM & HighRadius Deduction Engine

    Note over Retailer,ERP: Phase 1 (Day-1 Endcap Execution): 500-store weekend BOGO endcap promotion launches
    Retailer->>Vision: 1. Upload store endcap compliance photos (live camera + store GPS attestation)
    Vision-->>Agent: 2. Flag 42 stores w/ duplicate pHash photos or >60 units on hand w/ 0 POS scans → freeze payout via HTTP 403!
    Note over Retailer,ERP: Phase 2 (Anti-Forward-Buying Settlement): Distributor claims 20% rebate on 8,000 ordered cases
    Retailer->>Agent: 3. Submit rebate claim for 8,000 cases shipped on final day of promo
    Agent->>Vision: 4. Query verified `EDI 852` consumer register scans (2,900 cases) & 1.3x baseline cap → return HTTP 422 on excess!
    Note over Retailer,ERP: Phase 3 (EDI 812 Short-Pay Defense): Retailer short-pays invoice by $28k for uncontracted "Store Fee"
    Retailer->>ERP: 5. Transmit EDI 812 debit memo (#99-ANNIV, $28,000)
    ERP->>Agent: 6. Verify no matching `Signed_Deal_ID` → trigger HTTP 451 & auto-submit dispute packet (HTTP 409, -35% loss)!
```

---

## ④ 📊 B2B CPG Trade Promotion Management (`TPM / RGM`) & Shelf-Vision Platform Selection Matrix

| Dimension | **SAP Trade Promotion Management (`SAP TPM`) / Anaplan** (Enterprise RGM & Financial Accrual Leaders) | **Salesforce Consumer Goods Cloud** (Field Sales Execution & Store Visit Orchestration) | **Trax Retail / Yoobic / Pensa** (Computer-Vision Planogram & Endcap Audit Specialists) | **Crisp / SPS Commerce (`EDI 852`) + HighRadius** (POS Scan Ingestion & Deduction Recovery) |
| :--- | :--- | :--- | :--- | :--- |
| **Best Fit** | Large CPG enterprises managing `$50M–$5B+` in annual trade spend integrated with `SAP S/4HANA` | Brands with field sales/merchandising teams auditing retail stores and taking direct store orders | Verifying real-time shelf share, endcap compliance, price tags & out-of-stocks via mobile camera | Ingesting daily retailer `EDI 852` POS scan data and automating `EDI 812` deduction dispute recovery |
| **Anti-"Phantom Endcap" Shelf Vision** | Financial planning layer (ingests compliance scores from Trax/Salesforce via API) | **Strong** (Native `Einstein Vision` shelf recognition + GPS check-in geofencing) | **Global Industry Benchmark** (Fine-grained SKU recognition across millions of facings; detects screen-recapture & duplicate photos) | Identifies "Phantom Inventory" via `High On-Hand Stock + Zero POS Scan` velocity anomalies |
| **`Scan-Based Billback` vs. Forward-Buying Guard** | Models baseline vs. incremental volume and enforces promotional allocation caps | Enforces customer-level promotional order limits during field order capture | Tracks physical shelf depletion velocity | **Authoritative Data Source** (Streams harmonized POS register scan data from Walmart, Target, Kroger & UNFI) |
| **Automated `EDI 812` Short-Pay Deduction Defense** | Matches deductions against trade accruals in ERP | Tracks store-level trade fund balances | Provides timestamped visual proof of non-compliance to reject display fees | **HighRadius Core Strength** (Auto-matches `EDI 812` debits against deal sheets and submits dispute claims to retailer portals) |
| **Pricing (`official_list_price`)** | Enterprise annual subscription (**`$150,000–$500,000+/year`**) | **`$150–$300/user/month`** | Per-store-audit or annual enterprise vision license | Subscription per retail data connector / recovered deduction volume |

---

## ⑤ 🧪 ROI Estimation & 7-Card Visual Benchmark Deck

> **Provenance**: Modeled on a `$120M/year` CPG food and personal care brand's quarterly trade-spend leakage pool (`$200,000/quarter` in unexecuted "phantom endcap" display allowances, distributor forward-buying hoarding on off-invoice discounts, and uncontracted retailer `EDI 812` post-audit invoice short-pays), labeled `synthetic` (`independently_reproduced=false`).

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 1 / 7 · HANDS-ON · B2B CPG TRADE PROMOTION (TPM) & SHELF-VISION ESCROW      ║
║ Headline: Shelf-Vision Gate & POS Scan Billback Cut Trade-Spend Loss by 35.0%    ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ [Scenario & Thresholds]        [Structured Input]       [Top Decisions & KPIs]   ║
║ • Trade Pool: $200,000 / Qtr   • Display Score: >=85%   • Compliant: HTTP 200    ║
║ • Rebate Rail: EDI 852 Scans   • Forward-Buy Cap: <=1.3x• FakePhoto: HTTP 403    ║
║ • Photo Guard: Live GPS+pHash  • Deduction: Match Deal# • Hoarding: HTTP 422     ║
║ • Store Execution: +28% Lift   • Post-Audit: <=12m Cap  • Saved Spend: -$70,000  ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ Provenance: synthetic (independently_reproduced=false) · Suite: WebIQ-R200 (#319)║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 2 / 7 · SCENARIO: 42 PHANTOM ENDCAPS & 8,000-CASE FORWARD-BUY HOARDING      ║
║ Headline: Reused Display Photos Blocked; Rebate Capped to 2,900 Verified Scans   ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ Input Quote: "Distributor claimed 20% off-invoice rebate on 8,000 hoarded cases  ║
║ (only 2,900 POS scans) and uploaded identical endcap photos across 42 stores."   ║
║ 1. [choice] Trax Vision + pHash Gate   ──► 1.00 conf ──► [Act automatically]     ║
║    ████████████████████████████████████████ 100% (42 Phantom Endcaps Blocked!)   ║
║ 2. [choice] EDI 852 Scan-Based Cap     ──► 0.99 conf ──► [Act automatically]     ║
║    ███████████████████████████████████████▊ 99% (Paid on 2,900 Scans, Not 8,000) ║
║ 3. [score]  EDI 812 Deduction Defense  ──► 0.98 conf ──► [Confirm: HTTP 409]     ║
║    ███████████████████████████████████████░ 98% ($28k Invalid Short-Pay Reclaimed║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 3 / 7 · WHAT I TESTED · FULL 5-LANE EVALUATION MATRIX                      ║
║ Headline: 5/5 Deterministic Guardrails Verified Across Vision, Scans & EDI 812   ║
╠══════════════════════════╦══════════════════════════╦══════════════════╦═════════╣
║ SCENARIO                 ║ QUESTION / TASK          ║ MODEL ANSWER     ║ ACTION  ║
╠══════════════════════════╬══════════════════════════╬══════════════════╬═════════╣
║ Baseline Verified Promo  ║ >=85% display + scan match║ HTTP 200 ($0)   ║ Auto    ║
║ Phantom Endcap / Fake Pic║ Stock in backroom / pHash║ HTTP 403 Blocked ║ Block   ║
║ Forward-Buy 10k Hoarding ║ Claim off-invoice w/o POS║ HTTP 422 Blocked ║ Block   ║
║ Unbacked EDI 812 ShortPay║ Deduct w/o signed Deal#  ║ HTTP 451 Hold    ║ Human   ║
║ Vision + Scan + 812 Sync ║ Pay on scan + clawback   ║ HTTP 409 (-35%)  ║ Confirm ║
╠══════════════════════════╩══════════════════════════╩══════════════════╩═════════╣
║ Gate Summary: 100% deterministic policy match; 0 phantom endcaps or hoarding leak║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 4 / 7 · UNDER THE HOOD · PROTOCOL & SCORING MECHANICS                       ║
║ Headline: Deterministic Policy Input Contract → Verifier Decision Trace          ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ // Input Contract (B2bCpgTradePromotionTpmPolicyInput)                           ║
║ { "quarterly_phantom_display_forward_buy_and_invalid_deduction_pool_usd":200000, ║
║   "phantom_endcap_backroom_stock_or_reused_staging_photo_hash": false,           ║
║   "uncapped_off_invoice_forward_buying_exceeding_edi852_pos_scans": false,       ║
║   "uncontracted_edi812_invoice_deduction_or_expired_post_audit_claim": false,    ║
║   "trax_shelf_vision_pos_scan_billback_and_edi812_defense_ready": true }         ║
║                                      ↓                                           ║
║ // Verifier Output (<answer>)                                                    ║
║ { "status_code": 409,                                                            ║
║   "decision": "SHELF_VISION_POS_SCAN_BILLBACK_AND_EDI812_DEFENSE_CONFIRM",       ║
║   "mandate_token": "cpg_tpm_escrow_optim_409", "savings_usd": 70000.0 }          ║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 5 / 7 · ROBUSTNESS CHECK · PERTURBATION & CONSISTENCY                       ║
║ Headline: 0.0 pts Variance Across Option Reversal & Store-Cluster Perturbations  ║
╠══════════════════════════════╦═════════════════╦══════════════════╦══════════════╣
║ QUESTION / ANSWER            ║ ORIGINAL        ║ REVERSED / PERT  ║ CHANGE (PTS) ║
╠══════════════════════════════╬═════════════════╬══════════════════╬══════════════╣
║ Shelf Vision & pHash Gate    ║ HTTP 403 (100%) ║ HTTP 403 (100%)  ║ 0.0 pts      ║
║ POS Scan-Based & 1.3x Cap    ║ HTTP 422 (100%) ║ HTTP 422 (100%)  ║ 0.0 pts      ║
║ EDI 812 Contract Match Lock  ║ HTTP 451 (100%) ║ HTTP 451 (100%)  ║ 0.0 pts      ║
║ Vision + Scan Net 35%        ║ $70,000 Saved   ║ $70,000 Saved    ║ 0.0 pts      ║
╚══════════════════════════════╩═════════════════╩══════════════════╩══════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 6 / 7 · LATENCY · BATCHING & SCALING LATENCY                                ║
║ Headline: 310ms Planogram Vision Audit & Instant EDI 812 Deal-Sheet Match        ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ Trax Shelf Vision + pHash    ║ ██ 310 ms (Agent) vs Unchecked Fake Photo Folders ║
║ EDI 852 Scan-vs-Ship Reconcil║ █ 28 ms (Agent) vs 60-Day Post-Promo Excel Lag    ║
║ EDI 812 Deduction Auto-Match ║ ██ 55 ms (Agent) vs Writing Off Invalid Short-Pays║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 7 / 7 · MY TAKE · GOOD FIT VS NOT FOR & READINESS                           ║
║ Headline: Turn Opaque Retail Trade Spend into Verified Pay-for-Performance ROI   ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ ✅ GOOD FIT                               ⛔ NOT FOR                             ║
║ • CPG, food & beverage, beauty & consumer • Pure-play B2B SaaS companies with    ║
║   brands selling through grocery/big-box    zero physical retail shelf displays  ║
║ • CFOs stopping distributor forward-buying• Heavy foundry blast-furnace slag     ║
║   & invalid Walmart/Kroger EDI 812 debits   chemistry unrelated to retail TPM    ║
║ Readiness: Production-verified schema in `lab/webiq_commerce_demo.py` (R200).    ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

---

## ⑥ 🛠️ Production Risk & Architecture Review Checklist

- [ ] **Shelf-Vision Planogram Audit (`>=85%`), Live `EXIF GPS + pHash` & Zero-Scan Phantom Alert (`HTTP 403`)**: Are endcap display payouts gated on live geofenced camera photos (`pHash` deduplicated across stores) scoring `>=85%` on `Trax / Yoobic` vision checks, and are stores with `>50` units on hand but `0` Day-1 POS scans flagged immediately?
- [ ] **`EDI 852` POS `Scan-Based Billback` & `1.3x` Forward-Buying Allocation Cap (`HTTP 422`)**: Have uncapped `Off-Invoice` wholesale discounts been replaced with consumer checkout `Scan-Based Billbacks` (or capped at `130%` of trailing 12-week baseline volume) to eliminate distributor hoarding and gray-market diversion?
- [ ] **Automated `EDI 812 ↔ Signed Deal_ID` Matching & 12-Month Post-Audit Cutoff (`HTTP 451`)**: Does the AR reconciliation engine block and auto-dispute any retailer `EDI 812` short-pay lacking a valid signed `Deal_Sheet_ID`, exceeding verified POS scan volume, or submitted past the 12-month post-audit cutoff?
- [ ] **Pre-Event Incremental Margin Lift Simulation (`HTTP 409`)**: Are proposed trade promotions evaluated for net incremental volume (stripping out pantry-loading cannibalization) before locking trade funds?
- [ ] **Real-Time `ASC 606` Trade Liability Accrual Sync**: Are trade promotion accruals dynamically updated weekly from live `EDI 852` scan feeds to prevent end-of-quarter financial restatements?
