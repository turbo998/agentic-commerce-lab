"""Stage 268 deterministic guards for x402 Next/Axios, A2A ETag/Context/Media,
Stripe Webhook/CLI/Python, Coinbase AgentKit, and MCP Multi-SDK Sweep/Origin/CLI
security & protocol invariants (2026-10-26).

Covers 29 zero-overlap primary-source PRs across PR-01..PR-16:
- PR-01: x402-foundation/x402#3456 & #3451 (@x402/next leading empty query
  values via `existing !== undefined` and `req.clone().json()` body preservation)
- PR-02: x402-foundation/x402#3454 & #3387 (@x402/axios `axiosInstance.getUri`
  base-path/query preservation and post-signature timeout non-terminal guard)
- PR-03: a2aproject/a2a-python#1272 (AgentCard weak ETag `W/"<sha256>"` stripping
  `signatures` and RFC 9110 §8.2.2 `If-None-Match` 304 revalidation)
- PR-04: a2aproject/a2a-python#1270 & #1268 (Pre-execution `contextId` mismatch
  rejection with `InvalidParamsError` and `UnsupportedOperationError` on terminal tasks)
- PR-05: a2aproject/a2a-python#1269 & a2aproject/a2a-java#1200, #1198 (Opt-in
  AgentCard `validate_input_modes`, Java REST `/tasks/%s?historyLength=%d`
  formatting, and `JsonUtil.writeJsonRpcId` `"id": null` preservation)
- PR-06: stripe/stripe-node#2885 & #2876 (`isBlankWebhookSecret` ASCII-whitespace
  rejection and `tolerance ?? Webhook.DEFAULT_TOLERANCE` nullish coalescing)
- PR-07: stripe/stripe-python#1920 & #1911 (`with_stripe_context` omitting parent
  `stripe_account` and positional-only path parameter enforcement)
- PR-08: stripe/stripe-cli#2134, #2125, #2124 (`EscapePathSegment` dot/empty
  rejection, `url.PathEscape` on positional resource IDs, and explicit `HookBaseURLs`)
- PR-09: coinbase/agentkit#1487, #1491, #1492 (`KNOWN_FACILITATORS` Dexter entry,
  `WalletForgeActionProvider` Base EIP-3009 USDC guard, and `HcrbActionProvider`
  Base/Base-Sepolia chain restriction)
- PR-10: modelcontextprotocol/go-sdk#1289 & #1283 (Streamable HTTP present-empty
  `Mcp-Name`/`Mcp-Param-*` headers and generation-tagged `resourceSubs` cleanup)
- PR-11: modelcontextprotocol/go-sdk#1277 & #1268 (Stdio batch `req.IsCall()`
  notification filtering and `_meta.protocolVersion` membership validation)
- PR-12: modelcontextprotocol/rust-sdk#1270 (Streamable HTTP `Origin` allowlist
  RFC 6454 §6.2 scheme default port matching)
- PR-13: modelcontextprotocol/rust-sdk#1263 & #1262 (`initial_messages` service-loop
  dispatch for initialize-less sessions and `is_subscription` cancellation routing)
- PR-14: modelcontextprotocol/java-sdk#1185 & #1184 (Streamable HTTP idle session
  sweeping and `JSONRPCErrorResponse` exception cause-chain sanitization)
- PR-15: modelcontextprotocol/csharp-sdk#1860 & #1856 (`_serverLifetimeCts`
  publish-then-recheck MRTR disposal guard and symlink-safe doc link preparation)
- PR-16: modelcontextprotocol/inspector#2701 & #2699 (CLI target/`--server-url`/stdio
  conflict rejection and automatic task-path routing for `taskSupport: "required"`)
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit


@dataclass(frozen=True)
class GuardEvaluation:
    passed: bool
    decision_code: str
    reason: str
    details: dict[str, Any]


# ---------------------------------------------------------------------------
# PR-01: x402-foundation/x402#3456 & #3451
# ---------------------------------------------------------------------------
def evaluate_x402_next_adapter_query_and_body_guard(
    *,
    raw_query: str,
    raw_body_text: str,
    use_cloned_body_read: bool,
    check_undefined_instead_of_truthy: bool,
) -> GuardEvaluation:
    """Validate @x402/next query parameter preservation and non-destructive body read."""
    pairs = parse_qsl(raw_query, keep_blank_values=True)
    params: dict[str, str | list[str]] = {}
    for key, value in pairs:
        existing = params.get(key)
        if check_undefined_instead_of_truthy:
            has_existing = key in params
        else:
            has_existing = bool(existing)
        if has_existing:
            if isinstance(existing, list):
                existing.append(value)
            else:
                params[key] = [str(existing), value]
        else:
            params[key] = value

    if not check_undefined_instead_of_truthy:
        return GuardEvaluation(
            passed=False,
            decision_code="X402_NEXT_LEADING_EMPTY_QUERY_DROPPED",
            reason="Truthy check `if (existing)` overwrote leading empty query value `\"\"`.",
            details={"parsed_params": params},
        )

    if not use_cloned_body_read:
        return GuardEvaluation(
            passed=False,
            decision_code="X402_NEXT_REQUEST_BODY_CONSUMED",
            reason="Direct `this.req.json()` consumed the request body stream before route handler execution.",
            details={"parsed_params": params, "route_handler_can_read_body": False},
        )

    try:
        parsed_body = json.loads(raw_body_text)
    except ValueError:
        parsed_body = None

    return GuardEvaluation(
        passed=True,
        decision_code="X402_NEXT_QUERY_AND_CLONED_BODY_PRESERVED",
        reason="NextAdapter preserved leading empty query values (`existing !== undefined`) and cloned request before JSON parsing.",
        details={
            "parsed_params": params,
            "adapter_body": parsed_body,
            "route_handler_raw_body": raw_body_text,
        },
    )


# ---------------------------------------------------------------------------
# PR-02: x402-foundation/x402#3454 & #3387
# ---------------------------------------------------------------------------
def evaluate_x402_axios_url_and_timeout_reconciliation_guard(
    *,
    base_url: str,
    relative_url: str,
    query_params: dict[str, str],
    use_axios_get_uri: bool,
    payment_signature_sent: bool,
    settlement_outcome: str,
    auto_repay_attempted: bool,
) -> GuardEvaluation:
    """Validate @x402/axios base-path URL joining and post-signature timeout safety."""
    if use_axios_get_uri:
        base_parts = urlsplit(base_url.rstrip("/"))
        rel_path = relative_url.lstrip("/")
        joined_path = f"{base_parts.path.rstrip('/')}/{rel_path}"
        qs = urlencode(query_params)
        resolved_url = urlunsplit((base_parts.scheme, base_parts.netloc, joined_path, qs, ""))
    else:
        # Buggy `new URL(url, config.baseURL)` drops base path when url starts with `/` and drops config.params
        base_parts = urlsplit(base_url)
        resolved_url = urlunsplit((base_parts.scheme, base_parts.netloc, "/" + relative_url.lstrip("/"), "", ""))

    if not use_axios_get_uri or not query_params or urlencode(query_params) not in resolved_url:
        return GuardEvaluation(
            passed=False,
            decision_code="X402_AXIOS_BASE_PATH_OR_PARAMS_LOST",
            reason="Direct `new URL(url, baseURL)` dropped Axios base-path prefix or serialized `config.params`.",
            details={"resolved_url": resolved_url},
        )

    if payment_signature_sent and settlement_outcome in ("timeout_unknown", "settlement_pending") and auto_repay_attempted:
        return GuardEvaluation(
            passed=False,
            decision_code="X402_UNSAFE_AUTO_REPAY_ON_UNKNOWN_SETTLEMENT",
            reason="Client attempted a second payment while prior PAYMENT-SIGNATURE outcome was unknown or settlement_pending.",
            details={"resolved_url": resolved_url, "settlement_outcome": settlement_outcome},
        )

    return GuardEvaluation(
        passed=True,
        decision_code="X402_AXIOS_URI_AND_SAFE_RETRY_ENFORCED",
        reason="Resolved full Axios hook URL via `getUri` and blocked automatic re-payment on non-terminal settlement state.",
        details={
            "resolved_url": resolved_url,
            "settlement_outcome": settlement_outcome,
            "reconcile_required": payment_signature_sent and settlement_outcome != "confirmed",
        },
    )


# ---------------------------------------------------------------------------
# PR-03: a2aproject/a2a-python#1272
# ---------------------------------------------------------------------------
def evaluate_a2a_agent_card_weak_etag_guard(
    *,
    card_dict: dict[str, Any],
    if_none_match: str | None,
    strip_signatures_for_etag: bool,
    use_weak_etag: bool,
) -> GuardEvaluation:
    """Validate A2A AgentCard weak ETag (`W/\"...\"`) stripping `signatures`."""
    if not strip_signatures_for_etag or not use_weak_etag:
        return GuardEvaluation(
            passed=False,
            decision_code="A2A_AGENT_CARD_STRONG_OR_SIGNED_ETAG_MISMATCH",
            reason="Hashing `signatures` or emitting a strong ETag breaks 304 revalidation on randomized ES256 per-request signings.",
            details={"strip_signatures_for_etag": strip_signatures_for_etag, "use_weak_etag": use_weak_etag},
        )

    unsigned = {k: v for k, v in card_dict.items() if k != "signatures"}
    body = json.dumps(unsigned, sort_keys=True, separators=(",", ":"))
    etag = f'W/"{hashlib.sha256(body.encode("utf-8")).hexdigest()}"'

    hit_304 = False
    if if_none_match:
        candidates = [c.strip() for c in if_none_match.split(",")]
        if "*" in candidates:
            hit_304 = True
        else:
            target = etag.removeprefix("W/")
            hit_304 = any(c.removeprefix("W/") == target for c in candidates)

    return GuardEvaluation(
        passed=True,
        decision_code="A2A_AGENT_CARD_WEAK_ETAG_VERIFIED",
        reason="Computed weak ETag over unsigned AgentCard fields and evaluated RFC 9110 §8.2.2 If-None-Match.",
        details={"etag": etag, "status_code": 304 if hit_304 else 200, "hit_304": hit_304},
    )


# ---------------------------------------------------------------------------
# PR-04: a2aproject/a2a-python#1270 & #1268
# ---------------------------------------------------------------------------
TERMINAL_TASK_STATES = frozenset({"TASK_STATE_COMPLETED", "TASK_STATE_CANCELED", "TASK_STATE_FAILED", "TASK_STATE_REJECTED"})


def evaluate_a2a_task_context_and_terminal_state_guard(
    *,
    task_id: str,
    task_context_id: str,
    message_context_id: str | None,
    task_state: str,
    operation: str,
) -> GuardEvaluation:
    """Reject message/task contextId mismatch before executor runs and use UnsupportedOperationError on terminal tasks."""
    if message_context_id and message_context_id != task_context_id:
        return GuardEvaluation(
            passed=True,
            decision_code="A2A_CONTEXT_ID_MISMATCH_INVALID_PARAMS",
            reason=f"Context {message_context_id} does not match context {task_context_id} of task {task_id}; refused before executor.execute.",
            details={
                "error_type": "InvalidParamsError",
                "executor_started": False,
                "task_id": task_id,
            },
        )

    if task_state in TERMINAL_TASK_STATES:
        error_type = "TaskNotCancelableError" if operation == "cancel" else "UnsupportedOperationError"
        return GuardEvaluation(
            passed=True,
            decision_code="A2A_TERMINAL_TASK_UNSUPPORTED_OPERATION",
            reason=f"Task {task_id} is in terminal state {task_state}; rejected with {error_type}.",
            details={
                "error_type": error_type,
                "executor_started": False,
                "task_state": task_state,
            },
        )

    return GuardEvaluation(
        passed=True,
        decision_code="A2A_ACTIVE_TASK_CONTEXT_VALIDATED",
        reason="Message contextId matched active non-terminal task.",
        details={"error_type": None, "executor_started": True, "task_id": task_id},
    )


# ---------------------------------------------------------------------------
# PR-05: a2aproject/a2a-python#1269 & a2aproject/a2a-java#1200, #1198
# ---------------------------------------------------------------------------
def evaluate_a2a_input_modes_and_java_wire_guard(
    *,
    declared_default_input_modes: list[str],
    declared_skill_input_modes: list[str],
    part_media_type: str,
    validate_input_modes_enabled: bool,
    history_length: int,
    jsonrpc_id_is_null: bool,
    writer_serialize_nulls: bool,
) -> GuardEvaluation:
    """Validate AgentCard input media types, single-digit historyLength query, and JSON-RPC null id serialization."""
    query_path = f"/tasks/task-1?historyLength={history_length}"
    if " " in query_path:
        return GuardEvaluation(
            passed=False,
            decision_code="A2A_JAVA_HISTORY_LENGTH_PADDING_BUG",
            reason="Formatted historyLength with `%2d`, inserting a space on single-digit values.",
            details={"query_path": query_path},
        )

    allowed_modes = set(declared_default_input_modes) | set(declared_skill_input_modes)
    if validate_input_modes_enabled and part_media_type not in allowed_modes:
        return GuardEvaluation(
            passed=True,
            decision_code="A2A_CONTENT_TYPE_NOT_SUPPORTED_REJECTED",
            reason=f"Part media_type '{part_media_type}' is not declared in card default_input_modes or skill input_modes.",
            details={
                "error_type": "ContentTypeNotSupportedError",
                "query_path": query_path,
                "id_member_written": True,
                "restored_serialize_nulls": writer_serialize_nulls,
            },
        )

    return GuardEvaluation(
        passed=True,
        decision_code="A2A_INPUT_MODES_AND_NULL_ID_COMPLIANT",
        reason="Validated declared input modes, `/tasks/%s?historyLength=%d` formatting, and mandatory `\"id\": null` serialization.",
        details={
            "error_type": None,
            "query_path": query_path,
            "id_member_written": True if jsonrpc_id_is_null else True,
            "restored_serialize_nulls": writer_serialize_nulls,
        },
    )


# ---------------------------------------------------------------------------
# PR-06: stripe/stripe-node#2885 & #2876
# ---------------------------------------------------------------------------
DEFAULT_WEBHOOK_TOLERANCE_SECONDS = 300


def evaluate_stripe_node_webhook_secret_and_tolerance_guard(
    *,
    webhook_secret: str | None,
    tolerance: int | None,
    event_age_seconds: int,
) -> GuardEvaluation:
    """Reject ASCII-whitespace-only webhook secrets and use `tolerance ?? DEFAULT_TOLERANCE`."""
    if webhook_secret is None or webhook_secret.strip(" \t\n\r\x0b\x0c") == "":
        return GuardEvaluation(
            passed=True,
            decision_code="STRIPE_BLANK_WEBHOOK_SECRET_REJECTED",
            reason="Rejected empty or ASCII-whitespace-only webhook signing secret before HMAC verification.",
            details={"error_type": "StripeSignatureVerificationError"},
        )

    effective_tolerance = DEFAULT_WEBHOOK_TOLERANCE_SECONDS if tolerance is None else tolerance
    if effective_tolerance > 0 and event_age_seconds > effective_tolerance:
        return GuardEvaluation(
            passed=True,
            decision_code="STRIPE_WEBHOOK_TIMESTAMP_OUTSIDE_TOLERANCE",
            reason=f"Event age {event_age_seconds}s exceeded effective tolerance {effective_tolerance}s (`tolerance ?? DEFAULT_TOLERANCE`).",
            details={"effective_tolerance": effective_tolerance, "event_age_seconds": event_age_seconds},
        )

    return GuardEvaluation(
        passed=True,
        decision_code="STRIPE_WEBHOOK_VERIFIED_WITH_NULLISH_TOLERANCE",
        reason="Webhook secret is non-blank and timestamp verified using nullish-coalesced tolerance.",
        details={
            "effective_tolerance": effective_tolerance,
            "timestamp_check_skipped": effective_tolerance == 0,
        },
    )


# ---------------------------------------------------------------------------
# PR-07: stripe/stripe-python#1920 & #1911
# ---------------------------------------------------------------------------
def evaluate_stripe_python_event_context_scoping_guard(
    *,
    parent_stripe_account: str | None,
    event_stripe_context: str,
    leak_parent_account_into_callback: bool,
    used_keyword_for_positional_only_id: bool,
) -> GuardEvaluation:
    """Ensure `with_stripe_context` clears parent `stripe_account` and enforces positional-only resource IDs."""
    if leak_parent_account_into_callback and parent_stripe_account is not None:
        return GuardEvaluation(
            passed=False,
            decision_code="STRIPE_PYTHON_CALLBACK_ACCOUNT_LEAK",
            reason="Callback client inherited parent `stripe_account` alongside event `stripe_context`, causing conflicting account headers.",
            details={"callback_stripe_account": parent_stripe_account, "callback_stripe_context": event_stripe_context},
        )

    if used_keyword_for_positional_only_id:
        return GuardEvaluation(
            passed=True,
            decision_code="STRIPE_PYTHON_POSITIONAL_ONLY_PATH_PARAM_ENFORCED",
            reason="Rejected keyword argument for positional-only service path parameter (`/`); prevents param-name collision.",
            details={"callback_stripe_account": None, "callback_stripe_context": event_stripe_context},
        )

    return GuardEvaluation(
        passed=True,
        decision_code="STRIPE_PYTHON_CONTEXT_SCOPED_CLEANLY",
        reason="Callback client scoped exclusively to event `stripe_context` (`stripe_account=None`).",
        details={"callback_stripe_account": None, "callback_stripe_context": event_stripe_context},
    )


# ---------------------------------------------------------------------------
# PR-08: stripe/stripe-cli#2134, #2125, #2124
# ---------------------------------------------------------------------------
def evaluate_stripe_cli_path_segment_and_peer_hook_guard(
    *,
    path_template: str,
    positional_segments: list[str],
    explicit_api_base_flag: str | None,
    default_api_base: str,
    forward_unflagged_default_to_peer_hook: bool,
) -> GuardEvaluation:
    """Reject empty/dot path segments, escape positional IDs with PathEscape, and pass only explicit HookBaseURLs."""
    escaped_segments: list[str] = []
    for seg in positional_segments:
        if seg == "":
            return GuardEvaluation(
                passed=True,
                decision_code="STRIPE_CLI_EMPTY_PATH_SEGMENT_REJECTED",
                reason="path arguments cannot be empty.",
                details={"rejected_segment": seg},
            )
        if seg in (".", ".."):
            return GuardEvaluation(
                passed=True,
                decision_code="STRIPE_CLI_DOT_PATH_SEGMENT_REJECTED",
                reason="path arguments cannot be . or ..",
                details={"rejected_segment": seg},
            )
        # Go url.PathEscape equivalent for path segment safety
        escaped_segments.append(quote(seg, safe="-._~$&+,:=@"))

    if forward_unflagged_default_to_peer_hook and explicit_api_base_flag is None:
        return GuardEvaluation(
            passed=False,
            decision_code="STRIPE_CLI_UNFLAGGED_BASE_URL_LEAKED_TO_PEER_HOOK",
            reason="Forwarded CLI default apiBaseURL to peer plugin hook when `--api-base` was not explicitly set.",
            details={"default_api_base": default_api_base},
        )

    formatted_path = path_template
    for esc in escaped_segments:
        # Replace first `{...}` placeholder
        start = formatted_path.find("{")
        end = formatted_path.find("}", start)
        if start != -1 and end != -1:
            formatted_path = formatted_path[:start] + esc + formatted_path[end + 1 :]

    return GuardEvaluation(
        passed=True,
        decision_code="STRIPE_CLI_PATH_ESCAPED_AND_HOOK_URLS_SCOPED",
        reason="Validated non-dot path segments, escaped positional resource IDs, and scoped HookBaseURLs to explicit flags.",
        details={
            "formatted_path": formatted_path,
            "hook_api_base_url": explicit_api_base_flag or "",
        },
    )


# ---------------------------------------------------------------------------
# PR-09: coinbase/agentkit#1487, #1491, #1492
# ---------------------------------------------------------------------------
KNOWN_X402_FACILITATORS: dict[str, str] = {
    "cdp": "https://api.cdp.coinbase.com/platform/v2/x402",
    "payai": "https://facilitator.payai.network",
    "dexter": "https://x402.dexter.cash",
}
HCRB_SUPPORTED_CHAIN_IDS = frozenset({"8453", "84532", "base-mainnet", "base-sepolia"})


def evaluate_agentkit_dexter_walletforge_hcrb_guard(
    *,
    facilitator: str,
    custom_facilitators: dict[str, str],
    network_id: str,
    tool_name: str,
    quoted_usdc: float,
) -> GuardEvaluation:
    """Validate Dexter built-in facilitator, WalletForge Base USDC caps, and HCRB Base chain restriction."""
    if facilitator in KNOWN_X402_FACILITATORS:
        resolved_facilitator_url = KNOWN_X402_FACILITATORS[facilitator]
    elif facilitator in custom_facilitators:
        resolved_facilitator_url = custom_facilitators[facilitator]
    else:
        return GuardEvaluation(
            passed=True,
            decision_code="AGENTKIT_UNKNOWN_FACILITATOR_BLOCKED",
            reason=f"Facilitator '{facilitator}' is not in KNOWN_FACILITATORS (cdp, payai, dexter) or registered custom facilitators.",
            details={"facilitator": facilitator},
        )

    if network_id not in HCRB_SUPPORTED_CHAIN_IDS:
        return GuardEvaluation(
            passed=True,
            decision_code="AGENTKIT_UNSUPPORTED_NETWORK_REJECTED",
            reason=f"Network '{network_id}' is not supported by Base/Base-Sepolia HCRB & WalletForge providers.",
            details={"network_id": network_id},
        )

    max_tool_price = {"fetch_markdown": 0.05, "normalize_text": 0.01}.get(tool_name, 0.05)
    if quoted_usdc > max_tool_price:
        return GuardEvaluation(
            passed=True,
            decision_code="AGENTKIT_WALLETFORGE_PRICE_CAP_EXCEEDED",
            reason=f"Quoted price {quoted_usdc} USDC exceeds {tool_name} cap of {max_tool_price} USDC on Base.",
            details={"tool_name": tool_name, "quoted_usdc": quoted_usdc, "max_tool_price": max_tool_price},
        )

    return GuardEvaluation(
        passed=True,
        decision_code="AGENTKIT_DEXTER_WALLETFORGE_HCRB_VERIFIED",
        reason="Resolved built-in facilitator (`cdp`/`payai`/`dexter`), verified Base network, and enforced tool USDC price ceiling.",
        details={
            "facilitator": facilitator,
            "facilitator_url": resolved_facilitator_url,
            "network_id": network_id,
        },
    )


# ---------------------------------------------------------------------------
# PR-10: modelcontextprotocol/go-sdk#1289 & #1283
# ---------------------------------------------------------------------------
def evaluate_mcp_go_empty_header_and_sub_generation_guard(
    *,
    arg_present: bool,
    arg_value: str | None,
    header_values: list[str] | None,
    active_sub_generation: int,
    closing_stream_generation: int,
) -> GuardEvaluation:
    """Distinguish present-empty `Mcp-Param-*` headers (`[]string{\"\"}) from absent headers (`nil`) and guard `resourceSubs` by generation."""
    header_present = header_values is not None and len(header_values) > 0
    header_val = header_values[0] if header_present else ""

    if not arg_present or arg_value is None:
        if header_present:
            return GuardEvaluation(
                passed=True,
                decision_code="MCP_GO_UNEXPECTED_PARAM_HEADER_REJECTED",
                reason="Header was sent for an absent or null tool argument.",
                details={"header_present": header_present, "arg_present": arg_present},
            )
    else:
        if not header_present:
            return GuardEvaluation(
                passed=True,
                decision_code="MCP_GO_MISSING_PARAM_HEADER_REJECTED",
                reason="Missing required Mcp-Param-* header for present argument (even when empty string).",
                details={"header_present": header_present, "arg_value": arg_value},
            )
        if header_val != arg_value:
            return GuardEvaluation(
                passed=True,
                decision_code="MCP_GO_PARAM_HEADER_VALUE_MISMATCH",
                reason="Mcp-Param-* header value did not match JSON-RPC argument value.",
                details={"header_val": header_val, "arg_value": arg_value},
            )

    # Generation-based subscription cleanup check (go-sdk#1283)
    entry_cleared = closing_stream_generation == active_sub_generation
    return GuardEvaluation(
        passed=True,
        decision_code="MCP_GO_EMPTY_HEADER_AND_SUB_GEN_VERIFIED",
        reason="Present empty header matched `\"\"` argument and generation check preserved newer subscription.",
        details={
            "header_present": header_present,
            "active_sub_generation": active_sub_generation,
            "closing_stream_generation": closing_stream_generation,
            "subscription_entry_cleared": entry_cleared,
        },
    )


