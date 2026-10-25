"""Stage 232 deterministic guard module (880-Test Milestone).

Covers 42 primary-source PRs across x402 Foundation (#3925, #3927, #3827, #3271,
#3926), Universal Commerce Protocol (#679, #783, python-sdk#102/#101/#100/#96,
conformance#117/#89/#115/#112), and Model Context Protocol Spec & SDKs
(SEP-2778 #2778, python-sdk#3754/#3753/#3750, typescript-sdk#3076/#3079/#3024/
#3003/#3062/#3034, go-sdk#1411/#1443/#1441/#1442/#1438, rust-sdk#1197/#1282/
#1392/#1363/#1328/#1390, and csharp-sdk#1952/#1949/#1953/#1895/#1934/#1929).
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Any, Mapping, Sequence
from urllib.parse import unquote_to_bytes


@dataclass(frozen=True)
class GuardEvaluation:
    """Deterministic result from a Stage 232 guard evaluator."""

    allowed: bool
    decision_code: str
    remediation: str
    details: dict[str, Any]


_ALGOVOI_SUPPORTED_CHAINS = frozenset({
    "algorand",
    "base",
    "solana",
    "stellar",
    "hedera",
    "voi",
    "tempo",
})
_UCP_MEDIA_VARIANT_MODULES = frozenset({
    "media",
    "media_image",
    "media_video",
    "media_external_video",
    "media_3d",
})
_UCP_CALLER_OMIT_CHECKOUT_MEMBERS = frozenset({
    "continue_url",
    "expires_at",
    "messages",
    "order",
})
_DANGEROUS_URI_SCHEMES = ("javascript:", "data:", "vbscript:", "file:////")
_PROMPT_INJECTION_PATTERNS = (
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"<\s*system\s*>", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+in\s+developer\s+mode", re.IGNORECASE),
)
_WINDOWS_DRIVE_URI_RE = re.compile(r"^file:///(?P<drive>[A-Za-z])(?::|%3[Aa])/(?P<rest>.*)$")
_INT64_MIN = -(1 << 63)
_INT64_MAX = (1 << 63) - 1


def evaluate_x402_evm_exact_amount_and_trustscore_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    """PR-01: x402-foundation/x402#3925 & #3927."""
    required_amount = int(payload.get("required_amount", -1))
    eip3009_value = int(payload.get("eip3009_authorization_value", -1))
    permit2_amount = int(payload.get("permit2_permitted_amount", -1))
    now_epoch = int(payload.get("now_epoch", 0))
    valid_after = int(payload.get("valid_after", 0))
    valid_before = int(payload.get("valid_before", 0))
    selected_pay_to = str(payload.get("selected_pay_to", "")).lower()
    observed_endpoint_pay_to = str(payload.get("observed_endpoint_pay_to", "")).lower()
    trustscore = int(payload.get("trustscore", 0))
    min_trustscore = int(payload.get("min_trustscore", 70))

    if required_amount <= 0 or eip3009_value != required_amount:
        return GuardEvaluation(
            allowed=False,
            decision_code="invalid_exact_evm_payload_authorization_value_mismatch",
            remediation="Enforce exact equality authorization.value == required_amount per x402#3925.",
            details={"required_amount": required_amount, "eip3009_value": eip3009_value},
        )
    if permit2_amount != required_amount:
        return GuardEvaluation(
            allowed=False,
            decision_code="invalid_exact_evm_permit2_permitted_amount_mismatch",
            remediation="Enforce exact equality permit2Authorization.permitted.amount == required_amount.",
            details={"required_amount": required_amount, "permit2_amount": permit2_amount},
        )
    if not (valid_after <= now_epoch < valid_before):
        return GuardEvaluation(
            allowed=False,
            decision_code="invalid_exact_evm_payload_authorization_validity_window",
            remediation="Ensure validAfter <= now < validBefore before verifying or settling EIP-3009.",
            details={"valid_after": valid_after, "now_epoch": now_epoch, "valid_before": valid_before},
        )
    if not selected_pay_to or selected_pay_to != observed_endpoint_pay_to or trustscore < min_trustscore:
        return GuardEvaluation(
            allowed=False,
            decision_code="TRUSTSCORE_ENDPOINT_PAYEE_MISMATCH",
            remediation="Abort pre-signature when selected payTo diverges from TrustScore endpoint registry.",
            details={
                "selected_pay_to": selected_pay_to,
                "observed_endpoint_pay_to": observed_endpoint_pay_to,
                "trustscore": trustscore,
            },
        )
    return GuardEvaluation(
        allowed=True,
        decision_code="X402_EVM_EXACT_AMOUNT_AND_TRUSTSCORE_VERIFIED",
        remediation="None",
        details={"required_amount": required_amount, "trustscore": trustscore},
    )


