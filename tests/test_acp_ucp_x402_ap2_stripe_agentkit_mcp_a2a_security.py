"""Unit tests for Stage 264 guards and Stage 265 16-scenario benchmark."""

from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from lab.acp_ucp_x402_ap2_stripe_agentkit_mcp_a2a_security_bench import (
    build_benchmark_report,
    write_report_artifacts,
)
from lab.acp_ucp_x402_ap2_stripe_agentkit_mcp_a2a_security_guards import (
    RAW_PER_XNO,
    evaluate_a2a_java_logging_and_input_required_guard,
    evaluate_a2a_js_migration_lock_cleanup_guard,
    evaluate_a2a_python_cluster_and_card_guard,
    evaluate_a2a_python_jcs_depth_and_signing_guard,
    evaluate_agentkit_eip3009_gasless_usdc_guard,
    evaluate_agentkit_nano_state_block_guard,
    evaluate_agentkit_solana_cap_and_evm_case_guard,
    evaluate_mcp_csharp_http_correlation_and_claims_guard,
    evaluate_mcp_go_annotations_and_params_guard,
    evaluate_mcp_python_auth_and_ext_apps_chrome_guard,
    evaluate_mcp_rust_model_and_discovery_guard,
    evaluate_stripe_cli_install_and_update_guard,
    evaluate_stripe_cli_plugin_output_stream_guard,
    evaluate_stripe_go_safety_and_retry_guard,
    evaluate_stripe_node_barrel_and_fetch_dispose_guard,
    evaluate_stripe_python_v2_search_and_import_guard,
)


