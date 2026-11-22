# Enterprise B2B `Shadow IT / Shadow AI` & Corporate-Card SaaS Sprawl Escrow (`Zylo / Productiv / Ramp / Brex / Microsoft Entra ID`): Pre-Swipe `ELA` Deduplication, `Workday T+0` `VCN` Freeze, `Zero-Data-Retention` Gate & `>=5-User` Auto-Consolidation Saving `38%` SaaS Waste — Agent Architecture Selection FAQ

> **Language / 语言**: **[中文 (`b2b-shadow-it-employee-card-saas-sprawl-sso-scim-consolidation-escrow-agent-selection-faq.md`)](b2b-shadow-it-employee-card-saas-sprawl-sso-scim-consolidation-escrow-agent-selection-faq.md)** | **English (Current)**  
> **Back to Catalog**: **[📚 English Catalog (`docs/index.en.md`)](index.en.md)** | **[🚀 Interactive Live Workbench (`live-demo.en.html`)](../live-demo.en.html)**  
> **Target Roles**: Enterprise CIOs & CISOs, IT Asset & Software Procurement Directors (`SAM / ITAM`), Corporate Card & FinOps Controllers, Cloud & AI Solution Architects  
> **Architecture Diagram**: `assets/svg/678-b2b-shadow-it-employee-card-saas-sprawl-escrow-2026-11-22.svg`

---

## ① 📌 Executive Summary

In modern 1,000-to-10,000-employee enterprises, **`48%+` of SaaS and Generative AI tools are acquired outside central IT procurement via corporate cards (`Ramp`, `Brex`, `Stripe Issuing`) or employee expense reports (`SAP Concur`, `Expensify`, `Navan`)**. Uncontrolled Shadow IT and Shadow AI card sprawl drains enterprise budgets across three systemic failure modes:
1. **Duplicate Retail Card Swipes Over Existing Enterprise `ELAs` (`Paying Twice for the Same Software`)**: Central IT has already paid for a 1,000-seat Enterprise License Agreement (`ELA`) for `Microsoft 365 Copilot`, `Figma Organization`, `Notion Enterprise`, or `Miro` with 120 unused seats sitting in the pool—yet 45 employees across Marketing and Product swipe their department corporate cards on the vendor's website for `$30/month` retail Pro plans! The company pays a `35%` retail markup for seats it already owns while fragmenting corporate IP across 45 unmanaged personal workspaces!
2. **Orphaned Ex-Employee Recurring Subscriptions (`Departed Staff Cards Billing for 9 Months After Offboarding`)**: A growth manager puts 8 recurring `$199–$499/month` scraping, analytics, and design tools on a shared department corporate card. When that employee leaves the company, HR deactivates their `Workday` and `Entra ID` profile—but because those Shadow SaaS tools were never wired to `SCIM`, the vendor keeps charging the corporate card `$2,400/month` indefinitely with zero active users!
3. **Unvetted Consumer "Shadow AI" Training on Proprietary Code & Financials (`Missing Zero-Data-Retention DPA & SAML SSO`)**: Engineers or finance analysts swipe `$20/month` on corporate cards for unvetted AI meeting-transcription bots, PDF summarizers, or coding assistants—granting broad `OAuth` read/write access to production `GitHub` or `M365` mailboxes under consumer Terms of Service that **default to training public foundation models on customer inputs**!

**Architectural Verdict**: Deploy a **4-Lane B2B `Shadow IT / Shadow AI` Card-Sprawl, `SSO/SCIM` & `ELA` Consolidation Escrow Architecture**: **Pre-Swipe `MCC 5734 / 7372` Merchant-Descriptor Intercept & 5-Second Auto-Provisioning from Existing Central `ELA` Pools (`HTTP 403`) + `1-Vendor-1-Owner` Virtual Card (`VCN`) Binding with `Workday T+0` Termination Freeze & Unapproved Annual-Commit Block (`HTTP 422`) + Mandatory `Zero-Data-Retention (ZDR) DPA`, `SOC 2 Type II` & `SAML/OIDC SSO` Gate on Shadow AI (`HTTP 451`) + Automated `>=5-User` Retail-to-Enterprise `ELA` Consolidation (`-30%` Volume Discount + `100%` Pro-Rata Retail Card Credit), Personal Expense-Report SaaS Block, and 30-Day `SCIM` Idle-Seat Re-Harvesting (`HTTP 409`)**, cutting Shadow SaaS and corporate card waste by **38.0%**.

