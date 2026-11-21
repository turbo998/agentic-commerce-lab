# Cruise Line `Fly-Cruise` Embarkation, Shore Excursion & Onboard `SeaPass` Folio Escrow (`Royal Caribbean / Carnival / NCL / Amadeus Cruise / Oracle SPMS`): `T-6h` All-Aboard Air Buffer, `PVSA` Cabotage Lock, Back-to-Ship Guarantee & `Starlink` Incremental Auth Saving `36%` Voyage Loss — Agent Architecture Selection FAQ

> **Language / 语言**: **[中文 (`ota-cruise-fly-cruise-embarkation-shore-excursion-onboard-folio-escrow-agent-selection-faq.md`)](ota-cruise-fly-cruise-embarkation-shore-excursion-onboard-folio-escrow-agent-selection-faq.md)** | **English (Current)**  
> **Back to Catalog**: **[📚 English Catalog (`docs/index.en.md`)](index.en.md)** | **[🚀 Interactive Live Workbench (`live-demo.en.html`)](../live-demo.en.html)**  
> **Target Roles**: Cruise Line Digital & Revenue Management VPs (`Royal Caribbean / Carnival / NCL / MSC`), OTA Cruise Packaging Directors, Shipboard `PMS` & Shore-Excursion Operations Leaders, Cloud & AI Solution Architects  
> **Architecture Diagram**: `assets/svg/666-ota-cruise-fly-cruise-shore-excursion-folio-escrow-2026-11-22.svg`

---

## ① 📌 Executive Summary

In ocean and expedition cruise commerce (`$4,000–$18,000+` per stateroom across `Royal Caribbean`, `Carnival`, `Norwegian Cruise Line`, `MSC`, `Viking`, `Amadeus Cruise`, `Expedia Cruises`), a single voyage orchestrates four tightly coupled commercial ledgers: **① `Fly-Cruise` Inbound Airfare to the Embarkation Port → ② `T-90d` Stateroom Fare & Cabin Upgrade Waterfall → ③ Multi-Country Port Shore Excursions → ④ Cashless Onboard `SeaPass / Medallion` Folio Settlement (Specialty Dining, Beverage Packages, Duty-Free Boutiques & Casino Markers)**. Because a 5,000-passenger cruise ship cannot wait at the pier for a delayed flight or a late tour bus, cruise lines and OTAs suffer three costly operational failures:
1. **Tight Same-Day `Fly-Cruise` Connections ("Missed the Boat" `$8,000` Forfeiture) & U.S. `PVSA` (`$941/Pax`) Cabotage Fines**: A family books a flight landing at Miami International Airport at `1:00 PM` for a cruise whose mandatory `CBP` **All-Aboard Manifest Cutoff is `2:30 PM` (`4:00 PM` sail-away)**. A routine 90-minute air-traffic delay leaves the family stranded at the terminal watching the ship sail away with `$0` refund! Worse, if the stranded family flies to Key West or Juneau (another U.S. port) to catch the foreign-flagged ship mid-voyage and disembarks back in a U.S. port without visiting a Qualifying Distant Foreign Port, U.S. Customs (`CBP`) levies a mandatory **`$941 per passenger` penalty under the Passenger Vessel Services Act (`PVSA, 46 U.S.C. § 55103`)**!
2. **Unprotected Third-Party Shore Excursions ("Pier Runners") & Stateroom Beverage-Package Sharing**: Guests book a cheap independent island tour scheduled to return 20 minutes before sail-away without a **Back-to-Ship Transport Guarantee**, getting stranded in a foreign port when traffic stalls! Onboard, one adult in a 2-adult stateroom buys an `$85/day` Unlimited Deluxe Beverage Package and orders 14 drinks a day to share with their non-paying roommate.
3. **Disembarkation-Morning `$3,500` Onboard Folio Card Declines ("Walked Off the Ship Unpaid")**: A passenger links a `$150`-balance prepaid debit card at check-in, racks up `$3,500` in duty-free watches and casino charges at sea using their cabin `SeaPass` card, and walks off the gangway at 7:00 AM on disembarkation morning while the batch credit-card settlement declines!

