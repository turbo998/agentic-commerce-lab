"""Stage 246 deterministic security and protocol guards (`PR-01..PR-16`).

Covers 36 primary-source PRs across:
- `modelcontextprotocol/inspector` (`#2809`, `#2808`, `#2801`, `#2798`, `#2796`,
  `#2795`, `#2794`, `#2793`, `#2792`, `#2791`, `#2790`, `#2788`, `#2787`, `#2785`)
- `modelcontextprotocol/swift-sdk` (`#311`, `#310`, `#309`, `#302`, `#299`, `#294`)
- `modelcontextprotocol/ruby-sdk` (`#632`, `#631`, `#617`, `#614`, `#613`, `#612`)
- `modelcontextprotocol/php-sdk` (`#614`, `#605`, `#596`, `#595`, `#594`, `#593`)
- `modelcontextprotocol/kotlin-sdk` (`#1134`, `#1131`, `#1130`, `#1128`)
"""

from __future__ import annotations

import base64
import hashlib
import ipaddress
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse


@dataclass(frozen=True)
class GuardEvaluation:
    passed: bool
    decision_code: str
    reason: str
    evidence: dict[str, Any]


SKILL_MAX_FILES = 512
SKILL_MAX_BYTES = 16 * 1024 * 1024  # 16 MiB
SKILL_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
ALLOWED_REDIRECT_STATUSES = {301, 302, 303, 307, 308}
LOAD_THRESHOLD_EXIT_CODE = 10
DATA_URL_HEADER_RE = re.compile(r"^data:([^,]*?)(;base64)?,(.*)$", re.DOTALL)
NATURAL_SPLIT_RE = re.compile(r"(\d+)")


def _eval(
    passed: bool,
    decision_code: str,
    reason: str,
    evidence: dict[str, Any] | None = None,
) -> GuardEvaluation:
    return GuardEvaluation(
        passed=bool(passed),
        decision_code=decision_code,
        reason=reason,
        evidence=dict(evidence or {}),
    )


def _filter_declined_refresh_grant(scope_str: str | None, request_refresh_token: bool) -> str | None:
    if not scope_str:
        return None
    parts = [p for p in scope_str.split() if p]
    if not request_refresh_token:
        parts = [p for p in parts if p != "offline_access"]
    return " ".join(parts) if parts else None


# ---------------------------------------------------------------------------
# PR-01: modelcontextprotocol/inspector#2809
# Opt-in scope on OAuth token refresh via scopeForRefresh (Entra AADSTS90009)
# ---------------------------------------------------------------------------
def evaluate_inspector_oauth_refresh_scope_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    scope_on_refresh = bool(payload.get("scope_on_refresh", False))
    tokens_scope = payload.get("tokens_scope")
    stored_request_scope = payload.get("stored_request_scope")
    configured_scope = payload.get("configured_scope")
    request_refresh_token = bool(payload.get("request_refresh_token", True))
    ema_delegates_scope_for_refresh = bool(payload.get("ema_delegates_scope_for_refresh", True))
    persisted_config_has_false_flag = bool(payload.get("persisted_config_has_false_flag", False))
    actual_refresh_scope = payload.get("actual_refresh_scope")

    if not ema_delegates_scope_for_refresh:
        return _eval(
            False,
            "INSPECTOR_EMA_REFRESH_SCOPE_NOT_DELEGATED",
            "EmaTransportOAuthProvider must delegate scopeForRefresh to the inner provider (#2809).",
            {"ema_delegates_scope_for_refresh": False},
        )

    if not scope_on_refresh and persisted_config_has_false_flag:
        return _eval(
            False,
            "INSPECTOR_SCOPE_ON_REFRESH_FALSE_PERSISTED",
            "mcp.json must only persist oauth.scopeOnRefresh when opted in (true), omitting false (#2809).",
            {"persisted_config_has_false_flag": True},
        )

    if not scope_on_refresh:
        expected_scope = None
    else:
        if isinstance(tokens_scope, str) and tokens_scope.strip():
            expected_scope = tokens_scope.strip()
        elif isinstance(stored_request_scope, str) and stored_request_scope.strip():
            expected_scope = _filter_declined_refresh_grant(
                stored_request_scope.strip(), request_refresh_token
            )
        elif isinstance(configured_scope, str) and configured_scope.strip():
            expected_scope = _filter_declined_refresh_grant(
                configured_scope.strip(), request_refresh_token
            )
        else:
            expected_scope = None

    if actual_refresh_scope != expected_scope:
        return _eval(
            False,
            "INSPECTOR_REFRESH_SCOPE_MISMATCH",
            "Refresh request scope must match opt-in scopeForRefresh precedence (tokens.scope -> filtered request scope -> configured scope) (#2809).",
            {
                "scope_on_refresh": scope_on_refresh,
                "expected_scope": expected_scope,
                "actual_refresh_scope": actual_refresh_scope,
            },
        )

    return _eval(
        True,
        "INSPECTOR_OAUTH_REFRESH_SCOPE_VALID",
        "OAuth refresh scope opt-in precedence and EMA delegation verified (#2809).",
        {"scope_on_refresh": scope_on_refresh, "resolved_refresh_scope": expected_scope},
    )