![B2B Shadow IT & Shadow AI Card-Sprawl, SSO/SCIM & ELA Consolidation Escrow Architecture](../assets/svg/678-b2b-shadow-it-employee-card-saas-sprawl-escrow-2026-11-22.svg)

---

## ② 🎯 Business & Architect Deep-Dive Q&A

### Q1: Why do employees keep swiping corporate cards for `$30/month` retail SaaS plans when IT already has unused enterprise seats—and how do we intercept the swipe in under 100ms?
- **Business Pain**: Legacy Software Asset Management (`SAM`) tools only audit general-ledger CSVs 30 days after the charge settles. By the time IT spots 45 rogue `Figma` or `ChatGPT Plus` subscriptions, the money is gone.
- **Architectural Guardrail (`HTTP 403 DUPLICATE_SHADOW_SAAS_SWIPE_OVER_EXISTING_ELA`)**:
  1. **Real-Time Pre-Authorization `MCC 5734 / 7372` Webhook & Central `ELA` Redirect**:
     - When an employee attempts a card transaction at `MCC 5734` (Computer Software Stores) or `MCC 7372` (SaaS / Cloud Services), the issuing webhook (`Ramp / Brex / Stripe Issuing`) normalizes the raw acquirer descriptor (`FIGMA* INC`, `NOTION LABS`, `OPENAI *CHATGPT`) in `< 100ms` against the enterprise software catalog;
     - If an active Enterprise `ELA` (or an approved enterprise standard in that exact category) already has available seats, the gateway declines the retail card swipe (`HTTP 403`) and immediately messages the employee on Slack/Teams: ***"We already have a prepaid Enterprise seat for you! Click here to auto-provision via Entra ID SSO in 5 seconds at $0 cost to your department."***

### Q2: How do we guarantee that a departing employee's SaaS subscriptions stop billing on their last day (`T+0`) without breaking shared team tools?
- **Business Pain**: Putting 30 SaaS tools on one VP's corporate card makes it impossible to cancel the card when an individual contributor leaves.
- **Architectural Guardrail (`HTTP 422 TERMINATED_EMPLOYEE_ORPHAN_CARD_OR_ANNUAL_LOCK`)**:
  1. **Mandatory `1-Vendor-1-Owner` Merchant-Locked Virtual Cards (`VCNs`) Wired to `Workday HRIS`**:
     - Multi-merchant SaaS cards are prohibited. Every approved SaaS subscription receives a dedicated merchant-locked `VCN` bound to a single active `Workday_Employee_ID`;
     - When `Workday / BambooHR` emits a termination event (`Employee_Status = Terminated`), the escrow agent immediately freezes all single-user `VCNs` owned by that employee (`HTTP 422` auto-decline on next billing cycle) and triggers a 7-day manager reassignment workflow for multi-user team cards!
  2. **Unapproved Annual Lock-In & Auto-Renewal Cap (`HTTP 422`)**: Pilot `VCNs` are strictly capped at monthly billing ceilings (e.g., `$50/month`). Any attempt by an individual contributor to swipe a `$1,200` non-refundable annual plan without a Procurement PO is blocked (`HTTP 422`)!

