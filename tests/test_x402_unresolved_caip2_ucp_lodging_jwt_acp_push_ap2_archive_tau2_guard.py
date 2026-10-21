"""Unit tests for Stage 152 deterministic guards (UN-01..UN-16)."""

from __future__ import annotations

import base64
import hashlib
import json
import unittest

from lab.x402_unresolved_caip2_ucp_lodging_jwt_acp_push_ap2_archive_tau2_guard import (
    evaluate_acp_governance_binding_offer_expiry_and_order_status_guard,
    evaluate_acp_push_rail_and_appointment_scheduling_guard,
    evaluate_ap2_line_items_wildcard_and_wba_entropy_guard,
    evaluate_ap2_verified_merchant_and_dispute_archive_guard,
    evaluate_mcp_sync_dispatch_freshness_and_retry_guard,
    evaluate_stripe_order_summary_and_model_id_guard,
    evaluate_tau2_referral_tasks_sync_and_sandbox_guard,
    evaluate_ucp_checkout_jwt_and_precheck_guard,
    evaluate_ucp_contingencies_price_on_request_and_mcp_event_guard,
    evaluate_ucp_lodging_addons_board_and_booker_eligibility_guard,
    evaluate_ucp_webhook_signing_namespace_and_sale_basis_guard,
    evaluate_visa_tap_temporal_authority_and_receipt_guard,
    evaluate_x402_bounded_body_evm_cache_and_stellar_guard,
    evaluate_x402_mcp_timeout_and_svm_delegated_store_guard,
    evaluate_x402_route_template_fixed_point_and_caip2_guard,
    evaluate_x402_unresolved_settlement_and_pact_escrow_guard,
)


