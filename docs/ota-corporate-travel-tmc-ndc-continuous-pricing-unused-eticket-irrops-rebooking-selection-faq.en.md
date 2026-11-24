# 🏆 OTA Corporate Travel Management (`TMC`), `IATA NDC 21.3` Continuous Pricing, `Hold-Before-Cancel` Price-Drop Re-Shopping & `Unused e-Ticket (UET)` Credit Bank (`Navan / TravelPerk / SAP Concur / Amadeus Cytric` · 🏆 Round 330 Milestone) FAQ

> **Executive Summary (🏆 Round 330 Research Milestone)**: In enterprise Corporate Travel Management (`TMC`) and autonomous flight/hotel rebooking, legacy architectures built solely on `EDIFACT GDS` channels and fire-and-forget ticketing lose `15%–25%` of travel budgets across three structural gaps: (1) **`EDIFACT GDS` Distribution Surcharges (`$18–$28/segment`) & Missing `IATA NDC 21.3` Continuous Pricing**: Major carriers (`American`, `United`, `Lufthansa`, `British Airways`, `Air France-KLM`) withhold up to `30%+` of their lowest fares and dynamic inter-RBD continuous price points from legacy `EDIFACT` pipes while levying hefty GDS surcharges; (2) **"Cancel-Before-Hold" Price-Drop Re-Shopping Race Conditions**: Automated re-shopping scripts that cancel an existing `$680` flight or `$380/night` hotel *before* securing the new `$560` offer risk losing the last seat/room in a 200ms race condition—stranding executives without a reservation—or rebooking when change fees exceed the fare drop; and (3) **Orphaned `Unused e-Ticket (UET)` Credits from Cancelled Trips & Departed Employees**: Allowing `8%–12%` of annual air spend (`13-digit IATA ticket credits`) to sit trapped under individual employee names until they expire after 12 months while colleagues pay fresh cash on the same airline.  
> Production architectures must enforce **Federated `IATA NDC 21.3 + GDS` Corporate `TourCode` Shopping + Atomic `Hold-Before-Cancel` Price-Drop Re-Shopping (`Net_Savings >= $25`) + Centralized Corporate `UET Credit Bank` (`FIFO` Name-Change Waiver Redemption)**: cutting corporate travel overpayments, re-shopping errors, and expired ticket write-offs by **38%** (reducing a `$390,000` quarterly leakage pool to `$241,800`, saving **`$148,200/quarter`**).

![OTA Corporate Travel, NDC Continuous Pricing & Auto-Rebooking Architecture](../assets/svg/773-ota-corporate-travel-tmc-ndc-continuous-pricing-unused-eticket-2026-11-24.svg)

---

## 1. Solution Architect Deep-Dive Q&A

### Q1: Why do legacy corporate booking tools show fares `$50–$95` higher than airline websites, and how do we safely automate post-booking price-drop re-shopping?
- **Architectural Solution (`IATA NDC 21.3` Surcharge-Avoidance Gate `HTTP 403` + Atomic `Hold-Before-Cancel` Re-Shopping Saga Gate `HTTP 422`)**:
  - Query `IATA NDC 21.3` direct/aggregated pipes (`Navan / Travelfusion / Amadeus NDC-X`) alongside GDS with the enterprise's `Corporate_TourCode / SnapCode` injected, and hard-block booking a legacy `EDIFACT GDS` fare carrying a distribution surcharge when an equivalent or lower `NDC Continuous Price` offer is available (`HTTP 403 LEGACY_GDS_SURCHARGE_OVERPAY_OR_MISSING_NDC_CORPORATE_CONTINUOUS_FARE`);
  - Enforce a strict **Two-Phase `Hold-Before-Cancel` Saga** for post-booking price-drop re-shopping: verify `Net_Savings = Old_Fare - New_Fare - Change_Fee - Perk_Delta >= $25.00` and confirm the new `NDC OrderID / Hotel PNR` (preserving seat/bed preferences) *before* issuing a `Cancel` on the original booking (`HTTP 422 CANCEL_BEFORE_HOLD_REShop_RACE_OR_NEGATIVE_NET_REBOOKING_SAVINGS`).

