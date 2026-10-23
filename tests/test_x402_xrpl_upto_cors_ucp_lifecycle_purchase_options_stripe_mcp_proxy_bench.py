"""Unit tests for Stage 171 16-scenario bilingual 7-card 4:5 visual benchmark (2026-10-23)."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.x402_xrpl_upto_cors_ucp_lifecycle_purchase_options_stripe_mcp_proxy_tau2_bench import (
    build_report,
    evaluate_all_scenarios,
    generate_report_artifacts,
)


class TestStage171Benchmark(unittest.TestCase):
    def test_evaluate_all_16_scenarios_pass_and_perturbation_invariant(self) -> None:
        scenarios = evaluate_all_scenarios()
        self.assertEqual(len(scenarios), 16)
        self.assertEqual([s.scenario_id for s in scenarios], [f"XP-{i:02d}" for i in range(1, 17)])
        for s in scenarios:
            self.assertTrue(s.matched, f"Scenario {s.scenario_id} failed: {s}")
            self.assertEqual(s.perturbation_delta_pts, 0.0)

    def test_generate_bilingual_7_card_artifacts(self) -> None:
        report = build_report()
        self.assertEqual(report["summary"]["total_scenarios"], 16)
        self.assertEqual(report["summary"]["passed_scenarios"], 16)
        self.assertEqual(report["summary"]["pass_rate_pct"], 100.0)
        self.assertEqual(report["summary"]["perturbation_invariance_pct"], 100.0)
        self.assertEqual(report["summary"]["stripe_mcp_days_remaining"], 38)

        with tempfile.TemporaryDirectory() as tmp:
            paths = generate_report_artifacts(Path(tmp))
            zh_html = paths["zh"].read_text(encoding="utf-8")
            en_html = paths["en"].read_text(encoding="utf-8")
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", en_html)
            self.assertEqual(zh_html.count('class="card"'), 7)
            self.assertEqual(en_html.count('class="card"'), 7)
            self.assertIn("XP-01", zh_html)
            self.assertIn("XP-16", en_html)


if __name__ == "__main__":
    unittest.main()