# ---------------------------------------------------------------------------
# PR-02: modelcontextprotocol/inspector#2808
# SEP-2640 Skills SDK schema integration & Inspector permissive conformance
# ---------------------------------------------------------------------------
def evaluate_inspector_skills_sdk_hybrid_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    file_count = int(payload.get("file_count", 0))
    total_bytes = int(payload.get("total_bytes", 0))
    digest = str(payload.get("digest", ""))
    negotiated_era = str(payload.get("negotiated_era", "2026-07-28"))
    directory_result = dict(payload.get("directory_result") or {})
    non_conforming_entry_throws_ui = bool(payload.get("non_conforming_entry_throws_ui", False))
    dynamic_resource_treated_as_warning = bool(
        payload.get("dynamic_resource_treated_as_warning", True)
    )
    plain_http_lan_sha256_fallback = bool(payload.get("plain_http_lan_sha256_fallback", True))
    unknown_child_fields_preserved = bool(payload.get("unknown_child_fields_preserved", True))

    if file_count > SKILL_MAX_FILES or total_bytes > SKILL_MAX_BYTES:
        return _eval(
            False,
            "INSPECTOR_SKILL_LIMITS_EXCEEDED",
            "Skill exceeds SDK SKILL_LIMITS (512 files or 16 MiB) (#2808).",
            {"file_count": file_count, "total_bytes": total_bytes},
        )

    if not SKILL_DIGEST_RE.match(digest):
        return _eval(
            False,
            "INSPECTOR_SKILL_DIGEST_PATTERN_INVALID",
            "Skill digest must match SDK SKILL_DIGEST_PATTERN sha256:<64-hex> (#2808).",
            {"digest": digest},
        )

    if non_conforming_entry_throws_ui or not dynamic_resource_treated_as_warning:
        return _eval(
            False,
            "INSPECTOR_SKILLS_CONFORMANCE_VISIBILITY_LOST",
            "Inspector must keep permissive SkillEntrySchema and report dynamic resources as warnings without crashing the Skills view (#2808).",
            {
                "non_conforming_entry_throws_ui": non_conforming_entry_throws_ui,
                "dynamic_resource_treated_as_warning": dynamic_resource_treated_as_warning,
            },
        )

    if not plain_http_lan_sha256_fallback or not unknown_child_fields_preserved:
        return _eval(
            False,
            "INSPECTOR_SKILLS_SHA256_OR_LOOSE_OBJECT_REGRESSION",
            "Inspector must keep pure-JS SHA-256 fallback on plain-HTTP LAN IPs and preserve unknown directory child members via looseObject (#2808).",
            {
                "plain_http_lan_sha256_fallback": plain_http_lan_sha256_fallback,
                "unknown_child_fields_preserved": unknown_child_fields_preserved,
            },
        )

    if negotiated_era >= "2026-07-28":
        ttl_ms = directory_result.get("ttlMs")
        cache_scope = directory_result.get("cacheScope")
        if (
            not isinstance(ttl_ms, int)
            or isinstance(ttl_ms, bool)
            or ttl_ms < 0
            or cache_scope not in ("private", "public")
        ):
            return _eval(
                False,
                "INSPECTOR_MODERN_DIRECTORY_READ_CACHE_FIELDS_INVALID",
                "Modern resources/directory/read results must validate ttlMs and cacheScope via ReadResourceDirectoryResultSchema (#2808).",
                {"ttlMs": ttl_ms, "cacheScope": cache_scope},
            )

    return _eval(
        True,
        "INSPECTOR_SKILLS_SDK_HYBRID_VALID",
        "SDK SEP-2640 constants/schemas and Inspector permissive conformance verified (#2808).",
        {"file_count": file_count, "total_bytes": total_bytes, "era": negotiated_era},
    )


# ---------------------------------------------------------------------------
# PR-03: modelcontextprotocol/inspector#2796
# OAuth destination SSRF guard against link-local & metadata addresses
# ---------------------------------------------------------------------------
def _is_blocked_link_local_or_imds_ip(ip_str: str) -> bool:
    s = ip_str.strip().lower()
    if s.startswith("[") and s.endswith("]"):
        s = s[1:-1]
    # Check hex-form IPv4-mapped IPv6 e.g. ::ffff:a9fe:a9fe
    if s.startswith("::ffff:"):
        tail = s[len("::ffff:") :]
        if ":" in tail and "." not in tail:
            parts = tail.split(":")
            if len(parts) == 2:
                try:
                    hi = int(parts[0], 16)
                    lo = int(parts[1], 16)
                    b1, b2 = (hi >> 8) & 0xFF, hi & 0xFF
                    b3, b4 = (lo >> 8) & 0xFF, lo & 0xFF
                    s = f"{b1}.{b2}.{b3}.{b4}"
                except ValueError:
                    pass
    try:
        addr = ipaddress.ip_address(s)
    except ValueError:
        return False

    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        addr = addr.ipv4_mapped

    if isinstance(addr, ipaddress.IPv4Address):
        return addr in ipaddress.ip_network("169.254.0.0/16")

    aws_imds_v6 = ipaddress.ip_address("fd00:ec2::254")
    return addr in ipaddress.ip_network("fe80::/10") or addr == aws_imds_v6


def evaluate_inspector_oauth_destination_ssrf_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    is_mcp_wire_request = bool(payload.get("is_mcp_wire_request", False))
    hops: Sequence[Mapping[str, Any]] = list(payload.get("hops") or [])
    if is_mcp_wire_request:
        return _eval(
            True,
            "INSPECTOR_MCP_WIRE_ENDPOINT_EXEMPT",
            "Configured MCP endpoint traffic with valid MCP wire shape is exempt from OAuth destination guard (#2796).",
            {"is_mcp_wire_request": True},
        )

    if not hops:
        return _eval(
            False,
            "INSPECTOR_OAUTH_GUARD_EMPTY_HOPS",
            "OAuth request must specify at least one hop to validate (#2796).",
            {},
        )

    if len(hops) - 1 > 5:
        return _eval(
            False,
            "INSPECTOR_OAUTH_REDIRECT_LIMIT_EXCEEDED",
            "OAuth destination guard allows at most 5 manual redirects (#2796).",
            {"redirect_count": len(hops) - 1},
        )

    prev_origin: tuple[str, str, int | None] | None = None
    for idx, hop in enumerate(hops):
        url = str(hop.get("url", ""))
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return _eval(
                False,
                "INSPECTOR_OAUTH_UNSUPPORTED_SCHEME_BLOCKED",
                "OAuth destination guard allows only http: and https: schemes on every hop (#2796).",
                {"hop": idx, "scheme": parsed.scheme},
            )

        host_literal = parsed.hostname or ""
        resolved_ips = list(hop.get("resolved_ips") or ([host_literal] if host_literal else []))
        for ip_candidate in resolved_ips:
            if _is_blocked_link_local_or_imds_ip(str(ip_candidate)):
                return _eval(
                    False,
                    "INSPECTOR_OAUTH_LINK_LOCAL_OR_IMDS_BLOCKED",
                    "OAuth destination or connect.lookup resolved IP is in blocked link-local/IMDS range (169.254.0.0/16, fe80::/10, fd00:ec2::254) (#2796).",
                    {"hop": idx, "blocked_ip": ip_candidate, "url": url},
                )

        cur_origin = (parsed.scheme, (parsed.hostname or "").lower(), parsed.port)
        if prev_origin is not None and cur_origin != prev_origin:
            if bool(hop.get("carries_credentials_header", False)):
                return _eval(
                    False,
                    "INSPECTOR_OAUTH_CROSS_ORIGIN_CREDENTIALS_LEAK",
                    "Cross-origin OAuth redirect hop must strip Authorization/Cookie credential headers (#2796).",
                    {"hop": idx, "url": url},
                )
            if bool(hop.get("carries_request_body", False)):
                return _eval(
                    False,
                    "INSPECTOR_OAUTH_CROSS_ORIGIN_BODY_REDIRECT_BLOCKED",
                    "Cross-origin OAuth redirect hop that still carries a request body must be refused (#2796).",
                    {"hop": idx, "url": url},
                )

        if idx < len(hops) - 1:
            status = int(hop.get("redirect_status", 302))
            if status not in ALLOWED_REDIRECT_STATUSES:
                return _eval(
                    False,
                    "INSPECTOR_OAUTH_UNSUPPORTED_REDIRECT_STATUS",
                    "OAuth manual redirect loop only follows 301, 302, 303, 307, and 308 (#2796).",
                    {"hop": idx, "redirect_status": status},
                )
        prev_origin = cur_origin

    return _eval(
        True,
        "INSPECTOR_OAUTH_DESTINATION_SSRF_SAFE",
        "All OAuth hops and connect.lookup addresses passed link-local/IMDS and cross-origin redirect guards (#2796).",
        {"hop_count": len(hops)},
    )


