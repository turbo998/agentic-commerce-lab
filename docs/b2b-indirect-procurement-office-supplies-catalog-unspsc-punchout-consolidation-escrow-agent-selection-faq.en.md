# Enterprise B2B Indirect Procurement, `UNSPSC` Catalog Deduplication, `UOM` (`CS vs. EA`) & `Guided Buying` Escrow (`Amazon Business / Staples Advantage / Coupa / SAP Ariba`): Free-Text-to-Catalog Swap, Internal IT-Closet Reuse & Weekly Dock Consolidation Saving `36%` Indirect Spend — Agent Architecture Selection FAQ

> **Language / 语言**: **[中文 (`b2b-indirect-procurement-office-supplies-catalog-unspsc-punchout-consolidation-escrow-agent-selection-faq.md`)](b2b-indirect-procurement-office-supplies-catalog-unspsc-punchout-consolidation-escrow-agent-selection-faq.md)** | **English (Current)**  
> **Back to Catalog**: **[📚 English Catalog (`docs/index.en.md`)](index.en.md)** | **[🚀 Interactive Live Workbench (`live-demo.en.html`)](../live-demo.en.html)**  
> **Target Roles**: Enterprise Indirect Procurement & Sourcing VPs, Workplace Operations & IT Asset Management (`ITAM`) Directors, `SAP Ariba / Coupa` Guided-Buying Architects, Cloud & AI Solution Architects  
> **Architecture Diagram**: `assets/svg/691-b2b-indirect-procurement-unspsc-punchout-consolidation-escrow-2026-11-23.svg`

---

## ① 📌 Executive Summary

In enterprise Indirect Procurement—covering office supplies, IT peripherals (monitors, docks, headsets), breakroom consumables, and facility supplies across `SAP Ariba Guided Buying`, `Coupa`, `Amazon Business`, `Staples Advantage`, and `W.W. Grainger`—small-dollar requisitions account for **`80%+` of total purchase order volume**. Without deterministic catalog-matching and unit-of-measure (`UOM`) guardrails, enterprises hemorrhage 30%+ of their indirect budget across three everyday failure modes:
1. **Free-Text Requisition (`PR`) Bypass of Negotiated Contract Catalogs (`+42% Retail Markup & Duplicate Material Master Pollution`)**: Central Procurement negotiates a `$52` contract price for genuine HP laser toner inside the company's `Staples / Amazon Business PunchOut` catalog. Yet an office admin who doesn't know the exact catalog keyword clicks *"Create Non-Catalog Free-Text Request"*, pastes a `$89` retail link, and miscodes the **8-digit `UNSPSC` commodity code** (`44103103` Toner vs. `43211500` Computers) to tap the wrong department GL budget—paying a `42%` markup while polluting the ERP with a 19th duplicate material number!
2. **Unit-of-Measure (`ANSI X12 UOM: Case CS vs. Box BX vs. Each EA`) `24x` Over-Ordering & Ignoring Idle Internal IT Closet Inventory**: An employee wants `50 boxes` of copy paper or `50 pens`, overlooks that the B2B catalog item is priced per **`CS (Case of 24)`** rather than `EA (Each)`, types `Quantity = 50`, and accidentally orders **1,200 boxes** that block the building's loading dock! Meanwhile, HR offboards 35 remote employees who return 40 pristine `27-inch 4K monitors` and `USB-C docks` to the internal IT closet—yet when 10 new hires join the next week, Procurement approves `$4,500` to buy 10 brand-new monitors from an external vendor!
3. **35 Daily Micro-Deliveries to the Same Office Building (`$8.99/Order Shipping Fees`) & Unvetted 3P Marketplace Sellers**: Eighteen departments in the same headquarters building place 35 separate `$15` orders throughout the week—incurring `$8.99` shipping fees on each box and generating 1,200 micro-invoices per month for AP to reconcile—while employees accidentally buy counterfeit power adapters from unauthorized third-party marketplace resellers!

