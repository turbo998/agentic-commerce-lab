"""Stage 130 deterministic runtime guardrails.

Covers primary-source protocol & SDK controls audited on 2026-10-21:
1. x402 Foundation (#3698, #3697, #3696, #3691, #3690, #3687, #3683, #3682, #3681,
   #3676, #3674, #3671, #3668, #3664):
   - SVM batch `afterVerify` store fail-closed (#3697), distinct error on request ID
     reuse with changed ceiling (#3696), and server-signed channel refund recovery
     after restart (#3664).
   - Raw MCP `tools/call` exposure before SDK schema defaults (#3691), EVM payer
     `eth_getCode` failure reported as `invalid_exact_evm_failed_to_verify_signature`
     with single bytecode fetch (#3690), and Cardano raw signed CBOR submission without
     tag-258 re-serialization (#3674).
   - `hardware-attestation` TEE enclave verification (#3683), `execution-evidence`
     settlement-to-output binding (#3682), `refund` extension (#3681), EIP-712
     offer/receipt shape check (#3676), strict BOLT11 `lnbtc` decoding (#3698),
     Hono/Express `text/plain` error body preservation (#3687, #3668), and Python
     off-event-loop scheme payload creation (#3671).
2. Google UCP (#747, #746, #744, #740, #730, #725, #722, #716, #715, #713):
   - Normal Checkout/Cart/Order/Catalog resource responses constrained to
     `ucp.status == "success"` (#747) and vertical-agnostic token binding (#746).
   - Request Constraints outer-only `path` targeting (#744), Cart terminal status (#740),
     and `payment-actions` `action.ready` empty-object (`maxProperties: 0`) success
     branch (#730).
   - Validator schema cache key isolated by normalized `schema_base` (#722), OpenAPI
     `components.securitySchemes` (#716), Catalog `get_product`-only `discounts.available`
     previews (#715), and `dev.ucp.payment.shared_payment_token` (#713).
3. Stripe AI (#382, #379, #378, #377), MCP (#3306, #3304, #3285, #3279), & Sierra
   tau2-bench (#520, #516, #513, #511, #510, #508, #498, #484):
   - Stripe AI `clientName` CRLF/header-injection sanitization (#379), safe Buffer/chunked
     Base64 conversion (#382), upfront `/products` map (#378), and `/purchase` invoice
     payment persistence (#377).
   - MCP `-32023` `RateLimited` (#3304), Credential Destination Injection block (#3285),
     and negotiated tool result variants (#3279).
   - Sierra tau2-bench `pass^k` pandas 3.x string `.value` infra-error matching &
     denominator preservation (#498), Pydantic kwargs float->int coercion (#516),
     write-critic + parsed nested JSON argument comparison (#513), `llm_agent_solo_gt`
     solo-mode detection (#508), fixed `close_bank_account_7392` reason enum (#484), and
     Gemini 8kHz `START_SENSITIVITY_HIGH` + `SlidingWindow` (#511, #510).
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any


@dataclass(frozen=True)
class GuardResult:
    allowed: bool
    code: str
    detail: str
    metadata: dict[str, Any]


def evaluate_x402_svm_batch_mcp_raw_and_evm_cardano_guard(
    *,
    after_verify_store_failed: bool = False,
    request_refused_on_store_failure: bool = True,
    reused_batch_request_id: bool = False,
    new_ceiling_differs_from_original: bool = False,
    reported_error_code: str = "duplicate_request_id",
    server_signed_refund_after_restart_loaded_from_store: bool = True,
    mcp_bound_to_raw_tools_call_before_schema_defaults: bool = True,
    evm_payer_get_code_failed: bool = False,
    evm_reported_error: str = "invalid_exact_evm_failed_to_verify_signature",
    evm_get_code_call_count: int = 1,
    cardano_re_serialized_cbor_with_tag_258: bool = False,
) -> GuardResult:
    """Audit x402 #3697, #3696, #3664, #3691, #3690, and #3674."""
    if after_verify_store_failed and not request_refused_on_store_failure:
        return GuardResult(
            allowed=False,
            code="X402_SVM_BATCH_AFTER_VERIFY_STORE_FAILED_OPEN_BLOCKED",
            detail="SVM batch verify must fail closed when afterVerify operation-store call fails (#3697)",
            metadata={"after_verify_store_failed": True},
        )
    if reused_batch_request_id and new_ceiling_differs_from_original and reported_error_code == "transaction_failed":
        return GuardResult(
            allowed=False,
            code="X402_SVM_BATCH_CEILING_CHANGE_GENERIC_ERROR_BLOCKED",
            detail="Reused batch request ID with a new ceiling must report distinct ceiling-changed error, not generic transaction_failed (#3696)",
            metadata={"reported_error_code": reported_error_code},
        )
    if not server_signed_refund_after_restart_loaded_from_store:
        return GuardResult(
            allowed=False,
            code="X402_SVM_SERVER_SIGNED_REFUND_RESTART_LOST_BLOCKED",
            detail="locateRefundChannel must load persisted server-signed channel record after restart (#3664)",
            metadata={"server_signed_refund_after_restart_loaded_from_store": False},
        )
    if not mcp_bound_to_raw_tools_call_before_schema_defaults:
        return GuardResult(
            allowed=False,
            code="X402_MCP_POST_DEFAULT_SCHEMA_MUTATED_BINDING_BLOCKED",
            detail="Request-bound MCP payment schemes must bind raw tools/call before SDK schema defaults (#3691)",
            metadata={"mcp_bound_to_raw_tools_call_before_schema_defaults": False},
        )
    if evm_payer_get_code_failed and (
        evm_reported_error != "invalid_exact_evm_failed_to_verify_signature" or evm_get_code_call_count > 1
    ):
        return GuardResult(
            allowed=False,
            code="X402_EVM_GET_CODE_FAILURE_MISCLASSIFIED_OR_DUPLICATED_BLOCKED",
            detail="Failed payer eth_getCode must report invalid_exact_evm_failed_to_verify_signature with single bytecode fetch (#3690)",
            metadata={"evm_reported_error": evm_reported_error, "evm_get_code_call_count": evm_get_code_call_count},
        )
    if cardano_re_serialized_cbor_with_tag_258:
        return GuardResult(
            allowed=False,
            code="X402_CARDANO_SIGNED_CBOR_RESERIALIZED_TAG258_BLOCKED",
            detail="Cardano facilitator must broadcast client's signed CBOR bytes unchanged without re-serialization (#3674)",
            metadata={"cardano_re_serialized_cbor_with_tag_258": True},
        )
    return GuardResult(
        allowed=True,
        code="X402_SVM_BATCH_MCP_RAW_AND_EVM_CARDANO_VERIFIED",
        detail="x402 SVM batch store fail-closed, ceiling-change error, raw MCP tools/call, EVM getCode, and Cardano raw CBOR verified",
        metadata={"evm_get_code_call_count": evm_get_code_call_count},
    )


