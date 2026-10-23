"""Unit tests for Stage 208 guardrails."""

from __future__ import annotations

import unittest

from lab.ucp_verticals_ancillaries_acp_gift_card_ap2_welfare_x402_hooks_cardano_mcp_tau2_guard import (
    audit_acp_merchant_gift_card_source_and_extended_iin,
    audit_acp_universal_product_types_and_multi_location_feed,
    audit_ap2_social_welfare_mandate_and_discovery_polling,
    audit_mcp_error_structured_content_and_uri_template_id,
    audit_mcp_tool_side_effect_class_and_manifest_trust_tier,
    audit_tau2_banking_unrequested_referral_and_openai_tool_call_schema,
    audit_tau2_retail_confirmation_stop_and_airline_extra_passenger,
    audit_ucp_checkout_ancillaries_and_openattribution_telemetry,
    audit_ucp_product_property_value_and_single_type_extends,
    audit_ucp_shipping_discount_double_count_and_get_order_signatures,
    audit_ucp_vertical_hierarchy_and_capability_registry_map,
    audit_x402_agreement_session_terms_and_go_svm_failed_tx,
    audit_x402_cardano_raw_cbor_preservation_and_spec_payload,
    audit_x402_erc8183_job_escrow_and_delivery_conformance,
    audit_x402_hook_correlation_abort_release_and_paywall_xss,
    audit_x402_solidarity_owner_share_and_payment_backed_reviews,
)


