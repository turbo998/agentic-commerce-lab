"""Unit tests for Stage 13 x402 EIP-3009 Finality, Stablecoin De-Peg & Gas Routing Guard."""

from __future__ import annotations

import unittest

from lab.onchain_finality_peg_guard import (
    evaluate_stablecoin_depeg_and_gas_routing,
    main,
    verify_x402_eip3009_and_finality_guard,
)


class OnchainFinalityPegGuardTestSuite(unittest.TestCase):
    def test_valid_x402_eip3009_and_tiered_finality_passes_and_blocks_nonce_replay(self) -> None:
        nonces: set[str] = set()
        auth = {
            "chain_id": 8453,
            "token_contract": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
            "nonce_hex": "0x" + "1b" * 32,
            "valid_after_epoch": 1_760_800_000,
            "valid_before_epoch": 1_760_800_200,
            "now_epoch": 1_760_800_050,
            "amount_minor": 85_000,  # $850.00 -> requires L1_BATCH_FINALIZED
        }
        ctx = {
            "irreversible_delivery": True,
            "observed_finality_tier": "L1_BATCH_FINALIZED",
            "l2_confirmations": 30,
            "l1_batch_posted": True,
        }
        first = verify_x402_eip3009_and_finality_guard(auth, ctx, seen_nonces=nonces)
        self.assertTrue(first.allowed)
        self.assertEqual(first.decision_code, "X402_EIP3009_AND_FINALITY_VERIFIED")
        self.assertEqual(first.required_finality_tier, "L1_BATCH_FINALIZED")

        replay = verify_x402_eip3009_and_finality_guard(auth, ctx, seen_nonces=nonces)
        self.assertFalse(replay.allowed)
        self.assertEqual(replay.decision_code, "EIP3009_NONCE_REPLAY")

    def test_blocks_excessive_eip3009_valid_window_and_spoofed_usdc_contract(self) -> None:
        long_window = verify_x402_eip3009_and_finality_guard(
            auth_bundle={
                "chain_id": 8453,
                "token_contract": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
                "nonce_hex": "0x" + "2c" * 32,
                "valid_after_epoch": 1_760_800_000,
                "valid_before_epoch": 1_760_804_000,  # 3950s > 300s cap
                "now_epoch": 1_760_800_050,
                "amount_minor": 1_500,
            },
            delivery_context={"irreversible_delivery": False, "observed_finality_tier": "L2_SOFT_CONFIRM"},
        )
        self.assertFalse(long_window.allowed)
        self.assertEqual(long_window.decision_code, "EIP3009_VALID_WINDOW_EXCEEDED")

        spoofed_token = verify_x402_eip3009_and_finality_guard(
            auth_bundle={
                "chain_id": 8453,
                "token_contract": "0xdeadbeef00000000000000000000000000000000",
                "nonce_hex": "0x" + "3d" * 32,
                "valid_after_epoch": 1_760_800_000,
                "valid_before_epoch": 1_760_800_180,
                "now_epoch": 1_760_800_050,
                "amount_minor": 1_500,
            },
            delivery_context={"irreversible_delivery": False, "observed_finality_tier": "L2_SOFT_CONFIRM"},
        )
        self.assertFalse(spoofed_token.allowed)
        self.assertEqual(spoofed_token.decision_code, "EIP3009_CONTRACT_OR_CHAIN_MISMATCH")

    def test_blocks_soft_confirm_finality_on_high_value_or_irreversible_delivery(self) -> None:
        premature = verify_x402_eip3009_and_finality_guard(
            auth_bundle={
                "chain_id": 8453,
                "token_contract": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
                "nonce_hex": "0x" + "4e" * 32,
                "valid_after_epoch": 1_760_800_000,
                "valid_before_epoch": 1_760_800_180,
                "now_epoch": 1_760_800_050,
                "amount_minor": 75_000,  # $750.00 high value
            },
            delivery_context={
                "irreversible_delivery": True,
                "observed_finality_tier": "L2_SOFT_CONFIRM",
                "l2_confirmations": 1,
                "l1_batch_posted": False,
            },
        )
        self.assertFalse(premature.allowed)
        self.assertEqual(
            premature.decision_code,
            "INSUFFICIENT_FINALITY_FOR_HIGH_VALUE_DELIVERY",
        )

    def test_stablecoin_depeg_and_stale_oracle_trip_fiat_fallback(self) -> None:
        depegged = evaluate_stablecoin_depeg_and_gas_routing(
            {
                "stablecoin_price_usd": "0.9910",  # 90 bps > 50 bps threshold
                "oracle_published_epoch": 1_760_800_040,
                "now_epoch": 1_760_800_060,
                "payment_value_usd": "100.00",
                "relayer_gas_usd": "0.02",
            }
        )
        self.assertFalse(depegged.allowed_onchain_x402)
        self.assertEqual(depegged.decision_code, "STABLECOIN_DEPEG_CIRCUIT_BREAKER")
        self.assertEqual(depegged.recommended_rail, "STRIPE_SPT_FIAT_FALLBACK")

        stale_oracle = evaluate_stablecoin_depeg_and_gas_routing(
            {
                "stablecoin_price_usd": "1.0000",
                "oracle_published_epoch": 1_760_799_800,  # 260s old > 60s cap
                "now_epoch": 1_760_800_060,
                "payment_value_usd": "100.00",
                "relayer_gas_usd": "0.02",
            }
        )
        self.assertFalse(stale_oracle.allowed_onchain_x402)
        self.assertEqual(stale_oracle.decision_code, "ORACLE_FEED_STALE")
        self.assertEqual(stale_oracle.recommended_rail, "STRIPE_SPT_FIAT_FALLBACK")

    def test_gas_spike_routes_micropayments_to_mpp_tempo_streaming_channel(self) -> None:
        gas_heavy = evaluate_stablecoin_depeg_and_gas_routing(
            {
                "stablecoin_price_usd": "1.0000",
                "oracle_published_epoch": 1_760_800_050,
                "now_epoch": 1_760_800_060,
                "payment_value_usd": "0.015000",
                "relayer_gas_usd": "0.006000",  # 4000 bps (40%) > 1500 bps cap
            }
        )
        self.assertFalse(gas_heavy.allowed_onchain_x402)
        self.assertEqual(
            gas_heavy.decision_code,
            "GAS_TO_VALUE_RATIO_EXCEEDED_ROUTE_TO_MPP_CHANNEL",
        )
        self.assertEqual(
            gas_heavy.recommended_rail,
            "STRIPE_MPP_TEMPO_STREAMING_CHANNEL",
        )

    def test_healthy_onchain_x402_and_cli_demo(self) -> None:
        healthy = evaluate_stablecoin_depeg_and_gas_routing(
            {
                "stablecoin_price_usd": "0.9998",
                "oracle_published_epoch": 1_760_800_050,
                "now_epoch": 1_760_800_060,
                "payment_value_usd": "5.000000",
                "relayer_gas_usd": "0.004000",
            }
        )
        self.assertTrue(healthy.allowed_onchain_x402)
        self.assertEqual(healthy.decision_code, "ONCHAIN_X402_SETTLEMENT_HEALTHY")
        self.assertEqual(healthy.recommended_rail, "X402_EIP3009_ONCHAIN")
        self.assertEqual(main([]), 0)


if __name__ == "__main__":
    unittest.main()
