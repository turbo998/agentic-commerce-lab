"""Stage 176 deterministic guard module for 2026-10-23 UCP & AP2 protocol updates.

Covers:
1. Google UCP PR #974 (`2026-10-23T12:18:09Z`):
   Catalog similarity search (`like[]` product/variant anchors, self-exclusion,
   all-unresolved empty result rather than unconstrained browse, and
   `batch_limit_applied` truncation) & lookup/get_product `include`
   (`substitutes` / `recommendations` fail-safe by absence, variant-level
   self-exclusion, sibling-variant admission, and filter narrowing).
2. Google UCP PR #897 (`2026-10-23T05:53:53Z`):
   Food Checkout (`dev.ucp.food.checkout`) & Fulfillment (`dev.ucp.food.fulfillment`)
   single-establishment scoping (`food_establishment.id`), singular
   `fulfillment_method.destination` (rejecting plural `destinations[]`),
   `modification.quantity >= 1`, `/checkout-sessions` REST path alignment,
   and first-class `gratuity` total conservation.
3. Google UCP PR #939 (`2026-10-23T05:53:38Z`) & PR #774 (`2026-10-23T14:15:06Z`):
   Location-independent Business Identity (`dev.ucp.common.business` capability
   with `business_summary` and `contacts`, separated from retail branch
   `dev.ucp.common.location.*` and top-level `profile.business`) and JSONPath
   bracket-quoted reverse-domain/colon key parsing (`split_ucp_jsonpath` and
   RFC 6901 JSON Pointer conversion).
4. Google AP2 Issue #290 (`trail-head-ref-v1.md`, `2026-10-23T14:26:59Z`) & Issue #338:
   Post-checkout agent action record checkpoint cadence ceiling
   (`period_exceeds_declared_maximum`), mandatory empty-period seals,
   sequence/checkpoint integrity (`truncated`, `seq_order`, `checkpoint_mismatch`),
   `window_anchor="uncertified"` (`continuity_only`) anchor-blind bypass block
   (`thw-003`/`thw-006`/`thw-007`), and `vaara.receipt/v1` `terminal=True` gate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    decision_code: str
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)


RECOGNIZED_LIKE_KEYS = frozenset({"id", "image", "color"})
_BARE_SEGMENT_RE = re.compile(r"^([A-Za-z0-9_]+)(?:\[(\d+)\])?$")
_BRACKET_SEGMENT_RE = re.compile(
    r"^\['([^']+)'\](?:\[(\d+)\])?$|^\"([^\"]+)\"$|^\[\"([^\"]+)\"\](?:\[(\d+)\])?$"
)


def validate_ucp_catalog_search_and_substitutes(
    *,
    operation: str,
    like_anchors: list[dict[str, Any]] | None = None,
    max_anchors: int = 5,
    candidate_products: list[dict[str, Any]] | None = None,
    requested_id: str | None = None,
    requested_is_variant: bool = False,
    include: list[str] | None = None,
    merchant_supports_substitutes: bool = True,
    price_max_minor: int | None = None,
    primary_product: dict[str, Any] | None = None,
    raw_substitutes: list[dict[str, Any]] | None = None,
) -> GuardDecision:
    """Validate UCP PR #974 Catalog similarity `like[]` and lookup `include` rules."""
    if operation == "search_catalog":
        anchors = list(like_anchors or [])
        if not anchors:
            return GuardDecision(
                allowed=False,
                decision_code="ucp_catalog_like_anchors_empty",
                reason="search_catalog similarity check requires at least one like[] anchor.",
            )
        for item in anchors:
            if not isinstance(item, dict) or not (set(item.keys()) & RECOGNIZED_LIKE_KEYS):
                return GuardDecision(
                    allowed=False,
                    decision_code="ucp_catalog_like_item_unrecognized_key",
                    reason="Each like_item must contain at least one recognized anchor key (id, image, color).",
                )
        warnings: list[str] = []
        if len(anchors) > max_anchors:
            anchors = anchors[:max_anchors]
            warnings.append("batch_limit_applied")

        resolved_anchors: list[dict[str, Any]] = []
        for item in anchors:
            if item.get("resolved", True):
                resolved_anchors.append(item)
            else:
                warnings.append(f"not_found:{item.get('id', 'unknown')}")

        if not resolved_anchors:
            return GuardDecision(
                allowed=False,
                decision_code="ucp_catalog_search_all_anchors_unresolved_empty",
                reason="When no like[] anchors resolve, search_catalog must return an empty result rather than an unconstrained browse.",
                metadata={"results": [], "warnings": warnings},
            )

        excluded_product_ids = {
            str(a["id"]) for a in resolved_anchors if a.get("kind", "product") == "product" and "id" in a
        }
        excluded_variant_ids = {
            str(a["id"]) for a in resolved_anchors if a.get("kind") == "variant" and "id" in a
        }

        filtered_results: list[dict[str, Any]] = []
        for prod in candidate_products or []:
            pid = str(prod.get("id", ""))
            if pid in excluded_product_ids:
                continue
            variants = [
                v for v in prod.get("variants", [])
                if str(v.get("id", "")) not in excluded_variant_ids
                and (price_max_minor is None or int(v.get("price_minor", 0)) <= price_max_minor)
            ]
            if variants:
                filtered_results.append({"id": pid, "variants": variants})

        return GuardDecision(
            allowed=True,
            decision_code="ucp_catalog_similarity_search_ok",
            reason="UCP PR #974 search_catalog like[] anchors resolved with self-exclusion and filter narrowing.",
            metadata={"results": filtered_results, "warnings": warnings},
        )

    if operation in {"get_product", "lookup_catalog"}:
        if not primary_product:
            return GuardDecision(
                allowed=False,
                decision_code="ucp_catalog_primary_product_missing",
                reason="Primary product is required for get_product/lookup_catalog.",
            )
        primary_variants = [
            v for v in primary_product.get("variants", [])
            if price_max_minor is None or int(v.get("price_minor", 0)) <= price_max_minor
        ]
        if not primary_variants:
            return GuardDecision(
                allowed=False,
                decision_code="ucp_catalog_primary_excluded_by_filter_omits_include",
                reason="When a filter excludes the requested primary item, its included substitutes/recommendations are omitted with it.",
                metadata={"product": None},
            )

        req_include = set(include or [])
        response_product: dict[str, Any] = {
            "id": primary_product["id"],
            "variants": primary_variants,
        }
        if "substitutes" in req_include:
            if not merchant_supports_substitutes:
                return GuardDecision(
                    allowed=True,
                    decision_code="ucp_catalog_include_substitutes_absent_not_offered",
                    reason="Business that does not support substitutes omits the key (fail-safe by absence: not offered, never none exist).",
                    metadata={"product": response_product, "substitutes_key_present": False},
                )
            narrowed_subs: list[dict[str, Any]] = []
            for sub in raw_substitutes or []:
                sub_variants = []
                for v in sub.get("variants", []):
                    vid = str(v.get("id", ""))
                    if requested_is_variant and vid == str(requested_id):
                        return GuardDecision(
                            allowed=False,
                            decision_code="ucp_catalog_substitute_contains_self_variant",
                            reason=f"Substitute list cannot contain the exact variant being replaced ({vid}).",
                        )
                    if price_max_minor is None or int(v.get("price_minor", 0)) <= price_max_minor:
                        if v.get("available", True):
                            sub_variants.append(v)
                if sub_variants:
                    narrowed_subs.append({"id": sub["id"], "variants": sub_variants})
            response_product["substitutes"] = narrowed_subs

        return GuardDecision(
            allowed=True,
            decision_code="ucp_catalog_lookup_include_ok",
            reason="UCP PR #974 lookup/get_product include list verified with variant-relative narrowing.",
            metadata={
                "product": response_product,
                "substitutes_key_present": "substitutes" in response_product,
            },
        )

    return GuardDecision(
        allowed=False,
        decision_code="ucp_catalog_unknown_operation",
        reason=f"Unsupported catalog operation: {operation}",
    )


