"""Unit tests for Stage 11 Sealed-Bid Vickrey RFQ, B2B VAT Reverse-Charge & RMA Return Guard."""

from __future__ import annotations

import unittest

from lab.reverse_auction_tax_returns_guard import (
    compute_rfq_bid_commitment,
    run_demo_scenarios,
    verify_rma_return_and_restocking_guard,
    verify_sealed_rfq_and_tax_nexus,
)


class ReverseAuctionTaxReturnsGuardTest(unittest.TestCase):
    def _sample_bids(self, rfq_id: str = "rfq_01") -> list[dict]:
        return [
            {
                "seller_id": "seller_low",
                "all_in_price_minor": 30_000,
                "salt": "s_low",
                "commitment_sha256": compute_rfq_bid_commitment(
                    "seller_low", rfq_id, 30_000, "s_low"
                ),
            },
            {
                "seller_id": "seller_second",
                "all_in_price_minor": 34_500,
                "salt": "s_sec",
                "commitment_sha256": compute_rfq_bid_commitment(
                    "seller_second", rfq_id, 34_500, "s_sec"
                ),
            },
        ]

    def test_sealed_rfq_vickrey_winner_and_b2b_reverse_charge_pass(self) -> None:
        res = verify_sealed_rfq_and_tax_nexus(
            rfq_spec={"rfq_id": "rfq_01", "reserve_price_minor": 40_000},
            bids=self._sample_bids("rfq_01"),
            checkout_quote={
                "seller_id": "seller_low",
                "pre_tax_all_in_minor": 30_000,
                "tax_charged_minor": 0,
            },
            tax_context={
                "seller_country": "DE",
                "buyer_country": "NL",
                "buyer_is_b2b": True,
                "buyer_vat_verified": True,
                "seller_tax_registration_valid": True,
                "statutory_tax_rate_bps": 1900,
            },
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.decision_code, "SEALED_RFQ_AND_TAX_VERIFIED")
        self.assertEqual(res.winning_seller_id, "seller_low")
        self.assertEqual(res.winning_bid_all_in_minor, 30_000)
        self.assertEqual(res.vickrey_clearing_cap_minor, 34_500)

    def test_commit_reveal_hash_tampering_is_rejected(self) -> None:
        tampered_bids = [
            {
                "seller_id": "seller_tamper",
                "all_in_price_minor": 28_000,  # altered after commit of 35_000
                "salt": "s_tamp",
                "commitment_sha256": compute_rfq_bid_commitment(
                    "seller_tamper", "rfq_01", 35_000, "s_tamp"
                ),
            }
        ]
        res = verify_sealed_rfq_and_tax_nexus(
            rfq_spec={"rfq_id": "rfq_01", "reserve_price_minor": 40_000},
            bids=tampered_bids,
            checkout_quote={
                "seller_id": "seller_tamper",
                "pre_tax_all_in_minor": 28_000,
                "tax_charged_minor": 0,
            },
            tax_context={
                "seller_country": "US",
                "buyer_country": "US",
                "buyer_is_b2b": False,
                "buyer_vat_verified": False,
                "seller_tax_registration_valid": True,
                "statutory_tax_rate_bps": 0,
            },
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.decision_code, "RFQ_COMMIT_REVEAL_HASH_MISMATCH")

    def test_bait_and_switch_surcharge_and_b2b_vat_overcollection_are_blocked(self) -> None:
        res = verify_sealed_rfq_and_tax_nexus(
            rfq_spec={"rfq_id": "rfq_01", "reserve_price_minor": 40_000},
            bids=self._sample_bids("rfq_01"),
            checkout_quote={
                "seller_id": "seller_low",
                "pre_tax_all_in_minor": 32_500,  # $25.00 hidden surcharge
                "tax_charged_minor": 6_500,      # illegal VAT on cross-border B2B reverse charge
            },
            tax_context={
                "seller_country": "DE",
                "buyer_country": "NL",
                "buyer_is_b2b": True,
                "buyer_vat_verified": True,
                "seller_tax_registration_valid": True,
                "statutory_tax_rate_bps": 2000,
            },
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.decision_code, "BAIT_SWITCH_SURCHARGE_INJECTION")
        self.assertTrue(
            any("INVALID_B2B_VAT_REVERSE_CHARGE_OVERCOLLECTION" in r for r in res.reasons)
        )

    def test_unregistered_seller_tax_collection_is_blocked(self) -> None:
        res = verify_sealed_rfq_and_tax_nexus(
            rfq_spec={"rfq_id": "rfq_01", "reserve_price_minor": 40_000},
            bids=self._sample_bids("rfq_01"),
            checkout_quote={
                "seller_id": "seller_low",
                "pre_tax_all_in_minor": 30_000,
                "tax_charged_minor": 2_400,
            },
            tax_context={
                "seller_country": "US",
                "buyer_country": "US",
                "buyer_is_b2b": False,
                "buyer_vat_verified": False,
                "seller_tax_registration_valid": False,
                "statutory_tax_rate_bps": 800,
            },
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.decision_code, "UNREGISTERED_TAX_COLLECTION_BLOCKED")

    def test_rma_blocks_illegal_snad_restocking_fee_and_box_swap_fraud(self) -> None:
        snad_fee = verify_rma_return_and_restocking_guard(
            {
                "rma_id": "rma_01",
                "return_reason": "DEFECTIVE_OR_SNAD",
                "paid_item_amount_minor": 50_000,
                "proposed_restocking_fee_minor": 5_000,
                "ucp_disclosed_max_restocking_bps": 1500,
                "shipped_serial_sha256": "sha256:sn_ok",
                "returned_serial_sha256": "sha256:sn_ok",
                "shipped_weight_grams": 800.0,
                "returned_weight_grams": 798.0,
            }
        )
        self.assertFalse(snad_fee.refund_approved)
        self.assertEqual(snad_fee.decision_code, "ILLEGAL_SNAD_RESTOCKING_FEE_BLOCKED")

        box_swap = verify_rma_return_and_restocking_guard(
            {
                "rma_id": "rma_02",
                "return_reason": "BUYER_REMORSE",
                "paid_item_amount_minor": 50_000,
                "proposed_restocking_fee_minor": 5_000,
                "ucp_disclosed_max_restocking_bps": 1500,
                "shipped_serial_sha256": "sha256:sn_original",
                "returned_serial_sha256": "sha256:sn_counterfeit",
                "shipped_weight_grams": 800.0,
                "returned_weight_grams": 120.0,
            }
        )
        self.assertFalse(box_swap.refund_approved)
        self.assertEqual(box_swap.decision_code, "RMA_SERIAL_OR_WEIGHT_FRAUD_BLOCKED")

    def test_compliant_remorse_return_within_disclosed_restocking_cap_is_approved(self) -> None:
        ok_rma = verify_rma_return_and_restocking_guard(
            {
                "rma_id": "rma_03",
                "return_reason": "BUYER_REMORSE",
                "paid_item_amount_minor": 50_000,
                "proposed_restocking_fee_minor": 5_000,  # 10% <= 15% cap
                "ucp_disclosed_max_restocking_bps": 1500,
                "shipped_serial_sha256": "sha256:sn_original",
                "returned_serial_sha256": "sha256:sn_original",
                "shipped_weight_grams": 800.0,
                "returned_weight_grams": 795.0,
            }
        )
        self.assertTrue(ok_rma.refund_approved)
        self.assertEqual(ok_rma.approved_refund_minor, 45_000)

    def test_demo_scenarios_execute_cleanly(self) -> None:
        demos = run_demo_scenarios()
        self.assertEqual(len(demos), 3)
        self.assertTrue(demos[0]["allowed"])
        self.assertFalse(demos[1]["allowed"])
        self.assertFalse(demos[2]["refund_approved"])


if __name__ == "__main__":
    unittest.main()
