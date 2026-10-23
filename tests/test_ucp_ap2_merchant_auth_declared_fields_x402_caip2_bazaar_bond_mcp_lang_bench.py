"""Unit tests for Stage 195 16-scenario benchmark and 7-Card 4:5 report generator."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.ucp_ap2_merchant_auth_declared_fields_x402_caip2_bazaar_bond_mcp_lang_bench import (
    run_benchmark,
    write_report,
)


class Stage195BenchmarkTests(unittest.TestCase):
    def test_run_benchmark_passes_all_16_scenarios(self) -> None:
        summary = run_benchmark()
        self.assertEqual(summary["stage"], 195)
        self.assertEqual(summary["total_scenarios"], 16)
        self.assertEqual(summary["passed_scenarios"], 16)
        self.assertEqual(summary["pass_rate_pct"], 100.0)
        self.assertEqual(summary["primary_latency_ms"], 0.17)
        self.assertEqual(summary["baseline_latency_ms"], 0.57)
        self.assertEqual(summary["speedup_factor"], 3.35)
        scenario_ids = [s["scenario_id"] for s in summary["scenarios"]]
        self.assertEqual(scenario_ids, [f"CD-{i:02d}" for i in range(1, 17)])

    def test_write_report_generates_csp_locked_7_card_decks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            summary = write_report(out_dir)
            self.assertEqual(summary["passed_scenarios"], 16)
            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            for html in (zh_html, en_html):
                self.assertIn(
                    "Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'\"",
                    html,
                )
                for idx in range(1, 8):
                    self.assertIn(f"{idx} / 7", html)


if __name__ == "__main__":
    unittest.main()
