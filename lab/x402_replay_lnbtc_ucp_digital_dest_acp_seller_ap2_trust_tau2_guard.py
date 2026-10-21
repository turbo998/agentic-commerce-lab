"""Stage 150 deterministic guardrails across x402, UCP, ACP, AP2, MCP, Stripe AI, Visa TAP, and Sierra tau2-bench.

Covers 16 primary-source protocol PR guardrails (RL-01..RL-16):
- RL-01: x402 #3865 & #3796 onAfterVerify concurrent authorization replay-guard & HTTP HEAD payment bypass prevention
- RL-02: x402 #3853 & #3734 SVM server-signed batch-settlement post-channel-commit operation completion & duplicate retry guard
- RL-03: x402 #3688, #3727 & #3544 exact lnbtc BOLT11 http:1/mcp:1 description-hash request binding & atomic network:payment_hash consumption + Bitcoin 2-of-3 PSBT batch guard
- RL-04: x402 #3666, #3794/#3774 & #3686/#3669 ERC-8021 Schema 2 facilitator-authored builder-code metadata (m), CORS Access-Control-Expose-Headers & non-JSON error body preservation
- RL-05: UCP #719 & #871/#763 durable Order com.mercadopago.shopping.digital_delivery (redeemable_artifact vs entitlement) & complete_checkout cart_id omit + create line_item_ids omit
- RL-06: UCP #689, #688 & #671 method-level destination discrimination (shipping default vs response-only pickup) & context.location provisional availability evaluation
- RL-07: UCP #670, #883 & #741 A2A complete_in_progress mutation freeze parity, MCP complete_checkout extension allowlist & common payment namespace migration
- RL-08: UCP #686 & #662 post-strip array elision index alignment ("..." sentinel shift) & loyalty earning_forecast.breakdown minor-unit sum invariant
- RL-09: ACP #262, #249/#219, #214 & #144 MessageInfo/MessageWarning/MessageError schema conformance (intervention_required), integer minor-unit Refund.amount, empty risk_signals & 11-state session machine
- RL-10: ACP #114, #111, #133/#130, #125/#123 & #166/#151/#149 seller-backed credential isolation, crypto x402 SPT handler, display_order/display_name, sale & on-chain discount eligibility + content attribution
- RL-11: Google AP2 #271, #272 & #276 post-settlement SettlementAttestation (SETTLED/PENDING_FINALITY/REVERSED), multi-issuer TrustQuery verdict envelope & ZKP receipt binding
- RL-12: Google AP2 #257, #144 & #110 DID-based (did:tenzro:) mandate chain + STARK commitment, 4-role A2A VerifiableIntent SD-JWT delegation & Section 7.1 PaymentReceipt schema
- RL-13: MCP #3289, #3154, #3148 & #3125 IEEE-754 safe-integer bound, non-empty programmatic schema symbol generation & snake_case resultType="input_required"
- RL-14: Stripe AI #500, #504/#486, #426 & #343 provider empty-choices NoContentGeneratedError guard, stripe-directory vs stripe-projects routing, invoice /purchase wiring & MCP User-Agent version sync
- RL-15: Visa TAP #21, #18 & #11 hybrid post-quantum ed25519-ml-dsa-65 (64B || 3309B) dual-leg verification, explicit DIDResolverRegistry & x402 Solana/Base USDC mandate binding
- RL-16: Sierra tau2-bench 2.0 #667, #666, #665, #650, #602 & #600 one-to-one gold action bipartite matching, retail same-item exchange rejection, telecom empty-MMSC guard, lowercase airline user_id & check_status_bar grounding
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


def canonical_jcs_bytes(value: Any) -> bytes:
    """Deterministic RFC 8785 JCS-compatible UTF-8 bytes for JSON values."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def jcs_sha256_hex(value: Any) -> str:
    """Return hex SHA-256 of canonical JCS representation."""
    return hashlib.sha256(canonical_jcs_bytes(value)).hexdigest()


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    code: str
    detail: str
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# RL-01: x402 #3865 & #3796 onAfterVerify Replay-Guard & HTTP HEAD Bypass Guard
# ---------------------------------------------------------------------------

def evaluate_x402_on_after_verify_replay_and_head_guard(
    *,
    http_method: str,
    route_requires_payment: bool,
    has_payment_signature: bool,
    verify_is_valid: bool,
    scheme_type: str,
    network: str,
    asset: str,
    payer_from: str,
    nonce: str,
    claimed_authorizations: set[str],
) -> GuardDecision:
    """RL-01: Enforce payment on HEAD requests to paid GET routes (#3796) and atomically claim authorizations in onAfterVerify (#3865)."""
    method_upper = (http_method or "").upper().strip()
    if route_requires_payment and method_upper in {"GET", "HEAD"} and not has_payment_signature:
        return GuardDecision(
            allowed=False,
            code="X402_HEAD_OR_GET_PAYMENT_REQUIRED_402",
            detail=f"HTTP {method_upper} request to paid route rejected without payment signature (#3796).",
            metadata={"http_method": method_upper},
        )
    if not verify_is_valid:
        return GuardDecision(
            allowed=False,
            code="X402_VERIFY_INVALID_NOT_CLAIMED",
            detail="Authorization failed verify; onAfterVerify does not claim invalid authorizations (#3865).",
        )
    if not network or not payer_from or not nonce:
        return GuardDecision(
            allowed=False,
            code="X402_REPLAY_KEY_INCOMPLETE",
            detail="Authorization replay key requires non-empty network, from, and nonce (#3865).",
        )
    if scheme_type == "eip3009":
        if not asset:
            return GuardDecision(
                allowed=False,
                code="X402_EIP3009_ASSET_REQUIRED",
                detail="EIP-3009 replay key requires network:asset:from:nonce (#3865).",
            )
        replay_key = f"{network}:{asset.lower()}:{payer_from.lower()}:{nonce.lower()}"
    elif scheme_type == "permit2":
        replay_key = f"{network}:{payer_from.lower()}:{nonce.lower()}"
    else:
        return GuardDecision(
            allowed=False,
            code="X402_UNSUPPORTED_REPLAY_SCHEME",
            detail=f"Unsupported scheme_type={scheme_type!r} for onAfterVerify replay guard.",
        )

    if replay_key in claimed_authorizations:
        return GuardDecision(
            allowed=False,
            code="payment_replayed",
            detail="Concurrent or duplicate authorization blocked in onAfterVerify before handler execution (#3865).",
            metadata={"replay_key": replay_key},
        )
    claimed_authorizations.add(replay_key)
    return GuardDecision(
        allowed=True,
        code="X402_ON_AFTER_VERIFY_CLAIMED_OK",
        detail="Authorization claimed atomically in onAfterVerify and paid handler admitted.",
        metadata={"replay_key": replay_key, "http_method": method_upper},
    )


