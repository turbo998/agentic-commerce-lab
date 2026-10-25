"""Unit tests for Stage 272–273 guards and 16-scenario 7-Card benchmark suite (`PR-01..PR-16`)."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.x402_authority_ucp_a2a_rest_stripe_v2_search_agentkit_mcp_skills_bench import (
    run_benchmark_scenarios,
    write_benchmark_report,
)
from lab.x402_authority_ucp_a2a_rest_stripe_v2_search_agentkit_mcp_skills_guards import (
    SEI_MAINNET_USDC_ADDRESS,
    evaluate_a2a_dotnet_proactive_continuation_duplicate_json_keys_and_stream_ct_guard,
    evaluate_a2a_go_rest_query_service_params_nil_typed_and_pre_stream_error_guard,
    evaluate_a2a_js_grpc_ext_subms_timestamp_and_java_rest_sse_close_guard,
    evaluate_a2a_python_task_updater_recovery_v03_none_signing_and_httpx_isolation_guard,
    evaluate_agentkit_x402receipts_cdp_idempotency_assetfare_and_rsoft_lending_guard,
    evaluate_mcp_go_task_support_and_rust_duplicate_sep2243_legacy_discover_guard,
    evaluate_mcp_inspector_skill_reread_budget_remedy_quiet_output_and_epipe_guard,
    evaluate_mcp_python_skills_percent_traversal_oauth_rfc_and_linear_stdio_guard,
    evaluate_mcp_ts_live_resource_title_405_allow_lazy_validator_and_csharp_aot_guard,
    evaluate_stripe_agent_toolkit_config_warning_empty_choices_and_402_lanes_guard,
    evaluate_stripe_openapi_mock_pin_positional_args_and_cli_plugin_version_guard,
    evaluate_stripe_v2_search_post_pagination_async_notif_and_fetch_dispose_guard,
    evaluate_ucp_nested_extensions_fragment_links_failfast_and_line_item_note_guard,
    evaluate_x402_authority_mandate_payment_id_binding_and_siwx_origin_guard,
    evaluate_x402_bazaar_fixed_point_decode_settlement_pending_and_hedera_guard,
    evaluate_x402_facilitator_gas_limit_family_scoping_sei_and_auth_capture_guard,
)


class Stage272To273GuardAndBenchmarkTests(unittest.TestCase):
    def test_pr01_to_pr04_x402_and_ucp_guards(self) -> None:
        # PR-01
        bad_pr01 = evaluate_x402_authority_mandate_payment_id_binding_and_siwx_origin_guard(
            authority_mandate_signed=True,
            mandate_delegate="agent:buyer-01",
            caller_identity="agent:buyer-01",
            requested_amount=500,
            mandate_max_amount=1_000,
            payment_identifier="pay_id_99",
            cached_request_fingerprint="POST:/v1/order:sha256_item_A",
            current_request_fingerprint="POST:/v1/order:sha256_item_B",
            in_flight_locked=False,
            siwx_challenge_origin="https://evil.example.com",
            request_origin="https://api.merchant.example",
        )
        self.assertFalse(bad_pr01.passed)
        ok_pr01 = evaluate_x402_authority_mandate_payment_id_binding_and_siwx_origin_guard(
            authority_mandate_signed=True,
            mandate_delegate="agent:buyer-01",
            caller_identity="agent:buyer-01",
            requested_amount=500,
            mandate_max_amount=1_000,
            payment_identifier="pay_id_99",
            cached_request_fingerprint="POST:/v1/order:sha256_item_A",
            current_request_fingerprint="POST:/v1/order:sha256_item_A",
            in_flight_locked=False,
            siwx_challenge_origin="https://api.merchant.example",
            request_origin="https://api.merchant.example",
        )
        self.assertTrue(ok_pr01.passed)
        self.assertEqual(ok_pr01.details["remaining_mandate_budget"], 500)

        # PR-02
        bad_pr02 = evaluate_x402_bazaar_fixed_point_decode_settlement_pending_and_hedera_guard(
            route_template="/api/v1/%252e%252e/admin",
            use_fixed_point_decode=True,
            broadcast_tx_hash="0xabc123",
            confirmation_timed_out=True,
            enable_settlement_pending_recovery=False,
            hedera_transfer_method="transferExecutor",
            hedera_executor_allowance_verified=False,
        )
        self.assertFalse(bad_pr02.passed)
        ok_pr02 = evaluate_x402_bazaar_fixed_point_decode_settlement_pending_and_hedera_guard(
            route_template="/api/v1/items/:itemId",
            use_fixed_point_decode=True,
            broadcast_tx_hash="0xabc123",
            confirmation_timed_out=True,
            enable_settlement_pending_recovery=True,
            hedera_transfer_method="transferExecutor",
            hedera_executor_allowance_verified=True,
        )
        self.assertTrue(ok_pr02.passed)
        self.assertEqual(ok_pr02.details["settlement_state"], "settlement_pending")

        # PR-03
        ok_pr03 = evaluate_x402_facilitator_gas_limit_family_scoping_sei_and_auth_capture_guard(
            configured_gas_limit=600_000,
            required_settlement_gas=450_000,
            selected_families=["evm"],
            derive_unselected_family_signers=False,
            sei_chain_id="eip155:1329",
            sei_usdc_address=SEI_MAINNET_USDC_ADDRESS,
            auth_capture_max_authorized=1_000,
            auth_capture_capture_amount=750,
        )
        self.assertTrue(ok_pr03.passed)
        self.assertEqual(ok_pr03.details["auth_capture_released_hold"], 250)

        # PR-04
        ok_pr04 = evaluate_ucp_nested_extensions_fragment_links_failfast_and_line_item_note_guard(
            extension_doc_path="docs/specification/shopping/extensions/discount.md",
            rewritten_overview_link="/specification/overview/#capabilities",
            expected_fragment="capabilities",
            ucp_schema_binary_present=True,
            mask_missing_binary_in_sed_pipe=False,
            llmstxt_sections=[
                "specification/overview/index.md",
                "specification/split-payments.md",
                "specification/glossary.md",
            ],
            line_item_note="No onions",
            reference_renders_catalog_envelope=True,
        )
        self.assertTrue(ok_pr04.passed)

    def test_pr05_to_pr08_a2a_polyglot_guards(self) -> None:
        # PR-05
        ok_pr05 = evaluate_a2a_python_task_updater_recovery_v03_none_signing_and_httpx_isolation_guard(
            set_terminal_flag_before_event_validation=False,
            status_event_valid=False,
            v03_proto_has_status_message=False,
            v03_unset_mapped_to_none=True,
            preserve_agent_card_defaults_for_jcs_signing=True,
            share_default_httpx_across_clients=False,
            lazy_create_cluster_tables_on_get_delete=True,
        )
        self.assertTrue(ok_pr05.passed)
        self.assertIsNone(ok_pr05.details["v03_unset_status_message"])

        # PR-06
        ok_pr06 = evaluate_a2a_go_rest_query_service_params_nil_typed_and_pre_stream_error_guard(
            endpoint_url="https://agent.example.com/a2a?api_key=secret_token",
            operation_query={"historyLength": "5"},
            preserve_endpoint_query=True,
            service_param_keys=["A2A-Version", "Authorization"],
            normalize_service_param_keys_lowercase=True,
            typed_error_value_is_nil=True,
            guard_nil_map_in_typed_marshal=True,
            gateway_http_status=401,
            map_non_a2a_http_error_by_status=True,
            request_content_type="application/a2a+json",
            accept_header="*/*",
            pre_first_event_stream_error=True,
            send_200_sse_headers_before_first_event=False,
        )
        self.assertTrue(ok_pr06.passed)
        self.assertIn("api_key=secret_token", ok_pr06.details["final_url"])
        self.assertEqual(ok_pr06.details["response_content_type"], "application/a2a+json")

        # PR-07
        ok_pr07 = evaluate_a2a_js_grpc_ext_subms_timestamp_and_java_rest_sse_close_guard(
            defer_grpc_metadata_until_first_event=True,
            unwrap_typed_a2a_error_from_sse=True,
            task_timestamp_iso="2026-10-02T00:00:00.000900Z",
            filter_boundary_iso="2026-10-02T00:00:00.000500Z",
            preserve_sub_millisecond_precision=True,
            skip_unknown_stream_payload_kind=True,
            java_signal_normal_rest_sse_completion=True,
            java_cancel_inflight_futures_on_close=True,
        )
        self.assertTrue(ok_pr07.passed)
        self.assertTrue(ok_pr07.details["sub_millisecond_match"])

        # PR-08
        ok_pr08 = evaluate_a2a_dotnet_proactive_continuation_duplicate_json_keys_and_stream_ct_guard(
            raw_json_has_duplicate_keys=True,
            reject_duplicate_json_keys_on_ingress=True,
            streaming_response_content_type="text/event-stream",
            raise_on_non_event_stream_response=True,
            proactive_continue_without_synthetic_message=True,
            consolidated_context_handler=True,
            requested_extensions=["urn:a2a:ext:payments:v1"],
            registered_extensions=["urn:a2a:ext:payments:v1"],
        )
        self.assertTrue(ok_pr08.passed)
        self.assertEqual(ok_pr08.details["negotiated_extensions"], ["urn:a2a:ext:payments:v1"])

    def test_pr09_to_pr16_stripe_agentkit_and_mcp_polyglot_guards(self) -> None:
        # PR-09
        ok_pr09 = evaluate_stripe_v2_search_post_pagination_async_notif_and_fetch_dispose_guard(
            v2_search_pagination_method="POST",
            replay_original_json_body_on_next_page=True,
            cjs_exports_v2_search_and_list_types=True,
            await_async_crypto_signature_verification=True,
            dispose_unread_fetch_body_on_retry=True,
        )
        self.assertTrue(ok_pr09.passed)

        # PR-10
        ok_pr10 = evaluate_stripe_openapi_mock_pin_positional_args_and_cli_plugin_version_guard(
            sdk_openapi_version="2026-09-30.acacia",
            stripe_mock_version="2026-09-30.acacia",
            leading_path_arg_passed_by_keyword=False,
            enforce_positional_only_path_args=True,
            cli_version_sent_in_plugin_additional_info=True,
            install_ps1_honors_pinned_version=True,
            cli_telemetry_distinguishes_http_status=True,
        )
        self.assertTrue(ok_pr10.passed)

        # PR-11
        ok_pr11 = evaluate_stripe_agent_toolkit_config_warning_empty_choices_and_402_lanes_guard(
            config_keys=["context", "actions"],
            warn_on_ignored_config_keys=True,
            llm_response_choices_count=0,
            raise_no_content_generated_error_on_empty_choices=True,
            portable_agent_plugins_v1_synced=True,
            claude_lifecycle_feedback_hooks_enabled=True,
            micro_wallet_lane_index=42,
        )
        self.assertTrue(ok_pr11.passed)

        # PR-12
        ok_pr12 = evaluate_agentkit_x402receipts_cdp_idempotency_assetfare_and_rsoft_lending_guard(
            settled_payment_hash="0xsettled_hash_01",
            recorded_receipt_payment_hash="0xsettled_hash_01",
            cdp_tx_idempotency_key=None,
            auto_generate_uuid_when_idempotency_omitted=True,
            assetfare_action_mode="read_only",
            rsoft_usdc_health_factor_bps=14_500,
            solana_python_version="0.36.6",
        )
        self.assertTrue(ok_pr12.passed)
        self.assertTrue(ok_pr12.details["cdp_idempotency_key"])

        # PR-13
        ok_pr13 = evaluate_mcp_go_task_support_and_rust_duplicate_sep2243_legacy_discover_guard(
            go_proxy_preserves_tool_execution_task_support=True,
            tool_task_support="required",
            sep2243_header_values_count=2,
            reject_duplicate_sep2243_headers=True,
            server_is_legacy_only=True,
            reject_discover_on_legacy_only_server=True,
            cancel_inflight_work_on_http_transport_close=True,
            structured_auth_metadata_discovery_error=True,
        )
        self.assertTrue(ok_pr13.passed)

        # PR-14
        bad_pr14 = evaluate_mcp_python_skills_percent_traversal_oauth_rfc_and_linear_stdio_guard(
            skill_resource_uri="skill://payments/%2e%2e/secrets.env",
            unquote_percent_encoded_segments_before_check=True,
            oauth_client_authorized_for_grant=False,
            oauth_error_code="unauthorized_client",
            stdio_use_chunk_list_join_on_newline=True,
            bare_collection_return_generates_output_schema=True,
            atomic_session_group_refresh=True,
        )
        self.assertFalse(bad_pr14.passed)
        ok_pr14 = evaluate_mcp_python_skills_percent_traversal_oauth_rfc_and_linear_stdio_guard(
            skill_resource_uri="skill://payments/docs/SKILL.md",
            unquote_percent_encoded_segments_before_check=True,
            oauth_client_authorized_for_grant=False,
            oauth_error_code="unauthorized_client",
            stdio_use_chunk_list_join_on_newline=True,
            bare_collection_return_generates_output_schema=True,
            atomic_session_group_refresh=True,
        )
        self.assertTrue(ok_pr14.passed)

        # PR-15
        ok_pr15 = evaluate_mcp_ts_live_resource_title_405_allow_lazy_validator_and_csharp_aot_guard(
            initial_resource_title="Draft Invoice",
            updated_resource_title="Finalized Invoice #402",
            list_response_uses_live_title=True,
            stateless_405_allow_header="POST",
            compile_validators_lazily_per_called_tool=True,
            total_catalog_tools=128,
            csharp_endpoint_require_authorization_enforced=True,
            csharp_aot_list_object_metadata_registered=True,
        )
        self.assertTrue(ok_pr15.passed)
        self.assertEqual(ok_pr15.details["compiled_validators"], 1)

        # PR-16
        ok_pr16 = evaluate_mcp_inspector_skill_reread_budget_remedy_quiet_output_and_epipe_guard(
            reread_skill_file_on_explicit_skills_get=True,
            client_surface="cli",
            remedy_message="Pass --max-skill-bytes or --max-skill-count to the CLI",
            quiet_flag_enabled=True,
            output_file_specified=True,
            stderr_wrote_bytes_emitted=False,
            completion_reader_closed_early=True,
            handle_stdout_epipe_quietly=True,
            tui_header_height_rows=2,
            capability_counts_displayed=True,
        )
        self.assertTrue(ok_pr16.passed)

    def test_stage_273_benchmark_suite_and_7_card_report_generation(self) -> None:
        scenarios = run_benchmark_scenarios()
        self.assertEqual(len(scenarios), 16)
        self.assertTrue(all(not s.unpatched_passed for s in scenarios))
        self.assertTrue(all(s.patched_passed for s in scenarios))

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage273_report"
            payload = write_benchmark_report(out_dir)
            self.assertEqual(payload["scenario_count"], 16)
            self.assertEqual(payload["upstream_pr_count"], 86)
            self.assertEqual(payload["unpatched_interception_rate_pct"], 100.0)
            self.assertEqual(payload["patched_pass_rate_pct"], 100.0)
            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            for idx in range(1, 8):
                self.assertIn(f'id="card-{idx}"', zh_html)
                self.assertIn(f'id="card-{idx}"', en_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)


if __name__ == "__main__":
    unittest.main()
