"""Stage 256 deterministic guard evaluators covering 66 primary-source PRs across x402, AgentKit, A2A SDKs, UCP, Stripe, MCP SDKs/Conformance/Inspector, and tau2-bench."""

from __future__ import annotations

from typing import Any, Callable

GuardResult = dict[str, Any]


def _ok(guard_id: str, code: str, **details: Any) -> GuardResult:
    return {"guard_id": guard_id, "allowed": True, "decision_code": code, "details": details}


def _block(guard_id: str, code: str, **details: Any) -> GuardResult:
    return {"guard_id": guard_id, "allowed": False, "decision_code": code, "details": details}


def evaluate_x402_v1_networks_filter_and_versioned_requirements_guard(payload: dict[str, Any]) -> GuardResult:
    """PR-01: x402-foundation/x402#3935, #3934, #3789, #3777, #3771."""
    gid = "PR-01"
    configured_patterns = payload.get("configured_network_patterns", ["eip155:84532"])
    v1_network_caip2_map = payload.get(
        "v1_network_caip2_map",
        {"base": "eip155:8453", "base-sepolia": "eip155:84532", "solana": "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp"},
    )
    registered_v1_networks = payload.get("registered_v1_networks", [])
    for v1_name in registered_v1_networks:
        caip2_equiv = v1_network_caip2_map.get(v1_name)
        if not caip2_equiv or caip2_equiv not in configured_patterns:
            return _block(
                gid,
                "X402_V1_UNFILTERED_MAINNET_REGISTRATION_REJECTED",
                v1_network=v1_name,
                caip2_equivalent=caip2_equiv,
                configured_patterns=configured_patterns,
            )
    payload_version = int(payload.get("payload_x402_version", 1))
    requirements_parser_version = int(payload.get("requirements_parser_version", 1))
    invalid_requirements_http_status = int(payload.get("invalid_requirements_http_status", 400))
    if requirements_parser_version != payload_version or invalid_requirements_http_status != 400:
        return _block(
            gid,
            "X402_FACILITATOR_REQUIREMENTS_VERSION_MISMATCH_OR_500_REJECTED",
            payload_version=payload_version,
            requirements_parser_version=requirements_parser_version,
            invalid_requirements_http_status=invalid_requirements_http_status,
        )
    if payload.get("payer_sanctioned", False) and int(payload.get("payer_screen_http_status", 200)) != 451:
        return _block(gid, "X402_SANCTIONED_PAYER_MISSING_HTTP_451_REJECTED")
    return _ok(
        gid,
        "X402_V1_NETWORKS_FILTER_AND_VERSIONED_REQUIREMENTS_VERIFIED",
        registered_v1_networks=registered_v1_networks,
        payload_version=payload_version,
    )


def evaluate_agentkit_standing_witness_and_spend_preflight_guard(payload: dict[str, Any]) -> GuardResult:
    """PR-02: coinbase/agentkit#1546, #1545."""
    gid = "PR-02"
    if not payload.get("standing_witness_verified", False) or not payload.get("circuit_breaker_closed", False):
        return _block(
            gid,
            "AGENTKIT_STANDING_WITNESS_CIRCUIT_BREAKER_TRIPPED",
            standing_witness_verified=payload.get("standing_witness_verified", False),
            circuit_breaker_closed=payload.get("circuit_breaker_closed", False),
        )
    screening_fee_usd = float(payload.get("screening_fee_usd", 0.01))
    if screening_fee_usd not in (0.01, 0.02):
        return _block(gid, "AGENTKIT_SPEND_PREFLIGHT_FEE_MISMATCH_REJECTED", screening_fee_usd=screening_fee_usd)
    if payload.get("merchant_url_used_as_payment_destination", False):
        return _block(gid, "AGENTKIT_MERCHANT_URL_PAYMENT_DESTINATION_CONFUSION_REJECTED")
    if not payload.get("screening_service_available", True) and payload.get("preflight_decision") == "allow":
        return _block(gid, "AGENTKIT_UNAVAILABLE_SCREENING_SILENT_ALLOW_REJECTED")
    if payload.get("operator_trial_quota_exhausted", False) and payload.get("fell_back_to_paid_screening", False):
        return _block(gid, "AGENTKIT_TRIAL_QUOTA_PAID_FALLBACK_REJECTED")
    return _ok(
        gid,
        "AGENTKIT_STANDING_WITNESS_AND_SPEND_PREFLIGHT_VERIFIED",
        screening_fee_usd=screening_fee_usd,
        preflight_decision=payload.get("preflight_decision", "allow"),
    )


def evaluate_agentkit_erc20_multicall_fallback_and_cdp_idempotency_guard(payload: dict[str, Any]) -> GuardResult:
    """PR-03: coinbase/agentkit#1535, #1530, #1541, #1529."""
    gid = "PR-03"
    multicall3_configured = payload.get("multicall3_configured", False)
    multicall_error_name = payload.get("multicall_error_name", "ChainDoesNotSupportContract")
    used_read_contract_fallback = payload.get("used_read_contract_fallback", False)
    if not multicall3_configured and multicall_error_name == "ChainDoesNotSupportContract" and not used_read_contract_fallback:
        return _block(
            gid,
            "AGENTKIT_ERC20_MISSING_READ_CONTRACT_FALLBACK_ON_NO_MULTICALL3_REJECTED",
            multicall_error_name=multicall_error_name,
        )
    caller_idempotency_key = payload.get("caller_idempotency_key", "")
    forwarded_idempotency_key = payload.get("forwarded_idempotency_key", "")
    provider_generated_new_key_on_retry = payload.get("provider_generated_new_key_on_retry", False)
    if not caller_idempotency_key or forwarded_idempotency_key != caller_idempotency_key or provider_generated_new_key_on_retry:
        return _block(
            gid,
            "AGENTKIT_CDP_VALUE_MOVING_IDEMPOTENCY_KEY_DROPPED_OR_REGENERATED_REJECTED",
            caller_idempotency_key=caller_idempotency_key,
            forwarded_idempotency_key=forwarded_idempotency_key,
            provider_generated_new_key_on_retry=provider_generated_new_key_on_retry,
        )
    return _ok(
        gid,
        "AGENTKIT_ERC20_MULTICALL_FALLBACK_AND_CDP_IDEMPOTENCY_VERIFIED",
        forwarded_idempotency_key=forwarded_idempotency_key,
    )


def evaluate_a2a_python_boolean_id_executor_failfast_and_stream_cleanup_guard(payload: dict[str, Any]) -> GuardResult:
    """PR-04: a2aproject/a2a-python#1350, #1364, #1354, #1345, #1338, #1336, #1335."""
    gid = "PR-04"
    req_id = payload.get("jsonrpc_request_id")
    if isinstance(req_id, bool):
        if int(payload.get("error_code", 0)) != -32600 or payload.get("response_id") is not None or payload.get("handler_invoked", False):
            return _block(
                gid,
                "A2A_PYTHON_BOOLEAN_REQUEST_ID_ACCEPTED_REJECTED",
                jsonrpc_request_id=req_id,
                error_code=payload.get("error_code"),
            )
    if payload.get("executor_returned_without_events", False) and not payload.get("raised_internal_error_fast", False):
        return _block(gid, "A2A_PYTHON_SILENT_EXECUTOR_INFINITE_HANG_REJECTED")
    if int(payload.get("stream_history_length", 10)) < 0 and not payload.get("negative_history_rejected", False):
        return _block(gid, "A2A_PYTHON_NEGATIVE_STREAM_HISTORY_LENGTH_ACCEPTED_REJECTED")
    if payload.get("stream_cancelled", False) and not payload.get("lifecycle_events_marked_done", False):
        return _block(gid, "A2A_PYTHON_CANCELLED_STREAM_PRODUCER_LEAK_REJECTED")
    if payload.get("malformed_first_sig_header", False) and not payload.get("checked_remaining_signatures", False):
        return _block(gid, "A2A_PYTHON_MALFORMED_SIGNATURE_HEADER_ABORTED_EARLY_REJECTED")
    return _ok(
        gid,
        "A2A_PYTHON_BOOLEAN_ID_EXECUTOR_FAILFAST_AND_STREAM_CLEANUP_VERIFIED",
        jsonrpc_request_id=req_id,
    )


