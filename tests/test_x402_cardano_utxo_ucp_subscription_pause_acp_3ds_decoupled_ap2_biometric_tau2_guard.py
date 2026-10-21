"""Unit tests for Stage 164 (CD-01..CD-16) deterministic guardrails."""

from __future__ import annotations

import hashlib
import unittest

from lab.x402_cardano_utxo_ucp_subscription_pause_acp_3ds_decoupled_ap2_biometric_tau2_guard import (
    evaluate_acp_3ds_decoupled_auth_guard,
    evaluate_acp_instant_payout_reserve_guard,
    evaluate_ap2_federated_spiffe_trust_guard,
    evaluate_ap2_fido2_biometric_uv_guard,
    evaluate_mcp_roots_sandbox_escape_guard,
    evaluate_stripe_connect_destination_charge_guard,
    evaluate_tau2_loyalty_status_miles_reinstatement_guard,
    evaluate_tau2_retail_price_match_guard,
    evaluate_ucp_age_restricted_regulated_sku_guard,
    evaluate_ucp_subscription_pause_proration_guard,
    evaluate_ucp_warranty_protection_plan_binding_guard,
    evaluate_visa_tap_push_provisioning_guard,
    evaluate_x402_cardano_eutxo_native_token_guard,
    evaluate_x402_facilitator_solvency_reserve_guard,
    evaluate_x402_l3_custom_gas_sequencer_guard,
    evaluate_x402_streaming_token_metering_guard,
)


