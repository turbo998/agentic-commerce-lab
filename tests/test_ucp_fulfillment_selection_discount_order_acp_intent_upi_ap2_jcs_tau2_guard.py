"""Unit tests for Stage 102 guardrails across UCP, ACP, Google AP2, and Sierra tau2-bench."""

from __future__ import annotations

import unittest

from lab.ucp_fulfillment_selection_discount_order_acp_intent_upi_ap2_jcs_tau2_guard import (
    compute_raw_cart_mandate_jcs_hash,
    validate_acp_intent_trace_cancellation_and_delegated_upi_guard,
    validate_ap2_jcs_cart_to_payment_binding_and_trustboost_pii_x402_guard,
    validate_tau2_dummy_user_checkpoint_atomic_hallucination_retry_and_empty_user_turn_guard,
    validate_ucp_fulfillment_selection_available_discounts_order_payment_and_gift_discount_guard,
)


class TestStage102Guards(unittest.TestCase):
    def test_ucp_fulfillment_selection_available_discounts_order_payment_compliant(self) -> None:
        payload = {
            "fulfillment_event_check": {
                "selected_checkout_method_ids": ["method_ship_1"],
                "selected_checkout_option_ids": ["opt_express"],
                "fulfillment_method_id": "method_ship_1",
                "fulfillment_option_id": "opt_express",
                "estimated_delivery": {
                    "earliest": "2026-10-22T09:00:00Z",
                    "latest": "2026-10-23T18:00:00Z",
                },
            },
            "discounts_context": {
                "request_contains_available_discounts": False,
                "available_discounts": [
                    {"id": "disc_summer", "title": "15% Off", "type": "automatic", "remaining_amount": 0},
                    {"id": "disc_vip", "title": "VIP Promo", "type": "code", "remaining_amount": 1200},
                ],
                "applied_discounts": [
                    {"id": "disc_bogo", "gift_line_item_id": "li_free_tote"},
                ],
                "line_items": [
                    {"id": "li_main", "is_promotional_gift": False, "price_minor": 5000},
                    {"id": "li_free_tote", "is_promotional_gift": True, "price_minor": 0},
                ],
                "discount_rejections": [
                    {
                        "failure_cause": "usage_limit_exhausted",
                        "rejection_code": "discount_code_usage_limit_reached",
                    },
                    {
                        "failure_cause": "stacking_conflict",
                        "rejection_code": "discount_code_stacking_conflict",
                    },
                ],
            },
            "order_payment": {
                "instruments": [
                    {
                        "id": "pi_ord_1",
                        "type": "card",
                        "amount": 5000,
                        "billing_address": {"country": "US"},
                        "display": {"brand": "Visa", "last4": "4242"},
                    }
                ]
            },
        }
        res = validate_ucp_fulfillment_selection_available_discounts_order_payment_and_gift_discount_guard(payload)
        self.assertTrue(res["allowed"], res["violations"])

    def test_ucp_fulfillment_selection_available_discounts_order_payment_violations(self) -> None:
        payload = {
            "fulfillment_event_check": {
                "selected_checkout_method_ids": ["method_ship_1"],
                "selected_checkout_option_ids": ["opt_express"],
                "fulfillment_method_id": "method_unknown",
                "fulfillment_option_id": "opt_standard",
                "estimated_delivery": {
                    "earliest": "2026-10-25T09:00:00Z",
                    "latest": "2026-10-23T18:00:00Z",
                },
            },
            "discounts_context": {
                "request_contains_available_discounts": True,
                "available_discounts": [
                    {"id": "disc_vip", "title": "VIP Promo", "type": "code", "code": "SECRET50", "remaining_amount": -5},
                ],
                "applied_discounts": [],
                "line_items": [
                    {"id": "li_free_tote", "is_promotional_gift": True, "price_minor": 0},
                ],
                "discount_rejections": [
                    {
                        "failure_cause": "usage_limit_exhausted",
                        "rejection_code": "discount_code_already_applied",
                    },
                ],
            },
            "order_payment": {
                "instruments": [
                    {
                        "id": "pi_ord_1",
                        "type": "card",
                        "amount": 5000,
                        "credential": "spt_secret_token_99",
                        "handler_id": "h_stripe",
                    }
                ]
            },
        }
        res = validate_ucp_fulfillment_selection_available_discounts_order_payment_and_gift_discount_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("UCP_617_UNLINKED_FULFILLMENT_METHOD_ID", res["violations"])
        self.assertIn("UCP_617_UNLINKED_FULFILLMENT_OPTION_ID", res["violations"])
        self.assertIn("UCP_617_INVALID_DELIVERY_ESTIMATE_WINDOW", res["violations"])
        self.assertIn("UCP_609_AVAILABLE_DISCOUNTS_IN_REQUEST_FORBIDDEN", res["violations"])
        self.assertIn("UCP_609_PROMO_CODE_EXPOSED_IN_AVAILABLE_DISCOUNT", res["violations"])
        self.assertIn("UCP_584_COLLECTION_TIME_PAYMENT_FIELD_LEAKED_TO_ORDER:credential", res["violations"])
        self.assertIn("UCP_578_UNEXPLAINED_ZERO_PRICE_GIFT_LINE_ITEM:li_free_tote", res["violations"])
        self.assertIn("UCP_577_MISLEADING_USAGE_LIMIT_CODE:discount_code_already_applied", res["violations"])

    def test_acp_intent_trace_cancellation_and_delegated_upi_compliant(self) -> None:
        payload = {
            "cancel_session": {
                "request_body": {
                    "intent_trace": {
                        "reason_code": "shipping_cost",
                        "threshold_minor": 500,
                    }
                },
                "response_status": "canceled",
            },
            "delegated_upi": {
                "delegate_id": "upi_del_9981",
                "cryptogram": "crypto_otc_77123",
                "provider": "razorpay",
                "cryptogram_reused": False,
                "amount_minor": 149900,
                "pre_authorized_limit_minor": 200000,
                "india_data_localization_compliant": True,
            },
        }
        res = validate_acp_intent_trace_cancellation_and_delegated_upi_guard(payload)
        self.assertTrue(res["allowed"], res["violations"])

    def test_acp_intent_trace_cancellation_and_delegated_upi_violations(self) -> None:
        payload = {
            "cancel_session": {
                "request_body": {
                    "intent_trace": {
                        "reason_code": "shipping_cost",
                        "email": "user@example.com",
                    },
                    "unexpected_field": True,
                },
                "response_status": "in_progress",
            },
            "delegated_upi": {
                "delegate_id": "upi_del_9981",
                "cryptogram": "crypto_otc_77123",
                "provider": "stripe",
                "cryptogram_reused": True,
                "amount_minor": 250000,
                "pre_authorized_limit_minor": 200000,
                "india_data_localization_compliant": False,
            },
        }
        res = validate_acp_intent_trace_cancellation_and_delegated_upi_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("ACP_54_CANCEL_REQUEST_UNKNOWN_TOP_LEVEL_FIELD", res["violations"])
        self.assertIn("ACP_54_INTENT_TRACE_PII_FORBIDDEN:email", res["violations"])
        self.assertIn("ACP_54_CANCEL_RESPONSE_MUST_BE_CANCELED", res["violations"])
        self.assertIn("ACP_46_UNSUPPORTED_UPI_TSP_PROVIDER:stripe", res["violations"])
        self.assertIn("ACP_46_UPI_ONE_TIME_CRYPTOGRAM_REPLAYED", res["violations"])
        self.assertIn("ACP_46_UPI_AMOUNT_EXCEEDS_PREAUTHORIZED_LIMIT", res["violations"])
        self.assertIn("ACP_46_INDIA_DATA_LOCALIZATION_VIOLATION", res["violations"])

    def test_ap2_jcs_cart_to_payment_binding_and_trustboost_pii_x402_compliant(self) -> None:
        raw_cart = {
            "id": "cm_901",
            "total_minor": 8800,
            "optional_note": None,
            "x_vendor_extension": {"tier": "gold"},
        }
        digest = compute_raw_cart_mandate_jcs_hash(raw_cart)
        payload = {
            "cart_to_payment_binding": {
                "raw_received_cart_mandate": raw_cart,
                "payment_mandate_contents": {
                    "cart_mandate_id": "cm_901",
                    "cart_mandate_hash": digest,
                },
                "allow_unbound_cart": False,
                "hashed_after_schema_strip": False,
            },
            "trustboost_sanitization": {
                "pii_sanitized_before_llm": True,
                "raw_pii_exposed_to_llm": False,
                "x402_solana_usdc_settled": True,
                "solana_anchor_tx": "5xSolanaAnchorTx998123",
                "verify_endpoint": "https://trustboost.example/verify/5xSolanaAnchorTx998123",
            },
        }
        res = validate_ap2_jcs_cart_to_payment_binding_and_trustboost_pii_x402_guard(payload)
        self.assertTrue(res["allowed"], res["violations"])

    def test_ap2_jcs_cart_to_payment_binding_and_trustboost_pii_x402_violations(self) -> None:
        raw_cart = {
            "id": "cm_901",
            "total_minor": 8800,
            "x_vendor_extension": {"tier": "tampered_platinum"},
        }
        # Hash computed after dropping x_vendor_extension
        stripped_hash = compute_raw_cart_mandate_jcs_hash({"id": "cm_901", "total_minor": 8800})
        payload = {
            "cart_to_payment_binding": {
                "raw_received_cart_mandate": raw_cart,
                "payment_mandate_contents": {
                    "cart_mandate_id": "cm_901",
                    "cart_mandate_hash": stripped_hash,
                },
                "allow_unbound_cart": True,
                "hashed_after_schema_strip": True,
            },
            "trustboost_sanitization": {
                "pii_sanitized_before_llm": False,
                "raw_pii_exposed_to_llm": True,
                "x402_solana_usdc_settled": False,
                "solana_anchor_tx": "",
                "verify_endpoint": "https://trustboost.example/verify/",
            },
        }
        res = validate_ap2_jcs_cart_to_payment_binding_and_trustboost_pii_x402_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("AP2_253_HASHED_SCHEMA_STRIPPED_MODEL_INSTEAD_OF_RAW_JSON", res["violations"])
        self.assertIn("AP2_253_CART_MANDATE_HASH_MISMATCH", res["violations"])
        self.assertIn("AP2_267_UNSANITIZED_PII_EXPOSED_TO_LLM", res["violations"])
        self.assertIn("AP2_267_UNSETTLED_X402_SOLANA_SANITIZE_CALL", res["violations"])
        self.assertIn("AP2_267_MISSING_OR_MISMATCHED_SOLANA_ANCHOR_PROOF", res["violations"])

    def test_tau2_dummy_user_checkpoint_atomic_hallucination_retry_and_empty_user_turn_compliant(self) -> None:
        payload = {
            "dummy_user_construction": {
                "is_solo_mode": True,
                "passed_simulator_args_to_dummy_user": False,
            },
            "checkpoint_replacement": {
                "unlinked_old_before_replacement_write": False,
                "replacement_write_failed": True,
                "old_trajectory_preserved": True,
            },
            "hallucination_retry_safety": {
                "reviewed_final_retry": True,
                "checkpointed_discarded_retry": False,
                "truncated_tool_results_in_judge_input": False,
            },
            "empty_user_turn_retry": {
                "initial_turn_empty_without_tool_calls": True,
                "retried_with_stop_reminder": True,
                "reminder_leaked_into_recorded_trajectory": False,
            },
        }
        res = validate_tau2_dummy_user_checkpoint_atomic_hallucination_retry_and_empty_user_turn_guard(payload)
        self.assertTrue(res["allowed"], res["violations"])

    def test_tau2_dummy_user_checkpoint_atomic_hallucination_retry_and_empty_user_turn_violations(self) -> None:
        payload = {
            "dummy_user_construction": {
                "is_solo_mode": True,
                "passed_simulator_args_to_dummy_user": True,
            },
            "checkpoint_replacement": {
                "unlinked_old_before_replacement_write": True,
                "replacement_write_failed": True,
                "old_trajectory_preserved": False,
            },
            "hallucination_retry_safety": {
                "reviewed_final_retry": False,
                "checkpointed_discarded_retry": True,
                "truncated_tool_results_in_judge_input": True,
            },
            "empty_user_turn_retry": {
                "initial_turn_empty_without_tool_calls": True,
                "retried_with_stop_reminder": False,
                "reminder_leaked_into_recorded_trajectory": True,
            },
        }
        res = validate_tau2_dummy_user_checkpoint_atomic_hallucination_retry_and_empty_user_turn_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("TAU2_534_SIMULATOR_ARGS_PASSED_TO_DUMMY_USER_TYPEERROR", res["violations"])
        self.assertIn("TAU2_533_PREMATURE_CHECKPOINT_UNLINK_DATA_LOSS", res["violations"])
        self.assertIn("TAU2_533_OLD_TRAJECTORY_LOST_ON_WRITE_FAILURE", res["violations"])
        self.assertIn("TAU2_520_FINAL_RETRY_NOT_REVIEWED", res["violations"])
        self.assertIn("TAU2_520_DISCARDED_RETRY_CHECKPOINTED", res["violations"])
        self.assertIn("TAU2_520_TRUNCATED_TOOL_RESULTS_IN_JUDGE_INPUT", res["violations"])
        self.assertIn("TAU2_471_EMPTY_USER_TURN_NOT_RETRIED", res["violations"])
        self.assertIn("TAU2_471_RETRY_REMINDER_LEAKED_INTO_TRAJECTORY", res["violations"])


if __name__ == "__main__":
    unittest.main()
