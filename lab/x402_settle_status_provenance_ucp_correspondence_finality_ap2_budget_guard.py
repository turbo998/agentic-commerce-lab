"""Stage 148 deterministic runtime guards across x402, UCP, ACP, AP2, MCP, Stripe, Visa TAP, and tau2-bench.

Covers primary-source protocol PRs:
- SP-01: x402 #3325 SettleResponse 6-state vocabulary, evidence anchor & ledgerTime gate
- SP-02: x402 #3304 response-provenance RFC 8785 JCS fixed-point hash & #3306 server-only extension_responses isolation
- SP-03: x402 #3338 SettlementOverrides.amount ceiling enforcement & #3372 EVM batch extra.minDeposit cap
- SP-04: x402 #3370 near-intents upfront deposit address, #3320/#3313 v2 builder-code attribution & #3318/#3340 SVM Lighthouse / Path 1 error preservation
- SP-05: UCP #836 Correspondence record-chain continuity, stale-quote observation lag & #835 agent spend/payee signals
- SP-06: UCP #816 checkout amount_finality, payment.maximum_amount ceiling & Order authorized/captured reporting
- SP-07: UCP #811 catalog variant.offers[] per-seller MoR attribution, #831 reserved ucp_ prefix ban & #801/#802 continue_url / OpenRPC auth
- SP-08: UCP #793 permalink ucp/version pinning, #789 explicit buyer action before cart merge & #785 ucp-agent/signature-agent coverage
- SP-09: ACP #171 Store Extension BOPIS store_id binding, #165 per-line-item valid_until expiry & #162 order status semantics
- SP-10: ACP #161 Delegate Payment 401/500/503 error schema alignment, #156 com.stripe.link handler & #150 wallet intervention_types
- SP-11: Google AP2 #252 atomic external budget authority 4-verb gate preventing multi-merchant concurrent overspend
- SP-12: Google AP2 #229 AP2-Haggle multi-round negotiation constraints & #228 Solana Pay single-use reference pubkey mandate binding
- SP-13: MCP #3392 extension lifecycle repository stage gate, #3371 order-independent SDK extension registration & #3364 versioned negotiation
- SP-14: Stripe AI #434, #453 & #457 x402 settlement override guard, com.stripe.link mandate ceiling & stripe-projects preflight
- SP-15: Visa TAP #26, #25, #23 & #16 ucp-agent/signature-agent header coverage & provisional mandate ceiling enforcement
- SP-16: Sierra tau2-bench #611 active telecom line refuel precondition, #609/#610 live-DB hash grading vs timeout_after_commit replay divergence & #606 banking aggregate sync
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Mapping, Sequence


VALID_SETTLE_STATES = frozenset(
    {"settled", "pending", "deferred_until", "blocked", "canceled", "expired"}
)
VALID_ANCHOR_KINDS = frozenset({"transaction", "event", "read", "composite", "none"})
NON_TERMINAL_ERROR_CODES = frozenset(
    {"authorization_canceled", "settlement_deferred", "settlement_blocked"}
)
SPL_DIRECT_TOKEN_PROGRAMS = frozenset({"TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA", "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"})
EXEMPT_SVM_PROGRAMS = frozenset({"ComputeBudget111111111111111111111111111111", "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr", "Lighthouse111111111111111111111111111111111"})

VALID_CORRESPONDENCE_STATUSES = frozenset({"agrees", "diverges", "unverifiable"})
VALID_AMOUNT_FINALITY = frozenset({"final", "provisional"})
DATE_VERSION_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

ACP_DELEGATE_ERROR_TYPES = frozenset(
    {"invalid_request", "rate_limit_exceeded", "unauthorized", "internal_server_error"}
)
ACP_DELEGATE_ERROR_CODES = frozenset(
    {
        "invalid_card",
        "expired_card",
        "insufficient_funds",
        "unauthorized",
        "internal_server_error",
        "service_unavailable",
    }
)
ACP_WALLET_INTERVENTION_TYPES = frozenset(
    {
        "3ds",
        "biometric",
        "address_verification",
        "otp_email",
        "otp_sms",
        "redirect_auth",
        "embedded_webview",
    }
)


def _canonical_jcs_bytes(value: Any) -> bytes:
    """Deterministic RFC 8785 JCS-style canonical JSON serialization."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def compute_jcs_sha256_hex(value: Any) -> str:
    return hashlib.sha256(_canonical_jcs_bytes(value)).hexdigest()


# ---------------------------------------------------------------------------
# SP-01: x402 #3325 SettleResponse 6-State Vocabulary & Evidence Anchor Gate
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class X402SettleStatusAuditResult:
    allowed: bool
    reason_code: str
    status: str
    anchor_kind: str
    reader_may_deliver_or_retry: bool


