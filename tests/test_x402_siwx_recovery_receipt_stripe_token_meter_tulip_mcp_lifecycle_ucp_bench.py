"""Unit test for Stage 121 16-scenario (`SR-01..SR-16`) bilingual 7-Card 4:5 benchmark."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.x402_siwx_recovery_receipt_stripe_token_meter_tulip_mcp_lifecycle_ucp_bench import (
    run_stage121_benchmark,
)


class Stage121BenchmarkTests(unittest.TestCase):
    def test_stage121_benchmark_16_of_16_and_renders_bilingual_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = run_stage121_benchmark(tmp)
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["passed_scenarios"], 16)
            self.assertEqual(report["pass_rate_pct"], 100.0)

            out = Path(tmp)
            self.assertTrue((out / "report.json").exists())
            zh_html = (out / "index.html").read_text(encoding="utf-8")
            en_html = (out / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("1 / 7", zh_html)
            self.assertIn("7 / 7", zh_html)
            self.assertIn("SR-08", zh_html)
            self.assertIn("1 / 7", en_html)
            self.assertIn("7 / 7", en_html)
            self.assertIn("SR-08", en_html)


if __name__ == "__main__":
    unittest.main()
