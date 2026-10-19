"""Stage 44: UCP `platform_reference` Correlation & Immutability (#839), Cart `continue_url` &
Permalink `ucp/version` Two-Phase Resolution (#801/#793), Per-Operation-Class Idempotency &
`ETag`/`If-Match` Conditional Writes (#782/#679/#628) + Agent Signals (#835), Identity-Linking
Recognized-Issuer Anchoring & Loyalty Breakdown (#850/#783/#662), and Google AP2 `open_mandate_hash`
RFC 8785 JCS Derivation (#279), Entropy-Based `checkout_hash` (#278), `(type, id)` Instrument /
Non-Empty `Merchant.id` Constraints (#301/#324) & `rail_confirmation_verified` Receipt Honesty (#335).
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Mapping
from urllib.parse import urlparse


DATE_VERSION_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PII_OR_CREDENTIAL_PATTERNS = (
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),  # email
    re.compile(r"^eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$"),  # JWT/JWS
    re.compile(r"\b(?:sk_live_|rk_live_|oat_|Bearer\s+)[A-Za-z0-9_-]+"),  # secret/token
)


def _jcs_canonicalize(value: Any) -> str:
    """Deterministic RFC 8785 JSON Canonicalization Scheme (JCS) serializer for JSON values."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return json.dumps(value, allow_nan=False)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_jcs_canonicalize(item) for item in value) + "]"
    if isinstance(value, Mapping):
        # RFC 8785 sorts object properties lexicographically by UTF-16 code units (equivalent to code point for BMP)
        sorted_items = sorted(value.items(), key=lambda kv: str(kv[0]))
        return (
            "{"
            + ",".join(
                f"{json.dumps(str(k), ensure_ascii=False)}:{_jcs_canonicalize(v)}"
                for k, v in sorted_items
            )
            + "}"
        )
    raise TypeError(f"Unsupported JCS type: {type(value)!r}")


@dataclass(frozen=True)
class UCPPlatformReferencePermalinkDecision:
    allowed: bool
    decision_code: str
    retained_platform_reference: str | None
    selected_permalink_version: str
    consumed_control_params: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class UCPIdempotencyConditionalWriteSignalsDecision:
    allowed: bool
    decision_code: str
    http_status: int
    mcp_error_code: int | None
    etag_matched: bool
    reason: str


@dataclass(frozen=True)
class UCPIdentityIssuerLoyaltyDecision:
    allowed: bool
    decision_code: str
    selected_provider_issuer: str | None
    fallback_to_direct_oauth: bool
    loyalty_forecast_minor: int
    reason: str


@dataclass(frozen=True)
class AP2MandateHashConstraintsReceiptDecision:
    allowed: bool
    decision_code: str
    open_mandate_hash: str
    rail_confirmation_verified: bool
    reason: str


