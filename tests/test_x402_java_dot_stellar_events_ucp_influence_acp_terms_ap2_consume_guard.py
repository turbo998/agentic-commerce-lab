"""Unit tests for Stage 144 deterministic guardrails."""

from __future__ import annotations

import unittest

from lab.x402_java_dot_stellar_events_ucp_influence_acp_terms_ap2_consume_guard import (
    compute_acp_checkout_terms_digest,
    evaluate_acp_3ds_terms_digest_binding_guard,
    evaluate_acp_mcp_mutating_idempotency_and_default_delivery_guard,
    evaluate_ap2_closed_mandate_single_use_and_receipt_guard,
    evaluate_ap2_instrument_type_psp_key_and_token_rollback_guard,
    evaluate_mcp_stateless_error_codes_and_self_reported_info_guard,
    evaluate_stripe_mcp_resource_templates_and_model_spend_guard,
    evaluate_tau2_thought_signature_seed_and_order_invariant_guard,
    evaluate_ucp_at_property_local_currency_guard,
    evaluate_ucp_browser_cart_continuation_guard,
    evaluate_ucp_commercial_influence_provenance_guard,
    evaluate_ucp_invoice_and_sepa_debit_instrument_guard,
    evaluate_visa_tap_signed_receipt_and_commit_state_guard,
    evaluate_x402_facilitator_tiered_body_limit_guard,
    evaluate_x402_java_decode_before_dot_segment_guard,
    evaluate_x402_min_deposit_and_facilitator_timeout_guard,
    evaluate_x402_stellar_soroban_emitter_event_guard,
)


