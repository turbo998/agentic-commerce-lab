"""Stage 35: UCP Post-Order Lifecycle, Catalog Substitution & Food Allergen Safety Guards
+ ACP MCP Mutating Tool Idempotency & Host Spend Gate.

Implements deterministic offline conformance guards for:
1. UCP PR #964 (`food/checkout`): Per-allergen status (`contains` | `may_contain` | `free_of`)
   and buyer dietary restrictions (`allergen_conflict` with `severity: requires_buyer_review`,
   prohibiting platform inference of `free_of` or business restriction clearing).
2. UCP PR #974 (`catalog`): Entity `substitutes` (`get_product(include=["substitutes"])`)
   vs open-ended similarity discovery (`search_catalog(like=[...])`) and cross-sell
   `recommendations` isolation.
3. UCP PR #945 / EP #943 (`dev.ucp.shopping.order_modification`): Cancellation-first order
   modification with `base_order_version` equality precondition, RFC 9110 §9.2.1 safe
   `lookup_modification` (`Original-Idempotency-Key` header), and atomic compare-and-set
   `fence_modification` tombstone.
4. UCP PR #946 / EP #944 (`dev.ucp.shopping.order_consultation`): Business-initiated post-order
   consultation with schema-authority host prefix binding, auth-before-replay evaluation,
   dedicated `dev.ucp.shopping.order_consultation:decide` scope, and RFC 8785 canonical
   `proposal_digest` (`sha-256:<hex>`).
5. ACP PR #296 & PR #314: Required `meta.idempotency_key` on mutating MCP checkout tools
   and signed host-side spend gate (`mcpToolGate`) before `complete_checkout_session` /
   `delegate_payment`.

Pure Python standard library; zero network calls; zero secrets.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import ipaddress
import json
from typing import Any
from urllib.parse import urlparse


VALID_ALLERGEN_STATUSES = frozenset({"contains", "may_contain", "free_of"})
MUTATING_ACP_MCP_TOOLS = frozenset(
    {
        "create_checkout_session",
        "update_checkout_session",
        "complete_checkout_session",
        "cancel_checkout_session",
        "delegate_payment",
    }
)
SPEND_CAPABLE_ACP_MCP_TOOLS = frozenset(
    {
        "complete_checkout_session",
        "delegate_payment",
    }
)


@dataclass(frozen=True)
class UCPFoodAllergenGuardResult:
    line_item_id: str
    admitted: bool
    decision_code: str
    requires_buyer_review: bool
    conflict_allergen_codes: tuple[str, ...]
    conflict_messages: tuple[str, ...]


@dataclass(frozen=True)
class UCPCatalogSubstituteGuardResult:
    original_sku_id: str
    candidate_sku_id: str
    admitted: bool
    decision_code: str
    source_operation: str
    relation_type: str
    price_delta_bps: int


@dataclass(frozen=True)
class UCPOrderModificationFenceResult:
    order_id: str
    operation_mode: str
    admitted: bool
    decision_code: str
    http_status: int
    lookup_or_fence_outcome: str
    cache_control_no_store: bool


@dataclass(frozen=True)
class UCPOrderConsultationDecisionResult:
    consultation_id: str
    revision: int
    admitted: bool
    decision_code: str
    http_status: int
    computed_proposal_digest: str
    final: bool


@dataclass(frozen=True)
class ACPMcpMutatingToolGateResult:
    tool_name: str
    admitted: bool
    decision_code: str
    idempotency_key_present: bool
    host_spend_gate_verified: bool


def evaluate_ucp_food_allergen_and_dietary_guard(
    *,
    line_item_id: str,
    dish_name: str,
    dish_allergens: tuple[dict[str, str], ...],
    buyer_dietary_restrictions: tuple[dict[str, str], ...],
    platform_inferred_free_of_codes: tuple[str, ...] = (),
    business_cleared_restriction_codes: tuple[str, ...] = (),
    buyer_explicitly_reviewed_conflicts: bool = False,
) -> UCPFoodAllergenGuardResult:
    """Enforce UCP PR #964 per-allergen dish status and buyer dietary restriction rules."""
    if platform_inferred_free_of_codes:
        return UCPFoodAllergenGuardResult(
            line_item_id=line_item_id,
            admitted=False,
            decision_code="PLATFORM_INFERRED_FREE_OF_FORBIDDEN",
            requires_buyer_review=True,
            conflict_allergen_codes=tuple(sorted(platform_inferred_free_of_codes)),
            conflict_messages=(
                "Platform MUST NOT infer free_of when allergen is not explicitly business-asserted free_of",
            ),
        )

    if business_cleared_restriction_codes:
        return UCPFoodAllergenGuardResult(
            line_item_id=line_item_id,
            admitted=False,
            decision_code="BUSINESS_RESTRICTION_CLEARING_FORBIDDEN",
            requires_buyer_review=True,
            conflict_allergen_codes=tuple(sorted(business_cleared_restriction_codes)),
            conflict_messages=(
                "Business MUST NOT use a buyer dietary restriction to clear an allergen status",
            ),
        )

    allergen_map: dict[tuple[str, str], str] = {}
    for entry in dish_allergens:
        code_list = str(entry.get("code_list", "")).strip()
        code = str(entry.get("code", "")).strip().lower()
        status = str(entry.get("status", "")).strip()
        source = str(entry.get("source", "")).strip()
        if not code_list or not code or status not in VALID_ALLERGEN_STATUSES or not source:
            return UCPFoodAllergenGuardResult(
                line_item_id=line_item_id,
                admitted=False,
                decision_code="INVALID_DISH_ALLERGEN_SCHEMA",
                requires_buyer_review=True,
                conflict_allergen_codes=(code or "unknown",),
                conflict_messages=("Invalid dish.allergens item schema",),
            )
        allergen_map[(code_list, code)] = status

    conflict_codes: list[str] = []
    conflict_messages: list[str] = []
    for restriction in buyer_dietary_restrictions:
        r_list = str(restriction.get("code_list", "")).strip()
        r_code = str(restriction.get("code", "")).strip().lower()
        if not r_list or not r_code:
            continue
        recorded_status = allergen_map.get((r_list, r_code))
        if recorded_status is None:
            conflict_codes.append(r_code)
            conflict_messages.append(
                f"No allergen information about {r_code} for {dish_name}, which conflicts with buyer dietary restriction"
            )
        elif recorded_status in {"contains", "may_contain"}:
            conflict_codes.append(r_code)
            conflict_messages.append(
                f"Dish {dish_name} status is '{recorded_status}' for restricted allergen {r_code}"
            )

    if conflict_codes and not buyer_explicitly_reviewed_conflicts:
        return UCPFoodAllergenGuardResult(
            line_item_id=line_item_id,
            admitted=False,
            decision_code="ALLERGEN_CONFLICT_REQUIRES_BUYER_REVIEW",
            requires_buyer_review=True,
            conflict_allergen_codes=tuple(conflict_codes),
            conflict_messages=tuple(conflict_messages),
        )

    return UCPFoodAllergenGuardResult(
        line_item_id=line_item_id,
        admitted=True,
        decision_code=(
            "ALLERGEN_CONFLICT_BUYER_REVIEW_ACKNOWLEDGED"
            if conflict_codes
            else "FOOD_ALLERGEN_DIETARY_CHECK_PASSED"
        ),
        requires_buyer_review=bool(conflict_codes),
        conflict_allergen_codes=tuple(conflict_codes),
        conflict_messages=tuple(conflict_messages),
    )


