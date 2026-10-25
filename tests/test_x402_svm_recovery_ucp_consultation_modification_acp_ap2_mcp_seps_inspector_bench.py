"""Unit tests for Stage 235 (235-Stage Milestone!) 7-Card 4:5 visual benchmark report (`PR-01..PR-16`)."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.x402_svm_recovery_ucp_consultation_modification_acp_ap2_mcp_seps_inspector_bench import run_benchmark


class TestStage235Bench(unittest.TestCase):
    def test_stage235_benchmark_scores_16_of_16_and_renders_bilingual_7card_decks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            report = run_benchmark(out_dir)
            self.assertEqual(report["stage"], "Stage 235")
            self.assertEqual(report["milestone"], "235-Stage Milestone")
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["ai_native_passed"], 16)
            self.assertEqual(report["classic_3tier_passed"], 0)
            self.assertEqual(report["perturbation_consistency_pct"], 100.0)

            for fname in ("index.html", "index.en.html"):
                html = (out_dir / fname).read_text(encoding="utf-8")
                self.assertIn("default-src 'none'; style-src 'unsafe-inline'", html)
                self.assertEqual(html.count('<section class="card">'), 7)

    def test_stage235_default_report_artifacts_exist(self) -> None:
        report = run_benchmark()
        self.assertEqual(report["ai_native_passed"], 16)


if __name__ == "__main__":
    unittest.main()
