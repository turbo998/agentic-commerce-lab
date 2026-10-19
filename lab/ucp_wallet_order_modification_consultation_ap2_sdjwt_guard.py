"""Stage 45: UCP Wallet Attestation (#415) & Render Artifact (#635), Order Modification Safe Lookup & Permanent Fence (#945), Order Consultation Proposal Digest & Pre-Replay Auth (#946), and AP2 Merchant Authorization / SD-JWT+kb / P-521 Binding (#466/#496/#610/#625/#618) + Discount/Fulfillment Guards (#577/#578/#609/#617).

Implements deterministic offline validators covering:
1. UCP PR #415 (identity linking `wallet_attestation` non-OAuth mechanism) & PR #635
   (`com.mercadopago.payment.render_artifact` in-session out-of-band Pix action).
2. UCP PR #945 / EP #943 (`dev.ucp.shopping.order_modification` cancellation-first
   extension, safe GET `lookup_modification`, and permanent POST `fence_modification`).
3. UCP PR #946 / EP #944 (`dev.ucp.shopping.order_consultation` business-initiated
   post-order consultation, pre-replay buyer `:decide` scope check, single
   serialization-point closure, and RFC 8785 JCS `proposal_digest`).
4. UCP PRs #466, #496, #610, #625, #618 (AP2 `merchant_authorization` required field,
   `SD-JWT+kb` and `dSD-JWT` key-binding pattern, and `P-521`/`ES512` JWK curve-alg
   binding) plus PRs #577, #578, #609, #617 (discount rejection codes, `gift_line_item_id`,
   discoverable discount code secrecy, and fulfillment event selection linkage).
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any
from urllib.parse import urlparse


# UCP PR #496 + #610 SD-JWT+kb and dSD-JWT (`~~`) regex pattern:
# Allows `<issuer-JWT>~[disclosure]~...~<KB-JWT>` where KB-JWT has 3 dot-separated base64url parts.
SDJWT_WITH_KB_REGEX = re.compile(
    r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*\.[A-Za-z0-9_-]+"
    r"(~[A-Za-z0-9_-]*)*"
    r"~[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$"
)

JWK_CURVE_TO_ALG: dict[str, str] = {
    "P-256": "ES256",
    "P-384": "ES384",
    "P-521": "ES512",
    "Ed25519": "EdDSA",
}


def _jcs_rfc8785_serialize(value: Any) -> str:
    """Deterministic RFC 8785 JCS serializer for JSON objects/arrays/primitives."""
    if value is None or isinstance(value, (bool, int, str)):
        return json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    if isinstance(value, float):
        return json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_jcs_rfc8785_serialize(item) for item in value) + "]"
    if isinstance(value, dict):
        sorted_items = sorted(value.items(), key=lambda kv: str(kv[0]))
        return (
            "{"
            + ",".join(
                f"{json.dumps(str(k), separators=(',', ':'), ensure_ascii=False)}:{_jcs_rfc8785_serialize(v)}"
                for k, v in sorted_items
            )
            + "}"
        )
    raise TypeError(f"Unsupported type for JCS serialization: {type(value)!r}")


def compute_ucp_consultation_proposal_digest(canonical_proposal_input: dict[str, Any]) -> str:
    """Compute UCP PR #946 `proposal_digest` = `sha-256:<hex>` over RFC 8785 JCS input."""
    required_keys = {
        "consultation_id",
        "revision",
        "order_id",
        "baseline_order_version",
        "scope",
        "proposed_terms",
        "effective_time_rule",
        "decision_deadline",
        "execution_deadline",
        "digest_context",
    }
    missing = required_keys - set(canonical_proposal_input.keys())
    if missing:
        raise ValueError(f"Missing required proposal_digest input fields: {sorted(missing)}")
    # Exclude display and lifecycle members if caller passed extra fields
    filtered = {k: canonical_proposal_input[k] for k in sorted(required_keys)}
    jcs_bytes = _jcs_rfc8785_serialize(filtered).encode("utf-8")
    return "sha-256:" + hashlib.sha256(jcs_bytes).hexdigest()