# ---------------------------------------------------------------------------
# RL-02: x402 #3853 & #3734 SVM Batch-Settlement Post-Channel-Commit Ordering
# ---------------------------------------------------------------------------

def evaluate_x402_svm_batch_commit_order_guard(
    *,
    operation_id: str,
    channel_id: str,
    charge_amount_atomic: int,
    available_channel_balance_atomic: int,
    complete_called_inside_channel_update_callback: bool,
    channel_write_succeeded: bool,
    completed_operation_ids: set[str],
) -> GuardDecision:
    """RL-02: Require operationStore.complete to run strictly AFTER ChannelStore.update commits (#3853, #3734)."""
    if not operation_id or not channel_id or charge_amount_atomic <= 0:
        return GuardDecision(
            allowed=False,
            code="X402_SVM_BATCH_INVALID_CHARGE_INPUT",
            detail="Batch charge requires valid operation_id, channel_id, and positive charge_amount_atomic (#3734).",
        )
    if operation_id in completed_operation_ids:
        return GuardDecision(
            allowed=False,
            code="X402_SVM_BATCH_DUPLICATE_OPERATION_RETRY_BLOCKED",
            detail="Duplicate batch operation retry blocked; charge already committed (#3734).",
            metadata={"operation_id": operation_id},
        )
    if complete_called_inside_channel_update_callback:
        return GuardDecision(
            allowed=False,
            code="X402_SVM_BATCH_PREMATURE_OPERATION_COMPLETE_IN_CALLBACK_BLOCKED",
            detail="operationStore.complete must not run inside ChannelStore.update callback before durable channel write commits (#3853).",
        )
    if charge_amount_atomic > available_channel_balance_atomic:
        return GuardDecision(
            allowed=False,
            code="X402_SVM_BATCH_INSUFFICIENT_CHANNEL_DEPOSIT",
            detail="Accumulated batch charge exceeds available channel deposit (#3734).",
        )
    if not channel_write_succeeded:
        return GuardDecision(
            allowed=False,
            code="X402_SVM_BATCH_CHANNEL_COMMIT_FAILED_OPERATION_UNCOMMITTED",
            detail="Durable ChannelStore.update failed; operationStore.complete skipped to preserve retry safety (#3853).",
        )
    completed_operation_ids.add(operation_id)
    return GuardDecision(
        allowed=True,
        code="X402_SVM_BATCH_POST_COMMIT_COMPLETED_OK",
        detail="Channel charge committed durably first, then operationStore.complete recorded (#3853, #3734).",
        metadata={
            "operation_id": operation_id,
            "remaining_balance_atomic": available_channel_balance_atomic - charge_amount_atomic,
        },
    )


# ---------------------------------------------------------------------------
# RL-03: x402 #3688, #3727 & #3544 exact lnbtc BOLT11 Binding & BTC PSBT Batch
# ---------------------------------------------------------------------------

def evaluate_x402_lnbtc_exact_and_btc_psbt_guard(
    *,
    network: str,
    preimage_hex: str,
    invoice_payment_hash_hex: str,
    binding_profile: str,
    canonical_request_descriptor: dict[str, Any],
    invoice_description_hash_hex: str,
    header_lines: list[str],
    consumed_payment_hashes: set[str],
    btc_batch_psbt_signers: list[str] | None = None,
    btc_batch_required_quorum: int = 2,
) -> GuardDecision:
    """RL-03: Verify exact lnbtc preimage, http:1/mcp:1 description_hash request binding, header byte hygiene (#3688, #3727), and BTC 2-of-3 PSBT batch quorum (#3544)."""
    if binding_profile not in {"http:1", "mcp:1"}:
        return GuardDecision(
            allowed=False,
            code="X402_LNBTC_INVALID_BINDING_PROFILE",
            detail="lnbtc request binding profile must be 'http:1' or 'mcp:1' (#3688, #3727).",
        )
    for line in header_lines:
        if "\r" in line or "\n" in line or any(ord(ch) > 127 for ch in line):
            return GuardDecision(
                allowed=False,
                code="X402_LNBTC_HEADER_CRLF_OR_NON_ASCII_BLOCKED",
                detail="lnbtc http_binding rejects CR/LF or non-ASCII bytes in bound header lines (#3727).",
            )
    try:
        preimage_bytes = bytes.fromhex(preimage_hex)
    except ValueError:
        return GuardDecision(
            allowed=False,
            code="X402_LNBTC_PREIMAGE_HEX_INVALID",
            detail="Invalid hex encoding for Lightning payment preimage (#3688).",
        )
    derived_payment_hash = hashlib.sha256(preimage_bytes).hexdigest()
    if derived_payment_hash != invoice_payment_hash_hex.lower():
        return GuardDecision(
            allowed=False,
            code="X402_LNBTC_PREIMAGE_HASH_MISMATCH",
            detail="SHA-256(preimage) does not match BOLT11 invoice payment_hash (#3688).",
        )
    expected_desc_hash = jcs_sha256_hex({"profile": binding_profile, "request": canonical_request_descriptor})
    if expected_desc_hash != invoice_description_hash_hex.lower():
        return GuardDecision(
            allowed=False,
            code="X402_LNBTC_DESCRIPTION_HASH_REQUEST_MISMATCH",
            detail="BOLT11 signed description_hash does not match canonical request binding (#3688, #3727).",
        )
    replay_token = f"{network}:{derived_payment_hash}"
    if replay_token in consumed_payment_hashes:
        return GuardDecision(
            allowed=False,
            code="X402_LNBTC_PAYMENT_HASH_ALREADY_CONSUMED",
            detail="Atomic replay store rejected already-consumed network:payment_hash (#3688).",
        )
    if btc_batch_psbt_signers is not None:
        unique_signers = set(btc_batch_psbt_signers)
        if len(unique_signers) < btc_batch_required_quorum:
            return GuardDecision(
                allowed=False,
                code="X402_BTC_BATCH_PSBT_QUORUM_INSUFFICIENT",
                detail="Bitcoin batch settlement requires at least 2-of-3 pre-authorized PSBT cosigners (#3544).",
            )
    consumed_payment_hashes.add(replay_token)
    return GuardDecision(
        allowed=True,
        code="X402_LNBTC_AND_BTC_PSBT_VERIFIED_OK",
        detail="lnbtc preimage, description_hash request binding, and BTC PSBT quorum verified.",
        metadata={"replay_token": replay_token, "description_hash": expected_desc_hash},
    )


