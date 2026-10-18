"""Stage 22: Cross-Protocol Agentic Real-Time Auction / Reverse RFQ Clearing, Consortium Group-Buying Tiered Escrow & Anti-Collusion / Earnest-Bond Slashing Guard.

Implements three deterministic multi-agent market-clearing invariants:
1. `evaluate_vickrey_reverse_auction_clearing`:
   - Supports both B2B Reverse RFQ (`direction="REVERSE"`) and scarce compute/ad-slot
     forward auctions (`direction="FORWARD"`),
   - Detects shill bidding and collusion rings (`shill_bid_self_dealing_detected` or
     `collusion_ring_score >= 0.85` -> `BID_RIGGING_OR_SHILL_COLLUSION_BLOCKED`),
   - Enforces anti-sniping soft-close extensions when bids arrive within `<= 15s`
     of `scheduled_close_epoch` (`+30s` -> `ANTI_SNIPING_SOFT_CLOSE_EXTENDED`),
   - Computes incentive-compatible Vickrey second-price clearing (`VICKREY_INCENTIVE_COMPATIBLE_CLEARED`).
2. `evaluate_consortium_group_buying_tier_escrow`:
   - Aggregates multi-buyer consortium demand against volume-tier schedules,
   - Automatically releases 100% of pre-authorized escrow holds if total quantity
     falls below MOQ at cutoff (`MOQ_NOT_MET_ESCROW_AUTO_RELEASED`),
   - Unlocks wholesale tier pricing and settles early-bird rebates with zero-drift
     conservation `sum(final_charges) + sum(rebates) == sum(initial_holds)`
     (`GROUP_TIER_UNLOCKED_REBATE_SETTLED`).
3. `verify_winner_commitment_earnest_bond_slash`:
   - Defends against griefing defaults where a winning agent locks inventory and
     fails to settle within TTL, slashing the winner's earnest bond
     (`WINNER_DEFAULT_EARNEST_BOND_SLASHED`) and awarding the runner-up bidder
     (`SECOND_PRICE_FALLBACK_AWARDED`).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Any


@dataclass(frozen=True)
class VickreyAuctionClearingResult:
    """Result of Vickrey forward/reverse auction clearing & anti-sniping/collusion check."""

    cleared: bool
    decision_code: str
    auction_id: str
    direction: str
    winning_bidder_id: str
    winning_bid_minor: int
    vickrey_clearing_price_minor: int
    soft_close_extended: bool
    extended_close_epoch: int
    collusion_blocked: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConsortiumGroupEscrowResult:
    """Result of multi-buyer consortium group-buying tiered escrow settlement."""

    settled: bool
    decision_code: str
    consortium_id: str
    total_committed_qty: int
    moq_required_qty: int
    unlocked_unit_price_minor: int
    total_initial_holds_minor: int
    total_final_charges_minor: int
    total_rebates_minor: int
    conservation_verified: bool
    participant_settlements: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EarnestBondSlashResult:
    """Result of winning bidder default earnest-bond slashing and runner-up fallback."""

    default_handled: bool
    decision_code: str
    fallback_status: str
    auction_id: str
    defaulted_winner_id: str
    slashed_bond_minor: int
    fallback_awarded_bidder_id: str
    fallback_clearing_price_minor: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_vickrey_reverse_auction_clearing(
    auction_bundle: dict[str, Any],
) -> VickreyAuctionClearingResult:
    """Evaluate Vickrey second-price auction/RFQ clearing with anti-sniping & collusion guards."""

    auction_id = str(auction_bundle.get("auction_id", ""))
    direction = str(auction_bundle.get("direction", "REVERSE")).upper()
    reserve_minor = int(auction_bundle.get("reserve_price_minor", 0))
    scheduled_close = int(auction_bundle.get("scheduled_close_epoch", 0))
    sniping_window_sec = int(auction_bundle.get("anti_sniping_window_seconds", 15))
    extension_sec = int(auction_bundle.get("soft_close_extension_seconds", 30))
    already_extended = bool(auction_bundle.get("soft_close_already_extended", False))
    shill_detected = bool(auction_bundle.get("shill_bid_self_dealing_detected", False))
    collusion_score = float(auction_bundle.get("collusion_ring_score", 0.0))
    max_collusion_score = float(auction_bundle.get("max_collusion_ring_score", 0.85))
    auctioneer_principal = str(auction_bundle.get("auctioneer_principal_id", "")).strip()

    raw_bids: list[dict[str, Any]] = list(auction_bundle.get("bids", []))

    for b in raw_bids:
        bidder_principal = str(b.get("principal_id", "")).strip()
        if auctioneer_principal and bidder_principal == auctioneer_principal:
            shill_detected = True

    if shill_detected or collusion_score >= max_collusion_score:
        return VickreyAuctionClearingResult(
            cleared=False,
            decision_code="BID_RIGGING_OR_SHILL_COLLUSION_BLOCKED",
            auction_id=auction_id,
            direction=direction,
            winning_bidder_id="",
            winning_bid_minor=0,
            vickrey_clearing_price_minor=0,
            soft_close_extended=False,
            extended_close_epoch=scheduled_close,
            collusion_blocked=True,
        )

    latest_bid_epoch = max(
        (int(b.get("bid_epoch", 0)) for b in raw_bids),
        default=0,
    )
    if (
        scheduled_close > 0
        and 0 <= (scheduled_close - latest_bid_epoch) <= sniping_window_sec
        and not already_extended
    ):
        return VickreyAuctionClearingResult(
            cleared=False,
            decision_code="ANTI_SNIPING_SOFT_CLOSE_EXTENDED",
            auction_id=auction_id,
            direction=direction,
            winning_bidder_id="",
            winning_bid_minor=0,
            vickrey_clearing_price_minor=0,
            soft_close_extended=True,
            extended_close_epoch=scheduled_close + extension_sec,
            collusion_blocked=False,
        )

    if direction == "REVERSE":
        valid_bids = [
            b
            for b in raw_bids
            if 0 < int(b.get("bid_amount_minor", 0)) <= reserve_minor
        ]
        valid_bids.sort(key=lambda x: (int(x["bid_amount_minor"]), int(x.get("bid_epoch", 0))))
        if not valid_bids:
            return VickreyAuctionClearingResult(
                cleared=False,
                decision_code="NO_QUALIFYING_BIDS_WITHIN_RESERVE",
                auction_id=auction_id,
                direction=direction,
                winning_bidder_id="",
                winning_bid_minor=0,
                vickrey_clearing_price_minor=0,
                soft_close_extended=False,
                extended_close_epoch=scheduled_close,
                collusion_blocked=False,
            )
        winner = valid_bids[0]
        win_amt = int(winner["bid_amount_minor"])
        second_amt = (
            int(valid_bids[1]["bid_amount_minor"]) if len(valid_bids) >= 2 else reserve_minor
        )
        clearing_price = min(second_amt, reserve_minor)
    else:
        valid_bids = [
            b
            for b in raw_bids
            if int(b.get("bid_amount_minor", 0)) >= reserve_minor
        ]
        valid_bids.sort(
            key=lambda x: (-int(x["bid_amount_minor"]), int(x.get("bid_epoch", 0)))
        )
        if not valid_bids:
            return VickreyAuctionClearingResult(
                cleared=False,
                decision_code="NO_QUALIFYING_BIDS_WITHIN_RESERVE",
                auction_id=auction_id,
                direction=direction,
                winning_bidder_id="",
                winning_bid_minor=0,
                vickrey_clearing_price_minor=0,
                soft_close_extended=False,
                extended_close_epoch=scheduled_close,
                collusion_blocked=False,
            )
        winner = valid_bids[0]
        win_amt = int(winner["bid_amount_minor"])
        second_amt = (
            int(valid_bids[1]["bid_amount_minor"]) if len(valid_bids) >= 2 else reserve_minor
        )
        clearing_price = max(second_amt, reserve_minor)

    return VickreyAuctionClearingResult(
        cleared=True,
        decision_code="VICKREY_INCENTIVE_COMPATIBLE_CLEARED",
        auction_id=auction_id,
        direction=direction,
        winning_bidder_id=str(winner.get("bidder_id", "")),
        winning_bid_minor=win_amt,
        vickrey_clearing_price_minor=clearing_price,
        soft_close_extended=already_extended,
        extended_close_epoch=scheduled_close,
        collusion_blocked=False,
    )


def evaluate_consortium_group_buying_tier_escrow(
    consortium_bundle: dict[str, Any],
) -> ConsortiumGroupEscrowResult:
    """Evaluate multi-buyer consortium group-buying tiered pricing and escrow conservation."""

    consortium_id = str(consortium_bundle.get("consortium_id", ""))
    moq_qty = max(1, int(consortium_bundle.get("moq_required_qty", 1)))
    base_unit_price = max(1, int(consortium_bundle.get("base_unit_price_minor", 1)))
    participants: list[dict[str, Any]] = list(consortium_bundle.get("participants", []))
    tiers: list[dict[str, Any]] = list(consortium_bundle.get("volume_tiers", []))

    total_qty = sum(max(0, int(p.get("quantity", 0))) for p in participants)
    total_holds = sum(max(0, int(p.get("initial_hold_minor", 0))) for p in participants)

    if total_qty < moq_qty:
        settlements = [
            {
                "buyer_id": str(p.get("buyer_id", "")),
                "quantity": int(p.get("quantity", 0)),
                "initial_hold_minor": int(p.get("initial_hold_minor", 0)),
                "final_charge_minor": 0,
                "rebate_minor": int(p.get("initial_hold_minor", 0)),
            }
            for p in participants
        ]
        return ConsortiumGroupEscrowResult(
            settled=False,
            decision_code="MOQ_NOT_MET_ESCROW_AUTO_RELEASED",
            consortium_id=consortium_id,
            total_committed_qty=total_qty,
            moq_required_qty=moq_qty,
            unlocked_unit_price_minor=base_unit_price,
            total_initial_holds_minor=total_holds,
            total_final_charges_minor=0,
            total_rebates_minor=total_holds,
            conservation_verified=True,
            participant_settlements=settlements,
        )

    unlocked_price = base_unit_price
    for t in sorted(tiers, key=lambda x: int(x.get("min_qty", 0))):
        if total_qty >= int(t.get("min_qty", 0)):
            unlocked_price = min(unlocked_price, int(t.get("unit_price_minor", base_unit_price)))

    settlements = []
    total_final = 0
    total_rebates = 0
    insufficient_hold = False

    for p in participants:
        qty = max(0, int(p.get("quantity", 0)))
        hold = max(0, int(p.get("initial_hold_minor", 0)))
        charge = qty * unlocked_price
        if hold < charge:
            insufficient_hold = True
        rebate = max(0, hold - charge)
        total_final += charge
        total_rebates += rebate
        settlements.append(
            {
                "buyer_id": str(p.get("buyer_id", "")),
                "quantity": qty,
                "initial_hold_minor": hold,
                "final_charge_minor": charge,
                "rebate_minor": rebate,
            }
        )

    conservation_ok = not insufficient_hold and (total_final + total_rebates == total_holds)
    if not conservation_ok:
        return ConsortiumGroupEscrowResult(
            settled=False,
            decision_code="CONSORTIUM_ESCROW_HOLD_DEFICIT_BLOCKED",
            consortium_id=consortium_id,
            total_committed_qty=total_qty,
            moq_required_qty=moq_qty,
            unlocked_unit_price_minor=unlocked_price,
            total_initial_holds_minor=total_holds,
            total_final_charges_minor=total_final,
            total_rebates_minor=total_rebates,
            conservation_verified=False,
            participant_settlements=settlements,
        )

    return ConsortiumGroupEscrowResult(
        settled=True,
        decision_code="GROUP_TIER_UNLOCKED_REBATE_SETTLED",
        consortium_id=consortium_id,
        total_committed_qty=total_qty,
        moq_required_qty=moq_qty,
        unlocked_unit_price_minor=unlocked_price,
        total_initial_holds_minor=total_holds,
        total_final_charges_minor=total_final,
        total_rebates_minor=total_rebates,
        conservation_verified=True,
        participant_settlements=settlements,
    )


def verify_winner_commitment_earnest_bond_slash(
    default_context: dict[str, Any],
) -> EarnestBondSlashResult:
    """Slash earnest bond on winning bidder griefing default and award runner-up."""

    auction_id = str(default_context.get("auction_id", ""))
    winner_id = str(default_context.get("winner_bidder_id", ""))
    settled_in_ttl = bool(default_context.get("winner_settled_within_ttl", False))
    earnest_bond = max(0, int(default_context.get("winner_earnest_bond_minor", 0)))
    runner_up_id = str(default_context.get("runner_up_bidder_id", "")).strip()
    fallback_price = max(0, int(default_context.get("fallback_clearing_price_minor", 0)))

    if settled_in_ttl:
        return EarnestBondSlashResult(
            default_handled=False,
            decision_code="WINNER_COMMITMENT_SETTLED_ON_TIME",
            fallback_status="PRIMARY_WINNER_SETTLED",
            auction_id=auction_id,
            defaulted_winner_id="",
            slashed_bond_minor=0,
            fallback_awarded_bidder_id=winner_id,
            fallback_clearing_price_minor=fallback_price,
        )

    fb_status = (
        "SECOND_PRICE_FALLBACK_AWARDED"
        if runner_up_id
        else "NO_RUNNER_UP_AUCTION_REOPENED"
    )
    return EarnestBondSlashResult(
        default_handled=True,
        decision_code="WINNER_DEFAULT_EARNEST_BOND_SLASHED",
        fallback_status=fb_status,
        auction_id=auction_id,
        defaulted_winner_id=winner_id,
        slashed_bond_minor=earnest_bond,
        fallback_awarded_bidder_id=runner_up_id,
        fallback_clearing_price_minor=fallback_price if runner_up_id else 0,
    )


def main() -> int:
    vickrey_res = evaluate_vickrey_reverse_auction_clearing(
        {
            "auction_id": "rfq_vickrey_22",
            "direction": "REVERSE",
            "reserve_price_minor": 150_000,
            "scheduled_close_epoch": 5_000,
            "anti_sniping_window_seconds": 15,
            "soft_close_extension_seconds": 30,
            "soft_close_already_extended": False,
            "shill_bid_self_dealing_detected": False,
            "collusion_ring_score": 0.12,
            "bids": [
                {"bidder_id": "seller_alpha", "principal_id": "did:web:alpha", "bid_amount_minor": 118_000, "bid_epoch": 4_900},
                {"bidder_id": "seller_beta", "principal_id": "did:web:beta", "bid_amount_minor": 124_500, "bid_epoch": 4_920},
                {"bidder_id": "seller_gamma", "principal_id": "did:web:gamma", "bid_amount_minor": 139_000, "bid_epoch": 4_940},
            ],
        }
    )
    consortium_res = evaluate_consortium_group_buying_tier_escrow(
        {
            "consortium_id": "grp_22",
            "moq_required_qty": 100,
            "base_unit_price_minor": 1_000,
            "volume_tiers": [
                {"min_qty": 50, "unit_price_minor": 900},
                {"min_qty": 100, "unit_price_minor": 780},
            ],
            "participants": [
                {"buyer_id": "buyer_a", "quantity": 60, "initial_hold_minor": 60_000},
                {"buyer_id": "buyer_b", "quantity": 50, "initial_hold_minor": 50_000},
            ],
        }
    )
    slash_res = verify_winner_commitment_earnest_bond_slash(
        {
            "auction_id": "rfq_vickrey_22",
            "winner_bidder_id": "seller_malicious",
            "winner_settled_within_ttl": False,
            "winner_earnest_bond_minor": 15_000,
            "runner_up_bidder_id": "seller_alpha",
            "fallback_clearing_price_minor": 124_500,
        }
    )
    print(
        json.dumps(
            {
                "stage": "stage22-agentic-auction-consortium-clearing-guard",
                "vickrey_decision": vickrey_res.decision_code,
                "vickrey_winner": vickrey_res.winning_bidder_id,
                "vickrey_clearing_price_minor": vickrey_res.vickrey_clearing_price_minor,
                "consortium_decision": consortium_res.decision_code,
                "consortium_rebates_minor": consortium_res.total_rebates_minor,
                "slash_decision": slash_res.decision_code,
                "fallback_status": slash_res.fallback_status,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
