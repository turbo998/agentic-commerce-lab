"""Unit tests for Stage 99 16-scenario (DR-01..DR-16) bilingual 7-Card 4:5 benchmark."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.ucp_disclosure_return_acp_del_auth_ap2_session_tau2_goaway_bench import (
    run_benchmark,
)


class TestStage99Benchmark(unittest.TestCase):
    def test_stage99_benchmark_16_scenarios_and_bilingual_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            summary = run_benchmark(tmp)
            self.assertEqual(summary["total_scenarios"], 16)
            self.assertEqual(summary["ai_native_passed"], 16)
            self.assertEqual(summary["ai_native_accuracy_pct"], 100.0)
            self.assertEqual(summary["classic_3tier_passed"], 4)
            self.assertEqual(summary["classic_3tier_accuracy_pct"], 25.0)
            self.assertEqual(summary["reversal_consistency"], "16/16")

            out = Path(tmp)
            self.assertTrue((out / "report.json").exists())
            zh_html = (out / "index.html").read_text(encoding="utf-8")
            en_html = (out / "index.en.html").read_text(encoding="utf-8")
            for idx in range(1, 8):
                self.assertIn(f'id="card-{idx}"', zh_html)
                self.assertIn(f'id="card-{idx}"', en_html)
            self.assertIn("index.en.html", zh_html)
            self.assertIn("index.html", en_html)

    def test_stage99_default_reports_generated(self) -> None:
        summary = run_benchmark()
        self.assertEqual(summary["ai_native_passed"], 16)
        base = Path(
            "reports/agentic-commerce-ucp-disclosure-return-acp-del-auth-ap2-session-tau2-goaway-bench"
        )
        self.assertTrue((base / "report.json").exists())
        self.assertTrue((base / "index.html").exists())
        self.assertTrue((base / "index.en.html").exists())


if __name__ == "__main__":
    unittest.main()
