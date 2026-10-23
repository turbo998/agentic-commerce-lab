"""Unit tests for Stage 197 16-scenario (UC-01..UC-16) 7-Card 4:5 benchmark suite."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.x402_upto_erc3009_stellar_casper_body_limit_ucp_idp_mcp_atsa_signing_bench import (
    run_benchmark,
    write_report,
)


class Stage197BenchTest(unittest.TestCase):
    def test_run_benchmark_16_scenarios_100_percent(self) -> None:
        summary = run_benchmark()
        self.assertEqual(summary["total_scenarios"], 16)
        self.assertEqual(summary["ai_native_passed"], 16)
        self.assertEqual(summary["ai_native_pass_rate_pct"], 100.0)
        self.assertEqual(summary["classic_3tier_passed"], 0)
        ids = [s["scenario_id"] for s in summary["scenarios"]]
        self.assertEqual(ids[0], "UC-01")
        self.assertEqual(ids[-1], "UC-16")

    def test_write_report_generates_self_contained_7card_decks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            write_report(out_dir)
            for name in ("report.json", "index.html", "index.en.html"):
                self.assertTrue((out_dir / name).is_file())
            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", en_html)
            self.assertEqual(zh_html.count('<section class="card">'), 7)
            self.assertEqual(en_html.count('<section class="card">'), 7)


if __name__ == "__main__":
    unittest.main()
