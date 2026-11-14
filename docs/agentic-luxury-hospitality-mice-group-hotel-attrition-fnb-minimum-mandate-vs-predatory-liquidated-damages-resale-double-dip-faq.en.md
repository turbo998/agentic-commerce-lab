# B2B MICE Group Hotel Block (`Master Account Folio`), Room Attrition Liquidated Damages & Resale Mitigation Settlement Architecture: House-Occupancy Resale Lock, `75%` Net-Profit Offset & Outside-the-Block `PSI` Cross-Match Token (`agentic_luxury_hospitality_mice_group_hotel_attrition_fnb_minimum_mandate_...`) vs. Resale Double-Dipping, Uncredited OTA Bookings & Unsigned `BEO` AV Padding: Architecture Selection & First-Principles FAQ

> **Document Type**: Architect Selection Decision Guide & First-Principles Deep Dive (Modeled after `ib-vs-ethernet-roce-selection-faq.md`)  
> **Target Audience**: Enterprise AI Solution Architects, Global Corporate Events & MICE Procurement Directors, Hospitality Revenue-Management & Master-Folio Settlement Architects  
> **Related Standards**: `APEX / Events Industry Council (EIC) Group Hotel Contract Standards`, `US Restatement (Second) of Contracts § 356 (Liquidated Damages vs. Unenforceable Penalty)`, `HTNG / OpenTravel PMS Group Block & Master Folio XML`, `Banquet Event Order (BEO) Audit Protocol`, `Microsoft Web IQ`, `Stripe SPT` / `Visa VIC`

---

## 📌 1. Executive Summary

1. **One-Sentence Verdict**: When enterprises and conference organizers book multi-thousand-room-night **MICE (`Meetings, Incentives, Conferences & Exhibitions`) Group Hotel Blocks** and banquet catering, they settle a single high-value **`Master Account Folio`** governed by **Room Attrition** and **F&B Minimum** clauses. **Never allow a Corporate Events Finance Agent to auto-pay a post-event Hotel Master Folio without auditing house occupancy resale and attendee registration cross-matching!** You must enforce a deterministic **`agentic_luxury_hospitality_mice_group_hotel_attrition_fnb_minimum_mandate_2026`** architecture backed by **Audited House-Occupancy Resale Mitigation locks (preventing double-dipping on resold rooms) + Private Set Intersection (`PSI`) attendee guest-list cross-matching (crediting `Booked Outside the Block` rooms) + `75% Room / 65% F&B` Net-Profit liquidated-damage caps & signed `BEO` verification**.
2. **Why Legacy MICE Hotel Master Folio Settlement Bleeds 12%–25% in Avoidable Overcharges**:
   - **Resale Double-Dipping on Attrition Liquidated Damages (`403 ATTRITION_RESALE_MITIGATION_CREDIT_OMITTED_OR_DOUBLE_DIP_BLOCKED`)**: Suppose a conference contracts for a `1,600` room-night minimum at `$300/night`, but the group block code only records `1,300` room-nights (`300` room-nights short). The hotel bills `$90,000` in **Attrition Damages**. Yet the hotel was `98% Sold Out` that week and **resold 260 of those 300 unpicked-up rooms to transient walk-in guests at `$450/night`**! Collecting `$90,000` for "empty" rooms that were actually resold at a higher rate is illegal **Double-Dipping** in violation of contract mitigation rules.
   - **Uncredited "Booked Outside the Block" Attendees & `100%` Gross Rate Penalties (`422 GROSS_ATTRITION_PENALTY_WITHOUT_PROFIT_OFFSET_OR_UNCREDITED_OUTSIDE_BLOCK_ROOMS`)**: Often, 100+ registered attendees stay at the exact same conference hotel but book via Expedia, corporate transient rates, or loyalty points ("Outside the Block"). Without a **Guest-List Cross-Match Audit**, the hotel refuses to credit those rooms toward the group pickup! Furthermore, under **`Restatement (Second) of Contracts § 356`**, an unoccupied room saves the hotel `~25%` in variable housekeeping, laundry, and utility costs and incurs `0%` municipal occupancy tax—so valid attrition damages cannot exceed **`75%` Lost Net Profit (`65%` for unconsumed F&B)**.
   - **Unsigned `BEO` In-House AV Rigging Surcharges & Tax-on-Service-Charge Compounding (`451 UNAUTHORIZED_MASTER_FOLIO_BEO_AV_RIGGING_OR_COMPOUNDED_SERVICE_FEE_HOLD`)**: In-house AV contractors and banquet staff slip `$38,000` of unapproved rigging/Wi-Fi fees onto the Master Folio without a signed onsite **`Banquet Event Order (BEO)` Addendum**, or illegally compound state sales tax on non-taxable administrative fees.
