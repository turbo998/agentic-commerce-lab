"""Unit tests for Stage 39 UCP Food Checkout (#897), Lodging Deterministic Cancellation
Schedule (#861), Bulk Catalog Feed (#866), Identity Linking (#876/#891), and RFC 9421 ECDSA Raw r||s (#963).
"""

from __future__ import annotations

import hashlib
import unittest

from lab.ucp_food_lodging_feed_identity_guard import (
    evaluate_ucp_bulk_catalog_feed_guard,
    evaluate_ucp_food_checkout_and_fulfillment_guard,
    evaluate_ucp_identity_linking_and_ecdsa_raw_rs_guard,
    evaluate_ucp_lodging_cancellation_schedule_guard,
)


class TestUCPFoodLodgingFeedIdentityGuard(unittest.TestCase):
    def test_food_checkout_single_establishment_modifications_and_notes(self) -> None:
        ok = evaluate_ucp_food_checkout_and_fulfillment_guard(
            session_establishment_id="est_luigis_01",
            line_items=(
                {
                    "quantity": 2,
                    "dish": {
                        "id": "dish_margherita_12",
                        "establishment_id": "est_luigis_01",
                        "price_minor": 1400,
                        "modifications": (
                            {"id": "mod_extra_mozzarella", "price_minor": 200, "quantity": 1},
                        ),
                        "note": "Well done crust",
                    },
                    "reported_subtotal_minor": 3200,
                },
            ),
            paid_addon_keywords=("add avocado", "extra bacon"),
            note_attempts_silent_surcharge=False,
            fulfillment_destinations_count=1,
            buyer_selected_tip_minor=500,
            totals_tip_entry_minor=500,
        )
        self.assertTrue(ok.admitted)
        self.assertEqual(ok.computed_subtotal_minor, 3200)

        note_abuse = evaluate_ucp_food_checkout_and_fulfillment_guard(
            session_establishment_id="est_luigis_01",
            line_items=(
                {
                    "quantity": 1,
                    "dish": {
                        "id": "dish_caesar",
                        "establishment_id": "est_luigis_01",
                        "price_minor": 1200,
                        "modifications": (),
                        "note": "Please add avocado to salad",
                    },
                    "reported_subtotal_minor": 1200,
                },
            ),
            paid_addon_keywords=("add avocado",),
            note_attempts_silent_surcharge=True,
            fulfillment_destinations_count=1,
            buyer_selected_tip_minor=200,
            totals_tip_entry_minor=200,
        )
        self.assertFalse(note_abuse.admitted)
        self.assertEqual(note_abuse.decision_code, "PAID_ADDON_IN_FREEFORM_KITCHEN_NOTE_BLOCKED")
        self.assertIn("note_contains_modification", note_abuse.warning_codes)

    def test_lodging_cancellation_half_open_boundary_and_multi_stay_guard(self) -> None:
        intervals = (
            {"start_epoch": 1_000, "end_epoch": 2_000, "outcome_type": "fixed_fee", "amount_minor": 0},
            {"start_epoch": 2_000, "end_epoch": 3_000, "outcome_type": "percentage", "basis_points": 5000},
            {"start_epoch": 3_000, "end_epoch": None, "outcome_type": "percentage", "basis_points": 10000},
        )
        # Exactly at cutoff 2_000 -> half-open `[start, end)` selects index 1 (50% penalty = 10_000)
        boundary = evaluate_ucp_lodging_cancellation_schedule_guard(
            anchor_epoch=3_000,
            intervals=intervals,
            eval_instant_epoch=2_000,
            authoritative_booking_base_amount_minor=20_000,
            platform_extrapolated_cash_from_symbolic_without_base=False,
            targeted_stays_count=1,
            platform_multiplied_penalty_across_stays=False,
        )
        self.assertTrue(boundary.admitted)
        self.assertEqual(boundary.selected_interval_index, 1)
        self.assertEqual(boundary.resolved_penalty_minor, 10_000)

        # Multiplying penalty across multiple targeted stays is blocked
        multi_stay_err = evaluate_ucp_lodging_cancellation_schedule_guard(
            anchor_epoch=3_000,
            intervals=intervals,
            eval_instant_epoch=2_000,
            authoritative_booking_base_amount_minor=20_000,
            platform_extrapolated_cash_from_symbolic_without_base=False,
            targeted_stays_count=2,
            platform_multiplied_penalty_across_stays=True,
        )
        self.assertFalse(multi_stay_err.admitted)
        self.assertEqual(multi_stay_err.decision_code, "MULTI_STAY_PENALTY_MULTIPLICATION_BLOCKED")

    def test_bulk_catalog_feed_digest_and_live_serving_authority(self) -> None:
        payload = '{"id":"prod_1","title":"Espresso Machine"}'
        digest = "sha-256=:" + hashlib.sha256(payload.encode("utf-8")).hexdigest() + ":"
        ok = evaluate_ucp_bulk_catalog_feed_guard(
            manifest_snapshot_immutable=True,
            feed_files=({"format": "jsonl+gzip", "content": payload, "rfc9530_digest": digest},),
            used_directly_for_checkout_without_live_lookup=False,
        )
        self.assertTrue(ok.admitted)
        self.assertEqual(ok.verified_file_count, 1)

        stale_checkout = evaluate_ucp_bulk_catalog_feed_guard(
            manifest_snapshot_immutable=True,
            feed_files=({"format": "jsonl+gzip", "content": payload, "rfc9530_digest": digest},),
            used_directly_for_checkout_without_live_lookup=True,
        )
        self.assertFalse(stale_checkout.admitted)
        self.assertEqual(stale_checkout.decision_code, "STALE_BULK_FEED_USED_AS_CHECKOUT_AUTHORITY_BLOCKED")

    def test_identity_linking_multi_entry_dns_email_and_ecdsa_raw_rs(self) -> None:
        auth_servers = (
            {
                "entry_uri": "https://account.merchant.example.com",
                "discovered_metadata_issuer": "https://auth.provider.example/authentication/12345",
                "platform_holds_usable_client": True,
            },
            {
                "entry_uri": "https://auth.provider.example/authentication/12345",
                "discovered_metadata_issuer": "https://auth.provider.example/authentication/12345",
                "platform_holds_usable_client": True,
            },
        )
        ok = evaluate_ucp_identity_linking_and_ecdsa_raw_rs_guard(
            authorization_servers=auth_servers,
            platform_aborted_on_first_mismatch=False,
            attempt_accelerated_email_autolink=True,
            idp_email_verified=True,
            dns_txt_delegated_issuer="https://accounts.google.com",
            grant_iss="https://accounts.google.com",
            grant_sub="sub_user_42",
            business_verified_existing_account_email=True,
            existing_linked_sub_for_iss=None,
            ecdsa_curve="P-256",
            ecdsa_signature_bytes_len=64,
            ecdsa_is_asn1_der_encoded=False,
        )
        self.assertTrue(ok.admitted)
        self.assertEqual(ok.selected_authorization_server, "https://auth.provider.example/authentication/12345")
        self.assertEqual(ok.linked_key, ("https://accounts.google.com", "sub_user_42"))

        der_blocked = evaluate_ucp_identity_linking_and_ecdsa_raw_rs_guard(
            authorization_servers=auth_servers,
            platform_aborted_on_first_mismatch=False,
            attempt_accelerated_email_autolink=False,
            idp_email_verified=True,
            dns_txt_delegated_issuer=None,
            grant_iss="https://accounts.google.com",
            grant_sub="sub_user_42",
            business_verified_existing_account_email=True,
            existing_linked_sub_for_iss=None,
            ecdsa_curve="P-256",
            ecdsa_signature_bytes_len=71,
            ecdsa_is_asn1_der_encoded=True,
        )
        self.assertFalse(der_blocked.admitted)
        self.assertEqual(der_blocked.decision_code, "ASN1_DER_OR_INVALID_LENGTH_ECDSA_SIGNATURE_BLOCKED")


if __name__ == "__main__":
    unittest.main()
