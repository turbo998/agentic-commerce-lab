"""Unit tests for Stage 54 deterministic guards."""

from __future__ import annotations

from enum import Enum
import unittest

from lab.ucp_schema_bundle_acp_drift_ap2_aud_tau2_intake_guard import (
    verify_acp_schema_openapi_property_drift,
    verify_ap2_kb_aud_cnf_and_poppy_dpop_rules,
    verify_tau2_intake_and_tap_x402_checkout,
    verify_ucp_schema_bundle_and_seller_logo,
)


class _DummyUseEnum(Enum):
    SIG = "sig"


class Stage54GuardTest(unittest.TestCase):
    def test_ucp_schema_bundle_and_seller_logo_guard(self) -> None:
        ok = verify_ucp_schema_bundle_and_seller_logo(
            schema_path="source/schemas/shopping/../shopping/catalog.json",
            unbundled_refs={
                "pagination": "types/pagination.json#/$defs/request",
                "media": "../../common/types/media.json",
                "local_alias": "#/$defs/internal_only",
            },
            bundled_properties={
                "pagination": {"$ref": "types/pagination.json#/$defs/request"},
                "media": {"$ref": "../../common/types/media.json"},
                "local_alias": {"type": "object"},
            },
            variant_payload={
                "id": "var_01",
                "seller": {
                    "name": "Example Grocery",
                    "logo": {
                        "type": "image",
                        "url": "https://cdn.example.com/grocery-logo.png",
                        "alt_text": "Example Grocery logo",
                        "width": 128,
                        "height": 128,
                    },
                },
            },
            platform_claims_seller_discovery_authority=False,
        )
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.restored_ref_count, 2)
        self.assertTrue(ok.seller_logo_present)
        self.assertFalse(ok.seller_authority_bound)

        bad = verify_ucp_schema_bundle_and_seller_logo(
            schema_path="source/schemas/shopping/catalog.json",
            unbundled_refs={"pagination": "types/pagination.json#/$defs/request"},
            bundled_properties={"pagination": {"type": "object"}},
            variant_payload={
                "id": "var_02",
                "seller": {
                    "name": "Example Grocery",
                    "logo": {"type": "image", "url": "http://insecure.example/logo.png"},
                },
            },
            platform_claims_seller_discovery_authority=True,
        )
        self.assertFalse(bad.allowed)
        self.assertIn("UNRESTORED_BUNDLED_CROSS_FILE_REF:pagination", bad.violations)
        self.assertIn("INVALID_SELLER_LOGO_URL", bad.violations)
        self.assertIn("MISSING_SELLER_LOGO_ALT_TEXT", bad.violations)
        self.assertIn("SELLER_LOGO_AUTHORITY_CONFUSION_BLOCKED", bad.violations)

    def test_acp_schema_openapi_property_drift_guard(self) -> None:
        ok = verify_acp_schema_openapi_property_drift(
            version="2026-04-17",
            spec_name="agentic_checkout",
            json_schema_defs={
                "Address": {"properties": {"line1": {}, "company": {}}},
                "PaymentHandler": {"properties": {"id": {}, "display_order": {}}},
            },
            openapi_schemas={
                "Address": {"properties": {"line1": {}}},
                "PaymentHandler": {"properties": {"id": {}, "display_order": {}}},
            },
            known_property_drift={"2026-04-17/agentic_checkout/Address/company json-only"},
            allof_composed_schemas={
                "CheckoutSessionWithOrder": {
                    "base_additional_properties": False,
                    "base_properties": ("id", "status", "order"),
                    "sibling_properties": ("order",),
                }
            },
        )
        self.assertTrue(ok.allowed)

        bad = verify_acp_schema_openapi_property_drift(
            version="2026-04-17",
            spec_name="agentic_checkout",
            json_schema_defs={
                "Address": {"properties": {"line1": {}}},
                "Order": {"properties": {"id": {}, "client_reference_id": {}}},
            },
            openapi_schemas={
                "Address": {"properties": {"line1": {}}},
                "Order": {"properties": {"id": {}}},
                "PaymentHandler": {"display_order": {"type": "integer"}, "properties": {"id": {}}},
            },
            known_property_drift={"2026-04-17/agentic_checkout/Address/company json-only"},
            allof_composed_schemas={
                "DelegateAuthenticationSessionWithResult": {
                    "base_additional_properties": False,
                    "base_properties": ("id", "status"),
                    "sibling_properties": ("authentication_result",),
                }
            },
        )
        self.assertFalse(bad.allowed)
        self.assertIn("PAYMENT_HANDLER_DISPLAY_ORDER_MISINDENTED:PaymentHandler", bad.violations)
        self.assertIn(
            "UNLISTED_SCHEMA_OPENAPI_PROPERTY_DRIFT:2026-04-17/agentic_checkout/Order/client_reference_id json-only",
            bad.violations,
        )
        self.assertIn(
            "STALE_KNOWN_DRIFT_ENTRY:2026-04-17/agentic_checkout/Address/company json-only",
            bad.violations,
        )
        self.assertIn(
            "ALLOF_ADDITIONAL_PROPERTIES_SIBLING_STARVATION:DelegateAuthenticationSessionWithResult:authentication_result",
            bad.violations,
        )

    def test_ap2_kb_aud_cnf_and_poppy_dpop_guard(self) -> None:
        ok = verify_ap2_kb_aud_cnf_and_poppy_dpop_rules(
            terminal_hop_typ="kb+sd-jwt+kb",
            token_aud="https://honest-merchant.example/ap2",
            expected_aud="https://honest-merchant.example/ap2",
            token_nonce="nonce-2026-10-20",
            expected_nonce="nonce-2026-10-20",
            cnf_jwk_payload={"kty": "EC", "crv": "P-256", "use": "sig", "alg": "ES256"},
            receipt_reference="ref_123",
            has_reference_in_store_cb=None,
            poppy_request_target="api_write",
            poppy_carries_session_token=True,
            poppy_dpop_proof={"alg": "ES256", "jti": "e1j3V_bKic8-LAEBq7Rw2g"},
            poppy_http_method="POST",
            poppy_idempotency_key="4f1c2e8a-9b7d-4c3e-a5f6-0d8b1e2c3a4f",
        )
        self.assertTrue(ok.allowed)
        self.assertTrue(ok.terminal_aud_verified)
        self.assertEqual(ok.dpop_jti_bits, 128)

        bad = verify_ap2_kb_aud_cnf_and_poppy_dpop_rules(
            terminal_hop_typ="kb+sd-jwt+kb",
            token_aud="https://attacker.example/ap2",
            expected_aud="https://honest-merchant.example/ap2",
            token_nonce="nonce-2026-10-20",
            expected_nonce="nonce-2026-10-20",
            cnf_jwk_payload={"kty": "EC", "crv": "P-256", "use": _DummyUseEnum.SIG},
            receipt_reference="ref_missing",
            has_reference_in_store_cb=lambda ref: False,
            poppy_request_target="api_write",
            poppy_carries_session_token=True,
            poppy_dpop_proof={"alg": "HS256", "jti": "short_jti"},
            poppy_http_method="POST",
            poppy_idempotency_key=None,
        )
        self.assertFalse(bad.allowed)
        self.assertIn("AP2_KB_SD_JWT_AUD_MISMATCH", bad.violations)
        self.assertIn("AP2_CNF_JWK_ENUM_NOT_JSON_SERIALIZED:use", bad.violations)
        self.assertIn("AP2_RECEIPT_REFERENCE_NOT_IN_STORE", bad.violations)
        self.assertIn("POPPY_INVALID_DPOP_ALG:HS256", bad.violations)
        self.assertIn("POPPY_API_WRITE_MISSING_IDEMPOTENCY_KEY", bad.violations)

    def test_tau2_intake_and_tap_x402_checkout_guard(self) -> None:
        # 97 * 1000 + 1 = 97001 -> mod 97 == 1
        ok = verify_tau2_intake_and_tap_x402_checkout(
            consent_obtained=True,
            ordered_missing_fields=("appt_date", "appt_time", "member_id"),
            logged_captures={
                "appt_date": "2026-10-20",
                "appt_time": "10:30 AM",
                "member_id": "97001",
            },
            submitted_fields={
                "appt_date": "2026-10-20",
                "appt_time": "10:30 AM",
                "member_id": "97001",
            },
            submit_call_count=1,
            call_ended_early=False,
            submit_and_end_call_same_turn=False,
            field_types={
                "appt_date": "date",
                "appt_time": "time",
                "member_id": "member_id_mod97",
            },
            payment_signature_header="sig_x402_base_usdc",
            payment_response_header="resp_x402_settled",
            facilitator_settled=True,
        )
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.x402_mode, "mode_b_facilitator_settle")

        bad = verify_tau2_intake_and_tap_x402_checkout(
            consent_obtained=False,
            ordered_missing_fields=("appt_date", "member_id"),
            logged_captures={"appt_date": "10/20/2026", "extra_ssn": "123"},
            submitted_fields={"appt_date": "10/20/2026", "member_id": "97002"},
            submit_call_count=1,
            call_ended_early=False,
            submit_and_end_call_same_turn=True,
            external_or_invented_fields=("member_id",),
            field_types={"appt_date": "date", "member_id": "member_id_mod97"},
            payment_signature_header=None,
            payment_required_header=None,
        )
        self.assertFalse(bad.allowed)
        self.assertIn("TAU2_INTAKE_MISSING_CONSENT_BEFORE_COLLECTION", bad.violations)
        self.assertIn("EXTERNAL_OR_INVENTED_VALUE_BLOCKED", bad.violations)
        self.assertIn("UNSCHEDULED_FIELD_COLLECTION_BLOCKED:extra_ssn", bad.violations)
        self.assertIn("INVALID_DATE_OR_TIME_FORMAT:appt_date", bad.violations)
        self.assertIn("CODE_CHECK_DIGIT_INVALID:member_id", bad.violations)
        self.assertIn("SUBMIT_AND_END_CALL_SAME_TURN_BLOCKED", bad.violations)
        self.assertIn("TAP_X402_MISSING_PAYMENT_REQUIRED_HEADER", bad.violations)


if __name__ == "__main__":
    unittest.main()
