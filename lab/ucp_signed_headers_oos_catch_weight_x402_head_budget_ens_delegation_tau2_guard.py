"""Stage 204 deterministic security and protocol guardrails (`PR-01..PR-16`).

Covers 16 primary-source upstream Issues/PRs across UCP, x402, MCP, and tau2-bench:
- PR-01: Universal-Commerce-Protocol/ucp#794 — Checkout REST signed request `ucp-agent` / `signature-agent` / `idempotency-key` covered-component enforcement
- PR-02: Universal-Commerce-Protocol/ucp#641 — Out-of-session payment collection (`order.actions[]` `render_artifact` + per-instrument `collection_status`)
- PR-03: Universal-Commerce-Protocol/ucp#489 — Variable-yield / catch-weight tolerance & programmable authorization hold duration guard
- PR-04: Universal-Commerce-Protocol/ucp#668 + #649 — OpenAPI 3.1.0 `securitySchemes` vs ignored `Authorization` header & `update_checkout` `checkout.id` omit/readOnly guard
- PR-05: x402-foundation/x402#3810 + #3657 — `HEAD` request payment settlement prohibition & HTTP method payment eligibility contract
- PR-06: x402-foundation/x402#3803 — `PAYMENT-REQUIRED` base64 header size budget guard (Python aiohttp 8 KB / Node undici 16 KB limits)
- PR-07: x402-foundation/x402#3814 — Axios `responseType: "stream"` intermediate 402 body drain guard on bounded keep-alive pools
- PR-08: x402-foundation/x402#3747 — RFC 9111 quote-aware `Cache-Control: private` directive parser across TS/Go/Python
- PR-09: x402-foundation/x402#3755 — `payee-name` extension owner-signed ENS origin & multi-chain `payTo` binding guard
- PR-10: x402-foundation/x402#3693 — `ext-delegation` principal-signed JWS agent spend grant & facilitator scope guard
- PR-11: x402-foundation/x402#3792 + #3779 — Python async `BazaarExtension` `_get_async_client()` & non-200 facilitator `VerifyResponse`/`SettleResponse` body preservation
- PR-12: x402-foundation/x402#3650 + #3680 + #3811 — Go `OnAfterPaymentCreation` error propagation, `onPaymentResponse` HTTP status & Fastify `text/plain` body guard
- PR-13: x402-foundation/x402#3750 + #3660 — Per-call `PaymentPayloadContext.request` binding under concurrency & non-vacuous multi-rail amount law
- PR-14: modelcontextprotocol/modelcontextprotocol#3238 + #3226 — Dialect-agnostic `inputSchema` vs form-pinned `requestedSchema` & resource template `list_changed` guard
- PR-15: sierra-research/tau2-bench#654 + #477 — Content-addressed target DB hash cache invalidation & `user_scenario.persona` (`persoca` typo) schema guard
- PR-16: sierra-research/tau2-bench#154 + #474 + #430 — Concurrent `user_tools` deep-copy isolation, judge LLM preflight & banking numeric string coercion guard
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
import json
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    reason_code: str
    detail: str
    evidence: Mapping[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# PR-01: Universal-Commerce-Protocol/ucp#794
# ---------------------------------------------------------------------------
def audit_ucp_signed_request_covered_headers(
    *,
    present_headers: Mapping[str, str],
    signature_input_components: Sequence[str],
    has_body: bool = True,
) -> GuardDecision:
    """Enforce UCP Identity Resolution Step 5 covered-component requirements (#794)."""
    normalized_headers = {str(k).strip().lower(): str(v).strip() for k, v in present_headers.items() if str(v).strip()}
    covered = [str(c).strip().lower() for c in signature_input_components]
    covered_set = set(covered)

    required_base = ["@method", "@authority", "@path"]
    if has_body:
        required_base.extend(["content-digest", "content-type"])

    missing_base = [comp for comp in required_base if comp not in covered_set]
    mandatory_when_present = ("ucp-agent", "signature-agent", "idempotency-key")
    missing_conditional = [
        hdr for hdr in mandatory_when_present if hdr in normalized_headers and hdr not in covered_set
    ]

    if missing_base or missing_conditional:
        return GuardDecision(
            allowed=False,
            reason_code="UCP_SIGNED_REQUEST_OMITS_REQUIRED_COVERED_HEADER_BLOCKED",
            detail=(
                f"Signed UCP REST request omits mandatory covered components: "
                f"base={missing_base}, conditional_headers={missing_conditional}."
            ),
            evidence={
                "missing_base_components": missing_base,
                "missing_conditional_headers": missing_conditional,
                "covered_components": covered,
            },
        )

    return GuardDecision(
        allowed=True,
        reason_code="UCP_SIGNED_REQUEST_COVERED_HEADERS_OK",
        detail="All required base and conditional UCP identity/idempotency headers are covered by Signature-Input.",
        evidence={"covered_components": covered},
    )


# ---------------------------------------------------------------------------
# PR-02: Universal-Commerce-Protocol/ucp#641
# ---------------------------------------------------------------------------
WELL_KNOWN_COLLECTION_STATUSES = frozenset({"awaiting_payment", "paid", "expired", "canceled"})


def audit_ucp_order_out_of_session_collection(
    *,
    instrument_id: str,
    previous_collection_status: str | None,
    current_collection_status: str,
    order_actions: Sequence[Mapping[str, Any]],
    current_timestamp: int,
    attempt_fulfillment_release: bool = False,
) -> GuardDecision:
    """Validate out-of-session payment collection status and Order render_artifact actions (#641)."""
    status = str(current_collection_status or "").strip()
    prev = str(previous_collection_status or "").strip() if previous_collection_status else None

    if status not in WELL_KNOWN_COLLECTION_STATUSES:
        return GuardDecision(
            allowed=False,
            reason_code="UCP_ORDER_OUT_OF_SESSION_COLLECTION_VIOLATION_BLOCKED",
            detail=f"Invalid or unsupported per-instrument collection_status '{status}'.",
            evidence={"instrument_id": instrument_id, "collection_status": status},
        )

    if prev in {"expired", "canceled"} and status == "paid":
        return GuardDecision(
            allowed=False,
            reason_code="UCP_ORDER_OUT_OF_SESSION_COLLECTION_VIOLATION_BLOCKED",
            detail=f"Terminal out-of-session instrument '{instrument_id}' cannot transition from '{prev}' to 'paid'.",
            evidence={"instrument_id": instrument_id, "previous_status": prev, "current_status": status},
        )

    if status == "awaiting_payment":
        valid_artifacts = [
            act
            for act in order_actions
            if str(act.get("type", "")) == "dev.ucp.common.payment.render_artifact"
            and str(act.get("instrument_id", "")) == instrument_id
            and str(act.get("artifact_url", "")).startswith("https://")
            and int(act.get("expires_at", 0)) > current_timestamp
        ]
        if not valid_artifacts:
            return GuardDecision(
                allowed=False,
                reason_code="UCP_ORDER_OUT_OF_SESSION_COLLECTION_VIOLATION_BLOCKED",
                detail="Instrument awaiting_payment requires a non-expired dev.ucp.common.payment.render_artifact action on Order.",
                evidence={"instrument_id": instrument_id, "actions_count": len(order_actions)},
            )

    if attempt_fulfillment_release and status != "paid":
        return GuardDecision(
            allowed=False,
            reason_code="UCP_ORDER_OUT_OF_SESSION_COLLECTION_VIOLATION_BLOCKED",
            detail=f"Cannot release Order fulfillment while instrument '{instrument_id}' has collection_status='{status}'.",
            evidence={"instrument_id": instrument_id, "collection_status": status},
        )

    return GuardDecision(
        allowed=True,
        reason_code="UCP_ORDER_OUT_OF_SESSION_COLLECTION_OK",
        detail="Out-of-session Order payment collection state and render_artifact action verified.",
        evidence={"instrument_id": instrument_id, "collection_status": status},
    )


# ---------------------------------------------------------------------------
# PR-03: Universal-Commerce-Protocol/ucp#489
# ---------------------------------------------------------------------------
def audit_ucp_catch_weight_authorization_hold(
    *,
    target_weight: float,
    actual_weight: float,
    max_overage_tolerance: float,
    min_underage_tolerance: float,
    estimated_amount_minor: int,
    capture_amount_minor: int,
    mandate_max_amount_minor: int,
    required_hold_time_days: int,
    authorization_hold_days: int,
    elapsed_fulfillment_days: int,
) -> GuardDecision:
    """Validate variable-yield catch-weight bounds and programmable authorization hold window (#489)."""
    min_weight = target_weight * (1.0 - min_underage_tolerance)
    max_weight = target_weight * (1.0 + max_overage_tolerance)
    max_allowed_capture = int(round(estimated_amount_minor * (1.0 + max_overage_tolerance)))

    weight_ok = (min_weight - 1e-9) <= actual_weight <= (max_weight + 1e-9)
    amount_ok = 0 < capture_amount_minor <= min(max_allowed_capture, mandate_max_amount_minor)
    hold_ok = authorization_hold_days >= required_hold_time_days and elapsed_fulfillment_days <= authorization_hold_days

    if not (weight_ok and amount_ok and hold_ok):
        return GuardDecision(
            allowed=False,
            reason_code="UCP_CATCH_WEIGHT_TOLERANCE_OR_HOLD_VIOLATION_BLOCKED",
            detail=(
                f"Catch-weight invariant violated: weight_ok={weight_ok}, "
                f"amount_ok={amount_ok}, hold_ok={hold_ok}."
            ),
            evidence={
                "actual_weight": actual_weight,
                "allowed_weight_range": [round(min_weight, 4), round(max_weight, 4)],
                "capture_amount_minor": capture_amount_minor,
                "max_allowed_capture_minor": min(max_allowed_capture, mandate_max_amount_minor),
                "authorization_hold_days": authorization_hold_days,
                "required_hold_time_days": required_hold_time_days,
                "elapsed_fulfillment_days": elapsed_fulfillment_days,
            },
        )

    return GuardDecision(
        allowed=True,
        reason_code="UCP_CATCH_WEIGHT_TOLERANCE_AND_HOLD_OK",
        detail="Catch-weight fulfillment variance and programmable authorization hold satisfied.",
        evidence={
            "actual_weight": actual_weight,
            "capture_amount_minor": capture_amount_minor,
            "authorization_hold_days": authorization_hold_days,
        },
    )


# ---------------------------------------------------------------------------
# PR-04: Universal-Commerce-Protocol/ucp#668 + #649
# ---------------------------------------------------------------------------
def audit_ucp_openapi_auth_and_update_checkout_id(
    *,
    openapi_header_parameters: Sequence[Mapping[str, Any]],
    has_security_schemes: bool,
    update_checkout_schema_exposes_writable_id: bool,
    path_checkout_id: str,
    request_body: Mapping[str, Any],
) -> GuardDecision:
    """Reject OpenAPI 3.1.0 header Authorization parameter (#668) and update_checkout body id exposure (#649)."""
    illegal_auth_header = any(
        str(p.get("in", "")).strip().lower() == "header"
        and str(p.get("name", "")).strip().lower() == "authorization"
        for p in openapi_header_parameters
    )
    body_has_id = "id" in request_body
    body_id_mismatch = body_has_id and str(request_body.get("id")) != path_checkout_id

    if illegal_auth_header or not has_security_schemes or update_checkout_schema_exposes_writable_id or body_has_id:
        return GuardDecision(
            allowed=False,
            reason_code="UCP_OPENAPI_AUTH_HEADER_OR_UPDATE_ID_EXPOSED_BLOCKED",
            detail=(
                "OpenAPI 3.1.0 prohibits 'in: header, name: Authorization' (must use securitySchemes) "
                "and update_checkout must omit/readOnly checkout.id in requestBody."
            ),
            evidence={
                "illegal_auth_header": illegal_auth_header,
                "has_security_schemes": has_security_schemes,
                "update_checkout_schema_exposes_writable_id": update_checkout_schema_exposes_writable_id,
                "body_has_id": body_has_id,
                "body_id_mismatch": body_id_mismatch,
            },
        )

    return GuardDecision(
        allowed=True,
        reason_code="UCP_OPENAPI_AUTH_AND_UPDATE_CHECKOUT_ID_OK",
        detail="OpenAPI 3.1.0 securitySchemes and update_checkout request-omit id contract verified.",
        evidence={"path_checkout_id": path_checkout_id},
    )


# ---------------------------------------------------------------------------
# PR-05: x402-foundation/x402#3810 + #3657
# ---------------------------------------------------------------------------
def audit_x402_http_method_settlement_eligibility(
    *,
    http_method: str,
    has_payment_signature: bool,
    attempt_settlement: bool,
    allowed_payment_methods: Sequence[str],
) -> GuardDecision:
    """Prevent settling x402 payments on HEAD (#3810) and enforce HTTP method payment eligibility (#3657)."""
    method = str(http_method or "").strip().upper()
    allowed_upper = {str(m).strip().upper() for m in allowed_payment_methods}

    if method == "HEAD" and (has_payment_signature or attempt_settlement):
        return GuardDecision(
            allowed=False,
            reason_code="X402_HEAD_SETTLEMENT_OR_METHOD_MISMATCH_BLOCKED",
            detail="RFC 9110 §9.3.2 HEAD responses cannot carry a body; settling a payment on HEAD charges the buyer for zero content (#3810).",
            evidence={"http_method": method, "has_payment_signature": has_payment_signature},
        )

    if has_payment_signature and (method not in allowed_upper or "HEAD" in allowed_upper):
        return GuardDecision(
            allowed=False,
            reason_code="X402_HEAD_SETTLEMENT_OR_METHOD_MISMATCH_BLOCKED",
            detail=f"HTTP method '{method}' is not eligible for payment settlement under allowed_payment_methods={sorted(allowed_upper)} (#3657).",
            evidence={"http_method": method, "allowed_payment_methods": sorted(allowed_upper)},
        )

    return GuardDecision(
        allowed=True,
        reason_code="X402_HTTP_METHOD_SETTLEMENT_ELIGIBILITY_OK",
        detail=f"HTTP method '{method}' payment settlement eligibility verified.",
        evidence={"http_method": method, "allowed_payment_methods": sorted(allowed_upper)},
    )


# ---------------------------------------------------------------------------
# PR-06: x402-foundation/x402#3803
# ---------------------------------------------------------------------------
def audit_x402_payment_required_header_budget(
    *,
    payment_required_payload: Mapping[str, Any],
    max_header_bytes: int = 7168,
    aiohttp_limit_bytes: int = 8190,
    node_undici_limit_bytes: int = 16384,
) -> GuardDecision:
    """Enforce a size budget on base64 PAYMENT-REQUIRED headers so aiohttp (8 KB) and Node undici (16 KB) do not fail (#3803)."""
    raw_json = json.dumps(payment_required_payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded_b64 = base64.b64encode(raw_json)
    header_len = len(encoded_b64)

    if header_len > max_header_bytes:
        return GuardDecision(
            allowed=False,
            reason_code="X402_PAYMENT_REQUIRED_HEADER_BUDGET_EXCEEDED_BLOCKED",
            detail=(
                f"PAYMENT-REQUIRED header is {header_len} bytes (exceeds {max_header_bytes}-byte budget; "
                f"aiohttp limit={aiohttp_limit_bytes}, Node undici limit={node_undici_limit_bytes})."
            ),
            evidence={
                "encoded_header_bytes": header_len,
                "max_header_bytes": max_header_bytes,
                "exceeds_aiohttp_8kb": header_len > aiohttp_limit_bytes,
                "exceeds_node_16kb": header_len > node_undici_limit_bytes,
            },
        )

    return GuardDecision(
        allowed=True,
        reason_code="X402_PAYMENT_REQUIRED_HEADER_BUDGET_OK",
        detail=f"PAYMENT-REQUIRED header length ({header_len} bytes) is within the {max_header_bytes}-byte budget.",
        evidence={"encoded_header_bytes": header_len, "max_header_bytes": max_header_bytes},
    )


# ---------------------------------------------------------------------------
# PR-07: x402-foundation/x402#3814
# ---------------------------------------------------------------------------
def audit_x402_axios_stream_402_drain(
    *,
    response_type: str,
    keep_alive_max_sockets: int,
    intermediate_402_stream_drained: bool,
) -> GuardDecision:
    """Require draining or destroying intermediate 402 response streams before retrying paid requests (#3814)."""
    is_stream = str(response_type or "").strip().lower() == "stream"
    if is_stream and not intermediate_402_stream_drained:
        return GuardDecision(
            allowed=False,
            reason_code="X402_STREAM_INTERMEDIATE_402_UNDRAINED_DEADLOCK_BLOCKED",
            detail=(
                f"Unconsumed intermediate 402 stream with responseType='stream' (maxSockets={keep_alive_max_sockets}) "
                "blocks keep-alive socket reuse and queues paid retry indefinitely (#3814)."
            ),
            evidence={
                "response_type": response_type,
                "keep_alive_max_sockets": keep_alive_max_sockets,
                "intermediate_402_stream_drained": intermediate_402_stream_drained,
            },
        )

    return GuardDecision(
        allowed=True,
        reason_code="X402_STREAM_INTERMEDIATE_402_DRAIN_OK",
        detail="Intermediate 402 stream properly consumed/released before paid retry.",
        evidence={"response_type": response_type, "intermediate_402_stream_drained": intermediate_402_stream_drained},
    )


# ---------------------------------------------------------------------------
# PR-08: x402-foundation/x402#3747
# ---------------------------------------------------------------------------
def split_cache_control_directives_rfc9111(header_value: str) -> list[str]:
    """Split a Cache-Control header on top-level commas, ignoring commas inside quoted-string values (#3747)."""
    directives: list[str] = []
    buf: list[str] = []
    in_quotes = False
    escaped = False

    for ch in header_value:
        if escaped:
            buf.append(ch)
            escaped = False
            continue
        if ch == "\\":
            buf.append(ch)
            escaped = True
            continue
        if ch == '"':
            in_quotes = not in_quotes
            buf.append(ch)
            continue
        if ch == "," and not in_quotes:
            token = "".join(buf).strip()
            if token:
                directives.append(token)
            buf = []
            continue
        buf.append(ch)

    tail = "".join(buf).strip()
    if tail:
        directives.append(tail)
    return directives


def audit_x402_cache_control_private_directive(
    *,
    cache_control_header: str,
) -> GuardDecision:
    """Verify that paid x402 responses carry a real top-level 'private' directive, not 'private' inside quotes (#3747)."""
    directives = split_cache_control_directives_rfc9111(cache_control_header)
    names = [d.split("=", 1)[0].strip().lower() for d in directives]

    has_top_level_private = "private" in names
    has_top_level_public = "public" in names

    if not has_top_level_private or has_top_level_public:
        return GuardDecision(
            allowed=False,
            reason_code="X402_CACHE_CONTROL_QUOTED_PRIVATE_CONFUSION_BLOCKED",
            detail=(
                f"Cache-Control header lacks an unquoted top-level 'private' directive or retains 'public': "
                f"parsed_directives={directives}."
            ),
            evidence={
                "parsed_directives": directives,
                "has_top_level_private": has_top_level_private,
                "has_top_level_public": has_top_level_public,
            },
        )

    return GuardDecision(
        allowed=True,
        reason_code="X402_CACHE_CONTROL_PRIVATE_DIRECTIVE_OK",
        detail="Cache-Control contains an unquoted top-level 'private' directive and no 'public' leak.",
        evidence={"parsed_directives": directives},
    )


# ---------------------------------------------------------------------------
# PR-09: x402-foundation/x402#3755
# ---------------------------------------------------------------------------
def audit_x402_payee_name_ens_binding(
    *,
    payee_ens_name: str,
    request_origin: str,
    accepts: Sequence[Mapping[str, str]],
    ens_allowed_origins: Sequence[str],
    ens_authorized_payto_by_network: Mapping[str, Sequence[str]],
    ens_owner_signature_valid: bool,
    ens_expiry_timestamp: int,
    current_timestamp: int,
) -> GuardDecision:
    """Validate x402 `payee-name` extension binding between ENS name, origin, and (network, payTo) (#3755)."""
    if not payee_ens_name.endswith(".eth") or not ens_owner_signature_valid or current_timestamp >= ens_expiry_timestamp:
        return GuardDecision(
            allowed=False,
            reason_code="X402_PAYEE_NAME_ENS_ORIGIN_OR_PAYTO_UNBOUND_BLOCKED",
            detail="ENS payee-name record is expired, invalidly signed, or not a valid .eth name.",
            evidence={
                "payee_ens_name": payee_ens_name,
                "ens_owner_signature_valid": ens_owner_signature_valid,
                "expired": current_timestamp >= ens_expiry_timestamp,
            },
        )

    normalized_origin = request_origin.strip().lower().rstrip("/")
    allowed_origins_norm = {o.strip().lower().rstrip("/") for o in ens_allowed_origins}
    if normalized_origin not in allowed_origins_norm:
        return GuardDecision(
            allowed=False,
            reason_code="X402_PAYEE_NAME_ENS_ORIGIN_OR_PAYTO_UNBOUND_BLOCKED",
            detail=f"Request origin '{normalized_origin}' is not listed in ENS org.x402.origins for '{payee_ens_name}'.",
            evidence={"payee_ens_name": payee_ens_name, "request_origin": normalized_origin},
        )

    unbound_accepts: list[dict[str, str]] = []
    for item in accepts:
        net = str(item.get("network", "")).strip()
        pay_to = str(item.get("payTo", "")).strip().lower()
        allowed_addrs = {a.strip().lower() for a in ens_authorized_payto_by_network.get(net, ())}
        if not net or not pay_to or pay_to not in allowed_addrs:
            unbound_accepts.append({"network": net, "payTo": pay_to})

    if not accepts or unbound_accepts:
        return GuardDecision(
            allowed=False,
            reason_code="X402_PAYEE_NAME_ENS_ORIGIN_OR_PAYTO_UNBOUND_BLOCKED",
            detail=f"One or more (network, payTo) entries are not bound to ENS name '{payee_ens_name}': {unbound_accepts}.",
            evidence={"payee_ens_name": payee_ens_name, "unbound_accepts": unbound_accepts},
        )

    return GuardDecision(
        allowed=True,
        reason_code="X402_PAYEE_NAME_ENS_BINDING_OK",
        detail=f"All (network, payTo) pairs and origin '{normalized_origin}' verified against ENS '{payee_ens_name}'.",
        evidence={"payee_ens_name": payee_ens_name, "request_origin": normalized_origin},
    )


# ---------------------------------------------------------------------------
# PR-10: x402-foundation/x402#3693
# ---------------------------------------------------------------------------
def audit_x402_ext_delegation_grant(
    *,
    grant: Mapping[str, Any],
    principal_jws_valid: bool,
    authorization_from: str,
    resource_server_origin: str,
    payment_amount_minor: int,
    cumulative_spent_minor: int,
    payment_asset: str,
    payment_network: str,
    current_timestamp: int,
) -> GuardDecision:
    """Validate x402 `ext-delegation` principal-signed JWS grant scope and agent signer match (#3693)."""
    grant_agent = str(grant.get("agent", "")).strip().lower()
    signer = str(authorization_from or "").strip().lower()
    audience = [str(a).strip().lower().rstrip("/") for a in grant.get("audience", ())]
    origin_norm = resource_server_origin.strip().lower().rstrip("/")
    max_amount = int(grant.get("maxAmount", 0))
    agg_budget = int(grant.get("aggregateBudget", max_amount))
    expires_at = int(grant.get("expiresAt", 0))

    signer_ok = bool(grant_agent) and grant_agent == signer
    audience_ok = origin_norm in audience
    asset_ok = str(grant.get("asset", "")) == payment_asset and str(grant.get("network", "")) == payment_network
    amount_ok = 0 < payment_amount_minor <= max_amount and (cumulative_spent_minor + payment_amount_minor) <= agg_budget
    fresh_ok = current_timestamp < expires_at

    if not (principal_jws_valid and signer_ok and audience_ok and asset_ok and amount_ok and fresh_ok):
        return GuardDecision(
            allowed=False,
            reason_code="X402_EXT_DELEGATION_SCOPE_OR_SIGNER_VIOLATION_BLOCKED",
            detail=(
                f"ext-delegation grant check failed: jws={principal_jws_valid}, signer_ok={signer_ok}, "
                f"audience_ok={audience_ok}, asset_ok={asset_ok}, amount_ok={amount_ok}, fresh_ok={fresh_ok}."
            ),
            evidence={
                "principal": grant.get("principal"),
                "grant_agent": grant_agent,
                "authorization_from": signer,
                "payment_amount_minor": payment_amount_minor,
                "max_amount_minor": max_amount,
                "aggregate_budget_minor": agg_budget,
                "cumulative_spent_minor": cumulative_spent_minor,
            },
        )

    return GuardDecision(
        allowed=True,
        reason_code="X402_EXT_DELEGATION_GRANT_OK",
        detail="Principal-signed ext-delegation grant verified for agent signer, audience, asset, and spend cap.",
        evidence={"principal": grant.get("principal"), "agent": grant_agent},
    )


# ---------------------------------------------------------------------------
# PR-11: x402-foundation/x402#3792 + #3779
# ---------------------------------------------------------------------------
def audit_x402_python_facilitator_async_and_error_body(
    *,
    is_async_facilitator_client: bool,
    bazaar_called_method: str,
    facilitator_http_status: int,
    facilitator_error_body: Mapping[str, Any] | None,
    raises_generic_value_error_dropping_body: bool,
) -> GuardDecision:
    """Enforce Python async BazaarExtension `_get_async_client()` (#3792) and non-200 error body preservation (#3779)."""
    wrong_client_getter = is_async_facilitator_client and bazaar_called_method == "_get_client"
    dropped_non200_body = (
        facilitator_http_status != 200
        and bool(facilitator_error_body)
        and raises_generic_value_error_dropping_body
    )

    if wrong_client_getter or dropped_non200_body:
        return GuardDecision(
            allowed=False,
            reason_code="X402_PYTHON_ASYNC_CLIENT_OR_NON200_BODY_DROP_BLOCKED",
            detail=(
                f"Python x402 facilitator violation: wrong_client_getter={wrong_client_getter} (#3792), "
                f"dropped_non200_body={dropped_non200_body} (#3779)."
            ),
            evidence={
                "is_async_facilitator_client": is_async_facilitator_client,
                "bazaar_called_method": bazaar_called_method,
                "facilitator_http_status": facilitator_http_status,
                "preserved_error_reason": (facilitator_error_body or {}).get("invalidReason")
                or (facilitator_error_body or {}).get("errorReason"),
            },
        )

    return GuardDecision(
        allowed=True,
        reason_code="X402_PYTHON_FACILITATOR_ASYNC_AND_ERROR_BODY_OK",
        detail="Python async facilitator client dispatch and structured non-200 Verify/Settle body preserved.",
        evidence={"bazaar_called_method": bazaar_called_method, "facilitator_http_status": facilitator_http_status},
    )


# ---------------------------------------------------------------------------
# PR-12: x402-foundation/x402#3650 + #3680 + #3811
# ---------------------------------------------------------------------------
def audit_x402_hook_error_status_and_plain_body(
    *,
    after_payment_creation_hook_error: str | None,
    go_client_discards_hook_error: bool,
    payment_flow: str,
    settle_response_success: bool,
    paid_http_status: int,
    on_payment_response_receives_status: bool,
    custom_failure_content_type: str,
    serialized_failure_body: str,
) -> GuardDecision:
    """Block discarded Go hook errors (#3650), missing paid HTTP status on upfront settlement (#3680), and JSON-encoded text/plain bodies (#3811)."""
    hook_swallowed = bool(after_payment_creation_hook_error) and go_client_discards_hook_error
    upfront_blind_5xx = (
        payment_flow == "upfront"
        and settle_response_success
        and paid_http_status >= 400
        and not on_payment_response_receives_status
    )
    plain_json_encoded = (
        custom_failure_content_type.startswith("text/plain")
        and serialized_failure_body.startswith('"')
        and serialized_failure_body.endswith('"')
    )

    if hook_swallowed or upfront_blind_5xx or plain_json_encoded:
        return GuardDecision(
            allowed=False,
            reason_code="X402_HOOK_ERROR_SWALLOWED_STATUS_OMITTED_OR_PLAIN_JSON_ENCODED_BLOCKED",
            detail=(
                f"x402 lifecycle bug detected: hook_swallowed={hook_swallowed} (#3650), "
                f"upfront_blind_5xx={upfront_blind_5xx} (#3680), plain_json_encoded={plain_json_encoded} (#3811)."
            ),
            evidence={
                "hook_swallowed": hook_swallowed,
                "upfront_blind_5xx": upfront_blind_5xx,
                "plain_json_encoded": plain_json_encoded,
                "paid_http_status": paid_http_status,
            },
        )

    return GuardDecision(
        allowed=True,
        reason_code="X402_HOOK_STATUS_AND_PLAIN_BODY_OK",
        detail="OnAfterPaymentCreation errors propagated, paid HTTP status exposed to hooks, and text/plain body preserved.",
        evidence={"paid_http_status": paid_http_status},
    )


# ---------------------------------------------------------------------------
# PR-13: x402-foundation/x402#3750 + #3660
# ---------------------------------------------------------------------------
def audit_x402_per_call_request_context_and_amount_law(
    *,
    in_flight_request_id: str,
    payload_context_request_id: str | None,
    uses_shared_constructor_request: bool,
    expected_usd_minor: int,
    rail_quotes: Sequence[Mapping[str, Any]],
    max_fx_bps_drift: int = 100,
) -> GuardDecision:
    """Enforce per-call PaymentPayloadContext.request (#3750) and non-zero cross-rail amount law (#3660)."""
    context_mismatch = uses_shared_constructor_request or payload_context_request_id != in_flight_request_id

    invalid_rails: list[dict[str, Any]] = []
    for quote in rail_quotes:
        rail = str(quote.get("network", ""))
        max_amt = int(quote.get("maxAmountRequired", 0))
        usd_equiv = int(quote.get("usdEquivalentMinor", 0))
        drift_bps = abs(usd_equiv - expected_usd_minor) * 10_000 // max(expected_usd_minor, 1)
        if max_amt <= 0 or usd_equiv <= 0 or drift_bps > max_fx_bps_drift:
            invalid_rails.append(
                {
                    "network": rail,
                    "maxAmountRequired": max_amt,
                    "usdEquivalentMinor": usd_equiv,
                    "drift_bps": drift_bps,
                }
            )

    if context_mismatch or not rail_quotes or invalid_rails:
        return GuardDecision(
            allowed=False,
            reason_code="X402_CONCURRENT_REQUEST_CONTEXT_OR_ZERO_RAIL_AMOUNT_BLOCKED",
            detail=(
                f"Per-call request binding or multi-rail amount law violated: "
                f"context_mismatch={context_mismatch} (#3750), invalid_rails={invalid_rails} (#3660)."
            ),
            evidence={
                "in_flight_request_id": in_flight_request_id,
                "payload_context_request_id": payload_context_request_id,
                "uses_shared_constructor_request": uses_shared_constructor_request,
                "invalid_rails": invalid_rails,
            },
        )

    return GuardDecision(
        allowed=True,
        reason_code="X402_PER_CALL_REQUEST_CONTEXT_AND_AMOUNT_LAW_OK",
        detail="Per-call PaymentPayloadContext.request and non-vacuous cross-rail amount equivalence verified.",
        evidence={"in_flight_request_id": in_flight_request_id, "rails_verified": len(rail_quotes)},
    )


# ---------------------------------------------------------------------------
# PR-14: modelcontextprotocol/modelcontextprotocol#3238 + #3226
# ---------------------------------------------------------------------------
SUPPORTED_MCP_JSON_SCHEMA_DIALECTS = frozenset(
    {
        "https://json-schema.org/draft/2020-12/schema",
        "http://json-schema.org/draft-07/schema#",
    }
)


def audit_mcp_schema_dialect_and_template_list_changed(
    *,
    input_schema: Mapping[str, Any],
    requested_schema: Mapping[str, Any],
    resource_templates_mutated: bool,
    emitted_resources_list_changed: bool,
    client_refetched_resource_templates: bool,
) -> GuardDecision:
    """Validate MCP inputSchema dialect support, requestedSchema form-profile pinning (#3238), and template list_changed (#3226)."""
    declared_dialect = str(
        input_schema.get("$schema", "https://json-schema.org/draft/2020-12/schema")
    ).strip()
    unsupported_input_dialect = declared_dialect not in SUPPORTED_MCP_JSON_SCHEMA_DIALECTS

    requested_has_dialect_override = "$schema" in requested_schema
    req_props = requested_schema.get("properties", {})
    requested_has_nested_non_primitive = any(
        isinstance(spec, Mapping) and str(spec.get("type", "")) in {"object", "array"}
        for spec in (req_props.values() if isinstance(req_props, Mapping) else ())
    )

    template_sync_broken = resource_templates_mutated and (
        not emitted_resources_list_changed or not client_refetched_resource_templates
    )

    if (
        unsupported_input_dialect
        or requested_has_dialect_override
        or requested_has_nested_non_primitive
        or template_sync_broken
    ):
        return GuardDecision(
            allowed=False,
            reason_code="MCP_SCHEMA_DIALECT_LAYER_OR_TEMPLATE_LIST_CHANGED_BLOCKED",
            detail=(
                f"MCP schema/notification invariant violated: unsupported_input_dialect={unsupported_input_dialect}, "
                f"requested_has_dialect_override={requested_has_dialect_override}, "
                f"requested_has_nested_non_primitive={requested_has_nested_non_primitive} (#3238), "
                f"template_sync_broken={template_sync_broken} (#3226)."
            ),
            evidence={
                "declared_input_dialect": declared_dialect,
                "requested_has_dialect_override": requested_has_dialect_override,
                "requested_has_nested_non_primitive": requested_has_nested_non_primitive,
                "template_sync_broken": template_sync_broken,
            },
        )

    return GuardDecision(
        allowed=True,
        reason_code="MCP_SCHEMA_DIALECT_AND_TEMPLATE_LIST_CHANGED_OK",
        detail="MCP inputSchema dialect, requestedSchema flat form-profile, and resource template list_changed verified.",
        evidence={"declared_input_dialect": declared_dialect},
    )


# ---------------------------------------------------------------------------
# PR-15: sierra-research/tau2-bench#654 + #477
# ---------------------------------------------------------------------------
ALLOWED_USER_SCENARIO_KEYS = frozenset({"persona", "instructions"})


def audit_tau2_target_db_cache_and_persona_schema(
    *,
    task_id: str,
    current_actions_sha256: str,
    cached_actions_sha256: str,
    current_initial_db_sha256: str,
    cached_initial_db_sha256: str,
    current_env_version: str,
    cached_env_version: str,
    user_scenario_dict: Mapping[str, Any],
) -> GuardDecision:
    """Validate content-addressed target DB cache key freshness (#654) and reject `persoca` typo in user_scenario (#477)."""
    stale_cache_hit = (
        current_actions_sha256 != cached_actions_sha256
        or current_initial_db_sha256 != cached_initial_db_sha256
        or current_env_version != cached_env_version
    )
    scenario_keys = set(user_scenario_dict.keys())
    unknown_keys = sorted(scenario_keys - ALLOWED_USER_SCENARIO_KEYS)
    missing_persona = "persona" not in scenario_keys

    if stale_cache_hit or unknown_keys or missing_persona:
        return GuardDecision(
            allowed=False,
            reason_code="TAU2_STALE_TARGET_DB_CACHE_OR_PERSOCA_TYPO_BLOCKED",
            detail=(
                f"tau2-bench target DB cache or user_scenario schema violation: "
                f"stale_cache_hit={stale_cache_hit} (#654), unknown_keys={unknown_keys}, missing_persona={missing_persona} (#477)."
            ),
            evidence={
                "task_id": task_id,
                "stale_cache_hit": stale_cache_hit,
                "unknown_user_scenario_keys": unknown_keys,
                "missing_persona": missing_persona,
            },
        )

    return GuardDecision(
        allowed=True,
        reason_code="TAU2_TARGET_DB_CACHE_AND_PERSONA_SCHEMA_OK",
        detail="Target DB cache key matches actions/DB/env digests and user_scenario.persona key is valid.",
        evidence={"task_id": task_id},
    )


# ---------------------------------------------------------------------------
# PR-16: sierra-research/tau2-bench#154 + #474 + #430
# ---------------------------------------------------------------------------
def audit_tau2_concurrency_deepcopy_judge_and_num_coercion(
    *,
    shares_class_level_mutable_ref: bool,
    judge_llm_model: str,
    judge_api_key_is_placeholder: bool,
    trajectories_saved_before_judge_eval: bool,
    numeric_tool_arg_value: int | float | str,
    tool_rejects_numeric_string: bool,
) -> GuardDecision:
    """Block shared class-level default_vpn_details (#154), judge silent fallback (#474), and numeric string tool rejection (#430)."""
    can_parse_numeric = False
    try:
        float(str(numeric_tool_arg_value).strip())
        can_parse_numeric = True
    except ValueError:
        can_parse_numeric = False

    inconsistent_str_num_rejection = (
        isinstance(numeric_tool_arg_value, str) and can_parse_numeric and tool_rejects_numeric_string
    )
    unsafe_judge_config = judge_api_key_is_placeholder or not trajectories_saved_before_judge_eval or not judge_llm_model

    if shares_class_level_mutable_ref or unsafe_judge_config or inconsistent_str_num_rejection:
        return GuardDecision(
            allowed=False,
            reason_code="TAU2_SHARED_VPN_STATE_JUDGE_FALLBACK_OR_STR_NUM_ERROR_BLOCKED",
            detail=(
                f"tau2-bench reliability violation: shares_class_level_mutable_ref={shares_class_level_mutable_ref} (#154), "
                f"unsafe_judge_config={unsafe_judge_config} (#474), "
                f"inconsistent_str_num_rejection={inconsistent_str_num_rejection} (#430)."
            ),
            evidence={
                "shares_class_level_mutable_ref": shares_class_level_mutable_ref,
                "judge_llm_model": judge_llm_model,
                "judge_api_key_is_placeholder": judge_api_key_is_placeholder,
                "trajectories_saved_before_judge_eval": trajectories_saved_before_judge_eval,
                "inconsistent_str_num_rejection": inconsistent_str_num_rejection,
            },
        )

    return GuardDecision(
        allowed=True,
        reason_code="TAU2_CONCURRENCY_JUDGE_AND_NUM_COERCION_OK",
        detail="Per-simulation deep-copy isolation, preflight judge LLM validation, and numeric string coercion verified.",
        evidence={"judge_llm_model": judge_llm_model},
    )
