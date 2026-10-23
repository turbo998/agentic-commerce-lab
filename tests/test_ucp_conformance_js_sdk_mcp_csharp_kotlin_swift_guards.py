"""Unit tests for Stage 224 deterministic guards (`PR-01..PR-16`)."""

from __future__ import annotations

import unittest

from lab.ucp_conformance_js_sdk_mcp_csharp_kotlin_swift_bench import get_scenarios
from lab.ucp_conformance_js_sdk_mcp_csharp_kotlin_swift_guards import (
    evaluate_mcp_csharp_delegating_schema_serverinfo_uritemplate_and_killtree_guard,
    evaluate_mcp_kotlin_send_error_mcp_headers_and_uri_template_guard,
    evaluate_mcp_swift_oauth_www_auth_pkce_basic_and_issuer_guard,
    evaluate_ucp_payment_terms_conformance_invariants_guard,
)


class TestStage224Guards(unittest.TestCase):
    def test_all_16_fault_payloads_blocked(self) -> None:
        scenarios = get_scenarios()
        self.assertEqual(len(scenarios), 16)
        for item in scenarios:
            res = item["evaluator"](item["fault_payload"])
            self.assertFalse(res["allow"], msg=item["scenario_id"])
            self.assertEqual(
                res["decision_code"], item["expected_block_code"], msg=item["scenario_id"]
            )

    def test_all_16_patched_payloads_allowed(self) -> None:
        scenarios = get_scenarios()
        self.assertEqual(len(scenarios), 16)
        for item in scenarios:
            res = item["evaluator"](item["patched_payload"])
            self.assertTrue(res["allow"], msg=item["scenario_id"])
            self.assertEqual(
                res["decision_code"], item["expected_allow_code"], msg=item["scenario_id"]
            )

    def test_edge_cases_across_ucp_and_mcp_sdks(self) -> None:
        # PR-04 naive due_at without UTC offset rejected
        res_naive = evaluate_ucp_payment_terms_conformance_invariants_guard(
            {
                "terms": [
                    {
                        "id": "net_30",
                        "schedules": [{"amount": 1000, "due_at": "2026-11-23T00:00:00"}],
                    }
                ],
                "selected_term_id": "net_30",
                "checkout_total": 1000,
                "order_accepted_term": {
                    "id": "net_30",
                    "schedules": [{"amount": 1000, "due_at": "2026-11-23T00:00:00Z"}],
                },
                "order_total": 1000,
            }
        )
        self.assertFalse(res_naive["allow"])
        self.assertEqual(
            res_naive["decision_code"], "UCP_PAYMENT_TERMS_NAIVE_OR_INVALID_DUE_AT_BLOCKED"
        )

        # PR-09 encoded comma %2C in multi-variable URI template preserved inside value
        res_comma = evaluate_mcp_csharp_delegating_schema_serverinfo_uritemplate_and_killtree_guard(
            {
                "delegating_tool_legacy_output_schema_transformed": True,
                "connected_without_server_info_returns_null": True,
                "disconnected_server_info_throws": True,
                "uri_template": "resource://coords/{+lat,lon}",
                "uri_input": "resource://coords/a%2Cb,c",
                "parsed_vars": {"lat": "a,b", "lon": "c"},
                "kill_tree_waits_for_descendants": True,
                "pid_reuse_start_time_checked": True,
            }
        )
        self.assertTrue(res_comma["allow"])

        # PR-12 blank resource URI rejected
        res_blank = evaluate_mcp_kotlin_send_error_mcp_headers_and_uri_template_guard(
            {
                "sync_send_failure_on_error_calls": 0,
                "sync_send_failure_thrown_to_caller": True,
                "is_notification": False,
                "method": "resources/read",
                "headers": {"Mcp-Method": "resources/read", "Mcp-Name": ""},
                "resource_uri": "   ",
                "template_variable_capture": "",
            }
        )
        self.assertFalse(res_blank["allow"])
        self.assertEqual(
            res_blank["decision_code"], "MCP_KOTLIN_BLANK_URI_OR_EMPTY_CAPTURE_BLOCKED"
        )

        # PR-14 unencoded colon in client_id rejected
        res_basic = evaluate_mcp_swift_oauth_www_auth_pkce_basic_and_issuer_guard(
            {
                "raw_quoted_param": r"read\\write",
                "parsed_quoted_param": r"read\write",
                "pkce_rejection_threshold": 197,
                "client_id": "app:1",
                "client_secret": "sec",
                "basic_auth_header": "Basic YXBwOjE6c2Vj",
                "metadata_issuer": "https://auth.example.com",
                "callback_issuer": "https://auth.example.com",
                "re_registered_on_as_change": True,
            }
        )
        self.assertFalse(res_basic["allow"])
        self.assertEqual(
            res_basic["decision_code"], "MCP_SWIFT_CLIENT_SECRET_BASIC_UNENCODED_BLOCKED"
        )


if __name__ == "__main__":
    unittest.main()
