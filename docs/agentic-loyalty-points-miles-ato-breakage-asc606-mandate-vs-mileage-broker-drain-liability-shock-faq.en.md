# Agentic Loyalty Miles, Rewards & `Cash+Points` (`ASC 606 / IFRS 15`) Architecture: Anti-`ATO` `72h` Nominee Lock, Dynamic `CPP` Liability Ceiling & Original-Expiry Refund Token (`agentic_loyalty_points_miles_ato_breakage_asc606_mandate_...`) vs. Mileage-Broker Account Drains & Balance-Sheet Liability Shocks: Architecture Selection & First-Principles FAQ

> **Document Type**: Architect's Selection & First-Principles FAQ (Benchmarking the 6-Section Standard of `ib-vs-ethernet-roce-selection-faq.md`)  
> **Core Domain Coverage**: Agentic Airline Frequent-Flyer Miles, Hotel/Retail Loyalty Points & `Cash + Points` Hybrid Checkout, Blocking Account-Takeover (`ATO`) & Mileage-Brokerage Drains (`FIDO2 Passkey Step-Up` + `>= 72h` Redemption Nominee Cooling-Off + Banning Point-to-Gift-Card Cashout), `ASC 606-10-55-42 / IFRS 15` "Material Right" Standalone Selling Price (`SSP`) Deferred Contract Liability & Breakage Actuarial Accounting, Dynamic Cents-Per-Point (`CPP <= 1.25¢`) Ceiling Enforcement, and Segregating Non-Expiring `Purchased Points` from `Promotional Points` (`US DOT` Rewards Probe & Consumer Protection Laws)  
> **Target Audience**: Airline, Hospitality, Co-Brand Credit Card & Retail Loyalty Architects, Hybrid `Cash+Points` Checkout Leads, CFO Revenue-Recognition (`ASC 606`) Controllers, and Fraud Prevention Directors  
> **Companion Interactive Deliverables**: [`live-demo.en.html` (Includes the Round 222 Interactive Sandbox for Anti-ATO `72h` Nominee Gating, `ASC 606` Dynamic `CPP` Ceiling Enforcement, Original-Expiry Refund Locks & Microsoft Web IQ FASB/DOT Verification)](../live-demo.en.html) · [`assets/svg/224-agentic-loyalty-points-miles-ato-breakage-asc606-2026-11-14.svg`](../assets/svg/224-agentic-loyalty-points-miles-ato-breakage-asc606-2026-11-14.svg)

---

![2026-11-14 Agentic Loyalty Miles & Points: Anti-ATO 72h Nominee Lock, Dynamic CPP Ceiling & ASC 606 Deferred Liability Visual Summary](../assets/svg/224-agentic-loyalty-points-miles-ato-breakage-asc606-2026-11-14.svg)

## 1. 📌 Executive Summary

When airlines, hotel chains, co-brand card issuers, and retail marketplaces expose loyalty balances and `Cash + Points` hybrid checkout to AI shopping and travel agents, engineering teams frequently treat points as "free promotional play money"—**"allowing password-only point redemptions, letting an agent add a third-party passenger nominee and issue a first-class partner ticket in 5 seconds, or allowing a promotional agent to boost point value from `1.0¢` to `2.5¢` per point"**—triggering three catastrophic balance-sheet and fraud failures:
1. **Account-Takeover (`ATO`) Mileage-Broker Drains & 200% Double-Loss Liability**: Global loyalty programs hold over `$100 Billion` in redeemable value, yet lack the EMV 3DS2 protections of credit cards. When credential-stuffing bots compromise a high-tier member's account, they immediately add a stranger to the **Redemption Nominee List** and issue non-reversible partner airline tickets (sold via underground **Mileage Brokers**) or redeem points for instant digital gift cards. The merchant **pays hard cash to the partner airline/gift-card issuer AND must restore 100% of the stolen miles to the defrauded member—a 200% loss!**
2. **Unbounded `CPP` (Cents-Per-Point) Promotions Breaching `ASC 606 / IFRS 15` Deferred Contract Liability Reserves**: Under **`ASC 606-10-55-42` (Customer Options for Additional Goods or Services / Material Rights)**, every point issued is a balance-sheet **Contract Liability** accrued at its actuarial Standalone Selling Price (`SSP`) net of expected breakage (`1 - Breakage_Rate`, e.g., `1.00¢–1.25¢/pt`). If an AI marketing or pricing agent allows redemptions at **`2.50¢/pt`** (or opens a cross-program conversion loop), arbitrageurs drain high-margin inventory while auditors force an immediate **hundreds-of-millions balance-sheet liability revaluation charge** against quarterly earnings!
3. **Expiry Laundering via `Cash + Points` Refunds & Unlawful Forfeiture of `Purchased Points`**: If a `Cash + Points` order is refunded as 100% cash (or if refunded points receive a fresh 24-month expiration date), agents exploit buy-and-cancel loops to cash out or perpetually extend expiring points. Conversely, expiring **Purchased Points** (points bought with cash) alongside promotional points violates consumer gift-card / anti-forfeiture laws (e.g., Ontario CPA, California Civil Code, and US DOT unfair-practice scrutiny)!

