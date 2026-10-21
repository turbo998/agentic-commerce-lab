"""Stage 128 deterministic runtime guardrails.

Covers primary-source protocol & SDK controls audited on 2026-10-21:
1. x402 Foundation (#3735, #3733, #3731, #3728, #3726, #3725, #3723, #3718, #3717,
   #3715, #3711, #3710, #3707, #3702, #3700, #3699):
   - Python MCP payment approval & settlement outcome preservation (#3735): retries
     re-run approval checks; usage-charge calculation failures attempt cancellation
     instead of charging maxAmount; uncertain cancel is never reported as confirmed;
     tool output is preserved if receipt processing fails.
   - Facilitator-managed EVM batch-settlement voucher custody (#3725, #3726) &
     builder-code ERC-8021 Schema 2 settlement metadata `m` (#3723, #3711).
   - `skipHandler` before-handler settlement (#3718), gate-hook (`beforeVerify`/
     `beforeSettle`) throw fail-closed (#3702), and RFC 8785 JCS canonicalization for
     offer-receipt (#3700).
   - Transport & scheme guards: Next.js settled 204/205/304 null-body (#3733), Axios
     Cookie array preservation (#3728), Python client removal of response-only
     `Access-Control-Expose-Headers` (#3717), HTTP resource server rejection of V1
     payloads with 402 (#3715), SVM `upto` client v0 vs facilitator v1 transaction
     version gate (#3710), `knos-order` signed judge acceptance (#3731), `auth-capture`
     card opaque token + hold (#3707), and shared-node `lnbtc` issued-hash registry
     check (#3699).
2. Google UCP (#774, #773, #767, #766, #765, #762, #757, #753):
   - State-bound Cart Offer extension in `actions` map (#773) bound to
     `(applies_to.cart_id, applies_to.state_ref)` with immutable `(id, revision)`.
   - Tokenization resource binding (`type`, `id` replay check) separated from
     participant authorization (`identity` check, #762).
   - Location `filters.items` availability (#766), self-describing custom amenities
     (#765), and root-level `distance`/`serves` spatial relations with batch Lookup
     `inputs[]` correlation (#753).
   - Example validator whole-word `skip` + non-empty `reason` (#767) and bracket-quoted
     reverse-DNS JSONPath navigation (#774).
3. Stripe AI (#412), MCP (#3313, #3312, #3318), & Sierra tau2-bench (#562, #548, #533,
   #528, #525):
   - Stripe AI deprecation block on `registerPaidTool` / `experimental_PaidMcpAgent`
     (#412).
   - MCP `CallToolResult._meta["io.modelcontextprotocol/toolFailure"]` classification
     (#3313, #3312) and sequenced MAC-verified conversation handles (#3318).
   - Sierra tau2-bench `###OUT-OF-SCOPE###` premature abort zero-reward grading (#548),
     atomic checkpoint trajectory replacement (#533), fenced JSON NL-judge parsing
     (#562), and full-duplex `speech_started` vs `was_truncated` separation (#528, #525).
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json
import re
from typing import Any


@dataclass(frozen=True)
class GuardResult:
    allowed: bool
    code: str
    detail: str
    metadata: dict[str, Any]


def evaluate_x402_mcp_approval_and_settlement_guard(
    *,
    is_payment_retry: bool,
    approval_checked_on_retry: bool,
    usage_charge_calculation_failed: bool,
    charged_max_amount_on_calc_failure: bool,
    cancel_attempted_on_calc_failure: bool,
    cancel_outcome_uncertain: bool,
    reported_confirmed_cancellation: bool,
    receipt_processing_failed: bool,
    tool_output_preserved: bool,
) -> GuardResult:
    """Audit x402 #3735 Python MCP payment approval & settlement outcome preservation."""
    if is_payment_retry and not approval_checked_on_retry:
        return GuardResult(
            allowed=False,
            code="X402_MCP_PAYMENT_RETRY_BYPASSED_APPROVAL_BLOCKED",
            detail="Payment retries in MCP must re-run approval checks before submitting a new payment (#3735)",
            metadata={"is_payment_retry": is_payment_retry},
        )
    if usage_charge_calculation_failed:
        if charged_max_amount_on_calc_failure or not cancel_attempted_on_calc_failure:
            return GuardResult(
                allowed=False,
                code="X402_MCP_CALC_FAILURE_MAX_CHARGE_FALLBACK_BLOCKED",
                detail="Usage-charge calculation failure must attempt cancellation rather than charging maxAmount (#3735)",
                metadata={"charged_max_amount_on_calc_failure": charged_max_amount_on_calc_failure},
            )
    if cancel_outcome_uncertain and reported_confirmed_cancellation:
        return GuardResult(
            allowed=False,
            code="X402_MCP_UNCERTAIN_CANCEL_REPORTED_CONFIRMED_BLOCKED",
            detail="Uncertain payment cancellation outcome must not be reported as a confirmed cancellation (#3735)",
            metadata={"cancel_outcome_uncertain": True},
        )
    if receipt_processing_failed and not tool_output_preserved:
        return GuardResult(
            allowed=False,
            code="X402_MCP_RECEIPT_ERROR_DROPPED_TOOL_OUTPUT_BLOCKED",
            detail="Tool output must remain available even when post-settlement receipt processing fails (#3735)",
            metadata={"receipt_processing_failed": True},
        )
    return GuardResult(
        allowed=True,
        code="X402_MCP_APPROVAL_AND_SETTLEMENT_OUTCOMES_VERIFIED",
        detail="Python MCP payment retry approval, cancel-on-calc-failure, and tool output preservation verified",
        metadata={"tool_output_preserved": tool_output_preserved},
    )


