# Stage 21: EU ESPR Digital Product Passport (DPP) Provenance, C2C Authentication Escrow & Trade-In Anti-Bait-and-Switch Guard

**Verification Date:** 2026-10-19 (Beijing Time)  
**Implementation Module:** `lab/resale_dpp_authenticity_escrow_guard.py`  
**Benchmark Module:** `lab/lifecycle_finance_circular_bench.py` (`reports/agentic-commerce-lifecycle-finance-bench/index.html`)  
**Test Suite:** `tests/test_resale_dpp_authenticity_escrow_guard.py`

---

## 1. EU ESPR Digital Product Passport Provenance (`verify_digital_product_passport_provenance`)

- Verifies GS1 Digital Link (`https://id.gs1.org/...`), OEM cryptographic signature (`manufacturer_signature_valid`), repair Merkle lineage (`repair_merkle_root_valid`), and global stolen/recall registries.
- Blocks stolen or recalled hardware (`STOLEN_OR_RECALLED_DPP_ASSET_BLOCKED`) and counterfeit or tampered passports (`COUNTERFEIT_DPP_SIGNATURE_REJECTED`).

---

## 2. Two-Hop C2C Authentication Escrow & Brand Royalty Split (`evaluate_authenticated_c2c_escrow_inspection_release`)

- Releases buyer escrow only after an accredited authentication lab attests `inspection_verdict == "AUTHENTIC"` and `hardware_serial_matches_dpp == True`.
- Allocates `escrow_gross_minor` across `seller_net_minor`, `authentication_fee_minor`, and `brand_resale_royalty_minor` via the Largest Remainder Method with zero cent drift (`AUTHENTICATED_ESCROW_RELEASED_WITH_ROYALTY_SPLIT`).
- On counterfeit detection or serial swap, refunds 100% of buyer escrow and slashes the seller's collateral bond (`COUNTERFEIT_INSPECTION_FAILED_BUYER_REFUNDED`).

---

## 3. Trade-In Residual Valuation & Anti-Bait-and-Switch Guard (`evaluate_trade_in_residual_value_and_grade_clawback`)

- Blocks unilateral merchant card clawbacks when post-receipt re-grading slashes the locked Trade-In quote by `> 500 bps` (`5%`, `UNILATERAL_TRADE_IN_BAIT_AND_SWITCH_BLOCKED`), requiring explicit buyer re-consent or free prepaid return (`TRADE_IN_DOWNGRADE_RECONSENT_OR_FREE_RETURN`).