### Q2: How do we prevent cancelled airline tickets from expiring in departed employees' profiles?
- **Architectural Solution (Centralized Corporate `Unused e-Ticket (UET)` Credit Bank & Name-Waiver Gate `HTTP 451 / 409`)**:
  - Sweep every cancelled `13-digit` e-ticket (`016-...`, `006-...`, `125-...`) into a company-wide **`UET Credit Bank`** synced with HR offboarding (`Workday / BambooHR`). Before charging fresh virtual-card funds on a carrier, automatically match expiring `UET` credits (`FIFO` by expiration date) and invoke the airline's **Corporate Name-Change Waiver API** to transfer and apply the credit to the new traveler (`HTTP 451 ORPHANED_UNUSED_ETICKET_CREDIT_BYPASS_ON_ELIGIBLE_AIRLINE_BOOKING`; verified `NDC` continuous fare selection, `Hold-Before-Cancel` re-shopping, and `UET` pool redemption return `HTTP 409 NDC_CONTINUOUS_FARE_HOLD_BEFORE_CANCEL_RESHOP_AND_UET_BANK_CONFIRM`).

---

## 2. Visual Architecture Diagrams (Mermaid)

### 1. Corporate Travel `NDC 21.3`, `Hold-Before-Cancel` Re-Shopping & `UET Credit Bank` Decision Tree
```mermaid
flowchart TD
    A[Corporate Flight/Hotel Booking, Price-Drop Re-Shop & Ticket Settlement] --> B{Was the Corporate Unused e-Ticket (UET) Credit Bank<br/>Checked & Applied via FIFO Name-Waiver Before Card Charge?}
    B -- Charging $910 Fresh Card Funds While $820 Expiring United UET Sits Idle --> C[HTTP 451 Block: Invoke Corporate Name-Change Waiver & Redeem UET Credit First]
    B -- UET Pool Checked & Applied --> D{If Price-Drop Re-Shopping: Is New PNR Held First<br/>with Net Savings >= $25 After Change Fees?}
    D -- Cancelling Old Booking Before Holding New PNR or Net Savings < $25 --> E[HTTP 422 Block: Enforce Hold-Before-Cancel Two-Phase Lock & $25 Net Floor]
    D -- Re-Shop Atomicity Verified --> F{Did Shopping Compare IATA NDC 21.3 Continuous Fares<br/>with Corporate TourCode Against Surcharged EDIFACT GDS?}
    F -- Booking Legacy GDS Fare with $48 Surcharge Over Lower NDC Offer --> G[HTTP 403 Block: Route to Direct IATA NDC 21.3 Corporate Continuous Offer]
    F -- All Travel Fiduciary Gates Passed --> H[HTTP 409 Confirm: NDC Continuous + Safe Re-Shop + UET Bank Saves 38%]
```

---

## 3. Platform Selection Matrix (`Navan vs. TravelPerk vs. SAP Concur`)

| Dimension | Navan (formerly TripActions) | TravelPerk | SAP Concur + Legacy TMC | Consumer OTA Self-Booking |
| :--- | :--- | :--- | :--- | :--- |
| **`IATA NDC 21.3` Continuous Fares** | **Native global NDC connections bypassing `$18–$28` GDS surcharges** | **Strong European NDC, Eurostar/Rail & LCC aggregation** | Varies by legacy TMC fulfillment partner | Misses corporate negotiated `TourCodes` |
| **Automated Price-Drop Re-Shopping** | **Built-in `Hold-Before-Cancel` continuous fare/room re-shopper** | `FlexiPerk` instant refundable credits & rate optimization | Often requires `$25–$45` manual agent touch fee | Zero automated post-ticketing re-shopping |
| **`Unused e-Ticket (UET)` Recovery** | **Automated company-wide UET pool & 1-click name-change waiver** | Centralized credit dashboard & auto-redemption | High expiry leakage on departed staff | Credits trapped in personal traveler accounts |

---

## 4. Production Deployment & Risk Checklist

- [ ] **Enable Federated `IATA NDC 21.3 + GDS` Shopping with Injected `Corporate_TourCode`**: Automatically filter out surcharged `EDIFACT` duplicates.
- [ ] **Enforce Atomic `Hold-Before-Cancel` Sagas for All Automated Flight/Hotel Price-Drop Re-Shopping (`Net_Savings >= $25`)**.
- [ ] **Connect HR Offboarding (`Workday / BambooHR`) to a Centralized `13-Digit Unused e-Ticket (UET) Credit Bank`** for `FIFO` cross-employee name-waiver redemption.
- [ ] **Trigger Proactive Tail-Number `IRROPS` Backup Seat Holds (`Delay > 90m`) and Automated Hotel Late-Arrival Notifications**.
