"""Unit tests for Stage 252 guards and Stage 253 7-Card 4:5 benchmark report."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.tap_mtls_stripe_hooks_ucp_order_sig_acp_allof_ap2_corpus_agentkit_mcp_tau2_bench import (
    DEFAULT_REPORT_DIR,
    build_stage253_scenarios,
    run_stage253_benchmark,
)
from lab.tap_mtls_stripe_hooks_ucp_order_sig_acp_allof_ap2_corpus_agentkit_mcp_tau2_guards import (
    STAGE252_GUARD_EVALUATORS,
    evaluate_stage252_guards,
)


class TestStage252And253GuardsAndBenchmark(unittest.TestCase):
    """Verify all 16 Stage 252 guards and Stage 253 7-Card 4:5 report generation."""

    def test_all_16_compliant_scenarios_pass(self) -> None:
        scenarios = build_stage253_scenarios()
        self.assertEqual(len(scenarios), 16)
        compliant_map = {item["id"]: item["compliant_payload"] for item in scenarios}
        results = evaluate_stage252_guards(compliant_map)
        self.assertEqual(len(results), 16)
        for pr_id, res in results.items():
            self.assertTrue(res.passed, f"{pr_id} should pass on compliant payload: {res.reason}")
            self.assertEqual(res.action, "allow")

    def test_all_16_adversarial_scenarios_block(self) -> None:
        scenarios = build_stage253_scenarios()
        adversarial_map = {item["id"]: item["adversarial_payload"] for item in scenarios}
        results = evaluate_stage252_guards(adversarial_map)
        self.assertEqual(len(results), 16)
        for pr_id, res in results.items():
            self.assertFalse(res.passed, f"{pr_id} should block on adversarial payload")
            self.assertEqual(res.action, "block")
            self.assertTrue(res.reason)
            self.assertNotEqual(res.remediation, "none")

    def test_targeted_edge_cases_across_guards(self) -> None:
        scenarios = {item["id"]: item for item in build_stage253_scenarios()}

        # PR-05: custom fulfillment event without description must fail
        pr05_custom = dict(scenarios["PR-05"]["compliant_payload"])
        pr05_custom["fulfillment_events"] = [
            {"type": "custom_drone_drop", "semantic_stage": "custom", "description": "   "}
        ]
        res05 = STAGE252_GUARD_EVALUATORS["PR-05"](pr05_custom)
        self.assertFalse(res05.passed)
        self.assertIn("non-empty description", res05.reason)

        # PR-11: SwapChan requiring approval without receipt confirmation must fail
        pr11_unconfirmed = dict(scenarios["PR-11"]["compliant_payload"])
        pr11_unconfirmed["swapchan_approval_receipt_confirmed"] = False
        res11 = STAGE252_GUARD_EVALUATORS["PR-11"](pr11_unconfirmed)
        self.assertFalse(res11.passed)
        self.assertIn("approval transaction receipt", res11.reason)

        # PR-16: repeated gold action matched to fewer distinct calls must fail
        pr16_non_bipartite = dict(scenarios["PR-16"]["compliant_payload"])
        pr16_non_bipartite["distinct_predicted_tool_calls_matched"] = 3
        res16 = STAGE252_GUARD_EVALUATORS["PR-16"](pr16_non_bipartite)
        self.assertFalse(res16.passed)
        self.assertIn("one-to-one", res16.reason)

    def test_stage253_benchmark_and_7card_bilingual_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = run_stage253_benchmark(output_dir=Path(tmp))
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["ai_native_passed"], 16)
            self.assertEqual(report["ai_native_rate_pct"], 100.0)
            self.assertEqual(report["classic_passed"], 2)
            self.assertEqual(report["classic_rate_pct"], 12.5)
            self.assertEqual(report["perturbation_invariant_count"], 16)
            self.assertEqual(report["perturbation_rate_pct"], 100.0)

            zh_html = (Path(tmp) / "index.html").read_text(encoding="utf-8")
            en_html = (Path(tmp) / "index.en.html").read_text(encoding="utf-8")
            for doc in (zh_html, en_html):
                self.assertIn("Content-Security-Policy", doc)
                self.assertIn("default-src 'none'; style-src 'unsafe-inline'", doc)
                for i in range(1, 8):
                    self.assertIn(f"{i} / 7 ·", doc)

        # Also verify the canonical report artifacts exist in DEFAULT_REPORT_DIR
        prod_report = run_stage253_benchmark(output_dir=DEFAULT_REPORT_DIR)
        self.assertEqual(prod_report["ai_native_passed"], 16)
        self.assertTrue((DEFAULT_REPORT_DIR / "report.json").is_file())
        self.assertTrue((DEFAULT_REPORT_DIR / "index.html").is_file())
        self.assertTrue((DEFAULT_REPORT_DIR / "index.en.html").is_file())


if __name__ == "__main__":
    unittest.main()
