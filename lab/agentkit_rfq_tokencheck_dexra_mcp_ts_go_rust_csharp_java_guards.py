"""Stage 244 (245-Stage Milestone!): Deterministic Guards for Coinbase AgentKit & MCP Official SDKs (TS/Go/Rust/C#/Java).

Covers 26 primary-source PRs across 6 official upstream repositories:
- coinbase/agentkit: #1600, #1594, #1590, #1589, #1587, #1584, #1573, #1572
- modelcontextprotocol/typescript-sdk: #3080, #3068, #3047, #3028, #3021, #3011, #3010
- modelcontextprotocol/go-sdk: #1374, #1371, #1365, #1362, #1360, #1353
- modelcontextprotocol/rust-sdk: #1333, #1326, #1323, #1319
- modelcontextprotocol/csharp-sdk: #1884, #1883, #1882, #1877, #1876
- modelcontextprotocol/java-sdk: #1205, #1194, #1193, #1187
"""

from __future__ import annotations

from typing import Any
from urllib.parse import unquote, urlsplit


BASE_UNISWAP_V4_RFQ_HOOK = "0xd72cd1d46ba05479583fbb561b558f133ba98088"
SUPPORTED_BASE_RFQ_TOKENS = frozenset({"USDC", "WETH", "cbBTC", "cbETH", "wstETH", "AERO", "EURC"})
OBJECT_PROTOTYPE_NAMES = frozenset(
    {
        "constructor",
        "toString",
        "toLocaleString",
        "valueOf",
        "hasOwnProperty",
        "isPrototypeOf",
        "propertyIsEnumerable",
        "__defineGetter__",
        "__defineSetter__",
        "__lookupGetter__",
        "__lookupSetter__",
        "__proto__",
    }
)


def evaluate_agentkit_uniswap_v4_atomic_rfq_guard(
    *,
    chain_id: int,
    hook_address: str,
    token_in: str,
    token_out: str,
    eip712_quote_sig_valid: bool,
    quote_expired: bool,
    quoted_amount_out: int,
    min_amount_out: int,
    simulated_amount_out: int,
    preflight_eth_call_ok: bool,
) -> dict[str, Any]:
    """PR-01 (coinbase/agentkit#1600): Base Uniswap v4 Zero-Slippage Atomic RFQ Hook guard."""
    if chain_id != 8453 or hook_address.strip().lower() != BASE_UNISWAP_V4_RFQ_HOOK:
        return {
            "admitted": False,
            "decision_code": "AGENTKIT_RFQ_UNVERIFIED_CHAIN_OR_HOOK",
        }
    if token_in not in SUPPORTED_BASE_RFQ_TOKENS or token_out not in SUPPORTED_BASE_RFQ_TOKENS or token_in == token_out:
        return {
            "admitted": False,
            "decision_code": "AGENTKIT_RFQ_UNSUPPORTED_POOL_PAIR",
        }
    if not eip712_quote_sig_valid or quote_expired:
        return {
            "admitted": False,
            "decision_code": "AGENTKIT_RFQ_INVALID_OR_EXPIRED_EIP712_QUOTE",
        }
    if quoted_amount_out <= 0 or min_amount_out < quoted_amount_out:
        return {
            "admitted": False,
            "decision_code": "AGENTKIT_RFQ_ZERO_SLIPPAGE_FLOOR_VIOLATED",
        }
    if not preflight_eth_call_ok or simulated_amount_out < quoted_amount_out:
        return {
            "admitted": False,
            "decision_code": "AGENTKIT_RFQ_INSUFFICIENT_OUTPUT_FOR_QUOTED_SWAP",
        }
    return {
        "admitted": True,
        "decision_code": "AGENTKIT_UNISWAP_V4_ATOMIC_RFQ_OK",
        "simulated_amount_out": simulated_amount_out,
    }