class TestStage264To265SecurityGuardsAndBench(unittest.TestCase):
    """Test suite adding 4 unit test methods (940 -> 944 total unit tests)."""

    def test_agentkit_nano_solana_and_eip3009_guards(self) -> None:
        ok_nano = evaluate_agentkit_nano_state_block_guard(
            account="nano_1anrzcuwe64rwxzcco8dkhpyxpi8kd7zsjc1oeimpc3ppca4mrjtwnqposrs",
            destination="nano_3wm37qz19zhei7nzscjcopbrbnnachs4p1gnwo5oroi3qonw6inwgoeuufdp",
            previous_block_hash="991cf190094c00f0b68e2e5f75f6bee95a2e0bd93ceaa4a6734db9f19b728948",
            current_balance_raw=4 * RAW_PER_XNO,
            transfer_amount_raw=1 * RAW_PER_XNO,
            signature_hex="b" * 128,
            work_nonce_hex="e" * 16,
        )
        self.assertTrue(ok_nano.allowed)
        self.assertEqual(ok_nano.details["resulting_balance_raw"], str(3 * RAW_PER_XNO))

        bad_solana = evaluate_agentkit_solana_cap_and_evm_case_guard(
            solana_version=(0, 40, 0),
            token_contract_address="0x1111111111111111111111111111111111111111",
            destination_address="0x2222222222222222222222222222222222222222",
        )
        self.assertFalse(bad_solana.allowed)
        self.assertEqual(bad_solana.action, "block_incompatible_solana_sdk")

        bad_self = evaluate_agentkit_solana_cap_and_evm_case_guard(
            solana_version=(0, 36, 6),
            token_contract_address="0xABCDEF1234567890123456789012345678901234",
            destination_address="0xabcdef1234567890123456789012345678901234",
        )
        self.assertFalse(bad_self.allowed)
        self.assertEqual(bad_self.action, "block_token_contract_self_transfer")

        nonce = "0x" + "ab" * 32
        replay_eip3009 = evaluate_agentkit_eip3009_gasless_usdc_guard(
            chain_id=8453,
            domain_name="USD Coin",
            domain_version="2",
            valid_after=100,
            valid_before=200,
            now_ts=150,
            nonce=nonce,
            used_nonces={nonce.upper()},
            v=27,
        )
        self.assertFalse(replay_eip3009.allowed)
        self.assertEqual(replay_eip3009.action, "block_eip3009_nonce_replay")

    def test_stripe_cli_and_sdk_v2_guards(self) -> None:
        ok_stream = evaluate_stripe_cli_plugin_output_stream_guard(
            events=[
                {"kind": "message", "stream": "stdout", "text": "starting"},
                {"kind": "spinner", "stream": "stderr", "text": "✓ built files"},
            ]
        )
        self.assertTrue(ok_stream.allowed)

        payload = b"stripe-tarball"
        ok_install = evaluate_stripe_cli_install_and_update_guard(
            has_sha256sum=True,
            has_shasum=False,
            archive_bytes=payload,
            expected_sha256=hashlib.sha256(payload).hexdigest(),
            last_version_check_age_seconds=3600,
            disable_update_check_env=False,
            is_snapshot_ci=True,
            has_publishing_credentials=False,
        )
        self.assertTrue(ok_install.allowed)
        self.assertFalse(ok_install.details["should_query_github_releases"])

        bad_import = evaluate_stripe_python_v2_search_and_import_guard(
            import_path="stripe.api_resources.charge",
            object_type="v2.search_result",
            http_method_for_next_page="POST",
            carries_original_json_body=True,
        )
        self.assertFalse(bad_import.allowed)
        self.assertEqual(bad_import.action, "block_orphaned_api_resources_import")

        ok_node = evaluate_stripe_node_barrel_and_fetch_dispose_guard(
            barrel_evaluates_v2_core_events_at_import=False,
            cjs_exports_v2_list_and_search_result=True,
            has_web_body_cancel=False,
            has_node_readable_destroy=True,
            custom_event_name="custom.event",
        )
        self.assertTrue(ok_node.allowed)
        self.assertEqual(ok_node.details["disposal_method"], "destroy")

        ok_go = evaluate_stripe_go_safety_and_retry_guard(
            v2_list_pointer_is_nil=True,
            checked_nil_before_interface_assert=True,
            params_has_metadata_field=False,
            checked_field_valid_before_is_zero=True,
            webhook_secret="whsec_valid_secret",
            stripe_should_retry_header=None,
            http_status=503,
        )
        self.assertTrue(ok_go.allowed)
        self.assertTrue(ok_go.details["should_retry"])

    def test_a2a_jcs_cluster_logging_and_mcp_guards(self) -> None:
        ok_jcs = evaluate_a2a_python_jcs_depth_and_signing_guard(
            payload={"a": [{"b": []}]},
            max_depth=128,
            pruned_empty_map_entry=False,
        )
        self.assertTrue(ok_jcs.allowed)
        self.assertEqual(ok_jcs.details["observed_container_depth"], 4)

        bad_cluster = evaluate_a2a_python_cluster_and_card_guard(
            agent_card_fields={"name": "agent-only"},
            cluster_mode_enabled=True,
            shared_task_store_configured=True,
            shared_event_bus_configured=True,
        )
        self.assertFalse(bad_cluster.allowed)
        self.assertEqual(bad_cluster.action, "block_incomplete_agent_card")

        bad_log = evaluate_a2a_java_logging_and_input_required_guard(
            raw_payload={"Authorization": "Bearer secret_tok"},
            max_log_chars=80,
            task_state="TASK_STATE_INPUT_REQUIRED",
            followup_carries_task_id=True,
            followup_carries_context_id=True,
        )
        self.assertFalse(bad_log.allowed)
        self.assertEqual(bad_log.action, "block_unmasked_sensitive_payload_log")

        bad_lock = evaluate_a2a_js_migration_lock_cleanup_guard(
            migration_in_flight_elsewhere=True,
            migration_succeeded=True,
            lock_table_dropped_after_run=True,
        )
        self.assertFalse(bad_lock.allowed)

        ok_mcp_go = evaluate_mcp_go_annotations_and_params_guard(
            annotation_priority=0.0,
            serialized_json_contains_priority=True,
            server_message_method="elicitation/create",
            server_message_has_params=True,
            prompt_required_args=["order_id"],
            prompt_supplied_args={"order_id": "ord_1"},
        )
        self.assertTrue(ok_mcp_go.allowed)

        bad_mcp_rust = evaluate_mcp_rust_model_and_discovery_guard(
            wire_json={"jsonrpc": "2.0", "id": 1, "result": {}, "error": {"code": -32600}},
            is_tool_result=False,
            discovery_json_rejected=False,
            fell_back_to_well_known=True,
        )
        self.assertFalse(bad_mcp_rust.allowed)
        self.assertEqual(bad_mcp_rust.action, "block_conflicting_jsonrpc_result_and_error")

        ok_mcp_cs = evaluate_mcp_csharp_http_correlation_and_claims_guard(
            content_type="application/json",
            response_body='{"jsonrpc":"2.0","id":9,"result":{}}',
            expected_request_id=9,
            observed_response_id=9,
            requires_claims_principal=True,
            authenticated_principal_id="user:1",
        )
        self.assertTrue(ok_mcp_cs.allowed)

        ok_mcp_py = evaluate_mcp_python_auth_and_ext_apps_chrome_guard(
            requires_asymmetric_jwt_signing=True,
            oauth_crypto_extra_installed=True,
            token_scopes={"notes:read", "notes:write"},
            required_tool_scope="notes:write",
            token_tenant_id="t_1",
            resource_owner_tenant_id="t_1",
            tool_name="notes_update",
            tool_title="Update Customer Note",
        )
        self.assertTrue(ok_mcp_py.allowed)
        self.assertEqual(ok_mcp_py.details["chrome_label"], "Update Customer Note")

    def test_stage265_benchmark_report_and_7card_deck(self) -> None:
        report = build_benchmark_report()
        self.assertEqual(report["stage"], 265)
        self.assertEqual(report["guard_stage"], 264)
        self.assertEqual(report["total_scenarios"], 16)
        self.assertEqual(report["ai_native_passed"], 16)
        self.assertEqual(report["classic_3tier_passed"], 2)
        self.assertEqual(report["ai_native_pass_rate"], 1.0)

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            write_report_artifacts(out_dir)
            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)
            self.assertIn("1 / 7 · HANDS-ON", zh_html)
            self.assertIn("7 / 7 · MY TAKE", en_html)
