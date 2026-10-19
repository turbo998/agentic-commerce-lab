"""Stage 39: UCP Food Checkout & Fulfillment (`#897`), Lodging Deterministic Cancellation
Schedule (`#861`), Bulk Catalog Feed Snapshot vs Live Authority (`#866`), Identity Linking
DNS-Delegated Email Matching & RFC 9728 Multi-Entry Discovery (`#876`, `#891`), and
RFC 9421 §3.3.4/§3.3.5 ECDSA Raw `r||s` Signature Encoding (`#963`).

Pure Python standard library; zero network calls; zero secrets.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any


@dataclass(frozen=True)
class UCPFoodCheckoutFulfillmentGuardResult:
    admitted: bool
    decision_code: str
    computed_subtotal_minor: int
    warning_codes: tuple[str, ...]


@dataclass(frozen=True)
class UCPLodgingCancellationScheduleResult:
    admitted: bool
    decision_code: str
    selected_interval_index: int
    selected_outcome_type: str
    resolved_penalty_minor: int | None


@dataclass(frozen=True)
class UCPBulkCatalogFeedGuardResult:
    admitted: bool
    decision_code: str
    verified_file_count: int
    live_lookup_required_for_checkout: bool


@dataclass(frozen=True)
class UCPIdentityLinkingAndEcdsaGuardResult:
    admitted: bool
    decision_code: str
    selected_authorization_server: str | None
    linked_key: tuple[str, str] | None
    ecdsa_raw_rs_valid: bool


def evaluate_ucp_food_checkout_and_fulfillment_guard(
    *,
    session_establishment_id: str,
    line_items: tuple[dict[str, Any], ...],
    paid_addon_keywords: tuple[str, ...],
    note_attempts_silent_surcharge: bool,
    fulfillment_destinations_count: int,
    buyer_selected_tip_minor: int,
    totals_tip_entry_minor: int,
    kitchen_is_open: bool = True,
    minimum_order_minor: int = 0,
) -> UCPFoodCheckoutFulfillmentGuardResult:
    """Enforce UCP PR #897 (`dev.ucp.food.checkout` & `dev.ucp.food.fulfillment`)."""
    if not kitchen_is_open:
        return UCPFoodCheckoutFulfillmentGuardResult(
            admitted=False,
            decision_code="location_closed",
            computed_subtotal_minor=0,
            warning_codes=(),
        )

    if fulfillment_destinations_count != 1:
        return UCPFoodCheckoutFulfillmentGuardResult(
            admitted=False,
            decision_code="FOOD_SPLIT_DESTINATION_DELIVERY_FORBIDDEN",
            computed_subtotal_minor=0,
            warning_codes=(),
        )

    computed_subtotal = 0
    warnings: list[str] = []

    for item in line_items:
        dish = item.get("dish") or {}
        dish_est_id = str(dish.get("establishment_id", session_establishment_id))
        if dish_est_id != session_establishment_id:
            return UCPFoodCheckoutFulfillmentGuardResult(
                admitted=False,
                decision_code="MULTI_ESTABLISHMENT_OR_FOREIGN_DISH_BLOCKED",
                computed_subtotal_minor=0,
                warning_codes=(),
            )

        dish_price = int(dish.get("price_minor", 0))
        mods = dish.get("modifications") or ()
        seen_mod_ids: set[str] = set()
        mod_sum = 0
        for mod in mods:
            mod_id = str(mod.get("id", ""))
            if mod_id in seen_mod_ids:
                return UCPFoodCheckoutFulfillmentGuardResult(
                    admitted=False,
                    decision_code="DUPLICATE_MODIFICATION_ID_MUST_USE_QUANTITY",
                    computed_subtotal_minor=0,
                    warning_codes=(),
                )
            seen_mod_ids.add(mod_id)
            mod_qty = int(mod.get("quantity", 1))
            mod_price = int(mod.get("price_minor", 0))
            mod_sum += mod_price * mod_qty

        qty = int(item.get("quantity", 1))
        expected_line_subtotal = (dish_price + mod_sum) * qty
        reported_line_subtotal = int(item.get("reported_subtotal_minor", expected_line_subtotal))
        if reported_line_subtotal != expected_line_subtotal:
            return UCPFoodCheckoutFulfillmentGuardResult(
                admitted=False,
                decision_code="FOOD_LINE_ITEM_ARITHMETIC_MISMATCH",
                computed_subtotal_minor=expected_line_subtotal,
                warning_codes=(),
            )
        computed_subtotal += expected_line_subtotal

        note_text = str(dish.get("note", "")).lower()
        if any(kw.lower() in note_text for kw in paid_addon_keywords):
            warnings.append("note_contains_modification")
            if note_attempts_silent_surcharge:
                return UCPFoodCheckoutFulfillmentGuardResult(
                    admitted=False,
                    decision_code="PAID_ADDON_IN_FREEFORM_KITCHEN_NOTE_BLOCKED",
                    computed_subtotal_minor=computed_subtotal,
                    warning_codes=tuple(warnings),
                )

    if computed_subtotal < minimum_order_minor:
        return UCPFoodCheckoutFulfillmentGuardResult(
            admitted=False,
            decision_code="minimum_order_unmet",
            computed_subtotal_minor=computed_subtotal,
            warning_codes=tuple(warnings),
        )

    if buyer_selected_tip_minor != totals_tip_entry_minor:
        return UCPFoodCheckoutFulfillmentGuardResult(
            admitted=False,
            decision_code="FOOD_TIP_TOTALS_REFLECTION_MISMATCH",
            computed_subtotal_minor=computed_subtotal,
            warning_codes=tuple(warnings),
        )

    return UCPFoodCheckoutFulfillmentGuardResult(
        admitted=True,
        decision_code="UCP_FOOD_CHECKOUT_AND_FULFILLMENT_VERIFIED",
        computed_subtotal_minor=computed_subtotal,
        warning_codes=tuple(warnings),
    )


