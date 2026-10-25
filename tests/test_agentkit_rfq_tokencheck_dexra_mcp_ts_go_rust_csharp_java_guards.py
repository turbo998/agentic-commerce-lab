"""Unit tests for Stage 244 (245-Stage Milestone!) AgentKit & MCP Multi-SDK guards."""

from __future__ import annotations

import unittest

from lab.agentkit_rfq_tokencheck_dexra_mcp_ts_go_rust_csharp_java_guards import (
    BASE_UNISWAP_V4_RFQ_HOOK,
    evaluate_agentkit_cdp_basepath_uvloop_guard,
    evaluate_agentkit_dexra_solana_predge_pretrade_guard,
    evaluate_agentkit_uniswap_v4_atomic_rfq_guard,
    evaluate_agentkit_x402_pre_swap_token_check_guard,
    evaluate_mcp_csharp_entra_refresh_fallback_init_params_guard,
    evaluate_mcp_csharp_session_affinity_content_length_filter_guard,
    evaluate_mcp_go_cimd_url_request_state_retry_guard,
    evaluate_mcp_go_listen_subscription_stateless_recovery_guard,
    evaluate_mcp_go_multi_roundtrip_cache_colonless_sse_guard,
    evaluate_mcp_java_stdio_per_message_sse_commit_guard,
    evaluate_mcp_java_wildcard_numeric_port_session_sweep_guard,
    evaluate_mcp_rust_eof_token_cancel_20260728_s2c_guard,
    evaluate_mcp_rust_session_lock_release_origin_guard,
    evaluate_mcp_ts_async_output_validator_uri_fragment_guard,
    evaluate_mcp_ts_null_proto_registry_request_body_guard,
    evaluate_mcp_ts_sep2640_skills_extension_guard,
)


