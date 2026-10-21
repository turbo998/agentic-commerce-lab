"""Unit tests for Stage 146 deterministic guardrails (DE-01..DE-16)."""

from __future__ import annotations

import hashlib
import hmac
import unittest

from lab.x402_durable_evidence_erc6492_ucp_dns_idp_ap2_amount_jcs_guard import (
    canonical_jcs_sha256_hex,
    evaluate_acp_feed_deeplink_suggested_price_and_complete_fulfillment,
    evaluate_acp_razorpay_delegated_handlers,
    evaluate_ap2_checkout_hash_entropy_and_jcs_cart_binding,
    evaluate_ap2_x402_verified_mandate_amount_extraction,
    evaluate_mcp_base64_sentinel_dns_bootstrap_and_schema_id,
    evaluate_stripe_mcp_x402_batch_and_per_tool_auth,
    evaluate_tau2_gold_db_judge_verdicts_retail_and_union_args,
    evaluate_ucp_adjustment_cause_and_platform_reference,
    evaluate_ucp_conditional_idempotency_and_credential_redaction,
    evaluate_ucp_dns_authoritative_email_linking_and_auth_gate,
    evaluate_ucp_lodging_schedule_nights_and_guest_order_credential,
    evaluate_visa_tap_session_continuity_and_hop_digest,
    evaluate_x402_detached_paid_response_validation,
    evaluate_x402_durable_and_authorization_evidence,
    evaluate_x402_erc6492_settle_reuse_and_svm_backoff,
    evaluate_x402_svm_delegated_authorizer_and_stellar_feebump,
)


