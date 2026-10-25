"""Stage 260 deterministic protocol security guards (`PR-01..PR-16`).

Covers 20 non-overlapping primary-source PRs across x402 Foundation
(`#3940`, `#3939`, `#3938`), Coinbase AgentKit (`#1522`, `#1513`), Google A2A
Java/Python/Go SDKs (`a2a-java#1229`, `a2a-java#1227`, `a2a-python#1312`,
`a2a-go#476`), UCP Schema/Python-SDK/JS-SDK/Conformance (`ucp-schema#66`,
`python-sdk#71`, `js-sdk#57`, `conformance#107`, `conformance#106`), Stripe
Agent Toolkit & Stripe AI (`stripe/agent-toolkit#532`, `stripe/ai#586`, plus
Stripe MCP `2026-10-31` -> `2026-11-30` credential cutoff), MCP C#/Registry/
Kotlin/Rust/Java SDKs (`csharp-sdk#1957`, `csharp-sdk#1956`, `registry#1734`,
`kotlin-sdk#1057`, `rust-sdk#1302`, `java-sdk#1204`), and Sierra tau2-bench
2.0.0 (`#617`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List


@dataclass(frozen=True)
class GuardEvaluation:
    """Deterministic result from a Stage 260 guard check."""

    scenario_id: str
    passed: bool
    action: str
    reason: str
    http_status: int
    signals: Dict[str, Any]


def evaluate_x402_requests_payment_retry_body_replay_guard(
    payload: Dict[str, Any],
) -> GuardEvaluation:
    """PR-01: x402-foundation/x402#3940 (Python requests payment-retry body replay)."""
    body_kind = str(payload.get("request_body_kind", "bytes"))
    materialized_before_initial_send = bool(
        payload.get("one_shot_body_materialized_to_bytes_upfront", False)
    )
    transfer_encoding_chunked_dropped = bool(
        payload.get("transfer_encoding_chunked_dropped_for_one_shot", False)
    )
    paid_retry_bytes_match_initial = bool(
        payload.get("paid_retry_body_bytes_equal_initial_send", False)
    )

    is_one_shot = body_kind in {"generator", "file", "bytes_io"}
    if is_one_shot and (
        not materialized_before_initial_send
        or not transfer_encoding_chunked_dropped
        or not paid_retry_bytes_match_initial
    ):
        return GuardEvaluation(
            scenario_id="PR-01",
            passed=False,
            action="Send to a human",
            reason=(
                "x402 Python requests adapter exhausted generator/file body on initial 402 send "
                "and sent empty body or hung Content-Length on paid retry (#3940)"
            ),
            http_status=422,
            signals={
                "request_body_kind": body_kind,
                "one_shot_body_materialized_to_bytes_upfront": materialized_before_initial_send,
                "paid_retry_body_bytes_equal_initial_send": paid_retry_bytes_match_initial,
            },
        )

    if not paid_retry_bytes_match_initial:
        return GuardEvaluation(
            scenario_id="PR-01",
            passed=False,
            action="Send to a human",
            reason="x402 paid retry body diverged from initial send (#3940)",
            http_status=400,
            signals={"paid_retry_body_bytes_equal_initial_send": False},
        )

    return GuardEvaluation(
        scenario_id="PR-01",
        passed=True,
        action="Act automatically",
        reason=(
            "x402 Python requests adapter materialized one-shot file/generator body upfront, "
            "pinned Content-Length, and replayed identical bytes on PAYMENT-SIGNATURE retry (#3940)"
        ),
        http_status=200,
        signals={
            "request_body_kind": body_kind,
            "paid_retry_body_bytes_equal_initial_send": True,
        },
    )


def evaluate_x402_go_batch_settlement_refund_and_prior_process_guard(
    payload: Dict[str, Any],
) -> GuardEvaluation:
    """PR-02: x402-foundation/x402#3939 (Go batch-settlement refund & prior-process claims)."""
    refund_sets_pending_settle = bool(payload.get("refund_with_claims_sets_pending_settle", False))
    settle_job_runs_when_pending_false = bool(
        payload.get("settle_job_calls_facilitator_when_pending_settle_false", False)
    )
    nothing_to_settle_returns_empty_tx = bool(
        payload.get("err_nothing_to_settle_returns_empty_tx_not_error", False)
    )
    stop_flush_calls_settle_when_zero_claimed = bool(
        payload.get("stop_with_flush_settles_even_when_zero_claimed", False)
    )

    if not refund_sets_pending_settle or not settle_job_runs_when_pending_false:
        return GuardEvaluation(
            scenario_id="PR-02",
            passed=False,
            action="Send to a human",
            reason=(
                "x402 Go BatchSettlementChannelManager stranded refund/prior-process claims by "
                "skipping runSettleJob when in-memory pendingSettle was false (#3939)"
            ),
            http_status=409,
            signals={
                "refund_with_claims_sets_pending_settle": refund_sets_pending_settle,
                "settle_job_calls_facilitator_when_pending_settle_false": settle_job_runs_when_pending_false,
            },
        )

    if not nothing_to_settle_returns_empty_tx or not stop_flush_calls_settle_when_zero_claimed:
        return GuardEvaluation(
            scenario_id="PR-02",
            passed=False,
            action="Send to a human",
            reason=(
                "x402 Go BatchSettlementChannelManager failed on ErrNothingToSettle or skipped "
                "Settle during Stop(Flush: true) (#3939)"
            ),
            http_status=422,
            signals={
                "err_nothing_to_settle_returns_empty_tx_not_error": nothing_to_settle_returns_empty_tx,
                "stop_with_flush_settles_even_when_zero_claimed": stop_flush_calls_settle_when_zero_claimed,
            },
        )

    return GuardEvaluation(
        scenario_id="PR-02",
        passed=True,
        action="Act automatically",
        reason=(
            "x402 Go BatchSettlementChannelManager settles refund/prior-process claims on every tick "
            "and normalizes ErrNothingToSettle to empty SettleResult (#3939)"
        ),
        http_status=200,
        signals={
            "settle_job_calls_facilitator_when_pending_settle_false": True,
            "err_nothing_to_settle_returns_empty_tx_not_error": True,
        },
    )


