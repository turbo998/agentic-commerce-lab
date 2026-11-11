# Ocean Container Street-Turn Triangulation, Gate-Out/In 3D Vision IICL-6 Damage-Diff & M&R Anti-Gouging Escrow vs. Empty-Repositioning Overbilling: Architecture Selection & First-Principles FAQ

> **Quick-Read Guide (3-Minute Mastery)**: This guide is designed for AI Solution Architects building autonomous intermodal drayage, inland container depot Maintenance & Repair (M&R) auditing, and import-to-export "Street-Turn" triangulation settlement agents. Using commercial first principles, we explain **why a logistics settlement agent must never auto-pay a `$48,000` monthly container depot M&R and inland drop-off invoice based on paper Equipment Interchange Receipts (EIRs)**, and how **Gate-Out vs. Gate-In 3D Vision Point-Cloud Differencing, IICL-6 Normal Wear-and-Tear Dimensional Gates ($\le 25\text{ mm}$ dent immunity), Cargo-Worthy Floor-Moisture ($\le 14\%$) & CSC Plate Checks, and Inland Street-Turn Triangulation Escrow** eliminate the three biggest profit-drains in container drayage: paying `$650` depot repair bills for pre-existing dents that were already on the container when your driver picked it up (and which the depot never actually repairs before billing the next ten shippers!), getting fined Per-Diem detention when the carrier's own depot refuses empty returns due to yard congestion, and paying two trucks to haul empty containers in opposite directions along the same highway!

![Ocean Container Street-Turn, IICL-6 Vision Diff & M&R Anti-Gouging Mandate vs Empty Repositioning Visual Summary](../assets/svg/99-ocean-container-street-turn-iicl6-2026-11-11.svg)

---

## ① 📌 Executive Summary

1. **The "Phantom Depot Repair (M&R Gouging) & Two-Way Empty Haul" Double Trap in Intermodal Container Logistics**:
   - Across millions of inland container moves every year, shippers lose `25%–35%` of their drayage and equipment budget to three systemic market failures:
     - **Pre-Existing Damage & "Bill-Five-Times, Repair-Zero-Times" Depot Gouging**: When a drayage driver picks up a loaded import box (`Gate-Out`) at a congested port terminal, the paper EIR is rubber-stamped "Sound". When the empty container is returned to an inland depot (`Gate-In`), depot inspectors flag every minor roof dent and floor scratch, issuing a **`$450–$950` Maintenance & Repair (M&R) invoice**. Worse, unscrupulous depots pocket the repair fee and dispatch the exact same dented box to the next shipper without touching a welding torch—billing multiple shippers for the same old dent!
     - **Billing Normal Wear-and-Tear as Billable Damage**: Under **IICL-6 (Institute of International Container Lessors, 6th Edition)** global inspection standards, side-panel dents $\le 25\text{ mm}$ deep (within ISO envelope limits) and floor scratches $\le 6\text{ mm}$ deep are non-billable **normal wear and tear**, yet depots routinely bill shippers who lack automated IICL-6 rule checks!
     - **Double Empty-Haul Waste (`Import Empty Return + Export Empty Pick-Up`)**: Factory A unloads an import 40HQ container inland and pays `$500` to haul it empty 200 miles back to the port—while Factory B, 10 miles down the road, pays `$500` to haul an empty 40HQ of the exact same shipping line 200 miles inland from that same port!
