"""Unit tests for Stage 258 guards and Stage 259 7-Card benchmark suite."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.x402_facilitator_agentkit_firewall_a2a_compat_ucp_cart_mcp_sdk_tau2_bench import (
    build_stage259_scenarios,
    run_stage259_benchmark,
)
from lab.x402_facilitator_agentkit_firewall_a2a_compat_ucp_cart_mcp_sdk_tau2_guards import (
    STAGE258_GUARD_EVALUATORS,
    evaluate_stage258_guards,
)


class Stage258And259GuardBenchmarkTest(unittest.TestCase):
    """Verify all 16 Stage 258 guard evaluators and Stage 259 7-Card reports."""

    def test_compliant_scenarios_pass_all_16_guards(self) -> None:
        scenarios = build_stage259_scenarios()
        self.assertEqual(len(scenarios), 16)
        results = evaluate_stage258_guards(scenarios)
        for scenario, res in zip(scenarios, results):
            self.assertTrue(res.passed, msg=f"{scenario['scenario_id']} failed: {res.reason}")
            self.assertEqual(res.action, "Act automatically")
            self.assertEqual(res.http_status, 200)

    def test_adversarial_scenarios_blocked_or_routed_to_human(self) -> None:
        scenarios = build_stage259_scenarios()
        adv_inputs = [
            {"scenario_id": s["scenario_id"], "payload": s["adversarial_payload"]}
            for s in scenarios
        ]
        results = evaluate_stage258_guards(adv_inputs)
        for scenario, res in zip(scenarios, results):
            self.assertFalse(res.passed, msg=f"{scenario['scenario_id']} unexpectedly passed")
            self.assertEqual(res.action, "Send to a human")
            self.assertGreaterEqual(res.http_status, 400)

    def test_secondary_rejection_branches(self) -> None:
        r01_400 = STAGE258_GUARD_EVALUATORS["PR-01"](
            {
                "payment_payload_is_object": False,
                "registered_scheme_and_network": False,
                "invalid_facilitator_request_http_status": 400,
            }
        )
        self.assertTrue(r01_400.passed)
        self.assertEqual(r01_400.http_status, 400)

        r01_sponsor = STAGE258_GUARD_EVALUATORS["PR-01"](
            {
                "payment_payload_is_object": True,
                "registered_scheme_and_network": True,
                "gas_sponsor_advertised": True,
                "chain_reader_rpc_configured": False,
                "warned_missing_rpc_once": False,
            }
        )
        self.assertFalse(r01_sponsor.passed)
        self.assertEqual(r01_sponsor.http_status, 422)

        r01_remit = STAGE258_GUARD_EVALUATORS["PR-01"](
            {
                "payment_payload_is_object": True,
                "registered_scheme_and_network": True,
                "gas_sponsor_advertised": False,
                "remitbot_pre_settlement_decision": "Hold",
            }
        )
        self.assertFalse(r01_remit.passed)
        self.assertEqual(r01_remit.http_status, 403)

        r02_agorean = STAGE258_GUARD_EVALUATORS["PR-02"](
            {
                "automaton_firewall_simulated": True,
                "automaton_firewall_verdict": "ALLOW",
                "agorean_endpoint_reviewed": False,
            }
        )
        self.assertFalse(r02_agorean.passed)
        self.assertEqual(r02_agorean.http_status, 409)

        r09_proxy = STAGE258_GUARD_EVALUATORS["PR-09"](
            {
                "stripe_credential_kind": "rk_live",
                "local_proxy_preserves_remote_tool_metadata": False,
            }
        )
        self.assertFalse(r09_proxy.passed)
        self.assertEqual(r09_proxy.http_status, 403)

        with self.assertRaises(ValueError):
            evaluate_stage258_guards([{"scenario_id": "PR-99", "payload": {}}])

    def test_benchmark_generates_bilingual_7_card_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            report = run_stage259_benchmark(output_dir=out_dir)
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["ai_native_passed"], 16)
            self.assertEqual(report["classic_3tier_passed"], 2)
            self.assertEqual(report["perturbation_invariant_count"], 16)

            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", zh_html)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", en_html)
            for idx in range(1, 8):
                self.assertIn(f'id="card-{idx}"', zh_html)
                self.assertIn(f'id="card-{idx}"', en_html)


if __name__ == "__main__":
    unittest.main()
