"""Stage 194 deterministic protocol security guards.

Covers primary-source upstream protocol evolutions verified on 2026-10-23:
1. Universal-Commerce-Protocol/ucp PR #466 & PR #915 & PR #881:
   - Required `ap2.merchant_authorization` detached JWS in AP2-active checkout
     responses (`ap2_with_merchant_authorization`).
   - Extensible `checkout.config` (Reverse-DNS -> JSON Schema),
     `required_declared_fields` (`uniqueItems: true`, Checkout vs. line-item
     scope), buyer-submitted `declared_fields` on `create`/`update` (and strict
     omission on `complete`), plus empty `payment: {}` on `complete` for fully
     deferred payment terms (`PR #881`).
2. x402-foundation/x402 PR #3878, PR #3138, PR #3215, & PR #2730:
   - Strict V2 CAIP-2 network validation (`^[-a-z0-9]{3,8}:[-_a-zA-Z0-9]{1,32}$`)
     while preserving V1 legacy network names (`PR #3878`).
   - Bazaar opaque-origin (`url.origin === "null"`, e.g. `mcp://tool/x?a=1#b`)
     canonical URL reconstruction via `protocol + "//" + host + (routeTemplate ?? pathname)`
     stripping query/fragment without producing `"null/..."` (`PR #3138`).
   - Per-CAIP-2-namespace facilitator wildcard pattern derivation (`PR #3215`).
   - `x402-fetch` resilient `accepts[]` filtering via per-entry `safeParse` (`PR #2730`).
3. x402-foundation/x402 PR #3868 (Correctness & Dispute Extension — Bonded Verdicts):
   - Downstream-of-settlement bonded verdicts (`CONFIRMED | REFUTED | PARTIAL | INSUFFICIENT_DATA`),
     separating signature/hash authorship verification from independent criterion
     re-evaluation (`criterion_id`, `evidence_digest`, `resolver_id`, `resolver_version`),
     forbidding `INSUFFICIENT_DATA` from being treated/slashed as incorrect work,
     enforcing on-chain bond reservation math (`per_verdict_max <= free_collateral / obligations`),
     forbidding self-adjudication (`adjudicator_id != payee_id`), and requiring
     `(payer, payee, operation, receipt_digest)` binding rather than bare `payment_identifier`.
4. modelcontextprotocol/modelcontextprotocol PR #2792 (SEP-2792), PR #2778 (SEP-2778), & PR #2633 (SEP-2633):
   - Per-request language preference `_meta["io.modelcontextprotocol/acceptLanguage"]`
     and `_meta["io.modelcontextprotocol/contentLanguage"]`: request-scoped only
     (no session state persistence, no currency/timezone locale side effects),
     character-for-character Streamable HTTP `Accept-Language` mirror agreement
     (`-32020 HeaderMismatch`), and strict prohibition on translating machine
     identifiers (`BaseMetadata.name`, `params.name`, property keys, enum values).
   - SEP-2778 schema security constraints (`Icon.src`, `Root.uri`,
     `ElicitRequestURLParams.url` + `elicitationId`, `Identifier <= 256`,
     `Cursor <= 8192`, `ttlMs <= 86400000`) and SEP-2633 `mcp.json` validation.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

REVERSE_DNS_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$")
DETACHED_JWS_RE = re.compile(r"^[A-Za-z0-9_-]+\.\.[A-Za-z0-9_-]+$")
CAIP2_V2_NETWORK_RE = re.compile(r"^[-a-z0-9]{3,8}:[-_a-zA-Z0-9]{1,32}$")
WHATWG_SPECIAL_SCHEMES = frozenset({"http", "https", "ws", "wss", "ftp", "file"})
VALID_VERDICT_OUTCOMES = frozenset(
    {"CONFIRMED", "REFUTED", "PARTIAL", "INSUFFICIENT_DATA"}
)
MCP_ACCEPT_LANGUAGE_KEY = "io.modelcontextprotocol/acceptLanguage"
MCP_CONTENT_LANGUAGE_KEY = "io.modelcontextprotocol/contentLanguage"
MCP_SERVER_NAME_RE = re.compile(r"^[a-zA-Z0-9_\[\]-]+$")
MCP_ICON_SRC_RE = re.compile(r"^(https?://|data:image/)")
MCP_ICON_SIZE_RE = re.compile(r"^(\d+x\d+|any)$")
MCP_SECRET_INTERP_RE = re.compile(r"\$\{([a-z][a-z0-9+.-]*):([^}]+)\}")
ALLOWED_SECRET_SCHEMES = frozenset({"env", "value", "input", "op"})


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    action: str
    reason: str
    details: dict[str, Any]


def _validate_simple_json_schema(value: Any, schema: Mapping[str, Any]) -> bool:
    if not isinstance(value, Mapping):
        return False
    required = schema.get("required", [])
    if isinstance(required, Sequence):
        for req_key in required:
            if req_key not in value:
                return False
    properties = schema.get("properties", {})
    if isinstance(properties, Mapping):
        for prop_key, prop_val in value.items():
            if schema.get("additionalProperties") is False and prop_key not in properties:
                return False
            prop_schema = properties.get(prop_key)
            if isinstance(prop_schema, Mapping):
                expected_type = prop_schema.get("type")
                if expected_type == "string":
                    if not isinstance(prop_val, str):
                        return False
                    max_len = prop_schema.get("maxLength")
                    if isinstance(max_len, int) and len(prop_val) > max_len:
                        return False
                    enum_vals = prop_schema.get("enum")
                    if isinstance(enum_vals, Sequence) and prop_val not in enum_vals:
                        return False
                elif expected_type == "boolean" and not isinstance(prop_val, bool):
                    return False
                elif expected_type == "integer" and (
                    not isinstance(prop_val, int) or isinstance(prop_val, bool)
                ):
                    return False
    return True


def validate_ucp_ap2_merchant_auth_and_declared_fields(
    *,
    operation: str,
    direction: str,
    ap2_active: bool,
    ap2_payload: Mapping[str, Any] | None = None,
    checkout_status: str = "incomplete",
    config: Mapping[str, Any] | None = None,
    checkout_required_declared_fields: Sequence[str] | None = None,
    checkout_declared_fields: Mapping[str, Any] | None = None,
    line_items: Sequence[Mapping[str, Any]] | None = None,
    payment: Mapping[str, Any] | None = None,
    fully_deferred_payment_term: bool = False,
) -> GuardDecision:
    """Validate UCP PR #466 (`ap2.merchant_authorization`), PR #915 (`declared_fields`), and PR #881 (`payment: {}`)."""
    if operation not in {"create", "update", "complete"}:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason="invalid_ucp_checkout_operation",
            details={"operation": operation},
        )

    items = list(line_items or [])

    if direction == "response" and ap2_active:
        if not isinstance(ap2_payload, Mapping):
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                reason="missing_ap2_object_in_active_response",
                details={"ap2_active": True},
            )
        merchant_auth = ap2_payload.get("merchant_authorization")
        if not isinstance(merchant_auth, str) or not merchant_auth.strip():
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                reason="missing_ap2_merchant_authorization_in_response",
                details={"ap2_keys": sorted(ap2_payload.keys())},
            )
        if not DETACHED_JWS_RE.match(merchant_auth):
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                reason="invalid_ap2_merchant_authorization_jws",
                details={"merchant_authorization": merchant_auth[:32]},
            )

    if direction == "request":
        if config is not None or checkout_required_declared_fields is not None:
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                reason="response_only_declared_field_config_sent_in_request",
                details={"operation": operation},
            )
        for idx, item in enumerate(items):
            if "required_declared_fields" in item:
                return GuardDecision(
                    allowed=False,
                    action="Send to a human",
                    reason="response_only_line_item_required_declared_fields_in_request",
                    details={"line_item_index": idx},
                )
        if operation == "complete":
            if checkout_declared_fields is not None or any(
                "declared_fields" in item for item in items
            ):
                return GuardDecision(
                    allowed=False,
                    action="Send to a human",
                    reason="declared_fields_must_be_omitted_on_complete",
                    details={"operation": "complete"},
                )
            if fully_deferred_payment_term:
                if payment is None or not isinstance(payment, Mapping) or len(payment) != 0:
                    return GuardDecision(
                        allowed=False,
                        action="Send to a human",
                        reason="deferred_payment_term_requires_empty_payment_object_on_complete",
                        details={"payment": dict(payment) if isinstance(payment, Mapping) else payment},
                    )

    config_map = dict(config or {})
    for key, schema_val in config_map.items():
        if not REVERSE_DNS_RE.match(key) or not isinstance(schema_val, Mapping):
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                reason="invalid_reverse_dns_key_or_schema_in_config",
                details={"key": key},
            )

    req_checkout = list(checkout_required_declared_fields or [])
    if len(req_checkout) != len(set(req_checkout)):
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason="duplicate_checkout_required_declared_fields",
            details={"required_declared_fields": req_checkout},
        )
    for key in req_checkout:
        if not REVERSE_DNS_RE.match(key) or key not in config_map:
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                reason="undeclared_config_reference_in_required_declared_fields",
                details={"scope": "checkout", "key": key},
            )

    sub_checkout = dict(checkout_declared_fields or {})
    for key, val in sub_checkout.items():
        if key not in req_checkout:
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                reason="declared_field_scope_mismatch_or_unknown_key",
                details={"scope": "checkout", "key": key},
            )
        if not _validate_simple_json_schema(val, config_map[key]):
            return GuardDecision(
                allowed=False,
                action="Confirm",
                reason="declared_field_schema_validation_failed",
                details={"scope": "checkout", "key": key},
            )

    for idx, item in enumerate(items):
        item_req = list(item.get("required_declared_fields") or [])
        if len(item_req) != len(set(item_req)):
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                reason="duplicate_line_item_required_declared_fields",
                details={"line_item_index": idx, "required_declared_fields": item_req},
            )
        for key in item_req:
            if not REVERSE_DNS_RE.match(key) or key not in config_map:
                return GuardDecision(
                    allowed=False,
                    action="Send to a human",
                    reason="undeclared_config_reference_in_required_declared_fields",
                    details={"scope": f"line_items[{idx}]", "key": key},
                )
        item_sub = dict(item.get("declared_fields") or {})
        for key, val in item_sub.items():
            if key not in item_req:
                return GuardDecision(
                    allowed=False,
                    action="Send to a human",
                    reason="declared_field_scope_mismatch_or_unknown_key",
                    details={"scope": f"line_items[{idx}]", "key": key},
                )
            if not _validate_simple_json_schema(val, config_map[key]):
                return GuardDecision(
                    allowed=False,
                    action="Confirm",
                    reason="declared_field_schema_validation_failed",
                    details={"scope": f"line_items[{idx}]", "key": key},
                )
        if checkout_status == "ready_for_complete":
            missing_item_keys = [k for k in item_req if k not in item_sub]
            if missing_item_keys:
                return GuardDecision(
                    allowed=False,
                    action="Confirm",
                    reason="missing_required_declared_field_blocks_ready_for_complete",
                    details={"scope": f"line_items[{idx}]", "missing_keys": missing_item_keys},
                )

    if checkout_status == "ready_for_complete":
        missing_checkout_keys = [k for k in req_checkout if k not in sub_checkout]
        if missing_checkout_keys:
            return GuardDecision(
                allowed=False,
                action="Confirm",
                reason="missing_required_declared_field_blocks_ready_for_complete",
                details={"scope": "checkout", "missing_keys": missing_checkout_keys},
            )

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        reason="ucp_ap2_merchant_auth_and_declared_fields_verified",
        details={
            "operation": operation,
            "direction": direction,
            "ap2_active": ap2_active,
            "checkout_declared_fields_count": len(sub_checkout),
        },
    )


