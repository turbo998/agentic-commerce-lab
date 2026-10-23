"""Stage 222 deterministic guard evaluators across MCP Inspector, MCP Registry,
and MCP Go, Rust, C#, and Java SDKs (`PR-01` .. `PR-16`).

Covers 34 primary-source pull requests across `modelcontextprotocol/inspector`,
`modelcontextprotocol/registry`, `modelcontextprotocol/go-sdk`,
`modelcontextprotocol/rust-sdk`, `modelcontextprotocol/csharp-sdk`, and
`modelcontextprotocol/java-sdk`.
"""

from __future__ import annotations

import copy
import json
import re
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import quote, urlparse

STAGE_222_PR_IDS: tuple[str, ...] = tuple(f"PR-{i:02d}" for i in range(1, 17))

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_TOKEN_RE = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")
_SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _res(
    pr_id: str,
    passed: bool,
    reason_code: str,
    detail: str,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "pr_id": pr_id,
        "passed": bool(passed),
        "action": "allow" if passed else "block",
        "reason_code": reason_code,
        "detail": detail,
        "evidence": evidence or {},
    }


# ---------------------------------------------------------------------------
# PR-01: modelcontextprotocol/inspector#2777 & #2774
# ---------------------------------------------------------------------------
def evaluate_inspector_refusal_and_oversize_relay_guard(payload: dict[str, Any]) -> dict[str, Any]:
    """Verify request POST HTTP-refusal keeps session connected (#2777) and
    oversize error relay strips dropped-body framing headers (#2774).
    """
    pr_id = "PR-01"
    is_request_post_refusal = bool(payload.get("is_request_post_refusal", True))
    request_method = str(payload.get("request_method", "subscriptions/listen"))
    http_status = int(payload.get("http_status", 403))
    connection_status_after_onerror = str(payload.get("connection_status_after_onerror", "connected"))
    request_promise_rejected = bool(payload.get("request_promise_rejected", True))

    if is_request_post_refusal and http_status in (401, 403, 404, 405):
        if connection_status_after_onerror != "connected" or not request_promise_rejected:
            return _res(
                pr_id,
                False,
                "INSPECTOR_REQUEST_REFUSAL_DROPPED_CONNECTION",
                "Per-request HTTP refusal (e.g. subscriptions/listen 403) must reject the request without setting connection status to error",
                {
                    "request_method": request_method,
                    "http_status": http_status,
                    "connection_status_after_onerror": connection_status_after_onerror,
                },
            )

    oversize_error_relay = bool(payload.get("oversize_error_relay", True))
    upstream_status = int(payload.get("upstream_status", 404))
    body_dropped = bool(payload.get("body_dropped", True))
    relayed_headers = {str(k).lower(): str(v) for k, v in (payload.get("relayed_headers") or {}).items()}
    framing_headers = {"content-length", "transfer-encoding", "content-encoding"}
    leaked_framing = sorted(framing_headers.intersection(relayed_headers.keys()))

    if oversize_error_relay and upstream_status >= 400 and body_dropped and leaked_framing:
        return _res(
            pr_id,
            False,
            "INSPECTOR_OVERSIZE_ERROR_RELAY_FRAMING_HEADER_LEAK",
            "Oversize error relay with dropped body must strip content-length, transfer-encoding, and content-encoding headers",
            {"upstream_status": upstream_status, "leaked_framing": leaked_framing},
        )

    return _res(
        pr_id,
        True,
        "INSPECTOR_REFUSAL_AND_OVERSIZE_RELAY_SAFE",
        "Inspector keeps connection up on per-request HTTP refusal and strips framing headers on oversize error relay",
        {
            "connection_status_after_onerror": connection_status_after_onerror,
            "leaked_framing": leaked_framing,
        },
    )


