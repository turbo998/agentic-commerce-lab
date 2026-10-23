"""Unit tests for Stage 210 guardrails (210-Stage Milestone!)."""

from __future__ import annotations

import unittest

from lab.ucp_catalog_3ds2_acp_x402_ap2_sedi_x402_stellar_bazaar_mcp_tau2_guard import (
    audit_acp_3ds2_challenge_flow_and_x402_payment_method,
    audit_acp_selected_fulfillment_singular_and_date_version_snapshot,
    audit_ap2_mandate_vc_json_schema_and_sedi_keri_guardianship,
    audit_mcp_elicitation_pending_timeout_and_oob_https_resource,
    audit_mcp_sep2243_header_mismatch_32020_and_subscriptions_listen_envelope,
    audit_tau2_airline_cancellation_eligibility_and_agent_msg_validation_catch,
    audit_tau2_telecom_refuel_upper_bound_and_action_reward_basis,
    audit_ucp_asymmetric_key_signature_and_host_delegated_3ds2,
    audit_ucp_bulk_catalog_discovery_and_search_lookup_capabilities,
    audit_ucp_line_item_vs_catalog_item_id_and_order_total_enum,
    audit_x402_agent_switchboard_scitt_and_declarative_conformance,
    audit_x402_bazaar_indexing_readiness_preflight,
    audit_x402_kaspa_and_bch_utxo_exact_settlement,
    audit_x402_settlement_override_ceiling_and_axios_response_validator,
    audit_x402_stellar_fee_bump_signer_safety_and_svm_compute_unit_policy,
    audit_x402_stellar_smart_account_events_and_sponsored_fees,
)


