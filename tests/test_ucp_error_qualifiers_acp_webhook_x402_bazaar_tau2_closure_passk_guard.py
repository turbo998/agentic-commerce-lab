"""Unit tests for Stage 96 deterministic guardrails."""

from __future__ import annotations

import hashlib
import hmac
import unittest

from lab.ucp_error_qualifiers_acp_webhook_x402_bazaar_tau2_closure_passk_guard import (
    validate_acp_webhook_replay_and_error_enum_guard,
    validate_tau2_closure_reason_passk_and_coercion_guard,
    validate_ucp_status_error_qualifiers_and_instruments_guard,
    validate_x402_eip3009_error_and_bazaar_metadata_guard,
)


class TestStage96Guards(unittest.TestCase):
    def test_ucp_status_error_qualifiers_and_instruments_valid(self) -> None:
        payload = {
            "ucp_response_envelope": {
                "ucp": {"version": "2026-01-23", "status": "error"},
                "messages": [
                    {
                        "type": "error",
                        "code": "out_of_stock",
                        "severity": "unrecoverable",
                        "content": "All requested items are currently out of stock.",
                    }
                ],
                "continue_url": "https://merchant.example.com/",
                "wrapped_under_cart_key": False,
            },
            "payment_qualifier_check": {
                "instrument_qualifiers": ["com.visa.infinite", "com.merchant.vip_tier"],
                "benefits_applied_pre_completion": True,
                "required_benefit_qualifiers": ["com.visa.infinite"],
                "verified_completion_qualifiers": ["com.visa.infinite", "com.merchant.vip_tier"],
            },
            "handler_available_instruments_check": {
                "available_instruments": [
                    {"type": "card", "brands": ["visa", "mastercard"]},
                ],
                "selected_instrument": {"type": "card", "brand": "visa"},
            },
        }
        res = validate_ucp_status_error_qualifiers_and_instruments_guard(payload)
        self.assertTrue(res["allowed"])

    def test_ucp_error_with_resource_or_qualifier_mismatch_blocked(self) -> None:
        payload = {
            "ucp_response_envelope": {
                "ucp": {"version": "2026-01-23", "status": "error"},
                "id": "chk_invalid_resource_on_error",
                "messages": [],
                "wrapped_under_cart_key": True,
            },
            "payment_qualifier_check": {
                "instrument_qualifiers": ["invalid_non_reverse_domain"],
                "benefits_applied_pre_completion": True,
                "required_benefit_qualifiers": ["com.visa.infinite"],
                "verified_completion_qualifiers": ["com.visa.classic"],
            },
            "handler_available_instruments_check": {
                "available_instruments": [
                    {"type": "card", "brands": ["visa", "mastercard"]},
                ],
                "selected_instrument": {"type": "card", "brand": "amex"},
            },
        }
        res = validate_ucp_status_error_qualifiers_and_instruments_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn(
            "UCP_ERROR_RESPONSE_MUST_NOT_INCLUDE_RESOURCE_OR_CART_WRAPPER", res["violations"]
        )
        self.assertIn("UCP_PAYMENT_QUALIFIER_BENEFIT_MISMATCH_AT_COMPLETION", res["violations"])
        self.assertIn("UCP_HANDLER_AVAILABLE_INSTRUMENTS_CONSTRAINT_VIOLATION", res["violations"])

    def test_acp_webhook_replay_and_error_enum_valid(self) -> None:
        secret = "whsec_test_96"
        raw_body = '{"event":"order.updated","id":"ord_96"}'
        ts = 1761000000
        sig = hmac.new(
            secret.encode("utf-8"),
            f"{ts}.{raw_body}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        payload = {
            "webhook_verification": {
                "merchant_signature_header": f"t={ts},v1={sig}",
                "current_timestamp": 1761000120,
                "tolerance_seconds": 300,
                "shared_secret": secret,
                "raw_body": raw_body,
            },
            "delegate_payment_error_check": {
                "http_status": 401,
                "type": "unauthorized",
                "code": "unauthorized",
                "client_rejected_unrecognized_enum": False,
            },
        }
        res = validate_acp_webhook_replay_and_error_enum_guard(payload)
        self.assertTrue(res["allowed"])

    def test_acp_expired_webhook_or_strict_enum_rejection_blocked(self) -> None:
        payload = {
            "webhook_verification": {
                "merchant_signature_header": "t=1760000000,v1=" + ("a" * 64),
                "current_timestamp": 1760000900,
                "tolerance_seconds": 300,
                "shared_secret": "whsec_test_96",
                "raw_body": "{}",
            },
            "delegate_payment_error_check": {
                "http_status": 503,
                "type": "service_unavailable",
                "code": "processing_error",
                "client_rejected_unrecognized_enum": True,
            },
        }
        res = validate_acp_webhook_replay_and_error_enum_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("ACP_WEBHOOK_TIMESTAMP_OUTSIDE_REPLAY_WINDOW", res["violations"])
        self.assertIn("ACP_DELEGATE_ERROR_503_UNAVAILABLE_ALIGNMENT_REQUIRED", res["violations"])
        self.assertIn("ACP_DELEGATE_ERROR_FORWARD_COMPAT_VIOLATED", res["violations"])

    def test_x402_eip3009_error_and_bazaar_metadata_valid(self) -> None:
        payload = {
            "eip3009_diagnostic": {
                "phase": "settle_transfer",
                "failure_cause": "nonce_already_used",
                "mapped_error": "ErrEip3009NonceAlreadyUsed",
            },
            "bazaar_service_metadata": {
                "serviceName": "Alpha Market Feed",
                "tags": ["Analytics", "DeFi", "Base"],
                "iconUrl": "https://cdn.example.com/icons/alpha.png",
            },
        }
        res = validate_x402_eip3009_error_and_bazaar_metadata_guard(payload)
        self.assertTrue(res["allowed"])

    def test_x402_generic_error_or_loopback_icon_url_blocked(self) -> None:
        payload = {
            "eip3009_diagnostic": {
                "phase": "verify_simulation_rpc",
                "failure_cause": "rpc_unavailable",
                "mapped_error": "ErrInvalidPayload",
            },
            "bazaar_service_metadata": {
                "serviceName": "Bad\x07Name",
                "tags": ["DeFi", "defi"],
                "iconUrl": "http://localhost:8080/icon.png",
            },
        }
        res = validate_x402_eip3009_error_and_bazaar_metadata_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn(
            "X402_EIP3009_SIMULATION_RPC_MAPPED_TO_GENERIC_PAYLOAD_ERROR", res["violations"]
        )
        self.assertIn("X402_BAZAAR_ICON_URL_UNSAFE_OR_INVALID", res["violations"])

    def test_tau2_closure_reason_passk_and_coercion_valid(self) -> None:
        payload = {
            "bank_account_closure": {"reason": "simplifying_finances"},
            "pass_hat_k_metrics": {
                "compared_by_enum_value": True,
                "configured_total_tasks": 2,
                "reported_total_tasks": 2,
                "expected_pass_hat_1": 0.5,
                "reported_pass_hat_1": 0.5,
            },
            "tool_kwarg_coercion": {
                "schema_type": "integer",
                "raw_wire_value": 2.0,
                "persisted_db_value": 2,
            },
            "hallucination_retry_audit": {
                "final_retry_reviewed": True,
                "checkpointed_selected_only": True,
            },
        }
        res = validate_tau2_closure_reason_passk_and_coercion_guard(payload)
        self.assertTrue(res["allowed"])

    def test_tau2_freetext_closure_or_dropped_infra_task_blocked(self) -> None:
        payload = {
            "bank_account_closure": {
                "reason": "Customer requested closure after transferring balance"
            },
            "pass_hat_k_metrics": {
                "compared_by_enum_value": False,
                "configured_total_tasks": 2,
                "reported_total_tasks": 1,
                "expected_pass_hat_1": 0.5,
                "reported_pass_hat_1": 1.0,
            },
            "tool_kwarg_coercion": {
                "schema_type": "integer",
                "raw_wire_value": 2.0,
                "persisted_db_value": 2.0,
            },
            "hallucination_retry_audit": {
                "final_retry_reviewed": False,
                "checkpointed_selected_only": False,
            },
        }
        res = validate_tau2_closure_reason_passk_and_coercion_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("TAU2_BANK_CLOSURE_REASON_NOT_IN_CANONICAL_SET", res["violations"])
        self.assertIn("TAU2_ALL_INFRA_ERROR_TASK_DROPPED_FROM_DENOMINATOR", res["violations"])
        self.assertIn("TAU2_UNCOERCED_FLOAT_PERSISTED_IN_INTEGER_FIELD", res["violations"])


if __name__ == "__main__":
    unittest.main()
