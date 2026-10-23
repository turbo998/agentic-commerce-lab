"""Unit tests for Stage 187 16-scenario (`PR-01..PR-16`) benchmark suite and 7-Card report."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.ucp_return_policy_purchase_options_ap2_dispute_resolver_revocation_mcp_task_log_bench import (
    run_stage187_benchmark,
    write_stage187_report,
)


class TestStage187Benchmark(unittest.TestCase):
    def test_stage187_benchmark_16_scenarios_all_pass(self) -> None:
        summary = run_stage187_benchmark()
        self.assertEqual(summary["stage"], 187)
        self.assertEqual(summary["total_scenarios"], 16)
        self.assertEqual(summary["passed_scenarios"], 16)
        self.assertEqual(summary["pass_rate_pct"], 100.0)
        self.assertEqual(summary["median_latency_ms"], 0.17)
        self.assertEqual(summary["baseline_median_latency_ms"], 0.55)
        self.assertEqual(summary["speedup_factor"], 3.24)
        ids = [s["scenario_id"] for s in summary["scenarios"]]
        self.assertEqual(ids, [f"PR-{i:02d}" for i in range(1, 17)])

    def test_write_stage187_report_generates_csp_locked_7cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            report_json = write_stage187_report(out_dir)
            self.assertTrue(report_json.exists())
            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            for html in (zh_html, en_html):
                self.assertIn(
                    "Content-Security-Policy",
                    html,
                )
                self.assertIn(
                    "default-src 'none'; style-src 'unsafe-inline'",
                    html,
                )
                self.assertEqual(html.count('class="card"'), 7)
                self.assertIn("PR-01", html)
                self.assertIn("PR-16", html)


if __name__ == "__main__":
    unittest.main()
