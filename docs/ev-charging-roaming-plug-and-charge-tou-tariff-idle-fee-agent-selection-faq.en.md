# EV Supercharging Roaming (`OCPI`), `ISO 15118 Plug & Charge`, Dynamic TOU Tariff & Congestion Idle-Fee Agent Architecture FAQ: Anti-Quishing QR Guard, SoC-Bounded Pre-Auth & Peak-Shaving Optimization

> **Topic Positioning (EV Fast-Charging Networks `Tesla Supercharger / ChargePoint / NIO Power / Electrify America`, Commercial Fleet Mobility & `OCPI` Roaming Settlement Agent Focus · Round 430)**: Written for **Cloud & AI Solution Architects** building in-vehicle charging assistants, Charge Point Operator (`CPO`) billing engines, and e-Mobility Service Provider (`eMSP`) roaming hubs. This guide solves four critical EV charging commerce failures: **how scammers paste counterfeit static QR stickers over public EV chargers ("Quishing") to steal driver card credentials (`HTTP 403`), why locking a flat `$75.00` credit-card pre-authorization hold for a `$10.10` top-up infuriates drivers when SoC-bounded `capture_method="manual"` holds can release unused funds instantly (`HTTP 422`), why charging a `$1.00/min` Congestion Idle Fee at 2:00 AM when the station is `80%` empty (or within a 5-minute grace window) triggers mass chargebacks (`HTTP 422`), and how to route commercial fleets across Time-of-Use (`TOU`) off-peak windows and live grid-curtailment alerts via Web IQ (`HTTP 451 / 409`)**.  
> **Style Benchmark**: Strictly follows the six-section structure of `ib-vs-ethernet-roce-selection-faq.md` (Executive Summary, Architect Q&A, Mermaid Decision Tree / Architecture Comparison / Sequence Diagram, EV Charging & Roaming Architecture Decision Matrix, Quantitative Fleet-Savings/Dispute Evaluation & 7-Card Provenance Table, and Production Risk Checklist).  
> **Bilingual Editions**: **[English Version (Current)](ev-charging-roaming-plug-and-charge-tou-tariff-idle-fee-agent-selection-faq.en.md)** · **[中文版 (`ev-charging-roaming-plug-and-charge-tou-tariff-idle-fee-agent-selection-faq.md`)](ev-charging-roaming-plug-and-charge-tou-tariff-idle-fee-agent-selection-faq.md)**  
> **Provenance & As-Of (`2026-11-18`)**: Stripe `capture_method="manual"` pre-auth/capture mechanics, fleet merchant-locked virtual cards, and Web IQ `/v3/search` utility Time-of-Use (`TOU`) / grid demand-response grounding cite `research/daily/2026-11-08-sources.json` (`official_doc_snapshot`); `ISO 15118 Plug & Charge` certificate verification, anti-quishing QR locks, occupancy-gated idle fees, and SoC-bounded pre-auth cite `lab/webiq_commerce_demo.py` (`deterministic_offline_simulation`).

![2026-11-18 EV Supercharging Roaming (OCPI), ISO 15118 Plug & Charge, TOU Tariff & Congestion Idle-Fee Agent Architecture Visual Summary](../assets/svg/432-ev-charging-roaming-plug-and-charge-tou-tariff-idle-fee-2026-11-18.svg)

---

## 📌 1. Executive Summary

EV charging and autonomous fleet refueling involve millions of unattended, metered kilowatt-hour (`kWh`) micro-transactions daily. Solution Architects must enforce four core architectural rules:

