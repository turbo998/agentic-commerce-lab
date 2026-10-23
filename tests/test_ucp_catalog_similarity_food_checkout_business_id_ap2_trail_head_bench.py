"""Unit tests for Stage 177 16-scenario (`CF-01..CF-16`) 7-card benchmark suite."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.ucp_catalog_similarity_food_checkout_business_id_ap2_trail_head_bench import (
    run_benchmark,
)


class TestStage177Bench(unittest.TestCase):
    def test_stage_177_benchmark_and_7card_html(self) -> None:
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
                self.assertIn("CF-01", html)
                self.assertIn("CF-16", html)


if __name__ == "__main__":
    unittest.main()
