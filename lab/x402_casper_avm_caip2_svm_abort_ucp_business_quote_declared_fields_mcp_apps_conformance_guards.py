"""Stage 236 deterministic protocol & security guards (`PR-01..PR-16`).

Covers 46 primary-source PRs across x402 Foundation (`#3885`, `#3894`, `#3884`,
`#3878`, `#3892`, `#3881`, `#3877`, `#3887`, `#3886`, `#3874`, `#3869`, `#3895`,
`#3883`, `#3882`, `#3880`, `#3879`, `#3872`, `#3870`), Universal Commerce
Protocol (`#939`, `#930`, `#918`, `#915`, `#940`, `#933`, `#932`, `#913`,
`#911`, `#910`, `#907`), MCP Apps (`ext-apps#823`, `#822`, `#812`, `#819`,
`#818`, `#816`, `#815`, `#814`), MCP Conformance (`#563`, `#561`, `#560`,
`#559`, `#558`, `#556`, `#555`, `#554`, `#548`), MCP Registry (`#1730`, `#1728`,
`#1727`, `#1726`), and MCP Java SDK (`#1271`, `#1266`, `#1260`, `#1259`,
`#1257`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class GuardEvaluation:
    passed: bool
    code: str
    reason: str
    remediation: str


CAIP2_V2_REGEX = re.compile(r"^[a-z0-9-]{3,8}:[a-zA-Z0-9-_]{1,32}$")


def evaluate_x402_casper_exact_scheme(payload: Mapping[str, Any]) -> GuardEvaluation:
    """PR-01: x402#3885 Go Casper exact scheme support."""
    network = str(payload.get("network", ""))
    scheme = str(payload.get("scheme", ""))
    key_alg = str(payload.get("key_alg", ""))
    alg_tag_matches = bool(payload.get("alg_tag_matches", False))
    secp256k1_low_s = bool(payload.get("secp256k1_low_s", True))
    valid_after = int(payload.get("valid_after", 0))
    now_ts = int(payload.get("now_ts", 0))
    valid_before = int(payload.get("valid_before", 0))
    concurrent_duplicate_in_cache = bool(payload.get("concurrent_duplicate_in_cache", False))
    confirmation_timed_out = bool(payload.get("confirmation_timed_out", False))
    recorded_in_pending_store = bool(payload.get("recorded_in_pending_store", False))
    retry_rebroadcasted = bool(payload.get("retry_rebroadcasted", False))

    if not network.startswith("casper:") or scheme != "exact":
        return GuardEvaluation(
            False,
            "X402_CASPER_NETWORK_OR_SCHEME_INVALID",
            "Casper mechanism requires a 'casper:*' network and supports only the 'exact' scheme",
            "Use 'casper:casper' or 'casper:casper-test' with scheme 'exact'.",
        )
    if key_alg not in {"ed25519", "secp256k1"} or not alg_tag_matches or (key_alg == "secp256k1" and not secp256k1_low_s):
        return GuardEvaluation(
            False,
            "X402_CASPER_SIGNATURE_TAG_OR_LOW_S_INVALID",
            "Casper CEP-3009 signature failed algorithm tag match or secp256k1 low-s requirement",
            "Sign the CEP-3009 TransferWithAuthorization EIP-712 digest with matching algorithm tag and canonical low-s.",
        )
    if not (valid_after < now_ts < valid_before):
        return GuardEvaluation(
            False,
            "X402_CASPER_TIME_WINDOW_INVALID",
            "Casper authorization violates strict validAfter < now < validBefore window",
            "Ensure validAfter < current block/wall timestamp < validBefore.",
        )
    if concurrent_duplicate_in_cache:
        return GuardEvaluation(
            False,
            "X402_CASPER_DUPLICATE_SETTLEMENT",
            "SettlementCache keyed on (network, token, payer, nonce) detected concurrent duplicate settle",
            "Reject concurrent duplicate settlement attempts with duplicate_settlement.",
        )
    if confirmation_timed_out and (not recorded_in_pending_store or retry_rebroadcasted):
        return GuardEvaluation(
            False,
            "X402_CASPER_PENDING_SETTLEMENT_REBROADCAST",
            "Confirmation timeout was not stored in PendingSettlementStore or retry rebroadcasted TransactionV1",
            "Return settlement_pending with txHash in PendingSettlementStore and wait on the existing transaction on retry.",
        )
    return GuardEvaluation(
        True,
        "X402_CASPER_EXACT_SCHEME_VALID",
        "Casper exact scheme CEP-3009 signature, time bounds, SettlementCache, and PendingSettlementStore verified",
        "No action required.",
    )


def evaluate_x402_v2_caip2_network_grammar(payload: Mapping[str, Any]) -> GuardEvaluation:
    """PR-02: x402#3894, #3884, & #3878 canonical V2 CAIP-2 network grammar across TS/Go/Python."""
    x402_version = int(payload.get("x402_version", 2))
    network = str(payload.get("network", ""))
    accepted_networks = list(payload.get("accepted_networks", [network]))

    if x402_version == 2:
        for net in [network, *accepted_networks]:
            if not CAIP2_V2_REGEX.match(str(net)):
                return GuardEvaluation(
                    False,
                    "X402_V2_CAIP2_NETWORK_MALFORMED",
                    f"V2 network identifier '{net}' violates strict CAIP-2 grammar (namespace 3..8 chars, reference 1..32 chars)",
                    "Use canonical CAIP-2 identifiers (e.g., 'algorand:wGHE2Pwdvd7S12BL5FaOP20EGYesN73k' or 'eip155:84532').",
                )
    return GuardEvaluation(
        True,
        "X402_V2_CAIP2_NETWORK_VALID",
        "All V2 network identifiers conform to canonical CAIP-2 namespace and 32-char reference limits",
        "No action required.",
    )