def evaluate_x402_enclave_evidence_refund_and_transport_guard(
    *,
    enclave_platform: str = "tdx",
    enclave_measurement_verified: bool = True,
    execution_evidence_bound_to_settled_tx_and_output: bool = True,
    refund_requested: bool = False,
    refund_signed_by_original_payer: bool = True,
    refund_amount_minor: int = 500,
    paid_amount_minor: int = 1000,
    already_refunded_minor: int = 200,
    refund_window_seconds: int = 3600,
    refund_idempotency_key: str = "idem_ref_01",
    refund_paid_by_facilitator_funds: bool = False,
    eip712_receipt_fields_present: tuple[str, ...] = ("payer", "version", "issuedAt", "network", "amount"),
    lnbtc_bolt11_strict_decoded: bool = True,
    text_plain_error_json_stringified: bool = False,
    python_client_scheme_ran_off_event_loop: bool = True,
) -> GuardResult:
    """Audit x402 #3683, #3682, #3681, #3676, #3698, #3687/#3668, and #3671."""
    if enclave_platform not in {"tdx", "sev-snp", "nitro", "cca"} or not enclave_measurement_verified:
        return GuardResult(
            allowed=False,
            code="X402_HARDWARE_ATTESTATION_ENCLAVE_INVALID_BLOCKED",
            detail="hardware-attestation requires verified measurement from tdx/sev-snp/nitro/cca enclave (#3683)",
            metadata={"enclave_platform": enclave_platform},
        )
    if not execution_evidence_bound_to_settled_tx_and_output:
        return GuardResult(
            allowed=False,
            code="X402_EXECUTION_EVIDENCE_UNBOUND_SETTLEMENT_BLOCKED",
            detail="execution-evidence must cryptographically bind settled tx to fulfilled output digest (#3682)",
            metadata={"execution_evidence_bound_to_settled_tx_and_output": False},
        )
    if refund_requested:
        if (
            not refund_signed_by_original_payer
            or refund_window_seconds <= 0
            or not refund_idempotency_key.strip()
            or refund_paid_by_facilitator_funds
            or refund_amount_minor > (paid_amount_minor - already_refunded_minor)
        ):
            return GuardResult(
                allowed=False,
                code="X402_REFUND_EXTENSION_POLICY_OR_OVERREFUND_BLOCKED",
                detail="x402 refund must be signed by original payer, within remaining paid balance & window, idempotent, and server-funded (#3681)",
                metadata={
                    "refund_amount_minor": refund_amount_minor,
                    "remaining_refundable": paid_amount_minor - already_refunded_minor,
                },
            )
    required_eip712 = {"payer", "version", "issuedAt", "network", "amount"}
    if not required_eip712.issubset(set(eip712_receipt_fields_present)):
        return GuardResult(
            allowed=False,
            code="X402_EIP712_RECEIPT_MISSING_FIELD_TYPEERROR_BLOCKED",
            detail="verifyReceiptSignatureEIP712 must reject missing fields with defined error before BigInt() (#3676)",
            metadata={"missing": sorted(required_eip712 - set(eip712_receipt_fields_present))},
        )
    if not lnbtc_bolt11_strict_decoded or text_plain_error_json_stringified or not python_client_scheme_ran_off_event_loop:
        return GuardResult(
            allowed=False,
            code="X402_BOLT11_TEXT_ERROR_OR_EVENT_LOOP_BLOCKING_VIOLATION",
            detail="lnbtc strict BOLT11 decoding (#3698), Hono/Express text/plain error body (#3687/#3668), or Python async off-loop (#3671) violated",
            metadata={"text_plain_error_json_stringified": text_plain_error_json_stringified},
        )
    return GuardResult(
        allowed=True,
        code="X402_ENCLAVE_EVIDENCE_REFUND_AND_TRANSPORT_VERIFIED",
        detail="x402 hardware-attestation, execution-evidence, refund extension, EIP-712 shape, BOLT11, and text/async guards verified",
        metadata={"enclave_platform": enclave_platform},
    )


