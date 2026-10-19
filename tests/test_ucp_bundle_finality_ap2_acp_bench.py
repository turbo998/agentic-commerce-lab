"""Unit tests for Stage 43 (`lab/ucp_bundle_finality_ap2_acp_bench.py`)."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lab.ucp_bundle_finality_ap2_acp_bench import (
    render_ucp_bundle_finality_ap2_acp_html,
    run_ucp_bundle_finality_ap2_acp_benchmark,
    write_ucp_bundle_finality_ap2_acp_report,
)


class TestStage43UcpBundleFinalityAp2AcpBench(unittest.TestCase):
    def test_benchmark_runs_16_scenarios_with_100pct_ai_native_pass_rate(self) -> None:
        summary = run_ucp_bundle_finality_ap2_acp_benchmark()
        self.assertEqual(summary["total_scenarios"], 16)
        self.assertEqual(summary["ai_native_passed"], 16)
        self.assertEqual(summary["ai_native_pass_rate_pct"], 100.0)
        self.assertEqual(summary["classic_3tier_passed"], 1)
        self.assertEqual(summary["classic_3tier_pass_rate_pct"], 6.2)
        self.assertEqual(summary["perturbation_consistency_pct"], 100.0)

    def test_seven_card_html_contains_all_required_cards_and_csp(self) -> None:
        summary = run_ucp_bundle_finality_ap2_acp_benchmark()
        html_out = render_ucp_bundle_finality_ap2_acp_html(summary)
        self.assertIn("default-src 'none'; style-src 'unsafe-inline'", html_out)
        for idx in range(1, 8):
            self.assertIn(f"{idx} / 7 ·", html_out)
        self.assertIn("BF-01", html_out)
        self.assertIn("BF-16", html_out)

    def test_write_report_persists_json_and_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage43-report"
            summary = write_ucp_bundle_finality_ap2_acp_report(out_dir)
            self.assertTrue((out_dir / "report.json").exists())
            self.assertTrue((out_dir / "index.html").exists())
            self.assertEqual(summary["ai_native_passed"], 16)


if __name__ == "__main__":
    unittest.main()
