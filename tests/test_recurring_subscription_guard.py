"""Unit tests for Stage 9 Recurring Subscription TCCV & Atomic 3-Layer Revocation Guard."""

from __future__ import annotations

import unittest

from lab.recurring_subscription_guard import (
    execute_atomic_revocation_cascade,
    run_demo_scenarios,
    verify_subscription_trial_and_recurring_mandate,
)


class RecurringSubscriptionGuardTest(unittest.TestCase):
    def test_compliant_recurring_saas_mandate_passes_tccv_and_cycle_caps(self) -> None:
        result = verify_subscription_trial_and_recurring_mandate(
            mandate={
                "mandate_id": "mandate_saas_ok",
                "allow_recurring": True,
                "max_total_commitment_minor": 50_000,
                "max_per_cycle_minor": 5_000,
            },
            offer_terms={
                "billing_interval": "month",
                "trial_days": 14,
                "auto_convert": True,
                "initial_charge_minor": 100,
                "recurring_charge_minor": 4_900,
                "min_commitment_cycles": 6,
                "early_termination_fee_minor": 5_000,
                "cancel_cutoff_hours_before_trial_end": 24.0,
                "auto_cancel_hook_armed": False,
                "summary_discloses_recurring": True,
            },
        )
        self.assertTrue(result.allowed)
        self.assertEqual(result.decision_code, "RECURRING_MANDATE_VERIFIED")
        # TCCV = 100 + 6 * 4900 + 5000 = 34500
        self.assertEqual(result.tccv_minor, 34_500)
        self.assertTrue(result.audit_digest.startswith("sha256:"))

    def test_free_trial_auto_convert_on_one_time_mandate_is_blocked(self) -> None:
        result = verify_subscription_trial_and_recurring_mandate(
            mandate={
                "mandate_id": "mandate_onetime_only",
                "allow_recurring": False,
                "max_total_commitment_minor": 5_000,
                "max_per_cycle_minor": 5_000,
            },
            offer_terms={
                "billing_interval": "month",
                "trial_days": 7,
                "auto_convert": True,
                "initial_charge_minor": 0,
                "recurring_charge_minor": 9_900,
                "min_commitment_cycles": 12,
                "early_termination_fee_minor": 10_000,
                "cancel_cutoff_hours_before_trial_end": 12.0,
                "summary_discloses_recurring": True,
            },
        )
        self.assertFalse(result.allowed)
        self.assertEqual(result.decision_code, "NEGATIVE_OPTION_MANDATE_MISMATCH")
        # TCCV = 0 + 12 * 9900 + 10000 = 128800
        self.assertEqual(result.tccv_minor, 128_800)

    def test_tccv_exceeds_mandate_commitment_cap_is_blocked(self) -> None:
        result = verify_subscription_trial_and_recurring_mandate(
            mandate={
                "mandate_id": "mandate_recurring_small_cap",
                "allow_recurring": True,
                "max_total_commitment_minor": 20_000,
                "max_per_cycle_minor": 5_000,
            },
            offer_terms={
                "billing_interval": "month",
                "trial_days": 0,
                "auto_convert": False,
                "initial_charge_minor": 0,
                "recurring_charge_minor": 4_000,
                "min_commitment_cycles": 6,
                "early_termination_fee_minor": 5_000,
                "summary_discloses_recurring": True,
            },
        )
        self.assertFalse(result.allowed)
        self.assertEqual(result.decision_code, "TCCV_EXCEEDS_MANDATE_CAP")
        self.assertEqual(result.tccv_minor, 29_000)

    def test_predatory_cancellation_cutoff_without_armed_hook_is_blocked(self) -> None:
        result = verify_subscription_trial_and_recurring_mandate(
            mandate={
                "mandate_id": "mandate_recurring_ok",
                "allow_recurring": True,
                "max_total_commitment_minor": 50_000,
                "max_per_cycle_minor": 5_000,
            },
            offer_terms={
                "billing_interval": "month",
                "trial_days": 7,
                "auto_convert": True,
                "initial_charge_minor": 0,
                "recurring_charge_minor": 2_900,
                "min_commitment_cycles": 1,
                "early_termination_fee_minor": 0,
                "cancel_cutoff_hours_before_trial_end": 96.0,
                "auto_cancel_hook_armed": False,
                "summary_discloses_recurring": True,
            },
        )
        self.assertFalse(result.allowed)
        self.assertEqual(result.decision_code, "PREDATORY_CANCELLATION_WINDOW_BLOCKED")

    def test_atomic_3_layer_revocation_converges_when_all_three_layers_verified(self) -> None:
        result = execute_atomic_revocation_cascade(
            {
                "mandate_id": "mandate_rev_01",
                "revoked_at_epoch": 1792368000,
                "ap2_revocation_jws": "eyJhbGciOiJFZERTQSJ9.rev.sig",
                "spt_status": "deactivated",
                "network_token_status": "deactivated",
                "subscription_status": "canceled",
                "merchant_cancellation_ack_id": "ack_sub_001",
            }
        )
        self.assertTrue(result.revocation_complete)
        self.assertFalse(result.zombie_mit_blocked)
        self.assertEqual(result.decision_code, "ATOMIC_3_LAYER_REVOCATION_CONVERGED")

    def test_zombie_mit_charge_after_revocation_is_intercepted_with_visa_13_5_mc_4841(self) -> None:
        result = execute_atomic_revocation_cascade(
            {
                "mandate_id": "mandate_rev_02",
                "revoked_at_epoch": 1792368000,
                "ap2_revocation_jws": "eyJhbGciOiJFZERTQSJ9.rev.sig",
                "spt_status": "deactivated",
                "network_token_status": "deactivated",
                "subscription_status": "canceled",
                "merchant_cancellation_ack_id": "ack_sub_002",
                "mit_charge_attempt": {
                    "attempted": True,
                    "attempt_epoch": 1792400000,
                    "amount_minor": 4_900,
                },
            }
        )
        self.assertTrue(result.revocation_complete)
        self.assertTrue(result.zombie_mit_blocked)
        self.assertEqual(result.decision_code, "ZOMBIE_MIT_BLOCKED_VISA_13_5_MC_4841")
        self.assertEqual(
            result.dispute_reason_codes["visa"],
            "13.5_CANCELED_RECURRING_TRANSACTION",
        )
        self.assertEqual(
            result.dispute_reason_codes["mastercard"],
            "4841_CANCELED_RECURRING_OR_DIGITAL_GOODS",
        )

    def test_demo_scenarios_cover_compliant_and_adversarial_cases(self) -> None:
        demos = run_demo_scenarios()
        self.assertEqual(len(demos), 3)
        self.assertTrue(demos[0]["allowed"])
        self.assertFalse(demos[1]["allowed"])
        self.assertTrue(demos[2]["zombie_mit_blocked"])


if __name__ == "__main__":
    unittest.main()
