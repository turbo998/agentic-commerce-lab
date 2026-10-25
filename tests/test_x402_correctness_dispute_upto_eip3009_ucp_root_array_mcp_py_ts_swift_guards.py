"""Unit tests for Stage 240 (240-Stage Milestone!) deterministic protocol guards (`PR-01..PR-16`)."""

from __future__ import annotations

import unittest

from lab.x402_correctness_dispute_upto_eip3009_ucp_root_array_mcp_py_ts_swift_guards import (
    UPTO_EIP3009_PREAUDIT_PROXY,
    evaluate_mcp_python_oauth_token_revoke_error_guard,
    evaluate_mcp_python_return_annotation_and_schema_title_guard,
    evaluate_mcp_python_sse_head_method_guard,
    evaluate_mcp_swift_session_recovery_quoted_pair_pkce_guard,
    evaluate_mcp_swift_stateless_cancel_and_stdio_flags_guard,
    evaluate_mcp_ts_abort_cleanup_and_stdio_drain_guard,
    evaluate_mcp_ts_cache_generation_and_atomic_tool_metadata_guard,
    evaluate_mcp_ts_id_types_sampling_context_and_header_ascii_guard,
    evaluate_mcp_ts_ref_object_schema_and_prompt_icons_guard,
    evaluate_mcp_ts_refresh_scope_unread_body_and_exact_uri_guard,
    evaluate_ucp_root_array_schema_and_release_hygiene_guard,
    evaluate_x402_batch_refund_settle_paywall_xss_replay_guard,
    evaluate_x402_correctness_dispute_bonded_verdict_guard,
    evaluate_x402_evm_upto_eip3009_proxy_guard,
    evaluate_x402_go_wildcard_scheme_and_stellar_contract_guard,
    evaluate_x402_java_dot_decode_and_legacy_raw_route_guard,
)


