"""Unit tests for Stage 19 Promo Coupon Stacking, Affiliate Attribution & Loyalty Clawback Guard."""

from __future__ import annotations

import unittest

from lab.loyalty_affiliate_promo_stacking_guard import (
    evaluate_loyalty_points_escrow_and_return_clawback,
    evaluate_promo_coupon_stacking_invariant,
    verify_cryptographic_affiliate_attribution_chain,
)


class LoyaltyAffiliatePromoStackingGuardTestSuite(unittest.TestCase):
    def test_promo_stack_blocks_floor_margin_breach_and_exclusivity_conflict(self) -> None:
        floor_breach = evaluate_promo_coupon_stacking_invariant(
            {
                "order_subtotal_minor": 10000,
                "cogs_minor": 7200,
                "merchant_floor_margin_bps": 1500,
                "buyer_principal_did": "did:web:buyer.example",
                "referrer_principal_did": "did:web:partner.example",
                "coupons": [
                    {"code": "WELCOME15", "discount_minor": 1500, "exclusivity_group": "G1", "stackable": True},
                    {"code": "FLASH10", "discount_minor": 1000, "exclusivity_group": "G2", "stackable": True},
                ],
            }
        )
        self.assertFalse(floor_breach.allowed)
        self.assertEqual(floor_breach.decision_code, "PROMO_STACK_EXCEEDS_FLOOR_MARGIN_BLOCKED")
        self.assertEqual(floor_breach.post_discount_margin_bps, 300)

        conflict = evaluate_promo_coupon_stacking_invariant(
            {
                "order_subtotal_minor": 10000,
                "cogs_minor": 5000,
                "merchant_floor_margin_bps": 1500,
                "coupons": [
                    {"code": "SPRING10", "discount_minor": 1000, "exclusivity_group": "SEASONAL", "stackable": True},
                    {"code": "SUMMER15", "discount_minor": 1500, "exclusivity_group": "SEASONAL", "stackable": True},
                ],
            }
        )
        self.assertFalse(conflict.allowed)
        self.assertEqual(conflict.decision_code, "EXCLUSIVITY_GROUP_CONFLICT")
        self.assertEqual(conflict.conflicting_exclusivity_group, "SEASONAL")

    def test_promo_stack_blocks_sybil_self_referral_ring_and_admits_valid(self) -> None:
        sybil = evaluate_promo_coupon_stacking_invariant(
            {
                "order_subtotal_minor": 10000,
                "cogs_minor": 5000,
                "merchant_floor_margin_bps": 1500,
                "buyer_principal_did": "did:web:alice.example",
                "referrer_principal_did": "did:web:alice.example",
                "coupons": [{"code": "REFERRAL20", "discount_minor": 2000, "exclusivity_group": "REF"}],
            }
        )
        self.assertFalse(sybil.allowed)
        self.assertEqual(sybil.decision_code, "SELF_REFERRAL_SYBIL_RING_BLOCKED")
        self.assertTrue(sybil.sybil_self_referral_detected)

        valid = evaluate_promo_coupon_stacking_invariant(
            {
                "order_subtotal_minor": 10000,
                "cogs_minor": 6000,
                "merchant_floor_margin_bps": 2000,
                "buyer_principal_did": "did:web:alice.example",
                "referrer_principal_did": "did:web:bob.example",
                "coupons": [
                    {"code": "PARTNER10", "discount_minor": 1000, "exclusivity_group": "G1", "stackable": True},
                    {"code": "MEMBER5", "discount_minor": 500, "exclusivity_group": "G2", "stackable": True},
                ],
            }
        )
        self.assertTrue(valid.allowed)
        self.assertEqual(valid.decision_code, "PROMO_STACK_INVARIANT_VERIFIED")
        self.assertEqual(valid.post_discount_margin_bps, 2500)

    def test_affiliate_attribution_blocks_last_second_hijack_and_conserves_split(self) -> None:
        hijacked = verify_cryptographic_affiliate_attribution_chain(
            {
                "order_id": "ord_19_hijack",
                "total_commission_minor": 1000,
                "checkout_epoch": 5_000,
                "hijack_window_seconds": 5,
                "attribution_hops": [
                    {
                        "hop_id": "hop_discovery",
                        "timestamp_epoch": 4_600,
                        "jws_signature_valid": True,
                        "verified_interaction_digest": "sha256:disc_ok",
                        "weight_bps": 7000,
                    },
                    {
                        "hop_id": "hop_malicious_plugin",
                        "timestamp_epoch": 4_998,
                        "jws_signature_valid": True,
                        "verified_interaction_digest": "",
                        "weight_bps": 3000,
                    },
                ],
            }
        )
        self.assertFalse(hijacked.allowed)
        self.assertEqual(hijacked.decision_code, "LAST_SECOND_ATTRIBUTION_HIJACK_BLOCKED")
        self.assertEqual(hijacked.hijacked_hop_id, "hop_malicious_plugin")

        verified = verify_cryptographic_affiliate_attribution_chain(
            {
                "order_id": "ord_19_valid",
                "total_commission_minor": 1000,
                "checkout_epoch": 5_000,
                "hijack_window_seconds": 5,
                "attribution_hops": [
                    {
                        "hop_id": "hop_1",
                        "timestamp_epoch": 4_200,
                        "jws_signature_valid": True,
                        "verified_interaction_digest": "sha256:h1",
                        "weight_bps": 3333,
                    },
                    {
                        "hop_id": "hop_2",
                        "timestamp_epoch": 4_500,
                        "jws_signature_valid": True,
                        "verified_interaction_digest": "sha256:h2",
                        "weight_bps": 3333,
                    },
                    {
                        "hop_id": "hop_3",
                        "timestamp_epoch": 4_800,
                        "jws_signature_valid": True,
                        "verified_interaction_digest": "sha256:h3",
                        "weight_bps": 3334,
                    },
                ],
            }
        )
        self.assertTrue(verified.allowed)
        self.assertEqual(verified.decision_code, "AFFILIATE_ATTRIBUTION_SPLIT_VERIFIED")
        self.assertEqual(verified.conservation_delta_minor, 0)
        self.assertEqual(sum(verified.hop_allocations_minor.values()), 1000)

    def test_loyalty_points_escrow_and_return_deficit_deduction(self) -> None:
        deficit = evaluate_loyalty_points_escrow_and_return_clawback(
            {
                "order_id": "ord_19_ret",
                "order_total_minor": 20000,
                "gross_return_amount_minor": 20000,
                "earned_reward_minor": 2000,
                "buyer_available_reward_balance_minor": 500,
                "now_epoch": 1_760_950_000,
                "return_window_expires_epoch": 1_763_542_000,
            }
        )
        self.assertTrue(deficit.allowed)
        self.assertEqual(deficit.decision_code, "CASHBACK_DEFICIT_DEDUCTED_FROM_REFUND")
        self.assertEqual(deficit.revoked_reward_minor, 500)
        self.assertEqual(deficit.unrecovered_spent_deficit_minor, 1500)
        self.assertEqual(deficit.net_principal_refund_minor, 18500)

        clean_clawback = evaluate_loyalty_points_escrow_and_return_clawback(
            {
                "order_id": "ord_19_clean",
                "order_total_minor": 20000,
                "gross_return_amount_minor": 10000,
                "earned_reward_minor": 2000,
                "buyer_available_reward_balance_minor": 2000,
                "now_epoch": 1_760_950_000,
                "return_window_expires_epoch": 1_763_542_000,
            }
        )
        self.assertTrue(clean_clawback.allowed)
        self.assertEqual(clean_clawback.decision_code, "LOYALTY_POINTS_CLAWED_BACK")
        self.assertEqual(clean_clawback.revoked_reward_minor, 1000)
        self.assertEqual(clean_clawback.net_principal_refund_minor, 10000)


if __name__ == "__main__":
    unittest.main()