def evaluate_x402_go_facilitator_verify_error_response_guard(
    payload: Dict[str, Any],
) -> GuardEvaluation:
    """PR-03: x402-foundation/x402#3938 (Go facilitator /verify returns 200 isValid:false)."""
    verify_error_mapped_to_200_is_valid_false = bool(
        payload.get("verify_error_mapped_to_http_200_is_valid_false", False)
    )
    includes_invalid_reason_and_payer = bool(
        payload.get("verify_response_includes_invalid_reason_and_payer", False)
    )
    non_verify_error_returns_500 = bool(
        payload.get("non_verify_error_preserves_http_500", False)
    )
    uses_nonexistent_ve_reason_field = bool(
        payload.get("uses_nonexistent_ve_reason_or_network_field", False)
    )

    if not verify_error_mapped_to_200_is_valid_false or not includes_invalid_reason_and_payer:
        return GuardEvaluation(
            scenario_id="PR-03",
            passed=False,
            action="Send to a human",
            reason=(
                "x402 Go facilitator /verify returned HTTP 500 {'error'} instead of HTTP 200 "
                "VerifyResponse{isValid:false, invalidReason, payer} (#3938)"
            ),
            http_status=500,
            signals={
                "verify_error_mapped_to_http_200_is_valid_false": verify_error_mapped_to_200_is_valid_false,
                "verify_response_includes_invalid_reason_and_payer": includes_invalid_reason_and_payer,
            },
        )

    if not non_verify_error_returns_500 or uses_nonexistent_ve_reason_field:
        return GuardEvaluation(
            scenario_id="PR-03",
            passed=False,
            action="Send to a human",
            reason="x402 Go facilitator /verify masked transport error or referenced nonexistent ve.Reason (#3938)",
            http_status=422,
            signals={
                "non_verify_error_preserves_http_500": non_verify_error_returns_500,
                "uses_nonexistent_ve_reason_or_network_field": uses_nonexistent_ve_reason_field,
            },
        )

    return GuardEvaluation(
        scenario_id="PR-03",
        passed=True,
        action="Act automatically",
        reason=(
            "x402 Go facilitator writeVerifyError maps *x402.VerifyError to HTTP 200 "
            "VerifyResponse{IsValid:false, InvalidReason, InvalidMessage, Payer} (#3938)"
        ),
        http_status=200,
        signals={"verify_error_mapped_to_http_200_is_valid_false": True},
    )


def evaluate_agentkit_x402_doctor_preflight_guard(
    payload: Dict[str, Any],
) -> GuardEvaluation:
    """PR-04: coinbase/agentkit#1522 (x402 Doctor preflight_x402_endpoint action provider)."""
    preflight_executed = bool(payload.get("preflight_x402_endpoint_executed", False))
    preflight_verdict = str(payload.get("preflight_verdict", "no_go"))
    preflight_fee_usdc = float(payload.get("preflight_fee_usdc", 0.01))
    wallet_network = str(payload.get("wallet_network", "unknown"))
    endpoint_network = str(payload.get("endpoint_network", "unknown"))

    if not preflight_executed or preflight_verdict not in {"go", "caution"}:
        return GuardEvaluation(
            scenario_id="PR-04",
            passed=False,
            action="Send to a human",
            reason=(
                f"AgentKit x402 Doctor preflight missing or returned '{preflight_verdict}' "
                "before retry_http_request_with_x402 (#1522)"
            ),
            http_status=403,
            signals={"preflight_executed": preflight_executed, "preflight_verdict": preflight_verdict},
        )

    if preflight_fee_usdc > 0.002 or wallet_network != endpoint_network or wallet_network not in {
        "base-mainnet",
        "solana-mainnet",
    }:
        return GuardEvaluation(
            scenario_id="PR-04",
            passed=False,
            action="Send to a human",
            reason=(
                "AgentKit x402 Doctor preflight fee exceeded $0.002 USDC cap or mismatched "
                "Base/Solana mainnet wallet network (#1522)"
            ),
            http_status=422,
            signals={
                "preflight_fee_usdc": preflight_fee_usdc,
                "wallet_network": wallet_network,
                "endpoint_network": endpoint_network,
            },
        )

    return GuardEvaluation(
        scenario_id="PR-04",
        passed=True,
        action="Act automatically",
        reason=(
            f"AgentKit x402 Doctor preflight verified ({preflight_verdict}, "
            f"${preflight_fee_usdc:.3f} USDC <= $0.002 cap on {wallet_network}) (#1522)"
        ),
        http_status=200,
        signals={"preflight_verdict": preflight_verdict, "preflight_fee_usdc": preflight_fee_usdc},
    )


def evaluate_agentkit_assetfare_readonly_quote_and_continuation_guard(
    payload: Dict[str, Any],
) -> GuardEvaluation:
    """PR-05: coinbase/agentkit#1513 (AssetFare read-only cross-chain quote & continuation_v3)."""
    server_signing = bool(payload.get("server_signing", True))
    server_submission = bool(payload.get("server_submission", True))
    destination_chain = str(payload.get("destination_chain", "polygon"))
    typed_canonical_v1_hash_verified = bool(
        payload.get("typed_canonical_v1_hash_preserved_across_unsafe_int", False)
    )
    mode_0600_quote_file_and_caller_approval = bool(
        payload.get("mode_0600_quote_file_and_explicit_caller_approval", False)
    )

    if server_signing or server_submission:
        return GuardEvaluation(
            scenario_id="PR-05",
            passed=False,
            action="Send to a human",
            reason="AgentKit AssetFare violated read-only boundary (server_signing/server_submission must be False) (#1513)",
            http_status=403,
            signals={"server_signing": server_signing, "server_submission": server_submission},
        )

    if destination_chain in {"polygon", "optimism"}:
        return GuardEvaluation(
            scenario_id="PR-05",
            passed=False,
            action="Send to a human",
            reason=f"AgentKit AssetFare rejected source-only chain '{destination_chain}' as destination (#1513)",
            http_status=422,
            signals={"destination_chain": destination_chain},
        )

    if not typed_canonical_v1_hash_verified or not mode_0600_quote_file_and_caller_approval:
        return GuardEvaluation(
            scenario_id="PR-05",
            passed=False,
            action="Send to a human",
            reason=(
                "AgentKit AssetFare continuation_v3 hash mutated by unsafe JS integer or "
                "missing mode-0600 quote file / caller approval (#1513)"
            ),
            http_status=409,
            signals={
                "typed_canonical_v1_hash_preserved_across_unsafe_int": typed_canonical_v1_hash_verified,
                "mode_0600_quote_file_and_explicit_caller_approval": mode_0600_quote_file_and_caller_approval,
            },
        )

    return GuardEvaluation(
        scenario_id="PR-05",
        passed=True,
        action="Act automatically",
        reason=(
            "AgentKit AssetFare read-only boundary, source-only Polygon/Optimism direction check, "
            "typed-canonical-v1 hash, and mode-0600 continuation_v3 handoff verified (#1513)"
        ),
        http_status=200,
        signals={"destination_chain": destination_chain, "server_signing": False},
    )


def evaluate_a2a_java_otel_push_notification_tracing_guard(
    payload: Dict[str, Any],
) -> GuardEvaluation:
    """PR-06: a2aproject/a2a-java#1229 & #1228 (OpenTelemetry push notification tracing & W3C traceparent)."""
    sender_returns_boolean_outcome = bool(
        payload.get("push_notification_sender_returns_boolean", False)
    )
    w3c_traceparent_injected = bool(
        payload.get("w3c_traceparent_and_tracestate_injected", False)
    )
    client_span_reflects_delivery_status = bool(
        payload.get("client_span_status_reflects_delivery_outcome", False)
    )
    cdi_priority_disambiguated = bool(
        payload.get("cdi_alternative_priority_1_configured", False)
    )

    if not sender_returns_boolean_outcome or not client_span_reflects_delivery_status:
        return GuardEvaluation(
            scenario_id="PR-06",
            passed=False,
            action="Send to a human",
            reason=(
                "A2A Java PushNotificationSender returned void or failed to set CLIENT span "
                "status to ERROR on failed webhook delivery (#1229/#1228)"
            ),
            http_status=502,
            signals={
                "push_notification_sender_returns_boolean": sender_returns_boolean_outcome,
                "client_span_status_reflects_delivery_outcome": client_span_reflects_delivery_status,
            },
        )

    if not w3c_traceparent_injected or not cdi_priority_disambiguated:
        return GuardEvaluation(
            scenario_id="PR-06",
            passed=False,
            action="Send to a human",
            reason="A2A Java push notification omitted W3C traceparent header or hit CDI bean ambiguity (#1229)",
            http_status=422,
            signals={
                "w3c_traceparent_and_tracestate_injected": w3c_traceparent_injected,
                "cdi_alternative_priority_1_configured": cdi_priority_disambiguated,
            },
        )

    return GuardEvaluation(
        scenario_id="PR-06",
        passed=True,
        action="Act automatically",
        reason=(
            "A2A Java OpenTelemetryPushNotificationSenderDecorator CLIENT span status and "
            "W3C traceparent/tracestate propagation verified (#1229/#1228)"
        ),
        http_status=200,
        signals={"w3c_traceparent_and_tracestate_injected": True},
    )


