from __future__ import annotations

import json
import unittest

from lab.x402_batch_total_claimed_mcp_mismatch_ucp_lodging_vat_mcp_provenance_guard import (
    audit_mcp_provenance_mpas_and_stripe_stdio_proxy,
    audit_tau2_pine_voice_denominator_and_judge_override,
    audit_ucp_lodging_schedule_vat_and_profile_304,
    audit_x402_mcp_payment_mismatch_and_spend_controls,
    validate_x402_avm_galachain_bch_and_bazaar_no_eval,
    validate_x402_svm_confirmation_and_restart_refund,
    verify_x402_batch_total_claimed_and_minimum_advance,
)


class Stage132GuardTests(unittest.TestCase):
    def test_x402_batch_total_claimed_svm_and_mcp_mismatch_guards(self) -> None:
        # #3655 / #3661: Missing on-chain totalClaimed when local channel is absent must reject
        missing_onchain = verify_x402_batch_total_claimed_and_minimum_advance(
            local_channel_baseline_minor=None,
            facilitator_onchain_total_claimed_minor=None,
            requested_amount_minor=500,
            voucher_max_claimable_minor=500,
        )
        self.assertFalse(missing_onchain.allowed)
        self.assertEqual(
            missing_onchain.reason_code,
            "X402_BATCH_MISSING_ONCHAIN_TOTAL_CLAIMED_BASELINE",
        )

        # #3655 / #3661: Voucher must advance maxClaimableAmount >= totalClaimed + requested
        under_advance = verify_x402_batch_total_claimed_and_minimum_advance(
            local_channel_baseline_minor=None,
            facilitator_onchain_total_claimed_minor=2000,
            requested_amount_minor=500,
            voucher_max_claimable_minor=2300,
        )
        self.assertFalse(under_advance.allowed)
        self.assertEqual(
            under_advance.reason_code,
            "X402_BATCH_VOUCHER_BELOW_SETTLED_PLUS_AMOUNT_MINIMUM",
        )

        valid_advance = verify_x402_batch_total_claimed_and_minimum_advance(
            local_channel_baseline_minor=None,
            facilitator_onchain_total_claimed_minor=2000,
            requested_amount_minor=500,
            voucher_max_claimable_minor=2500,
        )
        self.assertTrue(valid_advance.allowed)

        # #3653 & #3637: SVM confirmation & restart server-signed refund
        pending = validate_x402_svm_confirmation_and_restart_refund(
            commitment_status="processed",
            typed_onchain_failure_error=False,
            rpc_timeout_or_malformed=False,
        )
        self.assertTrue(pending.allowed)
        self.assertEqual(pending.confirmation_disposition, "pending_store")

        terminal = validate_x402_svm_confirmation_and_restart_refund(
            commitment_status="finalized",
            typed_onchain_failure_error=True,
            rpc_timeout_or_malformed=False,
        )
        self.assertFalse(terminal.allowed)

        restored = validate_x402_svm_confirmation_and_restart_refund(
            commitment_status="finalized",
            typed_onchain_failure_error=False,
            rpc_timeout_or_malformed=False,
            is_restart_refund_lookup=True,
            requested_mode="server",
            operator_pubkey="op_svm_1",
            allowed_server_signed_operators=("op_svm_1",),
            durable_storage_channels={
                "chan_99": {"mode": "server", "operator": "op_svm_1"}
            },
        )
        self.assertTrue(restored.allowed)
        self.assertEqual(restored.restored_channel_id, "chan_99")

        # #3643 / #3631 / #3630: MCP dual representation mismatch & spendControls timeout cap
        mismatch = audit_x402_mcp_payment_mismatch_and_spend_controls(
            structured_payment_required={
                "accepts": [
                    {
                        "scheme": "exact",
                        "network": "eip155:8453",
                        "asset": "USDC",
                        "payTo": "0xMerchant",
                        "amount": "5000",
                    }
                ]
            },
            text_payment_required_json=json.dumps(
                {
                    "accepts": [
                        {
                            "scheme": "exact",
                            "network": "eip155:8453",
                            "asset": "USDC",
                            "payTo": "0xAttacker",
                            "amount": "5000",
                        }
                    ]
                }
            ),
            requested_max_timeout_seconds=120,
            client_max_timeout_seconds_cap=300,
        )
        self.assertFalse(mismatch.allowed)
        self.assertEqual(
            mismatch.reason_code, "X402_MCP_PAYMENT_REQUIRED_MISMATCH_ERROR"
        )

        # Benign 2 vs 2.0 numeric formatting passes, while excessive timeout fails
        timeout_exceeded = audit_x402_mcp_payment_mismatch_and_spend_controls(
            structured_payment_required={"accepts": [{"amount": "2"}]},
            text_payment_required_json=json.dumps({"accepts": [{"amount": "2.0"}]}),
            requested_max_timeout_seconds=86400 * 365,
            client_max_timeout_seconds_cap=300,
        )
        self.assertFalse(timeout_exceeded.allowed)
        self.assertEqual(
            timeout_exceeded.reason_code, "X402_SPEND_CONTROLS_MAX_TIMEOUT_EXCEEDED"
        )

    def test_x402_avm_bazaar_and_ucp_lodging_vat_guards(self) -> None:
        avm_ok = validate_x402_avm_galachain_bch_and_bazaar_no_eval(
            registered_avm_networks=("algorand:mainnet-v1.0",),
            requested_avm_network="algorand:wGHE2Pwdvd7S12BL5FaOP20EGYesN73ktiC1qzkkit8=",
            bazaar_runtime_allows_eval=False,
            bazaar_attempted_schema_codegen=False,
        )
        self.assertTrue(avm_ok.allowed)
        self.assertEqual(avm_ok.resolved_avm_network, "algorand:mainnet-v1.0")

        no_eval_fail = validate_x402_avm_galachain_bch_and_bazaar_no_eval(
            registered_avm_networks=("algorand:mainnet-v1.0",),
            requested_avm_network="algorand:mainnet-v1.0",
            bazaar_runtime_allows_eval=False,
            bazaar_attempted_schema_codegen=True,
        )
        self.assertFalse(no_eval_fail.allowed)

        # UCP #932 304 permitted on conditional request, #808 schedule, #680 VAT gross total
        schedule = (
            {"cutoff_epoch": 1000, "outcome_type": "free"},
            {"cutoff_epoch": 2000, "outcome_type": "nights", "nights": 1},
            {"cutoff_epoch": 3000, "outcome_type": "percentage", "basis_points": 10000},
        )
        ucp_ok = audit_ucp_lodging_schedule_vat_and_profile_304(
            profile_http_status=304,
            has_conditional_etag_or_last_modified=True,
            ucp_schema_version="1.4.1",
            booking_total_minor=45000,
            nightly_rate_minor=15000,
            cancellation_timestamp_epoch=2500,
            cancellation_schedule=schedule,
            tax_inclusive_vat_jurisdiction=True,
            items_gross_minor=11900,
            shipping_gross_minor=500,
            tax_breakdown_entries_minor=(1400, 350),
            reported_order_total_minor=12400,
        )
        self.assertTrue(ucp_ok.allowed)
        self.assertEqual(ucp_ok.calculated_cancellation_fee_minor, 15000)
        self.assertEqual(ucp_ok.gross_vat_total_minor, 12400)

        vat_double_added = audit_ucp_lodging_schedule_vat_and_profile_304(
            profile_http_status=200,
            has_conditional_etag_or_last_modified=False,
            ucp_schema_version="1.4.1",
            booking_total_minor=45000,
            nightly_rate_minor=15000,
            cancellation_timestamp_epoch=1500,
            cancellation_schedule=schedule,
            tax_inclusive_vat_jurisdiction=True,
            items_gross_minor=11900,
            shipping_gross_minor=500,
            tax_breakdown_entries_minor=(1400, 350),
            reported_order_total_minor=14150,
        )
        self.assertFalse(vat_double_added.allowed)
        self.assertEqual(
            vat_double_added.reason_code,
            "UCP_VAT_TAX_INCLUSIVE_GROSS_TOTAL_MISMATCH",
        )

    def test_mcp_provenance_mpas_stripe_proxy_and_tau2_guards(self) -> None:
        chain = (
            {
                "allowed_repos": ("org/repo-a", "org/repo-b"),
                "max_spend_minor": 10000,
            },
            {
                "allowed_repos": ("org/repo-a",),
                "max_spend_minor": 4000,
            },
        )
        mcp_ok = audit_mcp_provenance_mpas_and_stripe_stdio_proxy(
            delegation_chain_bounds=chain,
            requested_repository="org/repo-a",
            requested_spend_minor=3500,
            mpas_required_approvers=2,
            mpas_collected_distinct_approvers=("alice", "bob"),
            mcp_initialize_client_name="cursor",
            stdio_transport_created_before_initialize=False,
        )
        self.assertTrue(mcp_ok.allowed)
        self.assertEqual(mcp_ok.effective_user_agent, "stripe-mcp-local/0.3.1 (cursor)")
        self.assertEqual(mcp_ok.confined_max_spend_minor, 4000)

        repo_escalation = audit_mcp_provenance_mpas_and_stripe_stdio_proxy(
            delegation_chain_bounds=chain,
            requested_repository="org/repo-b",
            requested_spend_minor=2000,
            mpas_required_approvers=2,
            mpas_collected_distinct_approvers=("alice", "bob"),
            mcp_initialize_client_name="cursor",
            stdio_transport_created_before_initialize=False,
        )
        self.assertFalse(repo_escalation.allowed)
        self.assertEqual(
            repo_escalation.reason_code,
            "MCP_PROVENANCE_AUTHORITY_ESCALATION_REPO_OUT_OF_BOUNDS",
        )

        tau2_ok = audit_tau2_pine_voice_denominator_and_judge_override(
            domain="telecom",
            passed_tasks=98,
            infra_failed_tasks=1,
            reported_denominator=114,
            cli_judge_llm="gpt-5.2-judge",
            evaluator_used_judge_llm="gpt-5.2-judge",
        )
        self.assertTrue(tau2_ok.allowed)
        self.assertAlmostEqual(tau2_ok.effective_pass_rate, 98 / 114, places=4)

        tau2_trimmed = audit_tau2_pine_voice_denominator_and_judge_override(
            domain="telecom",
            passed_tasks=98,
            infra_failed_tasks=4,
            reported_denominator=110,
            cli_judge_llm="gpt-5.2-judge",
            evaluator_used_judge_llm="gpt-5.2-judge",
        )
        self.assertFalse(tau2_trimmed.allowed)
        self.assertEqual(
            tau2_trimmed.reason_code, "TAU2_VOICE_TRIMMED_DENOMINATOR_REJECTED"
        )


if __name__ == "__main__":
    unittest.main()
