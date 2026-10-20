"""Unit tests for Stage 101 16-scenario (`EG-01..EG-16`) bilingual 7-Card 4:5 benchmark."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.ucp_etag_gift_p521_acp_affiliate_3ds_ap2_open_hash_x402_fact_tau2_bench import (
    DEFAULT_OUTPUT_DIR,
    run_benchmark,
)


class TestStage101Benchmark(unittest.TestCase):
    def test_stage101_benchmark_16_scenarios_and_bilingual_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            summary = run_benchmark(tmp)
            self.assertEqual(summary["total_scenarios"], 16)
            self.assertEqual(summary["ai_native_passed"], 16)
            self.assertEqual(summary["ai_native_accuracy_pct"], 100.0)
            self.assertEqual(summary["classic_3tier_passed"], 4)
            self.assertEqual(summary["classic_3tier_accuracy_pct"], 25.0)
            self.assertEqual(summary["reversal_consistency_passed"], 16)

            for fname in ("report.json", "index.html", "index.en.html"):
                self.assertTrue((tmp / fname).exists(), fname)

            zh_html = (tmp / "index.html").read_text(encoding="utf-8")
            en_html = (tmp / "index.en.html").read_text(encoding="utf-8")
            for k in ("1 / 7", "2 / 7", "3 / 7", "4 / 7", "5 / 7", "6 / 7", "7 / 7"):
                self.assertIn(k, zh_html)
                self.assertIn(k, en_html)

    def test_stage101_default_reports_generated(self) -> None:
        summary = run_benchmark()
        self.assertEqual(summary["ai_native_passed"], 16)
        self.assertTrue((DEFAULT_OUTPUT_DIR / "report.json").exists())
        self.assertTrue((DEFAULT_OUTPUT_DIR / "index.html").exists())
        self.assertTrue((DEFAULT_OUTPUT_DIR / "index.en.html").exists())


if __name__ == "__main__":
    unittest.main()