def evaluate_ucp_platform_reference_and_permalink_version_guard(
    context: Mapping[str, Any],
) -> UCPPlatformReferencePermalinkDecision:
    """Enforce UCP PR #839 (`platform_reference` create-only immutability, Order carry-over,
    and no-PII/credential/auth misuse), PR #801 (Cart `continue_url` HTTPS & item preservation),
    and PR #793 (`ucp/version` permalink two-phase resolution & control-parameter consumption).
    """
    create_ref = context.get("create_platform_reference")
    update_or_complete_ref = context.get("update_or_complete_platform_reference")
    business_effective_ref = context.get("business_effective_platform_reference")
    order_ref = context.get("order_platform_reference")
    used_for_auth_or_idempotency = bool(context.get("used_platform_reference_for_auth_or_idempotency", False))

    if create_ref is not None:
        if not isinstance(create_ref, str) or not (1 <= len(create_ref) <= 512):
            return UCPPlatformReferencePermalinkDecision(
                allowed=False,
                decision_code="PLATFORM_REFERENCE_INVALID_TYPE_OR_LENGTH_BLOCKED",
                retained_platform_reference=None,
                selected_permalink_version="",
                consumed_control_params=(),
                reason="platform_reference must be a string between 1 and 512 characters.",
            )
        for pat in PII_OR_CREDENTIAL_PATTERNS:
            if pat.search(create_ref):
                return UCPPlatformReferencePermalinkDecision(
                    allowed=False,
                    decision_code="PLATFORM_REFERENCE_PII_CREDENTIAL_OR_AUTH_MISUSE_BLOCKED",
                    retained_platform_reference=None,
                    selected_permalink_version="",
                    consumed_control_params=(),
                    reason="platform_reference MUST NOT contain PII, JWTs, or credentials.",
                )

    if used_for_auth_or_idempotency:
        return UCPPlatformReferencePermalinkDecision(
            allowed=False,
            decision_code="PLATFORM_REFERENCE_PII_CREDENTIAL_OR_AUTH_MISUSE_BLOCKED",
            retained_platform_reference=create_ref,
            selected_permalink_version="",
            consumed_control_params=(),
            reason="platform_reference MUST NOT be used for authentication, authorization, or idempotency.",
        )

    if update_or_complete_ref is not None and business_effective_ref != create_ref:
        return UCPPlatformReferencePermalinkDecision(
            allowed=False,
            decision_code="PLATFORM_REFERENCE_MUTATED_ON_UPDATE_OR_COMPLETE_BLOCKED",
            retained_platform_reference=create_ref,
            selected_permalink_version="",
            consumed_control_params=(),
            reason="Business MUST ignore platform_reference on update/complete and retain the Create Checkout value.",
        )

    if order_ref != create_ref:
        return UCPPlatformReferencePermalinkDecision(
            allowed=False,
            decision_code="ORDER_PLATFORM_REFERENCE_CARRYOVER_MISMATCH",
            retained_platform_reference=create_ref,
            selected_permalink_version="",
            consumed_control_params=(),
            reason="Order response MUST carry platform_reference unchanged from originating checkout.",
        )

    # UCP PR #801: Cart continue_url absolute HTTPS & preserves line_items
    cart_continue_url = str(context.get("cart_continue_url", ""))
    cart_preserves_line_items = bool(context.get("cart_continue_url_preserves_line_items", True))
    parsed_continue = urlparse(cart_continue_url)
    if (
        parsed_continue.scheme != "https"
        or not parsed_continue.netloc
        or not cart_preserves_line_items
    ):
        return UCPPlatformReferencePermalinkDecision(
            allowed=False,
            decision_code="CART_CONTINUE_URL_NOT_HTTPS_OR_DROPPED_LINE_ITEMS_BLOCKED",
            retained_platform_reference=create_ref,
            selected_permalink_version="",
            consumed_control_params=(),
            reason="Cart continue_url MUST be absolute HTTPS and preserve current line_items, quantities, and variants.",
        )

    # UCP PR #793: Permalink ucp/version two-phase resolution & control parameter consumption
    permalink_params: list[tuple[str, str]] = list(context.get("permalink_query_params") or [])
    supported_versions: tuple[str, ...] = tuple(
        sorted(context.get("supported_versions") or ("2026-04-08", "2026-08-25"))
    )
    default_version = str(context.get("default_version") or supported_versions[-1])
    redirect_url_leaked_control_param = bool(context.get("redirect_url_leaked_control_param", False))
    applied_ucp_control_as_shopping_state = bool(context.get("applied_ucp_control_as_shopping_state", False))
    returned_json_version_unsupported_to_browser = bool(
        context.get("returned_json_version_unsupported_to_browser", False)
    )

    if returned_json_version_unsupported_to_browser:
        return UCPPlatformReferencePermalinkDecision(
            allowed=False,
            decision_code="PERMALINK_BROWSER_NAVIGATION_JSON_VERSION_ERROR_FORBIDDEN",
            retained_platform_reference=create_ref,
            selected_permalink_version="",
            consumed_control_params=(),
            reason="Business MUST NOT answer a browser permalink navigation with a UCP JSON version_unsupported error.",
        )

    # Phase 1: Normalize names, detect collisions, extract ucp/version regardless of parameter order
    seen_keys: set[str] = set()
    version_values: list[str] = []
    has_ucp_field_paths = False
    consumed_controls: list[str] = []

    for raw_k, raw_v in permalink_params:
        k = raw_k.strip()
        if k in seen_keys:
            return UCPPlatformReferencePermalinkDecision(
                allowed=False,
                decision_code="PERMALINK_VERSION_CONTROL_PARAM_COLLISION_OR_STATE_LEAK_BLOCKED",
                retained_platform_reference=create_ref,
                selected_permalink_version="",
                consumed_control_params=(),
                reason=f"Duplicate permalink query parameter '{k}' detected during Phase 1 normalization.",
            )
        seen_keys.add(k)
        if k == "ucp/version":
            version_values.append(raw_v.strip())
            consumed_controls.append(k)
        elif k == "continue_to" or k.startswith("ucp/"):
            consumed_controls.append(k)
        elif "/" in k:
            has_ucp_field_paths = True

    if redirect_url_leaked_control_param or applied_ucp_control_as_shopping_state:
        return UCPPlatformReferencePermalinkDecision(
            allowed=False,
            decision_code="PERMALINK_VERSION_CONTROL_PARAM_COLLISION_OR_STATE_LEAK_BLOCKED",
            retained_platform_reference=create_ref,
            selected_permalink_version="",
            consumed_control_params=tuple(consumed_controls),
            reason="Control parameters (ucp/version, continue_to, ucp/*) MUST be consumed and never leaked or applied as shopping state.",
        )

    platform_generated_permalink = bool(context.get("platform_generated_permalink", True))
    if platform_generated_permalink and has_ucp_field_paths and not version_values:
        return UCPPlatformReferencePermalinkDecision(
            allowed=False,
            decision_code="PERMALINK_WITH_FIELD_PATHS_MISSING_UCP_VERSION_BLOCKED",
            retained_platform_reference=create_ref,
            selected_permalink_version="",
            consumed_control_params=tuple(consumed_controls),
            reason="Platform-generated permalinks carrying UCP field-path parameters MUST include ucp/version.",
        )

    if not version_values:
        selected_version = default_version
    else:
        ver = version_values[0]
        if not DATE_VERSION_RE.match(ver):
            return UCPPlatformReferencePermalinkDecision(
                allowed=False,
                decision_code="PERMALINK_MALFORMED_OR_PRERELEASE_UCP_VERSION_BLOCKED",
                retained_platform_reference=create_ref,
                selected_permalink_version="",
                consumed_control_params=tuple(consumed_controls),
                reason="ucp/version MUST be YYYY-MM-DD and never a pre-release identifier.",
            )
        if ver in supported_versions:
            selected_version = ver
        else:
            later = [sv for sv in supported_versions if sv > ver]
            selected_version = later[0] if later else supported_versions[-1]

    return UCPPlatformReferencePermalinkDecision(
        allowed=True,
        decision_code="UCP_PLATFORM_REFERENCE_AND_PERMALINK_VERSION_VERIFIED",
        retained_platform_reference=create_ref,
        selected_permalink_version=selected_version,
        consumed_control_params=tuple(consumed_controls),
        reason="platform_reference immutability, Cart continue_url, and two-phase ucp/version permalink verified.",
    )


