"""Unit tests for Stage 93 16-scenario (`FS-01..FS-16`) bilingual 7-Card 4:5 benchmark."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.ucp_fee_ecap_acp_sale_crypto_ap2_receipt_tau2_airline_ctx_bench import run_benchmark


class TestStage93Benchmark(unittest.TestCase):
    def test_benchmark_16_scenarios_and_perturbation_consistency(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            report = run_benchmark(out_dir)
            summary = report["summary"]
            self.assertEqual(summary["total_scenarios"], 16)
            self.assertEqual(summary["ai_native_passed"], 16)
            self.assertEqual(summary["ai_native_accuracy_pct"], 100.0)
            self.assertEqual(summary["classic_3tier_passed"], 4)
            self.assertEqual(summary["classic_3tier_accuracy_pct"], 25.0)
            self.assertEqual(summary["perturbation_consistent"], 16)
            self.assertTrue((out_dir / "report.json").exists())
            self.assertTrue((out_dir / "index.html").exists())
            self.assertTrue((out_dir / "index.en.html").exists())

    def test_generated_bilingual_cards_csp_and_7card_markers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            run_benchmark(out_dir)
            for fname in ("index.html", "index.en.html"):
                html = (out_dir / fname).read_text(encoding="utf-8")
                self.assertIn("default-src 'none'; style-src 'unsafe-inline'", html)
                for idx in range(1, 8):
                    self.assertIn(f"{idx} / 7", html)


if __name__ == "__main__":
    unittest.main()
