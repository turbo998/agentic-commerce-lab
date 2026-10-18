# Agentic Subscription Lifecycle, Usage-Metering Watermark Idempotency & FTC Click-to-Cancel / PSD3 Recurring Mandate Guard

**Date**: 2026-10-19 (Stage 18 Overnight Deep-Dive)  
**Scope**: Stripe Billing / Metronome Usage Metering (`stripe-token-billing`) × PSD3 / RBI Recurring Mandate Pre-Debit & Price-Escalation Rules × FTC Negative Option ("Click-to-Cancel") Symmetric Offramp

---

## 1. High-Frequency Usage Metering Watermark & Hard Spend Cap (`evaluate_usage_based_metering_idempotency`)

When buyer agents consume metered SaaS seats, GPU compute seconds, or LLM token streams:
1. **Idempotency Deduplication**: Every usage event carries a deterministic `idempotency_key` (e.g., UUIDv7); duplicate webhook/stream deliveries are dropped at zero incremental charge.
2. **Late-Event Watermark Window (`<= 300s`)**: Events arriving after `watermark_epoch - event_timestamp_epoch > 300s` are rejected (`USAGE_EVENT_LATE_WATERMARK_EXPIRED`) so closed billing periods cannot be retroactively mutated.
3. **Runaway Agent Loop Circuit Breaker**: When cumulative cycle spend reaches `hard_spend_cap_minor`, metering immediately trips `SPEND_CAP_HARD_LIMIT_REACHED_THROTTLED` and halts downstream execution.

---

## 2. PSD3 / RBI Recurring Mandate Renewal & Price-Escalation Guard (`evaluate_recurring_mandate_renewal_and_pre_debit_notice`)

1. **48-Hour Pre-Debit Notification Invariant**: Merchants must emit a signed pre-debit webhook/notice at least `48 hours` before executing a Merchant-Initiated Transaction (`PRE_DEBIT_NOTICE_WINDOW_VIOLATION`).
2. **Trial-to-Paid Explicit Consent**: Converting a free or introductory trial into a paid cycle requires a separate signed buyer consent digest (`TRIAL_TO_PAID_EXPLICIT_CONSENT_MISSING`).
3. **Price Escalation Re-Consent (`> 5%` or `> mandate_max_amount_minor`)**: Any renewal exceeding the mandate ceiling or increasing more than `500 bps` (`5.0%`) over the prior cycle requires fresh buyer re-authorization (`RECURRING_PRICE_ESCALATION_RECONSENT_REQUIRED`).

---

## 3. FTC "Click-to-Cancel" Symmetric Offramp & Pro-Rata Refund (`execute_ftc_click_to_cancel_symmetric_offramp`)

1. **Symmetric Step Cap (`<= 2` deterministic protocol calls)**: Cancellation cannot require more steps than enrollment or force human-chat retention walls (`DARK_PATTERN_RETENTION_WALL_BLOCKED`).
2. **Pro-Rata Unused Cycle Refund & Token Revocation**: Unused days in a prepaid cycle are refunded deterministically:
   $$R_{\text{pro\_rata}} = \left\lfloor \frac{C_{\text{paid}} \times D_{\text{unused}}}{D_{\text{total}}} \right\rfloor$$
   while atomically revoking the Stripe `SPT` / network token (`PRO_RATA_REFUND_ISSUED`).