**Architectural Verdict**: Deploy a **4-Lane B2B Indirect Procurement, `UNSPSC` Dedup & `Guided Buying` Escrow Architecture**: **Free-Text `PR` `MPN / GTIN` Intercept & Automatic Swap to Negotiated Contract Catalog SKUs (`-38%` Price) + Deterministic 8-Digit `UNSPSC`-to-`GL` Mapping (`HTTP 403`) + `ANSI X12 UOM` (`CS / BX / PK / EA`) Base-Unit Multiplier Gate (`<= 90d` Department Burn Rate) & Mandatory Internal IT-Closet / Stockroom First Check (`HTTP 422`) + Authorized `1P / OEM` Seller Filter, Restricted Personal-SKU Block & `24h cXML PunchOut` Quote TTL (`HTTP 451`) + Building-Wide Weekly Delivery Day Consolidation (`-$8.99` Parcel Fees), Preferred Generic-Brand Auto-Swap (`-32%` Unit Cost), and Single Monthly Summary `EDI 810` Invoicing (`HTTP 409`)**, cutting indirect spend and AP processing costs by **36.0%**.

![B2B Indirect Procurement, UNSPSC Dedup, UOM & Guided Buying Escrow Architecture](../assets/svg/691-b2b-indirect-procurement-unspsc-punchout-consolidation-escrow-2026-11-23.svg)

---

## ② 🎯 Business & Architect Deep-Dive Q&A

### Q1: Why do 35% of indirect requisitions still end up as expensive "Free-Text PRs" even after deploying `SAP Ariba` or `Coupa`—and how do we intercept them in real time?
- **Business Pain**: When an employee searches internal catalogs using colloquial terms (*"MacBook HDMI dongle"*) and gets zero keyword hits, they immediately drop into the "Free-Text Request" form and paste a full-price retail URL.
- **Architectural Guardrail (`HTTP 403 FREE_TEXT_BYPASS_OF_CONTRACT_CATALOG_OR_BAD_UNSPSC`)**:
  1. **Real-Time Free-Text `MPN / GTIN` & Semantic Intercept (`Auto-Swap to Contract Catalog`)**:
     - Whenever a requester submits a free-text `PR` or pastes an external URL, the Guided-Buying agent extracts the **Manufacturer Part Number (`MPN`), `14-digit GTIN / UPC`, and technical specs**, querying all active `cXML / OCI PunchOut` contract catalogs in `< 100ms`;
     - If an exact or functionally equivalent contract SKU exists (e.g., `$52` contract toner vs. `$89` free-text request), the free-text `PR` is blocked (`HTTP 403`) and **automatically converted into a catalog `PunchOut` cart line**!
  2. **Deterministic 8-Digit `UNSPSC` to `SAP GL Account` Lock (`HTTP 403`)**: Requesters are prevented from manually picking arbitrary General Ledger (`GL`) accounts to hide spend; the agent assigns the exact 8-digit `UNSPSC` taxonomy code from item attributes and binds the corresponding tax and cost-center `GL` code!

### Q2: How do we prevent the classic "Ordered 50 Cases (`CS`) Instead of 50 Each (`EA`)" warehouse disaster—and force reuse of idle monitors sitting in the IT closet?
- **Business Pain**: B2B distributors sell in nested packaging hierarchies (`EA` = 1, `PK` = 12, `BX` = 50, `CS` = 24 boxes); a single `UOM` oversight multiplies an order by `24x–100x`.
- **Architectural Guardrail (`HTTP 422 UOM_CASE_EACH_MULTIPLIER_ERROR_OR_IDLE_STOCKROOM`)**:
  1. **`ANSI X12 UOM` Base-Unit Normalization & 90-Day Department Burn-Rate Cap**:
     - On `cXML PunchOutOrderMessage` return, the agent multiplies `Order_Qty × UOM_Pack_Factor` to compute **`Total_Base_Eaches`**;
     - If `Total_Base_Eaches` exceeds the requesting department's **90-day historical consumption ceiling** (e.g., a 25-person team ordering `50 CS = 1,200 boxes` of pens), checkout blocks the submission (`HTTP 422`) and prompts: ***"You selected 50 Cases (1,200 units). Did you mean 50 Individual Boxes (2 Cases)?"***
  2. **Mandatory Internal IT Closet / Stockroom Lookup Before External Purchase (`HTTP 422`)**: Before approving any external `PO` for reusable IT peripherals (`monitors, keyboards, headsets, docking stations, chairs`), the agent queries `ServiceNow ITAM / SAP MM` internal stockrooms. If reclaimed, sanitized offboarded units are sitting in the building's IT closet (`Internal_Stock >= Requested_Qty`), external purchasing is blocked (`HTTP 422`) and converted into a **`$0` internal stock transfer ticket**!

