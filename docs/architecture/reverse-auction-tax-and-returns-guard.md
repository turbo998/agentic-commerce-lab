# Sealed-Bid Vickrey Reverse Auction (`Commit-Reveal RFQ`), Cross-Border B2B VAT Reverse-Charge & Post-Purchase RMA Bilateral Guard

**Stage 11 Deliverable — 2026-10-19 Overnight Evolution**

---

## 1. Executive Summary & Architectural Problem Statement

When a buyer's procurement agent negotiates across multiple competing merchant MCP endpoints, computes indirect taxes across jurisdictions, and manages post-purchase returns (`RMA`), three adversarial failure modes arise:

1. **Sequential Bid Sniping, Collusion & Checkout Bait-and-Switch in Multi-Seller RFQs**:
   Plaintext sequential polling allows later sellers to underbid by `$0.01` or collude, and unscrupulous sellers quote a low headline price during RFQ only to inject hidden `"platform activation / handling surcharges"` at Checkout (`BAIT_SWITCH_SURCHARGE_INJECTION`).
2. **Cross-Border B2B VAT Over-Collection & Unregistered Tax Nexus**:
   When a cross-border B2B buyer presents a verified VAT registration (`seller_country != buyer_country`, e.g., `DE -> FR` Intra-EU B2B), statutory tax law requires `0%` **Reverse-Charge** treatment. Naive checkout flows either overcharge standard 20% VAT (`INVALID_B2B_VAT_REVERSE_CHARGE_OVERCOLLECTION`) or permit sellers without valid local tax nexus registration (`seller_tax_registration_valid = False`) to collect unremitted sales tax (`UNREGISTERED_TAX_COLLECTION_BLOCKED`).
3. **Post-Purchase RMA Asymmetry (Predatory Restocking Fees vs. Empty-Box Swap Fraud)**:
   - *Merchant Abuse*: Deducting a 15% restocking fee on a defective or Significantly Not As Described (`DEFECTIVE_OR_SNAD`) return (`ILLEGAL_SNAD_RESTOCKING_FEE_BLOCKED`), or charging a remorse restocking fee higher than the cap disclosed in the UCP catalog snapshot (`UNDISCLOSED_RESTOCKING_FEE_TRAP`).
   - *Buyer Return Fraud*: Returning a counterfeit/swapped hardware serial number or an empty box whose net weight deviates beyond carrier tolerance (`RMA_SERIAL_OR_WEIGHT_FRAUD_BLOCKED`).

---

## 2. Deterministic Invariants (`lab/reverse_auction_tax_returns_guard.py`)

### 2.1 Cryptographic Commit-Reveal Second-Price (Vickrey) RFQ

1. **Phase 1 (`COMMIT`)**: Each seller $i \in \{1,\dots,K\}$ submits commitment hash:
   $$H_i = \text{SHA256}\!\left(\text{seller\_id}_i \;\|\; \text{rfq\_id} \;\|\; P_{\text{all\_in},i} \;\|\; \text{salt}_i\right)$$
2. **Phase 2 (`REVEAL` & Vickrey Clearing)**:
   - Any bid failing $H_i$ verification is rejected (`RFQ_COMMIT_REVEAL_HASH_MISMATCH`).
   - Qualifying bids satisfy $P_{\text{all\_in},i} \le P_{\text{reserve}}$.
   - Lowest bidder $i^* = \arg\min_i P_{\text{all\_in},i}$ wins, with incentive-compatible Vickrey ceiling:
     $$P_{\text{vickrey\_cap}} = \min\!\left(P_{(2)},\; P_{\text{reserve}}\right)$$
   - At checkout, any pre-tax total $C_{\text{pre\_tax}} > P_{\text{all\_in},i^*}$ triggers `BAIT_SWITCH_SURCHARGE_INJECTION`.

### 2.2 Cross-Border B2B VAT Reverse-Charge & Tax Nexus Rules

- **Unregistered Tax Collection Block**:
  $$\text{tax\_charged} > 0 \;\land\; \neg\text{seller\_tax\_registration\_valid} \implies \text{UNREGISTERED\_TAX\_COLLECTION\_BLOCKED}$$
- **Cross-Border B2B Reverse-Charge**:
  $$\text{buyer\_is\_b2b} \;\land\; \text{buyer\_vat\_verified} \;\land\; (\text{seller\_country} \ne \text{buyer\_country}) \implies T_{\text{expected}} = 0$$

### 2.3 Bilateral RMA Return Guard (`verify_rma_return_and_restocking_guard`)

- **Hardware Serial & Carrier Net-Weight Verification**:
  $$\text{SHA256}(\text{serial}_{\text{returned}}) = \text{SHA256}(\text{serial}_{\text{shipped}}) \;\land\; \left|W_{\text{returned}} - W_{\text{shipped}}\right| \le \Delta W_{\text{tol}}$$
- **SNAD Zero-Restocking Invariant**:
  $$\text{reason} = \text{DEFECTIVE\_OR\_SNAD} \implies F_{\text{restock}} = 0$$

---

## 3. Executable Verification

```bash
python -m lab.reverse_auction_tax_returns_guard --json
python -m unittest tests/test_reverse_auction_tax_returns_guard.py -v
```
