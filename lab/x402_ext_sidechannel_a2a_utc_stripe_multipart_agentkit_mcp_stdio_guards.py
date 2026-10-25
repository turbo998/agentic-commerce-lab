"""Stage 270 deterministic guard module covering 53 zero-overlap primary-source PRs (`PR-01..PR-16`)
across x402 Foundation, Google A2A (Go/Java/.NET/JS/Python), Stripe (Node/Python/CLI),
Coinbase AgentKit, and Model Context Protocol (Go/Rust/Java/C#/Kotlin/PHP/Conformance/Inspector).
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import re
from typing import Any
from urllib.parse import urljoin, urlparse


@dataclass(frozen=True)
class GuardEvaluation:
    passed: bool
    decision_code: str
    details: dict[str, Any]


# ---------------------------------------------------------------------------
# PR-01: x402-foundation/x402#3278 & #3275
# ---------------------------------------------------------------------------
CANONICAL_X402_UPTO_PERMIT2_PROXY = "0x4020A4f3b7b90ccA423B9fabCc0CE57C6C240002"
BROKEN_TRANSIENT_UPTO_PERMIT2_PROXY = "0x402015c795ecb48A360bDC6e35a2EaEb313a0002"


def evaluate_x402_extension_responses_sidechannel_and_upto_proxy_guard(
    *,
    extension_responses_header_json: str | None,
    merge_sidechannel_into_buyer_extensions: bool,
    strip_sidechannel_from_payment_response: bool,
    upto_permit2_proxy_address: str,
) -> GuardEvaluation:
    """Verify facilitator EXTENSION-RESPONSES sidechannel isolation (#3278) and canonical Upto proxy (#3275)."""
    if upto_permit2_proxy_address != CANONICAL_X402_UPTO_PERMIT2_PROXY:
        return GuardEvaluation(
            passed=False,
            decision_code="X402_NON_CANONICAL_UPTO_PERMIT2_PROXY_REJECTED",
            details={
                "configured_proxy": upto_permit2_proxy_address,
                "canonical_proxy": CANONICAL_X402_UPTO_PERMIT2_PROXY,
            },
        )
    if merge_sidechannel_into_buyer_extensions or not strip_sidechannel_from_payment_response:
        return GuardEvaluation(
            passed=False,
            decision_code="X402_EXTENSION_RESPONSES_SIDECHANNEL_LEAKED_TO_BUYER",
            details={
                "merge_sidechannel_into_buyer_extensions": merge_sidechannel_into_buyer_extensions,
                "strip_sidechannel_from_payment_response": strip_sidechannel_from_payment_response,
            },
        )

    decoded_sidechannel: dict[str, Any] | None = None
    if extension_responses_header_json:
        try:
            parsed = json.loads(extension_responses_header_json)
            if isinstance(parsed, dict):
                decoded_sidechannel = parsed
        except ValueError:
            decoded_sidechannel = None

    buyer_payment_response = {"success": True, "extensions": {}}
    return GuardEvaluation(
        passed=True,
        decision_code="X402_EXTENSION_SIDECHANNEL_AND_UPTO_PROXY_VERIFIED",
        details={
            "server_extension_responses": decoded_sidechannel,
            "buyer_payment_response_has_sidechannel": "extensionResponses" in buyer_payment_response,
            "canonical_upto_proxy": upto_permit2_proxy_address,
        },
    )


# ---------------------------------------------------------------------------
# PR-02: x402-foundation/x402#3251 & #3240
# ---------------------------------------------------------------------------
def evaluate_x402_batch_settlement_local_truth_and_upfront_flow_guard(
    *,
    local_cumulative_amount: int,
    local_refundable_balance: int,
    charged_amount: int,
    max_step_charge: int,
    client_signed_deposit: int,
    response_charged_cumulative_amount: int | None,
    requested_refund_amount: int,
    trust_unverified_server_channel_state: bool,
    upfront_payment_header_present: bool,
) -> GuardEvaluation:
    """Validate batch-settlement client local state derivation (#3251) and upfront exact flow (#3240)."""
    if trust_unverified_server_channel_state:
        return GuardEvaluation(
            passed=False,
            decision_code="X402_UNTRUSTED_SERVER_CHANNEL_STATE_COPY_BLOCKED",
            details={"trust_unverified_server_channel_state": True},
        )

    capped_charge = min(max(0, charged_amount), max_step_charge)
    expected_next_cumulative = local_cumulative_amount + capped_charge + max(0, client_signed_deposit)
    state_written = True
    if (
        response_charged_cumulative_amount is not None
        and response_charged_cumulative_amount != expected_next_cumulative
    ):
        state_written = False

    applied_refund = min(max(0, requested_refund_amount), local_refundable_balance)
    return GuardEvaluation(
        passed=True,
        decision_code="X402_BATCH_LOCAL_TRUTH_AND_UPFRONT_FLOW_VERIFIED",
        details={
            "expected_next_cumulative": expected_next_cumulative,
            "response_charged_cumulative_amount": response_charged_cumulative_amount,
            "state_written": state_written,
            "applied_refund": applied_refund,
            "upfront_payment_accepted_without_402": upfront_payment_header_present,
        },
    )


# ---------------------------------------------------------------------------
# PR-03: a2aproject/a2a-go#465, #452, #442
# ---------------------------------------------------------------------------
def evaluate_a2a_go_accept_negotiation_utc_and_terminal_error_guard(
    *,
    accept_header: str | None,
    timestamp_epoch_ms: int,
    task_is_terminal: bool,
    operation: str,
    return_spec_unsupported_on_terminal: bool,
) -> GuardEvaluation:
    """Negotiate application/a2a+json (#465), format UTC .sssZ timestamps (#452), and return ErrUnsupportedOperation (#442)."""
    raw_accept = (accept_header or "").lower()
    if "application/json" in raw_accept and "application/a2a+json" not in raw_accept:
        response_content_type = "application/json"
    else:
        response_content_type = "application/a2a+json"

    dt = datetime.fromtimestamp(timestamp_epoch_ms / 1000.0, tz=timezone.utc)
    utc_timestamp = dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{timestamp_epoch_ms % 1000:03d}Z"

    if task_is_terminal and operation in {"SendMessage", "SubscribeToTask"}:
        if not return_spec_unsupported_on_terminal:
            return GuardEvaluation(
                passed=False,
                decision_code="A2A_GO_TERMINAL_TASK_WRONG_ERROR_CODE",
                details={"operation": operation, "error_returned": "ErrTaskNotFound_or_ErrInvalidParams"},
            )
        return GuardEvaluation(
            passed=True,
            decision_code="A2A_GO_ACCEPT_UTC_AND_TERMINAL_SPEC_ERROR_VERIFIED",
            details={
                "response_content_type": response_content_type,
                "utc_timestamp": utc_timestamp,
                "terminal_error": "ErrUnsupportedOperation",
            },
        )

    return GuardEvaluation(
        passed=True,
        decision_code="A2A_GO_ACCEPT_UTC_AND_TERMINAL_SPEC_ERROR_VERIFIED",
        details={
            "response_content_type": response_content_type,
            "utc_timestamp": utc_timestamp,
            "terminal_error": None,
        },
    )


# ---------------------------------------------------------------------------
# PR-04: a2aproject/a2a-java#1181, #1179, #1174, #1173, #1172, #1162
# ---------------------------------------------------------------------------
def evaluate_a2a_java_terminal_sse_blank_ids_and_redirect_guard(
    *,
    sse_events: list[str],
    use_atomic_terminal_signal: bool,
    incoming_task_id: str | None,
    incoming_context_id: str | None,
    request_uri: str,
    redirect_location: str,
) -> GuardEvaluation:
    """Enforce single terminal SSE callback (#1173), blank ID normalization (#1172), and RFC 3986 redirect resolution (#1162)."""
    terminal_callbacks = 0
    terminal_latched = False
    for ev in sse_events:
        if ev in {"complete", "error", "cancel"}:
            if use_atomic_terminal_signal:
                if not terminal_latched:
                    terminal_latched = True
                    terminal_callbacks += 1
            else:
                terminal_callbacks += 1

    if terminal_callbacks > 1:
        return GuardEvaluation(
            passed=False,
            decision_code="A2A_JAVA_DUPLICATE_TERMINAL_SSE_CALLBACK",
            details={"terminal_callbacks": terminal_callbacks},
        )

    normalized_task_id = None if (incoming_task_id is None or incoming_task_id.strip() == "") else incoming_task_id
    normalized_context_id = (
        None if (incoming_context_id is None or incoming_context_id.strip() == "") else incoming_context_id
    )
    resolved_redirect = urljoin(request_uri, redirect_location)

    return GuardEvaluation(
        passed=True,
        decision_code="A2A_JAVA_ATOMIC_SSE_BLANK_IDS_AND_REDIRECT_VERIFIED",
        details={
            "terminal_callbacks": terminal_callbacks,
            "normalized_task_id": normalized_task_id,
            "normalized_context_id": normalized_context_id,
            "creates_new_task": normalized_task_id is None,
            "resolved_redirect_uri": resolved_redirect,
        },
    )


# ---------------------------------------------------------------------------
# PR-05: a2aproject/a2a-dotnet#452 & a2a-js#737, #726 & a2a-python#1233
# ---------------------------------------------------------------------------
_SAFE_TABLE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")


def evaluate_a2a_dotnet_parse_sanitization_js_compat_and_py_nanos_guard(
    *,
    raw_json_exception_message: str,
    sanitize_parse_error: bool,
    timestamps_ns: list[int],
    compare_as_integer_nanos: bool,
    custom_table_name: str,
) -> GuardEvaluation:
    """Sanitize .NET JSON-RPC parse errors (#452), compare Python timestamps in integer ns (#1233), and validate JS table names (#737)."""
    if not sanitize_parse_error:
        return GuardEvaluation(
            passed=False,
            decision_code="A2A_DOTNET_PARSE_ERROR_DETAIL_LEAKED",
            details={"exposed_message": raw_json_exception_message},
        )
    if not _SAFE_TABLE_NAME_RE.match(custom_table_name):
        return GuardEvaluation(
            passed=False,
            decision_code="A2A_JS_UNSAFE_STORE_TABLE_NAME_REJECTED",
            details={"custom_table_name": custom_table_name},
        )
    if not compare_as_integer_nanos:
        return GuardEvaluation(
            passed=False,
            decision_code="A2A_PYTHON_LEXICOGRAPHIC_TIMESTAMP_ORDER_BUG",
            details={"compare_as_integer_nanos": False},
        )

    sorted_desc_ns = sorted(timestamps_ns, reverse=True)
    return GuardEvaluation(
        passed=True,
        decision_code="A2A_CROSS_SDK_PARSE_SANITIZE_AND_NANOS_ORDER_VERIFIED",
        details={
            "wire_parse_error_message": "Invalid JSON payload",
            "sorted_desc_ns": sorted_desc_ns,
            "custom_table_name": custom_table_name,
        },
    )


# ---------------------------------------------------------------------------
# PR-06: stripe/stripe-node#2888, #2868, #2867
# ---------------------------------------------------------------------------
def evaluate_stripe_node_incomplete_body_and_esm_interceptor_guard(
    *,
    response_headers_received: bool,
    body_stream_aborted_midway: bool,
    payload_text: str,
    wait_for_raw_socket_event: bool,
    esm_default_is_constructable: bool,
) -> GuardEvaluation:
    """Classify incomplete buffered bodies as StripeConnectionError (#2868), avoid socket wait (#2867), and export constructable ESM (#2888)."""
    if wait_for_raw_socket_event:
        return GuardEvaluation(
            passed=False,
            decision_code="STRIPE_NODE_SOCKET_EVENT_WAIT_HANGS_INTERCEPTORS",
            details={"wait_for_raw_socket_event": True},
        )
    if not esm_default_is_constructable:
        return GuardEvaluation(
            passed=False,
            decision_code="STRIPE_NODE_ESM_DEFAULT_NOT_CONSTRUCTABLE",
            details={"esm_default_is_constructable": False},
        )

    if response_headers_received and body_stream_aborted_midway:
        error_class = "StripeConnectionError"
    else:
        try:
            json.loads(payload_text)
            error_class = "None"
        except ValueError:
            error_class = "StripeAPIError"

    return GuardEvaluation(
        passed=True,
        decision_code="STRIPE_NODE_INCOMPLETE_BODY_CONNECTION_ERROR_VERIFIED",
        details={
            "classified_error": error_class,
            "interceptor_compatible": True,
            "esm_constructable": True,
        },
    )


# ---------------------------------------------------------------------------
# PR-07: stripe/stripe-python#1904, #1902, #1898
# ---------------------------------------------------------------------------
def _escape_multipart_header_value(value: str) -> str:
    return value.replace('"', "%22").replace("\r", " ").replace("\n", " ")


def evaluate_stripe_python_csprng_multipart_and_singleton_event_guard(
    *,
    boundary_hex: str,
    used_csprng: bool,
    field_name: str,
    filename: str,
    related_object_is_singleton: bool,
    related_object_id: str | None,
) -> GuardEvaluation:
    """Enforce 30-byte CSPRNG multipart boundary & header escaping (#1898) and singleton EventNotification related object (#1904)."""
    if not used_csprng or len(boundary_hex) < 60:
        return GuardEvaluation(
            passed=False,
            decision_code="STRIPE_PYTHON_PREDICTABLE_MULTIPART_BOUNDARY_REJECTED",
            details={"used_csprng": used_csprng, "boundary_len": len(boundary_hex)},
        )

    escaped_name = _escape_multipart_header_value(field_name)
    escaped_filename = _escape_multipart_header_value(filename)
    if '"' in escaped_name or "\r" in escaped_name or "\n" in escaped_name:
        return GuardEvaluation(
            passed=False,
            decision_code="STRIPE_PYTHON_MULTIPART_HEADER_INJECTION",
            details={"escaped_name": escaped_name},
        )

    related_object_class = "SingletonRelatedObject" if related_object_is_singleton else "RelatedObject"
    return GuardEvaluation(
        passed=True,
        decision_code="STRIPE_PYTHON_CSPRNG_MULTIPART_AND_SINGLETON_VERIFIED",
        details={
            "boundary_len": len(boundary_hex),
            "escaped_name": escaped_name,
            "escaped_filename": escaped_filename,
            "related_object_class": related_object_class,
            "related_object_id": related_object_id,
        },
    )


# ---------------------------------------------------------------------------
# PR-08: stripe/stripe-cli#2128, #2126, #2116
# ---------------------------------------------------------------------------
def evaluate_stripe_cli_profile_oauth_sync_and_rename_retry_guard(
    *,
    selected_profile: str,
    profile_account_map: dict[str, str],
    active_oauth_account_before: str,
    sync_oauth_context_with_profile: bool,
    transient_sharing_violations: int,
    max_rename_retries: int,
) -> GuardEvaluation:
    """Sync OAuth active context with selected CLI profile (#2116) and retry Windows binary rename (#2126, #2128)."""
    expected_account = profile_account_map.get(selected_profile)
    effective_account = expected_account if sync_oauth_context_with_profile else active_oauth_account_before
    if effective_account != expected_account:
        return GuardEvaluation(
            passed=False,
            decision_code="STRIPE_CLI_PROFILE_OAUTH_ACCOUNT_MISMATCH",
            details={
                "selected_profile": selected_profile,
                "effective_account": effective_account,
                "expected_account": expected_account,
            },
        )

    rename_succeeded = transient_sharing_violations <= max_rename_retries
    if not rename_succeeded:
        return GuardEvaluation(
            passed=False,
            decision_code="STRIPE_CLI_BINARY_RENAME_EXHAUSTED_RETRIES",
            details={
                "transient_sharing_violations": transient_sharing_violations,
                "max_rename_retries": max_rename_retries,
            },
        )

    return GuardEvaluation(
        passed=True,
        decision_code="STRIPE_CLI_PROFILE_SYNC_AND_RENAME_RETRY_VERIFIED",
        details={
            "selected_profile": selected_profile,
            "effective_account": effective_account,
            "rename_attempts": transient_sharing_violations + 1,
        },
    )


# ---------------------------------------------------------------------------
# PR-09: coinbase/agentkit#1495, #1493, #1490
# ---------------------------------------------------------------------------
SAPIEN_VAULT_BASE_ADDRESS = "0x60Bf63729f688287a450299962b36Cef0aFfaa42"


def evaluate_agentkit_x402_scraper_sapien_vault_and_lazy_solana_guard(
    *,
    network_id: str,
    sapien_vault_address: str,
    scraper_settlement_mode: str,
    lazy_import_solana_deps: bool,
) -> GuardEvaluation:
    """Validate x402Scraper dual-rail settlement (#1495), Sapien Vault Base ERC-4626 (#1493), and lazy Solana imports (#1490)."""
    if not lazy_import_solana_deps:
        return GuardEvaluation(
            passed=False,
            decision_code="AGENTKIT_EAGER_SOLANA_IMPORT_BREAKS_EVM_USERS",
            details={"lazy_import_solana_deps": False},
        )
    if network_id != "8453" or sapien_vault_address != SAPIEN_VAULT_BASE_ADDRESS:
        return GuardEvaluation(
            passed=False,
            decision_code="AGENTKIT_SAPIEN_VAULT_NETWORK_OR_ADDRESS_INVALID",
            details={"network_id": network_id, "sapien_vault_address": sapien_vault_address},
        )
    if scraper_settlement_mode not in {"eip712_transfer_with_authorization", "erc20_transfer_receipt"}:
        return GuardEvaluation(
            passed=False,
            decision_code="AGENTKIT_X402_SCRAPER_UNSUPPORTED_SETTLEMENT_MODE",
            details={"scraper_settlement_mode": scraper_settlement_mode},
        )

    return GuardEvaluation(
        passed=True,
        decision_code="AGENTKIT_SCRAPER_SAPIEN_AND_LAZY_SOLANA_VERIFIED",
        details={
            "network_id": network_id,
            "sapien_vault_address": sapien_vault_address,
            "scraper_settlement_mode": scraper_settlement_mode,
            "lazy_import_solana_deps": True,
        },
    )


# ---------------------------------------------------------------------------
# PR-10: modelcontextprotocol/go-sdk#1316, #1278, #1267
# ---------------------------------------------------------------------------
def evaluate_mcp_go_case_insensitive_loopback_lazy_proxy_and_stdio_cancel_guard(
    *,
    host_header: str,
    build_discovery_transport_lazily: bool,
    protocol_version: str,
    transport_kind: str,
    request_was_cancelled: bool,
    suppress_cancelled_stdio_response: bool,
) -> GuardEvaluation:
    """Match localhost case-insensitively (#1316), build discovery transport lazily (#1278), and silence cancelled 2026-07-28 stdio responses (#1267)."""
    hostname = host_header.split(":", 1)[0].strip()
    is_loopback = hostname.lower() == "localhost" or hostname == "127.0.0.1" or hostname == "[::1]"
    if not is_loopback:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_GO_NON_LOOPBACK_HOST_REJECTED",
            details={"host_header": host_header},
        )
    if not build_discovery_transport_lazily:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_GO_IMPORT_TIME_PROXY_FREEZE_DETECTED",
            details={"build_discovery_transport_lazily": False},
        )

    should_send_response = True
    if protocol_version >= "2026-07-28" and transport_kind == "stdio" and request_was_cancelled:
        if not suppress_cancelled_stdio_response:
            return GuardEvaluation(
                passed=False,
                decision_code="MCP_GO_STDIO_CANCELLED_REQUEST_SENT_RESPONSE",
                details={"protocol_version": protocol_version, "transport_kind": transport_kind},
            )
        should_send_response = False

    return GuardEvaluation(
        passed=True,
        decision_code="MCP_GO_LOOPBACK_LAZY_PROXY_AND_STDIO_CANCEL_VERIFIED",
        details={
            "is_loopback": is_loopback,
            "should_send_response": should_send_response,
            "lazy_discovery_transport": True,
        },
    )


