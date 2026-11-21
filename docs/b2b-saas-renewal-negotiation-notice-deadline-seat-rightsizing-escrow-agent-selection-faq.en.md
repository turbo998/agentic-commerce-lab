# Enterprise B2B SaaS Renewal Negotiation, Auto-Renewal `60-Day Opt-Out` Shield & `SSO / SCIM` Seat Right-Sizing Escrow (`Vendr / Tropic / Zylo / Productiv`): `T-95d` Tactical Non-Renewal Notice, `Creator-to-Viewer` Downgrade & Cloud `MACC/EDP` Drawdown Saving `34%` SaaS Spend — Agent Architecture Selection FAQ

> **Language / 语言**: **[中文 (`b2b-saas-renewal-negotiation-notice-deadline-seat-rightsizing-escrow-agent-selection-faq.md`)](b2b-saas-renewal-negotiation-notice-deadline-seat-rightsizing-escrow-agent-selection-faq.md)** | **English (Current)**  
> **Back to Catalog**: **[📚 English Catalog (`docs/index.en.md`)](index.en.md)** | **[🚀 Interactive Live Workbench (`live-demo.en.html`)](../live-demo.en.html)**  
> **Target Roles**: Enterprise IT Procurement & Software Asset Management (`SAM`) Leaders, CIOs / CFOs, FinOps & Vendor Management Directors, Cloud & AI Solution Architects  
> **Architecture Diagram**: `assets/svg/623-b2b-saas-renewal-notice-deadline-seat-rightsizing-escrow-2026-11-21.svg`

---

## ① 📌 Executive Summary

In mid-to-large enterprises, **B2B SaaS subscription spend** is the third-largest operating expense after payroll and cloud infrastructure (`$4M–$15M/year` across 180+ SaaS applications per 1,000 employees). Yet relying on passive renewal workflows—where IT managers only look at a contract when the vendor emails an invoice two weeks before expiration—exposes enterprises to four costly procurement traps:
1. **The Predatory "60/90-Day Auto-Renewal Notice Window" & `12%` Price-Uplift Trap**: Most enterprise SaaS order forms (`Salesforce / Datadog / Snowflake / HubSpot / Jira`) bury an auto-renewal clause stating that unless the buyer delivers written notice of non-renewal **at least 60 or 90 days prior to the end of the term**, the contract automatically locks in for another 12 months at the full prior seat count **plus a `7%–12%` annual price uplift**. Account executives stay silent until **Day `T-58`**, then send the uplifted invoice after the opt-out window has legally slammed shut—blocking any seat reductions or competitive leverage.
2. **Renewing `40%` Inactive "Shelfware" Seats & Paying `$75/mo Creator` Prices for Read-Only Viewers**: A company renews 500 enterprise licenses even though 65 employees haven't logged in via `Okta / Entra ID` in 90 days, and another 95 executives/PMs only view dashboards (`0` create/edit actions in 90 days) and could sit on `$0–$12/mo Viewer` licenses instead of `$75/mo Full Creator` seats.
3. **Shadow-IT Credit-Card Sprawl & Unprotected AI Model-Training Data Leakage**: Six different departments swipe corporate cards (`Ramp / Brex / Amex`) for standalone team plans of the same SaaS tool already covered by an enterprise agreement—paying 40% list-price premiums while exposing corporate data in unmanaged workspaces lacking `Zero-Data-Retention (ZDR) & No-LLM-Training DPAs`.
4. **Price Opacity (`45%` Variance Across Identical Cohorts) & Unburned `Azure MACC / AWS EDP` Cloud Commitments**: Paying direct vendor invoices with fresh cash while `$400,000` in committed `Azure MACC` or `AWS EDP` cloud spend sits unburned at year-end.

**Architectural Verdict**: Deploy a **4-Lane Enterprise B2B SaaS Renewal & Seat Right-Sizing Escrow Architecture**: **Automated `T-95d` Tactical Non-Renewal Opt-Out Notice & `<=3%` Renewal Uplift Cap (`HTTP 403`) + Pre-Renewal `Okta / Entra SCIM` 60-Day Zombie-Seat Reclaim & 90-Day Read-Only `Creator → Viewer` Downgrade Gate (`HTTP 422`) + Shadow-IT Card Consolidation & Mandatory `Zero-Data-Retention AI DPA` Lock (`HTTP 451`) + Peer `P25` Price-Benchmark Negotiation (`Vendr / Tropic`) & `Azure MACC / AWS EDP` Cloud Marketplace Private-Offer Drawdown (`HTTP 409`)**, reducing net enterprise SaaS spend by **34.0%**.

