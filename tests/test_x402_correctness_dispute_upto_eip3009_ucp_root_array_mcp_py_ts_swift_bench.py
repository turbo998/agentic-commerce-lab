"""Unit tests for Stage 241 (240-Stage Milestone!) 16-scenario 7-Card 4:5 benchmark runner."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.x402_correctness_dispute_upto_eip3009_ucp_root_array_mcp_py_ts_swift_bench import (
    run_benchmark,
)


class Stage241BenchmarkTest(unittest.TestCase):
    def test_benchmark_16_of_16_and_7card_csp_compliance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage241-bench"
            summary = run_benchmark(out_dir)
            self.assertEqual(summary["total_scenarios"], 16)
            self.assertEqual(summary["ai_native_passed"], 16)
            self.assertEqual(summary["ai_native_pass_rate_pct"], 100.0)
            self.assertEqual(summary["classic_3tier_passed"], 0)
            self.assertEqual(summary["perturbation_consistency_pct"], 100.0)

            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", en_html)
            self.assertIn("1 / 7", zh_html)
            self.assertIn("7 / 7", en_html)

    def test_scenario_ids_cover_pr01_through_pr16(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            summary = run_benchmark(Path(tmp) / "stage241-ids")
            ids = [s["scenario_id"] for s in summary["scenarios"]]
            self.assertEqual(ids, [f"PR-{i:02d}" for i in range(1, 17)])


if __name__ == "__main__":
    unittest.main()
