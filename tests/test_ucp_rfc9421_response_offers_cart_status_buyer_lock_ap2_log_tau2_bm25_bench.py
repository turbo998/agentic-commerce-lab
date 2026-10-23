"""Unit tests for Stage 203 (`PR-01..PR-16`) 7-Card 4:5 visual benchmark suite."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.ucp_rfc9421_response_offers_cart_status_buyer_lock_ap2_log_tau2_bm25_bench import (
    run_benchmark,
)


class TestStage203Bench(unittest.TestCase):
    def test_benchmark_16_scenarios_and_bilingual_7_card_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            report = run_benchmark(out_dir)
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["ai_native_passed"], 16)
            self.assertEqual(report["classic_3tier_passed"], 0)
            self.assertEqual(report["perturbation_consistent_count"], 16)
            self.assertEqual(
                [s["scenario_id"] for s in report["scenarios"]],
                [f"PR-{i:02d}" for i in range(1, 17)],
            )

            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            for html in (zh_html, en_html):
                self.assertIn("default-src 'none'; style-src 'unsafe-inline'", html)
                for card_idx in range(1, 8):
                    self.assertIn(f"{card_idx} / 7", html)
                self.assertIn("PR-01", html)
                self.assertIn("PR-16", html)


if __name__ == "__main__":
    unittest.main()