def evaluate_x402_svm_abort_cleanup_and_override_ceiling(payload: Mapping[str, Any]) -> GuardEvaluation:
    """PR-03: x402#3892, #3881, & #3877 SVM failed local charge reservation release & settlement override ceiling."""
    local_charge_failed = bool(payload.get("local_charge_failed", False))
    batch_reservation_released = bool(payload.get("batch_reservation_released", False))
    authorized_amount = int(payload.get("authorized_amount", 0))
    resolved_override_amount = int(payload.get("resolved_override_amount", 0))

    if local_charge_failed and not batch_reservation_released:
        return GuardEvaluation(
            False,
            "X402_SVM_ABORT_RESERVATION_LEAKED",
            "SVM beforeSettle returned abort after failed local charge without releasing batch reservation",
            "Release request-specific batch reservation before returning the abort in beforeSettle.",
        )
    if resolved_override_amount > authorized_amount or resolved_override_amount < 0:
        return GuardEvaluation(
            False,
            "X402_INVALID_SETTLEMENT_OVERRIDE_CEILING",
            f"Resolved settlement override ({resolved_override_amount}) exceeds authorized PaymentRequirements.amount ({authorized_amount})",
            "Reject raw, percent, or dollar settlement overrides that resolve above PaymentRequirements.amount.",
        )
    return GuardEvaluation(
        True,
        "X402_SVM_ABORT_AND_OVERRIDE_CEILING_VALID",
        "SVM failed-charge reservation cleanup and settlement override ceiling verified",
        "No action required.",
    )


def evaluate_x402_evm_retryable_lookup_and_timeout_bounds(payload: Mapping[str, Any]) -> GuardEvaluation:
    """PR-04: x402#3887, #3886, #3874, & #3869 EVM retryable signature lookup, body limits & MCP retry timeout cap."""
    signature_lookup_transport_error = bool(payload.get("signature_lookup_transport_error", False))
    scheme = str(payload.get("scheme", "exact"))
    reported_error_code = str(payload.get("reported_error_code", ""))
    verify_eip3009_return_arity = int(payload.get("verify_eip3009_return_arity", 3))
    facilitator_endpoint = str(payload.get("facilitator_endpoint", "verify"))
    response_body_bytes = int(payload.get("response_body_bytes", 0))
    mcp_recovery_retry_timeout_s = int(payload.get("mcp_recovery_retry_timeout_s", 0))
    max_request_timeout_s = int(payload.get("max_request_timeout_s", 30))

    if verify_eip3009_return_arity != 3:
        return GuardEvaluation(
            False,
            "X402_VERIFY_EIP3009_RETURN_ARITY_MISMATCH",
            "Go verifyEIP3009 non-canonical signature branch returned fewer than 3 values",
            "Return (*x402.VerifyResponse, *EIP3009SignatureClassification, error) across all verifyEIP3009 branches.",
        )
    if signature_lookup_transport_error:
        expected = (
            "invalid_upto_evm_failed_to_verify_signature"
            if scheme == "upto"
            else "invalid_exact_evm_failed_to_verify_signature"
        )
        if reported_error_code != expected:
            return GuardEvaluation(
                False,
                "X402_EVM_LOOKUP_TRANSPORT_MISCLASSIFIED",
                f"Transport failure during eth_getCode/isValidSignature reported '{reported_error_code}' instead of '{expected}'",
                "Report RPC lookup transport failures as retryable failed_to_verify_signature codes.",
            )
    limit = 4 * 1024 * 1024 if facilitator_endpoint == "bazaar_discovery" else 1 * 1024 * 1024
    if response_body_bytes > limit:
        return GuardEvaluation(
            False,
            "X402_FACILITATOR_RESPONSE_BODY_TOO_LARGE",
            f"Facilitator {facilitator_endpoint} response ({response_body_bytes} B) exceeds {limit} B limit",
            "Raise ResponseBodyTooLargeError when facilitator responses exceed 1 MiB (control plane) or 4 MiB (Bazaar).",
        )
    if mcp_recovery_retry_timeout_s > max_request_timeout_s:
        return GuardEvaluation(
            False,
            "X402_MCP_RECOVERY_RETRY_TIMEOUT_UNCAPPED",
            "MCP corrective recovery retry exceeded MaxRequestTimeout / maxRequestTimeoutSeconds cap",
            "Apply MaxRequestTimeout cap to initial probes, paid retries, and corrective recovery retries.",
        )
    return GuardEvaluation(
        True,
        "X402_EVM_LOOKUP_AND_LIMITS_VALID",
        "EVM retryable signature lookup, verifyEIP3009 3-tuple, response body limits, and MCP retry timeout cap verified",
        "No action required.",
    )