def evaluate_x402_offer_receipt_v2_commitment_and_algovoi_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    """PR-02: x402-foundation/x402#3827 & #3271."""
    receipt_version = int(payload.get("receipt_version", 0))
    auth_method = str(payload.get("authorization_method", ""))
    signed_payload_fields = set(payload.get("signed_payload_fields", ()))
    salt_hex = str(payload.get("authorization_salt_hex", ""))
    salt_from_csprng = bool(payload.get("salt_from_csprng", False))
    asset = str(payload.get("asset", "")).lower()
    authorizer = str(payload.get("authorizer", "")).lower()
    nonce = str(payload.get("nonce", "")).lower()
    provided_commitment = str(payload.get("authorization_commitment", ""))
    algovoi_chain = str(payload.get("algovoi_chain", "")).lower()

    if receipt_version != 2 or auth_method != "eip3009":
        return GuardEvaluation(
            allowed=False,
            decision_code="X402_OFFER_RECEIPT_V2_VERSION_OR_METHOD_INVALID",
            remediation="Use receipt payload version 2 with authorizationMethod='eip3009'.",
            details={"receipt_version": receipt_version, "authorization_method": auth_method},
        )
    if "authorizationSalt" in signed_payload_fields or not salt_from_csprng or len(salt_hex) != 64:
        return GuardEvaluation(
            allowed=False,
            decision_code="X402_OFFER_RECEIPT_V2_SALT_RULE_VIOLATION",
            remediation="Return 32-byte CSPRNG authorizationSalt unsigned outside the signed receipt payload.",
            details={"salt_len_hex": len(salt_hex), "in_signed_payload": "authorizationSalt" in signed_payload_fields},
        )
    expected_commitment = "0x" + hashlib.sha256(
        f"x402-offer-receipt-v2|{auth_method}|{asset}|{authorizer}|{nonce}|{salt_hex.lower()}".encode("utf-8")
    ).hexdigest()
    if provided_commitment != expected_commitment:
        return GuardEvaluation(
            allowed=False,
            decision_code="X402_OFFER_RECEIPT_V2_COMMITMENT_MISMATCH",
            remediation="Recompute domain-tagged salted commitment over (asset, authorizer, nonce, salt).",
            details={"expected": expected_commitment, "provided": provided_commitment},
        )
    if algovoi_chain not in _ALGOVOI_SUPPORTED_CHAINS:
        return GuardEvaluation(
            allowed=False,
            decision_code="X402_ALGOVOI_UNSUPPORTED_CHAIN",
            remediation="Route AlgoVoi facilitator requests only to supported chains.",
            details={"algovoi_chain": algovoi_chain},
        )
    return GuardEvaluation(
        allowed=True,
        decision_code="X402_OFFER_RECEIPT_V2_AND_ALGOVOI_VERIFIED",
        remediation="None",
        details={"authorization_commitment": expected_commitment, "algovoi_chain": algovoi_chain},
    )


def evaluate_x402_neo_exact_scheme_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    """PR-03: x402-foundation/x402#3926."""
    network = str(payload.get("network", ""))
    nep17_transfer_count = int(payload.get("nep17_transfer_count", 0))
    has_nep21_context = bool(payload.get("has_nep21_contract_parameters_context", False))
    simulation_passed = bool(payload.get("simulation_passed", False))
    settlement_flow = str(payload.get("settlement_flow", ""))
    settlement_confirmed_before_resource = bool(payload.get("settlement_confirmed_before_resource", False))
    duplicate_tx_hash = bool(payload.get("duplicate_tx_hash", False))

    if not network.startswith("neo:") or nep17_transfer_count != 1 or not has_nep21_context:
        return GuardEvaluation(
            allowed=False,
            decision_code="X402_NEO_EXACT_PAYLOAD_STRUCTURE_INVALID",
            remediation="Require neo:* CAIP-2 network and exactly one NEP-17 transfer in NEP-21 context.",
            details={"network": network, "nep17_transfer_count": nep17_transfer_count},
        )
    if (
        not simulation_passed
        or settlement_flow != "upfront"
        or not settlement_confirmed_before_resource
        or duplicate_tx_hash
    ):
        return GuardEvaluation(
            allowed=False,
            decision_code="X402_NEO_EXACT_UPFRONT_SETTLEMENT_REQUIRED",
            remediation="Simulate NEP-17 tx, enforce upfront settlement before resource execution, and block replay.",
            details={
                "simulation_passed": simulation_passed,
                "settlement_flow": settlement_flow,
                "duplicate_tx_hash": duplicate_tx_hash,
            },
        )
    return GuardEvaluation(
        allowed=True,
        decision_code="X402_NEO_EXACT_SCHEME_VERIFIED",
        remediation="None",
        details={"network": network, "settlement_flow": settlement_flow},
    )