1. **Anti-Quishing & `ISO 15118 Plug & Charge` Authentication Gate 👉 Never Trust Static Printed Stickers on Charger Cabinets; Enforce [`ISO 15118` PLC Vehicle Certificate Handshake or Dynamic 30s Screen QR + `<= 15m` Vehicle GPS Match + `MCC 5552` Lock (`HTTP 403`)]**:
   - **Why**: Fraudsters paste malicious QR stickers over public EVSE cabinets ("Quishing") that direct drivers to phishing pages. Prefer **`ISO 15118 Plug & Charge`** (mutual TLS X.509 certificate exchange over the charging cable bound to a scoped `Stripe SPT`); if QR initiation is used, verify a dynamic 30-second cryptographic nonce on the charger's digital screen, confirm vehicle-to-charger GPS proximity (`<= 15m`), and lock the payment token to `MCC 5552` (`HTTP 403`).
2. **SoC-Bounded `capture_method="manual"` Pre-Auth & Fair Congestion Idle-Fee Gate 👉 Never Freeze Flat `$75` Holds or Charge Idle Fees on Empty Stations (`Occupancy < 50%`) (`HTTP 422`)**:
   - **Why**: Freezing `$75.00` for 7 days when a vehicle at `50% SoC` can physically accept at most `30 kWh` (`~$10.50`) causes card limit exhaustion and driver complaints. Size the `manual` pre-auth hold to `(100% - Current SoC) × Battery Capacity × Tariff × 1.10` and capture exact metered kWh immediately upon unplugging. Furthermore, **Congestion / Idle Fees (`$0.50–$1.00/min`)** must only activate when **station occupancy `>= 50%`**, after a **`>= 5-minute` post-charge grace period**, and when `connector_lock_fault == False` (`HTTP 422`).
3. **15-Minute Interval Time-of-Use (`TOU`) Tariff Slicing & Fleet Peak-Shaving 👉 Route Fleets to Off-Peak Windows (`HTTP 409`)**:
   - **Why**: When a charging session crosses a utility TOU boundary (e.g., Peak `$0.54/kWh` before 23:00 dropping to Off-Peak `$0.21/kWh` after 23:00), billing the entire session at the initial peak rate overcharges the driver; slice metered kWh across 15-minute tariff intervals and schedule non-urgent fleet charging into off-peak windows.
4. **Grid Demand-Response Curtailment & Zero-kWh Fault Auto-Void 👉 Enforce [Web IQ Grid Alert Grounding & Instant `$0`-Fee Pre-Auth Void on Failed Handshakes (`HTTP 451`)]**:
   - **Why**: If a charger faults (`0.0 kWh` delivered after 120 seconds) or the utility issues a grid curtailment event, immediately void the `manual` pre-auth hold and re-route the vehicle.

---

## 🎯 2. Architect & Stakeholder Deep-Dive Q&A (FAQ-Driven)

### Q1: How do we eliminate both "QR Quishing" phishing attacks on public EV chargers and "Private-Car Fueling Theft" on commercial EV fleet cards?

**Answer: Bind payment authorization to the vehicle's hardware `VIN / ISO 15118 Contract Certificate` and GPS telemetry (`HTTP 403`).**

- With **ISO 15118 Plug & Charge**, the charger verifies the vehicle's hardware-embedded X.509 certificate over Power Line Communication (`PLC`)—so a fleet driver cannot plug a personal car into a supercharger and bill the company fleet card, and a passenger driver never scans a physical sticker (`HTTP 403` blocks any static QR or mismatched VIN/GPS).

---

### Q2: How should the Deterministic Pre-Auth & Congestion Idle-Fee Equation be structured?

**Answer: Bound pre-authorization by physical battery headroom and gate idle fees by real-time station utilization:**

$$\text{Max Pre-Auth Hold \$} = (1.0 - \text{SoC}_{\text{start}}) \times C_{\text{battery\_kWh}} \times P_{\text{kWh}} \times 1.10$$

$$\text{Idle Fee \$} = \begin{cases} 0 & \text{if } \text{StationOccupancy} < 0.50 \;\lor\; t_{\text{idle}} \le 5\text{ min} \;\lor\; \text{ConnectorLockFault} \\ \min(\text{IdleCap},\; r_{\text{idle}} \times (t_{\text{idle}} - 5)) & \text{otherwise} \end{cases}$$

