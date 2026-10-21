"""Unit tests for Stage 124 guard module."""

from __future__ import annotations

import unittest

from lab.x402_pay_guard_bazaar_fastify_stripe_dxt_mcp_inspector_tau2_memory_guard import (
    MONEY_MOVING_STRIPE_TOOLS,
    evaluate_mcp_inspector_release_tau2_memory_guard,
    evaluate_stripe_dxt_hooks_pytest_guard,
    evaluate_x402_pay_guard_bazaar_fastify,
)


class TestStage124Guard(unittest.TestCase):
    def test_x402_pay_guard_bazaar_fastify(self) -> None:
        ok = evaluate_x402_pay_guard_bazaar_fastify(
            {
                "safe_pay_verdict": "allow",
                "reputation_tags": [],
                "seller_uptime_pct": 99.95,
                "required_amount_minor": 100,
                "contract_price_minor": 100,
                "spend_cap_minor": 500,
                "tanilo_eval_state": "evaluated_ok",
                "require_atc_card": True,
                "atc_ed25519_verified": True,
                "atc_version": "ATC/1.0",
                "agent_solvent": True,
                "bazaar_client_mode": "async_get_async_client",
                "bazaar_search_query": "market-data",
                "settlement_failure_content_type": "text/plain; charset=utf-8",
                "settlement_failure_body": "Settlement failed: insufficient balance",
                "double_json_encoded_plain_string": False,
                "amount_network_scheme": "xrpl_iou_decimal",
                "amount_value_str": "12.50",
                "network_family": "cardano",
                "cardano_transfer_method": "default",
                "cardano_token": "USDM",
            }
        )
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.decision_code, "X402_PAY_GUARD_BAZAAR_FASTIFY_OK")

        # Sanctions / drainer block (#3851/#3845)
        bad_sanctions = evaluate_x402_pay_guard_bazaar_fastify({"reputation_tags": ["ofac_sdn"]})
        self.assertFalse(bad_sanctions.allowed)
        self.assertEqual(bad_sanctions.decision_code, "X402_SAFE_PAY_SANCTIONS_OR_REPUTATION_BLOCKED")

        # Tanilo spend cap / indeterminate block (#3816)
        bad_tanilo = evaluate_x402_pay_guard_bazaar_fastify({"required_amount_minor": 600, "spend_cap_minor": 500})
        self.assertFalse(bad_tanilo.allowed)
        self.assertEqual(bad_tanilo.decision_code, "X402_TANILO_PRICE_CAP_OR_INDETERMINATE_BLOCKED")

        # UTA Trust Kit ATC/1.0 block (#3815)
        bad_atc = evaluate_x402_pay_guard_bazaar_fastify({"require_atc_card": True, "atc_ed25519_verified": False})
        self.assertFalse(bad_atc.allowed)
        self.assertEqual(bad_atc.decision_code, "X402_UTA_AGENT_TRUST_CARD_REJECTED")

        # Bazaar sync AttributeError / empty query (#3842)
        bad_bazaar = evaluate_x402_pay_guard_bazaar_fastify({"bazaar_client_mode": "sync_missing_get_client"})
        self.assertFalse(bad_bazaar.allowed)
        self.assertEqual(bad_bazaar.decision_code, "X402_BAZAAR_ASYNC_CLIENT_OR_EMPTY_QUERY_ERROR")

        # Fastify double JSON encoding on text/plain (#3834)
        bad_fastify = evaluate_x402_pay_guard_bazaar_fastify(
            {"settlement_failure_content_type": "text/plain", "double_json_encoded_plain_string": True}
        )
        self.assertFalse(bad_fastify.allowed)
        self.assertEqual(bad_fastify.decision_code, "X402_FASTIFY_NON_JSON_STRING_DOUBLE_ENCODED")

        # Cardano script method rejection (#3790)
        bad_cardano = evaluate_x402_pay_guard_bazaar_fastify(
            {"network_family": "cardano", "cardano_transfer_method": "script"}
        )
        self.assertFalse(bad_cardano.allowed)
        self.assertEqual(bad_cardano.decision_code, "X402_CARDANO_CIP30_PAYWALL_VIOLATION")

    def test_stripe_dxt_hooks_pytest_guard(self) -> None:
        tools = [
            {
                "name": name,
                "description": f"Executes {name}. Safety note: moves real money or mutates customer-visible billing state.",
            }
            for name in MONEY_MOVING_STRIPE_TOOLS
        ]
        ok = evaluate_stripe_dxt_hooks_pytest_guard(
            {
                "dxt_manifest_tools": tools,
                "workflow_action_refs": ["actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683"],
                "transcript_text": "Configure Metronome usage-based billing meters",
                "require_metronome_nudge": True,
                "python_test_runner": "pytest",
                "has_pytest_asyncio": True,
                "discovered_tests": 51,
            }
        )
        self.assertTrue(ok.allowed)
        self.assertTrue(ok.nudge_eligible)
        self.assertEqual(ok.discovered_tests, 51)

        # Missing safety note on create_refund (#480)
        bad_dxt = evaluate_stripe_dxt_hooks_pytest_guard(
            {"dxt_manifest_tools": [{"name": "create_refund", "description": "Creates a refund object."}]}
        )
        self.assertFalse(bad_dxt.allowed)
        self.assertEqual(bad_dxt.decision_code, "STRIPE_DXT_MONEY_TOOL_SAFETY_NOTE_MISSING")

        # Unpinned workflow tag (#552)
        bad_sha = evaluate_stripe_dxt_hooks_pytest_guard({"workflow_action_refs": ["actions/checkout@v4"]})
        self.assertFalse(bad_sha.allowed)
        self.assertEqual(bad_sha.decision_code, "STRIPE_WORKFLOW_ACTION_MUTABLE_TAG_REJECTED")

        # Silent skip under unittest discover (#560)
        bad_pytest = evaluate_stripe_dxt_hooks_pytest_guard(
            {"python_test_runner": "unittest_discover", "discovered_tests": 3}
        )
        self.assertFalse(bad_pytest.allowed)
        self.assertEqual(bad_pytest.decision_code, "STRIPE_PYTHON_SILENT_TEST_SKIP_BLOCKED")

    def test_mcp_inspector_release_tau2_memory_guard(self) -> None:
        ok = evaluate_mcp_inspector_release_tau2_memory_guard(
            {
                "inspector_dangerously_omit_auth": False,
                "inspector_bind_host": "127.0.0.1",
                "inspector_api_token_present": True,
                "sep3398_release_months": (3, 9),
                "sep3398_cycle_duration_months": 8,
                "sep3440_tasks_events_wg_unified": True,
                "tau2_standard_pass1": 49.48,
                "tau2_policy_harness_pass1": 57.22,
                "tau2_permissive_replay_grades": False,
                "ampup_bm25_scoped_to_opened_links": True,
            }
        )
        self.assertTrue(ok.allowed)
        self.assertAlmostEqual(ok.policy_harness_pass1_uplift_pts, 7.74, places=2)

        # DANGEROUSLY_OMIT_AUTH blocked (#3418)
        bad_inspector = evaluate_mcp_inspector_release_tau2_memory_guard({"inspector_dangerously_omit_auth": True})
        self.assertFalse(bad_inspector.allowed)
        self.assertEqual(bad_inspector.decision_code, "MCP_INSPECTOR_SECURITY_THREAT_BLOCKED")

        # Permissive replay grades blocked (#604)
        bad_tau2 = evaluate_mcp_inspector_release_tau2_memory_guard({"tau2_permissive_replay_grades": True})
        self.assertFalse(bad_tau2.allowed)
        self.assertEqual(bad_tau2.decision_code, "TAU2_MEMORY_REPLAY_OR_VOICE_TICK_VIOLATION")


if __name__ == "__main__":
    unittest.main()