def evaluate_ucp_mcp_idempotency_and_idp_subject_token_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    """PR-04: Universal-Commerce-Protocol/ucp#679 & #783."""
    operation = str(payload.get("operation", ""))
    idempotency_key = str(payload.get("idempotency_key", ""))
    request_hash = str(payload.get("request_hash", ""))
    stored_hash = payload.get("stored_request_hash")
    subject_token_sub = str(payload.get("subject_token_sub", ""))
    jwt_grant_sub = str(payload.get("jwt_grant_sub", ""))
    token_scopes = set(payload.get("subject_token_scopes", ()))
    required_claims = set(payload.get("business_required_claims", ()))
    consent_model = str(payload.get("consent_model", ""))
    consent_business_id = str(payload.get("consent_business_id", ""))
    target_business_id = str(payload.get("target_business_id", ""))

    if operation in ("complete_checkout", "cancel_checkout") and not idempotency_key:
        return GuardEvaluation(
            allowed=False,
            decision_code="UCP_MCP_IDEMPOTENCY_KEY_MISSING",
            remediation="Provide meta['idempotency-key'] on complete_checkout and cancel_checkout.",
            details={"operation": operation},
        )
    if stored_hash is not None and str(stored_hash) != request_hash:
        return GuardEvaluation(
            allowed=False,
            decision_code="UCP_MCP_IDEMPOTENCY_CONFLICT_MINUS_32000",
            remediation="Reject mismatched idempotency-key reuse with JSON-RPC -32000 (HTTP 409 semantics).",
            details={"jsonrpc_code": -32000, "stored_hash": stored_hash, "request_hash": request_hash},
        )
    if (
        not subject_token_sub
        or subject_token_sub != jwt_grant_sub
        or not required_claims.issubset(token_scopes)
        or consent_model not in ("explicit_consent", "remembered_consent", "enterprise_policy")
        or consent_business_id != target_business_id
    ):
        return GuardEvaluation(
            allowed=False,
            decision_code="UCP_ACCELERATED_IDP_SUBJECT_TOKEN_OR_CONSENT_INVALID",
            remediation="Bind subject_token identity/scopes to required_claims and verify business-scoped consent.",
            details={
                "subject_token_sub": subject_token_sub,
                "jwt_grant_sub": jwt_grant_sub,
                "consent_model": consent_model,
            },
        )
    return GuardEvaluation(
        allowed=True,
        decision_code="UCP_MCP_IDEMPOTENCY_AND_IDP_SUBJECT_TOKEN_VERIFIED",
        remediation="None",
        details={"idempotency_key": idempotency_key, "consent_model": consent_model},
    )


def evaluate_ucp_python_sdk_codegen_and_dependent_required_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    """PR-05: Universal-Commerce-Protocol/python-sdk#102, #101, #100, & #96."""
    media_modules = set(payload.get("generated_media_modules", ()))
    uses_ucp_schema_generate_types = bool(payload.get("uses_ucp_schema_generate_types", False))
    datetime_field_has_regex_pattern = bool(payload.get("datetime_field_has_regex_pattern", False))
    interval_fields_set = set(payload.get("time_interval_fields_set", ()))
    is_projected_single_side = bool(payload.get("is_projected_single_side", False))

    if not _UCP_MEDIA_VARIANT_MODULES.issubset(media_modules) or not uses_ucp_schema_generate_types:
        return GuardEvaluation(
            allowed=False,
            decision_code="UCP_PYTHON_SDK_MEDIA_OR_CODEGEN_DRIFT",
            remediation="Compile models with ucp-schema generate-types including all 5 media variant modules.",
            details={"media_modules": sorted(media_modules)},
        )
    if datetime_field_has_regex_pattern:
        return GuardEvaluation(
            allowed=False,
            decision_code="UCP_PYTHON_SDK_DATETIME_REGEX_TYPEERROR_RISK",
            remediation="Strip regex pattern constraints from generated datetime fields per python-sdk#100.",
            details={"datetime_field_has_regex_pattern": True},
        )
    if not is_projected_single_side and ("opens" in interval_fields_set) != ("closes" in interval_fields_set):
        return GuardEvaluation(
            allowed=False,
            decision_code="UCP_PYTHON_SDK_DEPENDENT_REQUIRED_VIOLATION",
            remediation="Enforce dependentRequired so TimeInterval/ExceptionHour require opens and closes together.",
            details={"time_interval_fields_set": sorted(interval_fields_set)},
        )
    return GuardEvaluation(
        allowed=True,
        decision_code="UCP_PYTHON_SDK_CODEGEN_AND_DEPENDENT_REQUIRED_VERIFIED",
        remediation="None",
        details={"media_variant_count": len(media_modules)},
    )