class Stage210GuardTests(unittest.TestCase):
    def test_ucp_acp_ap2_guards(self) -> None:
        # PR-01
        ok01 = audit_ucp_bulk_catalog_discovery_and_search_lookup_capabilities(
            {
                "declared_catalog_capabilities": [
                    "dev.ucp.shopping.catalog.search",
                    "dev.ucp.shopping.catalog.lookup",
                ],
                "search_request": {"query": "running shoes", "page_size": 50},
                "lookup_request": {"ids": ["prod_01", "var_02"]},
                "bulk_snapshot": {"snapshot_id": "snap_2026_10_23", "web_scraping_fallback": False},
            }
        )
        self.assertTrue(ok01.admitted)
        bad01 = audit_ucp_bulk_catalog_discovery_and_search_lookup_capabilities(
            {
                "declared_catalog_capabilities": ["dev.ucp.shopping.catalog.search"],
                "search_request": {"query": "", "page_size": 5000},
                "lookup_request": {"ids": []},
                "bulk_snapshot": {"snapshot_id": None, "web_scraping_fallback": True},
            }
        )
        self.assertFalse(bad01.admitted)

        # PR-02
        ok02 = audit_ucp_asymmetric_key_signature_and_host_delegated_3ds2(
            {
                "signature_algorithm": "ES256",
                "jwks_kid": "kid-merchant-2026",
                "three_ds2_challenge": {
                    "delegated_to_host": True,
                    "merchant_injected_iframe": False,
                    "acs_url": "https://acs.issuer.example/challenge",
                    "three_ds_server_trans_id": "8a9b0c1d-2e3f-4a5b-8c9d-0e1f2a3b4c5d",
                },
            }
        )
        self.assertTrue(ok02.admitted)
        bad02 = audit_ucp_asymmetric_key_signature_and_host_delegated_3ds2(
            {
                "signature_algorithm": "HS256",
                "jwks_kid": "",
                "three_ds2_challenge": {
                    "delegated_to_host": False,
                    "merchant_injected_iframe": True,
                    "acs_url": "http://insecure.example/acs",
                    "three_ds_server_trans_id": "",
                },
            }
        )
        self.assertFalse(bad02.admitted)

        # PR-03
        ok03 = audit_ucp_line_item_vs_catalog_item_id_and_order_total_enum(
            {
                "line_items": [
                    {"id": "li_01", "item": {"id": "sku_abc"}},
                    {"id": "li_02", "item": {"id": "sku_abc"}},
                ],
                "order_totals": [
                    {"type": "subtotal", "amount": 2000},
                    {"type": "fulfillment", "amount": 500},
                    {"type": "total", "amount": 2500},
                ],
            }
        )
        self.assertTrue(ok03.admitted)
        bad03 = audit_ucp_line_item_vs_catalog_item_id_and_order_total_enum(
            {
                "line_items": [{"id": "sku_abc", "item": {"id": "sku_abc"}}],
                "order_totals": [{"type": "shipping_total", "amount": 500}],
            }
        )
        self.assertFalse(bad03.admitted)

        # PR-04
        ok04 = audit_acp_selected_fulfillment_singular_and_date_version_snapshot(
            {
                "schema_names": ["CheckoutSession", "SelectedFulfillmentOption"],
                "spec_version_dir": "2026-10-23",
                "live_edit_in_snapshot": False,
            }
        )
        self.assertTrue(ok04.admitted)
        bad04 = audit_acp_selected_fulfillment_singular_and_date_version_snapshot(
            {
                "schema_names": ["AvailablePromotion", "SelectedFulfillmentOptions"],
                "spec_version_dir": "2026-10-23",
                "live_edit_in_snapshot": True,
            }
        )
        self.assertFalse(bad04.admitted)

        # PR-05
        ok05 = audit_acp_3ds2_challenge_flow_and_x402_payment_method(
            {
                "acp_3ds2_flow": {
                    "three_ds_version": "2.2.0",
                    "transaction_status": "C",
                    "acs_challenge_url": "https://acs.bank.example/stepup",
                },
                "acp_x402_payment_method": {
                    "type": "x402",
                    "scheme": "exact",
                    "network": "eip155:8453",
                    "max_amount_minor": 1500,
                },
            }
        )
        self.assertTrue(ok05.admitted)
        bad05 = audit_acp_3ds2_challenge_flow_and_x402_payment_method(
            {
                "acp_3ds2_flow": {
                    "three_ds_version": "1.0.2",
                    "transaction_status": "C",
                    "acs_challenge_url": "http://acs.bank.example/stepup",
                },
                "acp_x402_payment_method": {
                    "type": "x402",
                    "scheme": "unknown",
                    "network": "base",
                    "max_amount_minor": 0,
                },
            }
        )
        self.assertFalse(bad05.admitted)

        # PR-06
        ok06 = audit_ap2_mandate_vc_json_schema_and_sedi_keri_guardianship(
            {
                "mandate_vc": {
                    "type": ["VerifiableCredential", "IntentMandateCredential"],
                    "credentialSchema": {
                        "id": "https://ap2.agenticcommerce.dev/schemas/intent-mandate-vc.json",
                        "type": "JsonSchema",
                    },
                },
                "sedi_keri_guardianship": {
                    "guardian_keri_aid": "EBfdlu8R27Fbx-ehrqwImnK-8Cm79sqbAQ4MmvEAYqao",
                    "keri_kel_verified": True,
                    "ward_spend_minor": 1500,
                    "guardian_cap_minor": 2000,
                },
            }
        )
        self.assertTrue(ok06.admitted)
        bad06 = audit_ap2_mandate_vc_json_schema_and_sedi_keri_guardianship(
            {
                "mandate_vc": {
                    "type": ["VerifiableCredential"],
                    "credentialSchema": {},
                },
                "sedi_keri_guardianship": {
                    "guardian_keri_aid": "",
                    "keri_kel_verified": False,
                    "ward_spend_minor": 5000,
                    "guardian_cap_minor": 2000,
                },
            }
        )
        self.assertFalse(bad06.admitted)

    def test_x402_guards(self) -> None:
        # PR-07
        ok07 = audit_x402_settlement_override_ceiling_and_axios_response_validator(
            {
                "authorized_max_amount_minor": 1000,
                "resolved_override_amount_minor": 800,
                "axios_validate_paid_response_configured": True,
                "paid_response_schema_valid": True,
            }
        )
        self.assertTrue(ok07.admitted)
        bad07 = audit_x402_settlement_override_ceiling_and_axios_response_validator(
            {
                "authorized_max_amount_minor": 1000,
                "resolved_override_amount_minor": 1200,
                "axios_validate_paid_response_configured": False,
                "paid_response_schema_valid": False,
            }
        )
        self.assertFalse(bad07.admitted)

        # PR-08
        ok08 = audit_x402_stellar_smart_account_events_and_sponsored_fees(
            {
                "are_fees_sponsored": True,
                "rejected_non_transfer_contract_event": False,
                "simulation_contract_events": [
                    {"topic": "spend_cap_checked", "sep41_compliant": False},
                    {"topic": "transfer", "sep41_compliant": True},
                ],
            }
        )
        self.assertTrue(ok08.admitted)
        bad08 = audit_x402_stellar_smart_account_events_and_sponsored_fees(
            {
                "are_fees_sponsored": False,
                "rejected_non_transfer_contract_event": True,
                "simulation_contract_events": [{"topic": "spend_cap_checked", "sep41_compliant": False}],
            }
        )
        self.assertFalse(bad08.admitted)

        # PR-09
        ok09 = audit_x402_stellar_fee_bump_signer_safety_and_svm_compute_unit_policy(
            {
                "stellar_fee_bump_signer": "GFEEBUMP777",
                "facilitator_safety_signing_addresses": ["GFACILITATOR111", "GFEEBUMP777"],
                "stellar_tx_recipient": "GMERCHANT999",
                "svm_compute_unit_policy": {
                    "tx_compute_unit_limit": 200_000,
                    "operator_max_cu": 300_000,
                },
            }
        )
        self.assertTrue(ok09.admitted)
        bad09 = audit_x402_stellar_fee_bump_signer_safety_and_svm_compute_unit_policy(
            {
                "stellar_fee_bump_signer": "GFEEBUMP777",
                "facilitator_safety_signing_addresses": ["GFACILITATOR111"],
                "stellar_tx_recipient": "GFEEBUMP777",
                "svm_compute_unit_policy": {
                    "tx_compute_unit_limit": 450_000,
                    "operator_max_cu": 300_000,
                },
            }
        )
        self.assertFalse(bad09.admitted)

        # PR-10
        ok10 = audit_x402_agent_switchboard_scitt_and_declarative_conformance(
            {
                "agent_switchboard": {
                    "protocol": "x402.agent-switchboard/v0",
                    "scitt_transparency_verified": True,
                    "relay_ttl_seconds": 300,
                },
                "conformance_profile": {
                    "spec_version": "2.0.0",
                    "declarative_profile_valid": True,
                    "failed_assertions": 0,
                },
            }
        )
        self.assertTrue(ok10.admitted)
        bad10 = audit_x402_agent_switchboard_scitt_and_declarative_conformance(
            {
                "agent_switchboard": {
                    "protocol": "x402.agent-switchboard/v0",
                    "scitt_transparency_verified": False,
                    "relay_ttl_seconds": 999999,
                },
                "conformance_profile": {
                    "spec_version": "2.0.0",
                    "declarative_profile_valid": False,
                    "failed_assertions": 3,
                },
            }
        )
        self.assertFalse(bad10.admitted)

        # PR-11
        ok11 = audit_x402_bazaar_indexing_readiness_preflight(
            {
                "bazaar_extension_present_in_402": True,
                "bazaar_input_output_schema_valid": True,
                "resource_url_public_https": True,
                "cdp_facilitator_settlement_confirmed": True,
            }
        )
        self.assertTrue(ok11.admitted)
        bad11 = audit_x402_bazaar_indexing_readiness_preflight(
            {
                "bazaar_extension_present_in_402": True,
                "bazaar_input_output_schema_valid": False,
                "resource_url_public_https": True,
                "cdp_facilitator_settlement_confirmed": False,
            }
        )
        self.assertFalse(bad11.admitted)

        # PR-12
        ok12 = audit_x402_kaspa_and_bch_utxo_exact_settlement(
            {
                "kaspa_exact": {
                    "network": "kaspa:mainnet",
                    "output_sompi": 100_000_000,
                    "required_sompi": 100_000_000,
                    "unconfirmed_rbf_replaceable": False,
                },
                "bch_exact": {
                    "output_satoshis": 10_000,
                    "required_satoshis": 10_000,
                    "sighash_forkid_set": True,
                },
            }
        )
        self.assertTrue(ok12.admitted)
        bad12 = audit_x402_kaspa_and_bch_utxo_exact_settlement(
            {
                "kaspa_exact": {
                    "network": "kaspa:mainnet",
                    "output_sompi": 50_000_000,
                    "required_sompi": 100_000_000,
                    "unconfirmed_rbf_replaceable": True,
                },
                "bch_exact": {
                    "output_satoshis": 200,
                    "required_satoshis": 10_000,
                    "sighash_forkid_set": False,
                },
            }
        )
        self.assertFalse(bad12.admitted)

    def test_mcp_and_tau2_guards(self) -> None:
        # PR-13
        ok13 = audit_mcp_sep2243_header_mismatch_32020_and_subscriptions_listen_envelope(
            {
                "header_mismatch_error_code": -32020,
                "subscriptions_listen_response": {
                    "envelope_type": "SubscriptionsListenResultResponse",
                    "meta_type": "SubscriptionsListenResultMeta",
                },
            }
        )
        self.assertTrue(ok13.admitted)
        bad13 = audit_mcp_sep2243_header_mismatch_32020_and_subscriptions_listen_envelope(
            {
                "header_mismatch_error_code": -32001,
                "subscriptions_listen_response": {
                    "envelope_type": "EmptyResult",
                    "meta_type": "SubscriptionsListenMeta",
                },
            }
        )
        self.assertFalse(bad13.admitted)

        # PR-14
        ok14 = audit_mcp_elicitation_pending_timeout_and_oob_https_resource(
            {
                "elicitation_pending_notification": {
                    "method": "notifications/elicitation/pending",
                    "elicitationId": "elic_01",
                    "client_timeout_extended": True,
                },
                "oob_resource": {
                    "httpUrl": "https://cdn.merchant.example/catalog/export.parquet",
                    "httpUrlExpiresAt": 1761264000,
                    "now_epoch": 1761177600,
                },
            }
        )
        self.assertTrue(ok14.admitted)
        bad14 = audit_mcp_elicitation_pending_timeout_and_oob_https_resource(
            {
                "elicitation_pending_notification": {
                    "method": "notifications/elicitation/pending",
                    "elicitationId": "",
                    "client_timeout_extended": False,
                },
                "oob_resource": {
                    "httpUrl": "http://cdn.merchant.example/catalog/export.parquet",
                    "httpUrlExpiresAt": 1761100000,
                    "now_epoch": 1761177600,
                },
            }
        )
        self.assertFalse(bad14.admitted)

        # PR-15
        ok15 = audit_tau2_telecom_refuel_upper_bound_and_action_reward_basis(
            {
                "refuel_data_gb": 1.5,
                "user_needed_data_gb": 1.0,
                "hardcoded_exact_2gb_enforced": False,
                "reward_basis": ["DB", "ACTION", "COMMUNICATE"],
            }
        )
        self.assertTrue(ok15.admitted)
        bad15 = audit_tau2_telecom_refuel_upper_bound_and_action_reward_basis(
            {
                "refuel_data_gb": 1.5,
                "user_needed_data_gb": 1.0,
                "hardcoded_exact_2gb_enforced": True,
                "reward_basis": ["DB"],
            }
        )
        self.assertFalse(bad15.admitted)

        # PR-16
        ok16 = audit_tau2_airline_cancellation_eligibility_and_agent_msg_validation_catch(
            {
                "unhandled_agent_msg_validate_exception": False,
                "booking_cancellation_check": {
                    "booked_within_24h": True,
                    "flight_cancelled_by_airline": False,
                    "is_business_class": False,
                    "covered_by_travel_insurance": False,
                    "test_expects_cancelled": True,
                },
            }
        )
        self.assertTrue(ok16.admitted)
        bad16 = audit_tau2_airline_cancellation_eligibility_and_agent_msg_validation_catch(
            {
                "unhandled_agent_msg_validate_exception": True,
                "booking_cancellation_check": {
                    "booked_within_24h": False,
                    "flight_cancelled_by_airline": False,
                    "is_business_class": False,
                    "covered_by_travel_insurance": False,
                    "test_expects_cancelled": True,
                },
            }
        )
        self.assertFalse(bad16.admitted)


if __name__ == "__main__":
    unittest.main()