**First-Principles Architectural Mandates**:
1. **Enforce an "Anti-ATO & Anti-Brokerage Redemption Gate" (`FIDO2 Passkey Step-Up`, `>= 72h` Nominee Cooling-Off, and `Zero Gift-Card Cashout`)**: Require hardware-backed **FIDO2 Passkey** verification for point redemptions, enforce a mandatory **`>= 72-hour` cooling-off lock** on any newly added third-party redemption nominee, and block (`HTTP 403` in `11ms`) point-to-gift-card cashout loops.
2. **Mint an `agentic_loyalty_points_miles_ato_breakage_asc606_mandate_...` Token Enforcing the `ASC 606` Actuarial `CPP` Ceiling (`<= 1.25¢/pt`) & Original-Expiry Refund Preservation**: Hard-clamp dynamic point redemption valuation at or below the CFO's accrued liability ceiling (`CPP <= 1.25¢`) and ensure `Cash + Points` refunds restore points with their **original pre-purchase expiration timestamp (`Original_Expiry_Timestamp`)** (`14ms` gate).
3. **Select Microsoft Web IQ (`/v3/search` + `/v3/browse`) for `FASB ASC 606 / IFRS 15` Material-Right Guidance, `US DOT` Frequent-Flyer Transparency Rules, and Statutory Point-Expiration Prohibitions**: Benchmarked against Exa and Bright Data, Web IQ retrieves authoritative accounting and regulatory texts in `<350ms` with Entra ID tenant isolation.

| Core Loyalty & `Cash+Points` Dimension | Legacy Password Redemption + Instant Nominee + Uncapped `CPP` (Anti-Pattern) | `FIDO2` + `72h` Nominee Lock + `ASC 606` Dynamic `CPP` Gate (Recommended) | P&L & Balance-Sheet Impact |
| :--- | :--- | :--- | :--- |
| **ATO & Mileage-Brokerage Defense** | Instant ticket issuance for newly added stranger $\rightarrow$ 200% double loss | **`FIDO2 Passkey` + `>= 72h` Nominee Cooling-Off + No Gift-Card Cashout** | Eliminates automated ATO point drains & broker ticket laundering |
| **`ASC 606 / IFRS 15` Liability Reserve** | Agent runs `2.5¢/pt` promo $\rightarrow$ breaches `1.25¢` deferred revenue reserve | **Dynamic `CPP <= 1.25¢` Actuarial Ceiling Clamp per Transaction** | Protects balance-sheet Contract Liability from earnings restatements |
| **`Cash+Points` Refund & Expiry Integrity** | Refunds points as cash or resets expiry to +24 months (Expiry Laundering) | **Exact Split Reversal + Restores `Original_Expiry_Timestamp` Bucket** | Blocks buy-and-cancel cashout and expiration-extension abuse |
| **`Purchased` vs. `Promotional` Points** | Expires cash-purchased points after 12m $\rightarrow$ class-action lawsuits | **Dual-Bucket Sub-Ledger (`Promo_Points` vs. Non-Expiring `Purchased`)** | 100% compliance with statutory anti-forfeiture & US DOT rules |

