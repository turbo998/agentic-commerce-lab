"""Unit test for Stage 215 16-scenario 7-Card 4:5 visual benchmark generator."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.ucp_totals_lodging_acp_ajv_ap2_jcs_did_x402_svm_v1_bazaar_mcp_attestation_tau2_paired_bench import (
    run_benchmark,
)


class Stage215BenchTest(unittest.TestCase):
    def test_benchmark_generates_16_passed_scenarios_and_7_card_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage215-bench"
            report = run_benchmark(out_dir)
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["ai_native_passed"], 16)
            self.assertEqual(report["classic_3tier_passed"], 0)
            self.assertTrue((out_dir / "report.json").exists())
            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)
            self.assertIn("7 / 7 · MY TAKE", en_html)


if __name__ == "__main__":
    unittest.main()
