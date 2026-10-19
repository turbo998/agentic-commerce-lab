"""Stage 38: UCP Return Policy Eligibility & Typed Fees (`#966`), Generalized Capability Event
Webhooks (`#938`), Purchase Options & Subscription Open-Ended Instrument Rules (`#890`),
Business Identity Separation (`#939`), and Checkout Escalation `continue_url` Enforcement (`#912`).

Pure Python standard library; zero network calls; zero secrets.
"""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import re
from typing import Any
from urllib.parse import urlparse


WELL_KNOWN_RETURN_FEES = frozenset(
    {
        "dev.ucp.shopping.fee.restocking",
        "dev.ucp.shopping.fee.return_shipping",
        "dev.ucp.shopping.fee.handling",
    }
)
VALID_RETURN_ANCHORS = frozenset({"purchased", "fulfilled", "delivered"})
EVENT_TYPE_RE = re.compile(r"^([a-z0-9-]+(?:\.[a-z0-9-]+){2,}):([a-z0-9_]+)$")


@dataclass(frozen=True)
class UCPReturnPolicyGuardResult:
    admitted: bool
    decision_code: str
    eligibility_status: str
    resolved_channel_fees_minor: dict[str, int | None]
    channel_is_free_return: bool


@dataclass(frozen=True)
class UCPCapabilityWebhookGuardResult:
    admitted: bool
    decision_code: str
    effective_subscribed_events: tuple[str, ...]
    requires_authoritative_readback: bool


@dataclass(frozen=True)
class UCPSubscriptionPurchaseOptionGuardResult:
    admitted: bool
    decision_code: str
    retained_recurring_instrument_ids: tuple[str, ...]
    today_instrument_allocations: dict[str, int]


@dataclass(frozen=True)
class UCPBusinessIdentityAndEscalationGuardResult:
    admitted: bool
    decision_code: str
    business_identity_valid: bool
    escalation_continue_url_valid: bool


def evaluate_ucp_return_policy_eligibility_and_fees_guard(
    *,
    eligibility: dict[str, Any] | None,
    anchor_event_occurred: bool,
    platform_computed_deadline_from_duration: bool,
    selected_channel: str,
    guaranteed_methods: tuple[str, ...],
    fees: tuple[dict[str, Any], ...],
    item_unit_price_minor: int,
    platform_presents_channel_as_free: bool,
) -> UCPReturnPolicyGuardResult:
    """Enforce UCP PR #966 explicit return eligibility, business-stated deadlines, and narrowest-wins typed fees."""
    if not eligibility:
        if platform_presents_channel_as_free:
            return UCPReturnPolicyGuardResult(
                admitted=False,
                decision_code="OMITTED_RETURN_ELIGIBILITY_NEVER_UNLIMITED",
                eligibility_status="not_stated",
                resolved_channel_fees_minor={},
                channel_is_free_return=False,
            )
        return UCPReturnPolicyGuardResult(
            admitted=True,
            decision_code="RETURN_ELIGIBILITY_NOT_STATED_NO_INFERENCE",
            eligibility_status="not_stated",
            resolved_channel_fees_minor={},
            channel_is_free_return=False,
        )

    elig_type = str(eligibility.get("type", "")).strip()
    if elig_type not in {"window", "unlimited", "not_accepted"}:
        return UCPReturnPolicyGuardResult(
            admitted=False,
            decision_code="UNKNOWN_RETURN_ELIGIBILITY_TYPE_NO_INFERENCE",
            eligibility_status=elig_type or "unknown",
            resolved_channel_fees_minor={},
            channel_is_free_return=False,
        )

    if elig_type == "window":
        duration = str(eligibility.get("duration", "")).strip()
        anchor = str(eligibility.get("anchor", "")).strip()
        expires_at = eligibility.get("expires_at")
        if duration in {"", "P0D", "PT0S", "PT0M"} or anchor not in VALID_RETURN_ANCHORS:
            return UCPReturnPolicyGuardResult(
                admitted=False,
                decision_code="INVALID_ZERO_DURATION_OR_ANCHOR_FOR_RETURN_WINDOW",
                eligibility_status="invalid_window",
                resolved_channel_fees_minor={},
                channel_is_free_return=False,
            )
        if platform_computed_deadline_from_duration:
            return UCPReturnPolicyGuardResult(
                admitted=False,
                decision_code="PLATFORM_COMPUTED_RETURN_DEADLINE_FORBIDDEN",
                eligibility_status="window",
                resolved_channel_fees_minor={},
                channel_is_free_return=False,
            )
        if anchor_event_occurred and not expires_at:
            return UCPReturnPolicyGuardResult(
                admitted=False,
                decision_code="BUSINESS_MUST_STATE_EXPIRES_AT_AFTER_ANCHOR_EVENT",
                eligibility_status="window",
                resolved_channel_fees_minor={},
                channel_is_free_return=False,
            )

    # Resolve fees for `selected_channel` using narrowest-wins (method-scoped overrides unscoped per fee.type)
    unscoped_fees: dict[str, int | None] = {}
    scoped_fees: dict[str, int | None] = {}
    for entry in fees:
        fee_type = str(entry.get("type", "")).strip()
        if not fee_type:
            continue
        has_amount = "amount" in entry
        has_bps = "basis_points" in entry
        if has_amount and has_bps:
            return UCPReturnPolicyGuardResult(
                admitted=False,
                decision_code="RETURN_FEE_AMBIGUOUS_DUAL_ENCODING_BLOCKED",
                eligibility_status=elig_type,
                resolved_channel_fees_minor={},
                channel_is_free_return=False,
            )
        if has_amount:
            resolved_val: int | None = int(entry["amount"])
        elif has_bps:
            bps = int(entry["basis_points"])
            calc = (item_unit_price_minor * bps) // 10_000
            if "max_amount" in entry:
                calc = min(calc, int(entry["max_amount"]))
            resolved_val = calc
        else:
            resolved_val = None  # buyer pays actual cost, unstated maximum

        entry_methods = entry.get("methods")
        if entry_methods is None:
            unscoped_fees[fee_type] = resolved_val
        elif isinstance(entry_methods, (list, tuple)) and selected_channel in entry_methods:
            scoped_fees[fee_type] = resolved_val

    effective_fees = dict(unscoped_fees)
    effective_fees.update(scoped_fees)

    # A platform may present a channel as free ONLY when every well-known fee resolves to 0 for it
    all_well_known_zero = (
        selected_channel in guaranteed_methods
        and all(effective_fees.get(wk) == 0 for wk in WELL_KNOWN_RETURN_FEES if wk in effective_fees)
        and any(wk in effective_fees for wk in WELL_KNOWN_RETURN_FEES)
        and all(v == 0 for v in effective_fees.values())
    )
    if platform_presents_channel_as_free and not all_well_known_zero:
        return UCPReturnPolicyGuardResult(
            admitted=False,
            decision_code="CHANNEL_FALSELY_PRESENTED_AS_FREE_RETURN_BLOCKED",
            eligibility_status=elig_type,
            resolved_channel_fees_minor=effective_fees,
            channel_is_free_return=False,
        )

    return UCPReturnPolicyGuardResult(
        admitted=True,
        decision_code="UCP_RETURN_POLICY_ELIGIBILITY_AND_FEES_VERIFIED",
        eligibility_status=elig_type,
        resolved_channel_fees_minor=effective_fees,
        channel_is_free_return=all_well_known_zero,
    )


def _is_safe_https_webhook_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return False
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
            return False
    except ValueError:
        if parsed.hostname.lower() in {"localhost", "metadata.google.internal"}:
            return False
    return True


