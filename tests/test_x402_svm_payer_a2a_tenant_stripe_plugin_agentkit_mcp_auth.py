"""Unit tests for Stage 266 guards and Stage 267 16-scenario benchmark."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.x402_svm_payer_a2a_tenant_stripe_plugin_agentkit_mcp_auth_bench import (
    build_benchmark_report,
    write_report_artifacts,
)
from lab.x402_svm_payer_a2a_tenant_stripe_plugin_agentkit_mcp_auth_guards import (
    validate_a2a_card_jws_and_rest_media_type,
    validate_a2a_jsonrpc_response_envelope,
    validate_a2a_rest_tenant_prefix_mount,
    validate_agentkit_x402_guard_and_keeperhub_idempotency,
    validate_mcp_apps_v2_peer_isolation_and_csharp_clone,
    validate_mcp_go_stream_deadline_sse_custom_and_nonnull_slices,
    validate_mcp_java_notifier_factory_and_logging_coercion,
    validate_mcp_oauth_strict_expiry_boundary,
    validate_mcp_python_stream_probe_and_timeout,
    validate_mcp_rust_refresh_token_revocation_policy,
    validate_stripe_cli_plugin_and_release_guard,
    validate_stripe_sdk_retry_dispose_and_pagination,
    validate_x402_cardano_payto_resolver,
    validate_x402_package_exports_bundle,
    validate_x402_python_svm_solana_version_cap,
    validate_x402_svm_settlement_payer_authority,
)


class TestStage266To267SecurityGuardsAndBench(unittest.TestCase):
    """Test suite adding 4 unit test methods (944 -> 948 total unit tests)."""

    def test_x402_svm_payer_cardano_solana_and_exports_guards(self) -> None:
        buyer = "9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin"
        fee_payer = "4Nd1mBQtrMJVYVfKf2PJy9NZUZdTAsp7D4xWLs4gDB4T"

        ok_payer = validate_x402_svm_settlement_payer_authority(
            reported_payer=buyer,
            transfer_authority=buyer,
            fee_payer=fee_payer,
        )
        self.assertTrue(ok_payer.passed)

        bad_payer = validate_x402_svm_settlement_payer_authority(
            reported_payer=fee_payer,
            transfer_authority=buyer,
            fee_payer=fee_payer,
        )
        self.assertFalse(bad_payer.passed)
        self.assertEqual(bad_payer.reason_code, "svm_settlement_payer_returned_facilitator_fee_payer")

        bad_cardano = validate_x402_cardano_payto_resolver(
            network="cardano:Mainnet",
            direct_cardano_prebuild_import=True,
            masumi_escrow_resolver=lambda net: "addr1qx2fxv2umyhttkxyxp8x0dlpdt3k6cwng5pxj3jhsydzer",
        )
        self.assertFalse(bad_cardano.passed)
        self.assertEqual(bad_cardano.reason_code, "cardano_direct_prebuild_import_blocked")

        ok_solana = validate_x402_python_svm_solana_version_cap(
            solana_version="0.36.6",
            has_solana_rpc_api=True,
        )
        self.assertTrue(ok_solana.passed)

        bad_exports = validate_x402_package_exports_bundle(
            checked_count=2,
            declared_targets={"types": "./dist/index.d.ts", "import": "./dist/index.mjs"},
            existing_files={"./dist/index.mjs"},
        )
        self.assertFalse(bad_exports.passed)
        self.assertEqual(bad_exports.reason_code, "verify_exports_missing_target_file")

    def test_a2a_tenant_jsonrpc_and_card_jws_guards(self) -> None:
        bad_mount = validate_a2a_rest_tenant_prefix_mount(
            path_prefix="/a2a/rest",
            mounted_pattern="/{tenant}/a2a/rest/message:send",
            request_path="/a2a/rest/tenant-a/message:send",
        )
        self.assertFalse(bad_mount.passed)
        self.assertEqual(bad_mount.reason_code, "a2a_rest_tenant_mounted_before_prefix")

        bad_jsonrpc = validate_a2a_jsonrpc_response_envelope(["not", "a", "dict"])
        self.assertFalse(bad_jsonrpc.passed)
        self.assertEqual(bad_jsonrpc.reason_code, "a2a_jsonrpc_non_object_response")

        mapped_err = validate_a2a_jsonrpc_response_envelope(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "error": {"code": -32001, "reason": "MISSING_TASK"},
            }
        )
        self.assertFalse(mapped_err.passed)
        self.assertEqual(mapped_err.details["mapped_error"], "TaskNotFoundError")

        card_bytes = b'{"name":"Probe"}'
        tampered = validate_a2a_card_jws_and_rest_media_type(
            canonical_card_utf8=b'{"name":"Probe."}',
            expected_canonical_hex=card_bytes.hex(),
            content_type="application/a2a+json",
            message_payload={"parts": []},
        )
        self.assertFalse(tampered.passed)
        self.assertEqual(tampered.reason_code, "a2a_card_signature_canonical_bytes_mismatch")

    def test_stripe_agentkit_and_mcp_multi_sdk_guards(self) -> None:
        arch_gap = validate_stripe_cli_plugin_and_release_guard(
            installed_version="1.2.0",
            target_version="1.3.0",
            is_auto_upgrade=False,
            available_builds_for_target={"darwin/arm64", "linux/amd64"},
            requested_os_arch="windows/arm64",
            release_env_keys={
                "MACOS_SIGN_P12",
                "MACOS_SIGN_PASSWORD",
                "MACOS_NOTARY_ISSUER_ID",
                "MACOS_NOTARY_KEY_ID",
                "MACOS_NOTARY_KEY",
            },
        )
        self.assertFalse(arch_gap.passed)
        self.assertEqual(arch_gap.reason_code, "stripe_plugin_os_arch_build_unavailable")

        leak_retry = validate_stripe_sdk_retry_dispose_and_pagination(
            retry_scheduled=True,
            discarded_response_disposed=False,
            async_signature_verified=True,
            page_data_len=5,
            has_more=True,
        )
        self.assertFalse(leak_retry.passed)
        self.assertEqual(leak_retry.reason_code, "stripe_retry_undisposed_stream_leak")

        avoid_seller = validate_agentkit_x402_guard_and_keeperhub_idempotency(
            seller_verdict="avoid",
            eip712_attestation_valid=True,
            simulate_before_broadcast=True,
            simulation_reverted=False,
            task_id="task-99",
            seen_task_ids={},
        )
        self.assertFalse(avoid_seller.passed)
        self.assertEqual(avoid_seller.reason_code, "agentkit_x402_seller_avoid_blocked")

        ok_expiry = validate_mcp_oauth_strict_expiry_boundary(
            now_epoch=100.0,
            expiry_epoch=100.001,
        )
        self.assertTrue(ok_expiry.passed)

        bad_probe = validate_mcp_python_stream_probe_and_timeout(
            probe_request_id=1,
            custom_client_read_timeout_sec=300.0,
            stateless_or_json_response=False,
            expects_disconnect_cancellation=False,
        )
        self.assertFalse(bad_probe.passed)
        self.assertEqual(bad_probe.reason_code, "mcp_internal_probe_integer_id_collision")

        ok_rust = validate_mcp_rust_refresh_token_revocation_policy(
            oauth_error_code="invalid_grant",
            revoked_stored_credentials=True,
        )
        self.assertTrue(ok_rust.passed)

        null_notifier = validate_mcp_java_notifier_factory_and_logging_coercion(
            is_streaming_handler=True,
            notifier_factory_returned_null=True,
            log_level="info",
            raw_log_data="ok",
        )
        self.assertFalse(null_notifier.passed)
        self.assertEqual(null_notifier.reason_code, "mcp_java_null_stream_notifier_internal_error")

        peer_leak = validate_mcp_apps_v2_peer_isolation_and_csharp_clone(
            ui_initialize_version="2026-01-26",
            cloned_has_marshal_result=True,
            server_entry_imports_client_peer=True,
        )
        self.assertFalse(peer_leak.passed)
        self.assertEqual(peer_leak.reason_code, "mcp_apps_server_imports_client_peer")

    def test_stage_267_benchmark_report_and_7card_html(self) -> None:
        report = build_benchmark_report()
        self.assertEqual(report["stage"], 267)
        self.assertEqual(report["guard_stage"], 266)
        self.assertEqual(report["total_scenarios"], 16)
        self.assertEqual(report["ai_native_passed"], 16)
        self.assertEqual(report["ai_native_pass_rate"], 1.0)
        self.assertEqual(report["reversed_order_consistency"], 1.0)
        self.assertEqual(report["perturbed_consistency"], 1.0)

        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = write_report_artifacts(Path(tmp_dir))
            for key in ("report_json", "index_html", "index_en_html"):
                self.assertTrue(paths[key].exists(), f"Missing {key}")
            zh_html = paths["index_html"].read_text(encoding="utf-8")
            en_html = paths["index_en_html"].read_text(encoding="utf-8")
            for badge in ("1 / 7", "2 / 7", "3 / 7", "4 / 7", "5 / 7", "6 / 7", "7 / 7"):
                self.assertIn(badge, zh_html)
                self.assertIn(badge, en_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", en_html)


if __name__ == "__main__":
    unittest.main()
