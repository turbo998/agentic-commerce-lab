"""Unit tests for Stage 119 16-scenario (SU-01..SU-16) bilingual 7-Card 4:5 benchmark."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.x402_stellar_upto_ucp_media_headers_stripe_plugin_mcp_events_tau2_bench import (
    run_benchmark,
    write_benchmark_artifacts,
)


class Stage119BenchmarkTests(unittest.TestCase):
    def test_stage119_benchmark_16_scenarios_and_bilingual_cards(self) -> None:
        summary = run_benchmark()
        self.assertEqual(summary["total_scenarios"], 16)
        self.assertEqual(summary["ai_native_passed"], 16)
        self.assertEqual(summary["classic_3tier_passed"], 4)
        self.assertEqual(summary["reversal_invariant_count"], 16)

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage119-report"
            write_benchmark_artifacts(out_dir)
            self.assertTrue((out_dir / "report.json").exists())
            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("1 / 7", zh_html)
            self.assertIn("7 / 7", zh_html)
            self.assertIn("SU-16", en_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", en_html)


if __name__ == "__main__":
    unittest.main()