# ---------------------------------------------------------------------------
# RL-04: x402 #3666, #3794/#3774 & #3686/#3669 Builder-Code (m), CORS & Body
# ---------------------------------------------------------------------------

def evaluate_x402_builder_metadata_cors_and_error_body_guard(
    *,
    client_payload_builder_code: dict[str, Any],
    facilitator_settlement_metadata: dict[str, Any],
    response_payment_headers: list[str],
    access_control_expose_headers: list[str],
    custom_unpaid_body: str,
    declared_content_type: str,
    serialized_response_body: str,
) -> GuardDecision:
    """RL-04: Strip client-supplied builder-code 'm', validate facilitator 'x402*' keys (#3666), require CORS expose headers (#3794/#3774), and preserve non-JSON unpaid bodies (#3686/#3669)."""
    if "m" in client_payload_builder_code:
        return GuardDecision(
            allowed=False,
            code="X402_CLIENT_AUTHORED_BUILDER_METADATA_M_REJECTED",
            detail="ERC-8021 Schema 2 settlement metadata 'm' is facilitator-authored only; client-supplied 'm' rejected (#3666).",
        )
    for k in facilitator_settlement_metadata:
        if not k.startswith("x402"):
            return GuardDecision(
                allowed=False,
                code="X402_BUILDER_METADATA_KEY_PREFIX_INVALID",
                detail=f"Facilitator settlement metadata key {k!r} must start with 'x402' (#3666).",
            )
    exposed_upper = {h.upper().strip() for h in access_control_expose_headers}
    for hdr in response_payment_headers:
        if hdr.upper() in {"PAYMENT-REQUIRED", "PAYMENT-RESPONSE"} and hdr.upper() not in exposed_upper:
            return GuardDecision(
                allowed=False,
                code="X402_CORS_EXPOSE_PAYMENT_HEADER_MISSING",
                detail=f"Response header {hdr} must be listed in Access-Control-Expose-Headers for cross-origin browsers (#3794, #3774).",
            )
    ct_lower = (declared_content_type or "").lower()
    is_json_media = "application/json" in ct_lower or "+json" in ct_lower
    if not is_json_media and serialized_response_body != custom_unpaid_body:
        return GuardDecision(
            allowed=False,
            code="X402_NON_JSON_UNPAID_BODY_QUOTED_OR_CORRUPTED",
            detail="Non-JSON custom unpaid/error body must not be JSON-quoted or altered by Hono/Next middleware (#3686, #3669).",
        )
    return GuardDecision(
        allowed=True,
        code="X402_BUILDER_METADATA_CORS_AND_BODY_OK",
        detail="Facilitator builder-code 'm', CORS expose headers, and non-JSON error body preserved.",
    )


# ---------------------------------------------------------------------------
# RL-05: UCP #719 & #871/#763 Digital Delivery on Order & cart_id/line_item_ids Omit
# ---------------------------------------------------------------------------

def evaluate_ucp_digital_delivery_and_omit_annotations_guard(
    *,
    attachment_target: str,
    digital_delivery_payload: dict[str, Any],
    operation: str,
    request_payload: dict[str, Any],
) -> GuardDecision:
    """RL-05: Enforce com.mercadopago.shopping.digital_delivery on durable Order with kind discriminator (#719) and omit cart_id on complete / line_item_ids on create (#871, #763)."""
    if attachment_target != "order":
        return GuardDecision(
            allowed=False,
            code="UCP_DIGITAL_DELIVERY_MUST_ATTACH_TO_ORDER",
            detail="com.mercadopago.shopping.digital_delivery must attach to the durable Order, not ephemeral Checkout (#719).",
        )
    kind = digital_delivery_payload.get("kind")
    if kind not in {"redeemable_artifact", "entitlement"}:
        return GuardDecision(
            allowed=False,
            code="UCP_DIGITAL_DELIVERY_KIND_INVALID",
            detail="digital_delivery item requires kind in {'redeemable_artifact', 'entitlement'} (#719).",
        )
    if kind == "redeemable_artifact" and "code" not in digital_delivery_payload and "pin" not in digital_delivery_payload:
        return GuardDecision(
            allowed=False,
            code="UCP_REDEEMABLE_ARTIFACT_MISSING_BEARER_CODE",
            detail="redeemable_artifact requires bearer code or pin (#719).",
        )
    if operation == "complete_checkout" and "cart_id" in request_payload:
        return GuardDecision(
            allowed=False,
            code="UCP_COMPLETE_CHECKOUT_CART_ID_MUST_BE_OMITTED",
            detail="cart_id must be omitted on complete_checkout requests (#871, #911).",
        )
    if operation == "create_checkout":
        for method in request_payload.get("fulfillment_methods", []):
            if "line_item_ids" in method:
                return GuardDecision(
                    allowed=False,
                    code="UCP_CREATE_FULFILLMENT_METHOD_LINE_ITEM_IDS_OMIT",
                    detail="fulfillment_method.line_item_ids must be omitted on create requests because line_item.id is omitted on create (#763).",
                )
    return GuardDecision(
        allowed=True,
        code="UCP_DIGITAL_DELIVERY_AND_OMIT_ANNOTATIONS_OK",
        detail="Durable Order digital_delivery and request omit annotations verified.",
    )


# ---------------------------------------------------------------------------
# RL-06: UCP #689, #688 & #671 Method-Level Destination & Location Context
# ---------------------------------------------------------------------------

