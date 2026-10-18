# Stage 24: Healthcare & Pharmacy Agentic Commerce — SIGIS FSA/HSA IIAS Split-Tender, NCPDP/DEA eRx Dispense Guard & HIPAA PHI Descriptor Scrubber

**Verification Date:** `2026-10-19` (`Asia/Shanghai`)  
**Executable Module:** `lab/healthcare_fsa_rx_hipaa_guard.py`  
**Unit Test Suite:** `tests/test_healthcare_fsa_rx_hipaa_guard.py`  
**Pipeline Integration:** Gate 2 of `lab/unified_checkout_pipeline.py`

---

## 1. Architectural Problem Statement: Healthcare & Pharmacy Agentic Commerce

When autonomous consumer or clinical coordinator agents procure prescription medications (`Rx`), over-the-counter (`OTC`) medical devices, and general wellness items across telehealth and retail pharmacy merchants, Classic 3-Tier Web architectures fail across three compliance boundaries:

1. **IRS §213(d) & SIGIS IIAS Mixed-Basket Commingling**: Charging an entire mixed basket (e.g., insulin pens + non-LMN massage gun + shampoo) to a tax-advantaged FSA/HSA card violates IRS §213(d) substantiation rules, causing either whole-basket issuer declines or retroactive tax penalties.
2. **NCPDP SCRIPT / DEA EPCS Cross-Pharmacy Doctor Shopping & Early Refill Hoarding**: Autonomous refill agents retrying across multiple pharmacy MCP endpoints can trigger duplicate controlled-substance fills in the state Prescription Drug Monitoring Program (`PDMP`) or hoard medications before the mandatory `80%` days-supply utilization window.
3. **HIPAA §164.502(b) Payment Statement Descriptor PHI Leakage**: Naively copying LLM-generated order summaries containing `ICD-10` diagnosis codes (e.g., `C50.911`, `F33.1`), `NDC` drug identifiers (`0002-8215-01`), or clinical specialty names (`ONCOLOGY`, `PSYCHIATRY`) into ISO 8583 / Stripe statement descriptors exposes Protected Health Information (`PHI`) to card networks, issuing banks, and shared household bank statements.

---

## 2. Formal Invariants & Deterministic Guard Mechanics

### 2.1 IRS §213(d) & SIGIS IIAS Dual-Tender Split (`evaluate_sigis_fsa_hsa_iias_split_tender`)

For a mixed basket of line items $i \in \{1, \dots, N\}$ with amount $A_i$ and SIGIS category $C_i \in \{\text{ELIGIBLE\_RX}, \text{ELIGIBLE\_OTC}, \text{DUAL\_PURPOSE\_LMN}, \text{GENERAL\_MERCHANDISE}\}$:

$$A_{\text{qualified}} = \sum_{i: C_i \in \{\text{RX}, \text{OTC}\}} A_i + \sum_{i: C_i = \text{LMN} \land \text{LMN\_valid}_i = 1} A_i$$

$$A_{\text{FSA}} = \min\left(A_{\text{qualified}}, B_{\text{FSA\_avail}}\right), \quad A_{\text{backup}} = A_{\text{gross}} - A_{\text{FSA}}$$

- **Dual-Purpose LMN Routing**: Any `DUAL_PURPOSE_LMN` item without a cryptographically verified Letter of Medical Necessity (`lmn_verified=False`) is deterministically routed to the backup payment card (`DUAL_PURPOSE_SKU_LMN_MISSING_ROUTED_TO_BACKUP`).
- **Penny Conservation**: Strictly enforces $A_{\text{gross}} - (A_{\text{FSA}} + A_{\text{backup}}) = 0$ (`SIGIS_IIAS_DUAL_TENDER_SPLIT_VERIFIED`).

### 2.2 NCPDP SCRIPT / DEA EPCS & PDMP Dispense Guard (`verify_eprescribing_ncpdp_dea_dispense_guard`)

- **Prescriber & PDMP Check**: Requires `ncpdp_script_signature_valid == True`, `prescriber_dea_signature_valid == True`, and `pdmp_duplicate_active_fill_detected == False`; otherwise halts dispensing (`DEA_EPCS_OR_PDMP_DUPLICATE_FILL_BLOCKED`).
- **80% Refill Utilization Gate**: For refills (`is_refill=True`), requires:
  $$\frac{\Delta t_{\text{elapsed}}}{T_{\text{days\_supply}}} \ge 0.80$$
  Violations trigger `EARLY_REFILL_ACCUMULATION_BLOCKED`.

### 2.3 HIPAA §164.502(b) Minimum-Necessary Payment Descriptor Scrubber (`redact_hipaa_phi_from_payment_descriptor`)

- Inspects both `raw_statement_descriptor` and `raw_acquirer_metadata` for `ICD-10` regex patterns, `NDC` drug codes, and sensitive clinical specialty keywords.
- When PHI markers are detected, scrubs the card statement descriptor to a neutral MCC-8099/5912 string (capped at 22 ASCII chars) and strips clinical keys from acquirer metadata, retaining only an opaque `iias_substantiation_ref` (`HIPAA_PHI_DESCRIPTOR_SCRUBBED_TO_NEUTRAL_MCC`).
