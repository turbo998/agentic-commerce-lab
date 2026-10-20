"""Unit tests for Stage 110 guardrails."""

from __future__ import annotations

import unittest

from lab.ucp_webhook_sig_namespace_acp_seller_backed_ap2_budget_x402_nowallet_tau2_guard import (
    validate_acp_seller_backed_intervention_and_version_mismatch_guard,
    validate_ap2_budget_iso8601_and_x402_nowallet_guard,
    validate_tau2_historical_packages_time_verified_and_active_refuel_guard,
    validate_ucp_webhook_sig_namespace_and_quantity_unit_guard,
)


class TestStage110Guardrails(unittest.TestCase):
    def test_ucp_valid_webhook_namespace_and_quantity_unit(self) -> None:
        res = validate_ucp_webhook_sig_namespace_and_quantity_unit_guard(
            {
                "order_webhook": {
                    "headers": {"Webhook-Id": "wh_01", "Webhook-Timestamp": "1776643200"},
                    "signature_input": 'sig1=("@method" "@authority" "@path" "content-type" "webhook-id" "webhook-timestamp" "ucp-agent");created=1776643200',
                },
                "ucp": {
                    "version": "2026-01-11",
                    "payment_handlers": {"dev.shopify.shop_pay": [{"id": "sp"}]},
                    "map_order": {"payment_handlers": ["dev.shopify.shop_pay"]},
                    "request_constraints": {
                        "required": ["billing_address"],
                        "properties": {"quantity": {"const": 150}},
                    },
                },
                "submitted_request": {"billing_address": "123 Market St", "quantity": 150},
                "line_item": {
                    "quantity": 150,
                    "item": {
                        "price": 1299,
                        "quantity_unit": {"unit": "KGM", "scale": 2, "display_text": "kg"},
                    },
                    "declared_total_minor": 1949,
                },
            }
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.decision_code, "UCP_WEBHOOK_SIG_NAMESPACE_AND_QUANTITY_UNIT_VERIFIED")

    def test_ucp_rejects_unsigned_webhook_headers_and_c62_scale(self) -> None:
        res1 = validate_ucp_webhook_sig_namespace_and_quantity_unit_guard(
            {
                "order_webhook": {
                    "headers": {"Webhook-Id": "wh_01", "Webhook-Timestamp": "1776643200"},
                    "signature_input": 'sig1=("@method" "@authority" "@path" "content-type");created=1776643200',
                },
                "ucp": {"version": "2026-01-11"},
            }
        )
        self.assertFalse(res1.allowed)
        self.assertEqual(res1.decision_code, "UCP_WEBHOOK_HEADER_UNSIGNED_REJECTED")

        res2 = validate_ucp_webhook_sig_namespace_and_quantity_unit_guard(
            {
                "ucp": {"version": "2026-01-11"},
                "line_item": {
                    "quantity": 10,
                    "item": {
                        "price": 500,
                        "quantity_unit": {"unit": "C62", "scale": 2, "display_text": "each"},
                    },
                },
            }
        )
        self.assertFalse(res2.allowed)
        self.assertEqual(res2.decision_code, "UCP_EACH_UNIT_NONZERO_SCALE_REJECTED")

    def test_acp_valid_seller_backed_and_intervention_required(self) -> None:
        res = validate_acp_seller_backed_intervention_and_version_mismatch_guard(
            {
                "message_error": {"type": "intervention_required", "resolution": "complete_3ds_challenge"},
                "seller_backed_handler": {
                    "name": "dev.acp.seller_backed.points",
                    "requires_delegate_payment": True,
                    "requires_pci_compliance": False,
                    "raw_credentials_transferred": False,
                    "points_balance_minor": 5000,
                    "purchase_amount_minor": 4200,
                },
                "version_mismatch_error": {"supported_versions": ["2026-04-17", "2026-01-30"]},
            }
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.decision_code, "ACP_SELLER_BACKED_INTERVENTION_AND_VERSION_VERIFIED")

    def test_acp_rejects_typo_and_insufficient_points(self) -> None:
        res1 = validate_acp_seller_backed_intervention_and_version_mismatch_guard(
            {"message_error": {"type": "interventioned_required"}}
        )
        self.assertFalse(res1.allowed)
        self.assertEqual(res1.decision_code, "ACP_MESSAGE_ERROR_TYPE_INVALID")

        res2 = validate_acp_seller_backed_intervention_and_version_mismatch_guard(
            {
                "seller_backed_handler": {
                    "name": "dev.acp.seller_backed.points",
                    "requires_delegate_payment": True,
                    "requires_pci_compliance": False,
                    "points_balance_minor": 1000,
                    "purchase_amount_minor": 2500,
                }
            }
        )
        self.assertFalse(res2.allowed)
        self.assertEqual(res2.decision_code, "ACP_SELLER_BACKED_POINTS_INSUFFICIENT_BALANCE")

    def test_ap2_and_x402_valid_budget_window_and_nowallet(self) -> None:
        res = validate_ap2_budget_iso8601_and_x402_nowallet_guard(
            {
                "ap2_budget": {"currency": "USD", "max": 19.99, "requested_amount_minor": 1999},
                "ap2_execution_window": {
                    "execution_date": "2026-05-01T08:00:00+09:00",
                    "not_before": "2026-03-31T00:00:00Z",
                    "not_after": "2026-04-30T23:59:59Z",
                },
                "x402_no_wallet": {
                    "requires": {"asset": "USDC", "network": "eip155:8453", "amount": "5000"},
                    "anyWalletWorks": True,
                    "auto_execute_install_command": False,
                    "wallets": [{"name": "AgentWallet", "custodial": False}],
                },
            }
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.decision_code, "AP2_BUDGET_ISO8601_AND_X402_NOWALLET_VERIFIED")

    def test_ap2_and_x402_reject_jpy_overflow_and_offset_escape(self) -> None:
        res1 = validate_ap2_budget_iso8601_and_x402_nowallet_guard(
            {"ap2_budget": {"currency": "JPY", "max": 1000, "requested_amount_minor": 100000}}
        )
        self.assertFalse(res1.allowed)
        self.assertEqual(res1.decision_code, "AP2_BUDGET_ISO4217_CAP_EXCEEDED")

        res2 = validate_ap2_budget_iso8601_and_x402_nowallet_guard(
            {
                "ap2_execution_window": {
                    "execution_date": "2026-04-30T23:59:59-09:00",
                    "not_before": "2026-03-31T00:00:00Z",
                    "not_after": "2026-04-30T23:59:59Z",
                }
            }
        )
        self.assertFalse(res2.allowed)
        self.assertEqual(res2.decision_code, "AP2_EXECUTION_DATE_OUTSIDE_CHRONOLOGICAL_WINDOW")

    def test_tau2_valid_historical_package_time_and_active_refuel(self) -> None:
        res = validate_tau2_historical_packages_time_verified_and_active_refuel_guard(
            {
                "historical_package": {
                    "benchmark_frame": "voice-v2-banking",
                    "package_name": "gpt-5.4_openai_2026-10-02_banking",
                    "judges_root_supplied": False,
                    "cell_condition_fingerprints": ["fp_banking_01", "fp_banking_01"],
                },
                "banking_time_verified": {
                    "raw": "2025-11-14T03:40:00",
                    "gold_canonical": "2025-11-14 03:40:00 EST",
                },
                "telecom_refuel": {"line_status": "Active", "refuel_gb": 2.0},
            }
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.decision_code, "TAU2_HISTORICAL_PACKAGES_TIME_AND_ACTIVE_REFUEL_VERIFIED")

    def test_tau2_rejects_suspended_refuel_and_fabricated_time(self) -> None:
        res1 = validate_tau2_historical_packages_time_verified_and_active_refuel_guard(
            {"telecom_refuel": {"line_status": "Suspended", "refuel_gb": 2.0}}
        )
        self.assertFalse(res1.allowed)
        self.assertEqual(res1.decision_code, "TAU2_TELECOM_INACTIVE_LINE_REFUEL_BLOCKED")

        res2 = validate_tau2_historical_packages_time_verified_and_active_refuel_guard(
            {
                "banking_time_verified": {
                    "raw": "2024-01-01 00:00:00 EST",
                    "gold_canonical": "2025-11-14 03:40:00 EST",
                }
            }
        )
        self.assertFalse(res2.allowed)
        self.assertEqual(res2.decision_code, "TAU2_TIME_VERIFIED_MISMATCH_OR_FABRICATED")


if __name__ == "__main__":
    unittest.main()