def evaluate_x402_http_402_body_bazaar_method_and_stellar(payload: Mapping[str, Any]) -> GuardEvaluation:
    """PR-05: x402#3895, #3883, #3882, #3880, #3879, #3872, & #3870 HTTP 402 body, Bazaar method, OFAC & Stellar."""
    header_map_is_mapping = bool(payload.get("header_map_is_mapping", True))
    is_browser_request = bool(payload.get("is_browser_request", False))
    http_402_json_body = payload.get("http_402_json_body", {})
    declared_input_type = str(payload.get("declared_input_type", "body"))
    advertised_method = str(payload.get("advertised_method", "POST"))
    ofac_payer_sanctioned = bool(payload.get("ofac_payer_sanctioned", False))
    stellar_simulation_error = str(payload.get("stellar_simulation_error", "none"))
    typed_error_included_context = bool(payload.get("typed_error_included_context", True))

    if not header_map_is_mapping:
        return GuardEvaluation(
            False,
            "X402_CREATE_HEADERS_MAPPING_REJECTED",
            "create_headers rejected non-dict collections.abc.Mapping per-path header values",
            "Check isinstance(value, collections.abc.Mapping) when inspecting path-keyed create_headers results.",
        )
    if not is_browser_request and (not isinstance(http_402_json_body, Mapping) or not http_402_json_body.get("error")):
        return GuardEvaluation(
            False,
            "X402_HTTP_402_EMPTY_ERROR_BODY",
            "Non-browser HTTP 402 response returned an empty JSON body '{}' without rejection reason",
            "Return {'error': paymentRequired.error} or {'error': 'settlement_failed'} in non-browser 402 JSON bodies.",
        )
    if declared_input_type == "body" and advertised_method not in {"POST", "PUT", "PATCH"}:
        return GuardEvaluation(
            False,
            "X402_BAZAAR_DECLARED_METHOD_MISMATCH",
            f"Bazaar advertised '{advertised_method}' for a body input declaration",
            "Ensure resolveDeclaredMethod advertises POST/PUT/PATCH for body inputs and GET/HEAD/DELETE for query inputs.",
        )
    if declared_input_type == "query" and advertised_method not in {"GET", "HEAD", "DELETE"}:
        return GuardEvaluation(
            False,
            "X402_BAZAAR_DECLARED_METHOD_MISMATCH",
            f"Bazaar advertised '{advertised_method}' for a query input declaration",
            "Ensure resolveDeclaredMethod advertises GET/HEAD/DELETE for query inputs.",
        )
    if ofac_payer_sanctioned:
        return GuardEvaluation(
            False,
            "X402_PRESIGN_OFAC_SANCTIONED_PAYER",
            "presign-guard-payer-screen flagged payer on the OFAC SDN sanctions list before settlement",
            "Block settlement when pre-sign payer screening matches OFAC SDN sanctions.",
        )
    if stellar_simulation_error != "none" and (
        stellar_simulation_error
        not in {"SimulationFailedError", "TrustlineMissingError", "InsufficientBalanceError"}
        or not typed_error_included_context
    ):
        return GuardEvaluation(
            False,
            "X402_STELLAR_UNTYPED_SIMULATION_ERROR",
            "Soroban transaction simulation failure was not surfaced as a typed Stellar error with account/asset context",
            "Surface SimulationFailedError, TrustlineMissingError, or InsufficientBalanceError with account and asset context.",
        )
    return GuardEvaluation(
        True,
        "X402_HTTP_402_BAZAAR_AND_STELLAR_VALID",
        "Mapping headers, 402 JSON error body, Bazaar method matching, OFAC pre-sign screen, and Stellar errors verified",
        "No action required.",
    )


def evaluate_ucp_business_identity_capability(payload: Mapping[str, Any]) -> GuardEvaluation:
    """PR-06: ucp#939 dev.ucp.common.business location-independent business identity capability."""
    capability_name = str(payload.get("capability_name", ""))
    declared_in_ucp_capabilities = bool(payload.get("declared_in_ucp_capabilities", False))
    top_level_profile_business_field = bool(payload.get("top_level_profile_business_field", False))
    conflated_with_retail_location = bool(payload.get("conflated_with_retail_location", False))
    uses_shared_business_summary_schema = bool(payload.get("uses_shared_business_summary_schema", False))
    has_display_name = bool(payload.get("has_display_name", False))

    if capability_name != "dev.ucp.common.business" or not declared_in_ucp_capabilities:
        return GuardEvaluation(
            False,
            "UCP_BUSINESS_CAPABILITY_NOT_DECLARED",
            "Business identity was not declared as 'dev.ucp.common.business' in ucp.capabilities",
            "Model location-independent business identity via dev.ucp.common.business in ucp.capabilities.",
        )
    if top_level_profile_business_field or conflated_with_retail_location:
        return GuardEvaluation(
            False,
            "UCP_BUSINESS_IDENTITY_PLACEMENT_INVALID",
            "Business identity was placed as a top-level profile field or conflated with dev.ucp.common.location",
            "Keep brand/corporate identity in dev.ucp.common.business, separate from physical retail locations.",
        )
    if not uses_shared_business_summary_schema or not has_display_name:
        return GuardEvaluation(
            False,
            "UCP_BUSINESS_SUMMARY_SCHEMA_INVALID",
            "Business identity does not use shared business_summary.json or omits required display name",
            "Validate profile and catalog seller identity against common/types/business_summary.json and contact.json.",
        )
    return GuardEvaluation(
        True,
        "UCP_BUSINESS_IDENTITY_CAPABILITY_VALID",
        "UCP dev.ucp.common.business capability and shared business_summary schema verified",
        "No action required.",
    )


