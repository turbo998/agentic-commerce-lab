"""Stage 30: Commercial Real Estate CAM Lease Audit, Autonomous Fleet Mobility Toll/Deductible Escrow & Cross-Border EOR Payroll Statutory Withholding Guard.

Implements deterministic AI-Native settlement guardrails for:
1. Commercial Real Estate Triple-Net (NNN) Common Area Maintenance (CAM) reconciliation,
   cap enforcement, and excluded capital expenditure clawback (`evaluate_commercial_cam_lease_reconciliation`).
2. Autonomous Robotaxi / Logistics Fleet tolling, municipal traffic citation liability routing,
   and telematics-backed collision deductible escrow (`evaluate_autonomous_fleet_toll_and_deductible_escrow`).
3. Global Employer of Record (EOR) cross-border multi-currency payroll statutory social security,
   pension, and FX pre-funding reserve verification (`evaluate_eor_cross_border_payroll_statutory_escrow`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class CAMExpenseItem:
    expense_id: str
    category: str  # "OPERATING_MAINTENANCE", "STRUCTURAL_CAPITAL_ROOF", "LANDLORD_EXECUTIVE_OVERHEAD", "PROPERTY_TAX_UTILITY"
    gross_expense_minor: int


@dataclass(frozen=True)
class CAMLeaseReconciliationResult:
    lease_id: str
    admitted: bool
    decision_code: str
    tenant_pro_rata_share_bps: int
    raw_allocated_cam_minor: int
    excluded_capex_or_overhead_minor: int
    capped_controllable_cam_minor: int
    final_reconciled_cam_minor: int
    estimated_prepaid_cam_minor: int
    true_up_delta_minor: int  # positive = tenant owes, negative = landlord refund due


@dataclass(frozen=True)
class FleetMobilityEscrowResult:
    trip_id: str
    admitted: bool
    decision_code: str
    verified_gnss_toll_minor: int
    duplicate_transponder_scrubbed_minor: int
    citation_liability_party: str  # "AV_OPERATOR_FSD_ENGAGED", "HUMAN_LESSEE_MANUAL_DRIVE", "NONE"
    citation_fine_minor: int
    deductible_captured_minor: int
    lessee_deposit_refund_minor: int
    conservation_delta_minor: int


@dataclass(frozen=True)
class EORPayrollStatutoryResult:
    payroll_cycle_id: str
    jurisdiction: str
    admitted: bool
    decision_code: str
    gross_wages_minor: int
    employer_statutory_contrib_minor: int
    employee_tax_and_social_withholding_minor: int
    net_take_home_pay_minor: int
    eor_platform_fee_minor: int
    total_funding_required_minor: int
    prefunded_escrow_balance_minor: int
    conservation_delta_minor: int


EXCLUDED_CAM_CATEGORIES = frozenset({
    "STRUCTURAL_CAPITAL_ROOF",
    "LANDLORD_EXECUTIVE_OVERHEAD",
    "LEASING_BROKER_COMMISSION",
})


def evaluate_commercial_cam_lease_reconciliation(
    *,
    lease_id: str,
    tenant_pro_rata_share_bps: int,
    prior_year_controllable_cam_minor: int,
    annual_cam_cap_bps: int,
    estimated_prepaid_cam_minor: int,
    expense_items: Sequence[CAMExpenseItem],
    landlord_forces_uncapped_structural_pass_through: bool = False,
) -> CAMLeaseReconciliationResult:
    """Reconcile NNN commercial lease CAM charges, stripping excluded CapEx and enforcing annual controllable CAM caps."""
    if not (0 < tenant_pro_rata_share_bps <= 10000):
        raise ValueError("tenant_pro_rata_share_bps must be in (0, 10000]")

    raw_total_minor = sum(item.gross_expense_minor for item in expense_items)
    excluded_gross_minor = sum(
        item.gross_expense_minor
        for item in expense_items
        if item.category in EXCLUDED_CAM_CATEGORIES
    )
    uncontrollable_gross_minor = sum(
        item.gross_expense_minor
        for item in expense_items
        if item.category == "PROPERTY_TAX_UTILITY"
    )
    controllable_gross_minor = sum(
        item.gross_expense_minor
        for item in expense_items
        if item.category == "OPERATING_MAINTENANCE"
    )

    raw_allocated_cam_minor = (raw_total_minor * tenant_pro_rata_share_bps) // 10000
    excluded_tenant_share_minor = (excluded_gross_minor * tenant_pro_rata_share_bps) // 10000
    uncontrollable_tenant_share_minor = (uncontrollable_gross_minor * tenant_pro_rata_share_bps) // 10000
    controllable_tenant_share_minor = (controllable_gross_minor * tenant_pro_rata_share_bps) // 10000

    max_controllable_cam_minor = (
        prior_year_controllable_cam_minor * (10000 + annual_cam_cap_bps)
    ) // 10000
    capped_controllable_cam_minor = min(controllable_tenant_share_minor, max_controllable_cam_minor)
    final_reconciled_cam_minor = uncontrollable_tenant_share_minor + capped_controllable_cam_minor
    true_up_delta_minor = final_reconciled_cam_minor - estimated_prepaid_cam_minor

    if excluded_tenant_share_minor > 0 and landlord_forces_uncapped_structural_pass_through:
        return CAMLeaseReconciliationResult(
            lease_id=lease_id,
            admitted=False,
            decision_code="EXCLUDED_STRUCTURAL_CAPEX_CAM_PASS_THROUGH_BLOCKED",
            tenant_pro_rata_share_bps=tenant_pro_rata_share_bps,
            raw_allocated_cam_minor=raw_allocated_cam_minor,
            excluded_capex_or_overhead_minor=excluded_tenant_share_minor,
            capped_controllable_cam_minor=capped_controllable_cam_minor,
            final_reconciled_cam_minor=final_reconciled_cam_minor,
            estimated_prepaid_cam_minor=estimated_prepaid_cam_minor,
            true_up_delta_minor=true_up_delta_minor,
        )

    decision_code = (
        "CAM_CONTROLLABLE_CAP_APPLIED_AND_RECONCILED"
        if controllable_tenant_share_minor > max_controllable_cam_minor or excluded_tenant_share_minor > 0
        else "CAM_RECONCILIATION_VERIFIED"
    )
    return CAMLeaseReconciliationResult(
        lease_id=lease_id,
        admitted=True,
        decision_code=decision_code,
        tenant_pro_rata_share_bps=tenant_pro_rata_share_bps,
        raw_allocated_cam_minor=raw_allocated_cam_minor,
        excluded_capex_or_overhead_minor=excluded_tenant_share_minor,
        capped_controllable_cam_minor=capped_controllable_cam_minor,
        final_reconciled_cam_minor=final_reconciled_cam_minor,
        estimated_prepaid_cam_minor=estimated_prepaid_cam_minor,
        true_up_delta_minor=true_up_delta_minor,
    )


def evaluate_autonomous_fleet_toll_and_deductible_escrow(
    *,
    trip_id: str,
    lessee_security_deposit_minor: int,
    gnss_verified_toll_minor: int,
    billed_transponder_toll_minor: int,
    traffic_citation_fine_minor: int,
    autonomous_driving_mode_active_at_citation: bool,
    collision_repair_estimate_minor: int,
    policy_deductible_cap_minor: int,
    telematics_signed_crash_log_valid: bool,
) -> FleetMobilityEscrowResult:
    """Settle autonomous fleet tolls, route AV vs human traffic citations, and cap collision deductible draws."""
    duplicate_scrubbed_minor = max(0, billed_transponder_toll_minor - gnss_verified_toll_minor)

    if collision_repair_estimate_minor > 0 and not telematics_signed_crash_log_valid:
        return FleetMobilityEscrowResult(
            trip_id=trip_id,
            admitted=False,
            decision_code="UNSIGNED_TELEMATICS_COLLISION_CLAIM_BLOCKED",
            verified_gnss_toll_minor=gnss_verified_toll_minor,
            duplicate_transponder_scrubbed_minor=duplicate_scrubbed_minor,
            citation_liability_party="NONE",
            citation_fine_minor=traffic_citation_fine_minor,
            deductible_captured_minor=0,
            lessee_deposit_refund_minor=lessee_security_deposit_minor,
            conservation_delta_minor=0,
        )

    if traffic_citation_fine_minor > 0:
        if autonomous_driving_mode_active_at_citation:
            citation_party = "AV_OPERATOR_FSD_ENGAGED"
            lessee_citation_charge_minor = 0
        else:
            citation_party = "HUMAN_LESSEE_MANUAL_DRIVE"
            lessee_citation_charge_minor = traffic_citation_fine_minor
    else:
        citation_party = "NONE"
        lessee_citation_charge_minor = 0

    deductible_captured_minor = min(collision_repair_estimate_minor, policy_deductible_cap_minor)
    total_lessee_deduction_minor = min(
        lessee_security_deposit_minor,
        gnss_verified_toll_minor + lessee_citation_charge_minor + deductible_captured_minor,
    )
    lessee_deposit_refund_minor = lessee_security_deposit_minor - total_lessee_deduction_minor
    conservation_delta_minor = lessee_security_deposit_minor - (
        total_lessee_deduction_minor + lessee_deposit_refund_minor
    )

    decision_code = (
        "AV_CITATION_ROUTED_TO_OPERATOR_AND_ESCROW_SETTLED"
        if citation_party == "AV_OPERATOR_FSD_ENGAGED"
        else "FLEET_MOBILITY_ESCROW_SETTLED"
    )
    return FleetMobilityEscrowResult(
        trip_id=trip_id,
        admitted=True,
        decision_code=decision_code,
        verified_gnss_toll_minor=gnss_verified_toll_minor,
        duplicate_transponder_scrubbed_minor=duplicate_scrubbed_minor,
        citation_liability_party=citation_party,
        citation_fine_minor=traffic_citation_fine_minor,
        deductible_captured_minor=deductible_captured_minor,
        lessee_deposit_refund_minor=lessee_deposit_refund_minor,
        conservation_delta_minor=conservation_delta_minor,
    )


def evaluate_eor_cross_border_payroll_statutory_escrow(
    *,
    payroll_cycle_id: str,
    jurisdiction: str,
    gross_wages_minor: int,
    employer_statutory_rate_bps: int,
    employee_withholding_rate_bps: int,
    eor_platform_fee_minor: int,
    prefunded_escrow_balance_minor: int,
    statutory_minimum_wage_minor: int,
    worker_misclassification_risk_flagged: bool = False,
) -> EORPayrollStatutoryResult:
    """Verify cross-border EOR payroll statutory social contributions, minimum wage floor, and pre-funding adequacy."""
    employer_statutory_contrib_minor = (gross_wages_minor * employer_statutory_rate_bps) // 10000
    employee_withholding_minor = (gross_wages_minor * employee_withholding_rate_bps) // 10000
    net_take_home_pay_minor = gross_wages_minor - employee_withholding_minor
    total_funding_required_minor = (
        gross_wages_minor + employer_statutory_contrib_minor + eor_platform_fee_minor
    )
    conservation_delta_minor = total_funding_required_minor - (
        net_take_home_pay_minor
        + employee_withholding_minor
        + employer_statutory_contrib_minor
        + eor_platform_fee_minor
    )

    if worker_misclassification_risk_flagged:
        return EORPayrollStatutoryResult(
            payroll_cycle_id=payroll_cycle_id,
            jurisdiction=jurisdiction,
            admitted=False,
            decision_code="EOR_WORKER_MISCLASSIFICATION_COMPLIANCE_HOLD",
            gross_wages_minor=gross_wages_minor,
            employer_statutory_contrib_minor=employer_statutory_contrib_minor,
            employee_tax_and_social_withholding_minor=employee_withholding_minor,
            net_take_home_pay_minor=net_take_home_pay_minor,
            eor_platform_fee_minor=eor_platform_fee_minor,
            total_funding_required_minor=total_funding_required_minor,
            prefunded_escrow_balance_minor=prefunded_escrow_balance_minor,
            conservation_delta_minor=conservation_delta_minor,
        )

    if gross_wages_minor < statutory_minimum_wage_minor:
        return EORPayrollStatutoryResult(
            payroll_cycle_id=payroll_cycle_id,
            jurisdiction=jurisdiction,
            admitted=False,
            decision_code="STATUTORY_MINIMUM_WAGE_FLOOR_VIOLATION_BLOCKED",
            gross_wages_minor=gross_wages_minor,
            employer_statutory_contrib_minor=employer_statutory_contrib_minor,
            employee_tax_and_social_withholding_minor=employee_withholding_minor,
            net_take_home_pay_minor=net_take_home_pay_minor,
            eor_platform_fee_minor=eor_platform_fee_minor,
            total_funding_required_minor=total_funding_required_minor,
            prefunded_escrow_balance_minor=prefunded_escrow_balance_minor,
            conservation_delta_minor=conservation_delta_minor,
        )

    if prefunded_escrow_balance_minor < total_funding_required_minor:
        return EORPayrollStatutoryResult(
            payroll_cycle_id=payroll_cycle_id,
            jurisdiction=jurisdiction,
            admitted=False,
            decision_code="EOR_PAYROLL_PREFUNDING_DEFICIT_BLOCKED",
            gross_wages_minor=gross_wages_minor,
            employer_statutory_contrib_minor=employer_statutory_contrib_minor,
            employee_tax_and_social_withholding_minor=employee_withholding_minor,
            net_take_home_pay_minor=net_take_home_pay_minor,
            eor_platform_fee_minor=eor_platform_fee_minor,
            total_funding_required_minor=total_funding_required_minor,
            prefunded_escrow_balance_minor=prefunded_escrow_balance_minor,
            conservation_delta_minor=conservation_delta_minor,
        )

    return EORPayrollStatutoryResult(
        payroll_cycle_id=payroll_cycle_id,
        jurisdiction=jurisdiction,
        admitted=True,
        decision_code="EOR_STATUTORY_PAYROLL_DISBURSEMENT_SETTLED",
        gross_wages_minor=gross_wages_minor,
        employer_statutory_contrib_minor=employer_statutory_contrib_minor,
        employee_tax_and_social_withholding_minor=employee_withholding_minor,
        net_take_home_pay_minor=net_take_home_pay_minor,
        eor_platform_fee_minor=eor_platform_fee_minor,
        total_funding_required_minor=total_funding_required_minor,
        prefunded_escrow_balance_minor=prefunded_escrow_balance_minor,
        conservation_delta_minor=conservation_delta_minor,
    )
