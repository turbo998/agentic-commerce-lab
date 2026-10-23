"""Stage 214 deterministic guard module:
UCP Custom Totals Display Text & Lodging Booking / BYOPB Cleanup,
ACP AJV $id/$ref Schema Resolution & Example Conformance,
AP2 RFC 8785 JCS Cart-to-Payment Mandate Binding & TDIP DID STARK Settlement,
x402 SVM Transaction v1 (4096B) Gate, Bazaar Route Template & Empty Filter,
Go Builder-Code Attribution, EXTENSION-RESPONSES Sidechannel, Self-Send & EIP-3009 Timeout,
MCP SEP-2828/2787 Signed Execution & Tool Attestation, SEP-2822/2841/2847,
MCP Python SDK RFC 8707 Token Exchange & Surrogate Guard, Stripe Agent Toolkit DXT/PMC,
and Sierra tau2-bench Paired A/B Scorer, Secret Redaction & Threading Lock Checkpointing.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class GuardVerdict:
    passed: bool
    ScenarioId: str
    code: str
    reason: str
    metadata: Mapping[str, Any]


STANDARD_UCP_TOTAL_TYPES = frozenset(
    {
        "items_discount",
        "subtotal",
        "discount",
        "fulfillment",
        "tax",
        "fee",
        "total",
    }
)


# ---------------------------------------------------------------------------
# PR-01: Universal-Commerce-Protocol/python-sdk#75 & #56
# ---------------------------------------------------------------------------
def audit_ucp_custom_totals_display_text_and_capability_model_reuse(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce UCP Python SDK #75 custom total display_text & #56 capability model reuse."""
    totals: Sequence[Mapping[str, Any]] = payload.get("totals", ())
    reuse_model_enabled = bool(payload.get("reuse_model_enabled", False))
    duplicate_extends_diverged = bool(payload.get("duplicate_extends_diverged", False))

    if not totals:
        return GuardVerdict(
            False,
            "PR-01",
            "UCP_TOTALS_EMPTY",
            "Totals list must not be empty.",
            {},
        )

    for entry in totals:
        t_type = str(entry.get("type", "")).strip()
        if not t_type:
            return GuardVerdict(
                False,
                "PR-01",
                "UCP_TOTAL_TYPE_MISSING",
                "Every total entry must specify a type.",
                {},
            )
        if t_type not in STANDARD_UCP_TOTAL_TYPES:
            display_text = str(entry.get("display_text", "")).strip()
            if not display_text:
                return GuardVerdict(
                    False,
                    "PR-01",
                    "UCP_CUSTOM_TOTAL_DISPLAY_TEXT_REQUIRED",
                    f"Custom total type '{t_type}' requires non-empty display_text (python-sdk#75).",
                    {"custom_type": t_type},
                )

    if not reuse_model_enabled or duplicate_extends_diverged:
        return GuardVerdict(
            False,
            "PR-01",
            "UCP_CAPABILITY_EXTENDS_MODEL_REUSE_REQUIRED",
            "Capability generation must enable --reuse-model and prevent Extends* constraint drift (python-sdk#56).",
            {
                "reuse_model_enabled": reuse_model_enabled,
                "duplicate_extends_diverged": duplicate_extends_diverged,
            },
        )

    return GuardVerdict(
        True,
        "PR-01",
        "UCP_CUSTOM_TOTALS_AND_MODEL_REUSE_VERIFIED",
        "UCP custom total display_text validator and canonical capability model reuse verified.",
        {"totals_count": len(totals)},
    )


