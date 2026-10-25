"""Stage 258 deterministic protocol security guards (`PR-01..PR-16`).

Covers 68 non-overlapping primary-source PRs across x402 Foundation
(`#3936`, `#3889`, `#3800`), Coinbase AgentKit (`#1525`, `#1527`, `#1538`,
`#1524`, `#1537`, `#1540`), Google A2A Python/JS/Go/Java/.NET SDKs
(`a2a-python#1372..#1317`, `a2a-js#797..#708`, `a2a-go#488..#481`,
`a2a-java#1242..#1230`, `a2a-dotnet#563..#576`), UCP Samples/Python-SDK/
JS-SDK/Conformance (`samples#241..#236`, `python-sdk#86..#79`,
`js-sdk#81/#76/#75`, `conformance#100..#92`), Stripe Agent Toolkit & A2A x402
(`stripe/agent-toolkit#584/#581/#559/#578`, `a2a-x402#130`, `AP2#373`, plus
Stripe MCP `2026-10-31` cutoff), MCP Python/TS/Go/Rust/Ruby/Swift/PHP/Kotlin/
Inspector/Ext-Apps/Registry (`python-sdk#3742..#3749`,
`typescript-sdk#3044..#3051`, `go-sdk#1334/#1327`, `rust-sdk#1311..#1309`,
`ruby-sdk#610..#605`, `swift-sdk#280..#273`, `php-sdk#609..#584`,
`kotlin-sdk#1094..#1032`, `inspector#2730/#2728`, `ext-apps#804/#811`,
`registry#1732/#1716`), and Sierra tau2-bench 2.0 (`#629`, `#627`, `#618`,
`#630`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List


@dataclass(frozen=True)
class GuardEvaluation:
    """Deterministic result from a Stage 258 guard check."""

    scenario_id: str
    passed: bool
    action: str
    reason: str
    http_status: int
    signals: Dict[str, Any]


def evaluate_x402_facilitator_request_and_gas_sponsor_guard(
    payload: Dict[str, Any],
) -> GuardEvaluation:
    """PR-01: x402-foundation/x402#3936, #3889, #3800."""
    payment_payload_obj = bool(payload.get("payment_payload_is_object", False))
    registered_scheme_network = bool(payload.get("registered_scheme_and_network", False))
    invalid_request_status = int(payload.get("invalid_facilitator_request_http_status", 500))
    gas_sponsor_advertised = bool(payload.get("gas_sponsor_advertised", False))
    chain_reader_rpc_configured = bool(payload.get("chain_reader_rpc_configured", False))
    warned_missing_rpc_once = bool(payload.get("warned_missing_rpc_once", False))
    remitbot_decision = str(payload.get("remitbot_pre_settlement_decision", "Clear"))

    if not payment_payload_obj or not registered_scheme_network:
        if invalid_request_status == 400:
            return GuardEvaluation(
                scenario_id="PR-01",
                passed=True,
                action="Send to a human",
                reason="x402 facilitator rejected non-object payload or unregistered scheme/network with HTTP 400 (#3936)",
                http_status=400,
                signals={"invalid_facilitator_request_http_status": 400},
            )
        return GuardEvaluation(
            scenario_id="PR-01",
            passed=False,
            action="Send to a human",
            reason="x402 facilitator threw unhandled HTTP 500 on invalid payload or unregistered scheme (#3936)",
            http_status=500,
            signals={"invalid_facilitator_request_http_status": invalid_request_status},
        )

    if gas_sponsor_advertised and not chain_reader_rpc_configured and not warned_missing_rpc_once:
        return GuardEvaluation(
            scenario_id="PR-01",
            passed=False,
            action="Send to a human",
            reason="x402 EVM gas sponsoring silently skipped permit/approval without rpcUrl warning (#3889)",
            http_status=422,
            signals={"gas_sponsor_advertised": True, "chain_reader_rpc_configured": False},
        )

    if remitbot_decision != "Clear":
        return GuardEvaluation(
            scenario_id="PR-01",
            passed=False,
            action="Send to a human",
            reason=f"RemitBot pre-settlement policy gate blocked or held payment ({remitbot_decision}) (#3800)",
            http_status=403,
            signals={"remitbot_pre_settlement_decision": remitbot_decision},
        )

    return GuardEvaluation(
        scenario_id="PR-01",
        passed=True,
        action="Act automatically",
        reason="x402 facilitator request validated, EVM gas-sponsor rpcUrl verified, and RemitBot policy cleared (#3936/#3889/#3800)",
        http_status=200,
        signals={"remitbot_pre_settlement_decision": "Clear", "invalid_facilitator_request_http_status": 400},
    )