@dataclass(frozen=True)
class UcpWalletAttestationAndRenderArtifactDecision:
    admitted: bool
    decision_code: str
    entitlement_granted: bool
    contributed_oauth_scopes: tuple[str, ...]
    render_artifact_valid: bool


def evaluate_ucp_wallet_attestation_and_payment_render_artifact_guard(
    context: dict[str, Any],
) -> UcpWalletAttestationAndRenderArtifactDecision:
    """Validate UCP PR #415 (`wallet_attestation`) and PR #635 (`render_artifact`)."""
    provider_config = context.get("provider_config", {})
    if provider_config.get("type") != "wallet_attestation":
        return UcpWalletAttestationAndRenderArtifactDecision(
            admitted=False,
            decision_code="INVALID_WALLET_ATTESTATION_PROVIDER_TYPE",
            entitlement_granted=False,
            contributed_oauth_scopes=(),
            render_artifact_valid=False,
        )

    provider_jwks_uri = str(provider_config.get("provider_jwks") or "")
    parsed_jwks = urlparse(provider_jwks_uri)
    if parsed_jwks.scheme != "https" or not parsed_jwks.netloc:
        return UcpWalletAttestationAndRenderArtifactDecision(
            admitted=False,
            decision_code="WALLET_ATTESTATION_PROVIDER_JWKS_URI_INVALID",
            entitlement_granted=False,
            contributed_oauth_scopes=(),
            render_artifact_valid=False,
        )

    contributed_scopes = tuple(context.get("contributed_oauth_scopes") or ())
    if contributed_scopes:
        return UcpWalletAttestationAndRenderArtifactDecision(
            admitted=False,
            decision_code="WALLET_ATTESTATION_OAUTH_SCOPE_CONFLATION_BLOCKED",
            entitlement_granted=False,
            contributed_oauth_scopes=contributed_scopes,
            render_artifact_valid=False,
        )

    jwks_keys: dict[str, str] = dict(context.get("published_jwks_kid_to_alg") or {})
    attestation = context.get("attestation", {})
    kid = str(attestation.get("kid") or "")
    alg = str(attestation.get("alg") or "")
    signature_valid = bool(attestation.get("signature_valid", False))
    if not kid or kid not in jwks_keys or jwks_keys[kid] != alg or not signature_valid:
        return UcpWalletAttestationAndRenderArtifactDecision(
            admitted=False,
            decision_code="WALLET_ATTESTATION_JWKS_KID_OR_SIGNATURE_INVALID",
            entitlement_granted=False,
            contributed_oauth_scopes=(),
            render_artifact_valid=False,
        )

    now_epoch = int(context.get("now_epoch", 0))
    attested_at = int(attestation.get("attested_at", 0))
    exp_epoch = int(attestation.get("exp", 0))
    max_age_seconds = int(context.get("max_age_seconds", 300))
    if exp_epoch <= now_epoch or (now_epoch - attested_at) > max_age_seconds or attested_at > now_epoch:
        return UcpWalletAttestationAndRenderArtifactDecision(
            admitted=False,
            decision_code="WALLET_ATTESTATION_EXPIRED_OR_STALE_BLOCKED",
            entitlement_granted=False,
            contributed_oauth_scopes=(),
            render_artifact_valid=False,
        )

    # Privacy rule: provider MUST NOT leak raw wallet balances/holdings unless explicitly requested
    if bool(attestation.get("contains_raw_wallet_holdings", False)) and not bool(
        context.get("requester_opted_into_merkle_proof", False)
    ):
        return UcpWalletAttestationAndRenderArtifactDecision(
            admitted=False,
            decision_code="WALLET_ATTESTATION_RAW_PORTFOLIO_DISCLOSURE_LEAK_BLOCKED",
            entitlement_granted=False,
            contributed_oauth_scopes=(),
            render_artifact_valid=False,
        )

    signed_predicate_met = bool(attestation.get("signed_predicate_met", False))
    unsigned_override_eligible = bool(attestation.get("unsigned_override_eligible", False))
    if not signed_predicate_met and unsigned_override_eligible:
        return UcpWalletAttestationAndRenderArtifactDecision(
            admitted=False,
            decision_code="UNSIGNED_WALLET_ENTITLEMENT_OVERRIDE_BLOCKED",
            entitlement_granted=False,
            contributed_oauth_scopes=(),
            render_artifact_valid=False,
        )

    # UCP PR #635: com.mercadopago.payment.render_artifact action validation
    render_action = context.get("render_artifact_action")
    if render_action is not None:
        if "required" in render_action:
            return UcpWalletAttestationAndRenderArtifactDecision(
                admitted=False,
                decision_code="RENDER_ARTIFACT_FORBIDDEN_REQUIRED_BOOLEAN_FIELD",
                entitlement_granted=False,
                contributed_oauth_scopes=(),
                render_artifact_valid=False,
            )
        config = render_action.get("config", {})
        if bool(config.get("contains_pan_or_otp_or_secret", False)):
            return UcpWalletAttestationAndRenderArtifactDecision(
                admitted=False,
                decision_code="RENDER_ARTIFACT_CREDENTIAL_LEAK_OR_UNTRUSTED_INSTRUCTIONS_URL_BLOCKED",
                entitlement_granted=False,
                contributed_oauth_scopes=(),
                render_artifact_valid=False,
            )
        instructions_url = config.get("instructions_url")
        if instructions_url is not None:
            parsed_inst = urlparse(str(instructions_url))
            allowed_origins = set(context.get("allowed_handler_origins") or ())
            origin = f"{parsed_inst.scheme}://{parsed_inst.netloc}"
            if parsed_inst.scheme != "https" or origin not in allowed_origins:
                return UcpWalletAttestationAndRenderArtifactDecision(
                    admitted=False,
                    decision_code="RENDER_ARTIFACT_CREDENTIAL_LEAK_OR_UNTRUSTED_INSTRUCTIONS_URL_BLOCKED",
                    entitlement_granted=False,
                    contributed_oauth_scopes=(),
                    render_artifact_valid=False,
                )

    return UcpWalletAttestationAndRenderArtifactDecision(
        admitted=True,
        decision_code="UCP_WALLET_ATTESTATION_AND_RENDER_ARTIFACT_VERIFIED",
        entitlement_granted=signed_predicate_met,
        contributed_oauth_scopes=(),
        render_artifact_valid=True,
    )


