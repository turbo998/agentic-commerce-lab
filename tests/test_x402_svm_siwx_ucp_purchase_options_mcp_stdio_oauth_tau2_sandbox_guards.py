"""Unit tests for Stage 242 deterministic guards (PR-01..PR-16)."""

from __future__ import annotations

import unittest

from lab.x402_svm_siwx_ucp_purchase_options_mcp_stdio_oauth_tau2_sandbox_bench import (
    get_scenarios,
)
from lab.x402_svm_siwx_ucp_purchase_options_mcp_stdio_oauth_tau2_sandbox_guards import (
    evaluate_mcp_py_sse_headers_uri_surrogateescape_and_skills_cache_guard,
    evaluate_tau2_knowledge_sandbox_and_voice_canonical_reload_guard,
    evaluate_ucp_conformance_corpus_mcp_complete_and_self_hosting_guard,
    evaluate_ucp_order_snapshot_and_catalog_purpose_guard,
    evaluate_ucp_purchase_options_and_food_checkout_guard,
    evaluate_x402_evm_permit2_rpc_failure_disambiguation_guard,
    evaluate_x402_recovery_extension_fail_closed_guard,
    evaluate_x402_svm_batch_post_commit_completion_guard,
)


class TestStage242Guards(unittest.TestCase):
    def test_all_16_guards_pass_valid_and_reject_attack_payloads(self) -> None:
        scenarios = get_scenarios()
        self.assertEqual(len(scenarios), 16)
        for sc in scenarios:
            evaluator = sc["evaluator"]
            pass_res = evaluator(sc["passing_payload"])
            self.assertTrue(pass_res.passed, f"{sc['id']} should pass valid payload")
            self.assertEqual(pass_res.action, "Act automatically")

            atk_res = evaluator(sc["attack_payload"])
            self.assertFalse(atk_res.passed, f"{sc['id']} should reject attack payload")
            self.assertIn("REJECT:", atk_res.reason)

    def test_confirm_vs_human_escalation_branches(self) -> None:
        # PR-01 un-committed channel without premature completion -> Confirm
        r1 = evaluate_x402_svm_batch_post_commit_completion_guard(
            {
                "channel_charge_committed": False,
                "inside_channel_update_callback": False,
                "operations_marked_complete": False,
            }
        )
        self.assertFalse(r1.passed)
        self.assertEqual(r1.action, "Confirm")

        # PR-02 non-confirmed settlement with allow_free_replay=False -> Confirm
        r2 = evaluate_x402_recovery_extension_fail_closed_guard(
            {
                "settlement_status": "pending",
                "request_hash": "h1",
                "expected_request_hash": "h1",
                "response_hash": "h2",
                "allow_free_replay": False,
            }
        )
        self.assertFalse(r2.passed)
        self.assertEqual(r2.action, "Confirm")

        # PR-03 RPC failure reported properly as invalid_permit2_failed_to_verify_signature -> Confirm
        r3 = evaluate_x402_evm_permit2_rpc_failure_disambiguation_guard(
            {
                "rpc_transport_error": True,
                "reported_error_code": "invalid_permit2_failed_to_verify_signature",
                "signature_valid": False,
            }
        )
        self.assertFalse(r3.passed)
        self.assertEqual(r3.action, "Confirm")

        # PR-07 catalog search purpose without reference_ids -> Confirm
        r7 = evaluate_ucp_order_snapshot_and_catalog_purpose_guard(
            {
                "order_directional_annotations": [],
                "catalog_search_purpose": "recommendation",
                "catalog_reference_ids": [],
            }
        )
        self.assertFalse(r7.passed)
        self.assertEqual(r7.action, "Confirm")

        # PR-08 food fulfillment invalid slot -> Confirm
        r8 = evaluate_ucp_purchase_options_and_food_checkout_guard(
            {
                "advertised_purchase_option_ids": ["opt_1"],
                "selected_purchase_option_id": "opt_1",
                "order_line_purchase_option_id": "opt_1",
                "food_fulfillment_active": True,
                "food_fulfillment_slot_valid": False,
            }
        )
        self.assertFalse(r8.passed)
        self.assertEqual(r8.action, "Confirm")

        # PR-10 unvalidated conformance corpus -> Confirm
        r10 = evaluate_ucp_conformance_corpus_mcp_complete_and_self_hosting_guard(
            {
                "conformance_corpus_validated": False,
                "mcp_complete_checkout_declares_extensions": True,
                "vendor_extension_in_core_ucp_namespace": False,
            }
        )
        self.assertFalse(r10.passed)
        self.assertEqual(r10.action, "Confirm")

        # PR-14 pre-2026-07-28 cache fields -> Confirm
        r14 = evaluate_mcp_py_sse_headers_uri_surrogateescape_and_skills_cache_guard(
            {
                "shared_mutable_sse_headers": False,
                "non_utf8_uri_corrupted_to_fffd": False,
                "protocol_version": "2025-11-25",
                "sent_directory_cache_fields": True,
            }
        )
        self.assertFalse(r14.passed)
        self.assertEqual(r14.action, "Confirm")

        # PR-16 voice-v1 canonical reload false -> Confirm
        r16 = evaluate_tau2_knowledge_sandbox_and_voice_canonical_reload_guard(
            {
                "sandbox_inherited_parent_env": False,
                "sandbox_read_outside_knowledge_base": False,
                "voice_v1_canonical_tasks_preserved": False,
            }
        )
        self.assertFalse(r16.passed)
        self.assertEqual(r16.action, "Confirm")


if __name__ == "__main__":
    unittest.main()
