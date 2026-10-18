"""Unit tests for Stage 15 FX Quote Lock, Multi-Currency Natural Netting & ISO 20022 pacs.008 Guard."""

from __future__ import annotations

from decimal import Decimal
import unittest

from lab.fx_treasury_iso20022_guard import (
    evaluate_fx_quote_lock_and_slippage,
    main,
    optimize_multicurrency_netting_sweep,
    validate_iso20022_pacs008_instruction,
)


class FxTreasuryIso20022GuardTestSuite(unittest.TestCase):
    def test_fx_quote_lock_within_collar_and_merchant_buffer_absorption(self) -> None:
        within = evaluate_fx_quote_lock_and_slippage(
            {
                "pair": "GBP/USD",
                "quote_created_epoch": 1_760_800_000,
                "quote_expires_at_epoch": 1_760_800_090,
                "now_epoch": 1_760_800_030,
                "mid_market_rate": "1.3000",
                "locked_rate": "1.3020",
                "live_spot_rate": "1.3060",  # 31 bps <= 75 bps collar
                "merchant_buffer_bps": 35,
            }
        )
        self.assertTrue(within.allowed)
        self.assertFalse(within.buffer_absorbed)
        self.assertEqual(within.decision_code, "FX_QUOTE_LOCK_WITHIN_COLLAR")

        absorbed = evaluate_fx_quote_lock_and_slippage(
            {
                "pair": "EUR/USD",
                "quote_created_epoch": 1_760_800_000,
                "quote_expires_at_epoch": 1_760_800_090,
                "now_epoch": 1_760_800_045,
                "mid_market_rate": "1.0850",
                "locked_rate": "1.0870",
                "live_spot_rate": "1.0975",  # 97 bps <= 75 + 35 (110 bps)
                "merchant_buffer_bps": 35,
            }
        )
        self.assertTrue(absorbed.allowed)
        self.assertTrue(absorbed.buffer_absorbed)
        self.assertEqual(
            absorbed.decision_code,
            "FX_SLIPPAGE_ABSORBED_BY_MERCHANT_BUFFER",
        )

    def test_blocks_expired_fx_quote_excessive_spread_and_breached_collar(self) -> None:
        expired = evaluate_fx_quote_lock_and_slippage(
            {
                "pair": "EUR/USD",
                "quote_created_epoch": 1_760_800_000,
                "quote_expires_at_epoch": 1_760_800_180,  # 180s > 120s max TTL
                "now_epoch": 1_760_800_050,
                "mid_market_rate": "1.0850",
                "locked_rate": "1.0860",
                "live_spot_rate": "1.0865",
            }
        )
        self.assertFalse(expired.allowed)
        self.assertEqual(expired.decision_code, "FX_QUOTE_TTL_EXCEEDED_OR_EXPIRED")

        breached = evaluate_fx_quote_lock_and_slippage(
            {
                "pair": "USD/JPY",
                "quote_created_epoch": 1_760_800_000,
                "quote_expires_at_epoch": 1_760_800_090,
                "now_epoch": 1_760_800_040,
                "mid_market_rate": "150.00",
                "locked_rate": "150.30",
                "live_spot_rate": "152.50",  # 146 bps > 75 + 35 bps
                "merchant_buffer_bps": 35,
            }
        )
        self.assertFalse(breached.allowed)
        self.assertEqual(
            breached.decision_code,
            "FX_VOLATILITY_COLLAR_BREACHED_REQUOTE_REQUIRED",
        )

    def test_multicurrency_natural_netting_reduces_effective_fx_drag_below_12bps(self) -> None:
        res = optimize_multicurrency_netting_sweep(
            [
                {"currency": "EUR", "receivables_minor": 45_000_000, "payables_minor": 41_000_000, "mid_usd_rate": "1.0850"},
                {"currency": "GBP", "receivables_minor": 28_000_000, "payables_minor": 30_000_000, "mid_usd_rate": "1.3050"},
                {"currency": "JPY", "receivables_minor": 50_000_000, "payables_minor": 48_000_000, "mid_usd_rate": "0.0067"},
                {"currency": "SGD", "receivables_minor": 19_000_000, "payables_minor": 18_500_000, "mid_usd_rate": "0.7620"},
            ]
        )
        self.assertEqual(res.decision_code, "MULTICURRENCY_NATURAL_NETTING_OPTIMIZED")
        self.assertGreater(Decimal(res.netting_efficiency_pct), Decimal("90.00"))
        self.assertLess(Decimal(res.effective_blended_cost_bps), Decimal("12.00"))
        self.assertGreater(Decimal(res.fx_cost_savings_usd), Decimal("45000.00"))

    def test_validates_iso20022_pacs008_uetr_purpose_charge_bearer_and_cutoff(self) -> None:
        valid = validate_iso20022_pacs008_instruction(
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
        self.assertTrue(valid.valid)
        self.assertEqual(valid.decision_code, "ISO20022_PACS008_INSTRUCTION_VALID")

        bad_uetr = validate_iso20022_pacs008_instruction(
            {
                "uetr": "not-a-valid-uuidv4",
                "purpose_code": "GDDS",
                "charge_bearer": "SHAR",
                "currency": "EUR",
                "instructed_amount_minor": 100_000,
                "submission_epoch": 1_760_800_100,
                "correspondent_cutoff_epoch": 1_760_803_600,
            }
        )
        self.assertFalse(bad_uetr.valid)
        self.assertEqual(bad_uetr.decision_code, "ISO20022_INVALID_UETR_UUIDV4")

        bad_bearer_and_cutoff = validate_iso20022_pacs008_instruction(
            {
                "uetr": "97ed4827-7b6f-4491-a06f-b548d5a7512d",
                "purpose_code": "SUPP",
                "charge_bearer": "CRED",  # Violates full principal delivery
                "currency": "GBP",
                "instructed_amount_minor": 250_000,
                "submission_epoch": 1_760_805_000,
                "correspondent_cutoff_epoch": 1_760_803_600,
                "require_full_principal_delivery": True,
            }
        )
        self.assertFalse(bad_bearer_and_cutoff.valid)
        self.assertEqual(
            bad_bearer_and_cutoff.decision_code,
            "ISO20022_CHARGE_BEARER_VIOLATES_FULL_VALUE_DELIVERY",
        )
        self.assertIn(
            "ISO20022_CORRESPONDENT_CUTOFF_WINDOW_MISSED",
            bad_bearer_and_cutoff.reasons,
        )

    def test_cli_main_returns_zero(self) -> None:
        self.assertEqual(main([]), 0)


if __name__ == "__main__":
    unittest.main()
