"""Stage 106 deterministic protocol guardrails.

Covers:
1. UCP PRs #325, #340, #326, #324:
   - #325: ECP result envelope (`result.ucp.status` discriminator, JSON-RPC top-level `error`
     reserved for transport failures only, decoupled `severity`, and mandatory host teardown
     when `ec.ready` fails).
   - #340: Loyalty extension for catalog/cart/checkout (`loyalty_tier_disclosed` and non-negative
     fungible delayed-value `earning_forecast_points`).
   - #326 & #324: Optional human-readable `Order.label` distinct from immutable `Order.id`, and
     prohibition of non-date `"draft"` protocol versions in public discovery profiles.
2. OpenAI/Stripe ACP PRs #35, #32, #28, #18, #17:
   - #35: Brazilian PIX payment method in `BRL` (`provider` in `{"mercado_pago", "pagseguro"}`
     and 11-digit CPF or 14-digit CNPJ validation).
   - #32 & #28: Mandatory `TLSv1.3`, constant-time webhook signature verification, `Request-Id`
     idempotency header, and `<= 300s` timestamp replay window.
   - #18 & #17: Integer minor-unit monetary fields on `FulfillmentOptionShipping`,
     `FulfillmentOptionDigital`, and `FulfillmentOptionPickup` (with `pickup_location_id`).
3. Google AP2 PRs #64, #121, #216 & Coinbase x402 PRs #88, #135:
   - AP2 #64, #121, #216: Structured `AP2ErrorCode` with field-path reporting, plus non-custodial
     `IntentMandate` monthly USDC cap and EIP-712 signature verification.
   - x402 #88 & #135: RFC 6962 Signed Tree Head (`sth_signature_valid`) + Merkle inclusion proof
     verification, and Tenzro multi-VM `extra.facade` (`evm`/`svm`/`canton`) dispatch checks.
4. Sierra tau2-bench PRs #462, #444, #443:
   - #462: Multi-customer Telecom `DB` reward-basis enforcement, valid `(customer_id, line_id)`
     pair, and unshadowed 4,538-task catalog check.
   - #444: Leaderboard `submission_type` classification (`"standard"` vs `"custom"` reserved
     strictly for architectural scaffold changes).
   - #443: Trajectory cost (`cost + user_cost == total_cost`) and wall-clock time breakdown
     (`agent_time_seconds + user_time_seconds + tool_time_seconds <= duration_seconds`).
"""

from __future__ import annotations

import re
from typing import Any

DATE_VERSION_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CPF_CNPJ_RE = re.compile(r"^(\d{11}|\d{14})$")
ALLOWED_PIX_PROVIDERS = {"mercado_pago", "pagseguro"}
ALLOWED_TENZRO_FACADES = {"evm", "svm", "canton"}


