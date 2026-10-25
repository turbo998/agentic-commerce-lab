"""Unit tests for Stage 284 guards and Stage 285 16-scenario 7-Card benchmark (404 zero-overlap PRs across 50 repos)."""

from __future__ import annotations

import glob
import re
import tempfile
import unittest
from pathlib import Path

from lab.x402_erc8021_mppx_atomic_ap2_kb_ucp_loyalty_acp_feeds_a2a_stripe_mcp_bench import (
    run_stage285_benchmark,
)
from lab.x402_erc8021_mppx_atomic_ap2_kb_ucp_loyalty_acp_feeds_a2a_stripe_mcp_guards import (
    STAGE284_PR_GROUPS,
    evaluate_a2a_get_subscribe_push_copy_guard,
    evaluate_a2a_go_nil_marshal_java_tenant_guard,
    evaluate_a2a_x402_interline_timeout_guard,
    evaluate_acp_swagger_feeds_fulfillment_guard,
    evaluate_agentkit_ssh_uniswap_tau2_voice_guard,
    evaluate_mcp_csharp_hybrid_swift_backpressure_guard,
    evaluate_mcp_go_lazy_rust_cache_java_sweep_guard,
    evaluate_mcp_php_lock_ruby_null_id_inspector_redact_guard,
    evaluate_mcp_sep3221_py_405_ts_buffer_guard,
    evaluate_mppx_atomic_claim_tempo_reth_guard,
    evaluate_sdjwt_alg_wba_component_ext_auth_guard,
    evaluate_stripe_7sdk_v2_search_list_guard,
    evaluate_stripe_synaptic_hermes_oauth_guard,
    evaluate_ucp_loyalty_measure_idempotency_guard,
    evaluate_visa_mcp_vic_ap2_delegation_guard,
    evaluate_x402_rs_erc8021_caip_guard,
)