# ---------------------------------------------------------------------------
# PR-04: modelcontextprotocol/inspector#2794 & #2792
# Static client SEP-2352 issuer back-stamp & DCR keychain owner-stamp check
# ---------------------------------------------------------------------------
def evaluate_inspector_static_issuer_stamp_and_dcr_secret_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    registration_kind = str(payload.get("registration_kind", "preregistered"))
    preregistered_client_id = str(payload.get("preregistered_client_id", "static-client-1"))
    saved_client_id = str(payload.get("saved_client_id", "static-client-1"))
    back_stamped_slot = str(payload.get("back_stamped_slot", "preregistered"))
    stored_issuer_stamp = payload.get("stored_issuer_stamp")
    context_issuer = payload.get("context_issuer")
    reseed_client_changed = bool(payload.get("reseed_client_changed", False))
    returned_issuer_stamp = payload.get("returned_issuer_stamp")

    if registration_kind == "preregistered" and saved_client_id == preregistered_client_id:
        if back_stamped_slot != "preregistered":
            return _eval(
                False,
                "INSPECTOR_STATIC_CLIENT_STAMP_WRITTEN_TO_DYNAMIC_SLOT",
                "SDK SEP-2352 issuer back-stamp for a matching static client_id must write to the preregistered slot (#2794).",
                {"back_stamped_slot": back_stamped_slot},
            )
        expected_stamp = (
            None
            if reseed_client_changed or (context_issuer and stored_issuer_stamp != context_issuer)
            else stored_issuer_stamp
        )
        if returned_issuer_stamp != expected_stamp:
            return _eval(
                False,
                "INSPECTOR_STATIC_CLIENT_ISSUER_STAMP_MISMATCH",
                "Static client read must preserve matching issuer stamp across restarts, drop it on credential change, and return unstamped on AS issuer migration (#2794).",
                {
                    "expected_stamp": expected_stamp,
                    "returned_issuer_stamp": returned_issuer_stamp,
                },
            )

    dcr_state_client_id = payload.get("dcr_state_client_id")
    dcr_secret_stamp_owner = payload.get("dcr_secret_stamp_owner")
    dcr_secret_mac_valid = bool(payload.get("dcr_secret_mac_valid", True))
    dcr_secret_returned = bool(payload.get("dcr_secret_returned", False))

    if (
        registration_kind == "dynamic"
        and dcr_state_client_id
        and dcr_secret_mac_valid
        and dcr_secret_stamp_owner
        and dcr_secret_stamp_owner != dcr_state_client_id
        and dcr_secret_returned
    ):
        return _eval(
            False,
            "INSPECTOR_DCR_CROSS_CLIENT_SECRET_LEAKED",
            "joinClientInformation must treat a DCR secret stamped for another client_id as absent (#2792).",
            {
                "dcr_state_client_id": dcr_state_client_id,
                "dcr_secret_stamp_owner": dcr_secret_stamp_owner,
            },
        )

    return _eval(
        True,
        "INSPECTOR_STATIC_ISSUER_AND_DCR_SECRET_STAMP_VALID",
        "Static client SEP-2352 issuer back-stamp and DCR owner-stamp secret isolation verified (#2794/#2792).",
        {
            "registration_kind": registration_kind,
            "returned_issuer_stamp": returned_issuer_stamp,
        },
    )


# ---------------------------------------------------------------------------
# PR-05: modelcontextprotocol/inspector#2795, #2791, & #2787
# 429 rate_limited envelope, --load-connections stdio guard & SLO exit code 10
# ---------------------------------------------------------------------------
def evaluate_inspector_cli_rate_limit_and_load_slo_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    transport = str(payload.get("transport", "streamable-http"))
    load_connections = int(payload.get("load_connections", 1))
    stdio_multi_conn_rejected = bool(payload.get("stdio_multi_conn_rejected", True))

    if transport == "stdio" and load_connections > 1 and not stdio_multi_conn_rejected:
        return _eval(
            False,
            "INSPECTOR_LOAD_CONNECTIONS_STDIO_ALLOWED",
            "--load-connections > 1 against a stdio server must fail with exit 1 before connecting (#2791).",
            {"transport": transport, "load_connections": load_connections},
        )

    http_status = payload.get("http_status")
    if http_status == 429:
        envelope = dict(payload.get("error_envelope") or {})
        if (
            envelope.get("code") != "rate_limited"
            or envelope.get("status") != 429
            or not isinstance(envelope.get("method"), str)
        ):
            return _eval(
                False,
                "INSPECTOR_429_RATE_LIMITED_ENVELOPE_INVALID",
                "CLI and mcpdo 429 errors must emit code='rate_limited', status=429, method, retryAfter, and retryAfterMs (#2795).",
                {"error_envelope": envelope},
            )

    requests_total = int(payload.get("requests_total", 100))
    failed_calls = int(payload.get("failed_calls", 0))
    completed_calls = int(payload.get("completed_calls", requests_total - failed_calls))
    p99_ms = payload.get("p99_ms")
    max_error_rate = payload.get("max_error_rate")
    max_p99_ms = payload.get("max_p99_ms")
    exit_code = int(payload.get("exit_code", 0))
    threshold_error_code = payload.get("threshold_error_code")
    summary_printed_before_exit = bool(payload.get("summary_printed_before_exit", True))

    error_rate_breached = False
    if max_error_rate is not None:
        exact_rate = (failed_calls / requests_total) if requests_total > 0 else 1.0
        error_rate_breached = exact_rate > float(max_error_rate)

    p99_breached = False
    if max_p99_ms is not None:
        if completed_calls <= 0 or p99_ms is None or float(p99_ms) > float(max_p99_ms):
            p99_breached = True

    if error_rate_breached or p99_breached:
        expected_code = (
            "load_error_rate_exceeded" if error_rate_breached else "load_p99_exceeded"
        )
        if (
            exit_code != LOAD_THRESHOLD_EXIT_CODE
            or threshold_error_code != expected_code
            or not summary_printed_before_exit
        ):
            return _eval(
                False,
                "INSPECTOR_LOAD_SLO_BREACH_NOT_ENFORCED",
                "Breaching --load-max-error-rate or --load-max-p99 must print summary first and exit 10 with deterministic threshold code (#2787).",
                {
                    "exit_code": exit_code,
                    "expected_code": expected_code,
                    "actual_code": threshold_error_code,
                },
            )

    return _eval(
        True,
        "INSPECTOR_CLI_429_AND_LOAD_SLO_VALID",
        "CLI/mcpdo 429 rate_limited envelope, --load-connections stdio guard, and exit-10 SLO thresholds verified (#2795/#2791/#2787).",
        {"load_connections": load_connections, "exit_code": exit_code},
    )


