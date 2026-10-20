"""Stage 64 deterministic runtime guards across UCP, ACP, Google AP2, and Sierra tau2-bench.

Covers:
1. UCP PRs #833, #831, #791, #789, #785:
   - Service `schema` transport-definition media-type polymorphism (`rest` -> OpenAPI 3.1,
     `mcp`/`embedded` -> OpenRPC 1.3.2, `a2a` -> absent / resolved via `endpoint` Agent Card)
     vs. JSON Schema 2020-12 on `capabilities` and `payment_handlers` (#833).
   - Reserved `ucp_` prefix linter rule `W007` (only `ucp_request` and `ucp_response` allowed;
     `$defs/ucp_agent` renamed to `$defs/agent` in `mcp_tool_call.json`, #831).
   - Payment handler participant identifier (`identity.access_token` is a participant identifier,
     never caller authentication per Binding rule 4; `config.business_id` mapping;
     `encrypted-credential` omits `/tokenize` and `/detokenize`, #791).
   - Shopping permalink CSRF-class cart merge guard requiring explicit buyer action on rendered
     state before merging into an authenticated buyer's cart (#789 / #666).
   - `sign_rest_request` RFC 9421 component coverage requiring both `"ucp-agent"` and
     `"signature-agent";key="<label>"` (when `Signature-Agent` header is present) and checking
     `body_bytes` (#785).
2. ACP PRs #156, #150, #144, #166, #151:
   - `com.stripe.link` accelerated-checkout wallet payment handler (buyer authenticates with
     Link via email + OTP, Link returns scoped wallet token delegated via `delegate_payment`,
     no raw PAN/CVC exposure to agent or seller, #156).
   - Wallet `InterventionCapabilities` (`redirect`, `webview`, `otp`), `InterventionContext`,
     and `InterventionResponse` on checkout session create/update (#150).
   - All 11 `CheckoutSessionBase.status` values, `in_progress` vs `complete_in_progress`
     in-flight payment guard, and terminal state immutability (`completed`, `canceled`,
     `expired`, #144).
   - On-chain token-eligibility single-use discount (`duration="once"`, 30-min TTL, per-item
     `allocations[]` sum invariant, #166) and 10 canonical `intent_trace.reason_code` values (#151).
3. Google AP2 PRs #252 (#207), #228, #229:
   - Cross-merchant atomic Budget Authority (`authorize`, `commit`, `refund`, `query`) preventing
     independent per-merchant `BudgetEvaluator` TOCTOU overspending (#252 / #207).
   - Human-present Solana Pay single-use `reference` pubkey deterministic binding to signed
     `PaymentMandate` (`recipient`, `amount`, `spl_mint`, single-use `reference`, #228).
   - `AP2-Haggle` (`ap2haggle/ap2/extensions/haggle/v0.1`) multi-round negotiation constraints,
     non-binding intermediate `Offer`, and merchant-signed `CartMandate` on `NegotiationOutcome` (#229).
4. Sierra tau2-bench PRs #580 (#499), #581 (#554), #584 (#553), #593 (#556), #600 (#576), #588 (#586):
   - Incomplete gold DB state certification withdrawal when a state-mutating golden action raises
     during reference replay (`is_mutating_tool`, `db_check=None`, `analyze_reward` `.get()` guard, #580).
   - NL-assertion judge verdict count verification (`len(verdicts) == len(nl_assertions)`, #581)
     and omission of contentless tool-call turns (`content is None`, `"assistant: None"`, #584).
   - Separate `evaluator_cost` and `evaluator_usage` accounting on `RewardInfo` and `SimulationRun` (#593).
   - Telecom user-simulator `check_status_bar` tool grounding (#600) and banking sandbox `srt`
     `SIGTERM` before `SIGKILL` to prevent orphaned `socat` proxy leaks (#588).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


ALLOWED_UCP_ANNOTATIONS: frozenset[str] = frozenset({"ucp_request", "ucp_response"})

ACP_ALL_11_SESSION_STATUSES: frozenset[str] = frozenset(
    {
        "not_ready_for_payment",
        "ready_for_payment",
        "in_progress",
        "complete_in_progress",
        "completed",
        "canceled",
        "expired",
        "incomplete",
        "requires_escalation",
        "pending_approval",
        "authentication_required",
    }
)

ACP_TERMINAL_SESSION_STATUSES: frozenset[str] = frozenset(
    {"completed", "canceled", "expired"}
)

ACP_SUPPORTED_INTERVENTION_TYPES: frozenset[str] = frozenset(
    {"3ds", "biometric", "address_verification", "redirect", "webview", "otp"}
)

ACP_INTENT_TRACE_REASON_CODES: frozenset[str] = frozenset(
    {
        "price_sensitivity",
        "shipping_cost",
        "delivery_timing",
        "out_of_stock",
        "payment_declined",
        "found_better_alternative",
        "user_abandoned",
        "comparison_shopping",
        "policy_restriction",
        "other",
    }
)


@dataclass(frozen=True)
class UCPServiceSchemaPermalinkSignAuditResult:
    passed: bool
    service_schema_valid: bool
    w007_prefix_clean: bool
    participant_id_auth_rejected: bool
    permalink_cart_merge_safe: bool
    wba_signature_coverage_valid: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class ACPLinkInterventionSessionStatusAuditResult:
    passed: bool
    stripe_link_handler_valid: bool
    intervention_flow_valid: bool
    session_state_transition_valid: bool
    onchain_discount_valid: bool
    intent_trace_valid: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class AP2CrossMerchantBudgetSolanaHaggleAuditResult:
    passed: bool
    budget_authority_atomic_valid: bool
    remaining_budget_minor: int
    solana_pay_reference_bound: bool
    haggle_outcome_valid: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class Tau2GoldReplayNLJudgeCostSandboxAuditResult:
    passed: bool
    gold_db_certification_valid: bool
    db_check_withheld: bool
    nl_judge_verdicts_and_prompt_valid: bool
    evaluator_cost_separated: bool
    telecom_and_sandbox_valid: bool
    reason_codes: tuple[str, ...]


def verify_ucp_service_schema_w007_permalink_and_wba_signing(
    *,
    entity_registry: str,
    transport: str | None,
    schema_url: str | None,
    endpoint_url: str | None,
    schema_def_keys: Sequence[str],
    handler_type: str,
    identity_access_token_used_as_auth: bool,
    config_has_business_id: bool,
    encrypted_handler_exposes_tokenize_endpoints: bool,
    is_permalink_cart_merge: bool,
    explicit_buyer_action_on_rendered_state: bool,
    merge_trigger: str,
    has_ucp_agent_header: bool,
    has_signature_agent_header: bool,
    signature_agent_key_label: str | None,
    covered_components: Sequence[str],
    body_bytes_len: int,
) -> UCPServiceSchemaPermalinkSignAuditResult:
    """Enforce UCP PRs #833, #831, #791, #789, and #785."""
    reasons: list[str] = []

    # 1. UCP PR #833: Service schema vs Capability/PaymentHandler schema media-type polymorphism
    service_schema_valid = True
    if entity_registry == "services":
        if transport == "rest":
            if not schema_url or not schema_url.endswith(".openapi.json") or not endpoint_url:
                service_schema_valid = False
                reasons.append("ucp_service_schema_transport_format_mismatch")
        elif transport in {"mcp", "embedded"}:
            if not schema_url or not schema_url.endswith(".openrpc.json"):
                service_schema_valid = False
                reasons.append("ucp_service_schema_transport_format_mismatch")
            if transport == "mcp" and not endpoint_url:
                service_schema_valid = False
                reasons.append("ucp_service_mcp_missing_endpoint")
        elif transport == "a2a":
            if schema_url is not None or not endpoint_url:
                service_schema_valid = False
                reasons.append("ucp_service_a2a_schema_must_be_absent_use_endpoint_card")
        else:
            service_schema_valid = False
            reasons.append("ucp_service_unknown_transport")
    elif entity_registry in {"capabilities", "payment_handlers"}:
        if (
            not schema_url
            or not schema_url.endswith(".json")
            or schema_url.endswith(".openapi.json")
            or schema_url.endswith(".openrpc.json")
        ):
            service_schema_valid = False
            reasons.append("ucp_capability_or_handler_requires_json_schema")
    else:
        service_schema_valid = False
        reasons.append("ucp_unknown_entity_registry")

    # 2. UCP PR #831: Reserved `ucp_` prefix linter W007
    w007_prefix_clean = True
    for key in schema_def_keys:
        if key.startswith("ucp_") and key not in ALLOWED_UCP_ANNOTATIONS:
            w007_prefix_clean = False
            reasons.append("ucp_reserved_prefix_w007_violation")
            break

    # 3. UCP PR #791: Participant identifier (`identity.access_token`) & `config.business_id`
    participant_id_auth_rejected = True
    if identity_access_token_used_as_auth:
        participant_id_auth_rejected = False
        reasons.append("ucp_tokenizer_participant_id_used_as_authentication")
    if not config_has_business_id:
        participant_id_auth_rejected = False
        reasons.append("ucp_payment_handler_config_missing_business_id")
    if handler_type == "encrypted-credential" and encrypted_handler_exposes_tokenize_endpoints:
        participant_id_auth_rejected = False
        reasons.append("ucp_encrypted_credential_handler_must_not_expose_tokenize")

    # 4. UCP PR #789: Permalink CSRF-class cart merge guard (Fixes #666)
    permalink_cart_merge_safe = True
    if is_permalink_cart_merge:
        if (
            not explicit_buyer_action_on_rendered_state
            or merge_trigger in {"page_load", "redirect", "prefilled_auto_submit"}
        ):
            permalink_cart_merge_safe = False
            reasons.append("ucp_permalink_auto_cart_merge_without_buyer_action")

    # 5. UCP PR #785: `sign_rest_request` coverage for `ucp-agent`, `signature-agent`, and `body_bytes`
    wba_signature_coverage_valid = True
    comp_list = list(covered_components)
    if has_ucp_agent_header and "ucp-agent" not in comp_list:
        wba_signature_coverage_valid = False
        reasons.append("ucp_wba_signature_agent_or_ucp_agent_coverage_missing")
    if has_signature_agent_header:
        expected_sig_agent = (
            f'"signature-agent";key="{signature_agent_key_label}"'
            if signature_agent_key_label
            else "signature-agent"
        )
        if expected_sig_agent not in comp_list and "signature-agent" not in comp_list:
            wba_signature_coverage_valid = False
            reasons.append("ucp_wba_signature_agent_or_ucp_agent_coverage_missing")
    if body_bytes_len > 0:
        if "content-digest" not in comp_list or "content-type" not in comp_list:
            wba_signature_coverage_valid = False
            reasons.append("ucp_rest_signature_missing_body_bytes_coverage")

    passed = (
        service_schema_valid
        and w007_prefix_clean
        and participant_id_auth_rejected
        and permalink_cart_merge_safe
        and wba_signature_coverage_valid
        and not reasons
    )
    return UCPServiceSchemaPermalinkSignAuditResult(
        passed=passed,
        service_schema_valid=service_schema_valid,
        w007_prefix_clean=w007_prefix_clean,
        participant_id_auth_rejected=participant_id_auth_rejected,
        permalink_cart_merge_safe=permalink_cart_merge_safe,
        wba_signature_coverage_valid=wba_signature_coverage_valid,
        reason_codes=tuple(reasons),
    )


