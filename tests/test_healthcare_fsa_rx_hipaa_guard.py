"""Unit tests for Stage 24: Healthcare FSA/HSA IIAS, NCPDP/DEA Rx, and HIPAA PHI Guard."""

from __future__ import annotations

from dataclasses import replace
import unittest

from lab.healthcare_fsa_rx_hipaa_guard import (
    evaluate_sigis_fsa_hsa_iias_split_tender,
    redact_hipaa_phi_from_payment_descriptor,
    verify_eprescribing_ncpdp_dea_dispense_guard,
)
from lab.unified_checkout_pipeline import (
    build_golden_pipeline_input,
    execute_unified_agentic_checkout,
)


class TestHealthcareFsaRxHipaaGuard(unittest.TestCase):
    def test_sigis_iias_split_tender_routes_missing_lmn_to_backup(self) -> None:
        res = evaluate_sigis_fsa_hsa_iias_split_tender(
            {
                "cart_id": "cart_sigis_01",
                "merchant_iias_certified": True,
                "fsa_available_balance_minor": 20000,
                "items": [
                    {
                        "sku": "rx_statin_30d",
                        "sigis_category": "ELIGIBLE_RX",
                        "line_total_minor": 4000,
                    },
                    {
                        "sku": "otc_thermometer",
                        "sigis_category": "ELIGIBLE_OTC",
                        "line_total_minor": 2500,
                    },
                    {
                        "sku": "dual_vitamin_d_no_lmn",
                        "sigis_category": "DUAL_PURPOSE_LMN",
                        "lmn_verified": False,
                        "line_total_minor": 3000,
                    },
                    {
                        "sku": "cosmetic_lotion",
                        "sigis_category": "GENERAL_MERCHANDISE",
                        "line_total_minor": 1500,
                    },
                ],
            }
        )
        self.assertTrue(res["allowed"])
        self.assertEqual(res["gross_cart_minor"], 11000)
        self.assertEqual(res["fsa_hsa_charge_minor"], 6500)
        self.assertEqual(res["backup_card_charge_minor"], 4500)
        self.assertEqual(res["conservation_delta_minor"], 0)
        self.assertIn("DUAL_PURPOSE_SKU_LMN_MISSING_ROUTED_TO_BACKUP", res["reason_codes"])
        self.assertIn("SIGIS_IIAS_DUAL_TENDER_SPLIT_VERIFIED", res["reason_codes"])

    def test_sigis_iias_split_tender_accepts_verified_lmn_and_caps_fsa_balance(self) -> None:
        res = evaluate_sigis_fsa_hsa_iias_split_tender(
            {
                "cart_id": "cart_sigis_02",
                "merchant_iias_certified": True,
                "fsa_available_balance_minor": 5000,
                "items": [
                    {
                        "sku": "dual_orthopedic_brace_with_lmn",
                        "sigis_category": "DUAL_PURPOSE_LMN",
                        "lmn_verified": True,
                        "line_total_minor": 8000,
                    }
                ],
            }
        )
        self.assertTrue(res["allowed"])
        self.assertEqual(res["qualified_medical_minor"], 8000)
        self.assertEqual(res["fsa_hsa_charge_minor"], 5000)
        self.assertEqual(res["backup_card_charge_minor"], 3000)
        self.assertEqual(res["conservation_delta_minor"], 0)

    def test_eprescribing_blocks_pdmp_duplicate_and_early_refill(self) -> None:
        res = verify_eprescribing_ncpdp_dea_dispense_guard(
            {
                "rx_id": "rx_ctrl_01",
                "ncpdp_script_signature_valid": True,
                "prescriber_dea_signature_valid": True,
                "pdmp_duplicate_active_fill_detected": True,
                "is_refill": True,
                "days_supply": 30,
                "days_elapsed_since_last_fill": 15,
            }
        )
        self.assertFalse(res["allowed"])
        self.assertIn("DEA_EPCS_OR_PDMP_DUPLICATE_FILL_BLOCKED", res["reason_codes"])
        self.assertIn("EARLY_REFILL_ACCUMULATION_BLOCKED", res["reason_codes"])

    def test_eprescribing_allows_compliant_refill_after_80_percent_window(self) -> None:
        res = verify_eprescribing_ncpdp_dea_dispense_guard(
            {
                "rx_id": "rx_maint_02",
                "ncpdp_script_signature_valid": True,
                "prescriber_dea_signature_valid": True,
                "pdmp_duplicate_active_fill_detected": False,
                "is_refill": True,
                "days_supply": 30,
                "days_elapsed_since_last_fill": 25,
            }
        )
        self.assertTrue(res["allowed"])
        self.assertEqual(res["dispense_status"], "AUTHORIZED")
        self.assertIn("NCPDP_EPCS_DISPENSE_AUTHORIZED", res["reason_codes"])

    def test_hipaa_descriptor_scrubber_redacts_icd10_and_ndc_leakage(self) -> None:
        res = redact_hipaa_phi_from_payment_descriptor(
            {
                "raw_statement_descriptor": "PSYCHIATRY ICD10-F33.1 NDC 0069-3150-83",
                "raw_acquirer_metadata": {
                    "patient_diagnosis": "F33.1",
                    "ndc": "0069-3150-83",
                    "iias_substantiation_ref": "sigis_tx_442",
                },
                "neutral_merchant_descriptor": "HEALTHCARE SVCS 8099",
                "mcc": "8099",
            }
        )
        self.assertTrue(res["phi_detected"])
        self.assertEqual(res["safe_statement_descriptor"], "HEALTHCARE SVCS 8099")
        self.assertNotIn("F33.1", str(res["safe_acquirer_metadata"]))
        self.assertIn("HIPAA_PHI_DESCRIPTOR_SCRUBBED_TO_NEUTRAL_MCC", res["reason_codes"])

    def test_unified_pipeline_gate2_blocks_pdmp_duplicate_rx(self) -> None:
        base_inp = build_golden_pipeline_input()
        blocked_inp = replace(
            base_inp,
            eprescribing_rx_context={
                "rx_id": "rx_gate2_pdmp_01",
                "ncpdp_script_signature_valid": True,
                "prescriber_dea_signature_valid": True,
                "pdmp_duplicate_active_fill_detected": True,
                "is_refill": True,
                "days_supply": 30,
                "days_elapsed_since_last_fill": 10,
            },
        )
        res = execute_unified_agentic_checkout(blocked_inp)
        self.assertFalse(res.checkout_committed)
        self.assertEqual(res.blocked_at_gate, 2)
        self.assertIn("DEA_EPCS_OR_PDMP_DUPLICATE_FILL_BLOCKED", res.terminal_decision_code)


if __name__ == "__main__":
    unittest.main()
