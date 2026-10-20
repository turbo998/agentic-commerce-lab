"""Unit tests for Stage 60 protocol guards (UCP, ACP, Google AP2, and Sierra tau2-bench 2.0)."""

from __future__ import annotations

import unittest

from lab.ucp_root_array_order_acp_lineitem_ap2_vct_tau2_voice_design_guard import (
    verify_acp_checkout_line_item_and_delegate_auth_result,
    verify_ap2_vct_instrument_extensions_and_chain_decoder,
    verify_tau2_voice_design_scale_and_text_matrix_inline,
    verify_ucp_root_array_order_annotations_and_auth_state,
)


class Stage60ProtocolGuardTests(unittest.TestCase):
    """Test suite for Stage 60 UCP, ACP, AP2, and tau2-bench 2.0 guards."""

    def test_ucp_root_array_order_and_auth_state_valid(self) -> None:
        res = verify_ucp_root_array_order_annotations_and_auth_state(
            schema_name="dev.ucp.shopping.order",
            schema_category="capability",
            root_schema_type="object",
            populated_stored_user_fields=("buyer", "payment.instruments"),
            is_user_authenticated=True,
            is_authorized_for_operation=True,
            belongs_to_authenticated_user=True,
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.decision_code, "UCP_ROOT_ARRAY_ORDER_AND_AUTH_STATE_VERIFIED")

    def test_ucp_root_array_schema_rejected(self) -> None:
        res = verify_ucp_root_array_order_annotations_and_auth_state(
            schema_name="dev.ucp.shopping.catalog.items",
            schema_category="capability",
            root_schema_type="array",
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.decision_code, "UCP_ROOT_ARRAY_SCHEMA_FORBIDDEN")

    def test_ucp_order_stray_directional_annotations_rejected(self) -> None:
        res = verify_ucp_root_array_order_annotations_and_auth_state(
            schema_name="dev.ucp.shopping.order",
            schema_category="capability",
            root_schema_type="object",
            order_field_ucp_request_annotations={"currency": "omit", "policies": "omit"},
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.decision_code, "UCP_ORDER_STRAY_DIRECTIONAL_ANNOTATION_FORBIDDEN")

    def test_ucp_vendor_extension_and_unauthenticated_state_rejected(self) -> None:
        vendor_res = verify_ucp_root_array_order_annotations_and_auth_state(
            schema_name="com.acme.shopping.custom_loyalty",
            schema_category="extension",
            root_schema_type="object",
            is_core_ucp_repo_submission=True,
        )
        self.assertFalse(vendor_res.allowed)
        self.assertEqual(vendor_res.decision_code, "UCP_VENDOR_EXTENSION_MUST_BE_SELF_HOSTED")

        unauth_res = verify_ucp_root_array_order_annotations_and_auth_state(
            schema_name="dev.ucp.shopping.checkout",
            schema_category="capability",
            root_schema_type="object",
            populated_stored_user_fields=("payment.instruments",),
            is_user_authenticated=False,
        )
        self.assertFalse(unauth_res.allowed)
        self.assertEqual(unauth_res.decision_code, "UCP_UNAUTHENTICATED_STORED_USER_STATE_LEAK_FORBIDDEN")

    def test_acp_checkout_line_item_and_delegate_auth_result_valid(self) -> None:
        res = verify_acp_checkout_line_item_and_delegate_auth_result(
            create_request_line_items_ref="#/components/schemas/LineItem",
            update_request_line_items_ref="#/components/schemas/LineItem",
            request_line_items=[
                {
                    "id": "li_001",
                    "item": {
                        "id": "item_123",
                        "name": "Wireless Headphones",
                        "unit_amount": 7999,
                    },
                    "quantity": 2,
                    "totals": [{"type": "subtotal", "display_text": "Subtotal", "amount": 15998}],
                }
            ],
            delegate_auth_session_payload={
                "authentication_session_id": "auth_session_abc123",
                "status": "authenticated",
                "authentication_result": {
                    "outcome": "authenticated",
                    "transaction_id": "c4e59ceb-a382-4d6a-bc87-385d591fa09d",
                    "three_ds_server_trans_id": "6edcc246-23ee-4e94-ac5d-8ae620bea7d9",
                    "version": "2.2.0",
                },
            },
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.decision_code, "ACP_CHECKOUT_LINE_ITEM_AND_DELEGATE_AUTH_RESULT_VERIFIED")

    def test_acp_checkout_item_ref_and_unsatisfiable_delegate_auth_rejected(self) -> None:
        bad_ref = verify_acp_checkout_line_item_and_delegate_auth_result(
            create_request_line_items_ref="#/components/schemas/Item",
            update_request_line_items_ref="#/components/schemas/LineItem",
            request_line_items=[{"id": "item_123", "name": "Wireless Headphones", "unit_amount": 7999}],
            delegate_auth_session_payload={
                "authentication_session_id": "auth_session_abc123",
                "status": "authenticated",
            },
        )
        self.assertFalse(bad_ref.allowed)
        self.assertEqual(bad_ref.decision_code, "ACP_CHECKOUT_REQUEST_LINE_ITEM_SCHEMA_MISMATCH")

        bad_auth = verify_acp_checkout_line_item_and_delegate_auth_result(
            create_request_line_items_ref="#/components/schemas/LineItem",
            update_request_line_items_ref="#/components/schemas/LineItem",
            request_line_items=[
                {
                    "id": "li_001",
                    "item": {"id": "item_123", "name": "Headphones", "unit_amount": 7999},
                    "quantity": 1,
                    "totals": [{"type": "subtotal", "display_text": "Subtotal", "amount": 7999}],
                }
            ],
            delegate_auth_schema_uses_unsatisfiable_allof=True,
            delegate_auth_session_payload={
                "authentication_session_id": "auth_session_abc123",
                "status": "authenticated",
            },
        )
        self.assertFalse(bad_auth.allowed)
        self.assertEqual(bad_auth.decision_code, "ACP_DELEGATE_AUTH_RESULT_SCHEMA_UNSATISFIABLE_OR_INVALID")

    def test_ap2_vct_instrument_extensions_and_chain_decoder_valid(self) -> None:
        ext = {
            "payee_address": "0x1111111111111111111111111111111111111111",
            "facilitator": "https://facilitator.example",
        }
        res = verify_ap2_vct_instrument_extensions_and_chain_decoder(
            mandate_model="PaymentMandate",
            vct_value="mandate.payment.1",
            payment_instrument_input_extensions=ext,
            payment_instrument_signed_dump={"id": "x402-usdc-1", "type": "x402", **ext},
            dsd_jwt_token="eyJ0eXAiOiJkK3NkLWp3dCJ9.e30.sig~disc0~~eyJ0eXAiOiJrYitzZC1qd3QifQ.e30.sig~disc1~disc2~",
            split_double_tilde_first=True,
            receipt_public_key_format="ec_public_key",
            receipt_signature_valid=True,
            reference_callback_invoked_before_sig_verify=False,
            logs_contain_sensitive_payment_artifacts=False,
            mcp_logging_include_payloads=False,
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.decision_code, "AP2_VCT_INSTRUMENT_EXTENSIONS_AND_CHAIN_DECODER_VERIFIED")
        self.assertEqual(res.decoded_hop_count, 2)

    def test_ap2_unversioned_vct_dropped_extensions_and_single_tilde_split_rejected(self) -> None:
        ext = {"payee_address": "0x1111", "facilitator": "https://facilitator.example"}
        bad_vct = verify_ap2_vct_instrument_extensions_and_chain_decoder(
            mandate_model="PaymentMandate",
            vct_value="mandate.payment",
            payment_instrument_input_extensions=ext,
            payment_instrument_signed_dump={"id": "x402-1", "type": "x402", **ext},
            dsd_jwt_token="hop0~disc0~~hop1~disc1~",
        )
        self.assertFalse(bad_vct.allowed)
        self.assertEqual(bad_vct.decision_code, "AP2_UNVERSIONED_OR_INVALID_MANDATE_VCT")

        dropped_ext = verify_ap2_vct_instrument_extensions_and_chain_decoder(
            mandate_model="PaymentMandate",
            vct_value="mandate.payment.1",
            payment_instrument_input_extensions=ext,
            payment_instrument_signed_dump={"id": "x402-1", "type": "x402"},
            dsd_jwt_token="hop0~disc0~~hop1~disc1~",
        )
        self.assertFalse(dropped_ext.allowed)
        self.assertEqual(dropped_ext.decision_code, "AP2_PAYMENT_INSTRUMENT_EXTENSION_FIELDS_DROPPED")

        bad_split = verify_ap2_vct_instrument_extensions_and_chain_decoder(
            mandate_model="CheckoutMandate",
            vct_value="mandate.checkout.1",
            payment_instrument_input_extensions=ext,
            payment_instrument_signed_dump={"id": "x402-1", "type": "x402", **ext},
            dsd_jwt_token="hop0~disc0~~hop1~disc1~",
            split_double_tilde_first=False,
        )
        self.assertFalse(bad_split.allowed)
        self.assertEqual(bad_split.decision_code, "AP2_DSDJWT_CHAIN_SINGLE_TILDE_SPLIT_CORRUPTION")

    def test_tau2_voice_design_scale_and_text_matrix_valid_and_rejections(self) -> None:
        valid = verify_tau2_voice_design_scale_and_text_matrix_inline(
            guidance_scale_api_value=5,
            export_submission_passes_results_json_file=True,
            expected_inline_text_trials=6,
            counted_inline_text_trials=6,
        )
        self.assertTrue(valid.allowed)
        self.assertEqual(valid.decision_code, "TAU2_VOICE_DESIGN_SCALE_AND_TEXT_MATRIX_VERIFIED")

        bad_scale = verify_tau2_voice_design_scale_and_text_matrix_inline(
            guidance_scale_api_value=38,
        )
        self.assertFalse(bad_scale.allowed)
        self.assertEqual(bad_scale.decision_code, "TAU2_VOICE_DESIGN_UI_PERCENTAGE_SENT_AS_API_SCALE")

        bad_text_matrix = verify_tau2_voice_design_scale_and_text_matrix_inline(
            guidance_scale_api_value=5,
            export_submission_passes_results_json_file=False,
            expected_inline_text_trials=6,
            counted_inline_text_trials=0,
        )
        self.assertFalse(bad_text_matrix.allowed)
        self.assertEqual(bad_text_matrix.decision_code, "TAU2_TEXT_MATRIX_DIRECTORY_PATH_DROPS_INLINE_TRIALS")


if __name__ == "__main__":
    unittest.main()
