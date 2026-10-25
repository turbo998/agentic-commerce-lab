"""Unit tests for Stage 256 guards and Stage 257 16-scenario 7-Card benchmark."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.x402_v1_filter_agentkit_preflight_a2a_sdk_ucp_idempotency_mcp_sdk_tau2_bench import (
    build_scenarios,
    run_benchmark,
)
from lab.x402_v1_filter_agentkit_preflight_a2a_sdk_ucp_idempotency_mcp_sdk_tau2_guards import (
    STAGE256_GUARD_EVALUATORS,
    evaluate_stage256_guards,
)


class TestStage256And257GuardsAndBench(unittest.TestCase):
    def test_all_16_compliant_scenarios_pass(self) -> None:
        scenarios = {item["id"]: item["compliant"] for item in build_scenarios()}
        results = evaluate_stage256_guards(scenarios)
        self.assertEqual(len(results), 16)
        for gid, res in results.items():
            self.assertTrue(res["allowed"], f"{gid} compliant scenario should be allowed: {res}")

    def test_all_16_adversarial_scenarios_blocked(self) -> None:
        scenarios = {item["id"]: item["adversarial"] for item in build_scenarios()}
        results = evaluate_stage256_guards(scenarios)
        self.assertEqual(len(results), 16)
        for gid, res in results.items():
            self.assertFalse(res["allowed"], f"{gid} adversarial scenario should be blocked: {res}")

    def test_secondary_rejection_branches(self) -> None:
        r1 = STAGE256_GUARD_EVALUATORS["PR-01"](
            {
                "configured_network_patterns": ["eip155:84532"],
                "registered_v1_networks": ["base-sepolia"],
                "payload_x402_version": 1,
                "requirements_parser_version": 1,
                "invalid_requirements_http_status": 400,
                "payer_sanctioned": True,
                "payer_screen_http_status": 200,
            }
        )
        self.assertFalse(r1["allowed"])
        self.assertEqual(r1["decision_code"], "X402_SANCTIONED_PAYER_MISSING_HTTP_451_REJECTED")

        r8 = STAGE256_GUARD_EVALUATORS["PR-08"](
            {
                "concurrent_identical_500_count": 0,
                "differing_body_collision_status": 409,
                "rfc9421_ecdsa_p256_section": "3.3.4",
                "line_item_quantity": 2,
                "merchant_fixture_currency": "EUR",
                "conflict_test_currency": "EUR",
            }
        )
        self.assertFalse(r8["allowed"])
        self.assertEqual(r8["decision_code"], "UCP_CONFORMANCE_SAME_CURRENCY_NOOP_CONFLICT_TEST_REJECTED")

        r12 = STAGE256_GUARD_EVALUATORS["PR-12"](
            {
                "jsonrpc_error_code": -32602,
                "missing_required_meta": False,
                "http_status": 200,
                "roots_list_next_cursor": "",
                "requested_next_page": True,
            }
        )
        self.assertFalse(r12["allowed"])
        self.assertEqual(r12["decision_code"], "MCP_JAVA_SDK_EMPTY_NEXT_CURSOR_INFINITE_PAGINATION_REJECTED")

    def test_benchmark_and_7card_reports_generated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage257-bench"
            rep = run_benchmark(out_dir)
            self.assertEqual(rep["total_scenarios"], 16)
            self.assertEqual(rep["ai_native_passed"], 16)
            self.assertEqual(rep["classic_3tier_passed"], 2)
            self.assertEqual(rep["perturbation_invariant_count"], 16)
            zh_html = (out_dir / "index.html").read_text(encoding="utf-8")
            en_html = (out_dir / "index.en.html").read_text(encoding="utf-8")
            for html_doc in (zh_html, en_html):
                self.assertIn("default-src 'none'; style-src 'unsafe-inline'", html_doc)
                for idx in range(1, 8):
                    self.assertIn(f'id="card-{idx}"', html_doc)


if __name__ == "__main__":
    unittest.main()
