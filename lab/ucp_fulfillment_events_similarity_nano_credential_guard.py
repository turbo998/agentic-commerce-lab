"""Stage 47 deterministic guard: UCP standardized fulfillment events (#979),
catalog similarity extension & seller/business identity (#977/#962/#939),
Nano (XNO) payment instrument session binding (#862), and credential echo /
cart-only checkout / escalation / deferred terms / lodging guards
(#868/#940/#912/#908/#934/#870).
"""

from __future__ import annotations

import base64
from datetime import date
import re
from typing import Any

WELL_KNOWN_FULFILLMENT_EVENT_TYPES = frozenset(
    {
        "processing",
        "shipped",
        "in_transit",
        "delivered",
        "canceled",
    }
)

FORBIDDEN_FULFILLMENT_EVENT_SYNONYMS: dict[str, str] = {
    "preparing": "processing",
    "packing": "processing",
    "label_created": "processing",
    "dispatched": "shipped",
    "handed_to_carrier": "shipped",
    "sent": "shipped",
    "on_the_way": "in_transit",
    "out_for_delivery": "in_transit",
    "moving": "in_transit",
    "finished": "delivered",
    "completed": "delivered",
    "received": "delivered",
    "cancelled": "canceled",
    "aborted": "canceled",
    "voided": "canceled",
}

NANO_ADDRESS_RE = re.compile(r"^nano_[13][13456789a-km-uw-z]{59}$")
NANO_RAW_AMOUNT_RE = re.compile(r"^[1-9][0-9]*$")
NANO_BLOCK_HASH_RE = re.compile(r"^[0-9A-Fa-f]{64}$")

IRREVERSIBLE_REST_OPERATIONS = frozenset(
    {
        "complete_checkout",
        "cancel_checkout",
        "cancel_cart",
        "complete_booking_session",
        "cancel_booking_session",
    }
)

RELAXED_CREATE_UPDATE_REST_OPERATIONS = frozenset(
    {
        "create_checkout",
        "update_checkout",
        "create_cart",
        "update_cart",
        "create_booking_session",
        "update_booking_session",
    }
)

SENSITIVE_CREDENTIAL_FIELDS = frozenset(
    {
        "number",
        "cvc",
        "cryptogram",
        "token_requestor_id",
    }
)


def evaluate_ucp_standardized_fulfillment_events_and_split_shipment_guard(
    context: dict[str, Any],
) -> dict[str, Any]:
    """Enforce UCP PR #979 standardized fulfillment event types and split-shipment rules."""
    events = context.get("fulfillment_events") or []
    line_items = context.get("line_items") or []
    platform_summed_event_quantities = bool(
        context.get("platform_summed_event_quantities", False)
    )
    platform_inferred_global_order_status_from_latest_event = bool(
        context.get("platform_inferred_global_order_status_from_latest_event", False)
    )
    label_created_without_carrier_handoff_marked_shipped = bool(
        context.get("label_created_without_carrier_handoff_marked_shipped", False)
    )

    if label_created_without_carrier_handoff_marked_shipped:
        return {
            "allowed": False,
            "decision_code": "LABEL_CREATION_WITHOUT_HANDOFF_MARKED_SHIPPED_BLOCKED",
            "well_known_event_count": 0,
            "custom_event_count": 0,
        }

    if (
        platform_summed_event_quantities
        or platform_inferred_global_order_status_from_latest_event
    ):
        return {
            "allowed": False,
            "decision_code": "EVENT_QUANTITY_SUMMING_OR_GLOBAL_STATUS_COLLAPSE_BLOCKED",
            "well_known_event_count": 0,
            "custom_event_count": 0,
        }

    well_known_count = 0
    custom_count = 0
    for evt in events:
        evt_type = str(evt.get("type") or "").strip()
        if not evt_type:
            return {
                "allowed": False,
                "decision_code": "FULFILLMENT_EVENT_TYPE_MISSING_BLOCKED",
                "well_known_event_count": well_known_count,
                "custom_event_count": custom_count,
            }

        if evt_type.lower() in FORBIDDEN_FULFILLMENT_EVENT_SYNONYMS:
            return {
                "allowed": False,
                "decision_code": "CUSTOM_SYNONYM_FOR_WELL_KNOWN_FULFILLMENT_EVENT_BLOCKED",
                "canonical_well_known_type": FORBIDDEN_FULFILLMENT_EVENT_SYNONYMS[
                    evt_type.lower()
                ],
                "well_known_event_count": well_known_count,
                "custom_event_count": custom_count,
            }

        has_description_key = "description" in evt and evt.get("description") is not None
        desc_raw = str(evt.get("description") or "")

        if evt_type in WELL_KNOWN_FULFILLMENT_EVENT_TYPES:
            if has_description_key and not desc_raw.strip():
                return {
                    "allowed": False,
                    "decision_code": "EMPTY_FULFILLMENT_EVENT_DESCRIPTION_BLOCKED",
                    "well_known_event_count": well_known_count,
                    "custom_event_count": custom_count,
                }
            well_known_count += 1
        else:
            if not has_description_key or not desc_raw.strip():
                return {
                    "allowed": False,
                    "decision_code": "CUSTOM_FULFILLMENT_EVENT_MISSING_DESCRIPTION_BLOCKED",
                    "well_known_event_count": well_known_count,
                    "custom_event_count": custom_count,
                }
            custom_count += 1

    for li in line_items:
        qty = li.get("quantity") or {}
        total_qty = int(qty.get("total", 0))
        fulfilled_qty = int(qty.get("fulfilled", 0))
        status = str(li.get("status") or "")
        expected_status = (
            "fulfilled"
            if total_qty > 0 and fulfilled_qty == total_qty
            else ("partial" if fulfilled_qty > 0 else "processing")
        )
        if status and status != expected_status:
            return {
                "allowed": False,
                "decision_code": "LINE_ITEM_QUANTITY_DERIVED_STATUS_MISMATCH_BLOCKED",
                "expected_status": expected_status,
                "well_known_event_count": well_known_count,
                "custom_event_count": custom_count,
            }

    return {
        "allowed": True,
        "decision_code": "UCP_STANDARDIZED_FULFILLMENT_EVENTS_VERIFIED",
        "well_known_event_count": well_known_count,
        "custom_event_count": custom_count,
    }


