"""Unit tests for Stage 33 Wholesale CBDC mBridge PvP, LBMA Allocated Bullion Audit & Parametric Crop NDVI Oracle Guard."""

from __future__ import annotations

import unittest

from lab.cbdc_mbridge_bullion_crop_oracle_guard import (
    evaluate_lbma_allocated_bullion_bar_audit,
    evaluate_mbridge_wholesale_cbdc_pvp_settlement,
    evaluate_parametric_crop_ndvi_weather_escrow,
)


class TestCBDCMBridgeBullionCropOracleGuard(unittest.TestCase):
    def test_mbridge_wholesale_cbdc_pvp_settlement(self) -> None:
        inverted = evaluate_mbridge_wholesale_cbdc_pvp_settlement(
            pvp_trade_id="mbridge_pvp_01",
            corridor="e-CNY/e-HKD",
            source_cbdc_notional_minor=10_000_000_00,
            target_cbdc_notional_minor=10_850_000_00,
            agreed_fx_rate_scaled=10850,
            central_bank_mid_rate_scaled=10845,
            max_fx_corridor_band_bps=25,
            initiator_htlc_timelock_sec=600,
            responder_htlc_timelock_sec=550,  # margin 50s < 300s required
            min_htlc_safety_margin_sec=300,
            safe_capital_account_declaration_signed=True,
            commercial_bank_reserve_locked=True,
        )
        self.assertFalse(inverted.admitted)
        self.assertEqual(
            inverted.decision_code,
            "MBRIDGE_HTLC_TIMELOCK_INVERSION_HERSTATT_RISK_BLOCKED",
        )

        settled = evaluate_mbridge_wholesale_cbdc_pvp_settlement(
            pvp_trade_id="mbridge_pvp_02",
            corridor="e-CNY/e-HKD",
            source_cbdc_notional_minor=10_000_000_00,
            target_cbdc_notional_minor=10_850_000_00,
            agreed_fx_rate_scaled=10850,
            central_bank_mid_rate_scaled=10845,
            max_fx_corridor_band_bps=25,
            initiator_htlc_timelock_sec=900,
            responder_htlc_timelock_sec=450,
            min_htlc_safety_margin_sec=300,
            safe_capital_account_declaration_signed=True,
            commercial_bank_reserve_locked=True,
        )
        self.assertTrue(settled.admitted)
        self.assertEqual(
            settled.decision_code,
            "MBRIDGE_WHOLESALE_CBDC_ATOMIC_PVP_SETTLED",
        )
        self.assertTrue(settled.atomic_pvp_settled)

    def test_lbma_allocated_bullion_bar_audit(self) -> None:
        unallocated = evaluate_lbma_allocated_bullion_bar_audit(
            vault_receipt_id="lbma_vault_01",
            bar_serial_number="AU-ZH-88412",
            allocation_status="UNALLOCATED_PAPER_POOL",
            refiner_good_delivery_active=True,
            ultrasonic_c_scan_passed=True,
            ultrasonic_fineness_permille=999.9,
            gross_bar_troy_ounces_milli=400_000,
            locked_spot_price_per_fine_oz_minor=275_000,
            buyer_escrow_deposit_minor=110_000_000,
        )
        self.assertFalse(unallocated.admitted)
        self.assertEqual(
            unallocated.decision_code,
            "LBMA_UNALLOCATED_PAPER_GOLD_SUBSTITUTION_BLOCKED",
        )

        settled = evaluate_lbma_allocated_bullion_bar_audit(
            vault_receipt_id="lbma_vault_02",
            bar_serial_number="AU-ZH-88413",
            allocation_status="ALLOCATED_SEGREGATED",
            refiner_good_delivery_active=True,
            ultrasonic_c_scan_passed=True,
            ultrasonic_fineness_permille=999.9,
            gross_bar_troy_ounces_milli=400_000,
            locked_spot_price_per_fine_oz_minor=275_000,
            buyer_escrow_deposit_minor=110_000_000,
        )
        self.assertTrue(settled.admitted)
        self.assertEqual(
            settled.decision_code,
            "LBMA_ALLOCATED_BULLION_FINE_WEIGHT_SETTLED",
        )
        self.assertEqual(settled.fine_troy_ounces_milli, 399_960)
        self.assertEqual(settled.settled_bullion_value_minor, 109_989_000)
        self.assertEqual(settled.escrow_refund_to_buyer_minor, 11_000)
        self.assertEqual(settled.conservation_delta_minor, 0)

    def test_parametric_crop_ndvi_weather_escrow(self) -> None:
        divergent = evaluate_parametric_crop_ndvi_weather_escrow(
            policy_id="crop_ndvi_01",
            insured_sum_escrow_minor=50_000_00,
            sentinel2_ndvi_milli=180,
            modis_ndvi_milli=490,  # 310 divergence > 80 max
            max_satellite_divergence_milli=80,
            ground_rainfall_mm=15,
            drought_ndvi_threshold_milli=300,
            drought_rainfall_threshold_mm=40,
            dual_satellite_and_station_signatures_valid=True,
        )
        self.assertFalse(divergent.admitted)
        self.assertEqual(
            divergent.decision_code,
            "SATELLITE_NDVI_DIVERGENCE_OR_SPOOFED_ORACLE_BLOCKED",
        )

        released = evaluate_parametric_crop_ndvi_weather_escrow(
            policy_id="crop_ndvi_02",
            insured_sum_escrow_minor=50_000_00,
            sentinel2_ndvi_milli=180,
            modis_ndvi_milli=190,
            max_satellite_divergence_milli=80,
            ground_rainfall_mm=15,
            drought_ndvi_threshold_milli=300,
            drought_rainfall_threshold_mm=40,
            dual_satellite_and_station_signatures_valid=True,
        )
        self.assertTrue(released.admitted)
        self.assertEqual(
            released.decision_code,
            "PARAMETRIC_CROP_NDVI_DROUGHT_INDEMNITY_RELEASED",
        )
        self.assertEqual(released.indemnity_payout_minor, 50_000_00)
        self.assertEqual(released.conservation_delta_minor, 0)


if __name__ == "__main__":
    unittest.main()
