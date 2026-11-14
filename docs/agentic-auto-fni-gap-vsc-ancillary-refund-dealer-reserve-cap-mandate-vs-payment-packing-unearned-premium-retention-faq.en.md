# Agentic Auto `F&I` (`GAP Waiver, VSC Extended Warranty & Dealer Reserve`), Early-Payoff `Pro-Rata` Unearned Premium Refund & Dealer Markup Cap Settlement Architecture: Automated Payoff-Offset Lock, Low-`LTV` Anti-Packing Gate & `CFPB / State Statute` Token (`agentic_auto_fni_gap_vsc_ancillary_refund_dealer_reserve_cap_mandate_...`) vs. Retaining `$2,100` Unearned Refunds, Selling Worthless `GAP` on `65% LTV` Loans & `250 bps` Dealer Rate Markups: Architecture Selection & First-Principles FAQ

> **Document Type**: Solution Architect Selection Guide & First-Principles FAQ (modeled after `ib-vs-ethernet-roce-selection-faq.md`)  
> **Reading Time**: ~12 minutes | **Target Audience**: AI Solution Architects, Captive Auto Finance & Bank Auto Lending Risk VPs (`Toyota Financial / Ally / Chase Auto / Capital One`), Automotive Dealership Group Compliance Directors, `CFPB / ECOA` Regulatory Counsel & Lending FinOps Engineers  
> **Core Thesis**: First explain in plain language why over **65% of 72-month auto loans** terminate early around month 30 via trade-in, refinancing, or total-loss insurance payoff—entitling the borrower to a **`$1,500–$2,400` pro-rata refund of unearned `VSC` (Vehicle Service Contract) and `GAP` (Guaranteed Asset Protection) premiums**—yet legacy dealerships and administrators pocket billions in unearned premiums by forcing consumers to navigate a manual paper cancellation maze (triggering massive **`CFPB UDAAP` enforcement actions and state AG consent decrees**); why F&I managers sell `$1,200` `GAP` waivers to high-down-payment buyers (`LTV = 65%`) who can mathematically never be underwater; and why dealers mark up the lender's wholesale `Buy Rate` by `250 bps` (`Dealer Reserve`) while packing `$699` phantom `VIN Etching` and nitrogen-tire add-ons into the monthly payment. Then derive from first principles how **`agentic_auto_fni_gap_vsc_ancillary_refund_dealer_reserve_cap_mandate_...` + Microsoft Web IQ `/v3/browse` verification of state automatic GAP/VSC refund statutes (`CA AB 2311 / CO HB 22-1188 / TX / MA`), `FTC / CFPB` disclosure rules, and `NADA / Black Book` LTV valuations + automated loan-payoff `Pro-Rata` dealer-commission clawback locks + `LTV >= 80%` GAP & `<= 100 bps` dealer reserve gates** eliminate unearned premium retention and payment packing within 10ms–275ms.

---

## 📌 1. Executive Summary (30-Second Architect's Guide)

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  🔥 Core Architectural Law: Never allow an Auto Lending Agent to close an early loan payoff without automatically│
│  crediting pro-rata unearned GAP/VSC premiums & clawing back the dealer's unearned 70% commission share!         │
│  The only safe Auto F&I pattern = Automated Payoff Pro-Rata Clawback + LTV>=80% GAP Gate + <=100bps Reserve Cap  │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