def evaluate_ucp_conformance_lifecycle_terms_ap2_omit_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    """PR-06: Universal-Commerce-Protocol/conformance#117, #89, #115, & #112."""
    pre_complete_status = str(payload.get("pre_complete_status", ""))
    outstanding_errors_or_actions = int(payload.get("outstanding_errors_or_actions", 0))
    terms_ids: Sequence[str] = tuple(payload.get("payment_terms_ids", ()))
    selected_term_id = str(payload.get("selected_term_id", ""))
    ap2_negotiated_in_profile = bool(payload.get("ap2_negotiated_in_profile", False))
    ap2_signing_alg = str(payload.get("ap2_signing_alg", ""))
    caller_create_fields = set(payload.get("caller_create_fields", ()))
    server_echoed_caller_omit_fields = bool(payload.get("server_echoed_caller_omit_fields", False))

    if outstanding_errors_or_actions == 0 and pre_complete_status != "ready_for_complete":
        return GuardEvaluation(
            allowed=False,
            decision_code="UCP_CONFORMANCE_READY_FOR_COMPLETE_REQUIRED",
            remediation="Transition checkout to ready_for_complete when nothing is outstanding (#117).",
            details={"pre_complete_status": pre_complete_status},
        )
    if not terms_ids or len(set(terms_ids)) != len(terms_ids) or selected_term_id not in terms_ids:
        return GuardEvaluation(
            allowed=False,
            decision_code="UCP_CONFORMANCE_PAYMENT_TERMS_INVARIANT_VIOLATION",
            remediation="Ensure terms[].id are unique and selected_term_id names an offered term (#89).",
            details={"terms_ids": list(terms_ids), "selected_term_id": selected_term_id},
        )
    if not ap2_negotiated_in_profile or ap2_signing_alg != "ES256":
        return GuardEvaluation(
            allowed=False,
            decision_code="UCP_CONFORMANCE_AP2_NOT_NEGOTIATED",
            remediation="Negotiate AP2 in /profiles/shopping-agent-ap2.json with P-256 (ES256) key (#115).",
            details={"ap2_negotiated_in_profile": ap2_negotiated_in_profile, "ap2_signing_alg": ap2_signing_alg},
        )
    if (caller_create_fields & _UCP_CALLER_OMIT_CHECKOUT_MEMBERS) and server_echoed_caller_omit_fields:
        return GuardEvaluation(
            allowed=False,
            decision_code="UCP_CONFORMANCE_CALLER_OMIT_MEMBER_ACCEPTED",
            remediation="Never spread caller-supplied continue_url/expires_at/messages/order into response (#112).",
            details={"forbidden_fields": sorted(caller_create_fields & _UCP_CALLER_OMIT_CHECKOUT_MEMBERS)},
        )
    return GuardEvaluation(
        allowed=True,
        decision_code="UCP_CONFORMANCE_SUITE_INVARIANTS_VERIFIED",
        remediation="None",
        details={"pre_complete_status": pre_complete_status, "selected_term_id": selected_term_id},
    )


def evaluate_mcp_sep2778_type_constraints_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    """PR-07: modelcontextprotocol/modelcontextprotocol#2778 (SEP-2778)."""
    uri_value = str(payload.get("uri", "")).strip()
    tool_name = str(payload.get("tool_name", ""))
    cursor_value = str(payload.get("cursor", ""))
    max_string_bytes = int(payload.get("max_string_bytes", 4096))

    lower_uri = uri_value.lower()
    if not uri_value or any(lower_uri.startswith(scheme) for scheme in _DANGEROUS_URI_SCHEMES):
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_SEP2778_URI_SCHEME_REJECTED",
            remediation="Reject dangerous URI schemes (javascript:, data:, vbscript:) per SEP-2778.",
            details={"uri": uri_value},
        )
    if not re.fullmatch(r"[A-Za-z0-9_.\-]{1,64}", tool_name):
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_SEP2778_IDENTIFIER_CONSTRAINT_VIOLATION",
            remediation="Restrict MCP tool/prompt identifiers to 1..64 safe ASCII characters.",
            details={"tool_name": tool_name},
        )
    if any(ord(ch) < 0x20 for ch in cursor_value) or len(cursor_value.encode("utf-8")) > max_string_bytes:
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_SEP2778_CURSOR_OR_LENGTH_VIOLATION",
            remediation="Reject control characters and oversized strings per SEP-2778 constraints.",
            details={"cursor_len": len(cursor_value)},
        )
    return GuardEvaluation(
        allowed=True,
        decision_code="MCP_SEP2778_TYPE_CONSTRAINTS_VERIFIED",
        remediation="None",
        details={"tool_name": tool_name, "uri": uri_value},
    )


