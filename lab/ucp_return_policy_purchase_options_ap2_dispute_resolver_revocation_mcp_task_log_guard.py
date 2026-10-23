"""Stage 186 deterministic guardrails for:

1. Google UCP Return Policy Extension (`dev.ucp.shopping.policy.return`,
   `Universal-Commerce-Protocol/ucp` PR #634, merged commit `ba9795a6`,
   2026-10-23T17:46:18Z):
   - Guarantee-not-exhaustive semantics:
     - `eligibility.type` is required when `eligibility` is present; well-known
       values are `"window"`, `"unlimited"`, `"not_accepted"`.
     - `duration` (strict RFC 3339 Appendix A positive integer ISO 8601 duration)
       and `anchor` (`"purchased"`, `"fulfilled"`, `"delivered"`, or custom) are
       BOTH required when `eligibility.type == "window"`, and `duration`,
       `anchor`, `expires_at` are FORBIDDEN on `"unlimited"` and `"not_accepted"`.
     - Documentary requirements (e.g., `"proof_of_purchase"`) are NOT temporal
       anchors (IKEA US field note in PR #634); if no authoritative temporal
       anchor exists, `eligibility` MUST be omitted and carried in `description`.
     - `not_accepted` is the ONLY structural non-returnability signal and MUST
       NOT carry `supported_resolutions`, `methods`, or `fees`. A platform MUST
       NOT infer non-returnability from an elapsed `window` (`now > expires_at`)
       or an omitted `eligibility`.
     - Channel-scoped fee resolution & zero-fee rules:
       - `amount` and `basis_points` are mutually exclusive; `max_amount`
         requires `basis_points`.
       - A fee entry may omit `type` ONLY when `amount == 0` (meaning zero fee
         of any kind in that channel scope).
       - Channel-specific entries (`methods` present) override channel-wide
         entries (`methods` omitted); typed entries override untyped (`amount: 0`)
         entries at the same specificity; duplicate same-`type` (or two untyped)
         entries on the same channel are invalid. Omitted `fees` means "not
         stated", NEVER "free".

2. Google UCP Purchase Options & Subscription Policy Stacked on Split Payments
   (`Universal-Commerce-Protocol/ucp` PR #890 commit `185a04a8`,
   2026-10-23T17:52:11Z):
   - When `purchase_options[]` includes any one-time option (without
     `schedules`), the first (default) entry MUST be an option without
     `schedules` so a buyer is never enrolled in recurring orders by omission.
   - Every cart/checkout/order line whose selected option carries `schedules`
     MUST be governed by a `dev.ucp.shopping.policy.subscription` policy AND a
     `messages[]` disclosure warning (`presentation == "disclosure"`,
     `code == "dev.ucp.shopping.policy.subscription"`). Parent bundle policies
     do not cover sibling component lines unless `applies_to` targets them.
   - When a previously selected subscription option (`schedules` present) no
     longer resolves, the Business MUST NOT silently substitute a different
     subscription option; if no one-time option is listed, it sets checkout
     `status = "incomplete"` and emits `purchase_option_unavailable`.
   - Under Split Payments (`#987`), only instruments submitted WITHOUT `amount`
     and NOT assigned to an `immediate` `schedule_type` group are retained for
     recurring orders; if zero instruments are retained for a subscription
     checkout, the Business MUST reject with `payment_failed` at
     `$.payment.instruments`. Retained instruments that contribute `0` today
     are still processed and retained with `amount = 0`.

3. Google AP2 Post-Transaction Dispute Resolver (`PR #352`, 2026-10-22T16:06:30Z)
   & Open Mandate `cnf`-Bound Standing-Authority Revocation (`Issue #386`,
   2026-10-21T22:06:25Z):
   - Reproduces the deterministic `ATDRP-0.1` 5-step resolver (`resolve_dispute.py`):
     authorization chain check (`payment_mandate.transaction_id == checkout_hash`
     and both receipts' `reference == checkout_hash`, routing broken chains to
     `"network fraud process"`), pro-rata unlabelled order adjustment allocation,
     mootness check, mandate scope check (`charged > mandated`, `exec > exp`,
     `mandate_reuse_count > 1`), merchant performance check (unfulfilled share
     after `estimated_delivery.latest`), and platform intent-conflict attribution.
   - Enforces bounded `exp` (`MUST` set and `<= iat + max_task_lifetime_sec`) and
     fail-closed SD-JWT VC Status List revocation verification on open Mandates
     before admitting any open-Mandate-backed closed Mandate (`Issue #386`).

4. Model Context Protocol Task-Scoped Log Resource Streaming (`Issue #3237`,
   2026-10-21T19:18:22Z) & RFC 9728 / RFC 8707 Single-Audience Scope Fallback
   (`Issue #1614`, 2026-10-22T22:13:00Z):
   - Enforces strictly monotonic per-task sequence numbers on `task-log://{taskId}`,
     gap-free and duplicate-free resume (`seq > last_seen_seq`), namespaced
     record `kind`, and `terminal_result_independent=True` (forbidding clients
     from skipping final `tasks/get`).
   - Enforces HTTPS URL validation on RFC 9728 `resource` metadata and requires
     single-audience `scope` fallback (`len(requested_audiences) == 1`) with
     strict server `aud`/`iss` verification when an enterprise IdP omits/rejects
     the RFC 8707 `resource` parameter.
"""

from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
import hashlib
import json
import re
from typing import Any, Mapping, Sequence


DURATION_REGEX = re.compile(
    r"^P(?:[1-9]\d*W|(?:[1-9]\d*Y(?:[1-9]\d*M)?(?:[1-9]\d*D)?|"
    r"[1-9]\d*M(?:[1-9]\d*D)?|[1-9]\d*D)"
    r"(?:T(?:[1-9]\d*H(?:[1-9]\d*M)?(?:[1-9]\d*S)?|"
    r"[1-9]\d*M(?:[1-9]\d*S)?|[1-9]\d*S))?|"
    r"T(?:[1-9]\d*H(?:[1-9]\d*M)?(?:[1-9]\d*S)?|"
    r"[1-9]\d*M(?:[1-9]\d*S)?|[1-9]\d*S))$"
)

WELL_KNOWN_RETURN_FEES = frozenset(
    {
        "dev.ucp.shopping.fee.restocking",
        "dev.ucp.shopping.fee.return_shipping",
        "dev.ucp.shopping.fee.handling",
    }
)

DOCUMENTARY_NON_TEMPORAL_ANCHORS = frozenset(
    {
        "proof_of_purchase",
        "receipt_required",
        "original_packaging",
        "tags_attached",
        "null",
        "none",
        "",
    }
)


@dataclass(frozen=True)
class UcpReturnPolicyEvaluation:
    allowed: bool
    reason_code: str
    non_returnable: bool
    channel_free: bool
    estimated_max_fee_minor: int | None
    violation_Rule: str | None = None