@dataclass(frozen=True)
class UcpOrderModificationLookupAndFenceDecision:
    admitted: bool
    decision_code: str
    lookup_or_fence_status: str
    key_permanently_fenced: bool
    cache_control: str


def evaluate_ucp_order_modification_lookup_and_fence_guard(
    context: dict[str, Any],
) -> UcpOrderModificationLookupAndFenceDecision:
    """Validate UCP PR #945 / EP #943 (`dev.ucp.shopping.order_modification`)."""
    if not bool(context.get("extension_negotiated", True)) or not bool(
        context.get("parent_order_capability_negotiated", True)
    ):
        return UcpOrderModificationLookupAndFenceDecision(
            admitted=False,
            decision_code="UNNEGOTIATED_ORDER_MODIFICATION_INVOCATION_BLOCKED",
            lookup_or_fence_status="modification_not_supported",
            key_permanently_fenced=False,
            cache_control="no-store",
        )

    cache_control = str(context.get("response_cache_control") or "no-store")
    if cache_control != "no-store":
        return UcpOrderModificationLookupAndFenceDecision(
            admitted=False,
            decision_code="ORDER_MODIFICATION_MISSING_NO_STORE_CACHE_CONTROL_BLOCKED",
            lookup_or_fence_status="invalid_cache_control",
            key_permanently_fenced=False,
            cache_control=cache_control,
        )

    method_kind = str(context.get("method_kind") or "create_modification")
    op = str(context.get("op") or "cancel")
    if op != "cancel":
        return UcpOrderModificationLookupAndFenceDecision(
            admitted=False,
            decision_code="UNSUPPORTED_ORDER_MODIFICATION_OPERATION_BLOCKED",
            lookup_or_fence_status="unsupported_operation",
            key_permanently_fenced=False,
            cache_control="no-store",
        )

    claimed_keys: set[str] = set(context.get("claimed_keys") or ())
    expired_claimed_keys: set[str] = set(context.get("expired_claimed_keys") or ())
    fenced_keys: set[str] = set(context.get("fenced_keys") or ())

    if method_kind == "lookup_modification":
        if bool(context.get("original_key_in_url_query", False)):
            return UcpOrderModificationLookupAndFenceDecision(
                admitted=False,
                decision_code="LOOKUP_ORIGINAL_IDEMPOTENCY_KEY_IN_URL_LEAK_BLOCKED",
                lookup_or_fence_status="invalid_lookup",
                key_permanently_fenced=False,
                cache_control="no-store",
            )
        if bool(context.get("lookup_mutated_fence_or_claim_state", False)):
            return UcpOrderModificationLookupAndFenceDecision(
                admitted=False,
                decision_code="LOOKUP_MODIFICATION_MUTATED_FENCE_OR_CLAIM_STATE_BLOCKED",
                lookup_or_fence_status="invalid_lookup_side_effect",
                key_permanently_fenced=False,
                cache_control="no-store",
            )
        target_key = str(context.get("original_idempotency_key") or "")
        status = "found" if target_key in claimed_keys else "unresolved"
        return UcpOrderModificationLookupAndFenceDecision(
            admitted=True,
            decision_code="ORDER_MODIFICATION_SAFE_LOOKUP_VERIFIED",
            lookup_or_fence_status=status,
            key_permanently_fenced=target_key in fenced_keys,
            cache_control="no-store",
        )

    if method_kind == "fence_modification":
        if context.get("fenced_until") is not None:
            return UcpOrderModificationLookupAndFenceDecision(
                admitted=False,
                decision_code="TEMPORARY_FENCED_UNTIL_TOMBSTONE_FORBIDDEN",
                lookup_or_fence_status="invalid_fence",
                key_permanently_fenced=False,
                cache_control="no-store",
            )
        target_key = str(context.get("original_idempotency_key") or "")
        fence_req_key = str(context.get("fence_request_idempotency_key") or "")
        if not fence_req_key or fence_req_key == target_key:
            return UcpOrderModificationLookupAndFenceDecision(
                admitted=False,
                decision_code="FENCE_MODIFICATION_REQUIRES_FRESH_IDEMPOTENCY_KEY",
                lookup_or_fence_status="invalid_fence_key",
                key_permanently_fenced=False,
                cache_control="no-store",
            )
        if target_key in claimed_keys:
            return UcpOrderModificationLookupAndFenceDecision(
                admitted=True,
                decision_code="FENCE_LOST_TO_EXISTING_CLAIM_RETURNED_FOUND",
                lookup_or_fence_status="found",
                key_permanently_fenced=False,
                cache_control="no-store",
            )
        if target_key in expired_claimed_keys:
            return UcpOrderModificationLookupAndFenceDecision(
                admitted=True,
                decision_code="FENCE_ON_EXPIRED_CLAIMED_KEY_RETURNED_UNRESOLVED",
                lookup_or_fence_status="unresolved",
                key_permanently_fenced=False,
                cache_control="no-store",
            )
        return UcpOrderModificationLookupAndFenceDecision(
            admitted=True,
            decision_code="ORDER_MODIFICATION_KEY_PERMANENTLY_FENCED",
            lookup_or_fence_status="fenced",
            key_permanently_fenced=True,
            cache_control="no-store",
        )

    # create_modification
    submission_key = str(context.get("idempotency_key") or "")
    if submission_key in fenced_keys:
        return UcpOrderModificationLookupAndFenceDecision(
            admitted=False,
            decision_code="FENCED_MODIFICATION_KEY_LATE_SUBMISSION_BLOCKED",
            lookup_or_fence_status="fenced_rejected",
            key_permanently_fenced=True,
            cache_control="no-store",
        )

    base_order_version = str(context.get("base_order_version") or "")
    current_order_version = str(context.get("current_order_version") or "")
    is_admitted_replay = bool(context.get("is_admitted_replay", False))
    if not is_admitted_replay and base_order_version != current_order_version:
        return UcpOrderModificationLookupAndFenceDecision(
            admitted=False,
            decision_code="ORDER_MODIFICATION_STALE_ORDER_VERSION_CONFLICT",
            lookup_or_fence_status="stale_order_state",
            key_permanently_fenced=False,
            cache_control="no-store",
        )

    atomicity = str(context.get("atomicity") or "atomic")
    unit_outcomes: list[str] = list(context.get("unit_outcomes") or ["committed"])
    if atomicity == "atomic" and "awaiting_business_decision" in unit_outcomes and "committed" in unit_outcomes:
        return UcpOrderModificationLookupAndFenceDecision(
            admitted=False,
            decision_code="ATOMIC_MODIFICATION_PARTIAL_COMMIT_WHILE_REVIEW_PENDING_BLOCKED",
            lookup_or_fence_status="invalid_atomic_partial_commit",
            key_permanently_fenced=False,
            cache_control="no-store",
        )

    return UcpOrderModificationLookupAndFenceDecision(
        admitted=True,
        decision_code="UCP_ORDER_MODIFICATION_CANCEL_ADMITTED",
        lookup_or_fence_status="committed",
        key_permanently_fenced=False,
        cache_control="no-store",
    )