def evaluate_ucp_status_binding_constraints_and_spt_guard(
    *,
    is_resource_response: bool = True,
    ucp_status: str = "success",
    non_shopping_token_binding_forced_checkout_id: bool = False,
    request_constraint_path_is_outer_only: bool = True,
    action_ready_success_payload: dict[str, Any] | None = None,
    schema_cache_key_includes_schema_base: bool = True,
    openapi_auth_uses_security_schemes: bool = True,
    catalog_operation: str = "get_product",
    response_includes_discounts_available: bool = True,
    spt_exposes_raw_pan_or_cvc: bool = False,
) -> GuardResult:
    """Audit UCP #747, #746, #744, #730, #722, #716, #715, and #713."""
    if is_resource_response and ucp_status != "success":
        return GuardResult(
            allowed=False,
            code="UCP_RESOURCE_RESPONSE_ERROR_STATUS_BLOCKED",
            detail="Normal Checkout/Cart/Order/Catalog resource responses must constrain ucp.status to 'success' (#747)",
            metadata={"ucp_status": ucp_status},
        )
    if non_shopping_token_binding_forced_checkout_id:
        return GuardResult(
            allowed=False,
            code="UCP_TOKEN_BINDING_SHOPPING_COUPLED_BLOCKED",
            detail="Token binding must be vertical-agnostic in common/types without fabricating checkout_id (#746)",
            metadata={"non_shopping_token_binding_forced_checkout_id": True},
        )
    if not request_constraint_path_is_outer_only:
        return GuardResult(
            allowed=False,
            code="UCP_REQUEST_CONSTRAINT_NESTED_PATH_BLOCKED",
            detail="Request Constraint `path` targeting must be outer-only (#744)",
            metadata={"request_constraint_path_is_outer_only": False},
        )
    ready_obj = {} if action_ready_success_payload is None else action_ready_success_payload
    if len(ready_obj) > 0:
        return GuardResult(
            allowed=False,
            code="UCP_ACTION_READY_NON_EMPTY_SUCCESS_OBJECT_BLOCKED",
            detail="payment-actions action.ready success branch requires maxProperties: 0 ({}) to disambiguate oneOf (#730)",
            metadata={"keys": list(ready_obj.keys())},
        )
    if not schema_cache_key_includes_schema_base or not openapi_auth_uses_security_schemes:
        return GuardResult(
            allowed=False,
            code="UCP_SCHEMA_CACHE_OR_OPENAPI_AUTH_HEADER_PARAM_BLOCKED",
            detail="Validator cache must include schema_base (#722) and REST OpenAPI must declare auth via securitySchemes (#716)",
            metadata={"schema_cache_key_includes_schema_base": schema_cache_key_includes_schema_base},
        )
    if response_includes_discounts_available and catalog_operation != "get_product":
        return GuardResult(
            allowed=False,
            code="UCP_CATALOG_DISCOUNT_PREVIEW_OUTSIDE_GET_PRODUCT_BLOCKED",
            detail="Catalog `discounts.available` previews are permitted only on `get_product` responses (#715)",
            metadata={"catalog_operation": catalog_operation},
        )
    if spt_exposes_raw_pan_or_cvc:
        return GuardResult(
            allowed=False,
            code="UCP_SHARED_PAYMENT_TOKEN_RAW_CREDENTIAL_LEAK_BLOCKED",
            detail="dev.ucp.payment.shared_payment_token must never expose raw PAN or CVC (#713)",
            metadata={"spt_exposes_raw_pan_or_cvc": True},
        )
    return GuardResult(
        allowed=True,
        code="UCP_STATUS_BINDING_CONSTRAINTS_AND_SPT_VERIFIED",
        detail="UCP resource status='success', vertical-agnostic binding, constraint path, action.ready {}, and SPT handler verified",
        metadata={"catalog_operation": catalog_operation},
    )


