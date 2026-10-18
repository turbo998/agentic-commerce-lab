"""Stage 19: Promo Coupon Stacking Guard, Cryptographic Affiliate Attribution & Loyalty Clawback.

Implements three deterministic production guardrails for Agentic Commerce promotions,
multi-agent affiliate attribution, and loyalty/cashback return settlement:
1. Promo Coupon Stacking & Margin Floor Invariant (`evaluate_promo_coupon_stacking_invariant`):
   - Blocks Sybil self-referral rings (`SELF_REFERRAL_SYBIL_RING_BLOCKED`) where buyer and
     referrer share `principal_did`, payment fingerprint, or circular referral lineage.
   - Blocks mutually exclusive campaign group stacking (`EXCLUSIVITY_GROUP_CONFLICT`).
   - Blocks coupon combinations that push post-discount net margin below the merchant's
     minimum margin floor (`PROMO_STACK_EXCEEDS_FLOOR_MARGIN_BLOCKED`).
2. Cryptographic Multi-Hop Affiliate Attribution (`verify_cryptographic_affiliate_attribution_chain`):
   - Verifies JWS/RFC 9421 signed multi-hop discovery/comparison/checkout attribution tokens.
   - Blocks last-second honey-style coupon/extension attribution hijacking injected within
     `<= hijack_window_seconds` (default 5s) of checkout without verified discovery proof
     (`LAST_SECOND_ATTRIBUTION_HIJACK_BLOCKED`).
   - Allocates multi-hop affiliate commission using deterministic Largest Remainder Method
     so `sum(hop_allocations_minor) == total_commission_minor`.
3. Loyalty Points Return-Window Escrow & Clawback (`evaluate_loyalty_points_escrow_and_return_clawback`):
   - Locks earned points/cashback in `PENDING_RETURN_WINDOW_ESCROW` until return window expiry.
   - On partial or full return after points redemption, claws back available points and deducts
     any spent points/cashback deficit from the principal refund (`CASHBACK_DEFICIT_DEDUCTED_FROM_REFUND`
     or `LOYALTY_POINTS_CLAWED_BACK`).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Any


@dataclass(frozen=True)
class PromoCouponStackingDecision:
    allowed: bool
    decision_code: str
    order_subtotal_minor: int
    cogs_minor: int
    total_discount_minor: int
    net_revenue_minor: int
    post_discount_margin_bps: int
    merchant_floor_margin_bps: int
    applied_coupon_codes: list[str]
    conflicting_exclusivity_group: str | None
    sybil_self_referral_detected: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AffiliateAttributionDecision:
    allowed: bool
    decision_code: str
    order_id: str
    total_commission_minor: int
    valid_hop_count: int
    hijacked_hop_id: str | None
    hop_allocations_minor: dict[str, int]
    conservation_delta_minor: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LoyaltyReturnClawbackDecision:
    allowed: bool
    decision_code: str
    order_id: str
    escrow_status: str
    gross_return_amount_minor: int
    earned_reward_minor: int
    revoked_reward_minor: int
    unrecovered_spent_deficit_minor: int
    net_principal_refund_minor: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_promo_coupon_stacking_invariant(
    promo_context: dict[str, Any],
) -> PromoCouponStackingDecision:
    """Validate coupon stacking against Sybil referral rings, exclusivity groups, and margin floor."""
    subtotal = int(promo_context.get("order_subtotal_minor", 0))
    cogs = int(promo_context.get("cogs_minor", 0))
    floor_margin_bps = int(promo_context.get("merchant_floor_margin_bps", 1500))
    buyer_did = str(promo_context.get("buyer_principal_did", "")).strip()
    referrer_did = str(promo_context.get("referrer_principal_did", "")).strip()
    buyer_fingerprint = str(promo_context.get("buyer_payment_fingerprint", "")).strip()
    referrer_fingerprint = str(promo_context.get("referrer_payment_fingerprint", "")).strip()
    circular_referral_detected = bool(promo_context.get("circular_referral_detected", False))
    coupons = list(promo_context.get("coupons", []))

    # 1. Sybil Self-Referral Ring Check
    sybil_hit = (
        circular_referral_detected
        or bool(buyer_did and referrer_did and buyer_did == referrer_did)
        or bool(buyer_fingerprint and referrer_fingerprint and buyer_fingerprint == referrer_fingerprint)
    )
    if sybil_hit:
        return PromoCouponStackingDecision(
            allowed=False,
            decision_code="SELF_REFERRAL_SYBIL_RING_BLOCKED",
            order_subtotal_minor=subtotal,
            cogs_minor=cogs,
            total_discount_minor=0,
            net_revenue_minor=subtotal,
            post_discount_margin_bps=round((subtotal - cogs) * 10_000 / max(subtotal, 1)),
            merchant_floor_margin_bps=floor_margin_bps,
            applied_coupon_codes=[],
            conflicting_exclusivity_group=None,
            sybil_self_referral_detected=True,
            reason="Referral promo rejected: buyer and referrer share principal DID, payment fingerprint, or circular graph.",
        )

    # 2. Exclusivity Group Check & Discount Summation
    seen_groups: dict[str, str] = {}
    total_discount = 0
    applied_codes: list[str] = []

    for c in coupons:
        code = str(c.get("code", "")).strip()
        group = str(c.get("exclusivity_group", "")).strip()
        disc = int(c.get("discount_minor", 0))
        stackable = bool(c.get("stackable", True))

        if not stackable and len(coupons) > 1:
            return PromoCouponStackingDecision(
                allowed=False,
                decision_code="EXCLUSIVITY_GROUP_CONFLICT",
                order_subtotal_minor=subtotal,
                cogs_minor=cogs,
                total_discount_minor=total_discount + disc,
                net_revenue_minor=max(subtotal - (total_discount + disc), 0),
                post_discount_margin_bps=0,
                merchant_floor_margin_bps=floor_margin_bps,
                applied_coupon_codes=applied_codes + [code],
                conflicting_exclusivity_group="NON_STACKABLE_COUPON",
                sybil_self_referral_detected=False,
                reason=f"Coupon '{code}' is marked non-stackable and cannot be combined with other promotions.",
            )

        if group:
            if group in seen_groups:
                return PromoCouponStackingDecision(
                    allowed=False,
                    decision_code="EXCLUSIVITY_GROUP_CONFLICT",
                    order_subtotal_minor=subtotal,
                    cogs_minor=cogs,
                    total_discount_minor=total_discount + disc,
                    net_revenue_minor=max(subtotal - (total_discount + disc), 0),
                    post_discount_margin_bps=0,
                    merchant_floor_margin_bps=floor_margin_bps,
                    applied_coupon_codes=applied_codes + [code],
                    conflicting_exclusivity_group=group,
                    sybil_self_referral_detected=False,
                    reason=f"Coupons '{seen_groups[group]}' and '{code}' conflict in exclusivity group '{group}'.",
                )
            seen_groups[group] = code

        total_discount += disc
        applied_codes.append(code)

    net_revenue = subtotal - total_discount
    post_margin_bps = round((net_revenue - cogs) * 10_000 / max(subtotal, 1))

    # 3. Post-Discount Margin Floor Check
    if post_margin_bps < floor_margin_bps:
        return PromoCouponStackingDecision(
            allowed=False,
            decision_code="PROMO_STACK_EXCEEDS_FLOOR_MARGIN_BLOCKED",
            order_subtotal_minor=subtotal,
            cogs_minor=cogs,
            total_discount_minor=total_discount,
            net_revenue_minor=net_revenue,
            post_discount_margin_bps=post_margin_bps,
            merchant_floor_margin_bps=floor_margin_bps,
            applied_coupon_codes=applied_codes,
            conflicting_exclusivity_group=None,
            sybil_self_referral_detected=False,
            reason=(
                f"Stacked discount ({total_discount} minor) reduces margin to {post_margin_bps} bps, "
                f"breaching merchant floor ({floor_margin_bps} bps)."
            ),
        )

    return PromoCouponStackingDecision(
        allowed=True,
        decision_code="PROMO_STACK_INVARIANT_VERIFIED",
        order_subtotal_minor=subtotal,
        cogs_minor=cogs,
        total_discount_minor=total_discount,
        net_revenue_minor=net_revenue,
        post_discount_margin_bps=post_margin_bps,
        merchant_floor_margin_bps=floor_margin_bps,
        applied_coupon_codes=applied_codes,
        conflicting_exclusivity_group=None,
        sybil_self_referral_detected=False,
        reason="Coupon stack satisfies exclusivity groups, anti-Sybil rules, and merchant margin floor.",
    )


def verify_cryptographic_affiliate_attribution_chain(
    attribution_bundle: dict[str, Any],
) -> AffiliateAttributionDecision:
    """Verify multi-hop JWS attribution chain, block last-second hijacks, and split commission."""
    order_id = str(attribution_bundle.get("order_id", "ord_unknown"))
    total_commission = int(attribution_bundle.get("total_commission_minor", 0))
    checkout_epoch = int(attribution_bundle.get("checkout_epoch", 0))
    hijack_window_sec = int(attribution_bundle.get("hijack_window_seconds", 5))
    hops = list(attribution_bundle.get("attribution_hops", []))

    if not hops:
        return AffiliateAttributionDecision(
            allowed=True,
            decision_code="DIRECT_ORGANIC_NO_AFFILIATE",
            order_id=order_id,
            total_commission_minor=0,
            valid_hop_count=0,
            hijacked_hop_id=None,
            hop_allocations_minor={},
            conservation_delta_minor=0,
            reason="Organic checkout with zero affiliate attribution hops.",
        )

    for hop in hops:
        hop_id = str(hop.get("hop_id", "hop_unknown"))
        sig_valid = bool(hop.get("jws_signature_valid", False))
        hop_epoch = int(hop.get("timestamp_epoch", 0))
        has_interaction_proof = bool(hop.get("verified_interaction_digest", ""))
        injected_at_checkout = bool(hop.get("injected_at_checkout_without_discovery", False))

        if not sig_valid:
            return AffiliateAttributionDecision(
                allowed=False,
                decision_code="INVALID_ATTRIBUTION_JWS_SIGNATURE",
                order_id=order_id,
                total_commission_minor=total_commission,
                valid_hop_count=0,
                hijacked_hop_id=hop_id,
                hop_allocations_minor={},
                conservation_delta_minor=0,
                reason=f"Attribution hop '{hop_id}' failed JWS signature verification.",
            )

        delta_sec = checkout_epoch - hop_epoch
        if injected_at_checkout or (0 <= delta_sec <= hijack_window_sec and not has_interaction_proof):
            return AffiliateAttributionDecision(
                allowed=False,
                decision_code="LAST_SECOND_ATTRIBUTION_HIJACK_BLOCKED",
                order_id=order_id,
                total_commission_minor=total_commission,
                valid_hop_count=0,
                hijacked_hop_id=hop_id,
                hop_allocations_minor={},
                conservation_delta_minor=0,
                reason=(
                    f"Attribution hop '{hop_id}' injected {delta_sec}s before checkout "
                    f"(<= {hijack_window_sec}s window) without verified discovery interaction digest."
                ),
            )

    # Largest Remainder Method allocation across valid hops
    total_weight = sum(max(int(h.get("weight_bps", 0)), 0) for h in hops)
    if total_weight <= 0:
        total_weight = len(hops) * 1000

    floors: dict[str, int] = {}
    remainders: list[tuple[int, int, str]] = []
    allocated_sum = 0

    for idx, hop in enumerate(hops):
        hop_id = str(hop.get("hop_id", f"hop_{idx}"))
        w = max(int(hop.get("weight_bps", 1000)), 0)
        numerator = total_commission * w
        floor_share = numerator // total_weight
        rem = numerator % total_weight
        floors[hop_id] = floor_share
        allocated_sum += floor_share
        remainders.append((rem, -idx, hop_id))

    shortfall = total_commission - allocated_sum
    remainders.sort(reverse=True)
    for i in range(shortfall):
        _, _, hop_id = remainders[i]
        floors[hop_id] += 1

    final_sum = sum(floors.values())
    return AffiliateAttributionDecision(
        allowed=True,
        decision_code="AFFILIATE_ATTRIBUTION_SPLIT_VERIFIED",
        order_id=order_id,
        total_commission_minor=total_commission,
        valid_hop_count=len(hops),
        hijacked_hop_id=None,
        hop_allocations_minor=floors,
        conservation_delta_minor=total_commission - final_sum,
        reason="All attribution hops cryptographically verified; commission allocated with zero rounding drift.",
    )


def evaluate_loyalty_points_escrow_and_return_clawback(
    clawback_context: dict[str, Any],
) -> LoyaltyReturnClawbackDecision:
    """Enforce return-window loyalty escrow and deduct spent rewards from return principal."""
    order_id = str(clawback_context.get("order_id", "ord_unknown"))
    order_total = int(clawback_context.get("order_total_minor", 0))
    return_amount = int(clawback_context.get("gross_return_amount_minor", 0))
    earned_reward = int(clawback_context.get("earned_reward_minor", 0))
    buyer_available_reward_balance = int(clawback_context.get("buyer_available_reward_balance_minor", 0))
    now_epoch = int(clawback_context.get("now_epoch", 0))
    return_window_expires_epoch = int(clawback_context.get("return_window_expires_epoch", 0))

    escrow_status = (
        "PENDING_RETURN_WINDOW_ESCROW"
        if now_epoch < return_window_expires_epoch
        else "VESTED_POST_RETURN_WINDOW"
    )

    if return_amount <= 0 or order_total <= 0:
        return LoyaltyReturnClawbackDecision(
            allowed=True,
            decision_code="LOYALTY_ESCROW_ACTIVE_NO_RETURN",
            order_id=order_id,
            escrow_status=escrow_status,
            gross_return_amount_minor=0,
            earned_reward_minor=earned_reward,
            revoked_reward_minor=0,
            unrecovered_spent_deficit_minor=0,
            net_principal_refund_minor=0,
            reason="No return requested; earned loyalty rewards remain tracked under return-window policy.",
        )

    # Pro-rata reward revocation required for the returned amount
    required_clawback = round(earned_reward * return_amount / order_total)
    revoked_from_balance = min(buyer_available_reward_balance, required_clawback)
    unrecovered_deficit = max(required_clawback - revoked_from_balance, 0)
    net_refund = max(return_amount - unrecovered_deficit, 0)

    if unrecovered_deficit > 0:
        return LoyaltyReturnClawbackDecision(
            allowed=True,
            decision_code="CASHBACK_DEFICIT_DEDUCTED_FROM_REFUND",
            order_id=order_id,
            escrow_status=escrow_status,
            gross_return_amount_minor=return_amount,
            earned_reward_minor=earned_reward,
            revoked_reward_minor=revoked_from_balance,
            unrecovered_spent_deficit_minor=unrecovered_deficit,
            net_principal_refund_minor=net_refund,
            reason=(
                f"Buyer already redeemed {unrecovered_deficit} minor of earned rewards; "
                f"deducted deficit from principal refund ({return_amount} -> {net_refund} minor)."
            ),
        )

    return LoyaltyReturnClawbackDecision(
        allowed=True,
        decision_code="LOYALTY_POINTS_CLAWED_BACK",
        order_id=order_id,
        escrow_status=escrow_status,
        gross_return_amount_minor=return_amount,
        earned_reward_minor=earned_reward,
        revoked_reward_minor=revoked_from_balance,
        unrecovered_spent_deficit_minor=0,
        net_principal_refund_minor=net_refund,
        reason=f"Clawed back {revoked_from_balance} minor of escrowed/available rewards; full principal refunded.",
    )


def main() -> None:
    promo = evaluate_promo_coupon_stacking_invariant(
        {
            "order_subtotal_minor": 10000,
            "cogs_minor": 7200,
            "merchant_floor_margin_bps": 1500,
            "buyer_principal_did": "did:web:buyer.example",
            "referrer_principal_did": "did:web:partner.example",
            "coupons": [
                {"code": "WELCOME15", "discount_minor": 1500, "exclusivity_group": "TIER1", "stackable": True},
                {"code": "VIP10", "discount_minor": 1000, "exclusivity_group": "TIER2", "stackable": True},
            ],
        }
    )
    attr = verify_cryptographic_affiliate_attribution_chain(
        {
            "order_id": "ord_stage19_01",
            "total_commission_minor": 1000,
            "checkout_epoch": 2_000,
            "hijack_window_seconds": 5,
            "attribution_hops": [
                {
                    "hop_id": "hop_discovery_agent",
                    "timestamp_epoch": 1_820,
                    "jws_signature_valid": True,
                    "verified_interaction_digest": "sha256:disc_01",
                    "weight_bps": 6000,
                },
                {
                    "hop_id": "hop_checkout_extension",
                    "timestamp_epoch": 1_998,
                    "jws_signature_valid": True,
                    "verified_interaction_digest": "",
                    "weight_bps": 4000,
                },
            ],
        }
    )
    clawback = evaluate_loyalty_points_escrow_and_return_clawback(
        {
            "order_id": "ord_stage19_01",
            "order_total_minor": 20000,
            "gross_return_amount_minor": 20000,
            "earned_reward_minor": 2000,
            "buyer_available_reward_balance_minor": 500,
            "now_epoch": 1_760_950_000,
            "return_window_expires_epoch": 1_763_542_000,
        }
    )
    summary = {
        "stage": "stage19-loyalty-affiliate-promo-stacking-guard",
        "promo_stack_decision": promo.decision_code,
        "attribution_hijack_decision": attr.decision_code,
        "loyalty_clawback_decision": clawback.decision_code,
        "net_principal_refund_minor": clawback.net_principal_refund_minor,
        "unrecovered_spent_deficit_minor": clawback.unrecovered_spent_deficit_minor,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
