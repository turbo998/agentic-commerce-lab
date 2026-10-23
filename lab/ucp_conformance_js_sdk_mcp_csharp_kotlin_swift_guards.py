"""Stage 224 deterministic runtime guards covering 38 primary-source PRs across
UCP Conformance, UCP JS SDK, and MCP C#, Kotlin, and Swift Official SDKs:

- PR-01 (conformance#117, #111): UCP Conformance ready_for_complete pre-completion status & strict 4xx state transition guard (no 409 stock escape hatch)
- PR-02 (conformance#115, #109): UCP Conformance AP2 capability intersection & mandate_required rejection + mock agent 5 exercised capabilities
- PR-03 (conformance#112, #98, #97): UCP Conformance business-owned ucp_request:omit field strip, strict discovery URL allowlist & canonical ShippingDestination fields
- PR-04 (conformance#89): UCP Payment-Terms (dev.ucp.common.payment.terms) 7 cross-field wire invariants (terms.md)
- PR-05 (js-sdk#87, #84, #83): UCP JS SDK ucp-schema generate-types <Union>Base not.enum guard, open-schema .catchall(z.any()) & {id,type} Binding split
- PR-06 (js-sdk#80, #79, #74): UCP JS SDK non-vacuous dependentRequired, per-variant fulfillment projection & title-bearing JWK crv/x/y conditional rules
- PR-07 (js-sdk#73, #71, #69, #63, #59, #58): UCP JS SDK business_schema discovery registries, shared integer vs unit-price fractional Measure, LocationServes maxProperties:1 & warning URI validation
- PR-08 (csharp-sdk#1933, #1932): MCP C# SDK stdio EOF subscriptions/listen cancellation & Streamable HTTP non-string routing name -32020 HeaderMismatch
- PR-09 (csharp-sdk#1928, #1903, #1900, #1895): MCP C# SDK DelegatingMcpServerTool legacy outputSchema, nullable ServerInfo, multi-variable URI template comma split & descendant process tree wait
- PR-10 (csharp-sdk#1905): MCP C# SDK ASP.NET Core non-DCR OAuth 2.1 proxy dual S256 PKCE, server-side upstream token isolation & refresh-token family replay revocation
- PR-11 (kotlin-sdk#1129, #1122, #1120): MCP Kotlin SDK 16 MiB WebSocket frame limit & non-stopping onError loop, empty _meta omission & unknown tool -32602 INVALID_PARAMS
- PR-12 (kotlin-sdk#1119, #1118, #1117): MCP Kotlin SDK single-path send error propagation, SEP-2243/2663 request-only Mcp-Method/Mcp-Name & blank-URI/empty-capture rejection
- PR-13 (swift-sdk#307, #298): MCP Swift SDK stateful HTTP post-DELETE session recovery (404 on retired ID) & stateless HTTP cancellation isolation + shutdown 503
- PR-14 (swift-sdk#305, #303, #300, #293): MCP Swift SDK WWW-Authenticate quoted-pair unescaping, unbiased PKCE threshold 197, RFC 6749 §2.3.1 client_secret_basic percent-encoding & OAuth issuer check
- PR-15 (swift-sdk#296, #295, #291, #288): MCP Swift SDK standalone GET SSE resume ID isolation, data: URL string preservation, structured error.data retention & SEP-2243 Base64 Mcp-Name
- PR-16 (swift-sdk#297, #292, #290, #289): MCP Swift SDK stdio O_NONBLOCK flag restoration on disconnect, raw response retention on decode failure, CacheableResult & experimental/extensions capabilities
"""

from __future__ import annotations

import base64
import re
from typing import Any, Mapping
from urllib.parse import quote, unquote


_REVERSE_DOMAIN_RE = re.compile(
    r"^[a-z](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9_-]*[a-z0-9_])?)+$"
)
_RFC3339_ABSOLUTE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})$"
)
_URI_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://[^\s]+$")

_REQUIRED_MOCK_AGENT_CAPABILITIES = frozenset(
    {
        "dev.ucp.shopping.buyer_consent",
        "dev.ucp.shopping.checkout",
        "dev.ucp.shopping.discount",
        "dev.ucp.shopping.fulfillment",
        "dev.ucp.shopping.order",
    }
)
_BUSINESS_OWNED_OMIT_FIELDS = ("continue_url", "expires_at", "messages", "order")


