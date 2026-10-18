"""Stage 18: Agentic Subscription Lifecycle, Usage-Metering Watermark Idempotency & FTC Click-to-Cancel / PSD3 Recurring Mandate Guard.

Implements three deterministic controls for SaaS, token/API quota, and recurring replenishment subscriptions:
1. ``evaluate_usage_based_metering_idempotency``: Enforces UUIDv7/idempotency-key deduplication,
   late-event watermark rejection (`<= 300s`), and hard spend-cap circuit breaking to prevent
   runaway agent loops from causing bill shock.
2. ``evaluate_recurring_mandate_renewal_and_pre_debit_notice``: Enforces PSD3 / RBI recurring
   mandate rules including `>= 48h` pre-debit notice windows, `> 5%` (`500 bps`) price-escalation
   re-consent, and explicit trial-to-paid conversion consent.
3. ``execute_ftc_click_to_cancel_symmetric_offramp``: Enforces the FTC Negative Option Rule
   ("Click-to-Cancel" symmetric cancellation in `<= 2` protocol calls), blocks dark-pattern
   retention walls, calculates exact pro-rata unused-cycle refunds, and revokes Stripe SPT tokens.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Any


@dataclass(frozen=True)
class UsageMeteringEvaluationResult:
    """Result of evaluating a batch of metered token/API usage events."""

    allowed: bool
    decision_code: str
    subscription_id: str
    accepted_events_count: int
    duplicate_events_dropped: int
    late_watermark_events_rejected: int
    prior_spend_minor: int
    incremental_billed_minor: int
    cumulative_spend_minor: int
    hard_spend_cap_minor: int
    throttled: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RecurringMandateRenewalResult:
    """Result of PSD3 / RBI recurring mandate renewal & pre-debit verification."""

    allowed: bool
    decision_code: str
    mandate_id: str
    previous_cycle_debit_minor: int
    proposed_debit_minor: int
    mandate_max_amount_minor: int
    price_escalation_bps: int
    pre_debit_notice_hours_ahead: int
    reconsent_required: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ClickToCancelOfframpResult:
    """Result of executing an FTC Click-to-Cancel symmetric offramp."""

    canceled: bool
    decision_code: str
    subscription_id: str
    enrollment_steps: int
    required_cancellation_steps: int
    pro_rata_refund_minor: int
    unused_days: int
    total_cycle_days: int
    spt_token_revoked: bool
    mandate_revoked: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_usage_based_metering_idempotency(
    metering_bundle: dict[str, Any],
) -> UsageMeteringEvaluationResult:
    """Validate idempotency, watermark freshness (`<= 300s`), and hard spend cap on usage events."""

    subscription_id = str(metering_bundle.get("subscription_id", ""))
    watermark_epoch = int(metering_bundle.get("watermark_epoch", 0))
    max_lateness_sec = int(metering_bundle.get("max_watermark_lateness_seconds", 300))
    prior_spend_minor = int(metering_bundle.get("prior_spend_minor", 0))
    hard_cap_minor = int(metering_bundle.get("hard_spend_cap_minor", 100_000))
    unit_price_micro_minor = int(
        metering_bundle.get("unit_price_minor_per_1k_units", 100)
    )
    reject_on_late_watermark = bool(
        metering_bundle.get("reject_batch_on_late_watermark", True)
    )

    seen_keys: set[str] = set(str(k) for k in metering_bundle.get("seen_idempotency_keys", []))
    raw_events: list[dict[str, Any]] = list(metering_bundle.get("events", []))

    accepted = 0
    duplicates = 0
    late_rejected = 0
    incremental_units = 0

    for ev in raw_events:
        key = str(ev.get("idempotency_key", "")).strip()
        ev_epoch = int(ev.get("event_timestamp_epoch", watermark_epoch))
        units = int(ev.get("units", 0))

        if not key or key in seen_keys:
            duplicates += 1
            continue

        lateness = watermark_epoch - ev_epoch
        if lateness > max_lateness_sec or ev_epoch > watermark_epoch + 60:
            late_rejected += 1
            continue

        seen_keys.add(key)
        accepted += 1
        incremental_units += max(0, units)

    incremental_billed = (incremental_units * unit_price_micro_minor) // 1000
    cumulative_spend = prior_spend_minor + incremental_billed

    if late_rejected > 0 and reject_on_late_watermark:
        return UsageMeteringEvaluationResult(
            allowed=False,
            decision_code="USAGE_EVENT_LATE_WATERMARK_EXPIRED",
            subscription_id=subscription_id,
            accepted_events_count=accepted,
            duplicate_events_dropped=duplicates,
            late_watermark_events_rejected=late_rejected,
            prior_spend_minor=prior_spend_minor,
            incremental_billed_minor=incremental_billed,
            cumulative_spend_minor=cumulative_spend,
            hard_spend_cap_minor=hard_cap_minor,
            throttled=False,
        )

    if cumulative_spend > hard_cap_minor:
        return UsageMeteringEvaluationResult(
            allowed=False,
            decision_code="SPEND_CAP_HARD_LIMIT_REACHED_THROTTLED",
            subscription_id=subscription_id,
            accepted_events_count=accepted,
            duplicate_events_dropped=duplicates,
            late_watermark_events_rejected=late_rejected,
            prior_spend_minor=prior_spend_minor,
            incremental_billed_minor=incremental_billed,
            cumulative_spend_minor=cumulative_spend,
            hard_spend_cap_minor=hard_cap_minor,
            throttled=True,
        )

    return UsageMeteringEvaluationResult(
        allowed=True,
        decision_code="USAGE_METERING_IDEMPOTENT_AND_WITHIN_CAP",
        subscription_id=subscription_id,
        accepted_events_count=accepted,
        duplicate_events_dropped=duplicates,
        late_watermark_events_rejected=late_rejected,
        prior_spend_minor=prior_spend_minor,
        incremental_billed_minor=incremental_billed,
        cumulative_spend_minor=cumulative_spend,
        hard_spend_cap_minor=hard_cap_minor,
        throttled=False,
    )


def evaluate_recurring_mandate_renewal_and_pre_debit_notice(
    renewal_context: dict[str, Any],
) -> RecurringMandateRenewalResult:
    """Enforce PSD3 / RBI recurring mandate pre-debit notice (`>= 48h`), trial consent, and `<= 5%` escalation."""

    mandate_id = str(renewal_context.get("mandate_id", ""))
    prev_debit = int(renewal_context.get("previous_cycle_debit_minor", 0))
    proposed_debit = int(renewal_context.get("proposed_debit_minor", 0))
    mandate_max = int(renewal_context.get("mandate_max_amount_minor", 0))
    max_escalation_bps = int(renewal_context.get("max_price_escalation_bps", 500))
    notice_hours = int(renewal_context.get("pre_debit_notice_hours_ahead", 0))
    min_notice_hours = int(renewal_context.get("min_pre_debit_notice_hours", 48))
    is_trial_conversion = bool(
        renewal_context.get("is_trial_to_paid_conversion", False)
    )
    explicit_trial_consent = bool(
        renewal_context.get("explicit_trial_conversion_consent", False)
    )

    escalation_bps = 0
    if prev_debit > 0 and proposed_debit > prev_debit:
        escalation_bps = ((proposed_debit - prev_debit) * 10_000) // prev_debit

    if is_trial_conversion and not explicit_trial_consent:
        return RecurringMandateRenewalResult(
            allowed=False,
            decision_code="TRIAL_TO_PAID_EXPLICIT_CONSENT_MISSING",
            mandate_id=mandate_id,
            previous_cycle_debit_minor=prev_debit,
            proposed_debit_minor=proposed_debit,
            mandate_max_amount_minor=mandate_max,
            price_escalation_bps=escalation_bps,
            pre_debit_notice_hours_ahead=notice_hours,
            reconsent_required=True,
        )

    if notice_hours < min_notice_hours:
        return RecurringMandateRenewalResult(
            allowed=False,
            decision_code="PRE_DEBIT_NOTICE_WINDOW_VIOLATION",
            mandate_id=mandate_id,
            previous_cycle_debit_minor=prev_debit,
            proposed_debit_minor=proposed_debit,
            mandate_max_amount_minor=mandate_max,
            price_escalation_bps=escalation_bps,
            pre_debit_notice_hours_ahead=notice_hours,
            reconsent_required=False,
        )

    if proposed_debit > mandate_max or escalation_bps > max_escalation_bps:
        return RecurringMandateRenewalResult(
            allowed=False,
            decision_code="RECURRING_PRICE_ESCALATION_RECONSENT_REQUIRED",
            mandate_id=mandate_id,
            previous_cycle_debit_minor=prev_debit,
            proposed_debit_minor=proposed_debit,
            mandate_max_amount_minor=mandate_max,
            price_escalation_bps=escalation_bps,
            pre_debit_notice_hours_ahead=notice_hours,
            reconsent_required=True,
        )

    return RecurringMandateRenewalResult(
        allowed=True,
        decision_code="RECURRING_RENEWAL_AUTHORIZED",
        mandate_id=mandate_id,
        previous_cycle_debit_minor=prev_debit,
        proposed_debit_minor=proposed_debit,
        mandate_max_amount_minor=mandate_max,
        price_escalation_bps=escalation_bps,
        pre_debit_notice_hours_ahead=notice_hours,
        reconsent_required=False,
    )


def execute_ftc_click_to_cancel_symmetric_offramp(
    offramp_request: dict[str, Any],
) -> ClickToCancelOfframpResult:
    """Enforce FTC Click-to-Cancel symmetric offramp, pro-rata refund, and immediate SPT revocation."""

    subscription_id = str(offramp_request.get("subscription_id", ""))
    enrollment_steps = max(1, int(offramp_request.get("enrollment_steps", 2)))
    cancellation_steps = int(offramp_request.get("required_cancellation_steps", 1))
    forced_retention_wall = bool(
        offramp_request.get("forced_human_chat_retention_wall", False)
    )
    undisclosed_exit_penalty_minor = int(
        offramp_request.get("undisclosed_early_exit_penalty_minor", 0)
    )
    cycle_paid_minor = int(offramp_request.get("cycle_paid_minor", 0))
    total_cycle_days = max(1, int(offramp_request.get("total_cycle_days", 30)))
    unused_days = max(
        0, min(total_cycle_days, int(offramp_request.get("unused_days", 0)))
    )

    max_allowed_steps = min(enrollment_steps, 2)
    if (
        cancellation_steps > max_allowed_steps
        or forced_retention_wall
        or undisclosed_exit_penalty_minor > 0
    ):
        return ClickToCancelOfframpResult(
            canceled=False,
            decision_code="DARK_PATTERN_RETENTION_WALL_BLOCKED",
            subscription_id=subscription_id,
            enrollment_steps=enrollment_steps,
            required_cancellation_steps=cancellation_steps,
            pro_rata_refund_minor=0,
            unused_days=unused_days,
            total_cycle_days=total_cycle_days,
            spt_token_revoked=False,
            mandate_revoked=False,
        )

    pro_rata_refund = (cycle_paid_minor * unused_days) // total_cycle_days
    code = (
        "PRO_RATA_REFUND_ISSUED"
        if pro_rata_refund > 0
        else "CLICK_TO_CANCEL_EXECUTED_ZERO_UNUSED_BALANCE"
    )
    return ClickToCancelOfframpResult(
        canceled=True,
        decision_code=code,
        subscription_id=subscription_id,
        enrollment_steps=enrollment_steps,
        required_cancellation_steps=cancellation_steps,
        pro_rata_refund_minor=pro_rata_refund,
        unused_days=unused_days,
        total_cycle_days=total_cycle_days,
        spt_token_revoked=True,
        mandate_revoked=True,
    )


def _demo() -> None:
    meter_res = evaluate_usage_based_metering_idempotency(
        {
            "subscription_id": "sub_ai_agent_01",
            "watermark_epoch": 1_792_368_000,
            "max_watermark_lateness_seconds": 300,
            "prior_spend_minor": 42_000,
            "hard_spend_cap_minor": 50_000,
            "unit_price_minor_per_1k_units": 200,
            "seen_idempotency_keys": ["uuidv7_001"],
            "events": [
                {"idempotency_key": "uuidv7_001", "event_timestamp_epoch": 1_792_367_950, "units": 10_000},
                {"idempotency_key": "uuidv7_002", "event_timestamp_epoch": 1_792_367_960, "units": 20_000},
                {"idempotency_key": "uuidv7_003", "event_timestamp_epoch": 1_792_367_980, "units": 35_000},
            ],
        }
    )

    renewal_res = evaluate_recurring_mandate_renewal_and_pre_debit_notice(
        {
            "mandate_id": "mnd_psd3_01",
            "previous_cycle_debit_minor": 10_000,
            "proposed_debit_minor": 11_800,
            "mandate_max_amount_minor": 12_000,
            "max_price_escalation_bps": 500,
            "pre_debit_notice_hours_ahead": 72,
            "min_pre_debit_notice_hours": 48,
        }
    )

    cancel_res = execute_ftc_click_to_cancel_symmetric_offramp(
        {
            "subscription_id": "sub_ai_agent_01",
            "enrollment_steps": 2,
            "required_cancellation_steps": 1,
            "forced_human_chat_retention_wall": False,
            "undisclosed_early_exit_penalty_minor": 0,
            "cycle_paid_minor": 30_000,
            "total_cycle_days": 30,
            "unused_days": 18,
        }
    )

    summary = {
        "stage": "stage18-subscription-metering-click-to-cancel-guard",
        "metering_decision": meter_res.decision_code,
        "duplicates_dropped": meter_res.duplicate_events_dropped,
        "renewal_escalation_decision": renewal_res.decision_code,
        "click_to_cancel_decision": cancel_res.decision_code,
        "pro_rata_refund_minor": cancel_res.pro_rata_refund_minor,
        "spt_token_revoked": cancel_res.spt_token_revoked,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    _demo()
