"""Unit tests for Stage 135 16-scenario (`AC-01..AC-16`) bilingual 7-Card 4:5 benchmark."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.x402_evm_auth_capture_svm_lighthouse_ucp_delegated_idp_mcp_secure_params_bench import (
    run_benchmark,
)


class Stage135BenchTests(unittest.TestCase):
    def test_stage135_benchmark_generates_16_scenarios_and_bilingual_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            report = run_benchmark(out_dir)
            self.assertEqual(report["stage"], 135)
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["ai_native_passed"], 16)
            self.assertEqual(report["classic_3tier_passed"], 0)
            self.assertEqual(report["perturbation_consistency_passed"], 16)
            self.assertTrue((out_dir / "report.json").exists())
            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("1 / 7", zh_html)
            self.assertIn("7 / 7", zh_html)
            self.assertIn("AC-16", zh_html)
            self.assertIn("1 / 7", en_html)
            self.assertIn("7 / 7", en_html)
            self.assertIn("AC-16", en_html)


if __name__ == "__main__":
    unittest.main()