def validate_ucp_ecp_envelope_loyalty_order_label_and_version_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    violations: list[str] = []

    ecp = payload.get("ecp_response", {})
    has_jsonrpc_error = bool(ecp.get("has_jsonrpc_error", False))
    is_transport_failure = bool(ecp.get("is_transport_failure", False))
    ucp_status = str(ecp.get("result_ucp_status", ""))
    method_name = str(ecp.get("method", "ec.payment.submit"))
    host_tore_down = bool(ecp.get("host_tore_down_on_ec_ready_error", False))

    if has_jsonrpc_error and not is_transport_failure:
        violations.append("UCP_325_DELEGATION_ERROR_IN_JSONRPC_ERROR_FIELD_FORBIDDEN")
    if not has_jsonrpc_error and ucp_status not in {"ok", "error"}:
        violations.append("UCP_325_MISSING_OR_INVALID_RESULT_UCP_STATUS_DISCRIMINATOR")
    if method_name == "ec.ready" and ucp_status == "error" and not host_tore_down:
        violations.append("UCP_325_EC_READY_ERROR_REQUIRES_HOST_TEARDOWN")

    loyalty = payload.get("loyalty_extension", {})
    if not bool(loyalty.get("loyalty_tier_disclosed", False)):
        violations.append("UCP_340_LOYALTY_TIER_DISCLOSURE_MISSING")
    points = int(loyalty.get("earning_forecast_points", -1))
    if points < 0:
        violations.append("UCP_340_INVALID_NEGATIVE_EARNING_FORECAST_POINTS")

    order_meta = payload.get("order_and_version", {})
    order_id = str(order_meta.get("order_id", "")).strip()
    order_label = str(order_meta.get("order_label", "")).strip()
    advertised_version = str(order_meta.get("advertised_discovery_version", ""))

    if not order_id or not order_label or order_id == order_label:
        violations.append("UCP_326_ORDER_ID_AND_HUMAN_LABEL_MUST_BE_DISTINCT_NON_EMPTY")
    if not DATE_VERSION_RE.match(advertised_version):
        violations.append("UCP_324_NON_DATE_DRAFT_VERSION_IN_PUBLIC_DISCOVERY_FORBIDDEN")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def validate_acp_pix_tls13_webhook_and_integer_fulfillment_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    violations: list[str] = []

    pix = payload.get("pix_payment", {})
    if str(pix.get("currency", "")) != "BRL":
        violations.append("ACP_35_PIX_REQUIRES_BRL_CURRENCY")
    if str(pix.get("provider", "")) not in ALLOWED_PIX_PROVIDERS:
        violations.append("ACP_35_UNSUPPORTED_PIX_PROVIDER")
    tax_id = str(pix.get("cpf_or_cnpj", ""))
    if not CPF_CNPJ_RE.match(tax_id):
        violations.append("ACP_35_INVALID_CPF_OR_CNPJ_FORMAT")

    transport = payload.get("transport_and_webhook", {})
    if str(transport.get("tls_version", "")) != "TLSv1.3":
        violations.append("ACP_32_TLS_1_3_REQUIRED")
    if not bool(transport.get("constant_time_signature_verified", False)):
        violations.append("ACP_28_WEBHOOK_CONSTANT_TIME_SIGNATURE_REQUIRED")
    if not str(transport.get("request_id", "")).strip():
        violations.append("ACP_28_WEBHOOK_REQUEST_ID_HEADER_MISSING")
    skew_sec = abs(int(transport.get("timestamp_skew_seconds", 9999)))
    if skew_sec > 300:
        violations.append("ACP_28_WEBHOOK_TIMESTAMP_REPLAY_WINDOW_EXCEEDED")

    ff = payload.get("fulfillment_option", {})
    amount = ff.get("amount_minor")
    if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
        violations.append("ACP_18_FULFILLMENT_MONETARY_FIELD_MUST_BE_NON_NEGATIVE_INTEGER")
    if str(ff.get("type", "")) == "pickup" and not str(ff.get("pickup_location_id", "")).strip():
        violations.append("ACP_17_PICKUP_FULFILLMENT_MISSING_LOCATION_ID")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def validate_ap2_error_field_intent_cap_and_x402_rfc6962_tenzro_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    violations: list[str] = []

    ap2_val = payload.get("ap2_validation_and_intent", {})
    if bool(ap2_val.get("has_validation_error", False)):
        if not str(ap2_val.get("error_code", "")).strip() or not str(ap2_val.get("field_path", "")).strip():
            violations.append("AP2_64_VALIDATION_ERROR_MISSING_CODE_OR_FIELD_PATH")
    monthly_used = int(ap2_val.get("cumulative_monthly_usdc_micro", 0))
    monthly_cap = int(ap2_val.get("monthly_cap_usdc_micro", 0))
    if monthly_cap <= 0 or monthly_used > monthly_cap:
        violations.append("AP2_216_NON_CUSTODIAL_INTENT_MONTHLY_CAP_EXCEEDED")
    if not bool(ap2_val.get("eip712_intent_signature_valid", False)):
        violations.append("AP2_216_EIP712_INTENT_SIGNATURE_INVALID")

    x402_trust = payload.get("x402_rfc6962_and_tenzro", {})
    if not bool(x402_trust.get("sth_ed25519_signature_valid", False)) or not bool(
        x402_trust.get("merkle_inclusion_proof_valid", False)
    ):
        violations.append("X402_88_RFC6962_STH_OR_INCLUSION_PROOF_INVALID")

    facade = str(x402_trust.get("tenzro_facade", ""))
    if facade not in ALLOWED_TENZRO_FACADES:
        violations.append("X402_135_INVALID_TENZRO_MULTI_VM_FACADE")
    elif facade == "svm" and not bool(x402_trust.get("svm_9dec_spl_truncation_checked", False)):
        violations.append("X402_135_TENZRO_SVM_SPL_TRUNCATION_CHECK_MISSING")
    elif facade == "canton" and not bool(x402_trust.get("canton_cip56_holding_transfer_valid", False)):
        violations.append("X402_135_TENZRO_CANTON_CIP56_HOLDING_TRANSFER_INVALID")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def validate_tau2_telecom_db_reward_custom_arch_and_cost_time_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    violations: list[str] = []

    telecom = payload.get("telecom_check", {})
    reward_basis = list(telecom.get("reward_basis", []))
    if "DB" not in reward_basis:
        violations.append("TAU2_462_TELECOM_REWARD_BASIS_MISSING_DB")
    if not bool(telecom.get("customer_line_pair_valid_in_db", False)):
        violations.append("TAU2_462_INVALID_CUSTOMER_LINE_PAIR")
    if int(telecom.get("generated_task_count", 0)) != 4538:
        violations.append("TAU2_462_SHADOWED_OR_INCOMPLETE_TELECOM_TASK_COUNT")

    sub = payload.get("leaderboard_submission", {})
    sub_type = str(sub.get("submission_type", ""))
    has_arch_change = bool(sub.get("has_architectural_scaffold_change", False))
    expected_type = "custom" if has_arch_change else "standard"
    if sub_type != expected_type:
        violations.append("TAU2_444_SUBMISSION_TYPE_ARCHITECTURE_MISMATCH")

    metrics = payload.get("cost_time_metrics", {})
    agent_cost = float(metrics.get("cost", 0.0))
    user_cost = float(metrics.get("user_cost", 0.0))
    total_cost = float(metrics.get("total_cost", -1.0))
    if agent_cost < 0 or user_cost < 0 or abs((agent_cost + user_cost) - total_cost) > 1e-6:
        violations.append("TAU2_443_TOTAL_COST_BREAKDOWN_MISMATCH")

    dur = float(metrics.get("duration_seconds", 0.0))
    t_agent = float(metrics.get("agent_time_seconds", -1.0))
    t_user = float(metrics.get("user_time_seconds", -1.0))
    t_tool = float(metrics.get("tool_time_seconds", -1.0))
    if (
        dur <= 0
        or t_agent < 0
        or t_user < 0
        or t_tool < 0
        or (t_agent + t_user + t_tool) > dur + 1e-3
    ):
        violations.append("TAU2_443_TIME_BREAKDOWN_EXCEEDS_DURATION_OR_NEGATIVE")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }
