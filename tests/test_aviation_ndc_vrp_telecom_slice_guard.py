"""Unit tests for Aviation IATA NDC IRROPS, Open-Banking VRP Sweeping & Telecom SLA Guard."""

from __future__ import annotations

import unittest

from lab.aviation_ndc_vrp_telecom_slice_guard import (
    evaluate_iata_ndc_irrops_interline_escrow,
    evaluate_open_banking_vrp_sweeping_guard,
    evaluate_telecom_5g_network_slice_sla_escrow,
)


class TestAviationNDCVRPTelecomSliceGuard(unittest.TestCase):
    def test_iata_ndc_irrops_interline_escrow(self) -> None:
        comp = evaluate_iata_ndc_irrops_interline_escrow(
            order_id="ndc_order_01",
            gross_ticket_fare_minor=950_00,
            arrival_delay_minutes=240,
            flight_distance_km=4200,
            extraordinary_weather_or_atc_strike=False,
            flight_cancelled_unrebooked=False,
            operating_carrier_prorate_bps=6500,
        )
        self.assertTrue(comp.admitted)
        self.assertEqual(
            comp.decision_code,
            "IATA_IRROPS_STATUTORY_COMPENSATION_OR_REFUND_TRIGGERED",
        )
        self.assertEqual(comp.eu261_or_dot_statutory_compensation_minor, 600_00)
        self.assertEqual(comp.conservation_delta_minor, 0)

        exempt = evaluate_iata_ndc_irrops_interline_escrow(
            order_id="ndc_order_02",
            gross_ticket_fare_minor=950_00,
            arrival_delay_minutes=240,
            flight_distance_km=4200,
            extraordinary_weather_or_atc_strike=True,
            flight_cancelled_unrebooked=False,
            operating_carrier_prorate_bps=6500,
        )
        self.assertEqual(
            exempt.decision_code,
            "IRROPS_EXTRAORDINARY_CIRCUMSTANCE_COMPENSATION_EXEMPT",
        )
        self.assertEqual(exempt.eu261_or_dot_statutory_compensation_minor, 0)

    def test_open_banking_vrp_sweeping_guard(self) -> None:
        bypass = evaluate_open_banking_vrp_sweeping_guard(
            vrp_mandate_id="vrp_01",
            vrp_category="SWEEPING",
            debtor_beneficial_owner_id="user_alice",
            creditor_beneficial_owner_id="merchant_evil",
            transfer_amount_minor=50_000,
            max_single_payment_minor=100_000,
            current_month_cumulative_minor=10_000,
            max_monthly_cumulative_minor=500_000,
            psu_sca_bound_device_signature_valid=True,
        )
        self.assertFalse(bypass.admitted)
        self.assertEqual(
            bypass.decision_code,
            "VRP_SWEEPING_THIRD_PARTY_MERCHANT_BYPASS_BLOCKED",
        )

        settled = evaluate_open_banking_vrp_sweeping_guard(
            vrp_mandate_id="vrp_02",
            vrp_category="SWEEPING",
            debtor_beneficial_owner_id="user_alice",
            creditor_beneficial_owner_id="user_alice",
            transfer_amount_minor=50_000,
            max_single_payment_minor=100_000,
            current_month_cumulative_minor=10_000,
            max_monthly_cumulative_minor=500_000,
            psu_sca_bound_device_signature_valid=True,
        )
        self.assertTrue(settled.admitted)
        self.assertEqual(settled.decision_code, "OPEN_BANKING_VRP_EXECUTION_SETTLED")

    def test_telecom_5g_network_slice_sla_escrow(self) -> None:
        slashed = evaluate_telecom_5g_network_slice_sla_escrow(
            slice_id="slice_urllc_01",
            contract_slice_fee_minor=200_000,
            committed_latency_p99_ms=5.0,
            observed_latency_p99_ms=14.2,
            committed_max_packet_loss_bps=10,
            observed_packet_loss_bps=45,
            twamp_telemetry_signature_valid=True,
        )
        self.assertTrue(slashed.admitted)
        self.assertEqual(
            slashed.decision_code,
            "TELECOM_5G_URLLC_SLA_BREACH_REBATE_SLASHED",
        )
        self.assertEqual(slashed.sla_penalty_rebate_minor, 100_000)
        self.assertEqual(slashed.operator_net_settlement_minor, 100_000)
        self.assertEqual(slashed.conservation_delta_minor, 0)


if __name__ == "__main__":
    unittest.main()
