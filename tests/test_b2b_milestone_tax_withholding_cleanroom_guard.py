"""Unit tests for Stage 28: B2B Contractor Milestone Escrow, IRS 1099-K / W-8BEN-E Tax Withholding & Data-Clean-Room Differential Privacy Budget Guard."""

from __future__ import annotations

import unittest

from lab.b2b_milestone_tax_withholding_cleanroom_guard import (
    evaluate_b2b_contractor_milestone_escrow,
    evaluate_cross_border_tax_withholding_1099k_w8bene,
    evaluate_data_clean_room_differential_privacy_budget,
)


class TestB2bMilestoneTaxWithholdingCleanroomGuard(unittest.TestCase):
    def test_contractor_milestone_unverified_and_scope_creep_blocked(self) -> None:
        overrun = evaluate_b2b_contractor_milestone_escrow(
            {
                "milestone_id": "ms_01",
                "contracted_milestone_minor": 100_000,
                "requested_payout_minor": 135_000,
                "max_change_order_bps": 1_000,
                "deliverable_attestation_verified": True,
                "human_principal_change_order_approved": False,
            }
        )
        self.assertFalse(overrun["released"])
        self.assertEqual(
            overrun["decision_code"],
            "UNAPPROVED_CHANGE_ORDER_OVERRUN_BLOCKED",
        )

        unverified = evaluate_b2b_contractor_milestone_escrow(
            {
                "milestone_id": "ms_02",
                "contracted_milestone_minor": 100_000,
                "requested_payout_minor": 100_000,
                "deliverable_attestation_verified": False,
            }
        )
        self.assertFalse(unverified["released"])
        self.assertEqual(
            unverified["decision_code"],
            "UNVERIFIED_MILESTONE_DELIVERABLE_ESCROW_HELD",
        )

        released = evaluate_b2b_contractor_milestone_escrow(
            {
                "milestone_id": "ms_03",
                "contracted_milestone_minor": 100_000,
                "requested_payout_minor": 105_000,
                "max_change_order_bps": 1_000,
                "retainage_holdback_bps": 1_000,
                "deliverable_attestation_verified": True,
            }
        )
        self.assertTrue(released["released"])
        self.assertEqual(
            released["decision_code"],
            "MILESTONE_ESCROW_RELEASED_WITH_RETAINAGE_HOLD",
        )
        self.assertEqual(released["retainage_holdback_minor"], 10_500)
        self.assertEqual(released["net_disbursed_minor"], 94_500)

    def test_cross_border_tax_withholding_1099k_and_w8bene(self) -> None:
        us_no_tin = evaluate_cross_border_tax_withholding_1099k_w8bene(
            {
                "payee_id": "us_contractor_01",
                "gross_payout_minor": 100_000,
                "is_us_person": True,
                "us_tin_verified": False,
            }
        )
        self.assertEqual(
            us_no_tin["decision_code"],
            "TIN_MISSING_24PCT_BACKUP_WITHHOLDING_APPLIED",
        )
        self.assertEqual(us_no_tin["tax_withheld_minor"], 24_000)

        foreign_no_w8 = evaluate_cross_border_tax_withholding_1099k_w8bene(
            {
                "payee_id": "foreign_vendor_02",
                "gross_payout_minor": 100_000,
                "is_us_person": False,
                "w8bene_valid": False,
            }
        )
        self.assertEqual(
            foreign_no_w8["decision_code"],
            "W8BENE_MISSING_30PCT_STATUTORY_WITHHOLDING_APPLIED",
        )
        self.assertEqual(foreign_no_w8["tax_withheld_minor"], 30_000)

        treaty = evaluate_cross_border_tax_withholding_1099k_w8bene(
            {
                "payee_id": "de_vendor_03",
                "gross_payout_minor": 100_000,
                "is_us_person": False,
                "w8bene_valid": True,
                "verified_treaty_withholding_bps": 500,
            }
        )
        self.assertEqual(treaty["decision_code"], "TAX_TREATY_RATE_VERIFIED_NET_SETTLED")
        self.assertEqual(treaty["tax_withheld_minor"], 5_000)
        self.assertEqual(treaty["net_payee_disbursement_minor"], 95_000)

    def test_data_clean_room_differential_privacy_budget(self) -> None:
        admitted = evaluate_data_clean_room_differential_privacy_budget(
            {
                "dataset_id": "ds_healthcare_cohort",
                "prior_epsilon_consumed": 1.2,
                "query_epsilon_cost": 0.5,
                "max_epsilon_budget": 2.0,
                "price_per_unit_epsilon_minor": 20_000,
            }
        )
        self.assertTrue(admitted["admitted"])
        self.assertEqual(
            admitted["decision_code"],
            "CLEAN_ROOM_DP_QUERY_ADMITTED_AND_METERED",
        )
        self.assertEqual(admitted["query_royalty_fee_minor"], 10_000)

        exhausted = evaluate_data_clean_room_differential_privacy_budget(
            {
                "dataset_id": "ds_healthcare_cohort",
                "prior_epsilon_consumed": 1.8,
                "query_epsilon_cost": 0.5,
                "max_epsilon_budget": 2.0,
                "price_per_unit_epsilon_minor": 20_000,
            }
        )
        self.assertFalse(exhausted["admitted"])
        self.assertEqual(
            exhausted["decision_code"],
            "DIFFERENTIAL_PRIVACY_EPSILON_BUDGET_EXHAUSTED_BLOCKED",
        )


if __name__ == "__main__":
    unittest.main()
