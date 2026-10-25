"""Stage 242 deterministic guard evaluators for x402 SVM/SIWX/Permit2/Recovery,
UCP Order/Catalog/Purchase-Options/Identity-Linking, MCP Python SDK Stdio/HTTP/OAuth/SSE,
and tau2-bench Retail/Telecom/Evaluator/Sandbox safety (PR-01..PR-16).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class GuardResult:
    passed: bool
    action: str
    reason: str
    guard_id: str


def evaluate_x402_svm_batch_post_commit_completion_guard(payload: Dict[str, Any]) -> GuardResult:
    """PR-01: x402 #3854 SVM batch-settlement operation completion after channel charge commits."""
    guard_id = "PR-01"
    channel_committed = bool(payload.get("channel_charge_committed", False))
    inside_update_cb = bool(payload.get("inside_channel_update_callback", False))
    ops_completed = bool(payload.get("operations_marked_complete", False))

    if ops_completed and (not channel_committed or inside_update_cb):
        return GuardResult(
            passed=False,
            action="Send to a human",
            reason="REJECT: SVM batch operations marked complete inside ChannelStore.update callback before channel charge committed (x402 #3854).",
            guard_id=guard_id,
        )
    if not channel_committed:
        return GuardResult(
            passed=False,
            action="Confirm",
            reason="REJECT: SVM channel charge not yet committed; defer operationStore.complete (x402 #3854).",
            guard_id=guard_id,
        )
    return GuardResult(
        passed=True,
        action="Act automatically",
        reason="PASS: SVM batch operations completed strictly after channel charge committed outside update callback (x402 #3854).",
        guard_id=guard_id,
    )


def evaluate_x402_recovery_extension_fail_closed_guard(payload: Dict[str, Any]) -> GuardResult:
    """PR-02: x402 #3848 recovery extension fail-closed settled-response replay and hash binding."""
    guard_id = "PR-02"
    settlement_status = str(payload.get("settlement_status", ""))
    req_hash = str(payload.get("request_hash", ""))
    expected_req_hash = str(payload.get("expected_request_hash", ""))
    resp_hash = str(payload.get("response_hash", ""))
    free_replay = bool(payload.get("allow_free_replay", False))

    if settlement_status != "confirmed":
        if free_replay:
            return GuardResult(
                passed=False,
                action="Send to a human",
                reason=f"REJECT: Free replay granted on non-confirmed settlement status '{settlement_status}' violating fail-closed recovery rule (x402 #3848).",
                guard_id=guard_id,
            )
        return GuardResult(
            passed=False,
            action="Confirm",
            reason=f"REJECT: Settlement status '{settlement_status}' is not confirmed; recovery replay denied (x402 #3848).",
            guard_id=guard_id,
        )
    if not req_hash or req_hash != expected_req_hash or not resp_hash:
        return GuardResult(
            passed=False,
            action="Send to a human",
            reason="REJECT: Recovery extension evidence projection request/response hash mismatch (x402 #3848).",
            guard_id=guard_id,
        )
    return GuardResult(
        passed=True,
        action="Act automatically",
        reason="PASS: Recovery extension verified confirmed settlement and matching request/response hashes (x402 #3848).",
        guard_id=guard_id,
    )


def evaluate_x402_evm_permit2_rpc_failure_disambiguation_guard(payload: Dict[str, Any]) -> GuardResult:
    """PR-03: x402 #3843 EVM Permit2 signature-check RPC failure reported as failed_to_verify_signature."""
    guard_id = "PR-03"
    rpc_error = bool(payload.get("rpc_transport_error", False))
    reported_code = str(payload.get("reported_error_code", ""))
    sig_valid = bool(payload.get("signature_valid", False))

    if rpc_error:
        if reported_code == "invalid_permit2_signature":
            return GuardResult(
                passed=False,
                action="Send to a human",
                reason="REJECT: Facilitator RPC outage during Permit2 check misreported as forged signature 'invalid_permit2_signature' instead of 'invalid_permit2_failed_to_verify_signature' (x402 #3843).",
                guard_id=guard_id,
            )
        return GuardResult(
            passed=False,
            action="Confirm",
            reason="REJECT: Permit2 signature check deferred due to facilitator RPC error 'invalid_permit2_failed_to_verify_signature' (x402 #3843).",
            guard_id=guard_id,
        )
    if not sig_valid:
        return GuardResult(
            passed=False,
            action="Send to a human",
            reason="REJECT: Cryptographically invalid Permit2 signature (x402 #3843).",
            guard_id=guard_id,
        )
    return GuardResult(
        passed=True,
        action="Act automatically",
        reason="PASS: Permit2 signature verified cleanly with distinct RPC failure reporting (x402 #3843).",
        guard_id=guard_id,
    )