class Stage152GuardTests(unittest.TestCase):
    def test_x402_guards_un01_to_un04(self) -> None:
        # UN-01
        ok1 = evaluate_x402_unresolved_settlement_and_pact_escrow_guard(
            settlement_state="unresolved",
            receiver_issued_new_402_challenge=False,
            receiver_reported_payment_failed=False,
            receiver_represented_existing_authorization=True,
            requested_new_payer_signature=False,
            is_pact_escrow_auth_capture=True,
            delivery_verification_attested=True,
            toctou_lock_acquired=True,
        )
        self.assertTrue(ok1.allowed)
        bad1 = evaluate_x402_unresolved_settlement_and_pact_escrow_guard(
            settlement_state="unresolved",
            receiver_issued_new_402_challenge=True,
            receiver_reported_payment_failed=False,
            receiver_represented_existing_authorization=False,
            requested_new_payer_signature=True,
            is_pact_escrow_auth_capture=True,
            delivery_verification_attested=False,
            toctou_lock_acquired=False,
        )
        self.assertFalse(bad1.allowed)
        self.assertEqual(bad1.decision_code, "X402_UNRESOLVED_SETTLEMENT_RECHALLENGE_FORBIDDEN")

        # UN-02
        ok2 = evaluate_x402_route_template_fixed_point_and_caip2_guard(
            route_template="/api/v2/weather/%5Bcity%5D",
            caip2_network="eip155:8453",
        )
        self.assertTrue(ok2.allowed)
        bad2_trav = evaluate_x402_route_template_fixed_point_and_caip2_guard(
            route_template="/api/%252e%252e/admin",
            caip2_network="eip155:8453",
        )
        self.assertFalse(bad2_trav.allowed)
        self.assertEqual(
            bad2_trav.decision_code,
            "X402_ROUTE_TEMPLATE_FIXED_POINT_TRAVERSAL_BLOCKED",
        )
        bad2_caip = evaluate_x402_route_template_fixed_point_and_caip2_guard(
            route_template="/api/v2/pay",
            caip2_network="acme:api.example.com",
        )
        self.assertFalse(bad2_caip.allowed)
        self.assertEqual(bad2_caip.decision_code, "X402_CAIP2_REFERENCE_DOT_OR_CHAR_FORBIDDEN")

        # UN-03
        ok3 = evaluate_x402_mcp_timeout_and_svm_delegated_store_guard(
            accept_max_timeout_seconds=240,
            effective_mcp_tool_timeout_seconds=240,
            caller_read_timeout_seconds=None,
            initial_402_probe_timeout_seconds=300,
            svm_delegated_store_read_ok=False,
            svm_identity_authenticated=True,
            reported_svm_error_code="invalid_upto_svm_delegated_auth_store",
            svm_tx_broadcasted=False,
            channel_lock_storage_isolated=True,
        )
        self.assertTrue(ok3.allowed)
        bad3 = evaluate_x402_mcp_timeout_and_svm_delegated_store_guard(
            accept_max_timeout_seconds=240,
            effective_mcp_tool_timeout_seconds=60,
            caller_read_timeout_seconds=None,
            initial_402_probe_timeout_seconds=60,
            svm_delegated_store_read_ok=False,
            svm_identity_authenticated=True,
            reported_svm_error_code="invalid_upto_svm_delegated_settle_unauthenticated",
            svm_tx_broadcasted=True,
            channel_lock_storage_isolated=False,
        )
        self.assertFalse(bad3.allowed)
        self.assertEqual(bad3.decision_code, "X402_MCP_TOOL_TIMEOUT_UNDERSIZED")

        # UN-04
        ok4 = evaluate_x402_bounded_body_evm_cache_and_stellar_guard(
            response_kind="control_plane_402",
            response_body_bytes=65_536,
            stream_enabled=True,
            evm_getcode_positive=True,
            evm_check_awaited=True,
            evm_cached_entry_written=True,
            evm_cache_ttl_seconds=900,
            stellar_are_fees_sponsored=True,
        )
        self.assertTrue(ok4.allowed)
        bad4 = evaluate_x402_bounded_body_evm_cache_and_stellar_guard(
            response_kind="control_plane_402",
            response_body_bytes=2_097_152,
            stream_enabled=True,
            evm_getcode_positive=False,
            evm_check_awaited=False,
            evm_cached_entry_written=True,
            evm_cache_ttl_seconds=3600,
            stellar_are_fees_sponsored=False,
        )
        self.assertFalse(bad4.allowed)
        self.assertEqual(bad4.decision_code, "X402_CONTROL_PLANE_RESPONSE_BODY_TOO_LARGE")

    def test_ucp_and_acp_guards_un05_to_un10(self) -> None:
        # UN-05
        ok5 = evaluate_ucp_lodging_addons_board_and_booker_eligibility_guard(
            board_plan_type="half_board",
            selected_addons=[
                {"category": "extra", "price_minor": 2500},
                {"category": "flexibility", "price_minor": 1500},
            ],
            room_subtotal_minor=20_000,
            declared_addons_total_minor=4000,
            declared_grand_total_minor=24_000,
            required_min_age_years=21,
            booker_age_on_checkin_years=25,
            required_booker_fields=["birthdate", "family_name"],
            provided_booker_fields={"birthdate": "2001-04-10", "family_name": "Chen"},
        )
        self.assertTrue(ok5.allowed)
        bad5 = evaluate_ucp_lodging_addons_board_and_booker_eligibility_guard(
            board_plan_type="half_board",
            selected_addons=[{"category": "extra", "price_minor": 2500}],
            room_subtotal_minor=20_000,
            declared_addons_total_minor=2500,
            declared_grand_total_minor=22_500,
            required_min_age_years=21,
            booker_age_on_checkin_years=19,
            required_booker_fields=["birthdate"],
            provided_booker_fields={"birthdate": "2007-08-01"},
        )
        self.assertFalse(bad5.allowed)
        self.assertEqual(bad5.decision_code, "UCP_LODGING_BOOKER_UNDER_MINIMUM_AGE")

        # UN-06
        jwt_str = "eyJhbGciOiJFZERTQSJ9.eyJjaGVja291dF9pZCI6ImNoa18xIn0.c2lnbmF0dXJl"
        expected_hash = (
            base64.urlsafe_b64encode(hashlib.sha256(jwt_str.encode("ascii")).digest())
            .decode("ascii")
            .rstrip("=")
        )
        ok6 = evaluate_ucp_checkout_jwt_and_precheck_guard(
            checkout_jwt=jwt_str,
            checkout_mandate_checkout_hash=expected_hash,
            payment_mandate_transaction_id=expected_hash,
            profile_scheme="https",
            profile_status_code=304,
            profile_content_type="",
            has_cached_etag=True,
            supported_versions_intersect=True,
            payment_handlers_intersect=True,
        )
        self.assertTrue(ok6.allowed)
        bad6 = evaluate_ucp_checkout_jwt_and_precheck_guard(
            checkout_jwt=jwt_str,
            checkout_mandate_checkout_hash="tampered_hash",
            payment_mandate_transaction_id=expected_hash,
            profile_scheme="https",
            profile_status_code=200,
            profile_content_type="application/json",
            has_cached_etag=False,
            supported_versions_intersect=True,
            payment_handlers_intersect=True,
        )
        self.assertFalse(bad6.allowed)
        self.assertEqual(bad6.decision_code, "UCP_CHECKOUT_JWT_AP2_HASH_MISMATCH")

        # UN-07
        ok7 = evaluate_ucp_contingencies_price_on_request_and_mcp_event_guard(
            allow_item_substitution=False,
            substitution_occurred=False,
            max_capture_overage_bps=500,
            quoted_total_minor=10_000,
            capture_total_minor=10_400,
            max_delivery_delay_days=3,
            actual_delivery_delay_days=2,
            max_split_shipments=2,
            actual_split_shipments=2,
            item_is_price_on_request=True,
            has_bound_custom_quote=True,
            transport_type="mcp",
            order_event_emitted=True,
            mcp_order_notification_delivered=True,
        )
        self.assertTrue(ok7.allowed)
        bad7 = evaluate_ucp_contingencies_price_on_request_and_mcp_event_guard(
            allow_item_substitution=False,
            substitution_occurred=True,
            max_capture_overage_bps=500,
            quoted_total_minor=10_000,
            capture_total_minor=11_500,
            max_delivery_delay_days=3,
            actual_delivery_delay_days=7,
            max_split_shipments=1,
            actual_split_shipments=4,
            item_is_price_on_request=True,
            has_bound_custom_quote=False,
            transport_type="mcp",
            order_event_emitted=True,
            mcp_order_notification_delivered=False,
        )
        self.assertFalse(bad7.allowed)
        self.assertEqual(bad7.decision_code, "UCP_PRICE_ON_REQUEST_REQUIRES_BOUND_QUOTE")

        # UN-08
        ok8 = evaluate_ucp_webhook_signing_namespace_and_sale_basis_guard(
            signed_webhook_headers=["webhook-id", "webhook-timestamp", "content-digest"],
            webhook_id="wh_001",
            webhook_timestamp=1_792_000_000,
            now_epoch_seconds=1_792_000_050,
            extension_namespace="com.acme.custom_loyalty",
            is_core_ucp_spec_artifact=False,
            requested_quantity=12,
            min_quantity=6,
            step_quantity=6,
            response_required_constraints=["buyer.tax_id"],
            request_supplied_fields=["buyer.tax_id", "buyer.email"],
        )
        self.assertTrue(ok8.allowed)
        bad8 = evaluate_ucp_webhook_signing_namespace_and_sale_basis_guard(
            signed_webhook_headers=["content-digest"],
            webhook_id="wh_001",
            webhook_timestamp=1_792_000_000,
            now_epoch_seconds=1_792_000_050,
            extension_namespace="ucp",
            is_core_ucp_spec_artifact=False,
            requested_quantity=7,
            min_quantity=6,
            step_quantity=6,
            response_required_constraints=["buyer.tax_id"],
            request_supplied_fields=[],
        )
        self.assertFalse(bad8.allowed)
        self.assertEqual(bad8.decision_code, "UCP_WEBHOOK_SIGNING_GATE_INCOMPLETE")

        # UN-09
        ok9 = evaluate_acp_push_rail_and_appointment_scheduling_guard(
            payment_rail_type="pix_push",
            end_to_end_id="E18236120202610211234s0876543210",
            receiver_pix_key="pix:merchant@example.com.br",
            mandate_authorized_payee_key="pix:merchant@example.com.br",
            push_settlement_proof_present=True,
            contains_raw_card_pan=False,
            fulfillment_type="appointment",
            appointment_slot_id="slot_2026_10_22_1000",
            slot_starts_at_epoch=1_792_100_000,
            slot_ends_at_epoch=1_792_103_600,
            slot_hold_expires_at_epoch=1_792_050_000,
            now_epoch_seconds=1_792_049_500,
        )
        self.assertTrue(ok9.allowed)
        bad9 = evaluate_acp_push_rail_and_appointment_scheduling_guard(
            payment_rail_type="pix_push",
            end_to_end_id="",
            receiver_pix_key="pix:attacker@example.com.br",
            mandate_authorized_payee_key="pix:merchant@example.com.br",
            push_settlement_proof_present=False,
            contains_raw_card_pan=False,
            fulfillment_type="appointment",
            appointment_slot_id="slot_2026_10_22_1000",
            slot_starts_at_epoch=1_792_100_000,
            slot_ends_at_epoch=1_792_103_600,
            slot_hold_expires_at_epoch=1_792_040_000,
            now_epoch_seconds=1_792_049_500,
        )
        self.assertFalse(bad9.allowed)
        self.assertEqual(bad9.decision_code, "ACP_PUSH_RAIL_MANDATE_BINDING_INVALID")

        # UN-10
        ok10 = evaluate_acp_governance_binding_offer_expiry_and_order_status_guard(
            uses_static_shared_rak=False,
            delegation_token_principal_id="usr_principal_99",
            delegation_max_amount_minor=50_000,
            checkout_amount_minor=32_000,
            line_item_valid_until_epoch=1_792_050_000,
            now_epoch_seconds=1_792_049_000,
            previous_order_status="shipped",
            next_order_status="delivered",
        )
        self.assertTrue(ok10.allowed)
        bad10 = evaluate_acp_governance_binding_offer_expiry_and_order_status_guard(
            uses_static_shared_rak=True,
            delegation_token_principal_id="",
            delegation_max_amount_minor=10_000,
            checkout_amount_minor=32_000,
            line_item_valid_until_epoch=1_792_040_000,
            now_epoch_seconds=1_792_049_000,
            previous_order_status="delivered",
            next_order_status="shipped",
        )
        self.assertFalse(bad10.allowed)
        self.assertEqual(bad10.decision_code, "ACP_STATIC_RAK_WITHOUT_DELEGATION_BINDING")

    def test_ap2_mcp_stripe_tap_tau2_guards_un11_to_un16(self) -> None:
        # UN-11
        ok11 = evaluate_ap2_verified_merchant_and_dispute_archive_guard(
            merchant_registry_verified=True,
            merchant_legal_status="active",
            matched_on_mutable_display_name_only=False,
            merchant_registry_id="gleif:5493001KJTIIGC8Y1R12",
            allowed_payee_registry_ids=["gleif:5493001KJTIIGC8Y1R12"],
            dispute_bundle_has_sd_jwt_and_disclosures=True,
            dispute_bundle_has_pinned_issuer_jwks_snapshot=True,
            dispute_bundle_has_timestamp_authority_proof=True,
            retention_horizon_years=7,
            pact_escrow_pod_verified=True,
        )
        self.assertTrue(ok11.allowed)
        bad11 = evaluate_ap2_verified_merchant_and_dispute_archive_guard(
            merchant_registry_verified=False,
            merchant_legal_status="suspended",
            matched_on_mutable_display_name_only=True,
            merchant_registry_id="unverified",
            allowed_payee_registry_ids=["gleif:5493001KJTIIGC8Y1R12"],
            dispute_bundle_has_sd_jwt_and_disclosures=True,
            dispute_bundle_has_pinned_issuer_jwks_snapshot=False,
            dispute_bundle_has_timestamp_authority_proof=False,
            retention_horizon_years=1,
            pact_escrow_pod_verified=False,
        )
        self.assertFalse(bad11.allowed)
        self.assertEqual(bad11.decision_code, "AP2_MERCHANT_REGISTRY_IDENTITY_UNVERIFIED")

        # UN-12
        cart_payload = {"cart_id": "cart_77", "items": [{"sku": "sku_1", "qty": 2}], "total_minor": 9800}
        cart_hash = hashlib.sha256(
            json.dumps(cart_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        ok12 = evaluate_ap2_line_items_wildcard_and_wba_entropy_guard(
            revealed_acceptable_items=["sku_1", "sku_2"],
            selected_item_id="sku_1",
            mandated_quantity=2,
            actual_checkout_quantity=2,
            checkout_jws_alg="EdDSA",
            checkout_nonce_entropy_bits=128,
            cart_mandate_payload=cart_payload,
            payment_mandate_cart_hash=cart_hash,
        )
        self.assertTrue(ok12.allowed)
        bad12 = evaluate_ap2_line_items_wildcard_and_wba_entropy_guard(
            revealed_acceptable_items=[],
            selected_item_id="sku_any",
            mandated_quantity=2,
            actual_checkout_quantity=1,
            checkout_jws_alg="EdDSA",
            checkout_nonce_entropy_bits=64,
            cart_mandate_payload=cart_payload,
            payment_mandate_cart_hash="deadbeef",
        )
        self.assertFalse(bad12.allowed)
        self.assertEqual(bad12.decision_code, "AP2_EMPTY_ACCEPTABLE_ITEMS_WILDCARD_FORBIDDEN")

        # UN-13
        ok13 = evaluate_mcp_sync_dispatch_freshness_and_retry_guard(
            guardrail_evaluated_synchronously_before_dispatch=True,
            concurrent_dispatch_overlap_detected=False,
            token_cryptographically_valid=True,
            upstream_delegation_revoked_in_trust_domain=False,
            is_mutating_tool_call=True,
            prior_response_lost_after_effect=True,
            retry_uses_new_request_id_without_idempotency_key=False,
            stdio_bridge_oauth_discovery_target_is_loopback_or_metadata_ip=False,
        )
        self.assertTrue(ok13.allowed)
        bad13 = evaluate_mcp_sync_dispatch_freshness_and_retry_guard(
            guardrail_evaluated_synchronously_before_dispatch=False,
            concurrent_dispatch_overlap_detected=True,
            token_cryptographically_valid=True,
            upstream_delegation_revoked_in_trust_domain=True,
            is_mutating_tool_call=True,
            prior_response_lost_after_effect=True,
            retry_uses_new_request_id_without_idempotency_key=True,
            stdio_bridge_oauth_discovery_target_is_loopback_or_metadata_ip=False,
        )
        self.assertFalse(bad13.allowed)
        self.assertEqual(bad13.decision_code, "MCP_CONCURRENT_TOOL_DISPATCH_OVERLAP_BLOCKED")

        # UN-14
        ok14 = evaluate_stripe_order_summary_and_model_id_guard(
            uses_indexed_product_map=True,
            cart_item_count=250,
            catalog_product_count=10_000,
            model_id="claude-opus-4.6",
            resolved_max_tokens=16_384,
            dxt_manifest_all_tools_have_descriptions=True,
            agent_identity_bound_to_tool_scope=True,
        )
        self.assertTrue(ok14.allowed)
        bad14 = evaluate_stripe_order_summary_and_model_id_guard(
            uses_indexed_product_map=False,
            cart_item_count=250,
            catalog_product_count=10_000,
            model_id="claude-opus-4.6",
            resolved_max_tokens=None,
            dxt_manifest_all_tools_have_descriptions=False,
            agent_identity_bound_to_tool_scope=False,
        )
        self.assertFalse(bad14.allowed)
        self.assertEqual(bad14.decision_code, "STRIPE_ORDER_SUMMARY_QUADRATIC_SCAN_BLOCKED")

        # UN-15
        ok15 = evaluate_visa_tap_temporal_authority_and_receipt_guard(
            agent_authorized_at_instruction_creation=True,
            agent_revoked_before_credential_or_commit=False,
            standing_reevaluated_at_commit_boundary=True,
            object_signature_base_canonical_jcs=True,
            body_object_signature_verified=True,
            merchant_signed_transaction_receipt_present=True,
            receipt_bound_to_request_signature_digest=True,
        )
        self.assertTrue(ok15.allowed)
        bad15 = evaluate_visa_tap_temporal_authority_and_receipt_guard(
            agent_authorized_at_instruction_creation=True,
            agent_revoked_before_credential_or_commit=True,
            standing_reevaluated_at_commit_boundary=True,
            object_signature_base_canonical_jcs=False,
            body_object_signature_verified=False,
            merchant_signed_transaction_receipt_present=False,
            receipt_bound_to_request_signature_digest=False,
        )
        self.assertFalse(bad15.allowed)
        self.assertEqual(bad15.decision_code, "VISA_TAP_TEMPORAL_AUTHORITY_REVOKED_AT_COMMIT")

        # UN-16
        ok16 = evaluate_tau2_referral_tasks_sync_and_sandbox_guard(
            undocumented_referral_transferred_to_human=False,
            tasks_json_matches_per_task_files=True,
            tmpdir_path="/var/tmp/tau2_sandbox_kb",
            sandbox_kb_cwd_exists_and_isolated=True,
            discoverable_read_log_filtered_by_reference_actions=False,
        )
        self.assertTrue(ok16.allowed)
        bad16 = evaluate_tau2_referral_tasks_sync_and_sandbox_guard(
            undocumented_referral_transferred_to_human=True,
            tasks_json_matches_per_task_files=False,
            tmpdir_path="/dev/shm/agentic_search_1",
            sandbox_kb_cwd_exists_and_isolated=False,
            discoverable_read_log_filtered_by_reference_actions=True,
        )
        self.assertFalse(bad16.allowed)
        self.assertEqual(bad16.decision_code, "TAU2_UNDOCUMENTED_REFERRAL_FALSE_TRANSFER")


if __name__ == "__main__":
    unittest.main()
