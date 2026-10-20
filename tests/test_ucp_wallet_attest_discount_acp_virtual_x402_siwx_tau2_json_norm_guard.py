"""Unit tests for Stage 94 deterministic guardrails."""

from __future__ import annotations

import unittest

from lab.ucp_wallet_attest_discount_acp_virtual_x402_siwx_tau2_json_norm_guard import (
    validate_acp_card_virtual_address_and_client_ref_guard,
    validate_tau2_nested_json_numeric_seed_and_batch_guard,
    validate_ucp_wallet_attestation_inapplicable_discount_and_order_guard,
    validate_x402_mcp_siwx_entitlement_and_witness_sar_guard,
)


class TestStage94Guards(unittest.TestCase):
    def test_ucp_wallet_attestation_inapplicable_discount_and_order_valid(self) -> None:
        payload = {
            "identity_mechanism": {
                "type": "wallet_attestation",
                "provider_jwks": "https://verifier.example.com/.well-known/jwks.json",
                "derived_oauth_scopes": [],
            },
            "current_timestamp": 1760000000,
            "context_eligibility": ["com.example.token_holder"],
            "attestations": {
                "com.example.token_holder": {
                    "provider_jwks": "https://verifier.example.com/.well-known/jwks.json",
                    "kid": "key-2026-01",
                    "sig_verified": True,
                    "payload": {"id": "att-1", "pass": True},
                    "expires_at": 1760001800,
                }
            },
            "discounts": {
                "codes": ["SUMMER20", "EXPIRED50"],
                "applied": [{"code": "SUMMER20", "amount": 2000}],
                "inapplicable": [
                    {
                        "code": "EXPIRED50",
                        "reason": "discount_code_expired",
                        "content": "Code EXPIRED50 expired.",
                    }
                ],
            },
            "order": {"id": "ord_1", "currency": "USD"},
            "ec_link_delegation": {
                "ec_delegate_link_open": True,
                "ec_link_open_request_sent": True,
                "direct_iframe_navigation_attempted": False,
            },
        }
        res = validate_ucp_wallet_attestation_inapplicable_discount_and_order_guard(payload)
        self.assertTrue(res["allowed"])

    def test_ucp_unverified_attestation_or_missing_currency_blocked(self) -> None:
        payload = {
            "identity_mechanism": {
                "type": "wallet_attestation",
                "provider_jwks": "http://insecure.example.com/jwks.json",
                "derived_oauth_scopes": ["ucp:shopping:checkout"],
            },
            "current_timestamp": 1760000000,
            "context_eligibility": ["com.example.vip"],
            "attestations": {},
            "discounts": {
                "codes": ["BADCODE"],
                "applied": [],
                "inapplicable": [],
            },
            "order": {"id": "ord_1", "currency": ""},
            "ec_link_delegation": {
                "ec_delegate_link_open": True,
                "ec_link_open_request_sent": False,
                "direct_iframe_navigation_attempted": True,
            },
        }
        res = validate_ucp_wallet_attestation_inapplicable_discount_and_order_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("UCP_WALLET_ATTESTATION_HTTPS_JWKS_REQUIRED", res["violations"])
        self.assertIn("UCP_ELIGIBILITY_ATTESTATION_MISSING:com.example.vip", res["violations"])
        self.assertIn("UCP_ORDER_CURRENCY_REQUIRED_ISO4217", res["violations"])

    def test_acp_card_virtual_address_and_client_ref_valid(self) -> None:
        payload = {
            "payment_method_card": {"type": "card", "virtual": True},
            "address": {"email": "buyer@example.com", "phone": "+14155550199"},
            "allowance_expires_at": "2026-10-21T05:00:00Z",
            "delegate_response_expires_at": "2026-10-21T05:00:00Z",
            "payment_handlers": [{"id": "pm_1", "display_order": 0}],
            "request_client_reference_id": "agent_ref_94",
            "order_client_reference_id": "agent_ref_94",
        }
        res = validate_acp_card_virtual_address_and_client_ref_guard(payload)
        self.assertTrue(res["allowed"])

    def test_acp_missing_card_virtual_or_negative_display_order_blocked(self) -> None:
        payload = {
            "payment_method_card": {"type": "card", "virtual": None},
            "address": {"email": "invalid-email", "phone": "x" * 40},
            "allowance_expires_at": "2026-10-21T05:00:00Z",
            "delegate_response_expires_at": "2026-10-21T06:00:00Z",
            "payment_handlers": [{"id": "pm_1", "display_order": -1}],
            "request_client_reference_id": "agent_ref_94",
            "order_client_reference_id": "tampered_ref",
        }
        res = validate_acp_card_virtual_address_and_client_ref_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("ACP_PAYMENT_METHOD_CARD_VIRTUAL_BOOLEAN_REQUIRED", res["violations"])
        self.assertIn("ACP_HANDLER_DISPLAY_ORDER_INVALID:pm_1", res["violations"])
        self.assertIn("ACP_ORDER_CLIENT_REFERENCE_ID_MISMATCH", res["violations"])

    def test_x402_mcp_siwx_entitlement_and_witness_sar_valid(self) -> None:
        payload = {
            "mcp_tool_invocation": {
                "call_index": 1,
                "tool_name": "premium_market_feed",
                "payment_settled": False,
                "siwx_wallet_auth_verified": True,
                "stored_entitlement_active": True,
                "entitlement_tool_name": "premium_market_feed",
            },
            "settlement_attestation_receipt": {
                "task_satisfied": True,
                "witness_signature_valid": True,
            },
        }
        res = validate_x402_mcp_siwx_entitlement_and_witness_sar_guard(payload)
        self.assertTrue(res["allowed"])

    def test_x402_cross_tool_siwx_reuse_or_invalid_sar_blocked(self) -> None:
        payload = {
            "mcp_tool_invocation": {
                "call_index": 1,
                "tool_name": "expensive_exec_tool",
                "payment_settled": False,
                "siwx_wallet_auth_verified": True,
                "stored_entitlement_active": True,
                "entitlement_tool_name": "cheap_search_tool",
            },
            "settlement_attestation_receipt": {
                "task_satisfied": False,
                "witness_signature_valid": False,
            },
        }
        res = validate_x402_mcp_siwx_entitlement_and_witness_sar_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("X402_MCP_SIWX_CROSS_TOOL_ENTITLEMENT_REUSE_FORBIDDEN", res["violations"])
        self.assertIn("X402_SAR_TASK_SPECIFICATION_NOT_SATISFIED", res["violations"])

    def test_tau2_nested_json_numeric_seed_and_batch_valid(self) -> None:
        payload = {
            "nested_json_comparison": {
                "gold_arg": '{"account_type":"savings","account_class":"Green Account"}',
                "predicted_arg": '{"account_class": "Green Account", "account_type": "savings"}',
                "expected_equal": True,
            },
            "banking_numeric_call": {
                "tool_name": "apply_savings_account_credit_6831",
                "amount_or_limit": 33,
                "recorded_id_seed_amount": "33.00",
            },
            "batch_evaluator_event": {
                "exception_type": "ValueError",
                "aborted_entire_batch": False,
                "fallback_reward": 0.0,
            },
        }
        res = validate_tau2_nested_json_numeric_seed_and_batch_guard(payload)
        self.assertTrue(res["allowed"])

    def test_tau2_fractional_int_tool_or_swallowed_criteria_error_blocked(self) -> None:
        payload = {
            "banking_numeric_call": {
                "tool_name": "request_temporary_debit_card_limit_increase_8374",
                "amount_or_limit": 2500.5,
            },
            "batch_evaluator_event": {
                "exception_type": "EvaluationCriteriaError",
                "reraised_loudly": False,
            },
        }
        res = validate_tau2_nested_json_numeric_seed_and_batch_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn(
            "TAU2_BANKING_INTEGER_TOOL_FRACTIONAL_VALUE_FORBIDDEN:request_temporary_debit_card_limit_increase_8374",
            res["violations"],
        )
        self.assertIn("TAU2_EVALUATION_CRITERIA_ERROR_SILENTLY_SWALLOWED", res["violations"])


if __name__ == "__main__":
    unittest.main()