def evaluate_x402_settle_status_vocabulary_guard(
    *,
    status: str,
    anchor_kind: str,
    anchor_ref: str,
    observation_block_number: int,
    ledger_time_epoch_s: int | None,
    error_code: str = "",
    reader_attempted_delivery_or_unanchored_retry: bool = False,
) -> X402SettleStatusAuditResult:
    if status not in VALID_SETTLE_STATES:
        return X402SettleStatusAuditResult(
            allowed=False,
            reason_code="X402_SETTLE_STATUS_UNKNOWN",
            status=status,
            anchor_kind=anchor_kind,
            reader_may_deliver_or_retry=False,
        )
    if anchor_kind not in VALID_ANCHOR_KINDS:
        return X402SettleStatusAuditResult(
            allowed=False,
            reason_code="X402_SETTLE_ANCHOR_KIND_INVALID",
            status=status,
            anchor_kind=anchor_kind,
            reader_may_deliver_or_retry=False,
        )
    if anchor_kind != "none" and not anchor_ref.strip():
        return X402SettleStatusAuditResult(
            allowed=False,
            reason_code="X402_SETTLE_ANCHOR_REF_MISSING",
            status=status,
            anchor_kind=anchor_kind,
            reader_may_deliver_or_retry=False,
        )
    if observation_block_number <= 0:
        return X402SettleStatusAuditResult(
            allowed=False,
            reason_code="X402_SETTLE_OBSERVATION_BLOCK_MISSING",
            status=status,
            anchor_kind=anchor_kind,
            reader_may_deliver_or_retry=False,
        )
    if status == "settled":
        if anchor_kind == "none":
            return X402SettleStatusAuditResult(
                allowed=False,
                reason_code="X402_SETTLED_REQUIRES_EVIDENCE_ANCHOR",
                status=status,
                anchor_kind=anchor_kind,
                reader_may_deliver_or_retry=False,
            )
        if ledger_time_epoch_s is None or ledger_time_epoch_s <= 0:
            return X402SettleStatusAuditResult(
                allowed=False,
                reason_code="X402_SETTLED_LEDGER_TIME_REQUIRED",
                status=status,
                anchor_kind=anchor_kind,
                reader_may_deliver_or_retry=False,
            )
    is_non_terminal_or_blocked = (
        status in {"pending", "deferred_until", "blocked", "canceled", "expired"}
        or error_code in NON_TERMINAL_ERROR_CODES
    )
    if is_non_terminal_or_blocked and reader_attempted_delivery_or_unanchored_retry:
        return X402SettleStatusAuditResult(
            allowed=False,
            reason_code="X402_NON_TERMINAL_READER_ACTION_FORBIDDEN",
            status=status,
            anchor_kind=anchor_kind,
            reader_may_deliver_or_retry=False,
        )
    return X402SettleStatusAuditResult(
        allowed=True,
        reason_code="OK",
        status=status,
        anchor_kind=anchor_kind,
        reader_may_deliver_or_retry=(status == "settled" and not error_code),
    )


# ---------------------------------------------------------------------------
# SP-02: x402 #3304 response-provenance JCS Fixed-Point & #3306 Sidechannel
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class X402ResponseProvenanceAuditResult:
    allowed: bool
    reason_code: str
    computed_response_hash: str
    sidechannel_isolated: bool


def evaluate_x402_response_provenance_and_sidechannel_guard(
    *,
    endpoint: str,
    inputs: Mapping[str, Any],
    result: Any,
    method: str,
    data_vintage: str,
    declared_response_hash: str,
    facilitator_extension_responses: Mapping[str, Any],
    client_payment_response_extensions: Mapping[str, Any],
) -> X402ResponseProvenanceAuditResult:
    if not endpoint.strip() or not method.strip() or not data_vintage.strip():
        return X402ResponseProvenanceAuditResult(
            allowed=False,
            reason_code="X402_PROVENANCE_FIXED_POINT_INCOMPLETE",
            computed_response_hash="",
            sidechannel_isolated=False,
        )
    fixed_point = {
        "endpoint": endpoint,
        "inputs": dict(inputs),
        "result": result,
        "method": method.upper(),
        "dataVintage": data_vintage,
    }
    computed_hash = compute_jcs_sha256_hex(fixed_point)
    if computed_hash != declared_response_hash:
        return X402ResponseProvenanceAuditResult(
            allowed=False,
            reason_code="X402_RESPONSE_PROVENANCE_HASH_MISMATCH",
            computed_response_hash=computed_hash,
            sidechannel_isolated=False,
        )
    # #3306: facilitator EXTENSION-RESPONSES is a server-only sidechannel and must not leak into client PAYMENT-RESPONSE extensions
    leaked_keys = set(facilitator_extension_responses.keys()) & set(
        client_payment_response_extensions.keys()
    )
    if leaked_keys:
        return X402ResponseProvenanceAuditResult(
            allowed=False,
            reason_code="X402_SERVER_EXTENSION_RESPONSES_LEAKED_TO_CLIENT",
            computed_response_hash=computed_hash,
            sidechannel_isolated=False,
        )
    return X402ResponseProvenanceAuditResult(
        allowed=True,
        reason_code="OK",
        computed_response_hash=computed_hash,
        sidechannel_isolated=True,
    )


# ---------------------------------------------------------------------------
# SP-03: x402 #3338 SettlementOverrides Ceiling & #3372 EVM extra.minDeposit
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class X402OverrideAndMinDepositAuditResult:
    allowed: bool
    reason_code: str
    resolved_override_atomic: int
    effective_deposit_atomic: int


def evaluate_x402_settlement_override_and_min_deposit_guard(
    *,
    authorized_amount_atomic: int,
    override_spec: str,
    asset_decimals: int = 6,
    extra_min_deposit_atomic: int | None = None,
    client_max_escrow_atomic: int = 20_000_000,
) -> X402OverrideAndMinDepositAuditResult:
    if authorized_amount_atomic <= 0:
        return X402OverrideAndMinDepositAuditResult(
            allowed=False,
            reason_code="X402_AUTHORIZED_AMOUNT_INVALID",
            resolved_override_atomic=0,
            effective_deposit_atomic=0,
        )
    spec = override_spec.strip()
    if spec.endswith("%"):
        pct = float(spec[:-1])
        if pct < 0:
            return X402OverrideAndMinDepositAuditResult(
                allowed=False,
                reason_code="X402_OVERRIDE_NEGATIVE",
                resolved_override_atomic=0,
                effective_deposit_atomic=0,
            )
        resolved = int(round(authorized_amount_atomic * (pct / 100.0)))
    elif spec.startswith("$"):
        dollars = float(spec[1:])
        resolved = int(round(dollars * (10**asset_decimals)))
    else:
        resolved = int(spec)

    if resolved < 0 or resolved > authorized_amount_atomic:
        return X402OverrideAndMinDepositAuditResult(
            allowed=False,
            reason_code="X402_SETTLEMENT_OVERRIDE_EXCEEDS_AUTHORIZED_CEILING",
            resolved_override_atomic=resolved,
            effective_deposit_atomic=0,
        )

    deposit_target = (
        extra_min_deposit_atomic
        if extra_min_deposit_atomic is not None
        else authorized_amount_atomic * 10
    )
    if deposit_target < authorized_amount_atomic:
        return X402OverrideAndMinDepositAuditResult(
            allowed=False,
            reason_code="X402_MIN_DEPOSIT_BELOW_AMOUNT",
            resolved_override_atomic=resolved,
            effective_deposit_atomic=deposit_target,
        )
    if deposit_target > client_max_escrow_atomic:
        return X402OverrideAndMinDepositAuditResult(
            allowed=False,
            reason_code="X402_MIN_DEPOSIT_EXCEEDS_CLIENT_ESCROW_CAP",
            resolved_override_atomic=resolved,
            effective_deposit_atomic=deposit_target,
        )
    return X402OverrideAndMinDepositAuditResult(
        allowed=True,
        reason_code="OK",
        resolved_override_atomic=resolved,
        effective_deposit_atomic=deposit_target,
    )


