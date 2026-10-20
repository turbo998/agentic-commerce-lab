"""Unit tests for Stage 95 16-scenario (WA-01..WA-16) bilingual 7-Card 4:5 benchmark."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.ucp_wallet_attest_discount_acp_virtual_x402_siwx_tau2_json_norm_bench import (
    run_stage95_benchmark,
)


class TestStage95Benchmark(unittest.TestCase):
    def test_stage95_benchmark_16_scenarios_and_bilingual_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage95-bench"
            report = run_stage95_benchmark(out_dir)
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["ai_native_passed"], 16)
            self.assertEqual(report["ai_native_pass_rate"], 100.0)
            self.assertEqual(report["classic_3tier_passed"], 4)
            self.assertEqual(report["classic_3tier_pass_rate"], 25.0)
            self.assertEqual(report["perturbation_consistent_count"], 16)

            ids = [s["id"] for s in report["scenarios"]]
            self.assertEqual(ids[0], "WA-01")
            self.assertEqual(ids[-1], "WA-16")

            cn_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            for html in (cn_html, en_html):
                self.assertIn("Content-Security-Policy", html)
                self.assertIn("1 / 7", html)
                self.assertIn("7 / 7", html)
                self.assertIn("WA-01", html)
                self.assertIn("WA-16", html)

    def test_stage95_default_reports_generated(self) -> None:
        report = run_stage95_benchmark()
        self.assertEqual(report["ai_native_passed"], 16)
        repo_root = Path(__file__).resolve().parent.parent
        report_dir = (
            repo_root
            / "reports"
            / "agentic-commerce-ucp-wallet-attest-discount-acp-virtual-x402-siwx-tau2-json-norm-bench"
        )
        self.assertTrue((report_dir / "report.json").exists())
        self.assertTrue((report_dir / "index.html").exists())
        self.assertTrue((report_dir / "index.en.html").exists())


if __name__ == "__main__":
    unittest.main()
