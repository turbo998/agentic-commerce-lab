# Agentic Chargeback Defense & First-Party "Friendly Fraud" Architecture: Visa Compelling Evidence 3.0 (`CE 3.0`) 2-of-4 Historical Footprint Matching & Verifi RDR / Ethoca Triage (`chargeback_ce30_ethoca_mandate_...`) vs. Legacy Blind Representment Losses & 0.9% VDMP Monitoring Penalties: Architecture Selection & First-Principles FAQ

> **Document Type**: First-Principles Architecture Selection FAQ  
> **Target Audience**: AI Solution Architects, E-Commerce & SaaS Chargeback Representment Chief Architects, Visa Compelling Evidence 3.0 (CE 3.0) / Verifi RDR / Mastercard Ethoca Integration Directors, Acquiring Risk & VDMP/ECM Compliance Leads  
> **Executive Takeaway**: When buyers use an AI Agent to purchase goods or digital services and subsequently file a first-party "Friendly Fraud" chargeback claiming *"My AI Agent hallucinated / I did not authorize this Card-Not-Present transaction"* (Visa Reason Code `10.4` / Mastercard `4837`), **never submit a generic shipping tracking number alone (which loses $> 85\%$ of `10.4` fraud disputes while wasting `$15–$100` in dispute fees), nor fight unwinnable `$20` micro-disputes until your dispute count ratio breaches Visa's `0.65% / 0.90%` VDMP threshold**. You must enforce a deterministic architecture combining **Visa Compelling Evidence 3.0 (`CE 3.0`) Historical 2-Order 2-of-4 Footprint Matching ($\ge 2$ undisputed orders aged `120–365 days` on the same PAN sharing $\ge 2$ of `{User ID, IP Address, Device ID, Shipping Address}` to trigger mandatory pre-dispute Liability Shift) + a Verifi RDR / Ethoca Pre-Dispute ROI Triage & Zero-Double-Refund Gate + a Microsoft Web IQ VDMP Dispute-Ratio Guard & Automated Representment Escrow**.

![2026-11-14 Agentic Chargeback Defense: Visa CE 3.0 Historical 2-Order Matching, RDR/Ethoca Triage & Anti-VDMP Penalty Visual Summary](../assets/svg/200-agentic-chargeback-ce30-compelling-evidence-ethoca-rdr-2026-11-14.svg)

---

## 1. 📌 Executive Summary

### 1.1 Why Does Submitting a Signed FedEx Delivery Receipt Still Lose 85% of "Agentic Friendly Fraud (`10.4`)" Chargebacks, While Fighting `$20` Disputes Triggers `$50/tx` Visa VDMP Penalties?
From Visa/Mastercard dispute adjudication rules, **Visa Compelling Evidence 3.0 (CE 3.0)** statutory liability-shift algebra, and **VDMP count-ratio** first principles:
1. **Why Delivery Receipts Fail on Reason Code `10.4` (Card-Absent Fraud)**: A carrier delivery receipt proves merchandise reached an address (defending `13.1 Merchandise Not Received`), but under `10.4 Fraud`, issuers rule that a delivery receipt does not prove the true cardholder placed the order. Under **Visa CE 3.0**, however, if the merchant proves the same card (`PAN`) completed **at least 2 undisputed transactions `120–365 days` prior** to the dispute, and **at least 2 of 4 core attributes (`User Login ID`, `IP Address`, `Device Fingerprint`, `Shipping Address`)** match between both historical orders and the disputed order, Visa **automatically shifts 100% of the fraud liability to the issuer** in the pre-dispute phase and excludes the transaction from the merchant's dispute ratio!
2. **Negative-ROI Representment & Double-Refund Disasters**: Dispute ratios are calculated by **transaction count**, not dollar volume. Fighting a `$25` dispute without CE 3.0 evidence costs a `$15–$50` dispute fee plus a `$250–$500` pre-arbitration fee on loss, while pushing the merchant over the **`0.90%` Visa VDMP threshold**. Worse, if an Agent issues a standard API refund *after* a formal chargeback has already been opened, the merchant loses **200% of the order value** (Double Refund)!

