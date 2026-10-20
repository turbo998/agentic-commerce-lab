"""Unit tests for Stage 87 16-scenario bilingual 7-Card 4:5 benchmark suite (AP-01..AP-16)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.ucp_attr_path_acp_discount_res_x402_nowallet_erc8021_tau2_hospitality_bench import (
    run_benchmark,
)


class Stage87BenchmarkTests(unittest.TestCase):
    def test_stage87_benchmark_16_scenarios_and_bilingual_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "stage87-bench"
            report = run_benchmark(out)
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["ai_native_passed"], 16)
            self.assertEqual(report["classic_3tier_passed"], 4)
            self.assertEqual(report["reversal_consistency_passed"], 16)

            zh_html = (out / "index.html").read_text(encoding="utf-8")
            en_html = (out / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("1 / 7", zh_html)
            self.assertIn("7 / 7", zh_html)
            self.assertIn("AP-01", zh_html)
            self.assertIn("AP-16", zh_html)
            self.assertIn("1 / 7", en_html)
            self.assertIn("7 / 7", en_html)
            self.assertIn("AP-01", en_html)
            self.assertIn("AP-16", en_html)

    def test_stage87_Scenario_ids_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = run_benchmark(Path(tmp) / "stage87-ids")
            ids = [s["id"] for s in report["scenarios"]]
            self.assertEqual(ids, [f"AP-{i:02d}" for i in range(1, 17)])


if __name__ == "__main__":
    unittest.main()