def evaluate_x402_siwx_server_request_path_binding_guard(payload: Dict[str, Any]) -> GuardResult:
    """PR-04: x402 #3840 record SIWX payments on server request path instead of client resource.url."""
    guard_id = "PR-04"
    server_path = str(payload.get("server_request_path", ""))
    recorded_path = str(payload.get("recorded_payment_path", ""))
    client_resource_url = str(payload.get("client_resource_url", ""))

    if not server_path or recorded_path != server_path:
        return GuardResult(
            passed=False,
            action="Send to a human",
            reason=f"REJECT: SIWX payment recorded under '{recorded_path}' (client resource.url '{client_resource_url}') instead of server request path '{server_path}', enabling cross-route privilege escalation (x402 #3840).",
            guard_id=guard_id,
        )
    return GuardResult(
        passed=True,
        action="Act automatically",
        reason="PASS: SIWX payment recorded and verified strictly against server request path (x402 #3840).",
        guard_id=guard_id,
    )


def evaluate_x402_fastify_body_and_extensions_immutability_guard(payload: Dict[str, Any]) -> GuardResult:
    """PR-05: x402 #3834 Fastify non-JSON string settlement body preservation & #3826 402 extensions immutability."""
    guard_id = "PR-05"
    content_type = str(payload.get("content_type", "text/plain")).lower().split(";")[0].strip()
    body_is_string = bool(payload.get("body_is_string", True))
    json_encoded_on_wire = bool(payload.get("json_encoded_on_wire", False))
    mutated_caller_extensions = bool(payload.get("mutated_caller_extensions", False))

    is_json_media = content_type.endswith("/json") or content_type.endswith("+json")
    if body_is_string and not is_json_media and json_encoded_on_wire:
        return GuardResult(
            passed=False,
            action="Send to a human",
            reason=f"REJECT: Non-JSON string settlement body ({content_type}) was double-quoted via JSON.stringify in Fastify onSend hook (x402 #3834).",
            guard_id=guard_id,
        )
    if mutated_caller_extensions:
        return GuardResult(
            passed=False,
            action="Send to a human",
            reason="REJECT: createPaymentRequiredResponse mutated caller declaredExtensions object in place (x402 #3826).",
            guard_id=guard_id,
        )
    return GuardResult(
        passed=True,
        action="Act automatically",
        reason="PASS: Non-JSON settlement body sent as-is and 402 extensions shallow-cloned without mutating declaredExtensions (x402 #3834, #3826).",
        guard_id=guard_id,
    )


def evaluate_x402_v2_amount_format_and_go_settle_error_guard(payload: Dict[str, Any]) -> GuardResult:
    """PR-06: x402 #3828 scheme-specific v2 amount format validation & #3825 Go SettleError HTTP 200 mapping."""
    guard_id = "PR-06"
    scheme_type = str(payload.get("scheme_type", "atomic_uint"))
    amount_str = str(payload.get("amount", ""))
    client_rescaled = bool(payload.get("client_rescaled_invalid_amount", False))
    is_settle_error = bool(payload.get("is_wrapped_settle_error", False))
    http_status = int(payload.get("facilitator_http_status", 200))
    preserved_tx_hash = bool(payload.get("preserved_tx_hash", True))

    if client_rescaled:
        return GuardResult(
            passed=False,
            action="Send to a human",
            reason="REJECT: Client silently rounded or rescaled an invalid payment amount instead of failing validation (x402 #3828).",
            guard_id=guard_id,
        )
    if scheme_type == "atomic_uint" and (not amount_str or not amount_str.isascii() or not amount_str.isdigit()):
        return GuardResult(
            passed=False,
            action="Send to a human",
            reason=f"REJECT: Atomic-unit v2 payment amount '{amount_str}' is not a digit-only ASCII string (x402 #3828).",
            guard_id=guard_id,
        )
    if is_settle_error and (http_status != 200 or not preserved_tx_hash):
        return GuardResult(
            passed=False,
            action="Confirm",
            reason=f"REJECT: Wrapped *x402.SettleError returned HTTP {http_status} or dropped tx hash instead of HTTP 200 SettleResponse (x402 #3825).",
            guard_id=guard_id,
        )
    return GuardResult(
        passed=True,
        action="Act automatically",
        reason="PASS: V2 atomic-unit amount format verified and wrapped SettleError preserved on HTTP 200 SettleResponse (x402 #3828, #3825).",
        guard_id=guard_id,
    )


