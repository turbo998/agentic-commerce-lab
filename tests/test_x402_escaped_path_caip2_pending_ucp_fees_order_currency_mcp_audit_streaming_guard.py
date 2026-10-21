"""Unit tests for Stage 138 guardrails."""

from __future__ import annotations

import unittest

from lab.x402_escaped_path_caip2_pending_ucp_fees_order_currency_mcp_audit_streaming_guard import (
    compute_audit_record_hash,
    evaluate_mcp_audit_chain_streaming_and_tau2_guard,
    evaluate_ucp_itemized_fees_order_currency_and_update_id_guard,
    evaluate_x402_escaped_path_and_caip2_guard,
    evaluate_x402_settlement_pending_and_fastify_buffer_guard,
)


class Stage138GuardTests(unittest.TestCase):
    def test_x402_escaped_path_caip2_and_settlement_guards(self) -> None:
        ok_route = evaluate_x402_escaped_path_and_caip2_guard(
            protected_routes=("/api/premium",),
            request_raw_path="/api%2Fpremium",
            network_caip2="eip155:8453",
        )
        self.assertTrue(ok_route.allowed)
        self.assertTrue(ok_route.metadata["requires_payment"])

        bad_caip2 = evaluate_x402_escaped_path_and_caip2_guard(
            protected_routes=("/api/premium",),
            request_raw_path="/api/premium",
            network_caip2="eip155:8453abc",
        )
        self.assertFalse(bad_caip2.allowed)
        self.assertEqual(bad_caip2.decision_code, "X402_MALFORMED_CAIP2_CHAIN_ID_REJECTED")

        ok_settle = evaluate_x402_settlement_pending_and_fastify_buffer_guard(
            settlement_status="settlement_pending",
            tx_hash="0xabc123",
            reconciled_on_chain=True,
            client_mapped_status="settlement_pending",
            fastify_buffered_raw_consumed=True,
            error_pass_replayed_private_body=False,
            jws_header_kid="kid-1",
            jws_header_jwk={"kty": "OKP", "crv": "Ed25519", "x": "pub-1"},
            trusted_kids={"kid-1": "pub-1"},
            bare_dollar_price=True,
            selected_arbitrum_asset="USDC",
            python_mcp_paid_tool_handled=True,
            python_mcp_corrective_retries=1,
            eip6492_factory_allowlisted=True,
            gas_sponsor_rpc_capable=True,
        )
        self.assertTrue(ok_settle.allowed)

        bad_pending = evaluate_x402_settlement_pending_and_fastify_buffer_guard(
            settlement_status="settlement_pending",
            tx_hash="0xabc123",
            reconciled_on_chain=True,
            client_mapped_status="settle_failed",
            fastify_buffered_raw_consumed=True,
            error_pass_replayed_private_body=False,
            jws_header_kid="kid-1",
            jws_header_jwk=None,
            trusted_kids={"kid-1": "pub-1"},
            bare_dollar_price=True,
            selected_arbitrum_asset="USDC",
            python_mcp_paid_tool_handled=True,
            python_mcp_corrective_retries=0,
            eip6492_factory_allowlisted=True,
            gas_sponsor_rpc_capable=True,
        )
        self.assertFalse(bad_pending.allowed)
        self.assertEqual(bad_pending.decision_code, "X402_CLIENT_PENDING_MISCLASSIFIED_AS_SETTLE_FAILED")

    def test_ucp_fees_currency_and_update_id_guard(self) -> None:
        ok = evaluate_ucp_itemized_fees_order_currency_and_update_id_guard(
            order_currency="USD",
            line_item_currencies=("USD", "USD"),
            itemized_fees=({"type": "service", "amount_minor": 150}, {"type": "recycling", "amount_minor": 50}),
            declared_fees_total_minor=200,
            is_update_request=True,
            payload_contains_checkout_id=False,
            error_code=None,
            error_severity=None,
            schema_extends_parents=("dev.ucp.shopping.checkout", "dev.ucp.common.fulfillment"),
        )
        self.assertTrue(ok.allowed)

        bad_id = evaluate_ucp_itemized_fees_order_currency_and_update_id_guard(
            order_currency="USD",
            line_item_currencies=("USD",),
            itemized_fees=({"type": "service", "amount_minor": 100},),
            declared_fees_total_minor=100,
            is_update_request=True,
            payload_contains_checkout_id=True,
            error_code=None,
            error_severity=None,
            schema_extends_parents=("dev.ucp.shopping.checkout",),
        )
        self.assertFalse(bad_id.allowed)
        self.assertEqual(bad_id.decision_code, "UCP_UPDATE_CHECKOUT_ID_DEPRECATED_MUST_OMIT")

    def test_mcp_audit_chain_streaming_and_tau2_guard(self) -> None:
        h0 = "0" * 64
        p1 = '{"tool":"checkout.complete","amount":1200}'
        h1 = compute_audit_record_hash(h0, p1)
        chain = ({"prev_hash": h0, "canonical_payload": p1, "record_hash": h1},)

        ok = evaluate_mcp_audit_chain_streaming_and_tau2_guard(
            audit_chain=chain,
            header_mismatch_error_code=-32020,
            side_effect_triggered_on_partial_chunk=False,
            final_call_tool_result_received=True,
            mcp_param_header_sent=True,
            input_schema_obtained=True,
            reward_basis_includes_nl_assertion=True,
            nl_assertion_evaluator_executed=True,
            livekit_tick_blocking=False,
            barge_in_agent_yielded_audio=True,
        )
        self.assertTrue(ok.allowed)

        tampered = evaluate_mcp_audit_chain_streaming_and_tau2_guard(
            audit_chain=({"prev_hash": h0, "canonical_payload": p1, "record_hash": "f" * 64},),
            header_mismatch_error_code=-32020,
            side_effect_triggered_on_partial_chunk=False,
            final_call_tool_result_received=True,
            mcp_param_header_sent=False,
            input_schema_obtained=False,
            reward_basis_includes_nl_assertion=True,
            nl_assertion_evaluator_executed=True,
            livekit_tick_blocking=False,
            barge_in_agent_yielded_audio=True,
        )
        self.assertFalse(tampered.allowed)
        self.assertEqual(tampered.decision_code, "MCP_SEP3004_AUDIT_HASH_CHAIN_TAMPERED")


if __name__ == "__main__":
    unittest.main()
