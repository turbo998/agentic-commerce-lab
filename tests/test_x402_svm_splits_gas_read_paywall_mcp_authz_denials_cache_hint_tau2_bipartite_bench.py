"""Unit tests for Stage 193 16-scenario (`MS-01..MS-16`) benchmark and 7-Card 4:5 report generator."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from lab.x402_svm_splits_gas_read_paywall_mcp_authz_denials_cache_hint_tau2_bipartite_bench import (
    run_benchmark,
    write_report_artifacts,
)


class Stage193BenchmarkTests(unittest.TestCase):
    def test_run_benchmark_16_scenarios_all_pass(self) -> None:
        summary = run_benchmark()
        self.assertEqual(summary["stage"], 193)
        self.assertEqual(summary["total_scenarios"], 16)
        self.assertEqual(summary["passed_scenarios"], 16)
        self.assertEqual(summary["pass_rate_pct"], 100.0)
        self.assertAlmostEqual(summary["primary_latency_ms"], 0.17, places=2)
        ids = [s["scenario_id"] for s in summary["scenarios"]]
        self.assertEqual(ids[0], "MS-01")
        self.assertEqual(ids[-1], "MS-16")

    def test_write_report_artifacts_csp_and_bilingual_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            summary = write_report_artifacts(out_dir)
            self.assertEqual(summary["passed_scenarios"], 16)
            report_json = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(report_json["total_scenarios"], 16)
            for fname in ("index.html", "index.en.html"):
                html = (out_dir / fname).read_text(encoding="utf-8")
                self.assertIn(
                    "Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'\"",
                    html,
                )
                for idx in range(1, 8):
                    self.assertIn(f"{idx} / 7 ·", html)


if __name__ == "__main__":
    unittest.main()
