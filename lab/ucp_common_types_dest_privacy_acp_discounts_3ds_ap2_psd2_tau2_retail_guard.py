"""Stage 114 deterministic protocol & benchmark guardrails:
1. UCP (#736, #735, #725):
   - Common primitive types (`context.json`, `signals.json`, `totals.json`,
     `total.json`, `policy.json`, `price_filter.json`, `price_range.json`) must
     resolve under `common/types/` rather than legacy `shopping/types/` (#736).
   - Identity-linked buyer `email`, `phone`, and `name` must remain scalar
     strings, and precise saved address fields (`street_address`, `postal_code`)
     must not be proactively disclosed prior to explicit destination selection (#735).
   - UCP MCP mapping must preserve 1:N capability-to-operations and 1:1
     operation-to-MCP-tool cardinality (#725).
2. ACP (#129, #117):
   - `DiscountsResponse` must include both `applied` and `rejected` arrays, and
     3DS frictionless flows must provide `three_ds_version`,
     `directory_server_transaction_id`, and `trans_status == "Y"` (#129).
   - `complete` / `cancel` checkout fulfillment responses must reference a
     declared `fulfillment_options[].id` (#117).
3. Google AP2 (#270, #269):
   - PSD2 Art. 64 `CancellationReceipt` closed `cancellation_reason` enum
     (`USER_REQUESTED`, `MERCHANT_REQUESTED`, `COMPLIANCE_TERMINATED`, `EXPIRED`)
     and PSD2 Art. 89 `RefundReceipt` closed `refund_result` enum
     (`FULL`, `PARTIAL`, `REJECTED`) with `refund_amount_minor <= settled_amount_minor` (#270).
   - Admission-time `ComplianceReceipt` bound to `mandate_id` and `mandate_hash`
     with `verdict == "ADMITTED"` (#269).
4. Sierra tau2-bench (#571, #567):
   - Retail `exchange_delivered_order_items` requires `order_status == "delivered"`
     and `gift_card_balance_minor >= price_diff_minor` when `price_diff_minor > 0` (#571).
   - Reproducibility-critical LLM args (`seed`) dropped by `litellm.drop_params`
     must emit an explicit warning (`dropped_params_warned == True`, #567).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


UCP_MIGRATED_COMMON_PRIMITIVES = frozenset(
    {
        "context.json",
        "signals.json",
        "totals.json",
        "total.json",
        "policy.json",
        "price_filter.json",
        "price_range.json",
    }
)

AP2_CANCELLATION_REASONS = frozenset(
    {
        "USER_REQUESTED",
        "MERCHANT_REQUESTED",
        "COMPLIANCE_TERMINATED",
        "EXPIRED",
    }
)

AP2_REFUND_RESULTS = frozenset({"FULL", "PARTIAL", "REJECTED"})


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    decision_code: str
    reason: str
    details: dict[str, Any]


def validate_ucp_common_primitives_destination_privacy_and_mcp_mapping_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Validate UCP #736 common/types migration, #735 destination privacy, and #725 MCP mapping."""
    schema_refs = payload.get("schema_refs", [])
    if not isinstance(schema_refs, list) or not schema_refs:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_SCHEMA_REFS_MISSING",
            reason="schema_refs must be a non-empty list.",
            details={},
        )
    for ref in schema_refs:
        if not isinstance(ref, str):
            return GuardDecision(
                allowed=False,
                decision_code="UCP_SCHEMA_REF_INVALID",
                reason="Each schema_ref must be a string.",
                details={"ref": ref},
            )
        for prim in UCP_MIGRATED_COMMON_PRIMITIVES:
            if f"shopping/types/{prim}" in ref:
                return GuardDecision(
                    allowed=False,
                    decision_code="UCP_LEGACY_SHOPPING_TYPES_PRIMITIVE_REF",
                    reason="Migrated common primitives must reference common/types/, not shopping/types/ (#736).",
                    details={"ref": ref, "primitive": prim},
                )

    identity_buyer = payload.get("identity_linked_buyer", {})
    if not isinstance(identity_buyer, Mapping):
        return GuardDecision(
            allowed=False,
            decision_code="UCP_IDENTITY_BUYER_INVALID",
            reason="identity_linked_buyer must be a mapping.",
            details={},
        )
    for scalar_field in ("email", "phone", "name"):
        val = identity_buyer.get(scalar_field)
        if val is not None and not isinstance(val, str):
            return GuardDecision(
                allowed=False,
                decision_code="UCP_IDENTITY_BUYER_SCALAR_VIOLATION",
                reason=f"Identity-linked buyer.{scalar_field} must remain a scalar string (#735).",
                details={"field": scalar_field, "type": type(val).__name__},
            )
    destination_selected = bool(identity_buyer.get("destination_selected", False))
    disclosed_precise_address = bool(identity_buyer.get("disclosed_precise_saved_address", False))
    if disclosed_precise_address and not destination_selected:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_PREMATURE_SAVED_ADDRESS_DISCLOSURE",
            reason="Identity linking alone does not authorize proactive disclosure of precise saved-address fields before selection (#735).",
            details={"destination_selected": destination_selected},
        )

    mcp_mapping = payload.get("mcp_operation_mapping", {})
    if not isinstance(mcp_mapping, Mapping):
        return GuardDecision(
            allowed=False,
            decision_code="UCP_MCP_MAPPING_INVALID",
            reason="mcp_operation_mapping must be a mapping.",
            details={},
        )
    ops_count = mcp_mapping.get("exposed_operations_count")
    tools_count = mcp_mapping.get("mcp_tools_count")
    conflates_capability_1to1 = bool(mcp_mapping.get("claims_capability_maps_1to1_to_tool", False))
    if conflates_capability_1to1 or not isinstance(ops_count, int) or ops_count <= 0 or ops_count != tools_count:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_MCP_OPERATION_TO_TOOL_MAPPING_INVALID",
            reason="Each exposed UCP operation maps 1:1 to an MCP tool while a capability may expose multiple operations (#725).",
            details={
                "exposed_operations_count": ops_count,
                "mcp_tools_count": tools_count,
                "claims_capability_maps_1to1_to_tool": conflates_capability_1to1,
            },
        )

    return GuardDecision(
        allowed=True,
        decision_code="UCP_COMMON_TYPES_DEST_PRIVACY_AND_MCP_VERIFIED",
        reason="UCP common/types refs, destination selection privacy, and MCP operation-to-tool mapping verified.",
        details={"operations_count": ops_count},
    )


