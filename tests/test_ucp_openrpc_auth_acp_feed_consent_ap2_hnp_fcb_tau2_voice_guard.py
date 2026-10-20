"""Unit tests for Stage 68 protocol, payment, mandate, and evaluation guards."""

from __future__ import annotations

import unittest

from lab.ucp_openrpc_auth_acp_feed_consent_ap2_hnp_fcb_tau2_voice_guard import (
    verify_acp_feed_upsert_suggested_price_consent_and_razorpay_cart,
    verify_ap2_hnp_mandate_binding_string_amount_budget_and_fcb,
    verify_tau2_spoken_amount_reward_breakdown_replay_and_action_match,
    verify_ucp_openrpc_auth_discount_preview_spt_price_treatment_and_event_feed,
)


class Stage68GuardTests(unittest.TestCase):
    def test_ucp_valid_openrpc_auth_discount_spt_price_treatment_and_event_feed(self) -> None:
        res = verify_ucp_openrpc_auth_discount_preview_spt_price_treatment_and_event_feed(
            {
                "openrpc_methods": [
                    {
                        "name": "ec.auth",
                        "params": [{"name": "type", "required": True, "schema": {"$ref": "#/components/schemas/type"}}],
                    },
                    {
                        "name": "ep.cart.auth",
                        "params": [{"name": "type", "required": True, "schema": {"$ref": "#/components/schemas/type"}}],
                    },
                ],
                "embedded_auth_request": {"method": "ec.auth", "params": {"type": "oauth2_code"}},
                "catalog_operation": {
                    "op": "get_product",
                    "discounts": {"available": [{"id": "promo_10", "title": "10% Off"}]},
                },
                "spt_payment_handler": {
                    "name": "dev.ucp.payment.shared_payment_token",
                    "credential": {
                        "token": "spt_live_987654321",
                        "expires_at": "2026-10-20T16:30:00Z",
                        "merchant_id": "merch_acme_01",
                    },
                },
                "price": {
                    "amount": 11900,
                    "currency": "EUR",
                    "price_treatment": {"tax": {"inclusion": "included"}},
                    "downstream_tax_added_minor": 0,
                },
                "event_feed": {
                    "url": "https://merchant.example.com/ucp/events",
                    "event_types": ["order.updated", "inventory.low_stock"],
                    "transport": "webhook",
                },
                "fulfillment_event": {
                    "type": "shipment.delayed",
                    "description": "Weather delay at hub",
                    "agent_hints": [{"action": "notify_buyer", "reason": "Carrier delayed 24h"}],
                },
                "actions": {
                    "dev.ucp.shopping.buyer_consent": [{"id": "act_1"}],
                },
                "policies": [
                    {
                        "id": "pol_electronics_return",
                        "applies_to": ["$.products[?@.tags[?@=='electronics']]"],
                    }
                ],
            }
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.reason_code, "ucp_openrpc_discount_spt_price_event_policy_ok")
        self.assertEqual(res.details["normalized_tax_inclusion"], "included")

    def test_ucp_rejects_missing_openrpc_auth_required_and_catalog_applied_discount(self) -> None:
        r1 = verify_ucp_openrpc_auth_discount_preview_spt_price_treatment_and_event_feed(
            {
                "openrpc_methods": [
                    {"name": "ep.cart.auth", "params": [{"name": "type", "schema": {"$ref": "#/components/schemas/type"}}]}
                ]
            }
        )
        self.assertFalse(r1.allowed)
        self.assertEqual(r1.reason_code, "ucp_embedded_auth_type_param_not_required")

        r2 = verify_ucp_openrpc_auth_discount_preview_spt_price_treatment_and_event_feed(
            {
                "catalog_operation": {
                    "op": "get_product",
                    "discounts": {"applied": [{"code": "SAVE10"}]},
                }
            }
        )
        self.assertFalse(r2.allowed)
        self.assertEqual(r2.reason_code, "ucp_catalog_discount_applied_forbidden_on_product")

    def test_ucp_rejects_spt_raw_pan_double_tax_empty_actions_and_empty_policy_applies_to(self) -> None:
        r_spt = verify_ucp_openrpc_auth_discount_preview_spt_price_treatment_and_event_feed(
            {
                "spt_payment_handler": {
                    "name": "dev.ucp.payment.shared_payment_token",
                    "credential": {"token": "spt_1", "pan": "4111111111111111", "cvc": "123"},
                }
            }
        )
        self.assertFalse(r_spt.allowed)
        self.assertEqual(r_spt.reason_code, "ucp_spt_handler_raw_pan_or_cvc_leaked")

        r_tax = verify_ucp_openrpc_auth_discount_preview_spt_price_treatment_and_event_feed(
            {
                "price": {
                    "amount": 11900,
                    "currency": "EUR",
                    "price_treatment": {"tax": {"inclusion": "included"}},
                    "downstream_tax_added_minor": 2261,
                }
            }
        )
        self.assertFalse(r_tax.allowed)
        self.assertEqual(r_tax.reason_code, "ucp_price_treatment_included_double_taxed")

        r_act = verify_ucp_openrpc_auth_discount_preview_spt_price_treatment_and_event_feed({"actions": {}})
        self.assertFalse(r_act.allowed)
        self.assertEqual(r_act.reason_code, "ucp_empty_actions_map_present")

        r_pol = verify_ucp_openrpc_auth_discount_preview_spt_price_treatment_and_event_feed(
            {"policies": [{"id": "p1", "applies_to": []}]}
        )
        self.assertFalse(r_pol.allowed)
        self.assertEqual(r_pol.reason_code, "ucp_policy_empty_applies_to_array")

    def test_acp_valid_feed_upsert_suggested_price_consent_razorpay_and_cart(self) -> None:
        res = verify_acp_feed_upsert_suggested_price_consent_and_razorpay_cart(
            {
                "upsert_products_response": {"id": "feed_8f3K2x", "accepted": True},
                "feed_promotions": [
                    {
                        "id": "promo_spring_sale",
                        "title": "Spring Sale",
                        "status": "active",
                        "effective_period": {
                            "start_time": "2026-03-01T00:00:00Z",
                            "end_time": "2026-03-31T23:59:59Z",
                        },
                        "benefits": [{"type": "percent_off", "percent_off": 20}],
                        "applies_to": [{"product_id": "prod_classic_tee"}],
                    }
                ],
                "suggested_price": {
                    "amount": 7999,
                    "source": {"feed_id": "feed_8f3K2x", "channel": "feed_api"},
                    "observed_at": "2026-05-20T14:35:00Z",
                },
                "checkout_complete_request": {
                    "fulfillment_details": {"name": "John Smith", "email": "john@example.com"},
                    "applied_before_payment": True,
                },
                "marketing_consent_options": [
                    {
                        "channel": "email",
                        "display_text": "Promotional emails",
                        "privacy_policy_url": "https://www.testshop.com/privacy",
                    }
                ],
                "marketing_consents": [{"channel": "email", "opted_in": True}],
                "payment_handler": {
                    "id": "razorpay_upi",
                    "name": "in.razorpay.upi",
                    "psp": "razorpay",
                    "requires_delegate_payment": True,
                    "requires_pci_compliance": False,
                },
                "cart_session": {"id": "cart_01", "payment_handlers_negotiated": False},
            }
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.reason_code, "acp_feed_suggested_price_consent_razorpay_cart_ok")

    def test_acp_rejects_invalid_upsert_missing_feed_id_late_fulfillment_and_undeclared_consent(self) -> None:
        r1 = verify_acp_feed_upsert_suggested_price_consent_and_razorpay_cart(
            {"upsert_products_response": {"id": "feed_8f3K2x", "accepted": True, "extra": 1}}
        )
        self.assertFalse(r1.allowed)
        self.assertEqual(r1.reason_code, "acp_feed_upsert_response_schema_violation")

        r2 = verify_acp_feed_upsert_suggested_price_consent_and_razorpay_cart(
            {"suggested_price": {"amount": 7999, "source": {}, "observed_at": "2026-05-20T14:35:00Z"}}
        )
        self.assertFalse(r2.allowed)
        self.assertEqual(r2.reason_code, "acp_suggested_price_missing_feed_id_provenance")

        r3 = verify_acp_feed_upsert_suggested_price_consent_and_razorpay_cart(
            {
                "checkout_complete_request": {
                    "fulfillment_details": {"email": "new@example.com"},
                    "applied_before_payment": False,
                }
            }
        )
        self.assertFalse(r3.allowed)
        self.assertEqual(r3.reason_code, "acp_complete_fulfillment_details_applied_after_payment")

        r4 = verify_acp_feed_upsert_suggested_price_consent_and_razorpay_cart(
            {
                "marketing_consent_options": [
                    {
                        "channel": "email",
                        "display_text": "Promotional emails",
                        "privacy_policy_url": "https://www.testshop.com/privacy",
                    }
                ],
                "marketing_consents": [{"channel": "whatsapp", "opted_in": True}],
            }
        )
        self.assertFalse(r4.allowed)
        self.assertEqual(r4.reason_code, "acp_marketing_consent_undeclared_channel_or_missing_privacy_url")

    def test_ap2_valid_hnp_mandate_string_amount_budget_fcb_and_upi_collect(self) -> None:
        res = verify_ap2_hnp_mandate_binding_string_amount_budget_and_fcb(
            {
                "intent_mandate": {
                    "id": "intent_hnp_01",
                    "user_cart_confirmation_required": False,
                    "user_authorization": "eyJhbGciOiJFZERTQSJ9.eyJpbnRlbnQiOiJpbnRlbnRfaG5wXzAxIn0.c2ln",
                    "intent_mandate_hash": "sha256:abc123def456",
                    "budget": {"currency": "USD", "value": "250.00"},
                },
                "payment_mandate": {
                    "transaction_modality": "human_not_present",
                    "intent_mandate_id": "intent_hnp_01",
                    "signed_intent_mandate_hash": "sha256:abc123def456",
                    "total_amount": {"currency": "USD", "value": "199.95"},
                },
                "risk_payload": {
                    "fcb_state": "CLOSED",
                    "trip_conditions": [{"type": "VELOCITY_LIMIT", "status": "OK"}],
                },
                "upi_collect_request": {
                    "transaction_data": {"amount": "199.95", "vpa": "buyer@okaxis"},
                    "cred_block": {"mpin_encrypted": "enc_xyz"},
                    "device_fingerprint": {"device_id": "dev_99"},
                },
            }
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.reason_code, "ap2_hnp_string_amount_budget_fcb_upi_ok")

    def test_ap2_rejects_float_amount_budget_overrun_missing_hnp_auth_and_tripped_fcb(self) -> None:
        r_float = verify_ap2_hnp_mandate_binding_string_amount_budget_and_fcb(
            {"payment_mandate": {"total_amount": {"currency": "USD", "value": 199.95}}}
        )
        self.assertFalse(r_float.allowed)
        self.assertEqual(r_float.reason_code, "ap2_payment_currency_amount_value_not_string")

        r_budget = verify_ap2_hnp_mandate_binding_string_amount_budget_and_fcb(
            {
                "intent_mandate": {"budget": {"currency": "USD", "value": "100.00"}},
                "payment_mandate": {"total_amount": {"currency": "USD", "value": "125.00"}},
            }
        )
        self.assertFalse(r_budget.allowed)
        self.assertEqual(r_budget.reason_code, "ap2_intent_mandate_budget_exceeded")

        r_hnp = verify_ap2_hnp_mandate_binding_string_amount_budget_and_fcb(
            {
                "intent_mandate": {"id": "intent_hnp_01", "user_cart_confirmation_required": False},
                "payment_mandate": {
                    "transaction_modality": "human_not_present",
                    "intent_mandate_id": "intent_hnp_01",
                    "total_amount": {"currency": "USD", "value": "50.00"},
                },
            }
        )
        self.assertFalse(r_hnp.allowed)
        self.assertEqual(r_hnp.reason_code, "ap2_hnp_intent_missing_user_authorization")

        r_fcb = verify_ap2_hnp_mandate_binding_string_amount_budget_and_fcb(
            {
                "risk_payload": {
                    "fcb_state": "OPEN",
                    "trip_conditions": [{"type": "PRICE_DRIFT", "status": "TRIPPED"}],
                }
            }
        )
        self.assertFalse(r_fcb.allowed)
        self.assertEqual(r_fcb.reason_code, "ap2_fcb_circuit_open_or_condition_tripped")

    def test_tau2_valid_spoken_amount_reward_breakdown_replay_and_action_match(self) -> None:
        res = verify_tau2_spoken_amount_reward_breakdown_replay_and_action_match(
            {
                "voice_communication_check": {
                    "expected_amount": "5244",
                    "chunks": ["Refund is five thousand ", "two hundred forty four dollars."],
                    "reported_pass": True,
                },
                "reward_analysis": {
                    "reward_basis": ["DB", "COMMUNICATE"],
                    "reward_breakdown": {"DB": 1.0},
                    "used_direct_subscript": False,
                },
                "trajectory_replay": {
                    "replay_mismatches": 2,
                    "strict_replay": False,
                    "reward_info_metadata": {"replay_mismatches": 2},
                },
                "action_comparison": {
                    "gold_arguments": {
                        "order_id": "#W1",
                        "item_ids": ["1", "2"],
                        "new_item_ids": ["10", "20"],
                    },
                    "tool_call_arguments": {
                        "order_id": "#W1",
                        "item_ids": ["2", "1"],
                        "new_item_ids": ["20", "10"],
                    },
                    "reported_match": True,
                },
                "retail_reference_check": {
                    "order_status": "delivered",
                    "exchange_price_difference": "12.50",
                    "gift_card_balance": "17.00",
                },
            }
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.reason_code, "tau2_spoken_amount_reward_replay_action_retail_ok")

    def test_tau2_rejects_spoken_false_negative_keyerror_omitted_gold_args_and_retail_overdraft(self) -> None:
        r_voice = verify_tau2_spoken_amount_reward_breakdown_replay_and_action_match(
            {
                "voice_communication_check": {
                    "expected_amount": "5244",
                    "chunks": ["Refund is five thousand two hundred forty four dollars."],
                    "reported_pass": False,
                }
            }
        )
        self.assertFalse(r_voice.allowed)
        self.assertEqual(r_voice.reason_code, "tau2_voice_spoken_or_chunked_amount_false_negative")

        r_key = verify_tau2_spoken_amount_reward_breakdown_replay_and_action_match(
            {
                "reward_analysis": {
                    "reward_basis": ["DB", "COMMUNICATE"],
                    "reward_breakdown": {"DB": 0.0},
                    "used_direct_subscript": True,
                }
            }
        )
        self.assertFalse(r_key.allowed)
        self.assertEqual(r_key.reason_code, "tau2_analyze_reward_missing_component_keyerror")

        r_omit = verify_tau2_spoken_amount_reward_breakdown_replay_and_action_match(
            {
                "action_comparison": {
                    "gold_arguments": {"order_id": "#W1", "payment_method_id": "gc_1"},
                    "tool_call_arguments": {"order_id": "#W1"},
                    "reported_match": True,
                }
            }
        )
        self.assertFalse(r_omit.allowed)
        self.assertEqual(r_omit.reason_code, "tau2_action_check_omitted_gold_arguments_matched")

        r_retail = verify_tau2_spoken_amount_reward_breakdown_replay_and_action_match(
            {
                "retail_reference_check": {
                    "order_status": "delivered",
                    "exchange_price_difference": "21.10",
                    "gift_card_balance": "17.00",
                }
            }
        )
        self.assertFalse(r_retail.allowed)
        self.assertEqual(r_retail.reason_code, "tau2_retail_reference_insufficient_gift_card_or_pending_exchange")


if __name__ == "__main__":
    unittest.main()
