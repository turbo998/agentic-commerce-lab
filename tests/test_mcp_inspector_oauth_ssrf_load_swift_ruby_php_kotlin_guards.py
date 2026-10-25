"""Unit tests for Stage 246 MCP Inspector & Swift/Ruby/PHP/Kotlin SDK guards (`PR-01..PR-16`)."""

from __future__ import annotations

import unittest

from lab.mcp_inspector_oauth_ssrf_load_swift_ruby_php_kotlin_guards import (
    evaluate_inspector_cli_rate_limit_and_load_slo_guard,
    evaluate_inspector_oauth_destination_ssrf_guard,
    evaluate_inspector_oauth_refresh_scope_guard,
    evaluate_inspector_skills_sdk_hybrid_guard,
    evaluate_inspector_static_issuer_stamp_and_dcr_secret_guard,
    evaluate_inspector_ui_sort_bind_and_release_guard,
    evaluate_kotlin_016_sse_deprecation_and_api_migration_guard,
    evaluate_kotlin_flow_pagination_and_cursor_cycle_guard,
    evaluate_php_gateway_progress_token_and_list_changed_guard,
    evaluate_php_reconnect_transport_close_and_vanished_stream_guard,
    evaluate_php_structured_tool_output_and_session_gc_guard,
    evaluate_ruby_initialize_sse_return_and_dns_rebinding_guard,
    evaluate_ruby_jsonrpc_null_id_and_string_id_guard,
    evaluate_ruby_listen_subscribe_handler_and_exception_reporter_guard,
    evaluate_swift_data_url_header_and_byte_decode_guard,
    evaluate_swift_transport_heartbeat_oauth_port_and_coder_guard,
)


