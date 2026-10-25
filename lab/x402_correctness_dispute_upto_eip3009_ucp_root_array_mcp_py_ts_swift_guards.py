"""Stage 240 (240-Stage Milestone!): Deterministic protocol security guards (`PR-01..PR-16`) covering:
- x402 Foundation (`#3868` Correctness & Dispute Extension bonded verdicts, `#3867` EVM `upto` `eip3009`
  stateless proxy `0x40208Cd083acD9559Ce44742c4BcD9Cf04850006`, `#3864` Java decode-before-dot-segment
  path normalization, `#3857` legacy raw-path `%2F`/`%5C` parameter matching, `#3862` Go server wildcard
  scheme lookup & hook isolation, `#3860`/`#3859` Stellar contract account `C...` `authorizeEntry` &
  `upto` scheme, `#3858` batch-settlement refund/prior-process claim drain & `ErrNothingToSettle` no-op,
  `#3855` paywall script-safe `<` JSON escaping, `#3865` server replay guard)
- Universal Commerce Protocol (`#948` root-array schema anti-pattern guard, `#942` `source-map-js >= 1.2.2`
  `CVE-2026-93749`, `#941`/`#935` media-variants release backports, `#928` single-pass base-path stripping)
- MCP Python SDK (`#3759`/`#3744` `HEAD /sse` `405 Method Not Allowed` with `Allow: GET` after auth,
  `#3758`/`#3756`/`#3746` bare `dict`/`set`/`frozenset` structured output vs bare `list`/`tuple` content-block
  safety & `typing.Dict` origin check, `#3757` stripping generated `<func>Arguments`/`<func>Output` &
  property-derived schema titles, `#3743`/`#3755` RFC 6749 §5.2 & RFC 7009 `/token` & `/revoke` error codes
  and `WWW-Authenticate: Basic realm="OAuth"`)
- MCP TypeScript SDK (`#3095`/`#3081`/`#3096` one-hop `$ref` to typeless object-shaped `$defs` & v1 prompt
  icons, `#3092`/`#3072`/`#3093` monotonic `_generationBase` across `resetForReconnect` & atomic
  `cacheToolMetadata`, `#3091`/`#3073` post-response `AbortSignal` cleanup & `StdioClientTransport` shared
  `drain` / `[exited, close-pending]` guard, `#3085`/`#3082`/`#3074` opt-in `scopeForRefresh`, non-blocking
  unread POST body release & exact-URI static resource lookup, `#3071`/`#3064`/`#3063`/`#3087` exact
  string/number response ID & progress token correlation, `2025-11-25` `sampling.context` capability gate &
  plain `Mcp-Param-*`/`Mcp-Name` ASCII validation `-32020`)
- MCP Swift SDK (`#307`/`#305`/`#303`/`#300` stateful HTTP recovery after `DELETE`, full RFC 7230 §3.2.6
  `quoted-pair` unescaping in `WWW-Authenticate`, bias-free PKCE byte ceiling `197` & RFC 6749 §2.3.1
  `client_secret_basic` encoding, `#298`/`#297`/`#301`/`#304` stateless HTTP private request ID isolation
  during cancellation & `StdioTransport` descriptor blocking-flag restoration on disconnect)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, unquote


@dataclass(frozen=True)
class GuardEvaluation:
    passed: bool
    code: str
    reason: str
    details: dict[str, Any]


UPTO_EIP3009_PREAUDIT_PROXY = "0x40208Cd083acD9559Ce44742c4BcD9Cf04850006"
PKCE_UNRESERVED_RADIX = 66
PKCE_MAX_UNBIASED_BYTE = PKCE_UNRESERVED_RADIX * (256 // PKCE_UNRESERVED_RADIX) - 1  # 197


# ---------------------------------------------------------------------------
# PR-01: x402#3868 Correctness & Dispute Extension (bonded verdicts)
# ---------------------------------------------------------------------------
def evaluate_x402_correctness_dispute_bonded_verdict_guard(
    *,
    resolver: str,
    ed25519_signature_valid: bool,
    prev_verdict_hash: str,
    expected_prev_verdict_hash: str,
    bond_balance_minor: int,
    slashed_total_minor: int,
    per_verdict_max_minor: int,
    disputed_claim_minor: int,
    custody_threshold_met: bool = True,
) -> GuardEvaluation:
    if not resolver or not resolver.strip():
        return GuardEvaluation(
            passed=False,
            code="X402_DISPUTE_MISSING_RESOLVER",
            reason="Correctness verdict must name a resolver authority.",
            details={"resolver": resolver},
        )
    if not ed25519_signature_valid or not custody_threshold_met:
        return GuardEvaluation(
            passed=False,
            code="X402_DISPUTE_INVALID_VERDICT_SIGNATURE_OR_CUSTODY",
            reason="Verdict Ed25519 signature or 2-of-2 notary bond custody check failed.",
            details={
                "ed25519_signature_valid": ed25519_signature_valid,
                "custody_threshold_met": custody_threshold_met,
            },
        )
    if prev_verdict_hash != expected_prev_verdict_hash:
        return GuardEvaluation(
            passed=False,
            code="X402_DISPUTE_VERDICT_HASH_CHAIN_BROKEN",
            reason="Verdict hash chain does not match the prior recorded verdict digest.",
            details={
                "prev_verdict_hash": prev_verdict_hash,
                "expected_prev_verdict_hash": expected_prev_verdict_hash,
            },
        )
    effective_bond_minor = bond_balance_minor - max(0, slashed_total_minor)
    if per_verdict_max_minor <= 0 or effective_bond_minor < per_verdict_max_minor:
        return GuardEvaluation(
            passed=False,
            code="X402_DISPUTE_BOND_UNDERCOLLATERALIZED",
            reason="On-chain effective bond balance after slashes is below declared per_verdict_max.",
            details={
                "effective_bond_minor": effective_bond_minor,
                "per_verdict_max_minor": per_verdict_max_minor,
            },
        )
    if disputed_claim_minor <= 0 or disputed_claim_minor > per_verdict_max_minor:
        return GuardEvaluation(
            passed=False,
            code="X402_DISPUTE_CLAIM_EXCEEDS_PER_VERDICT_MAX",
            reason="Verdict economic trust is bounded by per_verdict_max; claim exceeds slashable cap.",
            details={
                "disputed_claim_minor": disputed_claim_minor,
                "per_verdict_max_minor": per_verdict_max_minor,
            },
        )
    return GuardEvaluation(
        passed=True,
        code="X402_DISPUTE_BONDED_VERDICT_OK",
        reason="Hash-chained Ed25519 verdict verified within slashable per_verdict_max bond cap.",
        details={
            "resolver": resolver,
            "effective_bond_minor": effective_bond_minor,
            "disputed_claim_minor": disputed_claim_minor,
        },
    )


# ---------------------------------------------------------------------------
# PR-02: x402#3867 EVM upto eip3009 stateless proxy contracts
# ---------------------------------------------------------------------------
def evaluate_x402_evm_upto_eip3009_proxy_guard(
    *,
    proxy_address: str,
    authorization_method: str,
    nonce_matches_payto_settler_salt: bool,
    caller_address: str,
    committed_settler: str,
    signed_maximum_minor: int,
    actual_amount_minor: int,
    payer_balance_minor: int,
    merchant_paid_minor: int,
    payer_refunded_minor: int,
) -> GuardEvaluation:
    if proxy_address != UPTO_EIP3009_PREAUDIT_PROXY:
        return GuardEvaluation(
            passed=False,
            code="X402_UPTO_EIP3009_UNEXPECTED_PROXY",
            reason="EVM upto eip3009 proxy address does not match pinned deterministic CREATE2 address.",
            details={"proxy_address": proxy_address},
        )
    if authorization_method != "receiveWithAuthorization":
        return GuardEvaluation(
            passed=False,
            code="X402_UPTO_EIP3009_FRONT_RUNNABLE_AUTH_METHOD",
            reason="EVM upto eip3009 must use receiveWithAuthorization to prevent third-party front-running.",
            details={"authorization_method": authorization_method},
        )
    if not nonce_matches_payto_settler_salt:
        return GuardEvaluation(
            passed=False,
            code="X402_UPTO_EIP3009_NONCE_COMMITMENT_MISMATCH",
            reason="EIP-3009 nonce must commit to (payTo, settler, salt_bytes32).",
            details={"nonce_matches_payto_settler_salt": nonce_matches_payto_settler_salt},
        )
    if caller_address.lower() != committed_settler.lower():
        return GuardEvaluation(
            passed=False,
            code="X402_UPTO_EIP3009_UNAUTHORIZED_SETTLER",
            reason="Only the committed settler may execute upto eip3009 settlement.",
            details={"caller_address": caller_address, "committed_settler": committed_settler},
        )
    if actual_amount_minor <= 0 or actual_amount_minor > signed_maximum_minor:
        return GuardEvaluation(
            passed=False,
            code="X402_UPTO_EIP3009_INVALID_ACTUAL_AMOUNT",
            reason="Settlement requires 0 < actualAmount <= signedMaximum.",
            details={
                "actual_amount_minor": actual_amount_minor,
                "signed_maximum_minor": signed_maximum_minor,
            },
        )
    if payer_balance_minor < signed_maximum_minor:
        return GuardEvaluation(
            passed=False,
            code="X402_UPTO_EIP3009_INSUFFICIENT_MAX_BALANCE",
            reason="Payer must retain full signedMaximum balance so proxy can receive before refunding remainder.",
            details={
                "payer_balance_minor": payer_balance_minor,
                "signed_maximum_minor": signed_maximum_minor,
            },
        )
    if (
        merchant_paid_minor != actual_amount_minor
        or merchant_paid_minor + payer_refunded_minor != signed_maximum_minor
    ):
        return GuardEvaluation(
            passed=False,
            code="X402_UPTO_EIP3009_CONSERVATION_VIOLATION",
            reason="Proxy must pay actualAmount to merchant and atomically refund signedMaximum - actualAmount.",
            details={
                "merchant_paid_minor": merchant_paid_minor,
                "payer_refunded_minor": payer_refunded_minor,
                "signed_maximum_minor": signed_maximum_minor,
            },
        )
    return GuardEvaluation(
        passed=True,
        code="X402_UPTO_EIP3009_PROXY_OK",
        reason="EVM upto eip3009 receiveWithAuthorization settlement and atomic remainder refund verified.",
        details={
            "merchant_paid_minor": merchant_paid_minor,
            "payer_refunded_minor": payer_refunded_minor,
        },
    )


# ---------------------------------------------------------------------------
# PR-03: x402#3864 Java decode-before-dot-segments & #3857 legacy raw-path match
# ---------------------------------------------------------------------------
def _normalize_java_filter_path(raw_path: str) -> str:
    decoded = unquote(raw_path)
    segments: list[str] = []
    for seg in decoded.split("/"):
        if not seg or seg == ".":
            continue
        if seg == "..":
            if segments:
                segments.pop()
            continue
        segments.append(seg)
    return "/" + "/".join(segments)


def _match_route_pattern(path: str, pattern: str) -> bool:
    norm_path = path.replace("\\", "/")
    p_segs = [s for s in norm_path.split("/") if s]
    r_segs = [s for s in pattern.split("/") if s]
    if len(p_segs) != len(r_segs):
        return False
    for p_seg, r_seg in zip(p_segs, r_segs):
        if (r_seg.startswith("[") and r_seg.endswith("]")) or r_seg.startswith(":"):
            if not p_seg:
                return False
            continue
        if p_seg != r_seg:
            return False
    return True


def evaluate_x402_java_dot_decode_and_legacy_raw_route_guard(
    *,
    raw_request_path: str,
    protected_exact_paths: set[str],
    protected_param_patterns: tuple[str, ...],
    payment_present: bool,
) -> GuardEvaluation:
    normalized_java_path = _normalize_java_filter_path(raw_request_path)
    decoded_view = unquote(raw_request_path)
    requires_payment = normalized_java_path in protected_exact_paths or any(
        _match_route_pattern(raw_request_path, pat) or _match_route_pattern(decoded_view, pat)
        for pat in protected_param_patterns
    )
    if requires_payment and not payment_present:
        return GuardEvaluation(
            passed=False,
            code="X402_PATH_TRAVERSAL_OR_ENCODED_PARAM_402_REQUIRED",
            reason="Encoded dot-segment path or %2F/%5C parameter route matched a protected route; 402 required.",
            details={
                "raw_request_path": raw_request_path,
                "normalized_java_path": normalized_java_path,
                "requires_payment": True,
            },
        )
    return GuardEvaluation(
        passed=True,
        code="X402_PATH_NORMALIZATION_AND_RAW_ROUTE_OK",
        reason="Java decode-first dot-segment normalization and legacy raw-path route matching satisfied.",
        details={
            "raw_request_path": raw_request_path,
            "normalized_java_path": normalized_java_path,
            "requires_payment": requires_payment,
        },
    )


# ---------------------------------------------------------------------------
# PR-04: x402#3862 Go wildcard scheme lookup & #3860/#3859 Stellar C-account / upto
# ---------------------------------------------------------------------------
def evaluate_x402_go_wildcard_scheme_and_stellar_contract_guard(
    *,
    registered_schemes: dict[str, dict[str, Any]],
    requested_network: str,
    stellar_payer_account: str,
    has_custom_authorize_entry: bool,
    stellar_upto_actual_minor: int,
    stellar_upto_max_minor: int,
) -> GuardEvaluation:
    matched_entry: dict[str, Any] | None = None
    matched_key: str | None = None
    if requested_network in registered_schemes:
        matched_key = requested_network
        matched_entry = registered_schemes[requested_network]
    elif ":" in requested_network:
        wildcard_key = requested_network.split(":", 1)[0] + ":*"
        if wildcard_key in registered_schemes:
            matched_key = wildcard_key
            matched_entry = registered_schemes[wildcard_key]
    if matched_entry is None or matched_key is None:
        return GuardEvaluation(
            passed=False,
            code="X402_GO_SCHEME_NOT_REGISTERED",
            reason="Neither exact network nor namespace wildcard scheme is registered on Go server.",
            details={"requested_network": requested_network},
        )
    if matched_key == requested_network and matched_entry.get("inherited_wildcard_hooks", False):
        return GuardEvaluation(
            passed=False,
            code="X402_GO_EXACT_SCHEME_INHERITED_WILDCARD_HOOKS",
            reason="Exact network registration without hooks must not inherit wildcard registration hooks.",
            details={"matched_key": matched_key},
        )
    if stellar_payer_account.startswith("C") and not has_custom_authorize_entry:
        return GuardEvaluation(
            passed=False,
            code="X402_STELLAR_CONTRACT_PAYER_MISSING_AUTHORIZE_ENTRY",
            reason="Stellar contract account (C..., strkey byte 16) requires custom authorizeEntry override.",
            details={"stellar_payer_account": stellar_payer_account},
        )
    if stellar_upto_actual_minor <= 0 or stellar_upto_actual_minor > stellar_upto_max_minor:
        return GuardEvaluation(
            passed=False,
            code="X402_STELLAR_UPTO_AMOUNT_OUT_OF_BOUNDS",
            reason="Stellar upto settlement requires 0 < actual <= max authorized.",
            details={
                "stellar_upto_actual_minor": stellar_upto_actual_minor,
                "stellar_upto_max_minor": stellar_upto_max_minor,
            },
        )
    return GuardEvaluation(
        passed=True,
        code="X402_GO_WILDCARD_AND_STELLAR_CONTRACT_OK",
        reason="Go wildcard scheme lookup with hook isolation and Stellar C-account / upto rules verified.",
        details={"matched_key": matched_key, "hooks": matched_entry.get("hooks", [])},
    )


# ---------------------------------------------------------------------------
# PR-05: x402#3858 batch-settlement refund/prior claims, #3855 paywall XSS & #3865 replay
# ---------------------------------------------------------------------------
def evaluate_x402_batch_refund_settle_paywall_xss_replay_guard(
    *,
    total_claimed_minor: int,
    total_settled_minor: int,
    facilitator_err: str | None,
    on_settle_called_on_empty_tx: bool,
    paywall_serialized_json: str,
    payment_payload_hash: str,
    seen_payload_hashes: set[str],
) -> GuardEvaluation:
    nothing_to_settle = (
        total_claimed_minor <= total_settled_minor
        or facilitator_err == "invalid_batch_settlement_evm_nothing_to_settle"
    )
    if nothing_to_settle and on_settle_called_on_empty_tx:
        return GuardEvaluation(
            passed=False,
            code="X402_BATCH_SETTLE_SPURIOUS_ON_SETTLE_ON_EMPTY_TX",
            reason="ErrNothingToSettle must resolve to {transaction: ''} without calling onSettle or onError.",
            details={"total_claimed_minor": total_claimed_minor, "total_settled_minor": total_settled_minor},
        )
    if "<" in paywall_serialized_json or "</script" in paywall_serialized_json.lower():
        return GuardEvaluation(
            passed=False,
            code="X402_PAYWALL_UNESCAPED_SCRIPT_TAG_XSS",
            reason="Paywall inline JSON must escape '<' as '\\u003c' to prevent reflected XSS.",
            details={"paywall_serialized_json": paywall_serialized_json},
        )
    if payment_payload_hash in seen_payload_hashes:
        return GuardEvaluation(
            passed=False,
            code="X402_SERVER_REPLAY_DETECTED",
            reason="Server replay guard rejected duplicate payment payload hash.",
            details={"payment_payload_hash": payment_payload_hash},
        )
    return GuardEvaluation(
        passed=True,
        code="X402_BATCH_SETTLE_PAYWALL_XSS_REPLAY_OK",
        reason="Batch-settlement refund claim drain, script-safe paywall JSON, and replay guard verified.",
        details={"nothing_to_settle": nothing_to_settle},
    )


# ---------------------------------------------------------------------------
# PR-06: ucp#948 root-array anti-pattern, #942 source-map-js, #941/#935, #928
# ---------------------------------------------------------------------------
def evaluate_ucp_root_array_schema_and_release_hygiene_guard(
    *,
    schema_kind: str,
    root_schema_type: str,
    shared_contains_constraint: bool,
    source_map_js_version: tuple[int, int, int],
    media_variants_backported_branches: set[str],
    site_base_path: str,
    raw_doc_link: str,
    stripped_doc_link: str,
) -> GuardEvaluation:
    if root_schema_type == "array":
        if schema_kind in {"capability", "extension", "operation_payload"} or not shared_contains_constraint:
            return GuardEvaluation(
                passed=False,
                code="UCP_ROOT_ARRAY_SCHEMA_ANTI_PATTERN",
                reason="Capability, extension, and operation payload schemas MUST NOT use root type 'array'.",
                details={"schema_kind": schema_kind, "root_schema_type": root_schema_type},
            )
    if source_map_js_version < (1, 2, 2):
        return GuardEvaluation(
            passed=False,
            code="UCP_CVE_2026_93749_SOURCE_MAP_JS",
            reason="source-map-js must be >= 1.2.2 to remediate CVE-2026-93749.",
            details={"source_map_js_version": source_map_js_version},
        )
    required_backports = {"release/2026-08-25", "release/2026-04-08"}
    if not required_backports.issubset(media_variants_backported_branches):
        return GuardEvaluation(
            passed=False,
            code="UCP_MEDIA_VARIANTS_BACKPORT_MISSING",
            reason="Media variants (#690) must be backported to both 2026-08-25 and 2026-04-08 release branches.",
            details={"branches": sorted(media_variants_backported_branches)},
        )
    expected_stripped = (
        raw_doc_link[len(site_base_path) :]
        if site_base_path and raw_doc_link.startswith(site_base_path)
        else raw_doc_link
    )
    if stripped_doc_link != expected_stripped:
        return GuardEvaluation(
            passed=False,
            code="UCP_LINK_CHECK_DOUBLE_BASE_STRIP",
            reason="Link checker must strip site base path at most once (removeprefix, not repeated replace).",
            details={"expected_stripped": expected_stripped, "stripped_doc_link": stripped_doc_link},
        )
    return GuardEvaluation(
        passed=True,
        code="UCP_ROOT_ARRAY_AND_RELEASE_HYGIENE_OK",
        reason="UCP root-object schema rule, CVE-2026-93749 patch, backports, and single-strip link check verified.",
        details={"expected_stripped": expected_stripped},
    )


# ---------------------------------------------------------------------------
# PR-07: python-sdk#3759 & #3744 HEAD /sse -> 405 Method Not Allowed (Allow: GET)
# ---------------------------------------------------------------------------
def evaluate_mcp_python_sse_head_method_guard(
    *,
    http_method: str,
    auth_configured: bool,
    is_authenticated: bool,
    status_code: int,
    allow_header: str | None,
    sse_stream_opened: bool,
) -> GuardEvaluation:
    if auth_configured and not is_authenticated:
        if status_code != 401 or sse_stream_opened:
            return GuardEvaluation(
                passed=False,
                code="MCP_PY_SSE_UNAUTHENTICATED_HEAD_MUST_401",
                reason="Unauthenticated HEAD /sse must return 401 via RequireAuthMiddleware without opening stream.",
                details={"status_code": status_code, "sse_stream_opened": sse_stream_opened},
            )
        return GuardEvaluation(
            passed=True,
            code="MCP_PY_SSE_UNAUTHENTICATED_HEAD_401_OK",
            reason="Unauthenticated HEAD /sse answered 401 before sse_endpoint.",
            details={"status_code": status_code},
        )
    if http_method.upper() == "HEAD":
        if status_code != 405 or allow_header != "GET" or sse_stream_opened:
            return GuardEvaluation(
                passed=False,
                code="MCP_PY_SSE_HEAD_STREAM_LEAK_OR_WRONG_STATUS",
                reason="HEAD /sse must return 405 with Allow: GET without calling connect_sse().",
                details={
                    "status_code": status_code,
                    "allow_header": allow_header,
                    "sse_stream_opened": sse_stream_opened,
                },
            )
    return GuardEvaluation(
        passed=True,
        code="MCP_PY_SSE_HEAD_GUARD_OK",
        reason="MCPServer.sse_app() answers HEAD /sse with 405 and Allow: GET without opening a stream.",
        details={"status_code": status_code, "allow_header": allow_header},
    )


# ---------------------------------------------------------------------------
# PR-08: python-sdk#3758, #3756, #3746, #3757 bare dict/set output & title stripping
# ---------------------------------------------------------------------------
def evaluate_mcp_python_return_annotation_and_schema_title_guard(
    *,
    return_annotation: str,
    structured_output_opt_in: bool,
    published_output_schema: dict[str, Any] | None,
    tool_input_schema: dict[str, Any],
    explicit_field_titles: set[str],
) -> GuardEvaluation:
    if return_annotation in {"dict", "dict[str, Any]", "typing.Dict[str, int]"}:
        if not published_output_schema or published_output_schema.get("type") != "object":
            return GuardEvaluation(
                passed=False,
                code="MCP_PY_DICT_ANNOTATION_MISSING_OBJECT_SCHEMA",
                reason="Bare dict and typing.Dict[str, X] annotations must publish an object outputSchema.",
                details={"return_annotation": return_annotation, "schema": published_output_schema},
            )
    elif return_annotation in {"set", "frozenset"}:
        props = (published_output_schema or {}).get("properties", {})
        res_schema = props.get("result", {}) if isinstance(props, dict) else {}
        if res_schema.get("type") != "array" or not res_schema.get("uniqueItems"):
            return GuardEvaluation(
                passed=False,
                code="MCP_PY_SET_ANNOTATION_MISSING_WRAPPED_ARRAY_SCHEMA",
                reason="Bare set/frozenset must wrap output in {'result': {'type': 'array', 'uniqueItems': True}}.",
                details={"return_annotation": return_annotation, "schema": published_output_schema},
            )
    elif return_annotation in {"list", "tuple"} and not structured_output_opt_in:
        if published_output_schema is not None:
            return GuardEvaluation(
                passed=False,
                code="MCP_PY_BARE_LIST_DOUBLE_SENDS_CONTENT_BLOCKS",
                reason="Bare list/tuple without structured_output=True must omit outputSchema to avoid echoing ImageContent.",
                details={"return_annotation": return_annotation, "schema": published_output_schema},
            )
    root_title = tool_input_schema.get("title")
    if isinstance(root_title, str) and (
        root_title.endswith("Arguments") or root_title.endswith("Output") or root_title.endswith("DictOutput")
    ):
        return GuardEvaluation(
            passed=False,
            code="MCP_PY_GENERATED_ROOT_TITLE_NOT_STRIPPED",
            reason="Generated <func>Arguments/<func>Output/<func>DictOutput root titles must be dropped.",
            details={"root_title": root_title},
        )
    for prop_name, prop_schema in tool_input_schema.get("properties", {}).items():
        if isinstance(prop_schema, dict) and "title" in prop_schema and prop_name not in explicit_field_titles:
            return GuardEvaluation(
                passed=False,
                code="MCP_PY_GENERATED_PROPERTY_TITLE_NOT_STRIPPED",
                reason="Derived property titles must be stripped unless explicitly set via Field(title=...).",
                details={"property": prop_name, "title": prop_schema["title"]},
            )
    return GuardEvaluation(
        passed=True,
        code="MCP_PY_STRUCTURED_OUTPUT_AND_TITLE_STRIP_OK",
        reason="Python SDK structured output annotations and generated title stripping verified.",
        details={"return_annotation": return_annotation},
    )


# ---------------------------------------------------------------------------
# PR-09: python-sdk#3743 & #3755 /token & /revoke RFC 6749 §5.2 / RFC 7009 error codes
# ---------------------------------------------------------------------------
def evaluate_mcp_python_oauth_token_revoke_error_guard(
    *,
    endpoint: str,
    grant_type: str | None,
    server_supported_grants: set[str],
    client_registered_grants: set[str],
    client_auth_succeeded: bool,
    used_basic_auth_header: bool,
    returned_error_code: str,
    www_authenticate_header: str | None,
) -> GuardEvaluation:
    if not client_auth_succeeded:
        expected_error = "invalid_client"
        if returned_error_code != expected_error:
            return GuardEvaluation(
                passed=False,
                code="MCP_PY_OAUTH_WRONG_CLIENT_AUTH_ERROR",
                reason="Failed client authentication on /token or /revoke must return 'invalid_client'.",
                details={"endpoint": endpoint, "returned_error_code": returned_error_code},
            )
        if used_basic_auth_header and www_authenticate_header != 'Basic realm="OAuth"':
            return GuardEvaluation(
                passed=False,
                code="MCP_PY_OAUTH_MISSING_BASIC_REALM_HEADER",
                reason="Failed Basic authentication must include WWW-Authenticate: Basic realm=\"OAuth\" (RFC 7617 §2).",
                details={"www_authenticate_header": www_authenticate_header},
            )
        if not used_basic_auth_header and www_authenticate_header is not None:
            return GuardEvaluation(
                passed=False,
                code="MCP_PY_OAUTH_SPURIOUS_WWW_AUTH_ON_POST_BODY_AUTH",
                reason="client_secret_post failures must not attach a Basic WWW-Authenticate header.",
                details={"www_authenticate_header": www_authenticate_header},
            )
    elif endpoint == "/token" and grant_type is not None:
        if grant_type not in server_supported_grants:
            expected_error = "unsupported_grant_type"
        elif grant_type not in client_registered_grants:
            expected_error = "unauthorized_client"
        else:
            expected_error = "ok"
        if returned_error_code != expected_error:
            return GuardEvaluation(
                passed=False,
                code="MCP_PY_OAUTH_GRANT_ERROR_CODE_SWAPPED",
                reason="Unimplemented grants must return unsupported_grant_type; unregistered client grants return unauthorized_client.",
                details={
                    "grant_type": grant_type,
                    "expected_error": expected_error,
                    "returned_error_code": returned_error_code,
                },
            )
    return GuardEvaluation(
        passed=True,
        code="MCP_PY_OAUTH_ERROR_CODES_OK",
        reason="RFC 6749 §5.2 and RFC 7009 §2.2.1 /token and /revoke error codes verified.",
        details={"endpoint": endpoint, "returned_error_code": returned_error_code},
    )


# ---------------------------------------------------------------------------
# PR-10: typescript-sdk#3095, #3081, #3096 one-hop $ref to object-shaped $defs & prompt icons
# ---------------------------------------------------------------------------
def _is_provably_object_shaped(schema: dict[str, Any], root: dict[str, Any]) -> bool:
    if schema.get("type") == "object" or isinstance(schema.get("properties"), dict):
        return True
    for kw in ("oneOf", "anyOf", "allOf"):
        branches = schema.get(kw)
        if isinstance(branches, list) and branches and all(
            isinstance(b, dict) and _is_provably_object_shaped(b, {}) for b in branches
        ):
            return True
    ref = schema.get("$ref")
    if isinstance(ref, str) and root:
        for prefix, container_key in (("#/$defs/", "$defs"), ("#/definitions/", "definitions")):
            if ref.startswith(prefix):
                def_name = ref[len(prefix) :]
                defs = root.get(container_key)
                if isinstance(defs, dict) and isinstance(defs.get(def_name), dict):
                    target = defs[def_name]
                    return target.get("type") == "object" or _is_provably_object_shaped(target, {})
    return False


def evaluate_mcp_ts_ref_object_schema_and_prompt_icons_guard(
    *,
    output_schema: dict[str, Any],
    prompt_icons_preserved: bool,
) -> GuardEvaluation:
    if not _is_provably_object_shaped(output_schema, output_schema):
        return GuardEvaluation(
            passed=False,
            code="MCP_TS_OUTPUT_SCHEMA_NOT_PROVABLY_OBJECT",
            reason="outputSchema root or one-hop $defs target is not provably object-shaped.",
            details={"output_schema": output_schema},
        )
    if not prompt_icons_preserved:
        return GuardEvaluation(
            passed=False,
            code="MCP_TS_V1_PROMPT_ICONS_DROPPED",
            reason="v1 prompt registration and update must preserve prompt icons.",
            details={"prompt_icons_preserved": prompt_icons_preserved},
        )
    return GuardEvaluation(
        passed=True,
        code="MCP_TS_REF_OBJECT_SCHEMA_AND_PROMPT_ICONS_OK",
        reason="One-hop $ref to typeless object-shaped $defs entry and v1 prompt icons verified.",
        details={"object_shaped": True},
    )


# ---------------------------------------------------------------------------
# PR-11: typescript-sdk#3092, #3072, #3093 ClientResponseCache generationBase & atomic tool cache
# ---------------------------------------------------------------------------
def evaluate_mcp_ts_cache_generation_and_atomic_tool_metadata_guard(
    *,
    pre_reset_max_generation: int,
    post_reset_generation_base: int,
    current_key_generation: int | None,
    write_captured_generation: int,
    write_accepted: bool,
    malformed_schema_mid_loop: bool,
    previous_tool_cache_preserved: bool,
) -> GuardEvaluation:
    if post_reset_generation_base <= pre_reset_max_generation:
        return GuardEvaluation(
            passed=False,
            code="MCP_TS_CACHE_GENERATION_BASE_NOT_MONOTONIC",
            reason="resetForReconnect() must advance _generationBase past max pre-reset generation.",
            details={
                "pre_reset_max_generation": pre_reset_max_generation,
                "post_reset_generation_base": post_reset_generation_base,
            },
        )
    expected_write_ok = current_key_generation is not None and current_key_generation == write_captured_generation
    if write_accepted != expected_write_ok:
        return GuardEvaluation(
            passed=False,
            code="MCP_TS_CACHE_STALE_PRE_RESET_WRITE_ACCEPTED",
            reason="ClientResponseCache.write() must require exact _evictionGeneration.get(gk) === capturedGen without ?? 0 fallback.",
            details={
                "current_key_generation": current_key_generation,
                "write_captured_generation": write_captured_generation,
                "write_accepted": write_accepted,
            },
        )
    if malformed_schema_mid_loop and not previous_tool_cache_preserved:
        return GuardEvaluation(
            passed=False,
            code="MCP_TS_NON_ATOMIC_TOOL_METADATA_CACHE",
            reason="cacheToolMetadata must build validators in local maps and swap only after all schemas compile.",
            details={"previous_tool_cache_preserved": previous_tool_cache_preserved},
        )
    return GuardEvaluation(
        passed=True,
        code="MCP_TS_CACHE_GENERATION_AND_ATOMIC_METADATA_OK",
        reason="Monotonic post-reset cache generation guard and atomic cacheToolMetadata swap verified.",
        details={"post_reset_generation_base": post_reset_generation_base},
    )


# ---------------------------------------------------------------------------
# PR-12: typescript-sdk#3091 post-response abort listener & #3073 stdio drain/exit guard
# ---------------------------------------------------------------------------
def evaluate_mcp_ts_abort_cleanup_and_stdio_drain_guard(
    *,
    response_received: bool,
    late_abort_sent_cancelled_notification: bool,
    abort_listener_removed_on_finally: bool,
    concurrent_backpressured_sends: int,
    stdin_drain_listener_count: int,
    process_exited_before_close: bool,
    late_send_rejected_not_connected: bool,
    waiting_sends_settled_on_exit: bool,
) -> GuardEvaluation:
    if response_received and (late_abort_sent_cancelled_notification or not abort_listener_removed_on_finally):
        return GuardEvaluation(
            passed=False,
            code="MCP_TS_LATE_ABORT_CANCELLED_OR_LISTENER_LEAK",
            reason="Once response arrives, abort listener must be removed and late abort() must not send notifications/cancelled.",
            details={
                "late_abort_sent_cancelled_notification": late_abort_sent_cancelled_notification,
                "abort_listener_removed_on_finally": abort_listener_removed_on_finally,
            },
        )
    if concurrent_backpressured_sends > 0 and stdin_drain_listener_count > 1:
        return GuardEvaluation(
            passed=False,
            code="MCP_TS_STDIO_DRAIN_LISTENER_ACCUMULATION",
            reason="StdioClientTransport.send() must share at most 1 drain listener on stdin under back-pressure.",
            details={
                "concurrent_backpressured_sends": concurrent_backpressured_sends,
                "stdin_drain_listener_count": stdin_drain_listener_count,
            },
        )
    if process_exited_before_close and (
        not late_send_rejected_not_connected or not waiting_sends_settled_on_exit
    ):
        return GuardEvaluation(
            passed=False,
            code="MCP_TS_STDIO_EXITED_CLOSE_PENDING_WINDOW_LEAK",
            reason="In [exited, close-pending] window, waiting sends must settle on exit and new sends must reject with NotConnected.",
            details={
                "late_send_rejected_not_connected": late_send_rejected_not_connected,
                "waiting_sends_settled_on_exit": waiting_sends_settled_on_exit,
            },
        )
    return GuardEvaluation(
        passed=True,
        code="MCP_TS_ABORT_AND_STDIO_DRAIN_OK",
        reason="Post-response abort listener cleanup and shared stdio drain / exit settlement verified.",
        details={"stdin_drain_listener_count": stdin_drain_listener_count},
    )


# ---------------------------------------------------------------------------
# PR-13: typescript-sdk#3085 scopeForRefresh, #3082 non-blocking releaseBody & #3074 exact-URI read
# ---------------------------------------------------------------------------
def evaluate_mcp_ts_refresh_scope_unread_body_and_exact_uri_guard(
    *,
    scope_for_refresh: str | None,
    sent_refresh_scope: str | None,
    server_returned_scope: str | None,
    resulting_token_scope: str | None,
    awaited_unread_post_body: bool,
    registered_resources: dict[str, dict[str, Any]],
    requested_resource_uri: str,
    served_resource_key: str,
) -> GuardEvaluation:
    expected_sent_scope = scope_for_refresh if scope_for_refresh else None
    if sent_refresh_scope != expected_sent_scope:
        return GuardEvaluation(
            passed=False,
            code="MCP_TS_REFRESH_SCOPE_MISMATCH",
            reason="refreshAuthorization must send scope only when scopeForRefresh/option is non-empty.",
            details={"scope_for_refresh": scope_for_refresh, "sent_refresh_scope": sent_refresh_scope},
        )
    expected_token_scope = (
        server_returned_scope if server_returned_scope is not None else expected_sent_scope
    )
    if expected_sent_scope is not None and resulting_token_scope != expected_token_scope:
        return GuardEvaluation(
            passed=False,
            code="MCP_TS_REFRESH_OMITTED_SCOPE_NOT_PRESERVED",
            reason="When a refresh scope was sent and response omits scope, sent scope must stay on returned tokens (RFC 6749 §5.1).",
            details={
                "expected_token_scope": expected_token_scope,
                "resulting_token_scope": resulting_token_scope,
            },
        )
    if awaited_unread_post_body:
        return GuardEvaluation(
            passed=False,
            code="MCP_TS_UNREAD_POST_BODY_AWAITED",
            reason="releaseBody() must cancel/release unread 2xx POST bodies without awaiting stream completion.",
            details={"awaited_unread_post_body": awaited_unread_post_body},
        )
    expected_key = (
        requested_resource_uri
        if requested_resource_uri in registered_resources
        else requested_resource_uri.rstrip("/") + "/"
    )
    if served_resource_key != expected_key:
        return GuardEvaluation(
            passed=False,
            code="MCP_TS_STATIC_RESOURCE_EXACT_URI_BYPASSED",
            reason="resources/read and scope challenges must look up the exact registered URI before URL-parsed form.",
            details={"expected_key": expected_key, "served_resource_key": served_resource_key},
        )
    if registered_resources.get(expected_key, {}).get("enabled") is False:
        return GuardEvaluation(
            passed=False,
            code="MCP_TS_DISABLED_EXACT_URI_FELL_THROUGH_TO_PARSED_TWIN",
            reason="A disabled exact-key static resource must be rejected rather than falling back to its parsed-form twin.",
            details={"expected_key": expected_key},
        )
    return GuardEvaluation(
        passed=True,
        code="MCP_TS_REFRESH_SCOPE_RELEASE_BODY_EXACT_URI_OK",
        reason="Opt-in refresh scope preservation, non-blocking releaseBody(), and exact-URI resource lookup verified.",
        details={"served_resource_key": served_resource_key},
    )


# ---------------------------------------------------------------------------
# PR-14: typescript-sdk#3071 ID/progress types, #3064 sampling.context & #3063 Mcp-Param ASCII
# ---------------------------------------------------------------------------
def _is_valid_plain_mcp_header_value(value: str) -> bool:
    for ch in value:
        code = ord(ch)
        if code == 0x09 or (0x20 <= code <= 0x7E):
            continue
        return False
    return True


def evaluate_mcp_ts_id_types_sampling_context_and_header_ascii_guard(
    *,
    pending_request_id: int | str,
    incoming_response_id: int | str,
    correlated_as_match: bool,
    negotiated_protocol_version: str,
    include_context: str | None,
    client_has_sampling_context_cap: bool,
    sampling_request_allowed: bool,
    plain_mcp_header_value: str,
    header_rejected_with_minus_32020: bool,
) -> GuardEvaluation:
    exact_type_match = (
        type(pending_request_id) is type(incoming_response_id)
        and pending_request_id == incoming_response_id
    )
    if correlated_as_match != exact_type_match:
        return GuardEvaluation(
            passed=False,
            code="MCP_TS_RESPONSE_ID_TYPE_COERCION",
            reason="Protocol must preserve response ID and progress token types without Number() coercion ('0' != 0).",
            details={
                "pending_request_id": pending_request_id,
                "incoming_response_id": incoming_response_id,
                "correlated_as_match": correlated_as_match,
            },
        )
    requires_sampling_context_cap = (
        negotiated_protocol_version >= "2025-11-25"
        and include_context in {"thisServer", "allServers"}
    )
    if requires_sampling_context_cap and not client_has_sampling_context_cap and sampling_request_allowed:
        return GuardEvaluation(
            passed=False,
            code="MCP_TS_SAMPLING_CONTEXT_CAPABILITY_UNGATED",
            reason="Server.createMessage must refuse includeContext thisServer/allServers on >= 2025-11-25 without sampling.context.",
            details={
                "negotiated_protocol_version": negotiated_protocol_version,
                "include_context": include_context,
            },
        )
    valid_ascii = _is_valid_plain_mcp_header_value(plain_mcp_header_value)
    if not valid_ascii and not header_rejected_with_minus_32020:
        return GuardEvaluation(
            passed=False,
            code="MCP_TS_INVALID_PLAIN_MCP_HEADER_CHAR_ACCEPTED",
            reason="Plain Mcp-Param-* or Mcp-Name value with bytes outside 0x20..0x7E/HTAB must be rejected with 400 / -32020.",
            details={"plain_mcp_header_value": plain_mcp_header_value},
        )
    return GuardEvaluation(
        passed=True,
        code="MCP_TS_ID_TYPES_SAMPLING_CONTEXT_HEADER_ASCII_OK",
        reason="Type-safe ID correlation, 2025-11-25 sampling.context gate, and Mcp-Param-* ASCII validation verified.",
        details={"valid_ascii": valid_ascii},
    )


# ---------------------------------------------------------------------------
# PR-15: swift-sdk#307 DELETE recovery/maxSessions, #305 quoted-pair, #303 PKCE 197 & #300 Basic
# ---------------------------------------------------------------------------
def _unescape_rfc7230_quoted_pair(raw_value: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(raw_value):
        if raw_value[i] == "\\" and i + 1 < len(raw_value):
            out.append(raw_value[i + 1])
            i += 2
        else:
            out.append(raw_value[i])
            i += 1
    return "".join(out)


def evaluate_mcp_swift_session_recovery_quoted_pair_pkce_guard(
    *,
    previous_session_deleted: bool,
    reinitialize_succeeded: bool,
    active_sessions: int,
    max_sessions: int,
    at_capacity_status_code: int,
    raw_quoted_param: str,
    parsed_quoted_param: str,
    pkce_rejection_threshold_byte: int,
    client_id: str,
    client_secret: str,
    encoded_basic_pair: str,
) -> GuardEvaluation:
    if previous_session_deleted and active_sessions < max_sessions and not reinitialize_succeeded:
        return GuardEvaluation(
            passed=False,
            code="MCP_SWIFT_STATEFUL_HTTP_NO_RECOVERY_AFTER_DELETE",
            reason="Stateful HTTP endpoint must create a fresh server/transport and allow initialize after DELETE.",
            details={"previous_session_deleted": previous_session_deleted},
        )
    if active_sessions >= max_sessions and at_capacity_status_code != 503:
        return GuardEvaluation(
            passed=False,
            code="MCP_SWIFT_MAX_SESSIONS_MUST_RETURN_503",
            reason="Stateful HTTP session manager must return 503 before calling server factory when maxSessions is reached.",
            details={"active_sessions": active_sessions, "max_sessions": max_sessions},
        )
    expected_unescaped = _unescape_rfc7230_quoted_pair(raw_quoted_param)
    if parsed_quoted_param != expected_unescaped:
        return GuardEvaluation(
            passed=False,
            code="MCP_SWIFT_WWW_AUTH_QUOTED_PAIR_RESIDUAL_BACKSLASH",
            reason="WWW-Authenticate parser must unescape all RFC 7230 §3.2.6 quoted-pair sequences (\\_, \\\", \\\\).",
            details={"expected_unescaped": expected_unescaped, "parsed_quoted_param": parsed_quoted_param},
        )
    if pkce_rejection_threshold_byte != PKCE_MAX_UNBIASED_BYTE:
        return GuardEvaluation(
            passed=False,
            code="MCP_SWIFT_PKCE_MODULO_BIAS_THRESHOLD",
            reason="PKCE rejection sampling threshold must be 66 * (256 // 66) - 1 = 197 (not 198, which biases 'A').",
            details={"pkce_rejection_threshold_byte": pkce_rejection_threshold_byte},
        )
    expected_pair = f"{quote(client_id, safe='')}:{quote(client_secret, safe='')}"
    if encoded_basic_pair != expected_pair:
        return GuardEvaluation(
            passed=False,
            code="MCP_SWIFT_CLIENT_SECRET_BASIC_NOT_PERCENT_ENCODED",
            reason="Swift OAuth client_secret_basic must percent-encode client_id and client_secret per RFC 6749 §2.3.1.",
            details={"expected_pair": expected_pair, "encoded_basic_pair": encoded_basic_pair},
        )
    return GuardEvaluation(
        passed=True,
        code="MCP_SWIFT_SESSION_QUOTED_PAIR_PKCE_OK",
        reason="Swift stateful DELETE recovery, RFC 7230 quoted-pair unescaping, PKCE 197 threshold, and Basic encoding verified.",
        details={"expected_unescaped": expected_unescaped},
    )


# ---------------------------------------------------------------------------
# PR-16: swift-sdk#298 stateless HTTP private IDs on cancel & #297 stdio O_NONBLOCK restore
# ---------------------------------------------------------------------------
def evaluate_mcp_swift_stateless_cancel_and_stdio_flags_guard(
    *,
    stateless_requests_use_private_internal_ids: bool,
    response_restored_original_client_id: bool,
    ambiguous_cancel_terminated_sibling_request: bool,
    cancel_post_status_code: int,
    client_accepts_sse: bool,
    cancelled_original_post_outcome: str,
    stdio_changed_blocking_mode: bool,
    inflight_io_drained_before_restore: bool,
    stdio_blocking_mode_restored_on_disconnect: bool,
) -> GuardEvaluation:
    if (
        not stateless_requests_use_private_internal_ids
        or not response_restored_original_client_id
        or ambiguous_cancel_terminated_sibling_request
    ):
        return GuardEvaluation(
            passed=False,
            code="MCP_SWIFT_STATELESS_HTTP_ID_COLLISION_OR_SIBLING_CANCEL",
            reason="Stateless HTTP requests must use private internal IDs, restore original client IDs on response, and leave sibling requests alone on ambiguous cancel.",
            details={
                "stateless_requests_use_private_internal_ids": stateless_requests_use_private_internal_ids,
                "ambiguous_cancel_terminated_sibling_request": ambiguous_cancel_terminated_sibling_request,
            },
        )
    expected_outcome = "empty_sse" if client_accepts_sse else "jsonrpc_error_-32800"
    if cancel_post_status_code != 202 or cancelled_original_post_outcome != expected_outcome:
        return GuardEvaluation(
            passed=False,
            code="MCP_SWIFT_CANCEL_WIRE_CONTRACT_MISMATCH",
            reason="Cancellation POST must return 202 and end original POST with empty SSE (if SSE accepted) or -32800 JSON-RPC error.",
            details={
                "cancel_post_status_code": cancel_post_status_code,
                "cancelled_original_post_outcome": cancelled_original_post_outcome,
            },
        )
    if stdio_changed_blocking_mode and (
        not inflight_io_drained_before_restore or not stdio_blocking_mode_restored_on_disconnect
    ):
        return GuardEvaluation(
            passed=False,
            code="MCP_SWIFT_STDIO_DESCRIPTOR_FLAGS_NOT_RESTORED",
            reason="StdioTransport must wait for in-flight reads/sends and restore descriptor blocking mode on disconnect.",
            details={
                "inflight_io_drained_before_restore": inflight_io_drained_before_restore,
                "stdio_blocking_mode_restored_on_disconnect": stdio_blocking_mode_restored_on_disconnect,
            },
        )
    return GuardEvaluation(
        passed=True,
        code="MCP_SWIFT_STATELESS_CANCEL_AND_STDIO_FLAGS_OK",
        reason="Swift stateless HTTP private ID cancellation isolation and StdioTransport descriptor flag restoration verified.",
        details={"cancelled_original_post_outcome": cancelled_original_post_outcome},
    )
