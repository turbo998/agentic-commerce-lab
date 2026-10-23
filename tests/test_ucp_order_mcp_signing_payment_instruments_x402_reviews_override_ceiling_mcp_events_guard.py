"""Unit tests for Stage 178 UCP #988/#584/#791, x402 #3656/#3881/#3877/#2728/#3883/#3508 & MCP SEP-3415 guard."""

from __future__ import annotations

import unittest

from lab.ucp_order_mcp_signing_payment_instruments_x402_reviews_override_ceiling_mcp_events_guard import (
    SECP256K1_HALF_N,
    validate_mcp_sep3415_events_transport_and_dedup,
    validate_ucp_order_mcp_signing_and_payment_instruments,
    validate_x402_reviews_extension,
    validate_x402_settlement_override_and_low_s_and_mcp,
)


class TestStage178Guard(unittest.TestCase):
    def test_ucp_order_mcp_signing_and_payment_instruments(self) -> None:
        res_ok = validate_ucp_order_mcp_signing_and_payment_instruments(
            mcp_tool="get_order",
            request_signature_valid=True,
            response_signature_present=True,
            require_signed_response=True,
            order_payment_instruments=[
                {
                    "id": "pi_card_1",
                    "type": "card",
                    "amount": 4500,
                    "display": {"brand": "visa", "last4": "4242"},
                }
            ],
            handler_type="processor-tokenizer",
            handler_config={"business_id": "biz_acme_01"},
        )
        self.assertTrue(res_ok.allowed)
        self.assertEqual(res_ok.decision_code, "ucp_order_mcp_and_payment_instruments_ok")

        # Leaked collection-time credential field on order_payment_instrument
        res_leak = validate_ucp_order_mcp_signing_and_payment_instruments(
            mcp_tool="get_order",
            request_signature_valid=True,
            response_signature_present=True,
            require_signed_response=True,
            order_payment_instruments=[
                {
                    "id": "pi_card_1",
                    "type": "card",
                    "credential": {"token": "tok_secret"},
                }
            ],
            handler_type="processor-tokenizer",
            handler_config={"business_id": "biz_acme_01"},
        )
        self.assertFalse(res_leak.allowed)
        self.assertEqual(res_leak.decision_code, "ucp_order_payment_collection_field_leaked")

        # Tokenizer accepting identity.access_token as authentication (PR #791)
        res_tok = validate_ucp_order_mcp_signing_and_payment_instruments(
            mcp_tool="get_order",
            request_signature_valid=True,
            response_signature_present=True,
            require_signed_response=True,
            order_payment_instruments=[{"id": "pi_1", "type": "card"}],
            tokenizer_auth_uses_identity_access_token=True,
            handler_type="processor-tokenizer",
            handler_config={"business_id": "biz_acme_01"},
        )
        self.assertFalse(res_tok.allowed)
        self.assertEqual(
            res_tok.decision_code,
            "ucp_tokenizer_identity_access_token_auth_forbidden",
        )

    def test_x402_reviews_extension(self) -> None:
        res_ok = validate_x402_reviews_extension(
            phase="402",
            providers=[
                {"provider": "agorean.com", "read": "https://agorean.com/v1/reviews?resource=res_1"}
            ],
        )
        self.assertTrue(res_ok.allowed)
        self.assertEqual(res_ok.decision_code, "x402_reviews_extension_ok")

        res_rating = validate_x402_reviews_extension(
            phase="402",
            providers=[
                {
                    "provider": "agorean.com",
                    "read": "https://agorean.com/v1/reviews?resource=res_1",
                    "rating": 5.0,
                }
            ],
        )
        self.assertFalse(res_rating.allowed)
        self.assertEqual(res_rating.decision_code, "x402_reviews_self_claimed_rating_forbidden")

        res_self = validate_x402_reviews_extension(
            phase="post_payment",
            providers=[
                {"provider": "agorean.com", "write": "https://agorean.com/v1/reviews/write"}
            ],
            payer="0xAlice",
            pay_to="0xalice",
        )
        self.assertFalse(res_self.allowed)
        self.assertEqual(res_self.decision_code, "x402_reviews_self_dealing_payer_equals_payto")

    def test_x402_settlement_override_low_s_and_mcp_sep3415(self) -> None:
        # 500% override above authorized_amount_atomic -> invalid_settlement_override
        res_over = validate_x402_settlement_override_and_low_s_and_mcp(
            authorized_amount_atomic=1_000_000,
            override_value="500%",
        )
        self.assertFalse(res_over.allowed)
        self.assertEqual(res_over.decision_code, "invalid_settlement_override")

        # High-s plain 65-byte ECDSA signature -> invalid_exact_evm_non_canonical_signature
        res_high_s = validate_x402_settlement_override_and_low_s_and_mcp(
            authorized_amount_atomic=1_000_000,
            override_value="50%",
            signature_len_bytes=65,
            ecdsa_s_int=SECP256K1_HALF_N + 1,
        )
        self.assertFalse(res_high_s.allowed)
        self.assertEqual(
            res_high_s.decision_code,
            "invalid_exact_evm_non_canonical_signature",
        )

        # SEP-3415 same eventId across two distinct subscriptions reaches both
        res_events = validate_mcp_sep3415_events_transport_and_dedup(
            method="events/stream",
            mcp_name_header="commerce.order.updated",
            deliveries=[
                {"subscription_id": "sub_A", "event_id": "evt_100", "webhook_id": "msg_1"},
                {"subscription_id": "sub_B", "event_id": "evt_100", "webhook_id": "msg_2"},
            ],
        )
        self.assertTrue(res_events.allowed)
        self.assertEqual(res_events.metadata["accepted_count"], 2)

        # Duplicate eventId within same subscription is dropped
        res_dup = validate_mcp_sep3415_events_transport_and_dedup(
            method="events/stream",
            mcp_name_header="commerce.order.updated",
            deliveries=[
                {"subscription_id": "sub_A", "event_id": "evt_100", "webhook_id": "msg_1"},
                {"subscription_id": "sub_A", "event_id": "evt_100", "webhook_id": "msg_1"},
            ],
        )
        self.assertFalse(res_dup.allowed)
        self.assertEqual(
            res_dup.decision_code,
            "mcp_events_within_subscription_duplicate_dropped",
        )


if __name__ == "__main__":
    unittest.main()
