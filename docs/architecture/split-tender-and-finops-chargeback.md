# Split-Tender Reverse Refund Waterfall, Anti-Cash-Out Laundering & Enterprise Multi-Cost-Center Pre-Auth Encumbrance Architecture

**Stage 12 Deliverable — 2026-10-19 Overnight Evolution**

---

## 1. Executive Summary & Architectural Problem Statement

When consumer or enterprise shopping agents combine multiple payment instruments (`Split-Tender`: promotional coupons + closed-loop gift cards / loyalty points + open-loop Stripe `SPT` cards / `x402` USDC) or allocate procurement spend across multiple corporate cost centers, two high-severity financial exploits emerge:

1. **Closed-Loop Gift Card / Loyalty Cash-Out Laundering & Earn-Then-Return Double-Spend**:
   - *Cash-Out Laundering (`CLOSED_LOOP_CASH_OUT_LAUNDERING_BLOCKED`)*: A buyer pays `$500` using a `$350` closed-loop gift card, `$50` promo coupon, and `$100` on an open-loop card/USDC wallet, then immediately triggers a `$450` refund directed entirely (`$450`) to the open-loop card/USDC rail—converting non-transferable closed-loop store credit into liquid cash.
   - *Earn-Then-Return Clawback Deficit (`LOYALTY_EARN_CLAWBACK_DEFICIT`)*: A buyer's secondary agent immediately redeems loyalty points earned on Order A before returning Order A for a full refund.
2. **Concurrent Multi-Agent Departmental Budget Race Conditions (`COST_CENTER_ENCUMBRANCE_EXCEEDED`)**:
   - When multiple departmental agents check `actual_spent < budget_cap` concurrently without atomic pre-authorization **Encumbrance** (`available = budget_cap - existing_encumbrance - actual_spent`), parallel requisitions breach the cost center's hard budget ceiling or fail to book LLM reasoning token overhead (`6150-Agent-Token-Overhead`) into the ERP General Ledger (`GL`).

---

## 2. Deterministic Invariants (`lab/split_tender_finops_guard.py`)

### 2.1 Split-Tender Forward & Reverse Waterfall Equations

- **Forward Tender Conservation**:
  $$D_{\text{promo}} + T_{\text{closed\_loop}} + C_{\text{captured\_open\_loop}} = G_{\text{order}}$$
- **Open-Loop Refund Ceiling (Anti-Cash-Out Invariant)**:
  $$R_{\text{open\_loop}} \le C_{\text{captured\_open\_loop}}, \qquad R_{\text{total}} \le T_{\text{closed\_loop}} + C_{\text{captured\_open\_loop}}$$
  Promotional discounts ($D_{\text{promo}}$) are strictly non-refundable (`PROMO_DISCOUNT_CASH_REFUND_BLOCKED`).
- **Loyalty Earn Vesting & Clawback Conservation**:
  $$L_{\text{redeemed\_unvested}} \le L_{\text{clawback\_deducted}}$$

### 2.2 Multi-Cost-Center Pre-Auth Encumbrance & Balanced Double-Entry GL

For requisition total $C_{\text{total}} = C_{\text{merchandise}} + C_{\text{tax}} + C_{\text{token\_overhead}}$ allocated across cost centers $k \in \{1,\dots,M\}$ with basis points $\sum_{k=1}^M b_k = 10000\text{ bps}$:

$$\text{Share}_k \le \text{BudgetCap}_k - \text{Encumbrance}_k - \text{ActualSpent}_k$$

$$\sum_{k=1}^M \text{Debit}(\text{CC}_k) = \text{Credit}(\text{2100-AP-Clearing}) = C_{\text{total}}$$

---

## 3. Executable Verification & 7-Card Benchmark Report

```bash
python -m lab.split_tender_finops_guard --output-dir reports/agentic-commerce-enterprise-procurement-bench
python -m unittest tests/test_split_tender_finops_guard.py -v
```