class Stage244AgentKitMcpMultiSdkGuardsTest(unittest.TestCase):
    def test_agentkit_and_mcp_ts_go_guards_pr01_to_pr08(self) -> None:
        # PR-01
        r1_bad = evaluate_agentkit_uniswap_v4_atomic_rfq_guard(
            chain_id=8453,
            hook_address=BASE_UNISWAP_V4_RFQ_HOOK,
            token_in="WETH",
            token_out="USDC",
            eip712_quote_sig_valid=True,
            quote_expired=False,
            quoted_amount_out=1000,
            min_amount_out=1000,
            simulated_amount_out=999,
            preflight_eth_call_ok=True,
        )
        self.assertFalse(r1_bad["admitted"])
        self.assertEqual(r1_bad["decision_code"], "AGENTKIT_RFQ_INSUFFICIENT_OUTPUT_FOR_QUOTED_SWAP")

        r1_ok = evaluate_agentkit_uniswap_v4_atomic_rfq_guard(
            chain_id=8453,
            hook_address=BASE_UNISWAP_V4_RFQ_HOOK,
            token_in="WETH",
            token_out="USDC",
            eip712_quote_sig_valid=True,
            quote_expired=False,
            quoted_amount_out=1000,
            min_amount_out=1000,
            simulated_amount_out=1000,
            preflight_eth_call_ok=True,
        )
        self.assertTrue(r1_ok["admitted"])

        # PR-02
        r2_bad = evaluate_agentkit_x402_pre_swap_token_check_guard(
            demo_only=False,
            requires_x402_payment=True,
            x402_scheme="exact",
            x402_network="eip155:8453",
            x402_payee="0xbad",
            pinned_payee="0xgood",
            price_atomic_usdc=10000,
            max_price_atomic_usdc=10000,
            verdict="safe",
            block_on=("danger",),
            fail_closed=True,
            buy_tax_bps=0,
            sell_tax_bps=0,
        )
        self.assertFalse(r2_bad["admitted"])
        self.assertEqual(r2_bad["decision_code"], "AGENTKIT_TOKENCHECK_X402_SPEND_POLICY_REJECTED")

        # PR-03
        r3_bad = evaluate_agentkit_cdp_basepath_uvloop_guard(
            base_path="https://api.cdp.coinbase.com/platform",
            is_chain_rpc_url=False,
            event_loop_type="uvloop.Loop",
            nest_asyncio_patched=True,
            cdp_sdk_version=(1, 42, 0),
        )
        self.assertFalse(r3_bad["admitted"])
        self.assertEqual(r3_bad["decision_code"], "AGENTKIT_UVLOOP_NEST_ASYNCIO_PATCH_FORBIDDEN")

        # PR-04
        r4_bad = evaluate_agentkit_dexra_solana_predge_pretrade_guard(
            dexra_verdict="avoid",
            token2022_permanent_delegate_trap=True,
            sandwich_share_bps=100,
            max_sandwich_share_bps=500,
            predge_settlement_dispute_risk_bps=100,
            max_dispute_risk_bps=300,
            requires_402_payment=True,
            service_url="https://api.dexra.dev/swap_preflight",
            registered_x402_services={"https://api.dexra.dev"},
        )
        self.assertFalse(r4_bad["admitted"])
        self.assertEqual(r4_bad["decision_code"], "AGENTKIT_DEXRA_SOLANA_TOKEN_TRAP_OR_AVOID")

        # PR-05
        r5_bad = evaluate_mcp_ts_sep2640_skills_extension_guard(
            protocol_version="2026-07-28",
            skills_entries=[
                {"uri": "skill://a/SKILL.md", "valid_schema": True},
                {"uri": "skill://a/SKILL.md", "valid_schema": True},
            ],
            skip_invalid=False,
            file_declared_size=100,
            file_actual_size=100,
            file_declared_sha256="aa",
            file_actual_sha256="aa",
            yaml_frontmatter_valid=True,
        )
        self.assertFalse(r5_bad["admitted"])
        self.assertEqual(r5_bad["decision_code"], "MCP_TS_SKILLS_STRICT_LIST_VALIDATION_FAILED")

        # PR-06
        r6_bad = evaluate_mcp_ts_null_proto_registry_request_body_guard(
            registry_uses_null_prototype=False,
            existing_registered_names=set(),
            candidate_tool_name="constructor",
            request_body_stream_implemented=True,
            request_text_fallback_available=True,
        )
        self.assertFalse(r6_bad["admitted"])
        self.assertEqual(r6_bad["decision_code"], "MCP_TS_OBJECT_PROTOTYPE_COLLISION_IN_PLAIN_MAP")

        # PR-07
        r7_ok = evaluate_mcp_ts_async_output_validator_uri_fragment_guard(
            validator_is_async=True,
            awaited_compilation=True,
            compilation_succeeded=True,
            awaited_validation=True,
            validation_passed=True,
            uri_template_pattern="resource://items/{id}",
            candidate_uri="resource://items/42#frag",
        )
        self.assertTrue(r7_ok["admitted"])
        self.assertEqual(r7_ok["extracted_var"], "42")

        # PR-08
        r8_ok = evaluate_mcp_go_multi_roundtrip_cache_colonless_sse_guard(
            has_input_responses=True,
            has_request_state=False,
            is_retried_result=True,
            is_input_required_interim=False,
            served_from_cache=False,
            stored_in_cache=False,
            raw_sse_line="data",
        )
        self.assertTrue(r8_ok["admitted"])
        self.assertEqual(r8_ok["sse_value"], "")

    def test_mcp_go_rust_csharp_java_guards_pr09_to_pr16(self) -> None:
        # PR-09
        r9_bad = evaluate_mcp_go_cimd_url_request_state_retry_guard(
            raw_client_id_url="https://agent.example.com/oauth/#",
            input_required_has_request_state=True,
            input_required_has_elicitation=False,
            retried_with_request_state=True,
        )
        self.assertFalse(r9_bad["admitted"])
        self.assertEqual(r9_bad["decision_code"], "MCP_GO_CIMD_URL_CONTAINS_FRAGMENT")

        # PR-10
        r10_bad = evaluate_mcp_go_listen_subscription_stateless_recovery_guard(
            active_listener_id="gen2",
            retiring_listener_id="gen1",
            retired_active_subscription=True,
            stateless_client_prev_req_failed=False,
            stateless_client_next_req_blocked=False,
        )
        self.assertFalse(r10_bad["admitted"])
        self.assertEqual(r10_bad["decision_code"], "MCP_GO_FOREIGN_LISTENER_SUBSCRIPTION_RETIRED")

        # PR-11
        r11_bad = evaluate_mcp_rust_eof_token_cancel_20260728_s2c_guard(
            transport_eof_reached=False,
            response_drain_completed=False,
            service_loop_token_cancelled=False,
            pending_handlers_cancelled=0,
            pending_handlers_total=0,
            protocol_version="2026-07-28",
            is_stateless_http=True,
            server_to_client_request_attempted=True,
        )
        self.assertFalse(r11_bad["admitted"])
        self.assertEqual(r11_bad["decision_code"], "MCP_RUST_20260728_SERVER_TO_CLIENT_REQUEST_REJECTED")

        # PR-12
        r12_bad = evaluate_mcp_rust_session_lock_release_origin_guard(
            session_handle_cloned_before_await=False,
            rwlock_held_across_worker_await=True,
            concurrent_ping_latency_ms=2600.0,
            max_ping_latency_ms=50.0,
            origin_header="https://app.example.com",
            allowed_origins={"https://app.example.com"},
        )
        self.assertFalse(r12_bad["admitted"])
        self.assertEqual(r12_bad["decision_code"], "MCP_RUST_SESSION_MAP_RWLOCK_HELD_ACROSS_AWAIT")

        # PR-13
        r13_bad = evaluate_mcp_csharp_entra_refresh_fallback_init_params_guard(
            initialize_params_valid=True,
            initialize_error_http_status=200,
            initialize_error_jsonrpc_code=0,
            first_refresh_sent_resource=True,
            first_refresh_http_status=400,
            first_refresh_oauth_error="invalid_grant",
            retried_without_resource=True,
        )
        self.assertFalse(r13_bad["admitted"])
        self.assertEqual(r13_bad["decision_code"], "MCP_CSHARP_DEAD_REFRESH_TOKEN_INVALID_GRANT_RETRIED")

        # PR-14
        r14_bad = evaluate_mcp_csharp_session_affinity_content_length_filter_guard(
            session_found=False,
            unknown_session_http_status=404,
            unknown_session_jsonrpc_code=-32001,
            unknown_session_message="Session not found",
            post_uses_content_length=True,
            post_uses_chunked_encoding=False,
            call_tool_filter_allowed=True,
            tool_dispatched_over_wire=True,
        )
        self.assertFalse(r14_bad["admitted"])
        self.assertEqual(r14_bad["decision_code"], "MCP_CSHARP_OPAQUE_SESSION_NOT_FOUND_ERROR")

        # PR-15
        r15_bad = evaluate_mcp_java_stdio_per_message_sse_commit_guard(
            prior_message_threw_error=True,
            stdio_stream_terminated=True,
            subsequent_ping_answered=False,
            sse_get_response_committed_before_first_event=True,
        )
        self.assertFalse(r15_bad["admitted"])
        self.assertEqual(r15_bad["decision_code"], "MCP_JAVA_STDIO_FLATMAP_STREAM_KILLED_BY_SINGLE_MESSAGE_ERROR")

        # PR-16
        r16_bad = evaluate_mcp_java_wildcard_numeric_port_session_sweep_guard(
            wildcard_pattern="http://localhost:*",
            candidate_host_or_origin="http://localhost:3000.evil.com",
            idle_session_expired=True,
            session_has_active_stream=False,
            session_evicted_by_sweeper=True,
        )
        self.assertFalse(r16_bad["admitted"])
        self.assertEqual(r16_bad["decision_code"], "MCP_JAVA_WILDCARD_PORT_NON_NUMERIC_SUFFIX_REJECTED")


if __name__ == "__main__":
    unittest.main()
