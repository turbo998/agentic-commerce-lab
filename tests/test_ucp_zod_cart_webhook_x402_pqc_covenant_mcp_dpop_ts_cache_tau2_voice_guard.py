"""Unit tests for Stage 216 deterministic guard module (`PR-01..PR-16`)."""

from __future__ import annotations

import unittest

from lab.ucp_zod_cart_webhook_x402_pqc_covenant_mcp_dpop_ts_cache_tau2_voice_guard import (
    SCENARIO_EVALUATORS,
    _canonical_jcs_sha256,
    evaluate_stage216_scenario,
)


def build_valid_payloads() -> dict[str, dict]:
    receipt_body = {
        "network": "eip155:8453",
        "payer": "eip155:8453:0x1111111111111111111111111111111111111111",
        "payee": "eip155:8453:0x2222222222222222222222222222222222222222",
        "amount": "250000",
        "tx_hash": "0xabc123def456",
    }
    return {
        "PR-01": {
            "price": {"amount": 2500, "currency": "USD"},
            "signing_keys": [{"kid": "kid_thumb_01", "kty": "EC", "crv": "P-256", "x": "x_b64", "y": "y_b64"}],
            "unreachable_profile_urls": [],
        },
        "PR-02": {
            "cart_items": [{"id": "sku_01", "quantity": 2}],
            "checkout_items": [{"id": "sku_01", "quantity": 2}],
            "first_conversion_checkout_id": "chk_cart_01",
            "second_conversion_checkout_id": "chk_cart_01",
            "cart_discount_codes": ["SAVE10"],
            "checkout_discount_codes": ["SAVE10"],
            "supports_multi_group": False,
            "fulfillment_methods": [{"type": "shipping", "groups": [{"id": "grp_1", "options": []}]}],
        },
        "PR-03": {
            "headers": {
                "UCP-Agent": "merchant/1.0",
                "Signature": "sig1=:dGVzdA==:",
                "Signature-Input": 'sig1=("webhook-id" "webhook-timestamp" "x-event-type" "content-digest")',
                "Content-Digest": "sha-256=:abcd:",
                "Webhook-Id": "wh_01",
                "Webhook-Timestamp": "1792800000",
                "X-Event-Type": "order.created",
            },
            "signed_components": ["webhook-id", "webhook-timestamp", "x-event-type", "content-digest"],
            "signing_key_alg": "ES256",
            "kid_matches_rfc7638_thumbprint": True,
            "body": {"id": "ord_901", "status": "confirmed"},
            "last_delivery_status": 503,
            "retry_attempted": True,
            "reused_webhook_id_and_timestamp": True,
        },
        "PR-04": {
            "error_response": {
                "status": "error",
                "code": "IDEMPOTENCY_CONFLICT",
                "messages": [{"type": "error", "content": "Idempotency key reused with different parameters"}],
            },
            "discovery_cache_control": "public, max-age=3600",
            "checkout_ucp_envelope": {"version": "2026-04-08", "capabilities": [], "payment_handlers": {}},
            "a2a_task_state": "working",
            "a2a_active_task_id_after_turn": "task_a2a_88",
        },
        "PR-05": {
            "receipt_body": receipt_body,
            "jcs_sha256": _canonical_jcs_sha256(receipt_body),
            "pqc_witness": {
                "alg": "ML-DSA-65",
                "fips": "FIPS-204",
                "epoch_key_chain_verified": True,
                "tx_hash": "0xabc123def456",
                "log_index": 3,
            },
        },
        "PR-06": {
            "asset_symbol": "USDC",
            "amount_micro_usdc": 2500,
            "payer": "0x1111111111111111111111111111111111111111",
            "pay_to": "0x2222222222222222222222222222222222222222",
            "payee_daily_settlements": 42,
            "xrpl_upto_channel": {
                "escrowed_drops": 5000000,
                "settled_drops": 3200000,
                "claim_signature_valid": True,
            },
        },
        "PR-07": {
            "status_code": 402,
            "accepts": [{"scheme": "exact", "network": "eip155:8453"}],
            "vendor_header_masks_document": False,
            "preflight_attempted_sign_or_settle": False,
            "cbor_int_metadata_values": [0, 42, 18446744073709551615],
        },
        "PR-08": {
            "server_implements_grant": True,
            "client_registered_for_grant": False,
            "oauth_error_code": "unauthorized_client",
            "dpop_signing_alg_values_supported": ["ES256"],
            "dpop_proof_header_sent": True,
            "dpop_proof_alg": "ES256",
        },
        "PR-09": {
            "previous_session_tools": ["legacy_quote", "checkout_pay"],
            "updated_session_tools": ["checkout_pay", "order_track"],
            "active_group_tools_after_reregister": ["checkout_pay", "order_track"],
            "ui_bridge_initialized_before_consume": True,
            "notification_source_is_parent_window": True,
            "tool_result_read_from_notification_params": True,
        },
        "PR-10": {
            "stdio_buffering_strategy": "list_append_join_on_newline",
            "sse_shares_module_header_list": False,
            "leaked_headers_across_responses": [],
            "line_bytes_tested": 8388608,
        },
        "PR-11": {
            "outbound_request": {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            "header_mismatch_retries": 1,
            "explicit_null_structured_content_validated": True,
            "jsonrpc_error_recorded_on_otel_span": True,
        },
        "PR-12": {
            "provider_has_scope_for_refresh": True,
            "refresh_request_has_scope": True,
            "output_schema_root_ref_target_type": "object",
            "structured_content_wrapped_in_result": False,
        },
        "PR-13": {
            "key_generation_before": 4,
            "key_generation_after": 4,
            "connection_generation_before": 2,
            "connection_generation_after": 2,
            "used_cached_snapshot": True,
            "initialized_handshake_timeout_ms": 15000,
        },
        "PR-14": {
            "include_context": "thisServer",
            "client_declares_sampling_context": True,
            "plain_mcp_headers": {"Mcp-Name": "stripe-checkout-server", "Mcp-Param-Region": "us-east-1"},
            "blocked_on_unread_post_reply_body": False,
        },
        "PR-15": {
            "voice_user_simulator_version": "v1.0",
            "voice_user_simulator_decision_model": "gpt-4.1-2025-04-14",
            "voice_simulator_git_tag": "voice-user-sim-v1.0",
            "domain": "banking_knowledge",
            "retrieval_config_id": "hybrid_rerank_top12",
            "corpus_document_count": 698,
        },
        "PR-16": {
            "metric_groups_computed": [
                "reliability_consistency",
                "interaction_efficiency",
                "policy_tool_governance",
                "tool_call_accuracy",
                "first_call_resolution",
                "state_based_metrics",
            ],
            "environment_damage_rate": 0.0,
            "custom_model_litellm_pricing_mapped": True,
            "backend_and_tts_smoke_gate_passed": True,
            "fcr_pct": 88.5,
        },
    }


def build_adversarial_payloads() -> dict[str, dict]:
    valid = build_valid_payloads()
    return {
        "PR-01": {**valid["PR-01"], "price": {"amount": 9.99, "currency": "usd"}},
        "PR-02": {**valid["PR-02"], "fulfillment_methods": [{"type": "shipping", "groups": []}]},
        "PR-03": {**valid["PR-03"], "body": {"event_type": "order.created", "order": {"id": "ord_901"}}},
        "PR-04": {**valid["PR-04"], "a2a_active_task_id_after_turn": None},
        "PR-05": {**valid["PR-05"], "pqc_witness": {**valid["PR-05"]["pqc_witness"], "epoch_key_chain_verified": False}},
        "PR-06": {**valid["PR-06"], "amount_micro_usdc": 500},
        "PR-07": {**valid["PR-07"], "cbor_int_metadata_values": [-1]},
        "PR-08": {**valid["PR-08"], "oauth_error_code": "invalid_request"},
        "PR-09": {**valid["PR-09"], "active_group_tools_after_reregister": ["legacy_quote", "checkout_pay", "order_track"]},
        "PR-10": {**valid["PR-10"], "sse_shares_module_header_list": True},
        "PR-11": {**valid["PR-11"], "outbound_request": {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}},
        "PR-12": {**valid["PR-12"], "structured_content_wrapped_in_result": True},
        "PR-13": {**valid["PR-13"], "key_generation_after": 5, "used_cached_snapshot": True},
        "PR-14": {**valid["PR-14"], "client_declares_sampling_context": False},
        "PR-15": {**valid["PR-15"], "voice_user_simulator_version": "gpt-4.1-2025-04-14"},
        "PR-16": {**valid["PR-16"], "environment_damage_rate": 0.12},
    }


class TestStage216Guard(unittest.TestCase):
    def test_all_16_valid_scenarios_pass(self) -> None:
        valid = build_valid_payloads()
        self.assertEqual(len(valid), 16)
        for scenario_id, payload in valid.items():
            verdict = evaluate_stage216_scenario(scenario_id, payload)
            self.assertTrue(verdict.passed, f"{scenario_id} should pass: {verdict}")
            self.assertEqual(verdict.action, "Act automatically")

    def test_all_16_adversarial_scenarios_blocked(self) -> None:
        adversarial = build_adversarial_payloads()
        self.assertEqual(len(adversarial), 16)
        for scenario_id, payload in adversarial.items():
            verdict = evaluate_stage216_scenario(scenario_id, payload)
            self.assertFalse(verdict.passed, f"{scenario_id} should be blocked: {verdict}")
            self.assertEqual(verdict.action, "Send to a human")

    def test_evaluator_registry_completeness(self) -> None:
        expected = [f"PR-{i:02d}" for i in range(1, 17)]
        self.assertEqual(list(SCENARIO_EVALUATORS.keys()), expected)


if __name__ == "__main__":
    unittest.main()