# ---------------------------------------------------------------------------
# PR-06: modelcontextprotocol/inspector#2801, #2798, #2793, #2790, #2788, & #2785
# ServerCard connect error, natural tool sort, non-loopback warning & release hygiene
# ---------------------------------------------------------------------------
def _natural_base_key(label: str) -> tuple[Any, ...]:
    parts = NATURAL_SPLIT_RE.split(label.lower())
    out: list[Any] = []
    for part in parts:
        if part.isdigit():
            out.append((0, int(part)))
        else:
            out.append((1, part))
    return tuple(out)


def evaluate_inspector_ui_sort_bind_and_release_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    connect_failed = bool(payload.get("connect_failed", False))
    server_card_error_text = str(payload.get("server_card_error_text", ""))
    if connect_failed and not server_card_error_text.strip():
        return _eval(
            False,
            "INSPECTOR_SERVER_CARD_CONNECT_REASON_DROPPED",
            "ServerCard must preserve and render the failed connect reason when status is error (#2801).",
            {"connect_failed": True, "server_card_error_text": server_card_error_text},
        )

    tools: Sequence[Mapping[str, Any]] = list(payload.get("tools") or [])
    displayed_order: Sequence[str] = list(payload.get("displayed_tool_names") or [])
    if tools and displayed_order:
        expected_tools = sorted(
            tools,
            key=lambda t: _natural_base_key(str(t.get("title") or t.get("name") or "")),
        )
        expected_names = [str(t.get("name")) for t in expected_tools]
        if list(displayed_order) != expected_names:
            return _eval(
                False,
                "INSPECTOR_TOOLS_LIST_SORT_ORDER_INVALID",
                "Tools sidebar must sort by display label (title ?? name) case-insensitively and numerically while preserving server order on case ties (#2798).",
                {"expected_names": expected_names, "displayed_order": list(displayed_order)},
            )

    bind_host = str(payload.get("bind_host", "127.0.0.1")).strip().lower()
    is_loopback = bind_host in ("localhost", "::1", "[::1]") or bind_host.startswith("127.")
    non_loopback_warning_emitted = bool(payload.get("non_loopback_warning_emitted", False))
    if not is_loopback and not non_loopback_warning_emitted:
        return _eval(
            False,
            "INSPECTOR_NON_LOOPBACK_BIND_WARNING_MISSING",
            "Binding the web server to a non-loopback host must emit nonLoopbackBindWarning explaining GET / token exposure (#2790).",
            {"bind_host": bind_host},
        )

    test_catalog_in_tmpdir = bool(payload.get("test_catalog_in_tmpdir", True))
    v1_bump_ran_npm_install = bool(payload.get("v1_bump_ran_npm_install", False))
    advisory_pending_reporters_credited = bool(
        payload.get("advisory_pending_reporters_credited", True)
    )
    if not test_catalog_in_tmpdir or v1_bump_ran_npm_install or not advisory_pending_reporters_credited:
        return _eval(
            False,
            "INSPECTOR_TEST_HOME_OR_RELEASE_ADVISORY_VIOLATION",
            "CLI tests must isolate HOME in os.tmpdir() (#2793), v1 bumps must not run npm install (#2785), and --advisory must credit pending reporters (#2788).",
            {
                "test_catalog_in_tmpdir": test_catalog_in_tmpdir,
                "v1_bump_ran_npm_install": v1_bump_ran_npm_install,
                "advisory_pending_reporters_credited": advisory_pending_reporters_credited,
            },
        )

    return _eval(
        True,
        "INSPECTOR_UI_SORT_BIND_AND_RELEASE_VALID",
        "ServerCard connect reason, natural tool label sort, non-loopback warning, and v1/advisory hygiene verified (#2801/#2798/#2793/#2790/#2788/#2785).",
        {"bind_host": bind_host, "tool_count": len(tools)},
    )


# ---------------------------------------------------------------------------
# PR-07: modelcontextprotocol/swift-sdk#310 & #309
# RFC 2397 data URL header-only ;base64 detection & raw byte percent-decoding
# ---------------------------------------------------------------------------
def parse_rfc2397_data_url(data_url: str) -> bytes | None:
    m = DATA_URL_HEADER_RE.match(data_url)
    if not m:
        return None
    _mediatype, base64_marker, payload = m.group(1), m.group(2), m.group(3)
    if base64_marker == ";base64":
        try:
            return base64.b64decode(payload, validate=True)
        except Exception:
            return None
    out = bytearray()
    i = 0
    n = len(payload)
    while i < n:
        ch = payload[i]
        if ch == "%":
            if i + 2 >= n:
                return None
            hex_pair = payload[i + 1 : i + 3]
            try:
                out.append(int(hex_pair, 16))
            except ValueError:
                return None
            i += 3
        else:
            out.extend(ch.encode("utf-8"))
            i += 1
    return bytes(out)


