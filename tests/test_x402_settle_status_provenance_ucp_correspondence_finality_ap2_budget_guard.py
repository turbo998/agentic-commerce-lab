"""Unit tests for Stage 148 deterministic protocol guards (SP-01..SP-16)."""

from __future__ import annotations

import unittest

from lab.x402_settle_status_provenance_ucp_correspondence_finality_ap2_budget_guard import (
    compute_jcs_sha256_hex,
    evaluate_acp_delegate_link_intervention_guard,
    evaluate_acp_store_expiry_and_order_status_guard,
    evaluate_ap2_cross_merchant_budget_authority_guard,
    evaluate_ap2_haggle_and_solana_pay_reference_guard,
    evaluate_mcp_extension_lifecycle_and_sdk_guard,
    evaluate_stripe_link_override_and_projects_guard,
    evaluate_tau2_telecom_live_db_and_banking_sync_guard,
    evaluate_ucp_checkout_payment_finality_guard,
    evaluate_ucp_correspondence_and_agent_signals_guard,
    evaluate_ucp_permalink_and_signature_guard,
    evaluate_ucp_variant_offers_and_schema_guard,
    evaluate_visa_tap_signature_and_provisional_ceiling_guard,
    evaluate_x402_near_intents_builder_svm_guard,
    evaluate_x402_response_provenance_and_sidechannel_guard,
    evaluate_x402_settle_status_vocabulary_guard,
    evaluate_x402_settlement_override_and_min_deposit_guard,
)


class Stage148ProtocolGuardsTest(unittest.TestCase):
    def test_sp01_to_sp04_x402_guards(self) -> None:
        ok_sp01 = evaluate_x402_settle_status_vocabulary_guard(
            status="settled",
            anchor_kind="transaction",
            anchor_ref="0xabc123",
            observation_block_number=21_400_100,
            ledger_time_epoch_s=1_792_550_000,
        )
        self.assertTrue(ok_sp01.allowed)
        bad_sp01 = evaluate_x402_settle_status_vocabulary_guard(
            status="deferred_until",
            anchor_kind="read",
            anchor_ref="0xescrow",
            observation_block_number=21_400_100,
            ledger_time_epoch_s=None,
            error_code="settlement_deferred",
            reader_attempted_delivery_or_unanchored_retry=True,
        )
        self.assertFalse(bad_sp01.allowed)
        self.assertEqual(bad_sp01.reason_code, "X402_NON_TERMINAL_READER_ACTION_FORBIDDEN")

        fp = {
            "endpoint": "https://api.merchant.example/v1/forecast",
            "inputs": {"sku": "SKU-9"},
            "result": {"demand": 42},
            "method": "POST",
            "dataVintage": "2026-10-21T00:00:00Z",
        }
        r_hash = compute_jcs_sha256_hex(fp)
        ok_sp02 = evaluate_x402_response_provenance_and_sidechannel_guard(
            endpoint=fp["endpoint"],
            inputs=fp["inputs"],
            result=fp["result"],
            method="post",
            data_vintage=fp["dataVintage"],
            declared_response_hash=r_hash,
            facilitator_extension_responses={"risk_Sidechannel": {"score": 1}},
            client_payment_response_extensions={"response-provenance": {"responseHash": r_hash}},
        )
        self.assertTrue(ok_sp02.allowed)
        bad_sp02 = evaluate_x402_response_provenance_and_sidechannel_guard(
            endpoint=fp["endpoint"],
            inputs=fp["inputs"],
            result=fp["result"],
            method="POST",
            data_vintage=fp["dataVintage"],
            declared_response_hash=r_hash,
            facilitator_extension_responses={"risk_Sidechannel": {"score": 1}},
            client_payment_response_extensions={"risk_Sidechannel": {"score": 1}},
        )
        self.assertFalse(bad_sp02.allowed)

        ok_sp03 = evaluate_x402_settlement_override_and_min_deposit_guard(
            authorized_amount_atomic=1_000_000,
            override_spec="80%",
            extra_min_deposit_atomic=5_000_000,
            client_max_escrow_atomic=10_000_000,
        )
        self.assertTrue(ok_sp03.allowed)
        self.assertEqual(ok_sp03.resolved_override_atomic, 800_000)
        bad_sp03 = evaluate_x402_settlement_override_and_min_deposit_guard(
            authorized_amount_atomic=1_000_000,
            override_spec="500%",
        )
        self.assertFalse(bad_sp03.allowed)
        self.assertEqual(
            bad_sp03.reason_code,
            "X402_SETTLEMENT_OVERRIDE_EXCEEDS_AUTHORIZED_CEILING",
        )

        ok_sp04 = evaluate_x402_near_intents_builder_svm_guard(
            payment_flow="upfront",
            origin_network="eip155:8453",
            single_use_deposit_address="0xdeposit1",
            facilitator_confirmed_delivery=True,
            server_declared_builder_code_a="app_commerce_01",
            payload_builder_code_a="app_commerce_01",
            svm_instruction_programs=[
                "ComputeBudget111111111111111111111111111111",
                "Lighthouse111111111111111111111111111111111",
                "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
                "Lighthouse111111111111111111111111111111111",
            ],
        )
        self.assertTrue(ok_sp04.allowed)
        bad_sp04 = evaluate_x402_near_intents_builder_svm_guard(
            payment_flow="upfront",
            origin_network="eip155:8453",
            single_use_deposit_address="0xdeposit1",
            facilitator_confirmed_delivery=True,
            server_declared_builder_code_a=None,
            payload_builder_code_a="spoofed_app",
            svm_instruction_programs=["TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"],
        )
        self.assertFalse(bad_sp04.allowed)
        self.assertEqual(bad_sp04.reason_code, "extension_echo_mismatch")

    def test_sp05_to_sp08_ucp_guards(self) -> None:
        ok_sp05 = evaluate_ucp_correspondence_and_agent_signals_guard(
            derived_from_record_id="quote_101",
            derived_from_record_type="quote",
            derived_from_issued_at_s=1_000,
            derived_from_observed_at_s=1_020,
            max_observation_lag_s=60,
            prior_amount_minor=4500,
            current_amount_minor=4500,
            declared_correspondence_status="agrees",
            signals_payload={"dev.ucp.agent_spend_context": {"percentile": 80}},
            agent_amount_minor=15,
            agent_history_p99_minor=25,
            payee_seen_before=True,
        )
        self.assertTrue(ok_sp05.allowed)
        bad_sp05 = evaluate_ucp_correspondence_and_agent_signals_guard(
            derived_from_record_id="quote_101",
            derived_from_record_type="quote",
            derived_from_issued_at_s=1_000,
            derived_from_observed_at_s=1_020,
            max_observation_lag_s=60,
            prior_amount_minor=4500,
            current_amount_minor=4500,
            declared_correspondence_status="agrees",
            signals_payload={"dev.ucp.instruction_provenance": "user_turn"},
            agent_amount_minor=15,
            agent_history_p99_minor=25,
            payee_seen_before=True,
        )
        self.assertFalse(bad_sp05.allowed)

        ok_sp06 = evaluate_ucp_checkout_payment_finality_guard(
            amount_finality="provisional",
            checkout_total_minor=10_000,
            buyer_approved_maximum_minor=12_000,
            order_instrument_payload={
                "id": "pi_1",
                "authorized_amount": 12_000,
                "captured_amount": 11_200,
            },
        )
        self.assertTrue(ok_sp06.allowed)
        bad_sp06 = evaluate_ucp_checkout_payment_finality_guard(
            amount_finality="provisional",
            checkout_total_minor=10_000,
            buyer_approved_maximum_minor=12_000,
            order_instrument_payload={
                "id": "pi_1",
                "authorized_amount": 13_500,
                "captured_amount": 13_500,
            },
        )
        self.assertFalse(bad_sp06.allowed)

        ok_sp07 = evaluate_ucp_variant_offers_and_schema_guard(
            variant_offers=[
                {"id": "off_1", "seller_id": "merch_a", "price_minor": 2999},
                {"id": "off_2", "seller_id": "merch_b", "price_minor": 2799},
            ],
            requested_offer_id="off_2",
            checkout_seller_id="merch_b",
            checkout_price_minor=2799,
            schema_defs_keys=["agent_profile", "transport_binding"],
            continue_url="https://shop.example.com/cart/continue/abc",
            openrpc_embedded_auth_type_required=True,
        )
        self.assertTrue(ok_sp07.allowed)
        bad_sp07 = evaluate_ucp_variant_offers_and_schema_guard(
            variant_offers=[{"id": "off_1", "seller_id": "merch_a", "price_minor": 2999}],
            requested_offer_id="off_1",
            checkout_seller_id="merch_a",
            checkout_price_minor=2999,
            schema_defs_keys=["ucp_agent"],
            continue_url="https://shop.example.com/cart/continue/abc",
            openrpc_embedded_auth_type_required=True,
        )
        self.assertFalse(bad_sp07.allowed)

        ok_sp08 = evaluate_ucp_permalink_and_signature_guard(
            permalink_query_params={"ucp/version": "2026-04-08"},
            authenticated_existing_cart=True,
            explicit_buyer_merge_action=True,
            signed_components=["@authority", "@path", "ucp-agent", "signature-agent"],
            has_signature_agent_header=True,
        )
        self.assertTrue(ok_sp08.allowed)
        bad_sp08 = evaluate_ucp_permalink_and_signature_guard(
            permalink_query_params={"ucp/version": "2026-04-08"},
            authenticated_existing_cart=True,
            explicit_buyer_merge_action=False,
            signed_components=["@authority", "@path", "ucp-agent"],
            has_signature_agent_header=False,
        )
        self.assertFalse(bad_sp08.allowed)

    def test_sp09_to_sp16_acp_ap2_mcp_stripe_visa_tau2_guards(self) -> None:
        ok_sp09 = evaluate_acp_store_expiry_and_order_status_guard(
            fulfillment_type="bopis",
            store_id="store_nyc_01",
            store_inventory_available=True,
            line_item_valid_until_epoch_s=2_000,
            checkout_now_epoch_s=1_800,
            order_status="fulfilled",
        )
        self.assertTrue(ok_sp09.allowed)
        bad_sp09 = evaluate_acp_store_expiry_and_order_status_guard(
            fulfillment_type="digital",
            store_id=None,
            store_inventory_available=False,
            line_item_valid_until_epoch_s=2_000,
            checkout_now_epoch_s=1_800,
            order_status="shipped",
        )
        self.assertFalse(bad_sp09.allowed)

        ok_sp10 = evaluate_acp_delegate_link_intervention_guard(
            http_status=503,
            error_type="internal_server_error",
            error_code="service_unavailable",
            payment_handler_id="com.stripe.link",
            link_authenticated_session_id="link_sess_99",
            intervention_type="otp_sms",
        )
        self.assertTrue(ok_sp10.allowed)
        bad_sp10 = evaluate_acp_delegate_link_intervention_guard(
            http_status=401,
            error_type="invalid_request",
            error_code="unauthorized",
            payment_handler_id="com.stripe.link",
            link_authenticated_session_id="link_sess_99",
            intervention_type="otp_sms",
        )
        self.assertFalse(bad_sp10.allowed)

        ok_sp11 = evaluate_ap2_cross_merchant_budget_authority_guard(
            mandate_budget_minor=10_000,
            operations=[
                {"verb": "authorize", "hold_id": "h1", "amount_minor": 6_000},
                {"verb": "authorize", "hold_id": "h2", "amount_minor": 4_000},
                {"verb": "commit", "hold_id": "h1", "amount_minor": 5_500},
            ],
        )
        self.assertTrue(ok_sp11.allowed)
        self.assertEqual(ok_sp11.remaining_minor, 500)
        bad_sp11 = evaluate_ap2_cross_merchant_budget_authority_guard(
            mandate_budget_minor=10_000,
            operations=[
                {"verb": "authorize", "hold_id": "h1", "amount_minor": 6_000},
                {"verb": "authorize", "hold_id": "h2", "amount_minor": 6_000},
            ],
        )
        self.assertFalse(bad_sp11.allowed)

        ok_sp12 = evaluate_ap2_haggle_and_solana_pay_reference_guard(
            walk_away_price_minor=8_500,
            max_rounds=5,
            deadline_epoch_s=2_000,
            required_terms={"warranty_months": 12},
            offer_price_minor=8_200,
            offer_round=3,
            offer_timestamp_s=1_900,
            offer_terms={"warranty_months": 12},
            solana_pay_reference_pubkey="RefPubkey11111111111111111111111111111111",
            tx_readonly_accounts=["RefPubkey11111111111111111111111111111111"],
            indexed_signatures_for_reference=["5SolSigXyZ"],
        )
        self.assertTrue(ok_sp12.allowed)
        bad_sp12 = evaluate_ap2_haggle_and_solana_pay_reference_guard(
            walk_away_price_minor=8_500,
            max_rounds=5,
            deadline_epoch_s=2_000,
            required_terms={"warranty_months": 12},
            offer_price_minor=8_900,
            offer_round=3,
            offer_timestamp_s=1_900,
            offer_terms={"warranty_months": 12},
            solana_pay_reference_pubkey="RefPubkey11111111111111111111111111111111",
            tx_readonly_accounts=["RefPubkey11111111111111111111111111111111"],
            indexed_signatures_for_reference=["5SolSigXyZ"],
        )
        self.assertFalse(bad_sp12.allowed)

        ok_sp13 = evaluate_mcp_extension_lifecycle_and_sdk_guard(
            repo_name="ext-commerce-telemetry",
            has_breaking_change=False,
            has_extensions_track_sep=False,
            registered_extensions=[
                {"name": "ext_b", "dependencies": ["ext_a", "resources"]},
                {"name": "ext_a", "dependencies": ["tools"]},
            ],
            active_runtime_capabilities=["tools", "resources"],
            protocol_version="2025-11-25",
            negotiated_via_initialize=True,
        )
        self.assertTrue(ok_sp13.allowed)
        bad_sp13 = evaluate_mcp_extension_lifecycle_and_sdk_guard(
            repo_name="ext-commerce-telemetry",
            has_breaking_change=True,
            has_extensions_track_sep=False,
            registered_extensions=[],
            active_runtime_capabilities=["tools"],
            protocol_version="2026-07-28",
            negotiated_via_initialize=False,
        )
        self.assertFalse(bad_sp13.allowed)

        ok_sp14 = evaluate_stripe_link_override_and_projects_guard(
            mandate_maximum_minor=15_000,
            requested_settlement_override_minor=14_200,
            link_session_bound_to_mandate=True,
            projects_cli_preflight_ok=True,
        )
        self.assertTrue(ok_sp14.allowed)
        bad_sp14 = evaluate_stripe_link_override_and_projects_guard(
            mandate_maximum_minor=15_000,
            requested_settlement_override_minor=18_000,
            link_session_bound_to_mandate=True,
            projects_cli_preflight_ok=True,
        )
        self.assertFalse(bad_sp14.allowed)

        ok_sp15 = evaluate_visa_tap_signature_and_provisional_ceiling_guard(
            signed_headers=["@authority", "@path", "payment-token", "ucp-agent", "signature-agent"],
            provisional_maximum_minor=20_000,
            requested_capture_minor=19_500,
            tap_key_id="tap_key_01",
        )
        self.assertTrue(ok_sp15.allowed)
        bad_sp15 = evaluate_visa_tap_signature_and_provisional_ceiling_guard(
            signed_headers=["@authority", "@path", "payment-token"],
            provisional_maximum_minor=20_000,
            requested_capture_minor=19_500,
            tap_key_id="tap_key_01",
        )
        self.assertFalse(bad_sp15.allowed)

        task_102 = {"id": "102", "reward_basis": ["DB", "NL_ASSERTION"]}
        ok_sp16 = evaluate_tau2_telecom_live_db_and_banking_sync_guard(
            telecom_line_status="active",
            refuel_gb=2.0,
            db_mutated_on_rejected_call=False,
            live_db_hash="sha256:live_gold_01",
            replayed_db_hash="sha256:replay_diverged_01",
            expected_gold_db_hash="sha256:live_gold_01",
            injected_fault_mode="timeout_after_commit",
            banking_individual_tasks={"102": task_102},
            banking_aggregate_tasks=[task_102],
        )
        self.assertTrue(ok_sp16.allowed)
        self.assertTrue(ok_sp16.replay_divergence_recorded)
        bad_sp16 = evaluate_tau2_telecom_live_db_and_banking_sync_guard(
            telecom_line_status="suspended",
            refuel_gb=2.0,
            db_mutated_on_rejected_call=True,
            live_db_hash="sha256:live_gold_01",
            replayed_db_hash="sha256:live_gold_01",
            expected_gold_db_hash="sha256:live_gold_01",
            injected_fault_mode="none",
            banking_individual_tasks={"102": task_102},
            banking_aggregate_tasks=[task_102],
        )
        self.assertFalse(bad_sp16.allowed)
        self.assertEqual(bad_sp16.reason_code, "TAU2_INACTIVE_LINE_MUTATED_BILL_OR_DATA")


if __name__ == "__main__":
    unittest.main()
