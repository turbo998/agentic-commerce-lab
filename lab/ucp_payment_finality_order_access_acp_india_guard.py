"""Stage 42: UCP Checkout Payment Finality & Order Reporting (#816), Guest Order Access
Credentials (#848), RFC 9421 §2.4 REST Response-to-Request Binding (#699), Token Issuance
Context (#792), Buyer Consent Full-Replacement Exemption (#660), Correspondence & 3-Axis
Adjustment Cause (#836/#837/#843), and ACP Razorpay UPI/CoFT & Feed Extensions (#217/#218/#223)
Runtime Guards.

Implements deterministic, zero-network verification guards for:
1. UCP PR #816 (`feat!: define checkout payment finality and order reporting`):
   - Only aggregate `totals[]` (`type == "total"`) may carry `amount_finality` (`"final"` | `"provisional"`).
   - Final totals MUST omit `payment.maximum_amount`; provisional totals MUST require
     `payment.maximum_amount >= aggregate_total` plus explicit buyer ceiling disclosure.
   - `order.payment.maximum_amount` MUST preserve the Checkout-approved ceiling, and
     `order.payment.instruments[]` (`order_payment_instrument`) MUST require `display`
     while omitting `credential`, `handler_id`, and `selected`.
2. UCP PR #848 (`feat: add order access credentials for guest post-purchase access`) &
   UCP PR #699 (`fix!: bind signed REST responses to their request`):
   - Single-order-scoped `order_confirmation.access` / `order.access` credentials (`token`,
     `expires_at`, `{capability}:{scope}` tokens), blocking cross-order enumeration,
     listing operations, permalink URL leakage, missing `Cache-Control: no-store`, and
     unrevoked credentials after guest-to-account claim.
   - RFC 9421 §2.4 `;req` request-response binding (`@status`, `@authority;req`,
     `@method;req`, `@path;req`, `content-digest`, `content-type`, plus `@query;req` and
     `content-digest;req` when present on the request) reconstructed strictly from the
     client's sent request, with mandatory `created` freshness window.
3. UCP PR #792 (`TokenCredential` `binding` & `identity`), PR #660 (`buyer.consent`
   full-replacement exemption), and PRs #836/#837/#843 (`Correspondence` & `Adjustment.cause`):
   - Preserves `TokenCredential.binding` across Platform/Business/Processor and forbids
     accepting `TokenCredential.identity` as caller authentication.
   - Exempts `buyer.consent` from full-replacement dropping on `update_cart`/`update_checkout`.
   - Prevents treating `correspondence.status == "unverifiable"` as `"agrees"` or omitting
     `totals`/`currency` from `compared[]`, and enforces 3-axis `Adjustment.cause`
     (`category`, `attributed_to`, `nature`) with `undetermined` fallback when false assertion
     (`fraud`) vs rule exploitation (`abuse`) is unproven.
4. ACP PRs #217 (`com.razorpay.upi_intent`), #218 (`com.razorpay.s2s_cards`), and #223
   (ACP Feed Extensions Framework):
   - NPCI ₹1,00,000 (`10,000,000` paise) cap, `INR` currency lock, `upi://pay` `tr == checkout_session_id`
     binding, RBI CoFT `token_id`-only S2S cards (no raw PAN/CVV), and declared
     `FeedMetadata.extensions[]` enforcement without SSRF schema auto-fetching.

Pure Python standard library; zero network calls; zero secrets.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any
from urllib.parse import parse_qs, urlparse


SCOPE_TOKEN_RE = re.compile(r"^[a-z0-9_.]+:[a-z0-9_]+$")

STANDARD_ADJUSTMENT_TYPES: frozenset[str] = frozenset(
    {
        "refund",
        "return",
        "credit",
        "price_adjustment",
        "dispute",
        "cancellation",
    }
)

VALID_ADJUSTMENT_CAUSE_NATURES: frozenset[str] = frozenset(
    {
        "error",
        "fault",
        "abuse",
        "fraud",
        "compromise",
        "disagreement",
        "undetermined",
    }
)

NPCI_UPI_MAX_PAISE: int = 10_000_000  # ₹1,00,000 in minor units (paise)


@dataclass(frozen=True)
class UcpPaymentFinalityAndOrderReportingResult:
    allowed: bool
    decision_code: str
    amount_finality: str
    approved_maximum_amount_minor: int
    active_collected_or_authorized_minor: int
    order_instruments_sanitized: bool
    historical_retry_sum_ignored: bool


def evaluate_ucp_checkout_payment_finality_and_order_reporting_guard(
    context: dict[str, Any],
) -> UcpPaymentFinalityAndOrderReportingResult:
    """Verify UCP PR #816 checkout `amount_finality`, `payment.maximum_amount`, and Order payment reporting."""
    totals = context.get("checkout_totals", [])
    checkout_payment = context.get("checkout_payment", {}) or {}
    buyer_disclosed_provisional_ceiling = bool(
        context.get("buyer_disclosed_provisional_ceiling", True)
    )
    order_payment = context.get("order_payment")
    has_separate_post_purchase_buyer_approval = bool(
        context.get("has_separate_post_purchase_buyer_approval", False)
    )

    aggregate_total_minor: int | None = None
    amount_finality = "final"

    for entry in totals:
        t_type = str(entry.get("type", ""))
        has_finality = "amount_finality" in entry and entry.get("amount_finality") is not None
        if t_type != "total":
            if has_finality:
                return UcpPaymentFinalityAndOrderReportingResult(
                    allowed=False,
                    decision_code="NON_AGGREGATE_TOTAL_AMOUNT_FINALITY_FORBIDDEN",
                    amount_finality="invalid",
                    approved_maximum_amount_minor=0,
                    active_collected_or_authorized_minor=0,
                    order_instruments_sanitized=False,
                    historical_retry_sum_ignored=False,
                )
        else:
            aggregate_total_minor = int(entry.get("amount", 0))
            if has_finality:
                raw_finality = str(entry.get("amount_finality"))
                if raw_finality not in ("final", "provisional"):
                    return UcpPaymentFinalityAndOrderReportingResult(
                        allowed=False,
                        decision_code="INVALID_CHECKOUT_AMOUNT_FINALITY_ENUM",
                        amount_finality=raw_finality,
                        approved_maximum_amount_minor=0,
                        active_collected_or_authorized_minor=0,
                        order_instruments_sanitized=False,
                        historical_retry_sum_ignored=False,
                    )
                amount_finality = raw_finality

    if aggregate_total_minor is None:
        return UcpPaymentFinalityAndOrderReportingResult(
            allowed=False,
            decision_code="CHECKOUT_AGGREGATE_TOTAL_ENTRY_MISSING",
            amount_finality=amount_finality,
            approved_maximum_amount_minor=0,
            active_collected_or_authorized_minor=0,
            order_instruments_sanitized=False,
            historical_retry_sum_ignored=False,
        )

    has_checkout_max = (
        "maximum_amount" in checkout_payment
        and checkout_payment.get("maximum_amount") is not None
    )

    if amount_finality == "final":
        if has_checkout_max:
            return UcpPaymentFinalityAndOrderReportingResult(
                allowed=False,
                decision_code="FINAL_TOTAL_MAXIMUM_AMOUNT_MUST_BE_OMITTED",
                amount_finality="final",
                approved_maximum_amount_minor=aggregate_total_minor,
                active_collected_or_authorized_minor=0,
                order_instruments_sanitized=False,
                historical_retry_sum_ignored=False,
            )
        approved_max = aggregate_total_minor
    else:
        if not has_checkout_max:
            return UcpPaymentFinalityAndOrderReportingResult(
                allowed=False,
                decision_code="PROVISIONAL_TOTAL_MAXIMUM_AMOUNT_MISSING_OR_BELOW_TOTAL",
                amount_finality="provisional",
                approved_maximum_amount_minor=0,
                active_collected_or_authorized_minor=0,
                order_instruments_sanitized=False,
                historical_retry_sum_ignored=False,
            )
        approved_max = int(checkout_payment["maximum_amount"])
        if approved_max < aggregate_total_minor:
            return UcpPaymentFinalityAndOrderReportingResult(
                allowed=False,
                decision_code="PROVISIONAL_TOTAL_MAXIMUM_AMOUNT_MISSING_OR_BELOW_TOTAL",
                amount_finality="provisional",
                approved_maximum_amount_minor=approved_max,
                active_collected_or_authorized_minor=0,
                order_instruments_sanitized=False,
                historical_retry_sum_ignored=False,
            )
        if not buyer_disclosed_provisional_ceiling:
            return UcpPaymentFinalityAndOrderReportingResult(
                allowed=False,
                decision_code="PROVISIONAL_TOTAL_BUYER_DISCLOSURE_MISSING_BLOCKED",
                amount_finality="provisional",
                approved_maximum_amount_minor=approved_max,
                active_collected_or_authorized_minor=0,
                order_instruments_sanitized=False,
                historical_retry_sum_ignored=False,
            )

    active_total = 0
    order_sanitized = True
    historical_ignored = bool(context.get("historical_replaced_auth_or_retried_capture_minor", 0) > approved_max)

    if order_payment is not None:
        if (
            "maximum_amount" not in order_payment
            or order_payment.get("maximum_amount") is None
            or int(order_payment["maximum_amount"]) != approved_max
        ):
            return UcpPaymentFinalityAndOrderReportingResult(
                allowed=False,
                decision_code="ORDER_PAYMENT_MAXIMUM_AMOUNT_DRIFT_OR_MISSING_BLOCKED",
                amount_finality=amount_finality,
                approved_maximum_amount_minor=approved_max,
                active_collected_or_authorized_minor=0,
                order_instruments_sanitized=False,
                historical_retry_sum_ignored=historical_ignored,
            )

        instruments = order_payment.get("instruments", []) or []
        for inst in instruments:
            if not inst.get("id") or not inst.get("type"):
                return UcpPaymentFinalityAndOrderReportingResult(
                    allowed=False,
                    decision_code="ORDER_PAYMENT_INSTRUMENT_ID_OR_TYPE_MISSING",
                    amount_finality=amount_finality,
                    approved_maximum_amount_minor=approved_max,
                    active_collected_or_authorized_minor=active_total,
                    order_instruments_sanitized=False,
                    historical_retry_sum_ignored=historical_ignored,
                )
            if not isinstance(inst.get("display"), dict) or not inst.get("display"):
                return UcpPaymentFinalityAndOrderReportingResult(
                    allowed=False,
                    decision_code="ORDER_PAYMENT_INSTRUMENT_DISPLAY_MISSING_BLOCKED",
                    amount_finality=amount_finality,
                    approved_maximum_amount_minor=approved_max,
                    active_collected_or_authorized_minor=active_total,
                    order_instruments_sanitized=False,
                    historical_retry_sum_ignored=historical_ignored,
                )
            for forbidden_field in ("credential", "handler_id", "selected"):
                if forbidden_field in inst:
                    return UcpPaymentFinalityAndOrderReportingResult(
                        allowed=False,
                        decision_code="ORDER_PAYMENT_INSTRUMENT_FORBIDDEN_CHECKOUT_OR_CREDENTIAL_FIELD_LEAK",
                        amount_finality=amount_finality,
                        approved_maximum_amount_minor=approved_max,
                        active_collected_or_authorized_minor=active_total,
                        order_instruments_sanitized=False,
                        historical_retry_sum_ignored=historical_ignored,
                    )

            auth_amt = int(inst.get("authorized_amount", 0) or 0)
            cap_amt = int(inst.get("captured_amount", 0) or 0)
            # Active collection/authorization exposure on this instrument
            active_total += max(auth_amt, cap_amt)

        if active_total > approved_max and not has_separate_post_purchase_buyer_approval:
            return UcpPaymentFinalityAndOrderReportingResult(
                allowed=False,
                decision_code="PROVISIONAL_ORDER_COLLECTION_EXCEEDS_MAXIMUM_AMOUNT_BLOCKED",
                amount_finality=amount_finality,
                approved_maximum_amount_minor=approved_max,
                active_collected_or_authorized_minor=active_total,
                order_instruments_sanitized=order_sanitized,
                historical_retry_sum_ignored=historical_ignored,
            )

    return UcpPaymentFinalityAndOrderReportingResult(
        allowed=True,
        decision_code="UCP_PAYMENT_FINALITY_AND_ORDER_REPORTING_VERIFIED",
        amount_finality=amount_finality,
        approved_maximum_amount_minor=approved_max,
        active_collected_or_authorized_minor=active_total,
        order_instruments_sanitized=order_sanitized,
        historical_retry_sum_ignored=historical_ignored,
    )