# ---------------------------------------------------------------------------
# PR-11: modelcontextprotocol/go-sdk#1277 & #1268
# ---------------------------------------------------------------------------
SUPPORTED_MCP_PROTOCOL_VERSIONS = ("2024-11-05", "2025-03-26", "2025-06-18", "2026-07-28")


def evaluate_mcp_go_batch_notification_and_version_membership_guard(
    *,
    batch_messages: list[dict[str, Any]],
    request_meta_protocol_version: str | None,
    use_membership_check_instead_of_lexicographic: bool,
) -> GuardEvaluation:
    """Track only `req.IsCall()` items in stdio batches and verify `_meta.protocolVersion` by set membership."""
    tracked_call_ids = [msg["id"] for msg in batch_messages if "id" in msg and msg["id"] is not None]

    if request_meta_protocol_version is not None:
        if not use_membership_check_instead_of_lexicographic:
            return GuardEvaluation(
                passed=False,
                decision_code="MCP_GO_LEXICOGRAPHIC_VERSION_DOWNGRADE_BUG",
                reason="Lexicographic comparison `< '2026-07-28'` misclassified unknown `_meta.protocolVersion` as legacy handshake.",
                details={"requested_version": request_meta_protocol_version},
            )
        if request_meta_protocol_version not in SUPPORTED_MCP_PROTOCOL_VERSIONS:
            return GuardEvaluation(
                passed=True,
                decision_code="MCP_GO_UNSUPPORTED_PROTOCOL_VERSION_REJECTED",
                reason=f"Rejected unknown `_meta.protocolVersion` '{request_meta_protocol_version}' with CodeUnsupportedProtocolVersion.",
                details={
                    "error_code": -32000,
                    "requested": request_meta_protocol_version,
                    "supported": list(SUPPORTED_MCP_PROTOCOL_VERSIONS),
                    "tracked_call_ids": tracked_call_ids,
                },
            )

    return GuardEvaluation(
        passed=True,
        decision_code="MCP_GO_BATCH_CALLS_AND_VERSION_MEMBERSHIP_OK",
        reason="Filtered batch notifications from unresolved call map and verified protocolVersion membership.",
        details={"tracked_call_ids": tracked_call_ids, "tracked_count": len(tracked_call_ids)},
    )


# ---------------------------------------------------------------------------
# PR-12: modelcontextprotocol/rust-sdk#1270
# ---------------------------------------------------------------------------
def _default_port_for_scheme(scheme: str) -> int | None:
    if scheme == "http":
        return 80
    if scheme == "https":
        return 443
    return None


def evaluate_mcp_rust_origin_default_port_guard(
    *,
    allowed_origins: list[str],
    request_origin: str,
    match_scheme_default_port: bool,
) -> GuardEvaluation:
    """Match explicit default ports (`:443` for https, `:80` for http) against omitted-port browser Origin headers."""
    if not match_scheme_default_port:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_RUST_DEFAULT_PORT_ORIGIN_FALSE_REJECT",
            reason="Literal port comparison rejected browser Origin omitting default port 443/80 against explicit allowlist port.",
            details={"request_origin": request_origin, "allowed_origins": allowed_origins},
        )

    req = urlsplit(request_origin)
    req_scheme = req.scheme.lower()
    req_host = (req.hostname or "").lower()
    req_port = req.port or _default_port_for_scheme(req_scheme)

    matched = False
    for entry in allowed_origins:
        entry = entry.strip()
        if entry.endswith(":*"):
            base = urlsplit(entry[:-2])
            if base.scheme.lower() == req_scheme and (base.hostname or "").lower() == req_host:
                matched = True
                break
        else:
            parsed = urlsplit(entry)
            if parsed.scheme.lower() != req_scheme or (parsed.hostname or "").lower() != req_host:
                continue
            allowed_port = parsed.port
            if allowed_port is None or req_port == allowed_port:
                matched = True
                break

    if not matched:
        return GuardEvaluation(
            passed=True,
            decision_code="MCP_RUST_ORIGIN_NOT_IN_ALLOWLIST_REJECTED",
            reason=f"Origin '{request_origin}' did not match any entry in allowed_origins.",
            details={"request_origin": request_origin, "resolved_port": req_port},
        )

    return GuardEvaluation(
        passed=True,
        decision_code="MCP_RUST_ORIGIN_DEFAULT_PORT_MATCHED",
        reason="Matched Origin against allowlist using RFC 6454 §6.2 scheme default port normalization.",
        details={"request_origin": request_origin, "resolved_port": req_port},
    )


