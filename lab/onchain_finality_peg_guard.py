"""x402 EIP-3009 Authorization Window & Replay Guard, Stablecoin De-Peg Oracle Circuit Breaker, Tiered L2 Finality Gate & Gas-Congestion MPP Tempo Router (Stage 13).

Enforces four production invariants for on-chain and hybrid agentic payments
(`Coinbase x402` EIP-3009 `ReceiveWithAuthorization` on Base/EVM and
`Stripe MPP Tempo` streaming micropayment channels):

1. EIP-3009 Authorization Window, Contract Whitelist & Nonce Anti-Replay:
   - Verifies `(chain_id, token_contract)` against official canonical USDC
     contract addresses (`EIP3009_CONTRACT_OR_CHAIN_MISMATCH`).
   - Enforces `now_epoch > valid_after` and `now_epoch < valid_before`
     (`EIP3009_EXPIRED_OR_NOT_YET_VALID`).
   - Caps `valid_before - now_epoch <= max_valid_window_sec` (default `300s`) so
     malicious facilitators cannot hoard signed authorizations as free options
     (`EIP3009_VALID_WINDOW_EXCEEDED`).
   - Enforces single-use 32-byte `nonce` idempotency (`EIP3009_NONCE_REPLAY`).

2. Tiered L2 Block Finality vs. Delivery Value Gate:
   - Tier 1 (`< $50.00` reversible/low-value API call): admits `L2_SOFT_CONFIRM`.
   - Tier 2 (`$50.00 - $499.99`): requires at least `L2_SAFE_HEAD` (`>= 10` L2 blocks).
   - Tier 3 (`>= $500.00` or `irreversible_delivery=True`): requires
     `L1_BATCH_FINALIZED` (`l1_batch_posted=True`), blocking L2 sequencer
     reorg exploits (`INSUFFICIENT_FINALITY_FOR_HIGH_VALUE_DELIVERY`).

3. Stablecoin De-Peg & Oracle Staleness Circuit Breaker:
   - Verifies Pyth/Chainlink price age `<= max_oracle_age_sec` (`60s`,
     `ORACLE_FEED_STALE`).
   - Trips `STABLECOIN_DEPEG_CIRCUIT_BREAKER` if `|price - $1.0000| > 50 bps`
     (outside `[$0.9950, $1.0050]`), failing over to fiat `STRIPE_SPT_FIAT_FALLBACK`.

4. Relayer Gas-to-Value Ratio & Automatic MPP Tempo Channel Aggregation:
   - When per-transaction on-chain relayer gas exceeds `max_gas_to_value_bps`
     (default `1500 bps` = `15%`) or erodes net merchant yield below zero,
     blocks individual on-chain broadcast and routes to
     `STRIPE_MPP_TEMPO_STREAMING_CHANNEL` (`GAS_TO_VALUE_RATIO_EXCEEDED_ROUTE_TO_MPP_CHANNEL`).
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_HALF_UP
import json
from typing import Any


OFFICIAL_USDC_CONTRACTS: dict[int, str] = {
    8453: "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",   # Base Mainnet USDC
    84532: "0x036cbd53842c5426634e7929541ec2318f3dcf7e",  # Base Sepolia USDC
    1: "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",      # Ethereum Mainnet USDC
    42161: "0xaf88d065e77c8cc2239327c5edb3a432268e5831",  # Arbitrum One USDC
}


@dataclass(frozen=True)
class X402FinalityDecision:
    allowed: bool
    decision_code: str
    chain_id: int
    token_contract: str
    amount_minor: int
    remaining_valid_window_sec: int
    required_finality_tier: str
    observed_finality_tier: str
    nonce_recorded: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class StablecoinPegAndGasDecision:
    allowed_onchain_x402: bool
    decision_code: str
    recommended_rail: str
    stablecoin_price_usd: str
    depeg_deviation_bps: int
    oracle_age_sec: int
    gas_to_value_bps: int
    net_merchant_yield_usd: str
    reasons: tuple[str, ...]


def _to_decimal(value: str | float | int | Decimal) -> Decimal:
    return Decimal(str(value))


def _determine_required_finality_tier(
    amount_minor: int,
    irreversible_delivery: bool,
) -> str:
    if irreversible_delivery or amount_minor >= 50_000:
        return "L1_BATCH_FINALIZED"
    if amount_minor >= 5_000:
        return "L2_SAFE_HEAD"
    return "L2_SOFT_CONFIRM"


def _finality_rank(tier: str) -> int:
    ranks = {
        "UNCONFIRMED_MEMPOOL": 0,
        "L2_SOFT_CONFIRM": 1,
        "L2_SAFE_HEAD": 2,
        "L1_BATCH_FINALIZED": 3,
    }
    return ranks.get(tier, 0)


def verify_x402_eip3009_and_finality_guard(
    auth_bundle: dict[str, Any],
    delivery_context: dict[str, Any],
    *,
    seen_nonces: set[str] | None = None,
    trusted_contracts: dict[int, str] | None = None,
    max_valid_window_sec: int = 300,
) -> X402FinalityDecision:
    """Validate an x402 EIP-3009 ReceiveWithAuthorization payload and L2 finality tier."""
    reasons: list[str] = []
    whitelist = trusted_contracts or OFFICIAL_USDC_CONTRACTS
    nonce_registry = seen_nonces if seen_nonces is not None else set()

    chain_id = int(auth_bundle.get("chain_id", 0))
    token_contract = str(auth_bundle.get("token_contract", "")).strip().lower()
    nonce_hex = str(auth_bundle.get("nonce_hex", "")).strip().lower()
    valid_after = int(auth_bundle.get("valid_after_epoch", 0))
    valid_before = int(auth_bundle.get("valid_before_epoch", 0))
    now_epoch = int(auth_bundle.get("now_epoch", 0))
    amount_minor = int(auth_bundle.get("amount_minor", 0))

    irreversible_delivery = bool(delivery_context.get("irreversible_delivery", False))
    observed_tier = str(delivery_context.get("observed_finality_tier", "L2_SOFT_CONFIRM"))
    l2_confirmations = int(delivery_context.get("l2_confirmations", 1))
    l1_batch_posted = bool(delivery_context.get("l1_batch_posted", False))

    # Derive effective finality tier from block/batch telemetry if lower than claimed
    if observed_tier == "L1_BATCH_FINALIZED" and not l1_batch_posted:
        observed_tier = "L2_SAFE_HEAD" if l2_confirmations >= 10 else "L2_SOFT_CONFIRM"
    elif observed_tier == "L2_SAFE_HEAD" and l2_confirmations < 10:
        observed_tier = "L2_SOFT_CONFIRM"

    required_tier = _determine_required_finality_tier(amount_minor, irreversible_delivery)
    remaining_window = valid_before - now_epoch

    expected_contract = whitelist.get(chain_id, "").lower()
    if not expected_contract or token_contract != expected_contract:
        reasons.append("EIP3009_CONTRACT_OR_CHAIN_MISMATCH")

    if (
        not nonce_hex.startswith("0x")
        or len(nonce_hex) != 66
        or nonce_hex in nonce_registry
    ):
        reasons.append("EIP3009_NONCE_REPLAY")

    if now_epoch <= valid_after or now_epoch >= valid_before:
        reasons.append("EIP3009_EXPIRED_OR_NOT_YET_VALID")
    elif remaining_window > max_valid_window_sec:
        reasons.append("EIP3009_VALID_WINDOW_EXCEEDED")

    if _finality_rank(observed_tier) < _finality_rank(required_tier):
        reasons.append("INSUFFICIENT_FINALITY_FOR_HIGH_VALUE_DELIVERY")

    allowed = len(reasons) == 0
    if allowed:
        nonce_registry.add(nonce_hex)
    decision_code = "X402_EIP3009_AND_FINALITY_VERIFIED" if allowed else reasons[0]

    return X402FinalityDecision(
        allowed=allowed,
        decision_code=decision_code,
        chain_id=chain_id,
        token_contract=token_contract,
        amount_minor=amount_minor,
        remaining_valid_window_sec=remaining_window,
        required_finality_tier=required_tier,
        observed_finality_tier=observed_tier,
        nonce_recorded=allowed,
        reasons=tuple(reasons),
    )


def evaluate_stablecoin_depeg_and_gas_routing(
    peg_and_gas_context: dict[str, Any],
    *,
    max_depeg_bps: int = 50,
    max_oracle_age_sec: int = 60,
    max_gas_to_value_bps: int = 1500,
) -> StablecoinPegAndGasDecision:
    """Verify stablecoin oracle peg health and route gas-heavy micropayments to MPP Tempo."""
    reasons: list[str] = []

    price_usd = _to_decimal(peg_and_gas_context.get("stablecoin_price_usd", "1.0000"))
    oracle_published = int(peg_and_gas_context.get("oracle_published_epoch", 0))
    now_epoch = int(peg_and_gas_context.get("now_epoch", 0))
    payment_value_usd = _to_decimal(peg_and_gas_context.get("payment_value_usd", "1.00"))
    relayer_gas_usd = _to_decimal(peg_and_gas_context.get("relayer_gas_usd", "0.001"))

    oracle_age = now_epoch - oracle_published
    deviation_bps = int(
        (abs(price_usd - Decimal("1.0000")) * Decimal("10000")).to_integral_value(
            rounding=ROUND_HALF_UP
        )
    )

    if payment_value_usd <= Decimal("0"):
        gas_to_value_bps = 10_000
    else:
        gas_to_value_bps = int(
            ((relayer_gas_usd / payment_value_usd) * Decimal("10000")).to_integral_value(
                rounding=ROUND_HALF_UP
            )
        )

    effective_fiat_value = (payment_value_usd * price_usd).quantize(
        Decimal("0.000001"), rounding=ROUND_HALF_UP
    )
    net_yield = (effective_fiat_value - relayer_gas_usd).quantize(
        Decimal("0.000001"), rounding=ROUND_HALF_UP
    )

    recommended_rail = "X402_EIP3009_ONCHAIN"

    if oracle_age < 0 or oracle_age > max_oracle_age_sec:
        reasons.append("ORACLE_FEED_STALE")
        recommended_rail = "STRIPE_SPT_FIAT_FALLBACK"

    if deviation_bps > max_depeg_bps:
        reasons.append("STABLECOIN_DEPEG_CIRCUIT_BREAKER")
        recommended_rail = "STRIPE_SPT_FIAT_FALLBACK"

    if (
        not reasons
        and (gas_to_value_bps > max_gas_to_value_bps or net_yield <= Decimal("0"))
    ):
        reasons.append("GAS_TO_VALUE_RATIO_EXCEEDED_ROUTE_TO_MPP_CHANNEL")
        recommended_rail = "STRIPE_MPP_TEMPO_STREAMING_CHANNEL"

    allowed_onchain = len(reasons) == 0
    decision_code = (
        "ONCHAIN_X402_SETTLEMENT_HEALTHY" if allowed_onchain else reasons[0]
    )

    return StablecoinPegAndGasDecision(
        allowed_onchain_x402=allowed_onchain,
        decision_code=decision_code,
        recommended_rail=recommended_rail,
        stablecoin_price_usd=str(price_usd.quantize(Decimal("0.0001"))),
        depeg_deviation_bps=deviation_bps,
        oracle_age_sec=oracle_age,
        gas_to_value_bps=gas_to_value_bps,
        net_merchant_yield_usd=str(net_yield),
        reasons=tuple(reasons),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Stage 13 x402 EIP-3009 finality, stablecoin peg & MPP gas routing guard."
    )
    parser.parse_args(argv)

    valid_auth = verify_x402_eip3009_and_finality_guard(
        auth_bundle={
            "chain_id": 8453,
            "token_contract": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
            "nonce_hex": "0x" + "a1" * 32,
            "valid_after_epoch": 1_760_800_000,
            "valid_before_epoch": 1_760_800_180,
            "now_epoch": 1_760_800_060,
            "amount_minor": 120_000,
        },
        delivery_context={
            "irreversible_delivery": True,
            "observed_finality_tier": "L1_BATCH_FINALIZED",
            "l2_confirmations": 45,
            "l1_batch_posted": True,
        },
    )
    depeg_check = evaluate_stablecoin_depeg_and_gas_routing(
        {
            "stablecoin_price_usd": "0.9880",
            "oracle_published_epoch": 1_760_800_050,
            "now_epoch": 1_760_800_060,
            "payment_value_usd": "25.00",
            "relayer_gas_usd": "0.01",
        }
    )
    gas_spike_check = evaluate_stablecoin_depeg_and_gas_routing(
        {
            "stablecoin_price_usd": "1.0000",
            "oracle_published_epoch": 1_760_800_050,
            "now_epoch": 1_760_800_060,
            "payment_value_usd": "0.020000",
            "relayer_gas_usd": "0.008000",
        }
    )
    print(
        json.dumps(
            {
                "stage": "stage13-onchain-finality-peg-guard",
                "valid_eip3009_admitted": valid_auth.allowed,
                "depeg_circuit_breaker": depeg_check.decision_code,
                "depeg_fallback_rail": depeg_check.recommended_rail,
                "gas_spike_decision": gas_spike_check.decision_code,
                "gas_spike_routed_rail": gas_spike_check.recommended_rail,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