def evaluate_ucp_capability_event_webhook_guard(
    *,
    capability_name: str,
    platform_recognized_by_business: bool,
    subscription_request_rfc9421_signed: bool,
    webhook_url: str,
    webhook_follows_redirects: bool,
    platform_requested_events: tuple[str, ...] | None,
    business_supported_events: tuple[str, ...],
    event_type: str,
    is_broadcast_capability: bool,
    payload_is_thin_event_envelope: bool,
    platform_treats_thin_event_as_state_without_read: bool,
    is_location_removed_event: bool,
    platform_confirmed_removal_with_unfiltered_lookup: bool,
    covered_signature_components: tuple[str, ...],
    webhook_timestamp_Skew_seconds: int,
) -> UCPCapabilityWebhookGuardResult:
    """Enforce UCP PR #938 Capability Event Webhooks subscription, RFC 9421 headers, thin envelopes, and readback."""
    if not platform_recognized_by_business or not subscription_request_rfc9421_signed:
        return UCPCapabilityWebhookGuardResult(
            admitted=False,
            decision_code="UNRECOGNIZED_OR_UNSIGNED_WEBHOOK_SUBSCRIPTION_BLOCKED",
            effective_subscribed_events=(),
            requires_authoritative_readback=True,
        )

    if not _is_safe_https_webhook_url(webhook_url) or webhook_follows_redirects:
        return UCPCapabilityWebhookGuardResult(
            admitted=False,
            decision_code="UNSAFE_WEBHOOK_URL_OR_REDIRECT_BLOCKED",
            effective_subscribed_events=(),
            requires_authoritative_readback=True,
        )

    match = EVENT_TYPE_RE.match(event_type)
    if not match or match.group(1) != capability_name:
        return UCPCapabilityWebhookGuardResult(
            admitted=False,
            decision_code="INVALID_CAPABILITY_EVENT_NAMESPACE_BINDING",
            effective_subscribed_events=(),
            requires_authoritative_readback=True,
        )

    effective_events = (
        tuple(business_supported_events)
        if platform_requested_events is None
        else tuple(e for e in business_supported_events if e in platform_requested_events)
    )
    if event_type not in effective_events:
        return UCPCapabilityWebhookGuardResult(
            admitted=False,
            decision_code="EVENT_NOT_IN_INTERSECTED_WEBHOOK_SUBSCRIPTION",
            effective_subscribed_events=effective_events,
            requires_authoritative_readback=True,
        )

    required_sig_headers = {"webhook-id", "webhook-timestamp", "ucp-agent"}
    if not required_sig_headers.issubset({c.lower() for c in covered_signature_components}):
        return UCPCapabilityWebhookGuardResult(
            admitted=False,
            decision_code="WEBHOOK_SIGNATURE_COMPONENTS_INCOMPLETE",
            effective_subscribed_events=effective_events,
            requires_authoritative_readback=True,
        )

    if abs(webhook_timestamp_Skew_seconds) > 300:
        return UCPCapabilityWebhookGuardResult(
            admitted=False,
            decision_code="WEBHOOK_DELIVERY_TIMESTAMP_OUTSIDE_WINDOW",
            effective_subscribed_events=effective_events,
            requires_authoritative_readback=True,
        )

    if is_broadcast_capability and not payload_is_thin_event_envelope:
        return UCPCapabilityWebhookGuardResult(
            admitted=False,
            decision_code="BROADCAST_CAPABILITY_MUST_USE_THIN_EVENT_ENVELOPE",
            effective_subscribed_events=effective_events,
            requires_authoritative_readback=True,
        )

    if payload_is_thin_event_envelope and platform_treats_thin_event_as_state_without_read:
        return UCPCapabilityWebhookGuardResult(
            admitted=False,
            decision_code="THIN_EVENT_TREATED_AS_STATE_WITHOUT_READBACK_BLOCKED",
            effective_subscribed_events=effective_events,
            requires_authoritative_readback=True,
        )

    if is_location_removed_event and not platform_confirmed_removal_with_unfiltered_lookup:
        return UCPCapabilityWebhookGuardResult(
            admitted=False,
            decision_code="FILTERED_LOOKUP_USED_FOR_LOCATION_REMOVAL_BLOCKED",
            effective_subscribed_events=effective_events,
            requires_authoritative_readback=True,
        )

    return UCPCapabilityWebhookGuardResult(
        admitted=True,
        decision_code="UCP_CAPABILITY_EVENT_WEBHOOK_VERIFIED",
        effective_subscribed_events=effective_events,
        requires_authoritative_readback=payload_is_thin_event_envelope,
    )


def evaluate_ucp_purchase_options_subscription_payment_guard(
    *,
    has_one_time_option: bool,
    default_option_has_schedules: bool,
    selected_option_has_schedules: bool,
    withdrawn_subscription_replaced_by_another_subscription: bool,
    subscription_disclosure_presented_or_ap2_mandate_bound: bool,
    is_deferred_paid_trial: bool,
    payment_terms_capability_active: bool,
    today_order_total_minor: int,
    submitted_instruments: tuple[dict[str, Any], ...],
    business_reordered_open_ended_instruments: bool = False,
    business_charged_amounted_instrument_for_recurring: bool = False,
) -> UCPSubscriptionPurchaseOptionGuardResult:
    """Enforce UCP PR #890 purchase options, subscription disclosures, and open-ended recurring instrument rules."""
    if has_one_time_option and default_option_has_schedules:
        return UCPSubscriptionPurchaseOptionGuardResult(
            admitted=False,
            decision_code="DEFAULT_OPTION_MUST_NOT_AUTO_SUBSCRIBE_WHEN_ONE_TIME_EXISTS",
            retained_recurring_instrument_ids=(),
            today_instrument_allocations={},
        )

    if withdrawn_subscription_replaced_by_another_subscription:
        return UCPSubscriptionPurchaseOptionGuardResult(
            admitted=False,
            decision_code="SILENT_SUBSCRIPTION_TO_SUBSCRIPTION_REPLACEMENT_BLOCKED",
            retained_recurring_instrument_ids=(),
            today_instrument_allocations={},
        )

    if is_deferred_paid_trial and not payment_terms_capability_active:
        return UCPSubscriptionPurchaseOptionGuardResult(
            admitted=False,
            decision_code="DEFERRED_TRIAL_WITHOUT_PAYMENT_TERMS_CAPABILITY_BLOCKED",
            retained_recurring_instrument_ids=(),
            today_instrument_allocations={},
        )

    if selected_option_has_schedules and not subscription_disclosure_presented_or_ap2_mandate_bound:
        return UCPSubscriptionPurchaseOptionGuardResult(
            admitted=False,
            decision_code="SUBSCRIPTION_DISCLOSURE_OR_MANDATE_REQUIRED",
            retained_recurring_instrument_ids=(),
            today_instrument_allocations={},
        )

    if business_reordered_open_ended_instruments or business_charged_amounted_instrument_for_recurring:
        return UCPSubscriptionPurchaseOptionGuardResult(
            admitted=False,
            decision_code="AMOUNTED_OR_REORDERED_INSTRUMENT_RECURRING_VIOLATION_BLOCKED",
            retained_recurring_instrument_ids=(),
            today_instrument_allocations={},
        )

    remaining_today = today_order_total_minor
    allocations: dict[str, int] = {}
    retained_open_ended: list[str] = []

    for inst in submitted_instruments:
        inst_id = str(inst["id"])
        supports_recurring = bool(inst.get("supports_recurring", True))
        if "amount" in inst and inst["amount"] is not None:
            amt = min(remaining_today, int(inst["amount"]))
            allocations[inst_id] = amt
            remaining_today -= amt
        else:
            # Open-ended instrument: pays remaining today balance (or 0 if already covered) and is retained
            amt = remaining_today
            allocations[inst_id] = amt
            remaining_today = 0
            if supports_recurring:
                retained_open_ended.append(inst_id)

    if selected_option_has_schedules and not retained_open_ended:
        return UCPSubscriptionPurchaseOptionGuardResult(
            admitted=False,
            decision_code="SUBSCRIPTION_MISSING_OPEN_ENDED_RECURRING_INSTRUMENT",
            retained_recurring_instrument_ids=(),
            today_instrument_allocations=allocations,
        )

    return UCPSubscriptionPurchaseOptionGuardResult(
        admitted=True,
        decision_code="UCP_PURCHASE_OPTION_AND_OPEN_ENDED_INSTRUMENTS_VERIFIED",
        retained_recurring_instrument_ids=tuple(retained_open_ended),
        today_instrument_allocations=allocations,
    )


def evaluate_ucp_business_identity_and_escalation_guard(
    *,
    business_identity_in_capabilities: bool,
    business_identity_conflated_with_branch_location: bool,
    checkout_status: str,
    continue_url: str | None,
) -> UCPBusinessIdentityAndEscalationGuardResult:
    """Enforce UCP PR #939 (`dev.ucp.common.business` separation from `location`) and PR #912 (`requires_escalation` `continue_url`)."""
    if not business_identity_in_capabilities or business_identity_conflated_with_branch_location:
        return UCPBusinessIdentityAndEscalationGuardResult(
            admitted=False,
            decision_code="BUSINESS_IDENTITY_LOCATION_CONFLATION_BLOCKED",
            business_identity_valid=False,
            escalation_continue_url_valid=True,
        )

    if checkout_status == "requires_escalation" and not (
        continue_url and continue_url.startswith("https://")
    ):
        return UCPBusinessIdentityAndEscalationGuardResult(
            admitted=False,
            decision_code="ESCALATION_WITHOUT_CONTINUE_URL_BLOCKED",
            business_identity_valid=True,
            escalation_continue_url_valid=False,
        )

    return UCPBusinessIdentityAndEscalationGuardResult(
        admitted=True,
        decision_code="UCP_BUSINESS_IDENTITY_AND_ESCALATION_SCHEMA_VERIFIED",
        business_identity_valid=True,
        escalation_continue_url_valid=True,
    )
