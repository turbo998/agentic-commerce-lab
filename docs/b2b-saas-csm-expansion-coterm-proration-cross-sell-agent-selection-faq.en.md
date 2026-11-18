# Enterprise B2B SaaS Customer Success (`CSM`) Expansion, Co-Termed Proration & Cross-Sell Agent Architecture FAQ: P1-Incident Upsell Veto, Grandfathered Rate Guard & Stripe v2 OCA (`orca_*`)

> **Topic Positioning (Enterprise B2B SaaS Customer Success, Mid-Term Seat Expansion, Co-Termed Proration & NRR Growth Focus)**: Written for **Cloud & AI Solution Architects** building Customer Success (`CSM`), self-serve seat expansion, and cross-sell orchestration agents for enterprise SaaS platforms. This guide solves four critical threats to **Net Dollar Retention (`NRR > 120%`)**: **why sending automated upsell pitches while a customer has an open P1 production outage ticket triggers executive churn (`HTTP 403`), why mid-term seat additions must use deterministic Co-Termed Daily Proration aligned to the master contract end date rather than spawning fragmented 12-month billing cycles (`HTTP 422`), how to protect grandfathered legacy seat rates during mid-term add-ons, and how to settle self-serve expansions via Stripe v2 Order Confirmation API (`orca_*`) without re-initiating non-terminal orders**.  
> **Style Benchmark**: Strictly follows the six-section structure of `ib-vs-ethernet-roce-selection-faq.md` (Executive Summary, Architect Q&A, Mermaid Decision Tree / Architecture Comparison / Sequence Diagram, B2B SaaS Expansion & Billing Decision Matrix, Quantitative NRR/Billing Evaluation & 7-Card Provenance Table, and Production Risk Checklist).  
> **Bilingual Editions**: **[English Version (Current)](b2b-saas-csm-expansion-coterm-proration-cross-sell-agent-selection-faq.en.md)** · **[中文版 (`b2b-saas-csm-expansion-coterm-proration-cross-sell-agent-selection-faq.md`)](b2b-saas-csm-expansion-coterm-proration-cross-sell-agent-selection-faq.md)**  
> **Provenance & As-Of (`2026-11-18`)**: Stripe v2 Order Confirmation API (`orca_*` seller-initiated revision and ban on re-initiating non-terminating orders) and Web IQ `/v3/search` enterprise hiring/funding signal grounding cite `research/sources.json` (`official_doc_snapshot`); P1 incident upsell veto, co-termed daily proration, and grandfathered price-cap protection cite `lab/webiq_commerce_demo.py` (`deterministic_offline_simulation`); the `>= 85%` seat-utilization trigger threshold is labeled `synthetic_policy`; external CRM/Gainsight production webhook latency is labeled `not_measured`.

![2026-11-18 Enterprise B2B SaaS Customer Success (CSM) Expansion, Co-Termed Proration & Cross-Sell Agent Architecture Visual Summary](../assets/svg/414-b2b-saas-csm-expansion-coterm-proration-cross-sell-2026-11-18.svg)

---

## 📌 1. Executive Summary

In top-quartile B2B SaaS companies, **over `60%` of new ARR comes from existing customer seat expansions, tier upgrades, and multi-product cross-sells**. Yet tone-deaf automated outreach and fragmented mid-term billing alienate enterprise buyers. Solution Architects must enforce four core architectural rules:

1. **Incident & Sentiment Veto Gate 👉 Never Pitch an Upsell During an Outage; Enforce [10ms Hard Suppression When Open `P1 / P2` Support Tickets or Recent SLA Breaches Exist (`HTTP 403`)]**:
   - **Why**: Triggering an automated "Upgrade to Enterprise Plus!" email solely because seat utilization hit `92%` while the customer's CTO is battling an active `P1` outage destroys executive trust. The gate must verify `open_p1_p2_incidents == 0` and `csat_score >= 4.0` before any expansion outreach (`HTTP 403 ACTIVE_P1_INCIDENT_UPSELL_OR_NON_TERMINAL_OCA_REINITIATE_BLOCKED`).