# ---------------------------------------------------------------------------
# SP-04: x402 #3370 near-intents upfront, #3320 builder-code & #3318/#3340 SVM
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class X402NearIntentsBuilderSvmAuditResult:
    allowed: bool
    reason_code: str
    preserved_svm_error: str


def evaluate_x402_near_intents_builder_svm_guard(
    *,
    payment_flow: str,
    origin_network: str,
    single_use_deposit_address: str,
    facilitator_confirmed_delivery: bool,
    server_declared_builder_code_a: str | None,
    payload_builder_code_a: str | None,
    svm_instruction_programs: Sequence[str],
    svm_path1_rejection_reason: str = "",
    http_body_bytes: int = 1024,
    is_bazaar_discovery: bool = False,
) -> X402NearIntentsBuilderSvmAuditResult:
    max_body = 4 * 1024 * 1024 if is_bazaar_discovery else 1 * 1024 * 1024
    if http_body_bytes > max_body:
        return X402NearIntentsBuilderSvmAuditResult(
            allowed=False,
            reason_code="X402_HTTP_RESPONSE_BODY_LIMIT_EXCEEDED",
            preserved_svm_error="",
        )
    if payment_flow != "upfront" or origin_network == "near:mainnet":
        return X402NearIntentsBuilderSvmAuditResult(
            allowed=False,
            reason_code="X402_NEAR_INTENTS_UPFRONT_FLOW_OR_ORIGIN_INVALID",
            preserved_svm_error="",
        )
    if not single_use_deposit_address.strip() or not facilitator_confirmed_delivery:
        return X402NearIntentsBuilderSvmAuditResult(
            allowed=False,
            reason_code="X402_NEAR_INTENTS_DELIVERY_UNCONFIRMED",
            preserved_svm_error="",
        )
    # #3320 / #3313: server-owned builder-code `a` attribution on v2
    if payload_builder_code_a is not None:
        if (
            server_declared_builder_code_a is None
            or payload_builder_code_a != server_declared_builder_code_a
        ):
            return X402NearIntentsBuilderSvmAuditResult(
                allowed=False,
                reason_code="extension_echo_mismatch",
                preserved_svm_error="",
            )
    # #3318 & #3340: Lighthouse guards allowed at any position; preserve Path 1 direct token transfer error
    non_exempt_programs = [
        p for p in svm_instruction_programs if p not in EXEMPT_SVM_PROGRAMS
    ]
    distinct_non_exempt = set(non_exempt_programs)
    if svm_path1_rejection_reason:
        if (
            len(distinct_non_exempt) == 1
            and next(iter(distinct_non_exempt)) in SPL_DIRECT_TOKEN_PROGRAMS
        ):
            return X402NearIntentsBuilderSvmAuditResult(
                allowed=False,
                reason_code=svm_path1_rejection_reason,
                preserved_svm_error=svm_path1_rejection_reason,
            )
        return X402NearIntentsBuilderSvmAuditResult(
            allowed=False,
            reason_code="smart_wallet_program_not_allowed",
            preserved_svm_error="smart_wallet_program_not_allowed",
        )
    if not distinct_non_exempt.issubset(SPL_DIRECT_TOKEN_PROGRAMS):
        return X402NearIntentsBuilderSvmAuditResult(
            allowed=False,
            reason_code="X402_SVM_UNEXPECTED_PROGRAM",
            preserved_svm_error="",
        )
    return X402NearIntentsBuilderSvmAuditResult(
        allowed=True,
        reason_code="OK",
        preserved_svm_error="",
    )


# ---------------------------------------------------------------------------
# SP-05: UCP #836 Correspondence Record-Chain & #835 Agent Behavior Signals
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class UcpCorrespondenceAndSignalsAuditResult:
    allowed: bool
    reason_code: str
    correspondence_status: str
    observation_lag_s: int


