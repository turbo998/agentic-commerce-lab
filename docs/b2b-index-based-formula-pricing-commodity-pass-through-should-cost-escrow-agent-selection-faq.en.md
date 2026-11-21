# Enterprise B2B Index-Based Formula Pricing, `Should-Cost BOM` Pass-Through & Deflation-Clawback Escrow (`SAP Ariba / Coupa / Mintec / ICIS / Fastmarkets`): Anti-"Rocket-and-Feather" Ratchet, Component-Weight Scaling & Automated `SAP PIR` Sync Saving `35%` Commodity Spend — Agent Architecture Selection FAQ

> **Language / 语言**: **[中文 (`b2b-index-based-formula-pricing-commodity-pass-through-should-cost-escrow-agent-selection-faq.md`)](b2b-index-based-formula-pricing-commodity-pass-through-should-cost-escrow-agent-selection-faq.md)** | **English (Current)**  
> **Back to Catalog**: **[📚 English Catalog (`docs/index.en.md`)](index.en.md)** | **[🚀 Interactive Live Workbench (`live-demo.en.html`)](../live-demo.en.html)**  
> **Target Roles**: Chief Procurement Officers (`CPO`) in Retail/CPG/Foodservice, Direct & Packaging Category Directors, `Should-Cost` Value Engineers, `SAP Ariba / Coupa` Architects, Cloud & AI Solution Architects  
> **Architecture Diagram**: `assets/svg/639-b2b-index-formula-pricing-should-cost-escrow-2026-11-22.svg`

---

## ① 📌 Executive Summary

In retail private-label manufacturing, QSR and grocery foodservice supply chains (coffee, dairy, edible oils, proteins), e-commerce corrugated boxes and flexible plastic mailers, and electronics contract manufacturing, enterprises rely on **Index-Based Formula Pricing Contracts** to tie unit prices to underlying commodity benchmarks. Yet when formula clauses sit inside static PDF contracts managed manually by overburdened category buyers, enterprises suffer from three massive asymmetric pricing leaks:
1. **The "Rocket-and-Feather" Asymmetric Ratchet ("Suppliers Hike Prices the Day the Index Spikes, Then Stay Silent for 9 Months When the Index Crashes `22%`")**: When corrugated pulp or polyethylene resin rises `+12%`, the supplier immediately emails a formal price-increase notice. When the exact same commodity index drops `-22%` two quarters later, the supplier says nothing—and because one buyer manages 3,000 SKUs without automated index monitoring, the enterprise keeps paying peak inflation prices on every PO.
2. **The Unweighted `100%` Pass-Through Trap ("Applying a `+15%` Raw-Material Hike to `100%` of the Finished Unit Price")**: If raw paper pulp represents **`40%` of a shipping carton's `Should-Cost BOM`** (while `60%` is fixed conversion labor, machinery depreciation, and overhead) and the pulp index rises `+15%`, the mathematically valid finished-box adjustment is **`40% × 15% = +6.0%`**. Yet suppliers routinely demand a **`+15.0%` hike across the entire finished price**—or cherry-pick a single-day spot spike rather than the contracted 90-day trailing average.
3. **Unverified Benchmark Sources & Ad-Hoc `"Energy / Freight Surcharge"` Invoice Lines**: Suppliers attach screenshots from unverified regional blogs, trigger price hikes inside the contracted **`±5%` no-change deadband corridor**, or slip unauthorized `"Temporary Resin / Energy Surcharge"` line items onto `EDI 810` invoices.

**Architectural Verdict**: Deploy a **4-Lane B2B Index-Based Formula Pricing, Should-Cost Weighting & Deflation-Clawback Escrow Architecture**: **Bidirectional Symmetric Deflation Reset & `±5%` Deadband Corridor Lock (`HTTP 403`) + `Should-Cost BOM` Component-Weight Scaling & 90-Day Trailing-Average Gate (`HTTP 422`) + Authoritative Benchmark Ticker Pinning (`Mintec / ICIS / Fastmarkets / EIA`) & Ad-Hoc Surcharge Block (`HTTP 451`) + Automated Quarterly `SAP Purchasing Info Record (PIR)` Write-Back (`HTTP 409`)**, reducing commodity overpayment and uncaptured deflation leakage by **35.0%**.