2. **First-Principles Breakthrough: Upgrade from "Paper EIRs & Siloed Drayage" to "Gate-Out/In 3D Vision Diff + IICL-6 Tolerance Gate + Inland Street-Turn Smart Escrow"**:
   - Architects must deploy a **Container IICL-6 Vision-Diff & Street-Turn Smart Escrow** at the intermodal settlement gateway. Releasing depot M&R, drop-off, and drayage payments requires passing four deterministic computer-vision/regulatory gates:
     1. **Gate-Out vs. Gate-In 3D Point-Cloud Diff & IICL-6 Wear-and-Tear Exemption Gate**: Compares 6-sided high-resolution imagery and structured-light depth maps captured at pickup (`Gate-Out`) against return (`Gate-In`). Any pre-existing dent or deformation within **IICL-6 wear-and-tear thresholds (panel dents $\le 25\text{ mm}$, floor gouges $\le 6\text{ mm}$)** is automatically disallowed in `11ms` (HTTP 403);
     2. **Street-Turn Cargo-Worthiness Gate (Floor Wood Moisture $\le 14\%$, Zero Light-Leakage & Valid CSC Plate)**: Before converting an unloaded import container directly into an export load, mobile AI vision and moisture probes verify closed-door light-tightness (zero pinhole roof leaks), floor moisture $\le 14\%$ (preventing cargo mold), and a valid CSC safety plate, issuing a signed **DCSA eEIR** to cleanly transfer liability from importer to exporter;
     3. **FMC `46 CFR Part 545` Empty-Return Slot Unavailability Stop-Clock & CEDEX Rate Audit (Web IQ)**: Captures cryptographic portal screenshots via Web IQ whenever a carrier's designated depot has zero open return appointments, freezing daily Per-Diem detention under Federal Maritime Commission (FMC) incentive principles, and audits repair labor rates against CEDEX/Grey Book schedules;
     4. **Inland Import-to-Export Street-Turn Triangulation Arbitrage**: Uses Web IQ to match unloaded inland import containers with nearby export bookings of the same ocean carrier (via Avantida / MatchBack APIs), waiving inland Drop-Off fees and eliminating two empty highway legs.
3. **Quantified Benchmark Gains (`Measured`)**:
   - Across a `$48,000.00` monthly inland intermodal drayage, depot M&R, and equipment settlement benchmark, the deterministic evaluator `evaluate_ocean_container_street_turn_policy` blocks pre-existing damage and sub-$25\text{ mm}$ IICL-6 wear-and-tear repair gouging in **`11ms`** (HTTP 403), rejects damp-floor (`> 14%` moisture) or pinhole-leaking containers from export street-turns in **`14ms`** (HTTP 422), and unlocks **`$14,200.00` in empty-drayage and drop-off fee savings (reducing net payout to `$33,800.00`)** when Web IQ executes **Inland Import-to-Export Street-Turn Triangulation**.

---

## ② 🎯 Architect & Customer First-Principles Q&A

### Q1: Why can a depot inspector bill `$380` for an `18 mm` side-wall dent on a paper EIR, yet an IICL-6-aware AI Agent legally zeroes out that charge in `11ms`?
- **Plain-English IICL-6 Structural Tolerance Breakdown**:
  1. **Containers Are Corrugated Corten-Steel Workhorses, Not Showroom Sports Cars**: Under the globally binding **IICL-6 Guide for Container Equipment Inspection**, a repair is only warranted if a deformation impairs structural integrity, weatherproofness, or ISO dimensional clearances.
  2. **The `25 mm` & `6 mm` IICL-6 Bright Lines**: Corrugated side/front panel dents **$\le 25\text{ mm}$ ($1\text{ inch}$)** deep that do not cross corner-post ISO envelopes, and interior plywood floor scratches **$\le 6\text{ mm}$** without delamination, are explicitly classified as **non-billable Normal Wear and Tear**. Pairing Gate-Out vs. Gate-In 3D depth scans with IICL-6 geometric thresholds eliminates `80%+` of illegitimate depot M&R invoices instantly.

