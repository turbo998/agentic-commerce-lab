"""Unit tests for Stage 18 Agentic Subscription Lifecycle, Usage Metering & FTC Click-to-Cancel Guard."""

from __future__ import annotations

import unittest

from lab.subscription_metering_click_to_cancel_guard import (
    evaluate_recurring_mandate_renewal_and_pre_debit_notice,
    evaluate_usage_based_metering_idempotency,
    execute_ftc_click_to_cancel_symmetric_offramp,
)


class SubscriptionMeteringClickToCancelGuardTestSuite(unittest.TestCase):
    def test_usage_metering_idempotency_dedup_and_within_cap(self) -> None:
        res = evaluate_usage_based_metering_idempotency(
            {
                "subscription_id": "sub_01",
                "watermark_epoch": 2_000,
                "max_watermark_lateness_seconds": 300,
                "prior_spend_minor": 10_000,
                "hard_spend_cap_minor": 25_000,
                "unit_price_minor_per_1k_units": 100,
                "seen_idempotency_keys": ["ev_dup_01"],
                "events": [
                    {"idempotency_key": "ev_dup_01", "event_timestamp_epoch": 1_950, "units": 50_000},
                    {"idempotency_key": "ev_new_02", "event_timestamp_epoch": 1_960, "units": 20_000},
                    {"idempotency_key": "ev_new_02", "event_timestamp_epoch": 1_960, "units": 20_000},
                ],
            }
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.decision_code, "USAGE_METERING_IDEMPOTENT_AND_WITHIN_CAP")
        self.assertEqual(res.accepted_events_count, 1)
        self.assertEqual(res.duplicate_events_dropped, 2)
        self.assertEqual(res.incremental_billed_minor, 2_000)
        self.assertEqual(res.cumulative_spend_minor, 12_000)

    def test_usage_metering_blocks_late_watermark_and_hard_spend_cap(self) -> None:
        late = evaluate_usage_based_metering_idempotency(
            {
                "subscription_id": "sub_02",
                "watermark_epoch": 2_000,
                "max_watermark_lateness_seconds": 300,
                "prior_spend_minor": 5_000,
                "hard_spend_cap_minor": 25_000,
                "unit_price_minor_per_1k_units": 100,
                "events": [
                    {"idempotency_key": "ev_late_01", "event_timestamp_epoch": 1_500, "units": 10_000},
                ],
            }
        )
        self.assertFalse(late.allowed)
        self.assertEqual(late.decision_code, "USAGE_EVENT_LATE_WATERMARK_EXPIRED")
        self.assertEqual(late.late_watermark_events_rejected, 1)

        cap = evaluate_usage_based_metering_idempotency(
            {
                "subscription_id": "sub_02",
                "watermark_epoch": 2_000,
                "max_watermark_lateness_seconds": 300,
                "prior_spend_minor": 22_000,
                "hard_spend_cap_minor": 25_000,
                "unit_price_minor_per_1k_units": 100,
                "events": [
                    {"idempotency_key": "ev_spike_01", "event_timestamp_epoch": 1_980, "units": 50_000},
                ],
            }
        )
        self.assertFalse(cap.allowed)
        self.assertTrue(cap.throttled)
        self.assertEqual(cap.decision_code, "SPEND_CAP_HARD_LIMIT_REACHED_THROTTLED")

    def test_recurring_mandate_renewal_pre_debit_and_escalation_guard(self) -> None:
        ok = evaluate_recurring_mandate_renewal_and_pre_debit_notice(
            {
                "mandate_id": "mnd_01",
                "previous_cycle_debit_minor": 10_000,
                "proposed_debit_minor": 10_400,
                "mandate_max_amount_minor": 12_000,
                "max_price_escalation_bps": 500,
                "pre_debit_notice_hours_ahead": 72,
                "min_pre_debit_notice_hours": 48,
            }
        )
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.decision_code, "RECURRING_RENEWAL_AUTHORIZED")

        escalation = evaluate_recurring_mandate_renewal_and_pre_debit_notice(
            {
                "mandate_id": "mnd_01",
                "previous_cycle_debit_minor": 10_000,
                "proposed_debit_minor": 11_200,
                "mandate_max_amount_minor": 12_000,
                "max_price_escalation_bps": 500,
                "pre_debit_notice_hours_ahead": 72,
                "min_pre_debit_notice_hours": 48,
            }
        )
        self.assertFalse(escalation.allowed)
        self.assertTrue(escalation.reconsent_required)
        self.assertEqual(
            escalation.decision_code,
            "RECURRING_PRICE_ESCALATION_RECONSENT_REQUIRED",
        )

        notice_fail = evaluate_recurring_mandate_renewal_and_pre_debit_notice(
            {
                "mandate_id": "mnd_01",
                "previous_cycle_debit_minor": 10_000,
                "proposed_debit_minor": 10_000,
                "mandate_max_amount_minor": 12_000,
                "pre_debit_notice_hours_ahead": 12,
                "min_pre_debit_notice_hours": 48,
            }
        )
        self.assertFalse(notice_fail.allowed)
        self.assertEqual(notice_fail.decision_code, "PRE_DEBIT_NOTICE_WINDOW_VIOLATION")

    def test_ftc_click_to_cancel_blocks_retention_wall_and_issues_prorata_refund(
        self,
    ) -> None:
        wall = execute_ftc_click_to_cancel_symmetric_offramp(
            {
                "subscription_id": "sub_wall_01",
                "enrollment_steps": 1,
                "required_cancellation_steps": 4,
                "forced_human_chat_retention_wall": True,
                "cycle_paid_minor": 30_000,
                "total_cycle_days": 30,
                "unused_days": 20,
            }
        )
        self.assertFalse(wall.canceled)
        self.assertEqual(wall.decision_code, "DARK_PATTERN_RETENTION_WALL_BLOCKED")

        clean = execute_ftc_click_to_cancel_symmetric_offramp(
            {
                "subscription_id": "sub_clean_01",
                "enrollment_steps": 2,
                "required_cancellation_steps": 1,
                "forced_human_chat_retention_wall": False,
                "undisclosed_early_exit_penalty_minor": 0,
                "cycle_paid_minor": 30_000,
                "total_cycle_days": 30,
                "unused_days": 15,
            }
        )
        self.assertTrue(clean.canceled)
        self.assertTrue(clean.spt_token_revoked)
        self.assertEqual(clean.decision_code, "PRO_RATA_REFUND_ISSUED")
        self.assertEqual(clean.pro_rata_refund_minor, 15_000)


if __name__ == "__main__":
    unittest.main()
