"""Stage 11: Multi-Seller Commit-Reveal Vickrey Reverse Auction (RFQ), Cross-Border B2B VAT
Reverse-Charge / Tax Nexus Verification & Post-Purchase RMA Return Anti-Fraud / Anti-Restocking Trap Guard.

Implements deterministic verification for:
1. Cryptographic Commit-Reveal Sealed-Bid Second-Price (Vickrey) Reverse Auction (`verify_sealed_rfq_and_tax_nexus`):
   - Verifies each seller's revealed bid `(seller_id, rfq_id, all_in_price_minor, salt)` against
     its prior commitment hash `H_i = sha256("{seller_id}|{rfq_id}|{all_in_price_minor}|{salt}")`
     (blocks `RFQ_COMMIT_REVEAL_HASH_MISMATCH`).
   - Filters bids <= `reserve_price_minor` and awards the contract to the lowest bidder at the
     incentive-compatible Vickrey clearing price `min(second_lowest_valid_bid, reserve_price_minor)`.
   - Blocks post-award Checkout Bait-and-Switch surcharges (`BAIT_SWITCH_SURCHARGE_INJECTION`)
     if `checkout_merchandise_and_fees_minor > winning_bid_all_in_minor`.
2. Cross-Border B2B VAT Reverse-Charge & Tax Nexus Verification:
   - Blocks sellers without valid tax nexus/registration (`seller_tax_registration_valid == False`)
     from collecting tax (`UNREGISTERED_TAX_COLLECTION_BLOCKED`).
   - Blocks cross-border B2B VAT over-collection when `buyer_is_b2b and buyer_vat_verified and
     seller_country != buyer_country` where 0% Reverse-Charge applies (`INVALID_B2B_VAT_REVERSE_CHARGE_OVERCOLLECTION`).
3. Post-Purchase RMA Return Bilateral Guard (`verify_rma_return_and_restocking_guard`):
   - Buyer protection: blocks any restocking fee on defective/SNAD items (`ILLEGAL_SNAD_RESTOCKING_FEE_BLOCKED`)
     and blocks remorse restocking fees exceeding the UCP catalog-disclosed cap (`UNDISCLOSED_RESTOCKING_FEE_TRAP`).
   - Merchant protection: verifies returned hardware serial SHA-256 and package net-weight tolerance
     (`RMA_SERIAL_OR_WEIGHT_FRAUD_BLOCKED`).
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Any, Mapping, Sequence


def compute_rfq_bid_commitment(
    seller_id: str,
    rfq_id: str,
    all_in_price_minor: int,
    salt: str,
) -> str:
    """Compute the SHA-256 commitment hash for a sealed reverse-auction RFQ bid."""
    preimage = f"{seller_id}|{rfq_id}|{int(all_in_price_minor)}|{salt}".encode("utf-8")
    return hashlib.sha256(preimage).hexdigest()


@dataclass(frozen=True)
class SealedRfqAndTaxResult:
    allowed: bool
    decision_code: str
    rfq_id: str
    winning_seller_id: str | None
    winning_bid_all_in_minor: int | None
    vickrey_clearing_cap_minor: int | None
    checkout_pre_tax_minor: int
    tax_charged_minor: int
    expected_tax_minor: int
    commitments_verified_count: int
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RmaReturnGuardResult:
    refund_approved: bool
    decision_code: str
    rma_id: str
    return_reason: str
    paid_item_amount_minor: int
    proposed_restocking_fee_minor: int
    approved_refund_minor: int
    serial_match: bool
    weight_within_tolerance: bool
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def verify_sealed_rfq_and_tax_nexus(
    rfq_spec: Mapping[str, Any],
    bids: Sequence[Mapping[str, Any]],
    checkout_quote: Mapping[str, Any],
    tax_context: Mapping[str, Any],
) -> SealedRfqAndTaxResult:
    """Verify Commit-Reveal Vickrey RFQ clearing, anti-bait-and-switch checkout lock,
    and B2B VAT reverse-charge / tax nexus compliance.
    """
    reasons: list[str] = []
    rfq_id = str(rfq_spec.get("rfq_id") or "rfq_default")
    reserve_price_minor = int(rfq_spec.get("reserve_price_minor", 0))

    valid_bids: list[tuple[int, str]] = []
    commitments_verified = 0

    for bid in bids:
        seller_id = str(bid.get("seller_id") or "")
        all_in_minor = int(bid.get("all_in_price_minor", 0))
        salt = str(bid.get("salt") or "")
        committed_hash = str(bid.get("commitment_sha256") or "")
        expected_hash = compute_rfq_bid_commitment(seller_id, rfq_id, all_in_minor, salt)

        if committed_hash != expected_hash:
            reasons.append(
                f"RFQ_COMMIT_REVEAL_HASH_MISMATCH: seller {seller_id!r} revealed bid ({all_in_minor}) does not match commitment hash."
            )
            continue

        commitments_verified += 1
        if all_in_minor <= reserve_price_minor:
            valid_bids.append((all_in_minor, seller_id))

    valid_bids.sort(key=lambda item: (item[0], item[1]))

    winning_seller_id: str | None = None
    winning_bid_minor: int | None = None
    vickrey_cap_minor: int | None = None

    if not valid_bids:
        reasons.append(
            f"RFQ_NO_QUALIFYING_BIDS_BELOW_RESERVE: no valid revealed bid <= reserve_price_minor ({reserve_price_minor})."
        )
    else:
        winning_bid_minor, winning_seller_id = valid_bids[0]
        if len(valid_bids) >= 2:
            vickrey_cap_minor = min(valid_bids[1][0], reserve_price_minor)
        else:
            vickrey_cap_minor = reserve_price_minor

    checkout_seller = str(checkout_quote.get("seller_id") or "")
    checkout_pre_tax_minor = int(checkout_quote.get("pre_tax_all_in_minor", 0))

    if winning_seller_id is not None and checkout_seller != winning_seller_id:
        reasons.append(
            f"RFQ_WINNER_MISMATCH: checkout seller {checkout_seller!r} is not winning bidder {winning_seller_id!r}."
        )

    if winning_bid_minor is not None and checkout_pre_tax_minor > winning_bid_minor:
        reasons.append(
            f"BAIT_SWITCH_SURCHARGE_INJECTION: checkout pre-tax total ({checkout_pre_tax_minor}) exceeds locked RFQ bid ({winning_bid_minor})."
        )

    # Tax Nexus & Cross-Border B2B VAT Reverse-Charge verification
    seller_country = str(tax_context.get("seller_country") or "US").upper()
    buyer_country = str(tax_context.get("buyer_country") or "US").upper()
    buyer_is_b2b = bool(tax_context.get("buyer_is_b2b", False))
    buyer_vat_verified = bool(tax_context.get("buyer_vat_verified", False))
    seller_tax_reg_valid = bool(tax_context.get("seller_tax_registration_valid", True))
    statutory_rate_bps = int(tax_context.get("statutory_tax_rate_bps", 0))
    tax_charged_minor = int(checkout_quote.get("tax_charged_minor", 0))

    if tax_charged_minor > 0 and not seller_tax_reg_valid:
        reasons.append(
            "UNREGISTERED_TAX_COLLECTION_BLOCKED: seller lacks valid tax registration/nexus in buyer jurisdiction but charged tax."
        )

    is_cross_border_b2b_reverse_charge = (
        buyer_is_b2b and buyer_vat_verified and seller_country != buyer_country
    )
    if is_cross_border_b2b_reverse_charge:
        expected_tax_minor = 0
        if tax_charged_minor > 0:
            reasons.append(
                f"INVALID_B2B_VAT_REVERSE_CHARGE_OVERCOLLECTION: cross-border B2B with verified VAT ID requires 0% reverse-charge, but seller charged {tax_charged_minor}."
            )
    else:
        expected_tax_minor = (checkout_pre_tax_minor * statutory_rate_bps) // 10_000

    allowed = len(reasons) == 0
    decision_code = (
        "SEALED_RFQ_AND_TAX_VERIFIED"
        if allowed
        else reasons[0].split(":", 1)[0]
    )

    return SealedRfqAndTaxResult(
        allowed=allowed,
        decision_code=decision_code,
        rfq_id=rfq_id,
        winning_seller_id=winning_seller_id,
        winning_bid_all_in_minor=winning_bid_minor,
        vickrey_clearing_cap_minor=vickrey_cap_minor,
        checkout_pre_tax_minor=checkout_pre_tax_minor,
        tax_charged_minor=tax_charged_minor,
        expected_tax_minor=expected_tax_minor,
        commitments_verified_count=commitments_verified,
        reasons=reasons,
    )


def verify_rma_return_and_restocking_guard(
    rma_claim: Mapping[str, Any],
) -> RmaReturnGuardResult:
    """Verify post-purchase RMA return anti-fraud (serial + weight) and restocking-fee fairness."""
    reasons: list[str] = []
    rma_id = str(rma_claim.get("rma_id") or "rma_default")
    return_reason = str(rma_claim.get("return_reason") or "BUYER_REMORSE").upper()
    paid_amount = int(rma_claim.get("paid_item_amount_minor", 0))
    proposed_restocking_fee = int(rma_claim.get("proposed_restocking_fee_minor", 0))
    disclosed_max_restock_bps = int(rma_claim.get("ucp_disclosed_max_restocking_bps", 0))

    shipped_serial_sha = str(rma_claim.get("shipped_serial_sha256") or "")
    returned_serial_sha = str(rma_claim.get("returned_serial_sha256") or "")
    serial_match = bool(shipped_serial_sha) and shipped_serial_sha == returned_serial_sha

    shipped_weight_g = float(rma_claim.get("shipped_weight_grams", 0.0))
    returned_weight_g = float(rma_claim.get("returned_weight_grams", 0.0))
    max_weight_tol_g = float(rma_claim.get("max_weight_tolerance_grams", 25.0))
    weight_ok = abs(shipped_weight_g - returned_weight_g) <= max_weight_tol_g

    if not serial_match or not weight_ok:
        reasons.append(
            f"RMA_SERIAL_OR_WEIGHT_FRAUD_BLOCKED: serial_match={serial_match}, weight_delta_g={abs(shipped_weight_g - returned_weight_g):.1f} (tol={max_weight_tol_g:.1f}g)."
        )

    if return_reason == "DEFECTIVE_OR_SNAD":
        if proposed_restocking_fee > 0:
            reasons.append(
                f"ILLEGAL_SNAD_RESTOCKING_FEE_BLOCKED: merchant attempted to deduct restocking fee ({proposed_restocking_fee}) on defective/SNAD return."
            )
    else:
        max_allowed_fee = (paid_amount * disclosed_max_restock_bps) // 10_000
        if proposed_restocking_fee > max_allowed_fee:
            reasons.append(
                f"UNDISCLOSED_RESTOCKING_FEE_TRAP: proposed restocking fee ({proposed_restocking_fee}) exceeds UCP catalog-disclosed cap ({max_allowed_fee})."
            )

    refund_approved = len(reasons) == 0
    approved_refund = max(0, paid_amount - proposed_restocking_fee) if refund_approved else 0
    decision_code = (
        "RMA_REFUND_APPROVED"
        if refund_approved
        else reasons[0].split(":", 1)[0]
    )

    return RmaReturnGuardResult(
        refund_approved=refund_approved,
        decision_code=decision_code,
        rma_id=rma_id,
        return_reason=return_reason,
        paid_item_amount_minor=paid_amount,
        proposed_restocking_fee_minor=proposed_restocking_fee,
        approved_refund_minor=approved_refund,
        serial_match=serial_match,
        weight_within_tolerance=weight_ok,
        reasons=reasons,
    )


def run_demo_scenarios() -> list[dict[str, Any]]:
    """Run deterministic Stage 11 scenarios for Sealed RFQ, B2B VAT Reverse-Charge, and RMA Guard."""
    rfq_id = "rfq_enterprise_ssd_01"
    bids = [
        {
            "seller_id": "seller_alpha",
            "all_in_price_minor": 42_000,
            "salt": "salt_a_991",
            "commitment_sha256": compute_rfq_bid_commitment(
                "seller_alpha", rfq_id, 42_000, "salt_a_991"
            ),
        },
        {
            "seller_id": "seller_beta",
            "all_in_price_minor": 45_500,
            "salt": "salt_b_882",
            "commitment_sha256": compute_rfq_bid_commitment(
                "seller_beta", rfq_id, 45_500, "salt_b_882"
            ),
        },
    ]

    s1 = verify_sealed_rfq_and_tax_nexus(
        rfq_spec={"rfq_id": rfq_id, "reserve_price_minor": 50_000},
        bids=bids,
        checkout_quote={
            "seller_id": "seller_alpha",
            "pre_tax_all_in_minor": 42_000,
            "tax_charged_minor": 0,
        },
        tax_context={
            "seller_country": "DE",
            "buyer_country": "FR",
            "buyer_is_b2b": True,
            "buyer_vat_verified": True,
            "seller_tax_registration_valid": True,
            "statutory_tax_rate_bps": 2000,
        },
    )

    s2 = verify_sealed_rfq_and_tax_nexus(
        rfq_spec={"rfq_id": rfq_id, "reserve_price_minor": 50_000},
        bids=bids,
        checkout_quote={
            "seller_id": "seller_alpha",
            "pre_tax_all_in_minor": 44_900,  # +$29.00 bait-and-switch surcharge
            "tax_charged_minor": 8_980,      # illegal VAT collection on reverse-charge B2B
        },
        tax_context={
            "seller_country": "DE",
            "buyer_country": "FR",
            "buyer_is_b2b": True,
            "buyer_vat_verified": True,
            "seller_tax_registration_valid": True,
            "statutory_tax_rate_bps": 2000,
        },
    )

    s3 = verify_rma_return_and_restocking_guard(
        {
            "rma_id": "rma_snad_01",
            "return_reason": "DEFECTIVE_OR_SNAD",
            "paid_item_amount_minor": 42_000,
            "proposed_restocking_fee_minor": 6_300,
            "ucp_disclosed_max_restocking_bps": 1500,
            "shipped_serial_sha256": "sha256:sn_nvme_9901",
            "returned_serial_sha256": "sha256:sn_nvme_9901",
            "shipped_weight_grams": 540.0,
            "returned_weight_grams": 538.0,
        }
    )

    return [
        {"scenario_id": "S11_01_SEALED_RFQ_AND_B2B_REVERSE_CHARGE_OK", **s1.to_dict()},
        {"scenario_id": "S11_02_BAIT_SWITCH_AND_VAT_OVERCHARGE_BLOCKED", **s2.to_dict()},
        {"scenario_id": "S11_03_SNAD_ILLEGAL_RESTOCKING_FEE_BLOCKED", **s3.to_dict()},
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Stage 11 Sealed-Bid Vickrey RFQ, B2B VAT Reverse-Charge & RMA Guard demo."
    )
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args(argv)

    results = run_demo_scenarios()
    if args.json:
        print(json.dumps({"scenarios": results}, indent=2))
    else:
        print("=== Stage 11: Sealed-Bid Vickrey RFQ, B2B VAT Reverse-Charge & RMA Guard ===")
        for item in results:
            print(f"  [{item['scenario_id']}] decision={item['decision_code']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
