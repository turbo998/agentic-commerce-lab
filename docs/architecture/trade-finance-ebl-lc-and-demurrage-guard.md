# Stage 26: Maritime Trade Finance MLETR Electronic Bill of Lading (eBL) Title Transfer, eUCP 600 Letter of Credit Document-Match & Marine Demurrage Escrow Guard

**Verification Date:** `2026-10-19` (`Asia/Shanghai`)  
**Executable Module:** `lab/trade_finance_ebl_lc_demurrage_guard.py`  
**Unit Test Suite:** `tests/test_trade_finance_ebl_lc_demurrage_guard.py`

---

## 1. Architectural Problem Statement: Cross-Border Maritime Trade Finance & Documentary Credit Risks

When autonomous B2B supply-chain agents negotiate cross-border ocean freight and documentary credits, Classic 3-Tier Web apps fail across three high-value maritime trade boundaries:

1. **Electronic Bill of Lading (`eBL`) Double-Pledging**: Without UNCITRAL MLETR / DCSA eBL 3.0 "singularity of control" verification, a malicious exporter can pledge the same cargo title PDF/JSON to multiple trade-finance banks simultaneously (`EBL_EXCLUSIVE_CONTROL_DOUBLE_SPEND_BLOCKED`).
2. **ICC eUCP 600 Documentary Discrepancy & Late Shipment**: Releasing Letter of Credit (`L/C`) funds when shipped quantities breach UCP 600 Art. 30 `±5%` tolerance (`EUCP600_DOCUMENT_DISCREPANCY_TOLERANCE_BREACH`) or after the latest shipment cutoff (`EUCP600_LATE_PRESENTATION_OR_EXPIRED_LC_BLOCKED`).
3. **Unfair Port Congestion Demurrage & Detention Charges**: Automatically debiting consignee accounts for container dwell overages caused by carrier port omissions or customs holds rather than consignee delay (`PORT_CONGESTION_OR_CARRIER_FAULT_DEMURRAGE_WAIVED`), violating FMC OSRA interpretive rules.

---

## 2. Formal Invariants & Deterministic Guard Mechanics

1. **MLETR / DCSA eBL 3.0 Singularity of Control (`verify_mletr_electronic_bill_of_lading_endorsement`)**: Verifies carrier DCSA signature and matches `presented_control_token == registry_active_control_token` with zero concurrent pledge flags before atomic title endorsement (`MLETR_EBL_ATOMIC_TITLE_TRANSFERRED`).
2. **ICC eUCP 600 Documentary Examination (`evaluate_eucp600_letter_of_credit_document_presentation`)**: Enforces timely shipment/presentation windows, clean-on-board eBL status, and UCP 600 Art. 30 `±500 bps` quantity tolerance (`EUCP600_COMPLIANT_PRESENTATION_HONORED`).
3. **FMC Excusable Marine Demurrage & Detention Escrow (`evaluate_marine_demurrage_detention_parametric_escrow`)**: Deducts `carrier_or_customs_excusable_hours` from total container dwell time before applying `free_time_hours`, waiving carrier-fault demurrage and capping chargeable overages (`MARINE_DEMURRAGE_CAPPED_SETTLED`).
