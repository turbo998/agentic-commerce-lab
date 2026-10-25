"""Unit tests for Stage 229 16-scenario 7-Card 4:5 visual benchmark runner."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from lab.visa_tap_stripe_acp_ucp_ap2_x402_agentkit_mcp_tau2_bench import (
    run_stage229_benchmark,
)


class TestStage229VisaTapStripeAcpUcpAp2X402AgentKitMcpTau2Bench(unittest.TestCase):
    def test_stage229_benchmark_generates_7card_bilingual_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            res = run_stage229_benchmark(tmp)
            summary = res["summary"]
            self.assertEqual(summary["total_scenarios"], 16)
            self.assertEqual(summary["ai_native_passed"], 16)
            self.assertEqual(summary["classic_3tier_passed"], 0)
            self.assertEqual(summary["perturbed_consistent"], 16)

            zh_html = Path(res["report_html_zh"]).read_text(encoding="utf-8")
            en_html = Path(res["report_html_en"]).read_text(encoding="utf-8")
            report_data = json.loads(Path(res["report_json"]).read_text(encoding="utf-8"))

            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", en_html)
            self.assertEqual(zh_html.count('<section class="card">'), 7)
            self.assertEqual(en_html.count('<section class="card">'), 7)
            self.assertEqual(report_data["ai_native_pass_rate_pct"], 100.0)

    def test_unknown_scenario_raises_key_error(self) -> None:
        from lab.visa_tap_stripe_acp_ucp_ap2_x402_agentkit_mcp_tau2_guards import (
            evaluate_stage228_scenario,
        )

        with self.assertRaises(KeyError):
            evaluate_stage228_scenario("PR-99", {})


if __name__ == "__main__":
    unittest.main()