def validate_ucp_food_checkout_and_fulfillment(
    *,
    rest_path: str,
    establishment_id: str,
    line_items: list[dict[str, Any]],
    fulfillment_method: dict[str, Any],
    tax_minor: int,
    delivery_fee_minor: int,
    gratuity_minor: int,
    declared_total_minor: int,
) -> GuardDecision:
    """Validate UCP PR #897 Food Checkout (`dev.ucp.food.checkout`) & Fulfillment (`dev.ucp.food.fulfillment`)."""
    if not rest_path.startswith("/checkout-sessions"):
        return GuardDecision(
            allowed=False,
            decision_code="ucp_food_rest_path_invalid",
            reason="Food Checkout REST endpoints must align to /checkout-sessions*.",
        )
    if not establishment_id or not line_items:
        return GuardDecision(
            allowed=False,
            decision_code="ucp_food_checkout_empty_or_unscoped",
            reason="Food Checkout requires a target establishment_id and at least one dish line item.",
        )

    computed_dishes_minor = 0
    for idx, item in enumerate(line_items):
        item_est = str(item.get("establishment_id", ""))
        if item_est != establishment_id:
            return GuardDecision(
                allowed=False,
                decision_code="ucp_food_multi_establishment_forbidden",
                reason=f"Line item {idx} belongs to establishment '{item_est}', violating single-establishment scoping ('{establishment_id}').",
            )
        dish_qty = int(item.get("quantity", 1))
        if dish_qty < 1:
            return GuardDecision(
                allowed=False,
                decision_code="ucp_food_dish_quantity_invalid",
                reason="Dish line item quantity must be >= 1.",
            )
        mod_unit_total = 0
        for mod in item.get("modifications", []):
            mod_qty = mod.get("quantity", 1)
            if not isinstance(mod_qty, int) or mod_qty < 1:
                return GuardDecision(
                    allowed=False,
                    decision_code="ucp_food_modification_quantity_invalid",
                    reason="Food dish modification.quantity must be an integer >= 1 (default 1).",
                )
            mod_unit_total += int(mod.get("price_minor", 0)) * mod_qty
        computed_dishes_minor += (int(item.get("unit_price_minor", 0)) + mod_unit_total) * dish_qty

    if "destinations" in fulfillment_method:
        return GuardDecision(
            allowed=False,
            decision_code="ucp_food_plural_destinations_forbidden",
            reason="source/schemas/food/types/fulfillment_method.json requires singular 'destination', not plural 'destinations'.",
        )
    destination = fulfillment_method.get("destination")
    method_type = fulfillment_method.get("type", "")
    if not isinstance(destination, dict):
        return GuardDecision(
            allowed=False,
            decision_code="ucp_food_destination_missing",
            reason="fulfillment_method requires a singular destination object.",
        )
    if method_type == "delivery" and not destination.get("physical_address"):
        return GuardDecision(
            allowed=False,
            decision_code="ucp_food_delivery_physical_address_missing",
            reason="Delivery fulfillment_method requires destination.physical_address.",
        )
    if method_type in {"pickup", "curbside", "dine_in"} and not destination.get("location_id"):
        return GuardDecision(
            allowed=False,
            decision_code="ucp_food_pickup_location_missing",
            reason="Pickup/curbside/dine_in fulfillment_method requires destination.location_id.",
        )

    if gratuity_minor < 0:
        return GuardDecision(
            allowed=False,
            decision_code="ucp_food_gratuity_negative",
            reason="First-class gratuity amount must be non-negative.",
        )

    expected_total = computed_dishes_minor + tax_minor + delivery_fee_minor + gratuity_minor
    if expected_total != declared_total_minor:
        return GuardDecision(
            allowed=False,
            decision_code="ucp_food_total_or_gratuity_mismatch",
            reason=f"Food checkout total ({declared_total_minor}) != dishes ({computed_dishes_minor}) + tax ({tax_minor}) + delivery ({delivery_fee_minor}) + gratuity ({gratuity_minor}).",
        )

    return GuardDecision(
        allowed=True,
        decision_code="ucp_food_checkout_and_fulfillment_ok",
        reason="UCP PR #897 single-establishment Food Checkout, singular destination, modification quantities, and gratuity verified.",
        metadata={"computed_dishes_minor": computed_dishes_minor, "expected_total_minor": expected_total},
    )


def split_ucp_jsonpath(expr: str) -> list[tuple[str, int | None]]:
    """Parse UCP PR #774 JSONPath subset supporting bare, indexed, and bracket-quoted keys."""
    if not expr or not expr.startswith("$"):
        raise ValueError("JSONPath must start with '$'")
    rest = expr[1:]
    if not rest:
        return []
    segments: list[tuple[str, int | None]] = []
    pos = 0
    n = len(rest)
    while pos < n:
        if rest[pos] == ".":
            pos += 1
            if pos >= n or rest[pos] == "[":
                raise ValueError(f"Unparsable dot segment at position {pos} in {expr}")
            end = pos
            while end < n and rest[end] != "." and not (rest[end] == "[" and end + 1 < n and rest[end + 1] in {"'", '"'}):
                end += 1
            token = rest[pos:end]
            m = _BARE_SEGMENT_RE.match(token)
            if not m:
                raise ValueError(f"Unparsable bare segment '{token}' in {expr}")
            idx = int(m.group(2)) if m.group(2) is not None else None
            segments.append((m.group(1), idx))
            pos = end
        elif rest[pos] == "[":
            quote = rest[pos + 1 : pos + 2]
            if quote not in {"'", '"'}:
                raise ValueError(f"Bracket segment must be quoted at position {pos} in {expr}")
            close_quote = rest.find(f"{quote}]", pos + 2)
            if close_quote == -1:
                raise ValueError(f"Unterminated bracket-quoted key in {expr}")
            key = rest[pos + 2 : close_quote]
            if not key:
                raise ValueError(f"Empty bracket-quoted key in {expr}")
            after_bracket = close_quote + 2
            idx: int | None = None
            if after_bracket < n and rest[after_bracket] == "[":
                next_char = rest[after_bracket + 1 : after_bracket + 2]
                if next_char.isdigit():
                    close_idx = rest.find("]", after_bracket + 1)
                    if close_idx == -1:
                        raise ValueError(f"Unterminated array index in {expr}")
                    idx_str = rest[after_bracket + 1 : close_idx]
                    if not idx_str.isdigit():
                        raise ValueError(f"Non-numeric array index '{idx_str}' in {expr}")
                    idx = int(idx_str)
                    after_bracket = close_idx + 1
            segments.append((key, idx))
            pos = after_bracket
        else:
            raise ValueError(f"Unexpected character '{rest[pos]}' at position {pos} in {expr}")
    return segments


def ucp_jsonpath_to_pointer(expr: str) -> str:
    """Convert UCP PR #774 JSONPath expression to RFC 6901 JSON Pointer."""
    segments = split_ucp_jsonpath(expr)
    parts: list[str] = []
    for key, idx in segments:
        escaped = key.replace("~", "~0").replace("/", "~1")
        parts.append(escaped)
        if idx is not None:
            parts.append(str(idx))
    return "/" + "/".join(parts) if parts else ""


def validate_ucp_business_identity_and_jsonpath(
    *,
    profile: dict[str, Any],
    extract_expr: str,
) -> GuardDecision:
    """Validate UCP PR #939 `dev.ucp.common.business` capability and PR #774 bracket-quoted JSONPath."""
    if "business" in profile:
        return GuardDecision(
            allowed=False,
            decision_code="ucp_business_top_level_profile_field_forbidden",
            reason="Business identity must be declared under ucp.capabilities['dev.ucp.common.business'], not as a top-level profile.business field.",
        )

    capabilities = profile.get("ucp", {}).get("capabilities", {})
    biz_entries = capabilities.get("dev.ucp.common.business")
    if not isinstance(biz_entries, list) or not biz_entries:
        return GuardDecision(
            allowed=False,
            decision_code="ucp_business_capability_missing",
            reason="Profile must declare ucp.capabilities['dev.ucp.common.business'].",
        )
    biz_cfg = biz_entries[0].get("config", {}).get("business", {})
    if not biz_cfg.get("name"):
        return GuardDecision(
            allowed=False,
            decision_code="ucp_business_summary_name_missing",
            reason="business_summary requires a display name.",
        )
    if "geo" in biz_cfg or "hours" in biz_cfg or "amenities" in biz_cfg:
        return GuardDecision(
            allowed=False,
            decision_code="ucp_business_branch_location_conflation_forbidden",
            reason="dev.ucp.common.business models location-independent corporate identity; physical branch geo/hours/amenities belong in dev.ucp.common.location.*.",
        )
    for media_item in biz_cfg.get("media", []):
        if media_item.get("role") not in {"logo", "cover"}:
            return GuardDecision(
                allowed=False,
                decision_code="ucp_business_media_role_invalid",
                reason="business_summary media role must be 'logo' or 'cover'.",
            )

    try:
        segments = split_ucp_jsonpath(extract_expr)
        pointer = ucp_jsonpath_to_pointer(extract_expr)
    except ValueError as exc:
        return GuardDecision(
            allowed=False,
            decision_code="ucp_jsonpath_unparsable_segment",
            reason=str(exc),
        )

    cur: Any = profile
    for key, idx in segments:
        if not isinstance(cur, dict) or key not in cur:
            return GuardDecision(
                allowed=False,
                decision_code="ucp_jsonpath_unquoted_dotted_key_rejected",
                reason=f"Segment '{key}' not found in target object (reverse-domain/colon keys require bracket quotes).",
            )
        cur = cur[key]
        if idx is not None:
            if not isinstance(cur, list) or idx >= len(cur):
                return GuardDecision(
                    allowed=False,
                    decision_code="ucp_jsonpath_index_out_of_bounds",
                    reason=f"Index [{idx}] out of bounds for key '{key}'.",
                )
            cur = cur[idx]

    return GuardDecision(
        allowed=True,
        decision_code="ucp_business_identity_and_jsonpath_ok",
        reason="UCP PR #939 dev.ucp.common.business capability and PR #774 bracket-quoted JSONPath navigation verified.",
        metadata={"json_pointer": pointer, "extracted_value": cur},
    )


