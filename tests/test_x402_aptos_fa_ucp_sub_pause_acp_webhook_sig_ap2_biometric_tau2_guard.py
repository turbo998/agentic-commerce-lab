"""Unit tests for Stage 158 guardrails (`AD-01..AD-16`)."""

from __future__ import annotations

import hashlib
import hmac
import json
import unittest

from lab.x402_aptos_fa_ucp_sub_pause_acp_webhook_sig_ap2_biometric_tau2_guard import (
    CANONICAL_ENTRYPOINT_V07,
    evaluate_acp_b2b_tax_exemption_certificate_guard,
    evaluate_acp_webhook_hmac_sequence_guard,
    evaluate_ap2_corporate_quorum_sod_guard,
    evaluate_ap2_step_up_biometric_uv_guard,
    evaluate_mcp_oauth_audience_passthrough_guard,
    evaluate_stripe_connect_fee_transfer_guard,
    evaluate_tau2_pharmacy_refill_prior_auth_guard,
    evaluate_tau2_saas_contract_seat_downgrade_guard,
    evaluate_ucp_regulated_age_hazmat_fulfillment_guard,
    evaluate_ucp_split_shipment_partial_capture_guard,
    evaluate_ucp_subscription_pause_skip_cycle_guard,
    evaluate_visa_tap_passkey_c2p_binding_guard,
    evaluate_x402_accepts_option_selection_guard,
    evaluate_x402_aptos_fungible_asset_sponsor_guard,
    evaluate_x402_edge_stream_completion_settlement_guard,
    evaluate_x402_erc4337_userop_paymaster_guard,
)


