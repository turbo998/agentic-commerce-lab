from __future__ import annotations

import base64
import hashlib
import unittest

from lab.ucp_ap2_token_issuance_catalog_purpose_acp_upi_circle_tap_rfc9421_guard import (
    evaluate_acp_feed_extensions_and_razorpay_upi_circle_guard,
    evaluate_ap2_open_mandate_hash_entropy_and_tap_rfc9421_guard,
    evaluate_ucp_ap2_token_issuance_and_content_digest_guard,
    evaluate_ucp_catalog_search_purpose_and_reference_ids_guard,
)


class UCPAP2TokenIssuanceCatalogPurposeACPUPICircleTAPRFC9421GuardTests(unittest.TestCase):
    def test_ucp_ap2_token_issuance_and_raw_content_digest_guard(self) -> None:
        raw_body = b'{\n  "id": "chk_abc123",\n  "status": "ready_for_complete"\n}'
        digest = "sha-256=:" + base64.b64encode(hashlib.sha256(raw_body).digest()).decode("ascii") + ":"

        ok = evaluate_ucp_ap2_token_issuance_and_content_digest_guard(
            ap2_negotiated=True,
            tokenize_request={
                "credential": {
                    "type": "ap2_payment_mandate",
                    "payment_mandate": "eyJhbGciOiJFZERTQSJ9.eyJ0cmFuc2FjdGlvbl9pZCI6InR4XzAxIn0.sig~kb",
                    "checkout_jwt": "eyJhbGciOiJFZERTQSJ9.eyJ0cmFuc2FjdGlvbl9pZCI6InR4XzAxIn0.sig",
                },
                "binding": {"type": "dev.ucp.shopping.checkout", "id": "chk_abc123"},
                "identity": {"access_token": "at_01"},
            },
            checkout_jwt_transaction_id="tx_01",
            mandate_transaction_id="tx_01",
            mandate_signature_valid=True,
            mandate_expired=False,
            issued_payment_token="tok_opaque_9f8e7d6c5b4a3f2e1d0c9b8a",
            token_entropy_bits=160,
            token_embeds_reversible_mandate=False,
            complete_checkout_has_mandate_derived_token=True,
            raw_http_response_bytes=raw_body,
            content_digest_header=digest,
            verifier_canonicalized_body_with_jcs=False,
        )
        self.assertTrue(ok.admitted)
        self.assertEqual(ok.decision_code, "UCP_AP2_TOKEN_ISSUANCE_AND_RAW_CONTENT_DIGEST_VERIFIED")

        # Composite reversible token rejected
        composite = evaluate_ucp_ap2_token_issuance_and_content_digest_guard(
            ap2_negotiated=True,
            tokenize_request={
                "credential": {
                    "type": "ap2_payment_mandate",
                    "payment_mandate": "sdjwt~kb",
                    "checkout_jwt": "jws",
                },
                "binding": {"type": "dev.ucp.shopping.checkout", "id": "chk_abc123"},
            },
            checkout_jwt_transaction_id="tx_01",
            mandate_transaction_id="tx_01",
            mandate_signature_valid=True,
            mandate_expired=False,
            issued_payment_token="eyJhbGciOiJFZERTQSJ9.eyJtYW5kYXRlIjoidHJ1ZSJ9.sig",
            token_entropy_bits=160,
            token_embeds_reversible_mandate=True,
            complete_checkout_has_mandate_derived_token=True,
            raw_http_response_bytes=raw_body,
            content_digest_header=digest,
        )
        self.assertFalse(composite.admitted)
        self.assertEqual(composite.decision_code, "UCP_AP2_COMPOSITE_REVERSIBLE_TOKEN_REJECTED")

        # JCS canonicalization before Content-Digest check rejected
        jcs_err = evaluate_ucp_ap2_token_issuance_and_content_digest_guard(
            ap2_negotiated=True,
            tokenize_request={
                "credential": {
                    "type": "ap2_payment_mandate",
                    "payment_mandate": "sdjwt",
                    "checkout_jwt": "jws",
                },
                "binding": {"type": "dev.ucp.shopping.checkout", "id": "chk_abc123"},
            },
            checkout_jwt_transaction_id="tx_01",
            mandate_transaction_id="tx_01",
            mandate_signature_valid=True,
            mandate_expired=False,
            issued_payment_token="tok_opaque_9f8e7d6c5b4a3f2e1d0c9b8a",
            token_entropy_bits=160,
            token_embeds_reversible_mandate=False,
            complete_checkout_has_mandate_derived_token=True,
            raw_http_response_bytes=raw_body,
            content_digest_header=digest,
            verifier_canonicalized_body_with_jcs=True,
        )
        self.assertFalse(jcs_err.admitted)
        self.assertEqual(jcs_err.decision_code, "UCP_SHOPPING_CONTENT_DIGEST_JCS_MUTATION_FORBIDDEN")

    def test_ucp_catalog_search_purpose_and_reference_ids_guard(self) -> None:
        # Valid guided swap returning distinct substitute variant of same parent
        swap_ok = evaluate_ucp_catalog_search_purpose_and_reference_ids_guard(
            purpose="swap",
            reference_ids=["prod_boot_size10"],
            query="waterproof",
            filters={"price": {"max": 15000}},
            anchor_variant_to_parent={"prod_boot_size10": "prod_boot"},
            candidate_results=[
                {"id": "prod_boot_size10_wide", "parent_product_id": "prod_boot", "is_variant": True},
                {"id": "prod_hiker_size10", "parent_product_id": "prod_hiker", "is_variant": True},
            ],
        )
        self.assertTrue(swap_ok.admitted)
        self.assertTrue(swap_ok.distinct_variant_swap_allowed)

        # Search with reference_ids rejected
        bad_search = evaluate_ucp_catalog_search_purpose_and_reference_ids_guard(
            purpose="search",
            reference_ids=["prod_boot_size10"],
            query="boots",
            filters=None,
            anchor_variant_to_parent={},
            candidate_results=[],
        )
        self.assertFalse(bad_search.admitted)
        self.assertEqual(bad_search.decision_code, "UCP_CATALOG_SEARCH_REFERENCE_IDS_FORBIDDEN_ON_SEARCH")

        # Recommendation returning parent product of referenced variant rejected
        bad_rec = evaluate_ucp_catalog_search_purpose_and_reference_ids_guard(
            purpose="recommendation",
            reference_ids=["prod_boot_size10"],
            query=None,
            filters=None,
            anchor_variant_to_parent={"prod_boot_size10": "prod_boot"},
            candidate_results=[
                {"id": "prod_boot", "parent_product_id": "prod_boot", "is_variant": False},
            ],
        )
        self.assertFalse(bad_rec.admitted)
        self.assertEqual(bad_rec.decision_code, "UCP_CATALOG_RECOMMENDATION_PARENT_EXCLUSION_VIOLATION")

    def test_acp_feed_extensions_and_razorpay_upi_circle_guard(self) -> None:
        ok = evaluate_acp_feed_extensions_and_razorpay_upi_circle_guard(
            feed_metadata_extensions=[
                {
                    "name": "image_attributes",
                    "extends": ["$.Media.description", "$.Media.shot_style"],
                    "schema": "https://example.com/schemas/feed-extensions/image-attributes/2026-04-07.json",
                    "spec": "https://example.com/specs/feed-extensions/image-attributes",
                }
            ],
            feed_object_extension_paths=["$.Media.description", "$.Media.shot_style"],
            delegate_payment_request={
                "payment_method": {
                    "type": "upi_circle",
                    "delegate_id": "ucirc_P6WA7b8Ys3qKm2",
                    "user_vpa": "user@okicici",
                },
                "credential": {
                    "type": "upi_circle_cryptogram",
                    "value": "AQIDBAUGBwgJCgsMDQ4PEBESExQ=",
                    "expires_at": "2026-10-20T06:00:00Z",
                },
                "allowance": {
                    "reason": "one_time",
                    "max_amount": 49900,
                    "currency": "inr",
                    "checkout_session_id": "csn_01HV3P3XYZ789",
                    "merchant_id": "rzp_live_abc123xyz",
                },
                "risk_signals": [],
            },
            now_epoch_seconds=1792472400,
            cryptogram_expires_epoch_seconds=1792476000,
        )
        self.assertTrue(ok.admitted)
        self.assertEqual(ok.decision_code, "ACP_FEED_EXTENSIONS_AND_UPI_CIRCLE_VERIFIED")

        # Exceeding NPCI INR 15,000 (1,500,000 paise) limit rejected
        over_limit = evaluate_acp_feed_extensions_and_razorpay_upi_circle_guard(
            feed_metadata_extensions=[],
            feed_object_extension_paths=[],
            delegate_payment_request={
                "payment_method": {"type": "upi_circle", "delegate_id": "ucirc_P6WA7b8Ys3qKm2"},
                "credential": {"type": "upi_circle_cryptogram", "value": "AQID"},
                "allowance": {"max_amount": 1600000, "currency": "inr"},
                "risk_signals": [],
            },
            now_epoch_seconds=1792472400,
            cryptogram_expires_epoch_seconds=1792476000,
        )
        self.assertFalse(over_limit.admitted)
        self.assertEqual(over_limit.decision_code, "ACP_UPI_CIRCLE_CURRENCY_OR_NPCI_LIMIT_EXCEEDED")

    def test_ap2_open_mandate_hash_entropy_and_tap_rfc9421_guard(self) -> None:
        claims_a = {"merchant": "m_1", "budget": {"currency": "USD", "max": 5000}, "items": ["a", "b"]}
        claims_b = {"items": ["a", "b"], "budget": {"max": 5000, "currency": "USD"}, "merchant": "m_1"}

        res_a = evaluate_ap2_open_mandate_hash_entropy_and_tap_rfc9421_guard(
            unsigned_open_checkout_mandate_claims=claims_a,
            hashed_over_jws_compact_envelope=False,
            applied_unicode_normalization_before_hash=False,
            checkout_jwt_signature_alg="Ed25519",
            checkout_jwt_payload_entropy_bits=128,
            tap_signature_base_lines=[
                '"@authority": merchant.example.com',
                '"@path": /checkout',
                '"@signature-params": ("@authority" "@path");created=1792470000;keyid="did:web:agent.example#k1";alg="ed25519";nonce="n_123"',
            ],
            tap_signature_input_components_raw='"@authority" "@path"',
            tap_signature_alg="ed25519",
        )
        res_b = evaluate_ap2_open_mandate_hash_entropy_and_tap_rfc9421_guard(
            unsigned_open_checkout_mandate_claims=claims_b,
            hashed_over_jws_compact_envelope=False,
            applied_unicode_normalization_before_hash=False,
            checkout_jwt_signature_alg="Ed25519",
            checkout_jwt_payload_entropy_bits=128,
            tap_signature_base_lines=[
                '"@authority": merchant.example.com',
                '"@path": /checkout',
                '"@signature-params": ("@authority" "@path");created=1792470000;keyid="did:web:agent.example#k1";alg="ed25519";nonce="n_123"',
            ],
            tap_signature_input_components_raw='"@authority" "@path"',
            tap_signature_alg="ed25519",
        )
        self.assertTrue(res_a.admitted)
        self.assertEqual(res_a.open_mandate_hash_hex, res_b.open_mandate_hash_hex)

        # Space-joined single-blob covered components rejected
        bad_tap = evaluate_ap2_open_mandate_hash_entropy_and_tap_rfc9421_guard(
            unsigned_open_checkout_mandate_claims=claims_a,
            hashed_over_jws_compact_envelope=False,
            applied_unicode_normalization_before_hash=False,
            checkout_jwt_signature_alg="Ed25519",
            checkout_jwt_payload_entropy_bits=128,
            tap_signature_base_lines=[
                '"@authority": merchant.example.com',
                '"@path": /checkout',
                '"@signature-params": ("@authority @path");created=1792470000',
            ],
            tap_signature_input_components_raw='"@authority @path"',
            tap_signature_alg="ed25519",
        )
        self.assertFalse(bad_tap.admitted)
        self.assertEqual(bad_tap.decision_code, "TAP_RFC9421_MALFORMED_COVERED_COMPONENTS_OR_ALG")


if __name__ == "__main__":
    unittest.main()
