"""Unit tests for Stage 131 16-scenario bilingual 7-Card benchmark."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.x402_svm_batch_mcp_raw_ucp_status_constraints_stripe_ua_tau2_infra_bench import (
    run_benchmark,
)


class Stage131BenchTest(unittest.TestCase):
    def test_stage131_benchmark_all_16_scenarios_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            report = run_benchmark(output_dir=out_dir)
            self.assertEqual(report["summary"]["total"], 16)
            self.assertEqual(report["summary"]["passed"], 16)
            self.assertEqual(report["summary"]["pass_rate_pct"], 100.0)
            self.assertTrue((out_dir / "report.json").exists())
            self.assertTrue((out_dir / "index.html").exists())
            self.assertTrue((out_dir / "index.en.html").exists())
            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            for idx in range(1, 8):
                self.assertIn(f'id="card-{idx}"', zh_html)
                self.assertIn(f'id="card-{idx}"', en_html)


if __name__ == "__main__":
    unittest.main()