### 1.2 Architect Selection Comparison: Legacy Manual Tracking Upload vs. Web IQ + Visa CE 3.0 & RDR/Ethoca Triage Escrow
| Dimension | ❌ Legacy Manual Representment & Uncoordinated Refunds | ✅ Web IQ + Visa CE 3.0 2-of-4 Match & RDR/Ethoca Pre-Dispute Triage |
| :--- | :--- | :--- |
| **Dispute Defense Trigger** | Uploads PDF shipping receipt on `10.4` fraud disputes; fights all disputes regardless of ticket size | Bound to `chargeback_ce30_ethoca_mandate_`: enforces **Visa CE 3.0 (`>=2` undisputed orders `120–365d` old + `>=2/4` attribute match) for high-ticket wins + RDR/Ethoca `<24h` auto-resolution for low-ticket items** |
| **Reason Code `10.4` Friendly-Fraud Win Rate** | Dismal (`< 15%` win rate without CE 3.0 historical link; merchant loses principal + dispute fee) | **Deterministic Pre-Dispute Win** (validates CE 3.0 2-of-4 match via Order Insight to block dispute creation; blocks blind arbitration without CE 3.0 in `11ms` with `HTTP 403`) |
| **Double-Refund & Negative-ROI Defense** | Fragile (refunds order after chargeback is filed causing $2\times$ loss; fights `$20` orders with `$50` fees) | **Deterministic Block** (blocks standard refund API calls on active chargebacks and routes low-ticket non-CE30 alerts to RDR, blocking violations in `14ms` with `HTTP 422`) |
| **VDMP / ECM Ratio (`< 0.65%`) Monitoring** | Blind spot (breaches `0.90%` count ratio, triggering `$50/dispute` fines and 20% rolling reserve) | **Deterministic Verification** (Web IQ `/v3/browse` audits per-MID monthly VDMP/ECM ratios and Order Insight JSON schema compliance, `280ms` `HTTP 451`) |
| **Principal Recovery & Fee Avoidance** | Loses $1.5\%\text{–}3.0\%$ of GMV to first-party friendly fraud and dispute penalties | Web IQ enables **100% CE 3.0 pre-dispute liability shift + RDR ratio suppression**, saving **$69,000.00 (15.0%)** (`HTTP 409 Confirm`) |

---

## 2. 🎯 First-Principles Q&A for Customers & Architects

### Q1: What Are the Exact Mathematical Conditions Required to Trigger a 100% Mandatory Liability Shift Under Visa Compelling Evidence 3.0 (CE 3.0)?
* **First-Principles Historical Footprint Algebra**:
  - For a disputed `10.4` transaction $T_d$, the merchant must supply two prior transactions $T_1, T_2$ on the same PAN such that:
    1. $120\text{ days} \le t(T_d) - t(T_i) \le 365\text{ days}$ for $i \in \{1, 2\}$;
    2. Neither $T_1$ nor $T_2$ has an associated TC40 fraud report or chargeback;
    3. $|\{\text{attr} \in \{\texttt{user\_id}, \texttt{ip}, \texttt{device\_id}, \texttt{ship\_addr}\} : \text{attr}(T_1) = \text{attr}(T_2) = \text{attr}(T_d)\}| \ge 2$ (with at least one of `ip`, `device_id`, or `ship_addr` matching).
  - Enforcing `ce30_two_prior_orders_120_365d_and_2of4_match_verified` guarantees pre-dispute deflection (`HTTP 403` in `11ms` if unverified arbitration is attempted).

### Q2: How Do Verifi RDR / Ethoca Pre-Dispute Alerts and Active-Chargeback Refund Locks Prevent Both VDMP Ratio Breaches and Double Refunds?
* **Pre-Dispute Deflection & State-Machine Locking**:
  - When a non-CE30 dispute is below the economic fight threshold (`< $60`), auto-accepting a **Verifi RDR / Ethoca** alert within $24\text{ h}$ resolves the claim before a formal chargeback is created, keeping the VDMP ratio near zero while locking out duplicate standard refunds (`rdr_ethoca_pre_dispute_triage_and_no_double_refund_passed`, `HTTP 422` in `14ms`).