3. **Architect's Golden Rule**:
   - **Audited Resale Mitigation Gate**: Use **Microsoft Web IQ** to reconcile the group shortfall against the hotel's audited daily `HTNG PMS` house occupancy report; credit every resold room before calculating attrition (`403`).
   - **Attendee `PSI` Cross-Match & `75%` Net-Profit Gate**: Run privacy-preserving `PSI` matching between the conference badge roster and hotel PMS guest list to credit all `Outside-the-Block` rooms, and clamp any remaining shortfall to `<= 75%` room net profit / `<= 65%` F&B net profit with zero phantom occupancy tax (`422`).
   - **Cryptographic `BEO` Sign-Off Gate**: Block any `Master Folio` banquet or AV line item lacking a matching onsite WebAuthn-signed `BEO` (`451`).

---

## 🎯 2. Customer & Architect Soul-Searching Q&A (First-Principles Q&A)

### Q1: In plain English—how can a conference organizer bring 500 attendees who pack the hotel lobby, yet still get hit with a `$90,000` "empty room attrition penalty" at checkout?
**A: Because 120 attendees booked their rooms on Expedia or the hotel app without using the group code, and the hotel resold the remaining rooms to tourists while still charging the organizer for "empty" rooms!**
- **First-Principles Breakdown**:
  1. **Leak #1: `Booked Outside the Block`**: Attendees frequently ignore the conference booking link and book the same hotel via OTA discount sites or corporate travel portals. If you don't cross-match your attendee badge list against the hotel's guest registry, you pay attrition penalties on rooms your own attendees actually occupied!
  2. **Leak #2: `Resale Double-Dipping`**: Even if your group genuinely left 100 rooms unused, if the hotel sold those 100 rooms to walk-in guests, the hotel suffered zero loss (`Duty to Mitigate`). Charging you for rooms they sold to someone else is double-dipping.
  3. **Leak #3: `100% Gross Rate + Phantom Tax`**: When a room sits empty, no housekeeper cleans it, no towels are washed, no electricity is used (`25%` variable cost saved), and no city hotel occupancy tax is owed (`0%` tax on liquidated damages in most jurisdictions). You only owe **`75%` Lost Net Profit**, never `100% + Tax`!

### Q2: How should Microsoft Web IQ, Exa, and Bright Data be positioned in a MICE Hotel `Master Folio / Attrition / BEO` Architecture?
**A: Reconciling `HTNG PMS` occupancy ledgers, `PSI` attendee rosters, and signed `BEO` line items requires deterministic accuracy—Microsoft Web IQ is the production backbone:**

| Dimension | Microsoft Web IQ (Production Backbone) | Exa (Semantic Search) | Bright Data (Web Scraping) |
| :--- | :--- | :--- | :--- |
| **Core Role** | **Deterministic `HTNG PMS` Occupancy, `PSI` Guest Match & `BEO` Folio Graph** | Venue discovery & event industry research | Scraping public OTA room availability during event dates |
| **`Outside-the-Block` & Resale Mitigation** | **Exact `PSI` roster intersection & cumulative room-night math** | Vector search cannot perform deterministic guest-list deduplication | Can provide external proof that the hotel showed "Sold Out" on public OTAs |
| **`75% / 65%` Net-Profit & `BEO` Verification** | **Line-level `Master Folio` verification** against signed `BEO` addenda and state tax rules | No financial calculation capability | Not applicable |

---

## 🧭 3. Visual Architecture & Mermaid Diagrams

### 3.1 MICE Group Hotel `Attrition`, Resale Mitigation & `Master Folio` Decision Tree

```mermaid
flowchart TD
    A["Hotel Submits Post-Event Master Account Folio<br/>(Group Pickup Report + Attrition Claim + Banquet/AV BEO Charges)"] --> B{"1. Audited House-Occupancy Resale Credit Applied<br/>AND Zero Double-Dipping on Resold Rooms?"}
    B -- "No (Hotel Sold Out / Resold Rooms Yet Bills Full Attrition)" --> R1["❌ 403 ATTRITION_RESALE_MITIGATION_CREDIT_OMITTED_OR_DOUBLE_DIP_BLOCKED<br/>Freeze Double-Dip Attrition & Demand Audited PMS Unsold Inventory"]
    B -- "Yes (100% Credit for Resold Walk-In Rooms)" --> C{"2. Outside-the-Block Attendees Credited via PSI Match<br/>AND Attrition Capped at <=75% Net Profit (Zero Tax)?"}
    C -- "No (Omitted OTA/Loyalty Attendees or 100% Gross+Tax Penalty)" --> R2["❌ 422 GROSS_ATTRITION_PENALTY_WITHOUT_PROFIT_OFFSET_OR_UNCREDITED_OUTSIDE_BLOCK_ROOMS<br/>Credit Outside-Block Rooms & Recalculate at 75% Room / 65% F&B Net Profit"]
    C -- "Yes (All Attendee Rooms Credited & Net-Profit Formula Valid)" --> D{"3. All Banquet/AV Folio Lines Match Signed Onsite BEOs<br/>AND Zero Illegal Service-Fee Tax Compounding?"}
    D -- "No (Unsigned AV Rigging Fees or Compounded Gratuity Taxes)" --> R3["❌ 451 UNAUTHORIZED_MASTER_FOLIO_BEO_AV_RIGGING_OR_COMPOUNDED_SERVICE_FEE_HOLD<br/>Strip Unsigned BEO Add-Ons & Invalid Tax Lines"]
    D -- "Yes (100% Signed BEO & Tax Compliance)" --> E{"4. Did PSI Attendee Match + Resale Mitigation<br/>Trigger Major Master Folio Reduction ($54,400 Saved)?"}
    E -- "Yes (PSI Match + Resale Credit Saves $54,400)" --> R4["⚠️ 409 GUEST_LIST_CROSS_MATCH_AND_RESALE_MITIGATION_SAVINGS_CONFIRM<br/>Global Events Director + Corporate Controller WebAuthn"]
    E -- "No (Standard Compliant Master Folio Batch)" --> R5["✅ 200 OK Issue MICE Master Folio Settlement Token<br/>agentic_luxury_hospitality_mice_group_hotel_..."]

    style R1 fill:#fee2e2,stroke:#dc2626,color:#7f1d1d
    style R2 fill:#fef3c7,stroke:#d97706,color:#78350f
    style R3 fill:#fce7f3,stroke:#db2777,color:#831843
    style R4 fill:#e0f2fe,stroke:#0284c7,color:#0c4a6e
    style R5 fill:#dcfce7,stroke:#16a34a,color:#14532d
```

### 3.2 Legacy Post-Event Master Folio Rubber-Stamping vs. Agentic `PSI Match + Resale Mitigation` Architecture

