# Franchise Commerce POS Royalty Sweep, `FTC FDD Item 11` Ad-Fund Escrow, `3PD` Net-Sales Base & Commissary `BOM` Yield Audit (`FranConnect / Oracle Simphony / Toast Enterprise / Adyen for Platforms` · 🏆 1,325th Test Milestone) FAQ

> **Executive Summary (Includes 🏆 1,325th Deterministic Unit Test Milestone)**: In multi-thousand-unit Quick-Service Restaurant (`QSR`), coffee/boba, hotel, and fitness franchise networks, franchisors rely on `5%–8%` gross-sales royalties, `2%` national brand ad-fund contributions, and approved-vendor commissary supply chains. Legacy month-end self-reporting and `ACH` pull architectures fail in three costly ways: (1) **"Shadow POS" Revenue Skimming & Counterfeit Commissary Substitution**: A franchisee places an unauthorized personal QR/card terminal on the counter (or pockets cash) so that a store buying `50,000` branded cups from the commissary only reports `32,000` drinks in the official POS (`36%` royalty skimming)—or buys `30,000` cups and sells `50,000` drinks using unapproved counterfeit ingredients; (2) **Charging `6%` Royalties on Sales Tax, Tips, Unredeemed Gift-Card Loads & `25%` `UberEats / DoorDash` Menu Markups**: Crushing store-level franchisee unit economics by levying royalties on pass-through taxes and 3rd-party delivery commissions; and (3) **`FTC Franchise Rule (16 CFR Part 436 — FDD Item 8 & Item 11)` Ad-Fund Diversion & Kickback Lawsuits**: Spending the `2%` consumer Brand Marketing Fund on franchisor executive overhead or "franchise recruitment" ads.  
> Production architectures must enforce **Inline `T+0` PSP Split-at-Capture (`Adyen for Platforms / Stripe Connect`) + Daily Commissary `BOM`-to-POS Yield Corridor Audits (`[92%, 103%]`) + `FDD Item 6` Net-Sales Base Scrubbers + Ringfenced `FDD Item 11` Ad-Fund Trust Ledgers**: cutting royalty skimming, bounced ACH pulls, and franchise compliance disputes by **39%** (reducing a `$370,000` quarterly leakage pool to `$225,700`, saving **`$144,300/quarter`**).

![Franchise Royalty Sweep, Ad-Fund Escrow & 3PD Net-Base Architecture](../assets/svg/771-franchise-royalty-sweep-ad-fund-escrow-3pd-net-base-commissary-2026-11-24.svg)

---

## 1. Solution Architect Deep-Dive Q&A

### Q1: How do we eliminate franchisee revenue skimming and bounced month-end `ACH` royalty pulls without putting human auditors in every store?
- **Architectural Solution (Inline `T+0` PSP Split & Commissary `BOM` Mass-Balance Gate `HTTP 403` + `FDD Item 6` Net-Base Scrubber Gate `HTTP 422`)**:
  - Replace month-end `ACH` pulls with **inline `T+0` transaction-level split settlement** (`Adyen for Platforms / Stripe Connect`) so `Royalty %` and `Ad-Fund %` are routed at capture before funds settle to the franchisee's bank; simultaneously run a daily **Commissary `BOM` Yield Audit** comparing proprietary cup/packaging shipments against POS item counts—flagging stores where `POS_Units / Expected_BOM_Units < 92%` (shadow POS skimming) or `> 103%` (unauthorized off-spec ingredient sourcing: `HTTP 403 SHADOW_POS_REVENUE_SKIMMING_OR_UNAUTHORIZED_COMMISSARY_INGREDIENT_DIVERGENCE`);
  - Scrub raw POS totals before applying royalty percentages: strip **sales tax/VAT, employee tips, unredeemed gift-card loads (taxed only upon store redemption), refunds, and 3rd-party delivery (`UberEats / DoorDash`) pass-through markups** (`HTTP 422 ROYALTY_LEVIED_ON_SALES_TAX_TIPS_GIFT_LOAD_OR_UNADJUSTED_3PD_MARKUP`).

