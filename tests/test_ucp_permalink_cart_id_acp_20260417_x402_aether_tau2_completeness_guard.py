"""Unit tests for Stage 108 protocol guardrails."""

from __future__ import annotations

import unittest

from lab.ucp_permalink_cart_id_acp_20260417_x402_aether_tau2_completeness_guard import (
    validate_acp_20260417_release_refund_minor_units_and_seller_discovery_guard,
    validate_ap2_jwt_timestamps_pay_by_bank_and_x402_aether_audit_guard,
    validate_tau2_v2_completeness_live_transcript_and_set_state_guard,
    validate_ucp_permalink_headers_cart_id_omission_and_webhook_sig_guard,
)


class TestStage108ProtocolGuards(unittest.TestCase):
    def test_ucp_permalink_cart_id_and_webhook_sig_compliant(self) -> None:
        payload = {
            "permalink_303": {
                "status_code": 303,
                "cache_control": "no-store",
                "referrer_policy": "no-referrer",
                "routed_to_continue_to_or_safe_fallback": True,
            },
            "cart_update_request": {
                "path_cart_id": "cart_abc123",
                "body": {"line_items": [{"item": {"id": "sku_1"}, "quantity": 2}]},
                "has_deprecated_transition_annotation": False,
            },
            "order_webhook": {
                "has_ucp_agent_header": True,
                "signature_input_components": [
                    "@method",
                    "@authority",
                    "@path",
                    "content-digest",
                    "content-type",
                    "ucp-agent",
                ],
            },
        }
        res = validate_ucp_permalink_headers_cart_id_omission_and_webhook_sig_guard(payload)
        self.assertTrue(res["allowed"])
        self.assertEqual(res["violations"], [])

    def test_ucp_permalink_cart_id_and_webhook_sig_violations(self) -> None:
        payload = {
            "permalink_303": {
                "status_code": 302,
                "cache_control": "public",
                "referrer_policy": "unsafe-url",
                "routed_to_continue_to_or_safe_fallback": False,
            },
            "cart_update_request": {
                "path_cart_id": "",
                "body": {"id": "cart_abc123", "line_items": []},
                "has_deprecated_transition_annotation": True,
            },
            "order_webhook": {
                "has_ucp_agent_header": True,
                "signature_input_components": ["@method", "@authority", "@path"],
            },
        }
        res = validate_ucp_permalink_headers_cart_id_omission_and_webhook_sig_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("UCP_913_MISSING_CACHE_CONTROL_NO_STORE", res["violations"])
        self.assertIn("UCP_763_633_CART_ID_FORBIDDEN_IN_UPDATE_BODY", res["violations"])
        self.assertIn("UCP_568_WEBHOOK_SIGNATURE_INPUT_MISSING_UCP_AGENT", res["violations"])

    def test_acp_20260417_refund_and_seller_discovery_compliant(self) -> None:
        payload = {
            "release_snapshot": {"supported_versions": ["2026-01-30", "2026-04-17"]},
            "webhook_refund": {"amount": 100},
            "discovery_document": {"actor_terminology": "seller"},
            "selected_fulfillment_schema_ref": "#/$defs/SelectedFulfillmentOption",
        }
        res = validate_acp_20260417_release_refund_minor_units_and_seller_discovery_guard(payload)
        self.assertTrue(res["allowed"])

    def test_acp_20260417_refund_and_seller_discovery_violations(self) -> None:
        payload = {
            "release_snapshot": {"supported_versions": ["2026-01-30"]},
            "webhook_refund": {"amount": "1.00"},
            "discovery_document": {"actor_terminology": "platform", "platform_id": "plt_1"},
            "selected_fulfillment_schema_ref": "#/definitions/SelectedFulfillmentOption",
        }
        res = validate_acp_20260417_release_refund_minor_units_and_seller_discovery_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("ACP_227_MISSING_2026_04_17_IN_SUPPORTED_VERSIONS", res["violations"])
        self.assertIn("ACP_219_WEBHOOK_REFUND_AMOUNT_MUST_BE_MINOR_UNIT_INT", res["violations"])
        self.assertIn("ACP_176_DISCOVERY_MUST_USE_SELLER_TERMINOLOGY", res["violations"])
        self.assertIn("ACP_102_INVALID_SELECTED_FULFILLMENT_OPTION_REF", res["violations"])

    def test_ap2_and_x402_aether_audit_compliant(self) -> None:
        payload = {
            "ap2_mandate": {
                "iat": 1760918400,
                "exp": 1760922000,
                "shopping_agent_validated": True,
                "payment_rail": "pay_by_bank",
                "bank_account_mandate_bound": True,
            },
            "x402_aether_audit": {
                "http_status": 402,
                "payment_required_decoded": True,
                "caip2_network": "eip155:8453",
                "usdc_asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                "payto_eip55_checksum_valid": True,
                "eip712_domain_valid": True,
                "burn_once_secret_reads": 1,
            },
        }
        res = validate_ap2_jwt_timestamps_pay_by_bank_and_x402_aether_audit_guard(payload)
        self.assertTrue(res["allowed"])

    def test_ap2_and_x402_aether_audit_violations(self) -> None:
        payload = {
            "ap2_mandate": {
                "iat": 1760922000,
                "exp": 1760918400,
                "shopping_agent_validated": False,
                "payment_rail": "pay_by_bank",
                "bank_account_mandate_bound": False,
            },
            "x402_aether_audit": {
                "http_status": 200,
                "payment_required_decoded": False,
                "caip2_network": "eip155:8453",
                "usdc_asset": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
                "payto_eip55_checksum_valid": False,
                "eip712_domain_valid": False,
                "burn_once_secret_reads": 2,
            },
        }
        res = validate_ap2_jwt_timestamps_pay_by_bank_and_x402_aether_audit_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("AP2_157_INVALID_MANDATE_JWT_IAT_EXP_TIMESTAMPS", res["violations"])
        self.assertIn("X402_367_CAIP2_USDC_ASSET_NETWORK_MISMATCH", res["violations"])
        self.assertIn("X402_343_BURN_ONCE_SECRET_READ_REPLAY_DETECTED", res["violations"])

    def test_tau2_v2_completeness_and_set_state_compliant(self) -> None:
        payload = {
            "cell_completeness": {
                "owed_calls": 4,
                "scored_calls": 3,
                "error_trials": 1,
                "unscored_missing_calls": 0,
                "reported_denominator": 3,
            },
            "live_judge_diagnostics": {
                "fingerprint_has_input_error_units": True,
                "judged_applicable_calls": 3,
                "other_judge_errors": 0,
            },
            "v1x_base_task_pin": "v1.0.1",
            "set_state_call": {
                "passes_initialization_data_arg": True,
                "positional_arg_count": 4,
            },
        }
        res = validate_tau2_v2_completeness_live_transcript_and_set_state_guard(payload)
        self.assertTrue(res["allowed"])

    def test_tau2_v2_completeness_and_set_state_violations(self) -> None:
        payload = {
            "cell_completeness": {
                "owed_calls": 4,
                "scored_calls": 0,
                "error_trials": 4,
                "unscored_missing_calls": 1,
                "reported_denominator": 4,
            },
            "live_judge_diagnostics": {
                "fingerprint_has_input_error_units": False,
                "judged_applicable_calls": 0,
                "other_judge_errors": 1,
            },
            "v1x_base_task_pin": "v1.0.0",
            "set_state_call": {
                "passes_initialization_data_arg": False,
                "positional_arg_count": 3,
            },
        }
        res = validate_tau2_v2_completeness_live_transcript_and_set_state_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("TAU2_650_INVALID_CELL_COMPLETENESS_OR_DENOMINATOR", res["violations"])
        self.assertIn("TAU2_650_VERDICT_FINGERPRINT_MISSING_INPUT_ERROR_UNITS", res["violations"])
        self.assertIn("TAU2_623_V1X_BASE_TASKS_NOT_PINNED_TO_V1_0_1", res["violations"])
        self.assertIn("TAU2_500_SET_STATE_MISSING_INITIALIZATION_DATA_ARG", res["violations"])


if __name__ == "__main__":
    unittest.main()
