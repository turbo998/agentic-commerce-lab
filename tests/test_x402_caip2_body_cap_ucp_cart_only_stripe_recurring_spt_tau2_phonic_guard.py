"""Unit tests for Stage 168 deterministic protocol & benchmark guardrails (2026-10-22)."""

from __future__ import annotations

import unittest

from lab.x402_caip2_body_cap_ucp_cart_only_stripe_recurring_spt_tau2_phonic_guard import (
    validate_stripe_recurring_spt_ucp_handler_and_toolkit_guard,
    validate_tau2_exchange_mms_windows_hash_and_phonic_guard,
    validate_ucp_cart_only_checkout_and_return_identity_guard,
    validate_x402_caip2_body_cap_and_settlement_guard,
)


class TestStage168Guardrails(unittest.TestCase):
    def test_x402_caip2_body_cap_and_settlement_guard(self) -> None:
        valid = {
            "network": "eip155:84532",
            "payment_signature_version": 2,
            "response_body_check": {"plane": "control", "body_bytes": 4096},
            "extensions_mutated_in_place": False,
            "bazaar_probe": {"has_body_type": True, "advertised_method": "POST"},
            "cardano_tx": {"reencoded_cbor_before_submit": False},
            "stellar_settle": {
                "rpc_status": "TRY_AGAIN_LATER",
                "error_reason": "settle_exact_stellar_transaction_submission_retryable",
            },
            "evm_verify": {
                "payer_code_lookup_failed": True,
                "scheme": "upto",
                "reported_error": "invalid_upto_evm_failed_to_verify_signature",
            },
            "client_hygiene": {
                "mcp_major_version": 1,
                "retry_sent_access_control_expose_headers": False,
                "axios_cookie_array_dropped_or_comma_joined": False,
            },
        }
        res = validate_x402_caip2_body_cap_and_settlement_guard(valid)
        self.assertTrue(res.allowed)
        self.assertEqual(
            res.decision_code, "X402_CAIP2_BODY_CAP_AND_SETTLEMENT_VERIFIED"
        )

        bad_caip2 = validate_x402_caip2_body_cap_and_settlement_guard(
            {**valid, "network": "EIP155:base.mainnet"}
        )
        self.assertFalse(bad_caip2.allowed)
        self.assertEqual(
            bad_caip2.decision_code, "X402_CAIP2_NETWORK_SYNTAX_INVALID"
        )

        bad_body = validate_x402_caip2_body_cap_and_settlement_guard(
            {
                **valid,
                "response_body_check": {
                    "plane": "control",
                    "body_bytes": 2 * 1024 * 1024,
                },
            }
        )
        self.assertFalse(bad_body.allowed)
        self.assertEqual(bad_body.decision_code, "X402_RESPONSE_BODY_TOO_LARGE")

        bad_cardano = validate_x402_caip2_body_cap_and_settlement_guard(
            {**valid, "cardano_tx": {"reencoded_cbor_before_submit": True}}
        )
        self.assertFalse(bad_cardano.allowed)
        self.assertEqual(
            bad_cardano.decision_code,
            "X402_CARDANO_CBOR_REENCODE_MUTATION_FORBIDDEN",
        )

    def test_ucp_cart_only_checkout_and_return_identity_guard(self) -> None:
        valid = {
            "checkout_create": {
                "cart_id": "cart_abc123",
                "line_items": None,
                "cart_capability_negotiated": True,
                "authoritative_source": "cart",
            },
            "return_policy": {
                "eligibility_type": "window",
                "platform_did_date_math": False,
                "charged_fee_minor": 500,
                "stated_max_fee_minor": 500,
            },
            "identity_linking": {
                "client_auth_method": "private_key_jwt",
                "token_endpoint_auth_methods_supported": [
                    "private_key_jwt",
                    "client_secret_basic",
                ],
                "single_invalid_as_entry_aborted_discovery": False,
                "remaining_valid_as_entries": 2,
            },
        }
        res = validate_ucp_cart_only_checkout_and_return_identity_guard(valid)
        self.assertTrue(res.allowed)
        self.assertEqual(
            res.decision_code, "UCP_CART_ONLY_RETURN_AND_IDENTITY_VERIFIED"
        )

        unnegotiated = validate_ucp_cart_only_checkout_and_return_identity_guard(
            {
                **valid,
                "checkout_create": {
                    "cart_id": "cart_abc123",
                    "line_items": [{"id": "item_1", "quantity": 1}],
                    "cart_capability_negotiated": False,
                    "business_rejected_unnegotiated_cart_id": False,
                },
            }
        )
        self.assertFalse(unnegotiated.allowed)
        self.assertEqual(
            unnegotiated.decision_code,
            "UCP_UNNEGOTIATED_CART_ID_SILENT_FALLBACK_FORBIDDEN",
        )

    def test_stripe_recurring_spt_ucp_handler_and_toolkit_guard(self) -> None:
        valid = {
            "spt_payment_intent": {
                "uses_shared_payment_granted_token": True,
                "is_recurring_charge": True,
                "spt_recurring_interval": "month",
                "setup_future_usage": None,
                "card_setup_future_usage": None,
                "off_session": True,
                "spt_off_session_permitted": True,
            },
            "stripe_ucp_handler": {
                "handler_id": "stripe_payments",
                "instrument_type": "card",
                "identity_access_token": "profile_seller_xyz",
                "seller_business_profile": "profile_seller_xyz",
            },
            "stripe_toolkit_sync_run": {
                "uses_deprecated_get_event_loop": False,
            },
        }
        res = validate_stripe_recurring_spt_ucp_handler_and_toolkit_guard(valid)
        self.assertTrue(res.allowed)
        self.assertEqual(
            res.decision_code, "STRIPE_RECURRING_SPT_UCP_AND_TOOLKIT_VERIFIED"
        )

        sfu = validate_stripe_recurring_spt_ucp_handler_and_toolkit_guard(
            {
                **valid,
                "spt_payment_intent": {
                    **valid["spt_payment_intent"],
                    "setup_future_usage": "off_session",
                },
            }
        )
        self.assertFalse(sfu.allowed)
        self.assertEqual(
            sfu.decision_code, "STRIPE_SPT_SETUP_FUTURE_USAGE_REJECTED"
        )

    def test_tau2_exchange_mms_windows_hash_and_phonic_guard(self) -> None:
        valid = {
            "retail_exchange": {
                "item_ids": ["item_101"],
                "new_item_ids": ["item_102"],
            },
            "telecom_mms": {
                "mmsc_url": "http://mms.example.com",
                "can_send_mms_result": True,
            },
            "frozen_benchmark_checkout": {"line_endings": "LF"},
            "phonic_voice_adapter": {
                "audio_format": "mulaw_8000",
                "queued_inter_utterance_silence_frames": False,
                "session_id": "conv_123",
            },
        }
        res = validate_tau2_exchange_mms_windows_hash_and_phonic_guard(valid)
        self.assertTrue(res.allowed)
        self.assertEqual(
            res.decision_code, "TAU2_EXCHANGE_MMS_HASH_AND_PHONIC_VERIFIED"
        )

        same_item = validate_tau2_exchange_mms_windows_hash_and_phonic_guard(
            {
                **valid,
                "retail_exchange": {
                    "item_ids": ["item_101"],
                    "new_item_ids": ["item_101"],
                },
            }
        )
        self.assertFalse(same_item.allowed)
        self.assertEqual(
            same_item.decision_code, "TAU2_RETAIL_SAME_ITEM_EXCHANGE_REJECTED"
        )

        empty_mmsc = validate_tau2_exchange_mms_windows_hash_and_phonic_guard(
            {
                **valid,
                "telecom_mms": {
                    "mmsc_url": "",
                    "can_send_mms_result": True,
                },
            }
        )
        self.assertFalse(empty_mmsc.allowed)
        self.assertEqual(
            empty_mmsc.decision_code, "TAU2_TELECOM_EMPTY_MMSC_URL_UNCONFIGURED"
        )


if __name__ == "__main__":
    unittest.main()
