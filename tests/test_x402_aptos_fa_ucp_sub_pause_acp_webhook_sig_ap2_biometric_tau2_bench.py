"""Unit test for Stage 159 16-scenario (`AD-01..AD-16`) bilingual 7-Card benchmark."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.x402_aptos_fa_ucp_sub_pause_acp_webhook_sig_ap2_biometric_tau2_bench import run_benchmark


class Stage159BenchTests(unittest.TestCase):
    def test_stage159_benchmark_generates_16_scenario_bilingual_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage159-bench"
            report = run_benchmark(out_dir)
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["ai_native_passed"], 16)
            self.assertEqual(report["classic_3tier_passed"], 0)
            self.assertEqual(report["perturbation_consistent"], 16)
            self.assertTrue((out_dir / "report.json").is_file())
            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("1 / 7", zh_html)
            self.assertIn("7 / 7", zh_html)
            self.assertIn("AD-01", zh_html)
            self.assertIn("AD-16", zh_html)
            self.assertIn("Content-Security-Policy", en_html)
            self.assertIn("AD-16", en_html)


if __name__ == "__main__":
    unittest.main()