def evaluate_a2a_java_closed_child_queue_final_event_guard(
    payload: Dict[str, Any],
) -> GuardEvaluation:
    """PR-07: a2aproject/a2a-java#1227 (deliver awaited final events to gracefully closed child queues)."""
    child_queue_gracefully_closed = bool(payload.get("child_queue_gracefully_closed", False))
    child_awaiting_final_event = bool(payload.get("child_awaiting_final_event", False))
    event_is_final = bool(payload.get("event_is_final", False))
    delivered_without_3s_grace_stall = bool(
        payload.get("final_event_delivered_to_closed_awaiting_child", False)
    )

    if (
        child_queue_gracefully_closed
        and child_awaiting_final_event
        and event_is_final
        and not delivered_without_3s_grace_stall
    ):
        return GuardEvaluation(
            scenario_id="PR-07",
            passed=False,
            action="Send to a human",
            reason=(
                "A2A Java distributeToChildren skipped gracefully closed child queue awaiting "
                "final event, stalling EventConsumer for 3s grace period (#1227)"
            ),
            http_status=504,
            signals={
                "child_queue_gracefully_closed": True,
                "child_awaiting_final_event": True,
                "final_event_delivered_to_closed_awaiting_child": False,
            },
        )

    if not delivered_without_3s_grace_stall:
        return GuardEvaluation(
            scenario_id="PR-07",
            passed=False,
            action="Send to a human",
            reason="A2A Java final event delivery to child queue failed (#1227)",
            http_status=500,
            signals={"final_event_delivered_to_closed_awaiting_child": False},
        )

    return GuardEvaluation(
        scenario_id="PR-07",
        passed=True,
        action="Act automatically",
        reason=(
            "A2A Java EventQueue delivers in-flight final event to gracefully closed child "
            "queue awaiting final event without 3s grace-timeout stall (#1227)"
        ),
        http_status=200,
        signals={"final_event_delivered_to_closed_awaiting_child": True},
    )


def evaluate_a2a_python_v03_history_zero_and_go_grpc_metadata_guard(
    payload: Dict[str, Any],
) -> GuardEvaluation:
    """PR-08: a2aproject/a2a-python#1312 & a2aproject/a2a-go#476."""
    v03_history_length_zero_treated_as_unlimited = bool(
        payload.get("python_v03_history_length_zero_treated_as_unlimited", False)
    )
    go_grpc_preserves_caller_authorization = bool(
        payload.get("go_grpc_preserves_caller_metadata_with_service_params", False)
    )
    caller_metadata_map_unmutated = bool(
        payload.get("go_grpc_caller_metadata_map_not_mutated", False)
    )

    if not v03_history_length_zero_treated_as_unlimited:
        return GuardEvaluation(
            scenario_id="PR-08",
            passed=False,
            action="Send to a human",
            reason=(
                "A2A Python v0.3 compat passed history_length=0 as literal 0 limit on "
                "JSON-RPC/REST instead of unlimited (#1312)"
            ),
            http_status=422,
            signals={"python_v03_history_length_zero_treated_as_unlimited": False},
        )

    if not go_grpc_preserves_caller_authorization or not caller_metadata_map_unmutated:
        return GuardEvaluation(
            scenario_id="PR-08",
            passed=False,
            action="Send to a human",
            reason=(
                "A2A Go withGRPCMetadata overwrote caller authorization header when attaching "
                "ServiceParams or mutated caller map (#476)"
            ),
            http_status=401,
            signals={
                "go_grpc_preserves_caller_metadata_with_service_params": go_grpc_preserves_caller_authorization,
                "go_grpc_caller_metadata_map_not_mutated": caller_metadata_map_unmutated,
            },
        )

    return GuardEvaluation(
        scenario_id="PR-08",
        passed=True,
        action="Act automatically",
        reason=(
            "A2A Python v0.3 history_length=0 unlimited semantics and A2A Go gRPC caller "
            "metadata preservation verified (#1312/#476)"
        ),
        http_status=200,
        signals={
            "python_v03_history_length_zero_treated_as_unlimited": True,
            "go_grpc_preserves_caller_metadata_with_service_params": True,
        },
    )


