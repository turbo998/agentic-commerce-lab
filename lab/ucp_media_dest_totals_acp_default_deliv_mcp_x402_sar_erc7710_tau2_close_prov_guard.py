"""Stage 82 deterministic guardrails:
1. UCP Multi-Rendition Media (#690/#675), Method-Level Destination Discrimination (#689/#688),
   Object-Root totals.json (#684), MCP Idempotency-Key Server Contract & A2A complete_in_progress
   Freeze (#679/#670), Location-Context Provisional Fulfillment (#671), Sanitized order.payment
   Instruments (#584), Gift Line-Item & Discount Rejection Codes (#578/#577), Canonical keys[]
   JWKS (#566), Read-Only ask Capability (#538), and Recipient-Required Gift Checkout (#508).
2. ACP Default Delivery Option Selection (#198), Delegate Payment 401/500/503 & Virtual Card
   Requirement (#161/#132), Content Citation Attribution (#149), MCP Transport Binding (#139),
   PaymentHandler display_name & Capture/Authorize Intent (#130), and Consolidated AppliedDiscount (#125).
3. Coinbase x402 Pre-Sign onPaymentRequested Policy (#166), Payment-Identifier Request Fingerprint
   Binding (#165), AttestSeal Ed25519 DID Trust Attestation (#136), Settlement Attestation Receipt
   (SAR) Delivery Binding (#46), ERC-7710 Delegation Simulation (#22), and Facilitator Hook
   Isolation / CSPRNG Fee-Payer Selection (#13).
4. Sierra tau2-bench Banking close_bank_account_7392 Fixed Reason Enum (#484), Task 091 persona
   Key Validation (#478), Empty Text-Mode User-Simulator Retry (#471), Evaluator Provenance (#467),
   Multi-Customer Telecom DB-Safe Grading (#462), and Voice TTS Concurrency Bound (#457).
"""

from __future__ import annotations

from typing import Any, Mapping

VALID_UCP_MEDIA_TYPES = frozenset({"image", "video", "external_video", "model_3d"})
FORBIDDEN_ORDER_PAYMENT_FIELDS = frozenset({"handler_id", "credential", "selected"})
VALID_DISCOUNT_REJECTION_CODES = frozenset(
    {
        "discount_code_expired",
        "discount_code_invalid",
        "discount_code_minimum_not_met",
        "discount_code_already_applied",
        "discount_code_combination_disallowed",
        "discount_code_usage_limit_reached",
        "discount_code_stacking_conflict",
    }
)
FORBIDDEN_GIFT_PII_FIELDS = frozenset(
    {"recipient_id", "selection_token", "friend_list", "contact_book", "recipient_address"}
)

VALID_ACP_DELEGATE_ERROR_TYPES = frozenset(
    {
        "invalid_request",
        "rate_limit_exceeded",
        "unauthorized",
        "internal_server_error",
        "service_unavailable",
    }
)
VALID_ACP_DELEGATE_ERROR_CODES = frozenset(
    {
        "invalid_card",
        "expired_card",
        "unauthorized",
        "internal_server_error",
        "service_unavailable",
        "unsupported_api_version",
        "missing_api_version",
    }
)
VALID_ACP_MCP_TOOLS = frozenset(
    {
        "create_checkout_session",
        "get_checkout_session",
        "update_checkout_session",
        "complete_checkout_session",
        "cancel_checkout_session",
    }
)

VALID_BANKING_CLOSE_REASONS = frozenset(
    {
        "customer_request",
        "relocation",
        "switching_bank",
        "dissatisfied_with_service",
        "high_fees",
        "deceased_account_holder",
        "fraud_or_security_concern",
        "consolidating_accounts",
    }
)


def verify_ucp_media_destinations_totals_idempotency_order_gift_and_ask_guard(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Enforce UCP PRs #690, #689, #684, #679, #675, #671, #670, #584, #578, #577, #566, #538, #508."""
    violations: list[str] = []

    # 1. PR #690 & #675: Media variants (image, video, external_video, model_3d) & sources[]
    media_items = payload.get("media_items", [])
    if isinstance(media_items, list):
        for idx, item in enumerate(media_items):
            if not isinstance(item, Mapping):
                continue
            mtype = str(item.get("type", "image"))
            if mtype not in VALID_UCP_MEDIA_TYPES:
                violations.append(f"UCP_MEDIA_VARIANT_TYPE_INVALID:{idx}:{mtype}")
            sources = item.get("sources")
            if sources is not None and (not isinstance(sources, list) or len(sources) == 0):
                violations.append(f"UCP_MEDIA_SOURCES_MUST_BE_NON_EMPTY_ARRAY:{idx}")

    # 2. PR #689 / #688: Method-level request destination discrimination & explicit response destination type
    dest_check = payload.get("destination_contract", {})
    if isinstance(dest_check, Mapping) and dest_check:
        if dest_check.get("request_requires_per_object_type", False):
            violations.append("UCP_REQUEST_DESTINATION_PER_OBJECT_TYPE_BREAKS_DEPLOYED_PLATFORMS")
        if not dest_check.get("response_destination_has_explicit_type", True):
            violations.append("UCP_RESPONSE_DESTINATION_EXPLICIT_TYPE_REQUIRED")

    # 3. PR #684: totals.json schema root must be object, not RootArray
    if payload.get("totals_schema_root_type", "object") != "object":
        violations.append("UCP_TOTALS_SCHEMA_ROOT_ARRAY_FORBIDDEN")

    # 4. PR #679 & #670: MCP idempotency-key server contract & A2A complete_in_progress mutation freeze
    mcp_idemp = payload.get("mcp_idempotency", {})
    if isinstance(mcp_idemp, Mapping) and mcp_idemp:
        if mcp_idemp.get("key_reused_with_different_payload", False) and mcp_idemp.get(
            "returned_status_code"
        ) not in (409, -32000):
            violations.append("UCP_MCP_IDEMPOTENCY_KEY_CONFLICT_MUST_RETURN_409_OR_MINUS_32000")
    a2a_state = payload.get("a2a_checkout", {})
    if isinstance(a2a_state, Mapping) and a2a_state:
        if a2a_state.get("status") == "complete_in_progress" and a2a_state.get(
            "accepted_mutation_action", False
        ):
            violations.append("UCP_A2A_COMPLETE_IN_PROGRESS_MUTATION_FREEZE_VIOLATED")

    # 5. PR #671: context.location is provisional availability context, never auto-selects destination
    loc_ctx = payload.get("location_context", {})
    if isinstance(loc_ctx, Mapping) and loc_ctx:
        if loc_ctx.get("context_location_selected_delivery_destination", False):
            violations.append("UCP_CONTEXT_LOCATION_MUST_NOT_SELECT_DELIVERY_DESTINATION")

    # 6. PR #584: order.payment instruments must strip collection-time fields
    order_payment = payload.get("order_payment_instruments", [])
    if isinstance(order_payment, list):
        for idx, inst in enumerate(order_payment):
            if isinstance(inst, Mapping):
                leaked = FORBIDDEN_ORDER_PAYMENT_FIELDS.intersection(inst.keys())
                if leaked:
                    violations.append(
                        f"UCP_ORDER_PAYMENT_INSTRUMENT_LEAKED_COLLECTION_FIELDS:{idx}:{','.join(sorted(leaked))}"
                    )

    # 7. PR #578 & #577: Free gift line items linked via applied_discount.gift_line_item_id & accurate rejection codes
    discounts = payload.get("discounts", {})
    if isinstance(discounts, Mapping) and discounts:
        zero_price_gift_ids = set(discounts.get("zero_price_promotional_line_item_ids", []))
        linked_gift_ids = {
            str(d.get("gift_line_item_id"))
            for d in discounts.get("applied", [])
            if isinstance(d, Mapping) and d.get("gift_line_item_id")
        }
        unlinked = zero_price_gift_ids - linked_gift_ids
        if unlinked:
            violations.append(
                f"UCP_UNLINKED_ZERO_PRICE_GIFT_LINE_ITEM:{','.join(sorted(unlinked))}"
            )
        for code in discounts.get("rejection_codes", []):
            if str(code) not in VALID_DISCOUNT_REJECTION_CODES:
                violations.append(f"UCP_DISCOUNT_REJECTION_CODE_INVALID:{code}")
        if discounts.get("usage_limit_exhausted_reported_as_already_applied", False):
            violations.append("UCP_DISCOUNT_USAGE_LIMIT_MISREPORTED_AS_ALREADY_APPLIED")

    # 8. PR #566, #538 & #508: Canonical profile keys[], read-only ask capability, recipient-required gift checkout
    profile = payload.get("profile", {})
    if isinstance(profile, Mapping) and profile:
        if "signing_keys" in profile:
            violations.append("UCP_PROFILE_LEGACY_SIGNING_KEYS_FORBIDDEN_USE_KEYS_JWKS")
        if not isinstance(profile.get("keys", []), list) or len(profile.get("keys", [1])) == 0:
            violations.append("UCP_PROFILE_CANONICAL_KEYS_ARRAY_EMPTY")

    ask_op = payload.get("ask_operation", {})
    if isinstance(ask_op, Mapping) and ask_op:
        if ask_op.get("mutated_checkout_or_cart_state", False):
            violations.append("UCP_ASK_CAPABILITY_MUST_BE_STRICTLY_READ_ONLY")

    gift = payload.get("gift", {})
    if isinstance(gift, Mapping) and gift:
        leaked_pii = FORBIDDEN_GIFT_PII_FIELDS.intersection(gift.keys())
        if leaked_pii:
            violations.append(
                f"UCP_GIFT_EXTENSION_FORBIDDEN_RECIPIENT_PII:{','.join(sorted(leaked_pii))}"
            )
        if (
            gift.get("recipient_required", False)
            and payload.get("checkout_completing", False)
            and not gift.get("business_validated_recipient_present", False)
        ):
            violations.append("UCP_GIFT_RECIPIENT_REQUIRED_BEFORE_COMPLETE")

    return {
        "allowed": len(violations) == 0,
        "decision_code": "ADMIT_ALLOWED" if not violations else violations[0],
        "violations": violations,
    }


def verify_acp_default_delivery_delegate_errors_citation_and_mcp_binding_guard(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Enforce ACP PRs #198, #161, #149, #139, #132, #130, #125."""
    violations: list[str] = []

    # 1. PR #198: Default delivery option pre-selection on checkout create
    checkout_create = payload.get("checkout_create_response", {})
    if isinstance(checkout_create, Mapping) and checkout_create:
        options = checkout_create.get("fulfillment_options", [])
        selected_id = checkout_create.get("selected_fulfillment_option_id")
        if isinstance(options, list) and len(options) > 0:
            option_ids = {str(o.get("id")) for o in options if isinstance(o, Mapping) and o.get("id")}
            if not selected_id or str(selected_id) not in option_ids:
                violations.append("ACP_CHECKOUT_CREATE_DEFAULT_FULFILLMENT_OPTION_MISSING")

    # 2. PR #161 & #132: Delegate payment PaymentMethodCard.virtual required & 401/500/503/version Error enums
    delegate_payment = payload.get("delegate_payment", {})
    if isinstance(delegate_payment, Mapping) and delegate_payment:
        card = delegate_payment.get("payment_method_card", {})
        if isinstance(card, Mapping) and card:
            if not isinstance(card.get("virtual"), bool):
                violations.append("ACP_DELEGATE_PAYMENT_CARD_VIRTUAL_BOOLEAN_REQUIRED")
        error = delegate_payment.get("error", {})
        if isinstance(error, Mapping) and error:
            etype = str(error.get("type", ""))
            ecode = str(error.get("code", ""))
            if etype not in VALID_ACP_DELEGATE_ERROR_TYPES:
                violations.append(f"ACP_DELEGATE_PAYMENT_ERROR_TYPE_INVALID:{etype}")
            if ecode not in VALID_ACP_DELEGATE_ERROR_CODES:
                violations.append(f"ACP_DELEGATE_PAYMENT_ERROR_CODE_INVALID:{ecode}")

    # 3. PR #149: Content citation attribution extension
    citations = payload.get("content_attribution", [])
    if isinstance(citations, list):
        for idx, cit in enumerate(citations):
            if isinstance(cit, Mapping):
                if not cit.get("source_url") or not cit.get("publisher_id"):
                    violations.append(f"ACP_CONTENT_CITATION_SOURCE_OR_PUBLISHER_MISSING:{idx}")
                if cit.get("overrides_item_price", False):
                    violations.append(f"ACP_CONTENT_CITATION_PRICE_OVERRIDE_FORBIDDEN:{idx}")

    # 4. PR #139, #130 & #125: MCP transport binding tools, PaymentHandler.display_name + intent, AppliedDiscount consolidation
    mcp_call = payload.get("mcp_transport_call", {})
    if isinstance(mcp_call, Mapping) and mcp_call:
        if mcp_call.get("jsonrpc") != "2.0" or str(mcp_call.get("tool_name")) not in VALID_ACP_MCP_TOOLS:
            violations.append("ACP_MCP_TRANSPORT_TOOL_BINDING_INVALID")

    handler = payload.get("payment_handler", {})
    if isinstance(handler, Mapping) and handler:
        if not str(handler.get("display_name", "")).strip():
            violations.append("ACP_PAYMENT_HANDLER_DISPLAY_NAME_MISSING")
        if str(handler.get("payment_intent", "capture")) not in ("authorize", "capture"):
            violations.append("ACP_PAYMENT_INTENT_ENUM_INVALID")

    if payload.get("uses_deprecated_discount_detail_type", False):
        violations.append("ACP_DEPRECATED_DISCOUNT_DETAIL_MUST_CONSOLIDATE_TO_APPLIED_DISCOUNT")

    return {
        "allowed": len(violations) == 0,
        "decision_code": "ADMIT_ALLOWED" if not violations else violations[0],
        "violations": violations,
    }


def verify_x402_mcp_policy_request_binding_attestseal_sar_erc7710_and_hook_guard(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Enforce Coinbase x402 PRs #166, #165, #136, #46, #27, #22, #13."""
    violations: list[str] = []

    # 1. PR #166: Code-level onPaymentRequested policy enforcement before wallet signing
    mcp_policy = payload.get("mcp_payment_policy", {})
    if isinstance(mcp_policy, Mapping) and mcp_policy:
        if mcp_policy.get("enforced_only_in_prompt", False) or not mcp_policy.get(
            "verified_tool_network_and_max_amount_in_code", True
        ):
            violations.append("X402_MCP_SPEND_POLICY_MUST_ENFORCE_IN_CODE_BEFORE_SIGNING")

    # 2. PR #165: Payment identifier bound to normalized request+payment fingerprint
    pay_id = payload.get("payment_identifier_record", {})
    if isinstance(pay_id, Mapping) and pay_id:
        if not pay_id.get("bound_to_request_fingerprint", True):
            violations.append("X402_PAYMENT_IDENTIFIER_UNBOUND_TO_REQUEST_FINGERPRINT")
        if pay_id.get("reused_with_different_request_fingerprint", False) and pay_id.get(
            "returned_status"
        ) != 409:
            violations.append("X402_PAYMENT_IDENTIFIER_FINGERPRINT_MISMATCH_MUST_REJECT_409")

    # 3. PR #136: attestseal-trust-attestation Ed25519 DID authority check on 402 response
    attest = payload.get("attestseal_attestation", {})
    if isinstance(attest, Mapping) and attest:
        if (
            not attest.get("ed25519_signature_valid", True)
            or not attest.get("independent_authority_did_verified", True)
            or float(attest.get("did_cache_age_hours", 0.0)) > 24.0
        ):
            violations.append("X402_ATTESTSEAL_TRUST_ATTESTATION_INVALID_OR_STALE")

    # 4. PR #46: Settlement Attestation Receipt (SAR) binding payment, request, and delivered resource digest
    sar = payload.get("settlement_attestation_receipt", {})
    if isinstance(sar, Mapping) and sar:
        if (
            not sar.get("tx_hash")
            or not sar.get("request_digest")
            or not sar.get("delivered_resource_digest")
            or sar.get("delivered_resource_digest") != sar.get("actual_response_body_digest")
            or not sar.get("server_signature_verified", True)
        ):
            violations.append("X402_SAR_SETTLEMENT_TO_DELIVERY_DIGEST_BINDING_INVALID")

    # 5. PR #22 & #13: ERC-7710 redeemDelegations simulation, hook failure isolation & CSPRNG SVM fee-payer
    erc7710 = payload.get("erc7710_facilitator", {})
    if isinstance(erc7710, Mapping) and erc7710:
        if not erc7710.get("simulated_redeem_delegations_eth_call", True):
            violations.append("X402_ERC7710_REDEEM_DELEGATIONS_SIMULATION_MISSING")

    facilitator = payload.get("facilitator_runtime", {})
    if isinstance(facilitator, Mapping) and facilitator:
        if facilitator.get("optional_hook_threw", False) and facilitator.get(
            "aborted_verify_or_settle", False
        ):
            violations.append("X402_FACILITATOR_OPTIONAL_HOOK_FAILURE_NOT_ISOLATED")
        if not facilitator.get("svm_fee_payer_uses_csprng", True) or facilitator.get(
            "svm_signer_pool_empty_unhandled", False
        ):
            violations.append("X402_SVM_FEE_PAYER_WEAK_RNG_OR_EMPTY_POOL")

    return {
        "allowed": len(violations) == 0,
        "decision_code": "ADMIT_ALLOWED" if not violations else violations[0],
        "violations": violations,
    }


def verify_tau2_banking_close_reason_persona_empty_retry_provenance_and_tts_guard(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Enforce Sierra tau2-bench PRs #484, #478, #471, #467, #462, #457."""
    violations: list[str] = []

    # 1. PR #484 & #478: close_bank_account_7392 fixed reason enum & task_091 persona key
    banking = payload.get("banking_knowledge", {})
    if isinstance(banking, Mapping) and banking:
        close_reason = banking.get("close_account_reason")
        if close_reason is not None and str(close_reason) not in VALID_BANKING_CLOSE_REASONS:
            violations.append(f"TAU2_BANKING_CLOSE_ACCOUNT_REASON_NOT_IN_ENUM:{close_reason}")
        if banking.get("task_091_has_persoca_typo", False):
            violations.append("TAU2_BANKING_TASK_091_PERSOCA_KEY_TYPO")

    # 2. PR #471: Retry empty text-mode user-simulator completion after tracking-only user tool call
    user_sim = payload.get("text_user_simulator", {})
    if isinstance(user_sim, Mapping) and user_sim:
        if user_sim.get("empty_completion_after_user_tool", False) and user_sim.get(
            "crashed_episode_as_infrastructure_error", False
        ):
            violations.append("TAU2_EMPTY_USER_SIM_COMPLETION_MUST_RETRY_NOT_CRASH")

    # 3. PR #467: Evaluator provenance metadata distinguishing live evaluation from reference replay
    provenance = payload.get("evaluator_provenance", {})
    if isinstance(provenance, Mapping) and provenance:
        if provenance.get("evaluation_mode") not in ("live", "reference_replay") or not provenance.get(
            "state_source"
        ):
            violations.append("TAU2_EVALUATOR_PROVENANCE_METADATA_MISSING")

    # 4. PR #462: Multi-customer Telecom (C1001/C1002) DB-safe grading
    telecom = payload.get("telecom_multi_customer", {})
    if isinstance(telecom, Mapping) and telecom:
        if "DB" not in telecom.get("reward_bases", ["DB"]) or telecom.get(
            "unrelated_db_writes_received_full_reward", False
        ):
            violations.append("TAU2_TELECOM_MULTI_CUSTOMER_DB_GRADING_BYPASSED")

    # 5. PR #457: Voice TTS concurrency bound preventing ElevenLabs 429 dropped utterances
    voice_tts = payload.get("voice_tts_provider", {})
    if isinstance(voice_tts, Mapping) and voice_tts:
        max_conc = int(voice_tts.get("max_concurrent_syntheses", 5))
        sub_cap = int(voice_tts.get("subscription_concurrency_cap", 5))
        if max_conc > sub_cap or voice_tts.get("unbounded_parallel_synthesize_voice", False):
            violations.append("TAU2_VOICE_TTS_CONCURRENCY_UNBOUNDED_429_RISK")

    return {
        "allowed": len(violations) == 0,
        "decision_code": "ADMIT_ALLOWED" if not violations else violations[0],
        "violations": violations,
    }
