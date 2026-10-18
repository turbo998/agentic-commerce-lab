"""Unit tests for Stage 26: Maritime Trade Finance MLETR eBL Title Transfer, eUCP 600 Letter of Credit Document-Match & Marine Demurrage Escrow Guard."""

from __future__ import annotations

from dataclasses import replace
import unittest

from lab.trade_finance_ebl_lc_demurrage_guard import (
    evaluate_eucp600_letter_of_credit_document_presentation,
    evaluate_marine_demurrage_detention_parametric_escrow,
    verify_mletr_electronic_bill_of_lading_endorsement,
)
from lab.unified_checkout_pipeline import (
    build_golden_pipeline_input,
    execute_unified_agentic_checkout,
)


class TestTradeFinanceEblLcDemurrageGuard(unittest.TestCase):
    def test_mletr_ebl_exclusive_control_and_double_spend_block(self) -> None:
        valid_res = verify_mletr_electronic_bill_of_lading_endorsement(
            {
                "ebl_number": "DCSA-EBL-2026-9901",
                "carrier_dcsa_signature_valid": True,
                "registry_active_control_token": "ctrl_tok_alpha_99",
                "presented_control_token": "ctrl_tok_alpha_99",
                "concurrent_duplicate_pledge_detected": False,
                "current_holder_did": "did:web:shipper.example",
                "endorsee_did": "did:web:consignee.example",
                "escrow_payment_confirmed": True,
            }
        )
        self.assertTrue(valid_res["allowed"])
        self.assertEqual(valid_res["decision_code"], "MLETR_EBL_ATOMIC_TITLE_TRANSFERRED")

        double_spend = verify_mletr_electronic_bill_of_lading_endorsement(
            {
                "ebl_number": "DCSA-EBL-2026-9902",
                "carrier_dcsa_signature_valid": True,
                "registry_active_control_token": "ctrl_tok_alpha_99",
                "presented_control_token": "ctrl_tok_stale_01",
                "concurrent_duplicate_pledge_detected": True,
                "current_holder_did": "did:web:shipper.example",
                "endorsee_did": "did:web:bank2.example",
                "escrow_payment_confirmed": True,
            }
        )
        self.assertFalse(double_spend["allowed"])
        self.assertEqual(
            double_spend["decision_code"],
            "EBL_EXCLUSIVE_CONTROL_DOUBLE_SPEND_BLOCKED",
        )

    def test_eucp600_letter_of_credit_compliant_and_discrepancy_block(self) -> None:
        compliant = evaluate_eucp600_letter_of_credit_document_presentation(
            {
                "lc_number": "LC-EUCP-2026-01",
                "lc_max_amount_minor": 50_000_000,
                "commercial_invoice_amount_minor": 48_500_000,
                "contracted_quantity_units": 1_000,
                "ebl_shipped_quantity_units": 970,
                "ucp600_art30_tolerance_bps": 500,
                "latest_shipment_epoch": 10_000,
                "actual_shipment_epoch": 9_500,
                "lc_expiry_epoch": 20_000,
                "presentation_epoch": 12_000,
                "clean_on_board_ebl": True,
            }
        )
        self.assertTrue(compliant["honored"])
        self.assertEqual(compliant["decision_code"], "EUCP600_COMPLIANT_PRESENTATION_HONORED")
        self.assertEqual(compliant["settlement_undertaking_minor"], 48_500_000)

        discrepant = evaluate_eucp600_letter_of_credit_document_presentation(
            {
                "lc_number": "LC-EUCP-2026-02",
                "lc_max_amount_minor": 50_000_000,
                "commercial_invoice_amount_minor": 48_500_000,
                "contracted_quantity_units": 1_000,
                "ebl_shipped_quantity_units": 850,
                "ucp600_art30_tolerance_bps": 500,
                "latest_shipment_epoch": 10_000,
                "actual_shipment_epoch": 9_500,
                "lc_expiry_epoch": 20_000,
                "presentation_epoch": 12_000,
                "clean_on_board_ebl": True,
            }
        )
        self.assertFalse(discrepant["honored"])
        self.assertEqual(
            discrepant["decision_code"],
            "EUCP600_DOCUMENT_DISCREPANCY_TOLERANCE_BREACH",
        )

    def test_eucp600_late_presentation_blocked(self) -> None:
        late = evaluate_eucp600_letter_of_credit_document_presentation(
            {
                "lc_number": "LC-EUCP-2026-03",
                "lc_max_amount_minor": 50_000_000,
                "commercial_invoice_amount_minor": 45_000_000,
                "contracted_quantity_units": 1_000,
                "ebl_shipped_quantity_units": 1_000,
                "latest_shipment_epoch": 10_000,
                "actual_shipment_epoch": 11_200,
                "lc_expiry_epoch": 20_000,
                "presentation_epoch": 12_000,
            }
        )
        self.assertFalse(late["honored"])
        self.assertEqual(
            late["decision_code"],
            "EUCP600_LATE_PRESENTATION_OR_EXPIRED_LC_BLOCKED",
        )

    def test_marine_demurrage_port_congestion_waiver_and_capped_settlement(self) -> None:
        waived = evaluate_marine_demurrage_detention_parametric_escrow(
            {
                "container_id": "MSCU-889900-1",
                "total_dwell_hours": 140,
                "free_time_hours": 96,
                "carrier_or_customs_excusable_hours": 50,
                "hourly_demurrage_rate_minor": 1_500,
                "demurrage_escrow_hold_minor": 100_000,
                "max_liability_cap_minor": 80_000,
            }
        )
        self.assertTrue(waived["settled"])
        self.assertEqual(
            waived["decision_code"],
            "PORT_CONGESTION_OR_CARRIER_FAULT_DEMURRAGE_WAIVED",
        )
        self.assertEqual(waived["demurrage_fee_minor"], 0)
        self.assertEqual(waived["consignee_escrow_refund_minor"], 100_000)

        capped = evaluate_marine_demurrage_detention_parametric_escrow(
            {
                "container_id": "MSCU-889900-2",
                "total_dwell_hours": 180,
                "free_time_hours": 96,
                "carrier_or_customs_excusable_hours": 24,
                "hourly_demurrage_rate_minor": 2_000,
                "demurrage_escrow_hold_minor": 150_000,
                "max_liability_cap_minor": 80_000,
            }
        )
        self.assertTrue(capped["settled"])
        self.assertEqual(capped["decision_code"], "MARINE_DEMURRAGE_CAPPED_SETTLED")
        self.assertEqual(capped["chargeable_overage_hours"], 60)
        self.assertEqual(capped["demurrage_fee_minor"], 80_000)
        self.assertEqual(capped["consignee_escrow_refund_minor"], 70_000)

    def test_unified_pipeline_gate3_blocks_double_spent_ebl(self) -> None:
        base = build_golden_pipeline_input()
        blocked_inp = replace(
            base,
            mletr_ebl_context={
                "ebl_number": "DCSA-EBL-2026-9999",
                "carrier_dcsa_signature_valid": True,
                "registry_active_control_token": "ctrl_tok_valid",
                "presented_control_token": "ctrl_tok_forged",
                "concurrent_duplicate_pledge_detected": True,
                "current_holder_did": "did:web:shipper.example",
                "endorsee_did": "did:web:consignee.example",
                "escrow_payment_confirmed": True,
            },
        )
        res = execute_unified_agentic_checkout(blocked_inp)
        self.assertFalse(res.checkout_committed)
        self.assertEqual(res.blocked_at_gate, 3)
        self.assertIn("EBL_EXCLUSIVE_CONTROL_DOUBLE_SPEND_BLOCKED", res.terminal_decision_code)


if __name__ == "__main__":
    unittest.main()