def verify_acp_stripe_link_intervention_session_states_and_discounts(
    *,
    payment_handler_id: str,
    agent_saw_raw_pan_or_cvc: bool,
    buyer_authenticated_with_wallet: bool,
    delegated_via_delegate_payment: bool,
    delegated_token: str | None,
    session_status: str,
    next_operation: str | None,
    intervention_required: bool,
    intervention_context: Mapping[str, Any] | None,
    intervention_response: Mapping[str, Any] | None,
    current_unix_ts: int,
    onchain_discount: Mapping[str, Any] | None,
    intent_trace_reason_code: str | None,
) -> ACPLinkInterventionSessionStatusAuditResult:
    """Enforce ACP PRs #156, #150, #144, #166, and #151."""
    reasons: list[str] = []

    # 1. ACP PR #156: Stripe Link (`com.stripe.link`) accelerated-checkout wallet handler
    stripe_link_handler_valid = True
    if payment_handler_id == "com.stripe.link":
        if agent_saw_raw_pan_or_cvc:
            stripe_link_handler_valid = False
            reasons.append("acp_link_handler_raw_pan_exposure_forbidden")
        if (
            not buyer_authenticated_with_wallet
            or not delegated_via_delegate_payment
            or not delegated_token
            or not delegated_token.startswith(("vt_", "spt_"))
        ):
            stripe_link_handler_valid = False
            reasons.append("acp_link_handler_unauthenticated_or_undelegated_token")

    # 2. ACP PR #150: Intervention types (`redirect`, `webview`, `otp`), context & response
    intervention_flow_valid = True
    if intervention_required or session_status == "authentication_required":
        if not isinstance(intervention_context, Mapping):
            intervention_flow_valid = False
            reasons.append("acp_intervention_context_missing_or_expired")
        else:
            itype = str(intervention_context.get("intervention_type", ""))
            expires_at = int(intervention_context.get("expires_at", 0))
            provider = str(intervention_context.get("provider", ""))
            if (
                itype not in ACP_SUPPORTED_INTERVENTION_TYPES
                or not provider
                or expires_at <= current_unix_ts
            ):
                intervention_flow_valid = False
                reasons.append("acp_intervention_context_missing_or_expired")
            if itype in {"redirect", "webview"} and not str(
                intervention_context.get("redirect_url", "")
            ).startswith("https://"):
                intervention_flow_valid = False
                reasons.append("acp_intervention_redirect_url_invalid")

            if intervention_response is not None:
                rtype = str(intervention_response.get("type", ""))
                expected_map = {
                    "otp": "otp",
                    "redirect": "redirect_complete",
                    "webview": "webview_complete",
                }
                if itype in expected_map and rtype != expected_map[itype]:
                    intervention_flow_valid = False
                    reasons.append("acp_intervention_response_type_mismatch")
                if rtype == "otp" and not str(intervention_response.get("code", "")).strip():
                    intervention_flow_valid = False
                    reasons.append("acp_intervention_otp_code_missing")

    # 3. ACP PR #144: All 11 session states, `complete_in_progress` lock, terminal immutability
    session_state_transition_valid = True
    if session_status not in ACP_ALL_11_SESSION_STATUSES:
        session_state_transition_valid = False
        reasons.append("acp_unknown_checkout_session_status")
    elif session_status == "complete_in_progress" and next_operation == "complete":
        session_state_transition_valid = False
        reasons.append("acp_duplicate_complete_while_complete_in_progress")
    elif session_status in ACP_TERMINAL_SESSION_STATUSES and next_operation in {
        "update",
        "complete",
        "cancel",
    }:
        session_state_transition_valid = False
        reasons.append("acp_terminal_session_state_mutation_forbidden")

    # 4. ACP PR #166: On-chain eligibility discount verification
    onchain_discount_valid = True
    if onchain_discount is not None:
        wallet_verified = bool(onchain_discount.get("wallet_holdings_verified", False))
        duration = str(onchain_discount.get("duration", ""))
        issued_at = int(onchain_discount.get("issued_at", 0))
        expires_at = int(onchain_discount.get("expires_at", 0))
        already_redeemed = bool(onchain_discount.get("already_redeemed", False))
        discount_amount = int(onchain_discount.get("amount_minor", 0))
        allocations = onchain_discount.get("allocations", [])
        alloc_sum = (
            sum(int(a.get("amount_minor", 0)) for a in allocations if isinstance(a, Mapping))
            if isinstance(allocations, Sequence)
            else -1
        )
        if (
            not wallet_verified
            or duration != "once"
            or already_redeemed
            or expires_at <= current_unix_ts
            or (expires_at - issued_at) > 1800
            or discount_amount <= 0
            or alloc_sum != discount_amount
        ):
            onchain_discount_valid = False
            reasons.append("acp_onchain_discount_allocation_or_expiry_invalid")

    # 5. ACP PR #151: Intent traces 10 canonical reason codes
    intent_trace_valid = True
    if intent_trace_reason_code is not None:
        if intent_trace_reason_code not in ACP_INTENT_TRACE_REASON_CODES:
            intent_trace_valid = False
            reasons.append("acp_intent_trace_unknown_reason_code")

    passed = (
        stripe_link_handler_valid
        and intervention_flow_valid
        and session_state_transition_valid
        and onchain_discount_valid
        and intent_trace_valid
        and not reasons
    )
    return ACPLinkInterventionSessionStatusAuditResult(
        passed=passed,
        stripe_link_handler_valid=stripe_link_handler_valid,
        intervention_flow_valid=intervention_flow_valid,
        session_state_transition_valid=session_state_transition_valid,
        onchain_discount_valid=onchain_discount_valid,
        intent_trace_valid=intent_trace_valid,
        reason_codes=tuple(reasons),
    )


