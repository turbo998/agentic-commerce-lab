"""Unit tests for Stage 245 (245-Stage Milestone!) 16-scenario 7-Card 4:5 visual benchmark."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.agentkit_rfq_tokencheck_dexra_mcp_ts_go_rust_csharp_java_bench import (
    BENCHMARK_ID,
    run_benchmark,
)


class Stage245AgentKitMcpMultiSdkBenchTest(unittest.TestCase):
    def test_benchmark_16_of_16_pass_and_csp_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = run_benchmark(output_dir=tmpdir)
            self.assertEqual(summary["benchmark_id"], BENCHMARK_ID)
            self.assertEqual(summary["total_scenarios"], 16)
            self.assertEqual(summary["ai_native_passed"], 16)
            self.assertEqual(summary["classic_3tier_passed"], 0)
            self.assertEqual(summary["pass_rate_pct"], 100.0)

            zh_html = Path(summary["report_html"]).read_text(encoding="utf-8")
            en_html = Path(summary["report_en_html"]).read_text(encoding="utf-8")
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", en_html)
            self.assertIn("1 / 7", zh_html)
            self.assertIn("7 / 7", en_html)

    def test_scenario_ids_pr01_through_pr16_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = run_benchmark(output_dir=tmpdir)
            ids = [s["scenario_id"] for s in summary["scenarios"]]
            self.assertEqual(ids, [f"PR-{i:02d}" for i in range(1, 17)])
            self.assertTrue(all(s["passed"] for s in summary["scenarios"]))


if __name__ == "__main__":
    unittest.main()
