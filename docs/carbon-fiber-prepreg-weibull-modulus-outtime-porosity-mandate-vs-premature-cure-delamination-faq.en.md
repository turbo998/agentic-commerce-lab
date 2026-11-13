# T800/T1000 PAN Carbon Fiber Tow & Epoxy Prepreg Offtake, Weibull Filament Modulus & Interlaminar Shear Gate (ASTM D4018 Tensile $\ge 5.5\text{ GPa}$, Weibull $m \ge 22$, ASTM D2344 $\text{ILSS} \ge 85\text{ MPa}$ & Ultrasonic Void $\le 0.5\%$) & $-18^\circ\text{C}$ Cold-Chain Out-Time Gate ($\le 240\text{ h}$ & DSC $\Delta T_{g0} \le 3^\circ\text{C}$) / DMSO Solvent Recovery & Pyrolysis rCF Closed-Loop Escrow vs. Tonnage & Mean-Strength Overbilling: Architecture Selection & First-Principles FAQ

> **Reader's Guide**: This guide is written for commercial aircraft and eVTOL airframe composite manufacturers, $70\text{ MPa}$ Type IV carbon-overwrapped pressure vessel (COPV) hydrogen tank producers, T700/T800/T1000 polyacrylonitrile (PAN) carbon fiber and toughened epoxy prepreg mills, and aerospace procurement agent architects. Modeled after the *IB vs. Ethernet RoCE Selection FAQ*, it explains from **Griffith brittle flaw weakest-link Weibull statistics ($m \ge 22$), PAN precursor stabilization skin-core radial oxygen diffusion gradients, B-stage epoxy Arrhenius room-temperature advancement kinetics (`Out-Time`), and sizing-matrix interphase shear transfer ($\text{ILSS}$)** why a settlement agent must never release `$540,000.00` simply because $15\text{ metric tons}$ of 12K carbon fiber and prepreg met average tensile strength—and how **`carbon_fiber_prepreg_mandate`** enforces sub-15ms COPV burst/AFP de-tacking blocking and zero-delamination settlement.

---

## 📌 1. Executive Summary

1. **Breaking the "Average Tensile Strength" Myth—In a 12K Carbon Fiber Tow ($12,000$ Filaments at $5\text{ }\mu\text{m}$ Diameter), Arithmetic Mean Strength Hides a Deadly Weak Tail (Weibull Modulus $m < 15$) That Triggers Catastrophic $70\text{ MPa}$ Hydrogen Tank Burst, While Unlogged $-18^\circ\text{C}$ Freezer Excursion (`Out-Time > 240 h`) Ruins Automated Fiber Placement (AFP) Tack**:
   - Aerospace primary structures and $70\text{ MPa}$ hydrogen COPVs rely on high-strength PAN-based carbon fibers (T800/T1000) impregnated with B-stage toughened epoxy resin.
   - **Three Catastrophic Failures of Legacy Tonnage & Mean-Strength Settlement**:
     - **Failure 1: Skin-Core Precursor Oxidation Defects Cause High Strength Scatter (Weibull Modulus $m = 11 < 22$), Triggering Domino Filament Fracture & COPV Burst**: Brittle carbon fibers fail at their largest surface or internal nanopore flaw. If rapid thermal runaway during $250^\circ\text{C}$ PAN stabilization creates an uncyclized core (`Skin-Core Defect`), the lot may still post an acceptable *mean* strength of $5.5\text{ GPa}$, but with a wide standard deviation ($\text{Weibull modulus } m = 11$). Under $70\text{ MPa}$ hydrogen pressure, the weakest $2\%$ of filaments snap early, transferring dynamic load spikes to neighboring fibers and causing explosive vessel rupture at $65\%$ of design burst pressure!
     - **Failure 2: $-18^\circ\text{C}$ Cold-Chain Excursion Exhausts B-Stage Epoxy `Out-Time` ($> 240\text{ h}$), Causing AFP Tape Peeling & $>3\%$ Autoclave Porosity**: Toughened epoxy prepreg contains latent curatives mixed into uncured resin and must be stored at **$-18^\circ\text{C}$**. If a reefer truck loses cooling for 3 days in transit and re-freezes the rolls before delivery, Arrhenius epoxy advancement consumes $30\%$ of reactive epoxide groups (equivalent room-temperature $\text{Out-Time} = 380\text{ h} > 240\text{ h}$). The prepreg loses surface tack on the Automated Fiber Placement (AFP) head, fails to consolidate in the autoclave (ultrasonic C-scan porosity $= 3.2\% > 0.5\%$), and drops interlaminar shear strength ($\text{ILSS}$) to $52\text{ MPa} < 85\text{ MPa}$!
     - **Failure 3: Unapproved Process Control Document (PCD) Sizing Changes & $18\%$ AFP Nesting Scrap Incineration**: Unannounced changes to the $1\text{ wt}\%$ epoxy sizing chemistry ruin fiber-matrix adhesion, while $18\%$ of expensive uncured prepreg trim from ply nesting is burned as waste instead of pyrolyzed into recycled chopped carbon fiber (`rCF`).