def evaluate_agentkit_x402_pre_swap_token_check_guard(
    *,
    demo_only: bool,
    requires_x402_payment: bool,
    x402_scheme: str,
    x402_network: str,
    x402_payee: str,
    pinned_payee: str,
    price_atomic_usdc: int,
    max_price_atomic_usdc: int,
    verdict: str | None,
    block_on: tuple[str, ...],
    fail_closed: bool,
    buy_tax_bps: int,
    sell_tax_bps: int,
    max_tax_bps: int = 500,
) -> dict[str, Any]:
    """PR-02 (coinbase/agentkit#1584, #1589, #1594): Pre-swap token risk & x402 spend safety guard."""
    if requires_x402_payment:
        if demo_only:
            return {
                "admitted": False,
                "decision_code": "AGENTKIT_TOKENCHECK_DEMO_ONLY_PAYMENT_DISABLED",
            }
        if (
            x402_scheme != "exact"
            or x402_network != "eip155:8453"
            or x402_payee.strip().lower() != pinned_payee.strip().lower()
            or price_atomic_usdc <= 0
            or price_atomic_usdc > max_price_atomic_usdc
        ):
            return {
                "admitted": False,
                "decision_code": "AGENTKIT_TOKENCHECK_X402_SPEND_POLICY_REJECTED",
            }
    if verdict is None:
        if fail_closed:
            return {
                "admitted": False,
                "decision_code": "AGENTKIT_TOKENCHECK_FAIL_CLOSED_NO_VERDICT",
            }
        return {
            "admitted": True,
            "decision_code": "AGENTKIT_TOKENCHECK_FAIL_OPEN_PROCEED",
        }
    if verdict in block_on or buy_tax_bps > max_tax_bps or sell_tax_bps > max_tax_bps:
        return {
            "admitted": False,
            "decision_code": "AGENTKIT_TOKENCHECK_HIGH_RISK_OR_HONEYPOT_BLOCKED",
        }
    return {
        "admitted": True,
        "decision_code": "AGENTKIT_TOKENCHECK_PRE_SWAP_SAFE",
    }


def evaluate_agentkit_cdp_basepath_uvloop_guard(
    *,
    base_path: str | None,
    is_chain_rpc_url: bool,
    event_loop_type: str,
    nest_asyncio_patched: bool,
    cdp_sdk_version: tuple[int, int, int],
) -> dict[str, Any]:
    """PR-03 (coinbase/agentkit#1587, #1590): CDP custom basePath & uvloop LangChain adapter guard."""
    if is_chain_rpc_url:
        return {
            "admitted": False,
            "decision_code": "AGENTKIT_CDP_BASEPATH_CONFUSED_WITH_CHAIN_RPC",
        }
    if base_path is not None:
        parsed = urlsplit(base_path.strip())
        if parsed.scheme not in {"https", "http"} or not parsed.netloc:
            return {
                "admitted": False,
                "decision_code": "AGENTKIT_CDP_INVALID_BASEPATH_URL",
            }
        if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1"}:
            return {
                "admitted": False,
                "decision_code": "AGENTKIT_CDP_INSECURE_REMOTE_BASEPATH",
            }
    if cdp_sdk_version < (1, 42, 0):
        return {
            "admitted": False,
            "decision_code": "AGENTKIT_CDP_SDK_UNCONDITIONAL_LOOP_PATCH_VERSION",
        }
    if "uvloop" in event_loop_type.lower() and nest_asyncio_patched:
        return {
            "admitted": False,
            "decision_code": "AGENTKIT_UVLOOP_NEST_ASYNCIO_PATCH_FORBIDDEN",
        }
    return {
        "admitted": True,
        "decision_code": "AGENTKIT_CDP_BASEPATH_AND_UVLOOP_OK",
    }