class Stage240GuardsTest(unittest.TestCase):
    def test_pr01_to_pr08_x402_ucp_and_mcp_python_guards(self) -> None:
        g1 = evaluate_x402_correctness_dispute_bonded_verdict_guard(
            resolver="did:web:notary.stillos.xyz",
            ed25519_signature_valid=True,
            prev_verdict_hash="sha256:88aa11",
            expected_prev_verdict_hash="sha256:88aa11",
            bond_balance_minor=150_000,
            slashed_total_minor=20_000,
            per_verdict_max_minor=50_000,
            disputed_claim_minor=45_000,
        )
        self.assertTrue(g1.passed)
        self.assertEqual(g1.code, "X402_DISPUTE_BONDED_VERDICT_OK")

        g2 = evaluate_x402_evm_upto_eip3009_proxy_guard(
            proxy_address=UPTO_EIP3009_PREAUDIT_PROXY,
            authorization_method="receiveWithAuthorization",
            nonce_matches_payto_settler_salt=True,
            caller_address="0x1111111111111111111111111111111111111111",
            committed_settler="0x1111111111111111111111111111111111111111",
            signed_maximum_minor=10_000,
            actual_amount_minor=6_500,
            payer_balance_minor=10_000,
            merchant_paid_minor=6_500,
            payer_refunded_minor=3_500,
        )
        self.assertTrue(g2.passed)
        self.assertEqual(g2.code, "X402_UPTO_EIP3009_PROXY_OK")

        g3 = evaluate_x402_java_dot_decode_and_legacy_raw_route_guard(
            raw_request_path="/api/users/a%2Fb",
            protected_exact_paths={"/private"},
            protected_param_patterns=("/api/users/[id]",),
            payment_present=False,
        )
        self.assertFalse(g3.passed)
        self.assertEqual(g3.code, "X402_PATH_TRAVERSAL_OR_ENCODED_PARAM_402_REQUIRED")

        g4 = evaluate_x402_go_wildcard_scheme_and_stellar_contract_guard(
            registered_schemes={
                "eip155:*": {"hooks": ["BeforeVerify"]},
                "eip155:8453": {"hooks": [], "inherited_wildcard_hooks": False},
            },
            requested_network="eip155:8453",
            stellar_payer_account="CD752A22JHVS7ZWDRBFPLNMNTLVCWZAO4EZUZN7FHYA76V362MON7MHZ",
            has_custom_authorize_entry=True,
            stellar_upto_actual_minor=500,
            stellar_upto_max_minor=1_000,
        )
        self.assertTrue(g4.passed)
        self.assertEqual(g4.code, "X402_GO_WILDCARD_AND_STELLAR_CONTRACT_OK")

        g5 = evaluate_x402_batch_refund_settle_paywall_xss_replay_guard(
            total_claimed_minor=3_000,
            total_settled_minor=3_000,
            facilitator_err="invalid_batch_settlement_evm_nothing_to_settle",
            on_settle_called_on_empty_tx=False,
            paywall_serialized_json='{"appName":"\\u003c/script\\u003e"}',
            payment_payload_hash="sha256:99ff01",
            seen_payload_hashes=set(),
        )
        self.assertTrue(g5.passed)
        self.assertEqual(g5.code, "X402_BATCH_SETTLE_PAYWALL_XSS_REPLAY_OK")

        g6 = evaluate_ucp_root_array_schema_and_release_hygiene_guard(
            schema_kind="capability",
            root_schema_type="object",
            shared_contains_constraint=False,
            source_map_js_version=(1, 2, 2),
            media_variants_backported_branches={"release/2026-08-25", "release/2026-04-08"},
            site_base_path="/ucp",
            raw_doc_link="/ucp/specification/ucp/overview",
            stripped_doc_link="/specification/ucp/overview",
        )
        self.assertTrue(g6.passed)
        self.assertEqual(g6.code, "UCP_ROOT_ARRAY_AND_RELEASE_HYGIENE_OK")

        g7 = evaluate_mcp_python_sse_head_method_guard(
            http_method="HEAD",
            auth_configured=True,
            is_authenticated=True,
            status_code=405,
            allow_header="GET",
            sse_stream_opened=False,
        )
        self.assertTrue(g7.passed)
        self.assertEqual(g7.code, "MCP_PY_SSE_HEAD_GUARD_OK")

        g8 = evaluate_mcp_python_return_annotation_and_schema_title_guard(
            return_annotation="dict",
            structured_output_opt_in=False,
            published_output_schema={"type": "object", "additionalProperties": True},
            tool_input_schema={
                "type": "object",
                "properties": {"query": {"type": "string", "title": "Custom Query"}},
            },
            explicit_field_titles={"query"},
        )
        self.assertTrue(g8.passed)
        self.assertEqual(g8.code, "MCP_PY_STRUCTURED_OUTPUT_AND_TITLE_STRIP_OK")

    def test_pr09_to_pr16_mcp_python_ts_and_swift_sdk_guards(self) -> None:
        g9 = evaluate_mcp_python_oauth_token_revoke_error_guard(
            endpoint="/revoke",
            grant_type=None,
            server_supported_grants={"authorization_code"},
            client_registered_grants={"authorization_code"},
            client_auth_succeeded=False,
            used_basic_auth_header=True,
            returned_error_code="invalid_client",
            www_authenticate_header='Basic realm="OAuth"',
        )
        self.assertTrue(g9.passed)
        self.assertEqual(g9.code, "MCP_PY_OAUTH_ERROR_CODES_OK")

        g10 = evaluate_mcp_ts_ref_object_schema_and_prompt_icons_guard(
            output_schema={
                "$ref": "#/$defs/ResultUnion",
                "$defs": {
                    "ResultUnion": {
                        "oneOf": [
                            {"properties": {"kind": {"const": "ok"}}},
                            {"properties": {"kind": {"const": "err"}}},
                        ]
                    }
                },
            },
            prompt_icons_preserved=True,
        )
        self.assertTrue(g10.passed)
        self.assertEqual(g10.code, "MCP_TS_REF_OBJECT_SCHEMA_AND_PROMPT_ICONS_OK")

        g11 = evaluate_mcp_ts_cache_generation_and_atomic_tool_metadata_guard(
            pre_reset_max_generation=4,
            post_reset_generation_base=5,
            current_key_generation=5,
            write_captured_generation=5,
            write_accepted=True,
            malformed_schema_mid_loop=True,
            previous_tool_cache_preserved=True,
        )
        self.assertTrue(g11.passed)
        self.assertEqual(g11.code, "MCP_TS_CACHE_GENERATION_AND_ATOMIC_METADATA_OK")

        g12 = evaluate_mcp_ts_abort_cleanup_and_stdio_drain_guard(
            response_received=True,
            late_abort_sent_cancelled_notification=False,
            abort_listener_removed_on_finally=True,
            concurrent_backpressured_sends=27,
            stdin_drain_listener_count=1,
            process_exited_before_close=True,
            late_send_rejected_not_connected=True,
            waiting_sends_settled_on_exit=True,
        )
        self.assertTrue(g12.passed)
        self.assertEqual(g12.code, "MCP_TS_ABORT_AND_STDIO_DRAIN_OK")

        g13 = evaluate_mcp_ts_refresh_scope_unread_body_and_exact_uri_guard(
            scope_for_refresh="mcp:tools",
            sent_refresh_scope="mcp:tools",
            server_returned_scope=None,
            resulting_token_scope="mcp:tools",
            awaited_unread_post_body=False,
            registered_resources={
                "https://example.com": {"enabled": True},
                "https://example.com/": {"enabled": True},
            },
            requested_resource_uri="https://example.com",
            served_resource_key="https://example.com",
        )
        self.assertTrue(g13.passed)
        self.assertEqual(g13.code, "MCP_TS_REFRESH_SCOPE_RELEASE_BODY_EXACT_URI_OK")

        g14 = evaluate_mcp_ts_id_types_sampling_context_and_header_ascii_guard(
            pending_request_id=0,
            incoming_response_id="0",
            correlated_as_match=False,
            negotiated_protocol_version="2025-11-25",
            include_context="thisServer",
            client_has_sampling_context_cap=True,
            sampling_request_allowed=True,
            plain_mcp_header_value="caf\xe9",
            header_rejected_with_minus_32020=True,
        )
        self.assertTrue(g14.passed)
        self.assertEqual(g14.code, "MCP_TS_ID_TYPES_SAMPLING_CONTEXT_HEADER_ASCII_OK")

        g15 = evaluate_mcp_swift_session_recovery_quoted_pair_pkce_guard(
            previous_session_deleted=True,
            reinitialize_succeeded=True,
            active_sessions=4,
            max_sessions=8,
            at_capacity_status_code=200,
            raw_quoted_param=r"read\\write\_\"ok\"",
            parsed_quoted_param='read\\write_"ok"',
            pkce_rejection_threshold_byte=197,
            client_id="client:1",
            client_secret="sec/2",
            encoded_basic_pair="client%3A1:sec%2F2",
        )
        self.assertTrue(g15.passed)
        self.assertEqual(g15.code, "MCP_SWIFT_SESSION_QUOTED_PAIR_PKCE_OK")

        g16 = evaluate_mcp_swift_stateless_cancel_and_stdio_flags_guard(
            stateless_requests_use_private_internal_ids=True,
            response_restored_original_client_id=True,
            ambiguous_cancel_terminated_sibling_request=False,
            cancel_post_status_code=202,
            client_accepts_sse=True,
            cancelled_original_post_outcome="empty_sse",
            stdio_changed_blocking_mode=True,
            inflight_io_drained_before_restore=True,
            stdio_blocking_mode_restored_on_disconnect=True,
        )
        self.assertTrue(g16.passed)
        self.assertEqual(g16.code, "MCP_SWIFT_STATELESS_CANCEL_AND_STDIO_FLAGS_OK")


if __name__ == "__main__":
    unittest.main()