- Attempting to levy an idle fee on an empty station (`Occupancy < 50%`) or freeze a `$75` hold above physical battery headroom is blocked in **`14 ms`** (`HTTP 422`).

---

### Q3: How does Time-of-Use (`TOU`) Split-Session Optimization save commercial EV fleets 22%–40%?

**Answer: When a fleet vehicle arrives at 22:35 with `15% SoC` (needing `10%` to finish its shift before 23:00 Off-Peak pricing begins), the agent charges *only* the `8 kWh` needed at Peak rates (`$0.54/kWh`) or pauses until 23:00 to fill the remaining `55 kWh` at Off-Peak rates (`$0.21/kWh`).**

---

## 🧭 3. Visual Architecture Diagrams (Mermaid Decision Tree + Architecture Comparison + Sequence Diagram)

### 3.1 EV Charging `ISO 15118`, SoC Pre-Auth, Idle-Fee & `TOU` Decision Tree

```mermaid
flowchart TD
    A["🎯 EV Driver / Fleet Agent Initiates Charging Session or Settlement"] --> B{"1. ISO 15118 / Dynamic QR Anti-Quishing & VIN/MCC Check?"}

    B -- "Static Sticker QR Phishing (Quishing) / Mismatched Fleet VIN<br/>OR Non-Certified EVSE Merchant (MCC != 5552)" --> C["🛑 HTTP 403 Block Quishing / Unauthorized Fleet Charge<br/>(QUISHING_STATIC_QR_OR_INVALID_EVSE_MCC_BLOCKED)"]

    B -- "ISO 15118 PLC Certificate & MCC 5552 Verified" --> D{"2. SoC-Bounded Pre-Auth & Congestion Idle-Fee Check?"}

    D -- "Charging Idle Fee When Station Occupancy <50% or <5m Grace<br/>OR Freezing $75 Pre-Auth Above Physical Battery Headroom" --> E["🚨 HTTP 422 Block Unfair Idle Fee / Excessive Hold<br/>Cap pre-auth to SoC headroom & waive empty-station idle fee"]

    D -- "Exact SoC Pre-Auth & Fair Congestion Rule" --> F{"3. Web IQ Grid Curtailment & EVSE Meter Integrity Gate?"}

    F -- "Utility Demand-Response Curtailment OR 0 kWh Faulty EVSE Relay" --> G["🛑 HTTP 451 Void Pre-Auth at $0 Fee & Re-Route to Nearby Hub"]

    F -- "Grid Active & Signed kWh Meter Verified" --> H["✅ HTTP 200 Single Capture of Exact TOU-Sliced kWh Upon Unplug<br/>(10ms settlement + instant release of unused pre-auth buffer)"]
```

---

### 3.2 Vulnerable Static-QR / $75-Hold Anti-Pattern vs. ISO 15118 + TOU-Optimized Architecture

```mermaid
flowchart LR
    subgraph BadEV["❌ Anti-Pattern: Sticker QR Quishing + $75 7-Day Hold + Empty-Lot Idle Fines"]
        direction TB
        BEV1["Static sticker QR on charger -> Scammers paste phishing QR & steal cards"] --> BEV2["Flat $75 pre-auth hold for a $10 charge -> Ties up driver credit for 7 days"]
        BEV2 --> BEV3["Charges $20 idle fee at 2 AM when 18 of 20 stalls are empty -> Chargeback dispute"]
    end

    subgraph GoodEV["✅ Production ISO 15118 Plug & Charge, SoC Pre-Auth & TOU Architecture"]
        direction TB
        GEV1["ISO 15118 PLC certificate handshake + VIN fleet lock + MCC 5552 guard"] --> GEV2["SoC-bounded manual pre-auth ($11 hold) + instant single capture on unplug"]
        GEV2 --> GEV3["Occupancy >=50% + 5m grace idle-fee gate + 15m interval TOU peak-shaving"]
    end
```

