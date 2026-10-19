"""Unit tests for Stage 51 16-scenario benchmark and 7-Card 4:5 visual report."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from lab.ucp_address_webhooks_quote_acp_feed_bench import (
    run_ucp_address_webhooks_quote_acp_feed_benchmark,
    write_ucp_address_webhooks_quote_acp_feed_report,
)


class Stage51AddressWebhooksQuoteACPFeedBenchTest(unittest.TestCase):
    def test_benchmark_16_scenarios_summary(self) -> None:
        report = run_ucp_address_webhooks_quote_acp_feed_benchmark()
        self.assertEqual(report["total_scenarios"], 16)
        self.assertEqual(report["ai_native_passed"], 16)
        self.assertEqual(report["ai_native_pass_rate_pct"], 100.0)
        self.assertEqual(report["classic_3tier_passed"], 1)
        self.assertEqual(report["classic_3tier_pass_rate_pct"], 6.2)
        self.assertEqual(report["perturbation_stability_pct"], 100.0)

    def test_scenario_ids_and_categories(self) -> None:
        report = run_ucp_address_webhooks_quote_acp_feed_benchmark()
        ids = [s["scenario_id"] for s in report["scenarios"]]
        self.assertEqual(ids, [f"AW-{i:02d}" for i in range(1, 17)])
        for s in report["scenarios"]:
            self.assertTrue(s["ai_native_passed"], f"Scenario failed: {s}")
            self.assertTrue(s["perturbation_stable"], f"Scenario unstable: {s}")

    def test_write_7card_report_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            json_path, html_path = write_ucp_address_webhooks_quote_acp_feed_report(Path(tmp))
            self.assertTrue(json_path.exists())
            self.assertTrue(html_path.exists())
            parsed = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(parsed["benchmark_id"], "agentic-commerce-ucp-address-webhooks-quote-acp-feed-bench")
            html_text = html_path.read_text(encoding="utf-8")
            self.assertIn("Content-Security-Policy", html_text)
            for idx in range(1, 8):
                self.assertIn(f"{idx} / 7 ·", html_text)


if __name__ == "__main__":
    unittest.main()
