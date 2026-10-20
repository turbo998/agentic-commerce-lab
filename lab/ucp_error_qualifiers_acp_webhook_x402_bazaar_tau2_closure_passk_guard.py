"""Stage 96 deterministic guardrails for UCP Error Discriminator / Payment Qualifiers / Handler Available Instruments, ACP Webhook Replay & Extensible Error Enums, Coinbase x402 EIP-3009 Error Mapping & Bazaar Metadata Sanitizer, and Sierra tau2-bench Canonical Account Closure / pass^k Denominator / Tool Kwarg Coercion / Result-Safe Retries.

Primary-source references:
- Universal-Commerce-Protocol/ucp PRs #216 & #223 (`ucp.status` discriminator & `unrecoverable` error_response envelope), #214 (`PaymentInstrument.qualifiers` reverse-domain hints), and #187 (`payment_handler.available_instruments` constraint matching).
- agentic-commerce-protocol/agentic-commerce-protocol PRs #160 (`Merchant-Signature: t=<ts>,v1=<hex>` webhook HMAC & 300s replay window) and #161/#143 (`DelegatePayment` 401/500/503/intervention_required error enums & RFC §4.2 forward-compatible client handling).
- coinbase/x402 PRs #70 (`ErrEip3009SimulationFailed` & `parseEIP3009TransferError` revert mapping) and #156/#150 (`bazaar.SanitizeResourceServiceMetadata` printable-ASCII, loopback/IP-literal iconUrl rejection, and case-insensitive tag deduplication).
- Sierra-Research/tau2-bench PRs #484 (`close_bank_account_7392` canonical `reason` enum), #498 (pandas 3 `.value` infra-error filter & all-infra-error task retention in `pass^k` denominator), #516 (Pydantic tool kwarg schema coercion), and #520 (result-safe hallucination retries).
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import re
from typing import Any
from urllib.parse import urlsplit

MERCHANT_SIG_RE = re.compile(r"^t=(\d+),v1=([a-fA-F0-9]{64})$")
REVERSE_DOMAIN_RE = re.compile(r"^[a-z0-9-]+(\.[a-z0-9_-]+)+$")
FORBIDDEN_UCP_ERROR_RESOURCE_KEYS = {
    "id",
    "line_items",
    "totals",
    "buyer",
    "fulfillment",
    "payment",
    "cart",
    "checkout",
}
KNOWN_EIP3009_REVERT_MAP = {
    "authorization_expired": "ErrEip3009AuthorizationExpired",
    "not_yet_valid": "ErrEip3009AuthorizationNotYetValid",
    "nonce_already_used": "ErrEip3009NonceAlreadyUsed",
    "insufficient_balance": "ErrEip3009InsufficientBalance",
    "invalid_signature": "ErrEip3009InvalidSignature",
}
LOOPBACK_ALIASES = {
    "localhost",
    "localhost.localdomain",
    "ip6-localhost",
    "ip6-loopback",
}
VALID_BANK_CLOSURE_REASONS = {
    "customer_request",
    "simplifying_finances",
    "moving_banks",
    "fees_too_high",
    "fraud_suspected",
    "other",
}


def validate_ucp_status_error_qualifiers_and_instruments_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate UCP #216/#223 ucp.status error envelope, #214 payment instrument qualifiers, and #187 available_instruments."""
    violations: list[str] = []

    envelope = payload.get("ucp_response_envelope", {})
    if envelope:
        ucp_meta = envelope.get("ucp", {})
        status = ucp_meta.get("status", "success")
        if status == "error":
            present_forbidden = FORBIDDEN_UCP_ERROR_RESOURCE_KEYS.intersection(envelope.keys())
            if present_forbidden or envelope.get("wrapped_under_cart_key", False):
                violations.append("UCP_ERROR_RESPONSE_MUST_NOT_INCLUDE_RESOURCE_OR_CART_WRAPPER")
            msgs = envelope.get("messages", [])
            has_unrecoverable = any(
                isinstance(m, dict)
                and m.get("type") == "error"
                and m.get("severity") == "unrecoverable"
                and str(m.get("content", "")).strip()
                for m in msgs
            )
            if not has_unrecoverable:
                violations.append("UCP_ERROR_RESPONSE_UNRECOVERABLE_MESSAGE_REQUIRED")
        elif status != "success":
            violations.append("UCP_STATUS_DISCRIMINATOR_INVALID")

    qual_check = payload.get("payment_qualifier_check", {})
    if qual_check:
        inst_qualifiers = [str(q) for q in qual_check.get("instrument_qualifiers", [])]
        for q in inst_qualifiers:
            if not REVERSE_DOMAIN_RE.match(q):
                violations.append(f"UCP_PAYMENT_QUALIFIER_NAMESPACE_INVALID:{q}")
        if qual_check.get("benefits_applied_pre_completion", False):
            required_quals = set(str(q) for q in qual_check.get("required_benefit_qualifiers", []))
            verified_quals = set(str(q) for q in qual_check.get("verified_completion_qualifiers", []))
            if not required_quals.issubset(verified_quals):
                violations.append("UCP_PAYMENT_QUALIFIER_BENEFIT_MISMATCH_AT_COMPLETION")

    handler_check = payload.get("handler_available_instruments_check", {})
    if handler_check:
        available = handler_check.get("available_instruments")
        selected = handler_check.get("selected_instrument", {})
        if isinstance(available, list) and available and selected:
            sel_type = selected.get("type")
            sel_brand = selected.get("brand")
            matched = False
            for rule in available:
                if rule.get("type") != sel_type:
                    continue
                allowed_brands = rule.get("brands")
                if allowed_brands and sel_brand not in allowed_brands:
                    continue
                matched = True
                break
            if not matched:
                violations.append("UCP_HANDLER_AVAILABLE_INSTRUMENTS_CONSTRAINT_VIOLATION")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def validate_acp_webhook_replay_and_error_enum_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate ACP #160 Merchant-Signature webhook replay protection and #161/#143 extensible DelegatePayment Error enums."""
    violations: list[str] = []

    webhook = payload.get("webhook_verification", {})
    if webhook:
        header = str(webhook.get("merchant_signature_header", ""))
        m = MERCHANT_SIG_RE.match(header)
        if not m:
            violations.append("ACP_WEBHOOK_SIGNATURE_HEADER_FORMAT_INVALID")
        else:
            ts = int(m.group(1))
            sig_hex = m.group(2).lower()
            now_ts = int(webhook.get("current_timestamp", 0))
            tolerance = int(webhook.get("tolerance_seconds", 300))
            if abs(now_ts - ts) > tolerance:
                violations.append("ACP_WEBHOOK_TIMESTAMP_OUTSIDE_REPLAY_WINDOW")
            secret = str(webhook.get("shared_secret", ""))
            raw_body = str(webhook.get("raw_body", ""))
            expected_sig = hmac.new(
                secret.encode("utf-8"),
                f"{ts}.{raw_body}".encode("utf-8"),
                hashlib.sha256,
            ).hexdigest().lower()
            if not hmac.compare_digest(sig_hex, expected_sig):
                violations.append("ACP_WEBHOOK_HMAC_SIGNATURE_MISMATCH")

    err_check = payload.get("delegate_payment_error_check", {})
    if err_check:
        http_status = int(err_check.get("http_status", 400))
        err_type = str(err_check.get("type", ""))
        err_code = str(err_check.get("code", ""))
        if http_status == 401 and (err_type != "unauthorized" or err_code != "unauthorized"):
            violations.append("ACP_DELEGATE_ERROR_401_UNAUTHORIZED_ALIGNMENT_REQUIRED")
        if http_status == 500 and (
            err_type != "internal_server_error" or err_code != "internal_server_error"
        ):
            violations.append("ACP_DELEGATE_ERROR_500_INTERNAL_ALIGNMENT_REQUIRED")
        if http_status == 503 and (
            err_type != "service_unavailable" or err_code != "service_unavailable"
        ):
            violations.append("ACP_DELEGATE_ERROR_503_UNAVAILABLE_ALIGNMENT_REQUIRED")
        if err_check.get("client_rejected_unrecognized_enum", False):
            violations.append("ACP_DELEGATE_ERROR_FORWARD_COMPAT_VIOLATED")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def _is_valid_printable_ascii(text: str, max_len: int) -> bool:
    if not text or len(text) > max_len:
        return False
    return all(0x20 <= ord(ch) <= 0x7E for ch in text)


