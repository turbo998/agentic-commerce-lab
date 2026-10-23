"""Stage 218 deterministic guardrails covering 16 primary-source PRs (`PR-01..PR-16`)
across UCP (`#880`/`#803`/`#847`), x402 (`#3909`/`#3709`/`#3833`/`#3713`/`#3872`/`#3751`),
MCP Python SDK (`#3675`/`#3558`/`#3626`/`#3624`/`#3623`/`#3584`/`#3595`/`#3609`/`#3593`/`#3568`),
MCP TypeScript SDK (`#3076`/`#3074`/`#3073`/`#3069`/`#3066`/`#3065`/`#3062`/`#3059`/`#3057`/`#3087`/`#3050`),
and Sierra tau2-bench / tau3-bench (`#527`/`#536`/`#537`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class GuardVerdict:
    passed: bool
    scenario_id: str
    control_id: str
    reason_code: str
    action: str
    details: dict[str, Any]


SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
REGISTERED_IMAGE_MIMES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
REGISTERED_AUDIO_MIMES = {"audio/mpeg", "audio/mp4", "audio/wav", "audio/ogg", "audio/webm"}
WORLD_CHAIN_USDC = "0x79a02482a880bce3f13e09da970dc34db4cd24d1"


# ---------------------------------------------------------------------------
# PR-01: Universal-Commerce-Protocol/ucp#880, #803, & #847
# ---------------------------------------------------------------------------
def audit_ucp_ci_workflow_sha_pinning_fast_uri_and_blame_ignore(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce UCP Prettier schema formatting + `.git-blame-ignore-revs` (`ucp#880`),
    `fast-uri >= 3.1.6` override (`ucp#803`), and GitHub Actions 40-char commit
    SHA pinning + `persist-credentials: false` + `contents: read` (`ucp#847`).
    """
    if not bool(payload.get("prettier_schema_check_passed", False)) or not bool(
        payload.get("git_blame_ignore_revs_present", False)
    ):
        return GuardVerdict(
            passed=False,
            scenario_id="PR-01",
            control_id="ucp_ci_sha_pinning_fast_uri_and_blame_gate",
            reason_code="UCP_SCHEMA_FORMAT_OR_BLAME_IGNORE_MISSING",
            action="Send to a human",
            details={},
        )

    fast_uri_tuple = tuple(payload.get("fast_uri_version", (0, 0, 0)))
    if fast_uri_tuple < (3, 1, 6):
        return GuardVerdict(
            passed=False,
            scenario_id="PR-01",
            control_id="ucp_ci_sha_pinning_fast_uri_and_blame_gate",
            reason_code="UCP_FAST_URI_OVERRIDE_VULNERABLE",
            action="Send to a human",
            details={"fast_uri_version": list(fast_uri_tuple)},
        )

    action_refs: Sequence[str] = payload.get("workflow_action_refs", [])
    if not action_refs or any(not SHA40_RE.match(str(ref).split("@")[-1]) for ref in action_refs):
        return GuardVerdict(
            passed=False,
            scenario_id="PR-01",
            control_id="ucp_ci_sha_pinning_fast_uri_and_blame_gate",
            reason_code="UCP_WORKFLOW_MUTABLE_ACTION_TAG_DETECTED",
            action="Send to a human",
            details={"workflow_action_refs": list(action_refs)},
        )

    if bool(payload.get("readonly_checkout_persists_credentials", False)) or str(
        payload.get("workflow_token_permissions", "")
    ) != "contents:read":
        return GuardVerdict(
            passed=False,
            scenario_id="PR-01",
            control_id="ucp_ci_sha_pinning_fast_uri_and_blame_gate",
            reason_code="UCP_WORKFLOW_EXCESSIVE_TOKEN_PERMISSIONS_OR_CREDENTIAL_RETENTION",
            action="Send to a human",
            details={"workflow_token_permissions": payload.get("workflow_token_permissions")},
        )

    return GuardVerdict(
        passed=True,
        scenario_id="PR-01",
        control_id="ucp_ci_sha_pinning_fast_uri_and_blame_gate",
        reason_code="UCP_CI_SHA_PINNING_FAST_URI_AND_BLAME_VERIFIED",
        action="Act automatically",
        details={"actions_verified": len(action_refs)},
    )