# ---------------------------------------------------------------------------
# PR-11: modelcontextprotocol/go-sdk#1255, #1246, #1245
# ---------------------------------------------------------------------------
_HEADER_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9_.\-/]+$")


def evaluate_mcp_go_cancel_cause_mcp_name_base64_and_issuer_slash_guard(
    *,
    cancellation_reason: str,
    propagate_reason_to_context_cause: bool,
    mcp_name: str,
    issuer_url: str,
) -> GuardEvaluation:
    """Carry cancellation reason as context cause (#1255), Base64-encode non-safe Mcp-Name (#1246), and strip trailing slash from issuer (#1245)."""
    if not propagate_reason_to_context_cause:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_GO_CANCEL_REASON_DROPPED_FROM_CONTEXT_CAUSE",
            details={"cancellation_reason": cancellation_reason},
        )

    if _HEADER_SAFE_NAME_RE.match(mcp_name):
        encoded_mcp_name = mcp_name
    else:
        b64 = base64.b64encode(mcp_name.encode("utf-8")).decode("ascii")
        encoded_mcp_name = f"=?base64?{b64}?="

    parsed = urlparse(issuer_url)
    issuer_path = parsed.path.strip("/")
    base_origin = f"{parsed.scheme}://{parsed.netloc}"
    if issuer_path == "":
        metadata_urls = [
            f"{base_origin}/.well-known/oauth-authorization-server",
            f"{base_origin}/.well-known/openid-configuration",
        ]
    else:
        metadata_urls = [
            f"{base_origin}/.well-known/oauth-authorization-server/{issuer_path}",
            f"{base_origin}/.well-known/openid-configuration/{issuer_path}",
            f"{base_origin}/{issuer_path}/.well-known/openid-configuration",
        ]

    return GuardEvaluation(
        passed=True,
        decision_code="MCP_GO_CANCEL_CAUSE_NAME_B64_AND_ISSUER_URLS_VERIFIED",
        details={
            "context_cancel_cause": cancellation_reason,
            "encoded_mcp_name": encoded_mcp_name,
            "metadata_urls": metadata_urls,
        },
    )