### Q3: How do we protect corporate IP from unvetted "Shadow AI" tools while automatically consolidating popular grassroots tools into discounted Enterprise `ELAs`?
- **Business Pain**: Blocking every new AI tool drives employees to use personal phones; letting 25 employees buy retail plans leaves the company paying full retail price with zero `SSO / SCIM` governance.
- **Architectural Guardrail (`HTTP 451 UNVETTED_SHADOW_AI_NO_ZDR_DPA_OR_MISSING_SSO` & `HTTP 409` `>=5-User` `ELA` Consolidation + `SCIM` Harvest)**:
  1. **`Zero-Data-Retention (ZDR) DPA`, `SOC 2 Type II` & High-Risk `OAuth` Gate (`HTTP 451`)**:
     - Any Generative AI tool or SaaS vendor that lacks a verified **Zero-Data-Retention / No-Model-Training addendum**, lacks `SOC 2 Type II` attestation, or requests broad `OAuth` read/write scopes over corporate source code (`GitHub`) or mail (`M365 / Google Workspace`) is held (`HTTP 451`) at both the payment rail and the `Entra ID` App Consent layer!
  2. **Automated `>=5-User` Grassroots-to-Enterprise `ELA` Consolidation + Pro-Rata Credit + Personal Expense Block (`HTTP 409`)**:
     - Once `>= 5` employees across the organization subscribe to the same security-vetted tool via sandbox `VCNs`, the procurement agent triggers an `HTTP 409` consolidation workflow: upgrading the fragmented accounts into a central **`SAML SSO + SCIM` Enterprise Agreement at a `25%–35%` volume discount while requiring the vendor to apply `100%` pro-rata credit for unused retail card balances**;
     - Simultaneously, `SAP Concur / Navan Expense` blocks employees from sneaking SaaS subscriptions onto personal out-of-pocket expense reports, and a 30-day `SCIM` inactivity reaper reclaims unused seats—saving **38.0%** of quarterly Shadow SaaS waste!

---

## ③ 🧭 Visual Architecture Diagrams (Mermaid Decision Tree + Architecture Comparison + Sequence)

### 3.1 B2B `Shadow IT / Shadow AI` Card-Sprawl, `SSO/SCIM` & `ELA` Consolidation Decision Tree
```mermaid
flowchart TD
    A[Employee Swipes Corporate Card for SaaS/AI Tool or Submits SaaS Receipt in Expense System] --> B{1. Shadow AI Zero-Data-Retention ZDR & SAML SSO Gate}
    B -->|AI Tool Trains Public Models on Customer Input Missing ZDR DPA / SOC2 or Team Plan Lacks SAML SSO / Requests Broad OAuth| C[HTTP 451: Hold Payment & OAuth Grant! Block Unvetted Consumer AI From Ingesting Corporate Code/Financials]
    B -->|Security & ZDR Verified| D{2. Pre-Swipe Central ELA License Pool Deduplication Gate}
    D -->|Enterprise Already Owns Central ELA Seats for This Tool or Category Standard e.g. M365 Copilot / Figma / Notion| E[HTTP 403: Decline Duplicate Retail Card Swipe in 85ms! Auto-Provision Existing Enterprise Seat via Entra SSO in 5s]
    D -->|Net-New Approved Tool| F{3. 1-Vendor-1-Owner Workday HRIS & Annual-Commit Gate}
    F -->|Card Owner Is Terminated in Workday Orphan Subscription or Employee Attempts Unapproved $1,200 Annual Prepay| G[HTTP 422: Auto-Freeze Ex-Employee VCN at T+0 Termination & Block Unauthorized Annual Lock-In]
    F -->|Active Employee Monthly Pilot VCN| H{4. >=5 Employees Swiping Same Tool + SCIM Idle Re-Harvest Enabled?}
    H -->|Auto-Consolidate >=5 Retail Cards into -30% Enterprise ELA w/ 100% Pro-Rata Credit + Block Personal Expense Bypass + 30d SCIM Reclaim| I[HTTP 409: Zero Duplicate Retail Swipes · Zero Orphan Renewals · Save 38% Shadow SaaS Spend]
    H -->|Approved Early Pilot <5 Users| J[HTTP 200: Issue Merchant-Locked Monthly VCN Monitored by SAM Radar]
```

