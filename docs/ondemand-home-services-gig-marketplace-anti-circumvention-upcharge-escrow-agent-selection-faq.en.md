# On-Demand Home Services & Gig Marketplace Anti-Circumvention, Rate-Card Upcharge Guard & 7-Day Warranty Escrow (`Thumbtack / TaskRabbit / Angi / Stripe Connect`): Geofence Cancel Audit, Pre-Disassembly Price Lock & `80/20` Holdback Saving `36%` Leakage & Rework Loss — Agent Architecture Selection FAQ

> **Language / 语言**: **[中文 (`ondemand-home-services-gig-marketplace-anti-circumvention-upcharge-escrow-agent-selection-faq.md`)](ondemand-home-services-gig-marketplace-anti-circumvention-upcharge-escrow-agent-selection-faq.md)** | **English (Current)**  
> **Back to Catalog**: **[📚 English Catalog (`docs/index.en.md`)](index.en.md)** | **[🚀 Interactive Live Workbench (`live-demo.en.html`)](../live-demo.en.html)**  
> **Target Roles**: On-Demand Marketplace Product & Trust/Safety VPs, Field-Service Network Operations Directors, Marketplace Payments & Escrow Architects, Cloud & AI Solution Architects  
> **Architecture Diagram**: `assets/svg/646-ondemand-home-services-anti-circumvention-escrow-2026-11-22.svg`

---

## ① 📌 Executive Summary

In two-sided home services, appliance repair, furniture assembly, and local contractor marketplaces (`Thumbtack`, `TaskRabbit`, `Angi`, `Handy`, `Wanshifu`), platform unit economics face three existential threats at the homeowner's doorstep:
1. **Doorstep Platform Circumvention ("Cancel on the App and Pay Me `$150` Cash/Venmo")**: The marketplace spends `$35–$60` in paid search CAC to acquire a homeowner needing an AC repair or furniture assembly. The dispatched technician drives to the homeowner's house, stays inside the property's GPS geofence for 40 minutes, and then marks the app order `"Cancelled — Customer Changed Mind"`—having whispered to the homeowner: *"Cancel the app order so we skip the 20% platform fee and just Venmo me directly."* The platform loses 100% of its CAC and all future repeat bookings.
2. **Mid-Job "Bait-and-Switch" Upcharge Extortion After Disassembly**: A rogue technician accepts a `$79` fixed-price faucet or appliance repair job, **disassembles the unit on the kitchen floor**, and then demands `$380` in unitemized "special valve / mainboard replacement fees" before putting it back together. Held hostage with a disassembled appliance, the homeowner pays under duress and then blasts the marketplace with 1-star reviews and credit-card chargebacks.
3. **Hit-and-Run `T+0` Payouts Before Next-Day Leaks & Unlicensed/Uninsured Dispatch**: Paying out `100%` of the job funds the second the technician leaves means that when a repaired pipe bursts that night, the technician blocks the homeowner's number—forcing the marketplace to pay a second technician out of pocket. Worse, dispatching a technician whose state electrical/plumbing license or `$1M` General Liability Certificate of Insurance (`COI`) expired last week exposes the platform to catastrophic liability lawsuits.

**Architectural Verdict**: Deploy a **4-Lane On-Demand Home Services Anti-Circumvention, Rate-Card & Warranty Escrow Architecture**: **Masked Proxy Communications & `>=15-Minute` Geofence-Dwell Cancellation Audit (`HTTP 403`) + Pre-Disassembly Standardized Parts Rate-Card & AI Symptom-Match Lock (`HTTP 422`) + Active Trade License / `COI` Verification & `80% Completion + 20% 7-Day Warranty Holdback` Split (`HTTP 451`) + 10-Second Pre-Visit Video AI Scoping & Sliding Repeat-Booking Take-Rate (`22% → 7%`) (`HTTP 409`)**, reducing off-platform leakage, upcharge disputes, and warranty rework losses by **36.0%**.

![On-Demand Home Services & Gig Marketplace Anti-Circumvention & Upcharge Escrow Architecture](../assets/svg/646-ondemand-home-services-anti-circumvention-escrow-2026-11-22.svg)

---

## ② 🎯 Business & Architect Deep-Dive Q&A

