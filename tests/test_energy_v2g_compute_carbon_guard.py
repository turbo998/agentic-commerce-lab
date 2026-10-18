"""Unit tests for Stage 25: EV ISO 15118/V2G Energy Settlement, GPU Goodput SLA & Carbon Guard."""

from __future__ import annotations

from dataclasses import replace
import unittest

from lab.energy_v2g_compute_carbon_guard import (
    evaluate_ev_iso15118_v2g_energy_settlement,
    evaluate_gpu_spot_compute_sla_and_carbon_retirement,
)
from lab.unified_checkout_pipeline import (
    build_golden_pipeline_input,
    execute_unified_agentic_checkout,
)


from lab.vertical_domain_clearing_bench import (
    run_vertical_domain_clearing_benchmark,
)


class TestEnergyV2gComputeCarbonGuard(unittest.TestCase):
    def test_v2g_blocks_unsigned_ocmf_telemetry_spoof(self) -> None:
        res = evaluate_ev_iso15118_v2g_energy_settlement(
            {
                "session_id": "v2g_spoof_01",
                "iso15118_contract_cert_valid": True,
                "ocmf_signature_valid": False,
                "initial_soc_pct": 80.0,
                "post_discharge_soc_pct": 55.0,
                "min_soc_floor_pct": 30.0,
                "charged_kwh": 10.0,
                "discharged_kwh": 15.0,
            }
        )
        self.assertFalse(res["allowed"])
        self.assertEqual(res["decision_code"], "UNSIGNED_OCMF_TELEMETRY_SPOOF_BLOCKED")

    def test_v2g_blocks_discharge_below_soc_floor(self) -> None:
        res = evaluate_ev_iso15118_v2g_energy_settlement(
            {
                "session_id": "v2g_soc_02",
                "iso15118_contract_cert_valid": True,
                "ocmf_signature_valid": True,
                "initial_soc_pct": 65.0,
                "post_discharge_soc_pct": 22.0,
                "min_soc_floor_pct": 35.0,
                "charged_kwh": 5.0,
                "discharged_kwh": 30.0,
            }
        )
        self.assertFalse(res["allowed"])
        self.assertEqual(res["decision_code"], "V2G_DISCHARGE_BELOW_SOC_FLOOR_BLOCKED")

    def test_v2g_settles_bidirectional_net_metering_accurately(self) -> None:
        res = evaluate_ev_iso15118_v2g_energy_settlement(
            {
                "session_id": "v2g_net_03",
                "iso15118_contract_cert_valid": True,
                "ocmf_signature_valid": True,
                "initial_soc_pct": 88.0,
                "post_discharge_soc_pct": 48.0,
                "min_soc_floor_pct": 35.0,
                "charged_kwh": 10.0,
                "discharged_kwh": 20.0,
                "tou_charge_rate_minor_per_kwh": 30,
                "fit_discharge_credit_minor_per_kwh": 85,
            }
        )
        self.assertTrue(res["allowed"])
        self.assertEqual(res["decision_code"], "V2G_BIDIRECTIONAL_NET_METER_SETTLED")
        self.assertEqual(res["gross_tou_charge_minor"], 300)
        self.assertEqual(res["gross_fit_export_credit_minor"], 1700)
        self.assertEqual(res["net_settlement_minor"], -1400)

    def test_gpu_compute_voids_uncheckpointed_preemption_and_blocks_double_carbon(self) -> None:
        preempted = evaluate_gpu_spot_compute_sla_and_carbon_retirement(
            {
                "job_id": "job_preempt_01",
                "escrow_hold_minor": 80_000,
                "promised_tflops": 1000.0,
                "measured_goodput_tflops": 920.0,
                "preempted_before_checkpoint": True,
                "carbon_credit_already_retired": False,
                "registry_attestation_valid": True,
            }
        )
        self.assertFalse(preempted["allowed"])
        self.assertEqual(preempted["decision_code"], "UNCHECKPOINTED_PREEMPTION_CHARGE_VOIDED")
        self.assertEqual(preempted["buyer_refund_minor"], 80_000)

        double_carbon = evaluate_gpu_spot_compute_sla_and_carbon_retirement(
            {
                "job_id": "job_carbon_02",
                "escrow_hold_minor": 80_000,
                "promised_tflops": 1000.0,
                "measured_goodput_tflops": 950.0,
                "preempted_before_checkpoint": False,
                "carbon_credit_already_retired": True,
                "registry_attestation_valid": True,
            }
        )
        self.assertFalse(double_carbon["allowed"])
        self.assertEqual(
            double_carbon["decision_code"], "CARBON_CREDIT_DOUBLE_COUNTING_RETIREMENT_BLOCKED"
        )

    def test_gpu_compute_slashes_escrow_on_goodput_breach_and_integrates_gate6(self) -> None:
        slashed = evaluate_gpu_spot_compute_sla_and_carbon_retirement(
            {
                "job_id": "job_slash_03",
                "escrow_hold_minor": 100_000,
                "promised_tflops": 1000.0,
                "measured_goodput_tflops": 750.0,
                "min_goodput_ratio": 0.85,
                "preempted_before_checkpoint": False,
                "carbon_credit_already_retired": False,
                "registry_attestation_valid": True,
                "sla_slash_bps": 2500,
            }
        )
        self.assertTrue(slashed["allowed"])
        self.assertEqual(slashed["decision_code"], "COMPUTE_GOODPUT_SLA_BREACH_ESCROW_SLASHED")
        self.assertEqual(slashed["provider_payout_minor"], 75_000)
        self.assertEqual(slashed["buyer_refund_minor"], 25_000)

        base_inp = build_golden_pipeline_input()
        blocked_inp = replace(
            base_inp,
            v2g_energy_session_context={
                "session_id": "v2g_gate6_spoof",
                "iso15118_contract_cert_valid": True,
                "ocmf_signature_valid": False,
                "charged_kwh": 20.0,
                "discharged_kwh": 0.0,
            },
        )
        res = execute_unified_agentic_checkout(blocked_inp)
        self.assertFalse(res.checkout_committed)
        self.assertEqual(res.blocked_at_gate, 6)
        self.assertIn("UNSIGNED_OCMF_TELEMETRY_SPOOF_BLOCKED", res.terminal_decision_code)

    def test_vertical_domain_clearing_benchmark_16_scenarios(self) -> None:
        report = run_vertical_domain_clearing_benchmark()
        self.assertEqual(report["total_scenarios"], 16)
        self.assertEqual(report["ai_native_passed"], 16)
        self.assertEqual(report["classic_3tier_passed"], 1)
        self.assertEqual(report["reversed_order_passed"], 16)


if __name__ == "__main__":
    unittest.main()