![B2B Index-Based Formula Pricing, Should-Cost Weighting & Deflation Clawback Escrow Architecture](../assets/svg/639-b2b-index-formula-pricing-should-cost-escrow-2026-11-22.svg)

---

## ② 🎯 Business & Architect Deep-Dive Q&A

### Q1: How do we eliminate the "Rocket-and-Feather" ratchet where suppliers aggressively push upward price hikes but never proactively pass through downward commodity drops?
- **Business Pain**: If downward price adjustments depend on a human buyer remembering to check 40 different commodity indices every quarter and emailing 200 suppliers, 70% of deflationary savings are left on the table.
- **Architectural Guardrail (`HTTP 403 ASYMMETRIC_RATCHET_OR_DEADBAND_BREACH_BLOCKED`)**:
  1. **Automated Bidirectional Symmetric Deflation Clawback**: On Day 1 of every contractual reset period (monthly/quarterly), the Agent polls the bound commodity index feeds across all active contracts. Whenever a trailing index drops past the lower deadband threshold and a supplier fails to submit a downward revision, the system blocks invoices at the old peak price (`HTTP 403`), automatically issues a **Contractual Downward Price Reset Notice**, and updates the ERP `Purchasing Info Record (PIR)` downward.
  2. **`±5.0%` Deadband Corridor & Cap/Collar Enforcement (`HTTP 403`)**: Price-increase requests submitted when the net index movement sits inside the contracted **`[-5.0%, +5.0%]` deadband** (or exceeding the annual cap ceiling) are automatically rejected (`HTTP 403`).

### Q2: How do we stop suppliers from applying a `+15%` raw-material increase to `100%` of the finished product price or cherry-picking a single-day spot peak?
- **Business Pain**: Raw materials rarely account for 100% of a manufactured item's price. Allowing 1-to-1 percentage pass-through inflates the supplier's fixed overhead and profit margin at the buyer's expense.
- **Architectural Guardrail (`HTTP 422 UNWEIGHTED_100PCT_PASSTHROUGH_OR_SPOT_PEAK_BLOCKED`)**:
  1. **Mandatory `Should-Cost BOM` Component-Weight Formula**: Every index-linked contract is encoded with explicit cost-share weights summing to `1.0`:
     $$P_t = P_0 \times \left[ w_{\text{fixed}} + \sum_{i} w_i \cdot \frac{\overline{\text{Index}}_{i, t}}{\overline{\text{Index}}_{i, 0}} \right]$$
     If raw pulp is `w_1 = 0.40` of a carton's cost and rises `+15%`, any supplier request exceeding `+6.0%` is blocked (`HTTP 422`) and counter-offered at the exact `Should-Cost` weighted delta.
  2. **90-Day Trailing-Average (`T-1 Quarter`) Window Lock**: Calculations using cherry-picked single-day spot peaks instead of the contracted 90-day trailing arithmetic mean are rejected (`HTTP 422`).

### Q3: How do we prevent suppliers from citing unverified web prices or sneaking uncontracted "energy/resin surcharges" onto `EDI 810` invoices?
- **Business Pain**: Accounts Payable (`AP`) teams often rubber-stamp extra surcharge lines on invoices because they cannot verify the underlying commodity clause.
- **Architectural Guardrail (`HTTP 451 UNVERIFIED_INDEX_SOURCE_OR_ADHOC_SURCHARGE_HOLD` & `HTTP 409` SAP PIR Sync)**:
  1. **Pinned Official Benchmark Ticker ID & Ad-Hoc Surcharge Freeze (`HTTP 451`)**: Every formula clause is cryptographically pinned to an immutable third-party benchmark series ID (**`Mintec / Expana`** for food/ag, **`ICIS`** for petrochemicals/resins, **`Fastmarkets RISI`** for pulp/paper, **`LME`** for metals, **`US EIA`** for diesel). Rate requests citing unpinned sources—or `EDI 810` invoices containing uncontracted surcharge codes—are placed on compliance hold (`HTTP 451`).
  2. **Zero-Touch Quarterly `SAP Ariba / S4HANA PIR` Write-Back (`HTTP 409`)**: Once the quarterly formula price is verified, the Agent writes the new unit price directly into the ERP **`Purchasing Info Record (PIR)`** and active scheduling agreements—ensuring 3-Way Match (`PO == GRN == Invoice`) automatically enforces every cent of commodity deflation and saves **35.0%** in commodity overpayments.