def evaluate_ucp_lodging_cancellation_schedule_guard(
    *,
    anchor_epoch: int,
    intervals: tuple[dict[str, Any], ...],
    eval_instant_epoch: int,
    authoritative_booking_base_amount_minor: int | None,
    platform_extrapolated_cash_from_symbolic_without_base: bool,
    targeted_stays_count: int,
    platform_multiplied_penalty_across_stays: bool,
) -> UCPLodgingCancellationScheduleResult:
    """Enforce UCP PR #861 deterministic lodging cancellation schedules with half-open `[start, end)` cutoffs."""
    if not intervals:
        return UCPLodgingCancellationScheduleResult(
            admitted=False,
            decision_code="EMPTY_CANCELLATION_SCHEDULE_FALLBACK_TO_PROSE",
            selected_interval_index=-1,
            selected_outcome_type="fallback_prose",
            resolved_penalty_minor=None,
        )

    # Verify strict ordering of cutoffs
    prev_end: int | None = None
    for interval in intervals:
        start = int(interval["start_epoch"])
        end = interval.get("end_epoch")
        if prev_end is not None and start != prev_end:
            return UCPLodgingCancellationScheduleResult(
                admitted=False,
                decision_code="NON_CONTIGUOUS_OR_UNORDERED_SCHEDULE_FALLBACK_TO_PROSE",
                selected_interval_index=-1,
                selected_outcome_type="fallback_prose",
                resolved_penalty_minor=None,
            )
        if end is not None:
            end_int = int(end)
            if end_int <= start:
                return UCPLodgingCancellationScheduleResult(
                    admitted=False,
                    decision_code="INVALID_ZERO_OR_NEGATIVE_CUTOFF_INTERVAL",
                    selected_interval_index=-1,
                    selected_outcome_type="fallback_prose",
                    resolved_penalty_minor=None,
                )
            prev_end = end_int

    if targeted_stays_count > 1 and platform_multiplied_penalty_across_stays:
        return UCPLodgingCancellationScheduleResult(
            admitted=False,
            decision_code="MULTI_STAY_PENALTY_MULTIPLICATION_BLOCKED",
            selected_interval_index=-1,
            selected_outcome_type="blocked",
            resolved_penalty_minor=None,
        )

    if authoritative_booking_base_amount_minor is None and platform_extrapolated_cash_from_symbolic_without_base:
        return UCPLodgingCancellationScheduleResult(
            admitted=False,
            decision_code="SYMBOLIC_PENALTY_EXTRAPOLATED_TO_CASH_WITHOUT_BASE_BLOCKED",
            selected_interval_index=-1,
            selected_outcome_type="blocked",
            resolved_penalty_minor=None,
        )

    # Half-open selection: `start_epoch <= eval_instant_epoch < end_epoch` (or `end_epoch is None`)
    selected_idx = -1
    selected_interval: dict[str, Any] | None = None
    for idx, interval in enumerate(intervals):
        start = int(interval["start_epoch"])
        end = interval.get("end_epoch")
        if eval_instant_epoch >= start and (end is None or eval_instant_epoch < int(end)):
            selected_idx = idx
            selected_interval = interval
            break

    if selected_interval is None or selected_idx > anchor_epoch:
        return UCPLodgingCancellationScheduleResult(
            admitted=False,
            decision_code="INSTANT_OUTSIDE_SCHEDULE_BOUNDS_FALLBACK_TO_PROSE",
            selected_interval_index=-1,
            selected_outcome_type="fallback_prose",
            resolved_penalty_minor=None,
        )

    outcome_type = str(selected_interval.get("outcome_type", ""))
    if outcome_type not in {"fixed_fee", "percentage", "measure_nights"}:
        return UCPLodgingCancellationScheduleResult(
            admitted=False,
            decision_code="UNSUPPORTED_OUTCOME_KIND_FALLBACK_TO_PROSE",
            selected_interval_index=selected_idx,
            selected_outcome_type="fallback_prose",
            resolved_penalty_minor=None,
        )

    resolved_penalty: int | None = None
    if outcome_type == "fixed_fee":
        resolved_penalty = int(selected_interval["amount_minor"])
    elif outcome_type == "percentage" and authoritative_booking_base_amount_minor is not None:
        bps = int(selected_interval["basis_points"])
        resolved_penalty = (authoritative_booking_base_amount_minor * bps) // 10_000

    return UCPLodgingCancellationScheduleResult(
        admitted=True,
        decision_code="LODGING_DETERMINISTIC_CANCELLATION_SCHEDULE_SELECTED",
        selected_interval_index=selected_idx,
        selected_outcome_type=outcome_type,
        resolved_penalty_minor=resolved_penalty,
    )


