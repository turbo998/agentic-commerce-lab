"""Stage 170 deterministic protocol & benchmark guardrails (2026-10-23 primary-source audit):
1. x402 Foundation (commits 2b06a54 #3023, 3bd3c1d #3738, 58a5d7d #3809, 5e8688a #3668,
   b5ee357 #3459, 9c50903 #3889, a9772e5 #3855, 470419d #3096, 2cf50eb #3893, 56054d8 #2730,
   and PRs #3910, #3894 on 2026-10-22..2026-10-23):
   - XRPL `upto` Payment Channel scheme (`specs/schemes/upto/scheme_upto_xrpl.md`, #3023):
     canonical CAIP-2 (`xrpl:0`, `xrpl:1`, `xrpl:2`), `asset == "XRP"`, `areFeesSponsored == False`,
     `CLM\\0` (`0x434C4D00`) + 32-byte `channelId` + big-endian uint64 `maxAmount` claim prefix with
     canonical low-`s` signature, verify-time rejection of `settlementTransaction`
     (`invalid_upto_xrpl_payload_unexpected_settlement_transaction`), 20-second landing margin floor on
     `CancelAfter` and `SettleDelay`, settle-time `payload.maxAmount` substitution for Rules 1 & 4,
     bare destination close when `settleAmount == 0` or `channelBalance >= settleAmount`, and atomic
     `(network, channelId)` deduplication.
   - HTTP `OPTIONS` preflight bypass on wildcard method-less routes (#3738) and browser CORS header
     directionality (`PAYMENT-SIGNATURE` in `Access-Control-Allow-Headers`, `PAYMENT-REQUIRED` and
     `PAYMENT-RESPONSE` in `Access-Control-Expose-Headers`, #3809).
   - Anti-wash self-payment prohibition (`payer !== payTo` -> `invalid_self_payment`, PR #3910),
     batch-settlement refund `Refunded` event fail-closed check (#3096), EVM gas sponsoring
     `readContract`/`rpcUrl` prerequisite (#3459/#3889), and paywall reflected XSS escaping (#3855).
2. Universal Commerce Protocol (UCP) (commit 5410813 #672 and PRs #890, #699, #782 on 2026-10-23):
   - Checkout status lifecycle transitions (#672): `ready_for_complete` supports transitions to
     `complete_in_progress`, `completed`, recoverable regression to `incomplete`, and buyer handoff
     to `requires_escalation`; terminal states (`completed`, `canceled`) cannot regress to active states.
   - Purchase Options extension & subscription policy (PR #890): `dev.ucp.shopping.purchase_options`
     and `dev.ucp.shopping.policy.subscription`; future recurring order `schedules` owe nothing at
     checkout and MUST NOT be added to checkout `totals`.
   - Signed REST response request-binding (PR #699) preventing TLS-terminating CDN/proxy stale replay,
     and operation-class idempotency payload identity (PR #782) binding `(idempotency_key, operation, target_id)`
     with signed MCP header precedence over `meta["idempotency-key"]`.
3. Stripe AI (`8a8818e` `8.0.5`, PRs #584, #542, #540) & MCP (`SEP-3415` Events Extension PR #3415):
   - Local `@stripe/mcp` proxy `registerTool` metadata preservation (`title` + `annotations`, PR #584).
   - Fast-fail JSON-RPC error response when forwarding a request fails (`isJSONRPCRequest == True`),
     while never replying to notifications or responses (PR #542).
   - Python `stripe-agent-toolkit` `mcp>=1.8.0,<2` and `openai-agents>=0.5.0` dependency bounds (PR #540),
     sandbox RAK guidance (`8a8818e`), and MCP `SEP-3415` `io.modelcontextprotocol/events` cursor/TTL rules.
4. Sierra tau2-bench 2.0 (commits cc1df47 #675, 14d65e8 #676, f3736fd #670, and PRs #674, #677):
   - Malformed tool-call arguments (non-JSON-object such as `42`, `null`, `[]`, or invalid JSON) and
     empty agent replies scored as `AGENT_ERROR` (`0.0` in denominator) instead of `INFRASTRUCTURE_ERROR`
     denominator exclusion (PR #674).
   - Retail `user_scenario.known_info` internal user ID leak prevention (`mei_kovacs_8020` -> `Mei Kovacs`,
     PR #677) and voice leaderboard release-date metadata integrity (#675, #676).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


CANONICAL_XRPL_NETWORKS = frozenset({"xrpl:0", "xrpl:1", "xrpl:2"})
XRPL_LANDING_MARGIN_SECONDS = 20
UCP_ACTIVE_STATES = frozenset(
    {"incomplete", "requires_escalation", "ready_for_complete", "complete_in_progress"}
)
UCP_TERMINAL_STATES = frozenset({"completed", "canceled"})
UCP_READY_FOR_COMPLETE_TARGETS = frozenset(
    {"incomplete", "requires_escalation", "complete_in_progress", "completed", "canceled"}
)


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    decision_code: str
    reason: str
    details: dict[str, Any]


def validate_x402_xrpl_upto_cors_and_anti_wash_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Validate x402 2026-10-23 commits (#3023, #3738, #3809, #3096, #3459, #3855, PR #3910)."""
    payer = str(payload.get("payer", "")).strip()
    pay_to = str(payload.get("pay_to", "")).strip()
    if payer and pay_to and payer.lower() == pay_to.lower():
        return GuardDecision(
            allowed=False,
            decision_code="X402_SELF_PAYMENT_PROHIBITED",
            reason="Facilitator verify/settle must reject self-payments where payer equals payTo with invalid_self_payment (PR #3910).",
            details={"payer": payer, "pay_to": pay_to},
        )

    xrpl_upto = payload.get("xrpl_upto", {})
    if isinstance(xrpl_upto, Mapping) and xrpl_upto:
        network = str(xrpl_upto.get("network", ""))
        if network not in CANONICAL_XRPL_NETWORKS:
            return GuardDecision(
                allowed=False,
                decision_code="X402_XRPL_UPTO_NON_CANONICAL_NETWORK",
                reason="XRPL upto requires canonical CAIP-2 network identifier xrpl:0, xrpl:1, or xrpl:2 (#3023).",
                details={"network": network},
            )
        if xrpl_upto.get("asset", "XRP") != "XRP" or xrpl_upto.get("are_fees_sponsored", False) is not False:
            return GuardDecision(
                allowed=False,
                decision_code="X402_XRPL_UPTO_ASSET_OR_SPONSOR_INVALID",
                reason="XRPL upto requires asset=='XRP' in drops and extra.areFeesSponsored==false (#3023).",
                details=dict(xrpl_upto),
            )
        if xrpl_upto.get("claim_prefix", "434C4D00") != "434C4D00" or xrpl_upto.get("low_s_canonical", True) is not True:
            return GuardDecision(
                allowed=False,
                decision_code="X402_XRPL_UPTO_CLAIM_SIGNATURE_NON_CANONICAL",
                reason="XRPL upto claim signature must sign CLM\\0 (0x434C4D00) + channelId + uint64 maxAmount with canonical low-s (#3023 Rule 5).",
                details=dict(xrpl_upto),
            )

        phase = str(xrpl_upto.get("phase", "verify"))
        max_amount = int(xrpl_upto.get("max_amount", 0))
        max_timeout = int(xrpl_upto.get("max_timeout_seconds", 300))
        min_settle_delay = int(xrpl_upto.get("min_settle_delay", 0))
        ledger_close = int(xrpl_upto.get("ledger_close_time", 1000))
        cancel_after = int(xrpl_upto.get("cancel_after", ledger_close + max_timeout + XRPL_LANDING_MARGIN_SECONDS))
        settle_delay = int(xrpl_upto.get("settle_delay", max(max_timeout + XRPL_LANDING_MARGIN_SECONDS, min_settle_delay)))
        channel_balance = int(xrpl_upto.get("channel_balance", 0))

        if phase == "verify":
            if xrpl_upto.get("has_settlement_transaction") is True:
                return GuardDecision(
                    allowed=False,
                    decision_code="X402_XRPL_UPTO_UNEXPECTED_SETTLEMENT_TX_AT_VERIFY",
                    reason="Facilitator /verify must reject client payloads carrying settlementTransaction (#3023).",
                    details=dict(xrpl_upto),
                )
            required_headroom = max_timeout + XRPL_LANDING_MARGIN_SECONDS
            if (
                channel_balance != 0
                or xrpl_upto.get("expiration_set") is True
                or cancel_after < ledger_close + required_headroom
                or settle_delay < max(required_headroom, min_settle_delay)
            ):
                return GuardDecision(
                    allowed=False,
                    decision_code="X402_XRPL_UPTO_VERIFY_HEADROOM_OR_BALANCE_INVALID",
                    reason="XRPL upto /verify requires Balance==0, Expiration unset, and CancelAfter/SettleDelay >= maxTimeoutSeconds + 20s landing margin (#3023 Rules 6-7).",
                    details=dict(xrpl_upto),
                )
        elif phase == "settle":
            settle_amount = int(xrpl_upto.get("settle_amount", 0))
            if settle_amount > max_amount:
                return GuardDecision(
                    allowed=False,
                    decision_code="X402_XRPL_UPTO_SETTLEMENT_EXCEEDS_MAX_AMOUNT",
                    reason="XRPL upto /settle must reject settlement-time amount exceeding signed maxAmount (#3023).",
                    details=dict(xrpl_upto),
                )
            bare_close_required = settle_amount == 0 or channel_balance >= settle_amount
            has_claim_fields = bool(xrpl_upto.get("claim_fields_present", not bare_close_required))
            if bare_close_required and has_claim_fields:
                return GuardDecision(
                    allowed=False,
                    decision_code="X402_XRPL_UPTO_BARE_CLOSE_MUST_OMIT_CLAIM_FIELDS",
                    reason="Zero settlement or pre-delivered charge (Balance >= settleAmount) must use a bare tfClose omitting Balance/Amount/Signature/PublicKey (#3023).",
                    details=dict(xrpl_upto),
                )
            if not bare_close_required:
                tx_amount = int(xrpl_upto.get("tx_amount", max_amount))
                tx_balance = int(xrpl_upto.get("tx_balance", settle_amount))
                if tx_amount != max_amount or tx_balance != settle_amount:
                    return GuardDecision(
                        allowed=False,
                        decision_code="X402_XRPL_UPTO_CLAIM_AMOUNT_SUBSTITUTION_INVALID",
                        reason="PaymentChannelClaim Amount must remain signed maxAmount while Balance carries actual settleAmount (#3023).",
                        details=dict(xrpl_upto),
                    )
            if xrpl_upto.get("reverified_with_max_amount", True) is not True:
                return GuardDecision(
                    allowed=False,
                    decision_code="X402_XRPL_UPTO_REVERIFY_MUST_SUBSTITUTE_MAX_AMOUNT",
                    reason="Settle-time re-verification must substitute payload.maxAmount for requirements.amount in Rules 1 & 4 (#3023).",
                    details=dict(xrpl_upto),
                )

    cors_check = payload.get("cors_check", {})
    if isinstance(cors_check, Mapping) and cors_check:
        if (
            cors_check.get("http_method") == "OPTIONS"
            and cors_check.get("route_explicit_options", False) is False
            and cors_check.get("returned_status") == 402
        ):
            return GuardDecision(
                allowed=False,
                decision_code="X402_OPTIONS_PREFLIGHT_TREATED_AS_PAID",
                reason="Method-less wildcard routes must skip OPTIONS preflight and let CORS middleware answer instead of returning HTTP 402 (#3738).",
                details=dict(cors_check),
            )
        allow_headers = {h.upper() for h in cors_check.get("allow_headers", ["PAYMENT-SIGNATURE", "CONTENT-TYPE"])}
        expose_headers = {h.upper() for h in cors_check.get("expose_headers", ["PAYMENT-REQUIRED", "PAYMENT-RESPONSE"])}
        if "PAYMENT-SIGNATURE" not in allow_headers or not {"PAYMENT-REQUIRED", "PAYMENT-RESPONSE"}.issubset(expose_headers):
            return GuardDecision(
                allowed=False,
                decision_code="X402_BROWSER_CORS_HEADER_DIRECTION_INVALID",
                reason="Browser CORS must allow PAYMENT-SIGNATURE on request and expose PAYMENT-REQUIRED & PAYMENT-RESPONSE on response (#3809).",
                details=dict(cors_check),
            )

    if payload.get("batch_refund_missing_event") is True:
        return GuardDecision(
            allowed=False,
            decision_code="X402_BATCH_REFUND_MISSING_EVENT",
            reason="Batch-settlement refund must fail closed when receipt emits no matching Refunded amount (#3096).",
            details={},
        )

    if payload.get("evm_gas_sponsoring_missing_chain_read") is True:
        return GuardDecision(
            allowed=False,
            decision_code="X402_EVM_GAS_SPONSORING_MISSING_CHAIN_READ",
            reason="EVM gas sponsoring requires signer.readContract or EvmSchemeConfig.rpcUrl when advertised (#3459, #3889).",
            details={},
        )

    if payload.get("paywall_unescaped_html") is True:
        return GuardDecision(
            allowed=False,
            decision_code="X402_PAYWALL_REFLECTED_XSS_UNESCAPED",
            reason="Paywall HTML template must escape embedded EVM/SVM/AVM configuration to prevent reflected XSS (#3855).",
            details={},
        )

    return GuardDecision(
        allowed=True,
        decision_code="X402_XRPL_UPTO_CORS_AND_ANTI_WASH_OK",
        reason="x402 XRPL upto, CORS preflight/header directionality, and anti-wash invariants verified.",
        details={"payer": payer, "pay_to": pay_to},
    )


