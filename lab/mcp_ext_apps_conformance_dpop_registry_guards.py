"""Stages 248-249 deterministic protocol guards for MCP Ext-Apps, Conformance DPoP/Stateless, and Registry v1.8.4.

Covers 16 primary-source engineering updates across:
- modelcontextprotocol/ext-apps (#820, #813, #810, #808, #807, #805, #803, #801, #799, #795)
- modelcontextprotocol/conformance (#563, #560, #545, #534, #533, #532, #528, #527, #525, #524, #523)
- modelcontextprotocol/registry (#1730, #1728, #1727, #1726, #1702, #1690, #1687)
"""

from __future__ import annotations

import re
from typing import Any

VALID_MCP_LOG_LEVELS = {
    "debug",
    "info",
    "notice",
    "warning",
    "error",
    "critical",
    "alert",
    "emergency",
}

NAMED_UI_RESOURCE_PERMISSIONS = {
    "clipboard-write",
    "clipboardWrite",  # legacy deprecated alias mapped to clipboard-write
    "fullscreen",
    "picture-in-picture",
    "autoplay",
    "encrypted-media",
    "camera",
    "microphone",
    "geolocation",
}

PERMISSION_POLICY_TOKEN_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def evaluate_ext_apps_get_current_pdf_dual_surface_guard(
    *,
    surface: str,
    json_limit_mb: int,
    payload_size_mb: float,
    resource_uri: str,
    mime_type: str,
    baseline_annotations: dict[str, Any],
    current_annotations: dict[str, Any],
    baseline_form_values: dict[str, Any],
    current_form_values: dict[str, Any],
    reported_edited: bool,
    request_id_known: bool = True,
) -> dict[str, Any]:
    """PR-01 (ext-apps#820): Dual-surface get_current_pdf (app tool + interact action) & 64MB limit."""
    reasons: list[str] = []
    if surface not in {"app_tool", "interact"}:
        reasons.append(f"unsupported_surface:{surface}")
    if json_limit_mb < 64:
        reasons.append(f"json_limit_below_64mb:{json_limit_mb}")
    if payload_size_mb > float(json_limit_mb):
        reasons.append("payload_exceeds_json_limit")
    if not request_id_known:
        reasons.append("unknown_interact_request_id")
    if not resource_uri.startswith("file:///") or " " in resource_uri:
        reasons.append("invalid_or_unencoded_file_uri")
    if mime_type != "application/pdf":
        reasons.append(f"unexpected_mime_type:{mime_type}")

    actual_in_viewer_edits = (
        baseline_annotations != current_annotations
        or baseline_form_values != current_form_values
    )
    if reported_edited != actual_in_viewer_edits:
        reasons.append(
            f"inaccurate_has_in_viewer_edits:reported={reported_edited},actual={actual_in_viewer_edits}"
        )

    passed = len(reasons) == 0
    return {
        "passed": passed,
        "action": "act_automatically" if passed else "send_to_human",
        "surface": surface,
        "has_in_viewer_edits": actual_in_viewer_edits,
        "reasons": reasons,
    }


def evaluate_ext_apps_register_app_tool_icons_guard(
    *,
    tool_config: dict[str, Any],
    tools_list_entry: dict[str, Any],
) -> dict[str, Any]:
    """PR-02 (ext-apps#813): Accept icons?: Icon[] in registerAppTool's McpUiAppToolConfig."""
    reasons: list[str] = []
    icons = tool_config.get("icons")
    if icons is not None:
        if not isinstance(icons, list) or len(icons) == 0:
            reasons.append("invalid_icons_list")
        else:
            for idx, icon in enumerate(icons):
                if not isinstance(icon, dict):
                    reasons.append(f"icon_not_dict:{idx}")
                    continue
                src = str(icon.get("src", ""))
                if not (src.startswith("https://") or src.startswith("data:image/")):
                    reasons.append(f"unsafe_or_missing_icon_src:{idx}")
                theme = icon.get("theme")
                if theme is not None and theme not in {"light", "dark"}:
                    reasons.append(f"invalid_icon_theme:{theme}")

        listed_icons = tools_list_entry.get("icons")
        if listed_icons != icons:
            reasons.append("icons_not_propagated_to_tools_list")

    if "_meta" not in tool_config or "ui" not in tool_config.get("_meta", {}):
        reasons.append("missing_app_tool_ui_meta")

    passed = len(reasons) == 0
    return {
        "passed": passed,
        "action": "act_automatically" if passed else "send_to_human",
        "icon_count": len(icons) if isinstance(icons, list) else 0,
        "reasons": reasons,
    }


