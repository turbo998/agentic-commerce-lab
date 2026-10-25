"""Unit tests for Stage 228 Visa TAP, Stripe, ACP, UCP, AP2, a2a-x402, AgentKit, MCP & tau2-bench guards."""

from __future__ import annotations

import unittest

from lab.visa_tap_stripe_acp_ucp_ap2_x402_agentkit_mcp_tau2_bench import (
    build_stage229_scenarios,
)
from lab.visa_tap_stripe_acp_ucp_ap2_x402_agentkit_mcp_tau2_guards import (
    STAGE228_GUARD_EVALUATORS,
    evaluate_stage228_scenario,
    iso4217_minor_unit_exponent,
    major_to_minor_units,
    map_slog_level_to_mcp,
)


class TestStage228VisaTapStripeAcpUcpAp2X402AgentKitMcpTau2Guards(unittest.TestCase):
    def test_all_16_evaluators_block_faults_and_allow_patched_and_perturbed(self) -> None:
        scenarios = build_stage229_scenarios()
        self.assertEqual(len(scenarios), 16)
        self.assertEqual(len(STAGE228_GUARD_EVALUATORS), 16)

        for item in scenarios:
            sid = item["scenario_id"]
            with self.subTest(scenario_id=sid):
                fault_res = evaluate_stage228_scenario(sid, item["fault_payload"])
                self.assertFalse(fault_res["allow"], f"{sid} fault should be blocked: {fault_res}")
                self.assertTrue(fault_res["code"].startswith("BLOCKED_"))

                patched_res = evaluate_stage228_scenario(sid, item["patched_payload"])
                self.assertTrue(patched_res["allow"], f"{sid} patched should be allowed: {patched_res}")
                self.assertTrue(patched_res["code"].startswith("ALLOW_"))

                perturbed_res = evaluate_stage228_scenario(sid, item["perturbed_payload"])
                self.assertTrue(perturbed_res["allow"], f"{sid} perturbed should be allowed: {perturbed_res}")

    def test_helpers_iso4217_and_slog_floor_mapping(self) -> None:
        self.assertEqual(iso4217_minor_unit_exponent("JPY"), 0)
        self.assertEqual(iso4217_minor_unit_exponent("USD"), 2)
        self.assertEqual(iso4217_minor_unit_exponent("KWD"), 3)
        self.assertEqual(iso4217_minor_unit_exponent("CLF"), 4)
        self.assertEqual(major_to_minor_units("19.99", "USD"), 1999)
        self.assertEqual(major_to_minor_units("0.29", "EUR"), 29)
        self.assertEqual(major_to_minor_units("1000", "JPY"), 1000)
        self.assertEqual(major_to_minor_units("1.5", "KWD"), 1500)
        self.assertEqual(map_slog_level_to_mcp(1), "info")
        self.assertEqual(map_slog_level_to_mcp(5), "warning")
        self.assertEqual(map_slog_level_to_mcp(-8), "debug")


if __name__ == "__main__":
    unittest.main()