def evaluate_ucp_catalog_substitute_vs_search_guard(
    *,
    original_sku_id: str,
    candidate_sku_id: str,
    source_operation: str,  # "get_product" | "lookup_catalog" | "search_catalog"
    include_relation_type: str,  # "substitutes" | "recommendations" | "like_similarity"
    original_price_minor: int,
    candidate_price_minor: int,
    max_auto_substitute_price_increase_bps: int = 500,
    candidate_allergen_conflict: bool = False,
) -> UCPCatalogSubstituteGuardResult:
    """Enforce UCP PR #974 separation between entity `substitutes` and open-ended `search_catalog(like=...)`."""
    price_delta_bps = (
        ((candidate_price_minor - original_price_minor) * 10000) // original_price_minor
        if original_price_minor > 0
        else 0
    )

    if source_operation not in {"get_product", "lookup_catalog"} or include_relation_type != "substitutes":
        return UCPCatalogSubstituteGuardResult(
            original_sku_id=original_sku_id,
            candidate_sku_id=candidate_sku_id,
            admitted=False,
            decision_code="UNVERIFIED_SIMILARITY_SEARCH_OR_RECOMMENDATION_SUBSTITUTION_BLOCKED",
            source_operation=source_operation,
            relation_type=include_relation_type,
            price_delta_bps=price_delta_bps,
        )

    if candidate_allergen_conflict or price_delta_bps > max_auto_substitute_price_increase_bps:
        return UCPCatalogSubstituteGuardResult(
            original_sku_id=original_sku_id,
            candidate_sku_id=candidate_sku_id,
            admitted=False,
            decision_code="SUBSTITUTE_PRICE_OR_ALLERGEN_BREACH_BLOCKED",
            source_operation=source_operation,
            relation_type=include_relation_type,
            price_delta_bps=price_delta_bps,
        )

    return UCPCatalogSubstituteGuardResult(
        original_sku_id=original_sku_id,
        candidate_sku_id=candidate_sku_id,
        admitted=True,
        decision_code="ENTITY_SUBSTITUTE_VERIFIED",
        source_operation=source_operation,
        relation_type=include_relation_type,
        price_delta_bps=price_delta_bps,
    )