# ---------------------------------------------------------------------------
# PR-02: x402-foundation/x402#3909 & #3709
# ---------------------------------------------------------------------------
def audit_x402_buyer_presign_origin_payee_pin_and_spend_killswitch(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce x402 buyer pre-sign policy (`Agent Safe` `#3909` & `Rein` `#3709`):
    per-origin payee pinning, per-call cap, session budget, max authorization
    window, and non-custodial kill switch.
    """
    if bool(payload.get("kill_switch_active", False)):
        return GuardVerdict(
            passed=False,
            scenario_id="PR-02",
            control_id="x402_buyer_presign_origin_pin_and_killswitch_gate",
            reason_code="X402_BUYER_KILL_SWITCH_ACTIVE",
            action="Send to a human",
            details={},
        )

    pinned_payee = str(payload.get("origin_pinned_payee", "")).lower()
    challenge_pay_to = str(payload.get("challenge_pay_to", "")).lower()
    if not pinned_payee or pinned_payee != challenge_pay_to:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-02",
            control_id="x402_buyer_presign_origin_pin_and_killswitch_gate",
            reason_code="X402_BUYER_ORIGIN_PAYEE_PIN_MISMATCH",
            action="Send to a human",
            details={"origin_pinned_payee": pinned_payee, "challenge_pay_to": challenge_pay_to},
        )

    call_amount = int(payload.get("call_amount_minor", 0))
    max_per_call = int(payload.get("max_per_call_minor", 0))
    session_spent = int(payload.get("session_spent_minor", 0))
    session_budget = int(payload.get("session_budget_minor", 0))
    auth_window_s = int(payload.get("auth_window_seconds", 0))
    max_auth_window_s = int(payload.get("max_auth_window_seconds", 0))

    if (
        call_amount <= 0
        or call_amount > max_per_call
        or (session_spent + call_amount) > session_budget
        or auth_window_s <= 0
        or auth_window_s > max_auth_window_s
    ):
        return GuardVerdict(
            passed=False,
            scenario_id="PR-02",
            control_id="x402_buyer_presign_origin_pin_and_killswitch_gate",
            reason_code="X402_BUYER_SPEND_CAP_OR_AUTH_WINDOW_EXCEEDED",
            action="Send to a human",
            details={
                "call_amount_minor": call_amount,
                "max_per_call_minor": max_per_call,
                "projected_session_spend": session_spent + call_amount,
                "session_budget_minor": session_budget,
                "auth_window_seconds": auth_window_s,
            },
        )

    return GuardVerdict(
        passed=True,
        scenario_id="PR-02",
        control_id="x402_buyer_presign_origin_pin_and_killswitch_gate",
        reason_code="X402_BUYER_PRESIGN_POLICY_VERIFIED",
        action="Act automatically",
        details={"call_amount_minor": call_amount, "remaining_budget_minor": session_budget - session_spent - call_amount},
    )


# ---------------------------------------------------------------------------
# PR-03: x402-foundation/x402#3833 & #3713
# ---------------------------------------------------------------------------
def audit_x402_world_chain_usdc_and_inam_payee_receipt_gate(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce World Chain (`eip155:480`) canonical USDC default asset (`x402#3833`)
    and INAM Protocol `withInamX402Gate` linked-address == `payTo` + receipt
    history policy gate (`x402#3713`).
    """
    network = str(payload.get("network", ""))
    asset_address = str(payload.get("asset_address", "")).lower()
    decimals = int(payload.get("decimals", 0))
    eip712_name = str(payload.get("eip712_name", ""))
    eip712_version = str(payload.get("eip712_version", ""))

    if (
        network != "eip155:480"
        or asset_address != WORLD_CHAIN_USDC
        or decimals != 6
        or eip712_name != "USDC"
        or eip712_version != "2"
    ):
        return GuardVerdict(
            passed=False,
            scenario_id="PR-03",
            control_id="x402_world_chain_usdc_and_inam_gate",
            reason_code="X402_WORLD_CHAIN_DEFAULT_USDC_SPEC_MISMATCH",
            action="Send to a human",
            details={"network": network, "asset_address": asset_address, "decimals": decimals},
        )

    inam = payload.get("inam_extension", {})
    pay_to = str(payload.get("pay_to", "")).lower()
    linked_addr = str(inam.get("linked_address", "")).lower()
    receipt_score = int(inam.get("receipt_history_score", 0))
    min_score = int(inam.get("min_required_score", 80))

    if not linked_addr or linked_addr != pay_to or receipt_score < min_score:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-03",
            control_id="x402_world_chain_usdc_and_inam_gate",
            reason_code="X402_INAM_PAYEE_ADDRESS_OR_RECEIPT_HISTORY_REJECTED",
            action="Send to a human",
            details={"pay_to": pay_to, "linked_address": linked_addr, "receipt_history_score": receipt_score},
        )

    return GuardVerdict(
        passed=True,
        scenario_id="PR-03",
        control_id="x402_world_chain_usdc_and_inam_gate",
        reason_code="X402_WORLD_CHAIN_USDC_AND_INAM_GATE_VERIFIED",
        action="Act automatically",
        details={"network": network, "receipt_history_score": receipt_score},
    )


