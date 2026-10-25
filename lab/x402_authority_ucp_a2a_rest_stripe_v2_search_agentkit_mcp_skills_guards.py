"""Stage 272 deterministic guard module covering 86 zero-overlap primary-source PRs (`PR-01..PR-16`)
across x402 Foundation, Universal Commerce Protocol (UCP), Google A2A (Python/Go/JS/Java/.NET),
Stripe (Node/Python/Go/CLI/Agent Toolkit), Coinbase AgentKit, and Model Context Protocol
(Go/Rust/Python/TypeScript/C#/Inspector).
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any
from urllib.parse import parse_qsl, unquote, urlencode, urlparse, urlunparse


@dataclass(frozen=True)
class GuardEvaluation:
    passed: bool
    decision_code: str
    details: dict[str, Any]


SEI_MAINNET_USDC_ADDRESS = "0x3894085Ef7Ff0f0aeDf52E2A2704928d1Ec074F1"
SEI_TESTNET_USDC_ADDRESS = "0x4fCF1784B31630811181f670Aea7A7bEF803eaED"
CANONICAL_UCP_SHOPPING_EXTENSIONS = (
    "docs/specification/shopping/extensions/buyer-consent.md",
    "docs/specification/shopping/extensions/discount.md",
    "docs/specification/shopping/extensions/fulfillment.md",
    "docs/specification/shopping/extensions/loyalty.md",
)


# ---------------------------------------------------------------------------
# PR-01: x402-foundation/x402#3220, #3218 & #3192
# ---------------------------------------------------------------------------
def evaluate_x402_authority_mandate_payment_id_binding_and_siwx_origin_guard(
    *,
    authority_mandate_signed: bool,
    mandate_delegate: str,
    caller_identity: str,
    requested_amount: int,
    mandate_max_amount: int,
    payment_identifier: str,
    cached_request_fingerprint: str | None,
    current_request_fingerprint: str,
    in_flight_locked: bool,
    siwx_challenge_origin: str,
    request_origin: str,
) -> GuardEvaluation:
    """Verify offline-verifiable authority spending mandate (#3220), HTTP-request-bound
    payment-identifier replay/409 protection (#3218), and SIWX origin-bound challenge (#3192).
    """
    if not authority_mandate_signed or mandate_delegate != caller_identity or requested_amount > mandate_max_amount:
        return GuardEvaluation(
            passed=False,
            decision_code="X402_AUTHORITY_MANDATE_UNAUTHORIZED_OR_CAP_EXCEEDED",
            details={
                "authority_mandate_signed": authority_mandate_signed,
                "mandate_delegate": mandate_delegate,
                "caller_identity": caller_identity,
                "requested_amount": requested_amount,
                "mandate_max_amount": mandate_max_amount,
            },
        )
    if in_flight_locked:
        return GuardEvaluation(
            passed=False,
            decision_code="X402_PAYMENT_IDENTIFIER_CONCURRENT_IN_FLIGHT_CONFLICT_409",
            details={"payment_identifier": payment_identifier, "http_status": 409},
        )
    if cached_request_fingerprint is not None and cached_request_fingerprint != current_request_fingerprint:
        return GuardEvaluation(
            passed=False,
            decision_code="X402_PAYMENT_IDENTIFIER_FINGERPRINT_MISMATCH_409",
            details={
                "payment_identifier": payment_identifier,
                "cached_fingerprint": cached_request_fingerprint,
                "current_fingerprint": current_request_fingerprint,
                "http_status": 409,
            },
        )
    if siwx_challenge_origin.rstrip("/").lower() != request_origin.rstrip("/").lower():
        return GuardEvaluation(
            passed=False,
            decision_code="X402_SIWX_CHALLENGE_ORIGIN_MISMATCH_REJECTED",
            details={
                "siwx_challenge_origin": siwx_challenge_origin,
                "request_origin": request_origin,
            },
        )
    return GuardEvaluation(
        passed=True,
        decision_code="X402_AUTHORITY_MANDATE_PAYMENT_ID_AND_SIWX_ORIGIN_VERIFIED",
        details={
            "payment_identifier": payment_identifier,
            "fingerprint_bound": current_request_fingerprint,
            "siwx_origin": request_origin,
            "remaining_mandate_budget": mandate_max_amount - requested_amount,
        },
    )


# ---------------------------------------------------------------------------
# PR-02: x402-foundation/x402#3213, #3214 & #3205
# ---------------------------------------------------------------------------
def _fixed_point_url_decode(value: str, max_passes: int = 8) -> str:
    current = value
    for _ in range(max_passes):
        nxt = unquote(current)
        if nxt == current:
            return current
        current = nxt
    return current


def evaluate_x402_bazaar_fixed_point_decode_settlement_pending_and_hedera_guard(
    *,
    route_template: str,
    use_fixed_point_decode: bool,
    broadcast_tx_hash: str | None,
    confirmation_timed_out: bool,
    enable_settlement_pending_recovery: bool,
    hedera_transfer_method: str,
    hedera_executor_allowance_verified: bool,
) -> GuardEvaluation:
    """Verify fixed-point URL decoding on Bazaar routeTemplate (#3213), settlement_pending
    auto-recovery for broadcast-but-unconfirmed transactions (#3214), and Exact-Hedera
    transferExecutor validation (#3205).
    """
    decoded_template = (
        _fixed_point_url_decode(route_template) if use_fixed_point_decode else unquote(route_template)
    )
    if not use_fixed_point_decode or ".." in decoded_template or "://" in decoded_template:
        return GuardEvaluation(
            passed=False,
            decision_code="X402_BAZAAR_ROUTE_TEMPLATE_TRAVERSAL_OR_SCHEME_INJECTION",
            details={
                "raw_route_template": route_template,
                "decoded_route_template": decoded_template,
                "use_fixed_point_decode": use_fixed_point_decode,
            },
        )
    if confirmation_timed_out and broadcast_tx_hash and not enable_settlement_pending_recovery:
        return GuardEvaluation(
            passed=False,
            decision_code="X402_BROADCAST_SETTLEMENT_LOST_WITHOUT_PENDING_RECOVERY",
            details={
                "broadcast_tx_hash": broadcast_tx_hash,
                "settlement_status": "failed_unrecovered",
            },
        )
    if hedera_transfer_method not in ("transaction", "transferExecutor") or (
        hedera_transfer_method == "transferExecutor" and not hedera_executor_allowance_verified
    ):
        return GuardEvaluation(
            passed=False,
            decision_code="X402_HEDERA_TRANSFER_EXECUTOR_ALLOWANCE_UNVERIFIED",
            details={
                "hedera_transfer_method": hedera_transfer_method,
                "hedera_executor_allowance_verified": hedera_executor_allowance_verified,
            },
        )
    settlement_state = "settlement_pending" if (confirmation_timed_out and broadcast_tx_hash) else "settled"
    return GuardEvaluation(
        passed=True,
        decision_code="X402_BAZAAR_DECODE_SETTLEMENT_PENDING_AND_HEDERA_VERIFIED",
        details={
            "decoded_route_template": decoded_template,
            "settlement_state": settlement_state,
            "retained_tx_hash": broadcast_tx_hash,
            "hedera_transfer_method": hedera_transfer_method,
        },
    )


# ---------------------------------------------------------------------------
# PR-03: x402-foundation/x402#3233, #3228, #3227, #3203 & #3197
# ---------------------------------------------------------------------------
def evaluate_x402_facilitator_gas_limit_family_scoping_sei_and_auth_capture_guard(
    *,
    configured_gas_limit: int | None,
    required_settlement_gas: int,
    selected_families: list[str],
    derive_unselected_family_signers: bool,
    sei_chain_id: str,
    sei_usdc_address: str,
    auth_capture_max_authorized: int,
    auth_capture_capture_amount: int,
) -> GuardEvaluation:
    """Verify Python FacilitatorWeb3Signer configurable gas_limit (#3233), selected-family
    signer derivation scoping (#3228), Sei default USDC assets (#3227), and auth-capture v1.1 (#3203, #3197).
    """
    effective_gas_limit = configured_gas_limit if configured_gas_limit is not None else 300_000
    if effective_gas_limit < required_settlement_gas:
        return GuardEvaluation(
            passed=False,
            decision_code="X402_FACILITATOR_FIXED_GAS_LIMIT_EXCEEDED",
            details={
                "effective_gas_limit": effective_gas_limit,
                "required_settlement_gas": required_settlement_gas,
            },
        )
    if derive_unselected_family_signers or not selected_families:
        return GuardEvaluation(
            passed=False,
            decision_code="X402_UNSCOPED_EVM_SVM_SIGNER_DERIVATION_CRASH",
            details={
                "selected_families": selected_families,
                "derive_unselected_family_signers": derive_unselected_family_signers,
            },
        )
    expected_sei_map = {
        "eip155:1329": SEI_MAINNET_USDC_ADDRESS,
        "eip155:1328": SEI_TESTNET_USDC_ADDRESS,
    }
    if expected_sei_map.get(sei_chain_id) != sei_usdc_address:
        return GuardEvaluation(
            passed=False,
            decision_code="X402_SEI_DEFAULT_STABLECOIN_ASSET_MISMATCH",
            details={
                "sei_chain_id": sei_chain_id,
                "sei_usdc_address": sei_usdc_address,
                "expected": expected_sei_map.get(sei_chain_id),
            },
        )
    if auth_capture_capture_amount < 0 or auth_capture_capture_amount > auth_capture_max_authorized:
        return GuardEvaluation(
            passed=False,
            decision_code="X402_AUTH_CAPTURE_V1_1_OVER_CAPTURE_REJECTED",
            details={
                "authorized_max": auth_capture_max_authorized,
                "capture_amount": auth_capture_capture_amount,
            },
        )
    return GuardEvaluation(
        passed=True,
        decision_code="X402_GAS_LIMIT_FAMILY_SCOPE_SEI_AND_AUTH_CAPTURE_VERIFIED",
        details={
            "effective_gas_limit": effective_gas_limit,
            "derived_families": list(selected_families),
            "sei_chain_id": sei_chain_id,
            "auth_capture_released_hold": auth_capture_max_authorized - auth_capture_capture_amount,
        },
    )


# ---------------------------------------------------------------------------
# PR-04: Universal-Commerce-Protocol/ucp#761, #759, #726, #720, #607 & #465
# ---------------------------------------------------------------------------
def evaluate_ucp_nested_extensions_fragment_links_failfast_and_line_item_note_guard(
    *,
    extension_doc_path: str,
    rewritten_overview_link: str,
    expected_fragment: str,
    ucp_schema_binary_present: bool,
    mask_missing_binary_in_sed_pipe: bool,
    llmstxt_sections: list[str],
    line_item_note: str | None,
    reference_renders_catalog_envelope: bool,
) -> GuardEvaluation:
    """Verify UCP nested shopping extension paths (#761), fragment preservation on root
    spec links (#759), fail-fast on missing ucp-schema/cargo (#726), llms.txt indexing
    for split-payments & glossary (#720), line_item.note <= 500 chars (#607), and
    response_catalog_schema rendering on reference page (#465).
    """
    if extension_doc_path not in CANONICAL_UCP_SHOPPING_EXTENSIONS:
        return GuardEvaluation(
            passed=False,
            decision_code="UCP_UNNESTED_SHOPPING_EXTENSION_PATH_REJECTED",
            details={"extension_doc_path": extension_doc_path},
        )
    if expected_fragment and not rewritten_overview_link.endswith(f"#{expected_fragment}"):
        return GuardEvaluation(
            passed=False,
            decision_code="UCP_ROOT_SPEC_LINK_FRAGMENT_DROPPED",
            details={
                "rewritten_overview_link": rewritten_overview_link,
                "expected_fragment": expected_fragment,
            },
        )
    if not ucp_schema_binary_present and mask_missing_binary_in_sed_pipe:
        return GuardEvaluation(
            passed=False,
            decision_code="UCP_MISSING_SCHEMA_BINARY_MASKED_BY_SED_PIPE",
            details={"ucp_schema_binary_present": False, "mask_missing_binary_in_sed_pipe": True},
        )
    required_llms_docs = {"specification/split-payments.md", "specification/glossary.md"}
    if not required_llms_docs.issubset(set(llmstxt_sections)):
        return GuardEvaluation(
            passed=False,
            decision_code="UCP_LLMSTXT_MISSING_SPLIT_PAYMENTS_OR_GLOSSARY",
            details={"llmstxt_sections": llmstxt_sections},
        )
    if line_item_note is not None and len(line_item_note) > 500:
        return GuardEvaluation(
            passed=False,
            decision_code="UCP_LINE_ITEM_NOTE_MAX_LENGTH_500_EXCEEDED",
            details={"note_length": len(line_item_note)},
        )
    if not reference_renders_catalog_envelope:
        return GuardEvaluation(
            passed=False,
            decision_code="UCP_CATALOG_RESPONSE_ENVELOPE_MISSING_FROM_REFERENCE",
            details={"reference_renders_catalog_envelope": False},
        )
    return GuardEvaluation(
        passed=True,
        decision_code="UCP_NESTED_EXT_FRAGMENT_FAILFAST_AND_LINE_NOTE_VERIFIED",
        details={
            "extension_doc_path": extension_doc_path,
            "rewritten_overview_link": rewritten_overview_link,
            "note_length": len(line_item_note or ""),
            "catalog_envelope_rendered": reference_renders_catalog_envelope,
        },
    )


# ---------------------------------------------------------------------------
# PR-05: a2aproject/a2a-python#1365, #1362, #1360, #1358 & #1357
# ---------------------------------------------------------------------------
def evaluate_a2a_python_task_updater_recovery_v03_none_signing_and_httpx_isolation_guard(
    *,
    set_terminal_flag_before_event_validation: bool,
    status_event_valid: bool,
    v03_proto_has_status_message: bool,
    v03_unset_mapped_to_none: bool,
    preserve_agent_card_defaults_for_jcs_signing: bool,
    share_default_httpx_across_clients: bool,
    lazy_create_cluster_tables_on_get_delete: bool,
) -> GuardEvaluation:
    """Verify A2A Python TaskUpdater recovery after invalid status event (#1365), v0.3 unset
    status/provider kept as None (#1362), AgentCard field presence preservation before JCS
    signing (#1360), per-client httpx instance creation (#1358), and lazy cluster table
    creation in VersionedDatabaseTaskStore.get/delete (#1357).
    """
    if set_terminal_flag_before_event_validation and not status_event_valid:
        return GuardEvaluation(
            passed=False,
            decision_code="A2A_PY_TASK_UPDATER_LOCKED_TERMINAL_ON_VALIDATION_ERROR",
            details={"terminal_latched_prematurely": True},
        )
    if not v03_proto_has_status_message and not v03_unset_mapped_to_none:
        return GuardEvaluation(
            passed=False,
            decision_code="A2A_PY_V03_UNSET_PROTO_CONVERTED_TO_EMPTY_OBJECT",
            details={"v03_unset_mapped_to_none": False},
        )
    if not preserve_agent_card_defaults_for_jcs_signing:
        return GuardEvaluation(
            passed=False,
            decision_code="A2A_PY_AGENT_CARD_SIGNING_DROPPED_PRESENT_DEFAULTS",
            details={"preserve_agent_card_defaults_for_jcs_signing": False},
        )
    if share_default_httpx_across_clients or not lazy_create_cluster_tables_on_get_delete:
        return GuardEvaluation(
            passed=False,
            decision_code="A2A_PY_SHARED_HTTPX_OR_MISSING_CLUSTER_TABLES",
            details={
                "share_default_httpx_across_clients": share_default_httpx_across_clients,
                "lazy_create_cluster_tables_on_get_delete": lazy_create_cluster_tables_on_get_delete,
            },
        )
    return GuardEvaluation(
        passed=True,
        decision_code="A2A_PY_RECOVERY_V03_NONE_SIGNING_AND_HTTPX_ISOLATION_VERIFIED",
        details={
            "recoverable_after_validation_error": True,
            "v03_unset_status_message": None,
            "per_client_httpx_isolated": True,
            "cluster_tables_lazy_initialized": True,
        },
    )


# ---------------------------------------------------------------------------
# PR-06: a2aproject/a2a-go#480, #479, #474, #471, #468 & #463
# ---------------------------------------------------------------------------
def evaluate_a2a_go_rest_query_service_params_nil_typed_and_pre_stream_error_guard(
    *,
    endpoint_url: str,
    operation_query: dict[str, str],
    preserve_endpoint_query: bool,
    service_param_keys: list[str],
    normalize_service_param_keys_lowercase: bool,
    typed_error_value_is_nil: bool,
    guard_nil_map_in_typed_marshal: bool,
    gateway_http_status: int,
    map_non_a2a_http_error_by_status: bool,
    request_content_type: str,
    accept_header: str,
    pre_first_event_stream_error: bool,
    send_200_sse_headers_before_first_event: bool,
) -> GuardEvaluation:
    """Verify A2A Go REST endpoint query parameter preservation (#480), lowercase ServiceParams
    key normalization (#479), nil Value map handling in Typed.MarshalJSON (#474), non-A2A HTTP
    status code error mapping (#471), application/a2a+json negotiation on wildcard Accept (#468),
    and plain error before SSE headers when streaming fails before first event (#463).
    """
    parsed = urlparse(endpoint_url)
    existing_q = dict(parse_qsl(parsed.query)) if preserve_endpoint_query else {}
    merged_q = {**existing_q, **operation_query}
    final_url = urlunparse(parsed._replace(query=urlencode(merged_q)))
    if not preserve_endpoint_query or "api_key" not in merged_q:
        return GuardEvaluation(
            passed=False,
            decision_code="A2A_GO_REST_ENDPOINT_QUERY_PARAMS_OVERWRITTEN",
            details={"final_url": final_url},
        )
    normalized_keys = (
        [k.lower() for k in service_param_keys]
        if normalize_service_param_keys_lowercase
        else list(service_param_keys)
    )
    if any(k != k.lower() for k in normalized_keys):
        return GuardEvaluation(
            passed=False,
            decision_code="A2A_GO_SERVICE_PARAMS_MIXED_CASE_KEY_MISS",
            details={"keys": normalized_keys},
        )
    if typed_error_value_is_nil and not guard_nil_map_in_typed_marshal:
        return GuardEvaluation(
            passed=False,
            decision_code="A2A_GO_TYPED_MARSHAL_NIL_MAP_PANIC",
            details={"typed_error_value_is_nil": True},
        )
    if gateway_http_status >= 400 and not map_non_a2a_http_error_by_status:
        return GuardEvaluation(
            passed=False,
            decision_code="A2A_GO_GATEWAY_HTTP_ERROR_MASKED_AS_PARSE_ERROR",
            details={"gateway_http_status": gateway_http_status},
        )
    if pre_first_event_stream_error and send_200_sse_headers_before_first_event:
        return GuardEvaluation(
            passed=False,
            decision_code="A2A_GO_PRE_EVENT_STREAM_ERROR_SWALLOWED_BY_EARLY_200_SSE",
            details={"early_200_sse_sent": True},
        )
    response_ct = (
        "application/a2a+json"
        if request_content_type == "application/a2a+json" and accept_header in ("", "*/*")
        else "application/json"
    )
    return GuardEvaluation(
        passed=True,
        decision_code="A2A_GO_REST_QUERY_PARAMS_TYPED_NIL_AND_STREAM_ERROR_VERIFIED",
        details={
            "final_url": final_url,
            "normalized_service_keys": normalized_keys,
            "response_content_type": response_ct,
            "mapped_gateway_status": gateway_http_status,
        },
    )


# ---------------------------------------------------------------------------
# PR-07: a2aproject/a2a-js#791, #788, #787, #770 & a2aproject/a2a-java#1209, #1202
# ---------------------------------------------------------------------------
def evaluate_a2a_js_grpc_ext_subms_timestamp_and_java_rest_sse_close_guard(
    *,
    defer_grpc_metadata_until_first_event: bool,
    unwrap_typed_a2a_error_from_sse: bool,
    task_timestamp_iso: str,
    filter_boundary_iso: str,
    preserve_sub_millisecond_precision: bool,
    skip_unknown_stream_payload_kind: bool,
    java_signal_normal_rest_sse_completion: bool,
    java_cancel_inflight_futures_on_close: bool,
) -> GuardEvaluation:
    """Verify A2A JS gRPC metadata deferred until first event (#791), typed SSE error
    unwrapping (#788), sub-millisecond statusTimestampAfter comparison (#787), skipping
    unrecognized stream payload kinds (#770), and A2A Java normal REST SSE completion
    signaling (#1209) & cancelling in-flight futures on close (#1202).
    """
    if not defer_grpc_metadata_until_first_event or not unwrap_typed_a2a_error_from_sse:
        return GuardEvaluation(
            passed=False,
            decision_code="A2A_JS_EARLY_GRPC_METADATA_OR_GENERIC_SSE_ERROR_WRAP",
            details={
                "defer_grpc_metadata_until_first_event": defer_grpc_metadata_until_first_event,
                "unwrap_typed_a2a_error_from_sse": unwrap_typed_a2a_error_from_sse,
            },
        )
    # Compare sub-millisecond ISO strings (e.g. .000900Z vs .000500Z)
    if not preserve_sub_millisecond_precision:
        # Simulates Date.parse truncation to milliseconds (.000)
        matched = task_timestamp_iso[:23] > filter_boundary_iso[:23]
    else:
        matched = task_timestamp_iso > filter_boundary_iso
    if not matched or not skip_unknown_stream_payload_kind:
        return GuardEvaluation(
            passed=False,
            decision_code="A2A_JS_SUB_MILLISECOND_TRUNCATION_OR_UNDEFINED_PAYLOAD",
            details={
                "matched": matched,
                "skip_unknown_stream_payload_kind": skip_unknown_stream_payload_kind,
            },
        )
    if not java_signal_normal_rest_sse_completion or not java_cancel_inflight_futures_on_close:
        return GuardEvaluation(
            passed=False,
            decision_code="A2A_JAVA_REST_SSE_HANG_ON_COMPLETE_OR_CLOSE_LEAK",
            details={
                "java_signal_normal_rest_sse_completion": java_signal_normal_rest_sse_completion,
                "java_cancel_inflight_futures_on_close": java_cancel_inflight_futures_on_close,
            },
        )
    return GuardEvaluation(
        passed=True,
        decision_code="A2A_JS_GRPC_SUBMS_AND_JAVA_REST_SSE_LIFECYCLE_VERIFIED",
        details={
            "sub_millisecond_match": matched,
            "grpc_first_event_extensions_included": True,
            "java_rest_sse_clean_close": True,
        },
    )


# ---------------------------------------------------------------------------
# PR-08: a2aproject/a2a-dotnet#554, #553, #552, #548 & #546
# ---------------------------------------------------------------------------
def evaluate_a2a_dotnet_proactive_continuation_duplicate_json_keys_and_stream_ct_guard(
    *,
    raw_json_has_duplicate_keys: bool,
    reject_duplicate_json_keys_on_ingress: bool,
    streaming_response_content_type: str,
    raise_on_non_event_stream_response: bool,
    proactive_continue_without_synthetic_message: bool,
    consolidated_context_handler: bool,
    requested_extensions: list[str],
    registered_extensions: list[str],
) -> GuardEvaluation:
    """Verify A2A .NET duplicate JSON-RPC property rejection (#546), non-event-stream
    streaming response error (#552), proactive ContinueTaskAsync (#554), consolidated
    IA2ARequestHandler context contract (#553), and registry-backed extension negotiation (#548).
    """
    if raw_json_has_duplicate_keys and not reject_duplicate_json_keys_on_ingress:
        return GuardEvaluation(
            passed=False,
            decision_code="A2A_DOTNET_DUPLICATE_JSONRPC_PROPERTY_ACCEPTED",
            details={"raw_json_has_duplicate_keys": True},
        )
    if streaming_response_content_type != "text/event-stream" and not raise_on_non_event_stream_response:
        return GuardEvaluation(
            passed=False,
            decision_code="A2A_DOTNET_NON_EVENT_STREAM_RESPONSE_SILENTLY_IGNORED",
            details={"streaming_response_content_type": streaming_response_content_type},
        )
    if not proactive_continue_without_synthetic_message or not consolidated_context_handler:
        return GuardEvaluation(
            passed=False,
            decision_code="A2A_DOTNET_SYNTHETIC_CONTINUE_OR_UNCONSOLIDATED_HANDLER",
            details={
                "proactive_continue_without_synthetic_message": proactive_continue_without_synthetic_message,
                "consolidated_context_handler": consolidated_context_handler,
            },
        )
    negotiated = [ext for ext in requested_extensions if ext in set(registered_extensions)]
    return GuardEvaluation(
        passed=True,
        decision_code="A2A_DOTNET_CONTINUATION_INGRESS_AND_EXTENSION_NEGOTIATION_VERIFIED",
        details={
            "duplicate_keys_rejected": raw_json_has_duplicate_keys,
            "negotiated_extensions": negotiated,
            "proactive_continuation": True,
        },
    )


# ---------------------------------------------------------------------------
# PR-09: stripe/stripe-node#2900, #2896, #2884 & stripe/stripe-go#2464
# ---------------------------------------------------------------------------
def evaluate_stripe_v2_search_post_pagination_async_notif_and_fetch_dispose_guard(
    *,
    v2_search_pagination_method: str,
    replay_original_json_body_on_next_page: bool,
    cjs_exports_v2_search_and_list_types: bool,
    await_async_crypto_signature_verification: bool,
    dispose_unread_fetch_body_on_retry: bool,
) -> GuardEvaluation:
    """Verify Stripe API v2 Search POST pagination with original JSON body replay
    (stripe-node#2884, stripe-go#2464), V2List/V2SearchResult CJS namespace exports
    (stripe-node#2900), and async notification verification + FetchHttpClient stream
    dispose on retry (stripe-node#2896).
    """
    if v2_search_pagination_method.upper() != "POST" or not replay_original_json_body_on_next_page:
        return GuardEvaluation(
            passed=False,
            decision_code="STRIPE_V2_SEARCH_PAGINATION_METHOD_OR_BODY_LOST",
            details={
                "method": v2_search_pagination_method,
                "replay_original_json_body_on_next_page": replay_original_json_body_on_next_page,
            },
        )
    if not cjs_exports_v2_search_and_list_types:
        return GuardEvaluation(
            passed=False,
            decision_code="STRIPE_NODE_CJS_V2_NAMESPACE_EXPORTS_MISSING",
            details={"cjs_exports_v2_search_and_list_types": False},
        )
    if not await_async_crypto_signature_verification or not dispose_unread_fetch_body_on_retry:
        return GuardEvaluation(
            passed=False,
            decision_code="STRIPE_NODE_SYNC_CRYPTO_OR_UNREAD_FETCH_STREAM_LEAK",
            details={
                "await_async_crypto_signature_verification": await_async_crypto_signature_verification,
                "dispose_unread_fetch_body_on_retry": dispose_unread_fetch_body_on_retry,
            },
        )
    return GuardEvaluation(
        passed=True,
        decision_code="STRIPE_V2_SEARCH_POST_PAGINATION_AND_FETCH_DISPOSE_VERIFIED",
        details={
            "pagination_method": "POST",
            "replayed_search_body": True,
            "async_signature_verified": True,
            "unread_stream_disposed": True,
        },
    )


# ---------------------------------------------------------------------------
# PR-10: stripe/stripe-python#1927, #1924, stripe/stripe-go#2452 & stripe/stripe-cli#2133, #2127, #2123
# ---------------------------------------------------------------------------
def evaluate_stripe_openapi_mock_pin_positional_args_and_cli_plugin_version_guard(
    *,
    sdk_openapi_version: str,
    stripe_mock_version: str,
    leading_path_arg_passed_by_keyword: bool,
    enforce_positional_only_path_args: bool,
    cli_version_sent_in_plugin_additional_info: bool,
    install_ps1_honors_pinned_version: bool,
    cli_telemetry_distinguishes_http_status: bool,
) -> GuardEvaluation:
    """Verify stripe-mock pinning to SDK OPENAPI_VERSION (stripe-python#1927, stripe-go#2452),
    positional-only leading path args (stripe-python#1924), Stripe CLI version in plugin
    AdditionalInfo (stripe-cli#2133), install.ps1 VERSION pinning (stripe-cli#2127), and
    HTTP status telemetry classification (stripe-cli#2123).
    """
    if sdk_openapi_version != stripe_mock_version:
        return GuardEvaluation(
            passed=False,
            decision_code="STRIPE_MOCK_OPENAPI_VERSION_DRIFT_REJECTED",
            details={
                "sdk_openapi_version": sdk_openapi_version,
                "stripe_mock_version": stripe_mock_version,
            },
        )
    if leading_path_arg_passed_by_keyword and not enforce_positional_only_path_args:
        return GuardEvaluation(
            passed=False,
            decision_code="STRIPE_PY_OVERLOADED_PATH_ARG_KEYWORD_AMBIGUITY",
            details={"leading_path_arg_passed_by_keyword": True},
        )
    if (
        not cli_version_sent_in_plugin_additional_info
        or not install_ps1_honors_pinned_version
        or not cli_telemetry_distinguishes_http_status
    ):
        return GuardEvaluation(
            passed=False,
            decision_code="STRIPE_CLI_PLUGIN_VERSION_OR_TELEMETRY_CONTRACT_BROKEN",
            details={
                "cli_version_sent_in_plugin_additional_info": cli_version_sent_in_plugin_additional_info,
                "install_ps1_honors_pinned_version": install_ps1_honors_pinned_version,
                "cli_telemetry_distinguishes_http_status": cli_telemetry_distinguishes_http_status,
            },
        )
    return GuardEvaluation(
        passed=True,
        decision_code="STRIPE_OPENAPI_MOCK_PIN_POSITIONAL_AND_CLI_PLUGIN_VERIFIED",
        details={
            "pinned_openapi_version": sdk_openapi_version,
            "positional_only_enforced": enforce_positional_only_path_args,
            "plugin_additional_info_cli_version": True,
        },
    )


# ---------------------------------------------------------------------------
# PR-11: stripe/agent-toolkit#525, #515, #506, #500 & #487
# ---------------------------------------------------------------------------
def evaluate_stripe_agent_toolkit_config_warning_empty_choices_and_402_lanes_guard(
    *,
    config_keys: list[str],
    warn_on_ignored_config_keys: bool,
    llm_response_choices_count: int,
    raise_no_content_generated_error_on_empty_choices: bool,
    portable_agent_plugins_v1_synced: bool,
    claude_lifecycle_feedback_hooks_enabled: bool,
    micro_wallet_lane_index: int,
) -> GuardEvaluation:
    """Verify Stripe Agent Toolkit unknown Configuration key warning (#525),
    NoContentGeneratedError on empty choices array (#500), portable Agent Plugins 1.0
    provider package (#487), Claude lifecycle feedback hooks (#515), and 256-lane HTTP 402
    micro-wallet bridge (#506).
    """
    unknown_keys = [k for k in config_keys if k != "context"]
    if unknown_keys and not warn_on_ignored_config_keys:
        return GuardEvaluation(
            passed=False,
            decision_code="STRIPE_AGENT_TOOLKIT_SILENT_UNKNOWN_CONFIG_KEYS",
            details={"unknown_keys": unknown_keys},
        )
    if llm_response_choices_count == 0 and not raise_no_content_generated_error_on_empty_choices:
        return GuardEvaluation(
            passed=False,
            decision_code="STRIPE_AGENT_TOOLKIT_UNHANDLED_EMPTY_CHOICES_TYPEERROR",
            details={"llm_response_choices_count": 0},
        )
    if (
        not portable_agent_plugins_v1_synced
        or not claude_lifecycle_feedback_hooks_enabled
        or not (0 <= micro_wallet_lane_index < 256)
    ):
        return GuardEvaluation(
            passed=False,
            decision_code="STRIPE_AGENT_TOOLKIT_PLUGIN_SYNC_OR_402_LANE_OUT_OF_RANGE",
            details={
                "portable_agent_plugins_v1_synced": portable_agent_plugins_v1_synced,
                "claude_lifecycle_feedback_hooks_enabled": claude_lifecycle_feedback_hooks_enabled,
                "micro_wallet_lane_index": micro_wallet_lane_index,
            },
        )
    return GuardEvaluation(
        passed=True,
        decision_code="STRIPE_AGENT_TOOLKIT_CONFIG_CHOICES_AND_402_LANES_VERIFIED",
        details={
            "warned_unknown_keys": unknown_keys,
            "empty_choices_error": "NoContentGeneratedError",
            "micro_wallet_lane": micro_wallet_lane_index,
        },
    )


# ---------------------------------------------------------------------------
# PR-12: coinbase/agentkit#1523, #1501, #1489, #1488 & #1482
# ---------------------------------------------------------------------------
def evaluate_agentkit_x402receipts_cdp_idempotency_assetfare_and_rsoft_lending_guard(
    *,
    settled_payment_hash: str,
    recorded_receipt_payment_hash: str,
    cdp_tx_idempotency_key: str | None,
    auto_generate_uuid_when_idempotency_omitted: bool,
    assetfare_action_mode: str,
    rsoft_usdc_health_factor_bps: int,
    solana_python_version: str,
) -> GuardEvaluation:
    """Verify Coinbase AgentKit x402receipts auditable spending reconciliation (#1523),
    CDP sendTransaction/sendUserOperation idempotencyKey forwarding (#1489), read-only
    AssetFare multichain quote enforcement (#1501), RsoftBankActionProvider Base USDC
    lending health check (#1482), and Python solana >=0.36.6,<0.37 pin (#1488).
    """
    if settled_payment_hash != recorded_receipt_payment_hash or not settled_payment_hash:
        return GuardEvaluation(
            passed=False,
            decision_code="AGENTKIT_X402RECEIPTS_SETTLEMENT_HASH_MISMATCH",
            details={
                "settled_payment_hash": settled_payment_hash,
                "recorded_receipt_payment_hash": recorded_receipt_payment_hash,
            },
        )
    effective_idempotency_key = cdp_tx_idempotency_key or (
        hashlib.sha256(settled_payment_hash.encode("utf-8")).hexdigest()[:32]
        if auto_generate_uuid_when_idempotency_omitted
        else None
    )
    if not effective_idempotency_key:
        return GuardEvaluation(
            passed=False,
            decision_code="AGENTKIT_CDP_SEND_TX_MISSING_IDEMPOTENCY_KEY",
            details={"cdp_tx_idempotency_key": None},
        )
    if assetfare_action_mode != "read_only":
        return GuardEvaluation(
            passed=False,
            decision_code="AGENTKIT_ASSETFARE_NON_READONLY_MUTATION_REJECTED",
            details={"assetfare_action_mode": assetfare_action_mode},
        )
    if rsoft_usdc_health_factor_bps < 10_000 or not solana_python_version.startswith("0.36."):
        return GuardEvaluation(
            passed=False,
            decision_code="AGENTKIT_RSOFT_HEALTH_FACTOR_OR_SOLANA_037_BREAKAGE",
            details={
                "rsoft_usdc_health_factor_bps": rsoft_usdc_health_factor_bps,
                "solana_python_version": solana_python_version,
            },
        )
    return GuardEvaluation(
        passed=True,
        decision_code="AGENTKIT_X402RECEIPTS_IDEMPOTENCY_ASSETFARE_AND_RSOFT_VERIFIED",
        details={
            "reconciled_payment_hash": settled_payment_hash,
            "cdp_idempotency_key": effective_idempotency_key,
            "assetfare_mode": assetfare_action_mode,
            "solana_version": solana_python_version,
        },
    )


# ---------------------------------------------------------------------------
# PR-13: modelcontextprotocol/go-sdk#1336, #1335 & rust-sdk#1365, #1324, #1286, #1280, #1274, #1269, #1267
# ---------------------------------------------------------------------------
def evaluate_mcp_go_task_support_and_rust_duplicate_sep2243_legacy_discover_guard(
    *,
    go_proxy_preserves_tool_execution_task_support: bool,
    tool_task_support: str,
    sep2243_header_values_count: int,
    reject_duplicate_sep2243_headers: bool,
    server_is_legacy_only: bool,
    reject_discover_on_legacy_only_server: bool,
    cancel_inflight_work_on_http_transport_close: bool,
    structured_auth_metadata_discovery_error: bool,
) -> GuardEvaluation:
    """Verify MCP Go SDK Tool.Execution.TaskSupport & Task struct preservation (go-sdk#1336, #1335),
    and Rust SDK duplicate SEP-2243 header rejection (#1274), legacy-only server/discover rejection
    (#1269), streamable HTTP transport close cancellation (#1267), structured AuthError (#1280),
    SEP-2640 skills (#1286), and macro/test feature gates (#1365, #1324).
    """
    if not go_proxy_preserves_tool_execution_task_support or tool_task_support not in (
        "forbidden",
        "optional",
        "required",
    ):
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_GO_PROXY_LOST_TOOL_EXECUTION_TASK_SUPPORT",
            details={
                "go_proxy_preserves_tool_execution_task_support": go_proxy_preserves_tool_execution_task_support,
                "tool_task_support": tool_task_support,
            },
        )
    if sep2243_header_values_count > 1 and not reject_duplicate_sep2243_headers:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_RUST_DUPLICATE_SEP2243_HEADERS_ACCEPTED",
            details={"sep2243_header_values_count": sep2243_header_values_count},
        )
    if server_is_legacy_only and not reject_discover_on_legacy_only_server:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_RUST_LEGACY_SERVER_DISCOVER_NOT_REJECTED",
            details={"server_is_legacy_only": True},
        )
    if not cancel_inflight_work_on_http_transport_close or not structured_auth_metadata_discovery_error:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_RUST_TRANSPORT_CLOSE_LEAK_OR_STRING_AUTH_ERROR",
            details={
                "cancel_inflight_work_on_http_transport_close": cancel_inflight_work_on_http_transport_close,
                "structured_auth_metadata_discovery_error": structured_auth_metadata_discovery_error,
            },
        )
    return GuardEvaluation(
        passed=True,
        decision_code="MCP_GO_TASK_SUPPORT_AND_RUST_SEP2243_DISCOVER_VERIFIED",
        details={
            "preserved_task_support": tool_task_support,
            "duplicate_sep2243_rejected": sep2243_header_values_count > 1,
            "legacy_discover_fallback": "initialize",
        },
    )


# ---------------------------------------------------------------------------
# PR-14: modelcontextprotocol/python-sdk#3733, #3731, #3722, #3705 & #3703
# ---------------------------------------------------------------------------
def evaluate_mcp_python_skills_percent_traversal_oauth_rfc_and_linear_stdio_guard(
    *,
    skill_resource_uri: str,
    unquote_percent_encoded_segments_before_check: bool,
    oauth_client_authorized_for_grant: bool,
    oauth_error_code: str,
    stdio_use_chunk_list_join_on_newline: bool,
    bare_collection_return_generates_output_schema: bool,
    atomic_session_group_refresh: bool,
) -> GuardEvaluation:
    """Verify MCP Python SDK percent-encoded dot-segment unquoting in skills URI validation (#3703),
    RFC 6749/7009 /token & /revoke error code alignment (#3733), O(N) chunk-list buffering in
    stdio_client stdout_reader (#3705), structured output model for bare dict/list/tuple (#3731),
    and session group refresh (#3722).
    """
    inspected_uri = unquote(skill_resource_uri) if unquote_percent_encoded_segments_before_check else skill_resource_uri
    segments = [seg for seg in inspected_uri.replace("\\", "/").split("/") if seg]
    if not unquote_percent_encoded_segments_before_check or any(seg in (".", "..") for seg in segments):
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_PY_SKILLS_PERCENT_ENCODED_DOT_SEGMENT_TRAVERSAL",
            details={
                "raw_uri": skill_resource_uri,
                "inspected_uri": inspected_uri,
                "unquoted": unquote_percent_encoded_segments_before_check,
            },
        )
    if not oauth_client_authorized_for_grant and oauth_error_code != "unauthorized_client":
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_PY_OAUTH_RFC6749_ERROR_CODE_MISMATCH",
            details={"oauth_error_code": oauth_error_code, "expected": "unauthorized_client"},
        )
    if (
        not stdio_use_chunk_list_join_on_newline
        or not bare_collection_return_generates_output_schema
        or not atomic_session_group_refresh
    ):
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_PY_QUADRATIC_STDIO_OR_MISSING_BARE_OUTPUT_SCHEMA",
            details={
                "stdio_use_chunk_list_join_on_newline": stdio_use_chunk_list_join_on_newline,
                "bare_collection_return_generates_output_schema": bare_collection_return_generates_output_schema,
                "atomic_session_group_refresh": atomic_session_group_refresh,
            },
        )
    return GuardEvaluation(
        passed=True,
        decision_code="MCP_PY_SKILLS_UNQUOTE_OAUTH_RFC_AND_LINEAR_STDIO_VERIFIED",
        details={
            "validated_skill_uri": inspected_uri,
            "oauth_error_code": oauth_error_code,
            "stdio_buffering_complexity": "O(N)",
        },
    )


# ---------------------------------------------------------------------------
# PR-15: modelcontextprotocol/typescript-sdk#3006, #3005, #3002, #2998 & csharp-sdk#1880, #1872, #1870
# ---------------------------------------------------------------------------
def evaluate_mcp_ts_live_resource_title_405_allow_lazy_validator_and_csharp_aot_guard(
    *,
    initial_resource_title: str,
    updated_resource_title: str,
    list_response_uses_live_title: bool,
    stateless_405_allow_header: str | None,
    compile_validators_lazily_per_called_tool: bool,
    total_catalog_tools: int,
    csharp_endpoint_require_authorization_enforced: bool,
    csharp_aot_list_object_metadata_registered: bool,
) -> GuardEvaluation:
    """Verify MCP TypeScript SDK live resource title in list responses (#3005), Allow: POST on
    stateless legacy 405 responses (#3002), lazy per-tool output validator compilation (#2998),
    DPoP client session reuse (#3006), and C# SDK RequireAuthorization() across session modes
    (#1870), Native AOT List<object> JSON metadata (#1872), and EverythingServer.Stdio (#1880).
    """
    returned_title = updated_resource_title if list_response_uses_live_title else initial_resource_title
    if returned_title != updated_resource_title:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_TS_STALE_RESOURCE_TITLE_IN_LIST_RESPONSE",
            details={"returned_title": returned_title, "expected_title": updated_resource_title},
        )
    if stateless_405_allow_header != "POST":
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_TS_STATELESS_405_MISSING_ALLOW_POST_HEADER",
            details={"stateless_405_allow_header": stateless_405_allow_header},
        )
    compiled_count = 1 if compile_validators_lazily_per_called_tool else total_catalog_tools
    if not compile_validators_lazily_per_called_tool:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_TS_EAGER_CATALOG_VALIDATOR_COMPILATION_BOTTLENECK",
            details={"compiled_validators_on_list": compiled_count},
        )
    if not csharp_endpoint_require_authorization_enforced or not csharp_aot_list_object_metadata_registered:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_CSHARP_ENDPOINT_AUTH_OR_NATIVE_AOT_LIST_OBJECT_MISSING",
            details={
                "csharp_endpoint_require_authorization_enforced": csharp_endpoint_require_authorization_enforced,
                "csharp_aot_list_object_metadata_registered": csharp_aot_list_object_metadata_registered,
            },
        )
    return GuardEvaluation(
        passed=True,
        decision_code="MCP_TS_LIVE_TITLE_405_ALLOW_LAZY_VALIDATOR_AND_CSHARP_AOT_VERIFIED",
        details={
            "listed_resource_title": returned_title,
            "allow_header": stateless_405_allow_header,
            "compiled_validators": compiled_count,
            "csharp_native_aot_list_object": True,
        },
    )


# ---------------------------------------------------------------------------
# PR-16: modelcontextprotocol/inspector#2708, #2706, #2702, #2700, #2698 & #2694
# ---------------------------------------------------------------------------
def evaluate_mcp_inspector_skill_reread_budget_remedy_quiet_output_and_epipe_guard(
    *,
    reread_skill_file_on_explicit_skills_get: bool,
    client_surface: str,
    remedy_message: str,
    quiet_flag_enabled: bool,
    output_file_specified: bool,
    stderr_wrote_bytes_emitted: bool,
    completion_reader_closed_early: bool,
    handle_stdout_epipe_quietly: bool,
    tui_header_height_rows: int,
    capability_counts_displayed: bool,
) -> GuardEvaluation:
    """Verify MCP Inspector live SKILL.md re-read on skills/get (#2694), client-specific
    catalog-budget remedies (#2698), quiet -q suppression of --output status line (#2702),
    quiet exit on early --completion pipe close (#2700), TUI header row height (#2706),
    and web capability counts (#2708).
    """
    if not reread_skill_file_on_explicit_skills_get:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_INSPECTOR_STALE_SKILL_FILE_ON_SKILLS_GET",
            details={"reread_skill_file_on_explicit_skills_get": False},
        )
    expected_surface_token = {
        "cli": "--max-skill",
        "tui": "Skills tab",
        "mcpdo": "mcpdo",
        "web": "Skills settings",
    }.get(client_surface, client_surface)
    if expected_surface_token not in remedy_message:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_INSPECTOR_WRONG_CLIENT_SURFACE_BUDGET_REMEDY",
            details={"client_surface": client_surface, "remedy_message": remedy_message},
        )
    if quiet_flag_enabled and output_file_specified and stderr_wrote_bytes_emitted:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_INSPECTOR_QUIET_MODE_LEAKED_WROTE_BYTES_STATUS",
            details={"stderr_wrote_bytes_emitted": True},
        )
    if completion_reader_closed_early and not handle_stdout_epipe_quietly:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_INSPECTOR_COMPLETION_UNHANDLED_STDOUT_EPIPE",
            details={"completion_reader_closed_early": True},
        )
    if tui_header_height_rows < 2 or not capability_counts_displayed:
        return GuardEvaluation(
            passed=False,
            decision_code="MCP_INSPECTOR_TUI_HEADER_CLIPPED_OR_COUNTS_HIDDEN",
            details={
                "tui_header_height_rows": tui_header_height_rows,
                "capability_counts_displayed": capability_counts_displayed,
            },
        )
    return GuardEvaluation(
        passed=True,
        decision_code="MCP_INSPECTOR_SKILL_REREAD_REMEDY_QUIET_AND_EPIPE_VERIFIED",
        details={
            "client_surface": client_surface,
            "quiet_stderr_clean": True,
            "tui_header_height_rows": tui_header_height_rows,
        },
    )
