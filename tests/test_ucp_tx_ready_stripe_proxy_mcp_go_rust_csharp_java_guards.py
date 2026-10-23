"""Unit tests for Stage 220 deterministic protocol security guards (`PR-01..PR-16`)."""

from __future__ import annotations

import math
import unittest

from lab.ucp_tx_ready_stripe_proxy_mcp_go_rust_csharp_java_bench import SCENARIOS
from lab.ucp_tx_ready_stripe_proxy_mcp_go_rust_csharp_java_guards import (
    GUARD_REGISTRY,
    INT64_MAX,
    INT64_MIN,
    evaluate_mcp_csharp_case_sensitive_protocol_and_java_template_notify_guard,
    evaluate_mcp_csharp_resource_indicators_and_oauth_fallback_guard,
    evaluate_mcp_go_jsonrpc_preceding_notifications_order_guard,
    evaluate_mcp_go_windows_file_root_and_int64_id_guard,
    evaluate_mcp_rust_exact_media_type_and_accept_q_guard,
    evaluate_mcp_rust_url_elicitation_sessionless_400_and_32602_guard,
    evaluate_stage220_scenario,
    evaluate_stripe_mcp_proxy_metadata_and_forwarding_error_guard,
)


class TestStage220UcpStripeMcpPolyglotGuards(unittest.TestCase):
    def test_all_16_fault_payloads_blocked_and_patched_payloads_admitted(self) -> None:
        self.assertEqual(len(SCENARIOS), 16)
        self.assertEqual(len(GUARD_REGISTRY), 16)

        for sc in SCENARIOS:
            sid = sc["id"]
            with self.subTest(scenario=sid, mode="fault"):
                fault_dec = evaluate_stage220_scenario(sid, sc["fault_payload"])
                self.assertFalse(fault_dec.allowed, f"{sid} fault should be blocked")
                self.assertEqual(fault_dec.action, "Send to a human")

            with self.subTest(scenario=sid, mode="patched"):
                patched_dec = evaluate_stage220_scenario(sid, sc["patched_payload"])
                self.assertTrue(patched_dec.allowed, f"{sid} patched should be allowed")
                self.assertEqual(patched_dec.action, "Act automatically")

    def test_edge_cases_across_stripe_go_rust_and_csharp_guards(self) -> None:
        # PR-05: notification forwarding failure must NOT produce a JSON-RPC reply
        notif_fail_ok = evaluate_stripe_mcp_proxy_metadata_and_forwarding_error_guard(
            {
                "remote_tool_title": "Create Refund",
                "proxied_tool_title": "Create Refund",
                "proxied_tool_annotations": {
                    "readOnlyHint": False,
                    "destructiveHint": True,
                    "idempotentHint": True,
                    "openWorldHint": True,
                },
                "forwarding_failed": True,
                "jsonrpc_message_kind": "notification",
                "proxy_error_reply": None,
            }
        )
        self.assertTrue(notif_fail_ok.allowed)

        notif_fail_bad = evaluate_stripe_mcp_proxy_metadata_and_forwarding_error_guard(
            {
                "remote_tool_title": "Create Refund",
                "proxied_tool_title": "Create Refund",
                "proxied_tool_annotations": {
                    "readOnlyHint": False,
                    "destructiveHint": True,
                    "idempotentHint": True,
                    "openWorldHint": True,
                },
                "forwarding_failed": True,
                "jsonrpc_message_kind": "notification",
                "proxy_error_reply": {"jsonrpc": "2.0", "error": {"code": -32603}},
            }
        )
        self.assertFalse(notif_fail_bad.allowed)
        self.assertEqual(
            notif_fail_bad.code,
            "stripe_mcp_proxy_replied_to_notification_or_response",
        )

        # PR-07: NaN, +Inf, bool, out-of-range int64, and drive-less Windows file:///foo
        for bad_id in (math.nan, math.inf, -math.inf, True, INT64_MAX + 1, INT64_MIN - 1):
            dec = evaluate_mcp_go_windows_file_root_and_int64_id_guard(
                {
                    "os_platform": "windows",
                    "file_root_uri": "file:///C:/Users/me/project",
                    "resolved_file_root": r"C:\Users\me\project",
                    "jsonrpc_id": bad_id,
                }
            )
            self.assertFalse(dec.allowed)

        driveless_dec = evaluate_mcp_go_windows_file_root_and_int64_id_guard(
            {
                "os_platform": "windows",
                "file_root_uri": "file:///foo/bar",
                "resolved_file_root": r"\foo\bar",
                "jsonrpc_id": 1,
            }
        )
        self.assertFalse(driveless_dec.allowed)
        self.assertEqual(
            driveless_dec.code, "mcp_go_windows_invalid_or_driveless_file_root"
        )

        # PR-10: nested call from active sync handler must NOT queue on handlerQueue
        nested_deadlock = evaluate_mcp_go_jsonrpc_preceding_notifications_order_guard(
            {
                "preceding_notifications_sent": 2,
                "notifications_handled_before_call_return": 0,
                "is_nested_call_from_active_sync_handler": True,
                "nested_call_queued_on_handler_queue": True,
            }
        )
        self.assertFalse(nested_deadlock.allowed)
        self.assertEqual(
            nested_deadlock.code, "mcp_go_jsonrpc_nested_sync_handler_deadlock"
        )

        nested_bypass_ok = evaluate_mcp_go_jsonrpc_preceding_notifications_order_guard(
            {
                "preceding_notifications_sent": 2,
                "notifications_handled_before_call_return": 0,
                "is_nested_call_from_active_sync_handler": True,
                "nested_call_queued_on_handler_queue": False,
            }
        )
        self.assertTrue(nested_bypass_ok.allowed)

    def test_rust_csharp_and_java_protocol_edge_cases(self) -> None:
        # PR-12: comma-joined response Content-Type rejected
        comma_ct = evaluate_mcp_rust_exact_media_type_and_accept_q_guard(
            {
                "response_content_type": "application/json, text/event-stream",
                "request_content_type": "application/json",
                "accept_headers": ["application/json, text/event-stream"],
            }
        )
        self.assertFalse(comma_ct.allowed)
        self.assertEqual(
            comma_ct.code, "mcp_rust_invalid_or_suffixed_response_media_type"
        )

        # PR-13: unserved lifecycle method must stay -32601 regardless of params
        unserved_bad = evaluate_mcp_rust_url_elicitation_sessionless_400_and_32602_guard(
            {
                "elicitation_mode": "url",
                "elicitation_id": None,
                "stateful_http_mode": True,
                "has_mcp_session_id": True,
                "jsonrpc_method": "logging/setLevel",
                "method_defined_by_sdk": True,
                "method_served_in_lifecycle": False,
                "params_valid": False,
                "jsonrpc_error_code": -32602,
            }
        )
        self.assertFalse(unserved_bad.allowed)
        self.assertEqual(
            unserved_bad.code, "mcp_rust_unserved_lifecycle_method_wrong_error_code"
        )

        # PR-15: trailing-slash issuer mismatch rejected with exact ordinal comparison
        slash_issuer = evaluate_mcp_csharp_resource_indicators_and_oauth_fallback_guard(
            {
                "resource_indicators_supported": None,
                "client_sent_resource_param": True,
                "protected_resource_metadata_available": True,
                "as_metadata_discovered": True,
                "code_challenge_methods_supported": ["S256"],
                "selected_as_identifier": "https://auth.example.com/tenant1",
                "as_metadata_issuer": "https://auth.example.com/tenant1/",
            }
        )
        self.assertFalse(slash_issuer.allowed)
        self.assertEqual(
            slash_issuer.code, "mcp_csharp_as_metadata_issuer_ordinal_mismatch"
        )

        # PR-16: removing a non-existent resource template must NOT emit list_changed
        nonexistent_notify = evaluate_mcp_csharp_case_sensitive_protocol_and_java_template_notify_guard(
            {
                "tools_call_params": {"name": "echo", "arguments": {"text": "hi"}},
                "bound_tool_name": "echo",
                "bound_arguments": {"text": "hi"},
                "to_content_block_serialized_text": '"ok"',
                "resources_list_changed_capability": True,
                "removed_template_existed": False,
                "resources_list_changed_notified": True,
            }
        )
        self.assertFalse(nonexistent_notify.allowed)
        self.assertEqual(
            nonexistent_notify.code,
            "mcp_java_remove_resource_template_notification_mismatch",
        )

        with self.assertRaises(KeyError):
            evaluate_stage220_scenario("PR-99", {})


if __name__ == "__main__":
    unittest.main()