class Stage146GuardTests(unittest.TestCase):
    def test_x402_guards_de01_to_de04(self) -> None:
        secret = "hmac_secret_3376"
        nonce = "chal_nonce_01"
        payee = "0x1111111111111111111111111111111111111111"
        exp = 2_000_000
        sig = hmac.new(secret.encode(), f"{nonce}:{payee}:{exp}".encode(), hashlib.sha256).hexdigest()
        seen: set[str] = set()

        ok_de01 = evaluate_x402_durable_and_authorization_evidence(
            buyer_opted_in_durable_evidence=True,
            durable_evidence_ext={
                "ciphertext_digest": "sha256:abc123",
                "retrieval_uri": "https://evidence.example.com/e/1",
                "facilitator_eip712_sig": "0x" + "a" * 64,
                "party_encrypted": True,
            },
            auth_challenge_secret=secret,
            advertised_challenge_nonce=nonce,
            advertised_payee=payee,
            challenge_expires_at=exp,
            now_epoch=exp - 10,
            client_auth_evidence={
                "challenge_nonce": nonce,
                "payee": payee,
                "challenge_hmac": sig,
                "evidence": "mandate-proof-v1",
            },
            seen_challenge_nonces=seen,
            external_verifier_decision="allow",
        )
        self.assertTrue(ok_de01.allowed)

        replay_de01 = evaluate_x402_durable_and_authorization_evidence(
            buyer_opted_in_durable_evidence=True,
            durable_evidence_ext={
                "ciphertext_digest": "sha256:abc123",
                "retrieval_uri": "https://evidence.example.com/e/1",
                "facilitator_eip712_sig": "0x" + "a" * 64,
                "party_encrypted": True,
            },
            auth_challenge_secret=secret,
            advertised_challenge_nonce=nonce,
            advertised_payee=payee,
            challenge_expires_at=exp,
            now_epoch=exp - 5,
            client_auth_evidence={
                "challenge_nonce": nonce,
                "payee": payee,
                "challenge_hmac": sig,
                "evidence": "mandate-proof-v1",
            },
            seen_challenge_nonces=seen,
            external_verifier_decision="allow",
        )
        self.assertFalse(replay_de01.allowed)

        ok_de02 = evaluate_x402_erc6492_settle_reuse_and_svm_backoff(
            verify_code_deployed=False,
            settle_performed_second_eth_get_code=False,
            settle_deployed_factory_wrap=True,
            svm_reread_delays_ms=[200, 400, 600],
        )
        self.assertTrue(ok_de02.allowed)
        bad_de02 = evaluate_x402_erc6492_settle_reuse_and_svm_backoff(
            verify_code_deployed=False,
            settle_performed_second_eth_get_code=True,
            settle_deployed_factory_wrap=True,
            svm_reread_delays_ms=[200, 400, 600],
        )
        self.assertFalse(bad_de02.allowed)

        live_res = {"data": "paid-payload"}
        live_ctx = {"settlement_receipt": "tx_0x123"}

        def mutating_accept_hook(r: dict, c: dict) -> bool:
            r["data"] = "tampered"
            return True

        ok_de03 = evaluate_x402_detached_paid_response_validation(
            paid_result=live_res,
            payment_context=live_ctx,
            validator_hook=mutating_accept_hook,
            payment_attempts_issued=1,
        )
        self.assertTrue(ok_de03.allowed)
        self.assertEqual(live_res["data"], "paid-payload")

        bad_de03 = evaluate_x402_detached_paid_response_validation(
            paid_result=live_res,
            payment_context=live_ctx,
            validator_hook=lambda r, c: False,
            payment_attempts_issued=1,
        )
        self.assertFalse(bad_de03.allowed)
        self.assertEqual(bad_de03.decision_code, "X402_PAID_RESPONSE_VALIDATION_ERROR_PRESERVED")

        ok_de04 = evaluate_x402_svm_delegated_authorizer_and_stellar_feebump(
            svm_payload_type="claim",
            delegated_receiver_authorizer=True,
            deposit_bound_caller_id="caller_agent_1",
            claim_caller_id="caller_agent_1",
            facilitator_primary_signers=["GFACIL_PRIMARY"],
            facilitator_fee_bump_signer="GFACIL_FEEBUMP",
            stellar_client_roles={"payer": "GCLIENT_1", "tx_source": "GCLIENT_1"},
        )
        self.assertTrue(ok_de04.allowed)
        bad_de04 = evaluate_x402_svm_delegated_authorizer_and_stellar_feebump(
            svm_payload_type="claim",
            delegated_receiver_authorizer=True,
            deposit_bound_caller_id="caller_agent_1",
            claim_caller_id="caller_agent_1",
            facilitator_primary_signers=["GFACIL_PRIMARY"],
            facilitator_fee_bump_signer="GFACIL_FEEBUMP",
            stellar_client_roles={"payer": "GCLIENT_1", "tx_source": "GFACIL_FEEBUMP"},
        )
        self.assertFalse(bad_de04.allowed)

    def test_ucp_and_acp_guards_de05_to_de10(self) -> None:
        ok_de05 = evaluate_ucp_dns_authoritative_email_linking_and_auth_gate(
            buyer_email="alice@corp.example.com",
            idp_issuer="https://idp.corp.example.com",
            email_verified_claim=True,
            dns_txt_records={"_email-verification.corp.example.com": ["iss=https://idp.corp.example.com"]},
            is_authenticated=True,
            response_contains_business_populated_private_values=True,
        )
        self.assertTrue(ok_de05.allowed)
        bad_de05 = evaluate_ucp_dns_authoritative_email_linking_and_auth_gate(
            buyer_email="alice@gmail.com",
            idp_issuer="https://rogue-idp.example.net",
            email_verified_claim=True,
            dns_txt_records={"_email-verification.gmail.com": ["iss=https://accounts.google.com"]},
            is_authenticated=True,
            response_contains_business_populated_private_values=False,
        )
        self.assertFalse(bad_de05.allowed)

        ok_de06 = evaluate_ucp_conditional_idempotency_and_credential_redaction(
            operation="create_checkout",
            idempotency_key=None,
            conflicting_payload_for_existing_key=False,
            endpoint_contract="/checkout-sessions/{id}",
            entity_response_credential_fields=["last4", "brand"],
        )
        self.assertTrue(ok_de06.allowed)
        bad_de06 = evaluate_ucp_conditional_idempotency_and_credential_redaction(
            operation="complete_checkout",
            idempotency_key="idem_1",
            conflicting_payload_for_existing_key=False,
            endpoint_contract="/checkout-sessions/{id}",
            entity_response_credential_fields=["last4", "cryptogram"],
        )
        self.assertFalse(bad_de06.allowed)

        ok_de07 = evaluate_ucp_lodging_schedule_nights_and_guest_order_credential(
            check_in_date="2026-11-10",
            check_out_date="2026-11-13",
            declared_nights=3,
            cancellation_schedule=[
                {"effective_from_epoch": 1000, "effective_until_epoch": 2000, "penalty_minor": 0},
                {"effective_from_epoch": 2000, "effective_until_epoch": 3000, "penalty_minor": 15000},
            ],
            evaluation_epoch=2500,
            selected_penalty_minor=15000,
            is_guest_buyer=True,
            issued_order_credential="ord_cred_9876543210abcdef",
            presented_order_credential="ord_cred_9876543210abcdef",
        )
        self.assertTrue(ok_de07.allowed)
        bad_de07 = evaluate_ucp_lodging_schedule_nights_and_guest_order_credential(
            check_in_date="2026-11-10",
            check_out_date="2026-11-13",
            declared_nights=2,
            cancellation_schedule=[
                {"effective_from_epoch": 1000, "effective_until_epoch": 3000, "penalty_minor": 15000},
            ],
            evaluation_epoch=2500,
            selected_penalty_minor=15000,
            is_guest_buyer=True,
            issued_order_credential="ord_cred_9876543210abcdef",
            presented_order_credential="ord_cred_9876543210abcdef",
        )
        self.assertFalse(bad_de07.allowed)

        ok_de08 = evaluate_ucp_adjustment_cause_and_platform_reference(
            adjustment_type="dispute",
            cause={"category": "amount_divergence", "attributed_to": "business", "nature": "abuse"},
            false_assertion_made=False,
            create_platform_reference="plat_ref_001",
            update_or_complete_includes_platform_reference=False,
            response_platform_reference="plat_ref_001",
        )
        self.assertTrue(ok_de08.allowed)
        bad_de08 = evaluate_ucp_adjustment_cause_and_platform_reference(
            adjustment_type="dispute",
            cause={"category": "amount_divergence", "attributed_to": "buyer", "nature": "fraud"},
            false_assertion_made=False,
            create_platform_reference="plat_ref_001",
            update_or_complete_includes_platform_reference=False,
            response_platform_reference="plat_ref_001",
        )
        self.assertFalse(bad_de08.allowed)

        ok_de09 = evaluate_acp_feed_deeplink_suggested_price_and_complete_fulfillment(
            deep_link_url="https://shop.merchant.example/p/42",
            allowed_app_schemes=["merchantapp"],
            allowed_https_hosts=["shop.merchant.example"],
            feed_extension_keys=["com.paypal.app_link", "io.stripe.inventory"],
            suggested_price_minor=9500,
            merchant_floor_price_minor=9000,
            complete_fulfillment_option_id="ship_express",
            available_fulfillment_options={"ship_std": 500, "ship_express": 1200},
            items_subtotal_minor=9500,
            declared_total_minor=10700,
        )
        self.assertTrue(ok_de09.allowed)
        bad_de09 = evaluate_acp_feed_deeplink_suggested_price_and_complete_fulfillment(
            deep_link_url="javascript:alert(1)",
            allowed_app_schemes=["merchantapp"],
            allowed_https_hosts=["shop.merchant.example"],
            feed_extension_keys=["com.paypal.app_link"],
            suggested_price_minor=9500,
            merchant_floor_price_minor=9000,
            complete_fulfillment_option_id="ship_express",
            available_fulfillment_options={"ship_express": 1200},
            items_subtotal_minor=9500,
            declared_total_minor=10700,
        )
        self.assertFalse(bad_de09.allowed)

        ok_de10 = evaluate_acp_razorpay_delegated_handlers(
            handler_type="razorpay_upi_circle",
            payload={
                "circle_mandate_id": "upic_mandate_01",
                "primary_approver_vpa": "parent@okaxis",
                "max_amount_minor": 50000,
                "expires_at_epoch": 2_000_000,
            },
            checkout_amount_minor=35000,
            expected_merchant_vpa="merchant@razorpay",
            now_epoch=1_900_000,
        )
        self.assertTrue(ok_de10.allowed)
        bad_de10 = evaluate_acp_razorpay_delegated_handlers(
            handler_type="razorpay_s2s_cards",
            payload={"raw_pan": "4111111111111111", "card_token_id": "tok_1", "afa_cryptogram": "crypt_1"},
            checkout_amount_minor=35000,
            expected_merchant_vpa="merchant@razorpay",
            now_epoch=1_900_000,
        )
        self.assertFalse(bad_de10.allowed)

    def test_ap2_mcp_stripe_tap_tau2_guards_de11_to_de16(self) -> None:
        ok_de11 = evaluate_ap2_x402_verified_mandate_amount_extraction(
            closed_mandate={
                "payment_instrument": {"id": "inst_1", "type": "x402_usdc"},
                "payment_amount": {"currency": "USD", "amount": 4890},
            },
            merchant_payee_address="0x2222222222222222222222222222222222222222",
            requested_transfer_amount_cents=4890,
        )
        self.assertTrue(ok_de11.allowed)
        bad_de11 = evaluate_ap2_x402_verified_mandate_amount_extraction(
            closed_mandate={
                "payment_instrument": {"id": "inst_1", "type": "x402_usdc"},
                "payment_amount": {"currency": "USD", "amount": 4890},
            },
            merchant_payee_address="0x2222222222222222222222222222222222222222",
            requested_transfer_amount_cents=1250,
        )
        self.assertFalse(bad_de11.allowed)

        cart_contents = {"items": [{"sku": "sku_1", "qty": 2, "price": 2445}], "currency": "USD"}
        cart_hash = canonical_jcs_sha256_hex(cart_contents)
        ok_de12 = evaluate_ap2_checkout_hash_entropy_and_jcs_cart_binding(
            checkout_jwt_payload={"jti": "9f8e7d6c5b4a392817263544aabbccdd"},
            cart_mandate_id="cart_m_01",
            cart_mandate_contents=cart_contents,
            payment_mandate_contents={"cart_mandate_id": "cart_m_01", "cart_mandate_hash": cart_hash},
        )
        self.assertTrue(ok_de12.allowed)
        bad_de12 = evaluate_ap2_checkout_hash_entropy_and_jcs_cart_binding(
            checkout_jwt_payload={"jti": "short"},
            cart_mandate_id="cart_m_01",
            cart_mandate_contents=cart_contents,
            payment_mandate_contents={"cart_mandate_id": "cart_m_01", "cart_mandate_hash": cart_hash},
        )
        self.assertFalse(bad_de12.allowed)

        ok_de13 = evaluate_mcp_base64_sentinel_dns_bootstrap_and_schema_id(
            mcp_param_header_value="=?base64?eyJmb28iOiJiYXIifQ==?=",
            dns_bootstrap_txt="mcp-server-card=https://mcp.example.com/.well-known/mcp-server-card",
            authorized_domain="example.com",
            generated_schema={"$id": "https://modelcontextprotocol.io/schemas/2026-07-28/schema.json"},
        )
        self.assertTrue(ok_de13.allowed)
        bad_de13 = evaluate_mcp_base64_sentinel_dns_bootstrap_and_schema_id(
            mcp_param_header_value="=?BASE64?eyJmb28iOiJiYXIifQ==?=",
            dns_bootstrap_txt="mcp-server-card=https://mcp.example.com/.well-known/mcp-server-card",
            authorized_domain="example.com",
            generated_schema={"$id": "https://modelcontextprotocol.io/schemas/2026-07-28/schema.json"},
        )
        self.assertFalse(bad_de13.allowed)

        ok_de14 = evaluate_stripe_mcp_x402_batch_and_per_tool_auth(
            agent_id="agt_procurement_01",
            invoked_tool="create_x402_batch_payment",
            agent_tool_permissions={"agt_procurement_01": ["create_x402_batch_payment", "retrieve_balance"]},
            batch_items=[{"nonce": "n1", "amount_minor": 1500}, {"nonce": "n2", "amount_minor": 2500}],
            signed_batch_total_minor=4000,
            preflight_errors=[],
        )
        self.assertTrue(ok_de14.allowed)
        bad_de14 = evaluate_stripe_mcp_x402_batch_and_per_tool_auth(
            agent_id="agt_procurement_01",
            invoked_tool="issue_refund",
            agent_tool_permissions={"agt_procurement_01": ["create_x402_batch_payment"]},
            batch_items=[{"nonce": "n1", "amount_minor": 1500}],
            signed_batch_total_minor=1500,
            preflight_errors=[],
        )
        self.assertFalse(bad_de14.allowed)

        tap_secret = "tap_continuity_secret"
        mandate_dig = "sha-256=:dGVzdF9tYW5kYXRlX2RpZ2VzdA==:"
        tap_hmac = hmac.new(
            tap_secret.encode(),
            f"bsess_01:tap_key_01:{mandate_dig}".encode(),
            hashlib.sha256,
        ).hexdigest()
        ok_de15 = evaluate_visa_tap_session_continuity_and_hop_digest(
            browser_session_id="bsess_01",
            agent_key_id="tap_key_01",
            active_directory_keys={"tap_key_01"},
            initial_mandate_digest=mandate_dig,
            terminal_hop_mandate_digest=mandate_dig,
            continuity_token_hmac=tap_hmac,
            shared_continuity_secret=tap_secret,
        )
        self.assertTrue(ok_de15.allowed)
        bad_de15 = evaluate_visa_tap_session_continuity_and_hop_digest(
            browser_session_id="bsess_01",
            agent_key_id="tap_key_01",
            active_directory_keys={"tap_key_01"},
            initial_mandate_digest=mandate_dig,
            terminal_hop_mandate_digest="sha-256=:dGFtcGVyZWRfZGlnZXN0:",
            continuity_token_hmac=tap_hmac,
            shared_continuity_secret=tap_secret,
        )
        self.assertFalse(bad_de15.allowed)

        ok_de16 = evaluate_tau2_gold_db_judge_verdicts_retail_and_union_args(
            gold_write_actions_total=2,
            gold_write_actions_executed=2,
            nl_assertions_count=3,
            nl_judge_verdicts_count=3,
            retail_order_status="delivered",
            exchange_price_diff_cents=2110,
            gift_card_balance_cents=2500,
            agent_tool_args={"order_id": "#W4316152", "payment_method_id": "gift_card_1"},
            gold_tool_args={"order_id": "#W4316152", "payment_method_id": "gift_card_1"},
        )
        self.assertTrue(ok_de16.allowed)
        bad_de16 = evaluate_tau2_gold_db_judge_verdicts_retail_and_union_args(
            gold_write_actions_total=2,
            gold_write_actions_executed=2,
            nl_assertions_count=3,
            nl_judge_verdicts_count=3,
            retail_order_status="delivered",
            exchange_price_diff_cents=2110,
            gift_card_balance_cents=2500,
            agent_tool_args={"order_id": "#W4316152"},
            gold_tool_args={"order_id": "#W4316152", "payment_method_id": "gift_card_1"},
        )
        self.assertFalse(bad_de16.allowed)


if __name__ == "__main__":
    unittest.main()
