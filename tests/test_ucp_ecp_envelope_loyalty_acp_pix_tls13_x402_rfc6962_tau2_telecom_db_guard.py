"""Unit tests for Stage 106 deterministic protocol guardrails."""

from __future__ import annotations

import unittest

from lab.ucp_ecp_envelope_loyalty_acp_pix_tls13_x402_rfc6962_tau2_telecom_db_guard import (
    validate_acp_pix_tls13_webhook_and_integer_fulfillment_guard,
    validate_ap2_error_field_intent_cap_and_x402_rfc6962_tenzro_guard,
    validate_tau2_telecom_db_reward_custom_arch_and_cost_time_guard,
    validate_ucp_ecp_envelope_loyalty_order_label_and_version_guard,
)


class TestStage106Guards(unittest.TestCase):
    def test_ucp_ecp_envelope_loyalty_order_label_and_version_compliant(self) -> None:
        payload = {
            "ecp_response": {
                "has_jsonrpc_error": False,
                "is_transport_failure": False,
                "result_ucp_status": "ok",
                "method": "ec.payment.submit",
                "host_tore_down_on_ec_ready_error": True,
            },
            "loyalty_extension": {
                "loyalty_tier_disclosed": True,
                "earning_forecast_points": 450,
            },
            "order_and_version": {
                "order_id": "ord_internal_99812",
                "order_label": "#1042-NYC",
                "advertised_discovery_version": "2026-10-20",
            },
        }
        res = validate_ucp_ecp_envelope_loyalty_order_label_and_version_guard(payload)
        self.assertTrue(res["allowed"])
        self.assertEqual(res["violations"], [])

    def test_ucp_ecp_envelope_loyalty_order_label_and_version_violations(self) -> None:
        payload = {
            "ecp_response": {
                "has_jsonrpc_error": True,
                "is_transport_failure": False,
                "result_ucp_status": "error",
                "method": "ec.ready",
                "host_tore_down_on_ec_ready_error": False,
            },
            "loyalty_extension": {
                "loyalty_tier_disclosed": False,
                "earning_forecast_points": -10,
            },
            "order_and_version": {
                "order_id": "same_id",
                "order_label": "same_id",
                "advertised_discovery_version": "draft",
            },
        }
        res = validate_ucp_ecp_envelope_loyalty_order_label_and_version_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("UCP_325_DELEGATION_ERROR_IN_JSONRPC_ERROR_FIELD_FORBIDDEN", res["violations"])
        self.assertIn("UCP_325_EC_READY_ERROR_REQUIRES_HOST_TEARDOWN", res["violations"])
        self.assertIn("UCP_340_LOYALTY_TIER_DISCLOSURE_MISSING", res["violations"])
        self.assertIn("UCP_326_ORDER_ID_AND_HUMAN_LABEL_MUST_BE_DISTINCT_NON_EMPTY", res["violations"])
        self.assertIn("UCP_324_NON_DATE_DRAFT_VERSION_IN_PUBLIC_DISCOVERY_FORBIDDEN", res["violations"])

    def test_acp_pix_tls13_webhook_and_integer_fulfillment_compliant(self) -> None:
        payload = {
            "pix_payment": {
                "currency": "BRL",
                "provider": "mercado_pago",
                "cpf_or_cnpj": "12345678901",
            },
            "transport_and_webhook": {
                "tls_version": "TLSv1.3",
                "constant_time_signature_verified": True,
                "request_id": "req_webhook_01",
                "timestamp_skew_seconds": 15,
            },
            "fulfillment_option": {
                "type": "pickup",
                "amount_minor": 0,
                "pickup_location_id": "store_sp_01",
            },
        }
        res = validate_acp_pix_tls13_webhook_and_integer_fulfillment_guard(payload)
        self.assertTrue(res["allowed"])
        self.assertEqual(res["violations"], [])

    def test_acp_pix_tls13_webhook_and_integer_fulfillment_violations(self) -> None:
        payload = {
            "pix_payment": {
                "currency": "USD",
                "provider": "unknown_psp",
                "cpf_or_cnpj": "123",
            },
            "transport_and_webhook": {
                "tls_version": "TLSv1.2",
                "constant_time_signature_verified": False,
                "request_id": "",
                "timestamp_skew_seconds": 900,
            },
            "fulfillment_option": {
                "type": "pickup",
                "amount_minor": 12.50,
                "pickup_location_id": "",
            },
        }
        res = validate_acp_pix_tls13_webhook_and_integer_fulfillment_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("ACP_35_PIX_REQUIRES_BRL_CURRENCY", res["violations"])
        self.assertIn("ACP_32_TLS_1_3_REQUIRED", res["violations"])
        self.assertIn("ACP_18_FULFILLMENT_MONETARY_FIELD_MUST_BE_NON_NEGATIVE_INTEGER", res["violations"])
        self.assertIn("ACP_17_PICKUP_FULFILLMENT_MISSING_LOCATION_ID", res["violations"])

    def test_ap2_error_field_intent_cap_and_x402_rfc6962_tenzro_compliant(self) -> None:
        payload = {
            "ap2_validation_and_intent": {
                "has_validation_error": False,
                "cumulative_monthly_usdc_micro": 120_000_000,
                "monthly_cap_usdc_micro": 200_000_000,
                "eip712_intent_signature_valid": True,
            },
            "x402_rfc6962_and_tenzro": {
                "sth_ed25519_signature_valid": True,
                "merkle_inclusion_proof_valid": True,
                "tenzro_facade": "svm",
                "svm_9dec_spl_truncation_checked": True,
            },
        }
        res = validate_ap2_error_field_intent_cap_and_x402_rfc6962_tenzro_guard(payload)
        self.assertTrue(res["allowed"])
        self.assertEqual(res["violations"], [])

    def test_ap2_error_field_intent_cap_and_x402_rfc6962_tenzro_violations(self) -> None:
        payload = {
            "ap2_validation_and_intent": {
                "has_validation_error": True,
                "error_code": "",
                "field_path": "",
                "cumulative_monthly_usdc_micro": 250_000_000,
                "monthly_cap_usdc_micro": 200_000_000,
                "eip712_intent_signature_valid": False,
            },
            "x402_rfc6962_and_tenzro": {
                "sth_ed25519_signature_valid": False,
                "merkle_inclusion_proof_valid": True,
                "tenzro_facade": "canton",
                "canton_cip56_holding_transfer_valid": False,
            },
        }
        res = validate_ap2_error_field_intent_cap_and_x402_rfc6962_tenzro_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("AP2_64_VALIDATION_ERROR_MISSING_CODE_OR_FIELD_PATH", res["violations"])
        self.assertIn("AP2_216_NON_CUSTODIAL_INTENT_MONTHLY_CAP_EXCEEDED", res["violations"])
        self.assertIn("X402_88_RFC6962_STH_OR_INCLUSION_PROOF_INVALID", res["violations"])
        self.assertIn("X402_135_TENZRO_CANTON_CIP56_HOLDING_TRANSFER_INVALID", res["violations"])

    def test_tau2_telecom_db_reward_custom_arch_and_cost_time_compliant(self) -> None:
        payload = {
            "telecom_check": {
                "reward_basis": ["ACTION", "DB", "NL_ASSERTION"],
                "customer_line_pair_valid_in_db": True,
                "generated_task_count": 4538,
            },
            "leaderboard_submission": {
                "submission_type": "standard",
                "has_architectural_scaffold_change": False,
            },
            "cost_time_metrics": {
                "cost": 0.042,
                "user_cost": 0.008,
                "total_cost": 0.050,
                "duration_seconds": 18.5,
                "agent_time_seconds": 11.2,
                "user_time_seconds": 4.1,
                "tool_time_seconds": 2.9,
            },
        }
        res = validate_tau2_telecom_db_reward_custom_arch_and_cost_time_guard(payload)
        self.assertTrue(res["allowed"])
        self.assertEqual(res["violations"], [])

    def test_tau2_telecom_db_reward_custom_arch_and_cost_time_violations(self) -> None:
        payload = {
            "telecom_check": {
                "reward_basis": ["ACTION"],
                "customer_line_pair_valid_in_db": False,
                "generated_task_count": 120,
            },
            "leaderboard_submission": {
                "submission_type": "custom",
                "has_architectural_scaffold_change": False,
            },
            "cost_time_metrics": {
                "cost": 0.042,
                "user_cost": 0.008,
                "total_cost": 0.042,
                "duration_seconds": 10.0,
                "agent_time_seconds": 8.0,
                "user_time_seconds": 3.0,
                "tool_time_seconds": 2.0,
            },
        }
        res = validate_tau2_telecom_db_reward_custom_arch_and_cost_time_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("TAU2_462_TELECOM_REWARD_BASIS_MISSING_DB", res["violations"])
        self.assertIn("TAU2_462_SHADOWED_OR_INCOMPLETE_TELECOM_TASK_COUNT", res["violations"])
        self.assertIn("TAU2_444_SUBMISSION_TYPE_ARCHITECTURE_MISMATCH", res["violations"])
        self.assertIn("TAU2_443_TOTAL_COST_BREAKDOWN_MISMATCH", res["violations"])
        self.assertIn("TAU2_443_TIME_BREAKDOWN_EXCEEDS_DURATION_OR_NEGATIVE", res["violations"])


if __name__ == "__main__":
    unittest.main()