def evaluate_swift_data_url_header_and_byte_decode_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    data_url = str(payload.get("data_url", ""))
    expected_bytes_hex = payload.get("expected_bytes_hex")
    expect_nil = bool(payload.get("expect_nil", False))

    decoded = parse_rfc2397_data_url(data_url)
    if expect_nil:
        if decoded is not None:
            return _eval(
                False,
                "SWIFT_MALFORMED_DATA_URL_NOT_REJECTED",
                "Malformed percent-escapes or invalid base64 in data URL must return nil (#310/#309).",
                {"data_url": data_url},
            )
        return _eval(
            True,
            "SWIFT_DATA_URL_MALFORMED_REJECTED",
            "Malformed data URL properly rejected with nil (#310/#309).",
            {"data_url": data_url},
        )

    if decoded is None:
        return _eval(
            False,
            "SWIFT_VALID_DATA_URL_RETURNED_NIL",
            "Data.parseDataURL must detect ;base64 from header only and decode non-UTF-8 %XX escapes directly to bytes (#310/#309).",
            {"data_url": data_url},
        )

    actual_hex = decoded.hex()
    if expected_bytes_hex is not None and actual_hex != str(expected_bytes_hex).lower():
        return _eval(
            False,
            "SWIFT_DATA_URL_DECODED_BYTES_MISMATCH",
            "Decoded data URL bytes did not match expected RFC 2397 byte sequence (#310/#309).",
            {"expected_hex": expected_bytes_hex, "actual_hex": actual_hex},
        )

    return _eval(
        True,
        "SWIFT_DATA_URL_HEADER_AND_RAW_BYTES_VALID",
        "RFC 2397 header-only ;base64 detection and raw byte %XX decoding verified (#310/#309).",
        {"decoded_length": len(decoded), "actual_hex": actual_hex},
    )


# ---------------------------------------------------------------------------
# PR-08: modelcontextprotocol/swift-sdk#311, #302, #299, & #294
# Heartbeat failure transport behavior, redirect port race & Server coder cache
# ---------------------------------------------------------------------------
def evaluate_swift_transport_heartbeat_oauth_port_and_coder_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    heartbeat_Disconnect_and_reconnect_verified = bool(
        payload.get("heartbeat_disconnect_and_reconnect_verified", True)
    )
    is_production_oauth = bool(payload.get("is_production_oauth", True))
    uses_unbound_ephemeral_redirect_port = bool(
        payload.get("uses_unbound_ephemeral_redirect_port", False)
    )
    server_caches_json_coders = bool(payload.get("server_caches_json_coders", True))
    tool_schema_properties = dict(payload.get("tool_schema_properties") or {})

    if not heartbeat_Disconnect_and_reconnect_verified:
        return _eval(
            False,
            "SWIFT_HEARTBEAT_TEST_MOCK_STATE_RACE",
            "NetworkTransport heartbeat failure check must assert transport disconnect/reconnect behavior rather than racing sleep against mock .failed state (#311).",
            {},
        )

    if is_production_oauth and uses_unbound_ephemeral_redirect_port:
        return _eval(
            False,
            "SWIFT_OAUTH_EPHEMERAL_PORT_RACE_RISK",
            "Production OAuth configurations must use a bound fixed port or custom URL scheme rather than defaultAuthorizationRedirectURI()'s unbound ephemeral port (#302).",
            {"uses_unbound_ephemeral_redirect_port": True},
        )

    if not server_caches_json_coders:
        return _eval(
            False,
            "SWIFT_SERVER_PER_SEND_CODER_ALLOCATION",
            "Server actor must cache JSONEncoder and JSONDecoder across outbound sends and inbound message loops (#299).",
            {},
        )

    for prop_name, prop_schema in tool_schema_properties.items():
        if not isinstance(prop_schema, Mapping) or "type" not in prop_schema:
            return _eval(
                False,
                "SWIFT_TOOL_INPUT_SCHEMA_STRING_PROPERTY_INVALID",
                "Tool inputSchema properties must be typed schema objects, not bare description strings (#294).",
                {"property": prop_name, "value": prop_schema},
            )

    return _eval(
        True,
        "SWIFT_TRANSPORT_OAUTH_PORT_AND_CODER_VALID",
        "Swift NetworkTransport heartbeat behavior, OAuth redirect URI port safety, Server JSON coder cache, and typed tool schemas verified (#311/#302/#299/#294).",
        {"property_count": len(tool_schema_properties)},
    )


# ---------------------------------------------------------------------------
# PR-09: modelcontextprotocol/ruby-sdk#632 & #631
# subscriptions/listen per-URI subscribe handler & private exception_reporter fix
# ---------------------------------------------------------------------------
def evaluate_ruby_listen_subscribe_handler_and_exception_reporter_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    requested_uris: Sequence[str] = list(payload.get("requested_uris") or [])
    allowed_uris_set = set(payload.get("handler_allowed_uris") or [])
    acknowledged_uris = payload.get("acknowledged_uris")
    handler_received_meta_and_auth_info = bool(
        payload.get("handler_received_meta_and_auth_info", True)
    )
    unsubscribe_called_on_stream_end = bool(
        payload.get("unsubscribe_called_on_stream_end", False)
    )
    notification_failure_calls_private_report = bool(
        payload.get("notification_failure_calls_private_report", False)
    )
    tool_call_failed_on_notification_transport_error = bool(
        payload.get("tool_call_failed_on_notification_transport_error", False)
    )

    if not handler_received_meta_and_auth_info or unsubscribe_called_on_stream_end:
        return _eval(
            False,
            "RUBY_LISTEN_SUBSCRIBE_CONTEXT_OR_UNSUBSCRIBE_INVALID",
            "subscriptions/listen must pass distinct URIs with _meta and auth_info to resources_subscribe_handler and must not call resources_unsubscribe_handler on stream close (#632).",
            {
                "handler_received_meta_and_auth_info": handler_received_meta_and_auth_info,
                "unsubscribe_called_on_stream_end": unsubscribe_called_on_stream_end,
            },
        )

    expected_ack: list[str] = []
    seen: set[str] = set()
    for u in requested_uris:
        if u not in seen:
            seen.add(u)
            if u in allowed_uris_set:
                expected_ack.append(u)

    expected_ack_field = expected_ack if expected_ack else None
    if acknowledged_uris != expected_ack_field:
        return _eval(
            False,
            "RUBY_LISTEN_UNAUTHORIZED_URI_ACKNOWLEDGED",
            "subscriptions/listen must omit URIs rejected by resources_subscribe_handler and omit resourceSubscriptions entirely when no URI remains (#632).",
            {"expected_ack": expected_ack_field, "acknowledged_uris": acknowledged_uris},
        )

    if (
        notification_failure_calls_private_report
        or tool_call_failed_on_notification_transport_error
    ):
        return _eval(
            False,
            "RUBY_SESSION_NOTIFICATION_PRIVATE_METHOD_ERROR",
            "ServerSession#notify_* rescues must report transport errors via configuration.exception_reporter without raising NoMethodError (#631).",
            {
                "notification_failure_calls_private_report": notification_failure_calls_private_report,
                "tool_call_failed_on_notification_transport_error": tool_call_failed_on_notification_transport_error,
            },
        )

    return _eval(
        True,
        "RUBY_LISTEN_SUBSCRIBE_AND_EXCEPTION_REPORTER_VALID",
        "Ruby subscriptions/listen per-URI handler filtering and ServerSession exception_reporter routing verified (#632/#631).",
        {"acknowledged_uris": expected_ack_field},
    )


