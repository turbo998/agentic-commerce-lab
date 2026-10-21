"""Unit tests for Stage 153 16-scenario (UN-01..UN-16) 7-Card benchmark runner."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.x402_unresolved_caip2_ucp_lodging_jwt_acp_push_ap2_archive_tau2_bench import (
    run_benchmark,
    write_report_artifacts,
)


class Stage153BenchTests(unittest.TestCase):
    def test_stage153_benchmark_and_7card_artifacts(self) -> None:
        report = run_benchmark()
        summary = report["summary"]
        self.assertEqual(summary["total_scenarios"], 16)
        self.assertEqual(summary["ai_native_passed"], 16)
        self.assertEqual(summary["classic_3tier_passed"], 0)
        self.assertEqual(summary["perturbation_consistent_count"], 16)

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            write_report_artifacts(out_dir)
            self.assertTrue((out_dir / "report.json").is_file())
            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)
            self.assertIn("1 / 7", zh_html)
            self.assertIn("7 / 7", en_html)
            self.assertIn("UN-16", zh_html)
            self.assertIn("UN-16", en_html)


if __name__ == "__main__":
    unittest.main()
