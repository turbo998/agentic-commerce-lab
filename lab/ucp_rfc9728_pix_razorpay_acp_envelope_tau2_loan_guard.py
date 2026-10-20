"""Stage 56 deterministic guards: UCP RFC 9728/RFC 8414 multi-entry identity-linking discovery (#891),
fulfillment `options[].totals` rendering contract (#573) & checkout status lifecycle (#672),
UCP `com.mercadopago.payment.render_artifact` Pix out-of-band Action (#635) &
`com.razorpay.magic_checkout` hosted checkout instrument/credential (#316),
ACP Delegate Authentication `Signature` requirement (#287), `CheckoutSessionCreateRequest`
schema conformance (#289) & unwrapped `delegate_payment` `Error` envelope (#266/#243),
and Sierra tau-bench 2.0 `loan_servicing` (EN/FR Boréal Finance) policy (#638) +
`banking_knowledge` `canonicalize_time_verified` timestamp normalization (#634).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Any
from urllib.parse import urlparse


_TIMESTAMP_PATTERN = re.compile(
    r"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})(?::(\d{2}))?"
    r"\s*(Z|[+-]\d{2}:?\d{2}|[A-Za-z]{2,5})?"
)
_EQUIVALENT_EST_TIMEZONES = {None, "EST", "ET", "-05:00", "-0500"}
_CANONICAL_BANKING_NOW = datetime(2025, 11, 14, 3, 40, 0)
_CANONICAL_BANKING_NOW_STR = "2025-11-14 03:40:00 EST"

_VALID_CHECKOUT_TRANSITIONS: dict[str, set[str]] = {
    "incomplete": {"incomplete", "ready_for_complete", "requires_escalation", "canceled"},
    "ready_for_complete": {
        "ready_for_complete",
        "incomplete",
        "requires_escalation",
        "complete_in_progress",
        "completed",
        "canceled",
    },
    "requires_escalation": {
        "requires_escalation",
        "incomplete",
        "ready_for_complete",
        "complete_in_progress",
        "completed",
        "canceled",
    },
    "complete_in_progress": {"complete_in_progress", "completed", "requires_escalation", "incomplete", "canceled"},
    "completed": {"completed"},
    "canceled": {"canceled"},
}


@dataclass(frozen=True)
class UcpRfc9728CheckoutLifecycleGuardResult:
    allowed: bool
    reason_code: str
    selected_issuer: str | None
    discarded_issuers: tuple[str, ...]
    violations: tuple[str, ...]


def verify_ucp_rfc9728_identity_linking_and_checkout_lifecycle(
    *,
    authorization_servers: tuple[dict[str, Any], ...],
    platform_normalized_issuer_before_compare: bool = False,
    discarded_entries_logged: bool = True,
    fulfillment_option: dict[str, Any] | None = None,
    checkout_prev_status: str = "ready_for_complete",
    checkout_next_status: str = "requires_escalation",
) -> UcpRfc9728CheckoutLifecycleGuardResult:
    """Verify UCP PR #891 RFC 9728/8414 discovery, PR #573 fulfillment totals, and PR #672 checkout lifecycle."""
    violations: list[str] = []
    discarded: list[str] = []
    selected_issuer: str | None = None

    if platform_normalized_issuer_before_compare:
        violations.append("UCP_RFC8414_ISSUER_NORMALIZATION_FORBIDDEN")

    for entry in authorization_servers:
        candidate = str(entry.get("candidate_issuer") or "")
        rfc8414_status = int(entry.get("rfc8414_status", 200))
        attempted_oidc_fallback = bool(entry.get("attempted_oidc_fallback", False))
        oidc_status = int(entry.get("oidc_status", 200))
        discovered_issuer = str(entry.get("discovered_issuer") or "")
        platform_registered = bool(entry.get("platform_registered", True))
        well_known_appended_to_path = bool(entry.get("well_known_appended_to_path", False))

        if well_known_appended_to_path:
            violations.append(f"UCP_RFC8414_WELL_KNOWN_APPENDED_INSTEAD_OF_INSERTED:{candidate}")
            discarded.append(candidate)
            continue

        if rfc8414_status != 200:
            if rfc8414_status != 404 and attempted_oidc_fallback:
                violations.append(f"UCP_RFC8414_NON_404_FALLBACK_FORBIDDEN:{candidate}:{rfc8414_status}")
                discarded.append(candidate)
                continue
            if rfc8414_status != 404 or not attempted_oidc_fallback or oidc_status != 200:
                discarded.append(candidate)
                continue

        # Step 3: byte-for-byte exact match without trailing-slash normalization
        if discovered_issuer != candidate:
            discarded.append(candidate)
            continue

        if not platform_registered:
            discarded.append(candidate)
            continue

        if selected_issuer is None:
            selected_issuer = candidate

    if discarded and not discarded_entries_logged:
        violations.append("UCP_DISCARDED_AS_ENTRIES_NOT_SURFACED")

    if selected_issuer is None:
        violations.append("UCP_DISCOVERY_NO_VALID_AS_REMAINING")

    if fulfillment_option is not None:
        if "total" in fulfillment_option:
            violations.append("UCP_FULFILLMENT_SCALAR_TOTAL_FIELD_FORBIDDEN")
        totals = fulfillment_option.get("totals")
        if not isinstance(totals, (list, tuple)) or len(totals) == 0:
            violations.append("UCP_FULFILLMENT_TOTALS_ARRAY_REQUIRED")
        else:
            for item in totals:
                if not isinstance(item, dict) or item.get("amount") is None:
                    violations.append("UCP_FULFILLMENT_NULL_AMOUNT_FORBIDDEN")
        title = str(fulfillment_option.get("title") or "").strip()
        desc = str(fulfillment_option.get("description") or "").strip()
        if desc and title and title.lower() in desc.lower():
            violations.append("UCP_FULFILLMENT_DESCRIPTION_REPEATS_TITLE_OR_TOTALS")

    allowed_next = _VALID_CHECKOUT_TRANSITIONS.get(checkout_prev_status, set())
    if checkout_next_status not in allowed_next:
        violations.append(f"UCP_CHECKOUT_INVALID_STATUS_TRANSITION:{checkout_prev_status}->{checkout_next_status}")

    allowed = len(violations) == 0
    return UcpRfc9728CheckoutLifecycleGuardResult(
        allowed=allowed,
        reason_code="UCP_RFC9728_AND_CHECKOUT_LIFECYCLE_OK" if allowed else violations[0],
        selected_issuer=selected_issuer,
        discarded_issuers=tuple(discarded),
        violations=tuple(violations),
    )


