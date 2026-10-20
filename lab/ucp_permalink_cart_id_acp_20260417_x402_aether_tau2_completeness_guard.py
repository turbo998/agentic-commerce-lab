"""Stage 108 protocol guardrails: UCP (#968/#913/#763/#633/#568), ACP (#227/#219/#176/#102),
Google AP2 (#157/#148/#122) + Coinbase x402 (#367/#343), and Sierra tau2-bench (#650/#623/#500).
"""

from __future__ import annotations

from typing import Any


REQUIRED_WEBHOOK_SIG_COMPONENTS = {
    "@method",
    "@authority",
    "@path",
    "content-digest",
    "content-type",
    "ucp-agent",
}

CANONICAL_USDC_BY_CAIP2 = {
    "eip155:8453": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "eip155:84532": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
}


def validate_ucp_permalink_headers_cart_id_omission_and_webhook_sig_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate UCP #968/#913 permalink 303 headers, #763/#633 cart.id omission on update, and #568 webhook ucp-agent signing."""
    violations: list[str] = []

    permalink = payload.get("permalink_303", {})
    if permalink.get("status_code") != 303:
        violations.append("UCP_913_PERMALINK_REDIRECT_MUST_BE_303")
    if permalink.get("cache_control") != "no-store":
        violations.append("UCP_913_MISSING_CACHE_CONTROL_NO_STORE")
    if permalink.get("referrer_policy") != "no-referrer":
        violations.append("UCP_913_MISSING_REFERRER_POLICY_NO_REFERRER")
    if not permalink.get("routed_to_continue_to_or_safe_fallback", False):
        violations.append("UCP_968_UNSAFE_PERMALINK_FALLBACK_ROUTE")

    cart_update = payload.get("cart_update_request", {})
    if "id" in cart_update.get("body", {}):
        violations.append("UCP_763_633_CART_ID_FORBIDDEN_IN_UPDATE_BODY")
    if cart_update.get("has_deprecated_transition_annotation", False):
        violations.append("UCP_763_DEPRECATED_TRANSITION_ANNOTATION_PRESENT")
    if not str(cart_update.get("path_cart_id", "")).strip():
        violations.append("UCP_633_MISSING_TRANSPORT_PATH_CART_ID")

    webhook = payload.get("order_webhook", {})
    signed_components = set(webhook.get("signature_input_components", []))
    if webhook.get("has_ucp_agent_header", True) and not REQUIRED_WEBHOOK_SIG_COMPONENTS.issubset(
        signed_components
    ):
        violations.append("UCP_568_WEBHOOK_SIGNATURE_INPUT_MISSING_UCP_AGENT")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def validate_acp_20260417_release_refund_minor_units_and_seller_discovery_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate ACP #227 2026-04-17 release contract, #219 integer minor-unit webhook refund, #176 seller terminology, and #102 ref."""
    violations: list[str] = []

    release = payload.get("release_snapshot", {})
    supported_versions = release.get("supported_versions", [])
    if not isinstance(supported_versions, list) or "2026-04-17" not in supported_versions:
        violations.append("ACP_227_MISSING_2026_04_17_IN_SUPPORTED_VERSIONS")

    refund = payload.get("webhook_refund", {})
    amount = refund.get("amount")
    if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
        violations.append("ACP_219_WEBHOOK_REFUND_AMOUNT_MUST_BE_MINOR_UNIT_INT")

    discovery = payload.get("discovery_document", {})
    if discovery.get("actor_terminology") != "seller" or "platform_id" in discovery:
        violations.append("ACP_176_DISCOVERY_MUST_USE_SELLER_TERMINOLOGY")

    schema_ref = payload.get("selected_fulfillment_schema_ref", "")
    if schema_ref != "#/$defs/SelectedFulfillmentOption":
        violations.append("ACP_102_INVALID_SELECTED_FULFILLMENT_OPTION_REF")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def validate_ap2_jwt_timestamps_pay_by_bank_and_x402_aether_audit_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate AP2 #157/#148/#122 JWT timestamps & pay-by-bank and x402 #367/#343 Aether payability audit & burn-once vault."""
    violations: list[str] = []

    ap2 = payload.get("ap2_mandate", {})
    iat = ap2.get("iat")
    exp = ap2.get("exp")
    if (
        not isinstance(iat, int)
        or isinstance(iat, bool)
        or not isinstance(exp, int)
        or isinstance(exp, bool)
        or exp <= iat
    ):
        violations.append("AP2_157_INVALID_MANDATE_JWT_IAT_EXP_TIMESTAMPS")
    if not ap2.get("shopping_agent_validated", False):
        violations.append("AP2_148_SHOPPING_AGENT_VALIDATION_FAILED")
    if ap2.get("payment_rail") == "pay_by_bank" and not ap2.get("bank_account_mandate_bound", False):
        violations.append("AP2_122_PAY_BY_BANK_MISSING_MANDATE_BINDING")

    x402 = payload.get("x402_aether_audit", {})
    caip2 = str(x402.get("caip2_network", ""))
    usdc_asset = str(x402.get("usdc_asset", ""))
    if x402.get("http_status") != 402 or not x402.get("payment_required_decoded", False):
        violations.append("X402_367_INVALID_402_CHALLENGE_OR_HEADER")
    if CANONICAL_USDC_BY_CAIP2.get(caip2) != usdc_asset:
        violations.append("X402_367_CAIP2_USDC_ASSET_NETWORK_MISMATCH")
    if not x402.get("payto_eip55_checksum_valid", False) or not x402.get(
        "eip712_domain_valid", False
    ):
        violations.append("X402_367_PAYTO_CHECKSUM_OR_EIP712_DOMAIN_INVALID")
    if int(x402.get("burn_once_secret_reads", 0)) > 1:
        violations.append("X402_343_BURN_ONCE_SECRET_READ_REPLAY_DETECTED")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def validate_tau2_v2_completeness_live_transcript_and_set_state_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate Sierra tau2-bench #650 2.0 completeness/Live transcript rules, #623 v1.0.1 task pin, and #500 set_state signature."""
    violations: list[str] = []

    cell = payload.get("cell_completeness", {})
    owed_calls = int(cell.get("owed_calls", 0))
    scored_calls = int(cell.get("scored_calls", 0))
    infra_error_calls = int(cell.get("error_trials", 0))
    unscored_missing_calls = int(cell.get("unscored_missing_calls", 0))
    reported_denominator = int(cell.get("reported_denominator", 0))

    if (
        owed_calls <= 0
        or scored_calls < 1
        or unscored_missing_calls > 0
        or scored_calls + infra_error_calls != owed_calls
        or reported_denominator != scored_calls
    ):
        violations.append("TAU2_650_INVALID_CELL_COMPLETENESS_OR_DENOMINATOR")

    judge = payload.get("live_judge_diagnostics", {})
    if not judge.get("fingerprint_has_input_error_units", False):
        violations.append("TAU2_650_VERDICT_FINGERPRINT_MISSING_INPUT_ERROR_UNITS")
    if int(judge.get("judged_applicable_calls", 0)) < 1 or int(judge.get("other_judge_errors", 0)) > 0:
        violations.append("TAU2_650_ALL_APPLICABLE_CALLS_EXCLUDED_OR_JUDGE_ERROR")

    if payload.get("v1x_base_task_pin") != "v1.0.1":
        violations.append("TAU2_623_V1X_BASE_TASKS_NOT_PINNED_TO_V1_0_1")

    set_state = payload.get("set_state_call", {})
    if not set_state.get("passes_initialization_data_arg", False) or int(
        set_state.get("positional_arg_count", 0)
    ) != 4:
        violations.append("TAU2_500_SET_STATE_MISSING_INITIALIZATION_DATA_ARG")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }
