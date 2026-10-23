"""Unit tests for Stage 206 deterministic guard module (PR-01..PR-16)."""

from __future__ import annotations

import hashlib
import hmac
import json
import unittest

from lab.ucp_fulfillment_events_constraints_acp_attribution_ttl_x402_pod_ata_mcp_tau2_guard import (
    audit_acp_discovery_attribution_and_discount_consolidation,
    audit_acp_idempotency_ttl_and_intervention_error,
    audit_mcp_mrtr_still_waiting_and_tool_security_schemes,
    audit_mcp_trust_sensitivity_escalation_and_server_card,
    audit_tau2_out_of_scope_termination_and_unscored_reward_guard,
    audit_tau2_reproducibility_manifest_and_silent_dotenv,
    audit_ucp_atomic_release_version_and_server_timing,
    audit_ucp_execution_intent_binding_and_participant_id,
    audit_ucp_fulfillment_destination_and_billing_constraints,
    audit_ucp_fulfillment_event_types,
    audit_x402_evm_normative_must_and_supported_capabilities,
    audit_x402_proof_of_done_and_resolution_lineage,
    audit_x402_python_create_headers_and_uncertain_settlement_hook,
    audit_x402_stellar_typed_simulation_errors,
    audit_x402_svm_destination_ata_and_async_rpc,
    audit_x402_workers_bazaar_validator_and_go_mcp_timeout_cap,
)