![B2B SaaS Renewal Negotiation & SSO Seat Right-Sizing Escrow Architecture](../assets/svg/623-b2b-saas-renewal-notice-deadline-seat-rightsizing-escrow-2026-11-21.svg)

---

## ② 🎯 Business & Architect Deep-Dive Q&A

### Q1: Why do SaaS vendors wait until Day `T-58` to send renewal quotes, and how does an automated `T-95d` Tactical Opt-Out Notice flip negotiation leverage back to the buyer?
- **Business Pain**: If a contract has a 60-day cancellation notice window, the vendor's sales playbook is to avoid contacting the buyer until Day 59. Once Day 60 passes without written opt-out notice, the buyer is legally locked into 100% of their peak seat count plus the contract's default uplift.
- **Architectural Guardrail (`HTTP 403 MISSED_OPT_OUT_WINDOW_OR_UNCAPPED_UPLIFT_BLOCKED`)**:
  1. **Contract Ingestion `OCR` & Automated `T-95d` Tactical Non-Renewal Dispatch**: Upon contract signature, the Agent extracts `Term_End_Date`, `Opt_Out_Notice_Days (30/60/90d)`, and `Renewal_Uplift_Cap`. Exactly 35 days before the notice deadline (`T-95d` to `T-125d`), the Agent dispatches a timestamped, contractually compliant **Tactical Notice of Non-Renewal** to the vendor's legal/billing alias stating: *"We hereby suspend automatic renewal to evaluate seat utilization and commercial terms."* This legally disarms the auto-lock and forces the account executive to negotiate to win back the renewal.
  2. **Mandatory `<=3%` Renewal Uplift Cap & Cross-SKU Swap Rights**: Order forms containing uncapped renewal price increases or uplifts `>3%` above CPI are blocked prior to signature (`HTTP 403`).

### Q2: Why is checking `Okta` login timestamps alone insufficient, and how do we automate `Creator-to-Viewer` tier downgrades before the renewal quote is generated?
- **Business Pain**: Employees who open a shared link once a month generate an `Okta SAML` login event, making them look "active." Yet inside tools like `Figma, Jira, Miro, Tableau, or Salesforce`, 35% of licensed `Full Creators ($75/mo)` never create, edit, or export a single object.
- **Architectural Guardrail (`HTTP 422 UNHARVESTED_ZOMBIE_SEATS_OR_PRO_WASTE_BLOCKED`)**:
  1. **Two-Stage `SCIM 2.0` Zombie Reclaim & Feature-Telemetry Tier Downgrade**: Approving a flat or expanded renewal quote without running a 90-day telemetry harvest is blocked (`HTTP 422`). At `T-90d`, the Agent executes:
     - **60-Day Zero-Login De-Provisioning**: Reclaims licenses from users with `0` logins in 60 days (and instant `0s` revocation on `Workday / Rippling` termination).
     - **90-Day Zero-Write `Creator → Viewer` Downgrade**: Queries the SaaS Admin Activity API (`Write_Events_90d == 0`) and downgrades passive consumers from `$75/mo Creator/Enterprise` seats to `$0–$12/mo Viewer/Read-Only` tiers—slashing baseline license counts by **28%+**.

### Q3: How do we eliminate duplicate "Shadow IT" credit-card subscriptions across departments and route SaaS renewals through `Azure MACC / AWS EDP` cloud commitments?
- **Business Pain**: Individual managers expense standalone team subscriptions on corporate cards at full retail price while exposing company IP to default AI training terms. Meanwhile, the CIO has unburned cloud commit dollars sitting in Azure or AWS.
- **Architectural Guardrail (`HTTP 451 SHADOW_IT_DUPLICATE_SPEND_OR_AI_DPA_HOLD` & `HTTP 409` P25 + MACC Burn)**:
  1. **Shadow-IT Expense/OAuth Scanner & `No-LLM-Training DPA` Gate (`HTTP 451`)**: The Agent cross-correlates `Ramp / Brex / Concur` card descriptors and Google/Microsoft `OAuth` app grants against the master contract registry. Duplicate departmental subscriptions and AI tools lacking a signed `Zero-Data-Retention / No-Model-Training DPA` are held (`HTTP 451`) and consolidated into the enterprise SSO tenant.
  2. **Peer `P25` Price Benchmarking (`Vendr / Tropic`) & Cloud Marketplace `Private Offer` Drawdown (`HTTP 409`)**: Grounds renewal quotes against anonymized peer `P25` (top-quartile discount) unit prices for the exact seat tier, then structures the final purchase as an **Azure Marketplace (`MACC`) or AWS Marketplace (`EDP`) Private Offer**—capturing a `25%–35%` unit discount while burning down 100% pre-committed cloud spend (**-34.0%** net SaaS spend reduction).

