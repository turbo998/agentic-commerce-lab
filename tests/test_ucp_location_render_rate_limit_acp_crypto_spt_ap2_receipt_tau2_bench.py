"""Unit tests for Stage 113 16-scenario (LR-01..LR-16) bilingual 7-Card 4:5 benchmark."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.ucp_location_render_rate_limit_acp_crypto_spt_ap2_receipt_tau2_bench import (
    run_stage113_benchmark,
)


class TestStage113Benchmark(unittest.TestCase):
    def test_stage113_benchmark_16_scenarios_and_bilingual_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage113-report"
            report = run_stage113_benchmark(out_dir)
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