def evaluate_ucp_catalog_similarity_extension_and_image_anchor_guard(
    context: dict[str, Any],
) -> dict[str, Any]:
    """Enforce UCP PR #977 dev.ucp.shopping.catalog.similarity and PRs #962/#939 identity rules."""
    extension_declared = bool(context.get("similarity_extension_declared", True))
    request_uses_like_or_include = bool(
        context.get("request_uses_like_or_include", True)
    )
    config = context.get("similarity_config") or {}
    like_config = config.get("like") or {}
    max_items = int(like_config.get("max_items", 1))
    images_config = like_config.get("images") or {}
    max_image_items = int(images_config.get("max_items", 0))
    allowed_image_types = set(images_config.get("types") or [])
    max_image_bytes = int(images_config.get("max_bytes", 0))

    seller_logo_treated_as_mor = bool(
        context.get("seller_logo_treated_as_mor", False)
    )
    business_identity_conflated_with_branch_location = bool(
        context.get("business_identity_conflated_with_branch_location", False)
    )
    fallback_to_plain_search_when_all_anchors_dropped = bool(
        context.get("fallback_to_plain_search_when_all_anchors_dropped", False)
    )

    if seller_logo_treated_as_mor or business_identity_conflated_with_branch_location:
        return {
            "allowed": False,
            "decision_code": "SELLER_LOGO_TREATED_AS_MOR_OR_LOCATION_CONFLATION_BLOCKED",
            "accepted_anchor_count": 0,
            "messages": [],
        }

    if request_uses_like_or_include and not extension_declared:
        return {
            "allowed": False,
            "decision_code": "SIMILARITY_EXTENSION_NOT_DECLARED_IN_PROFILE_BLOCKED",
            "accepted_anchor_count": 0,
            "messages": [],
        }

    raw_anchors = list(context.get("like_anchors") or [])
    messages: list[str] = []
    if len(raw_anchors) > max_items:
        raw_anchors = raw_anchors[:max_items]
        messages.append("batch_limit_applied")

    accepted_anchors: list[dict[str, Any]] = []
    accepted_images = 0
    for anchor in raw_anchors:
        if "image" in anchor and anchor["image"] is not None:
            img = anchor["image"]
            content_type = str(img.get("content_type") or "")
            data_str = str(img.get("data") or "")
            if max_image_items <= 0 or accepted_images >= max_image_items:
                messages.append("image_type_unsupported")
                continue
            if content_type not in allowed_image_types:
                messages.append("image_type_unsupported")
                continue
            if max_image_bytes > 0 and len(data_str) > max_image_bytes:
                messages.append("image_too_large")
                continue
            try:
                base64.b64decode(data_str.encode("ascii"), validate=True)
            except Exception:
                messages.append("image_invalid")
                continue
            accepted_images += 1
            accepted_anchors.append(anchor)
        else:
            if bool(anchor.get("resolved", True)):
                accepted_anchors.append(anchor)
            else:
                messages.append("not_found")

    if raw_anchors and not accepted_anchors and fallback_to_plain_search_when_all_anchors_dropped:
        return {
            "allowed": False,
            "decision_code": "ALL_ANCHORS_DROPPED_FALLBACK_SEARCH_FORBIDDEN",
            "accepted_anchor_count": 0,
            "messages": messages,
        }

    return {
        "allowed": True,
        "decision_code": "UCP_CATALOG_SIMILARITY_AND_IDENTITY_VERIFIED",
        "accepted_anchor_count": len(accepted_anchors),
        "messages": messages,
        "empty_result_required": bool(raw_anchors and not accepted_anchors),
    }


