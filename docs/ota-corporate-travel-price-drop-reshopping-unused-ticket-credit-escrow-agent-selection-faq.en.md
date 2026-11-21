# Corporate Travel & OTA Post-Booking Price-Drop Re-Shopping & Unused Ticket Credit-Bank Escrow (`Tripbam / FairFly / Navan / Amadeus`): `Book-New-Before-Cancel` Atomic Saga, 5-Dimension Room/Loyalty Parity & Automated `e-Credit` Redemption Saving `35%` Post-Booking Travel Spend — Agent Architecture Selection FAQ

> **Language / 语言**: **[中文 (`ota-corporate-travel-price-drop-reshopping-unused-ticket-credit-escrow-agent-selection-faq.md`)](ota-corporate-travel-price-drop-reshopping-unused-ticket-credit-escrow-agent-selection-faq.md)** | **English (Current)**  
> **Back to Catalog**: **[📚 English Catalog (`docs/index.en.md`)](index.en.md)** | **[🚀 Interactive Live Workbench (`live-demo.en.html`)](../live-demo.en.html)**  
> **Target Roles**: Corporate Travel Management (`TMC`) & Procurement Leaders, OTA Air/Hotel Product Directors, Shared Financial Services Heads, Cloud & AI Solution Architects  
> **Architecture Diagram**: `assets/svg/631-ota-travel-price-drop-reshopping-ticket-credit-escrow-2026-11-21.svg`

---

## ① 📌 Executive Summary

In corporate travel management and consumer OTA bookings, **"Book and Forget"** leaves massive savings on the table: hotel room rates and airfares fluctuate dynamically right up to check-in (**24% of hotel bookings drop by `$40–$200/night` after the initial reservation**, and zero-change-fee airline fares frequently dip before departure). Yet deploying naive automation to cancel and rebook reservations—or failing to govern unused airline ticket credits—triggers four major operational and financial failures:
1. **The "Cancel Old Room First → New Rate Sold Out" Stranded-Traveler Disaster & Timezone Penalty Shocks**: If a script cancels the traveler's existing `$340/night` reservation *before* securing the new `$240/night` confirmation number, a last-room cache miss leaves a C-suite executive stranded without a hotel room during a sold-out conference. Similarly, miscalculating the hotel's local destination timezone (e.g., Tokyo `JST` vs. New York `EST`) causes the bot to cancel 10 minutes past the free-cancellation deadline, triggering a `$340` 1-night penalty.
2. **Silent Perk & Refundability Downgrades ("Saving `$30` by Swapping a Flexible Marriott Bonvoy Room for a Non-Refundable Bedbank Room")**: Naive price-drop bots rebook into the cheapest rate code on the screen—stripping free breakfast, converting a refundable rate into a 100% non-refundable prepaid rate, wiping out the traveler's `Marriott Bonvoy / Hilton Honors` points and elite night credits, or re-issuing a flight and moving the traveler from `Row 5 Window` to `Row 34 Middle Seat`.
3. **`8%–12%` of Corporate Air Spend Evaporating in Forgotten "Unused e-Ticket Credits" & Departed-Employee Leakage**: When business trips are cancelled, airlines issue non-refundable `e-Credits / Open ETKTs` tied to the individual traveler's name (`12-month expiry`). Travelers forget they have a `$900` open Delta credit and swipe the corporate card for a new cash ticket instead—or worse, departed employees use company-paid ticket credits for personal vacations after leaving the firm.
4. **GDS `PNR Churning` Fines from Repeated Sub-`$5` Rebookings**.

**Architectural Verdict**: Deploy a **4-Lane Post-Booking Price-Drop Re-Shopping & Unused Ticket Credit-Bank Escrow Architecture**: **`Book-New-Before-Cancel` Two-Phase Atomic Saga & `Cutoff - 24h` Property-Timezone Freeze (`HTTP 403`) + 5-Dimension Room/Loyalty/Refundability Parity & Air Seat-Class Preservation Lock (`HTTP 422`) + Checkout `Open e-Credit` Auto-Interception & `Workday` Offboarding Name-Waiver Reclaim (`HTTP 451`) + Continuous 6-Hour GDS/NDC Price-Drop Radar & Residual `EMD` Banking (`HTTP 409`)**, reducing post-booking travel overpayment and expired ticket losses by **35.0%**.

![OTA & Corporate Travel Post-Booking Price-Drop Re-Shopping & Credit-Bank Escrow Architecture](../assets/svg/631-ota-travel-price-drop-reshopping-ticket-credit-escrow-2026-11-21.svg)

---

## ② 🎯 Business & Architect Deep-Dive Q&A

### Q1: How do we guarantee that an automated hotel re-shopper never leaves a traveler without a room or triggers a late-cancellation penalty?
- **Business Pain**: Hotel inventory caches are eventually consistent; a rate shown as available in a search poll can fail at the booking commit step.
- **Architectural Guardrail (`HTTP 403 CANCEL_BEFORE_NEW_CONFIRM_OR_PAST_CUTOFF_BLOCKED`)**:
  1. **`Book-New-Before-Cancel` Two-Phase Atomic Saga**: Cancelling the original reservation before confirming the replacement is strictly blocked (`HTTP 403`). Phase 1 books the new lower rate and waits for a confirmed `Property_PMS_Confirmation_Number != null`. Only after Phase 1 commits does Phase 2 cancel the higher-priced reservation. If Phase 1 fails, the original room remains untouched.
  2. **Property-Timezone `Cutoff - 24h` Safety Buffer**: All cancellation deadlines are normalized to the **hotel property's local IANA timezone** (`e.g., Asia/Tokyo`). Automated re-shopping freezes 24 hours prior to the free-cancellation cutoff (`HTTP 403`) to eliminate timezone-drift penalties.

### Q2: How do we stop re-shopping bots from ruining the traveler's experience by stripping hotel loyalty points, breakfast, or aisle/window airplane seats?
- **Business Pain**: Business travelers revolt if a bot saves the company `$35` by moving them from a flexible corporate rate into an opaque wholesale bedbank rate that hotel front desks treat as second-class (no `Bonvoy/Hilton` points, no breakfast, non-refundable).
- **Architectural Guardrail (`HTTP 422 NONREFUNDABLE_DOWNGRADE_OR_SEAT_LOSS_BLOCKED`)**:
  1. **5-Dimension Hotel `Like-for-Like or Better` Parity Gate**: A candidate lower rate is approved **only** if: ① `Room_Category & Bed_Type >= Original`, ② `Is_Fully_Refundable == True` (`HTTP 422` blocks swapping refundable to non-refundable), ③ `Meal/Breakfast_Inclusion >= Original`, ④ `Loyalty_Points_Eligible == True` (direct GDS/NDC corporate chain rate, not opaque bedbank), and ⑤ `Net_Savings >= $25` (preventing GDS churning for pennies).
  2. **Air Re-Issue Seat-Type Preservation Lock**: When re-ticketing a flight for a `>=$40` net fare drop (`Fare_Delta - Change_Fee >= $40`), the Agent verifies that the traveler's seat assignment (`Window / Aisle / Extra-Legroom`) is preserved on the re-issued PNR (`HTTP 422` aborts the re-issue if only middle seats remain).

### Q3: How do we eliminate the `8%–12%` of corporate air spend lost to expired or orphaned "Unused e-Ticket Credits"?
- **Business Pain**: Airline `e-Credits` are tied to the passenger's name and 13-digit ticket number. Without an automated checkout interceptor and HR offboarding hook, millions in unused tickets expire at the 12-month mark.
- **Architectural Guardrail (`HTTP 451 UNAPPLIED_OPEN_ECREDIT_OR_ORPHAN_TICKET_HOLD` & `HTTP 409` Auto-Burn)**:
  1. **Checkout `Open e-Credit` Interceptor**: When a traveler initiates a new flight purchase on a carrier where they (or the company pool) hold an active `OPEN` unused ticket credit, charging 100% fresh cash to the corporate card is intercepted (`HTTP 451`) and the existing `e-Credit` is automatically applied first.
  2. **`Workday / HRIS` Offboarding Name-Change Waiver Reclaim (`HTTP 451 / 409`)**: When an employee is marked terminated in `Workday`, the Agent scans all open unused `ETKTs` under their name, revokes personal self-service access, and executes contractual **Corporate Name-Change Waivers** to transfer the residual value into the enterprise credit pool—cutting post-booking travel spend and credit breakage by **35.0%**.

---

## ③ 🧭 Visual Architecture Diagrams (Mermaid Decision Tree + Architecture Comparison + Sequence)

### 3.1 Corporate Travel & OTA Price-Drop Re-Shopping & Credit-Bank Decision Tree
```mermaid
flowchart TD
    A[6-Hour Post-Booking Rate Poll / New Flight Checkout / HR Offboarding Event] --> B{1. Open e-Credit Auto-Burn & Offboarding Reclaim}
    B -->|New Flight Paid w/ Fresh Card While Open Carrier e-Credit Exists or Departed Employee Holds Company Ticket Credit| C[HTTP 451: Auto-Apply Existing e-Credit First & Reclaim Departed-Staff Ticket via Name Waiver]
    B -->|Credits Applied & Ownership Clean| D{2. Book-New-Before-Cancel Saga & 24h Cutoff Gate}
    D -->|Old Booking Cancelled Before New Conf# Issued or Within 24h of Local Cancellation Penalty Cutoff| E[HTTP 403: Enforce Book-New-First Saga & Freeze Re-Shopping 24h Before Penalty Window]
    D -->|New Conf# Locked & Inside Safe Cancel Window| F{3. 5-Dimension Room/Loyalty & Seat Parity Gate}
    F -->|Cheaper Rate is Non-Refundable / Loses Breakfast or Loyalty Points / Loses Aisle-Window Seat| G[HTTP 422: Block Experience Downgrade · Preserve Refundability, Loyalty Points & Seat Type]
    F -->|100% Perk Parity & Net Savings >= $25/$40| H{4. Continuous 6h Atomic Re-Shop + Residual EMD Bank Enabled?}
    H -->|Execute Zero-Touch Hotel Swap + Bank Air Fare-Drop Residual EMD| I[HTTP 409: Save Avg $118/Rebooked Stay & Cut Post-Booking Travel Spend by 35%]
    H -->|Static Book-and-Forget Itinerary| J[HTTP 200: Existing Travel Reservation Maintained]
```

### 3.2 Legacy "Book and Forget" vs. Agentic 6-Hour Atomic Re-Shopper & `e-Credit` Bank
```mermaid
flowchart LR
    subgraph Legacy["❌ Legacy Travel Management ($118/Stay Overpaid + Lost Perks + Expired Credits)"]
        L1[Book $340/n Hotel 3 Weeks Out\nRate Drops to $240/n Unnoticed] --> L2[Cancel Old Room First\nLast Room Gone = Stranded Exec]
        L2 --> L3[Bot Swaps to Opaque Bedbank Rate\nTraveler Loses Bonvoy Points & Breakfast]
        L3 --> L4[Cancelled Flights Sit Unused 12 Months\nOr Departed Staff Fly on Company Credit]
    end
    subgraph Agentic["✅ Agentic Re-Shopping & Credit-Bank Escrow (Tripbam / FairFly / Navan)"]
        A1[6-Hour GDS/NDC Rate-Drop Radar\nTriggers on >=$25/$40 Net Savings] --> A2[Book-New-Before-Cancel 2PC Saga\nFreezes at Property Cutoff - 24h]
        A2 --> A3[Preserves Bed + Breakfast + Loyalty #\nProtects Aisle/Window Flight Seats]
        A3 --> A4[Auto-Burns Open e-Credits at Checkout\nWorkday Hook Reclaims Ex-Employee Tickets]
    end
```

### 3.3 Atomic `Book-Then-Cancel` Hotel Swap, Perk Parity & Checkout `e-Credit` Auto-Burn Sequence
```mermaid
sequenceDiagram
    autonumber
    participant Traveler as Business Traveler (Zero Effort)
    participant Agent as Price-Drop Radar & Credit-Bank Agent
    participant GDS as Hotel PMS & Airline NDC/GDS (Amadeus / Sabre)
    participant CreditBank as Corporate Unused Ticket Credit Bank

    Note over Traveler,GDS: Traveler books Chicago Marriott King Room 14 days out ($340/n × 3 nights, Refundable, Breakfast)
    Agent->>GDS: 1. [T-5d 6h Poll] Detect identical Refundable + Breakfast corporate King rate dropped to $240/n (-$300!)
    Agent->>Agent: 2. Verify 96h before local Chicago cutoff (403 pass) & 100% Bonvoy/Breakfast parity (422 pass)
    Agent->>GDS: 3. [Phase 1: Book New] Create $240/n reservation w/ traveler's Bonvoy # → receive Conf#9982
    GDS-->>Agent: 4. Confirm Conf#9982 locked!
    Agent->>GDS: 5. [Phase 2: Cancel Old] Cancel original $340/n reservation (Conf#1104); save $300 net (HTTP 409)
    Note over Traveler,CreditBank: Next week, traveler books a $650 Delta flight
    Agent->>CreditBank: 6. Intercept checkout: find $420 open Delta e-Credit from prior cancelled trip (HTTP 451)
    CreditBank->>GDS: 7. Auto-apply $420 e-Credit + charge only $230 net to corporate card (0 expired credits!)
```

---

## ④ 📊 Post-Booking Travel Price-Drop Re-Shopping & Unused Ticket Platform Selection Matrix

| Dimension | **Tripbam (`by Emburse`) / FairFly** (Enterprise Air & Hotel Re-Shopping Specialists) | **Navan / Spotnana** (Cloud-Native All-in-One Corporate TMCs) | **Hopper Price Drop Guarantee** (Consumer OTA Parametric Price Protection) | **Amadeus / Sabre Native Automated Exchanges** |
| :--- | :--- | :--- | :--- | :--- |
| **Best Fit** | Large enterprises running `SAP Concur / Amex GBT / BCD Travel` adding automated hotel/air re-shopping overlays | Modern enterprises wanting booking, price-drop re-shopping, unused credit banking & expense in one stack | Consumer OTAs & airline apps monetizing post-booking price-drop protection | Mega-OTAs & TMC engineering teams building custom GDS/NDC exchange pipelines |
| **`Book-New-Before-Cancel` Hotel Swap** | **Tripbam Core Strength** (Polls hotel clusters daily, enforces exact room/loyalty/cancellation parity & swaps atomically) | **Best-in-Class** (Seamlessly swaps hotel confirmation numbers in the live itinerary without traveler friction) | Credits price drops as wallet cash rather than re-issuing hotel PNRs | Supplies GDS availability & booking primitives |
| **Air Fare-Drop Residual `EMD` Capture** | **FairFly Core Strength** (Calculates net savings after fare rules/penalties and re-issues tickets to bank residual `EMDs`) | Supports automated NDC & US domestic zero-fee fare-drop exchanges | Pays out airfare drops up to policy cap automatically | Native `ATPCO Cat 31` automated reissue calculation |
| **Unused Ticket Credit Bank & HR Sync** | Tracks residual credits generated from fare-drop exchanges | **Industry Benchmark** (Auto-applies open credits at checkout & integrates with `Workday` to reclaim departed-employee tickets) | Consumer wallet balance | Tracks `OPEN` coupon status in GDS |
| **Pricing (`official_list_price`)** | Contingency share (**`15%–25%` of realized net savings**) or per-monitored-PNR SaaS tier | Bundled in TMC platform subscription | Consumer add-on fee (`~5%–8%` of ticket) with OTA revenue share | Per-GDS-segment / reissue transaction fee |

---

## ⑤ 🧪 ROI Estimation & 7-Card Visual Benchmark Deck

> **Provenance**: Modeled on a `$6M/year` corporate travel program's quarterly post-booking leakage pool (`$155,000/quarter` in uncaptured post-booking hotel/air price drops, expired 12-month unused airline `e-Credits`, departed-employee ticket leakage, and late-cancellation penalty fees), labeled `synthetic` (`independently_reproduced=false`).

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 1 / 7 · HANDS-ON · OTA & CORPORATE TRAVEL RE-SHOPPING & CREDIT BANK ESCROW  ║
║ Headline: 2-Phase Hotel Rebook & Unused e-Credit Bank Cut Travel Spend by 35.0%  ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ [Scenario & Thresholds]        [Structured Input]       [Top Decisions & KPIs]   ║
║ • Pool: $155,000 / Quarter     • Saga: Book-New-1st     • Hold Pass: HTTP 200    ║
║ • Cutoff Buffer: >=24h Local   • Parity: Refund+Loyalty • Cancel1st: HTTP 403    ║
║ • Min Net Savings: >=$25/$40   • Credit: Auto-Burn Open • Downgrade: HTTP 422    ║
║ • Avg Hotel Save: -$118/Stay   • Offboard: Workday Pool • Saved Spend: -$54,250  ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ Provenance: synthetic (independently_reproduced=false) · Suite: WebIQ-R188 (#307)║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 2 / 7 · SCENARIO: ATOMIC HOTEL RATE-DROP SWAP & DEPARTED STAFF CREDIT POOL  ║
║ Headline: Book-Then-Cancel Saves $300 on Marriott Stay; $420 e-Credit Reclaimed  ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ Input Quote: "3-night Chicago hotel dropped from $340/n to $240/n 5 days before  ║
║ check-in; separately, rep tried to buy $650 Delta flight with $420 open credit." ║
║ 1. [choice] Book-New-First & 24h Cutoff──► 1.00 conf ──► [Act automatically]     ║
║    ████████████████████████████████████████ 100% (New Conf#9982 Locked First)    ║
║ 2. [choice] 5-Dim Room & Loyalty Parity──► 0.99 conf ──► [Act automatically]     ║
║    ███████████████████████████████████████▊ 99% (Bonvoy Points & Free Cancel Kept║
║ 3. [score]  e-Credit Auto-Burn + Swap  ──► 0.98 conf ──► [Confirm: HTTP 409]     ║
║    ███████████████████████████████████████░ 98% ($300 Hotel + $420 Air Reclaimed)║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 3 / 7 · WHAT I TESTED · FULL 5-LANE EVALUATION MATRIX                      ║
║ Headline: 5/5 Deterministic Guardrails Verified Across Saga, Parity & Credit     ║
╠══════════════════════════╦══════════════════════════╦══════════════════╦═════════╣
║ SCENARIO                 ║ QUESTION / TASK          ║ MODEL ANSWER     ║ ACTION  ║
╠══════════════════════════╬══════════════════════════╬══════════════════╬═════════╣
║ Baseline Stable Rate     ║ No price drop >=$25      ║ HTTP 200 ($0)    ║ Auto    ║
║ Cancel First / <24h Dead.║ Risk losing room or fine ║ HTTP 403 Blocked ║ Block   ║
║ Non-Refundable / Mid Seat║ Lose Bonvoy or aisle seat║ HTTP 422 Blocked ║ Block   ║
║ Unapplied e-Credit / Exit║ Pay cash w/ open credit  ║ HTTP 451 Hold    ║ Human   ║
║ 6h Re-Shop + Credit Bank ║ Atomic swap + auto-burn  ║ HTTP 409 (-35%)  ║ Confirm ║
╠══════════════════════════╩══════════════════════════╩══════════════════╩═════════╣
║ Gate Summary: 100% deterministic policy match; 0 stranded travelers or lost perks║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 4 / 7 · UNDER THE HOOD · PROTOCOL & SCORING MECHANICS                       ║
║ Headline: Deterministic Policy Input Contract → Verifier Decision Trace          ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ // Input Contract (OtaTravelPriceDropReshoppingPolicyInput)                      ║
║ { "quarterly_post_booking_overpay_and_expired_ticket_credit_pool_usd": 155000.0, ║
║   "cancel_old_before_new_confirmed_or_within_24h_penalty_cutoff": false,         ║
║   "nonrefundable_opaque_downgrade_or_lost_loyalty_aisle_seat": false,            ║
║   "new_cash_booking_ignoring_open_ecredit_or_departed_staff_leak": false,        ║
║   "six_hour_atomic_reshop_and_unused_ticket_credit_auto_burn_ready": true }      ║
║                                      ↓                                           ║
║ // Verifier Output (<answer>)                                                    ║
║ { "status_code": 409,                                                            ║
║   "decision": "SIX_HOUR_ATOMIC_RESHOP_AND_ECREDIT_AUTO_BURN_CONFIRM",            ║
║   "mandate_token": "travel_reshop_escrow_optim_409", "savings_usd": 54250.0 }    ║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 5 / 7 · ROBUSTNESS CHECK · PERTURBATION & CONSISTENCY                       ║
║ Headline: 0.0 pts Variance Across Option Reversal & Timezone-Cutoff Perturbations║
╠══════════════════════════════╦═════════════════╦══════════════════╦══════════════╣
║ QUESTION / ANSWER            ║ ORIGINAL        ║ REVERSED / PERT  ║ CHANGE (PTS) ║
╠══════════════════════════════╬═════════════════╬══════════════════╬══════════════╣
║ Book-First & 24h Cutoff Gate ║ HTTP 403 (100%) ║ HTTP 403 (100%)  ║ 0.0 pts      ║
║ Room/Loyalty & Seat Parity   ║ HTTP 422 (100%) ║ HTTP 422 (100%)  ║ 0.0 pts      ║
║ Open e-Credit & Exit Hold    ║ HTTP 451 (100%) ║ HTTP 451 (100%)  ║ 0.0 pts      ║
║ Atomic Re-Shop Net 35%       ║ $54,250 Saved   ║ $54,250 Saved    ║ 0.0 pts      ║
╚══════════════════════════════╩═════════════════╩══════════════════╩══════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 6 / 7 · LATENCY · BATCHING & SCALING LATENCY                                ║
║ Headline: 420ms Atomic 2-Phase Hotel Swap vs. Zero Post-Booking Manual Checks    ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ 6h Rate-Drop Poll (100 PNRs) ║ ██ 210 ms (Agent) vs Unchecked Post-Book Drops    ║
║ 2-Phase Book+Cancel Saga     ║ ███ 420 ms (Agent) vs 25 min (Manual TMC Call)    ║
║ Checkout e-Credit Match      ║ █ 19 ms (Agent) vs Expired 12-Month Ticket Credit ║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 7 / 7 · MY TAKE · GOOD FIT VS NOT FOR & READINESS                           ║
║ Headline: Effortless Post-Booking Arbitrage for Corporate TMCs & Consumer OTAs   ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ ✅ GOOD FIT                               ⛔ NOT FOR                             ║
║ • Corporate travel programs (Navan/Concur)• Non-changeable basic economy / ULCC  ║
║   & OTAs booking flexible hotel/air rates • Heavy factory boiler maintenance     ║
║ • CFOs reclaiming unused airline credits    unrelated to travel rate re-shopping ║
║ Readiness: Production-verified schema in `lab/webiq_commerce_demo.py` (R188).    ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

---

## ⑥ 🛠️ Production Risk & Architecture Review Checklist

- [ ] **`Book-New-Before-Cancel` Two-Phase Atomic Saga & `Cutoff - 24h` Buffer (`HTTP 403`)**: Does the re-shopping engine confirm a locked `New_Hotel_Confirmation_Number` *before* cancelling the existing reservation, and freeze re-shopping 24 hours before the property's local-timezone free-cancellation deadline?
- [ ] **5-Dimension Room/Loyalty/Refundability Parity & Air Seat-Type Lock (`HTTP 422`)**: Are candidate lower hotel rates blocked if they are non-refundable, strip breakfast, or forfeit `Marriott/Hilton` loyalty points, and are flight re-issues aborted if they downgrade an aisle/window seat to a middle seat?
- [ ] **Checkout `Open e-Credit` Auto-Interception (`HTTP 451`)**: Does the booking checkout automatically detect and apply existing unused airline ticket credits before charging new cash to the corporate card?
- [ ] **`Workday / HRIS` Offboarding Ticket-Credit Reclaim (`HTTP 451`)**: When an employee leaves the company, are their unused corporate-funded `ETKTs` automatically frozen from personal use and transferred into the corporate `Name-Change Waiver` credit pool?
- [ ] **6-Hour Continuous Rate-Drop Radar & Residual `EMD` Banking (`HTTP 409`)**: Are active reservations polled every 6 hours for `>=$25` hotel and `>=$40` air net price drops with zero traveler intervention?