def evaluate_ucp_method_destination_and_location_context_guard(
    *,
    direction: str,
    method_type: str,
    destination: dict[str, Any] | None,
    selected_destination_id: str | None,
    context_location: dict[str, Any] | None,
    auto_selected_from_context_location: bool,
) -> GuardDecision:
    """RL-06: Discriminate destinations at the method level on requests, require explicit type on responses (#689, #688), and keep context.location provisional (#671)."""
    if context_location is not None and auto_selected_from_context_location:
        return GuardDecision(
            allowed=False,
            code="UCP_CONTEXT_LOCATION_MUST_NOT_SELECT_DESTINATION",
            detail="context.location only evaluates provisional fulfillment availability and must never select a destination (#671).",
        )
    if direction == "response":
        if not destination or not destination.get("type"):
            return GuardDecision(
                allowed=False,
                code="UCP_RESPONSE_DESTINATION_TYPE_REQUIRED",
                detail="Business responses must include explicit destination.type (#688, #689).",
            )
        return GuardDecision(
            allowed=True,
            code="UCP_RESPONSE_DESTINATION_TYPED_OK",
            detail="Business response destination carries explicit type.",
        )

    if method_type == "pickup":
        if destination is not None:
            return GuardDecision(
                allowed=False,
                code="UCP_PICKUP_DESTINATION_RESPONSE_ONLY_BLOCKED",
                detail="Pickup destinations are Business-authored and response-only; Platform must select via selected_destination_id (#688, #689).",
            )
        if not selected_destination_id:
            return GuardDecision(
                allowed=False,
                code="UCP_PICKUP_SELECTED_DESTINATION_ID_REQUIRED",
                detail="Platform pickup selection requires selected_destination_id (#688).",
            )
        return GuardDecision(
            allowed=True,
            code="UCP_PICKUP_SELECTION_VALID_OK",
            detail="Platform selected Business-authored pickup location by ID.",
        )

    if method_type == "shipping":
        if not destination:
            return GuardDecision(
                allowed=False,
                code="UCP_SHIPPING_DESTINATION_REQUIRED",
                detail="Shipping method requires Platform-written shipping destination (#689).",
            )
        resolved_type = destination.get("type", "shipping_address")
        if resolved_type != "shipping_address":
            return GuardDecision(
                allowed=False,
                code="UCP_SHIPPING_METHOD_DESTINATION_TYPE_MISMATCH",
                detail=f"Shipping method destination resolved to invalid type={resolved_type!r} (#689).",
            )
        return GuardDecision(
            allowed=True,
            code="UCP_SHIPPING_METHOD_DEFAULT_DESTINATION_OK",
            detail="Shipping destination accepted with method-level default type='shipping_address' (#689).",
            metadata={"resolved_type": resolved_type},
        )

    return GuardDecision(
        allowed=False,
        code="UCP_UNKNOWN_FULFILLMENT_METHOD_TYPE",
        detail=f"Unsupported fulfillment method_type={method_type!r}.",
    )


# ---------------------------------------------------------------------------
# RL-07: UCP #670, #883 & #741 A2A Freeze Parity, MCP Complete Extensions & Common Payment
# ---------------------------------------------------------------------------

ALLOWED_MCP_COMPLETE_EXTENSIONS = frozenset({
    "dev.ucp.shopping.buyer_consent",
    "dev.ucp.common.payment.ap2_mandate",
    "dev.ucp.common.payment.split_payments",
    "dev.ucp.common.payment.payment_terms",
    "dev.ucp.common.payment.payment_authentication",
})


def evaluate_ucp_a2a_freeze_mcp_complete_and_common_payment_guard(
    *,
    transport: str,
    checkout_status: str,
    action_verb: str,
    mcp_complete_extensions: list[str],
    schema_refs: list[str],
) -> GuardDecision:
    """RL-07: Enforce complete_in_progress mutation freeze across A2A/REST/MCP (#670), validate MCP complete_checkout extensions (#883), and reject legacy shopping/ payment refs (#741)."""
    if checkout_status == "complete_in_progress" and action_verb in {
        "add_to_checkout",
        "update_checkout",
        "patch_checkout",
        "remove_from_checkout",
    }:
        return GuardDecision(
            allowed=False,
            code="UCP_CHECKOUT_COMPLETE_IN_PROGRESS_MUTATION_FROZEN",
            detail=f"Transport {transport} action {action_verb!r} rejected while checkout is complete_in_progress (#670).",
        )
    for ext in mcp_complete_extensions:
        if ext not in ALLOWED_MCP_COMPLETE_EXTENSIONS:
            return GuardDecision(
                allowed=False,
                code="UCP_MCP_COMPLETE_EXTENSION_NOT_SUPPORTED",
                detail=f"Extension {ext!r} is not supported on complete_checkout (#883).",
            )
    legacy_shopping_payment_fragments = (
        "shopping/split_payments.json",
        "shopping/payment_terms.json",
        "shopping/payment_authentication.json",
        "shopping/ap2_mandate.json",
    )
    for ref in schema_refs:
        if any(frag in ref for frag in legacy_shopping_payment_fragments):
            return GuardDecision(
                allowed=False,
                code="UCP_LEGACY_SHOPPING_PAYMENT_SCHEMA_REF_BLOCKED",
                detail=f"Payment construct {ref!r} moved from shopping/ to common/ (#741).",
            )
    return GuardDecision(
        allowed=True,
        code="UCP_A2A_FREEZE_MCP_COMPLETE_COMMON_PAYMENT_OK",
        detail="A2A complete_in_progress freeze, MCP complete_checkout extensions, and common/ payment refs verified.",
    )


# ---------------------------------------------------------------------------
# RL-08: UCP #686 & #662 Post-Strip Array Elision & Loyalty Breakdown Invariant
# ---------------------------------------------------------------------------

