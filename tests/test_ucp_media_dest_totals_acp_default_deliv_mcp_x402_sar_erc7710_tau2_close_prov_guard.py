"""Unit tests for Stage 82 deterministic guard module."""

from __future__ import annotations

import unittest

from lab.ucp_media_dest_totals_acp_default_deliv_mcp_x402_sar_erc7710_tau2_close_prov_guard import (
    verify_acp_default_delivery_delegate_errors_citation_and_mcp_binding_guard,
    verify_tau2_banking_close_reason_persona_empty_retry_provenance_and_tts_guard,
    verify_ucp_media_destinations_totals_idempotency_order_gift_and_ask_guard,
    verify_x402_mcp_policy_request_binding_attestseal_sar_erc7710_and_hook_guard,
)


class TestStage82Guard(unittest.TestCase):
    def test_ucp_media_destinations_totals_idempotency_order_gift_and_ask_valid(self) -> None:
        payload = {
            "media_items": [
                {
                    "type": "video",
                    "url": "https://cdn.example.com/product.mp4",
                    "sources": [{"url": "https://cdn.example.com/product.m3u8", "mime": "application/x-mpegURL"}],
                },
                {
                    "type": "model_3d",
                    "url": "https://cdn.example.com/chair.glb",
                    "sources": [{"url": "https://cdn.example.com/chair.usdz"}],
                },
            ],
            "destination_contract": {
                "request_requires_per_object_type": False,
                "response_destination_has_explicit_type": True,
            },
            "totals_schema_root_type": "object",
            "mcp_idempotency": {
                "key_reused_with_different_payload": True,
                "returned_status_code": -32000,
            },
            "a2a_checkout": {
                "status": "complete_in_progress",
                "accepted_mutation_action": False,
            },
            "location_context": {
                "context_location_selected_delivery_destination": False,
            },
            "order_payment_instruments": [
                {"id": "pi_1", "type": "card", "brand": "visa", "last_digits": "4242"}
            ],
            "discounts": {
                "zero_price_promotional_line_item_ids": ["li_free_tote"],
                "applied": [{"code": "BOGOTOTE", "gift_line_item_id": "li_free_tote"}],
                "rejection_codes": ["discount_code_usage_limit_reached", "discount_code_stacking_conflict"],
                "usage_limit_exhausted_reported_as_already_applied": False,
            },
            "profile": {
                "keys": [{"kty": "OKP", "crv": "Ed25519", "kid": "k1", "x": "abc"}]
            },
            "ask_operation": {
                "mutated_checkout_or_cart_state": False,
            },
            "gift": {
                "recipient_required": True,
                "business_validated_recipient_present": True,
            },
            "checkout_completing": True,
        }
        res = verify_ucp_media_destinations_totals_idempotency_order_gift_and_ask_guard(payload)
        self.assertTrue(res["allowed"])
        self.assertEqual(res["violations"], [])

    def test_ucp_media_destinations_totals_idempotency_order_gift_and_ask_violations(self) -> None:
        payload = {
            "media_items": [{"type": "hologram", "sources": []}],
            "destination_contract": {
                "request_requires_per_object_type": True,
                "response_destination_has_explicit_type": False,
            },
            "totals_schema_root_type": "array",
            "mcp_idempotency": {
                "key_reused_with_different_payload": True,
                "returned_status_code": 200,
            },
            "a2a_checkout": {
                "status": "complete_in_progress",
                "accepted_mutation_action": True,
            },
            "location_context": {
                "context_location_selected_delivery_destination": True,
            },
            "order_payment_instruments": [
                {"id": "pi_1", "handler_id": "h_stripe", "credential": "tok_secret", "selected": True}
            ],
            "discounts": {
                "zero_price_promotional_line_item_ids": ["li_free_tote"],
                "applied": [{"code": "BOGOTOTE"}],
                "rejection_codes": ["unknown_code"],
                "usage_limit_exhausted_reported_as_already_applied": True,
            },
            "profile": {
                "signing_keys": [{"kid": "old"}],
                "keys": [],
            },
            "ask_operation": {
                "mutated_checkout_or_cart_state": True,
            },
            "gift": {
                "recipient_required": True,
                "business_validated_recipient_present": False,
                "recipient_address": "123 Secret St",
            },
            "checkout_completing": True,
        }
        res = verify_ucp_media_destinations_totals_idempotency_order_gift_and_ask_guard(payload)
        self.assertFalse(res["allowed"])
        for expected in (
            "UCP_MEDIA_VARIANT_TYPE_INVALID:0:hologram",
            "UCP_MEDIA_SOURCES_MUST_BE_NON_EMPTY_ARRAY:0",
            "UCP_REQUEST_DESTINATION_PER_OBJECT_TYPE_BREAKS_DEPLOYED_PLATFORMS",
            "UCP_RESPONSE_DESTINATION_EXPLICIT_TYPE_REQUIRED",
            "UCP_TOTALS_SCHEMA_ROOT_ARRAY_FORBIDDEN",
            "UCP_MCP_IDEMPOTENCY_KEY_CONFLICT_MUST_RETURN_409_OR_MINUS_32000",
            "UCP_A2A_COMPLETE_IN_PROGRESS_MUTATION_FREEZE_VIOLATED",
            "UCP_CONTEXT_LOCATION_MUST_NOT_SELECT_DELIVERY_DESTINATION",
            "UCP_ORDER_PAYMENT_INSTRUMENT_LEAKED_COLLECTION_FIELDS:0:credential,handler_id,selected",
            "UCP_UNLINKED_ZERO_PRICE_GIFT_LINE_ITEM:li_free_tote",
            "UCP_DISCOUNT_REJECTION_CODE_INVALID:unknown_code",
            "UCP_DISCOUNT_USAGE_LIMIT_MISREPORTED_AS_ALREADY_APPLIED",
            "UCP_PROFILE_LEGACY_SIGNING_KEYS_FORBIDDEN_USE_KEYS_JWKS",
            "UCP_PROFILE_CANONICAL_KEYS_ARRAY_EMPTY",
            "UCP_ASK_CAPABILITY_MUST_BE_STRICTLY_READ_ONLY",
            "UCP_GIFT_EXTENSION_FORBIDDEN_RECIPIENT_PII:recipient_address",
            "UCP_GIFT_RECIPIENT_REQUIRED_BEFORE_COMPLETE",
        ):
            self.assertIn(expected, res["violations"])

    def test_acp_default_delivery_delegate_errors_citation_and_mcp_binding_valid(self) -> None:
        payload = {
            "checkout_create_response": {
                "fulfillment_options": [{"id": "ship_std"}, {"id": "ship_exp"}],
                "selected_fulfillment_option_id": "ship_std",
            },
            "delegate_payment": {
                "payment_method_card": {"virtual": True},
                "error": {"type": "unauthorized", "code": "unsupported_api_version"},
            },
            "content_attribution": [
                {"source_url": "https://review.example/item", "publisher_id": "pub_01", "overrides_item_price": False}
            ],
            "mcp_transport_call": {
                "jsonrpc": "2.0",
                "tool_name": "complete_checkout_session",
            },
            "payment_handler": {
                "display_name": "Stripe Link Wallet",
                "payment_intent": "capture",
            },
            "uses_deprecated_discount_detail_type": False,
        }
        res = verify_acp_default_delivery_delegate_errors_citation_and_mcp_binding_guard(payload)
        self.assertTrue(res["allowed"])
        self.assertEqual(res["violations"], [])

    def test_acp_default_delivery_delegate_errors_citation_and_mcp_binding_violations(self) -> None:
        payload = {
            "checkout_create_response": {
                "fulfillment_options": [{"id": "ship_std"}],
                "selected_fulfillment_option_id": None,
            },
            "delegate_payment": {
                "payment_method_card": {"virtual": "yes"},
                "error": {"type": "bad_type", "code": "bad_code"},
            },
            "content_attribution": [
                {"source_url": "", "publisher_id": "", "overrides_item_price": True}
            ],
            "mcp_transport_call": {
                "jsonrpc": "1.0",
                "tool_name": "unknown_tool",
            },
            "payment_handler": {
                "display_name": "   ",
                "payment_intent": "instant_wire",
            },
            "uses_deprecated_discount_detail_type": True,
        }
        res = verify_acp_default_delivery_delegate_errors_citation_and_mcp_binding_guard(payload)
        self.assertFalse(res["allowed"])
        for expected in (
            "ACP_CHECKOUT_CREATE_DEFAULT_FULFILLMENT_OPTION_MISSING",
            "ACP_DELEGATE_PAYMENT_CARD_VIRTUAL_BOOLEAN_REQUIRED",
            "ACP_DELEGATE_PAYMENT_ERROR_TYPE_INVALID:bad_type",
            "ACP_DELEGATE_PAYMENT_ERROR_CODE_INVALID:bad_code",
            "ACP_CONTENT_CITATION_SOURCE_OR_PUBLISHER_MISSING:0",
            "ACP_CONTENT_CITATION_PRICE_OVERRIDE_FORBIDDEN:0",
            "ACP_MCP_TRANSPORT_TOOL_BINDING_INVALID",
            "ACP_PAYMENT_HANDLER_DISPLAY_NAME_MISSING",
            "ACP_PAYMENT_INTENT_ENUM_INVALID",
            "ACP_DEPRECATED_DISCOUNT_DETAIL_MUST_CONSOLIDATE_TO_APPLIED_DISCOUNT",
        ):
            self.assertIn(expected, res["violations"])

    def test_x402_mcp_policy_request_binding_attestseal_sar_erc7710_and_hook_valid(self) -> None:
        payload = {
            "mcp_payment_policy": {
                "enforced_only_in_prompt": False,
                "verified_tool_network_and_max_amount_in_code": True,
            },
            "payment_identifier_record": {
                "bound_to_request_fingerprint": True,
                "reused_with_different_request_fingerprint": True,
                "returned_status": 409,
            },
            "attestseal_attestation": {
                "ed25519_signature_valid": True,
                "independent_authority_did_verified": True,
                "did_cache_age_hours": 12.0,
            },
            "settlement_attestation_receipt": {
                "tx_hash": "0xabc123",
                "request_digest": "sha256:req1",
                "delivered_resource_digest": "sha256:body1",
                "actual_response_body_digest": "sha256:body1",
                "server_signature_verified": True,
            },
            "erc7710_facilitator": {
                "simulated_redeem_delegations_eth_call": True,
            },
            "facilitator_runtime": {
                "optional_hook_threw": True,
                "aborted_verify_or_settle": False,
                "svm_fee_payer_uses_csprng": True,
                "svm_signer_pool_empty_unhandled": False,
            },
        }
        res = verify_x402_mcp_policy_request_binding_attestseal_sar_erc7710_and_hook_guard(payload)
        self.assertTrue(res["allowed"])
        self.assertEqual(res["violations"], [])

    def test_x402_mcp_policy_request_binding_attestseal_sar_erc7710_and_hook_violations(self) -> None:
        payload = {
            "mcp_payment_policy": {
                "enforced_only_in_prompt": True,
                "verified_tool_network_and_max_amount_in_code": False,
            },
            "payment_identifier_record": {
                "bound_to_request_fingerprint": False,
                "reused_with_different_request_fingerprint": True,
                "returned_status": 200,
            },
            "attestseal_attestation": {
                "ed25519_signature_valid": False,
                "independent_authority_did_verified": True,
                "did_cache_age_hours": 36.0,
            },
            "settlement_attestation_receipt": {
                "tx_hash": "0xabc123",
                "request_digest": "sha256:req1",
                "delivered_resource_digest": "sha256:body1",
                "actual_response_body_digest": "sha256:tampered",
                "server_signature_verified": True,
            },
            "erc7710_facilitator": {
                "simulated_redeem_delegations_eth_call": False,
            },
            "facilitator_runtime": {
                "optional_hook_threw": True,
                "aborted_verify_or_settle": True,
                "svm_fee_payer_uses_csprng": False,
                "svm_signer_pool_empty_unhandled": True,
            },
        }
        res = verify_x402_mcp_policy_request_binding_attestseal_sar_erc7710_and_hook_guard(payload)
        self.assertFalse(res["allowed"])
        for expected in (
            "X402_MCP_SPEND_POLICY_MUST_ENFORCE_IN_CODE_BEFORE_SIGNING",
            "X402_PAYMENT_IDENTIFIER_UNBOUND_TO_REQUEST_FINGERPRINT",
            "X402_PAYMENT_IDENTIFIER_FINGERPRINT_MISMATCH_MUST_REJECT_409",
            "X402_ATTESTSEAL_TRUST_ATTESTATION_INVALID_OR_STALE",
            "X402_SAR_SETTLEMENT_TO_DELIVERY_DIGEST_BINDING_INVALID",
            "X402_ERC7710_REDEEM_DELEGATIONS_SIMULATION_MISSING",
            "X402_FACILITATOR_OPTIONAL_HOOK_FAILURE_NOT_ISOLATED",
            "X402_SVM_FEE_PAYER_WEAK_RNG_OR_EMPTY_POOL",
        ):
            self.assertIn(expected, res["violations"])

    def test_tau2_banking_close_reason_persona_empty_retry_provenance_and_tts_valid(self) -> None:
        payload = {
            "banking_knowledge": {
                "close_account_reason": "switching_bank",
                "task_091_has_persoca_typo": False,
            },
            "text_user_simulator": {
                "empty_completion_after_user_tool": True,
                "crashed_episode_as_infrastructure_error": False,
            },
            "evaluator_provenance": {
                "evaluation_mode": "live",
                "state_source": "caller_environment",
            },
            "telecom_multi_customer": {
                "reward_bases": ["ACTION", "DB"],
                "unrelated_db_writes_received_full_reward": False,
            },
            "voice_tts_provider": {
                "max_concurrent_syntheses": 4,
                "subscription_concurrency_cap": 5,
                "unbounded_parallel_synthesize_voice": False,
            },
        }
        res = verify_tau2_banking_close_reason_persona_empty_retry_provenance_and_tts_guard(payload)
        self.assertTrue(res["allowed"])
        self.assertEqual(res["violations"], [])

    def test_tau2_banking_close_reason_persona_empty_retry_provenance_and_tts_violations(self) -> None:
        payload = {
            "banking_knowledge": {
                "close_account_reason": "Found a better rate at Competitor X",
                "task_091_has_persoca_typo": True,
            },
            "text_user_simulator": {
                "empty_completion_after_user_tool": True,
                "crashed_episode_as_infrastructure_error": True,
            },
            "evaluator_provenance": {
                "evaluation_mode": "unknown",
                "state_source": "",
            },
            "telecom_multi_customer": {
                "reward_bases": ["ACTION"],
                "unrelated_db_writes_received_full_reward": True,
            },
            "voice_tts_provider": {
                "max_concurrent_syntheses": 10,
                "subscription_concurrency_cap": 5,
                "unbounded_parallel_synthesize_voice": True,
            },
        }
        res = verify_tau2_banking_close_reason_persona_empty_retry_provenance_and_tts_guard(payload)
        self.assertFalse(res["allowed"])
        for expected in (
            "TAU2_BANKING_CLOSE_ACCOUNT_REASON_NOT_IN_ENUM:Found a better rate at Competitor X",
            "TAU2_BANKING_TASK_091_PERSOCA_KEY_TYPO",
            "TAU2_EMPTY_USER_SIM_COMPLETION_MUST_RETRY_NOT_CRASH",
            "TAU2_EVALUATOR_PROVENANCE_METADATA_MISSING",
            "TAU2_TELECOM_MULTI_CUSTOMER_DB_GRADING_BYPASSED",
            "TAU2_VOICE_TTS_CONCURRENCY_UNBOUNDED_429_RISK",
        ):
            self.assertIn(expected, res["violations"])


if __name__ == "__main__":
    unittest.main()