def evaluate_ucp_order_modification_lookup_and_fence(
    *,
    order_id: str,
    extension_negotiated: bool,
    parent_order_capability_negotiated: bool,
    operation_mode: str,  # "create_cancel" | "lookup_cancel" | "fence_cancel"
    current_order_version: str,
    base_order_version: str = "",
    idempotency_key: str = "",
    original_idempotency_key: str = "",
    original_key_in_url_query: bool = False,
    claimed_keys: set[str] | frozenset[str] = frozenset(),
    fenced_keys: set[str] | frozenset[str] = frozenset(),
    lookup_attempts_state_mutation: bool = False,
    response_headers: dict[str, str] | None = None,
) -> UCPOrderModificationFenceResult:
    """Enforce UCP PR #945 (EP #943) cancellation-first order modification, safe lookup, and atomic fencing."""
    headers = {k.lower(): v for k, v in (response_headers or {"Cache-Control": "no-store"}).items()}
    has_no_store = "no-store" in headers.get("cache-control", "").lower()

    if not extension_negotiated or not parent_order_capability_negotiated:
        return UCPOrderModificationFenceResult(
            order_id=order_id,
            operation_mode=operation_mode,
            admitted=False,
            decision_code="modification_not_supported",
            http_status=400,
            lookup_or_fence_outcome="not_negotiated",
            cache_control_no_store=has_no_store,
        )

    if not has_no_store:
        return UCPOrderModificationFenceResult(
            order_id=order_id,
            operation_mode=operation_mode,
            admitted=False,
            decision_code="MISSING_CACHE_CONTROL_NO_STORE",
            http_status=500,
            lookup_or_fence_outcome="invalid_headers",
            cache_control_no_store=False,
        )

    if operation_mode == "lookup_cancel":
        if original_key_in_url_query or not original_idempotency_key:
            return UCPOrderModificationFenceResult(
                order_id=order_id,
                operation_mode=operation_mode,
                admitted=False,
                decision_code="ORIGINAL_IDEMPOTENCY_KEY_HEADER_REQUIRED",
                http_status=400,
                lookup_or_fence_outcome="invalid_request",
                cache_control_no_store=True,
            )
        if lookup_attempts_state_mutation:
            return UCPOrderModificationFenceResult(
                order_id=order_id,
                operation_mode=operation_mode,
                admitted=False,
                decision_code="UNSAFE_GET_LOOKUP_STATE_MUTATION_FORBIDDEN",
                http_status=400,
                lookup_or_fence_outcome="unsafe_mutation_blocked",
                cache_control_no_store=True,
            )
        outcome = "found" if original_idempotency_key in claimed_keys else "unresolved"
        return UCPOrderModificationFenceResult(
            order_id=order_id,
            operation_mode=operation_mode,
            admitted=True,
            decision_code="SAFE_MODIFICATION_LOOKUP_COMPLETED",
            http_status=200,
            lookup_or_fence_outcome=outcome,
            cache_control_no_store=True,
        )

    if operation_mode == "fence_cancel":
        if not idempotency_key or not original_idempotency_key or idempotency_key == original_idempotency_key:
            return UCPOrderModificationFenceResult(
                order_id=order_id,
                operation_mode=operation_mode,
                admitted=False,
                decision_code="FRESH_FENCE_IDEMPOTENCY_KEY_REQUIRED",
                http_status=400,
                lookup_or_fence_outcome="invalid_fence_keys",
                cache_control_no_store=True,
            )
        if original_idempotency_key in claimed_keys:
            return UCPOrderModificationFenceResult(
                order_id=order_id,
                operation_mode=operation_mode,
                admitted=True,
                decision_code="ALREADY_CLAIMED_KEY_RETURNED_FOUND",
                http_status=200,
                lookup_or_fence_outcome="found",
                cache_control_no_store=True,
            )
        return UCPOrderModificationFenceResult(
            order_id=order_id,
            operation_mode=operation_mode,
            admitted=True,
            decision_code="UNCLAIMED_KEY_PERMANENTLY_FENCED",
            http_status=200,
            lookup_or_fence_outcome="fenced",
            cache_control_no_store=True,
        )

    if operation_mode == "create_cancel":
        if not idempotency_key:
            return UCPOrderModificationFenceResult(
                order_id=order_id,
                operation_mode=operation_mode,
                admitted=False,
                decision_code="IDEMPOTENCY_KEY_REQUIRED",
                http_status=400,
                lookup_or_fence_outcome="rejected",
                cache_control_no_store=True,
            )
        if idempotency_key in fenced_keys:
            return UCPOrderModificationFenceResult(
                order_id=order_id,
                operation_mode=operation_mode,
                admitted=False,
                decision_code="FENCED_IDEMPOTENCY_KEY_LATE_ARRIVAL_BLOCKED",
                http_status=409,
                lookup_or_fence_outcome="fenced_tombstone_blocked",
                cache_control_no_store=True,
            )
        if idempotency_key not in claimed_keys and base_order_version != current_order_version:
            return UCPOrderModificationFenceResult(
                order_id=order_id,
                operation_mode=operation_mode,
                admitted=False,
                decision_code="stale_order_state",
                http_status=200,
                lookup_or_fence_outcome="stale_order_state",
                cache_control_no_store=True,
            )
        return UCPOrderModificationFenceResult(
            order_id=order_id,
            operation_mode=operation_mode,
            admitted=True,
            decision_code="ORDER_CANCELLATION_COMMITTED",
            http_status=200,
            lookup_or_fence_outcome="committed",
            cache_control_no_store=True,
        )

    return UCPOrderModificationFenceResult(
        order_id=order_id,
        operation_mode=operation_mode,
        admitted=False,
        decision_code="UNSUPPORTED_MODIFICATION_OPERATION",
        http_status=400,
        lookup_or_fence_outcome="unsupported",
        cache_control_no_store=has_no_store,
    )


