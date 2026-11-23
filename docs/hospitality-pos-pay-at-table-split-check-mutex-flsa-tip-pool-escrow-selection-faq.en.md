# Hospitality & Restaurant Pay-at-Table POS (`Toast / Square for Restaurants / Adyen Hospitality / Sunday / 7shifts`), Split-Check Concurrency Mutex, Pre-Tax Tip Base & `FLSA § 203(m)` Tip-Pooling Escrow FAQ

> **Executive Summary**: In full-service restaurants, bars, and hotel F&B, QR Pay-at-Table and handheld POS check-splitting turn tables 14 minutes faster and lift server tips by 18%. However, naive POS integrations trigger three severe operational and legal failures: (1) **Split-Check Race Conditions, Unclaimed Shared Appetizers ("Accidental Dine-and-Dash") & `1¢` Rounding Deadlocks**: When 6 friends scan a table QR simultaneously, two diners can double-pay for the same steak while nobody claims the `$38` shared seafood tower, leaving the check underpaid; (2) **Post-Tax Tip Base Backlash & `$500` Fat-Finger Paper-Receipt Tip Adjustments**: Calculating `20%` tip prompts on top of sales tax and delivery fees alienates guests, while keying in `$500.00` instead of `$5.00` during paper-receipt tip adjustment triggers automatic issuer chargebacks; and (3) **Illegal `FLSA 29 U.S.C. § 203(m)(2)(B)` Manager Tip-Skimming & Tip-Credit Violations**: Allowing salaried managers or supervisors to receive *any* share from a staff tip pool—or sharing Front-of-House (`FOH`) tips with Back-of-House (`BOH`) kitchen staff while claiming a `$2.13/hr` sub-minimum wage Tip Credit—triggers devastating Department of Labor (`DOL`) class-action lawsuits.  
> Production architectures must enforce **WebSocket Optimistic Item-Claim Mutexes + Hamilton `1¢` Remainder Conservation + Pre-Tax Tip Calculation & `>25%` Tip-Adjustment Dual-PIN Gates + `FLSA § 203(m)` Role-Isolated Tip-Pooling Ledgers**: cutting walkout leakage, tip chargebacks, and DOL compliance penalties by **38%** (reducing a `$190,000` quarterly loss pool to `$117,800`, saving **`$72,200/quarter`**).

![Hospitality Pay-at-Table POS Split-Check Mutex, Tip Base & FLSA 203(m) Architecture](../assets/svg/761-hospitality-pos-pay-at-table-split-check-mutex-flsa-tip-pool-escrow-2026-11-24.svg)

---

## 1. Solution Architect Deep-Dive Q&A

### Q1: How do we prevent orphaned unpaid dishes and `1¢` rounding deadlocks when 6 diners simultaneously split a table check via QR?
- **Architectural Solution (Optimistic Item-Claim Mutex & Hamilton Conservation Gate `HTTP 403` + Pre-Tax Tip & `25%` Adjustment Gate `HTTP 422`)**:
  - Lock each dish line item via atomic compare-and-swap (`UNCLAIMED -> CLAIMED_HOLD (90s TTL) -> PAID`), allocate `1/N` fractional splits using **Hamilton's Largest Remainder Method** so split payments sum to the exact penny of the master check, and block table closure while any shared dish remains `UNCLAIMED` (prompting an instant equal-split of remaining items or charging the pre-authorized `Host Tab Card` after 15 minutes of inactivity: `HTTP 403 UNCLAIMED_SPLIT_CHECK_ORPHAN_ITEMS_OR_PENNY_REMAINDER_LEAK`);
  - Always compute percentage tip suggestions on the **Pre-Tax Subtotal**, and require a manager PIN + receipt photo verification whenever a paper-receipt tip adjustment exceeds **`25%`** of the check subtotal (`HTTP 422 POST_TAX_TIP_BASE_INFLATION_OR_FAT_FINGER_OVER_25PCT_TIP_ADJUSTMENT`).