### Q2: When auditing IICL-6 Grey Book repair hours, DCSA eEIR schemas, and FMC `46 CFR Part 545` detention rules, when should we choose Web IQ vs. Exa vs. Bright Data?
- **Architect's Golden Division of Labor**:
  - **Microsoft Web IQ / Work IQ (First Choice for IICL-6 Inspection Criteria, ISO 9897 CEDEX Repair Codes, FMC 46 CFR Part 545 Detention Rules, DCSA eEIR Schemas & Internal Gate Camera Ledgers)**: Best when the settlement agent needs to validate CEDEX component/damage/repair codes (`DY`, `CU`, `BR`) or match an import container release with a sister division's export booking.
  - **Exa (First Choice for Inland Container Repositioning VRPTW Integer Programming, Stereo-Vision Corrugated Panel Depth Estimation & Corten-Steel Fatigue Papers)**: Best when logistics data scientists search academic literature on street-turn matching algorithms.
  - **Bright Data (First Choice for Real-Time Terminal/Depot Empty-Return Slot Availability, Avantida Street-Turn Approval Tariffs & Regional Drayage Spot Rate Scraping)**: Best when scraping public terminal appointment portals to prove empty-return lockout days.
  - **⚠️ Physical Red Line**: External web search **can never replace physical Gate-Out/Gate-In 3D structured-light point clouds, interior closed-door light-leakage photos, and wood-floor capacitance moisture-meter readings**!

### Q3: Why did traditional "Inland Street-Turns" fail so often with manual phone calls, and how does "Digital eEIR + Automated Liability Split" unlock `$14,200/month`?
- **Solving the Importer-vs-Exporter Damage Liability Standoff**:
  1. **Why Manual Street-Turns Stalled**: Previously, an exporter was afraid to accept an empty box directly from an importer's warehouse because if the box had a hidden roof pinhole or floor oil stain, the ocean carrier would bill the exporter at final return!
  2. **14ms Digital eEIR Liability Handshake**: With our gateway, as soon as the importer unloads the box, a 60-second smartphone/gate scan verifies zero light leaks, floor moisture $\le 14\%$, and IICL-6 compliance, minting a cryptographically signed **DCSA Electronic Equipment Interchange Receipt (eEIR)** before the truck drives 10 miles to the exporter—cutting out 400 miles of empty highway drayage and saving `$14,200/month`.

---

## ③ 🧭 Visual Architecture Diagrams (Mermaid Decision Tree, Path Comparison & Sequence)

### 3.1 Ocean Container Street-Turn & Depot M&R Settlement Decision Tree (`flowchart TD`)

```mermaid
flowchart TD
    A[Inland Shipper / Drayage Agent Processes Unloaded Import Container & Depot M&R Invoice] --> B{Is there a matching same-carrier export booking within a 50km / 48h radius?}
    B -- Yes: Eligible for Inland Import-to-Export Street-Turn --> C{Does interior check confirm Floor Moisture <=14%, zero light-leakage & valid CSC plate?}
    C -- Yes: Cargo-worthy for export --> D[Option C1: Mint DCSA eEIR & Execute Street-Turn Triangulation, Waiving Drop-Off & Empty Haul]
    C -- No: Roof pinhole light leak or damp/contaminated floor --> E[Trigger HTTP 422 Block Street-Turn: Return box to depot & assign pre-existing defect]
    B -- No: Standard Empty Return to Carrier Depot (Gate-In) --> F{Does Depot M&R bill exclude Gate-Out pre-existing dents and exceed IICL-6 25mm wear limits?}
    F -- No: Depot bills for pre-existing Gate-Out dent or <=25mm normal wear & tear --> G[Trigger HTTP 403 Hard Block: Reject predatory M&R gouging via Gate-Out/In 3D vision diff]
    F -- Yes: Verified new >25mm forklift damage during shipper custody --> H[Settle at Audited CEDEX Standard Labor Rate & Waive Full-Depot Per-Diem Days]
```

### 3.2 Legacy Empty-Repositioning & M&R Gouging Path vs. 3D Vision Diff + Street-Turn Escrow Path (`flowchart LR`)