# ---------------------------------------------------------------------------
# PR-04: x402-foundation/x402#3872 & #3751
# ---------------------------------------------------------------------------
def audit_x402_multichain_ofac_sdn_screen_and_sdk_license_notice(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce multi-chain (`evm`/`solana`/`algorand`/`xrpl`) pre-sign & pre-settle
    OFAC SDN screening (`x402#3872`) and Apache-2.0 `LICENSE` + `NOTICE` shipping
    across Python, TypeScript, and Go SDKs (`x402#3751`).
    """
    chain_family = str(payload.get("chain_family", ""))
    payer_sanctioned = bool(payload.get("payer_on_ofac_sdn_list", False))
    payee_sanctioned = bool(payload.get("payee_on_ofac_sdn_list", False))
    if chain_family not in {"evm", "solana", "algorand", "xrpl"} or payer_sanctioned or payee_sanctioned:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-04",
            control_id="x402_multichain_ofac_and_sdk_license_notice_gate",
            reason_code="X402_PRESIGN_OFAC_SDN_HIT_OR_UNSUPPORTED_CHAIN",
            action="Send to a human",
            details={"chain_family": chain_family, "payer_sanctioned": payer_sanctioned, "payee_sanctioned": payee_sanctioned},
        )

    sdks = payload.get("sdk_distributions", {})
    for sdk_name in ("python", "typescript", "go"):
        files = set(sdks.get(sdk_name, []))
        if not {"LICENSE", "NOTICE"}.issubset(files):
            return GuardVerdict(
                passed=False,
                scenario_id="PR-04",
                control_id="x402_multichain_ofac_and_sdk_license_notice_gate",
                reason_code="X402_SDK_APACHE_LICENSE_OR_NOTICE_MISSING",
                action="Send to a human",
                details={"sdk": sdk_name, "files": sorted(files)},
            )

    return GuardVerdict(
        passed=True,
        scenario_id="PR-04",
        control_id="x402_multichain_ofac_and_sdk_license_notice_gate",
        reason_code="X402_MULTICHAIN_OFAC_AND_SDK_NOTICE_VERIFIED",
        action="Act automatically",
        details={"chain_family": chain_family},
    )


# ---------------------------------------------------------------------------
# PR-05: modelcontextprotocol/python-sdk#3675 & #3558
# ---------------------------------------------------------------------------
def audit_mcp_python_case_insensitive_content_type_and_invalid_request_code(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce case-insensitive `application/json` `Content-Type` acceptance
    (`python-sdk#3675`) and `-32600 INVALID_REQUEST` (not `-32602 INVALID_PARAMS`)
    on non-Request JSON bodies (`python-sdk#3558`).
    """
    raw_ct = str(payload.get("content_type_header", ""))
    media_type = raw_ct.split(";")[0].strip().lower()
    accepted_by_transport = bool(payload.get("transport_accepted_content_type", False))
    expected_accept = media_type == "application/json"
    if accepted_by_transport != expected_accept:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-05",
            control_id="mcp_python_content_type_and_invalid_request_gate",
            reason_code="MCP_CONTENT_TYPE_CASE_NORMALIZATION_MISMATCH",
            action="Send to a human",
            details={"content_type_header": raw_ct, "accepted": accepted_by_transport},
        )

    is_jsonrpc_request = bool(payload.get("body_is_valid_jsonrpc_request", True))
    error_code = int(payload.get("non_request_jsonrpc_error_code", 0))
    if not is_jsonrpc_request and error_code != -32600:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-05",
            control_id="mcp_python_content_type_and_invalid_request_gate",
            reason_code="MCP_NON_REQUEST_BODY_MISCLASSIFIED_AS_INVALID_PARAMS",
            action="Send to a human",
            details={"returned_error_code": error_code},
        )

    return GuardVerdict(
        passed=True,
        scenario_id="PR-05",
        control_id="mcp_python_content_type_and_invalid_request_gate",
        reason_code="MCP_CONTENT_TYPE_AND_INVALID_REQUEST_CODE_VERIFIED",
        action="Act automatically",
        details={"normalized_media_type": media_type, "error_code": error_code},
    )