1. **Why is Automotive `F&I` (`GAP, VSC & Dealer Reserve`) the #1 Target of `CFPB` Enforcement and `$3,500–$7,000/Vehicle` Consumer Leakage?**
   - **Withholding Unearned `GAP` & `VSC` Premiums Upon Early Loan Payoff**: When a borrower finances `$4,400` of 72-month `VSC` and `GAP` contracts and pays off or trades in the vehicle at month 36, roughly `50%` (`$2,200`) of the coverage period is unused. Because the dealer kept **70%** of the retail price upfront as commission (`$3,080`), dealers obstruct cancellations to avoid returning their `$1,540` unearned commission—exposing the indirect auto lender to `CFPB UDAAP` liability and statutory treble damages under state laws like **California `AB 2311`**.
   - **Selling Worthless `GAP` Waivers on Low-`LTV` Loans & "Payment Packing"**: `GAP` only covers the negative-equity gap between loan balance and Actual Cash Value (`ACV`). When a borrower puts `30%–35%` down (`LTV <= 70%`), the loan is never underwater—making the `GAP` waiver mathematically worthless (`0%` claim probability). Dealers also pack `$699` window `VIN etching` (`$5` stencil cost) into quoted monthly payments without base-payment comparison disclosures.
   - **Discretionary `250 bps` Dealer Rate Markups (`Dealer Reserve`)**: Marking up a borrower's wholesale `5.49%` `Buy Rate` to `7.99%` creates severe `ECOA` disparate-impact liability and inflates early-default risk.
2. **How Does the Agentic Auto `F&I` Settlement Architecture Solve This?**
   - **Lock 1: Automated Early-Payoff `Pro-Rata` Refund Credit & Dealer Commission Clawback Lock**: Loan payoffs (trade-in, refinance, repossession, or total loss) that fail to automatically calculate and credit the borrower's `Pro-Rata` unearned `GAP / VSC` refund—simultaneously clawing back the dealer's proportional unearned commission from the `Dealer Reserve Holdback` account—or that apply punitive `Rule of 78s` formulas are blocked in **11ms** with `HTTP 403 UNEARNED_GAP_VSC_PRO_RATA_REFUND_WITHHOLDING_OR_RULE78_PENALTY_BLOCKED`.
   - **Lock 2: `LTV >= 80%` `GAP` Eligibility Gate + Dual-Payment Anti-Packing & `<= 100 bps` Reserve Cap**: Origination packets selling `GAP` on loans with `LTV < 80%`, packing unverified `$699` `VIN Etch / Nitrogen` add-ons without dual base-vs-packed payment signatures, or marking up `Buy Rate` by `> 100 bps` are rejected in **14ms** with `HTTP 422 WORTHLESS_LOW_LTV_GAP_WAIVER_OR_PAYMENT_PACKING_AND_EXCESS_DEALER_RESERVE`.
   - **Lock 3: Microsoft Web IQ `/v3/browse` State Auto Refund Statute (`CA AB 2311 / CO HB 1188`) & `FTC` Rule Verification**: Violations of state statutory refund timelines, cancellation fee caps (`<= $25` or `$0`), or mandatory cash-price disclosures trigger `HTTP 451 STATE_AUTO_FNI_REFUND_STATUTE_OR_FTC_CARS_RULE_DISCLOSURE_VIOLATION_HOLD` in **275ms**.

---

## 🎯 2. First-Principles Q&A for Architects & Auto Finance Risk Leaders

### Q1: How does the agent execute an instant split-clawback between the VSC Administrator (`30%` share) and the Dealership (`70%` share) when a loan pays off early?

- **Plain-Language Mechanics**:
  - Suppose a borrower buys a 72-month / 75,000-mile `VSC` for $P_{\text{retail}} = \$3,000$, where the Administrator retains $P_{\text{admin}} = \$900$ (`30%`) and the Dealer retains $C_{\text{dealer}} = \$2,100$ (`70%`).
  - At early payoff ($t = 36\text{ months}$, $\Delta M = 30,000\text{ miles}$), the unused time/mileage factor is:
    $$u = \min\left(\frac{72 - 36}{72}, \; \frac{75,000 - 30,000}{75,000}\right) = \min(0.50, 0.60) = 0.50$$
  - The borrower is owed $R_{\text{total}} = 0.50 \times \$3,000 = \$1,500$. The agent debits `$450` (`0.50 × $900`) from the Administrator via API and debits `$1,050` (`0.50 × $2,100`) directly from the dealership's monthly ACH reserve settlement pool—applying the full `$1,500` credit to the borrower's payoff balance in **240ms** via `HTTP 409 AUTOMATED_EARLY_PAYOFF_PRO_RATA_REFUND_AND_RESERVE_CAP_SAVINGS_CONFIRM`.