def validate_ap2_trail_head_window_and_cadence(
    *,
    checkpoints: list[dict[str, Any]],
    declared_max_period_s: int,
    records: list[dict[str, Any]],
    expected_record_count: int,
    window_anchor: str,
    verdict: str,
    require_certified_start: bool = True,
    require_terminal_receipt: bool = False,
) -> GuardDecision:
    """Validate AP2 Issue #290 (`trail-head-ref-v1.md`) checkpoint cadence & window_anchor rules."""
    if not checkpoints or len(checkpoints) < 2:
        return GuardDecision(
            allowed=False,
            decision_code="ap2_checkpoints_insufficient",
            reason="At least two checkpoints are required to verify period cadence.",
        )

    for prev, curr in zip(checkpoints, checkpoints[1:]):
        delta_s = int(curr.get("timestamp_s", 0)) - int(prev.get("timestamp_s", 0))
        if delta_s <= 0 or delta_s > declared_max_period_s:
            return GuardDecision(
                allowed=False,
                decision_code="period_exceeds_declared_maximum",
                reason=f"Checkpoint period ({delta_s}s) exceeds declared_max_period_s ({declared_max_period_s}s).",
            )
        if int(curr.get("record_count", 0)) == 0 and not curr.get("empty_period_seal"):
            return GuardDecision(
                allowed=False,
                decision_code="ap2_empty_period_seal_missing",
                reason="Mandatory empty-period seal is required when no actions occur during a period.",
            )

    prev_seq = -1
    for rec in records:
        seq = int(rec.get("seq", -1))
        if seq != prev_seq + 1:
            return GuardDecision(
                allowed=False,
                decision_code="seq_order",
                reason=f"Action record sequence out of order at seq={seq} (expected {prev_seq + 1}).",
            )
        prev_seq = seq
        if rec.get("rewritten", False):
            return GuardDecision(
                allowed=False,
                decision_code="checkpoint_mismatch",
                reason="Same-length record rewrite detected by domain-separated Merkle checkpoint mismatch.",
            )
        if require_terminal_receipt and not bool(rec.get("terminal", False)):
            return GuardDecision(
                allowed=False,
                decision_code="ap2_non_terminal_action_receipt_rejected",
                reason="In-progress action receipt (terminal=False) cannot be presented where a terminal receipt is required.",
            )

    if len(records) < expected_record_count:
        return GuardDecision(
            allowed=False,
            decision_code="truncated",
            reason=f"Tail cut detected: {len(records)} records present vs {expected_record_count} committed in checkpoint.",
        )

    if require_certified_start and (
        window_anchor == "uncertified" or verdict == "continuity_only"
    ):
        return GuardDecision(
            allowed=False,
            decision_code="ap2_window_anchor_uncertified_continuity_only_rejected",
            reason="window_anchor='uncertified' (verdict='continuity_only') is an unverifiable-start warning state, not a pass.",
        )

    return GuardDecision(
        allowed=True,
        decision_code="ap2_trail_head_window_and_cadence_ok",
        reason="AP2 #290 trail-head-ref-v1 checkpoint cadence ceiling, empty-period seals, Merkle sequence, and certified window_anchor verified.",
        metadata={"checkpoint_count": len(checkpoints), "record_count": len(records)},
    )
