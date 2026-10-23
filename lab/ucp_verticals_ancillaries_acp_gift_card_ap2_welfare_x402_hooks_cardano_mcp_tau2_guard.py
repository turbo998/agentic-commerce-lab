"""Stage 208 deterministic protocol & security guardrails (2026-10-23).

Covers 16 primary-source upstream issues and PRs across UCP, ACP, AP2, x402, MCP, and Sierra tau2-bench:
- PR-01: Universal-Commerce-Protocol/ucp#723 & #721 (Domain vertical hierarchy & capability registry object map)
- PR-02: Universal-Commerce-Protocol/ucp#754 & #422 (Shipping discount double-count guard & get_order 200 signature headers)
- PR-03: Universal-Commerce-Protocol/ucp#400 & #205 (Structured Product/Variant attributes & single-type capability.extends array)
- PR-04: Universal-Commerce-Protocol/ucp#186 & #185 (Shopping Checkout Ancillaries Extension & OpenAttribution telemetry citations)
- PR-05: agentic-commerce-protocol/agentic-commerce-protocol#107 & #47 (Universal Product Types & multi-location merchant feeds)
- PR-06: agentic-commerce-protocol/agentic-commerce-protocol#61 & #9 (Merchant-issued GiftCard sourceType & 8-digit IIN validation)
- PR-07: google-agentic-commerce/AP2#172 & #134 (Project Mulberry Social Welfare Mandates & ETag 304 Discovery Layer polling)
- PR-08: x402-foundation/x402#3703 & #3852 (Client hook invocation correlation/abort release & x402-paywall Reflected XSS escaping)
- PR-09: x402-foundation/x402#3694 & #3678 (ERC-8183 job-escrow evaluation state machine & ext-delivery conformance evidence)
- PR-10: x402-foundation/x402#3673 & #3659 (Cardano raw signed CBOR preservation & rejection of Sui BCS payload examples)
- PR-11: x402-foundation/x402#3646 & #3644 (agreement-session terms-bound lifecycle & Go SVM confirmed on-chain failure classification)
- PR-12: x402-foundation/x402#3896 & #3641 (solidarity owner-consented humanitarian share & payment-backed reviews verification)
- PR-13: modelcontextprotocol/modelcontextprotocol#3003 & #2601 (Tool execution error structuredContent & uriTemplate uniqueness)
- PR-14: modelcontextprotocol/modelcontextprotocol#3025 & #3024 (Tool side-effect classification & server manifest capability trust tiers)
- PR-15: sierra-research/tau2-bench#182 & #172 (Retail confirmation premature-stop guard & Airline extra-passenger hallucination block)
- PR-16: sierra-research/tau2-bench#373 & #169 (Banking doc _009 unrequested referral prohibition & OpenAI tool_calls schema compliance)
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class GuardDecision:
    admitted: bool
    decision_code: str
    reason: str
    Metadata: Mapping[str, Any] | None = None


_VERTICAL_PREFIXES = ("source/schemas/shopping/", "source/schemas/payment/", "source/schemas/common/")
_REV_DOMAIN_RE = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+){2,}$")
_HEX_RE = re.compile(r"^[0-9a-fA-F]+$")
_TRUST_TIER_ORDER = {
    "unverified": 0,
    "domain_verified": 1,
    "hardware_attested": 2,
    "regulated_financial": 3,
}


# PR-01: UCP #723 & #721
def audit_ucp_vertical_hierarchy_and_capability_registry_map(
    payload: Mapping[str, Any],
) -> GuardDecision:
    schema_paths = payload.get("schema_paths")
    capabilities = payload.get("ucp_capabilities")
    if not isinstance(schema_paths, Sequence) or isinstance(schema_paths, (str, bytes)) or len(schema_paths) == 0:
        return GuardDecision(
            False,
            "UCP_CAPABILITY_REGISTRY_ARRAY_OR_FLAT_VERTICAL_PATH_BLOCKED",
            "schema_paths must be a non-empty list of verticalized schema paths",
        )
    for sp in schema_paths:
        if not isinstance(sp, str) or not sp.startswith(_VERTICAL_PREFIXES):
            return GuardDecision(
                False,
                "UCP_CAPABILITY_REGISTRY_ARRAY_OR_FLAT_VERTICAL_PATH_BLOCKED",
                f"schema path '{sp}' must reside under shopping/, payment/, or common/ verticals",
            )
    if not isinstance(capabilities, Mapping) or len(capabilities) == 0:
        return GuardDecision(
            False,
            "UCP_CAPABILITY_REGISTRY_ARRAY_OR_FLAT_VERTICAL_PATH_BLOCKED",
            "ucp.capabilities must be an object map keyed by reverse-domain name (not a flat array)",
        )
    for cap_key, decls in capabilities.items():
        if not isinstance(cap_key, str) or not _REV_DOMAIN_RE.match(cap_key):
            return GuardDecision(
                False,
                "UCP_CAPABILITY_REGISTRY_ARRAY_OR_FLAT_VERTICAL_PATH_BLOCKED",
                f"invalid reverse-domain capability registry key '{cap_key}'",
            )
        if not isinstance(decls, Sequence) or isinstance(decls, (str, bytes)) or len(decls) == 0:
            return GuardDecision(
                False,
                "UCP_CAPABILITY_REGISTRY_ARRAY_OR_FLAT_VERTICAL_PATH_BLOCKED",
                f"capability registry key '{cap_key}' must map to a non-empty array of declarations",
            )
    return GuardDecision(
        True,
        "UCP_VERTICAL_HIERARCHY_AND_CAPABILITY_MAP_VERIFIED",
        "UCP vertical schema hierarchy and object-keyed capability registry verified",
    )


# PR-02: UCP #754 & #422
def audit_ucp_shipping_discount_double_count_and_get_order_signatures(
    payload: Mapping[str, Any],
) -> GuardDecision:
    subtotal_minor = payload.get("subtotal_minor")
    shipping_base_minor = payload.get("shipping_base_minor")
    fulfillment_total_minor = payload.get("fulfillment_total_minor")
    shipping_discount_minor = payload.get("shipping_discount_minor", 0)
    other_discount_minor = payload.get("other_discount_minor", 0)
    discount_total_minor = payload.get("discount_total_minor")
    tax_minor = payload.get("tax_minor", 0)
    grand_total_minor = payload.get("grand_total_minor")
    get_order_headers = payload.get("get_order_200_headers")

    ints = (
        subtotal_minor,
        shipping_base_minor,
        fulfillment_total_minor,
        shipping_discount_minor,
        other_discount_minor,
        discount_total_minor,
        tax_minor,
        grand_total_minor,
    )
    if not all(isinstance(v, int) and not isinstance(v, bool) for v in ints):
        return GuardDecision(
            False,
            "UCP_DISCOUNT_DOUBLE_COUNTED_OR_GET_ORDER_UNSIGNED_BLOCKED",
            "all monetary fields must be integers in minor units",
        )
    if shipping_discount_minor < 0 and fulfillment_total_minor != shipping_base_minor:
        return GuardDecision(
            False,
            "UCP_DISCOUNT_DOUBLE_COUNTED_OR_GET_ORDER_UNSIGNED_BLOCKED",
            "shipping discount already present in discount line; fulfillment total must remain shipping_base_minor to prevent double-counting",
        )
    if discount_total_minor != shipping_discount_minor + other_discount_minor:
        return GuardDecision(
            False,
            "UCP_DISCOUNT_DOUBLE_COUNTED_OR_GET_ORDER_UNSIGNED_BLOCKED",
            "discount_total_minor does not equal sum of shipping and other discounts",
        )
    expected_total = subtotal_minor + fulfillment_total_minor + tax_minor + discount_total_minor
    if grand_total_minor != expected_total:
        return GuardDecision(
            False,
            "UCP_DISCOUNT_DOUBLE_COUNTED_OR_GET_ORDER_UNSIGNED_BLOCKED",
            f"grand_total_minor ({grand_total_minor}) != expected ({expected_total})",
        )
    if not isinstance(get_order_headers, Mapping):
        return GuardDecision(
            False,
            "UCP_DISCOUNT_DOUBLE_COUNTED_OR_GET_ORDER_UNSIGNED_BLOCKED",
            "get_order 200 response headers missing",
        )
    lower_headers = {str(k).lower(): v for k, v in get_order_headers.items()}
    for req_hdr in ("signature", "signature-input", "content-digest"):
        val = lower_headers.get(req_hdr)
        if not isinstance(val, str) or not val.strip():
            return GuardDecision(
                False,
                "UCP_DISCOUNT_DOUBLE_COUNTED_OR_GET_ORDER_UNSIGNED_BLOCKED",
                f"get_order 200 response missing required header '{req_hdr}'",
            )
    return GuardDecision(
        True,
        "UCP_DISCOUNT_CONSERVATION_AND_GET_ORDER_SIGNATURE_VERIFIED",
        "shipping discount single-counted and get_order 200 signature headers verified",
    )


# PR-03: UCP #400 & #205
def audit_ucp_product_property_value_and_single_type_extends(
    payload: Mapping[str, Any],
) -> GuardDecision:
    attributes = payload.get("product_attributes")
    capability_extends = payload.get("capability_extends")
    if not isinstance(attributes, Sequence) or isinstance(attributes, (str, bytes)) or len(attributes) == 0:
        return GuardDecision(
            False,
            "UCP_PRODUCT_ATTRIBUTE_INVALID_OR_POLYMORPHIC_EXTENDS_BLOCKED",
            "product_attributes must be a non-empty array of PropertyValue objects",
        )
    for attr in attributes:
        if not isinstance(attr, Mapping):
            return GuardDecision(
                False,
                "UCP_PRODUCT_ATTRIBUTE_INVALID_OR_POLYMORPHIC_EXTENDS_BLOCKED",
                "attribute entry must be an object",
            )
        name = attr.get("name")
        value = attr.get("value")
        if not isinstance(name, str) or not name.strip() or not isinstance(value, str) or not value.strip():
            return GuardDecision(
                False,
                "UCP_PRODUCT_ATTRIBUTE_INVALID_OR_POLYMORPHIC_EXTENDS_BLOCKED",
                "attribute requires non-empty string 'name' and 'value'",
            )
        if "numeric_value" in attr:
            nv = attr["numeric_value"]
            if not isinstance(nv, (int, float)) or isinstance(nv, bool):
                return GuardDecision(
                    False,
                    "UCP_PRODUCT_ATTRIBUTE_INVALID_OR_POLYMORPHIC_EXTENDS_BLOCKED",
                    "numeric_value must be a number when provided",
                )
            unit = attr.get("unit")
            if not isinstance(unit, str) or not unit.strip():
                return GuardDecision(
                    False,
                    "UCP_PRODUCT_ATTRIBUTE_INVALID_OR_POLYMORPHIC_EXTENDS_BLOCKED",
                    "numeric_value requires a non-empty 'unit' code",
                )
    if not isinstance(capability_extends, list) or len(capability_extends) == 0:
        return GuardDecision(
            False,
            "UCP_PRODUCT_ATTRIBUTE_INVALID_OR_POLYMORPHIC_EXTENDS_BLOCKED",
            "capability.extends must be a single canonical type (non-empty list of strings), not a bare string",
        )
    for parent_cap in capability_extends:
        if not isinstance(parent_cap, str) or not _REV_DOMAIN_RE.match(parent_cap):
            return GuardDecision(
                False,
                "UCP_PRODUCT_ATTRIBUTE_INVALID_OR_POLYMORPHIC_EXTENDS_BLOCKED",
                f"invalid parent capability identifier '{parent_cap}' in capability.extends",
            )
    return GuardDecision(
        True,
        "UCP_PROPERTY_VALUE_ATTRIBUTES_AND_CANONICAL_EXTENDS_VERIFIED",
        "structured product attributes and canonical array-typed capability.extends verified",
    )


# PR-04: UCP #186 & #185
def audit_ucp_checkout_ancillaries_and_openattribution_telemetry(
    payload: Mapping[str, Any],
) -> GuardDecision:
    line_item_ids = payload.get("checkout_line_item_ids")
    ancillaries = payload.get("ancillaries")
    attribution = payload.get("openattribution_telemetry")
    if not isinstance(line_item_ids, Sequence) or isinstance(line_item_ids, (str, bytes)) or len(line_item_ids) == 0:
        return GuardDecision(
            False,
            "UCP_ANCILLARY_ORPHAN_LINE_ITEM_OR_CITATION_INVALID_BLOCKED",
            "checkout_line_item_ids must be a non-empty list",
        )
    valid_ids = {str(x) for x in line_item_ids if isinstance(x, str) and x.strip()}
    if not isinstance(ancillaries, Sequence) or isinstance(ancillaries, (str, bytes)) or len(ancillaries) == 0:
        return GuardDecision(
            False,
            "UCP_ANCILLARY_ORPHAN_LINE_ITEM_OR_CITATION_INVALID_BLOCKED",
            "ancillaries must be a non-empty list",
        )
    allowed_categories = {"protection_plan", "service", "accessory", "regulatory_fee"}
    for anc in ancillaries:
        if not isinstance(anc, Mapping):
            return GuardDecision(
                False,
                "UCP_ANCILLARY_ORPHAN_LINE_ITEM_OR_CITATION_INVALID_BLOCKED",
                "ancillary entry must be an object",
            )
        parent_id = anc.get("parent_line_item_id")
        cat = anc.get("category")
        if not isinstance(parent_id, str) or parent_id not in valid_ids:
            return GuardDecision(
                False,
                "UCP_ANCILLARY_ORPHAN_LINE_ITEM_OR_CITATION_INVALID_BLOCKED",
                f"ancillary parent_line_item_id '{parent_id}' does not match any checkout line item",
            )
        if cat not in allowed_categories:
            return GuardDecision(
                False,
                "UCP_ANCILLARY_ORPHAN_LINE_ITEM_OR_CITATION_INVALID_BLOCKED",
                f"unsupported ancillary category '{cat}'",
            )
        if cat == "regulatory_fee" and anc.get("selected") is not True:
            return GuardDecision(
                False,
                "UCP_ANCILLARY_ORPHAN_LINE_ITEM_OR_CITATION_INVALID_BLOCKED",
                "mandatory regulatory_fee ancillary cannot be deselected",
            )
    if not isinstance(attribution, Mapping) or attribution.get("namespace") != "org.openattribution.telemetry":
        return GuardDecision(
            False,
            "UCP_ANCILLARY_ORPHAN_LINE_ITEM_OR_CITATION_INVALID_BLOCKED",
            "openattribution_telemetry must declare namespace 'org.openattribution.telemetry'",
        )
    citations = attribution.get("citations")
    if not isinstance(citations, Sequence) or isinstance(citations, (str, bytes)) or len(citations) == 0:
        return GuardDecision(
            False,
            "UCP_ANCILLARY_ORPHAN_LINE_ITEM_OR_CITATION_INVALID_BLOCKED",
            "openattribution_telemetry.citations must be a non-empty list",
        )
    for cit in citations:
        if not isinstance(cit, Mapping):
            return GuardDecision(
                False,
                "UCP_ANCILLARY_ORPHAN_LINE_ITEM_OR_CITATION_INVALID_BLOCKED",
                "citation entry must be an object",
            )
        cid = cit.get("content_id")
        url = cit.get("source_url")
        turn = cit.get("retrieval_turn")
        if (
            not isinstance(cid, str)
            or not cid.strip()
            or not isinstance(url, str)
            or not url.startswith("https://")
            or not isinstance(turn, int)
            or isinstance(turn, bool)
            or turn < 0
        ):
            return GuardDecision(
                False,
                "UCP_ANCILLARY_ORPHAN_LINE_ITEM_OR_CITATION_INVALID_BLOCKED",
                "citation requires content_id, https:// source_url, and non-negative retrieval_turn",
            )
    return GuardDecision(
        True,
        "UCP_CHECKOUT_ANCILLARIES_AND_OPENATTRIBUTION_VERIFIED",
        "checkout ancillaries parent binding and OpenAttribution citation telemetry verified",
    )


# PR-05: ACP #107 & #47
def audit_acp_universal_product_types_and_multi_location_feed(
    payload: Mapping[str, Any],
) -> GuardDecision:
    product_type = payload.get("product_type")
    fulfillment_mode = payload.get("fulfillment_mode")
    billing_cadence = payload.get("billing_cadence")
    location_feed = payload.get("location_feed")
    requested_qty = payload.get("requested_qty", 1)

    allowed_types = {"physical", "digital", "service", "subscription", "bundle"}
    if product_type not in allowed_types:
        return GuardDecision(
            False,
            "ACP_PRODUCT_TYPE_MISMATCH_OR_STORE_LOCATION_UNAVAILABLE_BLOCKED",
            f"unsupported Universal Product Type '{product_type}'",
        )
    if product_type == "digital" and fulfillment_mode in {"shipping", "in_store_pickup"}:
        return GuardDecision(
            False,
            "ACP_PRODUCT_TYPE_MISMATCH_OR_STORE_LOCATION_UNAVAILABLE_BLOCKED",
            "digital product type cannot use physical shipping or in_store_pickup fulfillment",
        )
    if product_type == "subscription" and (not isinstance(billing_cadence, str) or not billing_cadence.strip()):
        return GuardDecision(
            False,
            "ACP_PRODUCT_TYPE_MISMATCH_OR_STORE_LOCATION_UNAVAILABLE_BLOCKED",
            "subscription product type requires a non-empty billing_cadence",
        )
    if not isinstance(location_feed, Mapping):
        return GuardDecision(
            False,
            "ACP_PRODUCT_TYPE_MISMATCH_OR_STORE_LOCATION_UNAVAILABLE_BLOCKED",
            "multi-location merchant requires location_feed metadata",
        )
    loc_id = location_feed.get("location_id")
    store_status = location_feed.get("store_status")
    stock_qty = location_feed.get("in_stock_qty")
    supported_modes = location_feed.get("supported_fulfillment_modes")
    if (
        not isinstance(loc_id, str)
        or not loc_id.strip()
        or store_status != "open"
        or not isinstance(stock_qty, int)
        or isinstance(stock_qty, bool)
        or not isinstance(requested_qty, int)
        or isinstance(requested_qty, bool)
        or requested_qty <= 0
        or stock_qty < requested_qty
        or not isinstance(supported_modes, Sequence)
        or fulfillment_mode not in supported_modes
    ):
        return GuardDecision(
            False,
            "ACP_PRODUCT_TYPE_MISMATCH_OR_STORE_LOCATION_UNAVAILABLE_BLOCKED",
            "store location closed, insufficient location inventory, or unsupported store fulfillment mode",
        )
    return GuardDecision(
        True,
        "ACP_UNIVERSAL_PRODUCT_TYPE_AND_LOCATION_FEED_VERIFIED",
        "ACP Universal Product Type and multi-location store inventory/fulfillment verified",
    )


# PR-06: ACP #61 & #9
def audit_acp_merchant_gift_card_source_and_extended_iin(
    payload: Mapping[str, Any],
) -> GuardDecision:
    gift_card = payload.get("gift_card")
    checkout_merchant_id = payload.get("checkout_merchant_id")
    card_iin = payload.get("card_iin")

    if not isinstance(gift_card, Mapping) or gift_card.get("sourceType") != "GiftCard":
        return GuardDecision(
            False,
            "ACP_GIFT_CARD_CROSS_MERCHANT_OR_IIN_LENGTH_INVALID_BLOCKED",
            "gift_card must declare sourceType == 'GiftCard'",
        )
    issuing_merchant = gift_card.get("issuing_merchant_id")
    balance = gift_card.get("available_balance_minor")
    redeem = gift_card.get("redeem_amount_minor")
    pin_verified = gift_card.get("pin_verified")
    if (
        not isinstance(issuing_merchant, str)
        or not issuing_merchant.strip()
        or issuing_merchant != checkout_merchant_id
        or pin_verified is not True
        or not isinstance(balance, int)
        or isinstance(balance, bool)
        or not isinstance(redeem, int)
        or isinstance(redeem, bool)
        or redeem <= 0
        or redeem > balance
    ):
        return GuardDecision(
            False,
            "ACP_GIFT_CARD_CROSS_MERCHANT_OR_IIN_LENGTH_INVALID_BLOCKED",
            "merchant-issued GiftCard must match checkout_merchant_id, pass PIN check, and not exceed balance",
        )
    if not isinstance(card_iin, str) or not card_iin.isdigit() or not (6 <= len(card_iin) <= 8):
        return GuardDecision(
            False,
            "ACP_GIFT_CARD_CROSS_MERCHANT_OR_IIN_LENGTH_INVALID_BLOCKED",
            "PaymentMethodCard.iin must be 6 to 8 numeric digits per ISO/IEC 7812-1",
        )
    return GuardDecision(
        True,
        "ACP_MERCHANT_GIFT_CARD_AND_8DIGIT_IIN_VERIFIED",
        "merchant-scoped GiftCard sourceType and 6..8 digit ISO/IEC 7812-1 IIN verified",
    )


# PR-07: AP2 #172 & #134
def audit_ap2_social_welfare_mandate_and_discovery_polling(
    payload: Mapping[str, Any],
) -> GuardDecision:
    mandate = payload.get("welfare_mandate")
    discovery_poll = payload.get("discovery_poll")
    if not isinstance(mandate, Mapping) or not isinstance(discovery_poll, Mapping):
        return GuardDecision(
            False,
            "AP2_WELFARE_MANDATE_VIOLATION_OR_HEAVY_POLL_HANDSHAKE_BLOCKED",
            "welfare_mandate and discovery_poll objects are required",
        )
    allowed_mccs = mandate.get("allowed_mccs")
    merchant_mcc = mandate.get("merchant_mcc")
    allowed_regions = mandate.get("allowed_regions")
    merchant_region = mandate.get("merchant_region")
    cash_out = mandate.get("cash_out_requested")
    now_epoch = mandate.get("now_epoch")
    expiry_epoch = mandate.get("expiry_epoch")
    if (
        not isinstance(allowed_mccs, Sequence)
        or merchant_mcc not in allowed_mccs
        or not isinstance(allowed_regions, Sequence)
        or merchant_region not in allowed_regions
        or cash_out is not False
        or not isinstance(now_epoch, int)
        or not isinstance(expiry_epoch, int)
        or now_epoch > expiry_epoch
    ):
        return GuardDecision(
            False,
            "AP2_WELFARE_MANDATE_VIOLATION_OR_HEAVY_POLL_HANDSHAKE_BLOCKED",
            "Social Welfare Mandate violated MCC allowlist, regional geofence, cash-out ban, or expiry window",
        )
    if_none_match = discovery_poll.get("if_none_match")
    current_etag = discovery_poll.get("current_etag")
    full_ap2_handshake_used = discovery_poll.get("full_ap2_handshake_used")
    status_code = discovery_poll.get("response_status")
    if full_ap2_handshake_used is True:
        return GuardDecision(
            False,
            "AP2_WELFARE_MANDATE_VIOLATION_OR_HEAVY_POLL_HANDSHAKE_BLOCKED",
            "high-frequency stock/price polling must use lightweight Discovery Layer ETag polling, not full AP2 handshakes",
        )
    if not isinstance(if_none_match, str) or not if_none_match.strip() or not isinstance(current_etag, str) or not current_etag.strip():
        return GuardDecision(
            False,
            "AP2_WELFARE_MANDATE_VIOLATION_OR_HEAVY_POLL_HANDSHAKE_BLOCKED",
            "discovery_poll requires non-empty if_none_match and current_etag",
        )
    if if_none_match == current_etag and status_code != 304:
        return GuardDecision(
            False,
            "AP2_WELFARE_MANDATE_VIOLATION_OR_HEAVY_POLL_HANDSHAKE_BLOCKED",
            "unchanged ETag on Discovery Layer poll must return HTTP 304 Not Modified",
        )
    return GuardDecision(
        True,
        "AP2_SOCIAL_WELFARE_MANDATE_AND_DISCOVERY_POLL_VERIFIED",
        "Project Mulberry social welfare mandate constraints and lightweight ETag discovery polling verified",
    )


# PR-08: x402 #3703 & #3852
def audit_x402_hook_correlation_abort_release_and_paywall_xss(
    payload: Mapping[str, Any],
) -> GuardDecision:
    before_id = payload.get("before_hook_invocation_id")
    after_or_fail_id = payload.get("completion_hook_invocation_id")
    aborted_by_second_before_hook = payload.get("aborted_by_second_before_hook", False)
    failure_hook_called = payload.get("failure_hook_called", False)
    reserved_budget_released = payload.get("reserved_budget_released", False)
    paywall_serialized_json = payload.get("paywall_serialized_json")

    if (
        not isinstance(before_id, str)
        or not before_id.strip()
        or before_id != after_or_fail_id
    ):
        return GuardDecision(
            False,
            "X402_HOOK_BUDGET_LEAK_OR_PAYWALL_XSS_UNESCAPED_BLOCKED",
            "createPaymentPayload hooks must share a deterministic per-call invocationId",
        )
    if aborted_by_second_before_hook is True and (failure_hook_called is not True or reserved_budget_released is not True):
        return GuardDecision(
            False,
            "X402_HOOK_BUDGET_LEAK_OR_PAYWALL_XSS_UNESCAPED_BLOCKED",
            "before-hook abort must trigger onPaymentCreationFailure to release budget reserved by earlier before-hooks",
        )
    if not isinstance(paywall_serialized_json, str) or not paywall_serialized_json.strip():
        return GuardDecision(
            False,
            "X402_HOOK_BUDGET_LEAK_OR_PAYWALL_XSS_UNESCAPED_BLOCKED",
            "paywall_serialized_json must be a non-empty string",
        )
    if any(tok in paywall_serialized_json.lower() for tok in ("</script", "<script", "<!--", "<svg", "onerror=")):
        return GuardDecision(
            False,
            "X402_HOOK_BUDGET_LEAK_OR_PAYWALL_XSS_UNESCAPED_BLOCKED",
            "x402-paywall serialized JSON contains unescaped HTML/script characters (Reflected XSS vector)",
        )
    return GuardDecision(
        True,
        "X402_HOOK_CORRELATION_AND_PAYWALL_XSS_SANITIZATION_VERIFIED",
        "per-call hook invocationId correlation, abort budget release, and paywall XSS escaping verified",
    )


# PR-09: x402 #3694 & #3678
def audit_x402_erc8183_job_escrow_and_delivery_conformance(
    payload: Mapping[str, Any],
) -> GuardDecision:
    scheme = payload.get("scheme")
    job_state = payload.get("job_state")
    evaluator_verdict = payload.get("evaluator_verdict")
    settlement_action = payload.get("settlement_action")
    delivery_evidence = payload.get("ext_delivery")

    if scheme != "job-escrow" or job_state != "EVALUATED":
        return GuardDecision(
            False,
            "X402_JOB_ESCROW_UNEVALUATED_OR_DELIVERY_NONCONFORMANT_BLOCKED",
            "job-escrow (ERC-8183) settlement requires scheme=='job-escrow' and job_state=='EVALUATED'",
        )
    if evaluator_verdict == "PASS" and settlement_action != "RELEASE_TO_WORKER":
        return GuardDecision(
            False,
            "X402_JOB_ESCROW_UNEVALUATED_OR_DELIVERY_NONCONFORMANT_BLOCKED",
            "PASS verdict must release escrow to worker",
        )
    if evaluator_verdict == "FAIL" and settlement_action != "REFUND_TO_BUYER":
        return GuardDecision(
            False,
            "X402_JOB_ESCROW_UNEVALUATED_OR_DELIVERY_NONCONFORMANT_BLOCKED",
            "FAIL verdict must refund escrow to buyer, never release to worker",
        )
    if evaluator_verdict not in {"PASS", "FAIL"}:
        return GuardDecision(
            False,
            "X402_JOB_ESCROW_UNEVALUATED_OR_DELIVERY_NONCONFORMANT_BLOCKED",
            "evaluator_verdict must be 'PASS' or 'FAIL'",
        )
    if not isinstance(delivery_evidence, Mapping):
        return GuardDecision(
            False,
            "X402_JOB_ESCROW_UNEVALUATED_OR_DELIVERY_NONCONFORMANT_BLOCKED",
            "ext-delivery conformance evidence object is required",
        )
    deliv_hash = delivery_evidence.get("deliverable_sha256")
    expected_hash = delivery_evidence.get("expected_spec_sha256")
    schema_conforms = delivery_evidence.get("schema_conforms")
    eval_sig = delivery_evidence.get("evaluator_signature")
    if (
        not isinstance(deliv_hash, str)
        or len(deliv_hash) != 64
        or not _HEX_RE.match(deliv_hash)
        or deliv_hash != expected_hash
        or schema_conforms is not True
        or not isinstance(eval_sig, str)
        or len(eval_sig) < 16
    ):
        return GuardDecision(
            False,
            "X402_JOB_ESCROW_UNEVALUATED_OR_DELIVERY_NONCONFORMANT_BLOCKED",
            "ext-delivery evidence failed deliverable hash match, schema conformance, or evaluator signature check",
        )
    return GuardDecision(
        True,
        "X402_ERC8183_JOB_ESCROW_AND_EXT_DELIVERY_VERIFIED",
        "ERC-8183 job-escrow evaluator gate and ext-delivery conformance evidence verified",
    )


# PR-10: x402 #3673 & #3659
def audit_x402_cardano_raw_cbor_preservation_and_spec_payload(
    payload: Mapping[str, Any],
) -> GuardDecision:
    client_cbor_hex = payload.get("client_signed_cbor_hex")
    submitted_cbor_hex = payload.get("facilitator_submitted_cbor_hex")
    reencoded_by_facilitator = payload.get("reencoded_by_facilitator", False)
    payload_encoding = payload.get("payload_encoding")

    if (
        not isinstance(client_cbor_hex, str)
        or len(client_cbor_hex) < 16
        or len(client_cbor_hex) % 2 != 0
        or not _HEX_RE.match(client_cbor_hex)
    ):
        return GuardDecision(
            False,
            "X402_CARDANO_CBOR_REENCODED_OR_SUI_PAYLOAD_CONTAMINATED_BLOCKED",
            "Cardano exact transaction payload must be valid even-length CBOR hex (not Sui BCS base64)",
        )
    if payload_encoding != "cardano_cbor_hex":
        return GuardDecision(
            False,
            "X402_CARDANO_CBOR_REENCODED_OR_SUI_PAYLOAD_CONTAMINATED_BLOCKED",
            f"invalid payload_encoding '{payload_encoding}'; must be 'cardano_cbor_hex'",
        )
    if reencoded_by_facilitator is True or submitted_cbor_hex != client_cbor_hex:
        return GuardDecision(
            False,
            "X402_CARDANO_CBOR_REENCODED_OR_SUI_PAYLOAD_CONTAMINATED_BLOCKED",
            "facilitator must submit the exact client-signed CBOR bytes without re-encoding untagged/tag-258 sets",
        )
    return GuardDecision(
        True,
        "X402_CARDANO_RAW_CBOR_AND_SPEC_PAYLOAD_VERIFIED",
        "Cardano exact raw CBOR byte preservation and CBOR hex format verified",
    )


# PR-11: x402 #3646 & #3644
def audit_x402_agreement_session_terms_and_go_svm_failed_tx(
    payload: Mapping[str, Any],
) -> GuardDecision:
    agreement = payload.get("agreement_session")
    svm_confirmation = payload.get("go_svm_confirmation")
    if not isinstance(agreement, Mapping) or not isinstance(svm_confirmation, Mapping):
        return GuardDecision(
            False,
            "X402_AGREEMENT_TERMS_BREACH_OR_SVM_FAILED_TX_PENDING_BLOCKED",
            "agreement_session and go_svm_confirmation objects are required",
        )
    agreed_hash = agreement.get("agreed_terms_sha256")
    current_hash = agreement.get("current_terms_sha256")
    cumulative_minor = agreement.get("cumulative_spend_minor")
    payment_minor = agreement.get("payment_amount_minor")
    cap_minor = agreement.get("session_cap_minor")
    now_epoch = agreement.get("now_epoch")
    expires_epoch = agreement.get("expires_epoch")
    if (
        not isinstance(agreed_hash, str)
        or len(agreed_hash) != 64
        or agreed_hash != current_hash
        or not isinstance(cumulative_minor, int)
        or not isinstance(payment_minor, int)
        or not isinstance(cap_minor, int)
        or cumulative_minor + payment_minor > cap_minor
        or not isinstance(now_epoch, int)
        or not isinstance(expires_epoch, int)
        or now_epoch > expires_epoch
    ):
        return GuardDecision(
            False,
            "X402_AGREEMENT_TERMS_BREACH_OR_SVM_FAILED_TX_PENDING_BLOCKED",
            "agreement-session terms hash mismatch, cumulative spend cap exceeded, or session expired",
        )
    tx_confirmed = svm_confirmation.get("tx_confirmed_onchain")
    status_err = svm_confirmation.get("status_err")
    recorded_state = svm_confirmation.get("recorded_settlement_state")
    if tx_confirmed is True and status_err is not None and recorded_state == "settlement_pending":
        return GuardDecision(
            False,
            "X402_AGREEMENT_TERMS_BREACH_OR_SVM_FAILED_TX_PENDING_BLOCKED",
            "Go SVM confirmed transaction with non-nil status.Err is a terminal on-chain failure and must not be recorded as settlement_pending",
        )
    if tx_confirmed is True and status_err is not None and recorded_state != "settlement_failed":
        return GuardDecision(
            False,
            "X402_AGREEMENT_TERMS_BREACH_OR_SVM_FAILED_TX_PENDING_BLOCKED",
            "confirmed SVM transaction with status.Err must be classified as 'settlement_failed'",
        )
    return GuardDecision(
        True,
        "X402_AGREEMENT_SESSION_AND_GO_SVM_FAILURE_STATE_VERIFIED",
        "agreement-session terms lifecycle and Go SVM terminal on-chain failure classification verified",
    )


# PR-12: x402 #3896 & #3641
def audit_x402_solidarity_owner_share_and_payment_backed_reviews(
    payload: Mapping[str, Any],
) -> GuardDecision:
    solidarity = payload.get("solidarity")
    review = payload.get("review")
    if not isinstance(solidarity, Mapping) or not isinstance(review, Mapping):
        return GuardDecision(
            False,
            "X402_SOLIDARITY_SELLER_SHORTFALL_OR_UNBACKED_REVIEW_BLOCKED",
            "solidarity and review objects are required",
        )
    seller_price = solidarity.get("seller_price_minor")
    seller_received = solidarity.get("seller_received_minor")
    share_minor = solidarity.get("humanitarian_share_minor")
    monthly_donated = solidarity.get("monthly_donated_minor")
    monthly_cap = solidarity.get("monthly_cap_minor")
    owner_consented = solidarity.get("owner_consented")
    if (
        owner_consented is not True
        or not isinstance(seller_price, int)
        or seller_received != seller_price
        or not isinstance(share_minor, int)
        or share_minor < 0
        or not isinstance(monthly_donated, int)
        or not isinstance(monthly_cap, int)
        or monthly_donated + share_minor > monthly_cap
    ):
        return GuardDecision(
            False,
            "X402_SOLIDARITY_SELLER_SHORTFALL_OR_UNBACKED_REVIEW_BLOCKED",
            "solidarity share requires owner consent, 100% full seller payout, and adherence to monthly owner cap",
        )
    tx_hash = review.get("settlement_tx_hash")
    settled_txs = review.get("verified_settlement_tx_hashes")
    reviewer_wallet = review.get("reviewer_wallet")
    tx_payer_wallet = review.get("tx_payer_wallet")
    if (
        not isinstance(tx_hash, str)
        or not tx_hash.strip()
        or not isinstance(settled_txs, Sequence)
        or tx_hash not in settled_txs
        or not isinstance(reviewer_wallet, str)
        or not reviewer_wallet.strip()
        or reviewer_wallet != tx_payer_wallet
    ):
        return GuardDecision(
            False,
            "X402_SOLIDARITY_SELLER_SHORTFALL_OR_UNBACKED_REVIEW_BLOCKED",
            "reviews extension entry must be backed by a verified settlement transaction from the reviewer's wallet",
        )
    return GuardDecision(
        True,
        "X402_SOLIDARITY_SHARE_AND_PAYMENT_BACKED_REVIEW_VERIFIED",
        "owner-consented solidarity share and payment-backed review settlement proof verified",
    )


# PR-13: MCP #3003 & #2601
def audit_mcp_error_structured_content_and_uri_template_id(
    payload: Mapping[str, Any],
) -> GuardDecision:
    tool_result = payload.get("tool_error_result")
    resource_templates = payload.get("resource_templates")
    if not isinstance(tool_result, Mapping):
        return GuardDecision(
            False,
            "MCP_UNSTRUCTURED_ERROR_FORWARDING_OR_DUPLICATE_URI_TEMPLATE_BLOCKED",
            "tool_error_result must be an object",
        )
    is_error = tool_result.get("isError")
    structured = tool_result.get("structuredContent")
    if is_error is True:
        if not isinstance(structured, Mapping):
            return GuardDecision(
                False,
                "MCP_UNSTRUCTURED_ERROR_FORWARDING_OR_DUPLICATE_URI_TEMPLATE_BLOCKED",
                "tool execution error (isError: true) requires schema-governed structuredContent for safe LLM forwarding",
            )
        err_code = structured.get("errorCode")
        retryable = structured.get("retryable")
        if not isinstance(err_code, str) or not err_code.strip() or not isinstance(retryable, bool):
            return GuardDecision(
                False,
                "MCP_UNSTRUCTURED_ERROR_FORWARDING_OR_DUPLICATE_URI_TEMPLATE_BLOCKED",
                "error structuredContent must include string 'errorCode' and boolean 'retryable'",
            )
    if not isinstance(resource_templates, Sequence) or isinstance(resource_templates, (str, bytes)) or len(resource_templates) == 0:
        return GuardDecision(
            False,
            "MCP_UNSTRUCTURED_ERROR_FORWARDING_OR_DUPLICATE_URI_TEMPLATE_BLOCKED",
            "resource_templates must be a non-empty list",
        )
    seen_templates: set[str] = set()
    for tmpl in resource_templates:
        if not isinstance(tmpl, Mapping):
            return GuardDecision(
                False,
                "MCP_UNSTRUCTURED_ERROR_FORWARDING_OR_DUPLICATE_URI_TEMPLATE_BLOCKED",
                "resource template entry must be an object",
            )
        uri_tmpl = tmpl.get("uriTemplate")
        if not isinstance(uri_tmpl, str) or not uri_tmpl.strip() or "://" not in uri_tmpl:
            return GuardDecision(
                False,
                "MCP_UNSTRUCTURED_ERROR_FORWARDING_OR_DUPLICATE_URI_TEMPLATE_BLOCKED",
                "resource template requires a valid non-empty uriTemplate identifier",
            )
        if uri_tmpl in seen_templates:
            return GuardDecision(
                False,
                "MCP_UNSTRUCTURED_ERROR_FORWARDING_OR_DUPLICATE_URI_TEMPLATE_BLOCKED",
                f"duplicate uriTemplate '{uri_tmpl}' in resource_templates; uriTemplate must be unique",
            )
        seen_templates.add(uri_tmpl)
    return GuardDecision(
        True,
        "MCP_ERROR_STRUCTURED_CONTENT_AND_URI_TEMPLATE_ID_VERIFIED",
        "schema-governed error structuredContent and unique uriTemplate identifiers verified",
    )


# PR-14: MCP #3025 & #3024
def audit_mcp_tool_side_effect_class_and_manifest_trust_tier(
    payload: Mapping[str, Any],
) -> GuardDecision:
    side_effect = payload.get("side_effect_classification")
    server_trust_tier = payload.get("server_trust_tier")
    required_trust_tier = payload.get("required_trust_tier")
    human_approval_granted = payload.get("human_approval_granted", False)

    allowed_side_effects = {
        "none",
        "read_only",
        "reversible_write",
        "irreversible_write",
        "external_execution",
    }
    if side_effect not in allowed_side_effects:
        return GuardDecision(
            False,
            "MCP_SIDE_EFFECT_APPROVAL_BYPASS_OR_TRUST_TIER_INSUFFICIENT_BLOCKED",
            f"invalid tool side_effect_classification '{side_effect}'",
        )
    if server_trust_tier not in _TRUST_TIER_ORDER or required_trust_tier not in _TRUST_TIER_ORDER:
        return GuardDecision(
            False,
            "MCP_SIDE_EFFECT_APPROVAL_BYPASS_OR_TRUST_TIER_INSUFFICIENT_BLOCKED",
            "server_trust_tier and required_trust_tier must be valid capability trust tiers",
        )
    if _TRUST_TIER_ORDER[server_trust_tier] < _TRUST_TIER_ORDER[required_trust_tier]:
        return GuardDecision(
            False,
            "MCP_SIDE_EFFECT_APPROVAL_BYPASS_OR_TRUST_TIER_INSUFFICIENT_BLOCKED",
            f"server trust tier '{server_trust_tier}' is below required '{required_trust_tier}'",
        )
    if side_effect in {"irreversible_write", "external_execution"} and human_approval_granted is not True:
        return GuardDecision(
            False,
            "MCP_SIDE_EFFECT_APPROVAL_BYPASS_OR_TRUST_TIER_INSUFFICIENT_BLOCKED",
            f"tool with side_effect_classification='{side_effect}' requires explicit approval gate authorization",
        )
    return GuardDecision(
        True,
        "MCP_TOOL_SIDE_EFFECT_AND_MANIFEST_TRUST_TIER_VERIFIED",
        "tool side-effect classification approval gate and server manifest trust tier verified",
    )


# PR-15: tau2-bench #182 & #172
def audit_tau2_retail_confirmation_stop_and_airline_extra_passenger(
    payload: Mapping[str, Any],
) -> GuardDecision:
    agent_awaiting_confirmation = payload.get("agent_awaiting_confirmation", False)
    user_sim_emitted_stop = payload.get("user_sim_emitted_stop", False)
    task_passengers = payload.get("task_instructed_passengers")
    sim_passengers = payload.get("user_sim_requested_passengers")

    if agent_awaiting_confirmation is True and user_sim_emitted_stop is True:
        return GuardDecision(
            False,
            "TAU2_PREMATURE_CONFIRMATION_STOP_OR_EXTRA_PASSENGER_HALLUCINATED_BLOCKED",
            "retail user simulator must not emit ###STOP### while agent is requesting confirmation for a pending action",
        )
    if (
        not isinstance(task_passengers, Sequence)
        or isinstance(task_passengers, (str, bytes))
        or len(task_passengers) == 0
        or not isinstance(sim_passengers, Sequence)
        or isinstance(sim_passengers, (str, bytes))
        or len(sim_passengers) == 0
    ):
        return GuardDecision(
            False,
            "TAU2_PREMATURE_CONFIRMATION_STOP_OR_EXTRA_PASSENGER_HALLUCINATED_BLOCKED",
            "task_instructed_passengers and user_sim_requested_passengers must be non-empty lists",
        )
    allowed_set = {str(p).strip() for p in task_passengers if isinstance(p, str) and p.strip()}
    for p in sim_passengers:
        if not isinstance(p, str) or p.strip() not in allowed_set:
            return GuardDecision(
                False,
                "TAU2_PREMATURE_CONFIRMATION_STOP_OR_EXTRA_PASSENGER_HALLUCINATED_BLOCKED",
                f"airline user simulator introduced extra passenger '{p}' not present in task instructions",
            )
    return GuardDecision(
        True,
        "TAU2_CONFIRMATION_CONTINUATION_AND_PASSENGER_GROUNDING_VERIFIED",
        "retail confirmation continuation and airline passenger persona grounding verified",
    )


# PR-16: tau2-bench #373 & #169
def audit_tau2_banking_unrequested_referral_and_openai_tool_call_schema(
    payload: Mapping[str, Any],
) -> GuardDecision:
    requested_card = payload.get("requested_referral_card")
    documented_cards = payload.get("documented_referral_cards")
    referred_card = payload.get("agent_referred_card")
    litellm_tool_calls = payload.get("litellm_tool_calls")

    if not isinstance(documented_cards, Sequence) or isinstance(documented_cards, (str, bytes)):
        return GuardDecision(
            False,
            "TAU2_UNREQUESTED_CARD_REFERRAL_OR_NONCOMPLIANT_TOOL_CALL_BLOCKED",
            "documented_referral_cards must be a sequence",
        )
    if referred_card is not None:
        if referred_card != requested_card or referred_card not in documented_cards:
            return GuardDecision(
                False,
                "TAU2_UNREQUESTED_CARD_REFERRAL_OR_NONCOMPLIANT_TOOL_CALL_BLOCKED",
                f"agent referred unrequested or undocumented card '{referred_card}' contrary to banking policy doc _009",
            )
    if not isinstance(litellm_tool_calls, Sequence) or isinstance(litellm_tool_calls, (str, bytes)) or len(litellm_tool_calls) == 0:
        return GuardDecision(
            False,
            "TAU2_UNREQUESTED_CARD_REFERRAL_OR_NONCOMPLIANT_TOOL_CALL_BLOCKED",
            "litellm_tool_calls must be a non-empty list",
        )
    for tc in litellm_tool_calls:
        if not isinstance(tc, Mapping):
            return GuardDecision(
                False,
                "TAU2_UNREQUESTED_CARD_REFERRAL_OR_NONCOMPLIANT_TOOL_CALL_BLOCKED",
                "tool_call entry must be an object",
            )
        if "name" in tc:
            return GuardDecision(
                False,
                "TAU2_UNREQUESTED_CARD_REFERRAL_OR_NONCOMPLIANT_TOOL_CALL_BLOCKED",
                "top-level 'name' field in tool_calls violates OpenAI Chat Completions schema; name belongs inside 'function'",
            )
        fn = tc.get("function")
        if (
            not isinstance(tc.get("id"), str)
            or tc.get("type") != "function"
            or not isinstance(fn, Mapping)
            or not isinstance(fn.get("name"), str)
            or not isinstance(fn.get("arguments"), str)
        ):
            return GuardDecision(
                False,
                "TAU2_UNREQUESTED_CARD_REFERRAL_OR_NONCOMPLIANT_TOOL_CALL_BLOCKED",
                "tool_call must contain id, type=='function', and function.{name, arguments}",
            )
    return GuardDecision(
        True,
        "TAU2_DOC_009_REFERRAL_POLICY_AND_OPENAI_TOOL_CALL_VERIFIED",
        "banking doc _009 referral policy compliance and OpenAI tool_calls schema verified",
    )