def evaluate_agentkit_dexra_solana_predge_pretrade_guard(
    *,
    dexra_verdict: str,
    token2022_permanent_delegate_trap: bool,
    sandwich_share_bps: int,
    max_sandwich_share_bps: int,
    predge_settlement_dispute_risk_bps: int,
    max_dispute_risk_bps: int,
    requires_402_payment: bool,
    service_url: str,
    registered_x402_services: set[str],
) -> dict[str, Any]:
    """PR-04 (coinbase/agentkit#1573, #1572): Dexra Solana pre-trade & Predge settlement risk guard."""
    if requires_402_payment:
        parsed = urlsplit(service_url.strip())
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in registered_x402_services:
            return {
                "admitted": False,
                "decision_code": "AGENTKIT_DEXRA_UNREGISTERED_X402_SERVICE",
            }
    if (
        dexra_verdict in {"avoid", "unknown"}
        or token2022_permanent_delegate_trap
        or sandwich_share_bps > max_sandwich_share_bps
    ):
        return {
            "admitted": False,
            "decision_code": "AGENTKIT_DEXRA_SOLANA_TOKEN_TRAP_OR_AVOID",
        }
    if predge_settlement_dispute_risk_bps > max_dispute_risk_bps:
        return {
            "admitted": False,
            "decision_code": "AGENTKIT_PREDGE_SETTLEMENT_DISPUTE_RISK_HIGH",
        }
    return {
        "admitted": True,
        "decision_code": "AGENTKIT_DEXRA_AND_PREDGE_PRETRADE_OK",
    }


def evaluate_mcp_ts_sep2640_skills_extension_guard(
    *,
    protocol_version: str,
    skills_entries: list[dict[str, Any]],
    skip_invalid: bool,
    file_declared_size: int,
    file_actual_size: int,
    file_declared_sha256: str,
    file_actual_sha256: str,
    yaml_frontmatter_valid: bool,
) -> dict[str, Any]:
    """PR-05 (modelcontextprotocol/typescript-sdk#3047, #3080, #3068): SEP-2640 Skills over MCP guard."""
    if protocol_version not in {"2025-11-25", "2026-07-28"}:
        return {
            "admitted": False,
            "decision_code": "MCP_TS_SKILLS_UNSUPPORTED_PROTOCOL_VERSION",
        }
    seen_uris: set[str] = set()
    invalid_entries: list[str] = []
    for idx, entry in enumerate(skills_entries):
        uri = str(entry.get("uri", "")).strip()
        valid_entry = bool(entry.get("valid_schema", True)) and uri.startswith("skill://")
        if not valid_entry or uri in seen_uris:
            invalid_entries.append(uri or f"index:{idx}")
        else:
            seen_uris.add(uri)
    if invalid_entries and not skip_invalid:
        return {
            "admitted": False,
            "decision_code": "MCP_TS_SKILLS_STRICT_LIST_VALIDATION_FAILED",
            "invalid_entries": invalid_entries,
        }
    if (
        file_declared_size != file_actual_size
        or file_declared_sha256.strip().lower() != file_actual_sha256.strip().lower()
        or not yaml_frontmatter_valid
    ):
        return {
            "admitted": False,
            "decision_code": "MCP_TS_SKILLS_FILE_DIGEST_SIZE_OR_FRONTMATTER_MISMATCH",
        }
    return {
        "admitted": True,
        "decision_code": "MCP_TS_SEP2640_SKILLS_EXTENSION_OK",
        "valid_count": len(seen_uris),
        "invalid_entries": invalid_entries,
    }


def evaluate_mcp_ts_null_proto_registry_request_body_guard(
    *,
    registry_uses_null_prototype: bool,
    existing_registered_names: set[str],
    candidate_tool_name: str,
    request_body_stream_implemented: bool,
    request_text_fallback_available: bool,
) -> dict[str, Any]:
    """PR-06 (modelcontextprotocol/typescript-sdk#3021, #3028): Null-prototype registry & Request.body fallback guard."""
    if not registry_uses_null_prototype and candidate_tool_name in OBJECT_PROTOTYPE_NAMES:
        return {
            "admitted": False,
            "decision_code": "MCP_TS_OBJECT_PROTOTYPE_COLLISION_IN_PLAIN_MAP",
        }
    if candidate_tool_name in existing_registered_names:
        return {
            "admitted": False,
            "decision_code": "MCP_TS_DUPLICATE_TOOL_REGISTRATION",
        }
    if not request_body_stream_implemented and not request_text_fallback_available:
        return {
            "admitted": False,
            "decision_code": "MCP_TS_REQUEST_BODY_UNREADABLE_NO_FALLBACK",
        }
    return {
        "admitted": True,
        "decision_code": "MCP_TS_NULL_PROTO_AND_BODY_FALLBACK_OK",
    }


def evaluate_mcp_ts_async_output_validator_uri_fragment_guard(
    *,
    validator_is_async: bool,
    awaited_compilation: bool,
    compilation_succeeded: bool,
    awaited_validation: bool,
    validation_passed: bool,
    uri_template_pattern: str,
    candidate_uri: str,
) -> dict[str, Any]:
    """PR-07 (modelcontextprotocol/typescript-sdk#3011, #3010): Async output validator & URI template fragment guard."""
    if validator_is_async and (not awaited_compilation or not awaited_validation):
        return {
            "admitted": False,
            "decision_code": "MCP_TS_UNWAITED_ASYNC_VALIDATOR_PROMISE_TRUTHY_BUG",
        }
    if not compilation_succeeded or not validation_passed:
        return {
            "admitted": False,
            "decision_code": "MCP_TS_TOOL_OUTPUT_VALIDATION_INVALID_PARAMS",
        }
    uri_without_fragment = candidate_uri.split("#", 1)[0]
    prefix = uri_template_pattern.split("{", 1)[0]
    if not uri_without_fragment.startswith(prefix):
        return {
            "admitted": False,
            "decision_code": "MCP_TS_URI_TEMPLATE_MISMATCH",
        }
    extracted_var = uri_without_fragment[len(prefix) :]
    if "#" in extracted_var or not extracted_var:
        return {
            "admitted": False,
            "decision_code": "MCP_TS_URI_TEMPLATE_FRAGMENT_LEAKED",
        }
    return {
        "admitted": True,
        "decision_code": "MCP_TS_ASYNC_VALIDATOR_AND_URI_FRAGMENT_OK",
        "extracted_var": extracted_var,
    }


def evaluate_mcp_go_multi_roundtrip_cache_colonless_sse_guard(
    *,
    has_input_responses: bool,
    has_request_state: bool,
    is_retried_result: bool,
    is_input_required_interim: bool,
    served_from_cache: bool,
    stored_in_cache: bool,
    raw_sse_line: str,
) -> dict[str, Any]:
    """PR-08 (modelcontextprotocol/go-sdk#1371, #1374): Multi-round-trip ReadResource cache & colon-less SSE guard."""
    is_multi_roundtrip_or_interim = (
        has_input_responses or has_request_state or is_retried_result or is_input_required_interim
    )
    if is_multi_roundtrip_or_interim and (served_from_cache or stored_in_cache):
        return {
            "admitted": False,
            "decision_code": "MCP_GO_MULTI_ROUNDTRIP_RESOURCE_CACHE_POISONING",
        }
    if ":" in raw_sse_line:
        field_name, field_value = raw_sse_line.split(":", 1)
        field_value = field_value.lstrip(" ")
    else:
        field_name, field_value = raw_sse_line, ""
    if not field_name:
        return {
            "admitted": False,
            "decision_code": "MCP_GO_SSE_EMPTY_FIELD_NAME",
        }
    return {
        "admitted": True,
        "decision_code": "MCP_GO_RESOURCE_CACHE_AND_COLONLESS_SSE_OK",
        "sse_field": field_name,
        "sse_value": field_value,
    }