def evaluate_ucp_array_elision_and_loyalty_invariant_guard(
    *,
    raw_items_array: list[Any],
    validation_error_post_strip_indices: list[int],
    loyalty_discount_amount_minor: int,
    stated_dollar_benefit: float,
    earning_forecast_total_minor: int,
    earning_forecast_breakdown_minor: list[int],
) -> GuardDecision:
    """RL-08: Record post-strip indices after removing '...' sentinels (#686) and enforce loyalty minor units + breakdown sum invariant (#662)."""
    post_strip_elided_indices: set[int] = set()
    post_idx = 0
    for item in raw_items_array:
        if item == "...":
            continue
        if isinstance(item, dict) and item.get("__elided__") is True:
            post_strip_elided_indices.add(post_idx)
        post_idx += 1

    unsuppressed_errors = [idx for idx in validation_error_post_strip_indices if idx not in post_strip_elided_indices]
    if unsuppressed_errors:
        return GuardDecision(
            allowed=False,
            code="UCP_POST_STRIP_ARRAY_ELISION_UNACKNOWLEDGED_ERROR",
            detail=f"Post-strip array validation failed at non-elided indices {unsuppressed_errors} (#686).",
        )
    expected_minor = round(stated_dollar_benefit * 100)
    if loyalty_discount_amount_minor != expected_minor:
        return GuardDecision(
            allowed=False,
            code="UCP_LOYALTY_MAJOR_MINOR_UNIT_MISMATCH",
            detail=f"Loyalty discount {loyalty_discount_amount_minor} minor units does not match stated ${stated_dollar_benefit:.2f} ({expected_minor} minor units) (#662).",
        )
    if sum(earning_forecast_breakdown_minor) != earning_forecast_total_minor:
        return GuardDecision(
            allowed=False,
            code="UCP_LOYALTY_EARNING_FORECAST_BREAKDOWN_SUM_MISMATCH",
            detail="Sum of earning_forecast.breakdown amounts must equal earning_forecast.total (#662).",
        )
    return GuardDecision(
        allowed=True,
        code="UCP_ARRAY_ELISION_AND_LOYALTY_INVARIANT_OK",
        detail="Post-strip array elision indices and loyalty minor-unit breakdown sum verified.",
        metadata={"post_strip_elided_indices": sorted(post_strip_elided_indices)},
    )


# ---------------------------------------------------------------------------
# RL-09: ACP #262, #249/#219, #214 & #144 Message Schema, Refund Minor Units & 11 States
# ---------------------------------------------------------------------------

ACP_VALID_SESSION_STATES = frozenset({
    "created",
    "incomplete",
    "ready_for_complete",
    "requires_escalation",
    "pending_approval",
    "complete_in_progress",
    "completed",
    "canceled",
    "expired",
    "failed",
    "disputed",
})


def evaluate_acp_message_refund_risk_and_session_state_guard(
    *,
    message_obj: dict[str, Any],
    refund_amount: Any,
    risk_signals: list[Any] | None,
    session_status: str,
) -> GuardDecision:
    """RL-09: Validate ACP MessageInfo/Warning/Error fields (#262, #118), integer Refund.amount (#249), empty risk_signals (#214), and 11 session states (#144)."""
    forbidden_message_fields = {"id", "message", "display_context"}
    present_forbidden = forbidden_message_fields.intersection(message_obj.keys())
    if present_forbidden:
        return GuardDecision(
            allowed=False,
            code="ACP_MESSAGE_HALLUCINATED_FIELDS_BLOCKED",
            detail=f"ACP Message object contains non-schema fields {sorted(present_forbidden)} (#262).",
        )
    msg_type = message_obj.get("type")
    if msg_type not in {"info", "warning", "error", "intervention_required"}:
        return GuardDecision(
            allowed=False,
            code="ACP_MESSAGE_TYPE_INVALID",
            detail=f"Invalid ACP Message type={msg_type!r} (#262, #118).",
        )
    if not message_obj.get("content"):
        return GuardDecision(
            allowed=False,
            code="ACP_MESSAGE_CONTENT_REQUIRED",
            detail="ACP Message requires non-empty 'content' field (#262).",
        )
    if not isinstance(refund_amount, int) or isinstance(refund_amount, bool) or refund_amount < 0:
        return GuardDecision(
            allowed=False,
            code="ACP_REFUND_AMOUNT_MUST_BE_INTEGER_MINOR_UNITS",
            detail=f"Refund.amount must be a non-negative integer in minor units, got {refund_amount!r} (#249, #219).",
        )
    if risk_signals is None or not isinstance(risk_signals, list):
        return GuardDecision(
            allowed=False,
            code="ACP_RISK_SIGNALS_MUST_BE_ARRAY",
            detail="delegate_payment risk_signals must be a list (empty list [] is allowed per #214).",
        )
    if session_status not in ACP_VALID_SESSION_STATES:
        return GuardDecision(
            allowed=False,
            code="ACP_SESSION_STATUS_NOT_IN_11_STATE_SPEC",
            detail=f"CheckoutSessionBase.status={session_status!r} is not in the 11 documented ACP states (#144).",
        )
    return GuardDecision(
        allowed=True,
        code="ACP_MESSAGE_REFUND_RISK_SESSION_STATE_OK",
        detail="ACP Message schema, integer minor-unit Refund.amount, empty risk_signals support, and 11-state status verified.",
    )


# ---------------------------------------------------------------------------
# RL-10: ACP #114, #111, #133/#130, #125/#123 & #166/#151/#149 Seller-Backed & Sale
# ---------------------------------------------------------------------------

ACP_INTENT_TRACE_REASONS = frozenset({
    "price_too_high",
    "shipping_too_slow",
    "shipping_cost_too_high",
    "out_of_stock",
    "payment_declined",
    "user_cancelled",
    "better_offer_found",
    "trust_or_policy_concern",
    "timeout",
    "other",
})


