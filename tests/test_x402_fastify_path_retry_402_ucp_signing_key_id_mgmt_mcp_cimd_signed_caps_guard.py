"""Unit tests for Stage 136 deterministic runtime guardrails."""

from __future__ import annotations

import unittest

from lab.x402_fastify_path_retry_402_ucp_signing_key_id_mgmt_mcp_cimd_signed_caps_guard import (
    evaluate_mcp_cimd_signed_caps_tau2_guard,
    evaluate_ucp_signing_key_id_mgmt_acp_ap2_guard,
    evaluate_x402_fastify_retry_ecdsa_bazaar_guard,
)


class Stage136GuardTest(unittest.TestCase):
    """Validate Stage 136 x402, UCP/ACP/AP2, and MCP/tau2 deterministic guardrails."""

    def test_x402_fastify_retry_ecdsa_bazaar_guard(self) -> None:
        ok = evaluate_x402_fastify_retry_ecdsa_bazaar_guard(
            raw_request_url="/protected-route?tier=pro",
            has_payment_signature=True,
            initial_402_amount_minor=100,
            hook_retried=True,
            retry_402_amount_minor=200,
            paid_amount_minor=200,
            ecdsa_y_parity=1,
            create_headers_output={"verify": {"Authorization": "Bearer jwt_v"}, "settle": {"Authorization": "Bearer jwt_s"}},
            header_bazaar_extensions={"schemaVersion": "2.0"},
            body_bazaar_extensions={"bazaar": {"discoverable": True}, "schemaVersion": "1.0"},
            route_has_explicit_verb=False,
            probe_method="GET",
            bazaar_body_type="json",
        )
        self.assertTrue(ok.admitted)
        self.assertEqual(ok.normalized_request_path, "/protected-route")
        self.assertEqual(ok.effective_402_amount_minor, 200)
        self.assertEqual(ok.normalized_ecdsa_v, 28)
        self.assertEqual(ok.effective_bazaar_method, "POST")
        self.assertEqual(ok.merged_bazaar_extensions["schemaVersion"], "2.0")
        self.assertIn("bazaar", ok.merged_bazaar_extensions)

        bad = evaluate_x402_fastify_retry_ecdsa_bazaar_guard(
            raw_request_url="https://attacker.com/protected-route?bypass=1",
            has_payment_signature=False,
            initial_402_amount_minor=100,
            hook_retried=True,
            retry_402_amount_minor=200,
            paid_amount_minor=100,
            ecdsa_v=5,
            create_headers_output={"Authorization": "Bearer flat_dict"},
            paid_http_status=500,
            has_payment_response_header=True,
            on_payment_response_called_before_reject=False,
            mcp_accepted_timeout_sec=3600,
            mcp_max_request_timeout_sec=90,
            mcp_recovery_retry_timeout_sec=3600,
            cardano_channel_reserve_lovelace=500_000,
            lnbtc_transfer_method="invoice",
            lnbtc_facilitator_verified_receiver=False,
        )
        self.assertFalse(bad.admitted)
        self.assertEqual(bad.normalized_request_path, "/protected-route")
        self.assertIn("FASTIFY_PROTECTED_ROUTE_PAYMENT_REQUIRED_BYPASS_BLOCKED", bad.reason_codes)
        self.assertIn("X402_STALE_402_REQUIREMENTS_AFTER_HOOK_RETRY_REJECTED", bad.reason_codes)
        self.assertIn("X402_EVM_INVALID_ECDSA_RECOVERY_BYTE_REJECTED", bad.reason_codes)
        self.assertIn("X402_PYTHON_FLAT_CREATE_HEADERS_DICT_REJECTED", bad.reason_codes)
        self.assertIn("X402_AXIOS_PAID_ERROR_MISSING_ON_PAYMENT_RESPONSE_HOOK", bad.reason_codes)
        self.assertIn("X402_GO_MCP_RECOVERY_RETRY_TIMEOUT_UNCAPPED", bad.reason_codes)
        self.assertIn("X402_CARDANO_BATCH_CHANNEL_BELOW_MIN_UTXO_RESERVE", bad.reason_codes)
        self.assertIn("X402_LNBTC_INVOICE_RECEIVER_QUERY_UNVERIFIED", bad.reason_codes)

    def test_ucp_signing_key_id_mgmt_acp_ap2_guard(self) -> None:
        ok = evaluate_ucp_signing_key_id_mgmt_acp_ap2_guard(
            signing_key_jwk={"kty": "EC", "crv": "P-256", "x": "pub_x", "y": "pub_y", "kid": "ucp-key-1"},
            declared_identity_capability="dev.ucp.common.identity_management",
            identity_operation="create_identity",
            user_payment_methods=("CARD", "cashu-token"),
            merchant_accepted_payment_methods=("CARD", "BANK_ACCOUNT", "cashu-token"),
            cashu_mint_url="https://mint.example.com",
            cashu_nut24_proof_verified=True,
        )
        self.assertTrue(ok.admitted)
        self.assertEqual(ok.matched_payment_methods, ("CARD", "cashu-token"))

        bad = evaluate_ucp_signing_key_id_mgmt_acp_ap2_guard(
            signing_key_jwk={"kty": "EC", "crv": "P-256", "x": "pub_x", "y": "pub_y", "d": "secret_scalar"},
            declared_identity_capability="dev.ucp.common.identity_linking",
            has_deprecated_transition_fields=True,
            acp_address_company="94107",
            acp_address_postal_code="94107",
            acp_delegate_payment_phone_number="415-555-0199",
            credential_term="Verifiable Credential",
        )
        self.assertFalse(bad.admitted)
        self.assertIn("UCP_SIGNING_KEY_PRIVATE_JWK_FIELD_LEAK_BLOCKED", bad.reason_codes)
        self.assertIn("UCP_LEGACY_IDENTITY_LINKING_CAPABILITY_DEPRECATED", bad.reason_codes)
        self.assertIn("UCP_DEPRECATED_TRANSITION_SCHEMA_FIELD_REJECTED", bad.reason_codes)
        self.assertIn("ACP_ADDRESS_COMPANY_POSTAL_CODE_COPY_PASTE_CONFUSION", bad.reason_codes)
        self.assertIn("ACP_DELEGATE_PAYMENT_PHONE_NUMBER_E164_REQUIRED", bad.reason_codes)
        self.assertIn("AP2_LEGACY_VERIFIABLE_CREDENTIAL_TERM_REJECTED", bad.reason_codes)

    def test_mcp_cimd_signed_caps_tau2_guard(self) -> None:
        ok = evaluate_mcp_cimd_signed_caps_tau2_guard()
        self.assertTrue(ok.admitted)
        self.assertFalse(ok.rug_pull_detected)
        self.assertEqual(ok.elicitation_route, "app_rendered:ui://checkout/confirm-form")

        bad = evaluate_mcp_cimd_signed_caps_tau2_guard(
            cimd_token_endpoint_auth_methods_supported=("none",),
            cimd_singular_token_endpoint_auth_method="none",
            capability_manifest_jws_valid=False,
            previous_trust_labels={"effect": "read", "egress": "none", "dataSensitivity": "public", "reversibility": "reversible"},
            current_trust_labels={"effect": "irreversible", "egress": "external", "dataSensitivity": "regulated_pci_pii", "reversibility": "irreversible"},
            list_changed_re_gated_by_client=False,
            has_core_form_fallback=False,
            subscriptions_listen_has_result_response_envelope=False,
            number_schema_allows_float=False,
            tau2_model_is_thinking=True,
            tau2_reasoning_content_preserved=False,
            tau2_airline_task35_anchored_single_passenger=False,
            tau2_retail_known_info_text="You are mei_kovacs_8020 in zip code 28236.",
            tau2_task053_has_user_tool_call=False,
            tau2_openai_realtime_uses_beta_header=True,
        )
        self.assertFalse(bad.admitted)
        self.assertTrue(bad.rug_pull_detected)
        self.assertIn("MCP_SEP3149_DEPRECATED_SINGULAR_TOKEN_AUTH_METHOD_REJECTED", bad.reason_codes)
        self.assertIn("MCP_SEP3149_IMPLICIT_PUBLIC_CLIENT_NONE_AUTH_REJECTED", bad.reason_codes)
        self.assertIn("MCP_SEP3140_UNSIGNED_OR_INVALID_CAPABILITY_MANIFEST_JWS", bad.reason_codes)
        self.assertIn("MCP_SEP3140_LIST_CHANGED_RUG_PULL_ESCALATION_UNREGATED", bad.reason_codes)
        self.assertIn("MCP_SEP3118_MISSING_CORE_FORM_ELICITATION_FALLBACK", bad.reason_codes)
        self.assertIn("MCP_SUBSCRIPTIONS_LISTEN_MISSING_RESULT_RESPONSE_ENVELOPE", bad.reason_codes)
        self.assertIn("MCP_NUMBER_SCHEMA_FLOAT_DEFAULT_COERCED_TO_INTEGER", bad.reason_codes)
        self.assertIn("TAU2_THINKING_MODEL_REASONING_CONTENT_DROPPED", bad.reason_codes)
        self.assertIn("TAU2_AIRLINE_TASK35_UNANCHORED_PASSENGER_COUNT_DRIFT", bad.reason_codes)
        self.assertIn("TAU2_RETAIL_INTERNAL_USER_ID_LEAKED_IN_KNOWN_INFO", bad.reason_codes)
        self.assertIn("TAU2_BANKING_TASK053_MISSING_USER_TOOL_CALL", bad.reason_codes)
        self.assertIn("TAU2_OPENAI_REALTIME_LEGACY_BETA_HEADER_REJECTED", bad.reason_codes)


if __name__ == "__main__":
    unittest.main()
