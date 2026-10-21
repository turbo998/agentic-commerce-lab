"""Stage 152 deterministic runtime guards (UN-01..UN-16).

Covers newly audited upstream PRs and specification issues across:
- x402-foundation/x402 (#3437, #3448, #3401, #3441, #3436, #3432, #3443, #3442,
  #3430, #3431, #3427, #3369, #3368, #3363, #3362, #3423)
- Universal-Commerce-Protocol/ucp (#960, #959, #958, #954, #953, #905, #952,
  #904, #872, #896, #877, #865, #659, #657, #655, #653)
- agentic-commerce-protocol/agentic-commerce-protocol (#282, #242, #153, #141,
  #231, #165, #162, #160)
- google-agentic-commerce/AP2 (#375, #338, #224, #298, #268, #211)
- modelcontextprotocol/modelcontextprotocol (#3437, #3435, #3434, #3394)
- stripe/ai & stripe/agent-toolkit (#375, #464, #480, #453)
- visa/trusted-agent-protocol (#26, #23, #16, #8)
- sierra-research/tau2-bench (#663, #599, #587, #574)
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
import hashlib
import json
import re
from typing import Any, Mapping, Sequence
from urllib.parse import unquote

CAIP2_NAMESPACE_RE = re.compile(r"^[-a-z0-9]{3,8}$")
CAIP2_REFERENCE_RE = re.compile(r"^[-_a-zA-Z0-9]{1,32}$")
VALID_BOARD_TYPES = frozenset(
    {"room_only", "breakfast", "half_board", "full_board", "all_inclusive"}
)
VALID_ADDON_CATEGORIES = frozenset({"extra", "insurance", "flexibility"})
ACP_ORDER_PROGRESSION = {
    "created": 0,
    "confirmed": 1,
    "shipped": 2,
    "delivered": 3,
    "fulfilled": 4,
}


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    decision_code: str
    reason: str
    evidence: Mapping[str, Any] = field(default_factory=dict)


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _b64u_sha256_ascii(text: str) -> str:
    digest = hashlib.sha256(text.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


# ---------------------------------------------------------------------------
# UN-01: x402 #3437 / #3448 / #3401 — Unresolved Settlement Receiver Obligation
# & Pact-Escrow Verification-Gated Release
# ---------------------------------------------------------------------------
def evaluate_x402_unresolved_settlement_and_pact_escrow_guard(
    *,
    settlement_state: str,
    receiver_issued_new_402_challenge: bool,
    receiver_reported_payment_failed: bool,
    receiver_represented_existing_authorization: bool,
    requested_new_payer_signature: bool,
    is_pact_escrow_auth_capture: bool,
    delivery_verification_attested: bool,
    toctou_lock_acquired: bool,
) -> GuardDecision:
    """Enforce x402 §5.3.5 receiver obligation on unresolved settlement (#3437)
    and verification-gated capture release for pact-escrow auth-capture (#3448/#3401)."""
    if settlement_state == "unresolved":
        if receiver_issued_new_402_challenge:
            return GuardDecision(
                False,
                "X402_UNRESOLVED_SETTLEMENT_RECHALLENGE_FORBIDDEN",
                "Receiver must not issue a new 402 challenge while authorization settlement is unresolved (#3437).",
                {"settlement_state": settlement_state},
            )
        if receiver_reported_payment_failed:
            return GuardDecision(
                False,
                "X402_UNRESOLVED_SETTLEMENT_FALSE_FAILURE_REPORT",
                "Receiver must not present an unresolved settlement as a failed payment (#3437).",
                {"settlement_state": settlement_state},
            )
        if requested_new_payer_signature or not receiver_represented_existing_authorization:
            return GuardDecision(
                False,
                "X402_UNRESOLVED_SETTLEMENT_MUST_REPRESENT_EXISTING_AUTH",
                "Receiver must re-present the existing authorization rather than ask the payer to sign a new one (#3437).",
                {
                    "requested_new_payer_signature": requested_new_payer_signature,
                    "receiver_represented_existing_authorization": receiver_represented_existing_authorization,
                },
            )
    if is_pact_escrow_auth_capture:
        if not toctou_lock_acquired:
            return GuardDecision(
                False,
                "X402_PACT_ESCROW_TOCTOU_LOCK_MISSING",
                "Server-side TOCTOU replay-protection lock is required before auth-capture release (#3401).",
                {"toctou_lock_acquired": toctou_lock_acquired},
            )
        if not delivery_verification_attested:
            return GuardDecision(
                False,
                "X402_PACT_ESCROW_VERIFICATION_GATE_UNSATISFIED",
                "Pact-escrow auth-capture release requires verified delivery attestation (#3448).",
                {"delivery_verification_attested": delivery_verification_attested},
            )
    return GuardDecision(
        True,
        "X402_UNRESOLVED_AND_PACT_ESCROW_VERIFIED",
        "Unresolved settlement receiver obligations and pact-escrow verification gate satisfied.",
        {
            "settlement_state": settlement_state,
            "is_pact_escrow_auth_capture": is_pact_escrow_auth_capture,
        },
    )


# ---------------------------------------------------------------------------
# UN-02: x402 #3441 / #3436 / #3432 — Fixed-Point routeTemplate Unescape &
# CAIP-2 Reference Grammar (No Dots)
# ---------------------------------------------------------------------------
def evaluate_x402_route_template_fixed_point_and_caip2_guard(
    *,
    route_template: str,
    caip2_network: str,
    max_unescape_passes: int = 5,
) -> GuardDecision:
    """Decode routeTemplate up to a fixed point (max 5 passes) before checking for
    traversal/scheme injection (#3441), and enforce CAIP-2 grammar without dots (#3436)."""
    if not route_template or not route_template.startswith("/"):
        return GuardDecision(
            False,
            "X402_ROUTE_TEMPLATE_INVALID_ROOT",
            "routeTemplate must be a non-empty relative path starting with '/' (#3441).",
            {"route_template": route_template},
        )
    current = route_template
    converged = False
    for _ in range(max_unescape_passes):
        decoded = unquote(current)
        if ".." in decoded or "://" in decoded or "\\" in decoded:
            return GuardDecision(
                False,
                "X402_ROUTE_TEMPLATE_FIXED_POINT_TRAVERSAL_BLOCKED",
                "Fixed-point percent-decoding detected path traversal ('..') or scheme injection ('://') (#3441).",
                {"raw": route_template, "decoded": decoded},
            )
        if decoded == current:
            converged = True
            break
        current = decoded

    if not converged and unquote(current) != current:
        return GuardDecision(
            False,
            "X402_ROUTE_TEMPLATE_EXCESSIVE_ENCODING_DEPTH",
            "routeTemplate did not converge within 5 percent-unescape passes (#3441).",
            {"raw": route_template, "max_unescape_passes": max_unescape_passes},
        )

    if ":" not in caip2_network or caip2_network.count(":") != 1:
        return GuardDecision(
            False,
            "X402_CAIP2_MALFORMED_IDENTIFIER",
            "CAIP-2 network identifier must contain exactly one ':' separator (#3436).",
            {"caip2_network": caip2_network},
        )
    namespace, reference = caip2_network.split(":", 1)
    if not CAIP2_NAMESPACE_RE.match(namespace):
        return GuardDecision(
            False,
            "X402_CAIP2_NAMESPACE_INVALID",
            "CAIP-2 namespace must match [-a-z0-9]{3,8} (#3436).",
            {"namespace": namespace},
        )
    if "." in reference or not CAIP2_REFERENCE_RE.match(reference):
        return GuardDecision(
            False,
            "X402_CAIP2_REFERENCE_DOT_OR_CHAR_FORBIDDEN",
            "CAIP-2 reference must match [-_a-zA-Z0-9]{1,32}; dots ('.') are forbidden (#3436).",
            {"reference": reference, "caip2_network": caip2_network},
        )

    return GuardDecision(
        True,
        "X402_ROUTE_TEMPLATE_AND_CAIP2_VALID",
        "routeTemplate converged without traversal and CAIP-2 network reference grammar is valid.",
        {"decoded_route": current, "caip2_network": caip2_network},
    )


# ---------------------------------------------------------------------------
# UN-03: x402 #3443 / #3442 / #3430 / #3431 / #3427 — MCP Timeout Sizing from
# accept.maxTimeoutSeconds, SVM Delegated-Auth Store Error Split & Lock Split
# ---------------------------------------------------------------------------
def evaluate_x402_mcp_timeout_and_svm_delegated_store_guard(
    *,
    accept_max_timeout_seconds: int | None,
    effective_mcp_tool_timeout_seconds: int,
    caller_read_timeout_seconds: int | None,
    initial_402_probe_timeout_seconds: int,
    svm_delegated_store_read_ok: bool,
    svm_identity_authenticated: bool,
    reported_svm_error_code: str | None,
    svm_tx_broadcasted: bool,
    channel_lock_storage_isolated: bool,
) -> GuardDecision:
    """Size MCP paid tool-call timeouts from accept.maxTimeoutSeconds (#3443/#3442/#3430),
    separate SVM upto delegated-auth store errors from unauthenticated (#3431),
    and require isolated ChannelLockStorage (#3427)."""
    expected_tool_timeout = (
        accept_max_timeout_seconds
        if accept_max_timeout_seconds is not None and accept_max_timeout_seconds > 0
        else 300
    )
    if effective_mcp_tool_timeout_seconds < expected_tool_timeout:
        return GuardDecision(
            False,
            "X402_MCP_TOOL_TIMEOUT_UNDERSIZED",
            "Paid MCP tool-call timeout must be sized from accept.maxTimeoutSeconds (default 300s), not 60s SDK default (#3443/#3442/#3430).",
            {
                "effective_mcp_tool_timeout_seconds": effective_mcp_tool_timeout_seconds,
                "expected_tool_timeout": expected_tool_timeout,
            },
        )
    expected_probe_timeout = (
        caller_read_timeout_seconds
        if caller_read_timeout_seconds is not None and caller_read_timeout_seconds > 0
        else 300
    )
    if initial_402_probe_timeout_seconds != expected_probe_timeout:
        return GuardDecision(
            False,
            "X402_MCP_INITIAL_PROBE_TIMEOUT_MISMATCH",
            "Initial 402 MCP probe must use caller read_timeout_seconds or a 300s ceiling (#3443).",
            {
                "initial_402_probe_timeout_seconds": initial_402_probe_timeout_seconds,
                "expected_probe_timeout": expected_probe_timeout,
            },
        )
    if not channel_lock_storage_isolated:
        return GuardDecision(
            False,
            "X402_BATCH_CHANNEL_LOCK_STORAGE_NOT_ISOLATED",
            "Batch-settlement admission locks must be isolated in ChannelLockStorage (#3427/#3412).",
            {"channel_lock_storage_isolated": channel_lock_storage_isolated},
        )
    if not svm_delegated_store_read_ok:
        if svm_tx_broadcasted or reported_svm_error_code != "invalid_upto_svm_delegated_auth_store":
            return GuardDecision(
                False,
                "X402_SVM_DELEGATED_STORE_ERROR_COLLAPSED",
                "DelegatedAuthStore failure must return 'invalid_upto_svm_delegated_auth_store' without broadcasting, not collapse into unauthenticated (#3431).",
                {
                    "reported_svm_error_code": reported_svm_error_code,
                    "svm_tx_broadcasted": svm_tx_broadcasted,
                },
            )
    elif not svm_identity_authenticated:
        if svm_tx_broadcasted or reported_svm_error_code != "invalid_upto_svm_delegated_settle_unauthenticated":
            return GuardDecision(
                False,
                "X402_SVM_DELEGATED_IDENTITY_ERROR_MISMATCH",
                "Identity-only failure must return 'invalid_upto_svm_delegated_settle_unauthenticated' without broadcasting (#3431).",
                {"reported_svm_error_code": reported_svm_error_code},
            )

    return GuardDecision(
        True,
        "X402_MCP_TIMEOUT_AND_SVM_STORE_GUARD_VALID",
        "MCP tool timeout sizing, ChannelLockStorage split, and SVM delegated-auth error taxonomy verified.",
        {"effective_mcp_tool_timeout_seconds": effective_mcp_tool_timeout_seconds},
    )


# ---------------------------------------------------------------------------
# UN-04: x402 #3369 / #3368 / #3363 / #3362 / #3423 — Bounded HTTP Response Body
# Reads, Positive-Only Awaited EVM Asset Cache & Stellar areFeesSponsored Guard
# ---------------------------------------------------------------------------
def evaluate_x402_bounded_body_evm_cache_and_stellar_guard(
    *,
    response_kind: str,
    response_body_bytes: int,
    stream_enabled: bool,
    evm_getcode_positive: bool,
    evm_check_awaited: bool,
    evm_cached_entry_written: bool,
    evm_cache_ttl_seconds: int,
    stellar_are_fees_sponsored: bool,
) -> GuardDecision:
    """Enforce 1 MiB control-plane / 4 MiB discovery response body caps with stream=True (#3369/#3368),
    positive-only awaited 15-minute EVM eth_getCode caching (#3363/#3362), and Stellar
    areFeesSponsored=True constructor invariant (#3423/#3339)."""
    if not stream_enabled:
        return GuardDecision(
            False,
            "X402_HTTP_STREAMING_READ_REQUIRED",
            "HTTP 402 and discovery reads must use streaming mode so oversized bodies abort before full buffering (#3369/#3368).",
            {"stream_enabled": stream_enabled},
        )
    if response_kind == "control_plane_402" and response_body_bytes > 1_048_576:
        return GuardDecision(
            False,
            "X402_CONTROL_PLANE_RESPONSE_BODY_TOO_LARGE",
            "Control-plane 402 JSON response exceeds 1 MiB cap (ResponseBodyTooLargeError) (#3369/#3368).",
            {"response_body_bytes": response_body_bytes, "cap_bytes": 1_048_576},
        )
    if response_kind == "discovery_catalog" and response_body_bytes > 4_194_304:
        return GuardDecision(
            False,
            "X402_DISCOVERY_CATALOG_RESPONSE_BODY_TOO_LARGE",
            "Bazaar discovery catalog page exceeds 4 MiB cap (ResponseBodyTooLargeError) (#3369/#3368).",
            {"response_body_bytes": response_body_bytes, "cap_bytes": 4_194_304},
        )
    if evm_cached_entry_written:
        if not evm_getcode_positive or not evm_check_awaited or evm_cache_ttl_seconds > 900:
            return GuardDecision(
                False,
                "X402_EVM_ASSET_CACHE_POISON_OR_UNBOUNDED",
                "EVM asset-contract cache may only record awaited positive eth_getCode results with TTL <= 900s (15m) (#3363/#3362).",
                {
                    "evm_getcode_positive": evm_getcode_positive,
                    "evm_check_awaited": evm_check_awaited,
                    "evm_cache_ttl_seconds": evm_cache_ttl_seconds,
                },
            )
    if not stellar_are_fees_sponsored:
        return GuardDecision(
            False,
            "X402_STELLAR_UNSPONSORED_FEES_REJECTED",
            "Stellar scheme constructor must reject areFeesSponsored=False at construction time (#3423/#3339).",
            {"stellar_are_fees_sponsored": stellar_are_fees_sponsored},
        )
    return GuardDecision(
        True,
        "X402_BOUNDED_BODY_EVM_CACHE_STELLAR_VALID",
        "Streaming body caps, positive-only awaited EVM asset cache, and Stellar fee sponsorship verified.",
        {"response_kind": response_kind, "response_body_bytes": response_body_bytes},
    )


# ---------------------------------------------------------------------------
# UN-05: UCP #960 / #959 / #958 / #954 / #953 — Lodging Add-Ons, Structured
# Board/Meal Plan & Machine-Readable Booker Eligibility
# ---------------------------------------------------------------------------
def evaluate_ucp_lodging_addons_board_and_booker_eligibility_guard(
    *,
    board_plan_type: str,
    selected_addons: Sequence[Mapping[str, Any]],
    room_subtotal_minor: int,
    declared_addons_total_minor: int,
    declared_grand_total_minor: int,
    required_min_age_years: int,
    booker_age_on_checkin_years: int | None,
    required_booker_fields: Sequence[str],
    provided_booker_fields: Mapping[str, Any],
) -> GuardDecision:
    """Validate UCP lodging add-ons pricing into totals[] (#960), structured board
    plan enum (#958), and machine-readable booker minimum age + identity fields (#954/#953)."""
    if board_plan_type not in VALID_BOARD_TYPES:
        return GuardDecision(
            False,
            "UCP_LODGING_BOARD_PLAN_INVALID",
            "Lodging rate plan board_type must be a canonical structured board enum (#958).",
            {"board_plan_type": board_plan_type},
        )
    computed_addons_minor = 0
    for addon in selected_addons:
        cat = str(addon.get("category", ""))
        price = addon.get("price_minor")
        if cat not in VALID_ADDON_CATEGORIES or not isinstance(price, int) or price < 0:
            return GuardDecision(
                False,
                "UCP_LODGING_ADDON_SCHEMA_INVALID",
                "Selected lodging add-on must declare category in {extra, insurance, flexibility} and non-negative integer price_minor (#960).",
                {"addon": dict(addon)},
            )
        computed_addons_minor += price
    if (
        computed_addons_minor != declared_addons_total_minor
        or room_subtotal_minor + computed_addons_minor != declared_grand_total_minor
    ):
        return GuardDecision(
            False,
            "UCP_LODGING_ADDON_TOTALS_MISMATCH",
            "Selected lodging add-ons must sum exactly into totals[] and grand total (#960).",
            {
                "computed_addons_minor": computed_addons_minor,
                "declared_addons_total_minor": declared_addons_total_minor,
                "declared_grand_total_minor": declared_grand_total_minor,
            },
        )
    for req_field in required_booker_fields:
        val = provided_booker_fields.get(req_field)
        if val is None or (isinstance(val, str) and not val.strip()):
            return GuardDecision(
                False,
                "UCP_LODGING_BOOKER_REQUIRED_FIELD_MISSING",
                f"Booker is missing business-declared required identity field '{req_field}' (#954/#953).",
                {"missing_field": req_field},
            )
    if booker_age_on_checkin_years is None or booker_age_on_checkin_years < required_min_age_years:
        return GuardDecision(
            False,
            "UCP_LODGING_BOOKER_UNDER_MINIMUM_AGE",
            "Booker does not meet the business-declared minimum legal age on check-in date (#954).",
            {
                "booker_age_on_checkin_years": booker_age_on_checkin_years,
                "required_min_age_years": required_min_age_years,
            },
        )
    return GuardDecision(
        True,
        "UCP_LODGING_ADDONS_BOARD_AND_BOOKER_VALID",
        "Lodging add-ons, board plan, and booker age/identity eligibility verified.",
        {
            "board_plan_type": board_plan_type,
            "computed_addons_minor": computed_addons_minor,
        },
    )


# ---------------------------------------------------------------------------
# UN-06: UCP #905 / #952 / #904 / #872 — Computable Checkout JWT Binding,
# Pre-Checkout Precheck Procedure & 304 Not Modified Exemption
# ---------------------------------------------------------------------------
def evaluate_ucp_checkout_jwt_and_precheck_guard(
    *,
    checkout_jwt: str,
    checkout_mandate_checkout_hash: str,
    payment_mandate_transaction_id: str,
    profile_scheme: str,
    profile_status_code: int,
    profile_content_type: str,
    has_cached_etag: bool,
    supported_versions_intersect: bool,
    payment_handlers_intersect: bool,
) -> GuardDecision:
    """Verify computable UCP checkout_jwt hash binding (#905), pre-checkout /.well-known/ucp
    precheck (#952/#904), and 304 Not Modified conditional cache exemption (#872/#933)."""
    if profile_scheme != "https":
        return GuardDecision(
            False,
            "UCP_PRECHECK_HTTPS_REQUIRED",
            "UCP profile precheck requires HTTPS transport (#952).",
            {"profile_scheme": profile_scheme},
        )
    if profile_status_code == 304:
        if not has_cached_etag:
            return GuardDecision(
                False,
                "UCP_PRECHECK_UNSOLICITED_304",
                "304 Not Modified is only valid when conditional If-None-Match ETag is present (#872/#933).",
                {"profile_status_code": profile_status_code},
            )
    elif 300 <= profile_status_code < 400:
        return GuardDecision(
            False,
            "UCP_PRECHECK_REDIRECT_FORBIDDEN",
            "UCP profile hosting MUST NOT use 3xx redirects (other than conditional 304 Not Modified) (#872/#952).",
            {"profile_status_code": profile_status_code},
        )
    elif profile_status_code != 200:
        return GuardDecision(
            False,
            "UCP_PRECHECK_HTTP_STATUS_INVALID",
            "UCP profile fetch must return 200 OK or conditional 304 Not Modified (#952).",
            {"profile_status_code": profile_status_code},
        )

    if profile_status_code == 200 and not profile_content_type.lower().startswith("application/json"):
        return GuardDecision(
            False,
            "UCP_PRECHECK_NON_JSON_CONTENT_TYPE",
            "UCP profile endpoint must serve application/json (#904/#952).",
            {"profile_content_type": profile_content_type},
        )
    if not supported_versions_intersect or not payment_handlers_intersect:
        return GuardDecision(
            False,
            "UCP_PRECHECK_CAPABILITY_OR_HANDLER_DISJOINT",
            "Pre-checkout precheck failed: no overlapping UCP version or compatible payment handler (#952).",
            {
                "supported_versions_intersect": supported_versions_intersect,
                "payment_handlers_intersect": payment_handlers_intersect,
            },
        )
    if checkout_jwt.count(".") != 2 or not all(checkout_jwt.split(".")):
        return GuardDecision(
            False,
            "UCP_CHECKOUT_JWT_COMPACT_JWS_REQUIRED",
            "UCP checkout_jwt must be a 3-segment compact JWS so AP2 binding is computable (#905).",
            {"checkout_jwt": checkout_jwt},
        )
    expected_hash = _b64u_sha256_ascii(checkout_jwt)
    if (
        checkout_mandate_checkout_hash != expected_hash
        or payment_mandate_transaction_id != expected_hash
    ):
        return GuardDecision(
            False,
            "UCP_CHECKOUT_JWT_AP2_HASH_MISMATCH",
            "checkout_hash and payment_mandate.transaction_id must equal B64U(SHA-256(ASCII(checkout_jwt))) (#905).",
            {
                "expected_hash": expected_hash,
                "checkout_mandate_checkout_hash": checkout_mandate_checkout_hash,
                "payment_mandate_transaction_id": payment_mandate_transaction_id,
            },
        )
    return GuardDecision(
        True,
        "UCP_CHECKOUT_JWT_AND_PRECHECK_VALID",
        "UCP precheck procedure, 304 semantics, and computable checkout_jwt AP2 binding verified.",
        {"computed_checkout_hash": expected_hash, "profile_status_code": profile_status_code},
    )


# ---------------------------------------------------------------------------
# UN-07: UCP #896 / #877 / #865 — Buyer-Approved Order Contingencies,
# Price-on-Request Quote Gate & Order Event Webhook-to-MCP Parity
# ---------------------------------------------------------------------------
def evaluate_ucp_contingencies_price_on_request_and_mcp_event_guard(
    *,
    allow_item_substitution: bool,
    substitution_occurred: bool,
    max_capture_overage_bps: int,
    quoted_total_minor: int,
    capture_total_minor: int,
    max_delivery_delay_days: int,
    actual_delivery_delay_days: int,
    max_split_shipments: int,
    actual_split_shipments: int,
    item_is_price_on_request: bool,
    has_bound_custom_quote: bool,
    transport_type: str,
    order_event_emitted: bool,
    mcp_order_notification_delivered: bool,
) -> GuardDecision:
    """Enforce buyer-approved contingencies (#896), price_on_request quote gate (#877),
    and Order Event Webhook-to-MCP notification parity (#865)."""
    if item_is_price_on_request and not has_bound_custom_quote:
        return GuardDecision(
            False,
            "UCP_PRICE_ON_REQUEST_REQUIRES_BOUND_QUOTE",
            "Catalog items with price_on_request cannot enter direct checkout without a bound quote (#877/#930).",
            {"item_is_price_on_request": item_is_price_on_request},
        )
    if substitution_occurred and not allow_item_substitution:
        return GuardDecision(
            False,
            "UCP_CONTINGENCY_SUBSTITUTION_NOT_APPROVED",
            "Item substitution occurred but buyer contingencies forbid substitution (#896).",
            {"allow_item_substitution": allow_item_substitution},
        )
    max_allowed_capture = quoted_total_minor + (quoted_total_minor * max_capture_overage_bps) // 10_000
    if capture_total_minor > max_allowed_capture:
        return GuardDecision(
            False,
            "UCP_CONTINGENCY_CAPTURE_OVERAGE_EXCEEDED",
            "Capture amount exceeds buyer-approved contingency tolerance ceiling (#896).",
            {
                "capture_total_minor": capture_total_minor,
                "max_allowed_capture": max_allowed_capture,
            },
        )
    if actual_delivery_delay_days > max_delivery_delay_days:
        return GuardDecision(
            False,
            "UCP_CONTINGENCY_DELIVERY_DELAY_EXCEEDED",
            "Delivery delay exceeds buyer-approved contingency window (#896).",
            {
                "actual_delivery_delay_days": actual_delivery_delay_days,
                "max_delivery_delay_days": max_delivery_delay_days,
            },
        )
    if actual_split_shipments > max_split_shipments:
        return GuardDecision(
            False,
            "UCP_CONTINGENCY_SPLIT_SHIPMENT_CAP_EXCEEDED",
            "Split shipment box count exceeds buyer-approved contingency cap (#896).",
            {
                "actual_split_shipments": actual_split_shipments,
                "max_split_shipments": max_split_shipments,
            },
        )
    if transport_type == "mcp" and order_event_emitted and not mcp_order_notification_delivered:
        return GuardDecision(
            False,
            "UCP_MCP_ORDER_EVENT_PARITY_MISSING",
            "MCP transport must deliver an order event notification equivalent to the REST Order Event Webhook (#865).",
            {"transport_type": transport_type, "order_event_emitted": order_event_emitted},
        )
    return GuardDecision(
        True,
        "UCP_CONTINGENCIES_QUOTE_AND_MCP_PARITY_VALID",
        "Buyer contingencies, price-on-request quote gate, and MCP order event parity verified.",
        {"max_allowed_capture": max_allowed_capture},
    )


# ---------------------------------------------------------------------------
# UN-08: UCP #659 / #657 / #655 / #653 — Webhook Signing Gate (webhook-id +
# webhook-timestamp), Reserved ucp Namespace, request_constraints & Sale-Basis Steps
# ---------------------------------------------------------------------------
def evaluate_ucp_webhook_signing_namespace_and_sale_basis_guard(
    *,
    signed_webhook_headers: Sequence[str],
    webhook_id: str,
    webhook_timestamp: int,
    now_epoch_seconds: int,
    extension_namespace: str,
    is_core_ucp_spec_artifact: bool,
    requested_quantity: int,
    min_quantity: int,
    step_quantity: int,
    response_required_constraints: Sequence[str],
    request_supplied_fields: Sequence[str],
) -> GuardDecision:
    """Enforce UCP order webhook signing over webhook-id and webhook-timestamp (#659),
    reserved 'ucp' namespace (#657), response-carried request_constraints (#655),
    and sale-basis quantity steps (#653)."""
    lowered_headers = {h.lower() for h in signed_webhook_headers}
    if "webhook-id" not in lowered_headers or "webhook-timestamp" not in lowered_headers:
        return GuardDecision(
            False,
            "UCP_WEBHOOK_SIGNING_GATE_INCOMPLETE",
            "Order webhook signature must cover both 'webhook-id' and 'webhook-timestamp' headers (#659).",
            {"signed_webhook_headers": list(signed_webhook_headers)},
        )
    if not webhook_id.strip() or abs(now_epoch_seconds - webhook_timestamp) > 300:
        return GuardDecision(
            False,
            "UCP_WEBHOOK_ID_OR_TIMESTAMP_STALE",
            "Order webhook must carry a non-empty webhook-id and timestamp within 300s window (#659).",
            {"webhook_id": webhook_id, "webhook_timestamp": webhook_timestamp},
        )
    if (
        extension_namespace == "ucp" or extension_namespace.startswith("dev.ucp.")
    ) and not is_core_ucp_spec_artifact:
        return GuardDecision(
            False,
            "UCP_RESERVED_NAMESPACE_VIOLATION",
            "Third-party extensions must not claim the reserved 'ucp' / 'dev.ucp.*' protocol namespace (#657).",
            {"extension_namespace": extension_namespace},
        )
    if step_quantity <= 0 or min_quantity <= 0:
        return GuardDecision(
            False,
            "UCP_SALE_BASIS_STEP_CONFIG_INVALID",
            "Sale-basis min_quantity and step_quantity must be positive integers (#653).",
            {"min_quantity": min_quantity, "step_quantity": step_quantity},
        )
    if requested_quantity < min_quantity or (requested_quantity - min_quantity) % step_quantity != 0:
        return GuardDecision(
            False,
            "UCP_SALE_BASIS_QUANTITY_STEP_VIOLATION",
            "Requested quantity violates item sale-basis min_quantity or step_quantity increment (#653).",
            {
                "requested_quantity": requested_quantity,
                "min_quantity": min_quantity,
                "step_quantity": step_quantity,
            },
        )
    supplied_set = set(request_supplied_fields)
    missing = [f for f in response_required_constraints if f not in supplied_set]
    if missing:
        return GuardDecision(
            False,
            "UCP_RESPONSE_CARRIED_CONSTRAINTS_UNSATISFIED",
            "Follow-up request omitted fields mandated by response-carried request_constraints (#655).",
            {"missing_constraints": missing},
        )
    return GuardDecision(
        True,
        "UCP_WEBHOOK_NAMESPACE_AND_SALE_BASIS_VALID",
        "Webhook signing gate, reserved namespace, sale-basis steps, and request_constraints verified.",
        {"requested_quantity": requested_quantity, "step_quantity": step_quantity},
    )


# ---------------------------------------------------------------------------
# UN-09: ACP #282 / #242 / #153 / #141 — Push-Rail Mandate Payment Handler
# (Pix / A2A Push) & Appointment Scheduling Fulfillment Time-Slot Guard
# ---------------------------------------------------------------------------
def evaluate_acp_push_rail_and_appointment_scheduling_guard(
    *,
    payment_rail_type: str,
    end_to_end_id: str,
    receiver_pix_key: str,
    mandate_authorized_payee_key: str,
    push_settlement_proof_present: bool,
    contains_raw_card_pan: bool,
    fulfillment_type: str,
    appointment_slot_id: str,
    slot_starts_at_epoch: int,
    slot_ends_at_epoch: int,
    slot_hold_expires_at_epoch: int,
    now_epoch_seconds: int,
) -> GuardDecision:
    """Validate ACP mandate-delegated push-rail payment handler (Pix / A2A push) (#282/#153),
    Stripe Link handler isolation (#141), and appointment scheduling time-slot reservation (#242)."""
    if contains_raw_card_pan:
        return GuardDecision(
            False,
            "ACP_PUSH_RAIL_RAW_PAN_LEAK",
            "Push-rail or Link payment handlers must never carry raw card PANs (#282/#141).",
            {"payment_rail_type": payment_rail_type},
        )
    if payment_rail_type in {"pix_push", "a2a_push"}:
        if (
            not end_to_end_id.strip()
            or receiver_pix_key != mandate_authorized_payee_key
            or not push_settlement_proof_present
        ):
            return GuardDecision(
                False,
                "ACP_PUSH_RAIL_MANDATE_BINDING_INVALID",
                "Push-rail payment requires non-empty end_to_end_id, exact mandate payee key match, and push settlement proof (#282/#153).",
                {
                    "end_to_end_id": end_to_end_id,
                    "receiver_pix_key": receiver_pix_key,
                    "mandate_authorized_payee_key": mandate_authorized_payee_key,
                },
            )
    elif payment_rail_type not in {"stripe_link", "card_spt"}:
        return GuardDecision(
            False,
            "ACP_PAYMENT_RAIL_UNSUPPORTED",
            "Unsupported ACP payment handler rail type (#282/#141).",
            {"payment_rail_type": payment_rail_type},
        )

    if fulfillment_type == "appointment":
        if (
            not appointment_slot_id.strip()
            or slot_starts_at_epoch >= slot_ends_at_epoch
            or now_epoch_seconds > slot_hold_expires_at_epoch
        ):
            return GuardDecision(
                False,
                "ACP_APPOINTMENT_SLOT_INVALID_OR_EXPIRED",
                "Appointment fulfillment requires a valid slot_id, starts_at < ends_at, and active slot reservation hold (#242).",
                {
                    "appointment_slot_id": appointment_slot_id,
                    "slot_starts_at_epoch": slot_starts_at_epoch,
                    "slot_ends_at_epoch": slot_ends_at_epoch,
                    "slot_hold_expires_at_epoch": slot_hold_expires_at_epoch,
                },
            )
    return GuardDecision(
        True,
        "ACP_PUSH_RAIL_AND_APPOINTMENT_VALID",
        "ACP push-rail mandate handler and appointment time-slot fulfillment verified.",
        {"payment_rail_type": payment_rail_type, "appointment_slot_id": appointment_slot_id},
    )


# ---------------------------------------------------------------------------
# UN-10: ACP #231 / #165 / #162 / #160 — Governance-Layer Principal Attribution,
# Line-Item valid_until Offer Expiry & Monotonic Order Status Progression
# ---------------------------------------------------------------------------
def evaluate_acp_governance_binding_offer_expiry_and_order_status_guard(
    *,
    uses_static_shared_rak: bool,
    delegation_token_principal_id: str,
    delegation_max_amount_minor: int,
    checkout_amount_minor: int,
    line_item_valid_until_epoch: int,
    now_epoch_seconds: int,
    previous_order_status: str,
    next_order_status: str,
) -> GuardDecision:
    """Enforce ACP per-delegation principal attribution and spend limit over static
    Restricted API Keys (#231), line-item valid_until offer expiry (#165), and
    monotonic order status transitions (#162)."""
    if uses_static_shared_rak or not delegation_token_principal_id.strip():
        return GuardDecision(
            False,
            "ACP_STATIC_RAK_WITHOUT_DELEGATION_BINDING",
            "Agent checkout requires per-delegation principal attribution rather than static shared Restricted API Keys (#231).",
            {
                "uses_static_shared_rak": uses_static_shared_rak,
                "delegation_token_principal_id": delegation_token_principal_id,
            },
        )
    if checkout_amount_minor > delegation_max_amount_minor:
        return GuardDecision(
            False,
            "ACP_DELEGATION_SPEND_LIMIT_EXCEEDED",
            "Checkout total exceeds the per-delegation authorization ceiling (#231).",
            {
                "checkout_amount_minor": checkout_amount_minor,
                "delegation_max_amount_minor": delegation_max_amount_minor,
            },
        )
    if now_epoch_seconds > line_item_valid_until_epoch:
        return GuardDecision(
            False,
            "ACP_LINE_ITEM_OFFER_EXPIRED",
            "Line-item time-bound offer valid_until has expired prior to checkout completion (#165).",
            {
                "now_epoch_seconds": now_epoch_seconds,
                "line_item_valid_until_epoch": line_item_valid_until_epoch,
            },
        )
    if (
        previous_order_status not in ACP_ORDER_PROGRESSION
        or next_order_status not in ACP_ORDER_PROGRESSION
        or ACP_ORDER_PROGRESSION[next_order_status] < ACP_ORDER_PROGRESSION[previous_order_status]
    ):
        return GuardDecision(
            False,
            "ACP_ORDER_STATUS_REGRESSION_FORBIDDEN",
            "Order lifecycle transitions must progress monotonically (created -> confirmed -> shipped -> delivered -> fulfilled) (#162).",
            {
                "previous_order_status": previous_order_status,
                "next_order_status": next_order_status,
            },
        )
    return GuardDecision(
        True,
        "ACP_GOVERNANCE_OFFER_EXPIRY_AND_STATUS_VALID",
        "ACP governance delegation binding, line-item valid_until, and order status progression verified.",
        {"delegation_token_principal_id": delegation_token_principal_id},
    )


# ---------------------------------------------------------------------------
# UN-11: AP2 #375 / #338 / #224 — Register-Backed Merchant Identity, 7-Year
# Self-Contained Dispute Evidence Bundle & PactEscrow Proof-of-Delivery Gate
# ---------------------------------------------------------------------------
def evaluate_ap2_verified_merchant_and_dispute_archive_guard(
    *,
    merchant_registry_verified: bool,
    merchant_legal_status: str,
    matched_on_mutable_display_name_only: bool,
    merchant_registry_id: str,
    allowed_payee_registry_ids: Sequence[str],
    dispute_bundle_has_sd_jwt_and_disclosures: bool,
    dispute_bundle_has_pinned_issuer_jwks_snapshot: bool,
    dispute_bundle_has_timestamp_authority_proof: bool,
    retention_horizon_years: int,
    pact_escrow_pod_verified: bool,
) -> GuardDecision:
    """Enforce AP2 register-backed merchant identity (#375), 5-7 year self-contained
    dispute evidence archive with pinned historical JWKS (#338), and PactEscrow PoD (#224)."""
    if (
        matched_on_mutable_display_name_only
        or not merchant_registry_verified
        or merchant_legal_status != "active"
        or merchant_registry_id not in set(allowed_payee_registry_ids)
    ):
        return GuardDecision(
            False,
            "AP2_MERCHANT_REGISTRY_IDENTITY_UNVERIFIED",
            "Payee matching must verify active register-backed merchant identity rather than mutable display fields (#375).",
            {
                "merchant_registry_verified": merchant_registry_verified,
                "merchant_legal_status": merchant_legal_status,
                "matched_on_mutable_display_name_only": matched_on_mutable_display_name_only,
            },
        )
    if (
        not dispute_bundle_has_sd_jwt_and_disclosures
        or not dispute_bundle_has_pinned_issuer_jwks_snapshot
        or not dispute_bundle_has_timestamp_authority_proof
        or retention_horizon_years < 5
    ):
        return GuardDecision(
            False,
            "AP2_DISPUTE_EVIDENCE_ARCHIVE_INCOMPLETE",
            "Dispute evidence bundle must store SD-JWT + disclosures, pinned historical issuer JWKS snapshot, and timestamp proof for >= 5 years (#338).",
            {
                "dispute_bundle_has_pinned_issuer_jwks_snapshot": dispute_bundle_has_pinned_issuer_jwks_snapshot,
                "retention_horizon_years": retention_horizon_years,
            },
        )
    if not pact_escrow_pod_verified:
        return GuardDecision(
            False,
            "AP2_PACT_ESCROW_POD_MISSING",
            "On-chain PactEscrow settlement adapter requires cryptographic proof-of-delivery before funds release (#224).",
            {"pact_escrow_pod_verified": pact_escrow_pod_verified},
        )
    return GuardDecision(
        True,
        "AP2_MERCHANT_IDENTITY_AND_DISPUTE_ARCHIVE_VALID",
        "Register-backed merchant identity, self-contained 7-year dispute bundle, and PactEscrow PoD verified.",
        {"merchant_registry_id": merchant_registry_id, "retention_horizon_years": retention_horizon_years},
    )


# ---------------------------------------------------------------------------
# UN-12: AP2 #298 / #268 / #211 — Non-Empty acceptable_items & Exact Required
# Quantity, WBA Ed25519 + Entropy Checkout Hash & JCS Cart-to-Payment Binding
# ---------------------------------------------------------------------------
def evaluate_ap2_line_items_wildcard_and_wba_entropy_guard(
    *,
    revealed_acceptable_items: Sequence[str],
    selected_item_id: str,
    mandated_quantity: int,
    actual_checkout_quantity: int,
    checkout_jws_alg: str,
    checkout_nonce_entropy_bits: int,
    cart_mandate_payload: Mapping[str, Any],
    payment_mandate_cart_hash: str,
) -> GuardDecision:
    """Block empty acceptable_items wildcard and underfilled quantity (#298),
    allow WBA Ed25519 when checkout nonce entropy >= 128 bits (#268), and verify
    RFC 8785 JCS CartMandate-to-PaymentMandate hash binding (#211/#253)."""
    if not revealed_acceptable_items:
        return GuardDecision(
            False,
            "AP2_EMPTY_ACCEPTABLE_ITEMS_WILDCARD_FORBIDDEN",
            "Empty or undisclosed acceptable_items list must fail evaluation rather than act as a wildcard (#298).",
            {"revealed_acceptable_items": list(revealed_acceptable_items)},
        )
    if selected_item_id not in set(revealed_acceptable_items):
        return GuardDecision(
            False,
            "AP2_SELECTED_ITEM_NOT_IN_ACCEPTABLE_ITEMS",
            "Selected checkout item is not in the revealed acceptable_items allowlist (#298).",
            {"selected_item_id": selected_item_id},
        )
    if mandated_quantity <= 0 or actual_checkout_quantity != mandated_quantity:
        return GuardDecision(
            False,
            "AP2_REQUIRED_QUANTITY_UNDERFILLED_OR_MISMATCH",
            "Checkout line_items must satisfy the mandated required quantity exactly, not treat it as an underfillable cap (#298).",
            {
                "mandated_quantity": mandated_quantity,
                "actual_checkout_quantity": actual_checkout_quantity,
            },
        )
    if checkout_jws_alg not in {"EdDSA", "ES256", "ES384", "ES512"} or checkout_nonce_entropy_bits < 128:
        return GuardDecision(
            False,
            "AP2_CHECKOUT_HASH_ENTROPY_OR_ALG_INVALID",
            "Checkout JWT must use an approved signature algorithm (including WBA EdDSA/Ed25519) with >= 128 bits of nonce entropy (#268).",
            {
                "checkout_jws_alg": checkout_jws_alg,
                "checkout_nonce_entropy_bits": checkout_nonce_entropy_bits,
            },
        )
    expected_cart_hash = hashlib.sha256(_canonical_json(cart_mandate_payload).encode("utf-8")).hexdigest()
    if payment_mandate_cart_hash != expected_cart_hash:
        return GuardDecision(
            False,
            "AP2_JCS_CART_TO_PAYMENT_MANDATE_MISMATCH",
            "PaymentMandate cart_hash must match RFC 8785 JCS SHA-256 digest of CartMandate (#211/#253).",
            {
                "expected_cart_hash": expected_cart_hash,
                "payment_mandate_cart_hash": payment_mandate_cart_hash,
            },
        )
    return GuardDecision(
        True,
        "AP2_LINE_ITEMS_WBA_ENTROPY_AND_JCS_VALID",
        "AP2 acceptable_items, exact required quantity, WBA Ed25519 entropy, and JCS cart binding verified.",
        {"expected_cart_hash": expected_cart_hash, "checkout_jws_alg": checkout_jws_alg},
    )


# ---------------------------------------------------------------------------
# UN-13: MCP #3437 / #3435 / #3434 / #3394 — Synchronous Pre-Dispatch Gate,
# Cross-Domain Authority Freshness, Mutating Retry Idempotency & Stdio OAuth SSRF
# ---------------------------------------------------------------------------
def evaluate_mcp_sync_dispatch_freshness_and_retry_guard(
    *,
    guardrail_evaluated_synchronously_before_dispatch: bool,
    concurrent_dispatch_overlap_detected: bool,
    token_cryptographically_valid: bool,
    upstream_delegation_revoked_in_trust_domain: bool,
    is_mutating_tool_call: bool,
    prior_response_lost_after_effect: bool,
    retry_uses_new_request_id_without_idempotency_key: bool,
    stdio_bridge_oauth_discovery_target_is_loopback_or_metadata_ip: bool,
) -> GuardDecision:
    """Enforce synchronous deterministic validation prior to tool dispatch (#3435),
    cross-domain delegated authority freshness at effect boundaries (#3434),
    mutating tools/call lost-response retry deduplication (#3394), and local
    stdio-to-HTTP OAuth discovery SSRF protection (#3437)."""
    if stdio_bridge_oauth_discovery_target_is_loopback_or_metadata_ip:
        return GuardDecision(
            False,
            "MCP_STDIO_BRIDGE_OAUTH_SSRF_BLOCKED",
            "Local stdio-to-HTTP MCP bridge must block OAuth discovery requests targeting private/loopback/cloud-metadata IPs (#3437).",
            {"ssrf_target_blocked": True},
        )
    if not guardrail_evaluated_synchronously_before_dispatch or concurrent_dispatch_overlap_detected:
        return GuardDecision(
            False,
            "MCP_CONCURRENT_TOOL_DISPATCH_OVERLAP_BLOCKED",
            "Deterministic guardrail validation must complete synchronously before tool dispatch with zero concurrent overlap (#3435).",
            {
                "guardrail_evaluated_synchronously_before_dispatch": guardrail_evaluated_synchronously_before_dispatch,
                "concurrent_dispatch_overlap_detected": concurrent_dispatch_overlap_detected,
            },
        )
    if not token_cryptographically_valid or upstream_delegation_revoked_in_trust_domain:
        return GuardDecision(
            False,
            "MCP_CROSS_DOMAIN_DELEGATED_AUTHORITY_STALE",
            "Effect boundary rejected call because upstream delegated authority was revoked or narrowed in its originating trust domain (#3434).",
            {"upstream_delegation_revoked_in_trust_domain": upstream_delegation_revoked_in_trust_domain},
        )
    if (
        is_mutating_tool_call
        and prior_response_lost_after_effect
        and retry_uses_new_request_id_without_idempotency_key
    ):
        return GuardDecision(
            False,
            "MCP_MUTATING_LOST_RESPONSE_DUPLICATE_EFFECT_BLOCKED",
            "Retrying a mutating tools/call after a lost response requires a deterministic idempotency key to prevent duplicate external effects (#3394).",
            {"is_mutating_tool_call": is_mutating_tool_call},
        )
    return GuardDecision(
        True,
        "MCP_SYNC_DISPATCH_FRESHNESS_AND_IDEMPOTENCY_VALID",
        "MCP synchronous pre-dispatch gate, cross-domain authority freshness, idempotent retry, and stdio SSRF guard verified.",
        {"is_mutating_tool_call": is_mutating_tool_call},
    )


# ---------------------------------------------------------------------------
# UN-14: Stripe AI / Agent Toolkit #375 / #464 / #480 / #453 — O(N+M) Order
# Summary Product Map, Dash/Dot Model ID MaxTokens & Per-Tool Scope Auth
# ---------------------------------------------------------------------------
def evaluate_stripe_order_summary_and_model_id_guard(
    *,
    uses_indexed_product_map: bool,
    cart_item_count: int,
    catalog_product_count: int,
    model_id: str,
    resolved_max_tokens: int | None,
    dxt_manifest_all_tools_have_descriptions: bool,
    agent_identity_bound_to_tool_scope: bool,
) -> GuardDecision:
    """Enforce O(N+M) indexed productMap lookup in populateOrderSummary (#375),
    dash-form and dot-form model ID maxTokens resolution (#464), DXT per-tool
    descriptions (#480), and per-tool agent identity authorization (#453)."""
    if not uses_indexed_product_map:
        return GuardDecision(
            False,
            "STRIPE_ORDER_SUMMARY_QUADRATIC_SCAN_BLOCKED",
            "populateOrderSummary must pre-index products into an O(1) map (O(N+M)) rather than running O(N*M) Array.find scans (#375).",
            {"cart_item_count": cart_item_count, "catalog_product_count": catalog_product_count},
        )
    normalized_model = model_id.replace(".", "-")
    if normalized_model.startswith("claude-opus-4-6") or normalized_model.startswith("claude-sonnet-4-6"):
        if resolved_max_tokens is None or resolved_max_tokens <= 0:
            return GuardDecision(
                False,
                "STRIPE_MODEL_ID_DOT_OR_DASH_MAX_TOKENS_MISSING",
                "getDefaultMaxTokens must resolve both dash-form and dot-form model IDs (#464).",
                {"model_id": model_id, "resolved_max_tokens": resolved_max_tokens},
            )
    if not dxt_manifest_all_tools_have_descriptions:
        return GuardDecision(
            False,
            "STRIPE_DXT_MANIFEST_TOOL_DESCRIPTION_MISSING",
            "Every MCP tool in the DXT manifest must include a non-empty description (#480).",
            {"dxt_manifest_all_tools_have_descriptions": dxt_manifest_all_tools_have_descriptions},
        )
    if not agent_identity_bound_to_tool_scope:
        return GuardDecision(
            False,
            "STRIPE_AGENT_IDENTITY_PER_TOOL_SCOPE_MISSING",
            "Agent execution must bind agent identity to per-tool authorization scopes (#453).",
            {"agent_identity_bound_to_tool_scope": agent_identity_bound_to_tool_scope},
        )
    return GuardDecision(
        True,
        "STRIPE_ORDER_SUMMARY_AND_MODEL_ID_VALID",
        "O(N+M) productMap lookup, dash/dot model ID maxTokens, DXT descriptions, and per-tool scope verified.",
        {"model_id": model_id, "normalized_model": normalized_model},
    )


# ---------------------------------------------------------------------------
# UN-15: Visa TAP #26 / #23 / #16 / #8 — Temporal Authority Revocation at
# Credential & Commit Boundary, Canonical Object Signature Base & Signed Receipt
# ---------------------------------------------------------------------------
def evaluate_visa_tap_temporal_authority_and_receipt_guard(
    *,
    agent_authorized_at_instruction_creation: bool,
    agent_revoked_before_credential_or_commit: bool,
    standing_reevaluated_at_commit_boundary: bool,
    object_signature_base_canonical_jcs: bool,
    body_object_signature_verified: bool,
    merchant_signed_transaction_receipt_present: bool,
    receipt_bound_to_request_signature_digest: bool,
) -> GuardDecision:
    """Enforce Visa TAP temporal authority re-evaluation at credential retrieval
    and commit boundaries (#26/#8), canonical deterministic object signature base
    for Consumer Recognition Object / Payment Container (#23), and merchant-signed
    post-authentication transaction receipt (#16)."""
    if (
        not agent_authorized_at_instruction_creation
        or not standing_reevaluated_at_commit_boundary
        or agent_revoked_before_credential_or_commit
    ):
        return GuardDecision(
            False,
            "VISA_TAP_TEMPORAL_AUTHORITY_REVOKED_AT_COMMIT",
            "Originating agent standing and mandate scope must be re-evaluated at credential retrieval and commit-time boundaries; revoked instructions cannot settle (#26/#8).",
            {
                "agent_revoked_before_credential_or_commit": agent_revoked_before_credential_or_commit,
                "standing_reevaluated_at_commit_boundary": standing_reevaluated_at_commit_boundary,
            },
        )
    if not object_signature_base_canonical_jcs or not body_object_signature_verified:
        return GuardDecision(
            False,
            "VISA_TAP_BODY_OBJECT_SIGNATURE_BASE_INVALID",
            "Consumer Recognition Object and Payment Container signatures must use deterministic canonical serialization (#23).",
            {
                "object_signature_base_canonical_jcs": object_signature_base_canonical_jcs,
                "body_object_signature_verified": body_object_signature_verified,
            },
        )
    if not merchant_signed_transaction_receipt_present or not receipt_bound_to_request_signature_digest:
        return GuardDecision(
            False,
            "VISA_TAP_POST_AUTH_SIGNED_RECEIPT_MISSING",
            "Regulated agentic commerce requires a merchant-signed transaction receipt bound to the verified RFC 9421 request signature digest (#16).",
            {
                "merchant_signed_transaction_receipt_present": merchant_signed_transaction_receipt_present,
                "receipt_bound_to_request_signature_digest": receipt_bound_to_request_signature_digest,
            },
        )
    return GuardDecision(
        True,
        "VISA_TAP_TEMPORAL_AUTHORITY_AND_RECEIPT_VALID",
        "Visa TAP temporal authority commit-boundary check, canonical object signature base, and signed receipt verified.",
        {"standing_reevaluated_at_commit_boundary": standing_reevaluated_at_commit_boundary},
    )


# ---------------------------------------------------------------------------
# UN-16: Sierra tau2-bench #663 / #599 / #587 / #574 — Referral Procedure
# Alignment, tasks.json Sync, Bubblewrap /dev/shm Sandbox & Oracle Leak Guard
# ---------------------------------------------------------------------------
def evaluate_tau2_referral_tasks_sync_and_sandbox_guard(
    *,
    undocumented_referral_transferred_to_human: bool,
    tasks_json_matches_per_task_files: bool,
    tmpdir_path: str,
    sandbox_kb_cwd_exists_and_isolated: bool,
    discoverable_read_log_filtered_by_reference_actions: bool,
) -> GuardDecision:
    """Enforce tau2-bench banking_knowledge doc_009 referral handling without
    unwarranted human transfer (#663), tasks.json vs tasks/task_*.json reward_basis
    sync (#599), /dev/shm TMPDIR sandbox escape prevention (#587), and suppression
    of reference-derived read_log_allowlist oracle leak (#574)."""
    if undocumented_referral_transferred_to_human:
        return GuardDecision(
            False,
            "TAU2_UNDOCUMENTED_REFERRAL_FALSE_TRANSFER",
            "Per internal procedure doc_009, undocumented credit-card referral claims must be declined in-flow rather than transferred to human agents (#663).",
            {"undocumented_referral_transferred_to_human": undocumented_referral_transferred_to_human},
        )
    if not tasks_json_matches_per_task_files:
        return GuardDecision(
            False,
            "TAU2_TASKS_JSON_REWARD_BASIS_DRIFT",
            "tasks.json must stay bit-for-bit synchronized with per-task tasks/task_*.json reward_basis definitions (#599).",
            {"tasks_json_matches_per_task_files": tasks_json_matches_per_task_files},
        )
    if tmpdir_path.startswith("/dev/shm") or not sandbox_kb_cwd_exists_and_isolated:
        return GuardDecision(
            False,
            "TAU2_SANDBOX_DEV_SHM_TMPDIR_ESCAPE",
            "Knowledge-base sandbox must not place TMPDIR under /dev/shm where bubblewrap mounts an empty tmpfs and falls back to HOME (#587).",
            {
                "tmpdir_path": tmpdir_path,
                "sandbox_kb_cwd_exists_and_isolated": sandbox_kb_cwd_exists_and_isolated,
            },
        )
    if discoverable_read_log_filtered_by_reference_actions:
        return GuardDecision(
            False,
            "TAU2_DISCOVERABLE_TOOLS_REFERENCE_ORACLE_LEAK",
            "list_discoverable_agent_tools must record all invoked discoverable tools uniformly rather than leaking reference action membership (#574).",
            {
                "discoverable_read_log_filtered_by_reference_actions": discoverable_read_log_filtered_by_reference_actions
            },
        )
    return GuardDecision(
        True,
        "TAU2_REFERRAL_SYNC_SANDBOX_AND_ORACLE_GUARD_VALID",
        "tau2-bench referral procedure, tasks.json sync, sandbox TMPDIR isolation, and discoverable tool logging verified.",
        {"tmpdir_path": tmpdir_path},
    )