def evaluate_ucp_quote_extension_and_offer_integrity(payload: Mapping[str, Any]) -> GuardEvaluation:
    """PR-07: ucp#930 & #918 dev.ucp.common.quote extension and Offer decision-integrity digest binding."""
    quote_accepted = bool(payload.get("quote_accepted", False))
    quote_totals_entries = int(payload.get("quote_totals_entries", 0))
    quote_total_has_display_text = bool(payload.get("quote_total_has_display_text", False))
    operation = str(payload.get("operation", "update_checkout"))
    accepted_id_present_on_request = bool(payload.get("accepted_id_present_on_request", False))
    order_quote_projection_keys = set(payload.get("order_quote_projection_keys", []))
    polling_after_expires_at = bool(payload.get("polling_after_expires_at", False))
    offer_provenance_in_digest = bool(payload.get("offer_provenance_in_digest", True))
    offer_applied_conflated_with_committed = bool(payload.get("offer_applied_conflated_with_committed", False))

    if quote_accepted and (quote_totals_entries != 1 or not quote_total_has_display_text):
        return GuardEvaluation(
            False,
            "UCP_QUOTE_TOTALS_REFLECTION_INVALID",
            "Accepted quotation must be reflected in totals as exactly one entry of type 'quote' with display_text",
            "Emit a single totals[type='quote'] entry with display_text when a quotation is accepted.",
        )
    if operation == "complete_checkout" and accepted_id_present_on_request:
        return GuardEvaluation(
            False,
            "UCP_QUOTE_ACCEPTED_ID_ON_COMPLETE",
            "Buyer-written quote.accepted_id must be omitted on complete_checkout requests",
            "Pass quote.accepted_id on create/update only and omit it on complete_checkout.",
        )
    if quote_accepted and order_quote_projection_keys != {"id", "subtotal"}:
        return GuardEvaluation(
            False,
            "UCP_ORDER_QUOTE_PROJECTION_INVALID",
            f"Order quote projection keys {sorted(order_quote_projection_keys)} do not match {{'id', 'subtotal'}}",
            "Project accepted quotation onto Order strictly as quote: {id, subtotal}.",
        )
    if polling_after_expires_at:
        return GuardEvaluation(
            False,
            "UCP_QUOTE_POLLING_PAST_EXPIRY",
            "Platform continued asynchronous review polling after quote.expires_at",
            "Stop polling asynchronous quote review once expires_at is reached.",
        )
    if not offer_provenance_in_digest or offer_applied_conflated_with_committed:
        return GuardEvaluation(
            False,
            "UCP_OFFER_DECISION_INTEGRITY_VIOLATION",
            "Offer digest subject omitted commercial-provenance extension fields or conflated applied vs committed state",
            "Include all decision-relevant provenance fields in the Offer digest subject and separate applied from committed.",
        )
    return GuardEvaluation(
        True,
        "UCP_QUOTE_AND_OFFER_INTEGRITY_VALID",
        "UCP dev.ucp.common.quote lifecycle, Order projection, and Offer decision-integrity digest verified",
        "No action required.",
    )


def evaluate_ucp_declared_fields_extension(payload: Mapping[str, Any]) -> GuardEvaluation:
    """PR-08: ucp#915 shopping declared_fields for extensible checkout data collection."""
    config_schemas = dict(payload.get("config_schemas", {}))
    required_checkout_fields = list(payload.get("required_checkout_fields", []))
    required_line_item_fields = list(payload.get("required_line_item_fields", []))
    checkout_declared_fields = dict(payload.get("checkout_declared_fields", {}))
    line_item_declared_fields = dict(payload.get("line_item_declared_fields", {}))
    schema_validation_passed = bool(payload.get("schema_validation_passed", False))

    for key in [*required_checkout_fields, *required_line_item_fields]:
        if "." not in str(key) or str(key) not in config_schemas:
            return GuardEvaluation(
                False,
                "UCP_DECLARED_FIELDS_SCHEMA_UNBOUND",
                f"Required declared field '{key}' is not a Reverse-DNS key or is missing from checkout.config",
                "Define every required_declared_fields entry as a Reverse-DNS key in checkout.config.",
            )
    for key in required_checkout_fields:
        if key not in checkout_declared_fields:
            return GuardEvaluation(
                False,
                "UCP_CHECKOUT_DECLARED_FIELD_MISSING",
                f"Order-levelcheckout.declared_fields is missing required field '{key}'",
                "Provide all checkout.required_declared_fields in checkout.declared_fields before completion.",
            )
    for key in required_line_item_fields:
        if key not in line_item_declared_fields:
            return GuardEvaluation(
                False,
                "UCP_LINE_ITEM_DECLARED_FIELD_MISSING",
                f"Item-level line_item.declared_fields is missing required field '{key}'",
                "Provide all line_item.required_declared_fields in line_item.declared_fields.",
            )
    if not schema_validation_passed:
        return GuardEvaluation(
            False,
            "UCP_DECLARED_FIELDS_VALUE_INVALID",
            "Submitted declared_fields value failed Reverse-DNS JSON Schema validation against checkout.config",
            "Validate all declared_fields values against their corresponding JSON Schema in checkout.config.",
        )
    return GuardEvaluation(
        True,
        "UCP_DECLARED_FIELDS_VALID",
        "UCP checkout.config Reverse-DNS schemas and order/item declared_fields bindings verified",
        "No action required.",
    )