class Stage158GuardTests(unittest.TestCase):
    def test_x402_aptos_erc4337_accepts_and_edge_stream_guards(self) -> None:
        # AD-01
        ok_ad01 = evaluate_x402_aptos_fungible_asset_sponsor_guard(
            network="aptos:1",
            entry_function_id="0x1::primary_fungible_store::transfer",
            asset_metadata_address="0xbae207659db88bea0cbead6da0ed00aac12edcdda169e591cd41c94180b46f3b",
            expected_asset_metadata_address="0xbae207659db88bea0cbead6da0ed00aac12edcdda169e591cd41c94180b46f3b",
            transfer_amount=5_000_000,
            required_amount=5_000_000,
            expiration_timestamp_secs=1_792_555_150,
            now_unix=1_792_555_000,
            gas_unit_price=100,
            max_gas_unit_price=500,
            max_gas_amount=1500,
            max_sponsored_gas_units=3000,
        )
        self.assertTrue(ok_ad01.allowed)
        bad_ad01 = evaluate_x402_aptos_fungible_asset_sponsor_guard(
            network="aptos:1",
            entry_function_id="0x1::primary_fungible_store::transfer",
            asset_metadata_address="0xdeadbeef",
            expected_asset_metadata_address="0xbae207659db88bea0cbead6da0ed00aac12edcdda169e591cd41c94180b46f3b",
            transfer_amount=5_000_000,
            required_amount=5_000_000,
            expiration_timestamp_secs=1_792_555_150,
            now_unix=1_792_555_000,
        )
        self.assertFalse(bad_ad01.allowed)
        self.assertEqual(bad_ad01.decision_code, "X402_APTOS_FA_METADATA_OBJECT_MISMATCH_BLOCKED")

        # AD-02
        ok_ad02 = evaluate_x402_erc4337_userop_paymaster_guard(
            entry_point_address=CANONICAL_ENTRYPOINT_V07,
            paymaster_valid_after=1_792_554_900,
            paymaster_valid_until=1_792_555_300,
            now_unix=1_792_555_000,
            call_gas_limit=120_000,
            verification_gas_limit=150_000,
            pre_verification_gas=50_000,
            max_total_userop_gas=500_000,
            paymaster_signature_valid=True,
        )
        self.assertTrue(ok_ad02.allowed)
        bad_ad02 = evaluate_x402_erc4337_userop_paymaster_guard(
            entry_point_address="0x1111111111111111111111111111111111111111",
            paymaster_valid_after=1_792_554_900,
            paymaster_valid_until=1_792_555_300,
            now_unix=1_792_555_000,
            call_gas_limit=120_000,
            verification_gas_limit=150_000,
            pre_verification_gas=50_000,
            max_total_userop_gas=500_000,
            paymaster_signature_valid=True,
        )
        self.assertFalse(bad_ad02.allowed)
        self.assertEqual(bad_ad02.decision_code, "X402_ERC4337_UNTRUSTED_ENTRYPOINT_BLOCKED")

        # AD-03
        ok_ad03 = evaluate_x402_accepts_option_selection_guard(
            accepts=[
                {"scheme": "upto", "network": "eip155:8453", "maxAmountRequired": "1000"},
                {"scheme": "exact", "network": "eip155:8453", "maxAmountRequired": "1200"},
            ],
            supported_networks=["eip155:8453"],
            client_max_budget_minor=1500,
        )
        self.assertTrue(ok_ad03.allowed)
        self.assertEqual(ok_ad03.evidence["selected_scheme"], "exact")
        bad_ad03 = evaluate_x402_accepts_option_selection_guard(
            accepts=[{"scheme": "exact", "network": "eip155:8453", "maxAmountRequired": "0"}],
            supported_networks=["eip155:8453"],
            client_max_budget_minor=1500,
        )
        self.assertFalse(bad_ad03.allowed)
        self.assertEqual(bad_ad03.decision_code, "X402_ACCEPTS_NON_POSITIVE_INTEGER_AMOUNT_BLOCKED")

        # AD-04
        ok_ad04 = evaluate_x402_edge_stream_completion_settlement_guard(
            upstream_http_status=200,
            stream_aborted=False,
            bytes_streamed=4096,
            expected_content_length=4096,
            settlement_committed_early=False,
        )
        self.assertTrue(ok_ad04.allowed)
        bad_ad04 = evaluate_x402_edge_stream_completion_settlement_guard(
            upstream_http_status=200,
            stream_aborted=True,
            bytes_streamed=1024,
            expected_content_length=4096,
            settlement_committed_early=False,
        )
        self.assertFalse(bad_ad04.allowed)
        self.assertEqual(bad_ad04.decision_code, "X402_EDGE_TRUNCATED_STREAM_SETTLEMENT_BLOCKED")

    def test_ucp_and_acp_guards(self) -> None:
        # AD-05
        ok_ad05 = evaluate_ucp_subscription_pause_skip_cycle_guard(
            subscription_status="active",
            requested_action="charge",
            pause_duration_days=0,
            max_pause_days=60,
            billing_cycle_id="cyc_2026_11",
            skipped_cycle_ids=["cyc_2026_10"],
            expected_next_billing_unix=1_795_147_000,
            reported_next_billing_unix=1_795_147_000,
        )
        self.assertTrue(ok_ad05.allowed)
        bad_ad05 = evaluate_ucp_subscription_pause_skip_cycle_guard(
            subscription_status="paused",
            requested_action="charge",
            pause_duration_days=30,
            max_pause_days=60,
            billing_cycle_id="cyc_2026_11",
            skipped_cycle_ids=[],
            expected_next_billing_unix=1_795_147_000,
            reported_next_billing_unix=1_795_147_000,
        )
        self.assertFalse(bad_ad05.allowed)
        self.assertEqual(bad_ad05.decision_code, "UCP_SUBSCRIPTION_CHARGE_WHILE_PAUSED_BLOCKED")

        # AD-06
        ok_ad06 = evaluate_ucp_split_shipment_partial_capture_guard(
            authorized_total_minor=20_000,
            prior_captured_minor=8_500,
            current_shipment_items_minor=9_000,
            current_shipment_tax_minor=720,
            current_shipment_shipping_minor=0,
            shipping_already_captured=True,
            carrier_code="UPS",
            tracking_number="1Z999AA10123456784",
        )
        self.assertTrue(ok_ad06.allowed)
        bad_ad06 = evaluate_ucp_split_shipment_partial_capture_guard(
            authorized_total_minor=20_000,
            prior_captured_minor=8_500,
            current_shipment_items_minor=9_000,
            current_shipment_tax_minor=720,
            current_shipment_shipping_minor=999,
            shipping_already_captured=True,
            carrier_code="UPS",
            tracking_number="1Z999AA10123456784",
        )
        self.assertFalse(bad_ad06.allowed)
        self.assertEqual(bad_ad06.decision_code, "UCP_SPLIT_SHIPMENT_DUPLICATE_SHIPPING_FEE_BLOCKED")

        # AD-07
        ok_ad07 = evaluate_ucp_regulated_age_hazmat_fulfillment_guard(
            required_min_age=21,
            age_verified_min_years=25,
            age_verification_token_id="avt_998123",
            adult_signature_required_on_delivery=True,
            hazmat_classes=["lithium_ion_un3480"],
            selected_shipping_method="ground_hazmat",
        )
        self.assertTrue(ok_ad07.allowed)
        bad_ad07 = evaluate_ucp_regulated_age_hazmat_fulfillment_guard(
            required_min_age=21,
            age_verified_min_years=25,
            age_verification_token_id="avt_998123",
            adult_signature_required_on_delivery=True,
            hazmat_classes=["lithium_ion_un3480"],
            selected_shipping_method="air_express",
        )
        self.assertFalse(bad_ad07.allowed)
        self.assertEqual(bad_ad07.decision_code, "UCP_REGULATED_HAZMAT_AIR_TRANSPORT_FORBIDDEN_BLOCKED")

        # AD-08
        raw_body = '{"id":"evt_01","state":"completed"}'
        ts = 1_792_555_000
        secret = "whsec_stage158_secret"
        sig = hmac.new(secret.encode("utf-8"), f"{ts}.{raw_body}".encode("utf-8"), hashlib.sha256).hexdigest()
        ok_ad08 = evaluate_acp_webhook_hmac_sequence_guard(
            webhook_secret=secret,
            signature_timestamp=ts,
            now_unix=ts + 15,
            raw_body=raw_body,
            provided_hmac_hex=sig,
            event_sequence=5,
            last_processed_sequence=4,
            current_session_state="ready_for_complete",
            incoming_event_state="completed",
        )
        self.assertTrue(ok_ad08.allowed)
        bad_ad08 = evaluate_acp_webhook_hmac_sequence_guard(
            webhook_secret=secret,
            signature_timestamp=ts,
            now_unix=ts + 15,
            raw_body=raw_body,
            provided_hmac_hex=sig,
            event_sequence=6,
            last_processed_sequence=5,
            current_session_state="completed",
            incoming_event_state="in_progress",
        )
        self.assertFalse(bad_ad08.allowed)
        self.assertEqual(bad_ad08.decision_code, "ACP_WEBHOOK_TERMINAL_STATE_REGRESSION_BLOCKED")

        # AD-09
        ok_ad09 = evaluate_acp_b2b_tax_exemption_certificate_guard(
            claim_tax_exempt=True,
            certificate_id="cert_tx_ca_998",
            certificate_Verified_by_authority=True,
            certificate_expires_at=1_800_000_000,
            now_unix=1_792_555_000,
            certificate_jurisdictions=["US-CA", "US-WA"],
            shipping_jurisdiction="US-CA",
            certificate_buyer_tax_id="EIN-94-1234567",
            session_buyer_tax_id="EIN-94-1234567",
            reported_tax_amount_minor=0,
            standard_tax_amount_minor=1_650,
        )
        self.assertTrue(ok_ad09.allowed)
        bad_ad09 = evaluate_acp_b2b_tax_exemption_certificate_guard(
            claim_tax_exempt=True,
            certificate_id="cert_tx_ca_998",
            certificate_Verified_by_authority=True,
            certificate_expires_at=1_800_000_000,
            now_unix=1_792_555_000,
            certificate_jurisdictions=["US-CA"],
            shipping_jurisdiction="US-NY",
            certificate_buyer_tax_id="EIN-94-1234567",
            session_buyer_tax_id="EIN-94-1234567",
            reported_tax_amount_minor=0,
            standard_tax_amount_minor=1_650,
        )
        self.assertFalse(bad_ad09.allowed)
        self.assertEqual(bad_ad09.decision_code, "ACP_B2B_TAX_EXEMPTION_CERTIFICATE_INVALID_BLOCKED")

    def test_ap2_mcp_stripe_tap_and_tau2_guards(self) -> None:
        # AD-10
        rp_hash = hashlib.sha256(b"checkout.merchant.example").hexdigest()
        ok_ad10 = evaluate_ap2_step_up_biometric_uv_guard(
            amount_minor=150_000,
            autonomous_limit_minor=50_000,
            risk_tier="high",
            webauthn_assertion_present=True,
            authenticator_flag_up=True,
            authenticator_flag_uv=True,
            rp_id_hash_hex=rp_hash,
            expected_rp_id="checkout.merchant.example",
        )
        self.assertTrue(ok_ad10.allowed)
        bad_ad10 = evaluate_ap2_step_up_biometric_uv_guard(
            amount_minor=150_000,
            autonomous_limit_minor=50_000,
            risk_tier="high",
            webauthn_assertion_present=True,
            authenticator_flag_up=True,
            authenticator_flag_uv=False,
            rp_id_hash_hex=rp_hash,
            expected_rp_id="checkout.merchant.example",
        )
        self.assertFalse(bad_ad10.allowed)
        self.assertEqual(bad_ad10.decision_code, "AP2_STEP_UP_WEBAUTHN_BIOMETRIC_UV_REQUIRED_BLOCKED")

        # AD-11
        ok_ad11 = evaluate_ap2_corporate_quorum_sod_guard(
            requester_principal_id="emp_alice",
            approver_principal_ids=["mgr_bob", "vp_carol"],
            authorized_finance_approvers=["mgr_bob", "vp_carol", "cfo_dave"],
            required_quorum=2,
            requisition_amount_minor=250_000,
            cost_center_available_budget_minor=500_000,
        )
        self.assertTrue(ok_ad11.allowed)
        bad_ad11 = evaluate_ap2_corporate_quorum_sod_guard(
            requester_principal_id="emp_alice",
            approver_principal_ids=["emp_alice", "mgr_bob"],
            authorized_finance_approvers=["emp_alice", "mgr_bob", "vp_carol"],
            required_quorum=2,
            requisition_amount_minor=250_000,
            cost_center_available_budget_minor=500_000,
        )
        self.assertFalse(bad_ad11.allowed)
        self.assertEqual(bad_ad11.decision_code, "AP2_CORPORATE_SOD_SELF_APPROVAL_BLOCKED")

        # AD-12
        ok_ad12 = evaluate_mcp_oauth_audience_passthrough_guard(
            token_aud="https://mcp.merchant.example/v1",
            canonical_mcp_server_uri="https://mcp.merchant.example/v1",
            token_cnf_jkt="jkt_sha256_abc123",
            dpop_proof_jkt="jkt_sha256_abc123",
            forward_caller_token_to_downstream=False,
        )
        self.assertTrue(ok_ad12.allowed)
        bad_ad12 = evaluate_mcp_oauth_audience_passthrough_guard(
            token_aud="https://mcp.merchant.example/v1",
            canonical_mcp_server_uri="https://mcp.merchant.example/v1",
            token_cnf_jkt="jkt_sha256_abc123",
            dpop_proof_jkt="jkt_sha256_abc123",
            forward_caller_token_to_downstream=True,
        )
        self.assertFalse(bad_ad12.allowed)
        self.assertEqual(bad_ad12.decision_code, "MCP_OAUTH_DOWNSTREAM_TOKEN_PASSTHROUGH_BLOCKED")

        # AD-13
        ok_ad13 = evaluate_stripe_connect_fee_transfer_guard(
            charge_amount_minor=10_000,
            application_fee_amount_minor=500,
            min_platform_fee_minor=300,
            transfer_data_amount_minor=9_500,
            on_behalf_of_country="US",
            settlement_currency_country="US",
            cross_border_transfers_enabled=False,
        )
        self.assertTrue(ok_ad13.allowed)
        bad_ad13 = evaluate_stripe_connect_fee_transfer_guard(
            charge_amount_minor=10_000,
            application_fee_amount_minor=500,
            min_platform_fee_minor=300,
            transfer_data_amount_minor=9_800,
            on_behalf_of_country="US",
            settlement_currency_country="US",
            cross_border_transfers_enabled=False,
        )
        self.assertFalse(bad_ad13.allowed)
        self.assertEqual(bad_ad13.decision_code, "STRIPE_CONNECT_TRANSFER_PLUS_FEE_EXCEEDS_CHARGE_BLOCKED")

        # AD-14
        challenge = hashlib.sha256(
            json.dumps(
                {
                    "amount_minor": 18_500,
                    "currency": "USD",
                    "merchant_id": "merch_tap_01",
                    "tap_session_nonce": "nonce_c2p_99",
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        ok_ad14 = evaluate_visa_tap_passkey_c2p_binding_guard(
            merchant_id="merch_tap_01",
            amount_minor=18_500,
            currency="USD",
            tap_session_nonce="nonce_c2p_99",
            client_data_challenge_hex=challenge,
            client_data_origin="https://checkout.merchant.example",
            expected_checkout_origin="https://checkout.merchant.example",
            presented_sign_count=42,
            stored_sign_count=41,
        )
        self.assertTrue(ok_ad14.allowed)
        bad_ad14 = evaluate_visa_tap_passkey_c2p_binding_guard(
            merchant_id="merch_tap_01",
            amount_minor=18_500,
            currency="USD",
            tap_session_nonce="nonce_c2p_99",
            client_data_challenge_hex=challenge,
            client_data_origin="https://checkout.merchant.example",
            expected_checkout_origin="https://checkout.merchant.example",
            presented_sign_count=41,
            stored_sign_count=41,
        )
        self.assertFalse(bad_ad14.allowed)
        self.assertEqual(bad_ad14.decision_code, "VISA_TAP_PASSKEY_SIGN_COUNT_REPLAY_BLOCKED")

        # AD-15
        ok_ad15 = evaluate_tau2_pharmacy_refill_prior_auth_guard(
            refills_remaining=2,
            is_controlled_substance=True,
            days_since_last_fill=28,
            day_supply=30,
            prescriber_npi_active=True,
            requires_prior_auth=True,
            prior_auth_approved=True,
        )
        self.assertTrue(ok_ad15.allowed)
        bad_ad15 = evaluate_tau2_pharmacy_refill_prior_auth_guard(
            refills_remaining=2,
            is_controlled_substance=True,
            days_since_last_fill=20,
            day_supply=30,
            prescriber_npi_active=True,
            requires_prior_auth=True,
            prior_auth_approved=True,
        )
        self.assertFalse(bad_ad15.allowed)
        self.assertEqual(bad_ad15.decision_code, "TAU2_PHARMACY_EARLY_REFILL_INTERVAL_BLOCKED")

        # AD-16
        ok_ad16 = evaluate_tau2_saas_contract_seat_downgrade_guard(
            requested_seats=120,
            contracted_min_seats=100,
            now_unix=1_792_555_000,
            contract_renewal_unix=1_798_000_000,
            is_non_renewal_request=False,
            required_notice_days=30,
            preserve_compliance_audit_logs=True,
        )
        self.assertTrue(ok_ad16.allowed)
        bad_ad16 = evaluate_tau2_saas_contract_seat_downgrade_guard(
            requested_seats=60,
            contracted_min_seats=100,
            now_unix=1_792_555_000,
            contract_renewal_unix=1_798_000_000,
            is_non_renewal_request=False,
            required_notice_days=30,
            preserve_compliance_audit_logs=True,
        )
        self.assertFalse(bad_ad16.allowed)
        self.assertEqual(bad_ad16.decision_code, "TAU2_SAAS_MID_TERM_BELOW_CONTRACTED_SEATS_BLOCKED")


if __name__ == "__main__":
    unittest.main()
