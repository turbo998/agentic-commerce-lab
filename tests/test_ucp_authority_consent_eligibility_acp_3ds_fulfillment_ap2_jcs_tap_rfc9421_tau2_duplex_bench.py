"""Unit tests for Stage 81 16-scenario bilingual 7-Card 4:5 benchmark suite."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.ucp_authority_consent_eligibility_acp_3ds_fulfillment_ap2_jcs_tap_rfc9421_tau2_duplex_bench import (
    run_stage81_benchmark,
)


class TestStage81AuthorityConsent3dsJcsTapTau2DuplexBench(unittest.TestCase):
    def test_stage81_benchmark_16_scenarios_and_bilingual_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            report = run_stage81_benchmark(tmpdir)
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["ai_native_passed"], 16)
            self.assertEqual(report["ai_native_accuracy_pct"], 100.0)
            self.assertEqual(report["classic_3tier_passed"], 4)
            self.assertEqual(report["classic_3tier_accuracy_pct"], 25.0)
            self.assertEqual(report["option_reversal_consistency_pct"], 100.0)

            out_dir = Path(tmpdir)
            report_json = out_dir / "report.json"
            html_cn = out_dir / "index.html"
            html_en = out_dir / "index.en.html"
            self.assertTrue(report_json.exists())
            self.assertTrue(html_cn.exists())
            self.assertTrue(html_en.exists())

            cn_text = html_cn.read_text(encoding="utf-8")
            en_text = html_en.read_text(encoding="utf-8")
            for k in range(1, 8):
                self.assertIn(f"{k} / 7", cn_text)
                self.assertIn(f"{k} / 7", en_text)
            self.assertIn("AC-01", cn_text)
            self.assertIn("AC-16", en_text)
            self.assertIn("Content-Security-Policy", cn_text)
            self.assertIn("Content-Security-Policy", en_text)

    def test_stage81_scenario_codes_unique_and_complete(self) -> None:
        report = run_stage81_benchmark(None)
        ids = [s["scenario_id"] for s in report["scenarios"]]
        self.assertEqual(ids, [f"AC-{i:02d}" for i in range(1, 17)])
        for s in report["scenarios"]:
            self.assertTrue(s["ai_native_passed"], f"Scenario failed: {s}")
            self.assertTrue(s["option_reversal_consistent"], f"Reversal drift: {s}")


if __name__ == "__main__":
    unittest.main()
