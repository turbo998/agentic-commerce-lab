"""Unit tests for Stage 21 EU ESPR DPP Provenance, C2C Authentication Escrow, Trade-In Guard & 16-Scenario 7-Card Deck."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.lifecycle_finance_circular_bench import (
    run_lifecycle_finance_circular_benchmark,
    write_lifecycle_finance_report,
)
from lab.resale_dpp_authenticity_escrow_guard import (
    evaluate_authenticated_c2c_escrow_inspection_release,
    evaluate_trade_in_residual_value_and_grade_clawback,
    verify_digital_product_passport_provenance,
)


class ResaleDppAuthenticityEscrowGuardTestSuite(unittest.TestCase):
    def test_dpp_provenance_blocks_stolen_or_counterfeit_and_admits_valid(self) -> None:
        stolen = verify_digital_product_passport_provenance(
            {
                "dpp_id": "dpp_gpu_stolen",
                "gs1_digital_link": "https://id.gs1.org/01/09506000134352/21/SN-900",
                "oem_issuer_did": "did:web:nvidia.com:dpp",
                "manufacturer_signature_valid": True,
                "repair_merkle_root_valid": True,
                "reported_stolen_or_recalled": True,
            }
        )
        self.assertFalse(stolen.allowed)
        self.assertEqual(stolen.decision_code, "STOLEN_OR_RECALLED_DPP_ASSET_BLOCKED")

        counterfeit = verify_digital_product_passport_provenance(
            {
                "dpp_id": "dpp_gpu_fake",
                "gs1_digital_link": "https://id.gs1.org/01/09506000134352/21/SN-901",
                "oem_issuer_did": "did:web:nvidia.com:dpp",
                "manufacturer_signature_valid": False,
                "repair_merkle_root_valid": True,
                "reported_stolen_or_recalled": False,
            }
        )
        self.assertFalse(counterfeit.allowed)
        self.assertEqual(counterfeit.decision_code, "COUNTERFEIT_DPP_SIGNATURE_REJECTED")

        valid = verify_digital_product_passport_provenance(
            {
                "dpp_id": "dpp_gpu_ok",
                "gs1_digital_link": "https://id.gs1.org/01/09506000134352/21/SN-902",
                "oem_issuer_did": "did:web:nvidia.com:dpp",
                "manufacturer_signature_valid": True,
                "repair_merkle_root_valid": True,
                "reported_stolen_or_recalled": False,
                "circularity_recycled_content_bps": 3500,
            }
        )
        self.assertTrue(valid.allowed)
        self.assertEqual(valid.decision_code, "DPP_PROVENANCE_AUTHENTIC_VERIFIED")

    def test_c2c_escrow_releases_with_exact_royalty_split_and_refunds_counterfeit(self) -> None:
        released = evaluate_authenticated_c2c_escrow_inspection_release(
            {
                "order_id": "ord_c2c_ok",
                "inspection_verdict": "AUTHENTIC",
                "hardware_serial_matches_dpp": True,
                "escrow_gross_minor": 10001,
                "authentication_fee_bps": 350,
                "brand_resale_royalty_bps": 250,
                "seller_collateral_bond_minor": 2000,
            }
        )
        self.assertTrue(released.escrow_released_to_seller)
        self.assertEqual(released.decision_code, "AUTHENTICATED_ESCROW_RELEASED_WITH_ROYALTY_SPLIT")
        self.assertEqual(released.conservation_delta_minor, 0)
        self.assertEqual(
            released.seller_net_minor + released.authentication_fee_minor + released.brand_resale_royalty_minor,
            10001,
        )

        fake = evaluate_authenticated_c2c_escrow_inspection_release(
            {
                "order_id": "ord_c2c_fake",
                "inspection_verdict": "COUNTERFEIT",
                "hardware_serial_matches_dpp": False,
                "escrow_gross_minor": 50000,
                "seller_collateral_bond_minor": 5000,
            }
        )
        self.assertFalse(fake.escrow_released_to_seller)
        self.assertEqual(fake.decision_code, "COUNTERFEIT_INSPECTION_FAILED_BUYER_REFUNDED")
        self.assertEqual(fake.buyer_refunded_minor, 50000)
        self.assertEqual(fake.seller_bond_slashed_minor, 5000)

    def test_trade_in_blocks_unilateral_bait_and_switch_and_requires_reconsent(self) -> None:
        bait_switch = evaluate_trade_in_residual_value_and_grade_clawback(
            {
                "trade_in_id": "ti_01",
                "initial_quote_minor": 100000,
                "reinspected_offer_minor": 75000,
                "max_auto_accept_downgrade_bps": 500,
                "unilateral_debit_attempted": True,
                "buyer_reconsented": False,
            }
        )
        self.assertFalse(bait_switch.allowed)
        self.assertEqual(bait_switch.decision_code, "UNILATERAL_TRADE_IN_BAIT_AND_SWITCH_BLOCKED")
        self.assertTrue(bait_switch.free_return_shipping_triggered)

        settled = evaluate_trade_in_residual_value_and_grade_clawback(
            {
                "trade_in_id": "ti_02",
                "initial_quote_minor": 100000,
                "reinspected_offer_minor": 97000,
                "max_auto_accept_downgrade_bps": 500,
                "unilateral_debit_attempted": False,
                "buyer_reconsented": False,
            }
        )
        self.assertTrue(settled.allowed)
        self.assertEqual(settled.decision_code, "TRADE_IN_VALUATION_SETTLED")
        self.assertEqual(settled.settled_trade_in_credit_minor, 97000)

    def test_sixteen_scenario_lifecycle_finance_benchmark_and_seven_card_deck(self) -> None:
        report = run_lifecycle_finance_circular_benchmark()
        self.assertEqual(report["total_scenarios"], 16)
        self.assertEqual(report["ai_native_passed"], 16)
        self.assertEqual(report["classic_3tier_passed"], 1)
        self.assertEqual(report["reversed_order_passed"], 16)

        with tempfile.TemporaryDirectory() as tmp:
            json_p, html_p = write_lifecycle_finance_report(Path(tmp))
            self.assertTrue(json_p.exists())
            self.assertTrue(html_p.exists())
            html_text = html_p.read_text(encoding="utf-8")
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", html_text)
            for idx in range(1, 8):
                self.assertIn(f"{idx} / 7", html_text)


if __name__ == "__main__":
    unittest.main()
