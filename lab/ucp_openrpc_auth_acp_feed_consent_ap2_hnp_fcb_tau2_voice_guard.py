"""Stage 68 deterministic protocol, payment, mandate, and evaluation guards.

Covers primary-source specifications across four repositories:
1. Universal-Commerce-Protocol/ucp:
   - PR #802 (Fixes #787): OpenRPC `ec.auth` and `ep.cart.auth` descriptors MUST mark
     the `type` parameter `"required": true`, and runtime embedded auth requests MUST
     carry a non-empty `type`.
   - PR #715 (#707): `dev.ucp.shopping.discount` extends to Catalog Lookup (`get_product`
     only) for `discounts.available[]` previews while keeping Cart/Checkout authoritative
     for eligibility and application (`discounts.applied[]` forbidden on catalog `get_product`).
   - PR #713: Generic Shared Payment Token (`dev.ucp.payment.shared_payment_token`) payment
     handler requiring opaque, short-lived, merchant-scoped tokens without raw PAN/CVC/network
     token exposure.
   - PR #691 (#256): `price.price_treatment.tax.inclusion` (`included` | `excluded` |
     `not_applicable`; unrecognized open string treated as omitted `tax`; prevents double-taxing
     `included` prices).
   - PR #673: Business profile `event_feed` (`url`, non-empty `event_types`, transport in
     `webhook` | `sse` | `poll`) and non-normative `fulfillment_event.agent_hints[]` (`action`
     required, `additionalProperties: false`, advisory only).
   - PR #669 & PR #661: `actions` map requires `minProperties: 1` (omit `actions` when none
     are outstanding) and `policy.applies_to` requires `minItems: 1` when present, with set-match
     product tag filter `$.products[?@.tags[?@=='...']]`.
2. agentic-commerce-protocol/agentic-commerce-protocol:
   - PR #255, #190, #192: `UpsertProductsResponse` (`{"id": str, "accepted": bool}`,
     `additionalProperties: false`), Agent-hosted push-model Feed API, and Feed Promotions
     (`effective_period.start_time <= end_time`, non-empty `benefits` and `applies_to`).
   - PR #201 (SEP #197): `Item.suggested_price` on `CheckoutSessionCreateRequest` with
     `PriceSource.feed_id` provenance and `observed_at`.
   - PR #200 (SEP #196) & PR #199 (SEP #195): `CheckoutSessionCompleteRequest.fulfillment_details`
     applied BEFORE payment processing, and `marketing_consent_options` / `marketing_consents`
     channel binding + HTTPS `privacy_policy_url`.
   - PR #215, #213, #188: `razorpay` PSP (`in.razorpay.upi`, `in.razorpay.reserve_pay`,
     `com.razorpay.magic_checkout` / `redirect_checkout`) and pre-checkout `Cart` capability
     without premature payment handler negotiation.
3. google-agentic-commerce/AP2:
   - PR #202 & PR #189: Human-Not-Present (`HNP`) security alignment (`IntentMandate.id`,
     `user_authorization` JWT when `user_cart_confirmation_required == False`, and
     `PaymentMandateContents.intent_mandate_id` + `intent_mandate_hash` signature binding).
   - PR #198 (Closes #133) & PR #191: `PaymentCurrencyAmount.value` as `str` (`DOMString`
     per W3C Payment Request API) and `IntentMandate.budget` ceiling enforcement.
   - PR #187, #164, #139: Section 7.4 `RiskPayload` & Fiduciary Circuit Breaker (`FCBState`:
     `CLOSED` / `HALF_OPEN` / `OPEN`, `TripConditionStatus`) and UPI Collect 3-section request
     envelope (`transaction_data`, `cred_block`, `device_fingerprint`).
4. sierra-research/tau2-bench:
   - PR #582: Spoken word-number recognition (`"five thousand two hundred forty four"` -> `"5244"`)
     and cross-tick chunk reconstruction (`"1,"` + `"628"` -> `"1628"`) in voice communication
     evaluation.
   - PR #575 & PR #573: Safe `.get()` lookup in `analyze_reward()` when `reward_basis` names
     an absent component in `reward_breakdown`, and `replay_mismatches` tracking + strict replay
     enforcement in `evaluate-trajs`.
   - PR #570 & PR #569 (Fixes #568): `Action.compare_with_tool_call` union key comparison
     (`tool_call.arguments.keys() | self.arguments.keys()`) and paired row-by-row scalar list
     sorting (`item_ids` / `new_item_ids`).
   - PR #571, #567 (Closes #558), #566: Retail reference gift-card balance & delivered-status
     exchange checks, unsupported LLM `seed` drop warning, and sorted `banking_knowledge` loading.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import re
from typing import Any


@dataclass(frozen=True)
class GuardEvaluation:
    """Deterministic guard output across Stage 68 checks."""

    allowed: bool
    reason_code: str
    details: dict[str, Any]


# ---------------------------------------------------------------------------
# 1. UCP Guard (#802, #715, #713, #691, #673, #669, #661)
# ---------------------------------------------------------------------------

_KNOWN_TAX_INCLUSIONS = {"included", "excluded", "not_applicable"}
_VALID_EVENT_TRANSPORTS = {"webhook", "sse", "poll"}
_RAW_CREDENTIAL_KEYS = {"pan", "card_number", "cvc", "cvv", "network_token", "cryptogram"}


def verify_ucp_openrpc_auth_discount_preview_spt_price_treatment_and_event_feed(
    payload: dict[str, Any],
) -> GuardEvaluation:
    """Validate UCP #802, #715, #713, #691, #673, #669, and #661 invariants."""
    # 1. PR #802: OpenRPC `ec.auth` and `ep.cart.auth` `type` param required
    openrpc_methods = payload.get("openrpc_methods")
    if isinstance(openrpc_methods, list):
        for method in openrpc_methods:
            if not isinstance(method, dict):
                continue
            m_name = str(method.get("name", ""))
            if m_name in {"ec.auth", "ep.cart.auth"}:
                params = method.get("params", [])
                type_param = next(
                    (p for p in params if isinstance(p, dict) and p.get("name") == "type"),
                    None,
                )
                if not type_param or type_param.get("required") is not True:
                    return GuardEvaluation(
                        allowed=False,
                        reason_code="ucp_embedded_auth_type_param_not_required",
                        details={"method": m_name, "type_param": type_param},
                    )

    embedded_auth_request = payload.get("embedded_auth_request")
    if isinstance(embedded_auth_request, dict):
        method_name = str(embedded_auth_request.get("method", ""))
        params = embedded_auth_request.get("params") or {}
        auth_type = params.get("type") if isinstance(params, dict) else None
        if method_name in {"ec.auth", "ep.cart.auth"} and (
            not isinstance(auth_type, str) or not auth_type.strip()
        ):
            return GuardEvaluation(
                allowed=False,
                reason_code="ucp_embedded_auth_request_missing_type",
                details={"method": method_name, "params": params},
            )

    # 2. PR #715: Catalog discount previews (`discounts.available` only on `get_product`;
    # Cart/Checkout remain authoritative for `discounts.applied`)
    catalog_operation = payload.get("catalog_operation")
    if isinstance(catalog_operation, dict):
        op_name = str(catalog_operation.get("op", ""))
        discounts = catalog_operation.get("discounts")
        if isinstance(discounts, dict):
            if "applied" in discounts:
                return GuardEvaluation(
                    allowed=False,
                    reason_code="ucp_catalog_discount_applied_forbidden_on_product",
                    details={"op": op_name, "discounts": discounts},
                )
            if "available" in discounts and op_name != "get_product":
                return GuardEvaluation(
                    allowed=False,
                    reason_code="ucp_catalog_discount_available_on_non_get_product_op",
                    details={"op": op_name},
                )

    # 3. PR #713: Generic SPT payment handler (`dev.ucp.payment.shared_payment_token`)
    spt_handler = payload.get("spt_payment_handler")
    if isinstance(spt_handler, dict):
        handler_name = str(spt_handler.get("name", "dev.ucp.payment.shared_payment_token"))
        credential = spt_handler.get("credential") or {}
        if handler_name == "dev.ucp.payment.shared_payment_token" and isinstance(credential, dict):
            leaked_keys = sorted(_RAW_CREDENTIAL_KEYS.intersection(credential.keys()))
            if leaked_keys:
                return GuardEvaluation(
                    allowed=False,
                    reason_code="ucp_spt_handler_raw_pan_or_cvc_leaked",
                    details={"leaked_keys": leaked_keys},
                )
            token_val = credential.get("token")
            expires_at = credential.get("expires_at")
            merchant_scope = credential.get("merchant_id") or credential.get("merchant_scope")
            if (
                not isinstance(token_val, str)
                or not token_val.strip()
                or not isinstance(expires_at, str)
                or not expires_at.strip()
                or not isinstance(merchant_scope, str)
                or not merchant_scope.strip()
            ):
                return GuardEvaluation(
                    allowed=False,
                    reason_code="ucp_spt_handler_missing_expiry_or_merchant_scope",
                    details={"credential": credential},
                )

    # 4. PR #691: `price_treatment.tax.inclusion`
    price_obj = payload.get("price")
    normalized_tax_inclusion: str | None = None
    if isinstance(price_obj, dict):
        pt = price_obj.get("price_treatment")
        if isinstance(pt, dict):
            tax_obj = pt.get("tax")
            if isinstance(tax_obj, dict):
                raw_inc = tax_obj.get("inclusion")
                if isinstance(raw_inc, str) and raw_inc in _KNOWN_TAX_INCLUSIONS:
                    normalized_tax_inclusion = raw_inc
                else:
                    normalized_tax_inclusion = None
        if (
            normalized_tax_inclusion == "included"
            and price_obj.get("downstream_tax_added_minor", 0) > 0
        ):
            return GuardEvaluation(
                allowed=False,
                reason_code="ucp_price_treatment_included_double_taxed",
                details={
                    "inclusion": normalized_tax_inclusion,
                    "downstream_tax_added_minor": price_obj.get("downstream_tax_added_minor"),
                },
            )

    # 5. PR #673: `event_feed` capability and non-normative `agent_hints`
    event_feed = payload.get("event_feed")
    if isinstance(event_feed, dict):
        url = event_feed.get("url")
        event_types = event_feed.get("event_types")
        transport = event_feed.get("transport", "webhook")
        if (
            not isinstance(url, str)
            or not url.startswith("https://")
            or not isinstance(event_types, list)
            or len(event_types) == 0
            or transport not in _VALID_EVENT_TRANSPORTS
        ):
            return GuardEvaluation(
                allowed=False,
                reason_code="ucp_event_feed_invalid_schema",
                details={"event_feed": event_feed},
            )

    fulfillment_event = payload.get("fulfillment_event")
    if isinstance(fulfillment_event, dict):
        hints = fulfillment_event.get("agent_hints", [])
        if isinstance(hints, list):
            for hint in hints:
                if not isinstance(hint, dict) or not isinstance(hint.get("action"), str) or not hint.get("action"):
                    return GuardEvaluation(
                        allowed=False,
                        reason_code="ucp_agent_hint_missing_action",
                        details={"hint": hint},
                    )
                allowed_hint_keys = {"action", "reason", "target", "parameters"}
                extra_keys = set(hint.keys()) - allowed_hint_keys
                if extra_keys:
                    return GuardEvaluation(
                        allowed=False,
                        reason_code="ucp_agent_hint_additional_properties_forbidden",
                        details={"extra_keys": sorted(extra_keys)},
                    )
                if hint.get("auto_execute_financial_mutation") is True or fulfillment_event.get(
                    "auto_executed_without_agent_decision"
                ) is True:
                    return GuardEvaluation(
                        allowed=False,
                        reason_code="ucp_agent_hint_treated_as_mandatory_mutation",
                        details={"hint": hint},
                    )

    # 6. PR #669 & PR #661: non-empty `actions` map (`minProperties: 1`) and `policy.applies_to` (`minItems: 1`)
    if "actions" in payload:
        actions_map = payload.get("actions")
        if isinstance(actions_map, dict) and len(actions_map) == 0:
            return GuardEvaluation(
                allowed=False,
                reason_code="ucp_empty_actions_map_present",
                details={"actions": actions_map},
            )

    policies = payload.get("policies")
    if isinstance(policies, list):
        for pol in policies:
            if not isinstance(pol, dict):
                continue
            if "applies_to" in pol:
                applies_to = pol.get("applies_to")
                if not isinstance(applies_to, list) or len(applies_to) == 0:
                    return GuardEvaluation(
                        allowed=False,
                        reason_code="ucp_policy_empty_applies_to_array",
                        details={"policy": pol},
                    )
                for expr in applies_to:
                    if isinstance(expr, str) and "@.category==" in expr.replace(" ", ""):
                        return GuardEvaluation(
                            allowed=False,
                            reason_code="ucp_policy_set_match_invalid_category_scalar_path",
                            details={"expression": expr},
                        )

    return GuardEvaluation(
        allowed=True,
        reason_code="ucp_openrpc_discount_spt_price_event_policy_ok",
        details={"normalized_tax_inclusion": normalized_tax_inclusion},
    )