@dataclass(frozen=True)
class UcpRenderArtifactHostedCheckoutGuardResult:
    allowed: bool
    reason_code: str
    render_artifact_valid: bool
    hosted_checkout_valid: bool
    violations: tuple[str, ...]


def verify_ucp_render_artifact_and_hosted_checkout_guard(
    *,
    render_action_instance: dict[str, Any],
    checkout_expires_at: str,
    checkout_has_continue_url: bool = False,
    handler_allowed_origins: tuple[str, ...] = ("https://pay.mercadopago.com",),
    platform_auto_submitted_buyer_data_to_instructions: bool = False,
    hosted_instrument: dict[str, Any] | None = None,
    checkout_continue_url: str = "https://api.razorpay.com/v1/magic_checkout/chk_01",
    platform_attempted_credential_acquisition: bool = False,
    buyer_redirected_to_cancel_url: bool = False,
    platform_polled_checkout_after_cancel: bool = True,
) -> UcpRenderArtifactHostedCheckoutGuardResult:
    """Verify UCP PR #635 Mercado Pago Pix render_artifact and PR #316 Razorpay hosted_checkout."""
    violations: list[str] = []

    if "required" in render_action_instance:
        violations.append("UCP_RENDER_ARTIFACT_INSTANCE_REQUIRED_FIELD_FORBIDDEN")

    if checkout_has_continue_url:
        violations.append("UCP_RENDER_ARTIFACT_FORBIDS_CONTINUE_URL_REDIRECT")

    cfg = render_action_instance.get("config") or {}
    if not cfg.get("type") or not cfg.get("expires_at"):
        violations.append("UCP_RENDER_ARTIFACT_MISSING_TYPE_OR_EXPIRES_AT")
    else:
        if str(cfg["expires_at"]) > str(checkout_expires_at):
            violations.append("UCP_RENDER_ARTIFACT_EXPIRY_EXCEEDS_CHECKOUT")

    has_code = bool(isinstance(cfg.get("code"), str) and cfg.get("code").strip())
    has_image = bool(isinstance(cfg.get("image"), str) and cfg.get("image").strip())
    has_instr = bool(isinstance(cfg.get("instructions_url"), str) and cfg.get("instructions_url").strip())
    if not (has_code or has_image or has_instr):
        violations.append("UCP_RENDER_ARTIFACT_MISSING_DISPLAY_PAYLOAD")

    if has_image:
        img_uri = str(cfg["image"])
        if not (img_uri.startswith("https://") or img_uri.startswith("data:image/")):
            violations.append("UCP_RENDER_ARTIFACT_UNSAFE_IMAGE_URI")

    if has_instr:
        instr_url = str(cfg["instructions_url"])
        parsed = urlparse(instr_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if parsed.scheme != "https" or origin not in handler_allowed_origins:
            violations.append("UCP_RENDER_ARTIFACT_UNTRUSTED_INSTRUCTIONS_ORIGIN")
        if platform_auto_submitted_buyer_data_to_instructions:
            violations.append("UCP_RENDER_ARTIFACT_AUTO_SUBMIT_BUYER_DATA_FORBIDDEN")

    for forbidden_secret in ("pan", "card_number", "otp", "cvv", "cryptogram"):
        if forbidden_secret in cfg:
            violations.append(f"UCP_RENDER_ARTIFACT_SECRET_LEAK_BLOCKED:{forbidden_secret}")

    render_ok = len(violations) == 0

    if hosted_instrument is not None:
        if hosted_instrument.get("type") != "hosted_checkout":
            violations.append("UCP_HOSTED_CHECKOUT_INVALID_INSTRUMENT_TYPE")
        if platform_attempted_credential_acquisition:
            violations.append("UCP_HOSTED_CHECKOUT_CREDENTIAL_ACQUISITION_FORBIDDEN")

        cred = hosted_instrument.get("credential") or {}
        return_url = str(cred.get("return_url") or "")
        cancel_url = cred.get("cancel_url")
        if cred.get("type") != "hosted_checkout" or not return_url.startswith("https://"):
            violations.append("UCP_HOSTED_CHECKOUT_INVALID_RETURN_URL")
        elif return_url == checkout_continue_url:
            violations.append("UCP_HOSTED_CHECKOUT_RETURN_URL_EQUALS_CONTINUE_URL")

        if cancel_url is not None and not str(cancel_url).startswith("https://"):
            violations.append("UCP_HOSTED_CHECKOUT_INVALID_CANCEL_URL")

        for secret_field in ("token", "number", "pan", "cvv", "cryptogram"):
            if secret_field in cred:
                violations.append(f"UCP_HOSTED_CHECKOUT_SENSITIVE_CREDENTIAL_FORBIDDEN:{secret_field}")

        if buyer_redirected_to_cancel_url and not platform_polled_checkout_after_cancel:
            violations.append("UCP_HOSTED_CHECKOUT_CANCEL_WITHOUT_AUTHORITATIVE_POLL")

    allowed = len(violations) == 0
    return UcpRenderArtifactHostedCheckoutGuardResult(
        allowed=allowed,
        reason_code="UCP_RENDER_ARTIFACT_AND_HOSTED_CHECKOUT_OK" if allowed else violations[0],
        render_artifact_valid=render_ok,
        hosted_checkout_valid=allowed,
        violations=tuple(violations),
    )


@dataclass(frozen=True)
class AcpDelegateAuthAndErrorEnvelopeGuardResult:
    allowed: bool
    reason_code: str
    signature_verified: bool
    create_request_valid: bool
    error_envelope_unwrapped: bool
    violations: tuple[str, ...]


def verify_acp_delegate_auth_signature_and_error_envelope(
    *,
    delegate_auth_openapi_signature_required: bool = True,
    delegate_auth_request_signature: str | None = "ZXltZX...",
    checkout_create_request: dict[str, Any],
    delegate_payment_error_payload: dict[str, Any],
) -> AcpDelegateAuthAndErrorEnvelopeGuardResult:
    """Verify ACP PR #287 Delegate Auth Signature, PR #289 CheckoutCreateRequest, and PR #266/#243 Error envelope."""
    violations: list[str] = []

    if not delegate_auth_openapi_signature_required or not (
        isinstance(delegate_auth_request_signature, str) and delegate_auth_request_signature.strip()
    ):
        violations.append("ACP_DELEGATE_AUTH_SIGNATURE_MISSING")
    sig_ok = len(violations) == 0

    if "items" in checkout_create_request:
        violations.append("ACP_CHECKOUT_CREATE_LEGACY_ITEMS_FIELD_REJECTED")

    for req_field in ("line_items", "currency", "capabilities"):
        if req_field not in checkout_create_request:
            violations.append(f"ACP_CHECKOUT_CREATE_MISSING_REQUIRED_FIELD:{req_field}")

    line_items = checkout_create_request.get("line_items")
    if isinstance(line_items, (list, tuple)):
        for item in line_items:
            if isinstance(item, dict) and "product_id" in item:
                violations.append("ACP_CHECKOUT_CREATE_ITEM_PRODUCT_ID_FORBIDDEN")

    create_ok = len([v for v in violations if v.startswith("ACP_CHECKOUT_CREATE_")]) == 0

    if "error" in delegate_payment_error_payload:
        violations.append("ACP_DELEGATE_PAYMENT_WRAPPED_ERROR_ENVELOPE_REJECTED")
    for req_err in ("type", "code", "message"):
        if req_err not in delegate_payment_error_payload:
            violations.append(f"ACP_DELEGATE_PAYMENT_ERROR_MISSING_TOP_LEVEL_FIELD:{req_err}")

    err_ok = len([v for v in violations if v.startswith("ACP_DELEGATE_PAYMENT_")]) == 0
    allowed = len(violations) == 0
    return AcpDelegateAuthAndErrorEnvelopeGuardResult(
        allowed=allowed,
        reason_code="ACP_DELEGATE_AUTH_AND_ERROR_ENVELOPE_OK" if allowed else violations[0],
        signature_verified=sig_ok,
        create_request_valid=create_ok,
        error_envelope_unwrapped=err_ok,
        violations=tuple(violations),
    )


def canonicalize_tau2_banking_time_verified(time_verified: str) -> str:
    """Canonicalize equivalent timestamps per Sierra tau2-bench PR #634."""
    match = _TIMESTAMP_PATTERN.search(time_verified)
    if match is None:
        return time_verified.strip()
    day, hour_minute, seconds, timezone = match.groups()
    timezone_upper = timezone.upper() if timezone else None
    try:
        parsed = datetime.strptime(f"{day} {hour_minute}:{seconds or '00'}", "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return time_verified.strip()
    if parsed == _CANONICAL_BANKING_NOW and timezone_upper in _EQUIVALENT_EST_TIMEZONES:
        return _CANONICAL_BANKING_NOW_STR
    return time_verified.strip()


@dataclass(frozen=True)
class Tau2LoanServicingAndTimeGuardResult:
    allowed: bool
    reason_code: str
    canonical_time_verified: str
    violations: tuple[str, ...]


def verify_tau2_loan_servicing_and_time_canonicalization(
    *,
    caller_role: str = "borrower",
    verified_fields: tuple[str, ...] = ("full_name", "date_of_birth", "postal_code"),
    failed_verification_attempts: int = 0,
    transferred_reason: str | None = None,
    requested_action_kind: str = "write_payment",
    explicit_yes_confirmed_before_write: bool = True,
    tool_calls_in_turn: int = 1,
    messaged_borrower_in_same_turn_as_tool: bool = False,
    waiver_requested_with_payment: bool = False,
    waiver_processed_before_payment: bool = True,
    waiver_fee_amount_cad: float = 35.0,
    waiver_loan_status: str = "past_due_30",
    prior_waiver_within_12_months: bool = False,
    email_changed_in_conversation: bool = False,
    document_sent_in_conversation: bool = False,
    banking_time_verified_input: str = "2025-11-14T03:40:00-05:00",
) -> Tau2LoanServicingAndTimeGuardResult:
    """Verify Sierra tau2-bench PR #638 loan_servicing (EN/FR) policy and PR #634 time_verified canonicalization."""
    violations: list[str] = []

    if failed_verification_attempts >= 2 and transferred_reason != "failed_verification":
        violations.append("TAU2_LOAN_DOUBLE_VERIFICATION_FAILURE_MUST_TRANSFER")

    required_verification = {"full_name", "date_of_birth", "postal_code"}
    if not required_verification.issubset(set(verified_fields)):
        violations.append("TAU2_LOAN_CALLER_NOT_VERIFIED")

    if caller_role == "authorized_third_party" and requested_action_kind != "read_general_info":
        violations.append("TAU2_LOAN_THIRD_PARTY_WRITE_OR_DOC_FORBIDDEN")
    elif caller_role not in {"borrower", "co_borrower", "authorized_third_party"}:
        violations.append("TAU2_LOAN_UNAUTHORIZED_CALLER_ROLE")

    if requested_action_kind.startswith("write_") and not explicit_yes_confirmed_before_write:
        violations.append("TAU2_LOAN_WRITE_WITHOUT_CONFIRMATION")

    if tool_calls_in_turn > 1 or messaged_borrower_in_same_turn_as_tool:
        violations.append("TAU2_LOAN_TOOL_AND_MESSAGE_SAME_TURN_FORBIDDEN")

    if waiver_requested_with_payment:
        if not waiver_processed_before_payment:
            violations.append("TAU2_LOAN_PAYMENT_BEFORE_WAIVER_ORDER_VIOLATION")
        if (
            waiver_fee_amount_cad > 50.0
            or prior_waiver_within_12_months
            or waiver_loan_status not in {"current", "past_due_30"}
        ):
            violations.append("TAU2_LOAN_INELIGIBLE_FEE_WAIVER")

    if email_changed_in_conversation and document_sent_in_conversation:
        violations.append("TAU2_LOAN_DOC_AFTER_EMAIL_CHANGE_BLOCKED")

    canonical_time = canonicalize_tau2_banking_time_verified(banking_time_verified_input)
    if canonical_time != _CANONICAL_BANKING_NOW_STR:
        violations.append(f"TAU2_TIME_VERIFIED_FABRICATED_OR_WRONG_TZ:{canonical_time}")

    allowed = len(violations) == 0
    return Tau2LoanServicingAndTimeGuardResult(
        allowed=allowed,
        reason_code="TAU2_LOAN_SERVICING_AND_TIME_CANONICAL_OK" if allowed else violations[0],
        canonical_time_verified=canonical_time,
        violations=tuple(violations),
    )
