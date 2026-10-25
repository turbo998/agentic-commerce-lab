"""Unit tests for Stage 278–279 protocol & security guards and 7-Card benchmark."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.x402_eip3009_sar_ucp_rfc9421_acp_idempotency_a2a_cgnat_stripe_mcp_bench import run_benchmark
from lab.x402_eip3009_sar_ucp_rfc9421_acp_idempotency_a2a_cgnat_stripe_mcp_guards import (
    STAGE_278_PR_CITATIONS,
    evaluate_a2a_multi_sdk_trailing_json_unicode_tenant_guard,
    evaluate_a2a_python_cgnat_ssrf_card_canon_terminal_guard,
    evaluate_acp_mcp_idempotency_delegate_sig_spend_guard,
    evaluate_agentkit_receipt_cbbtc_spl_prepayment_guard,
    evaluate_mcp_csharp_rust_pkce_sessionless_post_guard,
    evaluate_mcp_go_idjag_discover_auth_int_id_guard,
    evaluate_mcp_inspector_registry_dcr_stamp_gitlab_io_guard,
    evaluate_mcp_java_kotlin_exception_scrub_sep2243_uri_guard,
    evaluate_mcp_python_uri_utf8_exact_expiry_sse_headers_guard,
    evaluate_mcp_ts_null_proto_reconnect_cache_header_guard,
    evaluate_stripe_cli_path_escape_plugin_reap_mcp_guard,
    evaluate_stripe_multi_sdk_blank_secret_retry_idempotency_guard,
    evaluate_ucp_conformance_samples_webhook_checkout_guard,
    evaluate_ucp_python_sdk_dependent_jwk_bounds_guard,
    evaluate_ucp_rfc9421_raw_rs_return_root_array_guard,
    evaluate_x402_eip3009_domain_sar_extensions_guard,
)


class TestStage278And279GuardsAndBench(unittest.TestCase):
    def test_stage_278_pr_citation_inventory(self) -> None:
        self.assertEqual(len(STAGE_278_PR_CITATIONS), 16)
        total = sum(len(v) for v in STAGE_278_PR_CITATIONS.values())
        self.assertEqual(total, 238)

    def test_x402_agentkit_ucp_acp_and_a2a_guards_pr01_to_pr08(self) -> None:
        d1_bad = evaluate_x402_eip3009_domain_sar_extensions_guard(
            eip712_domain={"name": "USD Coin", "version": "2", "chainId": 1, "verifyingContract": "0xWrong"},
            expected_chain_id=8453,
            expected_verifying_contract="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            sar_receipt={"tx_hash": "0x1"},
            owner_consented_solidarity_bps=500,
        )
        self.assertFalse(d1_bad.admitted)
        self.assertEqual(d1_bad.code, "X402_EIP3009_DOMAIN_MISMATCH")

        d2_bad = evaluate_agentkit_receipt_cbbtc_spl_prepayment_guard(
            erc20_receipt_status="1",
            userop_reverted_in_bundle=False,
            asset_symbol="cbBTC",
            resolved_decimals=8,
            spl_raw_amount="100",
            pre_payment_check_passed=True,
            canary_prompt_injection_detected=False,
            token_risk_verdict="safe",
        )
        self.assertFalse(d2_bad.admitted)
        self.assertEqual(d2_bad.code, "AGENTKIT_ERC20_RECEIPT_STATUS_FAILED")

        d3_bad = evaluate_ucp_rfc9421_raw_rs_return_root_array_guard(
            ecdsa_p256_signature_bytes=b"\x30\x44" + b"\x01" * 62,
            return_eligible=True,
            return_requested_at_epoch=100,
            business_return_deadline_epoch=200,
            return_fee_minor=0,
            fulfillment_event_type="delivered",
            schema_root_type="object",
        )
        self.assertFalse(d3_bad.admitted)
        self.assertEqual(d3_bad.code, "UCP_RFC9421_ECDSA_DER_OR_LENGTH_INVALID")

        d4_ok = evaluate_ucp_python_sdk_dependent_jwk_bounds_guard(
            payload={"a": 1, "b": 2},
            dependent_required={"a": ["b"]},
            max_properties=4,
            allowed_fields={"a", "b"},
            jwk={"kty": "EC", "crv": "P-256", "x": "1", "y": "2"},
            datetime_field_has_regex_pattern=False,
        )
        self.assertTrue(d4_ok.admitted)

        d5_bad = evaluate_ucp_conformance_samples_webhook_checkout_guard(
            discovery_url="https://merchant.example/.well-known/ucp",
            fixture_allowlist_hosts=set(),
            webhook_payload_event_type="order.created",
            relied_on_x_event_type_header=False,
            used_legacy_ucp_keys_mirror=False,
            payment_instruments_count=2,
            missing_catalog_product_ids=[],
        )
        self.assertFalse(d5_bad.admitted)
        self.assertEqual(d5_bad.code, "UCP_MULTIPLE_PAYMENT_INSTRUMENTS_REJECTED")

        d6_bad = evaluate_acp_mcp_idempotency_delegate_sig_spend_guard(
            is_mutating_mcp_checkout_tool=True,
            idempotency_key=None,
            delegate_endpoint="delegate_payment",
            signature_header="sig",
            timestamp_header="123",
            requires_spend_step=True,
            host_spend_authorized=True,
        )
        self.assertFalse(d6_bad.admitted)
        self.assertEqual(d6_bad.code, "ACP_MCP_IDEMPOTENCY_KEY_MISSING")

        d7_bad = evaluate_a2a_python_cgnat_ssrf_card_canon_terminal_guard(
            push_webhook_ip="100.100.10.5",
            agent_card_fields_preserved_before_jcs=True,
            malformed_sig_headers_skipped=True,
            is_terminal_task_state=True,
            status_timestamp_stamped=True,
            parked_interrupted_age_s=10.0,
            parked_timeout_s=60.0,
            parked_task_released=False,
        )
        self.assertFalse(d7_bad.admitted)
        self.assertEqual(d7_bad.code, "A2A_PY_SHARED_OR_PRIVATE_SSRF_BLOCKED")

        d8_bad = evaluate_a2a_multi_sdk_trailing_json_unicode_tenant_guard(
            raw_json_body='{"a":1} trailing',
            text_to_sign="ok",
            client_supplied_tenant=None,
            effective_tenant="t1",
            authenticated_tenant="t1",
            push_delete_config_id="cfg_1",
            incomplete_sse_discarded_at_eof=True,
            page_size=20,
        )
        self.assertFalse(d8_bad.admitted)
        self.assertEqual(d8_bad.code, "A2A_GO_TRAILING_JSON_DATA_REJECTED")

    def test_stripe_and_mcp_guards_pr09_to_pr16(self) -> None:
        d9_bad = evaluate_stripe_cli_path_escape_plugin_reap_mcp_guard(
            resource_id="cus_1/../admin",
            rendered_api_path="/v1/customers/cus_1/../admin",
            parent_terminated_abnormally=False,
            peer_plugins_reaped=True,
            auto_upgraded_across_major=False,
            mcp_forward_failed=False,
            mcp_error_reply_sent=True,
            abandoned_stream_stopped=True,
        )
        self.assertFalse(d9_bad.admitted)
        self.assertEqual(d9_bad.code, "STRIPE_CLI_UNESCAPED_RESOURCE_ID")

        d10_bad = evaluate_stripe_multi_sdk_blank_secret_retry_idempotency_guard(
            webhook_secrets_by_sdk={"stripe-go": ""},
            node_verify_tolerance_s=300,
            php_retry_idempotency_keys=["k1", "k1"],
            dotnet_used_ordinal_path_comparison=True,
            ruby_singleton_v2_called=False,
            ruby_singleton_v2_raised_error=False,
        )
        self.assertFalse(d10_bad.admitted)
        self.assertEqual(d10_bad.code, "STRIPE_SDK_BLANK_WEBHOOK_SECRET_REJECTED")

        d11_bad = evaluate_mcp_ts_null_proto_reconnect_cache_header_guard(
            registry_uses_null_prototype=True,
            requested_tool_name="pay",
            cache_write_epoch_gen=3,
            current_reconnect_epoch_gen=4,
            mcp_param_value="ok",
            mcp_name_value="ok",
            handshake_elapsed_ms=50,
            max_handshake_timeout_ms=1000,
        )
        self.assertFalse(d11_bad.admitted)
        self.assertEqual(d11_bad.code, "MCP_TS_STALE_RECONNECT_CACHE_WRITE")

        d12_bad = evaluate_mcp_python_uri_utf8_exact_expiry_sse_headers_guard(
            candidate_uri="mcp://item/%FF",
            token_now_epoch=10.0,
            token_expires_at_epoch=20.0,
            sse_response_headers_shared_ref=False,
            contains_lone_surrogate=False,
            lone_surrogate_contained=True,
            unknown_tool_error_code=-32602,
        )
        self.assertFalse(d12_bad.admitted)
        self.assertEqual(d12_bad.code, "MCP_PY_URI_NON_UTF8_PERCENT_ESCAPE")

        d13_bad = evaluate_mcp_go_idjag_discover_auth_int_id_guard(
            id_jag_target="https://auth.example",
            trusted_mcp_auth_server="https://auth.example",
            discover_auth_failed=True,
            fell_back_to_initialize=True,
            request_id_raw="10",
            is_error_result=False,
            error_result_has_structured_output=False,
            forbidden_www_authenticate_header="insufficient_scope",
        )
        self.assertFalse(d13_bad.admitted)
        self.assertEqual(d13_bad.code, "MCP_GO_DISCOVER_AUTH_FALLBACK_FORBIDDEN")

        d14_bad = evaluate_mcp_csharp_rust_pkce_sessionless_post_guard(
            oauth_issuer="https://idp.example",
            expected_issuer="https://idp.example",
            pkce_methods_supported=["S256"],
            property_case_matched_strictly=True,
            routing_method_name="tools/call",
            is_initialize_request=False,
            has_mcp_session_id=False,
            sessionless_post_http_status=200,
            jsonrpc_error_http_status=401,
        )
        self.assertFalse(d14_bad.admitted)
        self.assertEqual(d14_bad.code, "MCP_RUST_SESSIONLESS_POST_MUST_400")

        d15_bad = evaluate_mcp_java_kotlin_exception_scrub_sep2243_uri_guard(
            error_response_contains_aggregate_exception=True,
            post_content_type="application/json",
            jsonrpc_version="2.0",
            sep2243_headers_valid=True,
            resource_uri="mcp://x",
            template_captures={"id": "1"},
        )
        self.assertFalse(d15_bad.admitted)
        self.assertEqual(d15_bad.code, "MCP_JAVA_AGGREGATE_EXCEPTION_LEAKED")

        d16_bad = evaluate_mcp_inspector_registry_dcr_stamp_gitlab_io_guard(
            dcr_secret_stamped_client_id="c1",
            active_client_id="c1",
            bind_host="127.0.0.1",
            auth_token_enabled=True,
            vite_cors_origin="http://localhost:6274",
            configured_cors_origins={"http://localhost:6274"},
            oversize_relay_stripped_framing_headers=True,
            registry_verify_domain="team.gitlab.io",
            recorded_repository_id=123,
        )
        self.assertFalse(d16_bad.admitted)
        self.assertEqual(d16_bad.code, "MCP_REGISTRY_GITLAB_IO_DOMAIN_REJECTED")

    def test_stage_279_benchmark_report_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            rep = run_benchmark(out_dir)
            self.assertEqual(rep["total_scenarios"], 16)
            self.assertEqual(rep["ai_native_passed"], 16)
            self.assertEqual(rep["classic_3tier_passed"], 2)
            self.assertEqual(rep["total_primary_source_prs"], 238)
            self.assertTrue((out_dir / "report.json").exists())
            self.assertTrue((out_dir / "index.html").exists())
            self.assertTrue((out_dir / "index.en.html").exists())
            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", en_html)
            self.assertIn("7 / 7 · MY TAKE", en_html)


if __name__ == "__main__":
    unittest.main()