def verify_ap2_cross_merchant_budget_solana_pay_and_haggle(
    *,
    budget_limit_minor: int,
    enforcement_mode: str,
    operations: Sequence[Mapping[str, Any]],
    solana_pay_settlement: Mapping[str, Any] | None,
    seen_solana_references: Sequence[str],
    haggle_session: Mapping[str, Any] | None,
) -> AP2CrossMerchantBudgetSolanaHaggleAuditResult:
    """Enforce Google AP2 PRs #252 (#207), #228, and #229."""
    reasons: list[str] = []

    # 1. AP2 PR #252 (#207): Cross-merchant atomic Budget Authority (authorize, commit, refund, query)
    budget_authority_atomic_valid = True
    held_by_auth_id: dict[str, int] = {}
    committed_by_auth_id: dict[str, int] = {}

    if enforcement_mode != "external_atomic_authority":
        budget_authority_atomic_valid = False
        reasons.append("ap2_cross_merchant_independent_evaluator_overspend")

    for op in operations:
        verb = str(op.get("verb", ""))
        auth_id = str(op.get("auth_id", ""))
        amount = int(op.get("amount_minor", 0))
        if verb == "authorize":
            total_reserved = sum(held_by_auth_id.values()) + sum(committed_by_auth_id.values())
            if amount <= 0 or not auth_id or auth_id in held_by_auth_id or (total_reserved + amount) > budget_limit_minor:
                budget_authority_atomic_valid = False
                reasons.append("ap2_budget_authority_hold_exceeded_or_unauthorized")
            else:
                held_by_auth_id[auth_id] = amount
        elif verb == "commit":
            if auth_id not in held_by_auth_id or held_by_auth_id[auth_id] != amount:
                budget_authority_atomic_valid = False
                reasons.append("ap2_budget_authority_commit_without_matching_hold")
            else:
                committed_by_auth_id[auth_id] = held_by_auth_id.pop(auth_id)
        elif verb == "refund":
            if auth_id in committed_by_auth_id and 0 < amount <= committed_by_auth_id[auth_id]:
                committed_by_auth_id[auth_id] -= amount
            elif auth_id in held_by_auth_id and amount == held_by_auth_id[auth_id]:
                held_by_auth_id.pop(auth_id)
            else:
                budget_authority_atomic_valid = False
                reasons.append("ap2_budget_authority_invalid_refund")
        elif verb == "query":
            continue
        else:
            budget_authority_atomic_valid = False
            reasons.append("ap2_budget_authority_unknown_verb")

    remaining_budget_minor = max(
        0,
        budget_limit_minor - (sum(held_by_auth_id.values()) + sum(committed_by_auth_id.values())),
    )

    # 2. AP2 PR #228: Human-present Solana Pay single-use reference pubkey binding
    solana_pay_reference_bound = True
    if solana_pay_settlement is not None:
        ref_pubkey = str(solana_pay_settlement.get("reference_pubkey", ""))
        mandate_ref = str(solana_pay_settlement.get("mandate_reference_pubkey", ""))
        readonly_in_tx = bool(solana_pay_settlement.get("recorded_as_readonly_account", False))
        onchain_recipient = str(solana_pay_settlement.get("onchain_recipient", ""))
        mandate_recipient = str(solana_pay_settlement.get("mandate_recipient", ""))
        onchain_amount = int(solana_pay_settlement.get("onchain_amount_minor", -1))
        mandate_amount = int(solana_pay_settlement.get("mandate_amount_minor", -2))
        onchain_mint = str(solana_pay_settlement.get("onchain_spl_mint", ""))
        mandate_mint = str(solana_pay_settlement.get("mandate_spl_mint", ""))
        if (
            not ref_pubkey
            or len(ref_pubkey) < 32
            or ref_pubkey != mandate_ref
            or ref_pubkey in set(seen_solana_references)
            or not readonly_in_tx
            or onchain_recipient != mandate_recipient
            or onchain_amount != mandate_amount
            or not onchain_mint
            or onchain_mint != mandate_mint
        ):
            solana_pay_reference_bound = False
            reasons.append("ap2_solana_pay_reference_pubkey_reused_or_mismatched")

    # 3. AP2 PR #229: AP2-Haggle (`ap2haggle/ap2/extensions/haggle/v0.1`) negotiation guard
    haggle_outcome_valid = True
    if haggle_session is not None:
        ext_uri = str(haggle_session.get("extension_uri", ""))
        round_num = int(haggle_session.get("round_number", 0))
        max_rounds = int(haggle_session.get("max_rounds", 0))
        agreed_price = int(haggle_session.get("agreed_price_minor", 0))
        buyer_walk_away = int(haggle_session.get("buyer_walk_away_minor", 0))
        seller_cost_floor = int(haggle_session.get("seller_cost_floor_minor", 0))
        intermediate_offer_used_for_payment = bool(
            haggle_session.get("intermediate_offer_used_for_payment", False)
        )
        outcome_status = str(haggle_session.get("outcome_status", ""))
        has_merchant_signed_cart_mandate = bool(
            haggle_session.get("has_merchant_signed_cart_mandate", False)
        )
        if (
            ext_uri != "ap2haggle/ap2/extensions/haggle/v0.1"
            or round_num <= 0
            or round_num > max_rounds
            or intermediate_offer_used_for_payment
            or (
                outcome_status == "accepted"
                and (
                    not has_merchant_signed_cart_mandate
                    or agreed_price > buyer_walk_away
                    or agreed_price < seller_cost_floor
                )
            )
        ):
            haggle_outcome_valid = False
            reasons.append("ap2_haggle_unsigned_offer_or_constraint_violation")

    passed = (
        budget_authority_atomic_valid
        and solana_pay_reference_bound
        and haggle_outcome_valid
        and not reasons
    )
    return AP2CrossMerchantBudgetSolanaHaggleAuditResult(
        passed=passed,
        budget_authority_atomic_valid=budget_authority_atomic_valid,
        remaining_budget_minor=remaining_budget_minor,
        solana_pay_reference_bound=solana_pay_reference_bound,
        haggle_outcome_valid=haggle_outcome_valid,
        reason_codes=tuple(reasons),
    )


