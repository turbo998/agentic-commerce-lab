"""Unit tests for Stage 55 Bilingual 16-Scenario Benchmark & 7-Card 4:5 Report."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from lab.ucp_schema_acp_drift_ap2_aud_tau2_intake_bench import (
    run_ucp_schema_acp_drift_ap2_aud_tau2_intake_benchmark,
    write_ucp_schema_acp_drift_ap2_aud_tau2_intake_report,
)


class TestUcpSchemaAcpDriftAp2AudTau2IntakeBench(unittest.TestCase):
    def test_benchmark_16_scenarios_all_pass(self) -> None:
        report = run_ucp_schema_acp_drift_ap2_aud_tau2_intake_benchmark()
        self.assertEqual(report["total_scenarios"], 16)
        self.assertEqual(report["ai_native_passed"], 16)
        self.assertEqual(report["ai_native_pass_rate_pct"], 100.0)
        self.assertEqual(report["classic_3tier_passed"], 1)
        self.assertEqual(report["classic_3tier_pass_rate_pct"], 6.2)
        self.assertEqual(report["perturbation_stability_pct"], 100.0)
        self.assertEqual(report["languages"], ["zh-CN", "en"])

        scenario_ids = [s["scenario_id"] for s in report["scenarios"]]
        self.assertEqual(scenario_ids, [f"SD-{i:02d}" for i in range(1, 17)])

    def test_write_bilingual_7card_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage55-report"
            summary = write_ucp_schema_acp_drift_ap2_aud_tau2_intake_report(out_dir)
            self.assertEqual(summary["ai_native_passed"], 16)

            report_json = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(report_json["benchmark_version"], "2026-10-20-stage55")

            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")

            self.assertIn("Content-Security-Policy", zh_html)
            self.assertIn("index.en.html", zh_html)
            self.assertIn("1 / 7", zh_html)
            self.assertIn("7 / 7", zh_html)

            self.assertIn("Content-Security-Policy", en_html)
            self.assertIn("index.html", en_html)
            self.assertIn("1 / 7", en_html)
            self.assertIn("7 / 7", en_html)


if __name__ == "__main__":
    unittest.main()