def evaluate_mcp_python_sdk_rugpull_progress_utf8_uri_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    """PR-08: modelcontextprotocol/python-sdk#3754, #3753, & #3750."""
    initial_desc = str(payload.get("initial_tool_description", ""))
    refetched_desc = str(payload.get("refetched_tool_description", ""))
    dns_rebinding_enabled = bool(payload.get("enable_dns_rebinding_protection", False))
    windows_probe_shell_true = bool(payload.get("windows_probe_shell_true", False))
    progress_callbacks_drained_before_return = bool(payload.get("progress_callbacks_drained_before_return", False))
    progress_serialized = bool(payload.get("progress_callbacks_serialized", False))
    uri_candidate = str(payload.get("uri_candidate", ""))

    for pattern in _PROMPT_INJECTION_PATTERNS:
        if pattern.search(initial_desc) or pattern.search(refetched_desc):
            return GuardEvaluation(
                allowed=False,
                decision_code="MCP_PY_TOOL_DESCRIPTION_INJECTION_DROPPED",
                remediation="Drop tools whose description matches prompt-injection patterns (#3754 CWE-20).",
                details={"description": refetched_desc or initial_desc},
            )
    initial_pin = hashlib.sha256(initial_desc.encode("utf-8")).hexdigest()
    refetched_pin = hashlib.sha256(refetched_desc.encode("utf-8")).hexdigest()
    if initial_pin != refetched_pin:
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_PY_TOOL_DESCRIPTION_RUGPULL_BLOCKED",
            remediation="Pin SHA-256 of tool description on first sight and drop mutated re-fetches (#3754 CWE-345).",
            details={"initial_sha256": initial_pin, "refetched_sha256": refetched_pin},
        )
    if not dns_rebinding_enabled or windows_probe_shell_true:
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_PY_DNS_REBINDING_OR_SHELL_TRUE_UNSAFE",
            remediation="Default enable_dns_rebinding_protection=True and shell=False on Windows probe (#3754).",
            details={"dns_rebinding_enabled": dns_rebinding_enabled, "shell_true": windows_probe_shell_true},
        )
    if not progress_serialized or not progress_callbacks_drained_before_return:
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_PY_PROGRESS_CALLBACK_RACE_DETECTED",
            remediation="Serialize progress callbacks and drain them before call_tool() returns (#3753).",
            details={"serialized": progress_serialized, "drained": progress_callbacks_drained_before_return},
        )
    try:
        unquote_to_bytes(uri_candidate).decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_PY_NON_UTF8_PERCENT_ESCAPE_URI_UNMATCHED",
            remediation="Do not match URIs containing non-UTF-8 percent-escapes in UriTemplate.match() (#3750).",
            details={"uri_candidate": uri_candidate},
        )
    return GuardEvaluation(
        allowed=True,
        decision_code="MCP_PY_SECURITY_PROGRESS_AND_URI_VERIFIED",
        remediation="None",
        details={"description_sha256": initial_pin},
    )


def evaluate_mcp_ts_sdk_listchanged_handshake_admission_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    """PR-09: modelcontextprotocol/typescript-sdk#3076, #3079, & #3024."""
    configured_list_changed = payload.get("configured_tools_list_changed")
    effective_list_changed = payload.get("effective_tools_list_changed")
    initialized_has_own_timeout = bool(payload.get("initialized_has_own_timeout", False))
    transport_closed_on_handshake_abort = bool(payload.get("transport_closed_on_handshake_abort", False))
    handler_and_writes_completed = bool(payload.get("handler_and_writes_completed", False))
    sdk_cleanup_completed = bool(payload.get("sdk_cleanup_completed", False))
    credit_reclaimed = bool(payload.get("admission_credit_reclaimed", False))

    if configured_list_changed is False and effective_list_changed is not False:
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_TS_USER_LISTCHANGED_FALSE_OVERWRITTEN",
            remediation="Preserve user-configured capabilities.tools.listChanged=false (#3076).",
            details={"configured": configured_list_changed, "effective": effective_list_changed},
        )
    if not initialized_has_own_timeout or not transport_closed_on_handshake_abort:
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_TS_INITIALIZED_HANDSHAKE_TIMEOUT_UNBOUNDED",
            remediation="Bound notifications/initialized with its own timeout and close transport on abort (#3079).",
            details={"initialized_has_own_timeout": initialized_has_own_timeout},
        )
    if credit_reclaimed and (not handler_and_writes_completed or not sdk_cleanup_completed):
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_TS_PREMATURE_ADMISSION_CREDIT_RECLAIM",
            remediation="Await handler, response writes, and SDK cleanup before onMessageProcessed (#3024).",
            details={
                "handler_and_writes_completed": handler_and_writes_completed,
                "sdk_cleanup_completed": sdk_cleanup_completed,
            },
        )
    return GuardEvaluation(
        allowed=True,
        decision_code="MCP_TS_LISTCHANGED_HANDSHAKE_ADMISSION_VERIFIED",
        remediation="None",
        details={"effective_list_changed": effective_list_changed},
    )


