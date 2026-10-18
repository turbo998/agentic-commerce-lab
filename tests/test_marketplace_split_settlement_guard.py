"""Unit tests for Stage 14 Multi-Party Marketplace Split Settlement, KYB Rolling Reserve & Clawback Waterfall Guard."""

from __future__ import annotations

import unittest

from lab.marketplace_split_settlement_guard import (
    allocate_by_largest_remainder,
    evaluate_seller_kyb_rolling_reserve,
    evaluate_split_settlement_invariant,
    execute_negative_balance_clawback_waterfall,
    main,
)


class MarketplaceSplitSettlementGuardTestSuite(unittest.TestCase):
    def test_largest_remainder_eliminates_rounding_drift_and_verifies_split_conservation(self) -> None:
        allocs = allocate_by_largest_remainder(100, [1, 1, 1])
        self.assertEqual(allocs, (34, 33, 33))
        self.assertEqual(sum(allocs), 100)

        valid = evaluate_split_settlement_invariant(
            {
                "order_id": "ord_mkt_01",
                "gross_amount_minor": 10_000,
                "seller_net_splits_minor": [2_834, 2_833, 2_833],
                "platform_commission_minor": 800,
                "tax_withholding_minor": 200,
                "rolling_reserve_hold_minor": 500,
                "shared_pool_to_allocate_minor": 8_500,
                "seller_gross_weights_minor": [1, 1, 1],
                "claimed_pro_rata_allocations_minor": [2_834, 2_833, 2_833],
            }
        )
        self.assertTrue(valid.allowed)
        self.assertEqual(valid.decision_code, "SPLIT_SETTLEMENT_CONSERVATION_VERIFIED")
        self.assertEqual(valid.conservation_delta_minor, 0)

    def test_blocks_one_cent_rounding_drift_and_allocation_mismatch(self) -> None:
        drift = evaluate_split_settlement_invariant(
            {
                "order_id": "ord_mkt_02",
                "gross_amount_minor": 10_000,
                "seller_net_splits_minor": [2_833, 2_833, 2_833],  # missing 1 cent
                "platform_commission_minor": 800,
                "tax_withholding_minor": 200,
                "rolling_reserve_hold_minor": 500,
            }
        )
        self.assertFalse(drift.allowed)
        self.assertEqual(drift.decision_code, "SPLIT_SETTLEMENT_CONSERVATION_DRIFT")
        self.assertEqual(drift.conservation_delta_minor, 1)

        bad_pro_rata = evaluate_split_settlement_invariant(
            {
                "order_id": "ord_mkt_03",
                "gross_amount_minor": 10_000,
                "seller_net_splits_minor": [2_835, 2_833, 2_832],
                "platform_commission_minor": 800,
                "tax_withholding_minor": 200,
                "rolling_reserve_hold_minor": 500,
                "shared_pool_to_allocate_minor": 8_500,
                "seller_gross_weights_minor": [1, 1, 1],
                "claimed_pro_rata_allocations_minor": [2_835, 2_833, 2_832],
            }
        )
        self.assertFalse(bad_pro_rata.allowed)
        self.assertEqual(bad_pro_rata.decision_code, "LARGEST_REMAINDER_ALLOCATION_MISMATCH")

    def test_escalates_rolling_reserve_for_vamp_dispute_and_gmv_bustout_velocity(self) -> None:
        elevated_15 = evaluate_seller_kyb_rolling_reserve(
            {
                "seller_id": "acct_vamp_warn",
                "kyb_verified": True,
                "dispute_rate_bps": 72,  # > 65 bps VAMP warning
                "gmv_velocity_multiple_30d": "1.8",
                "current_settlement_gross_minor": 100_000,
                "applied_reserve_bps": 500,
                "instant_payout_requested": True,
            }
        )
        self.assertFalse(elevated_15.payouts_allowed)
        self.assertTrue(elevated_15.instant_payout_frozen)
        self.assertEqual(elevated_15.recommended_reserve_bps, 1500)
        self.assertEqual(
            elevated_15.decision_code,
            "ROLLING_RESERVE_ESCALATED_15PCT_INSTANT_PAYOUT_FROZEN",
        )

        bustout_25 = evaluate_seller_kyb_rolling_reserve(
            {
                "seller_id": "acct_bustout",
                "kyb_verified": True,
                "dispute_rate_bps": 80,
                "gmv_velocity_multiple_30d": "4.1",  # both VAMP > 65 bps and velocity > 3.5x
                "current_settlement_gross_minor": 100_000,
                "applied_reserve_bps": 1500,
                "instant_payout_requested": False,
            }
        )
        self.assertFalse(bustout_25.payouts_allowed)
        self.assertTrue(bustout_25.instant_payout_frozen)
        self.assertEqual(bustout_25.recommended_reserve_bps, 2500)
        self.assertEqual(
            bustout_25.decision_code,
            "ROLLING_RESERVE_ESCALATED_25PCT_BUST_OUT_GUARD",
        )

    def test_blocks_unverified_kyb_submerchant_payout(self) -> None:
        unverified = evaluate_seller_kyb_rolling_reserve(
            {
                "seller_id": "acct_no_kyb",
                "kyb_verified": False,
                "dispute_rate_bps": 10,
                "gmv_velocity_multiple_30d": "1.0",
                "current_settlement_gross_minor": 20_000,
            }
        )
        self.assertFalse(unverified.payouts_allowed)
        self.assertEqual(
            unverified.decision_code,
            "SUBMERCHANT_KYB_UNVERIFIED_PAYOUT_BLOCKED",
        )
        self.assertEqual(unverified.recommended_reserve_bps, 10_000)

    def test_clawback_recovery_waterfall_orders_sources_and_flags_uncovered_default(self) -> None:
        covered = execute_negative_balance_clawback_waterfall(
            {
                "seller_id": "acct_default_01",
                "refund_obligation_minor": 38_000,
                "pending_settlement_available_minor": 10_000,
                "rolling_reserve_pool_minor": 15_000,
                "linked_guarantor_available_minor": 8_000,
                "platform_risk_reserve_cap_minor": 10_000,
            }
        )
        self.assertTrue(covered.fully_covered)
        self.assertTrue(covered.seller_account_locked)
        self.assertEqual(covered.from_pending_settlement_minor, 10_000)
        self.assertEqual(covered.from_rolling_reserve_minor, 15_000)
        self.assertEqual(covered.from_linked_guarantor_minor, 8_000)
        self.assertEqual(covered.from_platform_risk_reserve_minor, 5_000)
        self.assertEqual(covered.uncovered_deficit_minor, 0)
        self.assertEqual(
            covered.decision_code,
            "CLAWBACK_COVERED_VIA_PLATFORM_RISK_BUFFER_ISOLATION",
        )

        uncovered = execute_negative_balance_clawback_waterfall(
            {
                "seller_id": "acct_default_02",
                "refund_obligation_minor": 60_000,
                "pending_settlement_available_minor": 10_000,
                "rolling_reserve_pool_minor": 15_000,
                "linked_guarantor_available_minor": 8_000,
                "platform_risk_reserve_cap_minor": 10_000,
            }
        )
        self.assertFalse(uncovered.fully_covered)
        self.assertEqual(uncovered.uncovered_deficit_minor, 17_000)
        self.assertEqual(
            uncovered.decision_code,
            "UNCOVERED_DEFAULT_EXCEEDS_PLATFORM_RISK_BUFFER",
        )

    def test_cli_main_returns_zero(self) -> None:
        self.assertEqual(main([]), 0)


if __name__ == "__main__":
    unittest.main()