# ---------------------------------------------------------------------------
# PR-02: Universal-Commerce-Protocol/ucp#875, #103, & #94
# ---------------------------------------------------------------------------
def audit_ucp_lodging_booking_and_byopb_payment_response_cleanup(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce UCP #875 Lodging Booking invariants, #94 BYOPB embedded action, & #103 payment response cleanup."""
    capability = str(payload.get("capability", ""))
    check_in_date = str(payload.get("check_in_date", ""))
    check_out_date = str(payload.get("check_out_date", ""))
    guest_count = int(payload.get("guest_count", 0))
    max_occupancy = int(payload.get("max_occupancy", 0))
    payment_instrument: Mapping[str, Any] = payload.get("payment_instrument", {})
    byopb_action_bound = bool(payload.get("byopb_action_bound", False))

    if capability != "dev.ucp.lodging.booking":
        return GuardVerdict(
            False,
            "PR-02",
            "UCP_LODGING_CAPABILITY_INVALID",
            "Lodging booking must declare dev.ucp.lodging.booking capability (ucp#875).",
            {"capability": capability},
        )

    if not check_in_date or not check_out_date or check_out_date <= check_in_date:
        return GuardVerdict(
            False,
            "PR-02",
            "UCP_LODGING_DATE_RANGE_INVALID",
            "check_out_date must be strictly after check_in_date (ucp#875).",
            {"check_in_date": check_in_date, "check_out_date": check_out_date},
        )

    if guest_count <= 0 or guest_count > max_occupancy:
        return GuardVerdict(
            False,
            "PR-02",
            "UCP_LODGING_OCCUPANCY_EXCEEDED",
            "guest_count must be positive and within room max_occupancy (ucp#875).",
            {"guest_count": guest_count, "max_occupancy": max_occupancy},
        )

    forbidden_response_keys = {"processor_raw_response", "gateway_response_payload", "acquirer_auth_blob"}
    leaked_keys = sorted(forbidden_response_keys.intersection(payment_instrument.keys()))
    if leaked_keys:
        return GuardVerdict(
            False,
            "PR-02",
            "UCP_PAYMENT_INSTRUMENT_RAW_RESPONSE_LEAK",
            "payment_instrument schema must strip raw payment gateway responses from checkout payload (ucp#103).",
            {"leaked_keys": leaked_keys},
        )

    if not byopb_action_bound:
        return GuardVerdict(
            False,
            "PR-02",
            "UCP_BYOPB_ACTION_NOT_BOUND",
            "Embedded checkout BYOPB flow must bind broker action descriptor in checkout.json (ucp#94).",
            {},
        )

    return GuardVerdict(
        True,
        "PR-02",
        "UCP_LODGING_AND_BYOPB_CLEANUP_VERIFIED",
        "UCP dev.ucp.lodging.booking, BYOPB action binding, and payment_instrument cleanup verified.",
        {"capability": capability, "guest_count": guest_count},
    )


# ---------------------------------------------------------------------------
# PR-03: agentic-commerce-protocol/agentic-commerce-protocol#119 & #126
# ---------------------------------------------------------------------------
def audit_acp_ajv_schema_id_ref_resolution_and_example_conformance(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce ACP #119 AJV $id/$ref schema example validation & #126 PR semantic governance."""
    registered_schema_ids = set(payload.get("registered_schema_ids", ()))
    required_schema_ids = {
        "schema.agentic_checkout.json",
        "schema.delegate_payment.json",
    }
    unresolved_refs: Sequence[str] = payload.get("unresolved_refs", ())
    invalid_examples: Sequence[str] = payload.get("invalid_examples", ())
    pr_title_valid = bool(payload.get("pr_title_valid", False))
    pr_description_non_empty = bool(payload.get("pr_description_non_empty", False))

    if not required_schema_ids.issubset(registered_schema_ids) or unresolved_refs:
        return GuardVerdict(
            False,
            "PR-03",
            "ACP_AJV_SCHEMA_REF_UNRESOLVED",
            "AJV validator must register both agentic_checkout and delegate_payment $id schemas with zero unresolved $refs (acp#119).",
            {"unresolved_refs": list(unresolved_refs)},
        )

    if invalid_examples:
        return GuardVerdict(
            False,
            "PR-03",
            "ACP_SPEC_EXAMPLE_VALIDATION_FAILED",
            "All versioned and unreleased agentic_checkout/delegate_payment examples must pass AJV validation (acp#119).",
            {"invalid_examples": list(invalid_examples)},
        )

    if not pr_title_valid or not pr_description_non_empty:
        return GuardVerdict(
            False,
            "PR-03",
            "ACP_PR_GOVERNANCE_METADATA_INVALID",
            "Spec change must satisfy PR title and non-empty description validator (acp#126).",
            {},
        )

    return GuardVerdict(
        True,
        "PR-03",
        "ACP_AJV_SCHEMA_AND_EXAMPLE_CONFORMANCE_VERIFIED",
        "ACP AJV $id/$ref resolution, example conformance, and governance checks verified.",
        {"registered_schemas": sorted(registered_schema_ids)},
    )


# ---------------------------------------------------------------------------
# PR-04: google-agentic-commerce/AP2#241 & #211
# ---------------------------------------------------------------------------
def _jcs_canonical_sha256(obj: Mapping[str, Any]) -> str:
    canonical_json = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def audit_ap2_jcs_cart_to_payment_mandate_binding_rfc8785(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce AP2 #241 (closes #211) RFC 8785 JCS cart_mandate_id and cart_mandate_hash binding."""
    cart_mandate: Mapping[str, Any] = payload.get("cart_mandate", {})
    payment_mandate_contents: Mapping[str, Any] = payload.get("payment_mandate_contents", {})

    cart_id = str(cart_mandate.get("id", "")).strip()
    bound_cart_id = str(payment_mandate_contents.get("cart_mandate_id", "")).strip()
    bound_cart_hash = str(payment_mandate_contents.get("cart_mandate_hash", "")).strip()

    if not cart_id or not bound_cart_id or cart_id != bound_cart_id:
        return GuardVerdict(
            False,
            "PR-04",
            "AP2_CART_MANDATE_ID_MISMATCH",
            "PaymentMandateContents.cart_mandate_id must match CartMandate.id (AP2#241).",
            {"cart_id": cart_id, "bound_cart_id": bound_cart_id},
        )

    if bound_cart_hash.startswith("fake_cart_mandate_hash_") or len(bound_cart_hash) != 64:
        return GuardVerdict(
            False,
            "PR-04",
            "AP2_PLACEHOLDER_CART_MANDATE_HASH_REJECTED",
            "Placeholder fake_cart_mandate_hash_* values are forbidden; must use RFC 8785 JCS SHA-256 (AP2#241).",
            {"bound_cart_hash": bound_cart_hash},
        )

    expected_hash = _jcs_canonical_sha256(cart_mandate)
    if bound_cart_hash != expected_hash:
        return GuardVerdict(
            False,
            "PR-04",
            "AP2_JCS_CART_MANDATE_HASH_MISMATCH",
            "PaymentMandateContents.cart_mandate_hash does not match RFC 8785 JCS SHA-256 of CartMandate (AP2#241).",
            {"expected_hash": expected_hash, "bound_cart_hash": bound_cart_hash},
        )

    return GuardVerdict(
        True,
        "PR-04",
        "AP2_JCS_CART_TO_PAYMENT_MANDATE_VERIFIED",
        "AP2 RFC 8785 JCS cart_mandate_id and cart_mandate_hash cryptographic binding verified.",
        {"cart_mandate_id": cart_id, "cart_mandate_hash": expected_hash},
    )


# ---------------------------------------------------------------------------
# PR-05: google-agentic-commerce/AP2#256 & #188
# ---------------------------------------------------------------------------
def audit_ap2_tenzro_did_stark_settlement_and_adk_session_serialization(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce AP2 #256 did:tenzro STARK settlement commitment & #188 ADK model_dump() session state."""
    payer_did = str(payload.get("payer_did", ""))
    merchant_did = str(payload.get("merchant_did", ""))
    mandate_chain = list(payload.get("mandate_chain", ()))
    stark_commitment_verified = bool(payload.get("stark_commitment_verified", False))
    session_state_values_json_serializable = bool(
        payload.get("session_state_values_json_serializable", False)
    )
    raw_pydantic_in_sqlite_session = bool(payload.get("raw_pydantic_in_sqlite_session", False))

    if not payer_did.startswith("did:tenzro:") or not merchant_did.startswith("did:tenzro:"):
        return GuardVerdict(
            False,
            "PR-05",
            "AP2_DID_IDENTITY_PREFIX_INVALID",
            "DID settlement requires valid did:tenzro: identifiers for payer and merchant (AP2#256).",
            {"payer_did": payer_did, "merchant_did": merchant_did},
        )

    if mandate_chain != ["IntentMandate", "CartMandate", "PaymentMandate"] or not stark_commitment_verified:
        return GuardVerdict(
            False,
            "PR-05",
            "AP2_DID_STARK_COMMITMENT_INVALID",
            "Complete IntentMandate -> CartMandate -> PaymentMandate chain and verified STARK commitment required (AP2#256).",
            {"mandate_chain": mandate_chain, "stark_commitment_verified": stark_commitment_verified},
        )

    if raw_pydantic_in_sqlite_session or not session_state_values_json_serializable:
        return GuardVerdict(
            False,
            "PR-05",
            "AP2_ADK_SESSION_UNSERIALIZED_PYDANTIC_MODEL",
            "Pydantic models must be serialized via .model_dump() before storing in sqlite_session_service state (AP2#188).",
            {"raw_pydantic_in_sqlite_session": raw_pydantic_in_sqlite_session},
        )

    return GuardVerdict(
        True,
        "PR-05",
        "AP2_DID_STARK_AND_SESSION_SERIALIZATION_VERIFIED",
        "AP2 did:tenzro STARK settlement commitment and ADK .model_dump() session serialization verified.",
        {"payer_did": payer_did, "merchant_did": merchant_did},
    )


# ---------------------------------------------------------------------------
# PR-06: x402-foundation/x402#3317 & #3329
# ---------------------------------------------------------------------------
def audit_x402_svm_transaction_v1_size_gate_and_pinet_exact_scheme(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce x402 #3317 Solana Transaction v1 (4096B) & version gate + #3329 Pi Network exact scheme."""
    protocol_path = str(payload.get("protocol_path", "v2_exact"))
    tx_version = payload.get("tx_version", 1)
    tx_size_bytes = int(payload.get("tx_size_bytes", 0))
    pinet_network = str(payload.get("pinet_network", "pinet:mainnet"))
    pinet_scheme = str(payload.get("pinet_scheme", "exact"))

    if protocol_path == "v1_legacy_exact":
        if tx_version not in (0, "legacy") or tx_size_bytes > 1232:
            return GuardVerdict(
                False,
                "PR-06",
                "X402_SVM_LEGACY_PATH_V1_TX_REJECTED",
                "Legacy v1 facilitator path must close version gate against Transaction v1 or >1232B payloads (x402#3317).",
                {"tx_version": tx_version, "tx_size_bytes": tx_size_bytes},
            )
    elif protocol_path == "v2_exact":
        if tx_version not in (0, 1, "legacy") or tx_size_bytes <= 0 or tx_size_bytes > 4096:
            return GuardVerdict(
                False,
                "PR-06",
                "X402_SVM_TX_V1_SIZE_OR_VERSION_INVALID",
                "SVM v2 exact facilitator supports Transaction v0/v1 up to 4096 bytes (SIMD-0385/0296, x402#3317).",
                {"tx_version": tx_version, "tx_size_bytes": tx_size_bytes},
            )
    else:
        return GuardVerdict(
            False,
            "PR-06",
            "X402_SVM_UNKNOWN_PROTOCOL_PATH",
            "Unknown SVM facilitator protocol path.",
            {"protocol_path": protocol_path},
        )

    if pinet_scheme != "exact" or not pinet_network.startswith("pinet:"):
        return GuardVerdict(
            False,
            "PR-06",
            "X402_PINET_EXACT_SCHEME_INVALID",
            "Pi Network payment requirement must bind scheme='exact' and 'pinet:*' CAIP-2 namespace (x402#3329).",
            {"pinet_scheme": pinet_scheme, "pinet_network": pinet_network},
        )

    return GuardVerdict(
        True,
        "PR-06",
        "X402_SVM_TX_V1_AND_PINET_VERIFIED",
        "x402 SVM Transaction v1 (4096B) version gate and Pi Network exact scheme verified.",
        {"protocol_path": protocol_path, "tx_version": tx_version, "tx_size_bytes": tx_size_bytes},
    )


# ---------------------------------------------------------------------------
# PR-07: x402-foundation/x402#3309 & #3298
# ---------------------------------------------------------------------------
def audit_x402_bazaar_withx402_route_template_and_empty_filter_conformance(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce x402 #3309 Next.js withX402 routeTemplate & #3298 Bazaar discovery non-matching filter rules."""
    route_template = str(payload.get("route_template", ""))
    supplied_filter = str(payload.get("supplied_filter", ""))
    matched_count = int(payload.get("matched_count", 0))
    returned_items_count = int(payload.get("returned_items_count", 0))
    unapplied_filters: Sequence[str] = payload.get("unapplied_filters", ())

    if not route_template or route_template in ("*", ":var1", "/:var1"):
        return GuardVerdict(
            False,
            "PR-07",
            "X402_BAZAAR_WILDCARD_ROUTE_TEMPLATE_INVALID",
            "withX402() must not index bare '*' as routeTemplate ':var1' in Bazaar discovery (x402#3309).",
            {"route_template": route_template},
        )

    if supplied_filter and matched_count == 0:
        filter_applied_empty = returned_items_count == 0
        filter_declared_unapplied = supplied_filter in unapplied_filters
        if not (filter_applied_empty or filter_declared_unapplied):
            return GuardVerdict(
                False,
                "PR-07",
                "X402_BAZAAR_UNMATCHED_FILTER_SILENTLY_IGNORED",
                "GET /discovery/resources must either return 0 items or list the filter in unappliedFilters (x402#3298).",
                {
                    "supplied_filter": supplied_filter,
                    "returned_items_count": returned_items_count,
                    "unapplied_filters": list(unapplied_filters),
                },
            )

    return GuardVerdict(
        True,
        "PR-07",
        "X402_BAZAAR_ROUTE_TEMPLATE_AND_FILTER_VERIFIED",
        "x402 Bazaar withX402 concrete routeTemplate and empty-match filter conformance verified.",
        {"route_template": route_template},
    )


# ---------------------------------------------------------------------------
# PR-08: x402-foundation/x402#3302 & #3301
# ---------------------------------------------------------------------------
def audit_x402_go_builder_code_attribution_and_extension_responses_sidechannel(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce x402 #3302 builder-code attribution & #3301 EXTENSION-RESPONSES sidechannel isolation."""
    server_declared_app_code = str(payload.get("server_declared_app_code", ""))
    root_app_code = str(payload.get("root_app_code", ""))
    nested_info_app_code = str(payload.get("nested_info_app_code", ""))
    extension_responses_sidechannel_populated = bool(
        payload.get("extension_responses_sidechannel_populated", False)
    )
    extension_responses_leaked_in_buyer_json = bool(
        payload.get("extension_responses_leaked_in_buyer_json", False)
    )

    if root_app_code and nested_info_app_code and root_app_code != nested_info_app_code:
        return GuardVerdict(
            False,
            "PR-08",
            "X402_BUILDER_CODE_ROOT_NESTED_CONFLICT",
            "Conflicting root and nested info builder-code app attribution values must be rejected (x402#3302).",
            {"root_app_code": root_app_code, "nested_info_app_code": nested_info_app_code},
        )

    effective_app_code = root_app_code or nested_info_app_code
    if not server_declared_app_code or effective_app_code != server_declared_app_code:
        return GuardVerdict(
            False,
            "PR-08",
            "X402_BUILDER_CODE_UNDECLARED_OR_MISMATCHED",
            "Go resource server must reject undeclared or mismatched builder-code app attribution (x402#3302).",
            {
                "server_declared_app_code": server_declared_app_code,
                "effective_app_code": effective_app_code,
            },
        )

    if not extension_responses_sidechannel_populated or extension_responses_leaked_in_buyer_json:
        return GuardVerdict(
            False,
            "PR-08",
            "X402_EXTENSION_RESPONSES_SIDECHANNEL_VIOLATION",
            "EXTENSION-RESPONSES must populate Verify/Settle sidechannel and be excluded (json:\"-\") from buyer JSON (x402#3301).",
            {
                "sidechannel_populated": extension_responses_sidechannel_populated,
                "leaked_in_buyer_json": extension_responses_leaked_in_buyer_json,
            },
        )

    return GuardVerdict(
        True,
        "PR-08",
        "X402_BUILDER_CODE_AND_EXTENSION_SIDECHANNEL_VERIFIED",
        "x402 Go builder-code attribution and EXTENSION-RESPONSES sidechannel isolation verified.",
        {"app_code": effective_app_code},
    )


# ---------------------------------------------------------------------------
# PR-09: x402-foundation/x402#3295 & #3282
# ---------------------------------------------------------------------------
def audit_x402_facilitator_self_send_guard_and_eip3009_max_timeout_valid_before(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce x402 #3295 self_send_not_allowed error & #3282 Go EIP-3009 maxTimeoutSeconds validBefore."""
    payer_address = str(payload.get("payer_address", "")).strip().lower()
    pay_to_address = str(payload.get("pay_to_address", "")).strip().lower()
    now_epoch = int(payload.get("now_epoch", 0))
    max_timeout_seconds = int(payload.get("max_timeout_seconds", 0))
    eip3009_valid_before = int(payload.get("eip3009_valid_before", 0))

    if not payer_address or not pay_to_address or payer_address == pay_to_address:
        return GuardVerdict(
            False,
            "PR-09",
            "X402_FACILITATOR_SELF_SEND_NOT_ALLOWED",
            "Facilitator must reject self-payment where payer equals payTo with self_send_not_allowed (x402#3295).",
            {"payer_address": payer_address, "pay_to_address": pay_to_address},
        )

    expected_valid_before = now_epoch + max_timeout_seconds
    if max_timeout_seconds <= 0 or eip3009_valid_before != expected_valid_before:
        return GuardVerdict(
            False,
            "PR-09",
            "X402_EIP3009_VALID_BEFORE_TIMEOUT_DRIFT",
            "Go EIP-3009 validBefore must equal now + paymentRequirements.maxTimeoutSeconds, not hardcoded +1h (x402#3282).",
            {
                "expected_valid_before": expected_valid_before,
                "eip3009_valid_before": eip3009_valid_before,
            },
        )

    return GuardVerdict(
        True,
        "PR-09",
        "X402_SELF_SEND_AND_EIP3009_TIMEOUT_VERIFIED",
        "x402 facilitator self_send_not_allowed guard and EIP-3009 maxTimeoutSeconds validBefore verified.",
        {"valid_before": eip3009_valid_before},
    )


# ---------------------------------------------------------------------------
# PR-10: x402-foundation/x402#3283 & #3323
# ---------------------------------------------------------------------------
def audit_x402_auth_capture_client_v1_1_and_solana_upto_facilitator(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce x402 #3283 auth-capture v1.1 client bounds & #3323 Solana upto facilitator ceiling."""
    auth_capture_version = str(payload.get("auth_capture_version", ""))
    authorized_minor = int(payload.get("authorized_minor", 0))
    capture_minor = int(payload.get("capture_minor", 0))
    solana_upto_max_lamports = int(payload.get("solana_upto_max_lamports", 0))
    solana_settled_lamports = int(payload.get("solana_settled_lamports", 0))

    if auth_capture_version != "1.1" or authorized_minor <= 0 or capture_minor > authorized_minor:
        return GuardVerdict(
            False,
            "PR-10",
            "X402_AUTH_CAPTURE_V1_1_BOUND_VIOLATION",
            "auth-capture v1.1 requires capture_minor <= authorized_minor and version '1.1' (x402#3283).",
            {
                "auth_capture_version": auth_capture_version,
                "authorized_minor": authorized_minor,
                "capture_minor": capture_minor,
            },
        )

    if solana_upto_max_lamports <= 0 or solana_settled_lamports > solana_upto_max_lamports:
        return GuardVerdict(
            False,
            "PR-10",
            "X402_SOLANA_UPTO_CEILING_EXCEEDED",
            "Solana upto facilitator settlement must not exceed max authorized lamports (x402#3323).",
            {
                "solana_upto_max_lamports": solana_upto_max_lamports,
                "solana_settled_lamports": solana_settled_lamports,
            },
        )

    return GuardVerdict(
        True,
        "PR-10",
        "X402_AUTH_CAPTURE_V1_1_AND_SOLANA_UPTO_VERIFIED",
        "x402 auth-capture client v1.1 and Solana upto facilitator ceiling verified.",
        {"capture_minor": capture_minor, "solana_settled_lamports": solana_settled_lamports},
    )


# ---------------------------------------------------------------------------
# PR-11: modelcontextprotocol/modelcontextprotocol#2828 & #2787
# ---------------------------------------------------------------------------
def audit_mcp_server_signed_execution_record_and_tool_call_attestation(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce MCP SEP-2828 Server-Side Signed Execution Record & SEP-2787 Tool Call Attestation."""
    attestation: Mapping[str, Any] = payload.get("client_tool_attestation", {})
    execution_record: Mapping[str, Any] = payload.get("server_execution_record", {})

    required_attestation_fields = {"intent", "agent_id", "tool_name", "arguments_sha256", "client_signature"}
    if not required_attestation_fields.issubset(attestation.keys()) or not all(
        str(attestation.get(k, "")).strip() for k in required_attestation_fields
    ):
        return GuardVerdict(
            False,
            "PR-11",
            "MCP_SEP2787_TOOL_ATTESTATION_INCOMPLETE",
            "SEP-2787 Tool Call Attestation requires non-empty intent, agent_id, tool_name, arguments_sha256, and client_signature (mcp#2787).",
            {},
        )

    required_record_fields = {"policy_decision", "execution_outcome_sha256", "attestation_ref", "server_signature"}
    if not required_record_fields.issubset(execution_record.keys()) or not all(
        str(execution_record.get(k, "")).strip() for k in required_record_fields
    ):
        return GuardVerdict(
            False,
            "PR-11",
            "MCP_SEP2828_EXECUTION_RECORD_INCOMPLETE",
            "SEP-2828 Server-Side Signed Execution Record requires policy_decision, execution_outcome_sha256, attestation_ref, and server_signature (mcp#2828).",
            {},
        )

    if execution_record.get("policy_decision") != "allow":
        return GuardVerdict(
            False,
            "PR-11",
            "MCP_SEP2828_POLICY_DECISION_DENIED",
            "Server-Side Signed Execution Record policy_decision did not allow tool call execution (mcp#2828).",
            {"policy_decision": execution_record.get("policy_decision")},
        )

    return GuardVerdict(
        True,
        "PR-11",
        "MCP_SIGNED_EXECUTION_RECORD_AND_ATTESTATION_VERIFIED",
        "MCP SEP-2787 Tool Call Attestation and SEP-2828 Server-Side Signed Execution Record verified.",
        {"tool_name": attestation.get("tool_name")},
    )


# ---------------------------------------------------------------------------
# PR-12: modelcontextprotocol/modelcontextprotocol#2822, #2841, & #2847
# ---------------------------------------------------------------------------
_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,128}$")
_CANONICAL_MCP_ERROR_TAXONOMY = frozenset(
    {
        "RESOURCE_NOT_FOUND",
        "TOOL_NOT_FOUND",
        "INVALID_TOOL_ARGUMENTS",
        "UNAUTHORIZED_SCOPE",
        "RATE_LIMITED",
        "UPSTREAM_TIMEOUT",
    }
)


def audit_mcp_client_session_id_error_taxonomy_and_structured_content(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce MCP SEP-2822 Mcp-Client-Session-Id, #2841 Error Taxonomy, & #2847 structuredContent."""
    transport = str(payload.get("transport", "streamable_http"))
    header_session_id = str(payload.get("mcp_client_session_id_header", ""))
    meta_session_id = str(payload.get("params_meta_session_id", ""))
    error_taxonomy_code = str(payload.get("error_taxonomy_code", ""))
    has_structured_content = bool(payload.get("has_structured_content", False))
    duplicated_json_in_text_content = bool(payload.get("duplicated_json_in_text_content", False))

    active_session_id = header_session_id if transport == "streamable_http" else meta_session_id
    if not _SESSION_ID_RE.match(active_session_id):
        return GuardVerdict(
            False,
            "PR-12",
            "MCP_SEP2822_CLIENT_SESSION_ID_INVALID",
            "SEP-2822 requires a valid Mcp-Client-Session-Id on HTTP header or params._meta (mcp#2822).",
            {"transport": transport, "active_session_id": active_session_id},
        )

    if error_taxonomy_code not in _CANONICAL_MCP_ERROR_TAXONOMY:
        return GuardVerdict(
            False,
            "PR-12",
            "MCP_ERROR_TAXONOMY_NON_CANONICAL",
            "MCP error must map to a canonical cross-SDK error taxonomy identifier (mcp#2841).",
            {"error_taxonomy_code": error_taxonomy_code},
        )

    if not has_structured_content or duplicated_json_in_text_content:
        return GuardVerdict(
            False,
            "PR-12",
            "MCP_STRUCTURED_CONTENT_DUPLICATION_VIOLATION",
            "Tool result with structuredContent should not redundantly duplicate raw JSON inside TextContent (mcp#2847).",
            {"duplicated_json_in_text_content": duplicated_json_in_text_content},
        )

    return GuardVerdict(
        True,
        "PR-12",
        "MCP_CLIENT_SESSION_ERROR_TAXONOMY_AND_STRUCTURED_CONTENT_VERIFIED",
        "MCP SEP-2822 Client Session ID, #2841 error taxonomy, and #2847 structuredContent verified.",
        {"session_id": active_session_id, "error_taxonomy_code": error_taxonomy_code},
    )


# ---------------------------------------------------------------------------
# PR-13: modelcontextprotocol/python-sdk#3739, #3708, & #3667
# ---------------------------------------------------------------------------
def _contains_lone_surrogate(text: str) -> bool:
    return any(0xD800 <= ord(ch) <= 0xDFFF for ch in text)


def audit_mcp_python_sdk_rfc8707_token_exchange_and_utf8_surrogate_transport_guard(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce MCP Python SDK #3739 RFC 8707 resource in token exchange, #3708 lone surrogates, & #3667 bytes output."""
    grant_type = str(payload.get("grant_type", ""))
    resource_indicator = str(payload.get("resource_indicator", ""))
    transport_message = str(payload.get("transport_message", ""))
    raw_bytes_output: bytes | None = payload.get("raw_bytes_output")
    encoded_bytes_output = str(payload.get("encoded_bytes_output", ""))

    if grant_type != "urn:ietf:params:oauth:grant-type:token-exchange" or not resource_indicator.startswith("https://"):
        return GuardVerdict(
            False,
            "PR-13",
            "MCP_RFC8707_TOKEN_EXCHANGE_RESOURCE_MISSING",
            "OAuth token-exchange grant must preserve HTTPS RFC 8707 resource indicator (python-sdk#3739).",
            {"grant_type": grant_type, "resource_indicator": resource_indicator},
        )

    if _contains_lone_surrogate(transport_message):
        return GuardVerdict(
            False,
            "PR-13",
            "MCP_TRANSPORT_LONE_SURROGATE_CONTAINED",
            "Transport writer must contain and reject lone UTF-16 surrogates (\\uD800-\\uDFFF) before serialization crash (python-sdk#3708).",
            {},
        )

    if raw_bytes_output is not None:
        expected_b64 = base64.b64encode(raw_bytes_output).decode("ascii")
        if encoded_bytes_output != expected_b64:
            return GuardVerdict(
                False,
                "PR-13",
                "MCP_BYTES_TOOL_OUTPUT_NOT_BASE64_ENCODED",
                "Non-UTF-8 bytes tool output must be base64-encoded instead of raising UnicodeDecodeError (python-sdk#3667).",
                {"expected_b64": expected_b64, "encoded_bytes_output": encoded_bytes_output},
            )

    return GuardVerdict(
        True,
        "PR-13",
        "MCP_PYTHON_SDK_TOKEN_EXCHANGE_AND_TRANSPORT_VERIFIED",
        "MCP Python SDK RFC 8707 token-exchange resource, lone-surrogate containment, and base64 bytes encoding verified.",
        {"resource_indicator": resource_indicator},
    )


# ---------------------------------------------------------------------------
# PR-14: stripe/agent-toolkit#119, #103, & #87
# ---------------------------------------------------------------------------
def audit_stripe_agent_toolkit_dxt_manifest_pmc_and_subscription_checkout_metadata(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce Stripe Agent Toolkit #119 DXT RAK key, #103 payment_method_configuration, & #87 subscription_data."""
    dxt_manifest_version = str(payload.get("dxt_manifest_version", ""))
    stripe_api_key_prefix = str(payload.get("stripe_api_key_prefix", ""))
    pmc_id = str(payload.get("payment_method_configuration_id", ""))
    subscription_data: Mapping[str, Any] = payload.get("subscription_data", {})

    if not dxt_manifest_version or stripe_api_key_prefix not in ("rk_live_", "rk_test_"):
        return GuardVerdict(
            False,
            "PR-14",
            "STRIPE_DXT_RESTRICTED_KEY_REQUIRED",
            "Stripe DXT manifest must require restricted API key (rk_live_/rk_test_) ahead of 2026-10-31 cutoff (agent-toolkit#119).",
            {"stripe_api_key_prefix": stripe_api_key_prefix},
        )

    if not pmc_id.startswith("pmc_"):
        return GuardVerdict(
            False,
            "PR-14",
            "STRIPE_PMC_ID_INVALID",
            "payment_method_configuration list/update requires valid pmc_* identifier (agent-toolkit#103).",
            {"pmc_id": pmc_id},
        )

    trial_days = int(subscription_data.get("trial_period_days", -1))
    metadata = subscription_data.get("metadata")
    if trial_days < 0 or trial_days > 730 or not isinstance(metadata, Mapping) or not metadata:
        return GuardVerdict(
            False,
            "PR-14",
            "STRIPE_CHECKOUT_SUBSCRIPTION_DATA_INVALID",
            "Checkout Session subscription_data requires bounded trial_period_days and non-empty metadata dict (agent-toolkit#87).",
            {"trial_period_days": trial_days},
        )

    return GuardVerdict(
        True,
        "PR-14",
        "STRIPE_DXT_PMC_AND_SUBSCRIPTION_CHECKOUT_VERIFIED",
        "Stripe Agent Toolkit DXT manifest, payment_method_configuration, and Checkout subscription_data verified.",
        {"pmc_id": pmc_id, "trial_period_days": trial_days},
    )


# ---------------------------------------------------------------------------
# PR-15: sierra-research/tau2-bench#505 & #503
# ---------------------------------------------------------------------------
def audit_tau2_paired_ab_scorer_secret_redaction_and_token_cache_ttft_guard(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce Sierra tau2-bench #505 paired A/B scorer + secret redaction & #503 token-cache TTFT guard."""
    arm_a_task_ids = list(payload.get("arm_a_task_ids", ()))
    arm_b_task_ids = list(payload.get("arm_b_task_ids", ()))
    infra_429_included_in_audit = bool(payload.get("infra_429_included_in_audit", False))
    max_steps_included_in_action_checks = bool(
        payload.get("max_steps_included_in_action_checks", False)
    )
    rollout_log_text = str(payload.get("rollout_log_text", ""))
    ttft_ms = float(payload.get("ttft_ms", 9999.0))
    prefix_cache_metrics_recorded = bool(payload.get("prefix_cache_metrics_recorded", False))

    if not arm_a_task_ids or arm_a_task_ids != arm_b_task_ids:
        return GuardVerdict(
            False,
            "PR-15",
            "TAU2_UNPAIRED_AB_TASK_SET_REJECTED",
            "A/B evaluation must score identical paired task sets rather than mismatched partial runs (tau2-bench#505).",
            {"arm_a_count": len(arm_a_task_ids), "arm_b_count": len(arm_b_task_ids)},
        )

    if not infra_429_included_in_audit or not max_steps_included_in_action_checks:
        return GuardVerdict(
            False,
            "PR-15",
            "TAU2_AB_DENOMINATOR_SURVIVORSHIP_BIAS",
            "Paired A/B scorer must account for 429 infra deaths and max_steps premature terminations (tau2-bench#505).",
            {},
        )

    if any(tok in rollout_log_text for tok in ("sk-", "Bearer ", "SUPABASE_SERVICE_ROLE_KEY=")):
        return GuardVerdict(
            False,
            "PR-15",
            "TAU2_ROLLOUT_SECRET_LEAK_DETECTED",
            "Rollout artifacts must redact API keys and service-role secrets before publishing (tau2-bench#505).",
            {},
        )

    if ttft_ms > 3000.0 or not prefix_cache_metrics_recorded:
        return GuardVerdict(
            False,
            "PR-15",
            "TAU2_TOKEN_CACHE_TTFT_SLO_EXCEEDED",
            "Token-cache benchmark requires TTFT <= 3000 ms and recorded prefix-cache bucket metrics (tau2-bench#503).",
            {"ttft_ms": ttft_ms, "prefix_cache_metrics_recorded": prefix_cache_metrics_recorded},
        )

    return GuardVerdict(
        True,
        "PR-15",
        "TAU2_PAIRED_AB_AND_TOKEN_CACHE_VERIFIED",
        "Sierra tau2-bench paired A/B scorer, secret redaction, and token-cache TTFT guard verified.",
        {"paired_tasks": len(arm_a_task_ids), "ttft_ms": ttft_ms},
    )


# ---------------------------------------------------------------------------
# PR-16: sierra-research/tau2-bench#524 & #501
# ---------------------------------------------------------------------------
def audit_tau2_batch_worker_interleaving_and_threading_lock_checkpoint_guard(
    payload: Mapping[str, Any],
) -> GuardVerdict:
    """Enforce Sierra tau2-bench #524 interleaved worker scheduling & #501 threading.Lock checkpointing."""
    interleaved_across_runs = bool(payload.get("interleaved_across_runs", False))
    worker_log_handle_closed_cleanly = bool(payload.get("worker_log_handle_closed_cleanly", False))
    checkpoint_lock_type = str(payload.get("checkpoint_lock_type", ""))

    if not interleaved_across_runs or not worker_log_handle_closed_cleanly:
        return GuardVerdict(
            False,
            "PR-16",
            "TAU2_BATCH_SCHEDULING_OR_LOG_HANDLE_INVALID",
            "Batch runner must interleave units across concurrent runs and own worker log handles cleanly (tau2-bench#524).",
            {
                "interleaved_across_runs": interleaved_across_runs,
                "worker_log_handle_closed_cleanly": worker_log_handle_closed_cleanly,
            },
        )

    if checkpoint_lock_type != "threading.Lock":
        return GuardVerdict(
            False,
            "PR-16",
            "TAU2_IPC_MULTIPROCESSING_LOCK_REJECTED",
            "Checkpointing must use threading.Lock in controller process instead of IPC multiprocessing.Lock (tau2-bench#501).",
            {"checkpoint_lock_type": checkpoint_lock_type},
        )

    return GuardVerdict(
        True,
        "PR-16",
        "TAU2_BATCH_INTERLEAVING_AND_THREADING_LOCK_VERIFIED",
        "Sierra tau2-bench batch worker interleaving and threading.Lock checkpointing verified.",
        {"checkpoint_lock_type": checkpoint_lock_type},
    )
