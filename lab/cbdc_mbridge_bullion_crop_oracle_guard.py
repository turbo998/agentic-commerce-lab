"""Stage 33: Wholesale CBDC mBridge PvP Settlement, LBMA Allocated Bullion Bar Audit & Dual-Satellite NDVI Crop Insurance Escrow Guard.

Implements deterministic AI-Native settlement guardrails for:
1. Multi-CBDC Bridge (mBridge) cross-border wholesale Payment-versus-Payment (PvP) atomic settlement,
   asymmetric HTLC timelock ordering, capital-account FX declaration verification, and corridor rate
   band enforcement (`evaluate_mbridge_wholesale_cbdc_pvp_settlement`).
2. London Bullion Market Association (LBMA) Good Delivery allocated gold bar serial audit,
   unallocated-paper-gold substitution blocking, and ultrasonic/assay fineness weight true-up
   (`evaluate_lbma_allocated_bullion_bar_audit`).
3. Parametric Agricultural Crop Insurance dual-satellite (Sentinel-2 + MODIS NDVI) and ground
   weather-station quorum verification (`evaluate_parametric_crop_ndvi_weather_escrow`).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MBridgeWholesalePvPResult:
    pvp_trade_id: str
    corridor: str
    admitted: bool
    decision_code: str
    source_cbdc_notional_minor: int
    target_cbdc_notional_minor: int
    fx_corridor_deviation_bps: int
    initiator_htlc_timelock_sec: int
    responder_htlc_timelock_sec: int
    atomic_pvp_settled: bool


@dataclass(frozen=True)
class LBMABullionBarAuditResult:
    vault_receipt_id: str
    bar_serial_number: str
    admitted: bool
    decision_code: str
    fine_troy_ounces_milli: int
    ultrasonic_fineness_permille: float
    settled_bullion_value_minor: int
    escrow_refund_to_buyer_minor: int
    conservation_delta_minor: int


@dataclass(frozen=True)
class ParametricCropNDVIEscrowResult:
    policy_id: str
    admitted: bool
    decision_code: str
    sentinel2_ndvi_Milli: int
    modis_ndvi_milli: int
    sensor_divergence_milli: int
    ground_rainfall_mm: int
    payout_tier_bps: int
    indemnity_payout_minor: int
    insurer_retained_escrow_minor: int
    conservation_delta_minor: int


def evaluate_mbridge_wholesale_cbdc_pvp_settlement(
    *,
    pvp_trade_id: str,
    corridor: str,  # e.g., "e-CNY/e-HKD", "e-THB/m-AED"
    source_cbdc_notional_minor: int,
    target_cbdc_notional_minor: int,
    agreed_fx_rate_scaled: int,  # scaled by 10_000
    central_bank_mid_rate_scaled: int,
    max_fx_corridor_band_bps: int,
    initiator_htlc_timelock_sec: int,
    responder_htlc_timelock_sec: int,
    min_htlc_safety_margin_sec: int,
    safe_capital_account_declaration_signed: bool,
    commercial_bank_reserve_locked: bool,
) -> MBridgeWholesalePvPResult:
    """Verify mBridge wholesale CBDC atomic PvP HTLC timelock safety, capital-account compliance, and FX band."""
    fx_deviation_bps = (
        abs(agreed_fx_rate_scaled - central_bank_mid_rate_scaled) * 10000
        // max(1, central_bank_mid_rate_scaled)
    )

    if not safe_capital_account_declaration_signed or not commercial_bank_reserve_locked:
        return MBridgeWholesalePvPResult(
            pvp_trade_id=pvp_trade_id,
            corridor=corridor,
            admitted=False,
            decision_code="MBRIDGE_CAPITAL_ACCOUNT_OR_RESERVE_LOCK_MISSING_BLOCKED",
            source_cbdc_notional_minor=source_cbdc_notional_minor,
            target_cbdc_notional_minor=target_cbdc_notional_minor,
            fx_corridor_deviation_bps=fx_deviation_bps,
            initiator_htlc_timelock_sec=initiator_htlc_timelock_sec,
            responder_htlc_timelock_sec=responder_htlc_timelock_sec,
            atomic_pvp_settled=False,
        )

    if initiator_htlc_timelock_sec - responder_htlc_timelock_sec < min_htlc_safety_margin_sec:
        return MBridgeWholesalePvPResult(
            pvp_trade_id=pvp_trade_id,
            corridor=corridor,
            admitted=False,
            decision_code="MBRIDGE_HTLC_TIMELOCK_INVERSION_HERSTATT_RISK_BLOCKED",
            source_cbdc_notional_minor=source_cbdc_notional_minor,
            target_cbdc_notional_minor=target_cbdc_notional_minor,
            fx_corridor_deviation_bps=fx_deviation_bps,
            initiator_htlc_timelock_sec=initiator_htlc_timelock_sec,
            responder_htlc_timelock_sec=responder_htlc_timelock_sec,
            atomic_pvp_settled=False,
        )

    if fx_deviation_bps > max_fx_corridor_band_bps:
        return MBridgeWholesalePvPResult(
            pvp_trade_id=pvp_trade_id,
            corridor=corridor,
            admitted=False,
            decision_code="MBRIDGE_FX_CORRIDOR_BAND_EXCEEDED_BLOCKED",
            source_cbdc_notional_minor=source_cbdc_notional_minor,
            target_cbdc_notional_minor=target_cbdc_notional_minor,
            fx_corridor_deviation_bps=fx_deviation_bps,
            initiator_htlc_timelock_sec=initiator_htlc_timelock_sec,
            responder_htlc_timelock_sec=responder_htlc_timelock_sec,
            atomic_pvp_settled=False,
        )

    return MBridgeWholesalePvPResult(
        pvp_trade_id=pvp_trade_id,
        corridor=corridor,
        admitted=True,
        decision_code="MBRIDGE_WHOLESALE_CBDC_ATOMIC_PVP_SETTLED",
        source_cbdc_notional_minor=source_cbdc_notional_minor,
        target_cbdc_notional_minor=target_cbdc_notional_minor,
        fx_corridor_deviation_bps=fx_deviation_bps,
        initiator_htlc_timelock_sec=initiator_htlc_timelock_sec,
        responder_htlc_timelock_sec=responder_htlc_timelock_sec,
        atomic_pvp_settled=True,
    )


def evaluate_lbma_allocated_bullion_bar_audit(
    *,
    vault_receipt_id: str,
    bar_serial_number: str,
    allocation_status: str,  # "ALLOCATED_SEGREGATED" or "UNALLOCATED_PAPER_POOL"
    refiner_good_delivery_active: bool,
    ultrasonic_c_scan_passed: bool,
    ultrasonic_fineness_permille: float,
    gross_bar_troy_ounces_milli: int,  # e.g., 400_000 for 400.000 oz
    locked_spot_price_per_fine_oz_minor: int,
    buyer_escrow_deposit_minor: int,
) -> LBMABullionBarAuditResult:
    """Audit LBMA Good Delivery physical bullion bars, blocking unallocated paper substitution and tungsten/assay failures."""
    fine_troy_ounces_milli = int(
        round(gross_bar_troy_ounces_milli * (ultrasonic_fineness_permille / 1000.0))
    )

    if allocation_status != "ALLOCATED_SEGREGATED":
        return LBMABullionBarAuditResult(
            vault_receipt_id=vault_receipt_id,
            bar_serial_number=bar_serial_number,
            admitted=False,
            decision_code="LBMA_UNALLOCATED_PAPER_GOLD_SUBSTITUTION_BLOCKED",
            fine_troy_ounces_milli=fine_troy_ounces_milli,
            ultrasonic_fineness_permille=ultrasonic_fineness_permille,
            settled_bullion_value_minor=0,
            escrow_refund_to_buyer_minor=buyer_escrow_deposit_minor,
            conservation_delta_minor=0,
        )

    if (
        not refiner_good_delivery_active
        or not ultrasonic_c_scan_passed
        or ultrasonic_fineness_permille < 999.5
    ):
        return LBMABullionBarAuditResult(
            vault_receipt_id=vault_receipt_id,
            bar_serial_number=bar_serial_number,
            admitted=False,
            decision_code="LBMA_FINENESS_OR_ULTRASONIC_ASSAY_FAILURE_BLOCKED",
            fine_troy_ounces_milli=fine_troy_ounces_milli,
            ultrasonic_fineness_permille=ultrasonic_fineness_permille,
            settled_bullion_value_minor=0,
            escrow_refund_to_buyer_minor=buyer_escrow_deposit_minor,
            conservation_delta_minor=0,
        )

    settled_value_minor = (
        fine_troy_ounces_milli * locked_spot_price_per_fine_oz_minor
    ) // 1000
    settled_value_minor = min(buyer_escrow_deposit_minor, settled_value_minor)
    refund_minor = buyer_escrow_deposit_minor - settled_value_minor
    conservation_delta = buyer_escrow_deposit_minor - (settled_value_minor + refund_minor)

    return LBMABullionBarAuditResult(
        vault_receipt_id=vault_receipt_id,
        bar_serial_number=bar_serial_number,
        admitted=True,
        decision_code="LBMA_ALLOCATED_BULLION_FINE_WEIGHT_SETTLED",
        fine_troy_ounces_milli=fine_troy_ounces_milli,
        ultrasonic_fineness_permille=ultrasonic_fineness_permille,
        settled_bullion_value_minor=settled_value_minor,
        escrow_refund_to_buyer_minor=refund_minor,
        conservation_delta_minor=conservation_delta,
    )


def evaluate_parametric_crop_ndvi_weather_escrow(
    *,
    policy_id: str,
    insured_sum_escrow_minor: int,
    sentinel2_ndvi_milli: int,  # e.g., 220 for 0.220 NDVI
    modis_ndvi_milli: int,
    max_satellite_divergence_milli: int,
    ground_rainfall_mm: int,
    drought_ndvi_threshold_milli: int,
    drought_rainfall_threshold_mm: int,
    dual_satellite_and_station_signatures_valid: bool,
) -> ParametricCropNDVIEscrowResult:
    """Verify dual-satellite NDVI (Sentinel-2 + MODIS) and ground weather telemetry before releasing crop indemnity."""
    divergence_milli = abs(sentinel2_ndvi_milli - modis_ndvi_milli)

    if (
        not dual_satellite_and_station_signatures_valid
        or divergence_milli > max_satellite_divergence_milli
    ):
        return ParametricCropNDVIEscrowResult(
            policy_id=policy_id,
            admitted=False,
            decision_code="SATELLITE_NDVI_DIVERGENCE_OR_SPOOFED_ORACLE_BLOCKED",
            sentinel2_ndvi_Milli=sentinel2_ndvi_milli,
            modis_ndvi_milli=modis_ndvi_milli,
            sensor_divergence_milli=divergence_milli,
            ground_rainfall_mm=ground_rainfall_mm,
            payout_tier_bps=0,
            indemnity_payout_minor=0,
            insurer_retained_escrow_minor=insured_sum_escrow_minor,
            conservation_delta_minor=0,
        )

    mean_ndvi_milli = (sentinel2_ndvi_milli + modis_ndvi_milli) // 2
    if (
        mean_ndvi_milli < drought_ndvi_threshold_milli
        and ground_rainfall_mm < drought_rainfall_threshold_mm
    ):
        if mean_ndvi_milli < (drought_ndvi_threshold_milli * 70) // 100:
            payout_tier_bps = 10000  # Severe drought: 100% payout
        else:
            payout_tier_bps = 5000  # Moderate drought: 50% payout
        decision_code = "PARAMETRIC_CROP_NDVI_DROUGHT_INDEMNITY_RELEASED"
    else:
        payout_tier_bps = 0
        decision_code = "CROP_NDVI_HEALTHY_ESCROW_RETURNED_TO_POOL"

    indemnity_minor = (insured_sum_escrow_minor * payout_tier_bps) // 10000
    retained_minor = insured_sum_escrow_minor - indemnity_minor
    conservation_delta = insured_sum_escrow_minor - (indemnity_minor + retained_minor)

    return ParametricCropNDVIEscrowResult(
        policy_id=policy_id,
        admitted=True,
        decision_code=decision_code,
        sentinel2_ndvi_Milli=sentinel2_ndvi_milli,
        modis_ndvi_milli=modis_ndvi_milli,
        sensor_divergence_milli=divergence_milli,
        ground_rainfall_mm=ground_rainfall_mm,
        payout_tier_bps=payout_tier_bps,
        indemnity_payout_minor=indemnity_minor,
        insurer_retained_escrow_minor=retained_minor,
        conservation_delta_minor=conservation_delta,
    )