def evaluate_ucp_order_snapshot_and_catalog_purpose_guard(payload: Dict[str, Any]) -> GuardResult:
    """PR-07: UCP #903 Order read-only snapshot purity & #902 Catalog search purpose/reference_ids."""
    guard_id = "PR-07"
    order_directional_tags: List[str] = list(payload.get("order_directional_annotations", []))
    search_purpose = payload.get("catalog_search_purpose")
    reference_ids: List[str] = list(payload.get("catalog_reference_ids", []))

    if order_directional_tags:
        return GuardResult(
            passed=False,
            action="Send to a human",
            reason=f"REJECT: Order schema contains stray client request annotations {order_directional_tags} on business-emitted snapshot (UCP #903).",
            guard_id=guard_id,
        )
    if search_purpose is not None:
        if search_purpose not in ("recommendation", "swap"):
            return GuardResult(
                passed=False,
                action="Send to a human",
                reason=f"REJECT: Unsupported catalog search purpose '{search_purpose}' (must be 'recommendation' or 'swap', UCP #902).",
                guard_id=guard_id,
            )
        if not reference_ids:
            return GuardResult(
                passed=False,
                action="Confirm",
                reason=f"REJECT: Relational catalog search purpose '{search_purpose}' requires non-empty reference_ids (UCP #902).",
                guard_id=guard_id,
            )
    return GuardResult(
        passed=True,
        action="Act automatically",
        reason="PASS: Order schema is free of directional request annotations and catalog search purpose/reference_ids are valid (UCP #903, #902).",
        guard_id=guard_id,
    )


def evaluate_ucp_purchase_options_and_food_checkout_guard(payload: Dict[str, Any]) -> GuardResult:
    """PR-08: UCP #901 purchase_options extension & #897 Food Checkout fulfillment extension."""
    guard_id = "PR-08"
    advertised_ids: List[str] = list(payload.get("advertised_purchase_option_ids", []))
    selected_id = str(payload.get("selected_purchase_option_id", ""))
    order_line_option_id = str(payload.get("order_line_purchase_option_id", ""))
    food_fulfillment_active = bool(payload.get("food_fulfillment_active", False))
    food_slot_valid = bool(payload.get("food_fulfillment_slot_valid", True))

    if not selected_id or selected_id not in advertised_ids:
        return GuardResult(
            passed=False,
            action="Send to a human",
            reason=f"REJECT: selected_purchase_option_id '{selected_id}' is not in variant purchase_options {advertised_ids} (UCP #901).",
            guard_id=guard_id,
        )
    if order_line_option_id != selected_id:
        return GuardResult(
            passed=False,
            action="Send to a human",
            reason=f"REJECT: Order line purchase option '{order_line_option_id}' lost selected_purchase_option_id '{selected_id}' (UCP #901).",
            guard_id=guard_id,
        )
    if food_fulfillment_active and not food_slot_valid:
        return GuardResult(
            passed=False,
            action="Confirm",
            reason="REJECT: Food Checkout fulfillment extension missing valid prep/delivery window constraints (UCP #897).",
            guard_id=guard_id,
        )
    return GuardResult(
        passed=True,
        action="Act automatically",
        reason="PASS: Purchase option selection preserved onto Order line and Food Checkout fulfillment constraints satisfied (UCP #901, #897).",
        guard_id=guard_id,
    )