def evaluate_ucp_bulk_catalog_feed_guard(
    *,
    manifest_snapshot_immutable: bool,
    feed_files: tuple[dict[str, str], ...],
    used_directly_for_checkout_without_live_lookup: bool,
) -> UCPBulkCatalogFeedGuardResult:
    """Enforce UCP PR #866 (`dev.ucp.common.feed` & `dev.ucp.shopping.catalog.feed`) snapshot integrity and live serving authority."""
    if not manifest_snapshot_immutable:
        return UCPBulkCatalogFeedGuardResult(
            admitted=False,
            decision_code="FEED_MANIFEST_MUTATION_VIOLATION_BLOCKED",
            verified_file_count=0,
            live_lookup_required_for_checkout=True,
        )

    verified = 0
    for f in feed_files:
        fmt = f.get("format", "")
        content_bytes = f.get("content", "").encode("utf-8")
        expected_rfc9530 = "sha-256=:" + hashlib.sha256(content_bytes).hexdigest() + ":"
        if fmt not in {"jsonl+gzip", "parquet"} or f.get("rfc9530_digest") != expected_rfc9530:
            return UCPBulkCatalogFeedGuardResult(
                admitted=False,
                decision_code="FEED_SNAPSHOT_DIGEST_OR_FORMAT_VIOLATION_BLOCKED",
                verified_file_count=verified,
                live_lookup_required_for_checkout=True,
            )
        verified += 1

    if used_directly_for_checkout_without_live_lookup:
        return UCPBulkCatalogFeedGuardResult(
            admitted=False,
            decision_code="STALE_BULK_FEED_USED_AS_CHECKOUT_AUTHORITY_BLOCKED",
            verified_file_count=verified,
            live_lookup_required_for_checkout=True,
        )

    return UCPBulkCatalogFeedGuardResult(
        admitted=True,
        decision_code="UCP_BULK_CATALOG_FEED_AND_LIVE_AUTHORITY_VERIFIED",
        verified_file_count=verified,
        live_lookup_required_for_checkout=True,
    )