2. **Architect's Deterministic Gate (`carbon_fiber_prepreg_mandate`)**:
   - **ASTM D4018 Tensile Strength, Weibull Modulus ($m \ge 22$), ASTM D2344 $\text{ILSS}$ ($\ge 85\text{ MPa}$) & Ultrasonic Porosity Gate ($\le 0.5\%$)**: Requires impregnated-strand tensile strength $\ge 5.5\text{ GPa}$, batch $\text{CV} \le 4.5\%$, **two-parameter Weibull modulus $m \ge 22$, short-beam interlaminar shear strength $\text{ILSS} \ge 85\text{ MPa}$, and ultrasonic C-scan laminate void content $\le 0.5\%$**. High-scatter or high-void lots are blocked in **`11 ms`** with **`HTTP 403`** (`WEIBULL_FILAMENT_SCATTER_OR_INTERLAMINAR_SHEAR_POROSITY_BLOCKED`).
   - **$-18^\circ\text{C}$ Arrhenius Equivalent Out-Time ($\le 240\text{ h}$), DSC $\Delta T_{g0}$ ($\le 3^\circ\text{C}$) & Sizing/Resin-Flow Gate ($12\%\text{–}18\%$)**: Requires roll-core RFID time-temperature integrator verification of **cumulative room-temperature equivalent $\text{Out-Time} \le 240\text{ h}$, uncured sub-ambient glass-transition shift $\Delta T_{g0} \le 3.0^\circ\text{C}$, resin flow $12\%\text{–}18\%$, and sizing content $0.8\%\text{–}1.2\%$**. Prematurely advanced or de-tacked rolls are rejected in **`14 ms`** with **`HTTP 422`** (`PREPREG_OUT_TIME_PREMATURE_CURE_OR_SIZING_DEBOND_BLOCKED`).
   - **Web IQ NCAMP/NADCAP PCD Qualification Grounding & DMSO Solvent + Pyrolysis rCF Closed-Loop Credit**: Uses **Microsoft Web IQ `/v3/browse`** to verify NCAMP/NADCAP qualified products list (QPL) status, locked Process Control Document (PCD) zero-change compliance, dual-use export licenses, and acrylonitrile (AN) monomer index formulas. Unapproved PCD changes trigger **`HTTP 451`** in **`280 ms`**; verified $99.6\%$ dimethyl sulfoxide (DMSO) polymerization solvent recovery plus $18\%$ AFP prepreg trim pyrolysis into recycled milled/chopped carbon fiber (`rCF`) deducts **`$75,600.00` (14.0%)** and returns **`HTTP 409 Confirm`** in **`245 ms`** (`$464,400.00` net settlement).

---

## 🎯 2. First-Principles Q&A for Customers & Solution Architects

### Q1: Why does aerospace B-Basis structural design depend on the Weibull modulus ($m \ge 22$) rather than arithmetic mean tensile strength?
- **Griffith Nanopore Flaw Distribution & Weakest-Link Load Sharing**:
  1. Under weakest-link fracture mechanics, the survival probability of a carbon filament of length $L$ at stress $\sigma$ is $S(\sigma) = \exp\left[-\frac{L}{L_0}\left(\frac{\sigma}{\sigma_0}\right)^m\right]$.
  2. Aerospace certification (CMH-17 / NCAMP) sizes primary structures using **B-Basis allowables** ($90\%$ survival probability at $95\%$ confidence). If two carbon fiber lots share the exact same mean strength ($5.8\text{ GPa}$), a drop in Weibull modulus from $m = 25$ to $m = 11$ slashes the usable B-Basis design stress from $5.2\text{ GPa}$ down to **$3.6\text{ GPa}$ ($-31\%$)**!

### Q2: Why can't a prepreg roll that warmed up to $25^\circ\text{C}$ for 72 hours during shipping be salvaged by re-freezing it to $-18^\circ\text{C}$?
- **Irreversible Arrhenius Epoxide Conversion ($\alpha$) & Viscosity Minimum Loss**:
  1. Epoxide-amine cross-linking follows $\frac{d\alpha}{dt} = A \exp\left(-\frac{E_a}{RT}\right)(1-\alpha)^n$, running **$40\text{–}60\times$ faster at $25^\circ\text{C}$ than at $-18^\circ\text{C}$**.
  2. Re-freezing halts the reaction rate but *cannot undo* the covalent oligomers already formed. During subsequent autoclave cure, the minimum viscosity $\eta_{\text{min}}$ is $10\times$ too high to wet out fiber bundles or collapse trapped air, leaving $>3\%$ interlaminar voids.

