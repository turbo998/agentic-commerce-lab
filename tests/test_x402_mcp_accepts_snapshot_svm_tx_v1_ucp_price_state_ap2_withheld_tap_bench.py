"""Unit tests for Stage 141 16-scenario bilingual 7-Card 4:5 benchmark."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.x402_mcp_accepts_snapshot_svm_tx_v1_ucp_price_state_ap2_withheld_tap_bench import (
    run_benchmark,
)


class Stage141BenchmarkTests(unittest.TestCase):
    def test_stage_141_benchmark_generates_16_scenarios_and_bilingual_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage141"
            report = run_benchmark(out_dir)
            self.assertEqual(report["stage"], 141)
            self.assertEqual(report["guard_stage"], 140)
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["passed_scenarios"], 16)
            self.assertEqual(report["pass_rate"], 1.0)
            self.assertTrue((out_dir / "report.json").exists())
            self.assertTrue((out_dir / "index.html").exists())
            self.assertTrue((out_dir / "index.en.html").exists())


if __name__ == "__main__":
    unittest.main()