def evaluate_acp_seller_backed_crypto_sale_and_trace_guard(
    *,
    handler_id: str,
    agent_received_raw_credential: bool,
    display_order: Any,
    display_name: str,
    onchain_discount_wallet_verified: bool,
    discount_expires_at_epoch: int,
    now_epoch: int,
    intent_trace_reason_code: str,
    content_citations: list[dict[str, Any]],
) -> GuardDecision:
    """RL-10: Enforce seller-backed credential isolation (#114), crypto x402 SPT handler (#111), display_order/display_name (#133/#130), on-chain sale discount (#166/#123), and intent traces/citations (#151/#149)."""
    if handler_id.startswith("dev.acp.seller_backed.") and agent_received_raw_credential:
        return GuardDecision(
            allowed=False,
            code="ACP_SELLER_BACKED_CREDENTIAL_LEAK_TO_AGENT_BLOCKED",
            detail="dev.acp.seller_backed.* handlers must resolve on seller backend without transferring credentials to the agent (#114).",
        )
    if not isinstance(display_order, int) or isinstance(display_order, bool) or display_order < 0 or not display_name.strip():
        return GuardDecision(
            allowed=False,
            code="ACP_HANDLER_DISPLAY_ORDER_OR_NAME_INVALID",
            detail="PaymentHandler requires non-negative integer display_order and non-empty display_name (#133, #130).",
        )
    if not onchain_discount_wallet_verified or now_epoch > discount_expires_at_epoch:
        return GuardDecision(
            allowed=False,
            code="ACP_ONCHAIN_SALE_DISCOUNT_INELIGIBLE_OR_EXPIRED",
            detail="On-chain token-holding discount requires verified wallet eligibility and unexpired window (#166, #123, #125).",
        )
    if intent_trace_reason_code not in ACP_INTENT_TRACE_REASONS:
        return GuardDecision(
            allowed=False,
            code="ACP_INTENT_TRACE_REASON_CODE_INVALID",
            detail=f"IntentTrace reason_code={intent_trace_reason_code!r} is not in the 10-code RFC enum (#151).",
        )
    for cit in content_citations:
        if not cit.get("source_url") or not cit.get("publisher_id"):
            return GuardDecision(
                allowed=False,
                code="ACP_CONTENT_CITATION_ATTRIBUTION_INCOMPLETE",
                detail="content_attribution citation requires source_url and publisher_id (#149).",
            )
    return GuardDecision(
        allowed=True,
        code="ACP_SELLER_BACKED_CRYPTO_SALE_AND_TRACE_OK",
        detail="Seller-backed credential isolation, handler display metadata, on-chain discount, and intent trace verified.",
    )


# ---------------------------------------------------------------------------
# RL-11: Google AP2 #271, #272 & #276 SettlementAttestation, TrustQuery & ZKP Receipt
# ---------------------------------------------------------------------------

def evaluate_ap2_settlement_attestation_trust_query_and_zkp_guard(
    *,
    settlement_state: str,
    payment_mandate_payload: dict[str, Any],
    settled_payment_ref: str,
    trust_verdict: str,
    issuer_references: list[str],
    zkp_receipt_payload_hash: str,
    expected_session_spend_hash: str,
) -> GuardDecision:
    """RL-11: Enforce closed 3-state SettlementAttestation with JCS sha256: payment ref (#271), 4-state TrustQuery (#272), and Phase 2 ATB ZKP receipt binding (#276)."""
    if settlement_state not in {"SETTLED", "PENDING_FINALITY", "REVERSED"}:
        return GuardDecision(
            allowed=False,
            code="AP2_SETTLEMENT_ATTESTATION_STATE_INVALID",
            detail=f"SettlementAttestation state={settlement_state!r} must be in {{'SETTLED', 'PENDING_FINALITY', 'REVERSED'}} (#271).",
        )
    expected_ref = f"sha256:{jcs_sha256_hex(payment_mandate_payload)}"
    if settled_payment_ref != expected_ref:
        return GuardDecision(
            allowed=False,
            code="AP2_SETTLED_PAYMENT_REF_JCS_MISMATCH",
            detail="SettlementAttestation settled_payment_ref does not match RFC 8785 JCS sha256 of PaymentMandate (#271).",
        )
    if trust_verdict not in {"TRUSTED", "PROVISIONAL", "INSUFFICIENT_EVIDENCE", "UNTRUSTED"}:
        return GuardDecision(
            allowed=False,
            code="AP2_TRUST_QUERY_VERDICT_INVALID",
            detail=f"TrustQuery verdict={trust_verdict!r} is not in closed 4-state enum (#272).",
        )
    if not issuer_references or any(not ref.startswith("sha256:") for ref in issuer_references):
        return GuardDecision(
            allowed=False,
            code="AP2_TRUST_QUERY_ISSUER_REFERENCES_INVALID",
            detail="TrustQuery requires non-empty content-addressed sha256: issuer_references (#272).",
        )
    if trust_verdict in {"INSUFFICIENT_EVIDENCE", "UNTRUSTED"}:
        return GuardDecision(
            allowed=False,
            code="AP2_TRUST_QUERY_VERDICT_REJECTED",
            detail=f"Composite TrustQuery verdict={trust_verdict} denied settlement execution (#272).",
        )
    if not zkp_receipt_payload_hash or zkp_receipt_payload_hash != expected_session_spend_hash:
        return GuardDecision(
            allowed=False,
            code="AP2_ZKP_RECEIPT_SPEND_TRACKER_MISMATCH",
            detail="X-ZKP-Receipt-Payload does not match session spend tracker commitment (#276).",
        )
    return GuardDecision(
        allowed=True,
        code="AP2_SETTLEMENT_ATTESTATION_TRUST_QUERY_ZKP_OK",
        detail="AP2 SettlementAttestation, multi-issuer TrustQuery, and ZKP receipt verified.",
        metadata={"settled_payment_ref": expected_ref},
    )


# ---------------------------------------------------------------------------
# RL-12: Google AP2 #257, #144 & #110 DID Mandate Chain, 4-Role A2A & PaymentReceipt
# ---------------------------------------------------------------------------

REQUIRED_AP2_A2A_ROLES = frozenset({
    "ShoppingAgent",
    "CredentialsProviderAgent",
    "MerchantAgent",
    "MerchantPaymentProcessorAgent",
})