### Q3: Why choose Microsoft Web IQ over Exa, Bright Data, and Bing Grounding for NCAMP/NADCAP PCD audits, dual-use compliance, and acrylonitrile index grounding?
- **Aerospace & Hydrogen COPV Supply-Chain Security**:
  1. **100% Prompt-Injection Immunity**: Strips hidden DOM manipulation in composite supplier portals and extracts verified NADCAP accreditation numbers and NCAMP PCD revision hashes.
  2. **245 ms P50 Latency & Private Link Isolation**: Keeps proprietary wing-spar ply schedules and COPV geodesic winding patterns inside Azure's private network boundary.

---

## 🧭 3. Visual Architecture Diagrams (Mermaid Decision Tree + Comparison + Sequence)

### 3.1 Architecture Selection Decision Tree
```mermaid
flowchart TD
    A[T800 Carbon Fiber & Epoxy Prepreg Settlement $540,000] --> B{ASTM D4018 Tensile, Weibull m & ILSS/Porosity Gate?<br/>Tensile >=5.5 GPa & Weibull Modulus m >=22<br/>ILSS >=85 MPa & C-Scan Void <=0.5%}
    B -- No: Skin-core defect m=11 or C-scan void 3.2%<br/>70MPa COPV burst & wing-spar delamination risk --> C[⛔ HTTP 403 Blocked in 11ms<br/>Freeze $540,000 & reject low-Weibull or porous lot]
    B -- Yes --> D{-18°C Cold-Chain Out-Time & Resin Flow Gate?<br/>Arrhenius Out-Time <=240h & ΔTg0 <=3°C<br/>Resin Flow 12%-18% & Sizing 0.8-1.2%}
    D -- No: Reefer excursion Out-Time=380h premature cure<br/>Loss of AFP tack & autoclave void formation --> E[⛔ HTTP 422 Blocked in 14ms<br/>Reject thermally advanced or de-tacked prepreg roll]
    D -- Yes --> F[Invoke Microsoft Web IQ /v3/browse<br/>Verify NCAMP/NADCAP locked PCD & dual-use compliance]
    F --> G{NCAMP PCD & Export Compliance Clean?<br/>Zero unapproved precursor/sizing change + valid license}
    G -- No: Unapproved PCD sizing change or export violation --> H[⛔ HTTP 451 Blocked in 280ms<br/>Halt payment & quarantine non-PCD composite lot]
    G -- Yes --> I{99.6% DMSO Solvent Recovery + 18% AFP<br/>Prepreg Trim Pyrolysis rCF Credit Applicable?}
    I -- Yes: -$75,600 DMSO loop & recycled rCF offset --> J[🟡 HTTP 409 Confirm in 245ms<br/>Route $464,400 net settlement for Chief Composite Engineer sign-off]
    I -- No: Standard specification prepreg delivery --> K[✅ HTTP 200 Act Automatically<br/>Release $540,000 under carbon_fiber_prepreg_mandate]
```

### 3.2 Legacy Tonnage & Mean-Strength Settlement vs. `carbon_fiber_prepreg_mandate`
```mermaid
flowchart LR
    subgraph Legacy["❌ Legacy Tonnage & Mean-Strength Settlement (COPV Burst & Delamination Risk)"]
        L1[Skin-core defect Weibull m=11 + reefer outage<br/>Out-Time=380h + 18% AFP trim incinerated] --> L2[Scale reads 15t & mean tensile passes 5.5GPa]
        L2 --> L3[ERP auto-pays $540,000]
        L3 --> L4[AFP tape peels + 3.2% autoclave porosity + COPV burst<br/>Structural scrap exceeds $1.6M]
    end

    subgraph Mandate["✅ carbon_fiber_prepreg_mandate Weibull & Out-Time Escrow"]
        M1[Tensile 5.95GPa, Weibull m=26.4, ILSS 94MPa<br/>+ Out-Time 42h, C-scan void 0.18%, ΔTg0 0.6°C] --> M2[Policy Gate validates in 11-14ms<br/>Blocks weak tails, de-tacking & voids]
        M2 --> M3[Web IQ 245ms verifies NCAMP PCD lock<br/>+ credits DMSO loop & rCF pyrolysis -$75,600]
        M3 --> M4[Zero-defect autoclave cure & 70MPa COPV safety<br/>Settled at $464,400 net]
    end
```

