"""Unit tests for Stage 150 guardrails (RL-01..RL-16)."""

from __future__ import annotations

import unittest

from lab.x402_replay_lnbtc_ucp_digital_dest_acp_seller_ap2_trust_tau2_guard import (
    evaluate_acp_message_refund_risk_and_session_state_guard,
    evaluate_acp_seller_backed_crypto_sale_and_trace_guard,
    evaluate_ap2_did_stark_a2a_roles_and_receipt_guard,
    evaluate_ap2_settlement_attestation_trust_query_and_zkp_guard,
    evaluate_mcp_safe_integer_schema_and_result_type_guard,
    evaluate_stripe_ai_empty_choices_routing_and_ua_guard,
    evaluate_tau2_one_to_one_actions_retail_telecom_airline_guard,
    evaluate_ucp_a2a_freeze_mcp_complete_and_common_payment_guard,
    evaluate_ucp_array_elision_and_loyalty_invariant_guard,
    evaluate_ucp_digital_delivery_and_omit_annotations_guard,
    evaluate_ucp_method_destination_and_location_context_guard,
    evaluate_visa_tap_hybrid_pqc_and_x402_guard,
    evaluate_x402_builder_metadata_cors_and_error_body_guard,
    evaluate_x402_lnbtc_exact_and_btc_psbt_guard,
    evaluate_x402_on_after_verify_replay_and_head_guard,
    evaluate_x402_svm_batch_commit_order_guard,
    jcs_sha256_hex,
)