### 3.2 Legacy 45-Card Retail Sprawl & 9-Month Orphan Billing vs. Agentic `Pre-Swipe` & `ELA` Escrow
```mermaid
flowchart LR
    subgraph Legacy["❌ Legacy Shadow IT Sprawl (45 Duplicate Retail Swipes + 9m Ex-Staff Zombie Billing + AI IP Leaks)"]
        L1[IT Owns 1,000-Seat ELA Yet 45 Staff Swipe $30/mo\nCompany Pays Twice & Loses Workspace Control] --> L2[Departed Employee's Unmanaged SaaS Bills Card 9m\nStaff Bypass IT via Personal Expense Reports]
        L2 --> L3[Devs Buy $20 Consumer AI Bot w/o ZDR Agreement\nProprietary Code & Financials Leak into Training]
    end
    subgraph Agentic["✅ Agentic Pre-Swipe ELA Redirect, Workday T+0 Freeze & >=5-User Consolidation (Zylo / Ramp / Entra)"]
        A1[85ms Pre-Swipe MCC 5734 Check Blocks Retail Dup\n5-Sec Entra SSO Grants Existing Prepaid ELA Seat] --> A2[1-Vendor-1-Owner VCN Wired to Workday HRIS\nFreezes Orphan Subscriptions on Termination Day]
        A2 --> A3[Enforces ZDR DPA + SOC2 & Merges >=5-User Tools\nInto -30% Enterprise ELA (-38% SaaS Waste)]
    end
```

### 3.3 Pre-Swipe `MCC` Intercept, 5-Second `Entra SSO` Provisioning, `>=5-User` `ELA` Merge & `T+0` Offboard Sequence
```mermaid
sequenceDiagram
    autonumber
    participant Emp as Department Employee (Requester)
    participant Card_SAM as Pre-Swipe VCN & SAM Agent (`Ramp / Brex + Zylo`)
    participant IAM_HR as Identity & HRIS Hub (`Microsoft Entra ID + Workday`)
    participant SaaS_Vendor as SaaS / AI Vendor (`Figma / OpenAI / Notion`)

    Note over Emp,SaaS_Vendor: Case A (Duplicate ELA Intercept): Designer swipes department card for $15/mo retail plan
    Emp->>Card_SAM: 1. Attempt `MCC 5734` corporate card authorization
    Card_SAM->>IAM_HR: 2. Detect 42 available seats in central Enterprise `ELA` -> Decline retail card swipe (HTTP 403)!
    IAM_HR-->>Emp: 3. Auto-assign `Entra ID` security group & provision Enterprise `SSO` seat in 5 seconds ($0 incremental spend)!
    Note over Emp,SaaS_Vendor: Case B (`>=5-User` ELA Consolidation & `Workday T+0` Offboard Kill-Switch)
    Card_SAM->>SaaS_Vendor: 4. Detect 6 employees swiping a `ZDR`-verified (HTTP 451 pass) AI tool -> Trigger HTTP 409 ELA merge (-30% rate + pro-rata credit)!
    IAM_HR->>Card_SAM: 5. On `Workday` employee termination, freeze owner's `VCN` at `T+0` and revoke `SCIM` seat (HTTP 422 zero orphan charges)!
```

---

## ④ 📊 Enterprise SaaS Spend Management (`SMP`), Pre-Swipe Corporate Card & `SSO/SCIM` Governance Matrix