def _verify_schema_authority_binding(capability_name: str, schema_url: str) -> bool:
    parsed = urlparse(schema_url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return False
    try:
        ipaddress.ip_address(parsed.hostname)
        return False
    except ValueError:
        pass
    host_labels = [lbl.lower() for lbl in parsed.hostname.split(".") if lbl]
    if len(host_labels) < 2:
        return False
    derived_prefix = ".".join(reversed(host_labels))
    return capability_name == derived_prefix or capability_name.startswith(derived_prefix + ".")


def compute_ucp_consultation_proposal_digest(proposal_core: dict[str, Any]) -> str:
    """Compute UCP PR #946 RFC 8785 canonical JSON SHA-256 digest (`sha-256:<hex>`), excluding display/lifecycle fields."""
    canonical_payload = {
        "consultation_id": proposal_core["consultation_id"],
        "revision": proposal_core["revision"],
        "order_id": proposal_core["order_id"],
        "baseline": proposal_core["baseline"],
        "scope": proposal_core["scope"],
        "proposed_terms": proposal_core["proposed_terms"],
        "effective_time_rules": proposal_core["effective_time_rules"],
        "decision_deadline": proposal_core["decision_deadline"],
        "execution_deadline": proposal_core["execution_deadline"],
        "digest_context": "ucp-order-consultation-v1",
    }
    canonical_bytes = json.dumps(
        canonical_payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha-256:" + hashlib.sha256(canonical_bytes).hexdigest()


def evaluate_ucp_order_consultation_decision_guard(
    *,
    capability_name: str,
    schema_url: str,
    proposal_core: dict[str, Any],
    submitted_revision: int,
    submitted_proposal_digest: str,
    buyer_token_valid: bool,
    buyer_token_is_platform_only: bool,
    granted_scopes: tuple[str, ...],
    token_subject_buyer_id: str,
    order_owner_buyer_id: str,
    delegation_max_additional_amount_minor: int,
    proposed_additional_amount_minor: int,
    serialization_timestamp_epoch: int,
    decision_deadline_epoch: int,
    consultation_withdrawn_or_superseded: bool = False,
) -> UCPOrderConsultationDecisionResult:
    """Enforce UCP PR #946 (EP #944) post-order consultation authority binding, auth-before-replay, and RFC 8785 digest."""
    consultation_id = str(proposal_core.get("consultation_id", ""))
    expected_digest = compute_ucp_consultation_proposal_digest(proposal_core)

    if not _verify_schema_authority_binding(capability_name, schema_url):
        return UCPOrderConsultationDecisionResult(
            consultation_id=consultation_id,
            revision=submitted_revision,
            admitted=False,
            decision_code="SCHEMA_AUTHORITY_BINDING_INVALID",
            http_status=400,
            computed_proposal_digest=expected_digest,
            final=False,
        )

    # Auth-before-replay: expired/missing/platform-only tokens fail with 401 before any replay or state check
    if not buyer_token_valid or buyer_token_is_platform_only:
        return UCPOrderConsultationDecisionResult(
            consultation_id=consultation_id,
            revision=submitted_revision,
            admitted=False,
            decision_code="identity_required",
            http_status=401,
            computed_proposal_digest=expected_digest,
            final=False,
        )

    if "dev.ucp.shopping.order_consultation:decide" not in granted_scopes:
        return UCPOrderConsultationDecisionResult(
            consultation_id=consultation_id,
            revision=submitted_revision,
            admitted=False,
            decision_code="insufficient_scope",
            http_status=403,
            computed_proposal_digest=expected_digest,
            final=False,
        )

    if token_subject_buyer_id != order_owner_buyer_id:
        return UCPOrderConsultationDecisionResult(
            consultation_id=consultation_id,
            revision=submitted_revision,
            admitted=False,
            decision_code="not_found",
            http_status=404,
            computed_proposal_digest=expected_digest,
            final=False,
        )

    if proposed_additional_amount_minor > delegation_max_additional_amount_minor:
        return UCPOrderConsultationDecisionResult(
            consultation_id=consultation_id,
            revision=submitted_revision,
            admitted=False,
            decision_code="decision_not_authorized",
            http_status=403,
            computed_proposal_digest=expected_digest,
            final=False,
        )

    if (
        consultation_withdrawn_or_superseded
        or serialization_timestamp_epoch > decision_deadline_epoch
        or submitted_revision != int(proposal_core["revision"])
        or submitted_proposal_digest != expected_digest
    ):
        return UCPOrderConsultationDecisionResult(
            consultation_id=consultation_id,
            revision=submitted_revision,
            admitted=False,
            decision_code="CONSULTATION_REVISION_DIGEST_OR_DEADLINE_MISMATCH",
            http_status=409,
            computed_proposal_digest=expected_digest,
            final=True,
        )

    return UCPOrderConsultationDecisionResult(
        consultation_id=consultation_id,
        revision=submitted_revision,
        admitted=True,
        decision_code="ORDER_CONSULTATION_DECISION_RECEIPT_ISSUED",
        http_status=200,
        computed_proposal_digest=expected_digest,
        final=True,
    )


def evaluate_acp_mcp_mutating_tool_and_host_gate(
    *,
    tool_name: str,
    meta_idempotency_key: str | None,
    host_spend_gate_required: bool,
    host_kya_signature_valid: bool,
    host_kya_bound_tool: str,
    host_kya_bound_session_id: str,
    target_session_id: str,
    merchant_psp_rail_authorized: bool,
) -> ACPMcpMutatingToolGateResult:
    """Enforce ACP PR #296 (`meta.idempotency_key` on mutating MCP checkout tools) and PR #314 (`mcpToolGate`)."""
    has_idem = bool(meta_idempotency_key and len(meta_idempotency_key.strip()) >= 8)
    if tool_name in MUTATING_ACP_MCP_TOOLS and not has_idem:
        return ACPMcpMutatingToolGateResult(
            tool_name=tool_name,
            admitted=False,
            decision_code="ACP_MCP_MUTATING_TOOL_IDEMPOTENCY_KEY_MISSING",
            idempotency_key_present=False,
            host_spend_gate_verified=False,
        )

    if tool_name in SPEND_CAPABLE_ACP_MCP_TOOLS and host_spend_gate_required:
        if (
            not host_kya_signature_valid
            or host_kya_bound_tool != tool_name
            or host_kya_bound_session_id != target_session_id
        ):
            return ACPMcpMutatingToolGateResult(
                tool_name=tool_name,
                admitted=False,
                decision_code="ACP_HOST_SPEND_GATE_KYA_DENIED",
                idempotency_key_present=has_idem,
                host_spend_gate_verified=False,
            )

    if tool_name in SPEND_CAPABLE_ACP_MCP_TOOLS and not merchant_psp_rail_authorized:
        return ACPMcpMutatingToolGateResult(
            tool_name=tool_name,
            admitted=False,
            decision_code="HOST_GATE_CANNOT_SUBSTITUTE_FOR_PSP_RAIL_AUTH",
            idempotency_key_present=has_idem,
            host_spend_gate_verified=True,
        )

    return ACPMcpMutatingToolGateResult(
        tool_name=tool_name,
        admitted=True,
        decision_code="ACP_MCP_MUTATING_TOOL_AND_HOST_GATE_VERIFIED",
        idempotency_key_present=has_idem,
        host_spend_gate_verified=True,
    )