def evaluate_mcp_ts_sdk_rfc6570_rfc9728_rfc8414_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    """PR-10: modelcontextprotocol/typescript-sdk#3003, #3062, & #3034."""
    var_spec = str(payload.get("var_spec", "name:3"))
    input_value = str(payload.get("input_value", "abcdef"))
    expanded_value = str(payload.get("expanded_value", ""))
    resource_url = str(payload.get("resource_url", ""))
    well_known_url = str(payload.get("well_known_url", ""))
    grant_type = str(payload.get("grant_type", ""))
    has_authorization_endpoint = bool(payload.get("has_authorization_endpoint", False))

    var_name, _, prefix_str = var_spec.partition(":")
    prefix_len = int(prefix_str) if prefix_str.isdigit() else len(input_value)
    if expanded_value != input_value[:prefix_len] or not var_name:
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_TS_RFC6570_PREFIX_MODIFIER_BROKEN",
            remediation="Parse :N prefix modifiers separately from variable names in UriTemplate (#3003).",
            details={"var_spec": var_spec, "expected": input_value[:prefix_len], "expanded": expanded_value},
        )
    if resource_url.endswith("/resource/") and not well_known_url.endswith(
        "/.well-known/oauth-protected-resource/resource/"
    ):
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_TS_RFC9728_PATH_TRAILING_SLASH_STRIPPED",
            remediation="Preserve trailing slash on path components in OAuth Protected Resource metadata URL (#3062).",
            details={"resource_url": resource_url, "well_known_url": well_known_url},
        )
    if grant_type == "authorization_code" and not has_authorization_endpoint:
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_TS_AUTH_CODE_MISSING_AUTHORIZATION_ENDPOINT",
            remediation="Allow omitting authorization_endpoint for client_credentials, but require it for auth-code (#3034).",
            details={"grant_type": grant_type},
        )
    return GuardEvaluation(
        allowed=True,
        decision_code="MCP_TS_RFC6570_RFC9728_RFC8414_VERIFIED",
        remediation="None",
        details={"clean_variable": var_name, "expanded_value": expanded_value, "grant_type": grant_type},
    )


def evaluate_mcp_go_sdk_queue_windows_root_jsonrpc_id_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    """PR-11: modelcontextprotocol/go-sdk#1411, #1443, & #1441."""
    preceding_notifications_handled = bool(payload.get("preceding_notifications_handled_before_response", False))
    windows_file_uri = str(payload.get("windows_file_uri", ""))
    raw_jsonrpc_id = payload.get("raw_jsonrpc_id")

    if not preceding_notifications_handled:
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_GO_RESPONSE_RETIRED_BEFORE_NOTIFICATIONS",
            remediation="Deliver *Response through handlerQueue so preceding notifications finish first (#1411).",
            details={"preceding_notifications_handled": False},
        )
    match = _WINDOWS_DRIVE_URI_RE.match(windows_file_uri)
    if not match or ".." in match.group("rest").split("/"):
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_GO_WINDOWS_FILE_ROOT_INVALID",
            remediation="Accept RFC 8089 file:///C:/... drive-letter roots and reject '..' traversal (#1443).",
            details={"windows_file_uri": windows_file_uri},
        )
    if (
        isinstance(raw_jsonrpc_id, bool)
        or not isinstance(raw_jsonrpc_id, int)
        or not (_INT64_MIN <= raw_jsonrpc_id <= _INT64_MAX)
    ):
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_GO_NON_INTEGER_OR_OUT_OF_RANGE_JSONRPC_ID",
            remediation="Reject fractional or out-of-int64-range numeric JSON-RPC IDs (#1441).",
            details={"raw_jsonrpc_id": raw_jsonrpc_id},
        )
    win_path = f"{match.group('drive').upper()}:\\" + match.group("rest").replace("/", "\\")
    return GuardEvaluation(
        allowed=True,
        decision_code="MCP_GO_QUEUE_WINDOWS_ROOT_AND_ID_VERIFIED",
        remediation="None",
        details={"windows_path": win_path, "jsonrpc_id": raw_jsonrpc_id},
    )


def evaluate_mcp_go_sdk_extauth_iss_and_id_jag_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    """PR-12: modelcontextprotocol/go-sdk#1442 & #1438."""
    iss_supported = bool(payload.get("authorization_response_iss_parameter_supported", False))
    response_iss = payload.get("response_iss")
    metadata_issuer = str(payload.get("metadata_issuer", ""))
    issued_token_type = str(payload.get("issued_token_type", ""))

    if iss_supported and not response_iss:
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_GO_EXTAUTH_MISSING_REQUIRED_ISS",
            remediation="Require authorization response iss when advertised by IdP metadata (#1442).",
            details={"metadata_issuer": metadata_issuer},
        )
    if response_iss is not None and str(response_iss) != metadata_issuer:
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_GO_EXTAUTH_ISS_MISMATCH",
            remediation="Verify present authorization response iss equals IdP metadata issuer per RFC 9207 (#1442).",
            details={"response_iss": response_iss, "metadata_issuer": metadata_issuer},
        )
    if issued_token_type != "urn:ietf:params:oauth:token-type:id-jag":
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_GO_EXTAUTH_NON_ID_JAG_TOKEN_REJECTED",
            remediation="Only forward exchanged tokens with issued_token_type == urn:ietf:params:oauth:token-type:id-jag (#1438).",
            details={"issued_token_type": issued_token_type},
        )
    return GuardEvaluation(
        allowed=True,
        decision_code="MCP_GO_EXTAUTH_ISS_AND_ID_JAG_VERIFIED",
        remediation="None",
        details={"metadata_issuer": metadata_issuer, "issued_token_type": issued_token_type},
    )