def evaluate_agentkit_automaton_firewall_and_agorean_guard(
    payload: Dict[str, Any],
) -> GuardEvaluation:
    """PR-02: coinbase/agentkit#1525, #1527, #1538, #1524, #1537, #1540."""
    firewall_simulated = bool(payload.get("automaton_firewall_simulated", False))
    firewall_verdict = str(payload.get("automaton_firewall_verdict", "BLOCK"))
    agorean_endpoint_reviewed = bool(payload.get("agorean_endpoint_reviewed", False))
    provider_selected_before_spend = bool(payload.get("provider_selected_before_spend", False))
    analytics_rejection_caught = bool(payload.get("analytics_rejection_caught", False))
    trdefi_read_only = bool(payload.get("trdefi_read_only", False))

    if not firewall_simulated or firewall_verdict != "ALLOW":
        return GuardEvaluation(
            scenario_id="PR-02",
            passed=False,
            action="Send to a human",
            reason="Automaton Pre-Flight AI Firewall blocked or did not simulate Base mainnet transaction (#1525)",
            http_status=403,
            signals={"automaton_firewall_simulated": firewall_simulated, "automaton_firewall_verdict": firewall_verdict},
        )

    if not agorean_endpoint_reviewed or not provider_selected_before_spend:
        return GuardEvaluation(
            scenario_id="PR-02",
            passed=False,
            action="Send to a human",
            reason="AgentKit x402 payment attempted without Agorean endpoint review or pre-spend provider selection (#1527/#1538)",
            http_status=409,
            signals={
                "agorean_endpoint_reviewed": agorean_endpoint_reviewed,
                "provider_selected_before_spend": provider_selected_before_spend,
            },
        )

    if not analytics_rejection_caught or not trdefi_read_only:
        return GuardEvaluation(
            scenario_id="PR-02",
            passed=False,
            action="Send to a human",
            reason="Detached sendAnalyticsEvent() promise lacked rejection handler or TRDEFI mutated state (#1537/#1524)",
            http_status=500,
            signals={"analytics_rejection_caught": analytics_rejection_caught, "trdefi_read_only": trdefi_read_only},
        )

    return GuardEvaluation(
        scenario_id="PR-02",
        passed=True,
        action="Act automatically",
        reason="AgentKit Automaton pre-flight firewall, Agorean review, and analytics rejection handler verified (#1525..#1540)",
        http_status=200,
        signals={"automaton_firewall_verdict": "ALLOW", "analytics_rejection_caught": True},
    )


def evaluate_a2a_python_compat_and_stream_context_guard(
    payload: Dict[str, Any],
) -> GuardEvaluation:
    """PR-03: a2aproject/a2a-python#1372, #1369, #1366, #1337, #1334, #1327, #1317, #1373."""
    v03_last_updated_set = bool(payload.get("v03_last_updated_set_from_status_timestamp", False))
    legacy_states_in_list_filter = bool(payload.get("legacy_states_included_in_list_filter", False))
    v03_jsonrpc_preserves_a2a_error = bool(payload.get("v03_jsonrpc_preserves_a2a_error_codes", False))
    single_consumer_records_failure = bool(payload.get("single_consumer_records_executor_failure", False))
    v03_unset_config_blocks = bool(payload.get("v03_unset_config_defaults_to_blocking", False))
    paused_task_resubscribed_from_shared = bool(payload.get("paused_task_resubscribed_from_shared_stream", False))
    followup_uses_sender_contextvars = bool(payload.get("followup_uses_sender_contextvars", False))

    if not v03_last_updated_set or not legacy_states_in_list_filter or not v03_jsonrpc_preserves_a2a_error:
        return GuardEvaluation(
            scenario_id="PR-03",
            passed=False,
            action="Send to a human",
            reason="a2a-python v0.3 compatibility dropped last_updated, legacy task states, or A2A error codes (#1372/#1337/#1369)",
            http_status=400,
            signals={
                "v03_last_updated_set": v03_last_updated_set,
                "legacy_states_in_list_filter": legacy_states_in_list_filter,
                "v03_jsonrpc_preserves_a2a_error": v03_jsonrpc_preserves_a2a_error,
            },
        )

    if (
        not single_consumer_records_failure
        or not v03_unset_config_blocks
        or not paused_task_resubscribed_from_shared
        or not followup_uses_sender_contextvars
    ):
        return GuardEvaluation(
            scenario_id="PR-03",
            passed=False,
            action="Send to a human",
            reason="a2a-python double-inserted failed task, returned early on v0.3 send, or leaked first-request contextvars (#1366/#1334/#1327/#1317)",
            http_status=409,
            signals={
                "single_consumer_records_failure": single_consumer_records_failure,
                "followup_uses_sender_contextvars": followup_uses_sender_contextvars,
            },
        )

    return GuardEvaluation(
        scenario_id="PR-03",
        passed=True,
        action="Act automatically",
        reason="a2a-python v0.3 migration compatibility, shared stream resubscription, and per-sender contextvars verified (#1372..#1317)",
        http_status=200,
        signals={"v03_last_updated_set": True, "followup_uses_sender_contextvars": True},
    )