### Q3: Why Use Microsoft Web IQ Instead of Exa or Bright Data to Audit Acquirer VDMP Ratio Telemetry and Visa Order Insight Schemas?
* **Architecture Selection Rationale**:
  - **Microsoft Web IQ** natively executes authenticated `/v3/search` and `/v3/browse` workflows across enterprise acquirer dispute portals and Visa/Mastercard CE 3.0 rulebooks in `245ms–280ms`, whereas Exa and Bright Data cannot access private merchant risk ledgers.

---

## 3. 🧭 Visual Architecture Diagrams

### 3.1 Decision Tree: Agentic Chargeback CE 3.0 & RDR/Ethoca Triage Gate
```mermaid
flowchart TD
    A[Risk / Dispute Agent Processes $460,000.00 Agentic Dispute & Representment Batch<br/>Cardholders File Reason Code 10.4 Friendly Fraud Claiming 'AI Agent Hallucination'] --> B{1. Visa CE 3.0 Historical 2-Order (120~365d) 2-of-4 Gate?<br/>>=2 undisputed orders 120~365d old on same PAN<br/>>=2 of {User ID, IP, Device ID, Ship Address} match}
    B -- Missing CE 3.0 historical match but attempts blind $500 pre-arbitration<br/>faces 85% loss rate & punitive arbitration fees --> C[🛑 HTTP 403 Hard Block<br/>UNQUALIFIED_CE30_EVIDENCE_OR_BLIND_ARBITRATION_BLOCKED<br/>11ms block blind arbitration & route to RDR triage]
    B -- CE 3.0 2-of-4 match verified (or routed to RDR) --> D{2. RDR/Ethoca ROI Triage & Zero Double-Refund Gate?<br/>Sub-$60 non-CE30 alerts auto-resolved via pre-dispute RDR<br/>Zero standard refund API call on already-active chargebacks}
    D -- Standard refund API called after formal chargeback debit<br/>causes 200% double-refund loss --> E[🚨 HTTP 422 Double-Loss Block<br/>DOUBLE_REFUND_ON_ACTIVE_CHARGEBACK_OR_NEGATIVE_ROI_BLOCKED<br/>14ms block duplicate refund & lock dispute state]
    D -- Zero double refund + positive-ROI triage verified --> F{3. Web IQ Acquirer VDMP Ratio (<0.65%) & Schema Check?<br/>Monthly MID dispute ratio safely below 0.65%/0.90% cap<br/>Order Insight CE 3.0 JSON payload schema valid}
    F -- Sub-MID dispute ratio hits 0.88% nearing VDMP penalty tier<br/>or missing device fingerprint hash in CE 3.0 payload --> G[🛑 HTTP 451 Compliance Hold<br/>VDMP_RATIO_THRESHOLD_BREACH_OR_SCHEMA_INVALID_HOLD<br/>280ms tighten RDR auto-refund threshold to protect MID]
    F -- VDMP ratio 0.18% + Order Insight schema valid --> H{4. Web IQ CE 3.0 100% Liability Shift & Fee Avoidance?<br/>Deflects high-ticket friendly fraud via Order Insight CE 3.0<br/>Recovers 100% principal & waives $15~$100 dispute fees}
    H -- Credits CE 3.0 principal recovery & fee avoidance --> I[🧑‍⚖️ HTTP 409 Architect Confirm<br/>CE30_LIABILITY_SHIFT_WIN_AND_VDMP_FEE_SAVINGS_CONFIRM<br/>Saves $69,000.00 / Net Protected $391,000.00]
    H -- Standard zero-dispute settlement --> J[⚡ HTTP 200 Auto Settlement<br/>VERIFIED_CHARGEBACK_CE30_DEFENSE_SETTLED<br/>10ms settles $460,000.00]
```

