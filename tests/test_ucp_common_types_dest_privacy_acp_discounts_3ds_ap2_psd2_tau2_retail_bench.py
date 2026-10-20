"""Unit tests for Stage 115 16-scenario (CP-01..CP-16) bilingual 7-Card 4:5 benchmark."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.ucp_common_types_dest_privacy_acp_discounts_3ds_ap2_psd2_tau2_retail_bench import (
    run_stage115_benchmark,
)


class TestStage115Benchmark(unittest.TestCase):
    def test_stage115_benchmark_16_scenarios_and_bilingual_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage115-report"
            report = run_stage115_benchmark(out_dir)
            self.assertEqual(report["summary"]["total_scenarios"], 16)
            self.assertEqual(report["summary"]["ai_native_passed"], 16)
            self.assertEqual(report["summary"]["classic_3tier_passed"], 4)
            self.assertEqual(report["summary"]["reversal_invariance_passed"], 16)
            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("1 / 7", zh_html)
            self.assertIn("7 / 7", zh_html)
            self.assertIn("1 / 7", en_html)
            self.assertIn("7 / 7", en_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", en_html)


if __name__ == "__main__":
    unittest.main()