def evaluate_a2a_js_canonicalization_depth_and_nanosecond_task_store_guard(payload: dict[str, Any]) -> GuardResult:
    """PR-05: a2aproject/a2a-js#786, #776, #756, #748, #745."""
    gid = "PR-05"
    extension_params_depth = int(payload.get("extension_params_depth", 16))
    max_depth = int(payload.get("max_canonicalization_depth", 128))
    if extension_params_depth > max_depth:
        if not payload.get("threw_canonicalization_error", False) or payload.get("invoked_key_provider", False):
            return _block(
                gid,
                "A2A_JS_UNBOUNDED_EXTENSION_PARAMS_DEPTH_STACK_EXHAUSTION_REJECTED",
                extension_params_depth=extension_params_depth,
                max_depth=max_depth,
            )
    if int(payload.get("preserved_submillisecond_nanosecond_digits", 0)) < 6:
        return _block(
            gid,
            "A2A_JS_TASK_STORE_MILLISECOND_TRUNCATION_TIE_REJECTED",
            preserved_digits=payload.get("preserved_submillisecond_nanosecond_digits", 0),
        )
    if not payload.get("status_and_artifact_metadata_merged", False):
        return _block(gid, "A2A_JS_STATUS_ARTIFACT_METADATA_DROPPED_REJECTED")
    return _ok(
        gid,
        "A2A_JS_CANONICALIZATION_DEPTH_AND_NANOSECOND_TASK_STORE_VERIFIED",
        extension_params_depth=extension_params_depth,
    )


def evaluate_a2a_go_java_taskstate_unmarshal_and_listtasks_query_guard(payload: dict[str, Any]) -> GuardResult:
    """PR-06: a2aproject/a2a-go#404, #425 & a2aproject/a2a-java#1240, #1239, #1236, #1235."""
    gid = "PR-06"
    valid_states = {
        "TASK_STATE_SUBMITTED",
        "TASK_STATE_WORKING",
        "TASK_STATE_INPUT_REQUIRED",
        "TASK_STATE_AUTH_REQUIRED",
        "TASK_STATE_COMPLETED",
        "TASK_STATE_CANCELED",
        "TASK_STATE_FAILED",
        "TASK_STATE_REJECTED",
    }
    task_state = str(payload.get("task_state", "TASK_STATE_WORKING"))
    if task_state not in valid_states and not payload.get("unmarshal_rejected_unknown_state", False):
        return _block(gid, "A2A_GO_UNKNOWN_OR_LOWERCASE_TASK_STATE_ACCEPTED_REJECTED", task_state=task_state)
    timestamp_query_param = str(payload.get("list_tasks_timestamp_param", "statusTimestampAfter"))
    if timestamp_query_param != "statusTimestampAfter":
        return _block(
            gid,
            "A2A_REST_LIST_TASKS_LEGACY_TIMESTAMP_PARAM_REJECTED",
            timestamp_query_param=timestamp_query_param,
        )
    if payload.get("tenant") is None and payload.get("called_proto_set_tenant_null", False):
        return _block(gid, "A2A_JAVA_GRPC_LIST_TASKS_NULL_TENANT_NPE_REJECTED")
    return _ok(
        gid,
        "A2A_GO_JAVA_TASKSTATE_UNMARSHAL_AND_LISTTASKS_QUERY_VERIFIED",
        task_state=task_state,
        timestamp_query_param=timestamp_query_param,
    )


def evaluate_a2a_dotnet_v03_exception_translation_and_push_cleanup_guard(payload: dict[str, Any]) -> GuardResult:
    """PR-07: a2aproject/a2a-dotnet#575, #572, #569, #568, #567."""
    gid = "PR-07"
    if not payload.get("v03_exception_translated_to_v1", False) or not payload.get("error_code_and_message_preserved", False):
        return _block(gid, "A2A_DOTNET_V03_ADAPTER_EXCEPTION_LEAK_OR_LOSS_REJECTED")
    if payload.get("task_reached_terminal_state", True) and not payload.get("terminal_push_config_deleted", False):
        return _block(gid, "A2A_DOTNET_TERMINAL_PUSH_CONFIG_RETENTION_LEAK_REJECTED")
    push_scheme = str(payload.get("push_destination_scheme", "https")).lower()
    is_loopback = bool(payload.get("push_destination_is_loopback", False))
    allow_loopback = bool(payload.get("allow_loopback_enabled", False))
    if push_scheme == "http" and (not is_loopback or not allow_loopback):
        return _block(
            gid,
            "A2A_DOTNET_INSECURE_NON_LOOPBACK_OR_UNOPTED_HTTP_PUSH_REJECTED",
            push_scheme=push_scheme,
            is_loopback=is_loopback,
            allow_loopback=allow_loopback,
        )
    return _ok(
        gid,
        "A2A_DOTNET_V03_EXCEPTION_TRANSLATION_AND_PUSH_CLEANUP_VERIFIED",
        push_scheme=push_scheme,
    )