def evaluate_ucp_idempotency_conditional_write_and_signals_guard(
    context: Mapping[str, Any],
) -> UCPIdempotencyConditionalWriteSignalsDecision:
    """Enforce UCP PR #782 & #679 (per-operation-class idempotency identity, JCS payload hashing,
    and signed header vs meta['idempotency-key'] equality), PR #628 (ETag / If-Match conditional
    writes with 412/428), and PR #835 (payee_continuity & missing browser signals non-decline rule).
    """
    request_signed = bool(context.get("request_signed", True))
    header_idempotency_key = context.get("header_idempotency_key")
    meta_idempotency_key = context.get("meta_idempotency_key")

    if request_signed and header_idempotency_key and meta_idempotency_key is not None:
        if str(header_idempotency_key) != str(meta_idempotency_key):
            return UCPIdempotencyConditionalWriteSignalsDecision(
                allowed=False,
                decision_code="IDEMPOTENCY_HEADER_META_MISMATCH_BLOCKED",
                http_status=400,
                mcp_error_code=-32602,
                etag_matched=False,
                reason="Payload meta['idempotency-key'] MUST equal the covered Idempotency-Key header on signed requests.",
            )

    operation_name = str(context.get("operation_name", "update_checkout"))
    operation_class = str(context.get("operation_class", "payload_carrying"))  # target_only | payload_carrying
    target_resource_id = str(context.get("target_resource_id", ""))
    payload_body = context.get("payload_body") or {}

    stored_record: Mapping[str, Any] | None = context.get("stored_idempotency_record")
    if stored_record is not None:
        stored_op = str(stored_record.get("operation_name", ""))
        stored_target = str(stored_record.get("target_resource_id", ""))
        if stored_op != operation_name or stored_target != target_resource_id:
            return UCPIdempotencyConditionalWriteSignalsDecision(
                allowed=False,
                decision_code="IDEMPOTENCY_KEY_CROSS_OPERATION_OR_TARGET_REUSE_BLOCKED",
                http_status=409,
                mcp_error_code=-32000,
                etag_matched=False,
                reason="Stored Idempotency-Key reused across a different operation or target resource.",
            )
        if operation_class == "payload_carrying":
            stored_payload = stored_record.get("payload_body") or {}
            curr_hash = hashlib.sha256(_jcs_canonicalize(payload_body).encode("utf-8")).hexdigest()
            stored_hash = hashlib.sha256(_jcs_canonicalize(stored_payload).encode("utf-8")).hexdigest()
            if curr_hash != stored_hash:
                return UCPIdempotencyConditionalWriteSignalsDecision(
                    allowed=False,
                    decision_code="IDEMPOTENCY_KEY_PAYLOAD_MISMATCH_CONFLICT",
                    http_status=409,
                    mcp_error_code=-32000,
                    etag_matched=False,
                    reason="Stored Idempotency-Key reused with a different JCS-canonicalized payload.",
                )

    # UCP PR #628: Conditional writes via ETag / If-Match
    conditional_write_required = bool(context.get("conditional_write_required", False))
    current_etag = context.get("current_etag")
    if_match_header = context.get("if_match_header")

    if conditional_write_required and not if_match_header:
        return UCPIdempotencyConditionalWriteSignalsDecision(
            allowed=False,
            decision_code="CHECKOUT_CONDITIONAL_WRITE_PRECONDITION_REQUIRED",
            http_status=428,
            mcp_error_code=None,
            etag_matched=False,
            reason="Business requires conditional writes (If-Match header missing -> 428 Precondition Required).",
        )

    if current_etag is not None and if_match_header is not None:
        if str(current_etag) != str(if_match_header):
            return UCPIdempotencyConditionalWriteSignalsDecision(
                allowed=False,
                decision_code="CHECKOUT_CONDITIONAL_WRITE_ETAG_PRECONDITION_FAILED",
                http_status=412,
                mcp_error_code=None,
                etag_matched=False,
                reason="Concurrent checkout writer modified state (ETag != If-Match -> 412 Precondition Failed).",
            )

    # UCP PR #835: Well-known agent signals
    declined_solely_on_payee_change = bool(context.get("declined_solely_on_payee_change", False))
    penalized_missing_browser_signals = bool(context.get("penalized_missing_browser_signals", False))
    placed_unverifiable_instruction_provenance_in_signals = bool(
        context.get("placed_unverifiable_instruction_provenance_in_signals", False)
    )

    if (
        declined_solely_on_payee_change
        or penalized_missing_browser_signals
        or placed_unverifiable_instruction_provenance_in_signals
    ):
        return UCPIdempotencyConditionalWriteSignalsDecision(
            allowed=False,
            decision_code="AGENT_SIGNAL_PAYEE_CHANGE_OR_MISSING_BROWSER_FALSE_DECLINE_BLOCKED",
            http_status=422,
            mcp_error_code=-32000,
            etag_matched=True,
            reason="payee_continuity is scoring-only; missing browser signals must not be penalized; instruction_provenance belongs in Correspondence.",
        )

    return UCPIdempotencyConditionalWriteSignalsDecision(
        allowed=True,
        decision_code="UCP_IDEMPOTENCY_CONDITIONAL_WRITE_AND_SIGNALS_VERIFIED",
        http_status=200,
        mcp_error_code=None,
        etag_matched=True,
        reason="Per-operation-class idempotency, ETag/If-Match optimistic concurrency, and agent signals verified.",
    )


def evaluate_ucp_identity_recognized_issuer_and_loyalty_guard(
    context: Mapping[str, Any],
) -> UCPIdentityIssuerLoyaltyDecision:
    """Enforce UCP PR #850 (recognized-issuer anchoring before discovery or subject_token exchange),
    PR #783 / #970 (per-user subject_token binding), and PR #662 (loyalty minor-unit &
    earning_forecast.breakdown sum invariant).
    """
    recognized_issuers: set[str] = set(context.get("recognized_issuers") or ())
    business_providers: list[Mapping[str, Any]] = list(context.get("business_providers") or [])
    platform_attempted_unrecognized_discovery_or_exchange = bool(
        context.get("platform_attempted_unrecognized_discovery_or_exchange", False)
    )
    subject_token_issuer = str(context.get("subject_token_issuer", ""))
    subject_token_user_id = str(context.get("subject_token_user_id", ""))
    acting_user_id = str(context.get("acting_user_id", ""))

    if platform_attempted_unrecognized_discovery_or_exchange:
        return UCPIdentityIssuerLoyaltyDecision(
            allowed=False,
            decision_code="UNRECOGNIZED_OR_NORMALIZED_IDP_ISSUER_SUBJECT_TOKEN_EXFILTRATION_BLOCKED",
            selected_provider_issuer=None,
            fallback_to_direct_oauth=False,
            loyalty_forecast_minor=0,
            reason="Platform MUST NOT run discovery against or present subject_token to an unrecognized or trailing-slash-normalized auth_url.",
        )

    if subject_token_user_id and acting_user_id and subject_token_user_id != acting_user_id:
        return UCPIdentityIssuerLoyaltyDecision(
            allowed=False,
            decision_code="CROSS_USER_SUBJECT_TOKEN_SUBSTITUTION_BLOCKED",
            selected_provider_issuer=None,
            fallback_to_direct_oauth=False,
            loyalty_forecast_minor=0,
            reason="Selected subject_token MUST belong to the user on whose behalf the platform is acting.",
        )

    # Exact string match (RFC 8414 §3.3, no trailing-slash normalization)
    selected_issuer: str | None = None
    for entry in business_providers:
        auth_url = str(entry.get("auth_url", ""))
        if auth_url in recognized_issuers and auth_url == subject_token_issuer:
            selected_issuer = auth_url
            break

    fallback_direct = selected_issuer is None

    # UCP PR #662: Loyalty minor-unit & earning_forecast.breakdown sum invariant
    loyalty: Mapping[str, Any] = context.get("loyalty") or {}
    forecast: Mapping[str, Any] = loyalty.get("earning_forecast") or {}
    if forecast:
        forecast_amount = int(forecast.get("amount", 0))
        breakdown = list(forecast.get("breakdown") or [])
        if breakdown:
            breakdown_sum = sum(int(item.get("amount", 0)) for item in breakdown)
            if breakdown_sum != forecast_amount:
                return UCPIdentityIssuerLoyaltyDecision(
                    allowed=False,
                    decision_code="LOYALTY_EARNING_FORECAST_BREAKDOWN_SUM_MISMATCH",
                    selected_provider_issuer=selected_issuer,
                    fallback_to_direct_oauth=fallback_direct,
                    loyalty_forecast_minor=forecast_amount,
                    reason="earning_forecast.breakdown amounts MUST sum to earning_forecast.amount.",
                )
    else:
        forecast_amount = 0

    if bool(loyalty.get("discount_expressed_in_major_units", False)):
        return UCPIdentityIssuerLoyaltyDecision(
            allowed=False,
            decision_code="LOYALTY_DISCOUNT_MAJOR_UNIT_CONFUSION_BLOCKED",
            selected_provider_issuer=selected_issuer,
            fallback_to_direct_oauth=fallback_direct,
            loyalty_forecast_minor=forecast_amount,
            reason="Loyalty discounts and allocations MUST be expressed in integer minor units (e.g., 1000 for $10.00).",
        )

    return UCPIdentityIssuerLoyaltyDecision(
        allowed=True,
        decision_code="UCP_IDENTITY_ISSUER_ANCHORING_AND_LOYALTY_VERIFIED",
        selected_provider_issuer=selected_issuer,
        fallback_to_direct_oauth=fallback_direct,
        loyalty_forecast_minor=forecast_amount,
        reason="Recognized-issuer anchoring, per-user subject_token binding, and loyalty breakdown invariant verified.",
    )


def compute_ap2_open_mandate_hash(unsigned_mandate_claims: Mapping[str, Any]) -> str:
    """Compute Google AP2 PR #279 `open_mandate_hash = SHA-256(JCS_RFC8785(unsigned_open_checkout_mandate_body))`."""
    canonical = _jcs_canonicalize(unsigned_mandate_claims)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def evaluate_ap2_mandate_hash_constraints_and_receipt_guard(
    context: Mapping[str, Any],
) -> AP2MandateHashConstraintsReceiptDecision:
    """Enforce Google AP2 PR #279 (`open_mandate_hash` JCS claims derivation),
    PR #278 (entropy-based `checkout_hash` requirement), PR #301 (`(type, id)` allowed
    instrument matching), PR #324 (non-empty `Merchant.id` matching without display-name fallback),
    and PR #335 (`PaymentReceipt.rail_confirmation_verified`).
    """
    unsigned_claims: Mapping[str, Any] = context.get("unsigned_open_mandate_claims") or {}
    derived_from_jws_compact = bool(context.get("derived_from_jws_compact_string", False))
    sorted_arrays_during_canonicalization = bool(
        context.get("sorted_arrays_during_canonicalization", False)
    )

    if derived_from_jws_compact or sorted_arrays_during_canonicalization:
        return AP2MandateHashConstraintsReceiptDecision(
            allowed=False,
            decision_code="AP2_OPEN_MANDATE_HASH_JWS_ENVELOPE_OR_ARRAY_SORT_BUG_BLOCKED",
            open_mandate_hash="",
            rail_confirmation_verified=False,
            reason="open_mandate_hash MUST be derived via RFC 8785 JCS over the unsigned claims object without sorting arrays or hashing JWS envelopes.",
        )

    mandate_hash = compute_ap2_open_mandate_hash(unsigned_claims)
    expected_hash = context.get("expected_open_mandate_hash")
    if expected_hash is not None and str(expected_hash) != mandate_hash:
        return AP2MandateHashConstraintsReceiptDecision(
            allowed=False,
            decision_code="AP2_OPEN_MANDATE_HASH_MISMATCH_BLOCKED",
            open_mandate_hash=mandate_hash,
            rail_confirmation_verified=False,
            reason="open_mandate_hash does not match expected RFC 8785 JCS SHA-256 digest.",
        )

    # AP2 PR #278: Entropy-based checkout_hash requirement (allows Ed25519 when payload carries >=128b entropy)
    checkout_jwt_entropy_bits = int(context.get("checkout_jwt_payload_entropy_bits", 128))
    if checkout_jwt_entropy_bits < 128:
        return AP2MandateHashConstraintsReceiptDecision(
            allowed=False,
            decision_code="AP2_LOW_ENTROPY_CHECKOUT_JWT_RAINBOW_TABLE_RISK_BLOCKED",
            open_mandate_hash=mandate_hash,
            rail_confirmation_verified=False,
            reason="Checkout JWT payload MUST carry a high-entropy per-session claim (>= 128 bits) so checkout_hash resists rainbow-table attacks.",
        )

    # AP2 PR #301: Match allowed payment instruments by (type, id), not id alone
    allowed_instruments: list[Mapping[str, Any]] = list(context.get("allowed_payment_instruments") or [])
    presented_instrument: Mapping[str, Any] = context.get("presented_payment_instrument") or {}
    if allowed_instruments:
        pres_id = str(presented_instrument.get("id", "")).strip()
        pres_type = str(presented_instrument.get("type", "")).strip()
        matched_inst = any(
            str(a.get("id", "")).strip() == pres_id and str(a.get("type", "")).strip() == pres_type
            for a in allowed_instruments
        )
        if not matched_inst:
            return AP2MandateHashConstraintsReceiptDecision(
                allowed=False,
                decision_code="AP2_INSTRUMENT_TYPE_CONFUSION_ON_ID_ONLY_MATCH_BLOCKED",
                open_mandate_hash=mandate_hash,
                rail_confirmation_verified=False,
                reason="AllowedPaymentInstrumentEvaluator MUST match both (type, id), never id alone.",
            )

    # AP2 PR #324: Match merchant/payee by stable non-empty id (drop name+website fallback, CWE-639)
    allowed_merchants: list[Mapping[str, Any]] = list(context.get("allowed_merchants") or [])
    presented_merchant: Mapping[str, Any] = context.get("presented_merchant") or {}
    if allowed_merchants:
        pres_mid = str(presented_merchant.get("id", "")).strip()
        if not pres_mid or not any(
            bool(str(m.get("id", "")).strip()) and str(m.get("id", "")).strip() == pres_mid
            for m in allowed_merchants
        ):
            return AP2MandateHashConstraintsReceiptDecision(
                allowed=False,
                decision_code="AP2_EMPTY_MERCHANT_ID_DISPLAY_NAME_SPOOF_BLOCKED",
                open_mandate_hash=mandate_hash,
                rail_confirmation_verified=False,
                reason="Merchant/Payee constraint MUST match by non-empty id equality and never fall back to spoofable name+website.",
            )

    # AP2 PR #335: PaymentReceipt rail_confirmation_verified honesty
    receipt: Mapping[str, Any] = context.get("payment_receipt") or {}
    psp_confirmed = bool(receipt.get("psp_independently_confirmed", True))
    network_confirmed = bool(receipt.get("network_independently_confirmed", True))
    claimed_verified = bool(receipt.get("rail_confirmation_verified", False))

    if claimed_verified and not (psp_confirmed and network_confirmed):
        return AP2MandateHashConstraintsReceiptDecision(
            allowed=False,
            decision_code="AP2_UNVERIFIED_SELF_GENERATED_RAIL_RECEIPT_CLAIMED_VERIFIED_BLOCKED",
            open_mandate_hash=mandate_hash,
            rail_confirmation_verified=False,
            reason="PaymentReceipt MUST NOT set rail_confirmation_verified=true when confirmation IDs are self-generated without independent rail checks.",
        )

    return AP2MandateHashConstraintsReceiptDecision(
        allowed=True,
        decision_code="AP2_MANDATE_HASH_CONSTRAINTS_AND_RECEIPT_VERIFIED",
        open_mandate_hash=mandate_hash,
        rail_confirmation_verified=claimed_verified and psp_confirmed and network_confirmed,
        reason="AP2 open_mandate_hash JCS derivation, checkout_hash entropy, (type, id) instrument, non-empty merchant.id, and receipt verification passed.",
    )