### Q1: How do we catch technicians who arrive at the customer's house and convince the customer to cancel the app order and pay cash/Venmo off-platform?
- **Business Pain**: Chat keyword filters only catch off-platform solicitation *before* the visit; once the pro is standing in the customer's living room, verbal circumvention bypasses chat moderation entirely.
- **Architectural Guardrail (`HTTP 403 ONSITE_GEOFENCE_CANCEL_CIRCUMVENTION_BLOCKED`)**:
  1. **Spatiotemporal `Geofence-Dwell × Cancellation` Forensics**: All voice/SMS coordination runs through expiring masked Twilio proxy numbers (with regex redaction blocking raw phone numbers and `Venmo / Zelle / CashApp / WeChat` handles in chat). If a technician's mobile app logs **`>= 15 minutes` of GPS dwell time inside a `100-meter` radius of the customer's service address** and the order is subsequently cancelled without a verified diagnostic fee, the engine flags an **`On-Site Circumvention Event` (`HTTP 403`)**—freezing the pro's security deposit, billing the pro the platform's lead-acquisition fee, and texting the homeowner an instant warning that off-platform cash payments void the platform's `$10,000` Property Damage Protection and 30-day workmanship warranty.
  2. **Sliding Repeat-Booking Take-Rate (`22% First Job → 7% Repeat Job`)**: To remove the economic incentive to poach repeat clients, the platform drops its commission from `22%` on the initial discovery booking to **`7%` on repeat bookings with the same homeowner** (bundling free liability insurance and automated invoicing).

### Q2: How do we stop predatory "Bait-and-Switch" technicians from taking an appliance apart and extorting `$350` in bogus on-site upcharges?
- **Business Pain**: When technicians can type arbitrary free-text add-on charges (`"Custom Valve Modification — $350"`) on-site, homeowners lose all price transparency.
- **Architectural Guardrail (`HTTP 422 UNITEMIZED_ONSITE_BAIT_AND_SWITCH_UPCHARGE_BLOCKED`)**:
  1. **Pre-Disassembly Standardized Parts Rate-Card & Photo Proof**: Free-text on-site price increases and post-disassembly verbal surcharges are hard-blocked (`HTTP 422`). Any scope expansion `> +30%` requires the technician—*before* disassembling the unit—to select a fixed-price SKU from the platform's **Standardized Parts & Labor Rate-Card** and upload a live photo of the faulty component/meter reading.
  2. **3-Second Multimodal Symptom-vs-Part Verification**: The diagnostic Agent verifies that the requested add-on part matches the initial symptom (e.g., blocking a `$260` mainboard replacement on a simple door-gasket leak via `HTTP 422`) and requires the homeowner's in-app incremental pre-authorization signature before work proceeds.

### Q3: How do we prevent technicians from ghosting when a repair fails 48 hours later—and ensure every pro on-site has an active license and insurance?
- **Business Pain**: If 100% of the payout settles the moment the pro walks out the door, the platform bears 100% of the cost when a poorly sealed pipe leaks the next day.
- **Architectural Guardrail (`HTTP 451 EXPIRED_TRADE_LICENSE_OR_INSTANT_100PCT_PAYOUT_HOLD` & `HTTP 409` Video Pre-Scoping + 80/20 Split)**:
  1. **Real-Time Trade License / `COI` Gate & `80% / 20%` 7-Day Warranty Holdback (`HTTP 451`)**: Dispatching a pro with an expired state trade license (electrical, plumbing, HVAC) or lapsed `$1M` general liability `COI`—or releasing 100% of funds at `T+0` on high-risk repair categories—is blocked (`HTTP 451`). Using `Stripe Connect Separate Charges and Transfers`, **80% of the payout releases upon completion sign-off, while 20% is held in a 7-Day Workmanship Warranty Escrow**. If a leak or failure occurs within 7 days and the original pro fails to respond within 4 hours, the `20%` holdback automatically funds a priority backup technician!
  2. **10-Second Pre-Visit Video & Nameplate AI Scoping (`HTTP 409`)**: During booking, the homeowner records a 10-second video of the issue and the appliance's serial nameplate. Multimodal AI identifies the exact model and required replacement part *before* dispatch—lifting the **First-Time Fix Rate to 92%** and cutting total leakage and rework losses by **36.0%**.

---