def evaluate_ucp_rest_idempotency_race_winner_and_rfc9421_ecdsa_guard(payload: dict[str, Any]) -> GuardResult:
    """PR-08: Universal-Commerce-Protocol/samples#245, #252, #256, #243 & conformance#113, #110, #107, #106, #93, #88."""
    gid = "PR-08"
    concurrent_identical_500_count = int(payload.get("concurrent_identical_500_count", 0))
    differing_body_collision_status = int(payload.get("differing_body_collision_status", 409))
    if concurrent_identical_500_count > 0 or differing_body_collision_status != 409:
        return _block(
            gid,
            "UCP_IDEMPOTENCY_RACE_HTTP_500_OR_MISSING_409_CONFLICT_REJECTED",
            concurrent_identical_500_count=concurrent_identical_500_count,
            differing_body_collision_status=differing_body_collision_status,
        )
    if str(payload.get("rfc9421_ecdsa_p256_section", "3.3.4")) != "3.3.4":
        return _block(
            gid,
            "UCP_SIGNING_WRONG_RFC9421_SECTION_CITATION_REJECTED",
            cited_section=payload.get("rfc9421_ecdsa_p256_section"),
        )
    if int(payload.get("line_item_quantity", 1)) <= 0:
        return _block(gid, "UCP_NON_POSITIVE_LINE_ITEM_QUANTITY_REJECTED", quantity=payload.get("line_item_quantity"))
    if payload.get("merchant_fixture_currency") == payload.get("conflict_test_currency"):
        return _block(gid, "UCP_CONFORMANCE_SAME_CURRENCY_NOOP_CONFLICT_TEST_REJECTED")
    return _ok(
        gid,
        "UCP_REST_IDEMPOTENCY_RACE_WINNER_AND_RFC9421_ECDSA_VERIFIED",
        differing_body_collision_status=differing_body_collision_status,
    )


def evaluate_ucp_sdk_discriminator_retyping_max_properties_and_allof_guard(payload: dict[str, Any]) -> GuardResult:
    """PR-09: Universal-Commerce-Protocol/python-sdk#93, #91, #89, #87, #83 & js-sdk#89, #82, #67."""
    gid = "PR-09"
    if not payload.get("conditional_array_retyping_applied", False) or not payload.get("root_max_properties_injected", False):
        return _block(gid, "UCP_PYTHON_SDK_MISSING_ARRAY_RETYPING_OR_MAX_PROPERTIES_REJECTED")
    if not payload.get("jwk_if_then_rules_restored", False) or not payload.get("unit_c62_scale_pinned", False):
        return _block(gid, "UCP_PYTHON_SDK_JWK_RULES_OR_C62_SCALE_PIN_DROPPED_REJECTED")
    if not payload.get("allof_top_level_required_preserved", False) or int(payload.get("unmodeled_capability_silent_exits", 0)) > 0:
        return _block(gid, "UCP_JS_SDK_ALLOF_REQUIRED_STRIPPED_OR_SILENT_CODEGEN_EXIT_REJECTED")
    return _ok(
        gid,
        "UCP_SDK_DISCRIMINATOR_RETYPING_MAX_PROPERTIES_AND_ALLOF_VERIFIED",
        constraint_families=9,
    )