_VALID_CLOSE_ACCOUNT_REASONS = {
    "customer_request",
    "relocation",
    "dissatisfied_with_service",
    "switching_banks",
    "duplicate_account",
    "deceased_account_holder",
    "fraud_or_security_concern",
}


def evaluate_stripe_mcp_security_and_tau2_metrics_guard(
    *,
    client_name: str = "stripe-mcp-agent/1.0",
    used_spread_from_char_code_base64: bool = False,
    products_endpoint_uses_n_plus_1_stripe_calls: bool = False,
    credential_forwarded_to_untrusted_arg_host: bool = False,
    mcp_rate_limit_code: int = -32023,
    mcp_rate_limit_retry_after_seconds: int = 30,
    pass_k_compared_enum_str_directly_in_pandas3: bool = False,
    all_infra_error_tasks_kept_in_pass_k_denominator: bool = True,
    pydantic_coerced_float_kwargs_before_tool_call: bool = True,
    nested_json_tool_args_compared_as_parsed_json: bool = True,
    agent_implementation: str = "llm_agent_solo_gt",
    detected_as_solo_mode: bool = True,
    close_account_reason: str = "customer_request",
    gemini_8khz_start_sensitivity_high_and_sliding_window: bool = True,
) -> GuardResult:
    """Audit Stripe AI #379/#382/#378, MCP #3304/#3285, and Sierra tau2-bench #498/#516/#513/#508/#484/#511/#510."""
    if "\r" in client_name or "\n" in client_name or not re.match(r"^[A-Za-z0-9._/\-]+$", client_name):
        return GuardResult(
            allowed=False,
            code="STRIPE_USER_AGENT_CLIENT_NAME_HEADER_INJECTION_BLOCKED",
            detail="Unsanitized clientName in User-Agent construction enables CRLF header injection (#379)",
            metadata={"client_name": client_name[:40]},
        )
    if used_spread_from_char_code_base64 or products_endpoint_uses_n_plus_1_stripe_calls:
        return GuardResult(
            allowed=False,
            code="STRIPE_BASE64_STACK_OVERFLOW_OR_N_PLUS_1_PRODUCTS_BLOCKED",
            detail="Base64 conversion must use Buffer/chunks (#382) and /products must avoid N+1 Stripe lookups (#378)",
            metadata={"used_spread_from_char_code_base64": used_spread_from_char_code_base64},
        )
    if credential_forwarded_to_untrusted_arg_host:
        return GuardResult(
            allowed=False,
            code="MCP_CREDENTIAL_DESTINATION_INJECTION_BLOCKED",
            detail="Credentials must never be sent to an untrusted destination URL supplied in tool arguments (#3285)",
            metadata={"credential_forwarded_to_untrusted_arg_host": True},
        )
    if mcp_rate_limit_code != -32023 or mcp_rate_limit_retry_after_seconds <= 0:
        return GuardResult(
            allowed=False,
            code="MCP_RATE_LIMITED_ERROR_SCHEMA_INVALID_BLOCKED",
            detail="Standardized MCP RateLimited error requires code -32023 and positive retryAfter (#3304)",
            metadata={"mcp_rate_limit_code": mcp_rate_limit_code},
        )
    if pass_k_compared_enum_str_directly_in_pandas3 or not all_infra_error_tasks_kept_in_pass_k_denominator:
        return GuardResult(
            allowed=False,
            code="TAU2_PASS_K_INFRA_ERROR_DENOMINATOR_CORRUPTION_BLOCKED",
            detail="pass^k must compare TerminationReason.value under pandas 3.x and keep all-infra-error tasks in denominator (#498)",
            metadata={"pass_k_compared_enum_str_directly_in_pandas3": pass_k_compared_enum_str_directly_in_pandas3},
        )
    if not pydantic_coerced_float_kwargs_before_tool_call or not nested_json_tool_args_compared_as_parsed_json:
        return GuardResult(
            allowed=False,
            code="TAU2_KWARGS_FLOAT_DRIFT_OR_RAW_JSON_STRING_COMPARE_BLOCKED",
            detail="Tool kwargs must be coerced via Pydantic (#516) and nested JSON-string tool args compared as parsed JSON (#513)",
            metadata={"pydantic_coerced_float_kwargs_before_tool_call": pydantic_coerced_float_kwargs_before_tool_call},
        )
    if agent_implementation in {"llm_agent_solo", "llm_agent_solo_gt"} and not detected_as_solo_mode:
        return GuardResult(
            allowed=False,
            code="TAU2_SOLO_GT_MODE_MISDETECTED_BLOCKED",
            detail="is_solo_mode() must recognize llm_agent_solo_gt so TelecomUserTools are loaded on replay (#508)",
            metadata={"agent_implementation": agent_implementation},
        )
    if close_account_reason not in _VALID_CLOSE_ACCOUNT_REASONS or not gemini_8khz_start_sensitivity_high_and_sliding_window:
        return GuardResult(
            allowed=False,
            code="TAU2_CLOSE_ACCOUNT_REASON_OR_GEMINI_VOICE_CONFIG_BLOCKED",
            detail="close_bank_account_7392 requires fixed reason enum (#484) and Gemini 8kHz requires START_SENSITIVITY_HIGH + SlidingWindow (#511/#510)",
            metadata={"close_account_reason": close_account_reason},
        )
    return GuardResult(
        allowed=True,
        code="STRIPE_MCP_SECURITY_AND_TAU2_METRICS_VERIFIED",
        detail="Stripe User-Agent/Base64, MCP -32023/Credential-Injection, and tau2-bench pass^k/Pydantic/solo_gt/banking guards verified",
        metadata={"agent_implementation": agent_implementation},
    )
