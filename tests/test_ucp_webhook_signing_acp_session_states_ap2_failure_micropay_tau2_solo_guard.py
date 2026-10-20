from __future__ import annotations

import hashlib
import hmac
import unittest

from lab.ucp_webhook_signing_acp_session_states_ap2_failure_micropay_tau2_solo_guard import (
    verify_acp_protocol_extensions_offer_expiry_webhook_hmac_and_mcp_binding,
    verify_ap2_failure_response_payment_receipt_json_schema_and_micropayment,
    verify_tau2_live_interruption_hallucination_retry_pydantic_coercion_and_metrics,
    verify_ucp_webhook_signing_map_order_request_constraints_and_sale_basis,
)


class TestStage70Guards(unittest.TestCase):
    def test_ucp_webhook_signing_map_order_constraints_and_sale_basis_passes(self) -> None:
        res = verify_ucp_webhook_signing_map_order_request_constraints_and_sale_basis(
            {
                "order_webhook": {
                    "headers": {
                        "Webhook-Id": "evt_ord_001",
                        "Webhook-Timestamp": "1792512000",
                        "UCP-Agent": 'profile="https://merchant.example/profile.json"',
                    },
                    "covered_components": [
                        "@method",
                        "@authority",
                        "@path",
                        "content-digest",
                        "ucp-agent",
                        "webhook-id",
                        "webhook-timestamp",
                    ],
                    "body": {"id": "ord_991", "status": "fulfilled"},
                },
                "profile": {
                    "ucp": {
                        "version": "2026-08-25",
                        "map_order": {
                            "payment_handlers": ["com.stripe.spt", "com.google.pay"]
                        },
                        "capabilities": {
                            "dev.ucp.shopping.checkout": [
                                {
                                    "version": "2026-08-25",
                                    "schema": "https://ucp.dev/schemas/shopping/checkout.json",
                                }
                            ]
                        },
                    }
                },
                "direction": "response",
                "available_instrument_request_constraints": {
                    "path": "$.payment.instruments[?@.handler_id=='h1' && @.type=='card']",
                    "required": ["billing_address"],
                },
                "response_request_constraints": {
                    "required": ["fulfillment_address"],
                    "properties": {
                        "quantity": {"const": 1500},
                        "shipping_speed": {"enum": ["standard", "express"]},
                    },
                },
                "next_request_object": {
                    "fulfillment_address": "addr_1",
                    "quantity": 1500,
                    "shipping_speed": "express",
                },
                "line_item": {
                    "quantity": 1500,
                    "quantity_unit": {"unit": "kg", "scale": 3},
                    "expected_decimal_quantity": 1.5,
                },
                "mcp_error": {"type": "rate_limit_exceeded", "code": -32004},
                "context_location": "store_default_01",
                "authoritative_fulfills_to": "store_pickup_09",
                "resolved_store_location": "store_pickup_09",
            }
        )
        self.assertTrue(res.allowed)
        self.assertEqual(
            res.reason_code,
            "ucp_webhook_signing_map_order_constraints_and_sale_basis_verified",
        )

    def test_ucp_webhook_signing_and_constraints_blocks_violations(self) -> None:
        # 1. Webhook body still carries legacy event_id / created_time (#659)
        r1 = verify_ucp_webhook_signing_map_order_request_constraints_and_sale_basis(
            {
                "order_webhook": {
                    "headers": {"Webhook-Id": "evt_1", "Webhook-Timestamp": "1792512000"},
                    "covered_components": ["webhook-id", "webhook-timestamp"],
                    "body": {"id": "ord_1", "event_id": "evt_1"},
                }
            }
        )
        self.assertFalse(r1.allowed)
        self.assertEqual(r1.reason_code, "ucp_webhook_body_legacy_event_fields_present")

        # 2. Webhook-Timestamp present in headers but omitted from RFC 9421 covered components (#659)
        r2 = verify_ucp_webhook_signing_map_order_request_constraints_and_sale_basis(
            {
                "order_webhook": {
                    "headers": {"Webhook-Id": "evt_1", "Webhook-Timestamp": "1792512000"},
                    "covered_components": ["webhook-id"],
                    "body": {"id": "ord_1"},
                }
            }
        )
        self.assertFalse(r2.allowed)
        self.assertEqual(r2.reason_code, "ucp_webhook_signing_gate_missing_id_or_timestamp")

        # 3. Profile capabilities declared as array or missing schema URL (#658)
        r3 = verify_ucp_webhook_signing_map_order_request_constraints_and_sale_basis(
            {
                "profile": {
                    "ucp": {
                        "capabilities": [{"name": "dev.ucp.shopping.checkout"}]
                    }
                }
            }
        )
        self.assertFalse(r3.allowed)
        self.assertEqual(r3.reason_code, "ucp_profile_capabilities_not_map_or_missing_schema")

        # 4. Platform request includes response-only map_order or request_constraints (#657/#655)
        r4 = verify_ucp_webhook_signing_map_order_request_constraints_and_sale_basis(
            {
                "direction": "request",
                "ucp_meta": {"map_order": {"payment_handlers": ["h1"]}},
            }
        )
        self.assertFalse(r4.allowed)
        self.assertEqual(r4.reason_code, "ucp_map_order_or_constraints_forbidden_on_request")

        # 5. Available instrument request_constraints missing RFC 9535 JSONPath (#655)
        r5 = verify_ucp_webhook_signing_map_order_request_constraints_and_sale_basis(
            {"available_instrument_request_constraints": {"required": ["holder_name"]}}
        )
        self.assertFalse(r5.allowed)
        self.assertEqual(r5.reason_code, "ucp_instrument_request_constraints_missing_path")

        # 6. Sale-basis float quantity or scale mismatch (#653)
        r6 = verify_ucp_webhook_signing_map_order_request_constraints_and_sale_basis(
            {
                "line_item": {
                    "quantity": 1500,
                    "quantity_unit": {"unit": "kg", "scale": 2},
                    "expected_decimal_quantity": 1.5,
                }
            }
        )
        self.assertFalse(r6.allowed)
        self.assertEqual(r6.reason_code, "ucp_quantity_sale_basis_invalid_step_or_scale")

    def test_acp_protocol_extensions_offer_expiry_webhook_and_mcp_passes(self) -> None:
        raw_body = '{"order_id":"ord_101","status":"fulfilled"}'
        secret = "whsec_stage70_test_secret"
        ts = 1792512000
        mac = hmac.new(
            secret.encode("utf-8"),
            f"{ts}.{raw_body}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        res = verify_acp_protocol_extensions_offer_expiry_webhook_hmac_and_mcp_binding(
            {
                "protocol": {
                    "version": "2026-01-30",
                    "extensions": [{"name": "discount"}, {"name": "fulfillment"}],
                },
                "capabilities": {"services": ["checkout", "orders", "delegate_payment"]},
                "session_status": "ready_for_payment",
                "operation": "complete_checkout",
                "evaluation_time": "2026-10-20T18:10:00Z",
                "line_items": [
                    {
                        "id": "line_flight_001",
                        "availability_status": "offer_valid",
                        "valid_until": "2026-10-20T18:15:00Z",
                    }
                ],
                "order_webhook_update": {
                    "fulfillment_type": "digital",
                    "status": "fulfilled",
                },
                "delegate_payment_error": {
                    "type": "unauthorized",
                    "code": "unauthorized",
                },
                "webhook_signature_check": {
                    "merchant_signature": f"t={ts},v1={mac}",
                    "raw_body": raw_body,
                    "shared_secret": secret,
                    "now_unix": ts + 120,
                    "tolerance_seconds": 300,
                },
                "mcp_tool_call": {
                    "name": "create_checkout_session",
                    "arguments": {
                        "meta": {"api_version": "2026-01-30", "idempotency_key": "idem_01"},
                        "payload": {"currency": "usd", "line_items": [{"id": "item_1", "quantity": 1}]},
                    },
                },
            }
        )
        self.assertTrue(res.allowed)
        self.assertEqual(
            res.reason_code,
            "acp_protocol_extensions_offer_expiry_webhook_and_mcp_verified",
        )

    def test_acp_protocol_extensions_offer_expiry_and_webhook_blocks_violations(self) -> None:
        # 1. Extensions placed under capabilities instead of protocol (#178)
        r1 = verify_acp_protocol_extensions_offer_expiry_webhook_hmac_and_mcp_binding(
            {"capabilities": {"extensions": [{"name": "discount"}]}}
        )
        self.assertFalse(r1.allowed)
        self.assertEqual(
            r1.reason_code,
            "acp_extensions_declared_under_capabilities_instead_of_protocol",
        )

        # 2. Line-item valid_until expired before session quote_expires_at (#165)
        r2 = verify_acp_protocol_extensions_offer_expiry_webhook_hmac_and_mcp_binding(
            {
                "evaluation_time": "2026-10-20T18:20:00Z",
                "line_items": [
                    {
                        "id": "line_flight_001",
                        "availability_status": "offer_valid",
                        "valid_until": "2026-10-20T18:15:00Z",
                    }
                ],
            }
        )
        self.assertFalse(r2.allowed)
        self.assertEqual(r2.reason_code, "acp_line_item_offer_valid_until_expired")

        # 3. Digital fulfillment marked as "shipped" (#162)
        r3 = verify_acp_protocol_extensions_offer_expiry_webhook_hmac_and_mcp_binding(
            {"order_webhook_update": {"fulfillment_type": "digital", "status": "shipped"}}
        )
        self.assertFalse(r3.allowed)
        self.assertEqual(r3.reason_code, "acp_digital_order_shipped_status_invalid")

        # 4. Webhook replay window exceeded (>300s) (#160)
        r4 = verify_acp_protocol_extensions_offer_expiry_webhook_hmac_and_mcp_binding(
            {
                "webhook_signature_check": {
                    "merchant_signature": "t=1792510000,v1=" + ("a" * 64),
                    "raw_body": "{}",
                    "shared_secret": "sec",
                    "now_unix": 1792510500,
                    "tolerance_seconds": 300,
                }
            }
        )
        self.assertFalse(r4.allowed)
        self.assertEqual(
            r4.reason_code,
            "acp_webhook_merchant_signature_invalid_or_replay_window_exceeded",
        )

    def test_ap2_failure_response_receipt_schema_and_micropayment_passes(self) -> None:
        res = verify_ap2_failure_response_payment_receipt_json_schema_and_micropayment(
            {
                "failure_response": {
                    "data_key": "ap2.errors.FailureResponse",
                    "category": "PRICE_DRIFT",
                    "recovery_action": "USER_CONFIRMATION_REQUIRED",
                    "agent_attempted_action": "prompt_user_for_updated_cart_mandate",
                },
                "artifacts_is_none_crashed": False,
                "mandate_json_schema": {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "$id": "https://raw.githubusercontent.com/google-agentic-commerce/AP2/main/schemas/payment-mandate.schema.json",
                },
                "audit_log_entry": {
                    "mandate_id": "pm_881",
                    "event_type": "MANDATE_VERIFIED",
                    "redacted_instrument": "tok_visa_4242",
                },
                "verifiable_intent_chain": {
                    "hops": ["issuer_credential", "user_mandate", "agent_fulfillment"],
                    "signature_valid": True,
                },
                "micropayment_channel": {
                    "role": "micropayment-provider",
                    "currency": "USDC",
                    "channel_deposit": 5.0,
                    "cumulative_spent": 1.25,
                    "tick_amount": 0.05,
                    "previous_sequence_number": 41,
                    "sequence_number": 42,
                },
            }
        )
        self.assertTrue(res.allowed)
        self.assertEqual(
            res.reason_code,
            "ap2_failure_response_receipt_schema_and_micropayment_verified",
        )

    def test_ap2_failure_response_and_micropayment_blocks_violations(self) -> None:
        # 1. Autonomous silent retry on PRICE_DRIFT / USER_CONFIRMATION_REQUIRED (#131/#132)
        r1 = verify_ap2_failure_response_payment_receipt_json_schema_and_micropayment(
            {
                "failure_response": {
                    "data_key": "ap2.errors.FailureResponse",
                    "category": "PRICE_DRIFT",
                    "recovery_action": "USER_CONFIRMATION_REQUIRED",
                    "agent_attempted_action": "autonomous_silent_retry",
                }
            }
        )
        self.assertFalse(r1.allowed)
        self.assertEqual(r1.reason_code, "ap2_failure_recovery_autonomous_retry_forbidden")

        # 2. Micropayment channel overdraft or sequence replay (#83)
        r2 = verify_ap2_failure_response_payment_receipt_json_schema_and_micropayment(
            {
                "micropayment_channel": {
                    "role": "streaming-payment-consumer",
                    "currency": "PYUSD",
                    "channel_deposit": 1.00,
                    "cumulative_spent": 0.98,
                    "tick_amount": 0.05,
                    "previous_sequence_number": 10,
                    "sequence_number": 11,
                }
            }
        )
        self.assertFalse(r2.allowed)
        self.assertEqual(r2.reason_code, "ap2_micropayment_channel_overdraft_or_nonce_replay")

    def test_tau2_live_interruption_retry_coercion_and_metrics_passes(self) -> None:
        res = verify_tau2_live_interruption_hallucination_retry_pydantic_coercion_and_metrics(
            {
                "openai_live_event": {
                    "type": "session.input_transcript.delta",
                    "speech_started": True,
                    "was_truncated": False,
                    "explicit_truncation_event": False,
                },
                "hallucination_retry": {
                    "hallucinations_field": [],
                    "final_retry_reviewed": True,
                    "only_selected_checkpointed": True,
                    "complete_tool_results_preserved": True,
                },
                "tool_kwargs_coercion": {
                    "schema_type": "int",
                    "persisted_value": 5,
                },
                "trajectory_replay": {
                    "agent_implementation": "llm_agent_solo_gt",
                    "solo_mode_enabled": True,
                    "user_tools_loaded": True,
                },
                "pass_hat_k_metrics": {
                    "total_tasks": 50,
                    "all_infra_error_tasks": 2,
                    "denominator_tasks": 50,
                    "compared_by_enum_value": True,
                },
                "close_bank_account_call": {
                    "account_id": "chk_001",
                    "reason": "customer_request",
                },
            }
        )
        self.assertTrue(res.allowed)
        self.assertEqual(
            res.reason_code,
            "tau2_live_interruption_retry_coercion_and_metrics_verified",
        )

    def test_tau2_live_interruption_retry_coercion_and_metrics_blocks_violations(self) -> None:
        # 1. OpenAI Live input_transcript.delta falsely sets was_truncated=True (#528)
        r1 = verify_tau2_live_interruption_hallucination_retry_pydantic_coercion_and_metrics(
            {
                "openai_live_event": {
                    "type": "session.input_transcript.delta",
                    "speech_started": True,
                    "was_truncated": True,
                    "explicit_truncation_event": False,
                }
            }
        )
        self.assertFalse(r1.allowed)
        self.assertEqual(r1.reason_code, "tau2_live_input_transcript_falsely_marked_truncated")

        # 2. Uncoerced float persisted into integer DB column (#516)
        r2 = verify_tau2_live_interruption_hallucination_retry_pydantic_coercion_and_metrics(
            {"tool_kwargs_coercion": {"schema_type": "int", "persisted_value": 5.0}}
        )
        self.assertFalse(r2.allowed)
        self.assertEqual(r2.reason_code, "tau2_tool_kwargs_uncoerced_float_db_hash_drift")

        # 3. llm_agent_solo_gt not recognized as solo mode during replay (#508)
        r3 = verify_tau2_live_interruption_hallucination_retry_pydantic_coercion_and_metrics(
            {
                "trajectory_replay": {
                    "agent_implementation": "llm_agent_solo_gt",
                    "solo_mode_enabled": False,
                    "user_tools_loaded": False,
                }
            }
        )
        self.assertFalse(r3.allowed)
        self.assertEqual(r3.reason_code, "tau2_solo_gt_missing_user_tools_on_replay")

        # 4. All-infra-error tasks dropped from pass^k denominator (#498)
        r4 = verify_tau2_live_interruption_hallucination_retry_pydantic_coercion_and_metrics(
            {
                "pass_hat_k_metrics": {
                    "total_tasks": 50,
                    "all_infra_error_tasks": 2,
                    "denominator_tasks": 48,
                    "compared_by_enum_value": True,
                }
            }
        )
        self.assertFalse(r4.allowed)
        self.assertEqual(r4.reason_code, "tau2_pass_hat_k_infra_error_denominator_inflation")

        # 5. Free-form close_bank_account_7392 reason corrupting DB hash (#484)
        r5 = verify_tau2_live_interruption_hallucination_retry_pydantic_coercion_and_metrics(
            {
                "close_bank_account_call": {
                    "account_id": "chk_closed",
                    "reason": "Customer requested Evergreen closure after splitting balance",
                }
            }
        )
        self.assertFalse(r5.allowed)
        self.assertEqual(
            r5.reason_code,
            "tau2_banking_close_account_freeform_reason_corrupts_db_hash",
        )


if __name__ == "__main__":
    unittest.main()