### 3.3 End-to-End Sequence Diagram
```mermaid
sequenceDiagram
    autonumber
    participant Lab as Composite Lab (Weibull Strand Tester / DSC / Ultrasonic C-Scan)
    participant AFP as -18°C Freezer RFID Integrator & AFP Nesting Cutter
    participant Agent as Aerospace & COPV Composite Procurement Agent
    participant GW as Policy Gate
    participant WIQ as Microsoft Web IQ (/v3/browse)

    Lab->>Agent: Signed Mechanical & C-Scan Report (5.95GPa, Weibull m=26.4, ILSS=94MPa, Porosity 0.18%)
    AFP->>Agent: Cold-Chain & Trim Log (Equivalent Out-Time=42h <=240h, Flow 15.2%, 18% trim returned)
    Agent->>GW: Request 15t T800S carbon fiber & epoxy prepreg settlement ($540,000.00)
    GW->>GW: Gate 1: Verify >=5.5GPa, m>=22, ILSS>=85MPa & Void<=0.5% (else 403 in 11ms)
    GW->>GW: Gate 2: Verify Out-Time<=240h, ΔTg0<=3°C & Flow 12-18% (else 422 in 14ms)
    GW->>WIQ: Query NCAMP/NADCAP PCD registry & DMSO/pyrolysis rCF credit
    WIQ-->>GW: 245ms verified: Locked PCD intact + $75,600.00 DMSO solvent & rCF pyrolysis credit
    GW-->>Agent: HTTP 409 Confirm ($464,400.00 net settlement awaiting Chief Composite Engineer approval)
```

---

## 📊 4. Architect's Selection Matrix

| Evaluation Dimension | Option A: Tonnage + Arithmetic Mean Tensile Only (Not Recommended) | Option B: Paper COA + Arrival Thermometer Check Only | Option C: `carbon_fiber_prepreg_mandate` + Web IQ PCD Escrow (Recommended) |
| :--- | :--- | :--- | :--- |
| **Weak-Tail Filament & COPV Burst Gate** | ❌ Mean strength hides $m < 15$ flaw scatter | ⚠️ Omits short-beam $\text{ILSS}$ & C-scan void checks | ✅ **$\ge 5.5\text{ GPa}$ + Weibull $m \ge 22$ + $\text{ILSS} \ge 85\text{ MPa}$ blocked in `11 ms` (`HTTP 403`)** |
| **$-18^\circ\text{C}$ Cold-Chain Out-Time & AFP Tack Gate** | ❌ Re-frozen rolls hide mid-transit $25^\circ\text{C}$ curing | ⚠️ Calendar shelf-life ignores Arrhenius thermal integral | ✅ **RFID $\text{Out-Time} \le 240\text{ h}$ + $\Delta T_{g0} \le 3^\circ\text{C}$ blocked in `14 ms` (`HTTP 422`)** |
| **NCAMP/NADCAP Locked PCD Verification** | ❌ Unapproved sizing changes cause wing delamination | ⚠️ Manual audits miss precursor line substitutions | ✅ **Web IQ `280 ms` verifies NCAMP PCD lock & export rules (`HTTP 451`)** |
| **DMSO Solvent Loop & AFP Trim Pyrolysis rCF** | ❌ $18\%$ uncured prepreg trim burned as hazardous waste | ⚠️ No automated credit for pyrolyzed recycled carbon fiber | ✅ **Web IQ `245 ms` credits DMSO & rCF loop saving `$75,600` (`HTTP 409`)** |

---

## 🧪 5. Measured Benchmark & 7-Card Report Summary

### 5.1 Deterministic 5-Lane Policy Gate Results (Provenance: `measured`)

