"""Unit tests for Stage 29: Commodity Weather-Index Forward Escrow, M2M eSIM Roaming CDR Settlement & Open-Banking ISO 20022 pain.008 Direct Debit Guard."""

from __future__ import annotations

import unittest

from lab.commodity_weather_esim_roaming_pain008_guard import (
    evaluate_commodity_weather_index_forward_escrow,
    evaluate_m2m_esim_roaming_cdr_settlement,
    verify_open_banking_pain008_direct_debit_mandate,
)
from lab.trade_sovereign_settlement_bench import (
    run_trade_sovereign_settlement_benchmark,
)


class TestCommodityWeatherEsimRoamingPain008Guard(unittest.TestCase):
    def test_commodity_weather_index_drought_hedge_and_oracle_guard(self) -> None:
        unverified = evaluate_commodity_weather_index_forward_escrow(
            {
                "contract_id": "cmd_coffee_01",
                "oracle_quorum_verified": False,
                "observed_rainfall_mm": 20,
                "drought_trigger_mm": 50,
                "forward_notional_minor": 1_000_000,
            }
        )
        self.assertFalse(unverified["settled"])
        self.assertEqual(
            unverified["decision_code"],
            "UNVERIFIED_WEATHER_ORACLE_QUORUM_BLOCKED",
        )

        drought = evaluate_commodity_weather_index_forward_escrow(
            {
                "contract_id": "cmd_coffee_02",
                "oracle_quorum_verified": True,
                "observed_rainfall_mm": 22,
                "drought_trigger_mm": 50,
                "forward_notional_minor": 1_000_000,
                "hedge_rebate_bps": 2_500,
            }
        )
        self.assertTrue(drought["settled"])
        self.assertEqual(
            drought["decision_code"],
            "PARAMETRIC_WEATHER_HEDGE_PAYOUT_TRIGGERED",
        )
        self.assertEqual(drought["hedge_payout_to_buyer_minor"], 250_000)
        self.assertEqual(drought["net_seller_settlement_minor"], 750_000)

    def test_m2m_esim_roaming_cdr_replay_and_rate_cap(self) -> None:
        rate_breach = evaluate_m2m_esim_roaming_cdr_settlement(
            {
                "cdr_batch_id": "cdr_sgp32_01",
                "visited_network_signature_valid": True,
                "batch_replay_detected": False,
                "billed_megabytes": 500,
                "rate_per_mb_minor": 120,
                "max_wholesale_rate_per_mb_minor": 40,
            }
        )
        self.assertFalse(rate_breach["settled"])
        self.assertEqual(
            rate_breach["decision_code"],
            "ROAMING_WHOLESALE_RATE_CAP_BREACH_BLOCKED",
        )

        settled = evaluate_m2m_esim_roaming_cdr_settlement(
            {
                "cdr_batch_id": "cdr_sgp32_02",
                "visited_network_signature_valid": True,
                "batch_replay_detected": False,
                "billed_megabytes": 500,
                "rate_per_mb_minor": 30,
                "max_wholesale_rate_per_mb_minor": 40,
            }
        )
        self.assertTrue(settled["settled"])
        self.assertEqual(settled["decision_code"], "M2M_ESIM_ROAMING_CDR_SETTLED")
        self.assertEqual(settled["total_settlement_minor"], 15_000)

    def test_open_banking_pain008_direct_debit_mandate(self) -> None:
        unregistered = verify_open_banking_pain008_direct_debit_mandate(
            {
                "umr_id": "UMR-SEPA-2026-01",
                "umr_signature_valid": True,
                "debtor_iban_binding_matches": True,
                "debtor_bank_b2b_mandate_registered": False,
                "debit_amount_minor": 250_000,
                "max_single_debit_minor": 500_000,
            }
        )
        self.assertFalse(unregistered["allowed"])
        self.assertEqual(
            unregistered["decision_code"],
            "PAIN008_B2B_PRE_REGISTRATION_OR_CAP_BLOCKED",
        )

        valid = verify_open_banking_pain008_direct_debit_mandate(
            {
                "umr_id": "UMR-SEPA-2026-02",
                "umr_signature_valid": True,
                "debtor_iban_binding_matches": True,
                "debtor_bank_b2b_mandate_registered": True,
                "debit_amount_minor": 250_000,
                "max_single_debit_minor": 500_000,
            }
        )
        self.assertTrue(valid["allowed"])
        self.assertEqual(
            valid["decision_code"],
            "ISO20022_PAIN008_DIRECT_DEBIT_SETTLED",
        )

    def test_trade_sovereign_settlement_benchmark_16_scenarios(self) -> None:
        report = run_trade_sovereign_settlement_benchmark()
        self.assertEqual(report["total_scenarios"], 16)
        self.assertEqual(report["ai_native_passed"], 16)
        self.assertEqual(report["classic_3tier_passed"], 1)
        self.assertEqual(report["reversed_order_passed"], 16)


if __name__ == "__main__":
    unittest.main()