def evaluate_ucp_correspondence_and_agent_signals_guard(
    *,
    derived_from_record_id: str,
    derived_from_record_type: str,
    derived_from_issued_at_s: int,
    derived_from_observed_at_s: int,
    max_observation_lag_s: int,
    prior_amount_minor: int,
    current_amount_minor: int,
    declared_correspondence_status: str,
    signals_payload: Mapping[str, Any],
    agent_amount_minor: int,
    agent_history_p99_minor: int,
    payee_seen_before: bool,
) -> UcpCorrespondenceAndSignalsAuditResult:
    if not derived_from_record_id.strip() or not derived_from_record_type.strip():
        return UcpCorrespondenceAndSignalsAuditResult(
            allowed=False,
            reason_code="UCP_CORRESPONDENCE_DERIVED_FROM_MISSING",
            correspondence_status="unverifiable",
            observation_lag_s=0,
        )
    if declared_correspondence_status not in VALID_CORRESPONDENCE_STATUSES:
        return UcpCorrespondenceAndSignalsAuditResult(
            allowed=False,
            reason_code="UCP_CORRESPONDENCE_STATUS_INVALID",
            correspondence_status=declared_correspondence_status,
            observation_lag_s=0,
        )
    lag = derived_from_observed_at_s - derived_from_issued_at_s
    if lag < 0 or lag > max_observation_lag_s:
        return UcpCorrespondenceAndSignalsAuditResult(
            allowed=False,
            reason_code="UCP_CORRESPONDENCE_STALE_QUOTE_OBSERVATION_LAG",
            correspondence_status="diverges",
            observation_lag_s=lag,
        )
    actual_status = "agrees" if prior_amount_minor == current_amount_minor else "diverges"
    if declared_correspondence_status != actual_status:
        return UcpCorrespondenceAndSignalsAuditResult(
            allowed=False,
            reason_code="UCP_CORRESPONDENCE_STATUS_MISMATCH",
            correspondence_status=actual_status,
            observation_lag_s=lag,
        )
    if actual_status == "diverges":
        return UcpCorrespondenceAndSignalsAuditResult(
            allowed=False,
            reason_code="UCP_CORRESPONDENCE_RECORD_CHAIN_DIVERGED",
            correspondence_status="diverges",
            observation_lag_s=lag,
        )
    # #835 review constraint: instruction_provenance must NOT be trusted in runtime signals; belong in signed evidence
    if "dev.ucp.instruction_provenance" in signals_payload:
        return UcpCorrespondenceAndSignalsAuditResult(
            allowed=False,
            reason_code="UCP_UNVERIFIED_INSTRUCTION_PROVENANCE_IN_SIGNALS",
            correspondence_status=actual_status,
            observation_lag_s=lag,
        )
    if agent_amount_minor > agent_history_p99_minor and not payee_seen_before:
        return UcpCorrespondenceAndSignalsAuditResult(
            allowed=False,
            reason_code="UCP_AGENT_SPEND_P99_ANOMALY_NEW_PAYEE_STEP_UP",
            correspondence_status=actual_status,
            observation_lag_s=lag,
        )
    return UcpCorrespondenceAndSignalsAuditResult(
        allowed=True,
        reason_code="OK",
        correspondence_status=actual_status,
        observation_lag_s=lag,
    )


# ---------------------------------------------------------------------------
# SP-06: UCP #816 Checkout Payment Finality, Maximum Amount & Order Reporting
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class UcpPaymentFinalityAuditResult:
    allowed: bool
    reason_code: str
    authorized_amount_minor: int
    captured_amount_minor: int


def evaluate_ucp_checkout_payment_finality_guard(
    *,
    amount_finality: str,
    checkout_total_minor: int,
    buyer_approved_maximum_minor: int | None,
    order_instrument_payload: Mapping[str, Any],
) -> UcpPaymentFinalityAuditResult:
    if amount_finality not in VALID_AMOUNT_FINALITY:
        return UcpPaymentFinalityAuditResult(
            allowed=False,
            reason_code="UCP_AMOUNT_FINALITY_INVALID",
            authorized_amount_minor=0,
            captured_amount_minor=0,
        )
    if amount_finality == "provisional" and (
        buyer_approved_maximum_minor is None
        or buyer_approved_maximum_minor < checkout_total_minor
    ):
        return UcpPaymentFinalityAuditResult(
            allowed=False,
            reason_code="UCP_PROVISIONAL_TOTAL_MISSING_VALID_MAXIMUM_AMOUNT",
            authorized_amount_minor=0,
            captured_amount_minor=0,
        )
    ceiling = (
        buyer_approved_maximum_minor
        if buyer_approved_maximum_minor is not None
        else checkout_total_minor
    )
    if "credential" in order_instrument_payload or "routing" in order_instrument_payload:
        return UcpPaymentFinalityAuditResult(
            allowed=False,
            reason_code="UCP_ORDER_INSTRUMENT_LEAKED_CREDENTIAL_OR_ROUTING",
            authorized_amount_minor=0,
            captured_amount_minor=0,
        )
    auth_amt = order_instrument_payload.get("authorized_amount")
    cap_amt = order_instrument_payload.get("captured_amount")
    if not isinstance(auth_amt, int) or not isinstance(cap_amt, int):
        return UcpPaymentFinalityAuditResult(
            allowed=False,
            reason_code="UCP_ORDER_INSTRUMENT_MISSING_AUTH_OR_CAPTURED_AMOUNT",
            authorized_amount_minor=0,
            captured_amount_minor=0,
        )
    if auth_amt > ceiling or cap_amt > auth_amt or cap_amt > ceiling:
        return UcpPaymentFinalityAuditResult(
            allowed=False,
            reason_code="UCP_ORDER_CAPTURE_EXCEEDS_MANDATE_MAXIMUM_AMOUNT",
            authorized_amount_minor=auth_amt,
            captured_amount_minor=cap_amt,
        )
    return UcpPaymentFinalityAuditResult(
        allowed=True,
        reason_code="OK",
        authorized_amount_minor=auth_amt,
        captured_amount_minor=cap_amt,
    )


# ---------------------------------------------------------------------------
# SP-07: UCP #811 Variant offers[], #831 Reserved ucp_ Prefix & #801/#802
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class UcpVariantOffersAndSchemaAuditResult:
    allowed: bool
    reason_code: str
    selected_seller_id: str


