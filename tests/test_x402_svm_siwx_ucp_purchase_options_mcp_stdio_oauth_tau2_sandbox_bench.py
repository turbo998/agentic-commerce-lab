"""Unit tests for Stage 243 16-scenario 7-Card 4:5 benchmark runner."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lab.x402_svm_siwx_ucp_purchase_options_mcp_stdio_oauth_tau2_sandbox_bench import (
    run_benchmark,
)


class TestStage243Benchmark(unittest.TestCase):
    def test_benchmark_16_of_16_pass_and_reversal_invariant(self) -> None:
        summary = run_benchmark(output_dir=None)
        self.assertEqual(summary["total_scenarios"], 16)
        self.assertEqual(summary["passed_scenarios"], 16)
        self.assertEqual(summary["pass_rate_pct"], 100.0)
        for item in summary["scenarios"]:
            self.assertTrue(item["passed"], f"{item['id']} must pass")
            self.assertTrue(item["reversal_invariant"], f"{item['id']} must be reversal-invariant")

    def test_7card_report_generation_and_csp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage243_report"
            summary = run_benchmark(output_dir=out_dir)
            self.assertEqual(summary["passed_scenarios"], 16)

            report_json = out_dir / "report.json"
            zh_html = out_dir / "index.html"
            en_html = out_dir / "index.en.html"
            self.assertTrue(report_json.exists())
            self.assertTrue(zh_html.exists())
            self.assertTrue(en_html.exists())

            loaded = json.loads(report_json.read_text(encoding="utf-8"))
            self.assertEqual(loaded["passed_scenarios"], 16)

            for html_file in (zh_html, en_html):
                text = html_file.read_text(encoding="utf-8")
                self.assertIn("default-src 'none'; style-src 'unsafe-inline'", text)
                for idx in range(1, 8):
                    self.assertIn(f'id="card-{idx}"', text)


if __name__ == "__main__":
    unittest.main()
