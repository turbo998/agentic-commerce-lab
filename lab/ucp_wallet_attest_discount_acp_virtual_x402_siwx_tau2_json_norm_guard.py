"""Stage 94 deterministic guardrails for UCP Wallet Attestation/Inapplicable Discounts/Order Currency/Link Delegation, ACP Card virtual/Address/Client-Reference Alignment, Coinbase x402 MCP+SIWX Entitlement Reuse & Witness SAR, and Sierra tau2-bench Nested JSON-String / Numeric DB-Hash Normalization & Batch Evaluator Guard.

Primary-source references:
- Universal-Commerce-Protocol/ucp PRs #280 (`wallet_attestation` identity linking mechanism), #264 & #250 (`context.eligibility` & `attestations` sibling map verification), #271 (`discounts.inapplicable[]` structured rejection codes), #283 (`Order.currency` required), and #247 (`ec_delegate=link.open` -> `ec.link.open_request`).
- agentic-commerce-protocol/agentic-commerce-protocol PRs #132 (`PaymentMethodCard.virtual` required, `Address.email`/`phone` bounds, `DelegatePaymentResponse.expires_at`), #133 (`PaymentHandler.display_order`), and #128 (`Order.client_reference_id` reconciliation).
- coinbase/x402 PRs #27 (`@x402/mcp` payment-first + SIWX wallet-auth stored entitlement reuse scoped to exact tool) and #50/#46 (`DefaultVerifier` Settlement Witness SAR receipt gate).
- Sierra-Research/tau2-bench PRs #401 (nested JSON-string argument normalization in `Action.compare_with_tool_call`), #397 (`banking_knowledge` numeric `int`/`float` seed normalization & fractional rejection on integer tools), and #393 (`evaluate_simulation` batch isolation catching runtime errors as `reward=0.0` while re-raising `EvaluationCriteriaError`).
"""

from __future__ import annotations

import json
import re
from typing import Any

ISO4217_RE = re.compile(r"^[A-Z]{3}$")
VALID_INAPPLICABLE_REASONS = {
    "discount_code_expired",
    "discount_code_invalid",
    "discount_code_already_applied",
    "discount_code_combination_disallowed",
    "discount_code_user_not_logged_in",
    "discount_code_user_ineligible",
}
INTEGER_STRICT_BANKING_TOOLS = {
    "submit_credit_limit_increase_request_7392",
    "request_temporary_debit_card_limit_increase_8374",
}