def evaluate_ucp_cart_checkout_304_permalink_and_agent_sig(payload: Mapping[str, Any]) -> GuardEvaluation:
    """PR-09: ucp#940, #933, #932, #913, #911, #910, & #907 cart-only create, 304, 303 permalink & ucp-agent sig."""
    operation = str(payload.get("operation", "create_checkout"))
    has_cart_id = bool(payload.get("has_cart_id", False))
    has_line_items = bool(payload.get("has_line_items", False))
    profile_status_code = int(payload.get("profile_status_code", 200))
    permalink_303_headers = {str(k).lower(): str(v) for k, v in dict(payload.get("permalink_303_headers", {})).items()}
    ucp_agent_header_present = bool(payload.get("ucp_agent_header_present", True))
    signature_input_covered = {str(x).lower() for x in payload.get("signature_input_covered", [])}

    if operation == "create_checkout" and not (has_cart_id or has_line_items):
        return GuardEvaluation(
            False,
            "UCP_CREATE_CHECKOUT_SOURCE_MISSING",
            "create_checkout requires either cart_id or line_items (operation-scoped anyOf)",
            "Supply cart_id, line_items, or both (with Cart precedence) on create_checkout.",
        )
    if operation == "complete_checkout" and has_cart_id:
        return GuardEvaluation(
            False,
            "UCP_CART_ID_ON_COMPLETE_CHECKOUT",
            "create-only cart_id was included on a complete_checkout request",
            "Omit cart_id on update_checkout and complete_checkout requests ('complete': 'omit').",
        )
    if profile_status_code in {301, 302, 303, 307, 308}:
        return GuardEvaluation(
            False,
            "UCP_PROFILE_REDIRECT_FORBIDDEN",
            f"Profile endpoint returned forbidden redirect status {profile_status_code} (only 200 OK or 304 Not Modified allowed)",
            "Allow 304 Not Modified for conditional ETag/Last-Modified revalidation, but reject 301/302/303/307/308 redirects.",
        )
    if permalink_303_headers.get("cache-control") != "no-store" or permalink_303_headers.get("referrer-policy") != "no-referrer":
        return GuardEvaluation(
            False,
            "UCP_PERMALINK_303_HEADERS_MISSING",
            "Handled permalink 303 redirect omitted Cache-Control: no-store or Referrer-Policy: no-referrer",
            "Include both Cache-Control: no-store and Referrer-Policy: no-referrer on every 303 permalink resolution.",
        )
    if ucp_agent_header_present and "ucp-agent" not in signature_input_covered:
        return GuardEvaluation(
            False,
            "UCP_AGENT_HEADER_NOT_COVERED_BY_SIGNATURE",
            "Request carries UCP-Agent header but Signature-Input covered set omits 'ucp-agent'",
            "Include 'ucp-agent' in Signature-Input covered components whenever UCP-Agent is present.",
        )
    return GuardEvaluation(
        True,
        "UCP_CART_304_PERMALINK_AND_AGENT_SIG_VALID",
        "Cart-only checkout creation, 304 profile revalidation, 303 permalink headers, and ucp-agent signature verified",
        "No action required.",
    )


def evaluate_mcp_apps_iframe_allow_init_and_dotted_root(payload: Mapping[str, Any]) -> GuardEvaluation:
    """PR-10: ext-apps#823, #822, & #812 iframe allow '; ' separator, ui/initialize & dotted-dir sandbox.html."""
    iframe_allow_attr = str(payload.get("iframe_allow_attr", ""))
    required_permissions = list(payload.get("required_permissions", ["camera", "microphone", "clipboard-write"]))
    init_method = str(payload.get("init_method", ""))
    init_params = dict(payload.get("init_params", {}))
    checkout_in_dotted_dir = bool(payload.get("checkout_in_dotted_dir", True))
    sendfile_uses_explicit_root = bool(payload.get("sendfile_uses_explicit_root", False))

    parts = [p.strip() for p in iframe_allow_attr.split(";") if p.strip()]
    if any(" " in p for p in parts) or not all(req in parts for req in required_permissions):
        return GuardEvaluation(
            False,
            "MCP_APPS_IFRAME_ALLOW_POLICY_MALFORMED",
            f"iframe allow attribute '{iframe_allow_attr}' used spaces instead of '; ' or omitted clipboard-write",
            "Join Permissions Policy directives with '; ' and include clipboard-write when requested.",
        )
    if init_method != "ui/initialize" or "appInfo" not in init_params or "appCapabilities" not in init_params:
        return GuardEvaluation(
            False,
            "MCP_APPS_INITIALIZE_CONTRACT_MISMATCH",
            "MCP App sent legacy 'initialize' or omitted appInfo/appCapabilities in McpUiInitializeRequest",
            "Send method 'ui/initialize' with appInfo and appCapabilities per normative specification.",
        )
    if checkout_in_dotted_dir and not sendfile_uses_explicit_root:
        return GuardEvaluation(
            False,
            "MCP_APPS_DOTTED_DIR_SANDBOX_404",
            "basic-host res.sendFile failed with 404 for sandbox.html under a dot-prefixed directory (.runs/)",
            "Pass explicit root option to res.sendFile so dot-prefixed ancestor directories do not trigger 404.",
        )
    return GuardEvaluation(
        True,
        "MCP_APPS_IFRAME_INIT_AND_SANDBOX_VALID",
        "MCP Apps '; ' iframe allow attribute, ui/initialize contract, and dotted-directory sandbox serving verified",
        "No action required.",
    )


