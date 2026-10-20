"""Unit tests for Stage 104 guardrails across UCP, ACP, Google AP2 + x402, and Sierra tau2-bench."""

from __future__ import annotations

import unittest

from lab.ucp_wba_keys_ask_rdns_acp_3ds_decimal_tau2_nl_judge_guard import (
    validate_acp_consumer_3ds_mixed_fulfillment_8char_iin_and_b2b_decimal_qty_guard,
    validate_ap2_verifier_checkout_hash_cross_merchant_budget_and_x402_spendguard_guard,
    validate_tau2_nl_judge_verdict_count_paired_list_action_and_sorted_kb_guard,
    validate_ucp_wba_keys_ask_rdns_authority_and_rating_guard,
)


class TestStage104Guards(unittest.TestCase):
    def test_ucp_wba_keys_ask_rdns_authority_and_rating_compliant(self) -> None:
        payload = {
            "profile_keys_and_wba": {
                "has_legacy_signing_keys_field": False,
                "keys": [{"kty": "OKP", "crv": "Ed25519", "kid": "thumb_99"}],
                "is_wba_dual_audience": True,
                "signature_tag": "web-bot-auth",
                "covered_components": ["@authority", "ucp-agent", "signature-agent"],
                "keyid_is_rfc7638_thumbprint": True,
                "created": 1792530000,
                "expires": 1792530060,
            },
            "ask_capability": {
                "mutated_commerce_state": False,
                "superseded_structured_capability": False,
                "answer_plain": "Sale items can be returned within 14 days for store credit.",
            },
            "rdns_authority_binding": {
                "capability_name": "com.example-shop.shopping.loyalty",
                "schema_url": "https://schemas.example-shop.com/ucp/loyalty.json",
                "spec_url": "https://docs.thirdparty-host.org/loyalty-spec",
            },
            "rating_check": {
                "count": 100,
                "verified_count": 82,
                "distribution": {"5": 60, "4": 25, "3": 10, "2": 3, "1": 2},
            },
        }
        res = validate_ucp_wba_keys_ask_rdns_authority_and_rating_guard(payload)
        self.assertTrue(res["allowed"], res["violations"])

    def test_ucp_wba_keys_ask_rdns_authority_and_rating_violations(self) -> None:
        payload = {
            "profile_keys_and_wba": {
                "has_legacy_signing_keys_field": True,
                "keys": [],
                "is_wba_dual_audience": True,
                "signature_tag": "wrong-tag",
                "covered_components": ["ucp-agent"],
                "keyid_is_rfc7638_thumbprint": False,
                "created": 1792530060,
                "expires": 1792530000,
            },
            "ask_capability": {
                "mutated_commerce_state": True,
                "superseded_structured_capability": True,
                "answer_plain": "",
            },
            "rdns_authority_binding": {
                "capability_name": "com.example-shop.shopping.loyalty",
                "schema_url": "https://evil-attacker.io/ucp/loyalty.json",
                "spec_url": "http://insecure.example-shop.com/spec",
            },
            "rating_check": {
                "count": 50,
                "verified_count": 65,
                "distribution": {"5": 40, "4": 25},
            },
        }
        res = validate_ucp_wba_keys_ask_rdns_authority_and_rating_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("UCP_566_LEGACY_SIGNING_KEYS_FIELD_FORBIDDEN", res["violations"])
        self.assertIn("UCP_483_WBA_MISSING_WEB_BOT_AUTH_TAG", res["violations"])
        self.assertIn("UCP_538_ASK_CAPABILITY_MUTATED_COMMERCE_STATE", res["violations"])
        self.assertIn("UCP_530_SCHEMA_URL_AUTHORITY_MISMATCH", res["violations"])
        self.assertIn("UCP_460_VERIFIED_COUNT_EXCEEDS_TOTAL_COUNT", res["violations"])

    def test_acp_consumer_3ds_mixed_fulfillment_8char_iin_and_b2b_decimal_qty_compliant(self) -> None:
        payload = {
            "fulfillment_and_3ds": {
                "has_physical_shipping": True,
                "fulfillment_address": {
                    "name": "Alice Buyer",
                    "phone": "+14155550101",
                    "email": "alice@example.com",
                },
                "cart_line_item_ids": ["li_phys_1", "li_dig_2"],
                "fulfillment_covered_item_ids": ["li_phys_1", "li_dig_2"],
                "tax_computed_at_complete": True,
                "shipping_address_in_complete": True,
                "requires_consumer_3ds": True,
                "consumer_3ds_cryptogram_verified": True,
            },
            "card_metadata": {
                "iin": "41111122",
                "display_last4": "4242",
            },
            "b2b_line_item": {
                "quantity": 2.5,
                "unit_price_minor": 1200,
                "subtotal_minor": 3000,
            },
        }
        res = validate_acp_consumer_3ds_mixed_fulfillment_8char_iin_and_b2b_decimal_qty_guard(payload)
        self.assertTrue(res["allowed"], res["violations"])

    def test_acp_consumer_3ds_mixed_fulfillment_8char_iin_and_b2b_decimal_qty_violations(self) -> None:
        payload = {
            "fulfillment_and_3ds": {
                "has_physical_shipping": True,
                "fulfillment_address": {"name": "Alice Buyer"},
                "cart_line_item_ids": ["li_phys_1", "li_dig_2"],
                "fulfillment_covered_item_ids": ["li_phys_1"],
                "tax_computed_at_complete": True,
                "shipping_address_in_complete": False,
                "requires_consumer_3ds": True,
                "consumer_3ds_cryptogram_verified": False,
            },
            "card_metadata": {
                "iin": "4111112299",
                "display_last4": "424",
            },
            "b2b_line_item": {
                "quantity": -1.5,
                "unit_price_minor": 1200,
                "subtotal_minor": 3000,
            },
        }
        res = validate_acp_consumer_3ds_mixed_fulfillment_8char_iin_and_b2b_decimal_qty_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("ACP_52_MISSING_FULFILLMENT_CONTACT_FIELD:phone", res["violations"])
        self.assertIn("ACP_52_MIXED_CART_ITEMS_NOT_FULLY_COVERED_BY_FULFILLMENT_OPTIONS", res["violations"])
        self.assertIn("ACP_53_UNVERIFIED_CONSUMER_3DS_AUTHENTICATION", res["violations"])
        self.assertIn("ACP_9_INVALID_ISO7812_IIN_LENGTH", res["violations"])
        self.assertIn("ACP_3_NON_POSITIVE_B2B_DECIMAL_QUANTITY", res["violations"])

    def test_ap2_verifier_checkout_hash_cross_merchant_budget_and_x402_spendguard_compliant(self) -> None:
        payload = {
            "verifier_checkout_hash": {
                "verifier_recomputed_checkout_hash": True,
                "recomputed_checkout_hash": "sha256_ch_9911",
                "payment_mandate_checkout_hash": "sha256_ch_9911",
            },
            "cross_merchant_budget": {
                "session_budget_cap_minor": 50000,
                "merchant_allocations": [
                    {"merchant_id": "m_flight", "amount_minor": 30000, "nonce": "n_1"},
                    {"merchant_id": "m_hotel", "amount_minor": 18000, "nonce": "n_2"},
                ],
            },
            "x402_spendguard": {
                "call_amount_usdc_micro": 50000,
                "max_per_call_usdc_micro": 100000,
                "window_cumulative_usdc_micro": 400000,
                "max_window_usdc_micro": 500000,
            },
        }
        res = validate_ap2_verifier_checkout_hash_cross_merchant_budget_and_x402_spendguard_guard(payload)
        self.assertTrue(res["allowed"], res["violations"])

    def test_ap2_verifier_checkout_hash_cross_merchant_budget_and_x402_spendguard_violations(self) -> None:
        payload = {
            "verifier_checkout_hash": {
                "verifier_recomputed_checkout_hash": False,
                "recomputed_checkout_hash": "sha256_ch_9911",
                "payment_mandate_checkout_hash": "sha256_tampered",
            },
            "cross_merchant_budget": {
                "session_budget_cap_minor": 50000,
                "merchant_allocations": [
                    {"merchant_id": "m_flight", "amount_minor": 35000, "nonce": "n_dup"},
                    {"merchant_id": "m_hotel", "amount_minor": 25000, "nonce": "n_dup"},
                ],
            },
            "x402_spendguard": {
                "call_amount_usdc_micro": 150000,
                "max_per_call_usdc_micro": 100000,
                "window_cumulative_usdc_micro": 600000,
                "max_window_usdc_micro": 500000,
            },
        }
        res = validate_ap2_verifier_checkout_hash_cross_merchant_budget_and_x402_spendguard_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("AP2_243_VERIFIER_SKIPPED_CHECKOUT_HASH_RECOMPUTATION", res["violations"])
        self.assertIn("AP2_243_CHECKOUT_HASH_MISMATCH", res["violations"])
        self.assertIn("AP2_252_CROSS_MERCHANT_CUMULATIVE_BUDGET_EXCEEDED", res["violations"])
        self.assertIn("AP2_252_DUPLICATE_CROSS_MERCHANT_ALLOCATION_NONCE", res["violations"])
        self.assertIn("X402_354_SPENDGUARD_PER_CALL_CAP_EXCEEDED", res["violations"])

    def test_tau2_nl_judge_verdict_count_paired_list_action_and_sorted_kb_compliant(self) -> None:
        payload = {
            "nl_judge_check": {
                "serialized_literal_assistant_none": False,
                "expected_assertion_count": 3,
                "returned_verdict_count": 3,
            },
            "action_comparison_check": {
                "gold_item_ids": ["item_1", "item_2"],
                "gold_new_item_ids": ["new_1", "new_2"],
                "call_item_ids": ["item_2", "item_1"],
                "call_new_item_ids": ["new_2", "new_1"],
                "gold_arg_keys": ["order_id", "item_ids", "new_item_ids"],
                "call_arg_keys": ["order_id", "item_ids", "new_item_ids"],
            },
            "knowledge_base_load": {
                "loaded_filenames": ["doc_01.json", "doc_02.json", "doc_03.json"],
            },
        }
        res = validate_tau2_nl_judge_verdict_count_paired_list_action_and_sorted_kb_guard(payload)
        self.assertTrue(res["allowed"], res["violations"])

    def test_tau2_nl_judge_verdict_count_paired_list_action_and_sorted_kb_violations(self) -> None:
        payload = {
            "nl_judge_check": {
                "serialized_literal_assistant_none": True,
                "expected_assertion_count": 3,
                "returned_verdict_count": 0,
            },
            "action_comparison_check": {
                "gold_item_ids": ["item_1", "item_2"],
                "gold_new_item_ids": ["new_1", "new_2"],
                "call_item_ids": ["item_2", "item_1"],
                "call_new_item_ids": ["new_1", "new_2"],
                "gold_arg_keys": ["order_id", "item_ids", "new_item_ids"],
                "call_arg_keys": ["order_id"],
            },
            "knowledge_base_load": {
                "loaded_filenames": ["doc_03.json", "doc_01.json", "doc_02.json"],
            },
        }
        res = validate_tau2_nl_judge_verdict_count_paired_list_action_and_sorted_kb_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("TAU2_584_LITERAL_ASSISTANT_NONE_IN_NL_JUDGE_PROMPT", res["violations"])
        self.assertIn("TAU2_581_NL_JUDGE_VERDICT_COUNT_MISMATCH", res["violations"])
        self.assertIn("TAU2_570_SWAPPED_OR_MISMATCHED_PAIRED_ACTION_LISTS", res["violations"])
        self.assertIn("TAU2_569_OMITTED_OR_EXTRA_GOLD_ARG_KEYS", res["violations"])
        self.assertIn("TAU2_566_UNSORTED_FILESYSTEM_KB_LOAD_ORDER", res["violations"])


if __name__ == "__main__":
    unittest.main()
