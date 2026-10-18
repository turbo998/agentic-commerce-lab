"""Unit tests for Stage 18 15-Scenario Global Clearing, FX, Customs & ZK-Privacy 7-Card Benchmark."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.global_clearing_privacy_bench import run_global_clearing_privacy_benchmark


class GlobalClearingPrivacyBenchTestSuite(unittest.TestCase):
    def test_fifteen_scenario_benchmark_and_seven_card_deck(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = run_global_clearing_privacy_benchmark(output_dir=tmp)
            self.assertEqual(report["total_scenarios"], 15)
            self.assertEqual(report["ai_native_passed"], 15)
            self.assertEqual(report["classic_3tier_passed"], 1)
            self.assertEqual(report["perturbation_drift_pts"], 0.0)

            html_text = Path(report["report_html"]).read_text(encoding="utf-8")
            self.assertIn(
                "default-src 'none'; style-src 'unsafe-inline'", html_text
            )
            for idx in range(1, 8):
                self.assertIn(f'id="card-{idx}"', html_text)


if __name__ == "__main__":
    unittest.main()
