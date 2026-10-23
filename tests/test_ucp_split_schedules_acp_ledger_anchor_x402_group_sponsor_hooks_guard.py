"""Unit tests for Stage 174 guard module (`lab/ucp_split_schedules_acp_ledger_anchor_x402_group_sponsor_hooks_guard.py`)."""

from __future__ import annotations

import unittest

from lab.ucp_split_schedules_acp_ledger_anchor_x402_group_sponsor_hooks_guard import (
    allocate_ucp_split_payments_across_schedules,
    validate_acp_atdrp_ledger_time_anchor,
    validate_ucp_per_checkout_split_combinations,
    validate_x402_http_header_overflow_and_text_error,
    validate_x402_payment_creation_hook_correlation,
    validate_x402_presigning_group_sponsorship,
    validate_x402_svm_failed_local_charge_cleanup,
)


class TestStage174Guard(unittest.TestCase):
    def test_ucp_per_checkout_split_combinations_and_schedule_allocation(self) -> None:
        profile_combos = [
            [
                {"types": ["gift_card", "loyalty"], "max": 2},
                {"types": ["card"], "min": 1, "max": 1},
            ],
            [
                {"types": ["gift_card"], "min": 1, "max": 5},
            ],
        ]
        checkout_combos = [
            [
                {"types": ["gift_card"], "max": 2, "schedule_type": "immediate"},
                {"types": ["card"], "min": 1, "max": 1},
            ]
        ]
        ok = validate_ucp_per_checkout_split_combinations(
            profile_allowed_combinations=profile_combos,
            checkout_allowed_combinations=checkout_combos,
            has_deferred_schedules=True,
        )
        self.assertTrue(ok.allowed)

        # Reject invalid schedule_type
        bad_sched = validate_ucp_per_checkout_split_combinations(
            profile_allowed_combinations=profile_combos,
            checkout_allowed_combinations=[
                [
                    {"types": ["gift_card"], "max": 2, "schedule_type": "later"},
                    {"types": ["card"], "min": 1, "max": 1},
                ]
            ],
            has_deferred_schedules=True,
        )
        self.assertFalse(bad_sched.allowed)
        self.assertEqual(bad_sched.code, "ucp_split_group_invalid_schedule_type")

        # Reject checkout combination that widens profile
        bad_widen = validate_ucp_per_checkout_split_combinations(
            profile_allowed_combinations=profile_combos,
            checkout_allowed_combinations=[
                [
                    {"types": ["crypto_wallet"], "min": 1, "max": 1},
                ]
            ],
            has_deferred_schedules=True,
        )
        self.assertFalse(bad_widen.allowed)
        self.assertEqual(bad_widen.code, "ucp_checkout_combination_widens_profile")

        # Allocate $25 immediate deposit + $75 check-in balance
        schedules = [
            {"id": "sched_deposit", "type": "immediate", "amount": 2500},
            {"id": "sched_checkin", "type": "deferred", "amount": 7500},
        ]
        alloc_ok = allocate_ucp_split_payments_across_schedules(
            schedules=schedules,
            instruments=[
                {"id": "pi_gc_1", "type": "gift_card", "schedule_type": "immediate", "amount": 2500},
                {"id": "pi_card_1", "type": "card", "schedule_type": None, "amount": None},
            ],
        )
        self.assertTrue(alloc_ok.allowed)
        self.assertEqual(
            alloc_ok.metadata["outbound_instruments"],
            [
                {"id": "pi_gc_1", "type": "gift_card", "amount": 2500},
                {"id": "pi_card_1", "type": "card", "amount": 7500},
            ],
        )

        # Reject immediate gift card specifying 5000 when only 2500 is due at completion
        alloc_over = allocate_ucp_split_payments_across_schedules(
            schedules=schedules,
            instruments=[
                {"id": "pi_gc_1", "type": "gift_card", "schedule_type": "immediate", "amount": 5000},
                {"id": "pi_card_1", "type": "card", "schedule_type": None, "amount": None},
            ],
        )
        self.assertFalse(alloc_over.allowed)
        self.assertEqual(alloc_over.code, "immediate_group_amount_exceeds_due_at_completion")

    def test_acp_atdrp_ledger_time_anchor(self) -> None:
        ok = validate_acp_atdrp_ledger_time_anchor(
            sequence_complete=True,
            anchored_digest="sha256:abc123",
            recomputed_digest="sha256:abc123",
            mechanism="rfc3161",
            proof_bytes_present=True,
            recompute_location="https://merchant.example/disputes/packs/1/ledger",
            provider_verified_anchor_proof=True,
            anchor_time_epoch=1761220000,
            records=[
                {"seq": 1, "timestamp": 1761219000},
                {"seq": 2, "timestamp": 1761220000},
                {"seq": 3, "timestamp": 1761220500},
            ],
            claim_is_time_based_ground=True,
            claim_relies_solely_on_post_anchor_records=False,
        )
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.metadata["anchored_count"], 2)
        self.assertEqual(ok.metadata["unanchored_count"], 1)

        bad_post = validate_acp_atdrp_ledger_time_anchor(
            sequence_complete=True,
            anchored_digest="sha256:abc123",
            recomputed_digest="sha256:abc123",
            mechanism="opentimestamps",
            proof_bytes_present=True,
            recompute_location="https://merchant.example/disputes/packs/1/ledger",
            provider_verified_anchor_proof=True,
            anchor_time_epoch=1761220000,
            records=[{"seq": 3, "timestamp": 1761220500}],
            claim_is_time_based_ground=True,
            claim_relies_solely_on_post_anchor_records=True,
        )
        self.assertFalse(bad_post.allowed)
        self.assertEqual(bad_post.code, "acp_unanchored_records_sole_time_ground_forbidden")

    def test_x402_presigning_group_and_hooks_and_svm_cleanup(self) -> None:
        grp_ok = validate_x402_presigning_group_sponsorship(
            expected_network="algorand:wGHE2Pwdvd7S12BL5FaOP20EGYesN73k",
            canonical_group_digest="grp_sha256_001",
            max_sponsored_fee_minor=2000,
            transactions=[
                {
                    "network": "algorand:wGHE2Pwdvd7S12BL5FaOP20EGYesN73k",
                    "group_digest": "grp_sha256_001",
                    "is_unsigned_facilitator_fee_tx": True,
                    "fee_minor": 1000,
                },
                {
                    "network": "algorand:wGHE2Pwdvd7S12BL5FaOP20EGYesN73k",
                    "group_digest": "grp_sha256_001",
                    "is_unsigned_facilitator_fee_tx": False,
                    "fee_minor": 0,
                },
            ],
        )
        self.assertTrue(grp_ok.allowed)

        grp_null = validate_x402_presigning_group_sponsorship(
            expected_network="algorand:wGHE2Pwdvd7S12BL5FaOP20EGYesN73k",
            canonical_group_digest="grp_sha256_001",
            max_sponsored_fee_minor=2000,
            transactions=[
                {
                    "network": "algorand:wGHE2Pwdvd7S12BL5FaOP20EGYesN73k",
                    "group_digest": None,
                    "is_unsigned_facilitator_fee_tx": True,
                    "fee_minor": 1000,
                },
                {
                    "network": "algorand:wGHE2Pwdvd7S12BL5FaOP20EGYesN73k",
                    "group_digest": None,
                    "is_unsigned_facilitator_fee_tx": False,
                    "fee_minor": 0,
                },
            ],
        )
        self.assertFalse(grp_null.allowed)
        self.assertEqual(grp_null.code, "x402_group_digest_missing_or_mismatch")

        hook_ok = validate_x402_payment_creation_hook_correlation(
            shared_context_id_across_phases=True,
            before_hook_aborted=True,
            failure_cleanup_hooks_ran=True,
            recovery_overrode_before_abort=False,
            cleanup_exception_replaced_original_error=False,
            payload_creation_started_after_before_abort=False,
        )
        self.assertTrue(hook_ok.allowed)

        svm_ok = validate_x402_svm_failed_local_charge_cleanup(
            channel_capacity=10000,
            committed_charged=1000,
            sibling_reserved=0,
            failed_request_reserved=4000,
            local_charge_failed=True,
            failed_reservation_released=True,
            sibling_reservation_preserved=True,
            consumed_request_id_retained=True,
        )
        self.assertTrue(svm_ok.allowed)
        self.assertEqual(svm_ok.metadata["available_capacity"], 9000)

        http_ok = validate_x402_http_header_overflow_and_text_error(
            error_cause_codes=["UND_ERR_HEADERS_OVERFLOW"],
            preserved_original_cause=True,
            triggered_auto_retry_on_overflow=False,
            declared_media_type="text/plain",
            response_body_is_raw_text=True,
            appended_duplicate_json_content_type=False,
        )
        self.assertTrue(http_ok.allowed)


if __name__ == "__main__":
    unittest.main()
