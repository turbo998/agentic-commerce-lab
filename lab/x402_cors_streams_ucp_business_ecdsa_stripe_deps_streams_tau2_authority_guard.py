"""Stage 122 deterministic protocol guards for x402 browser CORS headers,
PAYMENT-REQUIRED size limits, Axios stream release & facilitator error preservation,
UCP business identity, raw r||s ECDSA signatures, requires_escalation continue_url &
deferred payment-terms empty payment object, Stripe AI Python dependency hygiene,
ignored Configuration.actions privilege warning & inline stream meter cleanup, and
Sierra tau-bench 2.0 tau-Authority pre-mutation authorization guard.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any


CANONICAL_SUI_NETWORKS = {"sui:mainnet", "sui:testnet", "sui:devnet"}


@dataclass(frozen=True)
class X402CorsStreamsAndFacilitatorCheckResult:
    allowed: bool
    reason_code: str
    header_warning_level: str
    should_retry_settlement: bool


def validate_x402_cors_streams_and_facilitator(
    *,
    is_browser_cross_origin: bool,
    access_control_expose_headers: list[str],
    access_control_allow_headers: list[str],
    preflight_status_code: int,
    payment_required_header_bytes: int,
    intermediate_stream_released: bool,
    is_internal_corrective_402: bool,
    restarted_initial_payment_flow: bool,
    facilitator_http_status: int,
    facilitator_error_code: str | None,
    settlement_retry_count: int,
    non_browser_402_body_has_reason: bool,
    selected_network: str,
    selected_pay_to: str,
    expected_pay_to: str,
    selected_amount_minor: int,
    expected_max_amount_minor: int,
    svm_async_uses_blocking_rpc: bool,
) -> X402CorsStreamsAndFacilitatorCheckResult:
    """Validate x402 PRs #3809, #3805, #3817, #3818, #3802, #3795, #3799, #3804, and #3806."""
    # #3809: Browser CORS expose & preflight headers
    if is_browser_cross_origin:
        exposed = {h.upper() for h in access_control_expose_headers}
        allowed_hdrs = {h.upper() for h in access_control_allow_headers}
        if (
            "PAYMENT-REQUIRED" not in exposed
            or "PAYMENT-RESPONSE" not in exposed
            or "PAYMENT-SIGNATURE" not in allowed_hdrs
            or not (200 <= preflight_status_code < 300)
        ):
            return X402CorsStreamsAndFacilitatorCheckResult(
                allowed=False,
                reason_code="X402_BROWSER_CORS_HEADER_OR_PREFLIGHT_MISSING",
                header_warning_level="none",
                should_retry_settlement=False,
            )

    # #3805: PAYMENT-REQUIRED header size limits (8,190 aiohttp / 16,384 undici)
    if payment_required_header_bytes > 16384:
        return X402CorsStreamsAndFacilitatorCheckResult(
            allowed=False,
            reason_code="X402_PAYMENT_REQUIRED_HEADER_OVERFLOW_16KB",
            header_warning_level="overflow_16kb",
            should_retry_settlement=False,
        )
    warning_level = (
        "warn_8kb_aiohttp" if payment_required_header_bytes > 8190 else "none"
    )

    # #3817 & #3818: Axios intermediate stream release & internal 402 loop prevention
    if not intermediate_stream_released:
        return X402CorsStreamsAndFacilitatorCheckResult(
            allowed=False,
            reason_code="X402_AXIOS_INTERMEDIATE_STREAM_LEAKED",
            header_warning_level=warning_level,
            should_retry_settlement=False,
        )
    if is_internal_corrective_402 and restarted_initial_payment_flow:
        return X402CorsStreamsAndFacilitatorCheckResult(
            allowed=False,
            reason_code="X402_INTERNAL_CORRECTIVE_402_RESTARTED_INITIAL_FLOW",
            header_warning_level=warning_level,
            should_retry_settlement=False,
        )

    # #3806: Python async SVM payment creation must not block event loop
    if svm_async_uses_blocking_rpc:
        return X402CorsStreamsAndFacilitatorCheckResult(
            allowed=False,
            reason_code="X402_SVM_ASYNC_EVENT_LOOP_BLOCKED_BY_SYNC_RPC",
            header_warning_level=warning_level,
            should_retry_settlement=False,
        )

    # #3804 & #3799: Sui CAIP-2 registry & pre-sign onBeforePaymentCreation listing check
    if selected_network.startswith("sui:") and selected_network not in CANONICAL_SUI_NETWORKS:
        return X402CorsStreamsAndFacilitatorCheckResult(
            allowed=False,
            reason_code="X402_UNREGISTERED_SUI_CAIP2_NETWORK",
            header_warning_level=warning_level,
            should_retry_settlement=False,
        )
    if (
        selected_pay_to.lower() != expected_pay_to.lower()
        or selected_amount_minor > expected_max_amount_minor
    ):
        return X402CorsStreamsAndFacilitatorCheckResult(
            allowed=False,
            reason_code="X402_PRE_PAYMENT_LISTING_CHECK_MISMATCH",
            header_warning_level=warning_level,
            should_retry_settlement=False,
        )

    # #3802 & #3795: Facilitator HTTP error preservation & non-browser 402 JSON reason
    should_retry = False
    if facilitator_http_status != 200:
        if not non_browser_402_body_has_reason:
            return X402CorsStreamsAndFacilitatorCheckResult(
                allowed=False,
                reason_code="X402_NON_BROWSER_402_JSON_MISSING_REJECTION_REASON",
                header_warning_level=warning_level,
                should_retry_settlement=False,
            )
        if facilitator_error_code == "settlement_pending" and settlement_retry_count == 0:
            should_retry = True
        else:
            return X402CorsStreamsAndFacilitatorCheckResult(
                allowed=False,
                reason_code="X402_FACILITATOR_TERMINAL_OR_EXHAUSTED_ERROR",
                header_warning_level=warning_level,
                should_retry_settlement=False,
            )

    return X402CorsStreamsAndFacilitatorCheckResult(
        allowed=True,
        reason_code="X402_CORS_STREAMS_AND_FACILITATOR_VALID",
        header_warning_level=warning_level,
        should_retry_settlement=should_retry,
    )


