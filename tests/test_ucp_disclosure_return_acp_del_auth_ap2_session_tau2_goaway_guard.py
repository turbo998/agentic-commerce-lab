"""Unit tests for Stage 98 guardrails."""

from __future__ import annotations

import unittest

from lab.ucp_disclosure_return_acp_del_auth_ap2_session_tau2_goaway_guard import (
    validate_acp_delegated_auth_supported_versions_and_display_name_guard,
    validate_ap2_hnp_session_spending_rules_and_micropayment_channel_guard,
    validate_tau2_goaway_reconnect_banking_disputes_and_user_tool_calls_guard,
    validate_ucp_disclosure_return_signals_and_get_product_guard,
)


class TestStage98Guardrails(unittest.TestCase):
    def test_ucp_disclosure_return_signals_and_get_product_valid(self) -> None:
        res = validate_ucp_disclosure_return_signals_and_get_product_guard(
            {
                "messages": [
                    {
                        "type": "warning",
                        "code": "allergens",
                        "path": "$.products[0]",
                        "content": "**Contains: tree nuts.**",
                        "presentation": "disclosure",
                        "image_url": "https://merchant.com/allergen.svg",
                        "url": "https://merchant.com/allergen-info",
                    }
                ],
                "platform_supports_disclosure_rendering": True,
                "platform_dismissed_or_hidden_disclosure": False,
                "return_policies": {
                    "rp_std": {
                        "return_period_in_days": 30,
                        "supported_resolutions": ["original_payment_method"],
                        "methods": [
                            {
                                "type": "by_mail",
                                "fee": {"type": "fixed_fee", "amount": 500},
                            }
                        ],
                    },
                    "rp_final": {
                        "supported_resolutions": [],
                        "reason": "Final sale",
                    },
                },
                "line_items": [
                    {"id": "li_1", "return_policy_id": "rp_std"},
                    {"id": "li_2", "return_policy_id": "rp_final"},
                ],
                "agent_claimed_returnable_item_ids": ["li_1"],
                "signals": {"buyer_ip": "203.0.113.42"},
                "signals_source": "platform_observed",
                "a2a_data_attributes": ["a2a.ucp.checkout.payment", "a2a.ucp.checkout.signals"],
                "get_product_response": {
                    "product": {
                        "id": "prod_abc",
                        "selected": [{"name": "Color", "label": "Blue"}],
                        "variants": [
                            {
                                "id": "var_blue_10",
                                "options": [
                                    {"name": "Color", "label": "Blue"},
                                    {"name": "Size", "label": "10"},
                                ],
                            }
                        ],
                    }
                },
            }
        )
        self.assertTrue(res["allowed"], res["violations"])

    def test_ucp_disclosure_return_signals_and_get_product_violations(self) -> None:
        res = validate_ucp_disclosure_return_signals_and_get_product_guard(
            {
                "messages": [
                    {
                        "type": "warning",
                        "code": "allergens",
                        "presentation": "disclosure",
                    },
                    {
                        "type": "info",
                        "code": "promo",
                        "image_url": "https://merchant.com/promo.svg",
                    },
                ],
                "platform_supports_disclosure_rendering": False,
                "platform_dismissed_or_hidden_disclosure": True,
                "escalated_via_continue_url": False,
                "return_policies": {
                    "rp_bad": {
                        "supported_resolutions": [],
                        "methods": [{"type": "by_mail", "fee": {"type": "fixed_fee"}}],
                    }
                },
                "line_items": [
                    {"id": "li_final", "return_policy_id": "rp_bad"},
                    {"id": "li_missing", "return_policy_id": "rp_404"},
                ],
                "agent_claimed_returnable_item_ids": ["li_final"],
                "signals": {"buyer_ip": "1.2.3.4"},
                "signals_source": "buyer_asserted",
                "a2a_data_attributes": ["a2a.ucp.checkout.risk_signals"],
                "get_product_response": {
                    "product": {
                        "id": "prod_abc",
                        "selected": [{"name": "Color", "label": "Blue"}],
                        "variants": [
                            {
                                "id": "var_red_10",
                                "selected_options": [{"name": "Color", "label": "Red"}],
                                "options": [{"name": "Color", "label": "Red"}],
                            }
                        ],
                    }
                },
            }
        )
        self.assertFalse(res["allowed"])
        self.assertIn("ucp_disclosure_warning_dismissed_or_hidden", res["violations"])
        self.assertIn(
            "ucp_unrenderable_disclosure_missing_continue_url_escalation",
            res["violations"],
        )
        self.assertIn(
            "ucp_non_warning_message_has_image_or_url_field:1", res["violations"]
        )
        self.assertIn(
            "ucp_return_fixed_fee_missing_or_invalid_minor_amount:rp_bad:0",
            res["violations"],
        )
        self.assertIn("ucp_final_sale_item_claimed_returnable:li_final", res["violations"])
        self.assertIn("ucp_line_item_unknown_return_policy_id:rp_404", res["violations"])
        self.assertIn("ucp_signals_not_platform_observed:buyer_asserted", res["violations"])
        self.assertIn("ucp_deprecated_a2a_risk_signals_attribute_used", res["violations"])
        self.assertIn(
            "ucp_variant_uses_legacy_selected_options_field:0", res["violations"]
        )
        self.assertIn(
            "ucp_get_product_variant_mismatch_selected_anchor:0:Color",
            res["violations"],
        )

    def test_acp_delegated_auth_supported_versions_and_display_name_valid(self) -> None:
        res = validate_acp_delegated_auth_supported_versions_and_display_name_guard(
            {
                "delegated_authentication": {
                    "authentication_session_id": "auth_sess_01",
                    "create_action_type": "fingerprint",
                    "fingerprint_executed": True,
                    "authenticate_called": True,
                    "authenticate_action_type": "challenge",
                    "challenge_completed": True,
                    "retrieve_called": True,
                    "channel_data_in_create": True,
                },
                "error": {
                    "type": "invalid_request",
                    "code": "unsupported_api_version",
                    "supported_versions": ["2026-01-30", "2025-09-29"],
                },
                "agent_retry_api_version": "2026-01-30",
                "payment_handlers": [
                    {
                        "name": "dev.acp.tokenized.card",
                        "display_name": "Credit or Debit Card",
                    }
                ],
                "payment_data": {"token": "spt_123"},
            }
        )
        self.assertTrue(res["allowed"], res["violations"])

    def test_acp_delegated_auth_supported_versions_and_display_name_violations(
        self,
    ) -> None:
        res = validate_acp_delegated_auth_supported_versions_and_display_name_guard(
            {
                "delegated_authentication": {
                    "authentication_session_id": "",
                    "create_action_type": "fingerprint",
                    "fingerprint_executed": False,
                    "authenticate_called": True,
                    "authenticate_action_type": "challenge",
                    "challenge_completed": False,
                    "retrieve_called": True,
                    "channel_data_in_create": False,
                    "channel_data_in_authenticate": False,
                    "idempotency_key_reused_with_different_params": True,
                    "status_code": 200,
                },
                "error": {
                    "type": "invalid_request",
                    "code": "unsupported_api_version",
                    "supported_versions": ["2026-01-30"],
                },
                "agent_retry_api_version": "2024-01-01",
                "payment_handlers": [
                    {
                        "name": "dev.acp.tokenized.card",
                        "display_name": "dev.acp.tokenized.card",
                    }
                ],
                "payment_data": {"token": "spt_123", "capture_method": "manual"},
            }
        )
        self.assertFalse(res["allowed"])
        self.assertIn("acp_delegated_auth_missing_session_id", res["violations"])
        self.assertIn(
            "acp_delegated_auth_authenticate_before_fingerprint", res["violations"]
        )
        self.assertIn("acp_delegated_auth_retrieve_before_challenge", res["violations"])
        self.assertIn("acp_delegated_auth_missing_channel_data", res["violations"])
        self.assertIn(
            "acp_delegated_auth_idempotency_mismatch_not_409", res["violations"]
        )
        self.assertIn(
            "acp_agent_retry_version_not_in_supported_versions:2024-01-01",
            res["violations"],
        )
        self.assertIn("acp_payment_handler_invalid_display_name:0", res["violations"])
        self.assertIn(
            "acp_payment_data_undeclared_capture_method_forbidden", res["violations"]
        )

    def test_ap2_hnp_session_spending_rules_and_micropayment_channel_valid(
        self,
    ) -> None:
        res = validate_ap2_hnp_session_spending_rules_and_micropayment_channel_guard(
            {
                "current_timestamp": 1776643200,
                "hnp_intent_mandate": {
                    "user_cart_confirmation_required": False,
                    "delegation_depth": 1,
                    "session_authorization": {
                        "session_id": "sess_01",
                        "agent_did": "did:web:shopping-agent.example.com",
                        "status": "ACTIVE",
                        "session_expiry_ts": 1776650000,
                        "is_revoked": False,
                    },
                    "spending_rules": {
                        "max_per_transaction_minor": 10000,
                        "max_total_budget_minor": 50000,
                        "allowed_merchants": ["merch_01"],
                        "allowed_categories": ["electronics"],
                        "max_delegation_depth": 1,
                    },
                },
                "transaction_context": {
                    "amount_minor": 8000,
                    "cumulative_spent_minor": 20000,
                    "merchant_id": "merch_01",
                    "category": "electronics",
                },
                "micropayment_channel": {
                    "deposit_atomic": 1000000,
                    "min_deposit_atomic": 500000,
                    "voucher_nonce": 5,
                    "last_voucher_nonce": 4,
                    "cumulative_voucher_atomic": 250000,
                    "tokens_consumed": 250,
                    "rate_per_token_atomic": 1000,
                },
            }
        )
        self.assertTrue(res["allowed"], res["violations"])

    def test_ap2_hnp_session_spending_rules_and_micropayment_channel_violations(
        self,
    ) -> None:
        res = validate_ap2_hnp_session_spending_rules_and_micropayment_channel_guard(
            {
                "current_timestamp": 1776643200,
                "hnp_intent_mandate": {
                    "user_cart_confirmation_required": False,
                    "delegation_depth": 3,
                    "session_authorization": {
                        "session_id": "sess_01",
                        "agent_did": "invalid_did",
                        "status": "ACTIVE",
                        "session_expiry_ts": 1776640000,
                        "is_revoked": True,
                    },
                    "spending_rules": {
                        "max_per_transaction_minor": 5000,
                        "max_total_budget_minor": 20000,
                        "allowed_merchants": ["merch_01"],
                        "allowed_categories": ["electronics"],
                        "max_delegation_depth": 1,
                    },
                },
                "transaction_context": {
                    "amount_minor": 8000,
                    "cumulative_spent_minor": 15000,
                    "merchant_id": "merch_rogue",
                    "category": "gambling",
                },
                "micropayment_channel": {
                    "deposit_atomic": 100000,
                    "min_deposit_atomic": 500000,
                    "voucher_nonce": 4,
                    "last_voucher_nonce": 4,
                    "cumulative_voucher_atomic": 300000,
                    "tokens_consumed": 200,
                    "rate_per_token_atomic": 1000,
                },
            }
        )
        self.assertFalse(res["allowed"])
        self.assertIn("ap2_hnp_invalid_agent_did", res["violations"])
        self.assertIn("ap2_hnp_session_expired_or_revoked", res["violations"])
        self.assertIn("ap2_spending_rule_per_tx_limit_exceeded", res["violations"])
        self.assertIn("ap2_spending_rule_total_budget_exceeded", res["violations"])
        self.assertIn("ap2_spending_rule_merchant_not_allowed", res["violations"])
        self.assertIn("ap2_spending_rule_category_not_allowed", res["violations"])
        self.assertIn("ap2_spending_rule_delegation_depth_exceeded", res["violations"])
        self.assertIn("ap2_micropayment_deposit_below_minimum", res["violations"])
        self.assertIn("ap2_micropayment_voucher_nonce_not_monotonic", res["violations"])
        self.assertIn(
            "ap2_micropayment_voucher_exceeds_channel_deposit", res["violations"]
        )
        self.assertIn(
            "ap2_micropayment_token_rate_accounting_mismatch", res["violations"]
        )

    def test_tau2_goaway_reconnect_banking_disputes_and_user_tool_calls_valid(
        self,
    ) -> None:
        res = validate_tau2_goaway_reconnect_banking_disputes_and_user_tool_calls_guard(
            {
                "gemini_live_goaway": {
                    "go_away_received": True,
                    "reconnect_deadline_elapsed": True,
                    "needs_reconnection": True,
                    "reconnection_performed": True,
                },
                "disputed_debit_cards": [
                    {
                        "card_id": "dc_blue_01",
                        "dispute_reason": "card_present_fraud",
                        "card_action": "close_and_reissue",
                    },
                    {
                        "card_id": "dc_green_02",
                        "dispute_reason": "card_not_present_fraud",
                        "card_action": "close_and_reissue",
                    },
                ],
                "closed_debit_card_ids": ["dc_blue_01", "dc_green_02"],
                "replaced_debit_card_ids": ["dc_blue_01", "dc_green_02"],
                "light_blue_atm_fee_audit": {
                    "free_tier_overcharged_cents": 1700,
                    "uncharged_fee_cents": 250,
                    "credited_cents": 1450,
                },
                "duplicate_transactions": [
                    {"id": "tx_101", "posting_sequence": 1},
                    {"id": "tx_102", "posting_sequence": 2},
                ],
                "disputed_transaction_id": "tx_101",
                "user_message_litellm_conversion": {
                    "input_user_tool_calls": [{"id": "call_1", "name": "check_email"}],
                    "output_litellm_tool_calls": [
                        {"id": "call_1", "name": "check_email"}
                    ],
                },
            }
        )
        self.assertTrue(res["allowed"], res["violations"])

    def test_tau2_goaway_reconnect_banking_disputes_and_user_tool_calls_violations(
        self,
    ) -> None:
        res = validate_tau2_goaway_reconnect_banking_disputes_and_user_tool_calls_guard(
            {
                "gemini_live_goaway": {
                    "go_away_received": True,
                    "reconnect_deadline_elapsed": True,
                    "needs_reconnection": False,
                    "reconnection_performed": False,
                },
                "disputed_debit_cards": [
                    {
                        "card_id": "dc_blue_01",
                        "dispute_reason": "card_present_fraud",
                        "card_action": "close_and_reissue",
                    },
                    {
                        "card_id": "dc_green_02",
                        "dispute_reason": "card_not_present_fraud",
                        "card_action": "close_and_reissue",
                    },
                ],
                "closed_debit_card_ids": ["dc_blue_01"],
                "replaced_debit_card_ids": ["dc_blue_01"],
                "light_blue_atm_fee_audit": {
                    "free_tier_overcharged_cents": 1700,
                    "uncharged_fee_cents": 250,
                    "credited_cents": 800,
                },
                "duplicate_transactions": [
                    {"id": "tx_101", "posting_sequence": 1},
                    {"id": "tx_102", "posting_sequence": 2},
                ],
                "disputed_transaction_id": "tx_102",
                "user_message_litellm_conversion": {
                    "input_user_tool_calls": [{"id": "call_1", "name": "check_email"}],
                    "output_litellm_tool_calls": [],
                },
            }
        )
        self.assertFalse(res["allowed"])
        self.assertIn(
            "tau2_gemini_silent_goaway_deadline_missed_reconnection",
            res["violations"],
        )
        self.assertIn(
            "tau2_fraud_disputed_debit_card_not_closed_and_reissued:dc_green_02",
            res["violations"],
        )
        self.assertIn(
            "tau2_light_blue_atm_fee_net_credit_mismatch:800!=1450",
            res["violations"],
        )
        self.assertIn(
            "tau2_duplicate_dispute_not_earliest_posting_sequence:tx_102",
            res["violations"],
        )
        self.assertIn("tau2_litellm_user_tool_calls_dropped", res["violations"])


if __name__ == "__main__":
    unittest.main()
