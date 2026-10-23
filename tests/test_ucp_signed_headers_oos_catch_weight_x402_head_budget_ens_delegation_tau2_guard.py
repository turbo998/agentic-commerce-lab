"""Unit tests for Stage 204 guard module (`PR-01..PR-16`)."""

from __future__ import annotations

import unittest

from lab.ucp_signed_headers_oos_catch_weight_x402_head_budget_ens_delegation_tau2_guard import (
    audit_mcp_schema_dialect_and_template_list_changed,
    audit_tau2_concurrency_deepcopy_judge_and_num_coercion,
    audit_tau2_target_db_cache_and_persona_schema,
    audit_ucp_catch_weight_authorization_hold,
    audit_ucp_openapi_auth_and_update_checkout_id,
    audit_ucp_order_out_of_session_collection,
    audit_ucp_signed_request_covered_headers,
    audit_x402_axios_stream_402_drain,
    audit_x402_cache_control_private_directive,
    audit_x402_ext_delegation_grant,
    audit_x402_http_method_settlement_eligibility,
    audit_x402_payee_name_ens_binding,
    audit_x402_payment_required_header_budget,
    audit_x402_per_call_request_context_and_amount_law,
    audit_x402_python_facilitator_async_and_error_body,
    audit_x402_hook_error_status_and_plain_body,
)


class TestStage204Guard(unittest.TestCase):
    def test_pr01_to_pr04_ucp_signed_headers_oos_catch_weight_openapi(self) -> None:
        # PR-01: UCP #794 signed request omitting ucp-agent from covered components
        headers = {
            "UCP-Agent": 'profile="https://platform.example/profile"',
            "Idempotency-Key": "idem-123",
            "Content-Digest": "sha-256=:abc=:",
            "Content-Type": "application/json",
        }
        bad_pr01 = audit_ucp_signed_request_covered_headers(
            present_headers=headers,
            signature_input_components=[
                "@method",
                "@authority",
                "@path",
                "idempotency-key",
                "content-digest",
                "content-type",
            ],
        )
        self.assertFalse(bad_pr01.allowed)
        self.assertEqual(bad_pr01.reason_code, "UCP_SIGNED_REQUEST_OMITS_REQUIRED_COVERED_HEADER_BLOCKED")

        ok_pr01 = audit_ucp_signed_request_covered_headers(
            present_headers=headers,
            signature_input_components=[
                "@method",
                "@authority",
                "@path",
                "ucp-agent",
                "idempotency-key",
                "content-digest",
                "content-type",
            ],
        )
        self.assertTrue(ok_pr01.allowed)

        # PR-02: UCP #641 out-of-session payment collection
        bad_pr02 = audit_ucp_order_out_of_session_collection(
            instrument_id="pi_boleto_1",
            previous_collection_status=None,
            current_collection_status="awaiting_payment",
            order_actions=[],
            current_timestamp=1760000000,
            attempt_fulfillment_release=True,
        )
        self.assertFalse(bad_pr02.allowed)
        self.assertEqual(bad_pr02.reason_code, "UCP_ORDER_OUT_OF_SESSION_COLLECTION_VIOLATION_BLOCKED")

        ok_pr02 = audit_ucp_order_out_of_session_collection(
            instrument_id="pi_boleto_1",
            previous_collection_status=None,
            current_collection_status="awaiting_payment",
            order_actions=[
                {
                    "type": "dev.ucp.common.payment.render_artifact",
                    "instrument_id": "pi_boleto_1",
                    "artifact_url": "https://pay.merchant.example/boleto/pi_boleto_1",
                    "expires_at": 1760259200,
                }
            ],
            current_timestamp=1760000000,
            attempt_fulfillment_release=False,
        )
        self.assertTrue(ok_pr02.allowed)

        # PR-03: UCP #489 catch-weight tolerance and programmable authorization hold
        bad_pr03 = audit_ucp_catch_weight_authorization_hold(
            target_weight=5.0,
            actual_weight=6.2,
            max_overage_tolerance=0.15,
            min_underage_tolerance=0.20,
            estimated_amount_minor=7500,
            capture_amount_minor=9300,
            mandate_max_amount_minor=8625,
            required_hold_time_days=10,
            authorization_hold_days=7,
            elapsed_fulfillment_days=8,
        )
        self.assertFalse(bad_pr03.allowed)
        self.assertEqual(bad_pr03.reason_code, "UCP_CATCH_WEIGHT_TOLERANCE_OR_HOLD_VIOLATION_BLOCKED")

        ok_pr03 = audit_ucp_catch_weight_authorization_hold(
            target_weight=5.0,
            actual_weight=5.3,
            max_overage_tolerance=0.15,
            min_underage_tolerance=0.20,
            estimated_amount_minor=7500,
            capture_amount_minor=7950,
            mandate_max_amount_minor=8625,
            required_hold_time_days=10,
            authorization_hold_days=10,
            elapsed_fulfillment_days=6,
        )
        self.assertTrue(ok_pr03.allowed)

        # PR-04: UCP #668 + #649 OpenAPI Authorization header & update_checkout id exposure
        bad_pr04 = audit_ucp_openapi_auth_and_update_checkout_id(
            openapi_header_parameters=[{"in": "header", "name": "Authorization"}],
            has_security_schemes=False,
            update_checkout_schema_exposes_writable_id=True,
            path_checkout_id="chk_100",
            request_body={"id": "chk_999", "currency": "USD"},
        )
        self.assertFalse(bad_pr04.allowed)
        self.assertEqual(bad_pr04.reason_code, "UCP_OPENAPI_AUTH_HEADER_OR_UPDATE_ID_EXPOSED_BLOCKED")

        ok_pr04 = audit_ucp_openapi_auth_and_update_checkout_id(
            openapi_header_parameters=[{"in": "header", "name": "UCP-Agent"}],
            has_security_schemes=True,
            update_checkout_schema_exposes_writable_id=False,
            path_checkout_id="chk_100",
            request_body={"currency": "USD"},
        )
        self.assertTrue(ok_pr04.allowed)

    def test_pr05_to_pr10_x402_head_budget_stream_cache_ens_delegation(self) -> None:
        # PR-05: x402 #3810 + #3657 HEAD payment settlement & method mismatch
        bad_pr05 = audit_x402_http_method_settlement_eligibility(
            http_method="HEAD",
            has_payment_signature=True,
            attempt_settlement=True,
            allowed_payment_methods=["GET"],
        )
        self.assertFalse(bad_pr05.allowed)
        self.assertEqual(bad_pr05.reason_code, "X402_HEAD_SETTLEMENT_OR_METHOD_MISMATCH_BLOCKED")

        ok_pr05 = audit_x402_http_method_settlement_eligibility(
            http_method="GET",
            has_payment_signature=True,
            attempt_settlement=True,
            allowed_payment_methods=["GET", "POST"],
        )
        self.assertTrue(ok_pr05.allowed)

        # PR-06: x402 #3803 PAYMENT-REQUIRED header size budget
        huge_payload = {
            "x402Version": 2,
            "accepts": [{"scheme": "exact", "network": "eip155:8453", "maxAmountRequired": "1000"}],
            "extensions": {"bazaar": {"examples": ["x" * 9000]}},
        }
        bad_pr06 = audit_x402_payment_required_header_budget(payment_required_payload=huge_payload)
        self.assertFalse(bad_pr06.allowed)
        self.assertEqual(bad_pr06.reason_code, "X402_PAYMENT_REQUIRED_HEADER_BUDGET_EXCEEDED_BLOCKED")

        ok_pr06 = audit_x402_payment_required_header_budget(
            payment_required_payload={
                "x402Version": 2,
                "accepts": [{"scheme": "exact", "network": "eip155:8453", "maxAmountRequired": "1000"}],
                "extensions": {"bazaar": {"schemaUri": "https://cdn.example/bazaar.json", "sha256": "deadbeef"}},
            }
        )
        self.assertTrue(ok_pr06.allowed)

        # PR-07: x402 #3814 Axios streaming 402 drain
        bad_pr07 = audit_x402_axios_stream_402_drain(
            response_type="stream",
            keep_alive_max_sockets=1,
            intermediate_402_stream_drained=False,
        )
        self.assertFalse(bad_pr07.allowed)
        self.assertEqual(bad_pr07.reason_code, "X402_STREAM_INTERMEDIATE_402_UNDRAINED_DEADLOCK_BLOCKED")

        ok_pr07 = audit_x402_axios_stream_402_drain(
            response_type="stream",
            keep_alive_max_sockets=1,
            intermediate_402_stream_drained=True,
        )
        self.assertTrue(ok_pr07.allowed)

        # PR-08: x402 #3747 Cache-Control quoted private directive
        bad_pr08 = audit_x402_cache_control_private_directive(
            cache_control_header='public, max-age=60, example="a, private, b"'
        )
        self.assertFalse(bad_pr08.allowed)
        self.assertEqual(bad_pr08.reason_code, "X402_CACHE_CONTROL_QUOTED_PRIVATE_CONFUSION_BLOCKED")

        ok_pr08 = audit_x402_cache_control_private_directive(
            cache_control_header='private, max-age=60, example="a, private, b"'
        )
        self.assertTrue(ok_pr08.allowed)

        # PR-09: x402 #3755 payee-name ENS binding
        bad_pr09 = audit_x402_payee_name_ens_binding(
            payee_ens_name="weather.example.eth",
            request_origin="https://phishing-weather.example.com",
            accepts=[{"network": "eip155:8453", "payTo": "0xAttacker999"}],
            ens_allowed_origins=["https://api.weather.example.com"],
            ens_authorized_payto_by_network={"eip155:8453": ["0xOwner111"]},
            ens_owner_signature_valid=True,
            ens_expiry_timestamp=1790000000,
            current_timestamp=1760000000,
        )
        self.assertFalse(bad_pr09.allowed)
        self.assertEqual(bad_pr09.reason_code, "X402_PAYEE_NAME_ENS_ORIGIN_OR_PAYTO_UNBOUND_BLOCKED")

        ok_pr09 = audit_x402_payee_name_ens_binding(
            payee_ens_name="weather.example.eth",
            request_origin="https://api.weather.example.com",
            accepts=[{"network": "eip155:8453", "payTo": "0xOwner111"}],
            ens_allowed_origins=["https://api.weather.example.com"],
            ens_authorized_payto_by_network={"eip155:8453": ["0xOwner111"]},
            ens_owner_signature_valid=True,
            ens_expiry_timestamp=1790000000,
            current_timestamp=1760000000,
        )
        self.assertTrue(ok_pr09.allowed)

        # PR-10: x402 #3693 ext-delegation grant scope
        grant = {
            "principal": "did:pkh:eip155:8453:0xPrincipal01",
            "agent": "0xAgent01",
            "audience": ["https://api.weather.example.com"],
            "maxAmount": "500000",
            "aggregateBudget": "2000000",
            "asset": "USDC",
            "network": "eip155:8453",
            "expiresAt": 1790000000,
        }
        bad_pr10 = audit_x402_ext_delegation_grant(
            grant=grant,
            principal_jws_valid=True,
            authorization_from="0xRogueAgent99",
            resource_server_origin="https://api.weather.example.com",
            payment_amount_minor=800000,
            cumulative_spent_minor=1500000,
            payment_asset="USDC",
            payment_network="eip155:8453",
            current_timestamp=1760000000,
        )
        self.assertFalse(bad_pr10.allowed)
        self.assertEqual(bad_pr10.reason_code, "X402_EXT_DELEGATION_SCOPE_OR_SIGNER_VIOLATION_BLOCKED")

        ok_pr10 = audit_x402_ext_delegation_grant(
            grant=grant,
            principal_jws_valid=True,
            authorization_from="0xAgent01",
            resource_server_origin="https://api.weather.example.com",
            payment_amount_minor=400000,
            cumulative_spent_minor=1000000,
            payment_asset="USDC",
            payment_network="eip155:8453",
            current_timestamp=1760000000,
        )
        self.assertTrue(ok_pr10.allowed)

    def test_pr11_to_pr16_x402_sdk_mcp_dialect_and_tau2_bench(self) -> None:
        # PR-11: x402 #3792 + #3779 Python async facilitator & non-200 body preservation
        bad_pr11 = audit_x402_python_facilitator_async_and_error_body(
            is_async_facilitator_client=True,
            bazaar_called_method="_get_client",
            facilitator_http_status=422,
            facilitator_error_body={"isValid": False, "invalidReason": "insufficient_funds"},
            raises_generic_value_error_dropping_body=True,
        )
        self.assertFalse(bad_pr11.allowed)
        self.assertEqual(bad_pr11.reason_code, "X402_PYTHON_ASYNC_CLIENT_OR_NON200_BODY_DROP_BLOCKED")

        ok_pr11 = audit_x402_python_facilitator_async_and_error_body(
            is_async_facilitator_client=True,
            bazaar_called_method="_get_async_client",
            facilitator_http_status=422,
            facilitator_error_body={"isValid": False, "invalidReason": "insufficient_funds"},
            raises_generic_value_error_dropping_body=False,
        )
        self.assertTrue(ok_pr11.allowed)

        # PR-12: x402 #3650 + #3680 + #3811 hook error, status & plain body
        bad_pr12 = audit_x402_hook_error_status_and_plain_body(
            after_payment_creation_hook_error="budget_ledger_write_failed",
            go_client_discards_hook_error=True,
            payment_flow="upfront",
            settle_response_success=True,
            paid_http_status=500,
            on_payment_response_receives_status=False,
            custom_failure_content_type="text/plain",
            serialized_failure_body='"Settlement failed.\\nPlease retry."',
        )
        self.assertFalse(bad_pr12.allowed)
        self.assertEqual(
            bad_pr12.reason_code,
            "X402_HOOK_ERROR_SWALLOWED_STATUS_OMITTED_OR_PLAIN_JSON_ENCODED_BLOCKED",
        )

        ok_pr12 = audit_x402_hook_error_status_and_plain_body(
            after_payment_creation_hook_error=None,
            go_client_discards_hook_error=False,
            payment_flow="upfront",
            settle_response_success=True,
            paid_http_status=200,
            on_payment_response_receives_status=True,
            custom_failure_content_type="text/plain",
            serialized_failure_body="Settlement failed.\nPlease retry.",
        )
        self.assertTrue(ok_pr12.allowed)

        # PR-13: x402 #3750 + #3660 per-call request context & amount law
        bad_pr13 = audit_x402_per_call_request_context_and_amount_law(
            in_flight_request_id="req_concurrent_2",
            payload_context_request_id="req_concurrent_1",
            uses_shared_constructor_request=True,
            expected_usd_minor=500,
            rail_quotes=[
                {"network": "eip155:8453", "maxAmountRequired": 5000000, "usdEquivalentMinor": 500},
                {"network": "solana:mainnet", "maxAmountRequired": 0, "usdEquivalentMinor": 0},
            ],
        )
        self.assertFalse(bad_pr13.allowed)
        self.assertEqual(bad_pr13.reason_code, "X402_CONCURRENT_REQUEST_CONTEXT_OR_ZERO_RAIL_AMOUNT_BLOCKED")

        ok_pr13 = audit_x402_per_call_request_context_and_amount_law(
            in_flight_request_id="req_concurrent_2",
            payload_context_request_id="req_concurrent_2",
            uses_shared_constructor_request=False,
            expected_usd_minor=500,
            rail_quotes=[
                {"network": "eip155:8453", "maxAmountRequired": 5000000, "usdEquivalentMinor": 500},
                {"network": "solana:mainnet", "maxAmountRequired": 5000000, "usdEquivalentMinor": 500},
            ],
        )
        self.assertTrue(ok_pr13.allowed)

        # PR-14: MCP #3238 + #3226 schema dialect & resource template list_changed
        bad_pr14 = audit_mcp_schema_dialect_and_template_list_changed(
            input_schema={"$schema": "https://example.com/unsupported-dialect"},
            requested_schema={
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {"nested": {"type": "object"}},
            },
            resource_templates_mutated=True,
            emitted_resources_list_changed=False,
            client_refetched_resource_templates=False,
        )
        self.assertFalse(bad_pr14.allowed)
        self.assertEqual(bad_pr14.reason_code, "MCP_SCHEMA_DIALECT_LAYER_OR_TEMPLATE_LIST_CHANGED_BLOCKED")

        ok_pr14 = audit_mcp_schema_dialect_and_template_list_changed(
            input_schema={"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object"},
            requested_schema={"type": "object", "properties": {"confirm": {"type": "boolean"}}},
            resource_templates_mutated=True,
            emitted_resources_list_changed=True,
            client_refetched_resource_templates=True,
        )
        self.assertTrue(ok_pr14.allowed)

        # PR-15: tau2-bench #654 + #477 target DB cache & persoca typo
        bad_pr15 = audit_tau2_target_db_cache_and_persona_schema(
            task_id="banking_knowledge_task_091",
            current_actions_sha256="sha_new_actions",
            cached_actions_sha256="sha_old_actions",
            current_initial_db_sha256="sha_db_1",
            cached_initial_db_sha256="sha_db_1",
            current_env_version="v2.1",
            cached_env_version="v2.0",
            user_scenario_dict={"persoca": None, "instructions": "Ask about travel card"},
        )
        self.assertFalse(bad_pr15.allowed)
        self.assertEqual(bad_pr15.reason_code, "TAU2_STALE_TARGET_DB_CACHE_OR_PERSOCA_TYPO_BLOCKED")

        ok_pr15 = audit_tau2_target_db_cache_and_persona_schema(
            task_id="banking_knowledge_task_091",
            current_actions_sha256="sha_new_actions",
            cached_actions_sha256="sha_new_actions",
            current_initial_db_sha256="sha_db_1",
            cached_initial_db_sha256="sha_db_1",
            current_env_version="v2.1",
            cached_env_version="v2.1",
            user_scenario_dict={"persona": None, "instructions": "Ask about travel card"},
        )
        self.assertTrue(ok_pr15.allowed)

        # PR-16: tau2-bench #154 + #474 + #430 concurrent deepcopy, judge fallback & numeric string coercion
        bad_pr16 = audit_tau2_concurrency_deepcopy_judge_and_num_coercion(
            shares_class_level_mutable_ref=True,
            judge_llm_model="gpt-4.1-2025-04-14",
            judge_api_key_is_placeholder=True,
            trajectories_saved_before_judge_eval=False,
            numeric_tool_arg_value="250.75",
            tool_rejects_numeric_string=True,
        )
        self.assertFalse(bad_pr16.allowed)
        self.assertEqual(
            bad_pr16.reason_code,
            "TAU2_SHARED_VPN_STATE_JUDGE_FALLBACK_OR_STR_NUM_ERROR_BLOCKED",
        )

        ok_pr16 = audit_tau2_concurrency_deepcopy_judge_and_num_coercion(
            shares_class_level_mutable_ref=False,
            judge_llm_model="gpt-4.1-2025-04-14",
            judge_api_key_is_placeholder=False,
            trajectories_saved_before_judge_eval=True,
            numeric_tool_arg_value="250.75",
            tool_rejects_numeric_string=False,
        )
        self.assertTrue(ok_pr16.allowed)


if __name__ == "__main__":
    unittest.main()