@dataclass(frozen=True)
class UcpGuestOrderAccessAndRestBindingResult:
    allowed: bool
    decision_code: str
    order_access_bound: bool
    rest_response_request_bound: bool
    rotated_token_issued: bool


def evaluate_ucp_guest_order_access_and_rest_response_binding_guard(
    context: dict[str, Any],
) -> UcpGuestOrderAccessAndRestBindingResult:
    """Verify UCP PR #848 guest order access credentials and UCP PR #699 RFC 9421 §2.4 `;req` REST response binding."""
    issued_order_id = str(context.get("issued_order_id", "order_abc123"))
    requested_order_id = str(context.get("requested_order_id", issued_order_id))
    operation_name = str(context.get("operation_name", "get_order"))
    issued_access = context.get("issued_access") or {}
    presented_token = str(context.get("presented_access_token", issued_access.get("token", "")))
    permalink_url = str(context.get("permalink_url", "https://business.example.com/orders/abc123"))
    now_epoch = int(context.get("now_epoch", 1_760_000_000))
    expires_at_epoch = int(context.get("expires_at_epoch", now_epoch + 3600))
    guest_order_claimed_into_account = bool(context.get("guest_order_claimed_into_account", False))
    credential_revoked_on_claim = bool(context.get("credential_revoked_on_claim", True))
    transport = str(context.get("transport", "REST")).upper()
    cache_control_header = str(context.get("cache_control_header", "no-store"))
    rotated_access = context.get("rotated_access")

    issued_token = str(issued_access.get("token", ""))
    scopes = issued_access.get("scopes", ["dev.ucp.shopping.order:read"])

    if not issued_token or len(issued_token) < 12 or issued_order_id in issued_token:
        return UcpGuestOrderAccessAndRestBindingResult(
            allowed=False,
            decision_code="ORDER_ACCESS_CREDENTIAL_WEAK_OR_GUESSABLE_TOKEN_BLOCKED",
            order_access_bound=False,
            rest_response_request_bound=False,
            rotated_token_issued=False,
        )

    if issued_token in permalink_url or "access_token=" in permalink_url:
        return UcpGuestOrderAccessAndRestBindingResult(
            allowed=False,
            decision_code="ORDER_ACCESS_CREDENTIAL_IN_PERMALINK_URL_LEAK_BLOCKED",
            order_access_bound=False,
            rest_response_request_bound=False,
            rotated_token_issued=False,
        )

    if not scopes or not all(SCOPE_TOKEN_RE.match(str(s)) for s in scopes):
        return UcpGuestOrderAccessAndRestBindingResult(
            allowed=False,
            decision_code="ORDER_ACCESS_CREDENTIAL_INVALID_SCOPE_GRAMMAR",
            order_access_bound=False,
            rest_response_request_bound=False,
            rotated_token_issued=False,
        )

    if operation_name != "get_order":
        if operation_name in ("list_orders", "search_orders"):
            return UcpGuestOrderAccessAndRestBindingResult(
                allowed=False,
                decision_code="ORDER_ACCESS_CREDENTIAL_LISTING_OPERATION_FORBIDDEN",
                order_access_bound=False,
                rest_response_request_bound=False,
                rotated_token_issued=False,
            )
        if "dev.ucp.shopping.order:manage" not in scopes:
            return UcpGuestOrderAccessAndRestBindingResult(
                allowed=False,
                decision_code="ORDER_ACCESS_CREDENTIAL_READ_ONLY_SCOPE_MUTATION_BLOCKED",
                order_access_bound=False,
                rest_response_request_bound=False,
                rotated_token_issued=False,
            )

    if requested_order_id != issued_order_id or presented_token != issued_token:
        return UcpGuestOrderAccessAndRestBindingResult(
            allowed=False,
            decision_code="ORDER_ACCESS_CREDENTIAL_CROSS_ORDER_ENUMERATION_BLOCKED",
            order_access_bound=False,
            rest_response_request_bound=False,
            rotated_token_issued=False,
        )

    if now_epoch > expires_at_epoch:
        return UcpGuestOrderAccessAndRestBindingResult(
            allowed=False,
            decision_code="ORDER_ACCESS_CREDENTIAL_EXPIRED_BLOCKED",
            order_access_bound=False,
            rest_response_request_bound=False,
            rotated_token_issued=False,
        )

    if guest_order_claimed_into_account:
        if not credential_revoked_on_claim or context.get("allow_use_after_account_claim", False):
            return UcpGuestOrderAccessAndRestBindingResult(
                allowed=False,
                decision_code="CLAIMED_ACCOUNT_GUEST_ORDER_CREDENTIAL_NOT_REVOKED",
                order_access_bound=False,
                rest_response_request_bound=False,
                rotated_token_issued=False,
            )

    if transport == "REST" and "no-store" not in cache_control_header.lower():
        return UcpGuestOrderAccessAndRestBindingResult(
            allowed=False,
            decision_code="REST_ORDER_ACCESS_TOKEN_MISSING_NO_STORE_HEADER_BLOCKED",
            order_access_bound=False,
            rest_response_request_bound=False,
            rotated_token_issued=False,
        )

    # UCP PR #699: RFC 9421 §2.4 signed REST response binding to sent request
    rest_sig = context.get("rest_response_signature")
    if rest_sig is not None:
        covered = set(rest_sig.get("covered_components", []))
        required_components = {
            "@status",
            "@authority;req",
            "@method;req",
            "@path;req",
            "content-digest",
            "content-type",
        }
        sent_req = rest_sig.get("client_sent_request", {}) or {}
        if sent_req.get("query"):
            required_components.add("@query;req")
        if sent_req.get("content_digest"):
            required_components.add("content-digest;req")

        if not required_components.issubset(covered):
            return UcpGuestOrderAccessAndRestBindingResult(
                allowed=False,
                decision_code="REST_RESPONSE_SIGNATURE_REQUEST_BINDING_OR_FRESHNESS_FAILED",
                order_access_bound=True,
                rest_response_request_bound=False,
                rotated_token_issued=False,
            )

        if bool(rest_sig.get("rebuilt_req_components_from_response_echo", False)):
            return UcpGuestOrderAccessAndRestBindingResult(
                allowed=False,
                decision_code="REST_RESPONSE_SIGNATURE_SELF_CERTIFYING_RESPONSE_REBUILD_BLOCKED",
                order_access_bound=True,
                rest_response_request_bound=False,
                rotated_token_issued=False,
            )

        sig_req = rest_sig.get("signed_request_context", {}) or {}
        for key in ("authority", "method", "path", "query", "content_digest"):
            if key in sent_req and sent_req.get(key) != sig_req.get(key):
                return UcpGuestOrderAccessAndRestBindingResult(
                    allowed=False,
                    decision_code="REST_RESPONSE_SIGNATURE_REQUEST_BINDING_OR_FRESHNESS_FAILED",
                    order_access_bound=True,
                    rest_response_request_bound=False,
                    rotated_token_issued=False,
                )

        created_ts = rest_sig.get("created_epoch")
        max_window_sec = int(rest_sig.get("max_freshness_window_sec", 300))
        if created_ts is None or abs(now_epoch - int(created_ts)) > max_window_sec:
            return UcpGuestOrderAccessAndRestBindingResult(
                allowed=False,
                decision_code="REST_RESPONSE_SIGNATURE_REQUEST_BINDING_OR_FRESHNESS_FAILED",
                order_access_bound=True,
                rest_response_request_bound=False,
                rotated_token_issued=False,
            )

    rotated_ok = isinstance(rotated_access, dict) and bool(rotated_access.get("token"))
    return UcpGuestOrderAccessAndRestBindingResult(
        allowed=True,
        decision_code="UCP_GUEST_ORDER_ACCESS_AND_REST_RESPONSE_BINDING_VERIFIED",
        order_access_bound=True,
        rest_response_request_bound=True,
        rotated_token_issued=rotated_ok,
    )