class Stage150GuardTests(unittest.TestCase):
    def test_rl01_to_rl04_x402_guards(self) -> None:
        claimed: set[str] = set()
        # RL-01: HEAD without payment blocked, then valid claim succeeds, then replay blocked
        head_bypass = evaluate_x402_on_after_verify_replay_and_head_guard(
            http_method="HEAD",
            route_requires_payment=True,
            has_payment_signature=False,
            verify_is_valid=False,
            scheme_type="eip3009",
            network="eip155:8453",
            asset="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            payer_from="0xabc",
            nonce="0x01",
            claimed_authorizations=claimed,
        )
        self.assertFalse(head_bypass.allowed)
        self.assertEqual(head_bypass.code, "X402_HEAD_OR_GET_PAYMENT_REQUIRED_402")

        first_claim = evaluate_x402_on_after_verify_replay_and_head_guard(
            http_method="GET",
            route_requires_payment=True,
            has_payment_signature=True,
            verify_is_valid=True,
            scheme_type="eip3009",
            network="eip155:8453",
            asset="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            payer_from="0xabc",
            nonce="0x01",
            claimed_authorizations=claimed,
        )
        self.assertTrue(first_claim.allowed)

        dup_claim = evaluate_x402_on_after_verify_replay_and_head_guard(
            http_method="GET",
            route_requires_payment=True,
            has_payment_signature=True,
            verify_is_valid=True,
            scheme_type="eip3009",
            network="eip155:8453",
            asset="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            payer_from="0xabc",
            nonce="0x01",
            claimed_authorizations=claimed,
        )
        self.assertFalse(dup_claim.allowed)
        self.assertEqual(dup_claim.code, "payment_replayed")

        # RL-02: SVM batch commit ordering
        completed_ops: set[str] = set()
        premature = evaluate_x402_svm_batch_commit_order_guard(
            operation_id="op_1",
            channel_id="ch_1",
            charge_amount_atomic=500,
            available_channel_balance_atomic=1000,
            complete_called_inside_channel_update_callback=True,
            channel_write_succeeded=True,
            completed_operation_ids=completed_ops,
        )
        self.assertFalse(premature.allowed)

        ok_batch = evaluate_x402_svm_batch_commit_order_guard(
            operation_id="op_1",
            channel_id="ch_1",
            charge_amount_atomic=500,
            available_channel_balance_atomic=1000,
            complete_called_inside_channel_update_callback=False,
            channel_write_succeeded=True,
            completed_operation_ids=completed_ops,
        )
        self.assertTrue(ok_batch.allowed)

        # RL-03: lnbtc exact & BTC PSBT
        preimage_hex = "11" * 32
        import hashlib
        pay_hash = hashlib.sha256(bytes.fromhex(preimage_hex)).hexdigest()
        req_desc = {"method": "POST", "target": "/v1/infer", "body_sha256": "aa" * 32}
        desc_hash = jcs_sha256_hex({"profile": "http:1", "request": req_desc})
        consumed_ln: set[str] = set()

        bad_header = evaluate_x402_lnbtc_exact_and_btc_psbt_guard(
            network="lnbtc:mainnet",
            preimage_hex=preimage_hex,
            invoice_payment_hash_hex=pay_hash,
            binding_profile="http:1",
            canonical_request_descriptor=req_desc,
            invoice_description_hash_hex=desc_hash,
            header_lines=["host: api.example.com\r\nx-injected: 1"],
            consumed_payment_hashes=consumed_ln,
            btc_batch_psbt_signers=["cosigner_1", "cosigner_2"],
        )
        self.assertFalse(bad_header.allowed)

        ok_ln = evaluate_x402_lnbtc_exact_and_btc_psbt_guard(
            network="lnbtc:mainnet",
            preimage_hex=preimage_hex,
            invoice_payment_hash_hex=pay_hash,
            binding_profile="http:1",
            canonical_request_descriptor=req_desc,
            invoice_description_hash_hex=desc_hash,
            header_lines=["host: api.example.com"],
            consumed_payment_hashes=consumed_ln,
            btc_batch_psbt_signers=["cosigner_1", "cosigner_2"],
        )
        self.assertTrue(ok_ln.allowed)

        # RL-04: Builder metadata 'm', CORS expose headers & non-JSON body preservation
        bad_m = evaluate_x402_builder_metadata_cors_and_error_body_guard(
            client_payload_builder_code={"a": "builder_1", "m": {"x402ChargeCounts": 5}},
            facilitator_settlement_metadata={"x402ChargeCounts": 1},
            response_payment_headers=["PAYMENT-REQUIRED"],
            access_control_expose_headers=["PAYMENT-REQUIRED", "PAYMENT-RESPONSE"],
            custom_unpaid_body="Pay 100 sats to continue",
            declared_content_type="text/plain; charset=utf-8",
            serialized_response_body="Pay 100 sats to continue",
        )
        self.assertFalse(bad_m.allowed)

        ok_m = evaluate_x402_builder_metadata_cors_and_error_body_guard(
            client_payload_builder_code={"a": "builder_1"},
            facilitator_settlement_metadata={"x402ChargeCounts": 1},
            response_payment_headers=["PAYMENT-REQUIRED"],
            access_control_expose_headers=["PAYMENT-REQUIRED", "PAYMENT-RESPONSE"],
            custom_unpaid_body="Pay 100 sats to continue",
            declared_content_type="text/plain; charset=utf-8",
            serialized_response_body="Pay 100 sats to continue",
        )
        self.assertTrue(ok_m.allowed)

    def test_rl05_to_rl10_ucp_and_acp_guards(self) -> None:
        # RL-05
        bad_dd = evaluate_ucp_digital_delivery_and_omit_annotations_guard(
            attachment_target="checkout",
            digital_delivery_payload={"kind": "redeemable_artifact", "code": "GIFT-123"},
            operation="complete_checkout",
            request_payload={},
        )
        self.assertFalse(bad_dd.allowed)

        ok_dd = evaluate_ucp_digital_delivery_and_omit_annotations_guard(
            attachment_target="order",
            digital_delivery_payload={"kind": "redeemable_artifact", "code": "GIFT-123"},
            operation="complete_checkout",
            request_payload={"payment": {"id": "pay_1"}},
        )
        self.assertTrue(ok_dd.allowed)

        # RL-06
        bad_pickup = evaluate_ucp_method_destination_and_location_context_guard(
            direction="request",
            method_type="pickup",
            destination={"type": "pickup_location", "address": "123 St"},
            selected_destination_id="loc_1",
            context_location={"postal_code": "94105"},
            auto_selected_from_context_location=False,
        )
        self.assertFalse(bad_pickup.allowed)

        ok_shipping = evaluate_ucp_method_destination_and_location_context_guard(
            direction="request",
            method_type="shipping",
            destination={"street": "1 Market St"},
            selected_destination_id=None,
            context_location={"postal_code": "94105"},
            auto_selected_from_context_location=False,
        )
        self.assertTrue(ok_shipping.allowed)

        # RL-07
        frozen = evaluate_ucp_a2a_freeze_mcp_complete_and_common_payment_guard(
            transport="a2a",
            checkout_status="complete_in_progress",
            action_verb="add_to_checkout",
            mcp_complete_extensions=["dev.ucp.shopping.buyer_consent"],
            schema_refs=["common/ap2_mandate.json"],
        )
        self.assertFalse(frozen.allowed)

        ok_a2a = evaluate_ucp_a2a_freeze_mcp_complete_and_common_payment_guard(
            transport="a2a",
            checkout_status="ready_for_complete",
            action_verb="complete_checkout",
            mcp_complete_extensions=["dev.ucp.shopping.buyer_consent", "dev.ucp.common.payment.ap2_mandate"],
            schema_refs=["common/ap2_mandate.json", "common/split_payments.json"],
        )
        self.assertTrue(ok_a2a.allowed)

        # RL-08
        bad_loyalty = evaluate_ucp_array_elision_and_loyalty_invariant_guard(
            raw_items_array=["...", {"__elided__": True}, {"id": "item_2"}],
            validation_error_post_strip_indices=[0],
            loyalty_discount_amount_minor=10,
            stated_dollar_benefit=10.0,
            earning_forecast_total_minor=500,
            earning_forecast_breakdown_minor=[300, 200],
        )
        self.assertFalse(bad_loyalty.allowed)

        ok_loyalty = evaluate_ucp_array_elision_and_loyalty_invariant_guard(
            raw_items_array=["...", {"__elided__": True}, {"id": "item_2"}],
            validation_error_post_strip_indices=[0],
            loyalty_discount_amount_minor=1000,
            stated_dollar_benefit=10.0,
            earning_forecast_total_minor=500,
            earning_forecast_breakdown_minor=[300, 200],
        )
        self.assertTrue(ok_loyalty.allowed)

        # RL-09
        bad_msg = evaluate_acp_message_refund_risk_and_session_state_guard(
            message_obj={"id": "m1", "type": "error", "message": "bad"},
            refund_amount="1.00",
            risk_signals=[],
            session_status="pending_approval",
        )
        self.assertFalse(bad_msg.allowed)

        ok_msg = evaluate_acp_message_refund_risk_and_session_state_guard(
            message_obj={"type": "intervention_required", "code": "3ds_challenge", "content": "Complete 3DS challenge"},
            refund_amount=100,
            risk_signals=[],
            session_status="pending_approval",
        )
        self.assertTrue(ok_msg.allowed)

        # RL-10
        bad_seller = evaluate_acp_seller_backed_crypto_sale_and_trace_guard(
            handler_id="dev.acp.seller_backed.saved_card",
            agent_received_raw_credential=True,
            display_order=1,
            display_name="Saved Visa",
            onchain_discount_wallet_verified=True,
            discount_expires_at_epoch=2000,
            now_epoch=1500,
            intent_trace_reason_code="price_too_high",
            content_citations=[{"source_url": "https://reviews.example/1", "publisher_id": "pub_1"}],
        )
        self.assertFalse(bad_seller.allowed)

        ok_seller = evaluate_acp_seller_backed_crypto_sale_and_trace_guard(
            handler_id="dev.acp.seller_backed.saved_card",
            agent_received_raw_credential=False,
            display_order=1,
            display_name="Saved Visa",
            onchain_discount_wallet_verified=True,
            discount_expires_at_epoch=2000,
            now_epoch=1500,
            intent_trace_reason_code="price_too_high",
            content_citations=[{"source_url": "https://reviews.example/1", "publisher_id": "pub_1"}],
        )
        self.assertTrue(ok_seller.allowed)

    def test_rl11_to_rl16_ap2_mcp_stripe_tap_tau2_guards(self) -> None:
        # RL-11
        mandate = {"mandate_id": "pm_1", "amount_minor": 4500, "currency": "USD"}
        ref = f"sha256:{jcs_sha256_hex(mandate)}"
        bad_trust = evaluate_ap2_settlement_attestation_trust_query_and_zkp_guard(
            settlement_state="SETTLED",
            payment_mandate_payload=mandate,
            settled_payment_ref=ref,
            trust_verdict="INSUFFICIENT_EVIDENCE",
            issuer_references=["sha256:1111"],
            zkp_receipt_payload_hash="zkp_hash_1",
            expected_session_spend_hash="zkp_hash_1",
        )
        self.assertFalse(bad_trust.allowed)

        ok_trust = evaluate_ap2_settlement_attestation_trust_query_and_zkp_guard(
            settlement_state="SETTLED",
            payment_mandate_payload=mandate,
            settled_payment_ref=ref,
            trust_verdict="TRUSTED",
            issuer_references=["sha256:1111", "sha256:2222"],
            zkp_receipt_payload_hash="zkp_hash_1",
            expected_session_spend_hash="zkp_hash_1",
        )
        self.assertTrue(ok_trust.allowed)

        # RL-12
        ok_did = evaluate_ap2_did_stark_a2a_roles_and_receipt_guard(
            subject_did="did:tenzro:agent_01",
            stark_commitment_verified=True,
            attested_a2a_roles={
                "ShoppingAgent",
                "CredentialsProviderAgent",
                "MerchantAgent",
                "MerchantPaymentProcessorAgent",
            },
            sd_jwt_delegation_chain_valid=True,
            payment_receipt={
                "receipt_id": "rcpt_1",
                "payment_mandate_hash": ref,
                "amount_minor": 4500,
                "currency": "USD",
                "processor_timestamp": "2026-10-21T12:00:00Z",
            },
            expected_mandate_hash=ref,
        )
        self.assertTrue(ok_did.allowed)

        # RL-13
        bad_mcp = evaluate_mcp_safe_integer_schema_and_result_type_guard(
            integer_value=(1 << 53) + 7,
            generated_schema_bytes_len=4096,
            generated_symbol_definitions_count=42,
            mrtr_result_type="input_required",
        )
        self.assertFalse(bad_mcp.allowed)

        ok_mcp = evaluate_mcp_safe_integer_schema_and_result_type_guard(
            integer_value=9007199254740991,
            generated_schema_bytes_len=4096,
            generated_symbol_definitions_count=42,
            mrtr_result_type="input_required",
        )
        self.assertTrue(ok_mcp.allowed)

        # RL-14
        empty_choices = evaluate_stripe_ai_empty_choices_routing_and_ua_guard(
            provider_response_choices=[],
            user_intent_kind="provision_or_manage_resource",
            routed_skill="stripe-projects",
            mcp_user_agent_version="0.3.3",
            package_json_version="0.3.3",
            checkout_form_target_path="/purchase",
        )
        self.assertFalse(empty_choices.allowed)
        self.assertEqual(empty_choices.code, "NoContentGeneratedError")

        ok_stripe = evaluate_stripe_ai_empty_choices_routing_and_ua_guard(
            provider_response_choices=[{"message": {"content": "ok"}}],
            user_intent_kind="provision_or_manage_resource",
            routed_skill="stripe-projects",
            mcp_user_agent_version="0.3.3",
            package_json_version="0.3.3",
            checkout_form_target_path="/purchase",
        )
        self.assertTrue(ok_stripe.allowed)

        # RL-15
        bad_tap = evaluate_visa_tap_hybrid_pqc_and_x402_guard(
            alg="ed25519-ml-dsa-65",
            signature_bytes_len=3373,
            public_key_bytes_len=1952,
            ed25519_leg_valid=True,
            mldsa65_leg_valid=False,
            did_resolved_via_explicit_registry=True,
            x402_settlement_digest="sha256:abcd",
            tap_rfc9421_request_digest="sha256:abcd",
        )
        self.assertFalse(bad_tap.allowed)

        ok_tap = evaluate_visa_tap_hybrid_pqc_and_x402_guard(
            alg="ed25519-ml-dsa-65",
            signature_bytes_len=3373,
            public_key_bytes_len=1952,
            ed25519_leg_valid=True,
            mldsa65_leg_valid=True,
            did_resolved_via_explicit_registry=True,
            x402_settlement_digest="sha256:abcd",
            tap_rfc9421_request_digest="sha256:abcd",
        )
        self.assertTrue(ok_tap.allowed)

        # RL-16
        bad_tau2 = evaluate_tau2_one_to_one_actions_retail_telecom_airline_guard(
            gold_actions=["request_human_agent_transfer"] * 3,
            predicted_tool_calls=["request_human_agent_transfer"],
            retail_exchange_old_item_id="sku_1",
            retail_exchange_new_item_id="sku_2",
            telecom_mmsc_url="http://mms.carrier.example",
            airline_user_id="sara_doe_496",
            telecom_status_bar_tool_name="check_status_bar",
            ended_in_infrastructure_error=False,
        )
        self.assertFalse(bad_tau2.allowed)
        self.assertEqual(bad_tau2.code, "TAU2_GOLD_ACTION_ONE_TO_ONE_MATCH_FAILED")

        ok_tau2 = evaluate_tau2_one_to_one_actions_retail_telecom_airline_guard(
            gold_actions=["request_human_agent_transfer"] * 3,
            predicted_tool_calls=["request_human_agent_transfer"] * 3,
            retail_exchange_old_item_id="sku_1",
            retail_exchange_new_item_id="sku_2",
            telecom_mmsc_url="http://mms.carrier.example",
            airline_user_id="sara_doe_496",
            telecom_status_bar_tool_name="check_status_bar",
            ended_in_infrastructure_error=False,
        )
        self.assertTrue(ok_tau2.allowed)


if __name__ == "__main__":
    unittest.main()
