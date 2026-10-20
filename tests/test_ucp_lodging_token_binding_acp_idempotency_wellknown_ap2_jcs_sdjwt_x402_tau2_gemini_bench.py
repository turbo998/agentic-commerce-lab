"""Unit tests for Stage 75 16-scenario (LB-01..LB-16) bilingual 7-Card benchmark suite."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.ucp_lodging_token_binding_acp_idempotency_wellknown_ap2_jcs_sdjwt_x402_tau2_gemini_bench import (
    run_benchmark,
    write_report,
)


class TestStage75Bench(unittest.TestCase):
    def test_summary_metrics_and_scenarios(self) -> None:
        report = run_benchmark()
        summary = report["summary"]
        self.assertEqual(summary["total_scenarios"], 16)
        self.assertEqual(summary["ai_native_passed"], 16)
        self.assertEqual(summary["ai_native_accuracy_pct"], 100.0)
        self.assertEqual(summary["classic_3tier_passed"], 4)
        self.assertEqual(summary["classic_3tier_accuracy_pct"], 25.0)
        self.assertEqual(summary["perturbation_consistency_pct"], 100.0)
        self.assertEqual(
            [s["scenario_id"] for s in report["scenarios"]],
            [f"LB-{i:02d}" for i in range(1, 17)],
        )

    def test_write_bilingual_7card_report_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage75"
            write_report(out_dir)
            cn_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            for marker in ("1 / 7", "2 / 7", "3 / 7", "4 / 7", "5 / 7", "6 / 7", "7 / 7", "LB-01", "LB-16"):
                self.assertIn(marker, cn_html)
                self.assertIn(marker, en_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", cn_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", en_html)


if __name__ == "__main__":
    unittest.main()