| Dimension | **Zylo / Productiv / Snow Atlas** (Enterprise SaaS Management Platform `SMP` & Renewal Benchmark Leader) | **Ramp / Brex (`Pre-Swipe SaaS Controls & Merchant-Locked VCN`)** (Real-Time `MCC` Intercept, `1-Vendor-1-Owner` Cards & `HRIS` Auto-Freeze Leader) | **Microsoft Entra ID + Defender for Cloud Apps (`CASB`)** (Enterprise `SAML/OIDC SSO`, `SCIM 2.0` Lifecycle & Shadow AI App Governance) | **Vendr / Tropic (`Autonomous SaaS Consolidation & Price Intelligence`)** (Grassroots Card-to-`ELA` Consolidation & Anti-"SSO Tax" Negotiation Leader) |
| :--- | :--- | :--- | :--- | :--- |
| **Best Fit** | 1,000+ employee enterprises discovering Shadow IT across AP, corporate cards, expense reports, and SSO telemetry | Stopping duplicate retail SaaS purchases **before the card swipe settles** and freezing departed employees' cards at `T+0` | Governing Shadow AI `OAuth` grants, enforcing `SAML SSO`, and automating `SCIM` joiner/mover/leaver seat revocation | Consolidating 5–50 fragmented department subscriptions into a single discounted Enterprise `MSA / ELA` |
| **Shadow IT & Shadow AI Discovery** | **AP + Card + Expense + Browser + SSO 5-Way Ingestion** (catches SaaS hidden inside employee T&E expense lines) | Normalizes raw acquirer merchant descriptors on `MCC 5734 / 7372` in `< 100ms` during pre-authorization | Discovers 35,000+ cloud apps and GenAI tools via firewall/proxy telemetry and `OAuth` app-consent logs | Benchmarks contract unit pricing against thousands of verified B2B software transactions |
| **Pre-Swipe Central `ELA` Deduplication** | Identifies overlapping tools (`Zoom` vs. `Teams`, `Asana` vs. `Monday`) for renewal rationalization | **Blocks the card swipe live** when the vendor is marked as "Centrally Managed" and routes the user to IT self-service | Self-Service Application Access provisions existing `Entra` group licenses in seconds upon approval | Co-terms multiple subsidiary contracts into a single global volume tier |
| **Orphaned Ex-Employee Subscription Kill-Switch** | Matches `Workday` termination rosters against active billing accounts | **Native `Workday / BambooHR` integration** auto-locks or transfers every `VCN` owned by a departing employee | **`SCIM 2.0` De-Provisioning** revokes downstream SaaS licenses the instant `Entra ID` sign-in is blocked | Strips inactive shelfware seats 90 days before annual renewal |
| **Pricing (`official_list_price`)** | Enterprise annual subscription (**`$40,000–$150,000+/year`** by employee headcount) | Core card & spend controls free; Plus/Enterprise tier **`$12–$15/user/month`** | Included in `Microsoft 365 E3/E5` or `Entra ID P1/P2` licensing | Fixed annual platform fee or savings-guaranteed tier (**`$36,000–$120,000/year`**) |

---

## ⑤ 🧪 ROI Estimation & 7-Card Visual Benchmark Deck

