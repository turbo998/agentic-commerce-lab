"""Unit test for Stage 157 16-scenario (SB-01..SB-16) 7-Card 4:5 benchmark report."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.x402_sui_sponsor_ucp_bopis_lock_acp_idempotency_ap2_mandate_exp_tau2_bench import (
    run_benchmark,
    write_benchmark_reports,
)


class Stage157BenchmarkTests(unittest.TestCase):
    def test_stage157_benchmark_16_scenarios_and_bilingual_cards(self) -> None:
        report = run_benchmark()
        summary = report["summary"]
        self.assertEqual(summary["total_scenarios"], 16)
        self.assertEqual(summary["ai_native_passed"], 16)
        self.assertEqual(summary["classic_3tier_passed"], 0)
        self.assertEqual(summary["perturbation_consistent_count"], 16)
        self.assertEqual(report["scenario_range"], "SB-01..SB-16")

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            write_benchmark_reports(out_dir)
            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("1 / 7", zh_html)
            self.assertIn("7 / 7", zh_html)
            self.assertIn("SB-01", zh_html)
            self.assertIn("SB-16", en_html)
            self.assertIn("default-src 'none'", en_html)


if __name__ == "__main__":
    unittest.main()
