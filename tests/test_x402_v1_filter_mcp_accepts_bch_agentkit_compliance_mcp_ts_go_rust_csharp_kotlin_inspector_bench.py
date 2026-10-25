"""Unit tests for Stage 239 16-scenario 7-Card 4:5 visual benchmark runner (`PR-01..PR-16`)."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from lab.x402_v1_filter_mcp_accepts_bch_agentkit_compliance_mcp_ts_go_rust_csharp_kotlin_inspector_bench import (
    BENCHMARK_ID,
    generate_stage238_239_report,
    run_stage238_239_scenarios,
)


class Stage239BenchTest(unittest.TestCase):
    def test_scenarios_16_of_16_pass(self) -> None:
        scenarios = run_stage238_239_scenarios()
        self.assertEqual(len(scenarios), 16)
        self.assertTrue(all(s["ai_native_passed"] for s in scenarios))
        self.assertTrue(all(not s["classic_3tier_passed"] for s in scenarios))

    def test_generate_bilingual_7_card_report_and_csp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / BENCHMARK_ID
            summary = generate_stage238_239_report(out_dir)
            self.assertEqual(summary["total_scenarios"], 16)
            self.assertEqual(summary["ai_native_passed"], 16)
            self.assertEqual(summary["classic_3tier_passed"], 0)

            report_data = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(report_data["ai_native_pass_rate"], 1.0)
            self.assertEqual(len(report_data["scenarios"]), 16)

            for fname in ("index.html", "index.en.html"):
                html = (out_dir / fname).read_text(encoding="utf-8")
                self.assertIn("default-src 'none'; style-src 'unsafe-inline'", html)
                self.assertIn("1 / 7", html)
                self.assertIn("7 / 7", html)


if __name__ == "__main__":
    unittest.main()