# ---------------------------------------------------------------------------
# PR-01: Universal-Commerce-Protocol/conformance#117 & #111
# ---------------------------------------------------------------------------
def evaluate_ucp_conformance_ready_for_complete_and_4xx_state_guard(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate ready_for_complete pre-completion status, 4xx state guard, and no 409 escape hatch."""
    nothing_outstanding = bool(payload.get("nothing_outstanding", True))
    pre_complete_status = str(payload.get("pre_complete_status", ""))
    post_complete_status = str(payload.get("post_complete_status", ""))
    invalid_transition_statuses = list(payload.get("invalid_transition_statuses", []))
    allow_409_stock_escape_hatch = bool(payload.get("allow_409_stock_escape_hatch", False))

    if nothing_outstanding and pre_complete_status != "ready_for_complete":
        return {
            "allow": False,
            "decision_code": "UCP_PRE_COMPLETE_STATUS_NOT_READY_BLOCKED",
            "reason": "When buyer and fulfillment are satisfied with no errors/actions, status before complete must be ready_for_complete.",
        }

    if post_complete_status != "completed":
        return {
            "allow": False,
            "decision_code": "UCP_COMPLETE_CHECKOUT_NOT_COMPLETED_BLOCKED",
            "reason": "Complete Checkout on a ready session with in-stock fixture must transition to completed.",
        }

    if allow_409_stock_escape_hatch:
        return {
            "allow": False,
            "decision_code": "UCP_COMPLETE_CHECKOUT_409_ESCAPE_HATCH_BLOCKED",
            "reason": "test_complete_checkout must not pass via a 409 out-of-stock early-return escape hatch.",
        }

    if not invalid_transition_statuses or any(
        not isinstance(code, int) or code < 400 or code >= 500
        for code in invalid_transition_statuses
    ):
        return {
            "allow": False,
            "decision_code": "UCP_STATE_TRANSITION_NON_4XX_ERROR_BLOCKED",
            "reason": "Invalid checkout state transitions must return 4xx client errors ([400, 500)), not 200 or 500.",
        }

    return {
        "allow": True,
        "decision_code": "UCP_CONFORMANCE_READY_AND_4XX_STATE_VERIFIED",
        "pre_complete_status": pre_complete_status,
        "checked_transitions": len(invalid_transition_statuses),
    }


# ---------------------------------------------------------------------------
# PR-02: Universal-Commerce-Protocol/conformance#115 & #109
# ---------------------------------------------------------------------------
def evaluate_ucp_conformance_ap2_negotiation_and_agent_profile_guard(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate AP2 capability intersection, mandate_required rejection, and mock agent capabilities."""
    platform_caps = dict(payload.get("platform_capabilities", {}))
    business_caps = dict(payload.get("business_capabilities", {}))
    has_checkout_mandate = bool(payload.get("has_checkout_mandate", False))
    mandate_token = str(payload.get("mandate_token", ""))
    completion_http_status = int(payload.get("completion_http_status", 200))
    ucp_status = str(payload.get("ucp_status", ""))
    error_code = str(payload.get("error_code", ""))
    mock_agent_profile_caps = set(payload.get("mock_agent_profile_capabilities", []))

    if not _REQUIRED_MOCK_AGENT_CAPABILITIES.issubset(mock_agent_profile_caps):
        return {
            "allow": False,
            "decision_code": "UCP_MOCK_AGENT_PROFILE_MISSING_CAPABILITIES_BLOCKED",
            "reason": "shopping-agent-test.json must declare all 5 exercised shopping capabilities.",
        }

    # Compute intersection with parent pruning
    common: dict[str, dict[str, Any]] = {}
    for name, p_entry in platform_caps.items():
        if name in business_caps:
            b_entry = business_caps[name]
            p_versions = set(p_entry.get("versions", []))
            b_versions = set(b_entry.get("versions", []))
            shared_versions = sorted(p_versions & b_versions)
            if shared_versions:
                common[name] = {
                    "version": shared_versions[-1],
                    "extends": p_entry.get("extends") or b_entry.get("extends"),
                }

    changed = True
    while changed:
        changed = False
        for name in list(common.keys()):
            parent = common[name].get("extends")
            if parent and parent not in common:
                del common[name]
                changed = True

    ap2_negotiated = (
        "dev.ucp.shopping.ap2_mandate" in common
        or "dev.ucp.common.payment.ap2_mandate" in common
    )
    if not ap2_negotiated:
        return {
            "allow": False,
            "decision_code": "UCP_AP2_CAPABILITY_NOT_IN_INTERSECTION_BLOCKED",
            "reason": "AP2 capability must be negotiated in the pruned platform/business intersection.",
        }

    if not has_checkout_mandate:
        valid_mandate_required = (
            (completion_http_status == 200 and ucp_status == "error" and error_code == "mandate_required")
            or (400 <= completion_http_status < 500 and error_code == "mandate_required")
        )
        if not valid_mandate_required:
            return {
                "allow": False,
                "decision_code": "UCP_AP2_MISSING_MANDATE_NOT_REJECTED_BLOCKED",
                "reason": "When AP2 is negotiated, completion without ap2.checkout_mandate must fail with mandate_required.",
            }
    else:
        if mandate_token == "header.payload.signature~kb_signature":
            return {
                "allow": False,
                "decision_code": "UCP_AP2_PLACEHOLDER_MANDATE_ACCEPTED_BLOCKED",
                "reason": "Placeholder header.payload.signature~kb_signature mandate must not pass cryptographic AP2 verification.",
            }

    return {
        "allow": True,
        "decision_code": "UCP_AP2_NEGOTIATION_AND_AGENT_PROFILE_VERIFIED",
        "negotiated_capabilities": sorted(common.keys()),
    }


# ---------------------------------------------------------------------------
# PR-03: Universal-Commerce-Protocol/conformance#112, #98, & #97
# ---------------------------------------------------------------------------
def evaluate_ucp_conformance_field_ownership_discovery_and_address_guard(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate ucp_request:omit business field ownership, strict discovery URLs, and canonical address fields."""
    caller_injected_fields = dict(payload.get("caller_injected_fields", {}))
    create_response_fields = dict(payload.get("create_response_fields", {}))
    stored_checkout_fields = dict(payload.get("stored_checkout_fields", {}))
    omitted_fields_create_status = int(payload.get("omitted_fields_create_status", 200))
    discovery_urls = list(payload.get("discovery_urls", []))
    allow_unreachable_substrings = list(payload.get("allow_unreachable_urls", []))
    shipping_destination = dict(payload.get("shipping_destination", {}))

    for field in _BUSINESS_OWNED_OMIT_FIELDS:
        caller_val = caller_injected_fields.get(field)
        if caller_val is not None:
            if create_response_fields.get(field) == caller_val or stored_checkout_fields.get(field) == caller_val:
                return {
                    "allow": False,
                    "decision_code": "UCP_CALLER_OWNED_OMIT_FIELD_LEAK_BLOCKED",
                    "reason": f"Business-owned field '{field}' (ucp_request: omit) must not adopt caller-supplied value in create or stored checkout.",
                }

    if omitted_fields_create_status != 200:
        return {
            "allow": False,
            "decision_code": "UCP_OMIT_FIELDS_ABSENCE_REJECTED_BLOCKED",
            "reason": "Create checkout without business-owned ucp_request:omit fields must succeed (HTTP 200).",
        }

    for entry in discovery_urls:
        url = str(entry.get("url", ""))
        status = int(entry.get("status", 404))
        if status != 200:
            allowed = any(sub in url for sub in allow_unreachable_substrings)
            if not allowed:
                return {
                    "allow": False,
                    "decision_code": "UCP_DISCOVERY_URL_UNREACHABLE_BLOCKED",
                    "reason": f"Discovery URL '{url}' returned {status} and is not in allow_unreachable_urls.",
                }

    if "locality" in shipping_destination or "region" in shipping_destination:
        return {
            "allow": False,
            "decision_code": "UCP_NON_CANONICAL_SHIPPING_ADDRESS_KEYS_BLOCKED",
            "reason": "ShippingDestination must serialize canonical address_locality and address_region, not locality/region.",
        }
    if not shipping_destination.get("address_locality") or not shipping_destination.get("address_region"):
        return {
            "allow": False,
            "decision_code": "UCP_MISSING_CANONICAL_SHIPPING_ADDRESS_KEYS_BLOCKED",
            "reason": "ShippingDestination requires non-empty canonical address_locality and address_region.",
        }

    return {
        "allow": True,
        "decision_code": "UCP_FIELD_OWNERSHIP_DISCOVERY_AND_ADDRESS_VERIFIED",
        "verified_urls": len(discovery_urls),
    }


# ---------------------------------------------------------------------------
# PR-04: Universal-Commerce-Protocol/conformance#89
# ---------------------------------------------------------------------------
def evaluate_ucp_payment_terms_conformance_invariants_guard(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate all 7 cross-field wire invariants for dev.ucp.common.payment.terms (terms.md)."""
    terms = list(payload.get("terms", []))
    selected_term_id = str(payload.get("selected_term_id", ""))
    checkout_total = int(payload.get("checkout_total", -1))
    requested_term_id = str(payload.get("requested_term_id", selected_term_id))
    in_place_schedule_rewritten = bool(payload.get("in_place_schedule_rewritten", False))
    warning_codes = set(payload.get("warning_codes", []))
    order_accepted_term = dict(payload.get("order_accepted_term", {}))
    order_total = int(payload.get("order_total", -1))

    if not terms:
        return {
            "allow": False,
            "decision_code": "UCP_PAYMENT_TERMS_EMPTY_LIST_BLOCKED",
            "reason": "When payment.terms is present, it must contain at least one term.",
        }

    term_ids = [str(t.get("id", "")) for t in terms]
    if len(set(term_ids)) != len(term_ids) or any(not tid for tid in term_ids):
        return {
            "allow": False,
            "decision_code": "UCP_PAYMENT_TERMS_DUPLICATE_ID_BLOCKED",
            "reason": "payment.terms[].id must be non-empty and unique within a checkout.",
        }

    selected_matches = [t for t in terms if str(t.get("id", "")) == selected_term_id]
    if len(selected_matches) != 1:
        return {
            "allow": False,
            "decision_code": "UCP_PAYMENT_TERMS_DANGLING_SELECTED_ID_BLOCKED",
            "reason": "selected_term_id must resolve to exactly one offered terms[].id.",
        }

    selected_term = selected_matches[0]
    schedules = list(selected_term.get("schedules", []))
    schedule_sum = sum(int(s.get("amount", 0)) for s in schedules)
    if schedule_sum != checkout_total:
        return {
            "allow": False,
            "decision_code": "UCP_PAYMENT_TERMS_SCHEDULE_SUM_MISMATCH_BLOCKED",
            "reason": f"Selected term schedule sum ({schedule_sum}) must equal checkout total ({checkout_total}).",
        }

    for term in terms:
        for sched in term.get("schedules", []):
            due_at = sched.get("due_at")
            if due_at is not None and not _RFC3339_ABSOLUTE_RE.match(str(due_at)):
                return {
                    "allow": False,
                    "decision_code": "UCP_PAYMENT_TERMS_NAIVE_OR_INVALID_DUE_AT_BLOCKED",
                    "reason": "Every schedule due_at must be an absolute RFC 3339 timestamp with UTC offset.",
                }

    if (requested_term_id != selected_term_id or in_place_schedule_rewritten) and (
        "payment_term_changed" not in warning_codes
    ):
        return {
            "allow": False,
            "decision_code": "UCP_PAYMENT_TERMS_SILENT_SUBSTITUTION_BLOCKED",
            "reason": "Changing or rewriting the selected payment term requires a payment_term_changed warning.",
        }

    order_schedules = list(order_accepted_term.get("schedules", []))
    order_schedule_sum = sum(int(s.get("amount", 0)) for s in order_schedules)
    if (
        str(order_accepted_term.get("id", "")) != selected_term_id
        or not order_schedules
        or order_schedule_sum != order_total
    ):
        return {
            "allow": False,
            "decision_code": "UCP_ORDER_ACCEPTED_TERM_INVARIANT_BLOCKED",
            "reason": "Order payment.accepted_term must match the ready_for_complete term and sum to order_total.",
        }

    return {
        "allow": True,
        "decision_code": "UCP_PAYMENT_TERMS_INVARIANTS_VERIFIED",
        "selected_term_id": selected_term_id,
        "schedule_sum": schedule_sum,
    }


# ---------------------------------------------------------------------------
# PR-05: Universal-Commerce-Protocol/js-sdk#87, #84, & #83
# ---------------------------------------------------------------------------
def evaluate_ucp_js_sdk_open_schema_union_and_binding_split_guard(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate <Union>Base not.enum fatal guard, open-schema .catchall(z.any()), and Binding/Destination split."""
    union_base_has_fatal_not_enum = bool(payload.get("union_base_has_fatal_not_enum", False))
    known_variant_invalid_payload_accepted = bool(payload.get("known_variant_invalid_payload_accepted", False))
    parsed_credential_token = payload.get("parsed_credential_token")
    parsed_ap2_extension = payload.get("parsed_ap2_extension")
    closed_error_response_strict = bool(payload.get("closed_error_response_strict", False))
    destination_type = str(payload.get("destination_type", "shipping_address"))
    destination_accepted = bool(payload.get("destination_accepted", False))
    binding_type = str(payload.get("binding_type", "dev.ucp.shopping.checkout"))
    binding_id = str(payload.get("binding_id", "co_1"))

    if not union_base_has_fatal_not_enum or known_variant_invalid_payload_accepted:
        return {
            "allow": False,
            "decision_code": "UCP_JS_SDK_OPEN_UNION_BASE_FALLTHROUGH_BLOCKED",
            "reason": "Open-union <Union>Base schemas must enforce fatal not.enum guards so invalid known variants do not fall through.",
        }

    if not parsed_credential_token or not parsed_ap2_extension or not closed_error_response_strict:
        return {
            "allow": False,
            "decision_code": "UCP_JS_SDK_OPEN_SCHEMA_CREDENTIAL_STRIPPED_BLOCKED",
            "reason": "Open UCP schemas must retain payment.instruments[].credential.token and ap2 via .catchall(z.any()) while closed error schemas stay .strict().",
        }

    if destination_type == "shipping_address" and not destination_accepted:
        return {
            "allow": False,
            "decision_code": "UCP_JS_SDK_DESTINATION_POISONED_BY_BINDING_REGEX_BLOCKED",
            "reason": "FulfillmentDestinationSchema must accept bare token 'shipping_address' without BindingSchema's reverse-domain regex.",
        }

    if not _REVERSE_DOMAIN_RE.match(binding_type) or len(binding_id) < 1:
        return {
            "allow": False,
            "decision_code": "UCP_JS_SDK_BINDING_SCHEMA_CONSTRAINT_MISSING_BLOCKED",
            "reason": "Standalone BindingSchema must enforce reverse-domain type regex and id minLength >= 1.",
        }

    return {
        "allow": True,
        "decision_code": "UCP_JS_SDK_OPEN_SCHEMA_UNION_AND_BINDING_VERIFIED",
        "destination_type": destination_type,
        "binding_type": binding_type,
    }


# ---------------------------------------------------------------------------
# PR-06: Universal-Commerce-Protocol/js-sdk#80, #79, & #74
# ---------------------------------------------------------------------------
def evaluate_ucp_js_sdk_dependent_required_fulfillment_and_jwk_guard(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate non-vacuous dependentRequired, per-variant fulfillment projection, and JWK crv/x/y rules."""
    time_interval = dict(payload.get("time_interval", {}))
    fulfillment_update = dict(payload.get("fulfillment_update", {}))
    fulfillment_create_requires_id_or_line_items = bool(
        payload.get("fulfillment_create_requires_id_or_line_items", False)
    )
    fulfillment_create_retains_shipping_destinations = bool(
        payload.get("fulfillment_create_retains_shipping_destinations", True)
    )
    vacuous_dependent_required_skipped = bool(payload.get("vacuous_dependent_required_skipped", True))
    jwk_key = dict(payload.get("jwk_public_key", {}))

    has_opens = "opens" in time_interval and time_interval["opens"] is not None
    has_closes = "closes" in time_interval and time_interval["closes"] is not None
    if has_opens != has_closes:
        return {
            "allow": False,
            "decision_code": "UCP_JS_SDK_TIME_INTERVAL_DEPENDENT_REQUIRED_BLOCKED",
            "reason": "TimeInterval/DailyHour/ExceptionHour require opens and closes to appear together.",
        }

    if "destinations" in fulfillment_update and not fulfillment_update.get("type"):
        return {
            "allow": False,
            "decision_code": "UCP_JS_SDK_FULFILLMENT_UPDATE_DESTINATIONS_WITHOUT_TYPE_BLOCKED",
            "reason": "FulfillmentMethodUpdateRequestSchema requires 'type' when 'destinations' is present.",
        }

    if (
        fulfillment_create_requires_id_or_line_items
        or not fulfillment_create_retains_shipping_destinations
        or not vacuous_dependent_required_skipped
    ):
        return {
            "allow": False,
            "decision_code": "UCP_JS_SDK_FULFILLMENT_VARIANT_PROJECTION_INVALID_BLOCKED",
            "reason": "FulfillmentMethodCreateRequestSchema must omit response-only id/line_item_ids, retain shipping destinations, and skip vacuous dependentRequired.",
        }

    kty = str(jwk_key.get("kty", ""))
    if kty == "EC" and not (jwk_key.get("crv") and jwk_key.get("x") and jwk_key.get("y")):
        return {
            "allow": False,
            "decision_code": "UCP_JS_SDK_JWK_EC_MISSING_CRV_X_Y_BLOCKED",
            "reason": "jwk_public_key conditional rule requires crv, x, and y when kty == 'EC'.",
        }
    if kty == "OKP" and not (jwk_key.get("crv") and jwk_key.get("x")):
        return {
            "allow": False,
            "decision_code": "UCP_JS_SDK_JWK_OKP_MISSING_CRV_X_BLOCKED",
            "reason": "jwk_public_key conditional rule requires crv and x when kty == 'OKP'.",
        }

    return {
        "allow": True,
        "decision_code": "UCP_JS_SDK_DEPENDENT_REQUIRED_FULFILLMENT_AND_JWK_VERIFIED",
        "jwk_kty": kty,
    }


# ---------------------------------------------------------------------------
# PR-07: Universal-Commerce-Protocol/js-sdk#73, #71, #69, #63, #59, & #58
# ---------------------------------------------------------------------------
def evaluate_ucp_js_sdk_discovery_measure_location_and_warning_uri_guard(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate business_schema discovery registries, shared vs unit-price Measure, LocationServes, and warning URIs."""
    discovery_ucp = dict(payload.get("discovery_ucp", {}))
    capability_extends = payload.get("capability_extends")
    shared_measure_value = payload.get("shared_measure_value", 0)
    unit_price_measure_value = payload.get("unit_price_measure_value", 0.5)
    unit_price_reference_value = payload.get("unit_price_reference_value", 100)
    location_serves = dict(payload.get("location_serves", {}))
    warning_message = dict(payload.get("warning_message", {}))

    services = discovery_ucp.get("services")
    payment_handlers = discovery_ucp.get("payment_handlers")
    capabilities = discovery_ucp.get("capabilities", {})
    if (
        not isinstance(services, Mapping)
        or not isinstance(payment_handlers, Mapping)
        or not isinstance(capabilities, Mapping)
        or any(not isinstance(v, list) for v in services.values())
        or any(not isinstance(v, list) for v in payment_handlers.values())
        or any(not isinstance(v, list) for v in capabilities.values())
    ):
        return {
            "allow": False,
            "decision_code": "UCP_JS_SDK_DISCOVERY_REGISTRY_SHAPE_INVALID_BLOCKED",
            "reason": "UcpDiscoveryProfileSchema.ucp requires services and payment_handlers (and optional capabilities) as records of entity arrays.",
        }

    if isinstance(capability_extends, str):
        extends_valid = bool(_REVERSE_DOMAIN_RE.match(capability_extends))
    elif isinstance(capability_extends, list):
        extends_valid = len(capability_extends) >= 1 and all(
            isinstance(item, str) and bool(_REVERSE_DOMAIN_RE.match(item))
            for item in capability_extends
        )
    else:
        extends_valid = False

    if not extends_valid:
        return {
            "allow": False,
            "decision_code": "UCP_JS_SDK_CAPABILITY_EXTENDS_INVALID_BLOCKED",
            "reason": "CapabilityDiscoverySchema.extends must be a reverse-domain string or non-empty array of reverse-domain strings.",
        }

    if (
        isinstance(shared_measure_value, bool)
        or not isinstance(shared_measure_value, int)
        or abs(shared_measure_value) > 9007199254740991
    ):
        return {
            "allow": False,
            "decision_code": "UCP_JS_SDK_SHARED_MEASURE_NON_INTEGER_BLOCKED",
            "reason": "Shared MeasureSchema.value must be a safe integer in [-9007199254740991, 9007199254740991].",
        }

    if (
        isinstance(unit_price_measure_value, bool)
        or not isinstance(unit_price_measure_value, (int, float))
        or isinstance(unit_price_reference_value, bool)
        or not isinstance(unit_price_reference_value, int)
    ):
        return {
            "allow": False,
            "decision_code": "UCP_JS_SDK_UNIT_PRICE_MEASURE_TYPE_INVALID_BLOCKED",
            "reason": "Unit-price measure.value must accept numbers while reference.value requires an integer.",
        }

    if len(location_serves) != 1:
        return {
            "allow": False,
            "decision_code": "UCP_JS_SDK_LOCATION_SERVES_PROPERTY_COUNT_BLOCKED",
            "reason": "LocationServesSchema enforces minProperties: 1 and maxProperties: 1 (exactly one target entry).",
        }

    if warning_message.get("type") == "warning":
        for field in ("url", "image_url"):
            val = warning_message.get(field)
            if val is not None and not _URI_RE.match(str(val)):
                return {
                    "allow": False,
                    "decision_code": "UCP_JS_SDK_WARNING_MESSAGE_INVALID_URI_BLOCKED",
                    "reason": f"CheckoutResponseMessageSchema warning field '{field}' must be a valid URI.",
                }

    return {
        "allow": True,
        "decision_code": "UCP_JS_SDK_DISCOVERY_MEASURE_LOCATION_AND_WARNING_URI_VERIFIED",
        "location_serves_keys": list(location_serves.keys()),
    }


# ---------------------------------------------------------------------------
# PR-08: modelcontextprotocol/csharp-sdk#1933 & #1932
# ---------------------------------------------------------------------------
def evaluate_mcp_csharp_stdio_listen_eof_and_routing_name_type_guard(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate stdio EOF subscriptions/listen cancellation and non-string routing field -32020 error."""
    stdio_eof_cancels_subscriptions_listen = bool(
        payload.get("stdio_eof_cancels_subscriptions_listen", False)
    )
    stdio_eof_preserves_inflight_tools_call = bool(
        payload.get("stdio_eof_preserves_inflight_tools_call", False)
    )
    routing_field_value = payload.get("routing_field_value")
    http_status = int(payload.get("http_status", 200))
    jsonrpc_error_code = payload.get("jsonrpc_error_code")
    jsonrpc_error_id = payload.get("jsonrpc_error_id")
    request_id = payload.get("request_id", 1)

    if not stdio_eof_cancels_subscriptions_listen or not stdio_eof_preserves_inflight_tools_call:
        return {
            "allow": False,
            "decision_code": "MCP_CSHARP_STDIO_EOF_LISTEN_LEAK_BLOCKED",
            "reason": "McpSessionHandler must cancel open subscriptions/listen requests on stdin EOF while allowing in-flight tools/call handlers to finish.",
        }

    if not isinstance(routing_field_value, str):
        if http_status != 400 or jsonrpc_error_code != -32020 or jsonrpc_error_id != request_id:
            return {
                "allow": False,
                "decision_code": "MCP_CSHARP_NON_STRING_ROUTING_FIELD_500_BLOCKED",
                "reason": "Non-string params.name/params.uri in Streamable HTTP body must return HTTP 400 with JSON-RPC -32020 HeaderMismatch and original id.",
            }

    return {
        "allow": True,
        "decision_code": "MCP_CSHARP_STDIO_LISTEN_EOF_AND_ROUTING_TYPE_VERIFIED",
        "http_status": http_status,
        "jsonrpc_error_code": jsonrpc_error_code,
    }


# ---------------------------------------------------------------------------
# PR-09: modelcontextprotocol/csharp-sdk#1928, #1903, #1900, & #1895
# ---------------------------------------------------------------------------
def evaluate_mcp_csharp_delegating_schema_serverinfo_uritemplate_and_killtree_guard(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate DelegatingMcpServerTool legacy outputSchema, nullable ServerInfo, URI template comma split, and KillTree descendant wait."""
    delegating_tool_legacy_output_schema_transformed = bool(
        payload.get("delegating_tool_legacy_output_schema_transformed", False)
    )
    connected_without_server_info_returns_null = bool(
        payload.get("connected_without_server_info_returns_null", False)
    )
    disconnected_server_info_throws = bool(payload.get("disconnected_server_info_throws", False))
    uri_template = str(payload.get("uri_template", "resource://coords/{+lat,lon}"))
    uri_input = str(payload.get("uri_input", "resource://coords/45.4,9.1"))
    parsed_vars = dict(payload.get("parsed_vars", {}))
    kill_tree_waits_for_descendants = bool(payload.get("kill_tree_waits_for_descendants", False))
    pid_reuse_start_time_checked = bool(payload.get("pid_reuse_start_time_checked", False))

    if not delegating_tool_legacy_output_schema_transformed:
        return {
            "allow": False,
            "decision_code": "MCP_CSHARP_DELEGATING_TOOL_LEGACY_SCHEMA_MISSING_BLOCKED",
            "reason": "DelegatingMcpServerTool must apply the legacy outputSchema transform for 2025-06-18 and 2025-11-25 clients.",
        }

    if not connected_without_server_info_returns_null or not disconnected_server_info_throws:
        return {
            "allow": False,
            "decision_code": "MCP_CSHARP_SERVER_INFO_NULLABILITY_INVALID_BLOCKED",
            "reason": "McpClient.ServerInfo must return null when a connected 2026-07-28 server omits serverInfo and throw when disconnected.",
        }

    if "{+lat,lon}" in uri_template or "{lat,lon}" in uri_template or "{#lat,lon}" in uri_template:
        tail = uri_input.split("resource://coords/", 1)[-1].lstrip("#")
        parts = tail.split(",")
        if len(parts) != 2:
            return {
                "allow": False,
                "decision_code": "MCP_CSHARP_MULTI_VAR_URI_TEMPLATE_UNENCODED_COMMA_BLOCKED",
                "reason": "Multi-variable URI template must split on literal comma and reject unencoded commas inside values.",
            }
        expected_lat = unquote(parts[0])
        expected_lon = unquote(parts[1])
        if parsed_vars.get("lat") != expected_lat or parsed_vars.get("lon") != expected_lon:
            return {
                "allow": False,
                "decision_code": "MCP_CSHARP_MULTI_VAR_URI_TEMPLATE_GREEDY_MATCH_BLOCKED",
                "reason": "Multi-variable URI template must not greedily capture the comma and second variable into the first variable.",
            }

    if not kill_tree_waits_for_descendants or not pid_reuse_start_time_checked:
        return {
            "allow": False,
            "decision_code": "MCP_CSHARP_KILL_TREE_ORPHAN_DESCENDANT_BLOCKED",
            "reason": "ProcessHelper.KillTree must snapshot and wait on all descendant processes with start-time PID-reuse protection.",
        }

    return {
        "allow": True,
        "decision_code": "MCP_CSHARP_DELEGATING_SERVERINFO_TEMPLATE_AND_KILLTREE_VERIFIED",
        "parsed_vars": parsed_vars,
    }


# ---------------------------------------------------------------------------
# PR-10: modelcontextprotocol/csharp-sdk#1905
# ---------------------------------------------------------------------------
def evaluate_mcp_csharp_aspnetcore_oauth_proxy_guard(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate ASP.NET Core OAuth 2.1 proxy dual S256 PKCE, upstream token isolation, and refresh replay revocation."""
    client_to_proxy_pkce = str(payload.get("client_to_proxy_pkce_challenge", ""))
    proxy_to_provider_pkce = str(payload.get("proxy_to_provider_pkce_challenge", ""))
    upstream_tokens_kept_server_side = bool(payload.get("upstream_tokens_kept_server_side", False))
    upstream_token_returned_to_client = bool(payload.get("upstream_token_returned_to_client", False))
    refresh_token_replayed = bool(payload.get("refresh_token_replayed", False))
    descendant_family_revoked = bool(payload.get("descendant_family_revoked", False))
    audit_record = dict(payload.get("audit_record", {}))

    if not client_to_proxy_pkce or not proxy_to_provider_pkce or client_to_proxy_pkce == proxy_to_provider_pkce:
        return {
            "allow": False,
            "decision_code": "MCP_CSHARP_OAUTH_PROXY_SHARED_PKCE_BLOCKED",
            "reason": "OAuth proxy must use separate S256 PKCE flows for client-to-proxy and proxy-to-provider exchanges.",
        }

    if not upstream_tokens_kept_server_side or upstream_token_returned_to_client:
        return {
            "allow": False,
            "decision_code": "MCP_CSHARP_OAUTH_PROXY_UPSTREAM_TOKEN_LEAK_BLOCKED",
            "reason": "Upstream IDP access/refresh tokens must remain server-side in IMcpOAuthProxyStore and never be returned to MCP clients.",
        }

    if refresh_token_replayed and not descendant_family_revoked:
        return {
            "allow": False,
            "decision_code": "MCP_CSHARP_OAUTH_PROXY_REPLAY_UNREVOKED_BLOCKED",
            "reason": "Replayed refresh tokens must revoke the entire descendant refresh-token family.",
        }

    required_audit_keys = ("subject", "audience", "scopes", "client_id", "token_id", "minted_at")
    if any(not audit_record.get(k) for k in required_audit_keys):
        return {
            "allow": False,
            "decision_code": "MCP_CSHARP_OAUTH_PROXY_AUDIT_INCOMPLETE_BLOCKED",
            "reason": "Token-mint audit records must include subject, audience, scopes, client_id, token_id, and minted_at.",
        }

    return {
        "allow": True,
        "decision_code": "MCP_CSHARP_ASPNETCORE_OAUTH_PROXY_VERIFIED",
        "token_id": str(audit_record["token_id"]),
    }


# ---------------------------------------------------------------------------
# PR-11: modelcontextprotocol/kotlin-sdk#1129, #1122, & #1120
# ---------------------------------------------------------------------------
def evaluate_mcp_kotlin_websocket_limit_empty_meta_and_unknown_tool_guard(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate 16 MiB WebSocket frame limit & non-stopping onError loop, empty _meta omission, and unknown tool -32602."""
    max_frame_size_bytes = int(payload.get("max_frame_size_bytes", 0))
    inbound_frame_bytes = int(payload.get("inbound_frame_bytes", 0))
    continues_reading_after_malformed_frame = bool(
        payload.get("continues_reading_after_malformed_frame", False)
    )
    call_tool_wire_payload = dict(payload.get("call_tool_wire_payload", {}))
    unknown_tool_called = bool(payload.get("unknown_tool_called", False))
    unknown_tool_response_code = payload.get("unknown_tool_response_code")
    unknown_tool_returned_is_error_result = bool(
        payload.get("unknown_tool_returned_is_error_result", False)
    )

    limit_16_mib = 16 * 1024 * 1024
    if max_frame_size_bytes != limit_16_mib or inbound_frame_bytes > limit_16_mib or not continues_reading_after_malformed_frame:
        return {
            "allow": False,
            "decision_code": "MCP_KOTLIN_WEBSOCKET_FRAME_OR_READ_LOOP_BLOCKED",
            "reason": "WebSocket transport must enforce 16 MiB maxFrameSize and continue reading after reporting malformed frames via onError.",
        }

    params = dict(call_tool_wire_payload.get("params", {}))
    if "_meta" in params and params["_meta"] == {}:
        return {
            "allow": False,
            "decision_code": "MCP_KOTLIN_CALL_TOOL_EMPTY_META_SENT_BLOCKED",
            "reason": "Client.callTool must omit _meta on the wire when empty rather than sending '\"_meta\": {}'.",
        }

    if unknown_tool_called and (
        unknown_tool_returned_is_error_result or unknown_tool_response_code != -32602
    ):
        return {
            "allow": False,
            "decision_code": "MCP_KOTLIN_UNKNOWN_TOOL_IS_ERROR_MASKING_BLOCKED",
            "reason": "Calling an unregistered tool must return JSON-RPC -32602 INVALID_PARAMS rather than CallToolResult(isError=true).",
        }

    return {
        "allow": True,
        "decision_code": "MCP_KOTLIN_WEBSOCKET_META_AND_UNKNOWN_TOOL_VERIFIED",
        "max_frame_size_bytes": max_frame_size_bytes,
    }


# ---------------------------------------------------------------------------
# PR-12: modelcontextprotocol/kotlin-sdk#1119, #1118, & #1117
# ---------------------------------------------------------------------------
def evaluate_mcp_kotlin_send_error_mcp_headers_and_uri_template_guard(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate single-path send error propagation, SEP-2243/2663 Mcp-Method/Mcp-Name headers, and blank URI rejection."""
    sync_send_failure_on_error_calls = int(payload.get("sync_send_failure_on_error_calls", 0))
    sync_send_failure_thrown_to_caller = bool(payload.get("sync_send_failure_thrown_to_caller", False))
    is_notification = bool(payload.get("is_notification", False))
    method = str(payload.get("method", "tools/call"))
    headers = dict(payload.get("headers", {}))
    resource_uri = str(payload.get("resource_uri", "file:///report.txt"))
    template_variable_capture = payload.get("template_variable_capture", "item_42")

    if not sync_send_failure_thrown_to_caller or sync_send_failure_on_error_calls != 0:
        return {
            "allow": False,
            "decision_code": "MCP_KOTLIN_DUPLICATE_SEND_ERROR_REPORTING_BLOCKED",
            "reason": "Synchronous client send() failures must propagate once via thrown exception without duplicate onError reports.",
        }

    if is_notification and ("Mcp-Method" in headers or "Mcp-Name" in headers):
        return {
            "allow": False,
            "decision_code": "MCP_KOTLIN_NOTIFICATION_ROUTING_HEADERS_BLOCKED",
            "reason": "Notifications must not carry Mcp-Method or Mcp-Name headers.",
        }

    allowed_mcp_name_methods = {
        "tools/call",
        "prompts/get",
        "resources/read",
        "tasks/get",
        "tasks/cancel",
    }
    if not is_notification:
        if headers.get("Mcp-Method") != method:
            return {
                "allow": False,
                "decision_code": "MCP_KOTLIN_MISSING_MCP_METHOD_HEADER_BLOCKED",
                "reason": "JSON-RPC requests must carry Mcp-Method matching the request method.",
            }
        if method not in allowed_mcp_name_methods and "Mcp-Name" in headers:
            return {
                "allow": False,
                "decision_code": "MCP_KOTLIN_UNSUPPORTED_METHOD_MCP_NAME_BLOCKED",
                "reason": f"Method '{method}' must not carry Mcp-Name per SEP-2243/SEP-2663.",
            }

    if not resource_uri.strip() or (
        template_variable_capture is not None and str(template_variable_capture) == ""
    ):
        return {
            "allow": False,
            "decision_code": "MCP_KOTLIN_BLANK_URI_OR_EMPTY_CAPTURE_BLOCKED",
            "reason": "PathSegmentTemplateMatcher must reject blank URIs and empty template variable captures.",
        }

    return {
        "allow": True,
        "decision_code": "MCP_KOTLIN_SEND_HEADERS_AND_URI_TEMPLATE_VERIFIED",
        "method": method,
        "resource_uri": resource_uri,
    }


# ---------------------------------------------------------------------------
# PR-13: modelcontextprotocol/swift-sdk#307 & #298
# ---------------------------------------------------------------------------
def evaluate_mcp_swift_stateful_delete_recovery_and_stateless_cancel_guard(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate stateful HTTP post-DELETE session recovery (404 on retired ID) and stateless cancellation isolation."""
    retired_session_id = str(payload.get("retired_session_id", "sess_old"))
    new_session_id = str(payload.get("new_session_id", "sess_new"))
    retired_session_http_status = int(payload.get("retired_session_http_status", 404))
    concurrent_request_affected_by_cancel = bool(
        payload.get("concurrent_request_affected_by_cancel", False)
    )
    late_handler_sent_second_response = bool(payload.get("late_handler_sent_second_response", False))
    ambiguous_cancel_affected_active = bool(payload.get("ambiguous_cancel_affected_active", False))
    shutdown_inflight_http_status = int(payload.get("shutdown_inflight_http_status", 503))

    if (
        not retired_session_id
        or not new_session_id
        or retired_session_id == new_session_id
        or retired_session_http_status != 404
    ):
        return {
            "allow": False,
            "decision_code": "MCP_SWIFT_STATEFUL_DELETE_RECOVERY_INVALID_BLOCKED",
            "reason": "Stateful HTTP endpoint must return 404 for a DELETEd session ID and allocate a fresh session ID on subsequent initialize.",
        }

    if (
        concurrent_request_affected_by_cancel
        or late_handler_sent_second_response
        or ambiguous_cancel_affected_active
        or shutdown_inflight_http_status != 503
    ):
        return {
            "allow": False,
            "decision_code": "MCP_SWIFT_STATELESS_CANCEL_ISOLATION_VIOLATION_BLOCKED",
            "reason": "Stateless HTTP requests must isolate cancellation per exchange, prevent duplicate late responses, ignore ambiguous cancel IDs, and return 503 on server shutdown.",
        }

    return {
        "allow": True,
        "decision_code": "MCP_SWIFT_STATEFUL_DELETE_AND_STATELESS_CANCEL_VERIFIED",
        "new_session_id": new_session_id,
        "shutdown_inflight_http_status": shutdown_inflight_http_status,
    }


# ---------------------------------------------------------------------------
# PR-14: modelcontextprotocol/swift-sdk#305, #303, #300, & #293
# ---------------------------------------------------------------------------
def evaluate_mcp_swift_oauth_www_auth_pkce_basic_and_issuer_guard(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate WWW-Authenticate quoted-pair unescaping, unbiased PKCE threshold 197, RFC 6749 client_secret_basic, and OAuth issuer check."""
    raw_quoted_param = str(payload.get("raw_quoted_param", r"insufficient\_scope"))
    parsed_quoted_param = str(payload.get("parsed_quoted_param", "insufficient_scope"))
    pkce_rejection_threshold = int(payload.get("pkce_rejection_threshold", 197))
    client_id = str(payload.get("client_id", "app:client+1"))
    client_secret = str(payload.get("client_secret", "s3cr3t@%!"))
    basic_auth_header = str(payload.get("basic_auth_header", ""))
    metadata_issuer = str(payload.get("metadata_issuer", "https://auth.example.com"))
    callback_issuer = str(payload.get("callback_issuer", "https://auth.example.com"))
    re_registered_on_as_change = bool(payload.get("re_registered_on_as_change", True))

    expected_unescaped = re.sub(r"\\(.)", r"\1", raw_quoted_param)
    if parsed_quoted_param != expected_unescaped:
        return {
            "allow": False,
            "decision_code": "MCP_SWIFT_WWW_AUTHENTICATE_QUOTED_PAIR_BLOCKED",
            "reason": "WWW-Authenticate parser must unescape all RFC 7230 §3.2.6 quoted-pair sequences character by character.",
        }

    if pkce_rejection_threshold != 197:
        return {
            "allow": False,
            "decision_code": "MCP_SWIFT_PKCE_MODULO_BIAS_THRESHOLD_BLOCKED",
            "reason": "PKCE.makeVerifier rejection-sampling threshold must be 197 (3 * 66 - 1) to eliminate modulo bias.",
        }

    encoded_id = quote(client_id, safe="-._~")
    encoded_secret = quote(client_secret, safe="-._~")
    expected_b64 = base64.b64encode(f"{encoded_id}:{encoded_secret}".encode("utf-8")).decode("ascii")
    if basic_auth_header != f"Basic {expected_b64}":
        return {
            "allow": False,
            "decision_code": "MCP_SWIFT_CLIENT_SECRET_BASIC_UNENCODED_BLOCKED",
            "reason": "client_secret_basic must percent-encode client_id and client_secret per RFC 6749 §2.3.1 before Base64 encoding.",
        }

    if not metadata_issuer or metadata_issuer != callback_issuer or not re_registered_on_as_change:
        return {
            "allow": False,
            "decision_code": "MCP_SWIFT_OAUTH_ISSUER_OR_DCR_MISMATCH_BLOCKED",
            "reason": "OAuth client must verify metadata and callback issuers match and re-register when the authorization server changes.",
        }

    return {
        "allow": True,
        "decision_code": "MCP_SWIFT_OAUTH_WWW_AUTH_PKCE_BASIC_AND_ISSUER_VERIFIED",
        "pkce_rejection_threshold": pkce_rejection_threshold,
    }


# ---------------------------------------------------------------------------
# PR-15: modelcontextprotocol/swift-sdk#296, #295, #291, & #288
# ---------------------------------------------------------------------------
def evaluate_mcp_swift_sse_resume_dataurl_errordata_and_mcp_name_guard(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate standalone GET SSE resume ID isolation, data: URL string preservation, structured error.data, and SEP-2243 Mcp-Name."""
    standalone_get_last_event_id = str(payload.get("standalone_get_last_event_id", "get_evt_1"))
    post_sse_event_id = str(payload.get("post_sse_event_id", "post_evt_9"))
    reconnect_resumed_event_id = str(payload.get("reconnect_resumed_event_id", "get_evt_1"))
    data_url_input = str(payload.get("data_url_input", "data:text/plain;base64,SGVsbG8="))
    decoded_value_kind = str(payload.get("decoded_value_kind", "string"))
    jsonrpc_error_code = int(payload.get("jsonrpc_error_code", -32022))
    jsonrpc_error_data = payload.get("jsonrpc_error_data")
    raw_mcp_name = str(payload.get("raw_mcp_name", "工具/search"))
    wire_mcp_name = str(payload.get("wire_mcp_name", ""))

    if reconnect_resumed_event_id != standalone_get_last_event_id or reconnect_resumed_event_id == post_sse_event_id:
        return {
            "allow": False,
            "decision_code": "MCP_SWIFT_SSE_POST_OVERWROTE_GET_RESUME_ID_BLOCKED",
            "reason": "Standalone GET SSE reconnect must resume from the GET stream's event ID, never a POST SSE response event ID.",
        }

    if data_url_input.startswith("data:") and decoded_value_kind != "string":
        return {
            "allow": False,
            "decision_code": "MCP_SWIFT_DATA_URL_COERCED_TO_BINARY_BLOCKED",
            "reason": "JSON strings starting with 'data:' must remain Value.string rather than decoding as binary Value.data.",
        }

    if jsonrpc_error_code in (-32021, -32022) and not isinstance(jsonrpc_error_data, Mapping):
        return {
            "allow": False,
            "decision_code": "MCP_SWIFT_STRUCTURED_ERROR_DATA_DROPPED_BLOCKED",
            "reason": "Structured JSON-RPC server error.data must be preserved for -32022 (supported versions) and -32021 (required capabilities).",
        }

    needs_b64 = (
        not raw_mcp_name.isascii()
        or any(ord(ch) <= 0x20 or ord(ch) >= 0x7F for ch in raw_mcp_name)
        or raw_mcp_name.startswith("=?")
    )
    if needs_b64:
        expected_wire = f"=?UTF-8?B?{base64.b64encode(raw_mcp_name.encode('utf-8')).decode('ascii')}?="
    else:
        expected_wire = raw_mcp_name

    if wire_mcp_name != expected_wire:
        return {
            "allow": False,
            "decision_code": "MCP_SWIFT_MCP_NAME_ENCODING_MISMATCH_BLOCKED",
            "reason": "Non-ASCII, whitespace, or '=?' prefixed Mcp-Name values must use SEP-2243 '=?UTF-8?B?<base64>?=' encoding.",
        }

    return {
        "allow": True,
        "decision_code": "MCP_SWIFT_SSE_DATAURL_ERRORDATA_AND_MCP_NAME_VERIFIED",
        "wire_mcp_name": wire_mcp_name,
    }


# ---------------------------------------------------------------------------
# PR-16: modelcontextprotocol/swift-sdk#297, #292, #290, & #289
# ---------------------------------------------------------------------------
def evaluate_mcp_swift_stdio_flags_raw_response_cache_and_capabilities_guard(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate stdio O_NONBLOCK restoration on disconnect, raw response retention on decode error, CacheableResult, and server capabilities."""
    initial_fd_flags = int(payload.get("initial_fd_flags", 0x0002))
    post_disconnect_fd_flags = int(payload.get("post_disconnect_fd_flags", 0x0002))
    decode_failed = bool(payload.get("decode_failed", True))
    retained_raw_response = payload.get("retained_raw_response")
    ttl_ms = payload.get("ttl_ms", 30000)
    cache_scope = str(payload.get("cache_scope", "session"))
    server_capabilities = dict(payload.get("server_capabilities", {}))

    if post_disconnect_fd_flags != initial_fd_flags:
        return {
            "allow": False,
            "decision_code": "MCP_SWIFT_STDIO_FD_FLAGS_NOT_RESTORED_BLOCKED",
            "reason": "StdioTransport must restore original file descriptor flags (clearing O_NONBLOCK) on disconnect.",
        }

    if decode_failed and not isinstance(retained_raw_response, Mapping):
        return {
            "allow": False,
            "decision_code": "MCP_SWIFT_DECODE_ERROR_RAW_RESPONSE_DROPPED_BLOCKED",
            "reason": "When pending result decoding fails, the thrown error must retain the raw JSON-RPC Response.",
        }

    if (
        isinstance(ttl_ms, bool)
        or not isinstance(ttl_ms, int)
        or ttl_ms < 0
        or cache_scope not in {"public", "private", "session"}
    ):
        return {
            "allow": False,
            "decision_code": "MCP_SWIFT_CACHEABLE_RESULT_INVALID_BLOCKED",
            "reason": "List and resource read results require non-negative integer ttlMs and valid cacheScope.",
        }

    if not isinstance(server_capabilities.get("experimental"), Mapping) or not isinstance(
        server_capabilities.get("extensions"), Mapping
    ):
        return {
            "allow": False,
            "decision_code": "MCP_SWIFT_SERVER_CAPABILITIES_MISSING_EXTENSIONS_BLOCKED",
            "reason": "Server.Capabilities must preserve both experimental and extensions capability maps.",
        }

    return {
        "allow": True,
        "decision_code": "MCP_SWIFT_STDIO_FLAGS_RAW_RESPONSE_CACHE_AND_CAPABILITIES_VERIFIED",
        "ttl_ms": ttl_ms,
        "cache_scope": cache_scope,
    }