def evaluate_stripe_action_sha_pinning_plugin_subtree_and_key_cutoff_guard(payload: dict[str, Any]) -> GuardResult:
    """PR-10: stripe/agent-toolkit#537, #495, #496, #476 + Stripe MCP 2026-10-31 Cutoff."""
    gid = "PR-10"
    if int(payload.get("unpinned_github_actions_count", 0)) > 0 or not payload.get("all_23_actions_sha_pinned", False):
        return _block(
            gid,
            "STRIPE_TOOLKIT_MUTABLE_GITHUB_ACTION_TAG_REJECTED",
            unpinned_github_actions_count=payload.get("unpinned_github_actions_count"),
        )
    if not payload.get("agent_plugin_subtree_synced", False) or not payload.get("guard_skills_uses_paths_ignore", False):
        return _block(gid, "STRIPE_TOOLKIT_PLUGIN_SUBTREE_OR_GUARD_SKILLS_DRIFT_REJECTED")
    credential = str(payload.get("stripe_mcp_credential", ""))
    if credential.startswith(("sk_live_", "sk_test_")) or not (
        credential.startswith("rk_") or credential.startswith("oauth_")
    ):
        return _block(
            gid,
            "STRIPE_MCP_LEGACY_SECRET_KEY_POST_CUTOFF_REJECTED",
            credential_prefix=credential[:8],
            cutoff_date="2026-10-31",
        )
    return _ok(
        gid,
        "STRIPE_ACTION_SHA_PINNING_PLUGIN_SUBTREE_AND_KEY_CUTOFF_VERIFIED",
        pinned_actions=23,
        cutoff_date="2026-10-31",
    )


def evaluate_mcp_go_sdk_expiry_before_scopes_and_www_authenticate_guard(payload: dict[str, Any]) -> GuardResult:
    """PR-11: modelcontextprotocol/go-sdk#1350, #1351, #1348, #1345, #1395."""
    gid = "PR-11"
    token_expired = bool(payload.get("token_expired", False))
    token_missing_exp = bool(payload.get("token_missing_expiration", False))
    allow_missing_exp = bool(payload.get("allow_missing_expiration", False))
    returned_http_status = int(payload.get("returned_http_status", 200))
    if (token_expired or (token_missing_exp and not allow_missing_exp)) and returned_http_status != 401:
        return _block(
            gid,
            "MCP_GO_SDK_EXPIRED_TOKEN_RETURNED_403_INSTEAD_OF_401_REJECTED",
            returned_http_status=returned_http_status,
        )
    if not payload.get("www_authenticate_empty_elements_accepted", False):
        return _block(gid, "MCP_GO_SDK_RFC9110_EMPTY_WWW_AUTHENTICATE_ELEMENT_REJECTED")
    if "?" in str(payload.get("fallback_authorization_base_url", "")) or not payload.get("legacy_requests_rejected_on_2026_server", False):
        return _block(gid, "MCP_GO_SDK_FALLBACK_AUTH_QUERY_LEAK_OR_LEGACY_REQUEST_ACCEPTED_REJECTED")
    return _ok(
        gid,
        "MCP_GO_SDK_EXPIRY_BEFORE_SCOPES_AND_WWW_AUTHENTICATE_VERIFIED",
        returned_http_status=returned_http_status,
    )


def evaluate_mcp_rust_inband_invalid_params_and_java_list_roots_cursor_guard(payload: dict[str, Any]) -> GuardResult:
    """PR-12: modelcontextprotocol/rust-sdk#1322, #1318, #1342, #1384, #1387 & java-sdk#1275, #1258, #1264."""
    gid = "PR-12"
    jsonrpc_error_code = int(payload.get("jsonrpc_error_code", -32602))
    missing_required_meta = bool(payload.get("missing_required_meta", False))
    http_status = int(payload.get("http_status", 200))
    if jsonrpc_error_code == -32602 and not missing_required_meta and http_status != 200:
        return _block(
            gid,
            "MCP_RUST_SDK_APPLICATION_INVALID_PARAMS_HTTP_400_DOWNGRADE_TRIGGER_REJECTED",
            http_status=http_status,
        )
    next_cursor = payload.get("roots_list_next_cursor", "")
    requested_next_page = bool(payload.get("requested_next_page", False))
    if (next_cursor is None or next_cursor == "") and requested_next_page:
        return _block(
            gid,
            "MCP_JAVA_SDK_EMPTY_NEXT_CURSOR_INFINITE_PAGINATION_REJECTED",
            next_cursor=next_cursor,
        )
    return _ok(
        gid,
        "MCP_RUST_INBAND_INVALID_PARAMS_AND_JAVA_LIST_ROOTS_CURSOR_VERIFIED",
        http_status=http_status,
        next_cursor=next_cursor,
    )


