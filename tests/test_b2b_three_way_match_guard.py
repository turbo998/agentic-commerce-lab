"""Unit tests for Stage 10 Enterprise B2B 3-Way Match, Split-Shipment Escrow & Dynamic Discounting Guard."""

from __future__ import annotations

import unittest

from lab.b2b_three_way_match_guard import (
    evaluate_dynamic_discounting_apr,
    run_demo_scenarios,
    verify_b2b_three_way_match_and_escrow,
)


class B2BThreeWayMatchGuardTest(unittest.TestCase):
    def _base_po(self) -> dict:
        return {
            "po_id": "po_ind_001",
            "ancillary_allowance_minor": 10_000,
            "lines": [
                {"sku": "sku_servo_a", "qty_ordered": 10, "unit_price_minor": 50_000},
            ],
        }

    def test_partial_shipment_three_way_match_approves_proportional_capture(self) -> None:
        res = verify_b2b_three_way_match_and_escrow(
            po_mandate=self._base_po(),
            grn_receipt={
                "lines": [{"sku": "sku_servo_a", "qty_delivered": 6, "qty_rejected_damaged": 0}]
            },
            e_invoice={
                "invoice_id": "inv_part_01",
                "payout_endpoint_id": "acct_kyb_vendor_01",
                "ancillary_charges_minor": 6_000,
                "lines": [{"sku": "sku_servo_a", "qty_invoiced": 6, "unit_price_minor": 50_000}],
            },
            vendor_master={
                "kyb_verified_endpoint_id": "acct_kyb_vendor_01",
                "ofac_sanctioned": False,
            },
        )
        self.assertTrue(res.settlement_approved)
        self.assertEqual(res.decision_code, "THREE_WAY_MATCH_PARTIAL_CAPTURE_APPROVED")
        self.assertEqual(res.approved_partial_capture_minor, 306_000)
        self.assertEqual(res.remaining_escrow_hold_minor, 204_000)

    def test_unfulfilled_backorder_capture_is_blocked(self) -> None:
        res = verify_b2b_three_way_match_and_escrow(
            po_mandate=self._base_po(),
            grn_receipt={
                "lines": [{"sku": "sku_servo_a", "qty_delivered": 4, "qty_rejected_damaged": 0}]
            },
            e_invoice={
                "invoice_id": "inv_premature_full",
                "payout_endpoint_id": "acct_kyb_vendor_01",
                "ancillary_charges_minor": 10_000,
                "lines": [{"sku": "sku_servo_a", "qty_invoiced": 10, "unit_price_minor": 50_000}],
            },
            vendor_master={
                "kyb_verified_endpoint_id": "acct_kyb_vendor_01",
                "ofac_sanctioned": False,
            },
        )
        self.assertFalse(res.settlement_approved)
        self.assertEqual(res.decision_code, "UNFULFILLED_BACKORDER_CAPTURE_VIOLATION")
        self.assertEqual(res.approved_partial_capture_minor, 0)

    def test_damaged_goods_overbilling_and_unit_price_drift_are_blocked(self) -> None:
        res = verify_b2b_three_way_match_and_escrow(
            po_mandate=self._base_po(),
            grn_receipt={
                "lines": [{"sku": "sku_servo_a", "qty_delivered": 10, "qty_rejected_damaged": 2}]
            },
            e_invoice={
                "invoice_id": "inv_damaged_overbill",
                "payout_endpoint_id": "acct_kyb_vendor_01",
                "ancillary_charges_minor": 10_000,
                "lines": [{"sku": "sku_servo_a", "qty_invoiced": 9, "unit_price_minor": 51_000}],
            },
            vendor_master={
                "kyb_verified_endpoint_id": "acct_kyb_vendor_01",
                "ofac_sanctioned": False,
            },
        )
        self.assertFalse(res.settlement_approved)
        self.assertEqual(res.decision_code, "THREE_WAY_MATCH_QTY_OVERBILL")
        self.assertTrue(
            any("THREE_WAY_MATCH_UNIT_PRICE_DRIFT" in r for r in res.reasons)
        )

    def test_beneficiary_endpoint_hijack_and_sanctions_hit_are_blocked(self) -> None:
        bec_res = verify_b2b_three_way_match_and_escrow(
            po_mandate=self._base_po(),
            grn_receipt={
                "lines": [{"sku": "sku_servo_a", "qty_delivered": 10, "qty_rejected_damaged": 0}]
            },
            e_invoice={
                "invoice_id": "inv_bec_spoof",
                "payout_endpoint_id": "acct_attacker_999",
                "ancillary_charges_minor": 10_000,
                "lines": [{"sku": "sku_servo_a", "qty_invoiced": 10, "unit_price_minor": 50_000}],
            },
            vendor_master={
                "kyb_verified_endpoint_id": "acct_kyb_vendor_01",
                "ofac_sanctioned": False,
            },
        )
        self.assertFalse(bec_res.settlement_approved)
        self.assertEqual(bec_res.decision_code, "BENEFICIARY_ENDPOINT_HIJACK_BLOCKED")

        sanc_res = verify_b2b_three_way_match_and_escrow(
            po_mandate=self._base_po(),
            grn_receipt={
                "lines": [{"sku": "sku_servo_a", "qty_delivered": 10, "qty_rejected_damaged": 0}]
            },
            e_invoice={
                "invoice_id": "inv_sanctioned",
                "payout_endpoint_id": "acct_kyb_vendor_01",
                "ancillary_charges_minor": 10_000,
                "lines": [{"sku": "sku_servo_a", "qty_invoiced": 10, "unit_price_minor": 50_000}],
            },
            vendor_master={
                "kyb_verified_endpoint_id": "acct_kyb_vendor_01",
                "ofac_sanctioned": True,
            },
        )
        self.assertFalse(sanc_res.settlement_approved)
        self.assertEqual(sanc_res.decision_code, "SANCTIONS_SCREENING_HIT")

    def test_dynamic_discounting_2_10_net_30_calculates_37_24_pct_implied_apr(self) -> None:
        disc = evaluate_dynamic_discounting_apr(
            gross_invoice_minor=1_000_000,
            discount_rate_bps=200,  # 2%
            discount_day=10,
            net_due_day=30,
            treasury_hurdle_apr_pct=8.0,
            three_way_match_verified=True,
        )
        self.assertTrue(disc.take_early_discount)
        self.assertEqual(disc.decision_code, "ACCELERATE_SETTLEMENT_CAPTURE_DISCOUNT")
        self.assertAlmostEqual(disc.implied_apr_pct, 37.2449, places=4)
        self.assertEqual(disc.savings_minor, 20_000)
        self.assertEqual(disc.discounted_settlement_minor, 980_000)

    def test_demo_scenarios_run_cleanly(self) -> None:
        demos = run_demo_scenarios()
        self.assertEqual(len(demos), 3)
        self.assertTrue(demos[0]["settlement_approved"])
        self.assertFalse(demos[1]["settlement_approved"])
        self.assertTrue(demos[2]["take_early_discount"])


if __name__ == "__main__":
    unittest.main()