def validate_x402_caip2_bazaar_opaque_origin_and_namespace_patterns(
    *,
    x402_version: int,
    network: str,
    resource_url: str,
    reported_canonical_url: str,
    route_template: str | None = None,
    registered_networks: Sequence[str] = (),
    derived_namespace_patterns: Mapping[str, str] | None = None,
    accepts_entries: Sequence[Mapping[str, Any]] = (),
    supported_schemes: Sequence[str] = ("exact",),
) -> GuardDecision:
    """Validate x402 PR #3878 (V2 CAIP-2), PR #3138 (Bazaar opaque origin), PR #3215 (per-namespace wildcards), and PR #2730 (accepts filtering)."""
    if x402_version == 2:
        if not isinstance(network, str) or not CAIP2_V2_NETWORK_RE.match(network):
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                reason="malformed_v2_caip2_network",
                details={"network": network, "x402_version": x402_version},
            )
    elif x402_version != 1 or not isinstance(network, str) or not network.strip():
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason="invalid_x402_version_or_network",
            details={"network": network, "x402_version": x402_version},
        )

    parsed = urlsplit(resource_url)
    if not parsed.scheme or not parsed.netloc:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason="invalid_bazaar_resource_url",
            details={"resource_url": resource_url},
        )
    origin_base = f"{parsed.scheme}://{parsed.netloc}"
    expected_canonical = f"{origin_base}{route_template if route_template is not None else parsed.path}"
    if (
        reported_canonical_url.startswith("null/")
        or "?" in reported_canonical_url
        or "#" in reported_canonical_url
        or reported_canonical_url != expected_canonical
    ):
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason="bazaar_opaque_origin_null_or_unstripped_canonical_url",
            details={
                "resource_url": resource_url,
                "reported_canonical_url": reported_canonical_url,
                "expected_canonical_url": expected_canonical,
                "is_opaque_origin": parsed.scheme.lower() not in WHATWG_SPECIAL_SCHEMES,
            },
        )

    if registered_networks:
        by_ns: dict[str, list[str]] = {}
        for reg_net in registered_networks:
            if ":" not in reg_net:
                return GuardDecision(
                    allowed=False,
                    action="Send to a human",
                    reason="invalid_registered_network_format",
                    details={"network": reg_net},
                )
            ns = reg_net.split(":", 1)[0]
            by_ns.setdefault(ns, []).append(reg_net)
        expected_patterns = {ns: f"{ns}:*" for ns in by_ns}
        provided_patterns = dict(derived_namespace_patterns or {})
        if provided_patterns != expected_patterns:
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                reason="mixed_namespace_wildcard_pattern_collapse",
                details={
                    "expected_patterns": expected_patterns,
                    "provided_patterns": provided_patterns,
                },
            )

    compatible_entries: list[Mapping[str, Any]] = []
    supported_set = set(supported_schemes)
    for entry in accepts_entries:
        entry_net = entry.get("network", "")
        entry_scheme = entry.get("scheme", "")
        entry_ver = entry.get("x402Version", x402_version)
        net_ok = (
            bool(CAIP2_V2_NETWORK_RE.match(entry_net))
            if entry_ver == 2
            else bool(isinstance(entry_net, str) and entry_net.strip())
        )
        if net_ok and entry_scheme in supported_set:
            compatible_entries.append(entry)

    if accepts_entries and not compatible_entries:
        return GuardDecision(
            allowed=False,
            action="Confirm",
            reason="no_compatible_payment_requirements_in_accepts",
            details={"total_accepts": len(accepts_entries)},
        )

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        reason="x402_caip2_bazaar_and_namespace_patterns_verified",
        details={
            "canonical_url": expected_canonical,
            "compatible_accepts_count": len(compatible_entries),
            "namespaces": sorted((derived_namespace_patterns or {}).keys()),
        },
    )


