"""Unit tests for Stage 238 deterministic protocol & security guards (`PR-01..PR-16`)."""

from __future__ import annotations

import unittest

from lab.x402_v1_filter_mcp_accepts_bch_agentkit_compliance_mcp_ts_go_rust_csharp_kotlin_inspector_guards import (
    evaluate_agentkit_stablecoin_compliance_and_mizan_zk_guard,
    evaluate_agentkit_x402_hook_base_units_and_erc4337_receipt_guard,
    evaluate_mcp_csharp_oauth_state_cancellation_and_id_jag_guard,
    evaluate_mcp_go_jsonrpc_id_precision_and_error_response_guard,
    evaluate_mcp_go_logging_session_header_schema_and_sse_context_guard,
    evaluate_mcp_go_redirect_origin_bearer_metadata_and_aud_guard,
    evaluate_mcp_kotlin_init_buffer_rfc3986_and_inspector_security_guard,
    evaluate_mcp_rust_per_request_schema_host_and_cancel_guard,
    evaluate_mcp_rust_www_authenticate_dcr_scope_and_4xx_guard,
    evaluate_mcp_ts_auth_encoding_null_proto_and_local_ref_guard,
    evaluate_mcp_ts_sampling_history_abort_and_tool_snapshot_guard,
    evaluate_stage238_239_all_15_guards,
    evaluate_x402_bch_exact_and_php_v2_sdk_guard,
    evaluate_x402_mcp_multi_network_matching_and_test_gate_guard,
    evaluate_x402_non_object_header_and_facilitator_payload_guard,
    evaluate_x402_v1_network_filter_and_facilitator_supported_guard,
)