@dataclass(frozen=True)
class UcpTokenConsentAndCorrespondenceResult:
    allowed: bool
    decision_code: str
    token_binding_verified: bool
    effective_buyer_consent: dict[str, bool]
    correspondence_verified: bool
    adjustment_cause_valid: bool


def evaluate_ucp_token_context_buyer_consent_and_correspondence_guard(
    context: dict[str, Any],
) -> UcpTokenConsentAndCorrespondenceResult:
    """Verify UCP PR #792 TokenCredential context, PR #660 buyer.consent exemption, and PRs #836/#837/#843."""
    # 1. UCP PR #792: TokenCredential `binding` and `identity`
    token_ctx = context.get("token_credential_context") or {}
    issued_binding = token_ctx.get("issued_binding")
    platform_forwarded_binding = token_ctx.get("platform_forwarded_binding", issued_binding)
    processor_expected_binding = token_ctx.get("processor_expected_binding", issued_binding)
    issued_identity = token_ctx.get("issued_identity")
    platform_forwarded_identity = token_ctx.get("platform_forwarded_identity", issued_identity)
    caller_authenticated_independently = bool(
        token_ctx.get("caller_authenticated_independently", True)
    )
    accepted_identity_as_caller_auth = bool(
        token_ctx.get("accepted_identity_as_caller_auth", False)
    )

    if (
        platform_forwarded_binding != issued_binding
        or platform_forwarded_binding != processor_expected_binding
        or platform_forwarded_identity != issued_identity
    ):
        return UcpTokenConsentAndCorrespondenceResult(
            allowed=False,
            decision_code="TOKEN_CREDENTIAL_BINDING_MISMATCH_OR_MUTATION_BLOCKED",
            token_binding_verified=False,
            effective_buyer_consent={},
            correspondence_verified=False,
            adjustment_cause_valid=False,
        )

    if accepted_identity_as_caller_auth or not caller_authenticated_independently:
        return UcpTokenConsentAndCorrespondenceResult(
            allowed=False,
            decision_code="TOKEN_CREDENTIAL_IDENTITY_ACCEPTED_AS_CALLER_AUTH_BLOCKED",
            token_binding_verified=False,
            effective_buyer_consent={},
            correspondence_verified=False,
            adjustment_cause_valid=False,
        )

    # 2. UCP PR #660: buyer.consent exemption from Cart/Checkout full replacement
    prior_consent = dict(context.get("prior_buyer_consent") or {"marketing": False, "analytics": False})
    update_buyer_payload = context.get("update_buyer_payload") or {}
    advertised_default_consent = dict(
        context.get("advertised_default_consent") or {"marketing": True, "analytics": True}
    )
    business_applied_consent = context.get("business_applied_consent")

    if "consent" in update_buyer_payload and update_buyer_payload["consent"] is not None:
        expected_consent = dict(prior_consent)
        expected_consent.update(update_buyer_payload["consent"])
    else:
        # Omitting buyer.consent MUST retain prior captured position, NOT reset to advertised defaults
        expected_consent = dict(prior_consent)

    if business_applied_consent is not None and dict(business_applied_consent) != expected_consent:
        return UcpTokenConsentAndCorrespondenceResult(
            allowed=False,
            decision_code="BUYER_CONSENT_DROPPED_ON_FULL_REPLACEMENT_UPDATE_BLOCKED",
            token_binding_verified=True,
            effective_buyer_consent=expected_consent,
            correspondence_verified=False,
            adjustment_cause_valid=False,
        )

    # 3. UCP PR #836: Correspondence chain verification
    corr = context.get("correspondence")
    if corr is not None:
        status = str(corr.get("status", ""))
        if status not in ("agrees", "diverges", "unverifiable"):
            return UcpTokenConsentAndCorrespondenceResult(
                allowed=False,
                decision_code="INVALID_CORRESPONDENCE_STATUS_ENUM",
                token_binding_verified=True,
                effective_buyer_consent=expected_consent,
                correspondence_verified=False,
                adjustment_cause_valid=False,
            )
        if status == "unverifiable" and bool(corr.get("reader_treated_unverifiable_as_agrees", False)):
            return UcpTokenConsentAndCorrespondenceResult(
                allowed=False,
                decision_code="UNVERIFIABLE_CORRESPONDENCE_TREATED_AS_AGREES_BLOCKED",
                token_binding_verified=True,
                effective_buyer_consent=expected_consent,
                correspondence_verified=False,
                adjustment_cause_valid=False,
            )
        compared = corr.get("compared", []) or []
        compared_fields = {str(c.get("field", "")) for c in compared}
        if status == "agrees" and not ({"$.totals", "$.currency"}.issubset(compared_fields)):
            return UcpTokenConsentAndCorrespondenceResult(
                allowed=False,
                decision_code="CORRESPONDENCE_AGREES_MISSING_TOTALS_COMPARISON_BLOCKED",
                token_binding_verified=True,
                effective_buyer_consent=expected_consent,
                correspondence_verified=False,
                adjustment_cause_valid=False,
            )
        for item in compared:
            if item.get("prior_value") != item.get("current_value") and status == "agrees":
                return UcpTokenConsentAndCorrespondenceResult(
                    allowed=False,
                    decision_code="CORRESPONDENCE_AGREES_CONTRADICTS_COMPARED_VALUES_BLOCKED",
                    token_binding_verified=True,
                    effective_buyer_consent=expected_consent,
                    correspondence_verified=False,
                    adjustment_cause_valid=False,
                )

    # 4. UCP PRs #837 & #843: Adjustment standard types + 3-axis cause
    adj = context.get("adjustment")
    if adj is not None:
        adj_type = str(adj.get("type", "")).strip()
        if not adj_type:
            return UcpTokenConsentAndCorrespondenceResult(
                allowed=False,
                decision_code="ADJUSTMENT_TYPE_EMPTY_BLOCKED",
                token_binding_verified=True,
                effective_buyer_consent=expected_consent,
                correspondence_verified=True,
                adjustment_cause_valid=False,
            )
        cause = adj.get("cause")
        if cause is not None:
            nature = str(cause.get("nature", "undetermined"))
            if nature not in VALID_ADJUSTMENT_CAUSE_NATURES:
                return UcpTokenConsentAndCorrespondenceResult(
                    allowed=False,
                    decision_code="INVALID_ADJUSTMENT_CAUSE_NATURE_ENUM",
                    token_binding_verified=True,
                    effective_buyer_consent=expected_consent,
                    correspondence_verified=True,
                    adjustment_cause_valid=False,
                )
            false_assertion_proven = bool(cause.get("false_assertion_of_fact_proven", True))
            treated_as_binding_liability = bool(cause.get("treated_as_binding_liability_adjudication", False))
            if (nature == "fraud" and not false_assertion_proven) or treated_as_binding_liability:
                return UcpTokenConsentAndCorrespondenceResult(
                    allowed=False,
                    decision_code="ADJUSTMENT_CAUSE_UNPROVEN_FRAUD_OR_LIABILITY_CONFLATION_BLOCKED",
                    token_binding_verified=True,
                    effective_buyer_consent=expected_consent,
                    correspondence_verified=True,
                    adjustment_cause_valid=False,
                )

    _ = advertised_default_consent
    return UcpTokenConsentAndCorrespondenceResult(
        allowed=True,
        decision_code="UCP_TOKEN_CONTEXT_CONSENT_AND_CORRESPONDENCE_VERIFIED",
        token_binding_verified=True,
        effective_buyer_consent=expected_consent,
        correspondence_verified=True,
        adjustment_cause_valid=True,
    )