def validate_ucp_checkout_lifecycle_purchase_options_and_response_binding_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Validate UCP 2026-10-23 commit #672 (5410813) and PRs #890, #699, #782."""
    transition = payload.get("status_transition", {})
    if isinstance(transition, Mapping) and transition:
        from_state = str(transition.get("from_state", ""))
        to_state = str(transition.get("to_state", ""))
        if from_state in UCP_TERMINAL_STATES and to_state in UCP_ACTIVE_STATES:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_TERMINAL_STATE_REGRESSION_FORBIDDEN",
                reason="Terminal checkout states (completed, canceled) cannot transition back into active states (#672).",
                details=dict(transition),
            )
        if from_state == "ready_for_complete" and to_state not in UCP_READY_FOR_COMPLETE_TARGETS:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_INVALID_READY_FOR_COMPLETE_TRANSITION",
                reason="ready_for_complete may only transition to incomplete, requires_escalation, complete_in_progress, completed, or canceled (#672).",
                details=dict(transition),
            )

    purchase_opt = payload.get("purchase_option_check", {})
    if isinstance(purchase_opt, Mapping) and purchase_opt:
        selected_id = purchase_opt.get("selected_purchase_option_id")
        available_ids = set(purchase_opt.get("available_option_ids", []))
        if selected_id and available_ids and selected_id not in available_ids:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_PURCHASE_OPTION_ID_UNKNOWN",
                reason="selected_purchase_option_id must match an advertised variant purchase_options[].id (PR #890).",
                details=dict(purchase_opt),
            )
        if purchase_opt.get("has_recurring_schedules") is True:
            if int(purchase_opt.get("recurring_schedule_amount_in_totals", 0)) > 0:
                return GuardDecision(
                    allowed=False,
                    decision_code="UCP_RECURRING_SCHEDULE_OWED_AT_CHECKOUT_FORBIDDEN",
                    reason="Recurring order schedules represent future Orders; nothing is owed at checkout and they must not be added to totals (PR #890).",
                    details=dict(purchase_opt),
                )
            if purchase_opt.get("has_subscription_policy", True) is not True:
                return GuardDecision(
                    allowed=False,
                    decision_code="UCP_SUBSCRIPTION_POLICY_MISSING",
                    reason="A line with recurring order schedules must be governed by a dev.ucp.shopping.policy.subscription policy (PR #890).",
                    details=dict(purchase_opt),
                )

    resp_sig = payload.get("signed_response_check", {})
    if isinstance(resp_sig, Mapping) and resp_sig:
        if (
            resp_sig.get("bound_to_request_method_and_uri", True) is not True
            or resp_sig.get("stale_replayed_response", False) is True
        ):
            return GuardDecision(
                allowed=False,
                decision_code="UCP_SIGNED_RESPONSE_NOT_BOUND_TO_REQUEST",
                reason="Signed REST responses must bind to the originating request (@method, @target-uri, freshness) to prevent intermediary stale replay (PR #699).",
                details=dict(resp_sig),
            )

    idem = payload.get("idempotency_check", {})
    if isinstance(idem, Mapping) and idem:
        if (
            idem.get("stored_operation")
            and idem.get("current_operation")
            and (
                idem.get("stored_operation") != idem.get("current_operation")
                or idem.get("stored_target_id") != idem.get("current_target_id")
            )
        ):
            return GuardDecision(
                allowed=False,
                decision_code="UCP_IDEMPOTENCY_TARGET_MISMATCH",
                reason="Reusing an idempotency key with a different operation or target resource identifier must be rejected without executing (PR #782).",
                details=dict(idem),
            )
        if (
            idem.get("signed_mcp_request") is True
            and idem.get("header_idempotency_key") != idem.get("meta_idempotency_key")
        ):
            return GuardDecision(
                allowed=False,
                decision_code="UCP_MCP_IDEMPOTENCY_HEADER_META_MISMATCH",
                reason="On a signed MCP request, the covered Idempotency-Key header is authoritative and meta['idempotency-key'] must equal it (PR #782).",
                details=dict(idem),
            )

    return GuardDecision(
        allowed=True,
        decision_code="UCP_LIFECYCLE_PURCHASE_OPTIONS_AND_BINDING_OK",
        reason="UCP checkout status lifecycle, purchase_options subscription policy, request-bound response signature, and idempotency verified.",
        details={},
    )


