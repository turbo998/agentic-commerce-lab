"""Stage 142 deterministic guardrails for x402 MCP payment disagreement & route decode,
UCP duplicate selected-option & issuer anchoring, ACP session_context & flat Error,
AP2 execution_date & token-mandate binding, MCP SEP-3140/3149, Stripe AI & tau2-bench.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import unquote


@dataclass(frozen=True)
class GuardEvaluation:
    allowed: bool
    decision: str
    reason_code: str
    violations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def validate_x402_mcp_payment_disagreement_and_route_guard(
    *,
    structured_payment_required: dict[str, Any] | None,
    text_payment_required: dict[str, Any] | None,
    route_template: str,
    authorized_max_amount: int,
    settlement_override_amount: int | None,
    charged_amount_str: str,
    charged_cumulative_amount_str: str | None,
    discovery_resource_url: str,
    mcp_result_meta: dict[str, Any] | None,
    mcp_result_dunder_meta: dict[str, Any] | None,
) -> GuardEvaluation:
    """Enforces x402 PRs #3643/#3631, #3422, #3419, #3421, #3417, and #3411."""
    violations: list[str] = []

    # 1. #3643 / #3631: Refuse MCP auto-pay when structuredContent and content[0].text disagree
    if structured_payment_required is not None and text_payment_required is not None:
        if structured_payment_required != text_payment_required:
            violations.append("x402_mcp_payment_required_mismatch")

    # 2. #3422: Iterative decode-until-stable in isValidRouteTemplate
    cur = route_template
    for _ in range(8):
        nxt = unquote(cur)
        if nxt == cur:
            break
        cur = nxt
    else:
        violations.append("x402_route_template_excessive_encoding")

    if ".." in cur or "://" in cur:
        violations.append("x402_route_template_traversal_or_scheme_injection")

    # 3. #3419: Enforce settlement override ceiling in settlePayment
    if settlement_override_amount is not None:
        if settlement_override_amount < 0 or settlement_override_amount > authorized_max_amount:
            violations.append("x402_settlement_override_exceeds_ceiling")

    # 4. #3421: Validate EVM channel state shape before BigInt conversion
    channel_state_skipped = False
    if not charged_amount_str.isdigit():
        violations.append("x402_evm_invalid_charged_amount_digits")
    if charged_cumulative_amount_str is None or not charged_cumulative_amount_str.isdigit():
        channel_state_skipped = True
        violations.append("x402_evm_malformed_channel_state_cumulative_amount")

    # 5. #3417: Preserve mcp:// scheme URLs in extractDiscoveryInfo without new URL() corruption
    canonical_discovery_url = discovery_resource_url
    if discovery_resource_url.startswith("mcp://"):
        if "null" in discovery_resource_url or not discovery_resource_url.startswith("mcp://tool/"):
            violations.append("x402_mcp_discovery_url_corrupted")

    # 6. #3411: Prefer .meta over ._meta in convert_mcp_result for MCP SDK 2.x
    resolved_meta = mcp_result_meta if mcp_result_meta is not None else mcp_result_dunder_meta
    if resolved_meta is None or "x402/payment-response" not in resolved_meta:
        violations.append("x402_mcp_settlement_metadata_missing")

    if violations:
        return GuardEvaluation(
            allowed=False,
            decision="block",
            reason_code=violations[0],
            violations=violations,
            metadata={
                "decoded_route_template": cur,
                "channel_state_skipped": channel_state_skipped,
                "canonical_discovery_url": canonical_discovery_url,
            },
        )

    return GuardEvaluation(
        allowed=True,
        decision="allow",
        reason_code="x402_mcp_route_and_settlement_valid",
        metadata={
            "decoded_route_template": cur,
            "channel_state_skipped": channel_state_skipped,
            "canonical_discovery_url": canonical_discovery_url,
            "resolved_meta_source": "meta" if mcp_result_meta is not None else "_meta",
        },
    )


