"""Unit tests for Stage 188 deterministic guardrails."""

from __future__ import annotations

import unittest

from lab.x402_ingress_identity_text_plain_bazaar_method_tau2_voice_v1_checkpoint_fence_guard import (
    evaluate_tau2_voice_v1_checkpoint_and_nl_fence,
    evaluate_x402_ingress_settlement_refusal_identity,
    evaluate_x402_text_plain_bazaar_method_and_stellar_floor,
)


class TestStage188Guardrails(unittest.TestCase):
    def setUp(self) -> None:
        self.base_snapshot = {
            "method": "POST",
            "path": "/v1/chat/completions",
            "query": "model=gpt-5",
            "body": {"messages": [{"role": "user", "content": "hello"}]},
            "payTo": "0xAbCdEf1234567890AbCdEf1234567890AbCdEf12",
            "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "network": "eip155:8453",
            "amount": "10000",
            "scheme": "exact",
        }

    def test_x402_ingress_identity_pr3776(self) -> None:
        res_ok = evaluate_x402_ingress_settlement_refusal_identity(self.base_snapshot)
        self.assertTrue(res_ok.allowed)
        self.assertIsNotNone(res_ok.operation_identity)

        # Case-insensitive EVM address normalization yields identical operation_identity
        lower_snapshot = dict(
            self.base_snapshot,
            payTo=self.base_snapshot["payTo"].lower(),
            asset=self.base_snapshot["asset"].lower(),
        )
        res_lower = evaluate_x402_ingress_settlement_refusal_identity(lower_snapshot)
        self.assertEqual(res_ok.operation_identity, res_lower.operation_identity)

        # Downstream re-derivation with mutated query/amount is prohibited
        res_div = evaluate_x402_ingress_settlement_refusal_identity(
            self.base_snapshot,
            downstream_rederived_snapshot=dict(self.base_snapshot, amount="20000"),
        )
        self.assertFalse(res_div.allowed)
        self.assertEqual(
            res_div.reason_code,
            "x402_ingress_identity_downstream_divergence_prohibited",
        )

        # "Absence is not difference": missing counterparty bytes must report refused_comparison_impossible
        res_abs = evaluate_x402_ingress_settlement_refusal_identity(
            self.base_snapshot,
            counterparty_missing_observed_bytes=True,
            collapse_absence_into_mismatch=False,
        )
        self.assertFalse(res_abs.allowed)
        self.assertEqual(
            res_abs.countersignature_status, "refused_comparison_impossible"
        )

        res_collapsed = evaluate_x402_ingress_settlement_refusal_identity(
            self.base_snapshot,
            counterparty_missing_observed_bytes=True,
            collapse_absence_into_mismatch=True,
        )
        self.assertFalse(res_collapsed.allowed)
        self.assertEqual(
            res_collapsed.reason_code,
            "x402_countersignature_absence_collapsed_into_mismatch",
        )

    def test_x402_text_plain_and_bazaar_method_pr3901_pr3880(self) -> None:
        # Valid text/plain + body route probed with GET resolved to POST
        ok = evaluate_x402_text_plain_bazaar_method_and_stellar_floor(
            bazaar_input={"bodyType": "json", "body": {"prompt": "hi"}},
            probe_method="GET",
        )
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.resolved_bazaar_method, "POST")
        self.assertEqual(ok.bazaar_method_enum, ("POST",))
        self.assertEqual(
            ok.rendered_402_body_bytes, b"Payment required.\nPreview line 2."
        )

        # JSON-encoding a text/plain 402 string body is rejected
        bad_plain = evaluate_x402_text_plain_bazaar_method_and_stellar_floor(
            middleware_json_encoded_plain_text=True
        )
        self.assertFalse(bad_plain.allowed)
        self.assertEqual(
            bad_plain.reason_code, "x402_text_plain_402_body_json_encoded"
        )

        # Advertising probe method GET for a body route is rejected
        bad_bazaar = evaluate_x402_text_plain_bazaar_method_and_stellar_floor(
            bazaar_input={"bodyType": "json", "body": {"prompt": "hi"}},
            probe_method="GET",
            advertised_method="GET",
        )
        self.assertFalse(bad_bazaar.allowed)
        self.assertEqual(
            bad_bazaar.reason_code,
            "x402_bazaar_probe_method_mismatches_declared_input_shape",
        )

    def test_tau2_voice_v1_checkpoint_and_nl_fence_pr673_pr533_pr562(self) -> None:
        ok = evaluate_tau2_voice_v1_checkpoint_and_nl_fence()
        self.assertTrue(ok.allowed)
        self.assertEqual(len(ok.parsed_judge_results), 1)

        # PR #673: reloading voice-v1 without canonical_tasks=True is rejected
        bad_canon = evaluate_tau2_voice_v1_checkpoint_and_nl_fence(
            benchmark_version="voice-v1", reload_used_canonical_tasks=False
        )
        self.assertFalse(bad_canon.allowed)
        self.assertEqual(
            bad_canon.reason_code,
            "tau2_voice_v1_canonical_task_reload_flag_mismatch",
        )

        # PR #533: unlinking old trajectory before atomic os.replace is rejected
        bad_ckpt = evaluate_tau2_voice_v1_checkpoint_and_nl_fence(
            replacement_write_failed=True,
            deleted_old_trajectory_before_replace=True,
        )
        self.assertFalse(bad_ckpt.allowed)
        self.assertEqual(
            bad_ckpt.reason_code,
            "tau2_checkpoint_replacement_deleted_before_atomic_write",
        )

        # PR #562: fenced JSON with leading prose or ```python tag is rejected
        bad_fence = evaluate_tau2_voice_v1_checkpoint_and_nl_fence(
            judge_raw_response='Here is the verdict:\n```json\n{"results": []}\n```'
        )
        self.assertFalse(bad_fence.allowed)
        self.assertEqual(
            bad_fence.reason_code,
            "tau2_nl_judge_malformed_or_non_whole_response_fence",
        )


if __name__ == "__main__":
    unittest.main()