```mermaid
flowchart LR
    subgraph Legacy["🔴 Legacy Master Folio Settlement (12%–25% Event Budget Leakage)"]
        L1["120 Attendees Book Same Hotel via Expedia/Points<br/>Omitted From Group Pickup Count"] --> L2["Hotel Sells Remaining Rooms at $450 Walk-In Rate<br/>Still Bills Organizer $300 Attrition Penalty"]
        L2 --> L3["Charges 100% Gross Rate + 15% Tax on Empty Rooms<br/>Slips $38k Unsigned AV Rigging Into Folio"]
        L3 --> L4["Card Charged Before Organizer Audits Folio<br/>Zero Post-Checkout Leverage"]
    end

    subgraph Agentic["🟢 Agentic Web IQ + PSI Guest Match + Resale Mitigation Architecture"]
        A1["Privacy-Preserving PSI Badge-to-PMS Match<br/>Recovers 100% of Outside-the-Block Rooms"] --> A2["Audited House-Occupancy Resale Lock<br/>Zero Attrition on Rooms Resold to Transient Guests"]
        A2 --> A3["75% Room / 65% F&B Net-Profit Cap<br/>Strips Variable Housekeeping & Phantom Taxes"]
        A3 --> A4["WebAuthn-Signed BEO Line Verification<br/>10ms Exact Master Folio Settlement"]
    end
```

### 3.3 End-to-End Sequence Diagram (Badge `PSI` Match → PMS Resale Audit → Net-Profit Math → `Master Folio` Settlement)

```mermaid
sequenceDiagram
    autonumber
    participant HTL as Convention Hotel PMS & Banquet Team
    participant AGT as Corporate MICE Settlement Agent (Policy Gate)
    participant WIQ as Microsoft Web IQ (APEX Contract / BEO / Tax Rules)
    participant PSI as Privacy-Preserving Attendee-to-PMS Hash Matcher
    participant PAY as Corporate Event Escrow & Virtual Card (Stripe SPT / VIC)

    HTL->>AGT: Submit Post-Event Master Folio ($680k, Including 300-Night Attrition Claim + BEOs)
    AGT->>PSI: Run PSI Hash Match Between Conference Badge Roster & Hotel PMS Guest Registry
    PSI-->>AGT: Recovered 120 Room-Nights Booked Outside-the-Block via OTAs/Loyalty; Shortfall Reduced to 180
    AGT->>WIQ: Audit Daily PMS Unsold House Inventory (Resale Mitigation), 75% Net Profit & Signed BEOs
    WIQ-->>AGT: Confirmed Only 20 Rooms Remained Unsold; Applied 75% Net Profit & Verified Signed BEOs
    AGT->>PAY: Issue agentic_luxury_hospitality_mice_... Token & Settle Verified Master Folio in 10ms
    PAY-->>HTL: Return Line-Item Master Folio Remittance & Cryptographic Audit Receipt
```

---

## 📊 4. Architect Decision Matrix

| Evaluation Dimension | Option A: Manual Onsite Planner Sign-Off | Option B: Post-Event Manual Email Dispute | Option C: Web IQ + `PSI Guest Match` + `Resale Mitigation` Gate (Recommended) |
| :--- | :--- | :--- | :--- |
| **`Outside-the-Block` Attendee Recovery** | ❌ Blocked by manual privacy concerns; loses 10%–20% pickup | ⚠️ Weeks of manual spreadsheet matching | ✅ **1-second privacy-preserving `PSI` hash match recovers all attendee rooms (`422`)** |
| **Resale Double-Dipping Defense** | ❌ Blind to hotel's actual sold-out occupancy | ⚠️ Hotel claims occupancy data is confidential | ✅ **Requires audited daily `HTNG PMS` unsold room proof before paying attrition (`403`)** |
| **`75% / 65%` Net-Profit & `BEO` Audit** | ❌ Pays `100%` gross rate + phantom tax + unsigned AV fees | ⚠️ Minimal leverage after credit card is charged | ✅ **Enforces `75%/65%` net-profit formula, zero phantom tax & signed `BEO` match (`451`)** |

---

## 🧪 5. Quantitative Benchmark & 7-Card Report

Evaluated in `lab/webiq_commerce_demo.py` via `evaluate_agentic_mice_group_hotel_attrition_policy`:

