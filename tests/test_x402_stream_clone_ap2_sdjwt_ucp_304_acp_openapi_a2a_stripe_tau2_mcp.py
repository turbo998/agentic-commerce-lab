"""Unit tests for Stage 280–281 deterministic guards and 16-scenario 7-Card 4:5 bilingual benchmark."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.x402_stream_clone_ap2_sdjwt_ucp_304_acp_openapi_a2a_stripe_tau2_mcp_bench import (
    build_stage281_summary,
    write_stage281_artifacts,
)
from lab.x402_stream_clone_ap2_sdjwt_ucp_304_acp_openapi_a2a_stripe_tau2_mcp_guards import (
    STAGE280_PR_GROUPS,
    evaluate_a2a_multilang_streaming_and_tenant_routing_guard,
    evaluate_a2a_python_push_isolation_and_active_task_guard,
    evaluate_acp_openapi_examples_and_minor_unit_refund_guard,
    evaluate_ap2_sdjwt_delegation_and_visa_tap_pqc_guard,
    evaluate_mcp_conformance_sep2243_dpop_and_inspector_scripts_guard,
    evaluate_mcp_csharp_java_kotlin_id_jag_and_rfc3986_guard,
    evaluate_mcp_go_rust_preinit_and_stateless_2026_07_28_guard,
    evaluate_mcp_ruby_php_auth_redaction_and_elicitation_isolation_guard,
    evaluate_mcp_swift_pkce_modulo_and_stateless_id_collision_guard,
    evaluate_mcp_ts_py_uri_fragment_and_dpop_guard,
    evaluate_stripe_tulip_gate_and_sdk_account_scoping_guard,
    evaluate_tau2_knowledge_sandbox_and_evaluator_matching_guard,
    evaluate_ucp_304_profile_escalation_and_deferred_payment_guard,
    evaluate_ucp_conformance_and_samples_order_envelope_guard,
    evaluate_ucp_python_sdk_unique_items_and_contains_guard,
    evaluate_x402_stream_clone_and_agentkit_cdp_idempotency_guard,
)


class TestStage280And281GuardsAndBench(unittest.TestCase):
    def test_pr_groups_completeness_and_zero_internal_duplicates(self) -> None:
        self.assertEqual(len(STAGE280_PR_GROUPS), 16)
        all_prs = [pr for prs in STAGE280_PR_GROUPS.values() for pr in prs]
        self.assertEqual(len(all_prs), 293)
        self.assertEqual(len(set(all_prs)), 293)
        repos = {pr.split("#")[0] for pr in all_prs}
        self.assertEqual(len(repos), 40)

    def test_commerce_and_payment_guards_pr01_to_pr06(self) -> None:
        # PR-01
        res01_fail = evaluate_x402_stream_clone_and_agentkit_cdp_idempotency_guard(
            request_is_stream=True,
            request_cloned_before_402_retry=False,
            unparseable_accepts_skipped=True,
            valid_accepts_remaining=1,
            signer_address="0x71C7656EC7ab88b098defB751B7401B5f6d8976F",
            cdp_value_moving=True,
            cdp_idempotency_key="idem-1",
            evm_expected_address="0x71C7656EC7ab88b098defB751B7401B5f6d8976F",
            evm_actual_address="0x71c7656ec7ab88b098defb751b7401b5f6d8976f",
            quote_amount_minor=100,
            auto_pay_limit_minor=500,
            quote_settlement_identity_bound=True,
            preflight_passed=True,
        )
        self.assertFalse(res01_fail.passed)
        self.assertEqual(res01_fail.reason_code, "X402_STREAMED_REQUEST_NOT_CLONED_BEFORE_RETRY")

        # PR-02
        res02_fail = evaluate_ap2_sdjwt_delegation_and_visa_tap_pqc_guard(
            has_reference_in_store_cb_callable=True,
            cnf_jwk_dumped_in_json_mode=True,
            execution_date_iso="2026-10-26T04:00:00Z",
            window_start_iso="2026-10-26T00:00:00Z",
            window_end_iso="2026-10-27T00:00:00Z",
            currency="JPY",
            budget_max_major=1000.0,
            budget_max_minor=1000,
            requested_minor=500,
            terminal_kb_aud_present=True,
            terminal_kb_nonce_present=True,
            closed_checkout_binding_verified=True,
            mandate_already_consumed=True,
            rail_confirmation_verified=True,
            tap_did_key_resolved=True,
            tap_hybrid_alg="Ed25519+ML-DSA-65",
            tap_mtls_authorized=True,
        )
        self.assertFalse(res02_fail.passed)
        self.assertEqual(res02_fail.reason_code, "AP2_SDJWT_TERMINAL_HOP_OR_ATOMIC_MANDATE_FAILURE")

        # PR-03, PR-04, PR-05, PR-06
        res03_fail = evaluate_ucp_304_profile_escalation_and_deferred_payment_guard(
            profile_http_status=304,
            has_cached_profile=True,
            treated_304_as_redirect_error=False,
            checkout_status="requires_escalation",
            continue_url="",
            is_complete_checkout_request=True,
            has_cart_id_field=False,
            payment_terms_deferred=True,
            payment_object={},
            ap2_mandate_verified_by_cp=True,
            content_digest_matches=True,
        )
        self.assertFalse(res03_fail.passed)
        self.assertEqual(res03_fail.reason_code, "UCP_REQUIRES_ESCALATION_MISSING_CONTINUE_URL")

        res04_ok = evaluate_ucp_python_sdk_unique_items_and_contains_guard(
            array_items=["a", "b"],
            unique_items_required=True,
            validator_scoped_to_declaring_class=True,
            required_contains_token="a",
            min_contains=1,
            max_contains=1,
            object_properties_count=2,
            min_properties=1,
            catalog_included_in_ucp_metadata_union=True,
            transition_ucp_request_handled=True,
        )
        self.assertTrue(res04_ok.passed)

        res05_fail = evaluate_ucp_conformance_and_samples_order_envelope_guard(
            line_item_quantities=[1, -1],
            order_response_has_null_padded_optionals=False,
            missing_order_returns_ucp_envelope=True,
            invalid_input_routed_via_discovered_endpoint=True,
            checkout_creation_status_code=200,
            in_band_payment_and_fulfillment_errors_accepted=True,
            webhook_uses_checkout_line_item_ids=True,
        )
        self.assertFalse(res05_fail.passed)

        res06_fail = evaluate_acp_openapi_examples_and_minor_unit_refund_guard(
            openapi_inline_examples_match_ref_schemas=True,
            delegate_payment_error_envelope_unwrapped=True,
            refund_amount_value=True,
            checkout_line_items_match_schema=True,
            session_context_telemetry_present=True,
            upsert_products_response_in_feed_bundle=True,
        )
        self.assertFalse(res06_fail.passed)

    def test_a2a_stripe_tau2_and_mcp_guards_pr07_to_pr16(self) -> None:
        res07_fail = evaluate_a2a_python_push_isolation_and_active_task_guard(
            push_notification_failed=False,
            task_lifecycle_aborted_by_push_failure=False,
            direct_message_response_completed=True,
            active_task_released=False,
            followup_message_preserved_on_reemit=True,
            malformed_jsonrpc_printed_traceback_to_stderr=False,
            non_status_rest_error_handled=True,
            terminal_error_names_task_state=True,
            sender_attribution_valid=True,
        )
        self.assertFalse(res07_fail.passed)
        self.assertEqual(res07_fail.reason_code, "A2A_PYTHON_ACTIVE_TASK_LEAKED_AFTER_DIRECT_MESSAGE")

        res08_fail = evaluate_a2a_multilang_streaming_and_tenant_routing_guard(
            js_jsonrpc_error_http_status=200,
            js_media_type_matches_default_input_modes=True,
            js_unapplied_migration_downgrade_refused=True,
            go_streaming_json_error_surfaced=True,
            go_page_token_preserves_task_id_underscore=True,
            java_failed_terminal_enqueue_recovered=True,
            java_multitenant_card_resolved_via_router=True,
            dotnet_loopback_push_destination_opt_in=False,
            dotnet_is_loopback_push=True,
        )
        self.assertFalse(res08_fail.passed)
        self.assertEqual(res08_fail.reason_code, "A2A_DOTNET_LOOPBACK_PUSH_WITHOUT_OPT_IN")

        res09_fail = evaluate_stripe_tulip_gate_and_sdk_account_scoping_guard(
            tulip_admission_gate_passed=False,
            model_id="claude-3.5-sonnet",
            resolved_max_tokens=8192,
            cli_plugin_is_known=True,
            cli_auto_install_allowed=True,
            event_handler_account_scoped_across_py_java_php=True,
            php_malformed_webhook_sig_items_handled=True,
            go_normalized_path_param_valid=True,
            python_service_path_params_positional_only=True,
        )
        self.assertFalse(res09_fail.passed)

        res10_fail = evaluate_tau2_knowledge_sandbox_and_evaluator_matching_guard(
            requested_read_path="knowledge_base/faq.md",
            knowledge_base_root="knowledge_base",
            shell_env_keys={"PATH", "OPENAI_API_KEY"},
            gold_action_count=1,
            matched_unique_tool_call_count=1,
            reused_single_tool_call_for_multiple_gold=False,
            exchange_old_item_id="a",
            exchange_new_item_id="b",
            mmsc_url="",
            can_send_mms_result=False,
        )
        self.assertFalse(res10_fail.passed)
        self.assertEqual(res10_fail.reason_code, "TAU2_SANDBOX_SHELL_SECRET_ENV_LEAK")

        res11_ok = evaluate_mcp_ts_py_uri_fragment_and_dpop_guard(
            uri_template_matched_value="item-42",
            stale_stdio_frames_cleared_on_restart=True,
            dpop_proof_attached_on_token_request=True,
            bytes_tool_output_base64_encoded=True,
            invalid_host_origin_crashed_sse_server=False,
            completion_items_count=120,
            completion_page_size=100,
        )
        self.assertTrue(res11_ok.passed)

        res12_fail = evaluate_mcp_go_rust_preinit_and_stateless_2026_07_28_guard(
            request_before_initialize=False,
            preinit_error_code=-32600,
            peer_cancellation_bound_before_id_reuse=True,
            resource_metadata_secret_redacted=True,
            session_protocol_version="2026-07-28",
            server_to_client_request_attempted=True,
            server_to_client_request_rejected=False,
            host_and_origin_literals_validated=True,
            multiline_auth_secret_rejected=True,
        )
        self.assertFalse(res12_fail.passed)
        self.assertEqual(res12_fail.reason_code, "MCP_RUST_2026_07_28_SERVER_TO_CLIENT_REQUEST_ALLOWED")

        res13_ok = evaluate_mcp_csharp_java_kotlin_id_jag_and_rfc3986_guard(
            discovered_issuer="https://auth.example/tenant",
            id_jag_audience="https://auth.example/tenant",
            cancellation_misreported_as_missing_oauth_meta=False,
            comma_separated_uri_vars_split=True,
            java_bare_cr_terminated_message=False,
            kotlin_sse_endpoint_resolved_per_rfc3986=True,
            kotlin_stdio_kept_running_on_handler_cancel=True,
        )
        self.assertTrue(res13_ok.passed)

        res14_fail = evaluate_mcp_swift_pkce_modulo_and_stateless_id_collision_guard(
            pkce_random_byte=100,
            pkce_byte_accepted=True,
            oauth_issuer_validated=True,
            omitted_refresh_token_retained=True,
            client_secret_basic_percent_encoded=True,
            base64_detected_from_data_url_header_only=True,
            in_flight_request_ids={"id-99"},
            incoming_request_id="id-99",
            stateless_collision_rejected=False,
            resource_templates_excluded_from_resources_list=True,
        )
        self.assertFalse(res14_fail.passed)
        self.assertEqual(res14_fail.reason_code, "MCP_SWIFT_STATELESS_HTTP_IN_FLIGHT_ID_COLLISION")

        res15_ok = evaluate_mcp_ruby_php_auth_redaction_and_elicitation_isolation_guard(
            ruby_retained_error_text="HTTP 401 [REDACTED]",
            ruby_non_jsonrpc2_rejected=True,
            ruby_non_utf8_json_key_code=-32700,
            ruby_undeclared_capability_code=-32601,
            php_host_and_origin_validated_independently=True,
            php_parallel_elicitation_answers_isolated=True,
            php_queued_notifications_bundled_in_request_json=False,
            php_unreachable_session_store_http_status=503,
        )
        self.assertTrue(res15_ok.passed)

        res16_ok = evaluate_mcp_conformance_sep2243_dpop_and_inspector_scripts_guard(
            sep2243_header_mismatch_error_code=-32020,
            sep2164_resource_not_found_error_code=-32002,
            reject_all_server_scored_green=False,
            sep1932_dpop_jkt_bound=True,
            sep1932_bearer_downgrade_rejected=True,
            inspector_npm_allow_scripts_stripped=True,
            inspector_directory_read_has_ttl_and_cache_scope=True,
            registry_backup_verifiable=True,
        )
        self.assertTrue(res16_ok.passed)

    def test_stage281_benchmark_summary_and_7card_bilingual_html(self) -> None:
        summary = build_stage281_summary()
        self.assertEqual(summary["scenario_count"], 16)
        self.assertEqual(summary["total_unique_prs"], 293)
        self.assertEqual(summary["upstream_repo_count"], 40)
        self.assertEqual(summary["attack_block_rate"], "16/16")
        self.assertEqual(summary["remediated_pass_rate"], "16/16")
        self.assertEqual(summary["perturbation_consistency"], "16/16")

        with tempfile.TemporaryDirectory() as tmp:
            paths = write_stage281_artifacts(Path(tmp))
            for key in ("summary", "cards_zh", "cards_en"):
                self.assertTrue(paths[key].exists())
            zh_html = paths["cards_zh"].read_text(encoding="utf-8")
            en_html = paths["cards_en"].read_text(encoding="utf-8")
            for page in (zh_html, en_html):
                self.assertIn("default-src 'none'; style-src 'unsafe-inline'", page)
                for idx in range(1, 8):
                    self.assertIn(f'id="card-{idx}"', page)
                    self.assertIn(f"{idx} / 7", page)


if __name__ == "__main__":
    unittest.main()