### 3.2 Legacy "Blind Delivery-Slip Representment" Loss Path vs. "Visa CE 3.0 + RDR Triage" Secure Path
```mermaid
flowchart LR
    subgraph Legacy ["❌ Legacy Path: Delivery Slip Only on 10.4 Fraud + Duplicate Refunds"]
        L1[Buyer claims AI Agent unauthorized 10.4 fraud on $800 order<br/>Merchant submits FedEx tracking slip without CE 3.0 history] --> L2[Issuer rejects representment & debits $800 + $50 fee<br/>Support bot also triggers standard refund causing 2x loss]
        L2 --> L3[Unfought $20 disputes push count ratio above 0.90%<br/>Visa places merchant in VDMP penalty program]
        L3 --> L4[Merchant loses $69,000+ to friendly fraud,<br/>double refunds & acquirer penalties]
    end

    subgraph Mandate ["✅ Modern Path: Visa CE 3.0 2-of-4 Match + Verifi RDR Pre-Dispute Triage"]
        M1[Gate links 2 undisputed orders 120~365d old on same PAN<br/>Matches Login ID + Device Fingerprint + Shipping Address] --> M2[Order Insight triggers 100% CE 3.0 Liability Shift<br/>High-ticket friendly fraud deflected before chargeback creation]
        M2 --> M3[Routes sub-$60 new-user alerts to 24h RDR auto-refund<br/>Blocks duplicate refund API calls on active chargebacks]
        M3 --> M4[100% win rate on CE 3.0 orders & 0.18% VDMP ratio<br/>Net protected $391,000.00 saving $69,000.00]
    end
```

### 3.3 End-to-End Sequence Diagram: Agentic Chargeback CE 3.0 & RDR/Ethoca Gate
```mermaid
sequenceDiagram
    autonumber
    participant Agent as Merchant Dispute / Risk Agent
    participant CE3Engine as Visa CE 3.0 & RDR Triage Engine
    participant WebIQ as Microsoft Web IQ (/v3/browse)
    participant Gate as Policy Gate (lab/webiq_commerce_demo.py)

    Agent->>CE3Engine: Request Batch #CB-CE30-202611 historical 2-order match, RDR triage & refund lock
    CE3Engine-->>Gate: Push metrics (CE30Match=True, PriorOrders=2, DoubleRefund=False, PositiveROI=True)
    Gate->>Gate: 1. Verify CE 3.0 120~365d 2-of-4 match (else 11ms HTTP 403 on blind arbitration)
    Gate->>Gate: 2. Verify zero double refund & positive-ROI RDR triage (else 14ms HTTP 422)
    Gate->>WebIQ: 3. Audit per-MID VDMP dispute ratio (<0.65%) & Order Insight CE 3.0 schema
    WebIQ-->>Gate: Return ratio safe + CE 3.0 liability shift & fee avoidance saving $69,000.00
    Gate-->>Agent: 4. Return HTTP 409 Confirm (Net $391,000.00) or HTTP 200 Auto Settlement
```

---

## 4. 📊 Architect Decision Matrix

| Evaluation Dimension | Option A: Legacy Delivery-Slip Representment | Option B: Blanket Auto-Refund on All Claims | Option C: Microsoft Web IQ + Visa CE 3.0 2-of-4 Match + RDR/Ethoca Triage (Recommended) |
| :--- | :--- | :--- | :--- |
| **`10.4` Friendly-Fraud Win Rate** | ❌ $< 15\%$ (shipping slip alone fails `10.4` rules) | ❌ $0\%$ (surrenders $100\%$ of high-ticket goods) | ✅ **100% pre-dispute Liability Shift win on CE 3.0 qualified orders** |
| **VDMP `0.90%` Count-Ratio Safety** | ❌ Micro-disputes breach `0.90%` ratio cap | ⚠️ Post-chargeback refunds still count against ratio | ✅ **CE 3.0 & RDR pre-dispute deflection keep ratio $< 0.20\%$** |
| **Double-Refund Prevention** | ❌ Support bots often refund already-charged-back orders | ❌ High risk of duplicate refund + chargeback debit | ✅ **State lock blocks standard refunds on active chargebacks (`HTTP 422`)** |
| **Net Recovery & Fee Economics** | ❌ Wastes `$15–$500` in dispute/arbitration fees | ❌ Loses $2\%+$ of GMV to first-party abuse | ✅ **Recovers principal + avoids dispute fees saving $69,000 (15.0%)** |

