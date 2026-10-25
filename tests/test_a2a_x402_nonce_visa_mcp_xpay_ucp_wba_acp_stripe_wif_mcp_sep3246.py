"""Unit tests for Stage 282 guards and Stage 283 16-scenario 7-Card 4:5 benchmark (356 PRs across 49 repos)."""

from __future__ import annotations

import glob
import re
import unittest
from pathlib import Path

from lab.a2a_x402_nonce_visa_mcp_xpay_ucp_wba_acp_stripe_wif_mcp_sep3246_bench import (
    build_stage283_summary,
    write_stage283_report,
)
from lab.a2a_x402_nonce_visa_mcp_xpay_ucp_wba_acp_stripe_wif_mcp_sep3246_guards import (
    STAGE282_PR_GROUPS,
    evaluate_a2a_go_java_dotnet_inspector_guard,
    evaluate_a2a_remote_attestation_and_python_js_task_guard,
    evaluate_a2a_x402_nonce_and_settlement_guard,
    evaluate_acp_delegate_auth_and_discount_extension_guard,
    evaluate_agentkit_relayshield_sentinel_and_tau2_voice_guard,
    evaluate_ap2_conformance_sdjwt_rfc9901_and_wba_guard,
    evaluate_mcp_csharp_kotlin_swift_runtime_guard,
    evaluate_mcp_go_rust_java_transport_guard,
    evaluate_mcp_php_ruby_inspector_registry_guard,
    evaluate_mcp_sep3246_authority_and_py_ts_guard,
    evaluate_mppx_atomic_reservation_and_tempo_voucher_guard,
    evaluate_stripe_7sdk_wif_and_v2_search_guard,
    evaluate_stripe_ai_plugin_hooks_and_cli_sandbox_guard,
    evaluate_ucp_wba_interop_and_schema_twin_isolation_guard,
    evaluate_visa_mcp_xpay_and_tap_hybrid_mldsa_guard,
    evaluate_x402_rs_settle_retry_and_caip_cwp_guard,
)