def validate_acp_discounts_3ds_frictionless_and_fulfillment_ref_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Validate ACP #129 DiscountsResponse.rejected + 3DS frictionless and #117 fulfillment refs."""
    discounts = payload.get("discounts_response", {})
    if not isinstance(discounts, Mapping):
        return GuardDecision(
            allowed=False,
            decision_code="ACP_DISCOUNTS_RESPONSE_INVALID",
            reason="discounts_response must be a mapping.",
            details={},
        )
    if not isinstance(discounts.get("applied"), list) or not isinstance(discounts.get("rejected"), list):
        return GuardDecision(
            allowed=False,
            decision_code="ACP_DISCOUNTS_REJECTED_ARRAY_MISSING",
            reason="DiscountsResponse must include both applied and rejected arrays across JSON Schema and OpenAPI (#129).",
            details={"keys": list(discounts.keys())},
        )

    three_ds = payload.get("three_ds_frictionless", {})
    if not isinstance(three_ds, Mapping):
        return GuardDecision(
            allowed=False,
            decision_code="ACP_3DS_FRICTIONLESS_INVALID",
            reason="three_ds_frictionless must be a mapping.",
            details={},
        )
    version = str(three_ds.get("three_ds_version", ""))
    ds_tx_id = str(three_ds.get("directory_server_transaction_id", ""))
    trans_status = str(three_ds.get("trans_status", ""))
    if not version.startswith("2.") or not ds_tx_id or trans_status != "Y":
        return GuardDecision(
            allowed=False,
            decision_code="ACP_3DS_FRICTIONLESS_SCHEMA_MISMATCH",
            reason="3DS frictionless result requires 2.x three_ds_version, directory_server_transaction_id, and trans_status == 'Y' (#129).",
            details={"three_ds_version": version, "trans_status": trans_status},
        )

    fulfillment = payload.get("checkout_response_fulfillment", {})
    if not isinstance(fulfillment, Mapping):
        return GuardDecision(
            allowed=False,
            decision_code="ACP_FULFILLMENT_RESPONSE_INVALID",
            reason="checkout_response_fulfillment must be a mapping.",
            details={},
        )
    options = fulfillment.get("fulfillment_options", [])
    selected_id = fulfillment.get("selected_fulfillment_option_id")
    valid_ids = {
        opt.get("id")
        for opt in options
        if isinstance(opt, Mapping) and isinstance(opt.get("id"), str) and opt.get("id")
    }
    if not isinstance(selected_id, str) or selected_id not in valid_ids:
        return GuardDecision(
            allowed=False,
            decision_code="ACP_COMPLETE_CANCEL_FULFILLMENT_VALUE_INVALID",
            reason="complete/cancel response selected_fulfillment_option_id must reference a declared fulfillment_options[].id (#117).",
            details={"selected_fulfillment_option_id": selected_id, "declared_ids": sorted(valid_ids)},
        )

    return GuardDecision(
        allowed=True,
        decision_code="ACP_DISCOUNTS_3DS_AND_FULFILLMENT_VERIFIED",
        reason="ACP DiscountsResponse.rejected, 3DS frictionless fields, and complete/cancel fulfillment reference verified.",
        details={"selected_fulfillment_option_id": selected_id},
    )


