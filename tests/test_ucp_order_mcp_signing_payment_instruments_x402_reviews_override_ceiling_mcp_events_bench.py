"""Unit tests for Stage 179 16-scenario (`OM-01..OM-16`) 7-card benchmark suite."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.ucp_order_mcp_signing_payment_instruments_x402_reviews_override_ceiling_mcp_events_bench import (
    run_benchmark,
)


class TestStage179Bench(unittest.TestCase):
    def test_stage_179_benchmark_and_7card_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            report = run_benchmark(out_dir)
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["ai_native_passed"], 16)
            self.assertEqual(report["ai_native_pass_rate_pct"], 100.0)
            self.assertEqual(report["perturbation_consistent"], 16)

            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            for html in (zh_html, en_html):
                self.assertIn("default-src 'none'; style-src 'unsafe-inline'", html)
                for card_idx in range(1, 8):
                    self.assertIn(f"{card_idx} / 7", html)
                self.assertIn("OM-01", html)
                self.assertIn("OM-16", html)


if __name__ == "__main__":
    unittest.main()
