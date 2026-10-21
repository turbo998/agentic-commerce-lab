"""Unit tests for Stage 120 x402 SIWX/recovery/receipt, Stripe token-meter/Tulip,
and MCP SEP-3392/3405 + UCP bundled schema table guards."""

from __future__ import annotations

import unittest

from lab.x402_siwx_recovery_receipt_stripe_token_meter_tulip_mcp_lifecycle_ucp_guard import (
    validate_mcp_lifecycle_and_ucp_schema_tables,
    validate_stripe_token_meter_and_tulip_gate,
    validate_x402_siwx_recovery_and_receipt,
)


class Stage120GuardTests(unittest.TestCase):
    def test_x402_siwx_recovery_and_receipt_valid(self) -> None:
        res = validate_x402_siwx_recovery_and_receipt(
            http_method="GET",
            has_http_transport=True,
            server_request_path="/api/premium/report",
            client_payload_resource_url="/api/cheap/ping",
            requested_protected_path="/api/premium/report",
            settlement_status="confirmed",
            server_operation_id="op_01",
            lookup_operation_id="op_01",
            confirmed_settlement_ref="tx_0xabc",
            promotion_hook_failed=False,
            staged_projection_hash="sha256:111",
            recomputed_projection_hash="sha256:111",
            permit2_rpc_failed=False,
            permit2_reported_code="",
            raw_signature_v=1,
            declared_extensions={"offer-receipt": {"includeTxHash": True}},
            mutated_declared_extensions_in_402=False,
            receipt_version=2,
            authorization_method="svm-memo",
            authorization_id="memo-nonce-99",
            commitment_salt="salt_abc",
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.normalized_v, 28)
        self.assertTrue(res.receipt_tx_included)
        self.assertTrue(res.recovery_promoted)
        self.assertEqual(len(res.authorization_commitment), 64)

    def test_x402_siwx_client_url_spoof_or_head_settle_blocked(self) -> None:
        res = validate_x402_siwx_recovery_and_receipt(
            http_method="GET",
            has_http_transport=True,
            server_request_path="/api/cheap/ping",
            client_payload_resource_url="/api/premium/report",
            requested_protected_path="/api/premium/report",
            settlement_status="confirmed",
            server_operation_id="op_01",
            lookup_operation_id="op_01",
            confirmed_settlement_ref="tx_0xabc",
            promotion_hook_failed=False,
            staged_projection_hash="sha256:111",
            recomputed_projection_hash="sha256:111",
            permit2_rpc_failed=False,
            permit2_reported_code="",
            raw_signature_v=27,
            declared_extensions={"offer-receipt": {"includeTxHash": True}},
            mutated_declared_extensions_in_402=False,
            receipt_version=2,
            authorization_method="eip3009",
            authorization_id="0xnonce",
            commitment_salt="salt_abc",
        )
        self.assertFalse(res.allowed)
        self.assertEqual(
            res.reason_code, "X402_SIWX_SERVER_PATH_ENTITLEMENT_MISMATCH"
        )

        head_res = validate_x402_siwx_recovery_and_receipt(
            http_method="HEAD",
            has_http_transport=True,
            server_request_path="/api/premium/report",
            client_payload_resource_url="/api/premium/report",
            requested_protected_path="/api/premium/report",
            settlement_status="confirmed",
            server_operation_id="op_01",
            lookup_operation_id="op_01",
            confirmed_settlement_ref="tx_0xabc",
            promotion_hook_failed=False,
            staged_projection_hash="sha256:111",
            recomputed_projection_hash="sha256:111",
            permit2_rpc_failed=False,
            permit2_reported_code="",
            raw_signature_v=27,
            declared_extensions={},
            mutated_declared_extensions_in_402=False,
            receipt_version=1,
            authorization_method="eip3009",
            authorization_id="",
            commitment_salt="",
        )
        self.assertFalse(head_res.allowed)
        self.assertEqual(
            head_res.reason_code, "X402_HEAD_REQUEST_CANNOT_SETTLE_PAYMENT"
        )

    def test_stripe_token_meter_and_tulip_gate_valid_and_blocks_underbilling(self) -> None:
        res = validate_stripe_token_meter_and_tulip_gate(
            message_start_input_tokens=25,
            message_delta_input_tokens_stream=[None, 4120, 10682, None],
            reported_billed_input_tokens=10682,
            rule_risk_level="low",
            advisory_risk_level="high",
            advisory_raised_error=False,
            user_confirmed_high_risk=True,
            audit_chain_linked=True,
            model_id="anthropic/claude-3.7-sonnet",
            lane_id=42,
            merkle_root_verified=True,
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.billed_input_tokens, 10682)
        self.assertEqual(res.resolved_max_tokens, 64000)
        self.assertEqual(res.effective_risk_level, "high")

        bad = validate_stripe_token_meter_and_tulip_gate(
            message_start_input_tokens=25,
            message_delta_input_tokens_stream=[10682],
            reported_billed_input_tokens=25,
            rule_risk_level="low",
            advisory_risk_level=None,
            advisory_raised_error=False,
            user_confirmed_high_risk=True,
            audit_chain_linked=True,
            model_id="anthropic/claude-3.7-sonnet",
            lane_id=0,
            merkle_root_verified=True,
        )
        self.assertFalse(bad.allowed)
        self.assertEqual(
            bad.reason_code, "STRIPE_TOKEN_METER_NON_CUMULATIVE_INPUT_UNDERBILLING"
        )

    def test_mcp_lifecycle_and_ucp_schema_tables_valid_and_blocks_breaking_stable(
        self,
    ) -> None:
        res = validate_mcp_lifecycle_and_ucp_schema_tables(
            extension_repo_name="ext-auth",
            maturity_stage="stable",
            has_extensions_track_sep=True,
            has_standards_track_sep=False,
            has_sep2484_conformance=True,
            introduces_breaking_change=False,
            has_new_core_protocol_revision=False,
            conformance_pass_rate_pct=100.0,
            claimed_sdk_tier=1,
            obsolete_early_allof_branch_present=False,
            schema_table_fields=[
                {"name": "ucp", "resolved_display_type": "UCP Checkout Response Schema"},
                {"name": "ap2", "resolved_display_type": "object"},
            ],
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.computed_sdk_tier, 1)
        self.assertEqual(res.any_type_cells_count, 0)

        bad = validate_mcp_lifecycle_and_ucp_schema_tables(
            extension_repo_name="ext-auth",
            maturity_stage="stable",
            has_extensions_track_sep=True,
            has_standards_track_sep=False,
            has_sep2484_conformance=True,
            introduces_breaking_change=True,
            has_new_core_protocol_revision=False,
            conformance_pass_rate_pct=100.0,
            claimed_sdk_tier=1,
            obsolete_early_allof_branch_present=False,
            schema_table_fields=[{"name": "ucp", "resolved_display_type": "UCP Error"}],
        )
        self.assertFalse(bad.allowed)
        self.assertEqual(
            bad.reason_code,
            "MCP_STABLE_EXTENSION_BREAKING_CHANGE_WITHOUT_CORE_REVISION",
        )


if __name__ == "__main__":
    unittest.main()
