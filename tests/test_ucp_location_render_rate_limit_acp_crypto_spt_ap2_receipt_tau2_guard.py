"""Unit tests for Stage 112 guardrails."""

from __future__ import annotations

import unittest

from lab.ucp_location_render_rate_limit_acp_crypto_spt_ap2_receipt_tau2_guard import (
    validate_acp_iin_length_and_crypto_spt_guard,
    validate_ap2_jwk_json_receipt_key_and_x402_eip712_domain_guard,
    validate_tau2_factory_brevity_airline_userid_and_status_bar_guard,
    validate_ucp_location_render_artifact_and_rate_limit_guard,
)


class TestStage112Guardrails(unittest.TestCase):
    def test_ucp_valid_location_render_artifact_and_rate_limit(self) -> None:
        res = validate_ucp_location_render_artifact_and_rate_limit_guard(
            {
                "context": {"location": "store_hint_01"},
                "fulfillment_pickup_location_id": "store_pickup_99",
                "claimed_effective_location": "store_pickup_99",
                "render_artifact_action": {
                    "id": "com.mercadopago.payment.render_artifact",
                    "contains_credentials_or_otp": False,
                    "uses_continue_url_redirect": False,
                    "instructions_url": "https://www.mercadopago.com/pix/instructions/123",
                    "allowed_https_origins": ["https://www.mercadopago.com"],
                },
                "mcp_error": {"error_slug": "rate_limit_exceeded", "code": -32004, "declared_methods_count": 13},
            }
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.decision_code, "UCP_LOCATION_RENDER_ARTIFACT_AND_RATE_LIMIT_VERIFIED")

    def test_ucp_rejects_location_override_failure_and_render_artifact_required(self) -> None:
        res1 = validate_ucp_location_render_artifact_and_rate_limit_guard(
            {
                "context": {"location": "store_hint_01"},
                "fulfillment_pickup_location_id": "store_pickup_99",
                "claimed_effective_location": "store_hint_01",
            }
        )
        self.assertFalse(res1.allowed)
        self.assertEqual(res1.decision_code, "UCP_LOCATION_PRECEDENCE_VIOLATION")

        res2 = validate_ucp_location_render_artifact_and_rate_limit_guard(
            {
                "render_artifact_action": {
                    "id": "com.mercadopago.payment.render_artifact",
                    "required": True,
                }
            }
        )
        self.assertFalse(res2.allowed)
        self.assertEqual(res2.decision_code, "UCP_RENDER_ARTIFACT_FORBIDDEN_REQUIRED_FIELD")

    def test_acp_valid_8digit_iin_and_crypto_spt(self) -> None:
        res = validate_acp_iin_length_and_crypto_spt_guard(
            {
                "payment_method_card": {"iin": "41111122"},
                "payment_method_crypto": {
                    "type": "crypto",
                    "network": "eip155:8453",
                    "signature_verified": True,
                    "nonce_unused": True,
                    "valid_before": 1780000500,
                    "current_unix": 1780000000,
                    "x402_amount_minor": 2500,
                    "allowance_amount_minor": 2500,
                },
            }
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.decision_code, "ACP_IIN_LENGTH_AND_CRYPTO_SPT_VERIFIED")

    def test_acp_rejects_9digit_iin_and_x402_amount_mismatch(self) -> None:
        res1 = validate_acp_iin_length_and_crypto_spt_guard({"payment_method_card": {"iin": "411111229"}})
        self.assertFalse(res1.allowed)
        self.assertEqual(res1.decision_code, "ACP_CARD_IIN_LENGTH_OR_FORMAT_INVALID")

        res2 = validate_acp_iin_length_and_crypto_spt_guard(
            {
                "payment_method_crypto": {
                    "type": "crypto",
                    "network": "eip155:8453",
                    "signature_verified": True,
                    "nonce_unused": True,
                    "valid_before": 1780000500,
                    "current_unix": 1780000000,
                    "x402_amount_minor": 5000,
                    "allowance_amount_minor": 2500,
                }
            }
        )
        self.assertFalse(res2.allowed)
        self.assertEqual(res2.decision_code, "ACP_X402_ALLOWANCE_AMOUNT_MISMATCH")

    def test_ap2_and_x402_valid_jwk_receipt_and_eip712_domain(self) -> None:
        res = validate_ap2_jwk_json_receipt_key_and_x402_eip712_domain_guard(
            {
                "ap2_cnf_jwk": {"kty": "EC", "crv": "P-256", "use": "sig"},
                "ap2_receipt_verification": {
                    "public_key_kind": "pyca_ec",
                    "signature_valid": True,
                    "reference_callback_invoked": True,
                    "reference_in_store": True,
                },
                "x402_eip3009_domain": {
                    "payment_requirements": {
                        "network": "eip155:8453",
                        "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                        "extra": {"name": "USD Coin", "version": "2"},
                    },
                    "eip712_domain": {
                        "name": "USD Coin",
                        "version": "2",
                        "chainId": 8453,
                        "verifyingContract": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                    },
                },
            }
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.decision_code, "AP2_JWK_RECEIPT_AND_X402_EIP712_DOMAIN_VERIFIED")

    def test_ap2_and_x402_reject_unserialized_enum_and_callback_before_sig(self) -> None:
        res1 = validate_ap2_jwk_json_receipt_key_and_x402_eip712_domain_guard(
            {"ap2_cnf_jwk": {"kty": "EC", "use": "Use.sig"}}
        )
        self.assertFalse(res1.allowed)
        self.assertEqual(res1.decision_code, "AP2_CNF_JWK_ENUM_NOT_JSON_SERIALIZED")

        res2 = validate_ap2_jwk_json_receipt_key_and_x402_eip712_domain_guard(
            {
                "ap2_receipt_verification": {
                    "public_key_kind": "pyca_ec",
                    "signature_valid": False,
                    "reference_callback_invoked": True,
                }
            }
        )
        self.assertFalse(res2.allowed)
        self.assertEqual(res2.decision_code, "AP2_RECEIPT_REFERENCE_CALLBACK_BEFORE_SIG_CHECK")

    def test_tau2_valid_factory_airline_and_status_bar(self) -> None:
        res = validate_tau2_factory_brevity_airline_userid_and_status_bar_guard(
            {
                "factory_draft": {
                    "pack_language": "de",
                    "has_language_directive_origin": True,
                    "non_directed_phrases": ["Einen Moment bitte", "Ich schaue nach"],
                    "repair_attempts": 1,
                },
                "airline_tool_call": {"tool": "get_user_details", "user_id": "sara_doe_496"},
                "telecom_tool_grounding": {"referenced_user_tools": ["check_status_bar", "check_network_status"]},
            }
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.decision_code, "TAU2_FACTORY_AIRLINE_USERID_AND_STATUS_BAR_VERIFIED")

    def test_tau2_rejects_capitalized_airline_userid_and_get_status_bar(self) -> None:
        res1 = validate_tau2_factory_brevity_airline_userid_and_status_bar_guard(
            {"airline_tool_call": {"tool": "get_user_details", "user_id": "Sara_Doe_496"}}
        )
        self.assertFalse(res1.allowed)
        self.assertEqual(res1.decision_code, "TAU2_AIRLINE_USER_ID_NOT_LOWERCASE")

        res2 = validate_tau2_factory_brevity_airline_userid_and_status_bar_guard(
            {"telecom_tool_grounding": {"referenced_user_tools": ["get_status_bar"]}}
        )
        self.assertFalse(res2.allowed)
        self.assertEqual(res2.decision_code, "TAU2_TELECOM_STATUS_BAR_TOOL_GROUNDING_MISMATCH")


if __name__ == "__main__":
    unittest.main()
