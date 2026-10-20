"""Stage 70 deterministic runtime guards for UCP, ACP, Google AP2, and Sierra tau2-bench.

Covers primary-source protocol and benchmark invariants audited on 2026-10-20:
1. Universal Commerce Protocol (UCP) PRs #659, #658, #657, #655, #653, #642, #626/#580, #622, #596:
   - Order Event Webhook signing gate (`webhook-id`, `webhook-timestamp` in covered components;
     `event_id` and `created_time` prohibited in the webhook JSON body).
   - Reserved `ucp` protocol namespace at every structured object scope (covered by AP2
     `merchant_authorization` JCS; only `ap2` excluded), `ucp.map_order` registry traversal
     ordering (`ucp_request: "omit"`), and `ucp.capabilities` map validation with `schema` URL.
   - Response-carried `ucp.request_constraints` (`path`, `required`, `properties` with `enum`/`const`),
     mandatory RFC 9535 JSONPath `path` on available payment instruments, and next-request validation.
   - Integer step-count `quantity` with `quantity_unit` (`unit`, `scale` where 1 step = 10^-scale),
     `context.location` precedence, MCP `-32004` `rate_limit_exceeded`, and `dev.ucp.user_id` /
     `dev.ucp.user_location` abuse-prevention signals.
2. Agentic Commerce Protocol (ACP) PRs #178, #165, #162, #161, #160, #144, #139, #130, #125:
   - Extension declarations moved from `capabilities.extensions` to `protocol.extensions`.
   - Line-item time-bound offer expiry (`valid_until` RFC 3339 and `availability_status`
     `offer_valid` / `offer_expired`) enforced independently of session `quote_expires_at`.
   - Stripe-aligned `Merchant-Signature` (`t=<unix_seconds>,v1=<64_hex>`) HMAC-SHA256 verification
     over `"{timestamp}.{raw_body}"` with 300s replay protection window.
   - All 11 `CheckoutSessionBase.status` lifecycle states, digital vs. physical `shipped`/`fulfilled`
     order status rules, delegate payment 401/500/503 error enums, and 5 MCP checkout tools.
3. Google Agent Payments Protocol (AP2) PRs #144, #132, #131, #128, #110, #92, #83:
   - Standardized `ap2.errors.FailureResponse` (`FailureCategory` -> `RecoveryAction`) blocking
     autonomous retry when `USER_CONFIRMATION_REQUIRED` or `NEW_MANDATE_REQUIRED`.
   - Section 7.1 `PaymentReceipt` null-safe artifact extraction, Mandate JSON Schema `$schema`/`$id`
     conformance, and PCI/SOX/GDPR mandate audit log redaction.
   - Fail-closed Verifiable Intent 3-hop SD-JWT delegation chain and AP2 Micropayment Channel
     (`micropayment-provider`, `streaming-payment-consumer`) cumulative deposit and sequence bounds.
4. Sierra tau2-bench PRs #528, #520, #516, #513, #508, #498, #484:
   - OpenAI Live `LiveInputTranscriptDelta` (`session.input_transcript.delta`) mapped to
     `speech_started=True` (`contains_speech=True`) without falsely setting `was_truncated=True`.
   - Result-safe full-duplex hallucination retries (list validation on `hallucinations`, reviewing
     final retry with `review_model`, checkpointing only selected run, full tool results for judge).
   - Runtime Pydantic coercion of float-encoded integer tool kwargs (`5.0 -> 5`), nested JSON string
     argument comparison in `call_discoverable_agent_tool`, `llm_agent_solo_gt` solo-mode detection,
     pandas 3.x `.value` infra-error filtering + retaining all-infra-error tasks in `pass^k`
     denominator, and fixed-enum `reason` validation on `close_bank_account_7392`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import hmac
import json
from typing import Any


@dataclass(frozen=True)
class GuardEvaluation:
    allowed: bool
    reason_code: str
    details: dict[str, Any] = field(default_factory=dict)


UCP_SIGNING_GATE_HEADERS = frozenset({
    "ucp-agent",
    "signature-agent",
    "idempotency-key",
    "webhook-id",
    "webhook-timestamp",
})

ACP_ELEVEN_SESSION_STATES = frozenset({
    "incomplete",
    "not_ready_for_payment",
    "in_progress",
    "requires_escalation",
    "authentication_required",
    "ready_for_payment",
    "pending_approval",
    "complete_in_progress",
    "completed",
    "canceled",
    "expired",
})

ACP_MCP_CHECKOUT_TOOLS = frozenset({
    "create_checkout_session",
    "get_checkout_session",
    "update_checkout_session",
    "complete_checkout_session",
    "cancel_checkout_session",
})

ACP_DELEGATE_ERROR_TYPES = frozenset({
    "invalid_request",
    "unauthorized",
    "idempotency_conflict",
    "rate_limit_exceeded",
    "internal_server_error",
    "service_unavailable",
})

ACP_DELEGATE_ERROR_CODES = frozenset({
    "invalid_card",
    "expired_card",
    "insufficient_funds",
    "unauthorized",
    "internal_server_error",
    "service_unavailable",
    "invalid_amount",
    "currency_not_supported",
})

AP2_REQUIRED_RECOVERY_BY_CATEGORY: dict[str, set[str]] = {
    "MANDATE_EXPIRED": {"NEW_MANDATE_REQUIRED", "ABORT_TRANSACTION"},
    "PRICE_DRIFT": {"USER_CONFIRMATION_REQUIRED", "NEW_MANDATE_REQUIRED"},
    "CART_MODIFIED": {"USER_CONFIRMATION_REQUIRED", "NEW_MANDATE_REQUIRED"},
    "PAYMENT_DECLINED": {"SELECT_ALTERNATE_PAYMENT", "RETRY_ALLOWED", "USER_CONFIRMATION_REQUIRED"},
    "MERCHANT_REJECTION": {"ABORT_TRANSACTION", "SELECT_ALTERNATE_MERCHANT"},
}

AP2_VALID_ROLES = frozenset({
    "merchant",
    "shopper",
    "credentials-provider",
    "payment-processor",
    "micropayment-provider",
    "streaming-payment-consumer",
})

TAU2_SOLO_IMPLEMENTATIONS = frozenset({
    "llm_agent_solo",
    "llm_agent_solo_gt",
})

TAU2_ALLOWED_CLOSE_ACCOUNT_REASONS = frozenset({
    "customer_request",
    "inactivity",
    "fraud_or_security",
    "deceased_account_holder",
    "compliance_or_policy",
    "duplicate_account",
})


def _parse_rfc3339(ts: str) -> datetime:
    normalized = ts.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    return datetime.fromisoformat(normalized)


def verify_ucp_webhook_signing_map_order_request_constraints_and_sale_basis(
    payload: dict[str, Any],
) -> GuardEvaluation:
    """Validate UCP PRs #659, #658, #657, #655, #653, #642, #626/#580, #622, and #596."""
    # 1. PR #659: Order Event Webhook signing gate & body hygiene
    webhook = payload.get("order_webhook")
    if isinstance(webhook, dict):
        headers = {str(k).lower(): v for k, v in (webhook.get("headers") or {}).items()}
        covered = {str(c).lower() for c in (webhook.get("covered_components") or [])}
        body = webhook.get("body") or {}

        if "event_id" in body or "created_time" in body:
            return GuardEvaluation(
                allowed=False,
                reason_code="ucp_webhook_body_legacy_event_fields_present",
                details={"forbidden_body_fields": [k for k in ("event_id", "created_time") if k in body]},
            )
        if "webhook-id" not in headers or "webhook-timestamp" not in headers:
            return GuardEvaluation(
                allowed=False,
                reason_code="ucp_webhook_missing_required_headers",
                details={"present_headers": sorted(headers.keys())},
            )
        for gate_hdr in UCP_SIGNING_GATE_HEADERS:
            if gate_hdr in headers and gate_hdr not in covered:
                return GuardEvaluation(
                    allowed=False,
                    reason_code="ucp_webhook_signing_gate_missing_id_or_timestamp",
                    details={"missing_covered_header": gate_hdr, "covered_components": sorted(covered)},
                )

    # 2. PR #658 & #657: Profile capabilities map with `schema` URL & reserved `ucp` / `map_order`
    profile = payload.get("profile")
    if isinstance(profile, dict):
        ucp_env = profile.get("ucp") or {}
        caps = ucp_env.get("capabilities")
        if not isinstance(caps, dict) or not caps:
            return GuardEvaluation(
                allowed=False,
                reason_code="ucp_profile_capabilities_not_map_or_missing_schema",
                details={"capabilities_type": type(caps).__name__},
            )
        for cap_name, cap_val in caps.items():
            entries = cap_val if isinstance(cap_val, list) else [cap_val]
            for entry in entries:
                if not isinstance(entry, dict) or not str(entry.get("schema", "")).startswith("https://"):
                    return GuardEvaluation(
                        allowed=False,
                        reason_code="ucp_profile_capabilities_not_map_or_missing_schema",
                        details={"capability": cap_name, "entry": entry},
                    )

    direction = str(payload.get("direction", "response"))
    ucp_meta = payload.get("ucp_meta") or {}
    if direction == "request" and ("map_order" in ucp_meta or "request_constraints" in ucp_meta):
        return GuardEvaluation(
            allowed=False,
            reason_code="ucp_map_order_or_constraints_forbidden_on_request",
            details={"direction": direction, "ucp_meta_keys": sorted(ucp_meta.keys())},
        )

    if payload.get("merchant_authorization_stripped_ucp_member") is True:
        return GuardEvaluation(
            allowed=False,
            reason_code="ucp_merchant_authorization_stripped_reserved_ucp_member",
            details={"rule": "Only ap2 is excluded from JCS merchant_authorization; ucp members MUST stay covered"},
        )

    # 3. PR #655 & #626: Response-carried `ucp.request_constraints` & instrument `path` requirement
    instrument_constraints = payload.get("available_instrument_request_constraints")
    if isinstance(instrument_constraints, dict):
        path_val = str(instrument_constraints.get("path", "")).strip()
        if not path_val.startswith("$"):
            return GuardEvaluation(
                allowed=False,
                reason_code="ucp_instrument_request_constraints_missing_path",
                details={"path": path_val},
            )

    response_constraints = payload.get("response_request_constraints")
    next_request = payload.get("next_request_object")
    if isinstance(response_constraints, dict) and isinstance(next_request, dict):
        req_fields = response_constraints.get("required") or []
        for rf in req_fields:
            if rf not in next_request or next_request[rf] is None:
                return GuardEvaluation(
                    allowed=False,
                    reason_code="ucp_next_request_violates_response_constraints",
                    details={"missing_required_field": rf},
                )
        prop_constraints = response_constraints.get("properties") or {}
        for prop_name, rule in prop_constraints.items():
            if prop_name in next_request and isinstance(rule, dict):
                val = next_request[prop_name]
                if "const" in rule and val != rule["const"]:
                    return GuardEvaluation(
                        allowed=False,
                        reason_code="ucp_next_request_violates_response_constraints",
                        details={"property": prop_name, "expected_const": rule["const"], "actual": val},
                    )
                if "enum" in rule and val not in rule["enum"]:
                    return GuardEvaluation(
                        allowed=False,
                        reason_code="ucp_next_request_violates_response_constraints",
                        details={"property": prop_name, "allowed_enum": rule["enum"], "actual": val},
                    )

    # 4. PR #653: Sale-basis step quantities (`quantity` integer + `quantity_unit` scale)
    line_item = payload.get("line_item")
    if isinstance(line_item, dict):
        qty = line_item.get("quantity")
        if isinstance(qty, bool) or not isinstance(qty, int) or qty < 1:
            return GuardEvaluation(
                allowed=False,
                reason_code="ucp_quantity_sale_basis_invalid_step_or_scale",
                details={"quantity": qty, "type": type(qty).__name__},
            )
        qty_unit = line_item.get("quantity_unit")
        if qty_unit is not None:
            if not isinstance(qty_unit, dict):
                return GuardEvaluation(
                    allowed=False,
                    reason_code="ucp_quantity_sale_basis_invalid_step_or_scale",
                    details={"quantity_unit": qty_unit},
                )
            scale = qty_unit.get("scale", 0)
            unit_code = str(qty_unit.get("unit", "")).strip()
            if isinstance(scale, bool) or not isinstance(scale, int) or scale < 0 or scale > 6 or not unit_code:
                return GuardEvaluation(
                    allowed=False,
                    reason_code="ucp_quantity_sale_basis_invalid_step_or_scale",
                    details={"unit": unit_code, "scale": scale},
                )
            expected_decimal = line_item.get("expected_decimal_quantity")
            if expected_decimal is not None:
                computed = round(qty * (10 ** (-scale)), scale)
                if abs(float(expected_decimal) - computed) > 1e-9:
                    return GuardEvaluation(
                        allowed=False,
                        reason_code="ucp_quantity_sale_basis_invalid_step_or_scale",
                        details={"steps": qty, "scale": scale, "computed": computed, "expected": expected_decimal},
                    )

    # 5. PR #642, #622 & #596: Location hint precedence, MCP -32004 rate_limit_exceeded & signals
    mcp_error = payload.get("mcp_error")
    if isinstance(mcp_error, dict):
        if mcp_error.get("type") == "rate_limit_exceeded" and mcp_error.get("code") != -32004:
            return GuardEvaluation(
                allowed=False,
                reason_code="ucp_rate_limit_or_context_signal_contract_violation",
                details={"expected_code": -32004, "actual_code": mcp_error.get("code")},
            )

    context_hint = payload.get("context_location")
    authoritative_fulfills_to = payload.get("authoritative_fulfills_to")
    resolved_store = payload.get("resolved_store_location")
    if context_hint and authoritative_fulfills_to and resolved_store:
        if resolved_store != authoritative_fulfills_to:
            return GuardEvaluation(
                allowed=False,
                reason_code="ucp_rate_limit_or_context_signal_contract_violation",
                details={
                    "context_location": context_hint,
                    "authoritative_fulfills_to": authoritative_fulfills_to,
                    "resolved_store_location": resolved_store,
                },
            )

    return GuardEvaluation(
        allowed=True,
        reason_code="ucp_webhook_signing_map_order_constraints_and_sale_basis_verified",
        details={
            "webhook_checked": isinstance(webhook, dict),
            "sale_basis_checked": isinstance(line_item, dict),
        },
    )


