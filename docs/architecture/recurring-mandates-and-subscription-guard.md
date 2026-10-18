# Recurring Mandates, Free-Trial Dark-Pattern Trap Defense & Atomic 3-Layer Revocation Architecture

**Stage 9 Deliverable — 2026-10-19 Overnight Evolution**

---

## 1. Executive Summary & Architectural Problem Statement

When autonomous shopping agents procure B2C/B2B SaaS seats, API subscriptions, or scheduled replenishment orders, two severe financial hazards arise that classic single-checkout guardrails fail to prevent:

1. **Negative-Option Billing & Free-Trial Auto-Conversion Traps**:
   A deceptive merchant advertises a `"$0.00 7-day free trial"` (or `"$0.99 intro offer"`) in the human-facing summary while embedding a 12-month minimum commitment (`min_commitment_cycles = 12` at `$199.00/mo`) plus a `$150.00` early termination fee (`ETF`) and a predatory 72-hour pre-expiration cancellation cutoff inside the machine-readable billing contract. A naive shopping agent that checks only `initial_charge_minor <= mandate.max_amount_minor` approves the `$0.00` checkout and silently binds the principal to `$2,538.00` in unbudgeted liability.
2. **Post-Revocation "Zombie MIT Charges"**:
   When a buyer or enterprise governance engine revokes a recurring mandate, canceling only the local agent schedule leaves the downstream Stripe Shared Payment Token (`SPT`) / Card Network Token (`VTS`/`MDES`) or Stripe Billing subscription active, enabling merchants to continue firing `Merchant-Initiated Transactions (MIT)` after revocation.

---

## 2. Invariant 1: Total Committed Contract Value (`TCCV`) & Negative-Option Guard

### 2.1 Worst-Case Liability Formula

For any offer where `billing_interval != "one_time"`, `recurring_charge_minor > 0`, or `(trial_days > 0 and auto_convert == True)`, the Policy Broker computes the **Total Committed Contract Value (`TCCV`)** before authorizing even a `$0.00` initial trial:

$$\text{TCCV} = C_{\text{initial}} + \max(N_{\text{min\_commit}}, 1) \times C_{\text{recurring}} + F_{\text{ETF}}$$

where:
- $C_{\text{initial}}$ (`initial_charge_minor`): Immediate signup or trial activation fee;
- $N_{\text{min\_commit}}$ (`min_commitment_cycles`): Minimum non-cancelable billing cycles;
- $C_{\text{recurring}}$ (`recurring_charge_minor`): Per-cycle recurring price after trial conversion;
- $F_{\text{ETF}}$ (`early_termination_fee_minor`): Penalty for breaking commitment prior to $N_{\text{min\_commit}}$.

### 2.2 Five Deterministic Pre-Authorization Invariants (`verify_subscription_trial_and_recurring_mandate`)

| # | Invariant | Rejection Code | Architectural Defense |
|---|---|---|---|
| 1 | **Summary vs. Machine Recurring Disclosure** | `SUMMARY_HIDES_NEGATIVE_OPTION_RENEWAL` | Blocks prompt-injected or dark-pattern offers where machine terms specify recurring/auto-convert billing omitted from the human summary. |
| 2 | **Explicit Recurring Mandate Consent** | `NEGATIVE_OPTION_MANDATE_MISMATCH` | Rejects any recurring or auto-converting trial offer when `mandate.allow_recurring != True`. |
| 3 | **Worst-Case Liability Ceiling (`TCCV`)** | `TCCV_EXCEEDS_MANDATE_CAP` | Requires $\text{TCCV} \le \text{mandate.max\_total\_commitment\_minor}$ even when $C_{\text{initial}} = 0$. |
| 4 | **Per-Cycle Spend Ceiling** | `PER_CYCLE_EXCEEDS_MANDATE_CAP` | Requires $C_{\text{recurring}} \le \text{mandate.max\_per\_cycle\_minor}$. |
| 5 | **Predatory Cancellation Window Defense** | `PREDATORY_CANCELLATION_WINDOW_BLOCKED` | Blocks trials whose cancellation deadline precedes trial end by $> 48\text{h}$ unless an autonomous pre-cutoff cancellation hook (`auto_cancel_hook_armed = True`) is cryptographically registered. |

---

## 3. Invariant 2: Atomic 3-Layer Revocation Cascade & Zombie MIT Charge Defense

```
  [Buyer / FinOps Revocation Request]
                 │
                 ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │ Layer 1: AP2 Cryptographic MandateRevocation Receipt (JWS)      │
  │   - Signs (mandate_id, revoked_at_epoch, reason) with Ed25519   │
  └──────────────┬──────────────────────────────────────────────────┘
                 │
                 ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │ Layer 2: Payment Rail Token Deactivation (SPT + VTS/MDES)       │
  │   - spt_status = "deactivated"                                  │
  │   - network_token_status = "deactivated"                        │
  └──────────────┬──────────────────────────────────────────────────┘
                 │
                 ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │ Layer 3: Merchant Billing Subscription State Convergence        │
  │   - subscription_status in ("canceled", "cancel_at_period_end") │
  │   - Verified merchant_cancellation_ack_id                       │
  └──────────────┬──────────────────────────────────────────────────┘
                 │
                 ▼
  [Post-Revocation MIT Charge Attempt at t >= revoked_at_epoch?]
        ├── No  ──► ATOMIC_3_LAYER_REVOCATION_CONVERGED
        └── Yes ──► ZOMBIE_MIT_BLOCKED_VISA_13_5_MC_4841
                    (Auto-compiles Visa 13.5 / Mastercard 4841 CE3.0 receipt)
```

---

## 4. Executable Verification

```bash
python -m lab.recurring_subscription_guard --json
python -m unittest tests/test_recurring_subscription_guard.py -v
```
