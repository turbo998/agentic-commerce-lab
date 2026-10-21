"""Unit tests for Stage 154 deterministic guardrails (FX-01..FX-16)."""

from __future__ import annotations

import base64
import hashlib
import unittest

from lab.x402_fetch_cap_xrpl_ucp_bundle_allergen_acp_term_bind_ap2_jpy_tau2_guard import (
    ACP_OPENAPI_REQUIRED_PARITY_FIELDS,
    evaluate_acp_agent_identity_host_auth_and_mcp_idempotency,
    evaluate_acp_signature_freshness_3ds_binding_and_item_url,
    evaluate_ap2_iso4217_budget_multihop_and_kb_sdjwt,
    evaluate_ap2_receipt_verifier_delivery_constraint_and_openid4vp,
    evaluate_mcp_supply_chain_routing_and_token_privilege,
    evaluate_stripe_worker_thread_loop_and_host_action_gate,
    evaluate_tau2_airline_telecom_retail_and_reward_integrity,
    evaluate_ucp_ad_attribution_root_schema_and_nano_instrument,
    evaluate_ucp_address_components_fulfillment_and_bundles,
    evaluate_ucp_payment_terms_idp_attestation_and_option_rules,
    evaluate_ucp_similarity_allergen_and_ecdsa_raw_rs,
    evaluate_visa_tap_mtls_passport_and_correctness_receipt,
    evaluate_x402_fetch_overcharge_cap_and_header_parity,
    evaluate_x402_paywall_route_and_siwx_entitlement_guard,
    evaluate_x402_recovery_fastify_and_stellar_smart_account_fee,
    evaluate_x402_wildcard_network_and_xrpl_multisig,
)


def _b64u_sha256(text: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(text.encode("ascii")).digest()).decode("ascii").rstrip("=")


class Stage154GuardTest(unittest.TestCase):
    def test_fx01_to_fx04_x402_guards(self) -> None:
        # FX-01
        ok1 = evaluate_x402_fetch_overcharge_cap_and_header_parity(
            declared_402_amount_atomic=100_000,
            caller_max_amount_atomic=150_000,
            quoted_amount_atomic=100_000,
            request_headers={"X-PAYMENT": "eyJhbGciOiJFZERTQSJ9.payload"},
            verify_response={"isValid": True},
            settle_response={"success": True},
        )
        self.assertTrue(ok1.allowed)
        bad1 = evaluate_x402_fetch_overcharge_cap_and_header_parity(
            declared_402_amount_atomic=1_000_000,
            caller_max_amount_atomic=100_000,
            quoted_amount_atomic=100_000,
            request_headers={"PAYMENT-SIGNATURE": "eyJhbGciOiJFZERTQSJ9.payload"},
            verify_response={"isValid": True},
            settle_response={"success": True},
        )
        self.assertFalse(bad1.allowed)
        self.assertEqual(bad1.decision_code, "X402_FETCH_SERVER_OVERCHARGE_EXCEEDS_MAX_AMOUNT_BLOCKED")

        # FX-02
        ok2 = evaluate_x402_wildcard_network_and_xrpl_multisig(
            registered_patterns=["eip155:*", "xrpl:*"],
            route_network="xrpl:0",
            xrpl_tx={
                "SigningPubKey": "",
                "InvoiceID": "a" * 64,
                "SourceTag": 20261021,
                "Signers": [
                    {"Signer": {"Account": "rSigner1", "SigningPubKey": "ED01", "TxnSignature": "SIG1", "signature_valid": True}},
                    {"Signer": {"Account": "rSigner2", "SigningPubKey": "ED02", "TxnSignature": "SIG2", "signature_valid": True}},
                ],
            },
            signer_quorum=3,
            signer_list_weights={"rSigner1": 2, "rSigner2": 2},
        )
        self.assertTrue(ok2.allowed)
        bad2 = evaluate_x402_wildcard_network_and_xrpl_multisig(
            registered_patterns=["eip155:1"],
            route_network="eip155:8453",
            xrpl_tx={"SigningPubKey": "", "InvoiceID": "a" * 64, "SourceTag": 1},
            signer_quorum=1,
            signer_list_weights={},
        )
        self.assertFalse(bad2.allowed)
        self.assertEqual(bad2.decision_code, "X402_WILDCARD_NETWORK_SCHEME_UNRESOLVED")

        # FX-03
        ok3 = evaluate_x402_paywall_route_and_siwx_entitlement_guard(
            protected_route_pattern="/api/reports/:id",
            servlet_context_path="/app",
            raw_request_uri="/app/api/reports/rep_42",
            payment_present=True,
            siwx_client_resource_url="https://api.example.com/app/api/reports/rep_42",
            server_canonical_url="https://api.example.com/app/api/reports/rep_42",
        )
        self.assertTrue(ok3.allowed)
        bad3 = evaluate_x402_paywall_route_and_siwx_entitlement_guard(
            protected_route_pattern="/api/reports/:id",
            servlet_context_path="/app",
            raw_request_uri="/app/api/reports/rep_42",
            payment_present=True,
            siwx_client_resource_url="https://api.example.com/app/api/admin/unlock_all",
            server_canonical_url="https://api.example.com/app/api/reports/rep_42",
        )
        self.assertFalse(bad3.allowed)
        self.assertEqual(bad3.decision_code, "X402_SIWX_CLIENT_RESOURCE_URL_ENTITLEMENT_SPOOF_BLOCKED")

        # FX-04
        ok4 = evaluate_x402_recovery_fastify_and_stellar_smart_account_fee(
            is_retry_recovery=True,
            settled_record={"settled": True, "request_digest": "sha256:req1", "tx_hash": "0xabc", "evidence_projection": {"ok": True}},
            current_request_digest="sha256:req1",
            fastify_hook_stage="preHandler",
            fastify_raw_hijacked_without_settle=False,
            stellar_is_smart_account=True,
            stellar_cross_contract_auth_calls=2,
            stellar_required_fee_stroops=180_000,
            facilitator_max_fee_stroops=300_000,
        )
        self.assertTrue(ok4.allowed)
        bad4 = evaluate_x402_recovery_fastify_and_stellar_smart_account_fee(
            is_retry_recovery=False,
            settled_record=None,
            current_request_digest="sha256:req1",
            fastify_hook_stage="preHandler",
            fastify_raw_hijacked_without_settle=False,
            stellar_is_smart_account=True,
            stellar_cross_contract_auth_calls=2,
            stellar_required_fee_stroops=180_000,
            facilitator_max_fee_stroops=50_000,
        )
        self.assertFalse(bad4.allowed)
        self.assertEqual(bad4.decision_code, "X402_STELLAR_SMART_ACCOUNT_FEE_CEILING_TOO_LOW_BLOCKED")

    def test_fx05_to_fx10_ucp_and_acp_guards(self) -> None:
        # FX-05
        ok5 = evaluate_ucp_address_components_fulfillment_and_bundles(
            postal_address={
                "address_line_1": "Marktplatz 14",
                "address_line_components": {"street_name": "Marktplatz", "street_number": "14"},
            },
            fulfillment_event_type="out_for_delivery",
            line_items=[
                {"id": "bundle_1", "total_minor": 5000, "is_atomic_bundle": True},
                {"id": "comp_1", "parent_id": "bundle_1", "total_minor": 3000},
                {"id": "comp_2", "parent_id": "bundle_1", "total_minor": 2000},
            ],
            attempted_partial_component_cancel=False,
        )
        self.assertTrue(ok5.allowed)
        bad5 = evaluate_ucp_address_components_fulfillment_and_bundles(
            postal_address={"address_line_1": "Marktplatz 14"},
            fulfillment_event_type="out_for_delivery",
            line_items=[
                {"id": "bundle_1", "total_minor": 5000, "is_atomic_bundle": True},
                {"id": "comp_1", "parent_id": "bundle_1", "total_minor": 3000},
                {"id": "comp_2", "parent_id": "bundle_1", "total_minor": 2000},
            ],
            attempted_partial_component_cancel=True,
        )
        self.assertFalse(bad5.allowed)
        self.assertEqual(bad5.decision_code, "UCP_ATOMIC_BUNDLE_PARTIAL_COMPONENT_CANCEL_BLOCKED")

        # FX-06
        ok6 = evaluate_ucp_similarity_allergen_and_ecdsa_raw_rs(
            similarity_query={"like": ["sku_anchor_1"], "substitutes": [{"id": "sku_sub_2", "in_stock": True}]},
            buyer_allergen_restrictions=["peanuts", "shellfish"],
            dish_allergen_status={"peanuts": "free_from", "shellfish": "free_from"},
            ecdsa_curve="P-256",
            signature_bytes=b"\x11" * 64,
        )
        self.assertTrue(ok6.allowed)
        bad6 = evaluate_ucp_similarity_allergen_and_ecdsa_raw_rs(
            similarity_query={"like": ["sku_anchor_1"], "substitutes": [{"id": "sku_sub_2", "in_stock": True}]},
            buyer_allergen_restrictions=["peanuts"],
            dish_allergen_status={"peanuts": "unknown"},
            ecdsa_curve="P-256",
            signature_bytes=b"\x11" * 64,
        )
        self.assertFalse(bad6.allowed)
        self.assertEqual(bad6.decision_code, "UCP_FOOD_ALLERGEN_UNSAFE_OR_UNKNOWN_FOR_BUYER_BLOCKED")

        # FX-07
        ok7 = evaluate_ucp_ad_attribution_root_schema_and_nano_instrument(
            ad_attribution={"campaign_id": "cmp_101", "click_id": "clk_998"},
            extension_schema={"type": "object", "properties": {"items": {"type": "array"}}},
            nano_instrument={
                "type": "nano",
                "account": "nano_1" + "a" * 59,
                "block_hash": "b" * 64,
                "amount_raw": "100000000000000000000000000000",
                "work_nonce": "c" * 16,
            },
        )
        self.assertTrue(ok7.allowed)
        bad7 = evaluate_ucp_ad_attribution_root_schema_and_nano_instrument(
            ad_attribution={"campaign_id": "cmp_101", "click_id": "clk_998"},
            extension_schema={"type": "array"},
            nano_instrument={
                "type": "nano",
                "account": "nano_1" + "a" * 59,
                "block_hash": "b" * 64,
                "amount_raw": "1000",
                "work_nonce": "c" * 16,
            },
        )
        self.assertFalse(bad7.allowed)
        self.assertEqual(bad7.decision_code, "UCP_ROOT_ARRAY_SCHEMA_ANTIPATTERN_BLOCKED")

        # FX-08
        ok8 = evaluate_ucp_payment_terms_idp_attestation_and_option_rules(
            complete_payment_obj={"selected_term_id": "net_30", "credit_agreement_id": "agr_77"},
            payment_terms_active=True,
            first_contact_idp_headers={
                "OAuth-Client-Attestation": "h.p.s",
                "OAuth-Client-Attestation-PoP": "h.p.s",
            },
            mutation_admission={"admission_coverage_hash": "sha256:cov1", "satisfaction_proof": "sig:sat1"},
            option_selection={"min_selected": 1, "max_selected": 2, "selected_values": [{"id": "opt_a", "quantity": 1, "max_quantity": 2}]},
        )
        self.assertTrue(ok8.allowed)
        bad8 = evaluate_ucp_payment_terms_idp_attestation_and_option_rules(
            complete_payment_obj={},
            payment_terms_active=True,
            first_contact_idp_headers={
                "OAuth-Client-Attestation": "h.p.s",
                "OAuth-Client-Attestation-PoP": "h.p.s",
            },
            mutation_admission={"admission_coverage_hash": "sha256:cov1", "satisfaction_proof": "sig:sat1"},
            option_selection={"min_selected": 1, "max_selected": 2, "selected_values": [{"id": "opt_a", "quantity": 1, "max_quantity": 2}]},
        )
        self.assertFalse(bad8.allowed)
        self.assertEqual(bad8.decision_code, "UCP_COMPLETE_EMPTY_PAYMENT_OBJECT_BLOCKED")

        # FX-09
        ok9 = evaluate_acp_agent_identity_host_auth_and_mcp_idempotency(
            merchant_has_stored_agent_id=False,
            ephemeral_agent_attestation_jws="h.p.s",
            host_authorization={"checkout_session_id": "cs_1", "max_amount_minor": 9000, "signature_valid": True},
            checkout_session_id="cs_1",
            spend_amount_minor=8500,
            openapi_declared_fields=set(ACP_OPENAPI_REQUIRED_PARITY_FIELDS),
            mcp_tool_name="checkout.complete",
            mcp_meta={"idempotency_key": "idem_20261021_abcdef123456"},
        )
        self.assertTrue(ok9.allowed)
        bad9 = evaluate_acp_agent_identity_host_auth_and_mcp_idempotency(
            merchant_has_stored_agent_id=False,
            ephemeral_agent_attestation_jws="h.p.s",
            host_authorization={"checkout_session_id": "cs_1", "max_amount_minor": 9000, "signature_valid": True},
            checkout_session_id="cs_1",
            spend_amount_minor=8500,
            openapi_declared_fields=set(ACP_OPENAPI_REQUIRED_PARITY_FIELDS),
            mcp_tool_name="checkout.complete",
            mcp_meta={},
        )
        self.assertFalse(bad9.allowed)
        self.assertEqual(bad9.decision_code, "ACP_MCP_MUTATING_CHECKOUT_IDEMPOTENCY_KEY_MISSING")

        # FX-10
        terms = {"checkout_session_id": "cs_1", "merchant_id": "m_1", "amount_minor": 8500, "currency": "USD", "acquirer_bin": "444455"}
        ok10 = evaluate_acp_signature_freshness_3ds_binding_and_item_url(
            endpoint_name="delegate_payment",
            signature_header="sig_b64u_xyz",
            timestamp_epoch_s=1_760_000_000,
            now_epoch_s=1_760_000_050,
            auth_result={**terms, "used": False, "expires_at": 1_760_000_600},
            final_terms=terms,
            item_url="https://merchant.example.com/products/pro-widget",
        )
        self.assertTrue(ok10.allowed)
        bad10 = evaluate_acp_signature_freshness_3ds_binding_and_item_url(
            endpoint_name="delegate_payment",
            signature_header="sig_b64u_xyz",
            timestamp_epoch_s=1_760_000_000,
            now_epoch_s=1_760_000_050,
            auth_result={**terms, "amount_minor": 4500, "used": False, "expires_at": 1_760_000_600},
            final_terms=terms,
            item_url="https://merchant.example.com/products/pro-widget",
        )
        self.assertFalse(bad10.allowed)
        self.assertEqual(bad10.decision_code, "ACP_DELEGATE_AUTH_RESULT_FINAL_TERMS_MISMATCH_BLOCKED")

    def test_fx11_to_fx16_ap2_mcp_stripe_tap_and_tau2_guards(self) -> None:
        # FX-11
        ok11 = evaluate_ap2_receipt_verifier_delivery_constraint_and_openid4vp(
            receipt_key_type="EllipticCurvePublicKey",
            has_reference_in_store_cb=None,
            receipt_reference_id="ref_101",
            mandate_delivery_constraint={"ship_to_address_hash": "sha256:addr1", "delivery_email_hash": "sha256:mail1"},
            checkout_delivery={"ship_to_address_hash": "sha256:addr1", "delivery_email_hash": "sha256:mail1"},
            openid4vp_request={"dcql_query": {"credentials": []}, "transaction_data": ["tx_1"]},
            sample_log_line="A2A status=200 mandates_verified=1",
        )
        self.assertTrue(ok11.allowed)
        bad11 = evaluate_ap2_receipt_verifier_delivery_constraint_and_openid4vp(
            receipt_key_type="EllipticCurvePublicKey",
            has_reference_in_store_cb=None,
            receipt_reference_id="ref_101",
            mandate_delivery_constraint={"ship_to_address_hash": "sha256:addr1", "delivery_email_hash": "sha256:mail1"},
            checkout_delivery={"ship_to_address_hash": "sha256:attacker_addr", "delivery_email_hash": "sha256:mail1"},
            openid4vp_request={"dcql_query": {"credentials": []}, "transaction_data": ["tx_1"]},
            sample_log_line="A2A status=200 mandates_verified=1",
        )
        self.assertFalse(bad11.allowed)
        self.assertEqual(bad11.decision_code, "AP2_MANDATE_DELIVERY_DESTINATION_REDIRECT_BLOCKED")

        # FX-12
        c_jwt = "eyJhbGciOiJFZERTQSJ9.eyJjaGVja291dF9pZCI6ImNrXzEifQ.c2ln"
        c_hash = _b64u_sha256(c_jwt)
        ok12 = evaluate_ap2_iso4217_budget_multihop_and_kb_sdjwt(
            currency="JPY",
            budget_max_major="5000",
            requested_amount_minor=5000,
            sd_jwt_chain="h1.p1.s1~d1~~h2.p2.s2~d2~kb",
            presented_checkout_jwt=c_jwt,
            closed_mandate_checkout_hash=c_hash,
            terminal_kb_payload={"aud": "https://merchant.example.com", "nonce": "n_998877"},
            expected_aud="https://merchant.example.com",
            expected_nonce="n_998877",
        )
        self.assertTrue(ok12.allowed)
        # In JPY (0 decimals), 5000 JPY is 5000 minor units, NOT 500,000 (#368)
        bad12 = evaluate_ap2_iso4217_budget_multihop_and_kb_sdjwt(
            currency="JPY",
            budget_max_major="5000",
            requested_amount_minor=500_000,
            sd_jwt_chain="h1.p1.s1~d1~~h2.p2.s2~d2~kb",
            presented_checkout_jwt=c_jwt,
            closed_mandate_checkout_hash=c_hash,
            terminal_kb_payload={"aud": "https://merchant.example.com", "nonce": "n_998877"},
            expected_aud="https://merchant.example.com",
            expected_nonce="n_998877",
        )
        self.assertFalse(bad12.allowed)
        self.assertEqual(bad12.decision_code, "AP2_BUDGET_ISO4217_MINOR_CAP_EXCEEDED_BLOCKED")

        # FX-13
        ok13 = evaluate_mcp_supply_chain_routing_and_token_privilege(
            command_args=["npx", "-y", "@stripe/mcp@1.4.2"],
            package_integrity_sha512="sha512-abcdef1234567890",
            server_info={"description": "Stripe payment and checkout orchestration MCP server", "domain_tags": ["payments", "billing"]},
            transport_mode="serveStdio",
            access_token_claims={"aud": "mcp://stripe-checkout-server", "is_passthrough_project_token": False},
            mcp_server_resource_uri="mcp://stripe-checkout-server",
        )
        self.assertTrue(ok13.allowed)
        bad13 = evaluate_mcp_supply_chain_routing_and_token_privilege(
            command_args=["npx", "-y", "@stripe/mcp"],
            package_integrity_sha512=None,
            server_info={"description": "Stripe payment and checkout orchestration MCP server", "domain_tags": ["payments"]},
            transport_mode="serveStdio",
            access_token_claims={"aud": "mcp://stripe-checkout-server", "is_passthrough_project_token": False},
            mcp_server_resource_uri="mcp://stripe-checkout-server",
        )
        self.assertFalse(bad13.allowed)
        self.assertEqual(bad13.decision_code, "MCP_UNPINNED_NPX_AUTO_INSTALL_SUPPLY_CHAIN_BLOCKED")

        # FX-14
        ok14 = evaluate_stripe_worker_thread_loop_and_host_action_gate(
            in_worker_thread_without_loop=True,
            uses_get_event_loop_directly=False,
            tool_name="create_payment_intent",
            is_mutating_pay_tool=True,
            host_action_attestation={"decision": "ALLOW", "tool": "create_payment_intent"},
            enforces_mandatory_stripe_first_directory=False,
            user_requested_connect_or_billing=False,
            injected_unsolicited_connect_sequencing=False,
        )
        self.assertTrue(ok14.allowed)
        bad14 = evaluate_stripe_worker_thread_loop_and_host_action_gate(
            in_worker_thread_without_loop=True,
            uses_get_event_loop_directly=True,
            tool_name="create_payment_intent",
            is_mutating_pay_tool=True,
            host_action_attestation={"decision": "ALLOW", "tool": "create_payment_intent"},
            enforces_mandatory_stripe_first_directory=False,
            user_requested_connect_or_billing=False,
            injected_unsolicited_connect_sequencing=False,
        )
        self.assertFalse(bad14.allowed)
        self.assertEqual(bad14.decision_code, "STRIPE_WORKER_THREAD_NO_CURRENT_EVENT_LOOP_CRASH_BLOCKED")

        # FX-15
        ok15 = evaluate_visa_tap_mtls_passport_and_correctness_receipt(
            mtls_cert_thumbprint_s256="x5t_sha256_cert_01",
            rfc9421_key_bound_thumbprint="x5t_sha256_cert_01",
            agent_passport={"agent_did": "did:web:agent.example.com", "values_commitment_hash": "sha256:val1"},
            nonce="nonce_20261021_abcdef12",
            seen_nonces=set(),
            correctness_commitment={"order_spec_hash": "sha256:ord1", "dispute_arbitration_uri": "https://tap.visa.com/disputes"},
            cors_allow_origins=["http://localhost:3000", "http://localhost:3001"],
        )
        self.assertTrue(ok15.allowed)
        bad15 = evaluate_visa_tap_mtls_passport_and_correctness_receipt(
            mtls_cert_thumbprint_s256="x5t_sha256_cert_01",
            rfc9421_key_bound_thumbprint="x5t_sha256_cert_01",
            agent_passport={"agent_did": "did:web:agent.example.com", "values_commitment_hash": "sha256:val1"},
            nonce="nonce_20261021_abcdef12",
            seen_nonces={"nonce_20261021_abcdef12"},
            correctness_commitment={"order_spec_hash": "sha256:ord1", "dispute_arbitration_uri": "https://tap.visa.com/disputes"},
            cors_allow_origins=["http://localhost:3000", "http://localhost:3001"],
        )
        self.assertFalse(bad15.allowed)
        self.assertEqual(bad15.decision_code, "VISA_TAP_NONCE_REPLAY_OR_LOW_ENTROPY_BLOCKED")

        # FX-16
        ok16 = evaluate_tau2_airline_telecom_retail_and_reward_integrity(
            flight_total_duration_minutes=165,
            max_upgrade_duration_minutes=180,
            requested_flight_upgrade=True,
            telecom_line_state={"overdue_bill_unpaid": False, "contract_ended": False},
            called_resume_line=True,
            retail_exchange_old_item_id="item_blue_m",
            retail_exchange_new_item_id="item_blue_l",
            apn_mmsc_url="http://mms.carrier.example.com",
            gold_action_counts={"get_account_transactions": 2},
            agent_action_counts={"get_account_transactions": 2},
            reward_from_live_env_hash=True,
        )
        self.assertTrue(ok16.allowed)
        bad16 = evaluate_tau2_airline_telecom_retail_and_reward_integrity(
            flight_total_duration_minutes=420,
            max_upgrade_duration_minutes=180,
            requested_flight_upgrade=True,
            telecom_line_state={"overdue_bill_unpaid": False, "contract_ended": False},
            called_resume_line=True,
            retail_exchange_old_item_id="item_blue_m",
            retail_exchange_new_item_id="item_blue_l",
            apn_mmsc_url="http://mms.carrier.example.com",
            gold_action_counts={"get_account_transactions": 2},
            agent_action_counts={"get_account_transactions": 2},
            reward_from_live_env_hash=True,
        )
        self.assertFalse(bad16.allowed)
        self.assertEqual(bad16.decision_code, "TAU2_AIRLINE_DURATION_INCLUDING_LAYOVER_EXCEEDED_BLOCKED")


if __name__ == "__main__":
    unittest.main()