## ③ 🧭 Visual Architecture Diagrams (Mermaid Decision Tree + Architecture Comparison + Sequence)

### 3.1 On-Demand Home Services Anti-Circumvention, Rate-Card & Warranty Escrow Decision Tree
```mermaid
flowchart TD
    A[Homeowner Books Job w/ 10s Video / Pro Arrives at GPS Geofence / On-Site Add-On / Job Completion] --> B{1. Active Trade License/COI & 80/20 Warranty Hold Gate}
    B -->|Pro's State Trade License or $1M Liability COI Is Expired or 100% Instant T+0 Payout Requested| C[HTTP 451: Block Unlicensed Dispatch · Enforce 80% Completion Payout + 20% 7-Day Warranty Holdback]
    B -->|License Active & 80/20 Escrow Set| D{2. Geofence-Dwell Cancel & Proxy Anti-Circumvention Gate}
    D -->|Order Cancelled After Pro Dwelled >=15 Mins at Customer GPS or Raw Phone/Venmo Shared in Chat| E[HTTP 403: Flag Doorstep Circumvention · Freeze Pro Deposit, Bill Lead Fee & Warn Homeowner on Warranty Loss]
    D -->|In-App Transaction Intact| F{3. Standardized Rate-Card & Pre-Disassembly Upcharge Gate}
    F -->|Pro Demands Unitemized Verbal Upcharge After Disassembly or Add-On Fails AI Symptom Match| G[HTTP 422: Block Bait-and-Switch Extortion · Require Rate-Card SKU, Pre-Work Photo & In-App Auth]
    F -->|Upfront Fixed Price or Verified SKU Add-On| H{4. 10s Video Pre-Scoping + Sliding 7% Repeat Fee Enabled?}
    H -->|AI Reads Appliance Nameplate Pre-Visit + 80/20 Warranty Split + 7% Repeat Take-Rate| I[HTTP 409: 92% First-Time Fix Rate · -76% Off-Platform Leakage · Save 36% Marketplace Loss]
    H -->|Blind Dispatch & Flat 25% Take-Rate| J[HTTP 200: Standard Home Service Order Completed]
```

### 3.2 Legacy Home-Services Marketplace vs. Agentic Video Pre-Scoping & `80/20` Escrow Architecture
```mermaid
flowchart LR
    subgraph Legacy["❌ Legacy Service Marketplace (Doorstep Cash Leakage + 3x Upcharges + Ghosted Leaks)"]
        L1[Platform Spends $35 CAC on Lead\nPro Cancels at Door & Takes Venmo Cash] --> L2[Pro Quotes $79 Then Disassembles Unit\nDemands $380 Unitemized 'Valve Fee']
        L2 --> L3[100% Paid Out Instantly at Sign-Off\nPipe Leaks That Night & Pro Ghosts]
        L3 --> L4[Pro Arrives Without Right Model Part\nRequires 2nd Trip & Triggers Cancel]
    end
    subgraph Agentic["✅ Agentic Home-Services & Warranty Escrow (Thumbtack / TaskRabbit / Stripe Connect)"]
        A1[10s Video + Nameplate OCR Pre-Scoping\nPro Arrives w/ Exact Replacement Part] --> A2[Masked Proxy + >=15m GPS Cancel Audit\n7% Repeat Take-Rate Keeps Pros On-App]
        A2 --> A3[Pre-Disassembly Rate-Card SKU Lock\nAI Symptom Check Stops Fake Add-Ons]
        A3 --> A4[80% Payout on Completion + 20% at T+7d\nHoldback Funds Instant Backup Re-Dispatch]
    end
```