def evaluate_ucp_nano_payment_instrument_and_session_binding_guard(
    context: dict[str, Any],
) -> dict[str, Any]:
    """Enforce UCP PR #862 Nano (XNO) payment instrument session binding and block claim rules."""
    issued_receive_address = str(context.get("issued_receive_address") or "")
    issued_amount_raw = str(context.get("issued_amount_raw") or "")
    submitted_receive_address = context.get("submitted_receive_address")
    submitted_amount_raw = context.get("submitted_amount_raw")
    address_reused_across_checkouts = bool(
        context.get("address_reused_across_checkouts", False)
    )
    settlement_block = str(context.get("settlement_block") or "")
    network = str(context.get("network") or "mainnet")
    ledger_block_destination = str(
        context.get("ledger_block_destination") or issued_receive_address
    )
    ledger_block_amount_raw = str(
        context.get("ledger_block_amount_raw") or issued_amount_raw
    )
    ledger_block_is_send = bool(context.get("ledger_block_is_send", True))
    ledger_block_confirmed = bool(context.get("ledger_block_confirmed", True))
    checkout_expired = bool(context.get("checkout_expired", False))
    multi_block_sum_attempted = bool(context.get("multi_block_sum_attempted", False))
    claimed_blocks = {
        (str(net), str(blk).upper())
        for net, blk in (context.get("claimed_network_blocks") or [])
    }
    is_idempotent_retry_of_claiming_op = bool(
        context.get("is_idempotent_retry_of_claiming_op", False)
    )

    if not NANO_ADDRESS_RE.match(issued_receive_address) or not NANO_RAW_AMOUNT_RE.match(
        issued_amount_raw
    ):
        return {
            "allowed": False,
            "decision_code": "NANO_ISSUED_BINDING_SCHEMA_INVALID_BLOCKED",
            "claim_key": None,
        }

    if address_reused_across_checkouts:
        return {
            "allowed": False,
            "decision_code": "NANO_RECEIVE_ADDRESS_REUSE_ACROSS_CHECKOUTS_BLOCKED",
            "claim_key": None,
        }

    if (
        submitted_receive_address is not None
        and str(submitted_receive_address) != issued_receive_address
    ) or (
        submitted_amount_raw is not None
        and str(submitted_amount_raw) != issued_amount_raw
    ):
        return {
            "allowed": False,
            "decision_code": "NANO_CLIENT_SUBMITTED_BINDING_OVERRIDE_BLOCKED",
            "error_code": "payment_failed",
            "severity": "recoverable",
            "claim_key": None,
        }

    if not NANO_BLOCK_HASH_RE.match(settlement_block):
        return {
            "allowed": False,
            "decision_code": "NANO_SETTLEMENT_BLOCK_HASH_INVALID_BLOCKED",
            "error_code": "payment_failed",
            "severity": "recoverable",
            "claim_key": None,
        }

    claim_key = (network, settlement_block.upper())
    if claim_key in claimed_blocks and not is_idempotent_retry_of_claiming_op:
        return {
            "allowed": False,
            "decision_code": "NANO_SETTLEMENT_BLOCK_REPLAY_CLAIM_BLOCKED",
            "error_code": "payment_failed",
            "severity": "recoverable",
            "claim_key": claim_key,
        }

    if not ledger_block_is_send or ledger_block_destination != issued_receive_address:
        return {
            "allowed": False,
            "decision_code": "NANO_BLOCK_DESTINATION_OR_TYPE_MISMATCH_BLOCKED",
            "error_code": "payment_failed",
            "severity": "recoverable",
            "claim_key": claim_key,
        }

    if multi_block_sum_attempted or ledger_block_amount_raw != issued_amount_raw:
        return {
            "allowed": False,
            "decision_code": "NANO_BLOCK_AMOUNT_MISMATCH_OR_MULTI_BLOCK_SUM_BLOCKED",
            "error_code": "payment_failed",
            "error_path": "$.payment.instruments[0].settlement_block",
            "severity": "recoverable",
            "claim_key": claim_key,
        }

    if checkout_expired and not ledger_block_confirmed:
        return {
            "allowed": False,
            "decision_code": "NANO_UNCONFIRMED_OR_EXPIRED_SETTLEMENT_BLOCK_REJECTED",
            "error_code": "payment_failed",
            "severity": "unrecoverable",
            "claim_key": claim_key,
        }

    if not ledger_block_confirmed:
        return {
            "allowed": False,
            "decision_code": "NANO_UNCONFIRMED_OR_EXPIRED_SETTLEMENT_BLOCK_REJECTED",
            "checkout_status": "complete_in_progress",
            "claim_key": claim_key,
        }

    return {
        "allowed": True,
        "decision_code": "UCP_NANO_PAYMENT_INSTRUMENT_SETTLEMENT_VERIFIED",
        "checkout_status": "completed",
        "claim_key": claim_key,
    }


