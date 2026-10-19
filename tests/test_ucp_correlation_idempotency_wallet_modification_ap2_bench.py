"""Unit tests for Stage 46 16-Scenario Benchmark & 7-Card 4:5 Report (`CI-01`..`CI-16`)."""

from pathlib import Path
import tempfile
import unittest

from lab.ucp_correlation_idempotency_wallet_modification_ap2_bench import (
    render_7card_html,
    run_ucp_correlation_idempotency_wallet_modification_ap2_benchmark,
    write_stage46_benchmark_artifacts,
)


class TestStage46UcpCorrelationIdempotencyWalletModificationAp2Bench(unittest.TestCase):
    def test_16_scenario_matrix_and_pass_rates(self) -> None:
        summary = run_ucp_correlation_idempotency_wallet_modification_ap2_benchmark()
        self.assertEqual(summary["total_scenarios"], 16)
        self.assertEqual(summary["ai_native_passed"], 16)
        self.assertEqual(summary["ai_native_pass_rate_pct"], 100.0)
        self.assertEqual(summary["classic_3tier_passed"], 1)
        self.assertEqual(summary["classic_3tier_pass_rate_pct"], 6.2)
        self.assertEqual(summary["perturbation_consistency_pct"], 100.0)

    def test_specific_blocking_decision_codes(self) -> None:
        summary = run_ucp_correlation_idempotency_wallet_modification_ap2_benchmark()
        by_id = {s["scenario_id"]: s for s in summary["scenarios"]}
        self.assertEqual(
            by_id["CI-02"]["ai_native_decision_code"],
            "PLATFORM_REFERENCE_MUTATED_ON_UPDATE_OR_COMPLETE_BLOCKED",
        )
        self.assertEqual(
            by_id["CI-05"]["ai_native_decision_code"],
            "IDEMPOTENCY_KEY_CROSS_OPERATION_OR_TARGET_REUSE_BLOCKED",
        )
        self.assertEqual(
            by_id["CI-08"]["ai_native_decision_code"],
            "UNRECOGNIZED_OR_NORMALIZED_IDP_ISSUER_SUBJECT_TOKEN_EXFILTRATION_BLOCKED",
        )
        self.assertEqual(
            by_id["CI-11"]["ai_native_decision_code"],
            "AP2_EMPTY_MERCHANT_ID_DISPLAY_NAME_SPOOF_BLOCKED",
        )
        self.assertEqual(
            by_id["CI-14"]["ai_native_decision_code"],
            "LOOKUP_MODIFICATION_MUTATED_FENCE_OR_CLAIM_STATE_BLOCKED",
        )
        self.assertEqual(
            by_id["CI-15"]["ai_native_decision_code"],
            "CONSULTATION_DECIDE_AUTH_OR_SCOPE_FAILED_BEFORE_REPLAY",
        )
        self.assertEqual(
            by_id["CI-16"]["ai_native_decision_code"],
            "AP2_JWK_CURVE_OR_PROTECTED_ALG_MISMATCH_BLOCKED",
        )

    def test_7card_html_csp_and_artifact_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage46-bench"
            summary = write_stage46_benchmark_artifacts(out_dir)
            html = render_7card_html(summary)
            self.assertIn("default-src 'none'; style-src 'unsafe-inline'", html)
            self.assertEqual(html.count('class="card"'), 7)
            self.assertTrue((out_dir / "report.json").exists())
            self.assertTrue((out_dir / "index.html").exists())


if __name__ == "__main__":
    unittest.main()
