"""Unit tests for Stage 222 deterministic guard evaluators (`PR-01` .. `PR-16`)."""

from __future__ import annotations

import unittest

from lab.mcp_inspector_registry_go_rust_csharp_java_bench import build_stage_223_scenarios
from lab.mcp_inspector_registry_go_rust_csharp_java_guards import (
    STAGE_222_PR_IDS,
    evaluate_all_stage_222_guards,
    evaluate_stage_222_guard,
)


class TestMcpInspectorRegistryGoRustCsharpJavaGuards(unittest.TestCase):
    def test_all_16_stage_222_fault_payloads_blocked(self) -> None:
        scenarios = build_stage_223_scenarios()
        self.assertEqual(len(scenarios), 16)
        for sc in scenarios:
            pr_id = sc["scenario_id"]
            res = evaluate_stage_222_guard(pr_id, sc["fault_payload"])
            self.assertFalse(res["passed"], f"{pr_id} fault payload should be blocked")
            self.assertEqual(res["action"], "block")

    def test_all_16_stage_222_patched_payloads_allowed(self) -> None:
        scenarios = build_stage_223_scenarios()
        batch_payload = {sc["scenario_id"]: sc["patched_payload"] for sc in scenarios}
        summary = evaluate_all_stage_222_guards(batch_payload)
        self.assertEqual(summary["stage"], 222)
        self.assertEqual(summary["total"], 16)
        self.assertEqual(summary["passed"], 16)
        self.assertEqual(summary["failed"], 0)
        self.assertTrue(summary["all_passed"])

    def test_stage_222_edge_cases_and_unknown_pr_id(self) -> None:
        self.assertEqual(len(STAGE_222_PR_IDS), 16)
        with self.assertRaises(ValueError):
            evaluate_stage_222_guard("PR-99", {})

        # PR-11 cross-origin 307 redirect must be blocked
        cross_origin = evaluate_stage_222_guard(
            "PR-11",
            {
                "redirect_status": 307,
                "original_url": "https://mcp.example.com/v1/mcp",
                "redirect_target_url": "https://evil.example.org/v1/mcp",
                "redirect_hops": 1,
                "redirect_followed": True,
                "tool_input_schema": {},
                "tool_arguments": {},
                "extracted_headers": {},
            },
        )
        self.assertFalse(cross_origin["passed"])
        self.assertEqual(cross_origin["reason_code"], "RUST_SDK_REDIRECT_POLICY_VIOLATION")

        # PR-16 application/problem+json with charset parameter must be accepted on 200
        problem_json_ok = evaluate_stage_222_guard(
            "PR-16",
            {
                "legacy_initialize_error": {
                    "code": -32602,
                    "message": "Unsupported protocol version",
                    "data": {"supported": ["2026-07-28"]},
                },
                "subscriptions_listen_params": {"notifications": ["resources/updated"]},
                "listen_rejected_with_invalid_params": True,
                "servlet_post_content_type": "Application/JSON; charset=utf-8",
                "servlet_http_status": 200,
                "body_read_before_content_type_check": False,
            },
        )
        self.assertTrue(problem_json_ok["passed"])


if __name__ == "__main__":
    unittest.main()