# ---------------------------------------------------------------------------
# PR-06: modelcontextprotocol/python-sdk#3626 & #3624
# ---------------------------------------------------------------------------
def audit_mcp_python_subscriptions_listen_optout_and_generic_context_preservation(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce `MCPServer` opt-out of `subscriptions/listen` on static catalogs
    (`python-sdk#3626`) and live `Context[AppState]` preservation on generic
    prompt/template annotations (`python-sdk#3624`).
    """
    catalog_is_static = bool(payload.get("catalog_is_static", False))
    opt_out_subscriptions_listen = bool(payload.get("opt_out_subscriptions_listen", False))
    advertises_listen_stream = bool(payload.get("advertises_subscriptions_listen", False))
    if catalog_is_static and opt_out_subscriptions_listen and advertises_listen_stream:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-06",
            control_id="mcp_python_listen_optout_and_generic_context_gate",
            reason_code="MCP_STATIC_SERVER_FORCED_SUBSCRIPTIONS_LISTEN_STREAM",
            action="Send to a human",
            details={"advertises_subscriptions_listen": advertises_listen_stream},
        )

    generic_ctx_has_request_context = bool(payload.get("generic_context_has_live_request_context", False))
    if not generic_ctx_has_request_context:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-06",
            control_id="mcp_python_listen_optout_and_generic_context_gate",
            reason_code="MCP_GENERIC_CONTEXT_REBUILT_EMPTY_BY_PYDANTIC",
            action="Send to a human",
            details={},
        )

    return GuardVerdict(
        passed=True,
        scenario_id="PR-06",
        control_id="mcp_python_listen_optout_and_generic_context_gate",
        reason_code="MCP_LISTEN_OPTOUT_AND_GENERIC_CONTEXT_VERIFIED",
        action="Act automatically",
        details={"advertises_subscriptions_listen": advertises_listen_stream},
    )


# ---------------------------------------------------------------------------
# PR-07: modelcontextprotocol/python-sdk#3623 & #3584
# ---------------------------------------------------------------------------
def audit_mcp_python_progress_callback_containment_and_post_transport_error_isolation(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce `DirectDispatcher` containment of raising `on_progress` callbacks
    (`python-sdk#3623`) and post-connect `StreamableHTTPTransport` single-POST
    `TransportError` isolation (`python-sdk#3584`).
    """
    progress_callback_raised = bool(payload.get("progress_callback_raised", False))
    tool_execution_aborted = bool(payload.get("tool_execution_aborted_by_progress_callback", False))
    if progress_callback_raised and tool_execution_aborted:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-07",
            control_id="mcp_python_progress_and_post_transport_isolation_gate",
            reason_code="MCP_DIRECT_DISPATCHER_PROGRESS_CALLBACK_CRASHED_TOOL",
            action="Send to a human",
            details={},
        )

    post_transport_error = bool(payload.get("single_post_transport_error_occurred", False))
    session_kept_alive = bool(payload.get("session_kept_alive_after_post_error", False))
    isolated_error_code = str(payload.get("single_post_error_code", ""))
    if post_transport_error and (not session_kept_alive or isolated_error_code != "CONNECTION_CLOSED"):
        return GuardVerdict(
            passed=False,
            scenario_id="PR-07",
            control_id="mcp_python_progress_and_post_transport_isolation_gate",
            reason_code="MCP_STREAMABLE_HTTP_POST_ERROR_CRASHED_SESSION",
            action="Send to a human",
            details={"session_kept_alive": session_kept_alive, "single_post_error_code": isolated_error_code},
        )

    return GuardVerdict(
        passed=True,
        scenario_id="PR-07",
        control_id="mcp_python_progress_and_post_transport_isolation_gate",
        reason_code="MCP_PROGRESS_AND_POST_TRANSPORT_ISOLATION_VERIFIED",
        action="Act automatically",
        details={"session_kept_alive": session_kept_alive},
    )