def validate_stripe_mcp_proxy_metadata_forwarding_and_skills_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Validate Stripe AI 2026-10-23 commit 8a8818e (8.0.5), PRs #584, #542, #540, and MCP SEP-3415 (#3415)."""
    proxy_tool = payload.get("mcp_proxy_tool", {})
    if isinstance(proxy_tool, Mapping) and proxy_tool:
        if (
            proxy_tool.get("preserved_title", True) is not True
            or proxy_tool.get("preserved_annotations", True) is not True
        ):
            return GuardDecision(
                allowed=False,
                decision_code="STRIPE_MCP_PROXY_METADATA_DROPPED",
                reason="Local @stripe/mcp proxy must use registerTool to preserve remote tool title and safety annotations (PR #584).",
                details=dict(proxy_tool),
            )

    forwarding = payload.get("mcp_forwarding_failure", {})
    if isinstance(forwarding, Mapping) and forwarding:
        is_request = bool(forwarding.get("is_jsonrpc_request", True))
        replied_with_error = bool(forwarding.get("replied_with_jsonrpc_error", True))
        if is_request and not replied_with_error:
            return GuardDecision(
                allowed=False,
                decision_code="STRIPE_MCP_FORWARDING_REQUEST_DROPPED",
                reason="When forwarding a JSON-RPC request to mcp.stripe.com fails (e.g., HTTP 401), the stdio proxy must immediately return a JSON-RPC error instead of hanging 60s (PR #542).",
                details=dict(forwarding),
            )
        if not is_request and replied_with_error:
            return GuardDecision(
                allowed=False,
                decision_code="STRIPE_MCP_NOTIFICATION_MUST_NOT_REPLY",
                reason="JSON-RPC notifications and client responses must never receive an error reply on forwarding failure (PR #542).",
                details=dict(forwarding),
            )

    py_deps = payload.get("python_toolkit_deps", {})
    if isinstance(py_deps, Mapping) and py_deps:
        if (
            py_deps.get("mcp_major_version", 1) >= 2
            or py_deps.get("openai_extra_package", "openai-agents") != "openai-agents"
        ):
            return GuardDecision(
                allowed=False,
                decision_code="STRIPE_PYTHON_TOOLKIT_MCP2_OR_AGENTS_DEP_INVALID",
                reason="stripe-agent-toolkit requires mcp>=1.8.0,<2 (preserving streamablehttp_client) and openai-agents>=0.5.0 (PR #540).",
                details=dict(py_deps),
            )

    mcp_events = payload.get("mcp_events_ext", {})
    if isinstance(mcp_events, Mapping) and mcp_events:
        if (
            mcp_events.get("delivery_mode") == "webhook"
            and mcp_events.get("standard_webhooks_signature_valid", True) is not True
        ):
            return GuardDecision(
                allowed=False,
                decision_code="MCP_EVENTS_WEBHOOK_SIGNATURE_INVALID",
                reason="MCP SEP-3415 webhook delivery requires valid Standard Webhooks signature and refreshed TTL (#3415).",
                details=dict(mcp_events),
            )
        if mcp_events.get("skipped_events_detected") is True and mcp_events.get("truncated_flag") is not True:
            return GuardDecision(
                allowed=False,
                decision_code="MCP_EVENTS_TRUNCATED_FLAG_REQUIRED",
                reason="MCP SEP-3415 cursor resume must set truncated=true when events were skipped (#3415).",
                details=dict(mcp_events),
            )

    return GuardDecision(
        allowed=True,
        decision_code="STRIPE_MCP_PROXY_TOOLKIT_AND_EVENTS_OK",
        reason="Stripe local MCP proxy metadata, fast-fail JSON-RPC error forwarding, Python dependency bounds, and MCP SEP-3415 Events verified.",
        details={},
    )