@dataclass(frozen=True)
class UcpOrderConsultationDigestAndAuthDecision:
    admitted: bool
    decision_code: str
    computed_proposal_digest: str
    final_receipt_issued: bool


def evaluate_ucp_order_consultation_digest_and_auth_guard(
    context: dict[str, Any],
) -> UcpOrderConsultationDigestAndAuthDecision:
    """Validate UCP PR #946 / EP #944 (`dev.ucp.shopping.order_consultation`)."""
    canonical_input = context.get("canonical_proposal_input", {})
    computed_digest = compute_ucp_consultation_proposal_digest(canonical_input)

    # Authentication and dedicated `:decide` scope MUST be evaluated BEFORE replay lookup
    buyer_token_valid = bool(context.get("buyer_token_valid", False))
    token_subject = str(context.get("token_subject") or "")
    order_owner_subject = str(context.get("order_owner_subject") or "")
    token_scopes = set(context.get("token_scopes") or ())
    if (
        not buyer_token_valid
        or not token_subject
        or token_subject != order_owner_subject
        or "dev.ucp.shopping.order_consultation:decide" not in token_scopes
    ):
        return UcpOrderConsultationDigestAndAuthDecision(
            admitted=False,
            decision_code="CONSULTATION_DECIDE_AUTH_OR_SCOPE_FAILED_BEFORE_REPLAY",
            computed_proposal_digest=computed_digest,
            final_receipt_issued=False,
        )

    proposed_delta_minor = int(context.get("proposed_delta_minor", 0))
    delegation_max_delta_minor = int(context.get("delegation_max_delta_minor", 0))
    if proposed_delta_minor > delegation_max_delta_minor:
        return UcpOrderConsultationDigestAndAuthDecision(
            admitted=False,
            decision_code="CONSULTATION_DELEGATION_LIMIT_EXCEEDED",
            computed_proposal_digest=computed_digest,
            final_receipt_issued=False,
        )

    # Single serialization-point check for revision, supersession, withdrawal, and deadline
    serialization_epoch = int(context.get("serialization_point_epoch", 0))
    decision_deadline_epoch = int(context.get("decision_deadline_epoch", 0))
    active_revision = int(context.get("active_revision", 1))
    submitted_revision = int(context.get("submitted_revision", 1))
    consultation_status = str(context.get("consultation_status_at_serialization") or "open")
    if (
        submitted_revision != active_revision
        or consultation_status in {"withdrawn", "superseded", "expired"}
        or serialization_epoch > decision_deadline_epoch
    ):
        return UcpOrderConsultationDigestAndAuthDecision(
            admitted=False,
            decision_code="CONSULTATION_STALE_REVISION_OR_EXPIRED_AT_SERIALIZATION_POINT_BLOCKED",
            computed_proposal_digest=computed_digest,
            final_receipt_issued=False,
        )

    submitted_digest = str(context.get("submitted_proposal_digest") or "")
    if submitted_digest != computed_digest:
        return UcpOrderConsultationDigestAndAuthDecision(
            admitted=False,
            decision_code="CONSULTATION_PROPOSAL_DIGEST_MISMATCH_BLOCKED",
            computed_proposal_digest=computed_digest,
            final_receipt_issued=False,
        )

    if bool(context.get("approval_triggered_immediate_silent_capture", False)):
        return UcpOrderConsultationDigestAndAuthDecision(
            admitted=False,
            decision_code="CONSULTATION_APPROVAL_SILENT_IMMEDIATE_CAPTURE_BLOCKED",
            computed_proposal_digest=computed_digest,
            final_receipt_issued=False,
        )

    return UcpOrderConsultationDigestAndAuthDecision(
        admitted=True,
        decision_code="UCP_ORDER_CONSULTATION_DECISION_RECEIPT_COMMITTED",
        computed_proposal_digest=computed_digest,
        final_receipt_issued=True,
    )


