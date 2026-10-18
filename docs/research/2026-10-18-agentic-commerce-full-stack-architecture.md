# Agentic Commerce Full-Stack AI-Native Reference Architecture (Stages 1–14 Consolidated Blueprint)

> **Canonical Reference Blueprint (`2026-10-18` – `2026-10-19` Overnight Evolution)**
> Covers the 6-Plane AI-Native Workload Architecture, 7-Gate Deterministic Checkout Pipeline, and §20 Multi-Party Marketplace Split Settlement, Sub-Merchant KYB Rolling Reserve Escalation & Clawback Recovery Waterfall.

---

## 1–19. Architectural Planes & Stage 1–13 Guard Matrix

| Section / Stage | Architectural Domain | Executable Module | Core Deterministic Invariants |
|---|---|---|---|
| **§1–§6 (Stages 1–2)** | 6-Plane AI-Native vs. Classic 3-Tier Workload Benchmark | [`lab/workload_arch_bench.py`](../../lab/workload_arch_bench.py) | Connect SPT profile routing, single-use `SPT Resolve` + RSA slicing, SPT 3DS state machine, AP2 §7.4 FCB, Policy Broker, UCP RFC 9530 catalog feed digest barrier, ATDRP 17-gateway fallback, MPP Tempo sub-cent forfeiture |
| **§7–§9 (Stage 3)** | Cross-Border Multi-Seller Split, Token Margin & Customs Incoterms | [`lab/cross_border_b2b_guard.py`](../../lab/cross_border_b2b_guard.py) | `separate_charges_and_transfers` conservation, `reverse_transfer=True`, `token_burn + rail_fee <= gross_margin`, `DDP` & WCO 6-digit `HS` lock |
| **§10–§11 (Stage 4)** | ACP PR #316 Appendix C 17-Gateway CE 3.0 Dispute Compiler | [`lab/dispute_evidence_replay.py`](../../lab/dispute_evidence_replay.py) | 4-pillar Merkle root (`AP2 Mandate JWS` + `SPT cryptogram` + `UCP RFC 9530 digest` + `DDP/HS6 proof`) & 3-way liability routing |
| **§12 (Stage 5)** | Enterprise Dual-Stack Cutover (`2026-11-30` 42-Day Countdown) | [`lab/protocol_readiness_auditor.py`](../../lab/protocol_readiness_auditor.py) | Phase A/B/C readiness scoring (`100/100`) & self-contained H5 Architect Workbench |
| **§13–§14 (Stage 6)** | Multi-Leg Booking Two-Phase Hold Saga & SFTP EOD Reconciliation | [`lab/booking_sftp_reconciliation_guard.py`](../../lab/booking_sftp_reconciliation_guard.py) | `HOLD_ALL (manual) -> VERIFY_TTL -> ATOMIC_CAPTURE_OR_REVERSE` & `00:00 UTC` SFTP × Tempo × Metronome three-way ledger balance |
| **§15 (Stage 7)** | RFC 9421 Agent Identity Attestation & Anti-Scalping Quotas | [`lab/agent_identity_attestation_guard.py`](../../lab/agent_identity_attestation_guard.py) | Mandatory 6-component RFC 9421 signatures, `<=60s` window, single-use `nonce`, Visa TAP/Stripe Directory JWKS & `(principal_did, sku_id)` scarcity quota |
| **§16 (Stage 8)** | 7-Gate Unified Agentic Checkout Pipeline Orchestrator | [`lab/unified_checkout_pipeline.py`](../../lab/unified_checkout_pipeline.py) | Fail-fast 7-gate execution across 14 chaos & adversarial scenarios (`14/14` AI-Native vs `1/14` Classic 3-Tier) |
| **§17 (Stage 9)** | Recurring Mandate `TCCV` Guard & 3-Layer Atomic Revocation | [`lab/recurring_subscription_guard.py`](../../lab/recurring_subscription_guard.py) | Worst-case $\text{TCCV} = C_{\text{init}} + \max(N_{\text{min}},1)C_{\text{rec}} + F_{\text{ETF}}$ & AP2 + SPT + Billing revocation cascade (`Visa 13.5` / `MC 4841`) |
| **§18 (Stage 10)** | Enterprise B2B 3-Way Match (`PO == GRN == Invoice`) & `2/10 Net 30` | [`lab/b2b_three_way_match_guard.py`](../../lab/b2b_three_way_match_guard.py) | Split-shipment partial capture escrow, BEC/OFAC sanctions block & `37.2449%` implied APR dynamic discounting |
| **§19 (Stages 11–13)** | Sealed Vickrey RFQ, B2B VAT, RMA, Split-Tender & `x402` Finality | [`lab/reverse_auction_tax_returns_guard.py`](../../lab/reverse_auction_tax_returns_guard.py), [`lab/split_tender_finops_guard.py`](../../lab/split_tender_finops_guard.py), [`lab/onchain_finality_peg_guard.py`](../../lab/onchain_finality_peg_guard.py) | Commit-Reveal second-price RFQ, reverse-charge VAT, bilateral RMA guard, split-tender anti-cash-out waterfall, cost-center encumbrance & `x402` EIP-3009 finality/peg guard |

