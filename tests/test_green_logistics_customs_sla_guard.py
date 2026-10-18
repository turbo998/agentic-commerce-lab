"""Unit tests for Stage 16 HS-Code DDP Landed Cost (De-Minimis/CBAM), Cold-Chain MKT Escrow & Scope 3 Carbon Router."""

from __future__ import annotations

from decimal import Decimal
import unittest

from lab.green_logistics_customs_sla_guard import (
    evaluate_cold_chain_iot_telemetry_escrow,
    evaluate_hs_code_landed_cost_and_deminimis,
    main,
    optimize_carbon_pareto_carrier_route,
)


class GreenLogisticsCustomsSlaGuardTestSuite(unittest.TestCase):
    def test_valid_ddp_landed_cost_with_cbam_and_vat_passes(self) -> None:
        # CIF = 100_000 + 5_000 + 1_000 = 106_000
        # Duty (5%) = 5_300, Surtax (2%) = 2_120, CBAM (2.0t * 8_000) = 16_000
        # VAT base = 106_000 + 5_300 + 2_120 + 16_000 = 129_420
        # VAT (20%) = 25_884 -> Total DDP = 155_304
        res = evaluate_hs_code_landed_cost_and_deminimis(
            {
                "destination_jurisdiction": "EU",
                "declared_fob_minor": 100_000,
                "reference_fair_value_minor": 105_000,
                "freight_minor": 5_000,
                "insurance_minor": 1_000,
                "duty_rate_bps": 500,
                "surtax_rate_bps": 200,
                "import_vat_rate_bps": 2000,
                "embedded_emissions_tco2e": "2.0",
                "cbam_price_per_ton_minor": 8_000,
                "claimed_de_minimis_exempt": False,
                "quoted_ddp_total_minor": 155_304,
            }
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.decision_code, "CUSTOMS_DDP_LANDED_COST_VERIFIED")
        self.assertEqual(res.calculated_ddp_total_minor, 155_304)

    def test_blocks_undervaluation_fraud_and_split_consignment_structuring(self) -> None:
        underval = evaluate_hs_code_landed_cost_and_deminimis(
            {
                "destination_jurisdiction": "US",
                "declared_fob_minor": 40_000,  # $400 vs $850 fair value (0.47 < 0.70)
                "reference_fair_value_minor": 85_000,
                "freight_minor": 2_000,
                "insurance_minor": 500,
                "claimed_de_minimis_exempt": True,
            }
        )
        self.assertFalse(underval.allowed)
        self.assertEqual(underval.decision_code, "CUSTOMS_UNDERVALUATION_FRAUD_BLOCKED")

        structuring = evaluate_hs_code_landed_cost_and_deminimis(
            {
                "destination_jurisdiction": "EU",
                "declared_fob_minor": 12_000,
                "reference_fair_value_minor": 12_500,
                "freight_minor": 1_000,
                "insurance_minor": 200,
                "claimed_de_minimis_exempt": True,
                "same_consignee_24h_cumulative_minor": 36_000,  # > €150 cap
            }
        )
        self.assertFalse(structuring.allowed)
        self.assertEqual(
            structuring.decision_code,
            "CUSTOMS_SPLIT_CONSIGNMENT_EVASION_BLOCKED",
        )

    def test_cold_chain_arrhenius_mkt_verifies_compliant_and_claims_escrow_on_breach(self) -> None:
        compliant = evaluate_cold_chain_iot_telemetry_escrow(
            {
                "shipment_id": "shp_ok_01",
                "temperature_readings_c": [4.2, 4.5, 4.8, 5.1, 4.9, 4.6],
                "sample_interval_minutes": 5,
                "min_allowed_temp_c": 2.0,
                "max_allowed_temp_c": 8.0,
                "max_mkt_celsius": 8.0,
                "max_excursion_minutes": 15,
                "escrow_total_minor": 120_000,
            }
        )
        self.assertTrue(compliant.sla_compliant)
        self.assertTrue(compliant.seller_payout_released)
        self.assertEqual(compliant.buyer_compensation_minor, 0)
        self.assertEqual(compliant.seller_net_release_minor, 120_000)

        breached = evaluate_cold_chain_iot_telemetry_escrow(
            {
                "shipment_id": "shp_breach_02",
                "temperature_readings_c": [4.5, 11.5, 12.2, 13.0, 12.5, 5.0],  # 4 * 5 = 20 min > 15 min
                "sample_interval_minutes": 5,
                "min_allowed_temp_c": 2.0,
                "max_allowed_temp_c": 8.0,
                "max_mkt_celsius": 8.0,
                "max_excursion_minutes": 15,
                "escrow_total_minor": 200_000,
                "breach_compensation_bps": 10_000,
            }
        )
        self.assertFalse(breached.sla_compliant)
        self.assertFalse(breached.seller_payout_released)
        self.assertEqual(breached.decision_code, "COLD_CHAIN_SLA_BREACH_ESCROW_CLAIMED")
        self.assertEqual(breached.buyer_compensation_minor, 200_000)
        self.assertGreater(Decimal(breached.mkt_celsius), Decimal("8.00"))

    def test_scope3_carbon_pareto_router_selects_lowest_co2e_within_sla(self) -> None:
        res = optimize_carbon_pareto_carrier_route(
            shipment_spec={
                "cargo_weight_tons": "2.0",
                "distance_km": "2000",
                "max_sla_hours": 48,
                "max_budget_minor": 300_000,
                "max_carbon_budget_kg_co2e": "350.0",
            },
            carrier_options=[
                {"carrier_id": "air_fast", "mode": "AIR_FREIGHT", "transit_hours": 12, "cost_minor": 280_000, "gco2e_per_ton_km": "600"},
                {"carrier_id": "rail_green", "mode": "EURASIA_RAIL", "transit_hours": 38, "cost_minor": 110_000, "gco2e_per_ton_km": "25"},
                {"carrier_id": "sea_slow", "mode": "OCEAN_LCL", "transit_hours": 180, "cost_minor": 50_000, "gco2e_per_ton_km": "12"},
            ],
        )
        self.assertTrue(res.route_found)
        self.assertEqual(res.selected_carrier_id, "rail_green")
        self.assertEqual(res.total_kg_co2e, "100.00")
        self.assertGreater(Decimal(res.carbon_savings_vs_air_pct), Decimal("95.00"))

        infeasible = optimize_carbon_pareto_carrier_route(
            shipment_spec={
                "cargo_weight_tons": "5.0",
                "distance_km": "5000",
                "max_sla_hours": 10,
                "max_budget_minor": 50_000,
                "max_carbon_budget_kg_co2e": "10.0",
            },
            carrier_options=[
                {"carrier_id": "air_fast", "mode": "AIR_FREIGHT", "transit_hours": 12, "cost_minor": 280_000, "gco2e_per_ton_km": "600"},
            ],
        )
        self.assertFalse(infeasible.route_found)
        self.assertEqual(
            infeasible.decision_code,
            "NO_CARRIER_MEETS_SLA_AND_CARBON_ENVELOPE",
        )

    def test_cli_main_returns_zero(self) -> None:
        self.assertEqual(main([]), 0)


if __name__ == "__main__":
    unittest.main()