def evaluate_ext_apps_ui_initialize_handshake_guard(
    *,
    method: str,
    params: dict[str, Any],
    sent_initialized_notification: bool,
    notification_method: str,
    host_sent_tool_input_before_initialized: bool,
) -> dict[str, Any]:
    """PR-03 (ext-apps#810): View-to-Host handshake uses ui/initialize + appInfo + ui/notifications/initialized."""
    reasons: list[str] = []
    if method != "ui/initialize":
        reasons.append(f"invalid_view_handshake_method:{method}")
    if "clientInfo" in params or "appInfo" not in params:
        reasons.append("missing_appInfo_or_used_mcp_clientInfo")
    else:
        app_info = params["appInfo"]
        if not isinstance(app_info, dict) or not app_info.get("name") or not app_info.get("version"):
            reasons.append("incomplete_appInfo")

    if "capabilities" in params or "appCapabilities" not in params:
        reasons.append("missing_appCapabilities_or_used_mcp_capabilities")
    else:
        app_caps = params["appCapabilities"]
        modes = app_caps.get("availableDisplayModes") if isinstance(app_caps, dict) else None
        if not isinstance(modes, list) or len(modes) == 0:
            reasons.append("missing_availableDisplayModes")

    if not sent_initialized_notification or notification_method != "ui/notifications/initialized":
        reasons.append("missing_ui_notifications_initialized")
    if host_sent_tool_input_before_initialized:
        reasons.append("host_sent_payload_before_initialized_notification")

    passed = len(reasons) == 0
    return {
        "passed": passed,
        "action": "act_automatically" if passed else "send_to_human",
        "effective_method": method,
        "reasons": reasons,
    }


def evaluate_ext_apps_postmessage_loglevel_privacy_guard(
    *,
    configured_log_level: str | None,
    message_type: str,
    emitted_console_debug: bool,
    emitted_console_error: bool,
    fired_onerror_callback: bool,
) -> dict[str, Any]:
    """PR-04 (ext-apps#808, #803): PostMessageTransport logLevel defaults to 'warning' for message privacy."""
    reasons: list[str] = []
    effective_level = (
        configured_log_level
        if configured_log_level in VALID_MCP_LOG_LEVELS
        else "warning"
    )

    if message_type == "tool-input-partial":
        if emitted_console_debug:
            reasons.append("partial_tool_input_logged_to_console")
    elif message_type in {"outgoing_rpc", "incoming_rpc", "ignored_unknown_source"}:
        should_debug = effective_level == "debug"
        if emitted_console_debug != should_debug:
            reasons.append(
                f"traffic_debug_privacy_violation:level={effective_level},emitted={emitted_console_debug}"
            )
    elif message_type == "malformed_jsonrpc":
        should_error = effective_level in {"debug", "info", "notice", "warning", "error"}
        if emitted_console_error != should_error:
            reasons.append(
                f"malformed_error_log_mismatch:level={effective_level},emitted={emitted_console_error}"
            )
        if not fired_onerror_callback:
            reasons.append("malformed_jsonrpc_did_not_fire_onerror")
    else:
        reasons.append(f"unknown_message_type:{message_type}")

    passed = len(reasons) == 0
    return {
        "passed": passed,
        "action": "act_automatically" if passed else "send_to_human",
        "effective_log_level": effective_level,
        "reasons": reasons,
    }


def evaluate_ext_apps_resolve_qualified_tool_name_guard(
    *,
    entry_bare_tool_name: str,
    host_context_tool_name: str | None,
    target_bare_tool_name: str,
    dispatched_tool_name: str,
) -> dict[str, Any]:
    """PR-05 (ext-apps#807): Recover host-applied prefix in callServerTool via getHostContext().toolInfo."""
    reasons: list[str] = []
    expected_name = target_bare_tool_name
    if host_context_tool_name and host_context_tool_name.endswith(entry_bare_tool_name):
        prefix = host_context_tool_name[: -len(entry_bare_tool_name)]
        expected_name = f"{prefix}{target_bare_tool_name}"

    if dispatched_tool_name != expected_name:
        reasons.append(
            f"unqualified_or_mismatched_tool_call:expected={expected_name},got={dispatched_tool_name}"
        )

    passed = len(reasons) == 0
    return {
        "passed": passed,
        "action": "act_automatically" if passed else "send_to_human",
        "expected_tool_name": expected_name,
        "reasons": reasons,
    }


def evaluate_ext_apps_cli_roots_refresh_provenance_guard(
    *,
    cli_local_dirs: list[str],
    previous_client_roots: list[str],
    refreshed_client_roots: list[str],
    resulting_allowed_local_dirs: list[str],
) -> dict[str, Any]:
    """PR-06 (ext-apps#805): Keep CLI-arg directories across client roots refreshes while revoking removed client roots."""
    reasons: list[str] = []
    expected_allowed = set(cli_local_dirs) | set(refreshed_client_roots)
    actual_allowed = set(resulting_allowed_local_dirs)

    missing_cli = set(cli_local_dirs) - actual_allowed
    if missing_cli:
        reasons.append(f"cli_local_dirs_wiped_on_refresh:{sorted(missing_cli)}")

    revoked_roots = (set(previous_client_roots) - set(refreshed_client_roots)) - set(cli_local_dirs)
    leaked_revoked = revoked_roots & actual_allowed
    if leaked_revoked:
        reasons.append(f"revoked_client_roots_retained:{sorted(leaked_revoked)}")

    if actual_allowed != expected_allowed:
        reasons.append("allowed_dirs_mismatch_expected_provenance_union")

    passed = len(reasons) == 0
    return {
        "passed": passed,
        "action": "act_automatically" if passed else "send_to_human",
        "expected_allowed_dirs": sorted(expected_allowed),
        "reasons": reasons,
    }


def evaluate_ext_apps_cors_permissions_sandbox_guard(
    *,
    cors_allow_headers: list[str],
    requested_permissions: dict[str, bool],
    rendered_allow_attribute: list[str],
    sandbox_synchronous_task_processor: bool,
    knockout_unsafe_eval_disabled: bool,
    fallback_on_undefined_coordinates: bool,
) -> dict[str, Any]:
    """PR-07 (ext-apps#801, #799, #795): Browser-host CORS headers (SEP-2243), open UI permissions, and Cesium sandbox."""
    reasons: list[str] = []
    normalized_headers = {h.lower() for h in cors_allow_headers}
    required_cors = {
        "content-type",
        "accept",
        "mcp-session-id",
        "mcp-protocol-version",
        "mcp-method",
        "mcp-name",
    }
    missing_cors = sorted(required_cors - normalized_headers)
    if missing_cors:
        reasons.append(f"missing_browser_host_cors_headers:{missing_cors}")

    expected_allow: list[str] = []
    for key, enabled in requested_permissions.items():
        if not enabled:
            continue
        canonical_key = "clipboard-write" if key == "clipboardWrite" else key
        if not PERMISSION_POLICY_TOKEN_RE.match(canonical_key):
            reasons.append(f"invalid_permission_policy_feature:{key}")
            continue
        if canonical_key not in expected_allow:
            expected_allow.append(canonical_key)

    if sorted(rendered_allow_attribute) != sorted(expected_allow):
        reasons.append(
            f"allow_attribute_mismatch:expected={sorted(expected_allow)},got={sorted(rendered_allow_attribute)}"
        )

    if not sandbox_synchronous_task_processor:
        reasons.append("sandbox_web_worker_task_processor_not_patched")
    if not knockout_unsafe_eval_disabled:
        reasons.append("knockout_unsafe_eval_widget_not_disabled")
    if not fallback_on_undefined_coordinates:
        reasons.append("undefined_coordinates_not_handled")

    passed = len(reasons) == 0
    return {
        "passed": passed,
        "action": "act_automatically" if passed else "send_to_human",
        "effective_allow": expected_allow,
        "reasons": reasons,
    }


