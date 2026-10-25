"""Unit tests for Stage 270–271 guards and 16-scenario 7-Card benchmark suite (`PR-01..PR-16`)."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.x402_ext_sidechannel_a2a_utc_stripe_multipart_agentkit_mcp_stdio_bench import (
    run_benchmark_scenarios,
    write_benchmark_report,
)
from lab.x402_ext_sidechannel_a2a_utc_stripe_multipart_agentkit_mcp_stdio_guards import (
    BROKEN_TRANSIENT_UPTO_PERMIT2_PROXY,
    CANONICAL_X402_UPTO_PERMIT2_PROXY,
    SAPIEN_VAULT_BASE_ADDRESS,
    evaluate_a2a_dotnet_parse_sanitization_js_compat_and_py_nanos_guard,
    evaluate_a2a_go_accept_negotiation_utc_and_terminal_error_guard,
    evaluate_a2a_java_terminal_sse_blank_ids_and_redirect_guard,
    evaluate_agentkit_x402_scraper_sapien_vault_and_lazy_solana_guard,
    evaluate_mcp_csharp_autodetect_400_404_legacy_meta_and_parse_detail_guard,
    evaluate_mcp_go_cancel_cause_mcp_name_base64_and_issuer_slash_guard,
    evaluate_mcp_go_case_insensitive_loopback_lazy_proxy_and_stdio_cancel_guard,
    evaluate_mcp_inspector_oauth_lock_restore_403_challenge_and_temp_cleanup_guard,
    evaluate_mcp_java_nullable_list_changed_and_resubscribable_mono_guard,
    evaluate_mcp_kotlin_sse_plugin_null_ttl_and_php_variadic_guard,
    evaluate_mcp_rust_resource_metadata_origin_and_discover_neutral_guard,
    evaluate_stripe_cli_profile_oauth_sync_and_rename_retry_guard,
    evaluate_stripe_node_incomplete_body_and_esm_interceptor_guard,
    evaluate_stripe_python_csprng_multipart_and_singleton_event_guard,
    evaluate_x402_batch_settlement_local_truth_and_upfront_flow_guard,
    evaluate_x402_extension_responses_sidechannel_and_upto_proxy_guard,
)


class Stage270To271GuardAndBenchmarkTests(unittest.TestCase):
    def test_pr01_to_pr05_x402_and_a2a_polyglot_guards(self) -> None:
        # PR-01
        bad_pr01 = evaluate_x402_extension_responses_sidechannel_and_upto_proxy_guard(
            extension_responses_header_json='{"facilitatorReceipt":"internal"}',
            merge_sidechannel_into_buyer_extensions=True,
            strip_sidechannel_from_payment_response=False,
            upto_permit2_proxy_address=BROKEN_TRANSIENT_UPTO_PERMIT2_PROXY,
        )
        self.assertFalse(bad_pr01.passed)
        ok_pr01 = evaluate_x402_extension_responses_sidechannel_and_upto_proxy_guard(
            extension_responses_header_json='{"facilitatorReceipt":"internal"}',
            merge_sidechannel_into_buyer_extensions=False,
            strip_sidechannel_from_payment_response=True,
            upto_permit2_proxy_address=CANONICAL_X402_UPTO_PERMIT2_PROXY,
        )
        self.assertTrue(ok_pr01.passed)
        self.assertFalse(ok_pr01.details["buyer_payment_response_has_sidechannel"])

        # PR-02
        bad_pr02 = evaluate_x402_batch_settlement_local_truth_and_upfront_flow_guard(
            local_cumulative_amount=100,
            local_refundable_balance=40,
            charged_amount=50,
            max_step_charge=30,
            client_signed_deposit=10,
            response_charged_cumulative_amount=999,
            requested_refund_amount=80,
            trust_unverified_server_channel_state=True,
            upfront_payment_header_present=True,
        )
        self.assertFalse(bad_pr02.passed)
        ok_pr02 = evaluate_x402_batch_settlement_local_truth_and_upfront_flow_guard(
            local_cumulative_amount=100,
            local_refundable_balance=40,
            charged_amount=50,
            max_step_charge=30,
            client_signed_deposit=10,
            response_charged_cumulative_amount=999,
            requested_refund_amount=80,
            trust_unverified_server_channel_state=False,
            upfront_payment_header_present=True,
        )
        self.assertTrue(ok_pr02.passed)
        self.assertEqual(ok_pr02.details["expected_next_cumulative"], 140)
        self.assertFalse(ok_pr02.details["state_written"])
        self.assertEqual(ok_pr02.details["applied_refund"], 40)

        # PR-03
        ok_pr03 = evaluate_a2a_go_accept_negotiation_utc_and_terminal_error_guard(
            accept_header="application/json",
            timestamp_epoch_ms=1792972800045,
            task_is_terminal=True,
            operation="SubscribeToTask",
            return_spec_unsupported_on_terminal=True,
        )
        self.assertTrue(ok_pr03.passed)
        self.assertEqual(ok_pr03.details["response_content_type"], "application/json")
        self.assertTrue(ok_pr03.details["utc_timestamp"].endswith(".045Z"))

        # PR-04
        ok_pr04 = evaluate_a2a_java_terminal_sse_blank_ids_and_redirect_guard(
            sse_events=["complete", "error"],
            use_atomic_terminal_signal=True,
            incoming_task_id="  ",
            incoming_context_id="",
            request_uri="https://agent.example.com/a2a/v1/send",
            redirect_location="/collect",
        )
        self.assertTrue(ok_pr04.passed)
        self.assertEqual(ok_pr04.details["terminal_callbacks"], 1)
        self.assertIsNone(ok_pr04.details["normalized_task_id"])
        self.assertEqual(ok_pr04.details["resolved_redirect_uri"], "https://agent.example.com/collect")

        # PR-05
        ok_pr05 = evaluate_a2a_dotnet_parse_sanitization_js_compat_and_py_nanos_guard(
            raw_json_exception_message="LineNumber: 1",
            sanitize_parse_error=True,
            timestamps_ns=[100, 900, 300],
            compare_as_integer_nanos=True,
            custom_table_name="custom_tasks",
        )
        self.assertTrue(ok_pr05.passed)
        self.assertEqual(ok_pr05.details["wire_parse_error_message"], "Invalid JSON payload")
        self.assertEqual(ok_pr05.details["sorted_desc_ns"], [900, 300, 100])

    def test_pr06_to_pr09_stripe_and_agentkit_guards(self) -> None:
        # PR-06
        ok_pr06 = evaluate_stripe_node_incomplete_body_and_esm_interceptor_guard(
            response_headers_received=True,
            body_stream_aborted_midway=True,
            payload_text='{"incomplete":',
            wait_for_raw_socket_event=False,
            esm_default_is_constructable=True,
        )
        self.assertTrue(ok_pr06.passed)
        self.assertEqual(ok_pr06.details["classified_error"], "StripeConnectionError")

        # PR-07
        ok_pr07 = evaluate_stripe_python_csprng_multipart_and_singleton_event_guard(
            boundary_hex="f" * 60,
            used_csprng=True,
            field_name='file"; evil="1\r\n',
            filename='doc"\n.pdf',
            related_object_is_singleton=True,
            related_object_id=None,
        )
        self.assertTrue(ok_pr07.passed)
        self.assertIn("%22", ok_pr07.details["escaped_name"])
        self.assertEqual(ok_pr07.details["related_object_class"], "SingletonRelatedObject")

        # PR-08
        ok_pr08 = evaluate_stripe_cli_profile_oauth_sync_and_rename_retry_guard(
            selected_profile="prod",
            profile_account_map={"prod": "acct_prod_999"},
            active_oauth_account_before="acct_dev_000",
            sync_oauth_context_with_profile=True,
            transient_sharing_violations=1,
            max_rename_retries=3,
        )
        self.assertTrue(ok_pr08.passed)
        self.assertEqual(ok_pr08.details["effective_account"], "acct_prod_999")

        # PR-09
        ok_pr09 = evaluate_agentkit_x402_scraper_sapien_vault_and_lazy_solana_guard(
            network_id="8453",
            sapien_vault_address=SAPIEN_VAULT_BASE_ADDRESS,
            scraper_settlement_mode="erc20_transfer_receipt",
            lazy_import_solana_deps=True,
        )
        self.assertTrue(ok_pr09.passed)

    def test_pr10_to_pr16_mcp_polyglot_sdk_and_inspector_guards(self) -> None:
        # PR-10
        ok_pr10 = evaluate_mcp_go_case_insensitive_loopback_lazy_proxy_and_stdio_cancel_guard(
            host_header="LocalHost:3000",
            build_discovery_transport_lazily=True,
            protocol_version="2026-07-28",
            transport_kind="stdio",
            request_was_cancelled=True,
            suppress_cancelled_stdio_response=True,
        )
        self.assertTrue(ok_pr10.passed)
        self.assertFalse(ok_pr10.details["should_send_response"])

        # PR-11
        ok_pr11 = evaluate_mcp_go_cancel_cause_mcp_name_base64_and_issuer_slash_guard(
            cancellation_reason="user_cancelled",
            propagate_reason_to_context_cause=True,
            mcp_name="Agent / Space",
            issuer_url="https://issuer.example.com/realm/",
        )
        self.assertTrue(ok_pr11.passed)
        self.assertTrue(ok_pr11.details["encoded_mcp_name"].startswith("=?base64?"))
        self.assertEqual(
            ok_pr11.details["metadata_urls"][0],
            "https://issuer.example.com/.well-known/oauth-authorization-server/realm",
        )

        # PR-12
        ok_pr12 = evaluate_mcp_rust_resource_metadata_origin_and_discover_neutral_guard(
            pointer_from_well_known_guess_401=True,
            pointer_fetch_failed=True,
            remaining_candidates=1,
            treat_guess_pointer_as_advertised=False,
            first_request_method="server/discover",
            subsequent_request_method="initialize",
        )
        self.assertTrue(ok_pr12.passed)
        self.assertEqual(ok_pr12.details["selected_lifecycle"], "classic_initialized")

        # PR-13
        ok_pr13 = evaluate_mcp_java_nullable_list_changed_and_resubscribable_mono_guard(
            derived_list_changed=None,
            use_null_safe_boolean_check=True,
            items_per_page=["a", "b"],
            subscription_count=3,
            fresh_seed_per_subscription=True,
        )
        self.assertTrue(ok_pr13.passed)
        self.assertEqual(ok_pr13.details["observed_size_on_second_subscribe"], 2)

        # PR-14
        ok_pr14 = evaluate_mcp_csharp_autodetect_400_404_legacy_meta_and_parse_detail_guard(
            discover_probe_status=404,
            skip_sse_fallback_on_400_404=True,
            session_protocol_version="2025-11-25",
            request_has_2026_meta_keys=True,
            reject_future_meta_on_legacy_session=False,
            malformed_json_detail="Line 1, Pos 4",
        )
        self.assertTrue(ok_pr14.passed)

        # PR-15
        ok_pr15 = evaluate_mcp_kotlin_sse_plugin_null_ttl_and_php_variadic_guard(
            sse_plugin_already_installed=True,
            check_plugin_or_null_before_install=True,
            task_ttl=None,
            serialize_explicit_null_ttl=True,
            variadic_raw_elements=["1", "2"],
        )
        self.assertTrue(ok_pr15.passed)
        self.assertIn('"ttl": null', ok_pr15.details["serialized_task_json"])

        # PR-16
        ok_pr16 = evaluate_mcp_inspector_oauth_lock_restore_403_challenge_and_temp_cleanup_guard(
            claimed_lock_is_fresh=True,
            restore_fresh_lock_instead_of_delete=True,
            http_status=403,
            www_authenticate_header="",
            as_metadata_published=False,
            configured_token_endpoint_override="https://override.example/token",
            cleanup_temp_copy_files_on_exit=True,
        )
        self.assertTrue(ok_pr16.passed)
        self.assertFalse(ok_pr16.details["is_oauth_challenge"])
        self.assertEqual(ok_pr16.details["effective_token_endpoint"], "https://override.example/token")

    def test_stage_271_benchmark_suite_and_7_card_report_generation(self) -> None:
        scenarios = run_benchmark_scenarios()
        self.assertEqual(len(scenarios), 16)
        self.assertTrue(all(not s.unpatched_passed for s in scenarios))
        self.assertTrue(all(s.patched_passed for s in scenarios))

        with tempfile.TemporaryDirectory() as tmp_dir:
            out = Path(tmp_dir)
            payload = write_benchmark_report(out)
            self.assertEqual(payload["scenario_count"], 16)
            self.assertEqual(payload["upstream_pr_count"], 53)
            self.assertEqual(payload["unpatched_interception_count"], 16)
            self.assertEqual(payload["patched_pass_count"], 16)
            self.assertTrue((out / "report.json").exists())
            self.assertTrue((out / "index.html").exists())
            self.assertTrue((out / "index.en.html").exists())
            zh_html = (out / "index.html").read_text(encoding="utf-8")
            en_html = (out / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", en_html)
            self.assertIn("1 / 7", zh_html)
            self.assertIn("7 / 7", en_html)


if __name__ == "__main__":
    unittest.main()