---

## 20. Multi-Party Marketplace Split Settlement, Sub-Merchant KYB Rolling Reserve Escalation & Negative-Balance Clawback Waterfall (Stage 14)

### 20.1 Split Settlement Conservation & Largest Remainder Allocation (`evaluate_split_settlement_invariant`)

In multi-seller carts settled via Stripe Connect or Adyen Balance Platform, proportional allocation of shared pools across seller weights $w_1, \dots, w_K$ must use **Hamilton's Largest Remainder Method**:
1. Compute exact floor shares $q_i = \lfloor P_{\text{pool}} \cdot w_i / \sum w_j \rfloor$ and remainders $r_i = (P_{\text{pool}} \cdot w_i) \bmod \sum w_j$.
2. Distribute the residual cents $\Delta = P_{\text{pool}} - \sum_{i=1}^K q_i$ one cent each to the $\Delta$ sellers with the largest remainders $(r_i, -i)$.
3. Enforce global conservation:
   $$\text{gross\_amount\_minor} = \sum_{i=1}^K \text{seller\_net\_split}_i + \text{platform\_commission\_minor} + \text{tax\_withholding\_minor} + \text{rolling\_reserve\_hold\_minor}$$

### 20.2 Sub-Merchant KYB Risk Tiering & Dynamic Rolling Reserve Escalation (`evaluate_seller_kyb_rolling_reserve`)

- **Unverified KYB (`kyb_verified=False`)**: `100%` (`10000 bps`) escrow hold, all payouts blocked (`SUBMERCHANT_KYB_UNVERIFIED_PAYOUT_BLOCKED`).
- **Standard Verified Tier (`dispute_rate_bps <= 65` & `gmv_velocity_30d <= 3.5x`)**: `5%` (`500 bps`) rolling reserve, `T+0` Instant Payout permitted.
- **Elevated Risk Tier (`65 < dispute_rate_bps <= 90` OR `3.5x < gmv_velocity_30d <= 5.0x`)**: Escalates rolling reserve to `15%` (`1500 bps`) and freezes `T+0` Instant Payout (`ROLLING_RESERVE_ESCALATED_15PCT_INSTANT_PAYOUT_FROZEN`).
- **High-Risk Bust-Out Guard (`dispute_rate_bps > 90` OR `gmv_velocity_30d > 5.0x` OR dual VAMP + velocity breach)**: Escalates rolling reserve to `25%` (`2500 bps`) and freezes `T+0` Instant Payout (`ROLLING_RESERVE_ESCALATED_25PCT_BUST_OUT_GUARD`).

### 20.3 Cross-Seller Partial Fulfillment Default & 4-Stage Clawback Recovery Waterfall (`execute_negative_balance_clawback_waterfall`)

When a defaulting sub-merchant owes $R_{\text{obligation}}$ on a failed bundle leg:
1. **Stage 1 (`Pending Settlement Freeze`)**: $C_1 = \min(R_{\text{obligation}}, B_{\text{pending}})$
2. **Stage 2 (`Rolling Reserve Pool Offset`)**: $C_2 = \min(R_{\text{obligation}} - C_1, B_{\text{reserve}})$
3. **Stage 3 (`Linked Guarantor Debit`)**: $C_3 = \min(R_{\text{obligation}} - C_1 - C_2, B_{\text{guarantor}})$
4. **Stage 4 (`Platform Risk Reserve Isolation`)**: $C_4 = \min(R_{\text{obligation}} - C_1 - C_2 - C_3, B_{\text{platform\_cap}})$, locking the sub-merchant account (`seller_account_locked=True`). Any remaining deficit triggers `UNCOVERED_DEFAULT_EXCEEDS_PLATFORM_RISK_BUFFER`.