class Stage284GuardsAndStage285BenchmarkTests(unittest.TestCase):
    def test_stage284_pr_groups_have_404_unique_prs_across_50_repos_with_zero_overlap(self) -> None:
        self.assertEqual(len(STAGE284_PR_GROUPS), 16)
        stage284_prs = [pr for prs in STAGE284_PR_GROUPS.values() for pr in prs]
        self.assertEqual(len(stage284_prs), 404)
        self.assertEqual(len(set(stage284_prs)), 404)
        repos = {pr.split("#")[0] for pr in stage284_prs}
        self.assertEqual(len(repos), 50)

        prior_prs: set[str] = set()
        for path_str in glob.glob("lab/*guards.py"):
            p = Path(path_str)
            if p.name == "x402_erc8021_mppx_atomic_ap2_kb_ucp_loyalty_acp_feeds_a2a_stripe_mcp_guards.py":
                continue
            txt = p.read_text(encoding="utf-8")
            for m in re.finditer(r"([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)#(\d+)", txt):
                prior_prs.add(f"{m.group(1)}#{m.group(2)}")

        overlap = set(stage284_prs) & prior_prs
        self.assertEqual(overlap, set(), f"Found unexpected overlap with prior stages: {overlap}")

    def test_payment_mandate_ucp_acp_guards_block_attacks_and_admit_remediated(self) -> None:
        self.assertFalse(
            evaluate_a2a_x402_interline_timeout_guard(
                payment_timeout_seconds=0,
                non_custodial_interline_router=True,
                trust_receipt_verified=True,
            ).passed
        )
        self.assertTrue(
            evaluate_a2a_x402_interline_timeout_guard(
                payment_timeout_seconds=120,
                non_custodial_interline_router=True,
                trust_receipt_verified=True,
            ).passed
        )
        self.assertFalse(
            evaluate_x402_rs_erc8021_caip_guard(
                erc8021_attribution_tag_appended=False,
                malformed_money_amount_rejected=True,
                caip27_uses_chain_id_key=True,
                permit2_eip2612_metadata_valid=True,
            ).passed
        )
        self.assertFalse(
            evaluate_mppx_atomic_claim_tempo_reth_guard(
                scheduled_settlement_claimed_atomically=True,
                chain_state_refreshed_before_voucher_accept=False,
                shared_replay_store_enabled=True,
                reth_persisted_before_finalized_ack=True,
            ).passed
        )
        self.assertFalse(
            evaluate_visa_mcp_vic_ap2_delegation_guard(
                vic_card_response_validated=True,
                sdjwt_delegation_chain_decoded=True,
                every_kb_hop_aud_nonce_verified=False,
                x402_psp_fails_closed_without_provider_key=True,
            ).passed
        )
        self.assertFalse(
            evaluate_sdjwt_alg_wba_component_ext_auth_guard(
                sd_alg_in_iana_registry=True,
                unreferenced_or_reserved_disclosures_rejected=True,
                duplicate_wba_covered_components_rejected=False,
                wba_alg_matches_resolved_key=True,
                id_jag_04_aligned=True,
            ).passed
        )
        self.assertFalse(
            evaluate_ucp_loyalty_measure_idempotency_guard(
                non_public_lockfile_registries_blocked=False,
                measure_integer_and_max_properties_enforced=True,
                complete_checkout_bound_to_request_body=True,
                cart_idempotency_scoped_to_op_and_cart=True,
            ).passed
        )
        self.assertFalse(
            evaluate_acp_swagger_feeds_fulfillment_guard(
                openapi_swagger_semantic_valid=False,
                fulfillment_details_allowed_on_complete=True,
                product_feeds_and_promotions_valid=True,
                cart_capability_schema_valid=True,
            ).passed
        )

    def test_a2a_stripe_agentkit_mcp_guards_block_attacks_and_admit_remediated(self) -> None:
        self.assertFalse(
            evaluate_a2a_get_subscribe_push_copy_guard(
                subscribe_to_task_http_method="POST",
                push_configs_deep_copied=True,
                unspecified_state_is_non_terminal=True,
                js_sse_throws_typed_a2a_error=True,
            ).passed
        )
        self.assertFalse(
            evaluate_a2a_go_nil_marshal_java_tenant_guard(
                nil_typed_marshal_handled=True,
                pre_first_event_stream_error_plain=True,
                task_timestamps_serialized_utc=True,
                java_per_tenant_routing_isolated=False,
            ).passed
        )
        self.assertFalse(
            evaluate_stripe_synaptic_hermes_oauth_guard(
                no_content_generated_throws_error=False,
                hermes_plugin_skills_hardened=True,
                ignored_config_key_warned=True,
                cli_multi_oauth_profiles_isolated=True,
            ).passed
        )
        self.assertFalse(
            evaluate_stripe_7sdk_v2_search_list_guard(
                v2_search_supported_across_sdks=True,
                node_v2_list_cjs_exports_present=True,
                node_fetch_response_disposed=False,
                ruby_wif_trusted_publishing_enabled=True,
            ).passed
        )
        self.assertFalse(
            evaluate_agentkit_ssh_uniswap_tau2_voice_guard(
                ssh_paths_confined_to_cwd_or_dot_ssh=False,
                non_https_remote_image_rejected=True,
                zero_or_missing_uniswap_quote_fails_closed=True,
                tau2_voice_call_quality_verified=True,
            ).passed
        )
        self.assertFalse(
            evaluate_mcp_sep3221_py_405_ts_buffer_guard(
                sep3221_secure_parameters_redacted=False,
                stateless_listen_get_returns_405=True,
                auth_endpoint_existing_query_preserved=True,
                ts_consumed_read_buffer_released=True,
            ).passed
        )
        self.assertFalse(
            evaluate_mcp_go_lazy_rust_cache_java_sweep_guard(
                go_cancelled_stdio_2026_sends_no_response=True,
                go_retires_only_own_listen_subscriptions=True,
                rust_empty_cache_scope_treated_as_omitted=False,
                java_last_event_id_stream_leak_closed=True,
            ).passed
        )
        self.assertFalse(
            evaluate_mcp_csharp_hybrid_swift_backpressure_guard(
                csharp_streamable_http_status_deterministic=True,
                swift_stdio_backpressure_frames_isolated=False,
                swift_early_cancellation_race_resolved=True,
                swift_client_loop_terminates_on_stream_end=True,
            ).passed
        )
        self.assertFalse(
            evaluate_mcp_php_lock_ruby_null_id_inspector_redact_guard(
                php_resumed_fiber_writes_saved_with_lock=True,
                ruby_null_request_id_rejected=False,
                conformance_stateless_result_type_stamped=True,
                inspector_url_query_secrets_redacted=True,
            ).passed
        )

    def test_stage285_benchmark_generates_7card_bilingual_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            summary = run_stage285_benchmark(tmp)
            self.assertEqual(summary["total_scenarios"], 16)
            self.assertEqual(summary["attack_blocked_count"], 16)
            self.assertEqual(summary["remediated_passed_count"], 16)
            self.assertEqual(summary["total_unique_prs"], 404)
            self.assertEqual(summary["total_unique_repos"], 50)

            zh_html = (Path(tmp) / "index.html").read_text(encoding="utf-8")
            en_html = (Path(tmp) / "index.en.html").read_text(encoding="utf-8")
            for k in range(1, 8):
                self.assertIn(f"{k} / 7 ·", zh_html)
                self.assertIn(f"{k} / 7 ·", en_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)


if __name__ == "__main__":
    unittest.main()