---

## ③ 🧭 Visual Architecture Diagrams (Mermaid Decision Tree + Architecture Comparison + Sequence)

### 3.1 Enterprise B2B SaaS Renewal & Seat Right-Sizing Decision Tree
```mermaid
flowchart TD
    A[SaaS Contract Enters T-120d Renewal Window / New Purchase Request] --> B{1. Shadow-IT Card Sprawl & AI-DPA Gate}
    B -->|Duplicate Departmental Card Subscriptions Found or Missing No-LLM-Training ZDR DPA| C[HTTP 451: Freeze Rogue Cards · Consolidate into Enterprise SSO & Enforce AI DPA]
    B -->|Unified Enterprise Tenant & Signed DPA| D{2. T-95d Auto-Renew Opt-Out & Uplift Cap Gate}
    D -->|60/90d Opt-Out Notice Not Sent or Order Form Contains >3% Uncapped Renewal Uplift| E[HTTP 403: Auto-Send Tactical Opt-Out Notice & Block Uncapped Uplift Clauses]
    D -->|Leverage Secured & Uplift Capped <=3%| F{3. Okta SCIM Zombie Reclaim & Viewer Downgrade Gate}
    F -->|60d Inactive Zombie Seats Unharvested or 90d Read-Only Users Left on $75 Creator Tier| G[HTTP 422: Reclaim Inactive Seats via SCIM & Downgrade Read-Only Users to Viewer]
    F -->|Seat Count Right-Sized to Active Usage| H{4. Peer P25 Benchmark + Cloud MACC/EDP Private Offer Enabled?}
    H -->|Negotiate to Peer P25 Price + Route via Azure MACC / AWS EDP Private Offer| I[HTTP 409: Cut Net Enterprise SaaS Spend by 34% & Burn Cloud Commit]
    H -->|Standard Direct PO Renewal| J[HTTP 200: Compliant Right-Sized SaaS Renewal Authorized]
```

### 3.2 Legacy Passive Auto-Renewal vs. Agentic `T-95d` Shield, `SCIM` Trim & `MACC` Drawdown
```mermaid
flowchart LR
    subgraph Legacy["❌ Legacy Passive SaaS Renewal (Day-58 Trap + 40% Shelfware + Shadow IT)"]
        L1[Vendor Waits Until Day T-58\nLocks 100% Seats + 12% Uplift] --> L2[500 Seats Renewed Blindly\n160 Idle or Read-Only on $75 Tier]
        L2 --> L3[6 Teams Swipe Corporate Cards\nPay List Price & Leak Data to AI]
        L3 --> L4[$300k Unburned Azure MACC Penalty\nWhile Paying SaaS Vendors in Cash]
    end
    subgraph Agentic["✅ Agentic SaaS Renewal & SAM Escrow (Vendr / Zylo + Okta SCIM + MACC)"]
        A1[T-95d Tactical Non-Renewal Notice\nLocks <=3% Uplift Cap & Swap Rights] --> A2[SCIM Reclaims >60d Inactive Seats\nDowngrades 0-Write Users to Viewer]
        A2 --> A3[Merges Shadow-IT Card Subscriptions\nEnforces Zero-Data-Retention AI DPA]
        A3 --> A4[Grounds Quote on Peer P25 Benchmark\nSettles via Azure MACC / AWS EDP]
    end
```

