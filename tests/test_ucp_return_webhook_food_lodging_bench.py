"""Unit tests for Stage 40 UCP Return Policy, Webhooks, Subscriptions, Food & Lodging 16-scenario benchmark."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.ucp_return_webhook_food_lodging_bench import (
    render_ucp_return_webhook_food_lodging_html,
    run_ucp_return_webhook_food_lodging_benchmark,
    write_ucp_return_webhook_food_lodging_report,
)


class TestUCPReturnWebhookFoodLodgingBench(unittest.TestCase):
    def test_benchmark_runs_16_scenarios_with_100_pct_ai_native_pass(self) -> None:
        summary = run_ucp_return_webhook_food_lodging_benchmark()
        self.assertEqual(summary["total_scenarios"], 16)
        self.assertEqual(summary["ai_native_passed"], 16)
        self.assertEqual(summary["ai_native_pass_rate_pct"], 100.0)
        self.assertEqual(summary["classic_3tier_passed"], 1)
        self.assertEqual(summary["classic_3tier_pass_rate_pct"], 6.2)

    def test_html_report_is_self_contained_7_card_deck(self) -> None:
        summary = run_ucp_return_webhook_food_lodging_benchmark()
        html_doc = render_ucp_return_webhook_food_lodging_html(summary)
        self.assertIn("default-src 'none'; style-src 'unsafe-inline'", html_doc)
        for idx in range(1, 8):
            self.assertIn(f"{idx} / 7 ·", html_doc)

    def test_write_report_creates_json_and_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "ucp-return-webhook-food-lodging-bench"
            summary = write_ucp_return_webhook_food_lodging_report(out_dir)
            self.assertTrue((out_dir / "report.json").exists())
            self.assertTrue((out_dir / "index.html").exists())
            self.assertEqual(summary["ai_native_passed"], 16)


if __name__ == "__main__":
    unittest.main()
