"""Cross-Border HS-Code DDP Landed Cost (De-Minimis / CBAM), Cold-Chain IoT Mean Kinetic Temperature (MKT) Escrow Claim & Scope 3 Low-Carbon Pareto Carrier Router (Stage 16).

Enforces three deterministic customs, physical IoT fulfillment, and Scope 3
sustainability invariants for autonomous global supply-chain agents:

1. HS-Code DDP Landed Cost, De-Minimis Structuring & Undervaluation Anti-Fraud Guard
   (`evaluate_hs_code_landed_cost_and_deminimis`):
   - Computes exact `CIF + Duty + Surtax + CBAM Carbon Levy + Import VAT (IOSS/VAT)`.
   - Enforces jurisdiction De-Minimis thresholds (`US $800`, `EU €150`, `UK £135`),
     blocking Split-Consignment / Structuring evasion
     (`CUSTOMS_SPLIT_CONSIGNMENT_EVASION_BLOCKED`) and undervaluation fraud where
     `declared_fob_minor < 0.70 * reference_fair_value_minor`
     (`CUSTOMS_UNDERVALUATION_FRAUD_BLOCKED`).

2. Cold-Chain IoT Arrhenius Mean Kinetic Temperature (MKT) Escrow Auto-Claim Guard
   (`evaluate_cold_chain_iot_telemetry_escrow`):
   - Computes Arrhenius Mean Kinetic Temperature (`MKT`) in Celsius and cumulative
     excursion duration outside `[min_temp_c, max_temp_c]` (e.g., `2°C - 8°C`).
   - Automatically freezes final seller payout and releases buyer escrow
     compensation when `excursion_minutes > max_excursion_minutes` (`15 min`) or
     `mkt_celsius > max_mkt_celsius` (`8.0°C`,
     `COLD_CHAIN_SLA_BREACH_ESCROW_CLAIMED`).

3. Scope 3 Carbon Budget & SLA Pareto-Optimal Multimodal Carrier Router
   (`optimize_carbon_pareto_carrier_route`):
   - Selects the lowest-carbon multimodal route (`gCO2e/ton-km`) among options
     satisfying customer SLA deadline (`transit_hours <= max_sla_hours`), cost ceiling,
     and Scope 3 carbon budget (`NO_CARRIER_MEETS_SLA_AND_CARBON_ENVELOPE`).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
import json
import math
from typing import Any


DE_MINIMIS_THRESHOLDS_MINOR: dict[str, int] = {
    "US": 80_000,   # US Section 321 / Type 86 ($800.00)
    "EU": 15_000,   # EU IOSS (€150.00)
    "UK": 13_500,   # UK HMRC (£135.00)
}


@dataclass(frozen=True)
class CustomsLandedCostDecision:
    allowed: bool
    decision_code: str
    destination_jurisdiction: str
    cif_minor: int
    duty_minor: int
    surtax_minor: int
    cbam_carbon_levy_minor: int
    import_vat_minor: int
    calculated_ddp_total_minor: int
    de_minimis_cap_minor: int
    undervaluation_ratio: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ColdChainEscrowDecision:
    sla_compliant: bool
    seller_payout_released: bool
    decision_code: str
    shipment_id: str
    mkt_celsius: str
    excursion_minutes: int
    escrow_total_minor: int
    buyer_compensation_minor: int
    seller_net_release_minor: int
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class CarbonParetoRouteDecision:
    route_found: bool
    decision_code: str
    selected_carrier_id: str
    selected_mode: str
    transit_hours: int
    cost_minor: int
    total_kg_co2e: str
    carbon_savings_vs_air_pct: str
    reasons: tuple[str, ...]


def _round_minor(val: Decimal) -> int:
    return int(val.to_integral_value(rounding=ROUND_HALF_UP))


def evaluate_hs_code_landed_cost_and_deminimis(
    customs_context: dict[str, Any],
) -> CustomsLandedCostDecision:
    """Compute CIF + Duty + Surtax + CBAM + VAT and block undervaluation or structuring."""
    reasons: list[str] = []

    jurisdiction = str(customs_context.get("destination_jurisdiction", "US")).upper()
    declared_fob = int(customs_context.get("declared_fob_minor", 0))
    ref_fair_value = int(customs_context.get("reference_fair_value_minor", declared_fob))
    freight_minor = int(customs_context.get("freight_minor", 0))
    insurance_minor = int(customs_context.get("insurance_minor", 0))

    duty_bps = int(customs_context.get("duty_rate_bps", 0))
    surtax_bps = int(customs_context.get("surtax_rate_bps", 0))
    vat_bps = int(customs_context.get("import_vat_rate_bps", 0))

    embedded_tco2e = Decimal(str(customs_context.get("embedded_emissions_tco2e", "0")))
    cbam_price_minor_per_ton = int(
        customs_context.get("cbam_price_per_ton_minor", 0)
    )

    claimed_de_minimis = bool(customs_context.get("claimed_de_minimis_exempt", False))
    consignee_24h_cumulative = int(
        customs_context.get("same_consignee_24h_cumulative_minor", declared_fob)
    )
    quoted_ddp_total = customs_context.get("quoted_ddp_total_minor")

    de_minimis_cap = int(
        customs_context.get(
            "de_minimis_cap_minor",
            DE_MINIMIS_THRESHOLDS_MINOR.get(jurisdiction, 15_000),
        )
    )

    if ref_fair_value > 0:
        valuation_ratio = Decimal(str(declared_fob)) / Decimal(str(ref_fair_value))
    else:
        valuation_ratio = Decimal("1.00")

    if valuation_ratio < Decimal("0.70"):
        reasons.append("CUSTOMS_UNDERVALUATION_FRAUD_BLOCKED")

    if claimed_de_minimis and (
        declared_fob > de_minimis_cap or consignee_24h_cumulative > de_minimis_cap
    ):
        reasons.append("CUSTOMS_SPLIT_CONSIGNMENT_EVASION_BLOCKED")

    cif = declared_fob + freight_minor + insurance_minor
    effective_exempt = (
        claimed_de_minimis
        and declared_fob <= de_minimis_cap
        and consignee_24h_cumulative <= de_minimis_cap
    )

    if effective_exempt:
        duty = 0
        surtax = 0
    else:
        duty = _round_minor(Decimal(str(cif)) * Decimal(str(duty_bps)) / Decimal("10000"))
        surtax = _round_minor(
            Decimal(str(cif)) * Decimal(str(surtax_bps)) / Decimal("10000")
        )

    cbam_levy = _round_minor(embedded_tco2e * Decimal(str(cbam_price_minor_per_ton)))
    taxable_vat_base = cif + duty + surtax + cbam_levy
    import_vat = _round_minor(
        Decimal(str(taxable_vat_base)) * Decimal(str(vat_bps)) / Decimal("10000")
    )
    calculated_ddp = cif + duty + surtax + cbam_levy + import_vat

    if quoted_ddp_total is not None and int(quoted_ddp_total) != calculated_ddp:
        reasons.append("DDP_LANDED_COST_CALCULATION_MISMATCH")

    allowed = len(reasons) == 0
    decision_code = "CUSTOMS_DDP_LANDED_COST_VERIFIED" if allowed else reasons[0]

    return CustomsLandedCostDecision(
        allowed=allowed,
        decision_code=decision_code,
        destination_jurisdiction=jurisdiction,
        cif_minor=cif,
        duty_minor=duty,
        surtax_minor=surtax,
        cbam_carbon_levy_minor=cbam_levy,
        import_vat_minor=import_vat,
        calculated_ddp_total_minor=calculated_ddp,
        de_minimis_cap_minor=de_minimis_cap,
        undervaluation_ratio=str(
            valuation_ratio.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        ),
        reasons=tuple(reasons),
    )


def evaluate_cold_chain_iot_telemetry_escrow(
    telemetry_bundle: dict[str, Any],
    *,
    activation_energy_over_r_kelvin: float = 10_000.0,
) -> ColdChainEscrowDecision:
    """Compute Arrhenius Mean Kinetic Temperature (MKT) and trigger escrow claim on breach."""
    reasons: list[str] = []

    shipment_id = str(telemetry_bundle.get("shipment_id", ""))
    readings_c = [float(t) for t in telemetry_bundle.get("temperature_readings_c", [])]
    sample_interval_min = int(telemetry_bundle.get("sample_interval_minutes", 5))
    min_temp_c = float(telemetry_bundle.get("min_allowed_temp_c", 2.0))
    max_temp_c = float(telemetry_bundle.get("max_allowed_temp_c", 8.0))
    max_mkt_c = float(telemetry_bundle.get("max_mkt_celsius", 8.0))
    max_excursion_min = int(telemetry_bundle.get("max_excursion_minutes", 15))
    escrow_total = int(telemetry_bundle.get("escrow_total_minor", 0))
    breach_compensation_bps = int(
        telemetry_bundle.get("breach_compensation_bps", 10_000)
    )

    if not readings_c:
        mkt_c = Decimal("0.00")
        excursion_minutes = 0
        reasons.append("MISSING_IOT_TELEMETRY_READINGS")
    else:
        boltzmann_terms = [
            math.exp(-activation_energy_over_r_kelvin / (t_c + 273.15))
            for t_c in readings_c
        ]
        mean_exp = sum(boltzmann_terms) / len(boltzmann_terms)
        mkt_kelvin = -activation_energy_over_r_kelvin / math.log(mean_exp)
        mkt_c = Decimal(str(mkt_kelvin - 273.15)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        excursion_samples = sum(
            1 for t_c in readings_c if (t_c < min_temp_c or t_c > max_temp_c)
        )
        excursion_minutes = excursion_samples * sample_interval_min

        if excursion_minutes > max_excursion_min or float(mkt_c) > max_mkt_c:
            reasons.append("COLD_CHAIN_SLA_BREACH_ESCROW_CLAIMED")

    sla_compliant = len(reasons) == 0
    if sla_compliant:
        buyer_comp = 0
        seller_release = escrow_total
        decision_code = "COLD_CHAIN_MKT_SLA_VERIFIED_ESCROW_RELEASED"
    else:
        buyer_comp = (escrow_total * breach_compensation_bps) // 10_000
        seller_release = escrow_total - buyer_comp
        decision_code = reasons[0]

    return ColdChainEscrowDecision(
        sla_compliant=sla_compliant,
        seller_payout_released=sla_compliant,
        decision_code=decision_code,
        shipment_id=shipment_id,
        mkt_celsius=str(mkt_c),
        excursion_minutes=excursion_minutes,
        escrow_total_minor=escrow_total,
        buyer_compensation_minor=buyer_comp,
        seller_net_release_minor=seller_release,
        reasons=tuple(reasons),
    )


def optimize_carbon_pareto_carrier_route(
    shipment_spec: dict[str, Any],
    carrier_options: list[dict[str, Any]],
) -> CarbonParetoRouteDecision:
    """Select the lowest-carbon multimodal route meeting SLA deadline and budget caps."""
    weight_tons = Decimal(str(shipment_spec.get("cargo_weight_tons", "1.0")))
    distance_km = Decimal(str(shipment_spec.get("distance_km", "1000")))
    max_sla_hours = int(shipment_spec.get("max_sla_hours", 72))
    max_budget_minor = int(shipment_spec.get("max_budget_minor", 100_000))
    max_carbon_kg = Decimal(str(shipment_spec.get("max_carbon_budget_kg_co2e", "1000")))

    ton_km = weight_tons * distance_km
    air_baseline_kg: Decimal | None = None
    feasible: list[tuple[Decimal, int, int, str, str]] = []

    for opt in carrier_options:
        cid = str(opt.get("carrier_id", ""))
        mode = str(opt.get("mode", "ROAD"))
        hours = int(opt.get("transit_hours", 999))
        cost_minor = int(opt.get("cost_minor", 0))
        g_co2e_per_ton_km = Decimal(str(opt.get("gco2e_per_ton_km", "500")))

        total_kg = (ton_km * g_co2e_per_ton_km) / Decimal("1000")
        if mode.upper() == "AIR_FREIGHT":
            if air_baseline_kg is None or total_kg > air_baseline_kg:
                air_baseline_kg = total_kg

        if (
            hours <= max_sla_hours
            and cost_minor <= max_budget_minor
            and total_kg <= max_carbon_kg
        ):
            feasible.append((total_kg, cost_minor, hours, cid, mode))

    if not feasible:
        return CarbonParetoRouteDecision(
            route_found=False,
            decision_code="NO_CARRIER_MEETS_SLA_AND_CARBON_ENVELOPE",
            selected_carrier_id="",
            selected_mode="NONE",
            transit_hours=0,
            cost_minor=0,
            total_kg_co2e="0.00",
            carbon_savings_vs_air_pct="0.00",
            reasons=("NO_CARRIER_MEETS_SLA_AND_CARBON_ENVELOPE",),
        )

    feasible.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
    best_kg, best_cost, best_hours, best_cid, best_mode = feasible[0]

    if air_baseline_kg is not None and air_baseline_kg > Decimal("0"):
        savings_pct = ((air_baseline_kg - best_kg) / air_baseline_kg) * Decimal("100")
    else:
        savings_pct = Decimal("0.00")

    return CarbonParetoRouteDecision(
        route_found=True,
        decision_code="SCOPE3_CARBON_PARETO_ROUTE_SELECTED",
        selected_carrier_id=best_cid,
        selected_mode=best_mode,
        transit_hours=best_hours,
        cost_minor=best_cost,
        total_kg_co2e=str(best_kg.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        carbon_savings_vs_air_pct=str(
            savings_pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        ),
        reasons=(),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Stage 16 HS-Code DDP Landed Cost, Cold-Chain MKT Escrow & Scope 3 Carbon Router."
    )
    parser.parse_args(argv)

    customs_res = evaluate_hs_code_landed_cost_and_deminimis(
        {
            "destination_jurisdiction": "EU",
            "declared_fob_minor": 12_000,
            "reference_fair_value_minor": 12_500,
            "freight_minor": 1_500,
            "insurance_minor": 200,
            "duty_rate_bps": 650,
            "surtax_rate_bps": 0,
            "import_vat_rate_bps": 2000,
            "embedded_emissions_tco2e": "1.20",
            "cbam_price_per_ton_minor": 8_500,
            "claimed_de_minimis_exempt": True,
            "same_consignee_24h_cumulative_minor": 42_000,  # Structuring > €150
        }
    )
    cold_res = evaluate_cold_chain_iot_telemetry_escrow(
        {
            "shipment_id": "shp_biologics_901",
            "temperature_readings_c": [4.0, 4.5, 5.0, 12.5, 13.0, 12.8, 11.9, 5.2],
            "sample_interval_minutes": 5,
            "min_allowed_temp_c": 2.0,
            "max_allowed_temp_c": 8.0,
            "max_mkt_celsius": 8.0,
            "max_excursion_minutes": 15,
            "escrow_total_minor": 250_000,
            "breach_compensation_bps": 10_000,
        }
    )
    route_res = optimize_carbon_pareto_carrier_route(
        shipment_spec={
            "cargo_weight_tons": "2.5",
            "distance_km": "1800",
            "max_sla_hours": 48,
            "max_budget_minor": 350_000,
            "max_carbon_budget_kg_co2e": "400.0",
        },
        carrier_options=[
            {"carrier_id": "car_air_01", "mode": "AIR_FREIGHT", "transit_hours": 14, "cost_minor": 320_000, "gco2e_per_ton_km": "620"},
            {"carrier_id": "car_rail_02", "mode": "EURASIA_HIGH_SPEED_RAIL", "transit_hours": 36, "cost_minor": 145_000, "gco2e_per_ton_km": "28"},
            {"carrier_id": "car_ev_03", "mode": "EV_GREEN_CORRIDOR", "transit_hours": 42, "cost_minor": 160_000, "gco2e_per_ton_km": "42"},
        ],
    )
    print(
        json.dumps(
            {
                "stage": "stage16-green-logistics-customs-sla-guard",
                "customs_structuring_decision": customs_res.decision_code,
                "calculated_ddp_total_minor": customs_res.calculated_ddp_total_minor,
                "cold_chain_decision": cold_res.decision_code,
                "cold_chain_mkt_celsius": cold_res.mkt_celsius,
                "cold_chain_buyer_compensation_minor": cold_res.buyer_compensation_minor,
                "pareto_selected_carrier": route_res.selected_carrier_id,
                "carbon_savings_vs_air_pct": route_res.carbon_savings_vs_air_pct,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
