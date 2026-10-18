# x402 EIP-3009 Authorization Window & Replay Guard, Stablecoin De-Peg Oracle Circuit Breaker, Tiered L2 Finality Gate & Gas-Congestion MPP Tempo Router

**Stage 13 Deliverable — 2026-10-19 Overnight Evolution**

---

## 1. Executive Summary & Architectural Problem Statement

When machine agents execute autonomous micropayments and B2B settlements over **`Coinbase x402`** (`EIP-3009` `ReceiveWithAuthorization` on Base / Arbitrum / Ethereum) and **`Stripe MPP`** (`Tempo` / Bridge streaming payment channels), four critical on-chain and hybrid settlement vulnerabilities arise:

1. **EIP-3009 Free-Option Signature Hoarding & Token Contract Spoofing**:
   - If a buyer agent signs an `EIP-712` `ReceiveWithAuthorization` payload with an unbounded or multi-hour `validBefore` timestamp (`validBefore - now_epoch > 300s`), a malicious facilitator or merchant can hoard the off-chain signature as a free option and broadcast it selectively (`EIP3009_VALID_WINDOW_EXCEEDED`).
   - Unverified `token_contract` or `chainId` fields allow spoofed ERC-20 contracts to pass off worthless tokens as canonical USDC (`EIP3009_CONTRACT_OR_CHAIN_MISMATCH`), while reused 32-byte nonces enable replay attacks (`EIP3009_NONCE_REPLAY`).
2. **L2 Sequencer Soft-Confirmation Reorg vs. High-Value Irreversible Delivery**:
   - Accepting an optimistic L2 sequencer `L2_SOFT_CONFIRM` receipt for high-value (`>= $500.00`) or irreversible digital/compute/physical fulfillment exposes the merchant to L2 block reorg or batch submission failures (`INSUFFICIENT_FINALITY_FOR_HIGH_VALUE_DELIVERY`).
3. **Stablecoin De-Peg & Stale Oracle Feed Contagion**:
   - During market stress, accepting stablecoin settlement when Pyth/Chainlink price feeds deviate beyond $\pm 50\text{ bps}$ from `$1.0000` (`[$0.9950, $1.0050]`) or when oracle updates stall (`oracle_age_sec > 60s`) transfers de-peg losses directly onto the merchant treasury (`STABLECOIN_DEPEG_CIRCUIT_BREAKER`, `ORACLE_FEED_STALE`).
4. **L2 Relayer Gas Spike Margin Erosion on Micropayments**:
   - Broadcasting individual `EIP-3009` transactions during L2 blob/execution gas spikes can drive `relayer_gas_usd / payment_value_usd > 15%` (or negative net yield), requiring automatic aggregation into `Stripe MPP Tempo` off-chain signed voucher streaming channels (`GAS_TO_VALUE_RATIO_EXCEEDED_ROUTE_TO_MPP_CHANNEL`).

---

## 2. Deterministic Invariants (`lab/onchain_finality_peg_guard.py`)

### 2.1 EIP-3009 Authorization & Tiered L2 Finality Equations

$$\text{validAfter} < t_{\text{now}} < \text{validBefore}, \qquad \text{validBefore} - t_{\text{now}} \le 300\text{ s}$$

$$\text{RequiredFinality}(V, \text{irreversible}) = \begin{cases} \text{L1\_BATCH\_FINALIZED} & \text{if } V \ge \$500.00 \text{ or } \text{irreversible}=\text{True} \\ \text{L2\_SAFE\_HEAD } (\ge 10\text{ blocks}) & \text{if } \$50.00 \le V < \$500.00 \\ \text{L2\_SOFT\_CONFIRM} & \text{if } V < \$50.00 \text{ and reversible} \end{cases}$$

### 2.2 Stablecoin De-Peg Circuit Breaker & MPP Tempo Gas Routing

$$|P_{\text{USDC/USD}} - 1.0000| \le 50\text{ bps}, \qquad t_{\text{now}} - t_{\text{oracle}} \le 60\text{ s}$$

$$\text{GasRatio}_{\text{bps}} = \left\lfloor \frac{G_{\text{relayer\_usd}}}{V_{\text{payment\_usd}}} \times 10000 \right\rceil \le 1500\text{ bps} \quad \Longrightarrow \quad \text{otherwise route to }\texttt{STRIPE\_MPP\_TEMPO\_STREAMING\_CHANNEL}$$

---

## 3. Executable Verification Commands

```bash
python -m lab.onchain_finality_peg_guard
python -m unittest tests/test_onchain_finality_peg_guard.py -v
```
