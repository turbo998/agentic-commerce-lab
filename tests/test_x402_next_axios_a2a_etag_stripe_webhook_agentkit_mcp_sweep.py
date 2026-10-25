"""Unit tests for Stage 268 deterministic guards and Stage 269 16-scenario 7-Card benchmark."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.x402_next_axios_a2a_etag_stripe_webhook_agentkit_mcp_sweep_bench import (
    run_benchmark_suite,
    write_report_artifacts,
)
from lab.x402_next_axios_a2a_etag_stripe_webhook_agentkit_mcp_sweep_guards import (
    evaluate_a2a_agent_card_weak_etag_guard,
    evaluate_a2a_input_modes_and_java_wire_guard,
    evaluate_a2a_task_context_and_terminal_state_guard,
    evaluate_agentkit_dexter_walletforge_hcrb_guard,
    evaluate_mcp_csharp_mrtr_dispose_race_and_symlink_guard,
    evaluate_mcp_go_batch_notification_and_version_membership_guard,
    evaluate_mcp_go_empty_header_and_sub_generation_guard,
    evaluate_mcp_inspector_cli_config_and_task_routing_guard,
    evaluate_mcp_java_session_sweep_and_error_sanitization_guard,
    evaluate_mcp_rust_initial_dispatch_and_cancel_routing_guard,
    evaluate_mcp_rust_origin_default_port_guard,
    evaluate_stripe_cli_path_segment_and_peer_hook_guard,
    evaluate_stripe_node_webhook_secret_and_tolerance_guard,
    evaluate_stripe_python_event_context_scoping_guard,
    evaluate_x402_axios_url_and_timeout_reconciliation_guard,
    evaluate_x402_next_adapter_query_and_body_guard,
)


class TestStage268And269GuardsAndBenchmark(unittest.TestCase):
    def test_pr01_to_pr05_x402_and_a2a_guards(self) -> None:
        # PR-01: @x402/next leading empty query and cloned body
        ok_01 = evaluate_x402_next_adapter_query_and_body_guard(
            raw_query="tag=&tag=b",
            raw_body_text='{"data":"test"}',
            use_cloned_body_read=True,
            check_undefined_instead_of_truthy=True,
        )
        self.assertTrue(ok_01.passed)
        self.assertEqual(ok_01.details["parsed_params"]["tag"], ["", "b"])
        bad_01 = evaluate_x402_next_adapter_query_and_body_guard(
            raw_query="tag=&tag=b",
            raw_body_text='{"data":"test"}',
            use_cloned_body_read=False,
            check_undefined_instead_of_truthy=True,
        )
        self.assertFalse(bad_01.passed)

        # PR-02: @x402/axios getUri & post-signature timeout
        ok_02 = evaluate_x402_axios_url_and_timeout_reconciliation_guard(
            base_url="https://api.example.com/v2/paid",
            relative_url="/quotes",
            query_params={"sku": "gpu"},
            use_axios_get_uri=True,
            payment_signature_sent=True,
            settlement_outcome="settlement_pending",
            auto_repay_attempted=False,
        )
        self.assertTrue(ok_02.passed)
        self.assertIn("/v2/paid/quotes?sku=gpu", ok_02.details["resolved_url"])
        bad_02 = evaluate_x402_axios_url_and_timeout_reconciliation_guard(
            base_url="https://api.example.com/v2/paid",
            relative_url="/quotes",
            query_params={"sku": "gpu"},
            use_axios_get_uri=True,
            payment_signature_sent=True,
            settlement_outcome="timeout_unknown",
            auto_repay_attempted=True,
        )
        self.assertFalse(bad_02.passed)

        # PR-03: A2A AgentCard weak ETag
        card_a = {"name": "Agent", "version": "1.0", "signatures": [{"signature": "sig1"}]}
        card_b = {"name": "Agent", "version": "1.0", "signatures": [{"signature": "sig2"}]}
        etag_a = evaluate_a2a_agent_card_weak_etag_guard(
            card_dict=card_a,
            if_none_match=None,
            strip_signatures_for_etag=True,
            use_weak_etag=True,
        )
        etag_b = evaluate_a2a_agent_card_weak_etag_guard(
            card_dict=card_b,
            if_none_match=etag_a.details["etag"],
            strip_signatures_for_etag=True,
            use_weak_etag=True,
        )
        self.assertEqual(etag_a.details["etag"], etag_b.details["etag"])
        self.assertEqual(etag_b.details["status_code"], 304)

        # PR-04: A2A contextId mismatch & terminal task
        ctx_err = evaluate_a2a_task_context_and_terminal_state_guard(
            task_id="t1",
            task_context_id="ctx-real",
            message_context_id="ctx-wrong",
            task_state="TASK_STATE_WORKING",
            operation="send",
        )
        self.assertEqual(ctx_err.decision_code, "A2A_CONTEXT_ID_MISMATCH_INVALID_PARAMS")
        self.assertFalse(ctx_err.details["executor_started"])

        term_err = evaluate_a2a_task_context_and_terminal_state_guard(
            task_id="t1",
            task_context_id="ctx-real",
            message_context_id="ctx-real",
            task_state="TASK_STATE_COMPLETED",
            operation="cancel",
        )
        self.assertEqual(term_err.details["error_type"], "TaskNotCancelableError")

        # PR-05: A2A input modes & Java REST/JSON-RPC
        res_05 = evaluate_a2a_input_modes_and_java_wire_guard(
            declared_default_input_modes=["text/plain"],
            declared_skill_input_modes=["application/json"],
            part_media_type="image/png",
            validate_input_modes_enabled=True,
            history_length=5,
            jsonrpc_id_is_null=True,
            writer_serialize_nulls=False,
        )
        self.assertEqual(res_05.decision_code, "A2A_CONTENT_TYPE_NOT_SUPPORTED_REJECTED")
        self.assertEqual(res_05.details["query_path"], "/tasks/task-1?historyLength=5")

    def test_pr06_to_pr09_stripe_and_agentkit_guards(self) -> None:
        # PR-06: Stripe Node blank webhook secret & nullish tolerance
        blank = evaluate_stripe_node_webhook_secret_and_tolerance_guard(
            webhook_secret="   \t\n ",
            tolerance=None,
            event_age_seconds=10,
        )
        self.assertEqual(blank.decision_code, "STRIPE_BLANK_WEBHOOK_SECRET_REJECTED")

        zero_tol = evaluate_stripe_node_webhook_secret_and_tolerance_guard(
            webhook_secret="whsec_valid_secret",
            tolerance=0,
            event_age_seconds=99999,
        )
        self.assertEqual(zero_tol.decision_code, "STRIPE_WEBHOOK_VERIFIED_WITH_NULLISH_TOLERANCE")
        self.assertTrue(zero_tol.details["timestamp_check_skipped"])

        # PR-07: Stripe Python event context account isolation
        leak = evaluate_stripe_python_event_context_scoping_guard(
            parent_stripe_account="acct_123",
            event_stripe_context="ctx_456",
            leak_parent_account_into_callback=True,
            used_keyword_for_positional_only_id=False,
        )
        self.assertFalse(leak.passed)
        clean = evaluate_stripe_python_event_context_scoping_guard(
            parent_stripe_account="acct_123",
            event_stripe_context="ctx_456",
            leak_parent_account_into_callback=False,
            used_keyword_for_positional_only_id=False,
        )
        self.assertTrue(clean.passed)
        self.assertIsNone(clean.details["callback_stripe_account"])

        # PR-08: Stripe CLI dot/empty segment & PathEscape
        dot_seg = evaluate_stripe_cli_path_segment_and_peer_hook_guard(
            path_template="/v1/query_runs/{id}",
            positional_segments=[".."],
            explicit_api_base_flag=None,
            default_api_base="https://api.stripe.com",
            forward_unflagged_default_to_peer_hook=False,
        )
        self.assertEqual(dot_seg.decision_code, "STRIPE_CLI_DOT_PATH_SEGMENT_REJECTED")

        esc_seg = evaluate_stripe_cli_path_segment_and_peer_hook_guard(
            path_template="/v1/customers/{customer}",
            positional_segments=["id1/../../customers/cus_123"],
            explicit_api_base_flag=None,
            default_api_base="https://api.stripe.com",
            forward_unflagged_default_to_peer_hook=False,
        )
        self.assertEqual(
            esc_seg.details["formatted_path"],
            "/v1/customers/id1%2F..%2F..%2Fcustomers%2Fcus_123",
        )

        # PR-09: AgentKit Dexter, WalletForge & HCRB
        ak_ok = evaluate_agentkit_dexter_walletforge_hcrb_guard(
            facilitator="dexter",
            custom_facilitators={},
            network_id="8453",
            tool_name="normalize_text",
            quoted_usdc=0.01,
        )
        self.assertEqual(ak_ok.decision_code, "AGENTKIT_DEXTER_WALLETFORGE_HCRB_VERIFIED")
        self.assertEqual(ak_ok.details["facilitator_url"], "https://x402.dexter.cash")

    def test_pr10_to_pr16_mcp_multi_sdk_guards(self) -> None:
        # PR-10: MCP Go empty header & sub generation
        go_hdr = evaluate_mcp_go_empty_header_and_sub_generation_guard(
            arg_present=True,
            arg_value="",
            header_values=[""],
            active_sub_generation=2,
            closing_stream_generation=1,
        )
        self.assertTrue(go_hdr.passed)
        self.assertFalse(go_hdr.details["subscription_entry_cleared"])

        # PR-11: MCP Go batch notifications & protocolVersion membership
        go_ver = evaluate_mcp_go_batch_notification_and_version_membership_guard(
            batch_messages=[
                {"jsonrpc": "2.0", "id": 1, "method": "ping"},
                {"jsonrpc": "2.0", "method": "notifications/cancelled"},
            ],
            request_meta_protocol_version="1900-01-01",
            use_membership_check_instead_of_lexicographic=True,
        )
        self.assertEqual(go_ver.decision_code, "MCP_GO_UNSUPPORTED_PROTOCOL_VERSION_REJECTED")
        self.assertEqual(go_ver.details["tracked_call_ids"], [1])

        # PR-12: MCP Rust Origin default port
        rust_orig = evaluate_mcp_rust_origin_default_port_guard(
            allowed_origins=["https://app.example.com:443"],
            request_origin="https://app.example.com",
            match_scheme_default_port=True,
        )
        self.assertEqual(rust_orig.decision_code, "MCP_RUST_ORIGIN_DEFAULT_PORT_MATCHED")
        self.assertEqual(rust_orig.details["resolved_port"], 443)

        # PR-13: MCP Rust loop dispatch & cancel routing
        rust_loop = evaluate_mcp_rust_initial_dispatch_and_cancel_routing_guard(
            dispatch_initial_messages_in_service_loop=True,
            cancelled_request_is_subscription=True,
            route_cancellation_by_lifecycle=True,
        )
        self.assertTrue(rust_loop.passed)
        self.assertEqual(rust_loop.details["cancelled_target"], "subscription_channel")

        # PR-14: MCP Java session sweep & error sanitization
        java_sweep = evaluate_mcp_java_session_sweep_and_error_sanitization_guard(
            session_has_open_stream=False,
            session_active_in_interval=False,
            expose_aggregate_exception_in_jsonrpc_data=False,
            top_level_exception_message=None,
        )
        self.assertTrue(java_sweep.passed)
        self.assertTrue(java_sweep.details["session_evicted"])
        self.assertEqual(java_sweep.details["wire_error_message"], "Internal error")
        self.assertIsNone(java_sweep.details["wire_error_data"])

        # PR-15: MCP C# MRTR dispose race & doc symlink
        cs_mrtr = evaluate_mcp_csharp_mrtr_dispose_race_and_symlink_guard(
            server_lifetime_cts_cancelled=True,
            recheck_after_publish=True,
            docs_path_is_symlink=False,
        )
        self.assertTrue(cs_mrtr.passed)
        self.assertTrue(cs_mrtr.details["handler_cancelled"])

        # PR-16: MCP Inspector CLI conflict & taskSupport routing
        insp_conflict = evaluate_mcp_inspector_cli_config_and_task_routing_guard(
            positional_target="node",
            server_url_flag="https://example.com/mcp",
            transport_flag=None,
            tool_task_support=None,
            explicit_task_flag=False,
        )
        self.assertEqual(insp_conflict.decision_code, "MCP_INSPECTOR_TARGET_AND_SERVER_URL_CONFLICT")

        insp_task = evaluate_mcp_inspector_cli_config_and_task_routing_guard(
            positional_target=None,
            server_url_flag="https://example.com/mcp",
            transport_flag="http",
            tool_task_support="required",
            explicit_task_flag=False,
        )
        self.assertTrue(insp_task.details["use_task_augmented_stream"])

    def test_stage269_benchmark_and_7card_report_generation(self) -> None:
        report = run_benchmark_suite()
        self.assertEqual(report["total_scenarios"], 16)
        self.assertEqual(report["ai_native_passed"], 16)
        self.assertEqual(report["classic_3tier_passed"], 0)
        self.assertEqual(report["ai_native_pass_rate_pct"], 100.0)

        with tempfile.TemporaryDirectory() as tmp:
            paths = write_report_artifacts(Path(tmp))
            zh_html = Path(paths["index_html"]).read_text(encoding="utf-8")
            en_html = Path(paths["index_en_html"]).read_text(encoding="utf-8")
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)
            self.assertIn("1 / 7", zh_html)
            self.assertIn("7 / 7", en_html)
            self.assertIn("PR-16", en_html)


if __name__ == "__main__":
    unittest.main()
