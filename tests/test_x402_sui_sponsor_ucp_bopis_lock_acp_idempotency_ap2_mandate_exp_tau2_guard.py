"""Unit tests for Stage 156 guardrails (SB-01..SB-16)."""

from __future__ import annotations

import unittest

from lab.x402_sui_sponsor_ucp_bopis_lock_acp_idempotency_ap2_mandate_exp_tau2_guard import (
    build_stage156_audit_summary,
    evaluate_acp_idempotency_key_fingerprint_and_lock_guard,
    evaluate_acp_spt_cryptogram_eci_and_arn_refund_guard,
    evaluate_ap2_customs_hs_code_and_de_minimis_guard,
    evaluate_ap2_mandate_clock_skew_and_inheritance_guard,
    evaluate_mcp_roots_symlink_sampling_and_cancel_guard,
    evaluate_stripe_proration_credit_note_and_efw_guard,
    evaluate_tau2_airline_cabin_upgrade_and_pnr_split_guard,
    evaluate_tau2_retail_price_match_and_roaming_proration_guard,
    evaluate_ucp_bopis_inventory_lock_and_pickup_guard,
    evaluate_ucp_multicurrency_fx_lock_guard,
    evaluate_ucp_trade_in_credit_escrow_guard,
    evaluate_visa_tap_forwarded_model_and_bin_routing_guard,
    evaluate_x402_facilitator_failover_and_v2_downgrade_guard,
    evaluate_x402_permit2_witness_batch_parity_guard,
    evaluate_x402_solana_token2022_transfer_fee_guard,
    evaluate_x402_sui_sponsored_ptb_equivocation_guard,
)