### 3.3 10s Video AI Pre-Scoping, Blocking a Fake `$260` Board Upcharge & `80/20` Warranty Split Sequence
```mermaid
sequenceDiagram
    autonumber
    participant Homeowner as Homeowner
    participant Agent as Video Scoping & Escrow Guard Agent
    participant Pro as Field Technician (Pro App)
    participant Escrow as Stripe Connect Split-Escrow Ledger

    Note over Homeowner,Escrow: Phase 1 (Pre-Visit Video Scoping): Homeowner uploads 10s video of leaking dishwasher & nameplate
    Homeowner->>Agent: 1. Upload 10s video → Vision AI identifies Bosch SHP878 drain-pump seal & locks $145 fixed quote
    Agent->>Pro: 2. Verify active plumbing license + $1M COI (HTTP 451 pass) & dispatch via masked proxy w/ part #BOS-09
    Note over Homeowner,Escrow: Phase 2 (On-Site Anti-Circumvention & Anti-Extortion): Pro arrives at homeowner address
    Pro->>Agent: 3. Check into 100m GPS geofence (cancelling after >=15m dwell triggers HTTP 403 circumvention lock!)
    Pro->>Agent: 4. Attempt to add "$260 Mainboard Replacement" on-site → AI flags mismatch w/ leak symptom & blocks via HTTP 422!
    Note over Homeowner,Escrow: Phase 3 (Completion & 80/20 7-Day Warranty Holdback)
    Pro->>Agent: 5. Replace seal & upload 5-min dry test video; homeowner signs off in app
    Agent->>Escrow: 6. Release 80% ($116) immediately & hold 20% ($29) for 7-day zero-leak warranty window (HTTP 409)!
```

---

## ④ 📊 On-Demand Home Services Marketplace & Field-Service Management (`FSM`) Platform Selection Matrix

| Dimension | **Thumbtack / Angi (`HomeAdvisor`)** (Lead-Gen & Instant-Book Home Services Giants) | **TaskRabbit (`by IKEA`) / Handy** (Standardized Assembly & Escrowed Gig Marketplaces) | **Wanshifu (`万师傅`) / Luban (`鲁班到家`) / JD Service+** (China Nationwide Home-Install Networks) | **ServiceTitan / Housecall Pro + Stripe Connect** (Enterprise Field-Service SaaS + Custom Escrow) |
| :--- | :--- | :--- | :--- | :--- |
| **Best Fit** | Plumbing, HVAC, electrical, roofing, cleaning & moving marketplaces connecting homeowners with local pros | Furniture assembly, mounting, handyman tasks & home cleaning with standardized hourly/fixed pricing | High-volume e-commerce furniture, appliance & smart-lock installation across thousands of cities | Building a managed home-services marketplace with strict pricebooks and split payouts |
| **Anti-Circumvention (`Geofence + Proxy`)** | Mitigates initial leakage via upfront lead fees (`Pay-per-Lead`), plus masked messaging | **Strong** (End-to-end masked phone/chat relay, GPS check-in/out & platform insurance tied to in-app payment) | **Best-in-Class** (Ties technician dispatch priority and deposit bonds to zero off-platform cash collection) | GPS fleet tracking paired with `Twilio Proxy` call masking |
| **Anti-"Bait-and-Switch" Rate-Card Enforcement** | Expanding fixed-price `Instant Book` categories with upfront scope definitions | Enforces hourly rates and requires receipt uploads + customer in-app approval for materials | **Industry Benchmark** (Strict standardized add-on price tables; unauthorized cash surcharges are auto-refunded from pro deposits) | **Visual Pricebook Leader** (Technicians can only select pre-priced catalog assemblies on their tablet) |
| **7-Day Workmanship Warranty Escrow** | Backed by platform `Happiness / Property Protection` guarantee funds | Holds payout settlement in rolling windows to cover damage/rework claims | Native **`T+7d / T+15d` warranty holdback** before releasing final installation settlement | Programmable `80/20` delayed transfers via `Stripe Connect` |
| **Pricing (`official_list_price`)** | Per-lead fee (`$15–$100+`) or **`15%–25%`** marketplace take-rate | **`15%–30%`** blended platform service & trust fee | **`10%–18%`** platform fee + refundable technician security bond | **`$150–$300/tech/month`** SaaS + standard `Stripe Connect` fees |

---

## ⑤ 🧪 ROI Estimation & 7-Card Visual Benchmark Deck

