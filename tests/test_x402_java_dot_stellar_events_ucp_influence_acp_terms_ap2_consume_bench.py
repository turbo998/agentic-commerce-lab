"""Unit tests for Stage 145 16-scenario bilingual 7-Card 4:5 benchmark."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.x402_java_dot_stellar_events_ucp_influence_acp_terms_ap2_consume_bench import (
    run_benchmark,
)


class Stage145BenchTests(unittest.TestCase):
    def test_stage145_benchmark_generates_16_scenario_bilingual_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            report = run_benchmark(out)
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["ai_native_passed"], 16)
            self.assertEqual(report["classic_3tier_passed"], 1)
            self.assertTrue((out / "report.json").exists())
            zh_html = (out / "index.html").read_text(encoding="utf-8")
            en_html = (out / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)
            self.assertIn("JS-16", zh_html)
            self.assertIn("JS-16", en_html)


if __name__ == "__main__":
    unittest.main()
