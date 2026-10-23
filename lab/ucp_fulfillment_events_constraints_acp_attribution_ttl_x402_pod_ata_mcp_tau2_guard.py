"""Stage 206 deterministic runtime guardrails for 2026-10-23 (PR-01..PR-16).

Covers primary-source verified specifications and bug fixes across:
- Universal-Commerce-Protocol/ucp (#729, #728, #564, #614, #547, #417, #394)
- agentic-commerce-protocol/agentic-commerce-protocol (#152, #124, #97, #98)
- x402-foundation/x402 (#3379, #3291, #2725, #2498, #2802, #3649, #2975, #2761, #3556, #3560, #3586, #2368)
- modelcontextprotocol/modelcontextprotocol (#2920, #1488, #1913, #2127)
- sierra-research/tau2-bench (#647, #624, #549, #678)
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json
import re
from typing import Any, Mapping, Sequence


WELL_KNOWN_FULFILLMENT_EVENT_TYPES = frozenset(
    {"processing", "shipped", "in_transit", "delivered", "canceled"}
)
AD_HOC_FULFILLMENT_SYNONYMS = {
    "in-transit": "in_transit",
    "intransit": "in_transit",
    "dispatched": "shipped",
    "handed_to_carrier": "shipped",
    "cancelled": "canceled",
    "completed": "delivered",
    "preparing": "processing",
}
ALLOWED_ADDRESS_CONSTRAINT_FIELDS = frozenset(
    {
        "street_address",
        "extended_address",
        "address_locality",
        "address_region",
        "address_country",
        "postal_code",
        "first_name",
        "last_name",
        "phone_number",
    }
)
ACP_DISCOVERY_METHODS = frozenset(
    {
        "direct_search",
        "recommendation",
        "comparison",
        "browsing",
        "reorder",
        "wishlist_match",
        "promotion",
        "external_referral",
    }
)
ACP_DISCOVERY_SESSION_TYPES = frozenset(
    {
        "active_shopping",
        "passive_suggestion",
        "automated_reorder",
        "gift_recommendation",
    }
)
SENSITIVITY_ORDER = {"low": 1, "medium": 2, "high": 3}
SECP256K1_HALF_N = int(
    "7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0", 16
)
HEX_64_RE = re.compile(r"^[0-9a-f]{64}$")
SERVER_TIMING_UCP_RE = re.compile(r"(?:^|,)\s*ucp\s*;\s*dur=(\d+(?:\.\d+)?)\b")


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    decision_code: str
    reason: str
    metadata: dict[str, Any]


# ---------------------------------------------------------------------------
# PR-01: Universal-Commerce-Protocol/ucp#729 & #728
# Standardized consumer-facing fulfillment.events[].type & fallback
# ---------------------------------------------------------------------------
def audit_ucp_fulfillment_event_types(
    events: Sequence[Mapping[str, Any]],
    *,
    platform_rejects_unknown_event_type: bool = False,
) -> GuardDecision:
    if platform_rejects_unknown_event_type or not events:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_FULFILLMENT_EVENT_TYPE_OR_FALLBACK_VIOLATION_BLOCKED",
            reason=(
                "Platform must tolerate unknown fulfillment.events[].type values via "
                "description fallback, and events[] must be non-empty."
            ),
            metadata={"platform_rejects_unknown_event_type": platform_rejects_unknown_event_type},
        )

    normalized_types: list[str] = []
    for ev in events:
        ev_type = str(ev.get("type", "")).strip()
        desc = str(ev.get("description", "")).strip()
        semantic_kind = str(ev.get("semantic_kind", "")).strip()

        if not ev_type or ev_type.lower() in AD_HOC_FULFILLMENT_SYNONYMS:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_FULFILLMENT_EVENT_TYPE_OR_FALLBACK_VIOLATION_BLOCKED",
                reason=(
                    f"Fulfillment event type '{ev_type}' uses an ad-hoc synonym instead of "
                    "the standardized well-known value."
                ),
                metadata={"invalid_type": ev_type},
            )

        if semantic_kind in WELL_KNOWN_FULFILLMENT_EVENT_TYPES and ev_type != semantic_kind:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_FULFILLMENT_EVENT_TYPE_OR_FALLBACK_VIOLATION_BLOCKED",
                reason=(
                    f"Event with standard semantic '{semantic_kind}' MUST use well-known "
                    f"type '{semantic_kind}', got '{ev_type}'."
                ),
                metadata={"semantic_kind": semantic_kind, "actual_type": ev_type},
            )

        if ev_type not in WELL_KNOWN_FULFILLMENT_EVENT_TYPES and not desc:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_FULFILLMENT_EVENT_TYPE_OR_FALLBACK_VIOLATION_BLOCKED",
                reason=(
                    f"Non-standard fulfillment event type '{ev_type}' MUST include a "
                    "non-empty consumer-facing description fallback."
                ),
                metadata={"custom_type": ev_type},
            )
        normalized_types.append(ev_type)

    return GuardDecision(
        allowed=True,
        decision_code="UCP_FULFILLMENT_EVENT_TYPES_VERIFIED",
        reason="Fulfillment events obey well-known types and non-standard description fallback.",
        metadata={"event_types": normalized_types},
    )


# ---------------------------------------------------------------------------
# PR-02: Universal-Commerce-Protocol/ucp#564
# Typed Constraint / AddressConstraint & fulfillment destination required_fields
# ---------------------------------------------------------------------------
def audit_ucp_fulfillment_destination_and_billing_constraints(
    *,
    destination_required_fields: Sequence[str],
    provided_destination_address: Mapping[str, Any],
    instrument_required_fields: Sequence[str],
    billing_address_required_fields: Sequence[str],
    provided_billing_address: Mapping[str, Any] | None,
) -> GuardDecision:
    if not destination_required_fields or len(set(destination_required_fields)) != len(
        destination_required_fields
    ):
        return GuardDecision(
            allowed=False,
            decision_code="UCP_CONSTRAINT_SCHEMA_OR_REQUIRED_FIELDS_VIOLATION_BLOCKED",
            reason="destination.required_fields must be non-empty and unique.",
            metadata={"destination_required_fields": list(destination_required_fields)},
        )

    invalid_dest_fields = [
        f for f in destination_required_fields if f not in ALLOWED_ADDRESS_CONSTRAINT_FIELDS
    ]
    invalid_bill_fields = [
        f for f in billing_address_required_fields if f not in ALLOWED_ADDRESS_CONSTRAINT_FIELDS
    ]
    invalid_inst_fields = [f for f in instrument_required_fields if f != "billing_address"]
    if invalid_dest_fields or invalid_bill_fields or invalid_inst_fields:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_CONSTRAINT_SCHEMA_OR_REQUIRED_FIELDS_VIOLATION_BLOCKED",
            reason="Constraint required_fields contain property names outside AddressConstraint/InstrumentConstraint.",
            metadata={
                "invalid_dest_fields": invalid_dest_fields,
                "invalid_bill_fields": invalid_bill_fields,
                "invalid_inst_fields": invalid_inst_fields,
            },
        )

    missing_dest = [
        f
        for f in destination_required_fields
        if not str(provided_destination_address.get(f, "")).strip()
    ]
    if missing_dest:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_CONSTRAINT_SCHEMA_OR_REQUIRED_FIELDS_VIOLATION_BLOCKED",
            reason=f"Destination address is missing constrained required_fields: {missing_dest}.",
            metadata={"missing_destination_fields": missing_dest},
        )

    if "billing_address" in instrument_required_fields:
        if not isinstance(provided_billing_address, Mapping):
            return GuardDecision(
                allowed=False,
                decision_code="UCP_CONSTRAINT_SCHEMA_OR_REQUIRED_FIELDS_VIOLATION_BLOCKED",
                reason="billing_address is required by instrument constraints but missing.",
                metadata={},
            )
        missing_bill = [
            f
            for f in billing_address_required_fields
            if not str(provided_billing_address.get(f, "")).strip()
        ]
        if missing_bill:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_CONSTRAINT_SCHEMA_OR_REQUIRED_FIELDS_VIOLATION_BLOCKED",
                reason=f"Billing address is missing constrained required_fields: {missing_bill}.",
                metadata={"missing_billing_fields": missing_bill},
            )

    return GuardDecision(
        allowed=True,
        decision_code="UCP_FULFILLMENT_AND_BILLING_CONSTRAINTS_VERIFIED",
        reason="Fulfillment destination and payment instrument AddressConstraint fields satisfied.",
        metadata={"destination_required_fields": list(destination_required_fields)},
    )


# ---------------------------------------------------------------------------
# PR-03: Universal-Commerce-Protocol/ucp#614 & #547
# Atomic core release versioning snapshot D & Server-Timing: ucp;dur=<ms>
# ---------------------------------------------------------------------------
def audit_ucp_atomic_release_version_and_server_timing(
    *,
    selected_release: str,
    profile_ucp_version: str,
    declaration_versions: Mapping[str, str],
    requires_substitutes_version: bool,
    server_timing_header: str | None,
    http_status: int,
) -> GuardDecision:
    if (
        not selected_release
        or profile_ucp_version != selected_release
        or requires_substitutes_version
        or not declaration_versions
    ):
        return GuardDecision(
            allowed=False,
            decision_code="UCP_ATOMIC_RELEASE_MISMATCH_OR_SERVER_TIMING_INVALID_BLOCKED",
            reason=(
                "Profile ucp.version must equal selected release D, and requires.* must "
                "verify rather than substitute versions."
            ),
            metadata={
                "selected_release": selected_release,
                "profile_ucp_version": profile_ucp_version,
            },
        )

    mismatched_decls = {
        name: ver for name, ver in declaration_versions.items() if ver != selected_release
    }
    if mismatched_decls:
        return GuardDecision(
            allowed=False,
            decision_code="UCP_ATOMIC_RELEASE_MISMATCH_OR_SERVER_TIMING_INVALID_BLOCKED",
            reason=f"UCP-authored declarations drifted from atomic release {selected_release}.",
            metadata={"mismatched_declarations": mismatched_decls},
        )

    dur_ms: float | None = None
    if server_timing_header is not None:
        m = SERVER_TIMING_UCP_RE.search(server_timing_header)
        if not m:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_ATOMIC_RELEASE_MISMATCH_OR_SERVER_TIMING_INVALID_BLOCKED",
                reason="Server-Timing header must expose a valid ucp;dur=<milliseconds> metric.",
                metadata={"server_timing_header": server_timing_header},
            )
        dur_ms = float(m.group(1))
        if dur_ms < 0 or http_status < 200 or http_status >= 600:
            return GuardDecision(
                allowed=False,
                decision_code="UCP_ATOMIC_RELEASE_MISMATCH_OR_SERVER_TIMING_INVALID_BLOCKED",
                reason="Server-Timing ucp;dur metric or HTTP status is out of bounds.",
                metadata={"dur_ms": dur_ms, "http_status": http_status},
            )

    return GuardDecision(
        allowed=True,
        decision_code="UCP_ATOMIC_RELEASE_AND_SERVER_TIMING_VERIFIED",
        reason="Atomic UCP release snapshot D and Server-Timing ucp;dur metric verified.",
        metadata={"selected_release": selected_release, "ucp_dur_ms": dur_ms},
    )


# ---------------------------------------------------------------------------
# PR-04: Universal-Commerce-Protocol/ucp#417 & #394
# Cryptographic authorization-to-execution binding & non-secret participant ID
# ---------------------------------------------------------------------------
def audit_ucp_execution_intent_binding_and_participant_id(
    *,
    authorized_intent: Mapping[str, Any],
    executed_checkout: Mapping[str, Any],
    shared_secret: str,
    provided_intent_hmac: str,
    participant_id: str,
    caller_authenticated_via_own_credential: bool,
    participant_id_used_as_bearer_secret: bool,
) -> GuardDecision:
    canonical_intent = json.dumps(
        {
            "merchant_id": authorized_intent.get("merchant_id"),
            "currency": authorized_intent.get("currency"),
            "max_amount_minor": authorized_intent.get("max_amount_minor"),
            "items": authorized_intent.get("items"),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    expected_hmac = hmac.new(
        shared_secret.encode("utf-8"),
        canonical_intent.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_hmac, provided_intent_hmac):
        return GuardDecision(
            allowed=False,
            decision_code="UCP_EXECUTION_UNBOUND_TO_INTENT_OR_PARTICIPANT_ID_MISUSED_BLOCKED",
            reason="Authorization intent HMAC signature verification failed.",
            metadata={},
        )

    exec_amount = int(executed_checkout.get("total_amount_minor", -1))
    max_amount = int(authorized_intent.get("max_amount_minor", -2))
    if (
        executed_checkout.get("merchant_id") != authorized_intent.get("merchant_id")
        or executed_checkout.get("currency") != authorized_intent.get("currency")
        or executed_checkout.get("items") != authorized_intent.get("items")
        or exec_amount <= 0
        or exec_amount > max_amount
    ):
        return GuardDecision(
            allowed=False,
            decision_code="UCP_EXECUTION_UNBOUND_TO_INTENT_OR_PARTICIPANT_ID_MISUSED_BLOCKED",
            reason="Executed checkout diverges from user-authorized items, merchant, or max_amount.",
            metadata={"executed_amount_minor": exec_amount, "max_amount_minor": max_amount},
        )

    if (
        not participant_id.strip()
        or not caller_authenticated_via_own_credential
        or participant_id_used_as_bearer_secret
    ):
        return GuardDecision(
            allowed=False,
            decision_code="UCP_EXECUTION_UNBOUND_TO_INTENT_OR_PARTICIPANT_ID_MISUSED_BLOCKED",
            reason=(
                "Processor-tokenizer participant identifier is a routing value and must not "
                "be treated as a bearer secret without caller authentication."
            ),
            metadata={
                "caller_authenticated_via_own_credential": caller_authenticated_via_own_credential,
                "participant_id_used_as_bearer_secret": participant_id_used_as_bearer_secret,
            },
        )

    return GuardDecision(
        allowed=True,
        decision_code="UCP_EXECUTION_INTENT_AND_PARTICIPANT_ID_VERIFIED",
        reason="Checkout execution matches signed user authorization and routing participant_id.",
        metadata={"intent_digest": expected_hmac[:16], "participant_id": participant_id},
    )


# ---------------------------------------------------------------------------
# PR-05: agentic-commerce-protocol/agentic-commerce-protocol#152 & #124
# Discovery Attribution Extension & single AppliedDiscount consolidation
# ---------------------------------------------------------------------------
def audit_acp_discovery_attribution_and_discount_consolidation(
    *,
    discovery_context: Mapping[str, Any],
    applied_discounts: Sequence[Mapping[str, Any]],
    line_item_discount_details_present: bool,
) -> GuardDecision:
    method = str(discovery_context.get("method", ""))
    session_type = str(discovery_context.get("session_type", ""))
    query_category = str(discovery_context.get("query_category", ""))
    alternatives = int(discovery_context.get("alternatives_considered", -1))
    rank_pos = int(discovery_context.get("rank_position", 0))

    if (
        method not in ACP_DISCOVERY_METHODS
        or session_type not in ACP_DISCOVERY_SESSION_TYPES
        or not (1 <= len(query_category) <= 100)
        or alternatives < 0
        or rank_pos < 1
    ):
        return GuardDecision(
            allowed=False,
            decision_code="ACP_DISCOVERY_ATTRIBUTION_OR_DUAL_DISCOUNT_AMBIGUITY_BLOCKED",
            reason="discovery_attribution.discovery_context violates enum or bounds constraints.",
            metadata={"method": method, "session_type": session_type},
        )

    if line_item_discount_details_present:
        return GuardDecision(
            allowed=False,
            decision_code="ACP_DISCOVERY_ATTRIBUTION_OR_DUAL_DISCOUNT_AMBIGUITY_BLOCKED",
            reason="Deprecated LineItem.discount_details[] must not coexist with AppliedDiscount.",
            metadata={"line_item_discount_details_present": True},
        )

    for disc in applied_discounts:
        if "automatic" in disc or not str(disc.get("type", "")).strip() or not str(
            disc.get("description", "")
        ).strip():
            return GuardDecision(
                allowed=False,
                decision_code="ACP_DISCOVERY_ATTRIBUTION_OR_DUAL_DISCOUNT_AMBIGUITY_BLOCKED",
                reason=(
                    "Consolidated AppliedDiscount requires type + description and forbids "
                    "redundant 'automatic' boolean."
                ),
                metadata={"discount_id": disc.get("id")},
            )

    return GuardDecision(
        allowed=True,
        decision_code="ACP_DISCOVERY_ATTRIBUTION_AND_DISCOUNT_CONSOLIDATED",
        reason="ACP discovery_attribution and consolidated AppliedDiscount verified.",
        metadata={"method": method, "applied_discount_count": len(applied_discounts)},
    )


# ---------------------------------------------------------------------------
# PR-06: agentic-commerce-protocol/agentic-commerce-protocol#97 & #98
# Idempotency-Key TTL headers & intervention_required vs requires_3ds
# ---------------------------------------------------------------------------
def audit_acp_idempotency_ttl_and_intervention_error(
    *,
    first_use_epoch_s: int,
    session_expires_at_epoch_s: int,
    idempotency_key_expires_epoch_s: int,
    idempotency_key_ttl_s: int,
    required_interventions: Sequence[str],
    supported_interventions: Sequence[str],
    returned_error_code: str | None,
    agent_attempted_retry: bool,
) -> GuardDecision:
    min_required_expiry = max(
        session_expires_at_epoch_s + 86400,
        first_use_epoch_s + 86400,
    )
    expected_ttl = idempotency_key_expires_epoch_s - first_use_epoch_s
    if (
        idempotency_key_expires_epoch_s < min_required_expiry
        or idempotency_key_ttl_s < 86400
        or idempotency_key_ttl_s != expected_ttl
    ):
        return GuardDecision(
            allowed=False,
            decision_code="ACP_IDEMPOTENCY_TTL_SHORT_OR_INTERVENTION_CODE_MISUSED_BLOCKED",
            reason=(
                "Idempotency-Key retention must be >= max(session.expires_at + 24h, "
                "first_use + 24h) with matching Idempotency-Key-TTL."
            ),
            metadata={
                "idempotency_key_expires_epoch_s": idempotency_key_expires_epoch_s,
                "min_required_expiry": min_required_expiry,
            },
        )

    unsupported = [i for i in required_interventions if i not in set(supported_interventions)]
    if unsupported:
        if returned_error_code != "intervention_required" or agent_attempted_retry:
            return GuardDecision(
                allowed=False,
                decision_code="ACP_IDEMPOTENCY_TTL_SHORT_OR_INTERVENTION_CODE_MISUSED_BLOCKED",
                reason=(
                    "Unsupported required intervention must return terminal "
                    "'intervention_required' and halt retries."
                ),
                metadata={
                    "unsupported": unsupported,
                    "returned_error_code": returned_error_code,
                    "agent_attempted_retry": agent_attempted_retry,
                },
            )
    elif "3ds" in required_interventions and returned_error_code not in (None, "requires_3ds"):
        return GuardDecision(
            allowed=False,
            decision_code="ACP_IDEMPOTENCY_TTL_SHORT_OR_INTERVENTION_CODE_MISUSED_BLOCKED",
            reason="Supported 3DS challenge must use 'requires_3ds', not terminal blocker.",
            metadata={"returned_error_code": returned_error_code},
        )

    return GuardDecision(
        allowed=True,
        decision_code="ACP_IDEMPOTENCY_TTL_AND_INTERVENTION_CODE_VERIFIED",
        reason="Idempotency-Key 24h+ TTL headers and intervention error code verified.",
        metadata={"idempotency_key_ttl_s": idempotency_key_ttl_s},
    )


# ---------------------------------------------------------------------------
# PR-07: x402-foundation/x402#3379 & #3291
# proof-of-done work-receipt ledger & resolution-lineage RLP-1 state derivation
# ---------------------------------------------------------------------------
def audit_x402_proof_of_done_and_resolution_lineage(
    *,
    proof_of_done: Mapping[str, Any],
    metered_work_record: Mapping[str, Any],
    required_checks: Sequence[Mapping[str, Any]],
    target_narrowed: bool,
    claimed_resolution_state: str,
    prior_record_hash: str | None,
    declared_prev_hash: str | None,
) -> GuardDecision:
    scheme = str(proof_of_done.get("scheme", ""))
    receipt_hash = str(proof_of_done.get("receiptHash", ""))
    verify_url = str(proof_of_done.get("verifyUrl", ""))

    computed_work_hash = hashlib.sha256(
        json.dumps(metered_work_record, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    if (
        scheme != "tamga-ledger-v1"
        or not HEX_64_RE.match(receipt_hash)
        or receipt_hash != computed_work_hash
        or not verify_url.startswith("https://")
        or receipt_hash not in verify_url
    ):
        return GuardDecision(
            allowed=False,
            decision_code="X402_PROOF_OF_DONE_OR_RESOLUTION_LINEAGE_FORGED_BLOCKED",
            reason="proof-of-done extension receiptHash or verifyUrl failed ledger verification.",
            metadata={"scheme": scheme, "receipt_hash": receipt_hash},
        )

    if not required_checks or (prior_record_hash is not None and declared_prev_hash != prior_record_hash):
        return GuardDecision(
            allowed=False,
            decision_code="X402_PROOF_OF_DONE_OR_RESOLUTION_LINEAGE_FORGED_BLOCKED",
            reason="resolution-lineage requires non-empty checks and intact prev_hash linkage.",
            metadata={"prior_record_hash": prior_record_hash, "declared_prev_hash": declared_prev_hash},
        )

    statuses = [str(c.get("status", "")) for c in required_checks]
    if any(s == "FAIL" for s in statuses):
        derived_state = "FAILED"
    elif any(s == "UNRESOLVED" for s in statuses) or not all(s == "PASS" for s in statuses):
        derived_state = "UNRESOLVED"
    elif target_narrowed:
        derived_state = "NARROWED"
    else:
        derived_state = "SURVIVED"

    if claimed_resolution_state != derived_state:
        return GuardDecision(
            allowed=False,
            decision_code="X402_PROOF_OF_DONE_OR_RESOLUTION_LINEAGE_FORGED_BLOCKED",
            reason=(
                f"RLP-1 resolution state '{claimed_resolution_state}' contradicts derived "
                f"state '{derived_state}'."
            ),
            metadata={"claimed": claimed_resolution_state, "derived": derived_state},
        )

    return GuardDecision(
        allowed=True,
        decision_code="X402_PROOF_OF_DONE_AND_RESOLUTION_LINEAGE_VERIFIED",
        reason="Tamga proof-of-done receipt and RLP-1 resolution-lineage state verified.",
        metadata={"receipt_hash": receipt_hash[:16], "resolution_state": derived_state},
    )


# ---------------------------------------------------------------------------
# PR-08: x402-foundation/x402#2725 & #2498
# Normative EVM exact facilitator MUST rules & SupportedKind.capabilities
# ---------------------------------------------------------------------------
def audit_x402_evm_normative_must_and_supported_capabilities(
    *,
    eip712_domain_matched: bool,
    recovered_signer: str,
    authorization_from: str,
    signature_s_int: int,
    now_epoch_s: int,
    valid_after_s: int,
    valid_before_s: int,
    nonce_already_used: bool,
    supported_capabilities: Mapping[str, Sequence[str]] | None,
    payment_requirements_extra: Mapping[str, Any],
) -> GuardDecision:
    if (
        not eip712_domain_matched
        or not recovered_signer
        or recovered_signer.lower() != authorization_from.lower()
        or signature_s_int <= 0
        or signature_s_int > SECP256K1_HALF_N
        or not (valid_after_s <= now_epoch_s < valid_before_s)
        or nonce_already_used
    ):
        return GuardDecision(
            allowed=False,
            decision_code="X402_EVM_NORMATIVE_MUST_OR_SUPPORTED_CAPABILITY_MISMATCH_BLOCKED",
            reason="EVM exact scheme facilitator MUST verification checklist failed.",
            metadata={
                "eip712_domain_matched": eip712_domain_matched,
                "nonce_already_used": nonce_already_used,
            },
        )

    if supported_capabilities is not None:
        for key, allowed_values in supported_capabilities.items():
            actual_val = payment_requirements_extra.get(key)
            if actual_val not in set(allowed_values):
                return GuardDecision(
                    allowed=False,
                    decision_code="X402_EVM_NORMATIVE_MUST_OR_SUPPORTED_CAPABILITY_MISMATCH_BLOCKED",
                    reason=(
                        f"PaymentRequirements.extra['{key}']='{actual_val}' is not supported "
                        f"by facilitator SupportedKind.capabilities {list(allowed_values)}."
                    ),
                    metadata={"discriminator": key, "actual": actual_val},
                )

    return GuardDecision(
        allowed=True,
        decision_code="X402_EVM_NORMATIVE_MUST_AND_CAPABILITIES_VERIFIED",
        reason="EVM exact MUST checklist and SupportedKind.capabilities discriminators verified.",
        metadata={"asset_transfer_method": payment_requirements_extra.get("assetTransferMethod")},
    )


# ---------------------------------------------------------------------------
# PR-09: x402-foundation/x402#2802 & #3649
# SVM destination ATA existence/owner check & Python async non-blocking RPC
# ---------------------------------------------------------------------------
def audit_x402_svm_destination_ata_and_async_rpc(
    *,
    destination_ata_exists: bool,
    destination_ata_owner: str,
    expected_token_program: str,
    is_async_client: bool,
    uses_sync_solana_rpc_in_event_loop: bool,
) -> GuardDecision:
    if not destination_ata_exists or destination_ata_owner != expected_token_program:
        return GuardDecision(
            allowed=False,
            decision_code="X402_SVM_ATA_INVALID_OR_SYNC_EVENT_LOOP_BLOCKED",
            reason=(
                "Destination ATA does not exist or its owner does not match the mint's "
                "token program (would fail on-chain with InvalidAccountData)."
            ),
            metadata={
                "destination_ata_exists": destination_ata_exists,
                "destination_ata_owner": destination_ata_owner,
                "expected_token_program": expected_token_program,
            },
        )

    if is_async_client and uses_sync_solana_rpc_in_event_loop:
        return GuardDecision(
            allowed=False,
            decision_code="X402_SVM_ATA_INVALID_OR_SYNC_EVENT_LOOP_BLOCKED",
            reason="Python async SVM client must await async RPC calls instead of blocking the event loop.",
            metadata={"uses_sync_solana_rpc_in_event_loop": True},
        )

    return GuardDecision(
        allowed=True,
        decision_code="X402_SVM_DESTINATION_ATA_AND_ASYNC_RPC_VERIFIED",
        reason="SVM destination ATA ownership and non-blocking async RPC verified.",
        metadata={"token_program": expected_token_program},
    )


# ---------------------------------------------------------------------------
# PR-10: x402-foundation/x402#2975 & #2761
# Stellar Soroban typed simulation error classification
# ---------------------------------------------------------------------------
def audit_x402_stellar_typed_simulation_errors(
    *,
    diagnostic_kind: str,
    diagnostic_account: str | None,
    payer_account: str,
    emitted_error_class: str,
    preserves_raw_cause: bool,
) -> GuardDecision:
    if not preserves_raw_cause:
        return GuardDecision(
            allowed=False,
            decision_code="X402_STELLAR_UNPROVEN_SIMULATION_ERROR_MISCLASSIFIED_BLOCKED",
            reason="Stellar typed simulation errors must preserve the raw RPC error as cause.",
            metadata={},
        )

    if diagnostic_kind == "trustline_missing" and diagnostic_account:
        expected_class = "TrustlineMissingError"
    elif diagnostic_kind == "balance_low" and diagnostic_account == payer_account:
        expected_class = "InsufficientBalanceError"
    else:
        expected_class = "SimulationFailedError"

    if emitted_error_class != expected_class:
        return GuardDecision(
            allowed=False,
            decision_code="X402_STELLAR_UNPROVEN_SIMULATION_ERROR_MISCLASSIFIED_BLOCKED",
            reason=(
                f"Soroban diagnostic '{diagnostic_kind}' (account={diagnostic_account}) "
                f"must map to '{expected_class}', got '{emitted_error_class}'."
            ),
            metadata={"expected_class": expected_class, "emitted_error_class": emitted_error_class},
        )

    return GuardDecision(
        allowed=True,
        decision_code="X402_STELLAR_TYPED_SIMULATION_ERROR_VERIFIED",
        reason="Stellar Soroban diagnostic event mapped to exact typed simulation error.",
        metadata={"emitted_error_class": emitted_error_class},
    )


# ---------------------------------------------------------------------------
# PR-11: x402-foundation/x402#3556 & #3560
# Workers compile-free Bazaar schema check & Go MCP recovery timeout cap
# ---------------------------------------------------------------------------
def audit_x402_workers_bazaar_validator_and_go_mcp_timeout_cap(
    *,
    uses_runtime_ajv_compile_codegen: bool,
    accepted_max_timeout_s: int,
    max_request_timeout_s: int,
    recovery_retry_timeout_s: int,
) -> GuardDecision:
    if uses_runtime_ajv_compile_codegen:
        return GuardDecision(
            allowed=False,
            decision_code="X402_WORKERS_DYNAMIC_CODEGEN_OR_GO_RECOVERY_TIMEOUT_UNBOUNDED_BLOCKED",
            reason="Runtime ajv.compile() new Function() codegen is disallowed on Cloudflare Workers.",
            metadata={"uses_runtime_ajv_compile_codegen": True},
        )

    expected_capped_timeout = min(accepted_max_timeout_s, max_request_timeout_s)
    if recovery_retry_timeout_s <= 0 or recovery_retry_timeout_s > expected_capped_timeout:
        return GuardDecision(
            allowed=False,
            decision_code="X402_WORKERS_DYNAMIC_CODEGEN_OR_GO_RECOVERY_TIMEOUT_UNBOUNDED_BLOCKED",
            reason=(
                f"Go MCP recovery retry timeout ({recovery_retry_timeout_s}s) exceeds "
                f"MaxRequestTimeout cap ({expected_capped_timeout}s)."
            ),
            metadata={
                "recovery_retry_timeout_s": recovery_retry_timeout_s,
                "expected_capped_timeout": expected_capped_timeout,
            },
        )

    return GuardDecision(
        allowed=True,
        decision_code="X402_WORKERS_VALIDATOR_AND_GO_MCP_TIMEOUT_CAP_VERIFIED",
        reason="Compile-free Bazaar validation and Go MCP recovery timeout cap verified.",
        metadata={"recovery_retry_timeout_s": recovery_retry_timeout_s},
    )


# ---------------------------------------------------------------------------
# PR-12: x402-foundation/x402#3586 & #2368
# Python create_headers path-keyed auth dict & onUncertainSettlement hook
# ---------------------------------------------------------------------------
def audit_x402_python_create_headers_and_uncertain_settlement_hook(
    *,
    create_headers_result: Mapping[str, Any],
    settle_threw_error: bool,
    on_settle_failure_recovered: bool,
    on_uncertain_settlement_fired: bool,
    hook_error_isolated: bool,
    original_error_rethrown: bool,
) -> GuardDecision:
    required_endpoint_keys = {"verify", "settle", "supported"}
    if not required_endpoint_keys.issubset(set(create_headers_result.keys())) or not all(
        isinstance(create_headers_result[k], Mapping) and bool(create_headers_result[k])
        for k in required_endpoint_keys
    ):
        return GuardDecision(
            allowed=False,
            decision_code="X402_FLAT_AUTH_HEADERS_DROPPED_OR_UNCERTAIN_HOOK_VIOLATION_BLOCKED",
            reason=(
                "Python create_headers() must return path-keyed dicts "
                "{verify, settle, supported}; flat dicts silently drop facilitator auth."
            ),
            metadata={"keys": list(create_headers_result.keys())},
        )

    if settle_threw_error:
        should_fire_uncertain = not on_settle_failure_recovered
        if (
            on_uncertain_settlement_fired != should_fire_uncertain
            or not hook_error_isolated
            or (not on_settle_failure_recovered and not original_error_rethrown)
        ):
            return GuardDecision(
                allowed=False,
                decision_code="X402_FLAT_AUTH_HEADERS_DROPPED_OR_UNCERTAIN_HOOK_VIOLATION_BLOCKED",
                reason="onUncertainSettlement hook lifecycle or error isolation violated.",
                metadata={
                    "should_fire_uncertain": should_fire_uncertain,
                    "on_uncertain_settlement_fired": on_uncertain_settlement_fired,
                },
            )

    return GuardDecision(
        allowed=True,
        decision_code="X402_CREATE_HEADERS_AND_UNCERTAIN_SETTLEMENT_VERIFIED",
        reason="Path-keyed facilitator auth headers and onUncertainSettlement hook verified.",
        metadata={"on_uncertain_settlement_fired": on_uncertain_settlement_fired},
    )


# ---------------------------------------------------------------------------
# PR-13: modelcontextprotocol/modelcontextprotocol#2920 & #1488
# MRTR url-mode state-only InputRequiredResult & tool securitySchemes
# ---------------------------------------------------------------------------
def audit_mcp_mrtr_still_waiting_and_tool_security_schemes(
    *,
    is_still_waiting_poll: bool,
    prior_request_state: str,
    returned_request_state: str,
    returned_input_requests: Sequence[Any],
    holds_http_connection_open_unbounded: bool,
    retry_after_ms: int,
    supports_cancel_verb: bool,
    tool_security_schemes: Sequence[Mapping[str, Any]],
    caller_authenticated: bool,
    caller_scopes: Sequence[str],
) -> GuardDecision:
    if is_still_waiting_poll:
        if (
            holds_http_connection_open_unbounded
            or returned_request_state != prior_request_state
            or len(returned_input_requests) > 0
            or retry_after_ms < 500
            or not supports_cancel_verb
        ):
            return GuardDecision(
                allowed=False,
                decision_code="MCP_MRTR_BLOCKING_POLL_OR_TOOL_SECURITY_SCHEME_VIOLATION_BLOCKED",
                reason=(
                    "MRTR url-mode 'still waiting' response must return state-only "
                    "InputRequiredResult (empty inputRequests) with bounded backoff and cancel."
                ),
                metadata={
                    "holds_http_connection_open_unbounded": holds_http_connection_open_unbounded,
                    "input_requests_len": len(returned_input_requests),
                },
            )

    if not tool_security_schemes:
        return GuardDecision(
            allowed=False,
            decision_code="MCP_MRTR_BLOCKING_POLL_OR_TOOL_SECURITY_SCHEME_VIOLATION_BLOCKED",
            reason="Mixed-auth MCP tool descriptor must declare securitySchemes.",
            metadata={},
        )

    scheme_satisfied = False
    caller_scope_set = set(caller_scopes)
    for scheme in tool_security_schemes:
        s_type = scheme.get("type")
        if s_type == "noauth":
            scheme_satisfied = True
            break
        if s_type == "oauth2" and caller_authenticated:
            req_scopes = set(scheme.get("scopes", []))
            if req_scopes.issubset(caller_scope_set):
                scheme_satisfied = True
                break

    if not scheme_satisfied:
        return GuardDecision(
            allowed=False,
            decision_code="MCP_MRTR_BLOCKING_POLL_OR_TOOL_SECURITY_SCHEME_VIOLATION_BLOCKED",
            reason="Caller does not satisfy any declared MCP tool securityScheme (SEP-1488).",
            metadata={"caller_authenticated": caller_authenticated, "caller_scopes": list(caller_scopes)},
        )

    return GuardDecision(
        allowed=True,
        decision_code="MCP_MRTR_STILL_WAITING_AND_SECURITY_SCHEMES_VERIFIED",
        reason="MRTR state-only InputRequiredResult and SEP-1488 securitySchemes verified.",
        metadata={"retry_after_ms": retry_after_ms},
    )


# ---------------------------------------------------------------------------
# PR-14: modelcontextprotocol/modelcontextprotocol#1913 & #2127
# SEP-1913 monotonic trust/sensitivity escalation & .well-known/ai-catalog.json
# ---------------------------------------------------------------------------
def audit_mcp_trust_sensitivity_escalation_and_server_card(
    *,
    prior_sensitivity: str,
    input_sensitivity: str,
    resulting_sensitivity: str,
    prior_private_hint: bool,
    input_private_hint: bool,
    resulting_private_hint: bool,
    target_tool_open_world_hint: bool,
    server_card: Mapping[str, Any],
) -> GuardDecision:
    if (
        prior_sensitivity not in SENSITIVITY_ORDER
        or input_sensitivity not in SENSITIVITY_ORDER
        or resulting_sensitivity not in SENSITIVITY_ORDER
    ):
        return GuardDecision(
            allowed=False,
            decision_code="MCP_SENSITIVITY_DOWNGRADE_EXFILTRATION_OR_SERVER_CARD_INVALID_BLOCKED",
            reason="Invalid sensitiveHint level; must be low, medium, or high.",
            metadata={},
        )

    expected_max_sens = max(
        SENSITIVITY_ORDER[prior_sensitivity], SENSITIVITY_ORDER[input_sensitivity]
    )
    expected_private = prior_private_hint or input_private_hint
    if (
        SENSITIVITY_ORDER[resulting_sensitivity] < expected_max_sens
        or resulting_private_hint != expected_private
    ):
        return GuardDecision(
            allowed=False,
            decision_code="MCP_SENSITIVITY_DOWNGRADE_EXFILTRATION_OR_SERVER_CARD_INVALID_BLOCKED",
            reason="SEP-1913 sensitivity and privateHint must escalate monotonically without downgrade.",
            metadata={
                "resulting_sensitivity": resulting_sensitivity,
                "resulting_private_hint": resulting_private_hint,
            },
        )

    if target_tool_open_world_hint and (
        resulting_private_hint or resulting_sensitivity == "high"
    ):
        return GuardDecision(
            allowed=False,
            decision_code="MCP_SENSITIVITY_DOWNGRADE_EXFILTRATION_OR_SERVER_CARD_INVALID_BLOCKED",
            reason="Blocked exfiltration of private/high-sensitivity context to openWorldHint tool.",
            metadata={"target_tool_open_world_hint": True},
        )

    if (
        server_card.get("discovery_path") != "/.well-known/ai-catalog.json"
        or not server_card.get("protocol_versions")
        or not server_card.get("transports")
        or not isinstance(server_card.get("capabilities"), Mapping)
    ):
        return GuardDecision(
            allowed=False,
            decision_code="MCP_SENSITIVITY_DOWNGRADE_EXFILTRATION_OR_SERVER_CARD_INVALID_BLOCKED",
            reason="SEP-2127 MCP Server Card at /.well-known/ai-catalog.json is incomplete.",
            metadata={"discovery_path": server_card.get("discovery_path")},
        )

    return GuardDecision(
        allowed=True,
        decision_code="MCP_TRUST_SENSITIVITY_AND_SERVER_CARD_VERIFIED",
        reason="SEP-1913 monotonic sensitivity propagation and SEP-2127 Server Card verified.",
        metadata={"resulting_sensitivity": resulting_sensitivity},
    )


# ---------------------------------------------------------------------------
# PR-15: sierra-research/tau2-bench#647 & #624
# Airline reproducibility manifest pinning & silent .env absence at import
# ---------------------------------------------------------------------------
def audit_tau2_reproducibility_manifest_and_silent_dotenv(
    *,
    manifest: Mapping[str, Any],
    dotenv_present: bool,
    import_stderr_output: str,
) -> GuardDecision:
    required_fields = (
        "repo_commit_sha",
        "agent_model_snapshot",
        "user_model_snapshot",
        "temperature",
        "seed",
        "num_trials",
    )
    missing = [k for k in required_fields if manifest.get(k) in (None, "")]
    if (
        missing
        or float(manifest.get("temperature", -1.0)) != 0.0
        or int(manifest.get("num_trials", 0)) < 4
    ):
        return GuardDecision(
            allowed=False,
            decision_code="TAU2_UNPINNED_BENCHMARK_MANIFEST_OR_DOTENV_STDENV_POLLUTION_BLOCKED",
            reason="tau2-bench pass^4 reproducibility manifest is missing pinned model/commit/seed fields.",
            metadata={"missing_fields": missing},
        )

    if not dotenv_present and import_stderr_output.strip():
        return GuardDecision(
            allowed=False,
            decision_code="TAU2_UNPINNED_BENCHMARK_MANIFEST_OR_DOTENV_STDENV_POLLUTION_BLOCKED",
            reason="Import-time .env absence must not write warnings to stderr (#624).",
            metadata={"import_stderr_output": import_stderr_output},
        )

    return GuardDecision(
        allowed=True,
        decision_code="TAU2_REPRODUCIBILITY_MANIFEST_AND_CLEAN_STDERR_VERIFIED",
        reason="Pinned tau2-bench reproducibility manifest and clean import-time stderr verified.",
        metadata={"agent_model_snapshot": manifest.get("agent_model_snapshot")},
    )


# ---------------------------------------------------------------------------
# PR-16: sierra-research/tau2-bench#549 & #678
# TerminationReason.OUT_OF_SCOPE enum & unscored runner result reward guard
# ---------------------------------------------------------------------------
def audit_tau2_out_of_scope_termination_and_unscored_reward_guard(
    *,
    supported_termination_reasons: Sequence[str],
    simulation_termination_reason: str,
    simulation_runs: Sequence[Mapping[str, Any]],
    crashes_on_none_reward_info: bool,
) -> GuardDecision:
    if (
        "OUT_OF_SCOPE" not in set(supported_termination_reasons)
        or simulation_termination_reason not in set(supported_termination_reasons)
        or crashes_on_none_reward_info
        or not simulation_runs
    ):
        return GuardDecision(
            allowed=False,
            decision_code="TAU2_UNKNOWN_OUT_OF_SCOPE_TERMINATION_OR_UNSCORED_CRASH_BLOCKED",
            reason=(
                "TerminationReason must include OUT_OF_SCOPE (#549) and reward analysis "
                "must safely handle unscored runs where reward_info is None (#678)."
            ),
            metadata={
                "has_out_of_scope": "OUT_OF_SCOPE" in set(supported_termination_reasons),
                "crashes_on_none_reward_info": crashes_on_none_reward_info,
            },
        )

    scored_rewards = [
        float(r["reward_info"]["reward"])
        for r in simulation_runs
        if isinstance(r.get("reward_info"), Mapping) and "reward" in r["reward_info"]
    ]
    unscored_count = len(simulation_runs) - len(scored_rewards)

    return GuardDecision(
        allowed=True,
        decision_code="TAU2_OUT_OF_SCOPE_AND_UNSCORED_REWARD_GUARD_VERIFIED",
        reason="OUT_OF_SCOPE termination reason and null-safe reward analysis verified.",
        metadata={"scored_count": len(scored_rewards), "unscored_count": unscored_count},
    )
