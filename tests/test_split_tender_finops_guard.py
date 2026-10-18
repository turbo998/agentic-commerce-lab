"""Unit tests for Stage 12 Split-Tender Reverse Waterfall, Anti-Cash-Out & Enterprise FinOps Guard."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.split_tender_finops_guard import (
    main,
    run_enterprise_procurement_benchmark_suite,
    verify_enterprise_cost_center_chargeback,
    verify_split_tender_waterfall_and_clawback,
    write_enterprise_procurement_report_artifacts,
)


class SplitTenderFinOpsGuardTest(unittest.TestCase):
    def test_compliant_split_tender_reverse_waterfall_caps_open_loop_refund(self) -> None:
        res = verify_split_tender_waterfall_and_clawback(
            {
                "order_id": "ord_ok_01",
                "gross_order_minor": 50_000,
                "promo_discount_minor": 5_000,
                "max_promo_discount_cap_minor": 10_000,
                "mutually_exclusive_coupons_stacked": False,
                "closed_loop_tender_minor": 30_000,
                "captured_open_loop_minor": 15_000,
                "refund_requested_minor": 25_000,
                "proposed_open_loop_refund_minor": 15_000,
                "proposed_closed_loop_refund_minor": 10_000,
                "earned_loyalty_value_minor": 1_000,
                "redeemed_unvested_loyalty_minor": 0,
                "clawback_deducted_from_refund_minor": 0,
            }
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.decision_code, "SPLIT_TENDER_WATERFALL_VERIFIED")
        self.assertEqual(res.approved_open_loop_refund_minor, 15_000)
        self.assertEqual(res.approved_closed_loop_refund_minor, 10_000)

    def test_closed_loop_gift_card_cash_out_to_open_loop_is_blocked(self) -> None:
        res = verify_split_tender_waterfall_and_clawback(
            {
                "order_id": "ord_launder_01",
                "gross_order_minor": 50_000,
                "promo_discount_minor": 5_000,
                "max_promo_discount_cap_minor": 10_000,
                "mutually_exclusive_coupons_stacked": False,
                "closed_loop_tender_minor": 35_000,
                "captured_open_loop_minor": 10_000,
                "refund_requested_minor": 45_000,
                "proposed_open_loop_refund_minor": 45_000,  # tries to cash out $350 gift card to card/USDC
                "proposed_closed_loop_refund_minor": 0,
            }
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.decision_code, "CLOSED_LOOP_CASH_OUT_LAUNDERING_BLOCKED")

    def test_mutually_exclusive_coupon_stacking_and_loyalty_clawback_deficit_are_blocked(self) -> None:
        res = verify_split_tender_waterfall_and_clawback(
            {
                "order_id": "ord_stack_clawback",
                "gross_order_minor": 20_000,
                "promo_discount_minor": 8_000,
                "max_promo_discount_cap_minor": 5_000,
                "mutually_exclusive_coupons_stacked": True,
                "closed_loop_tender_minor": 2_000,
                "captured_open_loop_minor": 10_000,
                "refund_requested_minor": 12_000,
                "proposed_open_loop_refund_minor": 10_000,
                "proposed_closed_loop_refund_minor": 2_000,
                "earned_loyalty_value_minor": 1_500,
                "redeemed_unvested_loyalty_minor": 1_500,
                "clawback_deducted_from_refund_minor": 0,
            }
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.decision_code, "MUTUALLY_EXCLUSIVE_COUPON_STACKING")
        self.assertEqual(res.unrecovered_loyalty_clawback_minor, 1_500)
        self.assertTrue(any("LOYALTY_EARN_CLAWBACK_DEFICIT" in r for r in res.reasons))

    def test_enterprise_cost_center_chargeback_approves_within_unencumbered_budget(self) -> None:
        res = verify_enterprise_cost_center_chargeback(
            {
                "requisition_id": "req_ok_01",
                "merchandise_minor": 80_000,
                "tax_minor": 8_000,
                "agent_token_overhead_minor": 2_000,  # total = 90_000
                "cost_centers": [
                    {
                        "cost_center_id": "CC_ENG",
                        "split_bps": 5000,
                        "budget_cap_minor": 100_000,
                        "existing_encumbrance_minor": 20_000,
                        "actual_spent_minor": 10_000,
                    },
                    {
                        "cost_center_id": "CC_PROD",
                        "split_bps": 5000,
                        "budget_cap_minor": 100_000,
                        "existing_encumbrance_minor": 10_000,
                        "actual_spent_minor": 20_000,
                    },
                ],
            }
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.decision_code, "COST_CENTER_ENCUMBRANCE_AND_GL_BALANCED")
        self.assertTrue(res.gl_balanced)
        self.assertEqual(res.allocations_minor["CC_ENG"], 45_000)
        self.assertEqual(res.allocations_minor["CC_PROD"], 45_000)

    def test_enterprise_cost_center_encumbrance_overflow_and_bps_mismatch_are_blocked(self) -> None:
        res = verify_enterprise_cost_center_chargeback(
            {
                "requisition_id": "req_over_01",
                "merchandise_minor": 90_000,
                "tax_minor": 8_000,
                "agent_token_overhead_minor": 2_000,  # total = 100_000
                "cost_centers": [
                    {
                        "cost_center_id": "CC_AI",
                        "split_bps": 6000,  # 60,000 needed, only 50,000 available
                        "budget_cap_minor": 100_000,
                        "existing_encumbrance_minor": 30_000,
                        "actual_spent_minor": 20_000,
                    },
                    {
                        "cost_center_id": "CC_OPS",
                        "split_bps": 4000,
                        "budget_cap_minor": 100_000,
                        "existing_encumbrance_minor": 0,
                        "actual_spent_minor": 0,
                    },
                ],
            }
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.decision_code, "COST_CENTER_ENCUMBRANCE_EXCEEDED")

    def test_twelve_scenario_procurement_benchmark_and_seven_card_report(self) -> None:
        suite = run_enterprise_procurement_benchmark_suite()
        self.assertEqual(suite["total_scenarios"], 12)
        self.assertEqual(suite["ai_native_passed"], 12)
        self.assertEqual(suite["classic_3tier_passed"], 1)

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "enterprise-procurement-bench"
            json_p, html_p = write_enterprise_procurement_report_artifacts(out_dir)
            self.assertTrue(json_p.exists())
            self.assertTrue(html_p.exists())
            html_text = html_p.read_text(encoding="utf-8")
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", html_text)
            for idx in range(1, 8):
                self.assertIn(f"Card {idx} of 7", html_text)
            self.assertEqual(main(["--output-dir", str(out_dir)]), 0)


if __name__ == "__main__":
    unittest.main()