---

### 3.3 End-to-End Sequence: `ISO 15118` Handshake, SoC-Bounded Pre-Auth, TOU Slicing & Unplug Capture

```mermaid
sequenceDiagram
    autonumber
    actor Driver as 🚘 EV Driver / Fleet Vehicle
    participant EVAgent as 🤖 In-Vehicle Charging & Roaming Agent
    participant Charger as ⚡ Supercharger (ISO 15118 / OCPI 2.2.1)
    participant Gate as 🛡️ Anti-Quishing, SoC Pre-Auth & Idle-Fee Gate
    participant Stripe as 💳 Stripe SPT (capture_method='manual')

    Driver->>Charger: Plug in cable (Current SoC = 30%, Target = 80% -> 40 kWh max headroom)
    Charger->>EVAgent: 1. Complete ISO 15118 mutual TLS handshake over PLC; report TOU rate ($0.25/kWh) & Station Occupancy (35%)
    EVAgent->>Gate: 2. Calculate SoC-bounded pre-auth: 40 kWh × $0.25 × 1.10 = $11.00 (vs. legacy $75 flat hold!)
    Gate->>Gate: 3. Deterministic verification:<br/>• Hardware X.509 certificate & VIN matched (zero QR quishing)<br/>• Occupancy 35% < 50% -> Auto-exempt session from idle fees
    Gate-->>Stripe: 4. Authorize $11.00 manual hold & start DC fast charging!
    Note over Driver,Charger: 18 mins later: Reaches 80% SoC (40.4 kWh = $10.10) & unplugs
    EVAgent->>Stripe: 5. Execute single $10.10 Capture in 10ms & release $0.90 buffer at $0 fee!
```

---

## 📊 4. EV Charging Payment, `OCPI` Roaming & Fleet Refueling Decision Matrix

| Evaluation Dimension | Option A: Static Printed QR Sticker + Pre-Paid App Wallet | Option B: Flat `$75` Card Pre-Auth + 24/7 Unconditional Idle Fee | Option C: Siloed Single-Network RFID Card | Option D (Recommended): `ISO 15118 Plug & Charge` + SoC-Bounded `manual` Pre-Auth + Occupancy-Gated Idle Fee + `TOU` Agent |
|---|---|---|---|---|
| **QR Sticker Phishing (`Quishing`) & Fleet Theft Defense** | **Extremely Vulnerable** to pasted sticker overlays | Moderate | RFID cloning risk | **100% Hardware-Authenticated (`ISO 15118` PLC cert + VIN/GPS match `HTTP 403`)** |
| **Driver Card Hold Experience** | Forces trapped wallet top-ups | **Poor** (`$75` frozen for a `$10` charge) | Post-paid invoice | **Exact SoC-Bounded Hold (`$11` hold -> instant single capture on unplug)** |
| **Congestion Idle-Fee Fairness** | N/A | **High Dispute Rate** (fines drivers on empty 2 AM lots) | Rigid | **100% Fair (`HTTP 422` requires `Occupancy >= 50%` + `>= 5m` grace + zero lock fault)** |
| **Fleet Energy Cost Optimization (`TOU`)** | None | Pays peak rate for whole session | No cross-network routing | **Saves `22%–40%`** (15-min interval TOU slicing + off-peak routing `HTTP 409`) |

---

## 🧪 5. Quantitative EV Charging/Fleet Evaluation & 7-Card Provenance Matrix

