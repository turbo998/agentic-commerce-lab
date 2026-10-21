"""Unit tests for Stage 122 x402 CORS/streams/facilitator, UCP business/ECDSA/escalation/terms,
and Stripe deps/stream + tau-bench tau-Authority guards."""

from __future__ import annotations

import base64
import unittest

from lab.x402_cors_streams_ucp_business_ecdsa_stripe_deps_streams_tau2_authority_guard import (
    validate_stripe_deps_stream_and_tau2_authority,
    validate_ucp_business_ecdsa_escalation_and_terms,
    validate_x402_cors_streams_and_facilitator,
)


class Stage122GuardTests(unittest.TestCase):
    def test_x402_cors_streams_and_facilitator_valid_and_blocks_missing_cors(self) -> None:
        res = validate_x402_cors_streams_and_facilitator(
            is_browser_cross_origin=True,
            access_control_expose_headers=["PAYMENT-REQUIRED", "PAYMENT-RESPONSE"],
            access_control_allow_headers=["PAYMENT-SIGNATURE", "Content-Type"],
            preflight_status_code=204,
            payment_required_header_bytes=9200,
            intermediate_stream_released=True,
            is_internal_corrective_402=True,
            restarted_initial_payment_flow=False,
            facilitator_http_status=503,
            facilitator_error_code="settlement_pending",
            settlement_retry_count=0,
            non_browser_402_body_has_reason=True,
            selected_network="sui:mainnet",
            selected_pay_to="0xAbC123",
            expected_pay_to="0xabc123",
            selected_amount_minor=500,
            expected_max_amount_minor=1000,
            svm_async_uses_blocking_rpc=False,
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.header_warning_level, "warn_8kb_aiohttp")
        self.assertTrue(res.should_retry_settlement)

        bad = validate_x402_cors_streams_and_facilitator(
            is_browser_cross_origin=True,
            access_control_expose_headers=["Content-Length"],
            access_control_allow_headers=["PAYMENT-SIGNATURE"],
            preflight_status_code=204,
            payment_required_header_bytes=1200,
            intermediate_stream_released=True,
            is_internal_corrective_402=False,
            restarted_initial_payment_flow=False,
            facilitator_http_status=200,
            facilitator_error_code=None,
            settlement_retry_count=0,
            non_browser_402_body_has_reason=True,
            selected_network="sui:mainnet",
            selected_pay_to="0xabc123",
            expected_pay_to="0xabc123",
            selected_amount_minor=500,
            expected_max_amount_minor=1000,
            svm_async_uses_blocking_rpc=False,
        )
        self.assertFalse(bad.allowed)
        self.assertEqual(
            bad.reason_code, "X402_BROWSER_CORS_HEADER_OR_PREFLIGHT_MISSING"
        )

    def test_ucp_business_ecdsa_escalation_and_terms_valid_and_blocks_der(self) -> None:
        raw_p256 = base64.b64encode(b"\x11" * 64).decode("ascii")
        res = validate_ucp_business_ecdsa_escalation_and_terms(
            business_profile={
                "display_name": "Acme Global",
                "website": "https://acme.example.com",
            },
            curve="P-256",
            signature_b64=raw_p256,
            checkout_status="requires_escalation",
            continue_url="https://acme.example.com/checkout/escalate",
            is_deferred_payment_term=True,
            complete_checkout_payment_obj={},
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.signature_byte_length, 64)

        der_sig = base64.b64encode(b"\x30\x45\x02\x21" + b"\x22" * 67).decode("ascii")
        bad = validate_ucp_business_ecdsa_escalation_and_terms(
            business_profile={
                "display_name": "Acme Global",
                "website": "https://acme.example.com",
            },
            curve="P-256",
            signature_b64=der_sig,
            checkout_status="ready_for_complete",
            continue_url=None,
            is_deferred_payment_term=False,
            complete_checkout_payment_obj=None,
        )
        self.assertFalse(bad.allowed)
        self.assertEqual(
            bad.reason_code, "UCP_ECDSA_SIGNATURE_ASN1_DER_OR_WRONG_RAW_WIDTH"
        )

    def test_stripe_deps_stream_and_tau2_authority_valid_and_blocks_legacy_actions(
        self,
    ) -> None:
        res = validate_stripe_deps_stream_and_tau2_authority(
            mcp_major_version=1,
            strands_extra_package="strands-agents",
            openai_extra_package="openai-agents",
            configuration_keys=["context"],
            caller_broke_stream_early=True,
            unawaited_background_tee_used=False,
            source_iterator_closed_on_break=True,
            authenticated_customer_id="user_42",
            target_resource_owner_id="user_42",
            policy_permits_mutation=True,
            voice_submission_has_commit_and_recordings=True,
        )
        self.assertTrue(res.allowed)
        self.assertTrue(res.source_stream_closed)

        bad = validate_stripe_deps_stream_and_tau2_authority(
            mcp_major_version=1,
            strands_extra_package="strands-agents",
            openai_extra_package="openai-agents",
            configuration_keys=["context", "actions"],
            caller_broke_stream_early=False,
            unawaited_background_tee_used=False,
            source_iterator_closed_on_break=True,
            authenticated_customer_id="user_42",
            target_resource_owner_id="user_42",
            policy_permits_mutation=True,
            voice_submission_has_commit_and_recordings=True,
        )
        self.assertFalse(bad.allowed)
        self.assertEqual(
            bad.reason_code,
            "STRIPE_CONFIGURATION_LEGACY_ACTIONS_IGNORED_PRIVILEGE_RISK",
        )


if __name__ == "__main__":
    unittest.main()