@dataclass(frozen=True)
class UcpAp2MerchantAuthSdjwtAndDiscountFulfillmentDecision:
    admitted: bool
    decision_code: str
    sdjwt_kb_verified: bool
    jwk_curve_alg_bound: bool
    discount_and_fulfillment_valid: bool


def evaluate_ucp_ap2_merchant_auth_sdjwt_and_discount_fulfillment_guard(
    context: dict[str, Any],
) -> UcpAp2MerchantAuthSdjwtAndDiscountFulfillmentDecision:
    """Validate UCP PRs #466, #496, #610, #625, #618 and PRs #577, #578, #609, #617."""
    ap2_active = bool(context.get("ap2_active", True))
    merchant_auth = str(context.get("merchant_authorization") or "")
    if ap2_active and not merchant_auth:
        return UcpAp2MerchantAuthSdjwtAndDiscountFulfillmentDecision(
            admitted=False,
            decision_code="AP2_ACTIVE_CHECKOUT_MISSING_MERCHANT_AUTHORIZATION_BLOCKED",
            sdjwt_kb_verified=False,
            jwk_curve_alg_bound=False,
            discount_and_fulfillment_valid=False,
        )

    # UCP PR #625 + #618: JWK curve -> alg pairing (including P-521 -> ES512) & protected header alg binding
    jwk = context.get("signing_jwk", {})
    crv = str(jwk.get("crv") or "P-256")
    jwk_alg = jwk.get("alg")
    protected_alg = str(context.get("protected_jws_alg") or "ES256")
    expected_alg = JWK_CURVE_TO_ALG.get(crv)
    if expected_alg is None or protected_alg != expected_alg or (jwk_alg is not None and jwk_alg != expected_alg):
        return UcpAp2MerchantAuthSdjwtAndDiscountFulfillmentDecision(
            admitted=False,
            decision_code="AP2_JWK_CURVE_OR_PROTECTED_ALG_MISMATCH_BLOCKED",
            sdjwt_kb_verified=False,
            jwk_curve_alg_bound=False,
            discount_and_fulfillment_valid=False,
        )

    # UCP PR #496 + #610: checkout_mandate SD-JWT+kb / dSD-JWT (`~~`) with 3-part KB-JWT
    checkout_mandate = str(context.get("checkout_mandate") or "")
    if ap2_active and not SDJWT_WITH_KB_REGEX.match(checkout_mandate):
        return UcpAp2MerchantAuthSdjwtAndDiscountFulfillmentDecision(
            admitted=False,
            decision_code="AP2_CHECKOUT_MANDATE_MISSING_OR_MALFORMED_SDJWT_KB_BLOCKED",
            sdjwt_kb_verified=False,
            jwk_curve_alg_bound=True,
            discount_and_fulfillment_valid=False,
        )

    # UCP PR #578: Zero-price promotional gift line items must be linked by applied_discount.gift_line_item_id
    line_items: list[dict[str, Any]] = list(context.get("line_items") or [])
    applied_discounts: list[dict[str, Any]] = list(context.get("applied_discounts") or [])
    linked_gift_ids = {
        str(d.get("gift_line_item_id"))
        for d in applied_discounts
        if d.get("gift_line_item_id") is not None
    }
    for item in line_items:
        if int(item.get("total_minor", 0)) == 0 and bool(item.get("is_promotional_gift", False)):
            if str(item.get("id")) not in linked_gift_ids:
                return UcpAp2MerchantAuthSdjwtAndDiscountFulfillmentDecision(
                    admitted=False,
                    decision_code="UNEXPLAINED_ZERO_PRICE_GIFT_LINE_ITEM_BLOCKED",
                    sdjwt_kb_verified=True,
                    jwk_curve_alg_bound=True,
                    discount_and_fulfillment_valid=False,
                )

    # UCP PR #609: discounts.available[] with type == "code" must not expose the secret code string
    available_discounts: list[dict[str, Any]] = list(context.get("available_discounts") or [])
    for avail in available_discounts:
        if avail.get("type") == "code" and avail.get("code") is not None:
            return UcpAp2MerchantAuthSdjwtAndDiscountFulfillmentDecision(
                admitted=False,
                decision_code="DISCOVERABLE_DISCOUNT_SECRET_CODE_LEAK_BLOCKED",
                sdjwt_kb_verified=True,
                jwk_curve_alg_bound=True,
                discount_and_fulfillment_valid=False,
            )

    # UCP PR #617: fulfillment_event links to selected checkout method/option and valid delivery window
    fulfillment_event = context.get("fulfillment_event")
    if fulfillment_event is not None:
        selected_method_ids = set(context.get("selected_fulfillment_method_ids") or ())
        selected_option_ids = set(context.get("selected_fulfillment_option_ids") or ())
        ev_method = str(fulfillment_event.get("fulfillment_method_id") or "")
        ev_option = str(fulfillment_event.get("fulfillment_option_id") or "")
        earliest = int(fulfillment_event.get("estimated_delivery_earliest_epoch", 0))
        latest = int(fulfillment_event.get("estimated_delivery_latest_epoch", 0))
        if (
            (selected_method_ids and ev_method not in selected_method_ids)
            or (selected_option_ids and ev_option not in selected_option_ids)
            or earliest > latest
        ):
            return UcpAp2MerchantAuthSdjwtAndDiscountFulfillmentDecision(
                admitted=False,
                decision_code="FULFILLMENT_EVENT_SELECTION_OR_DELIVERY_WINDOW_MISMATCH_BLOCKED",
                sdjwt_kb_verified=True,
                jwk_curve_alg_bound=True,
                discount_and_fulfillment_valid=False,
            )

    return UcpAp2MerchantAuthSdjwtAndDiscountFulfillmentDecision(
        admitted=True,
        decision_code="UCP_AP2_MERCHANT_AUTH_SDJWT_DISCOUNT_FULFILLMENT_VERIFIED",
        sdjwt_kb_verified=True,
        jwk_curve_alg_bound=True,
        discount_and_fulfillment_valid=True,
    )