def evaluate_ucp_rfc9728_issuer_and_dns_email_linking_guard(payload: Dict[str, Any]) -> GuardResult:
    """PR-09: UCP #891 RFC 9728 authorization_servers exact issuer match & #876 DNS-delegated email linking."""
    guard_id = "PR-09"
    auth_server_entry = str(payload.get("authorization_server_entry", ""))
    discovered_issuer = str(payload.get("discovered_metadata_issuer", ""))
    auto_link_by_email = bool(payload.get("accelerated_idp_email_auto_link", False))
    email_verified = bool(payload.get("email_verified", False))
    dns_delegated_authority = bool(payload.get("idp_is_dns_delegated_email_authority", False))

    if not auth_server_entry or auth_server_entry != discovered_issuer:
        return GuardResult(
            passed=False,
            action="Send to a human",
            reason=f"REJECT: RFC 9728 authorization_servers entry '{auth_server_entry}' does not exactly match RFC 8414 discovered issuer '{discovered_issuer}' (UCP #891).",
            guard_id=guard_id,
        )
    if auto_link_by_email and (not email_verified or not dns_delegated_authority):
        return GuardResult(
            passed=False,
            action="Send to a human",
            reason="REJECT: Accelerated IdP email auto-linking attempted without both email_verified=true and DNS-delegated authoritative email issuer proof (UCP #876).",
            guard_id=guard_id,
        )
    return GuardResult(
        passed=True,
        action="Act automatically",
        reason="PASS: RFC 9728 authorization_servers issuer matches RFC 8414 metadata and email linking obeys DNS-delegated authority rule (UCP #891, #876).",
        guard_id=guard_id,
    )


def evaluate_ucp_conformance_corpus_mcp_complete_and_self_hosting_guard(payload: Dict[str, Any]) -> GuardResult:
    """PR-10: UCP #900 doc example conformance corpus, #883 MCP complete_checkout extensions & #882 vendor self-hosting."""
    guard_id = "PR-10"
    corpus_validated = bool(payload.get("conformance_corpus_validated", False))
    mcp_complete_has_extensions = bool(payload.get("mcp_complete_checkout_declares_extensions", False))
    vendor_ext_in_core_spec = bool(payload.get("vendor_extension_in_core_ucp_namespace", False))

    if not corpus_validated:
        return GuardResult(
            passed=False,
            action="Confirm",
            reason="REJECT: Spec example payload failed exported conformance corpus validation (UCP #900).",
            guard_id=guard_id,
        )
    if not mcp_complete_has_extensions:
        return GuardResult(
            passed=False,
            action="Send to a human",
            reason="REJECT: MCP complete_checkout schema omits supported checkout extensions block (UCP #883).",
            guard_id=guard_id,
        )
    if vendor_ext_in_core_spec:
        return GuardResult(
            passed=False,
            action="Send to a human",
            reason="REJECT: Vendor-specific extension or payment handler must be self-hosted, not placed in core dev.ucp.* namespace (UCP #882).",
            guard_id=guard_id,
        )
    return GuardResult(
        passed=True,
        action="Act automatically",
        reason="PASS: Exported conformance corpus validated, MCP complete_checkout extensions declared, and vendor extensions self-hosted (UCP #900, #883, #882).",
        guard_id=guard_id,
    )


def evaluate_mcp_py_stdio_jsonrpc_error_and_http_timeout_isolation_guard(payload: Dict[str, Any]) -> GuardResult:
    """PR-11: MCP Python SDK #3742 stdio unparseable line JSON-RPC error frame & #3741 HTTP ReadTimeout isolation."""
    guard_id = "PR-11"
    stdio_unparseable = bool(payload.get("stdio_line_unparseable", False))
    sent_jsonrpc_error_frame = bool(payload.get("sent_jsonrpc_error_frame", False))
    http_read_timeout = bool(payload.get("http_read_timeout_occurred", False))
    sibling_requests_cancelled = bool(payload.get("sibling_requests_cancelled", False))
    returned_request_timeout_code = int(payload.get("returned_error_code", -32001))

    if stdio_unparseable and not sent_jsonrpc_error_frame:
        return GuardResult(
            passed=False,
            action="Send to a human",
            reason="REJECT: Unparseable stdio line dropped as bare exception instead of returning a JSON-RPC error frame on the wire, hanging the client (mcp-py #3742).",
            guard_id=guard_id,
        )
    if http_read_timeout and (sibling_requests_cancelled or returned_request_timeout_code != -32001):
        return GuardResult(
            passed=False,
            action="Send to a human",
            reason="REJECT: StreamableHTTP ReadTimeout cancelled sibling requests or failed to return correlated REQUEST_TIMEOUT -32001 (mcp-py #3741).",
            guard_id=guard_id,
        )
    return GuardResult(
        passed=True,
        action="Act automatically",
        reason="PASS: Unparseable stdio lines receive JSON-RPC error frames and HTTP ReadTimeouts are isolated to the timed-out request task (mcp-py #3742, #3741).",
        guard_id=guard_id,
    )