### Q2: Why choose **Microsoft Web IQ** over Exa or Bright Data for state `GAP / VSC` statutory refund rules (`CA AB 2311`), `CFPB Supervisory Highlights` enforcement criteria, and `NADA / Black Book` LTV checks?

| Dimension | Microsoft Web IQ (`/v3/browse` + Search Grounding) | Exa (Neural Search API) | Bright Data (Scraper / Unlocker) |
| :--- | :--- | :--- | :--- |
| **State `GAP/VSC` Refund Statutes (`CA AB 2311 / CO / TX`) & Cancellation Fee Caps** | **Very High**: Deterministic extraction of state-by-state `Pro-Rata` mandates, `Rule of 78s` bans, and `VIN` wholesale book values with `domain_allowlist` | **Medium**: Often conflates older pre-reform state statutes with current automatic-refund laws | **High**: Can scrape state codes, but requires custom parsers across 50 state legislative portals |
| **Integration with Core Loan Payoff Quote & Dealer Reserve Clawback** | **Native**: Directly feeds state refund formulas and `LTV` caps into `agentic_auto_fni_gap_vsc_...` | **None**: No auto-loan servicing or F&I clawback engine | **None**: Raw HTML/JSON proxy transport only |
| **P95 Latency** | **240ms–275ms** (**10ms–14ms** on policy cache hit) | 850ms–1,700ms | 2,300ms–5,600ms |

---

## 🧭 3. Visual Architecture Diagrams (Mermaid Decision Tree, Path Comparison & Sequence)

### 3.1 Auto `F&I` Origination & Early-Payoff `Pro-Rata` Refund Decision Tree

```mermaid
flowchart TD
    A["Incoming Auto F&I Origination or Early-Payoff Batch<br/>(e.g., $590,000 Monthly Dealer F&I & Payoff Settlement)"] --> B{"1. Early Payoffs Credit 100% Pro-Rata<br/>Unearned GAP/VSC + Dealer Clawback?"}
    B -- "Unearned GAP/VSC Refund Withheld<br/>or Punitive Rule of 78s Formula Applied" --> C["HTTP 403: UNEARNED_GAP_VSC_PRO_RATA_REFUND_WITHHOLDING_OR_RULE78_PENALTY_BLOCKED<br/>11ms Hard Block"]
    B -- "Pro-Rata Refunds & Clawbacks Verified" --> D{"2. GAP Sold Only on LTV >=80% &<br/>Dealer Reserve <=100 bps (No Packing)?"}
    D -- "Worthless GAP on 65% LTV Loan, $699 VIN Etch<br/>Packing, or 250 bps Rate Markup" --> E["HTTP 422: WORTHLESS_LOW_LTV_GAP_WAIVER_OR_PAYMENT_PACKING_AND_EXCESS_DEALER_RESERVE<br/>14ms Reject Packing / Rate Markup"]
    D -- "LTV, Add-Ons & Reserve Verified" --> F{"3. Web IQ Verifies State Refund Statute<br/>(CA AB 2311) & FTC Disclosure Rules?"}
    F -- "Breach of State Automatic-Refund Deadline<br/>or Missing Dual Base/Packed Payment Signature" --> G["HTTP 451: STATE_AUTO_FNI_REFUND_STATUTE_OR_FTC_CARS_RULE_DISCLOSURE_VIOLATION_HOLD<br/>275ms Consumer-Protection Hold"]
    F -- "State Statutes & Disclosures Clean" --> H{"4. Automated Early-Payoff Commission Clawback<br/>or Reserve Cap Strip Applicable?"}
    H -- "Yes ($47,200 Refund Clawback & Reserve Strip)" --> I["HTTP 409: AUTOMATED_EARLY_PAYOFF_PRO_RATA_REFUND_AND_RESERVE_CAP_SAVINGS_CONFIRM<br/>240ms Confirm $542,800 Net"]
    H -- "No (Exact Compliant Net)" --> J["HTTP 200: VERIFIED_AUTO_FNI_GAP_VSC_SETTLED<br/>10ms Auto-Settle $590,000"]
```