def _is_safe_bazaar_icon_url(url: str) -> bool:
    if not url or len(url) > 2048 or any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in url):
        return False
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    if parts.scheme not in ("http", "https"):
        return False
    if parts.username is not None or parts.password is not None or "@" in parts.netloc:
        return False
    host = (parts.hostname or "").strip().lower().rstrip(".")
    if not host or host in LOOPBACK_ALIASES:
        return False
    if re.match(r"^(0x[0-9a-f]+|\d+)$", host):
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        pass
    return True


def validate_x402_eip3009_error_and_bazaar_metadata_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate Coinbase x402 #70 EIP-3009 error mapping and #156/#150 bazaar service-metadata sanitization."""
    violations: list[str] = []

    eip = payload.get("eip3009_diagnostic", {})
    if eip:
        stage = eip.get("phase")
        cause = eip.get("failure_cause")
        mapped_error = eip.get("mapped_error")
        if stage == "verify_simulation_rpc" and cause == "rpc_unavailable":
            if mapped_error != "ErrEip3009SimulationFailed":
                violations.append("X402_EIP3009_SIMULATION_RPC_MAPPED_TO_GENERIC_PAYLOAD_ERROR")
        elif stage == "settle_transfer" and cause in KNOWN_EIP3009_REVERT_MAP:
            expected_err = KNOWN_EIP3009_REVERT_MAP[cause]
            if mapped_error != expected_err:
                violations.append(f"X402_EIP3009_SETTLE_REVERT_UNMAPPED:{cause}")

    bazaar = payload.get("bazaar_service_metadata", {})
    if bazaar:
        svc_name = str(bazaar.get("serviceName", ""))
        if not _is_valid_printable_ascii(svc_name, 32):
            violations.append("X402_BAZAAR_SERVICE_NAME_INVALID")
        tags = bazaar.get("tags", [])
        if not isinstance(tags, list) or len(tags) > 5:
            violations.append("X402_BAZAAR_TAGS_COUNT_EXCEEDED")
        else:
            seen_lower: set[str] = set()
            for tag in tags:
                t_str = str(tag)
                if not _is_valid_printable_ascii(t_str, 32):
                    violations.append(f"X402_BAZAAR_TAG_INVALID:{t_str}")
                low = t_str.lower()
                if low in seen_lower:
                    violations.append(f"X402_BAZAAR_TAG_DUPLICATE_NOT_DEDUPED:{t_str}")
                seen_lower.add(low)
        icon_url = str(bazaar.get("iconUrl", ""))
        if not _is_safe_bazaar_icon_url(icon_url):
            violations.append("X402_BAZAAR_ICON_URL_UNSAFE_OR_INVALID")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }


def validate_tau2_closure_reason_passk_and_coercion_guard(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate Sierra tau2-bench #484 bank closure enum, #498 all-infra pass^k denominator, #516 Pydantic kwarg coercion, and #520 retry safety."""
    violations: list[str] = []

    closure = payload.get("bank_account_closure", {})
    if closure:
        reason = str(closure.get("reason", "customer_request"))
        if reason not in VALID_BANK_CLOSURE_REASONS:
            violations.append("TAU2_BANK_CLOSURE_REASON_NOT_IN_CANONICAL_SET")

    passk = payload.get("pass_hat_k_metrics", {})
    if passk:
        if not passk.get("compared_by_enum_value", True):
            violations.append("TAU2_INFRA_FILTER_PANDAS3_ENUM_VALUE_MISMATCH")
        configured_tasks = int(passk.get("configured_total_tasks", 0))
        reported_tasks = int(passk.get("reported_total_tasks", 0))
        if configured_tasks != reported_tasks:
            violations.append("TAU2_ALL_INFRA_ERROR_TASK_DROPPED_FROM_DENOMINATOR")
        expected_pass1 = float(passk.get("expected_pass_hat_1", 0.0))
        reported_pass1 = float(passk.get("reported_pass_hat_1", 0.0))
        if abs(expected_pass1 - reported_pass1) > 1e-6:
            violations.append("TAU2_PASS_HAT_K_INFLATED_BY_INFRA_EXCLUSION")

    coercion = payload.get("tool_kwarg_coercion", {})
    if coercion:
        if coercion.get("schema_type") == "integer" and isinstance(
            coercion.get("persisted_db_value"), float
        ):
            violations.append("TAU2_UNCOERCED_FLOAT_PERSISTED_IN_INTEGER_FIELD")

    retry = payload.get("hallucination_retry_audit", {})
    if retry:
        if not retry.get("final_retry_reviewed", True) or not retry.get(
            "checkpointed_selected_only", True
        ):
            violations.append("TAU2_HALLUCINATION_RETRY_UNSAFE_CHECKPOINT")

    return {
        "allowed": len(violations) == 0,
        "violations": violations,
    }