def evaluate_a2a_js_rest_query_and_verified_card_cache_guard(
    payload: Dict[str, Any],
) -> GuardEvaluation:
    """PR-04: a2aproject/a2a-js#797, #796, #795, #737, #726, #717, #711, #708."""
    rest_query_preserved = bool(payload.get("rest_endpoint_query_preserved_outside_path", False))
    card_cached_only_after_sig_verify = bool(payload.get("extended_card_cached_only_after_verify", False))
    zero_history_skips_column = bool(payload.get("zero_history_length_skips_db_column", False))
    tenant_preserves_call_context = bool(payload.get("jsonrpc_tenant_preserves_call_context", False))
    v03_push_converted_to_v1_stream = bool(payload.get("v03_push_converted_to_v1_stream_response", False))
    node_engine_supports_cjs_jose = bool(payload.get("node_engine_supports_cjs_jose_v6", False))

    if not rest_query_preserved or not card_cached_only_after_sig_verify:
        return GuardEvaluation(
            scenario_id="PR-04",
            passed=False,
            action="Send to a human",
            reason="a2a-js corrupted REST endpoint query path or cached unverified extended Agent Card (#797/#711)",
            http_status=400,
            signals={
                "rest_query_preserved": rest_query_preserved,
                "card_cached_only_after_sig_verify": card_cached_only_after_sig_verify,
            },
        )

    if (
        not zero_history_skips_column
        or not tenant_preserves_call_context
        or not v03_push_converted_to_v1_stream
        or not node_engine_supports_cjs_jose
    ):
        return GuardEvaluation(
            scenario_id="PR-04",
            passed=False,
            action="Send to a human",
            reason="a2a-js loaded full history for historyLength=0, replaced ServerCallContext, or mismatched Node engine (#795/#708/#726/#796)",
            http_status=422,
            signals={
                "zero_history_skips_column": zero_history_skips_column,
                "tenant_preserves_call_context": tenant_preserves_call_context,
            },
        )

    return GuardEvaluation(
        scenario_id="PR-04",
        passed=True,
        action="Act automatically",
        reason="a2a-js REST query preservation, post-verify card caching, history hints, and tenant context verified (#797..#708)",
        http_status=200,
        signals={"card_cached_only_after_sig_verify": True, "zero_history_skips_column": True},
    )


def evaluate_a2a_go_java_transport_and_logging_guard(
    payload: Dict[str, Any],
) -> GuardEvaluation:
    """PR-05: a2aproject/a2a-go#488, #487, #485, #481 & a2a-java#1242, #1238, #1237, #1230."""
    rest_segments_escaped = bool(payload.get("rest_path_segments_escaped", False))
    cr_only_sse_supported = bool(payload.get("cr_only_sse_line_endings_supported", False))
    in_place_artifact_recovered = bool(payload.get("in_place_artifact_recovered_completely", False))
    head_rejected_on_subscribe = bool(payload.get("head_rejected_before_task_subscribe", False))
    blank_push_config_id_rejected = bool(payload.get("blank_push_config_id_rejected", False))
    payload_logging_masked_truncated = bool(payload.get("payload_logging_masked_and_truncated", False))
    java_actions_sha_pinned = bool(payload.get("java_actions_pinned_to_commit_shas", False))

    if not rest_segments_escaped or not head_rejected_on_subscribe or not blank_push_config_id_rejected:
        return GuardEvaluation(
            scenario_id="PR-05",
            passed=False,
            action="Send to a human",
            reason="a2a-go/a2a-java allowed unescaped REST path injection, HEAD subscription consumption, or blank push config ID (#488/#481/#1242)",
            http_status=400,
            signals={
                "rest_segments_escaped": rest_segments_escaped,
                "head_rejected_on_subscribe": head_rejected_on_subscribe,
                "blank_push_config_id_rejected": blank_push_config_id_rejected,
            },
        )

    if (
        not cr_only_sse_supported
        or not in_place_artifact_recovered
        or not payload_logging_masked_truncated
        or not java_actions_sha_pinned
    ):
        return GuardEvaluation(
            scenario_id="PR-05",
            passed=False,
            action="Send to a human",
            reason="a2a-go/a2a-java dropped CR-only SSE frames, lost artifact parts on metadata update, or logged unmasked payloads (#487/#485/#1238/#1230)",
            http_status=422,
            signals={
                "cr_only_sse_supported": cr_only_sse_supported,
                "payload_logging_masked_truncated": payload_logging_masked_truncated,
            },
        )

    return GuardEvaluation(
        scenario_id="PR-05",
        passed=True,
        action="Act automatically",
        reason="a2a-go and a2a-java REST path escaping, HEAD subscribe guard, CR SSE framing, and masked logging verified (#488..#1230)",
        http_status=200,
        signals={"rest_segments_escaped": True, "head_rejected_on_subscribe": True},
    )


def evaluate_a2a_dotnet_registry_extension_and_push_store_guard(
    payload: Dict[str, Any],
) -> GuardEvaluation:
    """PR-06: a2aproject/a2a-dotnet#563, #564, #570, #571, #573, #576."""
    registry_token_validated = bool(payload.get("extension_registry_token_validated", False))
    foreign_registration_rejected = bool(payload.get("foreign_extension_registration_rejected", False))
    push_store_credentials_encrypted = bool(payload.get("push_store_credentials_encrypted", False))
    push_store_tenant_isolated = bool(payload.get("push_store_tenant_isolated", False))
    durable_sender_deduplicated = bool(payload.get("durable_push_sender_deduplicated", False))
    itk_acts_revision_synced = bool(payload.get("itk_acts_revision_synced", False))

    if not registry_token_validated or not foreign_registration_rejected:
        return GuardEvaluation(
            scenario_id="PR-06",
            passed=False,
            action="Send to a human",
            reason="a2a-dotnet accepted foreign A2AExtensionRegistration without registry token validation (#563/#564)",
            http_status=403,
            signals={
                "registry_token_validated": registry_token_validated,
                "foreign_registration_rejected": foreign_registration_rejected,
            },
        )

    if (
        not push_store_credentials_encrypted
        or not push_store_tenant_isolated
        or not durable_sender_deduplicated
        or not itk_acts_revision_synced
    ):
        return GuardEvaluation(
            scenario_id="PR-06",
            passed=False,
            action="Send to a human",
            reason="a2a-dotnet push store lacked credential encryption/tenant isolation or drifted ITK/ACTS revision (#570/#571/#576)",
            http_status=409,
            signals={
                "push_store_credentials_encrypted": push_store_credentials_encrypted,
                "push_store_tenant_isolated": push_store_tenant_isolated,
            },
        )

    return GuardEvaluation(
        scenario_id="PR-06",
        passed=True,
        action="Act automatically",
        reason="a2a-dotnet registry-aware extension activation, encrypted tenant-isolated push store, and ITK sync verified (#563..#576)",
        http_status=200,
        signals={"registry_token_validated": True, "push_store_tenant_isolated": True},
    )


def evaluate_ucp_samples_shop_id_cart_idempotency_and_sig_error_guard(
    payload: Dict[str, Any],
) -> GuardEvaluation:
    """PR-07: Universal-Commerce-Protocol/samples#241, #240, #239, #238, #237, #236."""
    shop_id_resolved_before_cache = bool(payload.get("shop_id_resolved_before_profile_cache", False))
    complete_checkout_top_level_body = bool(payload.get("complete_checkout_bound_to_spec_body", False))
    no_undocumented_risk_signals = bool(payload.get("no_undocumented_risk_signals_field", False))
    cart_idempotency_scoped_to_op_and_cart = bool(payload.get("cart_idempotency_scoped_to_op_and_cart", False))
    sig_failure_uses_ucp_error_envelope = bool(payload.get("signature_failure_uses_ucp_error_envelope", False))

    if not shop_id_resolved_before_cache or not complete_checkout_top_level_body or not no_undocumented_risk_signals:
        return GuardEvaluation(
            scenario_id="PR-07",
            passed=False,
            action="Send to a human",
            reason="UCP sample server cached literal {{SHOP_ID}} placeholder or required non-spec risk_signals wrapper (#241/#240)",
            http_status=400,
            signals={
                "shop_id_resolved_before_cache": shop_id_resolved_before_cache,
                "complete_checkout_top_level_body": complete_checkout_top_level_body,
            },
        )

    if not cart_idempotency_scoped_to_op_and_cart or not sig_failure_uses_ucp_error_envelope:
        return GuardEvaluation(
            scenario_id="PR-07",
            passed=False,
            action="Send to a human",
            reason="UCP CartService collided body-less Cancel Cart idempotency across carts or emitted FastAPI detail on signature error (#239/#238/#237)",
            http_status=409,
            signals={
                "cart_idempotency_scoped_to_op_and_cart": cart_idempotency_scoped_to_op_and_cart,
                "sig_failure_uses_ucp_error_envelope": sig_failure_uses_ucp_error_envelope,
            },
        )

    return GuardEvaluation(
        scenario_id="PR-07",
        passed=True,
        action="Act automatically",
        reason="UCP samples shop_id substitution, Complete Checkout body binding, per-cart idempotency, and error envelope verified (#241..#236)",
        http_status=200,
        signals={"shop_id_resolved_before_cache": True, "cart_idempotency_scoped_to_op_and_cart": True},
    )


def evaluate_ucp_sdk_preprocess_and_conformance_pin_guard(
    payload: Dict[str, Any],
) -> GuardEvaluation:
    """PR-08: Universal-Commerce-Protocol/python-sdk#86, #81, #80, #79, js-sdk#81, #76, #75 & conformance#100, #96, #94, #92."""
    properties_dict_expanded_safely = bool(payload.get("properties_dict_expanded_without_keyword_collision", False))
    entity_local_refs_resolved_before_inline = bool(payload.get("entity_local_refs_resolved_before_inlining", False))
    extension_op_schemas_generated = bool(payload.get("extension_operation_schemas_generated", False))
    js_payment_auth_schema_included = bool(payload.get("js_payment_authentication_schema_included", False))
    conformance_sdk_ref_pinned = bool(payload.get("conformance_sdk_checkout_and_version_pinned", False))
    absl_flags_passed_to_runner = bool(payload.get("conformance_absl_flags_passed_to_runner", False))

    if (
        not properties_dict_expanded_safely
        or not entity_local_refs_resolved_before_inline
        or not extension_op_schemas_generated
    ):
        return GuardEvaluation(
            scenario_id="PR-08",
            passed=False,
            action="Send to a human",
            reason="UCP Python SDK corrupted keyword-named properties, left broken #/$defs/version refs, or omitted extension request schemas (#86/#79/#80/#81)",
            http_status=422,
            signals={
                "properties_dict_expanded_safely": properties_dict_expanded_safely,
                "entity_local_refs_resolved_before_inline": entity_local_refs_resolved_before_inline,
            },
        )

    if not js_payment_auth_schema_included or not conformance_sdk_ref_pinned or not absl_flags_passed_to_runner:
        return GuardEvaluation(
            scenario_id="PR-08",
            passed=False,
            action="Send to a human",
            reason="UCP JS SDK omitted payment_authentication.json or conformance used unpinned python-sdk / invalid pytest absl flags (#81/#100/#96/#94)",
            http_status=409,
            signals={
                "js_payment_auth_schema_included": js_payment_auth_schema_included,
                "conformance_sdk_ref_pinned": conformance_sdk_ref_pinned,
            },
        )

    return GuardEvaluation(
        scenario_id="PR-08",
        passed=True,
        action="Act automatically",
        reason="UCP Python/JS SDK schema preprocessing, payment_authentication generation, and conformance SDK pinning verified (#86..#92)",
        http_status=200,
        signals={"entity_local_refs_resolved_before_inline": True, "conformance_sdk_ref_pinned": True},
    )


