"""Unit tests for Stage 116 deterministic protocol & benchmark guardrails."""

from __future__ import annotations

import unittest

from lab.acp_user_approval_ucp_mandate_ttl_return_x402_provenance_tau2_sandbox_guard import (
    compute_jcs_sha256_hex,
    validate_acp_user_approval_digest_and_intent_conflict_guard,
    validate_tau2_knowledge_sandbox_and_voice_bayes_guard,
    validate_ucp_admission_mandate_ttl_and_return_policy_guard,
    validate_x402_response_provenance_and_paywall_routing_guard,
)


class TestStage116Guard(unittest.TestCase):
    def setUp(self) -> None:
        self.approval_items = [{"sku": "TEE-01", "quantity": 1, "variant": "green"}]
        self.approved_at = "2026-10-21T14:30:00Z"
        self.approval_digest = compute_jcs_sha256_hex(
            {"items": self.approval_items, "approved_at": self.approved_at}
        )
        self.valid_acp = {
            "checkout_complete_approval_digest": self.approval_digest,
            "user_approval": {
                "items": self.approval_items,
                "approved_at": self.approved_at,
                "approval_digest": self.approval_digest,
            },
            "disputed_order_items": [
                {"sku": "TEE-01", "quantity": 1, "variant": "black"}
            ],
            "dispute_resolution_decision": {
                "conflict_type": "intent",
                "liable_party": "agent_platform",
                "merchant_charge_reversed": False,
            },
        }

        self.valid_ucp = {
            "mandate_evaluation": {
                "key_discovery_source": "well_known_ucp_keys",
                "evaluated_at_epoch": 1792590000,
                "mandate_exp_epoch": 1792590060,
                "completed_at_epoch": 1792590120,
                "admission_result": "VALID",
                "aborted_for_post_admission_expiry": False,
            },
            "return_policy": {
                "eligibility": "window",
                "anchor": "delivered",
                "platform_computed_expires_at": False,
                "charged_return_fee_minor": 500,
                "stated_max_return_fee_minor": 500,
            },
            "quote_extension": {
                "complete_includes_redundant_accepted_id": False,
                "quote_totals_entries_count": 1,
            },
        }

        self.fixed_point = {
            "endpoint": "https://api.example.com/v1/weather",
            "inputs": {"city": "SF"},
            "result": {"temp_c": 18},
            "method": "GET",
            "dataVintage": "2026-10-21T12:00:00Z",
        }
        self.response_hash = compute_jcs_sha256_hex(self.fixed_point)
        self.valid_x402 = {
            "response_provenance": {
                "fixed_point": self.fixed_point,
                "response_hash": self.response_hash,
                "verification_outcome": "verified",
                "verifier_self_proof_passed": True,
            },
            "paywall_inline_config_json": '{"appName":"Demo\\u003c/script\\u003e"}',
            "legacy_route_match": {
                "raw_path": "/api/users/a%2Fb",
                "served_unpaid": False,
            },
            "batch_settlement": {
                "refund_carried_claims": True,
                "pending_settle_after_refund": True,
                "stop_flush_calls_settle": True,
            },
        }

        self.valid_tau2 = {
            "knowledge_sandbox": {
                "sandbox_dir": "/var/tmp/tau2-kb-sandboxes-1000/sbx_01",
                "env_vars": {
                    "PATH": "/usr/bin:/bin",
                    "LANG": "C.UTF-8",
                    "HOME": "/var/tmp/tau2-kb-sandboxes-1000/sbx_01",
                    "LC_ALL": "C.UTF-8",
                },
                "parent_secret_values": ["sk-live-supersecret999"],
                "stdout": "Result: [REDACTED]",
                "stderr": "",
                "deny_read": [
                    "/home/user/.ssh",
                    "/home/user/.aws",
                    "/repo/data",
                    "/repo",
                    "/tmp",
                    "/etc/passwd",
                ],
                "required_outside_kb_denies": [
                    "/repo/data",
                    "/repo",
                    "/tmp",
                    "/etc/passwd",
                ],
            },
            "voice_v2_call_quality": {
                "interaction_flag_count": 1,
                "experience_bad_utterance_ratio": 0.15,
                "call_quality_passed": True,
            },
            "bayes_at_n_cohort": {
                "duplicate_trials": 0,
                "missing_grades": 0,
                "infra_error_trials": 0,
            },
        }

    def test_acp_user_approval_valid(self) -> None:
        res = validate_acp_user_approval_digest_and_intent_conflict_guard(
            self.valid_acp
        )
        self.assertTrue(res.allowed)
        self.assertEqual(
            res.decision_code, "ACP_USER_APPROVAL_AND_DISPUTE_RULE4_VERIFIED"
        )

    def test_acp_user_approval_digest_mismatch_rejected(self) -> None:
        bad = {
            **self.valid_acp,
            "checkout_complete_approval_digest": "0" * 64,
        }
        res = validate_acp_user_approval_digest_and_intent_conflict_guard(bad)
        self.assertFalse(res.allowed)
        self.assertEqual(res.decision_code, "ACP_USER_APPROVAL_DIGEST_MISMATCH")

    def test_acp_intent_conflict_merchant_reversal_rejected(self) -> None:
        bad = {
            **self.valid_acp,
            "dispute_resolution_decision": {
                "conflict_type": "intent",
                "liable_party": "merchant",
                "merchant_charge_reversed": True,
            },
        }
        res = validate_acp_user_approval_digest_and_intent_conflict_guard(bad)
        self.assertFalse(res.allowed)
        self.assertEqual(
            res.decision_code, "ACP_INTENT_CONFLICT_MERCHANT_REVERSAL_FORBIDDEN"
        )

    def test_ucp_mandate_ttl_and_return_valid(self) -> None:
        res = validate_ucp_admission_mandate_ttl_and_return_policy_guard(self.valid_ucp)
        self.assertTrue(res.allowed)
        self.assertEqual(
            res.decision_code, "UCP_MANDATE_TTL_RETURN_AND_QUOTE_VERIFIED"
        )

    def test_ucp_post_admission_expiry_abort_rejected(self) -> None:
        bad = {
            **self.valid_ucp,
            "mandate_evaluation": {
                **self.valid_ucp["mandate_evaluation"],
                "aborted_for_post_admission_expiry": True,
            },
        }
        res = validate_ucp_admission_mandate_ttl_and_return_policy_guard(bad)
        self.assertFalse(res.allowed)
        self.assertEqual(
            res.decision_code, "UCP_POST_ADMISSION_MANDATE_EXPIRY_ABORT_FORBIDDEN"
        )

    def test_ucp_omitted_return_eligibility_rejected(self) -> None:
        bad = {
            **self.valid_ucp,
            "return_policy": {
                **self.valid_ucp["return_policy"],
                "eligibility": None,
            },
        }
        res = validate_ucp_admission_mandate_ttl_and_return_policy_guard(bad)
        self.assertFalse(res.allowed)
        self.assertEqual(
            res.decision_code, "UCP_RETURN_ELIGIBILITY_OMITTED_OR_INVALID"
        )

    def test_x402_provenance_and_paywall_valid(self) -> None:
        res = validate_x402_response_provenance_and_paywall_routing_guard(
            self.valid_x402
        )
        self.assertTrue(res.allowed)
        self.assertEqual(
            res.decision_code, "X402_PROVENANCE_PAYWALL_AND_SETTLEMENT_VERIFIED"
        )

    def test_x402_provenance_hash_mismatch_rejected(self) -> None:
        bad = {
            **self.valid_x402,
            "response_provenance": {
                **self.valid_x402["response_provenance"],
                "response_hash": "f" * 64,
            },
        }
        res = validate_x402_response_provenance_and_paywall_routing_guard(bad)
        self.assertFalse(res.allowed)
        self.assertEqual(res.decision_code, "X402_RESPONSE_PROVENANCE_HASH_MISMATCH")

    def test_x402_encoded_separator_bypass_rejected(self) -> None:
        bad = {
            **self.valid_x402,
            "legacy_route_match": {
                "raw_path": "/api/users/a%2Fb",
                "served_unpaid": True,
            },
        }
        res = validate_x402_response_provenance_and_paywall_routing_guard(bad)
        self.assertFalse(res.allowed)
        self.assertEqual(res.decision_code, "X402_ENCODED_PATH_SEPARATOR_BYPASS")

    def test_tau2_sandbox_and_voice_bayes_valid(self) -> None:
        res = validate_tau2_knowledge_sandbox_and_voice_bayes_guard(self.valid_tau2)
        self.assertTrue(res.allowed)
        self.assertEqual(res.decision_code, "TAU2_SANDBOX_VOICE_AND_BAYES_VERIFIED")

    def test_tau2_sandbox_secret_env_leak_rejected(self) -> None:
        bad = {
            **self.valid_tau2,
            "knowledge_sandbox": {
                **self.valid_tau2["knowledge_sandbox"],
                "env_vars": {
                    **self.valid_tau2["knowledge_sandbox"]["env_vars"],
                    "LC_OPENAI_API_KEY": "sk-live-supersecret999",
                },
            },
        }
        res = validate_tau2_knowledge_sandbox_and_voice_bayes_guard(bad)
        self.assertFalse(res.allowed)
        self.assertEqual(res.decision_code, "TAU2_SANDBOX_ENV_OR_SECRET_LEAK")

    def test_tau2_sandbox_outside_kb_read_exposed_rejected(self) -> None:
        bad = {
            **self.valid_tau2,
            "knowledge_sandbox": {
                **self.valid_tau2["knowledge_sandbox"],
                "deny_read": ["/home/user/.ssh"],
            },
        }
        res = validate_tau2_knowledge_sandbox_and_voice_bayes_guard(bad)
        self.assertFalse(res.allowed)
        self.assertEqual(res.decision_code, "TAU2_SANDBOX_OUTSIDE_KB_READ_EXPOSED")


if __name__ == "__main__":
    unittest.main()