def validate_x402_correctness_dispute_bonded_verdict(
    *,
    verdict: str,
    resolver_id: str,
    resolver_version: str,
    criterion_id: str,
    evidence_digest: str,
    re_evaluation_procedure: str,
    signature_verified: bool,
    independent_criterion_re_evaluated: bool,
    claimed_correctness_verified: bool,
    slash_requested: bool,
    adjudicator_id: str,
    payer_id: str,
    payee_id: str,
    operation: str,
    receipt_digest: str,
    bound_only_by_payment_identifier: bool,
    live_onchain_balance: float,
    reserved_against_open_verdicts: float,
    per_verdict_max: float,
    outstanding_unslashed_obligations: int,
    unpaid_or_overdue_slash_obligations: float,
    payout_sla_committed: bool,
    presented_as_guaranteed_payout: bool,
) -> GuardDecision:
    """Validate x402 PR #3868 Correctness & Dispute Extension (bonded verdicts)."""
    if verdict not in VALID_VERDICT_OUTCOMES:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason="invalid_bonded_verdict_outcome",
            details={"verdict": verdict},
        )
    if not all(
        isinstance(v, str) and v.strip()
        for v in (
            resolver_id,
            resolver_version,
            criterion_id,
            evidence_digest,
            re_evaluation_procedure,
        )
    ):
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason="missing_resolver_or_criterion_metadata_in_verdict",
            details={"resolver_id": resolver_id, "criterion_id": criterion_id},
        )
    if not signature_verified:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason="unverified_verdict_signature_or_hash_preimage",
            details={"resolver_id": resolver_id},
        )
    if claimed_correctness_verified and not independent_criterion_re_evaluated:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason="signature_only_claimed_as_correctness_verification",
            details={
                "signature_verified": signature_verified,
                "independent_criterion_re_evaluated": independent_criterion_re_evaluated,
            },
        )
    if verdict == "INSUFFICIENT_DATA" and slash_requested:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason="insufficient_data_verdict_cannot_trigger_slash_or_refutation",
            details={"verdict": verdict},
        )
    if adjudicator_id == payee_id or adjudicator_id == payer_id:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason="self_adjudication_forbidden",
            details={"adjudicator_id": adjudicator_id, "payee_id": payee_id},
        )
    if (
        bound_only_by_payment_identifier
        or not payer_id.strip()
        or not payee_id.strip()
        or not operation.strip()
        or not receipt_digest.strip()
    ):
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason="dispute_must_bind_scoped_tuple_and_receipt_digest",
            details={
                "bound_only_by_payment_identifier": bound_only_by_payment_identifier,
                "receipt_digest": receipt_digest,
            },
        )
    if unpaid_or_overdue_slash_obligations > 0:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason="adjudicator_has_unpaid_or_overdue_slash_obligations",
            details={"unpaid_or_overdue_slash_obligations": unpaid_or_overdue_slash_obligations},
        )
    free_collateral = live_onchain_balance - reserved_against_open_verdicts
    max_coverable = free_collateral / max(1, outstanding_unslashed_obligations)
    if per_verdict_max <= 0 or free_collateral < per_verdict_max or per_verdict_max > max_coverable:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason="per_verdict_max_exceeds_unreserved_onchain_collateral",
            details={
                "per_verdict_max": per_verdict_max,
                "free_collateral": free_collateral,
                "max_coverable": max_coverable,
            },
        )
    if presented_as_guaranteed_payout and not payout_sla_committed:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason="uncommitted_payout_sla_presented_as_guarantee",
            details={"payout_sla_committed": payout_sla_committed},
        )

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        reason="x402_bonded_verdict_and_collateral_verified",
        details={
            "verdict": verdict,
            "per_verdict_max": per_verdict_max,
            "free_collateral": free_collateral,
        },
    )


