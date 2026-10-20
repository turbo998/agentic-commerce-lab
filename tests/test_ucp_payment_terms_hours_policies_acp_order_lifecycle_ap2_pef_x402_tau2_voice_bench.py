"""Unit tests for Stage 77 (`PT-01..PT-16`) 16-scenario bilingual 7-Card 4:5 benchmark suite."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.ucp_payment_terms_hours_policies_acp_order_lifecycle_ap2_pef_x402_tau2_voice_bench import (
    DEFAULT_REPORT_DIR,
    run_benchmark,
)


class TestStage77PaymentTermsOrderLifecyclePefVoiceBench(unittest.TestCase):
    def test_benchmark_16_scenarios_and_bilingual_7card_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage77-bench"
            report = run_benchmark(out_dir)

            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["ai_native_passed"], 16)
            self.assertEqual(report["ai_native_accuracy_pct"], 100.0)
            self.assertEqual(report["classic_3tier_passed"], 4)
            self.assertEqual(report["classic_3tier_accuracy_pct"], 25.0)
            self.assertEqual(report["option_reversal_consistency_pct"], 100.0)

            ids = [s["id"] for s in report["scenarios"]]
            self.assertEqual(ids, [f"PT-{i:02d}" for i in range(1, 17)])

            for filename in ("report.json", "index.html", "index.en.html"):
                p = out_dir / filename
                self.assertTrue(p.exists(), f"Missing {filename}")

            cn_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            for idx in range(1, 8):
                self.assertIn(f"{idx} / 7", cn_html)
                self.assertIn(f"{idx} / 7", en_html)
            self.assertIn("Content-Security-Policy", cn_html)
            self.assertIn("Content-Security-Policy", en_html)

    def test_default_report_dir_artifacts_exist(self) -> None:
        report = run_benchmark(DEFAULT_REPORT_DIR)
        self.assertEqual(report["ai_native_passed"], 16)
        self.assertTrue((DEFAULT_REPORT_DIR / "report.json").exists())
        self.assertTrue((DEFAULT_REPORT_DIR / "index.html").exists())
        self.assertTrue((DEFAULT_REPORT_DIR / "index.en.html").exists())


if __name__ == "__main__":
    unittest.main()
