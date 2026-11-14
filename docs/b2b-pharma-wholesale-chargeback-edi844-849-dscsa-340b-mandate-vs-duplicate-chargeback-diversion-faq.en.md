# B2B Pharma Wholesaler Chargeback (`McKesson / Cencora / Cardinal Health`), `EDI 844/849` Reconciliation & `DSCSA / 340B` Anti-Duplicate-Discount Settlement Architecture: `DEA/HIN` Roster Lock, Historical Lot-`WAC` Ledger & Serialized Anti-Diversion Token (`b2b_pharma_wholesale_chargeback_edi844_849_dscsa_340b_mandate_...`) vs. Class-of-Trade Diversion, `WAC`-Spike Arbitrage & `340B` Duplicate Discounts: Architecture Selection & First-Principles FAQ

> **Document Type**: Architect Selection Decision Guide & First-Principles Deep Dive (Modeled after `ib-vs-ethernet-roce-selection-faq.md`)  
> **Target Audience**: Enterprise AI Solution Architects, Biopharma Trade Finance & Gross-to-Net (GTN) Engineering Leads, Market Access & DSCSA Supply Chain Compliance Architects  
> **Related Standards**: `ANSI X12 EDI 844 (Product Transfer Account Adjustment)`, `ANSI X12 EDI 849 (Response to Product Transfer Account Adjustment)`, `EDI 845 (Price Authorization Acknowledgment)`, `FDA DSCSA EPCIS 2D Serialized SGTIN`, `HRSA 340B OPAIS & 42 U.S.C. § 256b(a)(5)(A)`, `Microsoft Web IQ`, `Stripe SPT` / `Visa VIC`

---

## 📌 1. Executive Summary

1. **One-Sentence Verdict**: In North American and global pharmaceutical distribution, manufacturers sell prescription drugs to primary wholesalers (`McKesson`, `Cencora`, `Cardinal Health`) at high **Wholesale Acquisition Cost (`WAC`, e.g., `$1,000/vial`)**; wholesalers then resell those units to contracted hospitals or `340B` clinics at negotiated **Contract Prices (e.g., `$620/vial`)** and submit an **`ANSI X12 EDI 844` Chargeback Claim** back to the manufacturer to recover the `$380/vial` spread. **Never allow a Trade Finance Agent to auto-issue credit memos based solely on a wholesaler's unverified `EDI 844` claim file!** You must enforce a deterministic **`b2b_pharma_wholesale_chargeback_edi844_849_dscsa_340b_mandate_2026`** architecture backed by **`DEA / HIN / HRSA 340B` point-in-time contract roster verification + historical Lot-`WAC` inventory depletion tracking + `DSCSA SGTIN` serialized anti-replay & `340B/Medicaid` duplicate-discount locks**.
2. **Why Legacy Pharma Chargeback Processing Bleeds 4%–8% of Gross Revenue (`$15B+/Year` Industry-Wide in Gross-to-Net Leakage)**:
   - **Class-of-Trade Diversion & Ineligible End-Customer Spoofing (`403 dea_hin_contract_roster_mismatch`)**: A wholesaler (or downstream secondary sub-distributor) sells 500 oncology vials to a non-contracted retail pharmacy or cosmetic clinic at `$920/vial`, but submits an `EDI 844` listing the `DEA` or `HIN` (Health Industry Number) of a contracted GPO hospital—or a hospital whose GPO membership expired last month—to pocket an unearned `$380/vial` contract chargeback.
   - **`WAC`-Spike Inventory Arbitrage & Phantom Lot Volume (`422 wac_lot_inventory_exhausted`)**: On January 1, the manufacturer increases `WAC` from `$900` to `$1,000`. The wholesaler holds 2,000 vials bought in December at the old `$900` `WAC` (`Lot #LOT-2025Q4`). When sold to a hospital at the `$620` contract price in January, the true spread is `$900 - $620 = $280`; yet the wholesaler submits an `EDI 844` claiming `$1,000 - $620 = $380/vial`, skimming `$100/vial` in phantom price-increase profit—or claims `1,350` vials against a lot where the manufacturer only shipped `1,000` vials.
   - **`340B + Medicaid` Duplicate Discounts & `DSCSA SGTIN` Serial Replay (`451 duplicate_340b_or_dscsa_serial_replay`)**: Under `42 U.S.C. § 256b(a)(5)(A)`, a manufacturer cannot be subjected to both a front-end `340B` chargeback discount and a back-end State `Medicaid` rebate on the same dispensed unit; similarly, wholesalers or 340B contract pharmacies may accidentally or fraudulently submit the same `DSCSA 2D DataMatrix SGTIN` serial number across multiple `EDI 844` batches.
3. **Architect's Golden Rule**:
   - **End-Customer Eligibility & Contract Roster Gate**: Use **Microsoft Web IQ** to deterministically verify that the end-hospital's `DEA Number`, `HIN`, and `HRSA OPAIS 340B ID` are active on the manufacturer's `EDI 845` price authorization roster on the exact invoice date (otherwise block with `403 dea_hin_contract_roster_mismatch` and emit an `EDI 849` rejection).
   - **Historical Lot-`WAC` & Inventory Depletion Gate**: Bind every `EDI 844` line to the original `EDI 810` manufacturer invoice `WAC` for that specific `DSCSA Lot`, blocking `WAC`-spike arbitrage and claims exceeding remaining lot units (`422 wac_lot_inventory_exhausted`).
   - **Serialized `DSCSA SGTIN` & `340B/Medicaid` Dedup Lock**: Verify every unit's `DSCSA SGTIN` is unredeemed and free of cross-filed Medicaid rebate claims (`451 duplicate_340b_or_dscsa_serial_replay`).

---

## 🎯 2. Customer & Architect Soul-Searching Q&A (First-Principles Q&A)

### Q1: In plain English—what is a Pharma `Wholesaler Chargeback (EDI 844)`, and why don't drug manufacturers simply sell to wholesalers at the hospital contract price upfront?
**A: Because at the moment the wholesaler buys a truckload of medicine from the factory, nobody knows which hospital will eventually buy each box!**
- **First-Principles Breakdown**:
  1. Suppose a biopharma manufacturer produces a specialty biologic with a list **Wholesale Acquisition Cost (`WAC`) of `$1,000/vial`**.
  2. Across the US, thousands of hospitals belong to different Group Purchasing Organizations (`GPOs`) or federal programs: Hospital A qualifies for a **`340B` price of `$520/vial`**, Hospital B has a **`GPO Tier-1` contract price of `$680/vial`**, and Clinic C has no contract and must pay **`$1,000/vial`**.
  3. The manufacturer ships 10,000 vials in bulk to `McKesson` at **`WAC $1,000/vial`**. A week later, Hospital B buys 100 vials from `McKesson` at its contracted **`$680/vial`** price.
  4. Now `McKesson` is out `$320/vial`! Every night, `McKesson` sends an **`EDI 844` Chargeback Claim** to the manufacturer asking for **`100 × ($1,000 - $680) = $32,000`** back, and the manufacturer responds via **`EDI 849`**.
- **Why Naive LLM Automation Fails**:
  - Without deterministic verification of the hospital's `DEA/HIN` membership on the invoice date, the lot's historical purchase `WAC`, and the unit's `DSCSA SGTIN` serial number, wholesalers can claim `$380/vial` rebates on drugs diverted to non-contracted clinics or pocket millions during annual `WAC` price increases.

### Q2: How should Microsoft Web IQ, Exa, and Bright Data be positioned in a Pharma `EDI 844/849` & `DSCSA/340B` Chargeback Architecture?
**A: Contract roster verification and serialized `DSCSA` accounting require zero-hallucination deterministic state—Microsoft Web IQ is the production backbone:**

| Dimension | Microsoft Web IQ (Production Backbone) | Exa (Semantic Search) | Bright Data (Web Scraping) |
| :--- | :--- | :--- | :--- |
| **Core Role** | **Deterministic `DEA/HIN/OPAIS` & `EDI 845` Contract Graph** | Policy research on 340B litigation & state legislation | Retail pharmacy cash-price scraping |
| **`DEA / HIN / HRSA 340B` Verification** | **Exact entity & date-range alignment**: Verifies active `EDI 845` contract membership and `HRSA OPAIS` covered-entity eligibility on the exact invoice date | Vector similarity confuses non-eligible outpatient clinics with parent 340B hospitals | Cannot access private `EDI 844/845` or `DSCSA EPCIS` ledgers |
| **Lot-`WAC` & `SGTIN` Depletion** | **Transactional state enforcement**: Binds claims to original `EDI 810` lot `WAC` and remaining unredeemed units | No stateful inventory depletion capability | Not applicable |

---

## 🧭 3. Visual Architecture & Mermaid Diagrams

### 3.1 Pharma Wholesaler `EDI 844` Chargeback & `DSCSA/340B` Verification Decision Tree

```mermaid
flowchart TD
    A["Wholesaler Submits EDI 844 Chargeback Claim<br/>(Hospital DEA/HIN + Contract ID + Lot/SGTIN + Claimed Spread)"] --> B{"1. Hospital DEA/HIN Active on EDI 845<br/>& HRSA 340B Roster on Invoice Date?"}
    B -- "No (Non-Member / Expired Contract / Terminated 340B ID)" --> R1["❌ 403 dea_hin_contract_roster_mismatch<br/>Emit EDI 849 Reject Code (Ineligible End-User)"]
    B -- "Yes (Verified Active Contract Member)" --> C{"2. Claimed WAC == Historical Lot Acquisition WAC<br/>AND Cumulative Lot Units <= Shipped Qty?"}
    C -- "No (WAC-Spike Arbitrage or Lot Volume Exhausted)" --> R2["❌ 422 wac_lot_inventory_exhausted<br/>Recalculate at Historical Lot WAC & Block Phantom Units"]
    C -- "Yes (Historical Lot WAC & Remaining Balance Valid)" --> D{"3. DSCSA SGTIN Serial Unredeemed<br/>AND Zero 340B+Medicaid Duplicate Claim?"}
    D -- "No (Replayed SGTIN or 340B+Medicaid Duplicate Discount)" --> R3["❌ 451 duplicate_340b_or_dscsa_serial_replay<br/>Quarantine Line & Log HRSA/MDRP Audit Trail"]
    D -- "Yes (Unique SGTIN & Single Discount Verified)" --> E{"4. Net EDI 844 Batch Credit <= $150,000<br/>AND Not Contested EDI 849 Resubmission?"}
    E -- "No (Batch > $150k or Contested Resubmission)" --> R4["⚠️ 409 require_pharma_trade_finance_hitl<br/>Trade Finance + Market Access Dual WebAuthn"]
    E -- "Yes (Fully Compliant Within Auto Cap)" --> R5["✅ 200 OK Emit EDI 849 Approval & Credit Memo<br/>b2b_pharma_wholesale_chargeback_..."]

    style R1 fill:#fee2e2,stroke:#dc2626,color:#7f1d1d
    style R2 fill:#fef3c7,stroke:#d97706,color:#78350f
    style R3 fill:#fce7f3,stroke:#db2777,color:#831843
    style R4 fill:#e0f2fe,stroke:#0284c7,color:#0c4a6e
    style R5 fill:#dcfce7,stroke:#16a34a,color:#14532d
```

### 3.2 Legacy Rubber-Stamp Chargebacks vs. Agentic `DSCSA + Lot-WAC + 340B` Deterministic Settlement

```mermaid
flowchart LR
    subgraph Legacy["🔴 Legacy Rubber-Stamp EDI 844 Processing (4%–8% GTN Revenue Leakage)"]
        L1["Wholesaler Sells to Non-Contract Clinic<br/>Submits Hospital HIN on EDI 844"] --> L2["After Jan 1 Price Hike, Old Inventory<br/>Claimed at New WAC (+$100/vial Fraud)"]
        L2 --> L3["Same Vial Gets 340B Chargeback<br/>AND State Medicaid Rebate"]
        L3 --> L4["Millions in Gross-to-Net Leakage<br/>Months of Manual EDI 849 Disputes"]
    end

    subgraph Agentic["🟢 Agentic Web IQ + DSCSA SGTIN + EDI 849 Deterministic Architecture"]
        A1["DEA + HIN + HRSA OPAIS Lock<br/>Point-in-Time EDI 845 Roster Match"] --> A2["Historical Lot EDI 810 WAC Binding<br/>Zero Price-Hike Inventory Arbitrage"]
        A2 --> A3["DSCSA 2D SGTIN Single-Use Lock<br/>+ 340B/Medicaid Mutual Exclusion"]
        A3 --> A4["11ms Automated EDI 849 Adjudication<br/>Exact Verified Credit Memo Issuance"]
    end
```

### 3.3 End-to-End Sequence Diagram (`EDI 845` Roster → `EDI 844` Claim → `DSCSA/340B` Gate → `EDI 849` Response)

```mermaid
sequenceDiagram
    autonumber
    participant WH as Primary Wholesaler (McKesson / Cencora)
    participant AGT as Pharma Trade Finance Agent (Policy Gate)
    participant WIQ as Microsoft Web IQ (EDI 845 / HRSA OPAIS / DEA)
    participant DSC as DSCSA EPCIS & Historical Lot-WAC Ledger
    participant PAY as Pharma ERP Credit Memo / Stripe SPT

    WH->>AGT: Submit EDI 844 Chargeback Claim (Hospital DEA/HIN, Contract #GPO-88, Lot #L99, SGTINs)
    AGT->>WIQ: Verify Hospital DEA/HIN Active on EDI 845 Roster & HRSA 340B Status on Invoice Date
    WIQ-->>AGT: Confirmed Active Member, Contract Price = $620/vial
    AGT->>DSC: Query Lot #L99 Original EDI 810 WAC ($1,000/vial), Remaining Lot Balance & SGTIN Status
    DSC-->>AGT: Confirmed Historical WAC=$1,000, Sufficient Balance, Unique SGTIN, Zero Medicaid Conflict
    AGT->>PAY: Issue b2b_pharma_wholesale_chargeback_... Token, Generate EDI 849 Approval ($380/vial Credit)
    PAY-->>WH: Return EDI 849 (Approved Without Adjustment) + Audit Receipt
```

---

## 📊 4. Architect Decision Matrix

| Evaluation Dimension | Option A: Legacy Batch ERP Auto-Credit | Option B: Generic RPA + LLM Text Review | Option C: Web IQ + `EDI 844/849` + `DSCSA SGTIN` Architecture (Recommended) |
| :--- | :--- | :--- | :--- |
| **End-Hospital `DEA/HIN` Roster Enforcement** | ❌ Checks contract ID only; misses expired or ineligible clinics | ⚠️ Fuzzy name matching confuses non-340B satellite clinics | ✅ **Deterministic `DEA + HIN + HRSA OPAIS` verification on invoice date (`403`)** |
| **`WAC`-Spike Inventory Arbitrage Defense** | ❌ Pays spread against current `WAC`, losing millions on price hikes | ❌ Cannot link `EDI 844` lines to historical `EDI 810` lot invoices | ✅ **Binds every claim to historical Lot-`WAC` and remaining shipped balance (`422`)** |
| **`340B + Medicaid` Duplicate & `SGTIN` Replay** | ❌ Post-hoc quarterly sampling (<15% recovery) | ⚠️ No unit-level `DSCSA SGTIN` state ledger | ✅ **Real-time `DSCSA SGTIN` dedup + `340B/Medicaid` cross-claim block (`451`)** |
| **Automated `EDI 849` Line-Level Adjustment** | ❌ Manual spreadsheets taking 60–90 days | ⚠️ Requires manual ERP re-entry | ✅ **11ms automated `ANSI X12 EDI 849` approval/recalculation/rejection generation** |

---

## 🧪 5. Quantitative Benchmark & 7-Card Report

