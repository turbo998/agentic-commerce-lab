"""Unit tests for Stage 61 16-scenario bilingual 7-Card 4:5 benchmark suite (`RA-01..RA-16`)."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.ucp_root_array_order_acp_lineitem_ap2_vct_tau2_voice_design_bench import (
    generate_stage61_benchmark_report,
    run_stage61_benchmark_scenarios,
)


class TestStage61RootArrayOrderAcpLineItemAp2VctTau2VoiceDesignBench(unittest.TestCase):
    def test_16_scenarios_achieve_100_percent_accuracy_and_stability(self) -> None:
        scenarios = run_stage61_benchmark_scenarios()
        self.assertEqual(len(scenarios), 16)
        self.assertEqual([s.scenario_id for s in scenarios], [f"RA-{i:02d}" for i in range(1, 17)])
        for s in scenarios:
            self.assertTrue(s.ai_native_correct, msg=f"{s.scenario_id} failed: {s.ai_native_decision_code}")
            self.assertTrue(s.reversed_order_stable, msg=f"{s.scenario_id} unstable")

    def test_generate_bilingual_7card_report_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage61-report"
            report = generate_stage61_benchmark_report(out_dir)
            self.assertEqual(report["summary"]["total_scenarios"], 16)
            self.assertEqual(report["summary"]["ai_native_passed"], 16)
            self.assertEqual(report["summary"]["ai_native_accuracy_pct"], 100.0)
            self.assertEqual(report["summary"]["classic_3tier_passed"], 1)
            self.assertEqual(report["summary"]["reversed_order_stability_pct"], 100.0)

            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            for html_doc in (zh_html, en_html):
                self.assertIn("Content-Security-Policy", html_doc)
                for idx in range(1, 8):
                    self.assertIn(f"{idx} / 7", html_doc)
                self.assertIn("RA-01", html_doc)
                self.assertIn("RA-16", html_doc)


if __name__ == "__main__":
    unittest.main()