### 3.3 `T-95d` Tactical Opt-Out, `SCIM` Tier Downgrade & Cloud Marketplace `Private Offer` Sequence
```mermaid
sequenceDiagram
    autonumber
    participant Agent as SaaS Renewal & SAM Escrow Agent
    participant IdP as Okta / Entra ID & App Activity API
    participant Bench as Vendr / Tropic Benchmark & Vendor AE
    participant CloudMkt as Azure Marketplace (MACC) / AWS (EDP)

    Agent->>Agent: 1. [T-95d] Detect $240k SaaS contract (400 Creator seats) approaching 60-day opt-out deadline
    Agent->>Bench: 2. Dispatch certified Tactical Non-Renewal Notice (HTTP 403 disarms 12% auto-uplift lock)
    Agent->>IdP: 3. Pull 90-day login & write-event telemetry: find 65 idle users + 95 read-only viewers
    IdP-->>Agent: 4. Execute SCIM de-provisioning on 65 seats & downgrade 95 users to $12 Viewer (HTTP 422 -32% seats)
    Agent->>Bench: 5. Query peer P25 benchmark for 240-seat tier (exposes 26% price padding) → counter-offer
    Bench->>CloudMkt: 6. Vendor agrees to P25 unit price + 3% uplift cap via Azure Marketplace Private Offer
    CloudMkt-->>Agent: 7. Execute renewal at $158k (-34% savings) & burn 100% against committed Azure MACC!
```

---

## ④ 📊 Enterprise SaaS Management (`SMP`), Shadow-IT Discovery & Negotiation Platform Selection Matrix

| Dimension | **Zylo / Productiv / Torii** (Enterprise SaaS Management & Telemetry Leaders) | **Vendr / Tropic** (Peer Contract Price Benchmark & Assisted Buying Leaders) | **Ramp Procurement / Brex / Airbase** (Card-Linked Intake & Price Intelligence) | **Coupa / Zip Intake-to-Procure** (Enterprise Procurement Orchestration) |
| :--- | :--- | :--- | :--- | :--- |
| **Best Fit** | Enterprises (`1,000–50,000+` employees) eliminating shelfware, automating SCIM downgrades & discovering Shadow IT | Tech & enterprise buyers (`$1M–$30M` SaaS spend) wanting verified `P25` price benchmarks & negotiation leverage | Mid-market & growth companies blocking rogue SaaS card auto-renewals at the payment rail | Enterprises orchestrating InfoSec, Legal DPA, Finance & ERP PO approvals in one intake portal |
| **`SSO + In-App Feature` Tier Downgrade** | **Best-in-Class** (Direct API connectors to 100+ SaaS apps measuring read-vs-write activity + automated `SCIM` workflows) | Tracks contract dates & high-level seat counts; pairs with Okta/SMP for deep feature telemetry | Detects duplicate card merchants & per-seat bill spikes on corporate cards | Integrates with Okta/Zylo during renewal intake steps |
| **Verified Peer Price Benchmarks (`P25`)** | Benchmarks spend across managed enterprise portfolio | **Core Moat** (Billions in anonymized order forms showing exact SKU unit pricing at `P25/P50/P75` percentiles) | Built-in `Ramp Price Intelligence` from thousands of corporate card/AP invoices | Process-focused; relies on external benchmark feeds |
| **Auto-Renewal Window & Negotiation** | Automated 90/120-day renewal calendar alerts & usage readiness packs | Dedicated negotiation playbooks + buyer specialists / AI agents that negotiate directly with vendors | Merchant-locked virtual cards with expiration dates that block unauthorized auto-renewals | Automated legal redlining (`<=3%` uplift, AI DPA clauses) |
| **Pricing (`official_list_price`)** | Annual subscription based on employee count / managed spend (`~$40k–$120k+/yr`) | Tiered annual fee (`~$35k–$90k/yr`) often backed by a **Guaranteed Savings Multiple** | Core card features free; advanced procurement `$15+/user/mo` | Enterprise module licensing |

---

## ⑤ 🧪 ROI Estimation & 7-Card Visual Benchmark Deck

