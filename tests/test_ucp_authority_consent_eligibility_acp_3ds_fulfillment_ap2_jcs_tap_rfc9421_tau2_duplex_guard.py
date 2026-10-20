"""Unit tests for Stage 80 deterministic guard module."""

from __future__ import annotations

import unittest

from lab.ucp_authority_consent_eligibility_acp_3ds_fulfillment_ap2_jcs_tap_rfc9421_tau2_duplex_guard import (
    verify_acp_consumer_3ds_mixed_fulfillment_iin_and_b2b_quantity_guard,
    verify_ap2_jcs_binding_did_stark_and_tap_rfc9421_verifier_guard,
    verify_tau2_voice_rescoring_banking_ordering_and_llm_execution_guard,
    verify_ucp_authority_consent_eligibility_mandate_ttl_and_signature_guard,
)


class TestStage80Guard(unittest.TestCase):
    def test_ucp_authority_consent_eligibility_mandate_ttl_and_signature_valid(self) -> None:
        payload = {
            "capabilities": [
                {
                    "name": "dev.ucp.shopping.checkout",
                    "schema": "https://ucp.dev/schemas/shopping/checkout.json",
                },
                {
                    "name": "com.merchant-stamp.mandate-evaluation",
                    "schema": "https://api.merchant-stamp.com/ucp/mandate-evaluation.json",
                },
            ],
            "buyer": {
                "consent": {
                    "dev.ucp.consent.marketing": {
                        "granted": True,
                        "source": "platform",
                        "description": "Promotional communications",
                        "segments": {
                            "dev.ucp.consent.segment.sms": {"granted": False},
                        },
                    }
                }
            },
            "eligibility_verification": {
                "claims": [
                    {"id": "claim_loyalty_gold", "influenced_checkout": True, "status": "verified"}
                ],
                "mutated_checkout_on_verification_failure": False,
            },
            "mandate_evaluation": {
                "expired_at_admission": False,
                "entered_complete_in_progress": True,
                "expired_during_settlement": True,
                "aborted_settlement_on_post_admission_expiry": False,
            },
            "ecdsa_signature_b64": "r8sRawFixedWidth64ByteSignatureBase64UrlValue==",
            "embedded_session": {
                "is_error_notification": True,
                "params": {"error": {"code": "payment_declined", "message": "Card declined"}},
                "ec_delegate_link_open": True,
                "buyer_activated_link": True,
                "emitted_link_open_request": True,
            },
            "cart_to_checkout_conversion": {
                "cart_discount_codes": ["SAVE10", "FREESHIP"],
                "checkout_discount_codes": ["SAVE10", "FREESHIP", "LOYALTY5"],
            },
        }
        res = verify_ucp_authority_consent_eligibility_mandate_ttl_and_signature_guard(payload)
        self.assertTrue(res["allowed"])
        self.assertEqual(res["violations"], [])

    def test_ucp_authority_consent_eligibility_mandate_ttl_and_signature_violations(self) -> None:
        payload = {
            "capabilities": [
                {
                    "name": "com.merchantstamp.mandate-evaluation",
                    "schema": "https://evil-attacker.org/mandate.json",
                }
            ],
            "buyer": {
                "consent": {
                    "bad_key": {"granted": "yes", "source": "unknown"},
                }
            },
            "eligibility_verification": {
                "claims": [
                    {"id": "claim_1", "influenced_checkout": True, "status": "pending"}
                ],
                "mutated_checkout_on_verification_failure": True,
            },
            "mandate_evaluation": {
                "expired_at_admission": True,
                "entered_complete_in_progress": True,
            },
            "ecdsa_signature_b64": "MEUCIQDf7xDerEncodedSequenceSignature==",
            "embedded_session": {
                "is_error_notification": True,
                "params": {"code": "raw_unwrapped_error"},
                "ec_delegate_link_open": True,
                "buyer_activated_link": True,
                "emitted_link_open_request": False,
            },
            "cart_to_checkout_conversion": {
                "cart_discount_codes": ["SAVE10"],
                "checkout_discount_codes": [],
            },
        }
        res = verify_ucp_authority_consent_eligibility_mandate_ttl_and_signature_guard(payload)
        self.assertFalse(res["allowed"])
        for expected in (
            "UCP_NAMESPACE_AUTHORITY_BINDING_MISMATCH:0:evil-attacker.org!=merchantstamp.com",
            "UCP_CONSENT_PURPOSE_RDNS_INVALID:bad_key",
            "UCP_CONSENT_STATE_OR_SOURCE_INVALID:bad_key",
            "UCP_UNRESOLVED_ELIGIBILITY_CLAIM_BLOCKS_COMPLETE:claim_1",
            "UCP_ELIGIBILITY_FAILURE_CHECKOUT_MUTATION_FORBIDDEN",
            "UCP_EXPIRED_MANDATE_ADMITTED_TO_COMPLETE_IN_PROGRESS",
            "UCP_ECDSA_DER_SIGNATURE_ENCODING_FORBIDDEN_RAW_RS_REQUIRED",
            "UCP_EMBEDDED_ERROR_MUST_WRAP_UNDER_PARAMS_ERROR",
            "UCP_EMBEDDED_LINK_DELEGATION_OPEN_REQUEST_MISSING",
            "UCP_CART_DISCOUNT_CONTINUITY_DROPPED",
        ):
            self.assertIn(expected, res["violations"])

    def test_acp_consumer_3ds_mixed_fulfillment_iin_and_b2b_quantity_valid(self) -> None:
        payload = {
            "tls_version": "TLSv1.3",
            "fulfillment": {
                "shipping_address": {
                    "name": "Alice Buyer",
                    "phone": "+14155550101",
                    "email": "alice@example.com",
                },
                "shipping_options": [{"subtotal": 500, "tax": 45, "total": 545}],
                "cart_line_item_ids": ["li_phys_1", "li_dig_2"],
                "covered_line_item_ids": ["li_phys_1", "li_dig_2"],
            },
            "links": [{"type": "return_policy", "url": "https://merchant.example/returns"}],
            "payment_method_card": {"iin": "41111122", "display_last4": "4242"},
            "line_items": [{"id": "li_b2b_steel", "quantity": 2.5}],
        }
        res = verify_acp_consumer_3ds_mixed_fulfillment_iin_and_b2b_quantity_guard(payload)
        self.assertTrue(res["allowed"])
        self.assertEqual(res["violations"], [])

    def test_acp_consumer_3ds_mixed_fulfillment_iin_and_b2b_quantity_violations(self) -> None:
        payload = {
            "tls_version": "TLSv1.2",
            "fulfillment": {
                "shipping_address": {"street": "123 Main St"},
                "shipping_options": [{"subtotal": "500", "tax": 45, "total": 545}],
                "cart_line_item_ids": ["li_phys_1", "li_dig_2"],
                "covered_line_item_ids": ["li_phys_1"],
            },
            "links": [{"type": "seller_shop_policies", "url": "https://merchant.example/policies"}],
            "payment_method_card": {"iin": "41111", "display_last4": "424"},
            "line_items": [{"id": "li_b2b_steel", "quantity": 0}],
        }
        res = verify_acp_consumer_3ds_mixed_fulfillment_iin_and_b2b_quantity_guard(payload)
        self.assertFalse(res["allowed"])
        for expected in (
            "ACP_TLS_1_3_REQUIRED:TLSv1.2",
            "ACP_FULFILLMENT_ADDRESS_CONTACT_DETAILS_MISSING",
            "ACP_FULFILLMENT_OPTION_AMOUNT_NOT_INTEGER:0:subtotal",
            "ACP_MIXED_CART_FULFILLMENT_COVERAGE_INCOMPLETE",
            "ACP_DEPRECATED_SELLER_SHOP_POLICIES_LINK_FORBIDDEN:0",
            "ACP_CARD_IIN_LENGTH_INVALID:41111",
            "ACP_CARD_DISPLAY_LAST4_INVALID:424",
            "ACP_B2B_LINE_ITEM_QUANTITY_NON_POSITIVE:0",
        ):
            self.assertIn(expected, res["violations"])

    def test_ap2_jcs_binding_did_stark_and_tap_rfc9421_verifier_valid(self) -> None:
        payload = {
            "ap2_jcs_binding": {
                "canonicalization_scheme": "RFC8785_JCS",
                "cart_jcs_sha256": "sha256:8f9d2c3b",
                "payment_mandate_cart_hash": "sha256:8f9d2c3b",
            },
            "ap2_mandate_metadata": {
                "did_settlement_enabled": True,
                "delegation_did_verified": True,
                "stark_commitment_verified": True,
                "payment_details_modifier_data_type": "dict[str, Any]",
                "uses_legacy_vc_term": False,
            },
            "tap_rfc9421_verification": {
                "signature_base_ends_with_signature_params": True,
                "covered_components_raw": '("@authority" "@path")',
                "alg": "ed25519",
                "agent_registry_key_type": "Ed25519PublicKey",
                "nonce_recorded_before_signature_verified": False,
                "nonce_reused_before_expiry": False,
            },
        }
        res = verify_ap2_jcs_binding_did_stark_and_tap_rfc9421_verifier_guard(payload)
        self.assertTrue(res["allowed"])
        self.assertEqual(res["violations"], [])

    def test_ap2_jcs_binding_did_stark_and_tap_rfc9421_verifier_violations(self) -> None:
        payload = {
            "ap2_jcs_binding": {
                "canonicalization_scheme": "PYTHON_JSON_DUMPS",
                "cart_jcs_sha256": "sha256:8f9d2c3b",
                "payment_mandate_cart_hash": "sha256:tampered",
            },
            "ap2_mandate_metadata": {
                "did_settlement_enabled": True,
                "delegation_did_verified": False,
                "stark_commitment_verified": False,
                "payment_details_modifier_data_type": "Any",
                "uses_legacy_vc_term": True,
            },
            "tap_rfc9421_verification": {
                "signature_base_ends_with_signature_params": False,
                "covered_components_raw": '("@authority @path")',
                "alg": "ed25519",
                "agent_registry_key_type": "RSAPublicKey",
                "nonce_recorded_before_signature_verified": True,
                "nonce_reused_before_expiry": True,
            },
        }
        res = verify_ap2_jcs_binding_did_stark_and_tap_rfc9421_verifier_guard(payload)
        self.assertFalse(res["allowed"])
        for expected in (
            "AP2_JCS_RFC8785_CANONICALIZATION_REQUIRED",
            "AP2_CART_TO_PAYMENT_MANDATE_JCS_HASH_MISMATCH",
            "AP2_DID_STARK_SETTLEMENT_COMMITMENT_UNVERIFIED",
            "AP2_PAYMENT_DETAILS_MODIFIER_UNTYPED_ANY_FORBIDDEN",
            "AP2_LEGACY_VC_TERM_FORBIDDEN_USE_VDC",
            "TAP_RFC9421_SIGNATURE_PARAMS_LINE_MISSING",
            "TAP_RFC9421_COVERED_COMPONENTS_SINGLE_BLOB_INVALID",
            "TAP_RFC9421_ALG_KEY_TYPE_CONFUSION:ed25519:RSAPublicKey",
            "TAP_RFC9421_NONCE_RECORDED_BEFORE_VERIFICATION",
            "TAP_RFC9421_NONCE_REPLAY_DETECTED",
        ):
            self.assertIn(expected, res["violations"])

    def test_tau2_voice_rescoring_banking_ordering_and_llm_execution_valid(self) -> None:
        payload = {
            "voice_trajectory_rescoring": {
                "is_full_duplex_voice": True,
                "passed_communication_mode": "FULL_DUPLEX",
                "evaluated_field": "simulation.ticks",
            },
            "banking_knowledge_eval": {
                "transactions_most_recent_first": True,
                "duplicate_dispute_targeted_earliest": True,
                "unlocked_discoverable_card_reads": True,
                "called_unlocked_discoverable_card_reads": True,
                "platinum_rewards_doc_002_title_rate_pct": 10,
            },
            "action_and_replay_grader": {
                "normalized_nested_json_strings": True,
                "normalized_numeric_int_float_args": True,
                "batch_aborted_on_single_simulation_replay_error": False,
            },
            "runtime_and_airline": {
                "reservation_cancelled": True,
                "seats_restored_to_inventory": True,
                "preserved_user_message_tool_calls": True,
                "retried_context_window_exceeded_as_infra_error": False,
                "is_reasoning_model": True,
                "sent_zero_temperature_param": False,
            },
        }
        res = verify_tau2_voice_rescoring_banking_ordering_and_llm_execution_guard(payload)
        self.assertTrue(res["allowed"])
        self.assertEqual(res["violations"], [])

    def test_tau2_voice_rescoring_banking_ordering_and_llm_execution_violations(self) -> None:
        payload = {
            "voice_trajectory_rescoring": {
                "is_full_duplex_voice": True,
                "passed_communication_mode": "HALF_DUPLEX",
                "evaluated_field": "simulation.messages",
            },
            "banking_knowledge_eval": {
                "transactions_most_recent_first": False,
                "duplicate_dispute_targeted_earliest": False,
                "unlocked_discoverable_card_reads": True,
                "called_unlocked_discoverable_card_reads": False,
                "platinum_rewards_doc_002_title_rate_pct": 4,
            },
            "action_and_replay_grader": {
                "normalized_nested_json_strings": False,
                "normalized_numeric_int_float_args": False,
                "batch_aborted_on_single_simulation_replay_error": True,
            },
            "runtime_and_airline": {
                "reservation_cancelled": True,
                "seats_restored_to_inventory": False,
                "preserved_user_message_tool_calls": False,
                "retried_context_window_exceeded_as_infra_error": True,
                "is_reasoning_model": True,
                "sent_zero_temperature_param": True,
            },
        }
        res = verify_tau2_voice_rescoring_banking_ordering_and_llm_execution_guard(payload)
        self.assertFalse(res["allowed"])
        for expected in (
            "TAU2_FULL_DUPLEX_VOICE_RESCORED_AS_HALF_DUPLEX_MESSAGES",
            "TAU2_BANKING_TRANSACTIONS_NOT_REVERSE_CHRONOLOGICAL",
            "TAU2_BANKING_DUPLICATE_DISPUTE_MUST_TARGET_EARLIEST",
            "TAU2_BANKING_LOST_STOLEN_GOLD_SKIPPED_DISCOVERABLE_READS",
            "TAU2_BANKING_PLATINUM_DOC_002_CONTRADICTORY_4PCT_TITLE",
            "TAU2_ACTION_GRADER_NESTED_JSON_WHITESPACE_MISMATCH",
            "TAU2_DB_HASH_INT_FLOAT_SPELLING_SENSITIVITY",
            "TAU2_BATCH_EVALUATION_ABORTED_BY_SINGLE_REPLAY_ERROR",
            "TAU2_AIRLINE_CANCELLED_SEATS_NOT_RELEASED",
            "TAU2_LITELLM_USER_MESSAGE_TOOL_CALLS_DROPPED",
            "TAU2_CONTEXT_WINDOW_EXCEEDED_MISCLASSIFIED_AS_INFRA_ERROR",
            "TAU2_REASONING_MODEL_ZERO_TEMPERATURE_BAD_REQUEST",
        ):
            self.assertIn(expected, res["violations"])


if __name__ == "__main__":
    unittest.main()
