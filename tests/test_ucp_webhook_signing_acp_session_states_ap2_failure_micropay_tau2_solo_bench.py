"""Unit tests for Stage 71 16-scenario (`WS-01..WS-16`) bilingual 7-Card 4:5 benchmark report."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.ucp_webhook_signing_acp_session_states_ap2_failure_micropay_tau2_solo_bench import (
    build_stage71_summary,
    write_stage71_report,
)


class TestStage71WebhookSigningAcpSessionStatesAp2FailureMicropayTau2SoloBench(unittest.TestCase):
    def test_summary_metrics_and_16_scenarios(self) -> None:
        summary = build_stage71_summary()
        self.assertEqual(summary["total_scenarios"], 16)
        self.assertEqual(summary["ai_native_passed"], 16)
        self.assertEqual(summary["ai_native_accuracy_pct"], 100.0)
        self.assertEqual(summary["classic_3tier_passed"], 4)
        self.assertEqual(summary["classic_3tier_accuracy_pct"], 25.0)
        self.assertEqual(summary["perturbation_consistency_pct"], 100.0)
        ids = [s["scenario_id"] for s in summary["scenarios"]]
        self.assertEqual(ids, [f"WS-{i:02d}" for i in range(1, 17)])

    def test_write_bilingual_7card_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            summary = write_stage71_report(out_dir)
            self.assertEqual(summary["ai_native_passed"], 16)
            report_json = out_dir / "report.json"
            zh_html = out_dir / "index.html"
            en_html = out_dir / "index.en.html"
            self.assertTrue(report_json.exists())
            self.assertTrue(zh_html.exists())
            self.assertTrue(en_html.exists())

            zh_text = zh_html.read_text(encoding="utf-8")
            en_text = en_html.read_text(encoding="utf-8")
            for idx in range(1, 8):
                self.assertIn(f"{idx} / 7", zh_text)
                self.assertIn(f"{idx} / 7", en_text)
            self.assertIn("index.en.html", zh_text)
            self.assertIn("index.html", en_text)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_text)


if __name__ == "__main__":
    unittest.main()