| Metric / Deterministic Gate | Measured Value / Gate Outcome | Provenance Category | Source Path / Calculation & Architectural Meaning |
|---|---|---|---|
| **`ISO 15118` Verified + SoC-Bounded Pre-Auth + Instant Unplug Capture (Happy Path)** | **`HTTP 200 OK` · `10 ms`** (gate latency; `$185,000.00` quarterly EV charging & fleet batch settled) | `deterministic_offline_simulation` | `lab/webiq_commerce_demo.py` (`evaluate_ev_charging_roaming_tou_idle_agent_policy`): Verifies Plug & Charge + SoC pre-auth |
| **Static Sticker QR Phishing (`Quishing`), Fleet VIN Mismatch, or Invalid `MCC != 5552`** | **`HTTP 403 Forbidden` · `11 ms` Block** (`QUISHING_STATIC_QR_SPOOF_OR_UNAUTHORIZED_EVSE_MCC_BLOCKED`) | `deterministic_offline_simulation` | Stops QR sticker phishing and unauthorized fleet card theft |
| **Idle Fee Charged on Empty Station (`<50%`) or Flat `$75` Hold Above SoC Headroom** | **`HTTP 422 Unprocessable` · `14 ms` Block** (`UNJUSTIFIED_IDLE_FEE_ON_EMPTY_STATION_OR_EXCESSIVE_SOC_PREAUTH_BLOCKED`) | `deterministic_offline_simulation` | Eliminates unfair idle-fee chargebacks and excessive card holds |
| **Web IQ Utility Grid Curtailment Event or Faulty `0 kWh` Charger Relay** | **`HTTP 451 Hold` · `265 ms` Hold** (`WEBIQ_GRID_DEMAND_RESPONSE_CURTAILMENT_OR_FAULTY_EVSE_METER_HOLD`) | `official_doc_snapshot` | Voids pre-auth holds at `$0` fee on faulty stalls and re-routes around grid events |
| **Enabling `TOU` Off-Peak Fleet Scheduling + Cross-Network `OCPI` Routing + Fair Idle Gate** | **`HTTP 409 Confirm` · Saves `$40,700.00` in Peak Tariff Bleed & Disputes (`$144,300.00` net)** | `deterministic_offline_simulation` | Cuts fleet per-kWh refueling costs and eliminates idle-fee disputes (`22.0%` savings) |
| **Sub-Zero (`-30°C`) Physical Cable PLC Modem & BMS Contactor Close Latency** | Labeled **`not_measured`** | `not_measured` | Verified via deterministic offline ISO 15118, OCPI, and TOU policy tests |

---

## 🛠️ 6. Production Risk & Architecture Review Checklist

- [ ] **1. `ISO 15118 Plug & Charge` Certificate & Anti-Quishing Gate (`HTTP 403`)**: Are static sticker QR URLs banned in favor of `ISO 15118` PLC hardware certificates (or dynamic 30s screen tokens verified against `<= 15m` vehicle GPS and `MCC 5552`)?
- [ ] **2. SoC-Bounded `capture_method="manual"` Pre-Authorization (`HTTP 422`)**: Is the pre-auth hold sized strictly to `(100% - Current SoC) × Battery kWh × Tariff × 1.10` and captured in a single call upon unplugging?
- [ ] **3. Occupancy-Gated Congestion Idle Fees (`Occupancy >= 50%` + `5m Grace` `HTTP 422`)**: Are idle fees automatically waived whenever station occupancy is `< 50%`, within the 5-minute grace window, or when a connector lock fault occurs?
- [ ] **4. 15-Minute Interval Time-of-Use (`TOU`) Tariff Slicing**: When a charging session spans peak and off-peak utility windows, does the billing engine prorate kWh across each 15-minute tariff slice?
- [ ] **5. Web IQ Grid Curtailment & Zero-kWh Fault Auto-Void (`HTTP 451`)**: If a stall delivers `0.0 kWh` after 120 seconds or hits a utility curtailment event, is the `manual` pre-auth voided at `$0` fee?
- [ ] **6. Commercial Fleet `VIN`-to-Virtual-Card Hardware Binding (`HTTP 403`)**: Are commercial fleet payment tokens cryptographically bound to authorized vehicle `VIN` certificates to prevent personal-vehicle fueling theft?
