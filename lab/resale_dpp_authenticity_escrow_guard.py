"""Stage 21: EU ESPR Digital Product Passport (DPP) Provenance, C2C Authentication Escrow & Trade-In Anti-Bait-and-Switch Guard.

Implements three deterministic production guardrails for circular-economy Agentic Commerce
(high-value electronics, enterprise GPUs, luxury goods, and certified industrial spares):
1. EU ESPR Digital Product Passport Provenance (`verify_digital_product_passport_provenance`):
   - Validates GS1 Digital Link URI, OEM hardware cryptographic signature (`manufacturer_signature_valid`),
     repair/component Merkle history root (`repair_merkle_root_valid`), and stolen/recall registry status.
   - Blocks stolen or recalled items (`STOLEN_OR_RECALLED_DPP_ASSET_BLOCKED`) and counterfeit or
     tampered passports (`COUNTERFEIT_DPP_SIGNATURE_REJECTED`).
2. Two-Hop Authenticated C2C Escrow & Brand Royalty Split (`evaluate_authenticated_c2c_escrow_inspection_release`):
   - Releases buyer escrow only when an accredited authentication hub verifies `inspection_verdict == "AUTHENTIC"`
     and `hardware_serial_matches_dpp == True`.
   - Splits `escrow_gross_minor` via the Largest Remainder Method into `seller_net_minor`,
     `authentication_fee_minor`, and `brand_resale_royalty_minor` with zero rounding drift.
   - If counterfeit or serial-swapped, refunds 100% of buyer escrow and slashes the seller's bond
     (`COUNTERFEIT_INSPECTION_FAILED_BUYER_REFUNDED`).
3. Trade-In Residual Valuation & Anti-Bait-and-Switch Guard (`evaluate_trade_in_residual_value_and_grade_clawback`):
   - Locks remote-telemetry Trade-In quote (`initial_quote_minor`).
   - If post-receipt inspection downgrades value by `> 500 bps` (`5%`), blocks unilateral merchant
     card debit (`UNILATERAL_TRADE_IN_BAIT_AND_SWITCH_BLOCKED`) and requires explicit buyer re-consent
     or free prepaid return (`TRADE_IN_DOWNGRADE_RECONSENT_OR_FREE_RETURN`).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Any


@dataclass(frozen=True)
class DigitalProductPassportDecision:
    allowed: bool
    decision_code: str
    dpp_id: str
    gs1_digital_link: str
    oem_issuer_did: str
    manufacturer_signature_valid: bool
    repair_merkle_root_valid: bool
    reported_stolen_or_recalled: bool
    circularity_recycled_content_bps: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AuthenticatedEscrowReleaseDecision:
    escrow_released_to_seller: bool
    decision_code: str
    order_id: str
    inspection_verdict: str
    hardware_serial_matches_dpp: bool
    escrow_gross_minor: int
    seller_net_minor: int
    authentication_fee_minor: int
    brand_resale_royalty_minor: int
    buyer_refunded_minor: int
    seller_bond_slashed_minor: int
    conservation_delta_minor: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TradeInValuationDecision:
    allowed: bool
    decision_code: str
    trade_in_id: str
    initial_quote_minor: int
    reinspected_offer_minor: int
    downgrade_bps: int
    max_auto_accept_downgrade_bps: int
    unilateral_debit_attempted: bool
    buyer_reconsented: bool
    free_return_shipping_triggered: bool
    settled_trade_in_credit_minor: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def verify_digital_product_passport_provenance(
    dpp_bundle: dict[str, Any],
) -> DigitalProductPassportDecision:
    """Verify EU ESPR Digital Product Passport OEM signature, repair Merkle history, and recall/theft status."""
    dpp_id = str(dpp_bundle.get("dpp_id", "dpp_unknown"))
    gs1_link = str(dpp_bundle.get("gs1_digital_link", ""))
    oem_did = str(dpp_bundle.get("oem_issuer_did", ""))
    sig_valid = bool(dpp_bundle.get("manufacturer_signature_valid", False))
    merkle_valid = bool(dpp_bundle.get("repair_merkle_root_valid", True))
    stolen_or_recalled = bool(dpp_bundle.get("reported_stolen_or_recalled", False))
    recycled_bps = int(dpp_bundle.get("circularity_recycled_content_bps", 0))

    if stolen_or_recalled:
        return DigitalProductPassportDecision(
            allowed=False,
            decision_code="STOLEN_OR_RECALLED_DPP_ASSET_BLOCKED",
            dpp_id=dpp_id,
            gs1_digital_link=gs1_link,
            oem_issuer_did=oem_did,
            manufacturer_signature_valid=sig_valid,
            repair_merkle_root_valid=merkle_valid,
            reported_stolen_or_recalled=True,
            circularity_recycled_content_bps=recycled_bps,
            reason=f"DPP '{dpp_id}' is flagged in the stolen or safety-recalled hardware registry.",
        )

    if not sig_valid or not merkle_valid or not gs1_link.startswith("https://id.gs1.org/"):
        return DigitalProductPassportDecision(
            allowed=False,
            decision_code="COUNTERFEIT_DPP_SIGNATURE_REJECTED",
            dpp_id=dpp_id,
            gs1_digital_link=gs1_link,
            oem_issuer_did=oem_did,
            manufacturer_signature_valid=sig_valid,
            repair_merkle_root_valid=merkle_valid,
            reported_stolen_or_recalled=False,
            circularity_recycled_content_bps=recycled_bps,
            reason="DPP failed OEM cryptographic signature, GS1 Digital Link format, or repair Merkle history check.",
        )

    return DigitalProductPassportDecision(
        allowed=True,
        decision_code="DPP_PROVENANCE_AUTHENTIC_VERIFIED",
        dpp_id=dpp_id,
        gs1_digital_link=gs1_link,
        oem_issuer_did=oem_did,
        manufacturer_signature_valid=True,
        repair_merkle_root_valid=True,
        reported_stolen_or_recalled=False,
        circularity_recycled_content_bps=recycled_bps,
        reason="EU ESPR Digital Product Passport OEM provenance and repair lineage verified.",
    )


def evaluate_authenticated_c2c_escrow_inspection_release(
    escrow_context: dict[str, Any],
) -> AuthenticatedEscrowReleaseDecision:
    """Evaluate two-hop C2C authentication hub verdict and split escrow with OEM resale royalty."""
    order_id = str(escrow_context.get("order_id", "ord_c2c_unknown"))
    verdict = str(escrow_context.get("inspection_verdict", "COUNTERFEIT")).upper()
    serial_matches = bool(escrow_context.get("hardware_serial_matches_dpp", False))
    gross = int(escrow_context.get("escrow_gross_minor", 0))
    auth_fee_bps = int(escrow_context.get("authentication_fee_bps", 350))
    royalty_bps = int(escrow_context.get("brand_resale_royalty_bps", 250))
    seller_bond = int(escrow_context.get("seller_collateral_bond_minor", 0))

    if verdict != "AUTHENTIC" or not serial_matches:
        return AuthenticatedEscrowReleaseDecision(
            escrow_released_to_seller=False,
            decision_code="COUNTERFEIT_INSPECTION_FAILED_BUYER_REFUNDED",
            order_id=order_id,
            inspection_verdict=verdict,
            hardware_serial_matches_dpp=serial_matches,
            escrow_gross_minor=gross,
            seller_net_minor=0,
            authentication_fee_minor=0,
            brand_resale_royalty_minor=0,
            buyer_refunded_minor=gross,
            seller_bond_slashed_minor=seller_bond,
            conservation_delta_minor=0,
            reason="Physical authentication or chip serial match failed; 100% buyer escrow refunded and seller bond slashed.",
        )

    seller_bps = max(10_000 - auth_fee_bps - royalty_bps, 0)
    weights = [
        ("seller", seller_bps),
        ("auth_hub", auth_fee_bps),
        ("brand_royalty", royalty_bps),
    ]
    floors: dict[str, int] = {}
    remainders: list[tuple[int, int, str]] = []
    allocated = 0
    for idx, (k, w) in enumerate(weights):
        num = gross * w
        fl = num // 10_000
        rem = num % 10_000
        floors[k] = fl
        allocated += fl
        remainders.append((rem, -idx, k))

    shortfall = gross - allocated
    remainders.sort(reverse=True)
    for i in range(shortfall):
        _, _, k = remainders[i]
        floors[k] += 1

    seller_net = floors["seller"]
    auth_fee = floors["auth_hub"]
    royalty = floors["brand_royalty"]
    delta = gross - (seller_net + auth_fee + royalty)

    return AuthenticatedEscrowReleaseDecision(
        escrow_released_to_seller=True,
        decision_code="AUTHENTICATED_ESCROW_RELEASED_WITH_ROYALTY_SPLIT",
        order_id=order_id,
        inspection_verdict=verdict,
        hardware_serial_matches_dpp=True,
        escrow_gross_minor=gross,
        seller_net_minor=seller_net,
        authentication_fee_minor=auth_fee,
        brand_resale_royalty_minor=royalty,
        buyer_refunded_minor=0,
        seller_bond_slashed_minor=0,
        conservation_delta_minor=delta,
        reason="Authentication passed; escrow split across seller, lab hub, and brand royalty with zero cent drift.",
    )


def evaluate_trade_in_residual_value_and_grade_clawback(
    trade_in_context: dict[str, Any],
) -> TradeInValuationDecision:
    """Prevent unilateral post-receipt Trade-In price slashing ('bait-and-switch' downgrade)."""
    trade_in_id = str(trade_in_context.get("trade_in_id", "ti_unknown"))
    initial_quote = int(trade_in_context.get("initial_quote_minor", 0))
    reinspected_offer = int(trade_in_context.get("reinspected_offer_minor", initial_quote))
    max_auto_bps = int(trade_in_context.get("max_auto_accept_downgrade_bps", 500))
    unilateral_debit = bool(trade_in_context.get("unilateral_debit_attempted", False))
    buyer_reconsented = bool(trade_in_context.get("buyer_reconsented", False))

    downgrade_minor = max(initial_quote - reinspected_offer, 0)
    downgrade_bps = round(downgrade_minor * 10_000 / max(initial_quote, 1))

    if downgrade_bps > max_auto_bps and unilateral_debit:
        return TradeInValuationDecision(
            allowed=False,
            decision_code="UNILATERAL_TRADE_IN_BAIT_AND_SWITCH_BLOCKED",
            trade_in_id=trade_in_id,
            initial_quote_minor=initial_quote,
            reinspected_offer_minor=reinspected_offer,
            downgrade_bps=downgrade_bps,
            max_auto_accept_downgrade_bps=max_auto_bps,
            unilateral_debit_attempted=True,
            buyer_reconsented=buyer_reconsented,
            free_return_shipping_triggered=True,
            settled_trade_in_credit_minor=0,
            reason=(
                f"Post-receipt Trade-In downgrade ({downgrade_bps} bps > {max_auto_bps} bps) "
                "cannot be unilaterally debited without buyer re-consent."
            ),
        )

    if downgrade_bps > max_auto_bps and not buyer_reconsented:
        return TradeInValuationDecision(
            allowed=False,
            decision_code="TRADE_IN_DOWNGRADE_RECONSENT_OR_FREE_RETURN",
            trade_in_id=trade_in_id,
            initial_quote_minor=initial_quote,
            reinspected_offer_minor=reinspected_offer,
            downgrade_bps=downgrade_bps,
            max_auto_accept_downgrade_bps=max_auto_bps,
            unilateral_debit_attempted=False,
            buyer_reconsented=False,
            free_return_shipping_triggered=True,
            settled_trade_in_credit_minor=0,
            reason=(
                f"Trade-In offer reduced by {downgrade_bps} bps (> {max_auto_bps} bps); "
                "halted pending buyer re-consent or free prepaid device return."
            ),
        )

    return TradeInValuationDecision(
        allowed=True,
        decision_code="TRADE_IN_VALUATION_SETTLED",
        trade_in_id=trade_in_id,
        initial_quote_minor=initial_quote,
        reinspected_offer_minor=reinspected_offer,
        downgrade_bps=downgrade_bps,
        max_auto_accept_downgrade_bps=max_auto_bps,
        unilateral_debit_attempted=False,
        buyer_reconsented=buyer_reconsented,
        free_return_shipping_triggered=False,
        settled_trade_in_credit_minor=reinspected_offer,
        reason="Trade-In valuation within tolerance or explicitly re-consented by buyer.",
    )


def main() -> None:
    dpp = verify_digital_product_passport_provenance(
        {
            "dpp_id": "dpp_h100_nv_01",
            "gs1_digital_link": "https://id.gs1.org/01/09506000134352/21/SN-H100-8821",
            "oem_issuer_did": "did:web:nvidia.com:dpp",
            "manufacturer_signature_valid": True,
            "repair_merkle_root_valid": True,
            "reported_stolen_or_recalled": False,
            "circularity_recycled_content_bps": 3200,
        }
    )
    escrow = evaluate_authenticated_c2c_escrow_inspection_release(
        {
            "order_id": "ord_c2c_21_01",
            "inspection_verdict": "AUTHENTIC",
            "hardware_serial_matches_dpp": True,
            "escrow_gross_minor": 100000,
            "authentication_fee_bps": 350,
            "brand_resale_royalty_bps": 250,
            "seller_collateral_bond_minor": 10000,
        }
    )
    trade_in = evaluate_trade_in_residual_value_and_grade_clawback(
        {
            "trade_in_id": "ti_mac_studio_21",
            "initial_quote_minor": 120000,
            "reinspected_offer_minor": 90000,
            "max_auto_accept_downgrade_bps": 500,
            "unilateral_debit_attempted": True,
            "buyer_reconsented": False,
        }
    )
    summary = {
        "stage": "stage21-resale-dpp-authenticity-escrow-guard",
        "dpp_decision": dpp.decision_code,
        "c2c_escrow_decision": escrow.decision_code,
        "c2c_splits": {
            "seller_net_minor": escrow.seller_net_minor,
            "authentication_fee_minor": escrow.authentication_fee_minor,
            "brand_resale_royalty_minor": escrow.brand_resale_royalty_minor,
        },
        "trade_in_bait_switch_decision": trade_in.decision_code,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