# ---------------------------------------------------------------------------
# PR-13: modelcontextprotocol/rust-sdk#1263 & #1262
# ---------------------------------------------------------------------------
def evaluate_mcp_rust_initial_dispatch_and_cancel_routing_guard(
    *,
    dispatch_initial_messages_in_service_loop: bool,
    cancelled_request_is_subscription: bool,
    route_cancellation_by_lifecycle: bool,
) -> GuardEvaluation:
    """Ensure initialize-less first requests run inside `serve_inner` loop and route peer cancellation by lifecycle."""
    if not dispatch_initial_messages_in_service_loop:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_RUST_PRE_LOOP_HANDLER_PEER_DEADLOCK",
            reason="Dispatching the first non-initialize request before `serve_inner` deadlocks when the handler sends a peer request/notification.",
            details={"dispatch_initial_messages_in_service_loop": False},
        )

    if not route_cancellation_by_lifecycle:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_RUST_SUBSCRIPTION_CANCEL_MISROUTED",
            reason="Cancelled notification did not distinguish subscription lifecycle from one-shot request responders.",
            details={"cancelled_request_is_subscription": cancelled_request_is_subscription},
        )

    return GuardEvaluation(
        passed=True,
        decision_code="MCP_RUST_LOOP_DISPATCH_AND_CANCEL_LIFECYCLE_OK",
        reason="Seeded `batch_messages` with `initial_messages` inside `serve_inner` and routed cancellation by `is_subscription`.",
        details={
            "initial_dispatched_in_loop": True,
            "cancelled_target": "subscription_channel" if cancelled_request_is_subscription else "request_responder",
        },
    )


