"""Unit tests for Stage 214 deterministic guard module (PR-01..PR-16)."""

from __future__ import annotations

import base64
import hashlib
import json
import unittest

from lab.ucp_totals_lodging_acp_ajv_ap2_jcs_did_x402_svm_v1_bazaar_mcp_attestation_tau2_paired_guard import (
    audit_acp_ajv_schema_id_ref_resolution_and_example_conformance,
    audit_ap2_jcs_cart_to_payment_mandate_binding_rfc8785,
    audit_ap2_tenzro_did_stark_settlement_and_adk_session_serialization,
    audit_mcp_client_session_id_error_taxonomy_and_structured_content,
    audit_mcp_python_sdk_rfc8707_token_exchange_and_utf8_surrogate_transport_guard,
    audit_mcp_server_signed_execution_record_and_tool_call_attestation,
    audit_stripe_agent_toolkit_dxt_manifest_pmc_and_subscription_checkout_metadata,
    audit_tau2_batch_worker_interleaving_and_threading_lock_checkpoint_guard,
    audit_tau2_paired_ab_scorer_secret_redaction_and_token_cache_ttft_guard,
    audit_ucp_custom_totals_display_text_and_capability_model_reuse,
    audit_ucp_lodging_booking_and_byopb_payment_response_cleanup,
    audit_x402_auth_capture_client_v1_1_and_solana_upto_facilitator,
    audit_x402_bazaar_withx402_route_template_and_empty_filter_conformance,
    audit_x402_facilitator_self_send_guard_and_eip3009_max_timeout_valid_before,
    audit_x402_go_builder_code_attribution_and_extension_responses_sidechannel,
    audit_x402_svm_transaction_v1_size_gate_and_pinet_exact_scheme,
)


class Stage214GuardTest(unittest.TestCase):
    def test_ucp_acp_and_ap2_guards_pass_and_block(self) -> None:
        # PR-01
        ok_01 = audit_ucp_custom_totals_display_text_and_capability_model_reuse(
            {
                "totals": [
                    {"type": "subtotal", "amount": 10000},
                    {"type": "eco_bottle_deposit", "amount": 50, "display_text": "Bottle Deposit"},
                    {"type": "total", "amount": 10050},
                ],
                "reuse_model_enabled": True,
                "duplicate_extends_diverged": False,
            }
        )
        self.assertTrue(ok_01.passed)
        bad_01 = audit_ucp_custom_totals_display_text_and_capability_model_reuse(
            {
                "totals": [{"type": "eco_bottle_deposit", "amount": 50}],
                "reuse_model_enabled": True,
                "duplicate_extends_diverged": False,
            }
        )
        self.assertFalse(bad_01.passed)
        self.assertEqual(bad_01.code, "UCP_CUSTOM_TOTAL_DISPLAY_TEXT_REQUIRED")

        # PR-02
        ok_02 = audit_ucp_lodging_booking_and_byopb_payment_response_cleanup(
            {
                "capability": "dev.ucp.lodging.booking",
                "check_in_date": "2026-11-10",
                "check_out_date": "2026-11-14",
                "guest_count": 2,
                "max_occupancy": 4,
                "payment_instrument": {"id": "pi_card_01", "type": "card"},
                "byopb_action_bound": True,
            }
        )
        self.assertTrue(ok_02.passed)
        bad_02 = audit_ucp_lodging_booking_and_byopb_payment_response_cleanup(
            {
                "capability": "dev.ucp.lodging.booking",
                "check_in_date": "2026-11-10",
                "check_out_date": "2026-11-14",
                "guest_count": 2,
                "max_occupancy": 4,
                "payment_instrument": {
                    "id": "pi_card_01",
                    "processor_raw_response": {"raw": "secret"},
                },
                "byopb_action_bound": True,
            }
        )
        self.assertFalse(bad_02.passed)
        self.assertEqual(bad_02.code, "UCP_PAYMENT_INSTRUMENT_RAW_RESPONSE_LEAK")

        # PR-03
        ok_03 = audit_acp_ajv_schema_id_ref_resolution_and_example_conformance(
            {
                "registered_schema_ids": [
                    "schema.agentic_checkout.json",
                    "schema.delegate_payment.json",
                ],
                "unresolved_refs": [],
                "invalid_examples": [],
                "pr_title_valid": True,
                "pr_description_non_empty": True,
            }
        )
        self.assertTrue(ok_03.passed)
        bad_03 = audit_acp_ajv_schema_id_ref_resolution_and_example_conformance(
            {
                "registered_schema_ids": ["schema.agentic_checkout.json"],
                "unresolved_refs": ["schema.delegate_payment.json#/definitions/Allowance"],
                "invalid_examples": [],
                "pr_title_valid": True,
                "pr_description_non_empty": True,
            }
        )
        self.assertFalse(bad_03.passed)
        self.assertEqual(bad_03.code, "ACP_AJV_SCHEMA_REF_UNRESOLVED")

        # PR-04
        cart = {"id": "cart_998", "currency": "USD", "total_minor": 18500}
        cart_hash = hashlib.sha256(
            json.dumps(cart, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        ok_04 = audit_ap2_jcs_cart_to_payment_mandate_binding_rfc8785(
            {
                "cart_mandate": cart,
                "payment_mandate_contents": {
                    "cart_mandate_id": "cart_998",
                    "cart_mandate_hash": cart_hash,
                },
            }
        )
        self.assertTrue(ok_04.passed)
        bad_04 = audit_ap2_jcs_cart_to_payment_mandate_binding_rfc8785(
            {
                "cart_mandate": cart,
                "payment_mandate_contents": {
                    "cart_mandate_id": "cart_998",
                    "cart_mandate_hash": "fake_cart_mandate_hash_cart_998",
                },
            }
        )
        self.assertFalse(bad_04.passed)
        self.assertEqual(bad_04.code, "AP2_PLACEHOLDER_CART_MANDATE_HASH_REJECTED")

        # PR-05
        ok_05 = audit_ap2_tenzro_did_stark_settlement_and_adk_session_serialization(
            {
                "payer_did": "did:tenzro:payer_01",
                "merchant_did": "did:tenzro:merchant_01",
                "mandate_chain": ["IntentMandate", "CartMandate", "PaymentMandate"],
                "stark_commitment_verified": True,
                "session_state_values_json_serializable": True,
                "raw_pydantic_in_sqlite_session": False,
            }
        )
        self.assertTrue(ok_05.passed)
        bad_05 = audit_ap2_tenzro_did_stark_settlement_and_adk_session_serialization(
            {
                "payer_did": "did:tenzro:payer_01",
                "merchant_did": "did:tenzro:merchant_01",
                "mandate_chain": ["IntentMandate", "CartMandate", "PaymentMandate"],
                "stark_commitment_verified": True,
                "session_state_values_json_serializable": False,
                "raw_pydantic_in_sqlite_session": True,
            }
        )
        self.assertFalse(bad_05.passed)
        self.assertEqual(bad_05.code, "AP2_ADK_SESSION_UNSERIALIZED_PYDANTIC_MODEL")

    def test_x402_guards_pass_and_block(self) -> None:
        # PR-06
        ok_06 = audit_x402_svm_transaction_v1_size_gate_and_pinet_exact_scheme(
            {
                "protocol_path": "v2_exact",
                "tx_version": 1,
                "tx_size_bytes": 2840,
                "pinet_network": "pinet:mainnet",
                "pinet_scheme": "exact",
            }
        )
        self.assertTrue(ok_06.passed)
        bad_06 = audit_x402_svm_transaction_v1_size_gate_and_pinet_exact_scheme(
            {
                "protocol_path": "v1_legacy_exact",
                "tx_version": 1,
                "tx_size_bytes": 2840,
                "pinet_network": "pinet:mainnet",
                "pinet_scheme": "exact",
            }
        )
        self.assertFalse(bad_06.passed)
        self.assertEqual(bad_06.code, "X402_SVM_LEGACY_PATH_V1_TX_REJECTED")

        # PR-07
        ok_07 = audit_x402_bazaar_withx402_route_template_and_empty_filter_conformance(
            {
                "route_template": "/api/weather",
                "supplied_filter": "category=quantum",
                "matched_count": 0,
                "returned_items_count": 0,
                "unapplied_filters": [],
            }
        )
        self.assertTrue(ok_07.passed)
        bad_07 = audit_x402_bazaar_withx402_route_template_and_empty_filter_conformance(
            {
                "route_template": ":var1",
                "supplied_filter": "category=quantum",
                "matched_count": 0,
                "returned_items_count": 10,
                "unapplied_filters": [],
            }
        )
        self.assertFalse(bad_07.passed)
        self.assertEqual(bad_07.code, "X402_BAZAAR_WILDCARD_ROUTE_TEMPLATE_INVALID")

        # PR-08
        ok_08 = audit_x402_go_builder_code_attribution_and_extension_responses_sidechannel(
            {
                "server_declared_app_code": "app_commerce_01",
                "root_app_code": "app_commerce_01",
                "nested_info_app_code": "app_commerce_01",
                "extension_responses_sidechannel_populated": True,
                "extension_responses_leaked_in_buyer_json": False,
            }
        )
        self.assertTrue(ok_08.passed)
        bad_08 = audit_x402_go_builder_code_attribution_and_extension_responses_sidechannel(
            {
                "server_declared_app_code": "app_commerce_01",
                "root_app_code": "app_commerce_01",
                "nested_info_app_code": "app_spoofed_99",
                "extension_responses_sidechannel_populated": True,
                "extension_responses_leaked_in_buyer_json": False,
            }
        )
        self.assertFalse(bad_08.passed)
        self.assertEqual(bad_08.code, "X402_BUILDER_CODE_ROOT_NESTED_CONFLICT")

        # PR-09
        ok_09 = audit_x402_facilitator_self_send_guard_and_eip3009_max_timeout_valid_before(
            {
                "payer_address": "0x1111111111111111111111111111111111111111",
                "pay_to_address": "0x2222222222222222222222222222222222222222",
                "now_epoch": 1760000000,
                "max_timeout_seconds": 300,
                "eip3009_valid_before": 1760000300,
            }
        )
        self.assertTrue(ok_09.passed)
        bad_09 = audit_x402_facilitator_self_send_guard_and_eip3009_max_timeout_valid_before(
            {
                "payer_address": "0x1111111111111111111111111111111111111111",
                "pay_to_address": "0x1111111111111111111111111111111111111111",
                "now_epoch": 1760000000,
                "max_timeout_seconds": 300,
                "eip3009_valid_before": 1760000300,
            }
        )
        self.assertFalse(bad_09.passed)
        self.assertEqual(bad_09.code, "X402_FACILITATOR_SELF_SEND_NOT_ALLOWED")

        # PR-10
        ok_10 = audit_x402_auth_capture_client_v1_1_and_solana_upto_facilitator(
            {
                "auth_capture_version": "1.1",
                "authorized_minor": 5000,
                "capture_minor": 4200,
                "solana_upto_max_lamports": 1_000_000,
                "solana_settled_lamports": 750_000,
            }
        )
        self.assertTrue(ok_10.passed)
        bad_10 = audit_x402_auth_capture_client_v1_1_and_solana_upto_facilitator(
            {
                "auth_capture_version": "1.1",
                "authorized_minor": 5000,
                "capture_minor": 5800,
                "solana_upto_max_lamports": 1_000_000,
                "solana_settled_lamports": 750_000,
            }
        )
        self.assertFalse(bad_10.passed)
        self.assertEqual(bad_10.code, "X402_AUTH_CAPTURE_V1_1_BOUND_VIOLATION")

    def test_mcp_stripe_and_tau2_guards_pass_and_block(self) -> None:
        # PR-11
        ok_11 = audit_mcp_server_signed_execution_record_and_tool_call_attestation(
            {
                "client_tool_attestation": {
                    "intent": "purchase_lodging",
                    "agent_id": "agent://buyer/01",
                    "tool_name": "complete_checkout",
                    "arguments_sha256": "a" * 64,
                    "client_signature": "sig_client_ed25519",
                },
                "server_execution_record": {
                    "policy_decision": "allow",
                    "execution_outcome_sha256": "b" * 64,
                    "attestation_ref": "att_01",
                    "server_signature": "sig_server_ed25519",
                },
            }
        )
        self.assertTrue(ok_11.passed)
        bad_11 = audit_mcp_server_signed_execution_record_and_tool_call_attestation(
            {
                "client_tool_attestation": {"intent": "purchase_lodging"},
                "server_execution_record": {},
            }
        )
        self.assertFalse(bad_11.passed)
        self.assertEqual(bad_11.code, "MCP_SEP2787_TOOL_ATTESTATION_INCOMPLETE")

        # PR-12
        ok_12 = audit_mcp_client_session_id_error_taxonomy_and_structured_content(
            {
                "transport": "streamable_http",
                "mcp_client_session_id_header": "sess_client_20261024_01",
                "error_taxonomy_code": "INVALID_TOOL_ARGUMENTS",
                "has_structured_content": True,
                "duplicated_json_in_text_content": False,
            }
        )
        self.assertTrue(ok_12.passed)
        bad_12 = audit_mcp_client_session_id_error_taxonomy_and_structured_content(
            {
                "transport": "streamable_http",
                "mcp_client_session_id_header": "sess_client_20261024_01",
                "error_taxonomy_code": "INVALID_TOOL_ARGUMENTS",
                "has_structured_content": True,
                "duplicated_json_in_text_content": True,
            }
        )
        self.assertFalse(bad_12.passed)
        self.assertEqual(bad_12.code, "MCP_STRUCTURED_CONTENT_DUPLICATION_VIOLATION")

        # PR-13
        raw_bytes = b"\xff\xfe\xfd"
        ok_13 = audit_mcp_python_sdk_rfc8707_token_exchange_and_utf8_surrogate_transport_guard(
            {
                "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
                "resource_indicator": "https://mcp.merchant.example/tools",
                "transport_message": "valid utf-8 message",
                "raw_bytes_output": raw_bytes,
                "encoded_bytes_output": base64.b64encode(raw_bytes).decode("ascii"),
            }
        )
        self.assertTrue(ok_13.passed)
        bad_13 = audit_mcp_python_sdk_rfc8707_token_exchange_and_utf8_surrogate_transport_guard(
            {
                "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
                "resource_indicator": "https://mcp.merchant.example/tools",
                "transport_message": "lone surrogate \ud800 crash",
                "raw_bytes_output": raw_bytes,
                "encoded_bytes_output": base64.b64encode(raw_bytes).decode("ascii"),
            }
        )
        self.assertFalse(bad_13.passed)
        self.assertEqual(bad_13.code, "MCP_TRANSPORT_LONE_SURROGATE_CONTAINED")

        # PR-14
        ok_14 = audit_stripe_agent_toolkit_dxt_manifest_pmc_and_subscription_checkout_metadata(
            {
                "dxt_manifest_version": "0.2.0",
                "stripe_api_key_prefix": "rk_live_",
                "payment_method_configuration_id": "pmc_12345",
                "subscription_data": {
                    "trial_period_days": 14,
                    "metadata": {"agent_id": "agent_01"},
                },
            }
        )
        self.assertTrue(ok_14.passed)
        bad_14 = audit_stripe_agent_toolkit_dxt_manifest_pmc_and_subscription_checkout_metadata(
            {
                "dxt_manifest_version": "0.2.0",
                "stripe_api_key_prefix": "sk_live_",
                "payment_method_configuration_id": "pmc_12345",
                "subscription_data": {
                    "trial_period_days": 14,
                    "metadata": {"agent_id": "agent_01"},
                },
            }
        )
        self.assertFalse(bad_14.passed)
        self.assertEqual(bad_14.code, "STRIPE_DXT_RESTRICTED_KEY_REQUIRED")

        # PR-15
        ok_15 = audit_tau2_paired_ab_scorer_secret_redaction_and_token_cache_ttft_guard(
            {
                "arm_a_task_ids": ["retail_01", "retail_02"],
                "arm_b_task_ids": ["retail_01", "retail_02"],
                "infra_429_included_in_audit": True,
                "max_steps_included_in_action_checks": True,
                "rollout_log_text": "episode finished with redacted=[REDACTED]",
                "ttft_ms": 412.5,
                "prefix_cache_metrics_recorded": True,
            }
        )
        self.assertTrue(ok_15.passed)
        bad_15 = audit_tau2_paired_ab_scorer_secret_redaction_and_token_cache_ttft_guard(
            {
                "arm_a_task_ids": ["retail_01", "retail_02"],
                "arm_b_task_ids": ["retail_01"],
                "infra_429_included_in_audit": True,
                "max_steps_included_in_action_checks": True,
                "rollout_log_text": "episode finished",
                "ttft_ms": 412.5,
                "prefix_cache_metrics_recorded": True,
            }
        )
        self.assertFalse(bad_15.passed)
        self.assertEqual(bad_15.code, "TAU2_UNPAIRED_AB_TASK_SET_REJECTED")

        # PR-16
        ok_16 = audit_tau2_batch_worker_interleaving_and_threading_lock_checkpoint_guard(
            {
                "interleaved_across_runs": True,
                "worker_log_handle_closed_cleanly": True,
                "checkpoint_lock_type": "threading.Lock",
            }
        )
        self.assertTrue(ok_16.passed)
        bad_16 = audit_tau2_batch_worker_interleaving_and_threading_lock_checkpoint_guard(
            {
                "interleaved_across_runs": True,
                "worker_log_handle_closed_cleanly": True,
                "checkpoint_lock_type": "multiprocessing.Lock",
            }
        )
        self.assertFalse(bad_16.passed)
        self.assertEqual(bad_16.code, "TAU2_IPC_MULTIPROCESSING_LOCK_REJECTED")


if __name__ == "__main__":
    unittest.main()