def evaluate_stripe_proxy_metadata_worker_loop_and_actions_key_guard(
    payload: Dict[str, Any],
) -> GuardEvaluation:
    """PR-09: stripe/agent-toolkit#584, #581, #559, #578 + a2a-x402#130 + AP2#373 + Stripe MCP 2026-10-31 cutoff."""
    proxy_preserves_tool_metadata = bool(payload.get("local_proxy_preserves_remote_tool_metadata", False))
    worker_thread_sync_tool_safe = bool(payload.get("worker_thread_without_event_loop_supported", False))
    deprecated_actions_key_blocked = bool(payload.get("deprecated_v06_actions_key_warned_or_rejected", False))
    payment_timeout_positive_finite = bool(payload.get("a2a_x402_payment_timeout_positive_finite", False))
    ap2_actions_sha_pinned = bool(payload.get("ap2_actions_pinned_to_commit_shas", False))
    stripe_credential_kind = str(payload.get("stripe_credential_kind", "sk_live"))
    eval_date = str(payload.get("evaluation_date", "2026-10-25"))

    if stripe_credential_kind not in ("rk_live", "rk_test", "oauth_access_token"):
        return GuardEvaluation(
            scenario_id="PR-09",
            passed=False,
            action="Send to a human",
            reason=f"Legacy Stripe key '{stripe_credential_kind}' rejected under 2026-10-31 / 2026-11-30 MCP migration cutoff (as of {eval_date})",
            http_status=401,
            signals={"stripe_credential_kind": stripe_credential_kind},
        )

    if not proxy_preserves_tool_metadata or not worker_thread_sync_tool_safe or not deprecated_actions_key_blocked:
        return GuardEvaluation(
            scenario_id="PR-09",
            passed=False,
            action="Send to a human",
            reason="Stripe Agent Toolkit dropped remote MCP tool annotations, crashed on worker thread without event loop, or failed open on deprecated 'actions' key (#584/#581/#559)",
            http_status=403,
            signals={
                "proxy_preserves_tool_metadata": proxy_preserves_tool_metadata,
                "deprecated_actions_key_blocked": deprecated_actions_key_blocked,
            },
        )

    if not payment_timeout_positive_finite or not ap2_actions_sha_pinned:
        return GuardEvaluation(
            scenario_id="PR-09",
            passed=False,
            action="Send to a human",
            reason="a2a-x402 accepted invalid payment timeout or AP2 CI used unpinned GitHub Action tags (#130/#373)",
            http_status=422,
            signals={"payment_timeout_positive_finite": payment_timeout_positive_finite, "ap2_actions_sha_pinned": ap2_actions_sha_pinned},
        )

    return GuardEvaluation(
        scenario_id="PR-09",
        passed=True,
        action="Act automatically",
        reason="Stripe MCP proxy metadata, worker-thread event loop, deprecated 'actions' fail-open guard, and a2a-x402/AP2 checks verified (#584..#373)",
        http_status=200,
        signals={"stripe_credential_kind": stripe_credential_kind, "deprecated_actions_key_blocked": True},
    )


def evaluate_mcp_python_stdio_error_and_timeout_isolation_guard(
    payload: Dict[str, Any],
) -> GuardEvaluation:
    """PR-10: modelcontextprotocol/python-sdk#3742, #3741, #3740, #3749."""
    unparseable_stdio_answered_with_jsonrpc_error = bool(
        payload.get("unparseable_stdio_answered_with_jsonrpc_error", False)
    )
    http_read_timeout_isolated_to_request = bool(payload.get("http_read_timeout_isolated_from_siblings", False))
    reserved_param_prefix_collision_free = bool(payload.get("reserved_param_prefix_collision_free", False))
    non_utf8_percent_escape_rejected = bool(payload.get("non_utf8_percent_escape_rejected_in_uri_template", False))

    if not unparseable_stdio_answered_with_jsonrpc_error or not http_read_timeout_isolated_to_request:
        return GuardEvaluation(
            scenario_id="PR-10",
            passed=False,
            action="Send to a human",
            reason="MCP Python SDK dropped unparseable stdio line without JSON-RPC error or let one HTTP ReadTimeout cancel sibling requests (#3742/#3741)",
            http_status=504,
            signals={
                "unparseable_stdio_answered_with_jsonrpc_error": unparseable_stdio_answered_with_jsonrpc_error,
                "http_read_timeout_isolated_to_request": http_read_timeout_isolated_to_request,
            },
        )

    if not reserved_param_prefix_collision_free or not non_utf8_percent_escape_rejected:
        return GuardEvaluation(
            scenario_id="PR-10",
            passed=False,
            action="Send to a human",
            reason="MCP Python SDK collided ArgModelBase prefixed tool parameter names or matched %FF as U+FFFD in UriTemplate (#3740/#3749)",
            http_status=400,
            signals={
                "reserved_param_prefix_collision_free": reserved_param_prefix_collision_free,
                "non_utf8_percent_escape_rejected": non_utf8_percent_escape_rejected,
            },
        )

    return GuardEvaluation(
        scenario_id="PR-10",
        passed=True,
        action="Act automatically",
        reason="MCP Python SDK stdio JSON-RPC error reply, sibling HTTP timeout isolation, parameter prefixing, and UTF-8 URI matching verified (#3742..#3749)",
        http_status=200,
        signals={"http_read_timeout_isolated_to_request": True, "non_utf8_percent_escape_rejected": True},
    )