def verify_tau2_gold_replay_nl_judge_cost_and_sandbox(
    *,
    golden_actions: Sequence[Mapping[str, Any]],
    predicted_db_matches_gold_db: bool,
    reported_db_check: bool | None,
    reward_breakdown_has_db_key: bool,
    nl_assertions_count: int,
    nl_judge_verdicts_count: int,
    nl_judge_prompt_lines: Sequence[str],
    agent_cost: float,
    user_cost: float,
    evaluator_cost: float | None,
    evaluator_cost_merged_into_agent_cost: bool,
    telecom_grounding_tool_name: str,
    sandbox_timeout_signal_sequence: Sequence[str],
    orphaned_socat_processes: int,
) -> Tau2GoldReplayNLJudgeCostSandboxAuditResult:
    """Enforce Sierra tau2-bench PRs #580, #581, #584, #593, #600, and #588."""
    reasons: list[str] = []

    # 1. PR #580 (#499): Don't certify an incomplete gold DB state
    mutating_gold_failed = any(
        bool(a.get("is_mutating", True)) and bool(a.get("raised_exception", False))
        for a in golden_actions
    )
    gold_db_certification_valid = True
    db_check_withheld = False

    if mutating_gold_failed:
        if predicted_db_matches_gold_db:
            # Must withhold certification (`db_check=None`) and omit DB from `reward_breakdown`
            if reported_db_check is not None or reward_breakdown_has_db_key:
                gold_db_certification_valid = False
                reasons.append("tau2_incomplete_gold_db_state_false_certification")
            else:
                db_check_withheld = True
        else:
            # Write mismatch must still score `False` (`db_reward=0.0`), never upgraded to `None` or `True`
            if reported_db_check is not False:
                gold_db_certification_valid = False
                reasons.append("tau2_incomplete_gold_db_mismatch_must_remain_zero")
    else:
        # Read-only golden action failures must not invalidate `db_check`
        if reported_db_check is None:
            gold_db_certification_valid = False
            reasons.append("tau2_readonly_gold_failure_wrongly_withheld_db_check")

    # 2. PRs #581 (#554) & #584 (#553): NL-assertion verdict count & contentless turn filtering
    nl_judge_verdicts_and_prompt_valid = True
    if nl_assertions_count > 0 and nl_judge_verdicts_count != nl_assertions_count:
        nl_judge_verdicts_and_prompt_valid = False
        reasons.append("tau2_nl_judge_verdict_count_mismatch")

    if any(line.strip() == "assistant: None" for line in nl_judge_prompt_lines):
        nl_judge_verdicts_and_prompt_valid = False
        reasons.append("tau2_nl_judge_prompt_contains_contentless_none_turns")

    # 3. PR #593 (#556): Persist NL-judge `evaluator_cost` and `evaluator_usage` separately
    evaluator_cost_separated = True
    if (
        nl_assertions_count > 0
        and (
            evaluator_cost is None
            or evaluator_cost < 0.0
            or evaluator_cost_merged_into_agent_cost
            or agent_cost < 0.0
            or user_cost < 0.0
        )
    ):
        evaluator_cost_separated = False
        reasons.append("tau2_evaluator_cost_discarded_or_merged_into_agent_cost")

    # 4. PRs #600 (#576) & #588 (#586): Telecom `check_status_bar` grounding & `srt` SIGTERM cleanup
    telecom_and_sandbox_valid = True
    if telecom_grounding_tool_name != "check_status_bar":
        telecom_and_sandbox_valid = False
        reasons.append("tau2_telecom_unexposed_user_tool_grounding")

    sig_seq = list(sandbox_timeout_signal_sequence)
    if (
        not sig_seq
        or sig_seq[0] != "SIGTERM"
        or orphaned_socat_processes > 0
    ):
        telecom_and_sandbox_valid = False
        reasons.append("tau2_sandbox_timeout_sigkill_socat_proxy_leak")

    passed = (
        gold_db_certification_valid
        and nl_judge_verdicts_and_prompt_valid
        and evaluator_cost_separated
        and telecom_and_sandbox_valid
        and not reasons
    )
    return Tau2GoldReplayNLJudgeCostSandboxAuditResult(
        passed=passed,
        gold_db_certification_valid=gold_db_certification_valid,
        db_check_withheld=db_check_withheld,
        nl_judge_verdicts_and_prompt_valid=nl_judge_verdicts_and_prompt_valid,
        evaluator_cost_separated=evaluator_cost_separated,
        telecom_and_sandbox_valid=telecom_and_sandbox_valid,
        reason_codes=tuple(reasons),
    )