# ---------------------------------------------------------------------------
# PR-08: modelcontextprotocol/python-sdk#3595 & #3609
# ---------------------------------------------------------------------------
def audit_mcp_python_stdio_exit_on_open_stdin_and_safe_join_junction_escape(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce `stdio_server` clean exit while peer holds `stdin` open (`python-sdk#3595`)
    and `safe_join` rejection of symlink/NTFS-junction path escapes (`python-sdk#3609`).
    """
    peer_holds_stdin_open = bool(payload.get("peer_holds_stdin_open", True))
    server_exited_cleanly = bool(payload.get("stdio_server_exited_without_hanging", False))
    if peer_holds_stdin_open and not server_exited_cleanly:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-08",
            control_id="mcp_python_stdio_exit_and_safe_join_junction_gate",
            reason_code="MCP_STDIO_SERVER_PARKED_ON_UNCANCELLABLE_STDIN_READ",
            action="Send to a human",
            details={},
        )

    if not bool(payload.get("safe_join_rejected_symlink_or_junction_escape", False)):
        return GuardVerdict(
            passed=False,
            scenario_id="PR-08",
            control_id="mcp_python_stdio_exit_and_safe_join_junction_gate",
            reason_code="MCP_SAFE_JOIN_SYMLINK_OR_JUNCTION_ESCAPE_ALLOWED",
            action="Send to a human",
            details={},
        )

    return GuardVerdict(
        passed=True,
        scenario_id="PR-08",
        control_id="mcp_python_stdio_exit_and_safe_join_junction_gate",
        reason_code="MCP_STDIO_EXIT_AND_SAFE_JOIN_JUNCTION_VERIFIED",
        action="Act automatically",
        details={"stdio_server_exited": server_exited_cleanly},
    )


# ---------------------------------------------------------------------------
# PR-09: modelcontextprotocol/python-sdk#3593 & #3568
# ---------------------------------------------------------------------------
def audit_mcp_python_media_mime_normalization_and_comma_scope_union(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce `Image` / `Audio` registered IANA MIME normalization (`python-sdk#3593`)
    and comma/space OAuth `parse_scopes` deduplication (`python-sdk#3568`).
    """
    image_mime = str(payload.get("image_mime_type", ""))
    audio_mime = str(payload.get("audio_mime_type", ""))
    if image_mime not in REGISTERED_IMAGE_MIMES or audio_mime not in REGISTERED_AUDIO_MIMES:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-09",
            control_id="mcp_python_media_mime_and_comma_scope_gate",
            reason_code="MCP_UNREGISTERED_IMAGE_OR_AUDIO_MIME_TYPE",
            action="Send to a human",
            details={"image_mime_type": image_mime, "audio_mime_type": audio_mime},
        )

    raw_scopes = str(payload.get("raw_scope_header", ""))
    parsed_Tokens = [tok for tok in re.split(r"[\s,]+", raw_scopes.strip()) if tok]
    deduped_expected = sorted(set(parsed_Tokens))
    actual_union = sorted(payload.get("union_scopes_result", []))
    if actual_union != deduped_expected or len( payload.get("union_scopes_result", []) ) != len(deduped_expected):
        return GuardVerdict(
            passed=False,
            scenario_id="PR-09",
            control_id="mcp_python_media_mime_and_comma_scope_gate",
            reason_code="MCP_OAUTH_COMMA_SEPARATED_SCOPES_NOT_DEDUPLICATED",
            action="Send to a human",
            details={"expected": deduped_expected, "actual": payload.get("union_scopes_result", [])},
        )

    return GuardVerdict(
        passed=True,
        scenario_id="PR-09",
        control_id="mcp_python_media_mime_and_comma_scope_gate",
        reason_code="MCP_MEDIA_MIME_AND_COMMA_SCOPE_UNION_VERIFIED",
        action="Act automatically",
        details={"image_mime_type": image_mime, "audio_mime_type": audio_mime, "scopes": deduped_expected},
    )


