"""Stage 31: Construction AIA G702/G703 Mechanics' Lien-Waiver Escrow, Sovereign Procurement Bid-Bond / Domestic-Content Guard & Legal IOLTA Trust Interest Sweep Guard.

Implements deterministic AI-Native settlement guardrails for:
1. Construction AIA G702/G703 Progress Billing, Conditional/Unconditional Subcontractor Mechanics'
   Lien-Waiver verification, and statutory retainage holdback (`evaluate_aia_g702_mechanics_lien_waiver_escrow`).
2. Sovereign / Public-Sector Procurement (FAR / Buy-American / EU Public Procurement Directive)
   Bid-Bond verification, debarment registry screening, and domestic-content threshold enforcement
   (`evaluate_sovereign_procurement_bid_bond_and_domestic_content`).
3. Legal / Fiduciary IOLTA Client Trust Account anti-commingling, unearned retainer drawdown gating,
   and statutory bar-foundation interest sweep (`evaluate_iolta_fiduciary_trust_account_guard`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class SubcontractorLienWaiver:
    subcontractor_id: str
    prior_period_paid_minor: int
    unconditional_prior_waiver_signed: bool
    current_period_billed_minor: int
    conditional_current_waiver_signed: bool


@dataclass(frozen=True)
class AIAG702LienWaiverResult:
    application_id: str
    admitted: bool
    decision_code: str
    gross_work_completed_this_period_minor: int
    retainage_withheld_minor: int
    net_progress_payment_minor: int
    missing_waiver_subcontractors: tuple[str, ...]
    conservation_delta_minor: int


@dataclass(frozen=True)
class SovereignProcurementBidResult:
    tender_id: str
    bidder_id: str
    admitted: bool
    decision_code: str
    bid_amount_minor: int
    required_bid_bond_minor: int
    verified_domestic_content_bps: int
    required_domestic_content_bps: int


@dataclass(frozen=True)
class IOLTATrustGuardResult:
    matter_id: str
    admitted: bool
    decision_code: str
    client_trust_balance_before_minor: int
    verified_earned_fees_transfer_minor: int
    client_trust_balance_after_minor: int
    accrued_interest_swept_to_bar_foundation_minor: int
    conservation_delta_minor: int


def evaluate_aia_g702_mechanics_lien_waiver_escrow(
    *,
    application_id: str,
    scheduled_value_minor: int,
    cumulative_completed_to_date_minor: int,
    previous_certificates_gross_minor: int,
    retainage_rate_bps: int,
    subcontractor_waivers: Sequence[SubcontractorLienWaiver],
) -> AIAG702LienWaiverResult:
    """Verify AIA G702/G703 progress draw against subcontractor mechanics' lien waivers and retainage holdbacks."""
    if cumulative_completed_to_date_minor > scheduled_value_minor:
        gross_this_period = max(0, cumulative_completed_to_date_minor - previous_certificates_gross_minor)
        return AIAG702LienWaiverResult(
            application_id=application_id,
            admitted=False,
            decision_code="AIA_G702_OVERBILLING_BEYOND_SCHEDULED_VALUE_BLOCKED",
            gross_work_completed_this_period_minor=gross_this_period,
            retainage_withheld_minor=0,
            net_progress_payment_minor=0,
            missing_waiver_subcontractors=(),
            conservation_delta_minor=0,
        )

    gross_this_period = max(0, cumulative_completed_to_date_minor - previous_certificates_gross_minor)
    retainage_withheld_minor = (gross_this_period * retainage_rate_bps) // 10000
    net_progress_payment_minor = gross_this_period - retainage_withheld_minor
    conservation_delta_minor = gross_this_period - (retainage_withheld_minor + net_progress_payment_minor)

    missing_subs: list[str] = []
    for sub in subcontractor_waivers:
        if sub.prior_period_paid_minor > 0 and not sub.unconditional_prior_waiver_signed:
            missing_subs.append(sub.subcontractor_id)
        elif sub.current_period_billed_minor > 0 and not sub.conditional_current_waiver_signed:
            missing_subs.append(sub.subcontractor_id)

    if missing_subs:
        return AIAG702LienWaiverResult(
            application_id=application_id,
            admitted=False,
            decision_code="SUBCONTRACTOR_MECHANICS_LIEN_WAIVER_MISSING_HOLD",
            gross_work_completed_this_period_minor=gross_this_period,
            retainage_withheld_minor=retainage_withheld_minor,
            net_progress_payment_minor=0,
            missing_waiver_subcontractors=tuple(missing_subs),
            conservation_delta_minor=conservation_delta_minor,
        )

    return AIAG702LienWaiverResult(
        application_id=application_id,
        admitted=True,
        decision_code="AIA_G702_LIEN_WAIVER_VERIFIED_PROGRESS_RELEASED",
        gross_work_completed_this_period_minor=gross_this_period,
        retainage_withheld_minor=retainage_withheld_minor,
        net_progress_payment_minor=net_progress_payment_minor,
        missing_waiver_subcontractors=(),
        conservation_delta_minor=conservation_delta_minor,
    )


def evaluate_sovereign_procurement_bid_bond_and_domestic_content(
    *,
    tender_id: str,
    bidder_id: str,
    bid_amount_minor: int,
    required_bid_bond_bps: int,
    posted_surety_bond_minor: int,
    surety_signature_valid: bool,
    sam_gov_or_eu_debarment_listed: bool,
    verified_domestic_bom_cost_minor: int,
    total_bom_cost_minor: int,
    required_domestic_content_bps: int,
) -> SovereignProcurementBidResult:
    """Validate public-sector procurement bid bonds, debarment lists, and Buy-American / domestic BOM content."""
    required_bid_bond_minor = (bid_amount_minor * required_bid_bond_bps) // 10000
    verified_domestic_bps = (
        (verified_domestic_bom_cost_minor * 10000) // total_bom_cost_minor
        if total_bom_cost_minor > 0
        else 0
    )

    if sam_gov_or_eu_debarment_listed:
        return SovereignProcurementBidResult(
            tender_id=tender_id,
            bidder_id=bidder_id,
            admitted=False,
            decision_code="DEBARRED_OR_EXCLUDED_VENDOR_REGISTRY_BLOCKED",
            bid_amount_minor=bid_amount_minor,
            required_bid_bond_minor=required_bid_bond_minor,
            verified_domestic_content_bps=verified_domestic_bps,
            required_domestic_content_bps=required_domestic_content_bps,
        )

    if not surety_signature_valid or posted_surety_bond_minor < required_bid_bond_minor:
        return SovereignProcurementBidResult(
            tender_id=tender_id,
            bidder_id=bidder_id,
            admitted=False,
            decision_code="SURETY_BID_BOND_INSUFFICIENT_OR_UNSIGNED_BLOCKED",
            bid_amount_minor=bid_amount_minor,
            required_bid_bond_minor=required_bid_bond_minor,
            verified_domestic_content_bps=verified_domestic_bps,
            required_domestic_content_bps=required_domestic_content_bps,
        )

    if verified_domestic_bps < required_domestic_content_bps:
        return SovereignProcurementBidResult(
            tender_id=tender_id,
            bidder_id=bidder_id,
            admitted=False,
            decision_code="DOMESTIC_CONTENT_BUY_AMERICAN_THRESHOLD_BREACH_BLOCKED",
            bid_amount_minor=bid_amount_minor,
            required_bid_bond_minor=required_bid_bond_minor,
            verified_domestic_content_bps=verified_domestic_bps,
            required_domestic_content_bps=required_domestic_content_bps,
        )

    return SovereignProcurementBidResult(
        tender_id=tender_id,
        bidder_id=bidder_id,
        admitted=True,
        decision_code="SOVEREIGN_PROCUREMENT_BID_COMPLIANT_ADMITTED",
        bid_amount_minor=bid_amount_minor,
        required_bid_bond_minor=required_bid_bond_minor,
        verified_domestic_content_bps=verified_domestic_bps,
        required_domestic_content_bps=required_domestic_content_bps,
    )


def evaluate_iolta_fiduciary_trust_account_guard(
    *,
    matter_id: str,
    client_trust_balance_minor: int,
    requested_operating_drawdown_minor: int,
    client_approved_earned_billing_minor: int,
    firm_operating_expense_charged_directly_to_trust: bool,
    accrued_trust_interest_minor: int,
    firm_attempts_to_retain_trust_interest: bool = False,
) -> IOLTATrustGuardResult:
    """Enforce ABA Model Rule 1.15 IOLTA trust separation, earned-fee drawdown ceilings, and bar-foundation interest sweep."""
    if firm_operating_expense_charged_directly_to_trust:
        return IOLTATrustGuardResult(
            matter_id=matter_id,
            admitted=False,
            decision_code="IOLTA_TRUST_COMMINGLING_OR_DIRECT_OPERATING_DEBIT_BLOCKED",
            client_trust_balance_before_minor=client_trust_balance_minor,
            verified_earned_fees_transfer_minor=0,
            client_trust_balance_after_minor=client_trust_balance_minor,
            accrued_interest_swept_to_bar_foundation_minor=accrued_trust_interest_minor,
            conservation_delta_minor=0,
        )

    if firm_attempts_to_retain_trust_interest and accrued_trust_interest_minor > 0:
        return IOLTATrustGuardResult(
            matter_id=matter_id,
            admitted=False,
            decision_code="IOLTA_INTEREST_DIVERSION_FROM_BAR_FOUNDATION_BLOCKED",
            client_trust_balance_before_minor=client_trust_balance_minor,
            verified_earned_fees_transfer_minor=0,
            client_trust_balance_after_minor=client_trust_balance_minor,
            accrued_interest_swept_to_bar_foundation_minor=accrued_trust_interest_minor,
            conservation_delta_minor=0,
        )

    if (
        requested_operating_drawdown_minor > client_approved_earned_billing_minor
        or requested_operating_drawdown_minor > client_trust_balance_minor
    ):
        return IOLTATrustGuardResult(
            matter_id=matter_id,
            admitted=False,
            decision_code="IOLTA_UNEARNED_RETAINER_PREMATURE_DRAWDOWN_BLOCKED",
            client_trust_balance_before_minor=client_trust_balance_minor,
            verified_earned_fees_transfer_minor=0,
            client_trust_balance_after_minor=client_trust_balance_minor,
            accrued_interest_swept_to_bar_foundation_minor=accrued_trust_interest_minor,
            conservation_delta_minor=0,
        )

    balance_after = client_trust_balance_minor - requested_operating_drawdown_minor
    conservation_delta = client_trust_balance_minor - (
        requested_operating_drawdown_minor + balance_after
    )
    return IOLTATrustGuardResult(
        matter_id=matter_id,
        admitted=True,
        decision_code="IOLTA_EARNED_FEE_DISBURSED_AND_BAR_INTEREST_SWEPT",
        client_trust_balance_before_minor=client_trust_balance_minor,
        verified_earned_fees_transfer_minor=requested_operating_drawdown_minor,
        client_trust_balance_after_minor=balance_after,
        accrued_interest_swept_to_bar_foundation_minor=accrued_trust_interest_minor,
        conservation_delta_minor=conservation_delta,
    )
