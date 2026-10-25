"""Unit tests for Stage 231 (230-Stage Milestone!) 16-scenario 7-Card benchmark generator."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.x402_expected_amount_delivery_receipt_lnbtc_ucp_lodging_mcp_sep3149_bench import (
    generate_benchmark_report,
    run_benchmark_scenarios,
)


class Stage231BenchTest(unittest.TestCase):
    def test_scenarios_all_pass_and_classic_fails(self) -> None:
        scenarios = run_benchmark_scenarios()
        self.assertEqual(len(scenarios), 16)
        self.assertTrue(all(s["ai_native_passed"] for s in scenarios))
        self.assertTrue(all(not s["classic_3tier_passed"] for s in scenarios))
        self.assertTrue(all(s["perturbation_consistent"] for s in scenarios))

    def test_generate_bilingual_7card_report_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage231-report"
            report = generate_benchmark_report(out_dir)
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["ai_native_passed"], 16)
            self.assertEqual(report["classic_3tier_passed"], 0)
            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            for html_doc in (zh_html, en_html):
                self.assertIn("default-src 'none'; style-src 'unsafe-inline'", html_doc)
                for idx in range(1, 8):
                    self.assertIn(f"<span>{idx} / 7</span>", html_doc)


if __name__ == "__main__":
    unittest.main()
