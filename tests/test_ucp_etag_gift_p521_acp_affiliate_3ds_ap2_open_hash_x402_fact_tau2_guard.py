"""Unit tests for Stage 100 guardrails across UCP, ACP, Google AP2, Coinbase x402, and Sierra tau2-bench."""

from __future__ import annotations

import unittest

from lab.ucp_etag_gift_p521_acp_affiliate_3ds_ap2_open_hash_x402_fact_tau2_guard import (
    compute_rfc8785_jcs_sha256,
    validate_acp_affiliate_attribution_merchant_3ds_and_hotel_hydration_guard,
    validate_ap2_open_mandate_hash_entropy_and_x402_fact_attestation_guard,
    validate_tau2_write_critic_close_account_reason_pydantic_coercion_and_solo_gt_guard,
    validate_ucp_conditional_writes_p521_mandate_ttl_and_gift_guard,
)


class TestStage100Guards(unittest.TestCase):
    def test_ucp_conditional_writes_p521_mandate_ttl_and_gift_compliant(self) -> None:
        payload = {
            "conditional_write": {
                "is_state_changing": True,
                "if_match_header": '"etag-v3"',
                "current_etag": '"etag-v3"',
                "idempotency_key_reused": False,
                "payload_digest_changed": False,
            },
            "catalog_operation": {
                "request_cannot_be_served": True,
                "response": {
                    "ucp": {"status": "error"},
                    "messages": [{"type": "error", "code": "service_unavailable"}],
                },
            },
            "signing_keys": [
                {"kty": "EC", "crv": "P-521", "alg": "ES512"},
                {"kty": "EC", "crv": "P-256", "alg": "ES256"},
            ],
            "mandate_evaluation": {
                "evaluated_at": 1792483200,
                "mandate_exp": 1792483260,
                "checkout_status": "complete_in_progress",
                "aborted_after_admission_due_to_ttl": False,
            },
            "gift_checkout": {
                "gift": {"recipient_required": True},
                "recipient_selected_on_business": False,
                "checkout_status": "requires_escalation",
                "continue_url": "https://merchant.example.com/gift/recipient",
                "complete_request_body": {"payment": {"id": "pay_1"}},
            },
        }
        res = validate_ucp_conditional_writes_p521_mandate_ttl_and_gift_guard(payload)
        self.assertTrue(res["allowed"], res["violations"])

    def test_ucp_conditional_writes_p521_mandate_ttl_and_gift_violations(self) -> None:
        payload = {
            "conditional_write": {
                "is_state_changing": True,
                "if_match_header": '"etag-v1"',
                "current_etag": '"etag-v2"',
                "idempotency_key_reused": True,
                "payload_digest_changed": True,
            },
            "catalog_operation": {
                "request_cannot_be_served": True,
                "response": {"products": []},
            },
            "signing_keys": [
                {"kty": "EC", "crv": "P-521", "alg": "ES256"},
            ],
            "mandate_evaluation": {
                "evaluated_at": 1792483300,
                "mandate_exp": 1792483260,
                "checkout_status": "complete_in_progress",
                "aborted_after_admission_due_to_ttl": False,
            },
            "gift_checkout": {
                "gift": {"recipient_required": True, "recipient_email": "friend@example.com"},
                "recipient_selected_on_business": False,
                "checkout_status": "ready_for_complete",
                "continue_url": "",
                "complete_request_body": {"gift": {"recipient_required": True}},
            },
        }
        res = validate_ucp_conditional_writes_p521_mandate_ttl_and_gift_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("UCP_628_IF_MATCH_ETAG_MISMATCH_412", res["violations"])
        self.assertIn("UCP_628_IDEMPOTENCY_CONFLICT_409", res["violations"])
        self.assertIn("UCP_628_CATALOG_MISSING_STANDARD_ERROR_ENVELOPE", res["violations"])
        self.assertIn("UCP_625_CURVE_ALG_MISMATCH:P-521!=ES256", res["violations"])
        self.assertIn("UCP_540_EXPIRED_AT_ADMISSION_MUST_TERMINATE_CANCELED", res["violations"])
        self.assertIn("UCP_508_WIRE_RECIPIENT_PII_OR_HANDLE_FORBIDDEN:recipient_email", res["violations"])
        self.assertIn("UCP_508_MISSING_RECIPIENT_ESCALATION_REQUIRED", res["violations"])
        self.assertIn("UCP_508_GIFT_FIELD_FORBIDDEN_IN_COMPLETE_REQUEST", res["violations"])

    def test_acp_affiliate_attribution_merchant_3ds_and_hotel_hydration_compliant(self) -> None:
        payload = {
            "affiliate_attribution_context": {
                "endpoint_phase": "create",
                "request_affiliate_attribution": {
                    "touchpoint": "first",
                    "token": "aff_tok_opaque_991",
                    "metadata": {"campaign_id": "autumn_2026"},
                },
                "response_body": {"id": "cs_123", "status": "in_progress"},
                "idempotency_key_reused": False,
                "attribution_payload_changed": False,
                "http_status": 200,
            },
            "merchant_3ds": {
                "pending_action": "3ds_challenge",
                "acs_url": "https://acs.issuer.example/challenge",
                "encoded_creq": "eyJ0aHJlZURTU2VydmVyVHJhbnNJRCI6IjEyMyJ9",
                "finalize_requested": True,
                "cres": "eyJ0cmFuc1N0YXR1cyI6IlkifQ==",
            },
            "hotel_checkout": {
                "used_static_catalog_price_only": False,
                "quote_token": "qt_hotel_hydrated_01",
                "quote_expires_at": 1792489000,
                "checkout_now": 1792483200,
                "cancellation_policy_snapshot_preserved": True,
            },
        }
        res = validate_acp_affiliate_attribution_merchant_3ds_and_hotel_hydration_guard(payload)
        self.assertTrue(res["allowed"], res["violations"])

    def test_acp_affiliate_attribution_merchant_3ds_and_hotel_hydration_violations(self) -> None:
        payload = {
            "affiliate_attribution_context": {
                "endpoint_phase": "complete",
                "request_affiliate_attribution": {
                    "touchpoint": "first",
                    "token": "aff_tok_opaque_991",
                    "metadata": {"email": "buyer@example.com"},
                },
                "response_body": {
                    "id": "cs_123",
                    "affiliate_attribution": {"token": "aff_tok_opaque_991"},
                },
                "idempotency_key_reused": True,
                "attribution_payload_changed": True,
                "http_status": 200,
            },
            "merchant_3ds": {
                "pending_action": "3ds_challenge",
                "acs_url": "https://acs.issuer.example/challenge",
                "encoded_creq": "eyJ0aHJlZURTU2VydmVyVHJhbnNJRCI6IjEyMyJ9",
                "finalize_requested": True,
                "cres": "",
            },
            "hotel_checkout": {
                "used_static_catalog_price_only": True,
                "quote_token": "",
                "quote_expires_at": 1792480000,
                "checkout_now": 1792483200,
                "cancellation_policy_snapshot_preserved": False,
            },
        }
        res = validate_acp_affiliate_attribution_merchant_3ds_and_hotel_hydration_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("ACP_57_COMPLETE_REQUIRES_LAST_TOUCHPOINT", res["violations"])
        self.assertIn("ACP_57_AFFILIATE_PII_LEAK_FORBIDDEN:email", res["violations"])
        self.assertIn("ACP_57_AFFILIATE_ATTRIBUTION_ECHOED_IN_RESPONSE", res["violations"])
        self.assertIn("ACP_57_IDEMPOTENCY_PAYLOAD_CONFLICT_409_REQUIRED", res["violations"])
        self.assertIn("ACP_66_3DS_CHALLENGE_FINALIZE_WITHOUT_CRES", res["violations"])
        self.assertIn("ACP_45_STATIC_CATALOG_PRICE_USED_WITHOUT_HYDRATION_QUOTE", res["violations"])

    def test_ap2_open_mandate_hash_entropy_and_x402_fact_attestation_compliant(self) -> None:
        claims = {"aud": "https://merchant.example", "budget": {"currency": "USD", "max": 12500}, "nonce": "n_99a8b7c6"}
        digest = compute_rfc8785_jcs_sha256({"nonce": "n_99a8b7c6", "budget": {"max": 12500, "currency": "USD"}, "aud": "https://merchant.example"})
        payload = {
            "open_mandate_hash_check": {
                "hashed_jws_compact_envelope": False,
                "unsigned_claims": claims,
                "open_mandate_hash": digest,
            },
            "checkout_jwt_entropy": {
                "signature_alg": "EdDSA",
                "payload_entropy_bits": 128,
                "has_high_entropy_nonce_claim": True,
            },
            "fact_attestation": {
                "attester_signer": "0xAttesterIndependent1111111111111111111111",
                "pay_to": "0xMerchantPayTo2222222222222222222222222222",
                "observations": [
                    {"field": "domain_age_days", "value": 1420, "method": "rdap_whois_lookup_v1"},
                    {"field": "observed_price_minor", "value": 12500, "method": "headless_dom_jsonld_v1"},
                ],
            },
            "x402_facilitator_routing": {
                "network": "eip155:8453",
                "facilitator_url": "https://api.cdp.coinbase.com/platform/v2/x402",
            },
        }
        res = validate_ap2_open_mandate_hash_entropy_and_x402_fact_attestation_guard(payload)
        self.assertTrue(res["allowed"], res["violations"])

    def test_ap2_open_mandate_hash_entropy_and_x402_fact_attestation_violations(self) -> None:
        payload = {
            "open_mandate_hash_check": {
                "hashed_jws_compact_envelope": True,
                "unsigned_claims": {"aud": "https://merchant.example"},
                "open_mandate_hash": "deadbeef",
            },
            "checkout_jwt_entropy": {
                "signature_alg": "EdDSA",
                "payload_entropy_bits": 32,
                "has_high_entropy_nonce_claim": False,
            },
            "fact_attestation": {
                "attester_signer": "0xSameAddress333333333333333333333333333333",
                "pay_to": "0xSameAddress333333333333333333333333333333",
                "judgment": "legit",
                "observations": [{"field": "domain_age_days", "value": 2, "method": ""}],
            },
            "x402_facilitator_routing": {
                "network": "eip155:8453",
                "facilitator_url": "https://x402.org/facilitator",
            },
        }
        res = validate_ap2_open_mandate_hash_entropy_and_x402_fact_attestation_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("AP2_279_JWS_ENVELOPE_HASHED_INSTEAD_OF_UNSIGNED_CLAIMS", res["violations"])
        self.assertIn("AP2_279_OPEN_MANDATE_HASH_MISMATCH", res["violations"])
        self.assertIn("AP2_278_LOW_ENTROPY_CHECKOUT_JWT_PAYLOAD", res["violations"])
        self.assertIn("X402_225_SELF_ASSERTED_PAYTO_FACT_ATTESTATION_REJECTED", res["violations"])
        self.assertIn("X402_225_JUDGMENT_LABEL_FORBIDDEN_FACTS_ONLY", res["violations"])
        self.assertIn("X402_225_OBSERVATION_MISSING_DISCLOSED_METHOD", res["violations"])
        self.assertIn("X402_206_TESTNET_PUBLIC_FACILITATOR_ON_MAINNET_500", res["violations"])

    def test_tau2_write_critic_close_account_reason_pydantic_coercion_and_solo_gt_compliant(self) -> None:
        payload = {
            "write_critic_gate": {
                "is_mutating_tool": True,
                "verification_completed": True,
                "critic_approved": True,
                "nested_json_arg_comparison": {
                    "gold_arguments_json": '{"account_id":"acc_1","amount":50}',
                    "pred_arguments_json": '{\n  "amount": 50,\n  "account_id": "acc_1"\n}',
                    "used_raw_string_compare": False,
                },
            },
            "close_bank_account_call": {
                "reason": "customer_request",
            },
            "tool_kwarg_validation": {
                "expected_int_arg": 2.0,
                "coerced_via_pydantic_schema": True,
            },
            "solo_mode_regrading": {
                "agent_implementation": "llm_agent_solo_gt",
                "user_implementation": "dummy_user",
                "detected_is_solo": True,
            },
        }
        res = validate_tau2_write_critic_close_account_reason_pydantic_coercion_and_solo_gt_guard(payload)
        self.assertTrue(res["allowed"], res["violations"])

    def test_tau2_write_critic_close_account_reason_pydantic_coercion_and_solo_gt_violations(self) -> None:
        payload = {
            "write_critic_gate": {
                "is_mutating_tool": True,
                "verification_completed": False,
                "critic_approved": False,
                "nested_json_arg_comparison": {
                    "gold_arguments_json": '{"account_id":"acc_1","amount":50}',
                    "pred_arguments_json": '{"amount":50,"account_id":"acc_1"}',
                    "used_raw_string_compare": True,
                },
            },
            "close_bank_account_call": {
                "reason": "Customer requested closure after transferring full balance",
            },
            "tool_kwarg_validation": {
                "expected_int_arg": 2.5,
                "coerced_via_pydantic_schema": False,
            },
            "solo_mode_regrading": {
                "agent_implementation": "llm_agent_solo_gt",
                "user_implementation": "dummy_user",
                "detected_is_solo": False,
            },
        }
        res = validate_tau2_write_critic_close_account_reason_pydantic_coercion_and_solo_gt_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("TAU2_513_UNVERIFIED_MUTATING_TOOL_BLOCKED_BY_CRITIC", res["violations"])
        self.assertIn("TAU2_513_RAW_STRING_COMPARISON_ON_NESTED_JSON_ARGS", res["violations"])
        self.assertIn(
            "TAU2_484_INVALID_FREE_TEXT_CLOSURE_REASON:Customer requested closure after transferring full balance",
            res["violations"],
        )
        self.assertIn("TAU2_516_BYPASSED_PYDANTIC_KWARG_COERCION", res["violations"])
        self.assertIn("TAU2_516_NON_INTEGRAL_FLOAT_FOR_INT_PARAM", res["violations"])
        self.assertIn("TAU2_508_SOLO_GT_DETECTION_MISMATCH", res["violations"])


if __name__ == "__main__":
    unittest.main()