**Architectural Verdict**: Deploy a **4-Lane Cruise `Fly-Cruise`, Shore-Excursion & Onboard Folio Escrow Architecture**: **`T-6.0h` All-Aboard Flight Arrival Buffer (or Mandatory `D-1` Pre-Cruise Hotel) & `PVSA` (`46 U.S.C. § 55103`) Port-Pair Legality Gate (`HTTP 403`) + `T-120m` Shore-Excursion Dock Return Margin (with Verified Back-to-Ship Guarantee) & Cabin-Wide Adult Beverage-Package Parity Lock (`HTTP 422`) + Live `Starlink` `$250`-Step `ISO 8583` Incremental Folio Authorization & Gangway Security Beacon Hold (`HTTP 451`) + Sealed Cabin Bid-Up Waterfall (`Interior -> Balcony -> Suite`) & 5-Second Skipped-Port Tax/Tour Auto-Rebate (`HTTP 409`)**, reducing missed-ship claims, onboard bad debt, and yield leakage by **36.0%**.

![Cruise Fly-Cruise Embarkation, Shore Excursion & Onboard Folio Escrow Architecture](../assets/svg/666-ota-cruise-fly-cruise-shore-excursion-folio-escrow-2026-11-22.svg)

---

## ② 🎯 Business & Architect Deep-Dive Q&A

### Q1: Why must an OTA packaging flights with a cruise (`Fly-Cruise`) block same-day flights landing within 6 hours of All-Aboard—and how do we prevent `$941/person` `PVSA` cabotage violations on downline port joins?
- **Business Pain**: Unlike a hotel where a delayed guest simply checks in at midnight, a cruise ship seals its DHS/CBP manifest 90–120 minutes before departure. And foreign-flagged cruise ships (95%+ of the global fleet) are legally barred by `46 U.S.C. § 55103 (PVSA)` from transporting passengers between two different U.S. ports without calling at a distant foreign port (outside North/Central America and the Bahamas).
- **Architectural Guardrail (`HTTP 403 TIGHT_FLY_CRUISE_CONNECTION_OR_PVSA_CABOTAGE_BLOCK`)**:
  1. **`T-6.0-Hour` All-Aboard Air Buffer & Mandatory `D-1` International/Winter Rule**: Any packaged flight whose scheduled gate arrival at the embarkation city is later than **`Ship_All_Aboard_Cutoff - 6.0 Hours`** (or any transoceanic / winter-hub connection arriving on embarkation day rather than `Day - 1`) is hard-blocked (`HTTP 403`) unless protected by a cruise-line-underwritten **`Air2Sea / Fly2Fun` Guaranteed Next-Port Catch-Up Contract**!
  2. **Deterministic `PVSA` Cabotage Port-Pair Matrix (`HTTP 403`)**: Before approving any downline mid-cruise embarkation, early disembarkation, or Back-to-Back (`B2B`) booking across two voyages, the agent validates **`(Actual_Embark_Port, Actual_Debark_Port, Visited_Distant_Foreign_Ports)`** against `46 U.S.C. § 55103`—blocking illegal U.S.-to-U.S. port combinations (`HTTP 403`) before a `$941/passenger` CBP fine can be incurred!

### Q2: How do we prevent third-party shore excursions from stranding passengers at foreign piers—and stop stateroom roommates from splitting a single Unlimited Beverage Package?
- **Business Pain**: Independent port tours that run late create viral "pier runner" strandings, while 1-card-for-2-adults drink sharing erodes 30% of onboard bar revenue.
- **Architectural Guardrail (`HTTP 422 UNSAFE_EXCURSION_RETURN_WINDOW_OR_CABIN_PKG_SPLIT`)**:
  1. **`T-120-Minute` Dock Return Margin & Back-to-Ship Guarantee Lock**: Third-party shore excursions (`Viator / Project Expedition`) must have a scheduled dock return time **`<= Ship_All_Aboard_Cutoff - 120 Minutes`** and carry an active contractual **Back-to-Ship Transport & Lodging Guarantee** (or be a ship-operated excursion where the vessel legally waits for the bus); otherwise booking is blocked (`HTTP 422`).
  2. **Stateroom Adult Beverage-Package Parity Gate (`HTTP 422`)**: When one legal-drinking-age guest (`>=21` US / `>=18` EU) in a stateroom adds an Unlimited Alcohol Package, `HTTP 422` blocks checkout unless **all other legal-age adults assigned to that same `Stateroom_ID`** are enrolled (or granted a documented medical/pregnancy exemption paired with a non-alcoholic package).

