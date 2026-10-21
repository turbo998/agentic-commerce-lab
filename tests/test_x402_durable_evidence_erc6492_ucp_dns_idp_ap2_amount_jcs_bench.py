"""Unit tests for Stage 147 DE-01..DE-16 bilingual 7-Card 4:5 benchmark suite."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.x402_durable_evidence_erc6492_ucp_dns_idp_ap2_amount_jcs_bench import run_benchmark


class Stage147BenchTests(unittest.TestCase):
    def test_run_benchmark_generates_16_scenarios_and_bilingual_7card_decks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage-147-bench"
            report = run_benchmark(out_dir)
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["ai_native_passed"], 16)
            self.assertEqual(report["classic_3tier_passed"], 1)
            self.assertEqual(report["perturbation_consistency_passed"], 16)
            self.assertTrue((out_dir / "report.json").exists())
            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("1 / 7", zh_html)
            self.assertIn("7 / 7", zh_html)
            self.assertIn("DE-16", zh_html)
            self.assertIn("1 / 7", en_html)
            self.assertIn("7 / 7", en_html)
            self.assertIn("DE-16", en_html)


if __name__ == "__main__":
    unittest.main()
