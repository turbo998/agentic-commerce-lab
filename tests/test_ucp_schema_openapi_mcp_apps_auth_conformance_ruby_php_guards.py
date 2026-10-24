"""Unit tests for Stage 226 UCP Schema OpenAPI/Codegen & MCP Apps, Auth,
Conformance, Ruby & PHP SDK deterministic guards (`PR-01..PR-16`).
"""

from __future__ import annotations

import unittest

from lab.ucp_schema_openapi_mcp_apps_auth_conformance_ruby_php_bench import (
    build_stage227_scenarios,
)
from lab.ucp_schema_openapi_mcp_apps_auth_conformance_ruby_php_guards import (
    evaluate_mcp_conformance_url_elicitation_and_stream_guard,
    evaluate_mcp_ext_apps_iframe_allow_and_normative_spec_guard,
    evaluate_mcp_ext_auth_dpop_and_sep3392_guard,
    evaluate_mcp_php_sdk_session_lock_sse_queue_and_202_guard,
    evaluate_mcp_ruby_sdk_bytes_utf8_ping_and_capabilities_guard,
    evaluate_stage226_scenario,
    evaluate_ucp_schema_generate_openapi_binding_guard,
    evaluate_ucp_schema_open_union_and_extended_subtype_guard,
)


class TestStage226Guards(unittest.TestCase):
    def test_all_16_fault_payloads_blocked(self) -> None:
        for item in build_stage227_scenarios():
            res = evaluate_stage226_scenario(item["scenario_id"], item["fault_payload"])
            self.assertFalse(res["allow"], msg=f"{item['scenario_id']} fault was not blocked: {res}")
            self.assertTrue(res["code"].startswith("BLOCKED_"), msg=res["code"])

    def test_all_16_patched_payloads_allowed(self) -> None:
        for item in build_stage227_scenarios():
            res = evaluate_stage226_scenario(item["scenario_id"], item["patched_payload"])
            self.assertTrue(res["allow"], msg=f"{item['scenario_id']} patched was not allowed: {res}")
            self.assertTrue(res["code"].startswith("ALLOW_"), msg=res["code"])

    def test_edge_cases_across_ucp_schema_and_mcp_ecosystem(self) -> None:
        # PR-01: missing REST binding must exit with code 2
        res_oa = evaluate_ucp_schema_generate_openapi_binding_guard(
            {"has_rest_binding": False, "has_service_schema": True, "exit_code": 0}
        )
        self.assertFalse(res_oa["allow"])
        self.assertEqual(res_oa["code"], "BLOCKED_OPENAPI_INVALID_SERVICE_BINDING_EXIT_CODE")

        # PR-02: extended subtype tag missing from base not.enum
        res_ou = evaluate_ucp_schema_open_union_and_extended_subtype_guard(
            {
                "union_name": "FulfillmentDestination",
                "anyof_refs": [
                    "#/$defs/ShippingDestination",
                    "#/$defs/LockerPickupDestination",
                    "#/$defs/FulfillmentDestinationBase",
                ],
                "known_variant_refs": ["#/$defs/ShippingDestination"],
                "extended_subtype_refs": ["#/$defs/LockerPickupDestination"],
                "known_tags": ["shipping"],
                "extended_tags": ["locker_pickup"],
                "base_not_enum": ["shipping"],
            }
        )
        self.assertFalse(res_ou["allow"])
        self.assertEqual(res_ou["code"], "BLOCKED_OU2_BASE_NOT_ENUM_MISSING_EXTENDED_TAGS")

        # PR-05: space-separated iframe allow attribute rejected
        res_apps = evaluate_mcp_ext_apps_iframe_allow_and_normative_spec_guard(
            {
                "declared_permissions": ["camera", "clipboard-write"],
                "iframe_allow_attr": "camera clipboard-write",
                "handshake_method": "ui/initialize",
                "handshake_params": {"appInfo": {}, "appCapabilities": {}, "protocolVersion": "2026-01-26"},
                "teardown_is_request_with_id": True,
                "default_connect_src": "'none'",
            }
        )
        self.assertFalse(res_apps["allow"])
        self.assertEqual(res_apps["code"], "BLOCKED_IFRAME_ALLOW_PERMISSION_POLICY_MALFORMED")

        # PR-08: DPoP proof failure returning invalid_token instead of invalid_dpop_proof
        res_dpop = evaluate_mcp_ext_auth_dpop_and_sep3392_guard(
            {
                "token_is_dpop_bound": True,
                "auth_scheme": "DPoP",
                "http_status": 401,
                "dpop_proof_valid": False,
                "error_code": "invalid_token",
                "dpop_signing_alg_values_supported": ["ES256"],
                "dpop_jkt_bound_to_auth_code": True,
                "dpop_and_wif_in_experimental_dir": True,
            }
        )
        self.assertFalse(res_dpop["allow"])
        self.assertEqual(res_dpop["code"], "BLOCKED_DPOP_PROOF_FAILURE_WRONG_ERROR_CODE")

        # PR-09: retired -32042 URLElicitationRequiredError rejected
        res_url = evaluate_mcp_conformance_url_elicitation_and_stream_guard(
            {
                "elicitation_sent_on_originating_post_stream": True,
                "emitted_error_code": -32042,
            }
        )
        self.assertFalse(res_url["allow"])
        self.assertEqual(res_url["code"], "BLOCKED_RETIRED_URL_ELICITATION_REQUIRED_ERROR_32042")

        # PR-13: invalid UTF-8 JSON key returning -32603 instead of -32700
        res_ruby = evaluate_mcp_ruby_sdk_bytes_utf8_ping_and_capabilities_guard(
            {
                "stdio_frames_stripped_as_bytes": True,
                "invalid_utf8_key_error_code": -32603,
                "invalid_utf8_key_http_status": 500,
                "unencodable_ping_skipped": True,
                "unreadable_id_omitted_from_error": True,
                "stateless_init_strips_list_changed_and_subscribe": True,
            }
        )
        self.assertFalse(res_ruby["allow"])
        self.assertEqual(res_ruby["code"], "BLOCKED_RUBY_INVALID_UTF8_KEY_NOT_PARSE_ERROR_32700")

        # PR-15: queued notifications bundled into JSON array rejected
        res_php = evaluate_mcp_php_sdk_session_lock_sse_queue_and_202_guard(
            {
                "lock_unavailable_http_status": 503,
                "lock_unavailable_error_code": -32603,
                "lock_unavailable_message": "Session lock is unavailable.",
                "has_queued_notifications_on_request": True,
                "request_answer_content_type": "application/json",
                "bundled_into_json_array": True,
                "notification_only_post_status": 202,
                "notification_only_post_body": "",
                "notification_only_drained_queue": False,
            }
        )
        self.assertFalse(res_php["allow"])
        self.assertEqual(res_php["code"], "BLOCKED_PHP_QUEUED_NOTIFICATIONS_BUNDLED_AS_JSON_ARRAY")


if __name__ == "__main__":
    unittest.main()
