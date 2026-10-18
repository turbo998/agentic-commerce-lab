"""Stage 9: Recurring Mandate, Free-Trial Negative-Option Trap & Atomic 3-Layer Revocation Guard.

Implements deterministic verification for:
1. Total Committed Contract Value (TCCV) invariant and Negative-Option / Free-Trial Auto-Conversion
   trap prevention (`verify_subscription_trial_and_recurring_mandate`):
     TCCV = C_initial + max(N_min_commit, 1) * C_recurring + F_ETF
   Enforces:
   - Explicit recurring consent (`mandate.allow_recurring == True` when recurring or auto-converting trial)
   - Worst-case liability cap (`TCCV <= mandate.max_total_commitment_minor`)
   - Per-cycle cap (`C_recurring <= mandate.max_per_cycle_minor`)
   - Predatory cancellation cutoff defense (blocks offers where cancellation deadline precedes trial end
     by > 48 hours unless an autonomous pre-cutoff cancellation hook is armed and verified)
   - Policy Broker summary vs. machine-readable recurring terms alignment (prevents hidden auto-renewal)
2. Atomic 3-Layer Revocation Cascade & Zombie MIT Charge Defense (`execute_atomic_revocation_cascade`):
   - Synchronizes revocation across:
     (L1) AP2 Cryptographic Mandate Revocation Receipt (JWS digest + revocation timestamp)
     (L2) Stripe SPT / Card Network Token status (`active -> deactivated`)
     (L3) Merchant Stripe Billing Subscription state (`canceled` / `cancel_at_period_end`)
   - Intercepts post-revocation Merchant-Initiated Transactions (Zombie MIT charges) and compiles
     deterministic card-network dispute evidence for Visa Condition 13.5 / Mastercard 4841
     (Canceled Recurring Transaction).
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Any, Mapping, Sequence


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_prefixed(payload: Any) -> str:
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


@dataclass(frozen=True)
class SubscriptionMandateCheckResult:
    allowed: bool
    decision_code: str
    is_recurring_or_auto_convert: bool
    initial_charge_minor: int
    recurring_charge_minor: int
    min_commitment_cycles: int
    early_termination_fee_minor: int
    tccv_minor: int
    mandate_max_total_commitment_minor: int
    mandate_max_per_cycle_minor: int
    cancellation_lead_hours_before_trial_end: float
    reasons: list[str] = field(default_factory=list)
    audit_digest: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AtomicRevocationCascadeResult:
    revocation_complete: bool
    zombie_mit_blocked: bool
    decision_code: str
    mandate_id: str
    revoked_at_epoch: int
    layer1_ap2_revocation_verified: bool
    layer2_network_token_deactivated: bool
    layer3_billing_subscription_canceled: bool
    post_revocation_mit_attempted: bool
    mit_attempt_epoch: int | None
    mit_amount_minor: int
    dispute_reason_codes: dict[str, str]
    ce3_cancellation_receipt_digest: str
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def verify_subscription_trial_and_recurring_mandate(
    mandate: Mapping[str, Any],
    offer_terms: Mapping[str, Any],
    *,
    max_unhooked_cancel_lead_hours: float = 48.0,
) -> SubscriptionMandateCheckResult:
    """Verify recurring/subscription offer terms against an AP2 IntentMandate.

    Computes Total Committed Contract Value (TCCV):
      TCCV = initial_charge_minor + max(min_commitment_cycles, 1) * recurring_charge_minor + early_termination_fee_minor
    for any recurring or auto-converting trial offer.
    """
    reasons: list[str] = []

    billing_interval = str(offer_terms.get("billing_interval") or "one_time").lower()
    trial_days = int(offer_terms.get("trial_days", 0))
    auto_convert = bool(offer_terms.get("auto_convert", False))
    initial_charge = int(offer_terms.get("initial_charge_minor", 0))
    recurring_charge = int(offer_terms.get("recurring_charge_minor", 0))
    min_commit_cycles = int(offer_terms.get("min_commitment_cycles", 0))
    etf_minor = int(offer_terms.get("early_termination_fee_minor", 0))

    is_recurring = (
        billing_interval not in ("one_time", "none", "")
        or recurring_charge > 0
        or (trial_days > 0 and auto_convert)
    )

    if is_recurring:
        effective_cycles = max(min_commit_cycles, 1)
        tccv_minor = initial_charge + (effective_cycles * recurring_charge) + etf_minor
    else:
        tccv_minor = initial_charge

    allow_recurring = bool(mandate.get("allow_recurring", False))
    max_total_commitment = int(
        mandate.get(
            "max_total_commitment_minor",
            mandate.get("max_amount_minor", 0),
        )
    )
    max_per_cycle = int(
        mandate.get(
            "max_per_cycle_minor",
            max_total_commitment,
        )
    )

    # Check 1: Hidden negative-option / summary vs machine-readable terms mismatch
    summary_discloses_recurring = bool(offer_terms.get("summary_discloses_recurring", True))
    if is_recurring and not summary_discloses_recurring:
        reasons.append(
            "SUMMARY_HIDES_NEGATIVE_OPTION_RENEWAL: human-facing summary omits recurring/auto-conversion obligation present in machine terms."
        )

    # Check 2: One-time mandate used for recurring or auto-converting free trial
    if is_recurring and not allow_recurring:
        reasons.append(
            "NEGATIVE_OPTION_MANDATE_MISMATCH: offer requires recurring billing or auto-converting trial, but mandate.allow_recurring is False."
        )

    # Check 3: TCCV worst-case liability exceeds mandate cap
    if tccv_minor > max_total_commitment:
        reasons.append(
            f"TCCV_EXCEEDS_MANDATE_CAP: computed TCCV ({tccv_minor} minor units) exceeds mandate max_total_commitment_minor ({max_total_commitment})."
        )

    # Check 4: Per-cycle recurring charge exceeds mandate per-cycle cap
    if is_recurring and recurring_charge > max_per_cycle:
        reasons.append(
            f"PER_CYCLE_EXCEEDS_MANDATE_CAP: recurring_charge_minor ({recurring_charge}) exceeds mandate max_per_cycle_minor ({max_per_cycle})."
        )

    # Check 5: Predatory cancellation cutoff window before trial end
    cancel_lead_hours = float(offer_terms.get("cancel_cutoff_hours_before_trial_end", 0.0))
    auto_cancel_hook_armed = bool(offer_terms.get("auto_cancel_hook_armed", False))
    if (
        is_recurring
        and trial_days > 0
        and cancel_lead_hours > max_unhooked_cancel_lead_hours
        and not auto_cancel_hook_armed
    ):
        reasons.append(
            f"PREDATORY_CANCELLATION_WINDOW_BLOCKED: cancellation cutoff is {cancel_lead_hours:.1f}h before trial end (> {max_unhooked_cancel_lead_hours:.1f}h) without an armed autonomous cancellation hook."
        )

    allowed = len(reasons) == 0
    if allowed:
        decision_code = "RECURRING_MANDATE_VERIFIED" if is_recurring else "ONE_TIME_OFFER_VERIFIED"
    else:
        first = reasons[0].split(":", 1)[0]
        decision_code = first

    audit_digest = _sha256_prefixed(
        {
            "mandate_id": mandate.get("mandate_id", "mandate_default"),
            "is_recurring": is_recurring,
            "tccv_minor": tccv_minor,
            "decision_code": decision_code,
            "allowed": allowed,
        }
    )

    return SubscriptionMandateCheckResult(
        allowed=allowed,
        decision_code=decision_code,
        is_recurring_or_auto_convert=is_recurring,
        initial_charge_minor=initial_charge,
        recurring_charge_minor=recurring_charge,
        min_commitment_cycles=min_commit_cycles,
        early_termination_fee_minor=etf_minor,
        tccv_minor=tccv_minor,
        mandate_max_total_commitment_minor=max_total_commitment,
        mandate_max_per_cycle_minor=max_per_cycle,
        cancellation_lead_hours_before_trial_end=cancel_lead_hours,
        reasons=reasons,
        audit_digest=audit_digest,
    )


def execute_atomic_revocation_cascade(
    revocation_bundle: Mapping[str, Any],
) -> AtomicRevocationCascadeResult:
    """Verify atomic 3-layer revocation cascade and block post-revocation Zombie MIT charges.

    Layers verified:
      Layer 1: AP2 Cryptographic `MandateRevocation` receipt (non-empty JWS signature & timestamp)
      Layer 2: Payment rail token state (`spt_status == 'deactivated'` and `network_token_status == 'deactivated'`)
      Layer 3: Merchant subscription state (`subscription_status in ('canceled', 'cancel_at_period_end')`)

    Also evaluates any post-revocation Merchant-Initiated Transaction (`mit_charge_attempt`) and
    generates Visa Condition 13.5 / Mastercard 4841 representment/chargeback evidence.
    """
    reasons: list[str] = []
    mandate_id = str(revocation_bundle.get("mandate_id") or "mandate_unknown")
    revoked_at_epoch = int(revocation_bundle.get("revoked_at_epoch", 0))

    # Layer 1: AP2 MandateRevocation JWS
    ap2_jws = str(revocation_bundle.get("ap2_revocation_jws") or "").strip()
    layer1_ok = bool(ap2_jws) and revoked_at_epoch > 0
    if not layer1_ok:
        reasons.append(
            "LAYER1_AP2_REVOCATION_MISSING: missing cryptographic AP2 MandateRevocation JWS or valid revoked_at_epoch."
        )

    # Layer 2: SPT + Network Token deactivation
    spt_status = str(revocation_bundle.get("spt_status") or "").lower()
    network_token_status = str(revocation_bundle.get("network_token_status") or "").lower()
    layer2_ok = spt_status == "deactivated" and network_token_status == "deactivated"
    if not layer2_ok:
        reasons.append(
            f"LAYER2_TOKEN_NOT_DEACTIVATED: expected spt_status='deactivated' and network_token_status='deactivated', got ({spt_status!r}, {network_token_status!r})."
        )

    # Layer 3: Merchant Billing subscription state
    sub_status = str(revocation_bundle.get("subscription_status") or "").lower()
    merchant_ack_id = str(revocation_bundle.get("merchant_cancellation_ack_id") or "").strip()
    layer3_ok = sub_status in ("canceled", "cancel_at_period_end") and bool(merchant_ack_id)
    if not layer3_ok:
        reasons.append(
            f"LAYER3_SUBSCRIPTION_DRIFT: subscription_status={sub_status!r} or missing merchant_cancellation_ack_id."
        )

    revocation_complete = layer1_ok and layer2_ok and layer3_ok

    # Evaluate post-revocation MIT attempt
    mit_attempt = revocation_bundle.get("mit_charge_attempt")
    post_revocation_mit_attempted = isinstance(mit_attempt, Mapping) and bool(
        mit_attempt.get("attempted", False)
    )
    mit_attempt_epoch: int | None = None
    mit_amount_minor = 0
    zombie_mit_blocked = False

    if post_revocation_mit_attempted and isinstance(mit_attempt, Mapping):
        mit_attempt_epoch = int(mit_attempt.get("attempt_epoch", 0))
        mit_amount_minor = int(mit_attempt.get("amount_minor", 0))
        if revoked_at_epoch > 0 and mit_attempt_epoch >= revoked_at_epoch:
            zombie_mit_blocked = True
            reasons.append(
                f"ZOMBIE_MIT_CHARGE_INTERCEPTED: MIT charge of {mit_amount_minor} minor units at epoch {mit_attempt_epoch} occurred after revocation epoch {revoked_at_epoch}."
            )

    if zombie_mit_blocked:
        decision_code = "ZOMBIE_MIT_BLOCKED_VISA_13_5_MC_4841"
    elif revocation_complete:
        decision_code = "ATOMIC_3_LAYER_REVOCATION_CONVERGED"
    else:
        decision_code = reasons[0].split(":", 1)[0] if reasons else "REVOCATION_INCOMPLETE"

    dispute_codes = {
        "visa": "13.5_CANCELED_RECURRING_TRANSACTION",
        "mastercard": "4841_CANCELED_RECURRING_OR_DIGITAL_GOODS",
    }

    receipt_digest = _sha256_prefixed(
        {
            "mandate_id": mandate_id,
            "revoked_at_epoch": revoked_at_epoch,
            "ap2_revocation_jws": ap2_jws,
            "spt_status": spt_status,
            "network_token_status": network_token_status,
            "subscription_status": sub_status,
            "merchant_cancellation_ack_id": merchant_ack_id,
            "decision_code": decision_code,
        }
    )

    return AtomicRevocationCascadeResult(
        revocation_complete=revocation_complete,
        zombie_mit_blocked=zombie_mit_blocked,
        decision_code=decision_code,
        mandate_id=mandate_id,
        revoked_at_epoch=revoked_at_epoch,
        layer1_ap2_revocation_verified=layer1_ok,
        layer2_network_token_deactivated=layer2_ok,
        layer3_billing_subscription_canceled=layer3_ok,
        post_revocation_mit_attempted=post_revocation_mit_attempted,
        mit_attempt_epoch=mit_attempt_epoch,
        mit_amount_minor=mit_amount_minor,
        dispute_reason_codes=dispute_codes,
        ce3_cancellation_receipt_digest=receipt_digest,
        reasons=reasons,
    )


def run_demo_scenarios() -> list[dict[str, Any]]:
    """Run deterministic Stage 9 scenarios demonstrating TCCV & 3-layer revocation guards."""
    scenarios: list[dict[str, Any]] = []

    # 1. Compliant SaaS seat subscription within TCCV and per-cycle mandate caps
    s1 = verify_subscription_trial_and_recurring_mandate(
        mandate={
            "mandate_id": "mandate_saas_compliant_01",
            "allow_recurring": True,
            "max_total_commitment_minor": 60_000,  # $600.00
            "max_per_cycle_minor": 5_000,          # $50.00/mo
        },
        offer_terms={
            "billing_interval": "month",
            "trial_days": 14,
            "auto_convert": True,
            "initial_charge_minor": 0,
            "recurring_charge_minor": 4_900,       # $49.00/mo
            "min_commitment_cycles": 6,            # 6 months = $294.00
            "early_termination_fee_minor": 5_000,  # $50.00 ETF -> TCCV = $344.00
            "cancel_cutoff_hours_before_trial_end": 24.0,
            "auto_cancel_hook_armed": True,
            "summary_discloses_recurring": True,
        },
    )
    scenarios.append({"scenario_id": "S9_01_COMPLIANT_SAAS_RECURRING", **s1.to_dict()})

    # 2. Free-trial negative-option trap ($0 initial, $199/mo x 12-mo lock-in + $150 ETF on one-time $50 mandate)
    s2 = verify_subscription_trial_and_recurring_mandate(
        mandate={
            "mandate_id": "mandate_onetime_50usd",
            "allow_recurring": False,
            "max_total_commitment_minor": 5_000,   # $50.00 one-time budget
            "max_per_cycle_minor": 5_000,
        },
        offer_terms={
            "billing_interval": "month",
            "trial_days": 7,
            "auto_convert": True,
            "initial_charge_minor": 0,
            "recurring_charge_minor": 19_900,      # $199.00/mo
            "min_commitment_cycles": 12,
            "early_termination_fee_minor": 15_000, # TCCV = $2,538.00
            "cancel_cutoff_hours_before_trial_end": 72.0,
            "auto_cancel_hook_armed": False,
            "summary_discloses_recurring": False,
        },
    )
    scenarios.append({"scenario_id": "S9_02_FREE_TRIAL_DARK_PATTERN_TRAP", **s2.to_dict()})

    # 3. Atomic 3-layer revocation + Zombie MIT charge interception
    s3 = execute_atomic_revocation_cascade(
        {
            "mandate_id": "mandate_saas_compliant_01",
            "revoked_at_epoch": 1792368000,
            "ap2_revocation_jws": "eyJhbGciOiJFZERTQSJ9.revocation_payload.sig_ed25519",
            "spt_status": "deactivated",
            "network_token_status": "deactivated",
            "subscription_status": "canceled",
            "merchant_cancellation_ack_id": "sub_cancel_ack_99182",
            "mit_charge_attempt": {
                "attempted": True,
                "attempt_epoch": 1792454400,
                "amount_minor": 4_900,
            },
        }
    )
    scenarios.append({"scenario_id": "S9_03_ZOMBIE_MIT_INTERCEPTED", **s3.to_dict()})

    return scenarios


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Stage 9 Recurring Subscription TCCV & Atomic 3-Layer Revocation Guard demo."
    )
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args(argv)

    results = run_demo_scenarios()
    if args.json:
        print(json.dumps({"scenarios": results}, indent=2))
    else:
        print("=== Stage 9: Recurring Mandates, TCCV & Atomic 3-Layer Revocation Guard ===")
        for item in results:
            print(
                f"  [{item['scenario_id']}] decision={item['decision_code']} "
                f"reasons={len(item.get('reasons', []))}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
