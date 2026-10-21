"""Unit tests for Stage 140 guardrails."""

from __future__ import annotations

import unittest

from lab.x402_mcp_accepts_snapshot_svm_tx_v1_ucp_price_state_ap2_withheld_tap_guard import (
    evaluate_mcp_stdio_stripe_policy_and_tau2_flown_flight_guard,
    evaluate_ucp_acp_ap2_and_tap_temporal_authority_guard,
    evaluate_x402_mcp_accepts_snapshot_and_svm_version_guard,
)


class Stage140GuardTests(unittest.TestCase):
    def test_x402_mcp_accepts_snapshot_and_svm_version_guard(self) -> None:
        ok = evaluate_x402_mcp_accepts_snapshot_and_svm_version_guard(
            accepts_snapshotted_before_enricher=True,
            enricher_mutated_baseline=False,
            fastmcp_invalid_reason="insufficient_funds",
            payment_made=True,
            payment_response_present=True,
            logged_as_settled=True,
            mcp_tool_timeout_sec=300,
            retry_request_headers=("Authorization", "Payment-Signature"),
            svm_client_tx_version=0,
            facilitator_supported_tx_versions=(0,),
            upstream_http_status=200,
            settlement_triggered=True,
            gas_sponsoring_advertised=True,
            client_has_rpc_url=True,
            stellar_inclusion_fee_stroops=500,
        )
        self.assertTrue(ok.allowed)

        bad_svm = evaluate_x402_mcp_accepts_snapshot_and_svm_version_guard(
            accepts_snapshotted_before_enricher=True,
            enricher_mutated_baseline=False,
            fastmcp_invalid_reason="insufficient_funds",
            payment_made=True,
            payment_response_present=True,
            logged_as_settled=True,
            mcp_tool_timeout_sec=300,
            retry_request_headers=("Authorization",),
            svm_client_tx_version=1,
            facilitator_supported_tx_versions=(0,),
            upstream_http_status=200,
            settlement_triggered=True,
            gas_sponsoring_advertised=False,
            client_has_rpc_url=False,
            stellar_inclusion_fee_stroops=500,
        )
        self.assertFalse(bad_svm.allowed)
        self.assertEqual(bad_svm.decision_code, "X402_SVM_TX_VERSION_NOT_ADVERTISED_BY_FACILITATOR")

    def test_ucp_acp_ap2_and_tap_temporal_authority_guard(self) -> None:
        ok = evaluate_ucp_acp_ap2_and_tap_temporal_authority_guard(
            third_party_extension_key="com.acme.loyalty.tier",
            catalog_variant_requires_quote=True,
            catalog_variant_selling_price_minor=None,
            catalog_pricing_state="price_on_request",
            checkout_status_before_complete="ready_for_complete",
            digital_entitlement_audience_bound=True,
            is_purchase_order_payment=True,
            po_account_owner_approved=True,
            ap2_withheld_Constraint_disclosures=0,
            ap2_caller_supplied_expected_checkout_hash=True,
            ap2_recurrence_within_execution_window=True,
            ap2_cnf_jwk_use_is_string=True,
            tap_originating_agent_revoked=False,
            tap_action_attestation_verified=True,
        )
        self.assertTrue(ok.allowed)

        bad_ap2 = evaluate_ucp_acp_ap2_and_tap_temporal_authority_guard(
            third_party_extension_key="com.acme.loyalty.tier",
            catalog_variant_requires_quote=False,
            catalog_variant_selling_price_minor=1500,
            catalog_pricing_state="standard",
            checkout_status_before_complete="ready_for_complete",
            digital_entitlement_audience_bound=True,
            is_purchase_order_payment=False,
            po_account_owner_approved=False,
            ap2_withheld_Constraint_disclosures=1,
            ap2_caller_supplied_expected_checkout_hash=True,
            ap2_recurrence_within_execution_window=True,
            ap2_cnf_jwk_use_is_string=True,
            tap_originating_agent_revoked=False,
            tap_action_attestation_verified=True,
        )
        self.assertFalse(bad_ap2.allowed)
        self.assertEqual(bad_ap2.decision_code, "AP2_WITHHELD_CONSTRAINT_DISCLOSURE_FAIL_CLOSED")

    def test_mcp_stdio_stripe_policy_and_tau2_flown_flight_guard(self) -> None:
        ok = evaluate_mcp_stdio_stripe_policy_and_tau2_flown_flight_guard(
            is_stdio_transport=True,
            stdio_peer_sandboxed_or_trusted=True,
            input_schema_present=True,
            schema_ttl_ms=0,
            mcp_param_header_emitted=True,
            post_approval_tool_schema_drifted=False,
            stripe_pre_tool_spend_policy_checked=True,
            stripe_checkout_unintended_customer_assigned=False,
            airline_flight_segment_already_flown=True,
            agent_modified_or_cancelled_flown_flight=False,
            reward_basis_contains_action=True,
            leaderboard_submission_has_email_and_prompt_flag=True,
        )
        self.assertTrue(ok.allowed)

        bad_flight = evaluate_mcp_stdio_stripe_policy_and_tau2_flown_flight_guard(
            is_stdio_transport=False,
            stdio_peer_sandboxed_or_trusted=False,
            input_schema_present=True,
            schema_ttl_ms=0,
            mcp_param_header_emitted=True,
            post_approval_tool_schema_drifted=False,
            stripe_pre_tool_spend_policy_checked=True,
            stripe_checkout_unintended_customer_assigned=False,
            airline_flight_segment_already_flown=True,
            agent_modified_or_cancelled_flown_flight=True,
            reward_basis_contains_action=True,
            leaderboard_submission_has_email_and_prompt_flag=True,
        )
        self.assertFalse(bad_flight.allowed)
        self.assertEqual(bad_flight.decision_code, "TAU2_AIRLINE_ALREADY_FLOWN_SEGMENT_MODIFICATION_BLOCKED")


if __name__ == "__main__":
    unittest.main()