class Stage238GuardsTest(unittest.TestCase):
    def test_pr01_to_pr08_x402_agentkit_and_mcp_ts_guards(self) -> None:
        # PR-01: V1 network filter & facilitator /supported
        g1_ok = evaluate_x402_v1_network_filter_and_facilitator_supported_guard(
            configured_networks=["eip155:84532"],
            offer_x402_version=1,
            offer_network="base-sepolia",
            facilitator_supported_kinds=[{"x402Version": 2, "scheme": "exact", "network": "eip155:84532"}],
            facilitator_supports_v1_requirements_model=True,
        )
        self.assertTrue(g1_ok.passed)
        g1_bad = evaluate_x402_v1_network_filter_and_facilitator_supported_guard(
            configured_networks=["eip155:84532"],
            offer_x402_version=1,
            offer_network="base",
            facilitator_supported_kinds=[{"x402Version": 1, "scheme": "exact", "network": "base"}],
            facilitator_supports_v1_requirements_model=False,
        )
        self.assertFalse(g1_bad.passed)
        self.assertEqual(g1_bad.decision_code, "X402_V1_MAINNET_DOWNGRADE_ON_TESTNET_CLIENT_BLOCKED")

        # PR-02: Non-object header JSON & facilitator 500 guard
        g2_ok = evaluate_x402_non_object_header_and_facilitator_payload_guard(
            decoded_header_json={"x402Version": 2},
            payment_payload_inner={"from": "0x1"},
            requirement_network="eip155:84532",
            registered_facilitator_networks=["eip155:84532"],
            facilitator_http_status_on_invalid=400,
        )
        self.assertTrue(g2_ok.passed)
        g2_bad = evaluate_x402_non_object_header_and_facilitator_payload_guard(
            decoded_header_json=[1, 2],
            payment_payload_inner=[1, 2],
            requirement_network="eip155:8453",
            registered_facilitator_networks=["eip155:84532"],
            facilitator_http_status_on_invalid=500,
        )
        self.assertFalse(g2_bad.passed)
        self.assertEqual(g2_bad.decision_code, "X402_NON_OBJECT_PAYMENT_HEADER_JSON_REJECTED")

        # PR-03: MCP multi-network accepts matching
        g3_ok = evaluate_x402_mcp_multi_network_matching_and_test_gate_guard(
            accepts=[
                {"scheme": "exact", "network": "eip155:8453", "asset": "USDC", "payTo": "0xEvm"},
                {"scheme": "exact", "network": "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp", "asset": "USDC", "payTo": "Sol"},
            ],
            payment_payload={"accepted": {"scheme": "exact", "network": "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp"}},
            wrapper_uses_hardcoded_accepts_zero=False,
            pytest_testpaths=["tests", "mcp/tests"],
            sync_client_methods=["on_before_payment", "call_tool_with_payment"],
        )
        self.assertTrue(g3_ok.passed)
        g3_bad = evaluate_x402_mcp_multi_network_matching_and_test_gate_guard(
            accepts=[
                {"scheme": "exact", "network": "eip155:8453", "asset": "USDC", "payTo": "0xEvm"},
                {"scheme": "exact", "network": "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp", "asset": "USDC", "payTo": "Sol"},
            ],
            payment_payload={"accepted": {"scheme": "exact", "network": "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp"}},
            wrapper_uses_hardcoded_accepts_zero=True,
            pytest_testpaths=["tests"],
            sync_client_methods=[],
        )
        self.assertFalse(g3_bad.passed)
        self.assertEqual(g3_bad.decision_code, "X402_MCP_WRAPPER_HARDCODED_ACCEPTS_ZERO_BLOCKED")

        # PR-04: BCH exact & PHP v2 SDK
        g4_ok = evaluate_x402_bch_exact_and_php_v2_sdk_guard(
            bch_network="bch:mainnet",
            sighash_type=0x41,
            cashaddr_p2pkh_matches_pay_to=True,
            utxo_outpoint_unspent=True,
            fulcrum_quorum_verified=True,
            settlement_claim_already_locked=False,
            php_sdk_targets_v2_only=True,
            php_sdk_commits_vendor_dir=False,
        )
        self.assertTrue(g4_ok.passed)
        g4_bad = evaluate_x402_bch_exact_and_php_v2_sdk_guard(
            bch_network="bch:mainnet",
            sighash_type=0x01,
            cashaddr_p2pkh_matches_pay_to=True,
            utxo_outpoint_unspent=True,
            fulcrum_quorum_verified=True,
            settlement_claim_already_locked=False,
            php_sdk_targets_v2_only=True,
            php_sdk_commits_vendor_dir=False,
        )
        self.assertFalse(g4_bad.passed)
        self.assertEqual(g4_bad.decision_code, "X402_BCH_MISSING_SIGHASH_FORKID_BLOCKED")

        # PR-05 & PR-06: AgentKit compliance, MIZAN ZK, base units & ERC-4337 receipt
        g5_ok = evaluate_agentkit_stablecoin_compliance_and_mizan_zk_guard(
            ofac_address_sanctioned=False,
            counterparty_sanctions_hits=[],
            mizan_credential_status="PROVEN",
            require_proven_counterparty=True,
        )
        self.assertTrue(g5_ok.passed)
        g6_bad = evaluate_agentkit_x402_hook_base_units_and_erc4337_receipt_guard(
            before_payment_hook_approved=True,
            human_amount_str="2.01",
            token_symbol="cbBTC",
            token_decimals=8,
            submitted_base_units=201000000,
            moonwell_resolved_from_network_object=True,
            erc4337_bundle_tx_mined=True,
            erc4337_user_op_receipt_success=False,
        )
        self.assertFalse(g6_bad.passed)
        self.assertEqual(g6_bad.decision_code, "AGENTKIT_ERC4337_REVERTED_USEROP_IN_MINED_BUNDLE_BLOCKED")

        # PR-07 & PR-08: MCP TS SDK guards
        g7_bad = evaluate_mcp_ts_sampling_history_abort_and_tool_snapshot_guard(
            sampling_messages=[{"role": "assistant", "content": [{"type": "tool_use", "id": "tu_1"}]}],
            TerminationReason="abort_signal",
            error_code_emitted="RequestTimeout",
            mirror_schema_revision=2,
            validation_schema_revision=1,
        )
        self.assertFalse(g7_bad.passed)
        self.assertEqual(g7_bad.decision_code, "MCP_TS_SAMPLING_UNBALANCED_TOOL_USE_HISTORY_BLOCKED")

        g8_ok = evaluate_mcp_ts_auth_encoding_null_proto_and_local_ref_guard(
            requested_resource_url="https://host.example/mcp",
            configured_resource_url="https://host.example/mcp/",
            client_id="client:one~1",
            client_secret="sec+ret/2",
            encoded_basic_decoded_payload="client%3Aone~1:sec%2Bret%2F2",
            registry_uses_null_prototype=True,
            tool_name="constructor",
            output_schema_uses_local_ref=True,
            local_ref_target_type="object",
            classified_as_object_schema=True,
        )
        self.assertTrue(g8_ok.passed)

    def test_pr09_to_pr16_mcp_go_rust_csharp_kotlin_inspector_and_composite(self) -> None:
        g9_bad = evaluate_mcp_go_redirect_origin_bearer_metadata_and_aud_guard(
            endpoint_url="https://mcp.merchant.example/v1/mcp",
            redirect_target_url="https://evil.example/steal",
            challenges=[{"scheme": "Bearer"}],
            selected_resource_metadata_scheme="Bearer",
            token_aud="https://mcp.merchant.example/v1/mcp",
            expected_resource_aud="https://mcp.merchant.example/v1/mcp",
            token_info_user_id="u1",
        )
        self.assertFalse(g9_bad.passed)
        self.assertEqual(g9_bad.decision_code, "MCP_GO_CROSS_ORIGIN_TRANSPORT_REDIRECT_BLOCKED")

        g10_ok = evaluate_mcp_go_logging_session_header_schema_and_sse_context_guard(
            logging_transport_forwards_session_state=True,
            sse_stream_detached_from_connect_ctx=True,
            schema_has_type_array_or_bool_subschema=True,
            x_mcp_headers_extracted=True,
            sampling_tool_result_preserves_empty_text=True,
        )
        self.assertTrue(g10_ok.passed)

        g11_bad = evaluate_mcp_go_jsonrpc_id_precision_and_error_response_guard(
            raw_request_id_literal="9007199254740993.0",
            decoded_request_id=9007199254740992,
            handler_uncoded_error_rpc_code=-32603,
            marshal_failure_sent_error_response=True,
            rejected_id_returned_null_id_jsonrpc_error=True,
            null_input_request_rejected=True,
            is_error_result_has_structured_content=False,
        )
        self.assertFalse(g11_bad.passed)
        self.assertEqual(g11_bad.decision_code, "MCP_GO_JSONRPC_REQUEST_ID_FLOAT64_PRECISION_LOSS_BLOCKED")

        g12_bad = evaluate_mcp_rust_www_authenticate_dcr_scope_and_4xx_guard(
            www_authenticate_challenges_parsed_separately=False,
            selected_bearer_scope="dpop:read",
            dpop_challenge_scope="dpop:read",
            dcr_selected_auth_method="client_secret_post",
            dcr_supported_auth_methods=["client_secret_post"],
            dcr_returned_client_secret="s",
            initial_login_requested_scopes=["mcp.read"],
            challenge_requested_scopes=["mcp.read"],
            http_401_403_with_jsonrpc_body_treated_as_auth_error=True,
        )
        self.assertFalse(g12_bad.passed)
        self.assertEqual(g12_bad.decision_code, "MCP_RUST_WWW_AUTHENTICATE_CROSS_CHALLENGE_MIX_BLOCKED")

        g13_ok = evaluate_mcp_rust_per_request_schema_host_and_cancel_guard(
            per_request_tool_schema_lookup=True,
            host_header_checked_before_auth_middleware=True,
            output_schema_generated_for_serialize=True,
            peer_protocol_version="2025-11-25",
            structured_content_type="array",
            non_object_structured_content_omitted=True,
            invalid_request_reply_preserved_on_cancel=True,
            abandoned_request_sent_cancelled_notification=True,
        )
        self.assertTrue(g13_ok.passed)

        g14_bad = evaluate_mcp_csharp_oauth_state_cancellation_and_id_jag_guard(
            oauth_state_entropy_bits=256,
            oauth_state_matches_callback=True,
            additional_params_overrides_state=False,
            metadata_discovery_cancelled_rethrows_operation_canceled=True,
            discovered_issuer="https://auth.example.com",
            id_jag_token_exchange_audience="https://auth.example.com/",
        )
        self.assertFalse(g14_bad.passed)
        self.assertEqual(g14_bad.decision_code, "MCP_CSHARP_ID_JAG_AUDIENCE_TRAILING_SLASH_MISMATCH_BLOCKED")

        g15_ok = evaluate_mcp_kotlin_init_buffer_rfc3986_and_inspector_security_guard(
            kotlin_buffers_messages_during_initializing=True,
            kotlin_sse_endpoint_resolved_rfc3986=True,
            kotlin_lazy_state_message_evaluated=True,
            inspector_vite_dev_cors_restricted_to_allowed_origins=True,
            inspector_bare_403_resolves_protocol_entry=True,
            inspector_oauth_secret_carried_across_backends=True,
            inspector_strips_npm_config_allow_scripts=True,
            load_error_rate=0.001,
            load_max_error_rate=0.01,
            load_p99_ms=30.0,
            load_max_p99_ms=100.0,
        )
        self.assertTrue(g15_ok.passed)

        comp_fail = evaluate_stage238_239_all_15_guards([g10_ok, g13_ok])
        self.assertFalse(comp_fail.passed)
        self.assertEqual(comp_fail.decision_code, "STAGE238_239_COMPOSITE_GUARD_FAILED")


if __name__ == "__main__":
    unittest.main()