def evaluate_x402_voucher_skip_gate_and_jcs_guard(
    *,
    voucher_manager: str = "server",
    facilitator_supported_modes: tuple[str, ...] = ("server", "facilitator"),
    handler_failed_before_settle: bool = False,
    settle_on_cancel_invoked: bool = True,
    client_payload_has_builder_m: bool = False,
    client_builder_m_ignored: bool = True,
    facilitator_builder_cbor_bytes: int = 128,
    builder_map_keys_sorted_bytewise: bool = True,
    skip_handler_returned: bool = False,
    flow_has_before_handler_settle: bool = True,
    before_handler_settle_executed: bool = True,
    gate_hook_phase: str = "beforeVerify",
    gate_hook_threw: bool = False,
    failed_closed_on_hook_throw: bool = True,
    jcs_has_lone_surrogate: bool = False,
    jcs_top_level_undefined: bool = False,
    jcs_control_char_escaped_as_u00xx: bool = False,
) -> GuardResult:
    """Audit x402 #3725/#3726 voucher custody, #3723/#3711 builder-code `m`, #3718 skipHandler, #3702 gate throw, & #3700 JCS."""
    if voucher_manager not in {"server", "facilitator"}:
        return GuardResult(
            allowed=False,
            code="X402_BATCH_VOUCHER_MANAGER_MODE_INVALID_BLOCKED",
            detail=f"Unsupported extra.voucherManager={voucher_manager!r} (#3725)",
            metadata={"voucher_manager": voucher_manager},
        )
    if voucher_manager == "facilitator" and "facilitator" not in facilitator_supported_modes:
        return GuardResult(
            allowed=False,
            code="X402_FACILITATOR_VOUCHER_CUSTODY_UNSUPPORTED_BLOCKED",
            detail="Facilitator does not advertise 'facilitator' voucher custody in /supported (#3725/#3726)",
            metadata={"facilitator_supported_modes": list(facilitator_supported_modes)},
        )
    if handler_failed_before_settle and voucher_manager == "facilitator" and not settle_on_cancel_invoked:
        return GuardResult(
            allowed=False,
            code="X402_BATCH_VOUCHER_SETTLE_ON_CANCEL_SKIPPED_BLOCKED",
            detail="SettleOnCancel must run on handler failure in facilitator-managed voucher mode (#3726)",
            metadata={"voucher_manager": voucher_manager},
        )
    if client_payload_has_builder_m and not client_builder_m_ignored:
        return GuardResult(
            allowed=False,
            code="X402_BUILDER_CODE_CLIENT_METADATA_M_ACCEPTED_BLOCKED",
            detail="Client-supplied builder-code settlement metadata `m` must be ignored (#3723/#3711)",
            metadata={"client_payload_has_builder_m": True},
        )
    if facilitator_builder_cbor_bytes > 65535 or not builder_map_keys_sorted_bytewise:
        return GuardResult(
            allowed=False,
            code="X402_BUILDER_CODE_CBOR_SIZE_OR_KEY_ORDER_INVALID_BLOCKED",
            detail="Builder-code CBOR metadata `m` must be <= 65535 bytes with bytewise-sorted map keys (#3723)",
            metadata={
                "facilitator_builder_cbor_bytes": facilitator_builder_cbor_bytes,
                "builder_map_keys_sorted_bytewise": builder_map_keys_sorted_bytewise,
            },
        )
    if skip_handler_returned and flow_has_before_handler_settle and not before_handler_settle_executed:
        return GuardResult(
            allowed=False,
            code="X402_SKIP_HANDLER_BYPASSED_BEFORE_HANDLER_SETTLE_BLOCKED",
            detail="onAfterVerify skipHandler must still execute before-handler settle on upfront flows (#3718)",
            metadata={"skip_handler_returned": True},
        )
    if gate_hook_threw and gate_hook_phase in {"beforeVerify", "beforeSettle"} and not failed_closed_on_hook_throw:
        return GuardResult(
            allowed=False,
            code="X402_GATE_HOOK_THROW_FAILED_OPEN_BLOCKED",
            detail=f"Gate hook throw in {gate_hook_phase} must fail closed with extension_hook_error (#3702)",
            metadata={"gate_hook_phase": gate_hook_phase},
        )
    if jcs_has_lone_surrogate or jcs_top_level_undefined or jcs_control_char_escaped_as_u00xx:
        return GuardResult(
            allowed=False,
            code="X402_OFFER_RECEIPT_RFC8785_JCS_VIOLATION_BLOCKED",
            detail="offer-receipt canonicalize must reject lone surrogates/undefined and use RFC 8785 short control escapes (#3700)",
            metadata={
                "jcs_has_lone_surrogate": jcs_has_lone_surrogate,
                "jcs_top_level_undefined": jcs_top_level_undefined,
                "jcs_control_char_escaped_as_u00xx": jcs_control_char_escaped_as_u00xx,
            },
        )
    return GuardResult(
        allowed=True,
        code="X402_VOUCHER_SKIP_GATE_AND_JCS_VERIFIED",
        detail="x402 voucher custody, builder-code metadata `m`, skipHandler settlement, gate fail-closed, and RFC 8785 JCS verified",
        metadata={"voucher_manager": voucher_manager},
    )


