"""Unit tests for Stage 67 16-scenario (`TO-01..TO-16`) bilingual 7-Card 4:5 benchmark suite."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.ucp_token_context_cart_offer_acp_telemetry_ap2_instrument_tau2_abort_bench import (
    DEFAULT_OUTPUT_DIR,
    run_benchmark,
)


class Stage67BenchmarkTests(unittest.TestCase):
    def test_stage67_benchmark_generates_16_scenarios_and_bilingual_7card_decks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage67-bench"
            report = run_benchmark(out_dir)

            summary = report["summary"]
            self.assertEqual(summary["total_scenarios"], 16)
            self.assertEqual(summary["ai_native_passed"], 16)
            self.assertEqual(summary["ai_native_accuracy_pct"], 100.0)
            self.assertEqual(summary["classic_3tier_passed"], 4)
            self.assertEqual(summary["classic_3tier_accuracy_pct"], 25.0)
            self.assertEqual(summary["perturbation_consistency_pct"], 100.0)

            cn_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            for idx in range(1, 8):
                self.assertIn(f"{idx} / 7 ·", cn_html)
                self.assertIn(f"{idx} / 7 ·", en_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", cn_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", en_html)
            self.assertIn("TO-10", cn_html)
            self.assertIn("TO-16", en_html)

    def test_default_output_directory_artifacts_exist(self) -> None:
        report = run_benchmark(DEFAULT_OUTPUT_DIR)
        self.assertTrue((DEFAULT_OUTPUT_DIR / "report.json").exists())
        self.assertTrue((DEFAULT_OUTPUT_DIR / "index.html").exists())
        self.assertTrue((DEFAULT_OUTPUT_DIR / "index.en.html").exists())
        self.assertEqual(len(report["scenarios"]), 16)


if __name__ == "__main__":
    unittest.main()