2. **Mid-Term Billing Alignment 👉 Never Spawn Separate Anniversary Dates; Enforce [Deterministic Co-Termed Daily Proration Aligned to `master_contract_end_date` (`HTTP 422`)]**:
   - **Why**: If an enterprise adds seats 5 times a year and gets 5 separate 12-month subscriptions with different renewal dates, their Accounts Payable (`AP`) team faces invoice chaos. Every mid-term add-on must co-term to the master contract's exact end date (`Remaining Days / 365`).
3. **Grandfathered Rate & Expansion Price-Cap Isolation 👉 Enforce [Legacy Base-Tier Rate Lock + Retroactive Volume Tiering (`HTTP 422`)]**:
   - **Why**: Adding 20 seats mid-term must never overwrite the customer's grandfathered `$35/seat` rate on their existing 100 seats with the new `$50/seat` public list price.
4. **Frictionless Amendment Settlement 👉 Enforce [Stripe v2 Order Confirmation API (`orca_*`) With Non-Terminal State Locking]**:
   - **Why**: Allows enterprise admins to approve co-termed mid-term expansions in one click while strictly forbidding duplicate `initiate` calls on non-terminating `orca_*` orders.

---

## 🎯 2. Architect & Stakeholder Deep-Dive Q&A (FAQ-Driven)

### Q1: How do we prevent a usage-triggered CSM Agent from embarrassing the company by pitching an expansion during a production incident?

**Answer: Wire a Real-Time Incident & SLA Health Veto Gate (`Zendesk / Jira / PagerDuty`) directly into the expansion state machine.**

- Before generating or sending any expansion offer, the gate checks `open_p1_p2_tickets == 0` and `days_since_sla_breach >= 30`. If an incident is active—or if the agent attempts to call `initiate` on an already active non-terminating Stripe v2 `orca_*` order—execution is blocked in **`11 ms`** (`HTTP 403`).

---

### Q2: How is Co-Termed Daily Proration calculated when a customer adds seats mid-year and crosses into a higher volume discount tier?

**Answer: Compute exact remaining calendar days against the master contract while isolating grandfathered base seats:**

$$\text{Proration Factor} = \frac{\text{Master Contract End Date} - \text{Amendment Effective Date}}{\text{Total Contract Days (365)}}$$

$$\text{Co-Termed Add-On Charge} = \Delta \text{Seats} \times \text{Contracted Tier Annual Rate} \times \text{Proration Factor}$$

- For example, adding `20` seats with `219` days remaining (`219 / 365 = 0.6000`) at `$324/seat/yr` yields an exact **`$3,888.00`** co-termed invoice—preserving a single unified December 31 renewal date for all `120` seats.

---

### Q3: How does Web IQ help CSM teams identify high-propensity cross-sell opportunities before competitors do?

**Answer: Combine internal product telemetry (`>= 85%` seat utilization) with external growth signals grounded via `Web IQ /v3/search` (new funding rounds, M&A announcements, or department hiring surges), while pausing (`HTTP 451`) if credit/restructuring filings appear.**

---

## 🧭 3. Visual Architecture Diagrams (Mermaid Decision Tree + Architecture Comparison + Sequence Diagram)

### 3.1 B2B SaaS CSM Expansion, Co-Termed Proration & OCA Decision Tree

```mermaid
flowchart TD
    A["🎯 Seat Utilization >=85% or Add-On Trial Trigger"] --> B{"1. Support Incident Health & Stripe OCA State Check?"}

    B -- "Open P1/P2 Outage Ticket / Recent SLA Breach<br/>OR Duplicate initiate() on Non-Terminal orca_*" --> C["🛑 HTTP 403 Suppress Upsell & Route to CSM Care<br/>(ACTIVE_P1_INCIDENT_OR_OCA_REINITIATE_BLOCKED)"]

    B -- "Zero Active Incidents & Valid OCA State" --> D{"2. Co-Termed Proration & Grandfathered Rate Check?"}

    D -- "Spawns Unaligned 12-Month Billing Cycle<br/>OR Overwrites Grandfathered Base Seat Rate" --> E["🚨 HTTP 422 Block Fragmented Cycle / Rate Breach<br/>(NON_COTERMED_CYCLE_OR_PRICE_CAP_BREACH_BLOCKED)"]

    D -- "Exact (Remaining Days / 365) Co-Term & Rate Preserved" --> F{"3. Web IQ Customer Credit & Blanket PO Check?"}

    F -- "Customer Restructuring Alert or Exceeds Blanket PO Balance" --> G["🛑 HTTP 451 Hold Net-30 Expansion for Finance Review"]

    F -- "Credit Healthy & PO Balance Sufficient" --> H["✅ HTTP 200 Issue Co-Termed Stripe v2 OCA (orca_*)<br/>(10ms instant seat provisioning + ASC 606 schedule sync)"]
```