# ---------------------------------------------------------------------------
# PR-10: modelcontextprotocol/ruby-sdk#612 & #613
# Null-ID request refusal (-32600), ID-less request drop & arbitrary string IDs
# ---------------------------------------------------------------------------
def evaluate_ruby_jsonrpc_null_id_and_string_id_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    has_id_member = bool(payload.get("has_id_member", True))
    request_id = payload.get("request_id")
    is_custom_method = bool(payload.get("is_custom_method", False))
    method_executed = bool(payload.get("method_executed", False))
    response_error_code = payload.get("response_error_code")
    http_status = payload.get("http_status")
    lifecycle_era = str(payload.get("lifecycle_era", "2026-07-28"))

    if has_id_member and request_id is None:
        expected_http = 400 if lifecycle_era >= "2026-07-28" else 200
        if method_executed or response_error_code != -32600 or http_status != expected_http:
            return _eval(
                False,
                "RUBY_NULL_ID_REQUEST_EXECUTED_OR_ACCEPTED",
                "JSON-RPC message carrying 'id': null must be refused with -32600 Invalid Request (HTTP 400 modern / 200 legacy) without running the method (#612).",
                {
                    "method_executed": method_executed,
                    "response_error_code": response_error_code,
                    "http_status": http_status,
                },
            )
        return _eval(
            True,
            "RUBY_NULL_ID_REFUSED_WITH_INVALID_REQUEST",
            "Null-ID JSON-RPC message refused with -32600 without executing method (#612).",
            {"http_status": http_status},
        )

    if not has_id_member and not is_custom_method:
        if method_executed or response_error_code is not None:
            return _eval(
                False,
                "RUBY_IDLESS_PROTOCOL_REQUEST_EXECUTED",
                "Protocol request method sent without an id member must not execute and must produce no response (#612).",
                {"method_executed": method_executed},
            )
        return _eval(
            True,
            "RUBY_IDLESS_PROTOCOL_REQUEST_DROPPED",
            "ID-less protocol request dropped without execution (#612).",
            {},
        )

    if has_id_member and isinstance(request_id, str) and len(request_id) > 0:
        if response_error_code == -32600 or not method_executed:
            return _eval(
                False,
                "RUBY_STRING_REQUEST_ID_WRONGLY_REJECTED",
                "Any non-empty string request id (including dots, colons, and URNs) must be accepted (#613).",
                {"request_id": request_id, "response_error_code": response_error_code},
            )

    return _eval(
        True,
        "RUBY_JSONRPC_ID_RULES_VALID",
        "Ruby JSON-RPC null-id refusal, id-less request drop, and arbitrary string id acceptance verified (#612/#613).",
        {"request_id": request_id},
    )


# ---------------------------------------------------------------------------
# PR-11: modelcontextprotocol/ruby-sdk#617 & #614
# Streamable HTTP initialize immediate SSE return & DNS rebinding allowed_hosts
# ---------------------------------------------------------------------------
def evaluate_ruby_initialize_sse_return_and_dns_rebinding_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    initialize_sse_abortable_on_response = bool(
        payload.get("initialize_sse_abortable_on_response", True)
    )
    session_id_captured_from_headers = bool(
        payload.get("session_id_captured_from_headers", True)
    )
    dns_rebinding_enabled = bool(payload.get("dns_rebinding_enabled", True))
    allowed_hosts = {str(h).lower() for h in (payload.get("allowed_hosts") or ["localhost", "127.0.0.1"])}
    request_host = str(payload.get("request_host", "localhost")).lower()
    http_status = int(payload.get("http_status", 200))

    if not initialize_sse_abortable_on_response or not session_id_captured_from_headers:
        return _eval(
            False,
            "RUBY_INITIALIZE_SSE_STREAM_HANG",
            "MCP::Client::HTTP must capture Mcp-Session-Id on stream setup and return from initialize as soon as its SSE JSON-RPC response arrives (#617).",
            {
                "initialize_sse_abortable_on_response": initialize_sse_abortable_on_response,
                "session_id_captured_from_headers": session_id_captured_from_headers,
            },
        )

    if dns_rebinding_enabled and request_host not in allowed_hosts and http_status != 403:
        return _eval(
            False,
            "RUBY_DNS_REBINDING_UNALLOWED_HOST_ADMITTED",
            "Streamable HTTP DNS rebinding protection must refuse unallowed Host headers with 403 Forbidden (#614).",
            {"request_host": request_host, "allowed_hosts": sorted(allowed_hosts), "http_status": http_status},
        )

    if dns_rebinding_enabled and request_host in allowed_hosts and http_status == 403:
        return _eval(
            False,
            "RUBY_DNS_REBINDING_ALLOWED_HOST_BLOCKED",
            "Explicitly configured allowed_hosts entry must be admitted under DNS rebinding protection (#614).",
            {"request_host": request_host},
        )

    return _eval(
        True,
        "RUBY_INITIALIZE_SSE_AND_DNS_REBINDING_VALID",
        "Immediate initialize SSE return and DNS rebinding allowed_hosts enforcement verified (#617/#614).",
        {"request_host": request_host, "http_status": http_status},
    )


