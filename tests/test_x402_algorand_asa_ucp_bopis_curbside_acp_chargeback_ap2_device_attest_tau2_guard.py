"""Unit tests for Stage 162 guardrails (AR-01..AR-16)."""

from __future__ import annotations

import hashlib
import hmac
import unittest

from lab.x402_algorand_asa_ucp_bopis_curbside_acp_chargeback_ap2_device_attest_tau2_guard import (
    run_demo,
    verify_acp_b2b_tax_exemption_certificate_guard,
    verify_acp_chargeback_representment_guard,
    verify_ap2_hardware_device_attestation_guard,
    verify_ap2_treasury_cosigner_threshold_guard,
    verify_mcp_sampling_create_message_guard,
    verify_stripe_ai_portal_session_scope_guard,
    verify_tau2_hazmat_coldchain_carrier_guard,
    verify_tau2_utility_meter_billing_dispute_guard,
    verify_ucp_bopis_curbside_pickup_guard,
    verify_ucp_dcc_multi_currency_parity_guard,
    verify_ucp_trade_in_credit_mandate_guard,
    verify_visa_tap_mit_standing_instruction_guard,
    verify_x402_algorand_asa_transfer_guard,
    verify_x402_client_session_budget_guard,
    verify_x402_facilitator_webhook_hmac_guard,
    verify_x402_polkadot_assethub_keep_alive_guard,
)


