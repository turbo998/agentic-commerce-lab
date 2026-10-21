"""Unit tests for Stage 134 deterministic guardrails."""

from __future__ import annotations

import unittest

from lab.x402_evm_auth_capture_svm_lighthouse_ucp_delegated_idp_mcp_secure_params_guard import (
    evaluate_mcp_secure_params_flow_and_stripe_v2_guard,
    evaluate_tau2_banking_kb_voice_and_usersim_guard,
    evaluate_ucp_delegated_idp_and_capability_ops_guard,
    evaluate_ucp_marketing_upsell_and_return_url_guard,
    evaluate_x402_buyer_claim_xahau_runtime_guard,
    evaluate_x402_evm_auth_capture_guard,
    evaluate_x402_svm_lighthouse_and_seal_callback_guard,
)


class Stage134GuardTests(unittest.TestCase):
    def test_x402_evm_auth_capture_svm_lighthouse_and_xahau_guards(self) -> None:
        auth = evaluate_x402_evm_auth_capture_guard(
            action="authorize",
            authorized_amount_minor=5000,
            requested_amount_minor=5000,
            current_escrow_state="none",
            server_signature_verified=False,
        )
        self.assertTrue(auth.allowed)
        self.assertEqual(auth.escrow_state, "authorized")

        cap = evaluate_x402_evm_auth_capture_guard(
            action="capture",
            authorized_amount_minor=5000,
            requested_amount_minor=4200,
            current_escrow_state="authorized",
            server_signature_verified=True,
        )
        self.assertTrue(cap.allowed)
        self.assertEqual(cap.captured_amount_minor, 4200)

        bad_zero_fee = evaluate_x402_evm_auth_capture_guard(
            action="authorize",
            authorized_amount_minor=5000,
            requested_amount_minor=5000,
            current_escrow_state="none",
            server_signature_verified=False,
            fee_bps=0,
            fee_recipient="0x1111111111111111111111111111111111111111",
        )
        self.assertFalse(bad_zero_fee.allowed)
        self.assertEqual(
            bad_zero_fee.reason_code,
            "X402_EVM_AUTH_CAPTURE_INVALID_ZERO_FEE_OPERATOR_TERMS",
        )

        # Phantom Lighthouse placed BEFORE TransferChecked is valid (#3615)
        svm_ok = evaluate_x402_svm_lighthouse_and_seal_callback_guard(
            instruction_program_ids=(
                "ComputeBudget111111111111111111111111111111",
                "L2TExMFKdjpN9kozasaurPirfHy9P8sbXoAN1qA3S95",
                "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
                "L2TExMFKdjpN9kozasaurPirfHy9P8sbXoAN1qA3S95",
            ),
            has_transfer_checked=True,
            close_mode="seal",
            tx_landed_onchain=True,
            distribution_callback_succeeded=False,
        )
        self.assertTrue(svm_ok.allowed)
        self.assertEqual(svm_ok.settlement_status, "settlement_pending")

        svm_untrusted = evaluate_x402_svm_lighthouse_and_seal_callback_guard(
            instruction_program_ids=(
                "AttackerProgram11111111111111111111111111111",
                "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            ),
            has_transfer_checked=True,
        )
        self.assertFalse(svm_untrusted.allowed)

        xahau_ok = evaluate_x402_buyer_claim_xahau_runtime_guard()
        self.assertTrue(xahau_ok.allowed)

        xahau_bad_fee = evaluate_x402_buyer_claim_xahau_runtime_guard(
            xahau_fee_drops=250_000,
            xahau_max_fee_drops=100_000,
        )
        self.assertFalse(xahau_bad_fee.allowed)
        self.assertEqual(
            xahau_bad_fee.reason_code,
            "X402_XAHAU_HOOK_FEE_DROPS_EXCEEDS_MAX",
        )

    def test_ucp_delegated_idp_capability_ops_and_marketing_upsell_guards(self) -> None:
        idp_ok = evaluate_ucp_delegated_idp_and_capability_ops_guard(
            business_issuer="https://auth.merchant.example",
            business_delegated_idps=("https://accounts.google.com", "https://shop.app"),
            platform_idp_issuer="https://accounts.google.com",
            rfc8693_grant_type="urn:ietf:params:oauth:grant-type:token-exchange",
            rfc7523_client_assertion_verified=True,
            issued_access_token_issuer="https://auth.merchant.example",
            intersected_capabilities={
                "dev.ucp.shopping.checkout": ("create_checkout", "update_checkout", "complete_checkout")
            },
            requested_operation="complete_checkout",
        )
        self.assertTrue(idp_ok.allowed)

        idp_wrong_authority = evaluate_ucp_delegated_idp_and_capability_ops_guard(
            business_issuer="https://auth.merchant.example",
            business_delegated_idps=("https://accounts.google.com",),
            platform_idp_issuer="https://accounts.google.com",
            rfc8693_grant_type="urn:ietf:params:oauth:grant-type:token-exchange",
            rfc7523_client_assertion_verified=True,
            issued_access_token_issuer="https://accounts.google.com",
            intersected_capabilities={"dev.ucp.shopping.checkout": ("create_checkout",)},
            requested_operation="create_checkout",
        )
        self.assertFalse(idp_wrong_authority.allowed)
        self.assertEqual(
            idp_wrong_authority.reason_code,
            "UCP_DELEGATED_IDP_TOKEN_MUST_BE_ISSUED_BY_BUSINESS_AUTHORITY",
        )

        mkt_ok = evaluate_ucp_marketing_upsell_and_return_url_guard(
            marketing_consent_options=(
                {
                    "channel_id": "email",
                    "display_text": "Product updates via email",
                    "privacy_policy_url": "https://merchant.example/privacy",
                },
            ),
            submitted_marketing_channels=(
                {"channel_id": "email", "opt_in": True, "explicit_buyer_decision": True},
            ),
            message_presentation="compliance",
            subtotal_minor=4000,
            total_minor=4000,
            approaching_discounts=({"threshold_minor": 5000, "spend_remaining_minor": 1000},),
            return_url="https://platform.example.com/checkout/return",
            return_query_status_hint="completed",
            session_api_verified_status="completed",
        )
        self.assertTrue(mkt_ok.allowed)

        mkt_spoof_return = evaluate_ucp_marketing_upsell_and_return_url_guard(
            marketing_consent_options=(),
            submitted_marketing_channels=(),
            return_url="https://platform.example.com/checkout/return",
            return_query_status_hint="completed",
            session_api_verified_status="in_progress",
        )
        self.assertFalse(mkt_spoof_return.allowed)
        self.assertEqual(
            mkt_spoof_return.reason_code,
            "UCP_RETURN_URL_STATUS_HINT_UNVERIFIED_OR_MISMATCH",
        )

    def test_mcp_secure_params_flow_stripe_v2_and_tau2_guards(self) -> None:
        mcp_ok = evaluate_mcp_secure_params_flow_and_stripe_v2_guard(
            secure_input_keys=("tenant_id", "project_id"),
            model_arguments={"query": "list invoices"},
            host_secure_arguments={"tenant_id": "t_123", "project_id": "p_456"},
            flow_origins=("user", "mcp:billing-server"),
            server_allowed_flow_origins=("user", "mcp:billing-server"),
            oneof_root_property_types={"id": str, "name": str},
            oneof_instance={"id": "r1"},
            idempotency_key="idem_01",
            seen_idempotency_keys=("idem_01",),
        )
        self.assertTrue(mcp_ok.allowed)
        self.assertTrue(mcp_ok.deduplicated_replay)

        mcp_confused_deputy = evaluate_mcp_secure_params_flow_and_stripe_v2_guard(
            secure_input_keys=("tenant_id",),
            model_arguments={"query": "list", "tenant_id": "evil_tenant"},
            host_secure_arguments={"tenant_id": "t_123"},
            flow_origins=("user",),
            server_allowed_flow_origins=("user",),
        )
        self.assertFalse(mcp_confused_deputy.allowed)
        self.assertEqual(
            mcp_confused_deputy.reason_code,
            "MCP_SEP3221_MODEL_CONTROLLED_SECURE_PARAM_INJECTION_BLOCKED",
        )

        mcp_oneof_bypass = evaluate_mcp_secure_params_flow_and_stripe_v2_guard(
            secure_input_keys=(),
            model_arguments={},
            host_secure_arguments={},
            flow_origins=("user",),
            server_allowed_flow_origins=("user",),
            oneof_root_property_types={"id": str, "name": str},
            oneof_instance={"id": "r1", "name": 123},
        )
        self.assertFalse(mcp_oneof_bypass.allowed)
        self.assertEqual(
            mcp_oneof_bypass.reason_code,
            "MCP_ONEOF_INACTIVE_BRANCH_TYPE_BYPASS_BLOCKED",
        )

        tau2_ok = evaluate_tau2_banking_kb_voice_and_usersim_guard(
            kb_text="CLI eligibility requires $120 days of history and $500 minimum balance after $180 days.",
            voice_interaction_metrics_parity=True,
            voice_banking_task_count=97,
            transfer_stop_triggered_by="agent",
        )
        self.assertTrue(tau2_ok.allowed)
        self.assertEqual(tau2_ok.repaired_day_count_artifacts, 2)
        self.assertIn("120 days", tau2_ok.sanitized_kb_text)
        self.assertIn("$500", tau2_ok.sanitized_kb_text)


if __name__ == "__main__":
    unittest.main()