# ---------------------------------------------------------------------------
# PR-02: modelcontextprotocol/inspector#2775, #2773, & #2747
# ---------------------------------------------------------------------------
def evaluate_inspector_mcpdo_tls_handoff_and_skills_cache_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Verify mcpdo resources/directory/read URI+cursor registration (#2775),
    TLS --print-handoff deep-link scheme (#2773), and modern CacheableResult
    ttlMs + cacheScope validation (#2747).
    """
    pr_id = "PR-02"
    uri = str(payload.get("directory_uri") or "").strip()
    cursor_supported = bool(payload.get("cursor_option_supported", True))
    if not uri or not cursor_supported:
        return _res(
            pr_id,
            False,
            "INSPECTOR_MCPDO_DIRECTORY_READ_URI_OR_CURSOR_MISSING",
            "mcpdo resources/directory/read must accept a required URI and optional --cursor pagination",
            {"directory_uri": uri, "cursor_option_supported": cursor_supported},
        )

    tls_key_path = str(payload.get("tls_key_path") or "").strip()
    tls_cert_path = str(payload.get("tls_cert_path") or "").strip()
    handoff_url = str(payload.get("handoff_url") or "")
    expected_scheme = "https" if (tls_key_path and tls_cert_path) else "http"
    parsed_handoff = urlparse(handoff_url)
    if parsed_handoff.scheme != expected_scheme:
        return _res(
            pr_id,
            False,
            "INSPECTOR_PRINT_HANDOFF_TLS_SCHEME_MISMATCH",
            "buildHandoff must use https iff both INSPECTOR_TLS_KEY_PATH and INSPECTOR_TLS_CERT_PATH are non-blank",
            {
                "expected_scheme": expected_scheme,
                "actual_scheme": parsed_handoff.scheme,
                "tls_key_set": bool(tls_key_path),
                "tls_cert_set": bool(tls_cert_path),
            },
        )

    negotiated_era = str(payload.get("negotiated_era", "2026-07-28"))
    dir_result = payload.get("directory_read_result") or {}
    if negotiated_era >= "2026-07-28":
        ttl_ms = dir_result.get("ttlMs")
        cache_scope = dir_result.get("cacheScope")
        if (
            not isinstance(ttl_ms, int)
            or isinstance(ttl_ms, bool)
            or ttl_ms < 0
            or cache_scope not in ("private", "public")
        ):
            return _res(
                pr_id,
                False,
                "INSPECTOR_MODERN_DIRECTORY_READ_CACHEABLE_FIELDS_MISSING",
                "Modern (2026-07-28+) resources/directory/read results must carry non-negative integer ttlMs and cacheScope",
                {"ttlMs": ttl_ms, "cacheScope": cache_scope},
            )

    return _res(
        pr_id,
        True,
        "INSPECTOR_MCPDO_TLS_HANDOFF_AND_SKILLS_CACHE_VALID",
        "mcpdo directory read URI/cursor, TLS handoff scheme, and modern CacheableResult fields verified",
        {
            "directory_uri": uri,
            "handoff_scheme": parsed_handoff.scheme,
            "cacheScope": dir_result.get("cacheScope"),
        },
    )


# ---------------------------------------------------------------------------
# PR-03: modelcontextprotocol/inspector#2742 & #2739
# ---------------------------------------------------------------------------
def evaluate_inspector_pkce_flow_store_and_secret_stamp_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Verify in-flight PKCE verifiers are keyed by 64-hex flow authId (#2742)
    and client credentials carry only for the client named by their store stamp (#2739).
    """
    pr_id = "PR-03"
    pkce_key_mode = str(payload.get("pkce_key_mode", "flow_auth_id"))
    concurrent_flows = payload.get("concurrent_flows") or []
    if pkce_key_mode != "flow_auth_id" or not concurrent_flows:
        return _res(
            pr_id,
            False,
            "INSPECTOR_PKCE_SHARED_SERVER_URL_SLOT_COLLISION",
            "In-flight PKCE codeVerifier must be keyed by 64-hex OAuth flow authId in sessionStorage, not shared serverUrl",
            {"pkce_key_mode": pkce_key_mode},
        )

    seen_auth_ids: set[str] = set()
    for flow in concurrent_flows:
        auth_id = str(flow.get("auth_id") or "")
        verifier = str(flow.get("code_verifier") or "")
        overwritten = bool(flow.get("verifier_overwritten", False))
        if not _HEX64_RE.match(auth_id) or not verifier or auth_id in seen_auth_ids or overwritten:
            return _res(
                pr_id,
                False,
                "INSPECTOR_PKCE_FLOW_VERIFIER_OVERWRITTEN",
                "Each concurrent OAuth flow must preserve its own 64-hex authId and isolated PKCE codeVerifier",
                {"auth_id": auth_id, "verifier_overwritten": overwritten},
            )
        seen_auth_ids.add(auth_id)

    secret_stamp_client_id = str(payload.get("secret_stamp_client_id") or "")
    active_client_id = str(payload.get("active_client_id") or "")
    carried_secret_used = bool(payload.get("carried_secret_used", False))
    if carried_secret_used and secret_stamp_client_id != active_client_id:
        return _res(
            pr_id,
            False,
            "INSPECTOR_CLIENT_SECRET_STAMP_MISMATCH",
            "Carried client credential secret must only be used when its store stamp matches the active client_id",
            {
                "secret_stamp_client_id": secret_stamp_client_id,
                "active_client_id": active_client_id,
            },
        )

    return _res(
        pr_id,
        True,
        "INSPECTOR_PKCE_FLOW_AND_SECRET_STAMP_SAFE",
        "Concurrent OAuth PKCE verifiers isolated by 64-hex authId and client secret carry verified by owner stamp",
        {"flow_count": len(seen_auth_ids), "active_client_id": active_client_id},
    )


# ---------------------------------------------------------------------------
# PR-04: modelcontextprotocol/inspector#2738, #2737, & #2736
# ---------------------------------------------------------------------------
def _parse_retry_after(raw_val: str | None, now_epoch_ms: int) -> tuple[bool, int | None]:
    if raw_val is None:
        return True, None
    s = raw_val.strip()
    if not s:
        return False, None
    if re.fullmatch(r"\d+", s):
        return True, int(s) * 1000
    if re.fullmatch(r"-\d+", s):
        return False, None
    try:
        dt = parsedate_to_datetime(s)
        delta_ms = max(0, int(dt.timestamp() * 1000) - now_epoch_ms)
        return True, delta_ms
    except Exception:
        return False, None


def evaluate_inspector_insufficient_scope_refresh_429_and_ema_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Verify 403 insufficient_scope checks token expiry before treating challenge
    as satisfied (#2738), HTTP 429 parses Retry-After safely (#2737), and EMA
    allows public resource-AS clients in leg 3 (#2736).
    """
    pr_id = "PR-04"
    challenge_error = str(payload.get("challenge_error", "insufficient_scope"))
    scopes_covered = bool(payload.get("scopes_covered", True))
    token_unexpired = bool(payload.get("is_access_token_provably_unexpired", False))
    challenge_satisfied = bool(payload.get("challenge_marked_satisfied", False))
    refresh_attempted = bool(payload.get("refresh_attempted", True))

    if challenge_error == "insufficient_scope" and scopes_covered and not token_unexpired:
        if challenge_satisfied or not refresh_attempted:
            return _res(
                pr_id,
                False,
                "INSPECTOR_EXPIRED_TOKEN_REPLAYED_ON_INSUFFICIENT_SCOPE",
                "403 insufficient_scope with an expired token must not be marked satisfied; it must trigger token refresh",
                {
                    "challenge_marked_satisfied": challenge_satisfied,
                    "refresh_attempted": refresh_attempted,
                },
            )

    now_ms = int(payload.get("now_epoch_ms", 1792800000000))
    retry_after_raw = payload.get("retry_after_header")
    parsed_retry_ms = payload.get("annotated_retry_after_ms")
    valid_ra, expected_ms = _parse_retry_after(retry_after_raw, now_ms)
    if not valid_ra and parsed_retry_ms is not None:
        return _res(
            pr_id,
            False,
            "INSPECTOR_MALFORMED_RETRY_AFTER_MISPARSED_AS_DATE",
            "Negative or malformed Retry-After header (e.g. '-5') must not be trusted via Date.parse as a year",
            {"retry_after_header": retry_after_raw, "annotated_retry_after_ms": parsed_retry_ms},
        )
    if valid_ra and expected_ms is not None and parsed_retry_ms != expected_ms:
        return _res(
            pr_id,
            False,
            "INSPECTOR_RETRY_AFTER_MS_MISMATCH",
            "Valid Retry-After header must produce accurate retryAfterMs in AnnotatedRateLimitData",
            {"expected_ms": expected_ms, "annotated_retry_after_ms": parsed_retry_ms},
        )

    ema_resource_client_id = str(payload.get("ema_resource_client_id") or "").strip()
    ema_resource_client_secret = str(payload.get("ema_resource_client_secret") or "")
    ema_leg3_auth_method = str(payload.get("ema_leg3_token_endpoint_auth_method") or "")
    ema_threw_missing_secret = bool(payload.get("ema_threw_missing_secret", False))
    if ema_resource_client_id and ema_resource_client_secret == "":
        if ema_threw_missing_secret or ema_leg3_auth_method != "none":
            return _res(
                pr_id,
                False,
                "INSPECTOR_EMA_PUBLIC_RESOURCE_CLIENT_REJECTED",
                "EMA leg 3 must allow an empty resourceClientSecret for public clients using token_endpoint_auth_method='none'",
                {
                    "ema_threw_missing_secret": ema_threw_missing_secret,
                    "ema_leg3_token_endpoint_auth_method": ema_leg3_auth_method,
                },
            )

    return _res(
        pr_id,
        True,
        "INSPECTOR_INSUFFICIENT_SCOPE_429_AND_EMA_VALID",
        "Expired token refresh on 403 insufficient_scope, HTTP 429 Retry-After parsing, and EMA public client leg 3 verified",
        {
            "refresh_attempted": refresh_attempted,
            "annotated_retry_after_ms": parsed_retry_ms,
            "ema_leg3_auth_method": ema_leg3_auth_method,
        },
    )


# ---------------------------------------------------------------------------
# PR-05: modelcontextprotocol/registry#1730, #1726, & #1702
# ---------------------------------------------------------------------------
def evaluate_registry_trigram_backup_and_nested_publish_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Verify pg_trgm GIN index readiness (#1730), verifiable pg_dump+SHA256+Restic
    backup pipeline (#1726), and nested **/server.json publish PR rejection (#1702).
    """
    pr_id = "PR-05"
    index_valid = bool(payload.get("trigram_index_indisvalid", True))
    index_ready = bool(payload.get("trigram_index_indisready", True))
    if not index_valid or not index_ready:
        return _res(
            pr_id,
            False,
            "REGISTRY_TRIGRAM_INDEX_INVALID_OR_UNREADY",
            "Migration 015 must reject invalid or unready idx_servers_name_trgm GIN trigram indexes",
            {"indisvalid": index_valid, "indisready": index_ready},
        )

    backup = payload.get("backup_job") or {}
    if (
        backup.get("pg_dump_format") != "custom"
        or backup.get("pg_dump_compress") != 0
        or not bool(backup.get("sha256_verified", False))
        or not bool(backup.get("restic_check_read_data", False))
        or int(backup.get("snapshot_retention_days", 0)) < 28
    ):
        return _res(
            pr_id,
            False,
            "REGISTRY_BACKUP_UNVERIFIED_OR_COMPRESSED_BEFORE_DEDUP",
            "Registry backup job requires pg_dump --format=custom --compress=0, SHA-256 verification, restic check --read-data, and >=28 daily snapshots",
            {"backup_job": backup},
        )

    pr_files = [str(p).replace("\\", "/") for p in (payload.get("pr_changed_files") or [])]
    pr_blocked = bool(payload.get("invalid_publish_pr_blocked", False))
    has_nested_server_json = any(
        p == "server.json" or p.endswith("/server.json") for p in pr_files
    )
    if has_nested_server_json and not pr_blocked:
        return _res(
            pr_id,
            False,
            "REGISTRY_NESTED_SERVER_JSON_PR_NOT_BLOCKED",
            "PRs adding server.json at root or any nested path (**/server.json) must be detected and auto-closed with mcp-publisher guidance",
            {"pr_changed_files": pr_files},
        )

    return _res(
        pr_id,
        True,
        "REGISTRY_TRIGRAM_BACKUP_AND_PUBLISH_GUARD_VALID",
        "Registry pg_trgm index validity, verifiable Restic/pg_dump backup, and **/server.json PR guard verified",
        {"has_nested_server_json": has_nested_server_json, "invalid_publish_pr_blocked": pr_blocked},
    )


# ---------------------------------------------------------------------------
# PR-06: modelcontextprotocol/go-sdk#1439 & #1412
# ---------------------------------------------------------------------------
def _parse_whatwg_sse_field_value(raw_after_colon: str) -> str:
    if raw_after_colon.startswith(" "):
        return raw_after_colon[1:]
    return raw_after_colon


def evaluate_go_sdk_sse_non_message_skip_and_field_spacing_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Verify SSEClientTransport skips non-message/empty events (#1439) and
    scanEventsLimited strips at most one leading U+0020 SPACE per WHATWG SSE (#1412).
    """
    pr_id = "PR-06"
    sse_events = payload.get("sse_events") or []
    forwarded_payloads = payload.get("forwarded_to_jsonrpc_reader") or []
    expected_forwarded: list[str] = []
    for ev in sse_events:
        ev_name = str(ev.get("event") or "")
        ev_data = str(ev.get("data") or "")
        if ev_name in ("", "message") and ev_data != "":
            expected_forwarded.append(ev_data)

    if forwarded_payloads != expected_forwarded:
        return _res(
            pr_id,
            False,
            "GO_SDK_SSE_NON_MESSAGE_OR_EMPTY_EVENT_FORWARDED",
            "SSEClientTransport must only forward SSE events with event in ('', 'message') and non-empty data",
            {"expected": expected_forwarded, "actual": forwarded_payloads},
        )

    raw_after_colon = str(payload.get("raw_field_after_colon", "  1}"))
    parsed_value = str(payload.get("parsed_field_value", " 1}"))
    expected_value = _parse_whatwg_sse_field_value(raw_after_colon)
    if parsed_value != expected_value:
        return _res(
            pr_id,
            False,
            "GO_SDK_SSE_FIELD_WHITESPACE_OVERTRIMMED",
            "SSE field parser must remove at most one leading U+0020 SPACE and preserve remaining leading/trailing spaces",
            {"raw_after_colon": raw_after_colon, "expected": expected_value, "actual": parsed_value},
        )

    return _res(
        pr_id,
        True,
        "GO_SDK_SSE_EVENT_FILTER_AND_SPACING_VALID",
        "Go SDK SSEClientTransport non-message skip and WHATWG single-space trimming verified",
        {"forwarded_count": len(forwarded_payloads), "parsed_field_value": parsed_value},
    )


# ---------------------------------------------------------------------------
# PR-07: modelcontextprotocol/go-sdk#1435 & #1427
# ---------------------------------------------------------------------------
def evaluate_go_sdk_dcr_jwks_and_resource_not_found_json_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Verify RFC 7591 client metadata jwks object/string JSON marshaling (#1435)
    and ResourceNotFoundError valid JSON marshaling for DEL/emoji URIs (#1427).
    """
    pr_id = "PR-07"
    jwks_wire = payload.get("jwks_wire_value")
    dcr_accepted = bool(payload.get("dcr_unmarshal_accepted", True))
    jwks_valid_type = jwks_wire is None or isinstance(jwks_wire, (dict, str))
    if jwks_valid_type != dcr_accepted:
        return _res(
            pr_id,
            False,
            "GO_SDK_DCR_JWKS_METADATA_CODEC_MISMATCH",
            "ClientRegistrationMetadata.JWKS must accept JSON object, JSON string, or null and reject other JSON types",
            {"jwks_wire_value": jwks_wire, "dcr_unmarshal_accepted": dcr_accepted},
        )

    resource_uri = str(payload.get("unregistered_resource_uri", "file:///tmp/del-\x7f-flag-\U0001f3f4\U000e0067"))
    error_data_raw = str(payload.get("error_data_json") or "")
    session_stayed_open = bool(payload.get("session_alive_after_error", True))
    try:
        parsed_err = json.loads(error_data_raw)
        roundtrip_ok = isinstance(parsed_err, dict) and parsed_err.get("uri") == resource_uri
    except Exception:
        roundtrip_ok = False

    if not roundtrip_ok or not session_stayed_open:
        return _res(
            pr_id,
            False,
            "GO_SDK_RESOURCE_NOT_FOUND_INVALID_JSON_ESCAPE",
            "ResourceNotFoundError must marshal error data with json.Marshal instead of fmt.Sprintf('%q') so DEL/emoji URIs do not break the session",
            {"error_data_raw": error_data_raw, "session_alive_after_error": session_stayed_open},
        )

    return _res(
        pr_id,
        True,
        "GO_SDK_DCR_JWKS_AND_RESOURCE_ERROR_JSON_VALID",
        "Go SDK RFC 7591 jwks metadata codec and ResourceNotFoundError JSON marshaling verified",
        {"roundtrip_uri_len": len(resource_uri)},
    )


# ---------------------------------------------------------------------------
# PR-08: modelcontextprotocol/go-sdk#1432, #1419, & #1418
# ---------------------------------------------------------------------------
def evaluate_go_sdk_token_source_dcr_reuse_and_static_reauth_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Verify detached TokenSource context + mutex (#1432), issuer-keyed DCR
    client reuse across authorizations (#1419), and StaticTokenSource fallback
    when refresh_token is absent (#1418).
    """
    pr_id = "PR-08"
    token_source_bound_to_authorize_ctx = bool(payload.get("token_source_bound_to_authorize_ctx", False))
    token_source_mutex_guarded = bool(payload.get("token_source_mutex_guarded", True))
    if token_source_bound_to_authorize_ctx or not token_source_mutex_guarded:
        return _res(
            pr_id,
            False,
            "GO_SDK_EXTAUTH_TOKEN_SOURCE_CTX_OR_RACE_FAULT",
            "extauth handlers must detach TokenSource from the short-lived Authorize ctx and guard concurrent access with a mutex",
            {
                "token_source_bound_to_authorize_ctx": token_source_bound_to_authorize_ctx,
                "token_source_mutex_guarded": token_source_mutex_guarded,
            },
        )

    auth_events = int(payload.get("authorization_events_for_same_issuer", 2))
    dcr_registrations = int(payload.get("dcr_registrations_performed", 1))
    if auth_events >= 1 and dcr_registrations != 1:
        return _res(
            pr_id,
            False,
            "GO_SDK_DUPLICATE_DCR_CLIENT_REGISTRATION",
            "AuthorizationCodeHandler must reuse the dynamically registered client keyed by issuer across step-up and re-authorization flows",
            {
                "authorization_events_for_same_issuer": auth_events,
                "dcr_registrations_performed": dcr_registrations,
            },
        )

    has_refresh_token = bool(payload.get("has_refresh_token", False))
    token_source_kind = str(payload.get("token_source_kind", "StaticTokenSource"))
    reauthorized_on_401 = bool(payload.get("reauthorized_after_expiry_401", True))
    if not has_refresh_token and (token_source_kind != "StaticTokenSource" or not reauthorized_on_401):
        return _res(
            pr_id,
            False,
            "GO_SDK_REFRESHLESS_TOKEN_EXPIRY_DEADLOCK",
            "When token response omits refresh_token, handler must use StaticTokenSource so expiry triggers a 401 and re-authorization",
            {"token_source_kind": token_source_kind, "reauthorized_after_expiry_401": reauthorized_on_401},
        )

    return _res(
        pr_id,
        True,
        "GO_SDK_TOKEN_SOURCE_DCR_REUSE_AND_REAUTH_VALID",
        "Go SDK detached TokenSource lifetime, issuer-keyed DCR client reuse, and refreshless StaticTokenSource re-auth verified",
        {"dcr_registrations_performed": dcr_registrations, "token_source_kind": token_source_kind},
    )


# ---------------------------------------------------------------------------
# PR-09: modelcontextprotocol/go-sdk#1428 & #1414
# ---------------------------------------------------------------------------
def evaluate_go_sdk_discover_export_and_single_get_server_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Verify exported ClientSession.Discover (#1428) and single getServer
    callback invocation per Streamable HTTP POST (#1414).
    """
    pr_id = "PR-09"
    cs_discover_exported = bool(payload.get("client_session_discover_exported", True))
    discover_method_sent = str(payload.get("discover_method_sent", "server/discover"))
    if not cs_discover_exported or discover_method_sent != "server/discover":
        return _res(
            pr_id,
            False,
            "GO_SDK_CLIENT_SESSION_DISCOVER_MISSING",
            "ClientSession.Discover must be exported and send 'server/discover'",
            {
                "client_session_discover_exported": cs_discover_exported,
                "discover_method_sent": discover_method_sent,
            },
        )

    post_requests = int(payload.get("new_session_post_requests", 1))
    get_server_calls = int(payload.get("get_server_invocations", 1))
    if get_server_calls != post_requests:
        return _res(
            pr_id,
            False,
            "GO_SDK_DUPLICATE_GET_SERVER_INVOCATION",
            "Streamable HTTP session creation must reuse the Server selected for protocol-version validation (1 getServer call per POST)",
            {"new_session_post_requests": post_requests, "get_server_invocations": get_server_calls},
        )

    return _res(
        pr_id,
        True,
        "GO_SDK_DISCOVER_AND_SINGLE_GET_SERVER_VALID",
        "ClientSession.Discover export and single getServer invocation per POST verified",
        {"get_server_invocations": get_server_calls},
    )


# ---------------------------------------------------------------------------
# PR-10: modelcontextprotocol/rust-sdk#1386 & #1363
# ---------------------------------------------------------------------------
def evaluate_rust_sdk_http_status_error_and_sse_terminal_reconnect_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Verify body-free HttpStatusError with <=128-byte UTF-8 Retry-After and
    JSON 5xx RPC error preservation (#1386), plus terminal SSE GET reconnect
    classification on 401/403/405 (#1363).
    """
    pr_id = "PR-10"
    retry_after_bytes = int(payload.get("retained_retry_after_bytes", 16))
    retained_body_or_creds = bool(payload.get("retained_body_or_credentials_in_status_error", False))
    json_5xx_forwarded_as_rpc = bool(payload.get("json_5xx_post_forwarded_as_jsonrpc_error", True))

    if retry_after_bytes > 128 or retained_body_or_creds or not json_5xx_forwarded_as_rpc:
        return _res(
            pr_id,
            False,
            "RUST_SDK_HTTP_STATUS_ERROR_METADATA_VIOLATION",
            "HttpStatusError must cap Retry-After at 128 UTF-8 bytes, retain no body/URL/credentials, and preserve JSON 5xx RPC errors",
            {
                "retained_retry_after_bytes": retry_after_bytes,
                "retained_body_or_credentials_in_status_error": retained_body_or_creds,
                "json_5xx_post_forwarded_as_jsonrpc_error": json_5xx_forwarded_as_rpc,
            },
        )

    sse_get_error = str(payload.get("sse_reconnect_error_kind", "ServerDoesNotSupportSse"))
    reconnect_attempts_after_error = int(payload.get("reconnect_attempts_after_terminal_error", 0))
    terminal_kinds = {"ServerDoesNotSupportSse", "AuthRequired", "InsufficientScope"}
    if sse_get_error in terminal_kinds and reconnect_attempts_after_error > 0:
        return _res(
            pr_id,
            False,
            "RUST_SDK_INFINITE_SSE_RECONNECT_ON_TERMINAL_GET_ERROR",
            "SSE GET reconnect must stop immediately after yielding ServerDoesNotSupportSse (405), AuthRequired (401), or InsufficientScope (403)",
            {
                "sse_reconnect_error_kind": sse_get_error,
                "reconnect_attempts_after_terminal_error": reconnect_attempts_after_error,
            },
        )

    return _res(
        pr_id,
        True,
        "RUST_SDK_HTTP_STATUS_AND_SSE_RECONNECT_VALID",
        "Rust SDK body-free HttpStatusError metadata and terminal SSE GET reconnect classification verified",
        {"sse_reconnect_error_kind": sse_get_error, "retained_retry_after_bytes": retry_after_bytes},
    )


# ---------------------------------------------------------------------------
# PR-11: modelcontextprotocol/rust-sdk#1367 & #1359
# ---------------------------------------------------------------------------
def _collect_nested_mcp_headers(
    schema: dict[str, Any],
    args: dict[str, Any],
    prefix: tuple[str, ...] = (),
) -> tuple[bool, str, dict[str, str]]:
    props = schema.get("properties")
    if not isinstance(props, dict):
        return True, "OK", {}
    collected: dict[str, str] = {}
    seen_lower: dict[str, str] = {}
    for key, sub in props.items():
        if not isinstance(sub, dict):
            continue
        path = prefix + (key,)
        if "x-mcp-header" in sub:
            hdr = str(sub["x-mcp-header"])
            sub_type = sub.get("type")
            if not _TOKEN_RE.match(hdr) or sub_type not in ("string", "integer", "number", "boolean"):
                return False, "RUST_SDK_INVALID_NESTED_MCP_HEADER_SCHEMA", {}
            low = hdr.lower()
            if low in seen_lower:
                return False, "RUST_SDK_DUPLICATE_NESTED_MCP_HEADER", {}
            seen_lower[low] = hdr
            cur: Any = args
            found = True
            for part in path:
                if isinstance(cur, dict) and part in cur and cur[part] is not None:
                    cur = cur[part]
                else:
                    found = False
                    break
            if found:
                collected[hdr] = str(cur)
        if "properties" in sub:
            ok, code, child_headers = _collect_nested_mcp_headers(sub, args, path)
            if not ok:
                return False, code, {}
            for k, v in child_headers.items():
                if k.lower() in seen_lower:
                    return False, "RUST_SDK_DUPLICATE_NESTED_MCP_HEADER", {}
                seen_lower[k.lower()] = k
                collected[k] = v
    return True, "OK", collected


def evaluate_rust_sdk_same_origin_307_308_and_nested_mcp_header_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Verify same-origin 307/308 redirect policy up to 10 hops (#1367) and
    nested x-mcp-header properties chain extraction (#1359).
    """
    pr_id = "PR-11"
    status = int(payload.get("redirect_status", 307))
    orig = urlparse(str(payload.get("original_url", "https://mcp.example.com:8443/v1/mcp")))
    target = urlparse(str(payload.get("redirect_target_url", "https://mcp.example.com:8443/v2/mcp")))
    hops = int(payload.get("redirect_hops", 1))
    followed = bool(payload.get("redirect_followed", True))

    same_origin = (orig.scheme, orig.hostname, orig.port) == (target.scheme, target.hostname, target.port)
    should_follow = status in (307, 308) and same_origin and hops <= 10
    if followed != should_follow:
        return _res(
            pr_id,
            False,
            "RUST_SDK_REDIRECT_POLICY_VIOLATION",
            "Streamable HTTP client must follow only same-origin 307/308 redirects up to 10 hops and block 301/302/303 or cross-origin redirects",
            {
                "redirect_status": status,
                "same_origin": same_origin,
                "redirect_hops": hops,
                "redirect_followed": followed,
            },
        )

    schema = payload.get("tool_input_schema") or {}
    args = payload.get("tool_arguments") or {}
    expected_headers = payload.get("extracted_headers") or {}
    ok, err_code, computed_headers = _collect_nested_mcp_headers(schema, args)
    if not ok or computed_headers != expected_headers:
        return _res(
            pr_id,
            False,
            err_code if not ok else "RUST_SDK_NESTED_MCP_HEADER_EXTRACTION_MISMATCH",
            "x-mcp-header annotations must be validated and extracted along the full nested properties chain",
            {"computed_headers": computed_headers, "extracted_headers": expected_headers},
        )

    return _res(
        pr_id,
        True,
        "RUST_SDK_REDIRECT_AND_NESTED_MCP_HEADER_VALID",
        "Rust SDK same-origin 307/308 redirect policy and nested x-mcp-header extraction verified",
        {"redirect_status": status, "extracted_headers": computed_headers},
    )


# ---------------------------------------------------------------------------
# PR-12: modelcontextprotocol/rust-sdk#1366 & #1361
# ---------------------------------------------------------------------------
def evaluate_rust_sdk_init_ping_and_sse_init_error_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Verify client answers server ping during initialize handshake (#1366) and
    SSE/re-initialization stops immediately on initialize JSON-RPC error (#1361).
    """
    pr_id = "PR-12"
    handshake_phase = str(payload.get("handshake_phase", "initialize"))
    server_sent_ping = bool(payload.get("server_sent_ping_before_result", True))
    client_answered_ping = bool(payload.get("client_answered_ping", True))
    expected_answer = handshake_phase == "initialize" and server_sent_ping
    if client_answered_ping != expected_answer:
        return _res(
            pr_id,
            False,
            "RUST_SDK_HANDSHAKE_PING_BEHAVIOR_MISMATCH",
            "Client must answer server ping with empty result during initialize handshake (and ignore ping during 2026-07-28 server/discover)",
            {
                "handshake_phase": handshake_phase,
                "client_answered_ping": client_answered_ping,
                "expected_answer": expected_answer,
            },
        )

    init_error_over_sse = bool(payload.get("initialize_returned_jsonrpc_error", True))
    sse_stream_stopped_on_error = bool(payload.get("sse_stream_stopped_on_error", True))
    sent_initialized_after_reinit_error = bool(payload.get("sent_notifications_initialized_after_reinit_error", False))
    if init_error_over_sse and (not sse_stream_stopped_on_error or sent_initialized_after_reinit_error):
        return _res(
            pr_id,
            False,
            "RUST_SDK_INITIALIZE_ERROR_NOT_TERMINATED",
            "expect_initialized must stop draining SSE on a JSON-RPC error and perform_reinitialization must abort before sending notifications/initialized",
            {
                "sse_stream_stopped_on_error": sse_stream_stopped_on_error,
                "sent_notifications_initialized_after_reinit_error": sent_initialized_after_reinit_error,
            },
        )

    return _res(
        pr_id,
        True,
        "RUST_SDK_INIT_PING_AND_ERROR_HANDLING_VALID",
        "Rust SDK server ping reply during initialize and SSE/re-init error termination verified",
        {"handshake_phase": handshake_phase, "sse_stream_stopped_on_error": sse_stream_stopped_on_error},
    )


# ---------------------------------------------------------------------------
# PR-13: modelcontextprotocol/csharp-sdk#1931, #1929, & #1924
# ---------------------------------------------------------------------------
def evaluate_csharp_sdk_rune_uri_null_schema_and_primitive_order_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Verify supplementary Unicode scalar URI template expansion (#1931),
    explicit null preservation for structured output schemas (#1929), and
    registration-order server primitive listing (#1924).
    """
    pr_id = "PR-13"
    raw_var = str(payload.get("template_variable_value", "😀/test"))
    expanded_uri = str(payload.get("expanded_reserved_uri", ""))
    expected_encoded = quote(raw_var.encode("utf-8"), safe="/:@!$&'()*+,;=")
    if expanded_uri != expected_encoded or "%EF%BF%BD" in expanded_uri.upper():
        return _res(
            pr_id,
            False,
            "CSHARP_SDK_SURROGATE_PAIR_URI_TEMPLATE_CORRUPTION",
            "Reserved/fragment URI template expansion must encode supplementary Unicode scalars as full UTF-8 sequences without U+FFFD replacement",
            {"expected": expected_encoded, "actual": expanded_uri},
        )

    required_nullable_keys = list(payload.get("schema_required_nullable_keys") or [])
    structured_content = payload.get("structured_content") or {}
    missing_null_keys = [k for k in required_nullable_keys if k not in structured_content]
    if missing_null_keys:
        return _res(
            pr_id,
            False,
            "CSHARP_SDK_STRUCTURED_OUTPUT_REQUIRED_NULL_OMITTED",
            "Structured tool output with an outputSchema must preserve explicit null values for required nullable properties",
            {"missing_null_keys": missing_null_keys},
        )

    registered_order = list(payload.get("registered_primitive_names") or [])
    listed_order = list(payload.get("listed_primitive_names") or [])
    if not registered_order or listed_order != registered_order:
        return _res(
            pr_id,
            False,
            "CSHARP_SDK_PRIMITIVE_LIST_ORDER_RANDOMIZED",
            "McpServerPrimitiveCollection must list tools, prompts, resources, and templates in deterministic registration order",
            {"registered_order": registered_order, "listed_order": listed_order},
        )

    return _res(
        pr_id,
        True,
        "CSHARP_SDK_RUNE_URI_NULL_SCHEMA_AND_ORDER_VALID",
        "C# SDK supplementary Rune URI expansion, structured output null preservation, and registration-order listing verified",
        {"expanded_reserved_uri": expanded_uri, "primitive_count": len(listed_order)},
    )


# ---------------------------------------------------------------------------
# PR-14: modelcontextprotocol/csharp-sdk#1922, #1921, & #1917
# ---------------------------------------------------------------------------
def _deep_merge_json(request_obj: dict[str, Any], session_obj: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(request_obj)
    for k, v in session_obj.items():
        if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
            merged[k] = _deep_merge_json(merged[k], v)
        else:
            merged[k] = copy.deepcopy(v)
    return merged


def evaluate_csharp_sdk_parse_error_meta_merge_and_cancel_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Verify Streamable HTTP POST -32700 ParseError vs -32600 InvalidRequest (#1922),
    recursive _meta.clientCapabilities.extensions merge (#1921), and active
    notifications/cancelled delivery on token cancellation (#1917).
    """
    pr_id = "PR-14"
    raw_body = str(payload.get("post_raw_body", '{"jsonrpc":"2.0"'))
    returned_code = int(payload.get("returned_jsonrpc_error_code", -32700))
    try:
        parsed = json.loads(raw_body)
        expected_code = -32600 if (not isinstance(parsed, dict) or parsed.get("id") is None) else 0
    except Exception:
        expected_code = -32700

    if returned_code != expected_code:
        return _res(
            pr_id,
            False,
            "CSHARP_SDK_STREAMABLE_HTTP_PARSE_ERROR_CODE_MISMATCH",
            "Malformed JSON in Streamable HTTP POST must return -32700 (ParseError), while invalid JSON-RPC envelopes return -32600 (InvalidRequest)",
            {"expected_code": expected_code, "returned_code": returned_code},
        )

    req_caps = payload.get("request_client_capabilities") or {}
    sess_caps = payload.get("session_client_capabilities") or {}
    actual_merged = payload.get("merged_client_capabilities") or {}
    expected_merged = _deep_merge_json(req_caps, sess_caps)
    if actual_merged != expected_merged:
        return _res(
            pr_id,
            False,
            "CSHARP_SDK_PER_REQUEST_CAPABILITY_EXTENSIONS_DROPPED",
            "InjectRequestMeta must recursively merge _meta.clientCapabilities so per-request io.modelcontextprotocol/tasks survives alongside session extensions",
            {"expected_merged": expected_merged, "actual_merged": actual_merged},
        )

    request_canceled = bool(payload.get("request_cancellation_token_canceled", True))
    cancelled_notification_sent = bool(payload.get("notifications_cancelled_sent", True))
    if request_canceled and not cancelled_notification_sent:
        return _res(
            pr_id,
            False,
            "CSHARP_SDK_DROPPED_NOTIFICATIONS_CANCELLED",
            "Canceling a request CancellationToken must send notifications/cancelled before WaitAsync disposes the callback registration",
            {"notifications_cancelled_sent": cancelled_notification_sent},
        )

    return _res(
        pr_id,
        True,
        "CSHARP_SDK_PARSE_ERROR_META_MERGE_AND_CANCEL_VALID",
        "C# SDK -32700 ParseError split, recursive capability extension merge, and notifications/cancelled delivery verified",
        {"returned_code": returned_code, "extensions": list((actual_merged.get("extensions") or {}).keys())},
    )


# ---------------------------------------------------------------------------
# PR-15: modelcontextprotocol/java-sdk#1260 & #1214
# ---------------------------------------------------------------------------
def evaluate_java_sdk_list_filter_race_and_modern_skills_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Verify non-cancelling reactive tool-list filter composition (#1260) and
    modern server SEP-2640 SkillsFeature duplicate rejection + directoryRead opt-in (#1214).
    """
    pr_id = "PR-15"
    filter_cancelled_sibling = bool(payload.get("filter_false_cancelled_sibling_filters", False))
    deterministic_filtered_tools = bool(payload.get("deterministic_filtered_tools", True))
    if filter_cancelled_sibling or not deterministic_filtered_tools:
        return _res(
            pr_id,
            False,
            "JAVA_SDK_TOOLS_LIST_FILTER_RACE_CONDITION",
            "Multiple McpAsyncListFilter filters must compose without premature .all() upstream cancellation races",
            {"filter_false_cancelled_sibling_filters": filter_cancelled_sibling},
        )

    skills = payload.get("skills_list") or []
    seen_names: set[str] = set()
    for sk in skills:
        name = str(sk.get("name") or "")
        desc = str(sk.get("description") or "").strip()
        if not _SKILL_NAME_RE.match(name) or len(name) > 64 or not desc or name in seen_names:
            return _res(
                pr_id,
                False,
                "JAVA_SDK_INVALID_OR_DUPLICATE_SKILL_ENTRY",
                "Java modern server SkillsSchema must enforce SEP-2640 skill name syntax, non-empty description, and reject duplicate skill names",
                {"invalid_or_duplicate_skill": name},
            )
        seen_names.add(name)

    supports_dir_read = bool(payload.get("repository_supports_directory_read", True))
    advertised_dir_read = bool(payload.get("capability_advertised_directory_read", True))
    if supports_dir_read != advertised_dir_read:
        return _res(
            pr_id,
            False,
            "JAVA_SDK_SKILLS_DIRECTORY_READ_CAPABILITY_MISMATCH",
            "SkillsFeature must advertise and serve resources/directory/read iff repository.supportsDirectoryRead() is true",
            {
                "repository_supports_directory_read": supports_dir_read,
                "capability_advertised_directory_read": advertised_dir_read,
            },
        )

    return _res(
        pr_id,
        True,
        "JAVA_SDK_FILTER_AND_MODERN_SKILLS_VALID",
        "Java SDK non-cancelling tool filter composition and modern server SEP-2640 SkillsFeature verified",
        {"skill_count": len(seen_names), "supports_directory_read": supports_dir_read},
    )


# ---------------------------------------------------------------------------
# PR-16: modelcontextprotocol/java-sdk#1209, #1208, & #1207
# ---------------------------------------------------------------------------
def _is_valid_json_content_type(ct: str | None) -> bool:
    if not ct or not ct.strip():
        return False
    essence = ct.split(";", 1)[0].strip().lower()
    return essence == "application/json" or essence.endswith("+json")


def evaluate_java_sdk_legacy_init_versions_listen_params_and_415_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Verify modern server names supported versions when rejecting legacy initialize (#1209),
    rejects subscriptions/listen without notifications (#1208), and returns HTTP 415
    on missing/invalid Content-Type before reading body (#1207).
    """
    pr_id = "PR-16"
    legacy_init_err = payload.get("legacy_initialize_error") or {}
    err_data = legacy_init_err.get("data") or {}
    supported_versions = err_data.get("supported")
    if (
        legacy_init_err.get("code") != -32602
        or not isinstance(supported_versions, list)
        or "2026-07-28" not in supported_versions
    ):
        return _res(
            pr_id,
            False,
            "JAVA_SDK_LEGACY_INITIALIZE_MISSING_SUPPORTED_VERSIONS",
            "Modern server rejecting legacy initialize must return -32602 with data.supported naming supported protocol versions",
            {"legacy_initialize_error": legacy_init_err},
        )

    listen_params = payload.get("subscriptions_listen_params") or {}
    listen_rejected_invalid_params = bool(payload.get("listen_rejected_with_invalid_params", False))
    notifications_field = listen_params.get("notifications")
    notifications_valid = isinstance(notifications_field, list)
    if not notifications_valid and not listen_rejected_invalid_params:
        return _res(
            pr_id,
            False,
            "JAVA_SDK_SUBSCRIPTIONS_LISTEN_MISSING_NOTIFICATIONS_ACCEPTED",
            "subscriptions/listen without a non-null notifications list must fail with -32602 InvalidParams ('params.notifications is required')",
            {"subscriptions_listen_params": listen_params},
        )

    content_type = payload.get("servlet_post_content_type")
    servlet_http_status = int(payload.get("servlet_http_status", 200))
    body_read_before_415 = bool(payload.get("body_read_before_content_type_check", False))
    ct_ok = _is_valid_json_content_type(content_type)
    if (not ct_ok and servlet_http_status != 415) or body_read_before_415:
        return _res(
            pr_id,
            False,
            "JAVA_SDK_SERVLET_CONTENT_TYPE_415_BYPASS",
            "Modern servlet POST must validate Content-Type before reading the body and reject missing/non-JSON Content-Type with HTTP 415",
            {
                "servlet_post_content_type": content_type,
                "servlet_http_status": servlet_http_status,
                "body_read_before_content_type_check": body_read_before_415,
            },
        )

    return _res(
        pr_id,
        True,
        "JAVA_SDK_LEGACY_INIT_LISTEN_AND_415_VALID",
        "Java SDK legacy initialize supported versions, subscriptions/listen notifications validation, and servlet 415 Content-Type gate verified",
        {"supported_versions": supported_versions, "servlet_http_status": servlet_http_status},
    )


STAGE_222_EVALUATORS = {
    "PR-01": evaluate_inspector_refusal_and_oversize_relay_guard,
    "PR-02": evaluate_inspector_mcpdo_tls_handoff_and_skills_cache_guard,
    "PR-03": evaluate_inspector_pkce_flow_store_and_secret_stamp_guard,
    "PR-04": evaluate_inspector_insufficient_scope_refresh_429_and_ema_guard,
    "PR-05": evaluate_registry_trigram_backup_and_nested_publish_guard,
    "PR-06": evaluate_go_sdk_sse_non_message_skip_and_field_spacing_guard,
    "PR-07": evaluate_go_sdk_dcr_jwks_and_resource_not_found_json_guard,
    "PR-08": evaluate_go_sdk_token_source_dcr_reuse_and_static_reauth_guard,
    "PR-09": evaluate_go_sdk_discover_export_and_single_get_server_guard,
    "PR-10": evaluate_rust_sdk_http_status_error_and_sse_terminal_reconnect_guard,
    "PR-11": evaluate_rust_sdk_same_origin_307_308_and_nested_mcp_header_guard,
    "PR-12": evaluate_rust_sdk_init_ping_and_sse_init_error_guard,
    "PR-13": evaluate_csharp_sdk_rune_uri_null_schema_and_primitive_order_guard,
    "PR-14": evaluate_csharp_sdk_parse_error_meta_merge_and_cancel_guard,
    "PR-15": evaluate_java_sdk_list_filter_race_and_modern_skills_guard,
    "PR-16": evaluate_java_sdk_legacy_init_versions_listen_params_and_415_guard,
}


def evaluate_stage_222_guard(pr_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    evaluator = STAGE_222_EVALUATORS.get(pr_id)
    if evaluator is None:
        raise ValueError(f"Unknown Stage 222 PR id: {pr_id}")
    return evaluator(payload)


def evaluate_all_stage_222_guards(payload_by_pr: dict[str, dict[str, Any]]) -> dict[str, Any]:
    results = [
        evaluate_stage_222_guard(pr_id, payload_by_pr.get(pr_id, {}))
        for pr_id in STAGE_222_PR_IDS
    ]
    passed_count = sum(1 for r in results if r["passed"])
    return {
        "stage": 222,
        "total": len(results),
        "passed": passed_count,
        "failed": len(results) - passed_count,
        "all_passed": passed_count == len(results),
        "results": results,
    }