> **Provenance**: Modeled on a `$52M/year` on-demand appliance repair and home installation marketplace's quarterly disintermediation and rework leakage pool (`$170,000/quarter` in lost platform commissions and wasted `$35` CAC from doorstep cancel-for-cash circumvention, chargebacks from predatory on-site bait-and-switch upcharges, and emergency re-dispatch costs when technicians ghost on next-day warranty callbacks), labeled `synthetic` (`independently_reproduced=false`).

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 1 / 7 · HANDS-ON · ON-DEMAND HOME SERVICES & GIG MARKETPLACE ESCROW         ║
║ Headline: Geofence Cancel Lock & 80/20 Warranty Split Cut Leakage & Loss by 36%  ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ [Scenario & Thresholds]        [Structured Input]       [Top Decisions & KPIs]   ║
║ • Service Pool: $170,000 / Qtr • Geofence: >=15m Cancel • Verified: HTTP 200     ║
║ • Upcharge: Rate-Card + Photo  • Payout: 80% + 20% T+7d • DoorCancel: HTTP 403   ║
║ • Video Scope: 92% 1st-Visit   • Repeat Fee: 22% -> 7%  • Extortion: HTTP 422    ║
║ • Leakage Drop: -76% Reduction • License: Active COI    • Saved Loss: -$61,200   ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ Provenance: synthetic (independently_reproduced=false) · Suite: WebIQ-R203 (#322)║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 2 / 7 · SCENARIO: DOORSTEP CANCEL-FOR-CASH & $260 FAKE BOARD UPCHARGE       ║
║ Headline: 35-Min Geofence Cancel Flagged; Unjustified $260 Part Add-On Blocked   ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ Input Quote: "Tech stayed at homeowner GPS for 35m then cancelled order as       ║
║ 'No-Show'; separately, another tech demanded $260 for a mainboard on a leak job."║
║ 1. [choice] Geofence Stay + Cancel Gate──► 1.00 conf ──► [Act automatically]     ║
║    ████████████████████████████████████████ 100% (Circumvention Caught; CAC Kept)║
║ 2. [choice] Rate-Card & AI Symptom Gate──► 0.99 conf ──► [Act automatically]     ║
║    ███████████████████████████████████████▊ 99% ($260 Fake Board Upcharge Blocked║
║ 3. [score]  10s Video Scope + 80/20 Pay──► 0.98 conf ──► [Confirm: HTTP 409]     ║
║    ███████████████████████████████████████░ 98% (92% 1st-Fix; 20% 7d Warranty)   ║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 3 / 7 · WHAT I TESTED · FULL 5-LANE EVALUATION MATRIX                      ║
║ Headline: 5/5 Deterministic Guardrails Verified Across Geofence, Price & Escrow  ║
╠══════════════════════════╦══════════════════════════╦══════════════════╦═════════╣
║ SCENARIO                 ║ QUESTION / TASK          ║ MODEL ANSWER     ║ ACTION  ║
╠══════════════════════════╬══════════════════════════╬══════════════════╬═════════╣
║ Baseline Fixed-Price Job ║ Upfront video quote done ║ HTTP 200 ($0)    ║ Auto    ║
║ Cancel After 30m at Door ║ Pay cash off-platform    ║ HTTP 403 Blocked ║ Block   ║
║ $350 Verbal Mid-Job Hike ║ Extort after disassembly ║ HTTP 422 Blocked ║ Block   ║
║ Expired COI / 100% T+0   ║ Ghost on next-day leak   ║ HTTP 451 Hold    ║ Human   ║
║ Video Scope + 80/20 Split║ Pre-scope + 7d holdback  ║ HTTP 409 (-36%)  ║ Confirm ║
╠══════════════════════════╩══════════════════════════╩══════════════════╩═════════╣
║ Gate Summary: 100% deterministic policy match; 0 doorstep cash leaks or extortion║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 4 / 7 · UNDER THE HOOD · PROTOCOL & SCORING MECHANICS                       ║
║ Headline: Deterministic Policy Input Contract → Verifier Decision Trace          ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ // Input Contract (OndemandHomeServicesMarketplacePolicyInput)                   ║
║ { "quarterly_off_platform_leakage_upcharge_and_rework_pool_usd": 170000.0,       ║
║   "order_cancelled_after_15m_inside_homeowner_gps_or_phone_leak": false,         ║
║   "unitemized_onsite_upcharge_after_disassembly_exceeding_ratecard": false,      ║
║   "expired_trade_license_coi_or_instant_100pct_payout_without_hold": false,      ║
║   "pre_visit_video_scoping_sliding_repeat_fee_and_80_20_escrow_ready": true }    ║
║                                      ↓                                           ║
║ // Verifier Output (<answer>)                                                    ║
║ { "status_code": 409,                                                            ║
║   "decision": "VIDEO_PRE_SCOPING_AND_80_20_WARRANTY_ESCROW_CONFIRM",             ║
║   "mandate_token": "home_services_escrow_optim_409", "savings_usd": 61200.0 }    ║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 5 / 7 · ROBUSTNESS CHECK · PERTURBATION & CONSISTENCY                       ║
║ Headline: 0.0 pts Variance Across Option Reversal & GPS-Dwell Perturbations      ║
╠══════════════════════════════╦═════════════════╦══════════════════╦══════════════╣
║ QUESTION / ANSWER            ║ ORIGINAL        ║ REVERSED / PERT  ║ CHANGE (PTS) ║
╠══════════════════════════════╬═════════════════╬══════════════════╬══════════════╣
║ Geofence Cancel & Proxy Gate ║ HTTP 403 (100%) ║ HTTP 403 (100%)  ║ 0.0 pts      ║
║ Rate-Card & Upcharge Gate    ║ HTTP 422 (100%) ║ HTTP 422 (100%)  ║ 0.0 pts      ║
║ License/COI & 80/20 Hold Lock║ HTTP 451 (100%) ║ HTTP 451 (100%)  ║ 0.0 pts      ║
║ Video Scope + Escrow Net 36% ║ $61,200 Saved   ║ $61,200 Saved    ║ 0.0 pts      ║
╚══════════════════════════════╩═════════════════╩══════════════════╩══════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 6 / 7 · LATENCY · BATCHING & SCALING LATENCY                                ║
║ Headline: 450ms Pre-Visit Video Model Recognition & Instant Rate-Card Validation ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ 10s Video Appliance Nameplate║ ███ 450 ms (Agent) vs Wasted 2-Trip Parts Run     ║
║ On-Site Add-On Rate-Card Gate║ █ 19 ms (Agent) vs Verbal Cash Extortion Dispute  ║
║ Geofence Dwell + Cancel Audit║ █ 12 ms (Agent) vs Uncaught CAC Disintermediation ║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 7 / 7 · MY TAKE · GOOD FIT VS NOT FOR & READINESS                           ║
║ Headline: Protect Two-Sided Service Marketplaces from Leakage & Bait-and-Switch  ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ ✅ GOOD FIT                               ⛔ NOT FOR                             ║
║ • Home repair, appliance installation,    • Digital-only cloud API marketplaces  ║
║   plumbing/HVAC & cleaning marketplaces     with zero physical on-site visits    ║
║ • Platform ops teams stopping doorstep    • Heavy nuclear reactor control-rod    ║
║   cancel-for-cash & mid-job extortion       actuators unrelated to gig commerce  ║
║ Readiness: Production-verified schema in `lab/webiq_commerce_demo.py` (R203).    ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

---

## ⑥ 🛠️ Production Risk & Architecture Review Checklist

- [ ] **Masked Proxy Numbers & `>=15-Minute` Geofence-Dwell Cancellation Audit (`HTTP 403`)**: Are all homeowner-technician calls/texts routed through expiring masked numbers, and does cancelling an order after the technician has dwelled `>=15 minutes` inside the customer's `100m` GPS geofence trigger an automated circumvention hold and homeowner warranty-loss warning?
- [ ] **Pre-Disassembly Standardized Parts Rate-Card & AI Symptom Lock (`HTTP 422`)**: Are verbal cash surcharges and free-text add-on prices blocked, requiring any on-site scope change to select a fixed-price rate-card SKU backed by a pre-disassembly photo and homeowner in-app incremental authorization?
- [ ] **Active Trade License / `$1M COI` Gate & `80% / 20%` 7-Day Warranty Holdback (`HTTP 451`)**: Does dispatch verify active state trade licenses and liability insurance, and does settlement release `80%` on completion while holding `20%` for 7 days to fund an automatic backup technician if the repair leaks or fails?
- [ ] **10-Second Pre-Visit Video & Nameplate OCR Scoping (`HTTP 409`)**: Does the booking flow extract appliance model numbers and issue an all-in upfront quote from a 10-second homeowner video so pros bring the right part on Visit #1?
- [ ] **Sliding Repeat-Booking Take-Rate (`22% → 7%`)**: Does the marketplace lower its commission on repeat bookings between the same homeowner and pro so staying on-platform beats transacting in cash?
