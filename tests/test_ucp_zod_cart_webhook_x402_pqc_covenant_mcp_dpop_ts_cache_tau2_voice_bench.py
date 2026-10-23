"""Unit tests for Stage 217 16-scenario 7-Card 4:5 visual benchmark suite."""

from __future__ import annotations

import tempfile
import unittest
import pathlib

from lab.ucp_zod_cart_webhook_x402_pqc_covenant_mcp_dpop_ts_cache_tau2_voice_bench import (
    run_benchmark,
)


class TestStage217Bench(unittest.TestCase):
    def test_benchmark_generates_bilingual_7card_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = pathlib.Path(tmp) / "stage217-bench"
            summary = run_benchmark(out_dir)
            self.assertEqual(summary["total_scenarios"], 16)
            self.assertEqual(summary["ai_native_passed"], 16)
            self.assertEqual(summary["classic_3tier_passed"], 0)
            self.assertTrue((out_dir / "report.json").exists())
            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", en_html)
            for idx in range(1, 8):
                self.assertIn(f"{idx} / 7", zh_html)
                self.assertIn(f"{idx} / 7", en_html)


if __name__ == "__main__":
    unittest.main()
