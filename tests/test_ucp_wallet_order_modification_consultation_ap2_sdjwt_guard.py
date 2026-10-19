"""Unit tests for Stage 45 UCP Wallet Attestation (#415) & Render Artifact (#635), Order Modification Lookup/Fence (#945), Order Consultation Proposal Digest & Auth (#946), and AP2 Merchant Auth / SD-JWT+kb / P-521 Binding (#466/#496/#610/#625/#618) + Discount/Fulfillment Guards (#577/#578/#609/#617)."""

import unittest

from lab.ucp_wallet_order_modification_consultation_ap2_sdjwt_guard import (
    compute_ucp_consultation_proposal_digest,
    evaluate_ucp_ap2_merchant_auth_sdjwt_and_discount_fulfillment_guard,
    evaluate_ucp_order_consultation_digest_and_auth_guard,
    evaluate_ucp_order_modification_lookup_and_fence_guard,
    evaluate_ucp_wallet_attestation_and_payment_render_artifact_guard,
)


class TestStage45UcpWalletOrderModificationConsultationAp2SdjwtGuard(unittest.TestCase):
    def test_ucp_wallet_attestation_and_payment_render_artifact_guard(self) -> None:
        valid_ctx = {
            "provider_config": {
                "type": "wallet_attestation",
                "provider_jwks": "https://attest.example.com/.well-known/jwks.json",
                "attestation_endpoint": "https://attest.example.com/v1/prove",
            },
            "contributed_oauth_scopes": [],
            "published_jwks_kid_to_alg": {"kid_vip_01": "ES256"},
            "now_epoch": 1792454400,
            "max_age_seconds": 300,
            "attestation": {
                "kid": "kid_vip_01",
                "alg": "ES256",
                "signature_valid": True,
                "attested_at": 1792454350,
                "exp": 1792454650,
                "signed_predicate_met": True,
                "unsigned_override_eligible": False,
                "contains_raw_wallet_holdings": False,
            },
            "allowed_handler_origins": ["https://pix.mercadopago.com"],
            "render_artifact_action": {
                "id": "com.mercadopago.payment.render_artifact",
                "config": {
                    "code": "00020126580014BR.GOV.BCB.PIX0136...",
                    "instructions_url": "https://pix.mercadopago.com/instructions/tx_99",
                    "contains_pan_or_otp_or_secret": False,
                },
            },
        }
        res = evaluate_ucp_wallet_attestation_and_payment_render_artifact_guard(valid_ctx)
        self.assertTrue(res.admitted)
        self.assertTrue(res.entitlement_granted)

        # Unsigned override attempting to grant entitlement when signed boolean is False
        unsigned_override = {
            **valid_ctx,
            "attestation": {
                **valid_ctx["attestation"],
                "signed_predicate_met": False,
                "unsigned_override_eligible": True,
            },
        }
        res_unsigned = evaluate_ucp_wallet_attestation_and_payment_render_artifact_guard(unsigned_override)
        self.assertFalse(res_unsigned.admitted)
        self.assertEqual(res_unsigned.decision_code, "UNSIGNED_WALLET_ENTITLEMENT_OVERRIDE_BLOCKED")

        # Raw wallet holdings leaked without opt-in
        raw_leak = {
            **valid_ctx,
            "attestation": {
                **valid_ctx["attestation"],
                "contains_raw_wallet_holdings": True,
            },
        }
        res_leak = evaluate_ucp_wallet_attestation_and_payment_render_artifact_guard(raw_leak)
        self.assertFalse(res_leak.admitted)
        self.assertEqual(res_leak.decision_code, "WALLET_ATTESTATION_RAW_PORTFOLIO_DISCLOSURE_LEAK_BLOCKED")

        # Render artifact with forbidden `required: true` field (#635 / #582)
        bad_render = {
            **valid_ctx,
            "render_artifact_action": {
                "id": "com.mercadopago.payment.render_artifact",
                "required": True,
                "config": {},
            },
        }
        res_render = evaluate_ucp_wallet_attestation_and_payment_render_artifact_guard(bad_render)
        self.assertFalse(res_render.admitted)
        self.assertEqual(res_render.decision_code, "RENDER_ARTIFACT_FORBIDDEN_REQUIRED_BOOLEAN_FIELD")

    def test_ucp_order_modification_lookup_and_fence_guard(self) -> None:
        # 1. Safe GET lookup_modification
        lookup_ctx = {
            "extension_negotiated": True,
            "parent_order_capability_negotiated": True,
            "response_cache_control": "no-store",
            "method_kind": "lookup_modification",
            "op": "cancel",
            "original_idempotency_key": "idem_cancel_01",
            "claimed_keys": set(),
            "fenced_keys": set(),
            "original_key_in_url_query": False,
            "lookup_mutated_fence_or_claim_state": False,
        }
        res_lookup = evaluate_ucp_order_modification_lookup_and_fence_guard(lookup_ctx)
        self.assertTrue(res_lookup.admitted)
        self.assertEqual(res_lookup.lookup_or_fence_status, "unresolved")

        # Lookup that illegally installs a fence on GET
        bad_lookup = {**lookup_ctx, "lookup_mutated_fence_or_claim_state": True}
        res_bad_lookup = evaluate_ucp_order_modification_lookup_and_fence_guard(bad_lookup)
        self.assertFalse(res_bad_lookup.admitted)
        self.assertEqual(res_bad_lookup.decision_code, "LOOKUP_MODIFICATION_MUTATED_FENCE_OR_CLAIM_STATE_BLOCKED")

        # 2. Permanent POST fence_modification
        fence_ctx = {
            "extension_negotiated": True,
            "parent_order_capability_negotiated": True,
            "response_cache_control": "no-store",
            "method_kind": "fence_modification",
            "op": "cancel",
            "original_idempotency_key": "idem_cancel_01",
            "fence_request_idempotency_key": "idem_fence_fresh_02",
            "claimed_keys": set(),
            "expired_claimed_keys": set(),
            "fenced_keys": set(),
        }
        res_fence = evaluate_ucp_order_modification_lookup_and_fence_guard(fence_ctx)
        self.assertTrue(res_fence.admitted)
        self.assertTrue(res_fence.key_permanently_fenced)
        self.assertEqual(res_fence.lookup_or_fence_status, "fenced")

        # Temporary `fenced_until` is forbidden
        temp_fence = {**fence_ctx, "fenced_until": "2026-10-20T00:00:00Z"}
        res_temp = evaluate_ucp_order_modification_lookup_and_fence_guard(temp_fence)
        self.assertFalse(res_temp.admitted)
        self.assertEqual(res_temp.decision_code, "TEMPORARY_FENCED_UNTIL_TOMBSTONE_FORBIDDEN")

        # Late submission arriving under a permanently fenced key
        late_submit = {
            "extension_negotiated": True,
            "parent_order_capability_negotiated": True,
            "response_cache_control": "no-store",
            "method_kind": "create_modification",
            "op": "cancel",
            "idempotency_key": "idem_cancel_01",
            "fenced_keys": {"idem_cancel_01"},
            "base_order_version": "v1",
            "current_order_version": "v1",
        }
        res_late = evaluate_ucp_order_modification_lookup_and_fence_guard(late_submit)
        self.assertFalse(res_late.admitted)
        self.assertEqual(res_late.decision_code, "FENCED_MODIFICATION_KEY_LATE_SUBMISSION_BLOCKED")

    def test_ucp_order_consultation_digest_and_auth_guard(self) -> None:
        proposal_input = {
            "consultation_id": "cons_01",
            "revision": 2,
            "order_id": "ord_9001",
            "baseline_order_version": "v3",
            "scope": {"line_item_ids": ["li_1"]},
            "proposed_terms": {"delta_amount_minor": 1500, "currency": "USD"},
            "effective_time_rule": "upon_approval",
            "decision_deadline": "2026-10-20T12:00:00Z",
            "execution_deadline": "2026-10-21T12:00:00Z",
            "digest_context": "dev.ucp.shopping.order_consultation/v1",
        }
        digest = compute_ucp_consultation_proposal_digest(proposal_input)
        valid_ctx = {
            "canonical_proposal_input": proposal_input,
            "buyer_token_valid": True,
            "token_subject": "usr_buyer_77",
            "order_owner_subject": "usr_buyer_77",
            "token_scopes": ["dev.ucp.shopping.order_consultation:decide"],
            "proposed_delta_minor": 1500,
            "delegation_max_delta_minor": 5000,
            "serialization_point_epoch": 1792454400,
            "decision_deadline_epoch": 1792490000,
            "active_revision": 2,
            "submitted_revision": 2,
            "consultation_status_at_serialization": "open",
            "submitted_proposal_digest": digest,
            "approval_triggered_immediate_silent_capture": False,
        }
        res = evaluate_ucp_order_consultation_digest_and_auth_guard(valid_ctx)
        self.assertTrue(res.admitted)
        self.assertTrue(res.final_receipt_issued)

        # `order:manage` scope without `:decide` scope rejected before replay
        wrong_scope = {**valid_ctx, "token_scopes": ["dev.ucp.shopping.order:manage"]}
        res_scope = evaluate_ucp_order_consultation_digest_and_auth_guard(wrong_scope)
        self.assertFalse(res_scope.admitted)
        self.assertEqual(res_scope.decision_code, "CONSULTATION_DECIDE_AUTH_OR_SCOPE_FAILED_BEFORE_REPLAY")

        # Proposal digest mismatch
        bad_digest = {**valid_ctx, "submitted_proposal_digest": "sha-256:0000"}
        res_digest = evaluate_ucp_order_consultation_digest_and_auth_guard(bad_digest)
        self.assertFalse(res_digest.admitted)
        self.assertEqual(res_digest.decision_code, "CONSULTATION_PROPOSAL_DIGEST_MISMATCH_BLOCKED")

    def test_ucp_ap2_merchant_auth_sdjwt_and_discount_fulfillment_guard(self) -> None:
        valid_ctx = {
            "ap2_active": True,
            "merchant_authorization": "eyJhbGciOiJFUzUxMiJ9..c2lnbmF0dXJl",
            "signing_jwk": {"kty": "EC", "crv": "P-521", "alg": "ES512"},
            "protected_jws_alg": "ES512",
            "checkout_mandate": "eyJhbGciOiJFUzI1NiJ9.eyJfc2QiOltdfQ.c2ln~ZGlzY2xvc3VyZQ~~eyJhbGciOiJFUzI1NiJ9.eyJub25jZSI6IjEyMyJ9.a2Jfc2ln",
            "line_items": [
                {"id": "li_main", "total_minor": 5000, "is_promotional_gift": False},
                {"id": "li_gift", "total_minor": 0, "is_promotional_gift": True},
            ],
            "applied_discounts": [
                {"id": "disc_bogo", "title": "Free Tote Bag", "gift_line_item_id": "li_gift"},
            ],
            "available_discounts": [
                {"id": "avail_vip", "title": "Secret VIP Code Offer", "type": "code"},
            ],
            "selected_fulfillment_method_ids": ["method_ship"],
            "selected_fulfillment_option_ids": ["opt_express"],
            "fulfillment_event": {
                "fulfillment_method_id": "method_ship",
                "fulfillment_option_id": "opt_express",
                "estimated_delivery_earliest_epoch": 1792500000,
                "estimated_delivery_latest_epoch": 1792600000,
            },
        }
        res = evaluate_ucp_ap2_merchant_auth_sdjwt_and_discount_fulfillment_guard(valid_ctx)
        self.assertTrue(res.admitted)
        self.assertTrue(res.sdjwt_kb_verified)

        # P-521 paired with ES256 (#625)
        bad_p521 = {
            **valid_ctx,
            "signing_jwk": {"kty": "EC", "crv": "P-521", "alg": "ES256"},
            "protected_jws_alg": "ES256",
        }
        res_p521 = evaluate_ucp_ap2_merchant_auth_sdjwt_and_discount_fulfillment_guard(bad_p521)
        self.assertFalse(res_p521.admitted)
        self.assertEqual(res_p521.decision_code, "AP2_JWK_CURVE_OR_PROTECTED_ALG_MISMATCH_BLOCKED")

        # SD-JWT with stripped key-binding JWT (#496)
        no_kb = {
            **valid_ctx,
            "checkout_mandate": "eyJhbGciOiJFUzI1NiJ9.eyJfc2QiOltdfQ.c2ln~ZGlzY2xvc3VyZQ",
        }
        res_no_kb = evaluate_ucp_ap2_merchant_auth_sdjwt_and_discount_fulfillment_guard(no_kb)
        self.assertFalse(res_no_kb.admitted)
        self.assertEqual(res_no_kb.decision_code, "AP2_CHECKOUT_MANDATE_MISSING_OR_MALFORMED_SDJWT_KB_BLOCKED")

        # Unexplained zero-price promotional gift item (#578)
        unlinked_gift = {
            **valid_ctx,
            "applied_discounts": [{"id": "disc_bogo", "title": "Free Tote Bag"}],
        }
        res_gift = evaluate_ucp_ap2_merchant_auth_sdjwt_and_discount_fulfillment_guard(unlinked_gift)
        self.assertFalse(res_gift.admitted)
        self.assertEqual(res_gift.decision_code, "UNEXPLAINED_ZERO_PRICE_GIFT_LINE_ITEM_BLOCKED")


if __name__ == "__main__":
    unittest.main()