def evaluate_mcp_py_param_collision_and_sync_prompt_awaitable_guard(payload: Dict[str, Any]) -> GuardResult:
    """PR-12: MCP Python SDK #3740 reserved tool parameter prefix collision & #3734 sync prompt awaitable resolution."""
    guard_id = "PR-12"
    has_prefix_collision = bool(payload.get("prefixed_param_name_collision", False))
    sync_prompt_returned_awaitable = bool(payload.get("sync_prompt_returned_awaitable", False))
    awaited_prompt_result = bool(payload.get("awaited_prompt_result", False))

    if has_prefix_collision:
        return GuardResult(
            passed=False,
            action="Send to a human",
            reason="REJECT: Tool parameter shadowing ArgModelBase attribute collided with another prefixed parameter name (mcp-py #3740).",
            guard_id=guard_id,
        )
    if sync_prompt_returned_awaitable and not awaited_prompt_result:
        return GuardResult(
            passed=False,
            action="Send to a human",
            reason="REJECT: Awaitable returned by sync prompt callback was serialized as raw coroutine string instead of being awaited (mcp-py #3734).",
            guard_id=guard_id,
        )
    return GuardResult(
        passed=True,
        action="Act automatically",
        reason="PASS: Reserved tool parameter prefixing avoids field collisions and sync prompt awaitables are properly awaited (mcp-py #3740, #3734).",
        guard_id=guard_id,
    )


def evaluate_mcp_py_oauth_resource_indicator_and_exact_expiry_guard(payload: Dict[str, Any]) -> GuardResult:
    """PR-13: MCP Python SDK #3739 RFC 8707 resource indicator in token exchange & #3730 exact-timestamp token expiry."""
    guard_id = "PR-13"
    requested_resource = str(payload.get("requested_resource_indicator", ""))
    forwarded_resource = str(payload.get("forwarded_resource_indicator", ""))
    current_time = float(payload.get("current_time", 1000.0))
    token_expiry_time = float(payload.get("token_expiry_time", 1001.0))
    accepted_token = bool(payload.get("token_accepted_as_valid", True))

    if requested_resource and forwarded_resource != requested_resource:
        return GuardResult(
            passed=False,
            action="Send to a human",
            reason=f"REJECT: OAuth token exchange dropped RFC 8707 resource indicator '{requested_resource}' (mcp-py #3739).",
            guard_id=guard_id,
        )
    is_expired = current_time >= token_expiry_time
    if is_expired and accepted_token:
        return GuardResult(
            passed=False,
            action="Send to a human",
            reason=f"REJECT: OAuth token accepted at or after exact expiration timestamp ({current_time} >= {token_expiry_time}), violating RFC 7519 §4.1.4 (mcp-py #3730).",
            guard_id=guard_id,
        )
    return GuardResult(
        passed=True,
        action="Act automatically",
        reason="PASS: RFC 8707 resource indicator preserved in token exchange and RFC 7519 strict '<' expiry enforced (mcp-py #3739, #3730).",
        guard_id=guard_id,
    )


def evaluate_mcp_py_sse_headers_uri_surrogateescape_and_skills_cache_guard(payload: Dict[str, Any]) -> GuardResult:
    """PR-14: MCP Python SDK #3726 per-response SSE header list, #3724 URI surrogateescape & #3719 Skills cache gate."""
    guard_id = "PR-14"
    shared_sse_header_list = bool(payload.get("shared_mutable_sse_headers", False))
    non_utf8_uri_replaced_with_fffd = bool(payload.get("non_utf8_uri_corrupted_to_fffd", False))
    protocol_version = str(payload.get("protocol_version", "2026-07-28"))
    sent_cache_fields = bool(payload.get("sent_directory_cache_fields", False))

    if shared_sse_header_list:
        return GuardResult(
            passed=False,
            action="Send to a human",
            reason="REJECT: SSE response reused shared module-level _SSE_HEADERS list, leaking middleware headers across responses (mcp-py #3726).",
            guard_id=guard_id,
        )
    if non_utf8_uri_replaced_with_fffd:
        return GuardResult(
            passed=False,
            action="Send to a human",
            reason="REJECT: UriTemplate.match corrupted non-UTF-8 percent-encoded octets into U+FFFD instead of preserving via surrogateescape (mcp-py #3724).",
            guard_id=guard_id,
        )
    if protocol_version < "2026-07-28" and sent_cache_fields:
        return GuardResult(
            passed=False,
            action="Confirm",
            reason=f"REJECT: ReadDirectoryResult sent ttlMs/cacheScope on pre-2026-07-28 protocol '{protocol_version}' (mcp-py #3719).",
            guard_id=guard_id,
        )
    return GuardResult(
        passed=True,
        action="Act automatically",
        reason="PASS: SSE header lists isolated, URI octets preserved via surrogateescape, and directory cache fields gated on 2026-07-28+ (mcp-py #3726, #3724, #3719).",
        guard_id=guard_id,
    )


