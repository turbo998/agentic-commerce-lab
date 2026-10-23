"""Unit tests for Stage 191 16-scenario benchmark and 7-Card 4:5 report generator."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.x402_eoa_high_s_upto_sim_tron_exact_svm_seal_callback_mcp_requirements_meta_bench import (
    generate_report_artifacts,
    run_benchmark,
)


class TestStage191Benchmark(unittest.TestCase):
    def test_16_scenarios_pass(self) -> None:
        summary = run_benchmark()
        self.assertEqual(summary["stage"], 191)
        self.assertEqual(summary["total_scenarios"], 16)
        self.assertEqual(summary["passed_scenarios"], 16)
        self.assertEqual(summary["pass_rate_pct"], 100.0)
        self.assertEqual(summary["primary_latency_ms"], 0.17)

    def test_write_7_card_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            summary = generate_report_artifacts(out)
            self.assertEqual(summary["passed_scenarios"], 16)
            zh_html = (out / "index.html").read_text(encoding="utf-8")
            en_html = (out / "index.en.html").read_text(encoding="utf-8")
            for html in (zh_html, en_html):
                self.assertIn("Content-Security-Policy", html)
                self.assertIn("default-src 'none'; style-src 'unsafe-inline'", html)
                self.assertIn("7 / 7 · MY TAKE", html)
                self.assertIn("ET-01", html)
                self.assertIn("ET-16", html)


if __name__ == "__main__":
    unittest.main()
