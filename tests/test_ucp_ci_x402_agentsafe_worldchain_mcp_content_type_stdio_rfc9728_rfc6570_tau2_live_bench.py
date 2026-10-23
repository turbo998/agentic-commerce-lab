"""Unit test for Stage 219 16-scenario 7-Card 4:5 benchmark suite."""

from __future__ import annotations

import unittest
from pathlib import Path

from lab.ucp_ci_x402_agentsafe_worldchain_mcp_content_type_stdio_rfc9728_rfc6570_tau2_live_bench import (
    REPORT_DIR,
    run_benchmark,
)


class TestStage219Bench(unittest.TestCase):
    def test_benchmark_generates_16_scenarios_and_7_cards(self) -> None:
        summary = run_benchmark(REPORT_DIR)
        self.assertEqual(summary["total_scenarios"], 16)
        self.assertEqual(summary["passed_scenarios"], 16)
        self.assertEqual(summary["Pass_at_1"], 1.0)
        self.assertEqual(summary["Pass_hat_4"], 1.0)
        self.assertEqual(summary["Guard_Compensation_Score"], 1.0)

        for fname in ("report.json", "index.html", "index.en.html"):
            fpath = Path(REPORT_DIR) / fname
            self.assertTrue(fpath.exists(), f"Missing {fpath}")

        zh_html = (Path(REPORT_DIR) / "index.html").read_text(encoding="utf-8")
        en_html = (Path(REPORT_DIR) / "index.en.html").read_text(encoding="utf-8")
        for html in (zh_html, en_html):
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", html)
            for idx in range(1, 8):
                self.assertIn(f'data-card="{idx}/7"', html)


if __name__ == "__main__":
    unittest.main()