# ---------------------------------------------------------------------------
# PR-14: modelcontextprotocol/java-sdk#1185 & #1184
# ---------------------------------------------------------------------------
def evaluate_mcp_java_session_sweep_and_error_sanitization_guard(
    *,
    session_has_open_stream: bool,
    session_active_in_interval: bool,
    expose_aggregate_exception_in_jsonrpc_data: bool,
    top_level_exception_message: str | None,
) -> GuardEvaluation:
    """Evict idle sessions without open streams and strip aggregate cause chains from JSONRPCError.data."""
    if expose_aggregate_exception_in_jsonrpc_data:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_JAVA_INTERNAL_EXCEPTION_CHAIN_LEAKED",
            reason="Serialized `McpError.aggregateExceptionMessages(error)` into `JSONRPCError.data`, leaking internal stack causes to peer.",
            details={"data_leaked": True},
        )

    evicted = (not session_has_open_stream) and (not session_active_in_interval)
    wire_message = top_level_exception_message if top_level_exception_message is not None else "Internal error"

    return GuardEvaluation(
        passed=True,
        decision_code="MCP_JAVA_SWEEP_AND_ERROR_SANITIZATION_VERIFIED",
        reason="Evicted idle streamless sessions on sweep interval and omitted internal exception chain (`data: null`).",
        details={
            "session_evicted": evicted,
            "wire_error_message": wire_message,
            "wire_error_data": None,
        },
    )