### 3.2 Legacy F&I Payment Packing & Refund Obstruction vs. Agentic `Pro-Rata` Escrow

```mermaid
flowchart LR
    subgraph Legacy["❌ Legacy F&I Payment Packing & Manual Refund Maze ($4,500 Loss + CFPB Fines)"]
        L1["Sell Worthless GAP on 65% LTV<br/>+ Pack $699 VIN Etch & +250 bps Rate"] --> L2["Borrower Pays Off Early at Month 30;<br/>Dealer Keeps $2,100 Unearned Premium"]
    end

    subgraph Agentic["✅ Web IQ + Automated Payoff Pro-Rata Clawback + LTV/Reserve Lock"]
        A1["Hard Block GAP When LTV < 80%<br/>+ Cap Dealer Reserve at <=100 bps"] --> A2["Instant Payoff Pro-Rata Credit +<br/>70% Dealer Commission ACH Clawback"]
    end
```

### 3.3 End-to-End Sequence Diagram

```mermaid
sequenceDiagram
    participant Dealer as Auto Dealership F&I & VSC Administrator
    participant Agent as Lender Agentic F&I & Payoff Engine
    participant Core as Loan Servicing Core (Payoff / LTV / Reserve Pool)
    participant WebIQ as Microsoft Web IQ (/v3/browse)
    participant Borrower as Borrower Payoff / Dealer ACH Rail

    Dealer->>Agent: Submit Monthly F&I Origination & Early-Payoff Batch ($590,000 Total)
    Agent->>Core: 1. Audit Early-Payoff Loans for Automatic Pro-Rata GAP/VSC Refund & Dealer Clawback
    alt Early Payoff Omitted $2,100 Unearned Refund or Applied Punitive Rule of 78s
        Core-->>Agent: Unearned Premium Retained / Rule of 78s Violation
        Agent-->>Dealer: HTTP 403 UNEARNED_GAP_VSC_PRO_RATA_REFUND_WITHHOLDING_OR_RULE78_PENALTY_BLOCKED (11ms)
    else Payoff Refunds Verified; Audit New Originations for LTV, Add-On Packing & Reserve Cap
        Agent->>Core: 2. Check Loan LTV (65% vs 80% Floor), $699 VIN Etch & Rate Markup (250 vs 100 bps)
        alt Worthless GAP on 65% LTV Loan, Payment Packing, or 250 bps Dealer Reserve
            Agent-->>Dealer: HTTP 422 WORTHLESS_LOW_LTV_GAP_WAIVER_OR_PAYMENT_PACKING_AND_EXCESS_DEALER_RESERVE (14ms)
        else Verify State Auto Refund Statutes (CA AB 2311 / CO HB 1188) & FTC Disclosures
            Agent->>WebIQ: 3. /v3/browse Check State Automatic-Refund Statutes & Cancellation Fee Caps
            alt Statutory Refund Window Breached or Missing Dual-Payment Disclosure
                WebIQ-->>Agent: CA AB 2311 / FTC Disclosure Violation Detected
                Agent-->>Dealer: HTTP 451 STATE_AUTO_FNI_REFUND_STATUTE_OR_FTC_CARS_RULE_DISCLOSURE_VIOLATION_HOLD (275ms)
            else Claw Back $47,200 Unearned Dealer Commissions & Excess Rate Reserve
                WebIQ-->>Agent: Net Dealer Settlement Adjusted to $542,800.00
                Agent-->>Borrower: HTTP 409 Confirm ($542,800) or HTTP 200 Auto-Settle ($590,000)
            end
        end
    end
```

---

## 📊 4. Architect's Selection Decision Matrix

| Architecture Option | Early-Payoff `GAP/VSC` Refund Enforcement | Defense Against Low-`LTV` Worthless `GAP` & Packing | `Dealer Reserve` Markup & `ECOA / CFPB` Protection | Recommended Fit |
| :--- | :--- | :--- | :--- | :--- |
| **Option A: Consumer Must Visit Dealership to Request Refund** | ❌ <15% recovery; triggers massive `CFPB UDAAP` fines | ❌ 0% (dealers sell `GAP` on `60% LTV` loans) | ❌ Uncapped `250 bps` markups create `ECOA` liability | High regulatory enforcement risk |
| **Option B: Lender Fronts Refund Without Dealer ACH Clawback** | ⚠️ Protects borrower, but lender loses the dealer's `70%` share | ⚠️ Post-funding audit only | ⚠️ Manual rate-exception reviews | Small credit unions |
| **Option C (Recommended): Web IQ + `agentic_auto_fni_gap_vsc_...` + Payoff Clawback + `LTV` Gate** | ✅ **100% automated payoff credit + `70%` dealer ACH clawback** | ✅ **Hard `LTV < 80%` `GAP` block + dual-payment lock** | ✅ **`<=100 bps` flat reserve cap + 275ms state statute check** | **Captive Auto Finance, National Auto Lenders, Credit Unions & Franchise Dealer Groups** |

---

## 🧪 5. Quantitative Benchmark & 7-Card Report Summary

Evaluated in the deterministic offline suite (`lab/webiq_commerce_demo.py`) for a `$590,000.00` monthly automotive `F&I` origination and early-payoff refund settlement batch:

| Case | Scenario & Perturbation | Action Pill | HTTP Status | Latency | Settled / Blocked Amount | Provenance |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Case 1** | Automated `Pro-Rata` payoff refund + `LTV >= 80%` `GAP` + `<=100 bps` reserve & statute clean | `Act automatically` | `200 OK` | `10 ms` | `$590,000.00` | `deterministic_offline_simulation` |
| **Case 2** | Withheld unearned `GAP/VSC` refund on early payoff or punitive `Rule of 78s` deduction | `Send to a human` | `403 Forbidden` | `11 ms` | `$0.00` (`$590k` blocked) | `synthetic_policy` |
| **Case 3** | Worthless `GAP` on `65% LTV` loan, `$699` `VIN Etch` packing, or `250 bps` rate markup | `Send to a human` | `422 Unprocessable` | `14 ms` | `$0.00` (packing blocked) | `deterministic_offline_simulation` |
| **Case 4** | State automatic-refund statute (`CA AB 2311 / CO HB 1188`) or `FTC` disclosure violation | `Send to a human` | `451 Unavailable` | `275 ms` | `$0.00` (statutory hold) | `official_doc_snapshot` |
| **Case 5** | Web IQ automated early-payoff `Pro-Rata` dealer clawback & reserve cap strip (`-$47,200.00`) | `Confirm` | `409 Conflict` | `240 ms` | `$542,800.00` | `official_doc_snapshot` |

---

## 🛠️ 6. Production Readiness Checklist

- [ ] **Embed Automated `Pro-Rata` `GAP / VSC` Refund Credits & `70%` Dealer ACH Clawbacks into Core Loan Payoff Quotes**: Automatically offset unearned ancillary premiums at early payoff, refinance, or total loss without requiring consumer visits to the dealership.
- [ ] **Enforce a Hard `LTV >= 80%` Origination Floor for `GAP` Waivers**: Block `GAP` financing when borrower down payments or trade-in equity eliminate negative-equity exposure.
- [ ] **Cap Dealer Rate Participation (`<= 100 bps`) & Require Dual Base-vs-Packed Monthly Payment Signatures**: Prevent payment packing and `ECOA` disparate-impact pricing.
- [ ] **Enable Microsoft Web IQ `/v3/browse` 50-State Auto `F&I` Statute Verification**: Continuously enforce state-specific `Pro-Rata` mandates (`CA AB 2311`, `CO HB 22-1188`) and cancellation fee ceilings.
