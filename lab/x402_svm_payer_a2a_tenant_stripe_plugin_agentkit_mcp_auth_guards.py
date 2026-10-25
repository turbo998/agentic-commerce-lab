"""Stage 266 deterministic protocol & security guards (2026-10-26).

Covers 16 zero-overlap primary-source PRs across x402, Google A2A Python SDK,
Stripe CLI/Node/Go SDKs, Coinbase AgentKit, and Model Context Protocol SDKs:
- PR-01: x402-foundation/x402#3941 (SVM exact SettlementResponse.payer authority vs fee payer)
- PR-02: x402-foundation/x402#3594 (Cardano Masumi escrow address callback decoupling)
- PR-03: x402-foundation/x402#3573 (Python x402[svm] solana>=0.36.0,<0.40 cap for solana.rpc.api)
- PR-04: x402-foundation/x402#3550 (TypeScript verify-package-exports non-empty & target file guard)
- PR-05: a2aproject/a2a-python#1377 (REST tenant route mounting under path_prefix/{tenant})
- PR-06: a2aproject/a2a-python#1375 (JSON-RPC malformed envelope & extra-field error code mapping)
- PR-07: a2aproject/a2a-python#1286/#1274/#1273 (Cross-SDK AgentCard JWS, application/a2a+json, ignore_unknown_fields)
- PR-08: stripe/stripe-cli#2155/#2143/#2141 (macOS release signing, pinned plugin OS/arch diagnostic, major upgrade block)
- PR-09: stripe/stripe-node#2895 & stripe/stripe-go#2457 (Fetch retry stream dispose, async notification verify, empty V1 page guard)
- PR-10: coinbase/agentkit#1510 & #1504 (x402Guard EIP-712 seller census verdict & KeeperHub taskId idempotency)
- PR-11: modelcontextprotocol/python-sdk#3761 (Strict now < expiry OAuth token boundary per RFC 7519)
- PR-12: modelcontextprotocol/python-sdk#3625/#3619/#3618 (Non-integer probe IDs, 300s read timeout, stateless cancellation guard)
- PR-13: modelcontextprotocol/go-sdk#1293/#1292/#1290 (Stream keep-alive WriteDeadline extension, SSE custom methods, non-null slices)
- PR-14: modelcontextprotocol/rust-sdk#1285 (CredentialStore.on_refresh_token_rejected only on definitive invalid_grant)
- PR-15: modelcontextprotocol/java-sdk#1210 & #1201 (Per-subscription notifierFactory null guard & LoggingMessageNotification.data coercion)
- PR-16: modelcontextprotocol/csharp-sdk#1878/#1874 & ext-apps#720 (MCP Apps 2026-01-26 handshake, Clone MarshalResult, peer isolation)
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import re
from typing import Any, Callable

_BASE58_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")
_SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:-[0-9A-Za-z.-]+)?$")


@dataclass(frozen=True)
class GuardVerdict:
    passed: bool
    guard_id: str
    reason_code: str
    action: str  # "Act automatically" | "Confirm" | "Send to a human"
    confidence: float
    details: dict[str, Any] = field(default_factory=dict)


def _pass(
    guard_id: str,
    reason_code: str = "ok",
    confidence: float = 0.99,
    **details: Any,
) -> GuardVerdict:
    return GuardVerdict(
        passed=True,
        guard_id=guard_id,
        reason_code=reason_code,
        action="Act automatically",
        confidence=confidence,
        details=details,
    )


def _fail(
    guard_id: str,
    reason_code: str,
    action: str = "Send to a human",
    confidence: float = 0.99,
    **details: Any,
) -> GuardVerdict:
    return GuardVerdict(
        passed=False,
        guard_id=guard_id,
        reason_code=reason_code,
        action=action,
        confidence=confidence,
        details=details,
    )


# PR-01: x402-foundation/x402#3941
def validate_x402_svm_settlement_payer_authority(
    reported_payer: str,
    transfer_authority: str,
    fee_payer: str,
) -> GuardVerdict:
    """Ensure SettlementResponse.payer is the base58 token transfer authority, not the facilitator feePayer."""
    guard_id = "PR-01:x402_svm_settlement_payer_authority"
    if not reported_payer or not _BASE58_RE.match(reported_payer):
        return _fail(
            guard_id,
            "svm_settlement_payer_invalid_base58",
            reported_payer=reported_payer,
        )
    if not transfer_authority or not _BASE58_RE.match(transfer_authority):
        return _fail(
            guard_id,
            "svm_transfer_authority_invalid_base58",
            transfer_authority=transfer_authority,
        )
    if reported_payer != transfer_authority:
        reason = (
            "svm_settlement_payer_returned_facilitator_fee_payer"
            if reported_payer == fee_payer
            else "svm_settlement_payer_authority_mismatch"
        )
        return _fail(
            guard_id,
            reason,
            reported_payer=reported_payer,
            transfer_authority=transfer_authority,
            fee_payer=fee_payer,
        )
    return _pass(
        guard_id,
        "svm_settlement_payer_matches_transfer_authority",
        reported_payer=reported_payer,
        fee_payer=fee_payer,
    )


# PR-02: x402-foundation/x402#3594
def validate_x402_cardano_payto_resolver(
    network: str,
    direct_cardano_prebuild_import: bool,
    masumi_escrow_resolver: Callable[[str], str] | None,
) -> GuardVerdict:
    """Reject direct @x402/cardano pre-build imports in e2e and require an injected Masumi escrow callback."""
    guard_id = "PR-02:x402_cardano_payto_resolver"
    if direct_cardano_prebuild_import:
        return _fail(
            guard_id,
            "cardano_direct_prebuild_import_blocked",
            network=network,
        )
    if network.startswith("cardano:"):
        if masumi_escrow_resolver is None:
            return _fail(
                guard_id,
                "cardano_escrow_resolver_missing",
                network=network,
            )
        resolved = masumi_escrow_resolver(network)
        if not resolved or not resolved.startswith(("addr1", "addr_test1")):
            return _fail(
                guard_id,
                "cardano_escrow_address_invalid",
                network=network,
                resolved=resolved,
            )
        return _pass(
            guard_id,
            "cardano_payto_resolved_via_callback",
            network=network,
            pay_to=resolved,
        )
    return _pass(guard_id, "non_cardano_network_ok", network=network)


# PR-03: x402-foundation/x402#3573
def validate_x402_python_svm_solana_version_cap(
    solana_version: str,
    has_solana_rpc_api: bool,
) -> GuardVerdict:
    """Enforce solana>=0.36.0,<0.40 in Python x402[svm] so solana.rpc.api remains importable."""
    guard_id = "PR-03:x402_python_svm_solana_version_cap"
    match = _SEMVER_RE.match(solana_version.strip())
    if not match:
        return _fail(guard_id, "solana_version_invalid_semver", solana_version=solana_version)
    major, minor, patch = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    if (major, minor) < (0, 36):
        return _fail(
            guard_id,
            "solana_version_below_minimum_0_36",
            solana_version=solana_version,
        )
    if (major, minor) >= (0, 40) or not has_solana_rpc_api:
        return _fail(
            guard_id,
            "solana_0_40_rpc_api_removed",
            solana_version=solana_version,
            has_solana_rpc_api=has_solana_rpc_api,
        )
    return _pass(
        guard_id,
        "solana_version_within_0_36_to_0_40_cap",
        solana_version=f"{major}.{minor}.{patch}",
    )


# PR-04: x402-foundation/x402#3550
def validate_x402_package_exports_bundle(
    checked_count: int,
    declared_targets: dict[str, str],
    existing_files: set[str],
    allow_empty: bool = False,
) -> GuardVerdict:
    """Fail closed when verify-package-exports checks 0 built packages or finds missing dist targets."""
    guard_id = "PR-04:x402_package_exports_bundle"
    if checked_count <= 0 and not allow_empty:
        return _fail(
            guard_id,
            "verify_exports_zero_packages_checked",
            checked_count=checked_count,
        )
    missing = [
        f"{cond}:{target}"
        for cond, target in sorted(declared_targets.items())
        if target not in existing_files
    ]
    if missing:
        return _fail(
            guard_id,
            "verify_exports_missing_target_file",
            missing=missing,
        )
    return _pass(
        guard_id,
        "verify_exports_all_targets_present",
        checked_count=checked_count,
        verified_targets=len(declared_targets),
    )


# PR-05: a2aproject/a2a-python#1377
def validate_a2a_rest_tenant_prefix_mount(
    path_prefix: str,
    mounted_pattern: str,
    request_path: str,
) -> GuardVerdict:
    """Ensure A2A REST tenant routes mount at {path_prefix}/{tenant}/... instead of /{tenant}{path_prefix}/..."""
    guard_id = "PR-05:a2a_rest_tenant_prefix_mount"
    normalized_prefix = "/" + path_prefix.strip("/") if path_prefix.strip("/") else ""
    expected_prefix = f"{normalized_prefix}/{{tenant}}"
    if not mounted_pattern.startswith(expected_prefix):
        return _fail(
            guard_id,
            "a2a_rest_tenant_mounted_before_prefix",
            mounted_pattern=mounted_pattern,
            expected_prefix=expected_prefix,
        )
    prefix_with_slash = normalized_prefix + "/"
    if not request_path.startswith(prefix_with_slash):
        return _fail(
            guard_id,
            "a2a_rest_request_missing_path_prefix",
            request_path=request_path,
            expected_prefix=normalized_prefix,
        )
    remainder = request_path[len(prefix_with_slash) :]
    parts = [p for p in remainder.split("/") if p]
    if len(parts) < 2:
        return _fail(guard_id, "a2a_rest_tenant_or_route_missing", request_path=request_path)
    tenant = parts[0]
    return _pass(
        guard_id,
        "a2a_rest_tenant_context_resolved",
        tenant=tenant,
        route="/" + "/".join(parts[1:]),
    )


# PR-06: a2aproject/a2a-python#1375
_A2A_ERROR_CODE_MAP: dict[int, str] = {
    -32700: "JSONParseError",
    -32600: "InvalidRequestError",
    -32601: "MethodNotFoundError",
    -32602: "InvalidParamsError",
    -32603: "InternalError",
    -32001: "TaskNotFoundError",
    -32002: "TaskNotCancelableError",
    -32003: "PushNotificationNotSupportedError",
    -32004: "UnsupportedOperationError",
    -32005: "ContentTypeNotSupportedError",
    -32006: "InvalidAgentResponseError",
    -32007: "ExtendedAgentCardNotConfiguredError",
    -32008: "ExtensionSupportRequiredError",
    -32009: "VersionNotSupportedError",
}


def validate_a2a_jsonrpc_response_envelope(response_data: Any) -> GuardVerdict:
    """Validate JSON-RPC response dict and map error codes even when extra fields (e.g. reason) exist."""
    guard_id = "PR-06:a2a_jsonrpc_response_envelope"
    if not isinstance(response_data, dict):
        return _fail(guard_id, "a2a_jsonrpc_non_object_response")
    if "error" not in response_data and "result" not in response_data:
        return _fail(guard_id, "a2a_jsonrpc_missing_result_and_error")
    error = response_data.get("error")
    if error is not None:
        if not isinstance(error, dict):
            return _fail(guard_id, "a2a_jsonrpc_non_object_error")
        code = error.get("code")
        if not isinstance(code, int) or isinstance(code, bool):
            return _fail(guard_id, "a2a_jsonrpc_non_integer_error_code", code=code)
        mapped_error = _A2A_ERROR_CODE_MAP.get(code, "A2AClientJSONRPCError")
        return _fail(
            guard_id,
            f"a2a_jsonrpc_mapped_{mapped_error}",
            action="Confirm",
            mapped_error=mapped_error,
            code=code,
            message=str(error.get("message", "")),
        )
    return _pass(guard_id, "a2a_jsonrpc_valid_result_envelope")


# PR-07: a2aproject/a2a-python#1286, #1274, #1273
def validate_a2a_card_jws_and_rest_media_type(
    canonical_card_utf8: bytes,
    expected_canonical_hex: str,
    content_type: str,
    message_payload: dict[str, Any],
) -> GuardVerdict:
    """Verify cross-SDK AgentCard canonical bytes, application/a2a+json header, and structural field shape."""
    guard_id = "PR-07:a2a_card_jws_and_rest_media_type"
    actual_hex = canonical_card_utf8.hex()
    if actual_hex != expected_canonical_hex.lower():
        return _fail(
            guard_id,
            "a2a_card_signature_canonical_bytes_mismatch",
            actual_sha256=hashlib.sha256(canonical_card_utf8).hexdigest()[:16],
        )
    if not content_type.lower().startswith("application/a2a+json"):
        return _fail(
            guard_id,
            "a2a_rest_wrong_media_type",
            content_type=content_type,
        )
    parts = message_payload.get("parts")
    if parts is not None and not isinstance(parts, list):
        return _fail(
            guard_id,
            "a2a_invalid_params_parts_not_list",
            error_info={
                "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                "reason": "INVALID_PARAMS",
                "metadata": {"parseError": "parts must be a list"},
            },
        )
    ignored_unknown = [
        k for k in message_payload if k not in {"role", "parts", "messageId", "taskId", "contextId"}
    ]
    return _pass(
        guard_id,
        "a2a_card_verified_and_media_type_valid",
        content_type=content_type,
        ignored_unknown_fields=ignored_unknown,
    )


# PR-08: stripe/stripe-cli#2155, #2143, #2141
_REQUIRED_MACOS_SIGN_ENV = {
    "MACOS_SIGN_P12",
    "MACOS_SIGN_PASSWORD",
    "MACOS_NOTARY_ISSUER_ID",
    "MACOS_NOTARY_KEY_ID",
    "MACOS_NOTARY_KEY",
}


def validate_stripe_cli_plugin_and_release_guard(
    installed_version: str,
    target_version: str,
    is_auto_upgrade: bool,
    available_builds_for_target: set[str],
    requested_os_arch: str,
    release_env_keys: set[str],
) -> GuardVerdict:
    """Block silent major plugin auto-upgrades, diagnose OS/arch build gaps, and verify macOS signing secrets."""
    guard_id = "PR-08:stripe_cli_plugin_and_release_guard"
    missing_secrets = sorted(_REQUIRED_MACOS_SIGN_ENV - set(release_env_keys))
    if missing_secrets:
        return _fail(
            guard_id,
            "stripe_release_macos_signing_secrets_missing",
            missing_secrets=missing_secrets,
        )
    inst_match = _SEMVER_RE.match(installed_version.strip())
    targ_match = _SEMVER_RE.match(target_version.strip())
    if inst_match and targ_match:
        inst_major = int(inst_match.group(1))
        targ_major = int(targ_match.group(1))
        if is_auto_upgrade and targ_major != inst_major:
            return _fail(
                guard_id,
                "stripe_plugin_major_autoupgrade_blocked",
                action="Confirm",
                installed_version=installed_version,
                target_version=target_version,
                remediation="Run `stripe plugin upgrade <name>` explicitly",
            )
    if not available_builds_for_target:
        return _fail(
            guard_id,
            "stripe_plugin_version_does_not_exist",
            target_version=target_version,
        )
    if requested_os_arch not in available_builds_for_target:
        return _fail(
            guard_id,
            "stripe_plugin_os_arch_build_unavailable",
            target_version=target_version,
            requested_os_arch=requested_os_arch,
            available_builds=sorted(available_builds_for_target),
        )
    return _pass(
        guard_id,
        "stripe_plugin_and_release_verified",
        installed_version=installed_version,
        target_version=target_version,
    )


# PR-09: stripe/stripe-node#2895 & stripe/stripe-go#2457
def validate_stripe_sdk_retry_dispose_and_pagination(
    retry_scheduled: bool,
    discarded_response_disposed: bool,
    async_signature_verified: bool,
    page_data_len: int,
    has_more: bool,
    single_page_mode: bool = False,
) -> GuardVerdict:
    """Require fetch response disposal before retry, async webhook crypto verify, and non-empty has_more pages."""
    guard_id = "PR-09:stripe_sdk_retry_dispose_and_pagination"
    if retry_scheduled and not discarded_response_disposed:
        return _fail(
            guard_id,
            "stripe_retry_undisposed_stream_leak",
            retry_scheduled=retry_scheduled,
        )
    if not async_signature_verified:
        return _fail(
            guard_id,
            "stripe_webhook_sync_crypto_unsupported_on_edge",
        )
    if page_data_len == 0 and has_more and not single_page_mode:
        return _fail(
            guard_id,
            "stripe_empty_page_has_more_infinite_loop",
            error="stripe: invalid list response: has_more is true but data is empty",
        )
    return _pass(
        guard_id,
        "stripe_retry_disposed_and_page_valid",
        page_data_len=page_data_len,
        has_more=has_more,
    )


# PR-10: coinbase/agentkit#1510 & #1504
def validate_agentkit_x402_guard_and_keeperhub_idempotency(
    seller_verdict: str,
    eip712_attestation_valid: bool,
    simulate_before_broadcast: bool,
    simulation_reverted: bool,
    task_id: str,
    seen_task_ids: dict[str, str],
) -> GuardVerdict:
    """Enforce x402Guard EIP-712 seller trust verdict and KeeperHub mandatory simulation + taskId replay."""
    guard_id = "PR-10:agentkit_x402_guard_and_keeperhub_idempotency"
    if not eip712_attestation_valid:
        return _fail(guard_id, "agentkit_x402_guard_invalid_eip712_attestation")
    if seller_verdict not in {"pay", "caution", "avoid"}:
        return _fail(guard_id, "agentkit_x402_guard_unknown_verdict", seller_verdict=seller_verdict)
    if seller_verdict == "avoid":
        return _fail(guard_id, "agentkit_x402_seller_avoid_blocked", seller_verdict=seller_verdict)
    if not simulate_before_broadcast:
        return _fail(guard_id, "agentkit_keeperhub_simulation_disabled")
    if simulation_reverted:
        return _fail(guard_id, "agentkit_keeperhub_simulation_predicted_revert")
    if task_id in seen_task_ids:
        return _fail(
            guard_id,
            "agentkit_keeperhub_duplicate_transfer_replayed",
            action="Confirm",
            task_id=task_id,
            replayed_execution_id=seen_task_ids[task_id],
        )
    if seller_verdict == "caution":
        return GuardVerdict(
            passed=True,
            guard_id=guard_id,
            reason_code="agentkit_x402_seller_caution_confirm",
            action="Confirm",
            confidence=0.86,
            details={"task_id": task_id, "seller_verdict": seller_verdict},
        )
    return _pass(
        guard_id,
        "agentkit_x402_pay_and_keeperhub_new_execution",
        task_id=task_id,
    )


# PR-11: modelcontextprotocol/python-sdk#3761
def validate_mcp_oauth_strict_expiry_boundary(
    now_epoch: float,
    expiry_epoch: float,
) -> GuardVerdict:
    """Treat OAuth / identity-assertion tokens as expired at exact expiry timestamp (now < expiry)."""
    guard_id = "PR-11:mcp_oauth_strict_expiry_boundary"
    if not (now_epoch < expiry_epoch):
        return _fail(
            guard_id,
            "mcp_oauth_token_expired_at_or_past_boundary",
            action="Confirm",
            now_epoch=now_epoch,
            expiry_epoch=expiry_epoch,
        )
    return _pass(
        guard_id,
        "mcp_oauth_token_strictly_unexpired",
        remaining_seconds=round(expiry_epoch - now_epoch, 3),
    )


# PR-12: modelcontextprotocol/python-sdk#3625, #3619, #3618
def validate_mcp_python_stream_probe_and_timeout(
    probe_request_id: str | int,
    custom_client_read_timeout_sec: float,
    stateless_or_json_response: bool,
    expects_disconnect_cancellation: bool,
) -> GuardVerdict:
    """Require non-integer internal stream probe IDs, >=300s SSE read timeout, and flag stateless disconnect caveats."""
    guard_id = "PR-12:mcp_python_stream_probe_and_timeout"
    if isinstance(probe_request_id, int) or (
        isinstance(probe_request_id, str) and probe_request_id.isdigit()
    ):
        return _fail(
            guard_id,
            "mcp_internal_probe_integer_id_collision",
            probe_request_id=probe_request_id,
        )
    if custom_client_read_timeout_sec < 300.0:
        return _fail(
            guard_id,
            "mcp_httpx_default_read_timeout_too_short",
            read_timeout_sec=custom_client_read_timeout_sec,
        )
    if stateless_or_json_response and expects_disconnect_cancellation:
        return _fail(
            guard_id,
            "mcp_stateless_or_json_response_disables_disconnect_cancel",
            action="Confirm",
        )
    return _pass(
        guard_id,
        "mcp_stream_probe_and_timeout_valid",
        probe_request_id=probe_request_id,
        read_timeout_sec=custom_client_read_timeout_sec,
    )


# PR-13: modelcontextprotocol/go-sdk#1293, #1292, #1290
def validate_mcp_go_stream_deadline_sse_custom_and_nonnull_slices(
    keep_alive_interval_ms: int,
    write_deadline_advanced_ms: int,
    method_name: str,
    standard_methods: set[str],
    custom_methods: set[str],
    completion_values: list[str] | None,
    prompt_messages: list[dict[str, Any]] | None,
) -> GuardVerdict:
    """Verify WriteDeadline advances by 2*keepAliveInterval, SSE allows custom methods, and nil slices normalize to []."""
    guard_id = "PR-13:mcp_go_stream_deadline_sse_custom_and_nonnull_slices"
    if keep_alive_interval_ms > 0 and write_deadline_advanced_ms < 2 * keep_alive_interval_ms:
        return _fail(
            guard_id,
            "mcp_go_stream_write_deadline_not_extended",
            keep_alive_interval_ms=keep_alive_interval_ms,
            write_deadline_advanced_ms=write_deadline_advanced_ms,
        )
    allowed_methods = standard_methods | custom_methods
    if method_name not in allowed_methods:
        return _fail(
            guard_id,
            "mcp_go_sse_unregistered_method_rejected",
            method_name=method_name,
        )
    normalized_values = [] if completion_values is None else completion_values
    normalized_messages = [] if prompt_messages is None else prompt_messages
    return _pass(
        guard_id,
        "mcp_go_stream_sse_and_slices_valid",
        method_name=method_name,
        normalized_values=normalized_values,
        normalized_messages=normalized_messages,
    )


# PR-14: modelcontextprotocol/rust-sdk#1285
def validate_mcp_rust_refresh_token_revocation_policy(
    oauth_error_code: str,
    revoked_stored_credentials: bool,
) -> GuardVerdict:
    """Invoke on_refresh_token_rejected if and only if OAuth refresh fails with definitive invalid_grant."""
    guard_id = "PR-14:mcp_rust_refresh_token_revocation_policy"
    is_invalid_grant = oauth_error_code == "invalid_grant"
    if is_invalid_grant and not revoked_stored_credentials:
        return _fail(
            guard_id,
            "mcp_rust_invalid_grant_must_revoke_credentials",
            oauth_error_code=oauth_error_code,
        )
    if not is_invalid_grant and revoked_stored_credentials:
        return _fail(
            guard_id,
            "mcp_rust_transient_error_must_preserve_credentials",
            oauth_error_code=oauth_error_code,
        )
    return _pass(
        guard_id,
        "mcp_rust_refresh_revocation_policy_matched",
        oauth_error_code=oauth_error_code,
        revoked_stored_credentials=revoked_stored_credentials,
    )


# PR-15: modelcontextprotocol/java-sdk#1210 & #1201
def validate_mcp_java_notifier_factory_and_logging_coercion(
    is_streaming_handler: bool,
    notifier_factory_returned_null: bool,
    log_level: str | None,
    raw_log_data: Any,
) -> GuardVerdict:
    """Reject null per-subscription notifiers on streaming handlers and coerce structured log data via str()."""
    guard_id = "PR-15:mcp_java_notifier_factory_and_logging_coercion"
    if is_streaming_handler and notifier_factory_returned_null:
        return _fail(
            guard_id,
            "mcp_java_null_stream_notifier_internal_error",
            jsonrpc_error_code=-32603,
        )
    if not log_level or raw_log_data is None:
        return _fail(
            guard_id,
            "mcp_java_logging_missing_level_or_data",
            log_level=log_level,
        )
    coerced_data = raw_log_data if isinstance(raw_log_data, str) else str(raw_log_data)
    return _pass(
        guard_id,
        "mcp_java_notifier_and_logging_coercion_valid",
        coerced_data=coerced_data,
    )


# PR-16: modelcontextprotocol/csharp-sdk#1878, #1874 & modelcontextprotocol/ext-apps#720
def validate_mcp_apps_v2_peer_isolation_and_csharp_clone(
    ui_initialize_version: str,
    cloned_has_marshal_result: bool,
    server_entry_imports_client_peer: bool,
) -> GuardVerdict:
    """Verify MCP Apps 2026-01-26 handshake, preserved MarshalResult on Clone(), and server/client peer isolation."""
    guard_id = "PR-16:mcp_apps_v2_peer_isolation_and_csharp_clone"
    if ui_initialize_version != "2026-01-26":
        return _fail(
            guard_id,
            "mcp_apps_protocol_version_outdated",
            ui_initialize_version=ui_initialize_version,
        )
    if not cloned_has_marshal_result:
        return _fail(
            guard_id,
            "mcp_csharp_clone_dropped_marshal_result",
        )
    if server_entry_imports_client_peer:
        return _fail(
            guard_id,
            "mcp_apps_server_imports_client_peer",
        )
    return _pass(
        guard_id,
        "mcp_apps_v2_and_csharp_clone_verified",
        ui_initialize_version=ui_initialize_version,
    )
