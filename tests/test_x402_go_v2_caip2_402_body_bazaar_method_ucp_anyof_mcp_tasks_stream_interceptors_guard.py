"""Unit tests for Stage 198 deterministic guard module."""

from __future__ import annotations

import unittest

from lab.x402_go_v2_caip2_402_body_bazaar_method_ucp_anyof_mcp_tasks_stream_interceptors_guard import (
    validate_mcp_sep2343_elicitation_auth_and_sep1933_wif,
    validate_mcp_sep2624_interceptor_trust_boundary_pipeline,
    validate_mcp_sep2694_resumable_task_event_stream,
    validate_ucp_anyof_non_empty_branch_and_discriminator,
    validate_x402_bazaar_declared_method_enrichment,
    validate_x402_gas_sponsoring_stellar_sim_and_rust_primitives,
    validate_x402_go_402_json_error_body,
    validate_x402_go_v2_caip2_network_envelope,
)


class Stage198GuardTest(unittest.TestCase):
    def test_x402_go_v2_caip2_and_402_json_body(self) -> None:
        ok_v2 = validate_x402_go_v2_caip2_network_envelope(
            message_type="requirements",
            x402_version=2,
            network="eip155:84532",
        )
        self.assertTrue(ok_v2.allowed)

        ok_v1 = validate_x402_go_v2_caip2_network_envelope(
            message_type="payment_required",
            x402_version=1,
            accepts=[{"scheme": "exact", "network": "base-sepolia"}],
        )
        self.assertTrue(ok_v1.allowed)

        bad_v2 = validate_x402_go_v2_caip2_network_envelope(
            message_type="payload",
            x402_version=2,
            accepted={"scheme": "exact", "network": "eip155:84532:extra"},
        )
        self.assertFalse(bad_v2.allowed)
        self.assertEqual(bad_v2.decision_code, "X402_GO_V2_MALFORMED_CAIP2_NETWORK_BLOCKED")

        ok_402 = validate_x402_go_402_json_error_body(
            is_browser_request=False,
            has_custom_unpaid_body=False,
            failure_stage="settlement",
            payment_required_error="",
            response_status=402,
            response_headers={"Cache-Control": "no-store", "PAYMENT-RESPONSE": "eyJzdWNjZXNzIjpmYWxzZX0="},
            response_body={"error": "settlement_failed"},
        )
        self.assertTrue(ok_402.allowed)

    def test_x402_bazaar_method_and_gas_stellar_rust(self) -> None:
        ok_bazaar = validate_x402_bazaar_declared_method_enrichment(
            input_kind="query",
            probe_method="POST",
            advertised_method="GET",
            schema_method_enum=["GET"],
        )
        self.assertTrue(ok_bazaar.allowed)

        bad_bazaar = validate_x402_bazaar_declared_method_enrichment(
            input_kind="body",
            probe_method="GET",
            advertised_method="POST",
            schema_method_enum=["GET", "POST"],
        )
        self.assertFalse(bad_bazaar.allowed)
        self.assertEqual(bad_bazaar.decision_code, "X402_BAZAAR_SCHEMA_METHOD_ENUM_NOT_NARROWED_BLOCKED")

        bad_gas = validate_x402_gas_sponsoring_stellar_sim_and_rust_primitives(
            sponsoring_mode="eip2612",
            signer_can_read_contract=False,
            signer_can_sign_tx=True,
            extension_skipped_with_single_warning=False,
            stellar_sim_status="ok",
            stellar_error_class="",
            stellar_error_has_account_and_asset=True,
            rust_header_b64="eyJ4NDAyVmVyc2lvbiI6Mn0",
            rust_signature_hex="0x" + ("ab" * 65),
            rust_valid_after=100,
            rust_valid_before=460,
            now_epoch=160,
        )
        self.assertFalse(bad_gas.allowed)
        self.assertEqual(bad_gas.decision_code, "X402_GO_EIP2612_SIGNER_MISSING_READ_CONTRACT_NOT_SKIPPED_BLOCKED")

    def test_ucp_anyof_non_empty_and_discriminator_pinning(self) -> None:
        branches = [
            {
                "properties": {"card_number_type": {"const": "fpan"}},
                "required": ["card_number_type", "cvc"],
            },
            {
                "properties": {"card_number_type": {"const": "network_token"}},
                "required": ["card_number_type", "cryptogram", "eci_value"],
            },
        ]
        ok_fpan = validate_ucp_anyof_non_empty_branch_and_discriminator(
            anyof_branches=branches,
            discriminator_field="card_number_type",
            submitted_credential={"card_number_type": "fpan", "cvc": "123"},
        )
        self.assertTrue(ok_fpan.allowed)

        bad_dpan = validate_ucp_anyof_non_empty_branch_and_discriminator(
            anyof_branches=branches,
            discriminator_field="card_number_type",
            submitted_credential={"card_number_type": "dpan"},
        )
        self.assertFalse(bad_dpan.allowed)
        self.assertEqual(bad_dpan.decision_code, "UCP_SUBMITTED_CREDENTIAL_FAILS_CLOSED_ANYOF_BRANCHES_BLOCKED")

    def test_mcp_sep2694_sep2624_sep2343_sep1933(self) -> None:
        dup_stream = validate_mcp_sep2694_resumable_task_event_stream(
            task_id="task-1",
            active_streams_on_connection=["task-1"],
            after_cursor=0,
            earliest_retained_seq=0,
            latest_retained_seq=5,
            emitted_events=[],
        )
        self.assertFalse(dup_stream.allowed)
        self.assertEqual(dup_stream.decision_code, "MCP_SEP2694_DUPLICATE_ACTIVE_STREAM_ON_CONNECTION_BLOCKED")

        bad_mutator_order = validate_mcp_sep2624_interceptor_trust_boundary_pipeline(
            direction="sending",
            executed_stages=["mutate", "validate", "send"],
            mutators=[
                {"name": "b-mutator", "priority_hint": 10, "mode": "active", "fail_open": False, "status": "ok"},
                {"name": "a-mutator", "priority_hint": -10, "mode": "active", "fail_open": False, "status": "ok"},
            ],
            validators=[],
            atomic_mutation_applied=True,
        )
        self.assertFalse(bad_mutator_order.allowed)
        self.assertEqual(bad_mutator_order.decision_code, "MCP_SEP2624_MUTATOR_PRIORITY_ORDER_VIOLATION_BLOCKED")

        bad_wif_http = validate_mcp_sep2343_elicitation_auth_and_sep1933_wif(
            is_remote_server=True,
            elicitation_requested=True,
            mcp_authorization_authenticated=True,
            bound_to_user_sub_and_client_id=True,
            bound_to_session_id_only=False,
            wif_grant_type="urn:ietf:params:oauth:grant-type:jwt-bearer",
            wif_issuer="https://issuer.example.com",
            trusted_issuers=["https://issuer.example.com"],
            oidc_jwks_uri="http://issuer.example.com/jwks.json",
            jwt_ttl_seconds=300,
            tenant_key_isolated=True,
            tenant_claim_issuer_controlled=True,
            target_resource_matches_server=True,
        )
        self.assertFalse(bad_wif_http.allowed)
        self.assertEqual(bad_wif_http.decision_code, "MCP_SEP1933_NON_HTTPS_JWKS_URI_BLOCKED")


if __name__ == "__main__":
    unittest.main()
