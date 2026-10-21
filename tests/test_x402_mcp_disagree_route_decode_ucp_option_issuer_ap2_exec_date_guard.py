import unittest

from lab.x402_mcp_disagree_route_decode_ucp_option_issuer_ap2_exec_date_guard import (
    validate_acp_session_context_and_flat_error_guard,
    validate_ap2_exec_date_token_binding_merchant_kb_guard,
    validate_mcp_signed_manifest_stripe_toolkit_and_tau2_live_db_guard,
    validate_ucp_option_selection_and_issuer_anchor_guard,
    validate_x402_mcp_payment_disagreement_and_route_guard,
)


class TestStage142Guards(unittest.TestCase):
    def test_x402_mcp_disagreement_route_decode_and_settlement_guard(self) -> None:
        ok = validate_x402_mcp_payment_disagreement_and_route_guard(
            structured_payment_required={"amount": "1000", "network": "eip155:8453"},
            text_payment_required={"amount": "1000", "network": "eip155:8453"},
            route_template="/api/v1/weather",
            authorized_max_amount=1000,
            settlement_override_amount=1000,
            charged_amount_str="1000",
            charged_cumulative_amount_str="5000",
            discovery_resource_url="mcp://tool/get_weather",
            mcp_result_meta={"x402/payment-response": {"success": True}},
            mcp_result_dunder_meta=None,
        )
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.metadata["resolved_meta_source"], "meta")

        bad = validate_x402_mcp_payment_disagreement_and_route_guard(
            structured_payment_required={"amount": "999999", "network": "eip155:8453"},
            text_payment_required={"amount": "1000", "network": "eip155:8453"},
            route_template="/foo/%252e%252e%252fsecret",
            authorized_max_amount=1000,
            settlement_override_amount=1500,
            charged_amount_str="1000",
            charged_cumulative_amount_str="not_digits",
            discovery_resource_url="mcp://null/get_weather",
            mcp_result_meta=None,
            mcp_result_dunder_meta=None,
        )
        self.assertFalse(bad.allowed)
        self.assertIn("x402_mcp_payment_required_mismatch", bad.violations)
        self.assertIn("x402_route_template_traversal_or_scheme_injection", bad.violations)
        self.assertIn("x402_settlement_override_exceeds_ceiling", bad.violations)
        self.assertIn("x402_evm_malformed_channel_state_cumulative_amount", bad.violations)
        self.assertIn("x402_mcp_discovery_url_corrupted", bad.violations)
        self.assertIn("x402_mcp_settlement_metadata_missing", bad.violations)

    def test_ucp_and_acp_guards(self) -> None:
        ucp_ok = validate_ucp_option_selection_and_issuer_anchor_guard(
            selected_options=[
                {"name": "Color", "label": "Red"},
                {"name": "Color", "label": "Red"},
                {"name": "Size", "label": "M"},
            ],
            candidate_auth_url="https://idp.trusted.example",
            recognized_issuers={"https://idp.trusted.example"},
            subject_token_issuer="https://idp.trusted.example",
        )
        self.assertTrue(ucp_ok.allowed)
        self.assertEqual(len(ucp_ok.metadata["deduplicated_options"]), 2)

        ucp_bad = validate_ucp_option_selection_and_issuer_anchor_guard(
            selected_options=[
                {"name": "Color", "label": "Red"},
                {"name": "Color", "label": "Blue"},
            ],
            candidate_auth_url="https://idp.trusted.example/",
            recognized_issuers={"https://idp.trusted.example"},
            subject_token_issuer="https://idp.trusted.example",
        )
        self.assertFalse(ucp_bad.allowed)
        self.assertIn("ucp_duplicate_selected_option_conflict", ucp_bad.violations)
        self.assertIn("ucp_identity_linking_unrecognized_issuer_auth_url", ucp_bad.violations)

        acp_ok = validate_acp_session_context_and_flat_error_guard(
            endpoint="delegate_payment",
            payload={
                "risk_signals": [{"type": "card_testing", "score": 10, "action": "manual_review"}],
                "session_context": {"session_id": "sess_abc123", "ip_address": "203.0.113.45"},
            },
            error_response={"type": "unauthorized", "code": "unauthorized", "message": "Unauthorized"},
        )
        self.assertTrue(acp_ok.allowed)

        acp_bad = validate_acp_session_context_and_flat_error_guard(
            endpoint="complete_checkout",
            payload={"risk_signals": {"session_id": "sess_abc123"}},
            error_response={"error": {"type": "unauthorized", "code": "unauthorized", "message": "Unauthorized"}},
        )
        self.assertFalse(acp_bad.allowed)
        self.assertIn("acp_complete_checkout_deprecated_risk_signals_field", acp_bad.violations)
        self.assertIn("acp_error_response_wrapped_envelope_forbidden", acp_bad.violations)

    def test_ap2_mcp_stripe_and_tau2_guards(self) -> None:
        ap2_ok = validate_ap2_exec_date_token_binding_merchant_kb_guard(
            open_not_before=1000,
            open_not_after=2000,
            closed_execution_date=None,
            effective_execution_time=1500,
            token_bound_mandate_id="mandate_tx_1",
            verified_mandate_id="mandate_tx_1",
            open_merchant_id="merch_01",
            closed_merchant_id="merch_01",
            intermediate_kb_hops=[{"aud": "https://psp.example", "nonce": "n_123"}],
            expected_aud="https://psp.example",
            expected_nonce="n_123",
        )
        self.assertTrue(ap2_ok.allowed)

        ap2_bad = validate_ap2_exec_date_token_binding_merchant_kb_guard(
            open_not_before=1000,
            open_not_after=2000,
            closed_execution_date=None,
            effective_execution_time=2500,
            token_bound_mandate_id=None,
            verified_mandate_id="mandate_tx_1",
            open_merchant_id="",
            closed_merchant_id="",
            intermediate_kb_hops=[{"aud": "https://evil.example", "nonce": "n_999"}],
            expected_aud="https://psp.example",
            expected_nonce="n_123",
        )
        self.assertFalse(ap2_bad.allowed)
        self.assertIn("ap2_execution_date_outside_authorized_window", ap2_bad.violations)
        self.assertIn("ap2_credential_token_unbound_or_mandate_mismatch", ap2_bad.violations)
        self.assertIn("ap2_merchant_id_empty_display_fallback_forbidden", ap2_bad.violations)
        self.assertIn("ap2_intermediate_kb_hop_0_aud_or_nonce_mismatch", ap2_bad.violations)

        mst_ok = validate_mcp_signed_manifest_stripe_toolkit_and_tau2_live_db_guard(
            manifest_signed=True,
            manifest_server_uri="https://mcp.merchant.example",
            expected_server_uri="https://mcp.merchant.example",
            previous_content_hash="sha256:aaa",
            current_content_hash="sha256:aaa",
            reconsent_granted=False,
            trust_label_effect="financial_settlement",
            cimd_auth_methods_supported=["private_key_jwt"],
            stripe_toolkit_config={"context": {"account": "acct_123"}},
            anthropic_start_input_tokens=25,
            anthropic_delta_input_tokens=[None, 4120, 10682],
            stream_abandoned=False,
            tau2_telecom_line_status="active",
            tau2_live_db_hash="d10d0dcb",
            tau2_replay_db_hash="b25c9cb2",
            tau2_expected_db_hash="d10d0dcb",
        )
        self.assertTrue(mst_ok.allowed)
        self.assertEqual(mst_ok.metadata["cumulative_input_tokens"], 10682)
        self.assertTrue(mst_ok.metadata["replay_divergence"])

        mst_bad = validate_mcp_signed_manifest_stripe_toolkit_and_tau2_live_db_guard(
            manifest_signed=True,
            manifest_server_uri="https://mcp.merchant.example",
            expected_server_uri="https://mcp.merchant.example",
            previous_content_hash="sha256:aaa",
            current_content_hash="sha256:bbb",
            reconsent_granted=False,
            trust_label_effect="freeform_untrusted",
            cimd_auth_methods_supported=[],
            stripe_toolkit_config={"actions": {"payment_links": {"create": True}}},
            anthropic_start_input_tokens=25,
            anthropic_delta_input_tokens=[10682],
            stream_abandoned=True,
            tau2_telecom_line_status="suspended",
            tau2_live_db_hash="b25c9cb2",
            tau2_replay_db_hash="d10d0dcb",
            tau2_expected_db_hash="d10d0dcb",
        )
        self.assertFalse(mst_bad.allowed)
        self.assertIn("mcp_sep3140_rug_pull_unapproved_content_hash_change", mst_bad.violations)
        self.assertIn("mcp_sep3149_cimd_missing_auth_methods_supported", mst_bad.violations)
        self.assertIn("stripe_toolkit_deprecated_actions_policy_fail_open_blocked", mst_bad.violations)
        self.assertIn("tau2_telecom_refuel_requires_active_line", mst_bad.violations)
        self.assertIn("tau2_live_db_hash_mismatch", mst_bad.violations)


if __name__ == "__main__":
    unittest.main()
