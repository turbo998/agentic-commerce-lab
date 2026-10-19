"""Unit tests for Stage 44 (`lab/ucp_correlation_idempotency_ap2_conformance_guard.py`)."""

from __future__ import annotations

import unittest

from lab.ucp_correlation_idempotency_ap2_conformance_guard import (
    compute_ap2_open_mandate_hash,
    evaluate_ap2_mandate_hash_constraints_and_receipt_guard,
    evaluate_ucp_idempotency_conditional_write_and_signals_guard,
    evaluate_ucp_identity_recognized_issuer_and_loyalty_guard,
    evaluate_ucp_platform_reference_and_permalink_version_guard,
)


class TestStage44UcpCorrelationIdempotencyAp2ConformanceGuard(unittest.TestCase):
    def test_ucp_platform_reference_and_permalink_version_guard(self) -> None:
        base_ctx = {
            "create_platform_reference": "pref_platform_corr_9981",
            "update_or_complete_platform_reference": "pref_attempted_overwrite_ignored",
            "business_effective_platform_reference": "pref_platform_corr_9981",
            "order_platform_reference": "pref_platform_corr_9981",
            "used_platform_reference_for_auth_or_idempotency": False,
            "cart_continue_url": "https://merchant.example.com/cart/c_123",
            "cart_continue_url_preserves_line_items": True,
            "permalink_query_params": [
                ("context/postal_code", "94105"),
                ("ucp/version", "2026-06-01"),
                ("continue_to", "/checkout"),
            ],
            "supported_versions": ("2026-04-08", "2026-08-25"),
        }
        ok = evaluate_ucp_platform_reference_and_permalink_version_guard(base_ctx)
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.decision_code, "UCP_PLATFORM_REFERENCE_AND_PERMALINK_VERSION_VERIFIED")
        self.assertEqual(ok.selected_permalink_version, "2026-08-25")  # fell forward to oldest later release
        self.assertEqual(ok.consumed_control_params, ("ucp/version", "continue_to"))

        # Mutated platform_reference on update/complete blocked
        mutated = evaluate_ucp_platform_reference_and_permalink_version_guard(
            {
                **base_ctx,
                "business_effective_platform_reference": "pref_attempted_overwrite_ignored",
            }
        )
        self.assertFalse(mutated.allowed)
        self.assertEqual(
            mutated.decision_code,
            "PLATFORM_REFERENCE_MUTATED_ON_UPDATE_OR_COMPLETE_BLOCKED",
        )

        # PII/email inside platform_reference blocked
        pii = evaluate_ucp_platform_reference_and_permalink_version_guard(
            {
                **base_ctx,
                "create_platform_reference": "buyer:alice@example.com",
                "business_effective_platform_reference": "buyer:alice@example.com",
                "order_platform_reference": "buyer:alice@example.com",
            }
        )
        self.assertFalse(pii.allowed)
        self.assertEqual(
            pii.decision_code,
            "PLATFORM_REFERENCE_PII_CREDENTIAL_OR_AUTH_MISUSE_BLOCKED",
        )

    def test_ucp_idempotency_conditional_write_and_signals_guard(self) -> None:
        base_ctx = {
            "request_signed": True,
            "header_idempotency_key": "idem_001",
            "meta_idempotency_key": "idem_001",
            "operation_name": "update_checkout",
            "operation_class": "payload_carrying",
            "target_resource_id": "chk_123",
            "payload_body": {"b": 2, "a": 1},
            "stored_idempotency_record": {
                "operation_name": "update_checkout",
                "target_resource_id": "chk_123",
                "payload_body": {"a": 1, "b": 2},  # different key order -> identical JCS hash
            },
            "conditional_write_required": True,
            "current_etag": '"v3"',
            "if_match_header": '"v3"',
        }
        ok = evaluate_ucp_idempotency_conditional_write_and_signals_guard(base_ctx)
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.decision_code, "UCP_IDEMPOTENCY_CONDITIONAL_WRITE_AND_SIGNALS_VERIFIED")

        # Target-only operation (cancel_checkout) reusing key on a different target resource -> 409 / -32000
        cross_target = evaluate_ucp_idempotency_conditional_write_and_signals_guard(
            {
                **base_ctx,
                "operation_name": "cancel_checkout",
                "operation_class": "target_only",
                "target_resource_id": "chk_999",
                "stored_idempotency_record": {
                    "operation_name": "cancel_checkout",
                    "target_resource_id": "chk_123",
                },
            }
        )
        self.assertFalse(cross_target.allowed)
        self.assertEqual(
            cross_target.decision_code,
            "IDEMPOTENCY_KEY_CROSS_OPERATION_OR_TARGET_REUSE_BLOCKED",
        )
        self.assertEqual(cross_target.http_status, 409)
        self.assertEqual(cross_target.mcp_error_code, -32000)

        # ETag mismatch on concurrent update -> 412 Precondition Failed
        stale_etag = evaluate_ucp_idempotency_conditional_write_and_signals_guard(
            {
                **base_ctx,
                "if_match_header": '"v2"',
            }
        )
        self.assertFalse(stale_etag.allowed)
        self.assertEqual(
            stale_etag.decision_code,
            "CHECKOUT_CONDITIONAL_WRITE_ETAG_PRECONDITION_FAILED",
        )
        self.assertEqual(stale_etag.http_status, 412)

    def test_ucp_identity_recognized_issuer_and_loyalty_guard(self) -> None:
        base_ctx = {
            "recognized_issuers": {"https://accounts.idp.example"},
            "business_providers": [
                {"key": "google", "auth_url": "https://accounts.idp.example/"},  # trailing-slash lookalike!
                {"key": "custom", "auth_url": "https://accounts.idp.example"},
            ],
            "platform_attempted_unrecognized_discovery_or_exchange": False,
            "subject_token_issuer": "https://accounts.idp.example",
            "subject_token_user_id": "usr_alice",
            "acting_user_id": "usr_alice",
            "loyalty": {
                "earning_forecast": {
                    "amount": 30,
                    "breakdown": [{"type": "base", "amount": 10}, {"type": "bonus", "amount": 20}],
                },
                "discount_expressed_in_major_units": False,
            },
        }
        ok = evaluate_ucp_identity_recognized_issuer_and_loyalty_guard(base_ctx)
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.selected_provider_issuer, "https://accounts.idp.example")
        self.assertFalse(ok.fallback_to_direct_oauth)

        # Hostile auth_url discovery / subject_token exfiltration blocked
        exfil = evaluate_ucp_identity_recognized_issuer_and_loyalty_guard(
            {
                **base_ctx,
                "platform_attempted_unrecognized_discovery_or_exchange": True,
            }
        )
        self.assertFalse(exfil.allowed)
        self.assertEqual(
            exfil.decision_code,
            "UNRECOGNIZED_OR_NORMALIZED_IDP_ISSUER_SUBJECT_TOKEN_EXFILTRATION_BLOCKED",
        )

    def test_ap2_mandate_hash_constraints_and_receipt_guard(self) -> None:
        claims_a = {"currency": "USD", "max_amount": 5000, "items": ["sku_1", "sku_2"]}
        claims_b = {"items": ["sku_1", "sku_2"], "max_amount": 5000, "currency": "USD"}
        self.assertEqual(compute_ap2_open_mandate_hash(claims_a), compute_ap2_open_mandate_hash(claims_b))

        base_ctx = {
            "unsigned_open_mandate_claims": claims_a,
            "expected_open_mandate_hash": compute_ap2_open_mandate_hash(claims_b),
            "checkout_jwt_payload_entropy_bits": 128,
            "allowed_payment_instruments": [{"id": "pi-1", "type": "card"}],
            "presented_payment_instrument": {"id": "pi-1", "type": "card"},
            "allowed_merchants": [{"id": "merch_01", "name": "Acme", "website": "https://acme.example"}],
            "presented_merchant": {"id": "merch_01", "name": "Acme", "website": "https://acme.example"},
            "payment_receipt": {
                "psp_independently_confirmed": True,
                "network_independently_confirmed": True,
                "rail_confirmation_verified": True,
            },
        }
        ok = evaluate_ap2_mandate_hash_constraints_and_receipt_guard(base_ctx)
        self.assertTrue(ok.allowed)
        self.assertTrue(ok.rail_confirmation_verified)
        self.assertEqual(ok.decision_code, "AP2_MANDATE_HASH_CONSTRAINTS_AND_RECEIPT_VERIFIED")

        # Same id ("pi-1") but different type ("bank" vs "card") rejected (#301)
        type_confusion = evaluate_ap2_mandate_hash_constraints_and_receipt_guard(
            {
                **base_ctx,
                "presented_payment_instrument": {"id": "pi-1", "type": "bank"},
            }
        )
        self.assertFalse(type_confusion.allowed)
        self.assertEqual(
            type_confusion.decision_code,
            "AP2_INSTRUMENT_TYPE_CONFUSION_ON_ID_ONLY_MATCH_BLOCKED",
        )

        # Empty merchant.id with spoofed name+website rejected (#324, CWE-639)
        spoof_merchant = evaluate_ap2_mandate_hash_constraints_and_receipt_guard(
            {
                **base_ctx,
                "presented_merchant": {"id": "", "name": "Acme", "website": "https://acme.example"},
            }
        )
        self.assertFalse(spoof_merchant.allowed)
        self.assertEqual(
            spoof_merchant.decision_code,
            "AP2_EMPTY_MERCHANT_ID_DISPLAY_NAME_SPOOF_BLOCKED",
        )


if __name__ == "__main__":
    unittest.main()
