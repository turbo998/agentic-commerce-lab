"""Unit tests for Stage 56 deterministic guards."""

from __future__ import annotations

import unittest

from lab.ucp_rfc9728_pix_razorpay_acp_envelope_tau2_loan_guard import (
    canonicalize_tau2_banking_time_verified,
    verify_acp_delegate_auth_signature_and_error_envelope,
    verify_tau2_loan_servicing_and_time_canonicalization,
    verify_ucp_render_artifact_and_hosted_checkout_guard,
    verify_ucp_rfc9728_identity_linking_and_checkout_lifecycle,
)


class Stage56GuardTest(unittest.TestCase):
    def test_ucp_rfc9728_identity_linking_and_checkout_lifecycle(self) -> None:
        ok = verify_ucp_rfc9728_identity_linking_and_checkout_lifecycle(
            authorization_servers=(
                {
                    "candidate_issuer": "https://as1.example.com/tenant",
                    "rfc8414_status": 200,
                    "discovered_issuer": "https://as1.example.com/tenant/",  # trailing slash mismatch -> discarded
                    "platform_registered": True,
                },
                {
                    "candidate_issuer": "https://as2.example.com",
                    "rfc8414_status": 404,
                    "attempted_oidc_fallback": True,
                    "oidc_status": 200,
                    "discovered_issuer": "https://as2.example.com",
                    "platform_registered": True,
                },
            ),
            fulfillment_option={
                "id": "ship_std",
                "title": "Standard Ground",
                "description": "Arrives Oct 24-26 via UPS",
                "totals": [{"type": "total", "amount": 599}],
            },
            checkout_prev_status="ready_for_complete",
            checkout_next_status="incomplete",
        )
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.selected_issuer, "https://as2.example.com")
        self.assertEqual(ok.discarded_issuers, ("https://as1.example.com/tenant",))

        bad = verify_ucp_rfc9728_identity_linking_and_checkout_lifecycle(
            authorization_servers=(
                {
                    "candidate_issuer": "https://as1.example.com",
                    "rfc8414_status": 500,
                    "attempted_oidc_fallback": True,
                    "oidc_status": 200,
                    "discovered_issuer": "https://as1.example.com",
                },
            ),
            platform_normalized_issuer_before_compare=True,
            discarded_entries_logged=False,
            fulfillment_option={
                "id": "ship_bad",
                "title": "Express",
                "description": "Express delivery",
                "total": None,
            },
            checkout_prev_status="completed",
            checkout_next_status="incomplete",
        )
        self.assertFalse(bad.allowed)
        self.assertIn("UCP_RFC8414_ISSUER_NORMALIZATION_FORBIDDEN", bad.violations)
        self.assertIn("UCP_RFC8414_NON_404_FALLBACK_FORBIDDEN:https://as1.example.com:500", bad.violations)
        self.assertIn("UCP_FULFILLMENT_SCALAR_TOTAL_FIELD_FORBIDDEN", bad.violations)
        self.assertIn("UCP_CHECKOUT_INVALID_STATUS_TRANSITION:completed->incomplete", bad.violations)

    def test_ucp_render_artifact_and_hosted_checkout_guard(self) -> None:
        ok = verify_ucp_render_artifact_and_hosted_checkout_guard(
            render_action_instance={
                "id": "act_pix_01",
                "config": {
                    "type": "qr_code",
                    "code": "00020126580014br.gov.bcb.pix0136...",
                    "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==",
                    "instructions_url": "https://pay.mercadopago.com/pix/instructions/act_pix_01",
                    "expires_at": "2026-10-20T15:00:00Z",
                },
            },
            checkout_expires_at="2026-10-20T16:00:00Z",
            hosted_instrument={
                "type": "hosted_checkout",
                "display": {"name": "Pay with Razorpay", "logo_url": "https://cdn.razorpay.com/logo.png"},
                "credential": {
                    "type": "hosted_checkout",
                    "session_id": "order_AbCdEf123",
                    "return_url": "https://platform.example.com/checkout/return",
                    "cancel_url": "https://platform.example.com/checkout/cancel",
                },
            },
            buyer_redirected_to_cancel_url=True,
            platform_polled_checkout_after_cancel=True,
        )
        self.assertTrue(ok.allowed)

        bad = verify_ucp_render_artifact_and_hosted_checkout_guard(
            render_action_instance={
                "id": "act_pix_bad",
                "required": True,
                "config": {
                    "type": "qr_code",
                    "image": "javascript:alert(1)",
                    "instructions_url": "https://evil.example.com/phish",
                    "expires_at": "2026-10-20T18:00:00Z",
                    "otp": "123456",
                },
            },
            checkout_expires_at="2026-10-20T16:00:00Z",
            checkout_has_continue_url=True,
            hosted_instrument={
                "type": "hosted_checkout",
                "credential": {
                    "type": "hosted_checkout",
                    "return_url": "https://api.razorpay.com/v1/magic_checkout/chk_01",
                    "token": "tok_secret_leak",
                },
            },
            platform_attempted_credential_acquisition=True,
            buyer_redirected_to_cancel_url=True,
            platform_polled_checkout_after_cancel=False,
        )
        self.assertFalse(bad.allowed)
        self.assertIn("UCP_RENDER_ARTIFACT_INSTANCE_REQUIRED_FIELD_FORBIDDEN", bad.violations)
        self.assertIn("UCP_RENDER_ARTIFACT_FORBIDS_CONTINUE_URL_REDIRECT", bad.violations)
        self.assertIn("UCP_RENDER_ARTIFACT_EXPIRY_EXCEEDS_CHECKOUT", bad.violations)
        self.assertIn("UCP_RENDER_ARTIFACT_UNSAFE_IMAGE_URI", bad.violations)
        self.assertIn("UCP_RENDER_ARTIFACT_UNTRUSTED_INSTRUCTIONS_ORIGIN", bad.violations)
        self.assertIn("UCP_RENDER_ARTIFACT_SECRET_LEAK_BLOCKED:otp", bad.violations)
        self.assertIn("UCP_HOSTED_CHECKOUT_CREDENTIAL_ACQUISITION_FORBIDDEN", bad.violations)
        self.assertIn("UCP_HOSTED_CHECKOUT_RETURN_URL_EQUALS_CONTINUE_URL", bad.violations)
        self.assertIn("UCP_HOSTED_CHECKOUT_CANCEL_WITHOUT_AUTHORITATIVE_POLL", bad.violations)

    def test_acp_delegate_auth_signature_and_error_envelope(self) -> None:
        ok = verify_acp_delegate_auth_signature_and_error_envelope(
            delegate_auth_openapi_signature_required=True,
            delegate_auth_request_signature="ZXltZX...",
            checkout_create_request={
                "line_items": [{"id": "item_123"}],
                "currency": "usd",
                "capabilities": {},
            },
            delegate_payment_error_payload={
                "type": "invalid_request",
                "code": "invalid_card",
                "message": "card field is required when payment_method.type=card",
                "param": "payment_method.number",
            },
        )
        self.assertTrue(ok.allowed)

        bad = verify_acp_delegate_auth_signature_and_error_envelope(
            delegate_auth_openapi_signature_required=False,
            delegate_auth_request_signature="",
            checkout_create_request={"items": [{"id": "item_123", "product_id": "prod_1"}]},
            delegate_payment_error_payload={
                "error": {
                    "type": "invalid_request",
                    "code": "invalid_card",
                    "message": "wrapped error envelope",
                }
            },
        )
        self.assertFalse(bad.allowed)
        self.assertIn("ACP_DELEGATE_AUTH_SIGNATURE_MISSING", bad.violations)
        self.assertIn("ACP_CHECKOUT_CREATE_LEGACY_ITEMS_FIELD_REJECTED", bad.violations)
        self.assertIn("ACP_DELEGATE_PAYMENT_WRAPPED_ERROR_ENVELOPE_REJECTED", bad.violations)

    def test_tau2_loan_servicing_and_time_canonicalization(self) -> None:
        for equivalent in (
            "2025-11-14 03:40:00 EST",
            "2025-11-14T03:40:00",
            "2025-11-14 03:40 EST",
            "2025-11-14T03:40:00-05:00",
            "The current time is 2025-11-14 03:40:00 EST.",
        ):
            self.assertEqual(canonicalize_tau2_banking_time_verified(equivalent), "2025-11-14 03:40:00 EST")

        ok = verify_tau2_loan_servicing_and_time_canonicalization(
            caller_role="borrower",
            verified_fields=("full_name", "date_of_birth", "postal_code"),
            requested_action_kind="write_payment",
            explicit_yes_confirmed_before_write=True,
            waiver_requested_with_payment=True,
            waiver_processed_before_payment=True,
            waiver_fee_amount_cad=35.0,
            waiver_loan_status="past_due_30",
            banking_time_verified_input="The current time is 2025-11-14 03:40:00 EST.",
        )
        self.assertTrue(ok.allowed)

        bad = verify_tau2_loan_servicing_and_time_canonicalization(
            caller_role="authorized_third_party",
            verified_fields=("full_name", "date_of_birth"),
            failed_verification_attempts=2,
            transferred_reason=None,
            requested_action_kind="write_waive_fee",
            explicit_yes_confirmed_before_write=False,
            tool_calls_in_turn=2,
            messaged_borrower_in_same_turn_as_tool=True,
            waiver_requested_with_payment=True,
            waiver_processed_before_payment=False,
            waiver_fee_amount_cad=75.0,
            email_changed_in_conversation=True,
            document_sent_in_conversation=True,
            banking_time_verified_input="2025-11-14T03:40:00Z",
        )
        self.assertFalse(bad.allowed)
        self.assertIn("TAU2_LOAN_DOUBLE_VERIFICATION_FAILURE_MUST_TRANSFER", bad.violations)
        self.assertIn("TAU2_LOAN_CALLER_NOT_VERIFIED", bad.violations)
        self.assertIn("TAU2_LOAN_THIRD_PARTY_WRITE_OR_DOC_FORBIDDEN", bad.violations)
        self.assertIn("TAU2_LOAN_WRITE_WITHOUT_CONFIRMATION", bad.violations)
        self.assertIn("TAU2_LOAN_TOOL_AND_MESSAGE_SAME_TURN_FORBIDDEN", bad.violations)
        self.assertIn("TAU2_LOAN_PAYMENT_BEFORE_WAIVER_ORDER_VIOLATION", bad.violations)
        self.assertIn("TAU2_LOAN_DOC_AFTER_EMAIL_CHANGE_BLOCKED", bad.violations)


if __name__ == "__main__":
    unittest.main()