@dataclass(frozen=True)
class UcpBusinessEcdsaEscalationTermsCheckResult:
    allowed: bool
    reason_code: str
    signature_byte_length: int


def validate_ucp_business_ecdsa_escalation_and_terms(
    *,
    business_profile: dict[str, Any],
    curve: str,
    signature_b64: str,
    checkout_status: str,
    continue_url: str | None,
    is_deferred_payment_term: bool,
    complete_checkout_payment_obj: dict[str, Any] | None,
) -> UcpBusinessEcdsaEscalationTermsCheckResult:
    """Validate UCP PRs #939, #934, #912, and #908."""
    # #939: dev.ucp.common.business brand-level identity
    if not business_profile.get("display_name") or not business_profile.get("website"):
        return UcpBusinessEcdsaEscalationTermsCheckResult(
            allowed=False,
            reason_code="UCP_BUSINESS_IDENTITY_MISSING_DISPLAY_NAME_OR_WEBSITE",
            signature_byte_length=0,
        )

    # #934: Fixed-width raw r||s ECDSA signature encoding (never ASN.1 DER 0x30)
    try:
        sig_bytes = base64.b64decode(signature_b64, validate=True)
    except Exception:
        return UcpBusinessEcdsaEscalationTermsCheckResult(
            allowed=False,
            reason_code="UCP_ECDSA_SIGNATURE_INVALID_BASE64",
            signature_byte_length=0,
        )

    expected_len = 64 if curve == "P-256" else (96 if curve == "P-384" else -1)
    if (
        len(sig_bytes) != expected_len
        or (len(sig_bytes) >= 2 and sig_bytes[0] == 0x30 and sig_bytes[2:3] == b"\x02")
    ):
        return UcpBusinessEcdsaEscalationTermsCheckResult(
            allowed=False,
            reason_code="UCP_ECDSA_SIGNATURE_ASN1_DER_OR_WRONG_RAW_WIDTH",
            signature_byte_length=len(sig_bytes),
        )

    # #912: Enforce continue_url when checkout status is requires_escalation
    if checkout_status == "requires_escalation" and not (
        continue_url and continue_url.startswith("https://")
    ):
        return UcpBusinessEcdsaEscalationTermsCheckResult(
            allowed=False,
            reason_code="UCP_REQUIRES_ESCALATION_MISSING_CONTINUE_URL",
            signature_byte_length=len(sig_bytes),
        )

    # #908: Deferred payment terms require empty payment object {} on complete_checkout
    if is_deferred_payment_term:
        if complete_checkout_payment_obj is None:
            return UcpBusinessEcdsaEscalationTermsCheckResult(
                allowed=False,
                reason_code="UCP_DEFERRED_TERMS_MISSING_PAYMENT_OBJECT_ON_COMPLETE",
                signature_byte_length=len(sig_bytes),
            )
        if "selected_term_id" in complete_checkout_payment_obj or len(complete_checkout_payment_obj) > 0:
            return UcpBusinessEcdsaEscalationTermsCheckResult(
                allowed=False,
                reason_code="UCP_DEFERRED_TERMS_NON_EMPTY_PAYMENT_OR_SELECTED_TERM_ID_ON_COMPLETE",
                signature_byte_length=len(sig_bytes),
            )

    return UcpBusinessEcdsaEscalationTermsCheckResult(
        allowed=True,
        reason_code="UCP_BUSINESS_ECDSA_ESCALATION_AND_TERMS_VALID",
        signature_byte_length=len(sig_bytes),
    )