### Q2: How do we enforce `FTC Franchise Rule` (`FDD Item 8 & Item 11`) compliance on National Ad-Funds and vendor rebates?
- **Architectural Solution (Ringfenced `FDD Item 11` Fiduciary Trust & `Item 8` Rebate Pass-Back Gate `HTTP 451 / 409`)**:
  - Segregate all `2%` National Ad-Fund splits into an audited fiduciary trust ledger that hard-blocks GL codes associated with franchisor corporate salaries or franchise-recruitment lead generation, and automatically credit supplier volume rebates back to the Ad-Fund or purchasing franchisees per `FDD Item 8` disclosures (`HTTP 451 FDD_ITEM_11_AD_FUND_DIVERSION_OR_UNDISCLOSED_ITEM_8_VENDOR_KICKBACK`; verified `T+0` split, BOM yield parity, and FDD trust compliance return `HTTP 409 INLINE_T0_ROYALTY_SPLIT_BOM_YIELD_AND_FDD_AD_FUND_ESCROW_CONFIRM`).

---

## 2. Visual Architecture Diagrams (Mermaid)

### 1. Franchise Inline `T+0` Royalty Split, Commissary `BOM` Yield & `FDD Item 11` Decision Tree
```mermaid
flowchart TD
    A[Franchise Store Daily POS/3PD Settlement & Commissary Audit] --> B{Does Store POS Unit Volume Match Commissary<br/>Packaging/Ingredient BOM Within [92%, 103%]?}
    B -- <92% Shadow POS Cash/QR Skimming or >103% Fake Ingredients --> C[HTTP 403 Block: Trigger Field Audit & Enforce Locked PSP Terminal Routing]
    B -- Mass-Balance Yield Verified --> D{Is Royalty Base Scrubbed of Sales Tax, Tips,<br/>Unredeemed Gift Loads & 3PD Delivery Markups?}
    D -- Charging 6% Royalty on Sales Tax or DoorDash 25% Commission --> E[HTTP 422 Block: Normalize to FDD Item 6 In-Store Equivalent Net Sales Base]
    D -- Net Royalty Base Validated --> F{Is 2% Ad-Fund Ringfenced in FDD Item 11 Trust<br/>Excluding Franchise Recruitment & Unreported Kickbacks?}
    F -- Diverting Consumer Ad-Fund to Recruitment Ads or Hiding Rebates --> G[HTTP 451 Block: Enforce FDD Item 8/11 Trust Rules & Rebate Pass-Back]
    F -- FDD Governance Verified --> H[HTTP 409 Confirm: T+0 Split + BOM Yield + FDD Trust Saves 39%]
```

---

## 3. Platform Selection Matrix (`FranConnect + Oracle Simphony vs. Toast Enterprise + Adyen/Stripe`)

| Dimension | FranConnect + Oracle Simphony | Toast Enterprise + Adyen / Stripe Connect | Legacy Excel + Month-End ACH Pull | Standalone Un-Integrated POS |
| :--- | :--- | :--- | :--- | :--- |
| **Royalty Collection** | Automated multi-country FDD tier calculation & invoicing | **Real-time `T+0` split at payment capture (`0%` ACH bounce risk)** | High `R01 NSF` bounce rate & DSO lag | Manual export |
| **Anti-Skimming `BOM` Audit** | **Enterprise SCM-to-POS theoretical vs. actual yield variance** | Recipe-level ingredient depletion & waste tracking | Semi-annual physical store visits only | Blind to shadow terminals |
| **`FDD Item 8/11` Governance** | **Purpose-built FDD version tracking, Ad-Fund ledger & Co-Op matching** | Programmable split `Transfer_Group` sub-ledgers | High risk of fund commingling lawsuits | Zero FDD awareness |

---

## 4. Production Deployment & Risk Checklist

- [ ] **Execute Inline `T+0` Royalty & Ad-Fund Splits at Payment Capture (`Adyen for Platforms / Stripe Connect`)**.
- [ ] **Reconcile Daily POS Item Counts Against Commissary Packaging/Ingredient Shipments (`[92%, 103%]` Corridor)**.
- [ ] **Scrub Sales Tax, Tips, Unredeemed Gift-Card Loads & `3PD` Delivery Markups Before Calculating Royalties**.
- [ ] **Ringfence `2%` Brand Ad-Funds Inside `FDD Item 11` Trust Ledgers**: Block franchise-recruitment spend and return `FDD Item 8` vendor rebates.