def evaluate_ucp_schema_resource_identity_and_payment_instrument_guard(
    payload: Dict[str, Any],
) -> GuardEvaluation:
    """PR-09: Universal-Commerce-Protocol/ucp-schema#66 (preserve schema resource identity in $ref)."""
    schema_resource_identity_preserved = bool(
        payload.get("schema_resource_identity_preserved_in_bundling", False)
    )
    selected_instrument_has_required_fields = bool(
        payload.get("selected_payment_instrument_has_id_handler_id_type", False)
    )
    root_hash_ref_bound_to_defining_resource = bool(
        payload.get("internal_root_ref_bound_to_payment_instrument_schema", False)
    )

    if not schema_resource_identity_preserved or not root_hash_ref_bound_to_defining_resource:
        return GuardEvaluation(
            scenario_id="PR-09",
            passed=False,
            action="Send to a human",
            reason=(
                "UCP schema bundler transplanted $ref fragment and rebased '#' onto checkout.json "
                "root, validating payment instruments against nothing (#66)"
            ),
            http_status=422,
            signals={
                "schema_resource_identity_preserved_in_bundling": schema_resource_identity_preserved,
                "internal_root_ref_bound_to_payment_instrument_schema": root_hash_ref_bound_to_defining_resource,
            },
        )

    if not selected_instrument_has_required_fields:
        return GuardEvaluation(
            scenario_id="PR-09",
            passed=False,
            action="Send to a human",
            reason="UCP selected_payment_instrument missing required id, handler_id, or type (#66)",
            http_status=400,
            signals={"selected_payment_instrument_has_id_handler_id_type": False},
        )

    return GuardEvaluation(
        scenario_id="PR-09",
        passed=True,
        action="Act automatically",
        reason=(
            "UCP schema resource identity preserved across bundling/composition/selection; "
            "selected_payment_instrument enforces id, handler_id, and type (#66)"
        ),
        http_status=200,
        signals={"schema_resource_identity_preserved_in_bundling": True},
    )


def evaluate_ucp_conditional_numeric_bounds_and_vertical_conformance_guard(
    payload: Dict[str, Any],
) -> GuardEvaluation:
    """PR-10: Universal-Commerce-Protocol/python-sdk#71, js-sdk#57, conformance#107/#106."""
    discount_amount_strictly_negative = bool(
        payload.get("discount_total_amount_strictly_less_than_zero", False)
    )
    non_discount_amount_non_negative = bool(
        payload.get("subtotal_tax_fulfillment_amount_non_negative", False)
    )
    discovery_uri_and_tiered_conformance_valid = bool(
        payload.get("discovery_uri_and_vertical_agnostic_conformance_valid", False)
    )

    if not discount_amount_strictly_negative or not non_discount_amount_non_negative:
        return GuardEvaluation(
            scenario_id="PR-10",
            passed=False,
            action="Send to a human",
            reason=(
                "UCP Total model accepted positive discount amount or negative subtotal/tax/fee "
                "due to dropped JSON Schema if/then numeric bounds (python-sdk#71)"
            ),
            http_status=422,
            signals={
                "discount_total_amount_strictly_less_than_zero": discount_amount_strictly_negative,
                "subtotal_tax_fulfillment_amount_non_negative": non_discount_amount_non_negative,
            },
        )

    if not discovery_uri_and_tiered_conformance_valid:
        return GuardEvaluation(
            scenario_id="PR-10",
            passed=False,
            action="Send to a human",
            reason="UCP discovery URI constraint or vertical-agnostic tiered conformance failed (js-sdk#57/conformance#107)",
            http_status=400,
            signals={"discovery_uri_and_tiered_conformance_valid": False},
        )

    return GuardEvaluation(
        scenario_id="PR-10",
        passed=True,
        action="Act automatically",
        reason=(
            "UCP conditional Total numeric bounds (discount < 0, subtotal/tax/fee >= 0), "
            "discovery URI constraints, and RFC #520 tiered conformance verified (#71/#57/#107)"
        ),
        http_status=200,
        signals={"discount_total_amount_strictly_less_than_zero": True},
    )


def evaluate_stripe_hermes_plugin_hardening_and_mcp_cutoff_guard(
    payload: Dict[str, Any],
) -> GuardEvaluation:
    """PR-11: stripe/agent-toolkit#532 + Stripe MCP 2026-10-31 -> 2026-11-30 key cutoff."""
    allowed_tools_comma_string = bool(
        payload.get("hermes_allowed_tools_is_comma_separated_string", False)
    )
    current_turn_write_confirmation = bool(
        payload.get("current_turn_write_confirmation_matches_exact_params", False)
    )
    explicit_tos_and_feedback_consent = bool(
        payload.get("explicit_user_tos_and_feedback_consent", False)
    )
    cli_and_skills_versions_pinned = bool(
        payload.get("stripe_cli_1_51_0_and_skills_1_7_0_pinned", False)
    )
    credential_kind = str(payload.get("stripe_mcp_credential_kind", "sk_live"))

    if credential_kind not in {"rk_live", "oauth"}:
        return GuardEvaluation(
            scenario_id="PR-11",
            passed=False,
            action="Send to a human",
            reason=(
                f"Stripe MCP rejected legacy '{credential_kind}' credential under "
                "2026-10-31 / 2026-11-30 rk_*/OAuth cutoff policy"
            ),
            http_status=401,
            signals={"stripe_mcp_credential_kind": credential_kind},
        )

    if not allowed_tools_comma_string or not cli_and_skills_versions_pinned:
        return GuardEvaluation(
            scenario_id="PR-11",
            passed=False,
            action="Send to a human",
            reason=(
                "Stripe Hermes plugin used YAML list allowed-tools (silently skipped by loader) "
                "or unpinned @stripe/cli / skills version (#532)"
            ),
            http_status=422,
            signals={
                "hermes_allowed_tools_is_comma_separated_string": allowed_tools_comma_string,
                "stripe_cli_1_51_0_and_skills_1_7_0_pinned": cli_and_skills_versions_pinned,
            },
        )

    if not current_turn_write_confirmation or not explicit_tos_and_feedback_consent:
        return GuardEvaluation(
            scenario_id="PR-11",
            passed=False,
            action="Send to a human",
            reason=(
                "Stripe write tool lacked current-turn confirmation of exact (operation, amount, "
                "currency, target) or auto-passed --accept-tos / stripe feedback (#532)"
            ),
            http_status=403,
            signals={
                "current_turn_write_confirmation_matches_exact_params": current_turn_write_confirmation,
                "explicit_user_tos_and_feedback_consent": explicit_tos_and_feedback_consent,
            },
        )

    return GuardEvaluation(
        scenario_id="PR-11",
        passed=True,
        action="Act automatically",
        reason=(
            "Stripe Hermes plugin comma-string allowed-tools, current-turn write confirmation, "
            "explicit ToS/feedback consent, @stripe/cli@1.51.0 pin, and rk_*/OAuth verified (#532)"
        ),
        http_status=200,
        signals={"stripe_mcp_credential_kind": credential_kind},
    )