def evaluate_tau2_retail_exchange_telecom_mms_and_gold_action_guard(payload: Dict[str, Any]) -> GuardResult:
    """PR-15: tau2-bench #667 retail same-item exchange rejection, #666 empty MMSC URL & #665 1-to-1 gold action matching."""
    guard_id = "PR-15"
    item_id = str(payload.get("item_id", "item_1"))
    new_item_id = str(payload.get("new_item_id", "item_2"))
    mmsc_url = payload.get("mmsc_url", "http://mms.carrier.com")
    mms_reported_capable = bool(payload.get("mms_reported_capable", False))
    required_gold_count = int(payload.get("required_gold_action_count", 1))
    predicted_call_count = int(payload.get("predicted_matching_call_count", 1))
    evaluator_marked_pass = bool(payload.get("evaluator_marked_pass", False))

    if item_id == new_item_id:
        return GuardResult(
            passed=False,
            action="Send to a human",
            reason=f"REJECT: exchange_delivered_order_items accepted same-item exchange (new_item_id == item_id == '{item_id}', tau2 #667).",
            guard_id=guard_id,
        )
    if (mmsc_url is None or str(mmsc_url).strip() == "") and mms_reported_capable:
        return GuardResult(
            passed=False,
            action="Send to a human",
            reason="REJECT: Telecom can_send_mms reported True when mmsc_url was empty string '' (tau2 #666).",
            guard_id=guard_id,
        )
    if predicted_call_count < required_gold_count and evaluator_marked_pass:
        return GuardResult(
            passed=False,
            action="Send to a human",
            reason=f"REJECT: Evaluator satisfied {required_gold_count} repeated gold actions with only {predicted_call_count} predicted call(s), violating 1-to-1 matching (tau2 #665).",
            guard_id=guard_id,
        )
    return GuardResult(
        passed=True,
        action="Act automatically",
        reason="PASS: Same-item exchanges rejected, empty MMSC URL treated as unconfigured, and gold actions matched 1-to-1 (tau2 #667, #666, #665).",
        guard_id=guard_id,
    )


def evaluate_tau2_knowledge_sandbox_and_voice_canonical_reload_guard(payload: Dict[str, Any]) -> GuardResult:
    """PR-16: tau2-bench #655 sandbox read-boundary, #653 minimal-env srt & #673 voice-v1 canonical task reload."""
    guard_id = "PR-16"
    inherited_parent_env = bool(payload.get("sandbox_inherited_parent_env", False))
    read_outside_kb = bool(payload.get("sandbox_read_outside_knowledge_base", False))
    voice_v1_canonical_preserved = bool(payload.get("voice_v1_canonical_tasks_preserved", True))

    if inherited_parent_env:
        return GuardResult(
            passed=False,
            action="Send to a human",
            reason="REJECT: SandboxManager.run_command inherited full parent environment instead of minimal allowlisted env (tau2 #653).",
            guard_id=guard_id,
        )
    if read_outside_kb:
        return GuardResult(
            passed=False,
            action="Send to a human",
            reason="REJECT: Knowledge sandbox permitted file read outside the knowledge base directory (tau2 #655).",
            guard_id=guard_id,
        )
    if not voice_v1_canonical_preserved:
        return GuardResult(
            passed=False,
            action="Confirm",
            reason="REJECT: voice-v1 integrity reload dropped canonical_tasks=True, breaking English retail/telecom hash verification (tau2 #673).",
            guard_id=guard_id,
        )
    return GuardResult(
        passed=True,
        action="Act automatically",
        reason="PASS: Knowledge sandbox enforces minimal environment and KB read boundaries, and voice-v1 reloads preserve canonical_tasks=True (tau2 #655, #653, #673).",
        guard_id=guard_id,
    )