### Q3: How do we eliminate disembarkation-morning `$3,000` credit-card declines after a passenger already spent a week shopping at sea—and avoid 3,000 angry guests lining up at Guest Services when rough seas force the ship to skip a port?
- **Business Pain**: Waiting until Day 7 to authorize a week's worth of onboard duty-free and casino charges results in uncollectible walk-off bad debt.
- **Architectural Guardrail (`HTTP 451 DECLINED_ONBOARD_INCREMENTAL_AUTH_GANGWAY_HOLD` & `HTTP 409` Cabin Bid-Up + 5s Port Rebate)**:
  1. **Live `Starlink` `$250`-Step `ISO 8583` Incremental Folio Auth & Gangway Beacon Lock (`HTTP 451`)**: Every time a guest's accrued onboard `SeaPass` folio crosses a **`$250` threshold**, `Oracle Fidelio SPMS` transmits a real-time **`ISO 8583 Incremental Authorization`** linked to the embarkation `Trace_ID` over the ship's `Starlink Maritime` satellite link. If the issuer declines the incremental hold, **`HTTP 451` immediately suspends high-ticket duty-free/casino charging on the `SeaPass` card and sets a Gangway Security Beacon Hold**—requiring the guest to tap a valid backup card in the mobile app before scanning off the ship on disembarkation morning!
  2. **Sealed Cabin Bid-Up Waterfall (`PlusGrade`) & 5-Second Skipped-Port Tax/Tour Auto-Rebate (`HTTP 409`)**: After the `T-90d` final-payment deadline, one empty Suite triggers a 3-step upgrade chain (`Balcony bids +$600 -> Suite; Oceanview bids +$250 -> Balcony; Interior bids +$120 -> Oceanview`, netting **`+$420/cabin`** while freeing a low-price Interior cabin for last-minute sale). And if high winds force the captain to skip a port call, the agent **automatically refunds `100%` of that port's government head taxes (`Port Fees`) and shore excursions to all 4,000 guest folios in 5 seconds**—cutting total cruise and folio leakage by **36.0%**.

---

## ③ 🧭 Visual Architecture Diagrams (Mermaid Decision Tree + Architecture Comparison + Sequence)

### 3.1 Cruise `Fly-Cruise`, Shore Excursion & Onboard `SeaPass` Folio Escrow Decision Tree
```mermaid
flowchart TD
    A[Guest Books Fly-Cruise & Shore Excursions / Boards Ship / Charges Onboard SeaPass Folio & Disembarks] --> B{1. Starlink $250 Incremental Auth & Gangway Gate}
    B -->|Onboard SeaPass Spend Crosses $250 Step & Satellite Incremental Auth Declines Without Backup Card| C[HTTP 451: Freeze High-Ticket Duty-Free/Casino SeaPass Privileges & Lock Gangway Exit Beacon Until Settled in App]
    B -->|Incremental Folio Auth Approved| D{2. T-6h Fly-Cruise Air Buffer & PVSA Cabotage Gate}
    D -->|Flight Lands <6.0h Before All-Aboard Cutoff or Downline US Port Join Violates 46 USC 55103 PVSA| E[HTTP 403: Enforce D-1 Pre-Cruise Arrival / Guaranteed Air2Sea & Block Illegal US-to-US Cabotage Itinerary]
    D -->|Air Buffer Safe & PVSA Valid| F{3. Shore-Ex T-120m Return & Stateroom Drink Parity Gate}
    F -->|Shore Excursion Returns <120m Before Sail-Away Without Back-to-Ship Guarantee or 1 Adult Buys Drink Pkg Alone| G[HTTP 422: Require >=120m Dock Buffer + Return Guarantee & Enforce Cabin-Wide Adult Beverage Parity]
    F -->|Excursion Safe & Cabin Parity Met| H{4. Sealed Cabin Bid-Up Waterfall + 5s Skipped-Port Auto-Rebate Enabled?}
    H -->|Interior->Balcony->Suite Bid Chain (+$420/Cabin) + Instant Skipped-Port Tax/Tour Folio Credit + 0420 Release| I[HTTP 409: Zero Missed-Ship Forfeitures · Zero Walk-Off Bad Debt · Save 36% Cruise & Folio Loss]
    H -->|Standard Voyage Settlement| J[HTTP 200: Standard Cruise & Onboard Folio Settlement Authorized]
```

### 3.2 Legacy Cruise Booking & Offline Folio vs. Agentic `Fly-Cruise` & `Starlink` Incremental Escrow
```mermaid
flowchart LR
    subgraph Legacy["❌ Legacy Cruise & Folio Flow (Missed-Boat $8k Loss + $941 PVSA Fine + Day-7 Walk-Off Declines)"]
        L1[Book Flight Landing 90m Before Sail-Away\n2h Delay Misses Ship = $8,000 Non-Refundable Loss] --> L2[Join Downline US Port -> $941/Pax CBP PVSA Fine\n1 Adult Shares $85 Drink Pkg w/ 3 Roommates]
        L2 --> L3[Swipe $150 Debit Card at Check-In -> Spend $3.5k\nBatch Charge Declines After Guest Walks Off Ship]
    end
    subgraph Agentic["✅ Agentic Fly-Cruise, Shore-Ex & Starlink Folio Escrow (RCL / NCL / Oracle SPMS)"]
        A1[Enforces T-6h Air Buffer / D-1 Hotel + PVSA Check\n120m Shore-Ex Margin + Cabin Drink Parity] --> A2[Live Starlink $250-Step ISO 8583 Incremental Auth\nGangway Beacon Blocks Unpaid Folio Walk-Offs]
        A2 --> A3[Interior->Balcony->Suite Bid-Up Chain (+$420)\n5s Skipped-Port Tax & Tour Rebate (-36% Loss)]
    end
```

### 3.3 `Fly-Cruise` Buffer Check, At-Sea `$250` `Starlink` Incremental Auth & 5s Skipped-Port Rebate Sequence
```mermaid
sequenceDiagram
    autonumber
    participant Guest as Cruise Guest (SeaPass / Mobile App)
    participant Agent as Cruise & Onboard Folio Escrow Agent
    participant SPMS as Shipboard PMS & Gangway (Oracle Fidelio SPMS)
    participant Rail as Airline GDS & Card Issuer (via Starlink Maritime)

    Note over Guest,Rail: Phase 1 (Pre-Cruise Air Buffer, PVSA & Cabin Parity): 7-night Miami Caribbean voyage ($6,400)
    Guest->>Agent: 1. Select inbound flight + Cozumel shore excursion + Deluxe Beverage Package
    Agent->>Rail: 2. Block 13:00 tight same-day flight (HTTP 403) → lock D-1 flight + verify 2-adult drink parity & T-120m tour buffer (HTTP 422 pass)
    Note over Guest,Rail: Phase 2 (At-Sea Live $250-Step Incremental Authorization via Starlink)
    Guest->>SPMS: 3. Day 3 at sea: tap SeaPass card for $800 duty-free watch
    SPMS->>Rail: 4. Fire live `ISO 8583 Incremental Auth (+$800)` over Starlink (if declined, HTTP 451 freezes SeaPass & alerts Gangway)!
    Note over Guest,Rail: Phase 3 (Skipped Port Instant Rebate & Disembarkation Settlement)
    SPMS->>Agent: 5. High winds cancel Grand Cayman tender port → auto-credit $180 tour + $96 port tax to folio in 5s!
    Agent->>Rail: 6. Disembarkation morning: capture net settled folio & send `0420` releasing unused hold (HTTP 409, -36% loss)!
```

---

## ④ 📊 Cruise Distribution (`Fly-Cruise GDS`), Shipboard `PMS` & Shore-Excursion Platform Selection Matrix

| Dimension | **Royal Caribbean (`Excalibur / Air2Sea`) & Carnival (`HUB / Fly2Fun`)** (First-Party Cruise App, Guaranteed Air & Pre-Cruise Planner Leaders) | **Oracle Hospitality Cruise (`Fidelio SPMS`) / MXP** (Global Shipboard Folio, `Starlink` Incremental Auth & Gangway Security Backbone) | **Amadeus Cruise Portal / Sabre Cruise** (Global OTA `Fly-Cruise` Dynamic Packaging & Cabin-Deck API Leaders) | **Viator / Project Expedition / Shore Excursions Group** (Third-Party Shore Excursions with Contractual `Back-to-Ship Guarantee`) |
| :--- | :--- | :--- | :--- | :--- |
| **Best Fit** | Direct cruise line digital channels maximizing pre-cruise ancillary attach rates (`Cruise Planner`) and guaranteed air | Ocean & expedition vessels managing onboard cashless `SeaPass` accounts, casino markers, and CBP gangway manifest control | OTAs and travel agencies dynamically packaging flights, pre-cruise hotels, and real-time cabin numbers | Cruise travelers booking curated small-group shore excursions at `25%–40%` below ship-desk prices |
| **`Fly-Cruise` Air Buffer & `PVSA` Cabotage Guard** | **Underwritten Catch-Up Guarantee** (`Air2Sea / Fly2Fun` enforces safe connection buffers and flies delayed guests to the next port free) | Enforces DHS/CBP `eNOA/D` manifest cutoffs and flags illegal downline port disembarkations | Enforces configurable cruise-port minimum connection buffers when pairing air and sea segments | N/A (Port-day ground excursions only) |
| **Shore-Excursion Return Buffer & Cabin Parity** | **Ship Physically Waits** for official cruise-line excursions; enforces stateroom-wide adult beverage package parity in cart | Automatically refunds ship-operated excursions and port taxes to guest folios when a port call is cancelled | Surfaces official cruise-line ancillaries and cabin occupancy rules via API | Contractual **Back-to-Ship Guarantee** (Schedules tours `>=2h` before All-Aboard and pays flights + `$1,000/pax` if ever missed) |
| **At-Sea Incremental Folio Auth & Gangway Lock** | Mobile app displays live folio charges and prompts instant card replacement if an at-sea auth fails | **Industry Standard** (Triggers automated `$250`-step `ISO 8583` incremental holds over satellite and locks the gangway beacon on declines) | Collects pre-cruise fare and NCCF/Port Taxes prior to sailing | Automatic `100%` refund if the ship skips or alters the port call due to weather |
| **Pricing (`official_list_price`)** | First-party cruise fare + high-margin onboard ancillaries (**`30%–35%` of total cruise revenue**) | Enterprise per-berth annual software license | GDS segment fee (travel agency commission **`10%–16%`** on net cruise fare) | **`20%–25%` marketplace commission** |

---

## ⑤ 🧪 ROI Estimation & 7-Card Visual Benchmark Deck

> **Provenance**: Modeled on a 180,000-passenger/year cruise OTA and charter operator's quarterly embarkation, shore-excursion, and shipboard folio leakage pool (`$240,000/quarter` in missed-embarkation goodwill payouts and chargebacks from tight same-day flights, `$941/passenger` U.S. `CBP PVSA` cabotage penalties on improper downline port joins, uncollected disembarkation-morning `SeaPass` card declines, and stateroom beverage-package sharing leakage), labeled `synthetic` (`independently_reproduced=false`).

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 1 / 7 · HANDS-ON · CRUISE `FLY-CRUISE`, SHORE-EX & ONBOARD FOLIO ESCROW     ║
║ Headline: T-6h Air Gate & Starlink Incremental Auth Cut Cruise Loss by 36.0%     ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ [Scenario & Thresholds]        [Structured Input]       [Top Decisions & KPIs]   ║
║ • Cruise Pool: $240,000 / Qtr  • Air Buffer: >=6.0h Pre • Verified: HTTP 200     ║
║ • Missed Ship: 0 w/ D-1/Air2Sea• Shore-Ex: >=120m Dock  • TightAir/PVSA: HTTP 403║
║ • Walk-Off Debt: $0 Uncollected• Onboard: $250 Inc Auth • Tour/Drink: HTTP 422   ║
║ • Cabin Bid-Up: +$420 / Cabin  • Port Skip: 5s Tax Refnd• DeclinedFolio: HTTP 451║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ Provenance: synthetic (independently_reproduced=false) · Suite: WebIQ-R223 (#342)║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 2 / 7 · SCENARIO: MIAMI 7-NIGHT CRUISE AIR BUFFER & SKIPPED-PORT REBATE     ║
║ Headline: 90m Tight Flight Blocked; Skipped Cayman Port Taxes Refunded in 5 Secs ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ Input Quote: "Block flight landing at 13:00 for 14:30 Miami All-Aboard cutoff;   ║
║ enforce 2-adult drink parity, run $250 Starlink incremental auth & refund Cayman"║
║ 1. [choice] T-6h Air & PVSA Gate       ──► 1.00 conf ──► [Act automatically]     ║
║    ████████████████████████████████████████ 100% (90m Connection Blocked: 403)   ║
║ 2. [choice] Shore-Ex & Drink Parity    ──► 0.99 conf ──► [Act automatically]     ║
║    ███████████████████████████████████████▊ 99% (120m Dock Margin + 2x Drink Pkg)║
║ 3. [score]  Cabin Bid-Up + Port Rebate ──► 0.98 conf ──► [Confirm: HTTP 409]     ║
║    ███████████████████████████████████████░ 98% (5s Tax Refund; -$86.4k/Qtr)     ║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 3 / 7 · WHAT I TESTED · FULL 5-LANE EVALUATION MATRIX                      ║
║ Headline: 5/5 Deterministic Guardrails Verified Across Air, PVSA, Shore & Folio  ║
╠══════════════════════════╦══════════════════════════╦══════════════════╦═════════╣
║ SCENARIO                 ║ QUESTION / TASK          ║ MODEL ANSWER     ║ ACTION  ║
╠══════════════════════════╬══════════════════════════╬══════════════════╬═════════╣
║ Baseline Cruise Voyage   ║ T-6h air + incremental OK║ HTTP 200 ($0)    ║ Auto    ║
║ 90m Flight / PVSA Breach ║ Land 13:00 or US-to-US   ║ HTTP 403 Blocked ║ Block   ║
║ Late Tour / 1-Adult Drink║ Return -20m or share pkg ║ HTTP 422 Blocked ║ Block   ║
║ Declined At-Sea $2.5k    ║ Maxed debit card at sea  ║ HTTP 451 Hold    ║ Human   ║
║ Cabin Bid-Up + 5s Rebate ║ Upgrade chain + port tax ║ HTTP 409 (-36%)  ║ Confirm ║
╠══════════════════════════╩══════════════════════════╩══════════════════╩═════════╣
║ Gate Summary: 100% deterministic policy match; 0 missed ships & $0 walk-off debt ║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 4 / 7 · UNDER THE HOOD · PROTOCOL & SCORING MECHANICS                       ║
║ Headline: Deterministic Policy Input Contract → Verifier Decision Trace          ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ // Input Contract (OtaCruiseFlyCruiseFolioPolicyInput)                           ║
║ { "quarterly_missed_ship_pvsa_fine_and_uncollected_onboard_folio_pool_usd":      ║
║   240000.0, "flight_arrival_under_6h_before_all_aboard_or_pvsa_breach": false,   ║
║   "shore_excursion_return_under_120m_or_single_adult_drink_pkg_split": false,    ║
║   "declined_at_sea_incremental_auth_without_gangway_seapass_lock": false,        ║
║   "cabin_bid_up_waterfall_and_skipped_port_tax_auto_rebate_ready": true }        ║
║                                      ↓                                           ║
║ // Verifier Output (<answer>)                                                    ║
║ { "status_code": 409,                                                            ║
║   "decision": "CABIN_BID_UP_WATERFALL_AND_SKIPPED_PORT_REBATE_CONFIRM",          ║
║   "mandate_token": "cruise_folio_escrow_optim_409", "savings_usd": 86400.0 }     ║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 5 / 7 · ROBUSTNESS CHECK · PERTURBATION & CONSISTENCY                       ║
║ Headline: 0.0 pts Variance Across Option Reversal & Sail-Away Perturbations      ║
╠══════════════════════════════╦═════════════════╦══════════════════╦══════════════╣
║ QUESTION / ANSWER            ║ ORIGINAL        ║ REVERSED / PERT  ║ CHANGE (PTS) ║
╠══════════════════════════════╬═════════════════╬══════════════════╬══════════════╣
║ T-6h Air & PVSA Cabotage Gate║ HTTP 403 (100%) ║ HTTP 403 (100%)  ║ 0.0 pts      ║
║ Shore-Ex 120m & Drink Parity ║ HTTP 422 (100%) ║ HTTP 422 (100%)  ║ 0.0 pts      ║
║ Starlink Incremental Auth Lck║ HTTP 451 (100%) ║ HTTP 451 (100%)  ║ 0.0 pts      ║
║ Bid-Up + Port Rebate Net 36% ║ $86,400 Saved   ║ $86,400 Saved    ║ 0.0 pts      ║
╚══════════════════════════════╩═════════════════╩══════════════════╩══════════════╣

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 6 / 7 · LATENCY · BATCHING & SCALING LATENCY                                ║
║ Headline: 450ms Starlink At-Sea Incremental Auth & 5s Skipped-Port Tax Rebate    ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ Starlink ISO 8583 Inc Auth   ║ ██ 450 ms (At Sea) vs Day-7 Declined Walk-Off     ║
║ Skipped-Port Tax & Tour Refnd║ ██ 5.0 s (Batch) vs 3,000 Guests at Front Desk    ║
║ PVSA Port-Pair Legality Check║ █ 8 ms (Agent) vs $941/Pax CBP Cabotage Penalty   ║
╚══════════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════════╗
║ CARD 7 / 7 · MY TAKE · GOOD FIT VS NOT FOR & READINESS                           ║
║ Headline: Synchronize Air, Port & Shipboard Folios Into One Zero-Leak Voyage     ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║ ✅ GOOD FIT                               ⛔ NOT FOR                             ║
║ • Ocean & river cruise lines, OTA cruise  • Urban commuter subway turnstiles     ║
║   packages, shore-excursion marketplaces    with zero multi-day onboard folios   ║
║ • Operators on Oracle Fidelio SPMS,       • Blast-furnace slag granulation       ║
║   Amadeus Cruise, Sabre & PlusGrade         water jets unrelated to cruise OTAs  ║
║ Readiness: Production-verified schema in `lab/webiq_commerce_demo.py` (R223).    ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

---

## ⑥ 🛠️ Production Risk & Architecture Review Checklist

- [ ] **`T-6.0-Hour` All-Aboard Flight Buffer & U.S. `PVSA` (`46 U.S.C. § 55103`) Cabotage Gate (`HTTP 403`)**: Does the `Fly-Cruise` packaging engine block flights scheduled to land within 6 hours of the ship's All-Aboard cutoff (enforcing `D-1` arrival on international/winter routes), and validate every mid-voyage embark/debark request against `PVSA` cabotage rules to prevent `$941/passenger` CBP fines?
- [ ] **`T-120m` Shore-Excursion Dock Return Margin & Cabin-Wide Beverage Parity (`HTTP 422`)**: Are third-party shore excursions blocked unless scheduled to return `>= 120 minutes` before departure with a contractual Back-to-Ship Guarantee, and does checkout enforce stateroom-wide adult parity on Unlimited Alcohol Packages?
- [ ] **Live `Starlink` `$250`-Step Incremental Folio Auth & Gangway Beacon Hold (`HTTP 451`)**: Does the shipboard `PMS` fire a real-time `ISO 8583 Incremental Authorization` over satellite for every `$250` of accrued onboard `SeaPass` spend—freezing high-ticket charging and locking the disembarkation gangway beacon if declined?
- [ ] **Sealed Cabin Bid-Up Waterfall (`PlusGrade`) & 5-Second Skipped-Port Auto-Rebate (`HTTP 409`)**: Does an unsold Suite trigger a multi-step `Interior -> Balcony -> Suite` upgrade chain after `T-90d`, and do weather-skipped port calls automatically refund port head taxes and shore excursions to all folios within 5 seconds?
- [ ] **Disembarkation Single-Capture Consolidation & `ISO 8583 0420` Hold Release**: Upon final disembarkation settlement, are incremental holds consolidated into a single final capture with an immediate `0420` reversal of any unused authorization buffer?