def evaluate_mcp_ts_zero_request_id_and_same_read_progress_guard(
    payload: Dict[str, Any],
) -> GuardEvaluation:
    """PR-11: modelcontextprotocol/typescript-sdk#3044, #3023, #3051, #3088, #3084."""
    request_id_zero_treated_as_valid = bool(payload.get("request_id_zero_treated_as_real_id", False))
    same_read_progress_delivered_before_delete = bool(
        payload.get("same_read_progress_delivered_before_response_cleanup", False)
    )
    zod_upper_bound_patch_retained = bool(payload.get("zod_upper_bound_patch_version_retained", False))

    if not request_id_zero_treated_as_valid or not same_read_progress_delivered_before_delete:
        return GuardEvaluation(
            scenario_id="PR-11",
            passed=False,
            action="Send to a human",
            reason="MCP TypeScript SDK treated request id 0 as falsy or dropped progress notification sharing a read with its response (#3044/#3023)",
            http_status=400,
            signals={
                "request_id_zero_treated_as_valid": request_id_zero_treated_as_valid,
                "same_read_progress_delivered_before_delete": same_read_progress_delivered_before_delete,
            },
        )

    if not zod_upper_bound_patch_retained:
        return GuardEvaluation(
            scenario_id="PR-11",
            passed=False,
            action="Send to a human",
            reason="MCP TypeScript SDK codemod discarded patch version when classifying Zod upper bounds (#3051)",
            http_status=422,
            signals={"zod_upper_bound_patch_retained": False},
        )

    return GuardEvaluation(
        scenario_id="PR-11",
        passed=True,
        action="Act automatically",
        reason="MCP TypeScript SDK request id 0 handling, same-read progress delivery, and Zod patch-bound classification verified (#3044/#3023/#3051)",
        http_status=200,
        signals={"request_id_zero_treated_as_valid": True, "same_read_progress_delivered_before_delete": True},
    )


def evaluate_mcp_go_rust_discover_s256_and_body_bound_guard(
    payload: Dict[str, Any],
) -> GuardEvaluation:
    """PR-12: modelcontextprotocol/go-sdk#1334, #1327 & rust-sdk#1311, #1310, #1309, #1314, #1316."""
    stdio_discover_probe_bounded = bool(payload.get("go_stdio_discover_probe_bounded", False))
    auth_server_requires_s256_pkce = bool(payload.get("go_auth_server_meta_requires_s256_pkce", False))
    rust_non_streaming_body_bounded = bool(payload.get("rust_non_streaming_http_response_bounded", False))
    progress_dispatcher_lock_off_await = bool(payload.get("rust_progress_dispatcher_lock_off_await", False))
    oauth_example_discoverable = bool(payload.get("rust_complex_auth_oauth_discoverable", False))

    if not stdio_discover_probe_bounded or not auth_server_requires_s256_pkce:
        return GuardEvaluation(
            scenario_id="PR-12",
            passed=False,
            action="Send to a human",
            reason="MCP Go SDK hung on stdio server/discover probe or accepted plain-only PKCE authorization server (#1334/#1327)",
            http_status=401,
            signals={
                "stdio_discover_probe_bounded": stdio_discover_probe_bounded,
                "auth_server_requires_s256_pkce": auth_server_requires_s256_pkce,
            },
        )

    if not rust_non_streaming_body_bounded or not progress_dispatcher_lock_off_await or not oauth_example_discoverable:
        return GuardEvaluation(
            scenario_id="PR-12",
            passed=False,
            action="Send to a human",
            reason="MCP Rust SDK left non-streaming HTTP body unbounded, held ProgressDispatcher lock across await, or broke OAuth discovery (#1311/#1310/#1309)",
            http_status=413,
            signals={
                "rust_non_streaming_body_bounded": rust_non_streaming_body_bounded,
                "progress_dispatcher_lock_off_await": progress_dispatcher_lock_off_await,
            },
        )

    return GuardEvaluation(
        scenario_id="PR-12",
        passed=True,
        action="Act automatically",
        reason="MCP Go/Rust bounded stdio discover probe, S256 PKCE enforcement, HTTP body cap, and lock-free progress dispatch verified (#1334..#1309)",
        http_status=200,
        signals={"auth_server_requires_s256_pkce": True, "rust_non_streaming_body_bounded": True},
    )


def evaluate_mcp_ruby_swift_accept_id_and_transport_guard(
    payload: Dict[str, Any],
) -> GuardEvaluation:
    """PR-13: modelcontextprotocol/ruby-sdk#610, #608, #607, #605, #621 & swift-sdk#280, #279, #276, #273."""
    empty_accept_members_ignored = bool(payload.get("ruby_empty_accept_header_members_ignored", False))
    arbitrary_string_id_accepted = bool(payload.get("ruby_arbitrary_string_request_id_accepted", False))
    unknown_error_id_omitted = bool(payload.get("ruby_unknown_error_id_omitted", False))
    null_request_id_rejected_32600 = bool(payload.get("ruby_null_request_id_rejected_with_32600", False))
    swift_windows_and_capabilities_ready = bool(payload.get("swift_windows_transport_and_nested_capabilities_ready", False))

    if not empty_accept_members_ignored or not null_request_id_rejected_32600:
        return GuardEvaluation(
            scenario_id="PR-13",
            passed=False,
            action="Send to a human",
            reason="MCP Ruby SDK crashed with HTTP 500 on empty Accept member or executed request with null id (#610/#605)",
            http_status=400,
            signals={
                "empty_accept_members_ignored": empty_accept_members_ignored,
                "null_request_id_rejected_32600": null_request_id_rejected_32600,
            },
        )

    if not arbitrary_string_id_accepted or not unknown_error_id_omitted or not swift_windows_and_capabilities_ready:
        return GuardEvaluation(
            scenario_id="PR-13",
            passed=False,
            action="Send to a human",
            reason="MCP Ruby/Swift SDK rejected valid URN/colon request IDs, emitted null error id, or lacked nested capability modeling (#608/#607/#276/#280)",
            http_status=422,
            signals={
                "arbitrary_string_id_accepted": arbitrary_string_id_accepted,
                "unknown_error_id_omitted": unknown_error_id_omitted,
            },
        )

    return GuardEvaluation(
        scenario_id="PR-13",
        passed=True,
        action="Act automatically",
        reason="MCP Ruby and Swift Accept header parsing, null-id rejection, string ID support, and transport capabilities verified (#610..#273)",
        http_status=200,
        signals={"null_request_id_rejected_32600": True, "empty_accept_members_ignored": True},
    )


