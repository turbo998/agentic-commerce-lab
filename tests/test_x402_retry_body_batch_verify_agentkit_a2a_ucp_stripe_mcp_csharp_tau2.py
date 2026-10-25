"""Unit tests for Stage 260 guards and Stage 261 7-Card benchmark suite."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.x402_retry_body_batch_verify_agentkit_a2a_ucp_stripe_mcp_csharp_tau2_bench import (
    build_stage261_scenarios,
    run_stage261_benchmark,
)
from lab.x402_retry_body_batch_verify_agentkit_a2a_ucp_stripe_mcp_csharp_tau2_guards import (
    STAGE260_GUARD_EVALUATORS,
    evaluate_stage260_guards,
)


class Stage260And261GuardBenchmarkTest(unittest.TestCase):
    """Verify all 16 Stage 260 guard evaluators and Stage 261 7-Card reports."""

    def test_compliant_scenarios_pass_all_16_guards(self) -> None:
        scenarios = build_stage261_scenarios()
        self.assertEqual(len(scenarios), 16)
        results = evaluate_stage260_guards(scenarios)
        for scenario, res in zip(scenarios, results):
            self.assertTrue(res.passed, msg=f"{scenario['scenario_id']} failed: {res.reason}")
            self.assertEqual(res.action, "Act automatically")
            self.assertEqual(res.http_status, 200)

    def test_adversarial_scenarios_blocked_or_routed_to_human(self) -> None:
        scenarios = build_stage261_scenarios()
        adv_inputs = [
            {"scenario_id": s["scenario_id"], "payload": s["adversarial_payload"]}
            for s in scenarios
        ]
        results = evaluate_stage260_guards(adv_inputs)
        for scenario, res in zip(scenarios, results):
            self.assertFalse(res.passed, msg=f"{scenario['scenario_id']} unexpectedly passed")
            self.assertEqual(res.action, "Send to a human")
            self.assertGreaterEqual(res.http_status, 400)

    def test_secondary_rejection_branches(self) -> None:
        r01_bytes = STAGE260_GUARD_EVALUATORS["PR-01"](
            {
                "request_body_kind": "bytes",
                "paid_retry_body_bytes_equal_initial_send": False,
            }
        )
        self.assertFalse(r01_bytes.passed)
        self.assertEqual(r01_bytes.http_status, 400)

        r02_flush = STAGE260_GUARD_EVALUATORS["PR-02"](
            {
                "refund_with_claims_sets_pending_settle": True,
                "settle_job_calls_facilitator_when_pending_settle_false": True,
                "err_nothing_to_settle_returns_empty_tx_not_error": False,
                "stop_with_flush_settles_even_when_zero_claimed": False,
            }
        )
        self.assertFalse(r02_flush.passed)
        self.assertEqual(r02_flush.http_status, 422)

        r03_ve = STAGE260_GUARD_EVALUATORS["PR-03"](
            {
                "verify_error_mapped_to_http_200_is_valid_false": True,
                "verify_response_includes_invalid_reason_and_payer": True,
                "non_verify_error_preserves_http_500": True,
                "uses_nonexistent_ve_reason_or_network_field": True,
            }
        )
        self.assertFalse(r03_ve.passed)
        self.assertEqual(r03_ve.http_status, 422)

        r05_dest = STAGE260_GUARD_EVALUATORS["PR-05"](
            {
                "server_signing": False,
                "server_submission": False,
                "destination_chain": "optimism",
            }
        )
        self.assertFalse(r05_dest.passed)
        self.assertEqual(r05_dest.http_status, 422)

        r11_confirm = STAGE260_GUARD_EVALUATORS["PR-11"](
            {
                "stripe_mcp_credential_kind": "oauth",
                "hermes_allowed_tools_is_comma_separated_string": True,
                "stripe_cli_1_51_0_and_skills_1_7_0_pinned": True,
                "current_turn_write_confirmation_matches_exact_params": False,
                "explicit_user_tos_and_feedback_consent": False,
            }
        )
        self.assertFalse(r11_confirm.passed)
        self.assertEqual(r11_confirm.http_status, 403)

        r12_dl_err = STAGE260_GUARD_EVALUATORS["PR-12"](
            {
                "downloads_staged_in_memory_before_directory_clean": True,
                "existing_skills_preserved_when_any_download_fails": True,
                "sync_download_error_count": 1,
            }
        )
        self.assertFalse(r12_dl_err.passed)
        self.assertEqual(r12_dl_err.http_status, 502)

        with self.assertRaises(ValueError):
            evaluate_stage260_guards([{"scenario_id": "PR-99", "payload": {}}])

    def test_benchmark_generates_bilingual_7_card_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            report = run_stage261_benchmark(output_dir=out_dir)
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
