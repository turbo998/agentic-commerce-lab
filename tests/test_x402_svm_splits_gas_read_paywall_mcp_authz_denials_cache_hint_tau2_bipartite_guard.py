"""Unit tests for Stage 192 guardrails: x402 SVM multi-payee splits, gas-sponsoring chain-read warning, paywall auto-detect & create_headers Mapping, MCP SEP-2643 structured authorization denials & SEP-2419 cache_hint, and Sierra tau2-bench maximum bipartite action matching."""

from __future__ import annotations

from types import MappingProxyType
import unittest

from lab.x402_svm_splits_gas_read_paywall_mcp_authz_denials_cache_hint_tau2_bipartite_guard import (
    evaluate_mcp_sep2643_authz_denial_and_sep2419_cache_hint_guard,
    evaluate_tau2_bipartite_action_matching,
    evaluate_x402_gas_read_paywall_and_headers_guard,
    evaluate_x402_svm_multi_payee_splits_guard,
)


class Stage192GuardTests(unittest.TestCase):
    def test_x402_svm_multi_payee_splits_invariants(self) -> None:
        # 1. Valid 1-split payment with primary overpayment tolerance and sponsored CreateIdempotent
        ok = evaluate_x402_svm_multi_payee_splits_guard(
            total_amount_str="1050000",
            primary_pay_to="2wKupLR9q6wXYppw8Gr2NvWxKBUqm4PPJKkQfoxHDBg4",
            primary_ata_creation_required=False,
            splits=[
                {
                    "payTo": "3pF8Kg2aHbNvJkLMwEqR7YtDxZ5sGhJn4UV6mWcXrT9A",
                    "amount": "50000",
                    "memo": "platform fee",
                    "ataCreationRequired": True,
                }
            ],
            sponsor_max_splits=8,
            sponsor_ata_creation_sponsored=True,
            observed_transfers=[
                {
                    "payTo": "2wKupLR9q6wXYppw8Gr2NvWxKBUqm4PPJKkQfoxHDBg4",
                    "amount": 1000005,  # primary tolerates overpayment
                },
                {
                    "payTo": "3pF8Kg2aHbNvJkLMwEqR7YtDxZ5sGhJn4UV6mWcXrT9A",
                    "amount": 50000,  # split must be exact
                },
            ],
            observed_ata_creations=[
                {
                    "owner": "3pF8Kg2aHbNvJkLMwEqR7YtDxZ5sGhJn4UV6mWcXrT9A",
                    "instruction": "CreateIdempotent",
                    "ata_already_exists": False,
                }
            ],
            decompiled_instruction_count=6,  # 3 + N(1) + K(1) = 5 .. 9
            client_consented_splits=[
                {
                    "payTo": "3pF8Kg2aHbNvJkLMwEqR7YtDxZ5sGhJn4UV6mWcXrT9A",
                    "amount": "50000",
                    "memo": "platform fee",
                }
            ],
        )
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.primary_remainder, 1000000)
        self.assertEqual(ok.path1_min_instructions, 5)
        self.assertEqual(ok.path1_max_instructions, 9)

        # 2. Reject split overpayment (only primary leg tolerates overpayment)
        split_overpay = evaluate_x402_svm_multi_payee_splits_guard(
            total_amount_str="1050000",
            primary_pay_to="MerchantA",
            primary_ata_creation_required=False,
            splits=[{"payTo": "PlatformB", "amount": "50000"}],
            sponsor_max_splits=8,
            sponsor_ata_creation_sponsored=False,
            observed_transfers=[
                {"payTo": "MerchantA", "amount": 1000000},
                {"payTo": "PlatformB", "amount": 50001},
            ],
            observed_ata_creations=[],
            decompiled_instruction_count=5,
        )
        self.assertFalse(split_overpay.allowed)
        self.assertEqual(split_overpay.decision_code, "split_leg_unmatched")

        # 3. Reject when splits consume the entire amount (primary remainder <= 0)
        zero_rem = evaluate_x402_svm_multi_payee_splits_guard(
            total_amount_str="50000",
            primary_pay_to="MerchantA",
            primary_ata_creation_required=False,
            splits=[{"payTo": "PlatformB", "amount": "50000"}],
            sponsor_max_splits=8,
            sponsor_ata_creation_sponsored=False,
            observed_transfers=[],
            observed_ata_creations=[],
            decompiled_instruction_count=4,
        )
        self.assertFalse(zero_rem.allowed)
        self.assertEqual(zero_rem.decision_code, "split_remainder_not_positive")

        # 4. Reject when sponsor does not advertise maxSplits (absent => 0) or ataCreationSponsored
        unadvertised_splits = evaluate_x402_svm_multi_payee_splits_guard(
            total_amount_str="1050000",
            primary_pay_to="MerchantA",
            primary_ata_creation_required=False,
            splits=[{"payTo": "PlatformB", "amount": "50000"}],
            sponsor_max_splits=None,
            sponsor_ata_creation_sponsored=None,
            observed_transfers=[],
            observed_ata_creations=[],
            decompiled_instruction_count=4,
        )
        self.assertFalse(unadvertised_splits.allowed)
        self.assertEqual(unadvertised_splits.decision_code, "split_count_exceeded")

        # 5. Reject non-idempotent Create instruction or unmarked recipient ATA creation
        bad_ata = evaluate_x402_svm_multi_payee_splits_guard(
            total_amount_str="1050000",
            primary_pay_to="MerchantA",
            primary_ata_creation_required=False,
            splits=[
                {
                    "payTo": "PlatformB",
                    "amount": "50000",
                    "ataCreationRequired": True,
                }
            ],
            sponsor_max_splits=8,
            sponsor_ata_creation_sponsored=True,
            observed_transfers=[
                {"payTo": "MerchantA", "amount": 1000000},
                {"payTo": "PlatformB", "amount": 50000},
            ],
            observed_ata_creations=[
                {
                    "owner": "PlatformB",
                    "instruction": "Create",  # Must be CreateIdempotent
                    "ata_already_exists": False,
                }
            ],
            decompiled_instruction_count=6,
        )
        self.assertFalse(bad_ata.allowed)
        self.assertEqual(bad_ata.decision_code, "split_ata_creation_not_authorized")

    def test_x402_gas_read_paywall_and_headers(self) -> None:
        warned: set[str] = set()
        # Signer without read_contract warns once across 2 calls and skips extension
        res1 = evaluate_x402_gas_read_paywall_and_headers_guard(
            network="eip155:84532",
            advertised_sponsoring_key="eip2612GasSponsoring",
            signer_can_read_contract=False,
            signer_can_sign_transaction=True,
            warned_networks=warned,
            invocation_count=2,
            accepts=[
                {"scheme": "upto", "network": "eip155:8453"},
                {"scheme": "exact", "network": "eip155:8453"},
            ],
            create_headers_result={"verify": MappingProxyType({"Authorization": "Bearer tok"})},
        )
        self.assertTrue(res1.allowed)
        self.assertEqual(res1.warning_count_for_network, 1)
        self.assertFalse(res1.extension_signed)
        # accepts[0] is upto -> fallback static HTML even though accepts[1] is exact EVM
        self.assertEqual(res1.rendered_paywall_kind, "fallback_static_html")

        # Signer with read_contract but without sign_transaction stays silent on erc20ApprovalGasSponsoring
        warned2: set[str] = set()
        res2 = evaluate_x402_gas_read_paywall_and_headers_guard(
            network="eip155:84532",
            advertised_sponsoring_key="erc20ApprovalGasSponsoring",
            signer_can_read_contract=True,
            signer_can_sign_transaction=False,
            warned_networks=warned2,
            accepts=[{"scheme": "exact", "network": "eip155:8453"}],
        )
        self.assertEqual(res2.warning_count_for_network, 0)
        self.assertFalse(res2.extension_signed)
        self.assertEqual(res2.rendered_paywall_kind, "paywall_eip155")

        # Flat create_headers dict is rejected
        flat_err = evaluate_x402_gas_read_paywall_and_headers_guard(
            network="eip155:84532",
            advertised_sponsoring_key=None,
            signer_can_read_contract=True,
            signer_can_sign_transaction=True,
            warned_networks=set(),
            create_headers_result={"Authorization": "Bearer flat"},
        )
        self.assertFalse(flat_err.allowed)
        self.assertEqual(flat_err.decision_code, "create_headers_flat_dict_rejected")

    def test_mcp_sep2643_authz_denials_and_sep2419_cache_hint(self) -> None:
        # 1. Valid stdio RAR authorization_remediation for single-use payment + cache_hint="no-cache"
        ok = evaluate_mcp_sep2643_authz_denial_and_sep2419_cache_hint_guard(
            partial_execution=False,
            envelope={
                "reason": "insufficient_authorization",
                "remediation": "available",
                "authorizationContextId": "authzctx_c17a3f5e",
                "remediationHints": [
                    {
                        "type": "authorization_remediation",
                        "authorization_details": [{"type": "payment_initiation"}],
                    }
                ],
            },
            single_use_credential=True,
            result_meta={"cache_hint": "no-cache", "traceparent": "00-abc-def-01"},
        )
        self.assertTrue(ok.allowed)
        self.assertFalse(ok.should_cache_result)
        self.assertEqual(ok.forwarded_meta_keys, ("traceparent",))

        # 2. Reject single-use RAR hint that includes authorization_reference
        bad_ref = evaluate_mcp_sep2643_authz_denial_and_sep2419_cache_hint_guard(
            envelope={
                "reason": "insufficient_authorization",
                "remediation": "available",
                "remediationHints": [
                    {
                        "type": "authorization_remediation",
                        "authorization_details": [{"type": "payment_initiation"}],
                        "authorization_reference": "ref_reusable_123",
                    }
                ],
            },
            single_use_credential=True,
        )
        self.assertFalse(bad_ref.allowed)
        self.assertEqual(
            bad_ref.decision_code, "mcp_sep2643_single_use_rar_must_omit_reference"
        )

        # 3. Reject marking remediation="unavailable" when server has URL/task remedy but client lacks capabilities
        bad_unavail = evaluate_mcp_sep2643_authz_denial_and_sep2419_cache_hint_guard(
            envelope={
                "reason": "insufficient_authorization",
                "remediation": "unavailable",
            },
            server_has_interactive_or_task_remedy=True,
            client_supports_url_elicitation=False,
            client_supports_tasks=False,
        )
        self.assertFalse(bad_unavail.allowed)
        self.assertEqual(
            bad_unavail.decision_code,
            "mcp_sep2643_capability_gated_remedy_marked_unavailable",
        )

    def test_tau2_bipartite_action_matching(self) -> None:
        # 1. One call cannot satisfy 3 repeated gold actions (PR #665)
        repeated_gold = [
            {"name": "request_human_agent_transfer", "requestor": "user", "compare_args": []},
            {"name": "request_human_agent_transfer", "requestor": "user", "compare_args": []},
            {"name": "request_human_agent_transfer", "requestor": "user", "compare_args": []},
            {"name": "transfer_to_human_agents", "requestor": "assistant", "compare_args": []},
        ]
        single_call_res = evaluate_tau2_bipartite_action_matching(
            predicted_tool_calls=[
                {"name": "request_human_agent_transfer", "requestor": "user", "arguments": {}},
                {"name": "transfer_to_human_agents", "requestor": "assistant", "arguments": {"summary": "x"}},
            ],
            golden_actions=repeated_gold,
        )
        self.assertFalse(single_call_res.allowed)
        self.assertEqual(single_call_res.gold_matches, (True, False, False, True))

        # 2. Augmenting-path reassignment assigns specific call to constrained gold action
        reassigned = evaluate_tau2_bipartite_action_matching(
            predicted_tool_calls=[
                {"name": "lookup", "requestor": "assistant", "arguments": {"id": "b"}},
                {"name": "lookup", "requestor": "assistant", "arguments": {"id": "z"}},
            ],
            golden_actions=[
                {"name": "lookup", "requestor": "assistant", "arguments": {"id": "a"}, "compare_args": []},
                {"name": "lookup", "requestor": "assistant", "arguments": {"id": "b"}, "compare_args": ["id"]},
            ],
        )
        self.assertTrue(reassigned.allowed)
        self.assertEqual(reassigned.gold_matches, (True, True))


if __name__ == "__main__":
    unittest.main()
