# Enterprise B2B 3-Way Match (`PO == GRN == Invoice`), Split-Shipment Partial Capture Escrow & Dynamic Discounting (`2/10 Net 30`) Guard

**Stage 10 Deliverable — 2026-10-19 Overnight Evolution**

---

## 1. Executive Summary & Architectural Problem Statement

Enterprise B2B procurement agents (operating across UCP B2B Fulfillment, Stripe Invoicing / Connect, and ERP Accounts Payable) face four failure modes absent from simple B2C single-click checkouts:

1. **Premature Backorder Capture (`UNFULFILLED_BACKORDER_CAPTURE_VIOLATION`)**:
   A supplier ships 6 of 10 ordered GPU servers (`Partial ASN`) with 4 on backorder, yet submits an automated capture request for all 10 units—violating Visa/Mastercard delayed-delivery clearing rules and creating uncollateralized buyer credit exposure.
2. **Damaged-Goods Overbilling & Unit Price Drift (`PO == GRN == e-Invoice` 3-Way Mismatch)**:
   Warehouse / telemetry probes record a **Goods Receipt Note (`GRN`)** with `qty_rejected_damaged > 0`, or the supplier's `e-Invoice` inflates `unit_price_minor` above the locked Purchase Order (`PO`) Mandate.
3. **Business Email / MCP Prompt-Injected Beneficiary Hijack (`BEC`) & Sanctions Evasion**:
   An attacker injects a spoofed invoice changing the payout destination (`Stripe Connect acct_*`, `IBAN`, or `USDC` wallet) away from the KYB-verified vendor master record, or routes funds to an OFAC-sanctioned endpoint.
4. **Sub-Optimal Working Capital Timing (`2/10 Net 30` Dynamic Discounting)**:
   Treasury agents either pay on Day 1 without a discount (forfeiting float yield) or pay on Day 30 and miss a `2%` 10-day early-pay discount whose implied annualized return is **$37.24\%$**.

---

## 2. Deterministic Invariants (`lab/b2b_three_way_match_guard.py`)

### 2.1 Split-Shipment Partial Capture & 3-Way Match Equations

For each line item $i \in \text{PO}$:
- **Accepted GRN Quantity**:
  $$Q_{i,\text{accepted}} = \max(0,\; Q_{i,\text{delivered}} - Q_{i,\text{rejected\_damaged}})$$
- **Quantity Ceiling**:
  $$Q_{i,\text{invoiced}} \le Q_{i,\text{accepted}} \le Q_{i,\text{ordered}}$$
  If $Q_{i,\text{invoiced}} > Q_{i,\text{delivered}}$ while $Q_{i,\text{delivered}} < Q_{i,\text{ordered}}$, reject with `UNFULFILLED_BACKORDER_CAPTURE_VIOLATION`. If $Q_{i,\text{invoiced}} > Q_{i,\text{accepted}}$, reject with `THREE_WAY_MATCH_QTY_OVERBILL`.
- **Unit Price Lock (Zero Positive Tolerance)**:
  $$P_{i,\text{invoiced}} \le P_{i,\text{PO}}$$
  Any $P_{i,\text{invoiced}} > P_{i,\text{PO}}$ is rejected with `THREE_WAY_MATCH_UNIT_PRICE_DRIFT`.
- **Ancillary Freight/Tax Corridor**:
  $$A_{\text{invoiced}} \le A_{\text{PO}} \times \left(1 + \frac{\tau_{\text{bps}}}{10000}\right)$$

### 2.2 Dynamic Cash Discounting Implied APR (`evaluate_dynamic_discounting_apr`)

Given early discount rate $d$ (e.g., $2\% = 200\text{ bps}$) if paid by day $T_{\text{disc}}$ (e.g., Day 10) vs. net due day $T_{\text{net}}$ (e.g., Day 30):

$$\text{APR}_{\text{implied}} = \frac{d}{1 - d} \times \frac{365}{T_{\text{net}} - T_{\text{disc}}}$$

For `2/10 Net 30`:
$$\text{APR}_{\text{implied}} = \frac{0.02}{0.98} \times \frac{365}{30 - 10} = 37.2449\%$$

When `three_way_match_verified == True` and $\text{APR}_{\text{implied}} \ge r_{\text{treasury\_hurdle}}$ (e.g., $8.0\%$), the orchestrator schedules early settlement (`ACCELERATE_SETTLEMENT_CAPTURE_DISCOUNT`) on Day $T_{\text{disc}}$ via `x402` or `MPP Tempo`.

---

## 3. Executable Verification

```bash
python -m lab.b2b_three_way_match_guard --json
python -m unittest tests/test_b2b_three_way_match_guard.py -v
```
