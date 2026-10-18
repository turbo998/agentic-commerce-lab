"""Stage 28: Autonomous B2B Contractor Milestone Escrow, IRS 1099-K / W-8BEN-E Tax Withholding & Sovereign AI Data-Clean-Room Differential Privacy Budget Guard.

Implements three deterministic enterprise services & data-marketplace invariants:
1. `evaluate_b2b_contractor_milestone_escrow`:
   - Governs autonomous software/engineering/consulting procurement where a buyer agent hires a sub-agent or human contractor across milestones:
     - Requires cryptographic CI/CD or formal-verification acceptance proof (`deliverable_attestation_verified == True`) before releasing milestone escrow (`UNVERIFIED_MILESTONE_DELIVERABLE_ESCROW_HELD`),
     - Blocks scope-creep change-order overruns exceeding `max_change_order_bps` without human principal re-consent (`UNAPPROVED_CHANGE_ORDER_OVERRUN_BLOCKED`),
     - Releases verified milestone payout net of retainage holdback (`MILESTONE_ESCROW_RELEASED_WITH_RETAINAGE_HOLD`).
2. `evaluate_cross_border_tax_withholding_1099k_w8bene`:
   - Enforces IRS §6050W (1099-K) & Chapter 3 (§1441/§1442 W-8BEN-E) statutory backup withholding on cross-border contractor/marketplace payouts:
     - Applies 24% US backup withholding when a domestic payee lacks a verified TIN (`TIN_MISSING_24PCT_BACKUP_WITHHOLDING_APPLIED`),
     - Applies 30% statutory Chapter 3 withholding for foreign payees without a valid W-8BEN-E or tax-treaty LOB claim (`W8BENE_MISSING_30PCT_STATUTORY_WITHHOLDING_APPLIED`),
     - Applies reduced treaty rate (e.g., `0%`–`15%`) when a verified W-8BEN-E treaty article is on file (`TAX_TREATY_RATE_VERIFIED_NET_SETTLED`).
3. `evaluate_data_clean_room_differential_privacy_budget`:
   - Protects clean-room data-licensing and RAG dataset monetization against membership-inference / reconstruction exhaustion:
     - Tracks cumulative $(\varepsilon, \delta)$ differential privacy loss across buyer agent queries and blocks queries that would breach the dataset's `max_epsilon_budget` (`DIFFERENTIAL_PRIVACY_EPSILON_BUDGET_EXHAUSTED_BLOCKED`),
     - Admits privacy-safe clean-room queries and meters per-epsilon royalty settlement (`CLEAN_ROOM_DP_QUERY_ADMITTED_AND_METERED`).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ContractorMilestoneEscrowResult:
    """Result of evaluating a B2B contractor milestone escrow release."""

    released: bool
    decision_code: str
    milestone_id: str
    contracted_milestone_minor: int
    requested_payout_minor: int
    retainage_holdback_minor: int
    net_disbursed_minor: int
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TaxWithholdingSettlementResult:
    """Result of evaluating IRS 1099-K / W-8BEN-E tax withholding on payout."""

    settled: bool
    decision_code: str
    payee_id: str
    gross_payout_minor: int
    applied_withholding_bps: int
    tax_withheld_minor: int
    net_payee_disbursement_minor: int
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DataCleanRoomDpResult:
    """Result of evaluating a data-clean-room differential privacy budget query."""

    admitted: bool
    decision_code: str
    dataset_id: str
    prior_epsilon_consumed: float
    query_epsilon_cost: float
    projected_total_epsilon: float
    max_epsilon_budget: float
    query_royalty_fee_minor: int
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_b2b_contractor_milestone_escrow(
    milestone_context: dict[str, Any],
) -> dict[str, Any]:
    """Verify CI/CD acceptance proofs, change-order caps, and retainage holds for B2B milestone payouts."""

    milestone_id = str(milestone_context.get("milestone_id", "ms_unknown"))
    contracted_minor = max(1, int(milestone_context.get("contracted_milestone_minor", 1)))
    requested_minor = max(0, int(milestone_context.get("requested_payout_minor", contracted_minor)))
    max_change_order_bps = max(0, int(milestone_context.get("max_change_order_bps", 1_000)))
    retainage_bps = max(0, int(milestone_context.get("retainage_holdback_bps", 1_000)))
    attestation_verified = bool(milestone_context.get("deliverable_attestation_verified", False))
    human_change_order_approved = bool(
        milestone_context.get("human_principal_change_order_approved", False)
    )

    overrun_bps = max(0, ((requested_minor - contracted_minor) * 10_000) // contracted_minor)

    if overrun_bps > max_change_order_bps and not human_change_order_approved:
        return ContractorMilestoneEscrowResult(
            released=False,
            decision_code="UNAPPROVED_CHANGE_ORDER_OVERRUN_BLOCKED",
            milestone_id=milestone_id,
            contracted_milestone_minor=contracted_minor,
            requested_payout_minor=requested_minor,
            retainage_holdback_minor=0,
            net_disbursed_minor=0,
            reason_codes=["UNAPPROVED_CHANGE_ORDER_OVERRUN_BLOCKED"],
        ).to_dict()

    if not attestation_verified:
        return ContractorMilestoneEscrowResult(
            released=False,
            decision_code="UNVERIFIED_MILESTONE_DELIVERABLE_ESCROW_HELD",
            milestone_id=milestone_id,
            contracted_milestone_minor=contracted_minor,
            requested_payout_minor=requested_minor,
            retainage_holdback_minor=0,
            net_disbursed_minor=0,
            reason_codes=["UNVERIFIED_MILESTONE_DELIVERABLE_ESCROW_HELD"],
        ).to_dict()

    retainage_minor = (requested_minor * retainage_bps) // 10_000
    net_minor = max(0, requested_minor - retainage_minor)

    return ContractorMilestoneEscrowResult(
        released=True,
        decision_code="MILESTONE_ESCROW_RELEASED_WITH_RETAINAGE_HOLD",
        milestone_id=milestone_id,
        contracted_milestone_minor=contracted_minor,
        requested_payout_minor=requested_minor,
        retainage_holdback_minor=retainage_minor,
        net_disbursed_minor=net_minor,
        reason_codes=["MILESTONE_ESCROW_RELEASED_WITH_RETAINAGE_HOLD"],
    ).to_dict()


def evaluate_cross_border_tax_withholding_1099k_w8bene(
    tax_context: dict[str, Any],
) -> dict[str, Any]:
    """Calculate statutory IRS 1099-K backup withholding (24%) or Chapter 3 W-8BEN-E withholding (30% / treaty)."""

    payee_id = str(tax_context.get("payee_id", "payee_unknown"))
    gross_minor = max(0, int(tax_context.get("gross_payout_minor", 0)))
    is_us_person = bool(tax_context.get("is_us_person", False))
    tin_verified = bool(tax_context.get("us_tin_verified", False))
    w8bene_valid = bool(tax_context.get("w8bene_valid", False))
    treaty_rate_bps = max(0, min(3_000, int(tax_context.get("verified_treaty_withholding_bps", 0))))

    if is_us_person:
        if not tin_verified:
            bps = 2_400  # 24% IRS backup withholding
            withheld = (gross_minor * bps) // 10_000
            return TaxWithholdingSettlementResult(
                settled=True,
                decision_code="TIN_MISSING_24PCT_BACKUP_WITHHOLDING_APPLIED",
                payee_id=payee_id,
                gross_payout_minor=gross_minor,
                applied_withholding_bps=bps,
                tax_withheld_minor=withheld,
                net_payee_disbursement_minor=gross_minor - withheld,
                reason_codes=["TIN_MISSING_24PCT_BACKUP_WITHHOLDING_APPLIED"],
            ).to_dict()
        return TaxWithholdingSettlementResult(
            settled=True,
            decision_code="US_TIN_VERIFIED_ZERO_WITHHOLDING_SETTLED",
            payee_id=payee_id,
            gross_payout_minor=gross_minor,
            applied_withholding_bps=0,
            tax_withheld_minor=0,
            net_payee_disbursement_minor=gross_minor,
            reason_codes=["US_TIN_VERIFIED_ZERO_WITHHOLDING_SETTLED"],
        ).to_dict()

    if not w8bene_valid:
        bps = 3_000  # 30% Chapter 3 statutory withholding
        withheld = (gross_minor * bps) // 10_000
        return TaxWithholdingSettlementResult(
            settled=True,
            decision_code="W8BENE_MISSING_30PCT_STATUTORY_WITHHOLDING_APPLIED",
            payee_id=payee_id,
            gross_payout_minor=gross_minor,
            applied_withholding_bps=bps,
            tax_withheld_minor=withheld,
            net_payee_disbursement_minor=gross_minor - withheld,
            reason_codes=["W8BENE_MISSING_30PCT_STATUTORY_WITHHOLDING_APPLIED"],
        ).to_dict()

    withheld = (gross_minor * treaty_rate_bps) // 10_000
    return TaxWithholdingSettlementResult(
        settled=True,
        decision_code="TAX_TREATY_RATE_VERIFIED_NET_SETTLED",
        payee_id=payee_id,
        gross_payout_minor=gross_minor,
        applied_withholding_bps=treaty_rate_bps,
        tax_withheld_minor=withheld,
        net_payee_disbursement_minor=gross_minor - withheld,
        reason_codes=["TAX_TREATY_RATE_VERIFIED_NET_SETTLED"],
    ).to_dict()


def evaluate_data_clean_room_differential_privacy_budget(
    dp_context: dict[str, Any],
) -> dict[str, Any]:
    """Enforce cumulative differential privacy epsilon budgets in clean-room dataset licensing."""

    dataset_id = str(dp_context.get("dataset_id", "ds_cleanroom_01"))
    prior_eps = max(0.0, float(dp_context.get("prior_epsilon_consumed", 0.0)))
    query_eps = max(0.0, float(dp_context.get("query_epsilon_cost", 0.1)))
    max_eps = max(0.01, float(dp_context.get("max_epsilon_budget", 3.0)))
    price_per_unit_eps_minor = max(0, int(dp_context.get("price_per_unit_epsilon_minor", 10_000)))

    projected = round(prior_eps + query_eps, 6)

    if projected > max_eps:
        return DataCleanRoomDpResult(
            admitted=False,
            decision_code="DIFFERENTIAL_PRIVACY_EPSILON_BUDGET_EXHAUSTED_BLOCKED",
            dataset_id=dataset_id,
            prior_epsilon_consumed=prior_eps,
            query_epsilon_cost=query_eps,
            projected_total_epsilon=projected,
            max_epsilon_budget=max_eps,
            query_royalty_fee_minor=0,
            reason_codes=["DIFFERENTIAL_PRIVACY_EPSILON_BUDGET_EXHAUSTED_BLOCKED"],
        ).to_dict()

    fee_minor = int(round(query_eps * price_per_unit_eps_minor))
    return DataCleanRoomDpResult(
        admitted=True,
        decision_code="CLEAN_ROOM_DP_QUERY_ADMITTED_AND_METERED",
        dataset_id=dataset_id,
        prior_epsilon_consumed=prior_eps,
        query_epsilon_cost=query_eps,
        projected_total_epsilon=projected,
        max_epsilon_budget=max_eps,
        query_royalty_fee_minor=fee_minor,
        reason_codes=["CLEAN_ROOM_DP_QUERY_ADMITTED_AND_METERED"],
    ).to_dict()