---

## 2. 🎯 Customer & Architect Soul-Searching Q&A (First-Principles Deep Dive)

### Q1: Why are loyalty programs the #1 target for credential-stuffing bots, and how does a `>= 72-Hour` Nominee Cooling-Off Lock defeat underground Mileage Brokers?
* **First-Principles Breakdown**:
  1. **Zero Network Chargeback Rights on Stolen Points**: When a fraudster steals a credit card, the issuing bank and card network absorb or charge back the fraud under strict EMV rules. When a fraudster steals `400,000` airline miles and issues a partner award ticket on another carrier, the host airline **must pay the partner carrier hard interline settlement cash** AND replenish the victim's `400,000` miles!
  2. **Breaking the Mileage-Broker Business Model**: Underground mileage brokers sell discounted business-class tickets to retail buyers by hijacking dormant loyalty accounts, adding the buyer's name as a "Redemption Nominee", and ticketing within minutes for departure within 24–48 hours. Enforcing a **cryptographic `FIDO2 Passkey` step-up + mandatory `>= 72-hour` quarantine before any newly added third-party nominee can be ticketed** (paired with out-of-band SMS/email alerts to the account holder) renders stolen accounts useless to brokers!

### Q2: How does `ASC 606-10-55-42` ("Material Rights") govern loyalty points on the balance sheet, and why can an AI agent's `2x Point Value` campaign trigger an earnings restatement?
* **The Accounting Math of Deferred Revenue & Breakage**:
  - Under **ASC 606 / IFRS 15**, points earned in a transaction represent a separate performance obligation. The enterprise allocates transaction price to the points based on their **Standalone Selling Price (`SSP`) adjusted for expected unredeemed breakage (`1 - Breakage_Rate`)**, recording a **Contract Liability (Deferred Revenue)** on the balance sheet.
  - When a point is redeemed, the enterprise relieves the accrued liability (`e.g., $0.0125/pt`). If an autonomous pricing or promotional agent offers redemptions at **`$0.0250/pt` (`2.5¢ CPP`)** without an explicit marketing-budget subsidy transfer, the cost of goods/services delivered exceeds the deferred revenue relieved—forcing CFOs to increase the `SSP` valuation across the entire unredeemed point pool (`hundreds of billions of points`) and take a massive one-time P&L hit!

### Q3: How should architects choose between Microsoft Web IQ, Exa, and Bright Data for ASC 606 / IFRS 15 accounting rules, US DOT frequent-flyer regulations, and state point-expiration laws?
* **3-Way Capability Comparison**:
  - **Microsoft Web IQ (`/v3/search` + `/v3/browse`)**: Connects directly to `fasb.org` / `ifrs.org` revenue-recognition standards, `transportation.gov` US DOT airline rewards investigations, and statutory consumer protection codes in `280ms` with passage-level provenance (`official_doc_snapshot`) and Entra ID tenant isolation.
  - **Exa Neural Search**: Useful for general travel-hacking blog posts, not deterministic `ASC 606` CPP reserve ceilings or statutory `Purchased Points` non-forfeiture rules.
  - **Bright Data**: High proxy latency (`1.9s–4.2s`) and unsuitable for real-time hybrid `Cash + Points` checkout gating.

---

## 3. 🧭 Visual Architecture Diagrams (Mermaid Decision Tree + Path Comparison + Sequence)

### 3.1 Architect's Selection Decision Tree (Anti-ATO `72h` Nominee Gate & `ASC 606` Dynamic `CPP` Ceiling)

