"""Offline, zero-dependency Cross-Border Multi-Seller Settlement, Token-Margin FCB & Incoterms Guard.

Implements three deterministic AI-Native control-plane verifiers for Cross-Border Agentic Commerce
(Stage 3 — 2026-10-19), backed by Stripe Connect SPT (`2026-09-30.preview`), Stripe Billing
Token Metering (`docs.stripe.com/billing/token-billing.md`), Stripe MPP Tempo Sessions
(`2026-07-29.preview`), Google AP2 Section 7.4 Fiduciary Circuit Breaker (`PR #165`), and UCP
Catalog Feed (`PR #866`):

1. Connect Cross-Border Split & Reverse Refund Conservation (`verify_connect_split_and_refund_conservation`):
   - Validates Direct, Destination (`on_behalf_of`), and Separate Charges and Transfers split allocations,
     `application_fee_amount` bounds, FX quote TTL expiry (`now_epoch <= fx_quote_expires_at`), and
     FX slippage tolerance (`abs(live_fx_rate - locked_fx_rate) / locked_fx_rate <= max_fx_slippage_bps / 10000`).
   - Enforces strict partial-refund conservation: when refunding a split seller line item on Destination
     or Separate charges, `reverse_transfer=True` and proportional `refund_application_fee` are verified
     so the platform never absorbs an unrecovered negative balance.
2. Token Burn + Payment Rail Gross-Margin Envelope (`evaluate_token_margin_circuit_breaker`):
   - Combines Metronome-style LLM token metering (`input_tokens`, `output_tokens`, `cached_input_tokens`)
     with payment rail fees (`stripe_spt_card`, `x402_base_usdc`, `mpp_tempo_session` including sub-cent
     remainder forfeiture) and compares total variable cost against platform `gross_take_usd`.
   - Deterministically trips AP2 Fiduciary Circuit Breaker (`COST_ENVELOPE_EXCEEDED` -> `OPEN`) when
     `token_burn_usd + rail_fee_usd + forfeited_subcent_usd > max_allowed_cost_usd`.
3. Cross-Border Incoterms (`DDP` vs `DDU`/`DAP`) & HS Code Anti-Hallucination Guard (`verify_cross_border_incoterms_and_hs`):
   - Prevents an AI shopping agent from silently downgrading a buyer's required `DDP` (Delivered Duty Paid)
     mandate to `DDU`/`DAP` (Delivered Duty Unpaid / at Place) or substituting a lower-duty HS 6-digit prefix
     to artificially fit a buyer's `IntentMandate` budget ceiling.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_HALF_UP
import json
import re
import sys
from typing import Any, Literal

from lab.workload_arch_bench import audit_mpp_streaming_session, verify_connect_spt_routing


HS_CODE_RE = re.compile(r"^[0-9]{6,10}$")
SUPPORTED_INCOTERMS = frozenset({"DDP", "DAP", "DDU", "CIF", "FOB", "EXW"})
DUTY_PAID_INCOTERMS = frozenset({"DDP"})


# ---------------------------------------------------------------------------
# 1. Connect Cross-Border Split & Reverse Refund Conservation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SellerSplitAllocation:
    seller_account_id: str
    line_gross_minor: int
    transfer_amount_minor: int
    application_fee_minor: int
    settlement_currency: str
    locked_fx_rate: str
    live_fx_rate: str


@dataclass(frozen=True)
class ConnectSplitConservationResult:
    valid: bool
    reason: str
    total_buyer_charge_minor: int
    total_seller_transfers_minor: int
    total_application_fees_minor: int
    platform_net_retained_minor: int
    refund_platform_deficit_minor: int = 0


def verify_connect_split_and_refund_conservation(
    *,
    charge_type: str,
    seller_profile_owner: str,
    has_on_behalf_of: bool,
    stripe_account_header: str | None,
    connected_account_id: str,
    buyer_charge_minor: int,
    allocations: list[SellerSplitAllocation],
    now_epoch: int,
    fx_quote_expires_at: int,
    max_fx_slippage_bps: int = 50,
    refund_line_amount_minor: int = 0,
    refund_reverse_transfer: bool = True,
    refund_application_fee: bool = True,
) -> ConnectSplitConservationResult:
    """Verify Connect SPT routing, FX quote lock, split conservation, and partial-refund invariants."""
    routing = verify_connect_spt_routing(
        charge_type=charge_type,
        seller_profile_owner=seller_profile_owner,
        has_on_behalf_of=has_on_behalf_of,
        stripe_account_header=stripe_account_header,
        connected_account_id=connected_account_id,
    )
    if not routing.valid:
        return ConnectSplitConservationResult(
            False, routing.reason, buyer_charge_minor, 0, 0, 0
        )

    if not allocations or buyer_charge_minor <= 0:
        return ConnectSplitConservationResult(
            False, "empty_allocations_or_non_positive_charge", buyer_charge_minor, 0, 0, 0
        )

    if charge_type in {"direct", "destination"} and len(allocations) != 1:
        return ConnectSplitConservationResult(
            False,
            "multi_seller_split_requires_separate_charges_and_transfers",
            buyer_charge_minor,
            0,
            0,
            0,
        )

    if now_epoch > fx_quote_expires_at:
        return ConnectSplitConservationResult(
            False, "fx_quote_expired_requires_requote", buyer_charge_minor, 0, 0, 0
        )

    total_line_gross = 0
    total_transfers = 0
    total_fees = 0

    for alloc in allocations:
        if (
            alloc.line_gross_minor <= 0
            or alloc.transfer_amount_minor < 0
            or alloc.application_fee_minor < 0
        ):
            return ConnectSplitConservationResult(
                False, "negative_or_zero_allocation_component", buyer_charge_minor, 0, 0, 0
            )
        if alloc.transfer_amount_minor + alloc.application_fee_minor != alloc.line_gross_minor:
            return ConnectSplitConservationResult(
                False,
                "allocation_components_do_not_sum_to_line_gross",
                buyer_charge_minor,
                0,
                0,
                0,
            )

        locked_fx = Decimal(alloc.locked_fx_rate)
        live_fx = Decimal(alloc.live_fx_rate)
        if locked_fx <= Decimal("0") or live_fx <= Decimal("0"):
            return ConnectSplitConservationResult(
                False, "invalid_fx_rate", buyer_charge_minor, 0, 0, 0
            )
        slippage_bps = (abs(live_fx - locked_fx) / locked_fx) * Decimal("10000")
        if slippage_bps > Decimal(max_fx_slippage_bps):
            return ConnectSplitConservationResult(
                False,
                "fx_slippage_exceeds_locked_corridor",
                buyer_charge_minor,
                0,
                0,
                0,
            )

        total_line_gross += alloc.line_gross_minor
        total_transfers += alloc.transfer_amount_minor
        total_fees += alloc.application_fee_minor

    if total_line_gross != buyer_charge_minor:
        return ConnectSplitConservationResult(
            False,
            "split_line_gross_sum_mismatch_with_buyer_charge",
            buyer_charge_minor,
            total_transfers,
            total_fees,
            buyer_charge_minor - total_transfers,
        )

    # Partial or full refund conservation check
    if refund_line_amount_minor > 0:
        if refund_line_amount_minor > buyer_charge_minor:
            return ConnectSplitConservationResult(
                False,
                "refund_exceeds_original_buyer_charge",
                buyer_charge_minor,
                total_transfers,
                total_fees,
                total_fees,
            )
        if charge_type in {"destination", "separate_charges_and_transfers"} and not refund_reverse_transfer:
            # Platform refunds buyer 100% of refund_line_amount_minor while connected seller keeps transfer
            proportional_transfer = (
                refund_line_amount_minor * total_transfers
            ) // buyer_charge_minor
            return ConnectSplitConservationResult(
                False,
                "refund_without_reverse_transfer_creates_platform_deficit",
                buyer_charge_minor,
                total_transfers,
                total_fees,
                total_fees,
                refund_platform_deficit_minor=proportional_transfer,
            )
        if not refund_application_fee and total_fees > 0:
            return ConnectSplitConservationResult(
                False,
                "unaligned_application_fee_retention_on_refund",
                buyer_charge_minor,
                total_transfers,
                total_fees,
                total_fees,
            )

    return ConnectSplitConservationResult(
        True,
        "ok",
        buyer_charge_minor,
        total_transfers,
        total_fees,
        total_fees,
        refund_platform_deficit_minor=0,
    )


# ---------------------------------------------------------------------------
# 2. LLM Token Burn + Payment Rail Gross-Margin Circuit Breaker
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TokenMarginAuditResult:
    allowed: bool
    fcb_next_state: Literal["CLOSED", "OPEN"]
    tripped_condition: str | None
    reason: str
    gross_transaction_usd: str
    platform_gross_take_usd: str
    token_burn_usd: str
    rail_fee_usd: str
    forfeited_subcent_usd: str
    net_margin_usd: str


def evaluate_token_margin_circuit_breaker(
    *,
    gross_transaction_usd: str,
    platform_take_rate_bps: int,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
    input_price_per_million_usd: str = "2.50",
    output_price_per_million_usd: str = "10.00",
    cached_input_price_per_million_usd: str = "0.25",
    payment_rail: Literal["stripe_spt_card", "x402_base_usdc", "mpp_tempo_session"] = "stripe_spt_card",
    mpp_unit_price_usd: str = "0.000350",
    mpp_units_per_settlement_cycle: int = 200,
    mpp_total_units: int = 200,
    min_required_net_margin_usd: str = "0.000000",
) -> TokenMarginAuditResult:
    """Audit combined LLM token burn (`stripe-token-billing`) + payment rail fee against platform take."""
    gross_usd = Decimal(gross_transaction_usd)
    take_bps = Decimal(platform_take_rate_bps)
    gross_take = (gross_usd * take_bps) / Decimal("10000")

    in_cost = (Decimal(input_tokens) * Decimal(input_price_per_million_usd)) / Decimal("1000000")
    out_cost = (Decimal(output_tokens) * Decimal(output_price_per_million_usd)) / Decimal("1000000")
    cache_cost = (
        Decimal(cached_input_tokens) * Decimal(cached_input_price_per_million_usd)
    ) / Decimal("1000000")
    token_burn = in_cost + out_cost + cache_cost

    forfeited_subcent = Decimal("0")
    if payment_rail == "stripe_spt_card":
        if gross_usd < Decimal("0.50"):
            return TokenMarginAuditResult(
                False,
                "OPEN",
                "VALUE_THRESHOLD",
                "spt_card_below_0_50_usd_minimum_floor",
                f"{gross_usd:.6f}",
                f"{gross_take:.6f}",
                f"{token_burn:.6f}",
                "0.000000",
                "0.000000",
                "0.000000",
            )
        rail_fee = Decimal("0.30") + (gross_usd * Decimal("0.029"))
    elif payment_rail == "x402_base_usdc":
        if gross_usd < Decimal("0.01"):
            return TokenMarginAuditResult(
                False,
                "OPEN",
                "VALUE_THRESHOLD",
                "x402_below_0_01_usdc_minimum_floor",
                f"{gross_usd:.6f}",
                f"{gross_take:.6f}",
                f"{token_burn:.6f}",
                "0.000000",
                "0.000000",
                "0.000000",
            )
        rail_fee = Decimal("0.000200")  # Base L2 USDC settlement gas
    elif payment_rail == "mpp_tempo_session":
        mpp_audit = audit_mpp_streaming_session(
            unit_price_usd=mpp_unit_price_usd,
            units_per_settlement_cycle=mpp_units_per_settlement_cycle,
            total_units_consumed=mpp_total_units,
            deposit_usd=str(max(gross_usd, Decimal("1.000000"))),
        )
        if not mpp_audit.valid:
            return TokenMarginAuditResult(
                False,
                "OPEN",
                "VALUE_THRESHOLD",
                mpp_audit.reason,
                f"{gross_usd:.6f}",
                f"{gross_take:.6f}",
                f"{token_burn:.6f}",
                "0.000000",
                "0.000000",
                "0.000000",
            )
        forfeited_subcent = Decimal(mpp_audit.forfeited_subcent_usd)
        rail_fee = Decimal("0.000050")
    else:
        return TokenMarginAuditResult(
            False,
            "OPEN",
            "CUSTOM",
            "unsupported_payment_rail",
            f"{gross_usd:.6f}",
            f"{gross_take:.6f}",
            f"{token_burn:.6f}",
            "0.000000",
            "0.000000",
            "0.000000",
        )

    net_margin = gross_take - token_burn - rail_fee - forfeited_subcent
    min_margin = Decimal(min_required_net_margin_usd)

    if net_margin < min_margin:
        return TokenMarginAuditResult(
            False,
            "OPEN",
            "COST_ENVELOPE_EXCEEDED",
            "token_and_rail_burn_exceeds_platform_gross_take",
            f"{gross_usd:.6f}",
            f"{gross_take:.6f}",
            f"{token_burn:.6f}",
            f"{rail_fee:.6f}",
            f"{forfeited_subcent:.6f}",
            f"{net_margin:.6f}",
        )

    return TokenMarginAuditResult(
        True,
        "CLOSED",
        None,
        "ok",
        f"{gross_usd:.6f}",
        f"{gross_take:.6f}",
        f"{token_burn:.6f}",
        f"{rail_fee:.6f}",
        f"{forfeited_subcent:.6f}",
        f"{net_margin:.6f}",
    )


# ---------------------------------------------------------------------------
# 3. Cross-Border Incoterms (DDP vs DDU/DAP) & HS Code Anti-Hallucination Guard
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CrossBorderTradeGuardResult:
    allowed: bool
    reason: str
    landed_total_minor: int
    unpaid_import_liability_minor: int
    hs_chapter_match: bool


def verify_cross_border_incoterms_and_hs(
    *,
    buyer_mandate_max_landed_minor: int,
    buyer_requires_ddp: bool,
    proposed_incoterm: str,
    catalog_hs_code: str,
    proposed_hs_code: str,
    fob_merchandise_minor: int,
    freight_insurance_minor: int,
    estimated_duty_tax_minor: int,
    quoted_checkout_total_minor: int,
    de_minimis_threshold_minor: int = 0,
    de_minimis_exempt_allowed: bool = False,
) -> CrossBorderTradeGuardResult:
    """Block silent DDP->DDU/DAP downgrade and HS tariff code manipulation in cross-border checkout."""
    incoterm = proposed_incoterm.upper().strip()
    if incoterm not in SUPPORTED_INCOTERMS:
        return CrossBorderTradeGuardResult(False, "unsupported_incoterm", 0, 0, False)

    if not HS_CODE_RE.fullmatch(catalog_hs_code) or not HS_CODE_RE.fullmatch(proposed_hs_code):
        return CrossBorderTradeGuardResult(False, "malformed_hs_tariff_code", 0, 0, False)

    # First 6 digits of Harmonized System (WCO standard subheading) are immutable per catalog SKU
    hs_match = catalog_hs_code[:6] == proposed_hs_code[:6]
    if not hs_match:
        return CrossBorderTradeGuardResult(
            False,
            "hs_subheading_mismatch_with_catalog_authority",
            0,
            0,
            False,
        )

    duty_applicable = estimated_duty_tax_minor
    if de_minimis_exempt_allowed and fob_merchandise_minor <= de_minimis_threshold_minor:
        duty_applicable = 0

    true_landed_total = fob_merchandise_minor + freight_insurance_minor + duty_applicable

    if buyer_requires_ddp and incoterm not in DUTY_PAID_INCOTERMS:
        return CrossBorderTradeGuardResult(
            False,
            "incoterm_downgrade_from_ddp_forbidden",
            true_landed_total,
            duty_applicable,
            True,
        )

    if incoterm in DUTY_PAID_INCOTERMS and quoted_checkout_total_minor < true_landed_total:
        return CrossBorderTradeGuardResult(
            False,
            "ddp_checkout_quote_omits_duty_or_freight",
            true_landed_total,
            true_landed_total - quoted_checkout_total_minor,
            True,
        )

    if true_landed_total > buyer_mandate_max_landed_minor:
        return CrossBorderTradeGuardResult(
            False,
            "true_landed_cost_exceeds_buyer_mandate_ceiling",
            true_landed_total,
            duty_applicable if incoterm not in DUTY_PAID_INCOTERMS else 0,
            True,
        )

    return CrossBorderTradeGuardResult(
        True,
        "ok",
        true_landed_total,
        0 if incoterm in DUTY_PAID_INCOTERMS else duty_applicable,
        True,
    )


def run_demo() -> dict[str, Any]:
    """Run deterministic Stage 3 cross-border B2B settlement & FinOps guard demonstrations."""
    split_ok = verify_connect_split_and_refund_conservation(
        charge_type="separate_charges_and_transfers",
        seller_profile_owner="platform",
        has_on_behalf_of=False,
        stripe_account_header=None,
        connected_account_id="acct_seller_jp",
        buyer_charge_minor=50000,
        allocations=[
            SellerSplitAllocation("acct_seller_jp", 30000, 27000, 3000, "JPY", "150.00", "150.30"),
            SellerSplitAllocation("acct_seller_de", 20000, 18000, 2000, "EUR", "0.9200", "0.9215"),
        ],
        now_epoch=1760800000,
        fx_quote_expires_at=1760800900,
        max_fx_slippage_bps=50,
    )
    refund_deficit_blocked = verify_connect_split_and_refund_conservation(
        charge_type="destination",
        seller_profile_owner="connected_account",
        has_on_behalf_of=True,
        stripe_account_header=None,
        connected_account_id="acct_seller_jp",
        buyer_charge_minor=30000,
        allocations=[
            SellerSplitAllocation("acct_seller_jp", 30000, 27000, 3000, "JPY", "150.00", "150.10"),
        ],
        now_epoch=1760800000,
        fx_quote_expires_at=1760800900,
        refund_line_amount_minor=10000,
        refund_reverse_transfer=False,
    )
    margin_tripped = evaluate_token_margin_circuit_breaker(
        gross_transaction_usd="2.00",
        platform_take_rate_bps=1000,  # $0.20 gross take
        input_tokens=45000,
        output_tokens=8000,
        payment_rail="stripe_spt_card",  # $0.30 + $0.058 = $0.358 rail fee alone > $0.20 take
    )
    incoterm_downgrade_blocked = verify_cross_border_incoterms_and_hs(
        buyer_mandate_max_landed_minor=25000,
        buyer_requires_ddp=True,
        proposed_incoterm="DAP",
        catalog_hs_code="8471300100",
        proposed_hs_code="8471300100",
        fob_merchandise_minor=21000,
        freight_insurance_minor=2500,
        estimated_duty_tax_minor=3800,
        quoted_checkout_total_minor=23500,
    )
    return {
        "stage": "stage3-cross-border-b2b-guard",
        "split_conservation_ok": split_ok.valid,
        "refund_without_reverse_transfer_blocked": (
            not refund_deficit_blocked.valid
            and refund_deficit_blocked.reason == "refund_without_reverse_transfer_creates_platform_deficit"
            and refund_deficit_blocked.refund_platform_deficit_minor == 9000
        ),
        "token_margin_fcb_tripped": (
            not margin_tripped.allowed
            and margin_tripped.fcb_next_state == "OPEN"
            and margin_tripped.tripped_condition == "COST_ENVELOPE_EXCEEDED"
        ),
        "incoterm_downgrade_blocked": (
            not incoterm_downgrade_blocked.allowed
            and incoterm_downgrade_blocked.reason == "incoterm_downgrade_from_ddp_forbidden"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Stage 3 Cross-Border B2B Settlement, Token-Margin FCB & Incoterms Guard."
    )
    parser.parse_args(argv)
    summary = run_demo()
    print(json.dumps(summary, indent=2))
    return 0 if all(v is True for k, v in summary.items() if k != "stage") else 1


if __name__ == "__main__":
    sys.exit(main())