def evaluate_conformance_stateless_result_type_guard(
    *,
    protocol_version: str,
    tool_name: str,
    log_level_meta_present: bool,
    emitted_log_notification: bool,
    emitted_progress_notification: bool,
    result_payload: dict[str, Any],
) -> dict[str, Any]:
    """PR-08 (conformance#563): Stamp resultType: 'complete' on hand-written stateless tool results (2026-07-28)."""
    reasons: list[str] = []
    if protocol_version == "2026-07-28":
        if result_payload.get("resultType") != "complete":
            reasons.append("missing_or_invalid_stateless_resultType")

    if tool_name == "test_logging_tool":
        if not log_level_meta_present and emitted_log_notification:
            reasons.append("logged_without_logLevel_meta")
    elif tool_name == "test_streaming_elicitation":
        if not emitted_progress_notification:
            reasons.append("missing_unconditional_progress_notification")

    passed = len(reasons) == 0
    return {
        "passed": passed,
        "action": "act_automatically" if passed else "send_to_human",
        "result_type": result_payload.get("resultType"),
        "reasons": reasons,
    }


def evaluate_conformance_empty_custom_header_presence_guard(
    *,
    has_optional_annotated_string_fixture: bool,
    argument_state: str,
    header_state: str,
    http_status: int,
    jsonrpc_error_code: int | None,
    tool_invoked: bool,
) -> dict[str, Any]:
    """PR-09 (conformance#560): Cover empty custom-header presence mismatches (empty/absent, omitted/empty, null/empty)."""
    reasons: list[str] = []
    if not has_optional_annotated_string_fixture:
        return {
            "passed": False,
            "action": "send_to_human",
            "verdict": "untestable_missing_optional_annotated_string",
            "reasons": ["missing_optional_annotated_string_fixture"],
        }

    mismatch_cases = {
        ("empty_string", "absent"),
        ("omitted", "present_empty"),
        ("null", "present_empty"),
    }
    is_mismatch = (argument_state, header_state) in mismatch_cases
    if is_mismatch:
        if http_status != 400:
            reasons.append(f"expected_http_400_got_{http_status}")
        if jsonrpc_error_code != -32020:
            reasons.append(f"expected_jsonrpc_neg32020_got_{jsonrpc_error_code}")
        if tool_invoked:
            reasons.append("tool_invoked_on_header_presence_mismatch")

    passed = len(reasons) == 0
    return {
        "passed": passed,
        "action": "act_automatically" if passed else "send_to_human",
        "is_presence_mismatch": is_mismatch,
        "reasons": reasons,
    }