class Stage162GuardTests(unittest.TestCase):
    def test_demo_all_passed(self) -> None:
        summary = run_demo()
        self.assertTrue(summary["all_passed"])
        self.assertEqual(len(summary["checks"]), 16)

    def test_x402_and_ucp_guards_block_adversarial_inputs(self) -> None:
        h64 = "c" * 64
        # AR-01: Algorand asset_close_to drain blocked
        r01 = verify_x402_algorand_asa_transfer_guard(
            network="algorand:wGHE2Pwdvd7S12BL5FaOP20EGYesN73k",
            tx_type="axfer",
            xfer_asset_id=31566704,
            expected_asa_id=31566704,
            asset_receiver="ALGO_MERCHANT_ADDR",
            expected_pay_to="ALGO_MERCHANT_ADDR",
            asset_amount=5_000_000,
            min_required_amount=5_000_000,
            asset_close_to="ATTACKER_CLOSE_TO_ADDR",
            asset_sender="",
            first_valid_round=42_000_000,
            last_valid_round=42_000_800,
            current_round=42_000_100,
        )
        self.assertFalse(r01.allowed)
        self.assertEqual(r01.decision_code, "X402_ALGORAND_ASSET_CLOSE_TO_FORBIDDEN")

        # AR-02: Polkadot non-keep_alive or immortal era blocked
        r02 = verify_x402_polkadot_assethub_keep_alive_guard(
            network="polkadot:68d56f15f85d3136970ec16946040bc1",
            pallet_call="Assets::transfer",
            keep_alive=False,
            asset_id=1337,
            expected_asset_id=1337,
            beneficiary="15oF4uVJwmo4TdGW7VfQxNLavjCXviqxT9S1MgbjMNHr6Sp5",
            expected_pay_to="15oF4uVJwmo4TdGW7VfQxNLavjCXviqxT9S1MgbjMNHr6Sp5",
            amount=5_000_000,
            min_required_amount=5_000_000,
            is_mortal_era=True,
            era_period_blocks=64,
            signed_genesis_hash="0x68d56f15f85d3136970ec16946040bc1",
            expected_genesis_hash="0x68d56f15f85d3136970ec16946040bc1",
        )
        self.assertFalse(r02.allowed)
        self.assertEqual(r02.decision_code, "X402_POLKADOT_KEEP_ALIVE_REQUIRED")

        # AR-03: Facilitator webhook event replay blocked
        secret = "whsec_test"
        body = '{"ok":true}'
        sig = hmac.new(
            secret.encode("utf-8"),
            f"1761000000.evt_dup.{body}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        r03 = verify_x402_facilitator_webhook_hmac_guard(
            webhook_secret=secret,
            timestamp_epoch=1761000000,
            current_epoch=1761000010,
            event_id="evt_dup",
            raw_body=body,
            provided_signature_hex=sig,
            seen_event_ids=["evt_dup"],
        )
        self.assertFalse(r03.allowed)
        self.assertEqual(r03.decision_code, "X402_WEBHOOK_EVENT_REPLAY_DETECTED")

        # AR-04: Client origin budget exhaustion blocked
        r04 = verify_x402_client_session_budget_guard(
            origin="https://api.merchant.example",
            requested_payment_atomic=600_000,
            cumulative_origin_spent_atomic=1_600_000,
            cumulative_session_spent_atomic=2_000_000,
            max_payment_per_request_atomic=1_000_000,
            max_payment_per_origin_atomic=2_000_000,
            max_payment_per_session_atomic=5_000_000,
        )
        self.assertFalse(r04.allowed)
        self.assertEqual(r04.decision_code, "X402_CLIENT_ORIGIN_BUDGET_EXHAUSTED")

        # AR-05: BOPIS premature release PIN blocked
        r05 = verify_ucp_bopis_curbside_pickup_guard(
            pickup_store_id="store_nyc_01",
            active_store_ids=["store_nyc_01"],
            pickup_window_start_epoch=1761000000,
            pickup_window_end_epoch=1761086400,
            authorized_pickup_person_sha256=h64,
            order_fulfillment_state="picking_in_progress",
            emit_pickup_release_pin=True,
        )
        self.assertFalse(r05.allowed)
        self.assertEqual(r05.decision_code, "UCP_BOPIS_PREMATURE_RELEASE_PIN_BLOCKED")

        # AR-06: DCC excessive markup blocked
        r06 = verify_ucp_dcc_multi_currency_parity_guard(
            display_currency="EUR",
            settlement_currency="USD",
            fx_rate_quote_id="fxq_162",
            dcc_applied=True,
            dcc_markup_bps=450,
            buyer_dcc_opt_in=True,
        )
        self.assertFalse(r06.allowed)
        self.assertEqual(r06.decision_code, "UCP_DCC_MARKUP_BPS_EXCEEDS_CAP")

        # AR-07: Trade-in missing clawback mandate blocked
        r07 = verify_ucp_trade_in_credit_mandate_guard(
            instant_trade_in_credit_applied=True,
            trade_in_serial_sha256=h64,
            provisional_credit_minor=35000,
            max_trade_in_credit_minor=50000,
            new_item_price_minor=99900,
            clawback_authorization_mandate_id="",
            inspection_deadline_days=14,
        )
        self.assertFalse(r07.allowed)
        self.assertEqual(r07.decision_code, "UCP_TRADE_IN_CLAWBACK_MANDATE_REQUIRED")

    def test_acp_ap2_mcp_stripe_tap_and_tau2_guards_block_adversarial_inputs(self) -> None:
        h64 = "c" * 64
        # AR-08: Chargeback representment past due date blocked
        r08 = verify_acp_chargeback_representment_guard(
            dispute_id="dp_162",
            order_receipt_sha256=h64,
            delivery_proof_sha256=h64,
            user_approval_jws="eyJhbGciOiJFZERTQSJ9.eyJhcHByb3ZhbCI6dHJ1ZX0.c2ln",
            evidence_submitted_epoch=1761700000,
            dispute_due_by_epoch=1761600000,
            disputed_amount_minor=12500,
            receipt_total_minor=12500,
        )
        self.assertFalse(r08.allowed)
        self.assertEqual(r08.decision_code, "ACP_REPRESENTMENT_DEADLINE_EXPIRED")

        # AR-09: Tax-exempt jurisdiction mismatch blocked
        r09 = verify_acp_b2b_tax_exemption_certificate_guard(
            tax_exempt_claimed=True,
            tax_minor=0,
            tax_exemption_certificate_id="txcert_ny_9981",
            certificate_jurisdiction="US-NY",
            shipping_jurisdiction="US-CA",
            certificate_expires_epoch=1790000000,
            current_epoch=1761000000,
            verified_by_tax_engine=True,
        )
        self.assertFalse(r09.allowed)
        self.assertEqual(r09.decision_code, "ACP_TAX_EXEMPT_JURISDICTION_MISMATCH")

        # AR-10: AP2 weak device attestation verdict blocked
        r10 = verify_ap2_hardware_device_attestation_guard(
            amount_minor=150000,
            high_value_threshold_minor=100000,
            device_attestation_verdict="MEETS_BASIC_INTEGRITY",
            attested_public_key_thumbprint="jkt_hw_se_01",
            mandate_cnf_jkt="jkt_hw_se_01",
            attestation_issued_epoch=1761000000,
            current_epoch=1761000090,
        )
        self.assertFalse(r10.allowed)
        self.assertEqual(r10.decision_code, "AP2_DEVICE_ATTESTATION_STRONG_INTEGRITY_REQUIRED")

        # AR-11: AP2 duplicate co-signer fails quorum
        r11 = verify_ap2_treasury_cosigner_threshold_guard(
            mandate_digest_sha256=h64,
            required_threshold_m=2,
            authorized_treasury_signers=["cfo_key", "controller_key"],
            cosigner_entries=[
                {"signer_id": "cfo_key", "signed_digest_sha256": h64, "signature_valid": True},
                {"signer_id": "cfo_key", "signed_digest_sha256": h64, "signature_valid": True},
            ],
        )
        self.assertFalse(r11.allowed)
        self.assertEqual(r11.decision_code, "AP2_TREASURY_DUPLICATE_COSIGNER_BLOCKED")

        # AR-12: MCP sampling allServers context exfiltration blocked
        r12 = verify_mcp_sampling_create_message_guard(
            human_sampled_approval=True,
            max_tokens=1024,
            include_context="allServers",
            sampling_depth=1,
            system_prompt="Summarize warranty.",
        )
        self.assertFalse(r12.allowed)
        self.assertEqual(r12.decision_code, "MCP_SAMPLING_ALL_SERVERS_CONTEXT_EXFIL_BLOCKED")

        # AR-13: Stripe portal unsafe payment method removal on active sub blocked
        r13 = verify_stripe_ai_portal_session_scope_guard(
            customer_id="cus_principal_01",
            bound_principal_customer_id="cus_principal_01",
            has_active_subscription=True,
            allow_payment_method_removal_without_replacement=True,
            requested_Switch_price_ids=["price_pro_monthly"],
            catalog_allowed_price_ids=["price_pro_monthly"],
        )
        self.assertFalse(r13.allowed)
        self.assertEqual(
            r13.decision_code, "STRIPE_PORTAL_UNSAFE_PM_REMOVAL_ON_ACTIVE_SUB_BLOCKED"
        )

        # AR-14: Visa TAP MIT missing initial CIT trace blocked
        r14 = verify_visa_tap_mit_standing_instruction_guard(
            is_merchant_initiated=True,
            initial_cit_transaction_id="",
            standing_instruction_agreement_digest=h64,
            mit_amount_minor=4900,
            agreement_max_variable_amount_minor=6000,
            mit_interval_days=30,
            agreement_min_interval_days=28,
        )
        self.assertFalse(r14.allowed)
        self.assertEqual(r14.decision_code, "VISA_TAP_MIT_INITIAL_CIT_TRACE_MISSING")

        # AR-15: tau2 utility credit exceeding overcharge blocked
        r15 = verify_tau2_utility_meter_billing_dispute_guard(
            smart_meter_telemetry_verified=True,
            billed_usage_kwh=850,
            verified_meter_reading_kwh=600,
            tariff_minor_per_kwh=20,
            requested_credit_minor=9000,
        )
        self.assertFalse(r15.allowed)
        self.assertEqual(r15.decision_code, "TAU2_UTILITY_CREDIT_EXCEEDS_OVERCHARGE")

        # AR-16: tau2 HazMat shipment without certified carrier blocked
        r16 = verify_tau2_hazmat_coldchain_carrier_guard(
            un_hazmat_class="UN3480",
            requires_reefer_cold_chain=True,
            carrier_hazmat_certified=False,
            carrier_reefer_certified=True,
            route_tunnel_restriction_compliant=True,
        )
        self.assertFalse(r16.allowed)
        self.assertEqual(r16.decision_code, "TAU2_CARRIER_HAZMAT_CERTIFICATION_MISSING")


if __name__ == "__main__":
    unittest.main()
