"""Unit tests for Stage 286 guards and Stage 287 16-scenario 7-Card benchmark (432 zero-overlap PRs across 53 repos)."""

from __future__ import annotations

import glob
import re
import tempfile
import unittest
from pathlib import Path

from lab.x402_paygate_mppx_ws_ap2_entropy_ucp_extends_acp_bopis_a2a_stripe_mcp_bench import (
    run_stage287_benchmark,
)
from lab.x402_paygate_mppx_ws_ap2_entropy_ucp_extends_acp_bopis_a2a_stripe_mcp_guards import (
    STAGE286_PR_GROUPS,
    evaluate_a2a_card_security_direct_endpoint_guard,
    evaluate_a2a_go_terminal_error_dotnet_push_store_guard,
    evaluate_a2a_py_first_owner_js_unknown_event_guard,
    evaluate_acp_bopis_offer_expiry_wba_keyring_guard,
    evaluate_agentkit_404_method_permit2_cdp_utf8_jwt_guard,
    evaluate_ap2_entropy_sdjwt_caip380_erc7964_guard,
    evaluate_mcp_go_exact_id_rust_empty_router_csharp_guard,
    evaluate_mcp_java_concealed_chars_swift_stateless_php_ruby_guard,
    evaluate_mcp_safe_int_inspector_secret_redaction_budget_guard,
    evaluate_mcp_ts_expected_resource_py_32600_202_guard,
    evaluate_mppx_ws_bounds_decimals_tempo_rollback_guard,
    evaluate_stripe_ai_hermes_token_meter_abandoned_stream_guard,
    evaluate_stripe_ruby_gcp_wif_embedded_checkout_guard,
    evaluate_tau2_voice_submission_tau_strict_reward_guard,
    evaluate_ucp_continue_url_token_context_extends_guard,
    evaluate_x402_paygate_settle_permit2_guard,
)