def evaluate_conformance_tasks_extension_request_state_guard(
    *,
    advertises_tasks_extension: bool,
    supported_task_methods: list[str],
    has_execution_task_support_meta: bool,
    tasks_status_notifications_pending: bool,
    round2_is_error: bool,
    round2_text_blocks: list[str],
) -> dict[str, Any]:
    """PR-10 (conformance#545, #534): Implement Tasks extension in everything-server & validate state-ok completion."""
    reasons: list[str] = []
    if not advertises_tasks_extension:
        reasons.append("missing_tasks_capability_advertisement")
    required_methods = {"tasks/get", "tasks/update", "tasks/cancel"}
    if not required_methods.issubset(set(supported_task_methods)):
        reasons.append("missing_required_tasks_methods")
    if not has_execution_task_support_meta:
        reasons.append("missing_per_tool_execution_taskSupport")
    if not tasks_status_notifications_pending:
        reasons.append("tasks_status_notifications_must_stay_pending")
    if round2_is_error:
        reasons.append("round2_request_state_completion_is_error")
    if not any("state-ok" in block for block in round2_text_blocks):
        reasons.append("round2_completion_missing_state_ok_marker")

    passed = len(reasons) == 0
    return {
        "passed": passed,
        "action": "act_automatically" if passed else "send_to_human",
        "reasons": reasons,
    }


def evaluate_conformance_runner_session_sweep_stream_timer_guard(
    *,
    scenario_outcome: str,
    connection_resolved_after_timeout: bool,
    delete_requests_sent: int,
    leaked_live_sessions: int,
    header_latency_ms: int,
    header_timeout_ms: int,
    post_header_frame_arrival_ms: int,
    collection_window_ms: int,
    timer_reset_after_headers: bool,
) -> dict[str, Any]:
    """PR-11 (conformance#533, #532): Runner terminates leaked/late sessions (single DELETE) & resets stream timer after headers."""
    reasons: list[str] = []
    if leaked_live_sessions > 0:
        reasons.append(f"leaked_live_sessions:{leaked_live_sessions}")
    if delete_requests_sent != 1:
        reasons.append(f"expected_single_delete_got_{delete_requests_sent}")
    if connection_resolved_after_timeout and scenario_outcome != "timeout_closed_late_connection":
        reasons.append("late_post_timeout_connection_not_closed_by_scenarioFinished_guard")
    if not timer_reset_after_headers:
        reasons.append("stream_collection_timer_started_before_response_headers")
    if header_latency_ms > header_timeout_ms:
        reasons.append("response_headers_exceeded_stateless_timeout")
    if post_header_frame_arrival_ms > collection_window_ms:
        reasons.append("frame_arrived_after_post_header_collection_window")

    passed = len(reasons) == 0
    return {
        "passed": passed,
        "action": "act_automatically" if passed else "send_to_human",
        "delete_requests_sent": delete_requests_sent,
        "reasons": reasons,
    }


def evaluate_conformance_sep1932_dpop_server_challenge_guard(
    *,
    defect_kind: str,
    http_status: int,
    www_authenticate_schemes: list[str],
    dpop_error_code: str | None,
) -> dict[str, Any]:
    """PR-12 (conformance#528, #527): SEP-1932 DPoP server error codes & strict 401 Bearer-downgrade challenge."""
    reasons: list[str] = []
    if http_status != 401:
        reasons.append(f"expected_http_401_got_{http_status}")

    if defect_kind == "bearer_downgrade":
        if not any(s in {"Bearer", "DPoP"} for s in www_authenticate_schemes):
            reasons.append("missing_bearer_or_dpop_www_authenticate_challenge")
        if dpop_error_code is not None and dpop_error_code not in {"invalid_token", "invalid_dpop_proof"}:
            reasons.append(f"unexpected_dpop_error_code:{dpop_error_code}")
    elif defect_kind == "proof_defect":
        if "DPoP" not in www_authenticate_schemes:
            reasons.append("missing_dpop_www_authenticate_challenge")
        if dpop_error_code != "invalid_dpop_proof":
            reasons.append(f"expected_invalid_dpop_proof_got_{dpop_error_code}")
    elif defect_kind == "wrong_audience":
        if "DPoP" not in www_authenticate_schemes:
            reasons.append("missing_dpop_www_authenticate_challenge")
        if dpop_error_code != "invalid_token":
            reasons.append(f"expected_invalid_token_got_{dpop_error_code}")
    elif defect_kind == "cnf_jkt_mismatch":
        if "DPoP" not in www_authenticate_schemes:
            reasons.append("missing_dpop_www_authenticate_challenge")
        if dpop_error_code not in {"invalid_token", "invalid_dpop_proof"}:
            reasons.append(f"expected_invalid_token_or_proof_got_{dpop_error_code}")
    else:
        reasons.append(f"unknown_defect_kind:{defect_kind}")

    passed = len(reasons) == 0
    return {
        "passed": passed,
        "action": "act_automatically" if passed else "send_to_human",
        "defect_kind": defect_kind,
        "reasons": reasons,
    }


