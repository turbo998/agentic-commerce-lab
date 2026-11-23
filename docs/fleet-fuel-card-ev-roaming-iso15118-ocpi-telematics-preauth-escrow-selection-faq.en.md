# Commercial Fleet Fuel Cards & EV Charging Roaming (`WEX / Fleetcor / Stripe Issuing Fleet / Hubject ISO 15118 / OCPI 2.2.1`), Telematics `GPS + CAN-Bus` Fuel-Theft Lock, Instant `$175 AFD` `0420` Release & Idle-Fee Cap FAQ

> **Executive Summary**: For commercial delivery, ride-hail, and field-service fleets operating mixed internal-combustion (`ICE`) and electric (`EV`) vehicles, energy spend represents `30%+` of total operating costs. Legacy fleet cards and public EV charging apps suffer from three severe financial leaks: (1) **Side-Tank & Jerrycan Fuel Theft (`Fuel Slippage`)**: Drivers swipe a company fuel card and enter their valid PIN while the company truck is parked 5 miles away—or pump `95 liters` on a `60-liter` van that already had half a tank, filling a personal car parked next to the pump; (2) **Stranded `$175` Automated Fuel Dispenser (`AFD`) & EV Charger Pre-Auth Holds (`MCC 5542 / 5552`)**: Locking `$175` at plug-in for a `$38` charge without firing an immediate `ISO 8583 0420 Partial Reversal` upon nozzle/cable hangup freezes `$137` of credit line for 5–7 business days; and (3) **Overnight `$180` EV Idle-Fee Shocks & Opaque `OCPI` Roaming Markups**.  
> Production architectures must enforce **Sub-`100ms` Issuing Webhooks Cross-Checking Vehicle `Telematics GPS (<500m)` & `CAN-Bus` Empty-Tank Volume (`Partial Approval`) + `ISO 15118-20 Plug & Charge` Hardware `VIN/EMAID` Certificates + Sub-`3-Second` `0420` Pre-Auth Release & `OCPI 2.2.1` Tariff/Idle-Fee Caps**: cutting fuel theft, roaming markups, and idle penalties by **39%** (reducing a `$270,000` quarterly loss pool to `$164,700`, saving **`$105,300/quarter`**).

![Commercial Fleet Fuel Card & EV Roaming ISO 15118, OCPI & Telematics Architecture](../assets/svg/762-fleet-fuel-card-ev-roaming-iso15118-ocpi-telematics-preauth-escrow-2026-11-24.svg)

---

## 1. Solution Architect Deep-Dive Q&A

### Q1: How do we prevent drivers from fueling or charging personal vehicles with company fleet credentials, and how do we eliminate 7-day `$175` pre-auth holds?
- **Architectural Solution (`Telematics GPS + Tank-Void Partial Approval` & `ISO 15118` Gate `HTTP 403` + Instant `0420` Reversal Gate `HTTP 422`)**:
  - During the `<100ms` card-issuing authorization webhook (`Stripe Issuing / Marqeta`), query real-time vehicle telematics (`Samsara / Geotab`): decline the swipe if the truck's `GPS` is **`>500m`** from the station, and return an **`ISO 8583 Partial Approval`** capped at `(Tank_Capacity - Current_CAN_Bus_Fuel_Level) × Local_Price` so the pump physically shuts off as soon as the company van's tank is full; for EVs, replace physical RFID cards with **`ISO 15118-20 Plug & Charge`** hardware X.509 certificates bound to the vehicle's `VIN` (`HTTP 403 TELEMATICS_GPS_MISMATCH_OR_TANK_VOID_EXCEEDED_FUEL_THEFT`);
  - Size initial EV pre-authorizations to the vehicle's target `SoC` delta (`kWh needed`) and mandate an immediate **`ISO 8583 0420 Partial Reversal`** within 3 seconds of `OCPP/OCPI` session termination (`HTTP 422 STRANDED_AFD_175_PREAUTH_HOLD_WITHOUT_INSTANT_0420_REVERSAL`).

