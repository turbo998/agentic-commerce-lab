# Stage 19: Promo Coupon Stacking Guard, Cryptographic Affiliate Attribution & Loyalty Return Clawback

**Verification Date:** 2026-10-19 (Beijing Time)  
**Implementation Module:** `lab/loyalty_affiliate_promo_stacking_guard.py`  
**Test Suite:** `tests/test_loyalty_affiliate_promo_stacking_guard.py`

---

## 1. Promo Coupon Stacking & Margin Floor Invariant (`evaluate_promo_coupon_stacking_invariant`)

Autonomous shopping agents can enumerate hundreds of promo codes per second across partner channels. Without deterministic pre-authorization boundaries:
- **Sybil Self-Referral Rings (`SELF_REFERRAL_SYBIL_RING_BLOCKED`)**: Blocks referral rewards when `buyer_principal_did == referrer_principal_did`, payment fingerprints collide, or circular referral graphs are detected.
- **Exclusivity Group Conflict (`EXCLUSIVITY_GROUP_CONFLICT`)**: Enforces mutually exclusive campaign groups and non-stackable coupon flags.
- **Post-Discount Margin Floor (`PROMO_STACK_EXCEEDS_FLOOR_MARGIN_BLOCKED`)**: Requires
  $$\text{Margin}_{\text{bps}} = \left\lfloor \frac{(S_{\text{subtotal}} - \sum D_i) - \text{COGS}}{S_{\text{subtotal}}} \times 10000 \right\rceil \ge \text{Margin}_{\text{floor,bps}}$$

---

## 2. Cryptographic Multi-Hop Affiliate Attribution (`verify_cryptographic_affiliate_attribution_chain`)

- **Anti-Hijacking Window (`LAST_SECOND_ATTRIBUTION_HIJACK_BLOCKED`)**: Blocks browser extensions or malicious intermediary agents that inject an attribution claim within `<= 5s` of checkout without a verified upstream discovery interaction digest (`verified_interaction_digest`).
- **Largest Remainder Commission Split (`AFFILIATE_ATTRIBUTION_SPLIT_VERIFIED`)**: Allocates total affiliate commission across verified discovery, comparison, and checkout agents with zero integer-cent drift ($\sum C_k = C_{\text{total}}$).

---

## 3. Loyalty Points Return-Window Escrow & Clawback (`evaluate_loyalty_points_escrow_and_return_clawback`)

- Locks earned loyalty points/cashback in `PENDING_RETURN_WINDOW_ESCROW` until `return_window_expires_epoch`.
- If a buyer agent redeems rewards and subsequently returns the underlying merchandise, the guard revokes available points (`LOYALTY_POINTS_CLAWED_BACK`) and deducts any unrecovered spent deficit from the principal refund (`CASHBACK_DEFICIT_DEDUCTED_FROM_REFUND`).
