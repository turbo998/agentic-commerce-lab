"""Unit tests for Stage 149 16-scenario (SP-01..SP-16) 7-Card 4:5 benchmark suite."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.x402_settle_status_provenance_ucp_correspondence_finality_ap2_budget_bench import (
    run_stage149_benchmark_suite,
    write_stage149_benchmark_reports,
)


class Stage149BenchmarkTest(unittest.TestCase):
    def test_stage149_benchmark_suite_and_bilingual_7card_reports(self) -> None:
        summary = run_stage149_benchmark_suite()
        self.assertEqual(summary["total_scenarios"], 16)
        self.assertEqual(summary["ai_native_passed"], 16)
        self.assertEqual(summary["classic_3tier_passed"], 0)
        self.assertEqual(summary["ai_native_pass_rate_pct"], 100.0)
        self.assertGreater(summary["latency_speedup_factor"], 10.0)

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage149"
            write_stage149_benchmark_reports(out_dir)
            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("1 / 7 · HANDS-ON", zh_html)
            self.assertIn("7 / 7 · MY TAKE", en_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)
            self.assertIn("SP-16", en_html)


if __name__ == "__main__":
    unittest.main()
