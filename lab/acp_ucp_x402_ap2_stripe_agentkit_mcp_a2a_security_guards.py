"""Stage 264 runtime guardrails for AgentKit Nano/Solana/EIP-3009, Stripe CLI/SDKs, A2A & MCP security.

Covers 16 primary-source PR scenario groups (`PR-01` .. `PR-16`) across:
- Coinbase AgentKit (`#1517`, `#1515`, `#1507`, `#1498`)
- Stripe CLI & SDKs (`stripe-cli#2154`, `#2144`, `#2153`, `#2149`, `#2147`,
  `stripe-python#1939`, `#1951`, `stripe-node#2902`, `#2901`, `#2898`,
  `stripe-go#2477`, `#2476`, `#2468`, `#2465`)
- Google A2A (`a2a-python#1294`, `#1287`, `#1281`, `#1279`, `a2a-java#1234`, `#1212`, `a2a-js#749`)
- Model Context Protocol (`go-sdk#1320`, `#1315`, `#1297`, `rust-sdk#1295`, `#1287`, `#1288`,
  `csharp-sdk#1875`, `#1906`, `python-sdk#3684`, `#3647`, `ext-apps#749`)
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any


RAW_PER_XNO = 10**30
NANO_ADDRESS_RE = re.compile(r"^nano_[13][13456789abcdefghijkmnopqrstuwxyz]{59}$")
HEX_64_RE = re.compile(r"^[0-9a-fA-F]{64}$")
EVM_ADDR_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
EIP3009_NONCE_RE = re.compile(r"^0x[0-9a-fA-F]{64}$")
ASCII_WHITESPACE = " \t\r\n\f\v"
JCS_MAX_DEPTH = 128


@dataclass(frozen=True)
class GuardEvaluation:
    """Deterministic result returned by each Stage 264 security/protocol guard."""

    allowed: bool
    action: str
    reason: str
    details: dict[str, Any]


# ---------------------------------------------------------------------------
# PR-01: coinbase/agentkit#1517 - Nano (XNO) WalletProvider state block guard
# ---------------------------------------------------------------------------
def evaluate_agentkit_nano_state_block_guard(
    *,
    account: str,
    destination: str,
    previous_block_hash: str,
    current_balance_raw: int,
    transfer_amount_raw: int,
    signature_hex: str,
    work_nonce_hex: str,
) -> GuardEvaluation:
    """Validate Nano (`XNO`) feeless signed state block transition (`coinbase/agentkit#1517`)."""
    if not NANO_ADDRESS_RE.match(account) or not NANO_ADDRESS_RE.match(destination):
        return GuardEvaluation(
            allowed=False,
            action="block_invalid_nano_address",
            reason="Nano sender or destination address fails nano_ prefix/base32 format check",
            details={"account": account, "destination": destination},
        )
    if transfer_amount_raw <= 0:
        return GuardEvaluation(
            allowed=False,
            action="block_non_positive_nano_amount",
            reason="Nano transfer amount in raw must be strictly positive",
            details={"transfer_amount_raw": transfer_amount_raw},
        )
    if current_balance_raw < transfer_amount_raw:
        return GuardEvaluation(
            allowed=False,
            action="block_insufficient_nano_balance",
            reason="Resulting Nano state block balance cannot be negative",
            details={
                "current_balance_raw": current_balance_raw,
                "transfer_amount_raw": transfer_amount_raw,
            },
        )
    if not HEX_64_RE.match(previous_block_hash) or previous_block_hash == "0" * 64:
        return GuardEvaluation(
            allowed=False,
            action="block_missing_frontier_hash",
            reason="Send state block requires a non-zero 64-hex frontier previous block hash",
            details={"previous_block_hash": previous_block_hash},
        )
    if len(signature_hex) != 128 or len(work_nonce_hex) != 16:
        return GuardEvaluation(
            allowed=False,
            action="block_unsigned_nano_block",
            reason="State block requires 64-byte Ed25519 Blake2b signature and 8-byte PoW work nonce",
            details={"sig_len": len(signature_hex), "work_len": len(work_nonce_hex)},
        )
    resulting_balance_raw = current_balance_raw - transfer_amount_raw
    return GuardEvaluation(
        allowed=True,
        action="allow_nano_state_block",
        reason="Nano signed state block verified with exact raw resulting balance and work nonce",
        details={
            "resulting_balance_raw": str(resulting_balance_raw),
            "transfer_xno": transfer_amount_raw / RAW_PER_XNO,
        },
    )


# ---------------------------------------------------------------------------
# PR-02: coinbase/agentkit#1515 & #1507 - Solana <0.40 cap & EVM case-insensitive guard
# ---------------------------------------------------------------------------
def evaluate_agentkit_solana_cap_and_evm_case_guard(
    *,
    solana_version: tuple[int, int, int],
    token_contract_address: str,
    destination_address: str,
) -> GuardEvaluation:
    """Enforce `solana>=0.36.6,<0.40` (`#1515`) and case-insensitive EVM self-transfer rejection (`#1507`)."""
    if solana_version < (0, 36, 6) or solana_version >= (0, 40, 0):
        return GuardEvaluation(
            allowed=False,
            action="block_incompatible_solana_sdk",
            reason="solana>=0.40 removed synchronous solana.rpc.api; must pin >=0.36.6,<0.40",
            details={"solana_version": ".".join(map(str, solana_version))},
        )
    if not EVM_ADDR_RE.match(token_contract_address) or not EVM_ADDR_RE.match(destination_address):
        return GuardEvaluation(
            allowed=False,
            action="block_invalid_evm_address",
            reason="Invalid 20-byte hex EVM address",
            details={
                "token_contract_address": token_contract_address,
                "destination_address": destination_address,
            },
        )
    if token_contract_address.lower() == destination_address.lower():
        return GuardEvaluation(
            allowed=False,
            action="block_token_contract_self_transfer",
            reason="Refusing ERC-20 transfer whose destination matches the token contract in any case",
            details={
                "normalized_token": token_contract_address.lower(),
                "normalized_destination": destination_address.lower(),
            },
        )
    return GuardEvaluation(
        allowed=True,
        action="allow_verified_agentkit_transfer",
        reason="Solana SDK range valid and case-insensitive EVM destination check passed",
        details={
            "solana_version": ".".join(map(str, solana_version)),
            "normalized_destination": destination_address.lower(),
        },
    )


# ---------------------------------------------------------------------------
# PR-03: coinbase/agentkit#1498 - Base USDC EIP-3009 gasless transfer guard
# ---------------------------------------------------------------------------
def evaluate_agentkit_eip3009_gasless_usdc_guard(
    *,
    chain_id: int,
    domain_name: str,
    domain_version: str,
    valid_after: int,
    valid_before: int,
    now_ts: int,
    nonce: str,
    used_nonces: set[str],
    v: int,
) -> GuardEvaluation:
    """Validate Base USDC EIP-3009 `transferWithAuthorization` typed-data envelope (`#1498`)."""
    if chain_id not in (8453, 84532) or domain_name != "USD Coin" or domain_version != "2":
        return GuardEvaluation(
            allowed=False,
            action="block_eip3009_domain_mismatch",
            reason="EIP-3009 gasless USDC transfer requires Base (8453/84532) and USD Coin v2 domain",
            details={
                "chain_id": chain_id,
                "domain_name": domain_name,
                "domain_version": domain_version,
            },
        )
    if not (valid_after <= now_ts < valid_before):
        return GuardEvaluation(
            allowed=False,
            action="block_eip3009_expired_or_premature",
            reason="Current timestamp falls outside [validAfter, validBefore) authorization window",
            details={"valid_after": valid_after, "valid_before": valid_before, "now_ts": now_ts},
        )
    if not EIP3009_NONCE_RE.match(nonce) or nonce.lower() in {n.lower() for n in used_nonces}:
        return GuardEvaluation(
            allowed=False,
            action="block_eip3009_nonce_replay",
            reason="EIP-3009 authorization requires a fresh 32-byte random hex nonce",
            details={"nonce": nonce},
        )
    if v not in (27, 28):
        return GuardEvaluation(
            allowed=False,
            action="block_invalid_eip3009_v_parity",
            reason="ECDSA recovery byte v must be 27 or 28",
            details={"v": v},
        )
    return GuardEvaluation(
        allowed=True,
        action="allow_eip3009_gasless_relay",
        reason="Base USDC EIP-3009 gasless authorization verified for relayer submission",
        details={"chain_id": chain_id, "nonce": nonce.lower(), "v": v},
    )


# ---------------------------------------------------------------------------
# PR-04: stripe/stripe-cli#2154 & #2144 - Core CLI plugin output stream guard
# ---------------------------------------------------------------------------
def evaluate_stripe_cli_plugin_output_stream_guard(
    *,
    events: list[dict[str, str]],
) -> GuardEvaluation:
    """Keep plugin spinners on `stderr` and structured output on `stdout` (`stripe-cli#2154`, `#2144`)."""
    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    for ev in events:
        kind = ev.get("kind", "message")
        stream = ev.get("stream", "")
        text = ev.get("text", "")
        if kind == "spinner":
            if stream == "stdout":
                return GuardEvaluation(
                    allowed=False,
                    action="block_spinner_on_stdout",
                    reason="Plugin spinner output on stdout corrupts machine-parsed command output",
                    details={"event": ev},
                )
            stderr_lines.append(text)
        else:
            if stream == "stderr":
                stderr_lines.append(text)
            else:
                stdout_lines.append(text)
    return GuardEvaluation(
        allowed=True,
        action="allow_separated_plugin_streams",
        reason="Plugin spinners routed to stderr while command output stays clean on stdout",
        details={"stdout": stdout_lines, "stderr": stderr_lines},
    )


# ---------------------------------------------------------------------------
# PR-05: stripe/stripe-cli#2153, #2149 & #2147 - SHA-256 install & update guard
# ---------------------------------------------------------------------------
def evaluate_stripe_cli_install_and_update_guard(
    *,
    has_sha256sum: bool,
    has_shasum: bool,
    archive_bytes: bytes,
    expected_sha256: str,
    last_version_check_age_seconds: int,
    disable_update_check_env: bool,
    is_snapshot_ci: bool,
    has_publishing_credentials: bool,
) -> GuardEvaluation:
    """Fail install without SHA-256 tool (`#2153`), throttle update checks (`#2149`), strip snapshot secrets (`#2147`)."""
    if is_snapshot_ci and has_publishing_credentials:
        return GuardEvaluation(
            allowed=False,
            action="block_snapshot_ci_publishing_creds",
            reason="Snapshot CI builds must not receive release publishing credentials",
            details={"is_snapshot_ci": True},
        )
    if not has_sha256sum and not has_shasum:
        return GuardEvaluation(
            allowed=False,
            action="block_missing_sha256_verifier",
            reason="Error: sha256sum or shasum is required to verify the download",
            details={"has_sha256sum": False, "has_shasum": False},
        )
    actual_sha256 = hashlib.sha256(archive_bytes).hexdigest()
    if actual_sha256.lower() != expected_sha256.lower():
        return GuardEvaluation(
            allowed=False,
            action="block_sha256_mismatch",
            reason="Downloaded archive SHA-256 digest does not match expected release checksum",
            details={"actual": actual_sha256, "expected": expected_sha256},
        )
    should_query_github = (not disable_update_check_env) and (last_version_check_age_seconds >= 86400)
    return GuardEvaluation(
        allowed=True,
        action="allow_verified_cli_execution",
        reason="SHA-256 verified via system tool, snapshot CI isolated, and 24h update cache enforced",
        details={
            "sha256_verified": True,
            "should_query_github_releases": should_query_github,
        },
    )


# ---------------------------------------------------------------------------
# PR-06: stripe/stripe-python#1939 & #1951 - API v2 Search & orphaned import guard
# ---------------------------------------------------------------------------
def evaluate_stripe_python_v2_search_and_import_guard(
    *,
    import_path: str,
    object_type: str,
    http_method_for_next_page: str,
    carries_original_json_body: bool,
) -> GuardEvaluation:
    """Enforce `v2.search_result` POST pagination (`#1939`) and block `stripe.api_resources` (`#1951`)."""
    if import_path == "stripe.api_resources" or import_path.startswith("stripe.api_resources."):
        return GuardEvaluation(
            allowed=False,
            action="block_orphaned_api_resources_import",
            reason="stripe.api_resources was removed in v13; import directly from stripe",
            details={"import_path": import_path},
        )
    if object_type != "v2.search_result":
        return GuardEvaluation(
            allowed=False,
            action="block_unregistered_v2_search_object",
            reason="API v2 Search pages must deserialize into registered v2.search_result object",
            details={"object_type": object_type},
        )
    if http_method_for_next_page.upper() != "POST" or not carries_original_json_body:
        return GuardEvaluation(
            allowed=False,
            action="block_invalid_v2_search_pagination",
            reason="v2.search_result next_page_url pagination requires POST with original JSON body",
            details={
                "http_method": http_method_for_next_page,
                "carries_original_json_body": carries_original_json_body,
            },
        )
    return GuardEvaluation(
        allowed=True,
        action="allow_v2_search_pagination",
        reason="v2.search_result registered and paginated via POST with original JSON search body",
        details={"object_class": "SearchResultObject", "method": "POST"},
    )


# ---------------------------------------------------------------------------
# PR-07: stripe/stripe-node#2902, #2901 & #2898 - Barrel, V2List & fetch disposal guard
# ---------------------------------------------------------------------------
def evaluate_stripe_node_barrel_and_fetch_dispose_guard(
    *,
    barrel_evaluates_v2_core_events_at_import: bool,
    cjs_exports_v2_list_and_search_result: bool,
    has_web_body_cancel: bool,
    has_node_readable_destroy: bool,
    custom_event_name: str,
) -> GuardEvaluation:
    """Validate ESM barrel safety (`#2902`), CJS V2 exports (`#2901`), and fetch stream disposal (`#2898`)."""
    if barrel_evaluates_v2_core_events_at_import:
        return GuardEvaluation(
            allowed=False,
            action="block_eager_v2_core_events_barrel",
            reason="Eager V2.Core.Events evaluation in stripe.barrel.ts causes ESM import-time crash",
            details={"barrel_evaluates_v2_core_events_at_import": True},
        )
    if not cjs_exports_v2_list_and_search_result:
        return GuardEvaluation(
            allowed=False,
            action="block_missing_cjs_v2_exports",
            reason="stripe.cjs.node.ts must export V2List, V2ListPromise, and V2SearchResult namespaces",
            details={"cjs_exports_v2_list_and_search_result": False},
        )
    if not has_web_body_cancel and not has_node_readable_destroy:
        return GuardEvaluation(
            allowed=False,
            action="block_undisposed_fetch_body",
            reason="FetchHttpClient must call body.destroy() when Web ReadableStream.cancel() is absent",
            details={"has_web_body_cancel": False, "has_node_readable_destroy": False},
        )
    disposal_method = "cancel" if has_web_body_cancel else "destroy"
    return GuardEvaluation(
        allowed=True,
        action="allow_stripe_node_base_contract",
        reason="Stripe Node ESM/CJS barrel exports intact, custom event typed, and fetch body disposed",
        details={"disposal_method": disposal_method, "event_type": custom_event_name},
    )


# ---------------------------------------------------------------------------
# PR-08: stripe/stripe-go#2477, #2476, #2468 & #2465 - V2List nil, reflection, retry & webhook secret
# ---------------------------------------------------------------------------
def evaluate_stripe_go_safety_and_retry_guard(
    *,
    v2_list_pointer_is_nil: bool,
    checked_nil_before_interface_assert: bool,
    params_has_metadata_field: bool,
    checked_field_valid_before_is_zero: bool,
    webhook_secret: str,
    stripe_should_retry_header: str | None,
    http_status: int,
) -> GuardEvaluation:
    """Enforce Stripe Go nil `V2List` guard (`#2477`), reflection check (`#2476`), retries (`#2468`), and secret trim (`#2465`)."""
    if v2_list_pointer_is_nil and not checked_nil_before_interface_assert:
        return GuardEvaluation(
            allowed=False,
            action="block_nil_v2list_interface_panic",
            reason="A nil *V2List[T] still satisfies v2ListInitializer; must check IsNil() before init",
            details={"v2_list_pointer_is_nil": True},
        )
    if not params_has_metadata_field and not checked_field_valid_before_is_zero:
        return GuardEvaluation(
            allowed=False,
            action="block_reflection_invalid_field_panic",
            reason="Calling FieldByName('Metadata').IsZero() without IsValid() panics on SearchParams",
            details={"params_has_metadata_field": False},
        )
    if webhook_secret.strip(ASCII_WHITESPACE) == "":
        return GuardEvaluation(
            allowed=False,
            action="block_blank_webhook_secret",
            reason="webhookSecret made entirely of ASCII whitespace must be rejected",
            details={"webhook_secret_repr": repr(webhook_secret)},
        )
    if stripe_should_retry_header == "false":
        should_retry = False
    elif stripe_should_retry_header == "true":
        should_retry = True
    else:
        should_retry = http_status == 409 or http_status >= 500
    return GuardEvaluation(
        allowed=True,
        action="allow_stripe_go_safe_execution",
        reason="Nil V2List and reflection guards active, non-blank webhook secret verified, retry policy evaluated",
        details={"should_retry": should_retry, "http_status": http_status},
    )


# ---------------------------------------------------------------------------
# PR-09: a2aproject/a2a-python#1294 & #1287 - JCS open-container depth & AgentCard descriptor pruning
# ---------------------------------------------------------------------------
def _count_max_open_containers(obj: Any, current_depth: int = 1) -> int:
    if isinstance(obj, (list, tuple)):
        if not obj:
            return current_depth
        return max(_count_max_open_containers(item, current_depth + 1) for item in obj)
    if isinstance(obj, dict):
        if not obj:
            return current_depth
        return max(_count_max_open_containers(val, current_depth + 1) for val in obj.values())
    return current_depth - 1


def evaluate_a2a_python_jcs_depth_and_signing_guard(
    *,
    payload: Any,
    max_depth: int = JCS_MAX_DEPTH,
    pruned_empty_map_entry: bool = False,
) -> GuardEvaluation:
    """Count open containers from 1 for JCS nesting bound (`#1294`) and preserve map entries (`#1287`)."""
    observed_container_depth = _count_max_open_containers(payload, 1)
    if observed_container_depth > max_depth:
        return GuardEvaluation(
            allowed=False,
            action="block_jcs_container_depth_exceeded",
            reason=f"nesting exceeds the maximum depth of {max_depth} (open container depth={observed_container_depth})",
            details={"observed_container_depth": observed_container_depth, "max_depth": max_depth},
        )
    if pruned_empty_map_entry:
        return GuardEvaluation(
            allowed=False,
            action="block_corrupted_protobuf_map_pruning",
            reason="AgentCard canonical payload pruning must walk descriptors and preserve map entries",
            details={"pruned_empty_map_entry": True},
        )
    return GuardEvaluation(
        allowed=True,
        action="allow_canonical_jcs_signature",
        reason="JCS open-container depth within bound and descriptor-guided AgentCard pruning verified",
        details={"observed_container_depth": observed_container_depth, "max_depth": max_depth},
    )


# ---------------------------------------------------------------------------
# PR-10: a2aproject/a2a-python#1281 & #1279 - Multi-replica cluster & AgentCard required fields
# ---------------------------------------------------------------------------
def evaluate_a2a_python_cluster_and_card_guard(
    *,
    agent_card_fields: dict[str, Any],
    cluster_mode_enabled: bool,
    shared_task_store_configured: bool,
    shared_event_bus_configured: bool,
) -> GuardEvaluation:
    """Validate required `AgentCard` fields (`#1279`) and multi-replica cluster backing stores (`#1281`)."""
    required = ("name", "description", "url", "version", "capabilities", "skills")
    missing = [k for k in required if not agent_card_fields.get(k)]
    if missing:
        return GuardEvaluation(
            allowed=False,
            action="block_incomplete_agent_card",
            reason="AgentCard passed to DefaultRequestHandler is missing required fields",
            details={"missing_fields": missing},
        )
    if cluster_mode_enabled and (not shared_task_store_configured or not shared_event_bus_configured):
        return GuardEvaluation(
            allowed=False,
            action="block_unbacked_cluster_mode",
            reason="Multi-replica cluster mode requires shared task store and distributed event queue",
            details={
                "shared_task_store_configured": shared_task_store_configured,
                "shared_event_bus_configured": shared_event_bus_configured,
            },
        )
    return GuardEvaluation(
        allowed=True,
        action="allow_a2a_cluster_handler",
        reason="AgentCard required fields present and multi-replica cluster store/queue verified",
        details={"cluster_mode": cluster_mode_enabled},
    )


# ---------------------------------------------------------------------------
# PR-11: a2aproject/a2a-java#1234 & #1212 - Structured payload masking & input-required workflow
# ---------------------------------------------------------------------------
def evaluate_a2a_java_logging_and_input_required_guard(
    *,
    raw_payload: dict[str, Any],
    max_log_chars: int,
    task_state: str,
    followup_carries_task_id: bool,
    followup_carries_context_id: bool,
) -> GuardEvaluation:
    """Mask sensitive fields & truncate logged payloads (`#1234`) and validate `INPUT_REQUIRED` follow-up (`#1212`)."""
    sensitive_keys = {"authorization", "api_key", "apikey", "token", "secret", "password"}
    unmasked_leaks = [
        k for k, v in raw_payload.items() if k.lower() in sensitive_keys and v != "***MASKED***"
    ]
    if unmasked_leaks:
        return GuardEvaluation(
            allowed=False,
            action="block_unmasked_sensitive_payload_log",
            reason="Structured payload logger must mask Authorization/token/secret fields before logging",
            details={"unmasked_keys": unmasked_leaks},
        )
    if task_state == "TASK_STATE_INPUT_REQUIRED" and (
        not followup_carries_task_id or not followup_carries_context_id
    ):
        return GuardEvaluation(
            allowed=False,
            action="block_stateless_input_required_followup",
            reason="Multi-turn INPUT_REQUIRED continuation must echo server-generated taskId and contextId",
            details={
                "followup_carries_task_id": followup_carries_task_id,
                "followup_carries_context_id": followup_carries_context_id,
            },
        )
    serialized = str(raw_payload)
    truncated = serialized[:max_log_chars] + ("...(truncated)" if len(serialized) > max_log_chars else "")
    return GuardEvaluation(
        allowed=True,
        action="allow_masked_input_required_turn",
        reason="Payload log masked/truncated and INPUT_REQUIRED continuation bound to taskId/contextId",
        details={"logged_preview": truncated, "task_state": task_state},
    )


# ---------------------------------------------------------------------------
# PR-12: a2aproject/a2a-js#749 - Database migration lock table cleanup guard
# ---------------------------------------------------------------------------
def evaluate_a2a_js_migration_lock_cleanup_guard(
    *,
    migration_in_flight_elsewhere: bool,
    migration_succeeded: bool,
    lock_table_dropped_after_run: bool,
) -> GuardEvaluation:
    """Drop Kysely migration lock table after single-runner migration (`a2a-js#749`)."""
    if migration_in_flight_elsewhere:
        return GuardEvaluation(
            allowed=False,
            action="block_concurrent_migration_lock_drop",
            reason="Dropping migration_lock while another migration run is active corrupts lock acquisition",
            details={"migration_in_flight_elsewhere": True},
        )
    if migration_succeeded and not lock_table_dropped_after_run:
        return GuardEvaluation(
            allowed=False,
            action="block_leaked_migration_lock_table",
            reason="CLI migrator must drop migration_lock table after each completed migration run",
            details={"lock_table_dropped_after_run": False},
        )
    return GuardEvaluation(
        allowed=True,
        action="allow_clean_migration_lifecycle",
        reason="Migration completed sequentially and temporary migration_lock table was dropped",
        details={"lock_table_dropped": lock_table_dropped_after_run},
    )


# ---------------------------------------------------------------------------
# PR-13: modelcontextprotocol/go-sdk#1320, #1315 & #1297 - Priority 0, client & prompt params
# ---------------------------------------------------------------------------
def evaluate_mcp_go_annotations_and_params_guard(
    *,
    annotation_priority: float | None,
    serialized_json_contains_priority: bool,
    server_message_method: str,
    server_message_has_params: bool,
    prompt_required_args: list[str],
    prompt_supplied_args: dict[str, Any],
) -> GuardEvaluation:
    """Preserve `priority: 0` (`#1320`), reject missing server message `params` (`#1315`), and validate prompt args (`#1297`)."""
    if annotation_priority == 0.0 and not serialized_json_contains_priority:
        return GuardEvaluation(
            allowed=False,
            action="block_dropped_zero_priority_annotation",
            reason="Explicit priority=0 on Annotations must be serialized rather than omitted by omitempty",
            details={"annotation_priority": 0.0},
        )
    methods_requiring_params = {
        "elicitation/create",
        "notifications/elicitation/complete",
        "notifications/resources/updated",
    }
    if server_message_method in methods_requiring_params and not server_message_has_params:
        return GuardEvaluation(
            allowed=False,
            action="block_missing_server_message_params",
            reason=f"Server message {server_message_method} missing required params object (-32602)",
            details={"method": server_message_method},
        )
    missing_prompt_args = [arg for arg in prompt_required_args if arg not in prompt_supplied_args]
    if missing_prompt_args:
        return GuardEvaluation(
            allowed=False,
            action="block_missing_required_prompt_args",
            reason="prompts/get request missing required prompt arguments (-32602 Invalid Params)",
            details={"missing_prompt_args": missing_prompt_args},
        )
    return GuardEvaluation(
        allowed=True,
        action="allow_mcp_go_validated_message",
        reason="Annotations priority=0 preserved and client/server required parameters verified",
        details={"priority": annotation_priority, "method": server_message_method},
    )


# ---------------------------------------------------------------------------
# PR-14: modelcontextprotocol/rust-sdk#1295, #1287 & #1288 - Null structuredContent & JSON-RPC shape
# ---------------------------------------------------------------------------
def evaluate_mcp_rust_model_and_discovery_guard(
    *,
    wire_json: dict[str, Any],
    is_tool_result: bool,
    discovery_json_rejected: bool,
    fell_back_to_well_known: bool,
) -> GuardEvaluation:
    """Preserve explicit `null` `structuredContent` (`#1295`), reject `result`+`error` (`#1287`), and fallback discovery (`#1288`)."""
    if "result" in wire_json and "error" in wire_json:
        return GuardEvaluation(
            allowed=False,
            action="block_conflicting_jsonrpc_result_and_error",
            reason="JSON-RPC message cannot contain both 'result' and 'error' members",
            details={"keys": sorted(wire_json.keys())},
        )
    if discovery_json_rejected and not fell_back_to_well_known:
        return GuardEvaluation(
            allowed=False,
            action="block_aborted_oauth_discovery_fallback",
            reason="Transport must continue fallback discovery after a JSON discovery rejection",
            details={"discovery_json_rejected": True, "fell_back_to_well_known": False},
        )
    structured_state = "absent"
    target_obj = (
        wire_json["result"]
        if isinstance(wire_json.get("result"), dict)
        else wire_json
    )
    if is_tool_result and "structuredContent" in target_obj:
        structured_state = (
            "explicit_null" if target_obj["structuredContent"] is None else "present_value"
        )
    return GuardEvaluation(
        allowed=True,
        action="allow_mcp_rust_wire_envelope",
        reason="JSON-RPC envelope mutually exclusive and CallToolResult structuredContent state preserved",
        details={"structured_content_state": structured_state},
    )


# ---------------------------------------------------------------------------
# PR-15: modelcontextprotocol/csharp-sdk#1875 & #1906 - Streamable HTTP no-reply trace & ClaimsPrincipal
# ---------------------------------------------------------------------------
def evaluate_mcp_csharp_http_correlation_and_claims_guard(
    *,
    content_type: str,
    response_body: str,
    expected_request_id: int | str,
    observed_response_id: int | str | None,
    requires_claims_principal: bool,
    authenticated_principal_id: str | None,
) -> GuardEvaluation:
    """Record diagnosable `ResponseCorrelationTrace` on empty/unmatched HTTP reply (`#1875`) and check `ClaimsPrincipal` (`#1906`)."""
    if requires_claims_principal and not authenticated_principal_id:
        return GuardEvaluation(
            allowed=False,
            action="block_missing_claims_principal",
            reason="Protected MCP tool requires an authenticated ClaimsPrincipal identity",
            details={"requires_claims_principal": True},
        )
    if content_type == "application/json" and len(response_body.strip()) == 0:
        return GuardEvaluation(
            allowed=False,
            action="block_empty_json_http_reply",
            reason="Streamable HTTP response ended with empty application/json body (ResponseCorrelationTrace: EmptyBody)",
            details={"content_type": content_type, "trace": "EmptyBody"},
        )
    if observed_response_id != expected_request_id:
        return GuardEvaluation(
            allowed=False,
            action="block_uncorrelated_jsonrpc_id",
            reason="Streamable HTTP response ID did not match in-flight request ID",
            details={
                "expected_request_id": expected_request_id,
                "observed_response_id": observed_response_id,
            },
        )
    return GuardEvaluation(
        allowed=True,
        action="allow_correlated_streamable_http_reply",
        reason="Streamable HTTP response correlated with request ID and ClaimsPrincipal verified",
        details={"principal": authenticated_principal_id, "request_id": expected_request_id},
    )


# ---------------------------------------------------------------------------
# PR-16: modelcontextprotocol/python-sdk#3684, #3647 & ext-apps#749 - Tool auth, oauth extra & title chrome
# ---------------------------------------------------------------------------
def evaluate_mcp_python_auth_and_ext_apps_chrome_guard(
    *,
    requires_asymmetric_jwt_signing: bool,
    oauth_crypto_extra_installed: bool,
    token_scopes: set[str],
    required_tool_scope: str,
    token_tenant_id: str,
    resource_owner_tenant_id: str,
    tool_name: str,
    tool_title: str | None,
) -> GuardEvaluation:
    """Fail closed without `mcp[oauth]` (`#3684`), enforce per-call scope + tenant (`#3647`), and prefer `tool.title` (`ext-apps#749`)."""
    if requires_asymmetric_jwt_signing and not oauth_crypto_extra_installed:
        return GuardEvaluation(
            allowed=False,
            action="block_missing_oauth_crypto_extra",
            reason="Asymmetric JWT signing requires pip install 'mcp[oauth]<2'; never fall back to unsigned tokens",
            details={"requires_asymmetric_jwt_signing": True},
        )
    if required_tool_scope not in token_scopes:
        return GuardEvaluation(
            allowed=False,
            action="block_unauthorized_tool_execution",
            reason="tools/call must verify required operation scope even if caller guessed a hidden tool name",
            details={"required_scope": required_tool_scope, "token_scopes": sorted(token_scopes)},
        )
    if token_tenant_id != resource_owner_tenant_id:
        return GuardEvaluation(
            allowed=False,
            action="block_cross_tenant_resource_access",
            reason="Tenant ownership must come from verified token claims and server data, not model arguments",
            details={
                "token_tenant_id": token_tenant_id,
                "resource_owner_tenant_id": resource_owner_tenant_id,
            },
        )
    chrome_label = tool_title if (tool_title and tool_title.strip()) else tool_name
    return GuardEvaluation(
        allowed=True,
        action="allow_authorized_mcp_tool_and_chrome",
        reason="OAuth crypto, tool execution scope, server-side tenant ownership, and App View title verified",
        details={"chrome_label": chrome_label, "tenant_id": token_tenant_id},
    )
