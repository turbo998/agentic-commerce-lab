"""Unit tests for Stages 248-249 benchmark runner and 7-Card 4:5 HTML report."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.mcp_ext_apps_conformance_dpop_registry_bench import run_benchmark


class McpExtAppsConformanceDpopRegistryBenchTest(unittest.TestCase):
    def test_benchmark_16_scenarios_100_percent_and_zero_drift(self) -> None:
        summary = run_benchmark(None)
        self.assertEqual(summary["total_scenarios"], 16)
        self.assertEqual(summary["matched_scenarios"], 16)
        self.assertEqual(summary["accuracy_pct"], 100.0)
        self.assertEqual(summary["perturbation_consistent"], 16)
        self.assertEqual(summary["perturbation_total"], 16)

    def test_html_report_generation_and_csp_compliance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            run_benchmark(out_dir)
            report_json = out_dir / "report.json"
            zh_html = out_dir / "index.html"
            en_html = out_dir / "index.en.html"
            self.assertTrue(report_json.exists())
            self.assertTrue(zh_html.exists())
            self.assertTrue(en_html.exists())

            for html_file in (zh_html, en_html):
                text = html_file.read_text(encoding="utf-8")
                self.assertIn(
                    "Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'\"",
                    text,
                )
                for idx in range(1, 8):
                    self.assertIn(f'id="card-{idx}"', text)


if __name__ == "__main__":
    unittest.main()