def evaluate_mcp_go_cimd_url_request_state_retry_guard(
    *,
    raw_client_id_url: str,
    input_required_has_request_state: bool,
    input_required_has_elicitation: bool,
    retried_with_request_state: bool,
) -> dict[str, Any]:
    """PR-09 (modelcontextprotocol/go-sdk#1362, #1365): CIMD client_id URL & requestState-only retry guard."""
    if "#" in raw_client_id_url:
        return {
            "admitted": False,
            "decision_code": "MCP_GO_CIMD_URL_CONTAINS_FRAGMENT",
        }
    parsed = urlsplit(raw_client_id_url)
    if parsed.scheme != "https" or not parsed.hostname or not parsed.path:
        return {
            "admitted": False,
            "decision_code": "MCP_GO_CIMD_URL_NOT_NONROOT_HTTPS",
        }
    if parsed.username is not None or parsed.password is not None or "@" in parsed.netloc:
        return {
            "admitted": False,
            "decision_code": "MCP_GO_CIMD_URL_CONTAINS_USERINFO",
        }
    decoded_path = unquote(parsed.path)
    segments = [seg for seg in decoded_path.split("/") if seg != ""]
    if any(seg in {".", ".."} for seg in segments):
        return {
            "admitted": False,
            "decision_code": "MCP_GO_CIMD_URL_CONTAINS_DOT_SEGMENT",
        }
    if input_required_has_request_state and not input_required_has_elicitation and not retried_with_request_state:
        return {
            "admitted": False,
            "decision_code": "MCP_GO_REQUEST_STATE_ONLY_RETRY_SKIPPED",
        }
    return {
        "admitted": True,
        "decision_code": "MCP_GO_CIMD_URL_AND_REQUEST_STATE_RETRY_OK",
    }


def evaluate_mcp_go_listen_subscription_stateless_recovery_guard(
    *,
    active_listener_id: str,
    retiring_listener_id: str,
    retired_active_subscription: bool,
    stateless_client_prev_req_failed: bool,
    stateless_client_next_req_blocked: bool,
) -> dict[str, Any]:
    """PR-10 (modelcontextprotocol/go-sdk#1360, #1353): Listen subscription ownership & stateless client recovery guard."""
    if active_listener_id != retiring_listener_id and retired_active_subscription:
        return {
            "admitted": False,
            "decision_code": "MCP_GO_FOREIGN_LISTENER_SUBSCRIPTION_RETIRED",
        }
    if stateless_client_prev_req_failed and stateless_client_next_req_blocked:
        return {
            "admitted": False,
            "decision_code": "MCP_GO_STATELESS_CLIENT_WEDGED_AFTER_FAILED_REQUEST",
        }
    return {
        "admitted": True,
        "decision_code": "MCP_GO_LISTEN_OWNERSHIP_AND_STATELESS_RECOVERY_OK",
    }


def evaluate_mcp_rust_eof_token_cancel_20260728_s2c_guard(
    *,
    transport_eof_reached: bool,
    response_drain_completed: bool,
    service_loop_token_cancelled: bool,
    pending_handlers_cancelled: int,
    pending_handlers_total: int,
    protocol_version: str,
    is_stateless_http: bool,
    server_to_client_request_attempted: bool,
) -> dict[str, Any]:
    """PR-11 (modelcontextprotocol/rust-sdk#1333, #1326): EOF pending token cancel & 2026-07-28 S2C rejection guard."""
    if transport_eof_reached and response_drain_completed:
        if not service_loop_token_cancelled or pending_handlers_cancelled < pending_handlers_total:
            return {
                "admitted": False,
                "decision_code": "MCP_RUST_PENDING_HANDLERS_LEAKED_AFTER_EOF",
            }
    if protocol_version == "2026-07-28" and is_stateless_http and server_to_client_request_attempted:
        return {
            "admitted": False,
            "decision_code": "MCP_RUST_20260728_SERVER_TO_CLIENT_REQUEST_REJECTED",
        }
    return {
        "admitted": True,
        "decision_code": "MCP_RUST_EOF_CANCEL_AND_20260728_S2C_OK",
    }


