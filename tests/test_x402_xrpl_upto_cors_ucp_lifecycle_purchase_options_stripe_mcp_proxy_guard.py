"""Unit tests for Stage 170 deterministic protocol & benchmark guardrails (2026-10-23)."""

from __future__ import annotations

import unittest

from lab.x402_xrpl_upto_cors_ucp_lifecycle_purchase_options_stripe_mcp_proxy_tau2_guard import (
    validate_stripe_mcp_proxy_metadata_forwarding_and_skills_guard,
    validate_tau2_malformed_tool_call_scoring_and_pii_leak_guard,
    validate_ucp_checkout_lifecycle_purchase_options_and_response_binding_guard,
    validate_x402_xrpl_upto_cors_and_anti_wash_guard,
)


class TestStage170Guards(unittest.TestCase):
    def test_x402_xrpl_upto_cors_and_anti_wash_guard(self) -> None:
        ok = validate_x402_xrpl_upto_cors_and_anti_wash_guard(
            {
                "payer": "rN7n7otQDd6FczFgLdSqtcsAUxDkw6fzRH",
                "pay_to": "rPT1Sjq2YGrBMTttX4GZHjKu9dyfzbpAYe",
                "xrpl_upto": {
                    "network": "xrpl:1",
                    "asset": "XRP",
                    "are_fees_sponsored": False,
                    "claim_prefix": "434C4D00",
                    "low_s_canonical": True,
                    "phase": "verify",
                    "max_amount": 10_000_000,
                    "max_timeout_seconds": 300,
                    "min_settle_delay": 600,
                    "ledger_close_time": 1000,
                    "cancel_after": 1320,
                    "settle_delay": 600,
                    "channel_balance": 0,
                },
                "cors_check": {
                    "http_method": "OPTIONS",
                    "route_explicit_options": False,
                    "returned_status": 204,
                    "allow_headers": ["PAYMENT-SIGNATURE", "CONTENT-TYPE"],
                    "expose_headers": ["PAYMENT-REQUIRED", "PAYMENT-RESPONSE"],
                },
            }
        )
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.decision_code, "X402_XRPL_UPTO_CORS_AND_ANTI_WASH_OK")

        # Self-payment rejected (PR #3910)
        self_pay = validate_x402_xrpl_upto_cors_and_anti_wash_guard(
            {
                "payer": "0xAbC1230000000000000000000000000000000001",
                "pay_to": "0xabc1230000000000000000000000000000000001",
            }
        )
        self.assertFalse(self_pay.allowed)
        self.assertEqual(self_pay.decision_code, "X402_SELF_PAYMENT_PROHIBITED")

        # Non-canonical XRPL network (#3023)
        bad_net = validate_x402_xrpl_upto_cors_and_anti_wash_guard(
            {"xrpl_upto": {"network": "xrpl:01"}}
        )
        self.assertFalse(bad_net.allowed)
        self.assertEqual(bad_net.decision_code, "X402_XRPL_UPTO_NON_CANONICAL_NETWORK")

        # Unexpected settlementTransaction at /verify (#3023)
        unexpected_tx = validate_x402_xrpl_upto_cors_and_anti_wash_guard(
            {
                "xrpl_upto": {
                    "network": "xrpl:1",
                    "phase": "verify",
                    "has_settlement_transaction": True,
                }
            }
        )
        self.assertFalse(unexpected_tx.allowed)
        self.assertEqual(
            unexpected_tx.decision_code,
            "X402_XRPL_UPTO_UNEXPECTED_SETTLEMENT_TX_AT_VERIFY",
        )

        # Bare close with claim fields present on pre-delivered charge (#3023)
        bad_bare_close = validate_x402_xrpl_upto_cors_and_anti_wash_guard(
            {
                "xrpl_upto": {
                    "network": "xrpl:1",
                    "phase": "settle",
                    "max_amount": 10_000_000,
                    "settle_amount": 2_000_000,
                    "channel_balance": 2_500_000,
                    "claim_fields_present": True,
                }
            }
        )
        self.assertFalse(bad_bare_close.allowed)
        self.assertEqual(
            bad_bare_close.decision_code,
            "X402_XRPL_UPTO_BARE_CLOSE_MUST_OMIT_CLAIM_FIELDS",
        )

        # OPTIONS preflight treated as 402 (#3738)
        bad_options = validate_x402_xrpl_upto_cors_and_anti_wash_guard(
            {
                "cors_check": {
                    "http_method": "OPTIONS",
                    "route_explicit_options": False,
                    "returned_status": 402,
                }
            }
        )
        self.assertFalse(bad_options.allowed)
        self.assertEqual(bad_options.decision_code, "X402_OPTIONS_PREFLIGHT_TREATED_AS_PAID")

    def test_ucp_checkout_lifecycle_purchase_options_and_response_binding_guard(self) -> None:
        ok = validate_ucp_checkout_lifecycle_purchase_options_and_response_binding_guard(
            {
                "status_transition": {
                    "from_state": "ready_for_complete",
                    "to_state": "requires_escalation",
                },
                "purchase_option_check": {
                    "selected_purchase_option_id": "po_sub_monthly",
                    "available_option_ids": ["po_once", "po_sub_monthly"],
                    "has_recurring_schedules": True,
                    "recurring_schedule_amount_in_totals": 0,
                    "has_subscription_policy": True,
                },
                "signed_response_check": {
                    "bound_to_request_method_and_uri": True,
                    "stale_replayed_response": False,
                },
                "idempotency_check": {
                    "stored_operation": "cancel_checkout",
                    "current_operation": "cancel_checkout",
                    "stored_target_id": "chk_123",
                    "current_target_id": "chk_123",
                    "signed_mcp_request": True,
                    "header_idempotency_key": "idem_abc",
                    "meta_idempotency_key": "idem_abc",
                },
            }
        )
        self.assertTrue(ok.allowed)

        # Terminal state regression (#672)
        bad_term = validate_ucp_checkout_lifecycle_purchase_options_and_response_binding_guard(
            {"status_transition": {"from_state": "completed", "to_state": "incomplete"}}
        )
        self.assertFalse(bad_term.allowed)
        self.assertEqual(bad_term.decision_code, "UCP_TERMINAL_STATE_REGRESSION_FORBIDDEN")

        # Recurring schedule included in checkout totals (PR #890)
        bad_sub = validate_ucp_checkout_lifecycle_purchase_options_and_response_binding_guard(
            {
                "purchase_option_check": {
                    "selected_purchase_option_id": "po_sub_monthly",
                    "available_option_ids": ["po_sub_monthly"],
                    "has_recurring_schedules": True,
                    "recurring_schedule_amount_in_totals": 2900,
                }
            }
        )
        self.assertFalse(bad_sub.allowed)
        self.assertEqual(
            bad_sub.decision_code,
            "UCP_RECURRING_SCHEDULE_OWED_AT_CHECKOUT_FORBIDDEN",
        )

        # Stale signed REST response replay (PR #699)
        bad_sig = validate_ucp_checkout_lifecycle_purchase_options_and_response_binding_guard(
            {"signed_response_check": {"bound_to_request_method_and_uri": False}}
        )
        self.assertFalse(bad_sig.allowed)
        self.assertEqual(bad_sig.decision_code, "UCP_SIGNED_RESPONSE_NOT_BOUND_TO_REQUEST")

        # Cross-target idempotency key reuse on cancel_checkout (PR #782)
        bad_idem = validate_ucp_checkout_lifecycle_purchase_options_and_response_binding_guard(
            {
                "idempotency_check": {
                    "stored_operation": "cancel_checkout",
                    "current_operation": "cancel_checkout",
                    "stored_target_id": "chk_123",
                    "current_target_id": "chk_999",
                }
            }
        )
        self.assertFalse(bad_idem.allowed)
        self.assertEqual(bad_idem.decision_code, "UCP_IDEMPOTENCY_TARGET_MISMATCH")

    def test_stripe_mcp_proxy_metadata_forwarding_and_skills_guard(self) -> None:
        ok = validate_stripe_mcp_proxy_metadata_forwarding_and_skills_guard(
            {
                "mcp_proxy_tool": {
                    "preserved_title": True,
                    "preserved_annotations": True,
                },
                "mcp_forwarding_failure": {
                    "is_jsonrpc_request": True,
                    "replied_with_jsonrpc_error": True,
                },
                "python_toolkit_deps": {
                    "mcp_major_version": 1,
                    "openai_extra_package": "openai-agents",
                },
                "mcp_events_ext": {
                    "delivery_mode": "webhook",
                    "standard_webhooks_signature_valid": True,
                    "skipped_events_detected": True,
                    "truncated_flag": True,
                },
            }
        )
        self.assertTrue(ok.allowed)

        # Dropped remote tool annotations in local proxy (PR #584)
        bad_meta = validate_stripe_mcp_proxy_metadata_forwarding_and_skills_guard(
            {"mcp_proxy_tool": {"preserved_title": False, "preserved_annotations": False}}
        )
        self.assertFalse(bad_meta.allowed)
        self.assertEqual(bad_meta.decision_code, "STRIPE_MCP_PROXY_METADATA_DROPPED")

        # Dropped forwarding error on JSON-RPC request (PR #542)
        bad_fwd = validate_stripe_mcp_proxy_metadata_forwarding_and_skills_guard(
            {
                "mcp_forwarding_failure": {
                    "is_jsonrpc_request": True,
                    "replied_with_jsonrpc_error": False,
                }
            }
        )
        self.assertFalse(bad_fwd.allowed)
        self.assertEqual(bad_fwd.decision_code, "STRIPE_MCP_FORWARDING_REQUEST_DROPPED")

        # Replying to JSON-RPC notification on forwarding failure (PR #542)
        bad_notif = validate_stripe_mcp_proxy_metadata_forwarding_and_skills_guard(
            {
                "mcp_forwarding_failure": {
                    "is_jsonrpc_request": False,
                    "replied_with_jsonrpc_error": True,
                }
            }
        )
        self.assertFalse(bad_notif.allowed)
        self.assertEqual(bad_notif.decision_code, "STRIPE_MCP_NOTIFICATION_MUST_NOT_REPLY")

    def test_tau2_malformed_tool_call_scoring_and_pii_leak_guard(self) -> None:
        ok = validate_tau2_malformed_tool_call_scoring_and_pii_leak_guard(
            {
                "orchestrator_trial": {
                    "agent_fault": "non_object_tool_arguments",
                    "termination_reason": "AGENT_ERROR",
                    "dropped_from_denominator": False,
                },
                "retail_scenario_check": {
                    "known_info": "You are Mei Kovacs in zipcode 28236.",
                    "internal_user_id": "mei_kovacs_8020",
                },
                "voice_submission_check": {
                    "release_date": "2026-10-22",
                    "legacy_ava_0_slug": False,
                },
            }
        )
        self.assertTrue(ok.allowed)

        # Malformed tool-call arguments misclassified as INFRASTRUCTURE_ERROR (PR #674)
        bad_score = validate_tau2_malformed_tool_call_scoring_and_pii_leak_guard(
            {
                "orchestrator_trial": {
                    "agent_fault": "non_object_tool_arguments",
                    "termination_reason": "INFRASTRUCTURE_ERROR",
                    "dropped_from_denominator": True,
                }
            }
        )
        self.assertFalse(bad_score.allowed)
        self.assertEqual(
            bad_score.decision_code,
            "TAU2_AGENT_FAULT_MISCLASSIFIED_AS_INFRA_ERROR",
        )

        # Internal user_id leaked in retail known_info (PR #677)
        bad_pii = validate_tau2_malformed_tool_call_scoring_and_pii_leak_guard(
            {
                "retail_scenario_check": {
                    "known_info": "You are mei_kovacs_8020 in zipcode 28236.",
                    "internal_user_id": "mei_kovacs_8020",
                }
            }
        )
        self.assertFalse(bad_pii.allowed)
        self.assertEqual(bad_pii.decision_code, "TAU2_KNOWN_INFO_INTERNAL_USER_ID_LEAK")


if __name__ == "__main__":
    unittest.main()
