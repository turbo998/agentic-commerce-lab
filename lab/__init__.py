"""Offline, synthetic agentic commerce experiments, not vendor integrations."""

from __future__ import annotations

from typing import Any

__all__ = [
    "allocate_by_largest_remainder",
    "evaluate_fx_quote_lock_and_slippage",
    "evaluate_seller_kyb_rolling_reserve",
    "evaluate_split_settlement_invariant",
    "execute_negative_balance_clawback_waterfall",
    "optimize_multicurrency_netting_sweep",
    "validate_iso20022_pacs008_instruction",
]


def __getattr__(name: str) -> Any:
    if name in {
        "evaluate_fx_quote_lock_and_slippage",
        "optimize_multicurrency_netting_sweep",
        "validate_iso20022_pacs008_instruction",
    }:
        from lab import fx_treasury_iso20022_guard

        return getattr(fx_treasury_iso20022_guard, name)
    if name in {
        "allocate_by_largest_remainder",
        "evaluate_seller_kyb_rolling_reserve",
        "evaluate_split_settlement_invariant",
        "execute_negative_balance_clawback_waterfall",
    }:
        from lab import marketplace_split_settlement_guard

        return getattr(marketplace_split_settlement_guard, name)
    raise AttributeError(f"module 'lab' has no attribute {name!r}")


