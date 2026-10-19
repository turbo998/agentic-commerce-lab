"""Unit tests for Stage 42 (`lab/ucp_payment_finality_order_access_acp_india_guard.py`)."""

from __future__ import annotations

import unittest

from lab.ucp_payment_finality_order_access_acp_india_guard import (
    evaluate_acp_razorpay_upi_s2s_and_feed_extensions_guard,
    evaluate_ucp_checkout_payment_finality_and_order_reporting_guard,
    evaluate_ucp_guest_order_access_and_rest_response_binding_guard,
    evaluate_ucp_token_context_buyer_consent_and_correspondence_guard,
)


class TestStage42UcpPaymentFinalityOrderAccessAcpIndiaGuard(unittest.TestCase):
    def test_ucp_payment_finality_and_order_reporting_guard(self) -> None:
        # 1. Valid provisional checkout + order reporting (including historical retry sum > maximum_amount)
        ok = evaluate_ucp_checkout_payment_finality_and_order_reporting_guard(
            {
                "checkout_totals": [
                    {"type": "subtotal", "amount": 5000},
                    {"type": "tax", "amount": 400},
                    {"type": "total", "amount": 5400, "amount_finality": "provisional"},
                ],
                "checkout_payment": {"maximum_amount": 6000},
                "buyer_disclosed_provisional_ceiling": True,
                "historical_replaced_auth_or_retried_capture_minor": 10800,
                "order_payment": {
                    "maximum_amount": 6000,
                    "instruments": [
                        {
                            "id": "pi_gift",
                            "type": "gift_card",
                            "captured_amount": 1000,
                            "display": {"description": "Gift card", "last_digits": "9821"},
                        },
                        {
                            "id": "pi_card",
                            "type": "card",
                            "authorized_amount": 0,
                            "captured_amount": 4800,
                            "display": {"brand": "visa", "last_digits": "4242"},
                        },
                    ],
                },
            }
        )
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.decision_code, "UCP_PAYMENT_FINALITY_AND_ORDER_REPORTING_VERIFIED")
        self.assertEqual(ok.approved_maximum_amount_minor, 6000)
        self.assertEqual(ok.active_collected_or_authorized_minor, 5800)
        self.assertTrue(ok.historical_retry_sum_ignored)

        # 2. Non-aggregate total carrying amount_finality -> blocked
        bad_non_agg = evaluate_ucp_checkout_payment_finality_and_order_reporting_guard(
            {
                "checkout_totals": [
                    {"type": "subtotal", "amount": 5000, "amount_finality": "provisional"},
                    {"type": "total", "amount": 5400},
                ]
            }
        )
        self.assertFalse(bad_non_agg.allowed)
        self.assertEqual(bad_non_agg.decision_code, "NON_AGGREGATE_TOTAL_AMOUNT_FINALITY_FORBIDDEN")

        # 3. Final total carrying checkout.payment.maximum_amount -> blocked
        bad_final_max = evaluate_ucp_checkout_payment_finality_and_order_reporting_guard(
            {
                "checkout_totals": [
                    {"type": "total", "amount": 5400, "amount_finality": "final"},
                ],
                "checkout_payment": {"maximum_amount": 5400},
            }
        )
        self.assertFalse(bad_final_max.allowed)
        self.assertEqual(bad_final_max.decision_code, "FINAL_TOTAL_MAXIMUM_AMOUNT_MUST_BE_OMITTED")

        # 4. Order instrument leaking credential or handler_id -> blocked
        bad_leak = evaluate_ucp_checkout_payment_finality_and_order_reporting_guard(
            {
                "checkout_totals": [{"type": "total", "amount": 5400}],
                "order_payment": {
                    "maximum_amount": 5400,
                    "instruments": [
                        {
                            "id": "pi_card",
                            "type": "card",
                            "handler_id": "stripe_handler",
                            "credential": {"type": "card", "token": "tok_leak"},
                            "display": {"brand": "visa", "last_digits": "4242"},
                        }
                    ],
                },
            }
        )
        self.assertFalse(bad_leak.allowed)
        self.assertEqual(
            bad_leak.decision_code,
            "ORDER_PAYMENT_INSTRUMENT_FORBIDDEN_CHECKOUT_OR_CREDENTIAL_FIELD_LEAK",
        )

        # 5. Active collection exceeding order.payment.maximum_amount without separate approval -> blocked
        bad_over = evaluate_ucp_checkout_payment_finality_and_order_reporting_guard(
            {
                "checkout_totals": [
                    {"type": "total", "amount": 5400, "amount_finality": "provisional"}
                ],
                "checkout_payment": {"maximum_amount": 6000},
                "order_payment": {
                    "maximum_amount": 6000,
                    "instruments": [
                        {
                            "id": "pi_card",
                            "type": "card",
                            "captured_amount": 6500,
                            "display": {"brand": "visa", "last_digits": "4242"},
                        }
                    ],
                },
            }
        )
        self.assertFalse(bad_over.allowed)
        self.assertEqual(
            bad_over.decision_code,
            "PROVISIONAL_ORDER_COLLECTION_EXCEEDS_MAXIMUM_AMOUNT_BLOCKED",
        )

    def test_ucp_guest_order_access_and_rest_response_binding_guard(self) -> None:
        base_ctx = {
            "issued_order_id": "order_abc123",
            "requested_order_id": "order_abc123",
            "operation_name": "get_order",
            "issued_access": {
                "token": "oat_3f9a1c7e5b2d48a6",
                "expires_at": "2026-10-20T00:00:00Z",
                "scopes": ["dev.ucp.shopping.order:read"],
            },
            "presented_access_token": "oat_3f9a1c7e5b2d48a6",
            "permalink_url": "https://business.example.com/orders/abc123",
            "now_epoch": 1_760_000_000,
            "expires_at_epoch": 1_760_003_600,
            "transport": "REST",
            "cache_control_header": "no-store, max-age=0",
            "rotated_access": {"token": "oat_9988776655443322"},
            "rest_response_signature": {
                "covered_components": [
                    "@status",
                    "@authority;req",
                    "@method;req",
                    "@path;req",
                    "@query;req",
                    "content-digest",
                    "content-type",
                ],
                "client_sent_request": {
                    "authority": "business.example.com",
                    "method": "GET",
                    "path": "/orders/order_abc123",
                    "query": "?access_token=oat_3f9a1c7e5b2d48a6",
                },
                "signed_request_context": {
                    "authority": "business.example.com",
                    "method": "GET",
                    "path": "/orders/order_abc123",
                    "query": "?access_token=oat_3f9a1c7e5b2d48a6",
                },
                "created_epoch": 1_759_999_950,
                "max_freshness_window_sec": 300,
                "rebuilt_req_components_from_response_echo": False,
            },
        }
        ok = evaluate_ucp_guest_order_access_and_rest_response_binding_guard(base_ctx)
        self.assertTrue(ok.allowed)
        self.assertTrue(ok.rotated_token_issued)

        # Cross-order enumeration -> blocked
        bad_enum = dict(base_ctx, requested_order_id="order_xyz999")
        res_enum = evaluate_ucp_guest_order_access_and_rest_response_binding_guard(bad_enum)
        self.assertFalse(res_enum.allowed)
        self.assertEqual(
            res_enum.decision_code, "ORDER_ACCESS_CREDENTIAL_CROSS_ORDER_ENUMERATION_BLOCKED"
        )

        # Guest order claimed into account without revoking standing guest token -> blocked
        bad_claim = dict(
            base_ctx,
            guest_order_claimed_into_account=True,
            credential_revoked_on_claim=False,
        )
        res_claim = evaluate_ucp_guest_order_access_and_rest_response_binding_guard(bad_claim)
        self.assertFalse(res_claim.allowed)
        self.assertEqual(
            res_claim.decision_code, "CLAIMED_ACCOUNT_GUEST_ORDER_CREDENTIAL_NOT_REVOKED"
        )

        # Signed REST response replayed from a different path or stale window (#699) -> blocked
        bad_replay = dict(base_ctx)
        bad_replay["rest_response_signature"] = {
            **base_ctx["rest_response_signature"],
            "signed_request_context": {
                "authority": "business.example.com",
                "method": "GET",
                "path": "/orders/order_other",
                "query": "?access_token=oat_3f9a1c7e5b2d48a6",
            },
        }
        res_replay = evaluate_ucp_guest_order_access_and_rest_response_binding_guard(bad_replay)
        self.assertFalse(res_replay.allowed)
        self.assertEqual(
            res_replay.decision_code,
            "REST_RESPONSE_SIGNATURE_REQUEST_BINDING_OR_FRESHNESS_FAILED",
        )

    def test_ucp_token_context_buyer_consent_and_correspondence_guard(self) -> None:
        base_ctx = {
            "token_credential_context": {
                "issued_binding": "chk_bind_001",
                "platform_forwarded_binding": "chk_bind_001",
                "processor_expected_binding": "chk_bind_001",
                "issued_identity": "merchant_part_01",
                "platform_forwarded_identity": "merchant_part_01",
                "caller_authenticated_independently": True,
                "accepted_identity_as_caller_auth": False,
            },
            "prior_buyer_consent": {"marketing": False, "analytics": False},
            "update_buyer_payload": {"email": "alice@example.com"},
            "advertised_default_consent": {"marketing": True, "analytics": True},
            "business_applied_consent": {"marketing": False, "analytics": False},
            "correspondence": {
                "status": "agrees",
                "compared": [
                    {"field": "$.totals", "prior_value": 5400, "current_value": 5400},
                    {"field": "$.currency", "prior_value": "USD", "current_value": "USD"},
                ],
            },
            "adjustment": {
                "type": "dispute",
                "cause": {
                    "category": "amount_divergence",
                    "attributed_to": "business",
                    "nature": "undetermined",
                    "false_assertion_of_fact_proven": False,
                    "treated_as_binding_liability_adjudication": False,
                },
            },
        }
        ok = evaluate_ucp_token_context_buyer_consent_and_correspondence_guard(base_ctx)
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.effective_buyer_consent, {"marketing": False, "analytics": False})

        # Full-replacement update dropping buyer.consent to advertised opt-in defaults (#660) -> blocked
        bad_consent = dict(
            base_ctx,
            business_applied_consent={"marketing": True, "analytics": True},
        )
        res_consent = evaluate_ucp_token_context_buyer_consent_and_correspondence_guard(bad_consent)
        self.assertFalse(res_consent.allowed)
        self.assertEqual(
            res_consent.decision_code,
            "BUYER_CONSENT_DROPPED_ON_FULL_REPLACEMENT_UPDATE_BLOCKED",
        )

        # Accepting TokenCredential.identity as caller authentication (#792) -> blocked
        bad_auth = dict(
            base_ctx,
            token_credential_context={
                **base_ctx["token_credential_context"],
                "accepted_identity_as_caller_auth": True,
            },
        )
        res_auth = evaluate_ucp_token_context_buyer_consent_and_correspondence_guard(bad_auth)
        self.assertFalse(res_auth.allowed)
        self.assertEqual(
            res_auth.decision_code,
            "TOKEN_CREDENTIAL_IDENTITY_ACCEPTED_AS_CALLER_AUTH_BLOCKED",
        )

        # Treating correspondence `unverifiable` as `agrees` (#836) -> blocked
        bad_corr = dict(
            base_ctx,
            correspondence={
                "status": "unverifiable",
                "reader_treated_unverifiable_as_agrees": True,
            },
        )
        res_corr = evaluate_ucp_token_context_buyer_consent_and_correspondence_guard(bad_corr)
        self.assertFalse(res_corr.allowed)
        self.assertEqual(
            res_corr.decision_code,
            "UNVERIFIABLE_CORRESPONDENCE_TREATED_AS_AGREES_BLOCKED",
        )

        # Recording `fraud` nature when false assertion is unproven (#837) -> blocked
        bad_adj = dict(
            base_ctx,
            adjustment={
                "type": "dispute",
                "cause": {
                    "category": "terms_not_honored",
                    "attributed_to": "buyer",
                    "nature": "fraud",
                    "false_assertion_of_fact_proven": False,
                },
            },
        )
        res_adj = evaluate_ucp_token_context_buyer_consent_and_correspondence_guard(bad_adj)
        self.assertFalse(res_adj.allowed)
        self.assertEqual(
            res_adj.decision_code,
            "ADJUSTMENT_CAUSE_UNPROVEN_FRAUD_OR_LIABILITY_CONFLATION_BLOCKED",
        )

    def test_acp_razorpay_upi_s2s_and_feed_extensions_guard(self) -> None:
        base_ctx = {
            "checkout_session_id": "cs_india_001",
            "now_epoch": 1_760_000_000,
            "upi_intent_context": {
                "currency": "INR",
                "amount_minor": 4_500_00,  # ₹4,500.00
                "intent_url": "upi://pay?pa=merchant@razorpay&pn=Acme&am=4500.00&cu=INR&tr=cs_india_001",
                "expires_at_epoch": 1_760_000_300,
            },
            "s2s_card_context": {
                "currency": "INR",
                "token_id": "token_rbi_coft_998877",
                "token_merchant_id": "merch_in_01",
                "request_merchant_id": "merch_in_01",
            },
            "feed_extensions_context": {
                "metadata_extensions": [
                    {
                        "name": "sustainability",
                        "extends": "$.ProductFeed",
                        "schema": "https://merchant.example/schemas/sustainability/v1.json",
                        "spec": "https://merchant.example/docs/sustainability",
                    }
                ],
                "record_extension_names": ["sustainability"],
                "auto_fetch_untrusted_external_schema": False,
            },
        }
        ok = evaluate_acp_razorpay_upi_s2s_and_feed_extensions_guard(base_ctx)
        self.assertTrue(ok.allowed)

        # UPI Intent exceeding ₹1,00,000 NPCI cap (#217) -> blocked
        bad_upi = dict(
            base_ctx,
            upi_intent_context={
                **base_ctx["upi_intent_context"],
                "amount_minor": 15_000_000,  # ₹1,50,000
            },
        )
        res_upi = evaluate_acp_razorpay_upi_s2s_and_feed_extensions_guard(bad_upi)
        self.assertFalse(res_upi.allowed)
        self.assertEqual(res_upi.decision_code, "ACP_UPI_INTENT_CAP_OR_TR_BINDING_VIOLATION")

        # S2S Card carrying raw PAN or cross-merchant CoFT token (#218) -> blocked
        bad_s2s = dict(
            base_ctx,
            s2s_card_context={
                **base_ctx["s2s_card_context"],
                "pan": "4111111111111111",
            },
        )
        res_s2s = evaluate_acp_razorpay_upi_s2s_and_feed_extensions_guard(bad_s2s)
        self.assertFalse(res_s2s.allowed)
        self.assertEqual(res_s2s.decision_code, "ACP_S2S_CARD_RAW_PAN_OR_TOKEN_SCOPE_VIOLATION")

        # Undeclared feed extension or SSRF external schema auto-fetch (#223) -> blocked
        bad_feed = dict(
            base_ctx,
            feed_extensions_context={
                **base_ctx["feed_extensions_context"],
                "record_extension_names": ["sustainability", "undeclared_shadow_ext"],
            },
        )
        res_feed = evaluate_acp_razorpay_upi_s2s_and_feed_extensions_guard(bad_feed)
        self.assertFalse(res_feed.allowed)
        self.assertEqual(
            res_feed.decision_code,
            "ACP_FEED_UNDECLARED_EXTENSION_OR_SSRF_SCHEMA_FETCH_BLOCKED",
        )


if __name__ == "__main__":
    unittest.main()
