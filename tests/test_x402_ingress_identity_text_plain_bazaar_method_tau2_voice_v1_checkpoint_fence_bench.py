"""Unit tests for Stage 189 16-scenario (`XI-01..XI-16`) benchmark and 7-Card report."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.x402_ingress_identity_text_plain_bazaar_method_tau2_voice_v1_checkpoint_fence_bench import (
    run_benchmark,
    write_Benchmark_reports,
)


class TestStage189Benchmark(unittest.TestCase):
    def test_16_scenarios_pass(self) -> None:
        summary = run_benchmark()
        self.assertEqual(summary["total_scenarios"], 16)
        self.assertEqual(summary["passed_scenarios"], 16)
        self.assertEqual(summary["pass_rate_pct"], 100.0)
        self.assertEqual(summary["primary_latency_ms"], 0.17)

    def test_write_7_card_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            write_Benchmark_reports(out)
            zh_html = (out / "index.html").read_text(encoding="utf-8")
            en_html = (out / "index.en.html").read_text(encoding="utf-8")
            self.assertIn(
                "default-src 'none'; style-src 'unsafe-inline'", zh_html
            )
            self.assertIn("7 / 7 · MY TAKE", en_html)
            self.assertIn("XI-16", zh_html)


if __name__ == "__main__":
    unittest.main()