def evaluate_stripe_ai_atomic_skill_sync_guard(
    payload: Dict[str, Any],
) -> GuardEvaluation:
    """PR-12: stripe/ai#586 (Preserve skills when a sync download fails)."""
    all_downloads_buffered_in_memory = bool(
        payload.get("downloads_staged_in_memory_before_directory_clean", False)
    )
    download_error_count = int(payload.get("sync_download_error_count", 1))
    existing_skills_preserved_on_failure = bool(
        payload.get("existing_skills_preserved_when_any_download_fails", False)
    )

    if not all_downloads_buffered_in_memory or not existing_skills_preserved_on_failure:
        return GuardEvaluation(
            scenario_id="PR-12",
            passed=False,
            action="Send to a human",
            reason=(
                "Stripe AI sync.js wiped canonical/provider output directories before verifying "
                "downloads, leaving skill directories incomplete on failure (#586)"
            ),
            http_status=503,
            signals={
                "downloads_staged_in_memory_before_directory_clean": all_downloads_buffered_in_memory,
                "existing_skills_preserved_when_any_download_fails": existing_skills_preserved_on_failure,
            },
        )

    if download_error_count > 0:
        return GuardEvaluation(
            scenario_id="PR-12",
            passed=False,
            action="Send to a human",
            reason=f"Stripe AI skill sync aborted directory swap due to {download_error_count} download error(s) (#586)",
            http_status=502,
            signals={"sync_download_error_count": download_error_count},
        )

    return GuardEvaluation(
        scenario_id="PR-12",
        passed=True,
        action="Act automatically",
        reason=(
            "Stripe AI skill sync buffered all downloads in memory with zero errors before "
            "atomically updating canonical and provider skill directories (#586)"
        ),
        http_status=200,
        signals={"sync_download_error_count": 0},
    )


def evaluate_mcp_csharp_blob_data_base64_utf8_setter_guard(
    payload: Dict[str, Any],
) -> GuardEvaluation:
    """PR-13: modelcontextprotocol/csharp-sdk#1957 (Blob/Data setters reject raw binary disguised as base64)."""
    setter_validates_base64_utf8 = bool(
        payload.get("blob_and_data_setters_validate_base64_utf8", False)
    )
    raw_binary_rejected_with_from_bytes_hint = bool(
        payload.get("raw_binary_rejected_with_from_bytes_argument_exception", False)
    )
    payload_is_valid_base64_utf8 = bool(
        payload.get("assigned_bytes_are_valid_base64_utf8", False)
    )

    if not setter_validates_base64_utf8 or not raw_binary_rejected_with_from_bytes_hint:
        return GuardEvaluation(
            scenario_id="PR-13",
            passed=False,
            action="Send to a human",
            reason=(
                "MCP C# SDK Blob/Data setter accepted raw binary bytes without ValidateBase64Utf8, "
                "causing mangled UTF-8 JSON output and downstream FormatException (#1957)"
            ),
            http_status=400,
            signals={
                "blob_and_data_setters_validate_base64_utf8": setter_validates_base64_utf8,
                "raw_binary_rejected_with_from_bytes_argument_exception": raw_binary_rejected_with_from_bytes_hint,
            },
        )

    if not payload_is_valid_base64_utf8:
        return GuardEvaluation(
            scenario_id="PR-13",
            passed=False,
            action="Send to a human",
            reason="MCP C# SDK rejected non-base64 bytes in Blob/Data setter; use FromBytes(...) (#1957)",
            http_status=422,
            signals={"assigned_bytes_are_valid_base64_utf8": False},
        )

    return GuardEvaluation(
        scenario_id="PR-13",
        passed=True,
        action="Act automatically",
        reason=(
            "MCP C# SDK EncodingUtilities.ValidateBase64Utf8 enforced on BlobResourceContents.Blob, "
            "ImageContentBlock.Data, and AudioContentBlock.Data setters (#1957)"
        ),
        http_status=200,
        signals={"blob_and_data_setters_validate_base64_utf8": True},
    )


def evaluate_mcp_csharp_discover_probe_non_committal_version_guard(
    payload: Dict[str, Any],
) -> GuardEvaluation:
    """PR-14: modelcontextprotocol/csharp-sdk#1956 (server/discover probe must not commit protocol version)."""
    discover_probe_leaves_version_uncommitted = bool(
        payload.get("server_discover_leaves_negotiated_version_null", False)
    )
    initialize_fallback_succeeds_after_probe_timeout = bool(
        payload.get("initialize_fallback_succeeds_after_timed_out_discover_probe", False)
    )
    list_changed_gated_on_initialize_handshake = bool(
        payload.get("list_changed_broadcast_gated_on_supports_initialize_handshake", False)
    )

    if (
        not discover_probe_leaves_version_uncommitted
        or not initialize_fallback_succeeds_after_probe_timeout
    ):
        return GuardEvaluation(
            scenario_id="PR-14",
            passed=False,
            action="Send to a human",
            reason=(
                "MCP C# SDK server/discover probe prematurely latched session to 2026-07-28, "
                "rejecting same-connection initialize fallback after probe timeout (#1956)"
            ),
            http_status=409,
            signals={
                "server_discover_leaves_negotiated_version_null": discover_probe_leaves_version_uncommitted,
                "initialize_fallback_succeeds_after_timed_out_discover_probe": initialize_fallback_succeeds_after_probe_timeout,
            },
        )

    if not list_changed_gated_on_initialize_handshake:
        return GuardEvaluation(
            scenario_id="PR-14",
            passed=False,
            action="Send to a human",
            reason="MCP C# SDK broadcast list_changed notification to uncommitted discover probe session (#1956)",
            http_status=422,
            signals={"list_changed_broadcast_gated_on_supports_initialize_handshake": False},
        )

    return GuardEvaluation(
        scenario_id="PR-14",
        passed=True,
        action="Act automatically",
        reason=(
            "MCP C# SDK treats server/discover as non-committal probe, preserving initialize "
            "fallback and gating legacy list_changed broadcasts (#1956)"
        ),
        http_status=200,
        signals={"server_discover_leaves_negotiated_version_null": True},
    )


def evaluate_mcp_registry_private_key_and_multi_sdk_transport_guard(
    payload: Dict[str, Any],
) -> GuardEvaluation:
    """PR-15: modelcontextprotocol/registry#1734, kotlin-sdk#1057, rust-sdk#1302, java-sdk#1204."""
    key_source = str(payload.get("publisher_private_key_source", "cli_flag"))
    mutually_exclusive_flags_enforced = bool(
        payload.get("private_key_and_file_flags_mutually_exclusive", False)
    )
    pem_prefix_and_empty_file_rejected = bool(
        payload.get("pem_prefix_and_empty_key_file_rejected", False)
    )
    kotlin_sse_rust_cors_java_headers_ready = bool(
        payload.get("kotlin_sse_discovery_rust_cross_origin_meta_java_sse_headers_valid", False)
    )

    if key_source not in {"private_key_file", "MCP_PRIVATE_KEY"} or not mutually_exclusive_flags_enforced:
        return GuardEvaluation(
            scenario_id="PR-15",
            passed=False,
            action="Send to a human",
            reason=(
                "MCP Registry publisher exposed signing key on CLI process list or accepted "
                "conflicting --private-key and --private-key-file flags (registry#1734)"
            ),
            http_status=400,
            signals={
                "publisher_private_key_source": key_source,
                "private_key_and_file_flags_mutually_exclusive": mutually_exclusive_flags_enforced,
            },
        )

    if not pem_prefix_and_empty_file_rejected or not kotlin_sse_rust_cors_java_headers_ready:
        return GuardEvaluation(
            scenario_id="PR-15",
            passed=False,
            action="Send to a human",
            reason=(
                "MCP Registry accepted -----BEGIN PEM / empty key file or Kotlin SSE discovery / "
                "Rust cross-origin resource_metadata / Java SSE headers failed (#1734/#1057/#1302/#1204)"
            ),
            http_status=422,
            signals={
                "pem_prefix_and_empty_key_file_rejected": pem_prefix_and_empty_file_rejected,
                "kotlin_sse_discovery_rust_cross_origin_meta_java_sse_headers_valid": kotlin_sse_rust_cors_java_headers_ready,
            },
        )

    return GuardEvaluation(
        scenario_id="PR-15",
        passed=True,
        action="Act automatically",
        reason=(
            "MCP Registry --private-key-file / MCP_PRIVATE_KEY resolution, PEM/empty-file rejection, "
            "Kotlin SSE discovery, Rust cross-origin metadata, and Java SSE headers verified (#1734..#1204)"
        ),
        http_status=200,
        signals={"publisher_private_key_source": key_source},
    )


