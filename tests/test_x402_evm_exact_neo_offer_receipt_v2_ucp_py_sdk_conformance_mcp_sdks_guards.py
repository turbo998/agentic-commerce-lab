"""Unit tests for Stage 232 deterministic protocol guards (880-Test Milestone)."""

from __future__ import annotations

import unittest

from lab.x402_evm_exact_neo_offer_receipt_v2_ucp_py_sdk_conformance_mcp_sdks_bench import (
    SCENARIOS,
)


class Stage232GuardsTest(unittest.TestCase):
    """Verify all 16 Stage 232 guard evaluators admit valid inputs and block attacks."""

    def test_all_16_stage_232_guards_admit_valid_payloads(self) -> None:
        self.assertEqual(len(SCENARIOS), 16)
        for item in SCENARIOS:
            with self.subTest(scenario_id=item["scenario_id"]):
                res = item["fn"](item["valid"])
                self.assertTrue(res.allowed, f"{item['scenario_id']} valid payload rejected: {res}")

    def test_all_16_stage_232_guards_block_attack_payloads(self) -> None:
        for item in SCENARIOS:
            with self.subTest(scenario_id=item["scenario_id"]):
                res = item["fn"](item["attack"])
                self.assertFalse(res.allowed, f"{item['scenario_id']} attack payload admitted: {res}")
                self.assertTrue(res.decision_code)
                self.assertNotEqual(res.remediation, "None")


if __name__ == "__main__":
    unittest.main()