def evaluate_mcp_rust_sdk_custom_result_origin_port_skills_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    """PR-13: modelcontextprotocol/rust-sdk#1197, #1282, & #1392."""
    response_keys = set(payload.get("response_keys", ()))
    decoded_variant = str(payload.get("decoded_variant", ""))
    incoming_origin = str(payload.get("incoming_origin", ""))
    allowlist_entry = str(payload.get("allowlist_entry", ""))
    skill_method = str(payload.get("skill_method", ""))

    tool_keys = {"content", "structuredContent", "isError"}
    has_tool_key = bool(response_keys & tool_keys)
    custom_keys = response_keys - {"_meta", "resultType"} - tool_keys
    expected_variant = "CustomResult" if ("_meta" in response_keys and custom_keys and not has_tool_key) else "CallToolResult"
    if decoded_variant != expected_variant:
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_RUST_CUSTOM_RESULT_META_DECODE_MISMATCH",
            remediation="Decode _meta + custom fields without tool fields as CustomResult (#1197).",
            details={"expected_variant": expected_variant, "decoded_variant": decoded_variant},
        )
    normalized_origin = (
        f"{incoming_origin}:443"
        if incoming_origin.startswith("https://") and incoming_origin.count(":") == 1
        else (
            f"{incoming_origin}:80"
            if incoming_origin.startswith("http://") and incoming_origin.count(":") == 1
            else incoming_origin
        )
    )
    if normalized_origin != allowlist_entry:
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_RUST_ORIGIN_DEFAULT_PORT_MISMATCH",
            remediation="Resolve omitted RFC 6454 default port before comparing Origin against allowlist (#1282).",
            details={"incoming_origin": incoming_origin, "allowlist_entry": allowlist_entry},
        )
    if skill_method not in ("skills/list", "skills/get", "resources/directory/read"):
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_RUST_SEP2640_SKILL_METHOD_UNSUPPORTED",
            remediation="Use SEP-2640 io.modelcontextprotocol/skills methods (#1392).",
            details={"skill_method": skill_method},
        )
    return GuardEvaluation(
        allowed=True,
        decision_code="MCP_RUST_CUSTOM_RESULT_ORIGIN_AND_SKILLS_VERIFIED",
        remediation="None",
        details={"decoded_variant": decoded_variant, "normalized_origin": normalized_origin},
    )


def evaluate_mcp_rust_sdk_sse_terminal_cancel_media_type_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    """PR-14: modelcontextprotocol/rust-sdk#1363, #1328, & #1390."""
    sse_get_status = int(payload.get("sse_get_status", 200))
    will_reconnect = bool(payload.get("will_reconnect", False))
    replayed_interrupted_post = bool(payload.get("replayed_interrupted_post", False))
    client_disconnected_mid_stream = bool(payload.get("client_disconnected_mid_stream", False))
    sent_cancelled_notification = bool(payload.get("sent_cancelled_notification", False))
    content_type = str(payload.get("content_type", ""))

    if sse_get_status in (401, 403, 405) and will_reconnect:
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_RUST_SSE_TERMINAL_GET_INFINITE_RECONNECT",
            remediation="Stop SSE GET reconnects on terminal 401/403/405 errors (#1363).",
            details={"sse_get_status": sse_get_status},
        )
    if replayed_interrupted_post:
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_RUST_INTERRUPTED_POST_REPLAY_FORBIDDEN",
            remediation="Fail interrupted POST requests without replaying them (#1363).",
            details={"replayed_interrupted_post": True},
        )
    if client_disconnected_mid_stream and not sent_cancelled_notification:
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_RUST_DISCONNECT_CANCELLATION_MISSING",
            remediation="Send notifications/cancelled via drop guard when SSE client disconnects (#1328).",
            details={"client_disconnected_mid_stream": True},
        )
    essence = content_type.split(";", 1)[0].strip().lower()
    if "," in content_type or essence not in ("application/json", "text/event-stream"):
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_RUST_MEDIA_TYPE_ESSENCE_INVALID",
            remediation="Match full response media-type essence case-insensitively and reject suffixes/commas (#1390).",
            details={"content_type": content_type, "essence": essence},
        )
    return GuardEvaluation(
        allowed=True,
        decision_code="MCP_RUST_SSE_CANCEL_AND_MEDIA_TYPE_VERIFIED",
        remediation="None",
        details={"essence": essence, "sse_get_status": sse_get_status},
    )


