# Multi-Party Marketplace Split Settlement Conservation, Sub-Merchant KYB Rolling Reserve Escalation & Negative-Balance Clawback Waterfall

**Stage 14 Deliverable — 2026-10-19 Overnight Evolution**

---

## 1. Executive Summary & Architectural Problem Statement

When multi-seller marketplaces (Stripe Connect / Adyen Balance Platform / UCP Multi-Merchant Carts) settle aggregated agentic orders across $K$ sub-merchants, three high-impact financial risks arise:

1. **Pro-Rata Rounding Drift (`\pm 1\text{ cent}` Ledger Imbalance)**:
   - Naive floating-point or independent `round()` allocation of shared cart discounts, shipping fees, or net payouts across 3 equal sellers (`$85.00 / 3 = $28.33 \times 3 = $84.99`) leaves a `1 cent` unallocated residual (`SPLIT_SETTLEMENT_CONSERVATION_DRIFT`).
   - Enforcing the deterministic **Largest Remainder Method (Hamilton's Method)** guarantees exact cent conservation:
     $$G_{\text{gross}} = \sum_{i=1}^K S_{\text{net},i} + C_{\text{platform}} + T_{\text{withholding}} + R_{\text{rolling\_reserve}}$$
2. **Sub-Merchant Bust-Out Fraud & Visa VAMP Dispute Escalation**:
   - Colluding or compromised sub-merchants can use synthetic AI agents to spike 30-day GMV (`> 3.5x` trailing average) or breach the Visa VAMP early-warning dispute threshold (`> 65 bps` / `0.65%`) and drain funds via `T+0` Instant Payouts before chargebacks land.
   - Our KYB Rolling Reserve Escalation engine dynamically raises reserve holds from baseline `5%` (`500 bps`) to `15%` (`1500 bps`) or `25%` (`2500 bps`) and freezes `T+0` Instant Payouts (`ROLLING_RESERVE_ESCALATED_15PCT_INSTANT_PAYOUT_FROZEN`, `ROLLING_RESERVE_ESCALATED_25PCT_BUST_OUT_GUARD`).
3. **Cross-Seller Partial Fulfillment Default & Negative-Balance Clawback Waterfall**:
   - When one sub-merchant in a multi-seller bundle defaults and its pending settlement balance cannot cover the refund obligation, recovery must execute deterministically in strict order:
     $$\text{Pending Settlement Freeze} \longrightarrow \text{Rolling Reserve Pool Offset} \longrightarrow \text{Linked Guarantor Debit} \longrightarrow \text{Platform Risk Reserve Isolation}$$

---

## 2. Executable Verification Commands

```bash
python -m lab.marketplace_split_settlement_guard
python -m unittest tests/test_marketplace_split_settlement_guard.py -v
```