class Stage164GuardTest(unittest.TestCase):
    def test_x402_cardano_l3_solvency_and_streaming_guards(self) -> None:
        policy = "a" * 56
        ok_cd01 = evaluate_x402_cardano_eutxo_native_token_guard(
            network="cardano:mainnet",
            policy_id=policy,
            expected_policy_id=policy,
            asset_name_hex="5553444d",
            expected_asset_name_hex="5553444d",
            token_amount=25_000_000,
            required_token_amount=25_000_000,
            output_lovelace=1_500_000,
            min_utxo_lovelace=1_400_000,
            tx_ttl_slot=120_300,
            current_slot=120_000,
        )
        self.assertTrue(ok_cd01.allowed)
        bad_cd01 = evaluate_x402_cardano_eutxo_native_token_guard(
            network="cardano:mainnet",
            policy_id=policy,
            expected_policy_id=policy,
            asset_name_hex="5553444d",
            expected_asset_name_hex="5553444d",
            token_amount=25_000_000,
            required_token_amount=25_000_000,
            output_lovelace=900_000,
            min_utxo_lovelace=1_400_000,
            tx_ttl_slot=120_300,
            current_slot=120_000,
        )
        self.assertFalse(bad_cd01.allowed)
        self.assertEqual(bad_cd01.decision_code, "X402_CARDANO_MIN_UTXO_LOVELACE_VIOLATION")

        ok_cd02 = evaluate_x402_l3_custom_gas_sequencer_guard(
            payment_amount_minor=100_000,
            l1_da_blob_fee_minor=800,
            l3_execution_fee_minor=200,
            rollup_fee_scalar_bps=10500,
            sequencer_soft_confirmed_only=False,
            l1_batch_posted=True,
        )
        self.assertTrue(ok_cd02.allowed)
        bad_cd02 = evaluate_x402_l3_custom_gas_sequencer_guard(
            payment_amount_minor=100_000,
            l1_da_blob_fee_minor=800,
            l3_execution_fee_minor=200,
            rollup_fee_scalar_bps=10500,
            sequencer_soft_confirmed_only=True,
            l1_batch_posted=False,
        )
        self.assertFalse(bad_cd02.allowed)
        self.assertEqual(bad_cd02.decision_code, "X402_L3_UNPOSTED_SEQUENCER_SOFT_CONFIRM_REJECTED")

        ok_cd03 = evaluate_x402_facilitator_solvency_reserve_guard(
            attested_reserves_minor=5_500_000,
            total_liabilities_minor=5_000_000,
            pending_settlement_minor=200_000,
            merkle_root_age_seconds=900,
        )
        self.assertTrue(ok_cd03.allowed)
        bad_cd03 = evaluate_x402_facilitator_solvency_reserve_guard(
            attested_reserves_minor=4_800_000,
            total_liabilities_minor=5_000_000,
            pending_settlement_minor=200_000,
            merkle_root_age_seconds=900,
        )
        self.assertFalse(bad_cd03.allowed)
        self.assertEqual(bad_cd03.decision_code, "X402_FACILITATOR_UNDERCOLLATERALIZED_BLOCKED")

        digest = hashlib.sha256(b"chunk-42").hexdigest()
        ok_cd04 = evaluate_x402_streaming_token_metering_guard(
            expected_prev_chunk_seq=41,
            chunk_seq=42,
            delivered_tokens=512,
            billed_tokens=512,
            unit_price_micro_usd=10,
            cumulative_billed_micro_usd=100_000,
            stream_cap_micro_usd=500_000,
            chunk_payload_sha256=digest,
            receipt_payload_sha256=digest,
        )
        self.assertTrue(ok_cd04.allowed)
        bad_cd04 = evaluate_x402_streaming_token_metering_guard(
            expected_prev_chunk_seq=41,
            chunk_seq=42,
            delivered_tokens=512,
            billed_tokens=1024,
            unit_price_micro_usd=10,
            cumulative_billed_micro_usd=100_000,
            stream_cap_micro_usd=500_000,
            chunk_payload_sha256=digest,
            receipt_payload_sha256=digest,
        )
        self.assertFalse(bad_cd04.allowed)
        self.assertEqual(bad_cd04.decision_code, "X402_STREAM_GHOST_TOKEN_OVERBILLING_BLOCKED")

    def test_ucp_acp_and_ap2_guards(self) -> None:
        ok_cd05 = evaluate_ucp_subscription_pause_proration_guard(
            subscription_state="PAUSED",
            requested_pause_days=30,
            cycle_price_minor=3000,
            cycle_total_days=30,
            unused_days_in_cycle=15,
            reported_proration_credit_minor=1500,
            pause_period_charge_minor=0,
            auto_resume_notified_hours_ahead=48,
        )
        self.assertTrue(ok_cd05.allowed)
        bad_cd05 = evaluate_ucp_subscription_pause_proration_guard(
            subscription_state="PAUSED",
            requested_pause_days=30,
            cycle_price_minor=3000,
            cycle_total_days=30,
            unused_days_in_cycle=15,
            reported_proration_credit_minor=1500,
            pause_period_charge_minor=3000,
            auto_resume_notified_hours_ahead=48,
        )
        self.assertFalse(bad_cd05.allowed)
        self.assertEqual(bad_cd05.decision_code, "UCP_SUBSCRIPTION_PAUSED_BILLING_LEAK_BLOCKED")

        ok_cd06 = evaluate_ucp_age_restricted_regulated_sku_guard(
            is_age_restricted_sku=True,
            required_minimum_age=21,
            zk_age_attestation_verified=True,
            attested_minimum_age=21,
            issuer_trusted=True,
            adult_signature_on_delivery_required=True,
        )
        self.assertTrue(ok_cd06.allowed)
        bad_cd06 = evaluate_ucp_age_restricted_regulated_sku_guard(
            is_age_restricted_sku=True,
            required_minimum_age=21,
            zk_age_attestation_verified=False,
            attested_minimum_age=21,
            issuer_trusted=True,
            adult_signature_on_delivery_required=True,
            self_asserted_only=True,
        )
        self.assertFalse(bad_cd06.allowed)
        self.assertEqual(bad_cd06.decision_code, "UCP_AGE_ATTESTATION_UNVERIFIED_BLOCKED")

        serial_hash = hashlib.sha256(b"SN-MACBOOK-991").hexdigest()
        ok_cd07 = evaluate_ucp_warranty_protection_plan_binding_guard(
            parent_hardware_line_active=True,
            parent_sku_price_minor=199_900,
            plan_min_hardware_price_minor=100_000,
            plan_max_hardware_price_minor=300_000,
            hardware_serial_sha256=serial_hash,
            bound_serial_sha256=serial_hash,
            coverage_start_epoch=1_760_000_500,
            delivery_confirmed_epoch=1_760_000_000,
        )
        self.assertTrue(ok_cd07.allowed)
        bad_cd07 = evaluate_ucp_warranty_protection_plan_binding_guard(
            parent_hardware_line_active=False,
            parent_sku_price_minor=199_900,
            plan_min_hardware_price_minor=100_000,
            plan_max_hardware_price_minor=300_000,
            hardware_serial_sha256=serial_hash,
            bound_serial_sha256=serial_hash,
            coverage_start_epoch=1_760_000_500,
            delivery_confirmed_epoch=1_760_000_000,
        )
        self.assertFalse(bad_cd07.allowed)
        self.assertEqual(bad_cd07.decision_code, "UCP_ORPHAN_WARRANTY_ON_CANCELLED_HARDWARE_BLOCKED")

        ok_cd08 = evaluate_acp_3ds_decoupled_auth_guard(
            trans_status="D",
            oob_challenge_completed=True,
            elapsed_oob_seconds=180,
            cavv_present=True,
            eci="05",
            bound_checkout_session_id="cs_decoupled_01",
            expected_checkout_session_id="cs_decoupled_01",
        )
        self.assertTrue(ok_cd08.allowed)
        bad_cd08 = evaluate_acp_3ds_decoupled_auth_guard(
            trans_status="D",
            oob_challenge_completed=False,
            elapsed_oob_seconds=180,
            cavv_present=True,
            eci="05",
            bound_checkout_session_id="cs_decoupled_01",
            expected_checkout_session_id="cs_decoupled_01",
        )
        self.assertFalse(bad_cd08.allowed)
        self.assertEqual(bad_cd08.decision_code, "ACP_3DS_DECOUPLED_PREMATURE_CAPTURE_BLOCKED")

        ok_cd09 = evaluate_acp_instant_payout_reserve_guard(
            merchant_account_age_days=180,
            delivery_confirmed=True,
            bonded_reserve_minor=50_000,
            requested_instant_payout_minor=80_000,
            daily_instant_payout_used_minor=100_000,
            daily_instant_payout_cap_minor=500_000,
        )
        self.assertTrue(ok_cd09.allowed)
        bad_cd09 = evaluate_acp_instant_payout_reserve_guard(
            merchant_account_age_days=180,
            delivery_confirmed=False,
            bonded_reserve_minor=10_000,
            requested_instant_payout_minor=80_000,
            daily_instant_payout_used_minor=100_000,
            daily_instant_payout_cap_minor=500_000,
        )
        self.assertFalse(bad_cd09.allowed)
        self.assertEqual(bad_cd09.decision_code, "ACP_UNCONFIRMED_DELIVERY_RESERVE_DEFICIT")

        rp_hash = hashlib.sha256(b"pay.merchant.example").hexdigest()
        ok_cd10 = evaluate_ap2_fido2_biometric_uv_guard(
            authenticator_flags_byte=0x05,
            prev_sign_count=10,
            current_sign_count=11,
            rp_id_hash_hex=rp_hash,
            expected_rp_id="pay.merchant.example",
        )
        self.assertTrue(ok_cd10.allowed)
        bad_cd10 = evaluate_ap2_fido2_biometric_uv_guard(
            authenticator_flags_byte=0x01,  # UV bit missing
            prev_sign_count=10,
            current_sign_count=11,
            rp_id_hash_hex=rp_hash,
            expected_rp_id="pay.merchant.example",
        )
        self.assertFalse(bad_cd10.allowed)
        self.assertEqual(bad_cd10.decision_code, "AP2_FIDO2_BIOMETRIC_UV_UP_MISSING")

        ok_cd11 = evaluate_ap2_federated_spiffe_trust_guard(
            spiffe_id="spiffe://corp.buyer.example/ns/procurement/sa/agent-buyer",
            trusted_trust_domains={"corp.buyer.example"},
            actor_chain_depth=2,
            token_audience="ap2://checkout.merchant.example",
            expected_audience="ap2://checkout.merchant.example",
        )
        self.assertTrue(ok_cd11.allowed)
        bad_cd11 = evaluate_ap2_federated_spiffe_trust_guard(
            spiffe_id="spiffe://evil.external.example/ns/procurement/sa/agent-buyer",
            trusted_trust_domains={"corp.buyer.example"},
            actor_chain_depth=2,
            token_audience="ap2://checkout.merchant.example",
            expected_audience="ap2://checkout.merchant.example",
        )
        self.assertFalse(bad_cd11.allowed)
        self.assertEqual(bad_cd11.decision_code, "AP2_SPIFFE_UNTRUSTED_FEDERATION_DOMAIN")

    def test_mcp_stripe_visa_and_tau2_guards(self) -> None:
        ok_cd12 = evaluate_mcp_roots_sandbox_escape_guard(
            allowed_root_path="/workspace/project",
            requested_uri_or_path="file:///workspace/project/catalog/items.json",
            resolved_symlink_target_path="/workspace/project/catalog/items_v2.json",
        )
        self.assertTrue(ok_cd12.allowed)
        bad_cd12 = evaluate_mcp_roots_sandbox_escape_guard(
            allowed_root_path="/workspace/project",
            requested_uri_or_path="file:///workspace/project/catalog/items.json",
            resolved_symlink_target_path="/etc/shadow",
        )
        self.assertFalse(bad_cd12.allowed)
        self.assertEqual(bad_cd12.decision_code, "MCP_ROOTS_SYMLINK_ESCAPE_BLOCKED")

        ok_cd13 = evaluate_stripe_connect_destination_charge_guard(
            charge_amount_minor=10_000,
            application_fee_amount_minor=1_000,
            processing_fee_minor=320,
            connected_account_transfers_active=True,
            on_behalf_of_country="US",
            destination_country="US",
        )
        self.assertTrue(ok_cd13.allowed)
        bad_cd13 = evaluate_stripe_connect_destination_charge_guard(
            charge_amount_minor=10_000,
            application_fee_amount_minor=4_500,
            processing_fee_minor=320,
            connected_account_transfers_active=True,
            on_behalf_of_country="US",
            destination_country="US",
        )
        self.assertFalse(bad_cd13.allowed)
        self.assertEqual(bad_cd13.decision_code, "STRIPE_CONNECT_APPLICATION_FEE_CAP_EXCEEDED")

        se_hash = hashlib.sha256(b"apple-se-enclave-01").hexdigest()
        ok_cd14 = evaluate_visa_tap_push_provisioning_guard(
            issuer_provisioning_cryptogram_valid=True,
            wallet_device_se_hash=se_hash,
            expected_device_se_hash=se_hash,
            provisioning_nonce="nonce_prov_01",
            seen_provisioning_nonces=set(),
            token_requestor_id="40010030273",
            allowed_token_requestor_ids={"40010030273"},
        )
        self.assertTrue(ok_cd14.allowed)
        bad_cd14 = evaluate_visa_tap_push_provisioning_guard(
            issuer_provisioning_cryptogram_valid=True,
            wallet_device_se_hash=se_hash,
            expected_device_se_hash=se_hash,
            provisioning_nonce="nonce_prov_01",
            seen_provisioning_nonces={"nonce_prov_01"},
            token_requestor_id="40010030273",
            allowed_token_requestor_ids={"40010030273"},
        )
        self.assertFalse(bad_cd14.allowed)
        self.assertEqual(bad_cd14.decision_code, "VISA_TAP_PROVISIONING_NONCE_REPLAY_BLOCKED")

        ok_cd15 = evaluate_tau2_retail_price_match_guard(
            competitor_domain="bestbuy.com",
            authorized_competitor_domains={"bestbuy.com", "target.com"},
            exact_sku_match=True,
            competitor_in_stock_verified=True,
            is_liquidation_or_flash_sale=False,
            quote_age_hours=4,
            days_since_purchase=5,
            original_paid_minor=29_900,
            competitor_price_minor=24_900,
            requested_refund_diff_minor=5_000,
        )
        self.assertTrue(ok_cd15.allowed)
        bad_cd15 = evaluate_tau2_retail_price_match_guard(
            competitor_domain="sketchy-clearance.example",
            authorized_competitor_domains={"bestbuy.com", "target.com"},
            exact_sku_match=True,
            competitor_in_stock_verified=True,
            is_liquidation_or_flash_sale=False,
            quote_age_hours=4,
            days_since_purchase=5,
            original_paid_minor=29_900,
            competitor_price_minor=24_900,
            requested_refund_diff_minor=5_000,
        )
        self.assertFalse(bad_cd15.allowed)
        self.assertEqual(bad_cd15.decision_code, "TAU2_PRICE_MATCH_UNAUTHORIZED_COMPETITOR")

        ok_cd16 = evaluate_tau2_loyalty_status_miles_reinstatement_guard(
            partner_statement_cryptographic_proof_valid=True,
            expired_miles_amount=45_000,
            months_since_expiration=6,
            reinstatement_fee_paid=True,
            already_reinstated_tx_ids=set(),
            reinstatement_tx_id="reinstate_tx_01",
        )
        self.assertTrue(ok_cd16.allowed)
        bad_cd16 = evaluate_tau2_loyalty_status_miles_reinstatement_guard(
            partner_statement_cryptographic_proof_valid=True,
            expired_miles_amount=45_000,
            months_since_expiration=6,
            reinstatement_fee_paid=True,
            already_reinstated_tx_ids={"reinstate_tx_01"},
            reinstatement_tx_id="reinstate_tx_01",
        )
        self.assertFalse(bad_cd16.allowed)
        self.assertEqual(bad_cd16.decision_code, "TAU2_LOYALTY_DOUBLE_REINSTATEMENT_BLOCKED")


if __name__ == "__main__":
    unittest.main()
