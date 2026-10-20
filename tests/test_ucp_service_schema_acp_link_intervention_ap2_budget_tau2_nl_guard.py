"""Unit tests for Stage 64 runtime guards (`ucp_service_schema_acp_link_intervention_ap2_budget_tau2_nl_guard`)."""

from __future__ import annotations

import unittest

from lab.ucp_service_schema_acp_link_intervention_ap2_budget_tau2_nl_guard import (
    verify_acp_stripe_link_intervention_session_states_and_discounts,
    verify_ap2_cross_merchant_budget_solana_pay_and_haggle,
    verify_tau2_gold_replay_nl_judge_cost_and_sandbox,
    verify_ucp_service_schema_w007_permalink_and_wba_signing,
)


class Stage64GuardTest(unittest.TestCase):
    def test_ucp_service_schema_w007_permalink_and_wba_signing_passes_valid(self) -> None:
        res = verify_ucp_service_schema_w007_permalink_and_wba_signing(
            entity_registry="services",
            transport="rest",
            schema_url="https://ucp.dev/2026-04-08/services/shopping/rest.openapi.json",
            endpoint_url="https://api.merchant.example/ucp",
            schema_def_keys=["agent", "ucp_request", "ucp_response"],
            handler_type="encrypted-credential",
            identity_access_token_used_as_auth=False,
            config_has_business_id=True,
            encrypted_handler_exposes_tokenize_endpoints=False,
            is_permalink_cart_merge=True,
            explicit_buyer_action_on_rendered_state=True,
            merge_trigger="explicit_button_click",
            has_ucp_agent_header=True,
            has_signature_agent_header=True,
            signature_agent_key_label="sig1",
            covered_components=[
                "@method",
                "@authority",
                "@path",
                '"signature-agent";key="sig1"',
                "ucp-agent",
                "content-digest",
                "content-type",
            ],
            body_bytes_len=128,
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.reason_codes, ())

    def test_ucp_service_schema_w007_permalink_and_wba_signing_blocks_violations(self) -> None:
        res = verify_ucp_service_schema_w007_permalink_and_wba_signing(
            entity_registry="services",
            transport="rest",
            schema_url="https://ucp.dev/2026-04-08/schemas/shopping/checkout.json",
            endpoint_url="https://api.merchant.example/ucp",
            schema_def_keys=["ucp_agent"],
            handler_type="encrypted-credential",
            identity_access_token_used_as_auth=True,
            config_has_business_id=True,
            encrypted_handler_exposes_tokenize_endpoints=True,
            is_permalink_cart_merge=True,
            explicit_buyer_action_on_rendered_state=False,
            merge_trigger="page_load",
            has_ucp_agent_header=True,
            has_signature_agent_header=True,
            signature_agent_key_label="sig1",
            covered_components=["@method", "@authority", "@path"],
            body_bytes_len=64,
        )
        self.assertFalse(res.passed)
        self.assertIn("ucp_service_schema_transport_format_mismatch", res.reason_codes)
        self.assertIn("ucp_reserved_prefix_w007_violation", res.reason_codes)
        self.assertIn("ucp_tokenizer_participant_id_used_as_authentication", res.reason_codes)
        self.assertIn("ucp_permalink_auto_cart_merge_without_buyer_action", res.reason_codes)
        self.assertIn("ucp_wba_signature_agent_or_ucp_agent_coverage_missing", res.reason_codes)

    def test_acp_stripe_link_intervention_and_session_states_passes_valid(self) -> None:
        res = verify_acp_stripe_link_intervention_session_states_and_discounts(
            payment_handler_id="com.stripe.link",
            agent_saw_raw_pan_or_cvc=False,
            buyer_authenticated_with_wallet=True,
            delegated_via_delegate_payment=True,
            delegated_token="vt_link_998123",
            session_status="authentication_required",
            next_operation="update",
            intervention_required=True,
            intervention_context={
                "intervention_type": "otp",
                "challenge_hint": "Enter 6-digit code sent to b***@example.com",
                "expires_at": 1792510000,
                "provider": "com.stripe.link",
            },
            intervention_response={"type": "otp", "code": "482910"},
            current_unix_ts=1792509000,
            onchain_discount={
                "wallet_holdings_verified": True,
                "duration": "once",
                "issued_at": 1792508500,
                "expires_at": 1792509900,
                "already_redeemed": False,
                "amount_minor": 1500,
                "allocations": [{"line_item_id": "li_1", "amount_minor": 900}, {"line_item_id": "li_2", "amount_minor": 600}],
            },
            intent_trace_reason_code="price_sensitivity",
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.reason_codes, ())

    def test_acp_stripe_link_intervention_and_session_states_blocks_violations(self) -> None:
        res = verify_acp_stripe_link_intervention_session_states_and_discounts(
            payment_handler_id="com.stripe.link",
            agent_saw_raw_pan_or_cvc=True,
            buyer_authenticated_with_wallet=False,
            delegated_via_delegate_payment=False,
            delegated_token=None,
            session_status="complete_in_progress",
            next_operation="complete",
            intervention_required=True,
            intervention_context={
                "intervention_type": "otp",
                "expires_at": 1792500000,
                "provider": "com.stripe.link",
            },
            intervention_response={"type": "redirect_complete", "code": ""},
            current_unix_ts=1792509000,
            onchain_discount={
                "wallet_holdings_verified": True,
                "duration": "once",
                "issued_at": 1792500000,
                "expires_at": 1792505000,
                "already_redeemed": True,
                "amount_minor": 1500,
                "allocations": [{"line_item_id": "li_1", "amount_minor": 1000}],
            },
            intent_trace_reason_code="unknown_reason",
        )
        self.assertFalse(res.passed)
        self.assertIn("acp_link_handler_raw_pan_exposure_forbidden", res.reason_codes)
        self.assertIn("acp_intervention_context_missing_or_expired", res.reason_codes)
        self.assertIn("acp_duplicate_complete_while_complete_in_progress", res.reason_codes)
        self.assertIn("acp_onchain_discount_allocation_or_expiry_invalid", res.reason_codes)
        self.assertIn("acp_intent_trace_unknown_reason_code", res.reason_codes)

    def test_ap2_cross_merchant_budget_solana_pay_and_haggle_passes_valid(self) -> None:
        res = verify_ap2_cross_merchant_budget_solana_pay_and_haggle(
            budget_limit_minor=10000,
            enforcement_mode="external_atomic_authority",
            operations=[
                {"verb": "authorize", "auth_id": "auth_m1", "amount_minor": 6000},
                {"verb": "commit", "auth_id": "auth_m1", "amount_minor": 6000},
                {"verb": "authorize", "auth_id": "auth_m2", "amount_minor": 3500},
            ],
            solana_pay_settlement={
                "reference_pubkey": "8x2b9ZpQkL4mN7vR1tY5wE3sD6fG8hJ2kL9mN4pQ7rS1",
                "mandate_reference_pubkey": "8x2b9ZpQkL4mN7vR1tY5wE3sD6fG8hJ2kL9mN4pQ7rS1",
                "recorded_as_readonly_account": True,
                "onchain_recipient": "MerchantSolanaWallet1111111111111111111111",
                "mandate_recipient": "MerchantSolanaWallet1111111111111111111111",
                "onchain_amount_minor": 3500,
                "mandate_amount_minor": 3500,
                "onchain_spl_mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                "mandate_spl_mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            },
            seen_solana_references=["OldRef111111111111111111111111111111111111"],
            haggle_session={
                "extension_uri": "ap2haggle/ap2/extensions/haggle/v0.1",
                "round_number": 2,
                "max_rounds": 4,
                "agreed_price_minor": 3500,
                "buyer_walk_away_minor": 4000,
                "seller_cost_floor_minor": 3000,
                "intermediate_offer_used_for_payment": False,
                "outcome_status": "accepted",
                "has_merchant_signed_cart_mandate": True,
            },
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.remaining_budget_minor, 500)
        self.assertEqual(res.reason_codes, ())

    def test_ap2_cross_merchant_budget_solana_pay_and_haggle_blocks_violations(self) -> None:
        res = verify_ap2_cross_merchant_budget_solana_pay_and_haggle(
            budget_limit_minor=10000,
            enforcement_mode="independent_per_merchant_evaluator",
            operations=[
                {"verb": "authorize", "auth_id": "auth_m1", "amount_minor": 6000},
                {"verb": "authorize", "auth_id": "auth_m2", "amount_minor": 6000},
            ],
            solana_pay_settlement={
                "reference_pubkey": "ReusedRef111111111111111111111111111111111",
                "mandate_reference_pubkey": "ReusedRef111111111111111111111111111111111",
                "recorded_as_readonly_account": True,
                "onchain_recipient": "MerchantSolanaWallet1111111111111111111111",
                "mandate_recipient": "MerchantSolanaWallet1111111111111111111111",
                "onchain_amount_minor": 6000,
                "mandate_amount_minor": 6000,
                "onchain_spl_mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                "mandate_spl_mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            },
            seen_solana_references=["ReusedRef111111111111111111111111111111111"],
            haggle_session={
                "extension_uri": "ap2haggle/ap2/extensions/haggle/v0.1",
                "round_number": 3,
                "max_rounds": 4,
                "agreed_price_minor": 3500,
                "buyer_walk_away_minor": 4000,
                "seller_cost_floor_minor": 3000,
                "intermediate_offer_used_for_payment": True,
                "outcome_status": "accepted",
                "has_merchant_signed_cart_mandate": False,
            },
        )
        self.assertFalse(res.passed)
        self.assertIn("ap2_cross_merchant_independent_evaluator_overspend", res.reason_codes)
        self.assertIn("ap2_budget_authority_hold_exceeded_or_unauthorized", res.reason_codes)
        self.assertIn("ap2_solana_pay_reference_pubkey_reused_or_mismatched", res.reason_codes)
        self.assertIn("ap2_haggle_unsigned_offer_or_constraint_violation", res.reason_codes)

    def test_tau2_gold_replay_nl_judge_cost_and_sandbox_passes_valid(self) -> None:
        res = verify_tau2_gold_replay_nl_judge_cost_and_sandbox(
            golden_actions=[
                {
                    "action_id": "106_0",
                    "tool": "exchange_delivered_order_items",
                    "is_mutating": True,
                    "raised_exception": True,
                }
            ],
            predicted_db_matches_gold_db=True,
            reported_db_check=None,
            reward_breakdown_has_db_key=False,
            nl_assertions_count=3,
            nl_judge_verdicts_count=3,
            nl_judge_prompt_lines=[
                "user: I want to exchange my order items.",
                "tool: Insufficient gift card balance to pay for the price difference",
                "assistant: Your gift card balance is $17.00, which cannot cover the $21.10 difference.",
            ],
            agent_cost=0.042,
            user_cost=0.011,
            evaluator_cost=0.026,
            evaluator_cost_merged_into_agent_cost=False,
            telecom_grounding_tool_name="check_status_bar",
            sandbox_timeout_signal_sequence=["SIGTERM", "SIGKILL"],
            orphaned_socat_processes=0,
        )
        self.assertTrue(res.passed)
        self.assertTrue(res.db_check_withheld)
        self.assertEqual(res.reason_codes, ())

    def test_tau2_gold_replay_nl_judge_cost_and_sandbox_blocks_violations(self) -> None:
        res = verify_tau2_gold_replay_nl_judge_cost_and_sandbox(
            golden_actions=[
                {
                    "action_id": "106_0",
                    "tool": "exchange_delivered_order_items",
                    "is_mutating": True,
                    "raised_exception": True,
                }
            ],
            predicted_db_matches_gold_db=True,
            reported_db_check=True,
            reward_breakdown_has_db_key=True,
            nl_assertions_count=3,
            nl_judge_verdicts_count=0,
            nl_judge_prompt_lines=[
                "user: I want to exchange my order items.",
                "assistant: None",
                "tool: Insufficient gift card balance",
            ],
            agent_cost=0.042,
            user_cost=0.011,
            evaluator_cost=None,
            evaluator_cost_merged_into_agent_cost=False,
            telecom_grounding_tool_name="get_status_bar",
            sandbox_timeout_signal_sequence=["SIGKILL"],
            orphaned_socat_processes=2,
        )
        self.assertFalse(res.passed)
        self.assertIn("tau2_incomplete_gold_db_state_false_certification", res.reason_codes)
        self.assertIn("tau2_nl_judge_verdict_count_mismatch", res.reason_codes)
        self.assertIn("tau2_nl_judge_prompt_contains_contentless_none_turns", res.reason_codes)
        self.assertIn("tau2_evaluator_cost_discarded_or_merged_into_agent_cost", res.reason_codes)
        self.assertIn("tau2_telecom_unexposed_user_tool_grounding", res.reason_codes)
        self.assertIn("tau2_sandbox_timeout_sigkill_socat_proxy_leak", res.reason_codes)


if __name__ == "__main__":
    unittest.main()