def evaluate_ucp_identity_linking_and_ecdsa_raw_rs_guard(
    *,
    authorization_servers: tuple[dict[str, Any], ...],
    platform_aborted_on_first_mismatch: bool,
    attempt_accelerated_email_autolink: bool,
    idp_email_verified: bool,
    dns_txt_delegated_issuer: str | None,
    grant_iss: str,
    grant_sub: str,
    business_verified_existing_account_email: bool,
    existing_linked_sub_for_iss: str | None,
    ecdsa_curve: str,  # "P-256" | "P-384"
    ecdsa_signature_bytes_len: int,
    ecdsa_is_asn1_der_encoded: bool,
) -> UCPIdentityLinkingAndEcdsaGuardResult:
    """Enforce UCP PRs #891 (RFC 9728 multi-entry discovery), #876 (DNS-delegated email linking), and #963 (RFC 9421 ECDSA raw r||s)."""
    expected_len = 64 if ecdsa_curve == "P-256" else (96 if ecdsa_curve == "P-384" else -1)
    if ecdsa_is_asn1_der_encoded or ecdsa_signature_bytes_len != expected_len:
        return UCPIdentityLinkingAndEcdsaGuardResult(
            admitted=False,
            decision_code="ASN1_DER_OR_INVALID_LENGTH_ECDSA_SIGNATURE_BLOCKED",
            selected_authorization_server=None,
            linked_key=None,
            ecdsa_raw_rs_valid=False,
        )

    if platform_aborted_on_first_mismatch and len(authorization_servers) > 1:
        return UCPIdentityLinkingAndEcdsaGuardResult(
            admitted=False,
            decision_code="PREMATURE_ABORT_ON_FIRST_MISMATCHED_AUTH_SERVER_BLOCKED",
            selected_authorization_server=None,
            linked_key=None,
            ecdsa_raw_rs_valid=True,
        )

    selected_as: str | None = None
    for entry in authorization_servers:
        entry_uri = str(entry.get("entry_uri", ""))
        discovered_issuer = str(entry.get("discovered_metadata_issuer", ""))
        usable_client = bool(entry.get("platform_holds_usable_client", True))
        # RFC 8414 §3.3 byte-for-byte issuer match
        if entry_uri and entry_uri == discovered_issuer and usable_client:
            selected_as = entry_uri
            break

    if selected_as is None:
        return UCPIdentityLinkingAndEcdsaGuardResult(
            admitted=False,
            decision_code="NO_VALID_RFC9728_AUTHORIZATION_SERVER_REMAINING",
            selected_authorization_server=None,
            linked_key=None,
            ecdsa_raw_rs_valid=True,
        )

    if attempt_accelerated_email_autolink:
        if (
            not idp_email_verified
            or not dns_txt_delegated_issuer
            or dns_txt_delegated_issuer != grant_iss
            or not business_verified_existing_account_email
            or (existing_linked_sub_for_iss is not None and existing_linked_sub_for_iss != grant_sub)
        ):
            return UCPIdentityLinkingAndEcdsaGuardResult(
                admitted=False,
                decision_code="UNAUTHORIZED_ACCELERATED_IDP_EMAIL_AUTOLINK_BLOCKED",
                selected_authorization_server=selected_as,
                linked_key=None,
                ecdsa_raw_rs_valid=True,
            )

    return UCPIdentityLinkingAndEcdsaGuardResult(
        admitted=True,
        decision_code="UCP_IDENTITY_LINKING_AND_ECDSA_RAW_RS_VERIFIED",
        selected_authorization_server=selected_as,
        linked_key=(grant_iss, grant_sub),
        ecdsa_raw_rs_valid=True,
    )