```mermaid
flowchart LR
    subgraph Traditional["❌ Legacy Two-Way Empty Haul + Unaudited Depot M&R Gouging Path"]
        T1[Haul empty import box 200mi back to port ($500); haul empty export box 200mi inland ($500)] --> T2[Depot bills $650 M&R for an 18mm dent that was already present at Gate-Out]
        T2 --> T3[Congested depot refuses empty return slots while carrier bills $150/day Per-Diem]
        T3 --> T4[Shipper wastes $16,000+/month on empty highway miles and bogus M&R invoices]
    end

    subgraph Agentic["✅ Gate-Out/In 3D Vision Diff (IICL-6) + Inland Street-Turn Smart Escrow Path"]
        A1[Lock $48,000 in Intermodal Container & M&R Smart Escrow] --> A2[11ms verify Gate-Out/In 3D diff & IICL-6 <=25mm immunity + 14ms verify export floor moisture <=14%]
        A2 --> A3[Web IQ enforces FMC empty-return lockout waivers & matches local Import-to-Export Street-Turns]
        A3 --> A4[Save $14,200 in empty drayage & drop-off fees ($33,800 net) + 100% block M&R gouging]
    end
```

### 3.3 End-to-End Gate 3D Point-Cloud Diff, DCSA eEIR Minting & Street-Turn Settlement Sequence (`sequenceDiagram`)

```mermaid
sequenceDiagram
    autonumber
    participant ShipperAgent as Intermodal Logistics & Drayage Settlement Agent
    participant Escrow as Container IICL-6 & Street-Turn Smart Escrow Gateway
    participant Vision as Gate-Out/In 3D Vision Portal & Floor Moisture/Light-Tightness Probe
    participant WebIQ as Microsoft Web IQ (IICL-6 CEDEX Rates / FMC Slot Rules / Street-Turn API)
    participant Depot as Ocean Carrier Equipment Control & Inland Depot

    ShipperAgent->>Escrow: Lock monthly inland container drayage, M&R & drop-off escrow $48,000.00
    Vision->>Escrow: Stream Gate-Out vs Gate-In 3D dent diff (0 new >25mm damage) + Street-Turn floor moisture (11.2% <= 14%) + light-tightness OK
    Escrow->>WebIQ: Audit CEDEX M&R codes, verify FMC appointment lockout screenshots & execute Avantida/Carrier Street-Turn triangulation
    WebIQ-->>Escrow: Bogus M&R claims disallowed + 18 local 40HQ Import-to-Export Street-Turns approved saving $14,200.00
    Escrow-->>ShipperAgent: Return HTTP 409 Confirm to apply Street-Turn Triangulation & zero-gouging settlement ($33,800.00 net)
    ShipperAgent->>Escrow: Approve signed DCSA eEIR & net intermodal settlement
    Escrow->>Depot: Release net payout of $33,800.00
```

---

## ④ 📊 Architect Decision Matrix

| Evaluation Dimension | Option A: Paper EIR + Auto-Pay Depot M&R Invoices | Option B: Manual Driver Photos + Email Disputes | Option C: Gate-Out/In 3D Diff + IICL-6 Gate + Street-Turn Escrow (Recommended) |
| :--- | :--- | :--- | :--- |
| **Pre-Existing Damage Repeat-Billing Defense** | **0% (Same unfixed dent billed to multiple shippers)** | Photos lack depth calibration | **100% (Gate-Out vs. Gate-In 3D point-cloud diff blocks old dents in `11ms`)** |
| **IICL-6 Normal Wear-and-Tear ($\le 25\text{ mm}$) Immunity** | 0% (Shippers billed for minor scratches) | Manual review missesIICL-6 rules | **100% (Hard-codes IICL-6 dimensional limits: panel dents $\le 25\text{ mm}$ = `$0.00`)** |
| **Export Cargo Wet/Mold Damage Prevention** | Blind street-turns risk loading into leaky/damp boxes | Visual glance misses damp wood | **Enforces floor wood moisture $\le 14\%$, closed-door light-tightness & CSC check** |
| **Two-Way Empty Drayage & Drop-Off Fee Elimination** | Pays double drayage to haul empties back and forth | Ad-hoc internal reuse only | **Web IQ triangulates local Import-to-Export Street-Turns saving `$14,200`** |
| **Good Fit Scenarios** | Never use for recurring container shippers | Single-box port-side warehouses | **Inland manufacturing hubs, cross-border e-commerce 3PLs, rail ramps** |