def evaluate_mcp_swift_socket_close_stream_termination_and_csharp_discovery_guard(payload: dict[str, Any]) -> GuardResult:
    """PR-13: modelcontextprotocol/swift-sdk#283, #275, #278, #301, #304 & csharp-sdk#1946, #1943, #1950, #1942."""
    gid = "PR-13"
    if not payload.get("reconnection_enabled", False) and payload.get("peer_closed_connection", True):
        if not payload.get("nw_connection_cancel_called", False):
            return _block(gid, "MCP_SWIFT_SDK_CLOSE_WAIT_SOCKET_LEAK_REJECTED")
    if payload.get("transport_stream_finished", True) and not payload.get("client_message_loop_terminated", False):
        return _block(gid, "MCP_SWIFT_SDK_FINISHED_STREAM_INFINITE_RETRY_LOOP_REJECTED")
    if payload.get("data_url_json_string_coerced_to_data", False):
        return _block(gid, "MCP_SWIFT_SDK_DATA_URL_STRING_COERCION_REJECTED")
    if payload.get("controlled_server_triggered_legacy_initialize_fallback", False):
        return _block(gid, "MCP_CSHARP_SDK_DISCOVERY_TIMEOUT_LEGACY_INITIALIZE_FALLBACK_REJECTED")
    return _ok(
        gid,
        "MCP_SWIFT_SOCKET_CLOSE_STREAM_TERMINATION_AND_CSHARP_DISCOVERY_VERIFIED",
        nw_connection_cancel_called=True,
    )


def evaluate_mcp_ruby_undeclared_capability_and_php_host_origin_reconnect_guard(payload: dict[str, Any]) -> GuardResult:
    """PR-14: modelcontextprotocol/ruby-sdk#611, #600, #596, #626 & php-sdk#589, #588, #592, #591."""
    gid = "PR-14"
    if payload.get("capability_declared", False) is False and int(payload.get("undeclared_method_error_code", 0)) != -32601:
        return _block(
            gid,
            "MCP_RUBY_SDK_UNDECLARED_CAPABILITY_RETURNED_INTERNAL_ERROR_REJECTED",
            error_code=payload.get("undeclared_method_error_code"),
        )
    if not payload.get("single_owner_listen_stream_close", False) or not payload.get("accepts_any_2xx_notification_ack", False):
        return _block(gid, "MCP_RUBY_SDK_STREAM_DOUBLE_CLOSE_OR_NON_202_ACK_REJECTION_REJECTED")
    if not payload.get("php_host_and_origin_validated_independently", False) or not payload.get("php_reconnect_clears_stale_server_metadata", False):
        return _block(gid, "MCP_PHP_SDK_HOST_ORIGIN_COUPLED_OR_STALE_RECONNECT_METADATA_REJECTED")
    return _ok(
        gid,
        "MCP_RUBY_UNDECLARED_CAPABILITY_AND_PHP_HOST_ORIGIN_RECONNECT_VERIFIED",
        undeclared_method_error_code=-32601,
    )


def evaluate_mcp_conformance_dpop_events_and_inspector_load_tsdown_guard(payload: dict[str, Any]) -> GuardResult:
    """PR-15: modelcontextprotocol/conformance#529, #521, #541, #518 & inspector#2743, #2799, #2803, #2807."""
    gid = "PR-15"
    if not payload.get("sep1932_dpop_discovery_signals_verified", False) or not payload.get("sep3415_events_conformance_verified", False):
        return _block(gid, "MCP_CONFORMANCE_MISSING_DPOP_SIGNALS_OR_SEP3415_EVENTS_REJECTED")
    if not payload.get("legacy_initialize_extensions_preserved", False):
        return _block(gid, "MCP_CONFORMANCE_LEGACY_EXTENSIONS_CAPABILITY_DROPPED_REJECTED")
    if str(payload.get("inspector_ts_sdk_version", "")) != "2.4.0" or not payload.get("inspector_tsdown_migrated", False) or not payload.get("inspector_cli_load_mode_enabled", False):
        return _block(
            gid,
            "MCP_INSPECTOR_SDK_DRIFT_OR_MISSING_CLI_LOAD_MODE_REJECTED",
            inspector_ts_sdk_version=payload.get("inspector_ts_sdk_version"),
        )
    return _ok(
        gid,
        "MCP_CONFORMANCE_DPOP_EVENTS_AND_INSPECTOR_LOAD_TSDOWN_VERIFIED",
        inspector_ts_sdk_version="2.4.0",
    )