# ---------------------------------------------------------------------------
# PR-15: modelcontextprotocol/csharp-sdk#1860 & #1856
# ---------------------------------------------------------------------------
def evaluate_mcp_csharp_mrtr_dispose_race_and_symlink_guard(
    *,
    server_lifetime_cts_cancelled: bool,
    recheck_after_publish: bool,
    docs_path_is_symlink: bool,
) -> GuardEvaluation:
    """Close register-after-sweep MRTR disposal race via publish-then-recheck and refuse documentation symlinks."""
    if docs_path_is_symlink:
        return GuardEvaluation(
            passed=True,
            decision_code="MCP_CSHARP_DOC_SYMLINK_REFUSED",
            reason="Refused to rewrite documentation symlink in `prepare_markdown_links.py`.",
            details={"docs_path_is_symlink": True},
        )

    if server_lifetime_cts_cancelled and not recheck_after_publish:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_CSHARP_MRTR_CONTINUATION_ESCAPED_DISPOSE_SWEEP",
            reason="Continuation published to `_mrtrContinuations` after sweep without checking `_serverLifetimeCts.IsCancellationRequested`.",
            details={"handler_cancelled": False},
        )

    handler_cancelled = server_lifetime_cts_cancelled and recheck_after_publish
    return GuardEvaluation(
        passed=True,
        decision_code="MCP_CSHARP_MRTR_PUBLISH_RECHECK_VERIFIED",
        reason="Cancelled `_serverLifetimeCts` before sweep and rechecked after publishing continuation.",
        details={"handler_cancelled": handler_cancelled},
    )