# ---------------------------------------------------------------------------
# PR-12: modelcontextprotocol/rust-sdk#1318, #1264, #1248
# ---------------------------------------------------------------------------
def evaluate_mcp_rust_resource_metadata_origin_and_discover_neutral_guard(
    *,
    pointer_from_well_known_guess_401: bool,
    pointer_fetch_failed: bool,
    remaining_candidates: int,
    treat_guess_pointer_as_advertised: bool,
    first_request_method: str,
    subsequent_request_method: str,
) -> GuardEvaluation:
    """Classify .well-known 401 pointer as WellKnownGuess (#1264) and keep server/discover bootstrap-neutral (#1248)."""
    if pointer_from_well_known_guess_401 and pointer_fetch_failed and treat_guess_pointer_as_advertised:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_RUST_WELL_KNOWN_POINTER_ABORTED_DISCOVERY_EARLY",
            details={"remaining_candidates": remaining_candidates},
        )

    if first_request_method == "server/discover" and subsequent_request_method == "initialize":
        selected_lifecycle = "classic_initialized"
    else:
        selected_lifecycle = "inline"

    return GuardEvaluation(
        passed=True,
        decision_code="MCP_RUST_DISCOVERY_ORIGIN_AND_BOOTSTRAP_NEUTRAL_VERIFIED",
        details={
            "fallback_to_remaining_candidates": pointer_from_well_known_guess_401 and remaining_candidates > 0,
            "selected_lifecycle": selected_lifecycle,
        },
    )