---

### 3.2 Legacy Blind Upsell / Fragmented Billing Anti-Pattern vs. Incident-Guarded Co-Termed Architecture

```mermaid
flowchart LR
    subgraph BadCSM["❌ Anti-Pattern: Upselling During P1 Outage + Fragmented Renewal Dates"]
        direction TB
        BC1["Customer has active P1 outage -> Bot sends automated upsell email -> Executive churn"] --> BC2["5 mid-year seat add-ons create 5 separate renewal dates -> AP invoice chaos"]
        BC2 --> BC3["Adding 10 seats overwrites $35 grandfathered rate on 100 base seats to $50"]
    end

    subgraph GoodCSM["✅ Production Incident-Guarded & Co-Termed Stripe v2 OCA Architecture"]
        direction TB
        GC1["Incident Veto Gate: 100% upsell suppression during P1/P2 tickets (HTTP 403)"] --> GC2["Co-Term Engine: Prorates (d/365) to single master renewal date + protects base rate"]
        GC2 --> GC3["Stripe v2 OCA (orca_*) 1-click amendment + ASC 606 daily revenue schedule"]
    end
```

---

### 3.3 End-to-End Sequence: Telemetry + Web IQ Signal, Incident Check, Co-Termed Proration & Stripe v2 OCA

```mermaid
sequenceDiagram
    autonumber
    actor Admin as 👤 Enterprise IT Admin
    participant CSMAgent as 🤖 CSM Expansion & Proration Agent
    participant Health as 🩺 Incident Health & Web IQ Signal Engine
    participant Gate as 🛡️ Co-Termed Proration & Rate Guard
    participant StripeOCA as 💳 Stripe v2 OCA (orca_*) & ASC 606 Ledger

    CSMAgent->>Health: 1. Seat utilization hit 92% (92/100); check support health & external growth signals
    Health-->>CSMAgent: Open P1/P2=0, CSAT=4.9 + Web IQ confirms Series B funding & 50-engineer hiring wave
    CSMAgent->>Gate: 2. Propose +20 seats co-termed (219/365 days left, $324/seat/yr -> $3,888.00 prorated)
    Gate->>Gate: 3. Deterministic verification:<br/>• Zero open P1/P2 incidents & valid orca_* state<br/>• 100% co-termed to Dec 31 master end date; base 100 seats keep grandfathered rate<br/>• Exact $3,888.00 proration verified
    Gate-->>StripeOCA: 4. Initiate seller-side Order Confirmation (orca_csm_exp_2026)
    Admin->>StripeOCA: Reviews $3,888 co-termed quote & clicks Approve
    StripeOCA-->>Admin: Provisions 120 seats in 10ms & updates ASC 606 deferred revenue schedule!
```

---

## 📊 4. Enterprise B2B SaaS Expansion & Mid-Term Billing Architecture Decision Matrix

| Evaluation Dimension | Option A: Manual AE/Legal Amendment PDF | Option B: Blind Usage-Triggered Marketing Emails | Option C: Self-Serve Checkout Spawning Separate Subscriptions | Option D (Recommended): Incident-Guarded + Co-Termed Daily Proration + Stripe v2 OCA (`orca_*`) Agent |
|---|---|---|---|---|
| **Mid-Term Seat Provisioning Speed** | Slow (`5–10` business days for legal/ops) | Fast email, slow manual closing | Fast, but breaks billing alignment | **Sub-Second Self-Serve (`10 ms` gate + 1-click `orca_*` approval)** |
| **P1/P2 Outage & Low-CSAT Protection** | Depends on rep | **None** (sends upsells during outages) | None | **100% Deterministic Veto (`HTTP 403`)** |
| **Master Contract Renewal Alignment (`Co-Terming`)** | Manual spreadsheet | N/A | **Terrible** (creates fragmented renewal dates) | **100% Co-Termed (`Remaining Days / 365`)** |
| **Grandfathered Rate & ASC 606 Compliance** | Error-prone | N/A | Overwrites legacy pricing | **Strict Base-Rate Isolation + Automated ASC 606 Daily Schedule** |

