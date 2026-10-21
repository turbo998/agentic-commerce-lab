"""Unit test for Stage 155 16-scenario (FX-01..FX-16) 7-Card benchmark suite."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.x402_fetch_cap_xrpl_ucp_bundle_allergen_acp_term_bind_ap2_jpy_tau2_bench import (
    run_benchmark,
    write_benchmark_reports,
)


class Stage155BenchTest(unittest.TestCase):
    def test_stage155_benchmark_and_html_generation(self) -> None:
        report = run_benchmark()
        summary = report["summary"]
        self.assertEqual(summary["total_scenarios"], 16)
        self.assertEqual(summary["ai_native_passed"], 16)
        self.assertEqual(summary["ai_native_pass_rate_pct"], 100.0)
        self.assertEqual(summary["classic_3tier_passed"], 0)
        self.assertEqual(summary["perturbation_consistent_count"], 16)

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            write_benchmark_reports(out_dir)
            self.assertTrue((out_dir / "report.json").exists())
            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("1 / 7", zh_html)
            self.assertIn("7 / 7", zh_html)
            self.assertIn("FX-01", zh_html)
            self.assertIn("FX-16", en_html)
            self.assertIn("default-src 'none'", en_html)


if __name__ == "__main__":
    unittest.main()