# ---------------------------------------------------------------------------
# 2. ACP Guard (#255, #190, #192, #201, #200, #199, #215, #213, #188)
# ---------------------------------------------------------------------------

_ALLOWED_ACP_PSPS = {"stripe", "adyen", "braintree", "checkout", "razorpay", "seller_managed"}


def verify_acp_feed_upsert_suggested_price_consent_and_razorpay_cart(
    payload: dict[str, Any],
) -> GuardEvaluation:
    """Validate ACP #255, #190, #192, #201, #200, #199, #215, #213, and #188 invariants."""
    # 1. PR #255 & #190: `UpsertProductsResponse` (`id`, `accepted`, additionalProperties: false)
    upsert_resp = payload.get("upsert_products_response")
    if isinstance(upsert_resp, dict):
        extra = set(upsert_resp.keys()) - {"id", "accepted"}
        if (
            extra
            or not isinstance(upsert_resp.get("id"), str)
            or not upsert_resp.get("id", "").strip()
            or not isinstance(upsert_resp.get("accepted"), bool)
        ):
            return GuardEvaluation(
                allowed=False,
                reason_code="acp_feed_upsert_response_schema_violation",
                details={"upsert_products_response": upsert_resp, "extra_keys": sorted(extra)},
            )

    # 2. PR #192: Feed Promotions (`GET / PATCH /feeds/{id}/promotions`)
    promotions = payload.get("feed_promotions")
    if isinstance(promotions, list):
        for promo in promotions:
            if not isinstance(promo, dict):
                continue
            period = promo.get("effective_period") or {}
            start_time = str(period.get("start_time", ""))
            end_time = str(period.get("end_time", ""))
            benefits = promo.get("benefits")
            applies_to = promo.get("applies_to")
            if (
                not start_time
                or not end_time
                or start_time > end_time
                or not isinstance(benefits, list)
                or len(benefits) == 0
                or not isinstance(applies_to, list)
                or len(applies_to) == 0
            ):
                return GuardEvaluation(
                    allowed=False,
                    reason_code="acp_feed_promotion_invalid_period_or_targets",
                    details={"promotion_id": promo.get("id"), "effective_period": period},
                )

    # 3. PR #201 (SEP #197): `Item.suggested_price` on `CheckoutSessionCreateRequest`
    suggested_price = payload.get("suggested_price")
    if isinstance(suggested_price, dict):
        amount = suggested_price.get("amount")
        observed_at = suggested_price.get("observed_at")
        source = suggested_price.get("source")
        feed_id = source.get("feed_id") if isinstance(source, dict) else None
        if (
            not isinstance(amount, int)
            or amount < 0
            or not isinstance(observed_at, str)
            or not observed_at.strip()
            or not isinstance(feed_id, str)
            or not feed_id.strip()
        ):
            return GuardEvaluation(
                allowed=False,
                reason_code="acp_suggested_price_missing_feed_id_provenance",
                details={"suggested_price": suggested_price},
            )

    # 4. PR #200 (SEP #196): `fulfillment_details` on `CheckoutSessionCompleteRequest`
    complete_req = payload.get("checkout_complete_request")
    if isinstance(complete_req, dict) and "fulfillment_details" in complete_req:
        if complete_req.get("applied_before_payment") is False:
            return GuardEvaluation(
                allowed=False,
                reason_code="acp_complete_fulfillment_details_applied_after_payment",
                details={"fulfillment_details": complete_req.get("fulfillment_details")},
            )

    # 5. PR #199 (SEP #195): Marketing Consent options & complete decisions
    consent_options = payload.get("marketing_consent_options")
    declared_channels: set[str] = set()
    if isinstance(consent_options, list):
        for opt in consent_options:
            if not isinstance(opt, dict):
                continue
            ch = opt.get("channel")
            text = opt.get("display_text")
            privacy_url = opt.get("privacy_policy_url")
            if (
                not isinstance(ch, str)
                or not ch.strip()
                or not isinstance(text, str)
                or not text.strip()
                or not isinstance(privacy_url, str)
                or not privacy_url.startswith("https://")
            ):
                return GuardEvaluation(
                    allowed=False,
                    reason_code="acp_marketing_consent_option_invalid",
                    details={"option": opt},
                )
            declared_channels.add(ch)

    submitted_consents = payload.get("marketing_consents")
    if isinstance(submitted_consents, list):
        for dec in submitted_consents:
            if not isinstance(dec, dict):
                continue
            ch = dec.get("channel")
            opted_in = dec.get("opted_in")
            if (
                not isinstance(ch, str)
                or (declared_channels and ch not in declared_channels)
                or not isinstance(opted_in, bool)
            ):
                return GuardEvaluation(
                    allowed=False,
                    reason_code="acp_marketing_consent_undeclared_channel_or_missing_privacy_url",
                    details={"decision": dec, "declared_channels": sorted(declared_channels)},
                )

    # 6. PR #215, #213, #188: Razorpay handlers (`in.razorpay.upi`, `com.razorpay.magic_checkout`) & Cart capability
    payment_handler = payload.get("payment_handler")
    if isinstance(payment_handler, dict):
        psp = payment_handler.get("psp")
        name = payment_handler.get("name")
        if psp is not None and psp not in _ALLOWED_ACP_PSPS:
            return GuardEvaluation(
                allowed=False,
                reason_code="acp_payment_handler_unsupported_psp",
                details={"psp": psp},
            )
        if name == "in.razorpay.upi":
            if (
                psp != "razorpay"
                or payment_handler.get("requires_pci_compliance") is not False
                or payment_handler.get("requires_delegate_payment") is not True
            ):
                return GuardEvaluation(
                    allowed=False,
                    reason_code="acp_razorpay_upi_pci_or_psp_mismatch",
                    details={"payment_handler": payment_handler},
                )

    cart_session = payload.get("cart_session")
    if isinstance(cart_session, dict):
        if cart_session.get("payment_handlers_negotiated") is True:
            return GuardEvaluation(
                allowed=False,
                reason_code="acp_cart_premature_payment_negotiation",
                details={"cart_id": cart_session.get("id")},
            )

    return GuardEvaluation(
        allowed=True,
        reason_code="acp_feed_suggested_price_consent_razorpay_cart_ok",
        details={"declared_consent_channels": sorted(declared_channels)},
    )