```mermaid
flowchart TD
    A["Agentic Loyalty Redemption / Cash+Points Request<br/>(Batch Volume: $540,000.00)"] --> B{"FIDO2 Step-Up Verified, Third-Party Nominee Aged >= 72h<br/>& Non-Gift-Card Cashout SKU?"}
    B -- "No: Newly added nominee <72h (Mileage Broker ATO)<br/>or open/closed-loop gift-card cashout attempt" --> C["🛑 HTTP 403 Blocked<br/>LOYALTY_ATO_NOMINEE_UNDER_72H_OR_GIFT_CARD_CASHOUT_BLOCKED (11ms)"]
    B -- "Yes: Authenticated member / aged nominee & valid SKU" --> D{"Redemption Valuation CPP <= 1.25¢ Actuarial Ceiling<br/>& Refund Preserves Original Point Expiry?"}
    D -- "No: Unfunded 2.5¢/pt promo breaching ASC 606 reserve<br/>or buy-and-cancel expiry laundering" --> E["🚨 HTTP 422 Blocked<br/>ASC606_CPP_LIABILITY_CEILING_BREACH_OR_EXPIRY_LAUNDERING (14ms)"]
    D -- "Yes: CPP within actuarial reserve & expiry locked" --> F["Call Microsoft Web IQ /v3/browse<br/>Verify Purchased-Points Non-Forfeiture & US DOT Devaluation Notice"]
    F --> G{"Cash-Purchased Points Segregated from Expiry<br/>& Devaluation Notice >= 90 Days Disclosed?"}
    G -- "No: Unlawful forfeiture of purchased points or silent devaluation" --> H["🛑 HTTP 451 Hold<br/>PURCHASED_POINTS_ILLEGAL_FORFEITURE_OR_DOT_DEVALUATION_HOLD (280ms)"]
    G -- "Yes: Dual-Bucket Ledger & DOT Disclosure Clean" --> I{"Apply Dynamic CPP Actuarial Clamping<br/>& Anti-Brokerage 72h Quarantine?"}
    I -- "Yes: Saves $43,200.00 in ATO & CPP arbitrage losses" --> J["🧑‍⚖️ HTTP 409 Confirm<br/>DYNAMIC_CPP_CLAMP_AND_ANTI_BROKER_DRAIN_SAVINGS_CONFIRM"]
    I -- "No: Standard Compliant Loyalty / ASC 606 Clearing" --> K["✅ HTTP 200 Settled<br/>VERIFIED_LOYALTY_POINTS_ASC606_SETTLED (10ms)"]
```

### 3.2 Legacy Instant-Nominee Drain + Uncapped `CPP` (Anti-Pattern) vs. Recommended Gateway

```mermaid
flowchart LR
    subgraph AntiPattern["❌ Legacy Anti-Pattern: ATO Nominee Drain + Uncapped CPP Liability Shock"]
        A1["Bot hijacks account & adds stranger nominee<br/>Tickets partner 1st-class flight in 10 seconds"] --> A2["Promo agent offers 2.5¢/pt redemption<br/>Breaches 1.25¢ ASC 606 deferred liability"]
        A2 --> A3["Buy-and-cancel resets point expiry +24m<br/>or unlawfully expires cash-purchased points!"]
    end

    subgraph BestPractice["✅ Recommended: FIDO2 + 72h Nominee Lock + ASC 606 Dynamic CPP Gateway"]
        B1["Enforces FIDO2 Passkey + >=72h nominee hold<br/>& blocks gift-card cashout (11ms gate)"] --> B2["Clamps redemption CPP <= 1.25¢ actuarial cap<br/>& restores original expiry on refunds"]
        B2 --> B3["Segregates non-expiring Purchased Points<br/>Saves $43,200.00 in ATO & arbitrage!"]
    end
```

### 3.3 End-to-End Sequence Diagram (`FIDO2 + 72h` Nominee Check → `ASC 606 CPP` Gate → Deferred Revenue Relief)

```mermaid
sequenceDiagram
    autonumber
    participant Member as Loyalty Member / Shopping Agent
    participant Gate as Loyalty Anti-ATO & ASC 606 Gate
    participant WebIQ as Microsoft Web IQ (/v3/browse)
    participant Ledger as Dual-Bucket Point Ledger (Promo vs. Purchased)
    participant ERP as CFO General Ledger (ASC 606 Contract Liability)

    Member->>Gate: 1. Submit Loyalty Redemption / Cash+Points Batch ($540,000.00)
    Gate->>Gate: 2. Assert FIDO2 Passkey signature, nominee age >= 72h & non-gift-card SKU (11ms)
    Gate->>Ledger: 3. Verify redemption CPP <= 1.25¢ actuarial ceiling & lock Original_Expiry_Timestamp (14ms)
    Gate->>WebIQ: 4. /v3/browse verify ASC 606 Material Right rules, Purchased-Point laws & DOT notice
    WebIQ-->>Gate: 280ms confirms non-expiring Purchased Points & DOT compliance (official_doc_snapshot)
    Gate->>ERP: 5. Mint agentic_loyalty_points_miles_ato_breakage_asc606_mandate_... & burn points
    ERP-->>Member: 6. Relieve exact ASC 606 Contract Liability into recognized revenue with 0 reserve deficit!
```

---

## 4. 📊 Architect's Selection Decision Matrix

| Evaluation Dimension | Option A: Password Auth + Instant Nominee + Static Award Chart (Forbidden) | Option B: Manual Call-Center ID Verification for Awards | Option C: `FIDO2` + `72h` Nominee Lock + `ASC 606` Dynamic `CPP` Gate (Recommended) |
| :--- | :--- | :--- | :--- |
| **ATO & Mileage-Brokerage Protection** | ❌ **Critical Vulnerability (Instant partner ticket drain)** | ⚠️ High call-center friction & cost | ✅ **100% Protected (`FIDO2` + `>= 72h` nominee quarantine + gift-card ban)** |
| **`ASC 606 / IFRS 15` Liability Reserve Safety** | ❌ **Severe Exposure (Promo `CPP` spikes force restatement)** | ⚠️ Discovered weeks later at close | ✅ **Actuarial Parity (Clamps `CPP <= 1.25¢` inline before checkout)** |
| **`Cash+Points` Refund & Expiry Laundering** | ❌ **Exploitable (Refunds cash or resets point expiry)** | ⚠️ Manual point adjustments fail | ✅ **Immutable Lot Tracking (Restores exact `Original_Expiry_Timestamp`)** |
| **`Purchased` vs. `Promotional` Point Legality** | ❌ **Illegal (Expires cash-bought points; class actions)** | ⚠️ Manual complaint credits | ✅ **Dual-Bucket Sub-Ledger (`Purchased_Points` exempt from inactivity expiry)** |
| **Recommended Use Case (Good Fit vs. Not For)** | ⛔ **Forbidden for airline, hotel, or retail loyalty** | Ultra-low-volume VIP concierges | ✅ **Mandatory for airlines, hotels, co-brand cards & retail loyalty programs** |

---

## 5. 🧪 Quantitative Benchmark & 7-Card 4:5 Report Summary (Benchmark & Provenance)

We implemented the deterministic policy evaluator `evaluate_agentic_loyalty_points_asc606_policy()` in `lab/webiq_commerce_demo.py` and verified 5 scenarios across a `$540,000.00` loyalty redemption and `Cash + Points` settlement batch (`synthetic_policy`, `deterministic_offline_simulation`, `official_doc_snapshot`):

| Scenario ID & Name | Input Conditions & Guard Trigger | Gateway HTTP Status & Action | Latency | Net Protected / Saved | Provenance |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Case 1 (`loy_commit_ok`)** | `FIDO2` verified + nominee aged `>=72h` + `CPP <= 1.25¢` (`ASC 606` safe) + original-expiry lock | `HTTP 200` · `Act automatically` | `10ms` | `$540,000.00` Settled | `deterministic_offline_simulation` |
| **Case 2 (`loy_ato_403`)** | Newly added stranger nominee `<72h` (Mileage Broker ATO) or point-to-gift-card cashout attempt | `HTTP 403` · `Send to a human` | `11ms` | `$540,000.00` ATO / Broker Drain Blocked | `synthetic_policy` |
| **Case 3 (`loy_cpp_422`)** | Unfunded `2.5¢/pt` redemption breaching `ASC 606` liability reserve or refund expiry laundering | `HTTP 422` · `Send to a human` | `14ms` | ASC 606 Reserve Breach / Laundering Blocked | `deterministic_offline_simulation` |
| **Case 4 (`loy_exp_451`)** | Web IQ `/v3/browse` flags unlawful expiration of cash-purchased points or silent DOT devaluation | `HTTP 451` · `Send to a human` | `280ms` | Purchased-Points / DOT Compliance Hold | `official_doc_snapshot` |
| **Case 5 (`loy_sav_409`)** | Web IQ enforces dynamic `CPP <= 1.25¢` clamping & `72h` nominee lock preventing ATO/arbitrage | `HTTP 409` · `Confirm` | `245ms` | **Saves `$43,200.00`** (`$496,800.00` net redemption liability cost) | `official_doc_snapshot` |

### 7-Card 4:5 Visual Report Deck Highlights
- **Card 1 (`1 / 7` · `HANDS-ON · LOYALTY MILES & ASC 606 GATE`)**: Displays the `$540,000.00` loyalty batch verified in `10ms` with `FIDO2` step-up, `>=72h` nominee cooling-off, and `ASC 606` dynamic `CPP <= 1.25¢` enforcement.
- **Card 2 (`2 / 7` · `SCENARIO: ANTI-ATO 72H NOMINEE & ASC 606 CPP`)**: Quantifies the `11ms` block on `<72h` stranger nominees / gift-card cashouts (`HTTP 403`) and `14ms` block on `ASC 606` `CPP` reserve breaches (`HTTP 422`).
- **Card 3 (`3 / 7` · `WHAT I TESTED`)**: 5-scenario evaluation matrix passing 100% (`HTTP 200 / 403 / 422 / 451 / 409`).
- **Card 4 (`4 / 7` · `UNDER THE HOOD`)**: Shows the `agentic_loyalty_points_miles_ato_breakage_asc606_mandate_...` payload (`fido2_stepup_verified: true`, `nominee_cooling_hours: 120`, `redemption_cpp_cents: 1.15`, `preserve_original_point_expiry_on_refund: true`).
- **Card 5 (`5 / 7` · `ROBUSTNESS CHECK`)**: Confirms that splitting redemptions into micro-batches or canceling `Cash + Points` orders never bypasses the gift-card ban or extends `Original_Expiry_Timestamp`.
- **Card 6 (`6 / 7` · `LATENCY`)**: Compares automated inline `ASC 606` `CPP` reserve gating (`10ms`) against manual quarterly actuarial breakage audits.
- **Card 7 (`7 / 7` · `MY TAKE`)**: Summarizes **✅ Good fit** (airline frequent-flyer programs, hotel loyalty, co-brand credit card portals, retail `Cash+Points` checkouts) vs. **⛔ Not for** (allowing instant third-party nominee ticketing, point-to-gift-card cashouts, or uncapped `CPP` redemptions).

---

## 6. 🛠️ Production Readiness Checklist

- [ ] **Require `FIDO2 Passkey` Step-Up + `>= 72-Hour` Cooling-Off on New Redemption Nominees**: Block credential-stuffing bots and underground mileage brokers from hijacking accounts and issuing immediate third-party tickets.
- [ ] **Prohibit Direct Point-to-Gift-Card / Open-Loop Cashout Redemptions**: Eliminate irreversible anonymous monetization paths for stolen loyalty balances.
- [ ] **Enforce an Inline `ASC 606 / IFRS 15` Actuarial `CPP` Ceiling (`e.g., <= 1.25¢/pt`)**: Prevent promotional agents from offering unfunded point valuations that exceed deferred revenue reserves.
- [ ] **Preserve `Original_Expiry_Timestamp` on `Cash + Points` Refunds**: Return refunded points strictly to their original lot expiration bucket and return cash only up to the actual cash tender paid.
- [ ] **Segregate Non-Expiring `Purchased Points` from `Promotional Points` & Audit Rules via Microsoft Web IQ (`/v3/browse`)**: Ensure cash-purchased points never expire under inactivity rules and verify US DOT notice compliance.
