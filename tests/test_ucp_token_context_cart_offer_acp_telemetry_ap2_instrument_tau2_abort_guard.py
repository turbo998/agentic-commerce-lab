"""Unit tests for Stage 66 UCP, ACP, Google AP2, and Sierra tau2-bench runtime guards."""

from __future__ import annotations

import unittest

from lab.ucp_token_context_cart_offer_acp_telemetry_ap2_instrument_tau2_abort_guard import (
    verify_acp_session_context_app_links_order_alignment_and_seller_backed,
    verify_ap2_instrument_type_id_golden_vectors_and_zod_sdk,
    verify_tau2_out_of_scope_abort_fenced_nl_json_checkpoint_and_campus,
    verify_ucp_permalink_version_token_context_cart_offer_and_security_schemes,
)


class Stage66UCPACPAP2Tau2GuardTests(unittest.TestCase):
    def test_ucp_permalink_version_token_context_cart_offer_and_security_schemes_passes(self) -> None:
        res = verify_ucp_permalink_version_token_context_cart_offer_and_security_schemes(
            permalink_has_ucp_field_paths=True,
            permalink_ucp_versions=["2026-08-25"],
            redirect_url_contains_control_params=False,
            browser_returned_json_version_unsupported=False,
            issued_token_binding={"checkout_id": "chk_100", "amount_minor": 4500, "currency": "USD"},
            presented_token_binding={"checkout_id": "chk_100", "amount_minor": 4500, "currency": "USD"},
            token_identity_accepted_as_caller_auth=False,
            cart_has_parallel_offers_available_array=False,
            cart_id="cart_501",
            cart_state_ref="state_sha256_abc",
            offer_action_applies_to_cart_id="cart_501",
            offer_action_applies_to_state_ref="state_sha256_abc",
            offer_revision_immutable=True,
            cart_previous_status="active",
            cart_next_status="ordered",
            payment_action_ready_result={},
            payment_action_ready_is_error_branch=False,
            digital_delivery_extension={
                "attached_to": "order",
                "kind": "redeemable_artifact",
                "reference": "dd_ref_991",
                "lookup": "https://issuer.example/lookup/dd_ref_991",
                "caches_mutable_balance": False,
                "releases_settlement_on_delivery": False,
            },
            openapi_declared_header_param_names=["Idempotency-Key", "Request-Id"],
            openapi_has_security_schemes=True,
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.reason_codes, ())
        self.assertEqual(res.resolved_permalink_version, "2026-08-25")
        self.assertTrue(res.cart_terminal)

    def test_ucp_permalink_version_token_context_cart_offer_and_security_schemes_rejects_violations(self) -> None:
        res = verify_ucp_permalink_version_token_context_cart_offer_and_security_schemes(
            permalink_has_ucp_field_paths=True,
            permalink_ucp_versions=["2026-08-25-rc1"],
            redirect_url_contains_control_params=True,
            browser_returned_json_version_unsupported=True,
            issued_token_binding={"checkout_id": "chk_100", "amount_minor": 4500},
            presented_token_binding={"checkout_id": "chk_100", "amount_minor": 9900},
            token_identity_accepted_as_caller_auth=True,
            cart_has_parallel_offers_available_array=True,
            cart_id="cart_501",
            cart_state_ref="state_sha256_abc",
            offer_action_applies_to_cart_id="cart_501",
            offer_action_applies_to_state_ref="state_sha256_stale",
            offer_revision_immutable=False,
            cart_previous_status="ordered",
            cart_next_status="active",
            payment_action_ready_result={"status": "ok"},
            payment_action_ready_is_error_branch=False,
            digital_delivery_extension={
                "attached_to": "checkout",
                "kind": "redeemable_artifact",
                "reference": "dd_ref_991",
                "lookup": "https://issuer.example/lookup/dd_ref_991",
                "caches_mutable_balance": True,
                "releases_settlement_on_delivery": True,
            },
            openapi_declared_header_param_names=["Authorization", "Content-Type"],
            openapi_has_security_schemes=False,
        )
        self.assertFalse(res.passed)
        self.assertEqual(
            res.reason_codes,
            (
                "ucp_permalink_version_missing_or_leaked_on_redirect",
                "ucp_token_credential_binding_mutated_or_mismatch",
                "ucp_cart_offer_state_ref_mismatch_or_parallel_array",
                "ucp_cart_terminal_status_invalid_or_mutated",
                "ucp_payment_action_ready_non_empty_success_object",
                "ucp_digital_delivery_cached_balance_or_premature_settlement",
                "ucp_openapi_ignored_auth_header_parameter_declared",
            ),
        )

    def test_acp_session_context_app_links_order_alignment_and_seller_backed_passes(self) -> None:
        res = verify_acp_session_context_app_links_order_alignment_and_seller_backed(
            complete_checkout_has_legacy_risk_signals_object=False,
            complete_checkout_session_context={
                "ip_address": "198.51.100.42",
                "user_agent": "ChatGPT-Agent/1.0",
                "session_id": "sess_77",
            },
            delegate_payment_session_context={
                "ip_address": "198.51.100.42",
                "device_fingerprint": "fp_998",
            },
            delegate_payment_risk_signals=[
                {"type": "bot_detection", "score": 12, "action": "allow"}
            ],
            product_url="https://merchant.example/products/sku_1",
            app_links=[
                {"platform": "ios", "uri": "merchantapp://products/sku_1"},
                {"platform": "embedded_app", "uri": "https://app.merchant.example/embed/sku_1"},
            ],
            client_supported_platforms=["embedded_app"],
            selected_uri="https://app.merchant.example/embed/sku_1",
            order_status="completed",
            line_item_quantities={"ordered": 3, "fulfilled": 2, "canceled": 1, "returned": 1},
            content_attribution_urls=["https://www.wirecutter.com/reviews/best-headphones"],
            seller_backed_handler={
                "id": "dev.acp.seller_backed.points",
                "requires_delegate_payment": True,
                "requires_pci_compliance": False,
                "credentials_transferred_to_agent": False,
                "points_balance_minor": 6000,
                "purchase_amount_minor": 4500,
            },
            x402_crypto_facilitator_verified=True,
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.reason_codes, ())
        self.assertEqual(res.selected_experience_uri, "https://app.merchant.example/embed/sku_1")

    def test_acp_session_context_app_links_order_alignment_and_seller_backed_rejects_violations(self) -> None:
        res = verify_acp_session_context_app_links_order_alignment_and_seller_backed(
            complete_checkout_has_legacy_risk_signals_object=True,
            complete_checkout_session_context=None,
            delegate_payment_session_context=None,
            delegate_payment_risk_signals={"ip_address": "198.51.100.42"},
            product_url="https://merchant.example/products/sku_1",
            app_links=[{"platform": "ios", "uri": "merchantapp://products/sku_1"}],
            client_supported_platforms=["web"],
            selected_uri="merchantapp://products/sku_1",
            order_status="fulfilled",
            line_item_quantities={"ordered": 3, "fulfilled": 2, "canceled": 0, "returned": 3},
            content_attribution_urls=["http://insecure.example/review"],
            seller_backed_handler={
                "id": "dev.acp.seller_backed.points",
                "requires_delegate_payment": True,
                "requires_pci_compliance": True,
                "credentials_transferred_to_agent": True,
                "points_balance_minor": 2000,
                "purchase_amount_minor": 4500,
            },
            x402_crypto_facilitator_verified=False,
        )
        self.assertFalse(res.passed)
        self.assertEqual(
            res.reason_codes,
            (
                "acp_session_context_or_risk_signals_schema_collision",
                "acp_feed_app_links_invalid_or_missing_url_fallback",
                "acp_order_post_checkout_quantity_or_status_violation",
                "acp_content_attribution_invalid_url",
                "acp_seller_backed_or_x402_crypto_handler_violation",
            ),
        )

    def test_ap2_instrument_type_id_golden_vectors_and_zod_sdk_passes(self) -> None:
        res = verify_ap2_instrument_type_id_golden_vectors_and_zod_sdk(
            allowed_instruments=[{"id": "pi-1", "type": "card"}],
            presented_instrument={"id": "pi-1", "type": "card"},
            vector_segment_count=3,
            wire_double_tilde_joins=2,
            wire_ends_with_tilde=True,
            jws_signatures_valid=True,
            receipt_payload={
                "status": "success",
                "psp_confirmation_id": "psp_881",
                "network_confirmation_id": "net_992",
            },
            ghost_protocol_mandate={
                "chain_id": 8453,
                "eip712_signature_valid": True,
                "monthly_cap_minor": 20000,
                "requested_spend_minor": 12500,
            },
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.reason_codes, ())
        self.assertEqual(res.matched_instrument_pair, ("card", "pi-1"))

    def test_ap2_instrument_type_id_golden_vectors_and_zod_sdk_rejects_violations(self) -> None:
        res = verify_ap2_instrument_type_id_golden_vectors_and_zod_sdk(
            allowed_instruments=[{"id": "pi-1", "type": "card"}],
            presented_instrument={"id": "pi-1", "type": "bank"},
            vector_segment_count=3,
            wire_double_tilde_joins=1,
            wire_ends_with_tilde=False,
            jws_signatures_valid=False,
            receipt_payload={"status": "success", "psp_confirmation_id": "psp_881"},
            ghost_protocol_mandate={
                "chain_id": 1,
                "eip712_signature_valid": False,
                "monthly_cap_minor": 20000,
                "requested_spend_minor": 25000,
            },
        )
        self.assertFalse(res.passed)
        self.assertEqual(
            res.reason_codes,
            (
                "ap2_allowed_payment_instrument_type_mismatch",
                "ap2_delegate_sd_jwt_golden_vector_wire_violation",
                "ap2_receipt_oneof_branch_required_fields_missing",
                "ap2_autonomous_infra_intent_mandate_cap_or_sig_invalid",
            ),
        )

    def test_tau2_out_of_scope_abort_fenced_nl_json_checkpoint_and_campus_passes(self) -> None:
        res = verify_tau2_out_of_scope_abort_fenced_nl_json_checkpoint_and_campus(
            user_message="Sorry, I have nothing left in the scenario ###OUT-OF-SCOPE### ###STOP###",
            recorded_termination_reason="OUT_OF_SCOPE",
            assigned_reward=0.0,
            nl_judge_raw_response='```json\n{"results": [{"met": true, "justification": "Verified"}]}\n```',
            malformed_json_swallowed_as_empty=False,
            checkpoint_unlinked_before_replacement_write=False,
            banking_aggregate_task_count=97,
            banking_individual_task_count=97,
            banking_task_102_has_nl_assertion=True,
            airline_user_id="sara_doe_496",
            campus_reward_basis=["DB", "COMMUNICATE"],
            campus_has_env_assertions=True,
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.reason_codes, ())
        self.assertEqual(res.classified_termination_reason, "OUT_OF_SCOPE")

    def test_tau2_out_of_scope_abort_fenced_nl_json_checkpoint_and_campus_rejects_violations(self) -> None:
        res = verify_tau2_out_of_scope_abort_fenced_nl_json_checkpoint_and_campus(
            user_message="Scenario missing details ###OUT-OF-SCOPE###",
            recorded_termination_reason="USER_STOP",
            assigned_reward=1.0,
            nl_judge_raw_response="```json\n{not_valid_json\n```",
            malformed_json_swallowed_as_empty=True,
            checkpoint_unlinked_before_replacement_write=True,
            banking_aggregate_task_count=97,
            banking_individual_task_count=97,
            banking_task_102_has_nl_assertion=False,
            airline_user_id="Sara_Doe_496",
            campus_reward_basis=["DB", "ACTION", "COMMUNICATE"],
            campus_has_env_assertions=False,
        )
        self.assertFalse(res.passed)
        self.assertEqual(
            res.reason_codes,
            (
                "tau2_out_of_scope_abort_conflated_with_user_stop",
                "tau2_nl_judge_fenced_json_or_malformed_swallowed",
                "tau2_checkpoint_pre_unlink_data_loss_on_write_failure",
                "tau2_banking_aggregate_or_airline_campus_invariant_violation",
            ),
        )


if __name__ == "__main__":
    unittest.main()