def evaluate_mcp_rust_session_lock_release_origin_guard(
    *,
    session_handle_cloned_before_await: bool,
    rwlock_held_across_worker_await: bool,
    concurrent_ping_latency_ms: float,
    max_ping_latency_ms: float,
    origin_header: str,
    allowed_origins: set[str],
) -> dict[str, Any]:
    """PR-12 (modelcontextprotocol/rust-sdk#1323, #1319): Session map RwLock release before await & Origin guard."""
    if not session_handle_cloned_before_await or rwlock_held_across_worker_await:
        return {
            "admitted": False,
            "decision_code": "MCP_RUST_SESSION_MAP_RWLOCK_HELD_ACROSS_AWAIT",
        }
    if concurrent_ping_latency_ms > max_ping_latency_ms:
        return {
            "admitted": False,
            "decision_code": "MCP_RUST_FAIR_RWLOCK_STARVATION_LATENCY_EXCEEDED",
        }
    parsed_origin = urlsplit(origin_header.strip())
    if (
        parsed_origin.scheme not in {"http", "https"}
        or not parsed_origin.netloc
        or parsed_origin.path not in {"", "/"}
        or origin_header.strip() not in allowed_origins
    ):
        return {
            "admitted": False,
            "decision_code": "MCP_RUST_INVALID_OR_UNTRUSTED_ORIGIN_LITERAL",
        }
    return {
        "admitted": True,
        "decision_code": "MCP_RUST_SESSION_LOCK_AND_ORIGIN_OK",
    }


def evaluate_mcp_csharp_entra_refresh_fallback_init_params_guard(
    *,
    initialize_params_valid: bool,
    initialize_error_http_status: int,
    initialize_error_jsonrpc_code: int,
    first_refresh_sent_resource: bool,
    first_refresh_http_status: int,
    first_refresh_oauth_error: str,
    retried_without_resource: bool,
) -> dict[str, Any]:
    """PR-13 (modelcontextprotocol/csharp-sdk#1883, #1884): Entra AADSTS9010010 refresh fallback & 400 InvalidParams guard."""
    if not initialize_params_valid:
        if initialize_error_http_status != 400 or initialize_error_jsonrpc_code != -32602:
            return {
                "admitted": False,
                "decision_code": "MCP_CSHARP_INVALID_INIT_PARAMS_RETURNED_500",
            }
    if not first_refresh_sent_resource:
        return {
            "admitted": False,
            "decision_code": "MCP_CSHARP_RFC8707_RESOURCE_OMITTED_ON_FIRST_REFRESH",
        }
    if first_refresh_http_status == 400:
        if first_refresh_oauth_error == "invalid_grant" and retried_without_resource:
            return {
                "admitted": False,
                "decision_code": "MCP_CSHARP_DEAD_REFRESH_TOKEN_INVALID_GRANT_RETRIED",
            }
        if first_refresh_oauth_error != "invalid_grant" and not retried_without_resource:
            return {
                "admitted": False,
                "decision_code": "MCP_CSHARP_ENTRA_RESOURCE_REJECTION_NOT_RETRIED",
            }
    return {
        "admitted": True,
        "decision_code": "MCP_CSHARP_ENTRA_REFRESH_FALLBACK_AND_INIT_OK",
    }