def evaluate_mcp_apps_bridge_lifecycle_and_windows_file_url(payload: Mapping[str, Any]) -> GuardEvaluation:
    """PR-11: ext-apps#819, #818, #816, #815, & #814 AppBridge lifecycle, RAF/ResizeObserver & Windows file://."""
    disconnected_context_buffered = bool(payload.get("disconnected_context_buffered", False))
    unhandled_rejection_on_disconnect = bool(payload.get("unhandled_rejection_on_disconnect", False))
    shared_list_change_dispatcher = bool(payload.get("shared_list_change_dispatcher", False))
    pending_raf_canceled_including_zero = bool(payload.get("pending_raf_canceled_including_zero", False))
    resize_observer_released_on_close = bool(payload.get("resize_observer_released_on_close", False))
    windows_file_url = str(payload.get("windows_file_url", "file:///C:/Users/me/doc.pdf"))
    resolved_windows_path = str(payload.get("resolved_windows_path", r"C:\Users\me\doc.pdf"))

    if not disconnected_context_buffered or unhandled_rejection_on_disconnect:
        return GuardEvaluation(
            False,
            "MCP_APPS_HOST_CONTEXT_UNHANDLED_REJECTION",
            "setHostContext() while disconnected caused an unhandled rejection or lost context before next handshake",
            "Buffer disconnected host context updates for the next initialization handshake and route send errors to onerror.",
        )
    if not shared_list_change_dispatcher:
        return GuardEvaluation(
            False,
            "MCP_APPS_LIST_CHANGE_HANDLER_OVERWRITTEN",
            "Multiple AppBridge views on one Client overwrote each other's list_changed handlers",
            "Share one list-change dispatcher per Client and forward only to connected Apps-ready views.",
        )
    if not pending_raf_canceled_including_zero or not resize_observer_released_on_close:
        return GuardEvaluation(
            False,
            "MCP_APPS_RESIZE_OBSERVER_OR_RAF_LEAK",
            "Pending animation frame (including ID 0) or automatic ResizeObserver leaked after cleanup/disconnect",
            "Cancel pending requestAnimationFrame IDs (including 0) and invoke resize cleanup from transport-close hook.",
        )
    if windows_file_url.startswith("file:///") and (
        resolved_windows_path.startswith("/") or "C:\\C:\\" in resolved_windows_path
    ):
        return GuardEvaluation(
            False,
            "MCP_APPS_WINDOWS_FILE_URL_DOUBLED_DRIVE",
            f"Windows file URL '{windows_file_url}' resolved to malformed path '{resolved_windows_path}'",
            "Strip the leading slash before a Windows drive letter in fileUrlToPath before calling path.resolve.",
        )
    return GuardEvaluation(
        True,
        "MCP_APPS_BRIDGE_AND_FILE_URL_VALID",
        "AppBridge host context buffering, shared list-change dispatcher, RAF/ResizeObserver cleanup, and Windows file:// verified",
        "No action required.",
    )


def evaluate_mcp_conformance_stateless_stream_and_cache_attrs(payload: Mapping[str, Any]) -> GuardEvaluation:
    """PR-12: conformance#563, #561, #560, & #559 resultType stamp, originating stream, empty headers & directory cache."""
    stateless_tool_has_result_type = bool(payload.get("stateless_tool_has_result_type", False))
    elicitation_sent_via_extra_send_request = bool(payload.get("elicitation_sent_via_extra_send_request", False))
    custom_header_presence_matches_arg = bool(payload.get("custom_header_presence_matches_arg", False))
    protocol_version = str(payload.get("protocol_version", "2026-07-28"))
    directory_read_result = dict(payload.get("directory_read_result", {}))

    if not stateless_tool_has_result_type:
        return GuardEvaluation(
            False,
            "MCP_CONFORMANCE_STATELESS_RESULT_TYPE_MISSING",
            "Hand-written stateless tools/call response bypassed normalizeStatelessResponse and omitted resultType",
            "Stamp resultType on all stateless tool results before writing JSON-RPC responses.",
        )
    if not elicitation_sent_via_extra_send_request:
        return GuardEvaluation(
            False,
            "MCP_CONFORMANCE_ELICITATION_WRONG_STREAM",
            "Tool handler sent elicitation/create via server.request() on GET stream instead of originating POST stream",
            "Use extra.sendRequest() so elicitation/create is correlated with the initiating tools/call stream.",
        )
    if not custom_header_presence_matches_arg:
        return GuardEvaluation(
            False,
            "MCP_CONFORMANCE_HEADER_PRESENCE_MISMATCH",
            "Empty/null argument vs custom HTTP header presence mismatch was not rejected",
            "Reject empty argument with absent header and omitted/null argument with present empty header.",
        )
    if protocol_version >= "2026-07-28" and (
        "ttlMs" not in directory_read_result or "cacheScope" not in directory_read_result
    ):
        return GuardEvaluation(
            False,
            "MCP_CONFORMANCE_DIRECTORY_CACHE_ATTRS_MISSING",
            "resources/directory/read result omitted required ttlMs or cacheScope on protocol >= 2026-07-28",
            "Include ttlMs and cacheScope on ReadResourceDirectoryResult per SEP-2640.",
        )
    return GuardEvaluation(
        True,
        "MCP_CONFORMANCE_STREAM_AND_CACHE_VALID",
        "Stateless resultType, originating-stream elicitation, header presence check, and directory cache attributes verified",
        "No action required.",
    )


