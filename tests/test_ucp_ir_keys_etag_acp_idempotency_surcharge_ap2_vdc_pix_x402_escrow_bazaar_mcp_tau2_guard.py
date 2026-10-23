"""Unit tests for Stage 212 deterministic protocol & security guardrails (PR-01..PR-16)."""

from __future__ import annotations

import unittest

from lab.ucp_ir_keys_etag_acp_idempotency_surcharge_ap2_vdc_pix_x402_escrow_bazaar_mcp_tau2_guard import (
    audit_acp_idempotency_payload_digest_and_merchant_defined_data,
    audit_acp_surcharging_disclosure_and_schema_consistency_examples,
    audit_ap2_anonymous_vdc_intent_mandate_and_checkout_agent_role,
    audit_ap2_b2b_procurement_mandate_and_pix_instant_rail,
    audit_mcp_hidden_prompt_visibility_and_cacheable_result_scope,
    audit_mcp_token_metering_session_budget_and_paid_tool_x402_flow,
    audit_tau2_detailed_conversation_history_and_validate_recovery,
    audit_tau2_lazy_voice_import_and_retail_calculate_optionality,
    audit_ucp_extension_ratification_and_json_schema_formatting,
    audit_ucp_ir_codegen_and_cart_to_checkout_extension_projection,
    audit_ucp_signing_keys_migration_and_checkout_etag_if_match,
    audit_x402_fetch_bazaar_extension_preservation_and_atomic_integer_amount,
    audit_x402_non_usd_spend_cap_fx_and_arc_native_gas_eip3009,
    audit_x402_pooled_escrow_crew_policy_and_spend_controls_timeout_cap,
    audit_x402_presign_ofac_guard_and_knos_order_arbiter_acceptance,
    audit_x402_retry_updated_requirements_and_error_status_response_hook,
)