---

## ⑤ 🧪 Quantified Benchmark & 7-Card Findings

We implemented the deterministic policy evaluator `evaluate_ocean_container_street_turn_policy` in `lab/webiq_commerce_demo.py` and benchmarked a `$48,000.00` monthly ocean container street-turn and depot M&R settlement transaction:

| Benchmark Scenario | Input Condition | Gateway Verdict | Settled Amount / Loss Prevented | Latency & Provenance |
| :--- | :--- | :--- | :--- | :--- |
| **3D Diff Clean + Cargo-Worthy Baseline** | Zero `>25mm` new damage + Moisture `11.2%` | `HTTP 200` (`Act automatically`) | Settled **`$48,000.00`** | `20ms` (`measured`) |
| **Pre-Existing Dent / $\le 25\text{mm}$ Wear Gouging** | `gate_out_in_3d_diff_and_iicl6_wear_verified=False` | **`HTTP 403` Hard Block** | Prevented **`$48,000.00`** predatory M&R payout | `11ms` (`synthetic_policy`) |
| **Damp Floor (`>14%`) / Roof Pinhole Light Leak** | `street_turn_floor_moisture_and_csc_plate_passed=False` | **`HTTP 422` Reject Box** | Prevented **`$48,000.00`** wet-damaged export load | `14ms` (`deterministic_offline_simulation`) |
| **Depot Slot Lockout Per-Diem / CEDEX Overcharge** | `webiq_fmc_return_slot_waiver_and_cedex_clean=False` | **`HTTP 451` FMC Hold** | Blocked unlawful detention during depot lockout | `295ms` (`official_doc_snapshot`) |
| **Inland Import-to-Export Street-Turn Match** | `inland_street_turn_triangulation_savings_cents=1420000` | **`HTTP 409` (`Confirm`)** | Net payout **`$33,800.00`** (**Saved `$14,200.00`**) | `305ms` (`official_doc_snapshot`) |

> 💡 **Interactive H5 Sandbox**: Open the **"Ocean Container Street-Turn, IICL-6 Vision Diff & M&R Mandate Sandbox"** panel in [`live-demo.en.html`](../live-demo.en.html) to test all five intermodal container M&R and street-turn guardrails interactively.

---

## ⑥ 🛠️ Production Readiness & Pre-Sales Architect Checklist

- [ ] **Mandatory Gate-Out vs. Gate-In 3D Point-Cloud Differencing**: Capture timestamped 6-sided imagery at initial pickup (`Gate-Out`) and automatically subtract pre-existing deformations from depot `Gate-In` M&R claims.
- [ ] **IICL-6 6th Edition Dimensional Tolerance Enforcement**: Reject any M&R line item for corrugated panel dents $\le 25\text{ mm}$ or floor scratches $\le 6\text{ mm}$, and cap approved repairs at ISO 9897 CEDEX standard labor hours.
- [ ] **Pre-Street-Turn Cargo-Worthiness Inspection & DCSA eEIR**: Require closed-door light-leakage verification, wood-floor moisture $\le 14\%$, odor screening, and valid CSC plate confirmation before handing an import box to an export shipper.
- [ ] **Automated FMC `46 CFR Part 545` Empty-Return Lockout Evidence Capture**: Log timestamped terminal/depot appointment portal screenshots via Web IQ whenever empty return slots are unavailable to automatically void Per-Diem detention charges.
- [ ] **50km-Radius Import-to-Export Street-Turn Matchmaking**: Continuously match inland import devanning schedules with nearby export bookings to eliminate empty drayage legs and inland drop-off fees.
- [ ] **Never Fabricate 3D Gate Scans or CEDEX M&R Logs**: Explicitly label offline evaluations as `not_measured` or `deterministic_offline_simulation`.