def evaluate_mcp_php_nested_empty_object_and_session_lock_guard(
    payload: Dict[str, Any],
) -> GuardEvaluation:
    """PR-14: modelcontextprotocol/php-sdk#609, #604, #585, #584, #590."""
    nested_empty_object_accepted = bool(payload.get("php_nested_empty_object_accepted_in_tool_args", False))
    structured_content_only_supported = bool(payload.get("php_structured_content_only_without_duplicate_text", False))
    timed_out_client_requests_expired = bool(payload.get("php_timed_out_client_requests_expired", False))
    per_session_lock_enabled = bool(payload.get("php_per_session_lock_for_concurrent_requests", False))

    if not nested_empty_object_accepted or not timed_out_client_requests_expired:
        return GuardEvaluation(
            scenario_id="PR-14",
            passed=False,
            action="Send to a human",
            reason="MCP PHP SDK rejected nested {} decoded as [] in tool arguments or leaked timed-out client requests in pendingRequests (#609/#585)",
            http_status=400,
            signals={
                "nested_empty_object_accepted": nested_empty_object_accepted,
                "timed_out_client_requests_expired": timed_out_client_requests_expired,
            },
        )

    if not structured_content_only_supported or not per_session_lock_enabled:
        return GuardEvaluation(
            scenario_id="PR-14",
            passed=False,
            action="Send to a human",
            reason="MCP PHP SDK raced concurrent session mutations without lock or duplicated structuredContent as text when opted out (#584/#604)",
            http_status=409,
            signals={
                "structured_content_only_supported": structured_content_only_supported,
                "per_session_lock_enabled": per_session_lock_enabled,
            },
        )

    return GuardEvaluation(
        scenario_id="PR-14",
        passed=True,
        action="Act automatically",
        reason="MCP PHP SDK nested empty object coercion, timed-out client request expiry, and per-session lock verified (#609..#584)",
        http_status=200,
        signals={"nested_empty_object_accepted": True, "per_session_lock_enabled": True},
    )


def evaluate_mcp_kotlin_inspector_ext_apps_and_registry_guard(
    payload: Dict[str, Any],
) -> GuardEvaluation:
    """PR-15: modelcontextprotocol/kotlin-sdk#1094..#1032, inspector#2730/#2728, ext-apps#804/#811, registry#1732/#1716."""
    kotlin_read_buffer_resumes = bool(payload.get("kotlin_read_buffer_resumes_newline_search", False))
    kotlin_connect_sends_protocol_version = bool(payload.get("kotlin_connect_sets_negotiated_protocol_version", False))
    kotlin_idle_sessions_expired_and_capped = bool(payload.get("kotlin_idle_sessions_expired_and_capped", False))
    kotlin_null_task_ttl_serialized = bool(payload.get("kotlin_unlimited_task_ttl_written_as_null", False))
    inspector_403_listen_not_retried = bool(payload.get("inspector_http_403_subscriptions_listen_not_retried", False))
    ext_apps_listener_snapshot_taken = bool(payload.get("ext_apps_listener_snapshot_before_singular_handler", False))
    registry_ownership_checked_before_tx = bool(payload.get("registry_ownership_validated_before_db_tx", False))

    if (
        not kotlin_read_buffer_resumes
        or not kotlin_connect_sends_protocol_version
        or not kotlin_idle_sessions_expired_and_capped
        or not kotlin_null_task_ttl_serialized
    ):
        return GuardEvaluation(
            scenario_id="PR-15",
            passed=False,
            action="Send to a human",
            reason="MCP Kotlin SDK rescanned ReadBuffer from 0, omitted negotiated MCP-Protocol-Version/null Task.ttl, or leaked unbounded idle sessions (#1094/#1091/#1089/#1032)",
            http_status=400,
            signals={
                "kotlin_connect_sends_protocol_version": kotlin_connect_sends_protocol_version,
                "kotlin_idle_sessions_expired_and_capped": kotlin_idle_sessions_expired_and_capped,
            },
        )

    if (
        not inspector_403_listen_not_retried
        or not ext_apps_listener_snapshot_taken
        or not registry_ownership_checked_before_tx
    ):
        return GuardEvaluation(
            scenario_id="PR-15",
            passed=False,
            action="Send to a human",
            reason="MCP Inspector retried HTTP 403 subscriptions/listen, ext-apps mutated listeners mid-dispatch, or Registry opened DB tx before ownership check (#2730/#804/#1732)",
            http_status=409,
            signals={
                "inspector_403_listen_not_retried": inspector_403_listen_not_retried,
                "registry_ownership_checked_before_tx": registry_ownership_checked_before_tx,
            },
        )

    return GuardEvaluation(
        scenario_id="PR-15",
        passed=True,
        action="Act automatically",
        reason="MCP Kotlin SDK session/buffer/version guards, Inspector 403 listen handling, ext-apps listener snapshot, and Registry pre-tx ownership check verified (#1094..#1732)",
        http_status=200,
        signals={"kotlin_idle_sessions_expired_and_capped": True, "registry_ownership_checked_before_tx": True},
    )


