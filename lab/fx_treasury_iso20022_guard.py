"""Cross-Border Real-Time FX Quote Lock, Multi-Currency Treasury Natural Netting Sweep & ISO 20022 `pacs.008` Clearing Compliance Guard (Stage 15).

Enforces three deterministic treasury and cross-border clearing invariants for
autonomous B2B/B2C agentic commerce:

1. Bounded FX Quote Lock & Volatility Collar Guard (`evaluate_fx_quote_lock_and_slippage`):
   - Enforces `quote_ttl_seconds <= 120` and `now_epoch <= quote_expires_at_epoch`
     (`FX_QUOTE_TTL_EXCEEDED_OR_EXPIRED`).
   - Enforces mid-market markup cap `<= max_spread_bps` (`FX_SPREAD_MARKUP_EXCEEDED`).
   - Evaluates intraday spot volatility `|live_spot - locked_rate| / locked_rate` against
     `collar_bps`: absorbs moderate spikes via the merchant spread buffer pool
     (`FX_SLIPPAGE_ABSORBED_BY_MERCHANT_BUFFER`) and triggers deterministic safe
     requote fallback when the collar + buffer is breached
     (`FX_VOLATILITY_COLLAR_BREACHED_REQUOTE_REQUIRED`).

2. Multi-Currency Natural Netting & Treasury Sweep Optimizer (`optimize_multicurrency_netting_sweep`):
   - Matches same-currency receivables and payables across `USD/EUR/GBP/JPY/SGD`
     sub-ledgers before sweeping only the net residual exposure (`Net Exposure`)
     at institutional wholesale FX spreads (`< 12 bps`), eliminating `250-300 bps`
     per-transaction retail double-conversion drag.

3. ISO 20022 `pacs.008` / SWIFT gpi `UETR` Wire Instruction Validator (`validate_iso20022_pacs008_instruction`):
   - Validates canonical UUIDv4 `UETR` end-to-end tracking reference
     (`ISO20022_INVALID_UETR_UUIDV4`), regulatory trade purpose code
     (`GDDS`/`SUPP`/`CORT`), charge bearer (`SHAR`/`DEBT`/`CRED`), and
     correspondent bank cutoff window (`ISO20022_CORRESPONDENT_CUTOFF_WINDOW_MISSED`).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
import json
import re
from typing import Any


UUIDV4_REGEX = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
ALLOWED_ISO20022_PURPOSES: frozenset[str] = frozenset(
    {"GDDS", "SUPP", "CORT", "INTC", "TREA"}
)
ALLOWED_CHARGE_BEARERS: frozenset[str] = frozenset({"SHAR", "DEBT", "CRED", "SLEV"})


@dataclass(frozen=True)
class FxQuoteLockDecision:
    allowed: bool
    buffer_absorbed: bool
    decision_code: str
    pair: str
    quote_ttl_seconds: int
    spread_markup_bps: int
    intraday_slippage_bps: int
    collar_bps: int
    merchant_buffer_bps: int
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class MulticurrencyNettingResult:
    decision_code: str
    currencies_processed: tuple[str, ...]
    gross_fx_volume_usd: str
    natural_netted_volume_usd: str
    net_fx_exposure_usd: str
    netting_efficiency_pct: str
    naive_retail_fx_cost_usd: str
    optimized_netted_fx_cost_usd: str
    fx_cost_savings_usd: str
    effective_blended_cost_bps: str


@dataclass(frozen=True)
class Iso20022Pacs008Decision:
    valid: bool
    decision_code: str
    uetr: str
    purpose_code: str
    charge_bearer: str
    currency: str
    instructed_amount_minor: int
    same_day_value_date_guaranteed: bool
    reasons: tuple[str, ...]


def _to_decimal(val: str | float | int | Decimal) -> Decimal:
    return Decimal(str(val))


def evaluate_fx_quote_lock_and_slippage(
    fx_quote_context: dict[str, Any],
    *,
    max_quote_ttl_seconds: int = 120,
    max_spread_bps: int = 50,
    collar_bps: int = 75,
) -> FxQuoteLockDecision:
    """Validate bounded FX quote lock TTL, spread markup, and intraday volatility collar."""
    reasons: list[str] = []

    pair = str(fx_quote_context.get("pair", "EUR/USD"))
    quote_created_epoch = int(fx_quote_context.get("quote_created_epoch", 0))
    quote_expires_epoch = int(fx_quote_context.get("quote_expires_at_epoch", 0))
    now_epoch = int(fx_quote_context.get("now_epoch", 0))

    mid_market_rate = _to_decimal(fx_quote_context.get("mid_market_rate", "1.0800"))
    locked_rate = _to_decimal(fx_quote_context.get("locked_rate", "1.0800"))
    live_spot_rate = _to_decimal(fx_quote_context.get("live_spot_rate", "1.0800"))
    merchant_buffer_bps = int(fx_quote_context.get("merchant_buffer_bps", 35))

    quote_ttl = quote_expires_epoch - quote_created_epoch
    if (
        quote_ttl <= 0
        or quote_ttl > max_quote_ttl_seconds
        or now_epoch < quote_created_epoch
        or now_epoch > quote_expires_epoch
    ):
        reasons.append("FX_QUOTE_TTL_EXCEEDED_OR_EXPIRED")

    spread_bps = int(
        (
            (abs(locked_rate - mid_market_rate) / mid_market_rate) * Decimal("10000")
        ).to_integral_value(rounding=ROUND_HALF_UP)
    )
    if spread_bps > max_spread_bps:
        reasons.append("FX_SPREAD_MARKUP_EXCEEDED")

    slippage_bps = int(
        (
            (abs(live_spot_rate - locked_rate) / locked_rate) * Decimal("10000")
        ).to_integral_value(rounding=ROUND_HALF_UP)
    )

    buffer_absorbed = False
    if not reasons:
        if slippage_bps <= collar_bps:
            decision_code = "FX_QUOTE_LOCK_WITHIN_COLLAR"
        elif slippage_bps <= collar_bps + merchant_buffer_bps:
            buffer_absorbed = True
            decision_code = "FX_SLIPPAGE_ABSORBED_BY_MERCHANT_BUFFER"
        else:
            reasons.append("FX_VOLATILITY_COLLAR_BREACHED_REQUOTE_REQUIRED")
            decision_code = "FX_VOLATILITY_COLLAR_BREACHED_REQUOTE_REQUIRED"
    else:
        decision_code = reasons[0]

    allowed = len(reasons) == 0
    return FxQuoteLockDecision(
        allowed=allowed,
        buffer_absorbed=buffer_absorbed,
        decision_code=decision_code,
        pair=pair,
        quote_ttl_seconds=quote_ttl,
        spread_markup_bps=spread_bps,
        intraday_slippage_bps=slippage_bps,
        collar_bps=collar_bps,
        merchant_buffer_bps=merchant_buffer_bps,
        reasons=tuple(reasons),
    )


def optimize_multicurrency_netting_sweep(
    ledger_positions: list[dict[str, Any]],
    *,
    retail_fx_spread_bps: int = 275,
    institutional_fx_spread_bps: int = 10,
) -> MulticurrencyNettingResult:
    """Compute multi-currency natural netting efficiency and wholesale sweep FX savings."""
    currencies: list[str] = []
    gross_fx_usd = Decimal("0")
    netted_internal_usd = Decimal("0")
    net_exposure_usd = Decimal("0")

    for row in ledger_positions:
        ccy = str(row.get("currency", "USD")).upper()
        currencies.append(ccy)
        receivables = _to_decimal(row.get("receivables_minor", 0)) / Decimal("100")
        payables = _to_decimal(row.get("payables_minor", 0)) / Decimal("100")
        usd_rate = _to_decimal(row.get("mid_usd_rate", "1.0000"))

        if ccy == "USD":
            continue

        gross_ccy_usd = (receivables + payables) * usd_rate
        matched_ccy_usd = (Decimal("2") * min(receivables, payables)) * usd_rate
        residual_ccy_usd = abs(receivables - payables) * usd_rate

        gross_fx_usd += gross_ccy_usd
        netted_internal_usd += matched_ccy_usd
        net_exposure_usd += residual_ccy_usd

    if gross_fx_usd > Decimal("0"):
        efficiency_pct = (netted_internal_usd / gross_fx_usd) * Decimal("100")
    else:
        efficiency_pct = Decimal("100.0")

    naive_cost = gross_fx_usd * (Decimal(str(retail_fx_spread_bps)) / Decimal("10000"))
    optimized_cost = net_exposure_usd * (
        Decimal(str(institutional_fx_spread_bps)) / Decimal("10000")
    )
    savings = naive_cost - optimized_cost

    if gross_fx_usd > Decimal("0"):
        blended_bps = (optimized_cost / gross_fx_usd) * Decimal("10000")
    else:
        blended_bps = Decimal("0.00")

    return MulticurrencyNettingResult(
        decision_code="MULTICURRENCY_NATURAL_NETTING_OPTIMIZED",
        currencies_processed=tuple(currencies),
        gross_fx_volume_usd=str(gross_fx_usd.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        natural_netted_volume_usd=str(
            netted_internal_usd.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        ),
        net_fx_exposure_usd=str(
            net_exposure_usd.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        ),
        netting_efficiency_pct=str(
            efficiency_pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        ),
        naive_retail_fx_cost_usd=str(
            naive_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        ),
        optimized_netted_fx_cost_usd=str(
            optimized_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        ),
        fx_cost_savings_usd=str(savings.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        effective_blended_cost_bps=str(
            blended_bps.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        ),
    )


def validate_iso20022_pacs008_instruction(
    pacs008_payload: dict[str, Any],
) -> Iso20022Pacs008Decision:
    """Validate an ISO 20022 `pacs.008` cross-border wire instruction and SWIFT gpi UETR."""
    reasons: list[str] = []

    uetr = str(pacs008_payload.get("uetr", "")).strip()
    purpose_code = str(pacs008_payload.get("purpose_code", "")).strip().upper()
    charge_bearer = str(pacs008_payload.get("charge_bearer", "")).strip().upper()
    currency = str(pacs008_payload.get("currency", "USD")).strip().upper()
    amount_minor = int(pacs008_payload.get("instructed_amount_minor", 0))
    submission_epoch = int(pacs008_payload.get("submission_epoch", 0))
    cutoff_epoch = int(pacs008_payload.get("correspondent_cutoff_epoch", 0))
    require_full_principal = bool(
        pacs008_payload.get("require_full_principal_delivery", False)
    )

    if not UUIDV4_REGEX.match(uetr):
        reasons.append("ISO20022_INVALID_UETR_UUIDV4")

    if purpose_code not in ALLOWED_ISO20022_PURPOSES:
        reasons.append("ISO20022_MISSING_OR_INVALID_PURPOSE_CODE")

    if charge_bearer not in ALLOWED_CHARGE_BEARERS:
        reasons.append("ISO20022_INVALID_CHARGE_BEARER")
    elif require_full_principal and charge_bearer != "DEBT":
        # In ISO 20022 pacs.008, DEBT = OUR (debtor pays all intermediary charges so creditor receives 100%)
        reasons.append("ISO20022_CHARGE_BEARER_VIOLATES_FULL_VALUE_DELIVERY")

    if amount_minor <= 0:
        reasons.append("ISO20022_NON_POSITIVE_INSTRUCTED_AMOUNT")

    same_day_guaranteed = submission_epoch <= cutoff_epoch
    if not same_day_guaranteed:
        reasons.append("ISO20022_CORRESPONDENT_CUTOFF_WINDOW_MISSED")

    valid = len(reasons) == 0
    decision_code = "ISO20022_PACS008_INSTRUCTION_VALID" if valid else reasons[0]

    return Iso20022Pacs008Decision(
        valid=valid,
        decision_code=decision_code,
        uetr=uetr,
        purpose_code=purpose_code,
        charge_bearer=charge_bearer,
        currency=currency,
        instructed_amount_minor=amount_minor,
        same_day_value_date_guaranteed=same_day_guaranteed,
        reasons=tuple(reasons),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Stage 15 FX Quote Lock, Multi-Currency Netting & ISO 20022 pacs.008 guard."
    )
    parser.parse_args(argv)

    fx_res = evaluate_fx_quote_lock_and_slippage(
        {
            "pair": "EUR/USD",
            "quote_created_epoch": 1_760_800_000,
            "quote_expires_at_epoch": 1_760_800_090,
            "now_epoch": 1_760_800_045,
            "mid_market_rate": "1.0850",
            "locked_rate": "1.0870",
            "live_spot_rate": "1.0975",  # 97 bps > 75 bps collar, absorbed by 35 bps buffer
            "merchant_buffer_bps": 35,
        }
    )
    netting_res = optimize_multicurrency_netting_sweep(
        [
            {"currency": "EUR", "receivables_minor": 45_000_000, "payables_minor": 41_000_000, "mid_usd_rate": "1.0850"},
            {"currency": "GBP", "receivables_minor": 28_000_000, "payables_minor": 30_000_000, "mid_usd_rate": "1.3050"},
            {"currency": "SGD", "receivables_minor": 19_000_000, "payables_minor": 18_500_000, "mid_usd_rate": "0.7620"},
        ]
    )
    iso_res = validate_iso20022_pacs008_instruction(
        {
            "uetr": "97ed4827-7b6f-4491-a06f-b548d5a7512d",
            "purpose_code": "GDDS",
            "charge_bearer": "DEBT",
            "currency": "EUR",
            "instructed_amount_minor": 4_000_000,
            "submission_epoch": 1_760_800_100,
            "correspondent_cutoff_epoch": 1_760_803_600,
            "require_full_principal_delivery": True,
        }
    )
    print(
        json.dumps(
            {
                "stage": "stage15-fx-treasury-iso20022-guard",
                "fx_quote_decision": fx_res.decision_code,
                "fx_buffer_absorbed": fx_res.buffer_absorbed,
                "netting_efficiency_pct": netting_res.netting_efficiency_pct,
                "effective_blended_cost_bps": netting_res.effective_blended_cost_bps,
                "fx_cost_savings_usd": netting_res.fx_cost_savings_usd,
                "iso20022_pacs008_valid": iso_res.valid,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
