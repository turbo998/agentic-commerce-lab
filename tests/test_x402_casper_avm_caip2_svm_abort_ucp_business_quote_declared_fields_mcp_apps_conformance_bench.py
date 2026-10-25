"""Unit tests for Stage 237 16-scenario 7-Card 4:5 benchmark suite."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.x402_casper_avm_caip2_svm_abort_ucp_business_quote_declared_fields_mcp_apps_conformance_bench import (
    run_benchmark,
)


class TestStage237Benchmark(unittest.TestCase):
    def test_benchmark_generates_16_of_16_and_bilingual_7card_decks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage237-bench"
            report = run_benchmark(out_dir)
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["ai_native_passed"], 16)
            self.assertEqual(report["classic_3tier_passed"], 0)
            self.assertEqual(report["perturbation_invariance_count"], 16)

            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            for html in (zh_html, en_html):
                self.assertIn("default-src 'none'; style-src 'unsafe-inline'", html)
                self.assertEqual(html.count('<section class="card">'), 7)
                self.assertIn("PR-16", html)

    def test_default_output_directory_artifacts_exist(self) -> None:
        report = run_benchmark()
        self.assertEqual(report["ai_native_passed"], 16)
        self.assertEqual(report["total_scenarios"], 16)


if __name__ == "__main__":
    unittest.main()
