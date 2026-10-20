"""Unit tests for Stage 73 16-scenario (`CR-01..CR-16`) bilingual 7-Card 4:5 benchmark."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.ucp_consent_return_etag_acp_affiliate_trace_ap2_haggle_solana_tau2_vpn_bench import (
    build_stage73_summary,
    write_stage73_report,
)


class TestStage73Bench(unittest.TestCase):
    def test_summary_metrics_and_scenarios(self) -> None:
        summary = build_stage73_summary()
        self.assertEqual(summary["total_scenarios"], 16)
        self.assertEqual(summary["ai_native_passed"], 16)
        self.assertEqual(summary["ai_native_accuracy_pct"], 100.0)
        self.assertEqual(summary["classic_3tier_passed"], 4)
        self.assertEqual(summary["classic_3tier_accuracy_pct"], 25.0)
        self.assertEqual(summary["perturbation_consistency_pct"], 100.0)
        self.assertEqual(
            [s["scenario_id"] for s in summary["scenarios"]],
            [f"CR-{i:02d}" for i in range(1, 17)],
        )

    def test_write_bilingual_7card_report_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            summary = write_stage73_report(out_dir)
            self.assertEqual(summary["ai_native_passed"], 16)
            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("1 / 7 · HANDS-ON", zh_html)
            self.assertIn("7 / 7 · MY TAKE", zh_html)
            self.assertIn("index.en.html", zh_html)
            self.assertIn("index.html", en_html)
            self.assertEqual(zh_html.count('<section class="card">'), 7)
            self.assertEqual(en_html.count('<section class="card">'), 7)


if __name__ == "__main__":
    unittest.main()
