"""Unit tests for Stages 248-249 MCP Ext-Apps, Conformance DPoP/Stateless, and Registry v1.8.4 guards."""

from __future__ import annotations

import unittest

from lab.mcp_ext_apps_conformance_dpop_registry_guards import (
    evaluate_conformance_empty_custom_header_presence_guard,
    evaluate_conformance_runner_session_sweep_stream_timer_guard,
    evaluate_conformance_sep1932_dpop_as_client_binding_guard,
    evaluate_conformance_sep1932_dpop_server_challenge_guard,
    evaluate_conformance_stateless_result_type_guard,
    evaluate_conformance_tasks_extension_request_state_guard,
    evaluate_ext_apps_cli_roots_refresh_provenance_guard,
    evaluate_ext_apps_cors_permissions_sandbox_guard,
    evaluate_ext_apps_get_current_pdf_dual_surface_guard,
    evaluate_ext_apps_postmessage_loglevel_privacy_guard,
    evaluate_ext_apps_register_app_tool_icons_guard,
    evaluate_ext_apps_resolve_qualified_tool_name_guard,
    evaluate_ext_apps_ui_initialize_handshake_guard,
    evaluate_registry_nested_server_json_and_remote_ownership_guard,
    evaluate_registry_prod_pgdump_restic_backup_guard,
    evaluate_registry_trigram_index_and_dpr_icon_guard,
)