def evaluate_x402_transport_and_scheme_extensions_guard(
    *,
    http_status: int = 204,
    rebuilt_body_is_null: bool = True,
    axios_cookie_array_preserved: bool = True,
    python_retry_request_headers: tuple[str, ...] = ("PAYMENT-SIGNATURE",),
    payload_version: int = 2,
    v1_rejected_with_status: int = 402,
    svm_upto_actor: str = "client",  # "client" | "facilitator"
    svm_upto_tx_version: int = 0,
    knos_order_judge_signed_acceptance: bool = True,
    auth_capture_card_opaque_token: bool = True,
    auth_capture_pre_resource_hold: bool = True,
    lnbtc_shared_receiver_node: bool = False,
    lnbtc_issued_hash_recorded_and_matched: bool = True,
) -> GuardResult:
    """Audit x402 #3733, #3731, #3728, #3717, #3715, #3710, #3707, and #3699."""
    if http_status in {204, 205, 304} and not rebuilt_body_is_null:
        return GuardResult(
            allowed=False,
            code="X402_NEXT_NULL_BODY_STATUS_CORRUPTED_BLOCKED",
            detail=f"Settled Next.js {http_status} response must preserve a null body (#3733)",
            metadata={"http_status": http_status},
        )
    if not axios_cookie_array_preserved:
        return GuardResult(
            allowed=False,
            code="X402_AXIOS_COOKIE_ARRAY_STRINGIFIED_BLOCKED",
            detail="Axios paid retry must preserve Cookie arrays rather than comma-stringifying (#3728)",
            metadata={"axios_cookie_array_preserved": False},
        )
    lowered_req_headers = {h.lower() for h in python_retry_request_headers}
    if "access-control-expose-headers" in lowered_req_headers:
        return GuardResult(
            allowed=False,
            code="X402_PYTHON_CLIENT_RESPONSE_CORS_HEADER_ON_REQUEST_BLOCKED",
            detail="Python httpx/requests client retries must not send response-only Access-Control-Expose-Headers (#3717)",
            metadata={"python_retry_request_headers": list(python_retry_request_headers)},
        )
    if payload_version == 1 and v1_rejected_with_status != 402:
        return GuardResult(
            allowed=False,
            code="X402_PYTHON_HTTP_V1_PAYLOAD_500_CRASH_BLOCKED",
            detail="HTTP V2 resource server must reject V1 payloads with 402 rather than raising 500 AttributeError (#3715)",
            metadata={"v1_rejected_with_status": v1_rejected_with_status},
        )
    if svm_upto_actor == "client" and svm_upto_tx_version != 0:
        return GuardResult(
            allowed=False,
            code="X402_SVM_UPTO_CLIENT_V1_TRANSACTION_BLOCKED",
            detail="Untrusted client-authored SVM `upto` channel-open transactions must be limited to legacy/v0 (#3710)",
            metadata={"svm_upto_actor": svm_upto_actor, "svm_upto_tx_version": svm_upto_tx_version},
        )
    if not knos_order_judge_signed_acceptance:
        return GuardResult(
            allowed=False,
            code="X402_KNOS_ORDER_UNSIGNED_JUDGE_ACCEPTANCE_BLOCKED",
            detail="knos-order escrow release requires a signed acceptance from the designated judge (#3731)",
            metadata={"knos_order_judge_signed_acceptance": False},
        )
    if not auth_capture_card_opaque_token or not auth_capture_pre_resource_hold:
        return GuardResult(
            allowed=False,
            code="X402_AUTH_CAPTURE_CARD_BINDING_HOLD_MISSING_BLOCKED",
            detail="auth-capture card binding requires an opaque PSP token and a pre-resource authorization hold (#3707)",
            metadata={
                "auth_capture_card_opaque_token": auth_capture_card_opaque_token,
                "auth_capture_pre_resource_hold": auth_capture_pre_resource_hold,
            },
        )
    if lnbtc_shared_receiver_node and not lnbtc_issued_hash_recorded_and_matched:
        return GuardResult(
            allowed=False,
            code="X402_LNBTC_SHARED_NODE_UNISSUED_INVOICE_HASH_BLOCKED",
            detail="Shared-node lnbtc requires server-side issued (payment_hash, network, amount, request_hash) verification before /settle (#3699)",
            metadata={"lnbtc_shared_receiver_node": True},
        )
    return GuardResult(
        allowed=True,
        code="X402_TRANSPORT_AND_SCHEME_EXTENSIONS_VERIFIED",
        detail="x402 Next.js null-body, Axios Cookie array, Python V1/CORS, SVM upto v1 gate, knos-order, card auth-capture, and lnbtc verified",
        metadata={"svm_upto_tx_version": svm_upto_tx_version},
    )


