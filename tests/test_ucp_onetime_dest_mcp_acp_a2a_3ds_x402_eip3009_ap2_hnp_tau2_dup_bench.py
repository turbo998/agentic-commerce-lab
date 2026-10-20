"""Unit tests for Stage 85 16-scenario bilingual 7-Card 4:5 benchmark suite (OD-01..OD-16)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.ucp_onetime_dest_mcp_acp_a2a_3ds_x402_eip3009_ap2_hnp_tau2_dup_bench import (
    run_stage85_benchmark,
)


class Stage85BenchmarkTests(unittest.TestCase):
    def test_stage85_benchmark_16_scenarios_and_bilingual_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage85"
            report = run_stage85_benchmark(out_dir)

            summary = report["summary"]
            self.assertEqual(summary["total_scenarios"], 16)
            self.assertEqual(summary["ai_native_passed"], 16)
            self.assertEqual(summary["ai_native_accuracy_pct"], 100.0)
            self.assertEqual(summary["classic_3tier_passed"], 4)
            self.assertEqual(summary["classic_3tier_accuracy_pct"], 25.0)
            self.assertEqual(summary["perturbation_consistency_pct"], 100.0)

            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            for html_doc in (zh_html, en_html):
                self.assertIn("default-src 'none'; style-src 'unsafe-inline'", html_doc)
                for idx in range(1, 8):
                    self.assertIn(f"{idx} / 7", html_doc)
                self.assertIn("OD-01", html_doc)
                self.assertIn("OD-16", html_doc)

    def test_stage85_scenario_ids_monotonic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = run_stage85_benchmark(Path(tmp) / "stage85_ids")
            ids = [s["id"] for s in report["scenarios"]]
            self.assertEqual(ids, [f"OD-{i:02d}" for i in range(1, 17)])


if __name__ == "__main__":
    unittest.main()