class McpExtAppsConformanceDpopRegistryGuardsTest(unittest.TestCase):
    def test_ext_apps_guards_pr01_to_pr07(self) -> None:
        # PR-01 (#820): get_current_pdf dual surface & 64MB limit & hasInViewerEdits
        ok_pdf = evaluate_ext_apps_get_current_pdf_dual_surface_guard(
            surface="app_tool",
            json_limit_mb=64,
            payload_size_mb=1.9,
            resource_uri="file:///arXiv-2610.12345.pdf",
            mime_type="application/pdf",
            baseline_annotations={"a": 1},
            current_annotations={"a": 1},
            baseline_form_values={"f": "v"},
            current_form_values={"f": "v"},
            reported_edited=False,
        )
        self.assertTrue(ok_pdf["passed"])
        self.assertFalse(ok_pdf["has_in_viewer_edits"])

        bad_pdf = evaluate_ext_apps_get_current_pdf_dual_surface_guard(
            surface="interact",
            json_limit_mb=1,
            payload_size_mb=1.9,
            resource_uri="file:///bad name.pdf",
            mime_type="application/pdf",
            baseline_annotations={"a": 1},
            current_annotations={"a": 1},
            baseline_form_values={"f": "v"},
            current_form_values={"f": "v"},
            reported_edited=True,
            request_id_known=False,
        )
        self.assertFalse(bad_pdf["passed"])
        self.assertIn("json_limit_below_64mb:1", bad_pdf["reasons"])
        self.assertIn("unknown_interact_request_id", bad_pdf["reasons"])

        # PR-02 (#813): registerAppTool icons
        ok_icons = evaluate_ext_apps_register_app_tool_icons_guard(
            tool_config={
                "icons": [{"src": "https://example.com/light.svg", "theme": "light"}],
                "_meta": {"ui": {"resourceUri": "ui://app/index.html"}},
            },
            tools_list_entry={
                "icons": [{"src": "https://example.com/light.svg", "theme": "light"}],
            },
        )
        self.assertTrue(ok_icons["passed"])

        # PR-03 (#810): ui/initialize handshake
        ok_init = evaluate_ext_apps_ui_initialize_handshake_guard(
            method="ui/initialize",
            params={
                "appInfo": {"name": "My UI", "version": "1.0.0"},
                "appCapabilities": {"availableDisplayModes": ["inline"]},
                "protocolVersion": "2026-01-26",
            },
            sent_initialized_notification=True,
            notification_method="ui/notifications/initialized",
            host_sent_tool_input_before_initialized=False,
        )
        self.assertTrue(ok_init["passed"])

        bad_init = evaluate_ext_apps_ui_initialize_handshake_guard(
            method="initialize",
            params={"clientInfo": {"name": "My UI", "version": "1.0.0"}, "capabilities": {}},
            sent_initialized_notification=False,
            notification_method="",
            host_sent_tool_input_before_initialized=True,
        )
        self.assertFalse(bad_init["passed"])

        # PR-04 (#808/#803): PostMessageTransport logLevel privacy
        ok_log = evaluate_ext_apps_postmessage_loglevel_privacy_guard(
            configured_log_level=None,
            message_type="outgoing_rpc",
            emitted_console_debug=False,
            emitted_console_error=False,
            fired_onerror_callback=False,
        )
        self.assertTrue(ok_log["passed"])
        self.assertEqual(ok_log["effective_log_level"], "warning")

        bad_log = evaluate_ext_apps_postmessage_loglevel_privacy_guard(
            configured_log_level="debug",
            message_type="tool-input-partial",
            emitted_console_debug=True,
            emitted_console_error=False,
            fired_onerror_callback=False,
        )
        self.assertFalse(bad_log["passed"])

        # PR-05 (#807): resolveToolName
        ok_res = evaluate_ext_apps_resolve_qualified_tool_name_guard(
            entry_bare_tool_name="show-clock",
            host_context_tool_name="pdf-server-show-clock",
            target_bare_tool_name="get-time",
            dispatched_tool_name="pdf-server-get-time",
        )
        self.assertTrue(ok_res["passed"])

        # PR-06 (#805): CLI roots provenance
        ok_roots = evaluate_ext_apps_cli_roots_refresh_provenance_guard(
            cli_local_dirs=["/cli/pdfs"],
            previous_client_roots=["/client/a"],
            refreshed_client_roots=[],
            resulting_allowed_local_dirs=["/cli/pdfs"],
        )
        self.assertTrue(ok_roots["passed"])

        # PR-07 (#801/#799/#795): CORS, open UI permissions, Cesium sandbox
        ok_cors = evaluate_ext_apps_cors_permissions_sandbox_guard(
            cors_allow_headers=[
                "Content-Type",
                "Accept",
                "Mcp-Session-Id",
                "Mcp-Protocol-Version",
                "Mcp-Method",
                "Mcp-Name",
            ],
            requested_permissions={"fullscreen": True, "clipboardWrite": True},
            rendered_allow_attribute=["fullscreen", "clipboard-write"],
            sandbox_synchronous_task_processor=True,
            knockout_unsafe_eval_disabled=True,
            fallback_on_undefined_coordinates=True,
        )
        self.assertTrue(ok_cors["passed"])

    def test_conformance_and_registry_guards_pr08_to_pr16(self) -> None:
        # PR-08 (#563): stateless resultType
        ok_stateless = evaluate_conformance_stateless_result_type_guard(
            protocol_version="2026-07-28",
            tool_name="test_logging_tool",
            log_level_meta_present=False,
            emitted_log_notification=False,
            emitted_progress_notification=False,
            result_payload={"resultType": "complete", "content": [{"type": "text", "text": "ok"}]},
        )
        self.assertTrue(ok_stateless["passed"])

        # PR-09 (#560): empty custom header presence
        ok_hdr = evaluate_conformance_empty_custom_header_presence_guard(
            has_optional_annotated_string_fixture=True,
            argument_state="empty_string",
            header_state="absent",
            http_status=400,
            jsonrpc_error_code=-32020,
            tool_invoked=False,
        )
        self.assertTrue(ok_hdr["passed"])

        untestable_hdr = evaluate_conformance_empty_custom_header_presence_guard(
            has_optional_annotated_string_fixture=False,
            argument_state="omitted",
            header_state="present_empty",
            http_status=400,
            jsonrpc_error_code=-32020,
            tool_invoked=False,
        )
        self.assertFalse(untestable_hdr["passed"])

        # PR-10 (#545/#534): Tasks extension & state-ok
        ok_tasks = evaluate_conformance_tasks_extension_request_state_guard(
            advertises_tasks_extension=True,
            supported_task_methods=["tasks/get", "tasks/update", "tasks/cancel"],
            has_execution_task_support_meta=True,
            tasks_status_notifications_pending=True,
            round2_is_error=False,
            round2_text_blocks=["state-ok"],
        )
        self.assertTrue(ok_tasks["passed"])

        # PR-11 (#533/#532): Runner session sweep & post-header timer
        ok_runner = evaluate_conformance_runner_session_sweep_stream_timer_guard(
            scenario_outcome="timeout_closed_late_connection",
            connection_resolved_after_timeout=True,
            delete_requests_sent=1,
            leaked_live_sessions=0,
            header_latency_ms=1000,
            header_timeout_ms=10000,
            post_header_frame_arrival_ms=300,
            collection_window_ms=500,
            timer_reset_after_headers=True,
        )
        self.assertTrue(ok_runner["passed"])

        # PR-12 (#528/#527): SEP-1932 DPoP server error codes & Bearer downgrade
        ok_dpop_srv = evaluate_conformance_sep1932_dpop_server_challenge_guard(
            defect_kind="proof_defect",
            http_status=401,
            www_authenticate_schemes=["DPoP"],
            dpop_error_code="invalid_dpop_proof",
        )
        self.assertTrue(ok_dpop_srv["passed"])

        # PR-13 (#525/#524/#523): SEP-1932 AS negative probes, refresh binding & dpop_jkt
        ok_dpop_as = evaluate_conformance_sep1932_dpop_as_client_binding_guard(
            as_invalid_proof_status=400,
            as_invalid_proof_error="invalid_dpop_proof",
            nonce_challenged=True,
            dpop_nonce_header_present=True,
            mismatched_nonce_rejected_4xx=True,
            refresh_token_used=True,
            refresh_proof_matches_original_key=True,
            prior_failed_refresh_sticky=True,
            auth_code_dpop_jkt="jkt_1",
            token_exchange_proof_jkt="jkt_1",
        )
        self.assertTrue(ok_dpop_as["passed"])

        # PR-14 (#1730/#1728): Registry trigram index & DPR icon scoring
        ok_trgm = evaluate_registry_trigram_index_and_dpr_icon_guard(
            trigram_index_exists=True,
            index_is_valid=True,
            index_is_ready=True,
            device_pixel_ratio=2.0,
            candidate_icons=[
                {"src": "https://example.com/48.png", "sizes": "48x48"},
                {"src": "https://example.com/vector.svg", "sizes": ""},
            ],
            selected_icon_src="https://example.com/vector.svg",
        )
        self.assertTrue(ok_trgm["passed"])

        # PR-15 (#1727/#1726): Prod pg_dump/Restic backup & K8up retirement
        ok_bkp = evaluate_registry_prod_pgdump_restic_backup_guard(
            environment="prod",
            retired_k8up_schedule_removed=True,
            backup_cronjob_enabled=True,
            pg_dump_compress_level=0,
            sha256_and_restic_check_passed=True,
            retention_days=28,
            gcs_prefix="postgres-custom-v1/",
            grafana_initial_admin_secret_created=False,
        )
        self.assertTrue(ok_bkp["passed"])

        # PR-16 (#1702/#1690/#1687): Nested server.json & remote ownership
        ok_pub = evaluate_registry_nested_server_json_and_remote_ownership_guard(
            changed_files=["io.quickbrew/mcp-server/server.json"],
            trusted_contributor=False,
            auto_closed_as_invalid_publish_pr=True,
            is_remote_only_server=True,
            has_packages_field=False,
            has_remotes_field=True,
            duplicate_remote_url_detected=False,
            search_query_active=False,
            page_number=1,
            recently_updated_visible=True,
            recently_updated_collapsed_count=6,
        )
        self.assertTrue(ok_pub["passed"])


if __name__ == "__main__":
    unittest.main()