class Stage156GuardTests(unittest.TestCase):
    def test_x402_and_ucp_guards_sb01_to_sb07(self) -> None:
        # SB-01
        ok_sb01 = evaluate_x402_sui_sponsored_ptb_equivocation_guard(
            network="sui:mainnet",
            facilitator_address="0xfacilitator",
            gas_data_owner="0xfacilitator",
            gas_coin_object_ids=["0xgas1"],
            payment_input_coin_object_ids=["0xusdc1"],
            gas_budget_mist=5_000_000,
            max_sponsored_gas_mist=10_000_000,
            recipient_address="0xmerchant",
            expected_pay_to="0xmerchant",
        )
        self.assertTrue(ok_sb01.allowed)
        bad_sb01 = evaluate_x402_sui_sponsored_ptb_equivocation_guard(
            network="sui:mainnet",
            facilitator_address="0xfacilitator",
            gas_data_owner="0xfacilitator",
            gas_coin_object_ids=["0xshared_coin"],
            payment_input_coin_object_ids=["0xshared_coin"],
            gas_budget_mist=5_000_000,
            max_sponsored_gas_mist=10_000_000,
            recipient_address="0xmerchant",
            expected_pay_to="0xmerchant",
        )
        self.assertFalse(bad_sb01.allowed)
        self.assertEqual(bad_sb01.code, "X402_SUI_COIN_OBJECT_EQUIVOCATION_RISK")

        # SB-02
        witness = (
            "TransferWitness witness)TokenPermissions(address token,uint256 amount)"
            "TransferWitness(address recipient,bytes32 resourceHash,uint256 nonce)"
        )
        ok_sb02 = evaluate_x402_permit2_witness_batch_parity_guard(
            witness_type_string=witness,
            permitted_tokens=["0xUSDC", "0xUSDC"],
            permitted_amounts=[600_000, 400_000],
            transfer_recipients=["0xMerchant", "0xMerchant"],
            transfer_requested_amounts=[600_000, 400_000],
            expected_asset="0xusdc",
            expected_pay_to="0xmerchant",
            expected_min_amount=1_000_000,
            nonce=42,
            used_permit2_nonces=[10, 11],
        )
        self.assertTrue(ok_sb02.allowed)
        bad_sb02 = evaluate_x402_permit2_witness_batch_parity_guard(
            witness_type_string=witness,
            permitted_tokens=["0xUSDC"],
            permitted_amounts=[600_000],
            transfer_recipients=["0xMerchant", "0xMerchant"],
            transfer_requested_amounts=[600_000, 400_000],
            expected_asset="0xusdc",
            expected_pay_to="0xmerchant",
            expected_min_amount=1_000_000,
            nonce=42,
            used_permit2_nonces=[10, 11],
        )
        self.assertFalse(bad_sb02.allowed)
        self.assertEqual(bad_sb02.code, "X402_PERMIT2_BATCH_ARRAY_LENGTH_MISMATCH")

        # SB-03
        ok_sb03 = evaluate_x402_solana_token2022_transfer_fee_guard(
            gross_amount_atomic=1_010_000,
            required_net_amount_atomic=1_000_000,
            transfer_fee_bps=50,
            maximum_fee_atomic=10_000,
            declared_fee_atomic=5_050,
            uses_confidential_transfer_extension=False,
            mint_decimals=6,
            instruction_decimals=6,
        )
        self.assertTrue(ok_sb03.allowed)
        bad_sb03 = evaluate_x402_solana_token2022_transfer_fee_guard(
            gross_amount_atomic=1_000_000,
            required_net_amount_atomic=1_000_000,
            transfer_fee_bps=50,
            maximum_fee_atomic=10_000,
            declared_fee_atomic=5_000,
            uses_confidential_transfer_extension=False,
            mint_decimals=6,
            instruction_decimals=6,
        )
        self.assertFalse(bad_sb03.allowed)
        self.assertEqual(bad_sb03.code, "X402_SVM_NET_RECEIVED_BELOW_REQUIRED")

        # SB-04
        ok_sb04 = evaluate_x402_facilitator_failover_and_v2_downgrade_guard(
            primary_http_status=503,
            primary_timed_out=False,
            attempted_secondary_failover=True,
            payment_header_version=2,
            route_minimum_version=2,
            nonce_valid_before_epoch=2_000_000_100,
            current_epoch=2_000_000_000,
        )
        self.assertTrue(ok_sb04.allowed)
        bad_sb04 = evaluate_x402_facilitator_failover_and_v2_downgrade_guard(
            primary_http_status=402,
            primary_timed_out=False,
            attempted_secondary_failover=True,
            payment_header_version=2,
            route_minimum_version=2,
            nonce_valid_before_epoch=2_000_000_100,
            current_epoch=2_000_000_000,
        )
        self.assertFalse(bad_sb04.allowed)
        self.assertEqual(bad_sb04.code, "X402_ILLEGAL_FACILITATOR_FAILOVER_ON_DETERMINISTIC_REJECT")

        # SB-05
        ok_sb05 = evaluate_ucp_bopis_inventory_lock_and_pickup_guard(
            fulfillment_type="bopis",
            store_id="store_nyc_01",
            inventory_lock_id="lock_991",
            lock_expires_at_epoch=2_000_000_900,
            current_epoch=2_000_000_000,
            pickup_submode="locker",
            pickup_verification_token="PIN-884920",
            unavailable_store_skus=[],
            auto_converted_to_paid_shipping=False,
            buyer_reconsented_split_shipping=False,
        )
        self.assertTrue(ok_sb05.allowed)
        bad_sb05 = evaluate_ucp_bopis_inventory_lock_and_pickup_guard(
            fulfillment_type="bopis",
            store_id="store_nyc_01",
            inventory_lock_id="lock_991",
            lock_expires_at_epoch=2_000_000_900,
            current_epoch=2_000_000_000,
            pickup_submode="locker",
            pickup_verification_token="PIN-884920",
            unavailable_store_skus=["sku_missing_1"],
            auto_converted_to_paid_shipping=True,
            buyer_reconsented_split_shipping=False,
        )
        self.assertFalse(bad_sb05.allowed)
        self.assertEqual(bad_sb05.code, "UCP_BOPIS_UNCONSENTED_PAID_SHIPPING_FALLBACK")

        # SB-06
        ok_sb06 = evaluate_ucp_multicurrency_fx_lock_guard(
            settlement_currency="USD",
            locked_settlement_currency="USD",
            presentment_currency="EUR",
            settlement_amount_minor=10_000,
            fx_rate_str="0.9235",
            declared_presentment_amount_minor=9_235,
            fx_quote_expires_at_epoch=2_000_000_300,
            current_epoch=2_000_000_000,
        )
        self.assertTrue(ok_sb06.allowed)
        bad_sb06 = evaluate_ucp_multicurrency_fx_lock_guard(
            settlement_currency="EUR",
            locked_settlement_currency="USD",
            presentment_currency="EUR",
            settlement_amount_minor=10_000,
            fx_rate_str="0.9235",
            declared_presentment_amount_minor=9_235,
            fx_quote_expires_at_epoch=2_000_000_300,
            current_epoch=2_000_000_000,
        )
        self.assertFalse(bad_sb06.allowed)
        self.assertEqual(bad_sb06.code, "UCP_FX_SETTLEMENT_CURRENCY_MUTATED")

        # SB-07
        ok_sb07 = evaluate_ucp_trade_in_credit_escrow_guard(
            device_imei="356938035643809",
            stolen_imei_registry=["356938035640000"],
            provisional_trade_in_credit_minor=30_000,
            immediate_unconditional_discount_minor=0,
            post_inspection_clawback_minor=5_000,
            escrow_hold_active=True,
        )
        self.assertTrue(ok_sb07.allowed)
        bad_sb07 = evaluate_ucp_trade_in_credit_escrow_guard(
            device_imei="356938035640000",
            stolen_imei_registry=["356938035640000"],
            provisional_trade_in_credit_minor=30_000,
            immediate_unconditional_discount_minor=0,
            post_inspection_clawback_minor=5_000,
            escrow_hold_active=True,
        )
        self.assertFalse(bad_sb07.allowed)
        self.assertEqual(bad_sb07.code, "UCP_TRADE_IN_STOLEN_DEVICE_BLOCKED")

    def test_acp_ap2_mcp_stripe_tap_tau2_guards_sb08_to_sb16(self) -> None:
        # SB-08
        ok_sb08 = evaluate_acp_idempotency_key_fingerprint_and_lock_guard(
            idempotency_key="idem_checkout_20261021_abcd1234",
            request_jcs_sha256="sha256:aaa111",
            stored_jcs_sha256="sha256:aaa111",
            key_created_at_epoch=2_000_000_000,
            current_epoch=2_000_000_100,
            in_flight_lock_active=False,
        )
        self.assertTrue(ok_sb08.allowed)
        bad_sb08 = evaluate_acp_idempotency_key_fingerprint_and_lock_guard(
            idempotency_key="idem_checkout_20261021_abcd1234",
            request_jcs_sha256="sha256:bbb222",
            stored_jcs_sha256="sha256:aaa111",
            key_created_at_epoch=2_000_000_000,
            current_epoch=2_000_000_100,
            in_flight_lock_active=False,
        )
        self.assertFalse(bad_sb08.allowed)
        self.assertEqual(bad_sb08.code, "ACP_IDEMPOTENCY_PAYLOAD_FINGERPRINT_CONFLICT_409")

        # SB-09
        ok_sb09 = evaluate_acp_spt_cryptogram_eci_and_arn_refund_guard(
            token_id="spt_live_99887766",
            cryptogram_type="TAVV",
            eci_indicator="05",
            exemption_reason=None,
            amount_minor=15_000,
            low_value_exemption_cap_minor=3_000,
            is_refund=True,
            acquirer_reference_number="74567890123456789012345",
        )
        self.assertTrue(ok_sb09.allowed)
        bad_sb09 = evaluate_acp_spt_cryptogram_eci_and_arn_refund_guard(
            token_id="spt_live_99887766",
            cryptogram_type="TAVV",
            eci_indicator="07",
            exemption_reason="low_value",
            amount_minor=8_500,
            low_value_exemption_cap_minor=3_000,
            is_refund=False,
            acquirer_reference_number="",
        )
        self.assertFalse(bad_sb09.allowed)
        self.assertEqual(bad_sb09.code, "ACP_SPT_LOW_VALUE_EXEMPTION_CAP_EXCEEDED")

        # SB-10
        ok_sb10 = evaluate_ap2_mandate_clock_skew_and_inheritance_guard(
            parent_nbf=2_000_000_000,
            parent_exp=2_000_050_000,
            child_iat=2_000_000_100,
            child_nbf=2_000_000_100,
            child_exp=2_000_030_000,
            current_epoch=2_000_000_085,
            is_closed_mandate=True,
        )
        self.assertTrue(ok_sb10.allowed)
        bad_sb10 = evaluate_ap2_mandate_clock_skew_and_inheritance_guard(
            parent_nbf=2_000_000_000,
            parent_exp=2_000_050_000,
            child_iat=2_000_000_100,
            child_nbf=2_000_000_100,
            child_exp=2_000_060_000,
            current_epoch=2_000_000_200,
            is_closed_mandate=True,
        )
        self.assertFalse(bad_sb10.allowed)
        self.assertEqual(bad_sb10.code, "AP2_CHILD_MANDATE_EXCEEDS_PARENT_WINDOW")

        # SB-11
        ok_sb11 = evaluate_ap2_customs_hs_code_and_de_minimis_guard(
            hs_code_6digit="847130",
            incoterm="DDP",
            shipment_customs_value_minor=50_000,
            prior_24h_consignee_customs_value_minor=40_000,
            de_minimis_threshold_minor=80_000,
            declared_duty_tax_minor=7_200,
            landed_total_minor=57_200,
            mandate_ddp_ceiling_minor=60_000,
        )
        self.assertTrue(ok_sb11.allowed)
        bad_sb11 = evaluate_ap2_customs_hs_code_and_de_minimis_guard(
            hs_code_6digit="847130",
            incoterm="DDP",
            shipment_customs_value_minor=50_000,
            prior_24h_consignee_customs_value_minor=40_000,
            de_minimis_threshold_minor=80_000,
            declared_duty_tax_minor=0,
            landed_total_minor=50_000,
            mandate_ddp_ceiling_minor=60_000,
        )
        self.assertFalse(bad_sb11.allowed)
        self.assertEqual(bad_sb11.code, "AP2_CUSTOMS_DE_MINIMIS_SPLIT_EVASION_BLOCKED")

        # SB-12
        ok_sb12 = evaluate_mcp_roots_symlink_sampling_and_cancel_guard(
            allowed_root_realpath="/workspace/merchant_catalog",
            target_resolved_realpath="/workspace/merchant_catalog/electronics/offers.json",
            sampling_requested_tokens=512,
            sampling_max_tokens_cap=1024,
            sampling_stop_sequences=["</tool_call>"],
            cancellation_received=True,
            tool_subprocess_terminated=True,
        )
        self.assertTrue(ok_sb12.allowed)
        bad_sb12 = evaluate_mcp_roots_symlink_sampling_and_cancel_guard(
            allowed_root_realpath="/workspace/merchant_catalog",
            target_resolved_realpath="/etc/passwd",
            sampling_requested_tokens=512,
            sampling_max_tokens_cap=1024,
            sampling_stop_sequences=["</tool_call>"],
            cancellation_received=False,
            tool_subprocess_terminated=False,
        )
        self.assertFalse(bad_sb12.allowed)
        self.assertEqual(bad_sb12.code, "MCP_ROOTS_SYMLINK_ESCAPE_BLOCKED")

        # SB-13
        ok_sb13 = evaluate_stripe_proration_credit_note_and_efw_guard(
            proration_behavior="create_prorations",
            buyer_approved_immediate_invoice=False,
            invoice_amount_paid_minor=20_000,
            existing_credit_notes_minor=5_000,
            new_credit_note_minor=10_000,
            has_active_early_fraud_warning=False,
            attempted_automated_agent_refund=False,
        )
        self.assertTrue(ok_sb13.allowed)
        bad_sb13 = evaluate_stripe_proration_credit_note_and_efw_guard(
            proration_behavior="create_prorations",
            buyer_approved_immediate_invoice=False,
            invoice_amount_paid_minor=20_000,
            existing_credit_notes_minor=5_000,
            new_credit_note_minor=5_000,
            has_active_early_fraud_warning=True,
            attempted_automated_agent_refund=True,
        )
        self.assertFalse(bad_sb13.allowed)
        self.assertEqual(bad_sb13.code, "STRIPE_RADAR_EFW_REFUND_HALTED")

        # SB-14
        ok_sb14 = evaluate_visa_tap_forwarded_model_and_bin_routing_guard(
            signed_forwarded_for="for=198.51.100.17;proto=https",
            observed_proxy_forwarded_for="for=198.51.100.17;proto=https",
            agent_model_id="gpt-5.4",
            approved_model_ids=["gpt-5.4", "claude-4.6-opus"],
            token_bin_prefix="411111",
            routed_card_network="visa",
        )
        self.assertTrue(ok_sb14.allowed)
        bad_sb14 = evaluate_visa_tap_forwarded_model_and_bin_routing_guard(
            signed_forwarded_for="for=198.51.100.17;proto=https",
            observed_proxy_forwarded_for="for=198.51.100.17;proto=https",
            agent_model_id="gpt-5.4",
            approved_model_ids=["gpt-5.4", "claude-4.6-opus"],
            token_bin_prefix="411111",
            routed_card_network="mastercard",
        )
        self.assertFalse(bad_sb14.allowed)
        self.assertEqual(bad_sb14.code, "VISA_TAP_BIN_NETWORK_ROUTING_MISMATCH")

        # SB-15
        ok_sb15 = evaluate_tau2_airline_cabin_upgrade_and_pnr_split_guard(
            current_cabin="economy",
            target_cabin="business",
            loyalty_tier="gold",
            checked_bags_count=3,
            charged_bag_fee_minor=5_000,
            original_pnr_passengers=["pax_1", "pax_2", "pax_3"],
            split_primary_pnr_passengers=["pax_1", "pax_2"],
            split_secondary_pnr_passengers=["pax_3"],
        )
        self.assertTrue(ok_sb15.allowed)
        bad_sb15 = evaluate_tau2_airline_cabin_upgrade_and_pnr_split_guard(
            current_cabin="basic_economy",
            target_cabin="economy",
            loyalty_tier="gold",
            checked_bags_count=2,
            charged_bag_fee_minor=0,
            original_pnr_passengers=["pax_1", "pax_2"],
            split_primary_pnr_passengers=["pax_1"],
            split_secondary_pnr_passengers=["pax_2"],
        )
        self.assertFalse(bad_sb15.allowed)
        self.assertEqual(bad_sb15.code, "TAU2_AIRLINE_BASIC_ECONOMY_UPGRADE_FORBIDDEN")

        # SB-16
        ok_sb16 = evaluate_tau2_retail_price_match_and_roaming_proration_guard(
            competitor_domain="bestbuy.com",
            approved_competitors=["bestbuy.com", "amazon.com", "target.com"],
            sku_exact_match=True,
            competitor_in_stock=True,
            is_liquidation_or_flash_sale=False,
            roaming_daily_rate_minor=1_000,
            active_roaming_days=7,
            billing_cycle_days=30,
            charged_roaming_fee_minor=7_000,
        )
        self.assertTrue(ok_sb16.allowed)
        bad_sb16 = evaluate_tau2_retail_price_match_and_roaming_proration_guard(
            competitor_domain="bestbuy.com",
            approved_competitors=["bestbuy.com", "amazon.com"],
            sku_exact_match=True,
            competitor_in_stock=True,
            is_liquidation_or_flash_sale=True,
            roaming_daily_rate_minor=1_000,
            active_roaming_days=7,
            billing_cycle_days=30,
            charged_roaming_fee_minor=7_000,
        )
        self.assertFalse(bad_sb16.allowed)
        self.assertEqual(bad_sb16.code, "TAU2_RETAIL_PRICE_MATCH_INELIGIBLE")

    def test_audit_summary(self) -> None:
        summary = build_stage156_audit_summary()
        self.assertEqual(summary["total_guards"], 16)
        self.assertTrue(summary["all_passed"])


if __name__ == "__main__":
    unittest.main()