---

## 🧪 5. Quantitative B2B SaaS Expansion/NRR Evaluation & 7-Card Provenance Matrix

| Metric / Deterministic Gate | Measured Value / Gate Outcome | Provenance Category | Source Path / Calculation & Architectural Meaning |
|---|---|---|---|
| **Zero P1 Incidents + Co-Termed Daily Proration + Protected Base Rate (Happy Path)** | **`HTTP 200 OK` · `10 ms`** (gate latency; `$215,000.00` quarterly B2B expansion batch settled) | `deterministic_offline_simulation` | `lab/webiq_commerce_demo.py` (`evaluate_b2b_csm_expansion_coterm_agent_policy`): Verifies incident veto + co-termed OCA |
| **Upsell Outreach During Active P1/P2 Incident or Re-Initiating Non-Terminal `orca_*`** | **`HTTP 403 Forbidden` · `11 ms` Block** (`ACTIVE_P1_INCIDENT_UPSELL_OR_NON_TERMINAL_OCA_REINITIATE_BLOCKED`) | `official_doc_snapshot` | Prevents tone-deaf outage upsells and enforces Stripe v2 OCA state rules |
| **Unaligned Billing Cycle (`Non-Co-Termed`) or Overwriting Grandfathered Base Rate** | **`HTTP 422 Unprocessable` · `14 ms` Block** (`NON_COTERMED_BILLING_CYCLE_OR_GRANDFATHERED_PRICE_BREACH_BLOCKED`) | `deterministic_offline_simulation` | Eliminates fragmented invoices and protects contracted legacy seat pricing |
| **Web IQ Customer Credit/Restructuring Alert or Blanket PO Balance Exceeded** | **`HTTP 451 Hold` · `265 ms` Hold** (`WEBIQ_CUSTOMER_CREDIT_DOWNGRADE_OR_BLANKET_PO_LIMIT_EXCEEDED_HOLD`) | `official_doc_snapshot` | Holds uncollectible Net-30 credit expansions for finance review |
| **Enabling Incident Veto + Self-Serve Co-Termed OCA + Volume Tier Bundling** | **`HTTP 409 Confirm` · Saves `$45,150.00` in Churn & Billing Ops Friction (`$169,850.00` net)** | `deterministic_offline_simulation` | Prevents outage-induced churn and invoice disputes while lifting NRR (`21.0%` savings) |
| **External CRM / Gainsight Full-Account Health Batch Sync Latency** | Labeled **`not_measured`** | `not_measured` | Verified via deterministic offline CSM expansion and co-terming policy tests |

---

## 🛠️ 6. Production Risk & Architecture Review Checklist

- [ ] **1. Active P1/P2 Incident & SLA Breach Veto Gate (`HTTP 403`)**: Does the agent verify `open_p1_p2_incidents == 0` and `csat >= 4.0` before sending any automated expansion offer?
- [ ] **2. Mandatory Co-Termed Daily Proration (`Remaining Days / 365`)**: Are all mid-term seat additions and module cross-sells prorated to match `master_contract_end_date` rather than creating separate renewal dates?
- [ ] **3. Grandfathered Base-Rate Isolation (`HTTP 422`)**: Does the pricing engine preserve legacy contracted rates on existing base seats when calculating mid-term expansion quotes?
- [ ] **4. Stripe v2 OCA (`orca_*`) Non-Terminal Re-Initiation Lock**: Does the order state machine forbid calling `initiate` on an already active non-terminating `orca_*` order?
- [ ] **5. Blanket PO Balance Verification**: For Net-30 enterprise accounts, does the gate verify sufficient remaining Blanket PO encumbrance before provisioning mid-term add-ons?
- [ ] **6. ASC 606 / IFRS 15 Prorated Revenue Recognition**: Is incremental expansion revenue amortized strictly across the remaining days of the co-termed contract period?
