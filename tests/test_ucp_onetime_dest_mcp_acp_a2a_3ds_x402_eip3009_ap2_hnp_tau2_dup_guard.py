"""Unit tests for Stage 84 guardrails."""

from __future__ import annotations

import unittest

from lab.ucp_onetime_dest_mcp_acp_a2a_3ds_x402_eip3009_ap2_hnp_tau2_dup_guard import (
    validate_acp_a2a_push_payment_and_3ds_outcome_guard,
    validate_tau2_duplicate_posting_seq_and_multicard_fraud_guard,
    validate_ucp_onetime_destination_and_mcp_binding_guard,
    validate_x402_eip3009_error_and_ap2_hnp_session_guard,
)


class Stage84GuardTests(unittest.TestCase):
    def test_ucp_onetime_destination_and_mcp_binding_pass(self) -> None:
        res = validate_ucp_onetime_destination_and_mcp_binding_guard(
            {
                "request_shipping_destination": {
                    "id": "dest_gift_1",
                    "postal_code": "94107",
                    "one_time_use": True,
                },
                "response_shipping_destination": {
                    "id": "dest_gift_1",
                    "postal_code": "94107",
                    "one_time_use": True,
                },
                "saved_to_address_book": False,
                "used_for_profile_enrichment": False,
                "buyer_consent": {"marketing": True},
                "mcp_binding_doc": {
                    "uses_schema_fields_macro": True,
                    "duplicate_per_op_meta": False,
                    "has_protocol_errors_section": True,
                },
            }
        )
        self.assertTrue(res["allowed"])
        self.assertEqual(res["decision_code"], "UCP_ONETIME_DEST_AND_MCP_OK")

    def test_ucp_onetime_destination_and_mcp_binding_rejects_retention_and_drift(self) -> None:
        res = validate_ucp_onetime_destination_and_mcp_binding_guard(
            {
                "request_shipping_destination": {"id": "dest_gift_1", "one_time_use": True},
                "response_shipping_destination": {"id": "dest_gift_1"},
                "saved_to_address_book": True,
                "used_for_profile_enrichment": True,
                "mcp_binding_doc": {
                    "uses_schema_fields_macro": False,
                    "duplicate_per_op_meta": True,
                    "has_protocol_errors_section": False,
                },
            }
        )
        self.assertFalse(res["allowed"])
        self.assertGreaterEqual(len(res["violations"]), 5)

    def test_acp_a2a_push_payment_and_3ds_outcome_pass(self) -> None:
        res_a2a = validate_acp_a2a_push_payment_and_3ds_outcome_guard(
            {
                "flow_type": "account_to_account",
                "handler": {
                    "id": "a2a_bank_transfer",
                    "name": "dev.acp.account_to_account",
                    "requires_delegate_payment": False,
                    "requires_pci_compliance": False,
                },
                "payment_data": {"handler_id": "a2a_bank_transfer"},
                "checkout_session_status": "complete_in_progress",
                "allow_fulfillment_release": False,
                "order": {
                    "id": "ord_a2a_123",
                    "status": "created",
                    "bank_instructions": {
                        "account_address": "DE89370400440532013000",
                        "bank_name": "Example Bank",
                        "reference": "ORDER-A2A-123456",
                        "expires_at": "2026-03-01T00:00:00Z",
                    },
                    "bank_transfer_confirmation": {"status": "pending"},
                },
            }
        )
        self.assertTrue(res_a2a["allowed"])

        res_3ds = validate_acp_a2a_push_payment_and_3ds_outcome_guard(
            {
                "flow_type": "three_ds",
                "requires_3ds": True,
                "allow_settlement": True,
                "authentication_result": {
                    "outcome": "attempt_acknowledged",
                    "outcome_details": {
                        "three_ds_cryptogram": "XYZ123FRICTIONLESS456789==",
                        "electronic_commerce_indicator": "06",
                        "transaction_id": "dsTransId_frictionless_456",
                        "version": "2.2.0",
                    },
                },
            }
        )
        self.assertTrue(res_3ds["allowed"])

    def test_acp_a2a_and_3ds_rejects_premature_release_and_denied_settlement(self) -> None:
        res_a2a = validate_acp_a2a_push_payment_and_3ds_outcome_guard(
            {
                "flow_type": "account_to_account",
                "handler": {
                    "id": "a2a_bank_transfer",
                    "name": "dev.acp.account_to_account",
                    "requires_delegate_payment": True,
                    "requires_pci_compliance": False,
                },
                "payment_data": {"handler_id": "a2a_bank_transfer", "token": "spt_bad"},
                "checkout_session_status": "completed",
                "allow_fulfillment_release": True,
                "order": {
                    "id": "ord_a2a_123",
                    "status": "created",
                    "bank_instructions": {"account_address": "", "bank_name": "Bank", "reference": "", "expires_at": ""},
                    "bank_transfer_confirmation": {"status": "pending"},
                },
            }
        )
        self.assertFalse(res_a2a["allowed"])

        res_3ds = validate_acp_a2a_push_payment_and_3ds_outcome_guard(
            {
                "flow_type": "three_ds",
                "requires_3ds": True,
                "allow_settlement": True,
                "authentication_result": {
                    "outcome": "denied",
                    "outcome_details": {
                        "transaction_id": "dsTransId_denied_789",
                        "version": "2.2.0",
                    },
                },
            }
        )
        self.assertFalse(res_3ds["allowed"])

    def test_x402_eip3009_and_ap2_hnp_session_pass(self) -> None:
        res = validate_x402_eip3009_error_and_ap2_hnp_session_guard(
            {
                "x402_eip3009": {
                    "phase": "settle_revert",
                    "revert_message": "ERC20: authorization is used (AuthorizationAlreadyUsed)",
                    "reported_error_code": "ErrNonceAlreadyUsed",
                },
                "ap2_hnp_mandate": {
                    "user_cart_confirmation_required": False,
                    "agent_did": "did:web:shopper.example.com",
                    "now_iso": "2026-10-20T12:00:00Z",
                    "session_authorization": {
                        "status": "active",
                        "expires_at": "2026-10-21T12:00:00Z",
                        "session_public_key": "z6MkpTHR8VNsBxYAAWHut2Geadd9jSwuBV8xRoAnwWsdvktH",
                    },
                    "spending_rule_set": {
                        "evaluation_mode": "all",
                        "rules": [
                            {
                                "rule_id": "freq_1",
                                "rule_type": "frequency_constraint",
                                "priority": 1,
                                "enabled": True,
                                "max_transactions": 3,
                                "merchant_specific": True,
                            },
                            {
                                "rule_id": "cat_1",
                                "rule_type": "category_constraint",
                                "priority": 2,
                                "enabled": True,
                                "constraint_type": "allow",
                                "categories": ["groceries", "electronics"],
                            },
                        ],
                    },
                    "transaction_context": {
                        "merchant_transaction_count_in_window": 1,
                        "item_categories": ["electronics"],
                    },
                },
            }
        )
        self.assertTrue(res["allowed"])

    def test_x402_eip3009_and_ap2_hnp_session_rejects_wrong_error_and_rule_breach(self) -> None:
        res = validate_x402_eip3009_error_and_ap2_hnp_session_guard(
            {
                "x402_eip3009": {
                    "phase": "verify_simulation_rpc_error",
                    "reported_error_code": "ErrInvalidPayload",
                },
                "ap2_hnp_mandate": {
                    "user_cart_confirmation_required": False,
                    "agent_did": "invalid_did",
                    "now_iso": "2026-10-20T12:00:00Z",
                    "session_authorization": {
                        "status": "expired",
                        "expires_at": "2026-10-19T12:00:00Z",
                        "session_public_key": "",
                    },
                    "spending_rule_set": {
                        "evaluation_mode": "all",
                        "rules": [
                            {
                                "rule_id": "freq_1",
                                "rule_type": "frequency_constraint",
                                "priority": 1,
                                "enabled": True,
                                "max_transactions": 2,
                                "merchant_specific": False,
                            }
                        ],
                    },
                    "transaction_context": {
                        "total_transaction_count_in_window": 2,
                    },
                },
            }
        )
        self.assertFalse(res["allowed"])
        self.assertGreaterEqual(len(res["violations"]), 4)

    def test_tau2_duplicate_posting_seq_and_multicard_fraud_pass(self) -> None:
        res = validate_tau2_duplicate_posting_seq_and_multicard_fraud_guard(
            {
                "duplicate_transactions": [
                    {
                        "transaction_id": "btxn_c843f1209a3e",
                        "date": "2026-02-07",
                        "description": "AUSTIN COFFEE ROASTERS",
                        "amount": -67.25,
                        "status": "posted",
                        "posting_sequence": 2,
                    },
                    {
                        "transaction_id": "btxn_d937eaa1d21d",
                        "date": "2026-02-07",
                        "description": "AUSTIN COFFEE ROASTERS",
                        "amount": -67.25,
                        "status": "posted",
                        "posting_sequence": 1,
                    },
                ],
                "disputed_transaction_id": "btxn_d937eaa1d21d",
                "filed_disputes": [
                    {
                        "dispute_id": "dsp_blue_1",
                        "card_id": "dbc_blue_001",
                        "category": "card_present_fraud",
                        "card_action": "close_and_reissue",
                    },
                    {
                        "dispute_id": "dsp_gff_2",
                        "card_id": "dbc_mc47a2b9e1_gff",
                        "category": "card_not_present_fraud",
                        "card_action": "close_and_reissue",
                    },
                ],
                "closed_debit_cards": [
                    {"card_id": "dbc_blue_001", "reason": "fraud_suspected"},
                    {"card_id": "dbc_mc47a2b9e1_gff", "reason": "fraud_suspected"},
                ],
                "final_card_statuses": {
                    "dbc_blue_001": "CLOSED",
                    "dbc_mc47a2b9e1_gff": "CLOSED",
                },
            }
        )
        self.assertTrue(res["allowed"])

    def test_tau2_duplicate_posting_seq_and_multicard_fraud_rejects_wrong_seq_and_unclosed_gff(self) -> None:
        res = validate_tau2_duplicate_posting_seq_and_multicard_fraud_guard(
            {
                "duplicate_transactions": [
                    {"transaction_id": "btxn_c843f1209a3e", "posting_sequence": 2},
                    {"transaction_id": "btxn_d937eaa1d21d", "posting_sequence": 1},
                ],
                "disputed_transaction_id": "btxn_c843f1209a3e",
                "filed_disputes": [
                    {
                        "dispute_id": "dsp_blue_1",
                        "card_id": "dbc_blue_001",
                        "category": "card_present_fraud",
                        "card_action": "close_and_reissue",
                    },
                    {
                        "dispute_id": "dsp_gff_2",
                        "card_id": "dbc_mc47a2b9e1_gff",
                        "category": "card_not_present_fraud",
                        "card_action": "close_and_reissue",
                    },
                ],
                "closed_debit_cards": [
                    {"card_id": "dbc_blue_001", "reason": "fraud_suspected"},
                ],
                "final_card_statuses": {
                    "dbc_blue_001": "CLOSED",
                    "dbc_mc47a2b9e1_gff": "ACTIVE",
                },
            }
        )
        self.assertFalse(res["allowed"])
        self.assertGreaterEqual(len(res["violations"]), 3)


if __name__ == "__main__":
    unittest.main()