def evaluate_ucp_variant_offers_and_schema_guard(
    *,
    variant_offers: Sequence[Mapping[str, Any]],
    requested_offer_id: str,
    checkout_seller_id: str,
    checkout_price_minor: int,
    schema_defs_keys: Sequence[str],
    continue_url: str,
    openrpc_embedded_auth_type_required: bool,
) -> UcpVariantOffersAndSchemaAuditResult:
    for key in schema_defs_keys:
        if key.startswith("ucp_"):
            return UcpVariantOffersAndSchemaAuditResult(
                allowed=False,
                reason_code="UCP_RESERVED_DEFS_PREFIX_VIOLATION",
                selected_seller_id="",
            )
    if not openrpc_embedded_auth_type_required:
        return UcpVariantOffersAndSchemaAuditResult(
            allowed=False,
            reason_code="UCP_OPENRPC_EMBEDDED_AUTH_TYPE_NOT_REQUIRED",
            selected_seller_id="",
        )
    if not continue_url.startswith("https://"):
        return UcpVariantOffersAndSchemaAuditResult(
            allowed=False,
            reason_code="UCP_CART_CONTINUE_URL_INVALID",
            selected_seller_id="",
        )
    matched = next(
        (o for o in variant_offers if o.get("id") == requested_offer_id), None
    )
    if matched is None:
        return UcpVariantOffersAndSchemaAuditResult(
            allowed=False,
            reason_code="UCP_VARIANT_OFFER_NOT_FOUND",
            selected_seller_id="",
        )
    seller_id = str(matched.get("seller_id", ""))
    price_minor = int(matched.get("price_minor", -1))
    if seller_id != checkout_seller_id or price_minor != checkout_price_minor:
        return UcpVariantOffersAndSchemaAuditResult(
            allowed=False,
            reason_code="UCP_VARIANT_OFFER_SELLER_OR_PRICE_MISMATCH",
            selected_seller_id=seller_id,
        )
    return UcpVariantOffersAndSchemaAuditResult(
        allowed=True,
        reason_code="OK",
        selected_seller_id=seller_id,
    )


# ---------------------------------------------------------------------------
# SP-08: UCP #793 Permalink ucp/version, #789 Explicit Merge & #785 Signatures
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class UcpPermalinkAndSignatureAuditResult:
    allowed: bool
    reason_code: str
    pinned_version: str


def evaluate_ucp_permalink_and_signature_guard(
    *,
    permalink_query_params: Mapping[str, str],
    authenticated_existing_cart: bool,
    explicit_buyer_merge_action: bool,
    signed_components: Sequence[str],
    has_signature_agent_header: bool,
) -> UcpPermalinkAndSignatureAuditResult:
    version = permalink_query_params.get("ucp/version", "")
    if not DATE_VERSION_RE.match(version):
        return UcpPermalinkAndSignatureAuditResult(
            allowed=False,
            reason_code="UCP_PERMALINK_VERSION_MISSING_OR_INVALID",
            pinned_version=version,
        )
    if authenticated_existing_cart and not explicit_buyer_merge_action:
        return UcpPermalinkAndSignatureAuditResult(
            allowed=False,
            reason_code="UCP_PERMALINK_CSRF_AUTO_CART_MERGE_BLOCKED",
            pinned_version=version,
        )
    comp_set = {c.lower() for c in signed_components}
    if "ucp-agent" not in comp_set:
        return UcpPermalinkAndSignatureAuditResult(
            allowed=False,
            reason_code="coverage_insufficient:ucp-agent",
            pinned_version=version,
        )
    if has_signature_agent_header and "signature-agent" not in comp_set:
        return UcpPermalinkAndSignatureAuditResult(
            allowed=False,
            reason_code="coverage_insufficient:signature-agent",
            pinned_version=version,
        )
    return UcpPermalinkAndSignatureAuditResult(
        allowed=True,
        reason_code="OK",
        pinned_version=version,
    )


# ---------------------------------------------------------------------------
# SP-09: ACP #171 Store BOPIS, #165 Line-Item valid_until & #162 Order Status
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class AcpStoreExpiryAndStatusAuditResult:
    allowed: bool
    reason_code: str
    order_status: str


def evaluate_acp_store_expiry_and_order_status_guard(
    *,
    fulfillment_type: str,
    store_id: str | None,
    store_inventory_available: bool,
    line_item_valid_until_epoch_s: int,
    checkout_now_epoch_s: int,
    order_status: str,
) -> AcpStoreExpiryAndStatusAuditResult:
    if fulfillment_type in {"bopis", "in_store"}:
        if not store_id or not store_id.strip() or not store_inventory_available:
            return AcpStoreExpiryAndStatusAuditResult(
                allowed=False,
                reason_code="ACP_STORE_BOPIS_INVENTORY_OR_STORE_ID_INVALID",
                order_status=order_status,
            )
    if checkout_now_epoch_s > line_item_valid_until_epoch_s:
        return AcpStoreExpiryAndStatusAuditResult(
            allowed=False,
            reason_code="ACP_LINE_ITEM_OFFER_VALID_UNTIL_EXPIRED",
            order_status=order_status,
        )
    # #162: 'shipped' is valid only for physical shipping in transit; digital cannot be 'shipped'
    if fulfillment_type == "digital" and order_status == "shipped":
        return AcpStoreExpiryAndStatusAuditResult(
            allowed=False,
            reason_code="ACP_DIGITAL_FULFILLMENT_CANNOT_USE_SHIPPED_STATUS",
            order_status=order_status,
        )
    if order_status not in {"created", "confirmed", "shipped", "fulfilled", "canceled"}:
        return AcpStoreExpiryAndStatusAuditResult(
            allowed=False,
            reason_code="ACP_ORDER_STATUS_INVALID",
            order_status=order_status,
        )
    return AcpStoreExpiryAndStatusAuditResult(
        allowed=True,
        reason_code="OK",
        order_status=order_status,
    )


# ---------------------------------------------------------------------------
# SP-10: ACP #161 Delegate Error 401/500/503, #156 Stripe Link & #150 Wallet
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class AcpDelegateLinkInterventionAuditResult:
    allowed: bool
    reason_code: str
    handler_id: str


def evaluate_acp_delegate_link_intervention_guard(
    *,
    http_status: int,
    error_type: str | None,
    error_code: str | None,
    payment_handler_id: str,
    link_authenticated_session_id: str,
    intervention_type: str,
) -> AcpDelegateLinkInterventionAuditResult:
    if http_status in {401, 500, 503}:
        if error_type not in ACP_DELEGATE_ERROR_TYPES or error_code not in ACP_DELEGATE_ERROR_CODES:
            return AcpDelegateLinkInterventionAuditResult(
                allowed=False,
                reason_code="ACP_DELEGATE_PAYMENT_ERROR_ENUM_MISMATCH",
                handler_id=payment_handler_id,
            )
        expected_map = {
            401: ("unauthorized", "unauthorized"),
            500: ("internal_server_error", "internal_server_error"),
            503: ("internal_server_error", "service_unavailable"),
        }
        if (error_type, error_code) != expected_map[http_status]:
            return AcpDelegateLinkInterventionAuditResult(
                allowed=False,
                reason_code="ACP_DELEGATE_PAYMENT_HTTP_STATUS_CODE_MISMATCH",
                handler_id=payment_handler_id,
            )
    if payment_handler_id == "com.stripe.link" and not link_authenticated_session_id.strip():
        return AcpDelegateLinkInterventionAuditResult(
            allowed=False,
            reason_code="ACP_STRIPE_LINK_SESSION_UNAUTHENTICATED",
            handler_id=payment_handler_id,
        )
    if intervention_type not in ACP_WALLET_INTERVENTION_TYPES:
        return AcpDelegateLinkInterventionAuditResult(
            allowed=False,
            reason_code="ACP_WALLET_INTERVENTION_TYPE_UNSUPPORTED",
            handler_id=payment_handler_id,
        )
    return AcpDelegateLinkInterventionAuditResult(
        allowed=True,
        reason_code="OK",
        handler_id=payment_handler_id,
    )


# ---------------------------------------------------------------------------
# SP-11: Google AP2 #252 Cross-Merchant External Budget Authority 4-Verb Gate
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Ap2CrossMerchantBudgetAuditResult:
    allowed: bool
    reason_code: str
    committed_minor: int
    held_minor: int
    remaining_minor: int


def evaluate_ap2_cross_merchant_budget_authority_guard(
    *,
    mandate_budget_minor: int,
    operations: Sequence[Mapping[str, Any]],
) -> Ap2CrossMerchantBudgetAuditResult:
    holds: dict[str, int] = {}
    committed = 0
    for op in operations:
        verb = str(op.get("verb", ""))
        hold_id = str(op.get("hold_id", ""))
        amount = int(op.get("amount_minor", 0))
        if verb == "authorize":
            if amount <= 0 or hold_id in holds:
                return Ap2CrossMerchantBudgetAuditResult(
                    allowed=False,
                    reason_code="AP2_BUDGET_AUTHORIZE_INVALID_OR_DUPLICATE",
                    committed_minor=committed,
                    held_minor=sum(holds.values()),
                    remaining_minor=mandate_budget_minor - committed - sum(holds.values()),
                )
            if committed + sum(holds.values()) + amount > mandate_budget_minor:
                return Ap2CrossMerchantBudgetAuditResult(
                    allowed=False,
                    reason_code="AP2_CROSS_MERCHANT_BUDGET_EXCEEDED",
                    committed_minor=committed,
                    held_minor=sum(holds.values()),
                    remaining_minor=mandate_budget_minor - committed - sum(holds.values()),
                )
            holds[hold_id] = amount
        elif verb == "commit":
            if hold_id not in holds:
                return Ap2CrossMerchantBudgetAuditResult(
                    allowed=False,
                    reason_code="AP2_BUDGET_COMMIT_WITHOUT_ACTIVE_HOLD",
                    committed_minor=committed,
                    held_minor=sum(holds.values()),
                    remaining_minor=mandate_budget_minor - committed - sum(holds.values()),
                )
            held_amt = holds.pop(hold_id)
            if amount <= 0 or amount > held_amt:
                return Ap2CrossMerchantBudgetAuditResult(
                    allowed=False,
                    reason_code="AP2_BUDGET_COMMIT_EXCEEDS_HOLD",
                    committed_minor=committed,
                    held_minor=sum(holds.values()),
                    remaining_minor=mandate_budget_minor - committed - sum(holds.values()),
                )
            committed += amount
        elif verb == "refund":
            if amount <= 0 or amount > committed:
                return Ap2CrossMerchantBudgetAuditResult(
                    allowed=False,
                    reason_code="AP2_BUDGET_REFUND_EXCEEDS_COMMITTED",
                    committed_minor=committed,
                    held_minor=sum(holds.values()),
                    remaining_minor=mandate_budget_minor - committed - sum(holds.values()),
                )
            committed -= amount
        elif verb == "query":
            continue
        else:
            return Ap2CrossMerchantBudgetAuditResult(
                allowed=False,
                reason_code="AP2_BUDGET_UNKNOWN_VERB",
                committed_minor=committed,
                held_minor=sum(holds.values()),
                remaining_minor=mandate_budget_minor - committed - sum(holds.values()),
            )
    held_total = sum(holds.values())
    return Ap2CrossMerchantBudgetAuditResult(
        allowed=True,
        reason_code="OK",
        committed_minor=committed,
        held_minor=held_total,
        remaining_minor=mandate_budget_minor - committed - held_total,
    )


# ---------------------------------------------------------------------------
# SP-12: Google AP2 #229 AP2-Haggle & #228 Solana Pay Reference Pubkey Binding
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Ap2HaggleAndSolanaPayAuditResult:
    allowed: bool
    reason_code: str
    settled_signature: str


def evaluate_ap2_haggle_and_solana_pay_reference_guard(
    *,
    walk_away_price_minor: int,
    max_rounds: int,
    deadline_epoch_s: int,
    required_terms: Mapping[str, Any],
    offer_price_minor: int,
    offer_round: int,
    offer_timestamp_s: int,
    offer_terms: Mapping[str, Any],
    solana_pay_reference_pubkey: str,
    tx_readonly_accounts: Sequence[str],
    indexed_signatures_for_reference: Sequence[str],
) -> Ap2HaggleAndSolanaPayAuditResult:
    if offer_round <= 0 or offer_round > max_rounds:
        return Ap2HaggleAndSolanaPayAuditResult(
            allowed=False,
            reason_code="AP2_HAGGLE_MAX_ROUNDS_EXCEEDED",
            settled_signature="",
        )
    if offer_timestamp_s > deadline_epoch_s:
        return Ap2HaggleAndSolanaPayAuditResult(
            allowed=False,
            reason_code="AP2_HAGGLE_DEADLINE_EXPIRED",
            settled_signature="",
        )
    if offer_price_minor > walk_away_price_minor:
        return Ap2HaggleAndSolanaPayAuditResult(
            allowed=False,
            reason_code="AP2_HAGGLE_OFFER_EXCEEDS_WALK_AWAY_PRICE",
            settled_signature="",
        )
    for k, v in required_terms.items():
        if offer_terms.get(k) != v:
            return Ap2HaggleAndSolanaPayAuditResult(
                allowed=False,
                reason_code="AP2_HAGGLE_REQUIRED_TERM_MISMATCH",
                settled_signature="",
            )
    if (
        not solana_pay_reference_pubkey.strip()
        or solana_pay_reference_pubkey not in tx_readonly_accounts
    ):
        return Ap2HaggleAndSolanaPayAuditResult(
            allowed=False,
            reason_code="AP2_SOLANA_PAY_REFERENCE_PUBKEY_MISSING",
            settled_signature="",
        )
    if len(indexed_signatures_for_reference) != 1:
        return Ap2HaggleAndSolanaPayAuditResult(
            allowed=False,
            reason_code="AP2_SOLANA_PAY_REFERENCE_MUST_RESOLVE_SINGLE_TX",
            settled_signature="",
        )
    return Ap2HaggleAndSolanaPayAuditResult(
        allowed=True,
        reason_code="OK",
        settled_signature=indexed_signatures_for_reference[0],
    )


# ---------------------------------------------------------------------------
# SP-13: MCP #3392 Extension Lifecycle, #3371 SDK Registration & #3364 Version
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class McpExtensionLifecycleAndSdkAuditResult:
    allowed: bool
    reason_code: str
    maturity_stage: str


def evaluate_mcp_extension_lifecycle_and_sdk_guard(
    *,
    repo_name: str,
    has_breaking_change: bool,
    has_extensions_track_sep: bool,
    registered_extensions: Sequence[Mapping[str, Any]],
    active_runtime_capabilities: Sequence[str],
    protocol_version: str,
    negotiated_via_initialize: bool,
) -> McpExtensionLifecycleAndSdkAuditResult:
    if repo_name.startswith("experimental-ext-"):
        stage = "experimental"
    elif repo_name.startswith("beta-ext-"):
        stage = "beta"
    elif repo_name.startswith("ext-"):
        stage = "stable"
    else:
        return McpExtensionLifecycleAndSdkAuditResult(
            allowed=False,
            reason_code="MCP_EXTENSION_REPO_NAMING_INVALID",
            maturity_stage="unknown",
        )
    if stage == "stable" and has_breaking_change and not has_extensions_track_sep:
        return McpExtensionLifecycleAndSdkAuditResult(
            allowed=False,
            reason_code="MCP_STABLE_EXTENSION_BREAKING_CHANGE_REQUIRES_SEP",
            maturity_stage=stage,
        )
    # #3371: order-independent dependency verification against active runtime capabilities + registered set
    available = set(active_runtime_capabilities) | {
        str(ext.get("name", "")) for ext in registered_extensions
    }
    for ext in registered_extensions:
        deps = ext.get("dependencies", ())
        for dep in deps:
            if dep not in available:
                return McpExtensionLifecycleAndSdkAuditResult(
                    allowed=False,
                    reason_code=f"MCP_SDK_EXTENSION_MISSING_DEPENDENCY:{dep}",
                    maturity_stage=stage,
                )
    if protocol_version == "2025-11-25" and not negotiated_via_initialize:
        return McpExtensionLifecycleAndSdkAuditResult(
            allowed=False,
            reason_code="MCP_2025_11_25_REQUIRES_INITIALIZE_NEGOTIATION",
            maturity_stage=stage,
        )
    return McpExtensionLifecycleAndSdkAuditResult(
        allowed=True,
        reason_code="OK",
        maturity_stage=stage,
    )


# ---------------------------------------------------------------------------
# SP-14: Stripe AI #434, #453 & #457 Override Ceiling & Link Mandate Binding
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class StripeLinkOverrideAndProjectsAuditResult:
    allowed: bool
    reason_code: str
    settled_amount_minor: int


def evaluate_stripe_link_override_and_projects_guard(
    *,
    mandate_maximum_minor: int,
    requested_settlement_override_minor: int,
    link_session_bound_to_mandate: bool,
    projects_cli_preflight_ok: bool,
) -> StripeLinkOverrideAndProjectsAuditResult:
    if not projects_cli_preflight_ok:
        return StripeLinkOverrideAndProjectsAuditResult(
            allowed=False,
            reason_code="STRIPE_PROJECTS_PREFLIGHT_FAILED",
            settled_amount_minor=0,
        )
    if not link_session_bound_to_mandate:
        return StripeLinkOverrideAndProjectsAuditResult(
            allowed=False,
            reason_code="STRIPE_LINK_SESSION_NOT_BOUND_TO_MANDATE",
            settled_amount_minor=0,
        )
    if requested_settlement_override_minor <= 0 or requested_settlement_override_minor > mandate_maximum_minor:
        return StripeLinkOverrideAndProjectsAuditResult(
            allowed=False,
            reason_code="STRIPE_SETTLEMENT_OVERRIDE_EXCEEDS_MANDATE_CEILING",
            settled_amount_minor=requested_settlement_override_minor,
        )
    return StripeLinkOverrideAndProjectsAuditResult(
        allowed=True,
        reason_code="OK",
        settled_amount_minor=requested_settlement_override_minor,
    )


# ---------------------------------------------------------------------------
# SP-15: Visa TAP #26, #25, #23 & #16 Header Coverage & Provisional Ceiling
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class VisaTapSignatureAndCeilingAuditResult:
    allowed: bool
    reason_code: str
    captured_minor: int


def evaluate_visa_tap_signature_and_provisional_ceiling_guard(
    *,
    signed_headers: Sequence[str],
    provisional_maximum_minor: int,
    requested_capture_minor: int,
    tap_key_id: str,
) -> VisaTapSignatureAndCeilingAuditResult:
    required_headers = {"@authority", "@path", "payment-token", "ucp-agent", "signature-agent"}
    hdr_set = {h.lower() for h in signed_headers}
    if not required_headers.issubset(hdr_set) or not tap_key_id.strip():
        return VisaTapSignatureAndCeilingAuditResult(
            allowed=False,
            reason_code="VISA_TAP_REQUIRED_SIGNATURE_HEADERS_MISSING",
            captured_minor=0,
        )
    if requested_capture_minor <= 0 or requested_capture_minor > provisional_maximum_minor:
        return VisaTapSignatureAndCeilingAuditResult(
            allowed=False,
            reason_code="VISA_TAP_CAPTURE_EXCEEDS_PROVISIONAL_CEILING",
            captured_minor=requested_capture_minor,
        )
    return VisaTapSignatureAndCeilingAuditResult(
        allowed=True,
        reason_code="OK",
        captured_minor=requested_capture_minor,
    )


# ---------------------------------------------------------------------------
# SP-16: Sierra tau2-bench #611 Active Line Refuel, #609/#610 Live DB & #606
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Tau2TelecomLiveDbAndBankingSyncAuditResult:
    allowed: bool
    reason_code: str
    reward_from_live_db: bool
    replay_divergence_recorded: bool


def evaluate_tau2_telecom_live_db_and_banking_sync_guard(
    *,
    telecom_line_status: str,
    refuel_gb: float,
    db_mutated_on_rejected_call: bool,
    live_db_hash: str,
    replayed_db_hash: str,
    expected_gold_db_hash: str,
    injected_fault_mode: str,
    banking_individual_tasks: Mapping[str, Mapping[str, Any]],
    banking_aggregate_tasks: Sequence[Mapping[str, Any]],
) -> Tau2TelecomLiveDbAndBankingSyncAuditResult:
    # #611: only 'active' telecom line can refuel data; rejected calls must not mutate DB/bill
    if telecom_line_status != "active":
        if db_mutated_on_rejected_call:
            return Tau2TelecomLiveDbAndBankingSyncAuditResult(
                allowed=False,
                reason_code="TAU2_INACTIVE_LINE_MUTATED_BILL_OR_DATA",
                reward_from_live_db=False,
                replay_divergence_recorded=False,
            )
        return Tau2TelecomLiveDbAndBankingSyncAuditResult(
            allowed=False,
            reason_code=f"TAU2_TELECOM_LINE_NOT_ACTIVE:{telecom_line_status}",
            reward_from_live_db=False,
            replay_divergence_recorded=False,
        )
    if refuel_gb <= 0:
        return Tau2TelecomLiveDbAndBankingSyncAuditResult(
            allowed=False,
            reason_code="TAU2_TELECOM_REFUEL_AMOUNT_INVALID",
            reward_from_live_db=False,
            replay_divergence_recorded=False,
        )
    # #606: banking aggregate tasks.json must match individual task files without duplicate IDs or missing NL_ASSERTION
    seen_ids: set[str] = set()
    for task_obj in banking_aggregate_tasks:
        tid = str(task_obj.get("id", ""))
        if not tid or tid in seen_ids:
            return Tau2TelecomLiveDbAndBankingSyncAuditResult(
                allowed=False,
                reason_code="TAU2_BANKING_AGGREGATE_DUPLICATE_OR_EMPTY_ID",
                reward_from_live_db=False,
                replay_divergence_recorded=False,
            )
        seen_ids.add(tid)
        if banking_individual_tasks.get(tid) != task_obj:
            return Tau2TelecomLiveDbAndBankingSyncAuditResult(
                allowed=False,
                reason_code=f"TAU2_BANKING_AGGREGATE_STALE_TASK:{tid}",
                reward_from_live_db=False,
                replay_divergence_recorded=False,
            )
    if set(banking_individual_tasks.keys()) != seen_ids:
        return Tau2TelecomLiveDbAndBankingSyncAuditResult(
            allowed=False,
            reason_code="TAU2_BANKING_AGGREGATE_ID_SET_MISMATCH",
            reward_from_live_db=False,
            replay_divergence_recorded=False,
        )
    # #609 & #610: grade against live_db_hash; record replay_divergence in RewardInfo.info when timeout_after_commit diverges
    if live_db_hash != expected_gold_db_hash:
        return Tau2TelecomLiveDbAndBankingSyncAuditResult(
            allowed=False,
            reason_code="TAU2_LIVE_DB_HASH_MISMATCH",
            reward_from_live_db=False,
            replay_divergence_recorded=(live_db_hash != replayed_db_hash),
        )
    replay_diverged = live_db_hash != replayed_db_hash
    if injected_fault_mode == "timeout_after_commit" and not replay_diverged:
        return Tau2TelecomLiveDbAndBankingSyncAuditResult(
            allowed=False,
            reason_code="TAU2_TIMEOUT_AFTER_COMMIT_DIVERGENCE_NOT_DETECTED",
            reward_from_live_db=True,
            replay_divergence_recorded=False,
        )
    return Tau2TelecomLiveDbAndBankingSyncAuditResult(
        allowed=True,
        reason_code="OK",
        reward_from_live_db=True,
        replay_divergence_recorded=replay_diverged,
    )
