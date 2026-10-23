"""Stage 174 deterministic guardrails for 2026-10-23 primary-source updates (Part 3):
- Universal-Commerce-Protocol/ucp PR #987 (`2026-10-23T14:53:46Z`):
  Split payments across payment-term schedules (`instrument_group.schedule_type="immediate"`,
  per-checkout `response_schema.config.allowed_combinations` profile narrowing,
  schedule-ordered contribution allocation, and whole-term outbound `amount` reporting).
- agentic-commerce-protocol/agentic-commerce-protocol PR #316 commit `8802ebe` (`2026-10-23T14:24:59Z`):
  ATDRP Section 7.4a Requirement 5 time anchor for ledger-based evidence packs
  (`anchored_digest`, `mechanism` in `{"rfc3161", "opentimestamps"}`, `proof_bytes`,
  `recompute_location`, separate sequence vs. anchor verification, and `unanchored` records
  after the last anchor forbidden as sole basis for time-based dispute grounds).
- x402-foundation/x402 PRs #3910, #3898, #3899, #3892, #3901/#3902, #3903, #3904 (`2026-10-23`):
  Pre-signing multi-transaction group sponsorship invariants (§10.3), payment creation hook
  correlation & before-abort cleanup isolation, HTTP response header overflow cause-chain
  diagnostics (`UND_ERR_HEADERS_OVERFLOW`/`HPE_HEADER_OVERFLOW`), `text/plain` raw 402 body
  preservation, Python EVM once-per-network gas sponsoring RPC warning, `@stellar/stellar-sdk >= 16.4.1`
  (`axios >= 1.20.0`), and SVM batch reservation release after failed local charges.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    code: str
    detail: str
    metadata: dict[str, Any]


# ---------------------------------------------------------------------------
# 1. UCP PR #987: Split Payments Across Payment-Term Schedules
# ---------------------------------------------------------------------------

def validate_ucp_per_checkout_split_combinations(
    *,
    profile_allowed_combinations: list[list[dict[str, Any]]],
    checkout_allowed_combinations: list[list[dict[str, Any]]] | None,
    has_deferred_schedules: bool,
) -> GuardDecision:
    """Enforce UCP PR #987 per-checkout `response_schema.config.allowed_combinations`:
    - Every group's `schedule_type`, if present, MUST be `"immediate"`.
    - Each group's `max` MUST be >= `min` (default 1).
    - Checkout `allowed_combinations` may only narrow the profile's combinations (every checkout
      combination's type set must be admitted by at least one profile combination).
    - When `has_deferred_schedules=True`, every resolved checkout combination MUST require at least
      one group without `schedule_type == "immediate"` (capable of funding later schedules).
    """
    active = (
        checkout_allowed_combinations
        if checkout_allowed_combinations is not None
        else profile_allowed_combinations
    )
    if not isinstance(active, list) or not active:
        return GuardDecision(
            False,
            "ucp_split_combinations_empty",
            "Split payments allowed_combinations must be a non-empty list of combinations",
            {},
        )

    profile_type_signatures: list[set[str]] = []
    for combo in profile_allowed_combinations:
        sig: set[str] = set()
        for grp in combo:
            sig.update(grp.get("types", []))
        profile_type_signatures.append(sig)

    for idx, combo in enumerate(active):
        if not isinstance(combo, list) or not combo:
            return GuardDecision(
                False,
                "ucp_split_combination_invalid_group_list",
                f"Combination at index {idx} must be a non-empty list of instrument groups",
                {"index": idx},
            )
        combo_types: set[str] = set()
        has_deferred_capable_group = False
        for grp in combo:
            g_min = int(grp.get("min", 0))
            g_max = int(grp.get("max", 1))
            if g_max < 1 or g_max < g_min:
                return GuardDecision(
                    False,
                    "ucp_split_group_invalid_min_max",
                    f"Instrument group max ({g_max}) must be >= 1 and >= min ({g_min})",
                    {"min": g_min, "max": g_max},
                )
            sched_type = grp.get("schedule_type")
            if sched_type is not None and sched_type != "immediate":
                return GuardDecision(
                    False,
                    "ucp_split_group_invalid_schedule_type",
                    f"Unsupported instrument_group.schedule_type '{sched_type}'; only 'immediate' is defined",
                    {"schedule_type": sched_type},
                )
            if sched_type is None and g_min >= 1:
                has_deferred_capable_group = True
            combo_types.update(grp.get("types", []))

        if checkout_allowed_combinations is not None:
            if not any(combo_types.issubset(p_sig) for p_sig in profile_type_signatures):
                return GuardDecision(
                    False,
                    "ucp_checkout_combination_widens_profile",
                    "Per-checkout allowed_combinations must only narrow the business profile's allowed_combinations",
                    {"checkout_types": sorted(combo_types)},
                )

        if has_deferred_schedules and not has_deferred_capable_group:
            return GuardDecision(
                False,
                "ucp_deferred_term_missing_deferred_capable_group",
                "Deferred payment terms require at least one mandatory non-immediate instrument group in every combination",
                {"index": idx},
            )

    return GuardDecision(
        True,
        "ucp_per_checkout_split_combinations_ok",
        "UCP PR #987 per-checkout split payment combinations and schedule_type constraints verified",
        {"combination_count": len(active), "has_deferred_schedules": has_deferred_schedules},
    )


def allocate_ucp_split_payments_across_schedules(
    *,
    schedules: list[dict[str, Any]],
    instruments: list[dict[str, Any]],
) -> GuardDecision:
    """Enforce UCP PR #987 split payment allocation across payment-term schedules:
    - `schedules`: each has `{"id": str, "type": "immediate" | "deferred", "amount": int}`
    - `instruments`: each has `{"id": str, "type": str, "schedule_type": str | None,
      "amount": int | None, "available_balance": int | None, "voided_or_unattempted": bool}`
    - Rules:
      1. Due-at-completion is the sum of `type == "immediate"` schedules.
      2. Instruments with `schedule_type == "immediate"` fund ONLY what is due at completion.
         If a specified `amount` on an `immediate` instrument exceeds remaining due-at-completion,
         reject with `immediate_group_amount_exceeds_due_at_completion`.
      3. Open-amount (`amount=None`) instruments in an `immediate` group take up to remaining
         due-at-completion (bounded by `available_balance`); unrestricted open-amount instruments
         take up to remaining total across all schedules.
      4. Outbound `amount` reports each instrument's whole contribution across all schedules of
         the term, and omits `amount` on voided/unattempted instruments.
    """
    if not schedules:
        return GuardDecision(False, "ucp_schedules_empty", "At least one payment schedule is required", {})

    immediate_due = sum(int(s["amount"]) for s in schedules if s.get("type") == "immediate")
    deferred_due = sum(int(s["amount"]) for s in schedules if s.get("type") != "immediate")
    total_due = immediate_due + deferred_due

    specified_sum = sum(
        int(inst["amount"])
        for inst in instruments
        if inst.get("amount") is not None and not inst.get("voided_or_unattempted", False)
    )
    if specified_sum > total_due:
        return GuardDecision(
            False,
            "ucp_specified_amounts_exceed_checkout_total",
            f"Sum of specified instrument amounts ({specified_sum}) exceeds checkout total ({total_due})",
            {"specified_sum": specified_sum, "total_due": total_due},
        )

    remaining_immediate = immediate_due
    remaining_deferred = deferred_due
    outbound_instruments: list[dict[str, Any]] = []

    # Process in submitted order; immediate-group instruments can only draw from remaining_immediate
    for inst in instruments:
        inst_id = str(inst.get("id", ""))
        if inst.get("voided_or_unattempted", False):
            if "amount" in inst and inst["amount"] is not None:
                return GuardDecision(
                    False,
                    "ucp_voided_instrument_must_omit_amount",
                    f"Voided or unattempted instrument '{inst_id}' must omit outbound amount",
                    {"instrument_id": inst_id},
                )
            outbound_instruments.append({"id": inst_id, "type": inst.get("type")})
            continue

        sched_type = inst.get("schedule_type")
        spec_amount = inst.get("amount")
        avail = inst.get("available_balance")

        if sched_type == "immediate":
            if spec_amount is not None:
                amt = int(spec_amount)
                if amt > remaining_immediate:
                    return GuardDecision(
                        False,
                        "immediate_group_amount_exceeds_due_at_completion",
                        f"Immediate-group instrument '{inst_id}' amount ({amt}) exceeds remaining due at completion ({remaining_immediate})",
                        {"instrument_id": inst_id, "amount": amt, "remaining_immediate": remaining_immediate},
                    )
                remaining_immediate -= amt
                contribution = amt
            else:
                cap = remaining_immediate if avail is None else min(int(avail), remaining_immediate)
                remaining_immediate -= cap
                contribution = cap
        else:
            remaining_all = remaining_immediate + remaining_deferred
            if spec_amount is not None:
                amt = int(spec_amount)
                if amt > remaining_all:
                    return GuardDecision(
                        False,
                        "ucp_instrument_amount_exceeds_remaining_total",
                        f"Instrument '{inst_id}' amount ({amt}) exceeds remaining total ({remaining_all})",
                        {"instrument_id": inst_id, "amount": amt, "remaining_total": remaining_all},
                    )
                take_imm = min(amt, remaining_immediate)
                remaining_immediate -= take_imm
                remaining_deferred -= amt - take_imm
                contribution = amt
            else:
                cap = remaining_all if avail is None else min(int(avail), remaining_all)
                take_imm = min(cap, remaining_immediate)
                remaining_immediate -= take_imm
                remaining_deferred -= cap - take_imm
                contribution = cap

        outbound_instruments.append(
            {
                "id": inst_id,
                "type": inst.get("type"),
                "amount": contribution,
            }
        )

    if remaining_immediate != 0 or remaining_deferred != 0:
        return GuardDecision(
            False,
            "ucp_schedules_underfunded",
            "Submitted instruments did not fully fund all payment schedules",
            {"unfunded_immediate": remaining_immediate, "unfunded_deferred": remaining_deferred},
        )

    return GuardDecision(
        True,
        "ucp_split_schedule_allocation_ok",
        "UCP PR #987 split-payment contributions allocated across immediate and deferred schedules",
        {
            "immediate_due": immediate_due,
            "deferred_due": deferred_due,
            "outbound_instruments": outbound_instruments,
        },
    )


# ---------------------------------------------------------------------------
# 2. ACP PR #316 (`8802ebe`): ATDRP §7.4a Req 5 Ledger Time-Anchor Guard
# ---------------------------------------------------------------------------

def validate_acp_atdrp_ledger_time_anchor(
    *,
    sequence_complete: bool,
    anchored_digest: str,
    recomputed_digest: str,
    mechanism: str,
    proof_bytes_present: bool,
    recompute_location: str,
    provider_verified_anchor_proof: bool,
    anchor_time_epoch: int,
    records: list[dict[str, Any]],
    claim_is_time_based_ground: bool,
    claim_relies_solely_on_post_anchor_records: bool,
    treats_anchor_as_truth_of_contents: bool = False,
) -> GuardDecision:
    """Enforce ACP PR #316 commit `8802ebe` (ATDRP Section 7.4a Requirement 5):
    - Sequence completeness (`AP2#290`) and external time anchor (`AP2#338`) fail separately.
    - Anchor requires `anchored_digest == recomputed_digest`, `mechanism in {"rfc3161", "opentimestamps"}`,
      non-empty `proof_bytes`, non-empty `recompute_location`, and `provider_verified_anchor_proof=True`.
    - An anchor attests existence no later than `anchor_time_epoch`, NOT truth of record contents.
    - Records with `timestamp > anchor_time_epoch` are marked `unanchored` and MUST NOT be the
      sole basis for a time-based dispute ground.
    """
    if not sequence_complete:
        return GuardDecision(
            False,
            "acp_ledger_sequence_incomplete",
            "Ledger pack failed internal sequence completeness check (AP2#290) separately from time anchoring",
            {},
        )
    if mechanism not in {"rfc3161", "opentimestamps"}:
        return GuardDecision(
            False,
            "acp_ledger_invalid_anchor_mechanism",
            f"Unsupported ledger time-anchor mechanism '{mechanism}'; must be 'rfc3161' or 'opentimestamps'",
            {"mechanism": mechanism},
        )
    if not anchored_digest or anchored_digest != recomputed_digest:
        return GuardDecision(
            False,
            "acp_ledger_anchored_digest_mismatch",
            "Recomputed ledger set digest does not match anchored_digest",
            {"anchored_digest": anchored_digest, "recomputed_digest": recomputed_digest},
        )
    if not proof_bytes_present or not recompute_location.strip() or not provider_verified_anchor_proof:
        return GuardDecision(
            False,
            "acp_ledger_anchor_proof_unverified",
            "Ledger time anchor requires proof_bytes, recompute_location, and independent TSA/header verification",
            {"recompute_location": recompute_location},
        )
    if treats_anchor_as_truth_of_contents:
        return GuardDecision(
            False,
            "acp_ledger_anchor_attests_existence_not_truth",
            "Time anchor attests only that the ledger set existed by anchor_time, not that a record in it is true",
            {},
        )

    anchored_count = 0
    unanchored_count = 0
    for rec in records:
        ts = int(rec.get("timestamp", 0))
        if ts <= anchor_time_epoch:
            anchored_count += 1
        else:
            unanchored_count += 1

    if claim_is_time_based_ground and claim_relies_solely_on_post_anchor_records:
        return GuardDecision(
            False,
            "acp_unanchored_records_sole_time_ground_forbidden",
            "Records written after the last time anchor are unanchored and MUST NOT be the sole basis for a time-based ground",
            {"anchored_count": anchored_count, "unanchored_count": unanchored_count},
        )

    return GuardDecision(
        True,
        "acp_ledger_time_anchor_ok",
        "ACP ATDRP §7.4a Requirement 5 ledger time anchor and post-anchor boundary verified",
        {
            "mechanism": mechanism,
            "anchored_count": anchored_count,
            "unanchored_count": unanchored_count,
        },
    )


# ---------------------------------------------------------------------------
# 3. x402 PRs #3910, #3898, #3899, #3892, #3901/#3902, #3903, #3904
# ---------------------------------------------------------------------------

def validate_x402_presigning_group_sponsorship(
    *,
    expected_network: str,
    canonical_group_digest: str,
    max_sponsored_fee_minor: int,
    transactions: list[dict[str, Any]],
) -> GuardDecision:
    """Enforce x402 PR #3910 (§10.3 & `scheme_exact.md`) pre-signing multi-transaction group
    sponsorship invariants BEFORE any facilitator private-key signing operation:
    (a) Every transaction's `network` matches `expected_network`.
    (b) In a multi-transaction group (`len(transactions) > 1`), every transaction carries a
        non-null `group_digest` equal to `canonical_group_digest` (blocking `null == null` extraction).
    (c) At most 1 unsigned facilitator fee-payer transaction (`is_unsigned_facilitator_fee_tx=True`)
        appears in the group, and total sponsored fees <= `max_sponsored_fee_minor`.
    (d) No transaction carries clawback (`asset_sender`) or close-to (`close_remainder_to`, `asset_close_to`).
    """
    if not transactions:
        return GuardDecision(False, "x402_group_empty", "Transaction group cannot be empty", {})

    unsigned_facilitator_txs = 0
    total_sponsored_fee = 0
    is_multi = len(transactions) > 1

    for idx, tx in enumerate(transactions):
        if tx.get("network") != expected_network:
            return GuardDecision(
                False,
                "x402_group_tx_network_mismatch",
                f"Transaction {idx} embedded network '{tx.get('network')}' != '{expected_network}'",
                {"index": idx},
            )
        if is_multi:
            g_digest = tx.get("group_digest")
            if not g_digest or g_digest != canonical_group_digest:
                return GuardDecision(
                    False,
                    "x402_group_digest_missing_or_mismatch",
                    f"Transaction {idx} missing or mismatched canonical group_digest",
                    {"index": idx, "group_digest": g_digest},
                )
        if tx.get("asset_sender") or tx.get("close_remainder_to") or tx.get("asset_close_to"):
            return GuardDecision(
                False,
                "x402_group_clawback_or_close_to_forbidden",
                f"Transaction {idx} contains forbidden clawback or close-to drain fields",
                {"index": idx},
            )
        if tx.get("is_unsigned_facilitator_fee_tx", False):
            unsigned_facilitator_txs += 1
            total_sponsored_fee += int(tx.get("fee_minor", 0))

    if unsigned_facilitator_txs > 1:
        return GuardDecision(
            False,
            "x402_group_multiple_facilitator_fee_txs",
            f"At most one unsigned facilitator fee-payer transaction is allowed (got {unsigned_facilitator_txs})",
            {"unsigned_facilitator_txs": unsigned_facilitator_txs},
        )
    if total_sponsored_fee > max_sponsored_fee_minor:
        return GuardDecision(
            False,
            "x402_group_sponsored_fee_cap_exceeded",
            f"Total facilitator-sponsored fee ({total_sponsored_fee}) exceeds cap ({max_sponsored_fee_minor})",
            {"total_sponsored_fee": total_sponsored_fee, "max_sponsored_fee_minor": max_sponsored_fee_minor},
        )

    return GuardDecision(
        True,
        "x402_presigning_group_sponsorship_ok",
        "x402 §10.3 pre-signing group sponsorship invariants verified prior to private-key signing",
        {"tx_count": len(transactions), "total_sponsored_fee": total_sponsored_fee},
    )


def validate_x402_payment_creation_hook_correlation(
    *,
    shared_context_id_across_phases: bool,
    before_hook_aborted: bool,
    failure_cleanup_hooks_ran: bool,
    recovery_overrode_before_abort: bool,
    cleanup_exception_replaced_original_error: bool,
    payload_creation_started_after_before_abort: bool,
) -> GuardDecision:
    """Enforce x402 PR #3898 (`@x402/core` `createPaymentPayload` hook correlation & abort cleanup):
    - Manual, scheme, and extension hooks share one context object per `createPaymentPayload` call.
    - When a `before` hook aborts/throws: failure cleanup hooks MUST run, recovery return values
      MUST NOT override the abort, cleanup exceptions MUST NOT replace the original error, and
      payload creation MUST NOT start.
    """
    if not shared_context_id_across_phases:
        return GuardDecision(
            False,
            "x402_hook_context_not_correlated",
            "before, after, and failure hooks must share a single per-call context object",
            {},
        )
    if before_hook_aborted:
        if not failure_cleanup_hooks_ran:
            return GuardDecision(
                False,
                "x402_before_abort_skipped_failure_cleanup",
                "Failure cleanup hooks must run when a before hook aborts or throws",
                {},
            )
        if recovery_overrode_before_abort:
            return GuardDecision(
                False,
                "x402_recovery_cannot_override_before_abort",
                "Failure hook recovery results cannot override a before-hook rejection",
                {},
            )
        if cleanup_exception_replaced_original_error:
            return GuardDecision(
                False,
                "x402_cleanup_exception_masked_original_abort",
                "Cleanup hook exceptions must not replace the original before-hook failure",
                {},
            )
        if payload_creation_started_after_before_abort:
            return GuardDecision(
                False,
                "x402_payload_created_after_before_abort",
                "Payment payload creation must never start after a before-hook abort",
                {},
            )

    return GuardDecision(
        True,
        "x402_payment_creation_hooks_ok",
        "x402 PR #3898 payment creation hook correlation and before-abort cleanup invariants verified",
        {"before_hook_aborted": before_hook_aborted},
    )


def validate_x402_svm_failed_local_charge_cleanup(
    *,
    channel_capacity: int,
    committed_charged: int,
    sibling_reserved: int,
    failed_request_reserved: int,
    local_charge_failed: bool,
    failed_reservation_released: bool,
    sibling_reservation_preserved: bool,
    consumed_request_id_retained: bool,
    cleanup_storage_failed: bool = False,
    original_abort_reason_preserved: bool = True,
) -> GuardDecision:
    """Enforce x402 PR #3892 (`@x402/svm` & Go SVM batch reservation cleanup after failed local charge):
    - When a local batch charge fails in `beforeSettle`, the failed request's reservation MUST be
      released (unless cleanup storage fails, in which case the original abort reason and context
      are retained for explicit retry), while sibling reservations, committed accounting, and
      consumed request IDs are preserved.
    """
    if local_charge_failed:
        if not sibling_reservation_preserved or not consumed_request_id_retained:
            return GuardDecision(
                False,
                "x402_svm_cleanup_corrupted_sibling_or_request_id",
                "SVM failed-charge cleanup must preserve sibling reservations and consumed request IDs",
                {},
            )
        if cleanup_storage_failed:
            if not original_abort_reason_preserved:
                return GuardDecision(
                    False,
                    "x402_svm_cleanup_storage_error_masked_abort",
                    "When cleanup storage fails, the original abort classification must be preserved",
                    {},
                )
        elif not failed_reservation_released:
            return GuardDecision(
                False,
                "x402_svm_failed_charge_reservation_leaked",
                "Failed SVM local batch charge must release its reserved capacity so cooperative close is not blocked",
                {"leaked_reservation": failed_request_reserved},
            )

    available_capacity = (
        channel_capacity
        - committed_charged
        - sibling_reserved
        - (0 if (not local_charge_failed or failed_reservation_released) else failed_request_reserved)
    )
    return GuardDecision(
        True,
        "x402_svm_batch_reservation_cleanup_ok",
        "x402 PR #3892 SVM failed local charge reservation cleanup verified",
        {"available_capacity": available_capacity, "committed_charged": committed_charged},
    )


def validate_x402_http_header_overflow_and_text_error(
    *,
    error_cause_codes: list[str],
    preserved_original_cause: bool,
    triggered_auto_retry_on_overflow: bool,
    declared_media_type: str,
    response_body_is_raw_text: bool,
    appended_duplicate_json_content_type: bool,
    stellar_sdk_version: tuple[int, int, int] = (16, 4, 1),
    axios_version: tuple[int, int, int] = (1, 20, 0),
) -> GuardDecision:
    """Enforce x402 PR #3899 (HTTP header overflow diagnostics), PR #3901/#3902 (`text/plain`
    error bodies), and PR #3904 (`@stellar/stellar-sdk >= 16.4.1` with `axios >= 1.20.0`).
    """
    is_overflow = any(
        code in {"UND_ERR_HEADERS_OVERFLOW", "HPE_HEADER_OVERFLOW"} for code in error_cause_codes
    )
    if is_overflow:
        if not preserved_original_cause:
            return GuardDecision(
                False,
                "x402_header_overflow_lost_original_cause",
                "Header overflow diagnostic wrapper must retain the original transport error as cause",
                {},
            )
        if triggered_auto_retry_on_overflow:
            return GuardDecision(
                False,
                "x402_header_overflow_must_not_auto_retry",
                "Response header overflow failures must fail before payment creation without automatic retry",
                {},
            )

    if declared_media_type == "text/plain":
        if not response_body_is_raw_text or appended_duplicate_json_content_type:
            return GuardDecision(
                False,
                "x402_text_plain_body_json_quoted_or_dup_header",
                "text/plain payment-error responses must send raw text without JSON string quoting or duplicate application/json Content-Type",
                {},
            )

    if stellar_sdk_version < (16, 4, 1) or axios_version < (1, 20, 0):
        return GuardDecision(
            False,
            "x402_stellar_sdk_axios_vulnerable_floor",
            "@x402/stellar requires @stellar/stellar-sdk >= 16.4.1 shipping axios >= 1.20.0",
            {"stellar_sdk_version": stellar_sdk_version, "axios_version": axios_version},
        )

    return GuardDecision(
        True,
        "x402_http_diagnostics_and_stellar_floor_ok",
        "x402 PR #3899/#3901/#3902/#3904 HTTP header overflow diagnostics, text/plain body & Stellar SDK floor verified",
        {"is_overflow": is_overflow, "declared_media_type": declared_media_type},
    )
