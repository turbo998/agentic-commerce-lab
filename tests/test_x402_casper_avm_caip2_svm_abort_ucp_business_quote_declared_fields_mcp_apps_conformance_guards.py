"""Unit tests for Stage 236 deterministic guards (`PR-01..PR-16`)."""

from __future__ import annotations

import unittest

from lab.x402_casper_avm_caip2_svm_abort_ucp_business_quote_declared_fields_mcp_apps_conformance_bench import (
    SCENARIOS,
    _valid_sub_payloads,
)
from lab.x402_casper_avm_caip2_svm_abort_ucp_business_quote_declared_fields_mcp_apps_conformance_guards import (
    evaluate_stage236_composite_gate,
)


class TestStage236Guards(unittest.TestCase):
    def test_all_15_individual_guards_admit_valid_and_block_attacks(self) -> None:
        valid_map = _valid_sub_payloads()
        self.assertEqual(len(SCENARIOS), 15)
        for item in SCENARIOS:
            sid = item["id"]
            fn = item["fn"]
            valid_res = fn(valid_map[sid])
            self.assertTrue(valid_res.passed, f"{sid} valid payload should pass: {valid_res}")
            attack_res = fn(item["attack"])
            self.assertFalse(attack_res.passed, f"{sid} attack payload should be blocked: {attack_res}")

    def test_composite_gate_pr16_enforces_all_subguards(self) -> None:
        valid_map = _valid_sub_payloads()
        ok_res = evaluate_stage236_composite_gate(valid_map)
        self.assertTrue(ok_res.passed)
        self.assertEqual(ok_res.code, "STAGE236_COMPOSITE_ALL_16_GUARDS_PASSED")

        tampered = {k: dict(v) for k, v in valid_map.items()}
        tampered["PR-02"]["network"] = "eip155:84532:extra"
        bad_res = evaluate_stage236_composite_gate(tampered)
        self.assertFalse(bad_res.passed)
        self.assertIn("STAGE236_COMPOSITE_BLOCKED_PR-02", bad_res.code)


if __name__ == "__main__":
    unittest.main()