# ---------------------------------------------------------------------------
# PR-10: modelcontextprotocol/typescript-sdk#3076 & #3074
# ---------------------------------------------------------------------------
def audit_mcp_ts_preserve_list_changed_false_and_literal_resource_uri_lookup(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce preservation of user-configured `tools.listChanged: false` in `McpServer`
    (`typescript-sdk#3076`) and static resource lookup by exact registered literal
    URI (`typescript-sdk#3074`).
    """
    configured_list_changed = bool(payload.get("configured_tools_list_changed", False))
    effective_list_changed = bool(payload.get("effective_tools_list_changed_after_register", False))
    if configured_list_changed != effective_list_changed:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-10",
            control_id="mcp_ts_list_changed_and_literal_uri_gate",
            reason_code="MCP_TS_USER_LIST_CHANGED_FALSE_OVERWRITTEN",
            action="Send to a human",
            details={"configured": configured_list_changed, "effective": effective_list_changed},
        )

    registered_uri = str(payload.get("registered_resource_uri", ""))
    lookup_key_used = str(payload.get("resource_read_lookup_key", ""))
    if not registered_uri or registered_uri != lookup_key_used:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-10",
            control_id="mcp_ts_list_changed_and_literal_uri_gate",
            reason_code="MCP_TS_RESOURCE_URI_REWRITTEN_BY_URL_SERIALIZER",
            action="Send to a human",
            details={"registered_uri": registered_uri, "lookup_key_used": lookup_key_used},
        )

    return GuardVerdict(
        passed=True,
        scenario_id="PR-10",
        control_id="mcp_ts_list_changed_and_literal_uri_gate",
        reason_code="MCP_TS_LIST_CHANGED_AND_LITERAL_URI_VERIFIED",
        action="Act automatically",
        details={"registered_uri": registered_uri},
    )


# ---------------------------------------------------------------------------
# PR-11: modelcontextprotocol/typescript-sdk#3073 & #3069
# ---------------------------------------------------------------------------
def audit_mcp_ts_stdio_single_drain_listener_and_dom_free_headers(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce bounded `StdioClientTransport` `stdin` `drain` listener count
    (`<= 1`, preventing `MaxListenersExceededWarning`, `typescript-sdk#3073`) and
    DOM-free `normalizeHeaders` signature (`typescript-sdk#3069`).
    """
    max_drain_listeners = int(payload.get("peak_stdin_drain_listeners", 0))
    listeners_after_close = int(payload.get("listeners_remaining_after_close", 0))
    references_dom_headers_init = bool(payload.get("references_dom_only_headers_init", False))

    if max_drain_listeners > 1 or listeners_after_close != 0 or references_dom_headers_init:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-11",
            control_id="mcp_ts_stdio_drain_listener_and_headers_gate",
            reason_code="MCP_TS_STDIO_DRAIN_LISTENER_LEAK_OR_DOM_TYPE_COUPLED",
            action="Send to a human",
            details={
                "peak_stdin_drain_listeners": max_drain_listeners,
                "listeners_remaining_after_close": listeners_after_close,
                "references_dom_only_headers_init": references_dom_headers_init,
            },
        )

    return GuardVerdict(
        passed=True,
        scenario_id="PR-11",
        control_id="mcp_ts_stdio_drain_listener_and_headers_gate",
        reason_code="MCP_TS_STDIO_SINGLE_DRAIN_AND_DOM_FREE_HEADERS_VERIFIED",
        action="Act automatically",
        details={"peak_stdin_drain_listeners": max_drain_listeners},
    )


