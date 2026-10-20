"""Unit tests for Stage 92 deterministic guardrails."""

from __future__ import annotations

import unittest

from lab.ucp_fee_ecap_acp_sale_crypto_ap2_receipt_tau2_airline_ctx_guard import (
    validate_acp_consolidated_discount_sale_omnibus_and_x402_crypto_guard,
    validate_ap2_payment_receipt_and_audit_log_guard,
    validate_tau2_airline_seat_release_and_context_window_guard,
    validate_ucp_fee_extension_ecap_and_totals_change_guard,
)


class TestStage92Guards(unittest.TestCase):
    def test_ucp_fee_ecap_and_totals_change_valid(self) -> None:
        payload = {
            "client_request_body": {"line_items": [{"id": "li_1", "quantity": 1}]},
            "fees_applied": [
                {
                    "fee_type": "environmental_recycling",
                    "amount": 350,
                    "allocations": [{"path": "$.line_items[0]", "amount": 350}],
                }
            ],
            "ecap_session": {
                "continue_url": "https://shop.example.com/cart/embedded?session_id=ecap_1",
                "requires_auth": True,
                "ep_cart_auth_postmessage_used": True,
                "declared_extensions": [],
            },
            "ec_totals_change": {
                "method": "ec.totals.change",
                "totals": [{"type": "total", "amount": 5350}],
            },
        }
        res = validate_ucp_fee_extension_ecap_and_totals_change_guard(payload)
        self.assertTrue(res["allowed"])
        self.assertEqual(res["violations"], [])

    def test_ucp_fee_waived_zero_or_ecap_query_token_blocked(self) -> None:
        payload = {
            "client_request_body": {"fees": [{"fee_type": "service", "amount": 100}]},
            "fees_applied": [{"fee_type": "bag_fee", "amount": 0}],
            "ecap_session": {
                "continue_url": "https://shop.example.com/cart?access_token=secret123",
                "requires_auth": True,
                "ep_cart_auth_postmessage_used": False,
                "declared_extensions": ["dev.ucp.shopping.fulfillment"],
            },
        }
        res = validate_ucp_fee_extension_ecap_and_totals_change_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("UCP_FEE_READONLY_CLIENT_FIELD_NOT_ALLOWED", res["violations"])
        self.assertIn("UCP_FEE_NON_POSITIVE_OR_WAIVED_AMOUNT_FORBIDDEN:index_0", res["violations"])
        self.assertIn("UCP_ECAP_CONTINUE_URL_AUTH_QUERY_LEAK:access_token", res["violations"])

    def test_acp_discount_sale_omnibus_and_x402_crypto_valid(self) -> None:
        payload = {
            "sales": [{"id": "sale_bfcm", "name": "Black Friday"}],
            "line_items": [
                {
                    "id": "li_1",
                    "unit_amount": 5000,
                    "discount_eligible": True,
                    "sale": {
                        "id": "sale_bfcm",
                        "compare_at_amount": 7500,
                        "eu_omnibus_applicable": True,
                        "lowest_recent_amount": 7000,
                        "lowest_recent_period_days": 30,
                    },
                },
                {
                    "id": "li_map",
                    "unit_amount": 10000,
                    "discount_eligible": False,
                },
            ],
            "applied_discounts": [
                {
                    "code": "SAVE10",
                    "type": "percentage",
                    "amount": 500,
                    "excluded_items": [{"item_id": "li_map", "reason": "discount_code_item_ineligible"}],
                    "allocations": [{"item_id": "li_1", "amount": 500}],
                }
            ],
            "crypto_delegate_payment": {
                "type": "crypto",
                "allowance_max_amount": 14500,
                "current_timestamp": 1760000000,
                "x402_payload": {
                    "amount": 14500,
                    "valid_before": 1760000600,
                    "nonce_reused": False,
                    "facilitator_signature_verified": True,
                },
            },
        }
        res = validate_acp_consolidated_discount_sale_omnibus_and_x402_crypto_guard(payload)
        self.assertTrue(res["allowed"])

    def test_acp_discount_automatic_or_omnibus_or_x402_mismatch_blocked(self) -> None:
        payload = {
            "sales": [{"id": "sale_bfcm", "name": "Black Friday"}],
            "line_items": [
                {
                    "id": "li_map",
                    "unit_amount": 10000,
                    "discount_eligible": False,
                    "sale": {
                        "id": "sale_bfcm",
                        "compare_at_amount": 9000,
                        "eu_omnibus_applicable": True,
                        "lowest_recent_amount": 9500,
                        "lowest_recent_period_days": 7,
                    },
                }
            ],
            "applied_discounts": [
                {
                    "code": "VIP20",
                    "automatic": True,
                    "type": "bogo",
                    "allocations": [{"item_id": "li_map", "amount": 2000}],
                }
            ],
            "crypto_delegate_payment": {
                "type": "crypto",
                "allowance_max_amount": 8000,
                "current_timestamp": 1760000000,
                "x402_payload": {
                    "amount": 9500,
                    "valid_before": 1759999000,
                    "nonce_reused": True,
                    "facilitator_signature_verified": False,
                },
            },
        }
        res = validate_acp_consolidated_discount_sale_omnibus_and_x402_crypto_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("ACP_APPLIED_DISCOUNT_REMOVED_AUTOMATIC_FIELD_FORBIDDEN", res["violations"])
        self.assertIn("ACP_APPLIED_DISCOUNT_INVALID_TYPE_ENUM:bogo", res["violations"])
        self.assertIn("ACP_DISCOUNT_CODE_APPLIED_TO_INELIGIBLE_ITEM:li_map", res["violations"])
        self.assertIn("ACP_SALE_EU_OMNIBUS_30DAY_LOWEST_PRICE_REQUIRED:li_map", res["violations"])

    def test_ap2_payment_receipt_and_audit_log_valid(self) -> None:
        payload = {
            "payment_receipt": {
                "payment_mandate_id": "pm_9201",
                "cart_mandate_id": "cm_9201",
                "transaction_id": "tx_9201",
                "timestamp": "2026-10-21T03:40:00Z",
                "rail_reference": "stripe_pi_9201",
                "payment_status": "SUCCESS",
                "amount": 14500,
                "payment_mandate_amount": 14500,
            },
            "audit_log": {
                "recorded_lifecycle_stages": ["created", "signed", "verified", "settled"],
                "contains_unmasked_pan_or_pii": False,
            },
        }
        res = validate_ap2_payment_receipt_and_audit_log_guard(payload)
        self.assertTrue(res["allowed"])

    def test_ap2_payment_receipt_mismatch_or_unmasked_pii_blocked(self) -> None:
        payload = {
            "payment_receipt": {
                "payment_mandate_id": "pm_9201",
                "cart_mandate_id": "",
                "transaction_id": "tx_9201",
                "timestamp": "2026-10-21T03:40:00Z",
                "rail_reference": "stripe_pi_9201",
                "payment_status": "SETTLED_CUSTOM",
                "amount": 16000,
                "payment_mandate_amount": 14500,
            },
            "audit_log": {
                "recorded_lifecycle_stages": ["created", "settled"],
                "contains_unmasked_pan_or_pii": True,
            },
        }
        res = validate_ap2_payment_receipt_and_audit_log_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("AP2_PAYMENT_RECEIPT_AMOUNT_MISMATCH:16000!=14500", res["violations"])
        self.assertIn("AP2_AUDIT_LOG_PCI_GDPR_UNMASKED_PII_LEAK", res["violations"])

    def test_tau2_airline_seat_release_and_context_window_valid(self) -> None:
        payload = {
            "airline_cancellation": {
                "passenger_count": 3,
                "flight_segments": [
                    {"flight_id": "HAT001", "seats_before_cancel": 40, "seats_after_cancel": 43},
                    {"flight_id": "HAT002", "seats_before_cancel": 12, "seats_after_cancel": 15},
                ],
            },
            "context_window_failure": {
                "error_type": "ContextWindowExceededError",
                "full_sim_retries_attempted": 0,
                "termination_reason": "CONTEXT_WINDOW_EXCEEDED",
                "included_in_evaluable_denominator": False,
            },
            "reasoning_model_call": {
                "is_reasoning_model": True,
                "rejected_zero_temperature": True,
                "dropped_temperature_on_retry": True,
            },
            "return_exchange_eval": {
                "token_usage": {
                    "agent_tokens": 2400,
                    "supervisor_tokens": 600,
                    "user_sim_tokens": 950,
                }
            },
        }
        res = validate_tau2_airline_seat_release_and_context_window_guard(payload)
        self.assertTrue(res["allowed"])

    def test_tau2_airline_seat_leak_or_context_window_retry_blocked(self) -> None:
        payload = {
            "airline_cancellation": {
                "passenger_count": 3,
                "flight_segments": [
                    {"flight_id": "HAT001", "seats_before_cancel": 40, "seats_after_cancel": 40}
                ],
            },
            "context_window_failure": {
                "error_type": "ContextWindowExceededError",
                "full_sim_retries_attempted": 3,
                "termination_reason": "INFRASTRUCTURE_ERROR",
                "included_in_evaluable_denominator": True,
            },
            "reasoning_model_call": {
                "is_reasoning_model": True,
                "rejected_zero_temperature": True,
                "dropped_temperature_on_retry": False,
            },
        }
        res = validate_tau2_airline_seat_release_and_context_window_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("TAU2_AIRLINE_CANCEL_SEAT_INVENTORY_NOT_RESTORED:HAT001", res["violations"])
        self.assertIn("TAU2_CONTEXT_WINDOW_REDUNDANT_SIM_RETRY_FORBIDDEN", res["violations"])
        self.assertIn("TAU2_REASONING_MODEL_TEMPERATURE_NOT_DROPPED", res["violations"])


if __name__ == "__main__":
    unittest.main()