class Stage282And283Tests(unittest.TestCase):
    def test_stage282_pr_inventory_is_unique_and_zero_overlap_with_prior_stages(self) -> None:
        all_prs = [pr for prs in STAGE282_PR_GROUPS.values() for pr in prs]
        self.assertEqual(len(STAGE282_PR_GROUPS), 16)
        self.assertEqual(len(all_prs), 356)
        self.assertEqual(len(set(all_prs)), 356)
        repos = {pr.split("#")[0] for pr in all_prs}
        self.assertEqual(len(repos), 49)

        this_guard = Path("lab/a2a_x402_nonce_visa_mcp_xpay_ucp_wba_acp_stripe_wif_mcp_sep3246_guards.py").resolve()
        prior_prs: set[str] = set()
        for p_str in glob.glob("lab/*guards.py"):
            p = Path(p_str).resolve()
            if p == this_guard:
                continue
            text = p.read_text(encoding="utf-8")
            for m in re.finditer(r"([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)#(\d+)", text):
                prior_prs.add(f"{m.group(1)}#{m.group(2)}")

        overlap = set(all_prs) & prior_prs
        self.assertEqual(overlap, set())

    def test_stage282_commerce_payment_and_identity_guards(self) -> None:
        self.assertFalse(
            evaluate_a2a_x402_nonce_and_settlement_guard(
                eip3009_nonce_csprng=True,
                response_deferred_until_settled=False,
                stepsecurity_workflow_pinned=True,
            )["passed"]
        )
        self.assertTrue(
            evaluate_a2a_x402_nonce_and_settlement_guard(
                eip3009_nonce_csprng=True,
                response_deferred_until_settled=True,
                stepsecurity_workflow_pinned=True,
            )["passed"]
        )
        self.assertFalse(
            evaluate_x402_rs_settle_retry_and_caip_cwp_guard(
                chain_reconciled_on_store_miss=False,
                receipt_timeout_returns_pending=True,
                rpc_url_redacted_in_error=True,
                caip_cwp_label_valid=True,
            )["passed"]
        )
        self.assertFalse(
            evaluate_mppx_atomic_reservation_and_tempo_voucher_guard(
                stream_reservation_atomic=True,
                settled_on_close_detected=True,
                retired_root_key_rejected=False,
                migrated_voucher_redeemable=True,
            )["passed"]
        )
        self.assertFalse(
            evaluate_visa_mcp_xpay_and_tap_hybrid_mldsa_guard(
                xpay_query_lexicographically_sorted=True,
                jwks_chain_and_card_redaction_verified=True,
                tap_ed25519_mldsa65_hybrid_valid=False,
            )["passed"]
        )
        self.assertFalse(
            evaluate_ap2_conformance_sdjwt_rfc9901_and_wba_guard(
                ap2_dual_lang_mandate_verified=False,
                sdjwt_rfc9901_vct_audited=True,
                wba_unique_labels_and_https_directory=True,
                ext_auth_dpop_jkt_bound=True,
            )["passed"]
        )
        self.assertFalse(
            evaluate_ucp_wba_interop_and_schema_twin_isolation_guard(
                wba_interop_and_payment_finality_defined=True,
                constrained_schema_twin_isolated=True,
                local_entity_refs_resolved_before_inline=False,
            )["passed"]
        )
        self.assertFalse(
            evaluate_acp_delegate_auth_and_discount_extension_guard(
                delegate_auth_and_cla_verified=True,
                discount_extension_links_and_changelog_valid=False,
                stale_pr_governance_active=True,
            )["passed"]
        )

    def test_stage282_a2a_stripe_agentkit_and_mcp_11sdk_guards(self) -> None:
        self.assertFalse(
            evaluate_a2a_remote_attestation_and_python_js_task_guard(
                hardware_remote_attestation_and_adr002_valid=False,
                idle_task_stale_snapshot_dropped=True,
                a2a_version_minor_validated=True,
            )["passed"]
        )
        self.assertFalse(
            evaluate_a2a_go_java_dotnet_inspector_guard(
                go_head_subscription_rejected=True,
                go_in_place_artifact_recovered=False,
                java_omitted_push_config_id_allowed=True,
                inspector_dompurify_and_go_backend_hardened=True,
            )["passed"]
        )
        self.assertFalse(
            evaluate_stripe_ai_plugin_hooks_and_cli_sandbox_guard(
                threadless_sync_tool_loop_safe=True,
                deprecated_actions_key_warned=False,
                cli_telemetry_optout_and_sandbox_stamped=True,
            )["passed"]
        )
        self.assertFalse(
            evaluate_stripe_7sdk_wif_and_v2_search_guard(
                workload_identity_package_trusted_publishing=True,
                node_fetch_dispose_and_v2list_exported=False,
                v2_search_and_cert_bundle_verified=True,
            )["passed"]
        )
        self.assertFalse(
            evaluate_agentkit_relayshield_sentinel_and_tau2_voice_guard(
                relayshield_and_m2m_sentinel_active=True,
                agent_guild_and_offramp_policy_enforced=False,
                tau2_voice_provider_dated_and_verified=True,
            )["passed"]
        )
        self.assertFalse(
            evaluate_mcp_sep3246_authority_and_py_ts_guard(
                sep3246_provenance_authority_confined=True,
                py_validation_input_redacted_and_stdio_clean=False,
                ts_expected_resource_and_ajv_cached=True,
            )["passed"]
        )
        self.assertFalse(
            evaluate_mcp_go_rust_java_transport_guard(
                go_stream_subscription_cleared_and_null_preserved=False,
                rust_streamable_http_response_bounded=True,
                java_roots_capability_and_sse_line_separators_safe=True,
            )["passed"]
        )
        self.assertFalse(
            evaluate_mcp_csharp_kotlin_swift_runtime_guard(
                csharp_degenerate_base64_header_safe=True,
                kotlin_zod_hono_interop_hardened=True,
                swift_actor_weak_self_and_codec_cached=False,
            )["passed"]
        )
        self.assertFalse(
            evaluate_mcp_php_ruby_inspector_registry_guard(
                php_fiber_outside_http_and_event_loop_driven=False,
                ruby_byte_frame_strip_and_unreadable_id_refusal=True,
                inspector_mrtr_state_chained_and_orphan_secrets_purged=True,
                registry_retired_k8up_schedule_removed=True,
            )["passed"]
        )

    def test_stage283_benchmark_and_7card_bilingual_report_generation(self) -> None:
        summary = build_stage283_summary()
        self.assertEqual(summary["stage"], "282-283")
        self.assertEqual(summary["scenario_count"], 16)
        self.assertEqual(summary["total_unique_prs"], 356)
        self.assertEqual(summary["upstream_repo_count"], 49)
        self.assertEqual(summary["attack_block_rate"], "16/16")
        self.assertEqual(summary["remediated_pass_rate"], "16/16")
        self.assertEqual(summary["perturbation_consistency"], "16/16")

        written = write_stage283_report()
        self.assertEqual(written["total_unique_prs"], 356)
        out_dir = Path(
            "reports/agentic-commerce-a2a-x402-nonce-visa-mcp-xpay-ucp-wba-acp-stripe-wif-mcp-sep3246-bench"
        )
        for fname in ("report.json", "index.html", "index.en.html"):
            p = out_dir / fname
            self.assertTrue(p.exists())
            content = p.read_text(encoding="utf-8")
            if fname.endswith(".html"):
                self.assertIn("default-src 'none'; style-src 'unsafe-inline'", content)
                for i in range(1, 8):
                    self.assertIn(f'id="card-{i}"', content)


if __name__ == "__main__":
    unittest.main()