def evaluate_conformance_sep1932_dpop_as_client_binding_guard(
    *,
    as_invalid_proof_status: int,
    as_invalid_proof_error: str,
    nonce_challenged: bool,
    dpop_nonce_header_present: bool,
    mismatched_nonce_rejected_4xx: bool,
    refresh_token_used: bool,
    refresh_proof_matches_original_key: bool,
    prior_failed_refresh_sticky: bool,
    auth_code_dpop_jkt: str | None,
    token_exchange_proof_jkt: str,
) -> dict[str, Any]:
    """PR-13 (conformance#525, #524, #523): SEP-1932 AS negative probes/nonce, sticky refresh binding, and dpop_jkt."""
    reasons: list[str] = []
    if as_invalid_proof_status != 400 or as_invalid_proof_error != "invalid_dpop_proof":
        reasons.append("as_failed_to_reject_invalid_proof_with_400_invalid_dpop_proof")
    if nonce_challenged:
        if not dpop_nonce_header_present:
            reasons.append("missing_dpop_nonce_header_on_challenge")
        if not mismatched_nonce_rejected_4xx:
            reasons.append("mismatched_dpop_nonce_not_rejected")
    if refresh_token_used:
        if not refresh_proof_matches_original_key:
            reasons.append("refresh_token_used_without_original_dpop_key_proof")
        if not prior_failed_refresh_sticky:
            reasons.append("failed_refresh_observation_not_sticky")
    if not auth_code_dpop_jkt:
        reasons.append("missing_authorization_dpop_jkt")
    elif auth_code_dpop_jkt != token_exchange_proof_jkt:
        reasons.append("dpop_jkt_mismatch_on_token_exchange")

    passed = len(reasons) == 0
    return {
        "passed": passed,
        "action": "act_automatically" if passed else "send_to_human",
        "reasons": reasons,
    }


def evaluate_registry_trigram_index_and_dpr_icon_guard(
    *,
    trigram_index_exists: bool,
    index_is_valid: bool,
    index_is_ready: bool,
    device_pixel_ratio: float,
    candidate_icons: list[dict[str, Any]],
    selected_icon_src: str,
) -> dict[str, Any]:
    """PR-14 (registry#1730, #1728): GIN pg_trgm index readiness & devicePixelRatio-aware icon selection."""
    reasons: list[str] = []
    if not trigram_index_exists:
        reasons.append("missing_idx_servers_name_trgm")
    if not index_is_valid or not index_is_ready:
        reasons.append("interrupted_or_invalid_trigram_index")

    target_px = 40.0 * max(device_pixel_ratio, 1.0)
    best_src = ""
    best_score = -1.0
    for icon in candidate_icons:
        sizes_raw = str(icon.get("sizes", "")).strip()
        src = str(icon.get("src", ""))
        if sizes_raw in {"", "any"}:
            score = 1000.0
        else:
            m = re.match(r"^(\d+)x(\d+)$", sizes_raw)
            if m:
                px = float(m.group(1))
                score = 500.0 - abs(px - target_px) if px >= target_px else px
            else:
                score = 0.0
        if score > best_score:
            best_score = score
            best_src = src

    if selected_icon_src != best_src:
        reasons.append(f"suboptimal_icon_for_dpr:expected={best_src},got={selected_icon_src}")

    passed = len(reasons) == 0
    return {
        "passed": passed,
        "action": "act_automatically" if passed else "send_to_human",
        "target_px": target_px,
        "expected_icon_src": best_src,
        "reasons": reasons,
    }