class Stage206GuardTest(unittest.TestCase):
    def test_pr01_to_pr06_ucp_and_acp_guards(self) -> None:
        # PR-01
        ok01 = audit_ucp_fulfillment_event_types(
            [
                {"type": "processing", "semantic_kind": "processing"},
                {"type": "in_transit", "semantic_kind": "in_transit"},
                {"type": "cold_chain_temp_checked", "description": "Dry ice verified at hub"},
            ],
            platform_rejects_unknown_event_type=False,
        )
        self.assertTrue(ok01.allowed)
        bad01 = audit_ucp_fulfillment_event_types(
            [{"type": "in-transit", "semantic_kind": "in_transit"}],
            platform_rejects_unknown_event_type=False,
        )
        self.assertFalse(bad01.allowed)

        # PR-02
        ok02 = audit_ucp_fulfillment_destination_and_billing_constraints(
            destination_required_fields=["postal_code", "address_country"],
            provided_destination_address={"postal_code": "94107", "address_country": "US"},
            instrument_required_fields=["billing_address"],
            billing_address_required_fields=["postal_code", "address_country"],
            provided_billing_address={"postal_code": "94107", "address_country": "US"},
        )
        self.assertTrue(ok02.allowed)
        bad02 = audit_ucp_fulfillment_destination_and_billing_constraints(
            destination_required_fields=["postal_code", "address_country"],
            provided_destination_address={"postal_code": "", "address_country": "US"},
            instrument_required_fields=["billing_address"],
            billing_address_required_fields=["postal_code"],
            provided_billing_address={"postal_code": "94107"},
        )
        self.assertFalse(bad02.allowed)

        # PR-03
        ok03 = audit_ucp_atomic_release_version_and_server_timing(
            selected_release="2026-08-25",
            profile_ucp_version="2026-08-25",
            declaration_versions={
                "dev.ucp.shopping.checkout": "2026-08-25",
                "dev.ucp.shopping.order": "2026-08-25",
            },
            requires_substitutes_version=False,
            server_timing_header="ucp;dur=14.8",
            http_status=201,
        )
        self.assertTrue(ok03.allowed)
        bad03 = audit_ucp_atomic_release_version_and_server_timing(
            selected_release="2026-08-25",
            profile_ucp_version="2026-08-25",
            declaration_versions={"dev.ucp.shopping.checkout": "2026-04-08"},
            requires_substitutes_version=False,
            server_timing_header="ucp;dur=14.8",
            http_status=200,
        )
        self.assertFalse(bad03.allowed)

        # PR-04
        intent = {
            "merchant_id": "merch_roses_01",
            "currency": "USD",
            "max_amount_minor": 3500,
            "items": [{"id": "red_roses_12", "qty": 1}],
        }
        secret = "intent_signing_secret_206"
        sig = hmac.new(
            secret.encode("utf-8"),
            json.dumps(intent, sort_keys=True, separators=(",", ":")).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        ok04 = audit_ucp_execution_intent_binding_and_participant_id(
            authorized_intent=intent,
            executed_checkout={
                "merchant_id": "merch_roses_01",
                "currency": "USD",
                "total_amount_minor": 3500,
                "items": [{"id": "red_roses_12", "qty": 1}],
            },
            shared_secret=secret,
            provided_intent_hmac=sig,
            participant_id="acct_merch_roses_01",
            caller_authenticated_via_own_credential=True,
            participant_id_used_as_bearer_secret=False,
        )
        self.assertTrue(ok04.allowed)
        bad04 = audit_ucp_execution_intent_binding_and_participant_id(
            authorized_intent=intent,
            executed_checkout={
                "merchant_id": "merch_roses_01",
                "currency": "USD",
                "total_amount_minor": 4900,
                "items": [{"id": "luxury_orchids", "qty": 1}],
            },
            shared_secret=secret,
            provided_intent_hmac=sig,
            participant_id="acct_merch_roses_01",
            caller_authenticated_via_own_credential=True,
            participant_id_used_as_bearer_secret=True,
        )
        self.assertFalse(bad04.allowed)

        # PR-05
        ok05 = audit_acp_discovery_attribution_and_discount_consolidation(
            discovery_context={
                "method": "comparison",
                "session_type": "active_shopping",
                "query_category": "wireless_earbuds",
                "alternatives_considered": 4,
                "rank_position": 1,
            },
            applied_discounts=[
                {"id": "disc_1", "type": "promo_code", "description": "10% summer off"}
            ],
            line_item_discount_details_present=False,
        )
        self.assertTrue(ok05.allowed)
        bad05 = audit_acp_discovery_attribution_and_discount_consolidation(
            discovery_context={
                "method": "comparison",
                "session_type": "active_shopping",
                "query_category": "wireless_earbuds",
                "alternatives_considered": 4,
                "rank_position": 1,
            },
            applied_discounts=[
                {
                    "id": "disc_1",
                    "type": "promo_code",
                    "description": "10% summer off",
                    "automatic": True,
                }
            ],
            line_item_discount_details_present=True,
        )
        self.assertFalse(bad05.allowed)

        # PR-06
        ok06 = audit_acp_idempotency_ttl_and_intervention_error(
            first_use_epoch_s=1_700_000_000,
            session_expires_at_epoch_s=1_700_003_600,
            idempotency_key_expires_epoch_s=1_700_090_000,
            idempotency_key_ttl_s=90_000,
            required_interventions=["3ds"],
            supported_interventions=[],
            returned_error_code="intervention_required",
            agent_attempted_retry=False,
        )
        self.assertTrue(ok06.allowed)
        bad06 = audit_acp_idempotency_ttl_and_intervention_error(
            first_use_epoch_s=1_700_000_000,
            session_expires_at_epoch_s=1_700_003_600,
            idempotency_key_expires_epoch_s=1_700_010_000,
            idempotency_key_ttl_s=10_000,
            required_interventions=["3ds"],
            supported_interventions=[],
            returned_error_code="requires_3ds",
            agent_attempted_retry=True,
        )
        self.assertFalse(bad06.allowed)

    def test_pr07_to_pr12_x402_guards(self) -> None:
        # PR-07
        work_rec = {"agent": "agt_01", "cpu_ms": 420, "io_bytes": 16384, "seq": 9}
        work_hash = hashlib.sha256(
            json.dumps(work_rec, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        ok07 = audit_x402_proof_of_done_and_resolution_lineage(
            proof_of_done={
                "scheme": "tamga-ledger-v1",
                "receiptHash": work_hash,
                "verifyUrl": f"https://ledger.example/verify?receipt={work_hash}",
            },
            metered_work_record=work_rec,
            required_checks=[{"id": "c1", "status": "PASS"}, {"id": "c2", "status": "PASS"}],
            target_narrowed=False,
            claimed_resolution_state="SURVIVED",
            prior_record_hash="a" * 64,
            declared_prev_hash="a" * 64,
        )
        self.assertTrue(ok07.allowed)
        bad07 = audit_x402_proof_of_done_and_resolution_lineage(
            proof_of_done={
                "scheme": "tamga-ledger-v1",
                "receiptHash": work_hash,
                "verifyUrl": f"https://ledger.example/verify?receipt={work_hash}",
            },
            metered_work_record=work_rec,
            required_checks=[{"id": "c1", "status": "PASS"}, {"id": "c2", "status": "FAIL"}],
            target_narrowed=False,
            claimed_resolution_state="SURVIVED",
            prior_record_hash="a" * 64,
            declared_prev_hash="a" * 64,
        )
        self.assertFalse(bad07.allowed)

        # PR-08
        ok08 = audit_x402_evm_normative_must_and_supported_capabilities(
            eip712_domain_matched=True,
            recovered_signer="0xAbC123",
            authorization_from="0xabc123",
            signature_s_int=123456789,
            now_epoch_s=1_700_000_100,
            valid_after_s=1_700_000_000,
            valid_before_s=1_700_000_900,
            nonce_already_used=False,
            supported_capabilities={"assetTransferMethod": ["eip3009", "permit2"]},
            payment_requirements_extra={"assetTransferMethod": "eip3009"},
        )
        self.assertTrue(ok08.allowed)
        bad08 = audit_x402_evm_normative_must_and_supported_capabilities(
            eip712_domain_matched=True,
            recovered_signer="0xAbC123",
            authorization_from="0xabc123",
            signature_s_int=123456789,
            now_epoch_s=1_700_000_100,
            valid_after_s=1_700_000_000,
            valid_before_s=1_700_000_900,
            nonce_already_used=False,
            supported_capabilities={"assetTransferMethod": ["eip3009"]},
            payment_requirements_extra={"assetTransferMethod": "erc7710"},
        )
        self.assertFalse(bad08.allowed)

        # PR-09
        ok09 = audit_x402_svm_destination_ata_and_async_rpc(
            destination_ata_exists=True,
            destination_ata_owner="TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            expected_token_program="TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            is_async_client=True,
            uses_sync_solana_rpc_in_event_loop=False,
        )
        self.assertTrue(ok09.allowed)
        bad09 = audit_x402_svm_destination_ata_and_async_rpc(
            destination_ata_exists=True,
            destination_ata_owner="11111111111111111111111111111111",
            expected_token_program="TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            is_async_client=True,
            uses_sync_solana_rpc_in_event_loop=True,
        )
        self.assertFalse(bad09.allowed)

        # PR-10
        ok10 = audit_x402_stellar_typed_simulation_errors(
            diagnostic_kind="balance_low",
            diagnostic_account="G_PAYER",
            payer_account="G_PAYER",
            emitted_error_class="InsufficientBalanceError",
            preserves_raw_cause=True,
        )
        self.assertTrue(ok10.allowed)
        bad10 = audit_x402_stellar_typed_simulation_errors(
            diagnostic_kind="recipient_overflow",
            diagnostic_account="G_PAYEE",
            payer_account="G_PAYER",
            emitted_error_class="InsufficientBalanceError",
            preserves_raw_cause=True,
        )
        self.assertFalse(bad10.allowed)

        # PR-11
        ok11 = audit_x402_workers_bazaar_validator_and_go_mcp_timeout_cap(
            uses_runtime_ajv_compile_codegen=False,
            accepted_max_timeout_s=3600,
            max_request_timeout_s=90,
            recovery_retry_timeout_s=90,
        )
        self.assertTrue(ok11.allowed)
        bad11 = audit_x402_workers_bazaar_validator_and_go_mcp_timeout_cap(
            uses_runtime_ajv_compile_codegen=True,
            accepted_max_timeout_s=3600,
            max_request_timeout_s=90,
            recovery_retry_timeout_s=3600,
        )
        self.assertFalse(bad11.allowed)

        # PR-12
        ok12 = audit_x402_python_create_headers_and_uncertain_settlement_hook(
            create_headers_result={
                "verify": {"Authorization": "Bearer tok"},
                "settle": {"Authorization": "Bearer tok"},
                "supported": {"Authorization": "Bearer tok"},
            },
            settle_threw_error=True,
            on_settle_failure_recovered=False,
            on_uncertain_settlement_fired=True,
            hook_error_isolated=True,
            original_error_rethrown=True,
        )
        self.assertTrue(ok12.allowed)
        bad12 = audit_x402_python_create_headers_and_uncertain_settlement_hook(
            create_headers_result={"Authorization": "Bearer tok"},
            settle_threw_error=True,
            on_settle_failure_recovered=False,
            on_uncertain_settlement_fired=False,
            hook_error_isolated=True,
            original_error_rethrown=False,
        )
        self.assertFalse(bad12.allowed)

    def test_pr13_to_pr16_mcp_and_tau2_guards(self) -> None:
        # PR-13
        ok13 = audit_mcp_mrtr_still_waiting_and_tool_security_schemes(
            is_still_waiting_poll=True,
            prior_request_state="state_oob_01",
            returned_request_state="state_oob_01",
            returned_input_requests=[],
            holds_http_connection_open_unbounded=False,
            retry_after_ms=2000,
            supports_cancel_verb=True,
            tool_security_schemes=[{"type": "oauth2", "scopes": ["orders:write"]}],
            caller_authenticated=True,
            caller_scopes=["orders:read", "orders:write"],
        )
        self.assertTrue(ok13.allowed)
        bad13 = audit_mcp_mrtr_still_waiting_and_tool_security_schemes(
            is_still_waiting_poll=True,
            prior_request_state="state_oob_01",
            returned_request_state="state_oob_01",
            returned_input_requests=[{"type": "url"}],
            holds_http_connection_open_unbounded=True,
            retry_after_ms=50,
            supports_cancel_verb=False,
            tool_security_schemes=[{"type": "oauth2", "scopes": ["orders:write"]}],
            caller_authenticated=False,
            caller_scopes=[],
        )
        self.assertFalse(bad13.allowed)

        # PR-14
        ok14 = audit_mcp_trust_sensitivity_escalation_and_server_card(
            prior_sensitivity="low",
            input_sensitivity="high",
            resulting_sensitivity="high",
            prior_private_hint=False,
            input_private_hint=True,
            resulting_private_hint=True,
            target_tool_open_world_hint=False,
            server_card={
                "discovery_path": "/.well-known/ai-catalog.json",
                "protocol_versions": ["2025-11-25"],
                "transports": ["streamable-http"],
                "capabilities": {"tools": {}},
            },
        )
        self.assertTrue(ok14.allowed)
        bad14 = audit_mcp_trust_sensitivity_escalation_and_server_card(
            prior_sensitivity="high",
            input_sensitivity="low",
            resulting_sensitivity="low",
            prior_private_hint=True,
            input_private_hint=False,
            resulting_private_hint=True,
            target_tool_open_world_hint=True,
            server_card={"discovery_path": "/mcp"},
        )
        self.assertFalse(bad14.allowed)

        # PR-15
        ok15 = audit_tau2_reproducibility_manifest_and_silent_dotenv(
            manifest={
                "repo_commit_sha": "a4edc7654",
                "agent_model_snapshot": "gpt-5.2-2026-08-01",
                "user_model_snapshot": "gpt-4.1-mini-2026-06-01",
                "temperature": 0.0,
                "seed": 42,
                "num_trials": 4,
            },
            dotenv_present=False,
            import_stderr_output="",
        )
        self.assertTrue(ok15.allowed)
        bad15 = audit_tau2_reproducibility_manifest_and_silent_dotenv(
            manifest={"repo_commit_sha": "a4edc7654", "temperature": 0.7, "num_trials": 1},
            dotenv_present=False,
            import_stderr_output="WARNING | No .env file found",
        )
        self.assertFalse(bad15.allowed)

        # PR-16
        ok16 = audit_tau2_out_of_scope_termination_and_unscored_reward_guard(
            supported_termination_reasons=[
                "USER_STOP",
                "AGENT_STOP",
                "MAX_STEPS",
                "OUT_OF_SCOPE",
            ],
            simulation_termination_reason="OUT_OF_SCOPE",
            simulation_runs=[
                {"id": "sim_1", "reward_info": {"reward": 1.0}},
                {"id": "sim_2", "reward_info": None},
            ],
            crashes_on_none_reward_info=False,
        )
        self.assertTrue(ok16.allowed)
        bad16 = audit_tau2_out_of_scope_termination_and_unscored_reward_guard(
            supported_termination_reasons=["USER_STOP", "AGENT_STOP"],
            simulation_termination_reason="OUT_OF_SCOPE",
            simulation_runs=[{"id": "sim_2", "reward_info": None}],
            crashes_on_none_reward_info=True,
        )
        self.assertFalse(bad16.allowed)


if __name__ == "__main__":
    unittest.main()