def validate_ap2_psd2_lifecycle_and_compliance_receipt_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Validate Google AP2 #270 PSD2 Art. 64/89 lifecycle receipts and #269 ComplianceReceipt."""
    compliance = payload.get("compliance_receipt", {})
    if not isinstance(compliance, Mapping):
        return GuardDecision(
            allowed=False,
            decision_code="AP2_COMPLIANCE_RECEIPT_INVALID",
            reason="compliance_receipt must be a mapping.",
            details={},
        )
    if (
        not compliance.get("mandate_id")
        or not compliance.get("mandate_hash")
        or compliance.get("verdict") != "ADMITTED"
        or not bool(compliance.get("signature_verified", False))
    ):
        return GuardDecision(
            allowed=False,
            decision_code="AP2_ADMISSION_COMPLIANCE_RECEIPT_UNVERIFIED",
            reason="Admission-time ComplianceReceipt must bind mandate_id + mandate_hash with verified signature and verdict == 'ADMITTED' (#269).",
            details={"verdict": compliance.get("verdict")},
        )

    cancel_rec = payload.get("cancellation_receipt", {})
    if not isinstance(cancel_rec, Mapping) or cancel_rec.get("cancellation_reason") not in AP2_CANCELLATION_REASONS:
        return GuardDecision(
            allowed=False,
            decision_code="AP2_PSD2_ART64_CANCELLATION_REASON_INVALID",
            reason="PSD2 Article 64 CancellationReceipt requires closed cancellation_reason enum (#270).",
            details={"cancellation_reason": cancel_rec.get("cancellation_reason") if isinstance(cancel_rec, Mapping) else None},
        )

    refund_rec = payload.get("refund_receipt", {})
    if not isinstance(refund_rec, Mapping):
        return GuardDecision(
            allowed=False,
            decision_code="AP2_PSD2_ART89_REFUND_RECEIPT_INVALID",
            reason="refund_receipt must be a mapping.",
            details={},
        )
    refund_result = refund_rec.get("refund_result")
    refund_minor = refund_rec.get("refund_amount_minor")
    settled_minor = refund_rec.get("settled_amount_minor")
    if (
        refund_result not in AP2_REFUND_RESULTS
        or not isinstance(refund_minor, int)
        or not isinstance(settled_minor, int)
        or refund_minor < 0
        or refund_minor > settled_minor
    ):
        return GuardDecision(
            allowed=False,
            decision_code="AP2_PSD2_ART89_REFUND_ENVELOPE_INVALID",
            reason="PSD2 Article 89 RefundReceipt requires closed refund_result enum and refund_amount_minor <= settled_amount_minor (#270).",
            details={"refund_result": refund_result, "refund_amount_minor": refund_minor, "settled_amount_minor": settled_minor},
        )

    return GuardDecision(
        allowed=True,
        decision_code="AP2_PSD2_LIFECYCLE_AND_COMPLIANCE_RECEIPT_VERIFIED",
        reason="AP2 admission ComplianceReceipt and PSD2 Art. 64/89 lifecycle envelopes verified.",
        details={"cancellation_reason": cancel_rec["cancellation_reason"], "refund_result": refund_result},
    )