# ---------------------------------------------------------------------------
# PR-12: modelcontextprotocol/typescript-sdk#3066 & #3065
# ---------------------------------------------------------------------------
def audit_mcp_ts_skills_extension_setup_contract_and_duplicate_id_guard(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce SEP-2640 Skills extension `{ id, setup(ctx) }` registration via
    `extensions: [skills]` and duplicate extension ID rejection (`typescript-sdk#3066`/`#3065`).
    """
    uses_deprecated_attach = bool(payload.get("uses_deprecated_skills_attach", False))
    extension_ids: Sequence[str] = payload.get("registered_extension_ids", [])
    has_setup_fn = bool(payload.get("skills_extension_has_setup_fn", False))

    if uses_deprecated_attach or not has_setup_fn or not extension_ids or len(extension_ids) != len(set(extension_ids)):
        return GuardVerdict(
            passed=False,
            scenario_id="PR-12",
            control_id="mcp_ts_skills_extension_setup_and_dupid_gate",
            reason_code="MCP_TS_SKILLS_LEGACY_ATTACH_OR_DUPLICATE_EXTENSION_ID",
            action="Send to a human",
            details={"registered_extension_ids": list(extension_ids), "uses_deprecated_attach": uses_deprecated_attach},
        )

    return GuardVerdict(
        passed=True,
        scenario_id="PR-12",
        control_id="mcp_ts_skills_extension_setup_and_dupid_gate",
        reason_code="MCP_TS_SKILLS_EXTENSION_SETUP_CONTRACT_VERIFIED",
        action="Act automatically",
        details={"registered_extension_ids": list(extension_ids)},
    )


# ---------------------------------------------------------------------------
# PR-13: modelcontextprotocol/typescript-sdk#3062 & #3059
# ---------------------------------------------------------------------------
def audit_mcp_ts_rfc9728_trailing_slash_metadata_and_ajv_dialect_options(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce RFC 9728 §3.1 path trailing-slash preservation on OAuth Protected
    Resource Metadata URLs (`typescript-sdk#3062`) and `AjvJsonSchemaValidator`
    custom options with preserved `$schema` dialect dispatch (`typescript-sdk#3059`).
    """
    resource_url = str(payload.get("resource_url", ""))
    metadata_url = str(payload.get("computed_protected_resource_metadata_url", ""))
    if resource_url.endswith("/resource/") and not metadata_url.endswith("/.well-known/oauth-protected-resource/resource/"):
        return GuardVerdict(
            passed=False,
            scenario_id="PR-13",
            control_id="mcp_ts_rfc9728_trailing_slash_and_ajv_dialect_gate",
            reason_code="MCP_TS_RFC9728_PATH_TRAILING_SLASH_STRIPPED",
            action="Send to a human",
            details={"resource_url": resource_url, "metadata_url": metadata_url},
        )

    if not bool(payload.get("ajv_custom_options_preserved_dialect_dispatch", False)):
        return GuardVerdict(
            passed=False,
            scenario_id="PR-13",
            control_id="mcp_ts_rfc9728_trailing_slash_and_ajv_dialect_gate",
            reason_code="MCP_TS_AJV_CUSTOM_OPTIONS_BYPASSED_DIALECT_DISPATCH",
            action="Send to a human",
            details={},
        )

    return GuardVerdict(
        passed=True,
        scenario_id="PR-13",
        control_id="mcp_ts_rfc9728_trailing_slash_and_ajv_dialect_gate",
        reason_code="MCP_TS_RFC9728_SLASH_AND_AJV_DIALECT_VERIFIED",
        action="Act automatically",
        details={"metadata_url": metadata_url},
    )


# ---------------------------------------------------------------------------
# PR-14: modelcontextprotocol/typescript-sdk#3057 & #3087
# ---------------------------------------------------------------------------
def audit_mcp_ts_event_bus_forwarded_meta_and_spec_handler_param_strip(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce `ServerEventBus` preservation of forwarded notification `_meta` &
    authoritative resource URI filtering (`typescript-sdk#3057`), plus dropping
    undeclared non-spec handler `params` members (`typescript-sdk#3087`).
    """
    if not bool(payload.get("event_bus_preserved_forwarded_meta", False)) or not bool(
        payload.get("filtered_by_authoritative_resource_uri", False)
    ):
        return GuardVerdict(
            passed=False,
            scenario_id="PR-14",
            control_id="mcp_ts_event_bus_meta_and_param_strip_gate",
            reason_code="MCP_TS_EVENT_BUS_DROPPED_META_OR_WRONG_URI",
            action="Send to a human",
            details={},
        )

    undeclared_params_retained = list(payload.get("undeclared_spec_handler_params_retained", []))
    if undeclared_params_retained:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-14",
            control_id="mcp_ts_event_bus_meta_and_param_strip_gate",
            reason_code="MCP_TS_SPEC_HANDLER_RETAINED_UNDECLARED_PARAMS",
            action="Send to a human",
            details={"undeclared_params_retained": undeclared_params_retained},
        )

    return GuardVerdict(
        passed=True,
        scenario_id="PR-14",
        control_id="mcp_ts_event_bus_meta_and_param_strip_gate",
        reason_code="MCP_TS_EVENT_BUS_META_AND_PARAM_STRIP_VERIFIED",
        action="Act automatically",
        details={"subscription_id_stamped": True},
    )


# ---------------------------------------------------------------------------
# PR-15: modelcontextprotocol/typescript-sdk#3050
# ---------------------------------------------------------------------------
def audit_mcp_ts_rfc6570_uri_template_expansion_conformance(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce RFC 6570 URI Template expansion for percent-encoding (`%25`),
    multi-variable `/` and `.` prefixes, and comma-joined non-exploded lists (`typescript-sdk#3050`).
    """
    expansions: Mapping[str, str] = payload.get("expansions", {})
    expected = {
        "{x,half,y}": "1024,50%25,768",
        "{/who,dub}": "/fred/me%2Ftoo",
        "{.who,who}": ".fred.fred",
        "X{.list}": "X.red,green,blue",
        "{/list}": "/red,green,blue",
    }
    mismatches = {k: expansions.get(k) for k, v in expected.items() if expansions.get(k) != v}
    if mismatches:
        return GuardVerdict(
            passed=False,
            scenario_id="PR-15",
            control_id="mcp_ts_rfc6570_uri_template_expansion_gate",
            reason_code="MCP_TS_RFC6570_URI_TEMPLATE_EXPANSION_NONCONFORMANT",
            action="Send to a human",
            details={"mismatches": mismatches},
        )

    return GuardVerdict(
        passed=True,
        scenario_id="PR-15",
        control_id="mcp_ts_rfc6570_uri_template_expansion_gate",
        reason_code="MCP_TS_RFC6570_URI_TEMPLATE_EXPANSION_VERIFIED",
        action="Act automatically",
        details={"templates_verified": len(expected)},
    )


# ---------------------------------------------------------------------------
# PR-16: sierra-research/tau2-bench#527, #536, & #537
# ---------------------------------------------------------------------------
def audit_tau2_openai_live_prompt_template_and_elicitation_evidence_integrity(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce standardized OpenAI Live voice prompt template binding (`tau2-bench#527`)
    and tau-Elicitation evidence link + deterministic figure rendering (`#536`/`#537`).
    """
    template_id = str(payload.get("openai_live_prompt_template_id", ""))
    if not template_id.startswith("openai-live-default-v") or not bool(
        payload.get("elicitation_evidence_link_reachable", False)
    ) or not bool(payload.get("elicitation_figure_render_deterministic", False)):
        return GuardVerdict(
            passed=False,
            scenario_id="PR-16",
            control_id="tau2_openai_live_template_and_elicitation_gate",
            reason_code="TAU2_UNVERSIONED_LIVE_PROMPT_OR_ELICITATION_BROKEN",
            action="Send to a human",
            details={"openai_live_prompt_template_id": template_id},
        )

    return GuardVerdict(
        passed=True,
        scenario_id="PR-16",
        control_id="tau2_openai_live_template_and_elicitation_gate",
        reason_code="TAU2_OPENAI_LIVE_TEMPLATE_AND_ELICITATION_VERIFIED",
        action="Act automatically",
        details={"openai_live_prompt_template_id": template_id},
    )


SCENARIO_EVALUATORS = {
    "PR-01": audit_ucp_ci_workflow_sha_pinning_fast_uri_and_blame_ignore,
    "PR-02": audit_x402_buyer_presign_origin_payee_pin_and_spend_killswitch,
    "PR-03": audit_x402_world_chain_usdc_and_inam_payee_receipt_gate,
    "PR-04": audit_x402_multichain_ofac_sdn_screen_and_sdk_license_notice,
    "PR-05": audit_mcp_python_case_insensitive_content_type_and_invalid_request_code,
    "PR-06": audit_mcp_python_subscriptions_listen_optout_and_generic_context_preservation,
    "PR-07": audit_mcp_python_progress_callback_containment_and_post_transport_error_isolation,
    "PR-08": audit_mcp_python_stdio_exit_on_open_stdin_and_safe_join_junction_escape,
    "PR-09": audit_mcp_python_media_mime_normalization_and_comma_scope_union,
    "PR-10": audit_mcp_ts_preserve_list_changed_false_and_literal_resource_uri_lookup,
    "PR-11": audit_mcp_ts_stdio_single_drain_listener_and_dom_free_headers,
    "PR-12": audit_mcp_ts_skills_extension_setup_contract_and_duplicate_id_guard,
    "PR-13": audit_mcp_ts_rfc9728_trailing_slash_metadata_and_ajv_dialect_options,
    "PR-14": audit_mcp_ts_event_bus_forwarded_meta_and_spec_handler_param_strip,
    "PR-15": audit_mcp_ts_rfc6570_uri_template_expansion_conformance,
    "PR-16": audit_tau2_openai_live_prompt_template_and_elicitation_evidence_integrity,
}


def evaluate_stage218_scenario(scenario_id: str, payload: Mapping[str, Any]) -> GuardVerdict:
    evaluator = SCENARIO_EVALUATORS[scenario_id]
    return evaluator(payload)
