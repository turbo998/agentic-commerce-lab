"""Unit tests for Stage 262 guards and Stage 263 7-Card 4:5 benchmark report."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.stripe_daemon_agentkit_guard_mcp_extauth_a2a_compat_bench import (
    build_benchmark_report,
    write_report_artifacts,
)
from lab.stripe_daemon_agentkit_guard_mcp_extauth_a2a_compat_guards import (
    evaluate_a2a_java_explicit_null_struct_and_js_migration_guard,
    evaluate_a2a_python_card_parse_version_and_jsonrpc_stderr_guard,
    evaluate_a2a_python_send_config_rest_error_and_followup_guard,
    evaluate_agentkit_agenda_guard_evidence_boundary,
    evaluate_agentkit_groundtruth_record_guard,
    evaluate_agentkit_sbor_benchmark_rate_guard,
    evaluate_mcp_go_extauth_resource_and_www_authenticate_guard,
    evaluate_mcp_inspector_cli_target_timeout_and_schema_form_guard,
    evaluate_mcp_kotlin_session_result_and_cancellation_guard,
    evaluate_mcp_rust_cache_hints_and_invalid_params_guard,
    evaluate_mcp_rust_structured_prm_error_and_stdio_pipes_guard,
    evaluate_mcp_ts_uri_exploded_path_and_ajv_format_guard,
    evaluate_stage262_cross_stack_synthesis_guard,
    evaluate_stripe_cli_daemon_auth_and_fixture_url_guard,
    evaluate_stripe_cli_multipart_and_plugin_reaper_guard,
    evaluate_stripe_sdk_webhook_error_fetch_and_wif_guard,
)


VALID_DAEMON_TOKEN = "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90"


class TestStripeDaemonAgentkitGuardMcpExtauthA2aCompat(unittest.TestCase):
    """Test suite for Stage 262–263 guards and benchmark runner."""

    def test_compliant_scenarios_pass_deterministically(self) -> None:
        ev01 = evaluate_stripe_cli_daemon_auth_and_fixture_url_guard(
            daemon_token=VALID_DAEMON_TOKEN,
            header_values=[VALID_DAEMON_TOKEN],
            auth_checked_before_telemetry=True,
            stderr_contains_token=False,
            api_key="rk_live_1",
            requested_livemode=True,
            fixture_api_base="https://files.stripe.com/v1",
        )
        self.assertTrue(ev01.passed)
        self.assertEqual(ev01.action, "Act automatically")

        ev02 = evaluate_stripe_cli_multipart_and_plugin_reaper_guard(
            request_media_type="multipart/form-data",
            param_format="binary",
            raw_flag_value="./receipt.pdf",
            effective_param_value="@./receipt.pdf",
            dispatched_method="MakeMultiPartRequestWithAdditionalParams",
            merged_additional_params=True,
            dry_run_is_v2=False,
            help_placeholder="<file-path>",
            sigint_sigterm_reaper_installed=True,
            reaps_peer_plugins_via_cleanup_all_clients=True,
        )
        self.assertTrue(ev02.passed)

        ev03 = evaluate_stripe_sdk_webhook_error_fetch_and_wif_guard(
            webhook_secret=" \t\r\n ",
            rejected_before_hmac=True,
            stripe_error_args_tuple_len=6,
            pickle_celery_roundtrip_ok=True,
            fetch_raw_response_has_status_code=True,
            fetch_status_code_value=200,
            workload_identity_package_name="@stripe/workload-identity",
            workload_identity_tag_prefix="wif-v",
        )
        self.assertTrue(ev03.passed)

        ev04 = evaluate_agentkit_agenda_guard_evidence_boundary(
            protocol_family="evm",
            recipient="0x2222222222222222222222222222222222222222",
            amount_usd=120.0,
            velocity_24h_usd=300.0,
            max_single_limit_usd=1000.0,
            daily_velocity_limit_usd=5000.0,
            calldata="0x",
            intent="Settle verified supplier invoice",
            remote_http_called_on_local_reject=False,
            allow_redirects=False,
            returned_is_safe=False,
            returned_decision="step_up_human_required",
            sanctions_aml_claimed_true=False,
            velocity_limits_claimed_true=False,
            history_verified_claimed_true=False,
        )
        self.assertTrue(ev04.passed)
        self.assertEqual(ev04.action, "Confirm")

        ev05 = evaluate_agentkit_sbor_benchmark_rate_guard(
            benchmark="SBOR-USD",
            side="borrow",
            offered_rate_pct=4.40,
            benchmark_rate_pct=4.15,
            fixing_age_hours=8.5,
            missing_benchmark_treated_as_zero=False,
            metadata_sanitized=True,
            stop_and_ask_human_returned=False,
        )
        self.assertTrue(ev05.passed)
        self.assertEqual(ev05.action, "Act automatically")

        ev06 = evaluate_agentkit_groundtruth_record_guard(
            address="So11111111111111111111111111111111111111112",
            explicit_chain=None,
            inferred_chain="solana",
            api_url_has_trailing_slash=False,
            creator_described_as_safe=False,
            unsettled_coin_described_as_clean=False,
            known_bad_null_treated_as_innocent=False,
            known_bad_flag=False,
            resolved_launches=12,
            binomial_p_value=0.42,
            http_status=200,
            http_402_x402_remedy_surfaced=True,
        )
        self.assertTrue(ev06.passed)

        ev07 = evaluate_mcp_go_extauth_resource_and_www_authenticate_guard(
            prm_resource="https://mcp.merchant.example/v1/mcp",
            endpoint_params_resource=["https://mcp.merchant.example/v1/mcp"],
            redirects_restricted=True,
            www_authenticate_header='Bearer realm="merchant",, error="insufficient_scope"',
            parsed_error_param="insufficient_scope",
            step_up_authorization_triggered=True,
        )
        self.assertTrue(ev07.passed)

        ev08 = evaluate_mcp_rust_cache_hints_and_invalid_params_guard(
            negotiated_protocol_version="2026-07-28",
            result_is_complete=True,
            ttl_ms=0,
            cache_scope="private",
            legacy_result_type_stripped=False,
            malformed_request_method="tools/call",
            returned_jsonrpc_error_code=-32602,
        )
        self.assertTrue(ev08.passed)

        ev09 = evaluate_mcp_rust_structured_prm_error_and_stdio_pipes_guard(
            prm_error_variant="ProtectedResourceMetadataInvalid",
            preserves_oauth_http_client_error_source=True,
            flattened_to_string_metadata_error=False,
            stdin_is_fifo=True,
            stdout_is_fifo=True,
            selected_transport_backend="unix_pipe_reactor",
            fd_duplicated_with_o_nonblock=True,
        )
        self.assertTrue(ev09.passed)

        ev10 = evaluate_mcp_ts_uri_exploded_path_and_ajv_format_guard(
            template_operator="/",
            exploded=True,
            uri_input="/files/src/index.ts",
            matched_segments=["src", "index.ts"],
            uri_length_validated=True,
            default_ajv_unknown_format_warning_suppressed=True,
            known_formats_still_validated=True,
            custom_ajv_logger_preserved=True,
        )
        self.assertTrue(ev10.passed)

        ev11 = evaluate_mcp_kotlin_session_result_and_cancellation_guard(
            uses_atomic_persistent_list_for_initialized=True,
            late_registered_on_initialized_ran_immediately=True,
            concurrent_registrations_preserved_count=6,
            expected_registrations_count=6,
            raw_result_captured_on_wire_decode=True,
            sse_replay_rewrites_id_in_raw_json_not_copy=True,
            deserializes_by_request_method_first=True,
            cancellation_exception_suppressed_from_on_error=True,
        )
        self.assertTrue(ev11.passed)

        ev12 = evaluate_mcp_inspector_cli_target_timeout_and_schema_form_guard(
            cli_option_precedes_stdio_target=True,
            stdio_target_preserved=True,
            unknown_server_flags_forwarded=True,
            client_surface="cli",
            timeout_remedy_text="pass a larger --connect-timeout <ms>",
            array_of_object_schema_rendered_as_rows=True,
        )
        self.assertTrue(ev12.passed)

        ev13 = evaluate_a2a_python_card_parse_version_and_jsonrpc_stderr_guard(
            decoded_agent_card_is_dict=True,
            compat_helper_raised_type_or_attr_error=False,
            normalized_to_agent_card_resolution_error=True,
            advertised_versions=["0.3.0", "1.0.0"],
            selected_interface_version="1.0.0",
            malformed_jsonrpc_printed_traceback_to_stderr=False,
        )
        self.assertTrue(ev13.passed)

        ev14 = evaluate_a2a_python_send_config_rest_error_and_followup_guard(
            v03_proto_send_config_history_length=0,
            mapped_send_config_history_length=None,
            rest_error_payload=["not", "a", "status"],
            rest_http_status=404,
            raised_attribute_error_on_non_status_body=False,
            mapped_to_http_status_fallback_error=True,
            existing_task_re_emitted_on_stream_followup=True,
            followup_message_to_save_preserved=True,
            spurious_duplicate_task_error_logged=False,
        )
        self.assertTrue(ev14.passed)

        ev15 = evaluate_a2a_java_explicit_null_struct_and_js_migration_guard(
            struct_contains_explicit_null=True,
            from_proto_value_returns_null_for_null_value=True,
            from_proto_struct_uses_hashmap_not_collectors_to_map=True,
            to_proto_maps_null_to_null_value=True,
            centralized_assert_is_null_or_empty_used=True,
            a2a_js_kysely_push_store_migration_applied=True,
            a2a_js_node_engine_major=22,
        )
        self.assertTrue(ev15.passed)

        ev16 = evaluate_stage262_cross_stack_synthesis_guard(
            stripe_eval=ev01,
            agentkit_eval=ev05,
            mcp_eval=ev08,
            a2a_eval=ev14,
        )
        self.assertTrue(ev16.passed)
        self.assertEqual(ev16.action, "Act automatically")

    def test_adversarial_scenarios_are_rejected(self) -> None:
        ev01 = evaluate_stripe_cli_daemon_auth_and_fixture_url_guard(
            daemon_token=VALID_DAEMON_TOKEN,
            header_values=["wrong-token"],
            auth_checked_before_telemetry=True,
            stderr_contains_token=False,
            api_key="rk_test_51Pxyz",
            requested_livemode=False,
            fixture_api_base="https://api.stripe.com/v1",
        )
        self.assertFalse(ev01.passed)
        self.assertEqual(ev01.reason_code, "STRIPE_DAEMON_UNAUTHENTICATED_RPC")

        ev04_tornado = evaluate_agentkit_agenda_guard_evidence_boundary(
            protocol_family="evm",
            recipient="0xD90E2F925DA726B50C4ED8D0FB90AD053324F31B",
            amount_usd=50.0,
            velocity_24h_usd=None,
            max_single_limit_usd=1000.0,
            daily_velocity_limit_usd=5000.0,
            calldata="0x",
            intent="Normal transfer",
            remote_http_called_on_local_reject=True,  # leaked HTTP on local reject!
            allow_redirects=False,
            returned_is_safe=False,
            returned_decision="reject",
            sanctions_aml_claimed_true=False,
            velocity_limits_claimed_true=False,
            history_verified_claimed_true=False,
        )
        self.assertFalse(ev04_tornado.passed)
        self.assertEqual(
            ev04_tornado.reason_code, "AGENDA_GUARD_LOCAL_REJECTION_BYPASSED_OR_LEAKED_HTTP"
        )

        ev05_stale = evaluate_agentkit_sbor_benchmark_rate_guard(
            benchmark="BTC-COLLATERAL-USDC",
            side="borrow",
            offered_rate_pct=5.2,
            benchmark_rate_pct=5.0,
            fixing_age_hours=51.4,
            missing_benchmark_treated_as_zero=False,
            metadata_sanitized=True,
            stop_and_ask_human_returned=False,
        )
        self.assertFalse(ev05_stale.passed)
        self.assertEqual(ev05_stale.reason_code, "SBOR_FIXING_STALE_OVER_48_HOURS")

        ev07_no_res = evaluate_mcp_go_extauth_resource_and_www_authenticate_guard(
            prm_resource="https://mcp.merchant.example/v1/mcp",
            endpoint_params_resource=[],
            redirects_restricted=True,
            www_authenticate_header='Bearer error="insufficient_scope"',
            parsed_error_param="insufficient_scope",
            step_up_authorization_triggered=True,
        )
        self.assertFalse(ev07_no_res.passed)
        self.assertEqual(
            ev07_no_res.reason_code,
            "MCP_GO_CLIENT_CREDENTIALS_MISSING_RFC8707_RESOURCE_OR_REDIRECT_GUARD",
        )

        ev08_bad_code = evaluate_mcp_rust_cache_hints_and_invalid_params_guard(
            negotiated_protocol_version="2026-07-28",
            result_is_complete=True,
            ttl_ms=0,
            cache_scope="private",
            legacy_result_type_stripped=False,
            malformed_request_method="tools/call",
            returned_jsonrpc_error_code=-32601,
        )
        self.assertFalse(ev08_bad_code.passed)
        self.assertEqual(
            ev08_bad_code.reason_code,
            "MCP_RUST_UNGATED_SPEC_METHOD_RETURNED_METHOD_NOT_FOUND",
        )

    def test_secondary_rejection_branches_across_all_guards(self) -> None:
        # PR-01 mode mismatch & weak token
        self.assertEqual(
            evaluate_stripe_cli_daemon_auth_and_fixture_url_guard(
                daemon_token="short",
                header_values=["short"],
                auth_checked_before_telemetry=True,
                stderr_contains_token=False,
                api_key="rk_test_1",
                requested_livemode=False,
                fixture_api_base="",
            ).reason_code,
            "STRIPE_DAEMON_WEAK_OR_MISSING_TOKEN",
        )
        self.assertEqual(
            evaluate_stripe_cli_daemon_auth_and_fixture_url_guard(
                daemon_token=VALID_DAEMON_TOKEN,
                header_values=[VALID_DAEMON_TOKEN],
                auth_checked_before_telemetry=True,
                stderr_contains_token=False,
                api_key="sk_test_123",
                requested_livemode=True,
                fixture_api_base="",
            ).reason_code,
            "STRIPE_API_KEY_MODE_MISMATCH",
        )

        # PR-02 binary flag sent as plain string & orphaned peer plugin
        self.assertEqual(
            evaluate_stripe_cli_multipart_and_plugin_reaper_guard(
                request_media_type="multipart/form-data",
                param_format="binary",
                raw_flag_value="./doc.pdf",
                effective_param_value="./doc.pdf",
                dispatched_method="MakeMultiPartRequestWithAdditionalParams",
                merged_additional_params=True,
                dry_run_is_v2=False,
                help_placeholder="<file-path>",
                sigint_sigterm_reaper_installed=True,
                reaps_peer_plugins_via_cleanup_all_clients=True,
            ).reason_code,
            "STRIPE_CLI_BINARY_FLAG_PATH_SENT_AS_PLAIN_STRING",
        )

        # PR-03 legacy workload identity package name
        self.assertEqual(
            evaluate_stripe_sdk_webhook_error_fetch_and_wif_guard(
                webhook_secret="whsec_valid",
                rejected_before_hmac=False,
                stripe_error_args_tuple_len=6,
                pickle_celery_roundtrip_ok=True,
                fetch_raw_response_has_status_code=True,
                fetch_status_code_value=200,
                workload_identity_package_name="@stripe/aws-workload-identity",
                workload_identity_tag_prefix="aws-wif-v",
            ).reason_code,
            "STRIPE_NODE_LEGACY_AWS_WORKLOAD_IDENTITY_NAME",
        )

        # PR-09 non-FIFO wrapped as unix pipe
        self.assertEqual(
            evaluate_mcp_rust_structured_prm_error_and_stdio_pipes_guard(
                prm_error_variant="None",
                preserves_oauth_http_client_error_source=True,
                flattened_to_string_metadata_error=False,
                stdin_is_fifo=False,
                stdout_is_fifo=True,
                selected_transport_backend="unix_pipe_reactor",
                fd_duplicated_with_o_nonblock=False,
            ).reason_code,
            "MCP_RUST_NON_FIFO_WRAPPED_AS_UNIX_PIPE",
        )

        # PR-10 exploded slash match failure
        self.assertEqual(
            evaluate_mcp_ts_uri_exploded_path_and_ajv_format_guard(
                template_operator="/",
                exploded=True,
                uri_input="/files/src/index.ts",
                matched_segments=["src/index.ts"],
                uri_length_validated=True,
                default_ajv_unknown_format_warning_suppressed=True,
                known_formats_still_validated=True,
                custom_ajv_logger_preserved=True,
            ).reason_code,
            "MCP_TS_EXPLODED_SLASH_PATH_MATCH_FAILED",
        )

        # PR-11 & PR-12 & PR-13 & PR-14 & PR-15 failure branches
        self.assertEqual(
            evaluate_mcp_kotlin_session_result_and_cancellation_guard(
                uses_atomic_persistent_list_for_initialized=True,
                late_registered_on_initialized_ran_immediately=True,
                concurrent_registrations_preserved_count=4,
                expected_registrations_count=4,
                raw_result_captured_on_wire_decode=True,
                sse_replay_rewrites_id_in_raw_json_not_copy=False,
                deserializes_by_request_method_first=True,
                cancellation_exception_suppressed_from_on_error=True,
            ).reason_code,
            "MCP_KOTLIN_SHAPE_POLYMORPHISM_CLASS_CAST_OR_COPY_DROPPED_RAW_RESULT",
        )
        self.assertEqual(
            evaluate_mcp_inspector_cli_target_timeout_and_schema_form_guard(
                cli_option_precedes_stdio_target=True,
                stdio_target_preserved=True,
                unknown_server_flags_forwarded=True,
                client_surface="cli",
                timeout_remedy_text="increase the timeout value in Server Settings.",
                array_of_object_schema_rendered_as_rows=True,
            ).reason_code,
            "MCP_INSPECTOR_WEB_SERVER_SETTINGS_REMEDY_SHOWN_IN_CLI",
        )
        self.assertEqual(
            evaluate_a2a_python_card_parse_version_and_jsonrpc_stderr_guard(
                decoded_agent_card_is_dict=True,
                compat_helper_raised_type_or_attr_error=False,
                normalized_to_agent_card_resolution_error=True,
                advertised_versions=["0.3.0", "1.0.0"],
                selected_interface_version="0.3.0",
                malformed_jsonrpc_printed_traceback_to_stderr=False,
            ).reason_code,
            "A2A_PYTHON_PATCH_VERSION_1_0_0_FELL_BACK_TO_0_3",
        )
        self.assertEqual(
            evaluate_a2a_python_send_config_rest_error_and_followup_guard(
                v03_proto_send_config_history_length=0,
                mapped_send_config_history_length=None,
                rest_error_payload={"error": {"message": "ok"}},
                rest_http_status=400,
                raised_attribute_error_on_non_status_body=False,
                mapped_to_http_status_fallback_error=True,
                existing_task_re_emitted_on_stream_followup=True,
                followup_message_to_save_preserved=False,
                spurious_duplicate_task_error_logged=True,
            ).reason_code,
            "A2A_PYTHON_STREAMING_FOLLOWUP_MESSAGE_DROPPED_ON_REEMITTED_TASK",
        )
        self.assertEqual(
            evaluate_a2a_java_explicit_null_struct_and_js_migration_guard(
                struct_contains_explicit_null=True,
                from_proto_value_returns_null_for_null_value=False,
                from_proto_struct_uses_hashmap_not_collectors_to_map=False,
                to_proto_maps_null_to_null_value=False,
                centralized_assert_is_null_or_empty_used=True,
                a2a_js_kysely_push_store_migration_applied=True,
                a2a_js_node_engine_major=22,
            ).reason_code,
            "A2A_JAVA_V03_EXPLICIT_JSON_NULL_THROW_OR_NPE",
        )

    def test_benchmark_report_and_bilingual_7card_html_generation(self) -> None:
        report = build_benchmark_report()
        self.assertEqual(report["stage"], 263)
        self.assertEqual(report["guard_stage"], 262)
        self.assertEqual(report["total_scenarios"], 16)
        self.assertEqual(report["ai_native_passed"], 16)
        self.assertEqual(report["classic_3tier_passed"], 2)

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            write_report_artifacts(out_dir)
            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            for html_doc in (zh_html, en_html):
                self.assertIn(
                    "Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'\"",
                    html_doc,
                )
                for idx in range(1, 8):
                    self.assertIn(f"{idx} / 7 ·", html_doc)


if __name__ == "__main__":
    unittest.main()