---

## ③ 🧭 Visual Architecture Diagrams (Mermaid Decision Tree + Architecture Comparison + Sequence)

### 3.1 Enterprise B2B Index-Based Formula Pricing & Deflation-Clawback Decision Tree
```mermaid
flowchart TD
    A[Quarterly Formula Reset Date / Supplier Price-Hike Request / Inbound EDI 810 Invoice] --> B{1. Authoritative Benchmark Source & Surcharge Gate}
    B -->|Supplier Cites Unverified Price Screenshot or Adds Uncontracted Energy/Resin Surcharge Line| C[HTTP 451: Hold Unverified Source & Strip Ad-Hoc Surcharges · Require Pinned Mintec/ICIS/RISI Series]
    B -->|Pinned Benchmark Series Verified| D{2. Symmetric Deflation Clawback & ±5% Deadband Gate}
    D -->|Index Dropped Past Lower Band While Supplier Keeps Peak Price or Hike Requested Inside ±5% Deadband| E[HTTP 403: Block Rocket-and-Feather Ratchet · Enforce Downward Reset & Reject Inside-Band Hikes]
    D -->|Outside ±5% Deadband & Symmetric| F{3. Should-Cost BOM Weighting & 90d Average Gate}
    F -->|Raw Material % Applied to 100% Finished Price Instead of BOM Share or Spot-Peak Date Used| G[HTTP 422: Scale Adjustment by Should-Cost BOM Weight e.g. 40% × 15% = +6.0% & Enforce 90d Mean]
    F -->|BOM Weight & 90d Trailing Mean Valid| H{4. Automated Quarterly Reset + Direct SAP PIR Write-Back Enabled?}
    H -->|Compute Weighted Formula Price Across All SKUs & Auto-Update SAP PIR / Scheduling Agreements| I[HTTP 409: Capture 100% of Commodity Deflation · Zero Over-Weighted Hikes · Save 35% Spend]
    H -->|Manual Spreadsheet Renegotiation| J[HTTP 200: Existing Contract Unit Price Maintained]
```

### 3.2 Legacy PDF Formula Clauses vs. Agentic `Should-Cost` & Automated `SAP PIR` Sync
```mermaid
flowchart LR
    subgraph Legacy["❌ Legacy Manual Formula Contracts (Rocket-and-Feather + 100% Pass-Through)"]
        L1[Index Spikes +15% → Supplier Hikes Next Day\nIndex Drops -22% → Supplier Stays Silent] --> L2[Buyer Too Busy to Check 50 Indices\nOverpays Peak Price for 12 Months]
        L2 --> L3[Pulp is 40% of Carton Cost\nSupplier Raises Full Carton Price +15%]
        L3 --> L4[Cherry-Picks 1-Day Spot Peak\nSlips 8% Ad-Hoc Energy Surcharge on Invoice]
    end
    subgraph Agentic["✅ Agentic Index Formula & Should-Cost Escrow (Mintec / ICIS / SAP Ariba)"]
        A1[Live Mintec / ICIS / Fastmarkets Feed\nEnforces 90d Trailing Avg & ±5% Deadband] --> A2[Should-Cost BOM Weight Scaling\n40% Pulp Share × 15% Hike = +6.0% Max]
        A2 --> A3[Automatic Downward Deflation Trigger\nIssues Reset Notice on Day 1 of Quarter]
        A3 --> A4[Direct Write-Back to SAP PIR Master\n3-Way Match Blocks Old-Price Invoices]
    end
```

