"""Unit tests for Stage 105 16-scenario (`WB-01..WB-16`) bilingual 7-Card 4:5 benchmark suite."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.ucp_wba_keys_ask_rdns_acp_3ds_decimal_tau2_nl_judge_bench import (
    run_benchmark,
)


class TestStage105Benchmark(unittest.TestCase):
    def test_wb01_to_wb16_full_matrix_and_reversal_invariance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            report = run_benchmark(out)
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["ai_native_passed"], 16)
            self.assertEqual(report["ai_native_pass_rate_pct"], 100.0)
            self.assertEqual(report["classic_3tier_passed"], 4)
            self.assertEqual(report["classic_3tier_pass_rate_pct"], 25.0)
            self.assertEqual(report["reversal_invariant_count"], 16)
            self.assertTrue((out / "report.json").exists())
            self.assertTrue((out / "index.html").exists())
            self.assertTrue((out / "index.en.html").exists())

    def test_7card_csp_and_bilingual_headers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            run_benchmark(out)
            zh_html = (out / "index.html").read_text(encoding="utf-8")
            en_html = (out / "index.en.html").read_text(encoding="utf-8")
            for doc in (zh_html, en_html):
                self.assertIn("default-src 'none'; style-src 'unsafe-inline'", doc)
                for n in range(1, 8):
                    self.assertIn(f"{n} / 7 ·", doc)
                self.assertIn("WB-01", doc)
                self.assertIn("WB-16", doc)


if __name__ == "__main__":
    unittest.main()
