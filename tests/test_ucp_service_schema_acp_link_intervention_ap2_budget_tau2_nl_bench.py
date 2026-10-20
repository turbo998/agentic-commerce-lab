"""Unit tests for Stage 65 bilingual 16-scenario 7-Card 4:5 benchmark suite."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.ucp_service_schema_acp_link_intervention_ap2_budget_tau2_nl_bench import (
    run_stage65_benchmark_suite,
    write_stage65_report_files,
)


class Stage65BenchmarkSuiteTests(unittest.TestCase):
    def test_stage65_scenarios_accuracy_and_stability(self) -> None:
        report = run_stage65_benchmark_suite()
        self.assertEqual(
            report["benchmark_id"],
            "agentic-commerce-ucp-service-schema-acp-link-intervention-ap2-budget-tau2-nl-bench",
        )
        self.assertEqual(report["stage"], "Stage 65")
        self.assertEqual(report["total_scenarios"], 16)
        self.assertEqual(report["ai_native_passed"], 16)
        self.assertEqual(report["ai_native_accuracy_pct"], 100.0)
        self.assertEqual(report["classic_3tier_passed"], 4)
        self.assertEqual(report["classic_3tier_accuracy_pct"], 25.0)
        self.assertEqual(report["perturbation_stable_count"], 16)
        self.assertEqual(report["perturbation_stability_pct"], 100.0)
        self.assertEqual(len(report["scenarios"]), 16)
        self.assertEqual(report["scenarios"][0]["scenario_id"], "SL-01")
        self.assertEqual(report["scenarios"][-1]["scenario_id"], "SL-16")

    def test_stage65_bilingual_report_files_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage65-report"
            report = write_stage65_report_files(out_dir)
            json_path = out_dir / "report.json"
            zh_path = out_dir / "index.html"
            en_path = out_dir / "index.en.html"
            self.assertTrue(json_path.is_file())
            self.assertTrue(zh_path.is_file())
            self.assertTrue(en_path.is_file())

            zh_html = zh_path.read_text(encoding="utf-8")
            en_html = en_path.read_text(encoding="utf-8")
            for idx in range(1, 8):
                self.assertIn(f"{idx} / 7", zh_html)
                self.assertIn(f"{idx} / 7", en_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", en_html)
            self.assertIn("index.en.html", zh_html)
            self.assertIn("index.html", en_html)
            self.assertEqual(len(report["report_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
