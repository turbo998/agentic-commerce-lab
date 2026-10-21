"""Unit tests for Stage 130 guardrails."""

from __future__ import annotations

import unittest

from lab.x402_svm_batch_mcp_raw_ucp_status_constraints_stripe_ua_tau2_infra_guard import (
    evaluate_stripe_mcp_security_and_tau2_metrics_guard,
    evaluate_ucp_status_binding_constraints_and_spt_guard,
    evaluate_x402_enclave_evidence_refund_and_transport_guard,
    evaluate_x402_svm_batch_mcp_raw_and_evm_cardano_guard,
)


class Stage130GuardTest(unittest.TestCase):
    def test_x402_svm_batch_mcp_raw_and_evm_cardano_guard(self) -> None:
        ok = evaluate_x402_svm_batch_mcp_raw_and_evm_cardano_guard()
        self.assertTrue(ok.allowed)

        store_open = evaluate_x402_svm_batch_mcp_raw_and_evm_cardano_guard(
            after_verify_store_failed=True,
            request_refused_on_store_failure=False,
        )
        self.assertFalse(store_open.allowed)
        self.assertEqual(store_open.code, "X402_SVM_BATCH_AFTER_VERIFY_STORE_FAILED_OPEN_BLOCKED")

        bad_cardano = evaluate_x402_svm_batch_mcp_raw_and_evm_cardano_guard(
            cardano_re_serialized_cbor_with_tag_258=True,
        )
        self.assertFalse(bad_cardano.allowed)
        self.assertEqual(bad_cardano.code, "X402_CARDANO_SIGNED_CBOR_RESERIALIZED_TAG258_BLOCKED")

    def test_x402_enclave_evidence_refund_and_transport_guard(self) -> None:
        ok = evaluate_x402_enclave_evidence_refund_and_transport_guard(refund_requested=True)
        self.assertTrue(ok.allowed)

        over_refund = evaluate_x402_enclave_evidence_refund_and_transport_guard(
            refund_requested=True,
            refund_amount_minor=900,
            paid_amount_minor=1000,
            already_refunded_minor=200,
        )
        self.assertFalse(over_refund.allowed)
        self.assertEqual(over_refund.code, "X402_REFUND_EXTENSION_POLICY_OR_OVERREFUND_BLOCKED")

    def test_ucp_and_stripe_mcp_tau2_guards(self) -> None:
        ok_ucp = evaluate_ucp_status_binding_constraints_and_spt_guard()
        self.assertTrue(ok_ucp.allowed)

        bad_status = evaluate_ucp_status_binding_constraints_and_spt_guard(
            is_resource_response=True,
            ucp_status="error",
        )
        self.assertFalse(bad_status.allowed)
        self.assertEqual(bad_status.code, "UCP_RESOURCE_RESPONSE_ERROR_STATUS_BLOCKED")

        ok_tau = evaluate_stripe_mcp_security_and_tau2_metrics_guard()
        self.assertTrue(ok_tau.allowed)

        crlf = evaluate_stripe_mcp_security_and_tau2_metrics_guard(
            client_name="bad\r\nX-Injected: 1",
        )
        self.assertFalse(crlf.allowed)
        self.assertEqual(crlf.code, "STRIPE_USER_AGENT_CLIENT_NAME_HEADER_INJECTION_BLOCKED")


if __name__ == "__main__":
    unittest.main()