def validate_ucp_wallet_attestation_inapplicable_discount_and_order_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate UCP #280 wallet_attestation, #264/#250 eligibility attestations, #271 inapplicable discounts, #283 Order.currency, and #247 link delegation."""
    violations: list[str] = []

    mech = payload.get("identity_mechanism", {})
    if mech.get("type") == "wallet_attestation":
        jwks = str(mech.get("provider_jwks", ""))
        if not jwks.startswith("https://"):
            violations.append("UCP_WALLET_ATTESTATION_HTTPS_JWKS_REQUIRED")
        if mech.get("derived_oauth_scopes", []):
            violations.append("UCP_WALLET_ATTESTATION_OAUTH_SCOPES_FORBIDDEN")

    now_ts = int(payload.get("current_timestamp", 0))
    claims = payload.get("context_eligibility", [])
    attestations = payload.get("attestations", {})
    for claim in claims:
        att = attestations.get(claim)
        if not isinstance(att, dict):
            violations.append(f"UCP_ELIGIBILITY_ATTESTATION_MISSING:{claim}")
            continue
        if not str(att.get("provider_jwks", "")).startswith("https://") or not str(att.get("kid", "")).strip():
            violations.append(f"UCP_ELIGIBILITY_ATTESTATION_METADATA_INVALID:{claim}")
        if not att.get("sig_verified", False):
            violations.append(f"UCP_ELIGIBILITY_ATTESTATION_SIGNATURE_INVALID:{claim}")
        att_payload = att.get("payload", {})
        if att_payload.get("pass") is not True:
            violations.append(f"UCP_ELIGIBILITY_ATTESTATION_CLAIM_NOT_PASSED:{claim}")
        if int(att.get("expires_at", 0)) <= now_ts:
            violations.append(f"UCP_ELIGIBILITY_ATTESTATION_EXPIRED:{claim}")

    discounts = payload.get("discounts", {})
    if discounts:
        submitted = [str(c) for c in discounts.get("codes", [])]
        applied_codes = {str(a.get("code")) for a in discounts.get("applied", []) if isinstance(a, dict)}
        inapplicable = discounts.get("inapplicable", [])
        inapp_map = {str(i.get("code")): i for i in inapplicable if isinstance(i, dict) and i.get("code")}
        for code in submitted:
            if code not in applied_codes and code not in inapp_map:
                violations.append(f"UCP_DISCOUNT_UNACCOUNTED_REJECTED_CODE:{code}")
        for item in inapplicable:
            reason = str(item.get("reason", ""))
            if reason not in VALID_INAPPLICABLE_REASONS:
                violations.append(f"UCP_DISCOUNT_INAPPLICABLE_INVALID_REASON:{reason}")
            if not str(item.get("content", "")).strip():
                violations.append("UCP_DISCOUNT_INAPPLICABLE_CONTENT_REQUIRED")

    order = payload.get("order", {})
    if order:
        currency = str(order.get("currency", ""))
        if not ISO4217_RE.match(currency):
            violations.append("UCP_ORDER_CURRENCY_REQUIRED_ISO4217")

    link_del = payload.get("ec_link_delegation", {})
    if link_del.get("ec_delegate_link_open", False):
        if link_del.get("direct_iframe_navigation_attempted", False) or not link_del.get(
            "ec_link_open_request_sent", False
        ):
            violations.append("UCP_ECP_LINK_OPEN_DELEGATION_BYPASSED")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def validate_acp_card_virtual_address_and_client_ref_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate ACP #132 PaymentMethodCard.virtual & Address/Allowance alignment, #133 display_order, and #128 client_reference_id."""
    violations: list[str] = []

    card_pm = payload.get("payment_method_card", {})
    if card_pm:
        if not isinstance(card_pm.get("virtual"), bool):
            violations.append("ACP_PAYMENT_METHOD_CARD_VIRTUAL_BOOLEAN_REQUIRED")

    addr = payload.get("address", {})
    if addr:
        email = addr.get("email")
        if email is not None and (not isinstance(email, str) or len(email) > 256 or "@" not in email):
            violations.append("ACP_ADDRESS_EMAIL_FORMAT_OR_MAXLEN_INVALID")
        phone = addr.get("phone")
        if phone is not None and (not isinstance(phone, str) or len(phone) > 32):
            violations.append("ACP_ADDRESS_PHONE_MAXLEN_INVALID")

    allowance_exp = payload.get("allowance_expires_at")
    resp_exp = payload.get("delegate_response_expires_at")
    if allowance_exp is not None and resp_exp is not None and allowance_exp != resp_exp:
        violations.append("ACP_DELEGATE_RESPONSE_EXPIRES_AT_MISMATCH")

    for handler in payload.get("payment_handlers", []):
        if "display_order" in handler:
            d_order = handler.get("display_order")
            if not isinstance(d_order, int) or isinstance(d_order, bool) or d_order < 0:
                violations.append(f"ACP_HANDLER_DISPLAY_ORDER_INVALID:{handler.get('id', 'unknown')}")

    req_ref = payload.get("request_client_reference_id")
    order_ref = payload.get("order_client_reference_id")
    if req_ref is not None and req_ref != order_ref:
        violations.append("ACP_ORDER_CLIENT_REFERENCE_ID_MISMATCH")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def validate_x402_mcp_siwx_entitlement_and_witness_sar_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate Coinbase x402 #27 MCP + SIWX entitlement reuse and #50/#46 DefaultVerifier SAR receipt."""
    violations: list[str] = []

    mcp = payload.get("mcp_tool_invocation", {})
    if mcp:
        call_index = int(mcp.get("call_index", 0))
        tool_name = str(mcp.get("tool_name", ""))
        payment_settled = bool(mcp.get("payment_settled", False))
        if call_index == 0:
            if not payment_settled:
                violations.append("X402_MCP_INITIAL_CALL_PAYMENT_SETTLEMENT_REQUIRED")
        else:
            if not payment_settled:
                if not mcp.get("siwx_wallet_auth_verified", False):
                    violations.append("X402_MCP_SIWX_REUSE_WALLET_AUTH_REQUIRED")
                if not mcp.get("stored_entitlement_active", False):
                    violations.append("X402_MCP_SIWX_REUSE_STORED_ENTITLEMENT_INACTIVE")
                if str(mcp.get("entitlement_tool_name", "")) != tool_name:
                    violations.append("X402_MCP_SIWX_CROSS_TOOL_ENTITLEMENT_REUSE_FORBIDDEN")

    sar = payload.get("settlement_attestation_receipt", {})
    if sar:
        if not sar.get("task_satisfied", False):
            violations.append("X402_SAR_TASK_SPECIFICATION_NOT_SATISFIED")
        if not sar.get("witness_signature_valid", False):
            violations.append("X402_SAR_WITNESS_SIGNATURE_INVALID")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def _normalize_nested_json_arg(val: Any) -> Any:
    if isinstance(val, str):
        stripped = val.strip()
        if (stripped.startswith("{") and stripped.endswith("}")) or (
            stripped.startswith("[") and stripped.endswith("]")
        ):
            try:
                parsed = json.loads(stripped)
                return _normalize_nested_json_arg(parsed)
            except ValueError:
                return val
        return val
    if isinstance(val, dict):
        return {k: _normalize_nested_json_arg(v) for k, v in sorted(val.items())}
    if isinstance(val, list):
        return [_normalize_nested_json_arg(x) for x in val]
    return val