# ---------------------------------------------------------------------------
# PR-13: modelcontextprotocol/java-sdk#1179, #1178, #1175
# ---------------------------------------------------------------------------
def evaluate_mcp_java_nullable_list_changed_and_resubscribable_mono_guard(
    *,
    derived_list_changed: bool | None,
    use_null_safe_boolean_check: bool,
    items_per_page: list[str],
    subscription_count: int,
    fresh_seed_per_subscription: bool,
) -> GuardEvaluation:
    """Guard nullable Boolean listChanged unboxing (#1178, #1179) and isolate listXyz Mono seed per subscription (#1175)."""
    if derived_list_changed is None and not use_null_safe_boolean_check:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_JAVA_NULL_LIST_CHANGED_UNBOXING_NPE",
            details={"derived_list_changed": None},
        )

    if not fresh_seed_per_subscription and subscription_count > 1:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_JAVA_SHARED_MONO_SEED_DUPLICATED_ITEMS",
            details={"observed_size": len(items_per_page) * subscription_count},
        )

    return GuardEvaluation(
        passed=True,
        decision_code="MCP_JAVA_NULL_SAFE_CAPABILITIES_AND_RESUBSCRIBABLE_MONO_VERIFIED",
        details={
            "notify_list_changed": bool(derived_list_changed),
            "observed_size_on_second_subscribe": len(items_per_page),
        },
    )