@dataclass(frozen=True)
class StripeDepsStreamAndTau2AuthorityCheckResult:
    allowed: bool
    reason_code: str
    source_stream_closed: bool


def validate_stripe_deps_stream_and_tau2_authority(
    *,
    mcp_major_version: int,
    strands_extra_package: str,
    openai_extra_package: str,
    configuration_keys: list[str],
    caller_broke_stream_early: bool,
    unawaited_background_tee_used: bool,
    source_iterator_closed_on_break: bool,
    authenticated_customer_id: str,
    target_resource_owner_id: str,
    policy_permits_mutation: bool,
    voice_submission_has_commit_and_recordings: bool,
) -> StripeDepsStreamAndTau2AuthorityCheckResult:
    """Validate Stripe AI PRs #540, #541, #525, #509 and Sierra tau-bench PRs #629 & #627."""
    # #540 & #541: Cap mcp < 2 and require strands-agents / openai-agents packages
    if (
        mcp_major_version >= 2
        or strands_extra_package != "strands-agents"
        or openai_extra_package != "openai-agents"
    ):
        return StripeDepsStreamAndTau2AuthorityCheckResult(
            allowed=False,
            reason_code="STRIPE_PYTHON_DEPENDENCY_MISMATCH_MCP2_OR_WRONG_EXTRA",
            source_stream_closed=False,
        )

    # #525: Reject ignored Configuration keys (especially legacy v0.6 'actions')
    unknown_keys = [k for k in configuration_keys if k != "context"]
    if unknown_keys:
        code = (
            "STRIPE_CONFIGURATION_LEGACY_ACTIONS_IGNORED_PRIVILEGE_RISK"
            if "actions" in unknown_keys
            else "STRIPE_CONFIGURATION_UNKNOWN_KEYS_IGNORED"
        )
        return StripeDepsStreamAndTau2AuthorityCheckResult(
            allowed=False,
            reason_code=code,
            source_stream_closed=False,
        )

    # #509: Inline stream metering & source iterator cleanup on early break
    if unawaited_background_tee_used or (
        caller_broke_stream_early and not source_iterator_closed_on_break
    ):
        return StripeDepsStreamAndTau2AuthorityCheckResult(
            allowed=False,
            reason_code="STRIPE_TOKEN_METER_ABANDONED_STREAM_NOT_CLOSED",
            source_stream_closed=False,
        )

    # #629: tau-Authority deterministic pre-mutation customer authority check
    if authenticated_customer_id != target_resource_owner_id or not policy_permits_mutation:
        return StripeDepsStreamAndTau2AuthorityCheckResult(
            allowed=False,
            reason_code="TAU2_AUTHORITY_OUT_OF_AUTHORITY_MUTATION_BLOCKED",
            source_stream_closed=True,
        )

    # #627: Voice submission archive & commit lineage integrity
    if not voice_submission_has_commit_and_recordings:
        return StripeDepsStreamAndTau2AuthorityCheckResult(
            allowed=False,
            reason_code="TAU2_VOICE_SUBMISSION_MISSING_LINEAGE_OR_RECORDINGS",
            source_stream_closed=True,
        )

    return StripeDepsStreamAndTau2AuthorityCheckResult(
        allowed=True,
        reason_code="STRIPE_DEPS_STREAM_AND_TAU2_AUTHORITY_VALID",
        source_stream_closed=True,
    )