def validate_tau2_nested_json_numeric_seed_and_batch_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate Sierra tau2-bench #401 nested JSON-string grading, #397 numeric DB-hash normalization, and #393 batch evaluator guard."""
    violations: list[str] = []

    comp = payload.get("nested_json_comparison", {})
    if comp:
        gold_norm = _normalize_nested_json_arg(comp.get("gold_arg"))
        pred_norm = _normalize_nested_json_arg(comp.get("predicted_arg"))
        actual_equal = gold_norm == pred_norm
        expected_equal = bool(comp.get("expected_equal", True))
        if actual_equal != expected_equal:
            violations.append("TAU2_NESTED_JSON_STRING_GRADING_MISMATCH")

    num_call = payload.get("banking_numeric_call", {})
    if num_call:
        tool_name = str(num_call.get("tool_name", ""))
        raw_val = num_call.get("amount_or_limit")
        if tool_name in INTEGER_STRICT_BANKING_TOOLS:
            if isinstance(raw_val, float) and not raw_val.is_integer():
                violations.append(f"TAU2_BANKING_INTEGER_TOOL_FRACTIONAL_VALUE_FORBIDDEN:{tool_name}")
            elif isinstance(raw_val, str) and "." in raw_val:
                violations.append(f"TAU2_BANKING_INTEGER_TOOL_FRACTIONAL_STRING_FORBIDDEN:{tool_name}")
        else:
            canonical_seed = f"{float(raw_val):.2f}"
            if str(num_call.get("recorded_id_seed_amount", "")) != canonical_seed:
                violations.append("TAU2_BANKING_FLOAT_SEED_UNNORMALIZED_HASH_DRIFT")

    batch = payload.get("batch_evaluator_event", {})
    if batch:
        exc_type = str(batch.get("exception_type", ""))
        if exc_type == "EvaluationCriteriaError":
            if not batch.get("reraised_loudly", False):
                violations.append("TAU2_EVALUATION_CRITERIA_ERROR_SILENTLY_SWALLOWED")
        elif exc_type:
            if batch.get("aborted_entire_batch", False) or batch.get("fallback_reward") != 0.0:
                violations.append("TAU2_RUNTIME_SIM_ERROR_ABORTED_BATCH")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }
