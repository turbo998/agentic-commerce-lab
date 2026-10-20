"""Unit tests for Stage 59 bilingual 16-scenario 7-Card 4:5 benchmark suite."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.ucp_purchase_options_offers_acp_feed_ap2_multihop_tau2_voice_bench import (
    generate_stage59_benchmark_report,
    run_stage59_benchmark_scenarios,
)


class TestStage59BenchmarkSuite(unittest.TestCase):
    def test_scenarios_16_of_16_pass_and_consistent(self) -> None:
        scenarios = run_stage59_benchmark_scenarios()
        self.assertEqual(len(scenarios), 16)
        self.assertEqual([s.scenario_id for s in scenarios], [f"PO-{i:02d}" for i in range(1, 17)])
        for s in scenarios:
            self.assertTrue(s.ai_native_passed, f"Scenario failed: {s}")
            self.assertTrue(s.reversed_order_consistent, f"Reversal drift in: {s}")
        self.assertEqual(sum(1 for s in scenarios if s.classic_3tier_passed), 1)

    def test_generate_bilingual_7card_report_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            report = generate_stage59_benchmark_report(tmpdir)
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["ai_native_passed"], 16)
            self.assertEqual(report["classic_3tier_passed"], 1)
            self.assertEqual(report["option_reversal_consistency_pct"], 100.0)

            out_dir = Path(tmpdir)
            report_json = out_dir / "report.json"
            html_zh = out_dir / "index.html"
            html_en = out_dir / "index.en.html"
            self.assertTrue(report_json.exists())
            self.assertTrue(html_zh.exists())
            self.assertTrue(html_en.exists())

            zh_text = html_zh.read_text(encoding="utf-8")
            en_text = html_en.read_text(encoding="utf-8")
            for idx in range(1, 8):
                self.assertIn(f"{idx} / 7 ·", zh_text)
                self.assertIn(f"{idx} / 7 ·", en_text)
            self.assertIn("index.en.html", zh_text)
            self.assertIn("index.html", en_text)
            self.assertIn("Content-Security-Policy", zh_text)
            self.assertIn("Content-Security-Policy", en_text)


if __name__ == "__main__":
    unittest.main()