> **Provenance**: Modeled on a 1,500-employee enterprise's quarterly SaaS renewal pool (`$210,000/quarter` in missed 60-day notice `12%` auto-uplifts, unharvested 60-day inactive seats, read-only users sitting on `$75` Creator licenses, duplicate Shadow-IT card subscriptions, and unburned cloud `MACC/EDP` commitments), labeled `synthetic` (`independently_reproduced=false`).

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 1 / 7 · HANDS-ON · B2B SAAS RENEWAL & SSO SEAT RIGHT-SIZING ESCROW          ║
║ Headline: T-95d Opt-Out Shield & SCIM Seat Reclaim Cut SaaS Spend by 34.0%       ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ [Scenario & Thresholds]        [Structured Input]       [Top Decisions & KPIs]   ║
║ • Pool: $210,000 / Quarter     • Notice Shield: T-95d   • Renew Pass: HTTP 200   ║
║ • Renewal Uplift Cap: <=3.0%   • Zombie Cutoff: >60d 0  • MissedWin: HTTP 403    ║
║ • Tier Downgrade: 90d 0-Write  • Benchmark: Peer P25    • Shelfware: HTTP 422    ║
║ • Cloud Burn: Azure MACC / EDP • DPA: Zero-Retention AI • Saved Spend: -$71,400  ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ Provenance: synthetic (independently_reproduced=false) · Suite: WebIQ-R180       ║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 2 / 7 · SCENARIO: T-58 AUTO-RENEW TRAP DEFEATED & CREATOR-TO-VIEWER DOWNGR. ║
║ Headline: T-95d Notice Blocks 12% Hike; SCIM Downgrades 95 Read-Only Creators    ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ Input Quote: "Vendor quoted $240k renewal (+12% uplift on 400 Creator seats)     ║
║ while Okta telemetry showed 65 inactive users and 95 read-only viewers."         ║
║ 1. [choice] T-95d Opt-Out & <=3% Cap   ──► 1.00 conf ──► [Act automatically]     ║
║    ████████████████████████████████████████ 100% (HTTP 403 12% Uplift Blocked)   ║
║ 2. [choice] SCIM Zombie & Viewer Gate  ──► 0.99 conf ──► [Act automatically]     ║
║    ███████████████████████████████████████▊ 99% (HTTP 422 160 Seats Right-Sized) ║
║ 3. [score]  P25 Benchmark + MACC Offer ──► 0.98 conf ──► [Confirm: HTTP 409]     ║
║    ███████████████████████████████████████░ 98% (Renewed at $158k via Azure MACC)║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 3 / 7 · WHAT I TESTED · FULL 5-LANE EVALUATION MATRIX                      ║
║ Headline: 5/5 Deterministic Guardrails Verified Across Contract & SCIM Lanes     ║
╠══════════════════════════╦══════════════════════════╦══════════════════╦═════════╣
║ SCENARIO                 ║ QUESTION / TASK          ║ MODEL ANSWER     ║ ACTION  ║
╠══════════════════════════╬══════════════════════════╬══════════════════╬═════════╣
║ Baseline Right-Sized EA  ║ Active seats <=P25 & 3%  ║ HTTP 200 ($0)    ║ Auto    ║
║ Missed 60d / 12% Uplift  ║ No T-95d notice or >3%   ║ HTTP 403 Blocked ║ Block   ║
║ 40% Zombie / Viewer Waste║ Unharvested >60d idle    ║ HTTP 422 Blocked ║ Block   ║
║ 6x Shadow Cards / No DPA ║ Duplicate card or AI leak║ HTTP 451 Hold    ║ Human   ║
║ P25 Benchmark + MACC Burn║ SCIM trim + Private Offer║ HTTP 409 (-34%)  ║ Confirm ║
╠══════════════════════════╩══════════════════════════╩══════════════════╩═════════╣
║ Gate Summary: 100% deterministic policy match; 0 missed auto-renewal deadlines.  ║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 4 / 7 · UNDER THE HOOD · PROTOCOL & SCORING MECHANICS                       ║
║ Headline: Deterministic Policy Input Contract → Verifier Decision Trace          ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ // Input Contract (B2BSaasRenewalRightSizingPolicyInput)                         ║
║ { "quarterly_enterprise_saas_waste_uplift_and_shadow_it_pool_usd": 210000.0,     ║
║   "missed_auto_renewal_opt_out_window_or_uncapped_price_uplift": false,          ║
║   "unharvested_60d_zombie_seats_or_read_only_users_on_creator_tier": false,      ║
║   "duplicate_shadow_it_card_subscriptions_or_missing_no_train_dpa": false,       ║
║   "t95_opt_out_scim_rightsizing_p25_benchmark_and_macc_offer_ready": true }      ║
║                                      ↓                                           ║
║ // Verifier Output (<answer>)                                                    ║
║ { "status_code": 409,                                                            ║
║   "decision": "T95_OPT_OUT_SCIM_RIGHTSIZING_P25_AND_MACC_OFFER_CONFIRM",         ║
║   "mandate_token": "b2b_saas_renewal_escrow_optim_409", "savings_usd": 71400.0 } ║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 5 / 7 · ROBUSTNESS CHECK · PERTURBATION & CONSISTENCY                       ║
║ Headline: 0.0 pts Variance Across Option Reversal & Seat-Tier Perturbations      ║
╠══════════════════════════════╦═════════════════╦══════════════════╦══════════════╣
║ QUESTION / ANSWER            ║ ORIGINAL        ║ REVERSED / PERT  ║ CHANGE (PTS) ║
╠══════════════════════════════╬═════════════════╬══════════════════╬══════════════╣
║ T-95d Notice & <=3% Uplift   ║ HTTP 403 (100%) ║ HTTP 403 (100%)  ║ 0.0 pts      ║
║ SCIM Zombie & Tier Downgrade ║ HTTP 422 (100%) ║ HTTP 422 (100%)  ║ 0.0 pts      ║
║ Shadow-IT & AI-DPA Hold      ║ HTTP 451 (100%) ║ HTTP 451 (100%)  ║ 0.0 pts      ║
║ P25 + MACC Offer Net 34%     ║ $71,400 Saved   ║ $71,400 Saved    ║ 0.0 pts      ║
╚══════════════════════════════╩═════════════════╩══════════════════╩══════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 6 / 7 · LATENCY · BATCHING & SCALING LATENCY                                ║
║ Headline: 320ms Automated SCIM Usage Audit vs. 3-Week Manual Dept Spreadsheet    ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ Contract Clause OCR (1 PDF)  ║ ██ 190 ms (Agent) vs Missed 60d Calendar Trap     ║
║ SCIM + Audit Harvest (5k usr)║ ███ 320 ms (Agent) vs 3 wks (Dept Head CSV Poll)  ║
║ P25 Benchmark Match (50 SKUs)║ ████ 440 ms (Agent) vs Blind List-Price Renewal   ║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 7 / 7 · MY TAKE · GOOD FIT VS NOT FOR & READINESS                           ║
║ Headline: High-Impact FinOps & Procurement Playbook for Any Enterprise IT Stack  ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ ✅ GOOD FIT                               ⛔ NOT FOR                             ║
║ • Enterprises managing 50–500+ SaaS apps  • Single-founder $10/mo personal tools ║
║   across Okta/Entra & cloud marketplaces  • Heavy factory furnace maintenance    ║
║ • CFO/CIO teams burning MACC/EDP commits    unrelated to B2B SaaS procurement    ║
║ Readiness: Production-verified schema in `lab/webiq_commerce_demo.py` (R180).    ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