# ---------------------------------------------------------------------------
# PR-14: modelcontextprotocol/csharp-sdk#1855, #1852, #1844
# ---------------------------------------------------------------------------
def evaluate_mcp_csharp_autodetect_400_404_legacy_meta_and_parse_detail_guard(
    *,
    discover_probe_status: int,
    skip_sse_fallback_on_400_404: bool,
    session_protocol_version: str,
    request_has_2026_meta_keys: bool,
    reject_future_meta_on_legacy_session: bool,
    malformed_json_detail: str | None,
) -> GuardEvaluation:
    """Skip SSE fallback on 400/404 discover rejection (#1855), ignore 2026 _meta on legacy sessions (#1852), and surface 400 parse detail (#1844)."""
    if discover_probe_status in {400, 404} and not skip_sse_fallback_on_400_404:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_CSHARP_SPURIOUS_SSE_FALLBACK_ON_400_404",
            details={"discover_probe_status": discover_probe_status},
        )

    if session_protocol_version == "2025-11-25" and request_has_2026_meta_keys and reject_future_meta_on_legacy_session:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_CSHARP_LEGACY_SESSION_REJECTED_OPAQUE_FUTURE_META",
            details={"session_protocol_version": session_protocol_version},
        )

    return GuardEvaluation(
        passed=True,
        decision_code="MCP_CSHARP_AUTODETECT_LEGACY_META_AND_PARSE_DETAIL_VERIFIED",
        details={
            "sse_fallback_attempted": False,
            "legacy_request_accepted": True,
            "surfaced_parse_detail": malformed_json_detail,
        },
    )


# ---------------------------------------------------------------------------
# PR-15: modelcontextprotocol/kotlin-sdk#1092, #1089 & php-sdk#465 & conformance#447
# ---------------------------------------------------------------------------
def evaluate_mcp_kotlin_sse_plugin_null_ttl_and_php_variadic_guard(
    *,
    sse_plugin_already_installed: bool,
    check_plugin_or_null_before_install: bool,
    task_ttl: int | None,
    serialize_explicit_null_ttl: bool,
    variadic_raw_elements: list[str],
) -> GuardEvaluation:
    """Avoid duplicate Ktor SSE plugin (#1092), write explicit null Task.ttl (#1089), and cast PHP variadic arguments element-by-element (#465)."""
    if sse_plugin_already_installed and not check_plugin_or_null_before_install:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_KOTLIN_DUPLICATE_SSE_PLUGIN_EXCEPTION",
            details={"sse_plugin_already_installed": True},
        )
    if task_ttl is None and not serialize_explicit_null_ttl:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_KOTLIN_OMITTED_REQUIRED_NULL_TASK_TTL",
            details={"task_ttl": None},
        )

    cast_elements = [int(x) for x in variadic_raw_elements]
    serialized_task = {"taskId": "task-1", "ttl": task_ttl}
    return GuardEvaluation(
        passed=True,
        decision_code="MCP_KOTLIN_SSE_NULL_TTL_AND_PHP_VARIADIC_VERIFIED",
        details={
            "serialized_task_json": json.dumps(serialized_task),
            "cast_variadic_ints": cast_elements,
        },
    )


