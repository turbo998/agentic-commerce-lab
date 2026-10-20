"""Unit tests for Stage 83 16-scenario bilingual 7-Card 4:5 benchmark suite (`MD-01..MD-16`)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.ucp_media_dest_totals_acp_default_deliv_mcp_x402_sar_erc7710_tau2_close_prov_bench import (
    run_stage83_benchmark,
)


class TestStage83Benchmark(unittest.TestCase):
    def test_stage83_metrics_and_scenarios(self) -> None:
        report = run_stage83_benchmark(output_dir=None)
        self.assertEqual(report["total_scenarios"], 16)
        self.assertEqual(report["ai_native_passed"], 16)
        self.assertEqual(report["ai_native_accuracy_pct"], 100.0)
        self.assertEqual(report["classic_3tier_passed"], 4)
        self.assertEqual(report["classic_3tier_accuracy_pct"], 25.0)
        self.assertEqual(report["perturbation_consistency_pct"], 100.0)
        ids = [r["scenario_id"] for r in report["results"]]
        self.assertEqual(ids[0], "MD-01")
        self.assertEqual(ids[-1], "MD-16")

    def test_stage83_bilingual_html_and_json_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage83"
            run_stage83_benchmark(output_dir=out_dir)
            json_path = out_dir / "report.json"
            zh_html_path = out_dir / "index.html"
            en_html_path = out_dir / "index.en.html"
            self.assertTrue(json_path.exists())
            self.assertTrue(zh_html_path.exists())
            self.assertTrue(en_html_path.exists())

            zh_html = zh_html_path.read_text(encoding="utf-8")
            en_html = en_html_path.read_text(encoding="utf-8")
            self.assertIn("Content-Security-Policy", zh_html)
            self.assertIn("Content-Security-Policy", en_html)
            self.assertIn("1 / 7", zh_html)
            self.assertIn("7 / 7", zh_html)
            self.assertIn("1 / 7", en_html)
            self.assertIn("7 / 7", en_html)
            self.assertIn("MD-01", zh_html)
            self.assertIn("MD-16", en_html)


if __name__ == "__main__":
    unittest.main()