def evaluate_mcp_conformance_sep1036_2243_2164_2322(payload: Mapping[str, Any]) -> GuardEvaluation:
    """PR-13: conformance#558, #556, #555, #554, & #548 SEP-1036 URL mode, SEP-2243 -32020, SEP-2164 -32602 & SEP-2322."""
    url_elicitation_echoed_newest_state = bool(payload.get("url_elicitation_echoed_newest_state", False))
    omitted_mode_treated_as_form = bool(payload.get("omitted_mode_treated_as_form", False))
    header_mismatch_http_status = int(payload.get("header_mismatch_http_status", 400))
    header_mismatch_rpc_code = int(payload.get("header_mismatch_rpc_code", -32020))
    missing_resource_rpc_code = int(payload.get("missing_resource_rpc_code", -32602))
    request_state_only_echoed_on_retry = bool(payload.get("request_state_only_echoed_on_retry", False))

    if not url_elicitation_echoed_newest_state or not omitted_mode_treated_as_form:
        return GuardEvaluation(
            False,
            "MCP_SEP1036_URL_ELICITATION_NONCONFORMANT",
            "Client failed to echo newest requestState across URL elicitation rounds or misread omitted mode",
            "Echo newest requestState on every URL-mode round and treat omitted mode as 'form' per SEP-1036.",
        )
    if header_mismatch_http_status != 400 or header_mismatch_rpc_code != -32020:
        return GuardEvaluation(
            False,
            "MCP_SEP2243_HEADER_ERROR_CODE_MUST_VIOLATION",
            f"Header validation rejection returned HTTP {header_mismatch_http_status} / RPC {header_mismatch_rpc_code} instead of 400 / -32020",
            "Return HTTP 400 Bad Request with JSON-RPC error code -32020 (MUST per SEP-2243).",
        )
    if missing_resource_rpc_code not in {-32602, -32002}:
        return GuardEvaluation(
            False,
            "MCP_SEP2164_RESOURCE_NOT_FOUND_CODE_INVALID",
            f"Non-existent resource returned JSON-RPC error {missing_resource_rpc_code} instead of MUST -32602 (-32002)",
            "Return JSON-RPC error code -32602 (Invalid Params) when a requested resource does not exist.",
        )
    if not request_state_only_echoed_on_retry:
        return GuardEvaluation(
            False,
            "MCP_SEP2322_REQUEST_STATE_ONLY_RETRY_OMITTED",
            "Client failed to echo requestState when InputRequiredResult omitted inputRequests",
            "Echo exact requestState on retry even when InputRequiredResult contains requestState without inputRequests.",
        )
    return GuardEvaluation(
        True,
        "MCP_CONFORMANCE_SEPS_VALID",
        "SEP-1036 URL elicitation, SEP-2243 -32020 MUST, SEP-2164 -32602 MUST, and SEP-2322 requestState retry verified",
        "No action required.",
    )


def evaluate_mcp_registry_trgm_icon_dpr_and_verified_backups(payload: Mapping[str, Any]) -> GuardEvaluation:
    """PR-14: registry#1730, #1728, #1727, & #1726 pg_trgm index, DPR icon scoring, retired K8up & verified backups."""
    trgm_index_valid_and_ready = bool(payload.get("trgm_index_valid_and_ready", False))
    device_pixel_ratio = float(payload.get("device_pixel_ratio", 2.0))
    tile_css_px = int(payload.get("tile_css_px", 40))
    selected_raster_px = int(payload.get("selected_raster_px", 96))
    omitted_sizes_treated_as_any = bool(payload.get("omitted_sizes_treated_as_any", False))
    retired_k8up_schedule_removed = bool(payload.get("retired_k8up_schedule_removed", False))
    backup_verified_sha256_and_restic = bool(payload.get("backup_verified_sha256_and_restic", False))

    if not trgm_index_valid_and_ready:
        return GuardEvaluation(
            False,
            "MCP_REGISTRY_TRGM_INDEX_INVALID",
            "server_name pg_trgm GIN index is missing or left invalid by an interrupted concurrent build",
            "Build the pg_trgm GIN index concurrently and verify indisvalid/indisready in migration 015.",
        )
    target_px = tile_css_px * device_pixel_ratio
    if selected_raster_px < target_px or not omitted_sizes_treated_as_any:
        return GuardEvaluation(
            False,
            "MCP_REGISTRY_ICON_DPR_OR_SIZES_INVALID",
            f"Icon selector chose {selected_raster_px}px for {target_px}px DPR target or penalized omitted sizes",
            "Multiply tile CSS pixels by devicePixelRatio and treat omitted/empty icon sizes as 'any'.",
        )
    if not retired_k8up_schedule_removed or not backup_verified_sha256_and_restic:
        return GuardEvaluation(
            False,
            "MCP_REGISTRY_BACKUP_OR_K8UP_UNSAFE",
            "Retired K8up Schedule remains present or daily pg_dump backup lacks SHA-256 + Restic verification",
            "Remove retired K8up Schedule and validate pg_dump --compress=0 archive with SHA-256 and restic check.",
        )
    return GuardEvaluation(
        True,
        "MCP_REGISTRY_DB_UI_AND_BACKUP_VALID",
        "MCP Registry pg_trgm index, DPR-aware icon selection, K8up cleanup, and verified backups confirmed",
        "No action required.",
    )


