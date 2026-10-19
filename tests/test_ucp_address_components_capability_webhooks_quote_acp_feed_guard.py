"""Unit tests for Stage 50 UCP Address Line Components, Identity Selection & Capability Webhooks, Quote & Declared Fields, and ACP Host Gate / Server-Timing / Feed Update guards."""

from __future__ import annotations

import unittest

from lab.ucp_address_components_capability_webhooks_quote_acp_feed_guard import (
    evaluate_acp_host_gate_server_timing_and_feed_update_guard,
    evaluate_ucp_address_line_components_guard,
    evaluate_ucp_identity_selection_and_capability_webhook_guard,
    evaluate_ucp_quote_and_declared_fields_guard,
)


class Stage50AddressWebhooksQuoteACPFeedGuardTest(unittest.TestCase):
    def test_ucp_address_line_components_guard(self) -> None:
        valid = evaluate_ucp_address_line_components_guard(
            {
                "capability_target": "checkout",
                "destination_type": "shipping_address",
                "method_type": "shipping",
                "address_line_components": {
                    "street_name": "Avenida Paulista",
                    "street_number": "1578",
                    "additional_information": "Conjunto 42",
                    "district": "Bela Vista",
                },
                "address_code": "2929",
                "composed_street_address": "Avenida Paulista, 1578",
                "composed_extended_address": "Conjunto 42, Bela Vista",
            }
        )
        self.assertTrue(valid.admitted)
        self.assertEqual(valid.decision_code, "UCP_ADDRESS_LINE_COMPONENTS_VERIFIED")

        # Reject pickup business_location carrying address_line_components
        pickup_rejected = evaluate_ucp_address_line_components_guard(
            {
                "capability_target": "checkout",
                "destination_type": "business_location",
                "method_type": "pickup",
                "address_line_components": {"street_name": "Olaya Street"},
            }
        )
        self.assertFalse(pickup_rejected.admitted)
        self.assertEqual(
            pickup_rejected.decision_code,
            "ADDRESS_COMPONENTS_NON_SHIPPING_OR_CART_SCOPE_BLOCKED",
        )

        # Reject null component or address_code
        null_rejected = evaluate_ucp_address_line_components_guard(
            {
                "capability_target": "checkout",
                "destination_type": "shipping_address",
                "address_line_components": {"street_name": None},
            }
        )
        self.assertFalse(null_rejected.admitted)
        self.assertEqual(
            null_rejected.decision_code,
            "ADDRESS_COMPONENTS_NULL_VALUE_OR_UNKNOWN_KEY_BLOCKED",
        )

    def test_ucp_identity_selection_and_capability_webhook_guard(self) -> None:
        valid = evaluate_ucp_identity_selection_and_capability_webhook_guard(
            {
                "candidate_authorization_servers": (
                    {
                        "candidate_issuer": "https://bad-idp.example.com",
                        "metadata_issuer": "https://bad-idp.example.com/",
                        "oauth_well_known_status": 200,
                        "has_client_registration": True,
                        "business_accepts_tokens_from_as": True,
                    },
                    {
                        "candidate_issuer": "https://good-idp.example.com",
                        "metadata_issuer": "https://good-idp.example.com",
                        "oauth_well_known_status": 200,
                        "has_client_registration": True,
                        "business_accepts_tokens_from_as": True,
                    },
                ),
                "surfaced_discarded_issuers": ("https://bad-idp.example.com",),
                "capability_webhook": {
                    "platform_recognized": True,
                    "subscription_request_signed": True,
                    "webhook_url": "https://platform.example/webhooks/ucp",
                    "event_type": "dev.ucp.common.location.lookup:updated",
                    "is_shared_broadcast_capability": True,
                    "payload_is_thin_notification": True,
                    "platform_mutated_state_without_readback": False,
                    "delisted_on_removed_without_unfiltered_lookup": False,
                    "covered_components": ("webhook-id", "webhook-timestamp", "ucp-agent"),
                    "delivery_timestamp_skew_seconds": 15,
                    "signer_owns_resource_ids": True,
                },
            }
        )
        self.assertTrue(valid.admitted)
        self.assertEqual(
            valid.decision_code,
            "UCP_IDENTITY_SELECTION_AND_CAPABILITY_WEBHOOK_VERIFIED",
        )

        # Reject broadcast full-snapshot leak or delisting without unfiltered lookup
        invalid_webhook = evaluate_ucp_identity_selection_and_capability_webhook_guard(
            {
                "capability_webhook": {
                    "platform_recognized": True,
                    "subscription_request_signed": True,
                    "webhook_url": "https://platform.example/webhooks/ucp",
                    "event_type": "dev.ucp.common.location.lookup:removed",
                    "is_shared_broadcast_capability": True,
                    "payload_is_thin_notification": False,
                    "delisted_on_removed_without_unfiltered_lookup": True,
                }
            }
        )
        self.assertFalse(invalid_webhook.admitted)
        self.assertEqual(
            invalid_webhook.decision_code,
            "CAPABILITY_WEBHOOK_DELIVERY_OR_THIN_READBACK_BLOCKED",
        )

    def test_ucp_quote_and_declared_fields_guard(self) -> None:
        valid = evaluate_ucp_quote_and_declared_fields_guard(
            {
                "quote_context": {
                    "quote_accepted": True,
                    "quote_expired": False,
                    "polled_after_expires_at": False,
                    "complete_request_has_proposal_or_accepted_id": False,
                    "quote_totals_entries": (
                        {"type": "quote", "display_text": "Agreed B2B Quote #Q-901", "amount": 45000},
                    ),
                },
                "declared_fields_context": {
                    "config_keys": ("com.merchant.gift_wrap", "com.merchant.engraving"),
                    "checkout_required_declared_fields": ("com.merchant.gift_wrap",),
                    "checkout_declared_fields": ("com.merchant.gift_wrap",),
                    "line_item_required_declared_fields": ("com.merchant.engraving",),
                    "line_item_declared_fields": ("com.merchant.engraving",),
                    "checkout_status": "ready_for_complete",
                    "schema_validation_passed": True,
                    "is_complete_checkout_request": True,
                    "complete_request_includes_declared_fields": False,
                },
            }
        )
        self.assertTrue(valid.admitted)
        self.assertEqual(valid.decision_code, "UCP_QUOTE_AND_DECLARED_FIELDS_VERIFIED")

        # Reject cross-scope declared_fields or sending declared_fields on complete_checkout
        invalid_df = evaluate_ucp_quote_and_declared_fields_guard(
            {
                "declared_fields_context": {
                    "config_keys": ("com.merchant.gift_wrap", "com.merchant.engraving"),
                    "checkout_required_declared_fields": ("com.merchant.gift_wrap",),
                    "checkout_declared_fields": ("com.merchant.engraving",),
                    "line_item_required_declared_fields": ("com.merchant.engraving",),
                    "line_item_declared_fields": (),
                    "is_complete_checkout_request": True,
                    "complete_request_includes_declared_fields": True,
                }
            }
        )
        self.assertFalse(invalid_df.admitted)
        self.assertEqual(
            invalid_df.decision_code,
            "UCP_DECLARED_FIELDS_SCOPE_OR_LIFECYCLE_BLOCKED",
        )

    def test_acp_host_gate_server_timing_and_feed_update_guard(self) -> None:
        valid = evaluate_acp_host_gate_server_timing_and_feed_update_guard(
            {
                "host_spend_gate": {
                    "is_sensitive_spend_step": True,
                    "gate_enabled": True,
                    "gate_decision_verified": True,
                    "gate_allowed": True,
                    "bypassed_acp_wire_auth_headers": False,
                    "leaked_gate_api_key_in_model_prompt": False,
                },
                "server_timing_header": "acp;dur=42.3",
                "used_server_timing_as_sole_client_sla": False,
                "feed_update_context": {
                    "upsert_accepted": True,
                    "versioning_supported": True,
                    "feed_update_id": "upd_7kQ9mR",
                    "touched_products_last_update_ids": ("upd_7kQ9mR", "upd_7kQ9mR"),
                    "checkout_suggested_price_source_id": "upd_7kQ9mR",
                    "known_feed_update_ids": ("upd_7kQ9mR", "upd_older"),
                },
            }
        )
        self.assertTrue(valid.admitted)
        self.assertEqual(
            valid.decision_code,
            "ACP_HOST_GATE_SERVER_TIMING_AND_FEED_UPDATE_VERIFIED",
        )

        # Reject Server-Timing leaking SQL/topology or mismatched feed_update_id
        invalid = evaluate_acp_host_gate_server_timing_and_feed_update_guard(
            {
                "server_timing_header": 'acp;dur=42.3, postgres_sql_shard_01;dur=19.1;desc="internal"',
                "feed_update_context": {
                    "upsert_accepted": True,
                    "versioning_supported": True,
                    "feed_update_id": "upd_7kQ9mR",
                    "touched_products_last_update_ids": ("upd_stale",),
                },
            }
        )
        self.assertFalse(invalid.admitted)
        self.assertEqual(
            invalid.decision_code,
            "ACP_SERVER_TIMING_HEADER_LEAK_OR_MISUSE_BLOCKED",
        )


if __name__ == "__main__":
    unittest.main()
