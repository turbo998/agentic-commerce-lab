"""Unit tests for Stage 78 deterministic guard module."""

from __future__ import annotations

import unittest

from lab.ucp_sale_basis_loyalty_actions_acp_delegated_auth_handlers_ap2_budget_pii_tau2_gptlive_guard import (
    verify_acp_delegated_authentication_and_payment_handlers_guard,
    verify_ap2_cross_merchant_budget_authority_and_trustboost_pii_guard,
    verify_tau2_gptlive_provider_transcription_retry_and_banking_leak_guard,
    verify_ucp_sale_basis_steps_loyalty_actions_policies_and_elision_guard,
)


class TestStage78Guard(unittest.TestCase):
    def test_ucp_sale_basis_steps_loyalty_actions_policies_and_elision_valid(self) -> None:
        payload = {
            "line_items": [
                {
                    "id": "li_fasteners",
                    "item": {
                        "id": "var_fasteners",
                        "price": 1299,
                        "quantity_unit": {"unit": "KGM", "scale": 2, "display_text": "kg"},
                        "unit_price": {
                            "measure": {"value": 100, "unit": "KGM", "currency": "USD"},
                            "reference": {"value": 1, "unit": "KGM", "currency": "USD"},
                        },
                    },
                    "quantity": 150,
                    "authoritative_subtotal": 1949,
                }
            ],
            "actions": {"verify_age": [{"type": "redirect", "url": "https://verify.example/age"}]},
            "policies": [
                {
                    "type": "dev.ucp.shopping.policy.return",
                    "applies_to": ["$.products[?@.tags[?@=='electronics']]"],
                }
            ],
            "loyalty": {
                "earning_forecast": {
                    "amount": 30,
                    "breakdown": [{"amount": 10}, {"amount": 20}],
                },
                "discounts": [{"amount": 1000, "expressed_in_major_units": False}],
            },
            "request_envelope": {
                "op": "update_checkout",
                "body": {"line_items": [{"id": "li_fasteners", "quantity": 150}]},
            },
            "event_feed": {
                "url": "https://store.example.com/ucp/events",
                "event_types": ["dev.ucp.order.shipped"],
                "transports": ["sse", "poll"],
            },
            "array_elision_check": {"recorded_pre_strip_index": False},
            "mcp_idempotency": {
                "key_reused_with_different_payload": True,
                "jsonrpc_error_code": -32000,
            },
        }
        res = verify_ucp_sale_basis_steps_loyalty_actions_policies_and_elision_guard(payload)
        self.assertTrue(res["allowed"])
        self.assertEqual(res["violations"], [])

    def test_ucp_sale_basis_steps_loyalty_actions_policies_and_elision_violations(self) -> None:
        payload = {
            "line_items": [
                {
                    "id": "li_bad",
                    "item": {
                        "id": "var_bad",
                        "price": 1299,
                        "quantity_unit": {"unit": "C62", "scale": 2, "display_text": "each"},
                        "unit_price": {
                            "measure": {"value": 0, "unit": "KGM", "currency": "USD"},
                            "reference": {"value": 1, "unit": "LTR", "currency": "EUR"},
                        },
                    },
                    "quantity": 150,
                    "authoritative_subtotal": 1900,
                }
            ],
            "actions": {},
            "policies": [
                {"type": "dev.ucp.shopping.policy.return", "applies_to": []},
                {
                    "type": "dev.ucp.shopping.policy.return",
                    "applies_to": ["$.products[?@.category=='electronics']"],
                },
            ],
            "loyalty": {
                "earning_forecast": {
                    "amount": 50,
                    "breakdown": [{"amount": 10}, {"amount": 20}],
                },
                "discounts": [{"amount": 10, "expressed_in_major_units": True}],
            },
            "request_envelope": {
                "op": "update_checkout",
                "body": {"id": "chk_1", "status": "ready_for_complete"},
            },
            "event_feed": {
                "url": "http://insecure.example.com/events",
                "event_types": [],
                "transports": ["websocket"],
            },
            "array_elision_check": {"recorded_pre_strip_index": True},
            "mcp_idempotency": {
                "key_reused_with_different_payload": True,
                "jsonrpc_error_code": -32603,
            },
        }
        res = verify_ucp_sale_basis_steps_loyalty_actions_policies_and_elision_guard(payload)
        self.assertFalse(res["allowed"])
        for expected in (
            "UCP_QUANTITY_UNIT_C62_NONZERO_SCALE_FORBIDDEN:0",
            "UCP_VARIABLE_QUANTITY_LINE_TOTAL_ROUNDING_MISMATCH:0:1900!=1949",
            "UCP_UNIT_PRICE_COMPARATOR_MISMATCH:0",
            "UCP_EMPTY_ACTIONS_MAP_FORBIDDEN",
            "UCP_POLICY_EMPTY_APPLIES_TO_FORBIDDEN:0",
            "UCP_POLICY_INVALID_PRODUCT_CATEGORY_SCALAR_PATH:1",
            "UCP_LOYALTY_EARNING_BREAKDOWN_SUM_MISMATCH:30!=50",
            "UCP_LOYALTY_MAJOR_UNIT_AMOUNT_FORBIDDEN",
            "UCP_REQUEST_BODY_SERVER_ASSIGNED_FIELD_LEAK",
            "UCP_REQUEST_BODY_DEPRECATED_ID_FORBIDDEN:update_checkout",
            "UCP_EVENT_FEED_CONTRACT_INVALID",
            "UCP_ARRAY_ELISION_PRE_STRIP_INDEX_MISMATCH",
            "UCP_MCP_IDEMPOTENCY_CONFLICT_CODE_MISMATCH",
        ):
            self.assertIn(expected, res["violations"])

    def test_acp_delegated_authentication_and_payment_handlers_valid(self) -> None:
        payload = {
            "delegated_authentication": {
                "implemented_endpoints": ["create", "authenticate", "retrieve"],
                "authentication_session_id": "auth_sess_01",
                "create_action_type": "fingerprint",
                "fingerprint_completed_before_authenticate": True,
                "authenticate_action_type": "challenge",
                "challenge_completed_before_retrieve": True,
                "retrieve_called_before_checkout_complete": True,
                "channel_provided_in_create_or_authenticate": True,
                "idempotency_conflict_detected": True,
                "http_status": 409,
            },
            "authentication_metadata": {"acquirer_bin": "444444", "acquirer_mid": "mid_123"},
            "capabilities": {
                "payment": {
                    "handlers": [
                        {
                            "id": "card_tokenized",
                            "name": "dev.acp.tokenized.card",
                            "psp": "stripe",
                            "requires_delegate_payment": True,
                            "requires_pci_compliance": False,
                            "config": {"merchant_id": "acct_1234567890"},
                        }
                    ]
                }
            },
            "delegate_payment_request": {
                "handler_id": "card_tokenized",
                "constraints": {"merchant_id": "acct_1234567890", "max_amount": 10000},
            },
            "discounts": {
                "applied": [
                    {"id": "disc_1", "amount": 500, "allocations": [{"amount": 300}, {"amount": 200}]}
                ],
                "rejected": [{"code": "WINTER50", "reason_code": "minimum_not_met"}],
            },
        }
        res = verify_acp_delegated_authentication_and_payment_handlers_guard(payload)
        self.assertTrue(res["allowed"])
        self.assertEqual(res["violations"], [])

    def test_acp_delegated_authentication_and_payment_handlers_violations(self) -> None:
        payload = {
            "delegated_authentication": {
                "implemented_endpoints": ["create", "authenticate"],
                "authentication_session_id": "",
                "create_action_type": "fingerprint",
                "fingerprint_completed_before_authenticate": False,
                "authenticate_action_type": "challenge",
                "challenge_completed_before_retrieve": False,
                "retrieve_called_before_checkout_complete": False,
                "channel_provided_in_create_or_authenticate": False,
                "idempotency_conflict_detected": True,
                "http_status": 200,
            },
            "authentication_metadata": {"channel": "browser"},
            "payment_methods": ["card"],
            "capabilities": {
                "payment": {
                    "handlers": [
                        {
                            "id": "card_tokenized",
                            "name": "invalid_name",
                            "psp": "stripe",
                            "requires_delegate_payment": True,
                            "requires_pci_compliance": False,
                            "config": {"merchant_id": "acct_1234567890"},
                        }
                    ]
                }
            },
            "delegate_payment_request": {
                "handler_id": "card_tokenized",
                "constraints": {"merchant_id": "acct_wrong"},
            },
            "discounts": {
                "applied": [{"id": "disc_1", "amount": 500, "allocations": [{"amount": 100}]}],
                "rejected": [{"code": "WINTER50"}],
            },
        }
        res = verify_acp_delegated_authentication_and_payment_handlers_guard(payload)
        self.assertFalse(res["allowed"])
        for expected in (
            "ACP_DELEGATED_AUTH_ENDPOINTS_INCOMPLETE",
            "ACP_DELEGATED_AUTH_SESSION_ID_REQUIRED",
            "ACP_DELEGATED_AUTH_FINGERPRINT_STEP_SKIPPED",
            "ACP_DELEGATED_AUTH_CHALLENGE_STEP_SKIPPED",
            "ACP_DELEGATED_AUTH_RETRIEVE_STEP_SKIPPED",
            "ACP_DELEGATED_AUTH_CHANNEL_DATA_MISSING",
            "ACP_DELEGATED_AUTH_IDEMPOTENCY_409_REQUIRED",
            "ACP_AUTH_METADATA_DEPRECATED_CHANNEL_FIELD_FORBIDDEN",
            "ACP_LEGACY_PAYMENT_METHODS_STRING_ARRAY_FORBIDDEN",
            "ACP_PAYMENT_HANDLER_REVERSE_DNS_NAME_INVALID:0",
            "ACP_HANDLER_DELEGATE_MERCHANT_ID_MISMATCH:acct_wrong!=acct_1234567890",
            "ACP_DISCOUNT_ALLOCATION_SUM_MISMATCH:0",
            "ACP_DISCOUNT_REJECTION_REASON_CODE_REQUIRED:0",
        ):
            self.assertIn(expected, res["violations"])

    def test_ap2_cross_merchant_budget_and_trustboost_pii_valid(self) -> None:
        payload = {
            "cross_merchant_budget": {
                "isolated_per_merchant_context": False,
                "authority_verbs": ["authorize", "commit", "refund", "query"],
                "total_budget_minor": 10000,
                "committed_minor": 3000,
                "active_holds_minor": 3000,
                "requested_authorize_minor": 4000,
            },
            "trustboost_pii": {
                "contains_pii": True,
                "sanitized_before_llm": True,
                "x402_sanitization_paid": True,
                "solana_anchor_tx": "5xSolanaAnchorTxSig1111111111111111",
                "anchor_proof_verified": True,
            },
            "mandate_verifier": {
                "recomputed_checkout_hash": "sha256:9f86d081884c7d659a2feaa0c55ad015",
                "mandate_checkout_hash": "sha256:9f86d081884c7d659a2feaa0c55ad015",
            },
        }
        res = verify_ap2_cross_merchant_budget_authority_and_trustboost_pii_guard(payload)
        self.assertTrue(res["allowed"])
        self.assertEqual(res["violations"], [])

    def test_ap2_cross_merchant_budget_and_trustboost_pii_violations(self) -> None:
        payload = {
            "cross_merchant_budget": {
                "isolated_per_merchant_context": True,
                "authority_verbs": ["authorize", "commit"],
                "total_budget_minor": 10000,
                "committed_minor": 6000,
                "active_holds_minor": 0,
                "requested_authorize_minor": 6000,
            },
            "trustboost_pii": {
                "contains_pii": True,
                "sanitized_before_llm": False,
                "x402_sanitization_paid": False,
                "solana_anchor_tx": "",
                "anchor_proof_verified": False,
            },
            "mandate_verifier": {
                "recomputed_checkout_hash": "sha256:aaa",
                "mandate_checkout_hash": "sha256:bbb",
            },
        }
        res = verify_ap2_cross_merchant_budget_authority_and_trustboost_pii_guard(payload)
        self.assertFalse(res["allowed"])
        for expected in (
            "AP2_ISOLATED_MERCHANT_BUDGET_CONTEXT_RACE",
            "AP2_BUDGET_AUTHORITY_VERBS_INCOMPLETE",
            "AP2_CROSS_MERCHANT_BUDGET_AUTHORIZE_EXCEEDED:12000>10000",
            "AP2_RAW_PII_EXPOSED_TO_LLM_BEFORE_SANITIZATION",
            "AP2_TRUSTBOOST_X402_PAYMENT_REQUIRED_402",
            "AP2_TRUSTBOOST_SOLANA_ANCHOR_PROOF_UNVERIFIED",
            "AP2_VERIFIER_CHECKOUT_HASH_OBLIGATION_UNMET",
        ):
            self.assertIn(expected, res["violations"])

    def test_tau2_gptlive_transcription_and_banking_leak_valid(self) -> None:
        payload = {
            "gptlive_session": {
                "uses_responses_delegation": True,
                "sent_response_create": False,
                "joined_call_id_via_output_item_added": True,
                "rms_hysteresis_silence_gate_enabled": True,
                "live_suite_executed": True,
                "gptlive_test_enabled_env": True,
            },
            "transcription_event": {
                "transient_error": True,
                "retried": True,
                "returned_empty_transcript": False,
            },
            "viewer_render": {
                "max_tool_result_chars": 500,
                "full_tool_results": False,
                "rendered_tool_result_chars": 500,
            },
            "reward_gate": {
                "active_reward_basis": ["DB", "COMMUNICATE"],
                "criteria_by_basis": {
                    "DB": ["account_balance == 100"],
                    "COMMUNICATE": ["confirm refund amount $14.50"],
                },
            },
            "banking_knowledge": {
                "rejected_numeric_string_arg": False,
                "task_074_light_blue_gold_credit": 14.50,
                "db_transaction_descriptions": [
                    "NON-RHO ATM FEE",
                    "FOREIGN ATM FEE - 1% (MIN $1.50)",
                ],
                "kb_day_count_has_currency_sign": False,
            },
        }
        res = verify_tau2_gptlive_provider_transcription_retry_and_banking_leak_guard(payload)
        self.assertTrue(res["allowed"])
        self.assertEqual(res["violations"], [])

    def test_tau2_gptlive_transcription_and_banking_leak_violations(self) -> None:
        payload = {
            "gptlive_session": {
                "uses_responses_delegation": False,
                "sent_response_create": True,
                "joined_call_id_via_output_item_added": False,
                "rms_hysteresis_silence_gate_enabled": False,
                "live_suite_executed": True,
                "gptlive_test_enabled_env": False,
            },
            "transcription_event": {
                "transient_error": True,
                "retried": False,
                "returned_empty_transcript": True,
            },
            "viewer_render": {
                "max_tool_result_chars": 500,
                "full_tool_results": False,
                "rendered_tool_result_chars": 12000,
            },
            "reward_gate": {
                "active_reward_basis": ["COMMUNICATE", "NL_ASSERTION"],
                "criteria_by_basis": {"COMMUNICATE": [], "NL_ASSERTION": []},
            },
            "banking_knowledge": {
                "rejected_numeric_string_arg": True,
                "task_074_light_blue_gold_credit": 8.00,
                "db_transaction_descriptions": [
                    "NON-RHO ATM FEE (SHOULD BE FREE - 1ST OF 2)",
                    "NON-RHO ATM FEE - AFTER FREE ALLOWANCE",
                ],
                "kb_day_count_has_currency_sign": True,
            },
        }
        res = verify_tau2_gptlive_provider_transcription_retry_and_banking_leak_guard(payload)
        self.assertFalse(res["allowed"])
        for expected in (
            "TAU2_GPTLIVE_RESPONSES_DELEGATION_PROTOCOL_VIOLATION",
            "TAU2_GPTLIVE_ITEM_ID_JOIN_REQUIRED",
            "TAU2_GPTLIVE_RMS_SILENCE_GATE_REQUIRED",
            "TAU2_GPTLIVE_ALPHA_ENV_GATE_MISSING",
            "TAU2_TRANSIENT_TRANSCRIPTION_SWALLOWED_AS_EMPTY",
            "TAU2_VIEW_TOOL_RESULT_NOT_TRUNCATED:12000>500",
            "TAU2_EMPTY_ACTIVE_REWARD_BASIS_GATE:COMMUNICATE",
            "TAU2_EMPTY_ACTIVE_REWARD_BASIS_GATE:NL_ASSERTION",
            "TAU2_BANKING_NUMERIC_STRING_ARG_REJECTED",
            "TAU2_BANKING_T074_LIGHT_BLUE_ATM_FEE_UNDER_REFUND",
            "TAU2_BANKING_DB_ANSWER_KEY_ANNOTATION_LEAK:0",
            "TAU2_BANKING_DB_ANSWER_KEY_ANNOTATION_LEAK:1",
            "TAU2_BANKING_KB_DAY_COUNT_STRAY_CURRENCY_SIGN",
        ):
            self.assertIn(expected, res["violations"])


if __name__ == "__main__":
    unittest.main()