Evaluated in `lab/webiq_commerce_demo.py` via `evaluate_b2b_pharma_wholesale_chargeback_policy`:

| Case ID | Input Scenario | Deterministic Gate Action | HTTP Status | Error Code / Mandate Token | Measured Latency |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Case 1** | Hospital `DEA/HIN` active on `EDI 845` roster, historical Lot `WAC $1,000`, contract `$620`, `100` unique `DSCSA SGTIN` vials (`$38,000` credit) | **Act Automatically (Approve EDI 849 & `$38,000` Credit Memo)** | `200 OK` | `b2b_pharma_wholesale_chargeback_edi844_849_dscsa_340b_mandate_2026` | `11ms` (`measured`) |
| **Case 2** | Wholesaler ships to non-contracted clinic or hospital with expired GPO/340B membership on invoice date | **Block (Reject Class-of-Trade Diversion via EDI 849)** | `403 Forbidden` | `dea_hin_contract_roster_mismatch` | `5ms` (`measured`) |
| **Case 3** | Wholesaler claims post-hike `$1,000` `WAC` on old `$900` `WAC` lot inventory or exceeds shipped lot quantity | **Block (Reject WAC-Spike Arbitrage & Phantom Volume)** | `422 Unprocessable` | `wac_lot_inventory_exhausted` | `6ms` (`measured`) |
| **Case 4** | Replayed `DSCSA SGTIN` serial number or `340B` unit already claimed under State `Medicaid` rebate | **Block (Reject Duplicate 340B Discount & SGTIN Replay)** | `451 Unavailable` | `duplicate_340b_or_dscsa_serial_replay` | `7ms` (`measured`) |
| **Case 5** | Compliant hospital system `EDI 844` batch credit of `$240,000` (`> $150,000` auto cap) or contested `EDI 849` resubmission | **Confirm (Escalate to Trade Finance + Market Access WebAuthn)** | `409 Conflict` | `require_pharma_trade_finance_hitl` | `9ms` (`measured`) |

### Good Fit vs. Not For
- **✅ Good Fit**:
  - Branded pharmaceutical, specialty biologic, and oncology manufacturers reconciling daily `EDI 844/849` chargebacks with primary wholesalers (`McKesson`, `Cencora`, `Cardinal Health`);
  - Gross-to-Net (`GTN`) revenue protection across `HRSA 340B`, `GPO` tiered contracts, `VA/DoD FSS`, and `DSCSA` serialized unit tracking.
- **⛔ Not For**:
  - Flat net-priced OTC consumer health products without distributor chargeback contracts;
  - Direct-to-patient retail pharmacy copay card adjudication (use Specialty Pharmacy `eBV/REMS` gates instead).

---

## 🛠️ 6. Production Readiness Checklist

- [ ] **Point-in-Time `DEA / HIN / HRSA 340B` Roster Alignment**: Are `EDI 845` contract rosters and daily `HRSA OPAIS` snapshots ingested into Microsoft Web IQ to validate end-customer eligibility as of the exact wholesaler invoice date?
- [ ] **Historical Lot-`WAC` & Inventory Depletion Ledger**: Is every `EDI 844` claim line bound to the original manufacturer `EDI 810` invoice `WAC` and remaining unredeemed unit balance for that `DSCSA Lot`?
- [ ] **`DSCSA SGTIN` Single-Use & `340B/Medicaid` Mutual Exclusion**: Are `2D DataMatrix SGTIN` serial numbers cryptographically locked upon first chargeback approval and cross-checked against State `Medicaid` rebate claims?
- [ ] **Automated `ANSI X12 EDI 849` Line-Code Generation**: Does the policy gate automatically emit standardized `EDI 849` adjustment/dispute codes (`CB`, `WA`, `DP`) on rejected or recalculated lines?
- [ ] **Dual WebAuthn Sign-Off for High-Value Batches (`> $150,000`)**: Are `EDI 844` batches exceeding `$150,000` or contested `EDI 849` resubmissions gated by Trade Finance and Market Access hardware `WebAuthn` approval?