def evaluate_ucp_offer_binding_location_and_validator_guard(
    *,
    offer_in_cart_actions_map: bool = True,
    uses_parallel_offers_available_array: bool = False,
    offer_bound_cart_id: str = "cart_101",
    current_cart_id: str = "cart_101",
    offer_bound_state_ref: str = "st_v3",
    current_cart_state_ref: str = "st_v3",
    offer_id_distinct_from_action_id: bool = True,
    token_binding_type: str = "checkout",
    token_binding_id: str = "chk_901",
    expected_binding_type: str = "checkout",
    expected_binding_id: str = "chk_901",
    caller_participant_authorized: bool = True,
    rule1_rejected_due_to_identity_omission: bool = False,
    location_uses_legacy_inventory_filter: bool = False,
    requested_item_ids: tuple[str, ...] = ("sku_1", "sku_2"),
    available_item_ids_at_location: tuple[str, ...] = ("sku_1", "sku_2", "sku_3"),
    custom_amenity_has_description_and_label: bool = True,
    spatial_relation_inside_filters_geo: bool = False,
    lookup_response_has_inputs_correlation: bool = True,
    annotation_skip_token: str = "skip",
    annotation_skip_reason: str = "illustrative fragment",
    bracket_quoted_jsonpath_supported: bool = True,
) -> GuardResult:
    """Audit UCP #773, #762, #766, #765, #753, #767, and #774."""
    if not offer_in_cart_actions_map or uses_parallel_offers_available_array:
        return GuardResult(
            allowed=False,
            code="UCP_CART_OFFER_PARALLEL_CARRIER_BLOCKED",
            detail="Cart Offer extension must reside in Cart `actions` map rather than `offers.available[]` (#773)",
            metadata={"uses_parallel_offers_available_array": uses_parallel_offers_available_array},
        )
    if (
        offer_bound_cart_id != current_cart_id
        or offer_bound_state_ref != current_cart_state_ref
        or not offer_id_distinct_from_action_id
    ):
        return GuardResult(
            allowed=False,
            code="UCP_CART_OFFER_STATE_REF_OR_IDENTITY_MISMATCH_BLOCKED",
            detail="Cart Offer must bind to current (cart_id, state_ref) and keep Offer (id, revision) distinct from Action id (#773)",
            metadata={
                "offer_bound_cart_id": offer_bound_cart_id,
                "current_cart_id": current_cart_id,
                "offer_bound_state_ref": offer_bound_state_ref,
                "current_cart_state_ref": current_cart_state_ref,
            },
        )
    if rule1_rejected_due_to_identity_omission:
        return GuardResult(
            allowed=False,
            code="UCP_BINDING_RULE1_CONFLATED_WITH_IDENTITY_BLOCKED",
            detail="Binding Rule 1 must compare only (type, id) and must not fail when direct Business detokenization omits identity (#762)",
            metadata={"rule1_rejected_due_to_identity_omission": True},
        )
    if (
        token_binding_type != expected_binding_type
        or token_binding_id != expected_binding_id
        or not caller_participant_authorized
    ):
        return GuardResult(
            allowed=False,
            code="UCP_RESOURCE_BINDING_OR_PARTICIPANT_AUTH_FAILED_BLOCKED",
            detail="Token detokenization failed resource (type, id) equality or participant authorization check (#762)",
            metadata={"caller_participant_authorized": caller_participant_authorized},
        )
    if location_uses_legacy_inventory_filter or not set(requested_item_ids).issubset(
        set(available_item_ids_at_location)
    ):
        return GuardResult(
            allowed=False,
            code="UCP_LOCATION_ITEM_AVAILABILITY_FILTER_VIOLATION_BLOCKED",
            detail="Location Search/Lookup must use `filters.items` and match only when every requested item is available (#766)",
            metadata={"location_uses_legacy_inventory_filter": location_uses_legacy_inventory_filter},
        )
    if not custom_amenity_has_description_and_label:
        return GuardResult(
            allowed=False,
            code="UCP_LOCATION_CUSTOM_AMENITY_NOT_SELF_DESCRIBING_BLOCKED",
            detail="Custom Location amenities must provide a business description and presentation label (#765)",
            metadata={"custom_amenity_has_description_and_label": False},
        )
    if spatial_relation_inside_filters_geo or not lookup_response_has_inputs_correlation:
        return GuardResult(
            allowed=False,
            code="UCP_LOCATION_SPATIAL_RELATION_OR_LOOKUP_CORRELATION_BLOCKED",
            detail="`distance` and `serves` must be root-level relations (not `filters.geo`) and Lookup must return `inputs[]` correlation (#753)",
            metadata={
                "spatial_relation_inside_filters_geo": spatial_relation_inside_filters_geo,
                "lookup_response_has_inputs_correlation": lookup_response_has_inputs_correlation,
            },
        )
    if annotation_skip_token != "skip" or not annotation_skip_reason.strip():
        return GuardResult(
            allowed=False,
            code="UCP_EXAMPLE_ANNOTATION_SKIP_TYPO_OR_EMPTY_REASON_BLOCKED",
            detail="Example annotation must use whole-word `skip` with a non-empty `reason` (#767)",
            metadata={
                "annotation_skip_token": annotation_skip_token,
                "annotation_skip_reason": annotation_skip_reason,
            },
        )
    if not bracket_quoted_jsonpath_supported:
        return GuardResult(
            allowed=False,
            code="UCP_JSONPATH_BRACKET_QUOTED_KEY_UNSUPPORTED_BLOCKED",
            detail="Validator JSONPath must support bracket-quoted reverse-DNS keys (#774)",
            metadata={"bracket_quoted_jsonpath_supported": False},
        )
    return GuardResult(
        allowed=True,
        code="UCP_OFFER_BINDING_LOCATION_AND_VALIDATOR_VERIFIED",
        detail="UCP state-bound Cart Offer, resource binding vs participant auth, Location availability/amenities/spatial, and validator verified",
        metadata={"offer_bound_state_ref": offer_bound_state_ref},
    )