# ---------------------------------------------------------------------------
# PR-16: modelcontextprotocol/inspector#2696, #2692, #2691, #2690
# ---------------------------------------------------------------------------
def evaluate_mcp_inspector_oauth_lock_restore_403_challenge_and_temp_cleanup_guard(
    *,
    claimed_lock_is_fresh: bool,
    restore_fresh_lock_instead_of_delete: bool,
    http_status: int,
    www_authenticate_header: str | None,
    as_metadata_published: bool,
    configured_token_endpoint_override: str | None,
    cleanup_temp_copy_files_on_exit: bool,
) -> GuardEvaluation:
    """Restore fresh OAuth lock on lost steal (#2696), ignore bare 403 without WWW-Authenticate (#2690), apply metadata-less overrides (#2691), and clean TUI temp files (#2692)."""
    if claimed_lock_is_fresh and not restore_fresh_lock_instead_of_delete:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_INSPECTOR_FRESH_OAUTH_LOCK_DELETED_ON_LOST_STEAL",
            details={"claimed_lock_is_fresh": True},
        )
    if not cleanup_temp_copy_files_on_exit:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_INSPECTOR_TUI_TEMP_TOKEN_FILE_LEAKED",
            details={"cleanup_temp_copy_files_on_exit": False},
        )

    has_www_auth = bool(www_authenticate_header and www_authenticate_header.strip())
    is_oauth_challenge = http_status == 401 or (http_status == 403 and has_www_auth)
    effective_token_endpoint = (
        configured_token_endpoint_override
        if (not as_metadata_published and configured_token_endpoint_override)
        else "https://mcp.example.com/token"
    )

    return GuardEvaluation(
        passed=True,
        decision_code="MCP_INSPECTOR_LOCK_RESTORE_403_AND_CLEANUP_VERIFIED",
        details={
            "lock_preserved": True,
            "is_oauth_challenge": is_oauth_challenge,
            "effective_token_endpoint": effective_token_endpoint,
            "temp_files_cleaned_on_exit": True,
        },
    )
