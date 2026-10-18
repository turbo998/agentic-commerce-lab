import unittest

from lab.booking_sftp_reconciliation_guard import (
    BookingLegHold,
    SftpPayoutBatchRow,
    main,
    reconcile_sftp_tempo_token_ledger,
    run_demo,
    verify_multi_leg_booking_saga,
)


class BookingSftpReconciliationGuardTests(unittest.TestCase):
    def test_multi_leg_booking_saga_prevents_orphan_legs(self) -> None:
        # Premature automatic capture on any leg is rejected
        auto_cap = verify_multi_leg_booking_saga(
            legs=[
                BookingLegHold("flight_gds", "airline", 45000, "automatic", "held", 1200, 3600, True),
                BookingLegHold("hotel_pms", "hotel", 32000, "manual", "held", 1300, 3600, True),
            ],
            commit_attempt_epoch=1100,
        )
        self.assertFalse(auto_cap.commit_allowed)
        self.assertEqual(auto_cap.reason, "premature_automatic_capture_forbidden:flight_gds")
        self.assertEqual(auto_cap.orphan_exposure_minor_prevented, 77000)

        # Summary claims free cancellation while terms are already non-refundable -> rejected
        deceptive = verify_multi_leg_booking_saga(
            legs=[
                BookingLegHold("flight_gds", "airline", 45000, "manual", "held", 1200, 1000, True),
                BookingLegHold("hotel_pms", "hotel", 32000, "manual", "held", 1300, 3600, True),
            ],
            commit_attempt_epoch=1100,
        )
        self.assertFalse(deceptive.commit_allowed)
        self.assertEqual(
            deceptive.reason,
            "summary_claims_free_cancel_but_terms_non_refundable:flight_gds",
        )

        # Hold TTL expired or inside 15s safety buffer -> atomic reversal of all legs
        ttl_breach = verify_multi_leg_booking_saga(
            legs=[
                BookingLegHold("flight_gds", "airline", 45000, "manual", "held", 1180, 3600, True),
                BookingLegHold("hotel_pms", "hotel", 32000, "manual", "held", 1300, 3600, True),
            ],
            commit_attempt_epoch=1170,
            safety_buffer_seconds=15,
        )
        self.assertFalse(ttl_breach.commit_allowed)
        self.assertEqual(ttl_breach.reason, "saga_hold_ttl_expired_or_within_safety_buffer")
        self.assertEqual(ttl_breach.legs_to_cancel_payment_intent, ("flight_gds", "hotel_pms"))

        # Valid 3-leg manual hold within TTL and refundable window -> atomic capture committed
        ok = verify_multi_leg_booking_saga(
            legs=[
                BookingLegHold("flight_gds", "airline", 45000, "manual", "held", 1180, 3600, True),
                BookingLegHold("hotel_pms", "hotel", 32000, "manual", "held", 1300, 3600, True),
                BookingLegHold("gpu_reserve", "compute", 15000, "manual", "held", 1240, 3600, True),
            ],
            commit_attempt_epoch=1150,
        )
        self.assertTrue(ok.commit_allowed)
        self.assertEqual(ok.saga_outcome, "ATOMIC_CAPTURE_COMMITTED")
        self.assertEqual(ok.total_captured_minor, 92000)

    def test_three_way_sftp_tempo_token_reconciliation(self) -> None:
        # Unreversed Connect refund deficit is caught
        deficit = reconcile_sftp_tempo_token_ledger(
            sftp_rows=[
                SftpPayoutBatchRow(
                    "evt_1",
                    "tx_1",
                    10000,
                    320,
                    9680,
                    14,
                    is_connect_refund_without_reversal=True,
                    unreversed_transfer_deficit_minor=9000,
                )
            ],
            mpp_gross_micro_usdc=20000,
            mpp_settled_cents_minor=2,
            token_billed_minor=500,
            token_collected_minor=500,
            reported_bank_payout_minor=9680 + 2 + 500,
        )
        self.assertFalse(deficit.reconciled)
        self.assertEqual(deficit.reason, "connect_unreversed_refund_deficit_detected")
        self.assertEqual(deficit.connect_unreversed_refund_deficit_minor, 9000)

        # Clean reconciliation with duplicate webhook deduplication and post-00:00 UTC in-flight separation
        clean = reconcile_sftp_tempo_token_ledger(
            sftp_rows=[
                SftpPayoutBatchRow("evt_1", "tx_1", 10000, 320, 9680, 14),
                SftpPayoutBatchRow("evt_1", "tx_1", 10000, 320, 9680, 14),
                SftpPayoutBatchRow("evt_2", "tx_2", 15000, 465, 14535, 25),  # D+1 in-flight
            ],
            mpp_gross_micro_usdc=43750,
            mpp_settled_cents_minor=2,
            token_billed_minor=1250,
            token_collected_minor=1250,
            reported_bank_payout_minor=9680 + 2 + 1250,
        )
        self.assertTrue(clean.reconciled)
        self.assertEqual(clean.duplicate_webhook_ids_dropped, ("evt_1",))
        self.assertEqual(clean.in_flight_after_cutoff_minor, 14535)
        self.assertEqual(clean.mpp_subcent_forfeited_usd, "0.023750")

    def test_demo_and_cli_run_cleanly(self) -> None:
        summary = run_demo()
        self.assertTrue(summary["valid_saga_committed"])
        self.assertTrue(summary["expired_saga_reversed"])
        self.assertTrue(summary["three_way_reconciled"])
        self.assertEqual(main([]), 0)


if __name__ == "__main__":
    unittest.main()