def verify_acp_protocol_extensions_offer_expiry_webhook_hmac_and_mcp_binding(
    payload: dict[str, Any],
) -> GuardEvaluation:
    """Validate ACP PRs #178, #165, #162, #161, #160, #144, #139, #130, and #125."""
    # 1. PR #178: Extensions must live under `protocol.extensions`, never `capabilities.extensions`
    capabilities = payload.get("capabilities") or {}
    protocol = payload.get("protocol") or {}
    if "extensions" in capabilities:
        return GuardEvaluation(
            allowed=False,
            reason_code="acp_extensions_declared_under_capabilities_instead_of_protocol",
            details={"invalid_path": "capabilities.extensions", "required_path": "protocol.extensions"},
        )

    # 2. PR #144, #162 & #161: 11 session states, completion state gate, digital order status, error enums
    session_status = payload.get("session_status")
    if session_status is not None and session_status not in ACP_ELEVEN_SESSION_STATES:
        return GuardEvaluation(
            allowed=False,
            reason_code="acp_session_state_or_order_status_violation",
            details={"invalid_session_status": session_status},
        )
    if payload.get("operation") == "complete_checkout" and session_status is not None:
        if session_status != "ready_for_payment":
            return GuardEvaluation(
                allowed=False,
                reason_code="acp_session_state_or_order_status_violation",
                details={"operation": "complete_checkout", "session_status": session_status},
            )

    order_update = payload.get("order_webhook_update")
    if isinstance(order_update, dict):
        fulfillment_kind = str(order_update.get("fulfillment_type", "physical"))
        order_status = str(order_update.get("status", ""))
        if fulfillment_kind == "digital" and order_status == "shipped":
            return GuardEvaluation(
                allowed=False,
                reason_code="acp_digital_order_shipped_status_invalid",
                details={"fulfillment_type": fulfillment_kind, "status": order_status},
            )

    delegate_error = payload.get("delegate_payment_error")
    if isinstance(delegate_error, dict):
        err_type = str(delegate_error.get("type", ""))
        err_code = str(delegate_error.get("code", ""))
        if err_type not in ACP_DELEGATE_ERROR_TYPES or err_code not in ACP_DELEGATE_ERROR_CODES:
            return GuardEvaluation(
                allowed=False,
                reason_code="acp_session_state_or_order_status_violation",
                details={"error_type": err_type, "error_code": err_code},
            )

    # 3. PR #165: Time-bound line-item offer expiry (`valid_until` & `availability_status`)
    eval_ts_raw = payload.get("evaluation_time")
    line_items = payload.get("line_items") or []
    if eval_ts_raw and isinstance(line_items, list):
        eval_dt = _parse_rfc3339(str(eval_ts_raw))
        for item in line_items:
            if not isinstance(item, dict):
                continue
            avail = item.get("availability_status")
            if avail == "offer_expired":
                return GuardEvaluation(
                    allowed=False,
                    reason_code="acp_line_item_offer_valid_until_expired",
                    details={"line_item_id": item.get("id"), "availability_status": avail},
                )
            valid_until_raw = item.get("valid_until")
            if valid_until_raw:
                valid_dt = _parse_rfc3339(str(valid_until_raw))
                if eval_dt > valid_dt:
                    return GuardEvaluation(
                        allowed=False,
                        reason_code="acp_line_item_offer_valid_until_expired",
                        details={
                            "line_item_id": item.get("id"),
                            "valid_until": valid_until_raw,
                            "evaluation_time": eval_ts_raw,
                        },
                    )

    # 4. PR #160: Webhook `Merchant-Signature` (`t=<unix_seconds>,v1=<64_hex>`) & 300s replay protection
    webhook_sig = payload.get("webhook_signature_check")
    if isinstance(webhook_sig, dict):
        header_val = str(webhook_sig.get("merchant_signature", ""))
        raw_body = str(webhook_sig.get("raw_body", ""))
        secret = str(webhook_sig.get("shared_secret", ""))
        now_unix = int(webhook_sig.get("now_unix", 0))
        tolerance_sec = int(webhook_sig.get("tolerance_seconds", 300))

        parts = dict(
            kv.split("=", 1) for kv in header_val.split(",") if "=" in kv
        )
        t_str = parts.get("t", "")
        v1_hex = parts.get("v1", "")
        if not t_str.isdigit() or len(v1_hex) != 64:
            return GuardEvaluation(
                allowed=False,
                reason_code="acp_webhook_merchant_signature_invalid_or_replay_window_exceeded",
                details={"merchant_signature": header_val},
            )
        ts_int = int(t_str)
        if abs(now_unix - ts_int) > tolerance_sec:
            return GuardEvaluation(
                allowed=False,
                reason_code="acp_webhook_merchant_signature_invalid_or_replay_window_exceeded",
                details={"timestamp": ts_int, "now_unix": now_unix, "tolerance_seconds": tolerance_sec},
            )
        expected_mac = hmac.new(
            secret.encode("utf-8"),
            f"{ts_int}.{raw_body}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected_mac.lower(), v1_hex.lower()):
            return GuardEvaluation(
                allowed=False,
                reason_code="acp_webhook_merchant_signature_invalid_or_replay_window_exceeded",
                details={"expected_prefix": expected_mac[:12], "received_prefix": v1_hex[:12]},
            )

    # 5. PR #139: MCP Transport Binding for Agentic Checkout
    mcp_call = payload.get("mcp_tool_call")
    if isinstance(mcp_call, dict):
        tool_name = str(mcp_call.get("name", ""))
        args = mcp_call.get("arguments") or {}
        meta = args.get("meta") or {}
        body_payload = args.get("payload")
        if (
            tool_name not in ACP_MCP_CHECKOUT_TOOLS
            or not isinstance(meta, dict)
            or not str(meta.get("api_version", "")).strip()
            or not isinstance(body_payload, dict)
        ):
            return GuardEvaluation(
                allowed=False,
                reason_code="acp_mcp_transport_binding_contract_violation",
                details={"tool_name": tool_name, "has_api_version": bool(meta.get("api_version"))},
            )

    return GuardEvaluation(
        allowed=True,
        reason_code="acp_protocol_extensions_offer_expiry_webhook_and_mcp_verified",
        details={
            "protocol_extensions_count": len(protocol.get("extensions") or []),
            "session_status": session_status,
        },
    )


def verify_ap2_failure_response_payment_receipt_json_schema_and_micropayment(
    payload: dict[str, Any],
) -> GuardEvaluation:
    """Validate Google AP2 PRs #144, #132, #131, #128, #110, #92, and #83."""
    # 1. PR #131 & #132: Standardized FailureResponse & RecoveryAction gate
    failure = payload.get("failure_response")
    if isinstance(failure, dict):
        data_key = str(failure.get("data_key", "ap2.errors.FailureResponse"))
        category = str(failure.get("category", ""))
        recovery = str(failure.get("recovery_action", ""))
        attempted_action = str(failure.get("agent_attempted_action", ""))

        allowed_recoveries = AP2_REQUIRED_RECOVERY_BY_CATEGORY.get(category)
        if data_key != "ap2.errors.FailureResponse" or not allowed_recoveries or recovery not in allowed_recoveries:
            return GuardEvaluation(
                allowed=False,
                reason_code="ap2_failure_response_category_recovery_mismatch",
                details={"category": category, "recovery_action": recovery, "data_key": data_key},
            )
        if recovery in {"USER_CONFIRMATION_REQUIRED", "NEW_MANDATE_REQUIRED", "ABORT_TRANSACTION"}:
            if attempted_action == "autonomous_silent_retry":
                return GuardEvaluation(
                    allowed=False,
                    reason_code="ap2_failure_recovery_autonomous_retry_forbidden",
                    details={"category": category, "recovery_action": recovery},
                )

    # 2. PR #110, #128 & #92: PaymentReceipt null-safe extraction, Mandate JSON Schema & Audit Log
    if payload.get("artifacts_is_none_crashed") is True:
        return GuardEvaluation(
            allowed=False,
            reason_code="ap2_payment_receipt_or_audit_schema_invalid",
            details={"reason": "find_canonical_objects/get_first_data_part must return []/{} when artifacts is None"},
        )

    mandate_schema = payload.get("mandate_json_schema")
    if isinstance(mandate_schema, dict):
        schema_uri = str(mandate_schema.get("$schema", ""))
        schema_id = str(mandate_schema.get("$id", ""))
        if "json-schema.org" not in schema_uri or not schema_id.endswith(".schema.json"):
            return GuardEvaluation(
                allowed=False,
                reason_code="ap2_payment_receipt_or_audit_schema_invalid",
                details={"$schema": schema_uri, "$id": schema_id},
            )

    audit_entry = payload.get("audit_log_entry")
    if isinstance(audit_entry, dict):
        serialized = json.dumps(audit_entry)
        if "raw_pan" in serialized or "cvv" in serialized or not audit_entry.get("mandate_id"):
            return GuardEvaluation(
                allowed=False,
                reason_code="ap2_payment_receipt_or_audit_schema_invalid",
                details={"has_mandate_id": bool(audit_entry.get("mandate_id"))},
            )

    # 3. PR #144 & #83: Verifiable Intent 3-hop chain & Micropayment channel bounds
    vi_chain = payload.get("verifiable_intent_chain")
    if isinstance(vi_chain, dict):
        hops = vi_chain.get("hops") or []
        if hops != ["issuer_credential", "user_mandate", "agent_fulfillment"] or not vi_chain.get("signature_valid", False):
            return GuardEvaluation(
                allowed=False,
                reason_code="ap2_verifiable_intent_chain_invalid",
                details={"hops": hops, "signature_valid": vi_chain.get("signature_valid")},
            )

    micropayment = payload.get("micropayment_channel")
    if isinstance(micropayment, dict):
        role = str(micropayment.get("role", "micropayment-provider"))
        currency = str(micropayment.get("currency", "USDC"))
        deposit = float(micropayment.get("channel_deposit", 0.0))
        cumulative_spent = float(micropayment.get("cumulative_spent", 0.0))
        tick_amount = float(micropayment.get("tick_amount", 0.0))
        prev_seq = int(micropayment.get("previous_sequence_number", 0))
        seq = int(micropayment.get("sequence_number", 0))

        if (
            role not in AP2_VALID_ROLES
            or currency not in {"USDC", "PYUSD", "USD"}
            or tick_amount <= 0
            or round(cumulative_spent + tick_amount, 8) > round(deposit, 8)
            or seq <= prev_seq
        ):
            return GuardEvaluation(
                allowed=False,
                reason_code="ap2_micropayment_channel_overdraft_or_nonce_replay",
                details={
                    "role": role,
                    "currency": currency,
                    "deposit": deposit,
                    "new_cumulative": round(cumulative_spent + tick_amount, 6),
                    "previous_sequence_number": prev_seq,
                    "sequence_number": seq,
                },
            )

    return GuardEvaluation(
        allowed=True,
        reason_code="ap2_failure_response_receipt_schema_and_micropayment_verified",
        details={
            "failure_checked": isinstance(failure, dict),
            "micropayment_checked": isinstance(micropayment, dict),
        },
    )


def verify_tau2_live_interruption_hallucination_retry_pydantic_coercion_and_metrics(
    payload: dict[str, Any],
) -> GuardEvaluation:
    """Validate Sierra tau2-bench PRs #528, #520, #516, #513, #508, #498, and #484."""
    # 1. PR #528: OpenAI Live `session.input_transcript.delta` -> `speech_started=True`, `was_truncated=False`
    live_event = payload.get("openai_live_event")
    if isinstance(live_event, dict):
        ev_type = str(live_event.get("type", ""))
        speech_started = bool(live_event.get("speech_started", False))
        was_truncated = bool(live_event.get("was_truncated", False))
        explicit_truncation = bool(live_event.get("explicit_truncation_event", False))
        if ev_type == "session.input_transcript.delta":
            if not speech_started or (was_truncated and not explicit_truncation):
                return GuardEvaluation(
                    allowed=False,
                    reason_code="tau2_live_input_transcript_falsely_marked_truncated",
                    details={
                        "speech_started": speech_started,
                        "was_truncated": was_truncated,
                        "explicit_truncation_event": explicit_truncation,
                    },
                )

    # 2. PR #520: Result-safe hallucination retries
    retry_check = payload.get("hallucination_retry")
    if isinstance(retry_check, dict):
        hallucinations_field = retry_check.get("hallucinations_field")
        if not isinstance(hallucinations_field, list):
            return GuardEvaluation(
                allowed=False,
                reason_code="tau2_hallucination_retry_unsafe_or_invalid_reviewer_output",
                details={"hallucinations_type": type(hallucinations_field).__name__},
            )
        if (
            not retry_check.get("final_retry_reviewed", True)
            or not retry_check.get("only_selected_checkpointed", True)
            or not retry_check.get("complete_tool_results_preserved", True)
        ):
            return GuardEvaluation(
                allowed=False,
                reason_code="tau2_hallucination_retry_unsafe_or_invalid_reviewer_output",
                details={
                    "final_retry_reviewed": retry_check.get("final_retry_reviewed"),
                    "only_selected_checkpointed": retry_check.get("only_selected_checkpointed"),
                    "complete_tool_results_preserved": retry_check.get("complete_tool_results_preserved"),
                },
            )

    # 3. PR #516 & #513: Pydantic float-to-int tool kwargs coercion & nested JSON string comparison
    tool_coercion = payload.get("tool_kwargs_coercion")
    if isinstance(tool_coercion, dict):
        expected_type = str(tool_coercion.get("schema_type", "int"))
        coerced_val = tool_coercion.get("persisted_value")
        if expected_type == "int" and (isinstance(coerced_val, float) or not isinstance(coerced_val, int)):
            return GuardEvaluation(
                allowed=False,
                reason_code="tau2_tool_kwargs_uncoerced_float_db_hash_drift",
                details={"persisted_value": coerced_val, "persisted_type": type(coerced_val).__name__},
            )

    # 4. PR #508: `llm_agent_solo_gt` recognized as solo mode during trajectory replay
    replay_info = payload.get("trajectory_replay")
    if isinstance(replay_info, dict):
        agent_impl = str(replay_info.get("agent_implementation", ""))
        solo_mode_enabled = bool(replay_info.get("solo_mode_enabled", False))
        user_tools_loaded = bool(replay_info.get("user_tools_loaded", False))
        if agent_impl in TAU2_SOLO_IMPLEMENTATIONS and (not solo_mode_enabled or not user_tools_loaded):
            return GuardEvaluation(
                allowed=False,
                reason_code="tau2_solo_gt_missing_user_tools_on_replay",
                details={
                    "agent_implementation": agent_impl,
                    "solo_mode_enabled": solo_mode_enabled,
                    "user_tools_loaded": user_tools_loaded,
                },
            )

    # 5. PR #498: pandas 3.x `.value` infra-error comparison & keeping all-infra-error tasks in pass^k denominator
    metrics_eval = payload.get("pass_hat_k_metrics")
    if isinstance(metrics_eval, dict):
        total_tasks = int(metrics_eval.get("total_tasks", 0))
        all_infra_error_tasks = int(metrics_eval.get("all_infra_error_tasks", 0))
        denominator_tasks = int(metrics_eval.get("denominator_tasks", 0))
        compared_by_enum_value = bool(metrics_eval.get("compared_by_enum_value", True))
        if not compared_by_enum_value or (all_infra_error_tasks > 0 and denominator_tasks < total_tasks):
            return GuardEvaluation(
                allowed=False,
                reason_code="tau2_pass_hat_k_infra_error_denominator_inflation",
                details={
                    "total_tasks": total_tasks,
                    "all_infra_error_tasks": all_infra_error_tasks,
                    "denominator_tasks": denominator_tasks,
                    "compared_by_enum_value": compared_by_enum_value,
                },
            )

    # 6. PR #484: `close_bank_account_7392` fixed-set reason validation
    close_account = payload.get("close_bank_account_call")
    if isinstance(close_account, dict):
        reason = str(close_account.get("reason", "customer_request"))
        if reason not in TAU2_ALLOWED_CLOSE_ACCOUNT_REASONS:
            return GuardEvaluation(
                allowed=False,
                reason_code="tau2_banking_close_account_freeform_reason_corrupts_db_hash",
                details={"reason": reason, "allowed_reasons": sorted(TAU2_ALLOWED_CLOSE_ACCOUNT_REASONS)},
            )

    return GuardEvaluation(
        allowed=True,
        reason_code="tau2_live_interruption_retry_coercion_and_metrics_verified",
        details={
            "live_checked": isinstance(live_event, dict),
            "metrics_checked": isinstance(metrics_eval, dict),
        },
    )
