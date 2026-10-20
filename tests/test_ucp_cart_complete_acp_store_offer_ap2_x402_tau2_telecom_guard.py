"""Unit tests for Stage 62 deterministic protocol & benchmark guards."""

from __future__ import annotations

import unittest

from lab.ucp_cart_complete_acp_store_offer_ap2_x402_tau2_telecom_guard import (
    compute_ucp_requirement_digest,
    validate_acp_store_offer_order_delegate_guard,
    validate_ap2_closed_binding_x402_trustboost_guard,
    validate_tau2_telecom_livedb_fault_cli_guard,
    validate_ucp_cart_complete_auth_requirements_guard,
)


class TestStage62UcpAcpAp2Tau2Guards(unittest.TestCase):
    """Test suite for Stage 62 UCP, ACP, AP2, and tau2-bench guards."""

    def test_ucp_cart_complete_auth_and_requirements_happy_path(self) -> None:
        digest = compute_ucp_requirement_digest(
            "dev.ucp.shopping.checkout",
            "checkout-functionality",
            "The checkout object MUST be returned as part of a DataPart object.",
        )
        res = validate_ucp_cart_complete_auth_requirements_guard(
            checkout_operation="create_checkout",
            checkout_payload={"cart_id": "cart_123", "line_items": []},
            cart_id_ucp_request_map={"create": "optional", "update": "omit", "complete": "omit"},
            has_ucp_agent_header=True,
            signature_input_covered_components=("@method", "@target-uri", "content-digest", "ucp-agent"),
            embedded_auth_method="ec.auth",
            embedded_auth_type_required_in_openrpc=True,
            embedded_auth_type_value="oauth2",
            mcp_complete_supported_extensions=(
                "dev.ucp.shopping.buyer_consent",
                "dev.ucp.common.payment.ap2_mandate",
            ),
            requirement_record={
                "id": "REQ-CHECKOUT-A2A-01",
                "capability": "dev.ucp.shopping.checkout",
                "list_stem": "checkout-functionality",
                "clause": "The checkout object MUST be returned as part of a DataPart object.",
                "content_digest": digest,
                "verify_digest_match": True,
            },
            extraction_counts={
                "bolded_obligations": 207,
                "unbolded_reported": 29,
                "schema_annotation_only": 23,
                "total_keyword_clauses": 259,
            },
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.error_codes, ())
        self.assertEqual(res.computed_content_digest, digest)

    def test_ucp_cart_id_on_complete_and_missing_line_items_rejected(self) -> None:
        res_complete = validate_ucp_cart_complete_auth_requirements_guard(
            checkout_operation="complete_checkout",
            checkout_payload={"id": "chk_1", "cart_id": "cart_leak"},
            cart_id_ucp_request_map={"create": "optional", "update": "omit"},
        )
        self.assertFalse(res_complete.allowed)
        self.assertIn("ucp_cart_id_schema_missing_complete_omit", res_complete.error_codes)
        self.assertIn("ucp_cart_id_forbidden_on_complete_checkout", res_complete.error_codes)

        res_create = validate_ucp_cart_complete_auth_requirements_guard(
            checkout_operation="create_checkout",
            checkout_payload={"cart_id": "cart_123"},
        )
        self.assertFalse(res_create.allowed)
        self.assertIn("ucp_line_items_required_on_cart_conversion", res_create.error_codes)

    def test_ucp_signature_coverage_openrpc_and_requirements_errors(self) -> None:
        res = validate_ucp_cart_complete_auth_requirements_guard(
            checkout_operation="complete_checkout",
            checkout_payload={"id": "chk_1"},
            has_ucp_agent_header=True,
            signature_input_covered_components=("@method", "@target-uri", "content-digest"),
            embedded_auth_method="ep.cart.auth",
            embedded_auth_type_required_in_openrpc=False,
            embedded_auth_type_value="",
            mcp_complete_supported_extensions=("dev.ucp.shopping.buyer_consent",),
            requirement_record={
                "id": "invalid_id",
                "capability": "dev.ucp.shopping.checkout",
                "list_stem": "stem",
                "clause": "Clause text",
                "content_digest": "deadbeef00",
                "verify_digest_match": True,
            },
            extraction_counts={
                "bolded_obligations": 200,
                "unbolded_reported": 29,
                "schema_annotation_only": 23,
                "total_keyword_clauses": 259,
            },
        )
        self.assertFalse(res.allowed)
        self.assertIn("ucp_signature_coverage_insufficient_ucp_agent", res.error_codes)
        self.assertIn("ucp_openrpc_embedded_auth_type_not_marked_required", res.error_codes)
        self.assertIn("ucp_embedded_auth_missing_type_param", res.error_codes)
        self.assertIn("ucp_mcp_complete_checkout_missing_extensions", res.error_codes)
        self.assertIn("ucp_requirement_id_invalid_format", res.error_codes)
        self.assertIn("ucp_requirement_content_digest_mismatch", res.error_codes)
        self.assertIn("ucp_requirements_extraction_reconciliation_failed", res.error_codes)

    def test_acp_store_offer_order_delegate_happy_path(self) -> None:
        res = validate_acp_store_offer_order_delegate_guard(
            allowance_payload={
                "reason": "one_time",
                "max_amount": 15000,
                "currency": "usd",
                "merchant_id": "merch_bopis_1",
                "expires_at": "2026-10-20T14:00:00Z",
            },
            delegate_error_payload={
                "type": "service_unavailable",
                "code": "x402_future_settlement_paused",
                "message": "Future error code handled gracefully",
            },
            strict_error_enum_rejection=False,
            checkout_operation="update",
            request_has_store_id=True,
            response_store={"id": "store_nyc_01", "name": "Midtown Flagship"},
            store_query_limit=20,
            store_query_radius_km=25.0,
            now_iso="2026-10-20T12:00:00Z",
            session_quote_expires_at="2026-10-20T12:30:00Z",
            line_item_valid_until="2026-10-20T12:15:00Z",
            line_item_availability_status="offer_valid",
            session_status="ready_for_payment",
            fulfillment_type="digital",
            order_status="fulfilled",
        )
        self.assertTrue(res.allowed)
        self.assertTrue(res.delegate_allowance_valid)
        self.assertTrue(res.delegate_error_forward_compatible)
        self.assertTrue(res. normalized_error_category.startswith("fallback_generic:"))

    def test_acp_store_complete_and_offer_expiry_and_digital_shipped_rejected(self) -> None:
        res = validate_acp_store_offer_order_delegate_guard(
            allowance_payload={"reason": "one_time", "max_amount": 1000},
            delegate_error_payload={"type": "service_unavailable", "code": "future_code"},
            strict_error_enum_rejection=True,
            checkout_operation="complete",
            request_has_store_id=True,
            response_store={"id": "store_01", "name": ""},
            store_query_limit=250,
            store_query_radius_km=-5.0,
            now_iso="2026-10-20T12:20:00Z",
            session_quote_expires_at="2026-10-20T12:30:00Z",
            line_item_valid_until="2026-10-20T12:15:00Z",
            line_item_availability_status="offer_valid",
            session_status="ready_for_payment",
            emitted_message_codes=(),
            fulfillment_type="digital",
            order_status="shipped",
        )
        self.assertFalse(res.allowed)
        self.assertIn("acp_delegate_allowance_missing_required_fields", res.error_codes)
        self.assertIn("acp_delegate_error_strict_enum_rejection_forbidden", res.error_codes)
        self.assertIn("acp_store_id_forbidden_on_checkout_complete", res.error_codes)
        self.assertIn("acp_store_response_missing_id_or_name", res.error_codes)
        self.assertIn("acp_store_discovery_invalid_query_bounds", res.error_codes)
        self.assertIn("acp_line_item_offer_expired_not_enforced", res.error_codes)
        self.assertIn("acp_digital_order_forbidden_shipped_status", res.error_codes)

    def test_ap2_closed_binding_x402_trustboost_happy_path(self) -> None:
        res = validate_ap2_closed_binding_x402_trustboost_guard(
            expected_open_checkout_hash="sha256:open_chk_001",
            actual_open_checkout_hash="sha256:open_chk_001",
            closed_mandate_transaction_id="sha256:closed_jwt_001",
            expected_checkout_jwt_hash="sha256:closed_jwt_001",
            agent_provider_pub="-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A...",
            mandate_signature_valid=True,
            verified_mandate_amount_cents=8900,
            proposed_eip3009_amount_cents=8900,
            payload_text="Customer [REDACTED_CPF] tax ID [REDACTED_RFC] verified.",
            x402_payment_settled=True,
            solana_anchor_tx="5xSolanaMainnetAnchorTxProof998",
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.authorized_amount_cents, 8900)
        self.assertEqual(res.detected_unredacted_pii_types, ())

    def test_ap2_unverified_closed_binding_missing_key_1250_fallback_and_pii_rejected(self) -> None:
        res = validate_ap2_closed_binding_x402_trustboost_guard(
            expected_open_checkout_hash="sha256:open_chk_001",
            actual_open_checkout_hash="sha256:open_chk_001",
            closed_mandate_transaction_id="sha256:other_checkout_jwt",
            expected_checkout_jwt_hash="sha256:closed_jwt_001",
            agent_provider_pub="",
            verified_mandate_amount_cents=8900,
            proposed_eip3009_amount_cents=1250,
            payload_text="Cliente CPF 123.456.789-01 e email maria@example.com",
            x402_payment_settled=False,
            solana_anchor_tx="",
        )
        self.assertFalse(res.allowed)
        self.assertIn("ap2_closed_mandate_checkout_binding_unverified", res.error_codes)
        self.assertIn("agent_provider_key_missing", res.error_codes)
        self.assertIn("ap2_x402_hardcoded_1250_amount_fallback_detected", res.error_codes)
        self.assertIn("ap2_trustboost_unredacted_pii_in_payload", res.error_codes)
        self.assertIn("ap2_trustboost_missing_x402_or_anchor_proof", res.error_codes)
        self.assertIn("CPF", res.detected_unredacted_pii_types)
        self.assertIn("EMAIL", res.detected_unredacted_pii_types)

    def test_tau2_telecom_livedb_fault_cli_happy_path(self) -> None:
        res = validate_tau2_telecom_livedb_fault_cli_guard(
            line_status="active",
            line_owned_by_customer=True,
            refuel_amount_gb=2.0,
            initial_data_gb=5.0,
            initial_bill_usd=40.0,
            rate_per_gb_usd=5.0,
            attempted_mutation_on_inactive=False,
            live_db_hash="sha256:live_committed_state",
            expected_target_db_hash="sha256:live_committed_state",
            replayed_db_hash="sha256:replay_skipped_timeout_after_commit",
            reward_graded_from="live",
            injected_tool_fault="timeout_after_commit",
            tool_mutated_live_db=True,
            recorded_language="en",
            verified_against_pack_tasks=True,
            is_bridged_gpt5_responses_call=True,
            allowed_openai_params=("tool_choice",),
            requested_tool_choice="required",
            sent_tool_choice="required",
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.updated_data_gb, 7.0)
        self.assertEqual(res.updated_bill_usd, 50.0)
        self.assertTrue(res.live_db_reward_passed)
        self.assertTrue(res.replay_divergence_detected)
        self.assertTrue(res.gpt5_tool_choice_preserved)

    def test_tau2_suspended_refuel_replay_grading_and_dropped_tool_choice_rejected(self) -> None:
        res = validate_tau2_telecom_livedb_fault_cli_guard(
            line_status="suspended",
            attempted_mutation_on_inactive=True,
            live_db_hash="sha256:live_state",
            expected_target_db_hash="sha256:live_state",
            replayed_db_hash="sha256:replay_state",
            reward_graded_from="replay",
            injected_tool_fault="timeout_before_commit",
            tool_mutated_live_db=True,
            recorded_language="en",
            verified_against_pack_tasks=False,
            is_bridged_gpt5_responses_call=True,
            allowed_openai_params=(),
            requested_tool_choice="required",
            sent_tool_choice=None,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.updated_data_gb, 5.0)
        self.assertEqual(res.updated_bill_usd, 40.0)
        self.assertIn("tau2_telecom_inactive_line_refuel_mutation", res.error_codes)
        self.assertIn("tau2_db_check_graded_from_replay_instead_of_live", res.error_codes)
        self.assertIn("tau2_tool_fault_timeout_before_commit_mutated_db", res.error_codes)
        self.assertIn("tau2_en_trajectory_verified_against_stale_registry_tasks", res.error_codes)
        self.assertIn("tau2_gpt5_bridged_call_dropped_tool_choice", res.error_codes)


if __name__ == "__main__":
    unittest.main()