def evaluate_mcp_java_sdk_stdio_close_and_template_notify(payload: Mapping[str, Any]) -> GuardEvaluation:
    """PR-15: java-sdk#1271, #1266, #1260, #1259, & #1257 bounded closeGracefully & removeResourceTemplate notify."""
    sigterm_ignored_by_child = bool(payload.get("sigterm_ignored_by_child", False))
    graceful_close_bounded_and_forced = bool(payload.get("graceful_close_bounded_and_forced", False))
    resource_template_removed = bool(payload.get("resource_template_removed", False))
    resources_list_changed_declared = bool(payload.get("resources_list_changed_declared", True))
    list_changed_notification_sent = bool(payload.get("list_changed_notification_sent", False))
    multi_filter_race_free = bool(payload.get("multi_filter_race_free", False))
    schema_validator_patched = bool(payload.get("schema_validator_patched", False))

    if sigterm_ignored_by_child and not graceful_close_bounded_and_forced:
        return GuardEvaluation(
            False,
            "MCP_JAVA_STDIO_CLOSE_UNBOUNDED_HANG",
            "StdioClientTransport.closeGracefully() waited indefinitely on Process.onExit() when child ignored SIGTERM",
            "Bound SIGTERM wait with processTerminationTimeout and escalate to Process.destroyForcibly().",
        )
    if resource_template_removed and resources_list_changed_declared and not list_changed_notification_sent:
        return GuardEvaluation(
            False,
            "MCP_JAVA_REMOVE_TEMPLATE_NOTIFICATION_MISSING",
            "McpAsyncServer.removeResourceTemplate did not emit notifications/resources/list_changed",
            "Send notifications/resources/list_changed when removing a resource template while listChanged is enabled.",
        )
    if not multi_filter_race_free or not schema_validator_patched:
        return GuardEvaluation(
            False,
            "MCP_JAVA_FILTER_RACE_OR_VALIDATOR_OUTDATED",
            "Tool list multiple-filter composition has cancellation race or json-schema-validator is below 2.0.8/3.0.8",
            "Avoid cancelling sibling tool filters and upgrade networknt json-schema-validator to >= 2.0.8 / 3.0.8.",
        )
    return GuardEvaluation(
        True,
        "MCP_JAVA_SDK_LIFECYCLE_VALID",
        "Java SDK bounded stdio closeGracefully, removeResourceTemplate list_changed, and filter safety verified",
        "No action required.",
    )


def evaluate_stage236_composite_gate(payload: Mapping[str, Any]) -> GuardEvaluation:
    """PR-16: Composite gate requiring all 15 Stage 236 domain guards (`PR-01..PR-15`) to pass."""
    evaluators = [
        ("PR-01", evaluate_x402_casper_exact_scheme),
        ("PR-02", evaluate_x402_v2_caip2_network_grammar),
        ("PR-03", evaluate_x402_svm_abort_cleanup_and_override_ceiling),
        ("PR-04", evaluate_x402_evm_retryable_lookup_and_timeout_bounds),
        ("PR-05", evaluate_x402_http_402_body_bazaar_method_and_stellar),
        ("PR-06", evaluate_ucp_business_identity_capability),
        ("PR-07", evaluate_ucp_quote_extension_and_offer_integrity),
        ("PR-08", evaluate_ucp_declared_fields_extension),
        ("PR-09", evaluate_ucp_cart_checkout_304_permalink_and_agent_sig),
        ("PR-10", evaluate_mcp_apps_iframe_allow_init_and_dotted_root),
        ("PR-11", evaluate_mcp_apps_bridge_lifecycle_and_windows_file_url),
        ("PR-12", evaluate_mcp_conformance_stateless_stream_and_cache_attrs),
        ("PR-13", evaluate_mcp_conformance_sep1036_2243_2164_2322),
        ("PR-14", evaluate_mcp_registry_trgm_icon_dpr_and_verified_backups),
        ("PR-15", evaluate_mcp_java_sdk_stdio_close_and_template_notify),
    ]
    for pr_id, fn in evaluators:
        sub = dict(payload.get(pr_id, {}))
        res = fn(sub)
        if not res.passed:
            return GuardEvaluation(
                False,
                f"STAGE236_COMPOSITE_BLOCKED_{pr_id}_{res.code}",
                f"{pr_id} failed: {res.reason}",
                res.remediation,
            )
    return GuardEvaluation(
        True,
        "STAGE236_COMPOSITE_ALL_16_GUARDS_PASSED",
        "All 16 Stage 236 guards across x402, UCP, MCP Apps, Conformance, Registry, and Java SDK passed",
        "No action required.",
    )