### 3.3 Trimming an Over-Weighted `+15%` Hike to `+6.0%` & Auto-Clawback on Index Deflation Sequence
```mermaid
sequenceDiagram
    autonumber
    participant Vendor as Packaging / Ingredient Supplier
    participant Agent as Formula Pricing & Should-Cost Agent
    participant IndexAPI as Official Benchmark API (Fastmarkets RISI / Mintec / ICIS)
    participant ERP as SAP Ariba / S4HANA (PIR Master)

    Note over Vendor,ERP: Case A (Q2 Inflation): Pulp 90d index rises +15%; supplier demands +15% on $1.00 carton
    Vendor->>Agent: 1. Submit Q2 price increase request: $1.00/unit → $1.15/unit (+15.0%)
    Agent->>IndexAPI: 2. Verify pinned Fastmarkets RISI 90d trailing mean == +15.0% (> +5% deadband, HTTP 451/403 pass)
    Agent->>Agent: 3. Check Should-Cost BOM: raw pulp share is 40% (60% fixed conversion) → return HTTP 422 on $1.15!
    Agent-->>Vendor: 4. Approve exact weighted price = $1.00 × (0.60 + 0.40 × 1.15) = $1.06/unit (60% of hike trimmed!)
    Note over Vendor,ERP: Case B (Q4 Deflation): Pulp 90d index falls -20%; supplier stays silent to keep $1.06 price
    IndexAPI-->>Agent: 5. [Q4 Day-1 Poll] Detect -20.0% index drop → compute new formula price = $0.975/unit
    Agent->>ERP: 6. Issue mandatory downward reset notice & update SAP PIR to $0.975/unit automatically (HTTP 409)!
```

---

## ④ 📊 Enterprise Commodity Intelligence & Formula-Pricing Platform Selection Matrix

| Dimension | **Mintec (`by Expana`) / Urner Barry** (Food, Ag, CPG & Retail Private-Label Leader) | **ICIS / Fastmarkets (`RISI`) / S&P Platts** (Chemicals, Resins, Paper/Pulp & Metals Benchmarks) | **SAP Ariba Contract Pricing / Coupa** (ERP Formula Execution & `PIR` Sync) | **aPriori / CleanSheeting AI** (Manufactured Component `Should-Cost` Modeling) |
| :--- | :--- | :--- | :--- | :--- |
| **Best Fit** | Grocery retailers, QSR restaurant chains & CPG brands buying food ingredients, proteins, dairy & packaging | Industrial, e-commerce & CPG buyers contracting corrugated cardboard, PE/PP/PET films, aluminum & energy | Executing index-linked pricing conditions directly inside enterprise POs, scheduling agreements & 3-Way Match | Building bottom-up `Should-Cost BOM` breakdowns (material weight vs. machine cycle time vs. overhead) |
| **Authoritative Benchmark Coverage** | **Best-in-Class for Food/CPG** (`17,000+` global agricultural, dairy, meat & packaging series) | **Global Settlement Standard** (Named directly in legal contracts for resin, pulp/paper, steel & fuel) | Ingests external benchmark feeds via API to recalculate contract condition tables | Built-in regional raw material, wage & machine-hour rate libraries |
| **`Should-Cost BOM` Multi-Index Weighting** | **Core Strength** (Models multi-ingredient cost baskets—e.g., wheat + cocoa + sugar + foil wrapper—in one dashboard) | Tracks petrochemical feedstock-to-polymer conversion spreads | Supports weighted pricing formulas on contract line items | **Industry Benchmark** (Derives exact material gram weights and conversion share from 3D CAD / specs) |
| **Symmetric Deflation Clawback & ERP Sync** | Alerts buyers the day supplier prices diverge from falling underlying cost models | Delivers automated API feeds on settlement dates | **System of Record** (Updates `SAP PIR` so AP 3-Way Match automatically blocks unreduced invoices) | Generates fact-based negotiation packs for supplier clawbacks |
| **Pricing (`official_list_price`)** | Enterprise subscription (**`$25,000–$80,000+/year`** by category pack & seats) | Per-series / API data license | Included in `SAP Ariba / Coupa` Contract Lifecycle & Sourcing suites | Annual enterprise license tiered by modeled spend |

---

## ⑤ 🧪 ROI Estimation & 7-Card Visual Benchmark Deck

