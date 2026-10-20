"""Unit tests for Stage 72 UCP, ACP, Google AP2, and Sierra tau2-bench runtime guards."""

from __future__ import annotations

import unittest

from lab.ucp_consent_return_etag_acp_affiliate_trace_ap2_haggle_solana_tau2_vpn_guard import (
    verify_acp_recurring_allowance_affiliate_attribution_intent_trace_and_3ds_channel,
    verify_ap2_haggle_negotiation_solana_algorand_binding_and_credential_sanitization,
    verify_tau2_banking_read_allowlist_retail_modify_items_vpn_deepcopy_and_replay_hallucination,
    verify_ucp_consent_persistence_return_policy_etag_p521_and_fulfillment_link,
)


class TestStage72Guards(unittest.TestCase):
    def test_ucp_consent_return_policy_etag_p521_and_fulfillment_passes(self) -> None:
        res = verify_ucp_consent_persistence_return_policy_etag_p521_and_fulfillment_link(
            {
                "consent_update": {
                    "prior_consent": {"marketing": False, "analytics": True},
                    "request_omitted_consent": True,
                    "resulting_consent": {"marketing": False, "analytics": True},
                },
                "return_policy": {
                    "type": "dev.ucp.shopping.policy.return",
                    "final_sale": False,
                    "window": {"days": 30, "anchor": "delivered"},
                    "supported_resolutions": ["refund", "exchange"],
                    "unstated_fee_rendered_as_free": False,
                },
                "conditional_write": {
                    "current_etag": '"v4-checkout-901"',
                    "if_match": '"v4-checkout-901"',
                    "conditional_required": True,
                    "applied_mutation": True,
                },
                "authority_binding": {
                    "name": "com.example.pay",
                    "authority_prefix": "com.example.pay",
                },
                "profile_keys": [{"kty": "EC", "crv": "P-521", "alg": "ES512"}],
                "fulfillment_event": {
                    "fulfillment_method_id": "fm_ship_1",
                    "fulfillment_option_id": "opt_express",
                    "estimated_delivery": {
                        "earliest": "2026-10-22T09:00:00Z",
                        "latest": "2026-10-23T18:00:00Z",
                    },
                },
                "availability": {
                    "status": "low_stock",
                    "quantity": 3,
                    "restock_at": "2026-10-28T00:00:00Z",
                },
            }
        )
        self.assertTrue(res.allowed)
        self.assertEqual(
            res.reason_code,
            "ucp_consent_return_policy_etag_p521_and_fulfillment_verified",
        )

    def test_ucp_consent_return_policy_etag_and_p521_blocks_violations(self) -> None:
        # 1. buyer.consent dropped during full-replacement update (#660)
        r1 = verify_ucp_consent_persistence_return_policy_etag_p521_and_fulfillment_link(
            {
                "consent_update": {
                    "prior_consent": {"marketing": False},
                    "request_omitted_consent": True,
                    "resulting_consent": {"marketing": True},
                }
            }
        )
        self.assertFalse(r1.allowed)
        self.assertEqual(r1.reason_code, "ucp_buyer_consent_dropped_on_full_replacement_update")

        # 2. final_sale=True combined with return window (#634)
        r2 = verify_ucp_consent_persistence_return_policy_etag_p521_and_fulfillment_link(
            {
                "return_policy": {
                    "type": "dev.ucp.shopping.policy.return",
                    "final_sale": True,
                    "window": {"days": 14, "anchor": "delivered"},
                }
            }
        )
        self.assertFalse(r2.allowed)
        self.assertEqual(r2.reason_code, "ucp_return_policy_final_sale_with_return_terms_invalid")

        # 3. ETag mismatch still applied mutation (#628)
        r3 = verify_ucp_consent_persistence_return_policy_etag_p521_and_fulfillment_link(
            {
                "conditional_write": {
                    "current_etag": '"v5"',
                    "if_match": '"v4"',
                    "applied_mutation": True,
                }
            }
        )
        self.assertFalse(r3.allowed)
        self.assertEqual(r3.reason_code, "ucp_checkout_conditional_write_etag_mismatch_or_missing")

        # 4. P-521 key paired with ES256 (#625)
        r4 = verify_ucp_consent_persistence_return_policy_etag_p521_and_fulfillment_link(
            {"profile_keys": [{"kty": "EC", "crv": "P-521", "alg": "ES256"}]}
        )
        self.assertFalse(r4.allowed)
        self.assertEqual(r4.reason_code, "ucp_profile_p521_key_alg_mismatch")

    def test_acp_recurring_allowance_affiliate_and_intent_trace_passes(self) -> None:
        res = verify_acp_recurring_allowance_affiliate_attribution_intent_trace_and_3ds_channel(
            {
                "authentication_metadata": {"acquirer_bin": "444444", "acquirer_merchant_id": "m_1"},
                "payment_provider": {
                    "provider": "adyen",
                    "merchant_id": "merch_adyen_001",
                    "authentication_provider": "adyen_3ds",
                },
                "allowance": {
                    "reason": "subscription",
                    "max_amount": 35988,
                    "billing_cycle": {"interval": "month", "interval_count": 1},
                    "amount_per_cycle": 2999,
                    "max_cycles": 12,
                },
                "affiliate_attribution": {
                    "provider": "impact.com",
                    "token": "aff_tok_opaque_901",
                    "echoed_in_read_or_webhook": False,
                    "same_idempotency_key_different_payload": False,
                    "contains_pii": False,
                },
                "intent_trace": {
                    "reason_code": "shipping_cost",
                    "trace_summary": "Buyer declined $18 standard shipping fee.",
                    "metadata": {"shipping_minor": 1800, "threshold_minor": 500},
                    "echoed_in_get_response": False,
                },
                "lodging_checkout": {"quote_token_revalidated": True},
            }
        )
        self.assertTrue(res.allowed)
        self.assertEqual(
            res.reason_code,
            "acp_recurring_allowance_affiliate_intent_trace_and_3ds_verified",
        )

    def test_acp_recurring_allowance_affiliate_and_intent_trace_blocks_violations(self) -> None:
        # 1. Deprecated channel in AuthenticationMetadata (#85)
        r1 = verify_acp_recurring_allowance_affiliate_attribution_intent_trace_and_3ds_channel(
            {"authentication_metadata": {"channel": "browser"}}
        )
        self.assertFalse(r1.allowed)
        self.assertEqual(r1.reason_code, "acp_3ds_authentication_metadata_deprecated_channel_present")

        # 2. Subscription allowance missing billing_cycle / amount_per_cycle (#73)
        r2 = verify_acp_recurring_allowance_affiliate_attribution_intent_trace_and_3ds_channel(
            {"allowance": {"reason": "subscription", "max_amount": 2999}}
        )
        self.assertFalse(r2.allowed)
        self.assertEqual(
            r2.reason_code,
            "acp_recurring_allowance_missing_billing_cycle_or_amount_per_cycle",
        )

        # 3. Write-only affiliate_attribution leaked in GET/webhook response (#57)
        r3 = verify_acp_recurring_allowance_affiliate_attribution_intent_trace_and_3ds_channel(
            {
                "affiliate_attribution": {
                    "provider": "impact.com",
                    "token": "aff_tok_1",
                    "echoed_in_read_or_webhook": True,
                }
            }
        )
        self.assertFalse(r3.allowed)
        self.assertEqual(r3.reason_code, "acp_affiliate_attribution_leaked_in_read_or_webhook")

        # 4. IntentTrace metadata contains nested object (#54)
        r4 = verify_acp_recurring_allowance_affiliate_attribution_intent_trace_and_3ds_channel(
            {
                "intent_trace": {
                    "reason_code": "price_sensitivity",
                    "metadata": {"nested": {"bad": True}},
                }
            }
        )
        self.assertFalse(r4.allowed)
        self.assertEqual(r4.reason_code, "acp_intent_trace_invalid_or_leaked_in_response")

    def test_ap2_haggle_solana_algorand_and_credential_sanitization_passes(self) -> None:
        res = verify_ap2_haggle_negotiation_solana_algorand_binding_and_credential_sanitization(
            {
                "haggle_negotiation": {
                    "rounds_used": 3,
                    "max_rounds": 5,
                    "final_price": 85.0,
                    "buyer_walk_away_price": 90.0,
                    "merchant_cost_floor": 75.0,
                    "intermediate_offers_signed": False,
                    "outcome_status": "accepted",
                    "outcome_has_signed_cart_mandate": True,
                },
                "crypto_solana_settlement": {
                    "single_use_reference_pubkey_bound": True,
                    "recipient_matches_mandate": True,
                    "amount_matches_mandate": True,
                    "spl_mint_matches_mandate": True,
                },
                "crypto_algo_settlement": {
                    "mandate_token": "mnd_token_1234567890abcdefghij_extra",
                    "tx_note": "av:mnd_token_1234567890",
                    "asa_amount_recipient_matched": True,
                },
                "credential_binding": {
                    "raw_wallet_credential_exposed": False,
                    "opaque_credential_reference_returned": True,
                    "payment_mandate_payer": "did:example:alice",
                    "token_owner": "did:example:alice",
                },
                "adk_session_state": {"serialized_via_model_dump": True},
            }
        )
        self.assertTrue(res.allowed)
        self.assertEqual(
            res.reason_code,
            "ap2_haggle_solana_algorand_and_credential_sanitization_verified",
        )

    def test_ap2_haggle_solana_algorand_and_credential_blocks_violations(self) -> None:
        # 1. Haggle accepted outcome missing signed CartMandate (#229)
        r1 = verify_ap2_haggle_negotiation_solana_algorand_binding_and_credential_sanitization(
            {
                "haggle_negotiation": {
                    "rounds_used": 2,
                    "max_rounds": 5,
                    "final_price": 85.0,
                    "buyer_walk_away_price": 90.0,
                    "merchant_cost_floor": 75.0,
                    "intermediate_offers_signed": False,
                    "outcome_status": "accepted",
                    "outcome_has_signed_cart_mandate": False,
                }
            }
        )
        self.assertFalse(r1.allowed)
        self.assertEqual(
            r1.reason_code,
            "ap2_haggle_negotiation_constraints_or_signed_outcome_violated",
        )

        # 2. Algorand note prefix mismatch (#218)
        r2 = verify_ap2_haggle_negotiation_solana_algorand_binding_and_credential_sanitization(
            {
                "crypto_algo_settlement": {
                    "mandate_token": "mnd_token_1234567890abcdefghij",
                    "tx_note": "av:wrong_prefix_00000",
                    "asa_amount_recipient_matched": True,
                }
            }
        )
        self.assertFalse(r2.allowed)
        self.assertEqual(r2.reason_code, "ap2_crypto_solana_or_algorand_mandate_binding_mismatch")

        # 3. Payer != token_owner or raw wallet credential leaked (#212)
        r3 = verify_ap2_haggle_negotiation_solana_algorand_binding_and_credential_sanitization(
            {
                "credential_binding": {
                    "raw_wallet_credential_exposed": False,
                    "opaque_credential_reference_returned": True,
                    "payment_mandate_payer": "did:example:mallory",
                    "token_owner": "did:example:alice",
                }
            }
        )
        self.assertFalse(r3.allowed)
        self.assertEqual(
            r3.reason_code,
            "ap2_credential_response_unsanitized_or_payer_token_mismatch",
        )

    def test_tau2_banking_read_allowlist_retail_modify_vpn_and_replay_passes(self) -> None:
        res = verify_tau2_banking_read_allowlist_retail_modify_items_vpn_deepcopy_and_replay_hallucination(
            {
                "banking_discoverable_tool_call": {
                    "mutates_state": False,
                    "tool_name": "check_account_eligibility_102",
                    "read_log_allowlist": ["verify_identity_read_046"],
                    "logged_to_db": False,
                },
                "retail_modify_items": [
                    {
                        "item_id": "item_1",
                        "applied_price": 49.99,
                        "replacement_variant_price": 49.99,
                        "applied_options": {"size": "M"},
                        "replacement_variant_options": {"size": "M"},
                    },
                    {
                        "item_id": "item_2",
                        "applied_price": 129.00,
                        "replacement_variant_price": 129.00,
                        "applied_options": {"color": "black"},
                        "replacement_variant_options": {"color": "black"},
                    },
                ],
                "telecom_vpn_simulation": {
                    "used_deepcopy_on_default_vpn_details": True,
                    "concurrent_sim_default_performance": "EXCELLENT",
                },
                "replay_evaluation": {
                    "raised_on_unknown_hallucinated_tool": False,
                    "interleaved_thinking_raw_data_preserved": True,
                },
            }
        )
        self.assertTrue(res.allowed)
        self.assertEqual(
            res.reason_code,
            "tau2_banking_read_allowlist_retail_modify_vpn_and_replay_verified",
        )

    def test_tau2_banking_read_allowlist_retail_modify_vpn_and_replay_blocks_violations(self) -> None:
        # 1. Extra read call logged to agent_discoverable_tools (#329)
        r1 = verify_tau2_banking_read_allowlist_retail_modify_items_vpn_deepcopy_and_replay_hallucination(
            {
                "banking_discoverable_tool_call": {
                    "mutates_state": False,
                    "tool_name": "check_account_eligibility_102",
                    "read_log_allowlist": ["verify_identity_read_046"],
                    "logged_to_db": True,
                }
            }
        )
        self.assertFalse(r1.allowed)
        self.assertEqual(
            r1.reason_code,
            "tau2_banking_discoverable_tool_extra_read_logged_to_db",
        )

        # 2. Multi-item retail modification reuses first item's replacement price (#322)
        r2 = verify_tau2_banking_read_allowlist_retail_modify_items_vpn_deepcopy_and_replay_hallucination(
            {
                "retail_modify_items": [
                    {
                        "item_id": "item_2",
                        "applied_price": 49.99,
                        "replacement_variant_price": 129.00,
                        "applied_options": {"size": "M"},
                        "replacement_variant_options": {"color": "black"},
                    }
                ]
            }
        )
        self.assertFalse(r2.allowed)
        self.assertEqual(
            r2.reason_code,
            "tau2_retail_multi_item_modification_variant_price_cross_contamination",
        )

        # 3. Shared default_vpn_details reference corrupted across simulations (#301)
        r3 = verify_tau2_banking_read_allowlist_retail_modify_items_vpn_deepcopy_and_replay_hallucination(
            {
                "telecom_vpn_simulation": {
                    "used_deepcopy_on_default_vpn_details": False,
                    "concurrent_sim_default_performance": "POOR",
                }
            }
        )
        self.assertFalse(r3.allowed)
        self.assertEqual(
            r3.reason_code,
            "tau2_telecom_vpn_default_details_shared_reference_corruption",
        )

        # 4. Replay raised ValueError on unknown hallucinated tool (#273)
        r4 = verify_tau2_banking_read_allowlist_retail_modify_items_vpn_deepcopy_and_replay_hallucination(
            {"replay_evaluation": {"raised_on_unknown_hallucinated_tool": True}}
        )
        self.assertFalse(r4.allowed)
        self.assertEqual(
            r4.reason_code,
            "tau2_replay_unknown_tool_raised_or_interleaved_thinking_stripped",
        )


if __name__ == "__main__":
    unittest.main()