def evaluate_tau2_v2_leaderboard_split_and_voice_banking_airline_guard(payload: dict[str, Any]) -> GuardResult:
    """PR-16: sierra-research/tau2-bench#641, #626, #614, #649, #594, #591."""
    gid = "PR-16"
    if not payload.get("leaderboard_v2_submissions_split_out", False) or not payload.get("voice_v2_package_ingested", False):
        return _block(gid, "TAU2_V2_LEADERBOARD_SPLIT_OR_VOICE_V2_INGESTION_MISSING_REJECTED")
    rgm_airline_pass1 = float(payload.get("rgm31_airline_pass1_pct", 0.0))
    cayu_banking_pass1 = float(payload.get("cayu_v19r3_banking_pass1_pct", 0.0))
    cayu_unscored = int(payload.get("cayu_v19r3_unscored_count", 1))
    if abs(rgm_airline_pass1 - 84.0) > 1e-6 or abs(cayu_banking_pass1 - 49.74) > 1e-6 or cayu_unscored != 0:
        return _block(
            gid,
            "TAU2_SUBMISSION_METRIC_OR_UNSCORED_TRIAL_DRIFT_REJECTED",
            rgm_airline_pass1=rgm_airline_pass1,
            cayu_banking_pass1=cayu_banking_pass1,
            cayu_unscored=cayu_unscored,
        )
    return _ok(
        gid,
        "TAU2_V2_LEADERBOARD_SPLIT_AND_VOICE_BANKING_AIRLINE_VERIFIED",
        rgm31_airline_pass1_pct=rgm_airline_pass1,
        cayu_v19r3_banking_pass1_pct=cayu_banking_pass1,
    )


STAGE256_GUARD_EVALUATORS: dict[str, Callable[[dict[str, Any]], GuardResult]] = {
    "PR-01": evaluate_x402_v1_networks_filter_and_versioned_requirements_guard,
    "PR-02": evaluate_agentkit_standing_witness_and_spend_preflight_guard,
    "PR-03": evaluate_agentkit_erc20_multicall_fallback_and_cdp_idempotency_guard,
    "PR-04": evaluate_a2a_python_boolean_id_executor_failfast_and_stream_cleanup_guard,
    "PR-05": evaluate_a2a_js_canonicalization_depth_and_nanosecond_task_store_guard,
    "PR-06": evaluate_a2a_go_java_taskstate_unmarshal_and_listtasks_query_guard,
    "PR-07": evaluate_a2a_dotnet_v03_exception_translation_and_push_cleanup_guard,
    "PR-08": evaluate_ucp_rest_idempotency_race_winner_and_rfc9421_ecdsa_guard,
    "PR-09": evaluate_ucp_sdk_discriminator_retyping_max_properties_and_allof_guard,
    "PR-10": evaluate_stripe_action_sha_pinning_plugin_subtree_and_key_cutoff_guard,
    "PR-11": evaluate_mcp_go_sdk_expiry_before_scopes_and_www_authenticate_guard,
    "PR-12": evaluate_mcp_rust_inband_invalid_params_and_java_list_roots_cursor_guard,
    "PR-13": evaluate_mcp_swift_socket_close_stream_termination_and_csharp_discovery_guard,
    "PR-14": evaluate_mcp_ruby_undeclared_capability_and_php_host_origin_reconnect_guard,
    "PR-15": evaluate_mcp_conformance_dpop_events_and_inspector_load_tsdown_guard,
    "PR-16": evaluate_tau2_v2_leaderboard_split_and_voice_banking_airline_guard,
}


def evaluate_stage256_guards(scenarios: dict[str, dict[str, Any]]) -> dict[str, GuardResult]:
    return {gid: fn(scenarios.get(gid, {})) for gid, fn in STAGE256_GUARD_EVALUATORS.items()}