def evaluate_stripe_mcp_tool_failure_and_tau2_abort_guard(
    *,
    uses_deprecated_register_paid_tool: bool = False,
    tool_failure_on_call_tool_result_meta: bool = True,
    tool_failure_class: str = "governance",
    tool_failure_code: str = "spend_limit_exceeded",
    tool_failure_correlation_id: str = "corr_991",
    conversation_handle_seq: int = 5,
    last_seen_conversation_seq: int = 4,
    conversation_handle_mac_valid: bool = True,
    conversation_principal_matches: bool = True,
    simulator_emitted_out_of_scope: bool = False,
    recorded_termination_reason: str = "USER_STOP",
    assigned_reward_on_abort: float = 0.0,
    checkpoint_unlinked_before_write_complete: bool = False,
    nl_judge_raw_response: str = '```json\n{"met": true, "reason": "verified"}\n```',
    live_speech_started_set_was_truncated: bool = False,
) -> GuardResult:
    """Audit Stripe AI #412, MCP #3313/#3312 & #3318, and Sierra tau2-bench #562, #548, #533, #528, #525."""
    if uses_deprecated_register_paid_tool:
        return GuardResult(
            allowed=False,
            code="STRIPE_DEPRECATED_REGISTER_PAID_TOOL_BLOCKED",
            detail="Deprecated `registerPaidTool` / `experimental_PaidMcpAgent` has been removed (#412)",
            metadata={"uses_deprecated_register_paid_tool": True},
        )
    if (
        not tool_failure_on_call_tool_result_meta
        or tool_failure_class not in {"capability", "reliability", "governance"}
        or not tool_failure_code.strip()
        or not tool_failure_correlation_id.strip()
    ):
        return GuardResult(
            allowed=False,
            code="MCP_STRUCTURED_TOOL_FAILURE_SCHEMA_INVALID_BLOCKED",
            detail="io.modelcontextprotocol/toolFailure must be on CallToolResult._meta with valid class, code, and correlationId (#3312/#3313)",
            metadata={
                "tool_failure_class": tool_failure_class,
                "tool_failure_correlation_id": tool_failure_correlation_id,
            },
        )
    if (
        conversation_handle_seq <= last_seen_conversation_seq
        or not conversation_handle_mac_valid
        or not conversation_principal_matches
    ):
        return GuardResult(
            allowed=False,
            code="MCP_CONVERSATION_HANDLE_SEQ_OR_MAC_INVALID_BLOCKED",
            detail="Verifiable conversation handle failed monotonic `seq`, edge MAC, or principal association (#3318)",
            metadata={
                "conversation_handle_seq": conversation_handle_seq,
                "last_seen_conversation_seq": last_seen_conversation_seq,
            },
        )
    if simulator_emitted_out_of_scope and (
        recorded_termination_reason == "USER_STOP" or assigned_reward_on_abort > 0.0
    ):
        return GuardResult(
            allowed=False,
            code="TAU2_OUT_OF_SCOPE_ABORT_GRADED_AS_USER_STOP_BLOCKED",
            detail="###OUT-OF-SCOPE### simulator abort must record its own termination reason and receive 0.0 reward (#548)",
            metadata={
                "recorded_termination_reason": recorded_termination_reason,
                "assigned_reward_on_abort": assigned_reward_on_abort,
            },
        )
    if checkpoint_unlinked_before_write_complete:
        return GuardResult(
            allowed=False,
            code="TAU2_CHECKPOINT_PREMATURE_UNLINK_DATA_LOSS_BLOCKED",
            detail="Checkpoint replacement must not unlink previous trajectory before replacement write + os.replace completes (#533)",
            metadata={"checkpoint_unlinked_before_write_complete": True},
        )
    # Extract fenced or plain JSON for NL-assertion judge (#562)
    cleaned = nl_judge_raw_response.strip()
    fence_match = re.match(r"^```(?:json)?\s*\n(.*?)\n```$", cleaned, flags=re.DOTALL)
    json_text = fence_match.group(1).strip() if fence_match else cleaned
    try:
        parsed_judge = json.loads(json_text)
        if not isinstance(parsed_judge, dict) or "met" not in parsed_judge:
            raise ValueError("missing met verdict")
    except Exception:
        return GuardResult(
            allowed=False,
            code="TAU2_NL_JUDGE_MALFORMED_JSON_BLOCKED",
            detail="NL-assertion judge response is malformed JSON even after Markdown fence extraction (#562)",
            metadata={"nl_judge_raw_response": nl_judge_raw_response[:80]},
        )
    if live_speech_started_set_was_truncated:
        return GuardResult(
            allowed=False,
            code="TAU2_LIVE_SPEECH_STARTED_CONFLATED_WITH_TRUNCATION_BLOCKED",
            detail="OpenAI Live speech_started signal must not set was_truncated without an explicit truncation event (#528/#525)",
            metadata={"live_speech_started_set_was_truncated": True},
        )
    return GuardResult(
        allowed=True,
        code="STRIPE_MCP_TOOL_FAILURE_AND_TAU2_ABORT_VERIFIED",
        detail="Stripe paid-tool removal, MCP ToolFailure + conversation handle, and tau2-bench abort/checkpoint/judge/live-voice guards verified",
        metadata={"parsed_judge_met": parsed_judge["met"]},
    )
