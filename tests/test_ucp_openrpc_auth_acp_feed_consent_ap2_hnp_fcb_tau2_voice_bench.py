"""Unit tests for Stage 69 16-scenario (`OA-01..OA-16`) bilingual 7-Card 4:5 benchmark."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lab.ucp_openrpc_auth_acp_feed_consent_ap2_hnp_fcb_tau2_voice_bench import (
    build_stage69_report,
    write_stage69_report,
)


class Stage69BenchmarkTest(unittest.TestCase):
    def test_stage69_report_metrics_and_16_scenarios(self) -> None:
        report = build_stage69_report()
        self.assertEqual(report["stage"], 69)
        summary = report["summary"]
        self.assertEqual(summary["total_scenarios"], 16)
        self.assertEqual(summary["ai_native_passed"], 16)
        self.assertEqual(summary["ai_native_accuracy_pct"], 100.0)
        self.assertEqual(summary["classic_passed"], 4)
        self.assertEqual(summary["classic_accuracy_pct"], 25.0)
        self.assertLess(summary["ai_native_median_latency_ms"], 1.0)
        self.assertGreater(summary["speedup_factor"], 10.0)

        ids = [s["scenario_id"] for s in report["scenarios"]]
        self.assertEqual(ids, [f"OA-{i:02d}" for i in range(1, 17)])
        for s in report["scenarios"]:
            self.assertTrue(s["ai_native_correct"], msg=f"{s['scenario_id']} failed")

    def test_write_stage69_bilingual_report_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            json_path, zh_path, en_path = write_stage69_report(Path(tmp))
            data = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(data["summary"]["ai_native_passed"], 16)

            zh_html = zh_path.read_text(encoding="utf-8")
            en_html = en_path.read_text(encoding="utf-8")
            for k in range(1, 8):
                self.assertIn(f'id="card-{k}"', zh_html)
                self.assertIn(f'id="card-{k}"', en_html)
            self.assertIn("Content-Security-Policy", zh_html)
            self.assertIn("index.en.html", zh_html)
            self.assertIn("index.html", en_html)


if __name__ == "__main__":
    unittest.main()