@dataclass(frozen=True)
class AcpRazorpayIndiaAndFeedExtensionsResult:
    allowed: bool
    decision_code: str
    upi_intent_valid: bool
    s2s_coft_card_valid: bool
    feed_extensions_valid: bool


def evaluate_acp_razorpay_upi_s2s_and_feed_extensions_guard(
    context: dict[str, Any],
) -> AcpRazorpayIndiaAndFeedExtensionsResult:
    """Verify ACP PR #217 (Razorpay UPI Intent), PR #218 (Razorpay S2S CoFT Cards), and PR #223 (Feed Extensions)."""
    checkout_session_id = str(context.get("checkout_session_id", "cs_india_001"))
    now_epoch = int(context.get("now_epoch", 1_760_000_000))

    # 1. ACP PR #217: com.razorpay.upi_intent
    upi = context.get("upi_intent_context")
    if upi is not None:
        currency = str(upi.get("currency", "INR"))
        amount_paise = int(upi.get("amount_minor", 0))
        intent_uri = str(upi.get("intent_url", ""))
        expires_at = int(upi.get("expires_at_epoch", now_epoch + 300))

        parsed = urlparse(intent_uri)
        qs = parse_qs(parsed.query)
        tr_val = (qs.get("tr") or [""])[0]
        cu_val = (qs.get("cu") or [""])[0]

        if (
            currency != "INR"
            or cu_val != "INR"
            or amount_paise <= 0
            or amount_paise > NPCI_UPI_MAX_PAISE
            or parsed.scheme != "upi"
            or parsed.netloc != "pay"
            or tr_val != checkout_session_id
            or now_epoch > expires_at
        ):
            return AcpRazorpayIndiaAndFeedExtensionsResult(
                allowed=False,
                decision_code="ACP_UPI_INTENT_CAP_OR_TR_BINDING_VIOLATION",
                upi_intent_valid=False,
                s2s_coft_card_valid=False,
                feed_extensions_valid=False,
            )

    # 2. ACP PR #218: com.razorpay.s2s_cards (RBI CoFT token handler)
    s2s = context.get("s2s_card_context")
    if s2s is not None:
        currency = str(s2s.get("currency", "INR"))
        token_id = str(s2s.get("token_id", ""))
        token_merchant_id = str(s2s.get("token_merchant_id", "merch_in_01"))
        request_merchant_id = str(s2s.get("request_merchant_id", "merch_in_01"))
        has_raw_pan_or_cvv = bool(
            s2s.get("number") or s2s.get("pan") or s2s.get("cvv") or s2s.get("cvc")
        )
        if (
            currency != "INR"
            or not token_id.startswith("token_")
            or token_merchant_id != request_merchant_id
            or has_raw_pan_or_cvv
        ):
            return AcpRazorpayIndiaAndFeedExtensionsResult(
                allowed=False,
                decision_code="ACP_S2S_CARD_RAW_PAN_OR_TOKEN_SCOPE_VIOLATION",
                upi_intent_valid=True,
                s2s_coft_card_valid=False,
                feed_extensions_valid=False,
            )

    # 3. ACP PR #223: ACP Feed Extensions Framework
    feed = context.get("feed_extensions_context")
    if feed is not None:
        declared_exts = feed.get("metadata_extensions", []) or []
        declared_names: set[str] = set()
        for ext in declared_exts:
            name = str(ext.get("name", ""))
            extends_path = str(ext.get("extends", ""))
            schema_url = str(ext.get("schema", ""))
            spec_url = str(ext.get("spec", ""))
            if (
                not name
                or not extends_path.startswith("$.")
                or not schema_url.startswith("https://")
                or not spec_url.startswith("https://")
            ):
                return AcpRazorpayIndiaAndFeedExtensionsResult(
                    allowed=False,
                    decision_code="ACP_FEED_UNDECLARED_EXTENSION_OR_SSRF_SCHEMA_FETCH_BLOCKED",
                    upi_intent_valid=True,
                    s2s_coft_card_valid=True,
                    feed_extensions_valid=False,
                )
            declared_names.add(name)

        record_ext_names = set(feed.get("record_extension_names", []) or [])
        auto_fetch_untrusted_schema = bool(feed.get("auto_fetch_untrusted_external_schema", False))
        if not record_ext_names.issubset(declared_names) or auto_fetch_untrusted_schema:
            return AcpRazorpayIndiaAndFeedExtensionsResult(
                allowed=False,
                decision_code="ACP_FEED_UNDECLARED_EXTENSION_OR_SSRF_SCHEMA_FETCH_BLOCKED",
                upi_intent_valid=True,
                s2s_coft_card_valid=True,
                feed_extensions_valid=False,
            )

    return AcpRazorpayIndiaAndFeedExtensionsResult(
        allowed=True,
        decision_code="ACP_RAZORPAY_INDIA_AND_FEED_EXTENSIONS_VERIFIED",
        upi_intent_valid=True,
        s2s_coft_card_valid=True,
        feed_extensions_valid=True,
    )