---

## ⑥ 🛠️ Production Risk & Architecture Review Checklist

- [ ] **Automated `T-95d` Tactical Non-Renewal Opt-Out Notice & `<=3%` Uplift Cap (`HTTP 403`)**: Does the contract lifecycle agent automatically send a certified non-renewal notice 35 days before the `60/90-day` opt-out deadline to preserve downsizing rights, and block order forms with `>3%` uncapped renewal uplifts?
- [ ] **`Okta / Entra ID SCIM` 60-Day Zombie Reclaim & 90-Day Read-Only Downgrade (`HTTP 422`)**: Before generating any renewal PO, does the agent automatically reclaim 60-day zero-login seats via `SCIM` and downgrade 90-day zero-write users from `$75 Creator` licenses to `Viewer` tiers?
- [ ] **Shadow-IT Corporate Card Consolidation & `Zero-Data-Retention AI DPA` Lock (`HTTP 451`)**: Are corporate card feeds and `OAuth` grants continuously scanned to merge duplicate departmental SaaS subscriptions into the enterprise tenant while enforcing `No-LLM-Training` DPAs?
- [ ] **Peer `P25` Price Benchmarking (`Vendr / Tropic`) & License Swap Rights (`HTTP 409`)**: Are renewal quotes benchmarked against top-quartile (`P25`) peer unit prices at the matching volume tier, with cross-product swap rights embedded in multi-SKU contracts?
- [ ] **`Azure Marketplace (MACC) / AWS Marketplace (EDP)` Private-Offer Drawdown (`HTTP 409`)**: Are eligible third-party SaaS renewals routed through cloud marketplace Private Offers so 100% of the SaaS spend burns down committed cloud infrastructure agreements?