class Stage212GuardTests(unittest.TestCase):
    def test_ucp_acp_ap2_guards(self) -> None:
        # PR-01
        ok01 = audit_ucp_ir_codegen_and_cart_to_checkout_extension_projection(
            {
                "ucp_ir": {
                    "ir_version": "2026-10-23",
                    "unresolved_schema_refs": 0,
                    "deterministic_ast": True,
                },
                "cart_to_checkout_projection": {
                    "cart_extensions": ["dev.ucp.shopping.loyalty"],
                    "checkout_extensions": ["dev.ucp.shopping.loyalty", "dev.ucp.shopping.fulfillment"],
                    "extension_state_preserved": True,
                },
            }
        )
        self.assertTrue(ok01.admitted)
        bad01 = audit_ucp_ir_codegen_and_cart_to_checkout_extension_projection(
            {
                "ucp_ir": {"ir_version": "2026-10-23", "unresolved_schema_refs": 2, "deterministic_ast": False},
                "cart_to_checkout_projection": {
                    "cart_extensions": ["dev.ucp.shopping.loyalty"],
                    "checkout_extensions": [],
                    "extension_state_preserved": False,
                },
            }
        )
        self.assertFalse(bad01.admitted)

        # PR-02
        ok02 = audit_ucp_signing_keys_migration_and_checkout_etag_if_match(
            {
                "ucp_profile_keys": {
                    "keys": [{"kid": "k1", "kty": "EC"}],
                    "supports_legacy_signing_keys_fallback": True,
                },
                "checkout_update": {"if_match": '"etag_v3"', "current_etag": '"etag_v3"'},
            }
        )
        self.assertTrue(ok02.admitted)
        bad02 = audit_ucp_signing_keys_migration_and_checkout_etag_if_match(
            {
                "ucp_profile_keys": {"keys": [{"kid": "k1"}], "supports_legacy_signing_keys_fallback": False},
                "checkout_update": {"if_match": '"etag_v1"', "current_etag": '"etag_v2"'},
            }
        )
        self.assertFalse(bad02.admitted)

        # PR-03
        ok03 = audit_ucp_extension_ratification_and_json_schema_formatting(
            {
                "extension_governance": {
                    "claims_normative_ucp_namespace": True,
                    "ratified_by_domain_tech_council": True,
                    "independent_implementations": 3,
                },
                "schema_formatting": {"validate_json_prettier": True, "schema_formatting_clean": True},
            }
        )
        self.assertTrue(ok03.admitted)
        bad03 = audit_ucp_extension_ratification_and_json_schema_formatting(
            {
                "extension_governance": {
                    "claims_normative_ucp_namespace": True,
                    "ratified_by_domain_tech_council": False,
                    "independent_implementations": 1,
                },
                "schema_formatting": {"validate_json_prettier": False, "schema_formatting_clean": False},
            }
        )
        self.assertFalse(bad03.admitted)

        # PR-04
        ok04 = audit_acp_idempotency_payload_digest_and_merchant_defined_data(
            {
                "idempotency_check": {
                    "idempotency_key": "idem_99",
                    "first_request_sha256": "abc123",
                    "retry_request_sha256": "abc123",
                },
                "merchant_defined_data": {"invoice_number": "INV-2026-01", "loyalty_tier": "gold"},
            }
        )
        self.assertTrue(ok04.admitted)
        bad04 = audit_acp_idempotency_payload_digest_and_merchant_defined_data(
            {
                "idempotency_check": {
                    "idempotency_key": "idem_99",
                    "first_request_sha256": "abc123",
                    "retry_request_sha256": "mutated999",
                },
                "merchant_defined_data": {},
            }
        )
        self.assertFalse(bad04.admitted)

        # PR-05
        ok05 = audit_acp_surcharging_disclosure_and_schema_consistency_examples(
            {
                "surcharge_policy": {
                    "card_funding": "credit",
                    "surcharge_bps": 250,
                    "jurisdiction_allows_surcharge": True,
                    "explicit_line_item_disclosed": True,
                },
                "schema_consistency_audit": {"missing_descriptions_count": 0, "missing_examples_count": 0},
            }
        )
        self.assertTrue(ok05.admitted)
        bad05 = audit_acp_surcharging_disclosure_and_schema_consistency_examples(
            {
                "surcharge_policy": {
                    "card_funding": "debit",
                    "surcharge_bps": 450,
                    "jurisdiction_allows_surcharge": False,
                    "explicit_line_item_disclosed": False,
                },
                "schema_consistency_audit": {"missing_descriptions_count": 2, "missing_examples_count": 4},
            }
        )
        self.assertFalse(bad05.admitted)

        # PR-06
        ok06 = audit_ap2_anonymous_vdc_intent_mandate_and_checkout_agent_role(
            {
                "anonymous_vdc_mandate": {
                    "bbs_or_zkp_proof_valid": True,
                    "exposed_pii_fields": [],
                    "challenge_nonce_bound": True,
                },
                "checkout_agent_bridge": {
                    "shopping_agent_touches_raw_pan": False,
                    "checkout_agent_role_attested": True,
                },
            }
        )
        self.assertTrue(ok06.admitted)
        bad06 = audit_ap2_anonymous_vdc_intent_mandate_and_checkout_agent_role(
            {
                "anonymous_vdc_mandate": {
                    "bbs_or_zkp_proof_valid": False,
                    "exposed_pii_fields": ["ssn"],
                    "challenge_nonce_bound": False,
                },
                "checkout_agent_bridge": {
                    "shopping_agent_touches_raw_pan": True,
                    "checkout_agent_role_attested": False,
                },
            }
        )
        self.assertFalse(bad06.admitted)

        # PR-07
        ok07 = audit_ap2_b2b_procurement_mandate_and_pix_instant_rail(
            {
                "b2b_mandate": {
                    "purchase_order_id": "PO-8891",
                    "cost_center_id": "CC-AI-INFRA",
                    "authorized_signatory_verified": True,
                    "invoice_amount_minor": 500_000,
                    "cost_center_limit_minor": 1_000_000,
                },
                "pix_settlement": {
                    "rail": "br.gov.bcb.pix",
                    "pix_txid": "E12345678202610231200ABCDEF1234",
                    "bacen_dict_key_verified": True,
                },
            }
        )
        self.assertTrue(ok07.admitted)
        bad07 = audit_ap2_b2b_procurement_mandate_and_pix_instant_rail(
            {
                "b2b_mandate": {
                    "purchase_order_id": "",
                    "cost_center_id": "CC-AI-INFRA",
                    "authorized_signatory_verified": False,
                    "invoice_amount_minor": 2_000_000,
                    "cost_center_limit_minor": 1_000_000,
                },
                "pix_settlement": {
                    "rail": "pix_unverified",
                    "pix_txid": "short",
                    "bacen_dict_key_verified": False,
                },
            }
        )
        self.assertFalse(bad07.admitted)

    def test_x402_guards(self) -> None:
        # PR-08
        ok08 = audit_x402_pooled_escrow_crew_policy_and_spend_controls_timeout_cap(
            {
                "pooled_escrow": {
                    "pool_escrow_cap_minor": 10_000,
                    "crew_cumulative_claimed_minor": 4_000,
                    "member_call_minor": 500,
                    "member_per_call_cap_minor": 1_000,
                },
                "spend_controls": {
                    "server_max_timeout_seconds": 3600,
                    "client_max_timeout_seconds_cap": 300,
                    "signed_validity_window_seconds": 300,
                },
            }
        )
        self.assertTrue(ok08.admitted)
        bad08 = audit_x402_pooled_escrow_crew_policy_and_spend_controls_timeout_cap(
            {
                "pooled_escrow": {
                    "pool_escrow_cap_minor": 10_000,
                    "crew_cumulative_claimed_minor": 9_800,
                    "member_call_minor": 500,
                    "member_per_call_cap_minor": 300,
                },
                "spend_controls": {
                    "server_max_timeout_seconds": 86400,
                    "client_max_timeout_seconds_cap": 300,
                    "signed_validity_window_seconds": 86400,
                },
            }
        )
        self.assertFalse(bad08.admitted)

        # PR-09
        ok09 = audit_x402_retry_updated_requirements_and_error_status_response_hook(
            {
                "payment_required_retry": {
                    "latest_402_amount": "2500",
                    "signed_payload_amount": "2500",
                    "rebound_to_latest_402_requirements": True,
                },
                "paid_error_response": {
                    "http_status": 500,
                    "has_payment_response_header": True,
                    "on_payment_response_invoked": True,
                },
            }
        )
        self.assertTrue(ok09.admitted)
        bad09 = audit_x402_retry_updated_requirements_and_error_status_response_hook(
            {
                "payment_required_retry": {
                    "latest_402_amount": "2500",
                    "signed_payload_amount": "1000",
                    "rebound_to_latest_402_requirements": False,
                },
                "paid_error_response": {
                    "http_status": 500,
                    "has_payment_response_header": True,
                    "on_payment_response_invoked": False,
                },
            }
        )
        self.assertFalse(bad09.admitted)

        # PR-10
        ok10 = audit_x402_fetch_bazaar_extension_preservation_and_atomic_integer_amount(
            {
                "fetch_preserved_extensions_bazaar": True,
                "payment_requirements_amount": "5000",
            }
        )
        self.assertTrue(ok10.admitted)
        bad10 = audit_x402_fetch_bazaar_extension_preservation_and_atomic_integer_amount(
            {
                "fetch_preserved_extensions_bazaar": False,
                "payment_requirements_amount": "0.111",
            }
        )
        self.assertFalse(bad10.admitted)

        # PR-11
        ok11 = audit_x402_non_usd_spend_cap_fx_and_arc_native_gas_eip3009(
            {
                "spend_cap_asset": {
                    "quote_currency": "EUR",
                    "assumed_usd_1to1_without_fx": False,
                    "fx_oracle_rate_applied": True,
                },
                "arc_native_gas_settlement": {
                    "network": "eip155:5042",
                    "asset_transfer_method": "client-broadcast-eip3009",
                    "tx_receipt_confirmed": True,
                },
            }
        )
        self.assertTrue(ok11.admitted)
        bad11 = audit_x402_non_usd_spend_cap_fx_and_arc_native_gas_eip3009(
            {
                "spend_cap_asset": {
                    "quote_currency": "JPY",
                    "assumed_usd_1to1_without_fx": True,
                    "fx_oracle_rate_applied": False,
                },
                "arc_native_gas_settlement": {
                    "network": "eip155:5042",
                    "asset_transfer_method": "facilitator-erc20-transferFrom",
                    "tx_receipt_confirmed": False,
                },
            }
        )
        self.assertFalse(bad11.admitted)

        # PR-12
        ok12 = audit_x402_presign_ofac_guard_and_knos_order_arbiter_acceptance(
            {
                "presign_guard": {"ofac_sanctions_clear": True, "pre_sign_simulation_passed": True},
                "knos_order_escrow": {
                    "third_party_arbiter_did": "did:web:arbiter.knos.example",
                    "payer_did": "did:web:buyer.example",
                    "payee_did": "did:web:worker.example",
                    "signed_acceptance_verified": True,
                },
            }
        )
        self.assertTrue(ok12.admitted)
        bad12 = audit_x402_presign_ofac_guard_and_knos_order_arbiter_acceptance(
            {
                "presign_guard": {"ofac_sanctions_clear": False, "pre_sign_simulation_passed": False},
                "knos_order_escrow": {
                    "third_party_arbiter_did": "did:web:worker.example",
                    "payer_did": "did:web:buyer.example",
                    "payee_did": "did:web:worker.example",
                    "signed_acceptance_verified": False,
                },
            }
        )
        self.assertFalse(bad12.admitted)

    def test_mcp_and_tau2_guards(self) -> None:
        # PR-13
        ok13 = audit_mcp_token_metering_session_budget_and_paid_tool_x402_flow(
            {
                "mcp_session_budget": {
                    "consumed_tokens": 12_000,
                    "estimated_call_tokens": 3_000,
                    "max_session_tokens": 50_000,
                },
                "paid_tool_call": {
                    "requires_x402_payment": True,
                    "x402_payment_receipt_verified": True,
                    "tool_price_disclosed_in_descriptor": True,
                },
            }
        )
        self.assertTrue(ok13.admitted)
        bad13 = audit_mcp_token_metering_session_budget_and_paid_tool_x402_flow(
            {
                "mcp_session_budget": {
                    "consumed_tokens": 49_000,
                    "estimated_call_tokens": 5_000,
                    "max_session_tokens": 50_000,
                },
                "paid_tool_call": {
                    "requires_x402_payment": True,
                    "x402_payment_receipt_verified": False,
                    "tool_price_disclosed_in_descriptor": False,
                },
            }
        )
        self.assertFalse(bad13.admitted)

        # PR-14
        ok14 = audit_mcp_hidden_prompt_visibility_and_cacheable_result_scope(
            {
                "confidential_prompt": {"hidden": True, "rendered_in_user_ui": False},
                "cacheable_result": {
                    "ttlMs": 60_000,
                    "cacheScope": "session",
                    "contains_user_private_data": True,
                },
            }
        )
        self.assertTrue(ok14.admitted)
        bad14 = audit_mcp_hidden_prompt_visibility_and_cacheable_result_scope(
            {
                "confidential_prompt": {"hidden": True, "rendered_in_user_ui": True},
                "cacheable_result": {
                    "ttlMs": 60_000,
                    "cacheScope": "global",
                    "contains_user_private_data": True,
                },
            }
        )
        self.assertFalse(bad14.admitted)

        # PR-15
        ok15 = audit_tau2_lazy_voice_import_and_retail_calculate_optionality(
            {
                "eager_voice_import_on_text_run": False,
                "retail_math_eval": {
                    "inline_math_accurate": True,
                    "called_calculate_tool": False,
                    "penalized_for_missing_calculate": False,
                },
            }
        )
        self.assertTrue(ok15.admitted)
        bad15 = audit_tau2_lazy_voice_import_and_retail_calculate_optionality(
            {
                "eager_voice_import_on_text_run": True,
                "retail_math_eval": {
                    "inline_math_accurate": True,
                    "called_calculate_tool": False,
                    "penalized_for_missing_calculate": True,
                },
            }
        )
        self.assertFalse(bad15.admitted)

        # PR-16
        ok16 = audit_tau2_detailed_conversation_history_and_validate_recovery(
            {
                "simulation_export": {
                    "includes_full_turn_trajectory": True,
                    "includes_step_by_step_tool_traces": True,
                },
                "orchestrator_validation": {
                    "agent_msg_validate_threw": True,
                    "entire_eval_shut_down": False,
                    "recorded_as_task_level_error": True,
                },
            }
        )
        self.assertTrue(ok16.admitted)
        bad16 = audit_tau2_detailed_conversation_history_and_validate_recovery(
            {
                "simulation_export": {
                    "includes_full_turn_trajectory": False,
                    "includes_step_by_step_tool_traces": False,
                },
                "orchestrator_validation": {
                    "agent_msg_validate_threw": True,
                    "entire_eval_shut_down": True,
                    "recorded_as_task_level_error": False,
                },
            }
        )
        self.assertFalse(bad16.admitted)


if __name__ == "__main__":
    unittest.main()
