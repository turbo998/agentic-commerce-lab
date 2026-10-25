"""Unit tests for Stage 234 (235-Stage Milestone!) deterministic guard evaluators (`PR-01..PR-16`)."""

from __future__ import annotations

import unittest

from lab.x402_svm_recovery_ucp_consultation_modification_acp_ap2_mcp_seps_inspector_bench import _build_scenarios


class TestStage234Guards(unittest.TestCase):
    def test_all_16_stage234_guards_accept_compliant_inputs(self) -> None:
        scenarios = _build_scenarios()
        self.assertEqual(len(scenarios), 16)
        for item in scenarios:
            with self.subTest(scenario_id=item["id"]):
                self.assertTrue(item["ai_eval"].passed, msg=f"{item['id']} failed: {item['ai_eval']}")

    def test_all_16_stage234_guards_reject_adversarial_inputs(self) -> None:
        scenarios = _build_scenarios()
        self.assertEqual(len(scenarios), 16)
        for item in scenarios:
            with self.subTest(scenario_id=item["id"]):
                self.assertFalse(item["attack_eval"].passed, msg=f"{item['id']} unexpectedly passed")


if __name__ == "__main__":
    unittest.main()
