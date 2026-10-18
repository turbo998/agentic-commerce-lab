"""Unit tests for Stage 30 Commercial CAM Lease Audit, Fleet Mobility Escrow & EOR Payroll Statutory Guard."""

from __future__ import annotations

import unittest

from lab.fleet_mobility_prop_lease_eor_payroll_guard import (
    CAMExpenseItem,
    evaluate_autonomous_fleet_toll_and_deductible_escrow,
    evaluate_commercial_cam_lease_reconciliation,
    evaluate_eor_cross_border_payroll_statutory_escrow,
)


class TestFleetMobilityPropLeaseEORPayrollGuard(unittest.TestCase):
    def test_commercial_cam_lease_reconciliation_and_capex_exclusion(self) -> None:
        items = [
            CAMExpenseItem("exp_1", "OPERATING_MAINTENANCE", 120_000_00),
            CAMExpenseItem("exp_2", "PROPERTY_TAX_UTILITY", 80_000_00),
            CAMExpenseItem("exp_3", "STRUCTURAL_CAPITAL_ROOF", 50_000_00),
        ]
        blocked = evaluate_commercial_cam_lease_reconciliation(
            lease_id="lease_nnn_01",
            tenant_pro_rata_share_bps=1000,  # 10%
            prior_year_controllable_cam_minor=10_000_00,
            annual_cam_cap_bps=500,  # 5% cap -> max controllable $10,500.00
            estimated_prepaid_cam_minor=18_000_00,
            expense_items=items,
            landlord_forces_uncapped_structural_pass_through=True,
        )
        self.assertFalse(blocked.admitted)
        self.assertEqual(
            blocked.decision_code,
            "EXCLUDED_STRUCTURAL_CAPEX_CAM_PASS_THROUGH_BLOCKED",
        )
        self.assertEqual(blocked.excluded_capex_or_overhead_minor, 5_000_00)

        reconciled = evaluate_commercial_cam_lease_reconciliation(
            lease_id="lease_nnn_01",
            tenant_pro_rata_share_bps=1000,
            prior_year_controllable_cam_minor=10_000_00,
            annual_cam_cap_bps=500,
            estimated_prepaid_cam_minor=18_000_00,
            expense_items=items,
            landlord_forces_uncapped_structural_pass_through=False,
        )
        self.assertTrue(reconciled.admitted)
        self.assertEqual(
            reconciled.decision_code,
            "CAM_CONTROLLABLE_CAP_APPLIED_AND_RECONCILED",
        )
        self.assertEqual(reconciled.capped_controllable_cam_minor, 10_500_00)
        self.assertEqual(reconciled.final_reconciled_cam_minor, 18_500_00)
        self.assertEqual(reconciled.true_up_delta_minor, 500_00)

    def test_autonomous_fleet_toll_citation_routing_and_deductible(self) -> None:
        unsigned = evaluate_autonomous_fleet_toll_and_deductible_escrow(
            trip_id="trip_av_01",
            lessee_security_deposit_minor=200_000,
            gnss_verified_toll_minor=4_500,
            billed_transponder_toll_minor=9_000,
            traffic_citation_fine_minor=15_000,
            autonomous_driving_mode_active_at_citation=True,
            collision_repair_estimate_minor=80_000,
            policy_deductible_cap_minor=50_000,
            telematics_signed_crash_log_valid=False,
        )
        self.assertFalse(unsigned.admitted)
        self.assertEqual(
            unsigned.decision_code,
            "UNSIGNED_TELEMATICS_COLLISION_CLAIM_BLOCKED",
        )

        settled = evaluate_autonomous_fleet_toll_and_deductible_escrow(
            trip_id="trip_av_01",
            lessee_security_deposit_minor=200_000,
            gnss_verified_toll_minor=4_500,
            billed_transponder_toll_minor=9_000,
            traffic_citation_fine_minor=15_000,
            autonomous_driving_mode_active_at_citation=True,
            collision_repair_estimate_minor=80_000,
            policy_deductible_cap_minor=50_000,
            telematics_signed_crash_log_valid=True,
        )
        self.assertTrue(settled.admitted)
        self.assertEqual(
            settled.decision_code,
            "AV_CITATION_ROUTED_TO_OPERATOR_AND_ESCROW_SETTLED",
        )
        self.assertEqual(settled.duplicate_transponder_scrubbed_minor, 4_500)
        self.assertEqual(settled.citation_liability_party, "AV_OPERATOR_FSD_ENGAGED")
        self.assertEqual(settled.deductible_captured_minor, 50_000)
        self.assertEqual(settled.lessee_deposit_refund_minor, 145_500)
        self.assertEqual(settled.conservation_delta_minor, 0)

    def test_eor_cross_border_payroll_statutory_escrow(self) -> None:
        misclassified = evaluate_eor_cross_border_payroll_statutory_escrow(
            payroll_cycle_id="pay_2026_10_de",
            jurisdiction="DE",
            gross_wages_minor=600_000,
            employer_statutory_rate_bps=2100,
            employee_withholding_rate_bps=3200,
            eor_platform_fee_minor=49_900,
            prefunded_escrow_balance_minor=800_000,
            statutory_minimum_wage_minor=220_000,
            worker_misclassification_risk_flagged=True,
        )
        self.assertFalse(misclassified.admitted)
        self.assertEqual(
            misclassified.decision_code,
            "EOR_WORKER_MISCLASSIFICATION_COMPLIANCE_HOLD",
        )

        underfunded = evaluate_eor_cross_border_payroll_statutory_escrow(
            payroll_cycle_id="pay_2026_10_de",
            jurisdiction="DE",
            gross_wages_minor=600_000,
            employer_statutory_rate_bps=2100,
            employee_withholding_rate_bps=3200,
            eor_platform_fee_minor=49_900,
            prefunded_escrow_balance_minor=700_000,
            statutory_minimum_wage_minor=220_000,
            worker_misclassification_risk_flagged=False,
        )
        self.assertFalse(underfunded.admitted)
        self.assertEqual(
            underfunded.decision_code,
            "EOR_PAYROLL_PREFUNDING_DEFICIT_BLOCKED",
        )

        settled = evaluate_eor_cross_border_payroll_statutory_escrow(
            payroll_cycle_id="pay_2026_10_de",
            jurisdiction="DE",
            gross_wages_minor=600_000,
            employer_statutory_rate_bps=2100,
            employee_withholding_rate_bps=3200,
            eor_platform_fee_minor=49_900,
            prefunded_escrow_balance_minor=800_000,
            statutory_minimum_wage_minor=220_000,
            worker_misclassification_risk_flagged=False,
        )
        self.assertTrue(settled.admitted)
        self.assertEqual(
            settled.decision_code,
            "EOR_STATUTORY_PAYROLL_DISBURSEMENT_SETTLED",
        )
        self.assertEqual(settled.total_funding_required_minor, 775_900)
        self.assertEqual(settled.net_take_home_pay_minor, 408_000)
        self.assertEqual(settled.conservation_delta_minor, 0)


if __name__ == "__main__":
    unittest.main()