def validate_mcp_language_negotiation_type_constraints_and_client_config(
    *,
    request_meta: Mapping[str, Any] | None = None,
    http_accept_language_headers: Sequence[str] | None = None,
    response_meta: Mapping[str, Any] | None = None,
    http_content_language_header: str | None = None,
    persisted_session_language_used: bool = False,
    non_language_locale_inferred: bool = False,
    machine_identifier_translated: bool = False,
    explicit_tool_language_arg: str | None = None,
    effective_content_language: str | None = None,
    schema_check: Mapping[str, Any] | None = None,
    mcp_json_config: Mapping[str, Any] | None = None,
) -> GuardDecision:
    """Validate MCP SEP-2792 (language negotiation), SEP-2778 (type constraints), and SEP-2633 (`mcp.json`)."""
    req_meta = dict(request_meta or {})
    resp_meta = dict(response_meta or {})
    meta_accept = req_meta.get(MCP_ACCEPT_LANGUAGE_KEY)

    if persisted_session_language_used:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason="mcp_accept_language_must_not_persist_across_session",
            details={"persisted_session_language_used": True},
        )
    if non_language_locale_inferred:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason="mcp_accept_language_must_not_infer_currency_or_timezone_locale",
            details={"non_language_locale_inferred": True},
        )
    if machine_identifier_translated:
        return GuardDecision(
            allowed=False,
            action="Send to a human",
            reason="mcp_machine_identifier_translation_forbidden",
            details={"machine_identifier_translated": True},
        )

    if http_accept_language_headers is not None and len(http_accept_language_headers) > 0:
        combined_http_accept = ", ".join(http_accept_language_headers)
        if meta_accept is None:
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                reason="bare_http_accept_language_without_canonical_meta",
                details={"http_accept_language": combined_http_accept},
            )
        if len(http_accept_language_headers) > 1 or combined_http_accept != meta_accept:
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                reason="mcp_accept_language_header_mismatch_minus_32020",
                details={
                    "error_code": -32020,
                    "meta_accept_language": meta_accept,
                    "http_accept_language": combined_http_accept,
                    "header_line_count": len(http_accept_language_headers),
                },
            )

    meta_content_lang = resp_meta.get(MCP_CONTENT_LANGUAGE_KEY)
    if meta_content_lang is not None and http_content_language_header is not None:
        if meta_content_lang != http_content_language_header:
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                reason="mcp_content_language_header_mirror_mismatch",
                details={
                    "meta_content_language": meta_content_lang,
                    "http_content_language": http_content_language_header,
                },
            )

    if (
        explicit_tool_language_arg is not None
        and effective_content_language is not None
        and effective_content_language != explicit_tool_language_arg
    ):
        return GuardDecision(
            allowed=False,
            action="Confirm",
            reason="explicit_tool_language_argument_must_override_accept_language",
            details={
                "explicit_tool_language_arg": explicit_tool_language_arg,
                "effective_content_language": effective_content_language,
            },
        )

    if schema_check is not None:
        icon_src = schema_check.get("icon_src")
        if icon_src is not None and (
            len(icon_src) > 8192 or not MCP_ICON_SRC_RE.match(icon_src)
        ):
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                reason="mcp_sep2778_invalid_icon_src_scheme_or_length",
                details={"icon_src": icon_src[:64]},
            )
        root_uri = schema_check.get("root_uri")
        if root_uri is not None and (
            len(root_uri) > 8192 or not str(root_uri).startswith("file://")
        ):
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                reason="mcp_sep2778_root_uri_must_use_file_scheme",
                details={"root_uri": str(root_uri)[:64]},
            )
        elicit_url = schema_check.get("elicit_url")
        elicit_id = schema_check.get("elicitation_id")
        if elicit_url is not None:
            if (
                not str(elicit_url).startswith("https://")
                or not isinstance(elicit_id, str)
                or not (1 <= len(elicit_id) <= 256)
            ):
                return GuardDecision(
                    allowed=False,
                    action="Send to a human",
                    reason="mcp_sep2778_invalid_elicit_url_or_missing_elicitation_id",
                    details={"elicit_url": elicit_url, "elicitation_id": elicit_id},
                )
        identifier = schema_check.get("identifier")
        if identifier is not None and len(str(identifier)) > 256:
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                reason="mcp_sep2778_identifier_exceeds_256_chars",
                details={"identifier_length": len(str(identifier))},
            )
        cursor = schema_check.get("cursor")
        if cursor is not None and len(str(cursor)) > 8192:
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                reason="mcp_sep2778_cursor_exceeds_8192_chars",
                details={"cursor_length": len(str(cursor))},
            )
        ttl_ms = schema_check.get("ttl_ms")
        if ttl_ms is not None and (not isinstance(ttl_ms, int) or ttl_ms < 0 or ttl_ms > 86400000):
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                reason="mcp_sep2778_ttl_ms_out_of_24h_bounds",
                details={"ttl_ms": ttl_ms},
            )

    if mcp_json_config is not None:
        if set(mcp_json_config.keys()) != {"mcpServers"} or not isinstance(
            mcp_json_config.get("mcpServers"), Mapping
        ):
            return GuardDecision(
                allowed=False,
                action="Send to a human",
                reason="mcp_sep2633_invalid_top_level_mcp_servers_key",
                details={"keys": sorted(mcp_json_config.keys())},
            )
        for srv_name, srv_cfg in mcp_json_config["mcpServers"].items():
            if not MCP_SERVER_NAME_RE.match(str(srv_name)) or not isinstance(
                srv_cfg, Mapping
            ):
                return GuardDecision(
                    allowed=False,
                    action="Send to a human",
                    reason="mcp_sep2633_invalid_server_name",
                    details={"server_name": srv_name},
                )
            transport_type = srv_cfg.get("type")
            if transport_type not in {"stdio", "sse", "streamable-http"}:
                return GuardDecision(
                    allowed=False,
                    action="Send to a human",
                    reason="mcp_sep2633_invalid_transport_type",
                    details={"server_name": srv_name, "type": transport_type},
                )
            if transport_type == "stdio":
                if not srv_cfg.get("command") or any(
                    k in srv_cfg for k in ("url", "headers", "oauth")
                ):
                    return GuardDecision(
                        allowed=False,
                        action="Send to a human",
                        reason="mcp_sep2633_stdio_transport_field_violation",
                        details={"server_name": srv_name},
                    )
                for arg in srv_cfg.get("args", []):
                    if str(arg).endswith("@latest") or str(arg).endswith(":latest"):
                        return GuardDecision(
                            allowed=False,
                            action="Confirm",
                            reason="mcp_sep2633_unpinned_stdio_package_version",
                            details={"server_name": srv_name, "arg": arg},
                        )
            else:
                if not srv_cfg.get("url") or any(
                    k in srv_cfg for k in ("command", "args", "env")
                ):
                    return GuardDecision(
                        allowed=False,
                        action="Send to a human",
                        reason="mcp_sep2633_remote_transport_field_violation",
                        details={"server_name": srv_name},
                    )
                headers = srv_cfg.get("headers") or {}
                has_auth_header = any(
                    str(k).lower() == "authorization" for k in headers.keys()
                )
                if "oauth" in srv_cfg and has_auth_header:
                    return GuardDecision(
                        allowed=False,
                        action="Send to a human",
                        reason="mcp_sep2633_oauth_and_authorization_header_conflict",
                        details={"server_name": srv_name},
                    )
            for env_Or_hdr_map in (srv_cfg.get("env") or {}, srv_cfg.get("headers") or {}):
                for k, v in env_Or_hdr_map.items():
                    matches = MCP_SECRET_INTERP_RE.findall(str(v))
                    for scheme, _ in matches:
                        if scheme not in ALLOWED_SECRET_SCHEMES:
                            return GuardDecision(
                                allowed=False,
                                action="Send to a human",
                                reason="mcp_sep2633_unsupported_secret_interpolation_scheme",
                                details={"server_name": srv_name, "key": k, "scheme": scheme},
                            )

    return GuardDecision(
        allowed=True,
        action="Act automatically",
        reason="mcp_sep2792_sep2778_sep2633_verified",
        details={
            "accept_language": meta_accept,
            "content_language": meta_content_lang,
        },
    )