def validate_tau2_malformed_tool_call_scoring_and_pii_leak_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Validate Sierra tau2-bench 2.0 PRs #674, #677, #675, #676 (2026-10-23)."""
    trial = payload.get("orchestrator_trial", {})
    if isinstance(trial, Mapping) and trial:
        fault = trial.get("agent_fault")
        recorded_termination = trial.get("termination_reason")
        dropped_from_denominator = bool(trial.get("dropped_from_denominator", False))
        if fault in {"malformed_tool_arguments", "non_object_tool_arguments", "empty_agent_reply"}:
            if recorded_termination != "AGENT_ERROR" or dropped_from_denominator:
                return GuardDecision(
                    allowed=False,
                    decision_code="TAU2_AGENT_FAULT_MISCLASSIFIED_AS_INFRA_ERROR",
                    reason="Malformed/non-object tool-call arguments and empty agent replies must terminate as scored AGENT_ERROR (0.0), never INFRASTRUCTURE_ERROR dropped from denominator (PR #674).",
                    details=dict(trial),
                )

    retail_task = payload.get("retail_scenario_check", {})
    if isinstance(retail_task, Mapping) and retail_task:
        known_info = str(retail_task.get("known_info", ""))
        internal_user_id = str(retail_task.get("internal_user_id", "mei_kovacs_8020"))
        if internal_user_id and internal_user_id in known_info:
            return GuardDecision(
                allowed=False,
                decision_code="TAU2_KNOWN_INFO_INTERNAL_USER_ID_LEAK",
                reason="Retail user_scenario.known_info must state the user's natural name (Mei Kovacs) rather than leaking internal user_id mei_kovacs_8020 before find_user_id_by_name_zip (PR #677).",
                details=dict(retail_task),
            )

    voice_sub = payload.get("voice_submission_check", {})
    if isinstance(voice_sub, Mapping) and voice_sub:
        if not voice_sub.get("release_date") or voice_sub.get("legacy_ava_0_slug", False) is True:
            return GuardDecision(
                allowed=False,
                decision_code="TAU2_VOICE_SUBMISSION_METADATA_INVALID",
                reason="Voice leaderboard submissions require explicit model_release.release_date and canonical ava-zero / phonic-1 model identifiers (#675, #676).",
                details=dict(voice_sub),
            )

    return GuardDecision(
        allowed=True,
        decision_code="TAU2_MALFORMED_TOOL_SCORING_AND_RETAIL_PII_OK",
        reason="Sierra tau2-bench 2.0 AGENT_ERROR scoring, retail known_info user_id leak guard, and voice release metadata verified.",
        details={},
    )