### Q2: How do we govern `OCPI 2.2.1` cross-network EV roaming tariffs and prevent predatory overnight idle fees?
- **Architectural Solution (`OCPI` Tariff Hash Parity & Occupancy-Gated Idle-Fee Cap `HTTP 451 / 409`)**:
  - Lock the `OCPI 2.2.1` tariff quote hash before session start (rejecting settlement `CDRs` that drift `>2%`), and enforce a **3-tier Idle-Fee Shield**: (1) mandatory `>=15-minute` post-charge grace period; (2) `$0` idle fee when station occupancy is `<50%`; and (3) a hard per-session dollar cap with proactive driver push alerts (`HTTP 451 UNCAPPED_EV_IDLE_FEE_SHOCK_OR_OCPI_ROAMING_TARIFF_DRIFT`; verified telematics/ISO-15118 lock, instant `0420` release, and tariff parity return `HTTP 409 TELEMATICS_PINNED_FLEET_FUEL_EV_PLUG_AND_CHARGE_0420_CONFIRM`).

---

## 2. Visual Architecture Diagrams (Mermaid)

### 1. Fleet Fuel & EV Roaming (`ISO 15118 / OCPI`) Anti-Theft & `0420` Release Decision Tree
```mermaid
flowchart TD
    A[Commercial Fleet Fuel Swipe or EV Charger Plug-In] --> B{Is Vehicle GPS <=500m from Dispenser & Volume Capped<br/>at Empty Tank Void (or Verified via ISO 15118 PKI)?}
    B -- Truck 5 Miles Away or Pumping 95L into 60L Van + Personal Car --> C[HTTP 403 Block: Decline Remote Swipe & Cap Partial Approval at Empty Tank Liters]
    B -- Vehicle-to-Dispenser Verified --> D{Upon Nozzle/Cable Hangup: Is Unused $175 Pre-Auth<br/>Released Within 3 Seconds via ISO 8583 0420?}
    D -- $137 Hold Stranded for 7 Days After $38 Charge --> E[HTTP 422 Block: Size Pre-Auth to Target SoC & Fire Instant 0420 Partial Reversal]
    D -- Credit Line Released in <3s --> F{Does OCPI CDR Match Locked Tariff & Enforce<br/>15m Idle Grace + <50% Occupancy Waiver?}
    F -- Uncapped $180 Overnight Idle Fee or Hidden Roaming Markup --> G[HTTP 451 Block: Enforce Idle-Fee Cap/Waiver & Reject Drifted OCPI CDR]
    F -- Tariff & Idle Rules Verified --> H[HTTP 409 Confirm: Telematics/ISO15118 Lock + 0420 Release Saves 39%]
```

---

## 3. Platform Selection Matrix (`WEX / Fleetcor vs. Stripe Issuing / Marqeta Fleet vs. Hubject ISO 15118 / OCPI`)

| Dimension | WEX / Fleetcor (Closed-Loop) | Stripe Issuing / Marqeta Fleet | Hubject (`ISO 15118 Plug & Charge`) | OCPI 2.2.1 Roaming Hubs |
| :--- | :--- | :--- | :--- | :--- |
| **Anti-Theft Verification** | Keypad PIN + odometer prompt (post-hoc anomaly alerts) | **Real-time `<100ms` webhook checking live `CAN-Bus` fuel level & `GPS`** | **Hardware X.509 certificate in vehicle ECU (zero card sharing)** | Relies on eMSP authentication |
| **Partial Approval Tank Cap** | Static daily/transaction dollar limits | **Dynamic per-swipe dollar cap calculated from live empty tank liters** | Session capped by vehicle BMS target `SoC` | Session-based settlement |
| **Level-3 Product Filtering** | Universal pump-level fuel restriction & `IFTA` tax reporting | `Visa Fleet 2.0 / MC Fleet` line-item product-code controls | Electricity (`kWh`) only | Granular `OCPI CDR` tariff components |

---

## 4. Production Deployment & Risk Checklist

- [ ] **Cross-Check Live Vehicle `GPS (<500m)` & `CAN-Bus` Fuel Level in Real-Time Authorization Webhooks**: Dynamically cap each fuel authorization at the vehicle's actual empty tank capacity via `ISO 8583 Partial Approval`.
- [ ] **Enforce `Visa Fleet 2.0` Level-3 Product Restrictions**: Hard-block convenience store merchandise, alcohol, tobacco, and gift cards at gas stations.
- [ ] **Deploy `ISO 15118-20 Plug & Charge` Hardware Certificates Across Commercial EVs**: Eliminate shareable physical RFID charging cards.
- [ ] **Mandate `<3-Second` `ISO 8583 0420` Partial Reversals & `OCPI` Idle-Fee Caps**: Immediately free unused `$175 AFD` pre-authorization holds and waive idle fees when station occupancy is `<50%`.
