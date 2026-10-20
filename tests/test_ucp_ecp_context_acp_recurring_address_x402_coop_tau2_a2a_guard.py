"""Unit tests for Stage 90 deterministic guardrails."""

from __future__ import annotations

import unittest

from lab.ucp_ecp_context_acp_recurring_address_x402_coop_tau2_a2a_guard import (
    validate_acp_recurring_allowance_address_and_lodging_guard,
    validate_tau2_a2a_green_white_isolation_and_thought_signature_guard,
    validate_ucp_ecp_delegations_and_context_currency_guard,
    validate_x402_v12_cooperative_withdraw_and_claim_guard,
)


class Stage90GuardTests(unittest.TestCase):
    def test_ucp_ecp_delegations_and_context_currency_valid(self) -> None:
        payload = {
            "ecp_session": {
                "use_embedded_checkout": True,
                "service_level_embedded_supported": True,
                "checkout_ucp_services": {
                    "dev.ucp.shopping": [
                        {
                            "version": "2026-01-11",
                            "transport": "embedded",
                            "config": {
                                "delegations": [
                                    "payment.credential",
                                    "fulfillment.address_change",
                                ]
                            },
                        }
                    ]
                },
                "requested_delegations": ["payment.credential"],
            },
            "checkout_request": {
                "operation": "create",
                "body": {
                    "context": {"country": "US", "region": "CA", "postal_code": "94105"},
                    "buyer": {"first_name": "Ada", "last_name": "Lovelace"},
                },
            },
            "capability_maturity": {
                "level": "Stable",
                "version": "2026-01-11",
            },
        }
        res = validate_ucp_ecp_delegations_and_context_currency_guard(payload)
        self.assertTrue(res["allowed"], res["violations"])

    def test_ucp_ecp_delegations_and_context_currency_blocks_violations(self) -> None:
        payload = {
            "ecp_session": {
                "use_embedded_checkout": True,
                "service_level_embedded_supported": True,
                "checkout_ucp_services": {
                    "dev.ucp.shopping": [
                        {
                            "version": "2026-01-11",
                            "transport": "embedded",
                            "config": {"delegations": ["fulfillment.address_change"]},
                        }
                    ]
                },
                "requested_delegations": ["payment.credential"],
            },
            "checkout_request": {
                "operation": "complete",
                "body": {
                    "currency": "USD",
                    "context": {"country": "US"},
                    "buyer": {"full_name": "Ada Lovelace"},
                },
            },
            "capability_maturity": {
                "level": "Working Draft",
                "version": "2026-01-11",
            },
        }
        res = validate_ucp_ecp_delegations_and_context_currency_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("UCP_ECP_UNCONFIRMED_DELEGATION:payment.credential", res["violations"])
        self.assertIn("UCP_CLIENT_INPUT_CURRENCY_FORBIDDEN", res["violations"])
        self.assertIn("UCP_CONTEXT_FORBIDDEN_ON_COMPLETE", res["violations"])
        self.assertIn("UCP_LEGACY_FULL_NAME_FORBIDDEN:buyer", res["violations"])
        self.assertIn("UCP_MATURITY_WORKING_DRAFT_MUST_OMIT_VERSION", res["violations"])

    def test_acp_recurring_allowance_address_and_lodging_valid(self) -> None:
        payload = {
            "allowance": {
                "reason": "subscription",
                "max_amount": 36000,
                "amount_per_cycle": 2999,
                "max_cycles": 12,
                "trial_period_days": 14,
                "trial_amount": 0,
                "billing_cycle": {"interval": "month", "interval_count": 1},
            },
            "addresses": {
                "billing_address": {"country": "US", "postal_code": "94107"},
                "fulfillment_address": {
                    "name": "Grace Hopper",
                    "line_one": "100 Market St",
                    "city": "San Francisco",
                    "state": "CA",
                    "country": "US",
                    "postal_code": "94107",
                },
            },
            "lodging_checkout": {
                "used_static_feed_base_price_directly": False,
                "quote_token": "qt_hotel_8811",
                "cancellation_deadline": "2026-11-10T18:00:00Z",
                "payment_model": "prepaid",
                "quoted_room_subtotal": 45000,
                "nightly_breakdown": [
                    {"date": "2026-11-12", "rate": 22000},
                    {"date": "2026-11-13", "rate": 23000},
                ],
            },
        }
        res = validate_acp_recurring_allowance_address_and_lodging_guard(payload)
        self.assertTrue(res["allowed"], res["violations"])

    def test_acp_recurring_allowance_address_and_lodging_blocks_violations(self) -> None:
        payload = {
            "allowance": {
                "reason": "recurring",
                "max_amount": 10000,
                "amount_per_cycle": 3000,
                "max_cycles": 4,
                "billing_cycle": {"interval": "month", "interval_count": 1},
            },
            "addresses": {
                "billing_address": {
                    "country": "US",
                    "postal_code": "94107",
                    "line_one": "N/A",
                },
                "fulfillment_address": {
                    "name": "Grace Hopper",
                    "country": "US",
                    "postal_code": "94107",
                },
            },
            "lodging_checkout": {
                "used_static_feed_base_price_directly": True,
                "quote_token": "",
                "cancellation_deadline": "",
                "payment_model": "wire_only",
                "quoted_room_subtotal": 50000,
                "nightly_breakdown": [{"date": "2026-11-12", "rate": 20000}],
            },
        }
        res = validate_acp_recurring_allowance_address_and_lodging_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("ACP_RECURRING_CUMULATIVE_EXPOSURE_EXCEEDS_MAX:12000>10000", res["violations"])
        self.assertIn("ACP_BILLING_ADDRESS_FABRICATED_PLACEHOLDER:line_one", res["violations"])
        self.assertIn("ACP_FULFILLMENT_ADDRESS_INCOMPLETE:line_one", res["violations"])
        self.assertIn("ACP_LODGING_NON_BINDING_BASE_PRICE_USED_AT_CHECKOUT", res["violations"])
        self.assertIn("ACP_LODGING_NIGHTLY_BREAKDOWN_SUM_MISMATCH", res["violations"])

    def test_x402_v12_cooperative_withdraw_and_claim_valid(self) -> None:
        payload = {
            "function_name": "cooperativeWithdraw",
            "msg_sender": "0xAbC1230000000000000000000000000000000001",
            "authorized_withdrawer": "0xabc1230000000000000000000000000000000001",
            "has_valid_signature": False,
        }
        res = validate_x402_v12_cooperative_withdraw_and_claim_guard(payload)
        self.assertTrue(res["allowed"], res["violations"])

    def test_x402_v12_cooperative_withdraw_and_claim_blocks_violations(self) -> None:
        p1 = {
            "function_name": "finalizeWithdraw",
            "msg_sender": "0xabc1230000000000000000000000000000000001",
            "authorized_withdrawer": "0xabc1230000000000000000000000000000000001",
        }
        r1 = validate_x402_v12_cooperative_withdraw_and_claim_guard(p1)
        self.assertFalse(r1["allowed"])
        self.assertIn("X402_V12_REMOVED_WITHDRAW_FUNCTION_FORBIDDEN:finalizeWithdraw", r1["violations"])

        p2 = {
            "function_name": "cooperativeWithdrawWithSignature",
            "msg_sender": "0x9999990000000000000000000000000000000009",
            "authorized_withdrawer": "0xabc1230000000000000000000000000000000001",
            "has_valid_signature": True,
            "recovered_signer": "0xdef4560000000000000000000000000000000002",
        }
        r2 = validate_x402_v12_cooperative_withdraw_and_claim_guard(p2)
        self.assertFalse(r2["allowed"])
        self.assertIn("X402_V12_COOPERATIVE_WITHDRAW_SIGNATURE_INVALID", r2["violations"])

    def test_tau2_a2a_and_thought_signature_valid(self) -> None:
        payload = {
            "a2a_eval": {
                "white_agent_accessed_gold_db": False,
                "white_agent_received_benchmark_rubric": False,
                "green_agent_manages_environment": True,
            },
            "gemini3_turns": {
                "model": "gemini-3-pro",
                "assistant_tool_turns": [
                    {
                        "has_tool_call": True,
                        "thought_signature": "tsig_998877aabbcc",
                        "thought_signature_echoed_in_history": True,
                    }
                ],
            },
        }
        res = validate_tau2_a2a_green_white_isolation_and_thought_signature_guard(payload)
        self.assertTrue(res["allowed"], res["violations"])

    def test_tau2_a2a_and_thought_signature_blocks_violations(self) -> None:
        payload = {
            "a2a_eval": {
                "white_agent_accessed_gold_db": True,
                "white_agent_received_benchmark_rubric": True,
                "green_agent_manages_environment": False,
            },
            "gemini3_turns": {
                "model": "gemini-3-pro",
                "assistant_tool_turns": [
                    {
                        "has_tool_call": True,
                        "thought_signature": "",
                        "thought_signature_echoed_in_history": False,
                    }
                ],
            },
        }
        res = validate_tau2_a2a_green_white_isolation_and_thought_signature_guard(payload)
        self.assertFalse(res["allowed"])
        self.assertIn("TAU2_A2A_WHITE_AGENT_GOLD_DB_LEAK", res["violations"])
        self.assertIn("TAU2_GEMINI3_THOUGHT_SIGNATURE_MISSING:turn_0", res["violations"])


if __name__ == "__main__":
    unittest.main()
