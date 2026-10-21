"""Unit tests for Stage 128 guardrails."""

from __future__ import annotations

import unittest

from lab.x402_mcp_approval_voucher_skip_ucp_offer_location_mcp_failure_tau2_abort_guard import (
    evaluate_stripe_mcp_tool_failure_and_tau2_abort_guard,
    evaluate_ucp_offer_binding_location_and_validator_guard,
    evaluate_x402_mcp_approval_and_settlement_guard,
    evaluate_x402_transport_and_scheme_extensions_guard,
    evaluate_x402_voucher_skip_gate_and_jcs_guard,
)


class Stage128GuardTest(unittest.TestCase):
    def test_x402_mcp_approval_and_settlement_guard(self) -> None:
        ok = evaluate_x402_mcp_approval_and_settlement_guard(
            is_payment_retry=True,
            approval_checked_on_retry=True,
            usage_charge_calculation_failed=True,
            charged_max_amount_on_calc_failure=False,
            cancel_attempted_on_calc_failure=True,
            cancel_outcome_uncertain=True,
            reported_confirmed_cancellation=False,
            receipt_processing_failed=True,
            tool_output_preserved=True,
        )
        self.assertTrue(ok.allowed)

        no_reapproval = evaluate_x402_mcp_approval_and_settlement_guard(
            is_payment_retry=True,
            approval_checked_on_retry=False,
            usage_charge_calculation_failed=False,
            charged_max_amount_on_calc_failure=False,
            cancel_attempted_on_calc_failure=True,
            cancel_outcome_uncertain=False,
            reported_confirmed_cancellation=False,
            receipt_processing_failed=False,
            tool_output_preserved=True,
        )
        self.assertFalse(no_reapproval.allowed)
        self.assertEqual(no_reapproval.code, "X402_MCP_PAYMENT_RETRY_BYPASSED_APPROVAL_BLOCKED")

        max_fallback = evaluate_x402_mcp_approval_and_settlement_guard(
            is_payment_retry=False,
            approval_checked_on_retry=True,
            usage_charge_calculation_failed=True,
            charged_max_amount_on_calc_failure=True,
            cancel_attempted_on_calc_failure=False,
            cancel_outcome_uncertain=False,
            reported_confirmed_cancellation=False,
            receipt_processing_failed=False,
            tool_output_preserved=True,
        )
        self.assertFalse(max_fallback.allowed)
        self.assertEqual(max_fallback.code, "X402_MCP_CALC_FAILURE_MAX_CHARGE_FALLBACK_BLOCKED")

    def test_x402_voucher_skip_gate_and_jcs_guard(self) -> None:
        ok = evaluate_x402_voucher_skip_gate_and_jcs_guard(
            voucher_manager="facilitator",
            facilitator_supported_modes=("server", "facilitator"),
        )
        self.assertTrue(ok.allowed)

        bad_skip = evaluate_x402_voucher_skip_gate_and_jcs_guard(
            skip_handler_returned=True,
            flow_has_before_handler_settle=True,
            before_handler_settle_executed=False,
        )
        self.assertFalse(bad_skip.allowed)
        self.assertEqual(bad_skip.code, "X402_SKIP_HANDLER_BYPASSED_BEFORE_HANDLER_SETTLE_BLOCKED")

        open_hook = evaluate_x402_voucher_skip_gate_and_jcs_guard(
            gate_hook_phase="beforeVerify",
            gate_hook_threw=True,
            failed_closed_on_hook_throw=False,
        )
        self.assertFalse(open_hook.allowed)
        self.assertEqual(open_hook.code, "X402_GATE_HOOK_THROW_FAILED_OPEN_BLOCKED")

        bad_jcs = evaluate_x402_voucher_skip_gate_and_jcs_guard(
            jcs_has_lone_surrogate=True,
        )
        self.assertFalse(bad_jcs.allowed)
        self.assertEqual(bad_jcs.code, "X402_OFFER_RECEIPT_RFC8785_JCS_VIOLATION_BLOCKED")

    def test_x402_transport_and_scheme_extensions_guard(self) -> None:
        ok = evaluate_x402_transport_and_scheme_extensions_guard()
        self.assertTrue(ok.allowed)

        bad_v1 = evaluate_x402_transport_and_scheme_extensions_guard(
            payload_version=1,
            v1_rejected_with_status=500,
        )
        self.assertFalse(bad_v1.allowed)
        self.assertEqual(bad_v1.code, "X402_PYTHON_HTTP_V1_PAYLOAD_500_CRASH_BLOCKED")

        bad_svm_v1 = evaluate_x402_transport_and_scheme_extensions_guard(
            svm_upto_actor="client",
            svm_upto_tx_version=1,
        )
        self.assertFalse(bad_svm_v1.allowed)
        self.assertEqual(bad_svm_v1.code, "X402_SVM_UPTO_CLIENT_V1_TRANSACTION_BLOCKED")

    def test_ucp_and_stripe_mcp_tau2_guards(self) -> None:
        ok_ucp = evaluate_ucp_offer_binding_location_and_validator_guard()
        self.assertTrue(ok_ucp.allowed)

        bad_offer = evaluate_ucp_offer_binding_location_and_validator_guard(
            uses_parallel_offers_available_array=True,
        )
        self.assertFalse(bad_offer.allowed)
        self.assertEqual(bad_offer.code, "UCP_CART_OFFER_PARALLEL_CARRIER_BLOCKED")

        bad_binding = evaluate_ucp_offer_binding_location_and_validator_guard(
            rule1_rejected_due_to_identity_omission=True,
        )
        self.assertFalse(bad_binding.allowed)
        self.assertEqual(bad_binding.code, "UCP_BINDING_RULE1_CONFLATED_WITH_IDENTITY_BLOCKED")

        ok_tau = evaluate_stripe_mcp_tool_failure_and_tau2_abort_guard()
        self.assertTrue(ok_tau.allowed)

        bad_abort = evaluate_stripe_mcp_tool_failure_and_tau2_abort_guard(
            simulator_emitted_out_of_scope=True,
            recorded_termination_reason="USER_STOP",
            assigned_reward_on_abort=1.0,
        )
        self.assertFalse(bad_abort.allowed)
        self.assertEqual(bad_abort.code, "TAU2_OUT_OF_SCOPE_ABORT_GRADED_AS_USER_STOP_BLOCKED")


if __name__ == "__main__":
    unittest.main()
