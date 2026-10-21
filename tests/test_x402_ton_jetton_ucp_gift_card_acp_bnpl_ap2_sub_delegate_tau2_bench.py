"""Unit tests for Stage 161 16-scenario (`TN-01..TN-16`) bilingual 7-Card benchmark."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.x402_ton_jetton_ucp_gift_card_acp_bnpl_ap2_sub_delegate_tau2_bench import (
    build_stage161_benchmark_report,
    write_stage161_benchmark_files,
)


class Stage161BenchmarkTests(unittest.TestCase):
    def test_stage161_benchmark_report_and_html_generation(self) -> None:
        report = build_stage161_benchmark_report()
        summary = report["summary"]
        self.assertEqual(summary["total_scenarios"], 16)
        self.assertEqual(summary["ai_native_passed"], 16)
        self.assertEqual(summary["classic_3tier_passed"], 0)
        self.assertEqual(summary["perturbation_consistency"], "16/16 (100.0%)")

        with tempfile.TemporaryDirectory() as tmp:
            paths = write_stage161_benchmark_files(Path(tmp))
            zh_html = Path(paths["index_html"]).read_text(encoding="utf-8")
            en_html = Path(paths["index_en_html"]).read_text(encoding="utf-8")
            self.assertIn("1 / 7", zh_html)
            self.assertIn("7 / 7", zh_html)
            self.assertIn("TN-16", zh_html)
            self.assertIn("1 / 7", en_html)
            self.assertIn("7 / 7", en_html)
            self.assertIn("TN-16", en_html)


if __name__ == "__main__":
    unittest.main()