class Stage208GuardTests(unittest.TestCase):
    def test_ucp_acp_ap2_guards(self) -> None:
        # PR-01
        ok01 = audit_ucp_vertical_hierarchy_and_capability_registry_map(
            {
                "schema_paths": [
                    "source/schemas/shopping/checkout.json",
                    "source/schemas/payment/instrument.json",
                    "source/schemas/common/address.json",
                ],
                "ucp_capabilities": {
                    "dev.ucp.shopping.checkout": [{"version": "2026-01-23"}],
                },
            }
        )
        self.assertTrue(ok01.admitted)
        bad01 = audit_ucp_vertical_hierarchy_and_capability_registry_map(
            {
                "schema_paths": ["source/schemas/checkout.json"],
                "ucp_capabilities": [{"name": "dev.ucp.shopping.checkout"}],
            }
        )
        self.assertFalse(bad01.admitted)

        # PR-02
        ok02 = audit_ucp_shipping_discount_double_count_and_get_order_signatures(
            {
                "subtotal_minor": 3200,
                "shipping_base_minor": 599,
                "fulfillment_total_minor": 599,
                "shipping_discount_minor": -599,
                "other_discount_minor": 0,
                "discount_total_minor": -599,
                "tax_minor": 0,
                "grand_total_minor": 3200,
                "get_order_200_headers": {
                    "Signature": "sig1=:YWJj:",
                    "Signature-Input": 'sig1=("@status" "content-digest");created=1761177600',
                    "Content-Digest": "sha-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:",
                },
            }
        )
        self.assertTrue(ok02.admitted)
        bad02 = audit_ucp_shipping_discount_double_count_and_get_order_signatures(
            {
                "subtotal_minor": 3200,
                "shipping_base_minor": 599,
                "fulfillment_total_minor": 0,
                "shipping_discount_minor": -599,
                "other_discount_minor": 0,
                "discount_total_minor": -599,
                "tax_minor": 0,
                "grand_total_minor": 2601,
                "get_order_200_headers": {},
            }
        )
        self.assertFalse(bad02.admitted)

        # PR-03
        ok03 = audit_ucp_product_property_value_and_single_type_extends(
            {
                "product_attributes": [
                    {"name": "Battery Life", "value": "18 hours", "numeric_value": 18, "unit": "HUR"}
                ],
                "capability_extends": ["dev.ucp.shopping.checkout"],
            }
        )
        self.assertTrue(ok03.admitted)
        bad03 = audit_ucp_product_property_value_and_single_type_extends(
            {
                "product_attributes": [{"name": "Battery Life", "value": "18 hours", "numeric_value": 18}],
                "capability_extends": "dev.ucp.shopping.checkout",
            }
        )
        self.assertFalse(bad03.admitted)

        # PR-04
        ok04 = audit_ucp_checkout_ancillaries_and_openattribution_telemetry(
            {
                "checkout_line_item_ids": ["li_laptop_01"],
                "ancillaries": [
                    {"parent_line_item_id": "li_laptop_01", "category": "protection_plan", "selected": False},
                    {"parent_line_item_id": "li_laptop_01", "category": "regulatory_fee", "selected": True},
                ],
                "openattribution_telemetry": {
                    "namespace": "org.openattribution.telemetry",
                    "citations": [
                        {
                            "content_id": "art_9921",
                            "source_url": "https://reviews.example.com/laptops/2026",
                            "retrieval_turn": 1,
                        }
                    ],
                },
            }
        )
        self.assertTrue(ok04.admitted)
        bad04 = audit_ucp_checkout_ancillaries_and_openattribution_telemetry(
            {
                "checkout_line_item_ids": ["li_laptop_01"],
                "ancillaries": [
                    {"parent_line_item_id": "li_unknown_99", "category": "regulatory_fee", "selected": False}
                ],
                "openattribution_telemetry": {"namespace": "org.openattribution.telemetry", "citations": []},
            }
        )
        self.assertFalse(bad04.admitted)

        # PR-05
        ok05 = audit_acp_universal_product_types_and_multi_location_feed(
            {
                "product_type": "subscription",
                "fulfillment_mode": "digital_delivery",
                "billing_cadence": "P1M",
                "requested_qty": 1,
                "location_feed": {
                    "location_id": "loc_seoul_01",
                    "store_status": "open",
                    "in_stock_qty": 10,
                    "supported_fulfillment_modes": ["digital_delivery", "in_store_pickup"],
                },
            }
        )
        self.assertTrue(ok05.admitted)
        bad05 = audit_acp_universal_product_types_and_multi_location_feed(
            {
                "product_type": "digital",
                "fulfillment_mode": "shipping",
                "requested_qty": 2,
                "location_feed": {
                    "location_id": "loc_seoul_01",
                    "store_status": "closed",
                    "in_stock_qty": 1,
                    "supported_fulfillment_modes": ["in_store_pickup"],
                },
            }
        )
        self.assertFalse(bad05.admitted)

        # PR-06
        ok06 = audit_acp_merchant_gift_card_source_and_extended_iin(
            {
                "checkout_merchant_id": "merch_acme_01",
                "gift_card": {
                    "sourceType": "GiftCard",
                    "issuing_merchant_id": "merch_acme_01",
                    "available_balance_minor": 5000,
                    "redeem_amount_minor": 2500,
                    "pin_verified": True,
                },
                "card_iin": "41111122",
            }
        )
        self.assertTrue(ok06.admitted)
        bad06 = audit_acp_merchant_gift_card_source_and_extended_iin(
            {
                "checkout_merchant_id": "merch_acme_01",
                "gift_card": {
                    "sourceType": "GiftCard",
                    "issuing_merchant_id": "merch_other_99",
                    "available_balance_minor": 1000,
                    "redeem_amount_minor": 2500,
                    "pin_verified": False,
                },
                "card_iin": "41111",
            }
        )
        self.assertFalse(bad06.admitted)

        # PR-07
        ok07 = audit_ap2_social_welfare_mandate_and_discovery_polling(
            {
                "welfare_mandate": {
                    "allowed_mccs": ["5411", "5912"],
                    "merchant_mcc": "5411",
                    "allowed_regions": ["kr-inje-gun"],
                    "merchant_region": "kr-inje-gun",
                    "cash_out_requested": False,
                    "now_epoch": 1761177600,
                    "expiry_epoch": 1761264000,
                },
                "discovery_poll": {
                    "if_none_match": '"etag-stock-v4"',
                    "current_etag": '"etag-stock-v4"',
                    "full_ap2_handshake_used": False,
                    "response_status": 304,
                },
            }
        )
        self.assertTrue(ok07.admitted)
        bad07 = audit_ap2_social_welfare_mandate_and_discovery_polling(
            {
                "welfare_mandate": {
                    "allowed_mccs": ["5411"],
                    "merchant_mcc": "7995",
                    "allowed_regions": ["kr-inje-gun"],
                    "merchant_region": "kr-seoul",
                    "cash_out_requested": True,
                    "now_epoch": 1761300000,
                    "expiry_epoch": 1761264000,
                },
                "discovery_poll": {
                    "if_none_match": '"etag-stock-v4"',
                    "current_etag": '"etag-stock-v4"',
                    "full_ap2_handshake_used": True,
                    "response_status": 200,
                },
            }
        )
        self.assertFalse(bad07.admitted)

    def test_x402_guards(self) -> None:
        # PR-08
        ok08 = audit_x402_hook_correlation_abort_release_and_paywall_xss(
            {
                "before_hook_invocation_id": "inv_01J8X402",
                "completion_hook_invocation_id": "inv_01J8X402",
                "aborted_by_second_before_hook": True,
                "failure_hook_called": True,
                "reserved_budget_released": True,
                "paywall_serialized_json": r'{"description":"\u003c/script\u003e\u003cscript\u003ealert(1)\u003c/script\u003e"}',
            }
        )
        self.assertTrue(ok08.admitted)
        bad08 = audit_x402_hook_correlation_abort_release_and_paywall_xss(
            {
                "before_hook_invocation_id": "inv_01J8X402",
                "completion_hook_invocation_id": "inv_MISMATCH",
                "aborted_by_second_before_hook": True,
                "failure_hook_called": False,
                "reserved_budget_released": False,
                "paywall_serialized_json": '{"description":"</script><script>alert(1)</script>"}',
            }
        )
        self.assertFalse(bad08.admitted)

        # PR-09
        ok09 = audit_x402_erc8183_job_escrow_and_delivery_conformance(
            {
                "scheme": "job-escrow",
                "job_state": "EVALUATED",
                "evaluator_verdict": "PASS",
                "settlement_action": "RELEASE_TO_WORKER",
                "ext_delivery": {
                    "deliverable_sha256": "a" * 64,
                    "expected_spec_sha256": "a" * 64,
                    "schema_conforms": True,
                    "evaluator_signature": "0x99887766554433221100",
                },
            }
        )
        self.assertTrue(ok09.admitted)
        bad09 = audit_x402_erc8183_job_escrow_and_delivery_conformance(
            {
                "scheme": "job-escrow",
                "job_state": "SUBMITTED",
                "evaluator_verdict": "FAIL",
                "settlement_action": "RELEASE_TO_WORKER",
                "ext_delivery": {
                    "deliverable_sha256": "b" * 64,
                    "expected_spec_sha256": "a" * 64,
                    "schema_conforms": False,
                    "evaluator_signature": "",
                },
            }
        )
        self.assertFalse(bad09.admitted)

        # PR-10
        ok10 = audit_x402_cardano_raw_cbor_preservation_and_spec_payload(
            {
                "client_signed_cbor_hex": "84a40081825820" + "11" * 32,
                "facilitator_submitted_cbor_hex": "84a40081825820" + "11" * 32,
                "reencoded_by_facilitator": False,
                "payload_encoding": "cardano_cbor_hex",
            }
        )
        self.assertTrue(ok10.admitted)
        bad10 = audit_x402_cardano_raw_cbor_preservation_and_spec_payload(
            {
                "client_signed_cbor_hex": "AAACAAgA+tJ6L3/SuiBase64==",
                "facilitator_submitted_cbor_hex": "84a400d9010281825820" + "11" * 32,
                "reencoded_by_facilitator": True,
                "payload_encoding": "sui_bcs_base64",
            }
        )
        self.assertFalse(bad10.admitted)

        # PR-11
        ok11 = audit_x402_agreement_session_terms_and_go_svm_failed_tx(
            {
                "agreement_session": {
                    "agreed_terms_sha256": "c" * 64,
                    "current_terms_sha256": "c" * 64,
                    "cumulative_spend_minor": 400,
                    "payment_amount_minor": 100,
                    "session_cap_minor": 1000,
                    "now_epoch": 1761177600,
                    "expires_epoch": 1761264000,
                },
                "go_svm_confirmation": {
                    "tx_confirmed_onchain": True,
                    "status_err": "InstructionError(0, Custom(1))",
                    "recorded_settlement_state": "settlement_failed",
                },
            }
        )
        self.assertTrue(ok11.admitted)
        bad11 = audit_x402_agreement_session_terms_and_go_svm_failed_tx(
            {
                "agreement_session": {
                    "agreed_terms_sha256": "c" * 64,
                    "current_terms_sha256": "c" * 64,
                    "cumulative_spend_minor": 400,
                    "payment_amount_minor": 100,
                    "session_cap_minor": 1000,
                    "now_epoch": 1761177600,
                    "expires_epoch": 1761264000,
                },
                "go_svm_confirmation": {
                    "tx_confirmed_onchain": True,
                    "status_err": "InstructionError(0, Custom(1))",
                    "recorded_settlement_state": "settlement_pending",
                },
            }
        )
        self.assertFalse(bad11.admitted)

        # PR-12
        ok12 = audit_x402_solidarity_owner_share_and_payment_backed_reviews(
            {
                "solidarity": {
                    "owner_consented": True,
                    "seller_price_minor": 1000,
                    "seller_received_minor": 1000,
                    "humanitarian_share_minor": 1,
                    "monthly_donated_minor": 250,
                    "monthly_cap_minor": 500,
                },
                "review": {
                    "settlement_tx_hash": "0xabc123",
                    "verified_settlement_tx_hashes": ["0xabc123"],
                    "reviewer_wallet": "0xBuyer01",
                    "tx_payer_wallet": "0xBuyer01",
                },
            }
        )
        self.assertTrue(ok12.admitted)
        bad12 = audit_x402_solidarity_owner_share_and_payment_backed_reviews(
            {
                "solidarity": {
                    "owner_consented": True,
                    "seller_price_minor": 1000,
                    "seller_received_minor": 999,
                    "humanitarian_share_minor": 1,
                    "monthly_donated_minor": 500,
                    "monthly_cap_minor": 500,
                },
                "review": {
                    "settlement_tx_hash": "0xfake999",
                    "verified_settlement_tx_hashes": ["0xabc123"],
                    "reviewer_wallet": "0xSybil99",
                    "tx_payer_wallet": "0xBuyer01",
                },
            }
        )
        self.assertFalse(bad12.admitted)

    def test_mcp_and_tau2_guards(self) -> None:
        # PR-13
        ok13 = audit_mcp_error_structured_content_and_uri_template_id(
            {
                "tool_error_result": {
                    "isError": True,
                    "structuredContent": {"errorCode": "INSUFFICIENT_FUNDS", "retryable": False},
                },
                "resource_templates": [
                    {"uriTemplate": "ucp://orders/{order_id}"},
                    {"uriTemplate": "ucp://catalog/{sku}"},
                ],
            }
        )
        self.assertTrue(ok13.admitted)
        bad13 = audit_mcp_error_structured_content_and_uri_template_id(
            {
                "tool_error_result": {"isError": True, "structuredContent": None},
                "resource_templates": [
                    {"uriTemplate": "ucp://orders/{order_id}"},
                    {"uriTemplate": "ucp://orders/{order_id}"},
                ],
            }
        )
        self.assertFalse(bad13.admitted)

        # PR-14
        ok14 = audit_mcp_tool_side_effect_class_and_manifest_trust_tier(
            {
                "side_effect_classification": "irreversible_write",
                "server_trust_tier": "regulated_financial",
                "required_trust_tier": "hardware_attested",
                "human_approval_granted": True,
            }
        )
        self.assertTrue(ok14.admitted)
        bad14 = audit_mcp_tool_side_effect_class_and_manifest_trust_tier(
            {
                "side_effect_classification": "irreversible_write",
                "server_trust_tier": "unverified",
                "required_trust_tier": "hardware_attested",
                "human_approval_granted": False,
            }
        )
        self.assertFalse(bad14.admitted)

        # PR-15
        ok15 = audit_tau2_retail_confirmation_stop_and_airline_extra_passenger(
            {
                "agent_awaiting_confirmation": True,
                "user_sim_emitted_stop": False,
                "task_instructed_passengers": ["Noah Patel"],
                "user_sim_requested_passengers": ["Noah Patel"],
            }
        )
        self.assertTrue(ok15.admitted)
        bad15 = audit_tau2_retail_confirmation_stop_and_airline_extra_passenger(
            {
                "agent_awaiting_confirmation": True,
                "user_sim_emitted_stop": True,
                "task_instructed_passengers": ["Noah Patel"],
                "user_sim_requested_passengers": ["Noah Patel", "Priya Ahmed"],
            }
        )
        self.assertFalse(bad15.admitted)

        # PR-16
        ok16 = audit_tau2_banking_unrequested_referral_and_openai_tool_call_schema(
            {
                "requested_referral_card": "Crypto-Cash-Back",
                "documented_referral_cards": ["Silver-Rewards", "Travel-Plus"],
                "agent_referred_card": None,
                "litellm_tool_calls": [
                    {
                        "id": "call_01",
                        "type": "function",
                        "function": {"name": "lookup_referral_policy", "arguments": '{"card":"Crypto-Cash-Back"}'},
                    }
                ],
            }
        )
        self.assertTrue(ok16.admitted)
        bad16 = audit_tau2_banking_unrequested_referral_and_openai_tool_call_schema(
            {
                "requested_referral_card": "Crypto-Cash-Back",
                "documented_referral_cards": ["Silver-Rewards", "Travel-Plus"],
                "agent_referred_card": "Silver-Rewards",
                "litellm_tool_calls": [
                    {
                        "id": "call_01",
                        "name": "lookup_referral_policy",
                        "type": "function",
                        "function": {"name": "lookup_referral_policy", "arguments": "{}"},
                    }
                ],
            }
        )
        self.assertFalse(bad16.admitted)


if __name__ == "__main__":
    unittest.main()