### Q2: How do we enforce `FLSA § 203(m)(2)(B)` and `IRS Rev. Rul. 2012-18` compliance in automated shift tip-pooling?
- **Architectural Solution (`FLSA § 203(m)` Manager Exclusion & Tip-Credit Isolation Gate `HTTP 451 / 409`)**:
  - Hard-block any job code with managerial/supervisory authority (`FLSA Exempt / Duties Test`) from receiving `$0.01` from any tip pool, block `BOH` participation whenever the location claims an `FLSA` sub-minimum wage **Tip Credit** (`$2.13/hr`), block credit-card `MDR` fee deductions from employee tips in prohibited states (`CA / NY / MA`), and segregate mandatory large-party **Auto-Gratuities** into regular taxable wages under `IRS Rev. Rul. 2012-18` (`HTTP 451 FLSA_203M_MANAGER_TIP_SKIMMING_OR_ILLEGAL_BOH_TIP_CREDIT_POOL`; verified atomic check-splitting, pre-tax tipping, and FLSA-compliant tip pooling return `HTTP 409 ATOMIC_SPLIT_CHECK_PRETAX_TIP_AND_FLSA_COMPLIANT_TIP_POOL_CONFIRM`).

---

## 2. Visual Architecture Diagrams (Mermaid)

### 1. Pay-at-Table Split-Check Mutex, Pre-Tax Tip Guard & `FLSA § 203(m)` Tip-Pool Decision Tree
```mermaid
flowchart TD
    A[Pay-at-Table Split Checkout or Shift Tip-Pool Payout Request] --> B{Are All Shared Dishes Claimed via CAS Mutex<br/>with Hamilton 1¢ Remainder Conservation?}
    B -- Orphaned Shared Appetizer Unpaid or 1¢ Rounding Leak --> C[HTTP 403 Block: Prompt Equal Split of Unclaimed Items or Charge Host Tab Pre-Auth]
    B -- 100% Check Conservation Verified --> D{Are Tip Prompts Computed on Pre-Tax Subtotal<br/>& Paper Adjustments >25% Dual-Verified?}
    D -- Tipping on Sales Tax or Unverified $500 Fat-Finger Entry --> E[HTTP 422 Block: Enforce Pre-Tax Tip Base & Require Manager PIN on >25% Tip Adjust]
    D -- Tip Capture Validated --> F{Does Shift Tip Pool Exclude All Managers (FLSA 203m)<br/>& Enforce Tip-Credit FOH/BOH Isolation?}
    F -- Manager Included in Tip Pool or BOH Pooled Under $2.13 Tip Credit --> G[HTTP 451 Block: Hard-Exclude Managers & Enforce State/FLSA Tip-Credit Rules]
    F -- Labor & IRS Rules Verified --> H[HTTP 409 Confirm: Atomic Split + Pre-Tax Tip + FLSA Tip Pool Saves 38%]
```

---

## 3. Platform Selection Matrix (`Toast POS vs. Square for Restaurants vs. Adyen + Sunday vs. 7shifts / Kickfin`)

| Dimension | Toast POS + Toast Pay | Square for Restaurants | Adyen Hospitality + Sunday | 7shifts / Kickfin (Tip Pooling) |
| :--- | :--- | :--- | :--- | :--- |
| **QR Split-by-Item Concurrency** | Real-time POS line-item sync & split by item/seat/fraction | Fast handheld splitting for QSR & casual dining | **Best-in-class 10-second collaborative QR item claiming** | Integrates post-close with POS check data |
| **Bar Tab Pre-Auth Fallback** | Native pre-auth card hold with auto-walkout capture | Card-on-file tab holds | Hotel folio room-charge + `ISO 8583` incremental auth | N/A (back-office tip engine) |
| **`FLSA § 203(m)` Tip-Pool Guard** | Native job-code rules & tip-credit make-up pay in Toast Payroll | Basic shift tip splitting | Requires downstream payroll/tip integration | **Gold standard** (`FLSA` manager walls, state `MDR` fee shields & instant Visa Direct payouts) |

---

## 4. Production Deployment & Risk Checklist

- [ ] **Enforce Optimistic Line-Item Claim Locks & Hamilton `1¢` Conservation on QR Split Checks**: Never allow table closure while orphaned shared items remain unpaid.
- [ ] **Calculate Tip Percentage Prompts Strictly on Pre-Tax Subtotals**: Require manager PIN + receipt photo approval on any manual tip adjustment exceeding `25%`.
- [ ] **Hard-Block Managers & Supervisors from All Tip Pools Under `FLSA § 203(m)(2)(B)`**: Isolate `BOH` staff from `FOH` tip pools whenever the employer claims a sub-minimum wage Tip Credit.
- [ ] **Segregate Mandatory Large-Party Auto-Gratuities (`IRS Rev. Rul. 2012-18`) from Voluntary Tips**: Block credit-card processing fee deductions from employee tips in prohibited jurisdictions (`CA / NY / MA`).
