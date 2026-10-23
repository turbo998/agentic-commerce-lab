"""Unit test for Stage 221 16-scenario 7-Card 4:5 visual benchmark suite."""

from __future__ import annotations

import json
import unittest

from lab.ucp_tx_ready_stripe_proxy_mcp_go_rust_csharp_java_bench import (
    REPORT_DIR,
    run_benchmark,
)


class TestStage221UcpStripeMcpPolyglotBench(unittest.TestCase):
    def test_run_benchmark_generates_report_and_bilingual_7card_decks(self) -> None:
        report = run_benchmark()
        summary = report["summary"]
        self.assertEqual(report["stage"], 221)
        self.assertEqual(summary["total_scenarios"], 16)
        self.assertEqual(summary["fault_blocked"], 16)
        self.assertEqual(summary["guarded_passed"], 16)
        self.assertEqual(summary["pass_rate_pct"], 100.0)
        self.assertEqual(summary["fault_interception_rate_pct"], 100.0)
        self.assertGreater(summary["batch_16_latency_ms"], 0.0)

        report_json = REPORT_DIR / "report.json"
        zh_html = REPORT_DIR / "index.html"
        en_html = REPORT_DIR / "index.en.html"
        self.assertTrue(report_json.is_file())
        self.assertTrue(zh_html.is_file())
        self.assertTrue(en_html.is_file())

        loaded = json.loads(report_json.read_text(encoding="utf-8"))
        self.assertEqual(loaded["summary"]["guarded_passed"], 16)

        for deck_path in (zh_html, en_html):
            text = deck_path.read_text(encoding="utf-8")
            self.assertIn(
                "Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'\"",
                text,
            )
            for idx in range(1, 8):
                self.assertIn(f'id="card-{idx}"', text)


if __name__ == "__main__":
    unittest.main()
