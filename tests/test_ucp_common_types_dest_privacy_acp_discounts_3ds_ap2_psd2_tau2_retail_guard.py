"""Unit tests for Stage 114 deterministic protocol & benchmark guardrails."""

from __future__ import annotations

import unittest

from lab.ucp_common_types_dest_privacy_acp_discounts_3ds_ap2_psd2_tau2_retail_guard import (
    validate_acp_discounts_3ds_frictionless_and_fulfillment_ref_guard,
    validate_ap2_psd2_lifecycle_and_compliance_receipt_guard,
    validate_tau2_retail_exchange_and_dropped_seed_warning_guard,
    validate_ucp_common_primitives_destination_privacy_and_mcp_mapping_guard,
)


class TestStage114Guardrails(unittest.TestCase):
    def setUp(self) -> None:
        self.valid_ucp = {
            "schema_refs": [
                "https://ucp.dev/schemas/common/types/context.json",
                "https://ucp.dev/schemas/common/types/totals.json",
            ],
            "identity_linked_buyer": {
                "email": "alice@example.com",
                "phone": "+14155550101",
                "name": "Alice Doe",
                "destination_selected": False,
                "disclosed_precise_saved_address": False,
            },
            "mcp_operation_mapping": {
                "exposed_operations_count": 5,
                "mcp_tools_count": 5,
                "claims_capability_maps_1to1_to_tool": False,
            },
        }
        self.valid_acp = {
            "discounts_response": {"applied": [], "rejected": []},
            "three_ds_frictionless": {
                "three_ds_version": "2.2.0",
                "directory_server_transaction_id": "ds_tx_9001",
                "trans_status": "Y",
            },
            "checkout_response_fulfillment": {
                "fulfillment_options": [{"id": "ful_std_01"}, {"id": "ful_exp_02"}],
                "selected_fulfillment_option_id": "ful_std_01",
            },
        }
        self.valid_ap2 = {
            "compliance_receipt": {
                "mandate_id": "mnd_101",
                "mandate_hash": "sha256:abcdef123456",
                "verdict": "ADMITTED",
                "signature_verified": True,
            },
            "cancellation_receipt": {"cancellation_reason": "USER_REQUESTED"},
            "refund_receipt": {
                "refund_result": "PARTIAL",
                "refund_amount_minor": 1500,
                "settled_amount_minor": 3000,
            },
        }
        self.valid_tau2 = {
            "retail_exchange": {
                "order_status": "delivered",
                "price_diff_minor": 2110,
                "payment_method_kind": "gift_card",
                "gift_card_balance_minor": 2500,
            },
            "llm_call_audit": {
                "seed_requested": True,
                "provider_supports_seed": False,
                "dropped_params_warned": True,
            },
        }

    def test_ucp_common_primitives_dest_privacy_and_mcp_pass(self) -> None:
        res = validate_ucp_common_primitives_destination_privacy_and_mcp_mapping_guard(self.valid_ucp)
        self.assertTrue(res.allowed)
        self.assertEqual(res.decision_code, "UCP_COMMON_TYPES_DEST_PRIVACY_AND_MCP_VERIFIED")

    def test_ucp_blocks_legacy_shopping_types_and_premature_address(self) -> None:
        bad_ref = {**self.valid_ucp, "schema_refs": ["https://ucp.dev/schemas/shopping/types/context.json"]}
        self.assertEqual(
            validate_ucp_common_primitives_destination_privacy_and_mcp_mapping_guard(bad_ref).decision_code,
            "UCP_LEGACY_SHOPPING_TYPES_PRIMITIVE_REF",
        )
        bad_addr = {
            **self.valid_ucp,
            "identity_linked_buyer": {
                **self.valid_ucp["identity_linked_buyer"],
                "disclosed_precise_saved_address": True,
            },
        }
        self.assertEqual(
            validate_ucp_common_primitives_destination_privacy_and_mcp_mapping_guard(bad_addr).decision_code,
            "UCP_PREMATURE_SAVED_ADDRESS_DISCLOSURE",
        )

    def test_acp_discounts_3ds_and_fulfillment_pass(self) -> None:
        res = validate_acp_discounts_3ds_frictionless_and_fulfillment_ref_guard(self.valid_acp)
        self.assertTrue(res.allowed)
        self.assertEqual(res.decision_code, "ACP_DISCOUNTS_3DS_AND_FULFILLMENT_VERIFIED")

    def test_acp_blocks_missing_rejected_array_and_bad_fulfillment_ref(self) -> None:
        bad_disc = {**self.valid_acp, "discounts_response": {"applied": []}}
        self.assertEqual(
            validate_acp_discounts_3ds_frictionless_and_fulfillment_ref_guard(bad_disc).decision_code,
            "ACP_DISCOUNTS_REJECTED_ARRAY_MISSING",
        )
        bad_ful = {
            **self.valid_acp,
            "checkout_response_fulfillment": {
                "fulfillment_options": [{"id": "ful_std_01"}],
                "selected_fulfillment_option_id": "ful_unknown_99",
            },
        }
        self.assertEqual(
            validate_acp_discounts_3ds_frictionless_and_fulfillment_ref_guard(bad_ful).decision_code,
            "ACP_COMPLETE_CANCEL_FULFILLMENT_VALUE_INVALID",
        )

    def test_ap2_psd2_lifecycle_and_compliance_receipt_pass(self) -> None:
        res = validate_ap2_psd2_lifecycle_and_compliance_receipt_guard(self.valid_ap2)
        self.assertTrue(res.allowed)
        self.assertEqual(res.decision_code, "AP2_PSD2_LIFECYCLE_AND_COMPLIANCE_RECEIPT_VERIFIED")

    def test_ap2_blocks_invalid_psd2_cancellation_or_over_refund(self) -> None:
        bad_cancel = {**self.valid_ap2, "cancellation_receipt": {"cancellation_reason": "ARBITRARY_REASON"}}
        self.assertEqual(
            validate_ap2_psd2_lifecycle_and_compliance_receipt_guard(bad_cancel).decision_code,
            "AP2_PSD2_ART64_CANCELLATION_REASON_INVALID",
        )
        bad_refund = {
            **self.valid_ap2,
            "refund_receipt": {
                "refund_result": "FULL",
                "refund_amount_minor": 4000,
                "settled_amount_minor": 3000,
            },
        }
        self.assertEqual(
            validate_ap2_psd2_lifecycle_and_compliance_receipt_guard(bad_refund).decision_code,
            "AP2_PSD2_ART89_REFUND_ENVELOPE_INVALID",
        )

    def test_tau2_retail_exchange_and_seed_warning_pass(self) -> None:
        res = validate_tau2_retail_exchange_and_dropped_seed_warning_guard(self.valid_tau2)
        self.assertTrue(res.allowed)
        self.assertEqual(res.decision_code, "TAU2_RETAIL_EXCHANGE_AND_SEED_WARNING_VERIFIED")

    def test_tau2_blocks_pending_exchange_insufficient_gc_and_silent_seed_drop(self) -> None:
        bad_pending = {
            **self.valid_tau2,
            "retail_exchange": {**self.valid_tau2["retail_exchange"], "order_status": "pending"},
        }
        self.assertEqual(
            validate_tau2_retail_exchange_and_dropped_seed_warning_guard(bad_pending).decision_code,
            "TAU2_RETAIL_EXCHANGE_NON_DELIVERED_ORDER",
        )
        bad_gc = {
            **self.valid_tau2,
            "retail_exchange": {**self.valid_tau2["retail_exchange"], "gift_card_balance_minor": 1700},
        }
        self.assertEqual(
            validate_tau2_retail_exchange_and_dropped_seed_warning_guard(bad_gc).decision_code,
            "TAU2_RETAIL_GIFT_CARD_BALANCE_INSUFFICIENT",
        )
        bad_seed = {
            **self.valid_tau2,
            "llm_call_audit": {
                "seed_requested": True,
                "provider_supports_seed": False,
                "dropped_params_warned": False,
            },
        }
        self.assertEqual(
            validate_tau2_retail_exchange_and_dropped_seed_warning_guard(bad_seed).decision_code,
            "TAU2_SILENT_DROPPED_SEED_PARAM",
        )


if __name__ == "__main__":
    unittest.main()