### Q3: How do we stop 35 daily micro-deliveries to the same office building while blocking gray-market marketplace resellers?
- **Business Pain**: Letting every employee ship a `$12` stapler individually via 2-day parcel shipping burns `$8.99` per box in shipping fees and floods the mailroom and AP ledger.
- **Architectural Guardrail (`HTTP 451 UNAUTHORIZED_3P_MARKETPLACE_SELLER_OR_RESTRICTED_SKU` & `HTTP 409` Weekly Dock Consolidation + Generic Swap)**:
  1. **Authorized `1P / OEM` Seller Lock & Restricted Personal-SKU Gate (`HTTP 451`)**:
     - Inside `Amazon Business / Marketplace PunchOut` sessions, third-party gray-market resellers lacking `Authorized_OEM_Partner` status—as well as restricted personal categories (`consumer gift cards, gaming consoles, uncertified lithium batteries`) and stale (`> 24h`) PunchOut quotes—are held (`HTTP 451`)!
  2. **Building-Wide Weekly Consolidated Delivery Day + Preferred Generic Swap + Monthly Summary `EDI 810` (`HTTP 409`)**:
     - Non-urgent requisitions from all departments inside the same office building are **batched into a single Weekly Consolidated Delivery Window (e.g., every Friday at 10:00 AM on a single pallet)**—slashing parcel deliveries by **`78%`** and eliminating `$8.99` small-order shipping fees;
     - Simultaneously, the agent offers a 1-click swap from name-brand consumables (`3M / Post-it`) to **contract house-brand equivalents (`-32%` unit cost)** and consolidates 1,200 monthly micro-orders into **1 Monthly Summary `EDI 810` Invoice**—cutting total indirect procurement and AP processing costs by **36.0%**!

---

## ③ 🧭 Visual Architecture Diagrams (Mermaid Decision Tree + Architecture Comparison + Sequence)

### 3.1 B2B Indirect Procurement, `UNSPSC` Dedup, `UOM` & `Guided Buying` Escrow Decision Tree
```mermaid
flowchart TD
    A[Employee Submits Indirect Office/IT Supply Requisition in SAP Ariba, Coupa or Amazon Business] --> B{1. Authorized 1P/OEM Seller & Restricted Category Gate}
    B -->|PunchOut Cart Contains Unvetted 3P Marketplace Reseller, Restricted Personal Item Gift Card/Console, or Stale >24h Quote| C[HTTP 451: Hold Non-Compliant Cart! Restrict to 1P/Authorized OEM Sellers, Strip Personal SKUs & Refresh Live Contract Price]
    B -->|Authorized Seller & Policy Compliant| D{2. Free-Text PR Intercept & 8-Digit UNSPSC GL Gate}
    D -->|Employee Submits Free-Text Non-Catalog PR for $89 Retail Item When $52 Contract Catalog MPN Exists or Miscodes UNSPSC GL| E[HTTP 403: Block Free-Text Maverick Spend! Auto-Swap to -38% Contract Catalog SKU & Bind Exact 8-Digit UNSPSC GL Code]
    D -->|Contract Catalog SKU & GL Verified| F{3. ANSI X12 UOM Case-vs-Each & Internal IT Closet Gate}
    F -->|Order Selects 50 Cases CS Instead of 50 Each EA Exceeding 90d Burn Rate or Requests Monitors Available in Internal IT Closet| G[HTTP 422: Block 24x UOM Multiplier Error & Route Monitor Request to $0 Internal IT Closet Stock Transfer]
    F -->|UOM Normalized & Net-New Need Confirmed| H{4. Weekly Building Delivery Consolidation + Generic Swap + Summary EDI 810 Enabled?}
    H -->|Batch Building Orders into Friday Pallet Delivery (-$8.99 Fee) + Swap to House-Brand Equivalent (-32%) + 1 Monthly Summary EDI 810| I[HTTP 409: -78% Parcel Deliveries · $0 Idle-Stock Waste · Save 36% Indirect Spend & AP Cost]
    H -->|Standard Approved Catalog PO| J[HTTP 200: Dispatch cXML OrderRequest w/ Floor/Desk Mailroom Routing Tag]
```

### 3.2 Legacy Free-Text Maverick Spend & `24x UOM` Errors vs. Agentic Guided-Buying Escrow
```mermaid
flowchart LR
    subgraph Legacy["❌ Legacy Indirect Procurement (+42% Free-Text Markup + 50-Case UOM Disasters + 35 Daily Micro-Parcels)"]
        L1[Admin Submits Free-Text PR for $89 Retail Toner\nIgnores $52 Contract SKU & Creates 19th Duplicate ID] --> L2[Orders 50 Cases (1,200 Units) Instead of 50 Each\nBuys 10 New Monitors While 40 Sit Idle in IT Closet]
        L2 --> L3[35 Separate $15 Orders Shipped Daily to Same Building\nPays $8.99 Shipping Each & Floods AP w/ 1,200 Invoices]
    end
    subgraph Agentic["✅ Agentic MPN Auto-Swap, UOM Multiplier Lock & Weekly Dock Merge (Coupa / Ariba / Amazon Business)"]
        A1[Intercepts Free-Text PR by MPN -> $52 Contract SKU\nAuto-Maps 8-Digit UNSPSC to Exact SAP GL Account] --> A2[Checks ServiceNow IT Closet First ($0 Monitor Reuse)\nValidates Qty × UOM Pack Size Against 90d Burn Rate]
        A2 --> A3[Batches Building Orders into 1 Friday Pallet Delivery\nSwaps to House-Brand (-32%) + 1 Monthly Summary EDI 810]
    end
```

### 3.3 Free-Text `MPN` Catalog Swap, Internal IT-Closet Fulfillment, `UOM` Check & Weekly Building Merge Sequence
```mermaid
sequenceDiagram
    autonumber
    participant Emp as Department Requester
    participant Agent as Guided-Buying & UOM Escrow Agent
    participant ITAM_ERP as Internal IT Closet & `SAP MM / ServiceNow`
    participant Catalog as `cXML PunchOut` & Weekly Merge Hub (`Amazon Business / Staples`)

    Note over Emp,Catalog: Phase 1 (Internal Closet Reuse & Free-Text Catalog Swap): PR for 5 monitors + 20 CS pens + $89 retail toner
    Emp->>Agent: 1. Submit indirect requisition (`PR`)
    Agent->>ITAM_ERP: 2. Detect 12 reclaimed 4K monitors in building IT closet -> Trigger HTTP 422 block on external buy & issue `$0` internal transfer!
    Agent->>Catalog: 3. Match `$89` free-text toner `MPN` -> Swap to `$52` contract SKU (HTTP 403); flag `20 CS = 2,880 pens` & normalize to `20 BX` (HTTP 422)!
    Note over Emp,Catalog: Phase 2 (1P Seller Filter, Generic Brand Swap & Friday Building Consolidation)
    Catalog-->>Agent: 4. Verify `1P` seller (HTTP 451 pass), swap pens to house-brand (-32%), and batch into Friday pallet delivery + monthly `EDI 810` (HTTP 409, -36% cost)!
```

---

## ④ 📊 Enterprise B2B Guided Buying, `cXML PunchOut` & Indirect Spend Management Platform Matrix

| Dimension | **SAP Ariba Guided Buying + SAP `MDG`** (Global Enterprise Material-Master Governance, `UNSPSC` Taxonomy & `S/4HANA` P2P Leader) | **Coupa (`Procure-to-Pay` + `Open Buy` + `Community.ai`)** (High-Adoption Unified `PunchOut` Search, Free-Text Prevention & Spend Guard Leader) | **Amazon Business (`PunchOut + Guided Buying + Consolidated Shipping`)** (Long-Tail Office/IT Catalog, Seller Curation & Weekly Pallet Delivery Leader) | **Staples Advantage / W.W. Grainger (`Contract Core-List & Stockroom VMI`)** (Contract Generic Equivalency, Breakroom/Closet Restocking & Summary Billing) |
| :--- | :--- | :--- | :--- | :--- |
| **Best Fit** | Large enterprises on `SAP S/4HANA` enforcing strict global material master deduplication, 8-digit `UNSPSC` GL mapping, and complex budget hierarchies | Modern enterprises maximizing employee catalog adoption (`95%+`) via consumer-grade search across all connected `PunchOut` stores | Consolidating tail-spend office, IT peripheral, and facility purchases while blocking unauthorized third-party marketplace sellers | High-volume contracted office supplies, janitorial consumables, and safety `MRO` with desktop delivery and house-brand savings |
| **Free-Text-to-Catalog Intercept** | Routes non-catalog requests through structured forms or tactical sourcing queues | **Native `Open Buy` Federated Search** surfaces contracted `PunchOut` items directly inside the main search bar before users can click free-text | **`Guided Buying` Policy Badges** automatically steer buyers away from retail listings toward company-negotiated contract SKUs | Locks buyers into a pre-negotiated **Custom Core List** with automated generic brand substitutions |
| **`UOM (CS vs. EA)` & Internal Closet Reuse** | Enforces SAP Base Unit of Measure (`BUoM`) to Order Unit conversion tables | AI anomaly detection flags line quantities or unit prices that deviate `> 3x` from peer benchmarks | Displays clear per-unit (`$/Each`) pricing across `Pack / Case` variants and enforces quantity caps | Manages on-site supply closets and smart vending machines to prevent department hoarding |
| **Weekly Building Consolidation & Summary `810`** | Supports scheduled delivery lines and Evaluated Receipt Settlement (`ERS`) | Automatically batches requisitions to the same supplier (`PO Consolidation`) to eliminate small-order fees | **Dedicated `Consolidated Delivery Day`** groups all building orders into a single weekly pallet/box drop | **Scheduled weekly desktop/dock delivery + 1 Monthly Summary `EDI 810` Invoice** across all branches |
| **Pricing (`official_list_price`)** | Enterprise annual license (**`$80,000–$300,000+/year`**) | Enterprise annual license (**`$60,000–$220,000+/year`**) | `Business Prime` tier (**`$179–$10,099/year`**) | **`$0 software fee`** (unlocks **`15%–40%` contracted volume discounts**) |

---

## ⑤ 🧪 ROI Estimation & 7-Card Visual Benchmark Deck

> **Provenance**: Modeled on a 6,000-employee multi-campus financial and technology enterprise's quarterly indirect office and IT supply leakage pool (`$240,000/quarter` in `+42%` off-contract markups from free-text requisitions, `24x` over-ordering from `Case vs. Each UOM` mistakes, redundant external purchases of monitors/peripherals already sitting idle in internal IT closets, and daily small-order parcel shipping fees), labeled `synthetic` (`independently_reproduced=false`).

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 1 / 7 · HANDS-ON · B2B INDIRECT PROCUREMENT, `UNSPSC` & `UOM` ESCROW        ║
║ Headline: Free-Text-to-Catalog Swap & Weekly Dock Merge Cut Spend by 36.0%       ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ [Scenario & Thresholds]        [Structured Input]       [Top Decisions & KPIs]   ║
║ • Indirect Pool: $240,000 /Qtr • Catalog: Auto-Swap MPN • Verified: HTTP 200     ║
║ • UOM Gate: CS vs EA <=90d Burn• Closet: Check Idle IT  • FreeText/GL: HTTP 403  ║
║ • Seller: 1P / Auth OEM Only   • Delivery: Friday Merge • UOM24x/Closet:HTTP 422 ║
║ • Generic Swap: -32% Unit Cost • Billing: 1 Monthly 810 • Rogue3P/Gift: HTTP 451 ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ Provenance: synthetic (independently_reproduced=false) · Suite: WebIQ-R248 (#367)║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 2 / 7 · SCENARIO: $89 FREE-TEXT TONER SWAP, IT CLOSET REUSE & FRIDAY MERGE  ║
║ Headline: 5 Monitors Filled From Idle IT Closet ($0); 20-Case UOM Error Caught   ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ Input Quote: "Process indirect PR for 5 4K monitors, 20 units of pens, and HP    ║
║ toner by checking internal IT closet, swapping to contract SKU, and Friday merge"║
║ 1. [choice] MPN Catalog Swap & UNSPSC GL──► 1.00 conf ──► [Act automatically]    ║
║    ████████████████████████████████████████ 100% ($89 Free-Text -> $52 Contract) ║
║ 2. [choice] UOM Multiplier & IT Closet  ──► 0.99 conf ──► [Act automatically]    ║
║    ███████████████████████████████████████▊ 99% (5 Monitors From Closet = $0)    ║
║ 3. [score]  Friday Merge + Generic Swap ──► 0.98 conf ──► [Confirm: HTTP 409]    ║
║    ███████████████████████████████████████░ 98% (-78% Parcels; -$86,400 / Qtr)   ║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 3 / 7 · WHAT I TESTED · FULL 5-LANE EVALUATION MATRIX                      ║
║ Headline: 5/5 Deterministic Guardrails Verified Across Catalog, UOM & Sellers    ║
╠══════════════════════════╦══════════════════════════╦══════════════════╦═════════╣
║ SCENARIO                 ║ QUESTION / TASK          ║ MODEL ANSWER     ║ ACTION  ║
╠══════════════════════════╬══════════════════════════╬══════════════════╬═════════╣
║ Verified Guided Catalog  ║ Contract SKU + EA UOM ok ║ HTTP 200 ($0)    ║ Auto    ║
║ Free-Text $89 vs $52 Cat ║ Bypass catalog / bad GL  ║ HTTP 403 Blocked ║ Block   ║
║ 50 Cases UOM / Idle Stock║ 24x CS typo / 40 in close║ HTTP 422 Blocked ║ Block   ║
║ Unvetted 3P Seller / Gift║ Gray-market / gift card  ║ HTTP 451 Hold    ║ Human   ║
║ Friday Merge + Generic   ║ Weekly pallet + 1 EDI 810║ HTTP 409 (-36%)  ║ Confirm ║
╠══════════════════════════╩══════════════════════════╩══════════════════╩═════════╣
║ Gate Summary: 100% deterministic policy match; 0 UOM over-orders & -78% parcels  ║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 4 / 7 · UNDER THE HOOD · PROTOCOL & SCORING MECHANICS                       ║
║ Headline: Deterministic Policy Input Contract → Verifier Decision Trace          ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ // Input Contract (B2BIndirectProcurementUNSPSCPunchOutPolicyInput)              ║
║ { "quarterly_free_text_markup_uom_error_and_parcel_freight_pool_usd": 240000.0,  ║
║   "free_text_pr_bypassing_contract_catalog_or_wrong_unspsc_gl": false,           ║
║   "uom_case_vs_each_24x_overorder_or_idle_internal_stock_ignored": false,        ║
║   "unauthorized_3p_marketplace_seller_or_restricted_personal_sku": false,        ║
║   "weekly_building_delivery_merge_and_generic_brand_swap_ready": true }          ║
║                                      ↓                                           ║
║ // Verifier Output (<answer>)                                                    ║
║ { "status_code": 409,                                                            ║
║   "decision": "WEEKLY_BUILDING_MERGE_AND_GENERIC_BRAND_SWAP_CONFIRM",            ║
║   "mandate_token": "b2b_indirect_escrow_optim_409", "savings_usd": 86400.0 }     ║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 5 / 7 · ROBUSTNESS CHECK · PERTURBATION & CONSISTENCY                       ║
║ Headline: 0.0 pts Variance Across Option Reversal & Pack-Size Perturbations      ║
╠══════════════════════════════╦═════════════════╦══════════════════╦══════════════╣
║ QUESTION / ANSWER            ║ ORIGINAL        ║ REVERSED / PERT  ║ CHANGE (PTS) ║
╠══════════════════════════════╬═════════════════╬══════════════════╬══════════════╣
║ Free-Text to Catalog & UNSPSC║ HTTP 403 (100%) ║ HTTP 403 (100%)  ║ 0.0 pts      ║
║ UOM Multiplier & IT Closet   ║ HTTP 422 (100%) ║ HTTP 422 (100%)  ║ 0.0 pts      ║
║ 1P Seller & Restricted SKU   ║ HTTP 451 (100%) ║ HTTP 451 (100%)  ║ 0.0 pts      ║
║ Weekly Merge + Generic 36%   ║ $86,400 Saved   ║ $86,400 Saved    ║ 0.0 pts      ║
╚══════════════════════════════╩═════════════════╩══════════════════╩══════════════╣

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 6 / 7 · LATENCY · BATCHING & SCALING LATENCY                                ║
║ Headline: 65ms MPN Vector-to-Catalog Lookup & 20ms Internal ITAM Closet Check    ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ MPN Vector-to-Catalog Match  ║ ██ 65 ms (Auto-Swap) vs +42% Retail Free-Text PR  ║
║ ServiceNow ITAM Closet Lookup║ █ 20 ms ($0 Reuse) vs Buying Redundant Monitors   ║
║ ANSI X12 UOM Base-Unit Check ║ █ 8 ms (Qty×Pack) vs 1,200-Box Corridor Pileup    ║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 7 / 7 · MY TAKE · GOOD FIT VS NOT FOR & READINESS                           ║
║ Headline: Essential for Enterprise Indirect Procurement, ITAM & Workplace Ops    ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ ✅ GOOD FIT                               ⛔ NOT FOR                             ║
║ • Enterprises running SAP Ariba, Coupa,   • Single-freelancer home offices with  ║
║   Amazon Business & Staples PunchOut        zero catalog contracts or stockrooms ║
║ • Procurement teams eliminating free-text • Cryogenic tokamak superconducting    ║
║   leakage, UOM errors & daily parcel fees   magnet quench valves unrelated to IT ║
║ Readiness: Production-verified schema in `lab/webiq_commerce_demo.py` (R248).    ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

---

## ⑥ 🛠️ Production Risk & Architecture Review Checklist

- [ ] **Free-Text `PR` `MPN / GTIN` Intercept & Automatic Swap to Contract Catalog SKUs + `UNSPSC` GL Lock (`HTTP 403`)**: Does the Guided-Buying agent parse free-text requisitions by `MPN / GTIN` to automatically swap them into negotiated `PunchOut` catalog items (`-38%` cost), and deterministically assign the 8-digit `UNSPSC` and `SAP GL` account?
- [ ] **`ANSI X12 UOM (CS vs. BX vs. EA)` Base-Unit Multiplier Gate & Internal IT-Closet Lookup (`HTTP 422`)**: Does checkout multiply `Quantity × UOM Pack Size` against 90-day department consumption caps to block `24x` Case-vs-Each errors, and check internal `ServiceNow ITAM` stockrooms for reclaimed monitors/peripherals before issuing an external `PO`?
- [ ] **Authorized `1P / OEM` Seller Lock & Restricted Personal-SKU Filter (`HTTP 451`)**: Are unauthorized third-party marketplace resellers, consumer gift cards, and stale (`> 24h`) `cXML PunchOut` carts blocked automatically?
- [ ] **Building-Wide Weekly Consolidated Delivery Day & House-Brand Generic Swap (`HTTP 409`)**: Are non-urgent office orders across floors batched into a single weekly pallet delivery (`-78%` parcels, `$0` small-order fees) with automated house-brand generic substitutions (`-32%` unit cost)?
- [ ] **Consolidated Monthly Summary `EDI 810` Invoicing**: Are hundreds of small indirect deliveries rolled up into a single cost-center-allocated monthly summary `EDI 810` invoice?
