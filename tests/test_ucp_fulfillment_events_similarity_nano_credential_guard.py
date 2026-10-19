"""Unit tests for Stage 47 UCP standardized fulfillment events (#979),
catalog similarity extension & seller/business identity (#977/#962/#939),
Nano (XNO) payment instrument session binding (#862), and credential echo /
cart-only checkout / escalation / deferred terms / lodging guards
(#868/#940/#912/#908/#934/#870).
"""

from __future__ import annotations

import base64
import unittest

from lab.ucp_fulfillment_events_similarity_nano_credential_guard import (
    evaluate_ucp_catalog_similarity_extension_and_image_anchor_guard,
    evaluate_ucp_credential_echo_cart_checkout_and_deferred_terms_guard,
    evaluate_ucp_nano_payment_instrument_and_session_binding_guard,
    evaluate_ucp_standardized_fulfillment_events_and_split_shipment_guard,
)


class TestUcpFulfillmentEventsSimilarityNanoCredentialGuard(unittest.TestCase):
    def test_standardized_fulfillment_events_and_split_shipment_guard(self) -> None:
        valid = evaluate_ucp_standardized_fulfillment_events_and_split_shipment_guard(
            {
                "fulfillment_events": [
                    {
                        "id": "evt_1",
                        "type": "delivered",
                        "line_items": [{"id": "li_shoes", "quantity": 1}],
                    },
                    {
                        "id": "evt_2",
                        "type": "failed_attempt",
                        "description": "Delivery could not be completed because no one was available.",
                        "line_items": [{"id": "li_shoes", "quantity": 1}],
                    },
                ],
                "line_items": [
                    {
                        "id": "li_shoes",
                        "quantity": {"original": 2, "total": 2, "fulfilled": 1},
                        "status": "partial",
                    }
                ],
            }
        )
        self.assertTrue(valid["allowed"])
        self.assertEqual(valid["well_known_event_count"], 1)
        self.assertEqual(valid["custom_event_count"], 1)

        synonym_blocked = (
            evaluate_ucp_standardized_fulfillment_events_and_split_shipment_guard(
                {
                    "fulfillment_events": [
                        {
                            "id": "evt_bad",
                            "type": "finished",
                            "description": "Package was delivered",
                        }
                    ]
                }
            )
        )
        self.assertFalse(synonym_blocked["allowed"])
        self.assertEqual(
            synonym_blocked["decision_code"],
            "CUSTOM_SYNONYM_FOR_WELL_KNOWN_FULFILLMENT_EVENT_BLOCKED",
        )
        self.assertEqual(synonym_blocked["canonical_well_known_type"], "delivered")

        missing_desc = (
            evaluate_ucp_standardized_fulfillment_events_and_split_shipment_guard(
                {
                    "fulfillment_events": [
                        {
                            "id": "evt_custom_no_desc",
                            "type": "failed_attempt",
                            "description": "   ",
                        }
                    ]
                }
            )
        )
        self.assertFalse(missing_desc["allowed"])
        self.assertEqual(
            missing_desc["decision_code"],
            "CUSTOM_FULFILLMENT_EVENT_MISSING_DESCRIPTION_BLOCKED",
        )

        sum_blocked = (
            evaluate_ucp_standardized_fulfillment_events_and_split_shipment_guard(
                {
                    "fulfillment_events": [{"id": "evt_1", "type": "delivered"}],
                    "platform_summed_event_quantities": True,
                }
            )
        )
        self.assertFalse(sum_blocked["allowed"])
        self.assertEqual(
            sum_blocked["decision_code"],
            "EVENT_QUANTITY_SUMMING_OR_GLOBAL_STATUS_COLLAPSE_BLOCKED",
        )

    def test_catalog_similarity_extension_and_image_anchor_guard(self) -> None:
        img_b64 = base64.b64encode(b"fake-webp-bytes").decode("ascii")
        valid = evaluate_ucp_catalog_similarity_extension_and_image_anchor_guard(
            {
                "similarity_extension_declared": True,
                "request_uses_like_or_include": True,
                "similarity_config": {
                    "like": {
                        "max_items": 2,
                        "images": {
                            "max_items": 1,
                            "types": ["image/jpeg", "image/webp"],
                            "max_bytes": 1024,
                        },
                    }
                },
                "like_anchors": [
                    {"id": "prod_1", "resolved": True},
                    {
                        "image": {
                            "content_type": "image/webp",
                            "data": img_b64,
                        }
                    },
                    {"id": "prod_3_truncated", "resolved": True},
                ],
            }
        )
        self.assertTrue(valid["allowed"])
        self.assertEqual(valid["accepted_anchor_count"], 2)
        self.assertIn("batch_limit_applied", valid["messages"])

        undeclared = evaluate_ucp_catalog_similarity_extension_and_image_anchor_guard(
            {
                "similarity_extension_declared": False,
                "request_uses_like_or_include": True,
            }
        )
        self.assertFalse(undeclared["allowed"])
        self.assertEqual(
            undeclared["decision_code"],
            "SIMILARITY_EXTENSION_NOT_DECLARED_IN_PROFILE_BLOCKED",
        )

        fallback_blocked = (
            evaluate_ucp_catalog_similarity_extension_and_image_anchor_guard(
                {
                    "similarity_extension_declared": True,
                    "request_uses_like_or_include": True,
                    "similarity_config": {"like": {"max_items": 1}},
                    "like_anchors": [
                        {
                            "image": {
                                "content_type": "image/png",
                                "data": img_b64,
                            }
                        }
                    ],
                    "fallback_to_plain_search_when_all_anchors_dropped": True,
                }
            )
        )
        self.assertFalse(fallback_blocked["allowed"])
        self.assertEqual(
            fallback_blocked["decision_code"],
            "ALL_ANCHORS_DROPPED_FALLBACK_SEARCH_FORBIDDEN",
        )

    def test_nano_payment_instrument_and_session_binding_guard(self) -> None:
        addr = "nano_1qno3zgq7qnr3rqbypqbs77wpan7aq3e3ou73go3rqx98eem3tckq1q4hie3"
        raw_amt = "2500000000000000000000000000000"
        blk = "6EE79D2BA2A8995179E4C2E12B10BAA7F828C9AD5D7F2D00E8D5B8A8D5C96C29"

        valid = evaluate_ucp_nano_payment_instrument_and_session_binding_guard(
            {
                "issued_receive_address": addr,
                "issued_amount_raw": raw_amt,
                "settlement_block": blk,
                "network": "mainnet",
                "ledger_block_destination": addr,
                "ledger_block_amount_raw": raw_amt,
                "ledger_block_is_send": True,
                "ledger_block_confirmed": True,
            }
        )
        self.assertTrue(valid["allowed"])
        self.assertEqual(
            valid["decision_code"], "UCP_NANO_PAYMENT_INSTRUMENT_SETTLEMENT_VERIFIED"
        )

        circular_override = (
            evaluate_ucp_nano_payment_instrument_and_session_binding_guard(
                {
                    "issued_receive_address": addr,
                    "issued_amount_raw": raw_amt,
                    "submitted_receive_address": "nano_3bad3zgq7qnr3rqbypqbs77wpan7aq3e3ou73go3rqx98eem3tckq1q4hie3",
                    "settlement_block": blk,
                }
            )
        )
        self.assertFalse(circular_override["allowed"])
        self.assertEqual(
            circular_override["decision_code"],
            "NANO_CLIENT_SUBMITTED_BINDING_OVERRIDE_BLOCKED",
        )

        replay_claim = evaluate_ucp_nano_payment_instrument_and_session_binding_guard(
            {
                "issued_receive_address": addr,
                "issued_amount_raw": raw_amt,
                "settlement_block": blk,
                "network": "mainnet",
                "claimed_network_blocks": [("mainnet", blk)],
                "is_idempotent_retry_of_claiming_op": False,
            }
        )
        self.assertFalse(replay_claim["allowed"])
        self.assertEqual(
            replay_claim["decision_code"],
            "NANO_SETTLEMENT_BLOCK_REPLAY_CLAIM_BLOCKED",
        )

        amount_mismatch = (
            evaluate_ucp_nano_payment_instrument_and_session_binding_guard(
                {
                    "issued_receive_address": addr,
                    "issued_amount_raw": raw_amt,
                    "settlement_block": blk,
                    "ledger_block_destination": addr,
                    "ledger_block_amount_raw": "2000000000000000000000000000000",
                }
            )
        )
        self.assertFalse(amount_mismatch["allowed"])
        self.assertEqual(
            amount_mismatch["decision_code"],
            "NANO_BLOCK_AMOUNT_MISMATCH_OR_MULTI_BLOCK_SUM_BLOCKED",
        )

    def test_credential_echo_cart_checkout_and_deferred_terms_guard(self) -> None:
        valid = evaluate_ucp_credential_echo_cart_checkout_and_deferred_terms_guard(
            {
                "endpoint": "/checkout-sessions/chk_1",
                "response_credential_fields": ["brand", "last4"],
                "rest_operation": "create_checkout",
                "has_idempotency_key": False,
                "is_create_checkout": True,
                "has_line_items": False,
                "has_cart_id": True,
                "checkout_status": "requires_escalation",
                "continue_url": "https://shop.example.com/checkout/chk_1/escalate",
                "fully_deferred_payment_terms": True,
                "complete_payment_object": {},
                "signature_is_asn1_der": False,
                "has_ucp_agent_header": True,
                "ucp_agent_in_covered_components": True,
                "stay_start_date": "2026-11-10",
                "stay_end_date": "2026-11-13",
                "billed_nights": 3,
            }
        )
        self.assertTrue(valid["allowed"])
        self.assertEqual(
            valid["decision_code"],
            "UCP_CREDENTIAL_CART_ESCALATION_DEFERRED_LODGING_VERIFIED",
        )

        cred_echo = evaluate_ucp_credential_echo_cart_checkout_and_deferred_terms_guard(
            {
                "endpoint": "/checkout-sessions/chk_1",
                "response_credential_fields": ["number", "cryptogram"],
            }
        )
        self.assertFalse(cred_echo["allowed"])
        self.assertEqual(
            cred_echo["decision_code"],
            "SENSITIVE_CREDENTIAL_FIELD_ECHOED_OUTSIDE_DETOKENIZE_BLOCKED",
        )

        missing_continue = (
            evaluate_ucp_credential_echo_cart_checkout_and_deferred_terms_guard(
                {
                    "checkout_status": "requires_escalation",
                    "continue_url": "",
                }
            )
        )
        self.assertFalse(missing_continue["allowed"])
        self.assertEqual(
            missing_continue["decision_code"],
            "REQUIRES_ESCALATION_MISSING_CONTINUE_URL_BLOCKED",
        )

        extra_night = (
            evaluate_ucp_credential_echo_cart_checkout_and_deferred_terms_guard(
                {
                    "stay_start_date": "2026-11-10",
                    "stay_end_date": "2026-11-13",
                    "billed_nights": 4,
                }
            )
        )
        self.assertFalse(extra_night["allowed"])
        self.assertEqual(
            extra_night["decision_code"],
            "LODGING_STAY_CHECKOUT_DATE_COUNTED_AS_EXTRA_NIGHT_BLOCKED",
        )


if __name__ == "__main__":
    unittest.main()
