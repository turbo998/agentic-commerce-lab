"""Unit tests for Stage 254 guards & Stage 255 benchmark (255-Stage Milestone!)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lab.x402_svm_recovery_agentkit_glee_a2a_card_ucp_stripe_mcp_sdk_tau2_bench import (
    build_stage255_scenarios,
    run_stage255_benchmark,
)
from lab.x402_svm_recovery_agentkit_glee_a2a_card_ucp_stripe_mcp_sdk_tau2_guards import (
    STAGE254_GUARD_EVALUATORS,
    evaluate_stage254_guards,
)


class TestStage254GuardsAndStage255Benchmark(unittest.TestCase):
    def test_all_16_compliant_payloads_pass(self) -> None:
        scenarios = build_stage255_scenarios()
        self.assertEqual(len(scenarios), 16)
        payload_map = {item["id"]: item["compliant_payload"] for item in scenarios}
        results = evaluate_stage254_guards(payload_map)
        for pr_id, res in results.items():
            self.assertTrue(res.passed, f"{pr_id} compliant payload failed: {res.reason}")

    def test_all_16_adversarial_payloads_blocked_with_expected_action(self) -> None:
        scenarios = build_stage255_scenarios()
        for item in scenarios:
            pr_id = item["id"]
            res = STAGE254_GUARD_EVALUATORS[pr_id](item["adversarial_payload"])
            self.assertFalse(res.passed, f"{pr_id} adversarial payload should be blocked")
            self.assertEqual(res.action, item["expected_action"])

    def test_secondary_rejection_branches(self) -> None:
        # PR-01 secondary branch: read_err=False but lookup error not returned
        res01 = STAGE254_GUARD_EVALUATORS["PR-01"](
            {
                "pending_store_read_error": False,
                "go_lookup_error_returned_before_settlement": False,
                "ts_duplicate_entry_released_only_if_owned": True,
                "existing_pending_records_preserved": True,
                "settlement_allowed_on_unknown_pending_state": False,
            }
        )
        self.assertFalse(res01.passed)
        self.assertEqual(res01.action, "REJECT_STALE_DUPLICATE_LOCK_OR_UNRETURNED_LOOKUP_ERR")

        # PR-02 secondary branch: matching program IDs but shared_mutable_program_state=True
        res02 = STAGE254_GUARD_EVALUATORS["PR-02"](
            {
                "mint_token_program": "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb",
                "source_ata_token_program": "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb",
                "dest_ata_token_program": "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb",
                "transfer_checked_token_program": "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb",
                "shared_mutable_program_state": True,
            }
        )
        self.assertFalse(res02.passed)
        self.assertEqual(res02.action, "REJECT_SHARED_MUTABLE_TOKEN_PROGRAM_STATE")

        # PR-04 secondary branch: hook denied but signature still created
        res04 = STAGE254_GUARD_EVALUATORS["PR-04"](
            {
                "tx_sent_hash_present": False,
                "receipt_lookup_failed": False,
                "reported_transfer_state": "SUCCESS",
                "tx_hash_retained_in_response": True,
                "pre_payment_check_allowed": False,
                "signature_created_after_hook_denial": True,
            }
        )
        self.assertFalse(res04.passed)
        self.assertEqual(res04.action, "BLOCK_X402_SIGNING_AFTER_PRE_PAYMENT_HOOK_DENIAL")

        # PR-10 secondary branch: deprecated Stripe key past 2026-10-31
        res10 = STAGE254_GUARD_EVALUATORS["PR-10"](
            {
                "manual_synced_skill_dir_edit_detected": False,
                "target_dir_cleaned_before_skills_sync": True,
                "claude_plugin_test_path_prefix": "tests/",
                "stripe_credential_kind": "sk_live_legacy",
                "evaluation_date": "2026-10-31",
            }
        )
        self.assertFalse(res10.passed)
        self.assertEqual(res10.action, "BLOCK_DEPRECATED_STRIPE_KEY_PAST_2026_10_31")

    def test_benchmark_and_7card_report_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "stage255-report"
            report = run_stage255_benchmark(output_dir=out_dir)
            self.assertEqual(report["total_scenarios"], 16)
            self.assertEqual(report["ai_native_passed"], 16)
            self.assertEqual(report["ai_native_rate_pct"], 100.0)
            self.assertEqual(report["classic_passed"], 2)
            self.assertEqual(report["classic_rate_pct"], 12.5)
            self.assertEqual(report["perturbation_invariant_count"], 16)

            json_path = out_dir / "report.json"
            zh_path = out_dir / "index.html"
            en_path = out_dir / "index.en.html"
            self.assertTrue(json_path.exists())
            self.assertTrue(zh_path.exists())
            self.assertTrue(en_path.exists())

            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["milestone"], "255-Stage Milestone!")

            for html_file in (zh_path, en_path):
                content = html_file.read_text(encoding="utf-8")
                self.assertIn("default-src 'none'; style-src 'unsafe-inline'", content)
                for idx in range(1, 8):
                    self.assertIn(f'id="card-{idx}"', content)


if __name__ == "__main__":
    unittest.main()