def validate_ucp_option_selection_and_issuer_anchor_guard(
    *,
    selected_options: list[dict[str, str]],
    candidate_auth_url: str,
    recognized_issuers: set[str],
    subject_token_issuer: str,
) -> GuardEvaluation:
    """Enforces UCP Issues/PRs #879 (duplicate selected option conflict) and #850 (exact issuer anchoring)."""
    violations: list[str] = []
    seen_options: dict[str, str] = {}
    deduplicated: list[dict[str, str]] = []

    for item in selected_options:
        name = str(item.get("name", "")).strip()
        label = str(item.get("label", "")).strip()
        if not name or not label:
            violations.append("ucp_selected_option_missing_name_or_label")
            continue
        if name in seen_options:
            if seen_options[name] != label:
                violations.append("ucp_duplicate_selected_option_conflict")
        else:
            seen_options[name] = label
            deduplicated.append({"name": name, "label": label})

    # #850: Exact character-string match against recognized issuers (no trailing-slash normalization)
    if candidate_auth_url not in recognized_issuers:
        violations.append("ucp_identity_linking_unrecognized_issuer_auth_url")
    elif subject_token_issuer != candidate_auth_url:
        violations.append("ucp_identity_linking_subject_token_issuer_mismatch")

    if violations:
        return GuardEvaluation(
            allowed=False,
            decision="block",
            reason_code=violations[0],
            violations=violations,
            metadata={"deduplicated_options": deduplicated},
        )

    return GuardEvaluation(
        allowed=True,
        decision="allow",
        reason_code="ucp_option_and_issuer_anchor_valid",
        metadata={"deduplicated_options": deduplicated, "anchored_issuer": candidate_auth_url},
    )


def validate_acp_session_context_and_flat_error_guard(
    *,
    endpoint: str,
    payload: dict[str, Any],
    error_response: dict[str, Any] | None = None,
) -> GuardEvaluation:
    """Enforces ACP PRs #238 (session_context vs risk_signals) and #243 (flat Error schema)."""
    violations: list[str] = []

    if endpoint == "complete_checkout":
        if "risk_signals" in payload:
            violations.append("acp_complete_checkout_deprecated_risk_signals_field")
        sc = payload.get("session_context")
        if sc is not None and not isinstance(sc, dict):
            violations.append("acp_session_context_must_be_object")
    elif endpoint == "delegate_payment":
        rs = payload.get("risk_signals")
        if rs is not None:
            if not isinstance(rs, list) or any(
                not isinstance(item, dict) or not {"type", "score", "action"}.issubset(item.keys())
                for item in rs
            ):
                violations.append("acp_delegate_payment_risk_signals_must_be_verdict_array")
        sc = payload.get("session_context")
        if sc is not None:
            if not isinstance(sc, dict) or not sc.get("session_id"):
                violations.append("acp_delegate_payment_invalid_session_context")
    else:
        violations.append("acp_unknown_endpoint")

    if error_response is not None:
        if "error" in error_response:
            violations.append("acp_error_response_wrapped_envelope_forbidden")
        if not {"type", "code", "message"}.issubset(error_response.keys()):
            violations.append("acp_error_response_missing_flat_required_fields")

    if violations:
        return GuardEvaluation(
            allowed=False,
            decision="block",
            reason_code=violations[0],
            violations=violations,
        )

    return GuardEvaluation(
        allowed=True,
        decision="allow",
        reason_code="acp_session_context_and_error_schema_valid",
    )


def validate_ap2_exec_date_token_binding_merchant_kb_guard(
    *,
    open_not_before: int,
    open_not_after: int,
    closed_execution_date: int | None,
    effective_execution_time: int,
    token_bound_mandate_id: str | None,
    verified_mandate_id: str,
    open_merchant_id: str,
    closed_merchant_id: str,
    intermediate_kb_hops: list[dict[str, str]],
    expected_aud: str,
    expected_nonce: str,
) -> GuardEvaluation:
    """Enforces AP2 Issues/PRs #317, #316, #315, and #313."""
    violations: list[str] = []

    # 1. #317: Closed mandate omitting execution_date must check effective_execution_time against window
    target_exec_time = (
        closed_execution_date if closed_execution_date is not None else effective_execution_time
    )
    if not (open_not_before <= target_exec_time <= open_not_after):
        violations.append("ap2_execution_date_outside_authorized_window")

    # 2. #316: Token must be explicitly bound to verified_mandate_id (never global unbound None scan)
    if not token_bound_mandate_id or token_bound_mandate_id != verified_mandate_id:
        violations.append("ap2_credential_token_unbound_or_mandate_mismatch")

    # 3. #315: Merchant/payee identity matching requires non-empty stable IDs (no display fallback)
    if not open_merchant_id.strip() or not closed_merchant_id.strip():
        violations.append("ap2_merchant_id_empty_display_fallback_forbidden")
    elif open_merchant_id != closed_merchant_id:
        violations.append("ap2_merchant_id_mismatch")

    # 4. #313: Honor expected_aud and expected_nonce on every intermediate KB-SD-JWT hop
    for idx, hop in enumerate(intermediate_kb_hops):
        if hop.get("aud") != expected_aud or hop.get("nonce") != expected_nonce:
            violations.append(f"ap2_intermediate_kb_hop_{idx}_aud_or_nonce_mismatch")

    if violations:
        return GuardEvaluation(
            allowed=False,
            decision="block",
            reason_code=violations[0],
            violations=violations,
            metadata={"evaluated_execution_time": target_exec_time},
        )

    return GuardEvaluation(
        allowed=True,
        decision="allow",
        reason_code="ap2_exec_date_token_merchant_kb_valid",
        metadata={"evaluated_execution_time": target_exec_time},
    )


