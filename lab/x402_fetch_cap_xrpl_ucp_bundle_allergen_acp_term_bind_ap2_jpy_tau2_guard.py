"""Stage 154 deterministic guardrails: x402 @x402/fetch overcharge cap & XRPL offline multisig / route & Java servlet paywall bypass & SIWX server-URL entitlement / fail-closed recovery extension & Stellar smart-account fee ceiling, UCP postal address components & standardized fulfillment events & nested bundle semantics / catalog similarity & food allergen safety & RFC 9421 ECDSA raw r||s / privacy-bounded ad attribution & root-object schema & Nano (XNO) instrument / payment terms empty-object guard & OAuth client attestation & option selection rules, ACP ephemeral agent identity & host-side spend attestation & 6-field OpenAPI parity / mutating REST signature freshness & 3DS AuthenticationResult term binding, Google AP2 ReceiptClient EC key & delivery destination constraint & OpenID4VP draft alignment / ISO 4217 currency-exponent Decimal budget cap & multi-hop SD-JWT isolation, and MCP supply-chain npx pinning & server routing description / Stripe worker-thread event loop & host ACTION gate / Visa TAP mTLS + Agent Passport & correctness receipt / Sierra tau2-bench flight duration, telecom suspension, retail self-exchange & answer-key minting guards (FX-01..FX-16)."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import Any
from urllib.parse import unquote, urlsplit


ISO4217_EXPONENTS: dict[str, int] = {
    "BHD": 3,
    "CLP": 0,
    "EUR": 2,
    "GBP": 2,
    "ISK": 0,
    "JPY": 0,
    "KRW": 0,
    "KWD": 3,
    "OMR": 3,
    "SGD": 2,
    "TND": 3,
    "UGX": 0,
    "USD": 2,
    "VND": 0,
}

STANDARD_UCP_FULFILLMENT_EVENTS: frozenset[str] = frozenset(
    {
        "shipped",
        "in_transit",
        "out_for_delivery",
        "delivered",
        "delivery_failed",
        "returned",
        "ready_for_pickup",
        "picked_up",
        "canceled",
    }
)

ACP_OPENAPI_REQUIRED_PARITY_FIELDS: frozenset[str] = frozenset(
    {
        "affiliate_attribution",
        "user_approval",
        "discounts",
        "authentication_result",
        "fulfillment_details",
        "intent_trace",
    }
)

NANO_ACCOUNT_RE = re.compile(r"^nano_[13][13456789abcdefghijkmnopqrstuwxyz]{59}$")
HEX64_RE = re.compile(r"^[0-9a-fA-F]{64}$")
HEX16_RE = re.compile(r"^[0-9a-fA-F]{16}$")


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    decision_code: str
    reason: str
    evidence: dict[str, Any]


def _b64u_sha256_ascii(text: str) -> str:
    digest = hashlib.sha256(text.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _fixed_point_unescape(path: str, max_passes: int = 5) -> str:
    curr = path
    for _ in range(max_passes):
        nxt = unquote(curr)
        if nxt == curr:
            break
        curr = nxt
    return curr


# ---------------------------------------------------------------------------
# FX-01: x402 #3866 / #3837 / #3829
# @x402/fetch client per-call quote/maxAmount cap, Payfetch header
# normalization, and SettleResponse/VerifyResponse errorMessage/invalidMessage
# ---------------------------------------------------------------------------
def evaluate_x402_fetch_overcharge_cap_and_header_parity(
    *,
    declared_402_amount_atomic: int,
    caller_max_amount_atomic: int | None,
    quoted_amount_atomic: int | None,
    request_headers: dict[str, str],
    verify_response: dict[str, Any],
    settle_response: dict[str, Any],
) -> GuardDecision:
    if caller_max_amount_atomic is None or caller_max_amount_atomic <= 0:
        return GuardDecision(
            allowed=False,
            decision_code="X402_FETCH_MISSING_CALLER_MAX_AMOUNT_CAP_BLOCKED",
            reason="x402 #3866: @x402/fetch MUST require a positive per-call maxAmount cap before signing any 402 payment requirement.",
            evidence={"caller_max_amount_atomic": caller_max_amount_atomic},
        )
    if declared_402_amount_atomic <= 0 or declared_402_amount_atomic > caller_max_amount_atomic:
        return GuardDecision(
            allowed=False,
            decision_code="X402_FETCH_SERVER_OVERCHARGE_EXCEEDS_MAX_AMOUNT_BLOCKED",
            reason="x402 #3866: Server-declared 402 payment amount exceeds the caller's per-call maxAmount ceiling (e.g. 10x adversarial overcharge).",
            evidence={
                "declared_402_amount_atomic": declared_402_amount_atomic,
                "caller_max_amount_atomic": caller_max_amount_atomic,
            },
        )
    if quoted_amount_atomic is not None and declared_402_amount_atomic > quoted_amount_atomic:
        return GuardDecision(
            allowed=False,
            decision_code="X402_FETCH_402_AMOUNT_EXCEEDS_PRIOR_QUOTE_BLOCKED",
            reason="x402 #3866: Server 402 challenge amount exceeds the previously agreed quote amount.",
            evidence={
                "declared_402_amount_atomic": declared_402_amount_atomic,
                "quoted_amount_atomic": quoted_amount_atomic,
            },
        )
    norm_headers = {k.upper(): v.strip() for k, v in request_headers.items() if v and v.strip()}
    payment_sig = norm_headers.get("PAYMENT-SIGNATURE") or norm_headers.get("X-PAYMENT")
    if not payment_sig:
        return GuardDecision(
            allowed=False,
            decision_code="X402_PAYMENT_HEADER_MISSING_OR_UNRECOGNIZED",
            reason="x402 #3837: Paid request must provide a non-empty PAYMENT-SIGNATURE or normalized legacy X-PAYMENT header.",
            evidence={"headers_present": sorted(norm_headers.keys())},
        )
    if "X-PAYMENT" in norm_headers and "PAYMENT-SIGNATURE" in norm_headers:
        if norm_headers["X-PAYMENT"] != norm_headers["PAYMENT-SIGNATURE"]:
            return GuardDecision(
                allowed=False,
                decision_code="X402_DUAL_PAYMENT_HEADER_CONFLICT_BLOCKED",
                reason="x402 #3837: When both X-PAYMENT and PAYMENT-SIGNATURE are present, their payloads must match byte-for-byte.",
                evidence={},
            )
    if not verify_response.get("isValid", True) and not str(verify_response.get("invalidMessage") or "").strip():
        return GuardDecision(
            allowed=False,
            decision_code="X402_VERIFY_RESPONSE_INVALID_MESSAGE_MISSING",
            reason="x402 #3829: VerifyResponse with isValid=false MUST preserve diagnostic invalidMessage alongside invalidReason.",
            evidence={"verify_response": verify_response},
        )
    if not settle_response.get("success", True) and not str(settle_response.get("errorMessage") or "").strip():
        return GuardDecision(
            allowed=False,
            decision_code="X402_SETTLE_RESPONSE_ERROR_MESSAGE_MISSING",
            reason="x402 #3829: SettleResponse with success=false MUST preserve diagnostic errorMessage alongside errorReason.",
            evidence={"settle_response": settle_response},
        )
    return GuardDecision(
        allowed=True,
        decision_code="X402_FETCH_CAP_AND_HEADER_PARITY_VERIFIED",
        reason="Caller maxAmount/quote cap, payment header normalization, and Verify/Settle diagnostic fields verified.",
        evidence={
            "declared_402_amount_atomic": declared_402_amount_atomic,
            "canonical_header_used": "PAYMENT-SIGNATURE",
        },
    )


# ---------------------------------------------------------------------------
# FX-02: x402 #3861 / #3856 / #3527
# Go wildcard network resolution, XRPL exact offline multisig quorum, and
# XRPL t54 mainnet facilitator invoiceId + SourceTag/DestinationTag
# ---------------------------------------------------------------------------
def evaluate_x402_wildcard_network_and_xrpl_multisig(
    *,
    registered_patterns: list[str],
    route_network: str,
    xrpl_tx: dict[str, Any],
    signer_quorum: int,
    signer_list_weights: dict[str, int],
    require_t54_invoice_binding: bool = True,
) -> GuardDecision:
    if ":" not in route_network:
        return GuardDecision(
            allowed=False,
            decision_code="X402_INVALID_CAIP2_ROUTE_NETWORK",
            reason="Route network must be a valid CAIP-2 identifier (namespace:reference).",
            evidence={"route_network": route_network},
        )
    ns, _ref = route_network.split(":", 1)
    matched_scheme = route_network in registered_patterns or f"{ns}:*" in registered_patterns
    if not matched_scheme:
        return GuardDecision(
            allowed=False,
            decision_code="X402_WILDCARD_NETWORK_SCHEME_UNRESOLVED",
            reason="x402 #3861: Resource server failed to resolve concrete CAIP-2 network via exact or namespace:* wildcard registration.",
            evidence={"route_network": route_network, "registered_patterns": registered_patterns},
        )
    is_multisig = bool(xrpl_tx.get("Signers"))
    if is_multisig:
        if xrpl_tx.get("SigningPubKey", None) != "":
            return GuardDecision(
                allowed=False,
                decision_code="X402_XRPL_MULTISIG_NONEMPTY_SIGNING_PUBKEY_BLOCKED",
                reason="x402 #3856: Multi-signed XRPL transaction MUST set top-level SigningPubKey to empty string \"\".",
                evidence={"SigningPubKey": xrpl_tx.get("SigningPubKey")},
            )
        seen_accounts: set[str] = set()
        accumulated_weight = 0
        for entry in xrpl_tx.get("Signers", []):
            signer = entry.get("Signer", entry)
            acct = str(signer.get("Account") or "").strip()
            sig = str(signer.get("TxnSignature") or "").strip()
            pub = str(signer.get("SigningPubKey") or "").strip()
            if not acct or not sig or not pub or not signer.get("signature_valid", True):
                return GuardDecision(
                    allowed=False,
                    decision_code="X402_XRPL_MULTISIG_INVALID_SIGNER_ENTRY",
                    reason="x402 #3856: Every XRPL Signer entry must carry valid Account, SigningPubKey, and verified TxnSignature.",
                    evidence={"signer": signer},
                )
            if acct in seen_accounts:
                return GuardDecision(
                    allowed=False,
                    decision_code="X402_XRPL_MULTISIG_DUPLICATE_SIGNER_BLOCKED",
                    reason="x402 #3856: Duplicate Signer Account in XRPL Signers[] is forbidden.",
                    evidence={"duplicate_account": acct},
                )
            if acct not in signer_list_weights:
                return GuardDecision(
                    allowed=False,
                    decision_code="X402_XRPL_MULTISIG_UNAUTHORIZED_SIGNER_BLOCKED",
                    reason="x402 #3856: Signer Account is not a member of the account's authorized SignerList.",
                    evidence={"unauthorized_account": acct},
                )
            seen_accounts.add(acct)
            accumulated_weight += int(signer_list_weights[acct])
        if signer_quorum <= 0 or accumulated_weight < signer_quorum:
            return GuardDecision(
                allowed=False,
                decision_code="X402_XRPL_MULTISIG_QUORUM_NOT_MET_BLOCKED",
                reason="x402 #3856: Sum of verified Signer weights does not meet SignerQuorum.",
                evidence={"accumulated_weight": accumulated_weight, "signer_quorum": signer_quorum},
            )
    if require_t54_invoice_binding:
        invoice_id = str(xrpl_tx.get("InvoiceID") or "").strip()
        source_tag = xrpl_tx.get("SourceTag")
        if not HEX64_RE.match(invoice_id) or not isinstance(source_tag, int) or source_tag < 0:
            return GuardDecision(
                allowed=False,
                decision_code="X402_XRPL_T54_INVOICE_ID_OR_SOURCE_TAG_MISSING",
                reason="x402 #3527: XRPL exact payment behind t54 mainnet facilitator requires 64-hex InvoiceID and integer SourceTag.",
                evidence={"InvoiceID": invoice_id, "SourceTag": source_tag},
            )
    return GuardDecision(
        allowed=True,
        decision_code="X402_WILDCARD_NETWORK_AND_XRPL_MULTISIG_VERIFIED",
        reason="Go wildcard CAIP-2 resolution, XRPL offline multisig quorum, and t54 InvoiceID/SourceTag verified.",
        evidence={"route_network": route_network, "is_multisig": is_multisig},
    )


# ---------------------------------------------------------------------------
# FX-03: x402 #3850 / #3849 / #3838
# Parameterised route & Java servlet paywall bypass prevention + SIWX settle
# hook server-canonical entitlement URL binding
# ---------------------------------------------------------------------------
def evaluate_x402_paywall_route_and_siwx_entitlement_guard(
    *,
    protected_route_pattern: str,
    servlet_context_path: str,
    raw_request_uri: str,
    payment_present: bool,
    siwx_client_resource_url: str,
    server_canonical_url: str,
) -> GuardDecision:
    decoded_uri = _fixed_point_unescape(raw_request_uri)
    path_only = urlsplit(decoded_uri).path
    # Block semicolon matrix parameters, dot segments, or double-slash bypasses (#3849/#3850)
    if ";" in path_only or ".." in path_only.split("/") or "//" in path_only:
        return GuardDecision(
            allowed=False,
            decision_code="X402_JAVA_OR_PARAM_ROUTE_NORMALIZATION_BYPASS_BLOCKED",
            reason="x402 #3849/#3850: Path normalization anomaly (matrix params ';', '..', or '//') blocked before route matching.",
            evidence={"raw_request_uri": raw_request_uri, "decoded_path": path_only},
        )
    if servlet_context_path and path_only.startswith(servlet_context_path):
        effective_path = path_only[len(servlet_context_path) :] or "/"
    else:
        effective_path = path_only

    # Compile parameterised route pattern like /api/items/:id or /api/items/[id]
    regex_pat = re.sub(r":([A-Za-z0-9_]+)|\[([A-Za-z0-9_]+)\]", r"[^/]+", protected_route_pattern)
    route_matches = bool(re.fullmatch(regex_pat, effective_path))
    if route_matches and not payment_present:
        return GuardDecision(
            allowed=False,
            decision_code="X402_PARAMETERISED_ROUTE_UNPAID_BYPASS_BLOCKED",
            reason="x402 #3850: Request matched parameterised protected route without valid payment.",
            evidence={"protected_route_pattern": protected_route_pattern, "effective_path": effective_path},
        )

    client_path = urlsplit(siwx_client_resource_url).path
    server_path = urlsplit(server_canonical_url).path
    if client_path != server_path:
        return GuardDecision(
            allowed=False,
            decision_code="X402_SIWX_CLIENT_RESOURCE_URL_ENTITLEMENT_SPOOF_BLOCKED",
            reason="x402 #3838: SIWX settle hook MUST record entitlement under server-canonical request URL, rejecting mismatched client PaymentPayload.resource.url.",
            evidence={"client_resource_path": client_path, "server_canonical_path": server_path},
        )
    return GuardDecision(
        allowed=True,
        decision_code="X402_PAYWALL_ROUTE_AND_SIWX_ENTITLEMENT_VERIFIED",
        reason="Parameterised/Java route matching and server-canonical SIWX entitlement binding verified.",
        evidence={"effective_path": effective_path, "entitlement_path": server_path},
    )


# ---------------------------------------------------------------------------
# FX-04: x402 #3847 / #3547 / #3529 / #3515
# Fail-closed settledResponse recovery extension, Fastify raw stream & body
# parse hook ordering, and Stellar smart-account cross-contract fee ceiling
# ---------------------------------------------------------------------------
def evaluate_x402_recovery_fastify_and_stellar_smart_account_fee(
    *,
    is_retry_recovery: bool,
    settled_record: dict[str, Any] | None,
    current_request_digest: str,
    fastify_hook_stage: str,
    fastify_raw_hijacked_without_settle: bool,
    stellar_is_smart_account: bool,
    stellar_cross_contract_auth_calls: int,
    stellar_required_fee_stroops: int,
    facilitator_max_fee_stroops: int,
) -> GuardDecision:
    if is_retry_recovery:
        if not settled_record or not settled_record.get("settled") or settled_record.get("request_digest") != current_request_digest:
            return GuardDecision(
                allowed=False,
                decision_code="X402_RECOVERY_EXTENSION_FAIL_CLOSED_REJECTED",
                reason="x402 #3847: Retry recovery must fail closed when no matching settledResponse record and request_digest exist.",
                evidence={"settled_record": settled_record, "current_request_digest": current_request_digest},
            )
        if not settled_record.get("tx_hash") or not settled_record.get("evidence_projection"):
            return GuardDecision(
                allowed=False,
                decision_code="X402_RECOVERY_EVIDENCE_PROJECTION_MISSING",
                reason="x402 #3847: Recovery response must project declared settlement evidence (tx_hash + evidence_projection).",
                evidence={"settled_record": settled_record},
            )
    if fastify_hook_stage != "preHandler":
        return GuardDecision(
            allowed=False,
            decision_code="X402_FASTIFY_PRE_BODY_PARSE_HOOK_STAGE_BLOCKED",
            reason="x402 #3529: Fastify payment hook MUST run at preHandler (after body parsing) so JSON POST bodies are readable.",
            evidence={"fastify_hook_stage": fastify_hook_stage},
        )
    if fastify_raw_hijacked_without_settle:
        return GuardDecision(
            allowed=False,
            decision_code="X402_FASTIFY_RAW_END_WITHOUT_SETTLE_HANG_BLOCKED",
            reason="x402 #3547: Protected Fastify route using reply.raw.end() must complete settlement hook before raw stream termination.",
            evidence={},
        )
    min_safe_stellar_fee = 50_000 + (stellar_cross_contract_auth_calls * 100_000 if stellar_is_smart_account else 0)
    if facilitator_max_fee_stroops < min_safe_stellar_fee or stellar_required_fee_stroops > facilitator_max_fee_stroops:
        return GuardDecision(
            allowed=False,
            decision_code="X402_STELLAR_SMART_ACCOUNT_FEE_CEILING_TOO_LOW_BLOCKED",
            reason="x402 #3515: Facilitator maxTransactionFeeStroops must accommodate Stellar smart-account __check_auth cross-contract invocations.",
            evidence={
                "stellar_required_fee_stroops": stellar_required_fee_stroops,
                "facilitator_max_fee_stroops": facilitator_max_fee_stroops,
                "min_safe_stellar_fee": min_safe_stellar_fee,
            },
        )
    return GuardDecision(
        allowed=True,
        decision_code="X402_RECOVERY_FASTIFY_AND_STELLAR_FEE_VERIFIED",
        reason="Fail-closed retry recovery, Fastify preHandler/raw-stream completion, and Stellar smart-account fee ceiling verified.",
        evidence={"min_safe_stellar_fee": min_safe_stellar_fee},
    )


# ---------------------------------------------------------------------------
# FX-05: UCP #981 / #979 / #976
# Postal address line components, standardized fulfillment event types, and
# nested line-item bundle semantics (parent_id)
# ---------------------------------------------------------------------------
def evaluate_ucp_address_components_fulfillment_and_bundles(
    *,
    postal_address: dict[str, Any],
    fulfillment_event_type: str,
    line_items: list[dict[str, Any]],
    attempted_partial_component_cancel: bool = False,
) -> GuardDecision:
    components = postal_address.get("address_line_components")
    if components is not None:
        street_name = str(components.get("street_name") or "").strip()
        street_number = str(components.get("street_number") or "").strip()
        rendered_line1 = str(postal_address.get("address_line_1") or "").strip()
        if not street_name or not street_number or street_name not in rendered_line1 or street_number not in rendered_line1:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_ADDRESS_LINE_COMPONENTS_MISMATCH_BLOCKED",
                reason="UCP #981: address_line_components (street_name, street_number) must be non-empty and consistent with address_line_1.",
                evidence={"postal_address": postal_address},
            )
    if fulfillment_event_type not in STANDARD_UCP_FULFILLMENT_EVENTS:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_NON_STANDARD_FULFILLMENT_EVENT_TYPE_BLOCKED",
            reason="UCP #979: Order fulfillment event type must use standardized UCP enum values.",
            evidence={"fulfillment_event_type": fulfillment_event_type},
        )
    items_by_id = {str(it.get("id")): it for it in line_items if it.get("id")}
    children_by_parent: dict[str, list[dict[str, Any]]] = {}
    for it in line_items:
        pid = it.get("parent_id")
        if pid is not None:
            pid_str = str(pid)
            if pid_str not in items_by_id or pid_str == str(it.get("id")):
                return GuardDecision(
                    allowed=False,
                    decision_code="UCP_BUNDLE_ORPHAN_OR_SELF_PARENT_ID_BLOCKED",
                    reason="UCP #976: Bundle component line item parent_id must reference an existing top-level parent line item.",
                    evidence={"item": it},
                )
            if items_by_id[pid_str].get("parent_id") is not None:
                return GuardDecision(
                    allowed=False,
                    decision_code="UCP_BUNDLE_MULTI_LEVEL_NESTING_BLOCKED",
                    reason="UCP #976: Nested bundle line items cannot form cycles or arbitrary multi-level trees.",
                    evidence={"item": it},
                )
            children_by_parent.setdefault(pid_str, []).append(it)

    for pid_str, children in children_by_parent.items():
        parent = items_by_id[pid_str]
        if parent.get("is_atomic_bundle", True) and attempted_partial_component_cancel:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_ATOMIC_BUNDLE_PARTIAL_COMPONENT_CANCEL_BLOCKED",
                reason="UCP #976: Components of an atomic bundle cannot be individually canceled or refunded without the bundle parent.",
                evidence={"parent_id": pid_str},
            )
        comp_sum = sum(int(c.get("total_minor", 0)) for c in children)
        if int(parent.get("total_minor", 0)) != comp_sum:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_BUNDLE_COMPONENT_TOTAL_ROLLUP_MISMATCH",
                reason="UCP #976: Bundle parent total_minor must equal the sum of its nested component line items.",
                evidence={"parent_total": parent.get("total_minor"), "components_sum": comp_sum},
            )
    return GuardDecision(
        allowed=True,
        decision_code="UCP_ADDRESS_FULFILLMENT_AND_BUNDLE_SEMANTICS_VERIFIED",
        reason="Address line components, standardized fulfillment event type, and nested bundle semantics verified.",
        evidence={"fulfillment_event_type": fulfillment_event_type, "bundle_parents": list(children_by_parent.keys())},
    )


# ---------------------------------------------------------------------------
# FX-06: UCP #977 / #974 / #964 / #963
# Catalog similarity & substitute stock, food per-allergen safety against
# buyer dietary restrictions, and RFC 9421 §3.3.4/§3.3.5 ECDSA raw r||s
# ---------------------------------------------------------------------------
def evaluate_ucp_similarity_allergen_and_ecdsa_raw_rs(
    *,
    similarity_query: dict[str, Any],
    buyer_allergen_restrictions: list[str],
    dish_allergen_status: dict[str, str],
    ecdsa_curve: str,
    signature_bytes: bytes,
) -> GuardDecision:
    anchors = similarity_query.get("like", [])
    if not isinstance(anchors, list) or len(anchors) == 0 or len(anchors) > 10:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_CATALOG_SIMILARITY_ANCHOR_BOUNDS_INVALID",
            reason="UCP #977/#974: dev.ucp.shopping.catalog.similarity 'like' must contain between 1 and 10 product/variant anchors.",
            evidence={"anchor_count": len(anchors) if isinstance(anchors, list) else -1},
        )
    for sub in similarity_query.get("substitutes", []):
        if not sub.get("in_stock", False) or sub.get("id") in anchors:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_CATALOG_SUBSTITUTE_OUT_OF_STOCK_OR_SELF_ANCHOR_BLOCKED",
                reason="UCP #977/#974: Substitute candidates must be in stock and distinct from the queried anchor.",
                evidence={"invalid_substitute": sub},
            )
    for restricted in buyer_allergen_restrictions:
        status = dish_allergen_status.get(restricted, "unknown")
        if status != "free_from":
            return GuardDecision(
                allowed=False,
                decision_code="UCP_FOOD_ALLERGEN_UNSAFE_OR_UNKNOWN_FOR_BUYER_BLOCKED",
                reason="UCP #964: Dish with allergen status 'contains', 'may_contain', or 'unknown' MUST NOT be ordered for a buyer restricting that allergen.",
                evidence={"allergen": restricted, "dish_status": status},
            )
    expected_len = 64 if ecdsa_curve == "P-256" else (96 if ecdsa_curve == "P-384" else -1)
    # ASN.1 DER sequences start with 0x30 and have variable length (typically 70-72 bytes for P-256)
    if expected_len == -1 or len(signature_bytes) != expected_len or (signature_bytes and signature_bytes[0] == 0x30 and len(signature_bytes) != expected_len):
        return GuardDecision(
            allowed=False,
            decision_code="UCP_RFC9421_ECDSA_ASN1_DER_OR_INVALID_LENGTH_BLOCKED",
            reason="UCP #963: RFC 9421 §3.3.4/§3.3.5 requires fixed-width raw r||s concatenation (64B for P-256, 96B for P-384), rejecting ASN.1 DER.",
            evidence={"ecdsa_curve": ecdsa_curve, "signature_len": len(signature_bytes)},
        )
    return GuardDecision(
        allowed=True,
        decision_code="UCP_SIMILARITY_ALLERGEN_AND_ECDSA_RAW_RS_VERIFIED",
        reason="Catalog similarity substitutes, food per-allergen free_from guarantee, and RFC 9421 ECDSA raw r||s signature verified.",
        evidence={"ecdsa_curve": ecdsa_curve, "signature_len": len(signature_bytes)},
    )


# ---------------------------------------------------------------------------
# FX-07: UCP #951 / #948 / #862
# Standardized ad attribution dimensions, root-object schema anti-pattern
# check, and Nano (XNO) feeless payment instrument schema
# ---------------------------------------------------------------------------
def evaluate_ucp_ad_attribution_root_schema_and_nano_instrument(
    *,
    ad_attribution: dict[str, Any],
    extension_schema: dict[str, Any],
    nano_instrument: dict[str, Any],
) -> GuardDecision:
    forbidden_pii_keys = {"email", "phone", "raw_ip", "device_fingerprint_raw", "full_name"}
    if forbidden_pii_keys.intersection(ad_attribution.keys()):
        return GuardDecision(
            allowed=False,
            decision_code="UCP_AD_ATTRIBUTION_RAW_PII_LEAK_BLOCKED",
            reason="UCP #951: Advertising attribution dimensions must use opaque campaign/click tokens without raw buyer PII.",
            evidence={"leaked_keys": sorted(forbidden_pii_keys.intersection(ad_attribution.keys()))},
        )
    if not str(ad_attribution.get("campaign_id") or "").strip() or not str(ad_attribution.get("click_id") or "").strip():
        return GuardDecision(
            allowed=False,
            decision_code="UCP_AD_ATTRIBUTION_DIMENSIONS_INCOMPLETE",
            reason="UCP #951: Standardized ad attribution requires non-empty campaign_id and click_id.",
            evidence={"ad_attribution": ad_attribution},
        )
    if extension_schema.get("type") == "array":
        return GuardDecision(
            allowed=False,
            decision_code="UCP_ROOT_ARRAY_SCHEMA_ANTIPATTERN_BLOCKED",
            reason="UCP #948: Root-array JSON schemas are forbidden; top-level schema must be type 'object' to allow additive evolution.",
            evidence={"schema_type": extension_schema.get("type")},
        )
    acct = str(nano_instrument.get("account") or "")
    blk = str(nano_instrument.get("block_hash") or "")
    amt_raw = str(nano_instrument.get("amount_raw") or "")
    work = str(nano_instrument.get("work_nonce") or "")
    if (
        nano_instrument.get("type") != "nano"
        or not NANO_ACCOUNT_RE.match(acct)
        or not HEX64_RE.match(blk)
        or not amt_raw.isdigit()
        or int(amt_raw) <= 0
        or not HEX16_RE.match(work)
    ):
        return GuardDecision(
            allowed=False,
            decision_code="UCP_NANO_PAYMENT_INSTRUMENT_SCHEMA_INVALID",
            reason="UCP #862: Nano (XNO) payment instrument requires valid nano_ address, 64-hex block_hash, positive integer amount_raw, and 16-hex work_nonce.",
            evidence={"nano_instrument": nano_instrument},
        )
    return GuardDecision(
        allowed=True,
        decision_code="UCP_AD_ATTRIBUTION_ROOT_OBJECT_AND_NANO_VERIFIED",
        reason="Privacy-safe ad attribution, root-object schema envelope, and Nano (XNO) payment instrument verified.",
        evidence={"nano_account": acct},
    )


# ---------------------------------------------------------------------------
# FX-08: UCP #857 / #852 / #846 / #824
# Payment Terms empty-payment guard on /complete, attestation-based platform
# client auth for first-contact IdP chaining, mutation admission evidence,
# and product option selection/quantity rules
# ---------------------------------------------------------------------------
def evaluate_ucp_payment_terms_idp_attestation_and_option_rules(
    *,
    complete_payment_obj: dict[str, Any],
    payment_terms_active: bool,
    first_contact_idp_headers: dict[str, str],
    mutation_admission: dict[str, Any],
    option_selection: dict[str, Any],
) -> GuardDecision:
    if not complete_payment_obj or (
        not complete_payment_obj.get("instruments")
        and not (payment_terms_active and complete_payment_obj.get("selected_term_id") and complete_payment_obj.get("credit_agreement_id"))
    ):
        return GuardDecision(
            allowed=False,
            decision_code="UCP_COMPLETE_EMPTY_PAYMENT_OBJECT_BLOCKED",
            reason="UCP #857: Checkout /complete MUST NOT accept an empty payment: {} object without instruments[] or a bound credit agreement + selected_term_id.",
            evidence={"complete_payment_obj": complete_payment_obj},
        )
    att = first_contact_idp_headers.get("OAuth-Client-Attestation", "").strip()
    pop = first_contact_idp_headers.get("OAuth-Client-Attestation-PoP", "").strip()
    if len(att.split(".")) != 3 or len(pop.split(".")) != 3:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_FIRST_CONTACT_IDP_CLIENT_ATTESTATION_MISSING",
            reason="UCP #852: First-contact Accelerated IdP token exchange requires 3-segment OAuth-Client-Attestation and OAuth-Client-Attestation-PoP JWTs.",
            evidence={"headers": list(first_contact_idp_headers.keys())},
        )
    if not mutation_admission.get("admission_coverage_hash") or not mutation_admission.get("satisfaction_proof"):
        return GuardDecision(
            allowed=False,
            decision_code="UCP_MUTATION_ADMISSION_SATISFACTION_EVIDENCE_MISSING",
            reason="UCP #846: Agent-initiated transaction changes require admission_coverage_hash and satisfaction_proof.",
            evidence={"mutation_admission": mutation_admission},
        )
    min_sel = int(option_selection.get("min_selected", 0))
    max_sel = int(option_selection.get("max_selected", 1))
    chosen = option_selection.get("selected_values", [])
    if len(chosen) < min_sel or len(chosen) > max_sel:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_PRODUCT_OPTION_SELECTION_COUNT_VIOLATION",
            reason="UCP #824: Selected product option count violates [min_selected, max_selected] rule.",
            evidence={"selected_count": len(chosen), "min_selected": min_sel, "max_selected": max_sel},
        )
    for val in chosen:
        qty = int(val.get("quantity", 1))
        max_q = int(val.get("max_quantity", 1))
        if qty < 1 or qty > max_q:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_PRODUCT_OPTION_VALUE_QUANTITY_VIOLATION",
                reason="UCP #824: Option value quantity violates per-option quantity rule.",
                evidence={"option_value": val},
            )
    return GuardDecision(
        allowed=True,
        decision_code="UCP_PAYMENT_TERMS_IDP_AND_OPTION_RULES_VERIFIED",
        reason="Non-empty /complete payment, first-contact IdP client attestation, mutation admission evidence, and option rules verified.",
        evidence={"selected_term_id": complete_payment_obj.get("selected_term_id")},
    )


# ---------------------------------------------------------------------------
# FX-09: ACP #315 / #314 / #297 / #296
# Ephemeral agent identity for unregistered merchants, host-side spend
# authorization, OpenAPI 6-field parity, and MCP checkout idempotency_key
# ---------------------------------------------------------------------------
def evaluate_acp_agent_identity_host_auth_and_mcp_idempotency(
    *,
    merchant_has_stored_agent_id: bool,
    ephemeral_agent_attestation_jws: str | None,
    host_authorization: dict[str, Any] | None,
    checkout_session_id: str,
    spend_amount_minor: int,
    openapi_declared_fields: set[str],
    mcp_tool_name: str,
    mcp_meta: dict[str, Any],
) -> GuardDecision:
    if not merchant_has_stored_agent_id:
        if not ephemeral_agent_attestation_jws or len(ephemeral_agent_attestation_jws.split(".")) != 3:
            return GuardDecision(
                allowed=False,
                decision_code="ACP_UNREGISTERED_MERCHANT_AGENT_ATTESTATION_MISSING",
                reason="ACP #315: When merchant has no stored agent identity, request must carry a verifiable 3-segment ephemeral agent identity JWS.",
                evidence={"merchant_has_stored_agent_id": merchant_has_stored_agent_id},
            )
    if (
        not host_authorization
        or host_authorization.get("checkout_session_id") != checkout_session_id
        or int(host_authorization.get("max_amount_minor", -1)) < spend_amount_minor
        or not host_authorization.get("signature_valid", False)
    ):
        return GuardDecision(
            allowed=False,
            decision_code="ACP_HOST_SIDE_SPEND_AUTHORIZATION_INVALID",
            reason="ACP #314: Spend step requires valid host-side authorization bound to checkout_session_id and covering spend_amount_minor.",
            evidence={"host_authorization": host_authorization, "spend_amount_minor": spend_amount_minor},
        )
    missing_parity = ACP_OPENAPI_REQUIRED_PARITY_FIELDS - openapi_declared_fields
    if missing_parity:
        return GuardDecision(
            allowed=False,
            decision_code="ACP_OPENAPI_JSON_SCHEMA_SIX_FIELD_DRIFT_BLOCKED",
            reason="ACP #297: openapi.agentic_checkout.yaml must declare all 6 fields present in schema.agentic_checkout.json.",
            evidence={"missing_fields": sorted(missing_parity)},
        )
    mutating_mcp_tools = {"checkout.create", "checkout.update", "checkout.complete", "checkout.cancel"}
    if mcp_tool_name in mutating_mcp_tools:
        idem = str(mcp_meta.get("idempotency_key") or "").strip()
        if len(idem) < 16:
            return GuardDecision(
                allowed=False,
                decision_code="ACP_MCP_MUTATING_CHECKOUT_IDEMPOTENCY_KEY_MISSING",
                reason="ACP #296: Mutating MCP checkout tools (create/update/complete/cancel) MUST include meta.idempotency_key.",
                evidence={"mcp_tool_name": mcp_tool_name, "mcp_meta": mcp_meta},
            )
    return GuardDecision(
        allowed=True,
        decision_code="ACP_AGENT_IDENTITY_HOST_AUTH_AND_MCP_IDEMPOTENCY_VERIFIED",
        reason="Ephemeral agent identity, host-side spend attestation, OpenAPI 6-field parity, and MCP idempotency_key verified.",
        evidence={"checkout_session_id": checkout_session_id},
    )


# ---------------------------------------------------------------------------
# FX-10: ACP #294 / #292 / #288 / #287 / #285 / #280
# Mandatory Signature + Timestamp freshness across mutating REST & delegate
# endpoints, 3DS AuthenticationResult term binding, and canonical Item.url
# ---------------------------------------------------------------------------
def evaluate_acp_signature_freshness_3ds_binding_and_item_url(
    *,
    endpoint_name: str,
    signature_header: str | None,
    timestamp_epoch_s: int | None,
    now_epoch_s: int,
    auth_result: dict[str, Any],
    final_terms: dict[str, Any],
    item_url: str | None,
) -> GuardDecision:
    if not signature_header or timestamp_epoch_s is None or abs(now_epoch_s - timestamp_epoch_s) > 300:
        return GuardDecision(
            allowed=False,
            decision_code="ACP_MUTATING_OR_DELEGATE_SIGNATURE_TIMESTAMP_MISSING_OR_STALE",
            reason="ACP #294/#288/#287/#285: Mutating Checkout, delegate_payment, and delegate_authentication requests MUST include detached Signature and fresh Timestamp (<= 300s).",
            evidence={"endpoint_name": endpoint_name, "timestamp_epoch_s": timestamp_epoch_s, "now_epoch_s": now_epoch_s},
        )
    for field in ("checkout_session_id", "merchant_id", "amount_minor", "currency", "acquirer_bin"):
        if auth_result.get(field) != final_terms.get(field):
            return GuardDecision(
                allowed=False,
                decision_code="ACP_DELEGATE_AUTH_RESULT_FINAL_TERMS_MISMATCH_BLOCKED",
                reason=f"ACP #292: 3DS AuthenticationResult '{field}' is not bound to the final authorization terms.",
                evidence={"field": field, "auth_result_val": auth_result.get(field), "final_terms_val": final_terms.get(field)},
            )
    if auth_result.get("used", False) or int(auth_result.get("expires_at", 0)) <= now_epoch_s:
        return GuardDecision(
            allowed=False,
            decision_code="ACP_DELEGATE_AUTH_RESULT_EXPIRED_OR_REPLAYED_BLOCKED",
            reason="ACP #292: 3DS AuthenticationResult is expired or already consumed.",
            evidence={"used": auth_result.get("used"), "expires_at": auth_result.get("expires_at")},
        )
    if item_url is not None:
        parts = urlsplit(item_url)
        if parts.scheme != "https" or not parts.netloc or ".." in parts.path:
            return GuardDecision(
                allowed=False,
                decision_code="ACP_CHECKOUT_ITEM_URL_NON_HTTPS_OR_INVALID_BLOCKED",
                reason="ACP #280: Optional Item.url on checkout line items must be a canonical https:// product page URL.",
                evidence={"item_url": item_url},
            )
    return GuardDecision(
        allowed=True,
        decision_code="ACP_SIGNATURE_FRESHNESS_3DS_BINDING_AND_ITEM_URL_VERIFIED",
        reason="Detached Signature/Timestamp freshness, 3DS AuthenticationResult term binding, and https:// Item.url verified.",
        evidence={"endpoint_name": endpoint_name, "checkout_session_id": final_terms.get("checkout_session_id")},
    )


# ---------------------------------------------------------------------------
# FX-11: Google AP2 #384 / #381 / #380 / #365 / #364
# ReceiptClient optional callback & EC public key normalization, delivery
# destination constraint in mandate, OpenID4VP draft shape, and log redaction
# ---------------------------------------------------------------------------
def evaluate_ap2_receipt_verifier_delivery_constraint_and_openid4vp(
    *,
    receipt_key_type: str,
    has_reference_in_store_cb: Any | None,
    receipt_reference_id: str,
    mandate_delivery_constraint: dict[str, str],
    checkout_delivery: dict[str, str],
    openid4vp_request: dict[str, Any],
    sample_log_line: str,
) -> GuardDecision:
    if receipt_key_type not in {"JWK", "EllipticCurvePublicKey"}:
        return GuardDecision(
            allowed=False,
            decision_code="AP2_RECEIPT_UNSUPPORTED_PUBLIC_KEY_TYPE",
            reason="AP2 #365: ReceiptClient.verify_receipt must normalize declared EllipticCurvePublicKey via JWK.from_pyca or accept JWK.",
            evidence={"receipt_key_type": receipt_key_type},
        )
    # Safe optional callback invocation (#384)
    if callable(has_reference_in_store_cb) and not has_reference_in_store_cb(receipt_reference_id):
        return GuardDecision(
            allowed=False,
            decision_code="AP2_RECEIPT_REFERENCE_NOT_IN_STORE_BLOCKED",
            reason="AP2 #384: Receipt reference failed caller-supplied has_reference_in_store_cb check.",
            evidence={"receipt_reference_id": receipt_reference_id},
        )
    for k in ("ship_to_address_hash", "delivery_email_hash"):
        expected = mandate_delivery_constraint.get(k)
        actual = checkout_delivery.get(k)
        if not expected or expected != actual:
            return GuardDecision(
                allowed=False,
                decision_code="AP2_MANDATE_DELIVERY_DESTINATION_REDIRECT_BLOCKED",
                reason=f"AP2 #381: Checkout delivery destination '{k}' violates the signed mandate's delivery constraint.",
                evidence={"field": k, "expected": expected, "actual": actual},
            )
    if "dcql_query" not in openid4vp_request or "transaction_data" not in openid4vp_request or "presentation_definition" in openid4vp_request:
        return GuardDecision(
            allowed=False,
            decision_code="AP2_OPENID4VP_LEGACY_SHAPE_DRIFT_BLOCKED",
            reason="AP2 #380: OpenID4VP delegation request must align with Delegate SD-JWT draft (dcql_query + transaction_data, not legacy presentation_definition).",
            evidence={"openid4vp_keys": sorted(openid4vp_request.keys())},
        )
    sensitive_markers = ("sd_jwt=", "payment_mandate_raw", "card_number", "cvv", "private_key")
    if any(m in sample_log_line for m in sensitive_markers):
        return GuardDecision(
            allowed=False,
            decision_code="AP2_PLAINTEXT_PAYMENT_ARTIFACT_LOGGING_BLOCKED",
            reason="AP2 #364: A2A and MCP middleware/samples must never write raw payment mandates or credentials to plaintext logs.",
            evidence={"sample_log_line": sample_log_line},
        )
    return GuardDecision(
        allowed=True,
        decision_code="AP2_RECEIPT_DELIVERY_OPENID4VP_AND_LOG_REDACTION_VERIFIED",
        reason="ReceiptClient optional callback/EC key normalization, delivery destination binding, OpenID4VP draft shape, and log redaction verified.",
        evidence={"receipt_reference_id": receipt_reference_id},
    )


# ---------------------------------------------------------------------------
# FX-12: Google AP2 #368 / #363 / #359 / #319
# ISO 4217 currency-exponent Decimal minor-unit budget cap, multi-hop SD-JWT
# terminal-hop isolation, CheckoutMandateChain.verify checkout_hash binding,
# and terminal KB-SD-JWT mandatory aud + nonce check
# ---------------------------------------------------------------------------
def evaluate_ap2_iso4217_budget_multihop_and_kb_sdjwt(
    *,
    currency: str,
    budget_max_major: str | float,
    requested_amount_minor: int,
    sd_jwt_chain: str,
    presented_checkout_jwt: str,
    closed_mandate_checkout_hash: str,
    terminal_kb_payload: dict[str, Any],
    expected_aud: str,
    expected_nonce: str,
) -> GuardDecision:
    if currency not in ISO4217_EXPONENTS:
        return GuardDecision(
            allowed=False,
            decision_code="AP2_BUDGET_UNKNOWN_ISO4217_CURRENCY_BLOCKED",
            reason="AP2 #368: BudgetEvaluator requires a known ISO 4217 currency exponent.",
            evidence={"currency": currency},
        )
    exp = ISO4217_EXPONENTS[currency]
    try:
        dec_max = Decimal(str(budget_max_major))
    except InvalidOperation:
        return GuardDecision(
            allowed=False,
            decision_code="AP2_BUDGET_INVALID_DECIMAL_MAX",
            reason="AP2 #368: budget.max must be a valid decimal number.",
            evidence={"budget_max_major": budget_max_major},
        )
    scale = Decimal(10) ** exp
    exact_scaled = dec_max * scale
    if exact_scaled != exact_scaled.to_integral_value():
        return GuardDecision(
            allowed=False,
            decision_code="AP2_BUDGET_SUB_MINOR_UNIT_PRECISION_BLOCKED",
            reason="AP2 #368: budget.max has more fractional digits than the ISO 4217 currency exponent allows.",
            evidence={"currency": currency, "exponent": exp, "budget_max_major": str(budget_max_major)},
        )
    cap_minor = int(exact_scaled)
    if requested_amount_minor > cap_minor:
        return GuardDecision(
            allowed=False,
            decision_code="AP2_BUDGET_ISO4217_MINOR_CAP_EXCEEDED_BLOCKED",
            reason="AP2 #368: Requested amount in minor units exceeds the exact ISO 4217 currency-exponent budget cap.",
            evidence={"currency": currency, "cap_minor": cap_minor, "requested_amount_minor": requested_amount_minor},
        )
    hops = [h for h in sd_jwt_chain.split("~~") if h.strip()]
    if len(hops) < 1 or any(len(h.split("~")[0].split(".")) != 3 for h in hops):
        return GuardDecision(
            allowed=False,
            decision_code="AP2_MULTIHOP_SDJWT_CHAIN_MALFORMED_BLOCKED",
            reason="AP2 #363: MandateClient.present() requires well-formed '~~'-delimited SD-JWT delegation hops.",
            evidence={"hop_count": len(hops)},
        )
    derived_checkout_hash = _b64u_sha256_ascii(presented_checkout_jwt)
    if derived_checkout_hash != closed_mandate_checkout_hash:
        return GuardDecision(
            allowed=False,
            decision_code="AP2_CLOSED_CHECKOUT_MANDATE_HASH_MISMATCH_BLOCKED",
            reason="AP2 #359: CheckoutMandateChain.verify MUST derive B64U(SHA-256(ASCII(checkout_jwt))) and match closed mandate checkout_hash.",
            evidence={"derived_checkout_hash": derived_checkout_hash, "closed_mandate_checkout_hash": closed_mandate_checkout_hash},
        )
    aud = str(terminal_kb_payload.get("aud") or "").strip()
    nonce = str(terminal_kb_payload.get("nonce") or "").strip()
    if not aud or not nonce or aud != expected_aud or nonce != expected_nonce:
        return GuardDecision(
            allowed=False,
            decision_code="AP2_TERMINAL_KB_SDJWT_MISSING_OR_MISMATCHED_AUD_NONCE_BLOCKED",
            reason="AP2 #319: Terminal KB-SD-JWT verifier MUST reject tokens missing aud or nonce or mismatching expected values.",
            evidence={"aud": aud, "nonce": nonce},
        )
    return GuardDecision(
        allowed=True,
        decision_code="AP2_ISO4217_BUDGET_MULTIHOP_AND_KB_SDJWT_VERIFIED",
        reason="Exact ISO 4217 Decimal budget cap, multi-hop SD-JWT isolation, closed checkout_hash binding, and KB-SD-JWT aud/nonce verified.",
        evidence={"currency": currency, "cap_minor": cap_minor, "hop_count": len(hops)},
    )


# ---------------------------------------------------------------------------
# FX-13: MCP #3431 / #3430 / #3427 / #3413
# Local MCP server npx pinning, server-level routing description for lazy
# tool loading, serveStdio transport parity, and OAuth token audience scope
# ---------------------------------------------------------------------------
def evaluate_mcp_supply_chain_routing_and_token_privilege(
    *,
    command_args: list[str],
    package_integrity_sha512: str | None,
    server_info: dict[str, Any],
    transport_mode: str,
    access_token_claims: dict[str, Any],
    mcp_server_resource_uri: str,
) -> GuardDecision:
    if "npx" in command_args and "-y" in command_args:
        pkg_specs = [a for a in command_args if not a.startswith("-") and a != "npx"]
        has_exact_pin = any(re.search(r"@\d+\.\d+\.\d+$", p) for p in pkg_specs)
        if not has_exact_pin or not package_integrity_sha512 or not package_integrity_sha512.startswith("sha512-"):
            return GuardDecision(
                allowed=False,
                decision_code="MCP_UNPINNED_NPX_AUTO_INSTALL_SUPPLY_CHAIN_BLOCKED",
                reason="MCP #3431: Local MCP server config MUST NOT use unpinned 'npx -y' without exact semver @x.y.z and sha512 integrity digest.",
                evidence={"command_args": command_args, "package_integrity_sha512": package_integrity_sha512},
            )
    routing_desc = str(server_info.get("description") or "").strip()
    if len(routing_desc) < 20 or not server_info.get("domain_tags"):
        return GuardDecision(
            allowed=False,
            decision_code="MCP_SERVER_LEVEL_ROUTING_DESCRIPTION_MISSING",
            reason="MCP #3430: Server initialization must provide non-trivial serverInfo.description and domain_tags for deferred/lazy tool routing.",
            evidence={"server_info": server_info},
        )
    if transport_mode not in {"serveStdio", "streamableHttp"}:
        return GuardDecision(
            allowed=False,
            decision_code="MCP_LEGACY_DISCONNECTED_QUICKSTART_TRANSPORT_BLOCKED",
            reason="MCP #3427/#3422: 2026-07-28 MCP server must bind serveStdio or streamableHttp transport.",
            evidence={"transport_mode": transport_mode},
        )
    token_aud = access_token_claims.get("aud")
    if token_aud != mcp_server_resource_uri or access_token_claims.get("is_passthrough_project_token", False):
        return GuardDecision(
            allowed=False,
            decision_code="MCP_ACCESS_TOKEN_PRIVILEGE_PASSTHROUGH_BLOCKED",
            reason="MCP #3413: Access token MUST be audience-restricted to the exact MCP server resource URI and never passed through across project APIs.",
            evidence={"token_aud": token_aud, "mcp_server_resource_uri": mcp_server_resource_uri},
        )
    return GuardDecision(
        allowed=True,
        decision_code="MCP_SUPPLY_CHAIN_ROUTING_AND_TOKEN_PRIVILEGE_VERIFIED",
        reason="Pinned MCP package execution, server-level routing description, serveStdio transport, and strict token audience verified.",
        evidence={"mcp_server_resource_uri": mcp_server_resource_uri},
    )


# ---------------------------------------------------------------------------
# FX-14: Stripe AI #581 / #580 / #569 / #546 / #528 / #526 / #524
# Worker-thread event-loop-safe StripeTool._run, host-side ACTION attestation
# for mutating pay tools, neutral provider routing, and requirement-scoped Connect
# ---------------------------------------------------------------------------
def evaluate_stripe_worker_thread_loop_and_host_action_gate(
    *,
    in_worker_thread_without_loop: bool,
    uses_get_event_loop_directly: bool,
    tool_name: str,
    is_mutating_pay_tool: bool,
    host_action_attestation: dict[str, Any] | None,
    enforces_mandatory_stripe_first_directory: bool,
    user_requested_connect_or_billing: bool,
    injected_unsolicited_connect_sequencing: bool,
) -> GuardDecision:
    if in_worker_thread_without_loop and uses_get_event_loop_directly:
        return GuardDecision(
            allowed=False,
            decision_code="STRIPE_WORKER_THREAD_NO_CURRENT_EVENT_LOOP_CRASH_BLOCKED",
            reason="Stripe #581/#580: StripeTool._run must fall back to an isolated event loop on worker threads instead of calling asyncio.get_event_loop().",
            evidence={"tool_name": tool_name},
        )
    if is_mutating_pay_tool:
        if not host_action_attestation or host_action_attestation.get("decision") != "ALLOW" or host_action_attestation.get("tool") != tool_name:
            return GuardDecision(
                allowed=False,
                decision_code="STRIPE_MUTATING_PAY_TOOL_HOST_ACTION_ATTESTATION_MISSING",
                reason="Stripe #528: Mutating Agent Toolkit pay tools require an explicit ALLOW host-side ACTION attestation.",
                evidence={"tool_name": tool_name, "host_action_attestation": host_action_attestation},
            )
    if enforces_mandatory_stripe_first_directory:
        return GuardDecision(
            allowed=False,
            decision_code="STRIPE_MANDATORY_DIRECTORY_PREEMPTION_BLOCKED",
            reason="Stripe #546: Payment plugin must not preempt general web search or non-Stripe vendor lookup with mandatory Stripe Directory routing.",
            evidence={},
        )
    if not user_requested_connect_or_billing and injected_unsolicited_connect_sequencing:
        return GuardDecision(
            allowed=False,
            decision_code="STRIPE_UNSOLICITED_CONNECT_BILLING_EXPANSION_BLOCKED",
            reason="Stripe #524: Connect sequencing and Billing recommendations must be scoped strictly to user requirements.",
            evidence={},
        )
    return GuardDecision(
        allowed=True,
        decision_code="STRIPE_WORKER_LOOP_AND_HOST_ACTION_GATE_VERIFIED",
        reason="Worker-thread event-loop safety, host ACTION pay-tool attestation, neutral vendor lookup, and requirement-scoped skills verified.",
        evidence={"tool_name": tool_name},
    )


# ---------------------------------------------------------------------------
# FX-15: Visa TAP #22 / #20 / #14 / #13 / #9 / #3
# mTLS client cert + RFC 9421 binding, W3C DID + Agent Passport attribution,
# nonce replay cache, and post-identity correctness/dispute primitive
# ---------------------------------------------------------------------------
def evaluate_visa_tap_mtls_passport_and_correctness_receipt(
    *,
    mtls_cert_thumbprint_s256: str | None,
    rfc9421_key_bound_thumbprint: str | None,
    agent_passport: dict[str, Any],
    nonce: str,
    seen_nonces: set[str],
    correctness_commitment: dict[str, Any],
    cors_allow_origins: list[str],
) -> GuardDecision:
    if not mtls_cert_thumbprint_s256 or mtls_cert_thumbprint_s256 != rfc9421_key_bound_thumbprint:
        return GuardDecision(
            allowed=False,
            decision_code="VISA_TAP_MTLS_CLIENT_CERT_BINDING_MISMATCH_BLOCKED",
            reason="Visa TAP #9: mTLS client certificate thumbprint must match the RFC 9421 signing key binding.",
            evidence={"mtls_cert": mtls_cert_thumbprint_s256, "bound_cert": rfc9421_key_bound_thumbprint},
        )
    if not nonce or len(nonce) < 16 or nonce in seen_nonces:
        return GuardDecision(
            allowed=False,
            decision_code="VISA_TAP_NONCE_REPLAY_OR_LOW_ENTROPY_BLOCKED",
            reason="Visa TAP #3: Request nonce must have >=16 chars and must not appear in the replay cache.",
            evidence={"nonce": nonce},
        )
    agent_did = str(agent_passport.get("agent_did") or "")
    values_hash = str(agent_passport.get("values_commitment_hash") or "")
    if not agent_did.startswith("did:") or not values_hash:
        return GuardDecision(
            allowed=False,
            decision_code="VISA_TAP_AGENT_PASSPORT_DID_OR_VALUES_MISSING",
            reason="Visa TAP #14/#13: Agent Passport must carry a verifiable W3C DID and values_commitment_hash attribution.",
            evidence={"agent_passport": agent_passport},
        )
    if not correctness_commitment.get("order_spec_hash") or not correctness_commitment.get("dispute_arbitration_uri"):
        return GuardDecision(
            allowed=False,
            decision_code="VISA_TAP_POST_IDENTITY_CORRECTNESS_LAYER_MISSING",
            reason="Visa TAP #22: Post-identity transaction envelope requires order_spec_hash and dispute_arbitration_uri.",
            evidence={"correctness_commitment": correctness_commitment},
        )
    if len(cors_allow_origins) != len(set(cors_allow_origins)):
        return GuardDecision(
            allowed=False,
            decision_code="VISA_TAP_DUPLICATE_CORS_ORIGIN_CONFIG_BLOCKED",
            reason="Visa TAP #20: Merchant CORS allow_origins configuration must not contain duplicate origin entries.",
            evidence={"cors_allow_origins": cors_allow_origins},
        )
    return GuardDecision(
        allowed=True,
        decision_code="VISA_TAP_MTLS_PASSPORT_AND_CORRECTNESS_VERIFIED",
        reason="Visa TAP mTLS binding, nonce replay defense, W3C DID Agent Passport, and post-identity correctness receipt verified.",
        evidence={"agent_did": agent_did, "nonce": nonce},
    )


# ---------------------------------------------------------------------------
# FX-16: Sierra tau2-bench #662 / #661 / #660 / #659 / #658 / #646
# Airline <=3h layover-inclusive upgrade filter, telecom unpaid/ended-contract
# resume_line block, retail self-exchange rejection, non-empty MMSC URL,
# 1-to-1 repeated gold action matching, and sealed DB state reward verification
# ---------------------------------------------------------------------------
def evaluate_tau2_airline_telecom_retail_and_reward_integrity(
    *,
    flight_total_duration_minutes: int,
    max_upgrade_duration_minutes: int,
    requested_flight_upgrade: bool,
    telecom_line_state: dict[str, Any],
    called_resume_line: bool,
    retail_exchange_old_item_id: str,
    retail_exchange_new_item_id: str,
    apn_mmsc_url: str | None,
    gold_action_counts: dict[str, int],
    agent_action_counts: dict[str, int],
    reward_from_live_env_hash: bool,
) -> GuardDecision:
    if requested_flight_upgrade and flight_total_duration_minutes > max_upgrade_duration_minutes:
        return GuardDecision(
            allowed=False,
            decision_code="TAU2_AIRLINE_DURATION_INCLUDING_LAYOVER_EXCEEDED_BLOCKED",
            reason="tau2-bench #662: Airline upgrade must be rejected when total duration including layovers exceeds user threshold (e.g. 7h > 3h in task_44).",
            evidence={
                "flight_total_duration_minutes": flight_total_duration_minutes,
                "max_upgrade_duration_minutes": max_upgrade_duration_minutes,
            },
        )
    if called_resume_line and (telecom_line_state.get("overdue_bill_unpaid") or telecom_line_state.get("contract_ended")):
        return GuardDecision(
            allowed=False,
            decision_code="TAU2_TELECOM_RESUME_LINE_ON_UNPAID_OR_ENDED_CONTRACT_BLOCKED",
            reason="tau2-bench #661: resume_line is forbidden on a suspended line with an unpaid overdue bill or ended contract.",
            evidence={"telecom_line_state": telecom_line_state},
        )
    if retail_exchange_old_item_id == retail_exchange_new_item_id:
        return GuardDecision(
            allowed=False,
            decision_code="TAU2_RETAIL_DELIVERED_SELF_EXCHANGE_BLOCKED",
            reason="tau2-bench #660: exchange_delivered_order_items must reject exchanging an item for itself (new_item_id == item_id).",
            evidence={"item_id": retail_exchange_old_item_id},
        )
    if apn_mmsc_url is None or not apn_mmsc_url.strip():
        return GuardDecision(
            allowed=False,
            decision_code="TAU2_TELECOM_EMPTY_MMSC_URL_TREATED_AS_UNCONFIGURED",
            reason="tau2-bench #659: can_send_mms must treat an empty or whitespace MMSC URL as unconfigured.",
            evidence={"apn_mmsc_url": apn_mmsc_url},
        )
    for act, required_n in gold_action_counts.items():
        if int(agent_action_counts.get(act, 0)) < required_n:
            return GuardDecision(
                allowed=False,
                decision_code="TAU2_GOLD_ACTION_CARDINALITY_UNDERCOUNT_BLOCKED",
                reason="tau2-bench #658: A single tool call cannot satisfy a gold action listed N times; 1-to-1 consumption matching required.",
                evidence={"action": act, "required": required_n, "actual": agent_action_counts.get(act, 0)},
            )
    if not reward_from_live_env_hash:
        return GuardDecision(
            allowed=False,
            decision_code="TAU2_PUBLIC_ANSWER_KEY_OFFLINE_REWARD_MINTING_BLOCKED",
            reason="tau2-bench #646: Evaluation reward must verify live environment state transitions rather than narrative/public answer-key replay.",
            evidence={"reward_from_live_env_hash": reward_from_live_env_hash},
        )
    return GuardDecision(
        allowed=True,
        decision_code="TAU2_AIRLINE_TELECOM_RETAIL_AND_REWARD_INTEGRITY_VERIFIED",
        reason="Airline layover-inclusive duration, telecom suspension gate, retail distinct-item exchange, MMSC check, 1-to-1 action cardinality, and live-env reward verified.",
        evidence={"flight_total_duration_minutes": flight_total_duration_minutes},
    )