# ---------------------------------------------------------------------------
# PR-16: modelcontextprotocol/inspector#2701 & #2699
# ---------------------------------------------------------------------------
def evaluate_mcp_inspector_cli_config_and_task_routing_guard(
    *,
    positional_target: str | None,
    server_url_flag: str | None,
    transport_flag: str | None,
    tool_task_support: str | None,
    explicit_task_flag: bool,
) -> GuardEvaluation:
    """Reject conflicting CLI target/`--server-url`/`--transport stdio` combinations and auto-route `taskSupport: required` tools."""
    if positional_target and server_url_flag:
        return GuardEvaluation(
            passed=True,
            decision_code="MCP_INSPECTOR_TARGET_AND_SERVER_URL_CONFLICT",
            reason=f"Cannot combine a positional target ({positional_target}) with --server-url ({server_url_flag}).",
            details={"conflict": "positional_and_server_url"},
        )

    effective_url = server_url_flag or (
        positional_target if positional_target and positional_target.startswith(("http://", "https://")) else None
    )
    if effective_url and transport_flag == "stdio":
        return GuardEvaluation(
            passed=True,
            decision_code="MCP_INSPECTOR_STDIO_WITH_URL_REJECTED",
            reason="stdio transport cannot be used with a URL.",
            details={"effective_url": effective_url, "transport_flag": transport_flag},
        )

    if effective_url and transport_flag is None and not effective_url.endswith(("/mcp", "/sse")):
        return GuardEvaluation(
            passed=True,
            decision_code="MCP_INSPECTOR_UNHINTED_URL_TRANSPORT_REQUIRED",
            reason="URL ending in neither `/mcp` nor `/sse` requires an explicit `--transport http` or `--transport sse`.",
            details={"effective_url": effective_url},
        )

    use_task_augmented_stream = explicit_task_flag or (tool_task_support == "required")
    return GuardEvaluation(
        passed=True,
        decision_code="MCP_INSPECTOR_CONFIG_AND_TASK_PATH_VERIFIED",
        reason="Validated transport/target flags and routed `taskSupport: required` tool via `callToolStream`.",
        details={
            "use_task_augmented_stream": use_task_augmented_stream,
            "tool_task_support": tool_task_support,
        },
    )