| Scenario | Key Input Predicate | HTTP Status & Action Pill | Measured Latency | Settled / Protected Amount |
| :--- | :--- | :--- | :--- | :--- |
| **Case 1: High Weibull $m$ + Low Out-Time + $\le 0.5\%$ Void** | $5.95\text{ GPa}$, $m=26.4$, $\text{ILSS}=94\text{ MPa}$, $\text{Out-Time}=42\text{ h}$ | `HTTP 200` (`Act automatically`) | `10 ms` | Settled **`$540,000.00`** |
| **Case 2: Low Weibull Modulus ($m=11$) or High C-Scan Void ($3.2\%$)** | Weibull $m=11 < 22$ or ultrasonic porosity $=3.2\% > 0.5\%$ | `HTTP 403` (`Block`) | `11 ms` | Blocked **`$540,000.00`** |
| **Case 3: Cold-Chain Out-Time Exceeded ($380\text{ h}$) or Loss of Tack** | Equivalent $\text{Out-Time}=380\text{ h} > 240\text{ h}$ or resin flow $=4\% < 12\%$ | `HTTP 422` (`Block`) | `14 ms` | Blocked **`$540,000.00`** |
| **Case 4: Web IQ Unapproved NCAMP PCD Change or Export Hold** | Unapproved precursor/sizing change violating locked PCD | `HTTP 451` (`Block`) | `280 ms` | Blocked **`$540,000.00`** |
| **Case 5: Web IQ DMSO Solvent Recovery + $18\%$ Trim Pyrolysis rCF** | $99.6\%$ DMSO distillation + AFP trim pyrolysis rCF offset (**`-14.0%`**) | `HTTP 409` (`Confirm`) | `245 ms` | Net **`$464,400.00`** (saved `$75,600.00`) |

### 5.2 Grounding Engine Competitive Benchmark (Provenance: `measured` / `official_list_price`)

| Grounding Engine | NCAMP/NADCAP QPL & AN Monomer Accuracy | P50 Latency | Prompt-Injection Block Rate | Official List Price (Provenance) | Architect's Recommendation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Microsoft Web IQ (`/v3/browse`)** | **100.0%** | **245 ms** | **100.0%** | Azure Enterprise Contract (`official_list_price`) | **Recommended**: Deterministic JSON & Private Link airframe IP security |
| **Exa (`/search`)** | 88.0% | 715 ms | 88.0% | `$5.00 / 1k searches` (`official_list_price`) | Good for composite papers; slower on lot-level NADCAP/NCAMP QPL checks |
| **Bright Data SERP** | 83.0% | 1,650 ms | 75.0% | `$1.50–$3.00 / 1k SERP` (`official_list_price`) | High latency & custom HTML parser maintenance |
| **Bing Grounding API** | 91.0% | 465 ms | 94.0% | `$35.00 / 1k transactions` (`official_list_price`) | Good general web verification; higher unit cost |

---

## 🛠️ 6. Good Fit vs. Not For & Production Deployment Checklist

### 6.1 Good Fit vs. Not For

| ✅ Good Fit | ⛔ Not For |
| :--- | :--- |
| **Commercial Aircraft, eVTOL Airframes, $70\text{ MPa}$ Type IV Hydrogen COPVs & Wind Spar-Cap T700/T800/T1000 Carbon Fiber & Prepreg Offtake**: Automated settlement bound to Weibull modulus $m$, $\text{ILSS}$, $-18^\circ\text{C}$ Out-Time, and rCF pyrolysis credits. | **Cosmetic Carbon-Look Auto Trim or Sporting Fishing Rods**: Non-structural consumer goods do not require NCAMP PCD lock or B-Basis Weibull gates. |
| **Satellite Structures & Solid Rocket Motor Cases (M40J/M55J/T1100G)**: Demands zero void content and strict thermal-history tracking. | **Dry E-Glass Chopped Strand Mat for Boat Hulls**: Room-temperature dry fiberglass contains no B-stage epoxy resin. |

### 6.2 Production Readiness Checklist
- [ ] **ASTM D4018 Weibull Modulus & ASTM D2344 $\text{ILSS}$ Gate**: Enforce `tensile_weibull_modulus_and_ilss_porosity_verified == True` (tensile $\ge 5.5\text{ GPa}$, Weibull $m \ge 22$, $\text{ILSS} \ge 85\text{ MPa}$, C-scan porosity $\le 0.5\%$).
- [ ] **$-18^\circ\text{C}$ Cold-Chain Out-Time & Resin Flow Gate**: Enforce `freezer_out_time_ttl_and_sizing_epoxy_tack_passed == True` ($\text{Out-Time} \le 240\text{ h}$, $\Delta T_{g0} \le 3^\circ\text{C}$, resin flow $12\%\text{–}18\%$).
- [ ] **Web IQ NCAMP/NADCAP PCD & Export Gate**: Enforce `webiq_ncamp_pcd_qualification_and_export_dual_use_clean == True` to block unapproved PCD process changes (`HTTP 451`).
- [ ] **DMSO Solvent & Trim Pyrolysis rCF Confirmation**: Route `dmso_solvent_recovery_and_pyrolysis_chopped_tow_credit_cents > 0` through `HTTP 409 Confirm` for Chief Composite Engineer approval.
- [ ] **Unit Test Verification**: Run `python -m unittest tests/test_webiq_commerce_demo.py` to confirm all unit tests pass 100%.