class Stage286GuardsAndStage287BenchmarkTests(unittest.TestCase):
    def test_stage286_pr_groups_have_432_unique_prs_across_53_repos_with_zero_overlap(self) -> None:
        self.assertEqual(len(STAGE286_PR_GROUPS), 16)
        stage286_prs = [pr for prs in STAGE286_PR_GROUPS.values() for pr in prs]
        self.assertEqual(len(stage286_prs), 432)
        self.assertEqual(len(set(stage286_prs)), 432)
        repos = {pr.split("#")[0] for pr in stage286_prs}
        self.assertEqual(len(repos), 53)

        prior_prs: set[str] = set()
        for path_str in glob.glob("lab/*guards.py"):
            p = Path(path_str)
            if p.name == "x402_paygate_mppx_ws_ap2_entropy_ucp_extends_acp_bopis_a2a_stripe_mcp_guards.py":
                continue
            txt = p.read_text(encoding="utf-8")
            for m in re.finditer(r"([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)#(\d+)", txt):
                prior_prs.add(f"{m.group(1)}#{m.group(2)}")

        overlap = set(stage286_prs) & prior_prs
        self.assertEqual(overlap, set(), f"Found unexpected overlap with prior stages: {overlap}")

    def test_payment_mandate_ucp_acp_guards_block_attacks_and_admit_remediated(self) -> None:
        self.assertFalse(
            evaluate_x402_paygate_settle_permit2_guard(
                paygate_settle_response_success=False,
                permit2_eip2612_gas_sponsor_valid=True,
                robinhood_chain_asset_verified=True,
                v2_exact_offline_validation_passed=True,
            ).passed
        )
        self.assertTrue(
            evaluate_x402_paygate_settle_permit2_guard(
                paygate_settle_response_success=True,
                permit2_eip2612_gas_sponsor_valid=True,
                robinhood_chain_asset_verified=True,
                v2_exact_offline_validation_passed=True,
            ).passed
        )
        self.assertFalse(
            evaluate_mppx_ws_bounds_decimals_tempo_rollback_guard(
                inbound_ws_frame_bytes=131072,
                max_ws_frame_bytes=65536,
                token_decimals_verified_before_approval=True,
                stripe_session_minimum_enforced=True,
                tempo_zone_offline_rollback_recovered=True,
            ).passed
        )
        self.assertFalse(
            evaluate_ap2_entropy_sdjwt_caip380_erc7964_guard(
                checkout_hash_entropy_bits=128,
                min_entropy_bits=256,
                open_mandate_hash_v0_valid=True,
                verifier_pubkey_source_pinned=True,
                caip380_portable_proof_and_erc7964_derived=True,
            ).passed
        )
        self.assertFalse(
            evaluate_ucp_continue_url_token_context_extends_guard(
                continue_url_https_and_origin_bound=True,
                token_issuance_context_carried=True,
                ucp_agent_covered_in_signed_request=True,
                capability_extends_constraints_enforced=False,
            ).passed
        )
        self.assertFalse(
            evaluate_acp_bopis_offer_expiry_wba_keyring_guard(
                offer_valid_until_unexpired=False,
                bopis_store_pickup_verified=True,
                onchain_eligibility_discount_valid=True,
                wba_keyring_rename_collision_free=True,
            ).passed
        )

    def test_a2a_stripe_agentkit_tau_mcp_guards_block_attacks_and_admit_remediated(self) -> None:
        self.assertFalse(
            evaluate_a2a_card_security_direct_endpoint_guard(
                agent_card_security_scheme_valid=True,
                direct_endpoint_mode_authenticated=False,
                pyjwt_version_at_least_2_15=True,
                standard_task_streaming_validated=True,
            ).passed
        )
        self.assertFalse(
            evaluate_a2a_py_first_owner_js_unknown_event_guard(
                first_owner_write_preserved=False,
                agent_card_jws_signature_verified=True,
                unknown_stream_event_kind_skipped_safely=True,
            ).passed
        )
        self.assertFalse(
            evaluate_a2a_go_terminal_error_dotnet_push_store_guard(
                terminal_or_parked_returns_spec_error_code=False,
                snapshot_materialization_verified=True,
                dotnet_push_notification_store_encrypted=True,
            ).passed
        )
        self.assertFalse(
            evaluate_stripe_ai_hermes_token_meter_abandoned_stream_guard(
                hermes_plugin_skills_hardened=True,
                cumulative_anthropic_input_metered=True,
                abandoned_stream_consumption_stopped=False,
                plugin_auto_update_precedence_explicit=True,
            ).passed
        )
        self.assertFalse(
            evaluate_stripe_ruby_gcp_wif_embedded_checkout_guard(
                gcp_wif_audience_bound=False,
                rk_live_or_wif_token_used=True,
                embedded_checkout_single_wrapper=True,
                pe_unupdatable_layout_blocked=True,
            ).passed
        )
        self.assertFalse(
            evaluate_agentkit_404_method_permit2_cdp_utf8_jwt_guard(
                http_method_preserved_on_404=False,
                enso_slippage_bps=100,
                permit2_exact_allowance_no_swap_retry=True,
                wallet_chain_bound_and_receipt_awaited=True,
                cdp_non_ascii_body_utf8_hashed=True,
            ).passed
        )
        self.assertFalse(
            evaluate_tau2_voice_submission_tau_strict_reward_guard(
                incomplete_voice_submission_refused=False,
                gpt5_tool_choice_preserved=True,
                strict_output_match_and_cabin_updated=True,
                user_sim_cost_and_seed_deterministic=True,
            ).passed
        )
        self.assertFalse(
            evaluate_mcp_safe_int_inspector_secret_redaction_budget_guard(
                integer_param_value=9007199254740992,
                url_query_secrets_redacted_in_errors=True,
                skill_catalog_within_count_and_byte_budget=True,
                ext_auth_wif_profile_valid=True,
            ).passed
        )
        self.assertFalse(
            evaluate_mcp_ts_expected_resource_py_32600_202_guard(
                bearer_auth_matches_expected_resource=True,
                schema_failure_error_code=-32602,
                non_request_body_error_code=-32602,
                bytes_base64_encoded_and_202_accepted=True,
            ).passed
        )
        self.assertFalse(
            evaluate_mcp_go_exact_id_rust_empty_router_csharp_guard(
                jsonrpc_id_exact_preserved=True,
                non_ascii_mcp_name_base64_encoded=True,
                empty_rust_tool_router_rejected=False,
                oauth_refresh_coordinated_via_store=True,
                csharp_per_user_client_isolated=True,
            ).passed
        )
        self.assertFalse(
            evaluate_mcp_java_concealed_chars_swift_stateless_php_ruby_guard(
                concealed_unicode_in_metadata_blocked=False,
                sep2549_ttl_cache_bounded=True,
                swift_stateless_http_isolated_and_cancelled_released=True,
                php_session_locked_and_timeout_expired=True,
                ruby_listen_teardown_bounded=True,
            ).passed
        )

    def test_stage287_benchmark_generates_7_card_bilingual_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            summary = run_stage287_benchmark(tmp)
            self.assertEqual(summary["total_scenarios"], 16)
            self.assertEqual(summary["attack_blocked_count"], 16)
            self.assertEqual(summary["remediated_passed_count"], 16)
            self.assertEqual(summary["perturbation_stable_count"], 16)
            self.assertEqual(summary["total_unique_prs"], 432)
            self.assertEqual(summary["total_unique_repos"], 53)

            zh_html = (Path(tmp) / "index.html").read_text(encoding="utf-8")
            en_html = (Path(tmp) / "index.en.html").read_text(encoding="utf-8")
            for idx in range(1, 8):
                self.assertIn(f"{idx} / 7 ·", zh_html)
                self.assertIn(f"{idx} / 7 ·", en_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)


if __name__ == "__main__":
    unittest.main()