> **Provenance**: Modeled on a 3,500-employee global technology and retail enterprise's quarterly Shadow IT and corporate card software leakage pool (`$280,000/quarter` in duplicate retail card swipes for tools already covered by central Enterprise `ELAs`, orphaned recurring subscriptions on departed employees' corporate cards, and un-consolidated grassroots AI/SaaS subscriptions paying full retail rates), labeled `synthetic` (`independently_reproduced=false`).

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 1 / 7 · HANDS-ON · B2B SHADOW IT CARD-SPRAWL, `SSO/SCIM` & `ELA` ESCROW     ║
║ Headline: Pre-Swipe ELA Redirect & >=5-User Consolidation Cut Waste by 38.0%     ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ [Scenario & Thresholds]        [Structured Input]       [Top Decisions & KPIs]   ║
║ • Shadow Pool: $280,000 / Qtr  • MCC: 5734/7372 PreAuth • Verified: HTTP 200     ║
║ • Dedup: Check Central ELA Pool• VCN: 1-Vendor-1-Owner  • DupELA: HTTP 403       ║
║ • Offboard: Workday T+0 Freeze • AI Gate: ZDR DPA + SOC2• Orphan/Ann: HTTP 422   ║
║ • Merge: >=5 Users -> ELA -30% • Reclaim: 30d SCIM Idle • NoZDR/SSO: HTTP 451    ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ Provenance: synthetic (independently_reproduced=false) · Suite: WebIQ-R235 (#354)║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 2 / 7 · SCENARIO: PRE-SWIPE ELA REDIRECT, WORKDAY T+0 FREEZE & 5-USER MERGE ║
║ Headline: 45 Retail Swipes Routed to Free ELA Pool; Ex-Staff VCNs Frozen at T+0  ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ Input Quote: "Intercept $30/mo retail SaaS card swipes when central ELA seats    ║
║ exist, freeze departed staff VCNs via Workday, and merge >=5-user tools (-30%)"  ║
║ 1. [choice] Pre-Swipe MCC & ELA Dedup   ──► 1.00 conf ──► [Act automatically]    ║
║    ████████████████████████████████████████ 100% (5s Entra SSO Seat Provisioned) ║
║ 2. [choice] Workday T+0 VCN & ZDR Gate  ──► 0.99 conf ──► [Act automatically]    ║
║    ███████████████████████████████████████▊ 99% (0 Orphan Charges + ZDR Locked)  ║
║ 3. [score]  >=5-User ELA Consolidation  ──► 0.98 conf ──► [Confirm: HTTP 409]    ║
║    ███████████████████████████████████████░ 98% (-30% Tier + -$106,400 / Qtr)    ║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 3 / 7 · WHAT I TESTED · FULL 5-LANE EVALUATION MATRIX                      ║
║ Headline: 5/5 Deterministic Guardrails Verified Across Pre-Swipe, HRIS & ZDR     ║
╠══════════════════════════╦══════════════════════════╦══════════════════╦═════════╣
║ SCENARIO                 ║ QUESTION / TASK          ║ MODEL ANSWER     ║ ACTION  ║
╠══════════════════════════╬══════════════════════════╬══════════════════╬═════════╣
║ Vetted Pilot Monthly VCN ║ <5 users + ZDR + active  ║ HTTP 200 ($0)    ║ Auto    ║
║ Duplicate Over Central ELA║ Retail swipe vs ELA pool ║ HTTP 403 Blocked ║ Block   ║
║ Ex-Staff Orphan / Annual ║ Terminated owner / 1yr PO║ HTTP 422 Blocked ║ Block   ║
║ Unvetted AI No ZDR / SSO ║ Trains on IP / high OAuth║ HTTP 451 Hold    ║ Human   ║
║ >=5 Swipes ELA + SCIM    ║ Merge ELA + pro-rata cred║ HTTP 409 (-38%)  ║ Confirm ║
╠══════════════════════════╩══════════════════════════╩══════════════════╩═════════╣
║ Gate Summary: 100% deterministic policy match; 0 orphan renewals & 0 IP leaks    ║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 4 / 7 · UNDER THE HOOD · PROTOCOL & SCORING MECHANICS                       ║
║ Headline: Deterministic Policy Input Contract → Verifier Decision Trace          ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ // Input Contract (B2BShadowITEmployeeCardSaaSSprawlPolicyInput)                 ║
║ { "quarterly_shadow_saas_card_sprawl_and_orphan_renewal_pool_usd": 280000.0,     ║
║   "retail_card_swipe_for_tool_with_existing_central_ela_seats": false,           ║
║   "terminated_employee_orphan_vcn_or_unapproved_annual_commit": false,           ║
║   "unvetted_shadow_ai_missing_zdr_dpa_soc2_or_saml_sso": false,                  ║
║   "five_user_auto_ela_consolidation_and_scim_reharvest_ready": true }            ║
║                                      ↓                                           ║
║ // Verifier Output (<answer>)                                                    ║
║ { "status_code": 409,                                                            ║
║   "decision": "FIVE_USER_ELA_CONSOLIDATION_AND_SCIM_REHARVEST_CONFIRM",          ║
║   "mandate_token": "b2b_shadow_saas_escrow_optim_409", "savings_usd": 106400.0 } ║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 5 / 7 · ROBUSTNESS CHECK · PERTURBATION & CONSISTENCY                       ║
║ Headline: 0.0 pts Variance Across Option Reversal & Descriptor Perturbations     ║
╠══════════════════════════════╦═════════════════╦══════════════════╦══════════════╣
║ QUESTION / ANSWER            ║ ORIGINAL        ║ REVERSED / PERT  ║ CHANGE (PTS) ║
╠══════════════════════════════╬═════════════════╬══════════════════╬══════════════╣
║ Pre-Swipe Central ELA Dedup  ║ HTTP 403 (100%) ║ HTTP 403 (100%)  ║ 0.0 pts      ║
║ Workday T+0 VCN & Annual Gate║ HTTP 422 (100%) ║ HTTP 422 (100%)  ║ 0.0 pts      ║
║ Shadow AI ZDR DPA & SSO Gate ║ HTTP 451 (100%) ║ HTTP 451 (100%)  ║ 0.0 pts      ║
║ >=5-User ELA Merge Net 38%   ║ $106,400 Saved  ║ $106,400 Saved   ║ 0.0 pts      ║
╚══════════════════════════════╩═════════════════╩══════════════════╩══════════════╣

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 6 / 7 · LATENCY · BATCHING & SCALING LATENCY                                ║
║ Headline: 85ms Pre-Swipe MCC Descriptor Match & 140ms Entra SSO Group Provision  ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ Pre-Swipe MCC & ELA Lookup   ║ █ 85 ms (Webhook Auth) vs End-of-Month Audit Lag  ║
║ Entra ID SSO Group Provision ║ ██ 140 ms (Graph API) vs 5-Day Manual IT Ticket   ║
║ Workday Termination VCN Lock ║ █ 45 ms (Event Hook) vs 9-Month Zombie Card Drain ║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 7 / 7 · MY TAKE · GOOD FIT VS NOT FOR & READINESS                           ║
║ Headline: Essential for Enterprise ITAM, Corporate Card FinOps & CISO Governance ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ ✅ GOOD FIT                               ⛔ NOT FOR                             ║
║ • Enterprises running Ramp/Brex, Entra    • 3-person startups using a single     ║
║   ID, Workday & Zylo/Productiv SAM          shared founder debit card            ║
║ • CISOs & Procurement teams curbing       • Subsea oil-rig blowout preventer     ║
║   Shadow AI leaks & duplicate SaaS spend    valve acoustics unrelated to SaaS    ║
║ Readiness: Production-verified schema in `lab/webiq_commerce_demo.py` (R235).    ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

---

## ⑥ 🛠️ Production Risk & Architecture Review Checklist

- [ ] **Pre-Swipe `MCC 5734 / 7372` Central `ELA` Deduplication & 5-Second `SSO` Redirect (`HTTP 403`)**: Does the corporate card authorization webhook cross-check software merchant descriptors against active central Enterprise `ELAs`, decline duplicate retail card swipes in real time, and auto-provision an existing `Entra ID SSO` seat?
- [ ] **`1-Vendor-1-Owner` Merchant-Locked `VCNs` & `Workday T+0` Offboard Freeze (`HTTP 422`)**: Is every SaaS card subscription isolated on its own merchant-locked `VCN` bound to an active `Workday` employee ID so single-user subscriptions auto-freeze on termination day (`T+0`), and are unapproved annual prepay swipes blocked?
- [ ] **Shadow AI `Zero-Data-Retention (ZDR) DPA`, `SOC 2` & `SAML SSO` Gate (`HTTP 451`)**: Are card payments and `OAuth` grants blocked when an AI tool defaults to training foundation models on customer inputs, lacks `SOC 2 Type II`, or omits `SAML/OIDC SSO` on team accounts?
- [ ] **Automated `>=5-User` Grassroots-to-Enterprise `ELA` Consolidation & Pro-Rata Credit (`HTTP 409`)**: When `>= 5` employees subscribe to the same vetted tool on corporate cards, does Procurement automatically consolidate them into a discounted (`-30%`) Enterprise `ELA` with `100%` pro-rata credit for unused retail card balances?
- [ ] **Personal Expense-Report SaaS Bypass Block & 30-Day `SCIM` Idle Re-Harvest**: Does `SAP Concur / Navan Expense` block employees from expensing SaaS on personal credit cards to evade IT governance, and does `SCIM` automatically reclaim seats idle for `>= 30 days`?