def evaluate_ucp_return_policy(
    policy: Mapping[str, Any],
    *,
    query_channel: str = "by_mail",
    returned_units: int = 1,
    unit_paid_minor: int = 20000,
    now_epoch: int | None = None,
    platform_claims_non_returnable: bool = False,
    platform_claims_free_returns: bool = False,
    covered_currencies: Sequence[str] = ("USD",),
) -> UcpReturnPolicyEvaluation:
    """Validate UCP `dev.ucp.shopping.policy.return` (`PR #634`, merged `ba9795a6`)."""
    if policy.get("type") != "dev.ucp.shopping.policy.return":
        return UcpReturnPolicyEvaluation(
            allowed=False,
            reason_code="ucp_return_policy_wrong_type",
            non_returnable=False,
            channel_free=False,
            estimated_max_fee_minor=None,
            violation_Rule="PR #634 policy_return.json",
        )

    if len(set(covered_currencies)) > 1 and policy.get("fees"):
        for fee in policy.get("fees", ()):
            if "amount" in fee or "max_amount" in fee:
                return UcpReturnPolicyEvaluation(
                    allowed=False,
                    reason_code="ucp_return_policy_multi_currency_fee_amount_forbidden",
                    non_returnable=False,
                    channel_free=False,
                    estimated_max_fee_minor=None,
                    violation_Rule="PR #634 §Return fees currency scope",
                )

    eligibility = policy.get("eligibility")
    is_not_accepted = False
    if eligibility is not None:
        elig_type = eligibility.get("type")
        if not isinstance(elig_type, str) or not elig_type.strip():
            return UcpReturnPolicyEvaluation(
                allowed=False,
                reason_code="ucp_return_policy_eligibility_type_missing",
                non_returnable=False,
                channel_free=False,
                estimated_max_fee_minor=None,
                violation_Rule="PR #634 return_eligibility.required",
            )
        if elig_type == "window":
            duration = str(eligibility.get("duration", ""))
            anchor = eligibility.get("anchor")
            if not DURATION_REGEX.match(duration):
                return UcpReturnPolicyEvaluation(
                    allowed=False,
                    reason_code="ucp_return_policy_invalid_iso8601_duration",
                    non_returnable=False,
                    channel_free=False,
                    estimated_max_fee_minor=None,
                    violation_Rule="PR #634 common/types/duration.json",
                )
            if (
                not isinstance(anchor, str)
                or anchor.strip().lower() in DOCUMENTARY_NON_TEMPORAL_ANCHORS
            ):
                return UcpReturnPolicyEvaluation(
                    allowed=False,
                    reason_code="ucp_return_policy_missing_or_documentary_anchor",
                    non_returnable=False,
                    channel_free=False,
                    estimated_max_fee_minor=None,
                    violation_Rule="PR #634 §Window and anchor (IKEA field note)",
                )
        elif elig_type in ("unlimited", "not_accepted"):
            if any(k in eligibility for k in ("duration", "anchor", "expires_at")):
                return UcpReturnPolicyEvaluation(
                    allowed=False,
                    reason_code="ucp_return_policy_window_fields_on_non_window_eligibility",
                    non_returnable=elig_type == "not_accepted",
                    channel_free=False,
                    estimated_max_fee_minor=None,
                    violation_Rule="PR #634 return_eligibility.allOf",
                )
            if elig_type == "not_accepted":
                is_not_accepted = True
                if any(
                    k in policy
                    for k in ("supported_resolutions", "methods", "fees")
                ):
                    return UcpReturnPolicyEvaluation(
                        allowed=False,
                        reason_code="ucp_return_policy_not_accepted_carries_return_terms",
                        non_returnable=True,
                        channel_free=False,
                        estimated_max_fee_minor=None,
                        violation_Rule="PR #634 return_body if/then false",
                    )

    # Only `not_accepted` signals non-returnability; elapsed `window` or omitted `eligibility` MUST NOT
    if platform_claims_non_returnable and not is_not_accepted:
        return UcpReturnPolicyEvaluation(
            allowed=False,
            reason_code="ucp_return_policy_false_non_returnable_inference",
            non_returnable=False,
            channel_free=False,
            estimated_max_fee_minor=None,
            violation_Rule="PR #634 §Eligibility & §Window and anchor",
        )

    for arr_field in ("supported_resolutions", "methods"):
        if arr_field in policy:
            arr = policy[arr_field]
            if not isinstance(arr, list) or len(arr) == 0 or len(set(arr)) != len(arr):
                return UcpReturnPolicyEvaluation(
                    allowed=False,
                    reason_code="ucp_return_policy_empty_or_duplicate_array",
                    non_returnable=is_not_accepted,
                    channel_free=False,
                    estimated_max_fee_minor=None,
                    violation_Rule="PR #634 minItems/uniqueItems",
                )

    fees = policy.get("fees")
    if fees is None:
        if platform_claims_free_returns:
            return UcpReturnPolicyEvaluation(
                allowed=False,
                reason_code="ucp_return_policy_omitted_fees_claimed_as_free",
                non_returnable=is_not_accepted,
                channel_free=False,
                estimated_max_fee_minor=None,
                violation_Rule="PR #634 §Return fees omitted != zero",
            )
        return UcpReturnPolicyEvaluation(
            allowed=True,
            reason_code="ok",
            non_returnable=is_not_accepted,
            channel_free=False,
            estimated_max_fee_minor=None,
        )

    if not isinstance(fees, list) or len(fees) == 0:
        return UcpReturnPolicyEvaluation(
            allowed=False,
            reason_code="ucp_return_policy_empty_fees_array",
            non_returnable=is_not_accepted,
            channel_free=False,
            estimated_max_fee_minor=None,
            violation_Rule="PR #634 fees.minItems",
        )

    # Validate individual fee entries and detect same-channel duplicates
    seen_channel_specific: set[str] = set()
    seen_channel_wide: set[str] = set()
    for fee in fees:
        fee_type = fee.get("type")
        has_amt = "amount" in fee
        has_bps = "basis_points" in fee
        has_max = "max_amount" in fee
        if has_amt and has_bps:
            return UcpReturnPolicyEvaluation(
                allowed=False,
                reason_code="ucp_return_policy_fee_amount_and_bps_mutually_exclusive",
                non_returnable=is_not_accepted,
                channel_free=False,
                estimated_max_fee_minor=None,
                violation_Rule="PR #634 fee.not required[amount, basis_points]",
            )
        if has_max and not has_bps:
            return UcpReturnPolicyEvaluation(
                allowed=False,
                reason_code="ucp_return_policy_fee_max_amount_without_bps",
                non_returnable=is_not_accepted,
                channel_free=False,
                estimated_max_fee_minor=None,
                violation_Rule="PR #634 fee.dependentRequired",
            )
        if fee_type is None:
            if not has_amt or int(fee["amount"]) != 0 or has_bps or has_max:
                return UcpReturnPolicyEvaluation(
                    allowed=False,
                    reason_code="ucp_return_policy_untyped_fee_must_be_zero_amount",
                    non_returnable=is_not_accepted,
                    channel_free=False,
                    estimated_max_fee_minor=None,
                    violation_Rule="PR #634 fee.allOf untyped amount==0",
                )
        else:
            if fee_type not in WELL_KNOWN_RETURN_FEES and not fee.get("display_text"):
                return UcpReturnPolicyEvaluation(
                    allowed=False,
                    reason_code="ucp_return_policy_vendor_fee_missing_display_text",
                    non_returnable=is_not_accepted,
                    channel_free=False,
                    estimated_max_fee_minor=None,
                    violation_Rule="PR #634 fee.allOf vendor display_text",
                )
        if not has_amt and not has_bps and not fee.get("display_text"):
            return UcpReturnPolicyEvaluation(
                allowed=False,
                reason_code="ucp_return_policy_unbounded_fee_missing_display_text",
                non_returnable=is_not_accepted,
                channel_free=False,
                estimated_max_fee_minor=None,
                violation_Rule="PR #634 fee.allOf actual-cost display_text",
            )

        key = fee_type or "__untyped__"
        methods = fee.get("methods")
        if methods is None:
            if key in seen_channel_wide:
                return UcpReturnPolicyEvaluation(
                    allowed=False,
                    reason_code="ucp_return_policy_duplicate_fee_type_on_channel",
                    non_returnable=is_not_accepted,
                    channel_free=False,
                    estimated_max_fee_minor=None,
                    violation_Rule="PR #634 §Return fees duplicate type",
                )
            seen_channel_wide.add(key)
        else:
            for ch in methods:
                ch_key = f"{ch}:{key}"
                if ch_key in seen_channel_specific:
                    return UcpReturnPolicyEvaluation(
                        allowed=False,
                        reason_code="ucp_return_policy_duplicate_fee_type_on_channel",
                        non_returnable=is_not_accepted,
                        channel_free=False,
                        estimated_max_fee_minor=None,
                        violation_Rule="PR #634 §Return fees duplicate type",
                    )
                seen_channel_specific.add(ch_key)

    # Resolve channel fees for `query_channel`
    channel_specific_untyped_zero = any(
        fee.get("type") is None
        and int(fee.get("amount", -1)) == 0
        and query_channel in (fee.get("methods") or ())
        for fee in fees
    )
    channel_specific_typed_charges = [
        fee
        for fee in fees
        if fee.get("type") is not None
        and query_channel in (fee.get("methods") or ())
        and (int(fee.get("amount", 0)) > 0 or int(fee.get("basis_points", 0)) > 0)
    ]
    if channel_specific_untyped_zero and not channel_specific_typed_charges:
        return UcpReturnPolicyEvaluation(
            allowed=True,
            reason_code="ok",
            non_returnable=is_not_accepted,
            channel_free=True,
            estimated_max_fee_minor=0,
        )

    total_estimated_max = 0
    applicable_entries = [
        fee
        for fee in fees
        if fee.get("methods") is None or query_channel in (fee.get("methods") or ())
    ]
    for fee in applicable_entries:
        ftype = fee.get("type")
        if ftype is None:
            continue
        if "amount" in fee:
            amt = int(fee["amount"])
            if ftype == "dev.ucp.shopping.fee.restocking":
                total_estimated_max += amt * max(returned_units, 1)
            else:
                total_estimated_max += amt
        elif "basis_points" in fee:
            bps = int(fee["basis_points"])
            per_unit = (unit_paid_minor * bps) // 10000
            if "max_amount" in fee:
                per_unit = min(per_unit, int(fee["max_amount"]))
            if ftype == "dev.ucp.shopping.fee.restocking":
                total_estimated_max += per_unit * max(returned_units, 1)
            else:
                total_estimated_max += per_unit

    if platform_claims_free_returns and total_estimated_max > 0:
        return UcpReturnPolicyEvaluation(
            allowed=False,
            reason_code="ucp_return_policy_non_free_channel_claimed_as_free",
            non_returnable=is_not_accepted,
            channel_free=False,
            estimated_max_fee_minor=total_estimated_max,
            violation_Rule="PR #634 §Return fees channel precedence",
        )

    return UcpReturnPolicyEvaluation(
        allowed=True,
        reason_code="ok",
        non_returnable=is_not_accepted,
        channel_free=False,
        estimated_max_fee_minor=total_estimated_max,
    )


@dataclass(frozen=True)
class UcpPurchaseOptionsEvaluation:
    allowed: bool
    reason_code: str
    retained_instrument_ids: tuple[str, ...]
    checkout_status: str
    emitted_warnings: tuple[str, ...]
    emitted_errors: tuple[str, ...]


def evaluate_ucp_purchase_options_and_subscription_split(
    *,
    catalog_purchase_options: Sequence[Mapping[str, Any]],
    line_id: str,
    selected_purchase_option_id: str | None,
    previous_selected_option_had_schedules: bool = False,
    policies: Sequence[Mapping[str, Any]] = (),
    messages: Sequence[Mapping[str, Any]] = (),
    buyer_saw_subscription_disclosure: bool = True,
    ap2_mandate_signed_over_checkout: bool = False,
    is_complete_request: bool = False,
    payment_terms_capability_active: bool = True,
    option_requires_deferred_payment_term: bool = False,
    split_payments_active: bool = False,
    submitted_instruments: Sequence[Mapping[str, Any]] = (),
    immediate_group_instrument_types: Sequence[str] = ("gift_card", "voucher"),
) -> UcpPurchaseOptionsEvaluation:
    """Validate UCP Purchase Options (`PR #890` commit `185a04a8`, stacked on `#987`)."""
    if not catalog_purchase_options:
        return UcpPurchaseOptionsEvaluation(
            allowed=False,
            reason_code="ucp_purchase_options_empty_list",
            retained_instrument_ids=(),
            checkout_status="incomplete",
            emitted_warnings=(),
            emitted_errors=("purchase_options_min_items",),
        )

    seen_ids: set[str] = set()
    for opt in catalog_purchase_options:
        oid = str(opt.get("id", ""))
        if not oid or oid in seen_ids:
            return UcpPurchaseOptionsEvaluation(
                allowed=False,
                reason_code="ucp_purchase_options_duplicate_or_empty_id",
                retained_instrument_ids=(),
                checkout_status="incomplete",
                emitted_warnings=(),
                emitted_errors=("duplicate_option_id",),
            )
        seen_ids.add(oid)

    has_onetime = any(not opt.get("schedules") for opt in catalog_purchase_options)
    first_has_schedules = bool(catalog_purchase_options[0].get("schedules"))
    if has_onetime and first_has_schedules:
        return UcpPurchaseOptionsEvaluation(
            allowed=False,
            reason_code="ucp_purchase_options_default_must_be_onetime_when_present",
            retained_instrument_ids=(),
            checkout_status="incomplete",
            emitted_warnings=(),
            emitted_errors=("default_option_enrolled_subscription",),
        )

    if option_requires_deferred_payment_term and not payment_terms_capability_active:
        return UcpPurchaseOptionsEvaluation(
            allowed=False,
            reason_code="ucp_purchase_options_deferred_trial_requires_payment_terms_capability",
            retained_instrument_ids=(),
            checkout_status="incomplete",
            emitted_warnings=(),
            emitted_errors=("payment_terms_inactive",),
        )

    if is_complete_request and selected_purchase_option_id is not None:
        return UcpPurchaseOptionsEvaluation(
            allowed=False,
            reason_code="ucp_purchase_options_selected_id_must_be_omitted_on_complete",
            retained_instrument_ids=(),
            checkout_status="incomplete",
            emitted_warnings=(),
            emitted_errors=("selected_purchase_option_id_on_complete",),
        )

    # Resolve option selection and handle stale selections (`Selections that no longer resolve`)
    opt_by_id = {str(o["id"]): o for o in catalog_purchase_options}
    effective_id = selected_purchase_option_id or str(catalog_purchase_options[0]["id"])
    selected_opt = opt_by_id.get(effective_id)
    if selected_opt is None:
        if previous_selected_option_had_schedules:
            onetime_candidates = [
                o for o in catalog_purchase_options if not o.get("schedules")
            ]
            if not onetime_candidates:
                return UcpPurchaseOptionsEvaluation(
                    allowed=False,
                    reason_code="ucp_purchase_options_unresolved_subscription_requires_buyer_selection",
                    retained_instrument_ids=(),
                    checkout_status="incomplete",
                    emitted_warnings=("purchase_option_changed",),
                    emitted_errors=("purchase_option_unavailable",),
                )
            return UcpPurchaseOptionsEvaluation(
                allowed=False,
                reason_code="ucp_purchase_options_cross_subscription_substitution_forbidden",
                retained_instrument_ids=(),
                checkout_status="incomplete",
                emitted_warnings=("purchase_option_changed",),
                emitted_errors=(),
            )
        return UcpPurchaseOptionsEvaluation(
            allowed=False,
            reason_code="ucp_purchase_options_stale_selection_changed_warning",
            retained_instrument_ids=(),
            checkout_status="incomplete",
            emitted_warnings=("purchase_option_changed",),
            emitted_errors=(),
        )

    schedules = selected_opt.get("schedules") or ()
    if schedules:
        for sched in schedules:
            if not sched.get("description"):
                return UcpPurchaseOptionsEvaluation(
                    allowed=False,
                    reason_code="ucp_purchase_options_schedule_missing_description",
                    retained_instrument_ids=(),
                    checkout_status="incomplete",
                    emitted_warnings=(),
                    emitted_errors=("schedule_description_missing",),
                )
            totals = sched.get("totals") or ()
            total_entries = [t for t in totals if t.get("type") == "total"]
            if len(total_entries) != 1:
                return UcpPurchaseOptionsEvaluation(
                    allowed=False,
                    reason_code="ucp_purchase_options_schedule_requires_single_total_entry",
                    retained_instrument_ids=(),
                    checkout_status="incomplete",
                    emitted_warnings=(),
                    emitted_errors=("schedule_total_count_invalid",),
                )

        # Must have governing `dev.ucp.shopping.policy.subscription` covering `line_id`
        has_sub_policy = False
        for pol in policies:
            if pol.get("type") == "dev.ucp.shopping.policy.subscription":
                targets = pol.get("applies_to")
                if targets is None or line_id in targets:
                    has_sub_policy = True
                    break
        has_sub_disclosure = any(
            m.get("presentation") == "disclosure"
            and m.get("code") == "dev.ucp.shopping.policy.subscription"
            and line_id in str(m.get("path", ""))
            for m in messages
        )
        if not has_sub_policy or not has_sub_disclosure:
            return UcpPurchaseOptionsEvaluation(
                allowed=False,
                reason_code="ucp_purchase_options_subscription_policy_or_disclosure_missing",
                retained_instrument_ids=(),
                checkout_status="incomplete",
                emitted_warnings=(),
                emitted_errors=("subscription_disclosure_missing",),
            )

        if not buyer_saw_subscription_disclosure and not ap2_mandate_signed_over_checkout:
            return UcpPurchaseOptionsEvaluation(
                allowed=False,
                reason_code="ucp_purchase_options_unacknowledged_disclosure_escalate_continue_url",
                retained_instrument_ids=(),
                checkout_status="requires_escalation",
                emitted_warnings=(),
                emitted_errors=("requires_buyer_review",),
            )

        # Split Payments retention rule (`185a04a8` stacked on `#987`):
        # Only instruments WITHOUT `amount` and NOT in an `immediate` group are retained.
        immediate_set = set(immediate_group_instrument_types)
        retained: list[str] = []
        for inst in submitted_instruments:
            inst_id = str(inst.get("id", ""))
            inst_type = str(inst.get("type", ""))
            sched_type = str(inst.get("schedule_type", ""))
            has_explicit_amount = "amount" in inst and inst["amount"] is not None
            if (
                not has_explicit_amount
                and inst_type not in immediate_set
                and sched_type != "immediate"
            ):
                retained.append(inst_id)

        if split_payments_active and not retained:
            return UcpPurchaseOptionsEvaluation(
                allowed=False,
                reason_code="ucp_purchase_options_no_retained_recurring_instrument",
                retained_instrument_ids=(),
                checkout_status="incomplete",
                emitted_warnings=(),
                emitted_errors=("payment_failed",),
            )

        return UcpPurchaseOptionsEvaluation(
            allowed=True,
            reason_code="ok",
            retained_instrument_ids=tuple(retained),
            checkout_status="ready_for_complete",
            emitted_warnings=(),
            emitted_errors=(),
        )

    return UcpPurchaseOptionsEvaluation(
        allowed=True,
        reason_code="ok",
        retained_instrument_ids=(),
        checkout_status="ready_for_complete",
        emitted_warnings=(),
        emitted_errors=(),
    )


def _iso_date_epoch(date_str: str) -> int:
    return int(
        dt.datetime.fromisoformat(date_str.replace("Z", "+00:00")).timestamp()
    )


def _pro_rata_completed_adjustment(
    order: Mapping[str, Any], line: Mapping[str, Any]
) -> int:
    adjustments = [
        a
        for a in order.get("adjustments", ())
        if a.get("status", "completed") == "completed"
        and a.get("type") in ("refund", "credit", "return")
    ]
    line_id = line["id"]
    labelled = sum(
        int(a.get("amount", 0))
        for a in adjustments
        if a.get("line_item_id") == line_id
    )
    unlabelled = sum(
        int(a.get("amount", 0))
        for a in adjustments
        if a.get("line_item_id") is None
    )
    total = sum(int(ln.get("total", 0)) for ln in order.get("line_items", ()))
    line_total = int(line.get("total", 0))
    share = round(unlabelled * line_total / total) if total > 0 else 0
    return labelled + share


@dataclass(frozen=True)
class Ap2DisputeAndRevocationEvaluation:
    eligible: bool
    outcome: str
    overturn_amount_minor: int
    fee_paid_by: str | None
    liability_target: str
    reason_code: str
    route: str | None = None
    receipt_status: str = "Success"


def evaluate_ap2_post_transaction_dispute_and_open_mandate_revocation(
    dispute_record: Mapping[str, Any],
    *,
    now_date_iso: str = "2025-10-24",
    open_mandate: Mapping[str, Any] | None = None,
    status_list_reachable: bool = True,
    status_list_revoked_indices: Sequence[int] = (),
    max_task_lifetime_sec: int = 86400 * 7,
) -> Ap2DisputeAndRevocationEvaluation:
    """Validate AP2 PR #352 post-transaction dispute resolver and Issue #386 open-mandate revocation."""
    if open_mandate is not None:
        iat = open_mandate.get("iat")
        exp = open_mandate.get("exp")
        if iat is None or exp is None or int(exp) <= int(iat):
            return Ap2DisputeAndRevocationEvaluation(
                eligible=False,
                outcome="rejected",
                overturn_amount_minor=0,
                fee_paid_by="merchant",
                liability_target="verifier",
                reason_code="ap2_open_mandate_missing_or_unbounded_exp",
                receipt_status="Failed",
            )
        if int(exp) - int(iat) > max_task_lifetime_sec:
            return Ap2DisputeAndRevocationEvaluation(
                eligible=False,
                outcome="rejected",
                overturn_amount_minor=0,
                fee_paid_by="merchant",
                liability_target="verifier",
                reason_code="ap2_open_mandate_exp_exceeds_task_lifetime",
                receipt_status="Failed",
            )
        if not status_list_reachable:
            return Ap2DisputeAndRevocationEvaluation(
                eligible=False,
                outcome="rejected",
                overturn_amount_minor=0,
                fee_paid_by="merchant",
                liability_target="verifier",
                reason_code="ap2_open_mandate_status_list_unreachable_fail_closed",
                receipt_status="Failed",
            )
        status_idx = open_mandate.get("status_list_index")
        if status_idx is not None and int(status_idx) in set(status_list_revoked_indices):
            return Ap2DisputeAndRevocationEvaluation(
                eligible=False,
                outcome="revoked",
                overturn_amount_minor=0,
                fee_paid_by="merchant",
                liability_target="shopping_agent",
                reason_code="ap2_open_mandate_cnf_authority_revoked",
                receipt_status="revoked",
            )

    ch = dispute_record.get("checkout_hash")
    pm = dispute_record.get("payment_mandate") or {}
    cr = dispute_record.get("checkout_receipt")
    pr = dispute_record.get("payment_receipt")

    chain_errors: list[str] = []
    if pm.get("transaction_id") != ch:
        chain_errors.append("payment_mandate.transaction_id != checkout_hash")
    if cr is not None and cr.get("reference") != ch:
        chain_errors.append("checkout_receipt.reference != checkout_hash")
    if pr is not None and pr.get("reference") != ch:
        chain_errors.append("payment_receipt.reference != checkout_hash")

    if chain_errors:
        return Ap2DisputeAndRevocationEvaluation(
            eligible=False,
            outcome="not_eligible",
            overturn_amount_minor=0,
            fee_paid_by=None,
            liability_target="network_fraud_process",
            reason_code="ap2_dispute_authorization_chain_broken",
            route="network fraud process",
        )

    if (pr or {}).get("status") != "Success":
        return Ap2DisputeAndRevocationEvaluation(
            eligible=False,
            outcome="not_eligible",
            overturn_amount_minor=0,
            fee_paid_by=None,
            liability_target="none",
            reason_code="ap2_dispute_payment_not_successful",
        )

    now_epoch = _iso_date_epoch(now_date_iso + "T12:00:00+00:00")
    order = dispute_record.get("order") or {}
    lines = order.get("line_items") or [
        {
            "id": "whole-transaction",
            "total": pm["payment_amount"]["amount"],
            "quantity": {"ordered": 1, "current": 1, "fulfilled": 0},
        }
    ]
    line = lines[0]
    line_amt = int(line.get("total", 0))
    adj = _pro_rata_completed_adjustment(order, line)

    # Rule 1: completed adjustment >= line amount -> uphold (moot)
    if line_amt and adj >= line_amt:
        return Ap2DisputeAndRevocationEvaluation(
            eligible=True,
            outcome="uphold",
            overturn_amount_minor=0,
            fee_paid_by="payer",
            liability_target="none_moot_by_prior_adjustment",
            reason_code="ap2_dispute_moot_by_completed_adjustment",
        )

    # Rule 2: mandate scope (charged > mandated, executed > exp, mandate reuse > 1)
    mandated = int(pm["payment_amount"]["amount"])
    charged = int((pr or {}).get("charged_amount", mandated))
    exec_epoch = (
        _iso_date_epoch(pm["execution_date"])
        if pm.get("execution_date")
        else int((pr or {}).get("iat", pm.get("iat", 0)))
    )
    exp_val = pm.get("exp")
    reuse = int(dispute_record.get("mandate_reuse_count", 1))
    after_exp = exp_val is not None and exec_epoch > int(exp_val)
    if charged > mandated or after_exp or reuse > 1:
        dead = after_exp or reuse > 1
        amt = line_amt if dead else min(max(charged - mandated, 0), line_amt)
        return Ap2DisputeAndRevocationEvaluation(
            eligible=True,
            outcome="overturn",
            overturn_amount_minor=amt,
            fee_paid_by="merchant",
            liability_target="merchant",
            reason_code="ap2_dispute_mandate_scope_exceeded_or_reused",
        )

    # Rule 3: merchant performance (canceled without refund, or unfulfilled past estimated_delivery.latest)
    q = line.get("quantity", {"ordered": 1, "current": 1, "fulfilled": 0})
    unfulfilled = max(int(q.get("current", 1)) - int(q.get("fulfilled", 0)), 0)
    est = order.get("estimated_delivery") or {}
    latest = est.get("latest") or est.get("earliest")
    delivery_passed = bool(latest) and now_epoch > _iso_date_epoch(
        str(latest) + "T23:59:59+00:00"
    )
    if order.get("status") == "canceled" and adj < line_amt:
        return Ap2DisputeAndRevocationEvaluation(
            eligible=True,
            outcome="overturn",
            overturn_amount_minor=line_amt - adj,
            fee_paid_by="merchant",
            liability_target="merchant",
            reason_code="ap2_dispute_merchant_canceled_without_refund",
        )
    if unfulfilled > 0 and delivery_passed:
        current_qty = max(int(q.get("current", 1)), 1)
        share = max(round(line_amt * unfulfilled / current_qty) - adj, 0)
        return Ap2DisputeAndRevocationEvaluation(
            eligible=True,
            outcome="overturn",
            overturn_amount_minor=share,
            fee_paid_by="merchant",
            liability_target="merchant",
            reason_code="ap2_dispute_unfulfilled_after_estimated_delivery",
        )

    # Rule 4: instruction vs confirmed_cart conflict -> recorded against AGENT PLATFORM, merchant charge stands
    if dispute_record.get("instruction_cart_conflict"):
        return Ap2DisputeAndRevocationEvaluation(
            eligible=True,
            outcome="uphold",
            overturn_amount_minor=0,
            fee_paid_by="payer",
            liability_target="agent_platform",
            reason_code="ap2_dispute_instruction_cart_conflict_platform_liable",
        )

    return Ap2DisputeAndRevocationEvaluation(
        eligible=True,
        outcome="uphold",
        overturn_amount_minor=0,
        fee_paid_by="payer",
        liability_target="none",
        reason_code="ok",
    )


@dataclass(frozen=True)
class McpTaskLogAndOAuthResourceEvaluation:
    allowed: bool
    reason_code: str
    resumed_sequences: tuple[int, ...]
    requires_final_tasks_get: bool


def evaluate_mcp_task_log_and_oauth_resource_fallback(
    *,
    task_id: str,
    resource_uri: str,
    log_records: Sequence[Mapping[str, Any]],
    last_seen_seq: int = 0,
    client_skips_final_tasks_get: bool = False,
    terminal_result_independent: bool = True,
    protected_resource_metadata_url: str = "https://mcp.merchant.example/v1",
    as_supports_rfc8707_resource_param: bool = True,
    requested_scope_audiences: Sequence[str] = ("api://mcp.merchant.example",),
    token_aud: str = "api://mcp.merchant.example",
    expected_aud: str = "api://mcp.merchant.example",
    token_iss: str = "https://login.microsoftonline.com/tenant/v2.0",
    expected_iss: str = "https://login.microsoftonline.com/tenant/v2.0",
) -> McpTaskLogAndOAuthResourceEvaluation:
    """Validate MCP Issue #3237 (`task-log://{taskId}`) and Issue #1614 (RFC 9728 / single-audience scope fallback)."""
    expected_uri = f"task-log://{task_id}"
    if resource_uri != expected_uri:
        return McpTaskLogAndOAuthResourceEvaluation(
            allowed=False,
            reason_code="mcp_task_log_invalid_resource_uri",
            resumed_sequences=(),
            requires_final_tasks_get=True,
        )

    prev_seq = 0
    resumed: list[int] = []
    for rec in log_records:
        seq = int(rec.get("seq", 0))
        kind = str(rec.get("kind", ""))
        if seq <= prev_seq:
            return McpTaskLogAndOAuthResourceEvaluation(
                allowed=False,
                reason_code="mcp_task_log_non_monotonic_or_duplicate_seq",
                resumed_sequences=(),
                requires_final_tasks_get=True,
            )
        if seq != prev_seq + 1:
            return McpTaskLogAndOAuthResourceEvaluation(
                allowed=False,
                reason_code="mcp_task_log_sequence_gap_detected",
                resumed_sequences=(),
                requires_final_tasks_get=True,
            )
        if not kind or ("/" not in kind and kind not in {"log", "artifact", "status", "approval"}):
            return McpTaskLogAndOAuthResourceEvaluation(
                allowed=False,
                reason_code="mcp_task_log_invalid_record_kind",
                resumed_sequences=(),
                requires_final_tasks_get=True,
            )
        prev_seq = seq
        if seq > last_seen_seq:
            resumed.append(seq)

    if terminal_result_independent and client_skips_final_tasks_get:
        return McpTaskLogAndOAuthResourceEvaluation(
            allowed=False,
            reason_code="mcp_task_log_cannot_replace_terminal_tasks_get",
            resumed_sequences=tuple(resumed),
            requires_final_tasks_get=True,
        )

    # Issue #1614: RFC 9728 resource identifier MUST be https:// URL
    if not protected_resource_metadata_url.startswith("https://"):
        return McpTaskLogAndOAuthResourceEvaluation(
            allowed=False,
            reason_code="mcp_oauth_rfc9728_resource_metadata_must_be_https",
            resumed_sequences=tuple(resumed),
            requires_final_tasks_get=terminal_result_independent,
        )

    # When AS omits/rejects RFC 8707 `resource` param, client MUST fall back to scopes for EXACTLY ONE audience
    if not as_supports_rfc8707_resource_param and len(set(requested_scope_audiences)) != 1:
        return McpTaskLogAndOAuthResourceEvaluation(
            allowed=False,
            reason_code="mcp_oauth_multi_audience_scope_fallback_forbidden",
            resumed_sequences=tuple(resumed),
            requires_final_tasks_get=terminal_result_independent,
        )

    if token_aud != expected_aud or token_iss != expected_iss:
        return McpTaskLogAndOAuthResourceEvaluation(
            allowed=False,
            reason_code="mcp_oauth_token_aud_or_iss_mismatch",
            resumed_sequences=tuple(resumed),
            requires_final_tasks_get=terminal_result_independent,
        )

    return McpTaskLogAndOAuthResourceEvaluation(
        allowed=True,
        reason_code="ok",
        resumed_sequences=tuple(resumed),
        requires_final_tasks_get=terminal_result_independent,
    )
