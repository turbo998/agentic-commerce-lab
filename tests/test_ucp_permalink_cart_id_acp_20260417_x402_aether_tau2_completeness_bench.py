"""Unit tests for Stage 109 16-scenario bilingual 7-Card 4:5 benchmark suite."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.ucp_permalink_cart_id_acp_20260417_x402_aether_tau2_completeness_bench import (
    generate_stage_109_benchmark_report,
)


class TestStage109Benchmark(unittest.TestCase):
    def test_stage_109_benchmark_16_scenarios_and_bilingual_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage109"
            report = generate_stage_109_benchmark_report(out_dir=out_dir)
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["ai_native_passed"], 16)
            self.assertEqual(report["classic_3tier_passed"], 4)
            self.assertEqual(report["reversal_invariance_passed"], 16)

            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", en_html)
            self.assertEqual(zh_html.count('class="card"'), 7)
            self.assertEqual(en_html.count('class="card"'), 7)
            self.assertIn("PC-01", zh_html)
            self.assertIn("PC-16", en_html)


if __name__ == "__main__":
    unittest.main()