def evaluate_registry_prod_pgdump_restic_backup_guard(
    *,
    environment: str,
    retired_k8up_schedule_removed: bool,
    backup_cronjob_enabled: bool,
    pg_dump_compress_level: int,
    sha256_and_restic_check_passed: bool,
    retention_days: int,
    gcs_prefix: str,
    grafana_initial_admin_secret_created: bool,
) -> dict[str, Any]:
    """PR-15 (registry#1727, #1726): Remove retired K8up schedule & enforce prod-only validated pg_dump/Restic backups."""
    reasons: list[str] = []
    if not retired_k8up_schedule_removed:
        reasons.append("retired_k8up_schedule_still_present")
    if grafana_initial_admin_secret_created:
        reasons.append("unused_grafana_initial_admin_secret_generated")

    if environment == "prod":
        if not backup_cronjob_enabled:
            reasons.append("prod_backup_cronjob_disabled")
        if pg_dump_compress_level != 0:
            reasons.append(f"pg_dump_compress_must_be_0_for_restic_dedup:got={pg_dump_compress_level}")
        if not sha256_and_restic_check_passed:
            reasons.append("backup_archive_or_restic_verification_failed")
        if retention_days != 28:
            reasons.append(f"unexpected_retention_days:{retention_days}")
        if gcs_prefix != "postgres-custom-v1/":
            reasons.append(f"unexpected_gcs_prefix:{gcs_prefix}")
    else:
        if backup_cronjob_enabled:
            reasons.append("backup_cronjob_must_not_run_outside_prod")

    passed = len(reasons) == 0
    return {
        "passed": passed,
        "action": "act_automatically" if passed else "send_to_human",
        "environment": environment,
        "reasons": reasons,
    }


def evaluate_registry_nested_server_json_and_remote_ownership_guard(
    *,
    changed_files: list[str],
    trusted_contributor: bool,
    auto_closed_as_invalid_publish_pr: bool,
    is_remote_only_server: bool,
    has_packages_field: bool,
    has_remotes_field: bool,
    duplicate_remote_url_detected: bool,
    search_query_active: bool,
    page_number: int,
    recently_updated_visible: bool,
    recently_updated_collapsed_count: int,
) -> dict[str, Any]:
    """PR-16 (registry#1702, #1690, #1687): Catch nested **/server.json PRs, remote URL uniqueness, and UI search collapse."""
    reasons: list[str] = []
    all_server_json = len(changed_files) > 0 and all(
        f == "server.json" or f.endswith("/server.json") for f in changed_files
    )
    should_auto_close = all_server_json and not trusted_contributor
    if auto_closed_as_invalid_publish_pr != should_auto_close:
        reasons.append(
            f"nested_server_json_autoclose_mismatch:expected={should_auto_close},got={auto_closed_as_invalid_publish_pr}"
        )

    if is_remote_only_server:
        if has_packages_field or not has_remotes_field:
            reasons.append("remote_only_server_must_replace_packages_with_remotes")
    if duplicate_remote_url_detected:
        reasons.append("duplicate_remote_url_across_server_names")

    should_show_recent = (not search_query_active) and (page_number == 1)
    if recently_updated_visible != should_show_recent:
        reasons.append("recently_updated_visibility_mismatch")
    if recently_updated_visible and recently_updated_collapsed_count != 6:
        reasons.append(f"expected_6_collapsed_cards_got_{recently_updated_collapsed_count}")

    passed = len(reasons) == 0
    return {
        "passed": passed,
        "action": "act_automatically" if passed else "send_to_human",
        "should_auto_close_pr": should_auto_close,
        "reasons": reasons,
    }