def evaluate_ap2_did_stark_a2a_roles_and_receipt_guard(
    *,
    subject_did: str,
    stark_commitment_verified: bool,
    attested_a2a_roles: set[str],
    sd_jwt_delegation_chain_valid: bool,
    payment_receipt: dict[str, Any],
    expected_mandate_hash: str,
) -> GuardDecision:
    """RL-12: Verify DID mandate chain + STARK commitment (#257), 4-role A2A VerifiableIntent SD-JWT delegation (#144), and Section 7.1 PaymentReceipt (#110)."""
    if not subject_did.startswith("did:") or len(subject_did.split(":")) < 3:
        return GuardDecision(
            allowed=False,
            code="AP2_DID_IDENTITY_INVALID",
            detail=f"Mandate chain subject_did={subject_did!r} must be a valid DID (e.g. did:tenzro:...) (#257).",
        )
    if not stark_commitment_verified:
        return GuardDecision(
            allowed=False,
            code="AP2_STARK_SETTLEMENT_COMMITMENT_INVALID",
            detail="DID settlement STARK commitment failed verification (#257).",
        )
    if not REQUIRED_AP2_A2A_ROLES.issubset(attested_a2a_roles) or not sd_jwt_delegation_chain_valid:
        return GuardDecision(
            allowed=False,
            code="AP2_A2A_VERIFIABLE_INTENT_DELEGATION_FAILED",
            detail="4-role A2A VerifiableIntent SD-JWT delegation chain failed fail-closed verification (#144).",
        )
    required_receipt_fields = {"receipt_id", "payment_mandate_hash", "amount_minor", "currency", "processor_timestamp"}
    if not required_receipt_fields.issubset(payment_receipt.keys()):
        return GuardDecision(
            allowed=False,
            code="AP2_PAYMENT_RECEIPT_SCHEMA_INCOMPLETE",
            detail="Section 7.1 PaymentReceipt is missing required schema fields (#110).",
        )
    if payment_receipt.get("payment_mandate_hash") != expected_mandate_hash:
        return GuardDecision(
            allowed=False,
            code="AP2_PAYMENT_RECEIPT_MANDATE_HASH_MISMATCH",
            detail="PaymentReceipt.payment_mandate_hash does not match authorized PaymentMandate (#110).",
        )
    return GuardDecision(
        allowed=True,
        code="AP2_DID_STARK_A2A_PAYMENT_RECEIPT_OK",
        detail="DID STARK commitment, 4-role A2A VerifiableIntent delegation, and PaymentReceipt verified.",
    )


# ---------------------------------------------------------------------------
# RL-13: MCP #3289, #3154, #3148 & #3125 Safe-Integer, Schema Gen & resultType
# ---------------------------------------------------------------------------

IEEE754_MAX_SAFE_INT = (1 << 53) - 1
IEEE754_MIN_SAFE_INT = -((1 << 53) - 1)


def evaluate_mcp_safe_integer_schema_and_result_type_guard(
    *,
    integer_value: int,
    generated_schema_bytes_len: int,
    generated_symbol_definitions_count: int,
    mrtr_result_type: str,
) -> GuardDecision:
    """RL-13: Enforce IEEE-754 double-precision safe integer range (#3289), non-empty programmatic schema generation (#3148, #3154), and snake_case resultType (#3125)."""
    if integer_value < IEEE754_MIN_SAFE_INT or integer_value > IEEE754_MAX_SAFE_INT:
        return GuardDecision(
            allowed=False,
            code="MCP_IEEE754_SAFE_INTEGER_BOUND_EXCEEDED",
            detail=f"Integer {integer_value} exceeds IEEE-754 double-precision safe integer range [-2^53+1, 2^53-1] (#3289).",
        )
    if generated_schema_bytes_len <= 100 or generated_symbol_definitions_count <= 0:
        return GuardDecision(
            allowed=False,
            code="MCP_WILDCARD_EMPTY_SCHEMA_GENERATION_BLOCKED",
            detail="Generated JSON schema is near-empty or has zero symbol definitions; use programmatic TJS generator (#3148).",
        )
    if mrtr_result_type == "inputRequired":
        return GuardDecision(
            allowed=False,
            code="MCP_CAMELCASE_RESULT_TYPE_REJECTED",
            detail="Normative MRTR ResultType is snake_case 'input_required', not camelCase 'inputRequired' (#3125).",
        )
    if mrtr_result_type not in {"complete", "input_required"}:
        return GuardDecision(
            allowed=False,
            code="MCP_RESULT_TYPE_INVALID",
            detail=f"Unsupported MCP ResultType={mrtr_result_type!r} (#3125).",
        )
    return GuardDecision(
        allowed=True,
        code="MCP_SAFE_INT_SCHEMA_AND_RESULT_TYPE_OK",
        detail="IEEE-754 safe integer bound, programmatic schema definitions, and snake_case resultType verified.",
    )


# ---------------------------------------------------------------------------
# RL-14: Stripe AI #500, #504/#486, #426 & #343 Empty Choices & Skill Routing
# ---------------------------------------------------------------------------

def evaluate_stripe_ai_empty_choices_routing_and_ua_guard(
    *,
    provider_response_choices: list[Any],
    user_intent_kind: str,
    routed_skill: str,
    mcp_user_agent_version: str,
    package_json_version: str,
    checkout_form_target_path: str,
) -> GuardDecision:
    """RL-14: Throw NoContentGeneratedError on empty choices[] (#500), route provisioning vs discovery (#504/#486), sync MCP User-Agent version (#343), and wire /purchase (#426)."""
    if not provider_response_choices:
        return GuardDecision(
            allowed=False,
            code="NoContentGeneratedError",
            detail="HTTP 200 provider response returned empty choices[]; raised typed NoContentGeneratedError instead of TypeError (#500).",
        )
    if user_intent_kind == "provision_or_manage_resource" and routed_skill != "stripe-projects":
        return GuardDecision(
            allowed=False,
            code="STRIPE_SKILL_ROUTING_MISMATCH",
            detail="Explicit resource provisioning (including Neon/Supabase without saying Stripe) must route to stripe-projects (#504, #486).",
        )
    if user_intent_kind == "vendor_discovery" and routed_skill != "stripe-directory":
        return GuardDecision(
            allowed=False,
            code="STRIPE_SKILL_ROUTING_MISMATCH",
            detail="Vendor exploration/discovery must route to stripe-directory (#504, #505).",
        )
    if mcp_user_agent_version != package_json_version:
        return GuardDecision(
            allowed=False,
            code="STRIPE_MCP_USER_AGENT_VERSION_DRIFT",
            detail=f"MCP User-Agent version {mcp_user_agent_version!r} drifted from package.json {package_json_version!r} (#343).",
        )
    if checkout_form_target_path != "/purchase":
        return GuardDecision(
            allowed=False,
            code="STRIPE_CHECKOUT_FORM_PURCHASE_ROUTE_MISMATCH",
            detail="Checkout form and invoice fallback flow must wire to '/purchase' (#426).",
        )
    return GuardDecision(
        allowed=True,
        code="STRIPE_AI_CHOICES_ROUTING_AND_UA_OK",
        detail="Provider non-empty choices, skill routing, User-Agent version parity, and /purchase wiring verified.",
    )


# ---------------------------------------------------------------------------
# RL-15: Visa TAP #21, #18 & #11 Hybrid PQC ed25519-ml-dsa-65 & x402 Binding
# ---------------------------------------------------------------------------