# ---------------------------------------------------------------------------
# 3. Google AP2 Guard (#202, #189, #198, #191, #187, #164, #139)
# ---------------------------------------------------------------------------

def verify_ap2_hnp_mandate_binding_string_amount_budget_and_fcb(
    payload: dict[str, Any],
) -> GuardEvaluation:
    """Validate Google AP2 #202, #189, #198, #191, #187, #164, and #139 invariants."""
    intent_mandate = payload.get("intent_mandate") or {}
    payment_mandate = payload.get("payment_mandate") or {}

    # 1. PR #191: `PaymentCurrencyAmount.value` MUST be `str` (`DOMString`), not float/int
    amounts_to_check: list[tuple[str, Any]] = []
    if isinstance(intent_mandate, dict) and "budget" in intent_mandate and intent_mandate["budget"] is not None:
        amounts_to_check.append(("intent_mandate.budget", intent_mandate["budget"]))
    if isinstance(payment_mandate, dict) and "total_amount" in payment_mandate:
        amounts_to_check.append(("payment_mandate.total_amount", payment_mandate["total_amount"]))

    for label, amt in amounts_to_check:
        if not isinstance(amt, dict) or not isinstance(amt.get("value"), str):
            return GuardEvaluation(
                allowed=False,
                reason_code="ap2_payment_currency_amount_value_not_string",
                details={"field": label, "amount": amt},
            )
        try:
            Decimal(amt["value"])
        except (InvalidOperation, ValueError):
            return GuardEvaluation(
                allowed=False,
                reason_code="ap2_payment_currency_amount_invalid_decimal_string",
                details={"field": label, "value": amt.get("value")},
            )

    # 2. PR #198: `IntentMandate.budget` ceiling enforcement
    if (
        isinstance(intent_mandate, dict)
        and isinstance(intent_mandate.get("budget"), dict)
        and isinstance(payment_mandate, dict)
        and isinstance(payment_mandate.get("total_amount"), dict)
    ):
        budget = intent_mandate["budget"]
        total = payment_mandate["total_amount"]
        if budget.get("currency") != total.get("currency") or Decimal(total["value"]) > Decimal(
            budget["value"]
        ):
            return GuardEvaluation(
                allowed=False,
                reason_code="ap2_intent_mandate_budget_exceeded",
                details={"budget": budget, "total_amount": total},
            )

    # 3. PR #202 & PR #189: HNP security (`user_authorization` on `IntentMandate`,
    # `intent_mandate_id` and `intent_mandate_hash` binding on `PaymentMandate`)
    modality = payment_mandate.get("transaction_modality") if isinstance(payment_mandate, dict) else None
    if modality == "human_not_present":
        confirm_required = intent_mandate.get("user_cart_confirmation_required", False)
        user_auth = intent_mandate.get("user_authorization")
        intent_id = intent_mandate.get("id")
        if confirm_required is False and (
            not isinstance(user_auth, str)
            or len(user_auth.split(".")) != 3
            or not isinstance(intent_id, str)
            or not intent_id.strip()
        ):
            return GuardEvaluation(
                allowed=False,
                reason_code="ap2_hnp_intent_missing_user_authorization",
                details={"intent_id": intent_id, "user_authorization": user_auth},
            )
        pm_intent_id = payment_mandate.get("intent_mandate_id")
        signed_intent_hash = payment_mandate.get("signed_intent_mandate_hash")
        expected_intent_hash = intent_mandate.get("intent_mandate_hash")
        if (
            not isinstance(pm_intent_id, str)
            or pm_intent_id != intent_id
            or not isinstance(signed_intent_hash, str)
            or not signed_intent_hash.strip()
            or (expected_intent_hash and signed_intent_hash != expected_intent_hash)
        ):
            return GuardEvaluation(
                allowed=False,
                reason_code="ap2_hnp_payment_missing_intent_mandate_binding",
                details={
                    "intent_id": intent_id,
                    "payment_intent_mandate_id": pm_intent_id,
                    "signed_intent_mandate_hash": signed_intent_hash,
                    "expected_intent_hash": expected_intent_hash,
                },
            )

    # 4. PR #187 & PR #164: Section 7.4 `RiskPayload` and Fiduciary Circuit Breaker (`FCBState`)
    risk_payload = payload.get("risk_payload")
    if isinstance(risk_payload, dict):
        fcb_state = risk_payload.get("fcb_state", "CLOSED")
        conditions = risk_payload.get("trip_conditions", [])
        tripped = [
            c
            for c in conditions
            if isinstance(c, dict) and c.get("status") == "TRIPPED"
        ]
        if fcb_state == "OPEN" or tripped:
            return GuardEvaluation(
                allowed=False,
                reason_code="ap2_fcb_circuit_open_or_condition_tripped",
                details={"fcb_state": fcb_state, "tripped_conditions": tripped},
            )

    # 5. PR #139: UPI Collect 3-section payment request (`transaction_data`, `cred_block`, `device_fingerprint`)
    upi_collect_req = payload.get("upi_collect_request")
    if isinstance(upi_collect_req, dict):
        required_sections = {"transaction_data", "cred_block", "device_fingerprint"}
        missing = sorted(
            s
            for s in required_sections
            if not isinstance(upi_collect_req.get(s), dict) or not upi_collect_req.get(s)
        )
        if missing:
            return GuardEvaluation(
                allowed=False,
                reason_code="ap2_upi_collect_missing_three_section_envelope",
                details={"missing_sections": missing},
            )

    return GuardEvaluation(
        allowed=True,
        reason_code="ap2_hnp_string_amount_budget_fcb_upi_ok",
        details={"modality": modality or "human_present"},
    )


