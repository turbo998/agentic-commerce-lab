"""Unit tests for Stage 200 (200-Stage Milestone!) guard module (`PM-01..PM-16`)."""

from __future__ import annotations

import base64
import hashlib
import unittest

from lab.x402_header_json_nonce_bazaar_ucp_projection_payment_max_lodging_cancel_tau2_guard import (
    compute_seller_resource_bound_nonce,
    evaluate_ucp_lodging_cancellation_schedule,
    validate_mcp_browser_automation_capability_contract,
    validate_mcp_channel_policy_per_send_attestation,
    validate_mcp_verifiable_tool_result,
    validate_tau2_airline_smallest_sufficient_gift_card,
    validate_tau2_telecom_uninvolved_customer_write_guard,
    validate_ucp_checkout_payment_maximum_and_order_summaries,
    validate_ucp_cross_boundary_carrier_projection,
    validate_ucp_lodging_dtc_signed_stay_quote,
    validate_ucp_payment_processing_policy_and_reporting,
    validate_ucp_request_time_capability_enforcement,
    validate_x402_bazaar_canonical_input_example,
    validate_x402_bazaar_origin_liveness_and_pruning,
    validate_x402_header_json_object_decode,
    validate_x402_offer_receipt_include_tx_hash_preservation,
    validate_x402_seller_issued_eip3009_nonce,
)


