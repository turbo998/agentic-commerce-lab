"""Unit tests for Stage 199 16-scenario (`GI-01..GI-16`) 7-Card 4:5 benchmark suite."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.x402_go_v2_caip2_402_body_bazaar_method_ucp_anyof_mcp_tasks_stream_interceptors_bench import (
    run_benchmark,
)


class Stage199BenchmarkTest(unittest.TestCase):
    def test_benchmark_all_16_scenarios_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            summary = run_benchmark(output_dir=Path(tmp))
            report = summary["report"]
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["ai_native_passed"], 16)
            self.assertEqual(report["ai_native_pass_rate"], 1.0)
            self.assertEqual(report["classic_3tier_passed"], 0)
            self.assertEqual(report["perturbation_consistent"], 16)

            zh_html = Path(summary["html_zh_path"]).read_text(encoding="utf-8")
            en_html = Path(summary["html_en_path"]).read_text(encoding="utf-8")
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", en_html)
            self.assertIn("GI-01", zh_html)
            self.assertIn("GI-16", en_html)

    def test_default_report_artifacts_generated(self) -> None:
        summary = run_benchmark()
        self.assertTrue(Path(summary["json_path"]).is_file())
        self.assertTrue(Path(summary["html_zh_path"]).is_file())
        self.assertTrue(Path(summary["html_en_path"]).is_file())


if __name__ == "__main__":
    unittest.main()