# ---------------------------------------------------------------------------
# 4. Sierra tau2-bench Guard (#582, #575, #573, #570, #569, #571, #567, #566)
# ---------------------------------------------------------------------------

_WORD_TO_NUM = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}


def _parse_spoken_integer(text: str) -> set[str]:
    """Extract integer strings from spoken English number phrases (e.g., 'five thousand two hundred forty four' -> '5244')."""
    tokens = re.findall(r"[a-z]+", text.lower())
    found: set[str] = set()
    total = 0
    current = 0
    in_number = False
    for tok in tokens:
        if tok == "and" and in_number:
            continue
        if tok in _WORD_TO_NUM:
            current += _WORD_TO_NUM[tok]
            in_number = True
        elif tok == "hundred" and in_number:
            current = (current or 1) * 100
        elif tok == "thousand" and in_number:
            total += (current or 1) * 1000
            current = 0
        else:
            if in_number:
                found.add(str(total + current))
                total = 0
                current = 0
                in_number = False
    if in_number:
        found.add(str(total + current))
    return found


def _compare_action_with_tool_call(
    gold_args: dict[str, Any],
    call_args: dict[str, Any],
    compare_args: list[str] | None = None,
) -> bool:
    """PR #569 & #570: compare union of keys and sort paired scalar lists row-by-row."""
    keys = set(compare_args) if compare_args is not None else (set(gold_args.keys()) | set(call_args.keys()))
    if not keys:
        return True
    for k in keys:
        if k not in gold_args or k not in call_args:
            return False

    def _normalize(d: dict[str, Any]) -> dict[str, Any]:
        out = dict(d)
        length_groups: dict[int, list[str]] = {}
        for k in sorted(keys):
            v = out.get(k)
            if isinstance(v, list) and all(isinstance(x, (str, int, float, bool)) for x in v):
                length_groups.setdefault(len(v), []).append(k)
        for length, group_keys in length_groups.items():
            if length <= 1:
                continue
            rows = list(zip(*(out[gk] for gk in group_keys)))
            rows.sort()
            for idx, gk in enumerate(group_keys):
                out[gk] = [r[idx] for r in rows]
        return {k: out[k] for k in keys}

    return _normalize(gold_args) == _normalize(call_args)