class TestStage200Guard(unittest.TestCase):
    def test_x402_header_json_nonce_bazaar_and_offer_receipt_guards(self) -> None:
        # PM-01: #3908 non-object JSON header decode
        for raw in ["[]", '"s"', "1", "null"]:
            enc = base64.b64encode(raw.encode("utf-8")).decode("ascii")
            res = validate_x402_header_json_object_decode(enc)
            self.assertFalse(res.allowed)
            self.assertEqual(res.decision_code, "X402_HEADER_JSON_NOT_OBJECT_REJECTED")
            self.assertEqual(res.http_status, 402)

        valid_enc = base64.b64encode(b'{"x402Version": 2, "payload": {}}').decode("ascii")
        self.assertTrue(validate_x402_header_json_object_decode(valid_enc).allowed)

        # PM-02: #3873 seller-issued 32-byte EIP-3009 resource-bound nonce
        nonce = compute_seller_resource_bound_nonce(
            secret="seller-hmac-key",
            method="GET",
            canonical_path_query="/check?target=A",
            resource_id="res_check_01",
            network="eip155:8453",
            asset="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            pay_to="0x1111111111111111111111111111111111111111",
            amount="10000",
            offer_id="offer_01",
            challenge="chal_99",
            expires_at=2000,
        )
        ok_nonce = validate_x402_seller_issued_eip3009_nonce(
            requires_resource_bound_nonce=True,
            client_supports_seller_nonce=True,
            signed_nonce=nonce,
            secret="seller-hmac-key",
            method="GET",
            canonical_path_query="/check?target=A",
            resource_id="res_check_01",
            network="eip155:8453",
            asset="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            pay_to="0x1111111111111111111111111111111111111111",
            amount="10000",
            offer_id="offer_01",
            challenge="chal_99",
            expires_at=2000,
            now_epoch=1950,
        )
        self.assertTrue(ok_nonce.allowed)

        mismatch_nonce = validate_x402_seller_issued_eip3009_nonce(
            requires_resource_bound_nonce=True,
            client_supports_seller_nonce=True,
            signed_nonce=nonce,
            secret="seller-hmac-key",
            method="GET",
            canonical_path_query="/check?target=B",
            resource_id="res_check_01",
            network="eip155:8453",
            asset="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            pay_to="0x1111111111111111111111111111111111111111",
            amount="10000",
            offer_id="offer_01",
            challenge="chal_99",
            expires_at=2000,
            now_epoch=1950,
        )
        self.assertFalse(mismatch_nonce.allowed)
        self.assertEqual(mismatch_nonce.decision_code, "X402_SELLER_NONCE_RESOURCE_MISMATCH_BLOCKED")

        # PM-03: #3844 Bazaar Cloudflare 530 dead origin pruning
        dead_530 = validate_x402_bazaar_origin_liveness_and_pruning(
            host="market.datapackvibe.com",
            probe_http_status=530,
            probe_body="error code: 1033",
            has_valid_402_shape=False,
            consecutive_non_402_checks=3,
        )
        self.assertFalse(dead_530.allowed)
        self.assertEqual(dead_530.decision_code, "X402_BAZAAR_DEAD_ORIGIN_530_PRUNED")

        # PM-04: #3841 duplicate alias in Bazaar input example
        dup_alias = validate_x402_bazaar_canonical_input_example(
            example_fields={"q": "hello", "query": "hello", "text": "hello world"},
            parameter_alias_groups=[["q", "query", "text"]],
        )
        self.assertFalse(dup_alias.allowed)
        self.assertEqual(dup_alias.decision_code, "X402_BAZAAR_INPUT_EXAMPLE_DUPLICATE_ALIAS_BLOCKED")

        # PM-05: #3824 offer-receipt includeTxHash preservation
        dropped_tx = validate_x402_offer_receipt_include_tx_hash_preservation(
            route_declaration={"includeTxHash": True},
            enriched_declaration={"info": {"offers": []}, "schema": {}},
            settlement_tx_hash="0xabc123",
            signed_receipt_payload={"transaction": None},
        )
        self.assertFalse(dropped_tx.allowed)
        self.assertEqual(dropped_tx.decision_code, "X402_OFFER_RECEIPT_INCLUDE_TX_HASH_DROPPED_BLOCKED")

    def test_ucp_projection_payment_max_processing_lodging_and_capability_guards(self) -> None:
        # PM-06: #827 cross-boundary projection contract
        bad_proj = validate_ucp_cross_boundary_carrier_projection(
            carrier_name="dev.ucp.shopping.risk_signals",
            persistence_sensitive=True,
            crosses_boundary=True,
            projection={
                "identity": "sig_session_01",
                "preserves": ["score"],
                "drops": ["raw_ip"],
                "on_unpreserved": "fail_closed",
                "reattest": "required",
            },
            carrier_present_at_target=True,
            freshly_reattested=False,
        )
        self.assertFalse(bad_proj.allowed)
        self.assertEqual(bad_proj.decision_code, "UCP_PROJECTION_UNPRESERVED_OR_REATTEST_REQUIRED_BLOCKED")

        # PM-07: #815 Checkout maximum_amount & Order summaries
        bad_final = validate_ucp_checkout_payment_maximum_and_order_summaries(
            checkout_totals=[{"type": "total", "amount": 5000, "amount_finality": "final"}],
            checkout_payment={"maximum_amount": 6000},
            order_payment={
                "maximum_amount": 6000,
                "instruments": [{"id": "pm_1", "type": "card", "display": "Visa 4242"}],
            },
        )
        self.assertFalse(bad_final.allowed)
        self.assertEqual(bad_final.decision_code, "UCP_CHECKOUT_FINALITY_MAXIMUM_AMOUNT_VIOLATION")

        ok_prov = validate_ucp_checkout_payment_maximum_and_order_summaries(
            checkout_totals=[{"type": "total", "amount": 5000, "amount_finality": "provisional"}],
            checkout_payment={"maximum_amount": 6000},
            order_payment={
                "maximum_amount": 6000,
                "instruments": [
                    {
                        "id": "pm_1",
                        "type": "card",
                        "display": "Visa 4242",
                        "authorized_amount": 5500,
                        "captured_amount": 5200,
                    }
                ],
            },
        )
        self.assertTrue(ok_prov.allowed)

        # PM-08: #820 payment processing policy & reporting
        bad_proc = validate_ucp_payment_processing_policy_and_reporting(
            complete_checkout_request={"capture_policy": "manual"},
            order_maximum_amount=6000,
            completed_checkout_policy="automatic",
            instrument_summary={"authorized_amount": 5500, "captured_amount": 5200},
            processing={"approvals": [], "attempts": []},
        )
        self.assertFalse(bad_proc.allowed)
        self.assertEqual(bad_proc.decision_code, "UCP_PAYMENT_PROCESSING_LEDGER_INVARIANT_VIOLATION")

        # PM-09: #807 deterministic lodging cancellation schedule
        schedule = {
            "anchor": "2026-12-22T15:00:00-05:00",
            "tiers": [
                {"until": "PT48H", "outcome": {"kind": "percentage", "buyer_bps": 10000}},
                {"until": "PT24H", "outcome": {"kind": "percentage", "buyer_bps": 5000}},
            ],
            "after_last_tier": {
                "kind": "unit_deduction",
                "penalty": {"measure": {"value": 1, "unit": "night", "display_text": "night"}},
            },
        }
        # Exact boundary at anchor - 48h (`2026-12-20T15:00:00-05:00`) advances to tier[1]
        exact_cutoff = evaluate_ucp_lodging_cancellation_schedule(
            schedule=schedule,
            at="2026-12-20T15:00:00-05:00",
        )
        self.assertTrue(exact_cutoff.allowed)
        self.assertEqual(exact_cutoff.details["selected_stage"], "tier[1]")

        # Equivalent duplicate cutoffs P1D and PT24H must fail
        dup_tier = evaluate_ucp_lodging_cancellation_schedule(
            schedule={
                "anchor": "2026-12-22T15:00:00-05:00",
                "tiers": [
                    {"until": "P1D", "outcome": {"kind": "percentage", "buyer_bps": 10000}},
                    {"until": "PT24H", "outcome": {"kind": "percentage", "buyer_bps": 5000}},
                ],
                "after_last_tier": {"kind": "percentage", "buyer_bps": 0},
            },
            at="2026-12-19T15:00:00-05:00",
        )
        self.assertFalse(dup_tier.allowed)

        # PM-10: #805 request-time capability enforcement
        incompat = validate_ucp_request_time_capability_enforcement(
            required_capability="dev.ucp.shopping.cart",
            platform_declared_capabilities={"dev.ucp.shopping.checkout": ["2026-08-25"]},
            business_supported_capabilities={"dev.ucp.shopping.cart": ["2026-08-25"]},
            has_signature_input_header=False,
        )
        self.assertFalse(incompat.allowed)
        self.assertEqual(incompat.decision_code, "UCP_CAPABILITIES_INCOMPATIBLE_OPERATION_REJECTED")

        # PM-11: #986 Lodging DTC origin-minted stay.id & signed quote
        unsigned_dtc = validate_ucp_lodging_dtc_signed_stay_quote(
            business_origin="https://hemmabo.se",
            stay_origin="https://hemmabo.se",
            published_key_ids={"key_2026_01"},
            quote_key_id="key_2026_01",
            quote_signature_valid=False,
            quote_expires_at=2000,
            now_epoch=1900,
            stay_id="stay_hemma_99",
        )
        self.assertFalse(unsigned_dtc.allowed)
        self.assertEqual(unsigned_dtc.decision_code, "UCP_LODGING_DTC_UNSIGNED_OR_EXPIRED_QUOTE_BLOCKED")

    def test_mcp_verifiable_channel_browser_and_tau2_guards(self) -> None:
        # PM-12: #3354 Verifiable MCP tool results
        bad_proof = validate_mcp_verifiable_tool_result(
            expected_program_digest="sha256:prog_1",
            canonical_input_digest="sha256:in_1",
            canonical_output_digest="sha256:out_1",
            expected_nonce="nonce_1",
            verifiable_meta={
                "proof_type": "tee_attestation",
                "program_digest": "sha256:prog_1",
                "input_digest": "sha256:in_1",
                "output_digest": "sha256:out_tampered",
                "freshness_nonce": "nonce_1",
                "cryptographic_proof_valid": True,
            },
        )
        self.assertFalse(bad_proof.allowed)
        self.assertEqual(bad_proof.decision_code, "MCP_VERIFIABLE_TOOL_RESULT_PROOF_INVALID")

        # PM-13: #3337 Channel-policy per-send attestation
        msg = "Approve wire transfer #402"
        ok_chan = validate_mcp_channel_policy_per_send_attestation(
            message_body=msg,
            target_channel_id="slack:finance-approvals",
            attestation={
                "channel_id": "slack:finance-approvals",
                "policy_id": "pol_fin_v1",
                "recipient_scope_allowed": True,
                "dlp_redaction_passed": True,
                "body_sha256": hashlib.sha256(msg.encode("utf-8")).hexdigest(),
            },
        )
        self.assertTrue(ok_chan.allowed)

        # PM-14: #3305 browser-automation capability safety invariants
        bad_browser = validate_mcp_browser_automation_capability_contract(
            advertised_invariants=["origin_scoped_credentials", "verified_actions"],
            is_mutating_action=True,
            has_before_after_state_evidence=True,
        )
        self.assertFalse(bad_browser.allowed)
        self.assertEqual(bad_browser.decision_code, "MCP_BROWSER_AUTOMATION_SAFETY_INVARIANT_MISSING")

        # PM-15: tau2 #459 uninvolved customer line suspension
        collateral_write = validate_tau2_telecom_uninvolved_customer_write_guard(
            authorized_customer_ids={"C2002"},
            authorized_line_ids={"L2002"},
            write_tool_calls=[
                {"tool": "suspend_line", "customer_id": "C1001", "line_id": "L1001"},
            ],
            env_assertion_passed=True,
        )
        self.assertFalse(collateral_write.allowed)
        self.assertEqual(collateral_write.decision_code, "TAU2_UNINVOLVED_CUSTOMER_WRITE_MUTATION_BLOCKED")
        self.assertEqual(collateral_write.details["reward"], 0.0)

        # PM-16: tau2 #664 airline smallest sufficient gift card ($157, $113, $6 for $59 change -> $113)
        cards = [
            {"id": "gift_card_157", "balance": 157},
            {"id": "gift_card_6276644", "balance": 113},
            {"id": "gift_card_6", "balance": 6},
        ]
        bad_card = validate_tau2_airline_smallest_sufficient_gift_card(
            gift_cards=cards,
            required_amount=59,
            selected_payment_id="gift_card_6",
        )
        self.assertFalse(bad_card.allowed)

        ok_card = validate_tau2_airline_smallest_sufficient_gift_card(
            gift_cards=cards,
            required_amount=59,
            selected_payment_id="gift_card_6276644",
        )
        self.assertTrue(ok_card.allowed)


if __name__ == "__main__":
    unittest.main()