def evaluate_mcp_csharp_session_affinity_content_length_filter_guard(
    *,
    session_found: bool,
    unknown_session_http_status: int,
    unknown_session_jsonrpc_code: int,
    unknown_session_message: str,
    post_uses_content_length: bool,
    post_uses_chunked_encoding: bool,
    call_tool_filter_allowed: bool,
    tool_dispatched_over_wire: bool,
) -> dict[str, Any]:
    """PR-14 (modelcontextprotocol/csharp-sdk#1876, #1877, #1882): Session affinity 404, Content-Length & CallTool filter guard."""
    if not session_found:
        has_guidance = (
            "session affinity" in unknown_session_message.lower()
            and "stateless" in unknown_session_message.lower()
        )
        if unknown_session_http_status != 404 or unknown_session_jsonrpc_code != -32001 or not has_guidance:
            return {
                "admitted": False,
                "decision_code": "MCP_CSHARP_OPAQUE_SESSION_NOT_FOUND_ERROR",
            }
    if not post_uses_content_length or post_uses_chunked_encoding:
        return {
            "admitted": False,
            "decision_code": "MCP_CSHARP_CHUNKED_POST_WITHOUT_CONTENT_LENGTH",
        }
    if not call_tool_filter_allowed and tool_dispatched_over_wire:
        return {
            "admitted": False,
            "decision_code": "MCP_CSHARP_CALL_TOOL_FILTER_BYPASSED",
        }
    return {
        "admitted": True,
        "decision_code": "MCP_CSHARP_SESSION_AFFINITY_CONTENT_LENGTH_FILTER_OK",
    }


def evaluate_mcp_java_stdio_per_message_sse_commit_guard(
    *,
    prior_message_threw_error: bool,
    stdio_stream_terminated: bool,
    subsequent_ping_answered: bool,
    sse_get_response_committed_before_first_event: bool,
) -> dict[str, Any]:
    """PR-15 (modelcontextprotocol/java-sdk#1205, #1194): Per-message stdio error isolation & SSE GET response commit guard."""
    if prior_message_threw_error and (stdio_stream_terminated or not subsequent_ping_answered):
        return {
            "admitted": False,
            "decision_code": "MCP_JAVA_STDIO_FLATMAP_STREAM_KILLED_BY_SINGLE_MESSAGE_ERROR",
        }
    if not sse_get_response_committed_before_first_event:
        return {
            "admitted": False,
            "decision_code": "MCP_JAVA_SSE_GET_RESPONSE_UNCOMMITTED_ON_OPEN",
        }
    return {
        "admitted": True,
        "decision_code": "MCP_JAVA_STDIO_ISOLATION_AND_SSE_COMMIT_OK",
    }


def evaluate_mcp_java_wildcard_numeric_port_session_sweep_guard(
    *,
    wildcard_pattern: str,
    candidate_host_or_origin: str,
    idle_session_expired: bool,
    session_has_active_stream: bool,
    session_evicted_by_sweeper: bool,
) -> dict[str, Any]:
    """PR-16 (modelcontextprotocol/java-sdk#1193, #1187): Wildcard Host/Origin numeric port & session sweeping guard."""
    if wildcard_pattern.endswith(":*"):
        prefix = wildcard_pattern[:-1]  # includes trailing ':'
        if candidate_host_or_origin == wildcard_pattern[:-2]:
            port_part = "80"
        elif candidate_host_or_origin.startswith(prefix):
            port_part = candidate_host_or_origin[len(prefix) :]
        else:
            return {
                "admitted": False,
                "decision_code": "MCP_JAVA_WILDCARD_PREFIX_MISMATCH",
            }
        if not port_part or not port_part.isascii() or not port_part.isdigit():
            return {
                "admitted": False,
                "decision_code": "MCP_JAVA_WILDCARD_PORT_NON_NUMERIC_SUFFIX_REJECTED",
            }
    if session_has_active_stream and session_evicted_by_sweeper:
        return {
            "admitted": False,
            "decision_code": "MCP_JAVA_ACTIVE_STREAM_SESSION_EVICTED",
        }
    if idle_session_expired and not session_has_active_stream and not session_evicted_by_sweeper:
        return {
            "admitted": False,
            "decision_code": "MCP_JAVA_EXPIRED_IDLE_SESSION_LEAKED",
        }
    return {
        "admitted": True,
        "decision_code": "MCP_JAVA_WILDCARD_NUMERIC_PORT_AND_SWEEP_OK",
    }