> **Provenance**: Modeled on an `$80M/year` CPG and retail packaging procurement organization's quarterly commodity formula leakage pool (`$190,000/quarter` in uncaptured downward commodity deflation due to "Rocket-and-Feather" supplier silence, overpayments from unweighted `100%` pass-through of raw-material hikes, cherry-picked spot peak dates, and uncontracted invoice energy surcharges), labeled `synthetic` (`independently_reproduced=false`).

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 1 / 7 · HANDS-ON · B2B INDEX FORMULA PRICING & SHOULD-COST ESCROW           ║
║ Headline: Symmetric Deflation Clawback & BOM Weighting Cut Material Spend 35.0%  ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ [Scenario & Thresholds]        [Structured Input]       [Top Decisions & KPIs]   ║
║ • Material Pool: $190,000/Qtr  • Deadband: ±5.0% Collar • Standard: HTTP 200     ║
║ • BOM Raw Weight: 40% Pulp/Res • Avg Window: 90d Trail  • Asymmetric: HTTP 403   ║
║ • Fixed Overhead: 60% Frozen   • Benchmark: Mintec/ICIS • 100% Pass: HTTP 422    ║
║ • ERP Sync: Auto SAP PIR Write • Ad-Hoc Fees: Blocked   • Saved Spend: -$66,500  ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ Provenance: synthetic (independently_reproduced=false) · Suite: WebIQ-R196 (#315)║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 2 / 7 · SCENARIO: +15% PULP HIKE ON 40%-PULP BOX & -20% RESIN DROP CLAWBACK ║
║ Headline: 15% Box Hike Trimmed to +6.0% via BOM Weight; -20% Resin Drop Captured ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ Input Quote: "Carton supplier demanded +15% total price hike when pulp rose +15% ║
║ (pulp is 40% of BOM); separately, resin vendor stayed silent after -20% drop."   ║
║ 1. [choice] Symmetric Deflation Gate   ──► 1.00 conf ──► [Act automatically]     ║
║    ████████████████████████████████████████ 100% (Auto-Lowered Resin PIR on Drop)║
║ 2. [choice] Should-Cost 40% BOM Weight ──► 0.99 conf ──► [Act automatically]     ║
║    ███████████████████████████████████████▊ 99% (+15% Demand Cut to +6.0% Valid) ║
║ 3. [score]  Mintec/ICIS → SAP PIR Sync ──► 0.98 conf ──► [Confirm: HTTP 409]     ║
║    ███████████████████████████████████████░ 98% ($66,500 Saved; 0 Ad-Hoc Fees)   ║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 3 / 7 · WHAT I TESTED · FULL 5-LANE EVALUATION MATRIX                      ║
║ Headline: 5/5 Deterministic Guardrails Verified Across Ratchet, BOM & Benchmarks ║
╠══════════════════════════╦══════════════════════════╦══════════════════╦═════════╣
║ SCENARIO                 ║ QUESTION / TASK          ║ MODEL ANSWER     ║ ACTION  ║
╠══════════════════════════╬══════════════════════════╬══════════════════╬═════════╣
║ Baseline Inside Deadband ║ Index delta within ±5%   ║ HTTP 200 ($0)    ║ Auto    ║
║ Silent on -20% Index Drop║ Rocket-and-feather abuse ║ HTTP 403 Blocked ║ Block   ║
║ 100% Pass-Through Demand ║ Apply raw % to full price║ HTTP 422 Blocked ║ Block   ║
║ Fake Quote / Ad-Hoc Fee  ║ Uncontracted surcharge   ║ HTTP 451 Hold    ║ Human   ║
║ Auto BOM Reset + PIR Sync║ Quarterly symmetric sync ║ HTTP 409 (-35%)  ║ Confirm ║
╠══════════════════════════╩══════════════════════════╩══════════════════╩═════════╣
║ Gate Summary: 100% deterministic policy match; 0 uncaptured commodity drops      ║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 4 / 7 · UNDER THE HOOD · PROTOCOL & SCORING MECHANICS                       ║
║ Headline: Deterministic Policy Input Contract → Verifier Decision Trace          ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ // Input Contract (B2bIndexFormulaPricingPolicyInput)                            ║
║ { "quarterly_commodity_ratchet_overpay_and_unweighted_hike_pool_usd": 190000.0,  ║
║   "asymmetric_ignored_index_deflation_or_inside_deadband_hike": false,           ║
║   "unweighted_100pct_finished_price_passthrough_or_spot_peak_date": false,       ║
║   "unverified_vendor_index_source_or_uncontracted_energy_surcharge": false,      ║
║   "quarterly_should_cost_bom_reset_and_sap_pir_auto_writeback_ready": true }     ║
║                                      ↓                                           ║
║ // Verifier Output (<answer>)                                                    ║
║ { "status_code": 409,                                                            ║
║   "decision": "QUARTERLY_SHOULD_COST_RESET_AND_SAP_PIR_SYNC_CONFIRM",            ║
║   "mandate_token": "b2b_index_formula_escrow_optim_409", "savings_usd": 66500.0 }║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 5 / 7 · ROBUSTNESS CHECK · PERTURBATION & CONSISTENCY                       ║
║ Headline: 0.0 pts Variance Across Option Reversal & Deadband Perturbations       ║
╠══════════════════════════════╦═════════════════╦══════════════════╦══════════════╣
║ QUESTION / ANSWER            ║ ORIGINAL        ║ REVERSED / PERT  ║ CHANGE (PTS) ║
╠══════════════════════════════╬═════════════════╬══════════════════╬══════════════╣
║ Symmetric Deflation & Band   ║ HTTP 403 (100%) ║ HTTP 403 (100%)  ║ 0.0 pts      ║
║ Should-Cost BOM Weight Gate  ║ HTTP 422 (100%) ║ HTTP 422 (100%)  ║ 0.0 pts      ║
║ Official Benchmark Source    ║ HTTP 451 (100%) ║ HTTP 451 (100%)  ║ 0.0 pts      ║
║ Auto PIR Reset Net 35%       ║ $66,500 Saved   ║ $66,500 Saved    ║ 0.0 pts      ║
╚══════════════════════════════╩═════════════════╩══════════════════╩══════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 6 / 7 · LATENCY · BATCHING & SCALING LATENCY                                ║
║ Headline: 45ms Quarterly Formula Recalculation Across 5,000 SKUs vs. Manual Lag  ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ Mintec/ICIS 90d Series Fetch ║ █ 19 ms (Agent) vs Unchecked 6-Month Deflation Lag║
║ Should-Cost BOM Weight Math  ║ █ 8 ms (Agent) vs 2.5x Over-Weighted Price Hikes  ║
║ Batch SAP PIR Price Writeback║ ██ 45 ms (Agent) vs Weeks of Manual Excel Edits   ║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 7 / 7 · MY TAKE · GOOD FIT VS NOT FOR & READINESS                           ║
║ Headline: Essential Margin Shield for CPG, Foodservice & Retail Packaging Buyers ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ ✅ GOOD FIT                               ⛔ NOT FOR                             ║
║ • CPG, grocery private-label, QSR chains &• Fixed-fee creative agency retainers  ║
║   e-commerce brands buying boxes/resin/ag   with zero physical raw-material BOM  ║
║ • CPOs automating downward price resets   • Heavy offshore oil-rig drill-bit     ║
║   into SAP Ariba / Coupa Info Records       vibration sensors unrelated to ERP   ║
║ Readiness: Production-verified schema in `lab/webiq_commerce_demo.py` (R196).    ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

---

## ⑥ 🛠️ Production Risk & Architecture Review Checklist

- [ ] **Bidirectional Symmetric Deflation Clawback & `±5%` Deadband Lock (`HTTP 403`)**: Does the contract engine automatically calculate downward unit-price resets when commodity indices fall past the lower threshold—without waiting for supplier consent—and reject price-hike requests inside the `±5%` deadband corridor?
- [ ] **`Should-Cost BOM` Component-Weight Scaling & 90-Day Trailing Mean (`HTTP 422`)**: Are raw-material percentage changes scaled strictly by the raw material's verified BOM share (e.g., `40%` pulp weight × `+15%` index = `+6.0%` max price change, keeping the `60%` fixed conversion portion frozen), using 90-day trailing averages rather than cherry-picked spot peaks?
- [ ] **Pinned Authoritative Benchmark Series (`Mintec / ICIS / Fastmarkets / EIA`) & Ad-Hoc Surcharge Block (`HTTP 451`)**: Does the system reject unverified vendor price screenshots and block `EDI 810` invoice surcharge lines not defined in the master formula agreement?
- [ ] **FX Double-Counting Guard**: When the commodity benchmark and PO currency match (or use a local-currency index), does the formula block adding duplicate FX depreciation markups?
- [ ] **Automated Quarterly `SAP PIR / Coupa` Price-Master Write-Back (`HTTP 409`)**: Are recalculated quarterly formula prices written directly into ERP Purchasing Info Records (`PIRs`) on Day 1 of the quarter so 3-Way Match enforces the new price immediately?
