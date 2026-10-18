"""Unit tests for Stage 31 Construction AIA G702 Lien-Waiver Escrow, Sovereign Procurement & Legal IOLTA Trust Guard."""

from __future__ import annotations

import unittest

from lab.construction_lien_public_tender_iolta_guard import (
    SubcontractorLienWaiver,
    evaluate_aia_g702_mechanics_lien_waiver_escrow,
    evaluate_iolta_fiduciary_trust_account_guard,
    evaluate_sovereign_procurement_bid_bond_and_domestic_content,
)


class TestConstructionLienPublicTenderIOLTAGuard(unittest.TestCase):
    def test_aia_g702_mechanics_lien_waiver_escrow(self) -> None:
        missing_waiver = evaluate_aia_g702_mechanics_lien_waiver_escrow(
            application_id="aia_g702_04",
            scheduled_value_minor=1_000_000_00,
            cumulative_completed_to_date_minor=600_000_00,
            previous_certificates_gross_minor=400_000_00,
            retainage_rate_bps=1000,
            subcontractor_waivers=[
                SubcontractorLienWaiver(
                    subcontractor_id="sub_hvac_01",
                    prior_period_paid_minor=80_000_00,
                    unconditional_prior_waiver_signed=False,
                    current_period_billed_minor=40_000_00,
                    conditional_current_waiver_signed=True,
                )
            ],
        )
        self.assertFalse(missing_waiver.admitted)
        self.assertEqual(
            missing_waiver.decision_code,
            "SUBCONTRACTOR_MECHANICS_LIEN_WAIVER_MISSING_HOLD",
        )
        self.assertEqual(missing_waiver.missing_waiver_subcontractors, ("sub_hvac_01",))

        released = evaluate_aia_g702_mechanics_lien_waiver_escrow(
            application_id="aia_g702_04",
            scheduled_value_minor=1_000_000_00,
            cumulative_completed_to_date_minor=600_000_00,
            previous_certificates_gross_minor=400_000_00,
            retainage_rate_bps=1000,
            subcontractor_waivers=[
                SubcontractorLienWaiver(
                    subcontractor_id="sub_hvac_01",
                    prior_period_paid_minor=80_000_00,
                    unconditional_prior_waiver_signed=True,
                    current_period_billed_minor=40_000_00,
                    conditional_current_waiver_signed=True,
                )
            ],
        )
        self.assertTrue(released.admitted)
        self.assertEqual(
            released.decision_code,
            "AIA_G702_LIEN_WAIVER_VERIFIED_PROGRESS_RELEASED",
        )
        self.assertEqual(released.net_progress_payment_minor, 180_000_00)
        self.assertEqual(released.retainage_withheld_minor, 20_000_00)
        self.assertEqual(released.conservation_delta_minor, 0)

    def test_sovereign_procurement_bid_bond_and_domestic_content(self) -> None:
        domestic_fail = evaluate_sovereign_procurement_bid_bond_and_domestic_content(
            tender_id="far_tender_2026_09",
            bidder_id="vendor_grid_ai",
            bid_amount_minor=500_000_00,
            required_bid_bond_bps=500,  # 5%
            posted_surety_bond_minor=25_000_00,
            surety_signature_valid=True,
            sam_gov_or_eu_debarment_listed=False,
            verified_domestic_bom_cost_minor=200_000_00,
            total_bom_cost_minor=400_000_00,  # 50% < 65% Buy American threshold
            required_domestic_content_bps=6500,
        )
        self.assertFalse(domestic_fail.admitted)
        self.assertEqual(
            domestic_fail.decision_code,
            "DOMESTIC_CONTENT_BUY_AMERICAN_THRESHOLD_BREACH_BLOCKED",
        )

        compliant = evaluate_sovereign_procurement_bid_bond_and_domestic_content(
            tender_id="far_tender_2026_09",
            bidder_id="vendor_grid_ai",
            bid_amount_minor=500_000_00,
            required_bid_bond_bps=500,
            posted_surety_bond_minor=25_000_00,
            surety_signature_valid=True,
            sam_gov_or_eu_debarment_listed=False,
            verified_domestic_bom_cost_minor=280_000_00,
            total_bom_cost_minor=400_000_00,  # 70% >= 65%
            required_domestic_content_bps=6500,
        )
        self.assertTrue(compliant.admitted)
        self.assertEqual(
            compliant.decision_code,
            "SOVEREIGN_PROCUREMENT_BID_COMPLIANT_ADMITTED",
        )

    def test_iolta_fiduciary_trust_account_guard(self) -> None:
        unearned = evaluate_iolta_fiduciary_trust_account_guard(
            matter_id="matter_mna_01",
            client_trust_balance_minor=100_000_00,
            requested_operating_drawdown_minor=45_000_00,
            client_approved_earned_billing_minor=30_000_00,
            firm_operating_expense_charged_directly_to_trust=False,
            accrued_trust_interest_minor=120_00,
            firm_attempts_to_retain_trust_interest=False,
        )
        self.assertFalse(unearned.admitted)
        self.assertEqual(
            unearned.decision_code,
            "IOLTA_UNEARNED_RETAINER_PREMATURE_DRAWDOWN_BLOCKED",
        )

        disbursed = evaluate_iolta_fiduciary_trust_account_guard(
            matter_id="matter_mna_01",
            client_trust_balance_minor=100_000_00,
            requested_operating_drawdown_minor=30_000_00,
            client_approved_earned_billing_minor=30_000_00,
            firm_operating_expense_charged_directly_to_trust=False,
            accrued_trust_interest_minor=120_00,
            firm_attempts_to_retain_trust_interest=False,
        )
        self.assertTrue(disbursed.admitted)
        self.assertEqual(
            disbursed.decision_code,
            "IOLTA_EARNED_FEE_DISBURSED_AND_BAR_INTEREST_SWEPT",
        )
        self.assertEqual(disbursed.client_trust_balance_after_minor, 70_000_00)
        self.assertEqual(disbursed.accrued_interest_swept_to_bar_foundation_minor, 120_00)
        self.assertEqual(disbursed.conservation_delta_minor, 0)


if __name__ == "__main__":
    unittest.main()
