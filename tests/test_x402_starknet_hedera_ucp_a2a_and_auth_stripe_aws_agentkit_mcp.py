"""Unit tests for Stage 276–277 protocol & security guards and 7-Card benchmark."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.x402_starknet_hedera_ucp_a2a_and_auth_stripe_aws_agentkit_mcp_bench import run_benchmark
from lab.x402_starknet_hedera_ucp_a2a_and_auth_stripe_aws_agentkit_mcp_guards import (
    STAGE_276_PR_CITATIONS,
    evaluate_a2a_java_failclosed_auth_ssrf_guard,
    evaluate_a2a_python_and_auth_path_tap_guard,
    evaluate_a2a_v101_error_jcs_edge_auth_guard,
    evaluate_agentkit_upload_cwd_beforepayment_actionref_guard,
    evaluate_mcp_csharp_java_inspector_guard,
    evaluate_mcp_go_dcr_version_listen_drain_guard,
    evaluate_mcp_python_host_case_mint_nan_405_guard,
    evaluate_mcp_rust_retired_session_origin_sha_guard,
    evaluate_mcp_ts_queue_order_tool_cache_progress_guard,
    evaluate_stripe_go_secret_cli_bool_release_guard,
    evaluate_stripe_node_workload_id_v2list_guard,
    evaluate_stripe_python_event_prehandle_guard,
    evaluate_ucp_fact_audit_mcp_sep_env_guard,
    evaluate_x402_buildercode_override_ed25519_guard,
    evaluate_x402_hedera_permit2_wildcard_mcp_guard,
    evaluate_x402_starknet_svm_xrpl_sim_guard,
)


class TestStage276And277GuardsAndBench(unittest.TestCase):
    def test_stage_276_pr_citation_inventory(self) -> None:
        self.assertEqual(len(STAGE_276_PR_CITATIONS), 16)
        total = sum(len(v) for v in STAGE_276_PR_CITATIONS.values())
        self.assertEqual(total, 203)

    def test_x402_ucp_and_a2a_guards_pr01_to_pr07(self) -> None:
        d1_bad = evaluate_x402_starknet_svm_xrpl_sim_guard(
            starknet_transfers=[{"from": "0xOther", "to": "0xMerch", "amount": 100}],
            expected_payer="0xBuyer",
            expected_pay_to="0xMerch",
            required_amount_minor=100,
            compute_unit_price_microlamports=1000,
            max_compute_unit_price_microlamports=5000,
            smart_wallet_verified=True,
            xrpl_decoded_tx={"TransactionType": "Payment"},
            xrpl_canonical_bytes_match=True,
            evm_simulation_outcome="ok",
        )
        self.assertFalse(d1_bad.admitted)
        self.assertEqual(d1_bad.code, "X402_STARKNET_PAYER_TRANSFER_COUNT_INVALID")

        d2_bad = evaluate_x402_hedera_permit2_wildcard_mcp_guard(
            hedera_declared_amount=500,
            hedera_payee_net_credit=450,
            settle_response_success=True,
            transfer_log_emitted=True,
            transfer_log_amount=500,
            route_pattern="/paid/*",
            request_path="/paid/resource",
            is_corrective_402_retry=False,
            reapproved_before_retry_sign=True,
        )
        self.assertFalse(d2_bad.admitted)
        self.assertEqual(d2_bad.code, "X402_HEDERA_NET_CREDIT_SHORTFALL")

        d3_ok = evaluate_x402_buildercode_override_ed25519_guard(
            server_service_codes=["s1", "s2", "s3"],
            client_service_codes=["c1", "c2", "c3", "c4"],
            response_body_bytes=4096,
            status_402_cache_control="no-store",
            status_402_body_mirrors_header=True,
            override_percent_str="50",
            base_amount_minor=2000,
            ed25519_pubkey_is_small_order=False,
            storage_error_occurred=False,
            retry_body_preserved=True,
        )
        self.assertTrue(d3_ok.admitted)
        self.assertEqual(len(d3_ok.metadata["service_codes"]), 5)
        self.assertEqual(d3_ok.metadata["effective_minor"], 1000)

        d4_ok = evaluate_ucp_fact_audit_mcp_sep_env_guard(
            ucp_broken_fact_refs=[],
            sep_job_has_deployment_environment=True,
            expired_charter_invites=[],
            home_page_has_security_link=True,
        )
        self.assertTrue(d4_ok.admitted)

        d5_bad = evaluate_a2a_v101_error_jcs_edge_auth_guard(
            error_type="InvalidAgentResponseError",
            http_status=500,
            grpc_status="UNKNOWN",
            jcs_contains_lone_surrogate=False,
            jcs_negative_zero_normalized=True,
            protocol="a2a",
            discovery_source="agent_card_security_schemes",
        )
        self.assertFalse(d5_bad.admitted)
        self.assertEqual(d5_bad.code, "A2A_V101_ERROR_MAPPING_MISMATCH")

        d6_bad = evaluate_a2a_python_and_auth_path_tap_guard(
            required_schemes_in_requirement=["oauth2", "apiKey"],
            applied_client_schemes=["oauth2"],
            rest_path_params={"task_id": "t1"},
            push_auth_configured=True,
            push_authorization_header_sent=True,
            slow_subscriber_queue_full=False,
            evicted_on_full=True,
            call_context_restored_after_cancel=True,
        )
        self.assertFalse(d6_bad.admitted)
        self.assertEqual(d6_bad.code, "A2A_PYTHON_MULTI_SCHEME_AND_UNSATISFIED")

        d7_bad = evaluate_a2a_java_failclosed_auth_ssrf_guard(
            task_auth_provider_configured=True,
            task_authorized=True,
            auth_header_name="Authorization",
            auth_header_value="Bearer ok",
            http_redirects_enabled=False,
            push_webhook_host="[::ffff:127.0.0.1]",
        )
        self.assertFalse(d7_bad.admitted)
        self.assertEqual(d7_bad.code, "A2A_JAVA_PUSH_SSRF_IPV4_MAPPED_IPV6_BLOCKED")

    def test_stripe_agentkit_and_mcp_guards_pr08_to_pr16(self) -> None:
        d8_bad = evaluate_stripe_node_workload_id_v2list_guard(
            auth_mode="aws_workload_identity",
            aws_sts_token_ttl_seconds=900,
            v2_list_payload={"data": [], "has_more": False},
            callback_mutated_parent_client=False,
            workflow_default_permissions="none",
        )
        self.assertFalse(d8_bad.admitted)
        self.assertEqual(d8_bad.code, "STRIPE_NODE_V2_LIST_CONTAINS_V1_FIELDS")

        d9_bad = evaluate_stripe_python_event_prehandle_guard(
            notification_payload={"id": "evt_1", "object": "event"},
            seen_event_ids={"evt_1"},
            pre_handle_executed=True,
            is_async_handler=True,
            awaited_properly=True,
        )
        self.assertFalse(d9_bad.admitted)
        self.assertEqual(d9_bad.code, "STRIPE_PYTHON_DUPLICATE_THIN_EVENT_BLOCKED")

        d10_ok = evaluate_stripe_go_secret_cli_bool_release_guard(
            webhook_secret="whsec_valid",
            cli_args=["--disabled", "false"],
            release_age_hours=26.0,
            upgrade_notice_shown=True,
            chmod_executed_on_invocation=False,
        )
        self.assertTrue(d10_ok.admitted)
        self.assertEqual(d10_ok.metadata["parsed_flags"], {"disabled": False})

        d11_bad = evaluate_agentkit_upload_cwd_beforepayment_actionref_guard(
            allowed_cwd="/app/work",
            requested_upload_path="../secrets.env",
            recipient_address="0xGood",
            sanctioned_recipients=frozenset(),
            declared_action_payload={"a": 1},
            claimed_action_ref="aref_any",
            beaver_knight_trust_score=95,
        )
        self.assertFalse(d11_bad.admitted)
        self.assertEqual(d11_bad.code, "AGENTKIT_UPLOAD_MEDIA_PATH_TRAVERSAL_BLOCKED")

        d12_bad = evaluate_mcp_go_dcr_version_listen_drain_guard(
            dcr_response_bytes=2_000_000,
            requested_protocol_version="2026-07-28",
            allowed_protocol_versions=["2026-07-28"],
            active_listen_ids=set(),
            completed_listen_ids=set(),
            sse_buffered_messages_drained_on_close=True,
        )
        self.assertFalse(d12_bad.admitted)
        self.assertEqual(d12_bad.code, "MCP_GO_OAUTHEX_DCR_RESPONSE_TOO_LARGE")

        d13_bad = evaluate_mcp_rust_retired_session_origin_sha_guard(
            session_retired=True,
            late_reply_accepted=True,
            origin_header="https://good.example",
            allowed_origins=["https://good.example"],
            action_pins=["a" * 40],
        )
        self.assertFalse(d13_bad.admitted)
        self.assertEqual(d13_bad.code, "MCP_RUST_RETIRED_SESSION_REPLY_ACCEPTED")

        d14_ok = evaluate_mcp_python_host_case_mint_nan_405_guard(
            host_header="MCP.Example.COM",
            allowed_hosts=["mcp.example.com"],
            caller_supplied_request_ids=[5, 19],
            next_minted_request_id=20,
            float_values=[2.5, float("nan")],
            get_stream_http_status=405,
            get_stream_retried=False,
        )
        self.assertTrue(d14_ok.admitted)
        self.assertEqual(d14_ok.metadata["serialized_floats"], [2.5, None])

        d15_bad = evaluate_mcp_ts_queue_order_tool_cache_progress_guard(
            queued_messages_before_close=["m1"],
            transport_closed=False,
            delivered_after_close=[],
            previous_tool_cache=["t1"],
            refresh_compile_failed=True,
            active_tool_cache=[],
            events_in_single_chunk=["progress", "response"],
        )
        self.assertFalse(d15_bad.admitted)
        self.assertEqual(d15_bad.code, "MCP_TS_TOOL_CACHE_LOST_ON_REFRESH_FAILURE")

        d16_bad = evaluate_mcp_csharp_java_inspector_guard(
            progress_token_json_value="99",
            jsonrpc_response_version="2.0",
            http_200_body_is_valid_json=True,
            send_message_completed_before_parse=False,
            sse_value_contains_u2028=False,
            sse_value_truncated=False,
            inspector_probe_status=200,
            inspector_auto_era_fell_back=True,
            stripped_namespace_secret_preserved=True,
        )
        self.assertFalse(d16_bad.admitted)
        self.assertEqual(d16_bad.code, "MCP_CSHARP_INTEGER_PROGRESS_TOKEN_STRINGIFIED")

    def test_stage_277_benchmark_report_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "stage-277-bench"
            rep = run_benchmark(out)
            self.assertEqual(rep["total_scenarios"], 16)
            self.assertEqual(rep["ai_native_passed"], 16)
            self.assertEqual(rep["classic_3tier_passed"], 2)
            self.assertEqual(rep["total_primary_source_prs"], 203)
            zh_html = (out / "index.html").read_text(encoding="utf-8")
            en_html = (out / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)
            self.assertIn("1 / 7 · HANDS-ON", zh_html)
            self.assertIn("7 / 7 · MY TAKE", en_html)


if __name__ == "__main__":
    unittest.main()
