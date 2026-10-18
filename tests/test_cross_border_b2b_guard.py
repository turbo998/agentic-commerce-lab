import unittest

from lab.cross_border_b2b_guard import (
    SellerSplitAllocation,
    evaluate_token_margin_circuit_breaker,
    main,
    run_demo,
    verify_connect_split_and_refund_conservation,
    verify_cross_border_incoterms_and_hs,
)


class CrossBorderB2BGuardTests(unittest.TestCase):
    def test_connect_multi_seller_split_fx_and_reverse_refund_conservation(self) -> None:
        # Multi-seller split must use separate_charges_and_transfers
        wrong_mode = verify_connect_split_and_refund_conservation(
            charge_type="destination",
            seller_profile_owner="platform",
            has_on_behalf_of=False,
            stripe_account_header=None,
            connected_account_id="acct_1",
            buyer_charge_minor=50000,
            allocations=[
                SellerSplitAllocation("acct_1", 30000, 27000, 3000, "JPY", "150.00", "150.10"),
                SellerSplitAllocation("acct_2", 20000, 18000, 2000, "EUR", "0.9200", "0.9205"),
            ],
            now_epoch=100,
            fx_quote_expires_at=200,
        )
        self.assertFalse(wrong_mode.valid)
        self.assertEqual(
            wrong_mode.reason,
            "multi_seller_split_requires_separate_charges_and_transfers",
        )

        # Expired FX quote rejected
        expired_fx = verify_connect_split_and_refund_conservation(
            charge_type="separate_charges_and_transfers",
            seller_profile_owner="platform",
            has_on_behalf_of=False,
            stripe_account_header=None,
            connected_account_id="acct_1",
            buyer_charge_minor=30000,
            allocations=[
                SellerSplitAllocation("acct_1", 30000, 27000, 3000, "JPY", "150.00", "150.10"),
            ],
            now_epoch=250,
            fx_quote_expires_at=200,
        )
        self.assertFalse(expired_fx.valid)
        self.assertEqual(expired_fx.reason, "fx_quote_expired_requires_requote")

        # Excessive FX slippage rejected
        fx_slip = verify_connect_split_and_refund_conservation(
            charge_type="separate_charges_and_transfers",
            seller_profile_owner="platform",
            has_on_behalf_of=False,
            stripe_account_header=None,
            connected_account_id="acct_1",
            buyer_charge_minor=30000,
            allocations=[
                SellerSplitAllocation("acct_1", 30000, 27000, 3000, "JPY", "150.00", "152.50"),
            ],
            now_epoch=100,
            fx_quote_expires_at=200,
            max_fx_slippage_bps=50,
        )
        self.assertFalse(fx_slip.valid)
        self.assertEqual(fx_slip.reason, "fx_slippage_exceeds_locked_corridor")

        # Partial refund without reverse_transfer creates platform deficit -> blocked
        no_rev = verify_connect_split_and_refund_conservation(
            charge_type="destination",
            seller_profile_owner="connected_account",
            has_on_behalf_of=True,
            stripe_account_header=None,
            connected_account_id="acct_1",
            buyer_charge_minor=30000,
            allocations=[
                SellerSplitAllocation("acct_1", 30000, 27000, 3000, "JPY", "150.00", "150.10"),
            ],
            now_epoch=100,
            fx_quote_expires_at=200,
            refund_line_amount_minor=10000,
            refund_reverse_transfer=False,
        )
        self.assertFalse(no_rev.valid)
        self.assertEqual(no_rev.reason, "refund_without_reverse_transfer_creates_platform_deficit")
        self.assertEqual(no_rev.refund_platform_deficit_minor, 9000)

        # Valid multi-seller split with reverse_transfer=True
        valid_split = verify_connect_split_and_refund_conservation(
            charge_type="separate_charges_and_transfers",
            seller_profile_owner="platform",
            has_on_behalf_of=False,
            stripe_account_header=None,
            connected_account_id="acct_1",
            buyer_charge_minor=50000,
            allocations=[
                SellerSplitAllocation("acct_1", 30000, 27000, 3000, "JPY", "150.00", "150.20"),
                SellerSplitAllocation("acct_2", 20000, 18000, 2000, "EUR", "0.9200", "0.9210"),
            ],
            now_epoch=100,
            fx_quote_expires_at=200,
            refund_line_amount_minor=10000,
            refund_reverse_transfer=True,
            refund_application_fee=True,
        )
        self.assertTrue(valid_split.valid)
        self.assertEqual(valid_split.total_seller_transfers_minor, 45000)
        self.assertEqual(valid_split.total_application_fees_minor, 5000)

    def test_token_margin_circuit_breaker_across_rails(self) -> None:
        # Card rail + heavy token burn exceeds platform take -> trips FCB OPEN
        tripped = evaluate_token_margin_circuit_breaker(
            gross_transaction_usd="2.00",
            platform_take_rate_bps=1000,
            input_tokens=40000,
            output_tokens=6000,
            payment_rail="stripe_spt_card",
        )
        self.assertFalse(tripped.allowed)
        self.assertEqual(tripped.fcb_next_state, "OPEN")
        self.assertEqual(tripped.tripped_condition, "COST_ENVELOPE_EXCEEDED")

        # Switching to x402 Base USDC with cached tokens preserves positive net margin -> CLOSED
        healthy = evaluate_token_margin_circuit_breaker(
            gross_transaction_usd="2.00",
            platform_take_rate_bps=1000,  # $0.20 take
            input_tokens=4000,
            output_tokens=1000,
            cached_input_tokens=36000,
            payment_rail="x402_base_usdc",
        )
        self.assertTrue(healthy.allowed)
        self.assertEqual(healthy.fcb_next_state, "CLOSED")
        self.assertIsNone(healthy.tripped_condition)

        # MPP Tempo unaligned schedule forfeiture erodes tight micro-margin -> trips FCB OPEN
        mpp_eroded = evaluate_token_margin_circuit_breaker(
            gross_transaction_usd="0.043750",
            platform_take_rate_bps=5000,  # $0.021875 take, but $0.023750 forfeited to sub-cent!
            input_tokens=100,
            output_tokens=50,
            payment_rail="mpp_tempo_session",
            mpp_unit_price_usd="0.000350",
            mpp_units_per_settlement_cycle=50,
            mpp_total_units=125,
        )
        self.assertFalse(mpp_eroded.allowed)
        self.assertEqual(mpp_eroded.tripped_condition, "COST_ENVELOPE_EXCEEDED")

    def test_cross_border_incoterms_and_hs_code_guard(self) -> None:
        # Silent DDP -> DAP downgrade blocked
        downgrade = verify_cross_border_incoterms_and_hs(
            buyer_mandate_max_landed_minor=25000,
            buyer_requires_ddp=True,
            proposed_incoterm="DAP",
            catalog_hs_code="8471300100",
            proposed_hs_code="8471300100",
            fob_merchandise_minor=21000,
            freight_insurance_minor=2500,
            estimated_duty_tax_minor=3800,
            quoted_checkout_total_minor=23500,
        )
        self.assertFalse(downgrade.allowed)
        self.assertEqual(downgrade.reason, "incoterm_downgrade_from_ddp_forbidden")
        self.assertEqual(downgrade.unpaid_import_liability_minor, 3800)

        # HS 6-digit subheading manipulation blocked
        hs_tamper = verify_cross_border_incoterms_and_hs(
            buyer_mandate_max_landed_minor=30000,
            buyer_requires_ddp=True,
            proposed_incoterm="DDP",
            catalog_hs_code="6403990000",  # Footwear (high duty)
            proposed_hs_code="4901990000",  # Printed books (0% duty hallucination)
            fob_merchandise_minor=21000,
            freight_insurance_minor=2500,
            estimated_duty_tax_minor=0,
            quoted_checkout_total_minor=23500,
        )
        self.assertFalse(hs_tamper.allowed)
        self.assertEqual(hs_tamper.reason, "hs_subheading_mismatch_with_catalog_authority")

        # Valid DDP within buyer mandate ceiling
        ddp_ok = verify_cross_border_incoterms_and_hs(
            buyer_mandate_max_landed_minor=28000,
            buyer_requires_ddp=True,
            proposed_incoterm="DDP",
            catalog_hs_code="8471300100",
            proposed_hs_code="8471309900",  # Same 6-digit WCO subheading 847130, country suffix differs
            fob_merchandise_minor=21000,
            freight_insurance_minor=2500,
            estimated_duty_tax_minor=3800,
            quoted_checkout_total_minor=27300,
        )
        self.assertTrue(ddp_ok.allowed)
        self.assertEqual(ddp_ok.landed_total_minor, 27300)
        self.assertEqual(ddp_ok.unpaid_import_liability_minor, 0)

    def test_cli_and_demo_run_cleanly(self) -> None:
        summary = run_demo()
        self.assertTrue(summary["split_conservation_ok"])
        self.assertTrue(summary["refund_without_reverse_transfer_blocked"])
        self.assertTrue(summary["token_margin_fcb_tripped"])
        self.assertTrue(summary["incoterm_downgrade_blocked"])
        self.assertEqual(main([]), 0)


if __name__ == "__main__":
    unittest.main()
