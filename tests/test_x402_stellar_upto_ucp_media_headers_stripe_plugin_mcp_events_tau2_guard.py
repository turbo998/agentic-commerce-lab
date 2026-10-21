"""Unit tests for Stage 118 x402 Stellar upto/SVM batch, UCP media/headers,
Stripe AI plugin/MCP forwarding, and MCP SEP-3415 events + tau2 voice guards."""

from __future__ import annotations

import unittest

from lab.x402_stellar_upto_ucp_media_headers_stripe_plugin_mcp_events_tau2_guard import (
    PINNED_STELLAR_TESTNET_UPTO_CONTRACT,
    validate_mcp_events_and_tau2_voice,
    validate_stripe_plugin_and_mcp_forwarding,
    validate_ucp_media_extension_and_headers,
    validate_x402_stellar_upto_and_svm_batch,
)


class Stage118GuardTests(unittest.TestCase):
    def test_x402_stellar_upto_and_svm_batch_valid(self) -> None:
        res = validate_x402_stellar_upto_and_svm_batch(
            network="stellar:testnet",
            contract_address=PINNED_STELLAR_TESTNET_UPTO_CONTRACT,
            wasm_hash="cc2d2fef99aa00ca797",
            payer_account="CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC",
            signs_tx_envelope=False,
            has_authorize_entry_override=True,
            max_amount=10_000_000,
            settle_amount=5_000_000,
            current_ledger=1200,
            expiration_ledger=1500,
            terms_facilitator="GD5DJQDDBKGAYNEAXU562HYGOOSYAEOO6AS53PZXBOZGCP5M2OPGMZV3",
            caller_facilitator="GD5DJQDDBKGAYNEAXU562HYGOOSYAEOO6AS53PZXBOZGCP5M2OPGMZV3",
            fee_stroops=150_000,
            max_timeout_seconds=60,
            signer_authorizations_count=2,
            contract_state_archived=False,
            prior_settled_amount=None,
            may_have_broadcast=False,
            broadcast_tx_hash=None,
            registered_schemes={"stellar:*": {"upto": {"before_verify_hook_ran": True}}},
            requested_scheme="upto",
            svm_channel_write_succeeded=True,
            svm_callback_retried=False,
            complete_called_inside_channel_callback=False,
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.matched_scheme_key, "stellar:*")
        self.assertEqual(res.settled_amount, 5_000_000)

    def test_x402_stellar_contract_account_without_authorize_entry_blocked(self) -> None:
        res = validate_x402_stellar_upto_and_svm_batch(
            network="stellar:testnet",
            contract_address=PINNED_STELLAR_TESTNET_UPTO_CONTRACT,
            wasm_hash="cc2d2fef99aa00ca797",
            payer_account="CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC",
            signs_tx_envelope=False,
            has_authorize_entry_override=False,
            max_amount=10_000_000,
            settle_amount=5_000_000,
            current_ledger=1200,
            expiration_ledger=1500,
            terms_facilitator="GFACIL",
            caller_facilitator="GFACIL",
            fee_stroops=100_000,
            max_timeout_seconds=60,
            signer_authorizations_count=1,
            contract_state_archived=False,
            prior_settled_amount=None,
            may_have_broadcast=False,
            broadcast_tx_hash=None,
            registered_schemes={"stellar:*": {"upto": {"before_verify_hook_ran": True}}},
            requested_scheme="upto",
            svm_channel_write_succeeded=True,
            svm_callback_retried=False,
            complete_called_inside_channel_callback=False,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(
            res.reason_code,
            "X402_STELLAR_CONTRACT_ACCOUNT_MISSING_AUTHORIZE_ENTRY_OVERRIDE",
        )

    def test_x402_svm_premature_operation_complete_inside_callback_blocked(self) -> None:
        res = validate_x402_stellar_upto_and_svm_batch(
            network="stellar:testnet",
            contract_address=PINNED_STELLAR_TESTNET_UPTO_CONTRACT,
            wasm_hash="cc2d2fef99aa00ca797",
            payer_account="GD5DJQDDBKGAYNEAXU562HYGOOSYAEOO6AS53PZXBOZGCP5M2OPGMZV3",
            signs_tx_envelope=False,
            has_authorize_entry_override=False,
            max_amount=10_000_000,
            settle_amount=5_000_000,
            current_ledger=1200,
            expiration_ledger=1500,
            terms_facilitator="GFACIL",
            caller_facilitator="GFACIL",
            fee_stroops=100_000,
            max_timeout_seconds=60,
            signer_authorizations_count=1,
            contract_state_archived=False,
            prior_settled_amount=None,
            may_have_broadcast=False,
            broadcast_tx_hash=None,
            registered_schemes={"stellar:*": {"upto": {"before_verify_hook_ran": True}}},
            requested_scheme="upto",
            svm_channel_write_succeeded=True,
            svm_callback_retried=True,
            complete_called_inside_channel_callback=True,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(
            res.reason_code,
            "X402_SVM_PREMATURE_OPERATION_COMPLETE_INSIDE_CHANNEL_CALLBACK",
        )

    def test_ucp_media_extension_and_headers_valid(self) -> None:
        res = validate_ucp_media_extension_and_headers(
            media_items=[
                {
                    "type": "image",
                    "url": "https://cdn.example.com/p.jpg",
                    "sources": [
                        {
                            "url": "https://cdn.example.com/p.avif",
                            "mime_type": "image/avif",
                        }
                    ],
                },
                {
                    "type": "external_video",
                    "url": "https://videos.example.com/embed/1",
                    "sandbox_isolated": True,
                    "allow_top_navigation": False,
                },
            ],
            require_https_media=True,
            checkout_example={
                "fulfillment": {
                    "options": [{"id": "opt_1", "description": {"text": "2-day"}}],
                    "methods": [{"id": "m_1", "line_item_ids": ["li_1"]}],
                },
                "ap2": {"checkout_mandate": "eyJhbGciOiJFUzI1NiJ9.eyJleHAiOjF9.c2ln"},
            },
            is_update_operation=True,
            http_method="POST",
            parameter_headers=["Idempotency-Key"],
            security_alternatives=[{}, {"oauth2": ""}, {"apiKey_header": "X-API-Key"}],
            has_request_body_content=True,
            has_2xx_response_content=True,
        )
        self.assertTrue(res.allowed)
        headers_dict = dict(res.synthesized_headers)
        self.assertIn("Authorization", headers_dict)
        self.assertFalse(headers_dict["Authorization"])
        self.assertIn("X-API-Key", headers_dict)
        self.assertIn("Content-Type", headers_dict)
        self.assertIn("Accept", headers_dict)

    def test_ucp_external_video_unisolated_or_string_fulfillment_desc_blocked(self) -> None:
        res = validate_ucp_media_extension_and_headers(
            media_items=[
                {
                    "type": "external_video",
                    "url": "https://videos.example.com/embed/1",
                    "sandbox_isolated": False,
                    "allow_top_navigation": True,
                }
            ],
            require_https_media=True,
            checkout_example={},
            is_update_operation=False,
            http_method="GET",
            parameter_headers=[],
            security_alternatives=[],
            has_request_body_content=False,
            has_2xx_response_content=True,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.reason_code, "UCP_EXTERNAL_VIDEO_IFRAME_NOT_ISOLATED")

        res2 = validate_ucp_media_extension_and_headers(
            media_items=[{"type": "image", "url": "https://cdn.example.com/p.jpg"}],
            require_https_media=True,
            checkout_example={
                "fulfillment": {"options": [{"id": "opt_1", "description": "string"}]}
            },
            is_update_operation=False,
            http_method="POST",
            parameter_headers=[],
            security_alternatives=[],
            has_request_body_content=True,
            has_2xx_response_content=True,
        )
        self.assertFalse(res2.allowed)
        self.assertEqual(
            res2.reason_code, "UCP_FULFILLMENT_OPTION_DESCRIPTION_MUST_BE_OBJECT"
        )

    def test_stripe_plugin_and_mcp_forwarding_valid_and_blocks_list_tools(self) -> None:
        res = validate_stripe_plugin_and_mcp_forwarding(
            skill_allowed_tools="Bash(stripe *), Bash(which stripe)",
            operation="payment_intents.create",
            amount_minor=2500,
            currency="usd",
            target_id="cus_123",
            current_turn_confirmation={
                "is_current_turn": True,
                "operation": "payment_intents.create",
                "amount_minor": 2500,
                "currency": "usd",
                "target_id": "cus_123",
            },
            requires_tos_acceptance=True,
            user_accepted_tos=True,
            passed_accept_tos_flag=True,
            auto_submitted_feedback=False,
            user_approved_feedback=False,
            stripe_cli_version="1.51.0",
            skills_cli_version="1.7.0",
            mcp_forwarding_failed=True,
            mcp_failure_message='HTTP 401: {"error":"invalid_api_key"}',
            mcp_incoming_jsonrpc={"jsonrpc": "2.0", "id": 7, "method": "tools/list"},
        )
        self.assertTrue(res.allowed)
        self.assertIsNotNone(res.forwarding_error_response)
        assert res.forwarding_error_response is not None
        self.assertEqual(res.forwarding_error_response["id"], 7)
        self.assertEqual(res.forwarding_error_response["error"]["code"], -32603)

        bad = validate_stripe_plugin_and_mcp_forwarding(
            skill_allowed_tools=["Bash(stripe *)"],
            operation="charges.create",
            amount_minor=2500,
            currency="usd",
            target_id="cus_123",
            current_turn_confirmation=None,
            requires_tos_acceptance=False,
            user_accepted_tos=False,
            passed_accept_tos_flag=False,
            auto_submitted_feedback=False,
            user_approved_feedback=False,
            stripe_cli_version="1.51.0",
            skills_cli_version="1.7.0",
            mcp_forwarding_failed=False,
            mcp_failure_message="",
            mcp_incoming_jsonrpc=None,
        )
        self.assertFalse(bad.allowed)
        self.assertEqual(
            bad.reason_code, "STRIPE_PLUGIN_ALLOWED_TOOLS_MUST_BE_STRING"
        )

    def test_mcp_events_and_tau2_voice_valid_and_blocks_localhost(self) -> None:
        res = validate_mcp_events_and_tau2_voice(
            cimd_redirect_uris=[
                "http://127.0.0.1:3000/callback",
                "http://[::1]:3000/callback",
            ],
            event_delivery_mode="webhook",
            supported_delivery_modes={"poll", "webhook"},
            webhook_signature_verified=True,
            webhook_ttl_seconds=3600,
            cursor_truncated=True,
            client_acknowledged_truncation=True,
            ava_zero_domain_policy_modified=False,
            ava_zero_has_bearer_token=True,
            ava_zero_has_rtvi_channel=True,
            db_check_passed=True,
            communication_check_passed=False,
            diagnostic_check_failed=True,
            diagnostic_counted_in_reward=False,
            core_import_loaded_voice_deps_eagerly=False,
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.effective_reward, 0.0)
        self.assertTrue(res.core_import_isolated)

        bad = validate_mcp_events_and_tau2_voice(
            cimd_redirect_uris=["http://localhost:3000/callback"],
            event_delivery_mode="poll",
            supported_delivery_modes={"poll"},
            webhook_signature_verified=True,
            webhook_ttl_seconds=3600,
            cursor_truncated=False,
            client_acknowledged_truncation=False,
            ava_zero_domain_policy_modified=False,
            ava_zero_has_bearer_token=True,
            ava_zero_has_rtvi_channel=True,
            db_check_passed=True,
            communication_check_passed=True,
            diagnostic_check_failed=False,
            diagnostic_counted_in_reward=False,
            core_import_loaded_voice_deps_eagerly=False,
        )
        self.assertFalse(bad.allowed)
        self.assertEqual(
            bad.reason_code,
            "MCP_CIMD_LOCALHOST_REDIRECT_URI_FORBIDDEN_USE_LOOPBACK_IP",
        )


if __name__ == "__main__":
    unittest.main()
