"""Unit tests for Stage 79 16-scenario bilingual 7-Card 4:5 benchmark report (`SB-01..SB-16`)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.ucp_sale_basis_loyalty_actions_acp_delegated_auth_handlers_ap2_budget_pii_tau2_gptlive_bench import (
     evaluate_scenarios,
    write_report,
)


class TestStage79BenchmarkReport(unittest.TestCase):
    def test_evaluate_16_scenarios_achieves_100_percent_and_consistency(self) -> None:
        summary = evaluate_scenarios()
        self.assertEqual(summary["total_scenarios"], 16)
        self.assertEqual(summary["ai_native_passed"], 16)
        self.assertEqual(summary["ai_native_accuracy_pct"], 100.0)
        self.assertEqual(summary["classic_3tier_passed"], 4)
        self.assertEqual(summary["classic_3tier_accuracy_pct"], 25.0)
        self.assertEqual(summary["perturbation_consistent_count"], 16)
        self.assertEqual(summary["perturbation_consistency_pct"], 100.0)
        scenario_ids = [row["scenario_id"] for row in summary["scenarios"]]
        self.assertEqual(scenario_ids, [f"SB-{i:02d}" for i in range(1, 17)])

    def test_write_bilingual_7card_html_and_json_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage79-bench"
            summary = write_report(out_dir)
            self.assertEqual(summary["ai_native_passed"], 16)
            report_json = out_dir / "report.json"
            index_zh = out_dir / "index.html"
            index_en = out_dir / "index.en.html"
            self.assertTrue(report_json.exists())
            self.assertTrue(index_zh.exists())
            self.assertTrue(index_en.exists())
            zh_html = index_zh.read_text(encoding="utf-8")
            en_html = index_en.read_text(encoding="utf-8")
            for idx in range(1, 8):
                self.assertIn(f"{idx} / 7", zh_html)
                self.assertIn(f"{idx} / 7", en_html)
            self.assertIn("Content-Security-Policy", zh_html)
            self.assertIn("SB-16", zh_html)
            self.assertIn("SB-16", en_html)


if __name__ == "__main__":
    unittest.main()