def evaluate_ucp_credential_echo_cart_checkout_and_deferred_terms_guard(
    context: dict[str, Any],
) -> dict[str, Any]:
    """Enforce UCP PRs #868, #940, #912, #908/#881, and #934/#870."""
    endpoint = str(context.get("endpoint") or "/checkout-sessions/chk_1")
    response_credential_fields = set(context.get("response_credential_fields") or [])
    rest_operation = str(context.get("rest_operation") or "complete_checkout")
    has_idempotency_key = bool(context.get("has_idempotency_key", True))

    if endpoint != "/detokenize" and (
        response_credential_fields & SENSITIVE_CREDENTIAL_FIELDS
    ):
        return {
            "allowed": False,
            "decision_code": "SENSITIVE_CREDENTIAL_FIELD_ECHOED_OUTSIDE_DETOKENIZE_BLOCKED",
        }

    if rest_operation in IRREVERSIBLE_REST_OPERATIONS and not has_idempotency_key:
        return {
            "allowed": False,
            "decision_code": "IRREVERSIBLE_OPERATION_MISSING_IDEMPOTENCY_KEY_BLOCKED",
        }

    is_create_checkout = bool(context.get("is_create_checkout", False))
    has_line_items = bool(context.get("has_line_items", True))
    has_cart_id = bool(context.get("has_cart_id", False))
    cart_id_present_on_complete_or_response = bool(
        context.get("cart_id_present_on_complete_or_response", False)
    )
    if is_create_checkout and not (has_line_items or has_cart_id):
        return {
            "allowed": False,
            "decision_code": "CREATE_CHECKOUT_MISSING_LINE_ITEMS_AND_CART_ID_BLOCKED",
        }
    if cart_id_present_on_complete_or_response:
        return {
            "allowed": False,
            "decision_code": "CART_ID_EXPOSED_ON_COMPLETE_OR_RESPONSE_BLOCKED",
        }

    checkout_status = str(context.get("checkout_status") or "ready_for_complete")
    continue_url = str(context.get("continue_url") or "").strip()
    if checkout_status == "requires_escalation" and not continue_url:
        return {
            "allowed": False,
            "decision_code": "REQUIRES_ESCALATION_MISSING_CONTINUE_URL_BLOCKED",
        }

    fully_deferred_payment_terms = bool(
        context.get("fully_deferred_payment_terms", False)
    )
    complete_payment_object = context.get("complete_payment_object", {})
    if fully_deferred_payment_terms:
        if not isinstance(complete_payment_object, dict) or (
            "selected_term_id" in complete_payment_object
            or bool(complete_payment_object.get("instruments"))
        ):
            return {
                "allowed": False,
                "decision_code": "DEFERRED_PAYMENT_TERMS_NON_EMPTY_COMPLETE_PAYMENT_BLOCKED",
            }

    signature_is_asn1_der = bool(context.get("signature_is_asn1_der", False))
    has_ucp_agent_header = bool(context.get("has_ucp_agent_header", True))
    ucp_agent_in_covered_components = bool(
        context.get("ucp_agent_in_covered_components", True)
    )
    if signature_is_asn1_der or (
        has_ucp_agent_header and not ucp_agent_in_covered_components
    ):
        return {
            "allowed": False,
            "decision_code": "LODGING_ASN1_DER_SIGNATURE_OR_MISSING_UCP_AGENT_COVERAGE_BLOCKED",
        }

    stay_start = context.get("stay_start_date")
    stay_end = context.get("stay_end_date")
    billed_nights = context.get("billed_nights")
    if stay_start and stay_end and billed_nights is not None:
        d_start = date.fromisoformat(str(stay_start))
        d_end = date.fromisoformat(str(stay_end))
        expected_nights = (d_end - d_start).days
        if expected_nights <= 0 or int(billed_nights) != expected_nights:
            return {
                "allowed": False,
                "decision_code": "LODGING_STAY_CHECKOUT_DATE_COUNTED_AS_EXTRA_NIGHT_BLOCKED",
                "expected_nights": expected_nights,
            }

    return {
        "allowed": True,
        "decision_code": "UCP_CREDENTIAL_CART_ESCALATION_DEFERRED_LODGING_VERIFIED",
    }