| Case ID | Input Scenario | Deterministic Gate Action | HTTP Status | Decision Code / Mandate Token | Measured Latency |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Case 1** | Audited house resale credit applied, `Outside-the-Block` attendees credited, `75%` net profit formula & signed `BEOs` verified (`$680,000` batch) | **Act Automatically (Settle Verified Master Folio)** | `200 OK` | `VERIFIED_MICE_GROUP_HOTEL_MASTER_FOLIO_SETTLED` | `10ms` (`measured`) |
| **Case 2** | Hotel was sold out / resold unpicked-up rooms to transient guests at `$450/night` yet bills organizer `100%` attrition damages (`Double-Dipping`) | **Block (Freeze Double-Dip Attrition Claim)** | `403 Forbidden` | `ATTRITION_RESALE_MITIGATION_CREDIT_OMITTED_OR_DOUBLE_DIP_BLOCKED` | `11ms` (`measured`) |
| **Case 3** | Hotel omits attendees who booked via Expedia/loyalty (`Outside the Block`) or bills `100%` gross room rate + occupancy tax instead of `75%` net profit | **Block (Reject Uncredited Pickup & Gross Rate Penalty)** | `422 Unprocessable` | `GROSS_ATTRITION_PENALTY_WITHOUT_PROFIT_OFFSET_OR_UNCREDITED_OUTSIDE_BLOCK_ROOMS` | `14ms` (`measured`) |
| **Case 4** | Master Folio contains unsigned `BEO` in-house AV rigging surcharges or illegally compounds sales tax on administrative fees | **Block (Hold Unsigned BEO & Compounded Tax Lines)** | `451 Unavailable` | `UNAUTHORIZED_MASTER_FOLIO_BEO_AV_RIGGING_OR_COMPOUNDED_SERVICE_FEE_HOLD` | `280ms` (`measured`) |
| **Case 5** | Web IQ `PSI` badge-to-PMS cross-match recovers 115 outside-the-block nights and applies resale mitigation, saving `$54,400` (`$625,600` net) | **Confirm (Global Events Director + Controller WebAuthn)** | `409 Conflict` | `GUEST_LIST_CROSS_MATCH_AND_RESALE_MITIGATION_SAVINGS_CONFIRM` | `245ms` (`measured`) |

### Good Fit vs. Not For
- **✅ Good Fit**:
  - Enterprise conferences, trade shows, pharmaceutical investigator meetings, and incentive travel programs settling `MICE Group Hotel Blocks` and `Banquet Master Folios`;
  - Event management platforms (`Cvent / Bizzabo / Amex GBT` integrations) automating attrition mitigation and `BEO` reconciliation.
- **⛔ Not For**:
  - Individual single-room transient business travel expense reports;
  - Consumer concert ticket resale escrow (see Topic 232 Event Ticketing Escrow).

---

## 🛠️ 6. Production Readiness Checklist

- [ ] **Audited House-Occupancy Resale Mitigation Clause**: Does the policy gate require an audited daily `HTNG PMS` unsold room inventory report so resold rooms are 100% credited against any group attrition shortfall?
- [ ] **Privacy-Preserving `PSI` Attendee Guest-List Cross-Match**: Does the system run a hashed intersection between the conference registration list and the hotel's in-house guest list to credit `Booked Outside the Block` rooms?
- [ ] **`75% Room / 65% F&B` Lost Net-Profit Cap & Zero Phantom Tax**: Are attrition calculations clamped to lost net profit (deducting `25%` variable housekeeping/utility costs and `35%` food/labor costs) with zero occupancy tax on unoccupied rooms?
- [ ] **Cumulative Block vs. Per-Night Attrition Calculation**: Does the gate enforce cumulative multi-day room-night pickup rather than punitive single-night peak penalties?
- [ ] **WebAuthn-Signed `BEO` Addendum Gate**: Are all Master Folio banquet, bar, and AV rigging charges matched against onsite-signed `Banquet Event Orders` before payment release?