def evaluate_mcp_csharp_sdk_oauth_fallback_pkce_resource_indicator_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    """PR-15: modelcontextprotocol/csharp-sdk#1952, #1949, & #1953."""
    has_protected_resource_metadata = bool(payload.get("has_protected_resource_metadata", False))
    has_auth_server_metadata = bool(payload.get("has_auth_server_metadata", False))
    legacy_fallback_opt_in = bool(payload.get("legacy_fallback_opt_in", False))
    pkce_s256_supported = bool(payload.get("pkce_s256_supported", False))
    issuer_matches = bool(payload.get("issuer_matches", False))
    server_resource_indicators_supported = payload.get("resource_indicators_supported", True)
    client_sent_resource_param = bool(payload.get("client_sent_resource_param", True))

    if not has_protected_resource_metadata and not has_auth_server_metadata and not legacy_fallback_opt_in:
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_CSHARP_SYNTHETIC_OAUTH_FALLBACK_DISABLED",
            remediation="Reject missing OAuth metadata unless legacy fallback is explicitly opted into (#1952).",
            details={"legacy_fallback_opt_in": False},
        )
    if (has_auth_server_metadata or has_protected_resource_metadata) and (not pkce_s256_supported or not issuer_matches):
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_CSHARP_PKCE_OR_ISSUER_VALIDATION_FAILED",
            remediation="Validate OAuth PKCE S256 support and RFC 8414 metadata issuer (#1949).",
            details={"pkce_s256_supported": pkce_s256_supported, "issuer_matches": issuer_matches},
        )
    if server_resource_indicators_supported is True and not client_sent_resource_param:
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_CSHARP_UNILATERAL_RESOURCE_INDICATOR_OMISSION",
            remediation="Only omit RFC 8707 resource parameter when server advertises resource_indicators_supported=false (#1953).",
            details={"resource_indicators_supported": True, "client_sent_resource_param": False},
        )
    if server_resource_indicators_supported is False and client_sent_resource_param:
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_CSHARP_ENTRA_RESOURCE_INDICATOR_REJECTED",
            remediation="Omit RFC 8707 resource parameter when server sets resource_indicators_supported=false (#1953).",
            details={"resource_indicators_supported": False, "client_sent_resource_param": True},
        )
    return GuardEvaluation(
        allowed=True,
        decision_code="MCP_CSHARP_OAUTH_PKCE_AND_RESOURCE_INDICATOR_VERIFIED",
        remediation="None",
        details={"resource_indicators_supported": server_resource_indicators_supported},
    )


def evaluate_mcp_csharp_sdk_process_tree_case_sensitive_null_schema_guard(
    payload: Mapping[str, Any],
) -> GuardEvaluation:
    """PR-16: modelcontextprotocol/csharp-sdk#1895, #1934, & #1929."""
    descendant_pids_running_after_dispose = int(payload.get("descendant_pids_running_after_dispose", 0))
    json_property_keys = set(payload.get("json_property_keys", ()))
    required_nullable_keys = set(payload.get("required_nullable_keys", ()))
    serialized_structured_keys = set(payload.get("serialized_structured_keys", ()))

    if descendant_pids_running_after_dispose > 0:
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_CSHARP_STDIO_DESCENDANT_PROCESS_LEAK",
            remediation="Wait for the entire server process tree (including descendants) on stdio DisposeAsync (#1895).",
            details={"descendant_pids_running_after_dispose": descendant_pids_running_after_dispose},
        )
    if any(k in json_property_keys for k in ("Name", "Code", "IsError", "Arguments")):
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_CSHARP_CASE_INSENSITIVE_PROPERTY_REJECTED",
            remediation="Match MCP protocol property names case-sensitively (#1934).",
            details={"json_property_keys": sorted(json_property_keys)},
        )
    if not required_nullable_keys.issubset(serialized_structured_keys):
        return GuardEvaluation(
            allowed=False,
            decision_code="MCP_CSHARP_REQUIRED_NULL_PROPERTY_OMITTED",
            remediation="Preserve explicit nulls required by structured output schemas in structuredContent (#1929).",
            details={"missing_keys": sorted(required_nullable_keys - serialized_structured_keys)},
        )
    return GuardEvaluation(
        allowed=True,
        decision_code="MCP_CSHARP_PROCESS_TREE_CASE_AND_NULL_SCHEMA_VERIFIED",
        remediation="None",
        details={"serialized_structured_keys": sorted(serialized_structured_keys)},
    )