def validate_mcp_signed_manifest_stripe_toolkit_and_tau2_live_db_guard(
    *,
    manifest_signed: bool,
    manifest_server_uri: str,
    expected_server_uri: str,
    previous_content_hash: str,
    current_content_hash: str,
    reconsent_granted: bool,
    trust_label_effect: str,
    cimd_auth_methods_supported: list[str] | None,
    stripe_toolkit_config: dict[str, Any],
    anthropic_start_input_tokens: int,
    anthropic_delta_input_tokens: list[int | None],
    stream_abandoned: bool,
    tau2_telecom_line_status: str,
    tau2_live_db_hash: str,
    tau2_replay_db_hash: str,
    tau2_expected_db_hash: str,
) -> GuardEvaluation:
    """Enforces MCP #3140/#3149, Stripe AI #508/#519/#509, and Sierra tau2-bench #611/#609/#608."""
    violations: list[str] = []
    valid_trust_effects = {"read_only", "state_mutating", "external_egress", "financial_settlement"}

    # 1. MCP #3140: Signed Capability Manifest & anti-rug-pull list_changed re-consent
    if not manifest_signed or manifest_server_uri != expected_server_uri:
        violations.append("mcp_sep3140_unsigned_or_server_uri_mismatch")
    if previous_content_hash != current_content_hash and not reconsent_granted:
        violations.append("mcp_sep3140_rug_pull_unapproved_content_hash_change")
    if trust_label_effect not in valid_trust_effects:
        violations.append("mcp_sep3140_unknown_trust_label_effect")

    # 2. MCP #3149: CIMD token_endpoint_auth_methods_supported required
    if not cimd_auth_methods_supported:
        violations.append("mcp_sep3149_cimd_missing_auth_methods_supported")

    # 3. Stripe AI #508: Reject removed v0.6.x `actions` key in v0.7.x toolkit configuration
    if "actions" in stripe_toolkit_config:
        violations.append("stripe_toolkit_deprecated_actions_policy_fail_open_blocked")

    # 4. Stripe AI #519 & #509: Cumulative Anthropic input tokens & no metering on abandoned streams
    cumulative_input_tokens = anthropic_start_input_tokens
    for delta_val in anthropic_delta_input_tokens:
        if delta_val is not None:
            cumulative_input_tokens = delta_val
    if stream_abandoned:
        violations.append("stripe_token_meter_abandoned_stream_closed_without_emit")

    # 5. Sierra tau2-bench #611: Require active telecom line before data refueling
    if tau2_telecom_line_status != "active":
        violations.append("tau2_telecom_refuel_requires_active_line")

    # 6. Sierra tau2-bench #609/#608: Grade against live_db_hash, report replay_divergence
    replay_divergence = tau2_live_db_hash != tau2_replay_db_hash
    if tau2_live_db_hash != tau2_expected_db_hash:
        violations.append("tau2_live_db_hash_mismatch")

    if violations:
        return GuardEvaluation(
            allowed=False,
            decision="block",
            reason_code=violations[0],
            violations=violations,
            metadata={
                "cumulative_input_tokens": cumulative_input_tokens,
                "replay_divergence": replay_divergence,
            },
        )

    return GuardEvaluation(
        allowed=True,
        decision="allow",
        reason_code="mcp_stripe_tau2_all_guards_valid",
        metadata={
            "cumulative_input_tokens": cumulative_input_tokens,
            "replay_divergence": replay_divergence,
        },
    )
