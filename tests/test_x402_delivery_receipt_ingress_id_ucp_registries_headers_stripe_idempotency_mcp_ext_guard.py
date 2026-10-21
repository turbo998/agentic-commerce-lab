"""Unit tests for Stage 126 guard module."""

from __future__ import annotations

import unittest

from lab.x402_delivery_receipt_ingress_id_ucp_registries_headers_stripe_idempotency_mcp_ext_guard import (
    evaluate_stripe_idempotency_mcp_ext_guard,
    evaluate_ucp_terms_registry_headers_guard,
    evaluate_x402_delivery_receipt_ingress_chains,
    parse_unquoted_cache_control_directives,
)


class TestStage126Guard(unittest.TestCase):
    def test_x402_delivery_receipt_ingress_chains(self) -> None:
        self.assertEqual(
            parse_unquoted_cache_control_directives('max-age=60, example="a, private, b"'),
            ["max-age", "example"],
        )
        ok = evaluate_x402_delivery_receipt_ingress_chains(
            {
                "http_method": "POST",
                "resource_info_paid_method": "POST",
                "ingress_identity": "id_ing_99",
                "payment_call": {"kind": "mcp", "toolName": "quote_swap", "arguments": {"pair": "ETH/USDC"}},
                "delivery_receipt_mode": "reference",
                "delivery_receipt_header_bytes": 480,
                "cache_control_in": 'max-age=60, example="a, private, b"',
            }
        )
        self.assertTrue(ok.allowed)
        self.assertTrue(ok.cache_control_out.endswith(", private"))

        # OPTIONS preflight charged 402 (#3738)
        bad_opt = evaluate_x402_delivery_receipt_ingress_chains(
            {"http_method": "OPTIONS", "options_preflight_charged_402": True}
        )
        self.assertFalse(bad_opt.allowed)
        self.assertEqual(bad_opt.decision_code, "X402_OPTIONS_PREFLIGHT_CHARGED_402")

        # Paid HTTP method mismatch (#3741)
        bad_method = evaluate_x402_delivery_receipt_ingress_chains(
            {"http_method": "GET", "resource_info_paid_method": "POST"}
        )
        self.assertFalse(bad_method.allowed)
        self.assertEqual(bad_method.decision_code, "X402_RESOURCE_INFO_PAID_METHOD_MISMATCH")

        # Downstream re-derivation of ingress identity (#3776)
        bad_id = evaluate_x402_delivery_receipt_ingress_chains(
            {"ingress_identity": "id_1", "replay_lookup_identity": "id_2"}
        )
        self.assertFalse(bad_id.allowed)
        self.assertEqual(bad_id.decision_code, "X402_INGRESS_IDENTITY_REDERIVED_OR_SPLIT")

        # SVM confirmed failure marked pending (#3784)
        bad_svm = evaluate_x402_delivery_receipt_ingress_chains(
            {"svm_confirmed_with_status_err": True, "svm_recorded_status": "settlement_pending"}
        )
        self.assertFalse(bad_svm.allowed)
        self.assertEqual(bad_svm.decision_code, "X402_SVM_CONFIRMED_FAILURE_MARKED_PENDING")

        # EVM upto simulated with ceiling instead of settlement amount (#3769)
        bad_upto = evaluate_x402_delivery_receipt_ingress_chains(
            {
                "upto_settlement_amount": 150,
                "upto_ceiling_amount": 1000,
                "upto_simulated_amount": 1000,
                "upto_payer_balance": 400,
            }
        )
        self.assertFalse(bad_upto.allowed)
        self.assertEqual(bad_upto.decision_code, "X402_EVM_UPTO_SIMULATED_CEILING_INSTEAD_OF_SETTLEMENT")

    def test_ucp_terms_registry_headers_guard(self) -> None:
        ok = evaluate_ucp_terms_registry_headers_guard(
            {
                "payment_terms_capability_id": "dev.ucp.common.payment.terms",
                "lockfile_registry_urls": ["https://registry.npmjs.org/pkg", "https://pypi.org/simple/pkg"],
                "has_ucp_agent_header": True,
                "is_location_rest_call": True,
                "location_headers": {"Request-Id": "req_1", "UCP-Agent": "agent_1"},
            }
        )
        self.assertTrue(ok.allowed)

        bad_terms = evaluate_ucp_terms_registry_headers_guard(
            {"payment_terms_capability_id": "dev.ucp.common.payment.payment_terms"}
        )
        self.assertFalse(bad_terms.allowed)
        self.assertEqual(bad_terms.decision_code, "UCP_PAYMENT_TERMS_CAPABILITY_ID_INVALID")

        bad_reg = evaluate_ucp_terms_registry_headers_guard(
            {"lockfile_registry_urls": ["https://my-corp.d.codeartifact.us-east-1.amazonaws.com/pypi/simple"]}
        )
        self.assertFalse(bad_reg.allowed)
        self.assertEqual(bad_reg.decision_code, "UCP_NON_PUBLIC_LOCKFILE_REGISTRY_BLOCKED")

        bad_cov = evaluate_ucp_terms_registry_headers_guard(
            {"has_ucp_agent_header": True, "covered_components": ["@method", "@authority", "@path"]}
        )
        self.assertFalse(bad_cov.allowed)
        self.assertEqual(bad_cov.decision_code, "UCP_SIGNATURE_MISSING_UCP_AGENT_COVERAGE")

    def test_stripe_idempotency_mcp_ext_guard(self) -> None:
        ok = evaluate_stripe_idempotency_mcp_ext_guard(
            {
                "agent_id": "agent_billing_1",
                "tool_name": "create_payment_intent",
                "agent_allowed_tools": ["create_payment_intent"],
                "is_list_or_search_tool": True,
                "supports_starting_after_cursor": True,
                "mcp_protocol_version": "2025-11-25",
                "mcp_extension_negotiation_carrier": "initialize_handshake",
            }
        )
        self.assertTrue(ok.allowed)
        self.assertEqual(len(ok.derived_idempotency_key), 32)

        bad_retry = evaluate_stripe_idempotency_mcp_ext_guard(
            {"agent_retry_regenerated_random_idempotency_key": True}
        )
        self.assertFalse(bad_retry.allowed)
        self.assertEqual(bad_retry.decision_code, "STRIPE_RETRY_DUPLICATE_CHARGE_OR_MISSING_PAGINATION")

        bad_mcp = evaluate_stripe_idempotency_mcp_ext_guard({"mcp_extension_order_dependent": True})
        self.assertFalse(bad_mcp.allowed)
        self.assertEqual(bad_mcp.decision_code, "MCP_SDK_EXTENSION_POINT_OR_NEGOTIATION_MISMATCH")


if __name__ == "__main__":
    unittest.main()