class Stage144GuardTests(unittest.TestCase):
    def test_x402_java_stellar_body_limit_and_min_deposit_guards(self) -> None:
        dot = evaluate_x402_java_decode_before_dot_segment_guard(
            raw_request_path="/public/%2e%2e/private/resource"
        )
        self.assertTrue(dot["requires_payment"])
        self.assertTrue(dot["bypass_blocked"])
        self.assertEqual(dot["normalized_path"], "/private/resource")

        root_clamp = evaluate_x402_java_decode_before_dot_segment_guard(
            raw_request_path="/%2e%2e/private"
        )
        self.assertTrue(root_clamp["clamped_above_root"])
        self.assertTrue(root_clamp["requires_payment"])

        stellar_ok = evaluate_x402_stellar_soroban_emitter_event_guard(
            requirements_asset="CASSET_USDC",
            expected_sender="GSENDER",
            expected_recipient="GRECIPIENT",
            expected_amount=5000,
            events=[
                {"emitter_id": "CSMART_ACCOUNT", "topic": "mint", "amount": 5000},
                {
                    "emitter_id": "CASSET_USDC",
                    "topic": "transfer",
                    "sender": "GSENDER",
                    "recipient": "GRECIPIENT",
                    "amount": 5000,
                },
            ],
        )
        self.assertTrue(stellar_ok["allowed"])
        self.assertEqual(stellar_ok["foreign_informational_count"], 1)

        stellar_bad = evaluate_x402_stellar_soroban_emitter_event_guard(
            requirements_asset="CASSET_USDC",
            expected_sender="GSENDER",
            expected_recipient="GRECIPIENT",
            expected_amount=5000,
            events=[
                {
                    "emitter_id": "CASSET_USDC",
                    "topic": "transfer",
                    "sender": "GSENDER",
                    "recipient": "GRECIPIENT",
                    "amount": 5000,
                },
                {"emitter_id": "CASSET_USDC", "topic": "clawback", "amount": 5000},
            ],
        )
        self.assertFalse(stellar_bad["allowed"])

        body_bad = evaluate_x402_facilitator_tiered_body_limit_guard(
            endpoint_kind="verify",
            chunks_byte_lengths=[600_000, 600_000],
        )
        self.assertFalse(body_bad["allowed"])
        self.assertEqual(body_bad["reason"], "X402_FACILITATOR_RESPONSE_BODY_LIMIT_EXCEEDED")

        bazaar_ok = evaluate_x402_facilitator_tiered_body_limit_guard(
            endpoint_kind="bazaar",
            chunks_byte_lengths=[1_500_000, 1_500_000],
        )
        self.assertTrue(bazaar_ok["allowed"])

        dep_ok = evaluate_x402_min_deposit_and_facilitator_timeout_guard(
            amount_atomic=100,
            server_min_deposit_hint=1200,
            enforce_min_deposit=False,
            spend_cap_per_payment=100,
            deposit_multiplier=10,
        )
        self.assertTrue(dep_ok["allowed"])
        self.assertEqual(dep_ok["sized_deposit_atomic"], 1000)

        dep_bad = evaluate_x402_min_deposit_and_facilitator_timeout_guard(
            amount_atomic=100,
            server_min_deposit_hint=1200,
            enforce_min_deposit=True,
            spend_cap_per_payment=100,
            deposit_multiplier=10,
        )
        self.assertFalse(dep_bad["allowed"])
        self.assertEqual(dep_bad["reason"], "X402_MIN_DEPOSIT_EXCEEDS_CLAMPED_SPEND_CAP")

    def test_ucp_and_acp_guards(self) -> None:
        base_assertion = {
            "extension_id": "io.github.arjun2075.shopping.commercial_influence",
            "subject_id": "sku_99",
            "influencer_id": "ad_net_1",
            "asserter_id": "merchant_1",
            "intervention_type": "sponsored_rank_boost",
            "effect": "rank_delta_+3",
            "reason_code": "CAMPAIGN_2026Q4",
        }
        stages = [
            {"stage": s, "assertion": dict(base_assertion)}
            for s in ("catalog", "offer", "cart", "checkout", "handoff")
        ]
        self.assertTrue(
            evaluate_ucp_commercial_influence_provenance_guard(stage_projections=stages)["allowed"]
        )
        stages[-1]["assertion"]["subject_id"] = "sku_tampered"
        self.assertFalse(
            evaluate_ucp_commercial_influence_provenance_guard(stage_projections=stages)["allowed"]
        )

        self.assertTrue(
            evaluate_ucp_browser_cart_continuation_guard(
                native_browser_cart_id="bcart_1",
                existing_ucp_cart_id="ucart_1",
                resolved_ucp_cart_id="ucart_1",
                verifier_bound_proof_valid=True,
                rebuilt_from_agent_item_list=False,
                raw_browser_cookie_forwarded=False,
            )["allowed"]
        )
        self.assertFalse(
            evaluate_ucp_browser_cart_continuation_guard(
                native_browser_cart_id="bcart_1",
                existing_ucp_cart_id="ucart_1",
                resolved_ucp_cart_id="ucart_1",
                verifier_bound_proof_valid=True,
                rebuilt_from_agent_item_list=True,
                raw_browser_cookie_forwarded=False,
            )["allowed"]
        )

        self.assertTrue(
            evaluate_ucp_invoice_and_sepa_debit_instrument_guard(
                instrument={
                    "type": "invoice",
                    "invoice_recipient": "Acme GmbH",
                    "vat_id": "DE123456789",
                    "amount_charged_at_completion": 0,
                }
            )["allowed"]
        )
        self.assertFalse(
            evaluate_ucp_invoice_and_sepa_debit_instrument_guard(
                instrument={
                    "type": "sepa_debit",
                    "iban": "DE89370400440532013000",
                    "account_holder": "Acme GmbH",
                    "mandate_text_hash": "sha256:abc",
                    "mandate_accepted": False,
                }
            )["allowed"]
        )

        self.assertTrue(
            evaluate_ucp_at_property_local_currency_guard(
                booking_currency="EUR",
                property_local_currency="JPY",
                schedule_item={
                    "type": "at_property",
                    "local_amount": {"currency": "JPY", "amount_minor": 400},
                    "booking_amount": {"currency": "EUR", "amount_minor": 245},
                },
                included_in_online_capture_minor=0,
            )["allowed"]
        )

        terms = {
            "checkout_session_id": "cs_1",
            "merchant_id": "m_1",
            "currency": "USD",
            "total_minor": 12500,
            "line_items": [{"id": "li_1", "qty": 1}],
        }
        digest = compute_acp_checkout_terms_digest(terms)
        self.assertTrue(
            evaluate_acp_3ds_terms_digest_binding_guard(
                checkout_terms=terms,
                authentication_result={"terms_digest": digest},
            )["allowed"]
        )
        self.assertFalse(
            evaluate_acp_3ds_terms_digest_binding_guard(
                checkout_terms=terms,
                authentication_result={"terms_digest": "sha256:wrong"},
            )["allowed"]
        )

        self.assertTrue(
            evaluate_acp_mcp_mutating_idempotency_and_default_delivery_guard(
                tool_name="update_checkout_session",
                meta={"api_version": "2026-08-25", "idempotency_key": "idem_1"},
                fulfillment_options=[{"id": "ship_std", "amount": 500}],
                selected_fulfillment_options=["ship_std"],
                totals=[{"type": "fulfillment", "amount": 500}],
            )["allowed"]
        )
        self.assertFalse(
            evaluate_acp_mcp_mutating_idempotency_and_default_delivery_guard(
                tool_name="update_checkout_session",
                meta={"api_version": "2026-08-25"},
                fulfillment_options=[{"id": "ship_std", "amount": 500}],
                selected_fulfillment_options=["ship_std"],
                totals=[{"type": "fulfillment", "amount": 500}],
            )["allowed"]
        )

    def test_ap2_mcp_stripe_tap_and_tau2_guards(self) -> None:
        consumed: set[str] = set()
        first = evaluate_ap2_closed_mandate_single_use_and_receipt_guard(
            closed_mandate_hash="mandate_h1",
            consumed_mandate_hashes=consumed,
            receipt={
                "status": "Success",
                "iss": "did:web:mpp.example",
                "iat": 1792600000,
                "reference": "mandate_h1",
            },
            rail_settlement_evidence={
                "rail_settled": True,
                "psp_confirmation_id": "psp_tx_9001",
                "is_generated_uuid_stub": False,
            },
        )
        self.assertTrue(first["allowed"])
        replay = evaluate_ap2_closed_mandate_single_use_and_receipt_guard(
            closed_mandate_hash="mandate_h1",
            consumed_mandate_hashes=consumed,
            receipt={
                "status": "Success",
                "iss": "did:web:mpp.example",
                "iat": 1792600005,
                "reference": "mandate_h1",
            },
            rail_settlement_evidence={
                "rail_settled": True,
                "psp_confirmation_id": "psp_tx_9002",
                "is_generated_uuid_stub": False,
            },
        )
        self.assertFalse(replay["allowed"])
        self.assertEqual(replay["reason"], "AP2_CLOSED_MANDATE_REPLAY_DETECTED")

        token_entry = {"used": True}
        inst_bad = evaluate_ap2_instrument_type_psp_key_and_token_rollback_guard(
            allowed_payment_instruments=[{"id": "shared-id", "type": "card"}],
            selected_instrument={"id": "shared-id", "type": "bank_account"},
            agent_provider_pub_loaded=True,
            psp_settlement_succeeded=True,
            token_store_entry=token_entry,
        )
        self.assertFalse(inst_bad["allowed"])
        self.assertFalse(token_entry["used"])

        mcp_bad = evaluate_mcp_stateless_error_codes_and_self_reported_info_guard(
            header_mismatch_detected=True,
            proposed_error_code=-32001,
            request_meta={},
            security_decision_uses_client_or_server_info=False,
        )
        self.assertFalse(mcp_bad["allowed"])

        stripe_ok = evaluate_stripe_mcp_resource_templates_and_model_spend_guard(
            resources_capability_advertised=True,
            resource_templates_list_supported=True,
            raw_model_id="anthropic/claude-3-7-sonnet-20250115",
            agent_signature_valid=True,
            tx_amount_minor=5000,
            daily_spent_minor=10000,
            per_tx_limit_minor=10000,
            daily_limit_minor=50000,
        )
        self.assertTrue(stripe_ok["allowed"])
        self.assertEqual(stripe_ok["resolved_max_tokens"], 64000)

        tap_state = {"amount_minor": 4500, "currency": "USD", "merchant_domain": "shop.example"}
        tap_ok = evaluate_visa_tap_signed_receipt_and_commit_state_guard(
            tap_request_signature="sig_tap_1",
            commit_economic_state=tap_state,
            merchant_receipt={
                "tap_request_signature": "sig_tap_1",
                "commit_state_hash": evaluate_visa_tap_signed_receipt_and_commit_state_guard(
                    tap_request_signature="sig_tap_1",
                    commit_economic_state=tap_state,
                    merchant_receipt={
                        "tap_request_signature": "sig_tap_1",
                        "commit_state_hash": "",
                        "merchant_signature": "msig",
                        "timestamp": 1,
                    },
                    treat_tap_verification_as_settlement_truth=False,
                ).get("commit_state_hash", ""),
                "merchant_signature": "msig_1",
                "timestamp": 1792600000,
            },
            treat_tap_verification_as_settlement_truth=False,
        )
        # Re-run with computed hash:
        from lab.x402_java_dot_stellar_events_ucp_influence_acp_terms_ap2_consume_guard import _canonical_sha256
        tap_ok = evaluate_visa_tap_signed_receipt_and_commit_state_guard(
            tap_request_signature="sig_tap_1",
            commit_economic_state=tap_state,
            merchant_receipt={
                "tap_request_signature": "sig_tap_1",
                "commit_state_hash": _canonical_sha256(tap_state),
                "merchant_signature": "msig_1",
                "timestamp": 1792600000,
            },
            treat_tap_verification_as_settlement_truth=False,
        )
        self.assertTrue(tap_ok["allowed"])

        tau2_ok = evaluate_tau2_thought_signature_seed_and_order_invariant_guard(
            tool_call={
                "id": "call_1",
                "provider_specific_fields": {"thought_signature": "sig_xyz"},
            },
            provider="gemini",
            seed=None,
            litellm_drop_params=False,
            gold_action_args={"item_ids": ["b", "a"]},
            candidate_action_args={"item_ids": ["a", "b"]},
            gold_payment_history=[{"id": "p2", "amt": 10}, {"id": "p1", "amt": 20}],
            candidate_payment_history=[{"id": "p1", "amt": 20}, {"id": "p2", "amt": 10}],
        )
        self.assertTrue(tau2_ok["allowed"])


if __name__ == "__main__":
    unittest.main()