def verify_tau2_spoken_amount_reward_breakdown_replay_and_action_match(
    payload: dict[str, Any],
) -> GuardEvaluation:
    """Validate Sierra tau2-bench #582, #575, #573, #570, #569, #571, #567, and #566 invariants."""
    # 1. PR #582: Spoken amount recognition and voice chunk reconstruction
    voice_comm = payload.get("voice_communication_check")
    if isinstance(voice_comm, dict):
        expected_amount = str(voice_comm.get("expected_amount", "")).replace(",", "")
        chunks = voice_comm.get("chunks", [])
        reconstructed = "".join(str(c) for c in chunks if c is not None)
        digits_in_text = {m.replace(",", "") for m in re.findall(r"\d[\d,]*", reconstructed)}
        spoken_in_text = _parse_spoken_integer(reconstructed)
        recognized = expected_amount in (digits_in_text | spoken_in_text)
        reported_pass = voice_comm.get("reported_pass")
        if recognized and reported_pass is False:
            return GuardEvaluation(
                allowed=False,
                reason_code="tau2_voice_spoken_or_chunked_amount_false_negative",
                details={
                    "expected_amount": expected_amount,
                    "reconstructed": reconstructed,
                    "recognized": recognized,
                },
            )

    # 2. PR #575: `analyze_reward` safe `.get()` on named-but-absent `reward_breakdown` components
    reward_analysis = payload.get("reward_analysis")
    if isinstance(reward_analysis, dict):
        basis = reward_analysis.get("reward_basis", [])
        breakdown = reward_analysis.get("reward_breakdown") or {}
        if reward_analysis.get("used_direct_subscript") is True and any(
            comp not in breakdown for comp in basis
        ):
            return GuardEvaluation(
                allowed=False,
                reason_code="tau2_analyze_reward_missing_component_keyerror",
                details={"reward_basis": basis, "reward_breakdown": breakdown},
            )

    # 3. PR #573: `evaluate-trajs` `replay_mismatches` tracking and strict replay enforcement
    replay_check = payload.get("trajectory_replay")
    if isinstance(replay_check, dict):
        mismatches = int(replay_check.get("replay_mismatches", 0))
        strict_mode = bool(replay_check.get("strict_replay", False))
        info = replay_check.get("reward_info_metadata") or {}
        if mismatches > 0:
            if strict_mode:
                return GuardEvaluation(
                    allowed=False,
                    reason_code="tau2_strict_replay_mismatch_rejected",
                    details={"replay_mismatches": mismatches},
                )
            if info.get("replay_mismatches") != mismatches:
                return GuardEvaluation(
                    allowed=False,
                    reason_code="tau2_silent_lenient_replay_divergence",
                    details={"replay_mismatches": mismatches, "reward_info_metadata": info},
                )

    # 4. PR #569 & #570: `Action.compare_with_tool_call` union keys & paired scalar list sorting
    action_cmp = payload.get("action_comparison")
    if isinstance(action_cmp, dict):
        gold_args = action_cmp.get("gold_arguments") or {}
        call_args = action_cmp.get("tool_call_arguments") or {}
        compare_args = action_cmp.get("compare_args")
        actual_match = _compare_action_with_tool_call(gold_args, call_args, compare_args)
        reported_match = action_cmp.get("reported_match")
        if reported_match is not None and bool(reported_match) != actual_match:
            reason = (
                "tau2_action_check_omitted_gold_arguments_matched"
                if set(call_args.keys()) < set(gold_args.keys())
                else "tau2_action_paired_list_order_mismatch"
            )
            return GuardEvaluation(
                allowed=False,
                reason_code=reason,
                details={
                    "gold_arguments": gold_args,
                    "tool_call_arguments": call_args,
                    "expected_match": actual_match,
                    "reported_match": reported_match,
                },
            )

    # 5. PR #571, #567, #566: Retail reference gift-card / delivered-order checks, seed drop warning, sorted KB
    retail_ref = payload.get("retail_reference_check")
    if isinstance(retail_ref, dict):
        order_status = str(retail_ref.get("order_status", "delivered"))
        price_diff = Decimal(str(retail_ref.get("exchange_price_difference", "0")))
        gc_balance = Decimal(str(retail_ref.get("gift_card_balance", "999999")))
        if order_status != "delivered" or price_diff > gc_balance:
            return GuardEvaluation(
                allowed=False,
                reason_code="tau2_retail_reference_insufficient_gift_card_or_pending_exchange",
                details={
                    "order_status": order_status,
                    "exchange_price_difference": str(price_diff),
                    "gift_card_balance": str(gc_balance),
                },
            )

    return GuardEvaluation(
        allowed=True,
        reason_code="tau2_spoken_amount_reward_replay_action_retail_ok",
        details={},
    )
