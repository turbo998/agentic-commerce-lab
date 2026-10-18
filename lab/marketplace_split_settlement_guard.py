"""Multi-Party Marketplace Split Settlement Conservation, Sub-Merchant KYB Rolling Reserve Escalation & Negative-Balance Clawback Waterfall Guard (Stage 14).

Enforces three production financial invariants for multi-seller agentic marketplaces
(Stripe Connect / Adyen Balance Platform / UCP Multi-Merchant Carts):

1. Multi-Seller Split Settlement Conservation & Largest Remainder Allocation:
   - Eliminates `+/- 1 cent` pro-rata rounding drift across seller line items using
     the deterministic Largest Remainder Method (Hamilton's Method).
   - Strictly verifies:
     `gross_amount_minor == sum(seller_net_splits) + platform_commission_minor + tax_withholding_minor + rolling_reserve_hold_minor`
     (`SPLIT_SETTLEMENT_CONSERVATION_DRIFT`, `LARGEST_REMAINDER_ALLOCATION_MISMATCH`).

2. Sub-Merchant KYB Risk Tiering & Dynamic Rolling Reserve Escalation:
   - Monitors Visa VAMP dispute ratio (`> 65 bps` / `0.65%`) and 30-day GMV velocity
     spikes (`> 3.5x` 30-day trailing average) to prevent Bust-Out Fraud.
   - Automatically escalates rolling reserve holds from baseline `5%` (`500 bps`)
     to `15%` (`1500 bps`) or `25%` (`2500 bps`) and freezes `T+0` Instant Payouts
     (`ROLLING_RESERVE_ESCALATED_15PCT_INSTANT_PAYOUT_FROZEN`,
      `ROLLING_RESERVE_ESCALATED_25PCT_BUST_OUT_GUARD`).

3. Cross-Seller Partial Fulfillment Default & 4-Stage Clawback Recovery Waterfall:
   - When a defaulting sub-merchant's pending balance cannot cover a bundle refund,
     recovers deterministically in strict order:
     `Pending Settlement Freeze -> Rolling Reserve Offset -> Linked Guarantor Recovery -> Platform Risk Reserve Isolation`.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from decimal import Decimal
import json
from typing import Any


@dataclass(frozen=True)
class SplitSettlementDecision:
    allowed: bool
    decision_code: str
    order_id: str
    gross_amount_minor: int
    total_seller_net_minor: int
    platform_commission_minor: int
    tax_withholding_minor: int
    rolling_reserve_hold_minor: int
    largest_remainder_allocations_minor: tuple[int, ...]
    conservation_delta_minor: int
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class RollingReserveEscalationDecision:
    payouts_allowed: bool
    instant_payout_frozen: bool
    decision_code: str
    seller_id: str
    risk_tier: str
    recommended_reserve_bps: int
    required_reserve_hold_minor: int
    dispute_rate_bps: int
    gmv_velocity_multiple_30d: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ClawbackWaterfallDecision:
    fully_covered: bool
    seller_account_locked: bool
    decision_code: str
    seller_id: str
    refund_obligation_minor: int
    from_pending_settlement_minor: int
    from_rolling_reserve_minor: int
    from_linked_guarantor_minor: int
    from_platform_risk_reserve_minor: int
    uncovered_deficit_minor: int
    reasons: tuple[str, ...]


def allocate_by_largest_remainder(
    total_pool_minor: int,
    weights: list[int],
) -> tuple[int, ...]:
    """Deterministically allocate `total_pool_minor` across `weights` with zero cent drift."""
    if total_pool_minor < 0 or not weights or sum(weights) <= 0:
        return tuple(0 for _ in weights)

    weight_sum = sum(weights)
    floors: list[int] = []
    remainders: list[tuple[int, int]] = []
    for idx, w in enumerate(weights):
        numerator = total_pool_minor * w
        floor_val = numerator // weight_sum
        rem = numerator % weight_sum
        floors.append(floor_val)
        # Sort key uses (-rem, idx) for deterministic tie-breaking
        remainders.append((rem, idx))

    shortfall = total_pool_minor - sum(floors)
    remainders.sort(key=lambda item: (-item[0], item[1]))
    for i in range(shortfall):
        _, target_idx = remainders[i]
        floors[target_idx] += 1

    return tuple(floors)


def evaluate_split_settlement_invariant(
    settlement_bundle: dict[str, Any],
) -> SplitSettlementDecision:
    """Verify multi-seller split conservation and Largest Remainder pro-rata allocation."""
    reasons: list[str] = []

    order_id = str(settlement_bundle.get("order_id", ""))
    gross_amount = int(settlement_bundle.get("gross_amount_minor", 0))
    seller_net_splits = [
        int(x) for x in settlement_bundle.get("seller_net_splits_minor", [])
    ]
    platform_commission = int(settlement_bundle.get("platform_commission_minor", 0))
    tax_withholding = int(settlement_bundle.get("tax_withholding_minor", 0))
    rolling_reserve_hold = int(settlement_bundle.get("rolling_reserve_hold_minor", 0))

    weights = [int(w) for w in settlement_bundle.get("seller_gross_weights_minor", [])]
    claimed_allocations = [
        int(a) for a in settlement_bundle.get("claimed_pro_rata_allocations_minor", [])
    ]
    shared_pool_total = int(
        settlement_bundle.get("shared_pool_to_allocate_minor", gross_amount)
    )

    if (
        gross_amount <= 0
        or any(s < 0 for s in seller_net_splits)
        or platform_commission < 0
        or tax_withholding < 0
        or rolling_reserve_hold < 0
    ):
        reasons.append("NEGATIVE_SETTLEMENT_COMPONENT_BLOCKED")

    expected_allocations: tuple[int, ...] = ()
    if weights:
        expected_allocations = allocate_by_largest_remainder(shared_pool_total, weights)
        if claimed_allocations and tuple(claimed_allocations) != expected_allocations:
            reasons.append("LARGEST_REMAINDER_ALLOCATION_MISMATCH")

    total_seller_net = sum(seller_net_splits)
    accounted_total = (
        total_seller_net
        + platform_commission
        + tax_withholding
        + rolling_reserve_hold
    )
    delta = gross_amount - accounted_total
    if delta != 0:
        reasons.append("SPLIT_SETTLEMENT_CONSERVATION_DRIFT")

    allowed = len(reasons) == 0
    decision_code = (
        "SPLIT_SETTLEMENT_CONSERVATION_VERIFIED" if allowed else reasons[0]
    )

    return SplitSettlementDecision(
        allowed=allowed,
        decision_code=decision_code,
        order_id=order_id,
        gross_amount_minor=gross_amount,
        total_seller_net_minor=total_seller_net,
        platform_commission_minor=platform_commission,
        tax_withholding_minor=tax_withholding,
        rolling_reserve_hold_minor=rolling_reserve_hold,
        largest_remainder_allocations_minor=expected_allocations,
        conservation_delta_minor=delta,
        reasons=tuple(reasons),
    )


def evaluate_seller_kyb_rolling_reserve(
    seller_risk_profile: dict[str, Any],
    *,
    baseline_reserve_bps: int = 500,
    vamp_warning_dispute_bps: int = 65,
    critical_dispute_bps: int = 90,
    velocity_warning_multiple: Decimal = Decimal("3.5"),
    velocity_critical_multiple: Decimal = Decimal("5.0"),
) -> RollingReserveEscalationDecision:
    """Evaluate sub-merchant KYB status, Visa VAMP dispute rate, and GMV spike velocity."""
    reasons: list[str] = []

    seller_id = str(seller_risk_profile.get("seller_id", ""))
    kyb_verified = bool(seller_risk_profile.get("kyb_verified", False))
    dispute_rate_bps = int(seller_risk_profile.get("dispute_rate_bps", 0))
    gmv_velocity = Decimal(
        str(seller_risk_profile.get("gmv_velocity_multiple_30d", "1.0"))
    )
    settlement_gross_minor = int(
        seller_risk_profile.get("current_settlement_gross_minor", 0)
    )
    applied_reserve_bps = int(
        seller_risk_profile.get("applied_reserve_bps", baseline_reserve_bps)
    )
    instant_payout_requested = bool(
        seller_risk_profile.get("instant_payout_requested", False)
    )

    if not kyb_verified:
        reasons.append("SUBMERCHANT_KYB_UNVERIFIED_PAYOUT_BLOCKED")
        return RollingReserveEscalationDecision(
            payouts_allowed=False,
            instant_payout_frozen=True,
            decision_code="SUBMERCHANT_KYB_UNVERIFIED_PAYOUT_BLOCKED",
            seller_id=seller_id,
            risk_tier="UNVERIFIED_100PCT_ESCROW",
            recommended_reserve_bps=10_000,
            required_reserve_hold_minor=settlement_gross_minor,
            dispute_rate_bps=dispute_rate_bps,
            gmv_velocity_multiple_30d=str(gmv_velocity),
            reasons=tuple(reasons),
        )

    vamp_breach = dispute_rate_bps > vamp_warning_dispute_bps
    velocity_breach = gmv_velocity > velocity_warning_multiple
    critical_breach = (
        dispute_rate_bps > critical_dispute_bps
        or gmv_velocity > velocity_critical_multiple
        or (vamp_breach and velocity_breach)
    )

    if critical_breach:
        recommended_bps = 2500
        risk_tier = "HIGH_RISK_25PCT_RESERVE"
        instant_frozen = True
        escalation_code = "ROLLING_RESERVE_ESCALATED_25PCT_BUST_OUT_GUARD"
    elif vamp_breach or velocity_breach:
        recommended_bps = 1500
        risk_tier = "ELEVATED_15PCT_RESERVE"
        instant_frozen = True
        escalation_code = "ROLLING_RESERVE_ESCALATED_15PCT_INSTANT_PAYOUT_FROZEN"
    else:
        recommended_bps = baseline_reserve_bps
        risk_tier = "STANDARD_5PCT"
        instant_frozen = False
        escalation_code = "STANDARD_ROLLING_RESERVE_OK"

    required_hold = (settlement_gross_minor * recommended_bps) // 10_000

    if applied_reserve_bps < recommended_bps:
        reasons.append(escalation_code)
    if instant_frozen and instant_payout_requested:
        reasons.append("INSTANT_PAYOUT_FROZEN_UNDER_RISK_ESCALATION")

    payouts_allowed = len(reasons) == 0
    decision_code = escalation_code if not payouts_allowed else "STANDARD_ROLLING_RESERVE_OK"
    if payouts_allowed and recommended_bps > baseline_reserve_bps:
        decision_code = escalation_code

    return RollingReserveEscalationDecision(
        payouts_allowed=payouts_allowed,
        instant_payout_frozen=instant_frozen,
        decision_code=decision_code,
        seller_id=seller_id,
        risk_tier=risk_tier,
        recommended_reserve_bps=recommended_bps,
        required_reserve_hold_minor=required_hold,
        dispute_rate_bps=dispute_rate_bps,
        gmv_velocity_multiple_30d=str(gmv_velocity),
        reasons=tuple(reasons),
    )


def execute_negative_balance_clawback_waterfall(
    clawback_request: dict[str, Any],
) -> ClawbackWaterfallDecision:
    """Execute the 4-stage deterministic recovery waterfall for a defaulting sub-merchant."""
    reasons: list[str] = []

    seller_id = str(clawback_request.get("seller_id", ""))
    obligation = int(clawback_request.get("refund_obligation_minor", 0))
    pending_avail = max(0, int(clawback_request.get("pending_settlement_available_minor", 0)))
    reserve_avail = max(0, int(clawback_request.get("rolling_reserve_pool_minor", 0)))
    guarantor_avail = max(0, int(clawback_request.get("linked_guarantor_available_minor", 0)))
    platform_buffer_cap = max(
        0, int(clawback_request.get("platform_risk_reserve_cap_minor", 0))
    )

    rem = obligation
    from_pending = min(rem, pending_avail)
    rem -= from_pending

    from_reserve = min(rem, reserve_avail)
    rem -= from_reserve

    from_guarantor = min(rem, guarantor_avail)
    rem -= from_guarantor

    from_platform = min(rem, platform_buffer_cap)
    rem -= from_platform

    uncovered = rem
    seller_locked = (from_guarantor > 0) or (from_platform > 0) or (uncovered > 0)

    if uncovered > 0:
        reasons.append("UNCOVERED_DEFAULT_EXCEEDS_PLATFORM_RISK_BUFFER")
    elif from_platform > 0:
        reasons.append("PLATFORM_RISK_RESERVE_TAPPED_SELLER_LOCKED")

    fully_covered = uncovered == 0
    if not fully_covered:
        decision_code = "UNCOVERED_DEFAULT_EXCEEDS_PLATFORM_RISK_BUFFER"
    elif from_platform > 0:
        decision_code = "CLAWBACK_COVERED_VIA_PLATFORM_RISK_BUFFER_ISOLATION"
    elif from_guarantor > 0:
        decision_code = "CLAWBACK_COVERED_VIA_GUARANTOR_RECOVERY"
    elif from_reserve > 0:
        decision_code = "CLAWBACK_COVERED_VIA_ROLLING_RESERVE"
    else:
        decision_code = "CLAWBACK_COVERED_BY_PENDING_SETTLEMENT"

    return ClawbackWaterfallDecision(
        fully_covered=fully_covered,
        seller_account_locked=seller_locked,
        decision_code=decision_code,
        seller_id=seller_id,
        refund_obligation_minor=obligation,
        from_pending_settlement_minor=from_pending,
        from_rolling_reserve_minor=from_reserve,
        from_linked_guarantor_minor=from_guarantor,
        from_platform_risk_reserve_minor=from_platform,
        uncovered_deficit_minor=uncovered,
        reasons=tuple(reasons),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Stage 14 marketplace split settlement, KYB rolling reserve & clawback guard."
    )
    parser.parse_args(argv)

    split_res = evaluate_split_settlement_invariant(
        {
            "order_id": "ord_mkt_1001",
            "gross_amount_minor": 10_000,
            "seller_net_splits_minor": [2_834, 2_833, 2_833],
            "platform_commission_minor": 800,
            "tax_withholding_minor": 200,
            "rolling_reserve_hold_minor": 500,
            "shared_pool_to_allocate_minor": 8_500,
            "seller_gross_weights_minor": [1, 1, 1],
            "claimed_pro_rata_allocations_minor": [2_834, 2_833, 2_833],
        }
    )
    reserve_res = evaluate_seller_kyb_rolling_reserve(
        {
            "seller_id": "acct_seller_bustout_99",
            "kyb_verified": True,
            "dispute_rate_bps": 82,
            "gmv_velocity_multiple_30d": "4.2",
            "current_settlement_gross_minor": 50_000,
            "applied_reserve_bps": 500,
            "instant_payout_requested": True,
        }
    )
    clawback_res = execute_negative_balance_clawback_waterfall(
        {
            "seller_id": "acct_seller_default_42",
            "refund_obligation_minor": 40_000,
            "pending_settlement_available_minor": 12_000,
            "rolling_reserve_pool_minor": 15_000,
            "linked_guarantor_available_minor": 8_000,
            "platform_risk_reserve_cap_minor": 10_000,
        }
    )
    print(
        json.dumps(
            {
                "stage": "stage14-marketplace-split-settlement-guard",
                "split_conservation_ok": split_res.allowed,
                "largest_remainder_splits": list(
                    split_res.largest_remainder_allocations_minor
                ),
                "bustout_reserve_escalation": reserve_res.decision_code,
                "bustout_recommended_reserve_bps": reserve_res.recommended_reserve_bps,
                "clawback_decision": clawback_res.decision_code,
                "clawback_fully_covered": clawback_res.fully_covered,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