def evaluate_tau2_bench_release_2_0_voice_env_and_fixture_guard(
    payload: Dict[str, Any],
) -> GuardEvaluation:
    """PR-16: sierra-research/tau2-bench#617 (2.0.0 release fix-ups: scoped logger, TAU2_VOICE_ID_EN_*, voice-v1)."""
    logger_disable_scoped_to_fixture = bool(
        payload.get("tau2_logger_disable_scoped_to_module_fixture", False)
    )
    voice_env_uses_lang_persona_format = bool(
        payload.get("voice_id_env_uses_tau2_voice_id_lang_persona", False)
    )
    gym_live_api_and_alltools_qwen_gated = bool(
        payload.get("gym_live_api_marked_and_alltools_qwen_registered", False)
    )
    voice_v1_refuses_partial_and_v1_resume = bool(
        payload.get("voice_v1_manifest_refuses_partial_runs_and_v1_resume", False)
    )

    if not logger_disable_scoped_to_fixture or not voice_env_uses_lang_persona_format:
        return GuardEvaluation(
            scenario_id="PR-16",
            passed=False,
            action="Send to a human",
            reason=(
                "tau2-bench silenced tau2 logger process-wide at import time or emitted legacy "
                "TAU2_VOICE_ID_<PERSONA> env keys without <LANG> (#617)"
            ),
            http_status=422,
            signals={
                "tau2_logger_disable_scoped_to_module_fixture": logger_disable_scoped_to_fixture,
                "voice_id_env_uses_tau2_voice_id_lang_persona": voice_env_uses_lang_persona_format,
            },
        )

    if not gym_live_api_and_alltools_qwen_gated or not voice_v1_refuses_partial_and_v1_resume:
        return GuardEvaluation(
            scenario_id="PR-16",
            passed=False,
            action="Send to a human",
            reason=(
                "tau2-bench ran live LLM Gym simulator in key-free mode or allowed partial / "
                "v1.x resume on voice-v1 manifest (#617)"
            ),
            http_status=409,
            signals={
                "gym_live_api_marked_and_alltools_qwen_registered": gym_live_api_and_alltools_qwen_gated,
                "voice_v1_manifest_refuses_partial_runs_and_v1_resume": voice_v1_refuses_partial_and_v1_resume,
            },
        )

    return GuardEvaluation(
        scenario_id="PR-16",
        passed=True,
        action="Act automatically",
        reason=(
            "Sierra tau2-bench 2.0.0 module-scoped logger fixture, TAU2_VOICE_ID_EN_* persona keys, "
            "live_api Gym gating, and voice-v1 manifest integrity verified (#617)"
        ),
        http_status=200,
        signals={"voice_id_env_uses_tau2_voice_id_lang_persona": True},
    )


STAGE260_GUARD_EVALUATORS: Dict[str, Callable[[Dict[str, Any]], GuardEvaluation]] = {
    "PR-01": evaluate_x402_requests_payment_retry_body_replay_guard,
    "PR-02": evaluate_x402_go_batch_settlement_refund_and_prior_process_guard,
    "PR-03": evaluate_x402_go_facilitator_verify_error_response_guard,
    "PR-04": evaluate_agentkit_x402_doctor_preflight_guard,
    "PR-05": evaluate_agentkit_assetfare_readonly_quote_and_continuation_guard,
    "PR-06": evaluate_a2a_java_otel_push_notification_tracing_guard,
    "PR-07": evaluate_a2a_java_closed_child_queue_final_event_guard,
    "PR-08": evaluate_a2a_python_v03_history_zero_and_go_grpc_metadata_guard,
    "PR-09": evaluate_ucp_schema_resource_identity_and_payment_instrument_guard,
    "PR-10": evaluate_ucp_conditional_numeric_bounds_and_vertical_conformance_guard,
    "PR-11": evaluate_stripe_hermes_plugin_hardening_and_mcp_cutoff_guard,
    "PR-12": evaluate_stripe_ai_atomic_skill_sync_guard,
    "PR-13": evaluate_mcp_csharp_blob_data_base64_utf8_setter_guard,
    "PR-14": evaluate_mcp_csharp_discover_probe_non_committal_version_guard,
    "PR-15": evaluate_mcp_registry_private_key_and_multi_sdk_transport_guard,
    "PR-16": evaluate_tau2_bench_release_2_0_voice_env_and_fixture_guard,
}


def evaluate_stage260_guards(scenarios: List[Dict[str, Any]]) -> List[GuardEvaluation]:
    """Evaluate a list of Stage 260 scenario dicts (`scenario_id` + `payload`)."""
    results: List[GuardEvaluation] = []
    for item in scenarios:
        sid = str(item.get("scenario_id", ""))
        evaluator = STAGE260_GUARD_EVALUATORS.get(sid)
        if evaluator is None:
            raise ValueError(f"Unknown Stage 260 scenario_id: {sid}")
        results.append(evaluator(item.get("payload", {})))
    return results
