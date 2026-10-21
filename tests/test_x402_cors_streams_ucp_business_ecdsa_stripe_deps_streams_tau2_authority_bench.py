"""Unit test for Stage 123 16-scenario (`BC-01..BC-16`) bilingual 7-Card 4:5 benchmark."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.x402_cors_streams_ucp_business_ecdsa_stripe_deps_streams_tau2_authority_bench import (
    run_stage123_benchmark,
)


class Stage123BenchmarkTests(unittest.TestCase):
    def test_stage123_benchmark_16_of_16_and_renders_bilingual_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = run_stage123_benchmark(tmp)
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["passed_scenarios"], 16)
            self.assertEqual(report["pass_rate_pct"], 100.0)

            out = Path(tmp)
            self.assertTrue((out / "report.json").exists())
            zh_html = (out / "index.html").read_text(encoding="utf-8")
            en_html = (out / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("1 / 7", zh_html)
            self.assertIn("7 / 7", zh_html)
            self.assertIn("BC-08", zh_html)
            self.assertIn("1 / 7", en_html)
            self.assertIn("7 / 7", en_html)
            self.assertIn("BC-08", en_html)


if __name__ == "__main__":
    unittest.main()