---

## 5. 🧪 Quantitative Benchmark & 7-Card Summary

### 5.1 Deterministic Policy Gate Benchmark (`evaluate_agentic_chargeback_ce30_policy`)
All benchmark numbers are sealed in `reports/agentic-commerce-webiq-grounding-demo-bench/report.json`:

| Lane | Scenario & Input Condition | HTTP Status | Action Pill | Settled / Blocked Amount | Latency | Provenance Label |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Lane 1** | CE 3.0 2-order (`120–365d`) 2-of-4 match + zero double refund + $0.18\%$ VDMP ratio | `200 OK` | `Act automatically` | **$460,000.00** (Auto-settled) | `10 ms` | `synthetic_policy` |
| **Lane 2** | Missing CE 3.0 historical match but attempts blind `$500` pre-arbitration on `10.4` | `403 Forbidden` | `Send to a human` | **$0.00** (Blocked blind loss) | `11 ms` | `synthetic_policy` |
| **Lane 3** | Standard refund API called on active formal chargeback (double loss) or negative-ROI fight | `422 Unprocessable` | `Send to a human` | **$0.00** (Blocked double refund) | `14 ms` | `deterministic_offline_simulation` |
| **Lane 4** | Web IQ detects MID dispute ratio nearing `0.90%` VDMP threshold or invalid CE 3.0 schema | `451 Legal Hold` | `Send to a human` | **$0.00** (Compliance hold) | `280 ms` | `official_doc_snapshot` |
| **Lane 5** | Web IQ credits CE 3.0 100% liability-shift recovery & RDR dispute-fee avoidance | `409 Conflict` | `Confirm` | **$391,000.00** (Saves **$69,000.00**) | `245 ms` | `official_doc_snapshot` |

### 5.2 Good Fit vs. Not For
* **✅ Good Fit**:
  - E-commerce, SaaS subscriptions, digital gaming, OTA travel, and AI Agent checkouts facing first-party "Friendly Fraud" (`10.4` / `4837`) disputes.
* **⛔ Not For**:
  - In-person EMV Chip-and-PIN physical retail point-of-sale terminals.

---

## 6. 🛠️ Production Readiness Checklist

- [ ] **1. Visa CE 3.0 365-Day Footprint Indexing & 2-of-4 Match Lock**: Set `ce30_two_prior_orders_120_365d_and_2of4_match_verified == True` to index `(pan_token, user_id, ip, device_id, shipping_address)` for 365 days and block blind arbitration when CE 3.0 criteria are unmet.
- [ ] **2. Verifi RDR / Ethoca Triage & Zero-Double-Refund Gate**: Require `rdr_ethoca_pre_dispute_triage_and_no_double_refund_passed == True` to auto-deflect low-ticket pre-disputes and lock out standard refunds once a chargeback is active.
- [ ] **3. Per-MID VDMP Ratio (`< 0.65%`) & Order Insight Schema Audit**: Configure Microsoft Web IQ `/v3/browse` to monitor monthly dispute ratios and CE 3.0 payload schemas (`webiq_vdmp_dispute_ratio_and_order_insight_schema_clean == True`).
- [ ] **4. CE 3.0 Liability-Shift Recovery & Fee-Avoidance Settlement**: Enable `ce30_liability_shift_recovery_and_rdr_fee_avoidance_credit_cents` to quantify recovered friendly-fraud revenue and avoided dispute fees ($15\%$ net savings).
