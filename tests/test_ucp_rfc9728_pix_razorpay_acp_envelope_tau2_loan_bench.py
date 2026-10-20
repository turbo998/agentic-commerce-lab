"""Unit tests for Stage 57 16-scenario bilingual 7-Card 4:5 benchmark suite (`RP-01..RP-16`)."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.ucp_rfc9728_pix_razorpay_acp_envelope_tau2_loan_bench import (
    run_ucp_rfc9728_pix_razorpay_acp_envelope_tau2_loan_benchmark,
    write_ucp_rfc9728_pix_razorpay_acp_envelope_tau2_loan_report,
)


class Stage57BenchmarkTest(unittest.TestCase):
    def test_benchmark_16_scenarios_and_metrics(self) -> None:
        report = run_ucp_rfc9728_pix_razorpay_acp_envelope_tau2_loan_benchmark()
        self.assertEqual(report["total_scenarios"], 16)
        self.assertEqual(report["ai_native_passed"], 16)
        self.assertEqual(report["ai_native_pass_rate_pct"], 100.0)
        self.assertEqual(report["classic_3tier_passed"], 1)
        self.assertEqual(report["classic_3tier_pass_rate_pct"], 6.2)
        self.assertEqual(report["perturbation_stability_pct"], 100.0)
        ids = [s["scenario_id"] for s in report["scenarios"]]
        self.assertEqual(ids, [f"RP-{i:02d}" for i in range(1, 17)])

    def test_write_bilingual_7card_report_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            j_path, zh_path, en_path = write_ucp_rfc9728_pix_razorpay_acp_envelope_tau2_loan_report(Path(tmp))
            self.assertTrue(j_path.exists())
            self.assertTrue(zh_path.exists())
            self.assertTrue(en_path.exists())
            zh_html = zh_path.read_text(encoding="utf-8")
            en_html = en_path.read_text(encoding="utf-8")
            for idx in range(1, 8):
                self.assertIn(f"{idx} / 7", zh_html)
                self.assertIn(f"{idx} / 7", en_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)
            self.assertIn("RP-16", zh_html)
            self.assertIn("RP-16", en_html)


if __name__ == "__main__":
    unittest.main()
