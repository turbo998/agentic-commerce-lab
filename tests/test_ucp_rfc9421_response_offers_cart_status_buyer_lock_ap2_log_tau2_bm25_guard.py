"""Unit tests for Stage 202 guard module (PR-01..PR-16)."""

from __future__ import annotations

import hashlib
import hmac
import unittest

from lab.ucp_rfc9421_response_offers_cart_status_buyer_lock_ap2_log_tau2_bm25_guard import (
    audit_ap2_selective_disclosure_log_payload,
    evaluate_tau2_airline_task7_other_flights_total,
    evaluate_tau2_bm25_grep_title_aware_retrieval,
    evaluate_tau2_pass_hat_k_infra_error_integrity,
    evaluate_ucp_cart_terminal_status_guard,
    evaluate_ucp_platform_funded_discount_reimbursement,
    evaluate_ucp_state_bound_cart_offer,
    validate_tau2_kb_read_tool_and_write_equivalence,
    validate_tau2_persona_solo_and_simulator_turn,
    validate_ucp_complete_checkout_buyer_lock,
    validate_ucp_instrument_payer_identification,
    validate_ucp_item_snapshot_and_fraud_signals,
    validate_ucp_variant_per_seller_offer_routing,
    validate_x402_verify_eip3009_and_next_402_contract,
    verify_ucp_rfc9421_rest_response_binding,
)


def _sign_rest_response(req: dict, resp: dict, created: int, secret: str) -> str:
    req_body = str(req.get("body", "") or "")
    resp_body = str(resp.get("body", "") or "")
    req_digest = hashlib.sha256(req_body.encode("utf-8")).hexdigest() if req_body else ""
    resp_digest = hashlib.sha256(resp_body.encode("utf-8")).hexdigest() if resp_body else ""
    base = "|".join(
        [
            f"@status:{resp.get('status', 200)}",
            f"@authority;req:{req.get('authority', '')}",
            f"@method;req:{req.get('method', '')}",
            f"@path;req:{req.get('path', '')}",
            f"@query;req:{req.get('query', '')}",
            f"content-digest;req:{req_digest}",
            f"content-digest:{resp_digest}",
            f"content-type:{resp.get('content_type', '')}",
            f"created:{created}",
        ]
    )
    return hmac.new(secret.encode("utf-8"), base.encode("utf-8"), hashlib.sha256).hexdigest()


class TestStage202Guard(unittest.TestCase):
    def test_ucp_rfc9421_response_binding_and_catalog_offers(self) -> None:
        req = {"authority": "merchant.example.com", "method": "GET", "path": "/checkout-sessions/chk_123", "query": "", "body": ""}
        resp = {"status": 200, "body": '{"id":"chk_123","total":6000}', "content_type": "application/json"}
        sig = _sign_rest_response(req, resp, 1738617600, "sec-1")
        comps = ["@status", "@authority;req", "@method;req", "@path;req", "content-digest", "content-type"]

        ok = verify_ucp_rfc9421_rest_response_binding(
            sent_request=req,
            received_response=resp,
            signature_input_components=comps,
            signature_created=1738617600,
            current_timestamp=1738617650,
            provided_signature_hex=sig,
            shared_verification_secret="sec-1",
        )
        self.assertTrue(ok.allowed)

        # Stale replay outside 300s window
        stale = verify_ucp_rfc9421_rest_response_binding(
            sent_request=req,
            received_response=resp,
            signature_input_components=comps,
            signature_created=1738617600,
            current_timestamp=1738618000,
            provided_signature_hex=sig,
            shared_verification_secret="sec-1",
        )
        self.assertFalse(stale.allowed)
        self.assertEqual(stale.reason_code, "UCP_RFC9421_RESPONSE_EXPIRED_OR_REPLAY_BLOCKED")

        # Cross-request substitution (/chk_123 response served for /chk_999)
        sub = verify_ucp_rfc9421_rest_response_binding(
            sent_request={**req, "path": "/checkout-sessions/chk_999"},
            received_response=resp,
            signature_input_components=comps,
            signature_created=1738617600,
            current_timestamp=1738617650,
            provided_signature_hex=sig,
            shared_verification_secret="sec-1",
        )
        self.assertFalse(sub.allowed)
        self.assertEqual(sub.reason_code, "UCP_RFC9421_RESPONSE_REQUEST_BINDING_MISMATCH_BLOCKED")

        # Catalog Variant per-seller offers[] (#810)
        variant = {
            "id": "agg_var_1",
            "price": 1000,
            "offers": [
                {"seller": {"domain": "shop-a.example.com"}, "item_id": "shop_a_item_9", "price": 1200},
            ],
        }
        offer_ok = validate_ucp_variant_per_seller_offer_routing(
            variant=variant,
            selected_offer_index=0,
            checkout_target_domain="shop-a.example.com",
            checkout_item_id="shop_a_item_9",
            checkout_unit_price_minor=1200,
            verified_well_known_domains=["shop-a.example.com"],
        )
        self.assertTrue(offer_ok.allowed)

        offer_bad = validate_ucp_variant_per_seller_offer_routing(
            variant=variant,
            selected_offer_index=0,
            checkout_target_domain="shop-a.example.com",
            checkout_item_id="agg_var_1",
            checkout_unit_price_minor=1200,
            verified_well_known_domains=["shop-a.example.com"],
        )
        self.assertFalse(offer_bad.allowed)
        self.assertEqual(offer_bad.reason_code, "UCP_VARIANT_OFFER_MOR_ROUTING_VIOLATION_BLOCKED")

    def test_ucp_buyer_lock_payer_id_cart_status_offer_discount_and_signals(self) -> None:
        lock_ok = validate_ucp_complete_checkout_buyer_lock(
            operation="complete_checkout",
            buyer_consent_negotiated=True,
            request_buyer_payload={"consent": {"marketing": True}},
        )
        self.assertTrue(lock_ok.allowed)

        lock_bad = validate_ucp_complete_checkout_buyer_lock(
            operation="complete_checkout",
            buyer_consent_negotiated=True,
            request_buyer_payload={"consent": {"marketing": True}, "email": "spoof@example.com"},
        )
        self.assertFalse(lock_bad.allowed)
        self.assertEqual(lock_bad.reason_code, "UCP_COMPLETE_CHECKOUT_BUYER_IDENTITY_MUTATION_BLOCKED")

        payer_ok = validate_ucp_instrument_payer_identification(
            instruments=[
                {"type": "pix", "payer": {"identification": {"type": "CPF", "number": "12345678901"}}},
                {"type": "card", "payer": {"identification": {"type": "CNPJ", "number": "12345678000199"}}},
            ]
        )
        self.assertTrue(payer_ok.allowed)

        payer_bad = validate_ucp_instrument_payer_identification(
            instruments=[{"type": "pix", "com.mercadopago.payer": {"type": "CPF", "number": "12345678901"}}]
        )
        self.assertFalse(payer_bad.allowed)

        cart_ok = evaluate_ucp_cart_terminal_status_guard(
            cart_status="ordered",
            request_sets_status=False,
            attempted_action="inspect",
        )
        self.assertTrue(cart_ok.allowed)

        cart_bad = evaluate_ucp_cart_terminal_status_guard(
            cart_status="ordered",
            request_sets_status=False,
            attempted_action="rebuild_abandoned_cart",
        )
        self.assertFalse(cart_bad.allowed)

        offer_doc = {
            "id": "offer_123",
            "revision": "1",
            "applies_to": {"cart_id": "cart_123", "state_ref": "state_s0"},
            "expires_at_epoch": 2000,
            "proposed_update": {"line_items": [{"id": "item_1", "quantity": 1}]},
            "impact": {"total_delta": 2000},
        }
        state_ok = evaluate_ucp_state_bound_cart_offer(
            cart_id="cart_123",
            current_cart_state_ref="state_s0",
            offer=offer_doc,
            requested_offer_id="offer_123",
            requested_revision="1",
            current_timestamp=1500,
        )
        self.assertTrue(state_ok.allowed)

        state_stale = evaluate_ucp_state_bound_cart_offer(
            cart_id="cart_123",
            current_cart_state_ref="state_s1",
            offer=offer_doc,
            requested_offer_id="offer_123",
            requested_revision="1",
            current_timestamp=1500,
        )
        self.assertFalse(state_stale.allowed)

        reimb_ok = evaluate_ucp_platform_funded_discount_reimbursement(
            capability_negotiated=True,
            funding_reference="plat_fund_99",
            approved_subsidy_cap_minor=1500,
            order_applied_discount_minor=1200,
            refunded_or_canceled_subsidy_minor=400,
            claimed_reimbursement_minor=800,
        )
        self.assertTrue(reimb_ok.allowed)

        reimb_bad = evaluate_ucp_platform_funded_discount_reimbursement(
            capability_negotiated=True,
            funding_reference="plat_fund_99",
            approved_subsidy_cap_minor=1500,
            order_applied_discount_minor=1200,
            refunded_or_canceled_subsidy_minor=400,
            claimed_reimbursement_minor=1200,
        )
        self.assertFalse(reimb_bad.allowed)

        sig_ok = validate_ucp_item_snapshot_and_fraud_signals(
            request_item_payload={"id": "var_1", "quantity": 2},
            order_captured_list_price=2500,
            order_returned_list_price=2500,
            catalog_current_list_price=2900,
            response_options_complete=True,
            signals={
                "dev.ucp.buyer_ip_country": "US",
                "dev.ucp.device_time_zone": "America/Los_Angeles",
                "dev.ucp.browser_screen_height": 1440,
                "dev.ucp.browser_screen_width": 2560,
                "dev.ucp.browser_language": "en-US",
                "dev.ucp.browser_java_enabled": False,
            },
        )
        self.assertTrue(sig_ok.allowed)

        sig_bad = validate_ucp_item_snapshot_and_fraud_signals(
            request_item_payload={"id": "var_1", "list_price": 100},
            order_captured_list_price=2500,
            order_returned_list_price=2500,
            catalog_current_list_price=2900,
            response_options_complete=True,
            signals={},
        )
        self.assertFalse(sig_bad.allowed)

    def test_ap2_log_x402_verify_and_tau2_guards(self) -> None:
        ap2_ok = audit_ap2_selective_disclosure_log_payload(
            log_record={"event": "a2a_request", "payment_token": "<REDACTED>", "risk_data": "<REDACTED>"},
        )
        self.assertTrue(ap2_ok.allowed)

        ap2_leak = audit_ap2_selective_disclosure_log_payload(
            log_record={"event": "a2a_request", "payment_token": "tok_live_secret_123"},
        )
        self.assertFalse(ap2_leak.allowed)
        self.assertEqual(ap2_leak.reason_code, "AP2_PLAINTEXT_PAYMENT_ARTIFACT_LOG_LEAK_BLOCKED")

        x402_ok = validate_x402_verify_eip3009_and_next_402_contract(
            verify_return_tuple_len=3,
            ecdsa_s_is_canonical_low=False,
            verify_error_code="ErrInvalidSignatureS",
            next_unpaid_402_json_body={"error": "Payment required"},
        )
        self.assertTrue(x402_ok.allowed)

        x402_bad = validate_x402_verify_eip3009_and_next_402_contract(
            verify_return_tuple_len=2,
            ecdsa_s_is_canonical_low=False,
            verify_error_code="ErrInvalidSignatureS",
            next_unpaid_402_json_body={},
        )
        self.assertFalse(x402_bad.allowed)

        docs = [
            {
                "id": "doc_business_credit_cards_business_silver_rewards_card_012",
                "title": "Business Silver Rewards Card: General Terms",
                "text": "See Exceptions and Exclusions for merchant restrictions.",
            },
            {
                "id": "doc_business_credit_cards_business_silver_rewards_card_005",
                "title": "Business Silver Rewards Card: Exceptions and Exclusions",
                "text": "Purchases at Apple do not qualify for rewards.",
            },
        ]
        bm25_ok = evaluate_tau2_bm25_grep_title_aware_retrieval(
            documents=docs,
            query="Exceptions and Exclusions",
            include_title_in_index=True,
            expected_top_doc_id="doc_business_credit_cards_business_silver_rewards_card_005",
        )
        self.assertTrue(bm25_ok.allowed)

        bm25_bad = evaluate_tau2_bm25_grep_title_aware_retrieval(
            documents=docs,
            query="Exceptions and Exclusions",
            include_title_in_index=False,
            expected_top_doc_id="doc_business_credit_cards_business_silver_rewards_card_005",
        )
        self.assertFalse(bm25_bad.allowed)

        t7_ok = evaluate_tau2_airline_task7_other_flights_total(
            reservation_totals_usd={"XEHM4B": 296, "59XX6W": 624, "7WPL39": 402, "3EMQJ6": 306},
            cancelled_in_session_ids=["XEHM4B", "59XX6W"],
            user_question_scope="other_upcoming_flights",
            communicated_amount_usd=708,
        )
        self.assertTrue(t7_ok.allowed)

        passk_bad = evaluate_tau2_pass_hat_k_infra_error_integrity(
            configured_trials=4,
            successful_trials=1,
            infrastructure_error_trials=3,
            reported_pass_hat_1=1.0,
            allow_silent_infra_exclusion=True,
        )
        self.assertFalse(passk_bad.allowed)

        sim_ok = validate_tau2_persona_solo_and_simulator_turn(
            persona_stated_age=41,
            db_birth_year=1985,
            reference_year=2026,
            is_solo_mode=True,
            first_message_role="user",
            first_message_content="Begin working on the ticket.",
            user_sim_turn_has_speech=True,
            user_sim_turn_has_tracking_tool=True,
            orchestrator_drops_speech_on_tool_call=False,
        )
        self.assertTrue(sim_ok.allowed)

        kb_ok = validate_tau2_kb_read_tool_and_write_equivalence(
            kb_required_tables=["cash_back_disputes", "transaction_disputes"],
            agent_callable_read_tables=["cash_back_disputes", "transaction_disputes"],
            unretired_card_closure_threads=[],
            write_arg_semantically_equivalent=True,
            penalize_equivalent_write_arg=False,
        )
        self.assertTrue(kb_ok.allowed)


if __name__ == "__main__":
    unittest.main()