def validate_tau2_retail_exchange_and_dropped_seed_warning_guard(
    payload: Mapping[str, Any],
) -> GuardDecision:
    """Validate Sierra tau2-bench #571 retail exchange constraints and #567 dropped seed warning."""
    exchange = payload.get("retail_exchange", {})
    if not isinstance(exchange, Mapping):
        return GuardDecision(
            allowed=False,
            decision_code="TAU2_RETAIL_EXCHANGE_INVALID",
            reason="retail_exchange must be a mapping.",
            details={},
        )
    if exchange.get("order_status") != "delivered":
        return GuardDecision(
            allowed=False,
            decision_code="TAU2_RETAIL_EXCHANGE_NON_DELIVERED_ORDER",
            reason="exchange_delivered_order_items cannot target a pending or non-delivered order (#571 task_64).",
            details={"order_status": exchange.get("order_status")},
        )
    price_diff = exchange.get("price_diff_minor", 0)
    payment_kind = exchange.get("payment_method_kind")
    gc_balance = exchange.get("gift_card_balance_minor", 0)
    if (
        isinstance(price_diff, int)
        and price_diff > 0
        and payment_kind == "gift_card"
        and (not isinstance(gc_balance, int) or gc_balance < price_diff)
    ):
        return GuardDecision(
            allowed=False,
            decision_code="TAU2_RETAIL_GIFT_CARD_BALANCE_INSUFFICIENT",
            reason="Gift card balance must cover positive exchange price difference (#571 task_105).",
            details={"price_diff_minor": price_diff, "gift_card_balance_minor": gc_balance},
        )

    llm_call = payload.get("llm_call_audit", {})
    if not isinstance(llm_call, Mapping):
        return GuardDecision(
            allowed=False,
            decision_code="TAU2_LLM_CALL_AUDIT_INVALID",
            reason="llm_call_audit must be a mapping.",
            details={},
        )
    seed_requested = bool(llm_call.get("seed_requested", False))
    provider_supports_seed = bool(llm_call.get("provider_supports_seed", True))
    dropped_params_warned = bool(llm_call.get("dropped_params_warned", False))
    if seed_requested and not provider_supports_seed and not dropped_params_warned:
        return GuardDecision(
            allowed=False,
            decision_code="TAU2_SILENT_DROPPED_SEED_PARAM",
            reason="When litellm.drop_params drops a requested --seed for an unsupported provider, an explicit warning must be emitted (#567).",
            details={"seed_requested": seed_requested, "provider_supports_seed": provider_supports_seed},
        )

    return GuardDecision(
        allowed=True,
        decision_code="TAU2_RETAIL_EXCHANGE_AND_SEED_WARNING_VERIFIED",
        reason="Sierra tau2-bench retail exchange invariants and dropped-parameter warning verified.",
        details={"order_status": exchange.get("order_status")},
    )