class TestStage246InspectorAndMultiSdkGuards(unittest.TestCase):
    def test_pr01_to_pr08_inspector_and_swift_sdk_guards(self) -> None:
        # PR-01
        r1_ok = evaluate_inspector_oauth_refresh_scope_guard(
            {
                "scope_on_refresh": True,
                "tokens_scope": None,
                "stored_request_scope": "mcp:tools offline_access",
                "configured_scope": "mcp:tools",
                "request_refresh_token": False,
                "ema_delegates_scope_for_refresh": True,
                "persisted_config_has_false_flag": False,
                "actual_refresh_scope": "mcp:tools",
            }
        )
        self.assertTrue(r1_ok.passed)
        r1_bad = evaluate_inspector_oauth_refresh_scope_guard(
            {
                "scope_on_refresh": False,
                "persisted_config_has_false_flag": True,
                "actual_refresh_scope": None,
            }
        )
        self.assertFalse(r1_bad.passed)

        # PR-02
        r2_ok = evaluate_inspector_skills_sdk_hybrid_guard(
            {
                "file_count": 12,
                "total_bytes": 1024,
                "digest": "sha256:" + "b" * 64,
                "negotiated_era": "2026-07-28",
                "directory_result": {"ttlMs": 5000, "cacheScope": "public"},
            }
        )
        self.assertTrue(r2_ok.passed)
        r2_bad = evaluate_inspector_skills_sdk_hybrid_guard(
            {
                "file_count": 12,
                "total_bytes": 1024,
                "digest": "md5:1234",
                "negotiated_era": "2026-07-28",
                "directory_result": {"ttlMs": 5000, "cacheScope": "public"},
            }
        )
        self.assertFalse(r2_bad.passed)

        # PR-03
        r3_ok = evaluate_inspector_oauth_destination_ssrf_guard(
            {
                "is_mcp_wire_request": False,
                "hops": [
                    {
                        "url": "https://auth.example.com/authorize",
                        "resolved_ips": ["93.184.216.34"],
                    }
                ],
            }
        )
        self.assertTrue(r3_ok.passed)
        r3_bad = evaluate_inspector_oauth_destination_ssrf_guard(
            {
                "is_mcp_wire_request": False,
                "hops": [
                    {
                        "url": "http://[fd00:ec2::254]/latest/meta-data",
                        "resolved_ips": ["fd00:ec2::254"],
                    }
                ],
            }
        )
        self.assertFalse(r3_bad.passed)

        # PR-04
        r4_ok = evaluate_inspector_static_issuer_stamp_and_dcr_secret_guard(
            {
                "registration_kind": "preregistered",
                "preregistered_client_id": "c1",
                "saved_client_id": "c1",
                "back_stamped_slot": "preregistered",
                "stored_issuer_stamp": "https://as1.example",
                "context_issuer": "https://as2.example",
                "reseed_client_changed": False,
                "returned_issuer_stamp": None,
            }
        )
        self.assertTrue(r4_ok.passed)
        r4_bad = evaluate_inspector_static_issuer_stamp_and_dcr_secret_guard(
            {
                "registration_kind": "dynamic",
                "dcr_state_client_id": "client-b",
                "dcr_secret_stamp_owner": "client-a",
                "dcr_secret_mac_valid": True,
                "dcr_secret_returned": True,
            }
        )
        self.assertFalse(r4_bad.passed)

        # PR-05
        r5_ok = evaluate_inspector_cli_rate_limit_and_load_slo_guard(
            {
                "transport": "streamable-http",
                "load_connections": 2,
                "requests_total": 30000,
                "failed_calls": 1,
                "completed_calls": 29999,
                "max_error_rate": 0.0,
                "exit_code": 10,
                "threshold_error_code": "load_error_rate_exceeded",
                "summary_printed_before_exit": True,
            }
        )
        self.assertTrue(r5_ok.passed)
        r5_bad = evaluate_inspector_cli_rate_limit_and_load_slo_guard(
            {
                "transport": "streamable-http",
                "requests_total": 30000,
                "failed_calls": 1,
                "completed_calls": 29999,
                "max_error_rate": 0.0,
                "exit_code": 0,
            }
        )
        self.assertFalse(r5_bad.passed)

        # PR-06
        r6_ok = evaluate_inspector_ui_sort_bind_and_release_guard(
            {
                "connect_failed": True,
                "server_card_error_text": "HTTP 502 Bad Gateway",
                "tools": [
                    {"name": "tool_10", "title": "Tool 10"},
                    {"name": "tool_2", "title": "Tool 2"},
                ],
                "displayed_tool_names": ["tool_2", "tool_10"],
                "bind_host": "127.0.0.1",
            }
        )
        self.assertTrue(r6_ok.passed)
        r6_bad = evaluate_inspector_ui_sort_bind_and_release_guard(
            {
                "connect_failed": False,
                "tools": [
                    {"name": "tool_10", "title": "Tool 10"},
                    {"name": "tool_2", "title": "Tool 2"},
                ],
                "displayed_tool_names": ["tool_10", "tool_2"],
            }
        )
        self.assertFalse(r6_bad.passed)

        # PR-07
        r7_ok = evaluate_swift_data_url_header_and_byte_decode_guard(
            {
                "data_url": "data:text/plain;charset=iso-8859-7,%be%d3%be",
                "expected_bytes_hex": "bed3be",
            }
        )
        self.assertTrue(r7_ok.passed)
        r7_bad = evaluate_swift_data_url_header_and_byte_decode_guard(
            {
                "data_url": "data:text/plain,%fg",
                "expect_nil": False,
            }
        )
        self.assertFalse(r7_bad.passed)

        # PR-08
        r8_ok = evaluate_swift_transport_heartbeat_oauth_port_and_coder_guard(
            {
                "heartbeat_disconnect_and_reconnect_verified": True,
                "is_production_oauth": True,
                "uses_unbound_ephemeral_redirect_port": False,
                "server_caches_json_coders": True,
                "tool_schema_properties": {"city": {"type": "string"}},
            }
        )
        self.assertTrue(r8_ok.passed)
        r8_bad = evaluate_swift_transport_heartbeat_oauth_port_and_coder_guard(
            {
                "heartbeat_disconnect_and_reconnect_verified": False,
            }
        )
        self.assertFalse(r8_bad.passed)

    def test_pr09_to_pr16_ruby_php_and_kotlin_sdk_guards(self) -> None:
        # PR-09
        r9_ok = evaluate_ruby_listen_subscribe_handler_and_exception_reporter_guard(
            {
                "requested_uris": ["file:///secret.txt"],
                "handler_allowed_uris": [],
                "acknowledged_uris": None,
                "handler_received_meta_and_auth_info": True,
                "unsubscribe_called_on_stream_end": False,
            }
        )
        self.assertTrue(r9_ok.passed)
        r9_bad = evaluate_ruby_listen_subscribe_handler_and_exception_reporter_guard(
            {
                "requested_uris": ["file:///a.txt"],
                "handler_allowed_uris": ["file:///a.txt"],
                "acknowledged_uris": ["file:///a.txt"],
                "notification_failure_calls_private_report": True,
            }
        )
        self.assertFalse(r9_bad.passed)

        # PR-10
        r10_ok = evaluate_ruby_jsonrpc_null_id_and_string_id_guard(
            {
                "has_id_member": True,
                "request_id": "urn:uuid:call:42.1",
                "method_executed": True,
                "response_error_code": None,
            }
        )
        self.assertTrue(r10_ok.passed)
        r10_bad = evaluate_ruby_jsonrpc_null_id_and_string_id_guard(
            {
                "has_id_member": False,
                "is_custom_method": False,
                "method_executed": True,
            }
        )
        self.assertFalse(r10_bad.passed)

        # PR-11
        r11_ok = evaluate_ruby_initialize_sse_return_and_dns_rebinding_guard(
            {
                "initialize_sse_abortable_on_response": True,
                "session_id_captured_from_headers": True,
                "dns_rebinding_enabled": True,
                "allowed_hosts": ["mcp.example.com"],
                "request_host": "evil.example.com",
                "http_status": 403,
            }
        )
        self.assertTrue(r11_ok.passed)
        r11_bad = evaluate_ruby_initialize_sse_return_and_dns_rebinding_guard(
            {
                "initialize_sse_abortable_on_response": True,
                "session_id_captured_from_headers": True,
                "dns_rebinding_enabled": True,
                "allowed_hosts": ["mcp.example.com"],
                "request_host": "evil.example.com",
                "http_status": 200,
            }
        )
        self.assertFalse(r11_bad.passed)

        # PR-12
        r12_ok = evaluate_php_reconnect_transport_close_and_vanished_stream_guard(
            {
                "reconnected": True,
                "previous_transport_closed_before_replace": True,
                "now_epoch_s": 1000,
                "grace_period_s": 60,
                "pending_entries": [
                    {
                        "id": "r1",
                        "timeout_at_epoch_s": 900,
                        "stream_alive": False,
                        "forgotten_on_new_request": True,
                    }
                ],
            }
        )
        self.assertTrue(r12_ok.passed)
        r12_bad = evaluate_php_reconnect_transport_close_and_vanished_stream_guard(
            {
                "reconnected": True,
                "previous_transport_closed_before_replace": True,
                "now_epoch_s": 1000,
                "grace_period_s": 60,
                "pending_entries": [
                    {
                        "id": "r1",
                        "timeout_at_epoch_s": 900,
                        "stream_alive": False,
                        "forgotten_on_new_request": False,
                    }
                ],
            }
        )
        self.assertFalse(r12_bad.passed)

        # PR-13
        r13_ok = evaluate_php_gateway_progress_token_and_list_changed_guard(
            {
                "parallel_calls": [
                    {
                        "call_id": "c1",
                        "request_progress_token": "tok-1",
                        "emitted_progress_token": "tok-1",
                    }
                ],
                "initialize_announces_list_changed": False,
                "has_notification_bus": False,
                "registry_publishes_list_changes": True,
                "discover_announces_list_changed": False,
            }
        )
        self.assertTrue(r13_ok.passed)
        r13_bad = evaluate_php_gateway_progress_token_and_list_changed_guard(
            {
                "parallel_calls": [],
                "initialize_announces_list_changed": False,
                "has_notification_bus": False,
                "registry_publishes_list_changes": True,
                "discover_announces_list_changed": True,
            }
        )
        self.assertFalse(r13_bad.passed)

        # PR-14
        r14_ok = evaluate_php_structured_tool_output_and_session_gc_guard(
            {
                "structured_content": {"ok": True},
                "content_blocks": [],
                "auto_duplicated_json_text": False,
                "session_store_kind": "psr16",
            }
        )
        self.assertTrue(r14_ok.passed)
        r14_bad = evaluate_php_structured_tool_output_and_session_gc_guard(
            {
                "structured_content": {"ok": True},
                "content_blocks": [],
                "auto_duplicated_json_text": True,
                "session_store_kind": "psr16",
            }
        )
        self.assertFalse(r14_bad.passed)

        # PR-15
        r15_ok = evaluate_kotlin_flow_pagination_and_cursor_cycle_guard(
            {
                "flow_is_cold": True,
                "requests_sent_before_collect": 0,
                "in_flight_page_cancelled_on_take": True,
                "meta_forwarded_every_page": True,
                "starting_cursor": None,
                "page_next_cursors": ["c1", "c2", None],
                "threw_illegal_state_on_cycle": False,
            }
        )
        self.assertTrue(r15_ok.passed)
        r15_bad = evaluate_kotlin_flow_pagination_and_cursor_cycle_guard(
            {
                "flow_is_cold": False,
                "requests_sent_before_collect": 1,
            }
        )
        self.assertFalse(r15_bad.passed)

        # PR-16
        r16_ok = evaluate_kotlin_016_sse_deprecation_and_api_migration_guard(
            {
                "sdk_version": "0.16.0",
                "transport_symbol": "StreamableHttpServerTransport",
                "used_legacy_symbols": [],
            }
        )
        self.assertTrue(r16_ok.passed)
        r16_bad = evaluate_kotlin_016_sse_deprecation_and_api_migration_guard(
            {
                "sdk_version": "0.16.0",
                "transport_symbol": "StreamableHttpServerTransport",
                "used_legacy_symbols": ["Configuration.enableDnsRebindingProtection"],
            }
        )
        self.assertFalse(r16_bad.passed)


if __name__ == "__main__":
    unittest.main()
