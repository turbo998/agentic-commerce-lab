"""Unit tests for Stage 22 Agentic Auction, Consortium Group-Buying Escrow & Earnest-Bond Slashing Guard."""

from __future__ import annotations

import unittest

from lab.agentic_auction_consortium_clearing_guard import (
    evaluate_consortium_group_buying_tier_escrow,
    evaluate_vickrey_reverse_auction_clearing,
    verify_winner_commitment_earnest_bond_slash,
)


class AgenticAuctionConsortiumClearingGuardTests(unittest.TestCase):
    def test_vickrey_reverse_rfq_incentive_compatible_second_price_clearing(self) -> None:
        res = evaluate_vickrey_reverse_auction_clearing(
            {
                "auction_id": "rfq_01",
                "direction": "REVERSE",
                "reserve_price_minor": 150_000,
                "scheduled_close_epoch": 5_000,
                "anti_sniping_window_seconds": 15,
                "soft_close_extension_seconds": 30,
                "soft_close_already_extended": False,
                "shill_bid_self_dealing_detected": False,
                "collusion_ring_score": 0.15,
                "bids": [
                    {"bidder_id": "seller_a", "principal_id": "did:web:a", "bid_amount_minor": 115_000, "bid_epoch": 4_800},
                    {"bidder_id": "seller_b", "principal_id": "did:web:b", "bid_amount_minor": 122_000, "bid_epoch": 4_850},
                    {"bidder_id": "seller_c", "principal_id": "did:web:c", "bid_amount_minor": 135_000, "bid_epoch": 4_900},
                ],
            }
        )
        self.assertTrue(res.cleared)
        self.assertEqual(res.decision_code, "VICKREY_INCENTIVE_COMPATIBLE_CLEARED")
        self.assertEqual(res.winning_bidder_id, "seller_a")
        self.assertEqual(res.winning_bid_minor, 115_000)
        self.assertEqual(res.vickrey_clearing_price_minor, 122_000)

    def test_anti_sniping_soft_close_extension_and_collusion_blocking(self) -> None:
        sniped = evaluate_vickrey_reverse_auction_clearing(
            {
                "auction_id": "rfq_02",
                "direction": "REVERSE",
                "reserve_price_minor": 150_000,
                "scheduled_close_epoch": 5_000,
                "anti_sniping_window_seconds": 15,
                "soft_close_extension_seconds": 30,
                "soft_close_already_extended": False,
                "shill_bid_self_dealing_detected": False,
                "collusion_ring_score": 0.10,
                "bids": [
                    {"bidder_id": "seller_sniper", "principal_id": "did:web:s", "bid_amount_minor": 110_000, "bid_epoch": 4_992},
                ],
            }
        )
        self.assertFalse(sniped.cleared)
        self.assertEqual(sniped.decision_code, "ANTI_SNIPING_SOFT_CLOSE_EXTENDED")
        self.assertTrue(sniped.soft_close_extended)
        self.assertEqual(sniped.extended_close_epoch, 5_030)

        collusion = evaluate_vickrey_reverse_auction_clearing(
            {
                "auction_id": "rfq_03",
                "direction": "REVERSE",
                "reserve_price_minor": 150_000,
                "scheduled_close_epoch": 5_000,
                "shill_bid_self_dealing_detected": False,
                "collusion_ring_score": 0.91,
                "bids": [
                    {"bidder_id": "seller_ring1", "principal_id": "did:web:r1", "bid_amount_minor": 148_000, "bid_epoch": 4_500},
                ],
            }
        )
        self.assertFalse(collusion.cleared)
        self.assertEqual(collusion.decision_code, "BID_RIGGING_OR_SHILL_COLLUSION_BLOCKED")
        self.assertTrue(collusion.collusion_blocked)

    def test_consortium_group_buying_tier_unlock_and_exact_rebate_conservation(self) -> None:
        settled = evaluate_consortium_group_buying_tier_escrow(
            {
                "consortium_id": "grp_100",
                "moq_required_qty": 100,
                "base_unit_price_minor": 1_000,
                "volume_tiers": [
                    {"min_qty": 50, "unit_price_minor": 900},
                    {"min_qty": 100, "unit_price_minor": 780},
                ],
                "participants": [
                    {"buyer_id": "agent_1", "quantity": 60, "initial_hold_minor": 60_000},
                    {"buyer_id": "agent_2", "quantity": 50, "initial_hold_minor": 50_000},
                ],
            }
        )
        self.assertTrue(settled.settled)
        self.assertEqual(settled.decision_code, "GROUP_TIER_UNLOCKED_REBATE_SETTLED")
        self.assertEqual(settled.unlocked_unit_price_minor, 780)
        self.assertEqual(settled.total_final_charges_minor, 85_800)
        self.assertEqual(settled.total_rebates_minor, 24_200)
        self.assertEqual(
            settled.total_final_charges_minor + settled.total_rebates_minor,
            settled.total_initial_holds_minor,
        )
        self.assertTrue(settled.conservation_verified)

    def test_consortium_moq_not_met_auto_releases_escrow(self) -> None:
        moq_fail = evaluate_consortium_group_buying_tier_escrow(
            {
                "consortium_id": "grp_under_moq",
                "moq_required_qty": 100,
                "base_unit_price_minor": 1_000,
                "volume_tiers": [{"min_qty": 100, "unit_price_minor": 780}],
                "participants": [
                    {"buyer_id": "agent_1", "quantity": 35, "initial_hold_minor": 35_000},
                    {"buyer_id": "agent_2", "quantity": 40, "initial_hold_minor": 40_000},
                ],
            }
        )
        self.assertFalse(moq_fail.settled)
        self.assertEqual(moq_fail.decision_code, "MOQ_NOT_MET_ESCROW_AUTO_RELEASED")
        self.assertEqual(moq_fail.total_final_charges_minor, 0)
        self.assertEqual(moq_fail.total_rebates_minor, 75_000)

    def test_winner_default_earnest_bond_slash_and_runner_up_fallback(self) -> None:
        slashed = verify_winner_commitment_earnest_bond_slash(
            {
                "auction_id": "rfq_default_01",
                "winner_bidder_id": "griefer_agent",
                "winner_settled_within_ttl": False,
                "winner_earnest_bond_minor": 20_000,
                "runner_up_bidder_id": "honest_runner_up",
                "fallback_clearing_price_minor": 125_000,
            }
        )
        self.assertTrue(slashed.default_handled)
        self.assertEqual(slashed.decision_code, "WINNER_DEFAULT_EARNEST_BOND_SLASHED")
        self.assertEqual(slashed.fallback_status, "SECOND_PRICE_FALLBACK_AWARDED")
        self.assertEqual(slashed.slashed_bond_minor, 20_000)
        self.assertEqual(slashed.fallback_awarded_bidder_id, "honest_runner_up")


if __name__ == "__main__":
    unittest.main()