# ---------------------------------------------------------------------------
# PR-12: modelcontextprotocol/php-sdk#614 & #596
# Client reconnect transport closure & vanished-stream pending request cleanup
# ---------------------------------------------------------------------------
def evaluate_php_reconnect_transport_close_and_vanished_stream_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    reconnected = bool(payload.get("reconnected", True))
    previous_transport_closed_before_replace = bool(
        payload.get("previous_transport_closed_before_replace", True)
    )
    if reconnected and not previous_transport_closed_before_replace:
        return _eval(
            False,
            "PHP_CLIENT_RECONNECT_TRANSPORT_LEAK",
            "Client::connect() must close the previously owned transport before replacing it (#614).",
            {"previous_transport_closed_before_replace": False},
        )

    pending_entries: Sequence[Mapping[str, Any]] = list(payload.get("pending_entries") or [])
    now_epoch_s = int(payload.get("now_epoch_s", 1000))
    grace_period_s = int(payload.get("grace_period_s", 60))

    for entry in pending_entries:
        deadline_s = int(entry.get("timeout_at_epoch_s", 900))
        stream_alive = bool(entry.get("stream_alive", False))
        forgotten_on_new_request = bool(entry.get("forgotten_on_new_request", True))
        if now_epoch_s > deadline_s + grace_period_s and not stream_alive and not forgotten_on_new_request:
            return _eval(
                False,
                "PHP_VANISHED_STREAM_PENDING_REQUEST_LEAK",
                "Registering a new client request must per-key forget() pending entries and stored answers past timeout + 60s grace period (#596).",
                {"entry_id": entry.get("id"), "now_epoch_s": now_epoch_s, "deadline_s": deadline_s},
            )
        if now_epoch_s <= deadline_s + grace_period_s and stream_alive and forgotten_on_new_request:
            return _eval(
                False,
                "PHP_LIVE_STREAM_REQUEST_PREMATURELY_DROPPED",
                "Pending client request on a live stream within the 60s grace period must not be dropped by another stream (#596).",
                {"entry_id": entry.get("id")},
            )

    return _eval(
        True,
        "PHP_RECONNECT_CLOSE_AND_VANISHED_STREAM_GC_VALID",
        "PHP Client reconnect transport cleanup and vanished-stream pending entry forget() verified (#614/#596).",
        {"checked_entries": len(pending_entries)},
    )


# ---------------------------------------------------------------------------
# PR-13: modelcontextprotocol/php-sdk#594 & #593
# Per-request progress token isolation & subscriptions/listen listChanged scope
# ---------------------------------------------------------------------------
def evaluate_php_gateway_progress_token_and_list_changed_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    parallel_calls: Sequence[Mapping[str, Any]] = list(payload.get("parallel_calls") or [])
    for call in parallel_calls:
        req_token = call.get("request_progress_token")
        emitted_token = call.get("emitted_progress_token")
        if req_token != emitted_token:
            return _eval(
                False,
                "PHP_GATEWAY_SHARED_SESSION_PROGRESS_TOKEN_COLLISION",
                "ClientGateway::progress() must read the progress token from the active Request's _meta rather than the shared session (#594).",
                {"call_id": call.get("call_id"), "expected": req_token, "emitted": emitted_token},
            )

    initialize_announces_list_changed = bool(
        payload.get("initialize_announces_list_changed", False)
    )
    has_notification_bus = bool(payload.get("has_notification_bus", True))
    registry_publishes_list_changes = bool(
        payload.get("registry_publishes_list_changes", True)
    )
    discover_announces_list_changed = bool(
        payload.get("discover_announces_list_changed", True)
    )

    if initialize_announces_list_changed:
        return _eval(
            False,
            "PHP_INITIALIZE_CARRIES_DEAD_LIST_CHANGED",
            "InitializeHandler must strip listChanged via ServerCapabilities::withoutListChanged() because list changes only flow over subscriptions/listen (#593).",
            {"initialize_announces_list_changed": True},
        )

    expected_discover = has_notification_bus and registry_publishes_list_changes
    if discover_announces_list_changed != expected_discover:
        return _eval(
            False,
            "PHP_DISCOVER_LIST_CHANGED_CAPABILITY_MISMATCH",
            "Detected capabilities on server/discover must announce listChanged iff a notification bus and change-publishing registry are wired (#593).",
            {
                "expected_discover": expected_discover,
                "discover_announces_list_changed": discover_announces_list_changed,
            },
        )

    return _eval(
        True,
        "PHP_GATEWAY_PROGRESS_AND_LIST_CHANGED_VALID",
        "Per-request ClientGateway progress token isolation and subscriptions/listen listChanged scoping verified (#594/#593).",
        {"parallel_calls": len(parallel_calls), "discover_announces_list_changed": discover_announces_list_changed},
    )


# ---------------------------------------------------------------------------
# PR-14: modelcontextprotocol/php-sdk#605 & #595
# Structured-content-only CallToolResult & out-of-band FileSessionStore GC
# ---------------------------------------------------------------------------
def evaluate_php_structured_tool_output_and_session_gc_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    structured_content = payload.get("structured_content")
    content_blocks: Sequence[Any] = list(payload.get("content_blocks") or [])
    auto_duplicated_json_text = bool(payload.get("auto_duplicated_json_text", False))
    session_store_kind = str(payload.get("session_store_kind", "file"))
    inline_gc_probability = float(payload.get("inline_gc_probability", 0.0))
    cron_gc_configured = bool(payload.get("cron_gc_configured", True))

    if structured_content is not None and len(content_blocks) == 0 and auto_duplicated_json_text:
        return _eval(
            False,
            "PHP_STRUCTURED_ONLY_TOOL_TEXT_DUPLICATED",
            "CallToolResult with structuredContent and empty content[] must omit redundant JSON text block (#605).",
            {"auto_duplicated_json_text": True},
        )

    if session_store_kind == "file" and (inline_gc_probability > 0.0 or not cron_gc_configured):
        return _eval(
            False,
            "PHP_FILE_SESSION_STORE_INLINE_GC_LATENCY_SPIKE",
            "Busy production FileSessionStore deployments must disable inline directory-scan GC and run gc() out of band via cron or use Psr16SessionStore (#595).",
            {
                "session_store_kind": session_store_kind,
                "inline_gc_probability": inline_gc_probability,
                "cron_gc_configured": cron_gc_configured,
            },
        )

    return _eval(
        True,
        "PHP_STRUCTURED_TOOL_OUTPUT_AND_SESSION_GC_VALID",
        "Structured-content-only CallToolResult and out-of-band FileSessionStore GC configuration verified (#605/#595).",
        {"session_store_kind": session_store_kind},
    )