def evaluate_tau2_authority_gate_and_duplex_voice_turn_guard(
    payload: Dict[str, Any],
) -> GuardEvaluation:
    """PR-16: sierra-research/tau2-bench#629, #627, #618, #630."""
    customer_authority_verified = bool(payload.get("tau_authority_customer_authorization_verified", False))
    unauthorized_mutation_blocked = bool(payload.get("unauthorized_mutation_blocked_and_reported", False))
    ai_rudder_dedupes_turn_writes = bool(payload.get("ai_rudder_prevents_duplicate_tool_writes_in_turn", False))
    barge_in_history_corrected = bool(payload.get("barge_in_history_corrected_by_playback_progress", False))
    gemini_live_rotates_audio_on_turn = bool(payload.get("gemini_live_rotates_audio_at_turn_complete", False))
    tau_naming_citations_canonical = bool(payload.get("tau_i18n_and_tau_entity_citations_canonical", False))

    if not customer_authority_verified or not unauthorized_mutation_blocked:
        return GuardEvaluation(
            scenario_id="PR-16",
            passed=False,
            action="Send to a human",
            reason="tau-Authority check failed: agent attempted refund/cancellation/booking change beyond customer authority (#629)",
            http_status=403,
            signals={
                "customer_authority_verified": customer_authority_verified,
                "unauthorized_mutation_blocked": unauthorized_mutation_blocked,
            },
        )

    if (
        not ai_rudder_dedupes_turn_writes
        or not barge_in_history_corrected
        or not gemini_live_rotates_audio_on_turn
        or not tau_naming_citations_canonical
    ):
        return GuardEvaluation(
            scenario_id="PR-16",
            passed=False,
            action="Send to a human",
            reason="tau2-bench voice harness duplicated intra-turn tool writes, desynced barge-in history, or stalled Gemini Live across turn_complete (#627/#618/#630)",
            http_status=409,
            signals={
                "ai_rudder_dedupes_turn_writes": ai_rudder_dedupes_turn_writes,
                "gemini_live_rotates_audio_on_turn": gemini_live_rotates_audio_on_turn,
            },
        )

    return GuardEvaluation(
        scenario_id="PR-16",
        passed=True,
        action="Act automatically",
        reason="tau-Authority customer authorization gate, AI Rudder intra-turn write deduplication, and Gemini Live turn rotation verified (#629/#627/#618/#630)",
        http_status=200,
        signals={"customer_authority_verified": True, "gemini_live_rotates_audio_on_turn": True},
    )


STAGE258_GUARD_EVALUATORS: Dict[str, Callable[[Dict[str, Any]], GuardEvaluation]] = {
    "PR-01": evaluate_x402_facilitator_request_and_gas_sponsor_guard,
    "PR-02": evaluate_agentkit_automaton_firewall_and_agorean_guard,
    "PR-03": evaluate_a2a_python_compat_and_stream_context_guard,
    "PR-04": evaluate_a2a_js_rest_query_and_verified_card_cache_guard,
    "PR-05": evaluate_a2a_go_java_transport_and_logging_guard,
    "PR-06": evaluate_a2a_dotnet_registry_extension_and_push_store_guard,
    "PR-07": evaluate_ucp_samples_shop_id_cart_idempotency_and_sig_error_guard,
    "PR-08": evaluate_ucp_sdk_preprocess_and_conformance_pin_guard,
    "PR-09": evaluate_stripe_proxy_metadata_worker_loop_and_actions_key_guard,
    "PR-10": evaluate_mcp_python_stdio_error_and_timeout_isolation_guard,
    "PR-11": evaluate_mcp_ts_zero_request_id_and_same_read_progress_guard,
    "PR-12": evaluate_mcp_go_rust_discover_s256_and_body_bound_guard,
    "PR-13": evaluate_mcp_ruby_swift_accept_id_and_transport_guard,
    "PR-14": evaluate_mcp_php_nested_empty_object_and_session_lock_guard,
    "PR-15": evaluate_mcp_kotlin_inspector_ext_apps_and_registry_guard,
    "PR-16": evaluate_tau2_authority_gate_and_duplex_voice_turn_guard,
}


def evaluate_stage258_guards(scenarios: List[Dict[str, Any]]) -> List[GuardEvaluation]:
    """Evaluate a list of Stage 258 scenarios deterministically."""
    results: List[GuardEvaluation] = []
    for item in scenarios:
        sid = str(item.get("scenario_id", ""))
        evaluator = STAGE258_GUARD_EVALUATORS.get(sid)
        if evaluator is None:
            raise ValueError(f"Unknown Stage 258 scenario_id: {sid}")
        results.append(evaluator(item.get("payload", {})))
    return results