def evaluate_visa_tap_hybrid_pqc_and_x402_guard(
    *,
    alg: str,
    signature_bytes_len: int,
    public_key_bytes_len: int,
    ed25519_leg_valid: bool,
    mldsa65_leg_valid: bool,
    did_resolved_via_explicit_registry: bool,
    x402_settlement_digest: str,
    tap_rfc9421_request_digest: str,
) -> GuardDecision:
    """RL-15: Verify Visa TAP ed25519-ml-dsa-65 (64B || 3309B = 3373B sig, 1952B pubkey) dual-leg verification (#21), explicit DIDResolverRegistry (#18), and x402 digest binding (#11)."""
    if alg != "ed25519-ml-dsa-65":
        return GuardDecision(
            allowed=False,
            code="TAP_HYBRID_PQC_ALG_INVALID",
            detail=f"Expected hybrid post-quantum algorithm 'ed25519-ml-dsa-65', got {alg!r} (#21).",
        )
    if signature_bytes_len != 3373 or public_key_bytes_len != 1952:
        return GuardDecision(
            allowed=False,
            code="TAP_HYBRID_PQC_KEY_OR_SIG_LENGTH_INVALID",
            detail=f"ed25519-ml-dsa-65 requires 3373B signature (64B+3309B) and 1952B public key, got sig={signature_bytes_len}B pub={public_key_bytes_len}B (#21).",
        )
    if not (ed25519_leg_valid and mldsa65_leg_valid):
        return GuardDecision(
            allowed=False,
            code="TAP_HYBRID_PQC_SINGLE_LEG_STRIPPING_BLOCKED",
            detail="Both Ed25519 and ML-DSA-65 signature legs must verify; single-leg downgrade rejected (#21).",
        )
    if not did_resolved_via_explicit_registry:
        return GuardDecision(
            allowed=False,
            code="TAP_IMPLICIT_DID_RESOLVER_BLOCKED",
            detail="DID resolution must use explicit DIDResolverRegistry (#18).",
        )
    if not x402_settlement_digest or x402_settlement_digest != tap_rfc9421_request_digest:
        return GuardDecision(
            allowed=False,
            code="TAP_X402_SETTLEMENT_DIGEST_MISMATCH",
            detail="x402 Solana/Base USDC settlement digest does not match Visa TAP RFC 9421 request digest (#11).",
        )
    return GuardDecision(
        allowed=True,
        code="TAP_HYBRID_PQC_AND_X402_BINDING_OK",
        detail="Visa TAP ed25519-ml-dsa-65 dual-leg PQC, DIDResolverRegistry, and x402 digest binding verified.",
    )


# ---------------------------------------------------------------------------
# RL-16: Sierra tau2-bench 2.0 #667, #666, #665, #650, #602 & #600 Guards
# ---------------------------------------------------------------------------

def evaluate_tau2_one_to_one_actions_retail_telecom_airline_guard(
    *,
    gold_actions: list[str],
    predicted_tool_calls: list[str],
    retail_exchange_old_item_id: str,
    retail_exchange_new_item_id: str,
    telecom_mmsc_url: str | None,
    airline_user_id: str,
    telecom_status_bar_tool_name: str,
    ended_in_infrastructure_error: bool,
) -> GuardDecision:
    """RL-16: Match gold actions to predicted tool calls one-to-one (#665), reject same-item retail exchange (#667), treat empty MMSC URL as unconfigured (#666), require lowercase airline user_id (#602), and enforce check_status_bar grounding (#600)."""
    if ended_in_infrastructure_error:
        return GuardDecision(
            allowed=False,
            code="TAU2_INFRASTRUCTURE_ERROR_EXCLUDED_FROM_DENOMINATOR",
            detail="Call ended in infrastructure error; excluded from score denominator and reported separately (#650).",
            metadata={"excluded_from_denominator": True},
        )
    if retail_exchange_old_item_id == retail_exchange_new_item_id:
        return GuardDecision(
            allowed=False,
            code="TAU2_RETAIL_SAME_ITEM_EXCHANGE_REJECTED",
            detail="The new item id should be different from the old item id in exchange_delivered_order_items (#667).",
        )
    if not bool(telecom_mmsc_url and telecom_mmsc_url.strip()):
        return GuardDecision(
            allowed=False,
            code="TAU2_TELECOM_EMPTY_MMSC_URL_UNCONFIGURED",
            detail="can_send_mms treats None or empty string mmsc_url='' as unconfigured (#666).",
        )
    if airline_user_id != airline_user_id.lower():
        return GuardDecision(
            allowed=False,
            code="TAU2_AIRLINE_USER_ID_MUST_BE_LOWERCASE",
            detail=f"Airline user_id={airline_user_id!r} contains uppercase letters; all airline user IDs are strictly lowercase (#602).",
        )
    if telecom_status_bar_tool_name != "check_status_bar":
        return GuardDecision(
            allowed=False,
            code="TAU2_TELECOM_STATUS_BAR_TOOL_GROUNDING_MISMATCH",
            detail=f"Telecom status-bar tool must be 'check_status_bar', not hallucinated {telecom_status_bar_tool_name!r} (#600).",
        )

    # One-to-one matching between gold_actions and predicted_tool_calls (#665)
    used_predicted_indices: set[int] = set()
    for gold in gold_actions:
        matched_idx = None
        for idx, pred in enumerate(predicted_tool_calls):
            if idx not in used_predicted_indices and pred == gold:
                matched_idx = idx
                break
        if matched_idx is None:
            return GuardDecision(
                allowed=False,
                code="TAU2_GOLD_ACTION_ONE_TO_ONE_MATCH_FAILED",
                detail=f"Repeated gold action {gold!r} was not satisfied by a distinct predicted tool call (#665).",
                metadata={"matched_count": len(used_predicted_indices), "required_count": len(gold_actions)},
            )
        used_predicted_indices.add(matched_idx)

    return GuardDecision(
        allowed=True,
        code="TAU2_ONE_TO_ONE_RETAIL_TELECOM_AIRLINE_OK",
        detail="One-to-one gold action matching, distinct-item exchange, non-empty MMSC URL, lowercase airline user_id, and check_status_bar verified.",
        metadata={"matched_count": len(used_predicted_indices)},
    )