# ---------------------------------------------------------------------------
# PR-15: modelcontextprotocol/kotlin-sdk#1134
# Cold lazy Flow pagination helpers & repeated/cyclic nextCursor detection
# ---------------------------------------------------------------------------
def evaluate_kotlin_flow_pagination_and_cursor_cycle_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    flow_is_cold = bool(payload.get("flow_is_cold", True))
    requests_sent_before_collect = int(payload.get("requests_sent_before_collect", 0))
    in_flight_page_cancelled_on_take = bool(
        payload.get("in_flight_page_cancelled_on_take", True)
    )
    meta_forwarded_every_page = bool(payload.get("meta_forwarded_every_page", True))
    starting_cursor = payload.get("starting_cursor")
    page_next_cursors: Sequence[str | None] = list(payload.get("page_next_cursors") or [])
    threw_illegal_state_on_cycle = bool(payload.get("threw_illegal_state_on_cycle", False))

    if not flow_is_cold or requests_sent_before_collect > 0:
        return _eval(
            False,
            "KOTLIN_FLOW_EAGER_PREFETCH_BEFORE_COLLECT",
            "toolsFlow/promptsFlow/resourcesFlow/resourceTemplatesFlow must be cold and send nothing before collection (#1134).",
            {"requests_sent_before_collect": requests_sent_before_collect},
        )

    if not in_flight_page_cancelled_on_take or not meta_forwarded_every_page:
        return _eval(
            False,
            "KOTLIN_FLOW_CANCELLATION_OR_META_PROPAGATION_BROKEN",
            "Flow pagination must forward _meta on every page and cancel in-flight requests on take(n)/first() (#1134).",
            {
                "in_flight_page_cancelled_on_take": in_flight_page_cancelled_on_take,
                "meta_forwarded_every_page": meta_forwarded_every_page,
            },
        )

    seen_cursors: set[str] = set()
    if isinstance(starting_cursor, str) and starting_cursor:
        seen_cursors.add(starting_cursor)

    cycle_detected = False
    for nxt in page_next_cursors:
        if nxt is None:
            break
        if nxt in seen_cursors:
            cycle_detected = True
            break
        seen_cursors.add(nxt)

    if cycle_detected and not threw_illegal_state_on_cycle:
        return _eval(
            False,
            "KOTLIN_FLOW_CURSOR_CYCLE_INFINITE_LOOP",
            "Flow pagination must track all seen cursors (including starting cursor) and throw IllegalStateException on repeated/cyclic nextCursor (#1134).",
            {"page_next_cursors": list(page_next_cursors), "starting_cursor": starting_cursor},
        )

    return _eval(
        True,
        "KOTLIN_FLOW_PAGINATION_AND_CYCLE_GUARD_VALID",
        "Cold lazy Flow pagination, _meta forwarding, cancellation, and cyclic nextCursor guard verified (#1134).",
        {"visited_pages": len(page_next_cursors), "cycle_detected": cycle_detected},
    )


# ---------------------------------------------------------------------------
# PR-16: modelcontextprotocol/kotlin-sdk#1131, #1130, & #1128
# Kotlin SDK 0.16.0 SSE deprecation (SEP-2596) & ERROR/HIDDEN migration cycle
# ---------------------------------------------------------------------------
DEPRECATED_SSE_SYMBOLS = {
    "SseClientTransport",
    "mcpSseTransport",
    "mcpSse",
    "SseServerTransport",
    "Route.mcp",
    "Application.mcp",
}
ERROR_LEVEL_SYMBOLS_016 = {
    "StreamableHttpServerTransport(enableJsonResponse)",
    "StreamableHttpClientTransport(reconnectionTime)",
    "ElicitRequest.requestedSchema",
    "ClientCapabilities(sampling: JsonObject?)",
    "Configuration.enableDnsRebindingProtection",
    "Configuration.allowedHosts",
    "Configuration.allowedOrigins",
}
REMOVED_OR_HIDDEN_SYMBOLS_016 = {
    "mcpStatelessStreamableHttp",
    "StdioServerTransport(inputStream, outputStream)",
}


def evaluate_kotlin_016_sse_deprecation_and_api_migration_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    sdk_version = str(payload.get("sdk_version", "0.16.0"))
    transport_symbol = str(payload.get("transport_symbol", "StreamableHttpClientTransport"))
    sse_deprecation_warning_acknowledged = bool(
        payload.get("sse_deprecation_warning_acknowledged", False)
    )
    used_legacy_symbols: Sequence[str] = list(payload.get("used_legacy_symbols") or [])

    if sdk_version != "0.16.0":
        return _eval(
            False,
            "KOTLIN_SDK_VERSION_MISMATCH",
            "Target Kotlin SDK release must be 0.16.0 (#1131).",
            {"sdk_version": sdk_version},
        )

    if transport_symbol in DEPRECATED_SSE_SYMBOLS and not sse_deprecation_warning_acknowledged:
        return _eval(
            False,
            "KOTLIN_DEPRECATED_SSE_TRANSPORT_UNACKNOWLEDGED",
            "SSE transport APIs are @Deprecated(WARNING) in 0.16.0 in favor of Streamable HTTP per SEP-2596 (#1130).",
            {"transport_symbol": transport_symbol},
        )

    for sym in used_legacy_symbols:
        if sym in REMOVED_OR_HIDDEN_SYMBOLS_016 or sym in ERROR_LEVEL_SYMBOLS_016:
            return _eval(
                False,
                "KOTLIN_016_ERROR_OR_REMOVED_API_USED",
                "0.9.0-0.15.0 deprecated symbols elevated to ERROR/HIDDEN or removed in 0.16.0 must not be called (#1128).",
                {"forbidden_symbol": sym},
            )

    return _eval(
        True,
        "KOTLIN_016_SSE_AND_DEPRECATION_CYCLE_VALID",
        "Kotlin SDK 0.16.0 SEP-2596 SSE deprecation and ERROR/HIDDEN symbol migration verified (#1131/#1130/#1128).",
        {"sdk_version": sdk_version, "transport_symbol": transport_symbol},
    )
