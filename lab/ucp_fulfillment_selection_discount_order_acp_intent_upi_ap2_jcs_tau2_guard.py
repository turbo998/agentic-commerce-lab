"""Stage 102 deterministic guardrails across UCP, ACP, Google AP2, and Sierra tau2-bench.

Covers:
1. UCP PR #617 (Fulfillment event linking to checkout `fulfillment_method_id` & `fulfillment_option_id` + `estimated_delivery`),
   PR #609 (`discounts_object.available[]` response-only & secret promo code redaction),
   PR #584 (`order.payment` `order_payment_instrument` subset redaction), and
   PR #578/#577 (`applied_discount.gift_line_item_id` & `discount_code_usage_limit_reached` / `discount_code_stacking_conflict`).
2. ACP PR #54 (`IntentTrace` structured cancellation context on `POST /checkout_sessions/{id}/cancel`) and
   PR #46 (`PaymentMethodUPI` delegated UPI + Razorpay AI Commerce TSP).
3. Google AP2 PR #253 (RFC 8785 JCS `CartMandate`-to-`PaymentMandate` binding over raw JSON preserving extension fields) and
   PR #267 (TrustBoost pre-LLM PII sanitization + Solana x402 proof anchor).
4. Sierra tau2-bench PR #534 (Solo-mode `DummyUser()` no-arg construction),
   PR #533 (Atomic checkpoint replacement preserving old trajectory on write failure),
   PR #520 (Result-safe full-duplex hallucination retries), and
   PR #471 (Retry empty text-mode user-simulator completions without leaking reminder to recorded trajectory).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

FORBIDDEN_ORDER_PAYMENT_FIELDS: frozenset[str] = frozenset(
    {
        "credential",
        "handler_id",
        "selected",
        "token",
        "pan",
    }
)

ALLOWED_CANCEL_REQUEST_KEYS: frozenset[str] = frozenset({"intent_trace"})

FORBIDDEN_INTENT_TRACE_PII_KEYS: frozenset[str] = frozenset(
    {
        "email",
        "phone",
        "phone_number",
        "user_id",
        "full_name",
    }
)


def _strip_none_recursive(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _strip_none_recursive(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [_strip_none_recursive(v) for v in obj]
    return obj


def compute_raw_cart_mandate_jcs_hash(raw_cart_mandate: dict[str, Any]) -> str:
    """Compute RFC 8785 JCS SHA-256 hex digest over raw CartMandate JSON with None optional fields excluded."""
    cleaned = _strip_none_recursive(raw_cart_mandate)
    canonical = json.dumps(cleaned, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_ucp_fulfillment_selection_available_discounts_order_payment_and_gift_discount_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate UCP #617 fulfillment event selection link, #609 available discounts, #584 order.payment, and #578/#577."""
    violations: list[str] = []

    # 1. UCP #617: Link fulfillment events to checkout fulfillment selections
    fe = payload.get("fulfillment_event_check", {})
    selected_methods = set(fe.get("selected_checkout_method_ids", []))
    selected_options = set(fe.get("selected_checkout_option_ids", []))
    event_method_id = str(fe.get("fulfillment_method_id", ""))
    event_option_id = str(fe.get("fulfillment_option_id", ""))
    if not event_method_id or event_method_id not in selected_methods:
        violations.append("UCP_617_UNLINKED_FULFILLMENT_METHOD_ID")
    if not event_option_id or event_option_id not in selected_options:
        violations.append("UCP_617_UNLINKED_FULFILLMENT_OPTION_ID")
    est = fe.get("estimated_delivery", {})
    earliest = str(est.get("earliest", ""))
    latest = str(est.get("latest", ""))
    if not earliest or not latest or earliest > latest:
        violations.append("UCP_617_INVALID_DELIVERY_ESTIMATE_WINDOW")

    # 2. UCP #609: Discoverable available discounts (response-only, no code leak)
    disc_ctx = payload.get("discounts_context", {})
    if bool(disc_ctx.get("request_contains_available_discounts", False)):
        violations.append("UCP_609_AVAILABLE_DISCOUNTS_IN_REQUEST_FORBIDDEN")
    for avail in disc_ctx.get("available_discounts", []):
        dtype = str(avail.get("type", ""))
        if dtype not in {"automatic", "code"}:
            violations.append(f"UCP_609_INVALID_AVAILABLE_DISCOUNT_TYPE:{dtype}")
        if dtype == "code" and "code" in avail:
            violations.append("UCP_609_PROMO_CODE_EXPOSED_IN_AVAILABLE_DISCOUNT")
        rem = avail.get("remaining_amount", 0)
        if not isinstance(rem, int) or isinstance(rem, bool) or rem < 0:
            violations.append("UCP_609_NEGATIVE_OR_INVALID_REMAINING_AMOUNT")

    # 3. UCP #584: Order payment instruments must strip collection-time fields
    ord_pay = payload.get("order_payment", {})
    for inst in ord_pay.get("instruments", []):
        for fkey in FORBIDDEN_ORDER_PAYMENT_FIELDS:
            if fkey in inst:
                violations.append(f"UCP_584_COLLECTION_TIME_PAYMENT_FIELD_LEAKED_TO_ORDER:{fkey}")

    # 4. UCP #578 & #577: gift_line_item_id link & usage-limit / stacking-conflict rejection codes
    gift_Ids_linked = {
        str(ad.get("gift_line_item_id"))
        for ad in disc_ctx.get("applied_discounts", [])
        if ad.get("gift_line_item_id")
    }
    for li in disc_ctx.get("line_items", []):
        if bool(li.get("is_promotional_gift", False)) and int(li.get("price_minor", 0)) == 0:
            if str(li.get("id", "")) not in gift_Ids_linked:
                violations.append(f"UCP_578_UNEXPLAINED_ZERO_PRICE_GIFT_LINE_ITEM:{li.get('id')}")

    for rej in disc_ctx.get("discount_rejections", []):
        cause = str(rej.get("failure_cause", ""))
        code = str(rej.get("rejection_code", ""))
        if cause == "usage_limit_exhausted" and code != "discount_code_usage_limit_reached":
            violations.append(f"UCP_577_MISLEADING_USAGE_LIMIT_CODE:{code}")
        elif cause == "stacking_conflict" and code != "discount_code_stacking_conflict":
            violations.append(f"UCP_577_MISLEADING_STACKING_CONFLICT_CODE:{code}")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def validate_acp_intent_trace_cancellation_and_delegated_upi_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate ACP #54 IntentTrace structured cancellation context and #46 Delegated UPI payment method."""
    violations: list[str] = []

    # 1. ACP #54: CancelSessionRequest & IntentTrace
    cancel_ctx = payload.get("cancel_session", {})
    req_body = cancel_ctx.get("request_body", {})
    if isinstance(req_body, dict):
        extra_top = set(req_body.keys()) - ALLOWED_CANCEL_REQUEST_KEYS
        if extra_top:
            violations.append("ACP_54_CANCEL_REQUEST_UNKNOWN_TOP_LEVEL_FIELD")
        it = req_body.get("intent_trace")
        if it is not None:
            if not isinstance(it, dict) or not str(it.get("reason_code", "")).strip():
                violations.append("ACP_54_MISSING_INTENT_TRACE_REASON_CODE")
            else:
                for k, v in it.items():
                    if str(k).lower() in FORBIDDEN_INTENT_TRACE_PII_KEYS or "@" in str(v):
                        violations.append(f"ACP_54_INTENT_TRACE_PII_FORBIDDEN:{k}")
    if str(cancel_ctx.get("response_status", "canceled")) != "canceled":
        violations.append("ACP_54_CANCEL_RESPONSE_MUST_BE_CANCELED")

    # 2. ACP #46: PaymentMethodUPI + Razorpay AI Commerce TSP
    upi = payload.get("delegated_upi", {})
    delegate_id = str(upi.get("delegate_id", "")).strip()
    cryptogram = str(upi.get("cryptogram", "")).strip()
    provider = str(upi.get("provider", "")).strip().lower()
    if not delegate_id or not cryptogram:
        violations.append("ACP_46_UPI_MISSING_DELEGATE_ID_OR_CRYPTOGRAM")
    if provider != "razorpay":
        violations.append(f"ACP_46_UNSUPPORTED_UPI_TSP_PROVIDER:{provider}")
    if bool(upi.get("cryptogram_reused", False)):
        violations.append("ACP_46_UPI_ONE_TIME_CRYPTOGRAM_REPLAYED")
    amt = int(upi.get("amount_minor", 0))
    limit = int(upi.get("pre_authorized_limit_minor", 0))
    if amt <= 0 or amt > limit:
        violations.append("ACP_46_UPI_AMOUNT_EXCEEDS_PREAUTHORIZED_LIMIT")
    if not bool(upi.get("india_data_localization_compliant", True)):
        violations.append("ACP_46_INDIA_DATA_LOCALIZATION_VIOLATION")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def validate_ap2_jcs_cart_to_payment_binding_and_trustboost_pii_x402_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate Google AP2 #253 raw-JSON JCS cart-to-payment mandate binding and #267 TrustBoost PII + Solana x402."""
    violations: list[str] = []

    # 1. AP2 #253: JCS cart-to-payment mandate binding
    cpb = payload.get("cart_to_payment_binding", {})
    raw_cart = cpb.get("raw_received_cart_mandate", {})
    payment_contents = cpb.get("payment_mandate_contents", {})
    allow_unbound = bool(cpb.get("allow_unbound_cart", False))
    hashed_after_schema_strip = bool(cpb.get("hashed_after_schema_strip", False))

    if hashed_after_schema_strip:
        violations.append("AP2_253_HASHED_SCHEMA_STRIPPED_MODEL_INSTEAD_OF_RAW_JSON")

    cart_id = payment_contents.get("cart_mandate_id")
    cart_hash = payment_contents.get("cart_mandate_hash")

    if cart_hash is None or not str(cart_hash).strip():
        if not allow_unbound:
            violations.append("AP2_253_MISSING_CART_MANDATE_HASH")
    else:
        if not cart_id or str(cart_id) != str(raw_cart.get("id", "")):
            violations.append("AP2_253_CART_MANDATE_ID_MISMATCH")
        expected_hash = compute_raw_cart_mandate_jcs_hash(raw_cart)
        if str(cart_hash) != expected_hash:
            violations.append("AP2_253_CART_MANDATE_HASH_MISMATCH")

    # 2. AP2 #267: TrustBoost pre-LLM PII sanitization + Solana x402 anchor proof
    tb = payload.get("trustboost_sanitization", {})
    if not bool(tb.get("pii_sanitized_before_llm", False)) or bool(tb.get("raw_pii_exposed_to_llm", False)):
        violations.append("AP2_267_UNSANITIZED_PII_EXPOSED_TO_LLM")
    if not bool(tb.get("x402_solana_usdc_settled", False)):
        violations.append("AP2_267_UNSETTLED_X402_SOLANA_SANITIZE_CALL")
    anchor_tx = str(tb.get("solana_anchor_tx", "")).strip()
    verify_url = str(tb.get("verify_endpoint", "")).strip()
    if not anchor_tx or not verify_url.endswith(f"/verify/{anchor_tx}"):
        violations.append("AP2_267_MISSING_OR_MISMATCHED_SOLANA_ANCHOR_PROOF")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def validate_tau2_dummy_user_checkpoint_atomic_hallucination_retry_and_empty_user_turn_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate Sierra tau2-bench #534 DummyUser, #533 atomic checkpoint, #520 hallucination retry, and #471 empty user turn."""
    violations: list[str] = []

    # 1. Sierra tau2-bench #534: Construct DummyUser without simulator arguments in solo mode
    du = payload.get("dummy_user_construction", {})
    if bool(du.get("is_solo_mode", True)) and bool(du.get("passed_simulator_args_to_dummy_user", False)):
        violations.append("TAU2_534_SIMULATOR_ARGS_PASSED_TO_DUMMY_USER_TYPEERROR")

    # 2. Sierra tau2-bench #533: Preserve checkpoint when replacement trajectory write fails
    cp = payload.get("checkpoint_replacement", {})
    if bool(cp.get("unlinked_old_before_replacement_write", False)):
        violations.append("TAU2_533_PREMATURE_CHECKPOINT_UNLINK_DATA_LOSS")
    if bool(cp.get("replacement_write_failed", False)) and not bool(cp.get("old_trajectory_preserved", True)):
        violations.append("TAU2_533_OLD_TRAJECTORY_LOST_ON_WRITE_FAILURE")

    # 3. Sierra tau2-bench #520: Result-safe full-duplex hallucination retries
    hr = payload.get("hallucination_retry_safety", {})
    if not bool(hr.get("reviewed_final_retry", True)):
        violations.append("TAU2_520_FINAL_RETRY_NOT_REVIEWED")
    if bool(hr.get("checkpointed_discarded_retry", False)):
        violations.append("TAU2_520_DISCARDED_RETRY_CHECKPOINTED")
    if bool(hr.get("truncated_tool_results_in_judge_input", False)):
        violations.append("TAU2_520_TRUNCATED_TOOL_RESULTS_IN_JUDGE_INPUT")

    # 4. Sierra tau2-bench #471: Retry empty text-mode user-simulator completions
    ut = payload.get("empty_user_turn_retry", {})
    if bool(ut.get("initial_turn_empty_without_tool_calls", False)):
        if not bool(ut.get("retried_with_stop_reminder", False)):
            violations.append("TAU2_471_EMPTY_USER_TURN_NOT_RETRIED")
        if bool(ut.get("reminder_leaked_into_recorded_trajectory", False)):
            violations.append("TAU2_471_RETRY_REMINDER_LEAKED_INTO_TRAJECTORY")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }
