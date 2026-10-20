"""Stage 92 deterministic guardrails for UCP Fee/ECaP/ec.totals.change, ACP Sale/Discount/x402-Crypto SPT, AP2 PaymentReceipt/AuditLog, and Sierra tau2-bench Airline Seat Release & Context-Window Classification.

Primary-source references:
- Universal-Commerce-Protocol/ucp PRs #245 (`dev.ucp.shopping.fee` Fee Extension), #244 (`Embedded Cart Protocol` ECaP + `ep.cart.auth`), and #272 (`ec.totals.change` in ECP).
- agentic-commerce-protocol/agentic-commerce-protocol PRs #125 (Consolidate `DiscountDetail` & `AppliedDiscount`), #123 (`sale` extension & EU Omnibus 30-day lowest price + `discount_eligible`), and #111 (x402-backed `crypto` payment method in `delegate_payment` issuing deferred-settlement SPT).
- google-agentic-commerce/AP2 PRs #110 (Section 7.1 `PaymentReceipt` v0.1) and #92 (Mandate Lifecycle PCI/SOX/GDPR Audit Log Standards).
- Sierra-Research/tau2-bench PRs #362 (release airline seats on cancellation), #360 (`CONTEXT_WINDOW_EXCEEDED` deterministic non-retry & denominator exclusion), #358 (drop `temperature` for reasoning models), and #364 (Return-and-Exchange `token_usage` & `cost_per_resolved_case`).
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qs, urlparse

RFC9535_ALLOCATION_PATH_RE = re.compile(r"^\$\.(line_items\[\d+\]|subtotal|shipping|fulfillment)(\.[a-zA-Z0-9_]+)?$")
SENSITIVE_QUERY_KEYS = {"access_token", "auth", "auth_token", "code", "id_token", "refresh_token", "secret", "token"}
VALID_APPLIED_DISCOUNT_TYPES = {"percentage", "fixed"}
VALID_RECEIPT_STATUSES = {"SUCCESS", "FAILURE", "PENDING"}


def validate_ucp_fee_extension_ecap_and_totals_change_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate UCP #245 Fee Extension, #244 Embedded Cart Protocol (ECaP), and #272 ec.totals.change."""
    violations: list[str] = []

    req_body = payload.get("client_request_body", {})
    if "fees" in req_body or "applied_fees" in req_body:
        violations.append("UCP_FEE_READONLY_CLIENT_FIELD_NOT_ALLOWED")

    fees_applied = payload.get("fees_applied", [])
    for idx, fee in enumerate(fees_applied):
        fee_type = str(fee.get("fee_type", "")).strip()
        if not fee_type:
            violations.append(f"UCP_FEE_TYPE_REQUIRED:index_{idx}")
        amount = fee.get("amount")
        if not isinstance(amount, int) or amount <= 0:
            violations.append(f"UCP_FEE_NON_POSITIVE_OR_WAIVED_AMOUNT_FORBIDDEN:index_{idx}")
        allocations = fee.get("allocations", [])
        if allocations:
            alloc_sum = 0
            for alloc in allocations:
                path = str(alloc.get("path", ""))
                if not RFC9535_ALLOCATION_PATH_RE.match(path):
                    violations.append(f"UCP_FEE_INVALID_RFC9535_ALLOCATION_PATH:{path}")
                alloc_sum += int(alloc.get("amount", 0))
            if isinstance(amount, int) and alloc_sum != amount:
                violations.append(f"UCP_FEE_ALLOCATION_SUM_MISMATCH:{alloc_sum}!={amount}")

    ecap = payload.get("ecap_session", {})
    continue_url = str(ecap.get("continue_url", ""))
    if continue_url:
        parsed = urlparse(continue_url)
        query_keys = {k.lower() for k in parse_qs(parsed.query).keys()}
        leaked = sorted(query_keys & SENSITIVE_QUERY_KEYS)
        if leaked:
            violations.append(f"UCP_ECAP_CONTINUE_URL_AUTH_QUERY_LEAK:{','.join(leaked)}")
    if ecap.get("requires_auth", False) and not ecap.get("ep_cart_auth_postmessage_used", False):
        violations.append("UCP_ECAP_POSTMESSAGE_AUTH_HANDSHAKE_REQUIRED")
    if ecap.get("declared_extensions", []):
        violations.append("UCP_ECAP_EXTENSIONS_OUT_OF_SCOPE_FORBIDDEN")

    totals_msg = payload.get("ec_totals_change")
    if isinstance(totals_msg, dict):
        if totals_msg.get("method") != "ec.totals.change":
            violations.append("UCP_ECP_TOTALS_CHANGE_METHOD_INVALID")
        totals = totals_msg.get("totals", [])
        if not isinstance(totals, list) or len(totals) == 0:
            violations.append("UCP_ECP_TOTALS_CHANGE_EMPTY_TOTALS")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def validate_acp_consolidated_discount_sale_omnibus_and_x402_crypto_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate ACP #125 consolidated AppliedDiscount, #123 Sale Extension (EU Omnibus), and #111 x402 Crypto SPT."""
    violations: list[str] = []

    line_items = payload.get("line_items", [])
    session_sales = {str(s.get("id")): s for s in payload.get("sales", []) if isinstance(s, dict) and s.get("id")}
    ineligible_item_ids: set[str] = set()

    for item in line_items:
        item_id = str(item.get("id", ""))
        unit_amount = int(item.get("unit_amount", 0))
        if item.get("discount_eligible") is False:
            ineligible_item_ids.add(item_id)
        if item.get("discount_details"):
            violations.append(f"ACP_DEPRECATED_LINE_ITEM_DISCOUNT_DETAILS_FORBIDDEN:{item_id}")

        sale_obj = item.get("sale")
        if isinstance(sale_obj, dict):
            sale_id = str(sale_obj.get("id", ""))
            if sale_id not in session_sales:
                violations.append(f"ACP_SALE_ID_NOT_IN_SESSION_REGISTRY:{sale_id}")
            compare_at = int(sale_obj.get("compare_at_amount", 0))
            if compare_at <= unit_amount:
                violations.append(f"ACP_SALE_COMPARE_AT_NOT_GREATER_THAN_UNIT_AMOUNT:{item_id}")
            if sale_obj.get("eu_omnibus_applicable", False):
                lowest_recent = int(sale_obj.get("lowest_recent_amount", 0))
                period_days = int(sale_obj.get("lowest_recent_period_days", 0))
                if lowest_recent <= 0 or period_days < 30:
                    violations.append(f"ACP_SALE_EU_OMNIBUS_30DAY_LOWEST_PRICE_REQUIRED:{item_id}")

    for disc in payload.get("applied_discounts", []):
        if "automatic" in disc:
            violations.append("ACP_APPLIED_DISCOUNT_REMOVED_AUTOMATIC_FIELD_FORBIDDEN")
        dtype = disc.get("type")
        if dtype is not None and dtype not in VALID_APPLIED_DISCOUNT_TYPES:
            violations.append(f"ACP_APPLIED_DISCOUNT_INVALID_TYPE_ENUM:{dtype}")
        if disc.get("is_catalog_level_price_reduction", False):
            violations.append("ACP_CATALOG_PRICE_REDUCTION_AS_APPLIED_DISCOUNT_FORBIDDEN")
        if disc.get("code"):
            excluded_ids = {str(ex.get("item_id")) for ex in disc.get("excluded_items", []) if isinstance(ex, dict)}
            for alloc in disc.get("allocations", []):
                target_id = str(alloc.get("item_id", ""))
                if target_id in ineligible_item_ids and target_id not in excluded_ids:
                    violations.append(f"ACP_DISCOUNT_CODE_APPLIED_TO_INELIGIBLE_ITEM:{target_id}")

    crypto_pm = payload.get("crypto_delegate_payment")
    if isinstance(crypto_pm, dict):
        if crypto_pm.get("type") != "crypto":
            violations.append("ACP_CRYPTO_PAYMENT_METHOD_TYPE_MISMATCH")
        allowance_max = int(crypto_pm.get("allowance_max_amount", 0))
        x402 = crypto_pm.get("x402_payload", {})
        x402_amount = int(x402.get("amount", -1))
        valid_before = int(x402.get("valid_before", 0))
        now_ts = int(crypto_pm.get("current_timestamp", 0))
        if x402_amount != allowance_max:
            violations.append(f"ACP_X402_AMOUNT_ALLOWANCE_MISMATCH:{x402_amount}!={allowance_max}")
        if valid_before <= now_ts:
            violations.append("ACP_X402_AUTHORIZATION_EXPIRED")
        if x402.get("nonce_reused", False):
            violations.append("ACP_X402_NONCE_REPLAY_DETECTED")
        if not x402.get("facilitator_signature_verified", False):
            violations.append("ACP_X402_FACILITATOR_SIGNATURE_INVALID")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def validate_ap2_payment_receipt_and_audit_log_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate Google AP2 #110 Section 7.1 PaymentReceipt and #92 Mandate Audit Log Standards."""
    violations: list[str] = []

    receipt = payload.get("payment_receipt", {})
    for req_field in ("payment_mandate_id", "cart_mandate_id", "transaction_id", "timestamp", "rail_reference"):
        if not str(receipt.get(req_field, "")).strip():
            violations.append(f"AP2_PAYMENT_RECEIPT_MISSING_FIELD:{req_field}")
    status = receipt.get("payment_status")
    if status not in VALID_RECEIPT_STATUSES:
        violations.append(f"AP2_PAYMENT_RECEIPT_INVALID_STATUS:{status}")
    receipt_amt = receipt.get("amount")
    mandate_amt = receipt.get("payment_mandate_amount")
    if receipt_amt != mandate_amt:
        violations.append(f"AP2_PAYMENT_RECEIPT_AMOUNT_MISMATCH:{receipt_amt}!={mandate_amt}")

    audit = payload.get("audit_log", {})
    stages = audit.get("recorded_lifecycle_stages", [])
    expected_stages = ["created", "signed", "verified", "settled"]
    if stages != expected_stages:
        violations.append("AP2_AUDIT_LOG_INCOMPLETE_MANDATE_LIFECYCLE")
    if audit.get("contains_unmasked_pan_or_pii", False):
        violations.append("AP2_AUDIT_LOG_PCI_GDPR_UNMASKED_PII_LEAK")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def validate_tau2_airline_seat_release_and_context_window_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate Sierra tau2-bench #362 airline seat restoration, #360 context-window non-retry, #358 reasoning temperature drop, and #364 cost-per-resolution."""
    violations: list[str] = []

    cancel = payload.get("airline_cancellation", {})
    if cancel:
        passengers = int(cancel.get("passenger_count", 0))
        for seg in cancel.get("flight_segments", []):
            seg_id = str(seg.get("flight_id", "unknown"))
            before = int(seg.get("seats_before_cancel", 0))
            after = int(seg.get("seats_after_cancel", 0))
            if after != before + passengers:
                violations.append(f"TAU2_AIRLINE_CANCEL_SEAT_INVENTORY_NOT_RESTORED:{seg_id}")

    ctx_err = payload.get("context_window_failure", {})
    if ctx_err.get("error_type") == "ContextWindowExceededError":
        if int(ctx_err.get("full_sim_retries_attempted", 0)) > 0:
            violations.append("TAU2_CONTEXT_WINDOW_REDUNDANT_SIM_RETRY_FORBIDDEN")
        if ctx_err.get("termination_reason") != "CONTEXT_WINDOW_EXCEEDED":
            violations.append(f"TAU2_CONTEXT_WINDOW_MISLABELED_REASON:{ctx_err.get('termination_reason')}")
        if ctx_err.get("included_in_evaluable_denominator", False):
            violations.append("TAU2_CONTEXT_WINDOW_MUST_EXCLUDE_FROM_DENOMINATOR")

    reasoning = payload.get("reasoning_model_call", {})
    if reasoning.get("is_reasoning_model", False) and reasoning.get("rejected_zero_temperature", False):
        if not reasoning.get("dropped_temperature_on_retry", False):
            violations.append("TAU2_REASONING_MODEL_TEMPERATURE_NOT_DROPPED")

    cost = payload.get("return_exchange_eval", {})
    if cost:
        usage = cost.get("token_usage", {})
        if not all(k in usage for k in ("agent_tokens", "supervisor_tokens", "user_sim_tokens")):
            violations.append("TAU2_RETURN_EXCHANGE_TOKEN_USAGE_INCOMPLETE")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }
